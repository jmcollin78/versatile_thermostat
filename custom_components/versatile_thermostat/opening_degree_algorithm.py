""" This class aims to calculate the opening/closing degree of a valve.
See: https://github.com/jmcollin78/versatile_thermostat/issues/1220 """

import logging

_LOGGER = logging.getLogger(__name__)


class OpeningClosingDegreeCalculation:
    """Class to calculate the opening/closing degree of a valve."""

    @staticmethod
    def calculate_opening_closing_degree(
        brut_valve_open_percent: float, min_opening_degree: float, max_closing_degree: float, max_opening_degree: float, opening_threshold: float
    ) -> float:
        """
        Calculate the opening/closing degree based on parameters. See explanation on README

        Args:
            brut_valve_open_percent: Raw valve opening percentage (0-100)
            min_opening_degree: Minimum opening degree
            max_closing_degree: Maximum closing degree
            max_opening_degree: Maximum opening degree
            opening_threshold: Opening threshold

        Returns:
            float: The calculated opening degree
            float: The calculated closing degree
        """
        _LOGGER.debug(
            "Calculate opening/closing degree - Input: brut_valve_open_percent=%.2f, min_opening_degree=%.2f, max_closing_degree=%.2f",
            brut_valve_open_percent,
            min_opening_degree,
            max_closing_degree,
        )

        # for direct test. Already done in underlyings.py
        if min_opening_degree >= max_opening_degree:
            min_opening_degree = opening_threshold

        # clamp the brut_valve_open_percent to be within 0 and 100
        brut_valve_open_percent = max(0, min(100, brut_valve_open_percent))

        # normalize to 0-1 range
        bvop = brut_valve_open_percent / 100.0
        min_od = min_opening_degree / 100.0
        max_cd = max_closing_degree / 100.0
        max_od = max_opening_degree / 100.0
        ot = opening_threshold / 100.0

        # if heating need is >= opening_threshold (and heating is > 0) -> open and calculate with interpolation,
        if bvop >= ot and bvop > 0:
            # interpolation is just here to normalize the max opening which can be != 100. Some TRV has a max which not 100
            slope = (max_od - min_od) / (1 - ot)
            calculated_degree = min_od + slope * (bvop - ot)
        else:
            calculated_degree = 1 - max_cd

        # set to base 100
        calculated_degree = round(calculated_degree * 100)
        _LOGGER.debug(
            "Calculate opening/closing degree - Output: calculated_degree=%.2f %%",
            calculated_degree,
        )

        return calculated_degree, 100 - calculated_degree
