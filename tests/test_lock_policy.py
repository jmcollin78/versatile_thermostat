import pytest
from homeassistant.core import Context

from custom_components.versatile_thermostat.lock_policy import (
    INTERNAL_CONTEXT_PREFIX,
    LockDecision,
    LockPolicy,
    OP_INTERNAL_AUTO_REGULATION,
    OP_INTERNAL_CENTRAL,
    OP_INTERNAL_SAFETY,
    OP_INTERNAL_WINDOW_UPDATE,
    OP_SERVICE_SET_PRESENCE,
    OP_SET_FAN_MODE,
    OP_SET_HVAC_MODE,
    OP_SET_PRESET_MODE,
    OP_SET_SWING_MODE,
    OP_SET_TEMPERATURE,
    OP_TURN_OFF,
    OP_TURN_ON,
    classify_context,
    internal_context_reason,
    is_internal_context,
    make_internal_context,
)


class MockContext:
    """Mock Context object that allows setting arbitrary attributes for testing.
    
    Context objects use __slots__ and don't allow arbitrary attributes.
    This mock allows testing different context marker patterns (reason, origin, id).
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _make_reason_context(reason: str) -> MockContext:
    """Create a mock context with reason attribute (older/other patterns)."""
    return MockContext(reason=reason)


def _make_origin_context(origin: str) -> MockContext:
    """Create a mock context with origin attribute (some environments)."""
    return MockContext(origin=origin)


@pytest.mark.parametrize(
    "ctx_factory",
    [
        lambda op: make_internal_context(op),
        lambda op: _make_reason_context(internal_context_reason(op)),
        lambda op: _make_origin_context(internal_context_reason(op)),
    ],
)
@pytest.mark.parametrize(
    "operation",
    [
        OP_INTERNAL_WINDOW_UPDATE,
        OP_INTERNAL_SAFETY,
        OP_INTERNAL_AUTO_REGULATION,
        OP_INTERNAL_CENTRAL,
        OP_SET_TEMPERATURE,
    ],
)
def test_is_internal_context_positive(ctx_factory, operation):
    ctx = ctx_factory(operation)
    assert is_internal_context(ctx) is True
    assert classify_context(ctx) == "internal"


@pytest.mark.parametrize(
    "ctx",
    [
        None,
        Context(),  # no markers
        _make_reason_context("some.other.domain"),
        _make_origin_context("unrelated"),
    ],
)
def test_is_internal_context_negative(ctx):
    assert is_internal_context(ctx) is False
    # None must map to unknown; others to external
    expected = "unknown" if ctx is None else "external"
    assert classify_context(ctx) == expected


def test_classify_context_external_default():
    ctx = Context()  # normal HA context without VTherm markers
    assert classify_context(ctx) == "external"


@pytest.mark.parametrize(
    "is_locked,operation,ctx,expected",
    [
        # Unlocked: everything allowed
        (False, OP_SET_TEMPERATURE, None, LockDecision.ALLOW),
        (False, OP_SET_HVAC_MODE, Context(), LockDecision.ALLOW),
        (False, OP_SET_PRESET_MODE, make_internal_context(OP_INTERNAL_WINDOW_UPDATE), LockDecision.ALLOW),
    ],
)
def test_decide_unlocked(is_locked, operation, ctx, expected):
    assert LockPolicy.decide(is_locked, True, True, operation, ctx) is expected
    assert LockPolicy.should_allow(is_locked, True, True, operation, ctx) is (expected is LockDecision.ALLOW)


@pytest.mark.parametrize(
    "operation",
    [
        OP_SET_TEMPERATURE,
        OP_SET_HVAC_MODE,
        OP_TURN_ON,
        OP_TURN_OFF,
        OP_SET_PRESET_MODE,
        OP_SET_FAN_MODE,
        OP_SET_SWING_MODE,
        OP_SERVICE_SET_PRESENCE,
    ],
)
@pytest.mark.parametrize(
    "ctx",
    [
        None,  # unknown
        Context(),  # external / normal
    ],
)
def test_decide_locked_protected_external_or_unknown_denied(operation, ctx):
    decision = LockPolicy.decide(True, True, True, operation, ctx)
    assert decision is LockDecision.DENY_LOG
    assert LockPolicy.should_allow(True, True, True, operation, ctx) is False


@pytest.mark.parametrize(
    "operation",
    [
        "non_protected_operation",
    ],
)
@pytest.mark.parametrize(
    "ctx",
    [
        None,
        Context(),
    ],
)
def test_decide_locked_non_protected_external_or_unknown_allowed(operation, ctx):
    decision = LockPolicy.decide(True, True, True, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, True, True, operation, ctx) is True


@pytest.mark.parametrize(
    "operation",
    [
        # Internal markers: both explicit internal ops and protected ops
        OP_INTERNAL_WINDOW_UPDATE,
        OP_INTERNAL_SAFETY,
        OP_INTERNAL_AUTO_REGULATION,
        OP_INTERNAL_CENTRAL,
        OP_SET_TEMPERATURE,
        OP_SET_HVAC_MODE,
        OP_SET_PRESET_MODE,
    ],
)
def test_decide_locked_internal_always_allowed(operation):
    ctx = make_internal_context(operation, vt_unique_id="vt_1")
    decision = LockPolicy.decide(True, True, True, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, True, True, operation, ctx) is True
# Tests for lock granularity feature

PROTECTED_OPERATIONS = [
    OP_SET_TEMPERATURE,
    OP_SET_HVAC_MODE,
    OP_TURN_ON,
    OP_TURN_OFF,
    OP_SET_PRESET_MODE,
    OP_SET_FAN_MODE,
    OP_SET_SWING_MODE,
    OP_SERVICE_SET_PRESENCE,
]

INTERNAL_OPERATIONS = [
    OP_INTERNAL_WINDOW_UPDATE,
    OP_INTERNAL_SAFETY,
    OP_INTERNAL_AUTO_REGULATION,
    OP_INTERNAL_CENTRAL,
]

NON_PROTECTED_OPERATION = "non_protected_operation"

@pytest.mark.parametrize("operation", PROTECTED_OPERATIONS)
def test_decide_locked_both_user_denied(operation):
    """Ensure locked both denies protected operations from user contexts."""
    ctx = Context(user_id="test_user")
    decision = LockPolicy.decide(True, True, True, operation, ctx)
    assert decision is LockDecision.DENY_LOG
    assert LockPolicy.should_allow(True, True, True, operation, ctx) is False

@pytest.mark.parametrize("operation", PROTECTED_OPERATIONS)
def test_decide_locked_both_automation_denied(operation):
    """Enhance coverage: explicitly test automation contexts denied in locked both."""
    ctx = Context(user_id=None)
    decision = LockPolicy.decide(True, True, True, operation, ctx)
    assert decision is LockDecision.DENY_LOG
    assert LockPolicy.should_allow(True, True, True, operation, ctx) is False

# Locked users only: deny users, allow automations
@pytest.mark.parametrize("operation", PROTECTED_OPERATIONS)
def test_decide_locked_users_only_protected_user_denied(operation):
    ctx = Context(user_id="test_user")
    decision = LockPolicy.decide(True, True, False, operation, ctx)
    assert decision is LockDecision.DENY_LOG
    assert LockPolicy.should_allow(True, True, False, operation, ctx) is False

@pytest.mark.parametrize("operation", PROTECTED_OPERATIONS)
def test_decide_locked_users_only_protected_automation_allowed(operation):
    ctx = Context(user_id=None)
    decision = LockPolicy.decide(True, True, False, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, True, False, operation, ctx) is True

@pytest.mark.parametrize("operation", PROTECTED_OPERATIONS)
def test_decide_locked_users_only_protected_unknown_denied(operation):
    ctx = None
    decision = LockPolicy.decide(True, True, False, operation, ctx)
    assert decision is LockDecision.DENY_LOG
    assert LockPolicy.should_allow(True, True, False, operation, ctx) is False

@pytest.mark.parametrize(
    "ctx",
    [
        None,
        Context(user_id="test_user"),
        Context(user_id=None),
        make_internal_context(OP_SET_TEMPERATURE),
        Context(),
    ],
)
def test_decide_locked_users_only_non_protected_allowed(ctx):
    operation = NON_PROTECTED_OPERATION
    decision = LockPolicy.decide(True, True, False, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, True, False, operation, ctx) is True

@pytest.mark.parametrize("operation", list(INTERNAL_OPERATIONS + PROTECTED_OPERATIONS))
def test_decide_locked_users_only_internal_allowed(operation):
    ctx = make_internal_context(operation)
    decision = LockPolicy.decide(True, True, False, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, True, False, operation, ctx) is True

# Locked automations only: deny automations, allow users
@pytest.mark.parametrize("operation", PROTECTED_OPERATIONS)
def test_decide_locked_automations_only_protected_automation_denied(operation):
    ctx = Context(user_id=None)
    decision = LockPolicy.decide(True, False, True, operation, ctx)
    assert decision is LockDecision.DENY_LOG
    assert LockPolicy.should_allow(True, False, True, operation, ctx) is False

@pytest.mark.parametrize("operation", PROTECTED_OPERATIONS)
def test_decide_locked_automations_only_protected_user_allowed(operation):
    ctx = Context(user_id="test_user")
    decision = LockPolicy.decide(True, False, True, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, False, True, operation, ctx) is True

@pytest.mark.parametrize("operation", PROTECTED_OPERATIONS)
def test_decide_locked_automations_only_protected_unknown_denied(operation):
    ctx = None
    decision = LockPolicy.decide(True, False, True, operation, ctx)
    assert decision is LockDecision.DENY_LOG
    assert LockPolicy.should_allow(True, False, True, operation, ctx) is False

@pytest.mark.parametrize(
    "ctx",
    [
        None,
        Context(user_id="test_user"),
        Context(user_id=None),
        make_internal_context(OP_SET_TEMPERATURE),
        Context(),
    ],
)
def test_decide_locked_automations_only_non_protected_allowed(ctx):
    operation = NON_PROTECTED_OPERATION
    decision = LockPolicy.decide(True, False, True, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, False, True, operation, ctx) is True

@pytest.mark.parametrize("operation", list(INTERNAL_OPERATIONS + PROTECTED_OPERATIONS))
def test_decide_locked_automations_only_internal_allowed(operation):
    ctx = make_internal_context(operation)
    decision = LockPolicy.decide(True, False, True, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, False, True, operation, ctx) is True

# Unlocked always allows, regardless of granularity settings
@pytest.mark.parametrize(
    "lock_users, lock_automations, operation, ctx",
    [
        (True, False, OP_SET_TEMPERATURE, Context(user_id="test_user")),
        (False, True, OP_SET_TEMPERATURE, Context(user_id=None)),
        (True, True, OP_SET_TEMPERATURE, None),
        (True, False, NON_PROTECTED_OPERATION, make_internal_context(OP_INTERNAL_SAFETY)),
        (False, True, OP_SET_HVAC_MODE, Context()),
    ],
)
def test_decide_unlocked_granularity(lock_users, lock_automations, operation, ctx):
    decision = LockPolicy.decide(False, lock_users, lock_automations, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(False, lock_users, lock_automations, operation, ctx) is True