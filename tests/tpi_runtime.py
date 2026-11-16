"""Build the native runtime objects without HA lifecycle I/O."""

from custom_components.versatile_thermostat.prop_handler_tpi import TPIHandler
from custom_components.versatile_thermostat.prop_algo_tpi import TpiAlgorithm
from custom_components.versatile_thermostat.auto_tpi_manager import (
    AutoTpiManager,
    AutoTpiState,
)


def native_runtime(thermostat, learning=False, continuous=False):
    handler = TPIHandler(thermostat)
    manager = object.__new__(AutoTpiManager)
    manager.state = AutoTpiState()
    manager.state.autolearn_enabled = learning
    manager._continuous_kext = continuous
    handler._auto_tpi_manager = manager
    thermostat._algo_handler = handler
    thermostat.auto_tpi_manager = manager
    thermostat.prop_algorithm = TpiAlgorithm(0.3, 0.02, "test")
    return thermostat
