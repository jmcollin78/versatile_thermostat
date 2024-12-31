""" Implements the Power Feature Manager """

# pylint: disable=line-too-long

import logging
from typing import Any

from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)


from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    EventStateChangedData,
)
from homeassistant.components.climate import HVACMode

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import ConfigData

from .base_manager import BaseFeatureManager

_LOGGER = logging.getLogger(__name__)


class FeaturePowerManager(BaseFeatureManager):
    """The implementation of the Power feature"""

    unrecorded_attributes = frozenset(
        {
            "power_sensor_entity_id",
            "max_power_sensor_entity_id",
            "is_power_configured",
            "device_power",
            "power_temp",
            "current_power",
            "current_max_power",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)
        self._power_sensor_entity_id = None
        self._max_power_sensor_entity_id = None
        self._current_power = None
        self._current_max_power = None
        self._power_temp = None
        self._overpowering_state = STATE_UNAVAILABLE
        self._is_configured: bool = False
        self._device_power: float = 0

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""

        # Power management
        self._power_sensor_entity_id = entry_infos.get(CONF_POWER_SENSOR)
        self._max_power_sensor_entity_id = entry_infos.get(CONF_MAX_POWER_SENSOR)
        self._power_temp = entry_infos.get(CONF_PRESET_POWER)

        self._device_power = entry_infos.get(CONF_DEVICE_POWER) or 0
        self._is_configured = False
        self._current_power = None
        self._current_max_power = None
        if (
            entry_infos.get(CONF_USE_POWER_FEATURE, False)
            and self._max_power_sensor_entity_id
            and self._power_sensor_entity_id
            and self._device_power
        ):
            self._is_configured = True
            self._overpowering_state = STATE_UNKNOWN
        else:
            _LOGGER.info("%s - Power management is not fully configured", self)

    @overrides
    def start_listening(self):
        """Start listening the underlying entity"""
        if self._is_configured:
            self.stop_listening()
        else:
            return

        self.add_listener(
            async_track_state_change_event(
                self.hass,
                [self._power_sensor_entity_id],
                self._async_power_sensor_changed,
            )
        )

        self.add_listener(
            async_track_state_change_event(
                self.hass,
                [self._max_power_sensor_entity_id],
                self._async_max_power_sensor_changed,
            )
        )

    @overrides
    async def refresh_state(self) -> bool:
        """Tries to get the last state from sensor
        Returns True if a change has been made"""
        ret = False
        if self._is_configured:
            # try to acquire current power and power max
            current_power_state = self.hass.states.get(self._power_sensor_entity_id)
            if current_power_state and current_power_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                self._current_power = float(current_power_state.state)
                _LOGGER.debug(
                    "%s - Current power have been retrieved: %.3f",
                    self,
                    self._current_power,
                )
                ret = True

            # Try to acquire power max
            current_power_max_state = self.hass.states.get(
                self._max_power_sensor_entity_id
            )
            if current_power_max_state and current_power_max_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                self._current_max_power = float(current_power_max_state.state)
                _LOGGER.debug(
                    "%s - Current power max have been retrieved: %.3f",
                    self,
                    self._current_max_power,
                )
                ret = True

        return ret

    @callback
    async def _async_power_sensor_changed(self, event: Event[EventStateChangedData]):
        """Handle power changes."""
        _LOGGER.debug("Thermostat %s - Receive new Power event", self)
        _LOGGER.debug(event)
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if (
            new_state is None
            or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
            or (old_state is not None and new_state.state == old_state.state)
        ):
            return

        try:
            current_power = float(new_state.state)
            if math.isnan(current_power) or math.isinf(current_power):
                raise ValueError(f"Sensor has illegal state {new_state.state}")
            self._current_power = current_power

            if self._vtherm.preset_mode == PRESET_POWER:
                await self._vtherm.async_control_heating()

        except ValueError as ex:
            _LOGGER.error("Unable to update current_power from sensor: %s", ex)

    @callback
    async def _async_max_power_sensor_changed(
        self, event: Event[EventStateChangedData]
    ):
        """Handle power max changes."""
        _LOGGER.debug("Thermostat %s - Receive new Power Max event", self.name)
        _LOGGER.debug(event)
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if (
            new_state is None
            or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
            or (old_state is not None and new_state.state == old_state.state)
        ):
            return

        try:
            current_power_max = float(new_state.state)
            if math.isnan(current_power_max) or math.isinf(current_power_max):
                raise ValueError(f"Sensor has illegal state {new_state.state}")
            self._current_max_power = current_power_max
            if self._vtherm.preset_mode == PRESET_POWER:
                await self._vtherm.async_control_heating()

        except ValueError as ex:
            _LOGGER.error("Unable to update current_power from sensor: %s", ex)

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update(
            {
                "power_sensor_entity_id": self._power_sensor_entity_id,
                "max_power_sensor_entity_id": self._max_power_sensor_entity_id,
                "overpowering_state": self._overpowering_state,
                "is_power_configured": self._is_configured,
                "device_power": self._device_power,
                "power_temp": self._power_temp,
                "current_power": self._current_power,
                "current_max_power": self._current_max_power,
                "mean_cycle_power": self.mean_cycle_power,
            }
        )

    async def check_overpowering(self) -> bool:
        """Check the overpowering condition
        Turn the preset_mode of the heater to 'power' if power conditions are exceeded
        Returns True if overpowering is 'on'
        """

        if not self._is_configured:
            return False

        if (
            self._current_power is None
            or self._device_power is None
            or self._current_max_power is None
        ):
            _LOGGER.warning(
                "%s - power not valued. check_overpowering not available", self
            )
            return False

        _LOGGER.debug(
            "%s - overpowering check: power=%.3f, max_power=%.3f heater power=%.3f",
            self,
            self._current_power,
            self._current_max_power,
            self._device_power,
        )

        # issue 407 - power_consumption_max is power we need to add. If already active we don't need to add more power
        if self._vtherm.is_device_active:
            power_consumption_max = 0
        else:
            if self._vtherm.is_over_climate:
                power_consumption_max = self._device_power
            else:
                power_consumption_max = max(
                    self._device_power / self._vtherm.nb_underlying_entities,
                    self._device_power * self._vtherm.proportional_algorithm.on_percent,
                )

        ret = (self._current_power + power_consumption_max) >= self._current_max_power
        if (
            self._overpowering_state == STATE_OFF
            and ret
            and self._vtherm.hvac_mode != HVACMode.OFF
        ):
            _LOGGER.warning(
                "%s - overpowering is detected. Heater preset will be set to 'power'",
                self,
            )
            if self._vtherm.is_over_climate:
                self._vtherm.save_hvac_mode()
            self._vtherm.save_preset_mode()
            await self._vtherm.async_underlying_entity_turn_off()
            await self._vtherm.async_set_preset_mode_internal(PRESET_POWER)
            self._vtherm.send_event(
                EventType.POWER_EVENT,
                {
                    "type": "start",
                    "current_power": self._current_power,
                    "device_power": self._device_power,
                    "current_max_power": self._current_max_power,
                    "current_power_consumption": power_consumption_max,
                },
            )

        # Check if we need to remove the POWER preset
        if (
            self._overpowering_state == STATE_ON
            and not ret
            and self._vtherm.preset_mode == PRESET_POWER
        ):
            _LOGGER.warning(
                "%s - end of overpowering is detected. Heater preset will be restored to '%s'",
                self,
                self._vtherm._saved_preset_mode,  # pylint: disable=protected-access
            )
            if self._vtherm.is_over_climate:
                await self._vtherm.restore_hvac_mode(False)
            await self._vtherm.restore_preset_mode()
            self._vtherm.send_event(
                EventType.POWER_EVENT,
                {
                    "type": "end",
                    "current_power": self._current_power,
                    "device_power": self._device_power,
                    "current_max_power": self._current_max_power,
                },
            )

        new_overpowering_state = STATE_ON if ret else STATE_OFF
        if self._overpowering_state != new_overpowering_state:
            self._overpowering_state = new_overpowering_state
            self._vtherm.update_custom_attributes()

        return self._overpowering_state == STATE_ON

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True of the presence is configured"""
        return self._is_configured

    @property
    def overpowering_state(self) -> str | None:
        """Return the current overpowering state STATE_ON or STATE_OFF
        or STATE_UNAVAILABLE if not configured"""
        if not self._is_configured:
            return STATE_UNAVAILABLE
        return self._overpowering_state

    @property
    def max_power_sensor_entity_id(self) -> bool:
        """Return the power max entity id"""
        return self._max_power_sensor_entity_id

    @property
    def power_sensor_entity_id(self) -> bool:
        """Return the power entity id"""
        return self._power_sensor_entity_id

    @property
    def power_temperature(self) -> bool:
        """Return the power temperature"""
        return self._power_temp

    @property
    def device_power(self) -> bool:
        """Return the device power"""
        return self._device_power

    @property
    def current_power(self) -> bool:
        """Return the current power from sensor"""
        return self._current_power

    @property
    def current_max_power(self) -> bool:
        """Return the current power from sensor"""
        return self._current_max_power

    @property
    def mean_cycle_power(self) -> float | None:
        """Returns the mean power consumption during the cycle"""
        if not self._device_power or not self._vtherm.proportional_algorithm:
            return None

        return float(
            self._device_power * self._vtherm.proportional_algorithm.on_percent
        )

    def __str__(self):
        return f"PowerManager-{self.name}"
