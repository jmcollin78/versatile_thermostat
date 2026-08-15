"""Factory for the auto_fan feature manager plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vtherm_api.log_collector import get_vtherm_logger

from .const import (
    CONF_THERMOSTAT_CLIMATE,
    CONF_THERMOSTAT_TYPE,
    FEATURE_MANAGER_AUTO_FAN,
)
from .manager import AutoFanFeatureManager

if TYPE_CHECKING:
    from vtherm_api.interfaces import (
        InterfaceFeatureManager,
        InterfaceThermostatRuntime,
    )

_LOGGER = get_vtherm_logger(__name__)


class AutoFanManagerFactory:
    """Create AutoFan feature managers for eligible VTherm thermostats."""

    @property
    def name(self) -> str:
        """Return the feature manager identifier."""
        return FEATURE_MANAGER_AUTO_FAN

    def supports(self, thermostat: "InterfaceThermostatRuntime") -> bool:
        """Return True only for over_climate thermostats.

        Auto fan needs the ``fan_modes`` of the underlying climate, which only
        exist on the ``over_climate`` scope.
        """
        try:
            entry_infos = thermostat.entry_infos
        except Exception:  # pylint: disable=broad-except
            return False

        if isinstance(entry_infos, dict):
            return entry_infos.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CLIMATE

        # Fallback: eligible when the runtime exposes underlying fan modes.
        return getattr(thermostat, "underlying_fan_modes", None) is not None

    def create(
        self,
        thermostat: "InterfaceThermostatRuntime",
    ) -> "InterfaceFeatureManager":
        """Create a manager bound to the runtime thermostat."""
        return AutoFanFeatureManager(thermostat, thermostat.hass)
