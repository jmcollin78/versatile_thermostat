# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the normal start of a Thermostat """
from unittest.mock import patch, call, ANY
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACAction
from homeassistant.config_entries import ConfigEntryState

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

# from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_over_climate_regulation(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event, fake_underlying_climate):
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

    # Creates the regulated VTherm over climate
    # change temperature so that the heating will start
    event_timestamp = now - timedelta(minutes=10)

    with patch(
        "custom_components.versatile_thermostat.const.NowClass.get_now",
        return_value=event_timestamp,
    ):
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.is_regulated is True
        assert entity.auto_regulation_use_device_temp is False
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.hvac_action is HVACAction.OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            VThermPreset.NONE,
            VThermPreset.FROST,
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
        ]
        assert entity.preset_mode is VThermPreset.NONE

        await wait_for_local_condition(lambda: entity.is_ready is True)

        # Activate the heating by changing VThermHvacMode and temperature
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
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
            await hass.async_block_till_done()

            entity.calculate_hvac_action()
            assert entity.hvac_action == HVACAction.HEATING
            assert entity.preset_mode == VThermPreset.NONE  # Manual mode

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
            await hass.async_block_till_done()

            # the regulated temperature should be under
            assert entity.regulated_target_temp < entity.target_temperature
            assert entity.regulated_target_temp == 18 - 2.0

    entity.remove_thermostat()


async def test_over_climate_regulation_ac_mode(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
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

    # change temperature so that the heating will start
    now = now + timedelta(minutes=10)

    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.is_regulated is True

    await wait_for_local_condition(lambda: entity.is_ready is True)

    assert entity.hvac_action is HVACAction.OFF
    assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
    assert entity.target_temperature == entity.max_temp
    assert entity.preset_modes == [
        VThermPreset.NONE,
        VThermPreset.FROST,
        VThermPreset.ECO,
        VThermPreset.COMFORT,
        VThermPreset.BOOST,
    ]
    assert entity.preset_mode is VThermPreset.NONE
    assert entity.vtherm_hvac_modes == [
        VThermHvacMode_OFF,
        VThermHvacMode_COOL,
        VThermHvacMode_HEAT,
    ]

    # Activate the heating by changing VThermHvacMode and temperature
    # Select a hvacmode, presence and preset
    await entity.async_set_hvac_mode(VThermHvacMode_COOL)
    assert entity.vtherm_hvac_mode is VThermHvacMode_COOL
    assert entity.hvac_action == HVACAction.OFF

    # change temperature so that the heating will start
    entity._set_now(now)
    fake_temp_sensor.set_native_value(30)
    fake_ext_temp_sensor.set_native_value(35)
    fake_underlying_climate.set_current_temperature(30)
    await hass.async_block_till_done()

    # set manual target temp
    now = now + timedelta(minutes=7)
    entity._set_now(now)

    await entity.async_set_temperature(temperature=25)

    await wait_for_local_condition(lambda: entity.hvac_action == HVACAction.COOLING)
    assert entity.preset_mode == VThermPreset.NONE  # Manual mode

    # the regulated temperature should be lower
    assert entity.regulated_target_temp < entity.target_temperature
    assert entity.regulated_target_temp == 25 - 2.5  # In medium we could go up to -3 degre
    assert entity.hvac_action == HVACAction.COOLING

    # change temperature so that the regulated temperature should slow down
    now = now + timedelta(minutes=3)
    entity._set_now(now)
    fake_temp_sensor.set_native_value(26)
    fake_ext_temp_sensor.set_native_value(35)
    fake_underlying_climate.set_current_temperature(26)
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)

    # the regulated temperature should be under
    assert entity.regulated_target_temp < entity.target_temperature
    assert entity.regulated_target_temp == 25 - 1  # +2.3 without round_to_nearest

    # change temperature so that the regulated temperature should slow down
    now = now + timedelta(minutes=3)
    entity._set_now(now)
    fake_temp_sensor.set_native_value(18)
    fake_ext_temp_sensor.set_native_value(25)
    fake_underlying_climate.set_current_temperature(18)
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)

    # the regulated temperature should be greater
    assert entity.regulated_target_temp > entity.target_temperature
    assert entity.regulated_target_temp == 25 + 3

    entity.remove_thermostat()


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

    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {})

    # Creates the regulated VTherm over climate at t-20
    # change temperature so that the heating will start
    event_timestamp = now - timedelta(minutes=20)

    with patch(
        "custom_components.versatile_thermostat.const.NowClass.get_now",
        return_value=event_timestamp,
    ):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        def find_my_entity(entity_id) -> ClimateEntity:
            """Find my new entity"""
            component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
            for entity in list(component.entities):
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
        # Activate the heating by changing VThermHvacMode and temperature
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        await entity.async_set_temperature(temperature=17)

        # it is cold today
        await send_temperature_change_event(entity, 15, event_timestamp)
        await send_ext_temperature_change_event(entity, 10, event_timestamp)

        # 1. set manual target temp (at now - 19) -> the regulation should be ignored because too early
        event_timestamp = now - timedelta(minutes=19)
        entity._set_now(event_timestamp)
        await entity.async_set_temperature(temperature=18)
        await hass.async_block_till_done()
        # A timer is not started (change target temperature forces the change)
        assert entity.is_recalculate_scheduled is False

        fake_underlying_climate.set_hvac_action(
            HVACAction.HEATING
        )  # simulate under heating
        await hass.async_block_till_done()
        entity.calculate_hvac_action()
        assert entity.hvac_action == HVACAction.HEATING

        # the regulated temperature will not change because when we set temp manually it is forced
        assert entity.regulated_target_temp == 19.5

        # 2. set manual target temp (at now - 18) -> the regulation should be taken into account
        event_timestamp = now - timedelta(minutes=18)
        entity._set_now(event_timestamp)

        # Set_target_temperature force the update
        await entity.async_set_temperature(temperature=17)
        assert entity.regulated_target_temp > entity.target_temperature
        assert entity.regulated_target_temp == 17 + 1.0  # In strong we could go up to +3 degre. 0.7 without round_to_nearest
        # A timer is stopped
        assert entity.is_recalculate_scheduled is False
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
        assert entity.regulated_target_temp == 17 + 1.5

    entity.remove_thermostat()


