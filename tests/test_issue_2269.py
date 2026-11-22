# pylint: disable=protected-access, unused-argument, line-too-long
"""Reproduction of #2269: an over_switch VTherm turned off and back on before the relay
confirms the turn_off.

The relay is a real switch entity that reports its new state only when the test says so,
like a Zigbee relay that confirms a command a few seconds later.
"""

from datetime import datetime
from typing import cast
from unittest.mock import MagicMock, patch


from custom_components.versatile_thermostat.cycle_scheduler import CycleScheduler
from custom_components.versatile_thermostat.thermostat_switch import ThermostatOverSwitch
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .test_cycle_scheduler import make_hass, make_thermostat, make_underlying


class SlowRelay(MockSwitch):
    """A switch that receives commands at once but reports its state only on confirm()."""

    def __init__(self, hass):
        super().__init__(hass, "mock_switch", "theMockedSwitch")
        self.commands: list[str] = []

    async def async_turn_on(self, **kwargs):
        self.commands.append("on")

    async def async_turn_off(self, **kwargs):
        self.commands.append("off")

    def confirm(self):
        """The relay reports the last command it received."""
        self._attr_is_on = self.commands[-1] == "on"
        self.async_write_ha_state()


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """An over_switch VTherm with keep-alive, as in the issue."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 30,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_HEATER_KEEP_ALIVE: 126,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.1,
        },
    )


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_quick_off_on_before_the_relay_confirms_turns_the_relay_back_on(hass: HomeAssistant, config_entry):
    """Off then heat before the relay confirms the turn_off: the new cycle's ON part turns the relay back on."""
    relay = SlowRelay(hass)
    await register_mock_entity(hass, relay, SWITCH_DOMAIN)
    thermostat = cast(ThermostatOverSwitch, await create_thermostat(hass, config_entry, "climate.theoverswitchmockname"))
    under = thermostat.underlying_entities[0]
    now = datetime.now(get_tz(hass))

    # 1. Heat with a partial cycle: the relay gets turn_on and confirms it
    await thermostat.async_set_hvac_mode(VThermHvacMode_HEAT)
    await thermostat.async_set_temperature(temperature=20)
    await send_ext_temperature_change_event(thermostat, 8, now)
    await send_temperature_change_event(thermostat, 18.5, now)
    assert 0 < thermostat.on_percent < 1
    assert relay.commands == ["on"]
    relay.confirm()
    await hass.async_block_till_done()
    assert under.is_device_active is True

    # 2. Off: the relay gets turn_off but does not confirm it yet
    await thermostat.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()
    assert relay.commands[-1] == "off"
    assert under.is_device_active is True  # stale: HA still shows "on"
    before = len(relay.commands)

    # 3. Heat again, before the relay confirms: a new cycle starts in its ON part
    await thermostat.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()
    assert under._should_be_on is True  # the scheduler believes the ON part is running

    # 4. The turn_off lands late
    relay.confirm()
    await hass.async_block_till_done()

    # 5. The keep-alive must hold the relay in the cycle's ON part
    await under._keep_alive_callback()
    await hass.async_block_till_done()

    assert relay.commands[before:] == ["on", "on"], (
        f"commands after the new cycle: {relay.commands[before:]}, " f"is_on_part_running={under.is_on_part_running}, should_be_on={under._should_be_on}"
    )

    thermostat.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_off_before_the_relay_confirms_a_turn_on_turns_the_relay_off(hass: HomeAssistant, config_entry):
    """The mirror case: VTherm goes off before the relay confirms a turn_on. The relay is turned off, and stays off."""
    relay = SlowRelay(hass)
    await register_mock_entity(hass, relay, SWITCH_DOMAIN)
    thermostat = cast(ThermostatOverSwitch, await create_thermostat(hass, config_entry, "climate.theoverswitchmockname"))
    under = thermostat.underlying_entities[0]
    now = datetime.now(get_tz(hass))

    # 1. Heat with a partial cycle: the relay gets turn_on but does not confirm it yet
    await thermostat.async_set_hvac_mode(VThermHvacMode_HEAT)
    await thermostat.async_set_temperature(temperature=20)
    await send_ext_temperature_change_event(thermostat, 8, now)
    await send_temperature_change_event(thermostat, 18.5, now)
    assert relay.commands == ["on"]
    assert under.is_device_active is False  # stale: HA still shows "off"

    # 2. Off, before the relay confirms: the relay gets turn_off
    await thermostat.async_set_hvac_mode(VThermHvacMode_OFF)
    await hass.async_block_till_done()
    assert relay.commands[-1] == "off"

    # 3. The relay reports its last command, and the keep-alive holds it off
    relay.confirm()
    await hass.async_block_till_done()
    await under._keep_alive_callback()
    await hass.async_block_till_done()
    assert relay.commands[-1] == "off"
    assert relay.is_on is False

    thermostat.remove_thermostat()


@patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later", return_value=MagicMock())
async def test_first_tick_turns_on_a_relay_commanded_off_but_still_shown_on(mock_call_later):
    """Scheduler level: an underlying shown on, but commanded off, gets turn_on on the first tick."""
    relay = make_underlying("R1", active=True)  # HA still shows "on"
    relay.is_on_part_running = False  # the last command was turn_off
    scheduler = CycleScheduler(make_hass(), make_thermostat(), [relay], 1800)

    await scheduler.start_cycle(VThermHvacMode_HEAT, 0.33, force=True)

    relay.turn_on.assert_awaited_once()


@patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later", return_value=MagicMock())
async def test_first_tick_turns_off_a_relay_commanded_on_but_still_shown_off(mock_call_later):
    """Scheduler level, the mirror case: an underlying in its OFF part, shown off, but commanded on, gets turn_off on the first tick."""
    first = make_underlying("R1")
    second = make_underlying("R2", active=False)  # HA still shows "off"
    second.is_on_part_running = True  # the last command was turn_on
    scheduler = CycleScheduler(make_hass(), make_thermostat(), [first, second], 1800)

    # With two underlyings, the second starts its ON part at mid-cycle: it is in its OFF part at t=0
    await scheduler.start_cycle(VThermHvacMode_HEAT, 0.2, force=True)

    second.turn_off.assert_awaited_once()
