# pylint: disable=unused-argument, line-too-long, protected-access
""" Test the Window management """
# import asyncio
import logging
from unittest.mock import patch, call
from datetime import datetime, timedelta

from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_inverted_switch(hass: HomeAssistant, fake_underlying_switch: MockSwitch, fake_temp_sensor: MockTemperatureSensor, fake_ext_temp_sensor: MockTemperatureSensor):
    """Test the Window auto management"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 21,
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
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_WINDOW_AUTO_OPEN_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_CLOSE_THRESHOLD: 0.1,
            CONF_WINDOW_AUTO_MAX_DURATION: 0,  # Should be 0 for test
            CONF_INVERSE_SWITCH: True,
        },
    )

    # 0. Create the entity
    entity: ThermostatOverSwitch = await create_thermostat(hass, entry, "climate.theoverswitchmockname", temps)
    assert entity
    assert entity.is_inversed

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now = datetime.now(tz)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 21

    await wait_for_local_condition(lambda: entity.is_device_active is False)

    # 1. Make the temperature down to activate the switch
    # Cancel existing cycle so the new cycle can start
    entity.cycle_scheduler.cancel_cycle()
    now = now + timedelta(minutes=4)
    entity._set_now(now)
    fake_temp_sensor.set_native_value(19)
    # await send_temperature_change_event(entity, 19, event_timestamp)

    # The heater turns on (for inverted switch, underlying switch turns OFF)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    # not updated cause mocked assert entity.is_device_active is True

    # For inverted switch: heater ON -> underlying switch OFF
    await wait_for_local_condition(lambda: fake_underlying_switch.is_on is False)

    # 2. Make the temperature up to deactivate the switch
    now = now + timedelta(minutes=3)
    entity._set_now(now)
    fake_temp_sensor.set_native_value(25)

    # The heater turns on
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    # not updated cause mocked assert entity.is_device_active is False

    # there is no change because the cycle is currenlty running.
    # we should simulate the end of the cycle to see of underlying switch turns on
    await entity._underlyings[0].turn_off()

    await wait_for_local_condition(lambda: fake_underlying_switch.is_on is True)

    # assert mock_service_call.call_count == 1
    # mock_service_call.assert_has_calls(
    #     [
    #         call.async_call(
    #             "switch", SERVICE_TURN_ON, {"entity_id": "switch.mock_switch"}
    #         ),
    #     ]
    # )

    # Clean the entity
    entity.remove_thermostat()
