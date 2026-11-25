# pylint: disable=line-too-long
""" Tests of the is_finite_number helper (Requirements 7.3) """
import pytest

from custom_components.versatile_thermostat.commons import is_finite_number


@pytest.mark.parametrize("value", [0, 1, -5, 10**12])
def test_int_is_finite_number(value):
    """Integers are finite numbers"""
    assert is_finite_number(value) is True


@pytest.mark.parametrize("value", [0.0, 1.5, -20.3, 1e300])
def test_float_is_finite_number(value):
    """Finite floats are finite numbers"""
    assert is_finite_number(value) is True


@pytest.mark.parametrize("value", [True, False])
def test_bool_is_not_number(value):
    """Booleans are rejected"""
    assert is_finite_number(value) is False


def test_nan_is_not_finite():
    """NaN is rejected"""
    assert is_finite_number(float("nan")) is False


@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
def test_infinity_is_not_finite(value):
    """+inf and -inf are rejected"""
    assert is_finite_number(value) is False


def test_none_is_not_number():
    """None is rejected"""
    assert is_finite_number(None) is False


@pytest.mark.parametrize("value", ["", "12", "abc", "nan"])
def test_str_is_not_number(value):
    """Strings are rejected, even numeric-looking ones"""
    assert is_finite_number(value) is False
