# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the auto fan mode of a over_climate thermostat """
from unittest.mock import patch, call

from datetime import datetime  # , timedelta

from homeassistant.core import HomeAssistant

# from homeassistant.components.climate import HVACAction, VThermHvacMode
from homeassistant.config_entries import ConfigEntryState

# from homeassistant.helpers.entity_component import EntityComponent
# from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

# from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_auto_fan_mode_turbo(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the init of an over climate thermostat with auto_fan_mode = Turbo which exists"""

    fan_modes = ["low", "medium", "high", "boost", "mute", "auto", "turbo"]

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
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
        },
    )

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mockUniqueId",
        name="MockClimateName",
        fan_modes=fan_modes,
    )

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        entity: ThermostatOverClimate = search_entity(
            hass, "climate.theoverclimatemockname", "climate"
        )

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.fan_modes == fan_modes
        assert entity._auto_fan_mode == "auto_fan_turbo"
        assert entity._auto_activated_fan_mode == "turbo"
        assert entity._auto_deactivated_fan_mode == "mute"


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_auto_fan_mode_not_turbo(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the init of an over climate thermostat with auto_fan_mode = Turbo which doesn't exists"""

    fan_modes = ["low", "medium", "high", "boost", "auto"]

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
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
        },
    )

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mockUniqueId",
        name="MockClimateName",
        fan_modes=fan_modes,
    )

    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        entity: ThermostatOverClimate = search_entity(
            hass, "climate.theoverclimatemockname", "climate"
        )

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.fan_modes == fan_modes
        assert entity._auto_fan_mode == "auto_fan_turbo"
        # Turbo doesn't exists -> fallback to high
        assert entity._auto_activated_fan_mode == "high"
        # Mute doesn't exists -> fallback to auto
        assert entity._auto_deactivated_fan_mode == "auto"


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_auto_fan_mode_turbo_activation(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the init of an over climate thermostat with auto_fan_mode = Turbo which exists"""

    fan_modes = ["low", "medium", "high", "boost", "mute", "auto", "turbo"]

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
            "eco_ac_temp": 25,
            "comfort_ac_temp": 23,
            "boost_ac_temp": 21,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_CLIMATE: "climate.mock_climate",
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_TURBO,
            CONF_AC_MODE: True,
        },
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    fake_underlying_climate = MockClimate(
        hass=hass,
        unique_id="mockUniqueId",
        name="MockClimateName",
        fan_modes=fan_modes,
    )

    # 1. Init fan mode
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
        # entry.add_to_hass(hass)
        # await hass.config_entries.async_setup(entry.entry_id)
        # assert entry.state is ConfigEntryState.LOADED
        #
        # entity: ThermostatOverClimate = search_entity(
        #    hass, "climate.theoverclimatemockname", "climate"
        # )

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.fan_modes == fan_modes
        assert entity.fan_mode is None
        assert entity._auto_fan_mode == "auto_fan_turbo"
        assert entity._auto_activated_fan_mode == "turbo"
        assert entity._auto_deactivated_fan_mode == "mute"

    # 2. Turn on and set temperature cold
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        # Force preset mode
        await entity.async_set_hvac_mode(VThermHvacMode.HEAT)
        assert entity.hvac_mode == VThermHvacMode.HEAT
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 18

        # Change the current temperature to 16 which is 2° under
        await send_temperature_change_event(entity, 16, now, True)
        fake_underlying_climate.set_fan_mode("turbo")

        assert mock_send_fan_mode.call_count == 1
        mock_send_fan_mode.assert_has_calls([call.set_fan_mode("turbo")])

        assert entity.fan_mode == "turbo"

    # 3. Set another low temperature
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        fake_underlying_climate.set_fan_mode("turbo")

        # Change the current temperature to 17 which is 1° under
        await send_temperature_change_event(entity, 15, now, True)

        # Nothing is send cause we are already in turbo fan mode
        assert mock_send_fan_mode.call_count == 0

        assert entity.fan_mode == "turbo"

    # 4. Set temperature not so cold
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        # Change the current temperature to 17 which is 1° under
        await send_temperature_change_event(entity, 17, now, True)
        fake_underlying_climate.set_fan_mode("mute")

        assert mock_send_fan_mode.call_count == 1
        mock_send_fan_mode.assert_has_calls([call.set_fan_mode("mute")])

        assert entity.fan_mode == "mute"

    # 5. Set temperature not so cold another time
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        fake_underlying_climate.set_fan_mode("mute")

        # Change the current temperature to 17 which is 1° under
        await send_temperature_change_event(entity, 17.1, now, True)

        assert mock_send_fan_mode.call_count == 0
        assert entity.fan_mode == "mute"

    # 6. Set temperature very high above the target
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        fake_underlying_climate.set_fan_mode("mute")

        # Change the current temperature to 17 which is 1° under
        await send_temperature_change_event(entity, 21, now, True)

        assert mock_send_fan_mode.call_count == 0
        assert entity.fan_mode == "mute"

    # 7. In AC mode, set temperature very high under the target
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        await entity.async_set_hvac_mode(VThermHvacMode.COOL)
        assert entity.hvac_mode == VThermHvacMode.COOL
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 23

        assert entity.current_temperature == 21

        fake_underlying_climate.set_fan_mode("mute")

        # Change the current temperature to 17 which is 1° under
        await send_temperature_change_event(entity, 20, now, True)

        assert mock_send_fan_mode.call_count == 0
        assert entity.fan_mode == "mute"

    # 8. In AC mode, set temperature not so high above the target
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        assert entity.target_temperature == 23
        await send_temperature_change_event(entity, 24, now, True)
        assert entity.current_temperature == 24
        fake_underlying_climate.set_fan_mode("mute")

        assert mock_send_fan_mode.call_count == 0
        assert entity.fan_mode == "mute"

    # 8. In AC mode, set temperature high above the target
    with patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
    ) as mock_send_fan_mode:
        assert entity.target_temperature == 23
        await send_temperature_change_event(entity, 25.1, now, True)
        assert entity.current_temperature == 25.1
        fake_underlying_climate.set_fan_mode("turbo")

        assert mock_send_fan_mode.call_count == 1
        mock_send_fan_mode.assert_has_calls([call.set_fan_mode("turbo")])
        assert entity.fan_mode == "turbo"
