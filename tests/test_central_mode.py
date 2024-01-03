# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the central_configuration """
from unittest.mock import patch  # , call

# from datetime import datetime  # , timedelta

from homeassistant.core import HomeAssistant

from homeassistant.components.climate import HVACMode

# from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import


# @pytest.mark.parametrize("expected_lingering_tasks", [True])
# @pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_config_with_central_mode_true(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """A config with central_mode True"""

    # Add a Switch VTherm
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_USE_CENTRAL_MODE: True,
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
        },
    )

    with patch("homeassistant.core.ServiceRegistry.async_call"):
        entity: ThermostatOverSwitch = await create_thermostat(
            hass, entry, "climate.theoverswitchmockname"
        )
        assert entity
        assert entity.name == "TheOverSwitchMockName"
        assert entity.is_over_switch
        assert entity.is_controlled_by_central_mode
        assert entity.last_central_mode is None  # cause no central config exists


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_config_with_central_mode_false(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """A config with central_mode False"""

    # Add a Climate VTherm
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_USE_CENTRAL_MODE: False,
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
            CONF_CLIMATE: "climate.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
        },
    )

    with patch("homeassistant.core.ServiceRegistry.async_call"):
        entity: ThermostatOverSwitch = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate
        assert entity.is_controlled_by_central_mode is False
        assert entity.last_central_mode is None  # cause no central config exists


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_config_with_central_mode_none(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """A config with central_mode is None"""

    # Add a Switch VTherm
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverValveMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverValveMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_USE_CENTRAL_MODE: True,
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
            CONF_VALVE: "number.mock_valve",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
        },
    )

    with patch("homeassistant.core.ServiceRegistry.async_call"):
        entity: ThermostatOverSwitch = await create_thermostat(
            hass, entry, "climate.theovervalvemockname"
        )
        assert entity
        assert entity.name == "TheOverValveMockName"
        assert entity.is_over_valve
        assert entity.is_controlled_by_central_mode
        assert entity.last_central_mode is None  # cause no central config exists


async def test_switch_change_central_mode_true(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_config
):
    """test that changes with over_switch config with central_mode True are
    taken into account"""

    # Add a Switch VTherm
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_USE_CENTRAL_MODE: True,
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
        },
    )

    # 1 initialize entity and find select entity
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        entity: ThermostatOverSwitch = await create_thermostat(
            hass, entry, "climate.theoverswitchmockname"
        )
        assert entity
        assert entity.is_controlled_by_central_mode
        assert entity.last_central_mode is None

        # Find the select entity
        select_entity = search_entity(hass, "select.central_mode", SELECT_DOMAIN)

        assert select_entity
        assert select_entity.current_option == CENTRAL_MODE_AUTO
        assert select_entity.options == CENTRAL_MODES

        # start entity
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_BOOST)

        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_BOOST

    # 2 change central_mode to STOPPED
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_STOPPED)

        assert entity.last_central_mode is CENTRAL_MODE_STOPPED
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.preset_mode == PRESET_BOOST

    # 3 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT

        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # hvac_mode should be restored as before the STOP and preset should be restored with the last choosen preset (COMFORT here)
        assert entity.last_central_mode is CENTRAL_MODE_AUTO
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT

    # 4 change central_mode to COOL_ONLY
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_COOL_ONLY)

        # hvac_mode should be set to OFF because there is no COOL mode for this VTherm
        assert entity.last_central_mode is CENTRAL_MODE_COOL_ONLY
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.preset_mode == PRESET_COMFORT

    # 5 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # hvac_mode should be restored to HEAT
        assert entity.last_central_mode is CENTRAL_MODE_AUTO
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT

    # 6 change central_mode to HEAT_ONLY
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_HEAT_ONLY)

        # hvac_mode should stay in HEAT mode
        assert entity.last_central_mode is CENTRAL_MODE_HEAT_ONLY
        assert entity.hvac_mode == HVACMode.HEAT
        # No change
        assert entity.preset_mode == PRESET_COMFORT

    # 7 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # hvac_mode should be restored to HEAT
        assert entity.last_central_mode is CENTRAL_MODE_AUTO
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT

    # 8 change central_mode to FROST_PROTECTION
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_FROST_PROTECTION)

        # hvac_mode should stay in HEAT mode
        assert entity.last_central_mode is CENTRAL_MODE_FROST_PROTECTION
        assert entity.hvac_mode == HVACMode.HEAT
        # change to Frost
        assert entity.preset_mode == PRESET_FROST_PROTECTION

    # 9 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # hvac_mode should be restored to HEAT
        assert entity.last_central_mode is CENTRAL_MODE_AUTO
        assert entity.hvac_mode == HVACMode.HEAT
        # preset restored to COMFORT
        assert entity.preset_mode == PRESET_COMFORT


