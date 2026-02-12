# pylint: disable=protected-access, unused-argument, line-too-long
""" Test the Power management """
from unittest.mock import patch, call, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timedelta
import logging

from homeassistant.components.number import SERVICE_SET_VALUE

from custom_components.versatile_thermostat.thermostat_switch import ThermostatOverSwitch
from custom_components.versatile_thermostat.thermostat_climate_valve import ThermostatOverClimateValve
from custom_components.versatile_thermostat.feature_power_manager import FeaturePowerManager

from custom_components.versatile_thermostat.prop_algo_tpi import TpiAlgorithm
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
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
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

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
    assert custom_attributes["is_power_configured"] is False
    assert custom_attributes.get("power_manager") is not None
    assert custom_attributes["power_manager"].get("device_power") == 0
    assert custom_attributes["power_manager"].get("mean_cycle_power") is None
    assert custom_attributes["power_manager"].get("power_sensor_entity_id") is None

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

    await power_manager.start_listening()

    assert power_manager.is_configured is True
    assert power_manager.overpowering_state == STATE_UNKNOWN

    custom_attributes = {}
    power_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_power_configured"] is True
    assert custom_attributes["power_manager"]["power_sensor_entity_id"] == "sensor.the_power_sensor"
    assert custom_attributes["power_manager"]["max_power_sensor_entity_id"] == "sensor.the_max_power_sensor"
    assert custom_attributes["power_manager"]["overpowering_state"] == STATE_UNKNOWN
    assert custom_attributes["power_manager"]["device_power"] == 1234
    assert custom_attributes["power_manager"]["power_temp"] == 10
    assert custom_attributes["power_manager"]["current_power"] is None
    assert custom_attributes["power_manager"]["current_max_power"] is None

    # 3. start listening
    await power_manager.start_listening()
    assert power_manager.is_configured is True
    assert power_manager.overpowering_state == STATE_UNKNOWN

    assert len(power_manager._active_listener) == 0  # no more listening

    # 4. test refresh and check_overpowering with the parametrized
    # fmt:off
    with patch("custom_components.versatile_thermostat.feature_central_power_manager.FeatureCentralPowerManager.current_max_power", new_callable=PropertyMock, return_value=max_power), \
        patch("custom_components.versatile_thermostat.feature_central_power_manager.FeatureCentralPowerManager.current_power", new_callable=PropertyMock, return_value=power):
    # fmt:on

        # Finish the mock configuration
        tpi_algo = TpiAlgorithm(0.6, 0.01, 5, 0, 0, "climate.vtherm")
        tpi_algo._on_percent = 1 # pylint: disable="protected-access"
        type(fake_vtherm).hvac_mode = PropertyMock(return_value=VThermHvacMode_HEAT)
        type(fake_vtherm).is_device_active = PropertyMock(return_value=is_device_active)
        type(fake_vtherm).is_over_climate = PropertyMock(return_value=is_over_climate)
        type(fake_vtherm).proportional_algorithm = PropertyMock(return_value=tpi_algo)
        type(fake_vtherm).nb_underlying_entities = PropertyMock(return_value=1)
        type(fake_vtherm).safe_on_percent = PropertyMock(return_value=1.0)
        fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

        ret, power_consumption_max = await power_manager.check_power_available()
        assert ret == check_power_available
        if is_device_active:
            assert power_consumption_max == 0
        else:
            assert power_consumption_max == 1234


