# pylint: disable=line-too-long
""" This file implements the Auto start/stop algorithm as described here: https://github.com/jmcollin78/versatile_thermostat/issues/585
"""

import logging
from datetime import datetime
from typing import Literal

from .vtherm_hvac_mode import VThermHvacMode, VThermHvacMode_HEAT, VThermHvacMode_COOL, VThermHvacMode_OFF

from .const import (
    AUTO_START_STOP_LEVEL_NONE,
    AUTO_START_STOP_LEVEL_FAST,
    AUTO_START_STOP_LEVEL_MEDIUM,
    AUTO_START_STOP_LEVEL_SLOW,
    AUTO_START_STOP_LEVEL_VERY_SLOW,
    TYPE_AUTO_START_STOP_LEVELS,
)


_LOGGER = logging.getLogger(__name__)

# Some constant to make algorithm depending of level
DT_MIN = {
    AUTO_START_STOP_LEVEL_NONE: 0,  # Not used
    AUTO_START_STOP_LEVEL_VERY_SLOW: 60,
    AUTO_START_STOP_LEVEL_SLOW: 30,
    AUTO_START_STOP_LEVEL_MEDIUM: 15,
    AUTO_START_STOP_LEVEL_FAST: 7,
}

# the measurement cycle (2 min)
CYCLE_SEC = 120

# A temp hysteresis to avoid rapid OFF/ON
TEMP_HYSTERESIS = 0.5

ERROR_THRESHOLD = {
    AUTO_START_STOP_LEVEL_NONE: 0,  # Not used
    AUTO_START_STOP_LEVEL_VERY_SLOW: 20,  # 20 cycle above 1° or 10 cycle above 2°, ...
    AUTO_START_STOP_LEVEL_SLOW: 10,  # 10 cycle above 1° or 5 cycle above 2°, ...
    AUTO_START_STOP_LEVEL_MEDIUM: 5,  # 5 cycle above 1° or 3 cycle above 2°, ..., 1 cycle above 5°
    AUTO_START_STOP_LEVEL_FAST: 2,  # 2 cycle above 1° or 1 cycle above 2°
}

AUTO_START_STOP_ACTION_OFF = "turnOff"
AUTO_START_STOP_ACTION_ON = "turnOn"
AUTO_START_STOP_ACTION_NOTHING = "nothing"
AUTO_START_STOP_ACTIONS = Literal[  # pylint: disable=invalid-name
    AUTO_START_STOP_ACTION_OFF,
    AUTO_START_STOP_ACTION_ON,
    AUTO_START_STOP_ACTION_NOTHING,
]

