"""Unit tests for the pure algorithmic logic of the TRUE TICK scheduler."""

import pytest
from custom_components.versatile_thermostat.cycle_tick_logic import (
    UnderlyingCycleState,
    compute_circular_offsets,
    compute_target_state,
    evaluate_need_on,
    evaluate_need_off,
    compute_e_eff,
)


def test_compute_circular_offsets():
    """Test standard normal case with spacing."""
    assert compute_circular_offsets(600, 1) == [0.0]
    assert compute_circular_offsets(600, 2) == [0.0, 300.0]
    assert compute_circular_offsets(600, 3) == [0.0, 200.0, 400.0]


def test_compute_target_state_normal():
    """Test the target compute with normal condition off_t > on_t."""
    # cycle 600, on_t=100, off_t=300
    # current_t < on_t -> OFF, next_tick=on_t
    t, nt, dur = compute_target_state(100, 300, 50, 600)
    assert t is False
    assert nt == 100
    assert dur == 50

    # current_t < off_t -> ON, next_tick=off_t
    t, nt, dur = compute_target_state(100, 300, 150, 600)
    assert t is True
    assert nt == 300
    assert dur == 150

    # current_t >= off_t -> OFF, next_tick=cycle_duration
    t, nt, dur = compute_target_state(100, 300, 400, 600)
    assert t is False
    assert nt == 600
    assert dur == 200


def test_compute_target_state_wrap_around():
    """Test the target compute with wrap around off_t <= on_t."""
    # cycle 600, on_t=400, off_t=100
    # current_t < off_t -> ON, next_tick=off_t
    t, nt, dur = compute_target_state(400, 100, 50, 600)
    assert t is True
    assert nt == 100
    assert dur == 50

    # current_t < on_t -> OFF, next_tick=on_t
    t, nt, dur = compute_target_state(400, 100, 250, 600)
    assert t is False
    assert nt == 400
    assert dur == 150

    # current_t >= on_t -> ON, next_tick=cycle_duration
    t, nt, dur = compute_target_state(400, 100, 500, 600)
    assert t is True
    assert nt == 600
    assert dur == 100


def test_evaluate_need_on_nominal():
    """Test turning ON is OK when constraints are met."""
    action, new_on_t, penalty = evaluate_need_on(
        under_dt=60, state_duration=30,
        min_deactivation=30, min_activation=20,
        on_t=100, current_t=100
    )
    assert action == 'turn_on'
    assert new_on_t is None
    assert penalty == 0.0


def test_evaluate_need_on_racollage_min_activation():
    """Test turning ON fails due to state_duration < min_activation."""
    action, new_on_t, penalty = evaluate_need_on(
        under_dt=60, state_duration=10,  # too short!
        min_deactivation=30, min_activation=20,
        on_t=100, current_t=100
    )
    assert action == 'skip'
    # new_on_t = on_t - state_duration = 100 - 10 = 90
    assert new_on_t == 90  # wait: new_on_t = 100 - 10 = 90
    # constraint check: (90 - 100) < (30 - 60) -> (-10) < (-30) which is False
    # so new_on_t should be 90
    assert penalty == 10.0


def test_evaluate_need_on_racollage_min_deactivation():
    """Test turning ON fails due to under_dt < min_deactivation."""
    action, new_on_t, penalty = evaluate_need_on(
        under_dt=10, state_duration=30,
        min_deactivation=30, min_activation=20,
        on_t=100, current_t=100
    )
    assert action == 'skip'
    # racollage logic: 
    # new_on_t = 100 - 30 = 70.
    # diff: 70 - 100 = -30. required wait = 30 - 10 = 20.
    # -30 < 20 is True.
    # so new_on_t = 100 + 20 = 120.
    assert new_on_t == 120.0
    assert penalty == 20.0


def test_evaluate_need_on_racollage_exact_equality():
    """Test finding 2: exact equality for min_activation should skip."""
    action, new_on_t, penalty = evaluate_need_on(
        under_dt=60, state_duration=20,
        min_deactivation=30, min_activation=20,
        on_t=100, current_t=100
    )
    assert action == 'skip'
    assert new_on_t == 80.0
    assert penalty == 20.0


def test_evaluate_need_on_racollage_negative():
    """Test finding 1: handles potential negative new_on_t correctly."""
    action, new_on_t, penalty = evaluate_need_on(
        under_dt=100, state_duration=50,
        min_deactivation=30, min_activation=60,
        on_t=0.0, current_t=0.0
    )
    assert action == 'skip'
    assert new_on_t == 0.0
    assert penalty == 50.0


def test_evaluate_need_off_nominal():
    """Test turning OFF is OK when constraints are met."""
    action, new_off_t, penalty = evaluate_need_off(
        under_dt=60, state_duration=30,
        min_activation=30, min_deactivation=20,
        off_t=200, current_t=200
    )
    assert action == 'turn_off'
    assert new_off_t is None
    assert penalty == 0.0


def test_evaluate_need_off_racollage_min_activation():
    """Test turning OFF fails due to under_dt < min_activation."""
    action, new_off_t, penalty = evaluate_need_off(
        under_dt=10, state_duration=30,
        min_activation=30, min_deactivation=20,
        off_t=200, current_t=200
    )
    assert action == 'skip'
    # new_off_t = 200 - 30 = 170
    # diff = -30. required wait = 30 - 10 = 20. -30 < 20 is True
    # new_off_t = 200 + 20 = 220
    assert new_off_t == 220.0
    assert penalty == -20.0


def test_evaluate_need_off_racollage_exact_equality():
    """Test finding 2: exact equality for min_deactivation should skip."""
    action, new_off_t, penalty = evaluate_need_off(
        under_dt=60, state_duration=20,
        min_activation=30, min_deactivation=20,
        off_t=200, current_t=200
    )
    assert action == 'skip'
    assert new_off_t == 180.0
    assert penalty == -20.0


def test_evaluate_need_off_racollage_negative():
    """Test finding 1: handles potential negative new_off_t correctly."""
    action, new_off_t, penalty = evaluate_need_off(
        under_dt=100, state_duration=50,
        min_activation=30, min_deactivation=60,
        off_t=0.0, current_t=0.0
    )
    assert action == 'skip'
    assert new_off_t == 0.0
    assert penalty == -50.0


def test_compute_e_eff():
    """Test e_eff computation with penalties."""
    # 2 underlyings, cycle 600 -> full_on_t = 1200
    # on_percent = 0.5 -> expected ON time = 600
    # penalty = 0 -> e_eff = 0.5
    assert compute_e_eff(0.5, 0.0, 600, 2) == 0.5
    
    # penalty = 60 (we skipped 60s of ON time)
    # real ON time = 540. e_eff = 540 / 1200 = 0.45
    assert compute_e_eff(0.5, 60.0, 600, 2) == 0.45
    
    # penalty = -120 (we skipped 120s of OFF time -> e.g. stayed ON more)
    # real ON time = 600 - (-120) = 720. e_eff = 720 / 1200 = 0.6
    assert compute_e_eff(0.5, -120.0, 600, 2) == 0.6