# Disable this test which is not working when run in // of others.
# I couldn't find out why
# @pytest.mark.skip
async def test_over_climate_regulation_use_device_temp(hass: HomeAssistant, skip_send_event):
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

    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {})

    assert fake_underlying_climate.current_temperature == 15

    # Creates the regulated VTherm over climate
    # change temperature so that the heating will start
    event_timestamp = now - timedelta(minutes=10)

    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert entity
    assert isinstance(entity, ThermostatOverClimate)

    assert entity.name == "TheOverClimateMockName"
    assert entity.is_over_climate is True
    assert entity.is_regulated is True
    assert entity.auto_regulation_use_device_temp is True
    entity._set_now(event_timestamp)

    # 1.  Activate the heating by changing VThermHvacMode and temperature
    # Select a hvacmode, presence and preset
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.regulated_target_temp == entity.min_temp

    await send_temperature_change_event(entity, 18, event_timestamp)
    await send_ext_temperature_change_event(entity, 10, event_timestamp)

    # 2. set manual target temp (at now - 7) -> no regulation should occurs
    # room temp is 18
    # target is 16
    # internal heater temp is 15
    fake_underlying_climate.set_current_temperature(15)
    event_timestamp = now - timedelta(minutes=7)
    entity._set_now(event_timestamp)

    await entity.async_set_temperature(temperature=16)

    await wait_for_local_condition(lambda: fake_underlying_climate.target_temperature == 12)  # 15 (regulated) - 3 (device offset 18-15)
    assert fake_underlying_climate.hvac_action == HVACAction.IDLE  # current is 15 and target is 12

    # entity.calculate_hvac_action()
    assert entity.hvac_action == HVACAction.IDLE
    assert entity.preset_mode == VThermPreset.NONE  # Manual mode

    # the regulated temperature should be higher
    assert entity.regulated_target_temp < entity.target_temperature
    # The calcul is the following: 16 + (16 - 18) x 0.4 (strong) + 0 x ki - 1 (device offset)
    assert entity.regulated_target_temp == 15  # round(16 + (16 - 18) * 0.4 + 0 * 0.08)

    # 3. change temperature so that the regulated temperature should slow down
    # HVACMODE.HEAT
    # room temp is 15
    # target is 18
    # internal heater temp is 20
    fake_underlying_climate.set_current_temperature(20.1)
    await entity.async_set_temperature(temperature=18)
    await send_ext_temperature_change_event(entity, 9, event_timestamp)

    event_timestamp = now - timedelta(minutes=5)
    entity._set_now(event_timestamp)
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
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
                    },
                    ANY,
                    ANY,
                    ANY,
                    ANY,
                ),
            ]
        )

    # 4. In cool mode
    # room temp is 25
    # target is 23
    # internal heater temp is 27
    await entity.async_set_hvac_mode(VThermHvacMode_COOL)
    await entity.async_set_temperature(temperature=23)
    fake_underlying_climate.set_current_temperature(26.9)
    await send_ext_temperature_change_event(entity, 30, event_timestamp)

    event_timestamp = now - timedelta(minutes=3)
    entity._set_now(event_timestamp)
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        await send_temperature_change_event(entity, 25, event_timestamp)

        # the regulated temperature should be upper (device offset is +1.9)
        assert entity.regulated_target_temp < entity.target_temperature
        assert entity.regulated_target_temp == 22

        mock_service_call.assert_has_calls(
            [
                call.service_call(
                    "climate",
                    "set_temperature",
                    {
                        "entity_id": "climate.mock_climate",
                        "temperature": 24,  # round(22 + 1.9° of offset)
                    },
                    ANY,
                    ANY,
                    ANY,
                    ANY,
                ),
            ]
        )

    entity.remove_thermostat()


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
    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {})

    # Creates the regulated VTherm over climate
    # change temperature so that the heating will start
    event_timestamp = now - timedelta(minutes=20)

    with patch(
        "custom_components.versatile_thermostat.const.NowClass.get_now",
        return_value=event_timestamp,
    ):
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.is_regulated is True

        # Activate the heating by changing VThermHvacMode and temperature
        # Select a hvacmode, presence and preset
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
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
            await hass.async_block_till_done()
            entity.calculate_hvac_action()
            assert entity.hvac_action == HVACAction.HEATING
            assert entity.preset_mode == VThermPreset.NONE  # Manual mode

            # the regulated temperature should be lower
            assert entity.regulated_target_temp > entity.target_temperature
            assert entity.regulated_target_temp == 20 + 2.4  # In Strong we could go up to +5 degre
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
            assert entity.regulated_target_temp == 20 + 1.0

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
            assert entity.regulated_target_temp == 20 + 0.6

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

    entity.remove_thermostat()


