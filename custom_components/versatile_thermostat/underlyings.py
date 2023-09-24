""" Underlying entities classes """
import logging
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, UnitOfTemperature

from homeassistant.exceptions import ServiceNotFound

from homeassistant.backports.enum import StrEnum
from homeassistant.core import HomeAssistant, DOMAIN as HA_DOMAIN, CALLBACK_TYPE
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    DOMAIN as CLIMATE_DOMAIN,
    HVACMode,
    HVACAction,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_SWING_MODE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_call_later

from .const import UnknownEntity

_LOGGER = logging.getLogger(__name__)

# remove this
# _LOGGER.setLevel(logging.DEBUG)


class UnderlyingEntityType(StrEnum):
    """All underlying device type"""

    # A switch
    SWITCH = "switch"

    # a climate
    CLIMATE = "climate"


class UnderlyingEntity:
    """Represent a underlying device which could be a switch or a climate"""

    _hass: HomeAssistant
    # Cannot import VersatileThermostat due to circular reference
    _thermostat: Any
    _entity_id: str
    _type: UnderlyingEntityType

    def __init__(
        self,
        hass: HomeAssistant,
        thermostat: Any,
        entity_type: UnderlyingEntityType,
        entity_id: str,
    ) -> None:
        """Initialize the underlying entity"""
        self._hass = hass
        self._thermostat = thermostat
        self._type = entity_type
        self._entity_id = entity_id

    def __str__(self):
        return str(self._thermostat) + "-" + self._entity_id

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
        _LOGGER.debug("%s - Stopping underlying entity %s", self, self._entity_id)
        # This may fails if called after shutdown
        try:
            data = {ATTR_ENTITY_ID: self._entity_id}
            await self._hass.services.async_call(
                HA_DOMAIN,
                SERVICE_TURN_OFF,
                data,
            )
        except ServiceNotFound as err:
            _LOGGER.error(err)

    async def turn_on(self):
        """Turn heater toggleable device on."""
        _LOGGER.debug("%s - Starting underlying entity %s", self, self._entity_id)
        try:
            data = {ATTR_ENTITY_ID: self._entity_id}
            await self._hass.services.async_call(
                HA_DOMAIN,
                SERVICE_TURN_ON,
                data,
            )
        except ServiceNotFound as err:
            _LOGGER.error(err)

    async def set_temperature(self, temperature, max_temp, min_temp):
        """Set the target temperature"""
        return

    def remove_entity(self):
        """Remove the underlying entity"""
        return

    # override to be able to mock the call
    def call_later(
        self, hass: HomeAssistant, delay_sec: int, called_method
    ) -> CALLBACK_TYPE:
        """Call the method after a delay"""
        return async_call_later(hass, delay_sec, called_method)


