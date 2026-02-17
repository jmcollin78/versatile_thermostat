"""Pure logic for the Versatile Thermostat True Tick Cycle Scheduler."""

class UnderlyingCycleState:
    """Per-underlying state tracking for a single cycle."""

    def __init__(self, underlying, offset: float):
        """Initialize the state with an underlying reference and a fixed circular offset."""
        self.underlying = underlying
        self.offset = offset
        self.on_t: float = 0.0
        self.off_t: float = 0.0
        self.on_time: float = 0.0


def compute_circular_offsets(cycle_duration_sec: float, n: int) -> list[float]:
    """Compute evenly-spaced circular offsets for n underlyings.
    
    Returns:
        List of start offsets in seconds for each underlying.
    """
    if n <= 1:
        return [0.0] * n

    step = cycle_duration_sec / n
    return [round(i * step, 1) for i in range(n)]


def compute_target_state(
    on_t: float, off_t: float, current_t: float, cycle_duration: float
) -> tuple[bool, float, float]:
    """Determine the theoretical target state and the next tick timestamp.

    Returns:
        (target_is_on, next_tick, state_duration)
    """
    if off_t > on_t:  # ON is confined in [on_t, off_t)
        if current_t < on_t:
            target = False
            next_tick = on_t
        elif current_t < off_t:
            target = True
            next_tick = off_t
        else:
            target = False
            next_tick = cycle_duration
    else:              # ON wraps around: [0, off_t) U [on_t, cycle_end)
        if current_t < off_t:
            target = True
            next_tick = off_t
        elif current_t < on_t:
            target = False
            next_tick = on_t
        else:
            target = True
            next_tick = cycle_duration

    # Note (off_t == on_t falls in wrap-around condition):
    # This works safely because upstream guards in cycle_scheduler._start_cycle_switch
    # handle `on_time == 0` and `on_time == cycle_duration` before evaluating ticks.
    state_duration = next_tick - current_t
    return target, next_tick, state_duration


def evaluate_need_on(
    under_dt: float, state_duration: float,
    min_deactivation: float, min_activation: float,
    on_t: float, current_t: float,
) -> tuple[str, float | None, float]:
    """Evaluate whether to actually turn ON (need_on) according to constraints.
    
    Returns:
        (action, new_on_t_or_none, penalty_delta)
        action is 'turn_on' or 'skip'
    """
    if under_dt >= min_deactivation and state_duration > min_activation:
        return 'turn_on', None, 0.0

    # CAS RACOLLAGE (Skip this turn ON)
    new_on_t = max(0.0, on_t - state_duration)
    penalty_delta = state_duration
    
    if (new_on_t - current_t) < (min_deactivation - under_dt):
        new_on_t = current_t + (min_deactivation - under_dt)
        delay = new_on_t - current_t
        penalty_delta = delay if delay < state_duration else state_duration

    return 'skip', new_on_t, penalty_delta


def evaluate_need_off(
    under_dt: float, state_duration: float,
    min_activation: float, min_deactivation: float,
    off_t: float, current_t: float,
) -> tuple[str, float | None, float]:
    """Evaluate whether to actually turn OFF (need_off) according to constraints.
    
    Returns:
        (action, new_off_t_or_none, penalty_delta)
        action is 'turn_off' or 'skip'
    """
    if under_dt >= min_activation and state_duration > min_deactivation:
        return 'turn_off', None, 0.0

    # CAS RACOLLAGE (Skip this turn OFF)
    new_off_t = max(0.0, off_t - state_duration)
    penalty_delta = -state_duration

    if (new_off_t - current_t) < (min_activation - under_dt):
        new_off_t = current_t + (min_activation - under_dt)
        delay = new_off_t - current_t
        penalty_delta = -delay if delay < state_duration else -state_duration

    return 'skip', new_off_t, penalty_delta


def compute_e_eff(
    on_percent: float, penalty: float,
    cycle_duration: float, n_underlyings: int,
) -> float:
    """Compute effective power ratio (e_eff) at the end of the cycle."""
    if n_underlyings == 0 or cycle_duration <= 0:
        return 0.0

    full_on_t = cycle_duration * n_underlyings
    e_eff = (full_on_t * on_percent - penalty) / full_on_t
    
    return max(0.0, min(1.0, e_eff))
