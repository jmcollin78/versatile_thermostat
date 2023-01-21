""" Implements the VersatileThermostat climate component """
import math
import logging

from datetime import timedelta, datetime

# from typing import Any

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    callback,
    CoreState,
    DOMAIN as HA_DOMAIN,
)
from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_call_later,
)

from homeassistant.exceptions import ConditionError
from homeassistant.helpers import (
    condition,
    entity_platform,
)  # , config_validation as cv

from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    # ATTR_FAN_MODE,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_ACTIVITY,
    # PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    # PRESET_HOME,
    PRESET_NONE,
    # PRESET_SLEEP,
    SUPPORT_PRESET_MODE,
    # SUPPORT_TARGET_TEMPERATURE,
)

from homeassistant.const import (
    # UnitOfTemperature,
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
    # TEMP_FAHRENHEIT,
    CONF_NAME,
    # CONF_UNIQUE_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    STATE_OFF,
    STATE_ON,
    EVENT_HOMEASSISTANT_START,
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_HOME,
    STATE_NOT_HOME,
)

from .const import (
    # DOMAIN,
    CONF_HEATER,
    CONF_POWER_SENSOR,
    CONF_TEMP_SENSOR,
    CONF_EXTERNAL_TEMP_SENSOR,
    CONF_MAX_POWER_SENSOR,
    CONF_WINDOW_SENSOR,
    CONF_WINDOW_DELAY,
    CONF_MOTION_SENSOR,
    CONF_MOTION_DELAY,
    CONF_MOTION_PRESET,
    CONF_NO_MOTION_PRESET,
    CONF_DEVICE_POWER,
    CONF_PRESETS,
    CONF_PRESETS_AWAY,
    CONF_CYCLE_MIN,
    CONF_PROP_FUNCTION,
    CONF_TPI_COEF_INT,
    CONF_TPI_COEF_EXT,
    CONF_PRESENCE_SENSOR,
    CONF_PRESET_POWER,
    SUPPORT_FLAGS,
    PRESET_POWER,
    PRESET_SECURITY,
    PROPORTIONAL_FUNCTION_TPI,
    SERVICE_SET_PRESENCE,
    SERVICE_SET_PRESET_TEMPERATURE,
    PRESET_AWAY_SUFFIX,
    CONF_SECURITY_DELAY_MIN,
    CONF_MINIMAL_ACTIVATION_DELAY,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    HIDDEN_PRESETS,
)

