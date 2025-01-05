# pylint: disable=wildcard-import, unused-wildcard-import, unused-argument, line-too-long, protected-access

""" Test the normal start of a Thermostat """
from unittest.mock import patch
from datetime import timedelta, datetime

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.binary_sensor import (
    SecurityBinarySensor,
    OverpoweringBinarySensor,
    WindowBinarySensor,
    MotionBinarySensor,
    PresenceBinarySensor,
)

from .commons import *


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_security_binary_sensors(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):   # pylint: disable=unused-argument
    """Test the security binary sensors in thermostat type"""

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
        },
    )

    entity: BaseThermostat = await create_thermostat (
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    security_binary_sensor: SecurityBinarySensor = search_entity(
        hass, "binary_sensor.theoverswitchmockname_security_state", "binary_sensor"
    )
    assert security_binary_sensor

    now: datetime = datetime.now(tz=get_tz(hass))

    # Security should be disabled
    await entity.async_set_preset_mode(PRESET_COMFORT)
    await entity.async_set_hvac_mode(HVACMode.HEAT)

    assert security_binary_sensor.state == STATE_OFF
    assert security_binary_sensor.device_class == BinarySensorDeviceClass.SAFETY

    # Set temperature in the past
    event_timestamp = now - timedelta(minutes=6)

    # set temperature to 15 so that on_percent will be > safety_min_on_percent (0.2)
    await send_temperature_change_event(entity, 15, event_timestamp)

    assert entity.safety_state is STATE_ON
    # Simulate the event reception
    await security_binary_sensor.async_my_climate_changed()
    assert security_binary_sensor.state == STATE_ON

    # set temperature now
    await send_temperature_change_event(entity, 15, now)
    assert entity.safety_state is not STATE_ON
    # Simulate the event reception
    await security_binary_sensor.async_my_climate_changed()
    assert security_binary_sensor.state == STATE_OFF


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_overpowering_binary_sensors(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
    init_central_power_manager,
):
    """Test the overpowering binary sensors in thermostat type"""

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
            CONF_HEATER: "switch.mock_switch",
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

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname", temps
    )
    assert entity

    overpowering_binary_sensor: OverpoweringBinarySensor = search_entity(
        hass, "binary_sensor.theoverswitchmockname_overpowering_state", "binary_sensor"
    )
    assert overpowering_binary_sensor

    now: datetime = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)

    # Overpowering should be not set because poer have not been received
    await entity.async_set_preset_mode(PRESET_COMFORT)
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await send_temperature_change_event(entity, 15, now)
    assert entity.power_manager.is_overpowering_detected is False
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN

    await overpowering_binary_sensor.async_my_climate_changed()
    assert overpowering_binary_sensor.state is STATE_OFF
    assert overpowering_binary_sensor.device_class == BinarySensorDeviceClass.POWER

    # Send power mesurement
    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", 150),
            "sensor.the_max_power_sensor": State("sensor.the_max_power_sensor", 100),
        },
        State("unknown.entity_id", "unknown"),
    )
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active", return_value="True"):
    # fmt: on
        await send_power_change_event(entity, 150, now)
        await send_max_power_change_event(entity, 100, now)

        assert entity.power_manager.is_overpowering_detected is True
        assert entity.power_manager.overpowering_state is STATE_ON

        # Simulate the event reception
        await overpowering_binary_sensor.async_my_climate_changed()
        assert overpowering_binary_sensor.state == STATE_ON

    # set max power to a low value
    side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 201))
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)
        await send_max_power_change_event(entity, 201, now)
        assert entity.power_manager.is_overpowering_detected is False
        assert entity.power_manager.overpowering_state is STATE_OFF
        # Simulate the event reception
        await overpowering_binary_sensor.async_my_climate_changed()
        assert overpowering_binary_sensor.state == STATE_OFF


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_window_binary_sensors(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test the window binary sensors in thermostat type"""

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,  # important to not been obliged to wait
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    window_binary_sensor: WindowBinarySensor = search_entity(
        hass, "binary_sensor.theoverswitchmockname_window_state", "binary_sensor"
    )
    assert window_binary_sensor

    now: datetime = datetime.now(tz=get_tz(hass))

    # Overpowering should be not set because poer have not been received
    await entity.async_set_preset_mode(PRESET_COMFORT)
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await send_temperature_change_event(entity, 15, now)
    assert entity.window_state is STATE_UNKNOWN

    await window_binary_sensor.async_my_climate_changed()
    assert window_binary_sensor.state is STATE_OFF
    assert window_binary_sensor.device_class == BinarySensorDeviceClass.WINDOW

    # Open the window
    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_window_condition = await send_window_change_event(entity, True, False, now)
        # simulate the call to try_window_condition
        await try_window_condition(None)

    assert entity.window_state is STATE_ON

    # Simulate the event reception
    await window_binary_sensor.async_my_climate_changed()
    assert window_binary_sensor.state == STATE_ON

    # close the window
    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_window_condition = await send_window_change_event(entity, False, True, now)
        # simulate the call to try_window_condition
        await try_window_condition(None)

    assert entity.window_state is STATE_OFF

    # Simulate the event reception
    await window_binary_sensor.async_my_climate_changed()
    assert window_binary_sensor.state == STATE_OFF


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_motion_binary_sensors(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test the motion binary sensors in thermostat type"""

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: True,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_MOTION_SENSOR: "binary_sensor.mock_motion_sensor",
            CONF_MOTION_DELAY: 0,  # important to not been obliged to wait
            CONF_MOTION_PRESET: PRESET_BOOST,
            CONF_NO_MOTION_PRESET: PRESET_ECO,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    motion_binary_sensor: MotionBinarySensor = search_entity(
        hass, "binary_sensor.theoverswitchmockname_motion_state", "binary_sensor"
    )
    assert motion_binary_sensor

    now: datetime = datetime.now(tz=get_tz(hass))

    # Overpowering should be not set because poer have not been received
    await entity.async_set_preset_mode(PRESET_COMFORT)
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await send_temperature_change_event(entity, 15, now)
    assert entity.motion_state is STATE_UNKNOWN

    await motion_binary_sensor.async_my_climate_changed()
    assert motion_binary_sensor.state is STATE_OFF
    assert motion_binary_sensor.device_class == BinarySensorDeviceClass.MOTION

    # Detect motion
    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_motion_condition = await send_motion_change_event(entity, True, False, now)
        # simulate the call to try_window_condition
        await try_motion_condition(None)

    assert entity.motion_state is STATE_ON

    # Simulate the event reception
    await motion_binary_sensor.async_my_climate_changed()
    assert motion_binary_sensor.state == STATE_ON

    # Undetect motion
    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_motion_condition = await send_motion_change_event(entity, False, True, now)
        # simulate the call to try_motion_condition
        await try_motion_condition(None)

    assert entity.motion_state is STATE_OFF

    # Simulate the event reception
    await motion_binary_sensor.async_my_climate_changed()
    assert motion_binary_sensor.state == STATE_OFF


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_presence_binary_sensors(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test the presence binary sensors in thermostat type"""

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            "eco_away_temp": 12,
            "comfort_away_temp": 13,
            "boost_away_temp": 14,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: True,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_PRESENCE_SENSOR: "binary_sensor.mock_presence_sensor",
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    presence_binary_sensor: PresenceBinarySensor = search_entity(
        hass, "binary_sensor.theoverswitchmockname_presence_state", "binary_sensor"
    )
    assert presence_binary_sensor

    now: datetime = datetime.now(tz=get_tz(hass))

    # Overpowering should be not set because poer have not been received
    await entity.async_set_preset_mode(PRESET_COMFORT)
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await send_temperature_change_event(entity, 15, now)
    assert entity.presence_state is STATE_UNKNOWN

    await presence_binary_sensor.async_my_climate_changed()
    assert presence_binary_sensor.state is STATE_OFF
    assert presence_binary_sensor.device_class == BinarySensorDeviceClass.PRESENCE

    # Detect motion
    await send_presence_change_event(entity, True, False, now)

    assert entity.presence_state is STATE_ON

    # Simulate the event reception
    await presence_binary_sensor.async_my_climate_changed()
    assert presence_binary_sensor.state == STATE_ON

    # Undetect motion
    await send_presence_change_event(entity, False, True, now)

    assert entity.presence_state is STATE_OFF

    # Simulate the event reception
    await presence_binary_sensor.async_my_climate_changed()
    assert presence_binary_sensor.state == STATE_OFF


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_binary_sensors_over_climate_minimal(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test the binary sensors with thermostat over climate type"""

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
                "eco_temp": 17,
                "comfort_temp": 18,
                "boost_temp": 19,
                CONF_USE_WINDOW_FEATURE: False,
                CONF_USE_MOTION_FEATURE: False,
                CONF_USE_POWER_FEATURE: False,
                CONF_USE_PRESENCE_FEATURE: False,
                CONF_CLIMATE: "climate.mock_climate",
                CONF_MINIMAL_ACTIVATION_DELAY: 30,
                CONF_SAFETY_DELAY_MIN: 5,
                CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            },
        )

        entity: BaseThermostat = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.is_over_climate

    security_binary_sensor: SecurityBinarySensor = search_entity(
        hass, "binary_sensor.theoverclimatemockname_security_state", "binary_sensor"
    )
    assert security_binary_sensor is not None

    overpowering_binary_sensor: OverpoweringBinarySensor = search_entity(
        hass, "binary_sensor.theoverclimatemockname_overpowering_state", "binary_sensor"
    )
    assert overpowering_binary_sensor is None

    window_binary_sensor: WindowBinarySensor = search_entity(
        hass, "binary_sensor.theoverclimatemockname_window_state", "binary_sensor"
    )
    assert window_binary_sensor is None

    motion_binary_sensor: MotionBinarySensor = search_entity(
        hass, "binary_sensor.theoverclimatemockname_motion_state", "binary_sensor"
    )
    assert motion_binary_sensor is None

    presence_binary_sensor: PresenceBinarySensor = search_entity(
        hass, "binary_sensor.theoverclimatemockname_presence_state", "binary_sensor"
    )
    assert presence_binary_sensor is None
