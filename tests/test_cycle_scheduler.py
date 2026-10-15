"""Tests for CycleScheduler."""

import time
from datetime import datetime, timezone

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from homeassistant.core import HomeAssistant
from vtherm_api.command_receipt import (
    AppliedCommandReceipt,
    CommandAlteration,
    CommandReceiptKind,
    InterfaceCommandReceiptScheduler,
)

from custom_components.versatile_thermostat.cycle_scheduler import CycleScheduler
from custom_components.versatile_thermostat.valve_command import ValveCommandMixin
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
    async def test_apply_valve_update_keeps_current_cycle_callbacks_stable(
        self,
        mock_call_later,
    ):
        """A deferred valve recompute must not emit a new cycle start callback."""
        import time as _time

        mock_call_later.return_value = MagicMock()

        hass = make_hass()
        thermostat = make_thermostat()
        valve = make_underlying("V1", active=False, entity_type=UnderlyingEntityType.VALVE)
        scheduler = CycleScheduler(hass, thermostat, [valve], 600)

        cb_start = AsyncMock()
        scheduler.register_cycle_start_callback(cb_start)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True)

        cb_start.assert_awaited_once()
        valve.set_valve_open_percent.assert_awaited_once()

        cb_start.reset_mock()
        valve.set_valve_open_percent.reset_mock()
        scheduler._cycle_start_time = _time.time() - 300

        await scheduler.apply_valve_update(VThermHvacMode_HEAT, 0.6)

        cb_start.assert_not_awaited()
        valve.set_valve_open_percent.assert_awaited_once()
        assert len(scheduler._valve_cycle_trace) == 2
        assert scheduler._valve_cycle_trace[0] == (0.0, 0.2)
        assert scheduler._valve_cycle_trace[1][0] == pytest.approx(300.0, rel=1e-4)
        assert scheduler._valve_cycle_trace[1][1] == pytest.approx(0.6)

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_valve_cycle_uses_command_retained_by_thermostat(
        self,
        mock_call_later,
    ):
        """Valve updates must send and trace the thermostat-retained command."""
        mock_call_later.return_value = MagicMock()

        class ValveThermostat:
            """Minimal thermostat exposing the over-valve command contract."""

            def __init__(self):
                self.valve_open_percent = 0
                self.calls = []
                self._on_time_sec = 0
                self._off_time_sec = 0

            def apply_valve_command_percent(self, on_percent, force=False):
                self.calls.append((on_percent, force))
                self.valve_open_percent = round(on_percent * 100)
                return self.valve_open_percent / 100.0

            def __str__(self):
                return "ValveThermostat"

        hass = make_hass()
        thermostat = ValveThermostat()
        valve = make_underlying("V1", active=False, entity_type=UnderlyingEntityType.VALVE)
        scheduler = CycleScheduler(hass, thermostat, [valve], 600)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.234, force=True)

        assert thermostat.valve_open_percent == 23
        assert thermostat.calls == [(0.234, True)]
        assert scheduler._active_on_percent == pytest.approx(0.23)
        assert scheduler._valve_cycle_trace == [(0.0, 0.23)]

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.678, force=False)

        assert thermostat.valve_open_percent == 68
        assert thermostat.calls == [(0.234, True), (0.678, False)]
        assert scheduler._active_on_percent == pytest.approx(0.68)
        assert scheduler._valve_cycle_trace[-1][1] == pytest.approx(0.68)
        assert valve.set_valve_open_percent.await_count == 2

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.cycle_scheduler.time.time")
    @patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later")
    async def test_valve_mid_cycle_update_contributes_to_realized_power(
        self,
        mock_call_later,
        mock_time,
    ):
        """Valve e_eff must reflect the real average of applied mid-cycle commands."""
        mock_call_later.return_value = MagicMock()
        mock_time.side_effect = [1000.0, 1300.0, 1600.0]

        hass = make_hass()
        thermostat = make_thermostat()
        valve = make_underlying("V1", active=False, entity_type=UnderlyingEntityType.VALVE)
        scheduler = CycleScheduler(hass, thermostat, [valve], 600)

        cb_end = AsyncMock()
        scheduler.register_cycle_end_callback(cb_end)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True)
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.6, force=False)
        await scheduler.cancel_cycle()

        assert valve.set_valve_open_percent.await_count == 2
        assert scheduler._valve_cycle_trace == []

        cb_end.assert_awaited_once()
        kwargs = cb_end.await_args.kwargs
        assert kwargs["e_eff"] == pytest.approx(0.4)
        assert kwargs["elapsed_ratio"] == pytest.approx(1.0)
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


