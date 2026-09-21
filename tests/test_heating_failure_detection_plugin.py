"""Tests for the external heating failure detection plugin."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.vtherm_heating_failure_detection import _async_update_options
from custom_components.vtherm_heating_failure_detection.const import (
    CONF_COOLING_PERCENT_THRESHOLD,
    CONF_DELAY_MINUTES,
    CONF_ENABLED,
    CONF_HEATING_PERCENT_THRESHOLD,
    CONF_TEMPERATURE_DELTA,
    DOMAIN,
)
from custom_components.vtherm_heating_failure_detection.manager import (
    HeatingFailureManager,
)
from vtherm_api.const import EventType


class FakeThermostat:
    """Small runtime double for an external feature manager."""

    def __init__(self, now: datetime) -> None:
        self.unique_id = "test-thermostat"
        self.has_prop = True
        self.requested_hvac_mode = "heat"
        self.vtherm_hvac_mode = "heat"
        self.now = now
        self.current_temperature = 18.0
        self.on_percent = 0.95
        self.target_temperature = 20.0
        self.valve_diagnostics = ()
        self.update_custom_attributes = MagicMock()
        self.async_write_ha_state = MagicMock()
        self.send_event = MagicMock()


def _configure_plugin(hass) -> None:
    hass.data[DOMAIN] = {
        "entries": {
            "global": {
                CONF_ENABLED: True,
                CONF_HEATING_PERCENT_THRESHOLD: 0.9,
                CONF_COOLING_PERCENT_THRESHOLD: 0.0,
                CONF_DELAY_MINUTES: 15,
                CONF_TEMPERATURE_DELTA: 0.5,
            }
        }
    }


async def test_detects_heating_failure_and_keeps_event_contract(hass) -> None:
    """A high output with insufficient heat gain starts a heating failure."""
    now = datetime.now()
    thermostat = FakeThermostat(now)
    _configure_plugin(hass)
    manager = HeatingFailureManager(thermostat, hass)
    manager.post_init({})

    await manager.refresh_state()
    thermostat.now = now + timedelta(minutes=16)
    thermostat.current_temperature = 18.2

    assert await manager.refresh_state() is True
    assert manager.is_heating_failure_detected is True
    thermostat.send_event.assert_called_once()
    event_type, payload = thermostat.send_event.call_args.args
    assert event_type is EventType.HEATING_FAILURE_EVENT
    assert payload["type"] == "heating_failure_start"
    assert payload["failure_type"] == "heating"
    assert payload["threshold"] == 0.9
    assert payload["detection_delay_min"] == 15


async def test_template_disable_ends_an_active_failure(hass) -> None:
    """Disabling the template emits the historical failure-end event."""
    now = datetime.now()
    thermostat = FakeThermostat(now)
    _configure_plugin(hass)
    hass.data[DOMAIN]["entries"]["global"]["activation_template"] = "false"
    manager = HeatingFailureManager(thermostat, hass)
    manager.post_init({})
    manager._heating_state = "on"  # pylint: disable=protected-access

    assert await manager.refresh_state() is False
    event_type, payload = thermostat.send_event.call_args.args
    assert event_type is EventType.HEATING_FAILURE_EVENT
    assert payload["type"] == "heating_failure_end"


async def test_options_update_replaces_cached_entry(hass) -> None:
    """Options updates must be visible to managers created after the reload."""
    hass.data[DOMAIN] = {"entries": {"entry-id": {CONF_DELAY_MINUTES: 15}}}
    entry = MagicMock(entry_id="entry-id")
    entry.options = {CONF_DELAY_MINUTES: 20}
    entry.data = {}

    with patch(
        "custom_components.vtherm_heating_failure_detection._reload_thermostats",
        new_callable=AsyncMock,
    ) as reload_thermostats:
        await _async_update_options(hass, entry)

    assert hass.data[DOMAIN]["entries"]["entry-id"] == {CONF_DELAY_MINUTES: 20}
    reload_thermostats.assert_awaited_once_with(hass, entry)