# pylint: disable=unused-argument, line-too-long, protected-access
"""A fake external feature manager (a plugin) shared by the tests of the contracts offered to the plugins."""

from homeassistant.core import HomeAssistant

from custom_components.versatile_thermostat.base_manager import BaseFeatureManager
from custom_components.versatile_thermostat.vtherm_central_api import VersatileThermostatAPI


class FakePluginManager(BaseFeatureManager):
    """Feature manager of a fake plugin. It records what it receives in a shared list"""

    def __init__(self, thermostat, name: str, events: list, configured: bool = True) -> None:
        super().__init__(thermostat, thermostat.hass, name)
        self.plugin_name = name
        self.events = events
        self.configured = configured
        # The tests let the plugin act once the VTherm is created and running
        self.enabled = False

    def post_init(self, entry_infos) -> None:
        """Nothing to read"""

    async def start_listening(self) -> None:
        """Nothing to listen"""

    async def refresh_state(self) -> bool:
        """Nothing to refresh"""
        return False

    @property
    def is_configured(self) -> bool:
        return self.configured

    @property
    def is_detected(self) -> bool:
        return False


class FaultyConfiguredMixin:
    """is_configured raises"""

    @property
    def is_configured(self) -> bool:
        raise RuntimeError("faulty is_configured")


class FakePluginFactory:
    """Factory of a fake plugin"""

    def __init__(self, name: str, manager_class, events: list, configured: bool = True) -> None:
        self.name = name
        self.manager_class = manager_class
        self.events = events
        self.configured = configured

    def supports(self, thermostat) -> bool:
        return True

    def create(self, thermostat):
        return self.manager_class(thermostat, self.name, self.events, self.configured)


def register_plugin(hass: HomeAssistant, manager_class, name: str = "fake_plugin", configured: bool = True, events: list | None = None) -> list:
    """Register a fake plugin before the creation of the thermostat. Returns the list shared with its manager"""
    events = [] if events is None else events
    VersatileThermostatAPI.get_vtherm_api(hass).register_feature_manager(FakePluginFactory(name, manager_class, events, configured))
    return events
