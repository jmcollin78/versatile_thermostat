# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the Window management """
import asyncio

from unittest.mock import patch, call, PropertyMock
from datetime import datetime, timedelta

import logging

from homeassistant.components.climate import (
    SERVICE_SET_TEMPERATURE,
)

from .commons import *

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_56(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that in over_climate mode there is no error when underlying climate is not available"""

    the_mock_underlying = MagicMockClimate()
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=None,  # dont find the underlying climate
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="TheOverClimateMockName",
            unique_id="uniqueId",
            data={
                CONF_NAME: "TheOverClimateMockName",
                CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
                CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
                CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
                CONF_CYCLE_MIN: 5,
                CONF_TEMP_MIN: 15,
                CONF_TEMP_MAX: 30,
                "eco_temp": 17,
                "comfort_temp": 18,
                "boost_temp": 19,
                CONF_USE_WINDOW_FEATURE: False,
                CONF_USE_MOTION_FEATURE: False,
                CONF_USE_POWER_FEATURE: False,
                CONF_USE_PRESENCE_FEATURE: False,
                CONF_CLIMATE: "climate.mock_climate",
                CONF_MINIMAL_ACTIVATION_DELAY: 30,
                CONF_SECURITY_DELAY_MIN: 5,
                CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            },
        )

        entity: BaseThermostat = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        # cause the underlying climate was not found
        assert entity.is_over_climate is True
        assert entity.underlying_entity(0)._underlying_climate is None

        # Should not failed
        entity.update_custom_attributes()

        # try to call async_control_heating
        try:
            ret = await entity.async_control_heating()
            # an exception should be send
            assert ret is False
        except Exception:  # pylint: disable=broad-exception-caught
            assert False

    # This time the underlying will be found
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=the_mock_underlying,  # dont find the underlying climate
    ):
        # try to call async_control_heating
        try:
            await entity.async_control_heating()
        except UnknownEntity:
            assert False
        except Exception:  # pylint: disable=broad-exception-caught
            assert False

        # Should not failed
        entity.update_custom_attributes()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_63(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it should be possible to set the security_default_on_percent to 0"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.0,  # !! here
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.0,  # !! here
            CONF_DEVICE_POWER: 200,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    assert entity._security_min_on_percent == 0
    assert entity._security_default_on_percent == 0


# Waiting for answer in https://github.com/jmcollin78/versatile_thermostat/issues/64
# Repro case not evident
@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_64(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it should be possible to set the security_default_on_percent to 0"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.5,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,  # !! here
            CONF_DEVICE_POWER: 200,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_66(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it should be possible to open/close the window rapidly without side effect"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.5,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,  # !! here
            CONF_DEVICE_POWER: 200,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)

    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.target_temperature == 19
    assert entity.window_state is STATE_OFF

    # Open the window and let the thermostat shut down
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=True,
    ):
        await send_temperature_change_event(entity, 15, now)
        try_window_condition = await send_window_change_event(
            entity, True, False, now, False
        )

        # simulate the call to try_window_condition
        await try_window_condition(None)

        assert mock_send_event.call_count == 1
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count >= 1
        assert mock_condition.call_count == 1

        assert entity.window_state == STATE_ON

    # Close the window but too shortly
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=False
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ):
        event_timestamp = now + timedelta(minutes=1)
        try_window_condition = await send_window_change_event(
            entity, False, True, event_timestamp
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)

        # window state should not have change
        assert entity.window_state == STATE_ON

    # Reopen immediatly with sufficient time
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ):
        try_window_condition = await send_window_change_event(
            entity, True, False, event_timestamp
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)

        # still no change
        assert entity.window_state == STATE_ON
        assert entity.hvac_mode == HVACMode.OFF

    # Close the window but with sufficient time this time
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ) as mock_condition, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        return_value=False,
    ):
        event_timestamp = now + timedelta(minutes=2)
        try_window_condition = await send_window_change_event(
            entity, False, True, event_timestamp
        )
        # simulate the call to try_window_condition
        await try_window_condition(None)

        # window state should be Off this time and old state should have been restored
        assert entity.window_state == STATE_OFF
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_82(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that when a underlying climate is not available the VTherm doesn't go into safety mode"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_CONFIG,  # 5 minutes security delay
    )

    fake_underlying_climate = MockUnavailableClimate(
        hass, "mockUniqueId", "MockClimateName", {}
    )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ) as mock_find_climate:
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        # entry.add_to_hass(hass)
        # await hass.config_entries.async_setup(entry.entry_id)
        # assert entry.state is ConfigEntryState.LOADED
        #
        # def find_my_entity(entity_id) -> ClimateEntity:
        #     """Find my new entity"""
        #     component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
        #     for entity in component.entities:
        #         if entity.entity_id == entity_id:
        #             return entity
        #
        # entity = find_my_entity("climate.theoverclimatemockname")

        assert entity

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        # assert entity.hvac_action is HVACAction.OFF
        assert entity.hvac_mode is HVACMode.OFF
        # assert entity.hvac_mode is None
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            PRESET_NONE,
            PRESET_FROST_PROTECTION,
            PRESET_ECO,
            PRESET_COMFORT,
            PRESET_BOOST,
        ]
        assert entity.preset_mode is PRESET_NONE
        assert entity._security_state is False

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

        assert mock_find_climate.call_count == 1
        assert mock_find_climate.mock_calls[0] == call()
        mock_find_climate.assert_has_calls([call.find_underlying_entity()])

        # Force safety mode
        assert entity._last_ext_temperature_measure is not None
        assert entity._last_temperature_measure is not None
        assert (
            entity._last_temperature_measure.astimezone(tz) - now
        ).total_seconds() < 1
        assert (
            entity._last_ext_temperature_measure.astimezone(tz) - now
        ).total_seconds() < 1

        # Tries to turns on the Thermostat
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode == HVACMode.HEAT

        # 2. activate security feature when date is expired
        with patch(
            "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
        ) as mock_send_event, patch(
            "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
        ):
            event_timestamp = now - timedelta(minutes=6)

            # set temperature to 15 so that on_percent will be > security_min_on_percent (0.2)
            await send_temperature_change_event(entity, 15, event_timestamp)
            # Should stay False
            assert entity.security_state is False
            assert entity.preset_mode == "none"
            assert entity._saved_preset_mode == "none"


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_101(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that when a underlying climate target temp is changed, the VTherm change its own temperature target and switch to manual"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,  # 5 minutes security delay
    )

    # Underlying is in HEAT mode but should be shutdown at startup
    fake_underlying_climate = MockClimate(
        hass, "mockUniqueId", "MockClimateName", {}, HVACMode.HEAT, HVACAction.HEATING
    )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ) as mock_find_climate, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        # entry.add_to_hass(hass)
        # await hass.config_entries.async_setup(entry.entry_id)
        # assert entry.state is ConfigEntryState.LOADED
        #
        # def find_my_entity(entity_id) -> ClimateEntity:
        #     """Find my new entity"""
        #     component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
        #     for entity in component.entities:
        #         if entity.entity_id == entity_id:
        #             return entity
        #
        # entity = find_my_entity("climate.theoverclimatemockname")

        assert entity

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.hvac_mode is HVACMode.OFF
        # because in MockClimate HVACAction is HEATING if hvac_mode is not set
        assert entity.hvac_action is HVACAction.HEATING
        # Underlying should have been shutdown
        assert mock_underlying_set_hvac_mode.call_count == 1
        mock_underlying_set_hvac_mode.assert_has_calls(
            [
                call.set_hvac_mode(HVACMode.OFF),
            ]
        )

        assert entity.target_temperature == entity.min_temp
        assert entity.preset_mode is PRESET_NONE

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

        assert mock_find_climate.call_count == 1
        assert mock_find_climate.mock_calls[0] == call()
        mock_find_climate.assert_has_calls([call.find_underlying_entity()])

        # Force preset mode
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode == HVACMode.HEAT
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT

        # 2. Change the target temp of underlying thermostat at now -> the event will be disgarded because to fast (to avoid loop cf issue 121)
        await send_climate_change_event_with_temperature(
            entity,
            HVACMode.HEAT,
            HVACMode.HEAT,
            HVACAction.OFF,
            HVACAction.OFF,
            now,
            12.75,
        )
        # Should NOT have been switched to Manual preset
        assert entity.target_temperature == 17
        assert entity.preset_mode is PRESET_COMFORT

        # 2. Change the target temp of underlying thermostat at 11 sec later -> the event will be taken
        # Wait 11 sec
        event_timestamp = now + timedelta(seconds=11)
        assert entity.is_regulated is False
        await send_climate_change_event_with_temperature(
            entity,
            HVACMode.HEAT,
            HVACMode.HEAT,
            HVACAction.OFF,
            HVACAction.OFF,
            event_timestamp,
            12.75,
        )
        assert entity.target_temperature == 12.75
        assert entity.preset_mode is PRESET_NONE


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_272(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it not possible to set the target temperature under the min_temp setting"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # default value are min 15°, max 30°, step 0.1
        data=PARTIAL_CLIMATE_CONFIG,  # 5 minutes security delay
    )

    # Min_temp is 15 and max_temp is 19
    fake_underlying_climate = MagicMockClimate()

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ), patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call:
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        # entry.add_to_hass(hass)
        # await hass.config_entries.async_setup(entry.entry_id)
        # assert entry.state is ConfigEntryState.LOADED
        #
        # def find_my_entity(entity_id) -> ClimateEntity:
        #     """Find my new entity"""
        #     component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
        #     for entity in component.entities:
        #         if entity.entity_id == entity_id:
        #             return entity
        #
        # entity = find_my_entity("climate.theoverclimatemockname")

        assert entity

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.hvac_mode is HVACMode.OFF
        # The VTherm value and not the underlying value
        assert entity.target_temperature_step == 0.1
        assert entity.target_temperature == entity.min_temp
        assert entity.is_regulated is True

        assert mock_service_call.call_count == 0

        # Set the hvac_mode to HEAT
        await entity.async_set_hvac_mode(HVACMode.HEAT)

        # In the accepted interval
        await entity.async_set_temperature(temperature=17.5)

        # MagicMock climate is already HEAT by default. So there is no SET_HAVC_MODE call
        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                # call.async_call(
                #     "climate",
                #     SERVICE_SET_HVAC_MODE,
                #     {"entity_id": "climate.mock_climate", "hvac_mode": HVACMode.HEAT},
                # ),
                call.async_call(
                    "climate",
                    SERVICE_SET_TEMPERATURE,
                    {
                        "entity_id": "climate.mock_climate",
                        "temperature": 17.5,
                        # "target_temp_high": 30,
                        # "target_temp_low": 15,
                    },
                ),
            ]
        )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        # Set room temperature to something very cold
        event_timestamp = now + timedelta(minutes=1)

        await send_temperature_change_event(entity, 13, event_timestamp)
        await send_ext_temperature_change_event(entity, 9, event_timestamp)

        # Not in the accepted interval (15-19)
        await entity.async_set_temperature(temperature=10)
        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    "climate",
                    SERVICE_SET_TEMPERATURE,
                    {
                        "entity_id": "climate.mock_climate",
                        "temperature": 15,  # the minimum acceptable
                        # "target_temp_high": 30,
                        # "target_temp_low": 15,
                    },
                ),
            ]
        )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        # Set room temperature to something very cold
        event_timestamp = now + timedelta(minutes=1)

        await send_temperature_change_event(entity, 13, event_timestamp)
        await send_ext_temperature_change_event(entity, 9, event_timestamp)

        # In the accepted interval
        await entity.async_set_temperature(temperature=20.8)
        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    "climate",
                    SERVICE_SET_TEMPERATURE,
                    {
                        "entity_id": "climate.mock_climate",
                        "temperature": 19,  # the maximum acceptable
                        # "target_temp_high": 30,
                        # "target_temp_low": 15,
                    },
                ),
            ]
        )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_407(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the followin case in power management:
    1. a heater is active (heating). So the power consumption takes the heater power into account. We suppose the power consumption is near the threshold,
    2. the user switch preset let's say from Comfort to Boost,
    3. expected: no shredding should occur because the heater was already active,
    4. constated: the heater goes into shredding.

    """

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_POWER_SENSOR: "sensor.mock_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.mock_power_max_sensor",
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    await send_temperature_change_event(entity, 16, now)
    await send_ext_temperature_change_event(entity, 10, now)

    # 1. An already active heater will not switch to overpowering
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_COMFORT
        assert entity.overpowering_state is None
        assert entity.target_temperature == 18
        # waits that the heater starts
        await asyncio.sleep(0.1)
        assert mock_service_call.call_count >= 1
        assert entity.is_device_active is True

        # Send power max mesurement
        await send_max_power_change_event(entity, 110, datetime.now())
        # Send power mesurement (theheater is already in the power measurement)
        await send_power_change_event(entity, 100, datetime.now())
        # No overpowering yet
        assert await entity.check_overpowering() is False
        # All configuration is complete and power is < power_max
        assert entity.preset_mode is PRESET_COMFORT
        assert entity.overpowering_state is False
        assert entity.is_device_active is True

    # 2. An already active heater that switch preset will not switch to overpowering
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        # change preset to Boost
        await entity.async_set_preset_mode(PRESET_BOOST)
        # waits that the heater starts
        await asyncio.sleep(0.1)

        assert await entity.check_overpowering() is False
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.overpowering_state is False
        assert entity.target_temperature == 19
        assert mock_service_call.call_count >= 1

    # 3. if heater is stopped (is_device_active==False), then overpowering should be started
    with patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        # change preset to Boost
        await entity.async_set_preset_mode(PRESET_COMFORT)
        # waits that the heater starts
        await asyncio.sleep(0.1)

        assert await entity.check_overpowering() is True
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_POWER
        assert entity.overpowering_state is True


async def test_bug_339(
    hass: HomeAssistant,
    # skip_hass_states_is_state,
    init_central_config_with_boiler_fixture,
):
    """Test that the counter of active Vtherm in central boiler is
    correctly updated with underlying is in auto and device is active
    """

    api = VersatileThermostatAPI.get_vtherm_api(hass)

    climate1 = MockClimate(
        hass=hass,
        unique_id="climate1",
        name="theClimate1",
        hvac_mode=HVACMode.AUTO,
        hvac_modes=[HVACMode.AUTO, HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL],
        hvac_action=HVACAction.HEATING,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 8,
            CONF_TEMP_MAX: 18,
            "frost_temp": 10,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_CLIMATE: climate1.entity_id,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
        },
    )

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=climate1,
    ):
        entity: ThermostatOverValve = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate
        assert entity.underlying_entities[0].entity_id == "climate.climate1"
        assert api.nb_active_device_for_boiler_threshold == 1

    await entity.async_set_hvac_mode(HVACMode.AUTO)
    # Simulate a state change in underelying
    await api.nb_active_device_for_boiler_entity.calculate_nb_active_devices(None)

    # The VTherm should be active
    assert entity.underlying_entity(0).is_device_active is True
    assert entity.is_device_active is True
    assert api.nb_active_device_for_boiler == 1

    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_508(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it not possible to set the target temperature under the min_temp setting"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # default value are min 15°, max 31°, step 0.1
        data=PARTIAL_CLIMATE_CONFIG,  # 5 minutes security delay
    )

    # Min_temp is 10 and max_temp is 31 and features contains TARGET_TEMPERATURE_RANGE
    fake_underlying_climate = MagicMockClimateWithTemperatureRange()

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ), patch(
        "homeassistant.core.ServiceRegistry.async_call"
    ) as mock_service_call:
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert entity

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.hvac_mode is HVACMode.OFF
        # The VTherm value and not the underlying value
        assert entity.target_temperature_step == 0.1
        assert entity.target_temperature == entity.min_temp
        assert entity.is_regulated is True

        assert mock_service_call.call_count == 0

        # Set the hvac_mode to HEAT
        await entity.async_set_hvac_mode(HVACMode.HEAT)

        # Not In the accepted interval -> should be converted into 10 (the min) and send with target_temp_high and target_temp_low
        await entity.async_set_temperature(temperature=8.5)

        # MagicMock climate is already HEAT by default. So there is no SET_HAVC_MODE call
        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    "climate",
                    SERVICE_SET_TEMPERATURE,
                    {
                        "entity_id": "climate.mock_climate",
                        # "temperature": 17.5,
                        "target_temp_high": 10,
                        "target_temp_low": 10,
                    },
                ),
            ]
        )

    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        # Not In the accepted interval -> should be converted into 10 (the min) and send with target_temp_high and target_temp_low
        await entity.async_set_temperature(temperature=32)

        # MagicMock climate is already HEAT by default. So there is no SET_HAVC_MODE call
        assert mock_service_call.call_count == 1
        mock_service_call.assert_has_calls(
            [
                call.async_call(
                    "climate",
                    SERVICE_SET_TEMPERATURE,
                    {
                        "entity_id": "climate.mock_climate",
                        "target_temp_high": 31,
                        "target_temp_low": 31,
                    },
                ),
            ]
        )
