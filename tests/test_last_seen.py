# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the Security featrure """
from unittest.mock import patch, call
from datetime import timedelta, datetime
import logging

from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


logging.getLogger().setLevel(logging.DEBUG)


async def test_last_seen_feature(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the last_ssen feature
    1. creates a thermostat and check that security is off
    2. activate security feature when date is expired
    3. change the last seen sensor
    4. check that security is off
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
        data={
            "name": "TheOverSwitchMockName",
            "thermostat_type": "thermostat_over_switch",
            "temperature_sensor_entity_id": "sensor.mock_temp_sensor",
            "last_seen_temperature_sensor_entity_id": "sensor.mock_last_seen_temp_sensor",
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
            "minimal_deactivation_delay": 0,
            CONF_SAFETY_DELAY_MIN: 5,  # 5 minutes
            CONF_SAFETY_MIN_ON_PERCENT: 0.2,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
        },
    )

    # 1. creates a thermostat and check that security is off
    now: datetime = datetime.now(tz=tz)
    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    assert entity

    entity._set_now(now)

    await set_all_climate_preset_temp(hass, entity, temps, "theoverswitchmockname")

    assert entity.safety_manager.is_safety_detected is False
    assert entity.preset_mode is not VThermPreset.SAFETY
    assert entity._last_ext_temperature_measure is not None
    assert entity._last_temperature_measure is not None
    assert (entity._last_temperature_measure.astimezone(tz) - now).total_seconds() < 1
    assert (
        entity._last_ext_temperature_measure.astimezone(tz) - now
    ).total_seconds() < 1

    # set a preset
    assert entity.preset_mode is VThermPreset.NONE
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    assert entity.preset_mode == VThermPreset.COMFORT

    # Turn On the thermostat
    assert entity.hvac_mode == VThermHvacMode_OFF
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    assert entity.hvac_mode == VThermHvacMode_HEAT

    last_change_time_from_vtherm = entity._last_change_time_from_vtherm

    # 2. activate security feature when date is expired
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on:
        event_timestamp = now - timedelta(minutes=6)

        # set temperature to 15 so that on_percent will be > safety_min_on_percent (0.2)
        await send_temperature_change_event(entity, 15, event_timestamp)
        assert entity.safety_state is STATE_ON
        assert entity.preset_mode == VThermPreset.SAFETY

        assert mock_send_event.call_count == 3
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.SAFETY}),
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
                    EventType.SAFETY_EVENT,
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

        assert entity._last_change_time_from_vtherm == last_change_time_from_vtherm

    # 3. change the last seen sensor
    event_timestamp = now - timedelta(minutes=4)
    await send_last_seen_temperature_change_event(entity, event_timestamp)
    assert entity.safety_state is not STATE_ON
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity._last_temperature_measure == event_timestamp

    assert entity._last_change_time_from_vtherm == last_change_time_from_vtherm
