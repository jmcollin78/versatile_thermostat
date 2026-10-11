# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the underlying battery sensor of the over_climate VTherm """
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.versatile_thermostat.sensor import find_underlying_battery_entities

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


def _climate_config(name: str, underlyings: list[str]) -> dict:
    """Build a minimal over_climate configuration"""
    return {
        CONF_NAME: name,
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 15,
        CONF_TEMP_MAX: 30,
        "eco_temp": 17,
        "comfort_temp": 18,
        "boost_temp": 19,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_UNDERLYING_LIST: underlyings,
        CONF_MINIMAL_ACTIVATION_DELAY: 30,
        CONF_MINIMAL_DEACTIVATION_DELAY: 0,
        CONF_SAFETY_DELAY_MIN: 5,
        CONF_SAFETY_MIN_ON_PERCENT: 0.3,
    }


def _add_device(hass: HomeAssistant, device_key: str, climate_id: str, battery_ids: list[str] | None = None, other_sensor: bool = False):
    """Register a device with a climate entity and optional battery sensors in the registries"""
    config_entry = MockConfigEntry(domain="test_underlying", title=f"dev_{device_key}")
    config_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(config_entry_id=config_entry.entry_id, identifiers={("test_underlying", device_key)})
    ent_reg = er.async_get(hass)
    ent_reg.async_get_or_create("climate", "test_underlying", f"{device_key}_climate", suggested_object_id=climate_id.split(".")[1], device_id=device.id, config_entry=config_entry)
    for battery_id in battery_ids or []:
        ent_reg.async_get_or_create(
            "sensor", "test_underlying", f"{device_key}_{battery_id}", suggested_object_id=battery_id.split(".")[1], device_id=device.id, config_entry=config_entry, original_device_class=SensorDeviceClass.BATTERY
        )
    if other_sensor:
        ent_reg.async_get_or_create(
            "sensor", "test_underlying", f"{device_key}_temp", suggested_object_id=f"{device_key}_temperature", device_id=device.id, config_entry=config_entry, original_device_class=SensorDeviceClass.TEMPERATURE
        )
    return device


def _battery_sensor_id(hass: HomeAssistant, name: str) -> str | None:
    """Return the entity_id of the battery sensor of a VTherm"""
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{name}_underlying_battery")


async def _create_over_climate(hass: HomeAssistant, name: str, underlyings: list[str]):
    """Create an over_climate VTherm and the mock underlyings"""
    for underlying in underlyings:
        await create_and_register_mock_climate(hass, underlying.split(".")[1], "MockClimateName", {})
    entry = MockConfigEntry(domain=DOMAIN, title=name, unique_id=f"uid_{name}", data=_climate_config(name, underlyings))
    entity = await create_thermostat(hass, entry, f"climate.{name.lower()}")
    await hass.async_block_till_done()
    return entry, entity


async def test_find_underlying_battery_entities(hass: HomeAssistant):
    """The helper keeps only battery sensors of the devices of the underlyings, deduplicated"""
    _add_device(hass, "trv1", "climate.trv1", ["sensor.trv1_battery"], other_sensor=True)
    _add_device(hass, "trv2", "climate.trv2", ["sensor.trv2_battery"])
    _add_device(hass, "other", "climate.other", ["sensor.other_battery"])

    assert find_underlying_battery_entities(hass, ["climate.trv1"]) == ["sensor.trv1_battery"]
    assert find_underlying_battery_entities(hass, ["climate.trv1", "climate.trv2", "climate.trv1"]) == ["sensor.trv1_battery", "sensor.trv2_battery"]
    # unknown entity or empty list
    assert find_underlying_battery_entities(hass, ["climate.unknown"]) == []
    assert find_underlying_battery_entities(hass, []) == []