async def test_switch_ac_change_central_mode_true(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_config
):
    """test that changes with over_switch config with central_mode True are
    taken into account"""

    # Add a Switch VTherm
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_USE_CENTRAL_MODE: True,
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
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
            CONF_AC_MODE: True,
        },
    )

    # 1 initialize entity and find select entity
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        entity: ThermostatOverSwitch = await create_thermostat(
            hass, entry, "climate.theoverswitchmockname"
        )
        assert entity
        assert entity.is_controlled_by_central_mode
        assert entity.ac_mode is True
        assert entity.hvac_modes == [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]

        # Find the select entity
        select_entity = search_entity(hass, "select.central_mode", SELECT_DOMAIN)

        assert select_entity
        assert select_entity.current_option == CENTRAL_MODE_AUTO
        assert select_entity.options == CENTRAL_MODES

        # start entity in cooling mode
        await entity.async_set_hvac_mode(HVACMode.COOL)
        await entity.async_set_preset_mode(PRESET_BOOST)

        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_BOOST

    # 2 change central_mode to STOPPED
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_STOPPED)

        assert entity.hvac_mode == HVACMode.OFF
        assert entity.preset_mode == PRESET_BOOST

    # 3 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT

        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # hvac_mode should be restored as before the STOP and preset should be restored with the last choosen preset (COMFORT here)
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_COMFORT

    # 4 change central_mode to COOL_ONLY
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_COOL_ONLY)

        # hvac_mode should be set to OFF because there is no COOL mode for this VTherm
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_COMFORT

    # 5 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # hvac_mode should be restored to HEAT
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_COMFORT

    # 6 change central_mode to HEAT_ONLY
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_HEAT_ONLY)

        # hvac_mode should stay in HEAT mode
        assert entity.hvac_mode == HVACMode.HEAT
        # No change
        assert entity.preset_mode == PRESET_COMFORT

    # 7 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # hvac_mode should be restored to COOL
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_COMFORT

    # 8 change central_mode to FROST_PROTECTION
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_FROST_PROTECTION)

        # hvac_mode should stay in COOL mode
        assert entity.hvac_mode == HVACMode.HEAT
        # change to Frost
        assert entity.preset_mode == PRESET_FROST_PROTECTION

    # 9 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # hvac_mode should be restored to COOL
        assert entity.hvac_mode == HVACMode.COOL
        # preset restored to COMFORT
        assert entity.preset_mode == PRESET_COMFORT


