# pylint: disable=unused-argument, line-too-long, too-many-lines
""" Test the Versatile Thermostat config flow """

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
# TODO Disable this test make the others tests failed
@pytest.mark.skip
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
        "features",
        "type",
        "presets",
        "window",
        "power",
        "presence",
        "advanced",
        "configuration_not_complete",
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
            CONF_CYCLE_MIN: 5.0,
            CONF_DEVICE_POWER: 1.0,
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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
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
        "features",
        "type",
        "tpi",
        "presets",
        "window",
        "power",
        "presence",
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
        "features",
        "type",
        "tpi",
        "presets",
        "window",
        "motion",
        "power",
        "presence",
        "advanced",
        "configuration_not_complete",
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
        "features",
        "type",
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
            CONF_USE_AUTO_START_STOP_FEATURE: False,
            CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: False,
            CONF_USE_CENTRAL_MODE: True,
            CONF_USED_BY_CENTRAL_BOILER: False,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_USE_CENTRAL_BOILER_FEATURE: False,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_NONE,
        }
    )
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 2
    assert result["result"].title == "TheOverSwitchMockName"
    assert isinstance(result["result"], ConfigEntry)

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# TODO this test fails when run in // but works alone
# @pytest.mark.skip
async def test_user_config_flow_over_climate(
    hass: HomeAssistant, skip_hass_states_get
):  # pylint: disable=unused-argument
    """Test the config flow with all thermostat_over_climate features and never use central config.
    We don't use any features"""
    # await create_central_config(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER

    # 1. Type
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
        "features",
        "type",
        "presets",
        "advanced",
        "lock",
        "configuration_not_complete",
    ]
    assert result.get("errors") is None

    # 2. Main
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
            CONF_USE_CENTRAL_MODE: False,
            # Keep default values which are False
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result.get("errors") == {}

    # 3. Main 2
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15.0,
            CONF_TEMP_MAX: 30.0,
            CONF_STEP_TEMPERATURE: 0.1,
            # Keep default values which are False
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    # 4. Type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "type"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "type"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
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
        "features",
        "type",
        "presets",
        "advanced",
        "lock",
        "configuration_not_complete",
        # "finalize",  # because we need Advanced default parameters
    ]
    assert result.get("errors") is None

    # 5. Presets
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

    # 6. Features
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
            CONF_USE_AUTO_START_STOP_FEATURE: False,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "presets",
        "advanced",
        "lock",
        "configuration_not_complete",
        # "finalize", finalize is not present waiting for advanced configuration
    ]

    # 7. Advanced
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
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.4,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "presets",
        "advanced",
        "lock",
        "finalize",  # Now finalize is present
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "finalize"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result.get("errors") is None
    assert result["data"] == MOCK_TH_OVER_CLIMATE_USER_CONFIG | MOCK_TH_OVER_CLIMATE_MAIN_CONFIG | MOCK_TH_OVER_CLIMATE_CENTRAL_MAIN_CONFIG | MOCK_TH_OVER_CLIMATE_TYPE_CONFIG | {
        CONF_SAFETY_DELAY_MIN: 5,
        CONF_SAFETY_MIN_ON_PERCENT: 0.4,
        CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
    } | MOCK_DEFAULT_FEATURE_CONFIG | {
        CONF_USE_MAIN_CENTRAL_CONFIG: False,
        CONF_USE_PRESETS_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_AUTO_START_STOP_FEATURE: False,
        CONF_USE_CENTRAL_BOILER_FEATURE: False,
        CONF_USE_TPI_CENTRAL_CONFIG: False,
        CONF_USE_WINDOW_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_CENTRAL_CONFIG: False,
        CONF_USE_POWER_CENTRAL_CONFIG: False,
        CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
        CONF_USE_ADVANCED_CENTRAL_CONFIG: False,
        CONF_USE_LOCK_CENTRAL_CONFIG: False,
        CONF_USED_BY_CENTRAL_BOILER: False,
        CONF_USE_CENTRAL_MODE: False,
        CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_STRONG,
        CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_NONE,
        CONF_SYNC_DEVICE_INTERNAL_TEMP: False,
    }
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 2
    assert result["result"].title == "TheOverClimateMockName"
    assert isinstance(result["result"], ConfigEntry)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# TODO Disable this test which only works alone
