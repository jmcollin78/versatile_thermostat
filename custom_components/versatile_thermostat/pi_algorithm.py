# pylint: disable=line-too-long
""" The PI algorithm implementation """

import logging

_LOGGER = logging.getLogger(__name__)


class PITemperatureRegulator:
    """A class implementing a PI Algorithm
    PI algorithms calculate a target temperature by adding an offset which is calculating as follow:
    - offset = kp * error + ki * accumulated_error

    To use it you must:
    - instanciate the class and gives the algorithm parameters: kp, ki, offset_max, accumulated_error_threshold, overheat_protection
    - call calculate_regulated_temperature with the internal, external temperature and time_delta. Time_delta is 1.0 for a standard regulation cycle.
    - call set_target_temp when the target temperature change.
    """

    def __init__(
        self,
        target_temp: float,
        kp: float,
        ki: float,
        k_ext: float,
        offset_max: float,
        accumulated_error_threshold: float,
        overheat_protection: bool,
    ):
        self.target_temp: float = target_temp
        self.kp: float = kp  # proportionnel gain
        self.ki: float = ki  # integral gain
        self.k_ext: float = k_ext  # exterior gain
        self.offset_max: float = offset_max
        self.accumulated_error: float = 0
        self.accumulated_error_threshold: float = accumulated_error_threshold
        self.overheat_protection: bool = overheat_protection

    def reset_accumulated_error(self):
        """Reset the accumulated error"""
        self.accumulated_error = 0

    def set_accumulated_error(self, accumulated_error):
        """Allow to persist and restore the accumulated_error"""
        self.accumulated_error = accumulated_error

    def set_target_temp(self, target_temp):
        """Set the new target_temp"""
        self.target_temp = target_temp
        # Discussion #191. After a target change we should reset the accumulated error which is certainly wrong now.
        # Discussion #384. Finally don't reset the accumulated error but smoothly reset it if the sign is inversed
        # if self.accumulated_error < 0:
        #     self.accumulated_error = 0

    def calculate_regulated_temperature(self, room_temp: float | None, external_temp: float | None, time_delta: float):  # pylint: disable=unused-argument
        """Calculate a new target_temp given some temperature"""
        if room_temp is None:
            _LOGGER.warning(
                "Temporarily skipping the self-regulation algorithm while the configured sensor for room temperature is unavailable"
            )
            return self.target_temp
        if external_temp is None:
            _LOGGER.warning(
                "Temporarily skipping the self-regulation algorithm while the configured sensor for outdoor temperature is unavailable"
            )
            return self.target_temp
        if time_delta > 2.0:
            _LOGGER.info(
                "The time delta (%.2f) is too high for the self-regulation algorithm. Capping to 1.0.",
                time_delta,
            )
            time_delta = 1.0

        # Calculate the error factor (P)
        error = self.target_temp - room_temp

        # Calculate the sum of error (I)
        # Discussion #384. Finally don't reset the accumulated error but smoothly reset it if the sign is inversed
        # If the error have change its sign, reset smoothly the accumulated error
        if self.overheat_protection and error * self.accumulated_error < 0:
            self.accumulated_error = self.accumulated_error / (2.0 * time_delta)

        self.accumulated_error += error * time_delta

        # Capping of the error
        self.accumulated_error = min(
            self.accumulated_error_threshold,
            max(-self.accumulated_error_threshold, self.accumulated_error),
        )

        # Calculate the offset (proportionnel + intégral)
        offset = self.kp * error + self.ki * self.accumulated_error

        # Calculate the exterior offset
        offset_ext = self.k_ext * (room_temp - external_temp)

        # Capping of offset
        total_offset = offset + offset_ext
        total_offset = min(self.offset_max, max(-self.offset_max, total_offset))

        result = round(self.target_temp + total_offset, 1)

        _LOGGER.debug(
            "PITemperatureRegulator - Error: %.2f accumulated_error: %.2f (overheat protection %s and delta %.2f) offset: %.2f offset_ext: %.2f target_tem: %.1f regulatedTemp: %.1f",
            error,
            self.accumulated_error,
            self.overheat_protection,
            time_delta,
            offset,
            offset_ext,
            self.target_temp,
            result,
        )

        return result
