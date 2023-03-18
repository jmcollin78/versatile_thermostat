""" Test the Window management """
from unittest.mock import patch
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

import logging

logging.getLogger().setLevel(logging.DEBUG)


async def test_bug_56(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that in over_climate mode there is no error when underlying climate is not available"""

    the_mock_underlying = MagicMockClimate()
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.find_underlying_climate",
        return_value=None,  # dont find the underlying climate
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
                CONF_SECURITY_DELAY_MIN: 5,
                CONF_SECURITY_MIN_ON_PERCENT: 0.3,
            },
        )

        entity: VersatileThermostat = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        # cause the underlying climate was not found
        assert entity.is_over_climate is True
        assert entity._underlying_climate is None

        # Should not failed
        entity.update_custom_attributes()

        # try to call _async_control_heating
        try:
            await entity._async_control_heating()
            # an exception should be send
            assert False
        except UnknownEntity:
            pass
        except Exception:  # pylint: disable=broad-exception-caught
            assert False

    # This time the underlying will be found
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.find_underlying_climate",
        return_value=the_mock_underlying,  # dont find the underlying climate
    ):
        # try to call _async_control_heating
        try:
            await entity._async_control_heating()
        except UnknownEntity:
            assert False
        except Exception:  # pylint: disable=broad-exception-caught
            assert False

        # Should not failed
        entity.update_custom_attributes()
