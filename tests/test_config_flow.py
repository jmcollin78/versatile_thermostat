# pylint: disable=unused-argument, line-too-long, too-many-lines
""" Test the Versatile Thermostat config flow """

import json
from pathlib import Path
from typing import Any, cast

from homeassistant.data_entry_flow import FlowResultType
from unittest.mock import patch

from homeassistant.core import HomeAssistant, State, StateMachine
from homeassistant.config_entries import SOURCE_USER, ConfigEntry

from custom_components.versatile_thermostat.const import DOMAIN
from custom_components.versatile_thermostat.config_flow import VersatileThermostatConfigFlow

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def _fill_underlyings(hass: HomeAssistant, flow_id: str, common_input: dict | None, devices: list, extra_input: dict | None = None):
    """From the menu: open the underlyings, fill the common settings, add the devices (list of (entity_id, device input)) and come back to the menu"""
    result = await hass.config_entries.flow.async_configure(flow_id, user_input={"next_step_id": "type"})
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"

    if common_input is not None:
        result = await hass.config_entries.flow.async_configure(flow_id, user_input={"next_step_id": "underlying_common"})
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "underlying_common"
        result = await hass.config_entries.flow.async_configure(flow_id, user_input=common_input)
        if extra_input is not None:
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "underlying_common_extra"
            result = await hass.config_entries.flow.async_configure(flow_id, user_input=extra_input)
        assert result["type"] == FlowResultType.MENU
        assert result["step_id"] == "type"

    for entity_id, device_input in devices:
        result = await hass.config_entries.flow.async_configure(flow_id, user_input={"next_step_id": "underlying_add"})
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "underlying_add"
        result = await hass.config_entries.flow.async_configure(flow_id, user_input={CONF_UNDERLYING_ENTITY: entity_id})
        if device_input is not None:
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "underlying"
            result = await hass.config_entries.flow.async_configure(flow_id, user_input=device_input)
        assert result["type"] == FlowResultType.MENU
        assert result["step_id"] == "type"

    return await hass.config_entries.flow.async_configure(flow_id, user_input={"next_step_id": "menu"})


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_show_form(hass: HomeAssistant, init_vtherm_api) -> None:
    """Test that the form is served with no input"""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER


