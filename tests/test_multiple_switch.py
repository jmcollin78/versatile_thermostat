# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, unused-variable

""" Test the Multiple switch management """
import asyncio
from unittest.mock import patch, call, ANY, PropertyMock
from datetime import datetime, timedelta
import logging

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_one_switch_cycle(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_switch):  # pylint: disable=unused-argument
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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
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
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_UNAVAILABLE

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        assert entity.is_ready is True

    # Checks that all heaters are off
    assert entity.is_device_active is False

    # Verify CycleScheduler is created
    assert entity.cycle_scheduler is not None

    # Set temperature to a low level - CycleScheduler will orchestrate the cycle
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ) as mock_device_active, patch(
        "custom_components.versatile_thermostat.cycle_scheduler.async_call_later",
        return_value=None,
    ) as mock_call_later:
        await send_ext_temperature_change_event(entity, 5, event_timestamp)

        # No special event
        assert mock_send_event.call_count == 0
        assert mock_heater_off.call_count == 0

        # The heater should be turned on immediately (offset=0 for single underlying)
        assert mock_heater_on.call_count == 1

        # At 100% power, on_time == cycle_duration so no turn_off is scheduled.
        # Only _on_master_cycle_end is scheduled.
        assert mock_call_later.call_count == 1

    # Set a temperature at middle level - cycle already running, no force
    event_timestamp = now - timedelta(minutes=4)
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ) as mock_device_active:
        await send_temperature_change_event(entity, 18, event_timestamp)

        # No special event
        assert mock_send_event.call_count == 0

    entity.remove_thermostat()


async def test_multiple_switchs(
    hass: HomeAssistant,
    skip_send_event,
    fake_temp_sensor,
    fake_ext_temp_sensor,
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
            CONF_UNDERLYING_LIST: ["switch.mock_switch1", "switch.mock_switch2", "switch.mock_switch3", "switch.mock_switch4"],
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
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

    assert entity.is_initialized is False
    assert entity._is_startup_done is True
    assert entity.is_ready is False

    entity.update_custom_attributes()

    assert MSG_NOT_INITIALIZED in entity._attr_extra_state_attributes["specific_states"].get("messages")
    assert "switch.mock_switch1" in entity._attr_extra_state_attributes["specific_states"].get("not_initialized_entities", [])
    assert "switch.mock_switch2" in entity._attr_extra_state_attributes["specific_states"].get("not_initialized_entities", [])
    assert "switch.mock_switch3" in entity._attr_extra_state_attributes["specific_states"].get("not_initialized_entities", [])
    assert "switch.mock_switch4" in entity._attr_extra_state_attributes["specific_states"].get("not_initialized_entities", [])

    # register the switch after thermostat creation
    for switch_id in ["mock_switch1", "mock_switch2", "mock_switch3", "mock_switch4"]:
        switch = MockSwitch(hass, switch_id, switch_id + "_name")
        await register_mock_entity(hass, switch, SWITCH_DOMAIN)

    await wait_for_local_condition(lambda: entity.is_ready is True)
    assert MSG_NOT_INITIALIZED not in entity._attr_extra_state_attributes["specific_states"].get("messages")
    assert len(entity._attr_extra_state_attributes["specific_states"].get("not_initialized_entities", [])) == 0

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_UNAVAILABLE

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 18.5, event_timestamp)

        # Checks that all climates are off
        assert entity.is_device_active is False  # pylint: disable=protected-access

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_HEAT),
            ]
        )

    # Set temperature to a low level - CycleScheduler handles all 4 underlyings
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ) as mock_device_active, patch(
        "custom_components.versatile_thermostat.cycle_scheduler.async_call_later",
        return_value=None,
    ) as mock_call_later:
        await send_ext_temperature_change_event(entity, 15, event_timestamp)

        # No special event
        assert mock_send_event.call_count == 0
        assert mock_heater_off.call_count == 0

        # The first heater (offset=0) should be turned on immediately
        assert mock_heater_on.call_count == 1

        # CycleScheduler schedules: turn_on for 3 other underlyings +
        # turn_off for each + cycle_end
        # With 4 underlyings at ~100% power, offsets are [0,0,0,0],
        # so all are turned on immediately and only cycle_end is scheduled
        # The exact count depends on on_percent
        assert mock_call_later.call_count >= 1

    entity.remove_thermostat()


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
            CONF_UNDERLYING_LIST: [
                "climate.mock_climate1",
                "climate.mock_climate2",
                "climate.mock_climate3",
                "climate.mock_climate4",
            ],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4climatemockname"
    )
    assert entity
    assert entity.is_over_climate is True
    assert entity.nb_underlying_entities == 4

    # register the switch after thermostat creation
    for climate_id in ["mock_climate1", "mock_climate2", "mock_climate3", "mock_climate4"]:
        climate = MockClimate(hass, climate_id, climate_id + "_name")
        await register_mock_entity(hass, climate, CLIMATE_DOMAIN)

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_UNAVAILABLE

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        # Should be call for all Climates
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_HEAT),
            ]
        )
        assert entity.is_device_active is False  # pylint: disable=protected-access

    # Stop heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(VThermHvacMode_OFF)

        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_UNAVAILABLE

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        # Should be call for all Switch
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_OFF),
            ]
        )
        assert entity.is_device_active is False  # pylint: disable=protected-access

    entity.remove_thermostat()

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate1", "climate.mock_climate2", "climate.mock_climate3", "climate.mock_climate4"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4climatemockname"
    )
    assert entity
    assert entity.is_over_climate is True
    assert entity.nb_underlying_entities == 4

    # register the switch after thermostat creation
    for climate_id in ["mock_climate1", "mock_climate2", "mock_climate3", "mock_climate4"]:
        climate = MockClimate(hass, climate_id, climate_id + "_name")
        await register_mock_entity(hass, climate, CLIMATE_DOMAIN)

    await wait_for_local_condition(lambda: entity.is_ready is True)
    entity.set_follow_underlying_temp_change(True)

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_UNAVAILABLE

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        # Should be call for all Climates
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_HEAT),
            ]
        )
        assert entity.is_device_active is False  # pylint: disable=protected-access

    # Stop heating on one underlying climate
    # All underlying supposed to be aligned with the hvac_mode now
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.hvac_mode",
        VThermHvacMode_HEAT,
    ):
        # Wait 11 sec so that the event will not be discarded
        event_timestamp = now + timedelta(seconds=11)
        await send_climate_change_event(
            entity,
            VThermHvacMode_OFF,
            VThermHvacMode_HEAT,
            HVACAction.OFF,
            HVACAction.HEATING,
            event_timestamp,
            underlying_entity_id="climate.mock_climate3",
        )

        # Should be call for all Climates
        assert mock_underlying_set_hvac_mode.call_count >= 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_OFF),
            ]
        )
        assert entity.hvac_mode == VThermHvacMode_OFF
        assert entity.is_device_active is False  # pylint: disable=protected-access

    # Start heating on one underlying climate
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode, patch(
        # notice that there is no need of return_value=HVACAction.IDLE because this is not
        # a function but a property
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.hvac_action",
        HVACAction.IDLE,
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.hvac_mode",
        VThermHvacMode_OFF,
    ):
        # Wait 11 sec so that the event will not be discarded
        event_timestamp = now + timedelta(seconds=11)
        await send_climate_change_event(
            entity,
            VThermHvacMode_HEAT,
            VThermHvacMode_OFF,
            HVACAction.IDLE,
            HVACAction.OFF,
            event_timestamp,
            underlying_entity_id="climate.mock_climate3",
        )

        # Should be call for all Climates
        assert mock_underlying_set_hvac_mode.call_count >= 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_HEAT),
            ]
        )
        assert entity.hvac_mode == VThermHvacMode_HEAT
        assert entity.hvac_action == HVACAction.IDLE
        assert entity.is_device_active is False  # pylint: disable=protected-access

    entity.remove_thermostat()

