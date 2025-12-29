# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the Security featrure """
from unittest.mock import patch, call, PropertyMock, MagicMock
from datetime import timedelta, datetime
import logging

from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.feature_safety_manager import (
    FeatureSafetyManager,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)

# @pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_migration_security_safety(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the migration of security parameters to safety in English"""
    central_config_entry = MockConfigEntry(
        # old version is 2.0
        version=2,
        minor_version=0,
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: "migrationName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_UNDERLYING_LIST: ["switch.under1"],
            "security_delay_min": 61,
            "security_min_on_percent": 0.5,
            "security_default_on_percent": 0.2,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
        },
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverSwitch = search_entity(
        hass, "climate.migrationname", "climate"
    )

    assert entity is not None

    assert entity.safety_manager.safety_min_on_percent == 0.5
    assert entity.safety_manager.safety_default_on_percent == 0.2
    assert entity.safety_manager.safety_delay_min == 61

    entity.remove_thermostat()

async def test_migration_of_central_config(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the clean_central_config_doubon of base_thermostat"""
    central_config_entry = MockConfigEntry(
        version=2,
        minor_version=0,
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: CENTRAL_CONFIG_NAME,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_MINIMAL_ACTIVATION_DELAY: 11,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 61,
            CONF_SAFETY_MIN_ON_PERCENT: 0.5,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.2,
            # The old central_boiler parameter
            "add_central_boiler_control": True,
            CONF_CENTRAL_BOILER_ACTIVATION_SRV: "switch.pompe_chaudiere/switch.turn_on",
            CONF_CENTRAL_BOILER_DEACTIVATION_SRV: "switch.pompe_chaudiere/switch.turn_off",
            CONF_CENTRAL_BOILER_ACTIVATION_DELAY_SEC: 10,
        },
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(
        hass, "climate.thecentralconfigmockname", "climate"
    )

    assert entity is None

    assert count_entities(hass, "climate.thecentralconfigmockname", "climate") == 0

    # Test that VTherm API find the CentralConfig
    api = VersatileThermostatAPI.get_vtherm_api(hass)
    central_configuration = api.find_central_configuration()
    assert central_configuration is not None

    assert central_config_entry.data.get(CONF_USE_CENTRAL_BOILER_FEATURE) is True

    # Test that VTherm API have any central boiler entities
    # It should have been migrated and initialized
    assert api.central_boiler_manager.nb_active_device_for_boiler == 0
    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 0  # the default value is 0
