# pylint: disable=unused-argument, line-too-long
""" Test the Versatile Thermostat config flow """

from homeassistant import data_entry_flow
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import SOURCE_USER, ConfigEntry

from custom_components.versatile_thermostat.const import DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_show_form(hass: HomeAssistant, init_vtherm_api) -> None:
    """Test that the form is served with no input"""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# Disable this test which don't work anymore (kill the pytest !)
# @pytest.mark.skip
async def test_user_config_flow_over_switch(
    hass: HomeAssistant, skip_hass_states_get, init_central_config
):  # pylint: disable=unused-argument
    """Test the config flow with all thermostat_over_switch features and central config on"""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"] == [
        "main",
        "type",
        "features",
        "presets",
        "advanced",
    ]
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "main"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "type"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "type"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HEATER: "switch.mock_switch",
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_AC_MODE: False,
            CONF_INVERSE_SWITCH: False,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"] == [
        "main",
        "type",
        "features",
        "tpi",
        "presets",
        "advanced",
        "finalize",  # because by default all options are "use central config"
    ]

    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tpi"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "tpi"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_TPI_CENTRAL_CONFIG: True}
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "presets"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presets"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_PRESETS_CENTRAL_CONFIG: True}
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "features"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "features"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_WINDOW_FEATURE: True,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "type",
        "features",
        "tpi",
        "presets",
        "window",
        "motion",
        "power",
        "presence",
        "advanced",
        # "finalize" : because for motion we need an motion sensor
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "window"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "window"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_WINDOW_SENSOR: "binary_sensor.window_sensor",
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "motion"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "motion"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MOTION_SENSOR: "input_boolean.motion_sensor",
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "power"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "power"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_POWER_CENTRAL_CONFIG: True}
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"] == [
        "main",
        "type",
        "features",
        "tpi",
        "presets",
        "window",
        "motion",
        "power",
        "presence",
        "advanced",
        "finalize",
    ]
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "presence"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presence"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USE_PRESENCE_CENTRAL_CONFIG: True,
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "advanced"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "advanced"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_ADVANCED_CENTRAL_CONFIG: True}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "finalize"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result.get("errors") is None
    assert result["data"] == (
        MOCK_TH_OVER_SWITCH_USER_CONFIG
        | MOCK_TH_OVER_SWITCH_MAIN_CONFIG
        | MOCK_TH_OVER_SWITCH_TYPE_CONFIG
        | {CONF_WINDOW_SENSOR: "binary_sensor.window_sensor"}
        | {CONF_MOTION_SENSOR: "input_boolean.motion_sensor"}
        # | {CONF_PRESENCE_SENSOR: "person.presence_sensor"} now in central config
        | {
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_TPI_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_WINDOW_CENTRAL_CONFIG: True,
            CONF_USE_MOTION_CENTRAL_CONFIG: True,
            CONF_USE_POWER_CENTRAL_CONFIG: True,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: True,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USE_CENTRAL_MODE: True,
            CONF_USED_BY_CENTRAL_BOILER: False,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
        }
    )
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 1
    assert result["result"].title == "TheOverSwitchMockName"
    assert isinstance(result["result"], ConfigEntry)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# TODO this test fails when run in // but works alone
@pytest.mark.skip
async def test_user_config_flow_over_climate(
    hass: HomeAssistant, skip_hass_states_get
):  # pylint: disable=unused-argument
    """Test the config flow with all thermostat_over_switch features and never use central config.
    We don't use any features"""
    # await create_central_config(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"] == [
        "main",
        "type",
        "features",
        "presets",
        "advanced",
    ]
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "main"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "TheOverClimateMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: True,
            # Keep default values which are False
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            # Keep default values which are False
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "type"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "type"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CLIMATE: "climate.mock_climate",
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_STRONG,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"] == [
        "main",
        "type",
        "features",
        "presets",
        "advanced",
        # "finalize",  # because we need Advanced default parameters
    ]
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "presets"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "presets"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_PRESETS_CENTRAL_CONFIG: False}
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "features"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "features"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_WINDOW_FEATURE: False,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "type",
        "features",
        "presets",
        "advanced",
        # "finalize", finalize is not present waiting for advanced configuration
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "advanced"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "advanced"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USE_ADVANCED_CENTRAL_CONFIG: False},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "advanced"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.4,
            CONF_SECURITY_DEFAULT_ON_PERCENT: 0.3,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "type",
        "features",
        "presets",
        "advanced",
        "finalize",  # Now finalize is present
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "finalize"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result.get("errors") is None
    assert result[
        "data"
    ] == MOCK_TH_OVER_CLIMATE_USER_CONFIG | MOCK_TH_OVER_CLIMATE_MAIN_CONFIG | MOCK_TH_OVER_CLIMATE_CENTRAL_MAIN_CONFIG | MOCK_TH_OVER_CLIMATE_TYPE_CONFIG | {
        CONF_MINIMAL_ACTIVATION_DELAY: 10,
        CONF_SECURITY_DELAY_MIN: 5,
        CONF_SECURITY_MIN_ON_PERCENT: 0.4,
        CONF_SECURITY_DEFAULT_ON_PERCENT: 0.3,
    } | MOCK_DEFAULT_FEATURE_CONFIG | {
        CONF_USE_MAIN_CENTRAL_CONFIG: False,
        CONF_USE_TPI_CENTRAL_CONFIG: False,
        CONF_USE_PRESETS_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_TPI_CENTRAL_CONFIG: False,
        CONF_USE_WINDOW_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_CENTRAL_CONFIG: False,
        CONF_USE_POWER_CENTRAL_CONFIG: False,
        CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
        CONF_USE_ADVANCED_CENTRAL_CONFIG: False,
        CONF_USED_BY_CENTRAL_BOILER: False,
    }
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 1
    assert result["result"].title == "TheOverClimateMockName"
    assert isinstance(result["result"], ConfigEntry)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# TODO reimplement this
