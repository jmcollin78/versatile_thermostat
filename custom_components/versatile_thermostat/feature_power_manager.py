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
)

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons_type import ConfigData

from .base_manager import BaseFeatureManager
from .vtherm_api import VersatileThermostatAPI

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
        self._power_temp = None
        self._overpowering_state = STATE_UNAVAILABLE
        self._is_configured: bool = False
        self._device_power: float = 0
        self._use_power_feature: bool = False

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""

        # Power management
        self._power_temp = entry_infos.get(CONF_PRESET_POWER)

        self._device_power = entry_infos.get(CONF_DEVICE_POWER) or 0
        self._use_power_feature = entry_infos.get(CONF_USE_POWER_FEATURE, False)
        self._is_configured = False

    @overrides
    async def start_listening(self):
        """Start listening the underlying entity. There is nothing to listen"""
        central_power_configuration = (
            VersatileThermostatAPI.get_vtherm_api().central_power_manager.is_configured
        )

        if self._use_power_feature and self._device_power and central_power_configuration:
            self._is_configured = True
            # Try to restore _overpowering_state from previous state
            old_state = await self._vtherm.async_get_last_state()
            self._overpowering_state = (
                STATE_ON if old_state is not None and hasattr(old_state, "attributes") and old_state.attributes.get("overpowering_state") == STATE_ON else STATE_UNKNOWN
            )
        else:
            if self._use_power_feature:
                if not central_power_configuration:
                    _LOGGER.warning(
                        "%s - Power management is not fully configured. You have to configure the central configuration power",
                        self,
                    )
                else:
                    _LOGGER.warning(
                        "%s - Power management is not fully configured. You have to configure the power feature of the VTherm",
                        self,
                    )

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        extra_state_attributes.update(
            {
                "power_sensor_entity_id": vtherm_api.central_power_manager.power_sensor_entity_id,
                "max_power_sensor_entity_id": vtherm_api.central_power_manager.max_power_sensor_entity_id,
                "overpowering_state": self._overpowering_state,
                "is_power_configured": self._is_configured,
                "device_power": self._device_power,
                "power_temp": self._power_temp,
                "current_power": vtherm_api.central_power_manager.current_power,
                "current_max_power": vtherm_api.central_power_manager.current_max_power,
                "mean_cycle_power": self.mean_cycle_power,
            }
        )

    async def check_power_available(self) -> bool:
        """Check if the Vtherm can be started considering overpowering.
        Returns True if no overpowering conditions are found.
        If True the vtherm power is written into the temporay vtherm started
        """

        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        if (
            not self._is_configured
            or not vtherm_api.central_power_manager.is_configured
        ):
            return True

        current_power = vtherm_api.central_power_manager.current_power
        current_max_power = vtherm_api.central_power_manager.current_max_power
        started_vtherm_total_power = vtherm_api.central_power_manager.started_vtherm_total_power
        if (
            current_power is None
            or current_max_power is None
            or self._device_power is None
        ):
            _LOGGER.warning(
                "%s - power not valued. check_power_available not available", self
            )
            return True

        _LOGGER.debug(
            "%s - overpowering check: power=%.3f, max_power=%.3f heater power=%.3f",
            self,
            current_power,
            current_max_power,
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

        ret = (current_power + started_vtherm_total_power + power_consumption_max) < current_max_power
        if not ret:
            _LOGGER.info(
                "%s - there is not enough power available power=%.3f, max_power=%.3f heater power=%.3f",
                self,
                current_power,
                current_max_power,
                self._device_power,
            )
        else:
            # Adds the current_power_max to the started vtherm total power
            vtherm_api.central_power_manager.add_started_vtherm_total_power(power_consumption_max)

        return ret

    async def set_overpowering(self, overpowering: bool, power_consumption_max: float = 0):
        """Force the overpowering state for the VTherm"""

        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        current_power = vtherm_api.central_power_manager.current_power
        current_max_power = vtherm_api.central_power_manager.current_max_power

        if overpowering and not self.is_overpowering_detected:
            _LOGGER.warning(
                "%s - overpowering is detected. Heater preset will be set to 'power'",
                self,
            )

            self._overpowering_state = STATE_ON

            # if self._vtherm.is_over_climate:
            #     self._vtherm.save_hvac_mode()

            # self._vtherm.save_preset_mode()
            await self._vtherm.async_underlying_entity_turn_off()
            # await self._vtherm.async_set_preset_mode_internal(PRESET_POWER, force=True)
            self._vtherm.send_event(
                EventType.POWER_EVENT,
                {
                    "type": "start",
                    "current_power": current_power,
                    "device_power": self._device_power,
                    "current_max_power": current_max_power,
                    "current_power_consumption": power_consumption_max,
                },
            )
        elif not overpowering and self.is_overpowering_detected:
            _LOGGER.warning(
                "%s - end of overpowering is detected. Heater preset will be restored.",
                self,
            )
            self._overpowering_state = STATE_OFF

            # restore state
            # if self._vtherm.is_over_climate:
            #     await self._vtherm.restore_hvac_mode()
            # await self._vtherm.restore_preset_mode()
            # # restart cycle
            # await self._vtherm.async_control_heating(force=True)
            self._vtherm.send_event(
                EventType.POWER_EVENT,
                {
                    "type": "end",
                    "current_power": current_power,
                    "device_power": self._device_power,
                    "current_max_power": current_max_power,
                },
            )
        elif not overpowering and self._overpowering_state != STATE_OFF:
            # just set to not overpowering the state which was not set
            self._overpowering_state = STATE_OFF
        else:
            # Nothing to do (already in the right state)
            return
        # self._vtherm.update_custom_attributes()

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
    def is_overpowering_detected(self) -> str | None:
        """Return True if the Vtherm is in overpowering state"""
        return self._overpowering_state == STATE_ON

    @property
    def power_temperature(self) -> bool:
        """Return the power temperature"""
        return self._power_temp

    @property
    def device_power(self) -> bool:
        """Return the device power"""
        return self._device_power

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
