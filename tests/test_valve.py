# pylint: disable=line-too-long, disable=protected-access

""" Test the normal start of a Switch AC Thermostat """
from unittest.mock import patch, call
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, State
from homeassistant.components.climate import HVACAction, HVACMode

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
            VThermPreset.FROST + PRESET_TEMP_SUFFIX: 7,
            VThermPreset.ECO + PRESET_TEMP_SUFFIX: 17,
            VThermPreset.COMFORT + PRESET_TEMP_SUFFIX: 19,
            VThermPreset.BOOST + PRESET_TEMP_SUFFIX: 21,
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
            CONF_MOTION_PRESET: VThermPreset.COMFORT,
            CONF_NO_MOTION_PRESET: VThermPreset.ECO,
            CONF_PRESENCE_SENSOR: "person.presence_sensor",
            VThermPreset.FROST + PRESET_AWAY_SUFFIX + PRESET_TEMP_SUFFIX: 7,
            VThermPreset.ECO + PRESET_AWAY_SUFFIX + PRESET_TEMP_SUFFIX: 17.1,
            VThermPreset.COMFORT + PRESET_AWAY_SUFFIX + PRESET_TEMP_SUFFIX: 17.2,
            VThermPreset.BOOST + PRESET_AWAY_SUFFIX + PRESET_TEMP_SUFFIX: 17.3,
            CONF_PRESET_POWER: 10,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_AC_MODE: False,
        },
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 1. create the entity
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:

        entity = await create_thermostat(hass, entry, "climate.theovervalvemockname")

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
            VThermPreset.NONE,
            VThermPreset.FROST,
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
            VThermPreset.ACTIVITY,
        ]
        assert entity.preset_mode is VThermPreset.NONE
        assert (
            entity.safety_manager.is_safety_detected is False
        )  # pylint: disable=protected-access
        assert entity.window_state is STATE_UNKNOWN
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN
        assert entity._prop_algorithm is not None  # pylint: disable=protected-access
        assert entity.have_valve_regulation is False

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        # assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": HVACMode.OFF},
                ),
            ]
        )

    # 2. Set the HVACMode to HEAT, with manual preset and target_temp to 18 before receiving temperature
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
        assert entity.preset_mode == VThermPreset.NONE  # Manual mode
        assert entity.target_temperature == 18
        # Nothing have changed cause we don't have room and external temperature
        assert mock_send_event.call_count == 1

    # 3. Set temperature and external temperature
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
                    domain="number",
                    service="set_value",
                    service_data={"value": 90},
                    target={"entity_id": "number.mock_valve"},
                    # {"entity_id": "number.mock_valve", "value": 90},
                ),
                call.async_call(
                    domain="number",
                    service="set_value",
                    service_data={"value": 98},
                    target={"entity_id": "number.mock_valve"},
                    # {"entity_id": "number.mock_valve", "value": 98},
                ),
            ]
        )

        assert mock_send_event.call_count == 0

        # Change to preset Comfort
        # Change presence to off
        event_timestamp = now - timedelta(minutes=4)
        await send_presence_change_event(entity, False, True, event_timestamp)
        await entity.async_set_preset_mode(preset_mode=VThermPreset.COMFORT)
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 17.2  # Comfort with presence off
        assert entity.valve_open_percent == 73
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

        # Change presence to on
        event_timestamp = now - timedelta(minutes=3)
        await send_presence_change_event(entity, True, False, event_timestamp)
        assert entity.presence_state == STATE_ON  # pylint: disable=protected-access
        assert entity.preset_mode is VThermPreset.COMFORT
        assert entity.target_temperature == 19
        assert entity.valve_open_percent == 100  # Full heating
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

    # 4. Change internal temperature
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
        event_timestamp = now - timedelta(minutes=2)
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
                    domain="number",
                    service="set_value",
                    service_data={"value": 10},
                    target={"entity_id": "number.mock_valve"},
                )
            ]
        )

        await send_temperature_change_event(entity, 17, datetime.now())
        assert mock_service_call.call_count == 2
        # The VTherm valve is 0, but the underlying have received 10 which is the min
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    domain="number",
                    service="set_value",
                    service_data={"value": 10},
                    target={"entity_id": "number.mock_valve"},  # the min allowed value
                ),
                call.async_call(
                    domain="number",
                    service="set_value",
                    service_data={
                        "value": 34
                    },  # 34 is 50 x open_percent (69%) and is the max allowed value
                    target={"entity_id": "number.mock_valve"},
                ),
            ]
        )
        # switch to Eco
        await entity.async_set_preset_mode(VThermPreset.ECO)
        assert entity.preset_mode is VThermPreset.ECO
        assert entity.target_temperature == 17
        assert entity.valve_open_percent == 7

        # Unset the presence
        event_timestamp = now - timedelta(minutes=1)
        await send_presence_change_event(entity, False, True, event_timestamp)
        assert entity.presence_state == STATE_OFF  # pylint: disable=protected-access
        assert entity.valve_open_percent == 10
        assert entity.target_temperature == 17.1  # eco_away
        assert entity.is_device_active is True
        assert entity.hvac_action == HVACAction.HEATING

    # 5. Test window open/close (with a normal min/max so that is_device_active is False when open_percent is 0)
    expected_state = State(
        entity_id="number.mock_valve", state="0", attributes={"min": 0, "max": 255}
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
            VThermPreset.FROST + PRESET_TEMP_SUFFIX: 7,
            VThermPreset.ECO + PRESET_TEMP_SUFFIX: 17,
            VThermPreset.COMFORT + PRESET_TEMP_SUFFIX: 19,
            VThermPreset.BOOST + PRESET_TEMP_SUFFIX: 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 60,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
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
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 21
        # the preset have changed
        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.PRESET_EVENT,
                    {"preset": VThermPreset.BOOST},
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
                    domain="number",
                    service="set_value",
                    service_data={"value": 90},
                    target={"entity_id": "number.mock_valve"},
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
                    domain="number",
                    service="set_value",
                    service_data={"value": 96},
                    target={"entity_id": "number.mock_valve"},
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


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_533(
    hass: HomeAssistant, skip_hass_states_is_state
):  # pylint: disable=unused-argument
    """Test that with an over_valve and _auto_regulation_dpercent is set that the valve could close totally"""

    # vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # The temperatures to set
    temps = {
        "frost": 7.0,
        "eco": 17.0,
        "comfort": 19.0,
        "boost": 21.0,
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverValveMockName",
        unique_id="overValveUniqueId",
        data={
            CONF_NAME: "overValve",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_VALVE: "number.mock_valve",
            CONF_AUTO_REGULATION_DTEMP: 10,  # This parameter makes the bug
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 60,
        },
        # | temps,
    )

    # Not used because number is not registred so we can use directly the underlying number
    # fake_underlying_number = MockNumber(
    #     hass=hass, unique_id="mock_number", name="mock_number"
    # )

    vtherm: ThermostatOverValve = await create_thermostat(
        hass, config_entry, "climate.overvalve"
    )

    assert vtherm is not None

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # Set all temps and check they are correctly initialized
    await set_all_climate_preset_temp(hass, vtherm, temps, "overvalve")
    await send_temperature_change_event(vtherm, 15, now)
    await send_ext_temperature_change_event(vtherm, 15, now)

    # 1. Set mode to Heat and preset to Comfort
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    with patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(
            entity_id="number.mock_valve",
            state="100",
            attributes={"min": 0, "max": 100},
        ),
    ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        await vtherm.async_set_preset_mode(VThermPreset.COMFORT)
        await hass.async_block_till_done()

        assert vtherm.target_temperature == 19.0
        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    domain="number",
                    service="set_value",
                    service_data={"value": 100},
                    target={"entity_id": "number.mock_valve"},
                ),
            ]
        )

    # 2. set current temperature to 18 -> still 50% open, so there is a call
    now = now + timedelta(minutes=1)
    with patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(
            entity_id="number.mock_valve",
            state="100",
            attributes={"min": 0, "max": 100},
        ),
    ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        await send_temperature_change_event(vtherm, 18, now)
        await hass.async_block_till_done()

        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    domain="number",
                    service="set_value",
                    service_data={"value": 50},
                    target={"entity_id": "number.mock_valve"},
                ),
            ]
        )

    # 3. set current temperature to 18.8 -> still 10% open, so there is one call
    now = now + timedelta(minutes=1)
    with patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(
            entity_id="number.mock_valve",
            state="50",
            attributes={"min": 0, "max": 100},
        ),
    ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        await send_temperature_change_event(vtherm, 18.8, now)
        await hass.async_block_till_done()

        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    domain="number",
                    service="set_value",
                    service_data={"value": 10},
                    target={"entity_id": "number.mock_valve"},
                ),
            ]
        )

    # 4. set current temperature to 19 -> should have 0% open and one call to set the 0
    now = now + timedelta(minutes=1)
    with patch(
        "homeassistant.core.StateMachine.get",
        return_value=State(
            entity_id="number.mock_valve",
            state="10",  # the previous value
            attributes={"min": 0, "max": 100},
        ),
    ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        await send_temperature_change_event(vtherm, 19, now)
        await hass.async_block_till_done()

        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    domain="number",
                    service="set_value",
                    service_data={"value": 0},
                    target={"entity_id": "number.mock_valve"},
                ),
            ]
        )