@pytest.mark.parametrize(
    "power_unit",
    [POWER_UNIT_WATT, POWER_UNIT_KILO_WATT],
)
async def test_config_flow_main_power_unit_options_and_acceptance(
    hass: HomeAssistant,
    init_vtherm_api,
    skip_hass_states_get,
    power_unit,
) -> None:
    """The main form exposes and accepts each VTherm power unit option."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "main"},
    )

    form_result = cast(dict[str, Any], result)
    assert form_result["type"] == FlowResultType.FORM
    assert form_result["data_schema"].schema[CONF_POWER_UNIT].config["options"] == CONF_POWER_UNITS
    assert (
        form_result["data_schema"](
            {
                CONF_NAME: "Power unit test",
                CONF_TEMP_SENSOR: "sensor.temperature",
                CONF_CYCLE_MIN: 5,
            }
        )[CONF_POWER_UNIT]
        == POWER_UNIT_WATT
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Power unit test",
            CONF_TEMP_SENSOR: "sensor.temperature",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 2.0,
            CONF_POWER_UNIT: power_unit,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
        },
    )
    assert result.get("type") == FlowResultType.FORM

    hass.config_entries.flow.async_abort(result["flow_id"])


@pytest.mark.parametrize(
    "power_unit",
    CONF_CENTRAL_POWER_UNITS,
)
async def test_config_flow_central_power_unit_options_and_acceptance(
    hass: HomeAssistant,
    init_vtherm_api,
    skip_hass_states_get,
    power_unit,
) -> None:
    """The central power form exposes and accepts W, kW, and Auto."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "features"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USE_POWER_FEATURE: True},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "power"},
    )

    form_result = cast(dict[str, Any], result)
    assert form_result["type"] == FlowResultType.FORM
    assert form_result["data_schema"].schema[CONF_POWER_UNIT].config["options"] == CONF_CENTRAL_POWER_UNITS
    assert (
        form_result["data_schema"](
            {
                CONF_POWER_SENSOR: "sensor.power",
                CONF_MAX_POWER_SENSOR: "sensor.max_power",
            }
        )[CONF_POWER_UNIT]
        == POWER_UNIT_AUTO
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_POWER_SENSOR: "sensor.power",
            CONF_MAX_POWER_SENSOR: "sensor.max_power",
            CONF_POWER_UNIT: power_unit,
            CONF_PRESET_POWER: 13,
        },
    )
    assert result.get("type") == FlowResultType.MENU

    hass.config_entries.flow.async_abort(result["flow_id"])


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
        "humidity",
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
    result = await _fill_underlyings(
        hass,
        result["flow_id"],
        {
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_STRONG,
            CONF_AUTO_REGULATION_DTEMP: 10,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
        },
        [("climate.mock_climate", None)],
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
        "humidity",
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
        "humidity",
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
            CONF_MANUAL_OVERRIDE_DURATION_MIN: 30,
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
        "humidity",
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
        CONF_REPAIR_INCORRECT_STATE: False,
        CONF_MANUAL_OVERRIDE_DURATION_MIN: 30,
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
        CONF_AUTO_REGULATION_DTEMP: 10,
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
        "humidity",
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
        "humidity",
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
    result = await _fill_underlyings(
        hass,
        result["flow_id"],
        {
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_STRONG,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
        },
        [("climate.mock_climate", None)],
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
        "humidity",
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
        "humidity",
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
        CONF_REPAIR_INCORRECT_STATE: False,
        CONF_MANUAL_OVERRIDE_DURATION_MIN: 0,
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
        "humidity",
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
        "humidity",
        "configuration_not_complete",  # tpi and presets are not configured and there is no central configuration
    ]

    # 6. Type
    result = await _fill_underlyings(
        hass,
        result["flow_id"],
        {
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_AC_MODE: False,
            CONF_INVERSE_SWITCH: False,
        },
        [("switch.mock_switch", {})],
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
        "humidity",
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
        "humidity",
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
        "humidity",
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
            CONF_REPAIR_INCORRECT_STATE: False,
            CONF_MANUAL_OVERRIDE_DURATION_MIN: 0,
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
        "humidity",
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

    # 4. Type: the common settings and the two devices
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "type"})
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"
    assert result["menu_options"] == ["underlying_common", "underlying_add", "menu"]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "underlying_common"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "underlying_common"
    assert result.get("errors") == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_AC_MODE: False,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
        },
    )
    # The valve regulation and the synchronization have their common settings
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "underlying_common_extra"
    assert set(result["data_schema"].schema.keys()) == {CONF_PROP_FUNCTION, CONF_OPENING_THRESHOLD_DEGREE, CONF_MAX_CLOSING_DEGREE, CONF_SYNC_WITH_CALIBRATION}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_MAX_CLOSING_DEGREE: 30,
            CONF_OPENING_THRESHOLD_DEGREE: 5,
            CONF_SYNC_WITH_CALIBRATION: True,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"

    # 4.1 the first device: the opening entity is mandatory
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "underlying_add"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_UNDERLYING_ENTITY: "climate.mock_climate1"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "underlying"
    assert set(result["data_schema"].schema.keys()) == {
        CONF_OPENING_DEGREE_ENTITY,
        CONF_CLOSING_DEGREE_ENTITY,
        CONF_MIN_OPENING_DEGREE,
        CONF_MAX_OPENING_DEGREE,
        CONF_SYNC_ENTITY,
    }
    # an unknown entity is refused
    with patch.object(StateMachine, "get", return_value=None):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_OPENING_DEGREE_ENTITY: "number.unknown", CONF_SYNC_ENTITY: "number.offset_calibration1"}
        )
    assert result["step_id"] == "underlying"
    assert result.get("errors") == {CONF_OPENING_DEGREE_ENTITY: "unknown_entity", CONF_SYNC_ENTITY: "unknown_entity"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening_degree1",
            CONF_MIN_OPENING_DEGREE: 10,
            CONF_MAX_OPENING_DEGREE: 90,
            CONF_SYNC_ENTITY: "number.offset_calibration1",
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"
    # the second device is missing: the first one is complete, only the second one is added
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "underlying_add"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_UNDERLYING_ENTITY: "climate.mock_climate2"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening_degree2",
            CONF_MIN_OPENING_DEGREE: 20,
            CONF_MAX_OPENING_DEGREE: 100,
            CONF_SYNC_ENTITY: "number.offset_calibration2",
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"
    assert result["menu_options"] == ["underlying_common", "underlying_1", "underlying_2", "underlying_add", "menu"]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "menu"})
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"] == [
        "main",
        "features",
        "type",
        "tpi",
        "presets",
        "advanced",
        "lock",
        "humidity",
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
        "advanced",
        "lock",
        "humidity",
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
        "advanced",
        "lock",
        "humidity",
        "finalize",  # Now finalize is present
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
        CONF_REPAIR_INCORRECT_STATE: False,
        CONF_MANUAL_OVERRIDE_DURATION_MIN: 0,
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
        CONF_MIN_OPENING_DEGREES: "10, 20",
        CONF_MAX_CLOSING_DEGREE: 30,
        CONF_MAX_OPENING_DEGREES: "90, 100",
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

    # 4. Type: common settings with valve regulation
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "type"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "underlying_common"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "underlying_common"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "underlying_common_extra"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI, CONF_MAX_CLOSING_DEGREE: 30, CONF_OPENING_THRESHOLD_DEGREE: 5},
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"

    # 4.1 Test with max <= min for the first underlying (50 <= 60)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "underlying_add"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_UNDERLYING_ENTITY: "climate.mock_climate1"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "underlying"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening_degree1",
            CONF_MIN_OPENING_DEGREE: 60,
            CONF_MAX_OPENING_DEGREE: 50,  # 50 <= 60 -> error
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "underlying"
    assert result.get("errors") == {CONF_MAX_OPENING_DEGREE: "min_max_opening_degrees_inconsistent"}

    # 4.2 Test with max == min (70 == 70)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening_degree1",
            CONF_MIN_OPENING_DEGREE: 70,
            CONF_MAX_OPENING_DEGREE: 70,  # 70 == 70 -> error
        },
    )
    assert result["step_id"] == "underlying"
    assert result.get("errors") == {CONF_MAX_OPENING_DEGREE: "min_max_opening_degrees_inconsistent"}

    # 4.3 Test with a max above the max of the valve (50), which is known only when the opening entity is given
    with patch.object(StateMachine, "get", return_value=State("number.opening_degree1", "0", attributes={"max": 50, "min": 0})):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_OPENING_DEGREE_ENTITY: "number.opening_degree1",
                CONF_MIN_OPENING_DEGREE: 10,
                CONF_MAX_OPENING_DEGREE: 80,
            },
        )
    assert result["step_id"] == "underlying"
    assert result.get("errors") == {CONF_MAX_OPENING_DEGREE: "max_opening_degree_out_of_range"}

    # 4.4 Test with a valid configuration (max > min)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening_degree1",
            CONF_MIN_OPENING_DEGREE: 10,
            CONF_MAX_OPENING_DEGREE: 80,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"

    # The second device
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "underlying_add"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_UNDERLYING_ENTITY: "climate.mock_climate2"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening_degree2",
            CONF_MIN_OPENING_DEGREE: 20,
            CONF_MAX_OPENING_DEGREE: 85,
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "menu"})
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

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_central_config_hidden_when_exists(hass: HomeAssistant, init_vtherm_api):
    """When a central configuration already exists, it should not appear as an option
    in the first step of the ConfigFlow. When it is deleted, it should reappear."""

    # 1. First flow: central config option should be available (no central config yet)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER

    schema_keys = [str(k) for k in result["data_schema"].schema.keys()]
    assert CONF_THERMOSTAT_TYPE in schema_keys

    # Retrieve options for thermostat_type
    type_selector = result["data_schema"].schema[CONF_THERMOSTAT_TYPE]
    available_options = [opt for opt in type_selector.config["options"]]
    assert CONF_THERMOSTAT_CENTRAL_CONFIG in available_options

    # Cancel this flow
    hass.config_entries.flow.async_abort(result["flow_id"])

    # 2. Create a central configuration
    central_config_entry = await create_central_config(hass, FULL_CENTRAL_CONFIG)
    assert central_config_entry is not None

    # 3. New flow: central config option should now be hidden
    result2 = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == SOURCE_USER

    type_selector2 = result2["data_schema"].schema[CONF_THERMOSTAT_TYPE]
    available_options2 = [opt for opt in type_selector2.config["options"]]
    assert CONF_THERMOSTAT_CENTRAL_CONFIG not in available_options2

    hass.config_entries.flow.async_abort(result2["flow_id"])

    # 4. Delete the central configuration
    api = VersatileThermostatAPI.get_vtherm_api(hass)
    central_entry = None
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG:
            central_entry = entry
            break
    assert central_entry is not None
    await hass.config_entries.async_remove(central_entry.entry_id)

    # Cache must have been reset
    assert api.find_central_configuration() is None

    # 5. New flow: central config option should be available again
    result3 = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == SOURCE_USER

    type_selector3 = result3["data_schema"].schema[CONF_THERMOSTAT_TYPE]
    available_options3 = [opt for opt in type_selector3.config["options"]]
    assert CONF_THERMOSTAT_CENTRAL_CONFIG in available_options3

    hass.config_entries.flow.async_abort(result3["flow_id"])


