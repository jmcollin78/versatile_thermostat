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
    assert LockPolicy.decide(is_locked, operation, ctx) is expected
    assert LockPolicy.should_allow(is_locked, operation, ctx) is (expected is LockDecision.ALLOW)


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
    decision = LockPolicy.decide(True, operation, ctx)
    assert decision is LockDecision.DENY_LOG
    assert LockPolicy.should_allow(True, operation, ctx) is False


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
    decision = LockPolicy.decide(True, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, operation, ctx) is True


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
    decision = LockPolicy.decide(True, operation, ctx)
    assert decision is LockDecision.ALLOW
    assert LockPolicy.should_allow(True, operation, ctx) is True