"""Closed-loop Auto TPI learning on a realistic room (emitter lag, sensor resolution and noise).

Kint reference: a P controller on a lag-dominant room reaches a closed-loop time
constant T_cl with Kint = 1 / (capacity * T_cl). T_cl is taken as twice the
emitter delay plus half a cycle. The learned Kint must not drift far below it.
"""

# pylint: disable=redefined-outer-name

import logging

import pytest

from .auto_tpi_sim import (
    SENSOR_001_60S_NOISY,
    SENSOR_01_ON_CHANGE_NOISY,
    RoomProfile,
    constant_schedule,
    default_schedule,
    run_simulation,
)

CYCLE_MIN = 5
HEATER_HEATING_TIME = 15
SIM_DAYS = 7

SCENARIOS = [
    pytest.param(default_schedule, 17.0, SENSOR_001_60S_NOISY, id="schedule-0.01_60s"),
    pytest.param(default_schedule, 17.0, SENSOR_01_ON_CHANGE_NOISY, id="schedule-0.1_on_change"),
    pytest.param(constant_schedule, 19.3, SENSOR_001_60S_NOISY, id="constant-0.01_60s"),
    pytest.param(constant_schedule, 19.3, SENSOR_01_ON_CHANGE_NOISY, id="constant-0.1_on_change"),
]


def kint_reference(capacity: float) -> float:
    """Kint for the target closed-loop time constant, capped like the learning."""
    t_cl_h = 2 * (HEATER_HEATING_TIME + CYCLE_MIN / 2) / 60
    return min(1.0, 1.0 / (capacity * t_cl_h))


@pytest.fixture(autouse=True)
def quiet_auto_tpi_logs():
    """The simulation runs thousands of cycles: keep the auto TPI logs quiet."""
    logger = logging.getLogger("custom_components.versatile_thermostat.auto_tpi_manager")
    previous = logger.level
    logger.setLevel(logging.ERROR)
    yield
    logger.setLevel(previous)


@pytest.mark.parametrize("schedule, start_temp, sensor", SCENARIOS)
async def test_auto_tpi_kint_does_not_collapse(schedule, start_temp, sensor):
    """The learned Kint stays at least at half of the reference value."""
    room = RoomProfile(capacity=1.2, emitter_lag_min=HEATER_HEATING_TIME)
    result = await run_simulation(
        room,
        sensor,
        days=SIM_DAYS,
        cycle_min=CYCLE_MIN,
        heater_heating_time=HEATER_HEATING_TIME,
        schedule=schedule,
        start_temp=start_temp,
    )

    assert result.kint >= 0.5 * kint_reference(room.capacity), f"Kint={result.kint:.3f}, history={result.kint_history[::24]}"


@pytest.mark.parametrize("schedule, start_temp, sensor", SCENARIOS)
async def test_auto_tpi_kext_converges(schedule, start_temp, sensor):
    """The learned Kext stays within ±50 % of the losses / capacity ratio."""
    room = RoomProfile(capacity=1.2, emitter_lag_min=HEATER_HEATING_TIME)
    result = await run_simulation(
        room,
        sensor,
        days=SIM_DAYS,
        cycle_min=CYCLE_MIN,
        heater_heating_time=HEATER_HEATING_TIME,
        schedule=schedule,
        start_temp=start_temp,
    )

    assert 0.5 * room.kext_ref <= result.kext <= 1.5 * room.kext_ref, f"Kext={result.kext:.4f}, reference={room.kext_ref:.4f}"
