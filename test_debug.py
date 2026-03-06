import asyncio
from unittest.mock import MagicMock
from datetime import timedelta
from homeassistant.util import dt as dt_util

class State:
    def __init__(self):
        self.last_power = 0.0
        self.cycle_active = False
        self.cycle_start_date = None
        self.current_cycle_params = None
        self.total_cycles = 0
        self.last_heater_stop_time = None
        self.last_state = "heat"
        self.current_cycle_cold_factor = 0.0
        self.max_capacity_heat = 0
        self.capacity_heat_learn_count = 0
        self.last_learning_status = ""

class Manager:
    def __init__(self):
        self.state = State()
        self._cycle_min = 5
        self._name = "Test"
        self._heater_heating_time = 0.1
        self._current_hvac_mode = "heat"
        self.learning_active = False
        self._continuous_kext = False

    async def on_cycle_completed(self, e_eff=None):
        now = dt_util.now()
        prev_params = self.state.current_cycle_params or {}
        if self.state.cycle_start_date is not None and self.state.current_cycle_params is not None:
             cycle_start = self.state.cycle_start_date
             if cycle_start.tzinfo is None:
                 cycle_start = dt_util.as_local(cycle_start)
             elapsed_minutes = (now - cycle_start).total_seconds() / 60
             expected_duration = self._cycle_min
             tolerance = max(expected_duration * 0.1, 1.0)
             duration_diff = elapsed_minutes - expected_duration
             if duration_diff < -tolerance:
                self.state.last_learning_status = "cycle_too_short"
                self.state.cycle_active = False
                return
             if duration_diff > tolerance:
                self.state.last_learning_status = "cycle_gap_detected"
        else:
            return

        on_time_sec = prev_params.get("on_time_sec", 0)
        off_time_sec = prev_params.get("off_time_sec", 0)
        
        if not self.state.cycle_active:
            return

        self.state.cycle_active = False

        if e_eff is not None:
            self.state.last_power = e_eff

        self.state.total_cycles += 1

async def main():
    m = Manager()
    m.state.last_power = 1.0
    now = dt_util.now()
    m.state.cycle_start_date = now - timedelta(minutes=5)
    m.state.current_cycle_params = {"on_time_sec": 150, "off_time_sec": 150}
    m.state.cycle_active = True
    await m.on_cycle_completed(0.5)
    print("LAST POWER:", m.state.last_power)
    print("STATUS:", m.state.last_learning_status)
    print("ACTIVE:", m.state.cycle_active)

asyncio.run(main())
