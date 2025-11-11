"""
Lock and context handling utilities for Versatile Thermostat.

This module is the single source of truth for:
- Tagging VTherm internal operations.
- Classifying a Context as internal / external / unknown.
- Deciding if an operation is allowed when a thermostat is locked.

It is intentionally lightweight and import-safe for tests.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

from homeassistant.core import Context

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Operation identifiers
# ---------------------------------------------------------------------------

# External / service level operations
OP_SET_HVAC_MODE = "set_hvac_mode"
OP_TURN_ON = "turn_on"
OP_TURN_OFF = "turn_off"
OP_SET_TEMPERATURE = "set_temperature"
OP_SET_PRESET_MODE = "set_preset_mode"
OP_SET_FAN_MODE = "set_fan_mode"
OP_SET_SWING_MODE = "set_swing_mode"
OP_SERVICE_SET_PRESENCE = "service_set_presence"
OP_SERVICE_SET_PRESET_TEMPERATURE = "service_set_preset_temperature"
OP_SERVICE_SET_SAFETY = "service_set_safety"
OP_SERVICE_SET_WINDOW_BYPASS = "service_set_window_bypass_state"
OP_SERVICE_SET_HVAC_MODE_SLEEP = "service_set_hvac_mode_sleep"

# Internal operations
OP_INTERNAL_WINDOW_UPDATE = "internal_window_update"
OP_INTERNAL_SAFETY = "internal_safety"
OP_INTERNAL_AUTO_REGULATION = "internal_auto_regulation"
OP_INTERNAL_CENTRAL = "internal_central"

# ---------------------------------------------------------------------------
# Context markers
# ---------------------------------------------------------------------------

INTERNAL_CONTEXT_PREFIX = "versatile_thermostat.internal."


def internal_context_reason(operation: str, vt_unique_id: str | None = None) -> str:
    """Build a stable internal context reason string.

    Format:
      versatile_thermostat.internal.<operation>[.<vt_unique_id>]
    """
    base = f"{INTERNAL_CONTEXT_PREFIX}{operation}"
    if vt_unique_id:
        base += f".{vt_unique_id}"
    return base


# ---------------------------------------------------------------------------
# Internal context helper
# ---------------------------------------------------------------------------


def make_internal_context(operation: str, vt_unique_id: str | None = None) -> Context:
    """Create a Home Assistant Context flagged as a VTherm internal operation.

    Implementation notes:
    - Use only constructor parameters that exist on all supported HA versions.
    - Encode the internal marker into the `id` field to avoid touching attributes
      like `reason` or `origin` that may be slotted or version-dependent.
    """
    internal_id = internal_context_reason(operation, vt_unique_id)
    return Context(
        id=internal_id,
        user_id=None,
        parent_id=None,
    )


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def is_internal_context(context: Optional[Context]) -> bool:
    """Return True if the context represents an internal VTherm operation.

    We support:
    - reason-based tagging, if available.
    - origin-based tagging, if used.
    - id-based tagging, as used by make_internal_context.
    """
    if not context:
        return False

    reason = getattr(context, "reason", None)
    if isinstance(reason, str) and reason.startswith(INTERNAL_CONTEXT_PREFIX):
        return True

    origin = getattr(context, "origin", None)
    if isinstance(origin, str) and origin.startswith(INTERNAL_CONTEXT_PREFIX):
        return True

    ctx_id = getattr(context, "id", None)
    if isinstance(ctx_id, str) and ctx_id.startswith(INTERNAL_CONTEXT_PREFIX):
        return True

    return False


def classify_context(context: Optional[Context]) -> str:
    """Classify a context as 'internal', 'external', or 'unknown'."""
    if is_internal_context(context):
        return "internal"
    if context is None:
        return "unknown"
    return "external"


# ---------------------------------------------------------------------------
# Decision enum
# ---------------------------------------------------------------------------


class LockDecision(Enum):
    ALLOW = "allow"
    DENY_LOG = "deny_log"


# ---------------------------------------------------------------------------
# Lock policy
# ---------------------------------------------------------------------------


class LockPolicy:
    """Encapsulate all lock / operation decision logic."""

    # Operations that should be protected from external / unknown sources
    # while the thermostat is locked.
    PROTECTED_OPERATIONS = {
        OP_SET_HVAC_MODE,
        OP_TURN_ON,
        OP_TURN_OFF,
        OP_SET_TEMPERATURE,
        OP_SET_PRESET_MODE,
        OP_SET_FAN_MODE,
        OP_SET_SWING_MODE,
        OP_SERVICE_SET_PRESENCE,
        OP_SERVICE_SET_PRESET_TEMPERATURE,
        OP_SERVICE_SET_SAFETY,
        OP_SERVICE_SET_WINDOW_BYPASS,
        OP_SERVICE_SET_HVAC_MODE_SLEEP,
    }

    # Internal operations that are always allowed, regardless of lock state.
    INTERNAL_ALWAYS_ALLOWED = {
        OP_INTERNAL_WINDOW_UPDATE,
        OP_INTERNAL_SAFETY,
        OP_INTERNAL_AUTO_REGULATION,
        OP_INTERNAL_CENTRAL,
    }

    @staticmethod
    def decide(is_locked: bool, operation: str, context: Optional[Context]) -> LockDecision:
        """Decide whether an operation is allowed based on lock state and context."""

        # Not locked: always allow
        if not is_locked:
            return LockDecision.ALLOW

        classification = classify_context(context)

        # Internal calls are always allowed; callers decide what is reasonable.
        if classification == "internal":
            if (
                operation in LockPolicy.INTERNAL_ALWAYS_ALLOWED
                or operation in LockPolicy.PROTECTED_OPERATIONS
            ):
                return LockDecision.ALLOW
            return LockDecision.ALLOW

        # External or unknown while locked
        if operation in LockPolicy.PROTECTED_OPERATIONS:
            return LockDecision.DENY_LOG

        return LockDecision.ALLOW

    @staticmethod
    def should_allow(is_locked: bool, operation: str, context: Optional[Context]) -> bool:
        """Return True if the operation should be executed."""
        return LockPolicy.decide(is_locked, operation, context) == LockDecision.ALLOW


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------


def log_blocked(logger, entity_id: str, operation: str, context: Optional[Context]) -> None:
    """Standard logging for blocked operations (used by callers)."""
    classification = classify_context(context)
    ctx_id = getattr(context, "id", None) if context else None
    logger.info(
        "[VTherm] %s - Blocked %s while locked (source=%s, context_id=%s)",
        entity_id,
        operation,
        classification,
        ctx_id,
    )


__all__ = [
    # Ops
    "OP_SET_HVAC_MODE",
    "OP_TURN_ON",
    "OP_TURN_OFF",
    "OP_SET_TEMPERATURE",
    "OP_SET_PRESET_MODE",
    "OP_SET_FAN_MODE",
    "OP_SET_SWING_MODE",
    "OP_SERVICE_SET_PRESENCE",
    "OP_SERVICE_SET_PRESET_TEMPERATURE",
    "OP_SERVICE_SET_SAFETY",
    "OP_SERVICE_SET_WINDOW_BYPASS",
    "OP_SERVICE_SET_HVAC_MODE_SLEEP",
    "OP_INTERNAL_WINDOW_UPDATE",
    "OP_INTERNAL_SAFETY",
    "OP_INTERNAL_AUTO_REGULATION",
    "OP_INTERNAL_CENTRAL",
    # Context helpers
    "INTERNAL_CONTEXT_PREFIX",
    "internal_context_reason",
    "make_internal_context",
    "is_internal_context",
    "classify_context",
    # Lock policy
    "LockDecision",
    "LockPolicy",
    # Logging
    "log_blocked",
]