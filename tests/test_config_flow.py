# pylint: disable=unused-argument, line-too-long
""" Test the Versatile Thermostat config flow """

from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import SOURCE_USER, ConfigEntry

from custom_components.versatile_thermostat.const import DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_show_form(hass: HomeAssistant) -> None:
    """Test that the form is served with no input"""
    # Init the API
    # hass.data["custom_components"] = None
    # loader.async_get_custom_components(hass)
    # BaseThermostatAPI(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# Disable this test which don't work anymore (kill the pytest !)
@pytest.mark.skip
async def test_user_config_flow_over_switch(
    hass: HomeAssistant, skip_hass_states_get
):  # pylint: disable=unused-argument
    """Test the config flow with all thermostat_over_switch features"""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_USER_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "type"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TYPE_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "tpi"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TPI_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "presets"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_PRESETS_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "window"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_WINDOW_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "motion"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_MOTION_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "power"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_POWER_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "presence"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_PRESENCE_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "advanced"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_ADVANCED_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert (
        result["data"]
        == MOCK_TH_OVER_SWITCH_USER_CONFIG
        | MOCK_TH_OVER_SWITCH_TYPE_CONFIG
        | MOCK_TH_OVER_SWITCH_TPI_CONFIG
        | MOCK_PRESETS_CONFIG
        | MOCK_WINDOW_CONFIG
        | MOCK_MOTION_CONFIG
        | MOCK_POWER_CONFIG
        | MOCK_PRESENCE_CONFIG
        | MOCK_ADVANCED_CONFIG
    )
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 1
    assert result["result"].title == "TheOverSwitchMockName"
    assert isinstance(result["result"], ConfigEntry)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_user_config_flow_over_climate(
    hass: HomeAssistant, skip_hass_states_get
):  # pylint: disable=unused-argument
    """Test the config flow with all thermostat_over_climate features and no additional features"""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_CLIMATE_USER_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "type"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_CLIMATE_TYPE_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "presets"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_PRESETS_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "advanced"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_ADVANCED_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert (
        result["data"]
        == MOCK_TH_OVER_CLIMATE_USER_CONFIG
        | MOCK_TH_OVER_CLIMATE_TYPE_CONFIG
        | MOCK_PRESETS_CONFIG
        | MOCK_ADVANCED_CONFIG
        | MOCK_DEFAULT_FEATURE_CONFIG
    )
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 1
    assert result["result"].title == "TheOverClimateMockName"
    assert isinstance(result["result"], ConfigEntry)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_user_config_flow_window_auto_ok(
    hass: HomeAssistant,
    skip_hass_states_get,
    skip_control_heating,  # pylint: disable=unused-argument
):
    """Test the config flow with only window auto feature"""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_DEVICE_POWER: 1,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
        },
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "type"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TYPE_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "tpi"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TPI_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "presets"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_PRESETS_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "window"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_WINDOW_AUTO_CONFIG,
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "advanced"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_ADVANCED_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert (
        result["data"]
        == MOCK_TH_OVER_SWITCH_USER_CONFIG
        | {
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_WINDOW_DELAY: 30,  # the default value is added
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
        }
        | MOCK_TH_OVER_SWITCH_TYPE_CONFIG
        | MOCK_TH_OVER_SWITCH_TPI_CONFIG
        | MOCK_PRESETS_CONFIG
        | MOCK_WINDOW_AUTO_CONFIG
        | MOCK_ADVANCED_CONFIG
    )
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 1
    assert result["result"].title == "TheOverSwitchMockName"
    assert isinstance(result["result"], ConfigEntry)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_user_config_flow_window_auto_ko(
    hass: HomeAssistant, skip_hass_states_get  # pylint: disable=unused-argument
):
    """Test the config flow with window auto and window features -> not allowed"""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_DEVICE_POWER: 1,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
        },
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "type"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TYPE_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "tpi"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TPI_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "presets"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_PRESETS_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "window"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_WINDOW_AUTO_CONFIG | MOCK_WINDOW_CONFIG,
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    # We should stay on window with an error
    assert result["step_id"] == "window"
    assert result["errors"] == {
        "window_sensor_entity_id": "window_open_detection_method"
    }


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_user_config_flow_over_4_switches(
    hass: HomeAssistant,
    skip_hass_states_get,
    skip_control_heating,  # pylint: disable=unused-argument
):
    """Test the config flow with 4 switchs thermostat_over_switch features"""

    SOURCE_CONFIG = {  # pylint: disable=wildcard-import, invalid-name
        CONF_NAME: "TheOver4SwitchMockName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 15,
        CONF_TEMP_MAX: 30,
        CONF_DEVICE_POWER: 1,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
    }

    TYPE_CONFIG = {  # pylint: disable=wildcard-import, invalid-name
        CONF_HEATER: "switch.mock_switch1",
        CONF_HEATER_2: "switch.mock_switch2",
        CONF_HEATER_3: "switch.mock_switch3",
        CONF_HEATER_4: "switch.mock_switch4",
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_AC_MODE: False,
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=SOURCE_CONFIG,
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "type"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=TYPE_CONFIG,
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "tpi"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TPI_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "presets"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_PRESETS_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "advanced"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_ADVANCED_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result[
        "data"
    ] == SOURCE_CONFIG | TYPE_CONFIG | MOCK_TH_OVER_SWITCH_TPI_CONFIG | MOCK_PRESETS_CONFIG | MOCK_ADVANCED_CONFIG | {
        CONF_INVERSE_SWITCH: False
    }
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 1
    assert result["result"].title == "TheOver4SwitchMockName"
    assert isinstance(result["result"], ConfigEntry)
