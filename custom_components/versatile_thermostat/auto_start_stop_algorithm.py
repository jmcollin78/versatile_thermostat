# pylint: disable=line-too-long
""" This file implements the Auto start/stop algorithm as described here: https://github.com/jmcollin78/versatile_thermostat/issues/585
"""

import logging

from homeassistant.components.climate import HVACMode

from .const import (
    AUTO_START_STOP_LEVEL_NONE,
    AUTO_START_STOP_LEVEL_FAST,
    AUTO_START_STOP_LEVEL_MEDIUM,
    AUTO_START_STOP_LEVEL_SLOW,
    CONF_AUTO_START_STOP_LEVELS,
)


_LOGGER = logging.getLogger(__name__)

# attribute name should be equal to AUTO_START_STOP_LEVEL_xxx constants (in const.yaml)
DTEMP = {
    AUTO_START_STOP_LEVEL_NONE: 99,
    AUTO_START_STOP_LEVEL_SLOW: 3,
    AUTO_START_STOP_LEVEL_MEDIUM: 2,
    AUTO_START_STOP_LEVEL_FAST: 1,
}
DT_MIN = {
    AUTO_START_STOP_LEVEL_NONE: 99,
    AUTO_START_STOP_LEVEL_SLOW: 30,
    AUTO_START_STOP_LEVEL_MEDIUM: 15,
    AUTO_START_STOP_LEVEL_FAST: 7,
}

AUTO_START_STOP_ACTION_OFF = "turnOff"
AUTO_START_STOP_ACTION_ON = "turnOn"
AUTO_START_STOP_ACTION_NOTHING = "nothing"
AUTO_START_STOP_ACTIONS = [
    AUTO_START_STOP_ACTION_OFF,
    AUTO_START_STOP_ACTION_ON,
    AUTO_START_STOP_ACTION_NOTHING,
]


class AutoStartStopDetectionAlgorithm:
    """The class that implements the algorithm listed above"""

    _dt: float
    _dtemp: float
    _level: str

    def __init__(self, level: CONF_AUTO_START_STOP_LEVELS, vtherm_name) -> None:
        """Initalize a new algorithm with the right constants"""
        self._level = level
        self._dt = DT_MIN[level]
        self._dtemp = DTEMP[level]
        self._vtherm_name = vtherm_name

    def calculate_action(
        self,
        hvac_mode: HVACMode | None,
        saved_hvac_mode: HVACMode | None,
        regulated_temp: float,
        target_temp: float,
        current_temp: float,
        slope_min: float,
    ) -> AUTO_START_STOP_ACTIONS:
        """Calculate an eventual action to do depending of the value in parameter"""
        if self._level == AUTO_START_STOP_LEVEL_NONE:
            _LOGGER.debug(
                "%s - auto-start/stop is disabled",
                self,
            )
            return AUTO_START_STOP_ACTION_NOTHING

        if (
            hvac_mode is None
            or regulated_temp is None
            or target_temp is None
            or current_temp is None
            or slope_min is None
        ):
            _LOGGER.debug(
                "%s - No all mandatory parameters are set. Disable auto-start/stop",
                self,
            )
            return AUTO_START_STOP_ACTION_NOTHING

        _LOGGER.debug(
            "%s - calculate_action: hvac_mode=%s, saved_hvac_mode=%s, regulated_temp=%s, target_temp=%s, current_temp=%s, slope_min=%s",
            self,
            hvac_mode,
            saved_hvac_mode,
            regulated_temp,
            target_temp,
            current_temp,
            slope_min,
        )

        if hvac_mode == HVACMode.HEAT:
            if regulated_temp + self._dtemp <= target_temp and slope_min >= 0:
                _LOGGER.info(
                    "%s - We need to stop, there is no need for heating for a long time.",
                )
                return AUTO_START_STOP_ACTION_OFF
            else:
                _LOGGER.debug(
                    "%s - nothing to do, we are heating",
                )
                return AUTO_START_STOP_ACTION_NOTHING

        if hvac_mode == HVACMode.COOL:
            if regulated_temp - self._dtemp >= target_temp and slope_min <= 0:
                _LOGGER.info(
                    "%s - We need to stop, there is no need for cooling for a long time.",
                )
                return AUTO_START_STOP_ACTION_OFF
            else:
                _LOGGER.debug(
                    "%s - nothing to do, we are cooling",
                )
                return AUTO_START_STOP_ACTION_NOTHING

        if hvac_mode == HVACMode.OFF and saved_hvac_mode == HVACMode.HEAT:
            if current_temp + slope_min * self._dt <= target_temp:
                _LOGGER.info(
                    "%s - We need to start, because it will be time to heat",
                )
                return AUTO_START_STOP_ACTION_ON
            else:
                _LOGGER.debug(
                    "%s - nothing to do, we don't need to heat soon",
                )
                return AUTO_START_STOP_ACTION_NOTHING

        if hvac_mode == HVACMode.OFF and saved_hvac_mode == HVACMode.COOL:
            if current_temp + slope_min * self._dt >= target_temp:
                _LOGGER.info(
                    "%s - We need to start, because it will be time to cool",
                )
                return AUTO_START_STOP_ACTION_ON
            else:
                _LOGGER.debug(
                    "%s - nothing to do, we don't need to cool soon",
                )
                return AUTO_START_STOP_ACTION_NOTHING

        _LOGGER.debug(
            "%s - nothing to do, no conditions applied",
        )
        return AUTO_START_STOP_ACTION_NOTHING

    def __str__(self) -> str:
        return f"AutoStartStopDetectionAlgorithm-{self._vtherm_name}"
