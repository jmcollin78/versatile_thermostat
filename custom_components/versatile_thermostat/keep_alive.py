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

from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers.event import async_track_time_interval


_LOGGER = logging.getLogger(__name__)


class IntervalCaller:
    """Repeatedly call a given async action function at a given regular interval.

    Convenience wrapper around Home Assistant's `async_track_time_interval` function.
    """

    def __init__(self, hass: HomeAssistant, interval_sec: int) -> None:
        self._hass = hass
        self._interval_sec = interval_sec
        self._remove_handle: CALLBACK_TYPE | None = None

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
                _LOGGER.debug("Calling keep-alive action")
                await action()
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.error(e)
                self.cancel()

        self._remove_handle = async_track_time_interval(
            self._hass, callback, timedelta(seconds=self._interval_sec)
        )
