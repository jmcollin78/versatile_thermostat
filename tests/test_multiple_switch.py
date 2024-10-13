# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, unused-variable

""" Test the Multiple switch management """
import asyncio
from unittest.mock import patch, call, ANY
from datetime import datetime, timedelta
import logging

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_one_switch_cycle(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
):  # pylint: disable=unused-argument
    """Test that when multiple switch are configured the activation is distributed"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOver4SwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOver4SwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch1",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4switchmockname"
    )
    assert entity
    assert entity.is_over_climate is False

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_BOOST)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_OFF

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

    # Checks that all heaters are off
    with patch(
        "homeassistant.core.StateMachine.is_state", return_value=False
    ) as mock_is_state:
        assert entity.is_device_active is False  # pylint: disable=protected-access

        # Should be call for the Switch
        assert mock_is_state.call_count == 1

    # Set temperature to a low level
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ) as mock_device_active, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.call_later",
        return_value=None,
    ) as mock_call_later:
        await send_ext_temperature_change_event(entity, 5, event_timestamp)

        # No special event
        assert mock_send_event.call_count == 0
        assert mock_heater_off.call_count == 0

        # The first heater should be on but because call_later is mocked heater_on is not called
        # assert mock_heater_on.call_count == 1
        assert mock_heater_on.call_count == 0
        # There is no check if active
        assert mock_device_active.call_count == 0

        # 4 calls dispatched along the cycle
        assert mock_call_later.call_count == 1
        mock_call_later.assert_has_calls(
            [
                call.call_later(hass, 0.0, ANY),
            ]
        )

    # Set a temperature at middle level
    event_timestamp = now - timedelta(minutes=4)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ) as mock_device_active:
        await send_temperature_change_event(entity, 18, event_timestamp)

        # No special event
        assert mock_send_event.call_count == 0
        assert mock_heater_off.call_count == 0

        # The first heater should be turned on but is already on but because above we mock
        # call_later the heater is not on. But this time it will be really on
        assert mock_heater_on.call_count == 1

    # Set another temperature at middle level
    event_timestamp = now - timedelta(minutes=3)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ) as mock_device_active:
        await send_temperature_change_event(entity, 18.1, event_timestamp)

        # No special event
        assert mock_send_event.call_count == 0
        assert mock_heater_off.call_count == 0

        # The heater is already on cycle. So we wait that the cycle ends and no heater action
        # is done
        assert mock_heater_on.call_count == 0
        # assert entity.underlying_entity(0)._should_relaunch_control_heating is True

        # Simulate the relaunch
        await entity.underlying_entity(
            0
        )._turn_on_later(  # pylint: disable=protected-access
            None
        )
        # wait restart
        await asyncio.sleep(0.1)

        assert mock_heater_on.call_count == 1
        # normal ? assert entity.underlying_entity(0)._should_relaunch_control_heating is False

    # Simulate the end of heater on cycle
    event_timestamp = now - timedelta(minutes=3)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ) as mock_device_active:
        await entity.underlying_entity(
            0
        )._turn_off_later(  # pylint: disable=protected-access
            None
        )

        # No special event
        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        # The heater should be turned off this time
        assert mock_heater_off.call_count == 1
        # assert entity.underlying_entity(0)._should_relaunch_control_heating is False

    # Simulate the start of heater on cycle
    event_timestamp = now - timedelta(minutes=3)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ) as mock_device_active:
        await entity.underlying_entity(
            0
        )._turn_on_later(  # pylint: disable=protected-access
            None
        )

        # No special event
        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 1
        # The heater should be turned off this time
        assert mock_heater_off.call_count == 0
        # assert entity.underlying_entity(0)._should_relaunch_control_heating is False


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_multiple_switchs(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
):  # pylint: disable=unused-argument
    """Test that when multiple switch are configured the activation is distributed"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOver4SwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOver4SwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch1",
            CONF_HEATER_2: "switch.mock_switch2",
            CONF_HEATER_3: "switch.mock_switch3",
            CONF_HEATER_4: "switch.mock_switch4",
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4switchmockname"
    )
    assert entity
    assert entity.is_over_climate is False
    assert entity.nb_underlying_entities == 4

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_BOOST)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_OFF

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        # Checks that all climates are off
        assert entity.is_device_active is False  # pylint: disable=protected-access

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.HEAT),
            ]
        )

    # Set temperature to a low level
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ) as mock_device_active, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.call_later",
        return_value=None,
    ) as mock_call_later:
        await send_ext_temperature_change_event(entity, 5, event_timestamp)

        # No special event
        assert mock_send_event.call_count == 0
        assert mock_heater_off.call_count == 0

        # The first heater should be on but because call_later is mocked heater_on is not called
        # assert mock_heater_on.call_count == 1
        assert mock_heater_on.call_count == 0
        # There is no check if active
        assert mock_device_active.call_count == 0

        # 4 calls dispatched along the cycle
        assert mock_call_later.call_count == 4
        mock_call_later.assert_has_calls(
            [
                call.call_later(hass, 0.0, ANY),
                call.call_later(hass, 120.0, ANY),
                call.call_later(hass, 240.0, ANY),
                call.call_later(hass, 360.0, ANY),
            ]
        )

    # Set a temperature at middle level
    event_timestamp = now - timedelta(minutes=4)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ) as mock_device_active:
        await send_temperature_change_event(entity, 18, event_timestamp)

        # No special event
        assert mock_send_event.call_count == 0
        assert mock_heater_off.call_count == 0

        # The first heater should be turned on but is already on but because call_later
        # is mocked, it is only turned on here
        assert mock_heater_on.call_count == 1


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_multiple_climates(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
):  # pylint: disable=unused-argument
    """Test that when multiple climates are configured the activation and deactivation
    is propagated to all climates"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOver4ClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOver4ClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_CLIMATE: "switch.mock_climate1",
            CONF_CLIMATE_2: "switch.mock_climate2",
            CONF_CLIMATE_3: "switch.mock_climate3",
            CONF_CLIMATE_4: "switch.mock_climate4",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4climatemockname"
    )
    assert entity
    assert entity.is_over_climate is True
    assert entity.nb_underlying_entities == 4

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_BOOST)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_OFF

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.HEAT),
            ]
        )
        assert entity.is_device_active is False  # pylint: disable=protected-access

    # Stop heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(HVACMode.OFF)

        assert entity.hvac_mode is HVACMode.OFF
        assert entity.preset_mode is PRESET_BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_OFF

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.OFF),
            ]
        )
        assert entity.is_device_active is False  # pylint: disable=protected-access


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_multiple_climates_underlying_changes(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
):  # pylint: disable=unused-argument
    """Test that when multiple climate are configured the activation of one underlying
    climate activate the others"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOver4ClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOver4ClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_CLIMATE: "switch.mock_climate1",
            CONF_CLIMATE_2: "switch.mock_climate2",
            CONF_CLIMATE_3: "switch.mock_climate3",
            CONF_CLIMATE_4: "switch.mock_climate4",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4climatemockname"
    )
    assert entity
    assert entity.is_over_climate is True
    assert entity.nb_underlying_entities == 4

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_BOOST)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_OFF

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.HEAT),
            ]
        )
        assert entity.is_device_active is False  # pylint: disable=protected-access

    # Stop heating on one underlying climate
    # All underlying supposed to be aligned with the hvac_mode now
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.hvac_mode",
        HVACMode.HEAT,
    ):
        # Wait 11 sec so that the event will not be discarded
        event_timestamp = now + timedelta(seconds=11)
        await send_climate_change_event(
            entity,
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACAction.OFF,
            HVACAction.HEATING,
            event_timestamp,
            underlying_entity_id="switch.mock_climate3",
        )

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.OFF),
            ]
        )
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.is_device_active is False  # pylint: disable=protected-access

    # Start heating on one underlying climate
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode, patch(
        # notice that there is no need of return_value=HVACAction.IDLE because this is not
        # a function but a property
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.hvac_action",
        HVACAction.IDLE,
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.hvac_mode",
        HVACMode.OFF,
    ):
        # Wait 11 sec so that the event will not be discarded
        event_timestamp = now + timedelta(seconds=11)
        await send_climate_change_event(
            entity,
            HVACMode.HEAT,
            HVACMode.OFF,
            HVACAction.IDLE,
            HVACAction.OFF,
            event_timestamp,
            underlying_entity_id="switch.mock_climate3",
        )

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.HEAT),
            ]
        )
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.hvac_action == HVACAction.IDLE
        assert entity.is_device_active is False  # pylint: disable=protected-access


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_multiple_climates_underlying_changes_not_aligned(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
):  # pylint: disable=unused-argument
    """Test that when multiple climate are configured the activation of one underlying
    climate don't activate the others if their havc_mode are not aligned"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOver4ClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOver4ClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_CLIMATE: "switch.mock_climate1",
            CONF_CLIMATE_2: "switch.mock_climate2",
            CONF_CLIMATE_3: "switch.mock_climate3",
            CONF_CLIMATE_4: "switch.mock_climate4",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4climatemockname"
    )
    assert entity
    assert entity.is_over_climate is True
    assert entity.nb_underlying_entities == 4

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_BOOST)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_OFF

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.HEAT),
            ]
        )

    # Stop heating on one underlying climate
    # All underlying supposed to be aligned with the hvac_mode now
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.hvac_mode",
        HVACMode.COOL,
    ):
        # Wait 11 sec so that the event will not be discarded
        event_timestamp = now + timedelta(seconds=11)
        await send_climate_change_event(
            entity,
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACAction.OFF,
            HVACAction.HEATING,
            event_timestamp,
            underlying_entity_id="switch.mock_climate3",
        )

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 0
        # mock_underlying_set_hvac_mode.assert_has_calls(
        #     [
        #         call.set_hvac_mode(HVACMode.OFF),
        #     ]
        # )
        # No change
        assert entity.hvac_mode == HVACMode.HEAT


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_multiple_switch_power_management(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Power management"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOver4SwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch1",
            CONF_HEATER_2: "switch.mock_switch2",
            CONF_HEATER_3: "switch.mock_switch3",
            CONF_HEATER_4: "switch.mock_switch4",
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_POWER_SENSOR: "sensor.mock_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.mock_power_max_sensor",
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4switchmockname"
    )
    assert entity
    assert entity.is_over_climate is False
    assert entity.nb_underlying_entities == 4

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 19

    # 1. Send power mesurement
    await send_power_change_event(entity, 50, datetime.now())
    # Send power max mesurement
    await send_max_power_change_event(entity, 300, datetime.now())
    assert await entity.check_overpowering() is False
    # All configuration is complete and power is < power_max
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is False

    # 2. Send power max mesurement too low and HVACMode is on
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off:
        # 100 of the device / 4 -> 25, current power 50 so max is 75
        await send_max_power_change_event(entity, 74, datetime.now())
        assert await entity.check_overpowering() is True
        # All configuration is complete and power is > power_max we switch to POWER preset
        assert entity.preset_mode is PRESET_POWER
        assert entity.overpowering_state is True
        assert entity.target_temperature == 12

        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_POWER}),
                call.send_event(
                    EventType.POWER_EVENT,
                    {
                        "type": "start",
                        "current_power": 50,
                        "device_power": 100,
                        "current_power_max": 74,
                        "current_power_consumption": 25.0,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 4  # The fourth are shutdown

    # 3. change PRESET
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        await entity.async_set_preset_mode(PRESET_ECO)
        assert entity.preset_mode is PRESET_ECO
        # No change
        assert entity.overpowering_state is True

    # 4. Send hugh power max mesurement to release overpowering
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off:
        # 100 of the device / 4 -> 25, current power 50 so max is 75. With 150 no overheating
        await send_max_power_change_event(entity, 150, datetime.now())
        assert await entity.check_overpowering() is False
        # All configuration is complete and power is > power_max we switch to POWER preset
        assert entity.preset_mode is PRESET_ECO
        assert entity.overpowering_state is False
        assert entity.target_temperature == 17

        assert (
            mock_heater_on.call_count == 0
        )  # The fourth are not restarted because temperature is enought
        assert mock_heater_off.call_count == 0
