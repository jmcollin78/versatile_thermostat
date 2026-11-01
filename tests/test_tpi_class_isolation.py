"""Domain instances must keep thermostat contexts and calculations independent."""

from datetime import timedelta

import numpy as np
import pytest

from custom_components.versatile_thermostat import tpi_history, tpi_identification
from .test_tpi_history import START, SOURCES, histories
from .test_tpi_identification import synthetic


def test_identification_instances_do_not_share_their_grid():
    good, _, _ = synthetic()
    bad, _, _ = synthetic()
    bad.temp_in = -bad.temp_in + 40
    first = tpi_identification.TPIIdentification(good, 10)
    second = tpi_identification.TPIIdentification(bad, 10)
    expected, _ = first.fit_resolution(10)
    with pytest.raises(
        tpi_identification.IdentificationError, match="invalid_physical_model"
    ):
        second.fit_resolution(10)
    actual, _ = first.fit_resolution(10)
    assert actual == expected


def test_history_instances_do_not_share_their_sources():
    states = histories(7)
    first = tpi_history.TPIHistory(None, dict(SOURCES))
    second = tpi_history.TPIHistory(None, {**SOURCES, "inverse_switch": True})
    normal, _ = first.build_grid(states, START, START + timedelta(days=7))
    inverse, _ = second.build_grid(states, START, START + timedelta(days=7))
    repeated, _ = first.build_grid(states, START, START + timedelta(days=7))
    np.testing.assert_equal(normal.heater, np.ones(len(normal.time)))
    np.testing.assert_equal(inverse.heater, np.zeros(len(inverse.time)))
    np.testing.assert_equal(repeated.heater, normal.heater)