async def test_multiple_climates_underlying_changes_not_aligned(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_send_event,
):  # pylint: disable=unused-argument
    """Test that when multiple climate are configured the activation of one underlying
    climate don't activate the others if their havc_mode are not aligned"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # register the switch after thermostat creation
    for climate_id in ["mock_climate1", "mock_climate2", "mock_climate3", "mock_climate4"]:
        climate = MockClimate(hass, climate_id, climate_id + "_name")
        await register_mock_entity(hass, climate, CLIMATE_DOMAIN)

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate1", "climate.mock_climate2", "climate.mock_climate3", "climate.mock_climate4"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4climatemockname"
    )
    assert entity
    assert entity.is_over_climate is True
    assert entity.nb_underlying_entities == 4

    entity._set_now(now)  # pylint: disable=protected-access

    await wait_for_local_condition(lambda: entity.is_ready is True)
    entity.set_follow_underlying_temp_change(True)

    # start heating, in boost mode. We block the control_heating to avoid running a cycle
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert entity.window_state is STATE_UNAVAILABLE

        event_timestamp = now - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

        # Should be call for all Climates
        assert mock_underlying_set_hvac_mode.call_count == 4
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(VThermHvacMode_HEAT),
            ]
        )

    # Stop heating on one underlying climate
    # All underlying supposed to be aligned with the hvac_mode now
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.hvac_mode",
        VThermHvacMode_COOL,
    ):
        # Wait 11 sec so that the event will not be discarded
        now = now + timedelta(seconds=11)
        entity._set_now(now)  # pylint: disable=protected-access
        await send_climate_change_event(
            entity,
            VThermHvacMode_OFF,
            VThermHvacMode_HEAT,
            HVACAction.OFF,
            HVACAction.HEATING,
            now,
            underlying_entity_id="climate.mock_climate3",
        )

        # Should not call hvac_mode
        assert mock_underlying_set_hvac_mode.call_count == 0  # off is not propagated because the hvac_mode are not aligned
        # No change
        assert entity.hvac_mode == VThermHvacMode_HEAT

    entity.remove_thermostat()


async def test_multiple_switch_power_management(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, init_central_power_manager):
    """Test the Power management with 4 underlyings switch"""
    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }
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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [
                "switch.mock_switch1",
                "switch.mock_switch2",
                "switch.mock_switch3",
                "switch.mock_switch4",
            ],
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theover4switchmockname", temps
    )
    assert entity
    assert entity.is_over_climate is False
    assert entity.nb_underlying_entities == 4

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    assert entity.is_ready is False

    # register the switch after thermostat creation
    for switch_id in ["mock_switch1", "mock_switch2", "mock_switch3", "mock_switch4"]:
        switch = MockSwitch(hass, switch_id, switch_id + "_name")
        await register_mock_entity(hass, switch, SWITCH_DOMAIN)

    await wait_for_local_condition(lambda: entity.is_ready is True)

    now: datetime = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN
    assert entity.target_temperature == 19

    # make the heater heats
    await send_temperature_change_event(entity, 15, now)
    await send_ext_temperature_change_event(entity, 1, now)
    await hass.async_block_till_done()

    # 1. Send power mesurement
    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", 50),
            "sensor.the_max_power_sensor": State("sensor.the_max_power_sensor", 300),
        },
        State("unknown.entity_id", "unknown"),
    )

    # Send power max mesurement
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_power_change_event(entity, 50, datetime.now())
        await send_max_power_change_event(entity, 300, datetime.now())
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF

    # 2. Send power max mesurement too low and VThermHvacMode is on
        side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 49))

        #fmt: off
        with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
            patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
            patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
            patch("custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active", new_callable=PropertyMock, return_value=True):
        #fmt: on
            now = now + timedelta(seconds=30)
            VersatileThermostatAPI.get_vtherm_api()._set_now(now)

            assert entity.power_percent > 0
            # 100 of the device / 4 -> 25, current power 50 so max is 75
            await send_max_power_change_event(entity, 49, datetime.now())
            assert entity.power_manager.is_overpowering_detected is True
            # All configuration is complete and power is > power_max we switch to POWER preset
            assert entity.preset_mode == VThermPreset.POWER
            assert entity.power_manager.overpowering_state is STATE_ON
            assert entity.target_temperature == 12

            assert mock_send_event.call_count == 2
            mock_send_event.assert_has_calls(
                [
                    call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.POWER}),
                    call.send_event(
                        EventType.POWER_EVENT,
                        {
                            "type": "start",
                            "current_power": 50,
                            "device_power": 100,
                            "current_max_power": 49,
                            "current_power_consumption": 100,
                        },
                    ),
                ],
                any_order=True,
            )
            assert mock_heater_on.call_count == 0
            assert mock_heater_off.call_count >= 4  # The fourth are shutdown

    # 3. change PRESET to ECO. But overpowering is still on cause temp is very low
        with patch(
            "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
        ) as mock_send_event:
            now = now + timedelta(seconds=30)
            VersatileThermostatAPI.get_vtherm_api()._set_now(now)

            await entity.async_set_preset_mode(VThermPreset.ECO)
            # before refacto: assert entity.preset_mode == VThermPreset.ECO
            await wait_for_local_condition(lambda: entity.preset_mode == VThermPreset.POWER)
            # No change cause temperature is very low
            assert entity.power_manager.overpowering_state is STATE_ON
            assert entity.target_temperature == 12

    # 4. Send hugh power max mesurement to release overpowering
        side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 150))

        with patch(
            "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
        ) as mock_send_event, patch(
            "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
        ) as mock_heater_on, patch(
            "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
        ) as mock_heater_off:
            now = now + timedelta(seconds=30)
            VersatileThermostatAPI.get_vtherm_api()._set_now(now)

            # 100 of the device / 4 -> 25, current power 50 so max is 75. With 150 no overheating
            await send_max_power_change_event(entity, 150, datetime.now())
            assert entity.power_manager.is_overpowering_detected is False
            # All configuration is complete and power is > power_max we switch to POWER preset
            assert entity.preset_mode == VThermPreset.ECO
            assert entity.power_manager.overpowering_state is STATE_OFF
            assert entity.target_temperature == 17

            # No more overheating so the 4th heater should be restarted
            assert (
                mock_heater_on.call_count == 1
            )
            # The 3 other heaters should be turned off because they have a non-zero offset
            # and were previously ON (from the 100% power cycle at step 1)
            assert mock_heater_off.call_count == 3

    entity.remove_thermostat()