async def test_config_flow_central_boiler_template_validation(hass: HomeAssistant, init_vtherm_api):
    """A template in the central boiler command value is validated by the config flow"""
    from custom_components.versatile_thermostat.config_flow import VersatileThermostatConfigFlow

    flow = VersatileThermostatConfigFlow()
    flow.hass = hass
    flow._infos[CONF_USE_CENTRAL_BOILER_FEATURE] = True

    valid = "climate.x/climate.set_temperature/temperature:{{ state_attr('climate.x', 'current_temperature') | float(20) / 2 + 1 }}"
    await flow.validate_input(
        {
            CONF_CENTRAL_BOILER_ACTIVATION_SRV: valid,
            CONF_CENTRAL_BOILER_DEACTIVATION_SRV: "switch.boiler/switch.turn_off",
        },
        "central_boiler",
    )

    with pytest.raises(ServiceConfigurationError) as err:
        await flow.validate_input(
            {
                CONF_CENTRAL_BOILER_ACTIVATION_SRV: "climate.x/climate.set_temperature/temperature:{{ 1 + }}",
                CONF_CENTRAL_BOILER_DEACTIVATION_SRV: "switch.boiler/switch.turn_off",
            },
            "central_boiler",
        )
    assert str(err.value) == CONF_CENTRAL_BOILER_ACTIVATION_SRV

    with pytest.raises(ServiceConfigurationError) as err:
        await flow.validate_input(
            {
                CONF_CENTRAL_BOILER_ACTIVATION_SRV: "switch.boiler/switch.turn_on",
                CONF_CENTRAL_BOILER_DEACTIVATION_SRV: "climate.x/climate.set_temperature/temperature:{{ (1 }}",
            },
            "central_boiler",
        )
    assert str(err.value) == CONF_CENTRAL_BOILER_DEACTIVATION_SRV

    with pytest.raises(ServiceConfigurationError) as err:
        await flow.validate_input(
            {
                CONF_CENTRAL_BOILER_ACTIVATION_SRV: "climate.x/climate.set_temperature/temperature:{% if true %}18",
                CONF_CENTRAL_BOILER_DEACTIVATION_SRV: "switch.boiler/switch.turn_off",
            },
            "central_boiler",
        )
    assert str(err.value) == CONF_CENTRAL_BOILER_ACTIVATION_SRV


def _complete_switch_infos() -> dict:
    """A complete over_switch configuration (no central configuration)"""
    return {
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_NAME: "TheOverSwitchMockName",
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_UNDERLYING_LIST: ["switch.mock_switch"],
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_USE_MAIN_CENTRAL_CONFIG: False,
        CONF_USE_TPI_CENTRAL_CONFIG: False,
        CONF_USE_ADVANCED_CENTRAL_CONFIG: False,
        CONF_USE_PRESETS_CENTRAL_CONFIG: False,
        CONF_USE_POWER_CENTRAL_CONFIG: False,
        CONF_USE_PRESENCE_CENTRAL_CONFIG: False,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.1,
        CONF_SAFETY_DELAY_MIN: 5,
        CONF_SAFETY_MIN_ON_PERCENT: 0.4,
        CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
    }


def _complete_climate_valve_infos() -> dict:
    """A complete over_climate configuration with valve regulation and 2 underlyings"""
    return _complete_switch_infos() | {
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
        CONF_UNDERLYING_LIST: ["climate.mock_climate1", "climate.mock_climate2"],
        CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
        CONF_OPENING_DEGREE_LIST: ["number.opening1", "number.opening2"],
        CONF_CLOSING_DEGREE_LIST: [],
    }


def _complete_central_infos() -> dict:
    """A complete central configuration"""
    return {
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG,
        CONF_NAME: CENTRAL_CONFIG_NAME,
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
    }


