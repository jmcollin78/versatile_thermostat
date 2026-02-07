# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the auto fan mode of a over_climate thermostat """
from unittest.mock import patch, call

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant

# from homeassistant.components.climate import HVACAction
from homeassistant.config_entries import ConfigEntryState

from homeassistant.components.climate import ClimateEntityFeature, PRESET_COMFORT, PRESET_ECO, PRESET_BOOST

from pytest_homeassistant_custom_component.common import MockConfigEntry

# from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_over_climate_auto_fan_mode_with_3_fan_speed_values(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the init of an over climate thermostat with 3 fan speed values"""

    fan_modes = ["1", "2", "3", "auto"]

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
        },
    )

    fake_underlying_climate = await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=fan_modes,
    )

    # 1. Init with CONF_AUTO_FAN_TURBO
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.theoverclimatemockname", "climate")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.fan_modes == fan_modes
    assert entity._auto_fan_mode == "auto_fan_turbo"
    assert entity._auto_activated_fan_mode == "3"
    assert entity._auto_deactivated_fan_mode == "1"

    # 2. Change auto_fan_mode by CONF_AUTO_FAN_HIGH
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("High")
        assert entity._auto_activated_fan_mode == "3"
        assert entity._auto_deactivated_fan_mode == "1"

    # 3. Change auto_fan_mode by CONF_AUTO_FAN_MEDIUM
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Medium")
        assert entity._auto_activated_fan_mode == "2"
        assert entity._auto_deactivated_fan_mode == "1"

    # 4. Change auto_fan_mode by CONF_AUTO_FAN_LOW
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Low")
        assert entity._auto_activated_fan_mode == "1"
        assert entity._auto_deactivated_fan_mode == "1"

    entity.remove_thermostat()

async def test_over_climate_auto_fan_mode_with_4_fan_speed_values(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the init of an over climate thermostat with 4 fan speed values"""

    fan_modes = ["low", "medium", "high", "boost", "auto"]

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
        },
    )

    fake_underlying_climate = await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=fan_modes,
    )

    # 1. Init with CONF_AUTO_FAN_TURBO
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.theoverclimatemockname", "climate")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.fan_modes == fan_modes
    assert entity._auto_fan_mode == "auto_fan_turbo"
    assert entity._auto_activated_fan_mode == "boost"
    assert entity._auto_deactivated_fan_mode == "low"

    # 2. Change auto_fan_mode by CONF_AUTO_FAN_HIGH
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("High")
        assert entity._auto_activated_fan_mode == "high"
        assert entity._auto_deactivated_fan_mode == "low"

    # 3. Change auto_fan_mode by CONF_AUTO_FAN_MEDIUM
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Medium")
        assert entity._auto_activated_fan_mode == "medium"
        assert entity._auto_deactivated_fan_mode == "low"

    # 4. Change auto_fan_mode by CONF_AUTO_FAN_LOW
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Low")
        assert entity._auto_activated_fan_mode == "low"
        assert entity._auto_deactivated_fan_mode == "low"

    entity.remove_thermostat()

async def test_over_climate_auto_fan_mode_with_5_fan_speed_values(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the init of an over climate thermostat with 5 fan speed values"""

    fan_modes = ["quiet", "1", "2", "3", "4", "auto"]

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
        },
    )

    fake_underlying_climate = await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=fan_modes,
    )

    # 1. Init with CONF_AUTO_FAN_TURBO
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.theoverclimatemockname", "climate")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.fan_modes == fan_modes
    assert entity._auto_fan_mode == "auto_fan_turbo"
    assert entity._auto_activated_fan_mode == "4"
    assert entity._auto_deactivated_fan_mode == "quiet"

    # 2. Change auto_fan_mode by CONF_AUTO_FAN_HIGH
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("High")
        assert entity._auto_activated_fan_mode == "3"
        assert entity._auto_deactivated_fan_mode == "quiet"

    # 3. Change auto_fan_mode by CONF_AUTO_FAN_MEDIUM
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Medium")
        assert entity._auto_activated_fan_mode == "2"
        assert entity._auto_deactivated_fan_mode == "quiet"

    # 4. Change auto_fan_mode by CONF_AUTO_FAN_LOW
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Low")
        assert entity._auto_activated_fan_mode == "1"
        assert entity._auto_deactivated_fan_mode == "quiet"

    entity.remove_thermostat()

