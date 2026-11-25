# pylint: disable=protected-access, line-too-long
""" Structural test: BaseThermostat no longer exposes the external manager hooks """
import pytest

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat

REMOVED_HOOKS = [
    "async_before_valve_write",
    "adjust_calibration_offset",
    "async_before_underlying_hvac_mode",
    "async_after_valve_command",
    "async_on_underlying_power",
]

@pytest.mark.parametrize("name", REMOVED_HOOKS)
def test_base_thermostat_has_no_hook(name):
    """Requirements 1.4, 1.5: hooks are not exposed on BaseThermostat"""
    assert not hasattr(BaseThermostat, name)

