# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the normal start of a Thermostat """
from unittest.mock import patch, call
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntryState

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

# from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_regulation(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
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
        "custom_components.versatile_thermostat.const.NowClass.get_now",
        return_value=event_timestamp,
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.is_regulated is True
        assert entity.auto_regulation_use_device_temp is False
        assert entity.hvac_mode is HVACMode.OFF
        assert entity.hvac_action is HVACAction.OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            PRESET_NONE,
            PRESET_FROST_PROTECTION,
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
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ):
            await entity.async_set_temperature(temperature=18)

            fake_underlying_climate.set_hvac_action(
                HVACAction.HEATING
            )  # simulate under heating
            assert entity.hvac_action == HVACAction.HEATING
            assert entity.preset_mode == PRESET_NONE  # Manual mode

            # the regulated temperature should be greater
            assert entity.regulated_target_temp > entity.target_temperature
            # In medium we could go up to +3 degre
            # normally the calcul gives 18 + 2.2 but we round the result to the nearest 0.5 which is 2.0
            assert entity.regulated_target_temp == 18 + 1.5
            assert entity.hvac_action == HVACAction.HEATING

        # change temperature so that the regulated temperature should slow down
        event_timestamp = now - timedelta(minutes=5)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ):
            await send_temperature_change_event(entity, 23, event_timestamp)
            await send_ext_temperature_change_event(entity, 19, event_timestamp)

            # the regulated temperature should be under
            assert entity.regulated_target_temp < entity.target_temperature
            assert entity.regulated_target_temp == 18 - 2.5


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_regulation_ac_mode(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
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
        "custom_components.versatile_thermostat.const.NowClass.get_now",
        return_value=event_timestamp,
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

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
            PRESET_FROST_PROTECTION,
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
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ):
            await entity.async_set_temperature(temperature=25)

            fake_underlying_climate.set_hvac_action(
                HVACAction.COOLING
            )  # simulate under heating
            assert entity.hvac_action == HVACAction.COOLING
            assert entity.preset_mode == PRESET_NONE  # Manual mode

            # the regulated temperature should be lower
            assert entity.regulated_target_temp < entity.target_temperature
            assert (
                entity.regulated_target_temp == 25 - 2.5
            )  # In medium we could go up to -3 degre
            assert entity.hvac_action == HVACAction.COOLING

        # change temperature so that the regulated temperature should slow down
        event_timestamp = now - timedelta(minutes=5)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ):
            await send_temperature_change_event(entity, 26, event_timestamp)
            await send_ext_temperature_change_event(entity, 35, event_timestamp)

            # the regulated temperature should be under
            assert entity.regulated_target_temp < entity.target_temperature
            assert (
                entity.regulated_target_temp == 25 - 1
            )  # +2.3 without round_to_nearest

            # change temperature so that the regulated temperature should slow down
        event_timestamp = now - timedelta(minutes=3)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ):
            await send_temperature_change_event(entity, 18, event_timestamp)
            await send_ext_temperature_change_event(entity, 25, event_timestamp)

            # the regulated temperature should be greater
            assert entity.regulated_target_temp > entity.target_temperature
            assert (
                entity.regulated_target_temp == 25 + 3
            )  # +0.4 without round_to_nearest


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_regulation_limitations(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
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
        "custom_components.versatile_thermostat.const.NowClass.get_now",
        return_value=event_timestamp,
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

        entity: ThermostatOverClimate = find_my_entity("climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.is_regulated is True

        entity._set_now(event_timestamp)
        # Will initialize the _last_regulation_change
        # Activate the heating by changing HVACMode and temperature
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode is HVACMode.HEAT
        await entity.async_set_temperature(temperature=17)

        # it is cold today
        await send_temperature_change_event(entity, 15, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        # 1. set manual target temp (at now - 19) -> the regulation should be ignored because too early
        event_timestamp = now - timedelta(minutes=19)
        entity._set_now(event_timestamp)
        await entity.async_set_temperature(temperature=18)

        fake_underlying_climate.set_hvac_action(
            HVACAction.HEATING
        )  # simulate under heating
        assert entity.hvac_action == HVACAction.HEATING

        # the regulated temperature will not change because when we set temp manually it is forced
        assert entity.regulated_target_temp == 19.5

        # 2. set manual target temp (at now - 18) -> the regulation should be taken into account
        event_timestamp = now - timedelta(minutes=18)
        entity._set_now(event_timestamp)

        # Set_target_temperature force the update
        await entity.async_set_temperature(temperature=17)
        assert entity.regulated_target_temp > entity.target_temperature
        assert entity.regulated_target_temp == 18 + 0.5  # In strong we could go up to +3 degre. 0.7 without round_to_nearest
        old_regulated_temp = entity.regulated_target_temp

        # 3. change temperature so that dtemp < 0.5 and time is > period_min (+ 3min)
        event_timestamp = now - timedelta(minutes=15)
        entity._set_now(event_timestamp)
        await send_temperature_change_event(entity, 16, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        # the regulated temperature should be under
        assert entity.regulated_target_temp <= old_regulated_temp

        # 4. change temperature so that dtemp > 0.5 and time is > period_min (+ 3min)
        event_timestamp = now - timedelta(minutes=12)
        entity._set_now(event_timestamp)
        await send_temperature_change_event(entity, 15, event_timestamp)
        await send_ext_temperature_change_event(entity, 12, event_timestamp)

        # the regulated should have been done
        assert entity.regulated_target_temp != old_regulated_temp
        assert entity.regulated_target_temp >= entity.target_temperature
        assert entity.regulated_target_temp == 17 + 2  # 0.7 without round_to_nearest


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
# Disable this test which is not working when run in // of others.
# I couldn't find out why
@pytest.mark.skip
async def test_over_climate_regulation_use_device_temp(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the regulation of an over climate thermostat"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # This is include a medium regulation
        data=PARTIAL_CLIMATE_CONFIG_USE_DEVICE_TEMP | {CONF_AUTO_REGULATION_DTEMP: 0.5},
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {})

    assert fake_underlying_climate.current_temperature == 15

    # Creates the regulated VTherm over climate
    # change temperature so that the heating will start
    event_timestamp = now - timedelta(minutes=10)

    with patch(
        "custom_components.versatile_thermostat.const.NowClass.get_now",
        return_value=event_timestamp,
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entity: ThermostatOverClimate = await create_thermostat(
            hass, entry, "climate.theoverclimatemockname"
        )
        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.is_regulated is True
        assert entity.auto_regulation_use_device_temp is True

        # 1.  Activate the heating by changing HVACMode and temperature
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.regulated_target_temp == entity.min_temp

        await send_temperature_change_event(entity, 18, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        # 2. set manual target temp (at now - 7) -> no regulation should occurs
        # room temp is 18
        # target is 16
        # internal heater temp is 15
        fake_underlying_climate.set_current_temperature(15)
        event_timestamp = now - timedelta(minutes=7)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
            await entity.async_set_temperature(temperature=16)

            fake_underlying_climate.set_hvac_action(
                HVACAction.HEATING
            )  # simulate under heating
            assert entity.hvac_action == HVACAction.HEATING
            assert entity.preset_mode == PRESET_NONE  # Manual mode

            # the regulated temperature should be higher
            assert entity.regulated_target_temp < entity.target_temperature
            # The calcul is the following: 16 + (16 - 18) x 0.4 (strong) + 0 x ki - 1 (device offset)
            assert (
                entity.regulated_target_temp == 15
            )  # round(16 + (16 - 18) * 0.4 + 0 * 0.08)
            assert entity.hvac_action == HVACAction.HEATING

            mock_service_call.assert_has_calls(
                [
                    call.service_call(
                        "climate",
                        "set_temperature",
                        {
                            "entity_id": "climate.mock_climate",
                            # because device offset is -3 but not used because target is reach
                            "temperature": 15.0,
                            "target_temp_high": 30,
                            "target_temp_low": 15,
                        },
                    ),
                ]
            )

        # 3. change temperature so that the regulated temperature should slow down
        # HVACMODE.HEAT
        # room temp is 15
        # target is 18
        # internal heater temp is 20
        fake_underlying_climate.set_current_temperature(20.1)
        await entity.async_set_temperature(temperature=18)
        await send_ext_temperature_change_event(entity, 9, event_timestamp)

        event_timestamp = now - timedelta(minutes=5)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
            await send_temperature_change_event(entity, 15, event_timestamp)

            # the regulated temperature should be under (device offset is -2)
            assert entity.regulated_target_temp > entity.target_temperature
            assert entity.regulated_target_temp == 19.5  # round(18 + 1.4, 0.5)

            mock_service_call.assert_has_calls(
                [
                    call.service_call(
                        "climate",
                        "set_temperature",
                        {
                            "entity_id": "climate.mock_climate",
                            "temperature": 24.5,  # round(19.5 + 5, 0.5)
                            "target_temp_high": 30,
                            "target_temp_low": 15,
                        },
                    ),
                ]
            )

        # 4. In cool mode
        # room temp is 25
        # target is 23
        # internal heater temp is 27
        await entity.async_set_hvac_mode(HVACMode.COOL)
        await entity.async_set_temperature(temperature=23)
        fake_underlying_climate.set_current_temperature(26.9)
        await send_ext_temperature_change_event(entity, 30, event_timestamp)

        event_timestamp = now - timedelta(minutes=3)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
            await send_temperature_change_event(entity, 25, event_timestamp)

            # the regulated temperature should be upper (device offset is +1.9)
            assert entity.regulated_target_temp < entity.target_temperature
            assert entity.regulated_target_temp == 22.5

            mock_service_call.assert_has_calls(
                [
                    call.service_call(
                        "climate",
                        "set_temperature",
                        {
                            "entity_id": "climate.mock_climate",
                            "temperature": 24.5,  # round(22.5 + 1.9° of offset)
                            "target_temp_high": 30,
                            "target_temp_low": 15,
                        },
                    ),
                ]
            )

@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_regulation_dtemp_null(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Test the regulation of an over climate thermostat with no Dtemp limitation"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # This is include a medium regulation
        data=PARTIAL_CLIMATE_AC_CONFIG | {CONF_AUTO_REGULATION_DTEMP: 0, CONF_STEP_TEMPERATURE: 0.1},
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {})

    # Creates the regulated VTherm over climate
    # change temperature so that the heating will start
    event_timestamp = now - timedelta(minutes=20)

    with patch(
        "custom_components.versatile_thermostat.const.NowClass.get_now",
        return_value=event_timestamp,
    ), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ):
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.is_regulated is True

        # Activate the heating by changing HVACMode and temperature
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.hvac_action == HVACAction.OFF

        # change temperature so that the heating will start
        await send_temperature_change_event(entity, 15, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        # set manual target temp
        event_timestamp = now - timedelta(minutes=17)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ):
            await entity.async_set_temperature(temperature=20)

            fake_underlying_climate.set_hvac_action(
                HVACAction.HEATING
            )  # simulate under cooling
            assert entity.hvac_action == HVACAction.HEATING
            assert entity.preset_mode == PRESET_NONE  # Manual mode

            # the regulated temperature should be lower
            assert entity.regulated_target_temp > entity.target_temperature
            assert entity.regulated_target_temp == 20 + 3.6  # In Strong we could go up to +5 degre
            assert entity.hvac_action == HVACAction.HEATING

        # change temperature so that the regulated temperature should slow down
        event_timestamp = now - timedelta(minutes=15)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ):
            await send_temperature_change_event(entity, 19, event_timestamp)
            await send_ext_temperature_change_event(entity, 10, event_timestamp)

            # the regulated temperature should be greater
            assert entity.regulated_target_temp > entity.target_temperature
            assert entity.regulated_target_temp == 20 + 2.1

            # change temperature so that the regulated temperature should slow down
        event_timestamp = now - timedelta(minutes=13)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ):
            await send_temperature_change_event(entity, 20, event_timestamp)
            await send_ext_temperature_change_event(entity, 10, event_timestamp)

            # the regulated temperature should be greater
            assert entity.regulated_target_temp > entity.target_temperature
            assert entity.regulated_target_temp == 20 + 1.7

        old_regulated_temp = entity.regulated_target_temp
        # Test if a small temperature change is taken into account : change temperature so that dtemp < 0.5 and time is > period_min (+ 3min)
        event_timestamp = now - timedelta(minutes=10)
        with patch(
            "custom_components.versatile_thermostat.const.NowClass.get_now",
            return_value=event_timestamp,
        ):
            await send_temperature_change_event(entity, 19.6, event_timestamp)
            await send_ext_temperature_change_event(entity, 10, event_timestamp)

            # the regulated temperature should be greater. This does not work if dtemp is not null
            assert entity.regulated_target_temp > old_regulated_temp
