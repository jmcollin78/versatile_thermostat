# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

""" Test the Window management """
from unittest.mock import patch, call
from datetime import datetime, timedelta

import logging

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import (
    SERVICE_SET_TEMPERATURE,
)

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)

from custom_components.versatile_thermostat.switch import (
    FollowUnderlyingTemperatureChange,
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
async def test_underlying_change_follow(
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

        assert entity
        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.hvac_mode is HVACMode.OFF
        # because in MockClimate HVACAction is HEATING if hvac_mode is not set
        assert entity.hvac_action is HVACAction.HEATING
        assert entity.follow_underlying_temp_change is False

        follow_entity: FollowUnderlyingTemperatureChange = search_entity(
            hass,
            "switch.theoverclimatemockname_follow_underlying_temp_change",
            SWITCH_DOMAIN,
        )
        assert follow_entity is not None
        assert follow_entity.state is STATE_OFF

        # follow the underlying temp change
        follow_entity.turn_on()

        assert entity.follow_underlying_temp_change is True
        assert follow_entity.state is STATE_ON

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

        # 1. Force preset mode
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
            entity.min_temp + 1,
            True,
            "climate.mock_climate",  # the underlying climate entity id
        )
        # Should NOT have been switched to Manual preset
        assert entity.target_temperature == 17
        assert entity.preset_mode is PRESET_COMFORT

        # 3. Change the target temp of underlying thermostat at 11 sec later -> the event will be taken
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
            entity.min_temp + 1,
            True,
            "climate.mock_climate",  # the underlying climate entity id
        )
        assert entity.target_temperature == entity.min_temp + 1
        assert entity.preset_mode is PRESET_NONE

        # 4. Change the target temp with < 1 value. The value should not be taken
        # Wait 11 sec
        event_timestamp = now + timedelta(seconds=11)
        await send_climate_change_event_with_temperature(
            entity,
            HVACMode.HEAT,
            HVACMode.HEAT,
            HVACAction.OFF,
            HVACAction.OFF,
            event_timestamp,
            entity.min_temp + 1.5,
            True,
            "climate.mock_climate",  # the underlying climate entity id
        )
        assert entity.target_temperature == entity.min_temp + 1
        assert entity.preset_mode is PRESET_NONE


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_underlying_change_not_follow(
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

        assert entity

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.hvac_mode is HVACMode.OFF
        # because in MockClimate HVACAction is HEATING if hvac_mode is not set
        assert entity.hvac_action is HVACAction.HEATING
        assert entity.target_temperature == 15
        assert entity.preset_mode is PRESET_NONE

        # default value
        assert entity.follow_underlying_temp_change is False

        follow_entity: FollowUnderlyingTemperatureChange = search_entity(
            hass,
            "switch.theoverclimatemockname_follow_underlying_temp_change",
            SWITCH_DOMAIN,
        )
        assert follow_entity is not None
        assert follow_entity.state is STATE_OFF

        # follow the underlying temp change
        follow_entity.turn_off()

        assert entity.follow_underlying_temp_change is False
        assert follow_entity.state is STATE_OFF

        # 1. Force preset mode
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode == HVACMode.HEAT
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT
        assert entity.target_temperature == 17

        # 2. Change the target temp of underlying thermostat at 11 sec later to avoid temporal filter
        event_timestamp = now + timedelta(seconds=30)
        await send_climate_change_event_with_temperature(
            entity,
            HVACMode.HEAT,
            HVACMode.HEAT,
            HVACAction.OFF,
            HVACAction.OFF,
            event_timestamp,
            21,
            True,
            "climate.mock_climate",  # the underlying climate entity id
        )
        # Should NOT have been switched to Manual preset
        assert entity.target_temperature == 17
        assert entity.preset_mode is PRESET_COMFORT


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_615(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that when a underlying climate target temp is changed, the VTherm don't change its own temperature target if no
    target_temperature have already been sent"""

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

    # 1. create the thermostat
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        vtherm = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert vtherm

        assert vtherm.name == "TheOverClimateMockName"
        assert vtherm.is_over_climate is True
        assert vtherm.hvac_mode is HVACMode.OFF
        # because in MockClimate HVACAction is HEATING if hvac_mode is not set
        assert vtherm.hvac_action is HVACAction.HEATING

        # Force a preset_mode without sending a temperature (as it was restored with a preset)
        vtherm._attr_preset_mode = PRESET_BOOST

        assert vtherm.target_temperature == vtherm.min_temp
        assert vtherm.preset_mode is PRESET_BOOST

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"
    ) as mock_underlying_set_hvac_mode:
        # 2. Change the target temp of underlying thermostat at now + 1 min
        now = now + timedelta(minutes=1)
        await send_climate_change_event_with_temperature(
            vtherm,
            HVACMode.OFF,
            HVACMode.OFF,
            HVACAction.OFF,
            HVACAction.OFF,
            now,
            25,
            True,
            "climate.mock_climate",  # the underlying climate entity id
        )
        # Should NOT have been taken the new target temp nor have change the preset
        assert vtherm.target_temperature == vtherm.min_temp
        assert vtherm.preset_mode is PRESET_BOOST

        mock_underlying_set_hvac_mode.assert_not_called()


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_508(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that it not possible to set the target temperature under the min_temp setting"""

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
                        "temperature": 10,
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
                        "temperature": 31,
                    },
                ),
            ]
        )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_bug_524(hass: HomeAssistant, skip_hass_states_is_state):
    """Test when switching from Cool to Heat the new temperature in Heat mode should be used"""

    # vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # The temperatures to set
    temps = {
        "frost": 7.0,
        "eco": 17.0,
        "comfort": 19.0,
        "boost": 21.0,
        "eco_ac": 27.0,
        "comfort_ac": 25.0,
        "boost_ac": 23.0,
        "frost_away": 7.1,
        "eco_away": 17.1,
        "comfort_away": 19.1,
        "boost_away": 21.1,
        "eco_ac_away": 27.1,
        "comfort_ac_away": 25.1,
        "boost_ac_away": 23.1,
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="overClimateUniqueId",
        data={
            CONF_NAME: "overClimate",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_CLIMATE: "climate.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
        },
        # | temps,
    )

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mock_climate",
        name="mock_climate",
        hvac_modes=[HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY],
    )

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        vtherm: ThermostatOverClimate = await create_thermostat(
            hass, config_entry, "climate.overclimate"
        )

    assert vtherm is not None

    # We search for NumberEntities
    for preset_name, value in temps.items():

        await set_climate_preset_temp(vtherm, preset_name, value)

        temp_entity: NumberEntity = search_entity(
            hass,
            "number.overclimate_preset_" + preset_name + PRESET_TEMP_SUFFIX,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        # Because set_value is not implemented in Number class (really don't understand why...)
        assert temp_entity.state == value

    # 1. Set mode to Heat and preset to Comfort
    await send_presence_change_event(vtherm, True, False, datetime.now())
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await vtherm.async_set_preset_mode(PRESET_COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 19.0

    # 2. Only change the HVAC_MODE (and keep preset to comfort)
    await vtherm.async_set_hvac_mode(HVACMode.COOL)
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 25.0

    # 3. Only change the HVAC_MODE (and keep preset to comfort)
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 19.0

    # 4. Change presence to off
    await send_presence_change_event(vtherm, False, True, datetime.now())
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 19.1

    # 5. Change hvac_mode to AC
    await vtherm.async_set_hvac_mode(HVACMode.COOL)
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 25.1

    # 6. Change presence to on
    await send_presence_change_event(vtherm, True, False, datetime.now())
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 25

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_ignore_temp_outside_minmax_range(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that when a underlying climate target temp is changed, the VTherm ignores the target temp if it is outside the min/max range"""

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

        # 1. VTherm must follow the underlying's temperature changes
        follow_entity: FollowUnderlyingTemperatureChange = search_entity(
            hass,
            "switch.theoverclimatemockname_follow_underlying_temp_change",
            SWITCH_DOMAIN,
        )

        # follow the underlying temp change
        follow_entity.turn_on()

        assert entity.follow_underlying_temp_change is True
        assert follow_entity.state is STATE_ON

        # 2. Force preset mode
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode == HVACMode.HEAT
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT

        # 3. Try to set the target temperature to a below min_temp -> should be ignored
        # Wait 11 sec
        event_timestamp = now + timedelta(seconds=11)
        assert entity.is_regulated is False
        await send_climate_change_event_with_temperature(
            entity,
            HVACMode.HEAT,
            HVACMode.HEAT,
            HVACAction.HEATING,
            HVACAction.HEATING,
            event_timestamp,
            entity.min_temp - 1,
            True,
            "climate.mock_climate",  # the underlying climate entity id
        )
        assert entity.target_temperature == 17

        # 4. Try to set the target temperature to a above max_temp -> should be ignored
        event_timestamp = event_timestamp + timedelta(seconds=11)
        assert entity.is_regulated is False
        await send_climate_change_event_with_temperature(
            entity,
            HVACMode.HEAT,
            HVACMode.HEAT,
            HVACAction.HEATING,
            HVACAction.HEATING,
            event_timestamp,
            entity.max_temp + 1,
            True,
            "climate.mock_climate",  # the underlying climate entity id
        )
        assert entity.target_temperature == 17

        # 5. Switch off the VTherm and receive an event from the underlying with a temp to be ignored,
        # but an HVACAction to be taken into account
        await entity.async_set_hvac_mode(HVACMode.OFF)
        assert entity.hvac_mode == HVACMode.OFF

        fake_underlying_climate.set_hvac_mode(HVACMode.OFF)
        fake_underlying_climate.set_hvac_action(HVACAction.IDLE)

        event_timestamp = event_timestamp + timedelta(seconds=11)
        await send_climate_change_event_with_temperature(
            entity,
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACAction.IDLE,
            HVACAction.HEATING,
            event_timestamp,
            entity.min_temp - 1,
            True,
            "climate.mock_climate",  # the underlying climate entity id
        )
        assert entity.target_temperature == 17
        assert entity.hvac_action == HVACAction.IDLE

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_hvac_off_should_take_the_lead_over_window(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test than a manual hvac_off is taken into account over a window hvac_off"""

    # The temperatures to set
    temps = {
        "frost": 7.0,
        "eco": 17.0,
        "comfort": 19.0,
        "boost": 21.0,
        "eco_ac": 27.0,
        "comfort_ac": 25.0,
        "boost_ac": 23.0,
        "frost_away": 7.1,
        "eco_away": 17.1,
        "comfort_away": 19.1,
        "boost_away": 21.1,
        "eco_ac_away": 27.1,
        "comfort_ac_away": 25.1,
        "boost_ac_away": 23.1,
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="overClimateUniqueId",
        data={
            CONF_NAME: "overClimate",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_SENSOR: "binary_sensor.window_sensor",
            CONF_WINDOW_DELAY: 10,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_CLIMATE: "climate.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_FAST,
        },
    )

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mock_climate",
        name="mock_climate",
        hvac_modes=[HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
    )

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        vtherm: ThermostatOverClimate = await create_thermostat(
            hass, config_entry, "climate.overclimate"
        )

        assert vtherm is not None

        # Initialize all temps
        await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

        # Check correct initialization of auto_start_stop attributes
        assert (
            vtherm._attr_extra_state_attributes["auto_start_stop_level"]
            == AUTO_START_STOP_LEVEL_FAST
        )

        assert vtherm.auto_start_stop_level == AUTO_START_STOP_LEVEL_FAST
        enable_entity = search_entity(
            hass, "switch.overclimate_enable_auto_start_stop", SWITCH_DOMAIN
        )
        assert enable_entity is not None
        assert enable_entity.state == STATE_ON

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 1. Set mode to Heat and preset to Comfort and close the window
    send_window_change_event(vtherm, False, False, now, False)
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 18, now, True)
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await vtherm.async_set_preset_mode(PRESET_COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 19.0
    # VTherm should be heating
    assert vtherm.hvac_mode == HVACMode.HEAT
    # VTherm window_state should be off
    assert vtherm.window_state == STATE_OFF

    # 2. Open the window and wait for the delay
    now = now + timedelta(minutes=2)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        vtherm._set_now(now)
        try_function = await send_window_change_event(
            vtherm, True, False, now, sleep=False
        )

        await try_function(None)

        # Nothing should have change (window event is ignoed as we are already OFF)
        assert vtherm.hvac_mode == HVACMode.OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
        assert vtherm._saved_hvac_mode == HVACMode.HEAT

        assert mock_send_event.call_count == 2

        assert vtherm.window_state == STATE_ON

    # 3. Turn off manually the VTherm. This should be taken into account
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        await vtherm.async_set_hvac_mode(HVACMode.OFF)
        await hass.async_block_till_done()

        # Should be off with reason MANUAL
        assert vtherm.hvac_mode == HVACMode.OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_MANUAL
        assert vtherm._saved_hvac_mode == HVACMode.OFF
        # Window state should not change
        assert vtherm.window_state == STATE_ON

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF}),
            ]
        )

    # 4. close the window -> we should stay off reason manual
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        try_function = await send_window_change_event(
            vtherm, False, True, now, sleep=False
        )

        await try_function(None)

        # The VTherm should turn on and off again due to auto-start-stop
        assert vtherm.hvac_mode == HVACMode.OFF
        assert vtherm.hvac_off_reason is HVAC_OFF_REASON_MANUAL
        assert vtherm._saved_hvac_mode == HVACMode.OFF

        assert vtherm.window_state == STATE_OFF
        assert mock_send_event.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_hvac_off_should_take_the_lead_over_auto_start_stop(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test than a manual hvac_off is taken into account over a auto-start/stop hvac_off"""

    # The temperatures to set
    temps = {
        "frost": 7.0,
        "eco": 17.0,
        "comfort": 19.0,
        "boost": 21.0,
        "eco_ac": 27.0,
        "comfort_ac": 25.0,
        "boost_ac": 23.0,
        "frost_away": 7.1,
        "eco_away": 17.1,
        "comfort_away": 19.1,
        "boost_away": 21.1,
        "eco_ac_away": 27.1,
        "comfort_ac_away": 25.1,
        "boost_ac_away": 23.1,
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="overClimateUniqueId",
        data={
            CONF_NAME: "overClimate",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_SENSOR: "binary_sensor.window_sensor",
            CONF_WINDOW_DELAY: 10,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_PRESENCE_SENSOR: "binary_sensor.presence_sensor",
            CONF_CLIMATE: "climate.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_FAST,
        },
    )

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mock_climate",
        name="mock_climate",
        hvac_modes=[HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
    )

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        vtherm: ThermostatOverClimate = await create_thermostat(
            hass, config_entry, "climate.overclimate"
        )

        assert vtherm is not None

        # Initialize all temps
        await set_all_climate_preset_temp(hass, vtherm, temps, "overclimate")

        # Check correct initialization of auto_start_stop attributes
        assert (
            vtherm._attr_extra_state_attributes["auto_start_stop_level"]
            == AUTO_START_STOP_LEVEL_FAST
        )

        assert vtherm.auto_start_stop_level == AUTO_START_STOP_LEVEL_FAST
        enable_entity = search_entity(
            hass, "switch.overclimate_enable_auto_start_stop", SWITCH_DOMAIN
        )
        assert enable_entity is not None
        assert enable_entity.state == STATE_ON

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 1. Set mode to Heat and preset to Comfort
    send_window_change_event(vtherm, False, False, now, False)
    await send_presence_change_event(vtherm, True, False, now)
    await send_temperature_change_event(vtherm, 18, now, True)
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await vtherm.async_set_preset_mode(PRESET_COMFORT)
    await hass.async_block_till_done()

    assert vtherm.target_temperature == 19.0
    # VTherm should be heating
    assert vtherm.hvac_mode == HVACMode.HEAT

    # 2. Set current temperature to 21 5 min later -> should turn off VTherm
    now = now + timedelta(minutes=5)
    vtherm._set_now(now)
    # reset accumulated error (only for testing)
    vtherm._auto_start_stop_algo._accumulated_error = 0
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        await send_temperature_change_event(vtherm, 21, now, True)
        await hass.async_block_till_done()

        # VTherm should no more be heating
        assert vtherm.hvac_mode == HVACMode.OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP
        assert vtherm._saved_hvac_mode == HVACMode.HEAT
        assert mock_send_event.call_count == 2  # turned to off

        mock_send_event.assert_has_calls(
            [
                call(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF}),
                call(
                    event_type=EventType.AUTO_START_STOP_EVENT,
                    data={
                        "type": "stop",
                        "name": "overClimate",
                        "cause": "Auto stop conditions reached",
                        "hvac_mode": HVACMode.OFF,
                        "saved_hvac_mode": HVACMode.HEAT,
                        "target_temperature": 19.0,
                        "current_temperature": 21.0,
                        "temperature_slope": 0.3,
                        "accumulated_error": -2,
                        "accumulated_error_threshold": 2,
                    },
                ),
            ]
        )

    # 3. Turn off manually the VTherm. This should be taken into account
    now = now + timedelta(minutes=1)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        await vtherm.async_set_hvac_mode(HVACMode.OFF)
        await hass.async_block_till_done()

        # Should be off with reason MANUAL
        assert vtherm.hvac_mode == HVACMode.OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_MANUAL
        assert vtherm._saved_hvac_mode == HVACMode.OFF

        assert mock_send_event.call_count == 1
        mock_send_event.assert_has_calls(
            [
                call(EventType.HVAC_MODE_EVENT, {"hvac_mode": HVACMode.OFF}),
            ]
        )

    # 4. removes the auto-start/stop detection
    now = now + timedelta(minutes=5)
    vtherm._set_now(now)
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        await send_temperature_change_event(vtherm, 15, now, True)
        await hass.async_block_till_done()

        # VTherm should no more be heating
        assert vtherm.hvac_mode == HVACMode.OFF
        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_MANUAL
        assert vtherm._saved_hvac_mode == HVACMode.OFF
        assert mock_send_event.call_count == 0  # nothing have change