# @pytest.mark.skip
async def test_user_config_flow_over_climate_auto_start_stop(
    hass: HomeAssistant, skip_hass_states_get
):  # pylint: disable=unused-argument
    """Test the config flow with auto_start_stop thermostat_over_climate features."""
    # await create_central_config(hass)

    # 1. start a config flow in over_climate
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
        "features",
        "type",
        "presets",
        "advanced",
        "lock",
        "configuration_not_complete",
    ]
    assert result.get("errors") is None

    # 2. Add auto-start-stop feature
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
            CONF_USE_AUTO_START_STOP_FEATURE: True,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "presets",
        "auto_start_stop",
        "advanced",
        "lock",
        "configuration_not_complete",
        # "finalize", finalize is not present waiting for advanced configuration
    ]

    # 3. Configure auto-start-stop attributes
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "auto_start_stop"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "auto_start_stop"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_MEDIUM,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    # 4. Configure main attributes
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
            CONF_USE_CENTRAL_MODE: False,
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

    # 5. Configure type attributes
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "type"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "type"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
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
        "features",
        "type",
        "presets",
        "auto_start_stop",
        "advanced",
        "lock",
        "configuration_not_complete",
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

    # 6. configure advanced attributes
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
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.4,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "presets",
        "auto_start_stop",
        "advanced",
        "lock",
        "finalize",  # Now finalize is present
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "finalize"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result.get("errors") is None
    assert result["data"] == MOCK_TH_OVER_CLIMATE_USER_CONFIG | MOCK_TH_OVER_CLIMATE_MAIN_CONFIG | MOCK_TH_OVER_CLIMATE_CENTRAL_MAIN_CONFIG | MOCK_TH_OVER_CLIMATE_TYPE_CONFIG | {
        CONF_SAFETY_DELAY_MIN: 5,
        CONF_SAFETY_MIN_ON_PERCENT: 0.4,
        CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
    } | MOCK_DEFAULT_FEATURE_CONFIG | {
        CONF_USE_MAIN_CENTRAL_CONFIG: False,
        CONF_USE_TPI_CENTRAL_CONFIG: False,
        CONF_USE_PRESETS_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_AUTO_START_STOP_FEATURE: False,
        CONF_USE_CENTRAL_BOILER_FEATURE: False,
        CONF_USE_CENTRAL_MODE: False,
        CONF_USE_WINDOW_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_CENTRAL_CONFIG: False,
        CONF_USE_POWER_CENTRAL_CONFIG: False,
        CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
        CONF_USE_ADVANCED_CENTRAL_CONFIG: False,
        CONF_USE_LOCK_CENTRAL_CONFIG: False,
        CONF_USED_BY_CENTRAL_BOILER: False,
        CONF_USE_AUTO_START_STOP_FEATURE: True,
        CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_MEDIUM,
        CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_STRONG,
        CONF_SYNC_DEVICE_INTERNAL_TEMP: False,
    }
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 2
    assert result["result"].title == "TheOverClimateMockName"
    assert isinstance(result["result"], ConfigEntry)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# TODO Disable this test which only works alone
