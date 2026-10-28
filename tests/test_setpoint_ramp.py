# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the setpoint ramp of an over climate thermostat """
import logging
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import voluptuous as vol

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant, State
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.versatile_thermostat.config_schema import STEP_THERMOSTAT_CLIMATE
from custom_components.versatile_thermostat.thermostat_climate import ThermostatOverClimate
from custom_components.versatile_thermostat.underlyings import UnderlyingClimate

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

# One cycle of the thermostat, in minutes. Longer than the minimal regulation period of the config
CYCLE_MIN = 5

HEAT_CONFIG = PARTIAL_CLIMATE_NOT_REGULATED_CONFIG | {CONF_AUTO_REGULATION_PERIOD_MIN: 1, CONF_AUTO_REGULATION_DTEMP: 0.5}
COOL_CONFIG = PARTIAL_CLIMATE_AC_CONFIG | {
    CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_NONE,
    CONF_AUTO_REGULATION_PERIOD_MIN: 1,
    CONF_AUTO_REGULATION_DTEMP: 0.5,
}


def ramp_config(base: dict, offset: float | None = -0.5, max_step: float | None = 1.0, enabled: bool = True) -> dict:
    """Build a config with the ramp options. A None option is left out of the config"""
    config = base | {CONF_AUTO_REGULATION_RAMP: enabled}
    if offset is not None:
        config[CONF_AUTO_REGULATION_RAMP_START_OFFSET] = offset
    if max_step is not None:
        config[CONF_AUTO_REGULATION_RAMP_MAX_STEP] = max_step
    return config


async def create_ramp_thermostat(hass: HomeAssistant, config: dict) -> tuple[ThermostatOverClimate, datetime]:
    """Create the thermostat and return it with the simulated date"""
    entry = MockConfigEntry(domain=DOMAIN, title="TheOverClimateMockName", unique_id="uniqueId", data=config)
    entity: ThermostatOverClimate = await create_thermostat(hass, entry, "climate.theoverclimatemockname")
    assert isinstance(entity, ThermostatOverClimate)
    await wait_for_local_condition(lambda: entity.is_ready is True)
    now = datetime.now(tz=get_tz(hass))
    entity._set_now(now)
    return entity, now


async def next_cycle(entity: ThermostatOverClimate, now: datetime) -> datetime:
    """Move the clock forward by one cycle and run the regulation"""
    now = now + timedelta(minutes=CYCLE_MIN)
    entity._set_now(now)
    await entity._send_regulated_temperature()
    return now


async def run_cycles(entity: ThermostatOverClimate, now: datetime, count: int) -> list[float]:
    """Run some cycles and return the setpoint last sent to the underlying after each one"""
    sent = []
    for _ in range(count):
        now = await next_cycle(entity, now)
        sent.append(entity._underlyings[0].last_sent_temperature)
    return sent


async def start_heating(entity: ThermostatOverClimate, now: datetime, room: float, target: float, mode=VThermHvacMode_HEAT):
    """Set the room temperature and the target, then switch the thermostat on"""
    await send_temperature_change_event(entity, room, now)
    await entity.async_set_temperature(temperature=target)
    await entity.async_set_hvac_mode(mode)
    await entity.hass.async_block_till_done()


