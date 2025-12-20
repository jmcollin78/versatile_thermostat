""" Implements a base Feature Manager for Versatile Thermostat """

import logging
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons_type import ConfigData

from .config_schema import *  # pylint: disable=wildcard-import, unused-wildcard-import

_LOGGER = logging.getLogger(__name__)


class BaseFeatureManager:
    """A base class for all feature"""

    def __init__(self, vtherm: Any, hass: HomeAssistant, name: str = None):
        """Init of a featureManager"""
        self._vtherm = vtherm
        self._name = vtherm.name if vtherm else name
        self._active_listener: list[CALLBACK_TYPE] = []
        self._hass = hass

    def post_init(self, entry_infos: ConfigData):
        """Initialize the attributes of the FeatureManager"""
        raise NotImplementedError()

    async def start_listening(self):
        """Start listening the underlying entity"""
        raise NotImplementedError()

    def stop_listening(self) -> bool:
        """stop listening to the sensor"""
        while self._active_listener:
            self._active_listener.pop()()

        self._active_listener = []

    async def refresh_state(self):
        """Refresh the state and return True if a change have been made"""
        return False

    def add_listener(self, func: CALLBACK_TYPE) -> None:
        """Add a listener to the list of active listener"""
        self._active_listener.append(func)

    def restore_state(self, old_state) -> None:
        """Restore state from old state."""

    @property
    def is_configured(self) -> bool:
        """True if the FeatureManager is fully configured"""
        raise NotImplementedError()

    @property
    def name(self) -> str:
        """The name"""
        return self._name if self._name else "Unnamed FeatureManager"

    @property
    def hass(self) -> HomeAssistant:
        """The HA instance"""
        return self._hass
