# pylint: disable=protected-access, unused-argument, line-too-long
""" Test the Power management """
from unittest.mock import patch, call
from datetime import datetime, timedelta
import logging

from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
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
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off:
        await send_max_power_change_event(entity, 149, datetime.now())
        assert await entity.check_overpowering() is True
        # All configuration is complete and power is > power_max but we stay in Boost cause thermostat if Off
        assert entity.preset_mode is PRESET_BOOST
        assert entity.overpowering_state is True

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
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

    entity: ThermostatOverSwitch = await create_thermostat(
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
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
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
                        "current_power_consumption": 100.0,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 1

    # Send power mesurement low to unseet power preset
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
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


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_energy_over_switch(
    hass: HomeAssistant, skip_hass_states_is_state
):
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
            CONF_HEATER_2: "switch.mock_switch2",
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

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
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

        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.preset_mode is PRESET_BOOST
        assert entity.target_temperature == 19
        assert entity.current_temperature == 15
        assert tpi_algo.on_percent == 1

        assert entity.device_power == 100.0

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
        assert entity.mean_cycle_power == 30.0

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
        assert entity.mean_cycle_power == 0.0

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
                CONF_USE_POWER_FEATURE: True,
                CONF_USE_PRESENCE_FEATURE: False,
                CONF_CLIMATE: "climate.mock_climate",
                CONF_MINIMAL_ACTIVATION_DELAY: 30,
                CONF_SECURITY_DELAY_MIN: 5,
                CONF_SECURITY_MIN_ON_PERCENT: 0.3,
                CONF_POWER_SENSOR: "sensor.mock_power_sensor",
                CONF_MAX_POWER_SENSOR: "sensor.mock_power_max_sensor",
                CONF_DEVICE_POWER: 100,
                CONF_PRESET_POWER: 12,
            },
        )

        entity: ThermostatOverSwitch = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
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
    assert entity.mean_cycle_power is None
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
    )
    # We have the end event -> we should have some power and on_percent
    assert entity._underlying_climate_start_hvac_action_date is None

    # 3 minutes at 100 W
    assert entity.total_energy == 100 * 3.0 / 60

    # Test the re-increment
    entity.incremente_energy()
    assert entity.total_energy == 2 * 100 * 3.0 / 60
