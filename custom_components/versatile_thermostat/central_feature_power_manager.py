""" Implements a central Power Feature Manager for Versatile Thermostat """

import logging
from typing import Any
from functools import cmp_to_key

from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
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

    def post_init(self, entry_infos: ConfigData):
        """Gets the configuration parameters"""
        central_config = self._vtherm_api.find_central_configuration()
        if not central_config:
            _LOGGER.info(
                "%s - No central configuration is found. Power management will be deactivated.",
                self,
            )
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
            _LOGGER.info(
                "%s - Power management is not fully configured and will be deactivated",
                self,
            )

    def start_listening(self):
        """Start listening the power sensor"""
        if not self._is_configured:
            return

        self.stop_listening()

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

    async def calculate_shedding(self):
        """Do the shedding calculation and set/unset VTherm into overpowering state"""
        if (
            not self.is_configured
            or not self.current_max_power
            or not self.current_power
        ):
            return

        # Find all VTherms
        vtherms_sorted = self.find_all_vtherm_with_power_management_sorted_by_dtemp()
        available_power = self.current_max_power - self.current_power

        total_affected_power = 0
        force_overpowering = False

        for vtherm in vtherms_sorted:
            device_power = vtherm.power_manager.device_power
            if vtherm.is_device_active:
                power_consumption_max = 0
            else:
                if vtherm.is_over_climate:
                    power_consumption_max = device_power
                else:
                    power_consumption_max = max(
                        device_power / vtherm.nb_underlying_entities,
                        device_power * vtherm.proportional_algorithm.on_percent,
                    )

            _LOGGER.debug(
                "%s - vtherm %s power_consumption_max is %s (device_power=%s, overclimate=%s)",
                self,
                vtherm.name,
                power_consumption_max,
                device_power,
                vtherm.is_over_climate,
            )
            if force_overpowering or (
                total_affected_power + power_consumption_max >= available_power
            ):
                _LOGGER.debug(
                    "%s - vtherm %s should be in overpowering state", self, vtherm.name
                )
                if not vtherm.power_manager.is_overpowering_detected:
                    # To force all others vtherms to be in overpowering
                    force_overpowering = True
                    await vtherm.power_manager.set_overpowering(True)
            else:
                total_affected_power += power_consumption_max
                if vtherm.power_manager.is_overpowering_detected:
                    _LOGGER.debug(
                        "%s - vtherm %s should not be in overpowering state",
                        self,
                        vtherm.name,
                    )
                    await vtherm.power_manager.set_overpowering(False)

            _LOGGER.debug(
                "%s - after vtherm %s total_affected_power=%s, available_power=%s",
                self,
                vtherm.name,
                total_affected_power,
                available_power,
            )

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
            if a.current_temperature is not None and a.target_temperature is not None:
                diff_a = a.target_temperature - a.current_temperature
            if b.current_temperature is not None and b.target_temperature is not None:
                diff_b = b.target_temperature - b.current_temperature

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

    def __str__(self):
        return "CentralPowerManager"
