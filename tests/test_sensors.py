# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the normal start of a Thermostat """
from datetime import timedelta, datetime

from homeassistant.core import HomeAssistant

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime, UnitOfPower, UnitOfEnergy, PERCENTAGE

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode
from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.sensor import (
    EnergySensor,
    MeanPowerSensor,
    OnPercentSensor,
    OnTimeSensor,
    OffTimeSensor,
    LastTemperatureSensor,
    LastExtTemperatureSensor,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_sensors_over_switch(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test the sensors with a thermostat avec switch type"""

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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 200,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    energy_sensor: EnergySensor = search_entity(
        hass, "sensor.theoverswitchmockname_energy", "sensor"
    )
    assert energy_sensor

    mean_power_sensor: MeanPowerSensor = search_entity(
        hass, "sensor.theoverswitchmockname_mean_power_cycle", "sensor"
    )
    assert mean_power_sensor

    on_percent_sensor: OnPercentSensor = search_entity(
        hass, "sensor.theoverswitchmockname_power_percent", "sensor"
    )
    assert on_percent_sensor

    on_time_sensor: OnTimeSensor = search_entity(
        hass, "sensor.theoverswitchmockname_on_time", "sensor"
    )
    assert on_time_sensor

    off_time_sensor: OffTimeSensor = search_entity(
        hass, "sensor.theoverswitchmockname_off_time", "sensor"
    )
    assert off_time_sensor

    last_temperature_sensor: LastTemperatureSensor = search_entity(
        hass, "sensor.theoverswitchmockname_last_temperature_date", "sensor"
    )
    assert last_temperature_sensor is None  # Not crearted by default now

    last_ext_temperature_sensor: LastExtTemperatureSensor = search_entity(
        hass, "sensor.theoverswitchmockname_last_external_temperature_date", "sensor"
    )
    assert last_ext_temperature_sensor is None  # Not crearted by default now

    # Simulate the event reception
    await energy_sensor.async_my_climate_changed()
    assert energy_sensor.state == 0.0
    await mean_power_sensor.async_my_climate_changed()
    assert mean_power_sensor.state == 0.0
    await on_percent_sensor.async_my_climate_changed()
    assert on_percent_sensor.state == 0.0
    await on_time_sensor.async_my_climate_changed()
    assert on_time_sensor.state == 0.0
    await off_time_sensor.async_my_climate_changed()
    assert off_time_sensor.state == 300.0
    # await last_temperature_sensor.async_my_climate_changed()
    # assert last_temperature_sensor.state is not None
    # await last_ext_temperature_sensor.async_my_climate_changed()
    # assert last_ext_temperature_sensor.state is not None

    # last_temp_date = last_temperature_sensor.state

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    event_timestamp = now - timedelta(minutes=1)

    # Start the heater to get some values
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await send_temperature_change_event(entity, 15, event_timestamp)
    await send_ext_temperature_change_event(entity, 5, event_timestamp)

    entity.incremente_energy()

    await energy_sensor.async_my_climate_changed()
    assert energy_sensor.state == round(16.667, 2)
    assert energy_sensor.device_class == SensorDeviceClass.ENERGY
    assert energy_sensor.state_class == SensorStateClass.TOTAL_INCREASING
    # because device_power is 200
    assert energy_sensor.unit_of_measurement == UnitOfEnergy.WATT_HOUR

    await mean_power_sensor.async_my_climate_changed()
    assert mean_power_sensor.state == 200.0
    assert mean_power_sensor.device_class == SensorDeviceClass.POWER
    assert mean_power_sensor.state_class == SensorStateClass.MEASUREMENT
    # because device_power is 200
    assert mean_power_sensor.unit_of_measurement == UnitOfPower.WATT

    await on_percent_sensor.async_my_climate_changed()
    assert on_percent_sensor.state == 100.0
    assert on_percent_sensor.unit_of_measurement == PERCENTAGE

    await on_time_sensor.async_my_climate_changed()
    assert on_time_sensor.state == 300.0
    assert on_time_sensor.device_class == SensorDeviceClass.DURATION
    assert on_time_sensor.state_class == SensorStateClass.MEASUREMENT
    assert on_time_sensor.unit_of_measurement == UnitOfTime.SECONDS

    await off_time_sensor.async_my_climate_changed()
    assert off_time_sensor.state == 0.0
    assert off_time_sensor.device_class == SensorDeviceClass.DURATION
    assert off_time_sensor.state_class == SensorStateClass.MEASUREMENT
    assert off_time_sensor.unit_of_measurement == UnitOfTime.SECONDS

    # await last_temperature_sensor.async_my_climate_changed()
    # assert (
    #     last_temperature_sensor.state is not None
    #     and last_temperature_sensor.state != last_temp_date
    # )
    # assert last_temperature_sensor.device_class == SensorDeviceClass.TIMESTAMP
    #
    # await last_ext_temperature_sensor.async_my_climate_changed()
    # assert (
    #     last_ext_temperature_sensor.state is not None
    #     and last_ext_temperature_sensor.state != last_temp_date
    # )
    # assert last_ext_temperature_sensor.device_class == SensorDeviceClass.TIMESTAMP

    cancel_switchs_cycles(entity)


async def test_sensors_over_climate(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test the sensors with thermostat over climate type"""

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
                CONF_UNDERLYING_LIST: ["climate.mock_climate"],
                CONF_MINIMAL_ACTIVATION_DELAY: 30,
                CONF_MINIMAL_DEACTIVATION_DELAY: 0,
                CONF_SAFETY_DELAY_MIN: 5,
                CONF_SAFETY_MIN_ON_PERCENT: 0.3,
                CONF_DEVICE_POWER: 1.5,
                CONF_PRESET_POWER: 12,
            },
        )

        entity: BaseThermostat = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.is_over_climate

    energy_sensor: EnergySensor = search_entity(
        hass, "sensor.theoverclimatemockname_energy", "sensor"
    )
    assert energy_sensor

    last_temperature_sensor: LastTemperatureSensor = search_entity(
        hass, "sensor.theoverclimatemockname_last_temperature_date", "sensor"
    )
    # last_temperature_sensor is not created by default now
    assert last_temperature_sensor is None

    last_ext_temperature_sensor: LastExtTemperatureSensor = search_entity(
        hass, "sensor.theoverclimatemockname_last_external_temperature_date", "sensor"
    )
    # last_ext_temperature_sensor is not created by default now
    assert last_ext_temperature_sensor is None

    # Simulate the event reception
    await energy_sensor.async_my_climate_changed()
    assert energy_sensor.state == 0.0
    # await last_temperature_sensor.async_my_climate_changed()
    # assert last_temperature_sensor.state is not None
    # await last_ext_temperature_sensor.async_my_climate_changed()
    # assert last_ext_temperature_sensor.state is not None

    # last_temp_date = last_temperature_sensor.state

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    event_timestamp = now - timedelta(minutes=1)

    # Start the heater to get some values
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await send_temperature_change_event(entity, 15, event_timestamp)
    await send_ext_temperature_change_event(entity, 5, event_timestamp)

    # to add energy we must have HVACAction underlying climate event
    # Send a climate_change event with HVACAction=HEATING
    event_timestamp = now - timedelta(minutes=60)
    await send_climate_change_event(
        entity,
        new_hvac_mode=VThermHvacMode_HEAT,
        old_hvac_mode=VThermHvacMode_HEAT,
        new_hvac_action=HVACAction.HEATING,
        old_hvac_action=HVACAction.OFF,
        date=event_timestamp,
        underlying_entity_id="climate.mock_climate",
    )

    # Send a climate_change event with HVACAction=IDLE (end of heating)
    await send_climate_change_event(
        entity,
        new_hvac_mode=VThermHvacMode_HEAT,
        old_hvac_mode=VThermHvacMode_HEAT,
        new_hvac_action=HVACAction.IDLE,
        old_hvac_action=HVACAction.HEATING,
        date=now,
        underlying_entity_id="climate.mock_climate",
    )

    # 60 minutes heating with 1.5 kW heating -> 1.5 kWh
    await energy_sensor.async_my_climate_changed()
    assert energy_sensor.state == 1.5
    assert energy_sensor.device_class == SensorDeviceClass.ENERGY
    assert energy_sensor.state_class == SensorStateClass.TOTAL_INCREASING
    # because device_power is 1.5 kW
    assert energy_sensor.unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR

    entity.incremente_energy()
    await energy_sensor.async_my_climate_changed()
    assert energy_sensor.state == 3.0

    # disabled by default now
    # await last_temperature_sensor.async_my_climate_changed()
    # assert (
    #     last_temperature_sensor.state is not None
    #     and last_temperature_sensor.state != last_temp_date
    # )
    # assert last_temperature_sensor.device_class == SensorDeviceClass.TIMESTAMP
    #
    # await last_ext_temperature_sensor.async_my_climate_changed()
    # assert (
    #     last_ext_temperature_sensor.state is not None
    #     and last_ext_temperature_sensor.state != last_temp_date
    # )
    # assert last_ext_temperature_sensor.device_class == SensorDeviceClass.TIMESTAMP


async def test_sensors_over_climate_minimal(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test the sensors with thermostat over climate type"""

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
                CONF_UNDERLYING_LIST: ["climate.mock_climate"],
                CONF_MINIMAL_ACTIVATION_DELAY: 30,
                CONF_MINIMAL_DEACTIVATION_DELAY: 0,
                CONF_SAFETY_DELAY_MIN: 5,
                CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            },
        )

        entity: BaseThermostat = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert entity.is_over_climate

    energy_sensor: EnergySensor = search_entity(
        hass, "sensor.theoverclimatemockname_energy", "sensor"
    )
    assert energy_sensor is None

    # LastTemperatureSensor and LastExtTemperatureSensor are now not created by default
    last_temperature_sensor: LastTemperatureSensor = search_entity(
        hass, "sensor.theoverclimatemockname_last_temperature_date", "sensor"
    )
    assert last_temperature_sensor is None

    last_ext_temperature_sensor: LastExtTemperatureSensor = search_entity(
        hass, "sensor.theoverclimatemockname_last_external_temperature_date", "sensor"
    )
    assert last_ext_temperature_sensor is None