@pytest.mark.parametrize(
    "infos, mutation, expected",
    [
        # Rules of a VTherm which is not a central configuration
        (_complete_switch_infos(), {CONF_NAME: None}, [("main", [CONF_NAME])]),
        (_complete_switch_infos(), {CONF_TEMP_SENSOR: None}, [("main", [CONF_TEMP_SENSOR])]),
        (_complete_switch_infos(), {CONF_CYCLE_MIN: None}, [("main", [CONF_CYCLE_MIN])]),
        (_complete_switch_infos(), {CONF_EXTERNAL_TEMP_SENSOR: None}, [("main", [CONF_EXTERNAL_TEMP_SENSOR])]),
        (_complete_switch_infos(), {CONF_UNDERLYING_LIST: []}, [("type", [CONF_UNDERLYING_ENTITY])]),
        (_complete_switch_infos(), {CONF_USE_MOTION_FEATURE: True}, [("motion", [CONF_MOTION_SENSOR])]),
        (_complete_switch_infos(), {CONF_USE_POWER_FEATURE: True}, [("power", [CONF_PRESET_POWER])]),
        (_complete_switch_infos(), {CONF_USE_PRESENCE_FEATURE: True}, [("presence", [CONF_PRESENCE_SENSOR])]),
        (
            _complete_switch_infos(),
            {CONF_SAFETY_DELAY_MIN: None, CONF_SAFETY_MIN_ON_PERCENT: None, CONF_SAFETY_DEFAULT_ON_PERCENT: None},
            [("advanced", [CONF_SAFETY_DELAY_MIN, CONF_SAFETY_MIN_ON_PERCENT, CONF_SAFETY_DEFAULT_ON_PERCENT])],
        ),
        (_complete_switch_infos(), {CONF_TPI_COEF_INT: None}, [("tpi", [CONF_TPI_COEF_INT])]),
        (_complete_switch_infos(), {CONF_TPI_COEF_EXT: None}, [("tpi", [CONF_TPI_COEF_EXT])]),
        # presets central config selected but no central configuration exists
        (_complete_switch_infos(), {CONF_USE_PRESETS_CENTRAL_CONFIG: True}, [("presets", [CONF_USE_PRESETS_CENTRAL_CONFIG])]),
        # valve regulation: the second device has no opening entity
        (_complete_climate_valve_infos(), {CONF_OPENING_DEGREE_LIST: ["number.opening1"]}, [("type", [CONF_OPENING_DEGREE_ENTITY])]),
        (_complete_climate_valve_infos(), {CONF_OPENING_DEGREE_LIST: ["number.opening1", ""]}, [("type", [CONF_OPENING_DEGREE_ENTITY])]),
        # valve regulation: closing entities are given for all the devices or for none
        (_complete_climate_valve_infos(), {CONF_CLOSING_DEGREE_LIST: ["number.closing1"]}, [("type", [CONF_CLOSING_DEGREE_ENTITY])]),
        (_complete_climate_valve_infos(), {CONF_CLOSING_DEGREE_LIST: ["number.closing1", "number.closing2"]}, []),
        # valve regulation is not selected: the lists are not checked
        (_complete_climate_valve_infos(), {CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_NONE, CONF_OPENING_DEGREE_LIST: []}, []),
        # synchronize internal temperature: the second device has no synchronization entity
        (
            _complete_climate_valve_infos(),
            {CONF_SYNC_DEVICE_INTERNAL_TEMP: True, CONF_SYNC_ENTITY_LIST: ["number.sync1"]},
            [("type", [CONF_SYNC_ENTITY])],
        ),
        # custom commands: mandatory for an entity which is not a switch
        (_complete_switch_infos(), {CONF_UNDERLYING_LIST: ["select.mock_select"]}, [("type", [CONF_VSWITCH_ON_CMD, CONF_VSWITCH_OFF_CMD])]),
        (
            _complete_switch_infos(),
            {CONF_UNDERLYING_LIST: ["select.mock_select"], CONF_VSWITCH_ON_CMD_LIST: ["select_option/option:on"], CONF_VSWITCH_OFF_CMD_LIST: ["select_option/option:off"]},
            [],
        ),
        # custom commands: given for all the devices or for none
        (
            _complete_switch_infos(),
            {CONF_UNDERLYING_LIST: ["switch.mock_switch1", "switch.mock_switch2"], CONF_VSWITCH_ON_CMD_LIST: ["turn_on", ""]},
            [("type", [CONF_VSWITCH_ON_CMD])],
        ),
        (_complete_switch_infos(), {CONF_UNDERLYING_LIST: ["switch.mock_switch1", "switch.mock_switch2"]}, []),
        # Rules of a central configuration
        (_complete_central_infos(), {CONF_NAME: None}, [("main", [CONF_NAME])]),
        (_complete_central_infos(), {CONF_EXTERNAL_TEMP_SENSOR: None}, [("main", [CONF_EXTERNAL_TEMP_SENSOR])]),
        (_complete_central_infos(), {CONF_USE_POWER_FEATURE: True}, [("power", [CONF_POWER_SENSOR, CONF_MAX_POWER_SENSOR])]),
        (_complete_central_infos(), {CONF_USE_PRESENCE_FEATURE: True}, [("presence", [CONF_PRESENCE_SENSOR])]),
        (
            _complete_central_infos(),
            {CONF_USE_CENTRAL_BOILER_FEATURE: True},
            [("central_boiler", [CONF_CENTRAL_BOILER_ACTIVATION_SRV, CONF_CENTRAL_BOILER_DEACTIVATION_SRV])],
        ),
        (
            _complete_central_infos(),
            {CONF_USE_CENTRAL_BOILER_FEATURE: True, CONF_CENTRAL_BOILER_ACTIVATION_SRV: "switch.boiler/switch.turn_on", CONF_CENTRAL_BOILER_DEACTIVATION_SRV: ""},
            [("central_boiler", [CONF_CENTRAL_BOILER_DEACTIVATION_SRV])],
        ),
    ],
)
async def test_get_missing_config(hass: HomeAssistant, init_vtherm_api, infos, mutation, expected) -> None:
    """Each rule of get_missing_config gives the step to open and the fields involved (no item if the mutation is still valid)"""
    flow = VersatileThermostatConfigFlow()
    flow.hass = hass

    # The initial configuration is complete
    assert flow.get_missing_config(infos) == []
    assert flow.check_config_complete(infos) is True

    infos = {**infos, **mutation}
    missing = flow.get_missing_config(infos)
    assert [(item.step_id, item.fields) for item in missing] == expected
    assert flow.check_config_complete(infos) is (not expected)


async def test_get_missing_config_several_items(hass: HomeAssistant, init_vtherm_api) -> None:
    """All the missing items are reported, one per step"""
    flow = VersatileThermostatConfigFlow()
    flow.hass = hass

    infos = _complete_switch_infos() | {CONF_NAME: None, CONF_UNDERLYING_LIST: [], CONF_USE_MOTION_FEATURE: True}
    missing = flow.get_missing_config(infos)
    assert [item.step_id for item in missing] == ["main", "type", "motion"]


async def test_configuration_not_complete_menu(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """The 'configuration not complete' menu lists the missing items and opens the steps to fix them"""
    flow = VersatileThermostatConfigFlow()
    flow.hass = hass
    flow._infos.update(_complete_switch_infos() | {CONF_USE_MOTION_FEATURE: True, CONF_NAME: None})

    # The main menu shows the summary and the 'configuration_not_complete' option
    result = await flow.async_step_menu()
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"][-1] == "configuration_not_complete"
    assert "finalize" not in result["menu_options"]
    assert result["description_placeholders"]["missing_count"] == "2"
    assert "2" in result["description_placeholders"]["missing_summary"]

    # The detail menu lists the steps to fix, and a way back
    result = await flow.async_step_configuration_not_complete()
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "configuration_not_complete"
    assert result["menu_options"] == ["main", "motion", "menu"]
    items = result["description_placeholders"]["missing_items"]
    assert len(items.splitlines()) == 2
    assert items.splitlines()[0].startswith("- **")

    # Once everything is fixed, the user is sent back to the main menu with 'finalize'
    flow._infos.update({CONF_NAME: "TheOverSwitchMockName", CONF_MOTION_SENSOR: "binary_sensor.motion"})
    result = await flow.async_step_configuration_not_complete()
    assert result["step_id"] == "menu"
    assert result["menu_options"][-1] == "finalize"
    assert result["description_placeholders"]["missing_count"] == "0"
    assert result["description_placeholders"]["missing_summary"] == ""


async def test_configuration_not_complete_flow(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """From a real flow, the 'configuration not complete' menu opens the step to fix"""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH})
    assert result["type"] == FlowResultType.MENU
    assert result["menu_options"][-1] == "configuration_not_complete"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "configuration_not_complete"})
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "configuration_not_complete"
    assert "main" in result["menu_options"]
    assert "type" in result["menu_options"]
    assert result["menu_options"][-1] == "menu"

    # Back to the menu
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "menu"})
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"

    # Open the step to fix
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "configuration_not_complete"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "main"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"

    hass.config_entries.flow.async_abort(result["flow_id"])


