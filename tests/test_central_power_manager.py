# pylint: disable=protected-access, unused-argument, line-too-long
""" Test the Central Power management """
from unittest.mock import patch, call, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timedelta
import logging

from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.feature_power_manager import (
    FeaturePowerManager,
)
from custom_components.versatile_thermostat.central_feature_power_manager import (
    CentralFeaturePowerManager,
)
from custom_components.versatile_thermostat.prop_algorithm import PropAlgorithm
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "use_power_feature, power_entity_id, max_power_entity_id, power_temp, is_configured",
    [
        (True, "sensor.power_id", "sensor.max_power_id", 13, True),
        (True, None, "sensor.max_power_id", 13, False),
        (True, "sensor.power_id", None, 13, False),
        (True, "sensor.power_id", "sensor.max_power_id", None, False),
        (False, "sensor.power_id", "sensor.max_power_id", 13, False),
    ],
)
async def test_central_power_manager_init(
    hass: HomeAssistant,
    use_power_feature,
    power_entity_id,
    max_power_entity_id,
    power_temp,
    is_configured,
):
    """Test creation and post_init of the Central Power Manager"""
    vtherm_api: VersatileThermostatAPI = MagicMock(spec=VersatileThermostatAPI)
    central_power_manager = CentralFeaturePowerManager(hass, vtherm_api)

    assert central_power_manager.is_configured is False
    assert central_power_manager.current_max_power is None
    assert central_power_manager.current_power is None
    assert central_power_manager.power_temperature is None
    assert central_power_manager.name == "centralPowerManager"

    # 2. post_init
    central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: power_entity_id,
            CONF_MAX_POWER_SENSOR: max_power_entity_id,
            CONF_USE_POWER_FEATURE: use_power_feature,
            CONF_PRESET_POWER: power_temp,
        }
    )

    assert central_power_manager.is_configured == is_configured
    assert central_power_manager.current_max_power is None
    assert central_power_manager.current_power is None
    assert central_power_manager.power_temperature == power_temp

    # 3. start listening
    central_power_manager.start_listening()
    assert len(central_power_manager._active_listener) == (2 if is_configured else 0)

    # 4. stop listening
    central_power_manager.stop_listening()
    assert len(central_power_manager._active_listener) == 0


