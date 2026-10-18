"""Valve command filter shared by the VTherms driving a valve opening"""

from datetime import datetime

from vtherm_api.log_collector import get_vtherm_logger

_LOGGER = get_vtherm_logger(__name__)


class ValveCommandMixin:
    """Convert a proportional command into the retained valve opening.

    Used by ThermostatOverValve and ThermostatOverClimateValve. The
    CycleScheduler calls apply_valve_command_percent for every valve command
    it receives (TPI or plugin algorithm), so the valve follows the command
    path and the cycle callbacks report the value actually retained.

    The host class provides valve_open_percent, is_sleeping, now,
    do_recalculate_later(), update_custom_attributes() and
    async_write_ha_state().
    """

    _valve_open_percent: int | None
    _last_calculation_timestamp: datetime | None
    _auto_regulation_dpercent: float | None
    _auto_regulation_period_min: int | None

    def apply_valve_command_percent(
        self,
        on_percent: float,
        force: bool = False,
    ) -> float:
        """Accept a requested valve command and return the retained ratio.

        This is the single conversion point between a proportional algorithm's
        continuous output and the integer command exposed by the thermostat.
        While sleeping the valve is fully open: the dpercent filter is bypassed
        but the regulation period still applies unless force is set.
        """
        if self.is_sleeping:
            return self._retain_valve_open_percent(100, force, filter_dpercent=False)

        if self._auto_regulation_period_min is None or self._auto_regulation_dpercent is None:
            _LOGGER.warning(
                "%s - auto_regulation_period_min or auto_regulation_dpercent is not set. Keeping current valve command.",
                self,
            )
            return self.valve_open_percent / 100.0

        new_valve_percent = round(max(0, min(on_percent, 1)) * 100)
        return self._retain_valve_open_percent(new_valve_percent, force)

    def _retain_valve_open_percent(
        self,
        new_valve_percent: int,
        force: bool,
        filter_dpercent: bool = True,
    ) -> float:
        """Apply the dpercent and period filters, then store the valve opening.

        Returns the retained ratio (0.0 to 1.0).
        """
        if filter_dpercent:
            # Issue 533 - don't filter with dtemp if valve should be close. Else it will never close
            if new_valve_percent < self._auto_regulation_dpercent:
                new_valve_percent = 0

            # The first command is never filtered by dpercent
            if self._valve_open_percent is not None:
                dpercent = new_valve_percent - self.valve_open_percent
                if new_valve_percent > 0 and -1 * self._auto_regulation_dpercent <= dpercent < self._auto_regulation_dpercent:
                    _LOGGER.debug(
                        "%s - do not calculate TPI because regulation_dpercent (%.1f) is not exceeded",
                        self,
                        dpercent,
                    )
                    return self.valve_open_percent / 100.0

        if self._valve_open_percent == new_valve_percent:
            _LOGGER.debug("%s - no change in valve_open_percent.", self)
            return self.valve_open_percent / 100.0

        now = self.now
        if self._last_calculation_timestamp is not None:
            period = (now - self._last_calculation_timestamp).total_seconds() / 60
            if not force and period < self._auto_regulation_period_min:
                _LOGGER.info(
                    "%s - do not apply valve command because regulation_period (%d) is not exceeded",
                    self,
                    period,
                )
                self.do_recalculate_later()
                return self.valve_open_percent / 100.0

        self._valve_open_percent = new_valve_percent

        # Valve open percent is sent to underlyings by CycleScheduler
        # in start_cycle (called from control_heating)

        self._last_calculation_timestamp = now

        self.update_custom_attributes()
        self.async_write_ha_state()
        return self.valve_open_percent / 100.0
