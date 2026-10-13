"""Core inhibition state of a VTherm (issue #2087).

An inhibition plugin calls ``async_set_inhibition(stop_underlyings)`` and
``async_unset_inhibition()`` on the VTherm (through the VTherm API facade). The
core only keeps the minimal operational state below, resolves the effective
HVAC mode to OFF (see ``StateManager``) and gates every command sent to the
underlyings at a single boundary (``UnderlyingEntity.hass_services_async_call``
and ``UnderlyingSwitch.turn_on/turn_off``).

While the gate is not OPEN, only the command of the active core transaction
passes: the optional ENTRY_STOP while CLOSED and the EXIT_RECONCILE while
EXIT_RECONCILING. A transaction is identified by its call chain: a ContextVar
holding the transaction token, bound to the task running the transaction (a task
or a timer created during the transaction inherits the ContextVar, it must not
pass). So a keep-alive, a timer or a background task never passes the gate.
"""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum
from typing import Any

from homeassistant.components.climate import (
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_SWING_HORIZONTAL_MODE,
    SERVICE_SET_SWING_MODE,
)
from homeassistant.core import State
from homeassistant.helpers.restore_state import async_get as restore_async_get
from homeassistant.util import dt as dt_util

from vtherm_api.log_collector import get_vtherm_logger

_LOGGER = get_vtherm_logger(__name__)

ATTR_INHIBITION = "inhibition"
INHIBITION_SCHEMA_VERSION = 1

ERROR_ENTRY_STOP_FAILED = "entry_stop_failed"
ERROR_EXIT_RECONCILE_FAILED = "exit_reconcile_failed"

# User settings which are not part of the requested state: dropped with a warning
_USER_SETTING_SERVICES = frozenset({SERVICE_SET_FAN_MODE, SERVICE_SET_HUMIDITY, SERVICE_SET_SWING_MODE, SERVICE_SET_SWING_HORIZONTAL_MODE})


class CommandGate(StrEnum):
    """State of the command boundary towards the underlyings"""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    EXIT_RECONCILING = "EXIT_RECONCILING"


class InhibitionTransaction(StrEnum):
    """The only core operations allowed to cross a non-open gate"""

    ENTRY_STOP = "ENTRY_STOP"
    EXIT_RECONCILE = "EXIT_RECONCILE"


# The transaction token of the running call chain (None outside a transaction)
_ACTIVE_TRANSACTION: ContextVar[object | None] = ContextVar("vtherm_inhibition_transaction", default=None)

# The transaction allowed in each gate state
_GATE_TRANSACTION = {
    CommandGate.CLOSED: InhibitionTransaction.ENTRY_STOP,
    CommandGate.EXIT_RECONCILING: InhibitionTransaction.EXIT_RECONCILE,
}


