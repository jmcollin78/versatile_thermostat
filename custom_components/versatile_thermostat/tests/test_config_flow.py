""" Test the Versatile Thermostat config flow """

from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import SOURCE_USER, ConfigEntry

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.versatile_thermostat.const import DOMAIN
from custom_components.versatile_thermostat import VersatileThermostatAPI

from custom_components.versatile_thermostat.tests.const import (
    MOCK_TH_OVER_SWITCH_USER_CONFIG,
    MOCK_TH_OVER_SWITCH_TYPE_CONFIG,
    MOCK_TH_OVER_SWITCH_TPI_CONFIG,
    MOCK_PRESETS_CONFIG,
    MOCK_ADVANCED_CONFIG,
    MOCK_DEFAULT_FEATURE_CONFIG,
)


async def test_show_form(hass: HomeAssistant) -> None:
    """Test that the form is served with no input"""
    # Init the API
    # hass.data["custom_components"] = None
    # loader.async_get_custom_components(hass)
    # VersatileThermostatAPI(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == SOURCE_USER


async def test_user_config_flow_over_switch(hass, skip_validate_input):
    """Test the config flow with thermostat_over_switch features"""
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
        | MOCK_ADVANCED_CONFIG
        | MOCK_DEFAULT_FEATURE_CONFIG
    )
    assert result["result"]
    assert result["result"].domain == DOMAIN
    assert result["result"].version == 1
    assert result["result"].title == "TheOverSwitchMockName"
    assert isinstance(result["result"], ConfigEntry)
