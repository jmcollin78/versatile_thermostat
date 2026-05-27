"""Implements the Humidity control Feature Manager."""

# pylint: disable=line-too-long

from typing import Any

from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.event import (
    async_track_state_change_event,
    EventStateChangedData,
)

from vtherm_api.log_collector import get_vtherm_logger

from .base_manager import BaseFeatureManager
from .commons import write_event_log
from .commons_type import ConfigData
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .vtherm_hvac_mode import (
    VThermHvacMode,
    VThermHvacMode_COOL,
    VThermHvacMode_DRY,
    VThermHvacMode_OFF,
)

_LOGGER = get_vtherm_logger(__name__)


class FeatureHumidityManager(BaseFeatureManager):
    """Humidity target management for thermostat_over_climate."""

    unrecorded_attributes = frozenset(
        {
            "is_humidity_configured",
            "humidity_manager",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager."""
        super().__init__(vtherm, hass)
        self._is_configured: bool = False
        self._humidity_sensor_entity_id: str | None = None
        self._humidity_control_mode: str = CONF_HUMIDITY_MODE_OFF
        self._target_humidity: int = DEFAULT_TARGET_HUMIDITY
        self._current_humidity: float | None = None
        self._last_humidity_measure = None
        self._is_humidity_available: bool = False
        self._humidity_stale_delay_min = None
        self._humidity_tolerance: float = DEFAULT_HUMIDITY_TOLERANCE

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager."""
        self._humidity_sensor_entity_id = entry_infos.get(CONF_HUMIDITY_SENSOR)
        self._humidity_control_mode = entry_infos.get(
            CONF_HUMIDITY_MODE, CONF_HUMIDITY_MODE_OFF
        )
        self._target_humidity = DEFAULT_TARGET_HUMIDITY
        self._humidity_tolerance = float(
            entry_infos.get(CONF_HUMIDITY_TOLERANCE, DEFAULT_HUMIDITY_TOLERANCE)
        )
        self._humidity_stale_delay_min = entry_infos.get(
            CONF_HUMIDITY_SAFETY_DELAY_MIN,
            DEFAULT_HUMIDITY_SAFETY_DELAY_MIN,
        )
        self._is_configured = (
            entry_infos.get(CONF_USE_HUMIDITY_FEATURE, False) is True
            and self._humidity_control_mode != CONF_HUMIDITY_MODE_OFF
            and self._vtherm.is_over_climate
            and not self._vtherm.have_valve_regulation
        )
        if not self._is_configured:
            self._current_humidity = None
            self._last_humidity_measure = None
            self._is_humidity_available = False

    @overrides
    async def start_listening(self):
        """Start listening to the external humidity sensor if configured."""
        self.stop_listening()
        if self._is_configured and self._humidity_sensor_entity_id:
            self.add_listener(
                async_track_state_change_event(
                    self.hass,
                    [self._humidity_sensor_entity_id],
                    self._humidity_sensor_changed,
                )
            )

    @overrides
    async def refresh_state(self) -> bool:
        """Refresh current humidity and return True if it changed."""
        if not self._is_configured:
            return False

        if self._humidity_sensor_entity_id:
            state = self.hass.states.get(self._humidity_sensor_entity_id)
            humidity = (
                get_safe_float_value(state.state)
                if state is not None
                and state.state not in [None, "None", STATE_UNAVAILABLE, STATE_UNKNOWN]
                else None
            )
            measurement_date = (
                self._vtherm.get_state_date_or_now(state)
                if state is not None and humidity is not None
                else None
            )
        else:
            humidity = self._get_underlying_current_humidity()
            measurement_date = self._vtherm.now if humidity is not None else None

        return self._update_current_humidity(humidity, measurement_date)

    async def refresh_and_update_if_changed(self) -> bool:
        """Refresh current humidity and force a VTherm state update if needed."""
        if await self.refresh_state():
            write_event_log(
                _LOGGER,
                self._vtherm,
                f"Humidity changed to {self._current_humidity}",
            )
            await self._async_update_vtherm_control()
            return True
        return False

    @callback
    async def _humidity_sensor_changed(self, event: Event[EventStateChangedData]):
        """Handle humidity sensor changes."""
        new_state = event.data.get("new_state")
        write_event_log(
            _LOGGER,
            self._vtherm,
            f"Humidity sensor changed to state {new_state.state if new_state else None}",
        )

        if new_state is None:
            return

        await self.refresh_and_update_if_changed()

    def _get_underlying_current_humidity(self) -> float | None:
        """Return current humidity from the first underlying climate if available."""
        if not hasattr(self._vtherm, "underlying_entity"):
            return None

        underlying = self._vtherm.underlying_entity(0)
        if not underlying:
            return None

        return get_safe_float_value(underlying.current_humidity)

    def _is_current_humidity_stale(self) -> bool:
        """Return True if the last humidity measurement is older than safety delay."""
        if self._humidity_stale_delay_min is None or self._last_humidity_measure is None:
            return False

        delta_humidity = (
            self._vtherm.now - self._last_humidity_measure
        ).total_seconds() / 60.0
        return delta_humidity > self._humidity_stale_delay_min

    def _update_current_humidity(self, humidity: float | None, measurement_date=None) -> bool:
        """Set current humidity and return True if it changed."""
        old_humidity = self._current_humidity
        old_measure = self._last_humidity_measure
        old_available = self._is_humidity_available

        if humidity is None:
            self._current_humidity = None
            self._last_humidity_measure = None
            self._is_humidity_available = False
            return (
                old_humidity != self._current_humidity
                or old_measure != self._last_humidity_measure
                or old_available != self._is_humidity_available
            )

        humidity = round(float(humidity), 1)
        self._current_humidity = humidity
        self._last_humidity_measure = measurement_date or self._vtherm.now
        self._is_humidity_available = not self._is_current_humidity_stale()
        return (
            old_humidity != self._current_humidity
            or old_measure != self._last_humidity_measure
            or old_available != self._is_humidity_available
        )

    async def async_set_target_humidity(self, humidity: int):
        """Set a new humidity target."""
        target_humidity = min(
            self.max_humidity,
            max(self.min_humidity, int(humidity)),
        )
        if target_humidity == self._target_humidity:
            return

        self._target_humidity = target_humidity
        await self._async_update_vtherm_control()

    async def _async_update_vtherm_control(self):
        """Update VTherm state and run a control cycle when only humidity changed."""
        self._vtherm.requested_state.force_changed()
        state_changed = await self._vtherm.update_states(force=True)
        if not state_changed:
            await self._vtherm.async_control_heating(force=True)

    def _is_auto_start_stop_enabled(self) -> bool:
        """Return True when auto start/stop is enabled on the VTherm."""
        auto_start_stop_manager = self._vtherm.auto_start_stop_manager
        return bool(
            auto_start_stop_manager
            and auto_start_stop_manager.is_configured
            and auto_start_stop_manager.auto_start_stop_enable
            and auto_start_stop_manager.auto_start_stop_level != AUTO_START_STOP_LEVEL_NONE
        )

    def calculate_hvac_mode(
        self,
        requested_hvac_mode: VThermHvacMode,
        current_hvac_mode: VThermHvacMode,
        vtherm_hvac_modes: list[VThermHvacMode],
    ) -> VThermHvacMode | None:
        """Return the humidity-driven HVAC mode, or None to keep default logic."""
        if not self._is_configured or requested_hvac_mode == VThermHvacMode_OFF:
            return None

        self.log_humidity_state(
            requested_hvac_mode=requested_hvac_mode,
            current_hvac_mode=current_hvac_mode,
        )

        if not self.is_humidity_available:
            return None

        dry_is_available = VThermHvacMode_DRY in vtherm_hvac_modes

        if requested_hvac_mode == VThermHvacMode_DRY:
            if not dry_is_available:
                return None
            if not self._is_auto_start_stop_enabled():
                return VThermHvacMode_DRY
            if current_hvac_mode == VThermHvacMode_DRY:
                return VThermHvacMode_OFF if self.is_target_reached else VThermHvacMode_DRY
            return VThermHvacMode_DRY if self.is_humidity_too_high else VThermHvacMode_OFF

        if (
            requested_hvac_mode == VThermHvacMode_COOL
            and self._humidity_control_mode == CONF_HUMIDITY_MODE_COOL_ASSIST
            and dry_is_available
        ):
            if self.is_cooling_needed:
                return VThermHvacMode_COOL
            if current_hvac_mode == VThermHvacMode_DRY:
                return VThermHvacMode_DRY
            return VThermHvacMode_DRY if self.is_humidity_too_high else VThermHvacMode_COOL

        return None

    def log_humidity_state(
        self,
        requested_hvac_mode: VThermHvacMode | None = None,
        current_hvac_mode: VThermHvacMode | None = None,
    ) -> None:
        """Log current humidity regulation state for troubleshooting."""
        if not self._is_configured:
            return

        _LOGGER.debug(
            "%s - checking humidity current=%s raw_current=%s target=%s tolerance=%.1f mode=%s "
            "available=%s stale=%s last_measure=%s too_high=%s target_reached=%s "
            "dehumidifying_required=%s auto_start_stop_enabled=%s requested_hvac_mode=%s current_hvac_mode=%s",
            self,
            self.current_humidity,
            self._current_humidity,
            self._target_humidity,
            self._humidity_tolerance,
            self._humidity_control_mode,
            self.is_humidity_available,
            self._is_current_humidity_stale(),
            self._last_humidity_measure,
            self.is_humidity_too_high,
            self.is_target_reached,
            self.is_dehumidifying_required,
            self._is_auto_start_stop_enabled(),
            requested_hvac_mode,
            current_hvac_mode,
        )

    @callback
    @overrides
    def restore_state(self, old_state) -> None:
        """Restore target humidity after a Home Assistant restart."""
        if not self._is_configured or not old_state:
            return

        target_humidity = get_safe_float_value(old_state.attributes.get("humidity"))
        if target_humidity is not None:
            self._target_humidity = int(target_humidity)

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add humidity manager custom attributes."""
        extra_state_attributes.update(
            {
                "is_humidity_configured": self._is_configured,
            }
        )
        if self._is_configured:
            extra_state_attributes.update(
                {
                    "humidity_manager": {
                        "humidity_sensor_entity_id": self._humidity_sensor_entity_id,
                        "humidity_control_mode": self._humidity_control_mode,
                        "current_humidity": self.current_humidity,
                        "last_humidity_measure": self._last_humidity_measure,
                        "is_humidity_available": self.is_humidity_available,
                        "target_humidity": self._target_humidity,
                        "humidity_tolerance": self._humidity_tolerance,
                        "humidity_safety_delay_min": self._humidity_stale_delay_min,
                        "is_humidity_too_high": self.is_humidity_too_high,
                        "is_target_reached": self.is_target_reached,
                    }
                }
            )

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True if humidity management is configured."""
        return self._is_configured

    @property
    def humidity_sensor_entity_id(self) -> str | None:
        """Return the configured humidity sensor."""
        return self._humidity_sensor_entity_id

    @property
    def humidity_control_mode(self) -> str:
        """Return the configured humidity control mode."""
        return self._humidity_control_mode

    @property
    def current_humidity(self) -> float | None:
        """Return current humidity."""
        return self._current_humidity if self.is_humidity_available else None

    @property
    def last_humidity_measure(self):
        """Return the last valid humidity measurement time."""
        return self._last_humidity_measure

    @property
    def is_humidity_available(self) -> bool:
        """Return True when the current humidity measurement can drive regulation."""
        return self._is_humidity_available and not self._is_current_humidity_stale()

    @property
    def target_humidity(self) -> int:
        """Return target humidity."""
        return self._target_humidity

    @property
    def min_humidity(self) -> int:
        """Return minimum settable humidity."""
        return DEFAULT_HUMIDITY_MIN

    @property
    def max_humidity(self) -> int:
        """Return maximum settable humidity."""
        return DEFAULT_HUMIDITY_MAX

    @property
    def target_humidity_step(self) -> int:
        """Return target humidity step."""
        return DEFAULT_HUMIDITY_STEP

    @property
    def humidity_tolerance(self) -> float:
        """Return humidity hysteresis tolerance."""
        return self._humidity_tolerance

    @property
    def is_humidity_too_high(self) -> bool:
        """Return True if humidity is high enough to start dehumidifying."""
        return (
            self.current_humidity is not None
            and self._target_humidity is not None
            and self.current_humidity > self._target_humidity + self._humidity_tolerance
        )

    @property
    def is_target_reached(self) -> bool:
        """Return True if humidity target is reached."""
        return (
            self.current_humidity is not None
            and self._target_humidity is not None
            and self.current_humidity <= self._target_humidity
        )

    @property
    def is_dehumidifying_required(self) -> bool:
        """Return True while humidity is above the configured target."""
        return (
            self.current_humidity is not None
            and self._target_humidity is not None
            and self.current_humidity > self._target_humidity
        )

    @property
    def is_cooling_needed(self) -> bool:
        """Return True if room temperature still requires cool mode."""
        current_temperature = self._vtherm.current_temperature
        target_temperature = self._vtherm.target_temperature
        if current_temperature is None or target_temperature is None:
            return False

        temperature_tolerance = max(
            getattr(self._vtherm, "target_temperature_step", None)
            or DEFAULT_HUMIDITY_COOLING_TEMPERATURE_TOLERANCE,
            DEFAULT_HUMIDITY_COOLING_TEMPERATURE_TOLERANCE,
        )
        return current_temperature > target_temperature + temperature_tolerance

    @property
    def is_detected(self) -> bool:
        """Return the overall state of the feature manager."""
        return self.is_dehumidifying_required

    def __str__(self):
        return f"HumidityManager-{self.name}"
