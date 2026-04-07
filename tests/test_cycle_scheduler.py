"""Tests for CycleScheduler."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from homeassistant.core import HomeAssistant

from custom_components.versatile_thermostat.cycle_scheduler import CycleScheduler
from custom_components.versatile_thermostat.underlyings import UnderlyingEntityType
from custom_components.versatile_thermostat.vtherm_hvac_mode import (
    VThermHvacMode_HEAT,
    VThermHvacMode_COOL,
    VThermHvacMode_OFF,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def make_underlying(name="R1", active=False, entity_type=UnderlyingEntityType.SWITCH):
    """Create a mock underlying entity."""
    under = MagicMock()
    under.turn_on = AsyncMock(return_value=True)
    under.turn_off = AsyncMock()
    under.set_valve_open_percent = AsyncMock()
    under.is_device_active = active
    under.min_activation_delay_sec = 0
    under.min_deactivation_delay_sec = 0
    under.entity_type = entity_type
    
    # Mock last_change to return a large elapsed time (e.g. 1000 seconds)
    import datetime
    delta_mock = MagicMock()
    delta_mock.total_seconds.return_value = 1000.0
    now_func_mock = MagicMock()
    now_func_mock.__rsub__.return_value = delta_mock
    under.last_change = now_func_mock

    under._should_be_on = False
    under._on_time_sec = 0
    under._off_time_sec = 0
    under._hvac_mode = None
    under.__str__ = lambda self: name
    return under


def make_thermostat():
    """Create a mock thermostat."""
    t = MagicMock()
    t.incremente_energy = MagicMock()
    t.__str__ = lambda self: "MockThermostat"
    return t


def make_hass():
    """Create a mock HomeAssistant instance."""
    return MagicMock(spec=HomeAssistant)


# ─────────────────────────────────────────────
# Tests for CycleScheduler lifecycle
# ─────────────────────────────────────────────


class TestCycleSchedulerLifecycle:
    """Tests for CycleScheduler start_cycle, cancel_cycle, etc."""

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_start_cycle_single_underlying(self, mock_call_later, freezer):
        """Single underlying: turn_on immediately, schedule turn_off and cycle_end."""
        freezer.move_to("2024-01-01T00:00:00Z")
        mock_cancel = MagicMock()
        mock_call_later.return_value = mock_cancel

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1")
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True)

        # R1 should be turned on immediately (offset=0)
        r1.turn_on.assert_called_once()
        assert r1._should_be_on is True

        # Should have scheduled: turn_off at 120s + cycle_end at 600s
        assert mock_call_later.call_count == 2
        delays = [c[0][1] for c in mock_call_later.call_args_list]
        assert 120 in delays  # turn_off
        assert 600 in delays  # cycle_end

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_start_cycle_two_underlyings(self, mock_call_later, freezer):
        """Two underlyings with 50%: R1 on immediately, R2 scheduled at 300s."""
        freezer.move_to("2024-01-01T00:00:00Z")
        mock_cancel = MagicMock()
        mock_call_later.return_value = mock_cancel

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1")
        r2 = make_underlying("R2")
        scheduler = CycleScheduler(hass, thermostat, [r1, r2], 600)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.5, force=True)

        # R1 immediately on (offset=0)
        r1.turn_on.assert_called_once()
        assert r1._should_be_on is True

        # R2 not turned on immediately (offset=300)
        r2.turn_on.assert_not_called()

        # Scheduled action: R1_off at 300s, master cycle evaluation at 600s
        # Note: R2 turn_on will be evaluated dynamically as time advances.
        assert mock_call_later.call_count == 2

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_hvac_off_turns_off_all(self, mock_call_later):
        """HVAC_OFF: all underlyings turned off, cycle scheduled for re-evaluation."""
        mock_cancel = MagicMock()
        mock_call_later.return_value = mock_cancel

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1", active=True)
        r2 = make_underlying("R2", active=True)
        scheduler = CycleScheduler(hass, thermostat, [r1, r2], 600)

        await scheduler.start_cycle(VThermHvacMode_OFF, 0.0, force=True)

        r1.turn_off.assert_called_once()
        r2.turn_off.assert_called_once()
        assert r1._should_be_on is False
        assert r2._should_be_on is False
        # Only cycle_end scheduled
        assert mock_call_later.call_count == 1

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_zero_on_time_turns_off_all(self, mock_call_later):
        """on_time=0: all underlyings turned off."""
        mock_cancel = MagicMock()
        mock_call_later.return_value = mock_cancel

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1", active=True)
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.0, force=True)

        r1.turn_off.assert_called_once()
        assert r1._should_be_on is False

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_full_power_all_on_immediately(self, mock_call_later):
        """100% power: all underlyings turned on immediately."""
        mock_cancel = MagicMock()
        mock_call_later.return_value = mock_cancel

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1")
        r2 = make_underlying("R2")
        scheduler = CycleScheduler(hass, thermostat, [r1, r2], 600)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 1.0, force=True)

        # Both turned on immediately (offsets = [0, 0])
        r1.turn_on.assert_called_once()
        r2.turn_on.assert_called_once()
        assert r1._should_be_on is True
        assert r2._should_be_on is True
        # Only cycle_end scheduled (no turn_off since end >= cycle_duration)
        assert mock_call_later.call_count == 1

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_cancel_cycle(self, mock_call_later):
        """cancel_cycle cancels all scheduled actions."""
        mock_cancel = MagicMock()
        mock_call_later.return_value = mock_cancel

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1")
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True)
        assert scheduler.is_cycle_running is True

        await scheduler.cancel_cycle()
        assert mock_cancel.call_count == 2  # turn_off + cycle_end
        assert scheduler.is_cycle_running is False

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_no_restart_without_force(self, mock_call_later):
        """Without force=True, a running cycle is not restarted."""
        mock_cancel = MagicMock()
        mock_call_later.return_value = mock_cancel

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1")
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True)
        first_call_count = mock_call_later.call_count

        # Try to start again without force
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.5, force=False)

        # No additional calls - cycle was not restarted
        assert mock_call_later.call_count == first_call_count

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_force_restart_cancels_previous(self, mock_call_later):
        """force=True cancels previous cycle and starts new one."""
        mock_cancel = MagicMock()
        mock_call_later.return_value = mock_cancel

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1")
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True)
        initial_calls = mock_call_later.call_count

        # Force restart
        r1.turn_on.reset_mock()
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.5, force=True)

        # Previous cancel functions were called
        assert mock_cancel.call_count >= initial_calls
        # R1 turned on again
        r1.turn_on.assert_called_once()


# ─────────────────────────────────────────────
# Tests for callbacks
# ─────────────────────────────────────────────


class TestCycleSchedulerCallbacks:
    """Tests for cycle start/end callbacks."""

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_cycle_start_callback_fired(self, mock_call_later):
        """Cycle start callbacks are fired at the beginning of start_cycle."""
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1")
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)

        cb = AsyncMock()
        scheduler.register_cycle_start_callback(cb)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True)

        cb.assert_called_once_with(
            on_time_sec=120,
            off_time_sec=480,
            on_percent=0.2,
            hvac_mode=VThermHvacMode_HEAT,
        )

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_cycle_end_callback_fired(self, mock_call_later):
        """Cycle end callbacks are fired at master cycle end via cancel_cycle."""
        import time as _time
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1", active=False)
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)

        cb_end = AsyncMock()
        scheduler.register_cycle_end_callback(cb_end)

        # Simulate a running cycle that is about to end naturally
        scheduler._current_on_time_sec = 120
        scheduler._current_off_time_sec = 480
        scheduler._current_on_percent = 0.2
        scheduler._current_hvac_mode = VThermHvacMode_HEAT
        scheduler._cycle_duration_sec = 600
        scheduler._cycle_end_unsub = MagicMock()
        # Simulate 300s of elapsed time so cancel_cycle fires the callback
        scheduler._cycle_start_time = _time.time() - 300

        await scheduler._on_master_cycle_end(None)

        cb_end.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("entity_type", "expected_class"),
        [
            (UnderlyingEntityType.VALVE, "thermostat_over_valve"),
            (UnderlyingEntityType.VALVE_REGULATION, "thermostat_over_climate_valve"),
        ],
    )
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_cycle_end_callback_fired_in_valve_mode(
        self,
        mock_call_later,
        entity_type,
        expected_class,
    ):
        """Valve-based schedulers must keep cycle callbacks active for SmartPI."""
        import time as _time

        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        valve = make_underlying("V1", active=False, entity_type=entity_type)
        scheduler = CycleScheduler(hass, thermostat, [valve], 600)

        assert scheduler.is_valve_mode is True, expected_class

        cb_end = AsyncMock()
        scheduler.register_cycle_end_callback(cb_end)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.4, force=True)

        valve.set_valve_open_percent.assert_awaited_once()
        assert scheduler.is_cycle_running is True
        assert mock_call_later.call_count == 1
        assert mock_call_later.call_args_list[0][0][1] == 600

        scheduler._cycle_start_time = _time.time() - 300
        await scheduler.cancel_cycle()

        cb_end.assert_awaited_once()
        kwargs = cb_end.await_args.kwargs
        assert kwargs["e_eff"] == pytest.approx(0.4)
        assert kwargs["elapsed_ratio"] == pytest.approx(0.5, rel=1e-4)
        assert kwargs["cycle_duration_min"] == pytest.approx(10.0)

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_callback_error_does_not_break_cycle(self, mock_call_later):
        """An error in a callback should not prevent the cycle from starting."""
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1")
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)

        failing_cb = AsyncMock(side_effect=RuntimeError("test error"))
        scheduler.register_cycle_start_callback(failing_cb)

        # Should not raise
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True)

        # R1 still turned on despite callback error
        r1.turn_on.assert_called_once()


# ─────────────────────────────────────────────
# Tests for master cycle end behavior
# ─────────────────────────────────────────────


class TestMasterCycleEnd:
    """Tests for _on_master_cycle_end behavior."""

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_cycle_end_does_not_turn_off_underlyings(self, mock_call_later):
        """At cycle end, underlyings are NOT turned off. The next cycle's tick handles state."""
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1", active=True)
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)
        scheduler._current_on_time_sec = 300  # < 600
        scheduler._current_off_time_sec = 300
        scheduler._current_on_percent = 0.5
        scheduler._current_hvac_mode = VThermHvacMode_HEAT
        scheduler._cycle_end_unsub = MagicMock()

        await scheduler._on_master_cycle_end(None)

        r1.turn_off.assert_not_called()
        thermostat.incremente_energy.assert_called_once()

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_cycle_end_full_power_no_turn_off(self, mock_call_later):
        """At cycle end with 100% power, underlyings are NOT turned off."""
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1", active=True)
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)
        scheduler._current_on_time_sec = 600  # == cycle_duration
        scheduler._current_off_time_sec = 0
        scheduler._current_on_percent = 1.0
        scheduler._current_hvac_mode = VThermHvacMode_HEAT
        scheduler._cycle_end_unsub = MagicMock()

        await scheduler._on_master_cycle_end(None)

        r1.turn_off.assert_not_called()
        thermostat.incremente_energy.assert_called_once()

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_cycle_end_increments_energy(self, mock_call_later):
        """Energy is incremented at cycle end."""
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1", active=False)
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)
        scheduler._current_on_time_sec = 120
        scheduler._current_off_time_sec = 480
        scheduler._current_on_percent = 0.2
        scheduler._current_hvac_mode = VThermHvacMode_HEAT
        scheduler._cycle_end_unsub = MagicMock()

        await scheduler._on_master_cycle_end(None)

        thermostat.incremente_energy.assert_called_once()

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_cycle_end_restarts_cycle(self, mock_call_later):
        """Master cycle end restarts the cycle with same parameters."""
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1", active=False)
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)
        scheduler._current_on_time_sec = 120
        scheduler._current_off_time_sec = 480
        scheduler._current_on_percent = 0.2
        scheduler._current_hvac_mode = VThermHvacMode_HEAT
        scheduler._cycle_end_unsub = MagicMock()

        await scheduler._on_master_cycle_end(None)

        # Should have scheduled new actions (turn_off + cycle_end for restarted cycle)
        assert mock_call_later.call_count >= 2


# ─────────────────────────────────────────────
# Tests for underlying state updates
# ─────────────────────────────────────────────


class TestUnderlyingStateUpdates:
    """Tests that the scheduler properly updates underlying state."""

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_underlying_times_updated(self, mock_call_later):
        """start_cycle updates _on_time_sec, _off_time_sec, _hvac_mode on underlyings."""
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1")
        r2 = make_underlying("R2")
        scheduler = CycleScheduler(hass, thermostat, [r1, r2], 600)

        await scheduler.start_cycle(VThermHvacMode_COOL, 0.3, force=True)

        assert r1._on_time_sec == 180
        assert r1._off_time_sec == 420
        assert r1._hvac_mode == VThermHvacMode_COOL
        assert r2._on_time_sec == 180
        assert r2._off_time_sec == 420
        assert r2._hvac_mode == VThermHvacMode_COOL