async def _open_options(hass: HomeAssistant, data: dict):
    """Open the options flow of a configuration entry made of data. Returns the first result (the menu)"""
    entry = MockConfigEntry(domain=DOMAIN, title=data[CONF_NAME], unique_id=data[CONF_NAME], data=data, version=2)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return entry, result


def _climate_valve_data() -> dict:
    """The data of an existing over_climate VTherm with valve regulation, 2 devices and the synchronization of the internal temperature"""
    return _complete_climate_valve_infos() | {
        CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
        CONF_SYNC_WITH_CALIBRATION: True,
        CONF_SYNC_ENTITY_LIST: ["number.calibration1", "number.calibration2"],
        CONF_MIN_OPENING_DEGREES: "10, 20",
        CONF_MAX_OPENING_DEGREES: "80, 90",
        CONF_OPENING_THRESHOLD_DEGREE: 5,
    }


async def test_options_flow_opens_the_menu_and_lists_existing_underlyings(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """The options flow opens the menu directly and an existing configuration is correctly displayed in the underlyings list"""
    _, result = await _open_options(hass, _climate_valve_data())
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "menu"
    assert "finalize" in result["menu_options"]
    assert "valve_regulation" not in result["menu_options"]
    assert "sync_device_internal_temp" not in result["menu_options"]

    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"next_step_id": "type"})
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "type"
    assert result["menu_options"] == ["underlying_common", "underlying_1", "underlying_2", "underlying_add", "menu"]
    placeholders = result["description_placeholders"]
    assert placeholders["underlying_1"] == "climate.mock_climate1"
    assert placeholders["underlying_2"] == "climate.mock_climate2"
    # the details give the entities of the device and its settings
    assert "number.opening1" in placeholders["underlying_1_details"]
    assert "number.calibration1" in placeholders["underlying_1_details"]
    assert "10" in placeholders["underlying_1_details"]
    assert "80" in placeholders["underlying_1_details"]
    assert "90" in placeholders["underlying_2_details"]
    assert not placeholders["underlying_1_details"].startswith("⚠")
    assert placeholders["underlying_common_details"] != ""
    hass.config_entries.options.async_abort(result["flow_id"])


async def test_options_flow_underlying_with_missing_settings(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """A device with a missing mandatory setting is flagged in the list and the 'configuration not complete' menu opens the list"""
    data = _climate_valve_data() | {CONF_OPENING_DEGREE_LIST: ["number.opening1"]}
    _, result = await _open_options(hass, data)
    assert result["menu_options"][-1] == "configuration_not_complete"

    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"next_step_id": "configuration_not_complete"})
    assert result["step_id"] == "configuration_not_complete"
    assert result["menu_options"] == ["type", "menu"]
    assert "climate.mock_climate2" in result["description_placeholders"]["missing_items"]

    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"next_step_id": "type"})
    assert result["step_id"] == "type"
    assert not result["description_placeholders"]["underlying_1_details"].startswith("⚠")
    assert result["description_placeholders"]["underlying_2_details"].startswith("⚠")

    # Open the device with the missing opening entity and fix it
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"next_step_id": "underlying_2"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "underlying"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening2",
            CONF_SYNC_ENTITY: "number.calibration2",
            CONF_MIN_OPENING_DEGREE: 20,
            CONF_MAX_OPENING_DEGREE: 90,
        },
    )
    assert result["step_id"] == "type"
    assert not result["description_placeholders"]["underlying_2_details"].startswith("⚠")
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"next_step_id": "menu"})
    assert "finalize" in result["menu_options"]
    hass.config_entries.options.async_abort(result["flow_id"])


async def test_underlying_edit_keeps_the_lists_consistent(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """Editing a device changes the position of this device in all the lists and nothing else"""
    entry, result = await _open_options(hass, _climate_valve_data())
    original = dict(entry.data)
    flow_id = result["flow_id"]
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "type"})
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_2"})
    assert result["step_id"] == "underlying"
    # The edit form has the replace and remove fields, with the current values suggested
    assert CONF_REPLACE_ENTITY in result["data_schema"].schema
    assert CONF_REMOVE_UNDERLYING in result["data_schema"].schema
    suggested = {str(key): key.description["suggested_value"] for key in result["data_schema"].schema if key.description}
    assert suggested[CONF_OPENING_DEGREE_ENTITY] == "number.opening2"
    assert suggested[CONF_SYNC_ENTITY] == "number.calibration2"
    assert suggested[CONF_MIN_OPENING_DEGREE] == 20
    assert suggested[CONF_MAX_OPENING_DEGREE] == 90
    assert suggested[CONF_REPLACE_ENTITY] == "climate.mock_climate2"

    result = await hass.config_entries.options.async_configure(
        flow_id,
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.new_opening2",
            CONF_CLOSING_DEGREE_ENTITY: "number.new_closing2",
            CONF_SYNC_ENTITY: "number.new_calibration2",
            CONF_MIN_OPENING_DEGREE: 25,
            CONF_MAX_OPENING_DEGREE: 95,
            CONF_REPLACE_ENTITY: "climate.mock_climate2",
            CONF_REMOVE_UNDERLYING: False,
        },
    )
    assert result["step_id"] == "type"

    # The other device is untouched, the closing entity of the first device is missing: closing entities are all or none
    flow = hass.config_entries.options._progress[flow_id]  # pylint: disable=protected-access
    infos = flow._infos  # pylint: disable=protected-access
    assert infos[CONF_UNDERLYING_LIST] == original[CONF_UNDERLYING_LIST]
    assert infos[CONF_OPENING_DEGREE_LIST] == ["number.opening1", "number.new_opening2"]
    assert infos[CONF_CLOSING_DEGREE_LIST] == ["", "number.new_closing2"]
    assert infos[CONF_SYNC_ENTITY_LIST] == ["number.calibration1", "number.new_calibration2"]
    assert infos[CONF_MIN_OPENING_DEGREES] == "10, 25"
    assert infos[CONF_MAX_OPENING_DEGREES] == "80, 95"
    assert result["description_placeholders"]["underlying_1_details"].startswith("⚠")
    assert not result["description_placeholders"]["underlying_2_details"].startswith("⚠")
    assert [(item.step_id, item.fields) for item in flow.get_missing_config(infos)] == [("type", [CONF_CLOSING_DEGREE_ENTITY])]

    # the configuration entry is not modified until the finalization
    assert dict(entry.data) == original
    hass.config_entries.options.async_abort(flow_id)