async def test_climate_ac_change_central_mode_false(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_config
):
    """test that changes with over_climate config with central_mode False are
    not taken into account"""

    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {})

    # Add a Climate VTherm
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_USE_CENTRAL_MODE: False,
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
            CONF_CLIMATE: "climate.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
        },
    )

    with patch("homeassistant.core.ServiceRegistry.async_call"), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entity: ThermostatOverSwitch = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate
        assert entity.is_controlled_by_central_mode is False
        assert entity.hvac_modes == [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]

        # Find the select entity
        select_entity = search_entity(hass, "select.central_mode", SELECT_DOMAIN)

        assert select_entity
        assert select_entity.current_option == CENTRAL_MODE_AUTO
        assert select_entity.options == CENTRAL_MODES

        # start entity in Heating mode
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_BOOST)

        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_BOOST

    # 2 change central_mode to STOPPED
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_STOPPED)

        # No change
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_BOOST

    # 3 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT

        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # No change
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT

    # 4 change central_mode to COOL_ONLY
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_COOL_ONLY)

        # No change
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT

    # 5 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # No change
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT

    # 6 change central_mode to HEAT_ONLY
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_HEAT_ONLY)

        # No change
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT

    # 7 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # No change
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT

    # 8 change central_mode to FROST_PROTECTION
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_FROST_PROTECTION)

        # No change
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT

    # 9 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # No change
        assert entity.hvac_mode == HVACMode.HEAT
        assert entity.preset_mode == PRESET_COMFORT


async def test_climate_ac_only_change_central_mode_true(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_config
):
    """test that changes with over_climate with AC only config with central_mode True are
    taken into account
    Test also switching from central_mode without coming to AUTO each time"""

    fake_underlying_climate = MockClimate(
        hass,
        "mockUniqueId",
        "MockClimateName",
        entry_infos={},
        hvac_modes=[HVACMode.OFF, HVACMode.COOL],
    )

    # Add a Climate VTherm
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_USE_CENTRAL_MODE: True,
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
            CONF_CLIMATE: "climate.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.1,
        },
    )

    with patch("homeassistant.core.ServiceRegistry.async_call"), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entity: ThermostatOverSwitch = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate
        assert entity.is_controlled_by_central_mode is True
        assert entity.hvac_modes == [HVACMode.OFF, HVACMode.COOL]

        # Find the select entity
        select_entity = search_entity(hass, "select.central_mode", SELECT_DOMAIN)

        assert select_entity
        assert select_entity.current_option == CENTRAL_MODE_AUTO
        assert select_entity.options == CENTRAL_MODES

        # start entity in Cooling mode
        await entity.async_set_hvac_mode(HVACMode.COOL)
        await entity.async_set_preset_mode(PRESET_ECO)

        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_ECO

    # 2 change central_mode to STOPPED
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_STOPPED)

        # No change
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.preset_mode == PRESET_ECO

    # 3 change central_mode to HEAT ONLY after switching to COMFORT preset
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await entity.async_set_preset_mode(PRESET_COMFORT)
        assert entity.preset_mode == PRESET_COMFORT

        await select_entity.async_select_option(CENTRAL_MODE_HEAT_ONLY)

        # Stay in OFF because HEAT is not permitted
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.preset_mode == PRESET_COMFORT

    # 4 change central_mode to COOL_ONLY
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_COOL_ONLY)

        # switch back to COOL restoring the preset
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_COMFORT

    # 5 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # No change
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_COMFORT

    # 6 change central_mode to FROST_PROTECTION
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_FROST_PROTECTION)

        # No change
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.preset_mode == PRESET_COMFORT

    # 7 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # No change
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_COMFORT

    # 8 change central_mode to FROST_PROTECTION
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_FROST_PROTECTION)

        # No change
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.preset_mode == PRESET_COMFORT

    # 9 change back central_mode to COOL_ONLY
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_COOL_ONLY)

        # No change
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_COMFORT

    await entity.async_set_preset_mode(PRESET_ECO)
    # 10 change back central_mode to HEAT_ONLY
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_HEAT_ONLY)

        # Shutdown cause no HEAT
        assert entity.hvac_mode == HVACMode.OFF
        assert entity.preset_mode == PRESET_ECO

    # 11 change back central_mode to AUTO
    with patch("homeassistant.core.ServiceRegistry.async_call"):
        await select_entity.async_select_option(CENTRAL_MODE_AUTO)

        # No change
        assert entity.hvac_mode == HVACMode.COOL
        assert entity.preset_mode == PRESET_ECO
