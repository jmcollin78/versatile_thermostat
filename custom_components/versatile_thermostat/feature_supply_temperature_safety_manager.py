# pylint: disable=line-too-long

"""Supply-water temperature safety manager."""

from datetime import timedelta
from collections.abc import Callable
from typing import Any

from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_call_later,
    async_track_state_change_event,
)

from vtherm_api.log_collector import get_vtherm_logger

from .base_manager import BaseFeatureManager
from .commons import write_event_log
from .commons_type import ConfigData
from .const import (
    CONF_SUPPLY_TEMP_COOL_MIN,
    CONF_SUPPLY_TEMP_DELAY_SEC,
    CONF_SUPPLY_TEMP_HEAT_MAX,
    CONF_SUPPLY_TEMP_SENSOR,
    CONF_SUPPLY_TEMP_TOLERANCE,
    DEFAULT_SUPPLY_TEMP_DELAY_SEC,
    DEFAULT_SUPPLY_TEMP_TOLERANCE,
    EventType,
    overrides,
)
from .vtherm_hvac_mode import (
    VThermHvacMode_COOL,
    VThermHvacMode_HEAT,
    VThermHvacMode_OFF,
)

_LOGGER = get_vtherm_logger(__name__)

REASON_HEAT_TOO_HOT = "heat_supply_temperature_too_hot"
REASON_COOL_TOO_COLD = "cool_supply_temperature_too_cold"
REASON_SENSOR_UNAVAILABLE = "supply_temperature_sensor_unavailable"


