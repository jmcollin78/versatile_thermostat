# pylint: disable=unused-argument, line-too-long
""" Test the OpenWindow algorithm """

from datetime import datetime, timedelta
from custom_components.versatile_thermostat.open_window_algorithm import WindowOpenDetectionAlgorithm

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_open_window_algo(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the Algo"""

    the_algo = WindowOpenDetectionAlgorithm(1.0, 0.0)
    assert the_algo.last_slope is None

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    event_timestamp = now - timedelta(minutes=5)
    last_slope = the_algo.add_temp_measurement(
        temperature=10, datetime_measure=event_timestamp
    )

    # We need at least 2 measurement
    assert last_slope is None
    assert the_algo.last_slope is None
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    event_timestamp = now - timedelta(minutes=4)
    last_slope = the_algo.add_temp_measurement(
        temperature=10, datetime_measure=event_timestamp
    )

    # No slope because same temperature
    assert last_slope == 0
    assert the_algo.last_slope == 0
    assert the_algo.is_window_close_detected() is True
    assert the_algo.is_window_open_detected() is False

    event_timestamp = now - timedelta(minutes=3)
    last_slope = the_algo.add_temp_measurement(
        temperature=9, datetime_measure=event_timestamp
    )

    # A slope is calculated
    assert last_slope == -0.5
    assert the_algo.last_slope == -0.5
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    # A new temperature with 2 degre less in one minute (value will be rejected)
    event_timestamp = now - timedelta(minutes=2)
    last_slope = the_algo.add_temp_measurement(
        temperature=7, datetime_measure=event_timestamp
    )

    # A slope is calculated
    assert last_slope == -0.5 / 2.0 - 2.0 / 2.0
    assert the_algo.last_slope == -1.25
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is True

    # A new temperature with 1 degre less
    event_timestamp = now - timedelta(minutes=1)
    last_slope = the_algo.add_temp_measurement(
        temperature=6, datetime_measure=event_timestamp
    )

    # A slope is calculated
    assert last_slope == -1.25 / 2 - 1.0 / 2.0
    assert the_algo.last_slope == -1.125
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is True

    # A new temperature with 0 degre less
    event_timestamp = now - timedelta(minutes=0)
    last_slope = the_algo.add_temp_measurement(
        temperature=6, datetime_measure=event_timestamp
    )

    # A slope is calculated
    assert last_slope == -1.125 / 2
    assert the_algo.last_slope == -1.125 / 2
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    # A new temperature with 1 degre more
    event_timestamp = now + timedelta(minutes=1)
    last_slope = the_algo.add_temp_measurement(
        temperature=7, datetime_measure=event_timestamp
    )

    # A slope is calculated
    assert last_slope == -1.125 / 4 + 0.5
    assert the_algo.last_slope == 0.21875
    assert the_algo.is_window_close_detected() is True
    assert the_algo.is_window_open_detected() is False


async def test_open_window_algo_wrong(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the Algo with wrong date"""
    the_algo = WindowOpenDetectionAlgorithm(1.0, 0.0)
    assert the_algo.last_slope is None

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    event_timestamp = now - timedelta(minutes=5)
    last_slope = the_algo.add_temp_measurement(
        temperature=10, datetime_measure=event_timestamp
    )

    # We need at least 2 measurement
    assert last_slope is None
    assert the_algo.last_slope is None
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    # The next datetime_measurement cannot be in the past
    event_timestamp = now - timedelta(minutes=6)
    last_slope = the_algo.add_temp_measurement(
        temperature=18, datetime_measure=event_timestamp
    )

    # No slope because same temperature
    assert last_slope is None
    assert the_algo.last_slope is None
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False
