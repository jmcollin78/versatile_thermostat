"""Implements the optional external humidity source feature."""

import math
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.helpers.event import EventStateChangedData, async_call_later, async_track_state_change_event

from vtherm_api.log_collector import get_vtherm_logger

from .base_manager import BaseFeatureManager
from .commons import write_event_log
from .commons_type import ConfigData
from .const import CONF_HUMIDITY_SENSOR, CONF_TEMP_SENSOR, CONF_USE_HUMIDITY_FEATURE
from .humidity import find_humidity_sensor_candidates

_LOGGER = get_vtherm_logger(__name__)

_MAX_HUMIDITY_RETRIES = 3
_HUMIDITY_RETRY_DELAY_SEC = 30


class FeatureHumidityManager(BaseFeatureManager):
    """Resolve, read and monitor an optional external humidity sensor."""

    unrecorded_attributes = frozenset(
        {
            "is_humidity_configured",
            "humidity_manager",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Initialize the humidity feature manager."""
        super().__init__(vtherm, hass)
        self._cur_humidity: float | None = None
        self._humidity_is_invalid = False
        self._configured_humidity_sensor_entity_id: str | None = None
        self._temperature_sensor_entity_id: str | None = None
        self._use_humidity_feature: bool | None = None
        self._humidity_sensor_entity_id: str | None = None
        self._humidity_source = "none"
        self._humidity_listener_entity_id: str | None = None
        self._humidity_retry_count = 0
        self._cancel_humidity_retry: CALLBACK_TYPE | None = None

    def post_init(self, entry_infos: ConfigData):
        """Store configuration; source resolution is deferred until startup."""
        self.stop_listening()
        self._cur_humidity = None
        self._humidity_is_invalid = False
        self._configured_humidity_sensor_entity_id = entry_infos.get(CONF_HUMIDITY_SENSOR)
        self._temperature_sensor_entity_id = entry_infos.get(CONF_TEMP_SENSOR)
        self._use_humidity_feature = entry_infos.get(CONF_USE_HUMIDITY_FEATURE)
        self._humidity_sensor_entity_id = None
        self._humidity_source = "none"
        self._humidity_listener_entity_id = None
        self._humidity_retry_count = 0

    def _resolve_humidity_source(self) -> None:
        """Resolve explicit configuration first, then the shared auto-detection."""
        self._humidity_sensor_entity_id = None
        self._humidity_source = "none"

        if self._use_humidity_feature is False:
            _LOGGER.info("%s - Humidity sensor disabled by configuration", self)
            return

        if self._configured_humidity_sensor_entity_id:
            self._humidity_sensor_entity_id = self._configured_humidity_sensor_entity_id
            self._humidity_source = "explicit"
            return

        candidates = find_humidity_sensor_candidates(
            self.hass, self._temperature_sensor_entity_id
        )
        if not candidates:
            _LOGGER.info("%s - No humidity candidate found for temperature sensor", self)
            return
        if len(candidates) > 1:
            _LOGGER.info(
                "%s - Multiple humidity candidates found %s; using the first one",
                self,
                candidates,
            )

        self._humidity_sensor_entity_id = candidates[0]
        self._humidity_source = "auto"
        _LOGGER.info("%s - Auto-detected humidity sensor %s", self, candidates[0])

    async def start_listening(self):
        """Resolve the source, install one listener and read its initial state."""
        self._resolve_humidity_source()
        sensor_entity_id = self._humidity_sensor_entity_id

        if sensor_entity_id != self._humidity_listener_entity_id:
            self.stop_listening()
            if sensor_entity_id:
                self.add_listener(
                    async_track_state_change_event(
                        self.hass,
                        [sensor_entity_id],
                        self._humidity_sensor_changed,
                    )
                )
                self._humidity_listener_entity_id = sensor_entity_id

        await self.refresh_state()

        if (
            self._humidity_source == "none"
            and self._humidity_retry_count < _MAX_HUMIDITY_RETRIES
            and self._cancel_humidity_retry is None
        ):
            self._humidity_retry_count += 1
            self._cancel_humidity_retry = async_call_later(
                self.hass, _HUMIDITY_RETRY_DELAY_SEC, self._retry_humidity_source
            )

    def stop_listening(self) -> bool:
        """Stop the listener and cancel an outstanding source-resolution retry."""
        if self._cancel_humidity_retry:
            self._cancel_humidity_retry()
            self._cancel_humidity_retry = None
        self._humidity_listener_entity_id = None
        return super().stop_listening()

    async def refresh_state(self) -> bool:
        """Read the latest state of the resolved humidity sensor."""
        if not self._humidity_sensor_entity_id:
            return self._set_current_humidity(None)
        return self._set_current_humidity(
            self.hass.states.get(self._humidity_sensor_entity_id)
        )

    @callback
    async def _humidity_sensor_changed(self, event: Event[EventStateChangedData]):
        """Update published humidity after a sensor state change."""
        new_state = event.data.get("new_state")
        write_event_log(
            _LOGGER,
            self._vtherm,
            f"Humidity sensor changed to state {new_state.state if new_state else None}",
        )
        self._set_current_humidity(new_state)
        self._vtherm.update_custom_attributes()
        self._vtherm.async_write_ha_state()

    @callback
    async def _retry_humidity_source(self, _now) -> None:
        """Retry discovery while Home Assistant is still loading sensors."""
        self._cancel_humidity_retry = None
        if self._humidity_source == "none":
            await self.start_listening()

    def _set_current_humidity(self, state: State | None) -> bool:
        """Set current humidity, explicitly propagating invalid sensor states."""
        old_humidity = self._cur_humidity
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._cur_humidity = None
            if not self._humidity_is_invalid:
                _LOGGER.warning("%s - Humidity sensor is unavailable or unknown", self)
            self._humidity_is_invalid = True
            return old_humidity is not None

        try:
            humidity = float(state.state)
            if math.isnan(humidity) or math.isinf(humidity):
                raise ValueError(f"Sensor has illegal state {state.state}")
        except (TypeError, ValueError) as err:
            self._cur_humidity = None
            if not self._humidity_is_invalid:
                _LOGGER.error("%s - Unable to update humidity from sensor: %s", self, err)
            self._humidity_is_invalid = True
            return old_humidity is not None

        self._cur_humidity = humidity
        self._humidity_is_invalid = False
        return old_humidity != humidity

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Expose the resolved source for diagnostics without adding an entity."""
        extra_state_attributes.update(
            {"is_humidity_configured": self.is_configured}
        )
        if self.is_configured:
            extra_state_attributes["humidity_manager"] = {
                "humidity_sensor_entity_id": self._humidity_sensor_entity_id,
                "humidity_source": self._humidity_source,
            }

    @property
    def current_humidity(self) -> float | None:
        """Return external humidity, or None when no external source exists."""
        return self._cur_humidity if self._humidity_source != "none" else None

    @property
    def humidity_sensor_entity_id(self) -> str | None:
        """Return the resolved external sensor entity identifier."""
        return self._humidity_sensor_entity_id

    @property
    def humidity_source(self) -> str:
        """Return the selected source kind: explicit, auto or none."""
        return self._humidity_source

    @property
    def is_configured(self) -> bool:
        """Return whether an external humidity source was resolved."""
        return self._humidity_source != "none"

    @property
    def is_detected(self) -> bool:
        """Return whether a usable external humidity source was resolved."""
        return self.is_configured

    def __str__(self):
        """Return a useful log name."""
        return f"HumidityManager-{self.name}"