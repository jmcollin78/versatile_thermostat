# pylint: disable=unused-argument, line-too-long

""" Underlying entities classes """
import logging
from typing import Any
from enum import StrEnum

from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, UnitOfTemperature
from homeassistant.core import State

from homeassistant.exceptions import ServiceNotFound

from homeassistant.core import HomeAssistant, CALLBACK_TYPE
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

from homeassistant.components.number import SERVICE_SET_VALUE

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_call_later

from .const import UnknownEntity, overrides
from .keep_alive import IntervalCaller

_LOGGER = logging.getLogger(__name__)

# remove this
# _LOGGER.setLevel(logging.DEBUG)


class UnderlyingEntityType(StrEnum):
    """All underlying device type"""

    # A switch
    SWITCH = "switch"

    # a climate
    CLIMATE = "climate"

    # a valve
    VALVE = "valve"


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

    async def set_temperature(self, temperature, max_temp, min_temp):
        """Set the target temperature"""
        return

    # This should be the correct way to handle turn_off and turn_on but this breaks the unit test
    # will an not understandable error: TypeError: object MagicMock can't be used in 'await' expression
    async def turn_off(self):
        """Turn off the underlying equipement.
        Need to be overriden"""
        return NotImplementedError

    async def turn_on(self):
        """Turn off the underlying equipement.
        Need to be overriden"""
        return NotImplementedError

    @property
    def is_inversed(self):
        """Tells if the switch command should be inversed"""
        return False

    def remove_entity(self):
        """Remove the underlying entity"""
        return

    async def check_initial_state(self, hvac_mode: HVACMode):
        """Prevent the underlying to be on but thermostat is off"""
        if hvac_mode == HVACMode.OFF and self.is_device_active:
            _LOGGER.info(
                "%s - The hvac mode is OFF, but the underlying device is ON. Turning off device %s",
                self,
                self._entity_id,
            )
            await self.set_hvac_mode(hvac_mode)
        elif hvac_mode != HVACMode.OFF and not self.is_device_active:
            _LOGGER.info(
                "%s - The hvac mode is %s, but the underlying device is not ON. Turning on device %s if needed",
                self,
                hvac_mode,
                self._entity_id,
            )
            await self.set_hvac_mode(hvac_mode)

    # override to be able to mock the call
    def call_later(
        self, hass: HomeAssistant, delay_sec: int, called_method
    ) -> CALLBACK_TYPE:
        """Call the method after a delay"""
        return async_call_later(hass, delay_sec, called_method)

    async def start_cycle(
        self,
        hvac_mode: HVACMode,
        on_time_sec: int,
        off_time_sec: int,
        on_percent: int,
        force=False,
    ):
        """Starting cycle for switch"""

    def _cancel_cycle(self):
        """Stops an eventual cycle"""

    def cap_sent_value(self, value) -> float:
        """capping of the value send to the underlying eqt"""
        return value


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
        keep_alive_sec: int,
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
        self._keep_alive = IntervalCaller(hass, keep_alive_sec)

    @property
    def initial_delay_sec(self):
        """The initial delay for this class"""
        return self._initial_delay_sec

    @overrides
    @property
    def is_inversed(self):
        """Tells if the switch command should be inversed"""
        return self._thermostat.is_inversed

    @overrides
    def startup(self):
        super().startup()
        self._keep_alive.set_async_action(
            self.turn_on if self.is_device_active else self.turn_off
        )

    # @overrides this breaks some unit tests TypeError: object MagicMock can't be used in 'await' expression
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
        real_state = self._hass.states.is_state(self._entity_id, STATE_ON)
        return (self.is_inversed and not real_state) or (
            not self.is_inversed and real_state
        )

    # @overrides this breaks some unit tests TypeError: object MagicMock can't be used in 'await' expression
    async def turn_off(self):
        """Turn heater toggleable device off."""
        _LOGGER.debug("%s - Stopping underlying entity %s", self, self._entity_id)
        command = SERVICE_TURN_OFF if not self.is_inversed else SERVICE_TURN_ON
        domain = self._entity_id.split(".")[0]
        # This may fails if called after shutdown
        try:
            try:
                data = {ATTR_ENTITY_ID: self._entity_id}
                await self._hass.services.async_call(domain, command, data)
                self._keep_alive.set_async_action(self.turn_off)
            except Exception:
                self._keep_alive.cancel()
                raise
        except ServiceNotFound as err:
            _LOGGER.error(err)

    async def turn_on(self):
        """Turn heater toggleable device on."""
        _LOGGER.debug("%s - Starting underlying entity %s", self, self._entity_id)
        command = SERVICE_TURN_ON if not self.is_inversed else SERVICE_TURN_OFF
        domain = self._entity_id.split(".")[0]
        try:
            try:
                data = {ATTR_ENTITY_ID: self._entity_id}
                await self._hass.services.async_call(domain, command, data)
                self._keep_alive.set_async_action(self.turn_on)
            except Exception:
                self._keep_alive.cancel()
                raise
        except ServiceNotFound as err:
            _LOGGER.error(err)

    @overrides
    async def start_cycle(
        self,
        hvac_mode: HVACMode,
        on_time_sec: int,
        off_time_sec: int,
        on_percent: int,
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

    @overrides
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
        # safety mode could have change the on_time percent
        await self._thermostat.check_safety()
        time = self._on_time_sec

        action_label = "start"

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

    @overrides
    def remove_entity(self):
        """Remove the entity after stopping its cycle"""
        self._cancel_cycle()
        self._keep_alive.cancel()


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

        if self._underlying_climate.hvac_mode == hvac_mode:
            _LOGGER.debug(
                "%s - hvac_mode is already is requested state %s. Do not send any command",
                self,
                self._underlying_climate.hvac_mode,
            )
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
            return (
                self._underlying_climate.hvac_mode != HVACMode.OFF
                and self._underlying_climate.hvac_action
                not in [
                    HVACAction.IDLE,
                    HVACAction.OFF,
                ]
            )
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
            "temperature": self.cap_sent_value(temperature),
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

    @property
    def underlying_current_temperature(self) -> float | None:
        """Get the underlying current_temperature if it exists
        and if initialized"""
        if not self.is_initialized:
            return None

        if not hasattr(self._underlying_climate, "current_temperature"):
            return None

        return self._underlying_climate.current_temperature

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

    @overrides
    def cap_sent_value(self, value) -> float:
        """Try to adapt the target temp value to the min_temp / max_temp found
        in the underlying entity (if any)"""

        if not self.is_initialized:
            return value

        # Gets the min_temp and max_temp
        if (
            self._underlying_climate.min_temp is not None
            and self._underlying_climate is not None
        ):
            min_val = self._underlying_climate.min_temp
            max_val = self._underlying_climate.max_temp

            new_value = max(min_val, min(value, max_val))
        else:
            _LOGGER.debug("%s - no min and max attributes on underlying", self)
            new_value = value

        if new_value != value:
            _LOGGER.info(
                "%s - Target temp have been updated due min, max of the underlying entity. new_value=%.0f value=%.0f min=%.0f max=%.0f",
                self,
                new_value,
                value,
                min_val,
                max_val,
            )

        return new_value


class UnderlyingValve(UnderlyingEntity):
    """Represent a underlying switch"""

    _hvac_mode: HVACMode
    # This is the percentage of opening int integer (from 0 to 100)
    _percent_open: int

    def __init__(
        self, hass: HomeAssistant, thermostat: Any, valve_entity_id: str
    ) -> None:
        """Initialize the underlying switch"""

        super().__init__(
            hass=hass,
            thermostat=thermostat,
            entity_type=UnderlyingEntityType.VALVE,
            entity_id=valve_entity_id,
        )
        self._async_cancel_cycle = None
        self._should_relaunch_control_heating = False
        self._hvac_mode = None
        self._percent_open = self._thermostat.valve_open_percent
        self._valve_entity_id = valve_entity_id

    async def send_percent_open(self):
        """Send the percent open to the underlying valve"""
        # This may fails if called after shutdown
        try:
            data = {ATTR_ENTITY_ID: self._entity_id, "value": self._percent_open}
            domain = self._entity_id.split(".")[0]
            await self._hass.services.async_call(
                domain,
                SERVICE_SET_VALUE,
                data,
            )
        except ServiceNotFound as err:
            _LOGGER.error(err)

    async def turn_off(self):
        """Turn heater toggleable device off."""
        _LOGGER.debug("%s - Stopping underlying valve entity %s", self, self._entity_id)
        # Issue 341
        is_active = self.is_device_active
        self._percent_open = self.cap_sent_value(0)
        if is_active:
            await self.send_percent_open()

    async def turn_on(self):
        """Nothing to do for Valve because it cannot be turned on"""
        self.set_valve_open_percent()

    async def set_hvac_mode(self, hvac_mode: HVACMode) -> bool:
        """Set the HVACmode. Returns true if something have change"""

        if hvac_mode == HVACMode.OFF and self.is_device_active:
            await self.turn_off()

        if hvac_mode != HVACMode.OFF and not self.is_device_active:
            await self.turn_on()

        if self._hvac_mode != hvac_mode:
            self._hvac_mode = hvac_mode
            return True
        else:
            return False

    @property
    def is_device_active(self):
        """If the toggleable device is currently active."""
        try:
            return self._percent_open > 0
            # To test if real device is open but this is causing some side effect
            # because the activation can be deferred -
            # or float(self._hass.states.get(self._entity_id).state) > 0
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    @overrides
    async def start_cycle(
        self,
        hvac_mode: HVACMode,
        _1,
        _2,
        _3,
        force=False,
    ):
        """We use this function to change the on_percent"""
        if force:
            self._percent_open = self.cap_sent_value(self._percent_open)
            await self.send_percent_open()

    @overrides
    def cap_sent_value(self, value) -> float:
        """Try to adapt the open_percent value to the min / max found
        in the underlying entity (if any)"""

        # Gets the last number state
        valve_state: State = self._hass.states.get(self._valve_entity_id)
        if valve_state is None:
            return value

        if "min" in valve_state.attributes and "max" in valve_state.attributes:
            min_val = valve_state.attributes["min"]
            max_val = valve_state.attributes["max"]

            new_value = round(max(min_val, min(value, max_val)))
        else:
            _LOGGER.debug("%s - no min and max attributes on underlying", self)
            new_value = value

        if new_value != value:
            _LOGGER.info(
                "%s - Valve open percent have been updated due min, max of the underlying entity. new_value=%.0f value=%.0f min=%.0f max=%.0f",
                self,
                new_value,
                value,
                min_val,
                max_val,
            )

        return new_value

    def set_valve_open_percent(self):
        """Update the valve open percent"""
        caped_val = self.cap_sent_value(self._thermostat.valve_open_percent)
        if self._percent_open == caped_val:
            # No changes
            return

        self._percent_open = caped_val
        # Send the new command to valve via a service call

        _LOGGER.info(
            "%s - Setting valve ouverture percent to %s", self, self._percent_open
        )
        # Send the change to the valve, in background
        self._hass.create_task(self.send_percent_open())

    def remove_entity(self):
        """Remove the entity after stopping its cycle"""
        self._cancel_cycle()