@pytest.mark.skip
async def test_user_config_flow_window_auto_ok(
    hass: HomeAssistant,
    skip_hass_states_get,
    skip_control_heating,  # pylint: disable=unused-argument
):
    """Test the config flow with only window auto feature"""
    await create_central_config(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "main"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TYPE_CONFIG
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "tpi"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_TPI_CENTRAL_CONFIG: False}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "tpi"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TPI_CONFIG
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "presets"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_PRESETS_CENTRAL_CONFIG: True}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "window"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USE_WINDOW_CENTRAL_CONFIG: False},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "window"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_WINDOW_AUTO_CONFIG,
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "advanced"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_ADVANCED_CENTRAL_CONFIG: True}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["data"] == {
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_NAME: "TheOverSwitchMockName",
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_DEVICE_POWER: 1,
        CONF_USE_WINDOW_FEATURE: True,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_WINDOW_DELAY: 30,  # the default value is added
        CONF_USE_CENTRAL_MODE: True,  # True is the defaulf value
    } | MOCK_TH_OVER_SWITCH_TYPE_CONFIG | MOCK_TH_OVER_SWITCH_TPI_CONFIG | MOCK_WINDOW_AUTO_CONFIG | {
        CONF_USE_MAIN_CENTRAL_CONFIG: True,
        CONF_USE_TPI_CENTRAL_CONFIG: False,
        CONF_USE_PRESETS_CENTRAL_CONFIG: True,
        CONF_USE_WINDOW_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_CENTRAL_CONFIG: False,
        CONF_USE_POWER_CENTRAL_CONFIG: False,
        CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
        CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
        CONF_USED_BY_CENTRAL_BOILER: True,
    }
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 1
    assert result["result"].title == "TheOverSwitchMockName"
    assert isinstance(result["result"], ConfigEntry)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# TODO reimplement this
@pytest.mark.skip
async def test_user_config_flow_window_auto_ko(
    hass: HomeAssistant, skip_hass_states_get  # pylint: disable=unused-argument
):
    """Test the config flow with window auto and window features -> not allowed"""

    await create_central_config(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "main"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TYPE_CONFIG
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "tpi"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_TPI_CENTRAL_CONFIG: False}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "tpi"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TPI_CONFIG
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "presets"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_PRESETS_CENTRAL_CONFIG: True}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "window"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_WINDOW_SENSOR: "binary_sensor.window_sensor",
            CONF_USE_WINDOW_CENTRAL_CONFIG: False,
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "window"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_WINDOW_DELAY_CONFIG,
    )

    # Since issue #280 we cannot have the error because we only display the
    # MOCK_WINDOW_DELAY_CONFIG form if we have a sensor configured
    assert result["type"] == FlowResultType.MENU
    # We should stay on window with an error
    assert result.get("errors") is None
    #    "window_sensor_entity_id": "window_open_detection_method"
    # }
    assert result["step_id"] == "advanced"


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# TODO reimplement this
@pytest.mark.skip
async def test_user_config_flow_over_4_switches(
    hass: HomeAssistant,
    skip_hass_states_get,
    skip_control_heating,  # pylint: disable=unused-argument
):
    """Test the config flow with 4 switchs thermostat_over_switch features"""

    await create_central_config(hass)

    SOURCE_CONFIG = {  # pylint: disable=invalid-name
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
    }

    MAIN_CONFIG = {  # pylint: disable=invalid-name
        CONF_NAME: "TheOver4SwitchMockName",
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_DEVICE_POWER: 1,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_USE_MAIN_CENTRAL_CONFIG: True,
        CONF_USE_CENTRAL_MODE: False,
        CONF_USED_BY_CENTRAL_BOILER: False,
    }

    TYPE_CONFIG = {  # pylint: disable=invalid-name
        CONF_HEATER: "switch.mock_switch1",
        CONF_HEATER_2: "switch.mock_switch2",
        CONF_HEATER_3: "switch.mock_switch3",
        CONF_HEATER_4: "switch.mock_switch4",
        CONF_HEATER_KEEP_ALIVE: 0,
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_AC_MODE: False,
        CONF_INVERSE_SWITCH: False,
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == SOURCE_USER

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=SOURCE_CONFIG,
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "main"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MAIN_CONFIG,
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=TYPE_CONFIG,
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "tpi"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_TPI_CENTRAL_CONFIG: True}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "presets"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_PRESETS_CENTRAL_CONFIG: True}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "advanced"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_ADVANCED_CENTRAL_CONFIG: True}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["data"] == (
        SOURCE_CONFIG
        | MAIN_CONFIG
        | TYPE_CONFIG
        | {
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_TPI_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: True,
            CONF_USE_WINDOW_CENTRAL_CONFIG: False,
            CONF_USE_MOTION_CENTRAL_CONFIG: False,
            CONF_USE_POWER_CENTRAL_CONFIG: False,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
        }
    )
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 1
    assert result["result"].title == "TheOver4SwitchMockName"
    assert isinstance(result["result"], ConfigEntry)