class FeatureSupplyTemperatureSafetyManager(BaseFeatureManager):
    """Blocks switch actuation when the supply-water temperature is unsafe."""

    unrecorded_attributes = frozenset(
        {
            "is_supply_temperature_safety_configured",
            "supply_temperature_sensor_entity_id",
            "supply_temperature",
            "supply_temperature_safety_state",
            "supply_temperature_safety_reason",
            "supply_temperature_heat_max",
            "supply_temperature_cool_min",
            "supply_temperature_tolerance",
            "supply_temperature_delay_sec",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Initialize the manager."""
        super().__init__(vtherm, hass)
        self._is_configured: bool = False
        self._supply_temp_sensor_entity_id: str | None = None
        self._heat_max: float | None = None
        self._cool_min: float | None = None
        self._tolerance: float = DEFAULT_SUPPLY_TEMP_TOLERANCE
        self._delay_sec: int = DEFAULT_SUPPLY_TEMP_DELAY_SEC
        self._current_supply_temperature: float | None = None
        self._safety_state: str = STATE_UNAVAILABLE
        self._safety_reason: str | None = None
        self._pending_call_cancel: Callable[[], None] | None = None

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Load configuration."""
        self._cancel_pending_call()

        self._supply_temp_sensor_entity_id = entry_infos.get(CONF_SUPPLY_TEMP_SENSOR)
        self._heat_max = entry_infos.get(CONF_SUPPLY_TEMP_HEAT_MAX)
        self._cool_min = entry_infos.get(CONF_SUPPLY_TEMP_COOL_MIN)
        self._tolerance = entry_infos.get(
            CONF_SUPPLY_TEMP_TOLERANCE,
            DEFAULT_SUPPLY_TEMP_TOLERANCE,
        )
        self._delay_sec = entry_infos.get(
            CONF_SUPPLY_TEMP_DELAY_SEC,
            DEFAULT_SUPPLY_TEMP_DELAY_SEC,
        )

        self._is_configured = bool(self._supply_temp_sensor_entity_id and (self._heat_max is not None or self._cool_min is not None))
        self._current_supply_temperature = None
        self._safety_reason = None
        self._safety_state = STATE_UNKNOWN if self._is_configured else STATE_UNAVAILABLE

    @overrides
    async def start_listening(self):
        """Listen to the configured supply temperature sensor."""
        if not self._is_configured:
            return

        self.stop_listening()
        self.add_listener(
            async_track_state_change_event(
                self.hass,
                [self._supply_temp_sensor_entity_id],
                self._supply_temperature_changed,
            )
        )
        await self.refresh_state()

    @overrides
    def stop_listening(self):
        """Stop listening and cancel pending delayed checks."""
        self._cancel_pending_call()
        super().stop_listening()

    @overrides
    async def refresh_state(self, restart_on_clear: bool = True) -> bool:
        """Refresh from the current sensor state."""
        if not self._is_configured:
            return False

        state = self.hass.states.get(self._supply_temp_sensor_entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return await self._apply_state(
                STATE_ON,
                REASON_SENSOR_UNAVAILABLE,
                restart_on_clear=restart_on_clear,
            )

        try:
            supply_temp = float(state.state)
        except (TypeError, ValueError):
            return await self._apply_state(
                STATE_ON,
                REASON_SENSOR_UNAVAILABLE,
                restart_on_clear=restart_on_clear,
            )

        self._current_supply_temperature = supply_temp
        return await self._evaluate_temperature(
            supply_temp,
            allow_delay=False,
            restart_on_clear=restart_on_clear,
        )

    @callback
    async def _supply_temperature_changed(self, event: Event[EventStateChangedData]):
        """Handle supply temperature changes."""
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        write_event_log(
            _LOGGER,
            self._vtherm,
            f"Supply temperature changed from {old_state.state if old_state else None} to {new_state.state if new_state else None}",
        )

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._current_supply_temperature = None
            await self._apply_state(STATE_ON, REASON_SENSOR_UNAVAILABLE)
            return

        try:
            supply_temp = float(new_state.state)
        except (TypeError, ValueError):
            self._current_supply_temperature = None
            await self._apply_state(STATE_ON, REASON_SENSOR_UNAVAILABLE)
            return

        self._current_supply_temperature = supply_temp
        await self._evaluate_temperature(
            supply_temp,
            allow_delay=True,
            restart_on_clear=True,
        )

    async def _evaluate_temperature(
        self,
        supply_temp: float,
        allow_delay: bool,
        restart_on_clear: bool,
    ) -> bool:
        """Evaluate the temperature and apply or schedule a state change."""
        desired_state, reason = self._desired_state(supply_temp)

        if desired_state != STATE_ON:
            self._cancel_pending_call()
            return await self._apply_state(
                STATE_OFF,
                None,
                restart_on_clear=restart_on_clear,
            )

        if self.is_supply_temperature_safety_detected:
            return await self._apply_state(
                STATE_ON,
                reason,
                restart_on_clear=restart_on_clear,
            )

        if allow_delay and self._delay_sec > 0:
            self._schedule_delayed_trip(reason)
            return False

        return await self._apply_state(
            STATE_ON,
            reason,
            restart_on_clear=restart_on_clear,
        )

    def _desired_state(self, supply_temp: float) -> tuple[str, str | None]:
        """Return desired safety state and reason, with hysteresis."""
        hvac_mode = self._vtherm.vtherm_hvac_mode

        if hvac_mode == VThermHvacMode_OFF:
            return STATE_OFF, None

        if hvac_mode == VThermHvacMode_HEAT and self._heat_max is not None:
            if self._safety_reason == REASON_HEAT_TOO_HOT:
                if supply_temp > self._heat_max - self._tolerance:
                    return STATE_ON, REASON_HEAT_TOO_HOT
            elif supply_temp >= self._heat_max:
                return STATE_ON, REASON_HEAT_TOO_HOT

        if hvac_mode == VThermHvacMode_COOL and self._cool_min is not None:
            if self._safety_reason == REASON_COOL_TOO_COLD:
                if supply_temp < self._cool_min + self._tolerance:
                    return STATE_ON, REASON_COOL_TOO_COLD
            elif supply_temp <= self._cool_min:
                return STATE_ON, REASON_COOL_TOO_COLD

        return STATE_OFF, None

    def _schedule_delayed_trip(self, reason: str | None) -> None:
        """Schedule a delayed trip check if one is not already pending."""
        if self._pending_call_cancel is not None:
            return

        async def try_trip(_):
            self._pending_call_cancel = None
            await self.refresh_state()

        _LOGGER.debug(
            "%s - supply temperature safety condition detected (%s). Waiting %s seconds before tripping.",
            self,
            reason,
            self._delay_sec,
        )
        self._pending_call_cancel = async_call_later(
            self.hass,
            timedelta(seconds=self._delay_sec),
            try_trip,
        )

    def _cancel_pending_call(self) -> None:
        """Cancel a delayed trip check."""
        if self._pending_call_cancel:
            self._pending_call_cancel()
            self._pending_call_cancel = None

    async def _apply_state(
        self,
        new_state: str,
        reason: str | None,
        restart_on_clear: bool = True,
    ) -> bool:
        """Apply the safety state and trigger the necessary device action."""
        old_state = self._safety_state
        old_reason = self._safety_reason

        self._safety_state = new_state
        self._safety_reason = reason if new_state == STATE_ON else None

        changed = old_state != self._safety_state or old_reason != self._safety_reason
        if not changed:
            return False

        if self._safety_state == STATE_ON:
            write_event_log(
                _LOGGER,
                self._vtherm,
                f"Supply temperature safety started ({self._safety_reason})",
            )
            _LOGGER.warning(
                "%s - supply temperature safety started. temp=%s reason=%s",
                self,
                self._current_supply_temperature,
                self._safety_reason,
            )
            await self._vtherm.async_underlying_entity_turn_off()
            self._send_event("start")
        else:
            write_event_log(_LOGGER, self._vtherm, "Supply temperature safety ended")
            _LOGGER.info("%s - supply temperature safety ended", self)
            self._send_event("end")
            if restart_on_clear and self._vtherm.is_ready:
                await self._vtherm.async_control_heating(force=True)

        self._vtherm.update_custom_attributes()
        self._vtherm.async_write_ha_state()
        return True

    def _send_event(self, event_action: str) -> None:
        """Send a VTherm safety event."""
        self._vtherm.send_event(
            EventType.SAFETY_EVENT,
            {
                "type": f"supply_temperature_{event_action}",
                "supply_temperature": self._current_supply_temperature,
                "reason": self._safety_reason,
                "heat_max": self._heat_max,
                "cool_min": self._cool_min,
            },
        )

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add custom state attributes."""
        extra_state_attributes.update(
            {
                "is_supply_temperature_safety_configured": self._is_configured,
            }
        )

        if self._is_configured:
            extra_state_attributes.update(
                {
                    "supply_temperature_safety_manager": {
                        "supply_temperature_safety_state": self._safety_state,
                        "supply_temperature_safety_reason": self._safety_reason,
                        "supply_temperature_sensor_entity_id": self._supply_temp_sensor_entity_id,
                        "supply_temperature": self._current_supply_temperature,
                        "supply_temperature_heat_max": self._heat_max,
                        "supply_temperature_cool_min": self._cool_min,
                        "supply_temperature_tolerance": self._tolerance,
                        "supply_temperature_delay_sec": self._delay_sec,
                    }
                }
            )

    @property
    def is_configured(self) -> bool:
        """Return True when the feature is configured."""
        return self._is_configured

    @property
    def is_supply_temperature_safety_detected(self) -> bool:
        """Return True when the supply-water safety is tripped."""
        return self._safety_state == STATE_ON

    @property
    def is_detected(self) -> bool:
        """Return the detected state."""
        return self.is_supply_temperature_safety_detected

    @property
    def safety_state(self) -> str:
        """Return the raw safety state."""
        return self._safety_state

    @property
    def safety_reason(self) -> str | None:
        """Return the current safety reason."""
        return self._safety_reason

    def __str__(self):
        return f"SupplyTemperatureSafetyManager-{self.name}"