async def test_over_climate_auto_fan_mode_turbo_activation(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the init of an over climate thermostat with auto_fan_mode = Turbo which exists"""

    fan_modes = ["low", "medium", "high", "boost", "mute", "auto", "turbo"]

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
            "eco_ac_temp": 25,
            "comfort_ac_temp": 23,
            "boost_ac_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
        },
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    # 1. Init fan mode
    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

    # Creates the under entity after the thermostat creation. It should works too.
    fake_underlying_climate = await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=fan_modes,
    )
    # The state is written so we wait to wait for propagation
    await hass.async_block_till_done()

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.fan_modes == fan_modes
    assert entity.fan_mode is None
    assert entity._auto_fan_mode == "auto_fan_turbo"
    assert entity._auto_activated_fan_mode == "turbo"
    assert entity._auto_deactivated_fan_mode == "mute"

    # 2. Turn on and set temperature cold
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        # Force preset mode
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert entity.hvac_mode == VThermHvacMode_HEAT
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 18

        # Change the current temperature to 16 which is 2° under
        await send_temperature_change_event(entity, 16, now, True)

        assert mock_send_fan_mode.call_count == 1  # send_temperature_change_event change also the fan mode
        mock_send_fan_mode.assert_has_calls([call.set_fan_mode("turbo")])

        fake_underlying_climate.set_fan_mode("turbo")
        await hass.async_block_till_done()
        assert entity.fan_mode == "turbo"

    # 3. Set another low temperature
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        fake_underlying_climate.set_fan_mode("turbo")

        # Change the current temperature to 15 which is 3° under
        await send_temperature_change_event(entity, 15, now, True)

        # Nothing is send cause we are already in turbo fan mode
        assert mock_send_fan_mode.call_count == 0

        assert entity.fan_mode == "turbo"

    # 4. Set temperature not so cold
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        # Change the current temperature to 17 which is 1° under
        await send_temperature_change_event(entity, 17, now, True)

        assert mock_send_fan_mode.call_count == 1
        mock_send_fan_mode.assert_has_calls([call.set_fan_mode("mute")])

        fake_underlying_climate.set_fan_mode("mute")
        await hass.async_block_till_done()
        assert entity.fan_mode == "mute"

    # 5. Set temperature not so cold another time
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        fake_underlying_climate.set_fan_mode("mute")

        # Change the current temperature to 17 which is 1° under
        await send_temperature_change_event(entity, 17.1, now, True)

        assert mock_send_fan_mode.call_count == 0
        assert entity.fan_mode == "mute"

    # 6. Set temperature very high above the target
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        fake_underlying_climate.set_fan_mode("mute")

        # Change the current temperature to 17 which is 1° under
        await send_temperature_change_event(entity, 21, now, True)

        assert mock_send_fan_mode.call_count == 0
        assert entity.fan_mode == "mute"

    # 7. In AC mode, set temperature very high under the target
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.async_set_hvac_mode(VThermHvacMode_COOL)
        assert entity.hvac_mode == VThermHvacMode_COOL
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 23

        assert entity.current_temperature == 21

        fake_underlying_climate.set_fan_mode("mute")

        # Change the current temperature to 17 which is 1° under
        await send_temperature_change_event(entity, 20, now, True)

        assert mock_send_fan_mode.call_count == 0
        assert entity.fan_mode == "mute"

    # 8. In AC mode, set temperature not so high above the target
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        assert entity.target_temperature == 23
        await send_temperature_change_event(entity, 24, now, True)
        assert entity.current_temperature == 24
        fake_underlying_climate.set_fan_mode("mute")

        assert mock_send_fan_mode.call_count == 0
        assert entity.fan_mode == "mute"

    # 9. In AC mode, set temperature high above the target
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        assert entity.target_temperature == 23
        await send_temperature_change_event(entity, 25.1, now, True)
        assert entity.current_temperature == 25.1

        assert mock_send_fan_mode.call_count == 1
        mock_send_fan_mode.assert_has_calls([call.set_fan_mode("turbo")])

        fake_underlying_climate.set_fan_mode("turbo")
        await hass.async_block_till_done()
        assert entity.fan_mode == "turbo"

    entity.remove_thermostat()

async def test_over_climate_auto_fan_mode_with_descending_speed_list(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """Test the init of an over climate thermostat with 4 fan speed values"""

    fan_modes = ["high", "medium", "low", "diffuse", "auto"]

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
        },
    )

    fake_underlying_climate = await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=fan_modes,
    )

    # 1. Init with CONF_AUTO_FAN_TURBO
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.theoverclimatemockname", "climate")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.fan_modes == fan_modes
    assert entity._auto_fan_mode == "auto_fan_turbo"
    assert entity._auto_activated_fan_mode == "high"
    assert entity._auto_deactivated_fan_mode == "low"

    # 2. Change auto_fan_mode by CONF_AUTO_FAN_HIGH
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode") as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("High")
        assert entity._auto_activated_fan_mode == "medium"
        assert entity._auto_deactivated_fan_mode == "low"

    # 3. Change auto_fan_mode by CONF_AUTO_FAN_MEDIUM
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode") as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Medium")
        assert entity._auto_activated_fan_mode == "low"
        assert entity._auto_deactivated_fan_mode == "low"

    # 4. Change auto_fan_mode by CONF_AUTO_FAN_LOW
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode") as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Low")
        assert entity._auto_activated_fan_mode == "diffuse"
        assert entity._auto_deactivated_fan_mode == "low"

    entity.remove_thermostat()

async def test_over_climate_auto_fan_mode_with_none_fan_speed_values(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the init of an over climate thermostat with none fan speed values"""

    fan_modes = ["on", "auto", "diffuse"]

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
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
        },
    )

    fake_underlying_climate = await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=fan_modes,
    )

    # 1. Init with CONF_AUTO_FAN_TURBO
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.theoverclimatemockname", "climate")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.fan_modes == fan_modes
    assert entity._auto_fan_mode == "auto_fan_turbo"
    assert entity._auto_activated_fan_mode is None
    assert entity._auto_deactivated_fan_mode is None

    # 2. Change auto_fan_mode by CONF_AUTO_FAN_HIGH
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("High")
        assert entity._auto_activated_fan_mode is None
        assert entity._auto_deactivated_fan_mode is None

    # 3. Change auto_fan_mode by CONF_AUTO_FAN_MEDIUM
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Medium")
        assert entity._auto_activated_fan_mode is None
        assert entity._auto_deactivated_fan_mode is None

    # 4. Change auto_fan_mode by CONF_AUTO_FAN_LOW
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.service_set_auto_fan_mode("Low")
        assert entity._auto_activated_fan_mode is None
        assert entity._auto_deactivated_fan_mode is None

    entity.remove_thermostat()

