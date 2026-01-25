# pylint: disable=line-too-long

""" Implements the Heating Failure Detection as a Feature Manager"""

import logging
from typing import Any
from datetime import datetime, timedelta

from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template

from .const import (
    CONF_USE_HEATING_FAILURE_DETECTION_FEATURE,
    CONF_HEATING_FAILURE_THRESHOLD,
    CONF_COOLING_FAILURE_THRESHOLD,
    CONF_HEATING_FAILURE_DETECTION_DELAY,
    CONF_TEMPERATURE_CHANGE_TOLERANCE,
    CONF_FAILURE_DETECTION_ENABLE_TEMPLATE,
    DEFAULT_HEATING_FAILURE_THRESHOLD,
    DEFAULT_COOLING_FAILURE_THRESHOLD,
    DEFAULT_HEATING_FAILURE_DETECTION_DELAY,
    DEFAULT_TEMPERATURE_CHANGE_TOLERANCE,
    EventType,
    overrides,
)
from .commons import write_event_log
from .commons_type import ConfigData

from .base_manager import BaseFeatureManager
from .vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_HEAT

_LOGGER = logging.getLogger(__name__)


class FeatureHeatingFailureDetectionManager(BaseFeatureManager):
    """The implementation of the Heating Failure Detection feature

    This feature detects:
    1. Heating failure: high on_percent but temperature not increasing
    2. Cooling failure: on_percent at 0 but temperature still increasing
    """

    unrecorded_attributes = frozenset(
        {
            "heating_failure_threshold",
            "cooling_failure_threshold",
            "heating_failure_detection_delay",
            "temperature_change_tolerance",
            "is_heating_failure_detection_configured",
            "failure_detection_enable_template",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)

        self._is_configured: bool = False
        self._heating_failure_threshold: float = DEFAULT_HEATING_FAILURE_THRESHOLD
        self._cooling_failure_threshold: float = DEFAULT_COOLING_FAILURE_THRESHOLD
        self._heating_failure_detection_delay: int = DEFAULT_HEATING_FAILURE_DETECTION_DELAY
        self._temperature_change_tolerance: float = DEFAULT_TEMPERATURE_CHANGE_TOLERANCE
        self._failure_detection_enable_template: Template | None = None

        # State tracking
        self._heating_failure_state: str = STATE_UNAVAILABLE
        self._cooling_failure_state: str = STATE_UNAVAILABLE

        # Temperature tracking for failure detection
        self._last_check_time: datetime | None = None
        self._last_check_temperature: float | None = None
        self._high_power_start_time: datetime | None = None
        self._zero_power_start_time: datetime | None = None

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""

        use_feature = entry_infos.get(CONF_USE_HEATING_FAILURE_DETECTION_FEATURE, False)

        if not use_feature:
            self._is_configured = False
            self._heating_failure_state = STATE_UNAVAILABLE
            self._cooling_failure_state = STATE_UNAVAILABLE
            return

        self._heating_failure_threshold = entry_infos.get(
            CONF_HEATING_FAILURE_THRESHOLD,
            DEFAULT_HEATING_FAILURE_THRESHOLD
        )
        self._cooling_failure_threshold = entry_infos.get(
            CONF_COOLING_FAILURE_THRESHOLD,
            DEFAULT_COOLING_FAILURE_THRESHOLD
        )
        self._heating_failure_detection_delay = entry_infos.get(
            CONF_HEATING_FAILURE_DETECTION_DELAY,
            DEFAULT_HEATING_FAILURE_DETECTION_DELAY
        )
        self._temperature_change_tolerance = entry_infos.get(CONF_TEMPERATURE_CHANGE_TOLERANCE, DEFAULT_TEMPERATURE_CHANGE_TOLERANCE)

        # Initialize the enable template if provided
        template_str = entry_infos.get(CONF_FAILURE_DETECTION_ENABLE_TEMPLATE)
        if template_str:
            self._failure_detection_enable_template = Template(template_str, self._hass)
        else:
            self._failure_detection_enable_template = None

        self._is_configured = True
        self._heating_failure_state = STATE_UNKNOWN
        self._cooling_failure_state = STATE_UNKNOWN

    @overrides
    async def start_listening(self):
        """Start listening the underlying entity"""
        # No external entity to listen to for this feature

    @overrides
    def stop_listening(self):
        """Stop listening and remove the eventual timer still running"""

    def _is_detection_enabled_by_template(self) -> bool:
        """Evaluate the enable template to determine if detection should be active.
        Returns True if detection is enabled (template returns True or no template configured).
        Returns False if template returns False.
        If template evaluation fails, returns True (detection enabled) as a safety measure.
        """
        if self._failure_detection_enable_template is None:
            # No template configured, detection is always enabled
            return True

        try:
            result = self._failure_detection_enable_template.async_render()
            # Handle various truthy/falsy values
            if isinstance(result, bool):
                return result
            if isinstance(result, str):
                return result.lower() in ("true", "1", "yes", "on")
            return bool(result)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning(
                "%s - Error evaluating failure_detection_enable_template: %s. Detection remains enabled.",
                self, err
            )
            # On error, enable detection as a safety measure
            return True

    @overrides
    async def refresh_state(self) -> bool:
        """Check for heating/cooling failures
        Return True if a failure is detected"""

        if not self._is_configured:
            _LOGGER.debug("%s - heating failure detection is disabled (or not configured)", self)
            return False

        # Only check for VTherms with proportional algorithm
        if not self._vtherm.has_prop:
            _LOGGER.debug("%s - heating failure detection skipped (no proportional algorithm)", self)
            return False

        if self._vtherm.requested_state.hvac_mode == VThermHvacMode_OFF:
            self._reset_tracking()
            self._heating_failure_state = STATE_OFF
            self._cooling_failure_state = STATE_OFF
            _LOGGER.debug("%s - heating failure detection is OFF because requested_state is OFF", self)
            return False

        # Check if detection is enabled by template
        if not self._is_detection_enabled_by_template():
            _LOGGER.debug("%s - heating failure detection is disabled by template", self)
            # Reset tracking when template disables detection
            self._reset_tracking()
            # Keep states at OFF when disabled by template (not UNAVAILABLE since feature is configured)
            if self._heating_failure_state == STATE_ON:
                self._heating_failure_state = STATE_OFF
                self._send_heating_failure_event("heating_failure_end", 0, 0, self._vtherm.current_temperature or 0)
            if self._cooling_failure_state == STATE_ON:
                self._cooling_failure_state = STATE_OFF
                self._send_cooling_failure_event("cooling_failure_end", 0, 0, self._vtherm.current_temperature or 0)
            return False

        now = self._vtherm.now

        # Get current values
        current_temp = self._vtherm.current_temperature
        on_percent = self._vtherm.on_percent

        if current_temp is None or on_percent is None:
            _LOGGER.debug("%s - heating failure detection skipped (no temp or on_percent)", self)
            return False

        # Determine the mode (heating or cooling)
        is_heating_mode = self._vtherm.vtherm_hvac_mode == VThermHvacMode_HEAT

        # Initialize tracking if needed
        if self._last_check_time is None:
            self._last_check_time = now
            self._last_check_temperature = current_temp
            return False

        detection_delay_td = timedelta(minutes=self._heating_failure_detection_delay)

        # Check for heating and cooling failures
        if is_heating_mode:
            self._check_heating_failure(now, current_temp, on_percent, detection_delay_td)
            self._check_cooling_failure(now, current_temp, on_percent, detection_delay_td)

        # Initialize states if still unknown
        if self._heating_failure_state == STATE_UNKNOWN:
            self._heating_failure_state = STATE_OFF
        if self._cooling_failure_state == STATE_UNKNOWN:
            self._cooling_failure_state = STATE_OFF

        return self.is_failure_detected

    def _check_heating_failure(self, now: datetime, current_temp: float, on_percent: float, detection_delay_td: timedelta):
        """Check for HEATING failure:
        High on_percent (>= threshold) but temperature not increasing"""

        old_heating_failure = self._heating_failure_state == STATE_ON

        if on_percent >= self._heating_failure_threshold:
            if self._high_power_start_time is None:
                self._high_power_start_time = now
                self._last_check_temperature = current_temp
                _LOGGER.debug(
                    "%s - Starting high power tracking (on_percent=%.2f >= threshold=%.2f)",
                    self, on_percent, self._heating_failure_threshold
                )
            else:
                elapsed = now - self._high_power_start_time
                if elapsed >= detection_delay_td:
                    # Check if temperature has increased enough (above tolerance)
                    if self._last_check_temperature is not None:
                        temp_diff = current_temp - self._last_check_temperature
                        if temp_diff < self._temperature_change_tolerance:
                            # Temperature not increasing enough - heating failure detected
                            if not old_heating_failure:
                                _LOGGER.warning(
                                    "%s - Heating failure detected: on_percent=%.2f%%, temp_diff=%.2f° (tolerance=%.2f°) over %d minutes",
                                    self,
                                    on_percent * 100,
                                    temp_diff,
                                    self._temperature_change_tolerance,
                                    self._heating_failure_detection_delay,
                                )
                                self._heating_failure_state = STATE_ON
                                self._send_heating_failure_event("heating_failure_start", on_percent, temp_diff, current_temp)
                        else:
                            # Temperature is increasing enough, reset if we were in failure
                            if old_heating_failure:
                                _LOGGER.info("%s - Heating failure ended: temperature is now increasing", self)
                                self._heating_failure_state = STATE_OFF
                                self._send_heating_failure_event("heating_failure_end", on_percent, temp_diff, current_temp)
                            self._high_power_start_time = now
                            self._last_check_temperature = current_temp
        else:
            # Not in high power, reset tracking
            if self._high_power_start_time is not None:
                self._high_power_start_time = None
                if old_heating_failure:
                    self._heating_failure_state = STATE_OFF
                    self._send_heating_failure_event("heating_failure_end", on_percent, 0, current_temp)

    def _check_cooling_failure(self, now: datetime, current_temp: float, on_percent: float, detection_delay_td: timedelta):
        """Check for COOLING failure:
        on_percent at 0 (or <= cooling threshold) but temperature still increasing"""

        old_cooling_failure = self._cooling_failure_state == STATE_ON

        if on_percent <= self._cooling_failure_threshold:
            if self._zero_power_start_time is None:
                self._zero_power_start_time = now
                self._last_check_temperature = current_temp
                _LOGGER.debug(
                    "%s - Starting zero power tracking (on_percent=%.2f <= threshold=%.2f)",
                    self, on_percent, self._cooling_failure_threshold
                )
            else:
                elapsed = now - self._zero_power_start_time
                if elapsed >= detection_delay_td:
                    # Check if temperature is increasing above tolerance
                    if self._last_check_temperature is not None:
                        temp_diff = current_temp - self._last_check_temperature
                        if temp_diff > self._temperature_change_tolerance:
                            # Temperature still increasing despite no heating - cooling failure
                            if not old_cooling_failure:
                                _LOGGER.warning(
                                    "%s - Cooling failure detected: on_percent=%.2f%%, temp_diff=+%.2f° (tolerance=%.2f°) over %d minutes",
                                    self,
                                    on_percent * 100,
                                    temp_diff,
                                    self._temperature_change_tolerance,
                                    self._heating_failure_detection_delay,
                                )
                                self._cooling_failure_state = STATE_ON
                                self._send_cooling_failure_event("cooling_failure_start", on_percent, temp_diff, current_temp)
                        else:
                            # Temperature is stable or decreasing, reset if we were in failure
                            if old_cooling_failure:
                                _LOGGER.info("%s - Cooling failure ended: temperature is now stable or decreasing", self)
                                self._cooling_failure_state = STATE_OFF
                                self._send_cooling_failure_event("cooling_failure_end", on_percent, temp_diff, current_temp)
                            self._zero_power_start_time = now
                            self._last_check_temperature = current_temp
        else:
            # Not at zero power, reset tracking
            if self._zero_power_start_time is not None:
                self._zero_power_start_time = None
                if old_cooling_failure:
                    self._cooling_failure_state = STATE_OFF
                    self._send_cooling_failure_event("cooling_failure_end", on_percent, 0, current_temp)

    def _reset_tracking(self):
        """Reset all tracking variables"""
        self._last_check_time = None
        self._last_check_temperature = None
        self._high_power_start_time = None
        self._zero_power_start_time = None

    def _send_heating_failure_event(self, event_type: str, on_percent: float, temp_diff: float, current_temp: float):
        """Send a heating failure event"""
        is_enabled_by_template = self._is_detection_enabled_by_template()
        # Log the event
        if event_type == "heating_failure_start":
            write_event_log(_LOGGER, self._vtherm, f"Heating failure detected: on_percent={on_percent*100:.0f}%, temp_diff={temp_diff:.2f}°")
        else:
            write_event_log(
                _LOGGER, self._vtherm, f"Heating failure ended: on_percent={on_percent*100:.0f}%, temp_diff={temp_diff:.2f}°, template_enabled={is_enabled_by_template}"
            )

        self._vtherm.send_event(
            EventType.HEATING_FAILURE_EVENT,
            {
                "type": event_type,
                "failure_type": "heating",
                "on_percent": on_percent,
                "temperature_difference": temp_diff,
                "current_temp": current_temp,
                "target_temp": self._vtherm.target_temperature,
                "threshold": self._heating_failure_threshold,
                "detection_delay_min": self._heating_failure_detection_delay,
                "is_enabled_by_template": is_enabled_by_template,
            },
        )

    def _send_cooling_failure_event(self, event_type: str, on_percent: float, temp_diff: float, current_temp: float):
        """Send a cooling failure event"""
        is_enabled_by_template = self._is_detection_enabled_by_template()
        # Log the event
        if event_type == "cooling_failure_start":
            write_event_log(_LOGGER, self._vtherm, f"Cooling failure detected: on_percent={on_percent*100:.0f}%, temp_diff=+{temp_diff:.2f}°")
        else:
            write_event_log(
                _LOGGER, self._vtherm, f"Cooling failure ended: on_percent={on_percent*100:.0f}%, temp_diff={temp_diff:.2f}°, template_enabled={is_enabled_by_template}"
            )

        self._vtherm.send_event(
            EventType.HEATING_FAILURE_EVENT,
            {
                "type": event_type,
                "failure_type": "cooling",
                "on_percent": on_percent,
                "temperature_difference": temp_diff,
                "current_temp": current_temp,
                "target_temp": self._vtherm.target_temperature,
                "threshold": self._cooling_failure_threshold,
                "detection_delay_min": self._heating_failure_detection_delay,
                "is_enabled_by_template": is_enabled_by_template,
            },
        )

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""

        extra_state_attributes.update(
            {
                "is_heating_failure_detection_configured": self._is_configured,
            }
        )

        if self._is_configured:
            # Calculate remaining time for heating failure detection
            heating_tracking_info = self._get_tracking_info(self._high_power_start_time, "heating")
            # Calculate remaining time for cooling failure detection
            cooling_tracking_info = self._get_tracking_info(self._zero_power_start_time, "cooling")

            # Get template status
            template_str = None
            template_enabled = True
            if self._failure_detection_enable_template is not None:
                template_str = self._failure_detection_enable_template.template
                template_enabled = self._is_detection_enabled_by_template()

            extra_state_attributes.update(
                {
                    "heating_failure_detection_manager": {
                        "heating_failure_state": self._heating_failure_state,
                        "cooling_failure_state": self._cooling_failure_state,
                        "heating_failure_threshold": self._heating_failure_threshold,
                        "cooling_failure_threshold": self._cooling_failure_threshold,
                        "detection_delay_min": self._heating_failure_detection_delay,
                        "temperature_change_tolerance": self._temperature_change_tolerance,
                        "failure_detection_enable_template": template_str,
                        "is_detection_enabled_by_template": template_enabled,
                        "heating_tracking": heating_tracking_info,
                        "cooling_tracking": cooling_tracking_info,
                    }
                }
            )

    def _get_tracking_info(self, start_time: datetime | None, tracking_type: str) -> dict[str, Any]:
        """Get tracking information for heating or cooling failure detection

        Args:
            start_time: The start time of the tracking (high_power or zero_power)
            tracking_type: "heating" or "cooling" for logging purposes

        Returns:
            A dictionary with tracking status information
        """
        if start_time is None:
            return {
                "is_tracking": False,
                "initial_temperature": None,
                "current_temperature": None,
                "remaining_time_min": None,
                "elapsed_time_min": None,
            }

        now = self._vtherm.now
        elapsed = now - start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        remaining_minutes = max(0, self._heating_failure_detection_delay - elapsed_minutes)

        return {
            "is_tracking": True,
            "initial_temperature": self._last_check_temperature,
            "current_temperature": self._vtherm.current_temperature,
            "remaining_time_min": round(remaining_minutes, 1),
            "elapsed_time_min": round(elapsed_minutes, 1),
        }

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True if the heating failure detection feature is configured"""
        return self._is_configured

    @property
    def is_failure_detected(self) -> bool:
        """Returns True if any failure is currently detected"""
        return self._heating_failure_state == STATE_ON or self._cooling_failure_state == STATE_ON

    @property
    def is_heating_failure_detected(self) -> bool:
        """Returns True if a heating failure is detected"""
        return self._heating_failure_state == STATE_ON

    @property
    def is_cooling_failure_detected(self) -> bool:
        """Returns True if a cooling failure is detected"""
        return self._cooling_failure_state == STATE_ON

    @property
    def heating_failure_state(self) -> str:
        """Returns the heating failure state: STATE_ON, STATE_OFF, STATE_UNKNOWN, STATE_UNAVAILABLE"""
        return self._heating_failure_state

    @property
    def cooling_failure_state(self) -> str:
        """Returns the cooling failure state: STATE_ON, STATE_OFF, STATE_UNKNOWN, STATE_UNAVAILABLE"""
        return self._cooling_failure_state

    @property
    def heating_failure_threshold(self) -> float:
        """Returns the heating failure threshold"""
        return self._heating_failure_threshold

    @property
    def cooling_failure_threshold(self) -> float:
        """Returns the cooling failure threshold"""
        return self._cooling_failure_threshold

    @property
    def detection_delay_min(self) -> int:
        """Returns the detection delay in minutes"""
        return self._heating_failure_detection_delay

    @property
    def temperature_change_tolerance(self) -> float:
        """Returns the temperature change tolerance in degrees"""
        return self._temperature_change_tolerance

    def __str__(self):
        return f"HeatingFailureDetectionManager-{self.name}"
