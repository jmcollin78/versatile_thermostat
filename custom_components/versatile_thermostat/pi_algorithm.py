# pylint: disable=line-too-long
""" The PI algorithm implementation """

import logging

_LOGGER = logging.getLogger(__name__)

class PITemperatureRegulator:
    """ A class implementing a PI Algorithm
    PI algorithms calculate a target temperature by adding an offset which is calculating as follow:
    - offset = kp * error + ki * accumulated_error

    To use it you must:
    - instanciate the class and gives the algorithm parameters: kp, ki, offset_max, stabilization_threshold, accumulated_error_threshold
    - call calculate_regulated_temperature with the internal and external temperature
    - call set_target_temp when the target temperature change.
    """

    def __init__(self, target_temp, kp, ki, k_ext, offset_max, stabilization_threshold, accumulated_error_threshold):
        self.target_temp = target_temp
        self.kp = kp  # proportionnel gain
        self.ki = ki  # integral gain
        self.k_ext = k_ext # exterior gain
        self.offset_max = offset_max
        self.stabilization_threshold = stabilization_threshold
        self.accumulated_error = 0
        self.accumulated_error_threshold = accumulated_error_threshold

    def set_target_temp(self, target_temp):
        """ Set the new target_temp"""
        self.target_temp = target_temp
        self.accumulated_error = 0

    def calculate_regulated_temperature(self, internal_temp, external_temp): # pylint: disable=unused-argument
        """ Calculate a new target_temp given some temperature"""
        # Calculate the error factor (P)
        error = self.target_temp - internal_temp

        # Calculate the sum of error (I)
        self.accumulated_error += error

        # Capping of the error
        self.accumulated_error = min(self.accumulated_error_threshold, max(-self.accumulated_error_threshold, self.accumulated_error))

        # Calculate the offset (proportionnel + intégral)
        offset = self.kp * error + self.ki * self.accumulated_error

        # Calculate the exterior offset
        offset_ext = self.k_ext * (self.target_temp - external_temp)

        # Capping of offset_ext
        total_offset = offset + offset_ext
        total_offset = min(self.offset_max, max(-self.offset_max, total_offset))


        # If temperature is near the target_temp, reset the accumulated_error
        if abs(error) < self.stabilization_threshold:
            _LOGGER.debug("Stabilisation")
            self.accumulated_error = 0

        result = round(self.target_temp + total_offset, 1)

        _LOGGER.debug("PITemperatureRegulator - Error: %.2f accumulated_error: %.2f offset: %.2f offset_ext: %.2f target_tem: %.1f regulatedTemp: %.1f",
            error, self.accumulated_error, offset, offset_ext, self.target_temp, result)

        return result
