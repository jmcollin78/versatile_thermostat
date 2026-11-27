"""Realistic closed-loop simulation harness for AutoTpiManager.

The plant is a 1R1C room heated by an emitter with a first-order lag, driven by
the TPI cycle (on/off PWM). The regulation and the learning only see the room
temperature through a sensor model (resolution and reporting policy), as in
production.

    emitter:  dP/dt = (pwm(t) - P) / emitter_lag
    room:     dT/dt = capacity * P - (T - Text) / tau
    sensor:   periodic (fixed period) or on change (rounded value changes)

Ideal coefficients used as references:
    Kext* = (1 / tau) / capacity            (steady state at the setpoint)
    Kint* = 1 / (capacity * T_cl)           (closed-loop time constant T_cl)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
import random
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.versatile_thermostat.auto_tpi_manager import AutoTpiManager
from custom_components.versatile_thermostat.const import CONF_TPI_COEF_EXT, CONF_TPI_COEF_INT
from custom_components.versatile_thermostat.prop_algo_tpi import TpiAlgorithm
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT

MANAGER_MODULE = "custom_components.versatile_thermostat.auto_tpi_manager"


@dataclass
class SensorProfile:
    """Temperature sensor model."""

    name: str
    resolution: float
    period_min: int | None = None  # periodic report every period_min minutes
    on_change: bool = False  # report as soon as the rounded value changes
    noise: float = 0.0  # standard deviation of the measurement noise before rounding (°C)

    def quantize(self, temp: float) -> float:
        """Round the temperature to the sensor resolution."""
        return round(round(temp / self.resolution) * self.resolution, 4)


SENSOR_001_60S = SensorProfile("0.01/60s", 0.01, period_min=1)
SENSOR_01_ON_CHANGE = SensorProfile("0.1/on_change", 0.1, on_change=True)
SENSOR_001_60S_NOISY = SensorProfile("0.01/60s+noise", 0.01, period_min=1, noise=0.02)
SENSOR_01_ON_CHANGE_NOISY = SensorProfile("0.1/on_change+noise", 0.1, on_change=True, noise=0.02)


@dataclass
class RoomProfile:
    """Physical room and emitter parameters."""

    capacity: float  # °C/h at 100 % power
    tau_h: float = 50.0  # room time constant (h)
    emitter_lag_min: float = 15.0  # emitter first-order lag (min)
    ext_mean: float = 5.0
    ext_amplitude: float = 3.0  # daily sine amplitude

    @property
    def kext_ref(self) -> float:
        """Kext that compensates the losses at the setpoint."""
        return (1.0 / self.tau_h) / self.capacity

    def ext_temp(self, minute: int) -> float:
        """Outdoor temperature, coldest at 06:00."""
        hour = (minute / 60.0) % 24
        return self.ext_mean - self.ext_amplitude * math.cos(2 * math.pi * (hour - 6) / 24)


def default_schedule(minute: int) -> float:
    """Setpoint: 20 °C from 06:00 to 22:00, 17.5 °C at night."""
    hour = (minute / 60.0) % 24
    return 20.0 if 6 <= hour < 22 else 17.5


def constant_schedule(minute: int) -> float:  # pylint: disable=unused-argument
    """Constant 19.5 °C setpoint."""
    return 19.5


@dataclass
class SimResult:
    """Outcome of a simulation run."""

    kint: float
    kext: float
    learning_active: bool
    kint_history: list = field(default_factory=list)
    kext_history: list = field(default_factory=list)
    status_counts: dict = field(default_factory=dict)
    in_band_ratio: float = 0.0  # time within ±0.3 °C once the setpoint is reached (last stats_days)
    max_overshoot: float = 0.0  # max T - setpoint once the setpoint is reached (last stats_days)


def make_hass():
    """Minimal hass mock for AutoTpiManager."""
    hass = MagicMock()
    hass.config.units.temperature_unit = "°C"
    hass.loop.is_closed.return_value = False

    def _create_task(coro):
        coro.close()
        return MagicMock()

    hass.async_create_task = MagicMock(side_effect=_create_task)
    return hass


async def run_simulation(
    room: RoomProfile,
    sensor: SensorProfile,
    days: float = 7.0,
    cycle_min: int = 5,
    coef_int: float = 0.6,
    coef_ext: float = 0.01,
    heater_heating_time: int = 15,
    start_temp: float = 17.0,
    schedule=default_schedule,
    stats_days: float = 2.0,
    seed: int = 1,
) -> SimResult:
    """Run the closed loop with the real AutoTpiManager and TpiAlgorithm."""
    sim_time = datetime(2026, 1, 5, 0, 0, 0)
    minute = 0
    rng = random.Random(seed)

    with patch(f"{MANAGER_MODULE}.Store") as store_cls, patch(f"{MANAGER_MODULE}.dt_util") as dt_util_mock:
        store = store_cls.return_value
        store.async_load = AsyncMock(return_value=None)
        store.async_save = AsyncMock()
        dt_util_mock.now.side_effect = lambda: sim_time
        dt_util_mock.as_local.side_effect = lambda x: x

        config_entry = MagicMock()
        config_entry.data = {}
        manager = AutoTpiManager(
            hass=make_hass(),
            config_entry=config_entry,
            unique_id="sim",
            name="Sim",
            cycle_min=cycle_min,
            coef_int=coef_int,
            coef_ext=coef_ext,
            heater_heating_time=heater_heating_time,
        )
        manager._enable_update_config = False  # pylint: disable=protected-access
        manager._enable_notification = False  # pylint: disable=protected-access
        await manager.start_learning(reset_data=True)

        algo = TpiAlgorithm(coef_int, coef_ext, "climate.sim")

        temp = start_temp
        emitter = 0.0
        reported = sensor.quantize(temp)
        result = SimResult(0, 0, True)
        in_band = counted = 0
        reached = False
        last_setpoint = schedule(0)
        total_minutes = int(days * 1440)
        stats_from = total_minutes - int(stats_days * 1440)

        while minute < total_minutes:
            setpoint = schedule(minute)
            if setpoint != last_setpoint:
                reached = False
                last_setpoint = setpoint
            ext = room.ext_temp(minute)

            await manager.update(room_temp=reported, ext_temp=ext, hvac_mode="heat", target_temp=setpoint)
            params = await manager.calculate()
            if params:
                algo.update_parameters(tpi_coef_int=params[CONF_TPI_COEF_INT], tpi_coef_ext=params[CONF_TPI_COEF_EXT])
            algo.calculate(setpoint, reported, ext, None, VThermHvacMode_HEAT)
            on_percent = algo.on_percent or 0.0
            on_min = on_percent * cycle_min

            await manager.on_cycle_started(on_min * 60, (cycle_min - on_min) * 60, on_percent, "heat")

            for step in range(cycle_min):
                pwm = min(1.0, max(0.0, on_min - step))
                emitter += (pwm - emitter) / room.emitter_lag_min
                temp += (room.capacity * emitter - (temp - ext) / room.tau_h) / 60.0
                minute += 1
                sim_time += timedelta(minutes=1)
                quantized = sensor.quantize(temp + (rng.gauss(0.0, sensor.noise) if sensor.noise else 0.0))
                if (sensor.period_min and minute % sensor.period_min == 0) or (sensor.on_change and quantized != reported):
                    reported = quantized

                if abs(temp - setpoint) <= 0.1:
                    reached = True
                if reached and minute >= stats_from:
                    counted += 1
                    in_band += abs(temp - setpoint) <= 0.3
                    result.max_overshoot = max(result.max_overshoot, temp - setpoint)

            await manager.update(room_temp=reported, ext_temp=room.ext_temp(minute), hvac_mode="heat", target_temp=schedule(minute))
            await manager.on_cycle_completed(e_eff=on_percent)

            status = manager.state.last_learning_status.split("(")[0]
            result.status_counts[status] = result.status_counts.get(status, 0) + 1
            if minute % 60 == 0:
                result.kint_history.append(round(manager.state.coeff_indoor_heat, 4))
                result.kext_history.append(round(manager.state.coeff_outdoor_heat, 4))

        result.kint = manager.state.coeff_indoor_heat
        result.kext = manager.state.coeff_outdoor_heat
        result.learning_active = manager.learning_active
        result.in_band_ratio = in_band / counted if counted else 0.0
        return result