async def test_battery_sensor_one_underlying(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """One underlying with a battery sensor at 80"""
    _add_device(hass, "trv1", "climate.mock_climate", ["sensor.trv1_battery"])
    hass.states.async_set("sensor.trv1_battery", "80")

    _, entity = await _create_over_climate(hass, "TheOverClimateBat", ["climate.mock_climate"])

    sensor_id = _battery_sensor_id(hass, "TheOverClimateBat")
    assert sensor_id is not None
    state = hass.states.get(sensor_id)
    assert state.state == "80.0"
    assert state.attributes["device_class"] == "battery"
    assert state.attributes["unit_of_measurement"] == "%"
    assert state.attributes["state_class"] == "measurement"
    assert state.attributes["battery_entities"] == {"sensor.trv1_battery": 80.0}

    hass.states.async_set("sensor.trv1_battery", "55")
    await hass.async_block_till_done()
    assert hass.states.get(sensor_id).state == "55.0"

    entity.remove_thermostat()


async def test_battery_sensor_two_underlyings(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """Two underlyings: the lowest level is shown"""
    _add_device(hass, "trv1", "climate.mock_climate1", ["sensor.trv1_battery"])
    _add_device(hass, "trv2", "climate.mock_climate2", ["sensor.trv2_battery"])
    hass.states.async_set("sensor.trv1_battery", "80")
    hass.states.async_set("sensor.trv2_battery", "35")

    _, entity = await _create_over_climate(hass, "TheOverClimateBat", ["climate.mock_climate1", "climate.mock_climate2"])
    sensor_id = _battery_sensor_id(hass, "TheOverClimateBat")
    state = hass.states.get(sensor_id)
    assert state.state == "35.0"
    assert state.attributes["battery_entities"] == {"sensor.trv1_battery": 80.0, "sensor.trv2_battery": 35.0}

    hass.states.async_set("sensor.trv2_battery", "90")
    await hass.async_block_till_done()
    state = hass.states.get(sensor_id)
    assert state.state == "80.0"
    assert state.attributes["battery_entities"] == {"sensor.trv1_battery": 80.0, "sensor.trv2_battery": 90.0}

    entity.remove_thermostat()


async def test_battery_sensor_ignores_invalid_states(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """Unavailable, unknown and non numeric states are ignored"""
    _add_device(hass, "trv1", "climate.mock_climate1", ["sensor.trv1_battery"])
    _add_device(hass, "trv2", "climate.mock_climate2", ["sensor.trv2_battery"])
    _add_device(hass, "trv3", "climate.mock_climate3", ["sensor.trv3_battery"])
    hass.states.async_set("sensor.trv1_battery", "80")
    hass.states.async_set("sensor.trv2_battery", "unavailable")
    hass.states.async_set("sensor.trv3_battery", "foo")

    _, entity = await _create_over_climate(hass, "TheOverClimateBat", ["climate.mock_climate1", "climate.mock_climate2", "climate.mock_climate3"])
    sensor_id = _battery_sensor_id(hass, "TheOverClimateBat")
    state = hass.states.get(sensor_id)
    assert state.state == "80.0"
    assert state.attributes["battery_entities"] == {"sensor.trv1_battery": 80.0, "sensor.trv2_battery": None, "sensor.trv3_battery": None}

    # All invalid -> the sensor becomes unavailable
    hass.states.async_set("sensor.trv1_battery", "unknown")
    await hass.async_block_till_done()
    assert hass.states.get(sensor_id).state == "unavailable"

    # And comes back
    hass.states.async_set("sensor.trv2_battery", "42")
    await hass.async_block_till_done()
    assert hass.states.get(sensor_id).state == "42.0"

    entity.remove_thermostat()


async def test_battery_sensor_no_battery_entity(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """No battery entity found: the sensor is unavailable"""
    _add_device(hass, "trv1", "climate.mock_climate", [], other_sensor=True)

    _, entity = await _create_over_climate(hass, "TheOverClimateBat", ["climate.mock_climate"])
    sensor_id = _battery_sensor_id(hass, "TheOverClimateBat")
    assert sensor_id is not None
    assert hass.states.get(sensor_id).state == "unavailable"

    entity.remove_thermostat()


async def test_battery_sensor_late_registry(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """The battery entity is registered after VTherm setup (late integration) and is discovered"""
    _add_device(hass, "trv1", "climate.mock_climate", [])
    _, entity = await _create_over_climate(hass, "TheOverClimateBat", ["climate.mock_climate"])
    sensor_id = _battery_sensor_id(hass, "TheOverClimateBat")
    assert hass.states.get(sensor_id).state == "unavailable"

    _add_device(hass, "trv1", "climate.mock_climate", ["sensor.trv1_battery"])
    hass.states.async_set("sensor.trv1_battery", "66")
    await hass.async_block_till_done()
    assert hass.states.get(sensor_id).state == "66.0"

    entity.remove_thermostat()


async def test_battery_sensor_discovery_waits_for_ha_started(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """When HA is not running yet, the discovery is done on EVENT_HOMEASSISTANT_STARTED"""
    _add_device(hass, "trv1", "climate.mock_climate", [])
    hass.set_state(CoreState.starting)
    _, entity = await _create_over_climate(hass, "TheOverClimateBat", ["climate.mock_climate"])
    sensor_id = _battery_sensor_id(hass, "TheOverClimateBat")
    assert hass.states.get(sensor_id).state == "unavailable"

    # The battery is registered later but the discovery is only done at start
    # (the registry update listener is also active, so here we only check the start event path)
    _add_device(hass, "trv1", "climate.mock_climate", ["sensor.trv1_battery"])
    hass.states.async_set("sensor.trv1_battery", "70")
    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    assert hass.states.get(sensor_id).state == "70.0"

    entity.remove_thermostat()


async def test_battery_sensor_not_created_for_over_switch(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """No battery sensor for an over_switch VTherm"""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchBat",
        unique_id="uid_switch",
        data={
            CONF_NAME: "TheOverSwitchBat",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
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
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
        },
    )
    entity = await create_thermostat(hass, entry, "climate.theoverswitchbat")
    assert entity is not None
    assert _battery_sensor_id(hass, "TheOverSwitchBat") is None

    entity.remove_thermostat()
