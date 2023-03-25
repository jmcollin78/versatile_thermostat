""" Underlying entities classes """
import logging

from homeassistant.const import ATTR_ENTITY_ID, STATE_ON

from homeassistant.backports.enum import StrEnum
from homeassistant.core import HomeAssistant, DOMAIN as HA_DOMAIN
from homeassistant.components.climate import (
    ClimateEntity,
    DOMAIN as CLIMATE_DOMAIN,
    HVACMode,
    HVACAction,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_SWING_MODE,
    SERVICE_TURN_OFF,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.helpers.entity_component import EntityComponent

from .const import UnknownEntity

_LOGGER = logging.getLogger(__name__)


class UnderlyingEntityType(StrEnum):
    """All underlying device type"""

    # A switch
    SWITCH = "switch"

    # a climate
    CLIMATE = "climate"


class UnderlyingEntity:
    """Represent a underlying device which could be a switch or a climate"""

    _hass: HomeAssistant
    _thermostat_name: str
    _entity_id: str
    _type: UnderlyingEntityType

    def __init__(
        self,
        hass: HomeAssistant,
        thermostat_name: str,
        entity_type: UnderlyingEntityType,
        entity_id: str,
    ) -> None:
        """Initialize the underlying entity"""
        self._hass = hass
        self._thermostat_name = thermostat_name
        self._type = entity_type
        self._entity_id = entity_id

    def __str__(self):
        return self._thermostat_name

    @property
    def entity_id(self):
        """The entiy id represented by this class"""
        return self._entity_id

    @property
    def entity_type(self) -> UnderlyingEntityType:
        """The entity type represented by this class"""
        return self._type

    @property
    def is_initialized(self) -> bool:
        """True if the underlying is initialized"""
        return True

    def startup(self):
        """Startup the Entity"""
        return

    async def set_hvac_mode(self, hvac_mode: HVACMode):
        """Set the HVACmode"""
        return

    @property
    def is_device_active(self) -> bool | None:
        """If the toggleable device is currently active."""
        return None

    async def turn_off(self):
        """Turn heater toggleable device off."""
        _LOGGER.debug("%s - Stopping underlying switch %s", self, self._entity_id)
        data = {ATTR_ENTITY_ID: self._entity_id}
        await self._hass.services.async_call(
            HA_DOMAIN,
            SERVICE_TURN_OFF,
            data,  # TODO needed ? context=self._context
        )

    async def set_temperature(self, temperature, max_temp, min_temp):
        """Set the target temperature"""
        return


class UnderlyingSwitch(UnderlyingEntity):
    """Represent a underlying switch"""

    _initialDelaySec: int

    def __init__(
        self,
        hass: HomeAssistant,
        thermostat_name: str,
        switch_entity_id: str,
        initial_delay_sec: int,
    ) -> None:
        """Initialize the underlying switch"""

        super().__init__(
            hass=hass,
            thermostat_name=thermostat_name,
            entity_type=UnderlyingEntityType.SWITCH,
            entity_id=switch_entity_id,
        )
        self._initial_delay_sec = initial_delay_sec

    @property
    def initial_delay_sec(self):
        """The initial delay for this class"""
        return self._initial_delay_sec

    async def set_hvac_mode(self, hvac_mode: HVACMode):
        """Set the HVACmode"""
        if hvac_mode == HVACMode.OFF:
            if self.is_device_active:
                await self.turn_off()
        return

    @property
    def is_device_active(self):
        """If the toggleable device is currently active."""
        return self._hass.states.is_state(self._entity_id, STATE_ON)


class UnderlyingClimate(UnderlyingEntity):
    """Represent a underlying climate"""

    _underlying_climate: ClimateEntity

    def __init__(
        self, hass: HomeAssistant, thermostat_name: str, climate_entity_id: str
    ) -> None:
        """Initialize the underlying climate"""

        super().__init__(
            hass=hass,
            thermostat_name=thermostat_name,
            entity_type=UnderlyingEntityType.CLIMATE,
            entity_id=climate_entity_id,
        )
        self._underlying_climate = None

    def find_underlying_climate(self) -> ClimateEntity:
        """Find the underlying climate entity"""
        component: EntityComponent[ClimateEntity] = self._hass.data[CLIMATE_DOMAIN]
        for entity in component.entities:
            if self.entity_id == entity.entity_id:
                return entity
        return None

    def startup(self):
        """Startup the Entity"""
        # Get the underlying climate
        self._underlying_climate = self.find_underlying_climate()
        if self._underlying_climate:
            _LOGGER.info(
                "%s - The underlying climate entity: %s have been succesfully found",
                self,
                self._underlying_climate,
            )
        else:
            _LOGGER.error(
                "%s - Cannot find the underlying climate entity: %s. Thermostat will not be operational",
                self,
                self.entity_id,
            )
            # #56 keep the over_climate and try periodically to find the underlying climate
            # self._is_over_climate = False
            raise UnknownEntity(f"Underlying entity {self.entity_id} not found")
        return

    @property
    def is_initialized(self) -> bool:
        """True if the underlying climate was found"""
        return self._underlying_climate is not None

    async def set_hvac_mode(self, hvac_mode: HVACMode):
        """Set the HVACmode of the underlying climate"""
        if not self.is_initialized:
            return

        data = {ATTR_ENTITY_ID: self._entity_id, "hvac_mode": hvac_mode}
        await self._hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            data,  # TODO Needed ?, context=self._context
        )

    @property
    def is_device_active(self):
        """If the toggleable device is currently active."""
        if self.is_initialized:
            return self._underlying_climate.hvac_action not in [
                HVACAction.IDLE,
                HVACAction.OFF,
            ]
        else:
            return None

    async def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if not self.is_initialized:
            return
        data = {
            ATTR_ENTITY_ID: self._entity_id,
            "fan_mode": fan_mode,
        }

        await self._hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            data,  # TODO needed ? context=self._context
        )

    async def set_humidity(self, humidity: int):
        """Set new target humidity."""
        _LOGGER.info("%s - Set fan mode: %s", self, humidity)
        if not self.is_initialized:
            return
        data = {
            ATTR_ENTITY_ID: self._entity_id,
            "humidity": humidity,
        }

        await self._hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HUMIDITY,
            data,  # TODO needed ? context=self._context
        )

    async def set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        _LOGGER.info("%s - Set fan mode: %s", self, swing_mode)
        if not self.is_initialized:
            return
        data = {
            ATTR_ENTITY_ID: self._entity_id,
            "swing_mode": swing_mode,
        }

        await self._hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_SWING_MODE,
            data,  # TODO needed ? context=self._context
        )

    async def set_temperature(self, temperature, max_temp, min_temp):
        """Set the target temperature"""
        if not self.is_initialized:
            return
        data = {
            ATTR_ENTITY_ID: self._entity_id,
            "temperature": temperature,
            "target_temp_high": max_temp,
            "target_temp_low": min_temp,
        }

        await self._hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            data,  # TODO needed ? context=self._context
        )

    @property
    def hvac_action(self) -> HVACAction:
        """Get the hvac action of the underlying"""
        if not self.is_initialized:
            return None
        return self._underlying_climate.hvac_action
