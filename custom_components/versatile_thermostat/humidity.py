"""Helpers used to resolve an optional humidity sensor."""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


def find_humidity_sensor_candidates(
    hass: HomeAssistant, temperature_sensor_entity_id: str | None
) -> list[str]:
    """Return humidity sensors attached to the temperature sensor device.

    Entity registry insertion order deliberately determines the preferred
    sensor when a device publishes more than one humidity measurement.
    """
    if not temperature_sensor_entity_id:
        return []

    registry = er.async_get(hass)
    temperature_entry = registry.async_get(temperature_sensor_entity_id)
    if temperature_entry is None or temperature_entry.device_id is None:
        return []

    candidates: list[str] = []
    for entry in registry.entities.values():
        if entry.device_id != temperature_entry.device_id:
            continue
        if not entry.entity_id.startswith("sensor."):
            continue
        device_class = entry.device_class
        if device_class is None:
            state = hass.states.get(entry.entity_id)
            device_class = state.attributes.get("device_class") if state else None
        if device_class == SensorDeviceClass.HUMIDITY:
            candidates.append(entry.entity_id)
    return candidates