async def test_underlying_replace_and_remove(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """Replace the entity of a device, then remove a device: all the lists stay aligned"""
    entry, result = await _open_options(hass, _climate_valve_data() | {CONF_CLOSING_DEGREE_LIST: ["number.closing1", "number.closing2"]})
    flow_id = result["flow_id"]
    flow = hass.config_entries.options._progress[flow_id]  # pylint: disable=protected-access
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "type"})

    # 1. replace the entity of the first device, an entity already used is refused
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_1"})
    result = await hass.config_entries.options.async_configure(
        flow_id,
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening1",
            CONF_CLOSING_DEGREE_ENTITY: "number.closing1",
            CONF_SYNC_ENTITY: "number.calibration1",
            CONF_MIN_OPENING_DEGREE: 10,
            CONF_MAX_OPENING_DEGREE: 80,
            CONF_REPLACE_ENTITY: "climate.mock_climate2",
        },
    )
    assert result["step_id"] == "underlying"
    assert result["errors"] == {CONF_REPLACE_ENTITY: "underlying_already_added"}

    result = await hass.config_entries.options.async_configure(
        flow_id,
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening1",
            CONF_CLOSING_DEGREE_ENTITY: "number.closing1",
            CONF_SYNC_ENTITY: "number.calibration1",
            CONF_MIN_OPENING_DEGREE: 10,
            CONF_MAX_OPENING_DEGREE: 80,
            CONF_REPLACE_ENTITY: "climate.mock_climate3",
        },
    )
    assert result["step_id"] == "type"
    assert flow._infos[CONF_UNDERLYING_LIST] == ["climate.mock_climate3", "climate.mock_climate2"]  # pylint: disable=protected-access
    assert flow._infos[CONF_OPENING_DEGREE_LIST] == ["number.opening1", "number.opening2"]  # pylint: disable=protected-access

    # 2. add a third device
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_add"})
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_UNDERLYING_ENTITY: "climate.mock_climate2"})
    assert result["step_id"] == "underlying_add"
    assert result["errors"] == {CONF_UNDERLYING_ENTITY: "underlying_already_added"}
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_UNDERLYING_ENTITY: "climate.mock_climate4"})
    assert result["step_id"] == "underlying"
    # no replace nor remove for a new device
    assert CONF_REPLACE_ENTITY not in result["data_schema"].schema
    assert CONF_REMOVE_UNDERLYING not in result["data_schema"].schema
    result = await hass.config_entries.options.async_configure(
        flow_id,
        user_input={
            CONF_OPENING_DEGREE_ENTITY: "number.opening4",
            CONF_CLOSING_DEGREE_ENTITY: "number.closing4",
            CONF_SYNC_ENTITY: "number.calibration4",
            CONF_MIN_OPENING_DEGREE: 0,
            CONF_MAX_OPENING_DEGREE: 100,
        },
    )
    assert result["menu_options"] == ["underlying_common", "underlying_1", "underlying_2", "underlying_3", "underlying_add", "menu"]
    infos = flow._infos  # pylint: disable=protected-access
    assert infos[CONF_UNDERLYING_LIST] == ["climate.mock_climate3", "climate.mock_climate2", "climate.mock_climate4"]
    assert infos[CONF_OPENING_DEGREE_LIST] == ["number.opening1", "number.opening2", "number.opening4"]
    assert infos[CONF_CLOSING_DEGREE_LIST] == ["number.closing1", "number.closing2", "number.closing4"]
    assert infos[CONF_SYNC_ENTITY_LIST] == ["number.calibration1", "number.calibration2", "number.calibration4"]
    assert infos[CONF_MIN_OPENING_DEGREES] == "10, 20, 0"
    assert infos[CONF_MAX_OPENING_DEGREES] == "80, 90, 100"

    # 3. remove the second device
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_2"})
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_REMOVE_UNDERLYING: True})
    assert result["step_id"] == "type"
    assert result["menu_options"] == ["underlying_common", "underlying_1", "underlying_2", "underlying_add", "menu"]
    assert infos[CONF_UNDERLYING_LIST] == ["climate.mock_climate3", "climate.mock_climate4"]
    assert infos[CONF_OPENING_DEGREE_LIST] == ["number.opening1", "number.opening4"]
    assert infos[CONF_CLOSING_DEGREE_LIST] == ["number.closing1", "number.closing4"]
    assert infos[CONF_SYNC_ENTITY_LIST] == ["number.calibration1", "number.calibration4"]
    assert infos[CONF_MIN_OPENING_DEGREES] == "10, 0"
    assert infos[CONF_MAX_OPENING_DEGREES] == "80, 100"
    assert flow.get_missing_config(infos) == []

    # 4. the configuration entry is updated when the flow is finalized
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "menu"})
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "finalize"})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_UNDERLYING_LIST] == ["climate.mock_climate3", "climate.mock_climate4"]
    assert entry.data[CONF_OPENING_DEGREE_LIST] == ["number.opening1", "number.opening4"]


async def test_underlying_remove_last_values_removes_the_optional_lists(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """The optional lists are removed when no device uses them anymore, the min / max opening degrees when they are the default ones"""
    data = _climate_valve_data() | {CONF_CLOSING_DEGREE_LIST: ["number.closing1", ""]}
    _, result = await _open_options(hass, data)
    flow_id = result["flow_id"]
    flow = hass.config_entries.options._progress[flow_id]  # pylint: disable=protected-access
    await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "type"})

    # The closing entity of the first device is removed: the closing list is empty
    await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_1"})
    await hass.config_entries.options.async_configure(
        flow_id,
        user_input={CONF_OPENING_DEGREE_ENTITY: "number.opening1", CONF_SYNC_ENTITY: "number.calibration1", CONF_MIN_OPENING_DEGREE: 0, CONF_MAX_OPENING_DEGREE: 100},
    )
    assert flow._infos[CONF_CLOSING_DEGREE_LIST] == []  # pylint: disable=protected-access
    # the second device has min 20 and max 90, so the lists are still there
    assert flow._infos[CONF_MIN_OPENING_DEGREES] == "0, 20"  # pylint: disable=protected-access
    assert flow._infos[CONF_MAX_OPENING_DEGREES] == "100, 90"  # pylint: disable=protected-access

    await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_2"})
    await hass.config_entries.options.async_configure(
        flow_id,
        user_input={CONF_OPENING_DEGREE_ENTITY: "number.opening2", CONF_SYNC_ENTITY: "number.calibration2", CONF_MIN_OPENING_DEGREE: 0, CONF_MAX_OPENING_DEGREE: 100},
    )
    assert CONF_MIN_OPENING_DEGREES not in flow._infos  # pylint: disable=protected-access
    assert CONF_MAX_OPENING_DEGREES not in flow._infos  # pylint: disable=protected-access
    hass.config_entries.options.async_abort(flow_id)


