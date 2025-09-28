""" Test the TPI algorithm """

from homeassistant.components.climate import HVACMode

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.prop_algorithm import (
    PropAlgorithm,
    PROPORTIONAL_FUNCTION_TPI,
)
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
            CONF_HEATER: "switch.mock_switch",
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

    tpi_algo: PropAlgorithm = entity._prop_algorithm  # pylint: disable=protected-access
    assert tpi_algo

    tpi_algo.calculate(15, 10, 7, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 1
    assert tpi_algo.calculated_on_percent == 1
    assert tpi_algo.on_time_sec == 300
    assert tpi_algo.off_time_sec == 0
    assert entity.power_manager.mean_cycle_power is None  # no device power configured

    tpi_algo.calculate(15, 14, 5, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 120
    assert tpi_algo.off_time_sec == 180

    tpi_algo.set_safety(0.1)
    tpi_algo.calculate(15, 14, 5, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.1
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 30  # >= minimal_activation_delay (=30)
    assert tpi_algo.off_time_sec == 270

    tpi_algo.unset_safety()
    tpi_algo.calculate(15, 14, 5, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 120
    assert tpi_algo.off_time_sec == 180

    # Test minimal activation delay
    tpi_algo.calculate(15, 14.7, 15, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300

    tpi_algo.set_safety(0.09)
    tpi_algo.calculate(15, 14.7, 15, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300

    tpi_algo.unset_safety()
    tpi_algo.calculate(25, 30, 35, 0, HVACMode.COOL)
    assert tpi_algo.on_percent == 1
    assert tpi_algo.calculated_on_percent == 1
    assert tpi_algo.on_time_sec == 300
    assert tpi_algo.off_time_sec == 0
    assert entity.power_manager.mean_cycle_power is None  # no device power configured

    tpi_algo.set_safety(0.09)
    tpi_algo.calculate(25, 30, 35, 0, HVACMode.COOL)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 1
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300
    assert entity.power_manager.mean_cycle_power is None  # no device power configured

    tpi_algo.unset_safety()
    # The calculated values for HVACMode.OFF are the same as for HVACMode.HEAT.
    tpi_algo.calculate(15, 10, 7, 0, HVACMode.OFF)
    assert tpi_algo.on_percent == 1
    assert tpi_algo.calculated_on_percent == 1
    assert tpi_algo.on_time_sec == 300
    assert tpi_algo.off_time_sec == 0

    # If target_temp or current_temp are None, _calculated_on_percent is set to 0.
    tpi_algo.calculate(15, None, 7, 0, HVACMode.OFF)
    assert tpi_algo.on_percent == 0
    assert tpi_algo.calculated_on_percent == 0
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300

    """
    Test the max_on_percent clamping calculations
    """
    tpi_algo._max_on_percent = 0.8

    # no clamping
    tpi_algo.calculate(15, 14.7, 15, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300

    # no clamping  (calculated_on_percent = 0.79)
    tpi_algo.calculate(15, 12.5, 11, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.79
    assert tpi_algo.calculated_on_percent == 0.79
    assert tpi_algo.on_time_sec == 237
    assert tpi_algo.off_time_sec == 63

    # clamping to 80%  (calculated_on_percent = 1)
    tpi_algo.calculate(15, 10, 7, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.8 # should be clamped to 80%
    assert tpi_algo.calculated_on_percent == 1 # calculated percentage should not be affected by clamping
    assert tpi_algo.on_time_sec == 240 # capped at 80%
    assert tpi_algo.off_time_sec == 60

    # clamping to 80%  (calculated_on_percent = 0.81)
    tpi_algo.calculate(15, 12.5, 9, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.80 # should be clamped to 80%
    assert tpi_algo.calculated_on_percent == 0.81 # calculated percentage should not be affected by clamping
    assert tpi_algo.on_time_sec == 240 # capped at 80%
    assert tpi_algo.off_time_sec == 60


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
            CONF_HEATER: "switch.mock_switch",
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

    tpi_algo: PropAlgorithm = entity._prop_algorithm  # pylint: disable=protected-access
    assert tpi_algo

    # off_time is less than minimal_deactivation_delay
    tpi_algo.calculate(9, 6, 10, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.89
    assert tpi_algo.calculated_on_percent == 0.89
    assert tpi_algo.on_time_sec == 300
    assert tpi_algo.off_time_sec == 0

    # off_time is less than minimal_deactivation_delay
    tpi_algo.calculate(6, 0, 104, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.82
    assert tpi_algo.calculated_on_percent == 0.82
    assert tpi_algo.on_time_sec == 300
    assert tpi_algo.off_time_sec == 0

    # off_time is exactly minimal_deactivation_delay
    tpi_algo.calculate(10, 8, -10, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.8
    assert tpi_algo.calculated_on_percent == 0.8
    assert tpi_algo.on_time_sec == 240
    assert tpi_algo.off_time_sec == 60  # Equal to minimal_deactivation_delay

    # off_time is greater than minimal_deactivation_delay
    tpi_algo.calculate(10, 9, 0, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 120
    assert tpi_algo.off_time_sec == 180

    # with safety mode
    tpi_algo.set_safety(0.2)
    tpi_algo.calculate(10, 8, -10, 0, HVACMode.HEAT)
    assert tpi_algo.on_percent == 0.2
    assert tpi_algo.calculated_on_percent == 0.8
    assert tpi_algo.on_time_sec == 60
    assert tpi_algo.off_time_sec == 240
    tpi_algo.unset_safety()

    # with cooling mode
    tpi_algo.calculate(10, 10, 90, 0, HVACMode.COOL)
    assert tpi_algo.on_percent == 0.8
    assert tpi_algo.calculated_on_percent == 0.8
    assert tpi_algo.on_time_sec == 240
    assert tpi_algo.off_time_sec == 60


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_wrong_tpi_parameters(
    hass: HomeAssistant, skip_hass_states_is_state: None
):  # pylint: disable=unused-argument
    """Test the wrong TPI parameters"""

    # Nominal case
    try:
        algo = PropAlgorithm(
            PROPORTIONAL_FUNCTION_TPI,
            0.6,
            0.01,
            5,
            1,
            1,
            "entity_id",
        )
        # We should not be there
        assert True
    except TypeError as e:
        # the normal case
        assert False

    # Test TPI function
    try:
        algo = PropAlgorithm(
            "WRONG",
            1,
            0,
            2,
            3,
            3,
            "entity_id",
        )
        # We should not be there
        assert False
    except TypeError as e:
        # the normal case
        pass

    # Test coef_int
    try:
        algo = PropAlgorithm(
            PROPORTIONAL_FUNCTION_TPI,
            None,
            0,
            2,
            3,
            3,
            "entity_id",
        )
        # We should not be there
        assert False
    except TypeError as e:
        # the normal case
        pass

    # Test coef_ext
    try:
        algo = PropAlgorithm(
            PROPORTIONAL_FUNCTION_TPI,
            0.6,
            None,
            2,
            3,
            3,
            "entity_id",
        )
        # We should not be there
        assert False
    except TypeError as e:
        # the normal case
        pass

    # Test cycle_min
    try:
        algo = PropAlgorithm(
            PROPORTIONAL_FUNCTION_TPI,
            0.6,
            0.00001,
            None,
            3,
            3,
            "entity_id",
        )
        # We should not be there
        assert False
    except TypeError as e:
        # the normal case
        pass

    # Test minimal_activation_delay
    try:
        algo = PropAlgorithm(
            PROPORTIONAL_FUNCTION_TPI,
            0.6,
            0.00001,
            0,
            None,
            "entity_id",
        )
        # We should not be there
        assert False
    except TypeError as e:
        # the normal case
        pass

    # Test minimal_activation_delay
    try:
        algo = PropAlgorithm(
            PROPORTIONAL_FUNCTION_TPI,
            0.6,
            0.00001,
            0,
            3,
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
        algo = PropAlgorithm(
            PROPORTIONAL_FUNCTION_TPI,
            0.6,
            0.00001,
            0,
            12,
            12,
            None,
        )
        # We should not be there
        assert False
    except TypeError as e:
        # the normal case
        pass
