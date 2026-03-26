# pylint: disable=unused-argument, line-too-long, protected-access
"""Tests for the allow_manual_override feature on ThermostatOverSwitch.

Use cases covered:
  UC1: VTherm ON + switch turned OFF manually while in ON cycle → VTherm turns OFF.
  UC2: VTherm ON + switch turned OFF manually → VTherm does NOT turn it back ON.
  UC3: VTherm OFF + switch turned ON manually → VTherm stays OFF (no interference).
  UC4: VTherm ON but idle (off-part of cycle) + switch turned ON manually → VTherm
       turns OFF and does not turn the switch off during the transition.
  UC5: Same events when allow_manual_override=False → default behaviour unchanged.
  UC_WIN: VTherm OFF but device active (manual override) + window opens
          → configured window action is applied.
"""
import asyncio
import logging
from unittest.mock import patch, PropertyMock
from datetime import datetime, timedelta

from homeassistant.core import Event, State
from homeassistant.const import STATE_ON, STATE_OFF, EVENT_STATE_CHANGED

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_switch import ThermostatOverSwitch
from custom_components.versatile_thermostat.underlyings import UnderlyingSwitch

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Minimal thermostat configuration for manual-override tests
# ---------------------------------------------------------------------------

_BASE_CONFIG = {
    CONF_NAME: "TheOverSwitchMockName",
    CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
    CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
    CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
    CONF_CYCLE_MIN: 5,
    CONF_TEMP_MIN: 15,
    CONF_TEMP_MAX: 30,
    "eco_temp": 17,
    "comfort_temp": 18,
    "boost_temp": 21,
    CONF_USE_WINDOW_FEATURE: False,
    CONF_USE_MOTION_FEATURE: False,
    CONF_USE_POWER_FEATURE: False,
    CONF_USE_PRESENCE_FEATURE: False,
    CONF_UNDERLYING_LIST: ["switch.mock_switch"],
    CONF_HEATER_KEEP_ALIVE: 0,
    CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
    CONF_AC_MODE: False,
    CONF_INVERSE_SWITCH: False,
    CONF_TPI_COEF_INT: 0.3,
    CONF_TPI_COEF_EXT: 0.01,
    CONF_MINIMAL_ACTIVATION_DELAY: 0,
    CONF_MINIMAL_DEACTIVATION_DELAY: 0,
    CONF_SAFETY_DELAY_MIN: 5,
    CONF_SAFETY_MIN_ON_PERCENT: 0.3,
}

_BASE_CONFIG_WITH_WINDOW = {
    **_BASE_CONFIG,
    CONF_USE_WINDOW_FEATURE: True,
    CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
    CONF_WINDOW_DELAY: 0,
    CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
}


# ---------------------------------------------------------------------------
# Helper: fire a switch state-change event directly at _async_switch_changed
# ---------------------------------------------------------------------------

def _fire_switch_event(
    entity: ThermostatOverSwitch,
    switch_entity_id: str,
    new_state_str: str,
    old_state_str: str,
):
    """Build and dispatch an EVENT_STATE_CHANGED event for a switch."""
    event = Event(
        EVENT_STATE_CHANGED,
        {
            "entity_id": switch_entity_id,
            "new_state": State(switch_entity_id, new_state_str),
            "old_state": State(switch_entity_id, old_state_str),
        },
    )
    entity._async_switch_changed(event)


# ===========================================================================
# UC1 – Switch turned OFF while VTherm is ON and in the ON part of the cycle
# ===========================================================================

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_uc1_switch_off_during_on_cycle(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    fake_underlying_switch: MockSwitch,
):
    """UC1: when VTherm is ON and the underlying is in the heating (ON) part of
    its cycle, manually turning the switch OFF should set VTherm to OFF."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={**_BASE_CONFIG, CONF_ALLOW_MANUAL_OVERRIDE: True},
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    assert entity._allow_manual_override is True

    # Start in HEAT mode
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT

        event_timestamp = datetime.now() - timedelta(minutes=4)
        await send_temperature_change_event(entity, 15, event_timestamp)

    # Simulate the underlying being in the ON part of the cycle
    underlying: UnderlyingSwitch = entity._underlyings[0]
    underlying._is_on_part_running = True

    # Now fire a manual switch-off event
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_turn_off:
        _fire_switch_event(entity, "switch.mock_switch", STATE_OFF, STATE_ON)
        await hass.async_block_till_done()

        # VTherm must have been switched to OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF, (
            "UC1: VTherm should have turned OFF after manual switch-off during ON cycle"
        )
        mock_send_event.assert_any_call(
            EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_OFF}
        )

    entity.remove_thermostat()


# ===========================================================================
# UC2 – VTherm turned OFF by UC1: the switch must NOT be turned back ON
# ===========================================================================

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_uc2_vtherm_stays_off(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    fake_underlying_switch: MockSwitch,
):
    """UC2: after VTherm goes OFF because of a manual switch-off (UC1), the
    switch must not be turned off again (it is already off — the user did it)."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={**_BASE_CONFIG, CONF_ALLOW_MANUAL_OVERRIDE: True},
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity._allow_manual_override is True

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        await send_temperature_change_event(entity, 15, datetime.now() - timedelta(minutes=4))

    underlying: UnderlyingSwitch = entity._underlyings[0]
    underlying._is_on_part_running = True

    # Trigger the manual OFF (UC1 scenario)
    _fire_switch_event(entity, "switch.mock_switch", STATE_OFF, STATE_ON)
    await hass.async_block_till_done()

    assert entity.vtherm_hvac_mode is VThermHvacMode_OFF

    # Now ensure VTherm does NOT send a turn_off to the switch (it is already off)
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_turn_off, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=False,
    ):
        # Trigger async_control_heating while VTherm is OFF
        await entity.async_control_heating(force=True)
        await hass.async_block_till_done()

        # The switch is already off — VTherm must not try to turn it off again
        assert mock_turn_off.call_count == 0, (
            "UC2: VTherm must not send turn_off to a switch the user already turned off"
        )

    entity.remove_thermostat()


