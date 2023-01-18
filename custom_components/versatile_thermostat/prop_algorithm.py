import logging

_LOGGER = logging.getLogger(__name__)

PROPORTIONAL_FUNCTION_ATAN = "atan"
PROPORTIONAL_FUNCTION_LINEAR = "linear"
PROPORTIONAL_FUNCTION_TPI = "tpi"

PROPORTIONAL_MIN_DURATION_SEC = 10

FUNCTION_TYPE = [PROPORTIONAL_FUNCTION_ATAN, PROPORTIONAL_FUNCTION_LINEAR]


class PropAlgorithm:
    """This class aims to do all calculation of the Proportional alogorithm"""

    def __init__(
        self,
        function_type: str,
        tpi_coef_int,
        tpi_coef_ext,
        cycle_min: int,
        minimal_activation_delay: int,
    ):
        """Initialisation of the Proportional Algorithm"""
        _LOGGER.debug(
            "Creation new PropAlgorithm function_type: %s, tpi_coef_int: %s, tpi_coef_ext: %s, cycle_min:%d, minimal_activation_delay:%d",
            function_type,
            tpi_coef_int,
            tpi_coef_ext,
            cycle_min,
            minimal_activation_delay,
        )
        self._function = function_type
        self._tpi_coef_int = tpi_coef_int
        self._tpi_coef_ext = tpi_coef_ext
        self._cycle_min = cycle_min
        self._minimal_activation_delay = minimal_activation_delay
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

            if self._function == PROPORTIONAL_FUNCTION_TPI:
                self._on_percent = (
                    self._tpi_coef_int * delta_temp
                    + self._tpi_coef_ext * delta_ext_temp
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
        if self._on_time_sec < self._minimal_activation_delay:
            if self._on_time_sec > 0:
                _LOGGER.info(
                    "No heating period due to heating period too small (%f < %f)",
                    self._on_time_sec,
                    self._minimal_activation_delay,
                )
            else:
                _LOGGER.debug(
                    "No heating period due to heating period too small (%f < %f)",
                    self._on_time_sec,
                    self._minimal_activation_delay,
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
