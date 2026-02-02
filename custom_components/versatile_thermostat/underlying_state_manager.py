# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught

"""Underlying state manager for versatile_thermostat.

This module provides `UnderlyingStateManager` which listens to state change
events for a list of entity_ids and stores the last known `State` for each
entity.
"""
from typing import List, Optional, Callable, Any
import logging

from homeassistant.core import HomeAssistant, State
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)


class UnknownEntity(Exception):
    """Raised when an entity_id is not managed by the manager."""


class UnderlyingStateManager:
    """Manage states of underlying entities.

    Accepts a list of `entity_id` strings to monitor, initializes an
    internal array of states (`State | None`) and stores the last received
    state for each entity when state change events occur.

    Optionally accepts `on_change` callback with signature
    `async def on_change(entity_id: str, new_state: Optional[State])` that
    will be scheduled when a state change is received.
    """

    def __init__(self, hass: HomeAssistant, on_change: Optional[Callable[[str, Optional[State]], Any]] = None) -> None:
        """Create the manager without any monitored entity IDs.

        Entities can be added later with `add_underlying_entities`.
        """
        self._hass: HomeAssistant = hass
        self._entity_ids: List[str] = []
        self._on_change = on_change

        # no states initially; entities added at runtime
        self._states: List[Optional[State]] = []

        # no listener registered until entities are added
        self._remove_callback: Optional[Callable[[], None]] = None

    async def _state_changed(self, event) -> None:
        """Internal callback invoked on each state change event."""
        new_state: Optional[State] = event.data.get("new_state", None)
        old_state: Optional[State] = event.data.get("old_state", None)
        # Retrieve the entity_id from the event (sometimes in data or via new_state)
        entity_id = event.data.get("entity_id") if event.data.get("entity_id") else (
            new_state.entity_id if new_state else None
        )
        _LOGGER.debug(
            "UnderlyingStateManager - State change event received: %s for entity_id: %s",
            new_state,
            entity_id,
        )
        if entity_id is None:
            return

        if not self._set_state(entity_id, new_state):
            return

        if self._on_change:
            try:
                self._hass.async_create_task(self._on_change(entity_id, new_state, old_state))
            except Exception as err:  # pragma: no cover - defensive
                _LOGGER.exception("Error %s scheduling on_change for %s", err, entity_id)

    def get_state(self, entity_id: str) -> Optional[State]:
        """Return the last known `State` for `entity_id`, or `None` if unknown."""
        idx = self._index_of(entity_id)
        if idx is None:
            _LOGGER.error("UnderlyingStateManager - Requested state for unknown entity_id: %s", entity_id)
            return None
        return self._states[idx]

    def _set_state(self, entity_id: str, state: Optional[State]) -> bool:
        """Set the cached state for an entity and schedule `on_change` if present.
        Return True if the state was updated, False if ignored.
        States that are `None`, `STATE_UNAVAILABLE`, or `STATE_UNKNOWN` are ignored
        """
        idx = self._index_of(entity_id)
        if idx is None:
            raise UnknownEntity(f"Entity ID {entity_id} is not managed by UnderlyingStateManager")

        # if state is None or state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
        #     _LOGGER.debug("UnderlyingStateManager - Ignoring state change to unavailable/unknown for entity_id: %s", entity_id)
        #     return False

        self._states[idx] = state
        return True

    @property
    def is_all_states_initialized(self) -> bool:
        """Return True if all monitored states are initialized and available.

        A state is considered initialized if it is not None and its
        `.state` is not `STATE_UNAVAILABLE` or `STATE_UNKNOWN`.
        """
        for st in self._states:
            if st is None or st.state in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
                return False
        return len(self._states) == len(self._entity_ids)

    def _index_of(self, entity_id: str) -> Optional[int]:
        """Return the index of `entity_id` in the monitored list, or None."""
        try:
            return self._entity_ids.index(entity_id)
        except ValueError:
            return None

    def add_underlying_entities(self, entity_ids: List[str]) -> None:
        """Add multiple entity_ids to the monitored list at runtime.

        Existing entities are ignored. The state change listener is (re)
        registered for the updated entity list. If any added entity has an
        initial state and `on_change` is set, the callback is scheduled for
        that entity.
        """
        added = []
        for entity_id in entity_ids:
            if entity_id in self._entity_ids:
                continue
            self._entity_ids.append(entity_id)
            state = self._hass.states.get(entity_id)
            # should always add an initial state even if None
            self._states.append(state)
            if state and state.state not in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
                # but don't notify if not a real state
                added.append(entity_id)

        # re-register the state change listener for the new set of entity_ids
        if self._remove_callback:
            try:
                self._remove_callback()
            except Exception:
                _LOGGER.exception("Error removing previous callback while adding %s", added)

        self._remove_callback = async_track_state_change_event(
            self._hass, self._entity_ids, self._state_changed
        )

        # schedule on_change for each newly added entity if initial state exists
        if self._on_change:
            for eid in added:
                st = self._states[self._entity_ids.index(eid)]
                if st is not None:
                    try:
                        self._hass.async_create_task(self._on_change(eid, st, None))
                    except Exception as error:  # pragma: no cover - defensive
                        _LOGGER.exception("Error scheduling on_change for {eid}. error is {error}", eid=eid, error=error)

    def stop(self) -> None:
        """Stop listening to state changes and remove the callback."""
        if self._remove_callback:
            try:
                self._remove_callback()
            except Exception:
                pass
            self._remove_callback = None