class AutoStartStopDetectionAlgorithm:
    """The class that implements the algorithm listed above"""

    _dt: float | None = None
    _level: str = AUTO_START_STOP_LEVEL_NONE
    _accumulated_error: float = 0
    _error_threshold: float | None = None
    _last_calculation_date: datetime | None = None
    _last_switch_date: datetime | None = None

    def __init__(self, level: TYPE_AUTO_START_STOP_LEVELS, vtherm_name: str):
        """Initalize a new algorithm with the right constants"""
        self._vtherm_name: str = vtherm_name
        self._last_calculation_date: datetime | None = None
        self._last_switch_date: datetime | None = None
        self._init_level(level)
        self._last_should_be_off: bool = False

    def _init_level(self, level: TYPE_AUTO_START_STOP_LEVELS):
        """Initialize a new level"""
        if level == self._level:
            return

        self._level = level
        if self._level != AUTO_START_STOP_LEVEL_NONE:
            self._dt = DT_MIN[level]
            self._error_threshold = ERROR_THRESHOLD[level]
            # reset accumulated error if we change the level
            self._accumulated_error = 0

    def should_be_turned_off(self, requested_hvac_mode: VThermHvacMode, target_temp: float, current_temp: float, slope_min: float | None, now: datetime) -> bool | None:
        """Check auto-start/stop state should be triggered
        Return True if the device should be turned off, False if the device should not be turned off
        """

        if self._level == AUTO_START_STOP_LEVEL_NONE:
            _LOGGER.debug(
                "%s - auto-start/stop is disabled",
                self,
            )
            self._last_should_be_off = False
            return self._last_should_be_off

        _LOGGER.debug(
            "%s - calculate_action: requested_hvac_mode=%s, target_temp=%s, current_temp=%s, slope_min=%s at %s",
            self,
            requested_hvac_mode,
            target_temp,
            current_temp,
            slope_min,
            now,
        )

        if requested_hvac_mode is None or target_temp is None or current_temp is None:
            _LOGGER.debug(
                "%s - No all mandatory parameters are set. Disable auto-start/stop",
                self,
            )
            self._last_should_be_off = False
            return self._last_should_be_off

        # Calculate the error factor (P)
        error = target_temp - current_temp

        # reduce the error considering the dt between the last measurement
        if self._last_calculation_date is not None:
            dtmin = (now - self._last_calculation_date).total_seconds() / CYCLE_SEC
            # ignore two calls too near (< 24 sec)
            if dtmin <= 0.2:
                _LOGGER.debug(
                    "%s - new calculation of auto_start_stop (%s) is too near of the last one (%s). Forget it",
                    self,
                    now,
                    self._last_calculation_date,
                )
                return self._last_should_be_off
            error = error * dtmin

        # If the error have change its sign, reset smoothly the accumulated error
        if error * self._accumulated_error < 0:
            self._accumulated_error = self._accumulated_error / 2.0

        self._accumulated_error += error

        # Capping of the error
        self._accumulated_error = min(
            self._error_threshold,
            max(-self._error_threshold, self._accumulated_error),
        )

        self._last_calculation_date = now

        temp_at_dt = current_temp + slope_min * self._dt

        # Calculate the number of minute from last_switch
        nb_minutes_since_last_switch = 999
        if self._last_switch_date is not None:
            nb_minutes_since_last_switch = (
                now - self._last_switch_date
            ).total_seconds() / 60

        # Check to turn-off
        # When we hit the threshold, that mean we can turn off
        if requested_hvac_mode == VThermHvacMode_HEAT:
            if self._accumulated_error <= -self._error_threshold and temp_at_dt >= target_temp + TEMP_HYSTERESIS and nb_minutes_since_last_switch >= self._dt:
                _LOGGER.info(
                    "%s - auto-start/stop: We need to stop, there is no need for heating for a long time.",
                    self,
                )
                self._last_switch_date = now
                self._last_should_be_off = True
            elif temp_at_dt <= target_temp - TEMP_HYSTERESIS and nb_minutes_since_last_switch >= self._dt:
                _LOGGER.info(
                    "%s - auto-start/stop: We need to start heating.",
                    self,
                )
                self._last_switch_date = now
                self._last_should_be_off = False

        elif requested_hvac_mode == VThermHvacMode_COOL:
            if self._accumulated_error >= self._error_threshold and temp_at_dt <= target_temp - TEMP_HYSTERESIS and nb_minutes_since_last_switch >= self._dt:
                _LOGGER.info(
                    "%s - We need to stop, there is no need for cooling for a long time.",
                    self,
                )
                self._last_switch_date = now
                self._last_should_be_off = True

            elif temp_at_dt >= target_temp + TEMP_HYSTERESIS and nb_minutes_since_last_switch >= self._dt:
                _LOGGER.info(
                    "%s - We need to start cooling.",
                    self,
                )
                self._last_switch_date = now
                self._last_should_be_off = False

        _LOGGER.debug("%s - nothing to do, requested hvac_mode is %s", self, requested_hvac_mode)
        return self._last_should_be_off

    # def calculate_action(
    #     self,
    #     hvac_mode: VThermHvacMode | None,
    #     saved_hvac_mode: VThermHvacMode | None,
    #     target_temp: float,
    #     current_temp: float,
    #     slope_min: float | None,
    #     now: datetime,
    # ) -> AUTO_START_STOP_ACTIONS:
    #     """Calculate an eventual action to do depending of the value in parameter"""

    #     # Check to turn-off
    #     # When we hit the threshold, that mean we can turn off
    #     if hvac_mode == VThermHvacMode_HEAT:
    #         if (
    #             self._accumulated_error <= -self._error_threshold
    #             and temp_at_dt >= target_temp + TEMP_HYSTERESIS
    #             and nb_minutes_since_last_switch >= self._dt
    #         ):
    #             _LOGGER.info(
    #                 "%s - We need to stop, there is no need for heating for a long time.",
    #                 self,
    #             )
    #             self._last_switch_date = now
    #             return AUTO_START_STOP_ACTION_OFF
    #         else:
    #             _LOGGER.debug("%s - nothing to do, we are heating", self)
    #             return AUTO_START_STOP_ACTION_NOTHING

    #     if hvac_mode == VThermHvacMode_COOL:
    #         if (
    #             self._accumulated_error >= self._error_threshold
    #             and temp_at_dt <= target_temp - TEMP_HYSTERESIS
    #             and nb_minutes_since_last_switch >= self._dt
    #         ):
    #             _LOGGER.info(
    #                 "%s - We need to stop, there is no need for cooling for a long time.",
    #                 self,
    #             )
    #             self._last_switch_date = now
    #             return AUTO_START_STOP_ACTION_OFF
    #         else:
    #             _LOGGER.debug(
    #                 "%s - nothing to do, we are cooling",
    #                 self,
    #             )
    #             return AUTO_START_STOP_ACTION_NOTHING

    #     # check to turn on
    #     if hvac_mode == VThermHvacMode_OFF and saved_hvac_mode == VThermHvacMode_HEAT:
    #         if (
    #             temp_at_dt <= target_temp - TEMP_HYSTERESIS
    #             and nb_minutes_since_last_switch >= self._dt
    #         ):
    #             _LOGGER.info(
    #                 "%s - We need to start, because it will be time to heat",
    #                 self,
    #             )
    #             self._last_switch_date = now
    #             return AUTO_START_STOP_ACTION_ON
    #         else:
    #             _LOGGER.debug(
    #                 "%s - nothing to do, we don't need to heat soon",
    #                 self,
    #             )
    #             return AUTO_START_STOP_ACTION_NOTHING

    #     if hvac_mode == VThermHvacMode_OFF and saved_hvac_mode == VThermHvacMode_COOL:
    #         if (
    #             temp_at_dt >= target_temp + TEMP_HYSTERESIS
    #             and nb_minutes_since_last_switch >= self._dt
    #         ):
    #             _LOGGER.info(
    #                 "%s - We need to start, because it will be time to cool",
    #                 self,
    #             )
    #             self._last_switch_date = now
    #             return AUTO_START_STOP_ACTION_ON
    #         else:
    #             _LOGGER.debug(
    #                 "%s - nothing to do, we don't need to cool soon",
    #                 self,
    #             )
    #             return AUTO_START_STOP_ACTION_NOTHING

    #     _LOGGER.debug(
    #         "%s - nothing to do, no conditions applied",
    #         self,
    #     )
    #     return AUTO_START_STOP_ACTION_NOTHING

    def set_level(self, level: TYPE_AUTO_START_STOP_LEVELS):
        """Set a new level"""
        self._init_level(level)

    @property
    def dt_min(self) -> float:
        """Get the dt value"""
        return self._dt

    @property
    def accumulated_error(self) -> float:
        """Get the accumulated error value"""
        return self._accumulated_error

    @property
    def accumulated_error_threshold(self) -> float:
        """Get the accumulated error threshold value"""
        return self._error_threshold

    @property
    def level(self) -> TYPE_AUTO_START_STOP_LEVELS:
        """Get the level value"""
        return self._level

    @property
    def last_switch_date(self) -> datetime | None:
        """Get the last of the last switch"""
        return self._last_switch_date

    def __str__(self) -> str:
        return f"AutoStartStopDetectionAlgorithm-{self._vtherm_name}"