async def test_over_climate_regulation_calculation_scheduled(hass: HomeAssistant, skip_send_event):
    """Test the scheduled calculation of regulation for an over climate thermostat
    We should delay the calculation, if room temp changes too frequently
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

    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {})

    # Creates the regulated VTherm over climate
    # change temperature so that the heating will start

    vtherm: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert vtherm
    assert isinstance(vtherm, ThermostatOverClimate)

    assert vtherm.name == "TheOverClimateMockName"
    assert vtherm.is_over_climate is True
    assert vtherm.is_regulated is True
    assert vtherm.is_recalculate_scheduled is False

    # Will initialize the _last_regulation_change
    # Activate the heating by changing VThermHvacMode and temperature
    # Select a hvacmode, presence and preset
    vtherm._set_now(now)
    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
    await vtherm.async_set_temperature(temperature=17)
    await hass.async_block_till_done()
    assert vtherm.is_recalculate_scheduled is False

    # Change the temperature too fast
    now += timedelta(seconds=30)
    vtherm._set_now(now)
    await send_temperature_change_event(vtherm, 15, now)
    await hass.async_block_till_done()
    assert vtherm.is_recalculate_scheduled is True

    # 1. set manual target temp -> the regulation should be send because it is forced
    now += timedelta(seconds=60)
    vtherm._set_now(now)
    await vtherm.async_set_temperature(temperature=18)
    await hass.async_block_till_done()
    # A timer is not started (change target temperature forces the change)
    assert vtherm.is_recalculate_scheduled is False

    # 2. set the outdoor temperature
    now += timedelta(seconds=60)
    vtherm._set_now(now)
    await send_ext_temperature_change_event(vtherm, 0, now)
    await hass.async_block_till_done()
    assert vtherm.is_recalculate_scheduled is True

    # 3 force hvac_mode
    now += timedelta(minutes=2)
    vtherm._set_now(now)
    await vtherm.async_set_hvac_mode(VThermHvacMode_COOL)
    await hass.async_block_till_done()
    assert vtherm.is_recalculate_scheduled is False

    # 2. set the outdoor temperature
    now += timedelta(seconds=60)
    vtherm._set_now(now)
    await send_ext_temperature_change_event(vtherm, 10, now)
    await hass.async_block_till_done()
    assert vtherm.is_recalculate_scheduled is True

    vtherm.remove_thermostat()


async def test_over_climate_set_regulation_mode_none_replaces_algo(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event, fake_underlying_climate
):
    """Test that switching the auto regulation mode to None at runtime replaces the
    active regulation algo with the do-nothing one. Before the fix the previous algo
    stayed in place and kept sending regulated setpoints to the underlyings, while
    is_regulated was already reporting False"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        # This is include a medium regulation
        data=PARTIAL_CLIMATE_CONFIG,
    )

    entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert entity
    assert isinstance(entity, ThermostatOverClimate)
    assert entity.is_regulated is True

    # The medium algo regulates: with a room temp below the target it adds an offset
    entity._regulation_algo.set_target_temp(20)
    assert entity._regulation_algo.calculate_regulated_temperature(17, 10, 1.0) != 20

    await entity.service_set_auto_regulation_mode("None")
    assert entity.is_regulated is False

    # The do-nothing algo must now be in place: it always returns the target
    entity._regulation_algo.set_target_temp(20)
    assert entity._regulation_algo.calculate_regulated_temperature(17, 10, 1.0) == 20

    entity.remove_thermostat()


