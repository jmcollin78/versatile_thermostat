""" Test the Power management """
from unittest.mock import patch, call
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from datetime import datetime

import logging

logging.getLogger().setLevel(logging.DEBUG)


async def test_power_management_hvac_off(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the Power management"""

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
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_POWER_SENSOR: "sensor.mock_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.mock_power_max_sensor",
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: "eco",
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.preset_mode is PRESET_BOOST
    assert entity.target_temperature == 19
    assert entity.overpowering_state is None
    assert entity.hvac_mode == HVACMode.OFF

    # Send power mesurement
    await send_power_change_event(entity, 50, datetime.now())
    assert await entity.check_overpowering() is False

    # All configuration is not complete
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None

    # Send power max mesurement
    await send_max_power_change_event(entity, 300, datetime.now())
    assert await entity.check_overpowering() is False
    # All configuration is complete and power is < power_max
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is False

    # Send power max mesurement too low but HVACMode is off
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_heater_turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_underlying_entity_turn_off"
    ) as mock_heater_off:
        await send_max_power_change_event(entity, 149, datetime.now())
        assert await entity.check_overpowering() is True
        # All configuration is complete and power is > power_max but we stay in Boost cause thermostat if Off
        assert entity.preset_mode is PRESET_BOOST
        assert entity.overpowering_state is True

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0


async def test_power_management_hvac_on(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Power management"""

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
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_POWER_SENSOR: "sensor.mock_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.mock_power_max_sensor",
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is None
    assert entity.target_temperature == 19

    # Send power mesurement
    await send_power_change_event(entity, 50, datetime.now())
    # Send power max mesurement
    await send_max_power_change_event(entity, 300, datetime.now())
    assert await entity.check_overpowering() is False
    # All configuration is complete and power is < power_max
    assert entity.preset_mode is PRESET_BOOST
    assert entity.overpowering_state is False

    # Send power max mesurement too low and HVACMode is on
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_heater_turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_underlying_entity_turn_off"
    ) as mock_heater_off:
        await send_max_power_change_event(entity, 149, datetime.now())
        assert await entity.check_overpowering() is True
        # All configuration is complete and power is > power_max we switch to POWER preset
        assert entity.preset_mode is PRESET_POWER
        assert entity.overpowering_state is True
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
                        "current_power_max": 149,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 1

    # Send power mesurement low to unseet power preset
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_heater_turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_underlying_entity_turn_off"
    ) as mock_heater_off:
        await send_power_change_event(entity, 48, datetime.now())
        assert await entity.check_overpowering() is False
        # All configuration is complete and power is < power_max, we restore previous preset
        assert entity.preset_mode is PRESET_BOOST
        assert entity.overpowering_state is False
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
                        "current_power_max": 149,
                    },
                ),
            ],
            any_order=True,
        )
        # No current temperature is set so the heater wont be turned on
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0


async def test_power_management_energy(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the Power management energy mesurement"""

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
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            CONF_POWER_SENSOR: "sensor.mock_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.mock_power_max_sensor",
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    # set temperature to 15 so that on_percent will be set
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_heater_turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_underlying_entity_turn_off"
    ) as mock_heater_off:
        await send_temperature_change_event(entity, 15, datetime.now())
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_preset_mode(PRESET_BOOST)

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.target_temperature == 19
        assert entity.current_temperature == 15
        assert tpi_algo.on_percent == 1

        assert entity.mean_cycle_power == 100.0

        assert mock_send_event.call_count == 2
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0

    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_heater_turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat._async_underlying_entity_turn_off"
    ) as mock_heater_off:
        # change temperature to a higher value
        await send_temperature_change_event(entity, 18, datetime.now())
        assert tpi_algo.on_percent == 0.3
        assert entity.mean_cycle_power == 30.0

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0