# @pytest.mark.skip
async def test_user_config_flow_over_switch_bug_552_tpi(
    hass: HomeAssistant, skip_hass_states_get
):  # pylint: disable=unused-argument
    """Test the bug 552 - a VTherm over_switch can be configured without TPI parameters
    if 'use central config is checked with no central config"""

    # 1. Thermostat over_switch
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

    # 2. Menu
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "presets",
        "advanced",
        "lock",
        "configuration_not_complete",
    ]
    assert result.get("errors") is None

    # 3. Main attributes
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
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
        },
    )

    # 4. Main attributes 2
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.5,
            # Keep default values which are False
        },
    )

    # 5. Menu
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "presets",
        "advanced",
        "lock",
        "configuration_not_complete",  # tpi and presets are not configured and there is no central configuration
    ]

    # 6. Type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "type"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "type"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_AC_MODE: False,
            CONF_INVERSE_SWITCH: False,
        },
    )

    # 7. Menu
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "tpi",
        "presets",
        "advanced",
        "lock",
        "configuration_not_complete",  # advanced, tpi and presets are not configured and there is no central configuration
    ]

    # 8. Advanced
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "advanced"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "advanced"
    assert result.get("errors") == {}

    # 8. Advanced 2
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USE_ADVANCED_CENTRAL_CONFIG: False},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "advanced"
    assert result.get("errors") == {}

    # 9. Advanced 3
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.4,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
        },
    )

    # 10. Menu
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "tpi",
        "presets",
        "advanced",
        "lock",
        "configuration_not_complete",  # tpi is not configured and there is no central configuration
    ]

    # 11. TPI
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tpi"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "tpi"
    assert result.get("errors") == {}

    # 11. TPI 2
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_TPI_CENTRAL_CONFIG: False}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "tpi"
    assert result.get("errors") == {}

    # 12. Menu
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TPI_CONFIG
    )

    # 11. Presets
    # We do not configure preset so we should have a default: don't use preset central config
    # result = await hass.config_entries.flow.async_configure(
    #     result["flow_id"], user_input={"next_step_id": "presets"}
    # )
    # assert result["type"] == FlowResultType.FORM
    # assert result["step_id"] == "presets"
    # assert result.get("errors") == {}
    #
    # result = await hass.config_entries.flow.async_configure(
    #     result["flow_id"], user_input={CONF_USE_PRESETS_CENTRAL_CONFIG: False}
    # )

    # 12. Menu
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "tpi",
        "presets",
        "advanced",
        "lock",
        "finalize",  # all is now configured
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "finalize"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result.get("errors") is None
    assert result["data"] == (
        MOCK_TH_OVER_SWITCH_USER_CONFIG
        | MOCK_TH_OVER_SWITCH_MAIN_CONFIG
        | MOCK_TH_OVER_SWITCH_TYPE_CONFIG
        | MOCK_TH_OVER_SWITCH_TPI_CONFIG
        | {
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.5,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.4,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_TPI_CENTRAL_CONFIG: False,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_WINDOW_CENTRAL_CONFIG: False,
            CONF_USE_MOTION_CENTRAL_CONFIG: False,
            CONF_USE_POWER_CENTRAL_CONFIG: False,
            CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: False,
            CONF_USE_LOCK_CENTRAL_CONFIG: False,
            CONF_USE_AUTO_START_STOP_FEATURE: False,
            CONF_USE_HEATING_FAILURE_DETECTION_FEATURE: False,
            CONF_USE_CENTRAL_MODE: False,
            CONF_USED_BY_CENTRAL_BOILER: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_CENTRAL_BOILER_FEATURE: False,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_NONE,
        }
    )
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 2
    assert result["result"].title == "TheOverSwitchMockName"
    assert isinstance(result["result"], ConfigEntry)