from .prop_algorithm import PropAlgorithm

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VersatileThermostat thermostat with config flow."""
    _LOGGER.debug(
        "Calling async_setup_entry entry=%s, data=%s", entry.entry_id, entry.data
    )

    unique_id = entry.entry_id
    name = entry.data.get(CONF_NAME)

    entity = VersatileThermostat(hass, unique_id, name, entry.data)

    async_add_entities([entity], True)
    VersatileThermostat.add_entity(entry.entry_id, entity)

    # Add services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_PRESENCE,
        {
            vol.Required("presence"): vol.In(
                [STATE_ON, STATE_OFF, STATE_HOME, STATE_NOT_HOME]
            ),
        },
        "service_set_presence",
    )

    platform.async_register_entity_service(
        SERVICE_SET_PRESET_TEMPERATURE,
        {
            vol.Required("preset"): vol.In(CONF_PRESETS),
            vol.Optional("temperature"): vol.Coerce(float),
            vol.Optional("temperature_away"): vol.Coerce(float),
        },
        "service_set_preset_temperature",
    )


class VersatileThermostat(ClimateEntity, RestoreEntity):
    """Representation of a Versatile Thermostat device."""

    # The list of VersatileThermostat entities
    _registry: dict[str, object] = {}

    def __init__(self, hass, unique_id, name, entry_infos) -> None:
        """Initialize the thermostat."""

        super().__init__()

        self._hass = hass
        self._attr_extra_state_attributes = {}

        self._unique_id = unique_id
        self._name = name
        self._prop_algorithm = None
        self._async_cancel_cycle = None
        self._hvac_mode = None
        self._target_temp = None
        self._saved_target_temp = None
        self._saved_preset_mode = None
        self._fan_mode = None
        self._humidity = None
        self._swing_mode = None
        self._current_power = None
        self._current_power_max = None
        self._window_state = None
        self._motion_state = None
        self._saved_hvac_mode = None
        self._window_call_cancel = None
        self._motion_call_cancel = None
        self._cur_ext_temp = None
        self._cur_temp = None
        self._ac_mode = None
        self._last_ext_temperature_mesure = None
        self._last_temperature_mesure = None
        self._cur_ext_temp = None
        self._presence_state = None
        self._overpowering_state = None
        self._should_relaunch_control_heating = None
        self._security_delay_min = None
        self._security_state = None

        self.post_init(entry_infos)

    def post_init(self, entry_infos):
        """Finish the initialization of the thermostast"""

        _LOGGER.info(
            "%s - Updating VersatileThermostat with infos %s",
            self,
            entry_infos,
        )
        # convert entry_infos into usable attributes
        presets = {}
        for (key, value) in CONF_PRESETS.items():
            _LOGGER.debug("looking for key=%s, value=%s", key, value)
            if value in entry_infos:
                presets[key] = entry_infos.get(value)
            else:
                _LOGGER.debug("value %s not found in Entry", value)

        presets_away = {}
        for (key, value) in CONF_PRESETS_AWAY.items():
            _LOGGER.debug("looking for key=%s, value=%s", key, value)
            if value in entry_infos:
                presets_away[key] = entry_infos.get(value)
            else:
                _LOGGER.debug("value %s not found in Entry", value)

        # Stop eventual cycle running
        if self._async_cancel_cycle is not None:
            self._async_cancel_cycle()
            self._async_cancel_cycle = None
        if self._window_call_cancel is not None:
            self._window_call_cancel()
            self._window_call_cancel = None
        if self._motion_call_cancel is not None:
            self._motion_call_cancel()
            self._motion_call_cancel = None

        # Exploit usable attributs
        self._heater_entity_id = entry_infos.get(CONF_HEATER)
        self._cycle_min = entry_infos.get(CONF_CYCLE_MIN)
        self._proportional_function = entry_infos.get(CONF_PROP_FUNCTION)
        self._temp_sensor_entity_id = entry_infos.get(CONF_TEMP_SENSOR)
        self._ext_temp_sensor_entity_id = entry_infos.get(CONF_EXTERNAL_TEMP_SENSOR)
        self._attr_max_temp = entry_infos.get(CONF_TEMP_MAX)
        self._attr_min_temp = entry_infos.get(CONF_TEMP_MIN)
        self._power_sensor_entity_id = entry_infos.get(CONF_POWER_SENSOR)
        self._max_power_sensor_entity_id = entry_infos.get(CONF_MAX_POWER_SENSOR)
        self._window_sensor_entity_id = entry_infos.get(CONF_WINDOW_SENSOR)
        self._window_delay_sec = entry_infos.get(CONF_WINDOW_DELAY)
        self._motion_sensor_entity_id = entry_infos.get(CONF_MOTION_SENSOR)
        self._motion_delay_sec = entry_infos.get(CONF_MOTION_DELAY)
        self._motion_preset = entry_infos.get(CONF_MOTION_PRESET)
        self._no_motion_preset = entry_infos.get(CONF_NO_MOTION_PRESET)
        self._motion_on = (
            self._motion_sensor_entity_id is not None
            and self._motion_preset is not None
            and self._no_motion_preset is not None
        )

        self._tpi_coef_int = entry_infos.get(CONF_TPI_COEF_INT)
        self._tpi_coef_ext = entry_infos.get(CONF_TPI_COEF_EXT)
        self._presence_sensor_entity_id = entry_infos.get(CONF_PRESENCE_SENSOR)
        self._power_temp = entry_infos.get(CONF_PRESET_POWER)

        self._presence_on = self._presence_sensor_entity_id is not None

        # TODO if self.ac_mode:
        #    self.hvac_list = [HVAC_MODE_COOL, HVAC_MODE_OFF]
        # else:
        self._hvac_list = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
        self._unit = TEMP_CELSIUS
        # Will be restored if possible
        self._hvac_mode = None  # HVAC_MODE_OFF
        self._saved_hvac_mode = self._hvac_mode

        self._support_flags = SUPPORT_FLAGS

        self._presets = presets
        self._presets_away = presets_away

        _LOGGER.debug(
            "%s - presets are set to: %s, away: %s",
            self,
            self._presets,
            self._presets_away,
        )
        # Will be restored if possible
        self._attr_preset_mode = None
        self._saved_preset_mode = None

        # Power management
        self._device_power = entry_infos.get(CONF_DEVICE_POWER)
        self._pmax_on = False
        self._current_power = None
        self._current_power_max = None
        if (
            self._max_power_sensor_entity_id
            and self._power_sensor_entity_id
            and self._device_power
        ):
            self._pmax_on = True
            self._current_power = 0
            self._current_power_max = 0
        else:
            _LOGGER.info("%s - Power management is not fully configured.", self)

        # will be restored if possible
        self._target_temp = None
        self._saved_target_temp = PRESET_NONE
        self._humidity = None
        self._ac_mode = False
        self._fan_mode = None
        self._swing_mode = None
        self._cur_temp = None
        self._cur_ext_temp = None

        # Fix parameters for TPI
        if (
            self._proportional_function == PROPORTIONAL_FUNCTION_TPI
            and self._ext_temp_sensor_entity_id is None
        ):
            _LOGGER.warning(
                "Using TPI function but not external temperature sensor is set. Removing the delta temp ext factor. Thermostat will not be fully operationnal"  # pylint: disable=line-too-long
            )
            self._tpi_coef_ext = 0

        self._security_delay_min = entry_infos.get(CONF_SECURITY_DELAY_MIN)
        self._minimal_activation_delay = entry_infos.get(CONF_MINIMAL_ACTIVATION_DELAY)
        self._last_temperature_mesure = datetime.now()
        self._last_ext_temperature_mesure = datetime.now()
        self._security_state = False
        self._saved_hvac_mode = None

        # Initiate the ProportionalAlgorithm
        if self._prop_algorithm is not None:
            del self._prop_algorithm
        self._prop_algorithm = PropAlgorithm(
            self._proportional_function,
            self._tpi_coef_int,
            self._tpi_coef_ext,
            self._cycle_min,
            self._minimal_activation_delay,
        )
        self._should_relaunch_control_heating = False

        # Memory synthesis state
        self._motion_state = None
        self._window_state = None
        self._overpowering_state = None
        self._presence_state = None

        # Calculate all possible presets
        self._attr_preset_modes = [PRESET_NONE]
        if len(presets):
            self._support_flags = SUPPORT_FLAGS | SUPPORT_PRESET_MODE

            for key, val in presets.items():
                if val != 0.0:
                    self._attr_preset_modes.append(key)

            # self._attr_preset_modes = (
            #    [PRESET_NONE] + list(presets.keys()) + [PRESET_ACTIVITY]
            # )
            _LOGGER.debug(
                "After adding presets, preset_modes to %s", self._attr_preset_modes
            )
        else:
            _LOGGER.debug("No preset_modes")

        if self._motion_on:
            self._attr_preset_modes.append(PRESET_ACTIVITY)

        _LOGGER.debug(
            "%s - Creation of a new VersatileThermostat entity: unique_id=%s heater_entity_id=%s",
            self,
            self.unique_id,
            self._heater_entity_id,
        )

    def __str__(self):
        return f"VersatileThermostat-{self.name}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return self._name

    @property
    def hvac_modes(self):
        """List of available operation modes."""
        return self._hvac_list

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def hvac_mode(self):
        """Return current operation."""
        return self._hvac_mode

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        if self._hvac_mode == HVAC_MODE_OFF:
            return CURRENT_HVAC_OFF
        if not self._is_device_active:
            return CURRENT_HVAC_IDLE
        if self._ac_mode:
            return CURRENT_HVAC_COOL
        return CURRENT_HVAC_HEAT

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temp

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def _is_device_active(self):
        """If the toggleable device is currently active."""
        if not self.hass.states.get(self._heater_entity_id):
            return None

        return self.hass.states.is_state(self._heater_entity_id, STATE_ON)

    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return self._cur_temp

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.info("%s - Set hvac mode: %s", self, hvac_mode)
        if hvac_mode == HVAC_MODE_HEAT:
            self._hvac_mode = HVAC_MODE_HEAT
            await self._async_control_heating(force=True)
        elif hvac_mode == HVAC_MODE_COOL:
            self._hvac_mode = HVAC_MODE_COOL
            await self._async_control_heating(force=True)
        elif hvac_mode == HVAC_MODE_OFF:
            self._hvac_mode = HVAC_MODE_OFF
            if self._is_device_active:
                await self._async_heater_turn_off()
            await self._async_control_heating(force=True)
        else:
            _LOGGER.error("Unrecognized hvac mode: %s", hvac_mode)
            return
        # Ensure we update the current operation after changing the mode
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        await self._async_set_preset_mode_internal(preset_mode)
        await self._async_control_heating(force=True)

    async def _async_set_preset_mode_internal(self, preset_mode, force=False):
        """Set new preset mode."""
        _LOGGER.info("%s - Set preset_mode: %s force=%s", self, preset_mode, force)
        if (
            preset_mode not in (self._attr_preset_modes or [])
            and preset_mode not in HIDDEN_PRESETS
        ):
            raise ValueError(
                f"Got unsupported preset_mode {preset_mode}. Must be one of {self._attr_preset_modes}"  # pylint: disable=line-too-long
            )

        if preset_mode == self._attr_preset_mode and not force:
            # I don't think we need to call async_write_ha_state if we didn't change the state
            return
        if preset_mode == PRESET_NONE:
            self._attr_preset_mode = PRESET_NONE
            if self._saved_target_temp:
                self._target_temp = self._saved_target_temp
        elif preset_mode == PRESET_ACTIVITY:
            self._attr_preset_mode = PRESET_ACTIVITY
            self._update_motion_temp()
        else:
            if self._attr_preset_mode == PRESET_NONE:
                self._saved_target_temp = self._target_temp
            self._attr_preset_mode = preset_mode
            self._target_temp = self.find_preset_temp(preset_mode)

        self.save_preset_mode()

        self.recalculate()

    def find_preset_temp(self, preset_mode):
        """Find the right temperature of a preset considering the presence if configured"""
        if preset_mode == PRESET_SECURITY:
            return (
                self._target_temp
            )  # in security just keep the current target temperature, the thermostat should be off
        if preset_mode == PRESET_POWER:
            return self._power_temp
        elif self._presence_on is False or self._presence_state in [
            STATE_ON,
            STATE_HOME,
        ]:
            return self._presets[preset_mode]
        else:
            return self._presets_away[self.get_preset_away_name(preset_mode)]

    def get_preset_away_name(self, preset_mode):
        """Get the preset name in away mode (when presence is off)"""
        return preset_mode + PRESET_AWAY_SUFFIX

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        _LOGGER.info("%s - Set fan mode: %s", self, fan_mode)
        if fan_mode is None:
            return
        self._fan_mode = fan_mode
        self.async_write_ha_state()

    async def async_set_humidity(self, humidity: int):
        """Set new target humidity."""
        _LOGGER.info("%s - Set fan mode: %s", self, humidity)
        if humidity is None:
            return
        self._humidity = humidity

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        _LOGGER.info("%s - Set fan mode: %s", self, swing_mode)
        if swing_mode is None:
            return
        self._swing_mode = swing_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.info("%s - Set target temp: %s", self, temperature)
        if temperature is None:
            return
        self._target_temp = temperature
        self._attr_preset_mode = PRESET_NONE
        self.recalculate()
        await self._async_control_heating(force=True)

    @callback
    async def entry_update_listener(
        self, _, config_entry: ConfigEntry  # hass: HomeAssistant,
    ) -> None:
        """Called when the entry have changed in ConfigFlow"""
        _LOGGER.info("%s - Change entry with the values: %s", self, config_entry.data)

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        _LOGGER.debug("Calling async_added_to_hass")

        await super().async_added_to_hass()

        # Add listener
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._heater_entity_id], self._async_switch_changed
            )
        )

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._temp_sensor_entity_id],
                self._async_temperature_changed,
            )
        )

        if self._ext_temp_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._ext_temp_sensor_entity_id],
                    self._async_ext_temperature_changed,
                )
            )

        if self._window_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._window_sensor_entity_id],
                    self._async_windows_changed,
                )
            )
        if self._motion_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._motion_sensor_entity_id],
                    self._async_motion_changed,
                )
            )

        if self._power_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._power_sensor_entity_id],
                    self._async_power_changed,
                )
            )

        if self._max_power_sensor_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._max_power_sensor_entity_id],
                    self._async_max_power_changed,
                )
            )

        if self._presence_on:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._presence_sensor_entity_id],
                    self._async_presence_changed,
                )
            )

        await self.async_startup()

        # starts the cycle
        # if self._cycle_min:
        #     self.async_on_remove(
        #         async_track_time_interval(
        #             self.hass,
        #             self._async_control_heating,
        #             interval=timedelta(minutes=self._cycle_min),
        #         )
        #     )

    async def async_startup(self):
        """Triggered on startup, used to get old state and set internal states accordingly"""
        _LOGGER.debug("%s - Calling async_startup", self)

        @callback
        async def _async_startup_internal(*_):
            _LOGGER.debug("%s - Calling async_startup_internal", self)
            need_write_state = False
            temperature_state = self.hass.states.get(self._temp_sensor_entity_id)
            if temperature_state and temperature_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                _LOGGER.debug(
                    "%s - temperature sensor have been retrieved: %.1f",
                    self,
                    float(temperature_state.state),
                )
                await self._async_update_temp(temperature_state)
                need_write_state = True

            if self._ext_temp_sensor_entity_id:
                ext_temperature_state = self.hass.states.get(
                    self._ext_temp_sensor_entity_id
                )
                if ext_temperature_state and ext_temperature_state.state not in (
                    STATE_UNAVAILABLE,
                    STATE_UNKNOWN,
                ):
                    _LOGGER.debug(
                        "%s - external temperature sensor have been retrieved: %.1f",
                        self,
                        float(ext_temperature_state.state),
                    )
                    await self._async_update_ext_temp(ext_temperature_state)
                else:
                    _LOGGER.debug(
                        "%s - external temperature sensor have NOT been retrieved cause unknown or unavailable",
                        self,
                    )
            else:
                _LOGGER.debug(
                    "%s - external temperature sensor have NOT been retrieved cause no external sensor",
                    self,
                )

            switch_state = self.hass.states.get(self._heater_entity_id)
            if switch_state and switch_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                self.hass.create_task(self._check_switch_initial_state())

            if self._pmax_on:
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
                    need_write_state = True

                # Try to acquire power max
                current_power_max_state = self.hass.states.get(
                    self._max_power_sensor_entity_id
                )
                if current_power_max_state and current_power_max_state.state not in (
                    STATE_UNAVAILABLE,
                    STATE_UNKNOWN,
                ):
                    self._current_power_max = float(current_power_max_state.state)
                    _LOGGER.debug(
                        "%s - Current power max have been retrieved: %.3f",
                        self,
                        self._current_power_max,
                    )
                    need_write_state = True

                # try to acquire window entity state
                if self._window_sensor_entity_id:
                    window_state = self.hass.states.get(self._window_sensor_entity_id)
                    if window_state and window_state.state not in (
                        STATE_UNAVAILABLE,
                        STATE_UNKNOWN,
                    ):
                        self._window_state = window_state.state
                        _LOGGER.debug(
                            "%s - Window state have been retrieved: %s",
                            self,
                            self._window_state,
                        )
                        need_write_state = True

                # try to acquire motion entity state
                if self._motion_sensor_entity_id:
                    motion_state = self.hass.states.get(self._motion_sensor_entity_id)
                    if motion_state and motion_state.state not in (
                        STATE_UNAVAILABLE,
                        STATE_UNKNOWN,
                    ):
                        self._motion_state = motion_state.state
                        _LOGGER.debug(
                            "%s - Motion state have been retrieved: %s",
                            self,
                            self._motion_state,
                        )
                        # recalculate the right target_temp in activity mode
                        self._update_motion_temp()
                        need_write_state = True

            if self._presence_on:
                # try to acquire presence entity state
                presence_state = self.hass.states.get(self._presence_sensor_entity_id)
                if presence_state and presence_state.state not in (
                    STATE_UNAVAILABLE,
                    STATE_UNKNOWN,
                ):
                    self._update_presence(presence_state.state)
                    _LOGGER.debug(
                        "%s - Presence have been retrieved: %s",
                        self,
                        presence_state.state,
                    )
                    need_write_state = True

            if need_write_state:
                self.async_write_ha_state()
                self._prop_algorithm.calculate(
                    self._target_temp, self._cur_temp, self._cur_ext_temp
                )
            self.hass.create_task(self._async_control_heating())

        await self.get_my_previous_state()

        if self.hass.state == CoreState.running:
            await _async_startup_internal()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_START, _async_startup_internal
            )

    async def get_my_previous_state(self):
        """Try to get my previou state"""
        # Check If we have an old state
        old_state = await self.async_get_last_state()
        _LOGGER.debug(
            "%s - Calling get_my_previous_state old_state is %s", self, old_state
        )
        if old_state is not None:
            # If we have no initial temperature, restore
            if self._target_temp is None:
                # If we have a previously saved temperature
                if old_state.attributes.get(ATTR_TEMPERATURE) is None:
                    if self._ac_mode:
                        self._target_temp = self.max_temp
                    else:
                        self._target_temp = self.min_temp
                    _LOGGER.warning(
                        "%s - Undefined target temperature, falling back to %s",
                        self,
                        self._target_temp,
                    )
                else:
                    self._target_temp = float(old_state.attributes[ATTR_TEMPERATURE])

            if old_state.attributes.get(ATTR_PRESET_MODE) in self._attr_preset_modes:
                self._attr_preset_mode = old_state.attributes.get(ATTR_PRESET_MODE)
                self.save_preset_mode()

            if not self._hvac_mode and old_state.state:
                self._hvac_mode = old_state.state

            # is done in startup above
            # self._prop_algorithm.calculate(
            #    self._target_temp, self._cur_temp, self._cur_ext_temp
            # )

        else:
            # No previous state, try and restore defaults
            if self._target_temp is None:
                if self._ac_mode:
                    self._target_temp = self.max_temp
                else:
                    self._target_temp = self.min_temp
            _LOGGER.warning(
                "No previously saved temperature, setting to %s", self._target_temp
            )

        self._saved_target_temp = self._target_temp

        # Set default state to off
        if not self._hvac_mode:
            self._hvac_mode = HVAC_MODE_OFF

        _LOGGER.info(
            "%s - restored state is target_temp=%.1f, preset_mode=%s, hvac_mode=%s",
            self,
            self._target_temp,
            self._attr_preset_mode,
            self._hvac_mode,
        )

    @callback
    async def _async_temperature_changed(self, event):
        """Handle temperature changes."""
        new_state = event.data.get("new_state")
        _LOGGER.info(
            "%s - Temperature changed. Event.new_state is %s",
            self,
            new_state,
        )
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        await self._async_update_temp(new_state)
        self.recalculate()
        await self._async_control_heating(force=False)

    async def _async_ext_temperature_changed(self, event):
        """Handle external temperature changes."""
        new_state = event.data.get("new_state")
        _LOGGER.info(
            "%s - external Temperature changed. Event.new_state is %s",
            self,
            new_state,
        )
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        await self._async_update_ext_temp(new_state)
        self.recalculate()
        await self._async_control_heating(force=False)

    @callback
    async def _async_windows_changed(self, event):
        """Handle window changes."""
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        _LOGGER.info(
            "%s - Window changed. Event.new_state is %s, _hvac_mode=%s, _saved_hvac_mode=%s",
            self,
            new_state,
            self._hvac_mode,
            self._saved_hvac_mode,
        )
        if new_state is None or old_state is None or new_state.state == old_state.state:
            return

        # Check delay condition
        async def try_window_condition(_):
            try:
                long_enough = condition.state(
                    self.hass,
                    self._window_sensor_entity_id,
                    new_state.state,
                    timedelta(seconds=self._window_delay_sec),
                )
            except ConditionError:
                long_enough = False

            if not long_enough:
                _LOGGER.debug(
                    "Window delay condition is not satisfied. Ignore window event"
                )
                return

            _LOGGER.debug("%s - Window delay condition is satisfied", self)
            if not self._saved_hvac_mode:
                self._saved_hvac_mode = self._hvac_mode

            self._window_state = new_state.state
            if self._window_state == STATE_OFF:
                _LOGGER.info(
                    "%s - Window is closed. Restoring hvac_mode '%s'",
                    self,
                    self._saved_hvac_mode,
                )
                await self.async_set_hvac_mode(self._saved_hvac_mode)
            elif self._window_state == STATE_ON:
                _LOGGER.info(
                    "%s - Window is open. Set hvac_mode to '%s'", self, HVAC_MODE_OFF
                )
                self._saved_hvac_mode = self._hvac_mode
                await self.async_set_hvac_mode(HVAC_MODE_OFF)

        if self._window_call_cancel:
            self._window_call_cancel()
            self._window_call_cancel = None
        self._window_call_cancel = async_call_later(
            self.hass, timedelta(seconds=self._window_delay_sec), try_window_condition
        )

    @callback
    async def _async_motion_changed(self, event):
        """Handle motion changes."""
        new_state = event.data.get("new_state")
        _LOGGER.info(
            "%s - Motion changed. Event.new_state is %s, _attr_preset_mode=%s, activity=%s",
            self,
            new_state,
            self._attr_preset_mode,
            PRESET_ACTIVITY,
        )

        if new_state is None or new_state.state not in (STATE_OFF, STATE_ON):
            return

        # Check delay condition
        async def try_motion_condition(_):
            try:
                long_enough = condition.state(
                    self.hass,
                    self._motion_sensor_entity_id,
                    new_state.state,
                    timedelta(seconds=self._motion_delay_sec),
                )
            except ConditionError:
                long_enough = False

            if not long_enough:
                _LOGGER.debug(
                    "Motion delay condition is not satisfied. Ignore motion event"
                )
                return

            _LOGGER.debug("%s - Motion delay condition is satisfied", self)
            self._motion_state = new_state.state
            if self._attr_preset_mode == PRESET_ACTIVITY:
                new_preset = (
                    self._motion_preset
                    if self._motion_state == STATE_ON
                    else self._no_motion_preset
                )
                _LOGGER.info(
                    "%s - Motion condition have changes. New preset temp will be %s",
                    self,
                    new_preset,
                )
                # We do not change the preset which is kept to ACTIVITY but only the target_temperature
                self._target_temp = self._presets[new_preset]
            self.recalculate()
            await self._async_control_heating(force=True)

        if self._motion_call_cancel:
            self._motion_call_cancel()
            self._motion_call_cancel = None
        self._motion_call_cancel = async_call_later(
            self.hass, timedelta(seconds=self._motion_delay_sec), try_motion_condition
        )

    @callback
    async def _check_switch_initial_state(self):
        """Prevent the device from keep running if HVAC_MODE_OFF."""
        _LOGGER.debug("%s - Calling _check_switch_initial_state", self)
        if self._hvac_mode == HVAC_MODE_OFF and self._is_device_active:
            _LOGGER.warning(
                "The climate mode is OFF, but the switch device is ON. Turning off device %s",
                self._heater_entity_id,
            )
            await self._async_heater_turn_off()

    @callback
    def _async_switch_changed(self, event):
        """Handle heater switch state changes."""
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None:
            return
        if old_state is None:
            self.hass.create_task(self._check_switch_initial_state())
        self.async_write_ha_state()

    @callback
    async def _async_update_temp(self, state):
        """Update thermostat with latest state from sensor."""
        try:
            cur_temp = float(state.state)
            if math.isnan(cur_temp) or math.isinf(cur_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")
            self._cur_temp = cur_temp
            self._last_temperature_mesure = datetime.now()
            # try to restart if we were in security mode
            if self._security_state:
                await self.async_set_hvac_mode(self._saved_hvac_mode)
                await self.restore_preset_mode()

        except ValueError as ex:
            _LOGGER.error("Unable to update temperature from sensor: %s", ex)

    @callback
    async def _async_update_ext_temp(self, state):
        """Update thermostat with latest state from sensor."""
        try:
            cur_ext_temp = float(state.state)
            if math.isnan(cur_ext_temp) or math.isinf(cur_ext_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")
            self._cur_ext_temp = cur_ext_temp
            self._last_ext_temperature_mesure = datetime.now()
            # try to restart if we were in security mode
            if self._security_state:
                await self.async_set_hvac_mode(self._saved_hvac_mode)
                await self.restore_preset_mode()
        except ValueError as ex:
            _LOGGER.error("Unable to update external temperature from sensor: %s", ex)

    @callback
    async def _async_power_changed(self, event):
        """Handle power changes."""
        _LOGGER.debug("Thermostat %s - Receive new Power event", self.name)
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

            if self._attr_preset_mode == PRESET_POWER:
                await self._async_control_heating()

        except ValueError as ex:
            _LOGGER.error("Unable to update current_power from sensor: %s", ex)

    @callback
    async def _async_max_power_changed(self, event):
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
            self._current_power_max = current_power_max
            if self._attr_preset_mode == PRESET_POWER:
                await self._async_control_heating()

        except ValueError as ex:
            _LOGGER.error("Unable to update current_power from sensor: %s", ex)

    @callback
    async def _async_presence_changed(self, event):
        """Handle presence changes."""
        new_state = event.data.get("new_state")
        _LOGGER.info(
            "%s - Presence changed. Event.new_state is %s, _attr_preset_mode=%s, activity=%s",
            self,
            new_state,
            self._attr_preset_mode,
            PRESET_ACTIVITY,
        )
        if new_state is None:
            return

        self._update_presence(new_state.state)
        await self._async_control_heating(force=True)

    def _update_presence(self, new_state):
        _LOGGER.debug("%s - Updating presence. New state is %s", self, new_state)
        self._presence_state = new_state
        if self._attr_preset_mode in HIDDEN_PRESETS or self._presence_on is False:
            _LOGGER.info(
                "%s - Ignoring presence change cause in Power or Security preset or presence not configured",
                self,
            )
            return
        if new_state is None or new_state not in (
            STATE_OFF,
            STATE_ON,
            STATE_HOME,
            STATE_NOT_HOME,
        ):
            return
        if self._attr_preset_mode not in [PRESET_BOOST, PRESET_COMFORT, PRESET_ECO]:
            return

        # Change temperature with preset named _way
        new_temp = None
        if new_state == STATE_ON or new_state == STATE_HOME:
            new_temp = self._presets[self._attr_preset_mode]
            _LOGGER.info(
                "%s - Someone is back home. Restoring temperature to %.2f",
                self,
                new_temp,
            )
        else:
            new_temp = self._presets_away[
                self.get_preset_away_name(self._attr_preset_mode)
            ]
            _LOGGER.info(
                "%s - No one is at home. Apply temperature %.2f",
                self,
                new_temp,
            )

        if new_temp is not None:
            _LOGGER.debug(
                "%s - presence change in temperature mode new_temp will be: %.2f",
                self,
                new_temp,
            )
            self._target_temp = new_temp
            self.recalculate()

    def _update_motion_temp(self):
        """Update the temperature considering the ACTIVITY preset and current motion state"""
        _LOGGER.debug(
            "%s - Calling _update_motion_temp preset_mode=%s, motion_state=%s",
            self,
            self._attr_preset_mode,
            self._motion_state,
        )
        if (
            self._motion_sensor_entity_id is None
            or self._attr_preset_mode != PRESET_ACTIVITY
        ):
            return

        self._target_temp = self._presets[
            self._motion_preset
            if self._motion_state == STATE_ON
            else self._no_motion_preset
        ]
        _LOGGER.debug(
            "%s - regarding motion, target_temp have been set to %.2f",
            self,
            self._target_temp,
        )

    async def _async_heater_turn_on(self):
        """Turn heater toggleable device on."""
        data = {ATTR_ENTITY_ID: self._heater_entity_id}
        await self.hass.services.async_call(
            HA_DOMAIN, SERVICE_TURN_ON, data, context=self._context
        )

    async def _async_heater_turn_off(self):
        """Turn heater toggleable device off."""
        data = {ATTR_ENTITY_ID: self._heater_entity_id}
        await self.hass.services.async_call(
            HA_DOMAIN, SERVICE_TURN_OFF, data, context=self._context
        )

    def save_preset_mode(self):
        """Save the current preset mode to be restored later
        We never save a hidden preset mode
        """
        if (
            self._attr_preset_mode not in HIDDEN_PRESETS
            and self._attr_preset_mode is not None
        ):
            self._saved_preset_mode = self._attr_preset_mode

    async def restore_preset_mode(self):
        """Restore a previous preset mode
        We never restore a hidden preset mode. Normally that is not possible
        """
        if (
            self._saved_preset_mode not in HIDDEN_PRESETS
            and self._saved_preset_mode is not None
        ):
            await self._async_set_preset_mode_internal(self._saved_preset_mode)

    async def check_overpowering(self) -> bool:
        """Check the overpowering condition
        Turn the preset_mode of the heater to 'power' if power conditions are exceeded
        """

        if not self._pmax_on:
            return

        _LOGGER.debug(
            "%s - overpowering check: power=%.3f, max_power=%.3f heater power=%.3f",
            self,
            self._current_power,
            self._current_power_max,
            self._device_power,
        )
        self._overpowering_state = (
            self._current_power + self._device_power >= self._current_power_max
        )
        if self._overpowering_state:
            _LOGGER.warning(
                "%s - overpowering is detected. Heater preset will be set to 'power'",
                self,
            )
            await self._async_set_preset_mode_internal(PRESET_POWER)
            return self._overpowering_state

        # Check if we need to remove the POWER preset
        if self._attr_preset_mode == PRESET_POWER and not self._overpowering_state:
            _LOGGER.warning(
                "%s - end of overpowering is detected. Heater preset will be restored to '%s'",
                self,
                self._saved_preset_mode,
            )
            await self.restore_preset_mode()

    def check_date_temperature(self) -> bool:
        """Check if last temperature date is too long"""
        now = datetime.now()
        delta_temp = (now - self._last_temperature_mesure).total_seconds() / 60.0
        delta_ext_temp = (
            now - self._last_ext_temperature_mesure
        ).total_seconds() / 60.0
        if (
            delta_temp > self._security_delay_min
            or delta_ext_temp > self._security_delay_min
        ):
            _LOGGER.warning(
                "%s - No temperature received for more than %.1f minutes (dt=%.1f, dext=%.1f)",
                self,
                self._security_delay_min,
                delta_temp,
                delta_ext_temp,
            )
            return False

        return True

    async def _async_control_heating(self, force=False, time=None):
        """The main function used to run the calculation at each cycle"""

        overpowering: bool = await self.check_overpowering()
        if overpowering:
            _LOGGER.debug(
                "%s - The max power is exceeded. Heater will not be started. preset_mode is now '%s'",  # pylint: disable=line-too-long
                self,
                self._attr_preset_mode,
            )
            await self._async_heater_turn_off()
            _LOGGER.debug("%s - End of cycle (0)", self)
            return

        on_time_sec: int = self._prop_algorithm.on_time_sec
        off_time_sec: int = self._prop_algorithm.off_time_sec
        _LOGGER.info(
            "%s - Checking new cycle. on_time_sec=%.0f, off_time_sec=%.0f, security_state=%s, preset_mode=%s",
            self,
            on_time_sec,
            off_time_sec,
            self._security_state,
            self._attr_preset_mode,
        )

        # Cancel eventual previous cycle if any
        if self._async_cancel_cycle is not None:
            if force:
                _LOGGER.debug("%s - we force a new cycle", self)
                self._async_cancel_cycle()
                self._async_cancel_cycle = None
            else:
                _LOGGER.debug(
                    "%s - A previous cycle is alredy running and no force -> waits for its end",
                    self,
                )
                self._should_relaunch_control_heating = True
                _LOGGER.debug("%s - End of cycle (1)", self)
                return

        if self._hvac_mode == HVAC_MODE_HEAT and on_time_sec > 0:

            async def _turn_on_off_later(
                on: bool, time, heater_action, next_cycle_action
            ):
                if self._async_cancel_cycle:
                    self._async_cancel_cycle()
                    self._async_cancel_cycle = None
                    _LOGGER.debug("%s - Stopping cycle during calculation", self)

                check_dates = self.check_date_temperature()
                if time > 0 and on is True and check_dates is False:
                    _LOGGER.warning("%s -  Set the thermostat into security mode", self)
                    self._security_state = True
                    self._saved_hvac_mode = self.hvac_mode
                    self.save_preset_mode()
                    await self._async_set_preset_mode_internal(PRESET_SECURITY)
                    await self.async_set_hvac_mode(HVAC_MODE_OFF)
                    # The cycle is not restarted in security mode. It will be restarted by a condition changes
                    _LOGGER.debug("%s - End of cycle (2)", self)
                    return
                if check_dates:
                    self._security_state = False

                action_label = "start" if on else "stop"
                if self._should_relaunch_control_heating:
                    _LOGGER.debug(
                        "Don't %s cause a cycle have to be relaunch", action_label
                    )
                    self._should_relaunch_control_heating = False
                    self.hass.create_task(self._async_control_heating())
                    # await self._async_control_heating()
                    _LOGGER.debug("%s - End of cycle (3)", self)
                    return

                if time > 0:
                    _LOGGER.info(
                        "%s - !!! %s heating for %d min %d sec",
                        self,
                        action_label,
                        time // 60,
                        time % 60,
                    )
                    await heater_action()
                else:
                    _LOGGER.debug("%s - No action on heater cause duration is 0", self)
                self.update_custom_attributes()
                self._async_cancel_cycle = async_call_later(
                    self.hass,
                    time,
                    next_cycle_action,
                )

            async def _turn_on_later(_):
                await _turn_on_off_later(
                    on=True,
                    time=self._prop_algorithm.on_time_sec,
                    heater_action=self._async_heater_turn_on,
                    next_cycle_action=_turn_off_later,
                )

            async def _turn_off_later(_):
                await _turn_on_off_later(
                    on=False,
                    time=self._prop_algorithm.off_time_sec,
                    heater_action=self._async_heater_turn_off,
                    next_cycle_action=_turn_on_later,
                )

            await _turn_on_later(None)

        elif self._is_device_active:
            _LOGGER.info(
                "%s - stop heating (2) for %d min %d sec",
                self,
                off_time_sec // 60,
                off_time_sec % 60,
            )
            await self._async_heater_turn_off()

        else:
            _LOGGER.debug("%s - nothing to do", self)

        self.update_custom_attributes()

    def recalculate(self):
        """A utility function to force the calculation of a the algo and
        update the custom attributes and write the state
        """
        _LOGGER.debug("%s - recalculate all", self)
        self._prop_algorithm.calculate(
            self._target_temp, self._cur_temp, self._cur_ext_temp
        )
        self.update_custom_attributes()
        self.async_write_ha_state()

    def update_custom_attributes(self):
        """Update the custom extra attributes for the entity"""

        self._attr_extra_state_attributes = {
            "eco_temp": self._presets[PRESET_ECO],
            "boost_temp": self._presets[PRESET_BOOST],
            "comfort_temp": self._presets[PRESET_COMFORT],
            "eco_away_temp": self._presets_away[self.get_preset_away_name(PRESET_ECO)],
            "boost_away_temp": self._presets_away[
                self.get_preset_away_name(PRESET_BOOST)
            ],
            "comfort_away_temp": self._presets_away[
                self.get_preset_away_name(PRESET_COMFORT)
            ],
            "power_temp": self._power_temp,
            "on_percent": self._prop_algorithm.on_percent,
            "on_time_sec": self._prop_algorithm.on_time_sec,
            "off_time_sec": self._prop_algorithm.off_time_sec,
            "ext_current_temperature": self._cur_ext_temp,
            "current_power": self._current_power,
            "current_power_max": self._current_power_max,
            "cycle_min": self._cycle_min,
            "function": self._proportional_function,
            "tpi_coef_int": self._tpi_coef_int,
            "tpi_coef_ext": self._tpi_coef_ext,
            "saved_preset_mode": self._saved_preset_mode,
            "saved_target_temp": self._saved_target_temp,
            "saved_hvac_mode": self._saved_hvac_mode,
            "window_state": self._window_state,
            "motion_state": self._motion_state,
            "overpowering_state": self._overpowering_state,
            "presence_state": self._presence_state,
            "security_delay_min": self._security_delay_min,
            "last_temperature_datetime": self._last_temperature_mesure.isoformat(),
            "last_ext_temperature_datetime": self._last_ext_temperature_mesure.isoformat(),
            "security_state": self._security_state,
            "minimal_activation_delay_sec": self._minimal_activation_delay,
            "last_update_datetime": datetime.now().isoformat(),
        }
        self.async_write_ha_state()
        _LOGGER.debug(
            "%s - Calling update_custom_attributes: %s",
            self,
            self._attr_extra_state_attributes,
        )

    @callback
    def async_registry_entry_updated(self):
        """update the entity if the config entry have been updated
        Note: this don't work either
        """
        _LOGGER.info("%s - The config entry have been updated.")

    async def service_set_presence(self, presence):
        """Called by a service call:
        service: versatile_thermostat.set_presence
        data:
            presence: "off"
        target:
            entity_id: climate.thermostat_1
        """
        _LOGGER.info("%s - Calling service_set_presence, presence: %s", self, presence)
        self._update_presence(presence)
        await self._async_control_heating(force=True)

    async def service_set_preset_temperature(
        self, preset, temperature=None, temperature_away=None
    ):
        """Called by a service call:
        service: versatile_thermostat.set_preset_temperature
        data:
            temperature: 17.8
            preset: boost
            temperature_away: 15
        target:
            entity_id: climate.thermostat_2
        """
        _LOGGER.info(
            "%s - Calling service_set_preset_temperature, preset: %s, temperature: %s, temperature_away: %s",
            self,
            preset,
            temperature,
            temperature_away,
        )
        if preset in self._presets:
            if temperature is not None:
                self._presets[preset] = temperature
            if self._presence_on and temperature_away is not None:
                self._presets_away[self.get_preset_away_name(preset)] = temperature_away
        else:
            _LOGGER.warning(
                "%s - No preset %s configured for this thermostat. Ignoring set_preset_temperature call",
                self,
                preset,
            )

        # If the changed preset is active, change the current temperature
        if self._attr_preset_mode == preset:
            await self._async_set_preset_mode_internal(preset, force=True)
            await self._async_control_heating(force=True)

    @classmethod
    def add_entity(cls, entry_id, entity):
        """Adds an entity into the VersatileRegistry entities"""
        _LOGGER.debug("Adding entity %s", entry_id)
        cls._registry[entry_id] = entity
        _LOGGER.debug("Entity registry is now %s", cls._registry)

    @classmethod
    async def update_entity(cls, entry_id, infos):
        """Updates an existing entity referenced by entry_id with the infos in arguments"""
        entity: VersatileThermostat = cls._registry.get(entry_id)
        if entity is None:
            _LOGGER.warning(
                "Tries to update VersatileThermostat entity %s but was not found in thermostat registry",
                entry_id,
            )
            return

        _LOGGER.debug("We have found the entity to update")
        entity.post_init(infos)

        await entity.async_added_to_hass()
