# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the Security featrure """
from unittest.mock import patch, call, PropertyMock, MagicMock
from datetime import timedelta, datetime
import logging

from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.feature_safety_manager import (
    FeatureSafetyManager,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_safety_feature_manager_create(
    hass: HomeAssistant,
):
    """Test the FeatureMotionManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    # 1. creation
    safety_manager = FeatureSafetyManager(fake_vtherm, hass)

    assert safety_manager is not None
    assert safety_manager.is_configured is False
    assert safety_manager.is_safety_detected is False
    assert safety_manager.safety_state is STATE_UNAVAILABLE
    assert safety_manager.name == "the name"

    assert len(safety_manager._active_listener) == 0

    custom_attributes = {}
    safety_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_safety_configured"] is False
    assert custom_attributes["safety_state"] is STATE_UNAVAILABLE
    assert custom_attributes.get("safety_delay_min", None) is None
    assert custom_attributes.get("safety_min_on_percent", None) is None
    assert custom_attributes.get("safety_default_on_percent", None) is None


@pytest.mark.parametrize(
    "safety_delay_min, safety_min_on_percent, safety_default_on_percent, is_configured, state",
    [
        # fmt: off
        ( 10, 11, 12, True, STATE_UNKNOWN),
        ( None, 11, 12, False, STATE_UNAVAILABLE),
        ( 10, None, 12, True, STATE_UNKNOWN),
        ( 10, 11, None, True, STATE_UNKNOWN),
        ( 10, None, None, True, STATE_UNKNOWN),
        ( None, None, None, False, STATE_UNAVAILABLE),
        # fmt: on
    ],
)
async def test_safety_feature_manager_post_init(
    hass: HomeAssistant,
    safety_delay_min,
    safety_min_on_percent,
    safety_default_on_percent,
    is_configured,
    state,
):
    """Test the FeatureSafetyManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")

    # 1. creation
    safety_manager = FeatureSafetyManager(fake_vtherm, hass)
    assert safety_manager is not None

    # 2. post_init
    safety_manager.post_init(
        {
            CONF_SAFETY_DELAY_MIN: safety_delay_min,
            CONF_SAFETY_MIN_ON_PERCENT: safety_min_on_percent,
            CONF_SAFETY_DEFAULT_ON_PERCENT: safety_default_on_percent,
        }
    )

    assert safety_manager.is_configured is is_configured
    assert safety_manager.safety_state is state

    custom_attributes = {}
    safety_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_safety_configured"] is is_configured
    assert custom_attributes["safety_state"] is state

    if safety_manager.is_configured:
        assert custom_attributes.get("safety_delay_min", None) == safety_delay_min
        assert (
            custom_attributes.get("safety_min_on_percent", None)
            == safety_min_on_percent
            or DEFAULT_SAFETY_MIN_ON_PERCENT
        )
        assert (
            custom_attributes.get("safety_default_on_percent", None)
            == safety_default_on_percent
            or DEFAULT_SAFETY_DEFAULT_ON_PERCENT
        )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_security_feature(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the security feature and https://github.com/jmcollin78/versatile_thermostat/issues/49:
    1. creates a thermostat and check that security is off
    2. activate security feature when date is expired
    3. change the preset to boost
    5. resolve the date issue
    6. check that security is off and preset is changed to boost
    """

    tz = get_tz(hass)  # pylint: disable=invalid-name

    temps = {
        "frost": 7,
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        # With migration
        version=CONFIG_VERSION,
        minor_version=0,
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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
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
    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    await set_all_climate_preset_temp(hass, entity, temps, "theoverswitchmockname")

    assert entity.safety_manager.safety_state is not STATE_ON
    assert entity.safety_manager.is_safety_detected is False
    assert entity.preset_mode is not PRESET_SAFETY
    assert entity.preset_modes == [
        PRESET_NONE,
        PRESET_FROST_PROTECTION,
        PRESET_ECO,
        PRESET_COMFORT,
        PRESET_BOOST,
    ]
    assert entity._last_ext_temperature_measure is not None
    assert entity._last_temperature_measure is not None
    assert (entity._last_temperature_measure.astimezone(tz) - now).total_seconds() < 1
    assert (
        entity._last_ext_temperature_measure.astimezone(tz) - now
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
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        event_timestamp = now - timedelta(minutes=6)

        # set temperature to 15 so that on_percent will be > security_min_on_percent (0.2)
        await send_temperature_change_event(entity, 15, event_timestamp)
        assert entity.safety_state is STATE_ON
        assert entity.preset_mode == PRESET_SAFETY
        assert entity._saved_preset_mode == PRESET_COMFORT
        assert entity._prop_algorithm.on_percent == 0.1
        assert entity._prop_algorithm.calculated_on_percent == 0.9

        assert mock_send_event.call_count == 3
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_SAFETY}),
                call.send_event(
                    EventType.TEMPERATURE_EVENT,
                    {
                        "last_temperature_measure": event_timestamp.isoformat(),
                        "last_ext_temperature_measure": entity._last_ext_temperature_measure.isoformat(),
                        "current_temp": 15,
                        "current_ext_temp": None,
                        "target_temp": 18,
                    },
                ),
                call.send_event(
                    EventType.SECURITY_EVENT,
                    {
                        "type": "start",
                        "last_temperature_measure": event_timestamp.isoformat(),
                        "last_ext_temperature_measure": entity._last_ext_temperature_measure.isoformat(),
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
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        await entity.async_set_preset_mode(PRESET_BOOST)

        # 4. check that security is still on
        assert entity.safety_manager.safety_state is STATE_ON
        assert entity.safety_manager.is_safety_detected is True

        assert entity._prop_algorithm.on_percent == 0.1
        assert entity._prop_algorithm.calculated_on_percent == 0.9
        assert entity._saved_preset_mode == PRESET_BOOST
        assert entity.preset_mode is PRESET_SAFETY

    # 5. resolve the datetime issue
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        event_timestamp = datetime.now()

        # set temperature to 15 so that on_percent will be > security_min_on_percent (0.2)
        await send_temperature_change_event(entity, 15.2, event_timestamp)

        assert entity.safety_manager.safety_state is not STATE_ON
        assert entity.safety_manager.is_safety_detected is False

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
                        "last_temperature_measure": event_timestamp.astimezone(
                            tz
                        ).isoformat(),
                        "last_ext_temperature_measure": entity._last_ext_temperature_measure.astimezone(
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
async def test_security_feature_back_on_percent(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the security feature and https://github.com/jmcollin78/versatile_thermostat/issues/49:
    1. creates a thermostat and check that security is off, preset Boost
    2. change temperature so that on_percent is high
    3. send next timestamp date so that security is on WITH A Eco preset that makes a on_percent low
    4. this shoud resolve the date issue
    4. check that security is off and preset is Boost
    """

    tz = get_tz(hass)  # pylint: disable=invalid-name
    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
        "frost": 10,
    }

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
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            "proportional_function": "tpi",
            "tpi_coef_int": 0.3,
            "tpi_coef_ext": 0.01,
            "minimal_activation_delay": 30,
            "safety_delay_min": 5,  # 5 minutes
            "safety_min_on_percent": 0.2,
            "safety_default_on_percent": 0.1,
        },
    )

    # 1. creates a thermostat and check that security is off
    now: datetime = datetime.now(tz=tz)
    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    await set_all_climate_preset_temp(hass, entity, temps, "theoverswitchmockname")

    assert entity.safety_manager.safety_state is not STATE_ON
    assert entity.safety_manager.is_safety_detected is False

    assert entity.preset_mode is not PRESET_SAFETY
    assert entity._last_ext_temperature_measure is not None
    assert entity._last_temperature_measure is not None
    assert (entity._last_temperature_measure.astimezone(tz) - now).total_seconds() < 1
    assert (
        entity._last_ext_temperature_measure.astimezone(tz) - now
    ).total_seconds() < 1

    # set a preset
    assert entity.preset_mode is PRESET_NONE
    await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.preset_mode is PRESET_BOOST

    # Turn On the thermostat
    assert entity.hvac_mode == HVACMode.OFF
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    assert entity.hvac_mode == HVACMode.HEAT

    # 2. activate on_percent
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        event_timestamp = now + timedelta(minutes=1)
        entity._set_now(event_timestamp)  # pylint: disable=protected-access

        # set temperature to 17 so that on_percent will be > security_min_on_percent (0.2)
        await send_temperature_change_event(entity, 17, event_timestamp)
        assert entity._prop_algorithm.calculated_on_percent == 0.6
        assert entity.preset_mode == PRESET_BOOST
        assert entity.safety_state is not STATE_ON
        assert mock_send_event.call_count == 0

    # 3. Set safety mode with a preset change
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        # 6 min between two mesure
        event_timestamp = event_timestamp + timedelta(minutes=6)
        entity._set_now(event_timestamp)  # pylint: disable=protected-access

        await send_temperature_change_event(entity, 17, event_timestamp)

        assert entity._prop_algorithm.calculated_on_percent == 0.6

        assert entity.safety_state is STATE_ON
        assert entity.preset_mode == PRESET_SAFETY
        assert entity._saved_preset_mode == PRESET_BOOST

        assert mock_send_event.call_count == 3
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_SAFETY}),
                call.send_event(
                    EventType.TEMPERATURE_EVENT,
                    {
                        "last_temperature_measure": event_timestamp.isoformat(),
                        "last_ext_temperature_measure": entity._last_ext_temperature_measure.isoformat(),
                        "current_temp": 17,
                        "current_ext_temp": None,
                        "target_temp": 19,
                    },
                ),
                call.send_event(
                    EventType.SECURITY_EVENT,
                    {
                        "type": "start",
                        "last_temperature_measure": event_timestamp.isoformat(),
                        "last_ext_temperature_measure": entity._last_ext_temperature_measure.isoformat(),
                        "current_temp": 17,
                        "current_ext_temp": None,
                        "target_temp": 19,
                    },
                ),
            ],
            any_order=True,
        )

        # heating have been started on the previous call
        assert mock_heater_on.call_count == 0

    # 4. change preset so that on_percent will be low
    event_timestamp = event_timestamp + timedelta(minutes=1)
    entity._set_now(event_timestamp)  # pylint: disable=protected-access

    await entity.async_set_preset_mode(PRESET_ECO)
    assert entity.safety_state is STATE_ON
    assert entity.preset_mode == PRESET_SAFETY

    # 5. resolve the datetime issue
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        # +2 min between two mesure
        event_timestamp = event_timestamp + timedelta(minutes=2)
        entity._set_now(event_timestamp)  # pylint: disable=protected-access

        # set temperature to 18.9 so that on_percent will be > security_min_on_percent (0.2)
        await send_temperature_change_event(entity, 18.92, event_timestamp)

        assert entity.safety_manager.safety_state is not STATE_ON
        assert entity.safety_manager.is_safety_detected is False

        assert entity.preset_mode == PRESET_ECO
        assert entity._saved_preset_mode == PRESET_ECO
        assert entity._prop_algorithm.on_percent == 0.0
        assert entity._prop_algorithm.calculated_on_percent == 0.0

        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": PRESET_ECO}),
                call.send_event(
                    EventType.SECURITY_EVENT,
                    {
                        "type": "end",
                        "last_temperature_measure": event_timestamp.astimezone(
                            tz
                        ).isoformat(),
                        "last_ext_temperature_measure": entity._last_ext_temperature_measure.astimezone(
                            tz
                        ).isoformat(),
                        "current_temp": 18.92,
                        "current_ext_temp": None,
                        "target_temp": 17,
                    },
                ),
            ],
            any_order=True,
        )

        # Heater is stays off
        assert mock_heater_on.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_security_over_climate(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    skip_turn_on_off_heater,
    skip_send_event,
):
    """Test that when a underlying climate is not available the VTherm doesn't go into safety mode"""

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_CONFIG,  # 5 minutes security delay
    )

    fake_underlying_climate = MockClimate(
        hass, "mockUniqueId", "MockClimateName", {}, HVACMode.HEAT, HVACAction.HEATING
    )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
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

        entity: ThermostatOverClimate = find_my_entity("climate.theoverclimatemockname")

        assert entity

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True

        # Because the underlying is HEATING. In real life the underlying will be shut-off
        assert entity.hvac_action is HVACAction.HEATING
        assert entity.hvac_mode is HVACMode.OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            PRESET_NONE,
            PRESET_FROST_PROTECTION,
            PRESET_ECO,
            PRESET_COMFORT,
            PRESET_BOOST,
        ]
        assert entity.preset_mode is PRESET_NONE
        assert entity.safety_manager.safety_state is not STATE_ON
        assert entity.safety_manager.is_safety_detected is False

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                # At startup
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

        # Force safety mode
        assert entity._last_ext_temperature_measure is not None
        assert entity._last_temperature_measure is not None
        assert (
            entity._last_temperature_measure.astimezone(tz) - now
        ).total_seconds() < 1
        assert (
            entity._last_ext_temperature_measure.astimezone(tz) - now
        ).total_seconds() < 1

        # Tries to turns on the Thermostat
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        assert entity.hvac_mode == HVACMode.HEAT

        # One call more
        assert mock_send_event.call_count == 3
        mock_send_event.assert_has_calls(
            [
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": HVACMode.HEAT},
                ),
            ]
        )

        # 2. activate security feature when date is expired
        with patch(
            "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
        ) as mock_send_event, patch(
            "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
        ):
            event_timestamp = now - timedelta(minutes=6)

            await send_temperature_change_event(entity, 15, event_timestamp)
            # Should stay False because a climate is never in safety mode
            assert entity.safety_state is not STATE_ON
            assert entity.preset_mode == "none"
            assert entity._saved_preset_mode == "none"


async def test_migration_security_safety(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the migration of security parameters to safety in English"""
    central_config_entry = MockConfigEntry(
        # Current is 2.1
        version=CONFIG_VERSION,
        # An old minor version
        minor_version=0,
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: "migrationName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_UNDERLYING_LIST: ["switch.under1"],
            "security_delay_min": 61,
            "security_min_on_percent": 0.5,
            "security_default_on_percent": 0.2,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
        },
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverSwitch = search_entity(
        hass, "climate.migrationname", "climate"
    )

    assert entity is not None

    assert entity.safety_manager.safety_min_on_percent == 0.5
    assert entity.safety_manager.safety_default_on_percent == 0.2
    assert entity.safety_manager.safety_delay_min == 61
