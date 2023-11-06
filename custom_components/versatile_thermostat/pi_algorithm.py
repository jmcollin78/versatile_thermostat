# pylint: disable=line-too-long
""" The PI algorithm implementation """

import logging

_LOGGER = logging.getLogger(__name__)


class PITemperatureRegulator:
    """A class implementing a PI Algorithm
    PI algorithms calculate a target temperature by adding an offset which is calculating as follow:
    - offset = kp * error + ki * accumulated_error

    To use it you must:
    - instanciate the class and gives the algorithm parameters: kp, ki, offset_max, stabilization_threshold, accumulated_error_threshold
    - call calculate_regulated_temperature with the internal and external temperature
    - call set_target_temp when the target temperature change.
    """

    def __init__(
        self,
        target_temp: float,
        kp: float,
        ki: float,
        k_ext: float,
        offset_max: float,
        stabilization_threshold: float,
        accumulated_error_threshold: float,
    ):
        self.target_temp: float = target_temp
        self.kp: float = kp  # proportionnel gain
        self.ki: float = ki  # integral gain
        self.k_ext: float = k_ext  # exterior gain
        self.offset_max: float = offset_max
        self.stabilization_threshold: float = stabilization_threshold
        self.accumulated_error: float = 0
        self.accumulated_error_threshold: float = accumulated_error_threshold

    def reset_accumulated_error(self):
        """Reset the accumulated error"""
        self.accumulated_error = 0

    def set_target_temp(self, target_temp):
        """Set the new target_temp"""
        self.target_temp = target_temp
        # Do not reset the accumulated error
        # self.accumulated_error = 0

    def calculate_regulated_temperature(
        self, internal_temp: float, external_temp: float
    ):  # pylint: disable=unused-argument
        """Calculate a new target_temp given some temperature"""
        if internal_temp is None:
            _LOGGER.warning(
                "Temporarily skipping the self-regulation algorithm while the configured sensor for room temperature is unavailable"
            )
            return self.target_temp
        if external_temp is None:
            _LOGGER.warning(
                "Temporarily skipping the self-regulation algorithm while the configured sensor for outdoor temperature is unavailable"
            )
            return self.target_temp

        # Calculate the error factor (P)
        error = self.target_temp - internal_temp

        # Calculate the sum of error (I)
        self.accumulated_error += error

        # Capping of the error
        self.accumulated_error = min(
            self.accumulated_error_threshold,
            max(-self.accumulated_error_threshold, self.accumulated_error),
        )

        # Calculate the offset (proportionnel + intégral)
        offset = self.kp * error + self.ki * self.accumulated_error

        # Calculate the exterior offset
        # For Maia tests - use the internal_temp vs external_temp and not target_temp - external_temp
        offset_ext = self.k_ext * (internal_temp - external_temp)

        # Capping of offset_ext
        total_offset = offset + offset_ext
        total_offset = min(self.offset_max, max(-self.offset_max, total_offset))

        # If temperature is near the target_temp, reset the accumulated_error
        if abs(error) < self.stabilization_threshold:
            _LOGGER.debug("Stabilisation")
            self.accumulated_error = 0

        result = round(self.target_temp + total_offset, 1)

        _LOGGER.debug(
            "PITemperatureRegulator - Error: %.2f accumulated_error: %.2f offset: %.2f offset_ext: %.2f target_tem: %.1f regulatedTemp: %.1f",
            error,
            self.accumulated_error,
            offset,
            offset_ext,
            self.target_temp,
            result,
        )

        return result
