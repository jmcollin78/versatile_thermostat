# pylint: disable=unused-argument, line-too-long
""" Test the OpenWindow algorithm """

from datetime import datetime, timedelta
from custom_components.versatile_thermostat.open_window_algorithm import (
    WindowOpenDetectionAlgorithm,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_open_window_algo(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the Algo"""

    the_algo = WindowOpenDetectionAlgorithm(60.0, 0.0)
    assert the_algo.last_slope is None

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    event_timestamp = now - timedelta(minutes=10)
    last_slope = the_algo.add_temp_measurement(temperature=10, datetime_measure=event_timestamp)

    # We need at least 4 measurement
    assert last_slope is None
    assert the_algo.last_slope is None
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    event_timestamp = now - timedelta(minutes=9)
    last_slope = the_algo.add_temp_measurement(temperature=10, datetime_measure=event_timestamp)

    event_timestamp = now - timedelta(minutes=8)
    last_slope = the_algo.add_temp_measurement(temperature=10, datetime_measure=event_timestamp)

    event_timestamp = now - timedelta(minutes=7)
    last_slope = the_algo.add_temp_measurement(temperature=10, datetime_measure=event_timestamp)

    # No slope because same temperature
    assert last_slope == 0
    assert the_algo.last_slope == 0
    assert the_algo.is_window_close_detected() is True
    assert the_algo.is_window_open_detected() is False

    event_timestamp = now - timedelta(minutes=6)
    last_slope = the_algo.add_temp_measurement(temperature=9, datetime_measure=event_timestamp)

    # A slope is calculated
    assert last_slope == -48.0
    assert the_algo.last_slope == -48.0
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    # A new temperature with 2 degre less in one minute (value will be rejected)
    event_timestamp = now - timedelta(minutes=5)
    last_slope = the_algo.add_temp_measurement(temperature=7, datetime_measure=event_timestamp)

    # A slope is calculated
    assert last_slope == (-48.0 * 0.2 - 120.0 * 0.8)
    assert the_algo.last_slope == -105.6
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is True

    # A new temperature with 1 degre less
    event_timestamp = now - timedelta(minutes=4)
    last_slope = the_algo.add_temp_measurement(temperature=6, datetime_measure=event_timestamp)

    # A slope is calculated
    assert last_slope == -105.6 * 0.2 - 60.0 * 0.8
    assert the_algo.last_slope == -69.12
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is True

    # A new temperature with 0 degre less
    event_timestamp = now - timedelta(minutes=3)
    last_slope = the_algo.add_temp_measurement(temperature=6, datetime_measure=event_timestamp)

    # A slope is calculated
    assert last_slope == round(-69.12 * 0.2 - 0.0 * 0.8, 2)
    assert the_algo.last_slope == -13.82
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    # A new temperature with 1 degre more
    event_timestamp = now - timedelta(minutes=2)
    last_slope = the_algo.add_temp_measurement(temperature=7, datetime_measure=event_timestamp)

    # A slope is calculated
    assert last_slope == round(-13.82 * 0.2 + 60.0 * 0.8, 2)
    assert the_algo.last_slope == 45.24
    assert the_algo.is_window_close_detected() is True
    assert the_algo.is_window_open_detected() is False


async def test_open_window_algo_wrong(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the Algo with wrong date"""
    the_algo = WindowOpenDetectionAlgorithm(60.0, 0.0)
    assert the_algo.last_slope is None

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    event_timestamp = now - timedelta(minutes=5)
    last_slope = the_algo.add_temp_measurement(temperature=10, datetime_measure=event_timestamp)

    # We need at least 2 measurement
    assert last_slope is None
    assert the_algo.last_slope is None
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    # The next datetime_measurement cannot be in the past
    event_timestamp = now - timedelta(minutes=6)
    last_slope = the_algo.add_temp_measurement(temperature=18, datetime_measure=event_timestamp)

    # No slope because same temperature
    assert last_slope is None
    assert the_algo.last_slope is None
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False


async def test_open_window_algo_fake_point(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the Algo with adding fake point"""

    the_algo = WindowOpenDetectionAlgorithm(3.0, 0.1)
    assert the_algo.last_slope is None

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    event_timestamp = now
    last_slope = the_algo.check_age_last_measurement(temperature=10, datetime_now=event_timestamp)

    # We need at least 4 measurement
    assert last_slope is None
    assert the_algo.last_slope is None
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    event_timestamp = now + timedelta(minutes=1)
    last_slope = the_algo.add_temp_measurement(temperature=10, datetime_measure=event_timestamp)

    event_timestamp = now + timedelta(minutes=2)
    last_slope = the_algo.add_temp_measurement(temperature=10, datetime_measure=event_timestamp)

    event_timestamp = now + timedelta(minutes=3)
    last_slope = the_algo.add_temp_measurement(temperature=10, datetime_measure=event_timestamp)

    # No slope because same temperature
    assert last_slope == 0
    assert the_algo.last_slope == 0
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is False

    event_timestamp = now + timedelta(minutes=4)
    last_slope = the_algo.add_temp_measurement(temperature=9, datetime_measure=event_timestamp)

    # A slope is calculated
    assert last_slope == -48.0
    assert the_algo.last_slope == -48.0
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is True  # One degre in one minute

    # 1 Add a fake point one minute later
    event_timestamp = now + timedelta(minutes=5)
    last_slope = the_algo.check_age_last_measurement(temperature=8, datetime_now=event_timestamp)

    # The slope not have change (fake point is ignored)
    assert last_slope == -48.0
    assert the_algo.last_slope == -48.0
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is True  # One degre in one minute

    # 2 Add a fake point 31 minute later -> +2 degres in 32 minutes
    event_timestamp = event_timestamp + timedelta(minutes=31)
    last_slope = the_algo.check_age_last_measurement(temperature=10, datetime_now=event_timestamp)

    # The slope should have change (fake point is added)
    assert last_slope == -8.1
    assert the_algo.last_slope == -8.1
    assert the_algo.is_window_close_detected() is False
    assert the_algo.is_window_open_detected() is True

    # 3 Add a 2nd fake point 30 minute later -> +3 degres in 30 minutes
    event_timestamp = event_timestamp + timedelta(minutes=31)
    last_slope = the_algo.check_age_last_measurement(temperature=13, datetime_now=event_timestamp)

    # The slope should have change (fake point is added)
    assert last_slope == 0.67
    assert the_algo.last_slope == 0.67
    assert the_algo.is_window_close_detected() is True
    assert the_algo.is_window_open_detected() is False
