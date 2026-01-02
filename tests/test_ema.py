# pylint: disable=line-too-long
""" Tests de EMA calculation"""
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant

from custom_components.versatile_thermostat.ema import ExponentialMovingAverage

from .commons import get_tz


def test_ema_basics(hass: HomeAssistant):
    """Test the EMA calculation with basic features"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    the_ema = ExponentialMovingAverage(
        "test",
        # 5 minutes
        300,
        # Needed for time calculation
        get_tz(hass),
        1,
        0.5
    )

    assert the_ema

    current_timestamp = now
    # First initialization
    assert the_ema.calculate_ema(20, current_timestamp) == 20

    current_timestamp = current_timestamp + timedelta(minutes=1)
    # One minute later, same temperature. EMA temperature should not have change
    assert the_ema.calculate_ema(20, current_timestamp) == 20

    # Too short measurement should be ignored
    assert the_ema.calculate_ema(2000, current_timestamp) == 20

    current_timestamp = current_timestamp + timedelta(seconds=4)
    assert the_ema.calculate_ema(20, current_timestamp) == 20

    # a new normal measurement 5 minutes later
    current_timestamp = current_timestamp + timedelta(minutes=5)
    ema = the_ema.calculate_ema(25, current_timestamp)
    assert ema > 20
    assert ema == 22.5

    # a big change in a short time does have a limited effect
    current_timestamp = current_timestamp + timedelta(seconds=5)
    ema = the_ema.calculate_ema(30, current_timestamp)
    assert ema > 22.5
    assert ema < 23
    assert ema == 22.6
