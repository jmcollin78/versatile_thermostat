"""Implements the Humidity Feature Manager"""

# pylint: disable=line-too-long

import logging
from typing import Any

from homeassistant.const import (
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

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import write_event_log
from .commons_type import ConfigData

from .base_manager import BaseFeatureManager

_LOGGER = logging.getLogger(__name__)


class FeatureHumidityManager(BaseFeatureManager):
    """The implementation of the Humidity feature"""

    unrecorded_attributes = frozenset(
        {
            "humidity_sensor_entity_id",
            "is_humidity_configured",
            "current_humidity",
            "humidity_threshold",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)
        self._humidity_sensor_entity_id: str = None
        self._current_humidity: float | None = None
        self._humidity_threshold: float = 60.0  # Default threshold
        self._is_configured: bool = False

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        self._humidity_sensor_entity_id = entry_infos.get(CONF_HUMIDITY_SENSOR)
        self._humidity_threshold = entry_infos.get(CONF_HUMIDITY_THRESHOLD, 60.0)

        if entry_infos.get(CONF_USE_HUMIDITY_FEATURE, False) and self._humidity_sensor_entity_id is not None:
            self._is_configured = True
            self._current_humidity = None

    @overrides
    async def start_listening(self):
        """Start listening the underlying entity"""
        if self._is_configured:
            self.stop_listening()
            self.add_listener(
                async_track_state_change_event(
                    self.hass,
                    [self._humidity_sensor_entity_id],
                    self._humidity_sensor_changed,
                )
            )

    @overrides
    async def refresh_state(self) -> bool:
        """Tries to get the last state from sensor
        Returns True if a change has been made"""
        ret = False
        if self._is_configured and self._humidity_sensor_entity_id:
            humidity_state = self.hass.states.get(self._humidity_sensor_entity_id)
            if humidity_state and humidity_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                old_humidity = self._current_humidity
                self._current_humidity = get_safe_float(self.hass, self._humidity_sensor_entity_id)
                if old_humidity != self._current_humidity:
                    _LOGGER.debug(
                        "%s - Humidity have been retrieved: %.1f%%",
                        self,
                        self._current_humidity,
                    )
                    ret = True
        return ret

    @callback
    async def _humidity_sensor_changed(self, event: Event[EventStateChangedData]):
        """Handle humidity sensor changes."""
        new_state = event.data.get("new_state")
        write_event_log(_LOGGER, self._vtherm, f"Humidity sensor changed to state {new_state.state if new_state else None}")

        if new_state is None:
            return

        old_humidity = self._current_humidity
        self._current_humidity = get_safe_float(self.hass, self._humidity_sensor_entity_id)

        if old_humidity != self._current_humidity:
            _LOGGER.info(
                "%s - Humidity changed from %.1f%% to %.1f%%",
                self,
                old_humidity if old_humidity is not None else 0,
                self._current_humidity if self._current_humidity is not None else 0,
            )
            # Force state update to check if DRY mode should be activated
            self._vtherm.requested_state.force_changed()
            await self._vtherm.update_states(force=True)

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        extra_state_attributes.update(
            {
                "is_humidity_configured": self._is_configured,
            }
        )
        if self._is_configured:
            extra_state_attributes.update(
                {
                    "humidity_manager": {
                        "humidity_sensor_entity_id": self._humidity_sensor_entity_id,
                        "current_humidity": self._current_humidity,
                        "humidity_threshold": self._humidity_threshold,
                        "is_humidity_too_high": self.is_humidity_too_high,
                    }
                }
            )

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True if humidity feature is configured"""
        return self._is_configured

    @property
    def current_humidity(self) -> float | None:
        """Return the current humidity level"""
        return self._current_humidity

    @property
    def humidity_threshold(self) -> float:
        """Return the humidity threshold"""
        return self._humidity_threshold

    @property
    def is_humidity_too_high(self) -> bool:
        """Return True if humidity is above threshold"""
        if not self._is_configured or self._current_humidity is None:
            return False
        return self._current_humidity > self._humidity_threshold

    @property
    def humidity_sensor_entity_id(self) -> str | None:
        """Return the humidity sensor entity ID"""
        return self._humidity_sensor_entity_id

    def __str__(self):
        return f"HumidityManager-{self.name}"
