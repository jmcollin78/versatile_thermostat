# pylint: disable=unused-argument, line-too-long, too-many-lines, broad-exception-caught

""" Underlying entities classes """
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, TypeVar
from collections.abc import Callable
from datetime import datetime, timedelta

from enum import StrEnum

from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State

from homeassistant.exceptions import ServiceNotFound

from homeassistant.core import HomeAssistant, CALLBACK_TYPE, Context, ServiceResponse
from homeassistant.components.climate import (
    ClimateEntityFeature,
    DOMAIN as CLIMATE_DOMAIN,
    HVACAction,
    HVACMode,
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

from homeassistant.helpers.event import async_call_later
from homeassistant.util.unit_conversion import TemperatureConverter

from custom_components.versatile_thermostat.opening_degree_algorithm import OpeningClosingDegreeCalculation


from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .vtherm_hvac_mode import VThermHvacMode, to_legacy_ha_hvac_mode
from .keep_alive import IntervalCaller
from .underlying_state_manager import UnderlyingStateManager

_LOGGER = logging.getLogger(__name__)

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
        # Use UnderlyingStateManager to track underlying entity state
        self._state_manager: UnderlyingStateManager = UnderlyingStateManager(self._hass, on_change=self._underlying_changed)
        self._is_initialized: bool = False

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
        """True if the underlying is initialized and have received a non None state"""
        return self._is_initialized

    def startup(self):
        """Startup the Entity. Listen to the underlying state changes"""
        # starts listening and can provide the initial cached state.
        self._state_manager.add_underlying_entities([self._entity_id])

    async def _underlying_changed(self, entity_id: str, new_state: Optional[State], old_state: Optional[State] = None):
        """Handle underlying state change notified by UnderlyingStateManager.

        `new_state` may be None when the entity is removed/unavailable.
        Runs the initial state checks when all underlying entities are initialized.
        """
        _LOGGER.debug("%s --------> Underlying state change received: '%s'", self, new_state)
        # If not yet initialized and we received a valid initial state, run initial checks
        if not self.is_initialized:
            # Check if we have a valid state for all underlying entities for the first time
            if self._state_manager.is_all_states_initialized:
                self._is_initialized = True
                _LOGGER.debug("%s - All underlying states are now initialized", self)
                await self.check_initial_state()
                await self._thermostat.init_underlyings_completed(self._entity_id)
            else:
                _LOGGER.debug("%s - Underlying state still not yet initialized", self)
        # Otherwise, nothing to do here: the manager holds the latest state

    async def set_hvac_mode(self, hvac_mode: VThermHvacMode):
        """Set the HVACmode"""
        self._hvac_mode = hvac_mode
        return

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

    def remove_entity(self):
        """Remove the underlying entity"""
        self._on_cycle_start_callbacks.clear()
        # Stop the state manager listener for this entity
        self._state_manager.stop()

    async def check_initial_state(self):
        """Prevent the underlying to be on but thermostat is off"""
        return NotImplementedError
        # is_device_active = self.is_device_active
        # hvac_mode = self._thermostat.vtherm_hvac_mode

        # if hvac_mode == VThermHvacMode_OFF and is_device_active:
        #     _LOGGER.info(
        #         "%s - The hvac mode is OFF, but the underlying device is ON. Turning off device %s",
        #         self,
        #         self._entity_id,
        #     )
        #     await self.set_hvac_mode(hvac_mode)
        # elif hvac_mode != VThermHvacMode_OFF and not is_device_active:
        #     _LOGGER.info(
        #         "%s - The hvac mode is %s, but the underlying device is not ON. Turning on device %s if needed",
        #         self,
        #         hvac_mode,
        #         self._entity_id,
        #     )
        #     await self.set_hvac_mode(hvac_mode)

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

    def clamp_sent_value(self, value) -> float:
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

    @property
    def hvac_mode(self) -> VThermHvacMode | None:
        """Return the current hvac_mode"""
        return self._hvac_mode

    @property
    def should_device_be_active(self) -> bool | None:
        """If the underlying device should currently be active.
        Need to be overriden"""
        return NotImplementedError

    @property
    def is_device_active(self) -> bool | None:
        """If the underlying device is currently active.
        Need to be overriden"""
        return NotImplementedError

    @property
    def hvac_action(self) -> HVACAction:
        """Calculate a hvac_action"""
        return HVACAction.HEATING if self.should_device_be_active is True else HVACAction.OFF

    @property
    def is_inversed(self):
        """Tells if the switch command should be inversed"""
        return False

    @property
    def state_manager(self) -> UnderlyingStateManager:
        """Return the underlying state manager"""
        return self._state_manager

    # For testing compatibility
    @property
    def _last_known_underlying_state(self) -> Optional[State]:
        """Return the last known underlying state"""
        return self._state_manager.get_state(self._entity_id)


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
    def should_device_be_active(self) -> bool:
        """If the toggleable device is currently active."""
        return self._on_time_sec > 0 and self.hvac_mode in [VThermHvacMode_HEAT, VThermHvacMode_COOL]

    @property
    def is_device_active(self) -> bool | None:
        """If the toggleable device is currently active."""
        if not self.is_initialized:
            return None
        state = self._state_manager.get_state(self._entity_id)
        if state is None:
            return None

        is_on = state.state == self._on_command.get("state")
        return is_on

    async def check_initial_state(self):
        """Prevent the underlying to be on but thermostat is off"""
        hvac_mode = self._thermostat.vtherm_hvac_mode

        if hvac_mode == VThermHvacMode_OFF and self.is_device_active:
            _LOGGER.info(
                "%s - The hvac mode is OFF, but the underlying device is ON. Turning off device %s",
                self,
                self._entity_id,
            )
            await self.turn_off()
        # elif hvac_mode != VThermHvacMode_OFF and not is_device_active:
        # it is normal, the cycle could be started later or in off phase

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
            await (self.turn_on() if self.should_device_be_active else self.turn_off())

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
        if self.should_device_be_active:
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
            if self.should_device_be_active:
                await self.turn_off()
            return

        # safety mode could have change the on_time percent
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
            if self.should_device_be_active:
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
        self._last_sent_temperature: Optional[float] = None
        self._cancel_set_fan_mode_later: Optional[Callable[[], None]] = None
        self._min_sync_entity: float = None
        self._max_sync_entity: float = None
        self._step_sync_entity: float = None

    async def set_hvac_mode(self, hvac_mode: VThermHvacMode) -> bool:
        """Set the HVACmode of the underlying climate. Returns true if something have change"""
        state = self._state_manager.get_state(self._entity_id)
        if state is None:
            return False

        if state.state == to_ha_hvac_mode(hvac_mode):
            _LOGGER.debug(
                "%s - hvac_mode is already is requested state %s. Do not send any command",
                self,
                state.state,
            )
            return False

        # When turning on a climate, check that power is available
        if hvac_mode in (VThermHvacMode_HEAT, VThermHvacMode_COOL) and not await self.check_overpowering():
            return False

        await super().set_hvac_mode(hvac_mode)

        data = {ATTR_ENTITY_ID: self._entity_id, "hvac_mode": to_legacy_ha_hvac_mode(hvac_mode)}
        await self.hass_services_async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            data,
        )

        return True

    @property
    def should_device_be_active(self):
        """If the toggleable device is currently active."""
        return self.hvac_mode != VThermHvacMode_OFF and self.hvac_action not in [
            HVACAction.IDLE,
            HVACAction.OFF,
            None,
        ]

    @property
    def is_device_active(self):
        """If the toggleable device is currently active."""
        state = self._state_manager.get_state(self._entity_id)
        if state is None:
            return None

        hvac_action = state.attributes.get("hvac_action", None)

        # The device is active if hvac_mode is not OFF/IDLE and hvac_action is not OFF/IDLE. hvac_action could be None because it is not always implemented by all climate entities
        return state.state != HVACMode.OFF and (hvac_action not in [HVACAction.IDLE, HVACAction.OFF])

    async def check_initial_state(self):
        """Prevent the underlying to be on but thermostat is off"""
        is_device_active = self._state_manager.get_state(self._entity_id).state not in [HVACMode.OFF, STATE_UNAVAILABLE, STATE_UNKNOWN]
        hvac_mode = self._thermostat.vtherm_hvac_mode

        if hvac_mode == VThermHvacMode_OFF and is_device_active:
            _LOGGER.info(
                "%s - The hvac mode is OFF, but the underlying device is ON. Turning off device %s",
                self,
                self._entity_id,
            )
            await self.set_hvac_mode(hvac_mode)
        elif hvac_mode != VThermHvacMode_OFF and not is_device_active:
            _LOGGER.info(
                "%s - The hvac mode is %s, but the underlying device is not ON. Turning on device %s if needed",
                self,
                hvac_mode,
                self._entity_id,
            )
            await self.set_hvac_mode(hvac_mode)

    async def _underlying_changed(self, entity_id: str, new_state: Optional[State], old_state: Optional[State] = None):
        """Handle underlying state change notified by UnderlyingStateManager.

        `new_state` may be None when the entity is removed/unavailable.
        Runs the initial state checks when all underlying entities are initialized.
        """
        await super()._underlying_changed(entity_id, new_state, old_state)
        if not self.is_initialized or new_state is None:
            return

        # Check if one attributes has changed that could impact the thermostat
        new_hvac_mode = VThermHvacMode(new_state.state)
        old_hvac_mode = VThermHvacMode(old_state.state) if old_state else None
        new_hvac_action = new_state.attributes.get("hvac_action") if new_state.attributes else None
        old_hvac_action = old_state.attributes.get("hvac_action") if old_state and old_state.attributes else None
        new_fan_mode = new_state.attributes.get("fan_mode") if new_state.attributes else None
        new_target_temp = new_state.attributes.get("temperature") if new_state.attributes else None

        # Ignore new target temperature when out of range
        if (
            not new_target_temp is None
            and not self._thermostat.min_temp is None
            and not self._thermostat.max_temp is None
            and not (self._thermostat.min_temp <= new_target_temp <= self._thermostat.max_temp)
        ):
            _LOGGER.debug(
                "%s - underlying sent a target temperature (%s) which is out of configured min/max range (%s / %s). The value will be ignored",
                self,
                new_target_temp,
                self._thermostat.min_temp,
                self._thermostat.max_temp,
            )
            new_target_temp = None

        under_temp_diff = 0
        if new_target_temp is not None:
            last_sent_temperature = self.last_sent_temperature or 0
            under_temp_diff = new_target_temp - last_sent_temperature

            # check the dtemp is > step
            step = self._thermostat.target_temperature_step or 1
            if -step < under_temp_diff < step:
                under_temp_diff = 0
                new_target_temp = None

        # Forget event when the event holds no real changes
        if new_hvac_mode == self._thermostat.hvac_mode:
            new_hvac_mode = None
        if new_hvac_action == old_hvac_action:
            new_hvac_action = None
        if new_fan_mode == self._thermostat.fan_mode:
            new_fan_mode = None
        if under_temp_diff == 0:
            new_target_temp = None

        if new_hvac_mode is None and new_hvac_action is None and new_target_temp is None and new_fan_mode is None:
            _LOGGER.debug(
                "%s - a underlying state change event is received but no real change have been found. Forget the event",
                self,
            )
            return

        await self._thermostat.underlying_changed(self, new_hvac_mode, new_hvac_action, new_target_temp, new_fan_mode, new_state, old_state)

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
        target_temp = self.clamp_sent_value(temperature)
        data = {
            ATTR_ENTITY_ID: self._entity_id,
        }

        _LOGGER.info("%s - Set setpoint temperature to: %s", self, target_temp)

        # Issue 807 add TARGET_TEMPERATURE only if in the features
        if ClimateEntityFeature.TARGET_TEMPERATURE_RANGE in self.supported_features:
            data.update(
                {
                    "target_temp_high": target_temp,
                    "target_temp_low": target_temp,
                }
            )

        if ClimateEntityFeature.TARGET_TEMPERATURE in self.supported_features:
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

        hvac_action = self.underlying_hvac_action
        if hvac_action is None:
            # simulate hvac action if not provided by underlying climate
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
        state = self._state_manager.get_state(self._entity_id)
        return state.state if state is not None else None

    @property
    def fan_mode(self) -> str | None:
        """Get the fan_mode of the underlying"""
        if not self.is_initialized or self.supported_features & ClimateEntityFeature.FAN_MODE == 0:
            return None
        return self.get_underlying_attribute("fan_mode")

    @property
    def swing_mode(self) -> str | None:
        """Get the swing_mode of the underlying"""
        if not self.is_initialized or self.supported_features & ClimateEntityFeature.SWING_MODE == 0:
            return None
        return self.get_underlying_attribute("swing_mode")

    @property
    def swing_horizontal_mode(self) -> str | None:
        """Get the swing_horizontal_mode of the underlying"""
        return self.get_underlying_attribute("swing_horizontal_mode")

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Get the supported features of the climate"""
        return self.get_underlying_attribute("supported_features")

    @property
    def hvac_modes(self) -> list[VThermHvacMode]:
        """Get the hvac_modes"""
        if not self.is_initialized:
            return []
        return self.get_underlying_attribute("hvac_modes")

    @property
    def current_humidity(self) -> float | None:
        """Get the humidity"""
        return self.get_underlying_attribute("current_humidity")

    @property
    def fan_modes(self) -> list[str]:
        """Get the fan_modes"""
        if not self.is_initialized or self.supported_features & ClimateEntityFeature.FAN_MODE == 0:
            return []
        return self.get_underlying_attribute("fan_modes")

    @property
    def swing_modes(self) -> list[str]:
        """Get the swing_modes"""
        if not self.is_initialized or self.supported_features & ClimateEntityFeature.SWING_MODE == 0:
            return []
        return self.get_underlying_attribute("swing_modes")

    @property
    def swing_horizontal_modes(self) -> list[str]:
        """Get the swing_horizontal_modes"""
        if not self.is_initialized or self.supported_features & ClimateEntityFeature.SWING_HORIZONTAL_MODE == 0:
            return []
        return self.get_underlying_attribute("swing_horizontal_modes")

    @property
    def temperature_unit(self) -> str:
        """Get the temperature_unit"""
        return self.get_underlying_attribute("temperature_unit")

    @property
    def min_temp(self) -> str:
        """Get the min_temp"""
        return self.get_underlying_attribute("min_temp")

    @property
    def max_temp(self) -> str:
        """Get the max_temp"""
        return self.get_underlying_attribute("max_temp")

    @property
    def target_temperature_step(self) -> float:
        """Get the target_temperature_step"""
        return self.get_underlying_attribute("target_temperature_step")

    @property
    def target_temperature_high(self) -> float:
        """Get the target_temperature_high"""
        return self.get_underlying_attribute("target_temperature_high")

    @property
    def target_temperature_low(self) -> float:
        """Get the target_temperature_low"""
        return self.get_underlying_attribute("target_temperature_low")

    @property
    def underlying_target_temperature(self) -> float:
        """Get the target_temperature"""
        return self.get_underlying_attribute("target_temperature")

    @property
    def underlying_current_temperature(self) -> float | None:
        """Get the underlying current_temperature if it exists
        and if initialized"""
        return self.get_underlying_attribute("current_temperature")

    @property
    def underlying_hvac_action(self) -> HVACAction | None:
        """Get the underlying hvac_action if it exists
        and if initialized"""
        return self.get_underlying_attribute("hvac_action")

    @property
    def is_aux_heat(self) -> bool:
        """Get the is_aux_heat"""
        return self.get_underlying_attribute("is_aux_heat")

    def get_underlying_attribute(self, attribute_name: str) -> Any:
        """Get an attribute from the underlying climate"""
        if not self.is_initialized:
            return None
        state = self._state_manager.get_state(self._entity_id)
        if state is None:
            return None
        return state.attributes.get(attribute_name, None)

    # Not used and there is no action to start. To be removed
    # def turn_aux_heat_on(self) -> None:
    #     """Turn auxiliary heater on."""
    #     if not self.is_initialized:
    #         return None
    #     return self._underlying_climate.turn_aux_heat_on()
    #
    # def turn_aux_heat_off(self) -> None:
    #     """Turn auxiliary heater on."""
    #     if not self.is_initialized:
    #         return None
    #     return self._underlying_climate.turn_aux_heat_off()

    @overrides
    def clamp_sent_value(self, value) -> float:
        """Try to adapt the target temp value to the min_temp / max_temp found
        in the underlying entity (if any)"""
        min_val = None
        max_val = None

        if not self.is_initialized:
            raise RuntimeError(f"{self} - cannot cap sent value because underlying is not initialized")
            # return value

        # Gets the min_temp and max_temp
        if self.min_temp is not None:
            min_val = TemperatureConverter.convert(self.min_temp, self.temperature_unit, self._hass.config.units.temperature_unit)
            max_val = TemperatureConverter.convert(self.max_temp, self.temperature_unit, self._hass.config.units.temperature_unit)

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
        self._min_open: float | None = None
        self._max_open: float | None = None
        self._last_sent_temperature = None
        self._last_sent_opening_value: int | None = None

    @overrides
    async def check_initial_state(self):
        """Handle initial valve state change to get the min and max open percent"""
        # Initialize percent_open to current state
        valve_state = self._state_manager.get_state(self.entity_id)
        valve_open: float = get_safe_float_value(valve_state.state)
        if valve_open is None:
            # should not happen
            raise ValueError(f"{self} - cannot check_initial_state because underlying entity {self._entity_id} value {valve_state.state} is not a valid float")

        self._last_sent_opening_value = valve_open

        if "min" in valve_state.attributes and "max" in valve_state.attributes:
            self._min_open = valve_state.attributes["min"]
            self._max_open = valve_state.attributes["max"]
        else:
            self._min_open = 0
            self._max_open = 100

        should_device_be_active = self.should_device_be_active
        is_device_active = self.is_device_active

        if should_device_be_active and not is_device_active:
            _LOGGER.info(
                "%s - The valve should be active (percent_open=%.0f), but the underlying valve is closed (current_valve_opening=%.0f). Opening valve %s",
                self,
                self._percent_open or 9999,
                valve_open or 9999,
                self._entity_id,
            )
            await self.send_percent_open()
        elif not should_device_be_active and is_device_active:
            _LOGGER.info(
                "%s - The valve should not be active (percent_open=%.0f), but the underlying valve is open (current_valve_opening=%.0f). Closing valve %s",
                self,
                self._percent_open or 9999,
                valve_open or 9999,
                self._entity_id,
            )
            await self.send_percent_open(fixed_value=self._min_open)

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
        self._percent_open = self.clamp_sent_value(0)
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

    @property
    def should_device_be_active(self) -> bool:
        """If the toggleable device is currently active."""
        try:
            return self._percent_open > (self._min_open or 0) if isinstance(self._percent_open, (int, float)) else False
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    @property
    def is_device_active(self) -> bool | None:
        """If the toggleable device is currently active."""
        if (current_opening := self.current_valve_opening) is None:
            return None

        return current_opening > (self._min_open or 0)

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
    def clamp_sent_value(self, value) -> float:
        """Try to adapt the open_percent value to the min / max found
        in the underlying entity (if any)"""
        if not self.is_initialized:
            raise RuntimeError(f"{self} - cannot clamp sent value because underlying is not initialized")
            # return value

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
        caped_val = self.clamp_sent_value(self._thermostat.valve_open_percent)
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

    @property
    def current_valve_opening(self) -> float | None:
        """Get the current valve opening from the underlying entity"""

        valve_state = self._state_manager.get_state(self.entity_id)
        valve_open: float = get_safe_float_value(valve_state.state)
        return valve_open


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
        self._has_max_closing_degree: bool = closing_degree_entity_id is not None
        self._climate_underlying = climate_underlying
        self._is_min_max_initialized: bool = False
        self._max_opening_degree: float = max_opening_degree
        self._min_opening_degree: int = min_opening_degree
        self._max_closing_degree: int = max_closing_degree
        self._opening_threshold: int = opening_threshold

        if self._min_opening_degree >= self._max_opening_degree:
            self._min_opening_degree = self._opening_threshold
            _LOGGER.error(
                "min_opening_degree must be less than the max value of the opening degree of the entity {self._opening_degree_entity_id}. Value has been defaulted to opening threshold ({self._opening_threshold})"
            )

    @overrides
    async def check_initial_state(self):
        """Handle initial valve state change and hvac_mode"""

        hvac_mode = self._thermostat.vtherm_hvac_mode
        device_valve_opening = self.current_valve_opening  # the real opening value

        cuurent_hvac_mode_is_active = self._state_manager.get_state(self._climate_underlying.entity_id).state not in [HVACMode.OFF, STATE_UNAVAILABLE, STATE_UNKNOWN]

        should_be_on = hvac_mode != VThermHvacMode_OFF and not self._thermostat.is_sleeping
        is_on = cuurent_hvac_mode_is_active or (device_valve_opening is not None and device_valve_opening > self._opening_threshold)

        if should_be_on and not is_on:
            _LOGGER.info(
                "%s - The valve should be active (hvac_mode=%s, sleeping=%s, percent_open=%.0f), but the underlying device is off or below threshold (current_valve_opening=%.0f). Opening valve %s",
                self,
                hvac_mode,
                self._thermostat.is_sleeping,
                self._percent_open or 9999,
                device_valve_opening or 9999,
                self._entity_id,
            )
            await self._climate_underlying.set_hvac_mode(hvac_mode)
            if self._thermostat.is_sleeping:
                self._percent_open = 100
            else:
                self._percent_open = self._thermostat.valve_open_percent or self._opening_threshold
            await self.send_percent_open()

        elif not should_be_on and is_on:
            _LOGGER.info(
                "%s - The hvac mode is OFF and not sleeping, but the underlying device is not at off. Setting to %d%% device %s",
                self,
                self._opening_threshold,
                self._entity_id,
            )
            self._percent_open = self._opening_threshold
            await self.send_percent_open()
            await self._climate_underlying.set_hvac_mode(hvac_mode)

    def startup(self):
        """Startup the Entity. Listen to the underlying state changes"""
        # starts listening and can provide the initial cached state.
        entities = [self._climate_underlying.entity_id, self._opening_degree_entity_id]
        if self._has_max_closing_degree:
            entities.append(self._closing_degree_entity_id)
        self._state_manager.add_underlying_entities(entities)

    async def send_percent_open(self, _: float = None):
        """Send the percent open to the underlying valve"""
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
        val = self.current_valve_opening
        return val > self._opening_threshold if isinstance(val, (int, float)) else False

    @property
    def should_device_be_active(self):
        """If the opening valve is open."""
        # return value > (100 - self._max_closing_degree) # TODO why this ?
        return self.hvac_mode not in [VThermHvacMode_OFF] and self._percent_open > self._opening_threshold if isinstance(self._percent_open, (int, float)) else False

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
    async def turn_off(self):
        """Turn valve off. In that context it means set the valve to the minimum opening degree."""
        _LOGGER.debug("%s - Stopping underlying entity %s", self, self._entity_id)
        self._percent_open = 0
        await self.send_percent_open()
        await self._climate_underlying.set_hvac_mode(VThermHvacMode_OFF)

T = TypeVar("T", bound=UnderlyingEntity)
