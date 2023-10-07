""" Test the Security featrure """
from unittest.mock import patch, call

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

from datetime import timedelta, datetime
import logging

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_security_feature(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the security feature and https://github.com/jmcollin78/versatile_thermostat/issues/49:
    1. creates a thermostat and check that security is off
    2. activate security feature when date is expired
    3. change the preset to boost
    4. check that security is still on
    5. resolve the date issue
    6. check that security is off and preset is changed to boost
    """

    tz = get_tz(hass)  # pylint: disable=invalid-name

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
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            "use_window_feature": False,
            "use_motion_feature": False,
            "use_power_feature": False,
            "use_presence_feature": False,
            "heater_entity_id": "switch.mock_switch",
            "proportional_function": "tpi",
            "tpi_coef_int": 0.3,
            "tpi_coef_ext": 0.01,
            "minimal_activation_delay": 30,
            "security_delay_min": 5,  # 5 minutes
            "security_min_on_percent": 0.2,
            "security_default_on_percent": 0.1,
        },
    )

    # 1. creates a thermostat and check that security is off
    now: datetime = datetime.now(tz=tz)
    entity: VersatileThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    assert entity._security_state is False
    assert entity.preset_mode is not PRESET_SECURITY
    assert entity.preset_modes == [
        PRESET_NONE,
        PRESET_ECO,
        PRESET_COMFORT,
        PRESET_BOOST,
    ]
    assert entity._last_ext_temperature_mesure is not None
    assert entity._last_temperature_mesure is not None
    assert (entity._last_temperature_mesure.astimezone(tz) - now).total_seconds() < 1
    assert (
        entity._last_ext_temperature_mesure.astimezone(tz) - now
    ).total_seconds() < 1

    # set a preset
    assert entity.preset_mode is PRESET_NONE
    await entity.async_set_preset_mode(PRESET_COMFORT)
    assert entity.preset_mode is PRESET_COMFORT

    # Turn On the thermostat
    assert entity.hvac_mode == HVACMode.OFF
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    assert entity.hvac_mode == HVACMode.HEAT

    # 2. activate security feature when date is expired
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        event_timestamp = now - timedelta(minutes=6)

        # set temperature to 15 so that on_percent will be > security_min_on_percent (0.2)
        await send_temperature_change_event(entity, 15, event_timestamp)
        assert entity.security_state is True
        assert entity.preset_mode == PRESET_SECURITY
        assert entity._saved_preset_mode == PRESET_COMFORT
        assert entity._prop_algorithm.on_percent == 0.1
        assert entity._prop_algorithm.calculated_on_percent == 0.9

        assert mock_send_event.call_count == 3
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_SECURITY}),
                call.send_event(
                    EventType.TEMPERATURE_EVENT,
                    {
                        "last_temperature_mesure": event_timestamp.isoformat(),
                        "last_ext_temperature_mesure": entity._last_ext_temperature_mesure.isoformat(),
                        "current_temp": 15,
                        "current_ext_temp": None,
                        "target_temp": 18,
                    },
                ),
                call.send_event(
                    EventType.SECURITY_EVENT,
                    {
                        "type": "start",
                        "last_temperature_mesure": event_timestamp.isoformat(),
                        "last_ext_temperature_mesure": entity._last_ext_temperature_mesure.isoformat(),
                        "current_temp": 15,
                        "current_ext_temp": None,
                        "target_temp": 18,
                    },
                ),
            ],
            any_order=True,
        )

        assert mock_heater_on.call_count == 1

    # 3. Change the preset to Boost (we should stay in SECURITY)
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        await entity.async_set_preset_mode(PRESET_BOOST)

        # 4. check that security is still on
        assert entity._security_state is True
        assert entity._prop_algorithm.on_percent == 0.1
        assert entity._prop_algorithm.calculated_on_percent == 0.9
        assert entity._saved_preset_mode == PRESET_BOOST
        assert entity.preset_mode is PRESET_SECURITY

    # 5. resolve the datetime issue
    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        event_timestamp = datetime.now()

        # set temperature to 15 so that on_percent will be > security_min_on_percent (0.2)
        await send_temperature_change_event(entity, 15.2, event_timestamp)

        assert entity._security_state is False
        assert entity.preset_mode == PRESET_BOOST
        assert entity._saved_preset_mode == PRESET_BOOST
        assert entity._prop_algorithm.on_percent == 1.0
        assert entity._prop_algorithm.calculated_on_percent == 1.0

        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_BOOST}),
                call.send_event(
                    EventType.SECURITY_EVENT,
                    {
                        "type": "end",
                        "last_temperature_mesure": event_timestamp.astimezone(
                            tz
                        ).isoformat(),
                        "last_ext_temperature_mesure": entity._last_ext_temperature_mesure.astimezone(
                            tz
                        ).isoformat(),
                        "current_temp": 15.2,
                        "current_ext_temp": None,
                        "target_temp": 19,
                    },
                ),
            ],
            any_order=True,
        )

        # Heater is now on
        assert mock_heater_on.call_count == 1


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_security_over_climate(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that when a underlying climate is not available the VTherm doesn't go into security mode"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_CONFIG, # 5 minutes security delay
    )

    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {}, HVACMode.HEAT)

    with patch(
        "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ) as mock_find_climate:
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        def find_my_entity(entity_id) -> ClimateEntity:
            """Find my new entity"""
            component: EntityComponent[ClimateEntity] = hass.data[CLIMATE_DOMAIN]
            for entity in component.entities:
                if entity.entity_id == entity_id:
                    return entity

        entity = find_my_entity("climate.theoverclimatemockname")

        assert entity

        assert entity.name == "TheOverClimateMockName"
        assert entity._is_over_climate is True
        assert entity.hvac_action is HVACAction.OFF
        assert entity.hvac_mode is HVACMode.HEAT
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            PRESET_NONE,
            PRESET_ECO,
            PRESET_COMFORT,
            PRESET_BOOST,
        ]
        assert entity.preset_mode is PRESET_NONE
        assert entity._security_state is False

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": HVACMode.OFF},
                ),
            ]
        )

        assert mock_find_climate.call_count == 1
        assert mock_find_climate.mock_calls[0] == call()
        mock_find_climate.assert_has_calls([call.find_underlying_entity()])

        # Force security mode
        assert entity._last_ext_temperature_mesure is not None
        assert entity._last_temperature_mesure is not None
        assert (entity._last_temperature_mesure.astimezone(tz) - now).total_seconds() < 1
        assert (
            entity._last_ext_temperature_mesure.astimezone(tz) - now
        ).total_seconds() < 1

        # Tries to turns on the Thermostat
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode == HVACMode.HEAT

        # 2. activate security feature when date is expired
        with patch(
            "custom_components.versatile_thermostat.climate.VersatileThermostat.send_event"
        ) as mock_send_event, patch(
            "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
        ) as mock_heater_on:
            event_timestamp = now - timedelta(minutes=6)

            await send_temperature_change_event(entity, 15, event_timestamp)
            # Should stay False because a climate is never in security mode
            assert entity.security_state is False
            assert entity.preset_mode == 'none'
            assert entity._saved_preset_mode == 'none'