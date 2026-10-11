# pylint: disable=line-too-long
"""Core runtime of the extensible VTherm inhibition (issue #2087).

An inhibition plugin registers an ``InterfaceInhibitionProviderFactory`` in the
VTherm API. For each VTherm, the first registered factory whose ``supports()``
accepts the VTherm creates the single ``InterfaceInhibitionProvider`` bound to
it. The provider reports a confirmed ``ACTIVE`` / ``INACTIVE`` / ``UNKNOWN``
status and the per-VTherm physical-stop policy.

This module owns the core side of the contract (controlled withdrawal):

- while the provider is ``ACTIVE`` (or an attached provider is ``UNKNOWN``)
  the VTherm control is withdrawn: the ``StateManager`` resolves ``OFF`` with
  the ``hvac_off_inhibition`` reason and no regulation, TPI, scheduler or
  repair command is sent to the underlyings;
- on entry, a single physical stop is sent, only when the policy is
  ``TURN_OFF``;
- on a confirmed ``INACTIVE``, the current requested state is applied once.

The runtime state is kept apart from ``VThermState``: the requested and
current states are never modified by the inhibition. It is published and
restored under ``specific_states.inhibition``.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE, State

from vtherm_api import (
    DEFAULT_INHIBITION_STOP_POLICY,
    InhibitionStatus,
    InhibitionStopPolicy,
    InhibitionTransition,
    InterfaceInhibitionProvider,
    InterfaceInhibitionProviderFactory,
)
from vtherm_api.log_collector import get_vtherm_logger

from .vtherm_central_api import VersatileThermostatAPI

if TYPE_CHECKING:
    from .base_thermostat import BaseThermostat

_LOGGER = get_vtherm_logger(__name__)

ATTR_INHIBITION = "inhibition"
INHIBITION_SCHEMA_VERSION = 1


class InhibitionProviderStatus(StrEnum):
    """Provider status seen by the core. ``ABSENT`` means no eligible factory."""

    ACTIVE = InhibitionStatus.ACTIVE.value
    INACTIVE = InhibitionStatus.INACTIVE.value
    UNKNOWN = InhibitionStatus.UNKNOWN.value
    ABSENT = "absent"


class InhibitionPhysicalStopResult(StrEnum):
    """Diagnostic of the single entry stop. It never claims the hardware state."""

    NOT_REQUIRED = "not_required"
    SENT = "sent"
    FAILED_OR_UNKNOWN = "failed_or_unknown"


class InhibitionErrorCode(StrEnum):
    """Stable error codes. They never contain source entities or values."""

    SUPPORTS_FAILED = "supports_failed"
    CREATE_FAILED = "create_failed"
    START_LISTENING_FAILED = "start_listening_failed"
    REFRESH_FAILED = "refresh_failed"
    RESTORE_FAILED = "restore_failed"
    INVALID_STATUS = "invalid_status"
    PROVIDER_UNREGISTERED = "provider_unregistered"
    PHYSICAL_STOP_FAILED = "physical_stop_failed"
    EXIT_RECONCILIATION_FAILED = "exit_reconciliation_failed"


class InhibitionProviderConflictError(Exception):
    """A second eligible inhibition factory for a VTherm that already has one.

    The first registered eligible factory is retained, the other one is
    rejected for this VTherm. The error is logged and kept in the runtime
    diagnostics; it is never raised into the Home Assistant loop.
    """

    def __init__(self, vtherm_name: str, retained: str, rejected: str) -> None:
        self.vtherm_name = vtherm_name
        self.retained = retained
        self.rejected = rejected
        super().__init__(
            f"{vtherm_name} - inhibition provider conflict: '{retained}' is retained, "
            f"'{rejected}' is rejected (only one inhibition provider is allowed per VTherm)"
        )

    def as_dict(self) -> dict[str, str]:
        """Structured view of the conflict"""
        return {"retained": self.retained, "rejected": self.rejected}


def to_inhibition_status(value: Any) -> InhibitionStatus | None:
    """Convert a provider value into an InhibitionStatus. None if invalid."""
    try:
        return InhibitionStatus(value)
    except ValueError:
        return None


def to_inhibition_stop_policy(value: Any) -> InhibitionStopPolicy:
    """Convert a provider value into a policy. Invalid or absent means TURN_OFF."""
    try:
        return InhibitionStopPolicy(value)
    except ValueError:
        return DEFAULT_INHIBITION_STOP_POLICY


@dataclass
class InhibitionRuntimeState:
    """Core withdrawal state of one VTherm, distinct from VThermState."""

    provider_name: str | None = None
    provider_status: InhibitionProviderStatus = InhibitionProviderStatus.ABSENT
    withdrawal_active: bool = False
    awaiting_confirmation: bool = False
    effective_stop_policy: InhibitionStopPolicy = DEFAULT_INHIBITION_STOP_POLICY
    entry_handled: bool = False
    physical_stop_emitted: bool = False
    physical_stop_result: InhibitionPhysicalStopResult | None = None
    last_transition_at: datetime | None = None
    last_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for the entity attributes (and so for the restart memory)"""
        return {
            "schema_version": INHIBITION_SCHEMA_VERSION,
            "provider_name": self.provider_name,
            "provider_status": str(self.provider_status),
            "withdrawal_active": self.withdrawal_active,
            "awaiting_confirmation": self.awaiting_confirmation,
            "effective_stop_policy": str(self.effective_stop_policy),
            "entry_handled": self.entry_handled,
            "physical_stop_emitted": self.physical_stop_emitted,
            "physical_stop_result": str(self.physical_stop_result) if self.physical_stop_result else None,
            "last_transition_at": self.last_transition_at.isoformat() if self.last_transition_at else None,
            "last_error_code": self.last_error_code,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "InhibitionRuntimeState | None":
        """Rebuild a snapshot from the attributes. None if missing or not understood."""
        if not isinstance(data, dict) or data.get("schema_version") != INHIBITION_SCHEMA_VERSION:
            return None

        try:
            status = InhibitionProviderStatus(data.get("provider_status") or InhibitionProviderStatus.ABSENT)
        except ValueError:
            status = InhibitionProviderStatus.UNKNOWN
        try:
            result = InhibitionPhysicalStopResult(data["physical_stop_result"]) if data.get("physical_stop_result") else None
        except ValueError:
            result = InhibitionPhysicalStopResult.FAILED_OR_UNKNOWN
        last_transition_at = None
        if isinstance(data.get("last_transition_at"), str):
            try:
                last_transition_at = datetime.fromisoformat(data["last_transition_at"])
            except ValueError:
                last_transition_at = None

        return cls(
            provider_name=data.get("provider_name"),
            provider_status=status,
            withdrawal_active=data.get("withdrawal_active") is True,
            awaiting_confirmation=data.get("awaiting_confirmation") is True,
            effective_stop_policy=to_inhibition_stop_policy(data.get("effective_stop_policy")),
            entry_handled=data.get("entry_handled") is True,
            physical_stop_emitted=data.get("physical_stop_emitted") is True,
            physical_stop_result=result,
            last_transition_at=last_transition_at,
            last_error_code=data.get("last_error_code"),
        )


class InhibitionManager:
    """Attach the inhibition provider of a VTherm and apply its transitions.

    All the transitions are serialized by a lock. Calls into the provider that
    may notify transitions (refresh) are done outside of the lock.
    """

    def __init__(self, vtherm: "BaseThermostat") -> None:
        self._vtherm = vtherm
        self._state = InhibitionRuntimeState()
        self._factory: InterfaceInhibitionProviderFactory | None = None
        self._provider: InterfaceInhibitionProvider | None = None
        self._remove_callback: CALLBACK_TYPE | None = None
        # Incremented on each attach / detach so that a late callback of a
        # previous provider instance is ignored
        self._generation: int = 0
        self._last_sequence: int | None = None
        # Last policy known from the provider or from the restored snapshot.
        # Used when the provider is unusable (UNKNOWN after an error)
        self._known_policy: InhibitionStopPolicy | None = None
        self._conflicts: dict[str, InhibitionProviderConflictError] = {}
        self._lock = asyncio.Lock()
        self._is_started = False

    def __str__(self) -> str:
        return f"InhibitionManager-{self._vtherm}"

    @property
    def state(self) -> InhibitionRuntimeState:
        """The runtime state"""
        return self._state

    @property
    def provider(self) -> InterfaceInhibitionProvider | None:
        """The attached provider instance, if usable"""
        return self._provider

    @property
    def provider_name(self) -> str | None:
        """The name of the attached provider (None means ABSENT)"""
        return self._state.provider_name

    @property
    def is_attached(self) -> bool:
        """True if an inhibition provider (possibly failing) is attached"""
        return self._state.provider_name is not None

    @property
    def is_withdrawn(self) -> bool:
        """True if the VTherm control is withdrawn (confirmed ACTIVE or pending UNKNOWN)"""
        return self.is_attached and self._state.withdrawal_active

    @property
    def conflicts(self) -> list[InhibitionProviderConflictError]:
        """The rejected providers of this VTherm"""
        return list(self._conflicts.values())

    def as_dict(self) -> dict[str, Any]:
        """The ``specific_states.inhibition`` attribute block"""
        ret = self._state.to_dict()
        ret["rejected_providers"] = [conflict.rejected for conflict in self._conflicts.values()]
        return ret

    ##
    ## Discovery and attachment
    ##

    @staticmethod
    def _factory_name(factory: InterfaceInhibitionProviderFactory) -> str:
        """Return the stable name of a factory"""
        return (getattr(factory, "name", "") or "").strip()

    def discover(self) -> bool:
        """Attach the first eligible registered factory (registration order).

        Later eligible factories are rejected with a logged conflict. A slot
        whose provider failed or was unregistered is retried with the factory
        registered under the same name. Returns True if a provider slot has
        been (re)attached.
        """
        api = VersatileThermostatAPI.get_vtherm_api(self._vtherm.hass)
        if api is None or not hasattr(api, "get_inhibition_provider_factories"):
            return False

        attached = False
        for factory in api.get_inhibition_provider_factories():
            name = self._factory_name(factory)
            if not name:
                continue

            if self._state.provider_name is None:
                attached = self._try_attach(factory, name) or attached
                continue

            if name == self._state.provider_name:
                if self._provider is None:
                    # failed or unregistered provider: try again
                    attached = self._try_attach(factory, name) or attached
                continue

            if name in self._conflicts:
                continue

            try:
                eligible = bool(factory.supports(self._vtherm))
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.error(
                    "%s - inhibition provider factory '%s' failed in supports(): %s",
                    self._vtherm,
                    name,
                    exc,
                )
                eligible = True

            if eligible:
                conflict = InhibitionProviderConflictError(str(self._vtherm), self._state.provider_name, name)
                self._conflicts[name] = conflict
                _LOGGER.error("%s", conflict)

        return attached

    def _try_attach(self, factory: InterfaceInhibitionProviderFactory, name: str) -> bool:
        """Evaluate one factory. Returns True if the slot is taken by it."""
        try:
            eligible = bool(factory.supports(self._vtherm))
        except Exception as exc:  # pylint: disable=broad-except
            # A failing candidate is never silently ignored: it takes the slot
            # in UNKNOWN so that the VTherm is safely withdrawn
            _LOGGER.error(
                "%s - inhibition provider factory '%s' failed in supports(): %s. The VTherm is withdrawn until a confirmed INACTIVE",
                self._vtherm,
                name,
                exc,
            )
            self._attach_slot(name, factory, None, InhibitionErrorCode.SUPPORTS_FAILED)
            return True

        if not eligible:
            if self._state.provider_name == name and self._provider is None:
                _LOGGER.warning(
                    "%s - inhibition provider factory '%s' does not support this VTherm anymore. Releasing the inhibition",
                    self._vtherm,
                    name,
                )
                self._detach_slot()
                self._schedule(self._async_release_to_absent())
            return False

        try:
            provider = factory.create(self._vtherm)
            provider.post_init(self._vtherm.entry_infos)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error(
                "%s - inhibition provider factory '%s' failed to create its provider: %s. The VTherm is withdrawn until a confirmed INACTIVE",
                self._vtherm,
                name,
                exc,
            )
            self._attach_slot(name, factory, None, InhibitionErrorCode.CREATE_FAILED)
            return True

        self._attach_slot(name, factory, provider, None)
        return True

    def _attach_slot(
        self,
        name: str,
        factory: InterfaceInhibitionProviderFactory,
        provider: InterfaceInhibitionProvider | None,
        error_code: str | None,
    ):
        """Bind a provider slot. The status is UNKNOWN until the first confirmation."""
        self._generation += 1
        self._factory = factory
        self._provider = provider
        self._remove_callback = None
        self._last_sequence = None
        self._state.provider_name = name
        self._state.provider_status = InhibitionProviderStatus.UNKNOWN
        self._state.awaiting_confirmation = True
        self._state.last_error_code = error_code
        if not self._state.withdrawal_active:
            self._begin_withdrawal(self._resolve_policy(None))

        if provider is not None:
            _LOGGER.info(
                "%s - inhibition provider '%s' attached. Status is unknown until its first confirmation",
                self._vtherm,
                name,
            )
        else:
            _LOGGER.warning(
                "%s - inhibition provider '%s' attached in error (%s). Status is unknown",
                self._vtherm,
                name,
                error_code,
            )

    def _detach_slot(self):
        """Forget the provider slot (back to ABSENT)"""
        self._generation += 1
        self._factory = None
        self._provider = None
        self._remove_callback = None
        self._state.provider_name = None
        self._state.provider_status = InhibitionProviderStatus.ABSENT
        self._state.awaiting_confirmation = False

    def _schedule(self, coro):
        """Run a coroutine in the HA loop (used from synchronous paths)"""
        hass = self._vtherm.hass
        if hass is None:
            coro.close()
            return
        hass.async_create_task(coro)

    ##
    ## Lifecycle
    ##

    def restore_state(self, old_state: State | None):
        """Restore the core snapshot, then give the old state to the provider.

        Called from ``get_my_previous_state()`` before the first reconciliation.
        A state without the block (V0) means no previous inhibition.
        """
        snapshot = None
        if old_state is not None:
            specific_states = old_state.attributes.get("specific_states", {}) or {}
            if isinstance(specific_states, dict):
                snapshot = InhibitionRuntimeState.from_dict(specific_states.get(ATTR_INHIBITION))

        if snapshot is not None:
            self._known_policy = snapshot.effective_stop_policy

        if not self.is_attached:
            if snapshot is not None and snapshot.withdrawal_active:
                _LOGGER.info(
                    "%s - a previous inhibition withdrawal is ignored because no inhibition provider supports this VTherm anymore",
                    self._vtherm,
                )
            return

        if snapshot is not None:
            self._state.last_transition_at = snapshot.last_transition_at
            if snapshot.withdrawal_active:
                # Keep the guard of the current activation: no second stop
                self._state.withdrawal_active = True
                self._state.effective_stop_policy = snapshot.effective_stop_policy
                self._state.entry_handled = snapshot.entry_handled
                self._state.physical_stop_emitted = snapshot.physical_stop_emitted
                self._state.physical_stop_result = snapshot.physical_stop_result
                _LOGGER.info(
                    "%s - inhibition withdrawal restored (entry_handled=%s, physical_stop_emitted=%s, policy=%s). Waiting for the provider confirmation",
                    self._vtherm,
                    snapshot.entry_handled,
                    snapshot.physical_stop_emitted,
                    snapshot.effective_stop_policy,
                )
            elif not self._state.entry_handled:
                self._state.effective_stop_policy = self._resolve_policy(None)

        if self._provider is not None and old_state is not None:
            try:
                self._provider.restore_state(old_state)
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.error("%s - inhibition provider '%s' failed to restore its state: %s", self._vtherm, self.provider_name, exc)
                self._state.last_error_code = InhibitionErrorCode.RESTORE_FAILED

    async def async_start(self):
        """Start the provider and reconcile its initial status (VTherm startup)"""
        if self._is_started:
            return
        self._is_started = True
        await self._async_start_provider()

    async def _async_start_provider(self):
        """Register the callback, start listening and do the initial refresh"""
        if not self.is_attached:
            return

        provider = self._provider
        if provider is None:
            # Failing provider: stays UNKNOWN. The safe withdrawal is completed
            # as soon as the VTherm is ready
            async with self._lock:
                await self._async_complete_entry()
            return

        generation = self._generation
        try:
            self._remove_callback = provider.register_transition_callback(self._make_callback(generation))
            await provider.async_start_listening()
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("%s - inhibition provider '%s' failed to start listening: %s", self._vtherm, self.provider_name, exc)
            async with self._lock:
                if generation == self._generation:
                    await self._async_apply_status(InhibitionStatus.UNKNOWN, None, InhibitionErrorCode.START_LISTENING_FAILED)
            return

        await self.async_refresh()

    async def async_refresh(self):
        """Ask the provider for its confirmed status and apply it"""
        provider = self._provider
        generation = self._generation
        if provider is None:
            return

        error_code = None
        policy = None
        try:
            status = await provider.async_refresh_state()
            policy = provider.physical_stop_policy
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("%s - inhibition provider '%s' failed to refresh its state: %s", self._vtherm, self.provider_name, exc)
            status = InhibitionStatus.UNKNOWN
            error_code = InhibitionErrorCode.REFRESH_FAILED

        async with self._lock:
            if generation != self._generation:
                return
            await self._async_apply_status(status, policy, error_code)

    async def async_on_vtherm_ready(self):
        """Complete a deferred entry once the underlyings are initialized"""
        async with self._lock:
            await self._async_complete_entry()

    async def async_on_factories_changed(self):
        """A factory has been registered after the VTherm startup (late plugin)"""
        if not self._is_started or self._vtherm.is_removed:
            return

        previous_provider = self._provider
        previous_name = self._state.provider_name
        self.discover()
        if self._provider is not None and self._provider is not previous_provider:
            await self._async_start_provider()
        elif self.is_attached and previous_name is None:
            # new failing provider
            await self._async_start_provider()

    async def async_on_factory_unregistered(self, name: str):
        """The factory of the attached provider has been unregistered (plugin unload)"""
        if self._state.provider_name != name or self._provider is None:
            return

        _LOGGER.warning(
            "%s - inhibition provider '%s' has been unregistered. The VTherm is withdrawn until a provider confirms INACTIVE",
            self._vtherm,
            name,
        )
        self._generation += 1
        remove_callback = self._remove_callback
        self._remove_callback = None
        self._provider = None
        self._factory = None
        if remove_callback:
            try:
                remove_callback()
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.debug("%s - error while removing the inhibition callback: %s", self._vtherm, exc)

        async with self._lock:
            await self._async_apply_status(InhibitionStatus.UNKNOWN, None, InhibitionErrorCode.PROVIDER_UNREGISTERED)

    def stop(self):
        """Detach the provider when the VTherm is removed. No resume command is sent.

        The runtime state is kept, so the last safe withdrawal stays persisted.
        """
        provider = self._provider
        remove_callback = self._remove_callback
        self._generation += 1
        self._remove_callback = None
        self._provider = None
        self._is_started = False
        if provider is not None:
            try:
                provider.stop_listening()
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.error("%s - inhibition provider '%s' failed to stop listening: %s", self._vtherm, self.provider_name, exc)
        if remove_callback is not None:
            try:
                remove_callback()
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.debug("%s - error while removing the inhibition callback: %s", self._vtherm, exc)
        if provider is not None:
            _LOGGER.info("%s - inhibition provider '%s' detached", self._vtherm, self.provider_name)

    ##
    ## Transitions
    ##

    def _make_callback(self, generation: int):
        """Build the transition callback bound to one provider instance"""

        async def _on_transition(transition: InhibitionTransition) -> None:
            await self._async_on_transition(generation, transition)

        return _on_transition

    async def _async_on_transition(self, generation: int, transition: InhibitionTransition):
        """Handle a confirmed transition notified by the provider"""
        try:
            async with self._lock:
                if generation != self._generation or self._vtherm.is_removed:
                    _LOGGER.debug("%s - stale inhibition transition ignored: %s", self._vtherm, transition)
                    return

                provider_name = getattr(transition, "provider_name", None)
                if provider_name and provider_name != self._state.provider_name:
                    _LOGGER.warning(
                        "%s - inhibition transition from '%s' ignored: the attached provider is '%s'",
                        self._vtherm,
                        provider_name,
                        self._state.provider_name,
                    )
                    return

                sequence = getattr(transition, "sequence", 0) or 0
                if sequence:
                    if self._last_sequence is not None and sequence <= self._last_sequence:
                        _LOGGER.debug("%s - replayed inhibition transition %s ignored", self._vtherm, sequence)
                        return
                    self._last_sequence = sequence

                await self._async_apply_status(transition.new_status, getattr(transition, "stop_policy", None), None)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("%s - error while handling the inhibition transition %s: %s", self._vtherm, transition, exc)

    def _resolve_policy(self, policy: Any) -> InhibitionStopPolicy:
        """Effective policy: notified one, then provider, then last known, then TURN_OFF"""
        if policy is not None:
            ret = to_inhibition_stop_policy(policy)
            self._known_policy = ret
            return ret

        if self._provider is not None:
            try:
                ret = to_inhibition_stop_policy(self._provider.physical_stop_policy)
                self._known_policy = ret
                return ret
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.warning("%s - cannot read the inhibition stop policy: %s", self._vtherm, exc)

        if self._known_policy is not None:
            return self._known_policy

        return DEFAULT_INHIBITION_STOP_POLICY

    def _begin_withdrawal(self, policy: InhibitionStopPolicy):
        """Start a new activation. The policy is captured until the exit"""
        self._state.withdrawal_active = True
        self._state.effective_stop_policy = policy
        self._state.entry_handled = False
        self._state.physical_stop_emitted = False
        self._state.physical_stop_result = None

    async def _async_apply_status(self, raw_status: Any, raw_policy: Any, error_code: str | None):
        """Apply a provider status. Must be called with the lock held"""
        status = to_inhibition_status(raw_status)
        if status is None:
            _LOGGER.error("%s - invalid inhibition status '%s' from provider '%s'. Using unknown", self._vtherm, raw_status, self.provider_name)
            status = InhibitionStatus.UNKNOWN
            error_code = InhibitionErrorCode.INVALID_STATUS

        if raw_policy is not None:
            self._known_policy = to_inhibition_stop_policy(raw_policy)

        old_status = self._state.provider_status
        new_status = InhibitionProviderStatus(status.value)
        changed = new_status != old_status
        self._state.provider_status = new_status

        if error_code is not None:
            changed = changed or self._state.last_error_code != error_code
            self._state.last_error_code = error_code
        elif status != InhibitionStatus.UNKNOWN and self._state.last_error_code is not None:
            self._state.last_error_code = None
            changed = True

        if status == InhibitionStatus.INACTIVE:
            self._state.awaiting_confirmation = False
            if self._state.withdrawal_active:
                await self._async_exit()
                changed = True
        else:
            self._state.awaiting_confirmation = status == InhibitionStatus.UNKNOWN
            if not self._state.withdrawal_active:
                self._begin_withdrawal(self._resolve_policy(raw_policy))
                changed = True
                if status == InhibitionStatus.ACTIVE:
                    _LOGGER.info(
                        "%s - inhibition entry: provider '%s' is active (policy %s)",
                        self._vtherm,
                        self.provider_name,
                        self._state.effective_stop_policy,
                    )
                else:
                    _LOGGER.warning(
                        "%s - inhibition provider '%s' is unknown: the VTherm control is withdrawn until a confirmed INACTIVE (policy %s)",
                        self._vtherm,
                        self.provider_name,
                        self._state.effective_stop_policy,
                    )
            elif not self._state.entry_handled and raw_policy is not None:
                # The entry is still pending (VTherm not ready): take the last policy
                self._state.effective_stop_policy = to_inhibition_stop_policy(raw_policy)
            elif changed and status == InhibitionStatus.UNKNOWN:
                _LOGGER.warning(
                    "%s - inhibition provider '%s' is unknown: the withdrawal is kept until a confirmed INACTIVE",
                    self._vtherm,
                    self.provider_name,
                )

            await self._async_complete_entry()

        if changed:
            self._state.last_transition_at = self._vtherm.now
            _LOGGER.info(
                "%s - inhibition status of provider '%s' changed from %s to %s (withdrawal_active=%s)",
                self._vtherm,
                self.provider_name,
                old_status,
                new_status,
                self._state.withdrawal_active,
            )
            self._publish()

    async def _async_complete_entry(self):
        """Resolve OFF, suspend the control and send the conditional single stop.

        Must be called with the lock held. Deferred until the VTherm is ready.
        """
        state = self._state
        if not self.is_withdrawn or state.entry_handled:
            return

        vtherm = self._vtherm
        if not vtherm.is_ready:
            _LOGGER.debug("%s - inhibition entry deferred until the VTherm is ready", vtherm)
            return

        # Recalculate and publish. update_states sends nothing to the underlyings
        # while the control is withdrawn: the stop below is the only command.
        try:
            vtherm.requested_state.force_changed()
            await vtherm.update_states(force=True)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("%s - error while recalculating the state on inhibition entry: %s", vtherm, exc)

        await vtherm.async_inhibition_suspend_control()

        if state.effective_stop_policy == InhibitionStopPolicy.TURN_OFF:
            if not state.physical_stop_emitted:
                # Persisted as emitted even if it fails: never resent automatically
                state.physical_stop_emitted = True
                try:
                    await vtherm.async_inhibition_physical_stop()
                    state.physical_stop_result = InhibitionPhysicalStopResult.SENT
                    _LOGGER.info("%s - inhibition entry stop sent to the underlyings (policy %s)", vtherm, state.effective_stop_policy)
                except Exception as exc:  # pylint: disable=broad-except
                    state.physical_stop_result = InhibitionPhysicalStopResult.FAILED_OR_UNKNOWN
                    state.last_error_code = InhibitionErrorCode.PHYSICAL_STOP_FAILED
                    _LOGGER.error("%s - inhibition entry stop failed: %s. It will not be resent automatically", vtherm, exc)
        else:
            state.physical_stop_result = InhibitionPhysicalStopResult.NOT_REQUIRED
            _LOGGER.info("%s - inhibition entry stop skipped (policy %s)", vtherm, state.effective_stop_policy)

        state.entry_handled = True
        _LOGGER.info("%s - inhibition: VTherm control withdrawn, regulation and repair are suspended", vtherm)
        self._publish()

    async def _async_exit(self):
        """Leave the withdrawal and apply the current requested state once.

        Must be called with the lock held.
        """
        state = self._state
        vtherm = self._vtherm
        if state.entry_handled:
            _LOGGER.info("%s - inhibition exit: provider '%s' confirmed inactive. Applying the requested state %s", vtherm, self.provider_name, vtherm.requested_state)
        else:
            _LOGGER.info("%s - inhibition provider '%s' confirmed inactive before any withdrawal was applied", vtherm, self.provider_name)
        state.withdrawal_active = False
        state.awaiting_confirmation = False
        state.entry_handled = False
        state.physical_stop_emitted = False
        state.physical_stop_result = None

        if not vtherm.is_ready:
            # The startup reconciliation (init_underlyings_completed) applies it
            _LOGGER.debug("%s - inhibition exit reconciliation deferred to the VTherm startup", vtherm)
            return

        try:
            vtherm.requested_state.force_changed()
            await vtherm.update_states(force=True)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("%s - inhibition exit reconciliation failed: %s. The VTherm control stays withdrawn", vtherm, exc)
            state.withdrawal_active = True
            state.entry_handled = True
            state.last_error_code = InhibitionErrorCode.EXIT_RECONCILIATION_FAILED

    async def _async_release_to_absent(self):
        """The factory does not support the VTherm anymore: historic behavior"""
        async with self._lock:
            if self.is_attached or not self._state.withdrawal_active:
                return
            await self._async_exit()
            self._publish()

    def _publish(self):
        """Publish the VTherm attributes if it is running"""
        vtherm = self._vtherm
        if vtherm.is_removed or not vtherm.is_ready or vtherm.entity_id is None:
            return
        vtherm.update_custom_attributes()
        vtherm.async_write_ha_state()