class UnderlyingSwitch(UnderlyingEntity):
    """Represent a underlying switch"""

    _initialDelaySec: int
    _on_time_sec: int
    _off_time_sec: int
    _hvac_mode: HVACMode

    def __init__(
        self,
        hass: HomeAssistant,
        thermostat: Any,
        switch_entity_id: str,
        initial_delay_sec: int,
    ) -> None:
        """Initialize the underlying switch"""

        super().__init__(
            hass=hass,
            thermostat=thermostat,
            entity_type=UnderlyingEntityType.SWITCH,
            entity_id=switch_entity_id,
        )
        self._initial_delay_sec = initial_delay_sec
        self._async_cancel_cycle = None
        self._should_relaunch_control_heating = False
        self._on_time_sec = 0
        self._off_time_sec = 0
        self._hvac_mode = None

    @property
    def initial_delay_sec(self):
        """The initial delay for this class"""
        return self._initial_delay_sec

    async def set_hvac_mode(self, hvac_mode: HVACMode) -> bool:
        """Set the HVACmode. Returns true if something have change"""

        if hvac_mode == HVACMode.OFF:
            if self.is_device_active:
                await self.turn_off()
            self._cancel_cycle()

        if self._hvac_mode != hvac_mode:
            self._hvac_mode = hvac_mode
            return True
        else:
            return False

    @property
    def is_device_active(self):
        """If the toggleable device is currently active."""
        return self._hass.states.is_state(self._entity_id, STATE_ON)

    async def check_initial_state(self, hvac_mode: HVACMode):
        """Prevent the heater to be on but thermostat is off"""
        if hvac_mode == HVACMode.OFF and self.is_device_active:
            _LOGGER.warning(
                "%s - The hvac mode is OFF, but the switch device is ON. Turning off device %s",
                self,
                self._entity_id,
            )
            await self.turn_off()

    async def start_cycle(
        self,
        hvac_mode: HVACMode,
        on_time_sec: int,
        off_time_sec: int,
        force=False,
    ):
        """Starting cycle for switch"""
        _LOGGER.debug(
            "%s - Starting new cycle hvac_mode=%s on_time_sec=%d off_time_sec=%d force=%s",
            self,
            hvac_mode,
            on_time_sec,
            off_time_sec,
            force,
        )

        self._on_time_sec = on_time_sec
        self._off_time_sec = off_time_sec
        self._hvac_mode = hvac_mode

        # Cancel eventual previous cycle if any
        if self._async_cancel_cycle is not None:
            if force:
                _LOGGER.debug("%s - we force a new cycle", self)
                self._cancel_cycle()
            else:
                _LOGGER.debug(
                    "%s - A previous cycle is alredy running and no force -> waits for its end",
                    self,
                )
                # self._should_relaunch_control_heating = True
                _LOGGER.debug("%s - End of cycle (2)", self)
                return

        # If we should heat, starts the cycle with delay
        if self._hvac_mode in [HVACMode.HEAT, HVACMode.COOL] and on_time_sec > 0:
            # Starts the cycle after the initial delay
            self._async_cancel_cycle = self.call_later(
                self._hass, self._initial_delay_sec, self._turn_on_later
            )
            _LOGGER.debug("%s - _async_cancel_cycle=%s", self, self._async_cancel_cycle)

        # if we not heat but device is active
        elif self.is_device_active:
            _LOGGER.info(
                "%s - stop heating (2) for %d min %d sec",
                self,
                off_time_sec // 60,
                off_time_sec % 60,
            )
            await self.turn_off()
        else:
            _LOGGER.debug("%s - nothing to do", self)

    def _cancel_cycle(self):
        """Cancel the cycle"""
        if self._async_cancel_cycle:
            self._async_cancel_cycle()
            self._async_cancel_cycle = None
            _LOGGER.debug("%s - Stopping cycle during calculation", self)

    async def _turn_on_later(self, _):
        """Turn the heater on after a delay"""
        _LOGGER.debug(
            "%s - calling turn_on_later hvac_mode=%s, should_relaunch_later=%s off_time_sec=%d",
            self,
            self._hvac_mode,
            self._should_relaunch_control_heating,
            self._on_time_sec,
        )

        self._cancel_cycle()

        if self._hvac_mode == HVACMode.OFF:
            _LOGGER.debug("%s - End of cycle (HVAC_MODE_OFF - 2)", self)
            if self.is_device_active:
                await self.turn_off()
            return

        if await self._thermostat.check_overpowering():
            _LOGGER.debug("%s - End of cycle (3)", self)
            return
        # Security mode could have change the on_time percent
        await self._thermostat.check_security()
        time = self._on_time_sec

        action_label = "start"
        # if self._should_relaunch_control_heating:
        #    _LOGGER.debug("Don't %s cause a cycle have to be relaunch", action_label)
        #    self._should_relaunch_control_heating = False
        #    # self.hass.create_task(self._async_control_heating())
        #    await self.start_cycle(
        #        self._hvac_mode, self._on_time_sec, self._off_time_sec
        #    )
        #    _LOGGER.debug("%s - End of cycle (3)", self)
        #    return

        if time > 0:
            _LOGGER.info(
                "%s - %s heating for %d min %d sec",
                self,
                action_label,
                time // 60,
                time % 60,
            )
            await self.turn_on()
        else:
            _LOGGER.debug("%s - No action on heater cause duration is 0", self)
        self._async_cancel_cycle = self.call_later(
            self._hass,
            time,
            self._turn_off_later,
        )

    async def _turn_off_later(self, _):
        """Turn the heater off and call the next cycle after the delay"""
        _LOGGER.debug(
            "%s - calling turn_off_later hvac_mode=%s, should_relaunch_later=%s off_time_sec=%d",
            self,
            self._hvac_mode,
            self._should_relaunch_control_heating,
            self._off_time_sec,
        )
        self._cancel_cycle()

        if self._hvac_mode == HVACMode.OFF:
            _LOGGER.debug("%s - End of cycle (HVAC_MODE_OFF - 2)", self)
            if self.is_device_active:
                await self.turn_off()
            return

        action_label = "stop"
        # if self._should_relaunch_control_heating:
        #    _LOGGER.debug("Don't %s cause a cycle have to be relaunch", action_label)
        #    self._should_relaunch_control_heating = False
        #    # self.hass.create_task(self._async_control_heating())
        #    await self.start_cycle(
        #        self._hvac_mode, self._on_time_sec, self._off_time_sec
        #    )
        #    _LOGGER.debug("%s - End of cycle (3)", self)
        #    return

        time = self._off_time_sec

        if time > 0:
            _LOGGER.info(
                "%s - %s heating for %d min %d sec",
                self,
                action_label,
                time // 60,
                time % 60,
            )
            await self.turn_off()
        else:
            _LOGGER.debug("%s - No action on heater cause duration is 0", self)
        self._async_cancel_cycle = self.call_later(
            self._hass,
            time,
            self._turn_on_later,
        )

        # increment energy at the end of the cycle
        self._thermostat.incremente_energy()

    def remove_entity(self):
        """Remove the entity after stopping its cycle"""
        self._cancel_cycle()


