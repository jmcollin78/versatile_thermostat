# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

""" Test the over_climate with valve regulation """
from unittest.mock import patch, call
from datetime import datetime, timedelta

import logging

from homeassistant.core import HomeAssistant, State

from custom_components.versatile_thermostat.thermostat_climate_valve import (
    ThermostatOverClimateValve,
)

from .commons import *
from .const import *

logging.getLogger().setLevel(logging.DEBUG)


# @pytest.mark.parametrize("expected_lingering_tasks", [True])
# @pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_valve_mono(hass: HomeAssistant, skip_hass_states_get):
    """Test the normal full start of a thermostat in thermostat_over_climate type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: ["number.mock_opening_degree"],
            CONF_CLOSING_DEGREE_LIST: ["number.mock_closing_degree"],
            CONF_OFFSET_CALIBRATION_LIST: ["number.mock_offset_calibration"],
        }
        | MOCK_DEFAULT_FEATURE_CONFIG
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {})

    # mock_get_state will be called for each OPENING/CLOSING/OFFSET_CALIBRATION list

    mock_get_state_side_effect = SideEffects(
        {
            "number.mock_opening_degree": State(
                "number.mock_opening_degree", "0", {"min": 0, "max": 100}
            ),
            "number.mock_closing_degree": State(
                "number.mock_closing_degree", "0", {"min": 0, "max": 100}
            ),
            "number.mock_offset_calibration": State(
                "number.mock_offset_calibration", "0", {"min": -12, "max": 12}
            ),
        },
        State("unknown.entity_id", "unknown"),
    )

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate", return_value=fake_underlying_climate) as mock_find_climate, \
        patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()) as mock_get_state:
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert vtherm
        vtherm._set_now(now)
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True

        assert vtherm.hvac_action is HVACAction.OFF
        assert vtherm.hvac_mode is HVACMode.OFF
        assert vtherm.target_temperature == vtherm.min_temp
        assert vtherm.preset_modes == [
            PRESET_NONE,
            PRESET_FROST_PROTECTION,
            PRESET_ECO,
            PRESET_COMFORT,
            PRESET_BOOST,
        ]
        assert vtherm.preset_mode is PRESET_NONE
        assert vtherm._security_state is False
        assert vtherm._window_state is None
        assert vtherm._motion_state is None
        assert vtherm._presence_state is None

        assert vtherm.is_device_active is False
        assert vtherm.valve_open_percent == 0

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

        mock_find_climate.assert_called_once()
        mock_find_climate.assert_has_calls([call.find_underlying_vtherm()])

        # the underlying set temperature call but no call to valve yet because VTherm is off
        assert mock_service_call.call_count == 3
        mock_service_call.assert_has_calls(
            [
                call("climate","set_temperature",{
                        "entity_id": "climate.mock_climate",
                        "temperature": 15,  # temp-min
                    },
                ),
                call(domain='number', service='set_value', service_data={'value': 0}, target={'entity_id': 'number.mock_opening_degree'}),
                call(domain='number', service='set_value', service_data={'value': 100}, target={'entity_id': 'number.mock_closing_degree'}),
                # we have no current_temperature yet
                # call(domain='number', service='set_value', service_data={'value': 12}, target={'entity_id': 'number.mock_offset_calibration'}),
            ]
        )

        assert mock_get_state.call_count > 5  # each temp sensor + each valve


        # initialize the temps
        await set_all_climate_preset_temp(hass, vtherm, None, "theoverclimatemockname")

        await send_temperature_change_event(vtherm, 18, now, True)
        await send_ext_temperature_change_event(vtherm, 18, now, True)

    # 2. Starts heating slowly (18 vs 19)
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()) as mock_get_state:
    # fmt: on
        now = now + timedelta(minutes=2) # avoid temporal filter
        vtherm._set_now(now)

        await vtherm.async_set_preset_mode(PRESET_COMFORT)
        await hass.async_block_till_done()

        assert vtherm.hvac_mode is HVACMode.HEAT
        assert vtherm.preset_mode is PRESET_COMFORT
        assert vtherm.target_temperature == 19
        assert vtherm.current_temperature == 18
        assert vtherm.valve_open_percent == 40 # 0.3*1 + 0.1*1


        assert mock_service_call.call_count == 4
        mock_service_call.assert_has_calls(
            [
                call('climate', 'set_temperature', {'entity_id': 'climate.mock_climate', 'temperature': 19.0}),
                call(domain='number', service='set_value', service_data={'value': 40}, target={'entity_id': 'number.mock_opening_degree'}),
                call(domain='number', service='set_value', service_data={'value': 60}, target={'entity_id': 'number.mock_closing_degree'}),
                # 3 = 18 (room) - 15 (current of underlying) + 0 (current offset)
                call(domain='number', service='set_value', service_data={'value': 3.0}, target={'entity_id': 'number.mock_offset_calibration'})
            ]
        )

        # set the opening to 40%
        mock_get_state_side_effect.add_or_update_side_effect(
            "number.mock_opening_degree",
            State(
                "number.mock_opening_degree", "40", {"min": 0, "max": 100}
            ))

        assert vtherm.hvac_action is HVACAction.HEATING
        assert vtherm.is_device_active is True

    # 2. Starts heating very slowly (18.9 vs 19)
    now = now + timedelta(minutes=2)
    vtherm._set_now(now)
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()) as mock_get_state:
    # fmt: on
        # set the offset to 3
        mock_get_state_side_effect.add_or_update_side_effect(
            "number.mock_offset_calibration",
            State(
                "number.mock_offset_calibration", "3", {"min": -12, "max": 12}
            ))

        await send_temperature_change_event(vtherm, 18.9, now, True)
        await hass.async_block_till_done()

        assert vtherm.hvac_mode is HVACMode.HEAT
        assert vtherm.preset_mode is PRESET_COMFORT
        assert vtherm.target_temperature == 19
        assert vtherm.current_temperature == 18.9
        assert vtherm.valve_open_percent == 13 # 0.3*0.1 + 0.1*1


        assert mock_service_call.call_count == 3
        mock_service_call.assert_has_calls(
            [
                call(domain='number', service='set_value', service_data={'value': 13}, target={'entity_id': 'number.mock_opening_degree'}),
                call(domain='number', service='set_value', service_data={'value': 87}, target={'entity_id': 'number.mock_closing_degree'}),
                # 6 = 18 (room) - 15 (current of underlying) + 3 (current offset)
                call(domain='number', service='set_value', service_data={'value': 6.899999999999999}, target={'entity_id': 'number.mock_offset_calibration'})
            ]
        )

        # set the opening to 13%
        mock_get_state_side_effect.add_or_update_side_effect(
            "number.mock_opening_degree",
            State(
                "number.mock_opening_degree", "13", {"min": 0, "max": 100}
            ))

        assert vtherm.hvac_action is HVACAction.HEATING
        assert vtherm.is_device_active is True

    # 3. Stop heating 21 > 19
    now = now + timedelta(minutes=2)
    vtherm._set_now(now)
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()) as mock_get_state:
    # fmt: on
        # set the offset to 3
        mock_get_state_side_effect.add_or_update_side_effect(
            "number.mock_offset_calibration",
            State(
                "number.mock_offset_calibration", "3", {"min": -12, "max": 12}
            ))

        await send_temperature_change_event(vtherm, 21, now, True)
        await hass.async_block_till_done()

        assert vtherm.hvac_mode is HVACMode.HEAT
        assert vtherm.preset_mode is PRESET_COMFORT
        assert vtherm.target_temperature == 19
        assert vtherm.current_temperature == 21
        assert vtherm.valve_open_percent == 0 # 0.3* (-2) + 0.1*1


        assert mock_service_call.call_count == 3
        mock_service_call.assert_has_calls(
            [
                call(domain='number', service='set_value', service_data={'value': 0}, target={'entity_id': 'number.mock_opening_degree'}),
                call(domain='number', service='set_value', service_data={'value': 100}, target={'entity_id': 'number.mock_closing_degree'}),
                # 6 = 18 (room) - 15 (current of underlying) + 3 (current offset)
                call(domain='number', service='set_value', service_data={'value': 9.0}, target={'entity_id': 'number.mock_offset_calibration'})
            ]
        )

        # set the opening to 13%
        mock_get_state_side_effect.add_or_update_side_effect(
            "number.mock_opening_degree",
            State(
                "number.mock_opening_degree", "0", {"min": 0, "max": 100}
            ))

        assert vtherm.hvac_action is HVACAction.OFF
        assert vtherm.is_device_active is False



    await hass.async_block_till_done()


async def test_over_climate_valve_multi_presence(
    hass: HomeAssistant, skip_hass_states_get
):
    """Test the normal full start of a thermostat in thermostat_over_climate type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_UNDERLYING_LIST: ["climate.mock_climate1", "climate.mock_climate2"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: [
                "number.mock_opening_degree1",
                "number.mock_opening_degree2",
            ],
            CONF_CLOSING_DEGREE_LIST: [
                "number.mock_closing_degree1",
                "number.mock_closing_degree2",
            ],
            CONF_OFFSET_CALIBRATION_LIST: [
                "number.mock_offset_calibration1",
                "number.mock_offset_calibration2",
            ],
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
        }
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    fake_underlying_climate1 = MockClimate(
        hass, "mockUniqueId1", "MockClimateName1", {}
    )
    fake_underlying_climate2 = MockClimate(
        hass, "mockUniqueId2", "MockClimateName2", {}
    )

    # mock_get_state will be called for each OPENING/CLOSING/OFFSET_CALIBRATION list
    mock_get_state_side_effect = SideEffects(
        {
            # Valve 1 is open
            "number.mock_opening_degree1": State(
                "number.mock_opening_degree1", "10", {"min": 0, "max": 100}
            ),
            "number.mock_closing_degree1": State(
                "number.mock_closing_degree1", "90", {"min": 0, "max": 100}
            ),
            "number.mock_offset_calibration1": State(
                "number.mock_offset_calibration1", "0", {"min": -12, "max": 12}
            ),
            # Valve 2 is closed
            "number.mock_opening_degree2": State(
                "number.mock_opening_degree2", "0", {"min": 0, "max": 100}
            ),
            "number.mock_closing_degree2": State(
                "number.mock_closing_degree2", "100", {"min": 0, "max": 100}
            ),
            "number.mock_offset_calibration2": State(
                "number.mock_offset_calibration2", "10", {"min": -12, "max": 12}
            ),
        },
        State("unknown.entity_id", "unknown"),
    )

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate", side_effect=[fake_underlying_climate1, fake_underlying_climate2]) as mock_find_climate, \
        patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()) as mock_get_state:
    # fmt: on

        vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        assert vtherm
        assert isinstance(vtherm, ThermostatOverClimateValve)

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.have_valve_regulation is True

        vtherm._set_now(now)

        # initialize the temps
        await set_all_climate_preset_temp(hass, vtherm, default_temperatures_away, "theoverclimatemockname")

        await send_temperature_change_event(vtherm, 18, now, True)
        await send_ext_temperature_change_event(vtherm, 18, now, True)
        await send_presence_change_event(vtherm, False, True, now)

        await vtherm.async_set_preset_mode(PRESET_COMFORT)
        await vtherm.async_set_hvac_mode(HVACMode.HEAT)

        assert vtherm.target_temperature == 17.2

    # 2: set presence on -> should activate the valve and change target
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()) as mock_get_state:
    # fmt: on
        now = now + timedelta(minutes=3)
        vtherm._set_now(now)

        await send_presence_change_event(vtherm, True, False, now)
        await hass.async_block_till_done()

        assert vtherm.is_device_active is True
        assert vtherm.valve_open_percent == 40

        # the underlying set temperature call and the call to the valve
        assert mock_service_call.call_count == 8
        mock_service_call.assert_has_calls([
            call('climate', 'set_temperature', {'entity_id': 'climate.mock_climate1', 'temperature': 19.0}),
            call('climate', 'set_temperature', {'entity_id': 'climate.mock_climate2', 'temperature': 19.0}),
            call(domain='number', service='set_value', service_data={'value': 40}, target={'entity_id': 'number.mock_opening_degree1'}),
            call(domain='number', service='set_value', service_data={'value': 60}, target={'entity_id': 'number.mock_closing_degree1'}),
            call(domain='number', service='set_value', service_data={'value': 3.0}, target={'entity_id': 'number.mock_offset_calibration1'}),
            call(domain='number', service='set_value', service_data={'value': 40}, target={'entity_id': 'number.mock_opening_degree2'}),
            call(domain='number', service='set_value', service_data={'value': 60}, target={'entity_id': 'number.mock_closing_degree2'}),
            call(domain='number', service='set_value', service_data={'value': 12}, target={'entity_id': 'number.mock_offset_calibration2'})
            ]
        )

    # 3: set presence off -> should deactivate the valve and change target
    # fmt: off
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call,\
        patch("homeassistant.core.StateMachine.get", side_effect=mock_get_state_side_effect.get_side_effects()) as mock_get_state:
    # fmt: on
        now = now + timedelta(minutes=3)
        vtherm._set_now(now)

        await send_presence_change_event(vtherm, False, True, now)
        await hass.async_block_till_done()

        assert vtherm.is_device_active is False
        assert vtherm.valve_open_percent == 0

        # the underlying set temperature call and the call to the valve
        assert mock_service_call.call_count == 8
        mock_service_call.assert_has_calls([
            call('climate', 'set_temperature', {'entity_id': 'climate.mock_climate1', 'temperature': 17.2}),
            call('climate', 'set_temperature', {'entity_id': 'climate.mock_climate2', 'temperature': 17.2}),
            call(domain='number', service='set_value', service_data={'value': 0}, target={'entity_id': 'number.mock_opening_degree1'}),
            call(domain='number', service='set_value', service_data={'value': 100}, target={'entity_id': 'number.mock_closing_degree1'}),
            call(domain='number', service='set_value', service_data={'value': 3.0}, target={'entity_id': 'number.mock_offset_calibration1'}),
            call(domain='number', service='set_value', service_data={'value': 0}, target={'entity_id': 'number.mock_opening_degree2'}),
            call(domain='number', service='set_value', service_data={'value': 100}, target={'entity_id': 'number.mock_closing_degree2'}),
            call(domain='number', service='set_value', service_data={'value': 12}, target={'entity_id': 'number.mock_offset_calibration2'})
            ]
        )
