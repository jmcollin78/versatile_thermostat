# pylint: disable=line-too-long
"""The Estimated Mobile Average calculation used for temperature slope
and maybe some others feature"""

import logging
import math
from datetime import datetime, tzinfo

_LOGGER = logging.getLogger(__name__)

MIN_TIME_DECAY_SEC = 0

# MAX_ALPHA:
# As for the EMA calculation of irregular time series, I've seen that it might be useful to
# have an upper limit for alpha in case the last measurement was too long ago.
# For example when using a half life of 10 minutes a measurement that is 60 minutes ago
# (if there's nothing inbetween) would contribute to the smoothed value with 1,5%,
# giving the current measurement 98,5% relevance. It could be wise to limit the alpha to e.g. 4x the half life (=0.9375).


class ExponentialMovingAverage:
    """A class that will do the Estimated Mobile Average calculation"""

    def __init__(
        self,
        vterm_name: str,
        halflife: float,
        timezone: tzinfo,
        precision: int = 3,
        max_alpha: float = 0.5,
    ):
        """The halflife is the duration in secondes of a normal cycle"""
        self._halflife: float = halflife
        self._timezone = timezone
        self._current_ema: float = None
        self._last_timestamp: datetime = datetime.now(self._timezone)
        self._name = vterm_name
        self._precision = precision
        self._max_alpha = max_alpha

    def __str__(self) -> str:
        return f"EMA-{self._name}"

    def calculate_ema(self, measurement: float, timestamp: datetime) -> float | None:
        """Calculate the new EMA from a new measurement measured at timestamp
        Return the EMA or None if all parameters are not initialized now
        """

        if measurement is None or timestamp is None:
            _LOGGER.warning(
                "%s - Cannot calculate EMA: measurement and timestamp are mandatory. This message can be normal at startup but should not persist",
                self,
            )
            return measurement

        if self._current_ema is None:
            _LOGGER.debug(
                "%s - First init of the EMA",
                self,
            )
            self._current_ema = measurement
            self._last_timestamp = timestamp
            return self._current_ema

        time_decay = (timestamp - self._last_timestamp).total_seconds()
        if time_decay < MIN_TIME_DECAY_SEC:
            _LOGGER.debug(
                "%s - time_decay %s is too small (< %s). Forget the measurement",
                self,
                time_decay,
                MIN_TIME_DECAY_SEC,
            )
            return self._current_ema

        alpha = 1 - math.exp(math.log(0.5) * time_decay / self._halflife)
        # capping alpha to avoid gap if last measurement was long time ago
        alpha = min(alpha, self._max_alpha)
        new_ema = alpha * measurement + (1 - alpha) * self._current_ema

        self._last_timestamp = timestamp
        self._current_ema = new_ema
        _LOGGER.debug(
            "%s - timestamp=%s alpha=%.2f measurement=%.2f current_ema=%.2f new_ema=%.2f",
            self,
            timestamp,
            alpha,
            measurement,
            self._current_ema,
            new_ema,
        )

        return round(self._current_ema, self._precision)
