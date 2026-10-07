# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the restore of a VTherm after a Home Assistant restart """
from homeassistant.core import HomeAssistant, State, CoreState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers import restore_state

from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

from custom_components.versatile_thermostat.thermostat_switch import ThermostatOverSwitch
from custom_components.versatile_thermostat.vtherm_state import VThermState

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_restore_state_when_restore_cache_is_dropped_at_start(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Test the restore when HA drops the restore cache before EVENT_HOMEASSISTANT_STARTED (HA >= 2026.10)"""
    entity_id = "climate.theoverswitchmockname"
    previous_state = VThermState(hvac_mode=VThermHvacMode_HEAT, preset=VThermPreset.COMFORT, target_temperature=19)

    hass.set_state(CoreState.not_running)
    mock_restore_cache(
        hass,
        [
            State(
                entity_id,
                "heat",
                {
                    "current_state": previous_state.to_dict(),
                    "requested_state": previous_state.to_dict(),
                    "preset_mode": str(VThermPreset.COMFORT),
                    "temperature": 19,
                    "window_manager": {"is_window_bypass": True},
                },
            )
        ],
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data=FULL_SWITCH_CONFIG,
    )
    entity = await create_thermostat(hass, entry, entity_id, temps=default_temperatures)
    assert isinstance(entity, ThermostatOverSwitch)
    assert entity.is_ready is False

    restore_state.async_get(hass).last_states.pop(entity_id, None)

    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    await wait_for_local_condition(lambda: entity.is_ready is True)

    assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == default_temperatures["comfort"]
    assert entity.is_window_bypass is True

    entity.remove_thermostat()
