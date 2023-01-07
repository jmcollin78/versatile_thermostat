import logging
import math

_LOGGER = logging.getLogger(__name__)

PROPORTIONAL_FUNCTION_ATAN = "atan"
PROPORTIONAL_FUNCTION_LINEAR = "linear"
PROPORTIONAL_FUNCTION_TPI = "tpi"

PROPORTIONAL_MIN_DURATION_SEC = 10

FUNCTION_TYPE = [PROPORTIONAL_FUNCTION_ATAN, PROPORTIONAL_FUNCTION_LINEAR]


class PropAlgorithm:
    """This class aims to do all calculation of the Proportional alogorithm"""

    def __init__(
        self, function_type: str, bias: float, tpi_coefc, tpi_coeft, cycle_min: int
    ):
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
        self._tpi_coefc = tpi_coefc
        self._tpi_coeft = tpi_coeft
        self._cycle_min = cycle_min
        self._on_percent = 0
        self._on_time_sec = 0
        self._off_time_sec = self._cycle_min * 60

    def calculate(
        self, target_temp: float, current_temp: float, ext_current_temp: float
    ):
        """Do the calculation of the duration"""
        if target_temp is None or current_temp is None:
            _LOGGER.warning(
                "Proportional algorithm: calculation is not possible cause target_temp or current_temp is null. Heating will be disabled"  # pylint: disable=line-too-long
            )
            self._on_percent = 0
        else:
            delta_temp = target_temp - current_temp
            delta_ext_temp = (
                target_temp - ext_current_temp if ext_current_temp is not None else 0
            )

            if self._function == PROPORTIONAL_FUNCTION_LINEAR:
                self._on_percent = 0.25 * delta_temp + self._bias
            elif self._function == PROPORTIONAL_FUNCTION_ATAN:
                self._on_percent = math.atan(delta_temp + self._bias) / 1.4
            elif self._function == PROPORTIONAL_FUNCTION_TPI:
                self._on_percent = (
                    self._tpi_coefc * delta_temp + self._tpi_coeft * delta_ext_temp
                )
            else:
                _LOGGER.warning(
                    "Proportional algorithm: unknown %s function. Heating will be disabled",
                    self._function,
                )
                self._on_percent = 0

        # calculated on_time duration in seconds
        if self._on_percent > 1:
            self._on_percent = 1
        if self._on_percent < 0:
            self._on_percent = 0
        self._on_time_sec = self._on_percent * self._cycle_min * 60

        # Do not heat for less than xx sec
        if self._on_time_sec < PROPORTIONAL_MIN_DURATION_SEC:
            _LOGGER.debug(
                "No heating period due to heating period too small (%f < %f)",
                self._on_time_sec,
                PROPORTIONAL_MIN_DURATION_SEC,
            )
            self._on_time_sec = 0

        self._off_time_sec = self._cycle_min * 60 - self._on_time_sec

        _LOGGER.debug(
            "heating percent calculated for current_temp %.1f, ext_current_temp %.1f and target_temp %.1f is %.2f, on_time is %d (sec), off_time is %d (sec)",  # pylint: disable=line-too-long
            current_temp if current_temp else -9999.0,
            ext_current_temp if ext_current_temp else -9999.0,
            target_temp if target_temp else -9999.0,
            self._on_percent,
            self.on_time_sec,
            self.off_time_sec,
        )

    @property
    def on_percent(self) -> float:
        """Returns the percentage the heater must be ON (1 means the heater will be always on, 0 never on)"""  # pylint: disable=line-too-long
        return round(self._on_percent, 2)

    @property
    def on_time_sec(self) -> int:
        """Returns the calculated time in sec the heater must be ON"""
        return int(self._on_time_sec)

    @property
    def off_time_sec(self) -> int:
        """Returns the calculated time in sec the heater must be OFF"""
        return int(self._off_time_sec)
