"""Utility functions for timing calculations in proportional algorithms."""


def calculate_cycle_times(
    on_percent: float,
    cycle_min: int,
    minimal_activation_delay: int | None = 0,
    minimal_deactivation_delay: int | None = 0,
) -> tuple[int, int, bool]:
    """
    Convert on_percent to on_time_sec and off_time_sec.

    Applies minimal activation and deactivation delays to avoid
    very short on/off periods that may damage equipment or be ineffective.

    Args:
        on_percent: The calculated heating percentage (0.0 to 1.0)
        cycle_min: The cycle duration in minutes
        minimal_activation_delay: Minimum on time in seconds (below this, turn off)
        minimal_deactivation_delay: Minimum off time in seconds (below this, stay on)

    Returns:
        Tuple of (on_time_sec, off_time_sec, forced_by_timing)
        - forced_by_timing: True if min_on or min_off delays modified the percentage significantly.
    """
    # Handle None values for delays
    min_on = minimal_activation_delay if minimal_activation_delay is not None else 0
    min_off = minimal_deactivation_delay if minimal_deactivation_delay is not None else 0

    # Clamp on_percent to [0, 1]
    on_percent = max(0.0, min(1.0, on_percent))

    cycle_sec = cycle_min * 60
    on_time_sec = on_percent * cycle_sec
    forced_by_timing = False

    # Do not heat for less than minimal_activation_delay
    if on_time_sec > 0 and on_time_sec < min_on:
        on_time_sec = 0
        forced_by_timing = True

    off_time_sec = cycle_sec - on_time_sec

    # Do not stop heating when off time less than minimal_deactivation_delay
    if on_time_sec < cycle_sec and off_time_sec < min_off:
        on_time_sec = cycle_sec
        off_time_sec = 0
        forced_by_timing = True

    return int(on_time_sec), int(off_time_sec), forced_by_timing
