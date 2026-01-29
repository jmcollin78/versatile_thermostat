""" The TPI calculation module """
# pylint: disable='line-too-long'
import logging

from .vtherm_hvac_mode import VThermHvacMode, VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_SLEEP

_LOGGER = logging.getLogger(__name__)




def is_number(value):
    """check if value is a number"""
    return isinstance(value, (int, float))


class TpiAlgorithm:
    """This class aims to do all calculation of the Proportional alogorithm"""

    def __init__(
        self,

        tpi_coef_int,
        tpi_coef_ext,
        vtherm_entity_id: str = None,
        max_on_percent: float = None,
        tpi_threshold_low: float = 0.0,
        tpi_threshold_high: float = 0.0,
    ) -> None:
        """Initialisation of the Proportional Algorithm"""
        _LOGGER.debug(
            "%s - Creation new TpiAlgorithm tpi_coef_int: %s, tpi_coef_ext: %s, tpi_threshold_low=%s, tpi_threshold_high=%s",  # pylint: disable=line-too-long
            vtherm_entity_id,

            tpi_coef_int,
            tpi_coef_ext,
            tpi_threshold_low,
            tpi_threshold_high,
        )

        # Issue 506 - check parameters
        if (
            vtherm_entity_id is None
            or not is_number(tpi_coef_int)
            or not is_number(tpi_coef_ext)
        ):
            _LOGGER.error(
                "%s - configuration is wrong. entity_id is %s, tpi_coef_int is %s, tpi_coef_ext is %s",
                vtherm_entity_id,
                vtherm_entity_id,
                tpi_coef_int,
                tpi_coef_ext,
            )
            raise TypeError(
                "TPI parameters are not set correctly. VTherm will not work as expected. Please reconfigure it correctly. See previous log for values"
            )

        self._vtherm_entity_id = vtherm_entity_id

        self._tpi_coef_int = tpi_coef_int
        self._tpi_coef_ext = tpi_coef_ext
        self._on_percent = 0
        self._calculated_on_percent = 0
        self._safety = False
        self._default_on_percent = 0
        self._max_on_percent = max_on_percent
        self._tpi_threshold_low = tpi_threshold_low
        self._tpi_threshold_high = tpi_threshold_high
        self._apply_threshold = tpi_threshold_low != 0.0 and tpi_threshold_high != 0.0

    def calculate(
        self,
        target_temp: float | None,
        current_temp: float | None,
        ext_current_temp: float | None,
        slope: float | None,
        hvac_mode: VThermHvacMode,
    ):
        """Do the calculation of the duration"""
        if target_temp is None or current_temp is None:
            log = _LOGGER.debug if hvac_mode == VThermHvacMode_OFF else _LOGGER.warning
            log(
                "%s - Proportional algorithm: calculation is not possible cause target_temp (%s) or current_temp (%s) is null. Heating/cooling will be disabled. This could be normal at startup",  # pylint: disable=line-too-long
                self._vtherm_entity_id,
                target_temp,
                current_temp,
            )
            self._calculated_on_percent = 0
        else:
            if hvac_mode == VThermHvacMode_COOL:
                delta_temp = current_temp - target_temp
                delta_ext_temp = ext_current_temp - target_temp if ext_current_temp is not None else 0
                slope = -slope if slope is not None else None
            else:
                delta_temp = target_temp - current_temp
                delta_ext_temp = target_temp - ext_current_temp if ext_current_temp is not None else 0

            # Apply thresholds
            if (
                # fmt: off
                self._apply_threshold
                and slope is not None
                and ((slope > 0.0 and -delta_temp > self._tpi_threshold_high)
                or (slope < 0.0 and -delta_temp > self._tpi_threshold_low))
                # fmt: on
            ):
                _LOGGER.debug(
                    "%s - Proportional algorithm: on_percent is forced to 0 cause current_temp (%.1f) is outside the thresholds (slope=%.1f, target_temp=%.1f, tpi_threshold_low=%.1f, tpi_threshold_high=%.1f). Heating/cooling will be disabled.",  # pylint: disable=line-too-long
                    self._vtherm_entity_id,
                    current_temp,
                    slope,
                    target_temp,
                    self._tpi_threshold_low,
                    self._tpi_threshold_high,
                )
                self._calculated_on_percent = 0
            else:
                if hvac_mode not in [VThermHvacMode_OFF, VThermHvacMode_SLEEP]:
                    self._calculated_on_percent = self._tpi_coef_int * delta_temp + self._tpi_coef_ext * delta_ext_temp
                else:
                    _LOGGER.debug(
                        "%s - Proportional algorithm: VTherm is off. Heating will be disabled",
                        self._vtherm_entity_id,
                    )
                    self._calculated_on_percent = 0

        self._calculate_internal()

        _LOGGER.debug(
            "%s - heating percent calculated for current_temp %.1f, ext_current_temp %.1f and target_temp %.1f is %.2f",  # pylint: disable=line-too-long
            self._vtherm_entity_id,
            current_temp if current_temp else -9999.0,
            ext_current_temp if ext_current_temp else -9999.0,
            target_temp if target_temp else -9999.0,
            self._calculated_on_percent,
        )

    def _calculate_internal(self):
        """Finish the calculation to get the on_percent"""

        # calculated on_time duration in seconds
        if self._calculated_on_percent > 1:
            self._calculated_on_percent = 1
        if self._calculated_on_percent < 0:
            self._calculated_on_percent = 0

        if self._safety:
            self._on_percent = self._default_on_percent
            _LOGGER.info(
                "%s - Security is On using the default_on_percent %f",
                self._vtherm_entity_id,
                self._on_percent,
            )
        else:
            _LOGGER.debug(
                "Safety is Off using the calculated_on_percent %f",
                self._calculated_on_percent,
            )
            self._on_percent = self._calculated_on_percent

        if self._max_on_percent is not None and self._on_percent > self._max_on_percent:
            _LOGGER.debug(
                "%s - Heating period clamped to %s (instead of %s) due to max_on_percent setting.",
                self._vtherm_entity_id,
                self._max_on_percent,
                self._on_percent,
            )
            self._on_percent = self._max_on_percent

    def set_safety(self, default_on_percent: float):
        """Set a default value for on_percent (used for safety mode)"""
        _LOGGER.info("%s - Proportional Algo - set safety to ON", self._vtherm_entity_id)
        self._safety = True
        self._default_on_percent = default_on_percent
        self._calculate_internal()

    def unset_safety(self):
        """Unset the safety mode"""
        _LOGGER.info("%s - Proportional Algo - set safety to OFF", self._vtherm_entity_id)
        self._safety = False
        self._calculate_internal()

    def update_parameters(
        self,
        tpi_coef_int=None,
        tpi_coef_ext=None,
        tpi_threshold_low=None,
        tpi_threshold_high=None,
    ):
        """Update the parameters of the algorithm"""
        if tpi_coef_int is not None:
            self._tpi_coef_int = tpi_coef_int
        if tpi_coef_ext is not None:
            self._tpi_coef_ext = tpi_coef_ext
        if tpi_threshold_low is not None:
            self._tpi_threshold_low = tpi_threshold_low
        if tpi_threshold_high is not None:
            self._tpi_threshold_high = tpi_threshold_high

        self._apply_threshold = self._tpi_threshold_low != 0.0 and self._tpi_threshold_high != 0.0
        _LOGGER.debug(
            "%s - Parameters updated. tpi_coef_int: %s, tpi_coef_ext: %s, tpi_threshold_low: %s, tpi_threshold_high: %s",
            self._vtherm_entity_id,
            self._tpi_coef_int,
            self._tpi_coef_ext,
            self._tpi_threshold_low,
            self._tpi_threshold_high,
        )

    @property
    def on_percent(self) -> float:
        """Returns the percentage the heater must be ON
        In safety mode this value is overriden with the _default_on_percent
        (1 means the heater will be always on, 0 never on)"""  # pylint: disable=line-too-long
        return round(self._on_percent, 2)

    @property
    def calculated_on_percent(self) -> float:
        """Returns the calculated percentage the heater must be ON
        Calculated means NOT overriden even in safety mode
        (1 means the heater will be always on, 0 never on)"""  # pylint: disable=line-too-long
        return round(self._calculated_on_percent, 2)

    @property
    def tpi_coef_int(self) -> float:
        """Returns the TPI coefficient int"""
        return self._tpi_coef_int

    @property
    def tpi_coef_ext(self) -> float:
        """Returns the TPI coefficient ext"""
        return self._tpi_coef_ext

    @property
    def tpi_threshold_low(self) -> float:
        """Returns the TPI threshold low"""
        return self._tpi_threshold_low

    @property
    def tpi_threshold_high(self) -> float:
        """Returns the TPI threshold high"""
        return self._tpi_threshold_high

