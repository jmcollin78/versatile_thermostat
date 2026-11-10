# pylint: disable=unused-argument, line-too-long, protected-access, redefined-outer-name, abstract-method
""" Test the Calendar scheduling feature manager """
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.setup import async_setup_component

from pytest_homeassistant.common import async_fire_time_changed

from custom_components.versatile_thermostat.config_flow import VersatileThermostatBaseConfigFlow
from custom_components.versatile_thermostat.feature_calendar_manager import (
    CALENDAR_STATE_EVENT,
    CALENDAR_STATE_IDLE,
    CALENDAR_STATE_PREHEAT,
    CalendarBlock,
    merge_events,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

CALENDAR_ENTITY_ID = "calendar.room"


class MockCalendar(CalendarEntity):
    """A calendar whose events are set by the test"""

    _attr_should_poll = False

    def __init__(self):
        self.entity_id = CALENDAR_ENTITY_ID
        self._attr_name = "Room"
        self.events: list[CalendarEvent] = []

    @property
    def event(self):
        return None

    async def async_get_events(self, hass, start_date, end_date):
        return [event for event in self.events if event.start_datetime_local < end_date and event.end_datetime_local > start_date]

    def set_available(self, available: bool):
        """Simulate a calendar which cannot be synchronized"""
        self._attr_available = available
        self.async_write_ha_state()


@pytest.fixture(autouse=True)
def wakeup():
    """The clock of the tests is simulated: the wake-up timers are only recorded"""
    with patch("custom_components.versatile_thermostat.feature_calendar_manager.async_track_point_in_time") as track:
        yield track


@pytest.fixture
async def calendar(hass: HomeAssistant) -> MockCalendar:
    """A calendar entity served by the real calendar integration"""
    assert await async_setup_component(hass, "calendar", {})
    mock_calendar = MockCalendar()
    await hass.data["calendar"].async_add_entities([mock_calendar])
    await hass.async_block_till_done()
    return mock_calendar


def at(hass: HomeAssistant, hour: int, minute: int = 0) -> datetime:
    """A time of the test day"""
    return datetime(2026, 1, 5, hour, minute, tzinfo=get_tz(hass))


def meeting(hass: HomeAssistant, start=(10, 0), end=(12, 0)) -> CalendarEvent:
    """An event of the test day"""
    return CalendarEvent(start=at(hass, *start), end=at(hass, *end), summary="Meeting")


def build_entry(extra: dict | None = None, unique_id="uniqueId") -> MockConfigEntry:
    """An over_switch VTherm following the calendar: comfort (21°) during the events, eco (17°) after, heating 3°/h"""
    data = {
        CONF_NAME: "TheOverSwitchMockName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 5,
        CONF_TEMP_MAX: 30,
        "eco_temp": 17,
        "comfort_temp": 21,
        "boost_temp": 23,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_USE_CALENDAR_FEATURE: True,
        CONF_CALENDAR_ENTITY: CALENDAR_ENTITY_ID,
        CONF_CALENDAR_EVENT_PRESET: VThermPreset.COMFORT,
        CONF_CALENDAR_END_PRESET: VThermPreset.ECO,
        CONF_CALENDAR_PREHEAT_GRADIENT: 3,
        CONF_CALENDAR_MAX_PREHEAT_MIN: 240,
        CONF_UNDERLYING_LIST: ["switch.mock_switch"],
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.01,
        CONF_MINIMAL_ACTIVATION_DELAY: 30,
        CONF_MINIMAL_DEACTIVATION_DELAY: 0,
        CONF_SAFETY_DELAY_MIN: 5,
        CONF_SAFETY_MIN_ON_PERCENT: 0.3,
    }
    data.update(extra or {})
    return MockConfigEntry(domain=DOMAIN, title="TheOverSwitchMockName", unique_id=unique_id, data=data)


async def setup_vtherm(hass: HomeAssistant, extra: dict | None = None, preset=VThermPreset.ECO, temperature=15) -> BaseThermostat:
    """Create the VTherm heating at 6:00 in a room at 15°: the comfort preset needs 2 hours"""
    entity: BaseThermostat = await create_thermostat(hass, build_entry(extra), "climate.theoverswitchmockname")
    assert entity
    entity._set_now(at(hass, 6))
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(preset)
    await send_temperature_change_event(entity, temperature, at(hass, 6))
    await move_to(entity, at(hass, 6))
    return entity


async def move_to(entity: BaseThermostat, now: datetime):
    """Move the clock and read the calendar as the timers do"""
    entity._set_now(now)
    await entity.calendar_manager._async_refresh()


def calendar_attributes(entity: BaseThermostat) -> dict:
    """The published attributes of the calendar manager"""
    return entity.extra_state_attributes["calendar_manager"]


def test_merge_events():
    """Overlapping and contiguous events are one block, empty events are ignored"""
    day = datetime(2026, 1, 5)

    def hour(value):
        return day + timedelta(hours=value)

    assert merge_events([(hour(14), hour(15)), (hour(8), hour(10)), (hour(9), hour(11)), (hour(11), hour(12)), (hour(13), hour(13))]) == [
        CalendarBlock(hour(8), hour(12)),
        CalendarBlock(hour(14), hour(15)),
    ]
    assert CalendarBlock(hour(8), hour(10)).overlaps(CalendarBlock(hour(9), hour(11)))
    assert not CalendarBlock(hour(8), hour(10)).overlaps(CalendarBlock(hour(10), hour(11)))


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_calendar_not_configured(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Without the feature the manager does nothing"""
    entity = await create_thermostat(hass, build_entry({CONF_USE_CALENDAR_FEATURE: False}), "climate.theoverswitchmockname")
    assert entity.calendar_manager.is_configured is False
    assert await entity.calendar_manager.refresh_state() is False
    assert entity.extra_state_attributes["is_calendar_configured"] is False
    assert "calendar_manager" not in entity.extra_state_attributes
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_preheat_event_and_end(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """The preheat starts 2 hours before the event (6° at 3°/h), holds whatever the temperature does and the end preset follows the event"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)
    manager = entity.calendar_manager

    assert manager.calendar_state == CALENDAR_STATE_IDLE
    assert entity.preset_mode == VThermPreset.ECO
    attributes = calendar_attributes(entity)
    assert attributes["is_calendar_available"] is True
    assert attributes["next_event_start"] == at(hass, 10).isoformat()
    assert attributes["preheat_start"] == at(hass, 8).isoformat()

    await move_to(entity, at(hass, 7, 59))
    assert manager.calendar_state == CALENDAR_STATE_IDLE

    await move_to(entity, at(hass, 8))
    assert manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == 21
    attributes = calendar_attributes(entity)
    assert attributes["event_start"] == at(hass, 10).isoformat()
    assert attributes["event_end"] == at(hass, 12).isoformat()
    assert attributes["estimated_ready_time"] == at(hass, 10).isoformat()

    # The room heats faster than predicted: the preheat is not released
    entity._set_now(at(hass, 8, 30))
    await send_temperature_change_event(entity, 20.9, at(hass, 8, 30))
    assert manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    await move_to(entity, at(hass, 8, 45))
    assert manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT

    await move_to(entity, at(hass, 10))
    assert manager.calendar_state == CALENDAR_STATE_EVENT
    assert manager.is_detected is True
    assert entity.preset_mode == VThermPreset.COMFORT

    await move_to(entity, at(hass, 12))
    assert manager.calendar_state == CALENDAR_STATE_IDLE
    assert manager.is_detected is False
    assert entity.preset_mode == VThermPreset.ECO
    assert entity.target_temperature == 17
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_preheat_starts_earlier_when_the_room_cools(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """A temperature change plans the preheat again without reading the calendar"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)

    entity._set_now(at(hass, 7))
    with patch.object(MockCalendar, "async_get_events") as get_events:
        await send_temperature_change_event(entity, 14, at(hass, 7))
        assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE
        assert calendar_attributes(entity)["preheat_start"] == at(hass, 7, 40).isoformat()

        await send_temperature_change_event(entity, 12, at(hass, 7))
        get_events.assert_not_called()

    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_event_appearing_too_late(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """An event known 30 minutes before its start is preheated at once and the room is late"""
    entity = await setup_vtherm(hass)
    await move_to(entity, at(hass, 9))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE

    calendar.events = [meeting(hass)]
    await move_to(entity, at(hass, 9, 30))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    assert calendar_attributes(entity)["estimated_ready_time"] == at(hass, 11, 30).isoformat()
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_preheat_is_capped(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """A very cold room does not start the preheat before the maximum preheat duration"""
    calendar.events = [meeting(hass, start=(10, 15), end=(11, 0))]
    entity = await setup_vtherm(hass, temperature=5)
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE
    assert calendar_attributes(entity)["preheat_start"] == at(hass, 6, 15).isoformat()
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.parametrize("extra", [{CONF_CALENDAR_PREHEAT_GRADIENT: 0}, {CONF_CALENDAR_MAX_PREHEAT_MIN: 0}])
async def test_no_preheat(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar, extra):
    """Without gradient or preheat duration the preset changes when the event starts"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass, extra)

    await move_to(entity, at(hass, 9, 59))
    assert calendar_attributes(entity)["preheat_start"] == at(hass, 10).isoformat()
    assert entity.preset_mode == VThermPreset.ECO
    await move_to(entity, at(hass, 10))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_EVENT
    assert entity.preset_mode == VThermPreset.COMFORT
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_no_preheat_when_off(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """A stopped VTherm is not started. It only gets the preset of the event"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)
    await entity.async_set_hvac_mode(VThermHvacMode_OFF)

    await move_to(entity, at(hass, 9))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE

    await move_to(entity, at(hass, 10))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_EVENT
    assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
    assert entity.requested_state.preset == VThermPreset.COMFORT
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_removed_event_is_released_after_one_read(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """A removed event keeps heating until it is still missing 15 minutes later"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)
    await move_to(entity, at(hass, 8))
    assert entity.preset_mode == VThermPreset.COMFORT

    calendar.events = []
    await move_to(entity, at(hass, 8, 5))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    assert calendar_attributes(entity)["missing_since"] == at(hass, 8, 5).isoformat()

    await move_to(entity, at(hass, 8, 19))
    assert entity.preset_mode == VThermPreset.COMFORT

    await move_to(entity, at(hass, 8, 20))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE
    assert entity.preset_mode == VThermPreset.ECO
    assert calendar_attributes(entity)["missing_since"] is None
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_event_missing_from_one_read_only(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """An event which comes back at the next read never stops the heating"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)
    await move_to(entity, at(hass, 8))

    calendar.events = []
    await move_to(entity, at(hass, 8, 5))
    assert calendar_attributes(entity)["missing_since"] is not None

    calendar.events = [meeting(hass)]
    await move_to(entity, at(hass, 8, 20))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    assert calendar_attributes(entity)["missing_since"] is None
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_unavailable_calendar_keeps_the_known_events(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """A calendar which cannot be read is not a removed event: the known event runs until its known end"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)

    calendar.set_available(False)
    await hass.async_block_till_done()
    await move_to(entity, at(hass, 8))
    assert calendar_attributes(entity)["is_calendar_available"] is False
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT

    await move_to(entity, at(hass, 11))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_EVENT
    assert entity.preset_mode == VThermPreset.COMFORT
    assert calendar_attributes(entity)["missing_since"] is None

    await move_to(entity, at(hass, 12))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE
    assert entity.preset_mode == VThermPreset.ECO
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_failing_calendar_read_keeps_the_known_events(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """An error of the calendar integration never breaks the schedule"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)

    with patch.object(MockCalendar, "async_get_events", side_effect=RuntimeError("boom")):
        await move_to(entity, at(hass, 8))
    assert calendar_attributes(entity)["is_calendar_available"] is False
    assert entity.preset_mode == VThermPreset.COMFORT
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_moved_event(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """An event moved onto its previous time span is followed. Moved further away, it is released then preheated again"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)
    await move_to(entity, at(hass, 8))

    calendar.events = [meeting(hass, start=(11, 0), end=(13, 0))]
    await move_to(entity, at(hass, 8, 30))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert calendar_attributes(entity)["event_start"] == at(hass, 11).isoformat()
    assert calendar_attributes(entity)["missing_since"] is None

    calendar.events = [meeting(hass, start=(13, 30), end=(14, 0))]
    await move_to(entity, at(hass, 9))
    assert entity.preset_mode == VThermPreset.COMFORT
    await move_to(entity, at(hass, 9, 15))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE
    assert entity.preset_mode == VThermPreset.ECO
    assert calendar_attributes(entity)["preheat_start"] == at(hass, 11, 30).isoformat()

    await move_to(entity, at(hass, 11, 30))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_consecutive_events_are_one_block(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """The end preset is not applied between two contiguous events"""
    calendar.events = [meeting(hass, start=(7, 0), end=(8, 0)), meeting(hass, start=(8, 0), end=(9, 0))]
    entity = await setup_vtherm(hass)
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT

    await move_to(entity, at(hass, 8))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_EVENT
    assert entity.preset_mode == VThermPreset.COMFORT
    assert calendar_attributes(entity)["event_end"] == at(hass, 9).isoformat()

    await move_to(entity, at(hass, 9))
    assert entity.preset_mode == VThermPreset.ECO
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_all_day_event(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """An all-day event runs from midnight to midnight"""
    calendar.events = [CalendarEvent(start=date(2026, 1, 5), end=date(2026, 1, 6), summary="Open day")]
    entity = await setup_vtherm(hass)
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_EVENT
    attributes = calendar_attributes(entity)
    assert attributes["event_start"] == at(hass, 0).isoformat()
    assert attributes["event_end"] == (at(hass, 0) + timedelta(days=1)).isoformat()
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_return_to_previous_preset(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """With the previous option the preset active before the event is restored when the event ends"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass, {CONF_CALENDAR_END_PRESET: CALENDAR_END_PRESET_PREVIOUS}, preset=VThermPreset.BOOST, temperature=17)
    assert calendar_attributes(entity)["end_preset"] == CALENDAR_END_PRESET_PREVIOUS

    await move_to(entity, at(hass, 10))
    assert entity.preset_mode == VThermPreset.COMFORT
    assert calendar_attributes(entity)["previous_preset"] == VThermPreset.BOOST

    await move_to(entity, at(hass, 12))
    assert entity.preset_mode == VThermPreset.BOOST
    assert calendar_attributes(entity)["previous_preset"] is None
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_change_is_kept_until_the_event_ends(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """The presets are only applied on transitions: a manual change wins until the next one"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)
    await move_to(entity, at(hass, 8))
    assert entity.preset_mode == VThermPreset.COMFORT

    await entity.async_set_preset_mode(VThermPreset.BOOST)
    await move_to(entity, at(hass, 9))
    await send_temperature_change_event(entity, 18, at(hass, 9))
    await move_to(entity, at(hass, 10))
    assert entity.preset_mode == VThermPreset.BOOST

    await move_to(entity, at(hass, 12))
    assert entity.preset_mode == VThermPreset.ECO
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_timed_preset_keeps_the_priority(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """A running timed preset is not interrupted and returns to the scheduled preset when it ends"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass, {CONF_CALENDAR_END_PRESET: CALENDAR_END_PRESET_PREVIOUS})

    await entity.timed_preset_manager.set_timed_preset(VThermPreset.BOOST, 600)
    assert entity.preset_mode == VThermPreset.BOOST

    await move_to(entity, at(hass, 8))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.timed_preset_manager.original_preset == VThermPreset.COMFORT
    assert calendar_attributes(entity)["previous_preset"] == VThermPreset.ECO

    await move_to(entity, at(hass, 12))
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.timed_preset_manager.original_preset == VThermPreset.ECO

    await entity.timed_preset_manager.cancel_timed_preset()
    assert entity.preset_mode == VThermPreset.ECO
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_unavailable_event_preset(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """A preset which is not configured on the VTherm is not applied"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass, {CONF_CALENDAR_EVENT_PRESET: VThermPreset.BOOST, "boost_temp": 0})

    await move_to(entity, at(hass, 10))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_EVENT
    assert entity.preset_mode == VThermPreset.ECO
    entity.remove_thermostat()


async def restart_during_preheat(hass: HomeAssistant, calendar: MockCalendar, restart_time: datetime) -> BaseThermostat:
    """Stop a VTherm preheating in an already warm room, with boost as previous preset, and start it again later"""
    extra = {CONF_CALENDAR_END_PRESET: CALENDAR_END_PRESET_PREVIOUS}
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass, extra, preset=VThermPreset.BOOST, temperature=17)
    await move_to(entity, at(hass, 8, 40))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    await send_temperature_change_event(entity, 21, at(hass, 9))

    stored_attributes = dict(entity.extra_state_attributes)
    entity.remove_thermostat()
    await hass.config_entries.async_remove(hass.config_entries.async_entries(DOMAIN)[0].entry_id)
    await hass.async_block_till_done()

    old_state = MagicMock()
    old_state.state = HVACMode.HEAT
    old_state.attributes = stored_attributes

    with (
        patch("homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state", return_value=old_state),
        patch("custom_components.versatile_thermostat.const.NowClass.get_now", return_value=restart_time),
    ):
        entity = await create_thermostat(hass, build_entry(extra, unique_id="uniqueId2"), "climate.theoverswitchmockname")
        await wait_for_local_condition(lambda: entity.is_ready is True)
    return entity


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_restart_during_preheat(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """After a restart in a room which is already warm, the preheat goes on and the previous preset is still known"""
    entity = await restart_during_preheat(hass, calendar, at(hass, 9))
    entity._set_now(at(hass, 9))
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT

    await send_temperature_change_event(entity, 21, at(hass, 9))
    await move_to(entity, at(hass, 9))

    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT

    await move_to(entity, at(hass, 12))
    assert entity.preset_mode == VThermPreset.BOOST
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_restart_after_the_event(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """An event which ended while Home Assistant was stopped is ended at startup"""
    entity = await restart_during_preheat(hass, calendar, at(hass, 13))

    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE
    assert entity.preset_mode == VThermPreset.BOOST
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_restore_ignores_another_calendar_and_corrupt_values(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """A stored block of another calendar or with corrupt values is not restored"""
    entity = await setup_vtherm(hass)
    manager = entity.calendar_manager
    stored = {"calendar_entity_id": CALENDAR_ENTITY_ID, "event_start": at(hass, 10).isoformat(), "event_end": at(hass, 12).isoformat(), "previous_preset": "boost"}

    for attributes in ({**stored, "calendar_entity_id": "calendar.other"}, {**stored, "event_end": "not a date"}, {**stored, "event_start": None}):
        old_state = MagicMock()
        old_state.attributes = {"calendar_manager": attributes}
        manager.restore_state(old_state)
        assert manager.is_detected is False

    old_state.attributes = {"calendar_manager": stored}
    manager.restore_state(old_state)
    assert manager.is_detected is True
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_wakeup_is_planned_at_the_next_transition(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar, wakeup):
    """The calendar is read again at the preheat start, at the end of the grace period and at the event end"""
    calendar.events = [meeting(hass)]
    entity = await setup_vtherm(hass)
    assert wakeup.call_args.args[2] == at(hass, 8)

    await move_to(entity, at(hass, 8))
    assert wakeup.call_args.args[2] == at(hass, 12)

    calendar.events = []
    await move_to(entity, at(hass, 8, 5))
    assert wakeup.call_args.args[2] == at(hass, 8, 20)

    wakeup.reset_mock()
    await move_to(entity, at(hass, 8, 20))
    wakeup.assert_not_called()
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_timers_follow_the_schedule(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar, wakeup):
    """With the real timers, the wake-up starts the preheat and the periodic read releases a removed event"""
    wakeup.side_effect = async_track_point_in_time
    now = datetime.now(get_tz(hass))
    calendar.events = [CalendarEvent(start=now + timedelta(hours=3), end=now + timedelta(hours=4), summary="Meeting")]

    entity: BaseThermostat = await create_thermostat(hass, build_entry({CONF_SAFETY_DELAY_MIN: 600}), "climate.theoverswitchmockname")
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.ECO)
    await send_temperature_change_event(entity, 15, now)
    await entity.calendar_manager._async_refresh()
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE

    async def elapse(minutes: int):
        entity._set_now(now + timedelta(minutes=minutes))
        async_fire_time_changed(hass, now + timedelta(minutes=minutes))
        await hass.async_block_till_done()

    await elapse(59)
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE
    await elapse(61)
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT

    calendar.events = []
    await elapse(76)
    assert calendar_attributes(entity)["missing_since"] is not None
    assert entity.preset_mode == VThermPreset.COMFORT
    await elapse(92)
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_IDLE
    assert entity.preset_mode == VThermPreset.ECO
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_calendar_change_is_read_at_once(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch, calendar):
    """A state change of the calendar entity triggers a read"""
    entity = await setup_vtherm(hass)
    entity._set_now(at(hass, 9, 30))

    calendar.events = [meeting(hass)]
    hass.states.async_set(CALENDAR_ENTITY_ID, "off", {"message": "Meeting"})
    await hass.async_block_till_done()
    assert entity.calendar_manager.calendar_state == CALENDAR_STATE_PREHEAT
    assert entity.preset_mode == VThermPreset.COMFORT
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_calendar_config_flow(hass: HomeAssistant, skip_hass_states_get):
    """The calendar step is offered once the feature is selected and its values are removed with the feature"""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH})
    assert "calendar" not in result["menu_options"]

    async def step(name: str, user_input: dict):
        result = await hass.config_entries.flow.async_configure(flow_id, user_input={"next_step_id": name})
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == name
        return await hass.config_entries.flow.async_configure(flow_id, user_input=user_input)

    flow_id = result["flow_id"]
    result = await step("features", {CONF_USE_CALENDAR_FEATURE: True})
    assert "calendar" in result["menu_options"]
    assert "configuration_not_complete" in result["menu_options"]

    result = await step("calendar", {CONF_CALENDAR_ENTITY: CALENDAR_ENTITY_ID, CONF_CALENDAR_END_PRESET: CALENDAR_END_PRESET_PREVIOUS, CONF_CALENDAR_PREHEAT_GRADIENT: 3})
    assert result["type"] == FlowResultType.MENU

    flow = hass.config_entries.flow._progress[flow_id]
    assert flow._infos[CONF_CALENDAR_ENTITY] == CALENDAR_ENTITY_ID
    assert flow._infos[CONF_CALENDAR_EVENT_PRESET] == VThermPreset.COMFORT
    assert flow._infos[CONF_CALENDAR_END_PRESET] == CALENDAR_END_PRESET_PREVIOUS
    assert flow._infos[CONF_CALENDAR_PREHEAT_GRADIENT] == 3
    assert flow._infos[CONF_CALENDAR_MAX_PREHEAT_MIN] == DEFAULT_CALENDAR_MAX_PREHEAT_MIN

    result = await step("features", {CONF_USE_CALENDAR_FEATURE: False})
    assert "calendar" not in result["menu_options"]
    await VersatileThermostatBaseConfigFlow.async_step_finalize(flow, None)
    assert not any(key.startswith("calendar") or key == CONF_USE_CALENDAR_FEATURE for key in flow._infos)
