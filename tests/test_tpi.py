""" Test the TPI algorithm """

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
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
            CONF_SECURITY_DELAY_MIN: 5,
            CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            # CONF_DEVICE_POWER: 100,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm   # pylint: disable=protected-access
    assert tpi_algo

    tpi_algo.calculate(15, 10, 7)
    assert tpi_algo.on_percent == 1
    assert tpi_algo.calculated_on_percent == 1
    assert tpi_algo.on_time_sec == 300
    assert tpi_algo.off_time_sec == 0
    assert entity.mean_cycle_power is None  # no device power configured

    tpi_algo.calculate(15, 14, 5, False)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 120
    assert tpi_algo.off_time_sec == 180

    tpi_algo.set_security(0.1)
    tpi_algo.calculate(15, 14, 5, False)
    assert tpi_algo.on_percent == 0.1
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 30  # >= minimal_activation_delay (=30)
    assert tpi_algo.off_time_sec == 270

    tpi_algo.unset_security()
    tpi_algo.calculate(15, 14, 5, False)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 120
    assert tpi_algo.off_time_sec == 180

    # Test minimal activation delay
    tpi_algo.calculate(15, 14.7, 15, False)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300

    tpi_algo.set_security(0.09)
    tpi_algo.calculate(15, 14.7, 15, False)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300

    tpi_algo.unset_security()
    tpi_algo.calculate(25, 30, 35, True)
    assert tpi_algo.on_percent == 1
    assert tpi_algo.calculated_on_percent == 1
    assert tpi_algo.on_time_sec == 300
    assert tpi_algo.off_time_sec == 0
    assert entity.mean_cycle_power is None  # no device power configured

    tpi_algo.set_security(0.09)
    tpi_algo.calculate(25, 30, 35, True)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 1
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300
    assert entity.mean_cycle_power is None  # no device power configured