class UnderlyingClimate(UnderlyingEntity):
    """Represent a underlying climate"""

    _underlying_climate: ClimateEntity

    def __init__(
        self,
        hass: HomeAssistant,
        thermostat: Any,
        climate_entity_id: str,
    ) -> None:
        """Initialize the underlying climate"""

        super().__init__(
            hass=hass,
            thermostat=thermostat,
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

    async def set_hvac_mode(self, hvac_mode: HVACMode) -> bool:
        """Set the HVACmode of the underlying climate. Returns true if something have change"""
        if not self.is_initialized:
            return False

        data = {ATTR_ENTITY_ID: self._entity_id, "hvac_mode": hvac_mode}
        await self._hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            data,
        )

        return True

    @property
    def is_device_active(self):
        """If the toggleable device is currently active."""
        if self.is_initialized:
            return self._underlying_climate.hvac_mode != HVACMode.OFF and self._underlying_climate.hvac_action not in [
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
            data,
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
            data,
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
            data,
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
            data,
        )

    @property
    def hvac_action(self) -> HVACAction | None:
        """Get the hvac action of the underlying"""
        if not self.is_initialized:
            return None
        return self._underlying_climate.hvac_action

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Get the hvac mode of the underlying"""
        if not self.is_initialized:
            return None
        return self._underlying_climate.hvac_mode

    @property
    def fan_mode(self) -> str | None:
        """Get the fan_mode of the underlying"""
        if not self.is_initialized:
            return None
        return self._underlying_climate.fan_mode

    @property
    def swing_mode(self) -> str | None:
        """Get the swing_mode of the underlying"""
        if not self.is_initialized:
            return None
        return self._underlying_climate.swing_mode

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Get the supported features of the climate"""
        if not self.is_initialized:
            return ClimateEntityFeature.TARGET_TEMPERATURE
        return self._underlying_climate.supported_features

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Get the hvac_modes"""
        if not self.is_initialized:
            return []
        return self._underlying_climate.hvac_modes

    @property
    def fan_modes(self) -> list[str]:
        """Get the fan_modes"""
        if not self.is_initialized:
            return []
        return self._underlying_climate.fan_modes

    @property
    def swing_modes(self) -> list[str]:
        """Get the swing_modes"""
        if not self.is_initialized:
            return []
        return self._underlying_climate.swing_modes

    @property
    def temperature_unit(self) -> str:
        """Get the temperature_unit"""
        if not self.is_initialized:
            return UnitOfTemperature.CELSIUS
        return self._underlying_climate.temperature_unit

    @property
    def target_temperature_step(self) -> float:
        """Get the target_temperature_step"""
        if not self.is_initialized:
            return 1
        return self._underlying_climate.target_temperature_step

    @property
    def target_temperature_high(self) -> float:
        """Get the target_temperature_high"""
        if not self.is_initialized:
            return 30
        return self._underlying_climate.target_temperature_high

    @property
    def target_temperature_low(self) -> float:
        """Get the target_temperature_low"""
        if not self.is_initialized:
            return 15
        return self._underlying_climate.target_temperature_low

    @property
    def is_aux_heat(self) -> bool:
        """Get the is_aux_heat"""
        if not self.is_initialized:
            return False
        return self._underlying_climate.is_aux_heat

    def turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        if not self.is_initialized:
            return None
        return self._underlying_climate.turn_aux_heat_on()

    def turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater on."""
        if not self.is_initialized:
            return None
        return self._underlying_climate.turn_aux_heat_off()
