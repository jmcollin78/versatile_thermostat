# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the normal start of a Thermostat """
from unittest.mock import patch, call

from homeassistant.core import HomeAssistant
from homeassistant.components.climate.const import HVACAction

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_switch_full_start(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the normal full start of a thermostat in thermostat_over_switch type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data=FULL_SWITCH_CONFIG,
    )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        entity = await create_thermostat(hass, entry, "climate.theoverswitchmockname")

        assert entity
        assert isinstance(entity, ThermostatOverSwitch)

        assert entity.name == "TheOverSwitchMockName"
        assert entity.is_over_climate is False
        assert entity.hvac_action is HVACAction.OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            VThermPreset.NONE,
            VThermPreset.FROST,
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
            VThermPreset.ACTIVITY,
        ]
        assert entity.preset_mode is VThermPreset.NONE
        assert entity.safety_manager.is_safety_detected is False
        assert entity.window_state is STATE_UNKNOWN
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN
        assert entity._prop_algorithm is not None
        assert entity.have_valve_regulation is False

        assert entity.vtherm_hvac_modes == [VThermHvacMode_HEAT, VThermHvacMode_OFF]

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2

        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": VThermHvacMode_OFF},
                ),
            ],
            # any_order=True,
        )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_full_start(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the normal full start of a thermostat in thermostat_over_climate type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_CONFIG,
    )

    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {}, hvac_modes=[VThermHvacMode_HEAT, VThermHvacMode_OFF, VThermHvacMode_HEAT_COOL])

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ) as mock_find_climate:
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname")

        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        assert entity.name == "TheOverClimateMockName"
        assert entity.is_over_climate is True
        assert entity.hvac_action is HVACAction.OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            VThermPreset.NONE,
            VThermPreset.FROST,
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
        ]
        assert entity.preset_mode is VThermPreset.NONE
        assert entity.safety_manager.is_safety_detected is False
        assert entity.window_state is STATE_UNAVAILABLE
        assert entity.motion_state is STATE_UNAVAILABLE
        assert entity.presence_state is STATE_UNAVAILABLE
        assert entity.have_valve_regulation is False

        # hvac_modes comes from underlying entity + OFF. there is no AC mode in underlying entity
        assert entity.vtherm_hvac_modes == [VThermHvacMode_HEAT, VThermHvacMode_OFF, VThermHvacMode_COOL]

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": VThermHvacMode_OFF},
                ),
            ]
        )

        assert mock_find_climate.call_count == 1
        assert mock_find_climate.mock_calls[0] == call()
        mock_find_climate.assert_has_calls([call.find_underlying_entity()])


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_duplicate_name(hass: HomeAssistant, skip_hass_states_is_state):
    """Test that sub entries are generated correctly when multiple thermostat entries have the same title"""

    fake_underlying_climate = MockClimate(hass, "mockUniqueId", "MockClimateName", {}, hvac_modes=[VThermHvacMode_HEAT, VThermHvacMode_OFF, VThermHvacMode_HEAT_COOL])

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate",
        return_value=fake_underlying_climate,
    ) as mock_find_climate:
        for idx in range(1, 4):
            entry = MockConfigEntry(
                domain=DOMAIN,
                title="TheOverClimateMockName",
                unique_id=f"uniqueId_{idx}",
                data=PARTIAL_CLIMATE_CONFIG,
                version=2,
                minor_version=2 if idx > 1 else 1,
            )

            entity = await create_thermostat(hass, entry, f"climate.theoverclimatemockname_{idx}")

            assert entity
            assert isinstance(entity, ThermostatOverClimate)

            entity_id_suffix = "" if idx == 1 else f"_{idx}"
            sensor_suffix = "_safety_state"
            sensor = search_simple_entity(hass, f"binary_sensor.theoverclimatemockname{sensor_suffix}{entity_id_suffix}")
            assert sensor is not None
            # Check that we use entry title in unique_id for old entries.
            if idx == 1:
                assert sensor.unique_id == entry.title + sensor_suffix


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_4switch_full_start(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the normal full start of a thermostat in thermostat_over_switch with 4 switches type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOver4SwitchMockName",
        unique_id="uniqueId",
        data=FULL_4SWITCH_CONFIG,
    )

    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event:
        entity = await create_thermostat(hass, entry, "climate.theover4switchmockname")

        assert entity

        assert entity.name == "TheOver4SwitchMockName"
        assert entity.is_over_switch
        assert entity.hvac_action is HVACAction.OFF
        assert entity.vtherm_hvac_mode is VThermHvacMode_OFF
        assert entity.target_temperature == entity.min_temp
        assert entity.preset_modes == [
            VThermPreset.NONE,
            VThermPreset.FROST,
            VThermPreset.ECO,
            VThermPreset.COMFORT,
            VThermPreset.BOOST,
            VThermPreset.ACTIVITY,
        ]
        assert entity.preset_mode is VThermPreset.NONE
        assert entity.safety_manager.is_safety_detected is False
        assert entity.window_state is STATE_UNKNOWN
        assert entity.motion_state is STATE_UNKNOWN
        assert entity.presence_state is STATE_UNKNOWN
        assert entity._prop_algorithm is not None

        assert entity.nb_underlying_entities == 4

        # Checks that we have the 4 UnderlyingEntity correctly configured
        for idx in range(4):
            under = entity.underlying_entity(idx)
            assert under is not None
            assert isinstance(under, UnderlyingSwitch)
            assert under.entity_id == "switch.mock_4switch" + str(idx)
            assert under.initial_delay_sec == 8 * 60 / 4 * idx

        # should have been called with EventType.PRESET_EVENT and EventType.HVAC_MODE_EVENT
        assert mock_send_event.call_count == 2

        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.NONE}),
                call.send_event(
                    EventType.HVAC_MODE_EVENT,
                    {"hvac_mode": VThermHvacMode_OFF},
                ),
            ]
        )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_switch_deactivate_preset(
    hass: HomeAssistant, skip_hass_states_is_state
):
    """Test the normal full start of a thermostat in thermostat_over_switch type"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 8,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "frost_temp": 0,
            "eco_temp": 17,
            "comfort_temp": 0,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_HEATER: "switch.mock_switch1",
            CONF_HEATER_2: None,
            CONF_HEATER_3: None,
            CONF_HEATER_4: None,
            CONF_HEATER_KEEP_ALIVE: 0,
            CONF_SAFETY_DELAY_MIN: 10,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.01,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity
    assert isinstance(entity, ThermostatOverSwitch)

    assert entity.preset_modes == [
        VThermPreset.NONE,
        # VThermPreset.FROST,
        VThermPreset.ECO,
        # VThermPreset.COMFORT,
        VThermPreset.BOOST,
    ]
    assert entity.preset_mode is VThermPreset.NONE

    # try to set the COMFORT Preset which is absent
    try:
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
    except ValueError as err:
        print(err)
    else:
        assert False
    finally:
        assert entity.preset_mode is VThermPreset.NONE
