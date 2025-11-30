""" This module manages the lock feature of the Versatile Thermostat integration. """
import logging
from typing import Any

from homeassistant.core import (
    HomeAssistant,
)

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons_type import ConfigData

from .base_manager import BaseFeatureManager

_LOGGER = logging.getLogger(__name__)

class FeatureLockManager(BaseFeatureManager):
    """ The implementation of the Lock Feature Manager for Versatile Thermostat """
    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Initialize the FeatureLockManager."""
        super().__init__(vtherm, hass)
        self._is_configured: bool = False
        self._lock_users: bool = True
        self._lock_automations: bool = True
        self._lock_code: str | None = None
        self._is_locked: bool = False

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        self._lock_users = entry_infos.get(CONF_LOCK_USERS, True)
        self._lock_automations = entry_infos.get(CONF_LOCK_AUTOMATIONS, True)
        self._lock_code = entry_infos.get(CONF_LOCK_CODE)
        self._is_configured = self._lock_users or self._lock_automations

    @overrides
    def restore_state(self, old_state) -> None:
        """Restore locks from old state."""
        if old_state is not None:
            self._is_locked = bool(old_state.attributes.get("is_locked", False))

    @overrides
    async def start_listening(self):
        """Nothing to listen here"""

    @property
    def is_configured(self) -> bool:
        """True if the FeatureManager is fully configured"""
        return self._is_configured

    @property
    def is_locked(self) -> bool:
        """Return True if the thermostat is locked."""
        return self._is_locked

    def check_is_locked(self, function_name: str) -> bool:
        """Check if the thermostat is locked."""
        context = getattr(self._vtherm, "_context", None)
        source_is_user = context and context.user_id is not None
        source_is_automation = not source_is_user

        if self._is_locked and (
            (self._lock_users and source_is_user)
            or (self._lock_automations and source_is_automation)
        ):
            _LOGGER.info(
                "%s - Blocked external call to %s while locked (source=%s)",
                self,
                function_name,
                "user" if source_is_user else "automation/unknown",
            )
            return True
        return False

    def _validate_lock_code(self, code: str | None) -> bool:
        """Validate the provided code against the configured lock code."""
        if self._lock_code:
            if not code or str(code) != str(self._lock_code):
                _LOGGER.error("%s - Lock code validation failed", self)
                raise HomeAssistantError(f"Lock code validation failed: {code}")
        return True

    def change_lock_state(self, locked: bool, code: str | None = None) -> None:
        """Set the internal lock state."""
        if self._validate_lock_code(code):
            self._is_locked = locked
            _LOGGER.info("%s - Lock state set to %s", self, locked)
            return True
        return False

    @property
    def has_lock_settings_enabled(self) -> bool:
        """Return True if any lock setting is enabled."""
        return self._is_configured and (self._lock_users or self._lock_automations)

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]) -> None:
        """Add custom attributes to the attributes dict."""

        extra_state_attributes.update(
            {
                "is_lock_configured": self._is_configured,
            }
        )
        if self._is_configured:
            extra_state_attributes.update(
                {
                    "lock_manager": {
                        "is_locked": self._is_locked,
                        "lock_users": self._lock_users,
                        "lock_automations": self._lock_automations,
                        "lock_code": bool(self._lock_code)
                    }
                })
