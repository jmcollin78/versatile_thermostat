""" Test the TPI algorithm """

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_tpi_calculation(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the TPI calculation"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            "name": "TheOverSwitchMockName",
            "thermostat_type": "thermostat_over_switch",
            "temperature_sensor_entity_id": "sensor.mock_temp_sensor",
            "external_temperature_sensor_entity_id": "sensor.mock_ext_temp_sensor",
            "cycle_min": 5,
            "temp_min": 15,
            "temp_max": 30,
            "use_window_feature": False,
            "use_motion_feature": False,
            "use_power_feature": False,
            "use_presence_feature": False,
            "heater_entity_id": "switch.mock_switch",
            "proportional_function": "tpi",
            "tpi_coef_int": 0.3,
            "tpi_coef_ext": 0.01,
            "minimal_activation_delay": 30,
            "security_delay_min": 5,
            "security_default_on_percent": 0.3,
        },
    )

    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    tpi_algo.calculate(15, 10, 7)
    assert tpi_algo.on_percent == 1
    assert tpi_algo.calculated_on_percent == 1
    assert tpi_algo.on_time_sec == 300
    assert tpi_algo.off_time_sec == 0

    tpi_algo.calculate(15, 14, 5)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 120
    assert tpi_algo.off_time_sec == 180

    tpi_algo.set_security(0.1)
    tpi_algo.calculate(15, 14, 5)
    assert tpi_algo.on_percent == 0.1
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 30  # >= minimal_activation_delay (=30)
    assert tpi_algo.off_time_sec == 270

    tpi_algo.unset_security()
    tpi_algo.calculate(15, 14, 5)
    assert tpi_algo.on_percent == 0.4
    assert tpi_algo.calculated_on_percent == 0.4
    assert tpi_algo.on_time_sec == 120
    assert tpi_algo.off_time_sec == 180

    # Test minimal activation delay
    tpi_algo.calculate(15, 14.7, 15)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300

    tpi_algo.set_security(0.09)
    tpi_algo.calculate(15, 14.7, 15)
    assert tpi_algo.on_percent == 0.09
    assert tpi_algo.calculated_on_percent == 0.09
    assert tpi_algo.on_time_sec == 0
    assert tpi_algo.off_time_sec == 300
