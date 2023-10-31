# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the normal start of a Thermostat """
from unittest.mock import patch #, call
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntryState

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

# from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import ThermostatOverClimate

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_regulation(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """Test the regulation of an over climate thermostat"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # This is include a medium regulation
        data=PARTIAL_CLIMATE_CONFIG,
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {})

    # Creates the regulated VTherm over climate
    # change temperature so that the heating will start
    event_timestamp = now - timedelta(minutes=10)

    with patch(
        "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        def find_my_entity(entity_id) -> ClimateEntity:
            """Find my new entity"""
            component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
            for entity in component.entities:
                if entity.entity_id == entity_id:
                    return entity

        entity:ThermostatOverClimate = find_my_entity("climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.is_regulated is True
        assert entity.hvac_action is HVACAction.OFF
        assert entity.hvac_mode is HVACMode.OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            PRESET_NONE,
            PRESET_ECO,
            PRESET_COMFORT,
            PRESET_BOOST,
        ]
        assert entity.preset_mode is PRESET_NONE

        # Activate the heating by changing HVACMode and temperature
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.hvac_action == HVACAction.OFF

        assert entity.regulated_target_temp == entity.min_temp

        await send_temperature_change_event(entity, 15, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        # set manual target temp (at now - 7) -> the regulation should occurs
        event_timestamp = now - timedelta(minutes=7)
        with patch(
            "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
        ):
            await entity.async_set_temperature(temperature=18)

            fake_underlying_climate.set_hvac_action(HVACAction.HEATING) # simulate under heating
            assert entity.hvac_action == HVACAction.HEATING
            assert entity.preset_mode == PRESET_NONE # Manual mode

            # the regulated temperature should be greater
            assert entity.regulated_target_temp > entity.target_temperature
            # In medium we could go up to +3 degre
            # normally the calcul gives 18 + 2.2 but we round the result to the nearest 0.5 which is 2.0
            assert entity.regulated_target_temp == 18+2.0
            assert entity.hvac_action == HVACAction.HEATING

        # change temperature so that the regulated temperature should slow down
        event_timestamp = now - timedelta(minutes=5)
        with patch(
            "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
        ):
            await send_temperature_change_event(entity, 22, event_timestamp)
            await send_ext_temperature_change_event(entity, 19, event_timestamp)

            # the regulated temperature should be under
            assert entity.regulated_target_temp < entity.target_temperature
            assert entity.regulated_target_temp == 18-0.5 # normally 0.6 but round_to_nearest gives 0.5

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_regulation_ac_mode(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """Test the regulation of an over climate thermostat"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # This is include a medium regulation
        data=PARTIAL_CLIMATE_AC_CONFIG,
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {})

    # Creates the regulated VTherm over climate
    # change temperature so that the heating will start
    event_timestamp = now - timedelta(minutes=10)

    with patch(
        "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        def find_my_entity(entity_id) -> ClimateEntity:
            """Find my new entity"""
            component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
            for entity in component.entities:
                if entity.entity_id == entity_id:
                    return entity

        entity:ThermostatOverClimate = find_my_entity("climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.is_regulated is True
        assert entity.hvac_action is HVACAction.OFF
        assert entity.hvac_mode is HVACMode.OFF
        assert entity.target_temperature == entity.max_temp
        assert entity.preset_modes == [
            PRESET_NONE,
            PRESET_ECO,
            PRESET_COMFORT,
            PRESET_BOOST,
        ]
        assert entity.preset_mode is PRESET_NONE

        # Activate the heating by changing HVACMode and temperature
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.hvac_action == HVACAction.OFF

        # change temperature so that the heating will start
        await send_temperature_change_event(entity, 30, event_timestamp)
        await send_ext_temperature_change_event(entity, 35, event_timestamp)


        # set manual target temp
        event_timestamp = now - timedelta(minutes=7)
        with patch(
                "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
        ):
            await entity.async_set_temperature(temperature=25)

            fake_underlying_climate.set_hvac_action(HVACAction.COOLING) # simulate under heating
            assert entity.hvac_action == HVACAction.COOLING
            assert entity.preset_mode == PRESET_NONE # Manual mode

            # the regulated temperature should be lower
            assert entity.regulated_target_temp < entity.target_temperature
            assert entity.regulated_target_temp == 25-3 # In medium we could go up to -3 degre
            assert entity.hvac_action == HVACAction.COOLING

        # change temperature so that the regulated temperature should slow down
        event_timestamp = now - timedelta(minutes=5)
        with patch(
                "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
        ):
            await send_temperature_change_event(entity, 26, event_timestamp)
            await send_ext_temperature_change_event(entity, 35, event_timestamp)

            # the regulated temperature should be under
            assert entity.regulated_target_temp < entity.target_temperature
            assert entity.regulated_target_temp == 25-2.5 # +2.3 without round_to_nearest

            # change temperature so that the regulated temperature should slow down
        event_timestamp = now - timedelta(minutes=3)
        with patch(
                "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
        ):
            await send_temperature_change_event(entity, 20, event_timestamp)
            await send_ext_temperature_change_event(entity, 25, event_timestamp)

            # the regulated temperature should be greater
            assert entity.regulated_target_temp > entity.target_temperature
            assert entity.regulated_target_temp == 25+0.5 # +0.4 without round_to_nearest

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_regulation_limitations(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """Test the limitations of the regulation of an over climate thermostat:
       1. test the period_min parameter: do not send regulation event too frequently
       2. test the dtemp parameter: do not send regulation event if offset temp is lower than dtemp
    """

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # This is include a medium regulation, dtemp=0.5, period_min=2
        data=PARTIAL_CLIMATE_CONFIG,
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {})

    # Creates the regulated VTherm over climate at t-20
    # change temperature so that the heating will start
    event_timestamp = now - timedelta(minutes=20)

    with patch(
        "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        def find_my_entity(entity_id) -> ClimateEntity:
            """Find my new entity"""
            component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
            for entity in component.entities:
                if entity.entity_id == entity_id:
                    return entity

        entity:ThermostatOverClimate = find_my_entity("climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.is_regulated is True

        # Activate the heating by changing HVACMode and temperature
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode is HVACMode.HEAT

        # it is cold today
        await send_temperature_change_event(entity, 15, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        # set manual target temp (at now - 19) -> the regulation should be ignored because too early
        event_timestamp = now - timedelta(minutes=19)
        with patch(
            "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
        ):
            await entity.async_set_temperature(temperature=18)

            fake_underlying_climate.set_hvac_action(HVACAction.HEATING) # simulate under heating
            assert entity.hvac_action == HVACAction.HEATING

            # the regulated temperature will change because when we set temp manually it is forced
            assert entity.regulated_target_temp == 20.

        # set manual target temp (at now - 18) -> the regulation should be taken into account
        event_timestamp = now - timedelta(minutes=18)
        with patch(
            "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
        ):
            await entity.async_set_temperature(temperature=17)
            assert entity.regulated_target_temp > entity.target_temperature
            assert entity.regulated_target_temp == 18+0.5 # In medium we could go up to +3 degre. 0.7 without round_to_nearest
            old_regulated_temp = entity.regulated_target_temp

        # change temperature so that dtemp < 0.5 and time is > period_min (+ 3min)
        event_timestamp = now - timedelta(minutes=15)
        with patch(
            "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
        ):
            await send_temperature_change_event(entity, 16, event_timestamp)
            await send_ext_temperature_change_event(entity, 10, event_timestamp)

            # the regulated temperature should be under
            assert entity.regulated_target_temp == old_regulated_temp

        # change temperature so that dtemp > 0.5 and time is > period_min (+ 3min)
        event_timestamp = now - timedelta(minutes=12)
        with patch(
            "custom_components.versatile_thermostat.commons.NowClass.get_now", return_value=event_timestamp
        ):
            await send_temperature_change_event(entity, 18, event_timestamp)
            await send_ext_temperature_change_event(entity, 12, event_timestamp)

            # the regulated should have been done
            assert entity.regulated_target_temp != old_regulated_temp
            assert entity.regulated_target_temp > entity.target_temperature
            assert entity.regulated_target_temp == 17 + 0.5 # 0.7 without round_to_nearest