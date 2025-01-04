""" Implements a central Power Feature Manager for Versatile Thermostat """

import logging
from typing import Any
from functools import cmp_to_key

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    EventStateChangedData,
)
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import (
    ClimateEntity,
    DOMAIN as CLIMATE_DOMAIN,
)


from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import ConfigData
from .base_manager import BaseFeatureManager

# circular dependency
# from .base_thermostat import BaseThermostat

MIN_DTEMP_SECS = 20

_LOGGER = logging.getLogger(__name__)


class CentralFeaturePowerManager(BaseFeatureManager):
    """A central Power feature manager"""

    def __init__(self, hass: HomeAssistant, vtherm_api: Any):
        """Init of a featureManager"""
        super().__init__(None, hass, "centralPowerManager")
        self._hass: HomeAssistant = hass
        self._vtherm_api = vtherm_api  # no type due to circular reference
        self._is_configured: bool = False
        self._power_sensor_entity_id: str = None
        self._max_power_sensor_entity_id: str = None
        self._current_power: float = None
        self._current_max_power: float = None
        self._power_temp: float = None
        self._last_shedding_date = None

    def post_init(self, entry_infos: ConfigData):
        """Gets the configuration parameters"""
        central_config = self._vtherm_api.find_central_configuration()
        if not central_config:
            _LOGGER.info("No central configuration is found. Power management will be deactivated")
            return

        self._power_sensor_entity_id = entry_infos.get(CONF_POWER_SENSOR)
        self._max_power_sensor_entity_id = entry_infos.get(CONF_MAX_POWER_SENSOR)
        self._power_temp = entry_infos.get(CONF_PRESET_POWER)

        self._is_configured = False
        self._current_power = None
        self._current_max_power = None
        if (
            entry_infos.get(CONF_USE_POWER_FEATURE, False)
            and self._max_power_sensor_entity_id
            and self._power_sensor_entity_id
            and self._power_temp
        ):
            self._is_configured = True
        else:
            _LOGGER.info("Power management is not fully configured and will be deactivated")

    def start_listening(self):
        """Start listening the power sensor"""
        if not self._is_configured:
            return

        self.stop_listening()

        self.add_listener(
            async_track_state_change_event(
                self.hass,
                [self._power_sensor_entity_id],
                self._power_sensor_changed,
            )
        )

        self.add_listener(
            async_track_state_change_event(
                self.hass,
                [self._max_power_sensor_entity_id],
                self._max_power_sensor_changed,
            )
        )

    @callback
    async def _power_sensor_changed(self, event: Event[EventStateChangedData]):
        """Handle power changes."""
        _LOGGER.debug("Receive new Power event")
        _LOGGER.debug(event)
        await self.refresh_state()

    @callback
    async def _max_power_sensor_changed(self, event: Event[EventStateChangedData]):
        """Handle power max changes."""
        _LOGGER.debug("Receive new Power Max event")
        _LOGGER.debug(event)
        await self.refresh_state()

    @overrides
    async def refresh_state(self) -> bool:
        """Tries to get the last state from sensor
        Returns True if a change has been made"""
        ret = False
        if self._is_configured:
            # try to acquire current power and power max
            if (
                new_state := get_safe_float(self._hass, self._power_sensor_entity_id)
            ) is not None:
                self._current_power = new_state
                _LOGGER.debug("Current power have been retrieved: %.3f", self._current_power)
                ret = True

            # Try to acquire power max
            if (
                new_state := get_safe_float(
                    self._hass, self._max_power_sensor_entity_id
                )
            ) is not None:
                self._current_max_power = new_state
                _LOGGER.debug("Current power max have been retrieved: %.3f", self._current_max_power)
                ret = True

            # check if we need to re-calculate shedding
            if ret:
                now = self._vtherm_api.now
                dtimestamp = (
                    (now - self._last_shedding_date).seconds
                    if self._last_shedding_date
                    else 999
                )
                if dtimestamp >= MIN_DTEMP_SECS:
                    await self.calculate_shedding()
                    self._last_shedding_date = now

        return ret

    async def calculate_shedding(self):
        """Do the shedding calculation and set/unset VTherm into overpowering state"""
        if not self.is_configured or self.current_max_power is None or self.current_power is None:
            return

        # Find all VTherms
        available_power = self.current_max_power - self.current_power
        vtherms_sorted = self.find_all_vtherm_with_power_management_sorted_by_dtemp()

        # shedding only
        if available_power < 0:
            _LOGGER.debug(
                "The available power is is < 0 (%s). Set overpowering only for list: %s",
                available_power,
                vtherms_sorted,
            )
            # we will set overpowering for the nearest target temp first
            total_power_gain = 0

            for vtherm in vtherms_sorted:
                device_power = vtherm.power_manager.device_power
                if vtherm.is_device_active and not vtherm.power_manager.is_overpowering_detected:
                    total_power_gain += device_power
                    _LOGGER.debug("vtherm %s should be in overpowering state", vtherm.name)
                    await vtherm.power_manager.set_overpowering(True, device_power)

                _LOGGER.debug("after vtherm %s total_power_gain=%s, available_power=%s", vtherm.name, total_power_gain, available_power)
                if total_power_gain >= -available_power:
                    _LOGGER.debug("We have found enough vtherm to set to overpowering")
                    break
        else:
            # vtherms_sorted.reverse()
            _LOGGER.debug("The available power is is > 0 (%s). Do a complete shedding/un-shedding calculation for list: %s", available_power, vtherms_sorted)

            total_affected_power = 0
            force_overpowering = False

            for vtherm in vtherms_sorted:
                device_power = vtherm.power_manager.device_power
                # calculate the power_consumption_max
                if vtherm.is_device_active:
                    power_consumption_max = 0
                else:
                    if vtherm.is_over_climate:
                        power_consumption_max = device_power
                    else:
                        if vtherm.proportional_algorithm.on_percent > 0:
                            power_consumption_max = max(
                                device_power / vtherm.nb_underlying_entities,
                                device_power * vtherm.proportional_algorithm.on_percent,
                            )
                        else:
                            power_consumption_max = 0

                _LOGGER.debug("vtherm %s power_consumption_max is %s (device_power=%s, overclimate=%s)", vtherm.name, power_consumption_max, device_power, vtherm.is_over_climate)
                if force_overpowering or (total_affected_power + power_consumption_max >= available_power):
                    _LOGGER.debug("vtherm %s should be in overpowering state", vtherm.name)
                    if not vtherm.power_manager.is_overpowering_detected:
                        # To force all others vtherms to be in overpowering
                        force_overpowering = True
                        await vtherm.power_manager.set_overpowering(True, power_consumption_max)
                else:
                    total_affected_power += power_consumption_max
                    # Always set to false to init the state
                    _LOGGER.debug("vtherm %s should not be in overpowering state", vtherm.name)
                    await vtherm.power_manager.set_overpowering(False)

                _LOGGER.debug("after vtherm %s total_affected_power=%s, available_power=%s", vtherm.name, total_affected_power, available_power)

    def get_climate_components_entities(self) -> list:
        """Get all VTherms entitites"""
        vtherms = []
        component: EntityComponent[ClimateEntity] = self._hass.data.get(
            CLIMATE_DOMAIN, None
        )
        if component:
            for entity in component.entities:
                # A little hack to test if the climate is a VTherm. Cannot use isinstance
                # due to circular dependency of BaseThermostat
                if (
                    entity.device_info
                    and entity.device_info.get("model", None) == DOMAIN
                ):
                    vtherms.append(entity)
        return vtherms

    def find_all_vtherm_with_power_management_sorted_by_dtemp(
        self,
    ) -> list:
        """Returns all the VTherms with power management activated"""
        entities = self.get_climate_components_entities()
        vtherms = [
            vtherm
            for vtherm in entities
            if vtherm.power_manager.is_configured and vtherm.is_on
        ]

        # sort the result with the min temp difference first. A and B should be BaseThermostat class
        def cmp_temps(a, b) -> int:
            diff_a = float("inf")
            diff_b = float("inf")
            a_target = a.target_temperature if not a.power_manager.is_overpowering_detected else a.saved_target_temp
            b_target = b.target_temperature if not b.power_manager.is_overpowering_detected else b.saved_target_temp
            if a.current_temperature is not None and a_target is not None:
                diff_a = a_target - a.current_temperature
            if b.current_temperature is not None and b_target is not None:
                diff_b = b_target - b.current_temperature

            if diff_a == diff_b:
                return 0
            return 1 if diff_a > diff_b else -1

        vtherms.sort(key=cmp_to_key(cmp_temps))
        return vtherms

    @property
    def is_configured(self) -> bool:
        """True if the FeatureManager is fully configured"""
        return self._is_configured

    @property
    def current_power(self) -> float | None:
        """Return the current power from sensor"""
        return self._current_power

    @property
    def current_max_power(self) -> float | None:
        """Return the current power from sensor"""
        return self._current_max_power

    @property
    def power_temperature(self) -> float | None:
        """Return the power temperature"""
        return self._power_temp

    @property
    def power_sensor_entity_id(self) -> float | None:
        """Return the power sensor entity id"""
        return self._power_sensor_entity_id

    @property
    def max_power_sensor_entity_id(self) -> float | None:
        """Return the max power sensor entity id"""
        return self._max_power_sensor_entity_id

    def __str__(self):
        return "CentralPowerManager"
