# pylint: disable=protected-access, missing-function-docstring, missing-module-docstring

from types import MethodType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.climate import HVACAction
from homeassistant.core import HomeAssistant

from custom_components.versatile_thermostat.thermostat_climate_valve import ThermostatOverClimateValve
from custom_components.versatile_thermostat.underlyings import UnderlyingClimate
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset
from .commons import (
    DOMAIN,
    MockConfigEntry,
    PARTIAL_CLIMATE_NOT_REGULATED_CONFIG,
    create_and_register_mock_climate,
    create_thermostat,
)

ECO_TEMP = 19.0
DIAL_TEMP = 20.5


async def test_adoption_marks_the_dial_setpoint_as_sent(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    temps = {VThermPreset.FROST: 7, VThermPreset.ECO: 16, VThermPreset.COMFORT: 17, VThermPreset.BOOST: 18}
    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="uniqueId", data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG)
    await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, hvac_mode=VThermHvacMode_HEAT, hvac_action=HVACAction.OFF)
    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps)
    under = entity.underlying_entity(0)
    entity.set_follow_underlying_temp_change(True)
    callbacks = []

    def capture_debounce(_hass, _delay, callback):
        callbacks.append(callback)
        return lambda: None

    dial_temperature = entity.target_temperature + 2
    hass.states.async_set(under.entity_id, VThermHvacMode_HEAT, {"temperature": dial_temperature})
    await hass.async_block_till_done()
    entity._on_external_command_received()
    under._last_sent_temperature = None
    with patch("custom_components.versatile_thermostat.thermostat_climate.async_call_later", side_effect=capture_debounce):
        entity._consider_underlying_temperature_candidate(under, dial_temperature)
    assert len(callbacks) == 1

    hass.states.async_set(under.entity_id, VThermHvacMode_HEAT, {"temperature": dial_temperature})
    await callbacks[0](None)

    assert entity._underlying_temperature_status[under.entity_id] == "accepted"
    assert under.last_sent_temperature == dial_temperature
    entity.remove_thermostat()


async def test_valve_sends_the_previous_setpoint_after_adoption():
    under = SimpleNamespace(
        entity_id="climate.trv",
        _last_sent_temperature=ECO_TEMP,
        underlying_target_temperature=DIAL_TEMP,
        set_temperature=AsyncMock(),
    )
    under.mark_temperature_as_sent = MethodType(UnderlyingClimate.mark_temperature_as_sent, under)
    under.mark_temperature_as_sent(DIAL_TEMP)
    under.last_sent_temperature = under._last_sent_temperature
    vtherm = MagicMock()
    vtherm.target_temperature = ECO_TEMP
    vtherm.vtherm_hvac_mode = VThermHvacMode_HEAT
    vtherm._underlyings = [under]
    vtherm._underlyings_valve_regulation = []
    vtherm._attr_max_temp = 30
    vtherm._attr_min_temp = 7

    await ThermostatOverClimateValve._send_regulated_temperature(vtherm, force=True)

    under.set_temperature.assert_awaited_once_with(ECO_TEMP, 30, 7, command_cause=None)