async def test_underlying_shorter_csv_lists_use_default_values(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """The min / max opening degrees of an existing configuration can be shorter than the underlyings: the default values are used"""
    data = _climate_valve_data() | {CONF_MIN_OPENING_DEGREES: "10", CONF_MAX_OPENING_DEGREES: "80"}
    _, result = await _open_options(hass, data)
    flow_id = result["flow_id"]
    await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "type"})
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_2"})
    suggested = {str(key): key.description["suggested_value"] for key in result["data_schema"].schema if key.description}
    assert suggested[CONF_MIN_OPENING_DEGREE] == 0
    assert suggested[CONF_MAX_OPENING_DEGREE] == 100
    # the number selectors are bounded by the maximum of the valve
    assert result["data_schema"].schema[CONF_MAX_OPENING_DEGREE].config["max"] == 100
    hass.config_entries.options.async_abort(flow_id)


async def test_over_switch_underlyings(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """An over_switch device: custom commands are optional for a switch (in a section) and mandatory for the other entities"""
    data = _complete_switch_infos()
    entry, result = await _open_options(hass, data)
    flow_id = result["flow_id"]
    flow = hass.config_entries.options._progress[flow_id]  # pylint: disable=protected-access
    await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "type"})

    # common settings of a switch
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_common"})
    assert set(result["data_schema"].schema.keys()) == {CONF_HEATER_KEEP_ALIVE, CONF_PROP_FUNCTION, CONF_AC_MODE, CONF_INVERSE_SWITCH}
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI, CONF_AC_MODE: True})
    assert result["step_id"] == "type"
    assert flow._infos[CONF_AC_MODE] is True  # pylint: disable=protected-access

    # a switch: the commands are in a section
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_add"})
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_UNDERLYING_ENTITY: "switch.mock_switch2"})
    assert result["step_id"] == "underlying"
    assert CONF_VSWITCH_COMMANDS_SECTION in result["data_schema"].schema
    assert CONF_VSWITCH_ON_CMD not in result["data_schema"].schema
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_VSWITCH_COMMANDS_SECTION: {}})
    assert result["step_id"] == "type"
    assert CONF_VSWITCH_ON_CMD_LIST not in flow._infos  # pylint: disable=protected-access
    assert flow._infos[CONF_UNDERLYING_LIST] == ["switch.mock_switch", "switch.mock_switch2"]  # pylint: disable=protected-access

    # an entity which is not a switch: the commands are mandatory and are checked
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_add"})
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_UNDERLYING_ENTITY: "select.mock_select"})
    assert result["step_id"] == "underlying"
    assert CONF_VSWITCH_ON_CMD in result["data_schema"].schema
    assert CONF_VSWITCH_COMMANDS_SECTION not in result["data_schema"].schema
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_VSWITCH_ON_CMD: "select_option/option on", CONF_VSWITCH_OFF_CMD: "select_option/option:off"})
    assert result["step_id"] == "underlying"
    assert result["errors"] == {"base": "vswitch_configuration_incorrect"}
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_VSWITCH_ON_CMD: "select_option/option:on", CONF_VSWITCH_OFF_CMD: "select_option/option:off"})
    assert result["step_id"] == "type"
    infos = flow._infos  # pylint: disable=protected-access
    assert infos[CONF_UNDERLYING_LIST] == ["switch.mock_switch", "switch.mock_switch2", "select.mock_select"]
    assert infos[CONF_VSWITCH_ON_CMD_LIST] == ["", "", "select_option/option:on"]
    assert infos[CONF_VSWITCH_OFF_CMD_LIST] == ["", "", "select_option/option:off"]

    # The commands are given for all the devices or for none: the switches have to be completed
    assert [(item.step_id, item.fields, item.device) for item in flow.get_missing_config(infos)] == [
        ("type", [CONF_VSWITCH_ON_CMD, CONF_VSWITCH_OFF_CMD], "switch.mock_switch"),
        ("type", [CONF_VSWITCH_ON_CMD, CONF_VSWITCH_OFF_CMD], "switch.mock_switch2"),
    ]
    assert result["description_placeholders"]["underlying_1_details"].startswith("⚠")
    for idx, entity_id in ((1, "switch.mock_switch"), (2, "switch.mock_switch2")):
        result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": f"underlying_{idx}"})
        assert result["step_id"] == "underlying"
        # the section is expanded when a device has commands
        result = await hass.config_entries.options.async_configure(
            flow_id, user_input={CONF_VSWITCH_COMMANDS_SECTION: {CONF_VSWITCH_ON_CMD: f"turn_on{idx}", CONF_VSWITCH_OFF_CMD: f"turn_off{idx}"}}
        )
        assert result["step_id"] == "type"
    assert infos[CONF_VSWITCH_ON_CMD_LIST] == ["turn_on1", "turn_on2", "select_option/option:on"]
    assert infos[CONF_VSWITCH_OFF_CMD_LIST] == ["turn_off1", "turn_off2", "select_option/option:off"]
    assert flow.get_missing_config(infos) == []

    # Replace the select by a switch: the commands become optional
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_3"})
    result = await hass.config_entries.options.async_configure(
        flow_id, user_input={CONF_VSWITCH_ON_CMD: "select_option/option:on", CONF_VSWITCH_OFF_CMD: "select_option/option:off", CONF_REPLACE_ENTITY: "switch.mock_switch3"}
    )
    # the form is displayed again for the new kind of entity
    assert result["step_id"] == "underlying"
    assert flow._infos[CONF_UNDERLYING_LIST][2] == "switch.mock_switch3"  # pylint: disable=protected-access
    assert CONF_VSWITCH_COMMANDS_SECTION in result["data_schema"].schema
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_VSWITCH_COMMANDS_SECTION: {CONF_VSWITCH_ON_CMD: "turn_on3", CONF_VSWITCH_OFF_CMD: "turn_off3"}})
    assert result["step_id"] == "type"
    assert flow._infos[CONF_VSWITCH_ON_CMD_LIST] == ["turn_on1", "turn_on2", "turn_on3"]  # pylint: disable=protected-access
    assert dict(entry.data) == data
    hass.config_entries.options.async_abort(flow_id)


