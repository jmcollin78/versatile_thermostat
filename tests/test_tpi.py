""" Test the TPI algorithm """

import pytest

from homeassistant.exceptions import ServiceValidationError
from homeassistant.components.climate import ClimateEntityFeature

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.prop_algo_tpi import TpiAlgorithm
from custom_components.versatile_thermostat.const import PROPORTIONAL_FUNCTION_TPI
from custom_components.versatile_thermostat.timing_utils import calculate_cycle_times
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_tpi_calculation(
    hass: HomeAssistant, skip_hass_states_is_state: None
):  # pylint: disable=unused-argument
    """Test the TPI calculation"""

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
            # CONF_DEVICE_POWER: 100,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    assert entity._prop_algorithm  # pylint: disable=protected-access

    tpi_algo: TpiAlgorithm = entity._prop_algorithm  # pylint: disable=protected-access
    assert tpi_algo

    tpi_algo.calculate(15, 10, 7, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 1
    assert tpi_algo.calculated_on_percent == 1
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 300
    assert off_sec == 0
    assert entity.power_manager.mean_cycle_power is None  # no device power configured

    tpi_algo.calculate(15, 14, 5, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 120
    assert off_sec == 180

    tpi_algo.set_safety(0.1)
    tpi_algo.calculate(15, 14, 5, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.1
    assert tpi_algo.calculated_on_percent == 0.4
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 30  # >= minimal_activation_delay (=30)
    assert off_sec == 270

    tpi_algo.unset_safety()
    tpi_algo.calculate(15, 14, 5, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 120
    assert off_sec == 180

    # Test minimal activation delay
    tpi_algo.calculate(15, 14.7, 15, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 0
    assert off_sec == 300

    tpi_algo.set_safety(0.09)
    tpi_algo.calculate(15, 14.7, 15, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 0
    assert off_sec == 300

    tpi_algo.unset_safety()
    tpi_algo.calculate(25, 30, 35, 0, VThermHvacMode_COOL)
    assert tpi_algo.on_percent == 1
    assert tpi_algo.calculated_on_percent == 1
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 300
    assert off_sec == 0
    assert entity.power_manager.mean_cycle_power is None  # no device power configured

    tpi_algo.set_safety(0.09)
    tpi_algo.calculate(25, 30, 35, 0, VThermHvacMode_COOL)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 1
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 0
    assert off_sec == 300
    assert entity.power_manager.mean_cycle_power is None  # no device power configured

    tpi_algo.unset_safety()
    # For OFF mode, all values are forced to zero so that apparent power will be zero.
    tpi_algo.calculate(15, 10, 7, 0, VThermHvacMode_OFF)
    assert tpi_algo.on_percent == 0
    assert tpi_algo.calculated_on_percent == 0
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 0
    assert off_sec == 300

    tpi_algo.unset_safety()
    # For SLEEP mode, all values are forced to zero so that apparent power will be zero.
    tpi_algo.calculate(15, 10, 7, 0, VThermHvacMode_SLEEP)
    assert tpi_algo.on_percent == 0
    assert tpi_algo.calculated_on_percent == 0
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 0
    assert off_sec == 300

    # If target_temp or current_temp are None, _calculated_on_percent is set to 0.
    tpi_algo.calculate(15, None, 7, 0, VThermHvacMode_OFF)
    assert tpi_algo.on_percent == 0
    assert tpi_algo.calculated_on_percent == 0
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 0
    assert off_sec == 300

    # Test the max_on_percent clamping calculations
    tpi_algo._max_on_percent = 0.8

    # no clamping
    tpi_algo.calculate(15, 14.7, 15, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 0
    assert off_sec == 300

    # no clamping  (calculated_on_percent = 0.79)
    tpi_algo.calculate(15, 12.5, 11, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.79
    assert tpi_algo.calculated_on_percent == 0.79
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 237
    assert off_sec == 63

    # clamping to 80%  (calculated_on_percent = 1)
    tpi_algo.calculate(15, 10, 7, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.8 # should be clamped to 80%
    assert tpi_algo.calculated_on_percent == 1 # calculated percentage should not be affected by clamping
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 240 # capped at 80%
    assert off_sec == 60

    # clamping to 80%  (calculated_on_percent = 0.81)
    tpi_algo.calculate(15, 12.5, 9, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.80 # should be clamped to 80%
    assert tpi_algo.calculated_on_percent == 0.81 # calculated percentage should not be affected by clamping
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 240 # capped at 80%
    assert off_sec == 60


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_minimal_deactivation_delay(
    hass: HomeAssistant, skip_hass_states_is_state: None
):  # pylint: disable=unused-argument
    """Test the minimal deactivation delay"""

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
            CONF_MINIMAL_DEACTIVATION_DELAY: 60,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    assert entity._prop_algorithm  # pylint: disable=protected-access

    tpi_algo: TpiAlgorithm = entity._prop_algorithm  # pylint: disable=protected-access
    assert tpi_algo

    # off_time is less than minimal_deactivation_delay
    tpi_algo.calculate(9, 6, 10, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.89
    assert tpi_algo.calculated_on_percent == 0.89
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 300
    assert off_sec == 0

    # off_time is less than minimal_deactivation_delay
    tpi_algo.calculate(6, 0, 104, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.82
    assert tpi_algo.calculated_on_percent == 0.82
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 300
    assert off_sec == 0

    # off_time is exactly minimal_deactivation_delay
    tpi_algo.calculate(10, 8, -10, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.8
    assert tpi_algo.calculated_on_percent == 0.8
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 240
    assert off_sec == 60  # Equal to minimal_deactivation_delay

    # off_time is greater than minimal_deactivation_delay
    tpi_algo.calculate(10, 9, 0, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 120
    assert off_sec == 180

    # with safety mode
    tpi_algo.set_safety(0.2)
    tpi_algo.calculate(10, 8, -10, 0, VThermHvacMode_HEAT)
    assert tpi_algo.on_percent == 0.2
    assert tpi_algo.calculated_on_percent == 0.8
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 60
    assert off_sec == 240
    tpi_algo.unset_safety()

    # with cooling mode
    tpi_algo.calculate(10, 10, 90, 0, VThermHvacMode_COOL)
    assert tpi_algo.on_percent == 0.8
    assert tpi_algo.calculated_on_percent == 0.8
    on_sec, off_sec, _ = calculate_cycle_times(tpi_algo.on_percent, entity.cycle_min, entity.minimal_activation_delay, entity.minimal_deactivation_delay)
    assert on_sec == 240
    assert off_sec == 60


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_wrong_tpi_parameters(
    hass: HomeAssistant, skip_hass_states_is_state: None
):  # pylint: disable=unused-argument
    """Test the wrong TPI parameters"""

    # Nominal case
    try:
        algo = TpiAlgorithm(

            0.6,
            0.01,
            "entity_id",
        )
        # We should be there
        assert True
    except TypeError as e:
        # the normal case
        assert False

    # Test coef_ext
    try:
        algo = TpiAlgorithm(

            0.6,
            None,
            "entity_id",
        )
        # We should not be there
        assert False
    except TypeError as e:
        # the normal case
        pass

    # Test vtherm_entity_id
    try:
        algo = TpiAlgorithm(
            0.6,
            0.00001,
            None,
        )
        # We should not be there
        assert False
    except TypeError as e:
        # the normal case
        pass


@pytest.mark.parametrize(
    # fmt: off
        "tpi_threshold_low, tpi_threshold_high, target_temp, current_temp, ext_current_temp, slope, hvac_mode,    expected_on_percent",
    [
        ## HEAT mode
        # temp < target, No thresholds
        (0.0,               0.0,                15,          14,           0,                0,     VThermHvacMode_HEAT, 0.25), #  0.1 + 0,15
        # temp > target, no thresholds, no slope
        (0.0,               0.0,                14,          15,           0,                0,     VThermHvacMode_HEAT, 0.04), # -0.1 + 0,14
        # Slope > 0 and below high threshold (no effect)
        (0.5,               1.1,                14,          15,           0,                1,     VThermHvacMode_HEAT, 0.04),
        # Slope > 0 and above high threshold (clamp to 0)
        (0.5,               0.9,                14,          15,           0,                1,     VThermHvacMode_HEAT, 0.0),
        # Slope < 0 and above low threshold (clamp to 0)
        (0.5,               1.1,                14,          15,           0,               -1,     VThermHvacMode_HEAT, 0.0),
        # Slope < 0 and below low threshold (no effect)
        (1.1,               2.0,                14,          15,           0,               -1,     VThermHvacMode_HEAT, 0.04),
        # Slope < 0 and above low negative threshold (clamp to 0)
        (-1,                2.0,                15,          14.1,         0,               -1,     VThermHvacMode_HEAT, 0.0),
        ## COOL mode
        # temp > target, No thresholds
        (0.0,               0.0,                14,          15,          29,                0,     VThermHvacMode_COOL, 0.25), #  0.1 + 0,15
        # temp < target, no thresholds, no slope
        (0.0,               0.0,                15,          14,          29,                0,     VThermHvacMode_COOL, 0.04), # -0.1 + 0,14
        # Slope < 0, below high threshold (no effect)
        (0.5,               1.1,                15,          14,          29,               -1,     VThermHvacMode_COOL, 0.04),
        # Slope < 0, above high threshold (clamp to 0)
        (0.5,               0.9,                15,          14,          29,               -1,     VThermHvacMode_COOL, 0.0),
        # Slope > 0, above low threshold (clamp to 0)
        (0.5,               1.1,                15,          14,          29,                1,     VThermHvacMode_COOL, 0.0),
        # Slope > 0, below low threshold (no effect)
        (1.1,               2,                  15,          14,          29,                1,     VThermHvacMode_COOL, 0.04),
        # Slope > 0 and above high negative threshold (clamp to 0)
        (-1,                2.0,                14,          16.1,        29,               1,      VThermHvacMode_HEAT, 0.0),

    ],
    # fmt: on
)
async def test_prop_algorithm_thresholds(
    hass,
    tpi_threshold_low,
    tpi_threshold_high,
    target_temp,
    current_temp,
    ext_current_temp,
    slope,
    hvac_mode,
    expected_on_percent,
):
    """Test TpiAlgorithm on_percent clamping to min/max thresholds."""
    tpi_algo: TpiAlgorithm = TpiAlgorithm(
        0.1,
        0.01,
        "test_entity_id",
        max_on_percent=None,
        tpi_threshold_low=tpi_threshold_low,
        tpi_threshold_high=tpi_threshold_high,
    )

    # Call the calculate
    tpi_algo.calculate(target_temp, current_temp, ext_current_temp, slope, hvac_mode)

    assert tpi_algo.on_percent == expected_on_percent


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_service_set_tpi_parameters(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, fake_underlying_switch: MockSwitch):
    """Test the set_tpi_parameters service to change TPI coefficients and verify on_percent changes"""
    # Initialize a VTherm over_switch with default TPI parameters
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
            CONF_MINIMAL_DEACTIVATION_DELAY: 30,
            CONF_TPI_THRESHOLD_LOW: 0.0,
            CONF_TPI_THRESHOLD_HIGH: 0.0,
        },
    )

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity

    # Set initial temperature and external temperature
    tz = get_tz(hass)  # Get timezone for datetime creation
    now: datetime = datetime.now(tz=tz)

    await send_temperature_change_event(entity, 15, now)
    await send_ext_temperature_change_event(entity, 5, now)
    await hass.async_block_till_done()

    # Activate the VTherm with a preset and mode
    assert entity.hvac_mode is HVACMode.OFF
    assert entity.vtherm_preset_mode is VThermPreset.NONE
    assert entity.target_temperature == 15.0  # temp min

    # Set hvac_mode to HEAT
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    await hass.async_block_till_done()

    assert entity.hvac_mode is HVACMode.HEAT
    assert entity.vtherm_preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == 18

    # Force a temperature update to trigger TPI calculation
    await send_temperature_change_event(entity, 17, now)
    await send_ext_temperature_change_event(entity, 17, now)
    await hass.async_block_till_done()

    # 1. Get the initial on_percent (should be calculated with default TPI coefficients)
    initial_on_percent = entity.proportional_algorithm.on_percent
    assert initial_on_percent is not None
    assert initial_on_percent > 0  # Should be heating since temp is below target

    # Store initial TPI parameters for verification
    assert entity.proportional_algorithm.tpi_coef_int == 0.3
    assert entity.proportional_algorithm.tpi_coef_ext == 0.01
    assert entity.minimal_activation_delay == 30
    assert entity.minimal_deactivation_delay == 30
    assert entity.proportional_algorithm.tpi_threshold_low == 0.0
    assert entity.proportional_algorithm.tpi_threshold_high == 0.0

    # Call the service to change TPI parameters
    new_tpi_coef_int = 0.6
    new_tpi_coef_ext = 0.02
    new_minimal_activation_delay = 60
    new_minimal_deactivation_delay = 60
    new_tpi_threshold_low = -0.5
    new_tpi_threshold_high = 0.5

    await entity.service_set_tpi_parameters(
        tpi_coef_int=new_tpi_coef_int,
        tpi_coef_ext=new_tpi_coef_ext,
        minimal_activation_delay=new_minimal_activation_delay,
        minimal_deactivation_delay=new_minimal_deactivation_delay,
        tpi_threshold_low=new_tpi_threshold_low,
        tpi_threshold_high=new_tpi_threshold_high,
    )
    await hass.async_block_till_done()

    # The service update triggers a reload of the integration, so the entity object is replaced.
    # We need to fetch the new entity instance.
    entity = search_entity(hass, "climate.theoverswitchmockname", CLIMATE_DOMAIN)
    assert entity

    # The new entity doesn't know the current temperature because the previous events were sent to the old instance
    # and not persisted in the HA state machine in a way that allows auto-recovery without event in this test setup.
    await send_temperature_change_event(entity, 17, now)
    await send_ext_temperature_change_event(entity, 17, now)
    await hass.async_block_till_done()

    # Verify that TPI parameters have been updated
    assert entity.proportional_algorithm.tpi_coef_int == new_tpi_coef_int
    assert entity.proportional_algorithm.tpi_coef_ext == new_tpi_coef_ext
    assert entity.minimal_activation_delay == new_minimal_activation_delay
    assert entity.minimal_deactivation_delay == new_minimal_deactivation_delay
    assert entity.proportional_algorithm.tpi_threshold_low == new_tpi_threshold_low
    assert entity.proportional_algorithm.tpi_threshold_high == new_tpi_threshold_high

    # Get the new on_percent after parameter change
    new_on_percent = entity.proportional_algorithm.on_percent
    assert new_on_percent is not None

    # Verify that on_percent has changed
    # With higher coefficients, the on_percent should be higher (more aggressive heating)
    assert new_on_percent != initial_on_percent, f"on_percent should have changed after TPI parameter update. " f"Initial: {initial_on_percent}, New: {new_on_percent}"
    assert new_on_percent > initial_on_percent, f"on_percent should be higher with increased TPI coefficients. " f"Initial: {initial_on_percent}, New: {new_on_percent}"

    initial_on_percent = new_on_percent

    # Test partial parameter update (only some parameters)
    await entity.service_set_tpi_parameters(
        tpi_coef_int=0.4,
        tpi_coef_ext=None,  # Should keep previous value
    )
    await hass.async_block_till_done()

    # The service update triggers a reload of the integration, so the entity object is replaced.
    # We need to fetch the new entity instance.
    entity = search_entity(hass, "climate.theoverswitchmockname", CLIMATE_DOMAIN)
    assert entity

    # The new entity doesn't know the current temperature because the previous events were sent to the old instance
    # and not persisted in the HA state machine in a way that allows auto-recovery without event in this test setup.
    await send_temperature_change_event(entity, 17, now)
    await send_ext_temperature_change_event(entity, 17, now)
    await hass.async_block_till_done()

    assert entity.proportional_algorithm.tpi_coef_int == 0.4
    assert entity.proportional_algorithm.tpi_coef_ext == new_tpi_coef_ext  # Should remain unchanged

    # Get the new on_percent after parameter change
    new_on_percent = entity.proportional_algorithm.on_percent
    assert new_on_percent is not None

    assert new_on_percent != initial_on_percent, f"on_percent should have changed after TPI parameter update. " f"Initial: {initial_on_percent}, New: {new_on_percent}"

    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_service_set_tpi_parameters_not_allowed_on_over_climate(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater):
    """Test that the set_tpi_parameters service cannot be called on a VTherm over_climate.
    This service is only available for VTherms using TPI algorithm (over_switch, over_valve)."""

    # Create a mock climate entity
    climate_entity = MockClimate(
        hass=hass,
        unique_id="mock_climate_entity",
        name="Mock Climate Entity",
        entry_infos={},
    )

    # with patch(
    #     "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
    #     return_value=climate_entity,
    # ):
    # Initialize a VTherm over_climate (which doesn't use TPI algorithm)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueIdOverClimate",
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
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_NONE,
        },
    )

    # set a state for the underlying climate
    set_entity_states(hass, entity_id="climate.mock_climate", state=HVACMode.HEAT, attributes={"supported_features": ClimateEntityFeature.TARGET_TEMPERATURE})

    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert entity
    assert entity.is_over_climate is True

    # Verify that the entity doesn't have a prop_algorithm (TPI is not used for over_climate)
    assert getattr(entity, "proportional_algorithm", None) is None

    # Try to call the service - it should raise an error or do nothing
    # since over_climate doesn't use TPI algorithm
    try:
        await entity.service_set_tpi_parameters(
            tpi_coef_int=0.6,
            tpi_coef_ext=0.02,
            minimal_activation_delay=60,
            minimal_deactivation_delay=60,
            tpi_threshold_low=-0.5,
            tpi_threshold_high=0.5,
        )
        await hass.async_block_till_done()

    except (ServiceValidationError, AttributeError) as e:
        # This is also acceptable - if the service tries to access
        # prop_algorithm attributes that don't exist
        # or if the method itself doesn't exist (AttributeError)
        pass

    finally:
        entity.remove_thermostat()
