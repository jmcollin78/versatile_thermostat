# pylint: disable=missing-function-docstring, missing-module-docstring, protected-access

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.versatile_thermostat.underlyings import UnderlyingSwitch, UnderlyingClimate, UnderlyingValve, UnderlyingValveRegulation
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_HEAT, VThermHvacMode_FAN_ONLY, VThermHvacMode_COOL, VThermHvacMode_AUTO


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hvac_mode, last_state, expect_off_call",
    [
        (VThermHvacMode_OFF, STATE_ON, True),
        (VThermHvacMode_OFF, STATE_OFF, False),
        (VThermHvacMode_HEAT, STATE_OFF, False),
        (VThermHvacMode_HEAT, STATE_ON, False),
        (VThermHvacMode_OFF, None, False),
        (VThermHvacMode_FAN_ONLY, STATE_UNAVAILABLE, False),
        (VThermHvacMode_OFF, STATE_UNKNOWN, False),
    ],
)
async def test_check_initial_state_underlying_switch(hass, hvac_mode, last_state, expect_off_call):
    """Test check_initial_state behavior for UnderlyingSwitch.

    - when thermostat HVAC mode is OFF and underlying is ON, the switch should be turned off
    - when HVAC mode is HEAT and underlying is OFF, no immediate turn_on is invoked but hvac_mode should be set
    """

    # Mock hass with async services call
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    # Minimal thermostat mock
    thermostat = MagicMock()
    thermostat.vtherm_hvac_mode = hvac_mode
    thermostat.now = None
    thermostat.is_inversed = False
    # power_manager used by turn_on/turn_off - provide safe mocks
    power_manager = MagicMock()
    power_manager.add_power_consumption_to_central_power_manager = MagicMock()
    power_manager.sub_power_consumption_to_central_power_manager = MagicMock()
    power_manager.check_power_available = AsyncMock(return_value=(True, None))
    thermostat.power_manager = power_manager

    # Instantiate the UnderlyingSwitch
    u = UnderlyingSwitch(hass=hass, thermostat=thermostat, switch_entity_id="switch.test", initial_delay_sec=0, keep_alive_sec=0.1)

    # Replace set_hvac_mode with a mock to assert it is invoked by check_initial_state
    u.turn_off = AsyncMock()

    # Ensure no previous state
    assert u._last_known_underlying_state is None
    assert u.state_manager.is_all_states_initialized is True

    u.startup()
    # because hass is a MagicMock, the switch.test will have an initial state
    assert u.state_manager.is_all_states_initialized is False

    # Generate an fake new state event
    if last_state is not None:
        hass.states.async_set("switch.test", last_state)
        await hass.async_block_till_done()

    state_is_defined = last_state not in [None, STATE_UNAVAILABLE, STATE_UNKNOWN]
    if state_is_defined:
        # Now the state manager should be initialized
        assert u.state_manager.is_all_states_initialized is True
    else:
        # still not initialized
        assert u.state_manager.is_all_states_initialized is False

    if last_state is None:
        # no state provided -> no initial check should be done
        assert u._last_known_underlying_state is None
        assert u.turn_off.await_count == 0
    else:
        # state provided -> check_initial_state should try to set HVAC mode
        assert u._last_known_underlying_state is not None
        # verify the stored state matches the passed state
        assert u._last_known_underlying_state.state == last_state
        if expect_off_call:
            assert u.turn_off.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hvac_mode, percent_open, last_state, min_open, max_open, expect_percent_open_call",
    [
        (VThermHvacMode_OFF, 0, "50", 0, 100, True),
        (VThermHvacMode_OFF, None, "50", 20, 100, True),
        (VThermHvacMode_OFF, 5, "0", 10, 100, False),
        (VThermHvacMode_HEAT, 50, "0", 10, 100, False),
        (VThermHvacMode_HEAT, 15, "0", 20, 100, False),
        (VThermHvacMode_OFF, None, None, 0, 100, False),
        (VThermHvacMode_HEAT, 10, STATE_UNAVAILABLE, 0, 100, False),
        (VThermHvacMode_AUTO, 20, STATE_UNKNOWN, 0, 100, False),
    ],
)
async def test_check_initial_state_underlying_valve(hass, hvac_mode, percent_open, last_state, min_open, max_open, expect_percent_open_call):
    """Test check_initial_state behavior for UnderlyingValve.

    """

    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    thermostat = MagicMock()
    thermostat.hvac_mode = hvac_mode
    thermostat.vtherm_hvac_mode = hvac_mode
    thermostat.valve_open_percent = 35 if hvac_mode == VThermHvacMode_HEAT else 0
    thermostat.now = None

    u = UnderlyingValve(hass=hass, thermostat=thermostat, valve_entity_id="number.valve")
    # Mock send_percent_open and set_hvac_mode
    u.send_percent_open = AsyncMock()

    # Ensure initial percent is None
    assert u._percent_open is None
    u._percent_open = percent_open

    # Generate an fake new state event
    if last_state is not None:
        hass.states.async_set("number.valve", last_state, attributes={ "min": min_open, "max": max_open })
        await hass.async_block_till_done()

    # startup after init this time
    u.startup()
    state_is_defined = last_state not in [None, STATE_UNAVAILABLE, STATE_UNKNOWN]
    if state_is_defined:
        # Now the state manager should be initialized
        assert u.state_manager.is_all_states_initialized is True
    else:
        # still not initialized
        assert u.state_manager.is_all_states_initialized is False

    if last_state is None:
        assert u._last_known_underlying_state is None
        assert u.send_percent_open.await_count == 0
    else:
        assert u._last_known_underlying_state.state == last_state
        if expect_percent_open_call:
            assert u.send_percent_open.await_count == 1
            assert u.send_percent_open.await_args.kwargs.get("fixed_value") == min_open

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hvac_mode, last_state, expect_hvac_call",
    [
        (VThermHvacMode_OFF, VThermHvacMode_HEAT, True),
        (VThermHvacMode_OFF, VThermHvacMode_OFF, False),
        (VThermHvacMode_HEAT, VThermHvacMode_OFF, True),
        (VThermHvacMode_COOL, VThermHvacMode_HEAT, False),
        (VThermHvacMode_OFF, None, False),
        (VThermHvacMode_FAN_ONLY, STATE_UNAVAILABLE, False),
        (VThermHvacMode_COOL, STATE_UNKNOWN, False),
    ],
)
async def test_check_initial_state_underlying_climate(hass, hvac_mode, last_state, expect_hvac_call):
    """Test check_initial_state behavior for UnderlyingClimate.

    - when thermostat HVAC mode is OFF and underlying is HEAT, the climate should be turned off
    - when HVAC mode is HEAT and underlying is OFF, the climate should be turned on
    - when no last_state is provided, no action is taken
    """

    # Mock hass with async services call
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    # Minimal thermostat mock
    thermostat = MagicMock()
    thermostat.vtherm_hvac_mode = hvac_mode
    thermostat.now = None
    # power_manager used by turn_on/turn_off - provide safe mocks
    power_manager = MagicMock()
    power_manager.add_power_consumption_to_central_power_manager = MagicMock()
    power_manager.sub_power_consumption_to_central_power_manager = MagicMock()
    power_manager.check_power_available = AsyncMock(return_value=(True, None))
    thermostat.power_manager = power_manager

    # Instantiate the UnderlyingClimate
    u = UnderlyingClimate(hass=hass, thermostat=thermostat, climate_entity_id="climate.test")
    # Replace set_hvac_mode with a mock to assert it is invoked by check_initial_state
    u.set_hvac_mode = AsyncMock()

    # Ensure no previous state
    assert u._last_known_underlying_state is None

    u.startup()

    if last_state is not None:
        hass.states.async_set("climate.test", last_state)
        await hass.async_block_till_done()

    u._hvac_mode = hvac_mode

    state_is_defined = last_state not in [None, STATE_UNAVAILABLE, STATE_UNKNOWN]
    if state_is_defined:
        # Now the state manager should be initialized
        assert u.state_manager.is_all_states_initialized is True
    else:
        # still not initialized
        assert u.state_manager.is_all_states_initialized is False

    if last_state is None:
        # no state provided -> no initial check should be done
        assert u._last_known_underlying_state is None
        assert u.set_hvac_mode.await_count == 0
    else:
        # state provided -> check_initial_state should try to set HVAC mode
        assert u._last_known_underlying_state is not None
        # verify the stored state matches the passed state
        assert u._last_known_underlying_state.state == last_state
        if expect_hvac_call:
            assert u.set_hvac_mode.await_count == 1
            u.set_hvac_mode.assert_awaited_once_with(thermostat.vtherm_hvac_mode)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hvac_mode, is_sleeping, last_state, open_percent, current_valve_opening, expect_percent_open_call",
    [
        (VThermHvacMode_OFF, False, VThermHvacMode_HEAT, 0, 20, True),
        (VThermHvacMode_OFF, False, VThermHvacMode_OFF, 0, 0, False),
        (VThermHvacMode_HEAT, False, VThermHvacMode_OFF, 0, 0, True),
        (VThermHvacMode_HEAT, False, VThermHvacMode_HEAT, 0, 20, False),
        (VThermHvacMode_OFF, False, None, None, None, False),
    ],
)
async def test_check_initial_state_underlying_climate_valve(hass, hvac_mode, is_sleeping, last_state, open_percent, current_valve_opening, expect_percent_open_call):
    """Test check_initial_state behavior for UnderlyingClimate.

    - when thermostat HVAC mode is OFF and underlying is HEAT, the climate should be turned off (ie valve set to min_open)
    - when HVAC mode is HEAT and underlying is OFF, the climate should be turned on
    - when no last_state is provided, no action is taken
    """

    # Mock hass with async services call
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    # Minimal thermostat mock
    thermostat = MagicMock()
    thermostat.vtherm_hvac_mode = hvac_mode
    thermostat.valve_open_percent = 35 if hvac_mode == VThermHvacMode_HEAT else 0
    thermostat.is_sleeping = is_sleeping
    thermostat.now = None
    thermostat.init_underlyings_completed = AsyncMock()
    thermostat.underlying_changed = AsyncMock()

    # power_manager used by turn_on/turn_off - provide safe mocks
    power_manager = MagicMock()
    power_manager.add_power_consumption_to_central_power_manager = MagicMock()
    power_manager.sub_power_consumption_to_central_power_manager = MagicMock()
    power_manager.check_power_available = AsyncMock(return_value=(True, None))
    thermostat.power_manager = power_manager

    # underlying climate
    under_climate = UnderlyingClimate(hass=hass, thermostat=thermostat, climate_entity_id="climate.test")
    under_climate._hvac_mode = VThermHvacMode_OFF
    under_climate.set_hvac_mode = AsyncMock()
    under_climate.check_initial_state = AsyncMock()

    # Instantiate the UnderlyingClimateValve
    u = UnderlyingValveRegulation(hass=hass, thermostat=thermostat, climate_underlying=under_climate, opening_degree_entity_id="number.opening",
        closing_degree_entity_id="number.closing",
        min_opening_degree=13,
        max_opening_degree=93,
        max_closing_degree=10,
        opening_threshold=7)

    # Ensure no previous state
    assert u._last_known_underlying_state is None

    u._hvac_mode = hvac_mode
    u._percent_open = open_percent

    # Replace set_hvac_mode with a mock to assert it is invoked by check_initial_state
    u.set_hvac_mode = AsyncMock()

    # Mock send_percent_open and set_hvac_mode
    u.send_percent_open = AsyncMock()

    # Init opening state
    if last_state is not None:
        hass.states.async_set("number.opening", current_valve_opening, attributes={ "min": 10, "max": 93 })
        await hass.async_block_till_done()

    # startup after init this time
    u.startup()
    assert u.state_manager.is_all_states_initialized is False  # closing degree is missing

    # Init closing state
    if last_state is not None:
        hass.states.async_set("number.closing", current_valve_opening, attributes={ "min": 0, "max": 100 })
        await hass.async_block_till_done()

        assert u.state_manager.is_all_states_initialized is True  # this time all states are initialized

    under_climate.startup()
    assert under_climate.state_manager.is_all_states_initialized is False  # climate state is missing
    if last_state is not None:
        # provide also the climate state
        hass.states.async_set("climate.test", last_state)
        await hass.async_block_till_done()

    state_is_defined = last_state not in [None, STATE_UNAVAILABLE, STATE_UNKNOWN]
    if state_is_defined:
        # Now the state manager should be initialized
        assert under_climate.state_manager.is_all_states_initialized is True
    else:
        # still not initialized
        assert under_climate.state_manager.is_all_states_initialized is False

    if last_state is None:
        # no state provided -> no initial check should be done
        assert u._last_known_underlying_state is None
        assert u.set_hvac_mode.await_count == 0
        assert under_climate.check_initial_state.await_count == 0
        assert under_climate.set_hvac_mode.await_count == 0
    else:
        # state provided -> check_initial_state should try to set HVAC mode
        assert u._last_known_underlying_state is not None
        # verify the stored state matches the passed state
        assert u._last_known_underlying_state.state == str(current_valve_opening)
        if expect_percent_open_call:
            # not called because thermostat is a MagicMock
            # assert under_climate.set_hvac_mode.await_count == 1
            # under_climate.set_hvac_mode.assert_awaited_once_with(thermostat.vtherm_hvac_mode)

            assert u.send_percent_open.await_count == 1
            # 7 is opening_threshold
            expected_percent = 7 if hvac_mode == VThermHvacMode_OFF else thermostat.valve_open_percent
            assert u._percent_open == expected_percent

        assert under_climate.check_initial_state.await_count == 1
