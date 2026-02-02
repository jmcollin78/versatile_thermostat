"""Global fixtures for integration_blueprint integration."""
# pylint: disable=line-too-long, wildcard-import, unused-wildcard-import, redefined-outer-name

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
from unittest.mock import patch, MagicMock

import pytest
# https://github.com/miketheman/pytest-socket/pull/275
from pytest_socket import socket_allow_hosts

from homeassistant.core import StateMachine, State
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN

from custom_components.versatile_thermostat.config_flow import (
    VersatileThermostatBaseConfigFlow,
)

from custom_components.versatile_thermostat.const import *
from custom_components.versatile_thermostat.vtherm_api import VersatileThermostatAPI
from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.vtherm_hvac_mode import *

from .commons import *

# ...
def pytest_runtest_setup():
    """setup tests"""
    socket_allow_hosts(
        allowed=["localhost", "127.0.0.1", "::1"], allow_unix_socket=True
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
    """Skip the get state in HomeAssistant by returning a mock State object"""
    mock_state = MagicMock(spec=State)
    mock_state.state = "20"
    mock_state.attributes = {"max": 100, "min": 0}
    with patch.object(StateMachine, "get", return_value=mock_state):
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


@pytest.fixture(autouse=True)
def isolate_singleton_state():
    """
    Cette fixture s'exécute AVANT et APRÈS chaque test,
    garantissant un état propre pour MonSingleton.
    """
    # 1. Setup : Le test s'exécute ici.
    yield

    # 2. Teardown : Exécuté après que le test soit terminé.
    # On force la réinitialisation de l'instance unique
    # reset API to avoid side effects between tests
    VersatileThermostatAPI.reset_vtherm_api()


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


@pytest.fixture(name="init_central_power_manager")
async def init_central_power_manager_fixture(
    hass, init_central_config
):  # pylint: disable=unused-argument
    """Initialize the central power_manager"""
    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # 1. creation / init
    vtherm_api.central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
        }
    )
    assert vtherm_api.central_power_manager.is_configured

    yield


@pytest.fixture(name="fake_underlying_switch")
async def fake_underlying_switch_fixture(hass):
    """Fixture to add an underlying switch named "switch.mock_switch" to a test"""
    switch = MockSwitch(hass, "mock_switch", "theMockedSwitch")
    await register_mock_entity(hass, switch, SWITCH_DOMAIN)
    yield switch


@pytest.fixture(name="fake_underlying_valve")
async def fake_underlying_valve_fixture(hass):
    """Fixture to add an underlying valve named "switch.mock_valve" to a test"""
    valve = MockNumber(hass, "mock_valve", "theMockedValve")
    await register_mock_entity(hass, valve, NUMBER_DOMAIN)
    yield valve


@pytest.fixture(name="fake_opening_degree")
async def fake_opening_degree_fixture(hass):
    """Fixture to add an underlying number opening degree named "number.mock_opening_degree" to a test"""
    opening_degree = MockNumber(hass, "mock_opening_degree", "theMockedOpeningDegree")
    await register_mock_entity(hass, opening_degree, NUMBER_DOMAIN)
    yield opening_degree


@pytest.fixture(name="fake_underlying_switch_ac")
async def fake_underlying_switch_ac_fixture(hass):
    """Fixture to add an underlying switch named "switch.mock_switch" to a test"""
    switch = MockSwitch(hass, "mock_switch", "theMockedSwitch", {"ac_mode": True})
    await register_mock_entity(hass, switch, SWITCH_DOMAIN)
    yield switch


@pytest.fixture(name="fake_underlying_climate")
async def fake_underlying_climate_fixture(hass):
    """Fixture to add an underlying switch named "climate.mock_climate" to a test"""
    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {})
    yield fake_underlying_climate


@pytest.fixture(name="fake_underlying_climate_off_cool")
async def fake_underlying_climate_off_cool_fixture(hass):
    """Fixture to add an underlying switch named "climate.mock_climate" to a test"""
    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL])
    yield fake_underlying_climate