async def test_over_climate_no_regulation_outside_heat_cool(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor
):
    """Test that auto-regulation is disabled when the over_climate is not in heat nor cool.

    When the VTherm runs in a mode other than heat/cool (e.g. dry), the underlying must
    receive the original (non regulated) target temperature."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: True,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_MEDIUM,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_NONE,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
        },
    )

    # The underlying must support DRY so the VTherm can be set to dry mode
    await create_and_register_mock_climate(
        hass,
        "mock_climate",
        "MockClimateName",
        {},
        hvac_modes=[VThermHvacMode_OFF, VThermHvacMode_COOL, VThermHvacMode_HEAT, VThermHvacMode_DRY],
    )

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

    assert entity
    assert isinstance(entity, ThermostatOverClimate)
    assert entity.is_over_climate is True
    assert entity.is_regulated is True

    await wait_for_local_condition(lambda: entity.is_ready is True)

    # 1. Set the VTherm in COOL mode with a manual target of 25°C and a hot room so
    # that the regulation is active and lowers the regulated temperature.
    now = now + timedelta(minutes=5)
    entity._set_now(now)
    fake_temp_sensor.set_native_value(30)
    fake_ext_temp_sensor.set_native_value(35)
    await entity.async_set_hvac_mode(VThermHvacMode_COOL)
    await entity.async_set_temperature(temperature=25)
    await hass.async_block_till_done()

    assert entity.vtherm_hvac_mode is VThermHvacMode_COOL
    assert entity.target_temperature == 25

    # Force a regulation calculation: the regulated temperature must differ from target
    now = now + timedelta(minutes=3)
    entity._set_now(now)
    await entity._send_regulated_temperature(force=True)
    assert entity.regulated_target_temp != entity.target_temperature

    # 2. Switch to DRY mode: auto-regulation must be disabled and the raw target
    # temperature must be sent to the underlying.
    now = now + timedelta(minutes=3)
    entity._set_now(now)
    await entity.async_set_hvac_mode(VThermHvacMode_DRY)
    await hass.async_block_till_done()

    assert entity.vtherm_hvac_mode is VThermHvacMode_DRY

    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_temperature") as mock_set_temp:
        await entity._send_regulated_temperature(force=True)
        await hass.async_block_till_done()

        # The regulated target temperature must be forced to the raw target temperature
        assert entity.regulated_target_temp == entity.target_temperature

        # The underlying must receive the raw target temperature (no regulation offset)
        assert mock_set_temp.call_count == 1
        sent_temp = mock_set_temp.call_args[0][0]
        assert sent_temp == entity.target_temperature, f"Expected raw target temp {entity.target_temperature} but got {sent_temp}"

    entity.remove_thermostat()

