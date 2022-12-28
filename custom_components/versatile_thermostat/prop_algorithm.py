import logging
import math

_LOGGER = logging.getLogger(__name__)

PROPORTIONAL_FUNCTION_ATAN = "atan"
PROPORTIONAL_FUNCTION_LINEAR = "linear"

PROPORTIONAL_MIN_DURATION_SEC = 10

FUNCTION_TYPE = [PROPORTIONAL_FUNCTION_ATAN, PROPORTIONAL_FUNCTION_LINEAR]


class PropAlgorithm:
    """This class aims to do all calculation of the Proportional alogorithm"""

    def __init__(self, function_type: str, bias: float, cycle_min: int):
        """Initialisation of the Proportional Algorithm"""
        _LOGGER.debug(
            "Creation new PropAlgorithm function_type: %s, bias: %f, cycle_min:%d",
            function_type,
            bias,
            cycle_min,
        )
        # TODO test function_type, bias, cycle_min
        self._function = function_type
        self._bias = bias
        self._cycle_min = cycle_min
        self._on_time_sec = 0
        self._off_time_sec = self._cycle_min * 60

    def calculate(self, target_temp: float, current_temp: float):
        """Do the calculation of the duration"""
        if target_temp is None or current_temp is None:
            _LOGGER.warning(
                "Proportional algorithm: calculation is not possible cause target_temp or current_temp is null. Heating will be disabled"
            )
            on_percent = 0
        else:
            delta_temp = target_temp - current_temp
            if self._function == PROPORTIONAL_FUNCTION_LINEAR:
                on_percent = 0.25 * delta_temp + self._bias
            elif self._function == PROPORTIONAL_FUNCTION_ATAN:
                on_percent = math.atan(delta_temp + self._bias) / 1.4
            else:
                _LOGGER.warning(
                    "Proportional algorithm: unknown %s function. Heating will be disabled",
                    self._function,
                )
                on_percent = 0

        # calculated on_time duration in seconds
        if on_percent > 1:
            on_percent = 1
        self._on_time_sec = on_percent * self._cycle_min * 60

        # Do not heat for less than xx sec
        if self._on_time_sec < PROPORTIONAL_MIN_DURATION_SEC:
            _LOGGER.debug(
                "No heating period due to heating period too small (%f < %f)",
                self._on_time_sec,
                PROPORTIONAL_MIN_DURATION_SEC,
            )
            self._on_time_sec = 0

        self._off_time_sec = (1.0 - on_percent) * self._cycle_min * 60

        _LOGGER.debug(
            "heating percent calculated is %f, on_time is %f (sec), off_time is %s (sec)",
            on_percent,
            self._on_time_sec,
            self._off_time_sec,
        )

    @property
    def on_time_sec(self):
        """Returns the calculated time in sec the heater must be ON"""
        return self._on_time_sec

    @property
    def off_time_sec(self):
        """Returns the calculated time in sec the heater must be OFF"""
        return self._off_time_sec