@pytest.mark.parametrize(
    "room, target, offset, max_step, expected",
    [
        # A negative offset starts below the room temperature: the unit sees no demand at first
        (18, 21, -0.5, 1.0, [17.5, 18.5, 19.5, 20.5, 21, 21]),
        # A positive offset starts above the room temperature. The step is the rounding step
        (18, 21, 1.0, 0.5, [19, 19.5, 20, 20.5, 21, 21]),
        # Zero starts at the room temperature
        (18, 21, 0.0, 1.0, [18, 19, 20, 21, 21]),
        # The start never goes beyond the target
        (20, 21, 1.5, 1.0, [21, 21]),
        # No limit per cycle: the target is sent on the first cycle after the start
        (18, 21, -1.0, 0.0, [17, 21, 21]),
    ],
)
async def test_ramp_heat(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate, room, target, offset, max_step, expected):
    """The setpoint starts relative to the room temperature, then moves by at most one step per cycle"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, offset, max_step))
    assert entity.is_ramp_active is True

    await start_heating(entity, now, room, target)

    under = entity._underlyings[0]
    # The start setpoint is sent when the thermostat is switched on
    assert under.last_sent_temperature == expected[0]
    assert entity.regulated_target_temp == expected[0]

    assert await run_cycles(entity, now, len(expected) - 1) == expected[1:]
    # The ramp stays on the target
    assert entity.regulated_target_temp == target

    entity.remove_thermostat()


@pytest.mark.parametrize(
    "room, target, offset, max_step, expected",
    [
        # Cooling is the mirror of heating: a negative offset starts above the room temperature
        (26, 23, -0.5, 1.0, [26.5, 25.5, 24.5, 23.5, 23, 23]),
        # A positive offset starts below the room temperature
        (26, 23, 1.0, 0.5, [25, 24.5, 24, 23.5, 23, 23]),
    ],
)
async def test_ramp_cool(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate, room, target, offset, max_step, expected):
    """In cool mode the setpoint goes down, never below the target"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(COOL_CONFIG, offset, max_step))

    await start_heating(entity, now, room, target, VThermHvacMode_COOL)

    under = entity._underlyings[0]
    assert under.last_sent_temperature == expected[0]
    assert await run_cycles(entity, now, len(expected) - 1) == expected[1:]

    entity.remove_thermostat()


