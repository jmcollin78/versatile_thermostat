# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the underlying_unavailable message and the unavailable_underlying_entities attribute """
import logging

from homeassistant.core import HomeAssistant

from .commons import *

logging.getLogger().setLevel(logging.DEBUG)


def _specific_states(entity: BaseThermostat) -> dict:
    """Return the specific_states attributes as exposed by the VTherm state"""
    return entity._attr_extra_state_attributes["specific_states"]


async def test_over_climate_underlying_unavailable(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event, fake_underlying_climate):
    """The underlying climate becomes unavailable then available again after the startup"""

    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="uniqueId", data=PARTIAL_CLIMATE_CONFIG)
    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert entity
    assert entity.is_over_climate is True
    assert entity.is_initialized is True

    specific_states = _specific_states(entity)
    assert specific_states["unavailable_underlying_entities"] == []
    assert MSG_UNDERLYING_UNAVAILABLE not in specific_states["messages"]

    # The underlying becomes unavailable
    hass.states.async_set("climate.mock_climate", STATE_UNAVAILABLE)
    await wait_for_local_condition(
        lambda: (
            hass.states.get("climate.theoverclimatemockname") is not None
            and hass.states.get("climate.theoverclimatemockname").attributes.get("specific_states", {}).get("unavailable_underlying_entities")
            == ["climate.mock_climate"]
        ),
        hass=hass,
    )

    specific_states = _specific_states(entity)
    assert specific_states["unavailable_underlying_entities"] == ["climate.mock_climate"]
    assert MSG_UNDERLYING_UNAVAILABLE in specific_states["messages"]
    assert MSG_NOT_INITIALIZED not in specific_states["messages"]
    # the published HA state is refreshed too
    published = hass.states.get("climate.theoverclimatemockname")
    assert published.attributes["specific_states"]["unavailable_underlying_entities"] == ["climate.mock_climate"]

    # The underlying is back
    hass.states.async_set("climate.mock_climate", "heat")
    await wait_for_local_condition(
        lambda: (
            hass.states.get("climate.theoverclimatemockname") is not None
            and hass.states.get("climate.theoverclimatemockname").attributes.get("specific_states", {}).get("unavailable_underlying_entities") == []
        ),
        hass=hass,
    )

    specific_states = _specific_states(entity)
    assert specific_states["unavailable_underlying_entities"] == []
    assert MSG_UNDERLYING_UNAVAILABLE not in specific_states["messages"]
    published = hass.states.get("climate.theoverclimatemockname")
    assert published.attributes["specific_states"]["unavailable_underlying_entities"] == []

    # unknown is handled like unavailable
    hass.states.async_set("climate.mock_climate", STATE_UNKNOWN)
    await wait_for_local_condition(
        lambda: (
            hass.states.get("climate.theoverclimatemockname") is not None
            and hass.states.get("climate.theoverclimatemockname").attributes.get("specific_states", {}).get("unavailable_underlying_entities")
            == ["climate.mock_climate"]
        ),
        hass=hass,
    )
    assert _specific_states(entity)["unavailable_underlying_entities"] == ["climate.mock_climate"]

    entity.remove_thermostat()


async def test_over_switch_underlying_unavailable(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch: MockSwitch):
    """The underlying switch becomes unavailable then available again after the startup"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_SAFETY_DELAY_MIN: 10,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.01,
        },
    )
    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity
    assert entity.is_initialized is True

    specific_states = _specific_states(entity)
    assert specific_states["unavailable_underlying_entities"] == []
    assert MSG_UNDERLYING_UNAVAILABLE not in specific_states["messages"]

    hass.states.async_set("switch.mock_switch", STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    specific_states = _specific_states(entity)
    assert specific_states["unavailable_underlying_entities"] == ["switch.mock_switch"]
    assert MSG_UNDERLYING_UNAVAILABLE in specific_states["messages"]
    published = hass.states.get("climate.theoverswitchmockname")
    assert published.attributes["specific_states"]["unavailable_underlying_entities"] == ["switch.mock_switch"]

    hass.states.async_set("switch.mock_switch", STATE_OFF)
    await hass.async_block_till_done()

    specific_states = _specific_states(entity)
    assert specific_states["unavailable_underlying_entities"] == []
    assert MSG_UNDERLYING_UNAVAILABLE not in specific_states["messages"]

    entity.remove_thermostat()


async def test_over_climate_not_initialized_has_no_unavailable_message(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """At startup with a missing underlying, only not_initialized is reported"""

    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="uniqueId", data=PARTIAL_CLIMATE_CONFIG)
    # no fake_underlying_climate: the underlying is not found
    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert entity
    assert entity.is_initialized is False

    entity.update_custom_attributes()
    specific_states = _specific_states(entity)
    assert MSG_NOT_INITIALIZED in specific_states["messages"]
    assert MSG_UNDERLYING_UNAVAILABLE not in specific_states["messages"]
    assert specific_states["not_initialized_entities"] == ["climate.mock_climate"]
    assert specific_states["unavailable_underlying_entities"] == []

    entity.remove_thermostat()
