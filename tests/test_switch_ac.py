""" Test the normal start of a Switch AC Thermostat """
from unittest.mock import patch, call
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACAction
from homeassistant.config_entries import ConfigEntryState

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN, HVACMode

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset, VThermPresetWithAC, VThermPresetWithAway, VThermPresetWithACAway

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_switch_ac_full_start(
    hass: HomeAssistant, skip_hass_states_is_state
):  # pylint: disable=unused-argument
    """Test the normal full start of a thermostat in thermostat_over_switch type"""

    temps = {
        VThermPreset.FROST: 7,
        VThermPreset.ECO: 17,
        VThermPreset.COMFORT: 19,
        VThermPreset.BOOST: 20,
        VThermPresetWithAC.ECO: 25,
        VThermPresetWithAC.COMFORT: 23,
        VThermPresetWithAC.BOOST: 21,
        # VThermPresetWithAC.FROST: 7,
        VThermPresetWithAway.ECO: 16,
        VThermPresetWithAway.COMFORT: 17,
        VThermPresetWithAway.BOOST: 18,
        VThermPresetWithAway.FROST: 7,
        VThermPresetWithACAway.ECO: 27,
        VThermPresetWithACAway.COMFORT: 26,
        VThermPresetWithACAway.BOOST: 25,
        # VThermPresetWithACAway.FROST: 7,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchACMockName",
        unique_id="uniqueId",
        data=FULL_SWITCH_AC_CONFIG,
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        def find_my_entity(entity_id) -> ClimateEntity:
            """Find my new entity"""
            component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
            for entity in component.entities:
                if entity.entity_id == entity_id:
                    return entity

        # The name is in the CONF and not the title of the entry
        entity: BaseThermostat = find_my_entity("climate.theoverswitchmockname")

        assert entity
        assert isinstance(entity, ThermostatOverSwitch)

        # Initialise the preset temp
        await set_all_climate_preset_temp(hass, entity, temps, "theoverswitchmockname")

        assert entity.name == "TheOverSwitchMockName"
        assert entity.is_over_climate is False  # pylint: disable=protected-access
        assert entity.ac_mode is True
        assert entity.hvac_action is HVACAction.OFF
        assert entity.hvac_mode is HVACMode.OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.hvac_modes == [VThermHvacMode_HEAT, VThermHvacMode_COOL, VThermHvacMode_OFF]
        assert entity.target_temperature == entity.max_temp
        assert entity.preset_modes == [
            VThermPreset.NONE,
            # VThermPreset.FROST, No frost in AC Mode
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
            VThermPreset.ACTIVITY,
        ]
        assert entity.preset_mode is VThermPreset.NONE
        assert entity.safety_manager.is_safety_detected is False
        assert entity.window_state is STATE_UNKNOWN
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN
        assert entity._prop_algorithm is not None  # pylint: disable=protected-access

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2

        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": VThermHvacMode_OFF},
                ),
            ]
        )

        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(VThermHvacMode_COOL)
        assert entity.vtherm_hvac_mode is VThermHvacMode_COOL

        event_timestamp = now - timedelta(minutes=4)
        await send_presence_change_event(entity, True, False, event_timestamp)
        assert entity.presence_state == STATE_ON  # pylint: disable=protected-access

        await entity.async_set_hvac_mode(VThermHvacMode_COOL)
        assert entity.vtherm_hvac_mode is VThermHvacMode_COOL

        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.vtherm_preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 23

        # switch to Eco
        await entity.async_set_preset_mode(VThermPreset.ECO)
        assert entity.vtherm_preset_mode == VThermPreset.ECO
        assert entity.target_temperature == 25

        # Unset the presence
        event_timestamp = now - timedelta(minutes=3)
        await send_presence_change_event(entity, False, True, event_timestamp)
        await wait_for_local_condition(lambda: entity.presence_state == STATE_OFF)
        assert entity.presence_state == STATE_OFF  # pylint: disable=protected-access
        assert entity.target_temperature == 27  # eco_ac_away

        # Open a window
        with patch("homeassistant.helpers.condition.state", return_value=True):
            event_timestamp = now - timedelta(minutes=2)
            try_condition = await send_window_change_event(
                entity, True, False, event_timestamp
            )

            # Confirme the window event
            await try_condition(None)

            await wait_for_local_condition(lambda: entity.vtherm_hvac_mode == VThermHvacMode_OFF)
            assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
            assert entity.hvac_action is HVACAction.OFF
            assert entity.target_temperature == 27  # eco_ac_away (no change)

        # Close a window
        with patch("homeassistant.helpers.condition.state", return_value=True):
            event_timestamp = now - timedelta(minutes=2)
            try_condition = await send_window_change_event(
                entity, False, True, event_timestamp
            )

            # Confirme the window event
            await try_condition(None)

            assert entity.vtherm_hvac_mode is VThermHvacMode_COOL
            assert (
                entity.hvac_action is HVACAction.OFF
                or entity.hvac_action is HVACAction.IDLE
            )
            assert entity.target_temperature == 27  # eco_ac_away (no change)

        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

        # switch to comfort
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 26  # comfort_ac_away

        # switch to Eco
        await entity.async_set_preset_mode(VThermPreset.ECO)
        assert entity.preset_mode == VThermPreset.ECO
        assert entity.target_temperature == 27  # eco ac away

        # switch to boost
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 25  # boost_ac_away