@pytest.mark.parametrize(
    "is_over_climate, is_device_active, power, max_power, current_overpowering_state, overpowering_state, nb_call, changed, check_overpowering_ret",
    [
        # don't switch to overpower (power is enough)
        (False, False, 1000, 3000, STATE_OFF, STATE_OFF, 0, True, False),
        # switch to overpower (power is not enough)
        (False, False, 2000, 3000, STATE_OFF, STATE_ON, 1, True, True),
        # don't switch to overpower (power is not enough but device is already on)
        (False, True, 2000, 3000, STATE_OFF, STATE_OFF, 0, True, False),
        # Same with a over_climate
        # don't switch to overpower (power is enough)
        (True, False, 1000, 3000, STATE_OFF, STATE_OFF, 0, True, False),
        # switch to overpower (power is not enough)
        (True, False, 2000, 3000, STATE_OFF, STATE_ON, 1, True, True),
        # don't switch to overpower (power is not enough but device is already on)
        (True, True, 2000, 3000, STATE_OFF, STATE_OFF, 0, True, False),
        # Leave overpowering state
        # switch to not overpower (power is enough)
        (False, False, 1000, 3000, STATE_ON, STATE_OFF, 1, True, False),
        # don't switch to overpower (power is still not enough)
        (False, False, 2000, 3000, STATE_ON, STATE_ON, 0, True, True),
        # keep overpower (power is not enough but device is already on)
        (False, True, 3000, 3000, STATE_ON, STATE_ON, 0, True, True),
    ],
)
async def test_central_power_manager(
    hass: HomeAssistant,
    is_over_climate,
    is_device_active,
    power,
    max_power,
    current_overpowering_state,
    overpowering_state,
    nb_call,
    changed,
    check_overpowering_ret,
):
    """Test the FeaturePresenceManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    # 1. creation
    power_manager = FeaturePowerManager(fake_vtherm, hass)

    assert power_manager is not None
    assert power_manager.is_configured is False
    assert power_manager.overpowering_state == STATE_UNAVAILABLE
    assert power_manager.name == "the name"

    assert len(power_manager._active_listener) == 0

    custom_attributes = {}
    power_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["power_sensor_entity_id"] is None
    assert custom_attributes["max_power_sensor_entity_id"] is None
    assert custom_attributes["overpowering_state"] == STATE_UNAVAILABLE
    assert custom_attributes["is_power_configured"] is False
    assert custom_attributes["device_power"] is 0
    assert custom_attributes["power_temp"] is None
    assert custom_attributes["current_power"] is None
    assert custom_attributes["current_max_power"] is None

    # 2. post_init
    power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 10,
            CONF_DEVICE_POWER: 1234,
        }
    )

    assert power_manager.is_configured is True
    assert power_manager.overpowering_state == STATE_UNKNOWN

    custom_attributes = {}
    power_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["power_sensor_entity_id"] == "sensor.the_power_sensor"
    assert (
        custom_attributes["max_power_sensor_entity_id"] == "sensor.the_max_power_sensor"
    )
    assert custom_attributes["overpowering_state"] == STATE_UNKNOWN
    assert custom_attributes["is_power_configured"] is True
    assert custom_attributes["device_power"] == 1234
    assert custom_attributes["power_temp"] == 10
    assert custom_attributes["current_power"] is None
    assert custom_attributes["current_max_power"] is None

    # 3. start listening
    power_manager.start_listening()
    assert power_manager.is_configured is True
    assert power_manager.overpowering_state == STATE_UNKNOWN

    assert len(power_manager._active_listener) == 2

    # 4. test refresh and check_overpowering with the parametrized
    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", power),
            "sensor.the_max_power_sensor": State(
                "sensor.the_max_power_sensor", max_power
            ),
        },
        State("unknown.entity_id", "unknown"),
    )
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()) as mock_get_state:
    # fmt:on
        # Finish the mock configuration
        tpi_algo = PropAlgorithm(PROPORTIONAL_FUNCTION_TPI, 0.6, 0.01, 5, 0, "climate.vtherm")
        tpi_algo._on_percent = 1 # pylint: disable="protected-access"
        type(fake_vtherm).hvac_mode = PropertyMock(return_value=HVACMode.HEAT)
        type(fake_vtherm).is_device_active = PropertyMock(return_value=is_device_active)
        type(fake_vtherm).is_over_climate = PropertyMock(return_value=is_over_climate)
        type(fake_vtherm).proportional_algorithm = PropertyMock(return_value=tpi_algo)
        type(fake_vtherm).nb_underlying_entities = PropertyMock(return_value=1)
        type(fake_vtherm).preset_mode = PropertyMock(return_value=PRESET_COMFORT if current_overpowering_state == STATE_OFF else PRESET_POWER)
        type(fake_vtherm)._saved_preset_mode = PropertyMock(return_value=PRESET_ECO)

        fake_vtherm.save_hvac_mode = MagicMock()
        fake_vtherm.restore_hvac_mode = AsyncMock()
        fake_vtherm.save_preset_mode = MagicMock()
        fake_vtherm.restore_preset_mode = AsyncMock()
        fake_vtherm.async_underlying_entity_turn_off = AsyncMock()
        fake_vtherm.async_set_preset_mode_internal = AsyncMock()
        fake_vtherm.send_event = MagicMock()
        fake_vtherm.update_custom_attributes = MagicMock()


        ret = await power_manager.refresh_state()
        assert ret == changed
        assert power_manager.is_configured is True
        assert power_manager.overpowering_state == STATE_UNKNOWN
        assert power_manager.current_power == power
        assert power_manager.current_max_power == max_power

        # check overpowering
        power_manager._overpowering_state = current_overpowering_state
        ret2 = await power_manager.check_overpowering()
        assert ret2 == check_overpowering_ret
        assert power_manager.overpowering_state == overpowering_state
        assert mock_get_state.call_count == 2

        if power_manager.overpowering_state == STATE_OFF:
            assert fake_vtherm.save_hvac_mode.call_count == 0
            assert fake_vtherm.save_preset_mode.call_count == 0
            assert fake_vtherm.async_underlying_entity_turn_off.call_count == 0
            assert fake_vtherm.async_set_preset_mode_internal.call_count == 0
            assert fake_vtherm.send_event.call_count == nb_call

            if current_overpowering_state == STATE_ON:
                assert fake_vtherm.update_custom_attributes.call_count == 1
                assert fake_vtherm.restore_preset_mode.call_count == 1
                if is_over_climate:
                    assert fake_vtherm.restore_hvac_mode.call_count == 1
                else:
                    assert fake_vtherm.restore_hvac_mode.call_count == 0
            else:
                assert fake_vtherm.update_custom_attributes.call_count == 0

            if nb_call == 1:
                fake_vtherm.send_event.assert_has_calls(
                    [
                        call.fake_vtherm.send_event(
                            EventType.POWER_EVENT,
                            {'type': 'end', 'current_power': power, 'device_power': 1234, 'current_max_power': max_power}),
                    ]
                )


        elif power_manager.overpowering_state == STATE_ON:
            if is_over_climate:
                assert fake_vtherm.save_hvac_mode.call_count == 1
            else:
                assert fake_vtherm.save_hvac_mode.call_count == 0

            if current_overpowering_state == STATE_OFF:
                assert fake_vtherm.save_preset_mode.call_count == 1
                assert fake_vtherm.async_underlying_entity_turn_off.call_count == 1
                assert fake_vtherm.async_set_preset_mode_internal.call_count == 1
                assert fake_vtherm.send_event.call_count == 1
                assert fake_vtherm.update_custom_attributes.call_count == 1
            else:
                assert fake_vtherm.save_preset_mode.call_count == 0
                assert fake_vtherm.async_underlying_entity_turn_off.call_count == 0
                assert fake_vtherm.async_set_preset_mode_internal.call_count == 0
                assert fake_vtherm.send_event.call_count == 0
                assert fake_vtherm.update_custom_attributes.call_count == 0
            assert fake_vtherm.restore_hvac_mode.call_count == 0
            assert fake_vtherm.restore_preset_mode.call_count == 0

            if nb_call == 1:
                fake_vtherm.send_event.assert_has_calls(
                    [
                        call.fake_vtherm.send_event(
                            EventType.POWER_EVENT,
                            {'type': 'start', 'current_power': power, 'device_power': 1234, 'current_max_power': max_power, 'current_power_consumption': 1234.0}),
                    ]
                )

        fake_vtherm.reset_mock()

    # 5. Check custom_attributes
        custom_attributes = {}
        power_manager.add_custom_attributes(custom_attributes)
        assert custom_attributes["power_sensor_entity_id"] == "sensor.the_power_sensor"
        assert (
            custom_attributes["max_power_sensor_entity_id"] == "sensor.the_max_power_sensor"
        )
        assert custom_attributes["overpowering_state"] == overpowering_state
        assert custom_attributes["is_power_configured"] is True
        assert custom_attributes["device_power"] == 1234
        assert custom_attributes["power_temp"] == 10
        assert custom_attributes["current_power"] == power
        assert custom_attributes["current_max_power"] == max_power

    power_manager.stop_listening()
    await hass.async_block_till_done()