class InhibitionManager:
    """Minimal operational and persisted inhibition state of one VTherm"""

    def __init__(self, vtherm: Any):
        self._vtherm = vtherm
        self._inhibited: bool = False
        self._entry_stop_requested: bool = False
        self._entry_stop_completed: bool = False
        self._gate: CommandGate = CommandGate.OPEN
        self._last_transition_at: str | None = None
        self._last_error_code: str | None = None
        # True once inhibition has been used (set called or snapshot restored)
        self._is_used: bool = False
        # Serializes set and unset (never update_states, which is re-entrant)
        self._lock = asyncio.Lock()
        self._transaction: tuple[InhibitionTransaction, object, asyncio.Task | None] | None = None
        self._exit_pending: bool = False
        self._exit_future: asyncio.Future | None = None
        self._warned: set[tuple[str, str]] = set()

    def __str__(self) -> str:
        return f"{self._vtherm}-inhibition"

    @property
    def is_inhibited(self) -> bool:
        """True while the inhibition constraint is active"""
        return self._inhibited

    @property
    def command_gate(self) -> CommandGate:
        """The command gate state"""
        return self._gate

    @property
    def is_used(self) -> bool:
        """True if the inhibition was ever used for this VTherm"""
        return self._is_used

    def as_dict(self) -> dict[str, Any]:
        """The persisted and published snapshot"""
        return {
            "schema_version": INHIBITION_SCHEMA_VERSION,
            "inhibited": self._inhibited,
            "entry_stop_requested": self._entry_stop_requested,
            "entry_stop_completed": self._entry_stop_completed,
            "command_gate": str(self._gate),
            "last_transition_at": self._last_transition_at,
            "last_error_code": self._last_error_code,
        }

    def restore_state(self, old_state: State | None):
        """Restore the snapshot. Must be called before any underlying command.
        A restart during the exit reconciliation is restored closed: the plugin
        has to call unset again."""
        if old_state is None:
            return
        snapshot = (old_state.attributes.get("specific_states") or {}).get(ATTR_INHIBITION)
        if not isinstance(snapshot, dict) or snapshot.get("schema_version") != INHIBITION_SCHEMA_VERSION:
            return
        self._is_used = True
        self._last_transition_at = snapshot.get("last_transition_at")
        self._last_error_code = snapshot.get("last_error_code")
        if snapshot.get("inhibited") is True or snapshot.get("command_gate") in (CommandGate.CLOSED, CommandGate.EXIT_RECONCILING):
            self._inhibited = True
            self._gate = CommandGate.CLOSED
            self._entry_stop_requested = snapshot.get("entry_stop_requested") is True
            self._entry_stop_completed = snapshot.get("entry_stop_completed") is True
            _LOGGER.info("%s - Inhibition restored (gate closed, entry stop completed=%s)", self, self._entry_stop_completed)

    ##
    ## The command gate
    ##
    def blocks_command(self, target: Any, domain: str, service: str) -> bool:
        """True if a command to an underlying must be dropped"""
        if self._gate is CommandGate.OPEN:
            return False
        transaction = self._transaction
        if (
            transaction is not None
            and transaction[0] is _GATE_TRANSACTION[self._gate]
            and _ACTIVE_TRANSACTION.get() is transaction[1]
            and asyncio.current_task() is transaction[2]
        ):
            return False

        key = (str(target), service)
        if service in _USER_SETTING_SERVICES and key not in self._warned:
            self._warned.add(key)
            _LOGGER.warning("%s - %s.%s for %s is dropped: the VTherm is inhibited (gate %s)", self, domain, service, target, self._gate)
        else:
            _LOGGER.debug("%s - %s.%s for %s is blocked by the inhibition gate (%s)", self, domain, service, target, self._gate)
        return True

    @contextmanager
    def _transaction_scope(self, kind: InhibitionTransaction) -> Iterator[None]:
        """Run the enclosed call chain as the only one allowed to cross the gate"""
        token = object()
        self._transaction = (kind, token, asyncio.current_task())
        context_token = _ACTIVE_TRANSACTION.set(token)
        try:
            yield
        finally:
            _ACTIVE_TRANSACTION.reset(context_token)
            self._transaction = None

    ##
    ## Transitions
    ##
    async def async_set(self, stop_underlyings: bool):
        """Enter the inhibition. Idempotent while inhibited."""
        async with self._lock:
            if self._inhibited:
                _LOGGER.debug("%s - Already inhibited. Nothing is sent again", self)
                return

            self._is_used = True
            self._exit_pending = False
            self._inhibited = True
            self._gate = CommandGate.CLOSED
            self._entry_stop_requested = stop_underlyings is True
            self._entry_stop_completed = False
            self._last_error_code = None
            self._warned.clear()
            self._touch()
            _LOGGER.info("%s - Inhibition set (stop_underlyings=%s)", self, self._entry_stop_requested)
            await self._async_persist()

            try:
                # Resolve the effective OFF. Every command it produces is dropped by the gate
                self._vtherm.requested_state.force_changed()
                await self._vtherm.update_states(force=True)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("%s - Error while resolving the inhibited state: %s", self, err)

            await self._async_entry_stop_if_ready()
            await self._async_persist()

    async def async_unset(self):
        """Leave the inhibition. A concurrent call joins the running exit.
        Raises if the exit reconciliation fails (the VTherm stays inhibited)."""
        if self._exit_future is not None:
            await asyncio.shield(self._exit_future)
            return

        future = asyncio.get_running_loop().create_future()
        self._exit_future = future
        try:
            async with self._lock:
                await self._async_exit()
        except asyncio.CancelledError:
            future.cancel()
            raise
        except Exception as err:
            future.set_exception(err)
            future.exception()  # the error is raised to the caller: mark it as retrieved
            raise
        else:
            future.set_result(None)
        finally:
            self._exit_future = None

    async def async_on_vtherm_ready(self):
        """Complete an entry stop or an exit deferred until the VTherm is ready"""
        if not self._exit_pending and not self._is_entry_stop_pending:
            return
        async with self._lock:
            if self._exit_pending:
                if self._vtherm.is_ready:
                    try:
                        await self._async_exit_reconcile()
                    except Exception:  # pylint: disable=broad-except
                        # already logged, the VTherm is inhibited again
                        pass
            elif self._is_entry_stop_pending:
                await self._async_entry_stop_if_ready()
                await self._async_persist()

    @property
    def _is_entry_stop_pending(self) -> bool:
        return self._inhibited and self._gate is CommandGate.CLOSED and self._entry_stop_requested and not self._entry_stop_completed

    async def _async_entry_stop_if_ready(self):
        """Send the single entry stop if it is requested and not done yet"""
        if not self._is_entry_stop_pending:
            return
        if not self._vtherm.is_ready:
            _LOGGER.info("%s - Entry stop deferred until the VTherm is ready", self)
            return

        # Cancel the running cycle before the transaction: nothing it triggers may pass
        scheduler = self._vtherm.cycle_scheduler
        if scheduler:
            await scheduler.cancel_cycle()

        failed = False
        with self._transaction_scope(InhibitionTransaction.ENTRY_STOP):
            for under in self._vtherm.all_underlying_entities:
                try:
                    await under.async_inhibition_stop()
                except Exception as err:  # pylint: disable=broad-except
                    failed = True
                    _LOGGER.error("%s - Entry stop failed for %s: %s", self, under, err)
        self._entry_stop_completed = True
        self._last_error_code = ERROR_ENTRY_STOP_FAILED if failed else None
        self._touch()
        _LOGGER.info("%s - Entry stop sent to the underlyings", self)

    async def _async_exit(self):
        """Leave the inhibition, now or when the VTherm becomes ready"""
        if not self._inhibited and self._gate is CommandGate.OPEN:
            _LOGGER.debug("%s - Not inhibited. Nothing to do", self)
            return
        if self._exit_pending:
            _LOGGER.debug("%s - Exit already pending until the VTherm is ready", self)
            return

        self._inhibited = False
        self._gate = CommandGate.EXIT_RECONCILING
        self._touch()
        _LOGGER.info("%s - Inhibition unset. Reconciling the underlyings", self)
        await self._async_persist()

        if not self._vtherm.is_ready:
            self._exit_pending = True
            _LOGGER.info("%s - Exit reconciliation deferred until the VTherm is ready", self)
            return

        await self._async_exit_reconcile()

    async def _async_exit_reconcile(self):
        """Apply the current requested state to every underlying, then open the gate"""
        self._exit_pending = False
        vtherm = self._vtherm
        try:
            with self._transaction_scope(InhibitionTransaction.EXIT_RECONCILE):
                # Commands dropped during the inhibition may have updated the last sent caches
                for under in vtherm.all_underlying_entities:
                    await under.async_inhibition_resync()
                # Walk every underlying even if the effective mode does not change (OFF -> OFF)
                vtherm.requested_state.force_changed()
                vtherm.current_state.force_changed()
                await vtherm.update_states(force=True)
        except Exception as err:
            self._inhibited = True
            self._gate = CommandGate.CLOSED
            self._last_error_code = ERROR_EXIT_RECONCILE_FAILED
            self._touch()
            _LOGGER.error("%s - Exit reconciliation failed, the VTherm stays inhibited: %s", self, err)
            try:
                vtherm.requested_state.force_changed()
                await vtherm.update_states(force=True)
            except Exception as err2:  # pylint: disable=broad-except
                _LOGGER.error("%s - Error while resolving the inhibited state: %s", self, err2)
            await self._async_persist()
            raise

        self._gate = CommandGate.OPEN
        self._entry_stop_requested = False
        self._entry_stop_completed = False
        self._last_error_code = None
        self._touch()
        _LOGGER.info("%s - Exit reconciliation done. Normal operation resumed", self)
        await self._async_persist()

    def _touch(self):
        self._last_transition_at = dt_util.now().isoformat()

    async def _async_persist(self):
        """Publish the snapshot and save it now (attributes alone are dumped every 15 min)"""
        vtherm = self._vtherm
        if vtherm.hass is None or vtherm.entity_id is None:
            return
        try:
            vtherm.update_custom_attributes()
            vtherm.async_write_ha_state()
            await restore_async_get(vtherm.hass).async_dump_states()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("%s - Cannot persist the inhibition state: %s", self, err)