# ===========================================================================
# UC3 – VTherm OFF: manually turning the switch ON must not be overridden
# ===========================================================================

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_uc3_vtherm_off_switch_on_no_interference(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    fake_underlying_switch: MockSwitch,
):
    """UC3: when VTherm is OFF and the user turns the switch ON manually, VTherm
    must stay OFF and must not turn the switch back off."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={**_BASE_CONFIG, CONF_ALLOW_MANUAL_OVERRIDE: True},
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity._allow_manual_override is True

    # Ensure VTherm is OFF
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_OFF)
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF

    # Manual switch ON while VTherm is OFF — the check in _async_switch_changed
    # only triggers when vtherm_hvac_mode != OFF, so this must pass silently.
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_turn_off:
        _fire_switch_event(entity, "switch.mock_switch", STATE_ON, STATE_OFF)
        await hass.async_block_till_done()

        # VTherm must remain OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF, (
            "UC3: VTherm must stay OFF when user turns switch ON while VTherm is OFF"
        )
        # VTherm must not try to turn the switch back off
        assert mock_turn_off.call_count == 0, (
            "UC3: VTherm must not turn the switch off when VTherm itself is OFF"
        )

    entity.remove_thermostat()


# ===========================================================================
# UC4 – VTherm ON but idle: switch turned ON manually → VTherm turns OFF,
#        switch remains ON (skip_turn_off guard is honoured)
# ===========================================================================

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_uc4_vtherm_idle_switch_on_manual_takeover(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    fake_underlying_switch: MockSwitch,
):
    """UC4: VTherm is ON but currently in the OFF (idle) part of the cycle.
    The user turns the AC ON with the remote.  VTherm should turn itself OFF
    without turning the switch back off (manual takeover)."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={**_BASE_CONFIG, CONF_ALLOW_MANUAL_OVERRIDE: True},
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity._allow_manual_override is True

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        await send_temperature_change_event(entity, 15, datetime.now() - timedelta(minutes=4))

    # Underlying is in the idle (OFF) part of its cycle
    underlying: UnderlyingSwitch = entity._underlyings[0]
    underlying._is_on_part_running = False

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_turn_off:
        _fire_switch_event(entity, "switch.mock_switch", STATE_ON, STATE_OFF)
        await hass.async_block_till_done()

        # VTherm must have turned itself OFF (manual takeover)
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF, (
            "UC4: VTherm should turn OFF when switch is turned ON manually while idle"
        )
        mock_send_event.assert_any_call(
            EventType.HVAC_MODE_EVENT, {"hvac_mode": VThermHvacMode_OFF}
        )

        # During the OFF transition, the switch must NOT be turned off
        # (_skip_turn_off_on_next_hvac_off must have prevented it)
        assert mock_turn_off.call_count == 0, (
            "UC4: VTherm must not turn the switch off during takeover transition "
            "(the user just turned it on manually)"
        )

    entity.remove_thermostat()


# ===========================================================================
# UC5 – Feature disabled: events should produce the default behaviour
# ===========================================================================

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_uc5_feature_disabled_no_effect(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    fake_underlying_switch: MockSwitch,
):
    """UC5: with allow_manual_override=False the switch-changed handler must
    follow the standard path (no automatic hvac_mode change)."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={**_BASE_CONFIG, CONF_ALLOW_MANUAL_OVERRIDE: False},
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity._allow_manual_override is False

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        await send_temperature_change_event(entity, 15, datetime.now() - timedelta(minutes=4))

    underlying: UnderlyingSwitch = entity._underlyings[0]
    underlying._is_on_part_running = True

    # The same event that would trigger UC1 must not change the hvac_mode
    with patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.async_set_hvac_mode"
    ) as mock_set_hvac:
        _fire_switch_event(entity, "switch.mock_switch", STATE_OFF, STATE_ON)
        await hass.async_block_till_done()

        assert mock_set_hvac.call_count == 0, (
            "UC5: async_set_hvac_mode must not be called when feature is disabled"
        )
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT, (
            "UC5: VTherm must stay in HEAT mode when allow_manual_override is False"
        )

    entity.remove_thermostat()


# ===========================================================================
# UC_WIN – Window opens while VTherm is OFF but device is active (manual override)
# ===========================================================================

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_window_applies_action_when_vtherm_off(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    fake_underlying_switch: MockSwitch,
):
    """UC_WIN: when VTherm is OFF but the underlying device is active due to a
    manual override, opening the window must still apply the configured window
    action (turn off the device in this case)."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            **_BASE_CONFIG_WITH_WINDOW,
            CONF_ALLOW_MANUAL_OVERRIDE: True,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity._allow_manual_override is True
    assert entity.window_manager is not None

    # VTherm is OFF
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"
    ):
        await entity.async_set_hvac_mode(VThermHvacMode_OFF)
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF

    # Device is active (user turned the AC/heater on manually)
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ), patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_turn_off, patch(
        "homeassistant.helpers.condition.state", return_value=True
    ):
        try_function = await send_window_change_event(
            entity, True, False, datetime.now(), sleep=False
        )
        if try_function:
            await try_function(None)

        await hass.async_block_till_done()
        await asyncio.sleep(0.1)

        # The window action (CONF_WINDOW_TURN_OFF) must have turned the device off
        assert mock_turn_off.call_count >= 1, (
            "UC_WIN: window action must turn off the device even when VTherm is OFF "
            "but the device is active due to manual override"
        )

    entity.remove_thermostat()
