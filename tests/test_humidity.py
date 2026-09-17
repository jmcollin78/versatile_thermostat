# pylint: disable=protected-access
"""Tests for external humidity resolution and the humidity feature manager."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EVENT_STATE_CHANGED, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, State

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.const import (
    CONF_HUMIDITY_SENSOR,
    CONF_USE_HUMIDITY_FEATURE,
)
from custom_components.versatile_thermostat.feature_humidity_manager import (
    FeatureHumidityManager,
)
from custom_components.versatile_thermostat.humidity import (
    find_humidity_sensor_candidates,
)
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)


class FakeThermostat:
    """Minimal thermostat contract needed by the humidity manager."""

    name = "Fake thermostat"

    def __init__(self, temperature_sensor_entity_id="sensor.temperature"):
        self._temp_sensor_entity_id = temperature_sensor_entity_id
        self.update_custom_attributes = Mock()
        self.async_write_ha_state = Mock()


@pytest.mark.parametrize("thermostat_type", ["over_switch", "over_valve", "over_climate"])
async def test_explicit_humidity_updates_and_invalid_states(hass, thermostat_type):
    """Every VTherm type exposes explicit humidity and propagates invalid states."""

    thermostat = FakeThermostat()
    thermostat.name = thermostat_type
    manager = FeatureHumidityManager(thermostat, hass)
    manager.post_init(
        {
            CONF_USE_HUMIDITY_FEATURE: True,
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
        }
    )

    hass.states.async_set("sensor.humidity", "42.5")
    await manager.start_listening()
    assert manager.current_humidity == 42.5

    assert manager.humidity_source == "explicit"
    assert manager.is_configured is True
    assert manager.is_detected is True

    for invalid_state in (STATE_UNAVAILABLE, STATE_UNKNOWN, "NaN", "Inf", "invalid"):
        hass.states.async_set("sensor.humidity", invalid_state)
        await manager.refresh_state()
        assert manager.current_humidity is None

    hass.states.async_set("sensor.humidity", "47")
    await manager.refresh_state()
    assert manager.current_humidity == 47


async def test_humidity_manager_auto_detects_first_candidate(hass):
    """The first auto-detected candidate is selected and read at startup."""
    thermostat = FakeThermostat()

    manager = FeatureHumidityManager(thermostat, hass)
    manager.post_init({})
    hass.states.async_set("sensor.humidity_first", "48")

    with patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.find_humidity_sensor_candidates",
        return_value=["sensor.humidity_first", "sensor.humidity_second"],
    ):
        await manager.start_listening()

    assert manager.humidity_source == "auto"
    assert manager.humidity_sensor_entity_id == "sensor.humidity_first"
    assert manager.current_humidity == 48


async def test_humidity_manager_explicit_sensor_skips_auto_detection(hass):
    """An explicitly configured sensor always takes precedence over detection."""
    thermostat = FakeThermostat()
    manager = FeatureHumidityManager(thermostat, hass)
    manager.post_init(
        {
            CONF_USE_HUMIDITY_FEATURE: True,
            CONF_HUMIDITY_SENSOR: "sensor.explicit_humidity",
        }
    )
    hass.states.async_set("sensor.explicit_humidity", "44")

    with patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.find_humidity_sensor_candidates"
    ) as find_candidates:
        await manager.start_listening()

    find_candidates.assert_not_called()
    assert manager.humidity_source == "explicit"
    assert manager.humidity_sensor_entity_id == "sensor.explicit_humidity"
    assert manager.current_humidity == 44


async def test_humidity_manager_disabled_skips_detection_and_sensor(hass):
    """An explicit disable takes precedence over configured and detected sensors."""
    thermostat = FakeThermostat()
    manager = FeatureHumidityManager(thermostat, hass)
    manager.post_init(
        {
            CONF_USE_HUMIDITY_FEATURE: False,
            CONF_HUMIDITY_SENSOR: "sensor.explicit_humidity",
        }
    )

    with patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.find_humidity_sensor_candidates"
    ) as find_candidates, patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.async_track_state_change_event"
    ) as track:
        await manager.start_listening()

    find_candidates.assert_not_called()
    track.assert_not_called()
    assert manager.humidity_source == "none"
    assert manager.current_humidity is None


async def test_humidity_manager_callback_publishes_valid_and_invalid_values(hass):
    """The listener publishes changes and clears humidity on an invalid state."""
    thermostat = FakeThermostat()
    manager = FeatureHumidityManager(thermostat, hass)
    manager.post_init({CONF_HUMIDITY_SENSOR: "sensor.humidity"})

    await manager.start_listening()
    await manager._humidity_sensor_changed(
        Event(
            EVENT_STATE_CHANGED,
            {"new_state": State("sensor.humidity", "46")},
        )
    )
    assert manager.current_humidity == 46

    await manager._humidity_sensor_changed(
        Event(
            EVENT_STATE_CHANGED,
            {"new_state": State("sensor.humidity", STATE_UNAVAILABLE)},
        )
    )
    assert manager.current_humidity is None
    assert thermostat.update_custom_attributes.call_count == 2
    assert thermostat.async_write_ha_state.call_count == 2


async def test_humidity_manager_retry_detects_sensor_when_registry_is_ready(hass):
    """A deferred retry installs and reads a sensor detected after startup."""
    thermostat = FakeThermostat()
    manager = FeatureHumidityManager(thermostat, hass)
    manager.post_init({})
    hass.states.async_set("sensor.detected_humidity", "53")
    scheduled_callbacks = []

    def schedule_retry(_hass, _delay, callback):
        scheduled_callbacks.append(callback)
        return Mock()

    with patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.find_humidity_sensor_candidates",
        side_effect=[[], ["sensor.detected_humidity"]],
    ), patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.async_call_later",
        side_effect=schedule_retry,
    ):
        await manager.start_listening()
        await scheduled_callbacks[0](None)

    assert manager.humidity_source == "auto"
    assert manager.humidity_sensor_entity_id == "sensor.detected_humidity"
    assert manager.current_humidity == 53
    assert manager._humidity_retry_count == 1


async def test_humidity_manager_does_not_duplicate_listener(hass):
    """Repeated startup with the same source keeps the existing listener."""
    thermostat = FakeThermostat()

    manager = FeatureHumidityManager(thermostat, hass)
    manager.post_init({CONF_HUMIDITY_SENSOR: "sensor.humidity"})
    listener = Mock()

    with patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.async_track_state_change_event",
        return_value=listener,
    ) as track:
        await manager.start_listening()
        await manager.start_listening()

    track.assert_called_once()
    assert len(manager._active_listener) == 1


async def test_humidity_manager_retries_at_most_three_times_and_cleans_up(hass):
    """No-source discovery retries are bounded and cancelled by normal cleanup."""
    thermostat = FakeThermostat()

    manager = FeatureHumidityManager(thermostat, hass)
    manager.post_init({})
    scheduled_callbacks = []

    canceller = Mock()

    def schedule_retry(_hass, _delay, callback):
        scheduled_callbacks.append(callback)
        return canceller

    with patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.find_humidity_sensor_candidates",
        return_value=[],
    ), patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.async_call_later",
        side_effect=schedule_retry,
    ):
        await manager.start_listening()
        while len(scheduled_callbacks) < 3:
            await scheduled_callbacks[-1](None)

    assert len(scheduled_callbacks) == 3
    assert manager._humidity_retry_count == 3
    manager.stop_listening()
    canceller.assert_called_once()
    assert manager._cancel_humidity_retry is None


def test_humidity_manager_is_registered_by_base_thermostat(hass):
    """The manager is part of BaseThermostat's generic lifecycle collection."""
    with patch.object(BaseThermostat, "post_init"):
        thermostat = BaseThermostat(hass, "humidity-test", "Humidity test", {})

    assert isinstance(thermostat._humidity_manager, FeatureHumidityManager)
    assert thermostat._humidity_manager in thermostat._managers


