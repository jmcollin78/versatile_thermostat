""" Test the NumberEntity taht holds the temperature of a VTherm or of a Central configuration """

# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long, too-many-lines

# from unittest.mock import patch, call
# from datetime import datetime, timedelta
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

# from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.const import NowClass
from custom_components.versatile_thermostat.vtherm_api import VersatileThermostatAPI

from .commons import *


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_add_number_for_central_config(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the construction of a central configuration and the
    creation and registration of the NumberEntity which holds
    the temperature initialized from config_entry"""

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    temps = {
        "frost_temp": 10,
        "eco_temp": 17.1,
        "comfort_temp": 18.1,
        "boost_temp": 19.1,
        "eco_ac_temp": 25.1,
        "comfort_ac_temp": 23.1,
        "boost_ac_temp": 21.1,
        "frost_away_temp": 15.1,
        "eco_away_temp": 15.2,
        "comfort_away_temp": 15.3,
        "boost_away_temp": 15.4,
        "eco_ac_away_temp": 30.5,
        "comfort_ac_away_temp": 30.6,
        "boost_ac_away_temp": 30.7,
    }

    central_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: CENTRAL_CONFIG_NAME,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_WINDOW_DELAY: 15,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 4,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 1,
            CONF_WINDOW_AUTO_MAX_DURATION: 31,
            CONF_MOTION_DELAY: 31,
            CONF_MOTION_OFF_DELAY: 301,
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "frost",
            CONF_POWER_SENSOR: "sensor.mock_central_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.mock_central_max_power_sensor",
            CONF_PRESET_POWER: 14,
            CONF_MINIMAL_ACTIVATION_DELAY: 11,
            CONF_SAFETY_DELAY_MIN: 61,
            CONF_SAFETY_MIN_ON_PERCENT: 0.5,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.2,
            CONF_USE_CENTRAL_BOILER_FEATURE: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        }
        | temps,
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    # We search for NumberEntities
    for preset_name, value in temps.items():
        temp_entity = search_entity(
            hass,
            "number.central_configuration_preset_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace(PRESET_TEMP_SUFFIX, "")
            .replace(PRESET_AC_SUFFIX, " ac")
            .replace(PRESET_AWAY_SUFFIX, " away")
            .lower()
        )

        # Find temp Number into vtherm_api
        val = vtherm_api.get_temperature_number_value(
            config_id=central_config_entry.entry_id, preset_name=preset_name
        )
        assert val == value


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_add_number_for_central_config_without_temp(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the construction of a central configuration and the
    creation and registration of the NumberEntity which holds
    the temperature not intialized from confif_entry.
    In non AC_MODE the value should be initialized to the MIN"""

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # Default is min Value in non AC_MODE
    temps = {
        "frost_temp": 15.0,
        "eco_temp": 15.0,
        "comfort_temp": 15.0,
        "boost_temp": 15.0,
        "eco_ac_temp": 15.0,
        "comfort_ac_temp": 15.0,
        "boost_ac_temp": 15.0,
        "frost_away_temp": 15.0,
        "eco_away_temp": 15.0,
        "comfort_away_temp": 15.0,
        "boost_away_temp": 15.0,
        "eco_ac_away_temp": 15.0,
        "comfort_ac_away_temp": 15.0,
        "boost_ac_away_temp": 15.0,
    }

    central_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: CENTRAL_CONFIG_NAME,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_WINDOW_DELAY: 15,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 4,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 1,
            CONF_WINDOW_AUTO_MAX_DURATION: 31,
            CONF_MOTION_DELAY: 31,
            CONF_MOTION_OFF_DELAY: 301,
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "frost",
            CONF_POWER_SENSOR: "sensor.mock_central_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.mock_central_max_power_sensor",
            CONF_PRESET_POWER: 14,
            CONF_MINIMAL_ACTIVATION_DELAY: 11,
            CONF_SAFETY_DELAY_MIN: 61,
            CONF_SAFETY_MIN_ON_PERCENT: 0.5,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.2,
            CONF_USE_CENTRAL_BOILER_FEATURE: False,
        },
        # | temps,
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    # We search for NumberEntities
    for preset_name, value in temps.items():
        temp_entity = search_entity(
            hass,
            "number.central_configuration_preset_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace(PRESET_TEMP_SUFFIX, "")
            .replace(PRESET_AC_SUFFIX, " ac")
            .replace(PRESET_AWAY_SUFFIX, " away")
            .lower()
        )

        # Find temp Number into vtherm_api
        val = vtherm_api.get_temperature_number_value(
            config_id=central_config_entry.entry_id, preset_name=preset_name
        )
        assert val == value


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_add_number_for_central_config_without_temp_ac_mode(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the construction of a central configuration and the
    creation and registration of the NumberEntity which holds
    the temperature not intialized from confif_entry.
    In AC_MODE the defaul value should the MAX"""

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # Default is min Value in non AC_MODE
    temps = {
        "frost_temp": 30.0,
        "eco_temp": 30.0,
        "comfort_temp": 30.0,
        "boost_temp": 30.0,
        "eco_ac_temp": 30.0,
        "comfort_ac_temp": 30.0,
        "boost_ac_temp": 30.0,
        "frost_away_temp": 30.0,
        "eco_away_temp": 30.0,
        "comfort_away_temp": 30.0,
        "boost_away_temp": 30.0,
        "eco_ac_away_temp": 30.0,
        "comfort_ac_away_temp": 30.0,
        "boost_ac_away_temp": 30.0,
    }

    central_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: CENTRAL_CONFIG_NAME,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_AC_MODE: True,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_WINDOW_DELAY: 15,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 4,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 1,
            CONF_WINDOW_AUTO_MAX_DURATION: 31,
            CONF_MOTION_DELAY: 31,
            CONF_MOTION_OFF_DELAY: 301,
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "frost",
            CONF_POWER_SENSOR: "sensor.mock_central_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.mock_central_max_power_sensor",
            CONF_PRESET_POWER: 14,
            CONF_MINIMAL_ACTIVATION_DELAY: 11,
            CONF_SAFETY_DELAY_MIN: 61,
            CONF_SAFETY_MIN_ON_PERCENT: 0.5,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.2,
            CONF_USE_CENTRAL_BOILER_FEATURE: False,
        },
        # | temps,
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    # We search for NumberEntities
    for preset_name, value in temps.items():
        temp_entity = search_entity(
            hass,
            "number.central_configuration_preset_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace(PRESET_TEMP_SUFFIX, "")
            .replace(PRESET_AC_SUFFIX, " ac")
            .replace(PRESET_AWAY_SUFFIX, " away")
            .lower()
        )

        # Find temp Number into vtherm_api
        val = vtherm_api.get_temperature_number_value(
            config_id=central_config_entry.entry_id, preset_name=preset_name
        )
        assert val == value


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_add_number_for_central_config_without_temp_restore(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the construction of a central configuration and the
    creation and registration of the NumberEntity which holds
    the temperature not intialized from confif_entry"""

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # Default is min Value in non AC_MODE
    temps = {
        "frost_temp": 23.0,
        "eco_temp": 23.0,
        "comfort_temp": 23.0,
        "boost_temp": 23.0,
        "eco_ac_temp": 23.0,
        "comfort_ac_temp": 23.0,
        "boost_ac_temp": 23.0,
        "frost_away_temp": 23.0,
        "eco_away_temp": 23.0,
        "comfort_away_temp": 23.0,
        "boost_away_temp": 23.0,
        "eco_ac_away_temp": 23.0,
        "comfort_ac_away_temp": 23.0,
        "boost_ac_away_temp": 23.0,
    }

    central_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: CENTRAL_CONFIG_NAME,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_AC_MODE: False,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_WINDOW_DELAY: 15,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 4,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 1,
            CONF_WINDOW_AUTO_MAX_DURATION: 31,
            CONF_MOTION_DELAY: 31,
            CONF_MOTION_OFF_DELAY: 301,
            CONF_MOTION_PRESET: "boost",
            CONF_NO_MOTION_PRESET: "frost",
            CONF_POWER_SENSOR: "sensor.mock_central_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.mock_central_max_power_sensor",
            CONF_PRESET_POWER: 14,
            CONF_MINIMAL_ACTIVATION_DELAY: 11,
            CONF_SAFETY_DELAY_MIN: 61,
            CONF_SAFETY_MIN_ON_PERCENT: 0.5,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.2,
            CONF_USE_CENTRAL_BOILER_FEATURE: False,
        },
        # | temps,
    )

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        return_value=State(entity_id="number.mock_valve", state="23"),
    ):
        central_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(central_config_entry.entry_id)

    assert central_config_entry.state is ConfigEntryState.LOADED

    # We search for NumberEntities
    for preset_name, value in temps.items():
        temp_entity = search_entity(
            hass,
            "number.central_configuration_preset_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace(PRESET_TEMP_SUFFIX, "")
            .replace(PRESET_AC_SUFFIX, " ac")
            .replace(PRESET_AWAY_SUFFIX, " away")
            .lower()
        )

        # Find temp Number into vtherm_api
        val = vtherm_api.get_temperature_number_value(
            config_id=central_config_entry.entry_id, preset_name=preset_name
        )
        assert val == value


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_add_number_for_over_switch_use_central(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the construction of a over switch vtherm with
    use central config for PRESET and PRESENCE.
    It also have old temp config value which should be not used.
    So it should have no Temp NumberEntity"""

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    temps = {
        "frost_temp": 10,
        "eco_temp": 17.1,
        "comfort_temp": 18.1,
        "boost_temp": 19.1,
        "eco_ac_temp": 25.1,
        "comfort_ac_temp": 23.1,
        "boost_ac_temp": 21.1,
        "frost_away_temp": 15.1,
        "eco_away_temp": 15.2,
        "comfort_away_temp": 15.3,
        "boost_away_temp": 15.4,
        "eco_ac_away_temp": 30.5,
        "comfort_ac_away_temp": 30.6,
        "boost_ac_away_temp": 30.7,
    }

    vtherm_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: "TheOverSwitchVTherm",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_AC_MODE: False,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        }
        | temps,
    )

    # The restore should not be used
    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        return_value=State(entity_id="number.mock_valve", state="23"),
    ) as mock_restore_state:
        vtherm_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(vtherm_entry.entry_id)

        assert mock_restore_state.call_count == 0

    assert vtherm_entry.state is ConfigEntryState.LOADED

    # We search for NumberEntities
    for preset_name, _ in temps.items():
        temp_entity = search_entity(
            hass,
            "number.central_configuration_preset_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity is None

        # Find temp Number into vtherm_api
        val = vtherm_api.get_temperature_number_value(
            config_id=vtherm_entry.entry_id, preset_name=preset_name
        )
        assert val is None


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_add_number_for_over_switch_use_central_presence(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_config
):
    """Test the construction of a over switch vtherm with
    use central config for PRESET and PRESENCE.
    It also have old temp config value which should be not used.
    So it should have no Temp NumberEntity"""

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    temps = {
        "frost_temp": 10,
        "eco_temp": 17.1,
        "comfort_temp": 18.1,
        "boost_temp": 19.1,
        "eco_ac_temp": 25.1,
        "comfort_ac_temp": 23.1,
        "boost_ac_temp": 21.1,
    }
    temps_missing = {
        "frost_away_temp": 15.1,
        "eco_away_temp": 15.2,
        "comfort_away_temp": 15.3,
        "boost_away_temp": 15.4,
        "eco_ac_away_temp": 30.5,
        "comfort_ac_away_temp": 30.6,
        "boost_ac_away_temp": 30.7,
    }

    vtherm_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: "TheOverSwitchVTherm",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_AC_MODE: True,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_CYCLE_MIN: 5,
            CONF_HEATER: "switch.mock_switch1",
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        }
        | temps
        | temps_missing,
    )

    vtherm: BaseThermostat = await create_thermostat(
        hass, vtherm_entry, "climate.theoverswitchvtherm"
    )

    assert vtherm.use_central_config_temperature is True

    # 1. We search for NumberEntities
    for preset_name, value in temps.items():
        temp_entity = search_entity(
            hass,
            "number.theoverswitchvtherm_preset_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace(PRESET_TEMP_SUFFIX, "")
            .replace(PRESET_AC_SUFFIX, " ac")
            .replace(PRESET_AWAY_SUFFIX, " away")
            .lower()
        )

        # Find temp Number into vtherm_api
        val = vtherm_api.get_temperature_number_value(
            config_id=vtherm_entry.entry_id, preset_name=preset_name
        )
        assert val == value

    # 2. We search for NumberEntities to be missing
    for preset_name, value in temps_missing.items():
        temp_entity = search_entity(
            hass,
            "number.theoverswitchvtherm_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity is None

        # Find temp Number into vtherm_api
        val = vtherm_api.get_temperature_number_value(
            config_id=vtherm_entry.entry_id, preset_name=preset_name
        )
        assert val is None

    # 3. The VTherm should be initialized with all presets and correct temperature
    assert vtherm
    assert isinstance(vtherm, ThermostatOverSwitch)
    assert vtherm.preset_modes == [
        PRESET_NONE,
        PRESET_FROST_PROTECTION,
        PRESET_ECO,
        PRESET_COMFORT,
        PRESET_BOOST,
    ]

    assert vtherm._presets == {
        PRESET_FROST_PROTECTION: temps["frost_temp"],
        PRESET_ECO: temps["eco_temp"],
        PRESET_COMFORT: temps["comfort_temp"],
        PRESET_BOOST: temps["boost_temp"],
        PRESET_ECO_AC: temps["eco_ac_temp"],
        PRESET_COMFORT_AC: temps["comfort_ac_temp"],
        PRESET_BOOST_AC: temps["boost_ac_temp"],
    }

    # Preset away should be initialized with the central config
    assert vtherm._presets_away == {
        PRESET_FROST_PROTECTION
        + PRESET_AWAY_SUFFIX: FULL_CENTRAL_CONFIG["frost_away_temp"],
        PRESET_ECO + PRESET_AWAY_SUFFIX: FULL_CENTRAL_CONFIG["eco_away_temp"],
        PRESET_COMFORT + PRESET_AWAY_SUFFIX: FULL_CENTRAL_CONFIG["comfort_away_temp"],
        PRESET_BOOST + PRESET_AWAY_SUFFIX: FULL_CENTRAL_CONFIG["boost_away_temp"],
        PRESET_ECO_AC + PRESET_AWAY_SUFFIX: FULL_CENTRAL_CONFIG["eco_ac_away_temp"],
        PRESET_COMFORT_AC
        + PRESET_AWAY_SUFFIX: FULL_CENTRAL_CONFIG["comfort_ac_away_temp"],
        PRESET_BOOST_AC + PRESET_AWAY_SUFFIX: FULL_CENTRAL_CONFIG["boost_ac_away_temp"],
    }


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_add_number_for_over_switch_use_central_presets_and_restore(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_config
):
    """Test the construction of a over switch vtherm with
    use central config for PRESET and PRESENCE.
    It also have old temp config value which should be not used.
    So it should have no Temp NumberEntity."""

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    temps = {
        "frost_away_temp": 23,
        "eco_away_temp": 23,
        "comfort_away_temp": 23,  # To test absence of preset
        "boost_away_temp": 23,
    }
    temps_missing = {
        "frost_temp": 10,
        "eco_temp": 17.1,
        "comfort_temp": 18.1,
        "boost_temp": 19.1,
        "eco_ac_temp": 25.1,
        "comfort_ac_temp": 23.1,
        "boost_ac_temp": 21.1,
        "eco_ac_away_temp": 30.5,
        "comfort_ac_away_temp": 30.6,
        "boost_ac_away_temp": 30.7,
    }

    vtherm_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: "TheOverSwitchVTherm",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_AC_MODE: False,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_CYCLE_MIN: 5,
            CONF_HEATER: "switch.mock_switch1",
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
            CONF_PRESENCE_SENSOR: "person.presence_sensor",
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        }
        | temps
        | temps_missing,
    )

    # The restore should be used
    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        return_value=State(entity_id="number.mock_valve", state="23"),
    ) as mock_restore_state:
        vtherm: BaseThermostat = await create_thermostat(
            hass, vtherm_entry, "climate.theoverswitchvtherm"
        )

        assert vtherm.use_central_config_temperature is True

        # We should try to restore all 4 temp entities and the VTherm itself
        assert mock_restore_state.call_count == 4 + 2

    # 1. We search for NumberEntities
    for preset_name, value in temps.items():
        temp_entity = search_entity(
            hass,
            "number.theoverswitchvtherm_preset_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace(PRESET_TEMP_SUFFIX, "")
            .replace(PRESET_AC_SUFFIX, " ac")
            .replace(PRESET_AWAY_SUFFIX, " away")
            .lower()
        )

        # Find temp Number into vtherm_api
        val = vtherm_api.get_temperature_number_value(
            config_id=vtherm_entry.entry_id, preset_name=preset_name
        )
        assert val == value

    # 2. We search for NumberEntities to be missing
    for preset_name, value in temps_missing.items():
        temp_entity = search_entity(
            hass,
            "number.theoverswitchvtherm_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity is None

        # Find temp Number into vtherm_api
        val = vtherm_api.get_temperature_number_value(
            config_id=vtherm_entry.entry_id, preset_name=preset_name
        )
        assert val is None

    # 3. The VTherm should be initialized with all presets and correct temperature
    assert vtherm
    assert isinstance(vtherm, ThermostatOverSwitch)
    assert vtherm.preset_modes == [
        PRESET_NONE,
        PRESET_FROST_PROTECTION,
        PRESET_ECO,
        # PRESET_COMFORT, because temp is 0
        PRESET_BOOST,
    ]

    # Preset away should be empty cause we use central config for presets
    assert vtherm._presets == {
        PRESET_FROST_PROTECTION: FULL_CENTRAL_CONFIG["frost_temp"],
        PRESET_ECO: FULL_CENTRAL_CONFIG["eco_temp"],
        PRESET_COMFORT: FULL_CENTRAL_CONFIG["comfort_temp"],
        PRESET_BOOST: FULL_CENTRAL_CONFIG["boost_temp"],
    }

    assert vtherm._presets_away == {
        PRESET_FROST_PROTECTION + PRESET_AWAY_SUFFIX: temps["frost_away_temp"],
        PRESET_ECO + PRESET_AWAY_SUFFIX: temps["eco_away_temp"],
        PRESET_COMFORT + PRESET_AWAY_SUFFIX: temps["comfort_away_temp"],
        PRESET_BOOST + PRESET_AWAY_SUFFIX: temps["boost_away_temp"],
    }


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_change_central_config_temperature(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_config
):
    """Test the construction of a over valve vtherm with
    use central config for PRESET and PRESENCE.
    When changing the central configuration temperature, the VTherm
    target temperature should change also
    For the test, another Vtherm with non central conf is used to
    check it is not impacted by central config temp change"""

    vtherm_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheValveConfigMockName",
        unique_id="valveConfigUniqueId",
        data={
            CONF_NAME: "TheOverValveVTherm",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_CYCLE_MIN: 5,
            CONF_VALVE: "switch.mock_valve",
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        },
    )

    # Their is nothing to restore so temp values should be initialized with default values
    vtherm: BaseThermostat = await create_thermostat(
        hass, vtherm_entry, "climate.theovervalvevtherm"
    )

    assert vtherm.use_central_config_temperature is True

    # Creates another VTherm which is NOT binded to central configuration
    vtherm2_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheValve2ConfigMockName",
        unique_id="valve2ConfigUniqueId",
        data={
            CONF_NAME: "TheOverValveVTherm2",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_CYCLE_MIN: 5,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_VALVE: "switch.mock_valve",
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
            CONF_PRESENCE_SENSOR: "person.presence_sensor",
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        },
    )

    # Their is nothing to restore so temp values should be initialized with default values
    vtherm2: BaseThermostat = await create_thermostat(
        hass, vtherm2_entry, "climate.theovervalvevtherm2"
    )

    assert vtherm2.use_central_config_temperature is False

    # 1. No temp Number should be present cause central config mode
    preset_name = "boost"
    temp_entity = search_entity(
        hass,
        "number.theovervalvevtherm_" + preset_name + PRESET_TEMP_SUFFIX,
        NUMBER_DOMAIN,
    )
    assert not temp_entity
    assert (
        vtherm.find_preset_temp(preset_name) == 19.1
    )  # 19.1 is the value of the central_config boost preset temp

    assert (
        vtherm2.find_preset_temp(preset_name) == 15
    )  # 15 is the min temp which is the default

    # 2. change the central_config temp Number entity value
    temp_entity = search_entity(
        hass,
        "number.central_configuration_preset_" + preset_name + PRESET_TEMP_SUFFIX,
        NUMBER_DOMAIN,
    )

    assert temp_entity
    assert temp_entity.value == 19.1

    await temp_entity.async_set_native_value(20.3)
    assert temp_entity
    assert temp_entity.value == 20.3
    # Wait for async job to complete
    await asyncio.sleep(0.1)

    assert vtherm.find_preset_temp(preset_name) == 20.3
    # No change for VTherm 2
    assert (
        vtherm2.find_preset_temp(preset_name) == 15
    )  # 15 is the min temp which is the default


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_change_vtherm_temperature(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_config
):
    """Test the construction of a over valve vtherm with
    use central config for PRESET and PRESENCE.
    When changing the central configuration temperature, the VTherm
    target temperature should change also"""

    vtherm_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheValveConfigMockName",
        unique_id="valveConfigUniqueId",
        data={
            CONF_NAME: "TheOverValveVTherm",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_CYCLE_MIN: 5,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_VALVE: "switch.mock_valve",
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        },
    )

    # Their is nothing to restore so temp values should be initialized with default values
    vtherm: BaseThermostat = await create_thermostat(
        hass, vtherm_entry, "climate.theovervalvevtherm"
    )

    assert vtherm.use_central_config_temperature is True

    # Creates another VTherm which is NOT binded to central configuration
    vtherm2_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheValve2ConfigMockName",
        unique_id="valve2ConfigUniqueId",
        data={
            CONF_NAME: "TheOverValveVTherm2",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_CYCLE_MIN: 5,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_VALVE: "switch.mock_valve",
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
            CONF_PRESENCE_SENSOR: "person.presence_sensor",
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        },
    )

    # Their is nothing to restore so temp values should be initialized with default values
    vtherm2: BaseThermostat = await create_thermostat(
        hass, vtherm2_entry, "climate.theovervalvevtherm2"
    )

    assert vtherm2.use_central_config_temperature is False

    # 1. No temp Number should be present cause central config mode
    preset_name = "boost"
    temp_entity = search_entity(
        hass,
        "number.theovervalvevtherm_" + preset_name + PRESET_TEMP_SUFFIX,
        NUMBER_DOMAIN,
    )
    assert not temp_entity
    assert (
        vtherm.find_preset_temp(preset_name) == 19.1
    )  # 19.1 is the value of the central_config boost preset temp

    assert (
        vtherm2.find_preset_temp(preset_name) == 15
    )  # 15 is the min temp which is the default

    # 2. change the central_config temp Number entity value
    temp_entity = search_entity(
        hass,
        "number.central_configuration_preset_" + preset_name + PRESET_TEMP_SUFFIX,
        NUMBER_DOMAIN,
    )

    assert temp_entity
    assert temp_entity.value == 19.1

    await temp_entity.async_set_native_value(20.3)
    assert temp_entity
    assert temp_entity.value == 20.3
    # Wait for async job to complete
    await asyncio.sleep(0.1)

    assert vtherm.find_preset_temp(preset_name) == 20.3
    # No change for VTherm 2
    assert (
        vtherm2.find_preset_temp(preset_name) == 15
    )  # 15 is the min temp which is the default


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_change_vtherm_temperature_with_presence(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_config
):
    """Test the construction of a over valve vtherm with
    no central config for PRESET and PRESENCE.
    When changing the Vtherm temperature, the VTherm
    target temperature should change but not the temp
    of a second which is linked to central config
    """

    vtherm_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheValveConfigMockName",
        unique_id="valveConfigUniqueId",
        data={
            CONF_NAME: "TheOverValveVTherm",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_CYCLE_MIN: 5,
            CONF_AC_MODE: True,
            CONF_VALVE: "switch.mock_valve",
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
            CONF_PRESENCE_SENSOR: "person.presence_sensor",
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        },
    )

    # Their is nothing to restore so temp values should be initialized with default values
    vtherm: BaseThermostat = await create_thermostat(
        hass, vtherm_entry, "climate.theovervalvevtherm"
    )
    assert vtherm.use_central_config_temperature is False
    await vtherm.async_set_hvac_mode(HVACMode.COOL)
    await vtherm.async_set_preset_mode(PRESET_BOOST)
    await send_presence_change_event(
        vtherm, STATE_ON, STATE_OFF, NowClass.get_now(hass), True
    )
    assert vtherm.target_temperature == 30  # default value

    # Creates another VTherm which is NOT binded to central configuration
    vtherm2_entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheValve2ConfigMockName",
        unique_id="valve2ConfigUniqueId",
        data={
            CONF_NAME: "TheOverValveVTherm2",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_CYCLE_MIN: 5,
            CONF_VALVE: "switch.mock_valve",
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        },
    )

    # Their is nothing to restore so temp values should be initialized with default values
    vtherm2: BaseThermostat = await create_thermostat(
        hass, vtherm2_entry, "climate.theovervalvevtherm2"
    )
    assert vtherm2.use_central_config_temperature is True

    # 1. Temp Number should be present cause no central config mode
    preset_name = "boost"
    temp_entity = search_entity(
        hass,
        "number.theovervalvevtherm_preset_" + preset_name + "_ac_away_temp",
        NUMBER_DOMAIN,
    )
    assert temp_entity
    assert temp_entity.state == 30  # default value in ac_mode
    assert vtherm.find_preset_temp(preset_name) == 30

    # 19.1 is the value of the central_config boost preset temp
    assert vtherm2.find_preset_temp(preset_name) == 19.1

    # 2. change the temp Number entity value for each VTherm
    temp_entity = search_entity(
        hass,
        "number.theovervalvevtherm_preset_" + preset_name + "_ac_away_temp",
        NUMBER_DOMAIN,
    )

    assert temp_entity
    assert temp_entity.value == 30

    await temp_entity.async_set_native_value(20.3)
    assert temp_entity
    assert temp_entity.value == 20.3
    # Wait for async job to complete
    await asyncio.sleep(0.1)

    # 30 because I change the preset _away but someeone is present
    assert vtherm.find_preset_temp(preset_name) == 30
    assert vtherm.target_temperature == 30  # default value

    # No change for VTherm 2
    assert (
        vtherm2.find_preset_temp(preset_name) == 19.1
    )  # 15 is the min temp which is the default

    # 3. We change now the current preset temp
    temp_entity = search_entity(
        hass,
        "number.theovervalvevtherm_preset_" + preset_name + "_ac_temp",
        NUMBER_DOMAIN,
    )

    assert temp_entity
    assert temp_entity.value == 30

    await temp_entity.async_set_native_value(20.3)
    assert temp_entity
    assert temp_entity.value == 20.3
    # Wait for async job to complete
    await asyncio.sleep(0.1)

    # the target should have been change
    assert vtherm.find_preset_temp(preset_name) == 20.3
    assert vtherm.target_temperature == 20.3  # default value
