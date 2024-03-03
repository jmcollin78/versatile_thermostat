""" Test the NumberEntity taht holds the temperature of a VTherm or of a Central configuration """

# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

# from unittest.mock import patch, call
# from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

# from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.number import NumberEntity, DOMAIN as NUMBER_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
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
            CONF_SECURITY_DELAY_MIN: 61,
            CONF_SECURITY_MIN_ON_PERCENT: 0.5,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.2,
            CONF_ADD_CENTRAL_BOILER_CONTROL: False,
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
            "number.central_configuration_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace("_temp", "")
            .replace("_ac", " ac")
            .replace("_away", " away")
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
            CONF_SECURITY_DELAY_MIN: 61,
            CONF_SECURITY_MIN_ON_PERCENT: 0.5,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.2,
            CONF_ADD_CENTRAL_BOILER_CONTROL: False,
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
            "number.central_configuration_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace("_temp", "")
            .replace("_ac", " ac")
            .replace("_away", " away")
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
            CONF_SECURITY_DELAY_MIN: 61,
            CONF_SECURITY_MIN_ON_PERCENT: 0.5,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.2,
            CONF_ADD_CENTRAL_BOILER_CONTROL: False,
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
            "number.central_configuration_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace("_temp", "")
            .replace("_ac", " ac")
            .replace("_away", " away")
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
            CONF_SECURITY_DELAY_MIN: 61,
            CONF_SECURITY_MIN_ON_PERCENT: 0.5,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.2,
            CONF_ADD_CENTRAL_BOILER_CONTROL: False,
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
            "number.central_configuration_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace("_temp", "")
            .replace("_ac", " ac")
            .replace("_away", " away")
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
    for preset_name, value in temps.items():
        temp_entity = search_entity(
            hass,
            "number.central_configuration_" + preset_name,
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

    # 1. We search for NumberEntities
    for preset_name, value in temps.items():
        temp_entity = search_entity(
            hass,
            "number.theoverswitchvtherm_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace("_temp", "")
            .replace("_ac", " ac")
            .replace("_away", " away")
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
    So it should have no Temp NumberEntity"""

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    temps = {
        "frost_away_temp": 23,
        "eco_away_temp": 23,
        "comfort_away_temp": 23,
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
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_central_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_AC_MODE: False,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_CYCLE_MIN: 5,
            CONF_HEATER: "switch.mock_switch1",
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
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

    # The restore should not be used
    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        return_value=State(entity_id="number.mock_valve", state="23"),
    ) as mock_restore_state:
        vtherm: BaseThermostat = await create_thermostat(
            hass, vtherm_entry, "climate.theoverswitchvtherm"
        )

        # We should try to restore all 4 temp entities
        assert mock_restore_state.call_count == 4

    # 1. We search for NumberEntities
    for preset_name, value in temps.items():
        temp_entity = search_entity(
            hass,
            "number.theoverswitchvtherm_" + preset_name,
            NUMBER_DOMAIN,
        )
        assert temp_entity
        assert temp_entity.state == value

        # This test is dependent to translation en.json. If translations change
        # this may fails
        assert (
            temp_entity.name.lower()
            == preset_name.replace("_temp", "")
            .replace("_ac", " ac")
            .replace("_away", " away")
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