async def test_over_climate_auto_fan_mode_check_delay_command(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """Test the delay of the fan_mode command when the setpoint temperature triggers auto_fan_mode"""

    fan_modes = ["low", "medium", "high", "boost", "mute", "auto", "turbo"]
    fake_underlying_climate = await create_and_register_mock_climate(
        hass=hass,
        unique_id="mockUniqueId",
        name="MockClimateName",
        fan_modes=fan_modes,
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
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            "eco_ac_temp": 25,
            "comfort_ac_temp": 23,
            "boost_ac_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [fake_underlying_climate.entity_id],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
        },
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.fan_modes == fan_modes
    assert entity.fan_mode is None

    assert entity._auto_fan_mode == "auto_fan_turbo"
    assert entity._auto_activated_fan_mode == "turbo"
    assert entity._auto_deactivated_fan_mode == "mute"

    # Force heating mode and preset
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)

    assert entity.hvac_mode == VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == 18

    planned_commands = []

    def fake_async_call_later(hass, delay, callback):
        value = None
        if hasattr(callback, "__closure__") and callback.__closure__:
            free_vars = callback.__code__.co_freevars
            if "fan_mode" in free_vars:
                index = free_vars.index("fan_mode")
                value = callback.__closure__[index].cell_contents

        planned_commands.append({"delay": delay, "fan_mode": value})
        return lambda: None

    # room temp is 18°C
    await send_temperature_change_event(entity, 18, now)

    with patch("custom_components.versatile_thermostat.underlyings.async_call_later", side_effect=fake_async_call_later) as mock_send:
        # --------------------------------------------------
        # 1. Temperature target at 20°C (+2 °C) → auto fan_mode (DELAYED)
        # --------------------------------------------------
        underlying = entity._underlyings[0]
        underlying._last_command_sent_datetime = now + timedelta(seconds=-10)

        await entity.async_set_temperature(temperature=20)

        assert len(planned_commands) == 1
        assert planned_commands[0]["delay"] == 2.0
        assert planned_commands[0]["fan_mode"] == "turbo"

        # --------------------------------------------------
        # 2. Manual fan_mode change withou previous command → NO DELAY
        # --------------------------------------------------
        underlying._last_command_sent_datetime = now + timedelta(seconds=-10)

        await entity.async_set_fan_mode("high")
        assert len(planned_commands) == 1
        assert entity._fan_mode == "high"

        # --------------------------------------------------
        # 3. Temperature target at 18°C (like room temp) → auto deactivation (DELAYED)
        # --------------------------------------------------
        underlying._last_command_sent_datetime = now + timedelta(seconds=-10)

        await entity.async_set_temperature(temperature=18)

        assert len(planned_commands) == 2
        assert planned_commands[1]["delay"] == 2.0
        assert planned_commands[1]["fan_mode"] == "mute"

    entity.remove_thermostat()
