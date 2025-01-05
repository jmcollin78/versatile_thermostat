""" Implements the Presence Feature Manager """

# pylint: disable=line-too-long

import logging
from typing import Any

from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_HOME,
    STATE_NOT_HOME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    EventStateChangedData,
)

from homeassistant.components.climate import (
    PRESET_ACTIVITY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
)

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import ConfigData

from .base_manager import BaseFeatureManager

_LOGGER = logging.getLogger(__name__)


class FeaturePresenceManager(BaseFeatureManager):
    """The implementation of the Presence feature"""

    unrecorded_attributes = frozenset(
        {
            "presence_sensor_entity_id",
            "is_presence_configured",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)
        self._presence_state: str = STATE_UNAVAILABLE
        self._presence_sensor_entity_id: str = None
        self._is_configured: bool = False

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        self._presence_sensor_entity_id = entry_infos.get(CONF_PRESENCE_SENSOR)
        if (
            entry_infos.get(CONF_USE_PRESENCE_FEATURE, False)
            and self._presence_sensor_entity_id is not None
        ):
            self._is_configured = True
            self._presence_state = STATE_UNKNOWN

    @overrides
    async def start_listening(self):
        """Start listening the underlying entity"""
        if self._is_configured:
            self.stop_listening()
            self.add_listener(
                async_track_state_change_event(
                    self.hass,
                    [self._presence_sensor_entity_id],
                    self._presence_sensor_changed,
                )
            )

    @overrides
    async def refresh_state(self) -> bool:
        """Tries to get the last state from sensor
        Returns True if a change has been made"""
        ret = False
        if self._is_configured:
            # try to acquire presence entity state
            presence_state = self.hass.states.get(self._presence_sensor_entity_id)
            if presence_state and presence_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                ret = await self.update_presence(presence_state.state)
                _LOGGER.debug(
                    "%s - Presence have been retrieved: %s",
                    self,
                    presence_state.state,
                )
        return ret

    @callback
    async def _presence_sensor_changed(self, event: Event[EventStateChangedData]):
        """Handle presence changes."""
        new_state = event.data.get("new_state")
        _LOGGER.info(
            "%s - Presence changed. Event.new_state is %s, _attr_preset_mode=%s, activity=%s",
            self,
            new_state,
            self._vtherm.preset_mode,
            PRESET_ACTIVITY,
        )
        if new_state is None:
            return

        if await self.update_presence(new_state.state):
            await self._vtherm.async_control_heating(force=True)

    async def update_presence(self, new_state: str) -> bool:
        """Update the value of the presence sensor and update the VTherm state accordingly
        Return true if a change has been made"""

        _LOGGER.info("%s - Updating presence. New state is %s", self, new_state)
        old_presence_state = self._presence_state
        self._presence_state = (
            STATE_ON if new_state in (STATE_ON, STATE_HOME) else STATE_OFF
        )
        if self._vtherm.preset_mode in HIDDEN_PRESETS or self._is_configured is False:
            _LOGGER.info(
                "%s - Ignoring presence change cause in Power or Security preset or presence not configured",
                self,
            )
            return old_presence_state != self._presence_state

        if new_state is None or new_state not in (
            STATE_OFF,
            STATE_ON,
            STATE_HOME,
            STATE_NOT_HOME,
        ):
            self._presence_state = STATE_UNKNOWN
            return old_presence_state != self._presence_state

        if self._vtherm.preset_mode not in [
            PRESET_BOOST,
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_ACTIVITY,
        ]:
            return old_presence_state != self._presence_state

        new_temp = self._vtherm.find_preset_temp(self._vtherm.preset_mode)
        if new_temp is not None:
            _LOGGER.debug(
                "%s - presence change in temperature mode new_temp will be: %.2f",
                self,
                new_temp,
            )
            await self._vtherm.change_target_temperature(new_temp)
            self._vtherm.recalculate()

            return True

        return old_presence_state != self._presence_state

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update(
            {
                "presence_sensor_entity_id": self._presence_sensor_entity_id,
                "presence_state": self._presence_state,
                "is_presence_configured": self._is_configured,
            }
        )

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True of the presence is configured"""
        return self._is_configured

    @property
    def presence_state(self) -> str | None:
        """Return the current presence state STATE_ON or STATE_OFF
        or STATE_UNAVAILABLE if not configured"""
        if not self._is_configured:
            return STATE_UNAVAILABLE
        return self._presence_state

    @property
    def is_absence_detected(self) -> bool:
        """Return true if the presence is configured and presence sensor is OFF"""
        return self._is_configured and self._presence_state in [
            STATE_NOT_HOME,
            STATE_OFF,
        ]

    @property
    def presence_sensor_entity_id(self) -> bool:
        """Return true if the presence is configured and presence sensor is OFF"""
        return self._presence_sensor_entity_id

    def __str__(self):
        return f"PresenceManager-{self.name}"