async def test_over_valve_underlyings(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """An over_valve device has a minimum and a maximum opening, bounded by the maximum of the valve"""
    data = _complete_switch_infos() | {
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_VALVE,
        CONF_UNDERLYING_LIST: ["number.valve1"],
        CONF_MIN_OPENING_DEGREES: "10",
        CONF_MAX_OPENING_DEGREES: "80",
    }
    _, result = await _open_options(hass, data)
    flow_id = result["flow_id"]
    flow = hass.config_entries.options._progress[flow_id]  # pylint: disable=protected-access
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "type"})
    assert result["menu_options"] == ["underlying_common", "underlying_1", "underlying_add", "menu"]

    # add a second valve whose max is 50
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_add"})
    with patch.object(StateMachine, "get", return_value=State("number.valve2", "0", attributes={"max": 50, "min": 0})):
        result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_UNDERLYING_ENTITY: "number.valve2"})
        assert result["step_id"] == "underlying"
        assert result["data_schema"].schema[CONF_MAX_OPENING_DEGREE].config["max"] == 50
        assert set(result["data_schema"].schema.keys()) == {CONF_MIN_OPENING_DEGREE, CONF_MAX_OPENING_DEGREE}
        result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_MIN_OPENING_DEGREE: 5, CONF_MAX_OPENING_DEGREE: 50})
    assert result["step_id"] == "type"
    assert flow._infos[CONF_UNDERLYING_LIST] == ["number.valve1", "number.valve2"]  # pylint: disable=protected-access
    assert flow._infos[CONF_MIN_OPENING_DEGREES] == "10, 5"  # pylint: disable=protected-access
    # 50 is the default of the second valve but the first one has 80
    assert flow._infos[CONF_MAX_OPENING_DEGREES] == "80, 50"  # pylint: disable=protected-access
    hass.config_entries.options.async_abort(flow_id)


async def test_underlying_slots_are_generated(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """One step is generated for each device which can be displayed, and the menu is limited to the slots"""
    from custom_components.versatile_thermostat.config_flow import VersatileThermostatOptionsFlowHandler  # pylint: disable=import-outside-toplevel

    for slot in range(1, MAX_UNDERLYINGS + 1):
        assert hasattr(VersatileThermostatOptionsFlowHandler, f"async_step_underlying_{slot}")
        assert hasattr(VersatileThermostatConfigFlow, f"async_step_underlying_{slot}")
    assert not hasattr(VersatileThermostatConfigFlow, f"async_step_underlying_{MAX_UNDERLYINGS + 1}")

    # with the maximum of devices, a device cannot be added anymore
    entities = [f"switch.mock_switch{idx}" for idx in range(MAX_UNDERLYINGS)]
    _, result = await _open_options(hass, _complete_switch_infos() | {CONF_UNDERLYING_LIST: entities})
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"next_step_id": "type"})
    assert len(result["menu_options"]) == MAX_UNDERLYINGS + 2
    assert "underlying_add" not in result["menu_options"]
    assert result["menu_options"][-2] == f"underlying_{MAX_UNDERLYINGS}"
    hass.config_entries.options.async_abort(result["flow_id"])


async def test_underlying_with_nothing_to_ask_is_added_directly(hass: HomeAssistant, init_vtherm_api, skip_hass_states_get) -> None:
    """An over_climate without valve regulation nor synchronization has no specific setting: the device is added at once"""
    data = _complete_switch_infos() | {CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE, CONF_UNDERLYING_LIST: ["climate.mock_climate1"]}
    _, result = await _open_options(hass, data)
    flow_id = result["flow_id"]
    await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "type"})
    await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_add"})
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_UNDERLYING_ENTITY: "climate.mock_climate2"})
    assert result["step_id"] == "type"
    assert result["menu_options"] == ["underlying_common", "underlying_1", "underlying_2", "underlying_add", "menu"]

    # the edit form of such a device only has the replace and remove fields
    result = await hass.config_entries.options.async_configure(flow_id, user_input={"next_step_id": "underlying_2"})
    assert result["step_id"] == "underlying"
    assert set(result["data_schema"].schema.keys()) == {CONF_REPLACE_ENTITY, CONF_REMOVE_UNDERLYING}
    result = await hass.config_entries.options.async_configure(flow_id, user_input={CONF_REMOVE_UNDERLYING: True})
    assert result["menu_options"] == ["underlying_common", "underlying_1", "underlying_add", "menu"]
    hass.config_entries.options.async_abort(flow_id)


TRANSLATIONS_DIR = Path(__file__).parent.parent / "custom_components" / DOMAIN / "translations"


@pytest.mark.parametrize("language_file", sorted(TRANSLATIONS_DIR.glob("*.json")), ids=lambda path: path.stem)
@pytest.mark.parametrize("section", ["config", "options"])
def test_translations_of_the_config_flow_steps(language_file: Path, section: str) -> None:
    """The steps and the errors added by the config flow are translated in all the languages, in the config and options sections"""
    translations = json.loads(language_file.read_text(encoding="utf-8"))
    steps = translations[section]["step"]

    # The steps of the underlyings
    for step_id in ("type", "underlying_common", "underlying_common_extra", "underlying_add", "underlying", "configuration_not_complete"):
        assert step_id in steps, step_id
        assert steps[step_id]["title"]
    assert steps["underlying"]["sections"]["commands"]["name"]

    # The menu of the underlyings has one option and one description for each device which can be displayed
    menu_options = steps["type"]["menu_options"]
    descriptions = steps["type"]["menu_option_descriptions"]
    for key in ["underlying_common", "underlying_add", "menu"] + [f"underlying_{slot}" for slot in range(1, MAX_UNDERLYINGS + 1)]:
        assert menu_options[key], key
    for slot in range(1, MAX_UNDERLYINGS + 1):
        assert menu_options[f"underlying_{slot}"] == "{underlying_%d}" % slot
        assert descriptions[f"underlying_{slot}"] == "{underlying_%d_details}" % slot

    # The valve regulation and the synchronization are now settings of the underlyings
    for step_id in ("valve_regulation", "sync_device_internal_temp"):
        assert step_id not in steps
        assert step_id not in steps.get("menu", {}).get("menu_options", {})
        assert step_id not in steps["configuration_not_complete"]["menu_options"]

    # The steps which can be fixed from the 'configuration not complete' menu
    for step_id in ("main", "type", "tpi", "presets", "power", "motion", "presence", "advanced", "central_boiler", "menu"):
        assert steps["configuration_not_complete"]["menu_options"][step_id]
    assert "{missing_items}" in steps["configuration_not_complete"]["description"]

    errors = translations[section]["error"]
    for key in ("underlying_already_added", "max_opening_degree_out_of_range", "underlying_field_missing", "missing_settings_summary", "min_max_opening_degrees_inconsistent", "vswitch_configuration_incorrect"):
        assert errors[key], key