@pytest.mark.parametrize(
    "current_overpowering_state, is_overpowering, new_overpowering_state, msg_sent",
    [
        # false -> false
        (STATE_OFF, False, STATE_OFF, False),
        # false -> true
        (STATE_OFF, True, STATE_ON, True),
        # true -> true
        (STATE_ON, True, STATE_ON, False),
        # true -> False
        (STATE_ON, False, STATE_OFF, True),
    ],
)
async def test_power_feature_manager_set_overpowering(
    hass,
    current_overpowering_state,
    is_overpowering,
    new_overpowering_state,
    msg_sent,
):
    """Test the set_overpowering method of FeaturePowerManager"""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

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

    await power_manager.start_listening()

    assert power_manager.is_configured is True
    assert power_manager.overpowering_state == STATE_UNKNOWN

    # overwrite overpowering state for the test
    power_manager._overpowering_state = current_overpowering_state

    # fmt:off
    with patch("custom_components.versatile_thermostat.feature_central_power_manager.FeatureCentralPowerManager.current_max_power", new_callable=PropertyMock, return_value=2000), \
        patch("custom_components.versatile_thermostat.feature_central_power_manager.FeatureCentralPowerManager.current_power", new_callable=PropertyMock, return_value=1000):
    # fmt:on
        # Finish mocking
        fake_vtherm.send_event = MagicMock()


        # Call set_overpowering
        await power_manager.set_overpowering(is_overpowering, 1234)

        assert power_manager.overpowering_state == new_overpowering_state

        if not is_overpowering:
            assert power_manager.overpowering_state == STATE_OFF

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

            if current_overpowering_state == STATE_OFF:
                assert fake_vtherm.send_event.call_count == 1
            else:
                assert fake_vtherm.send_event.call_count == 0

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

    power_manager.stop_listening()
    await hass.async_block_till_done()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_hvac_off(hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager, fake_underlying_switch: MockSwitch):
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
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
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

    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 19
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN
    assert entity.hvac_mode == VThermHvacMode_OFF

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
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_UNKNOWN # due to hvac_off

        # Send power max mesurement
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)
        await send_max_power_change_event(entity, 300, now)
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_UNKNOWN # # due to hvac_off

    # Send power max mesurement too low but VThermHvacMode is off
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
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_UNKNOWN

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_hvac_on(hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager, fake_underlying_switch: MockSwitch):
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
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
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

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN
    assert entity.target_temperature == 19

    # make the heater heats
    await send_temperature_change_event(entity, 15, now)
    await send_ext_temperature_change_event(entity, 1, now)
    await hass.async_block_till_done()

    assert entity.power_percent > 0

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
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF

    # Send power max mesurement too low and VThermHvacMode is on
    side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 49))
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active", new_callable=PropertyMock, return_value=True):
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_max_power_change_event(entity, 49, now)
        await wait_for_local_condition(lambda: entity.power_manager.is_overpowering_detected is True)
        assert entity.power_manager.is_overpowering_detected is True
        # All configuration is complete and power is > power_max we switch to POWER preset
        assert entity.vtherm_preset_mode == VThermPreset.POWER
        assert entity.preset_mode == VThermPreset.POWER
        assert entity.power_manager.overpowering_state is STATE_ON
        assert entity.target_temperature == 12

        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.POWER}),
                call.send_event(
                    EventType.POWER_EVENT,
                    {
                        "type": "start",
                        "current_power": 50,
                        "device_power": 100,
                        "current_max_power": 49,
                        "current_power_consumption": 100.0,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count >= 1 # can be call twice because is_device_active is patched to True

    # Send power mesurement low to unset power preset
    side_effects.add_or_update_side_effect("sensor.the_power_sensor", State("sensor.the_power_sensor", 48))
    side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 149))
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off:
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_power_change_event(entity, 48, now)
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max, we restore previous preset
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF
        assert entity.target_temperature == 19

        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.BOOST}),
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
        # heater should be turned on
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_energy_over_switch(hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager):
    """Test the Power management energy mesurement"""

    for switch_id in ["mock_switch1", "mock_switch2"]:
        switch = MockSwitch(hass, switch_id, switch_id + "_name")
        await register_mock_entity(hass, switch, SWITCH_DOMAIN)

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
            CONF_UNDERLYING_LIST: ["switch.mock_switch1", "switch.mock_switch2"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
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

    await wait_for_local_condition(lambda: entity.is_ready)

    # set temperature to 15 so that on_percent will be set
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off:
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        await send_temperature_change_event(entity, 15, datetime.now())

        await hass.async_block_till_done()

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert entity.current_temperature == 15
        assert tpi_algo.on_percent == 1

        assert entity.power_manager.device_power == 100.0

        assert mock_send_event.call_count == 2
        assert mock_heater_on.call_count == 2  # both switches turn on immediately at 100%
        assert mock_heater_off.call_count == 0

    with patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        entity.incremente_energy()
        assert entity.total_energy == round(100 * 5 / 60.0 / 2, 2)
        entity.incremente_energy()
        assert entity.total_energy == round(2 * 100 * 5 / 60.0 / 2, 2)

    # change temperature to a higher value
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        await send_temperature_change_event(entity, 18, datetime.now())
        assert tpi_algo.on_percent == 0.3
        assert entity.power_manager.mean_cycle_power == 30.0

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0

    with patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        entity.incremente_energy()
        assert round(entity.total_energy, 2) == round((2.0 + 0.3) * 100 * 5 / 60.0 / 2, 2)

        entity.incremente_energy()
        assert round(entity.total_energy, 2) == round((2.0 + 0.6) * 100 * 5 / 60.0 / 2, 2)

    # change temperature to a much higher value so that heater will be shut down
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        await send_temperature_change_event(entity, 20, datetime.now())
        assert tpi_algo.on_percent == 0.0
        assert entity.power_manager.mean_cycle_power == 0.0

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0

        entity.incremente_energy()
        # No change on energy
        assert round(entity.total_energy, 2) == round((2.0 + 0.6) * 100 * 5 / 60.0 / 2, 2)

        # Still no change
        entity.incremente_energy()
        assert round(entity.total_energy, 2) == round((2.0 + 0.6) * 100 * 5 / 60.0 / 2, 2)


async def test_power_management_energy_over_climate(
    hass: HomeAssistant, fake_temp_sensor: MockTemperatureSensor, fake_ext_temp_sensor: MockTemperatureSensor, fake_underlying_climate: MockClimate
):
    """Test the Power management for a over_climate thermostat"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    # Starts off
    fake_underlying_climate.set_hvac_mode(VThermHvacMode_OFF)
    fake_underlying_climate.set_hvac_action(HVACAction.OFF)

    # the_mock_underlying = MockClimate(hass=hass, unique_id="mock_climate", name="TheMockClimate")
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
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps)
    assert entity
    assert entity.is_over_climate

    assert entity.total_energy == 0
    assert entity.hvac_mode == VThermHvacMode_OFF
    assert entity.hvac_action == HVACAction.OFF

    now = datetime.now(tz=get_tz(hass))
    entity._set_now(now)

    # 1. Start heating
    now = now + timedelta(minutes=3)
    entity._set_now(now)

    await send_temperature_change_event(entity, 15, now)
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()

    await entity.async_set_preset_mode(VThermPreset.BOOST)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()

    await wait_for_local_condition(lambda: fake_underlying_climate.hvac_mode == VThermHvacMode_HEAT and fake_underlying_climate.hvac_action == HVACAction.HEATING)
    await wait_for_local_condition(lambda: entity.hvac_mode == VThermHvacMode_HEAT and entity.hvac_action == HVACAction.HEATING)

    # assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    # assert entity.hvac_action is HVACAction.OFF
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 19
    assert entity.current_temperature == 15

    assert entity.power_manager.mean_cycle_power == 100.0  # fully active yet
    assert entity.is_device_active is True

    # We have the start event and not the end event
    assert entity._underlying_climate_mean_power_cycle == 100.0
    assert (entity._underlying_climate_start_hvac_action_date - now).total_seconds() < 1

    # 2. wait a few and increment energy
    now = now + timedelta(minutes=3)
    entity._set_now(now)
    entity.incremente_energy()
    assert entity.total_energy == 5  # Vtherm is heating 100 w x 3 min / 60
    assert entity._underlying_climate_start_hvac_action_date == now

    # 3. wait a few and send a climate_change event with HVACAction=IDLE (end of heating)
    now = now + timedelta(minutes=10)
    entity._set_now(now)
    fake_underlying_climate.set_hvac_action(HVACAction.IDLE)
    await send_climate_change_event(
        entity,
        new_hvac_mode=VThermHvacMode_HEAT,
        old_hvac_mode=VThermHvacMode_HEAT,
        new_hvac_action=HVACAction.IDLE,
        old_hvac_action=HVACAction.HEATING,
        date=now,
        underlying_entity_id="climate.mock_climate",
    )
    # We have the end event -> we should have some power and on_percent
    assert entity._underlying_climate_start_hvac_action_date is None

    # 3 minutes at 100 W
    assert entity.total_energy == round(5 + 100 * 10 / 60, 2)

    assert entity.is_device_active is False
    assert entity._underlying_climate_start_hvac_action_date is None

    # Test the re-increment
    entity.incremente_energy()
    assert entity.total_energy == round(5 + 100 * 10 / 60, 2)  # No change

    entity.remove_thermostat()


async def test_power_management_turn_off_while_shedding(hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager, fake_underlying_switch: MockSwitch):
    """Test the Power management and that we can turn off a Vtherm that
    is in overpowering state"""

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
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(hass, entry, "climate.theoverswitchmockname", temps)
    assert entity

    now: datetime = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN
    assert entity.target_temperature == 19

    # make the heater heats
    await send_temperature_change_event(entity, 15, now)
    await send_ext_temperature_change_event(entity, 1, now)
    await hass.async_block_till_done()

    assert entity.power_percent > 0

    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", 50),
            "sensor.the_max_power_sensor": State("sensor.the_max_power_sensor", 49),
        },
        State("unknown.entity_id", "unknown"),
    )

    # 1. Set VTherm to overpowering
    # Send power max mesurement too low and VThermHvacMode is on and device is active
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"), \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active", new_callable=PropertyMock, return_value=True):
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_max_power_change_event(entity, 49, now)
        assert entity.power_manager.is_overpowering_detected is True
        # All configuration is complete and power is > power_max we switch to POWER preset
        assert entity.preset_mode == VThermPreset.POWER
        assert entity.power_manager.overpowering_state is STATE_ON
        assert entity.target_temperature == 12

        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count >= 1 # should be 1 but is_device_active is patched to True so can be called twice

    # 2. Turn-off Vtherm
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active", new_callable=PropertyMock, return_value=True):
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await entity.async_set_hvac_mode(VThermHvacMode_OFF)
        await wait_for_local_condition(lambda: entity.hvac_mode == VThermHvacMode_OFF)
        assert entity.hvac_mode == VThermHvacMode_OFF
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.is_overpowering_detected is False

        await VersatileThermostatAPI.get_vtherm_api().central_power_manager._do_immediate_shedding()
        await wait_for_local_condition(lambda: entity.power_manager.is_overpowering_detected is False)

        # VTherm is off and overpowering if off also
        assert entity.hvac_mode == VThermHvacMode_OFF
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.is_overpowering_detected is False
        assert entity.power_manager.overpowering_state is STATE_OFF
        assert entity.target_temperature == 19

    entity.remove_thermostat()


async def test_power_management_over_climate_valve(
    hass: HomeAssistant, fake_temp_sensor: MockTemperatureSensor, fake_ext_temp_sensor: MockTemperatureSensor, fake_underlying_climate: MockClimate, fake_opening_degree: MockNumber
):
    """Test the power and energy calculation for over_climate_valve thermostat"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        version=2,
        minor_version=2,
        data={
            CONF_NAME: "TheOverClimateValveMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: ["number.mock_opening_degree"],
            CONF_CLOSING_DEGREE_LIST: [],
            CONF_SYNC_ENTITY_LIST: [],
            CONF_SYNC_WITH_CALIBRATION: False,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: False,
        }
        | MOCK_DEFAULT_FEATURE_CONFIG
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    # mock_get_state will be called for each OPENING/CLOSING/OFFSET_CALIBRATION list
    fake_opening_degree.set_native_value(10)
    fake_opening_degree.set_min_value(0)
    fake_opening_degree.set_max_value(100)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatevalvemockname", temps=default_temperatures)

    assert vtherm
    vtherm._set_now(now)
    assert isinstance(vtherm, ThermostatOverClimateValve)

    assert vtherm.name == "TheOverClimateValveMockName"
    assert vtherm.is_over_climate is True
    assert vtherm.have_valve_regulation is True

    assert vtherm.hvac_action is HVACAction.OFF
    assert vtherm.vtherm_hvac_mode is VThermHvacMode_OFF

    assert vtherm.is_initialized is True

    assert vtherm.is_device_active is False
    assert vtherm.valve_open_percent == 0

    # the underlying set temperature call but no call to valve yet because VTherm is off
    await wait_for_local_condition(lambda: fake_opening_degree.native_value == 0)

    assert vtherm.nb_device_actives == 0

    assert vtherm.total_energy == 0.0
    assert vtherm.power_manager.mean_cycle_power == 0.0

    assert fake_underlying_climate.hvac_mode == VThermHvacMode_OFF
    assert fake_underlying_climate.hvac_action == HVACAction.OFF

    # 2. Turn on the VTherm and make heating
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    fake_temp_sensor.set_native_value(18)
    fake_ext_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()
    # await send_temperature_change_event(vtherm, 18, now, True)
    # await send_ext_temperature_change_event(vtherm, 18, now, True)
    await wait_for_local_condition(lambda: vtherm.current_temperature == 18 and vtherm.current_outdoor_temperature == 18)

    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)  # 19
    await wait_for_local_condition(lambda: vtherm.proportional_algorithm.on_percent == 0.4)  # 0.4 = (19-18)*0.3 + (19-18)*0.1

    assert vtherm.hvac_action is HVACAction.HEATING
    assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert vtherm.total_energy == 0.0
    assert vtherm.power_manager.mean_cycle_power == 1 * 0.4  # device_power * on_percent

    # sometimes this test failed here
    await asyncio.sleep(0.1)  # wait for the async_set_hvac_mode and async_set_preset_mode to be processed
    await wait_for_local_condition(lambda: fake_underlying_climate.hvac_mode == HVACMode.HEAT and fake_underlying_climate.hvac_action == HVACAction.HEATING)
    await wait_for_local_condition(lambda: vtherm._underlying_climate_start_hvac_action_date is not None)

    # 3. simulate a cycle that should calculate energy
    now = now + timedelta(minutes=5)
    vtherm._set_now(now)

    await vtherm.async_control_heating()
    assert vtherm.total_energy == 0.03 # 5 minutes (1/12 hour) at 0.4 power -> 0.4/12=0.0333 rounded to 0.03
    assert vtherm.power_manager.mean_cycle_power == 1 * 0.4  # device_power * on_percent

    # 4. limit the power by changing the room temperature closer to target
    now = now + timedelta(minutes=2)
    vtherm._set_now(now)
    fake_temp_sensor.set_native_value(18.5)
    # await send_temperature_change_event(vtherm, 18.5, now, True)
    await wait_for_local_condition(lambda: vtherm.proportional_algorithm.on_percent == 0.25) # 0.25 = (19-18.5)*0.3 + (19-18)*0.1

    # Simulate a cycle
    await vtherm.async_control_heating()
    assert vtherm.total_energy == 0.03 + 0.02  # 2 minutes (1/30 hour) at 0.25 power -> 0.25/30=0.0083 rounded to 0.01
    assert vtherm.power_manager.mean_cycle_power == 1 * 0.25  # device_power * on_percent

    # 5. Turn off the VTherm after 3 minutes of heating
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)

    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    # Simulate the underlying climate starting heating
    # await send_climate_change_event(
    #     vtherm,
    #     new_hvac_mode=VThermHvacMode_OFF,
    #     old_hvac_mode=VThermHvacMode_HEAT,
    #     new_hvac_action=HVACAction.OFF,
    #     old_hvac_action=HVACAction.HEATING,
    #     date=now,
    #     underlying_entity_id="climate.mock_climate",
    # )

    await wait_for_local_condition(lambda: vtherm.proportional_algorithm.on_percent == 0.0)

    assert vtherm.total_energy == 0.06 # 0.03 + 0.02 + 0.01
    assert vtherm.power_manager.mean_cycle_power == 0.0
    assert vtherm.valve_open_percent == 0

    vtherm.remove_thermostat()
