# pylint: disable=unused-argument, line-too-long, too-many-lines

""" Underlying entities classes """
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, TypeVar
from collections.abc import Callable
from datetime import datetime, timedelta

from enum import StrEnum

from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, STATE_OFF, STATE_UNAVAILABLE
from homeassistant.core import State

from homeassistant.exceptions import ServiceNotFound

from homeassistant.core import HomeAssistant, CALLBACK_TYPE, Context, ServiceResponse
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    DOMAIN as CLIMATE_DOMAIN,
    HVACAction,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_SWING_HORIZONTAL_MODE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_SET_TEMPERATURE,
)

from homeassistant.components.number import SERVICE_SET_VALUE

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_call_later
from homeassistant.util.unit_conversion import TemperatureConverter

from custom_components.versatile_thermostat.opening_degree_algorithm import OpeningClosingDegreeCalculation

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .vtherm_hvac_mode import VThermHvacMode, to_legacy_ha_hvac_mode
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

    # a direct valve regulation
    VALVE_REGULATION = "valve_regulation"


class UnderlyingEntity:
    """Represent a underlying device which could be a switch or a climate"""

    def __init__(
        self,
        hass: HomeAssistant,
        thermostat: Any,
        entity_type: UnderlyingEntityType,
        entity_id: str,
    ) -> None:
        """Initialize the underlying entity"""
        self._hass: HomeAssistant = hass
        self._thermostat: Any = thermostat
        self._type: UnderlyingEntityType = entity_type
        self._entity_id: str = entity_id
        self._hvac_mode: VThermHvacMode | None = None
        self._on_cycle_start_callbacks: list[Callable] = []
        self._last_command_sent_datetime: datetime = datetime.fromtimestamp(0)

    def register_cycle_callback(self, on_start: Callable):
        """Register a callback for cycle start"""
        self._on_cycle_start_callbacks.append(on_start)

    def __str__(self):
        return str(self._thermostat) + "-" + self._entity_id

    @property
    def entity_id(self):
        """The entity id represented by this class"""
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

    async def set_hvac_mode(self, hvac_mode: VThermHvacMode):
        """Set the HVACmode"""
        self._hvac_mode = hvac_mode
        return

    @property
    def hvac_mode(self) -> VThermHvacMode | None:
        """Return the current hvac_mode"""
        return self._hvac_mode

    @property
    def is_device_active(self) -> bool | None:
        """If the toggleable device is currently active."""
        return None

    @property
    def hvac_action(self) -> HVACAction:
        """Calculate a hvac_action"""
        return HVACAction.HEATING if self.is_device_active is True else HVACAction.OFF

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
        self._on_cycle_start_callbacks.clear()

    async def check_initial_state(self, hvac_mode: VThermHvacMode):
        """Prevent the underlying to be on but thermostat is off"""
        if hvac_mode == VThermHvacMode_OFF and self.is_device_active:
            _LOGGER.info(
                "%s - The hvac mode is OFF, but the underlying device is ON. Turning off device %s",
                self,
                self._entity_id,
            )
            await self.set_hvac_mode(hvac_mode)
        elif hvac_mode != VThermHvacMode_OFF and not self.is_device_active:
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

    async def hass_services_async_call(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        blocking: bool = False,
        context: Context | None = None,
        target: dict[str, Any] | None = None,
        return_response: bool = False,
    ) -> ServiceResponse:
        """Wrapper for HASS service calls"""
        reponse: ServiceResponse = await self._hass.services.async_call(domain, service, service_data, blocking, context, target, return_response)

        self._last_command_sent_datetime = self._thermostat.now
        return reponse

    async def start_cycle(
        self,
        hvac_mode: VThermHvacMode,
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

    async def turn_off_and_cancel_cycle(self):
        """Turn off and cancel eventual running cycle"""
        self._cancel_cycle()
        await self.turn_off()

    async def check_overpowering(self) -> bool:
        """Check that a underlying can be turned on, else
        activate the overpowering state of the VTherm associated.
        Returns True if the check is ok (no overpowering needed)"""
        ret, _ = await self._thermostat.power_manager.check_power_available()
        if not ret:
            _LOGGER.debug("%s - overpowering is detected", self)
            await self._thermostat.power_manager.set_overpowering(True)
            return False

        return True

    async def send_value_to_number(self, number_entity_id: str, value: int):
        """Send a value to a number entity"""
        try:
            data = {"value": value}
            target = {ATTR_ENTITY_ID: number_entity_id}
            domain = number_entity_id.split(".")[0]
            await self.hass_services_async_call(
                domain=domain,
                service=SERVICE_SET_VALUE,
                service_data=data,
                target=target,
            )
        except ServiceNotFound as err:
            _LOGGER.error(err)
            # This could happens in unit test if input_number domain is not yet loaded
            # raise err


class UnderlyingSwitch(UnderlyingEntity):
    """Represent a underlying switch"""

    def __init__(
        self, hass: HomeAssistant, thermostat: Any, switch_entity_id: str, initial_delay_sec: int, keep_alive_sec: float, vswitch_on: str = None, vswitch_off: str = None
    ) -> None:
        """Initialize the underlying switch"""

        super().__init__(
            hass=hass,
            thermostat=thermostat,
            entity_type=UnderlyingEntityType.SWITCH,
            entity_id=switch_entity_id,
        )
        self._initial_delay_sec = initial_delay_sec
        self._action_in_progress_count = 0
        self._async_cancel_cycle = None
        self._should_relaunch_control_heating = False
        self._on_time_sec = 0
        self._off_time_sec = 0
        self._is_removed = False
        self._keep_alive = IntervalCaller(hass, keep_alive_sec)
        self._vswitch_on = vswitch_on.strip() if vswitch_on else None
        self._vswitch_off = vswitch_off.strip() if vswitch_off else None
        self._domain = self._entity_id.split(".")[0]
        # build command
        command, data, state_on = self.build_command(use_on=True)
        self._on_command = {"command": command, "data": data, "state": state_on}
        command, data, state_off = self.build_command(use_on=False)
        self._off_command = {"command": command, "data": data, "state": state_off}

    @property
    def initial_delay_sec(self):
        """The initial delay for this class"""
        return self._initial_delay_sec

    @overrides
    @property
    def is_inversed(self) -> bool:
        """Tells if the switch command should be inversed"""
        return self._thermostat.is_inversed

    @property
    def keep_alive_sec(self) -> float:
        """Return the switch keep-alive interval in seconds."""
        return self._keep_alive.interval_sec

    @overrides
    def startup(self):
        super().startup()
        self._keep_alive.set_async_action(self._keep_alive_callback)

    # @overrides this breaks some unit tests TypeError: object MagicMock can't be used in 'await' expression
    async def set_hvac_mode(self, hvac_mode: VThermHvacMode) -> bool:
        """Set the HVACmode. Returns true if something have change"""

        if hvac_mode == VThermHvacMode_OFF:
            if self.is_device_active:
                await self.turn_off()
            self._cancel_cycle()

        if self.hvac_mode != hvac_mode:
            await super().set_hvac_mode(hvac_mode)
            return True
        else:
            return False

    @property
    def is_device_active(self):
        """If the toggleable device is currently active."""
        # real_state = self._hass.states.is_state(self._entity_id, STATE_ON)
        # return (self.is_inversed and not real_state) or (
        #    not self.is_inversed and real_state
        # )
        is_on = self._hass.states.is_state(self._entity_id, self._on_command.get("state"))
        # if self.is_inversed:
        #     return not is_on

        return is_on

    async def _keep_alive_callback(self):
        """Keep alive: Turn on if already turned on, turn off if already turned off."""
        timer = self._keep_alive.backoff_timer
        state: State | None = self._hass.states.get(self._entity_id)
        # Normal, expected state.state values are "on" and "off". An absent
        # underlying MQTT switch was observed to produce either state == None
        # or state.state == STATE_UNAVAILABLE ("unavailable").
        if state is None or state.state == STATE_UNAVAILABLE:
            if timer.is_ready():
                _LOGGER.warning(
                    "Entity %s is not available (state: %s). Will keep trying "
                    "keep alive calls, but won't log this condition every time.",
                    self._entity_id,
                    state.state if state else "None",
                )
        else:
            if timer.in_progress:
                timer.reset()
                _LOGGER.warning(
                    "Entity %s has recovered (state: %s).",
                    self._entity_id,
                    state.state,
                )
            await (self.turn_on() if self.is_device_active else self.turn_off())

    def build_command(self, use_on: bool) -> Tuple[str, Dict[str, str]]:
        """Build a command and returns a command and a dict as data"""

        value = None
        data = {ATTR_ENTITY_ID: self._entity_id}
        take_on = (use_on and not self.is_inversed) or (not use_on and self.is_inversed)
        vswitch = self._vswitch_on if take_on else self._vswitch_off
        if vswitch:
            pattern = r"^(?P<command>[^\s/]+)(?:/(?P<argument>[^\s:]+)(?::(?P<value>[^\s]+))?)?$"
            match = re.match(pattern, vswitch)

            if match:
                # Extraire les groupes nommés
                command = match.group("command")
                argument = match.group("argument")
                value = match.group("value")
                if argument is not None and value is not None:
                    data.update({argument: value})
            else:
                raise ValueError(f"Invalid input format: {vswitch}. Must be conform to 'command[/argument[:value]]'")

        else:
            command = SERVICE_TURN_ON if take_on else SERVICE_TURN_OFF

        if value is None:
            value = STATE_ON if take_on else STATE_OFF

        return command, data, value

    async def turn_off(self):
        """Turn heater toggleable device off."""
        self._keep_alive.cancel()  # Cancel early to avoid a turn_on/turn_off race condition
        _LOGGER.debug("%s - Stopping underlying entity %s", self, self._entity_id)

        command = self._off_command.get("command")
        data = self._off_command.get("data")

        # This may fails if called after shutdown
        try:
            try:
                self._thermostat.power_manager.sub_power_consumption_to_central_power_manager()
                _LOGGER.debug("%s - Sending command %s with data=%s", self, command, data)
                await self._hass.services.async_call(self._domain, command, data)
                self._keep_alive.set_async_action(self._keep_alive_callback)
            except Exception:
                self._keep_alive.cancel()
                raise
        except ServiceNotFound as err:
            _LOGGER.error(err)

    async def turn_on(self):
        """Turn heater toggleable device on."""
        self._keep_alive.cancel()  # Cancel early to avoid a turn_on/turn_off race condition
        _LOGGER.debug("%s - Starting underlying entity %s", self, self._entity_id)

        if not await self.check_overpowering():
            self._thermostat.requested_state.force_changed()
            await self._thermostat.update_states(force=True)

            return False

        command = self._on_command.get("command")
        data = self._on_command.get("data")
        try:
            try:
                self._thermostat.power_manager.add_power_consumption_to_central_power_manager()
                _LOGGER.debug("%s - Sending command %s with data=%s", self, command, data)
                await self._hass.services.async_call(self._domain, command, data)
                self._keep_alive.set_async_action(self._keep_alive_callback)
                return True
            except Exception:
                self._keep_alive.cancel()
                raise
        except ServiceNotFound as err:
            _LOGGER.error(err)

    @overrides
    async def start_cycle(
        self,
        hvac_mode: VThermHvacMode,
        on_time_sec: int,
        off_time_sec: int,
        on_percent: int,
        force=False,
    ):
        """Starting cycle for switch"""
        _LOGGER.debug(
            "%s - Starting new cycle hvac_mode=%s on_time_sec=%d off_time_sec=%d force=%s action_in_progress_count=%d",
            self,
            hvac_mode,
            on_time_sec,
            off_time_sec,
            force,
            self._action_in_progress_count
        )

        self._on_time_sec = on_time_sec
        self._off_time_sec = off_time_sec
        self._on_percent = on_percent
        self._hvac_mode = hvac_mode

        # Cancel eventual previous cycle if any
        if self._async_cancel_cycle is not None or self._action_in_progress_count > 0:
            if force:
                _LOGGER.debug("%s - we force a new cycle", self)
                self._cancel_cycle()
            else:
                _LOGGER.debug(
                    "%s - A previous cycle is alredy running and no force -> waits for its end",
                    self,
                )
                self._should_relaunch_control_heating = True
                return

        # If we should heat, starts the cycle with delay
        if self._hvac_mode in [VThermHvacMode_HEAT, VThermHvacMode_COOL] and on_time_sec > 0:
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
            self._action_in_progress_count += 1
            try:
                await self.turn_off()
            finally:
                self._action_in_progress_count -= 1
                if self._should_relaunch_control_heating:
                    _LOGGER.debug("%s - Relaunching control heating", self)
                    self._should_relaunch_control_heating = False
                    await self.start_cycle(
                        self._hvac_mode,
                        self._on_time_sec,
                        self._off_time_sec,
                        self._on_percent,
                        force=True,
                    )
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
        # Guard against race condition during reload
        if self._is_removed:
            _LOGGER.debug("%s - _turn_on_later called after remove_entity, ignoring", self)
            return

        _LOGGER.debug(
            "%s - calling turn_on_later hvac_mode=%s, should_relaunch_later=%s off_time_sec=%d",
            self,
            self._hvac_mode,
            self._should_relaunch_control_heating,
            self._on_time_sec,
        )

        self._cancel_cycle()

        if self._hvac_mode == VThermHvacMode_OFF:
            _LOGGER.debug("%s - End of cycle (HVAC_MODE_OFF - 2)", self)
            if self.is_device_active:
                await self.turn_off()
            return

        # safety mode could have change the on_time percent
        time = self._on_time_sec
        self._action_in_progress_count += 1

        try:
            if self._should_relaunch_control_heating:
                _LOGGER.debug("%s - Skipping turn_on because a relaunch is pending", self)
                return

            action_label = "start"

            if time > 0:
                _LOGGER.info(
                    "%s - %s heating for %d min %d sec",
                    self,
                    action_label,
                    time // 60,
                    time % 60,
                )
                if not await self.turn_on():
                    return
            else:
                _LOGGER.debug("%s - No action on heater cause duration is 0", self)

            # Trigger cycle start callbacks
            # The cycle really starts now (after the initial delay)
            # and will end at the next turn_on_later
            for callback in self._on_cycle_start_callbacks:
                try:
                    await callback(
                        on_time_sec=self._on_time_sec,
                        off_time_sec=self._off_time_sec,
                        on_percent=self._thermostat.safe_on_percent,
                        hvac_mode=self._hvac_mode,
                    )
                except Exception as ex:
                    _LOGGER.warning(
                        "%s - Error calling cycle start callback %s: %s",
                        self,
                        callback,
                        ex,
                    )

            self._async_cancel_cycle = self.call_later(
                self._hass,
                time,
                self._turn_off_later,
            )
        finally:
            self._action_in_progress_count -= 1
            if self._should_relaunch_control_heating:
                _LOGGER.debug("%s - Relaunching control heating", self)
                self._should_relaunch_control_heating = False
                await self.start_cycle(
                    self._hvac_mode,
                    self._on_time_sec,
                    self._off_time_sec,
                    self._on_percent,
                    force=True,
                )

    async def _turn_off_later(self, _):
        """Turn the heater off and call the next cycle after the delay"""
        # Guard against race condition during reload
        if self._is_removed:
            _LOGGER.debug("%s - _turn_off_later called after remove_entity, ignoring", self)
            return

        _LOGGER.debug(
            "%s - calling turn_off_later hvac_mode=%s, should_relaunch_later=%s off_time_sec=%d",
            self,
            self._hvac_mode,
            self._should_relaunch_control_heating,
            self._off_time_sec,
        )
        self._cancel_cycle()

        if self._hvac_mode == VThermHvacMode_OFF:
            _LOGGER.debug("%s - End of cycle (HVAC_MODE_OFF - 2)", self)
            if self.is_device_active:
                await self.turn_off()
            return


        self._action_in_progress_count += 1
        try:
            if self._should_relaunch_control_heating:
                _LOGGER.debug("%s - Skipping turn_off because a relaunch is pending", self)
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
        finally:
            self._action_in_progress_count -= 1
            if self._should_relaunch_control_heating:
                _LOGGER.debug("%s - Relaunching control heating", self)
                self._should_relaunch_control_heating = False
                await self.start_cycle(
                    self._hvac_mode,
                    self._on_time_sec,
                    self._off_time_sec,
                    self._on_percent,
                    force=True,
                )

        # increment energy at the end of the cycle
        self._thermostat.incremente_energy()

    @overrides
    def remove_entity(self):
        """Remove the entity after stopping its cycle"""
        self._is_removed = True
        self._cancel_cycle()
        self._keep_alive.cancel()
        super().remove_entity()


class UnderlyingClimate(UnderlyingEntity):
    """Represent a underlying climate"""

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
        self._underlying_climate: Optional[ClimateEntity] = None
        self._last_sent_temperature: Optional[float] = None
        self._cancel_set_fan_mode_later: Optional[Callable[[], None]] = None
        self._min_sync_entity: float = None
        self._max_sync_entity: float = None
        self._step_sync_entity: float = None

    def find_underlying_climate(self) -> ClimateEntity:
        """Find the underlying climate entity"""
        component: EntityComponent[ClimateEntity] = self._hass.data[CLIMATE_DOMAIN]
        for entity in list(component.entities):
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
            _LOGGER.info(
                "%s - Cannot find the underlying climate entity: %s. Thermostat will not be operational. Will try later.",
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

    async def set_hvac_mode(self, hvac_mode: VThermHvacMode) -> bool:
        """Set the HVACmode of the underlying climate. Returns true if something have change"""
        if not self.is_initialized:
            return False

        if self._underlying_climate.hvac_mode == to_ha_hvac_mode(hvac_mode):
            _LOGGER.debug(
                "%s - hvac_mode is already is requested state %s. Do not send any command",
                self,
                self._underlying_climate.hvac_mode,
            )
            return False

        # When turning on a climate, check that power is available
        if hvac_mode in (VThermHvacMode_HEAT, VThermHvacMode_COOL) and not await self.check_overpowering():
            return False

        data = {ATTR_ENTITY_ID: self._entity_id, "hvac_mode": to_legacy_ha_hvac_mode(hvac_mode)}
        await self.hass_services_async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            data,
        )

        return True

    @property
    def is_device_active(self):
        """If the toggleable device is currently active."""
        if self.is_initialized:
            return self.hvac_mode != VThermHvacMode_OFF and self.hvac_action not in [
                HVACAction.IDLE,
                HVACAction.OFF,
                None,
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

        if self._cancel_set_fan_mode_later:
            self._cancel_set_fan_mode_later()
            self._cancel_set_fan_mode_later = None

        delay: float = 2.0
        if self._thermostat.now > self._last_command_sent_datetime + timedelta(seconds=delay):
            await self.hass_services_async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_FAN_MODE,
                data,
            )

            return

        # Add a delay if last command was sent less than delay seconds ago
        # Some AC units (e.g. Daikin) do not handle multiple consecutive commands well
        _LOGGER.debug(
            "%s - #1458 - Delaying command set_fan_mode for underlying %s by %.2fs",
            self,
            self._entity_id,
            delay,
        )

        async def callback_set_fan_mode(_):
            await self.set_fan_mode(fan_mode)

        self._cancel_set_fan_mode_later = async_call_later(self._hass, delay, callback_set_fan_mode)

    async def set_humidity(self, humidity: int):
        """Set new target humidity."""
        _LOGGER.info("%s - Set humidity: %s", self, humidity)
        if not self.is_initialized:
            return
        data = {
            ATTR_ENTITY_ID: self._entity_id,
            "humidity": humidity,
        }

        await self.hass_services_async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HUMIDITY,
            data,
        )

    async def set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        _LOGGER.info("%s - Set swing mode: %s", self, swing_mode)
        if not self.is_initialized:
            return
        data = {
            ATTR_ENTITY_ID: self._entity_id,
            "swing_mode": swing_mode,
        }

        await self.hass_services_async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_SWING_MODE,
            data,
        )

    async def set_swing_horizontal_mode(self, swing_horizontal_mode):
        """Set new target swing horizontal operation."""
        _LOGGER.info("%s - Set swing horizontal mode: %s", self, swing_horizontal_mode)
        if not self.is_initialized:
            return
        data = {
            ATTR_ENTITY_ID: self._entity_id,
            "swing_horizontal_mode": swing_horizontal_mode,
        }

        await self.hass_services_async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_SWING_HORIZONTAL_MODE,
            data,
        )

    async def set_temperature(self, temperature, max_temp, min_temp):
        """Set the target temperature"""
        if not self.is_initialized:
            return

        # Issue 508 we have to take care of service set_temperature or set_range
        target_temp = self.cap_sent_value(temperature)
        data = {
            ATTR_ENTITY_ID: self._entity_id,
        }

        _LOGGER.info("%s - Set setpoint temperature to: %s", self, target_temp)

        # Issue 807 add TARGET_TEMPERATURE only if in the features
        if ClimateEntityFeature.TARGET_TEMPERATURE_RANGE in self._underlying_climate.supported_features:
            data.update(
                {
                    "target_temp_high": target_temp,
                    "target_temp_low": target_temp,
                }
            )

        if ClimateEntityFeature.TARGET_TEMPERATURE in self._underlying_climate.supported_features:
            data["temperature"] = target_temp

        await self.hass_services_async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            data,
        )

        self._last_sent_temperature = target_temp
        _LOGGER.debug("%s - Last_sent_temperature is now: %s", self, self._last_sent_temperature)

    @property
    def last_sent_temperature(self) -> float | None:
        """Get the last send temperature. None if no temperature have been sent yet"""
        return self._last_sent_temperature

    @property
    def hvac_action(self) -> HVACAction | None:
        """Get the hvac action of the underlying"""
        if not self.is_initialized:
            return None

        hvac_action = self._underlying_climate.hvac_action
        if hvac_action is None:
            target = (
                self.underlying_target_temperature
                or self._thermostat.target_temperature
            )
            current = (
                self.underlying_current_temperature
                or self._thermostat.current_temperature
            )
            hvac_mode = self.hvac_mode

            _LOGGER.debug(
                "%s - hvac_action simulation target=%s, current=%s, hvac_mode=%s",
                self,
                target,
                current,
                hvac_mode,
            )
            hvac_action = HVACAction.IDLE
            if target is not None and current is not None:
                dtemp = target - current

                if hvac_mode == VThermHvacMode_COOL and dtemp < 0:
                    hvac_action = HVACAction.COOLING
                elif hvac_mode in [VThermHvacMode_HEAT, VThermHvacMode_HEAT_COOL] and dtemp > 0:
                    hvac_action = HVACAction.HEATING

        return hvac_action

    @property
    def hvac_mode(self) -> VThermHvacMode | None:
        """Get the hvac mode of the underlying"""
        if not self.is_initialized:
            return None
        return self._underlying_climate.hvac_mode

    @property
    def fan_mode(self) -> str | None:
        """Get the fan_mode of the underlying"""
        if not self.is_initialized or self._underlying_climate.supported_features & ClimateEntityFeature.FAN_MODE == 0:
            return None
        return self._underlying_climate.fan_mode

    @property
    def swing_mode(self) -> str | None:
        """Get the swing_mode of the underlying"""
        if not self.is_initialized or self._underlying_climate.supported_features & ClimateEntityFeature.SWING_MODE == 0:
            return None
        return self._underlying_climate.swing_mode

    @property
    def swing_horizontal_mode(self) -> str | None:
        """Get the swing_horizontal_mode of the underlying"""
        if not self.is_initialized:
            return None
        return self._underlying_climate.swing_horizontal_mode

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Get the supported features of the climate"""
        if not self.is_initialized:
            return ClimateEntityFeature.TARGET_TEMPERATURE
        return self._underlying_climate.supported_features

    @property
    def hvac_modes(self) -> list[VThermHvacMode]:
        """Get the hvac_modes"""
        if not self.is_initialized:
            return []
        return self._underlying_climate.hvac_modes

    @property
    def current_humidity(self) -> float | None:
        """Get the humidity"""
        if not self.is_initialized or self._underlying_climate.current_humidity is None:
            return None
        return self._underlying_climate.current_humidity

    @property
    def fan_modes(self) -> list[str]:
        """Get the fan_modes"""
        if not self.is_initialized or self._underlying_climate.supported_features & ClimateEntityFeature.FAN_MODE == 0:
            return []
        return self._underlying_climate.fan_modes

    @property
    def swing_modes(self) -> list[str]:
        """Get the swing_modes"""
        if not self.is_initialized or self._underlying_climate.supported_features & ClimateEntityFeature.SWING_MODE == 0:
            return []
        return self._underlying_climate.swing_modes

    @property
    def swing_horizontal_modes(self) -> list[str]:
        """Get the swing_horizontal_modes"""
        if not self.is_initialized or self._underlying_climate.supported_features & ClimateEntityFeature.SWING_HORIZONTAL_MODE == 0:
            return []
        return self._underlying_climate.swing_horizontal_modes

    @property
    def temperature_unit(self) -> str:
        """Get the temperature_unit"""
        if not self.is_initialized:
            return self._hass.config.units.temperature_unit
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
    def underlying_target_temperature(self) -> float:
        """Get the target_temperature"""
        if not self.is_initialized:
            return None

        if not hasattr(self._underlying_climate, "target_temperature"):
            return None
        else:
            return self._underlying_climate.target_temperature

        # return self._hass.states.get(self._entity_id).attributes.get(
        #    "target_temperature"
        # )

    @property
    def underlying_current_temperature(self) -> float | None:
        """Get the underlying current_temperature if it exists
        and if initialized"""
        if not self.is_initialized:
            return None

        if not hasattr(self._underlying_climate, "current_temperature"):
            return None
        else:
            return self._underlying_climate.current_temperature

        # return self._hass.states.get(self._entity_id).attributes.get("current_temperature")

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

    @overrides
    def cap_sent_value(self, value) -> float:
        """Try to adapt the target temp value to the min_temp / max_temp found
        in the underlying entity (if any)"""
        min_val = None
        max_val = None

        if not self.is_initialized:
            return value

        # Gets the min_temp and max_temp
        if (
            self._underlying_climate.min_temp is not None
            and self._underlying_climate is not None
        ):
            min_val = TemperatureConverter.convert(
                self._underlying_climate.min_temp, self._underlying_climate.temperature_unit, self._hass.config.units.temperature_unit
            )
            max_val = TemperatureConverter.convert(
                self._underlying_climate.max_temp, self._underlying_climate.temperature_unit, self._hass.config.units.temperature_unit
            )

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

    def set_min_max_step_sync_entity(
        self,
        min_sync_entity: float,
        max_sync_entity: float,
        step_sync_entity: float,
    ):
        """Set the min, max and step for the offset calibration synchronization"""
        self._min_sync_entity = min_sync_entity
        self._max_sync_entity = max_sync_entity
        self._step_sync_entity = step_sync_entity

    @property
    def min_sync_entity(self) -> float:
        """Get the min sync entity"""
        return self._min_sync_entity

    @property
    def max_sync_entity(self) -> float:
        """Get the max sync entity"""
        return self._max_sync_entity

    @property
    def step_sync_entity(self) -> float:
        """Get the step sync entity"""
        return self._step_sync_entity


class UnderlyingValve(UnderlyingEntity):
    """Represent a underlying switch"""

    def __init__(
        self,
        hass: HomeAssistant,
        thermostat: Any,
        valve_entity_id: str,
        entity_type: UnderlyingEntityType = UnderlyingEntityType.VALVE,
    ) -> None:
        """Initialize the underlying valve"""

        super().__init__(
            hass=hass,
            thermostat=thermostat,
            entity_type=UnderlyingEntityType.VALVE,
            entity_id=valve_entity_id,
        )
        self._async_cancel_cycle = None
        self._should_relaunch_control_heating = False
        self._hvac_mode = None
        self._percent_open: int | None = None  # self._thermostat.valve_open_percent
        self._valve_entity_id = valve_entity_id
        self._min_open: float | None = None
        self._max_open: float | None = None

        self._last_sent_temperature = None
        self._last_sent_opening_value: int | None = None

    async def send_percent_open(self, fixed_value: int = None):
        """Send the percent open to the underlying valve"""
        # This may fails if called after shutdown
        value = self._percent_open if fixed_value is None else fixed_value
        await self.send_value_to_number(self._entity_id, value)
        self._last_sent_opening_value = value

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
        await self.set_valve_open_percent()

    async def set_hvac_mode(self, hvac_mode: VThermHvacMode) -> bool:
        """Set the HVACmode. Returns true if something have change"""

        if hvac_mode == VThermHvacMode_OFF and self.is_device_active:
            await self.turn_off()

        if hvac_mode != VThermHvacMode_OFF and not self.is_device_active:
            await self.turn_on()

        if self._hvac_mode != hvac_mode:
            self._hvac_mode = hvac_mode
            return True
        else:
            return False

    def init_min_max_open(self, force=False):
        """Init the min and max open percent value from underlying entity attributes. Returns true if initialized else false"""
        if not force and self._min_open is not None and self._max_open is not None:
            return True

        valve_state: State = self._hass.states.get(self._valve_entity_id)
        if valve_state is None:
            return False

        # Initialize percent_open to current state
        try:
            self._percent_open = self._last_sent_opening_value = float(valve_state.state)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "%s - Cannot initialize percent_open from underlying entity %s state=%s. Maybe normal at startup",
                self,
                self._valve_entity_id,
                valve_state.state,
            )
            return False

        if "min" in valve_state.attributes and "max" in valve_state.attributes:
            self._min_open = valve_state.attributes["min"]
            self._max_open = valve_state.attributes["max"]
        else:
            self._min_open = 0
            self._max_open = 100

        return True

    @property
    def is_device_active(self):
        """If the toggleable device is currently active."""
        try:
            if not self.init_min_max_open():
                return False

            return self._percent_open > (self._min_open or 0) if isinstance(self._percent_open, (int, float)) else False
            # To test if real device is open but this is causing some side effect
            # because the activation can be deferred -
            # or float(self._hass.states.get(self._entity_id).state) > 0
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    @overrides
    async def start_cycle(
        self,
        hvac_mode: VThermHvacMode,
        _1,
        _2,
        _3,
        force=False,
    ):
        """We use this function to change the on_percent"""
        # if force:
        await self.set_valve_open_percent()

    @overrides
    def cap_sent_value(self, value) -> float:
        """Try to adapt the open_percent value to the min / max found
        in the underlying entity (if any)"""
        if not self.init_min_max_open():
            return value

        # Gets the last number state
        new_value = round(max(self._min_open, min(value / 100 * self._max_open, self._max_open)))

        if new_value != value:
            _LOGGER.info(
                "%s - Valve open percent have been updated due min, max of the underlying entity. new_value=%.0f value=%.0f min=%.0f max=%.0f",
                self,
                new_value,
                value,
                self._min_open,
                self._max_open,
            )

        return new_value

    async def set_valve_open_percent(self):
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
        # self._hass.create_task(self.send_percent_open())
        await self.send_percent_open()

    def remove_entity(self):
        """Remove the entity after stopping its cycle"""
        self._cancel_cycle()
        super().remove_entity()

    @property
    def percent_open(self) -> int:
        """The current percent open"""
        return self._percent_open

    @property
    def last_sent_opening_value(self) -> int | None:
        """Return the last sent value to the valve"""
        return self._last_sent_opening_value


class UnderlyingValveRegulation(UnderlyingValve):
    """A specific underlying class for Valve regulation"""

    def __init__(
        self,
        hass: HomeAssistant,
        thermostat: Any,
        opening_degree_entity_id: str,
        closing_degree_entity_id: str,
        climate_underlying: UnderlyingClimate,
        min_opening_degree: int = 0,
        max_opening_degree: int = 100,
        max_closing_degree: int = 100,
        opening_threshold: int = 0,
    ) -> None:
        """Initialize the underlying TRV with valve regulation"""
        super().__init__(
            hass,
            thermostat,
            opening_degree_entity_id,
            entity_type=UnderlyingEntityType.VALVE_REGULATION,
        )
        self._opening_degree_entity_id: str = opening_degree_entity_id
        self._closing_degree_entity_id: str = closing_degree_entity_id
        self._climate_underlying = climate_underlying
        self._is_min_max_initialized: bool = False
        self._max_opening_degree: float = max_opening_degree
        self._min_opening_degree: int = min_opening_degree
        self._max_closing_degree: int = max_closing_degree
        self._opening_threshold: int = opening_threshold

    def initialize_min_max(self):
        """Initialize min and max values for opening and closing degrees"""
        if not self._is_min_max_initialized:
            _LOGGER.debug(
                "%s - initialize min offset_calibration and max open_degree", self
            )
            if not super().init_min_max_open(force=False):
                return False

            max_entity = self._hass.states.get(self._opening_degree_entity_id).attributes.get("max")
            self._max_opening_degree = min(self._max_opening_degree, max_entity if isinstance(max_entity, (int, float)) else 100)

            self._is_min_max_initialized = self._max_opening_degree is not None

            if self._min_opening_degree >= self._max_opening_degree:
                self._min_opening_degree = self._opening_threshold
                raise ValueError(
                    f"min_opening_degree must be less than the max value of the opening degree of the entity {self._opening_degree_entity_id}. Value has been defaulted to opening threshold ({self._opening_threshold})"
                )

        if not self._is_min_max_initialized:
            _LOGGER.warning(
                "%s - impossible to initialize max_opening_degree or min_offset_calibration. Abort sending percent open to the valve. This could be a temporary message at startup."
            )
            return False

        return True

    async def send_percent_open(self, _: float = None):
        """Send the percent open to the underlying valve"""
        if not self.initialize_min_max():
            return

        # Caclulate percent_open
        opening_degree, closing_degree = OpeningClosingDegreeCalculation.calculate_opening_closing_degree(
            brut_valve_open_percent=self._percent_open,
            min_opening_degree=self._min_opening_degree,
            max_closing_degree=self._max_closing_degree,
            max_opening_degree=self._max_opening_degree,
            opening_threshold=self._opening_threshold,
        )

        # Send opening_degree

        await super().send_percent_open(opening_degree)

        if self.has_closing_degree_entity:
            await self.send_value_to_number(self._closing_degree_entity_id, closing_degree)

        # Since 8.5.0 the syncrhonization is done upon reception of a new temperature from sensor
        # send offset_calibration to the difference between target temp and local temp
        # offset = None
        # if self.has_offset_calibration_entity:
        #     if (
        #         (local_temp := self._climate_underlying.underlying_current_temperature)
        #         is not None
        #         and (room_temp := self._thermostat.current_temperature) is not None
        #         and (
        #             current_offset := get_safe_float(
        #                 self._hass, self._offset_calibration_entity_id
        #             )
        #         )
        #         is not None
        #     ):
        #         val = round_to_nearest(room_temp - (local_temp - current_offset), self._step_sync_entoty)
        #         offset = min(self._max_offset_calibration, max(self._min_offset_calibration, val))
        #
        #         await self.send_value_to_number(
        #             self._offset_calibration_entity_id, offset
        #         )

        _LOGGER.debug(
            "%s - valve regulation - I have sent opening_degree=%s closing_degree=%s",
            self,
            opening_degree,
            closing_degree,
        )

    @property
    def opening_degree_entity_id(self) -> str:
        """The offset_calibration_entity_id"""
        return self._opening_degree_entity_id

    @property
    def closing_degree_entity_id(self) -> str:
        """The offset_calibration_entity_id"""
        return self._closing_degree_entity_id

    @property
    def min_opening_degree(self) -> int:
        """The minimum opening degree"""
        return self._min_opening_degree

    @property
    def has_closing_degree_entity(self) -> bool:
        """Return True if the underlying have a closing_degree entity"""
        return self._closing_degree_entity_id is not None

    @property
    def hvac_modes(self) -> list[VThermHvacMode]:
        """Get the hvac_modes"""
        if not self.is_initialized:
            return []
        return [VThermHvacMode_HEAT, VThermHvacMode_SLEEP, VThermHvacMode_OFF]

    @overrides
    async def start_cycle(
        self,
        hvac_mode: VThermHvacMode,
        _1,
        _2,
        _3,
        force=False,
    ):
        """We use this function to change the on_percent"""
        # if force:
        await self.set_valve_open_percent()

    @property
    def is_device_active(self):
        """If the opening valve is open."""
        if not self.initialize_min_max():
            return False

        if (value := self.last_sent_opening_value) is None:
            return False

        return value > (100 - self._max_closing_degree)

    @property
    def hvac_action(self) -> HVACAction:
        """Calculate a hvac_action"""
        if (value := self.last_sent_opening_value) is None:
            return HVACAction.OFF

        if value > (100 - self._max_closing_degree):
            return HVACAction.HEATING
        elif value > 0:
            return HVACAction.IDLE
        else:
            return HVACAction.OFF

    @property
    def valve_entity_ids(self) -> List[str]:
        """get an arrary with all entityd id of the valve"""
        ret = []
        for entity in [
            self.opening_degree_entity_id,
            self.closing_degree_entity_id,
        ]:
            if entity:
                ret.append(entity)
        return ret

    @overrides
    async def check_initial_state(self, hvac_mode: VThermHvacMode):
        """Check the initial state of the underlying valve"""
        if hvac_mode == VThermHvacMode_OFF and self._thermostat.is_sleeping and (self.percent_open is None or self.percent_open < 100):
            _LOGGER.info(
                "%s - The hvac mode is OFF (sleep mode), but the underlying device is not fully open. Setting to 100%% device %s",
                self,
                self._entity_id,
            )
            self._percent_open = 100
            await self.send_percent_open()
        elif hvac_mode == VThermHvacMode_OFF and not self._thermostat.is_sleeping and (self.percent_open is None or self.percent_open > 0):
            _LOGGER.info(
                "%s - The hvac mode is OFF and not sleeping, but the underlying device is not at off. Setting to %d%% device %s",
                self,
                0,
                self._entity_id,
            )
            self._percent_open = 0
            await self.send_percent_open()
        else:
            await super().check_initial_state(hvac_mode)

    @overrides
    async def turn_off(self):
        """Turn valve off. In that context it means set the valve to the minimum opening degree."""
        _LOGGER.debug("%s - Stopping underlying entity %s", self, self._entity_id)
        self._percent_open = 0
        await self.send_percent_open()

T = TypeVar("T", bound=UnderlyingEntity)
