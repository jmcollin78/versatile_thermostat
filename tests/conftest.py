"""Global fixtures for integration_blueprint integration."""
# pylint: disable=line-too-long

# Fixtures allow you to replace functions with a Mock object. You can perform
# many options via the Mock to reflect a particular behavior from the original
# function that you want to see without going through the function's actual logic.
# Fixtures can either be passed into tests as parameters, or if autouse=True, they
# will automatically be used across all tests.
#
# Fixtures that are defined in conftest.py are available across all tests. You can also
# define fixtures within a particular test file to scope them locally.
#
# pytest_homeassistant_custom_component provides some fixtures that are provided by
# Home Assistant core. You can find those fixture definitions here:
# https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/pytest_homeassistant_custom_component/common.py
#
# See here for more info: https://docs.pytest.org/en/latest/fixture.html (note that
# pytest includes fixtures OOB which you can use as defined on this page)
from unittest.mock import patch

import pytest

from homeassistant.core import StateMachine

from custom_components.versatile_thermostat.config_flow import (
    VersatileThermostatBaseConfigFlow,
)

from custom_components.versatile_thermostat.vtherm_api import VersatileThermostatAPI
from custom_components.versatile_thermostat.base_thermostat import BaseThermostat

from .commons import (
    create_central_config,
    FULL_CENTRAL_CONFIG,
    FULL_CENTRAL_CONFIG_WITH_BOILER,
)

pytest_plugins = "pytest_homeassistant_custom_component"  # pylint: disable=invalid-name


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations,
):  # pylint: disable=unused-argument
    """Enable all integration in tests"""
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


@pytest.fixture(name="skip_turn_on_off_heater")
def skip_turn_on_off_heater():
    """Skip turning on and off the heater"""
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingEntity.turn_on"
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingEntity.turn_off"
    ):
        yield


# This fixture is used to bypass the validate_input function in config_flow
# NOT USED Now (keeped for memory)
@pytest.fixture(name="skip_validate_input")
def skip_validate_input_fixture():
    """Skip the validate_input in config flow"""
    with patch.object(VersatileThermostatBaseConfigFlow, "validate_input"):
        yield


@pytest.fixture(name="skip_hass_states_get")
def skip_hass_states_get_fixture():
    """Skip the get state in HomeAssistant"""
    with patch.object(StateMachine, "get"):
        yield


@pytest.fixture(name="skip_control_heating")
def skip_control_heating_fixture():
    """Skip the control_heating of VersatileThermostat"""
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        yield


@pytest.fixture(name="skip_find_underlying_climate")
def skip_find_underlying_climate_fixture():
    """Skip the find_underlying_climate of VersatileThermostat"""
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate"
    ):
        yield


@pytest.fixture(name="skip_hass_states_is_state")
def skip_hass_states_is_state_fixture():
    """Skip the is_state in HomeAssistant"""
    with patch.object(StateMachine, "is_state", return_value=False):
        yield


@pytest.fixture(name="skip_send_event")
def skip_send_event_fixture():
    """Skip the send_event in BaseThermostat"""
    with patch.object(BaseThermostat, "send_event"):
        yield


@pytest.fixture(name="init_vtherm_api")
def init_vtherm_api_fixture(hass):
    """Initialize the VTherm API"""
    VersatileThermostatAPI.get_vtherm_api(hass)
    yield


@pytest.fixture(name="init_central_config")
async def init_central_config_fixture(
    hass, init_vtherm_api
):  # pylint: disable=unused-argument
    """Initialize the VTherm API"""
    await create_central_config(hass, FULL_CENTRAL_CONFIG)

    yield


@pytest.fixture(name="init_central_config_with_boiler_fixture")
async def init_central_config_with_boiler_fixture(
    hass, init_vtherm_api
):  # pylint: disable=unused-argument
    """Initialize the VTherm API"""
    await create_central_config(hass, FULL_CENTRAL_CONFIG_WITH_BOILER)

    yield
