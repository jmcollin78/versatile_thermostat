# pylint: disable=protected-access, unused-argument, line-too-long
""" Test the Power management """
from unittest.mock import patch, call, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timedelta
import logging

from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.feature_power_manager import (
    FeaturePowerManager,
)

from custom_components.versatile_thermostat.prop_algorithm import PropAlgorithm
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "is_over_climate, is_device_active, power, max_power, check_power_available",
    [
        # don't switch to overpower (power is enough)
        (False, False, 1000, 3000, True),
        # switch to overpower (power is not enough)
        (False, False, 2000, 3000, False),
        # don't switch to overpower (power is not enough but device is already on)
        (False, True, 2000, 3000, True),
        # Same with a over_climate
        # don't switch to overpower (power is enough)
        (True, False, 1000, 3000, True),
        # switch to overpower (power is not enough)
        (True, False, 2000, 3000, False),
        # don't switch to overpower (power is not enough but device is already on)
        (True, True, 2000, 3000, True),
        # Leave overpowering state
        # switch to not overpower (power is enough)
        (False, False, 1000, 3000, True),
        # don't switch to overpower (power is still not enough)
        (False, False, 2000, 3000, False),
        # keep overpower (power is not enough but device is already on)
        (False, True, 3000, 3000, False),
    ],
)
async def test_power_feature_manager(
    hass: HomeAssistant,
    is_over_climate,
    is_device_active,
    power,
    max_power,
    check_power_available,
):
    """Test the FeaturePresenceManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

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
    vtherm_api.find_central_configuration = MagicMock()
    vtherm_api.central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
        }
    )
    assert vtherm_api.central_power_manager.is_configured

    power_manager.post_init(
        {
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 10,
            CONF_DEVICE_POWER: 1234,
        }
    )

    power_manager.start_listening()

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

    assert len(power_manager._active_listener) == 0  # no more listening

    # 4. test refresh and check_overpowering with the parametrized
    # fmt:off
    with patch("custom_components.versatile_thermostat.central_feature_power_manager.CentralFeaturePowerManager.current_max_power", new_callable=PropertyMock, return_value=max_power), \
        patch("custom_components.versatile_thermostat.central_feature_power_manager.CentralFeaturePowerManager.current_power", new_callable=PropertyMock, return_value=power):
    # fmt:on

        # Finish the mock configuration
        tpi_algo = PropAlgorithm(PROPORTIONAL_FUNCTION_TPI, 0.6, 0.01, 5, 0, "climate.vtherm")
        tpi_algo._on_percent = 1 # pylint: disable="protected-access"
        type(fake_vtherm).hvac_mode = PropertyMock(return_value=HVACMode.HEAT)
        type(fake_vtherm).is_device_active = PropertyMock(return_value=is_device_active)
        type(fake_vtherm).is_over_climate = PropertyMock(return_value=is_over_climate)
        type(fake_vtherm).proportional_algorithm = PropertyMock(return_value=tpi_algo)
        type(fake_vtherm).nb_underlying_entities = PropertyMock(return_value=1)

        ret = await power_manager.check_power_available()
        assert ret == check_power_available


@pytest.mark.parametrize(
    "is_over_climate, current_overpowering_state, is_overpowering, new_overpowering_state, msg_sent",
    [
        # false -> false
        (False, STATE_OFF, False, STATE_OFF, False),
        # false -> true
        (False, STATE_OFF, True, STATE_ON, True),
        # true -> true
        (False, STATE_ON, True, STATE_ON, False),
        # true -> False
        (False, STATE_ON, False, STATE_OFF, True),
        # Same with over_climate
        # false -> false
        (True, STATE_OFF, False, STATE_OFF, False),
        # false -> true
        (True, STATE_OFF, True, STATE_ON, True),
        # true -> true
        (True, STATE_ON, True, STATE_ON, False),
        # true -> False
        (True, STATE_ON, False, STATE_OFF, True),
    ],
)
async def test_power_feature_manager_set_overpowering(
    hass,
    is_over_climate,
    current_overpowering_state,
    is_overpowering,
    new_overpowering_state,
    msg_sent,
):
    """Test the set_overpowering method of FeaturePowerManager"""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # 1. creation / init
    power_manager = FeaturePowerManager(fake_vtherm, hass)
    vtherm_api.find_central_configuration = MagicMock()
    vtherm_api.central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
        }
    )
    assert vtherm_api.central_power_manager.is_configured

    power_manager.post_init(
        {
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 10,
            CONF_DEVICE_POWER: 1234,
        }
    )

    power_manager.start_listening()

    assert power_manager.is_configured is True
    assert power_manager.overpowering_state == STATE_UNKNOWN

    # check overpowering
    power_manager._overpowering_state = current_overpowering_state

    # fmt:off
    with patch("custom_components.versatile_thermostat.central_feature_power_manager.CentralFeaturePowerManager.current_max_power", new_callable=PropertyMock, return_value=2000), \
        patch("custom_components.versatile_thermostat.central_feature_power_manager.CentralFeaturePowerManager.current_power", new_callable=PropertyMock, return_value=1000):
    # fmt:on
        # Finish mocking
        fake_vtherm.is_over_climate = is_over_climate
        fake_vtherm.preset_mode = MagicMock(return_value=PRESET_COMFORT if current_overpowering_state == STATE_OFF else PRESET_POWER)
        fake_vtherm._saved_preset_mode = PRESET_ECO

        fake_vtherm.save_hvac_mode = MagicMock()
        fake_vtherm.restore_hvac_mode = AsyncMock()
        fake_vtherm.save_preset_mode = MagicMock()
        fake_vtherm.restore_preset_mode = AsyncMock()
        fake_vtherm.async_underlying_entity_turn_off = AsyncMock()
        fake_vtherm.async_set_preset_mode_internal = AsyncMock()
        fake_vtherm.send_event = MagicMock()
        fake_vtherm.update_custom_attributes = MagicMock()


        # Call set_overpowering
        await power_manager.set_overpowering(is_overpowering, 1234)

        assert power_manager.overpowering_state == new_overpowering_state

        if not is_overpowering:
            assert power_manager.overpowering_state == STATE_OFF
            assert fake_vtherm.save_hvac_mode.call_count == 0
            assert fake_vtherm.save_preset_mode.call_count == 0
            assert fake_vtherm.async_underlying_entity_turn_off.call_count == 0
            assert fake_vtherm.async_set_preset_mode_internal.call_count == 0

            if current_overpowering_state == STATE_ON:
                assert fake_vtherm.update_custom_attributes.call_count == 1
                assert fake_vtherm.restore_preset_mode.call_count == 1
                if is_over_climate:
                    assert fake_vtherm.restore_hvac_mode.call_count == 1
                else:
                    assert fake_vtherm.restore_hvac_mode.call_count == 0
            else:
                assert fake_vtherm.update_custom_attributes.call_count == 0

            if msg_sent:
                fake_vtherm.send_event.assert_has_calls(
                    [
                        call.fake_vtherm.send_event(
                            EventType.POWER_EVENT,
                            {
                                "type": "end",
                                "current_power": 1000,
                                "device_power": 1234,
                                "current_max_power": 2000,
                            },
                        ),
                    ]
                )
        # is_overpowering is True
        else:
            assert power_manager.overpowering_state == STATE_ON
            if is_over_climate and current_overpowering_state == STATE_OFF:
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

            if msg_sent:
                fake_vtherm.send_event.assert_has_calls(
                    [
                        call.fake_vtherm.send_event(
                            EventType.POWER_EVENT,
                            {
                                "type": "start",
                                "current_power": 1000,
                                "device_power": 1234,
                                "current_max_power": 2000,
                                "current_power_consumption": 1234.0,
                            },
                        ),
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
        assert custom_attributes["overpowering_state"] == new_overpowering_state
        assert custom_attributes["is_power_configured"] is True
        assert custom_attributes["device_power"] == 1234
        assert custom_attributes["power_temp"] == 10
        assert custom_attributes["current_power"] == 1000
        assert custom_attributes["current_max_power"] == 2000

    power_manager.stop_listening()
    await hass.async_block_till_done()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_hvac_off(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager
):
    """Test the Power management"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname", temps
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.preset_mode is PRESET_BOOST
    assert entity.target_temperature == 19
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN
    assert entity.hvac_mode == HVACMode.OFF

    now: datetime = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)

    # Send power mesurement
    # fmt:off
    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", 50),
            "sensor.the_max_power_sensor": State("sensor.the_max_power_sensor", 300),
        },
        State("unknown.entity_id", "unknown"),
    )
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
    # fmt: on
        await send_power_change_event(entity, 50, now)
        assert entity.power_manager.is_overpowering_detected is False

        # All configuration is not complete
        assert entity.preset_mode is PRESET_BOOST
        assert entity.power_manager.overpowering_state is STATE_UNKNOWN # due to hvac_off

        # Send power max mesurement
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)
        await send_max_power_change_event(entity, 300, now)
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max
        assert entity.preset_mode is PRESET_BOOST
        assert entity.power_manager.overpowering_state is STATE_UNKNOWN # # due to hvac_off

    # Send power max mesurement too low but HVACMode is off
    side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 149))
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off:
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_max_power_change_event(entity, 149, datetime.now())
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is > power_max but we stay in Boost cause thermostat if Off
        assert entity.preset_mode is PRESET_BOOST
        assert entity.power_manager.overpowering_state is STATE_UNKNOWN

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_hvac_on(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager
):
    """Test the Power management"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname", temps
    )
    assert entity

    now: datetime = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN
    assert entity.target_temperature == 19

    # Send power mesurement
    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", 50),
            "sensor.the_max_power_sensor": State("sensor.the_max_power_sensor", 300),
        },
        State("unknown.entity_id", "unknown"),
    )
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
    # fmt: on
        await send_power_change_event(entity, 50, datetime.now())
        # Send power max mesurement
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)
        await send_max_power_change_event(entity, 300, datetime.now())

        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max
        assert entity.preset_mode is PRESET_BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF

    # Send power max mesurement too low and HVACMode is on
    side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 149))
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off:
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_max_power_change_event(entity, 149, datetime.now())
        assert entity.power_manager.is_overpowering_detected is True
        # All configuration is complete and power is > power_max we switch to POWER preset
        assert entity.preset_mode is PRESET_POWER
        assert entity.power_manager.overpowering_state is STATE_ON
        assert entity.target_temperature == 12

        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_POWER}),
                call.send_event(
                    EventType.POWER_EVENT,
                    {
                        "type": "start",
                        "current_power": 50,
                        "device_power": 100,
                        "current_max_power": 149,
                        "current_power_consumption": 100.0,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 1

    # Send power mesurement low to unseet power preset
    side_effects.add_or_update_side_effect("sensor.the_power_sensor", State("sensor.the_power_sensor", 48))
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off:
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_power_change_event(entity, 48, datetime.now())
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max, we restore previous preset
        assert entity.preset_mode is PRESET_BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF
        assert entity.target_temperature == 19

        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_BOOST}),
                call.send_event(
                    EventType.POWER_EVENT,
                    {
                        "type": "end",
                        "current_power": 48,
                        "device_power": 100,
                        "current_max_power": 149,
                    },
                ),
            ],
            any_order=True,
        )
        # No current temperature is set so the heater wont be turned on
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_energy_over_switch(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager
):
    """Test the Power management energy mesurement"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch", "switch.mock_switch2"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname", temps
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    assert entity.total_energy == 0
    assert entity.nb_underlying_entities == 2

    # set temperature to 15 so that on_percent will be set
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off:
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_BOOST)
        await send_temperature_change_event(entity, 15, datetime.now())

        await hass.async_block_till_done()

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.target_temperature == 19
        assert entity.current_temperature == 15
        assert tpi_algo.on_percent == 1

        assert entity.power_manager.device_power == 100.0

        assert mock_send_event.call_count == 2
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0

    entity.incremente_energy()
    assert entity.total_energy == round(100 * 5 / 60.0, 2)
    entity.incremente_energy()
    assert entity.total_energy == round(2 * 100 * 5 / 60.0, 2)

    # change temperature to a higher value
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off:
        await send_temperature_change_event(entity, 18, datetime.now())
        assert tpi_algo.on_percent == 0.3
        assert entity.power_manager.mean_cycle_power == 30.0

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0

    entity.incremente_energy()
    assert round(entity.total_energy, 2) == round((2.0 + 0.3) * 100 * 5 / 60.0, 2)

    entity.incremente_energy()
    assert round(entity.total_energy, 2) == round((2.0 + 0.6) * 100 * 5 / 60.0, 2)

    # change temperature to a much higher value so that heater will be shut down
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off:
        await send_temperature_change_event(entity, 20, datetime.now())
        assert tpi_algo.on_percent == 0.0
        assert entity.power_manager.mean_cycle_power == 0.0

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0

    entity.incremente_energy()
    # No change on energy
    assert round(entity.total_energy, 2) == round((2.0 + 0.6) * 100 * 5 / 60.0, 2)

    # Still no change
    entity.incremente_energy()
    assert round(entity.total_energy, 2) == round((2.0 + 0.6) * 100 * 5 / 60.0, 2)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_energy_over_climate(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Power management for a over_climate thermostat"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    the_mock_underlying = MagicMockClimate()
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=the_mock_underlying,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="TheOverClimateMockName",
            unique_id="uniqueId",
            data={
                CONF_NAME: "TheOverClimateMockName",
                CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
                CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
                CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
                CONF_CYCLE_MIN: 5,
                CONF_TEMP_MIN: 15,
                CONF_TEMP_MAX: 30,
                CONF_USE_WINDOW_FEATURE: False,
                CONF_USE_MOTION_FEATURE: False,
                CONF_USE_POWER_FEATURE: True,
                CONF_USE_PRESENCE_FEATURE: False,
                CONF_UNDERLYING_LIST: ["climate.mock_climate"],
                CONF_MINIMAL_ACTIVATION_DELAY: 30,
                CONF_SAFETY_DELAY_MIN: 5,
                CONF_SAFETY_MIN_ON_PERCENT: 0.3,
                CONF_POWER_SENSOR: "sensor.mock_power_sensor",
                CONF_MAX_POWER_SENSOR: "sensor.mock_power_max_sensor",
                CONF_DEVICE_POWER: 100,
                CONF_PRESET_POWER: 12,
            },
        )

        entity: ThermostatOverSwitch = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname", temps
        )
        assert entity
        assert entity.is_over_climate

    now = datetime.now(tz=get_tz(hass))
    await send_temperature_change_event(entity, 15, now)
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)

    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.hvac_action is HVACAction.IDLE
    assert entity.preset_mode is PRESET_BOOST
    assert entity.target_temperature == 19
    assert entity.current_temperature == 15

    # Not initialised yet
    assert entity.power_manager.mean_cycle_power is None
    assert entity._underlying_climate_start_hvac_action_date is None

    # Send a climate_change event with HVACAction=HEATING
    event_timestamp = now - timedelta(minutes=3)
    await send_climate_change_event(
        entity,
        new_hvac_mode=HVACMode.HEAT,
        old_hvac_mode=HVACMode.HEAT,
        new_hvac_action=HVACAction.HEATING,
        old_hvac_action=HVACAction.OFF,
        date=event_timestamp,
        underlying_entity_id="climate.mock_climate",
    )
    # We have the start event and not the end event
    assert (entity._underlying_climate_start_hvac_action_date - now).total_seconds() < 1

    entity.incremente_energy()
    assert entity.total_energy == 0

    # Send a climate_change event with HVACAction=IDLE (end of heating)
    await send_climate_change_event(
        entity,
        new_hvac_mode=HVACMode.HEAT,
        old_hvac_mode=HVACMode.HEAT,
        new_hvac_action=HVACAction.IDLE,
        old_hvac_action=HVACAction.HEATING,
        date=now,
        underlying_entity_id="climate.mock_climate",
    )
    # We have the end event -> we should have some power and on_percent
    assert entity._underlying_climate_start_hvac_action_date is None

    # 3 minutes at 100 W
    assert entity.total_energy == 100 * 3.0 / 60

    # Test the re-increment
    entity.incremente_energy()
    assert entity.total_energy == 2 * 100 * 3.0 / 60