# ─────────────────────────────────────────────
# Tests for applied-command receipts
# ─────────────────────────────────────────────


class FakeValveThermostat(ValveCommandMixin):
    """Minimal valve thermostat using the real valve command filter."""

    def __init__(self, dpercent: int = 0, period_min: int = 0):
        self._valve_open_percent = None
        self._last_calculation_timestamp = None
        self._auto_regulation_dpercent = dpercent
        self._auto_regulation_period_min = period_min
        self._on_time_sec = 0
        self._off_time_sec = 0
        self.is_sleeping = False
        self.now = datetime(2024, 1, 1, tzinfo=timezone.utc)
        self.recalculate_later_calls = 0

    @property
    def valve_open_percent(self) -> int:
        return self._valve_open_percent or 0

    def do_recalculate_later(self):
        self.recalculate_later_calls += 1

    def update_custom_attributes(self):
        pass

    def async_write_ha_state(self):
        pass

    def incremente_energy(self):
        pass

    def __str__(self):
        return "FakeValveThermostat"


def record_receipts(scheduler: CycleScheduler, events: list | None = None) -> list[AppliedCommandReceipt]:
    """Register a receipt callback storing every receipt (and an event marker)."""
    receipts: list[AppliedCommandReceipt] = []

    async def on_receipt(receipt: AppliedCommandReceipt):
        receipts.append(receipt)
        if events is not None:
            events.append("receipt")

    scheduler.register_command_receipt_callback(on_receipt)
    return receipts


async def end_master_cycle(scheduler: CycleScheduler):
    """Run the master cycle end as if the full cycle had elapsed."""
    scheduler._cycle_start_time -= scheduler._cycle_duration_sec
    await scheduler._on_master_cycle_end(None)


VALVE_ENTITY_TYPES = pytest.mark.parametrize(
    "entity_type",
    [UnderlyingEntityType.VALVE, UnderlyingEntityType.VALVE_REGULATION],
    ids=["over_valve", "over_climate_valve"],
)


@patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later", return_value=MagicMock())
class TestCommandReceipts:
    """Tests for the AppliedCommandReceipt emission (vtherm_api command receipt contract)."""

    async def test_scheduler_implements_receipt_protocol(self, _mock_call_later):
        """The scheduler satisfies the optional receipt protocol of vtherm_api."""
        scheduler = CycleScheduler(make_hass(), make_thermostat(), [make_underlying("R1")], 600)
        assert isinstance(scheduler, InterfaceCommandReceiptScheduler)
        assert scheduler.is_valve_mode is False

    async def test_switch_cycle_start_receipt(self, _mock_call_later):
        """A switch cycle start emits CYCLE_START after the start callbacks and before the actuation."""
        events: list = []
        r1 = make_underlying("R1")
        r1.turn_on = AsyncMock(side_effect=lambda: events.append("turn_on"))
        scheduler = CycleScheduler(make_hass(), make_thermostat(), [r1], 600)

        async def on_start(**_kwargs):
            events.append("start")

        scheduler.register_cycle_start_callback(on_start)
        receipts = record_receipts(scheduler, events)

        before = time.monotonic()
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.234, force=True, request_id=7)

        assert events == ["start", "receipt", "turn_on"]
        assert len(receipts) == 1
        receipt = receipts[0]
        assert receipt.kind == CommandReceiptKind.CYCLE_START
        assert receipt.request_id == 7
        assert receipt.hvac_mode == "heat"
        assert receipt.requested_on_percent == pytest.approx(0.234)
        assert receipt.on_time_sec == 140
        assert receipt.off_time_sec == 459
        assert receipt.applied_on_percent == pytest.approx(140 / 600)
        assert receipt.cycle_duration_sec == 600
        assert before <= receipt.cycle_start_monotonic <= receipt.monotonic
        assert receipt.is_repeat is False
        assert receipt.alterations == frozenset()

    async def test_switch_repeat_keeps_request_id(self, _mock_call_later):
        """The automatic restart emits CYCLE_START with is_repeat and the same request."""
        events: list = []
        scheduler = CycleScheduler(make_hass(), make_thermostat(), [make_underlying("R1")], 600)

        async def on_end(**_kwargs):
            events.append("end")

        async def on_start(**_kwargs):
            events.append("start")

        scheduler.register_cycle_end_callback(on_end)
        scheduler.register_cycle_start_callback(on_start)
        receipts = record_receipts(scheduler, events)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.234, force=True, request_id=7)
        events.clear()
        await end_master_cycle(scheduler)

        assert events == ["end", "start", "receipt"]
        assert len(receipts) == 2
        repeat = receipts[1]
        assert repeat.kind == CommandReceiptKind.CYCLE_START
        assert repeat.request_id == 7
        assert repeat.is_repeat is True
        assert repeat.requested_on_percent == pytest.approx(0.234)
        assert repeat.applied_on_percent == pytest.approx(140 / 600)
        assert repeat.cycle_start_monotonic >= receipts[0].cycle_start_monotonic

    async def test_switch_pending_request_receipt_at_next_cycle(self, _mock_call_later):
        """A request stored as pending emits no receipt until the next cycle applies it."""
        scheduler = CycleScheduler(make_hass(), make_thermostat(), [make_underlying("R1")], 600)
        receipts = record_receipts(scheduler)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.5, force=True, request_id=1)
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.3, False, request_id=2)
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.4, False, request_id=3)

        assert [r.request_id for r in receipts] == [1]

        await end_master_cycle(scheduler)

        assert [r.request_id for r in receipts] == [1, 3]
        assert receipts[1].is_repeat is True
        assert receipts[1].requested_on_percent == pytest.approx(0.4)
        assert receipts[1].applied_on_percent == pytest.approx(0.4)

    @pytest.mark.parametrize(
        ("on_percent", "expected_applied"),
        [(0.05, 0.0), (0.95, 1.0)],
        ids=["min_activation", "min_deactivation"],
    )
    async def test_switch_min_on_off_alteration_is_sticky(self, _mock_call_later, on_percent, expected_applied):
        """Min on/off delays flag MIN_ON_OFF, kept by the automatic restart."""
        scheduler = CycleScheduler(
            make_hass(),
            make_thermostat(),
            [make_underlying("R1")],
            600,
            min_activation_delay=60,
            min_deactivation_delay=60,
        )
        receipts = record_receipts(scheduler)

        await scheduler.start_cycle(VThermHvacMode_HEAT, on_percent, force=True, request_id=3)
        await end_master_cycle(scheduler)

        assert len(receipts) == 2
        for receipt in receipts:
            assert receipt.request_id == 3
            assert receipt.alterations == frozenset({CommandAlteration.MIN_ON_OFF})
            assert receipt.requested_on_percent == pytest.approx(on_percent)
            assert receipt.applied_on_percent == pytest.approx(expected_applied)
        assert receipts[1].is_repeat is True

        # A later request without alteration starts clean
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.5, force=True, request_id=4)
        assert receipts[-1].alterations == frozenset()

    async def test_untagged_request_receipt(self, _mock_call_later):
        """A positional call without request_id (TPI) emits receipts with request_id None."""
        scheduler = CycleScheduler(make_hass(), make_thermostat(), [make_underlying("R1")], 600)
        receipts = record_receipts(scheduler)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, True)

        assert len(receipts) == 1
        assert receipts[0].request_id is None
        assert receipts[0].kind == CommandReceiptKind.CYCLE_START

    async def test_idle_cycle_kept_with_other_request_id(self, mock_call_later):
        """request_id does not take part in the idle cycle comparison."""
        r1 = make_underlying("R1")
        scheduler = CycleScheduler(make_hass(), make_thermostat(), [r1], 600)
        receipts = record_receipts(scheduler)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.0, force=True, request_id=1)
        call_count = mock_call_later.call_count
        cycle_start_monotonic = scheduler._cycle_start_monotonic

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.0, False, request_id=2)

        assert mock_call_later.call_count == call_count
        assert scheduler._cycle_start_monotonic == cycle_start_monotonic
        assert [r.request_id for r in receipts] == [1]

        await end_master_cycle(scheduler)
        assert [r.request_id for r in receipts] == [1, 2]

    async def test_no_receipt_callback_keeps_behaviour(self, mock_call_later):
        """Without receipt callback, no receipt is built and the cycle behaves the same."""

        async def run(with_receipts: bool):
            mock_call_later.reset_mock()
            r1 = make_underlying("R1")
            r2 = make_underlying("R2")
            start_cb = AsyncMock()
            end_cb = AsyncMock()
            scheduler = CycleScheduler(make_hass(), make_thermostat(), [r1, r2], 600, 30, 30)
            scheduler.register_cycle_start_callback(start_cb)
            scheduler.register_cycle_end_callback(end_cb)
            if with_receipts:
                record_receipts(scheduler)
            await scheduler.start_cycle(VThermHvacMode_HEAT, 0.3, True)
            await scheduler.start_cycle(VThermHvacMode_HEAT, 0.6, False, request_id=1)
            await end_master_cycle(scheduler)
            await scheduler.start_cycle(VThermHvacMode_HEAT, 0.02, force=True, request_id=2)
            return (
                start_cb.await_args_list,
                [c.kwargs["elapsed_ratio"] for c in end_cb.await_args_list],
                [c.args[1] for c in mock_call_later.call_args_list],
                r1.turn_on.await_count,
                r1.turn_off.await_count,
                r2.turn_on.await_count,
                (scheduler._current_hvac_mode, scheduler._current_on_time_sec, scheduler._current_on_percent),
                (scheduler._active_hvac_mode, scheduler._active_on_time_sec, scheduler._active_on_percent),
            )

        with patch("custom_components.versatile_thermostat.cycle_scheduler.AppliedCommandReceipt") as mock_receipt:
            without_receipts = await run(with_receipts=False)
            mock_receipt.assert_not_called()

        assert await run(with_receipts=True) == without_receipts

    async def test_receipt_callback_exception_is_isolated(self, _mock_call_later):
        """An exception in a receipt callback is logged and does not break the cycle."""
        r1 = make_underlying("R1")
        scheduler = CycleScheduler(make_hass(), make_thermostat(), [r1], 600)
        failing_cb = AsyncMock(side_effect=RuntimeError("test error"))
        scheduler.register_command_receipt_callback(failing_cb)
        receipts = record_receipts(scheduler)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True, request_id=1)

        failing_cb.assert_awaited_once()
        assert len(receipts) == 1
        r1.turn_on.assert_called_once()
        assert scheduler.is_cycle_running is True

    async def test_unregister_receipt_callback(self, _mock_call_later):
        """The function returned by the registration removes the callback."""
        scheduler = CycleScheduler(make_hass(), make_thermostat(), [make_underlying("R1")], 600)
        cb = AsyncMock()
        remove = scheduler.register_command_receipt_callback(cb)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True, request_id=1)
        cb.assert_awaited_once()

        remove()
        remove()  # removing twice is harmless
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.4, force=True, request_id=2)
        cb.assert_awaited_once()

    @VALVE_ENTITY_TYPES
    async def test_valve_cycle_start_and_running_updates(self, _mock_call_later, entity_type):
        """Valve: CYCLE_START with the retained value, then one UPDATE per running-cycle start_cycle."""
        events: list = []
        thermostat = FakeValveThermostat()
        valve = make_underlying("V1", entity_type=entity_type)
        valve.set_valve_open_percent = AsyncMock(side_effect=lambda: events.append("valve"))
        scheduler = CycleScheduler(make_hass(), thermostat, [valve], 600)

        async def on_start(**_kwargs):
            events.append("start")

        scheduler.register_cycle_start_callback(on_start)
        receipts = record_receipts(scheduler, events)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.234, force=True, request_id=1)

        assert events == ["start", "receipt", "valve"]
        start = receipts[0]
        assert start.kind == CommandReceiptKind.CYCLE_START
        assert start.requested_on_percent == pytest.approx(0.234)
        assert start.applied_on_percent == pytest.approx(0.23)
        assert start.alterations == frozenset()

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.678, False, request_id=2)
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.678, False, request_id=3)

        assert [(r.kind, r.request_id) for r in receipts] == [
            (CommandReceiptKind.CYCLE_START, 1),
            (CommandReceiptKind.UPDATE, 2),
            (CommandReceiptKind.UPDATE, 3),
        ]
        for update in receipts[1:]:
            assert update.applied_on_percent == pytest.approx(0.68)
            assert update.requested_on_percent == pytest.approx(0.678)
            assert update.alterations == frozenset()
            assert update.is_repeat is False
            assert update.cycle_start_monotonic == start.cycle_start_monotonic

    @VALVE_ENTITY_TYPES
    async def test_valve_retained_by_dpercent_is_sticky(self, _mock_call_later, entity_type):
        """A valve held back by dpercent flags VALVE_RETAINED, kept by the automatic restart."""
        thermostat = FakeValveThermostat(dpercent=5)
        scheduler = CycleScheduler(make_hass(), thermostat, [make_underlying("V1", entity_type=entity_type)], 600)
        receipts = record_receipts(scheduler)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.40, force=True, request_id=1)
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.43, False, request_id=2)

        update = receipts[1]
        assert update.kind == CommandReceiptKind.UPDATE
        assert update.request_id == 2
        assert update.requested_on_percent == pytest.approx(0.43)
        assert update.applied_on_percent == pytest.approx(0.40)
        assert update.alterations == frozenset({CommandAlteration.VALVE_RETAINED})

        await end_master_cycle(scheduler)

        repeat = receipts[2]
        assert repeat.kind == CommandReceiptKind.CYCLE_START
        assert repeat.is_repeat is True
        assert repeat.request_id == 2
        assert repeat.requested_on_percent == pytest.approx(0.43)
        assert repeat.applied_on_percent == pytest.approx(0.40)
        assert repeat.alterations == frozenset({CommandAlteration.VALVE_RETAINED})

    @VALVE_ENTITY_TYPES
    async def test_valve_deferred_update_receipt(self, _mock_call_later, entity_type):
        """apply_valve_update emits an UPDATE without request_id, inside and outside a cycle."""
        thermostat = FakeValveThermostat()
        scheduler = CycleScheduler(make_hass(), thermostat, [make_underlying("V1", entity_type=entity_type)], 600)
        start_cb = AsyncMock()
        scheduler.register_cycle_start_callback(start_cb)
        receipts = record_receipts(scheduler)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True, request_id=1)
        await scheduler.apply_valve_update(VThermHvacMode_HEAT, 0.6)

        start_cb.assert_awaited_once()
        update = receipts[1]
        assert update.kind == CommandReceiptKind.UPDATE
        assert update.request_id is None
        assert update.applied_on_percent == pytest.approx(0.6)
        assert update.cycle_start_monotonic == receipts[0].cycle_start_monotonic

        await scheduler.cancel_cycle()
        await scheduler.apply_valve_update(VThermHvacMode_HEAT, 0.3)

        outside = receipts[2]
        assert outside.kind == CommandReceiptKind.UPDATE
        assert outside.request_id is None
        assert outside.applied_on_percent == pytest.approx(0.3)
        assert outside.cycle_start_monotonic is None

    async def test_no_receipt_while_inhibited(self, _mock_call_later):
        """The inhibition gate drops the commands: no receipt for a command that is not applied."""
        thermostat = make_thermostat()
        thermostat.is_inhibited = True
        scheduler = CycleScheduler(make_hass(), thermostat, [make_underlying("R1")], 600)
        receipts = record_receipts(scheduler)

        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.5, force=True, request_id=1)
        assert receipts == []

        # The exit reconciliation runs once the thermostat is no longer inhibited
        thermostat.is_inhibited = False
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.5, force=True, request_id=2)
        assert [receipt.request_id for receipt in receipts] == [2]
