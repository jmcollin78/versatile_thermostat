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

How it works, step by step: documentation/tech-docs/inhibition_manager.md
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

from vtherm_api import InhibitionNotStartedError  # raised before the startup restore (vtherm_api >= 0.6.2)
from vtherm_api.log_collector import get_vtherm_logger

_LOGGER = get_vtherm_logger(__name__)

ATTR_INHIBITION = "inhibition"
INHIBITION_SCHEMA_VERSION = 1

ERROR_ENTRY_STOP_FAILED = "entry_stop_failed"
ERROR_EXIT_RECONCILE_FAILED = "exit_reconcile_failed"
ERROR_EXIT_RECONCILE_CANCELLED = "exit_reconcile_cancelled"

# Maximum number of reconciliation walks when other call chains are dropped during the exit
MAX_EXIT_RECONCILE_WALKS = 3

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
        # The snapshot is restored once per entity lifetime (async_startup may run twice).
        # set and unset are refused before (InhibitionNotStartedError).
        self._is_restored: bool = False
        # A command of another call chain was dropped while EXIT_RECONCILING
        self._blocked_during_exit: bool = False
        self._dump_scheduled: bool = False
        self._dump_task: asyncio.Task | None = None

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
    def is_restored(self) -> bool:
        """True once the VTherm restored its inhibition state at startup: set and unset
        are accepted from then on"""
        return self._is_restored

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
        """Restore the snapshot, once per entity lifetime (a config entry update can run
        async_startup twice). Must be called before any underlying command.
        A restart during the exit reconciliation is restored like a failed exit: inhibited,
        gate closed, and the entry stop sent again once ready if it was requested (the
        partial reconciliation may have restarted devices). The plugin has to call unset again.
        set and unset are refused until this has run, so nothing can override the snapshot."""
        if self._is_restored:
            _LOGGER.debug("%s - Snapshot already restored", self)
            return
        self._is_restored = True
        if old_state is None:
            return
        snapshot = (old_state.attributes.get("specific_states") or {}).get(ATTR_INHIBITION)
        if not isinstance(snapshot, dict) or snapshot.get("schema_version") != INHIBITION_SCHEMA_VERSION:
            return
        gate = snapshot.get("command_gate")
        self._is_used = True
        self._last_transition_at = snapshot.get("last_transition_at")
        self._last_error_code = snapshot.get("last_error_code")
        if not (snapshot.get("inhibited") is True or gate in (CommandGate.CLOSED, CommandGate.EXIT_RECONCILING)):
            return

        self._inhibited = True
        self._gate = CommandGate.CLOSED
        self._entry_stop_requested = snapshot.get("entry_stop_requested") is True
        # an interrupted exit may have restarted devices: the stop is due again
        self._entry_stop_completed = snapshot.get("entry_stop_completed") is True and gate != CommandGate.EXIT_RECONCILING
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

        if self._gate is CommandGate.EXIT_RECONCILING:
            self._blocked_during_exit = True
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
        """Enter the inhibition. Idempotent while inhibited.
        A cancellation after the gate is closed does not stop the entry: it is
        completed (OFF resolution, entry stop, persistence), then re-raised.
        Raises InhibitionNotStartedError before the startup restore."""
        self._check_restored()
        # Last call wins: an unset called after this set must not join an exit started before it
        self._exit_future = None
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
            self._persist()

            cancelled: asyncio.CancelledError | None = None
            try:
                await self._async_resolve_inhibited_state()
            except asyncio.CancelledError as err:
                cancelled = err
            try:
                await self._async_entry_stop_if_ready()
            except asyncio.CancelledError as err:
                cancelled = cancelled or err
            self._persist()
            await self._async_flush()
            if cancelled is not None:
                raise cancelled

    async def async_unset(self):
        """Leave the inhibition. A concurrent call joins the running exit and gets its
        outcome; if that exit was cancelled, the joiner runs its own exit.
        Raises if the exit reconciliation fails (the VTherm stays inhibited), and
        InhibitionNotStartedError before the startup restore."""
        self._check_restored()
        while (running := self._exit_future) is not None:
            try:
                await asyncio.shield(running)
                return
            except asyncio.CancelledError:
                if running.cancelled() and not _is_current_task_cancelling():
                    continue
                raise

        future = asyncio.get_running_loop().create_future()
        self._exit_future = future
        try:
            async with self._lock:
                try:
                    await self._async_exit()
                finally:
                    await self._async_flush()
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
            if self._exit_future is future:
                self._exit_future = None

    def _check_restored(self):
        if not self._is_restored:
            raise InhibitionNotStartedError(f"{self._vtherm} has not restored its inhibition state yet (startup not done)")

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
                        # already logged (last_error_code), the VTherm is inhibited again
                        pass
            elif self._is_entry_stop_pending:
                await self._async_entry_stop_if_ready()
                self._persist()

    @property
    def _is_entry_stop_pending(self) -> bool:
        return self._inhibited and self._gate is CommandGate.CLOSED and self._entry_stop_requested and not self._entry_stop_completed

    async def _async_resolve_inhibited_state(self):
        """Resolve the effective OFF. Every command it produces is dropped by the gate"""
        try:
            self._vtherm.requested_state.force_changed()
            await self._vtherm.update_states(force=True)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("%s - Error while resolving the inhibited state: %s", self, err)

    async def _async_entry_stop_if_ready(self):
        """Send the single entry stop if it is requested and not done yet.
        A cancellation does not interrupt it: it is re-raised at the end."""
        if not self._is_entry_stop_pending:
            return
        if not self._vtherm.is_ready:
            _LOGGER.info("%s - Entry stop deferred until the VTherm is ready", self)
            return

        cancelled: asyncio.CancelledError | None = None
        # Cancel the running cycle before the transaction: nothing it triggers may pass
        scheduler = self._vtherm.cycle_scheduler
        if scheduler:
            try:
                await scheduler.cancel_cycle()
            except asyncio.CancelledError as err:
                cancelled = err

        failed = False
        with self._transaction_scope(InhibitionTransaction.ENTRY_STOP):
            for under in self._vtherm.all_underlying_entities:
                try:
                    await under.async_inhibition_stop()
                except asyncio.CancelledError as err:
                    cancelled = cancelled or err
                except Exception as err:  # pylint: disable=broad-except
                    failed = True
                    _LOGGER.error("%s - Entry stop failed for %s: %s", self, under, err)
        self._entry_stop_completed = True
        if failed:
            self._last_error_code = ERROR_ENTRY_STOP_FAILED
        self._touch()
        _LOGGER.info("%s - Entry stop sent to the underlyings", self)
        if cancelled is not None:
            raise cancelled

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
        self._persist()

        # #2049 bootstrap seed: now, even if the VTherm is not ready. After a restart while
        # inhibited the gate dropped the startup seed, and an unknown valve degree keeps the
        # VTherm not ready: the reconciliation waiting for ready would never run.
        try:
            with self._transaction_scope(InhibitionTransaction.EXIT_RECONCILE):
                for under in self._vtherm.all_underlying_entities:
                    await under.async_inhibition_exit_seed()
        except (Exception, asyncio.CancelledError) as err:
            await self._async_rollback_exit(err)
            raise

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
                for walk in range(MAX_EXIT_RECONCILE_WALKS):
                    if walk:
                        # Another call chain was dropped during the walk: it may have changed
                        # the current state and the caches. Walk again before opening the gate.
                        _LOGGER.info("%s - Commands were dropped during the reconciliation. Reconciling again", self)
                    self._blocked_during_exit = False
                    # Commands dropped during the inhibition may have updated the last sent caches
                    for under in vtherm.all_underlying_entities:
                        await under.async_inhibition_resync()
                    # Walk every underlying even if the effective mode does not change (OFF -> OFF)
                    vtherm.requested_state.force_changed()
                    vtherm.current_state.force_changed()
                    await vtherm.update_states(force=True)
                    if not self._blocked_during_exit:
                        break
        except (Exception, asyncio.CancelledError) as err:
            await self._async_rollback_exit(err)
            raise

        self._gate = CommandGate.OPEN
        self._entry_stop_requested = False
        self._entry_stop_completed = False
        self._last_error_code = None
        self._touch()
        _LOGGER.info("%s - Exit reconciliation done. Normal operation resumed", self)
        self._persist()

        if self._blocked_during_exit:
            # Still dropping commands after the last walk: open anyway (the next cycle
            # applies the state) and re-arm what a dropped command cancelled
            self._blocked_during_exit = False
            _LOGGER.warning("%s - Commands were still dropped after %d reconciliation walks. Gate opened", self, MAX_EXIT_RECONCILE_WALKS)
            for under in vtherm.all_underlying_entities:
                under.on_inhibition_gate_opened()

    async def _async_rollback_exit(self, err: BaseException):
        """Back to a safe inhibited state after a failed or cancelled exit. The entry stop
        is sent again if it was requested: the partial reconciliation may have restarted devices."""
        cancelled = isinstance(err, asyncio.CancelledError)
        self._inhibited = True
        self._gate = CommandGate.CLOSED
        self._last_error_code = ERROR_EXIT_RECONCILE_CANCELLED if cancelled else ERROR_EXIT_RECONCILE_FAILED
        if self._entry_stop_requested:
            self._entry_stop_completed = False
        self._touch()
        self._persist()
        _LOGGER.error("%s - Exit reconciliation %s, the VTherm stays inhibited: %s", self, "cancelled" if cancelled else "failed", err)
        try:
            await self._async_resolve_inhibited_state()
            await self._async_entry_stop_if_ready()
        except asyncio.CancelledError:
            _LOGGER.warning("%s - Rollback of the exit interrupted by a cancellation", self)
        self._persist()

    def _touch(self):
        self._last_transition_at = dt_util.now().isoformat()

    def _persist(self):
        """Publish the snapshot now and schedule a dump of the restore states (attributes
        alone are dumped every 15 min). Transitions of the same loop turn share one dump."""
        vtherm = self._vtherm
        if vtherm.hass is None or vtherm.entity_id is None:
            return
        try:
            vtherm.update_custom_attributes()
            vtherm.async_write_ha_state()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("%s - Cannot publish the inhibition state: %s", self, err)
        if not self._dump_scheduled:
            self._dump_scheduled = True
            self._dump_task = vtherm.hass.async_create_task(self._async_dump(), eager_start=False)

    async def _async_flush(self):
        """Wait for the last scheduled dump: set and unset return once saved"""
        if (task := self._dump_task) is not None and not task.done():
            await asyncio.shield(task)

    async def _async_dump(self):
        """Save the restore states. A transition after this point schedules another dump."""
        self._dump_scheduled = False
        try:
            await restore_async_get(self._vtherm.hass).async_dump_states()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("%s - Cannot persist the inhibition state: %s", self, err)


def _is_current_task_cancelling() -> bool:
    """True if a cancellation was requested for the running task"""
    task = asyncio.current_task()
    return task is not None and task.cancelling() > 0
