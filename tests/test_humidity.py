# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

"""Test the Humidity Feature Manager"""
import logging
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.feature_humidity_manager import (
    FeatureHumidityManager,
)

from .commons import *

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "humidity_value, threshold, is_too_high",
    [
        (65.0, 60.0, True),
        (55.0, 60.0, False),
        (60.0, 60.0, False),  # Equal to threshold, not too high
        (60.1, 60.0, True),  # Just above threshold
        (None, 60.0, False),  # No humidity reading
    ],
)
async def test_humidity_feature_manager(hass: HomeAssistant, humidity_value, threshold, is_too_high):
    """Test the FeatureHumidityManager class directly"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    # 1. creation
    humidity_manager = FeatureHumidityManager(fake_vtherm, hass)

    assert humidity_manager is not None
    assert humidity_manager.is_configured is False
    assert humidity_manager.current_humidity is None
    assert humidity_manager.humidity_threshold == 60.0  # Default
    assert humidity_manager.is_humidity_too_high is False
    assert humidity_manager.name == "the name"

    assert len(humidity_manager._active_listener) == 0

    custom_attributes = {}
    humidity_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_humidity_configured"] is False
    assert custom_attributes.get("humidity_manager") is None

    # 2. post_init
    humidity_manager.post_init(
        {
            CONF_HUMIDITY_SENSOR: "sensor.the_humidity_sensor",
            CONF_HUMIDITY_THRESHOLD: threshold,
            CONF_USE_HUMIDITY_FEATURE: True,
        }
    )

    assert humidity_manager.is_configured is True
    assert humidity_manager.current_humidity is None
    assert humidity_manager.humidity_threshold == threshold
    assert humidity_manager.humidity_sensor_entity_id == "sensor.the_humidity_sensor"

    custom_attributes = {}
    humidity_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_humidity_configured"] is True
    assert custom_attributes["humidity_manager"]["humidity_sensor_entity_id"] == "sensor.the_humidity_sensor"
    assert custom_attributes["humidity_manager"]["current_humidity"] is None
    assert custom_attributes["humidity_manager"]["humidity_threshold"] == threshold

    # 3. start listening
    await humidity_manager.start_listening()
    assert humidity_manager.is_configured is True

    assert len(humidity_manager._active_listener) == 1

    # 4. test refresh with humidity value
    with patch(
        "homeassistant.core.StateMachine.get",
        return_value=State("sensor.the_humidity_sensor", str(humidity_value) if humidity_value is not None else STATE_UNAVAILABLE),
    ), patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.get_safe_float",
        return_value=humidity_value,
    ):
        fake_vtherm.update_states = AsyncMock()
        fake_vtherm.requested_state = MagicMock()
        fake_vtherm.requested_state.force_changed = MagicMock()

        ret = await humidity_manager.refresh_state()
        assert humidity_manager.is_configured is True
        assert humidity_manager.current_humidity == humidity_value
        assert humidity_manager.is_humidity_too_high == is_too_high

        if humidity_value is not None:
            assert ret is True  # Changed from None
        else:
            assert ret is False  # No change

    # 5. test sensor change event
    fake_vtherm.update_states = AsyncMock()
    fake_vtherm.requested_state = MagicMock()
    fake_vtherm.requested_state.force_changed = MagicMock()

    old_humidity = humidity_manager.current_humidity
    new_humidity = 70.0 if humidity_value != 70.0 else 50.0

    with patch(
        "custom_components.versatile_thermostat.feature_humidity_manager.get_safe_float",
        return_value=new_humidity,
    ):
        await humidity_manager._humidity_sensor_changed(
            event=Event(
                event_type=EVENT_STATE_CHANGED,
                data={
                    "entity_id": "sensor.the_humidity_sensor",
                    "new_state": State("sensor.the_humidity_sensor", str(new_humidity)),
                    "old_state": State("sensor.the_humidity_sensor", str(old_humidity) if old_humidity is not None else STATE_UNAVAILABLE),
                },
            )
        )

        assert humidity_manager.current_humidity == new_humidity
        assert fake_vtherm.requested_state.force_changed.called
        fake_vtherm.update_states.assert_called_once_with(force=True)

    humidity_manager.stop_listening()
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    "use_humidity_feature, humidity_sensor_entity_id, threshold, is_configured",
    [
        (True, "sensor.the_humidity_sensor", 60.0, True),
        (True, "sensor.the_humidity_sensor", 70.0, True),
        (False, "sensor.the_humidity_sensor", 60.0, False),
        (True, None, 60.0, False),
        (True, "sensor.the_humidity_sensor", None, True),  # Uses default threshold
    ],
)
async def test_humidity_feature_manager_post_init(
    hass: HomeAssistant,
    use_humidity_feature,
    humidity_sensor_entity_id,
    threshold,
    is_configured,
):
    """Test the FeatureHumidityManager post_init with various configurations"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    humidity_manager = FeatureHumidityManager(fake_vtherm, hass)
    assert humidity_manager is not None

    config = {
        CONF_USE_HUMIDITY_FEATURE: use_humidity_feature,
        CONF_HUMIDITY_SENSOR: humidity_sensor_entity_id,
    }
    if threshold is not None:
        config[CONF_HUMIDITY_THRESHOLD] = threshold

    humidity_manager.post_init(config)

    assert humidity_manager.is_configured is is_configured
    assert humidity_manager.humidity_sensor_entity_id == humidity_sensor_entity_id
    if threshold is not None:
        assert humidity_manager.humidity_threshold == threshold
    else:
        assert humidity_manager.humidity_threshold == 60.0  # Default
