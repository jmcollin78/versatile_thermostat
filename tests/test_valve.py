# pylint: disable=line-too-long, disable=protected-access

""" Test the normal start of a Switch AC Thermostat """
from unittest.mock import patch, call
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, State
from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntryState

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.thermostat_valve import ThermostatOverValve

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_valve_full_start(
    hass: HomeAssistant, skip_hass_states_is_state
):  # pylint: disable=unused-argument
    """Test the normal full start of a thermostat in thermostat_over_switch type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverValveMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverValveMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_VALVE: "number.mock_valve",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            PRESET_FROST_PROTECTION + "_temp": 7,
            PRESET_ECO + "_temp": 17,
            PRESET_COMFORT + "_temp": 19,
            PRESET_BOOST + "_temp": 21,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MOTION_SENSOR: "input_boolean.motion_sensor",
            CONF_WINDOW_SENSOR: "binary_sensor.window_sensor",
            CONF_WINDOW_DELAY: 10,
            CONF_MOTION_DELAY: 10,
            CONF_MOTION_OFF_DELAY: 30,
            CONF_MOTION_PRESET: PRESET_COMFORT,
            CONF_NO_MOTION_PRESET: PRESET_ECO,
            CONF_POWER_SENSOR: "sensor.power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.power_max_sensor",
            CONF_PRESENCE_SENSOR: "person.presence_sensor",
            PRESET_FROST_PROTECTION + PRESET_AWAY_SUFFIX + "_temp": 7,
            PRESET_ECO + PRESET_AWAY_SUFFIX + "_temp": 17.1,
            PRESET_COMFORT + PRESET_AWAY_SUFFIX + "_temp": 17.2,
            PRESET_BOOST + PRESET_AWAY_SUFFIX + "_temp": 17.3,
            CONF_PRESET_POWER: 10,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_AC_MODE: False,
        },
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        def find_my_entity(entity_id) -> ClimateEntity:
            """Find my new entity"""
            component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
            for entity in component.entities:
                if entity.entity_id == entity_id:
                    return entity

        # The name is in the CONF and not the title of the entry
        entity: ThermostatOverValve = find_my_entity("climate.theovervalvemockname")

        assert entity
        assert isinstance(entity, ThermostatOverValve)

        assert entity.name == "TheOverValveMockName"
        assert entity.is_over_climate is False
        assert entity.is_over_switch is False
        assert entity.is_over_valve is True
        assert entity.ac_mode is False
        assert entity.hvac_mode is HVACMode.OFF
        assert entity.hvac_action is HVACAction.OFF
        assert entity.hvac_modes == [HVACMode.HEAT, HVACMode.OFF]
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            PRESET_NONE,
            PRESET_FROST_PROTECTION,
            PRESET_ECO,
            PRESET_COMFORT,
            PRESET_BOOST,
            PRESET_ACTIVITY,
        ]
        assert entity.preset_mode is PRESET_NONE
        assert entity._security_state is False  # pylint: disable=protected-access
        assert entity._window_state is None  # pylint: disable=protected-access
        assert entity._motion_state is None  # pylint: disable=protected-access
        assert entity._presence_state is None  # pylint: disable=protected-access
        assert entity._prop_algorithm is not None  # pylint: disable=protected-access

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": HVACMode.OFF},
                ),
            ]
        )

    # Set the HVACMode to HEAT, with manual preset and target_temp to 18 before receiving temperature
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        #
        assert entity.hvac_mode is HVACMode.HEAT
        # No heating now
        assert entity.valve_open_percent == 0
        assert entity.hvac_action == HVACAction.IDLE
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": HVACMode.HEAT},
                ),
            ]
        )

        # set manual target temp
        await entity.async_set_temperature(temperature=18)
        assert entity.preset_mode == PRESET_NONE  # Manual mode
        assert entity.target_temperature == 18
        # Nothing have changed cause we don't have room and external temperature
        assert mock_send_event.call_count == 1

    # Set temperature and external temperature
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(entity_id="number.mock_valve", state="90"),
    ):
        # Change temperature
        event_timestamp = now - timedelta(minutes=10)
        await send_temperature_change_event(entity, 15, datetime.now())
        assert entity.valve_open_percent == 90
        await send_ext_temperature_change_event(entity, 10, datetime.now())
        # Should heating strongly now
        assert entity.valve_open_percent == 98
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count == 2
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    "number",
                    "set_value",
                    {"entity_id": "number.mock_valve", "value": 90},
                ),
                call.async_call(
                    "number",
                    "set_value",
                    {"entity_id": "number.mock_valve", "value": 98},
                ),
            ]
        )

        assert mock_send_event.call_count == 0

        # Change to preset Comfort
        await entity.async_set_preset_mode(preset_mode=PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT
        assert entity.target_temperature == 17.2
        assert entity.valve_open_percent == 73
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

        # Change presence to on
        event_timestamp = now - timedelta(minutes=4)
        await send_presence_change_event(entity, True, False, event_timestamp)
        assert entity.presence_state == STATE_ON  # pylint: disable=protected-access
        assert entity.preset_mode is PRESET_COMFORT
        assert entity.target_temperature == 19
        assert entity.valve_open_percent == 100  # Full heating
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

    # Change internal temperature
    expected_state = State(
        entity_id="number.mock_valve", state="0", attributes={"min": 10, "max": 50}
    )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "homeassistant.core.StateMachine.get", return_value=expected_state
    ):
        event_timestamp = now - timedelta(minutes=3)
        await send_temperature_change_event(entity, 20, datetime.now())
        assert entity.valve_open_percent == 0
        assert entity.is_device_active is True  # Should be 0 but in fact 10 is send
        assert (
            entity.hvac_action == HVACAction.HEATING
        )  # Should be IDLE but heating due to 10

        assert mock_service_call.call_count == 1
        # The VTherm valve is 0, but the underlying have received 10 which is the min
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    "number",
                    "set_value",
                    {"entity_id": "number.mock_valve", "value": 10},
                )
            ]
        )

        await send_temperature_change_event(entity, 17, datetime.now())
        assert mock_service_call.call_count == 2
        # The VTherm valve is 0, but the underlying have received 10 which is the min
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    "number",
                    "set_value",
                    {
                        "entity_id": "number.mock_valve",
                        "value": 10,
                    },  # the min allowed value
                ),
                call.async_call(
                    "number",
                    "set_value",
                    {
                        "entity_id": "number.mock_valve",
                        "value": 50,
                    },  # the max allowed value
                ),
            ]
        )
        # switch to Eco
        await entity.async_set_preset_mode(PRESET_ECO)
        assert entity.preset_mode is PRESET_ECO
        assert entity.target_temperature == 17
        assert entity.valve_open_percent == 7

        # Unset the presence
        event_timestamp = now - timedelta(minutes=2)
        await send_presence_change_event(entity, False, True, event_timestamp)
        assert entity.presence_state == STATE_OFF  # pylint: disable=protected-access
        assert entity.valve_open_percent == 10
        assert entity.target_temperature == 17.1  # eco_away
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

    # Test window open/close (with a normal min/max so that is_device_active is False when open_percent is 0)
    expected_state = State(
        entity_id="number.mock_valve", state="0", attributes={"min": 0, "max": 99}
    )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "homeassistant.core.StateMachine.get", return_value=expected_state
    ):
        # Open a window
        with patch("homeassistant.helpers.condition.state", return_value=True):
            event_timestamp = now - timedelta(minutes=1)
            try_condition = await send_window_change_event(
                entity, True, False, event_timestamp
            )

            # Confirme the window event
            await try_condition(None)

            assert entity.hvac_mode is HVACMode.OFF
            assert entity.hvac_action is HVACAction.OFF
            assert entity.target_temperature == 17.1  # eco
            assert entity.valve_open_percent == 0

        # Close a window
        with patch("homeassistant.helpers.condition.state", return_value=True):
            event_timestamp = now - timedelta(minutes=0)
            try_condition = await send_window_change_event(
                entity, False, True, event_timestamp
            )

            # Confirme the window event
            await try_condition(None)

            assert entity.hvac_mode is HVACMode.HEAT
            assert entity.hvac_action is HVACAction.HEATING
            assert entity.target_temperature == 17.1  # eco
            assert entity.valve_open_percent == 10


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_valve_regulation(
    hass: HomeAssistant, skip_hass_states_is_state
):  # pylint: disable=unused-argument
    """Test the normal full start of a thermostat in thermostat_over_switch type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverValveMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverValveMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_VALVE: "number.mock_valve",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            PRESET_FROST_PROTECTION + "_temp": 7,
            PRESET_ECO + "_temp": 17,
            PRESET_COMFORT + "_temp": 19,
            PRESET_BOOST + "_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 60,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            # only send new valve open percent if dtemp is > 30%
            CONF_AUTO_REGULATION_DTEMP: 5,
            # only send new valve open percent last mesure was more than 5 min ago
            CONF_AUTO_REGULATION_PERIOD_MIN: 5,
        },
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 1. prepare the Valve at now
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        entity: ThermostatOverValve = await create_thermostat(
            hass, entry, "climate.theovervalvemockname"
        )
        assert entity
        assert isinstance(entity, ThermostatOverValve)

        assert entity.name == "TheOverValveMockName"
        assert entity.is_over_valve is True
        assert entity._auto_regulation_dpercent == 5
        assert entity._auto_regulation_period_min == 5
        assert entity.target_temperature == entity.min_temp
        assert entity._prop_algorithm is not None

    # 2. Set the HVACMode to HEAT, with manual preset and target_temp to 18 before receiving temperature
    # at now +1
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        now = now + timedelta(minutes=1)
        entity._set_now(now)

        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode is HVACMode.HEAT
        # No heating now
        assert entity.valve_open_percent == 0
        assert entity.hvac_action == HVACAction.IDLE
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": HVACMode.HEAT},
                ),
            ]
        )

    # 3. Set the preset
    # at now +1
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        now = now + timedelta(minutes=1)
        entity._set_now(now)

        # set preset
        await entity.async_set_preset_mode(PRESET_BOOST)
        assert entity.preset_mode == PRESET_BOOST
        assert entity.target_temperature == 21
        # the preset have changed
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.PRESET_EVENT,
                    {"preset": PRESET_BOOST},
                ),
            ]
        )

        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode is HVACMode.HEAT
        # Still no heating because we don't have temperature
        assert entity.valve_open_percent == 0
        assert entity.hvac_action == HVACAction.IDLE

    # 4. Set temperature and external temperature
    # at now + 1 (but the _last_calculation_timestamp is still not send)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(entity_id="number.mock_valve", state="90"),
    ):
        # Change temperature
        now = now + timedelta(minutes=1)
        entity._set_now(now)

        await send_temperature_change_event(entity, 18, now)
        assert entity.valve_open_percent == 90

        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    "number",
                    "set_value",
                    {"entity_id": "number.mock_valve", "value": 90},
                ),
            ]
        )

        assert mock_send_event.call_count == 0

    # 5. Set external temperature
    # at now + 1
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(entity_id="number.mock_valve", state="90"),
    ):
        # Change external temperature
        now = now + timedelta(minutes=1)
        entity._set_now(now)

        await send_ext_temperature_change_event(entity, 10, now)

        # Should not have change due to regulation (period_min !)
        assert entity.valve_open_percent == 90
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count == 0
        assert mock_send_event.call_count == 0

    # 6. Set temperature
    # at now + 5 (to avoid the period_min threshold)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(entity_id="number.mock_valve", state="90"),
    ):
        # Change external temperature
        now = now + timedelta(minutes=5)
        entity._set_now(now)

        await send_ext_temperature_change_event(entity, 15, now)

        # Should have change this time to 96
        assert entity.valve_open_percent == 96
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    "number",
                    "set_value",
                    {"entity_id": "number.mock_valve", "value": 96},
                ),
            ]
        )
        assert mock_send_event.call_count == 0

    # 7. Set small temperature update to test dtemp threshold
    # at now + 5
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(entity_id="number.mock_valve", state="96"),
    ):
        # Change external temperature
        now = now + timedelta(minutes=5)
        entity._set_now(now)

        # this generate a delta percent of -3
        await send_temperature_change_event(entity, 18.1, now)

        # Should not have due to dtemp
        assert entity.valve_open_percent == 96
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

        assert mock_service_call.call_count == 0
        assert mock_send_event.call_count == 0
