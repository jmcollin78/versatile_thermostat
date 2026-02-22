"""Tests for CycleScheduler."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from homeassistant.core import HomeAssistant

from custom_components.versatile_thermostat.cycle_scheduler import CycleScheduler
from custom_components.versatile_thermostat.vtherm_hvac_mode import (
    VThermHvacMode_HEAT,
    VThermHvacMode_COOL,
    VThermHvacMode_OFF,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def make_underlying(name="R1", active=False):
    """Create a mock UnderlyingSwitch."""
    under = MagicMock()
    under.turn_on = AsyncMock(return_value=True)
    under.turn_off = AsyncMock()
    under.is_device_active = active
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
# Tests for compute_offsets (pure function)
# ─────────────────────────────────────────────


class TestComputeOffsets:
    """Tests for CycleScheduler.compute_offsets static method."""

    def test_single_underlying(self):
        """1 underlying -> offset = [0]."""
        offsets = CycleScheduler.compute_offsets(120, 600, 1)
        assert offsets == [0.0]

    def test_two_low_power_20pct(self):
        """2 underlyings, 20% (120s ON in 600s) -> no overlap."""
        offsets = CycleScheduler.compute_offsets(120, 600, 2)
        assert offsets == [0.0, 480.0]
        # R1: 0-120, R2: 480-600 -> no overlap
        assert offsets[1] >= offsets[0] + 120  # no overlap

    def test_two_40pct(self):
        """2 underlyings, 40% (240s ON in 600s) -> no overlap."""
        offsets = CycleScheduler.compute_offsets(240, 600, 2)
        assert offsets == [0.0, 360.0]
        # R1: 0-240, R2: 360-600 -> no overlap
        assert offsets[1] >= offsets[0] + 240

    def test_two_half_power_50pct(self):
        """2 underlyings, 50% (300s ON in 600s) -> no overlap."""
        offsets = CycleScheduler.compute_offsets(300, 600, 2)
        assert offsets == [0.0, 300.0]
        # R1: 0-300, R2: 300-600 -> exactly zero overlap
        assert offsets[1] == offsets[0] + 300

    def test_two_high_power_60pct(self):
        """2 underlyings, 60% (360s ON in 600s) -> minimal overlap."""
        offsets = CycleScheduler.compute_offsets(360, 600, 2)
        assert offsets == [0.0, 240.0]
        # R1: 0-360, R2: 240-600 -> overlap 120s (unavoidable)
        overlap = (offsets[0] + 360) - offsets[1]
        assert overlap == 120

    def test_two_full_power_100pct(self):
        """2 underlyings, 100% -> all offsets at 0."""
        offsets = CycleScheduler.compute_offsets(600, 600, 2)
        assert offsets == [0.0, 0.0]

    def test_two_zero_power(self):
        """2 underlyings, 0% -> all offsets at 0."""
        offsets = CycleScheduler.compute_offsets(0, 600, 2)
        assert offsets == [0.0, 0.0]

    def test_three_20pct(self):
        """3 underlyings, 20% (120s ON in 600s) -> no overlap."""
        offsets = CycleScheduler.compute_offsets(120, 600, 3)
        assert offsets == [0.0, 240.0, 480.0]
        # Check no overlap between consecutive underlyings
        for i in range(len(offsets) - 1):
            assert offsets[i + 1] >= offsets[i] + 120

    def test_three_33pct(self):
        """3 underlyings, 33% (200s ON in 600s) -> no overlap."""
        offsets = CycleScheduler.compute_offsets(200, 600, 3)
        assert offsets == [0.0, 200.0, 400.0]
        for i in range(len(offsets) - 1):
            assert offsets[i + 1] >= offsets[i] + 200

    def test_three_50pct(self):
        """3 underlyings, 50% (300s ON in 600s) -> some overlap."""
        offsets = CycleScheduler.compute_offsets(300, 600, 3)
        assert offsets == [0.0, 150.0, 300.0]
        # R1: 0-300, R2: 150-450, R3: 300-600
        # R1-R2 overlap: 150s, R2-R3 overlap: 150s
        overlap_12 = (offsets[0] + 300) - offsets[1]
        overlap_23 = (offsets[1] + 300) - offsets[2]
        assert overlap_12 == 150
        assert overlap_23 == 150

    def test_three_full_power(self):
        """3 underlyings, 100% -> all at 0."""
        offsets = CycleScheduler.compute_offsets(600, 600, 3)
        assert offsets == [0.0, 0.0, 0.0]

    def test_on_time_exceeds_cycle(self):
        """on_time > cycle_duration -> treated as 100%."""
        offsets = CycleScheduler.compute_offsets(700, 600, 2)
        assert offsets == [0.0, 0.0]

    def test_four_underlyings_25pct(self):
        """4 underlyings, 25% (150s ON in 600s) -> no overlap."""
        offsets = CycleScheduler.compute_offsets(150, 600, 4)
        assert offsets == [0.0, 150.0, 300.0, 450.0]
        for i in range(len(offsets) - 1):
            assert offsets[i + 1] >= offsets[i] + 150


# ─────────────────────────────────────────────
# Tests for CycleScheduler lifecycle
# ─────────────────────────────────────────────


class TestCycleSchedulerLifecycle:
    """Tests for CycleScheduler start_cycle, cancel_cycle, etc."""

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_start_cycle_single_underlying(self, mock_call_later):
        """Single underlying: turn_on immediately, schedule turn_off and cycle_end."""
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
    async def test_start_cycle_two_underlyings(self, mock_call_later):
        """Two underlyings with 50%: R1 on immediately, R2 scheduled at 300s."""
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

        # Scheduled: R2_on at 300s, cycle_end at 600s
        # R1 end = 0+300 = 300 < 600, so R1_off at 300s
        # R2 end = 300+300 = 600 >= 600, so no R2_off (handled by cycle_end)
        assert mock_call_later.call_count == 3  # R1_off, R2_on, cycle_end

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

        scheduler.cancel_cycle()
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
        """Cycle end callbacks are fired at master cycle end."""
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1", active=False)
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)

        cb_end = AsyncMock()
        scheduler.register_cycle_end_callback(cb_end)

        # Simulate a cycle end
        scheduler._current_on_time_sec = 120
        scheduler._current_off_time_sec = 480
        scheduler._current_on_percent = 0.2
        scheduler._current_hvac_mode = VThermHvacMode_HEAT
        scheduler._cycle_duration_sec = 600

        await scheduler._on_master_cycle_end(None)

        cb_end.assert_called_once()

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
    async def test_cycle_end_turns_off_active_underlyings(self, mock_call_later):
        """At cycle end, active underlyings are turned off (unless 100% power)."""
        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        r1 = make_underlying("R1", active=True)
        scheduler = CycleScheduler(hass, thermostat, [r1], 600)
        scheduler._current_on_time_sec = 300  # < 600, so should turn off
        scheduler._current_off_time_sec = 300
        scheduler._current_on_percent = 0.5
        scheduler._current_hvac_mode = VThermHvacMode_HEAT

        await scheduler._on_master_cycle_end(None)

        r1.turn_off.assert_called_once()
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