async def test_ramp_disabled_by_default(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """An entry without the ramp options behaves as before: the target is sent at once"""
    entity, now = await create_ramp_thermostat(hass, HEAT_CONFIG)
    assert entity.is_ramp_active is False
    assert entity._ramp_start_offset == -0.5
    assert entity._ramp_max_step == 1.0

    await start_heating(entity, now, 18, 21)
    await next_cycle(entity, now)

    assert entity._underlyings[0].last_sent_temperature == 21
    assert entity._ramp_value is None

    entity.remove_thermostat()


async def test_ramp_options_not_enabled(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """The offset and the step are ignored while the ramp is not enabled"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -1.0, 0.5, enabled=False))
    assert entity.is_ramp_active is False

    await start_heating(entity, now, 18, 21)

    assert entity._underlyings[0].last_sent_temperature == 21

    entity.remove_thermostat()


async def test_ramp_step_once_per_cycle(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """Several regulations in the same cycle move the setpoint only once"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -0.5, 1.0))
    await start_heating(entity, now, 18, 21)
    under = entity._underlyings[0]
    assert under.last_sent_temperature == 17.5

    # Less than a cycle since the start
    for minutes in (1, 2, 3):
        entity._set_now(now + timedelta(minutes=minutes))
        await entity._send_regulated_temperature(force=True)
        assert under.last_sent_temperature == 17.5

    now = now + timedelta(minutes=CYCLE_MIN)
    entity._set_now(now)
    await entity._send_regulated_temperature(force=True)
    assert under.last_sent_temperature == 18.5

    # A forced regulation in the same cycle does not move it again
    await entity._send_regulated_temperature(force=True)
    assert under.last_sent_temperature == 18.5

    entity.remove_thermostat()


async def test_ramp_target_changes(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """A higher target is reached step by step, a lower target is sent at once"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -0.5, 1.0))
    await start_heating(entity, now, 18, 21)
    under = entity._underlyings[0]
    assert await run_cycles(entity, now, 2) == [18.5, 19.5]
    now = now + timedelta(minutes=2 * CYCLE_MIN)

    # The target is raised: the ramp goes on
    await entity.async_set_temperature(temperature=25)
    assert under.last_sent_temperature == 19.5
    assert await run_cycles(entity, now, 2) == [20.5, 21.5]
    now = now + timedelta(minutes=2 * CYCLE_MIN)

    # The target is lowered under the ramp: the demand decreases so it is sent at once
    await entity.async_set_temperature(temperature=20)
    entity._set_now(now)
    await entity._send_regulated_temperature(force=True)
    assert under.last_sent_temperature == 20
    assert entity.regulated_target_temp == 20

    entity.remove_thermostat()


async def test_ramp_restarts_after_off(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """The ramp starts again each time the thermostat is switched on"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -0.5, 1.0))
    await start_heating(entity, now, 18, 21)
    assert await run_cycles(entity, now, 4) == [18.5, 19.5, 20.5, 21]
    now = now + timedelta(minutes=4 * CYCLE_MIN)

    await entity.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()
    assert entity._ramp_value is None

    # The room is now at 19
    await send_temperature_change_event(entity, 19, now)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()
    assert entity._underlyings[0].last_sent_temperature == 18.5

    entity.remove_thermostat()


async def test_ramp_sends_setpoint_before_mode(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """The start setpoint reaches the device before it is switched on"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -0.5, 1.0))
    await send_temperature_change_event(entity, 18, now)
    await entity.async_set_temperature(temperature=21)

    commands: list[tuple[str, float | str]] = []
    original_set_temperature = UnderlyingClimate.set_temperature
    original_set_hvac_mode = UnderlyingClimate.set_hvac_mode

    async def spy_set_temperature(self, temperature, *args, **kwargs):
        commands.append(("temperature", temperature))
        return await original_set_temperature(self, temperature, *args, **kwargs)

    async def spy_set_hvac_mode(self, hvac_mode, *args, **kwargs):
        commands.append(("hvac_mode", hvac_mode))
        return await original_set_hvac_mode(self, hvac_mode, *args, **kwargs)

    with patch.object(UnderlyingClimate, "set_temperature", spy_set_temperature), patch.object(UnderlyingClimate, "set_hvac_mode", spy_set_hvac_mode):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()

    assert commands[0] == ("temperature", 17.5)
    assert commands[1][0] == "hvac_mode"
    # Nothing sends the full target afterwards
    assert ("temperature", 21) not in commands

    entity.remove_thermostat()


async def test_ramp_not_started_by_underlying_tracking(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """A device switched on by the user is not given a start setpoint: it already runs"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -0.5, 1.0))
    await send_temperature_change_event(entity, 18, now)
    await entity.async_set_temperature(temperature=21)

    with patch.object(UnderlyingClimate, "set_temperature") as mock_set_temperature:
        # The mode change comes from the device
        entity.requested_state.set_hvac_mode(VThermHvacMode_HEAT)
        await entity.update_states(force=True, _command_cause=COMMAND_CAUSE_UNDERLYING_TRACKING)

    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert 17.5 not in [call.args[0] for call in mock_set_temperature.call_args_list]
    assert entity._ramp_value == 21

    entity.remove_thermostat()


async def test_ramp_restore_after_restart(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """After a restart the ramp resumes from its last position instead of starting again"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -0.5, 1.0))
    await send_temperature_change_event(entity, 18, now)
    await entity.async_set_temperature(temperature=21)

    entity.restore_specific_previous_state(State("climate.theoverclimatemockname", "heat", {"regulation_ramp_value": 19.5}))
    assert entity._ramp_restored_value == 19.5

    with patch.object(UnderlyingClimate, "set_temperature") as mock_set_temperature:
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)

    # The start setpoint (17.5) is not sent, the ramp goes on from the restored setpoint
    assert 17.5 not in [call.args[0] for call in mock_set_temperature.call_args_list]
    assert entity._ramp_value == 19.5
    assert entity._ramp_restored_value is None

    entity.remove_thermostat()


async def test_ramp_device_ignoring_setpoint_while_off(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """A device which drops the setpoint while it is off gets the start setpoint again once it is on, never the target"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -0.5, 1.0))
    await send_temperature_change_event(entity, 18, now)
    await entity.async_set_temperature(temperature=21)

    device_on = False
    accepted_setpoints: list[float] = []

    async def fake_service_call(self, domain, service, service_data=None, *args, **kwargs):
        nonlocal device_on
        if service == "set_hvac_mode":
            device_on = service_data["hvac_mode"] != "off"
        elif service == "set_temperature" and device_on:
            accepted_setpoints.append(service_data["temperature"])

    with patch.object(UnderlyingClimate, "hass_services_async_call", fake_service_call):
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await hass.async_block_till_done()
        # Some time later, for the delayed resend of the setpoint after the mode change
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
        await hass.async_block_till_done()

    assert accepted_setpoints
    assert set(accepted_setpoints) == {17.5}

    entity.remove_thermostat()


async def test_ramp_attributes(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate):
    """The ramp position is published, at the root so that it can be restored"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -0.5, 1.0))
    await start_heating(entity, now, 18, 21)
    entity.update_custom_attributes()

    attributes = entity.extra_state_attributes
    assert attributes["regulation_ramp_value"] == 17.5
    assert attributes["vtherm_over_climate"]["setpoint_ramp"] == {
        "is_active": True,
        "start_offset": -0.5,
        "max_step": 1.0,
        "ramp_value": 17.5,
    }

    entity.remove_thermostat()


async def test_ramp_step_not_below_regulation_step(hass: HomeAssistant, skip_send_event, fake_temp_sensor, fake_ext_temp_sensor, fake_underlying_climate, caplog):
    """A step lower than the rounding step would stall the ramp, so the rounding step is used"""
    entity, now = await create_ramp_thermostat(hass, ramp_config(HEAT_CONFIG, -0.5, 0.2))
    await start_heating(entity, now, 18, 21)

    with caplog.at_level(logging.WARNING):
        assert await run_cycles(entity, now, 2) == [18, 18.5]
    assert "lower than the regulation step" in caplog.text

    entity.remove_thermostat()


def test_ramp_schema_defaults():
    """The ramp is disabled by default, with a gentle start offset and a step of one degree"""
    data = STEP_THERMOSTAT_CLIMATE({CONF_UNDERLYING_LIST: ["climate.mock_climate"]})
    assert data[CONF_AUTO_REGULATION_RAMP] is False
    assert data[CONF_AUTO_REGULATION_RAMP_START_OFFSET] == -0.5
    assert data[CONF_AUTO_REGULATION_RAMP_MAX_STEP] == 1.0


def test_ramp_schema_validation():
    """The offset is signed, the step is not negative"""
    base = {CONF_UNDERLYING_LIST: ["climate.mock_climate"]}
    assert STEP_THERMOSTAT_CLIMATE(base | {CONF_AUTO_REGULATION_RAMP_START_OFFSET: 2.0})[CONF_AUTO_REGULATION_RAMP_START_OFFSET] == 2.0
    assert STEP_THERMOSTAT_CLIMATE(base | {CONF_AUTO_REGULATION_RAMP_START_OFFSET: -2.0})[CONF_AUTO_REGULATION_RAMP_START_OFFSET] == -2.0
    assert STEP_THERMOSTAT_CLIMATE(base | {CONF_AUTO_REGULATION_RAMP_MAX_STEP: 0})[CONF_AUTO_REGULATION_RAMP_MAX_STEP] == 0

    with pytest.raises(vol.Invalid):
        STEP_THERMOSTAT_CLIMATE(base | {CONF_AUTO_REGULATION_RAMP_MAX_STEP: -0.5})


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_config_flow_over_climate_ramp(hass: HomeAssistant, skip_hass_states_get):
    """The ramp options are stored by the over_climate config flow, with a signed offset"""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE})
    assert result["step_id"] == "menu"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "main"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "TheOverClimateMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor", CONF_TEMP_MIN: 15.0, CONF_TEMP_MAX: 30.0, CONF_STEP_TEMPERATURE: 0.1},
    )
    assert result["step_id"] == "menu"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "type"})
    assert result["step_id"] == "type"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_NONE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_AUTO_REGULATION_RAMP: True,
            CONF_AUTO_REGULATION_RAMP_START_OFFSET: -1.0,
            CONF_AUTO_REGULATION_RAMP_MAX_STEP: 0.5,
        },
    )
    assert result["step_id"] == "menu"
    assert result.get("errors") is None

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "presets"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_USE_PRESETS_CENTRAL_CONFIG: False})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "features"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_AUTO_START_STOP_FEATURE: False,
        },
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "advanced"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_USE_ADVANCED_CENTRAL_CONFIG: False})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.4,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.3,
            CONF_MANUAL_OVERRIDE_DURATION_MIN: 30,
        },
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"next_step_id": "finalize"})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_AUTO_REGULATION_RAMP] is True
    assert result["data"][CONF_AUTO_REGULATION_RAMP_START_OFFSET] == -1.0
    assert result["data"][CONF_AUTO_REGULATION_RAMP_MAX_STEP] == 0.5