# @pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# TODO Disable this test which only works alone
# @pytest.mark.skip
async def test_user_config_flow_over_climate_valve(
    hass: HomeAssistant, skip_hass_states_get
):  # pylint: disable=unused-argument
    """Test the config flow with all thermostat_over_climate with the valve regulation activated.
    We don't use any features nor central config
    but we will add multiple underlying climate and valve"""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER

    # 1. Type
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
        "features",
        "type",
        "presets",
        "advanced",
        "lock",
        "configuration_not_complete",
    ]
    assert result.get("errors") is None

    # 2. Main
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
            CONF_USE_CENTRAL_MODE: False,
            # Keep default values which are False
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result.get("errors") == {}

    # 3. Main 2
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

    # 4. Type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "type"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "type"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_UNDERLYING_LIST: ["climate.mock_climate1", "climate.mock_climate2"],
            CONF_AC_MODE: False,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
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
        "features",
        "type",
        "tpi",
        "presets",
        "valve_regulation",
        "sync_device_internal_temp",
        "advanced",
        "lock",
        "configuration_not_complete",
        # "finalize",  # because we need Advanced default parameters
    ]
    assert result.get("errors") is None

    # 4.bis check that function doesn't contains auto_start_stop
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "features"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "features"
    assert result.get("errors") == {}

    assert result["data_schema"].schema.get("use_window_feature", None) is not None
    assert result["data_schema"].schema.get("use_motion_feature", None) is not None
    assert result["data_schema"].schema.get("use_power_feature", None) is not None
    assert result["data_schema"].schema.get("use_presence_feature", None) is not None
    assert result["data_schema"].schema.get("use_auto_start_stop_feature", None) is None

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={})
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"

    # 5. TPI
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "tpi"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "tpi"
    assert result.get("errors") == {}

    # 6. TPI 2
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_USE_TPI_CENTRAL_CONFIG: False}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "tpi"
    assert result.get("errors") == {}

    # 7. Menu
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TPI_CONFIG
    )

    # 8. Presets
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

    # 9. Features
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
            # CONF_USE_AUTO_START_STOP_FEATURE: False,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "tpi",
        "presets",
        "valve_regulation",
        "sync_device_internal_temp",
        "advanced",
        "lock",
        "configuration_not_complete",
        # "finalize", finalize is not present waiting for advanced configuration
    ]

    # 10. Valve_regulation
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "valve_regulation"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valve_regulation"
    assert result.get("errors") == {}

    # 10.1 Only one but 2 expected
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            # CONF_OFFSET_CALIBRATION_LIST: ["number.offset_calibration1"],
            CONF_OPENING_DEGREE_LIST: ["number.opening_degree1"],
            CONF_CLOSING_DEGREE_LIST: ["number.closing_degree1"],
            CONF_MIN_OPENING_DEGREES: "10, 20,0",
            CONF_MAX_CLOSING_DEGREE: "30",
            CONF_MAX_OPENING_DEGREES: "90",
            CONF_OPENING_THRESHOLD_DEGREE: "5",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valve_regulation"
    assert result.get("errors") == {"base": "valve_regulation_nb_entities_incorrect"}

    # 10.2 Give two openings but only one offset_calibration
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            # CONF_OFFSET_CALIBRATION_LIST: [
            #     "number.offset_calibration1",
            #     "number.offset_calibration2",
            # ],
            CONF_OPENING_DEGREE_LIST: [
                "number.opening_degree1",
                "number.opening_degree2",
            ],
            CONF_CLOSING_DEGREE_LIST: ["number.closing_degree1"],
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valve_regulation"
    assert result.get("errors") == {"base": "valve_regulation_nb_entities_incorrect"}

    # 10.3 Give two openings and 2 calibration and 0 closing
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            # CONF_OFFSET_CALIBRATION_LIST: [
            #     "number.offset_calibration1",
            #     "number.offset_calibration2",
            # ],
            CONF_OPENING_DEGREE_LIST: [
                "number.opening_degree1",
                "number.opening_degree2",
            ],
            CONF_CLOSING_DEGREE_LIST: [],
            CONF_MIN_OPENING_DEGREES: "10, 20,0",
            CONF_MAX_CLOSING_DEGREE: "30",
            CONF_MAX_OPENING_DEGREES: "90",
            CONF_OPENING_THRESHOLD_DEGREE: "5",
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "tpi",
        "presets",
        "valve_regulation",
        "sync_device_internal_temp",
        "advanced",
        "lock",
        "configuration_not_complete",
        # "finalize", finalize is not present waiting for advanced configuration
    ]

    # 11. Advanced
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
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.4,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "tpi",
        "presets",
        "valve_regulation",
        "sync_device_internal_temp",
        "advanced",
        "lock",
        "configuration_not_complete",
        # "finalize",  finalize is not present awaiting for sync_device_internal_temp configuration
    ]

    # 12. Synchronize device internal temp
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "sync_device_internal_temp"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sync_device_internal_temp"
    assert result.get("errors") == {}

    # 12.1 Only one but 2 expected
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYNC_WITH_CALIBRATION: True,
            CONF_SYNC_ENTITY_LIST: ["number.offset_calibration1"],
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sync_device_internal_temp"
    assert result.get("errors") == {"base": "sync_device_internal_temp_nb_entities_incorrect"}

    # 12.2 Give one sync entity and change the SYNC_WITH_CALIBRATION to False
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYNC_WITH_CALIBRATION: False,
            CONF_SYNC_ENTITY_LIST: [
                "number.offset_calibration1",
            ],
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sync_device_internal_temp"
    assert result.get("errors") == {"base": "sync_device_internal_temp_nb_entities_incorrect"}

    # 12.3 Give two openings and 2 calibration and 0 closing
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYNC_WITH_CALIBRATION: True,
            CONF_SYNC_ENTITY_LIST: [
                "number.offset_calibration1",
                "number.offset_calibration2",
            ],
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "tpi",
        "presets",
        "valve_regulation",
        "sync_device_internal_temp",
        "advanced",
        "lock",
        "finalize",  # This time finalize is present
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "finalize"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result.get("errors") is None
    assert result["data"] == MOCK_TH_OVER_CLIMATE_USER_CONFIG | MOCK_TH_OVER_CLIMATE_MAIN_CONFIG | MOCK_TH_OVER_CLIMATE_CENTRAL_MAIN_CONFIG | MOCK_TH_OVER_CLIMATE_TYPE_CONFIG | {
        CONF_MINIMAL_ACTIVATION_DELAY: 10,
        CONF_MINIMAL_DEACTIVATION_DELAY: 0,
        CONF_TPI_THRESHOLD_LOW: 0.0,
        CONF_TPI_THRESHOLD_HIGH: 0.0,
        CONF_AUTO_TPI_MODE: False,
        CONF_SAFETY_DELAY_MIN: 5,
        CONF_SAFETY_MIN_ON_PERCENT: 0.4,
        CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
    } | MOCK_DEFAULT_FEATURE_CONFIG | {
        CONF_USE_MAIN_CENTRAL_CONFIG: False,
        CONF_USE_PRESETS_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_AUTO_START_STOP_FEATURE: False,
        CONF_USE_CENTRAL_BOILER_FEATURE: False,
        CONF_USE_TPI_CENTRAL_CONFIG: False,
        CONF_USE_WINDOW_CENTRAL_CONFIG: False,
        CONF_USE_MOTION_CENTRAL_CONFIG: False,
        CONF_USE_POWER_CENTRAL_CONFIG: False,
        CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
        CONF_USE_ADVANCED_CENTRAL_CONFIG: False,
        CONF_USE_LOCK_CENTRAL_CONFIG: False,
        CONF_USED_BY_CENTRAL_BOILER: False,
        CONF_USE_CENTRAL_MODE: False,
        CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
        CONF_UNDERLYING_LIST: ["climate.mock_climate1", "climate.mock_climate2"],
        CONF_OPENING_DEGREE_LIST: ["number.opening_degree1", "number.opening_degree2"],
        CONF_CLOSING_DEGREE_LIST: [],
        CONF_SYNC_ENTITY_LIST: [
            "number.offset_calibration1",
            "number.offset_calibration2",
        ],
        CONF_SYNC_WITH_CALIBRATION: True,
        CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.1,
        CONF_MIN_OPENING_DEGREES: "10, 20,0",
        CONF_MAX_CLOSING_DEGREE: 30,
        CONF_MAX_OPENING_DEGREES: "90",
        CONF_OPENING_THRESHOLD_DEGREE: 5,
        CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_NONE,
    }
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 2
    assert result["result"].title == "TheOverClimateMockName"
    assert isinstance(result["result"], ConfigEntry)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_user_config_flow_valve_min_max_opening_degrees_error(hass: HomeAssistant, skip_hass_states_get):  # pylint: disable=unused-argument
    """Test the config flow with valve regulation to ensure max_opening_degrees > min_opening_degrees validation"""

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER

    # 1. Type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"

    # 2. Main
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "main"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "TheOverClimateMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"

    # 3. Main 2
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"

    # 4. Type
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "type"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "type"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_UNDERLYING_LIST: ["climate.mock_climate1", "climate.mock_climate2"],
            CONF_AC_MODE: False,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"

    # 5. Features
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "features"})
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

    # 6. TPI
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "tpi"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_USE_TPI_CENTRAL_CONFIG: False})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=MOCK_TH_OVER_SWITCH_TPI_CONFIG)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"

    # 7. Presets
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "presets"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_USE_PRESETS_CENTRAL_CONFIG: False})
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"

    # 8. Valve_regulation - Test case where max_opening_degrees <= min_opening_degrees for first underlying
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "valve_regulation"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valve_regulation"

    # 8.1 Test with max <= min for the first underlying (50 <= 60)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_LIST: [
                "number.opening_degree1",
                "number.opening_degree2",
            ],
            CONF_CLOSING_DEGREE_LIST: [],
            CONF_MIN_OPENING_DEGREES: "60, 20",
            CONF_MAX_OPENING_DEGREES: "50, 85",  # 50 <= 60 -> error
            CONF_MAX_CLOSING_DEGREE: 30,
            CONF_OPENING_THRESHOLD_DEGREE: 5,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valve_regulation"
    assert result.get("errors") == {CONF_MAX_OPENING_DEGREES: "min_max_opening_degrees_inconsistent"}

    # 8.2 Test with max == min for the second underlying (70 == 70)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_LIST: [
                "number.opening_degree1",
                "number.opening_degree2",
            ],
            CONF_CLOSING_DEGREE_LIST: [],
            CONF_MIN_OPENING_DEGREES: "10, 70",
            CONF_MAX_OPENING_DEGREES: "80, 70",  # 70 == 70 -> error
            CONF_MAX_CLOSING_DEGREE: 30,
            CONF_OPENING_THRESHOLD_DEGREE: 5,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valve_regulation"
    assert result.get("errors") == {CONF_MAX_OPENING_DEGREES: "min_max_opening_degrees_inconsistent"}

    # 8.3 Test with valid configuration (max > min for all underlyings)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_LIST: [
                "number.opening_degree1",
                "number.opening_degree2",
            ],
            CONF_CLOSING_DEGREE_LIST: [],
            CONF_MIN_OPENING_DEGREES: "10, 20",
            CONF_MAX_OPENING_DEGREES: "80, 85",  # All valid: 80 > 10 and 85 > 20
            CONF_MAX_CLOSING_DEGREE: 30,
            CONF_OPENING_THRESHOLD_DEGREE: 5,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result.get("errors") is None
