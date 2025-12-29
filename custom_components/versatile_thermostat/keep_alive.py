"""Building blocks for the heater switch keep-alive feature.

The heater switch keep-alive feature consists of regularly refreshing the state
of directly controlled switches at a configurable interval (regularly turning the
switch 'on' or 'off' again even if it is already turned 'on' or 'off'), just like
the keep_alive setting of Home Assistant's Generic Thermostat integration:
 https://www.home-assistant.io/integrations/generic_thermostat/
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta, datetime
from time import monotonic

from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers.event import async_track_time_interval


_LOGGER = logging.getLogger(__name__)


class BackoffTimer:
    """Exponential backoff timer with a non-blocking polling-style implementation.

    Usage example:
        timer = BackoffTimer(multiplier=1.5, upper_limit_sec=600)
        while some_condition:
            if timer.is_ready():
                do_something()
    """

    def __init__(
        self,
        *,
        multiplier=2.0,
        lower_limit_sec=30,
        upper_limit_sec=86400,
        initially_ready=True,
    ):
        """Initialize a BackoffTimer instance.

        Args:
            multiplier (int, optional): Period multiplier applied when is_ready() is True.
            lower_limit_sec (int, optional): Initial backoff period in seconds.
            upper_limit_sec (int, optional): Maximum backoff period in seconds.
            initially_ready (bool, optional): Whether is_ready() should return True the
            first time it is called, or after a call to reset().
        """
        self._multiplier = multiplier
        self._lower_limit_sec = lower_limit_sec
        self._upper_limit_sec = upper_limit_sec
        self._initially_ready = initially_ready

        self._timestamp = 0
        self._period_sec = self._lower_limit_sec

    @property
    def in_progress(self) -> bool:
        """Whether the backoff timer is in progress (True after a call to is_ready())."""
        return bool(self._timestamp)

    def reset(self):
        """Reset a BackoffTimer instance."""
        self._timestamp = 0
        self._period_sec = self._lower_limit_sec

    def is_ready(self) -> bool:
        """Check whether an exponentially increasing period of time has passed.

        Whenever is_ready() returns True, the timer period is multiplied so that
        it takes longer until is_ready() returns True again.
        Returns:
            bool: True if enough time has passed since one of the following events,
            in relation to an instance of this class:
            - The last time when this method returned True, if it ever did.
            - Or else, when this method was first called after a call to reset().
            - Or else, when this method was first called.
            False otherwise.
        """
        now = monotonic()
        if self._timestamp == 0:
            self._timestamp = now
            return self._initially_ready
        elif now - self._timestamp >= self._period_sec:
            self._timestamp = now
            self._period_sec = max(
                self._lower_limit_sec,
                min(self._upper_limit_sec, self._period_sec * self._multiplier),
            )
            return True

        return False


class IntervalCaller:
    """Repeatedly call a given async action function at a given regular interval.

    Convenience wrapper around Home Assistant's `async_track_time_interval` function.
    """

    def __init__(self, hass: HomeAssistant, interval_sec: float) -> None:
        self._hass = hass
        self._interval_sec = interval_sec
        self._remove_handle: CALLBACK_TYPE | None = None
        self.backoff_timer = BackoffTimer()

    @property
    def interval_sec(self) -> float:
        """Return the calling interval in seconds."""
        return self._interval_sec

    def cancel(self):
        """Cancel the regular calls to the action function."""
        if self._remove_handle:
            self._remove_handle()
            self._remove_handle = None

    def set_async_action(self, action: Callable[[], Awaitable[None]]):
        """Set the async action function to be called at regular intervals."""
        if not self._interval_sec:
            return
        self.cancel()

        async def callback(_time: datetime):
            try:
                _LOGGER.debug(
                    "Calling keep-alive action '%s' (%ss interval)",
                    action.__name__,
                    self._interval_sec,
                )
                await action()
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.error(e)
                self.cancel()

        self._remove_handle = async_track_time_interval(self._hass, callback, timedelta(seconds=self._interval_sec))