def test_base_thermostat_current_humidity_delegates_to_manager():
    """BaseThermostat has no current-humidity state of its own."""
    thermostat = object.__new__(BaseThermostat)

    thermostat._humidity_manager = SimpleNamespace(current_humidity=41.0)
    assert thermostat.current_humidity == 41.0


def test_thermostat_climate_uses_underlying_only_without_manager_source():
    """Over-climate fallback is used exclusively when no manager source exists."""
    thermostat = object.__new__(ThermostatOverClimate)

    thermostat._humidity_manager = SimpleNamespace(
        humidity_source="none", current_humidity=None
    )
    thermostat.underlying_entity = Mock(
        return_value=SimpleNamespace(current_humidity=51.0)
    )
    assert thermostat.current_humidity == 51.0

    thermostat._humidity_manager = SimpleNamespace(
        humidity_source="explicit", current_humidity=43.0
    )
    assert thermostat.current_humidity == 43.0


def test_auto_detection_returns_no_candidate_without_temperature_registry_entry(hass):
    """Auto-detection safely handles sensors not yet loaded in the registry."""
    registry = SimpleNamespace(async_get=lambda _: None, entities={})

    with patch(
        "custom_components.versatile_thermostat.humidity.er.async_get",
        return_value=registry,
    ):
        assert find_humidity_sensor_candidates(hass, "sensor.temperature") == []


def test_auto_detection_returns_first_registry_humidity_candidate(hass):
    """The first entity-registry humidity candidate is selected deterministically."""
    device_id = "device-id"

    temperature = SimpleNamespace(
        entity_id="sensor.temperature",
        device_id=device_id,
        device_class=None,
    )
    humidity_first = SimpleNamespace(
        entity_id="sensor.humidity_first",
        device_id=device_id,
        device_class=SensorDeviceClass.HUMIDITY,
    )
    humidity_second = SimpleNamespace(
        entity_id="sensor.humidity_second",
        device_id=device_id,
        device_class=SensorDeviceClass.HUMIDITY,
    )
    registry = SimpleNamespace(
        async_get=lambda entity_id: temperature if entity_id == temperature.entity_id else None,
        entities={
            temperature.entity_id: temperature,
            humidity_first.entity_id: humidity_first,
            humidity_second.entity_id: humidity_second,
        },
    )
    with patch(
        "custom_components.versatile_thermostat.humidity.er.async_get",
        return_value=registry,
    ):
        assert find_humidity_sensor_candidates(hass, temperature.entity_id) == [
            humidity_first.entity_id,
            humidity_second.entity_id,
        ]
