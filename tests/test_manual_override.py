# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the manual override with automatic revert to the previous preset (issue #1875) """
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.feature_timed_preset_manager import FeatureTimedPresetManager
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


def build_over_switch_entry(extra: dict | None = None, unique_id="uniqueId") -> MockConfigEntry:
    """Build an over_switch VTherm config entry with presets"""
    data = {
        CONF_NAME: "TheOverSwitchMockName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
        CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
        CONF_CYCLE_MIN: 5,
        CONF_TEMP_MIN: 15,
        CONF_TEMP_MAX: 30,
        "eco_temp": 17,
        "comfort_temp": 19,
        "boost_temp": 21,
        CONF_USE_WINDOW_FEATURE: False,
        CONF_USE_MOTION_FEATURE: False,
        CONF_USE_POWER_FEATURE: False,
        CONF_USE_PRESENCE_FEATURE: False,
        CONF_UNDERLYING_LIST: ["switch.mock_switch"],
        CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
        CONF_TPI_COEF_INT: 0.3,
        CONF_TPI_COEF_EXT: 0.01,
        CONF_MINIMAL_ACTIVATION_DELAY: 30,
        CONF_MINIMAL_DEACTIVATION_DELAY: 0,
        CONF_SAFETY_DELAY_MIN: 5,
        CONF_SAFETY_MIN_ON_PERCENT: 0.3,
    }
    if extra:
        data.update(extra)
    return MockConfigEntry(domain=DOMAIN, title="TheOverSwitchMockName", unique_id=unique_id, data=data)


#
# Task 1 - configuration
#
@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_duration_default_zero(hass: HomeAssistant, skip_hass_states_is_state):
    """A VTherm without the option has the manual override disabled"""
    entity: BaseThermostat = await create_thermostat(hass, build_over_switch_entry(), "climate.theoverswitchmockname")
    assert entity
    assert entity.timed_preset_manager.manual_override_duration_min == 0
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_duration_specific(hass: HomeAssistant, skip_hass_states_is_state):
    """A VTherm with its own advanced configuration uses its own duration"""
    entry = build_over_switch_entry({CONF_USE_ADVANCED_CENTRAL_CONFIG: False, CONF_MANUAL_OVERRIDE_DURATION_MIN: 20})
    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity
    assert entity.timed_preset_manager.manual_override_duration_min == 20
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_override_duration_from_central(hass: HomeAssistant, skip_hass_states_is_state):
    """A VTherm using the central advanced configuration takes the central duration"""
    await create_central_config(hass, FULL_CENTRAL_CONFIG | {CONF_MANUAL_OVERRIDE_DURATION_MIN: 45})

    entry = build_over_switch_entry({CONF_USE_ADVANCED_CENTRAL_CONFIG: True, CONF_MANUAL_OVERRIDE_DURATION_MIN: 20})
    entity: BaseThermostat = await create_thermostat(hass, entry, "climate.theoverswitchmockname")
    assert entity
    assert entity.timed_preset_manager.manual_override_duration_min == 45
    entity.remove_thermostat()


#
# Task 2 - FeatureTimedPresetManager
#
NOW = datetime(2026, 1, 2, 10, 0, 0)


def build_manager(hass, preset=VThermPreset.COMFORT, duration=60):
    """Build a manager on a mocked VTherm whose requested_state keeps the preset set"""
    vtherm = MagicMock()
    vtherm.name = "test_vtherm"
    vtherm.vtherm_preset_modes = [VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.BOOST]
    vtherm.requested_state = MagicMock()
    vtherm.requested_state.preset = preset

    def _set_preset(new_preset):
        vtherm.requested_state.preset = new_preset

    vtherm.requested_state.set_preset = MagicMock(side_effect=_set_preset)
    vtherm.requested_state.force_changed = MagicMock()
    vtherm.update_states = AsyncMock()
    vtherm.update_custom_attributes = MagicMock()
    vtherm.send_event = MagicMock()
    vtherm.now = NOW

    manager = FeatureTimedPresetManager(vtherm, hass)
    manager.post_init({CONF_MANUAL_OVERRIDE_DURATION_MIN: duration})
    return vtherm, manager


def events_data(vtherm):
    """Return the data of all the events sent"""
    return [c[1]["data"] for c in vtherm.send_event.call_args_list]


async def test_start_manual_override_from_preset(hass: HomeAssistant):
    """Case 1: a manual change from a preset starts a manual override"""
    vtherm, manager = build_manager(hass)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time") as mock_track:
        assert await manager.start_manual_override(VThermPreset.COMFORT) is True

    assert manager.is_timed_preset_active is True
    assert manager.is_manual_override is True
    assert manager.timed_preset == VThermPreset.NONE
    assert manager._original_preset == VThermPreset.COMFORT
    assert manager.timed_preset_end_time == NOW + timedelta(minutes=60)
    assert vtherm.requested_state.preset == VThermPreset.NONE
    assert mock_track.call_args[0][2] == NOW + timedelta(minutes=60)
    vtherm.update_states.assert_called_with(force=True)


async def test_start_manual_override_disabled_or_no_preset(hass: HomeAssistant):
    """Case 4 and duration 0: nothing happens"""
    vtherm, manager = build_manager(hass, duration=0)
    assert await manager.start_manual_override(VThermPreset.COMFORT) is False
    assert manager.is_timed_preset_active is False

    vtherm, manager = build_manager(hass, preset=VThermPreset.NONE, duration=60)
    assert await manager.start_manual_override(VThermPreset.NONE) is False
    assert await manager.start_manual_override(None) is False
    assert manager.is_timed_preset_active is False
    vtherm.requested_state.set_preset.assert_not_called()
    vtherm.send_event.assert_not_called()


async def test_manual_override_restart_timer(hass: HomeAssistant):
    """Case 2: a new manual change restarts the timer and keeps the original preset"""
    vtherm, manager = build_manager(hass)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time"):
        await manager.start_manual_override(VThermPreset.COMFORT)
        vtherm.now = NOW + timedelta(minutes=10)
        # the requested preset is now none, as set by the first override
        assert await manager.start_manual_override(VThermPreset.NONE) is True

    assert manager.timed_preset_end_time == NOW + timedelta(minutes=70)
    assert manager._original_preset == VThermPreset.COMFORT
    assert manager.is_manual_override is True


async def test_manual_override_expiry_restores_original(hass: HomeAssistant):
    """Case 1: at expiry the original preset is restored"""
    vtherm, manager = build_manager(hass)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time"):
        await manager.start_manual_override(VThermPreset.COMFORT)

    vtherm.now = NOW + timedelta(minutes=61)
    assert await manager.refresh_state() is False

    assert vtherm.requested_state.preset == VThermPreset.COMFORT
    assert manager.is_timed_preset_active is False
    assert manager.is_manual_override is False
    assert manager._resume_preset is None
    assert manager._resume_end_time is None
    end_event = events_data(vtherm)[-1]
    assert end_event["type"] == "end"
    assert end_event["manual_override"] is True
    assert end_event["restored_preset"] == str(VThermPreset.COMFORT)


async def test_manual_override_over_timed_preset_resumes(hass: HomeAssistant):
    """Case 3a: the interrupted timed preset is resumed until its own end time"""
    vtherm, manager = build_manager(hass, preset=VThermPreset.ECO)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time") as mock_track:
        await manager.set_timed_preset(VThermPreset.BOOST, 120)
        boost_end = NOW + timedelta(minutes=120)

        vtherm.now = NOW + timedelta(minutes=30)
        assert await manager.start_manual_override(VThermPreset.BOOST) is True
        assert manager._resume_preset == VThermPreset.BOOST
        assert manager._resume_end_time == boost_end
        assert manager._original_preset == VThermPreset.ECO
        assert manager.timed_preset == VThermPreset.NONE

        vtherm.now = NOW + timedelta(minutes=91)
        await manager.refresh_state()

        assert manager.is_timed_preset_active is True
        assert manager.timed_preset == VThermPreset.BOOST
        assert manager.timed_preset_end_time == boost_end
        assert manager._original_preset == VThermPreset.ECO
        assert manager.is_manual_override is False
        assert manager._resume_preset is None
        assert vtherm.requested_state.preset == VThermPreset.BOOST
        assert mock_track.call_args[0][2] == boost_end

    data = events_data(vtherm)
    assert data[-2]["type"] == "end" and data[-2]["manual_override"] is True
    assert data[-2]["restored_preset"] == str(VThermPreset.BOOST)
    assert data[-1]["type"] == "start" and data[-1]["manual_override"] is False
    assert data[-1]["preset"] == str(VThermPreset.BOOST)


async def test_manual_override_over_timed_preset_expired_resume(hass: HomeAssistant):
    """Case 3b: the interrupted timed preset ended during the override, the original preset is restored"""
    vtherm, manager = build_manager(hass, preset=VThermPreset.ECO)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time"):
        await manager.set_timed_preset(VThermPreset.BOOST, 30)
        vtherm.now = NOW + timedelta(minutes=10)
        await manager.start_manual_override(VThermPreset.BOOST)

        vtherm.now = NOW + timedelta(minutes=71)
        await manager.refresh_state()

    assert manager.is_timed_preset_active is False
    assert vtherm.requested_state.preset == VThermPreset.ECO


async def test_set_timed_preset_replaces_manual_override(hass: HomeAssistant):
    """Case 6: a timed preset set during the override replaces it"""
    vtherm, manager = build_manager(hass)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time"):
        await manager.start_manual_override(VThermPreset.COMFORT)
        assert await manager.set_timed_preset(VThermPreset.BOOST, 30) is True

    assert manager.is_manual_override is False
    assert manager._resume_preset is None
    assert manager.timed_preset == VThermPreset.BOOST
    assert manager._original_preset == VThermPreset.COMFORT


async def test_cancel_timed_preset_during_manual_override(hass: HomeAssistant):
    """Case 7: cancel during the override goes back to the original preset, never resumes"""
    vtherm, manager = build_manager(hass, preset=VThermPreset.ECO)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time"):
        await manager.set_timed_preset(VThermPreset.BOOST, 120)
        await manager.start_manual_override(VThermPreset.BOOST)
        assert await manager.cancel_timed_preset() is True

    assert manager.is_timed_preset_active is False
    assert manager._resume_preset is None
    assert vtherm.requested_state.preset == VThermPreset.ECO


async def test_cancel_manual_override_without_revert(hass: HomeAssistant):
    """Case 5 helper: the override is dropped and the requested preset is untouched"""
    vtherm, manager = build_manager(hass)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time"):
        await manager.start_manual_override(VThermPreset.COMFORT)
    vtherm.requested_state.set_preset(VThermPreset.ECO)

    manager.cancel_manual_override_without_revert()

    assert manager.is_timed_preset_active is False
    assert manager.is_manual_override is False
    assert vtherm.requested_state.preset == VThermPreset.ECO
    assert events_data(vtherm)[-1]["cause"] == "preset_selected"


async def test_manual_override_attributes_and_events(hass: HomeAssistant):
    """The attributes and the start event expose the manual override"""
    vtherm, manager = build_manager(hass)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time"):
        await manager.start_manual_override(VThermPreset.COMFORT)

    attrs = {}
    manager.add_custom_attributes(attrs)
    tpm = attrs["timed_preset_manager"]
    assert tpm["is_active"] is True
    assert tpm["is_manual_override"] is True
    assert tpm["preset"] == str(VThermPreset.NONE)
    assert tpm["original_preset"] == str(VThermPreset.COMFORT)
    assert tpm["resume_preset"] is None
    assert tpm["resume_end_time"] is None

    start_event = events_data(vtherm)[-1]
    assert start_event["type"] == "start"
    assert start_event["manual_override"] is True
    assert start_event["original_preset"] == str(VThermPreset.COMFORT)


async def test_restore_manual_override_remaining(hass: HomeAssistant):
    """Case 8: an active override is restored with its resume record"""
    vtherm, manager = build_manager(hass)
    end_time = NOW + timedelta(minutes=30)
    resume_end = NOW + timedelta(minutes=90)
    old_state = MagicMock()
    old_state.attributes = {
        "timed_preset_manager": {
            "is_active": True,
            "preset": str(VThermPreset.NONE),
            "original_preset": str(VThermPreset.ECO),
            "end_time": end_time.isoformat(),
            "remaining_time_min": 30,
            "is_manual_override": True,
            "resume_preset": str(VThermPreset.BOOST),
            "resume_end_time": resume_end.isoformat(),
        }
    }
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time") as mock_track:
        manager.restore_state(old_state)
        assert mock_track.call_args[0][2] == end_time

    assert manager.is_manual_override is True
    assert manager.timed_preset == VThermPreset.NONE
    assert manager._resume_preset == VThermPreset.BOOST
    assert manager._resume_end_time == resume_end


async def test_restore_manual_override_expired_with_stale_resume(hass: HomeAssistant):
    """Case 8 / review focus 3: expired override with a stale resume record restores the original preset"""
    vtherm, manager = build_manager(hass, preset=VThermPreset.NONE)
    old_state = MagicMock()
    old_state.attributes = {
        "timed_preset_manager": {
            "is_active": True,
            "preset": str(VThermPreset.NONE),
            "original_preset": str(VThermPreset.ECO),
            "end_time": (NOW - timedelta(minutes=10)).isoformat(),
            "remaining_time_min": 0,
            "is_manual_override": True,
            "resume_preset": str(VThermPreset.BOOST),
            "resume_end_time": (NOW - timedelta(minutes=5)).isoformat(),
        }
    }
    manager.restore_state(old_state)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time"):
        await manager.refresh_state()

    assert manager.is_timed_preset_active is False
    assert vtherm.requested_state.preset == VThermPreset.ECO


#
# Task 3 - trigger from manual temperature changes
#
from datetime import timezone  # pylint: disable=wrong-import-position,wrong-import-order

# Integration tests need an aware datetime in the future, so that the real timers never fire during the test
NOW_TZ = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
OVERRIDE_60 = {CONF_USE_ADVANCED_CENTRAL_CONFIG: False, CONF_MANUAL_OVERRIDE_DURATION_MIN: 60}


async def setup_vtherm_in_comfort(hass, extra: dict | None = None) -> BaseThermostat:
    """Create an over_switch VTherm in heat / comfort (19°) with the given extra config"""
    entity: BaseThermostat = await create_thermostat(hass, build_over_switch_entry(extra), "climate.theoverswitchmockname")
    assert entity
    entity._set_now(NOW_TZ)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == 19
    return entity


async def expire_override(entity: BaseThermostat, minutes: float):
    """Move the clock and let the timed preset manager end the expired override"""
    entity._set_now(NOW_TZ + timedelta(minutes=minutes))
    await entity.timed_preset_manager.refresh_state()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_set_temperature_duration_zero_unchanged(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Duration 0: a manual change behaves as before (preset none forever)"""
    entity = await setup_vtherm_in_comfort(hass)
    await entity.async_set_temperature(temperature=23)
    assert entity.target_temperature == 23
    assert entity.preset_mode == VThermPreset.NONE
    assert entity.timed_preset_manager.is_timed_preset_active is False
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_set_temperature_starts_override_and_reverts(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Case 1: the manual temperature applies, then the comfort preset comes back"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60)
    await entity.async_set_temperature(temperature=23)
    assert entity.target_temperature == 23
    assert entity.preset_mode == VThermPreset.NONE
    assert entity.timed_preset_manager.is_manual_override is True

    await expire_override(entity, 61)
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == 19
    assert entity.timed_preset_manager.is_timed_preset_active is False
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_set_temperature_no_override_without_preset(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Case 4: no preset before the change, no override"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60)
    await entity.async_set_preset_mode(VThermPreset.NONE)
    await entity.async_set_temperature(temperature=23)
    assert entity.target_temperature == 23
    assert entity.preset_mode == VThermPreset.NONE
    assert entity.timed_preset_manager.is_timed_preset_active is False
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_select_preset_cancels_manual_override(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Case 5: a preset selected during the override applies and is not reverted later"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60)
    await entity.async_set_temperature(temperature=23)
    await entity.async_set_preset_mode(VThermPreset.ECO)
    assert entity.preset_mode == VThermPreset.ECO
    assert entity.target_temperature == 17
    assert entity.timed_preset_manager.is_timed_preset_active is False

    await expire_override(entity, 61)
    assert entity.preset_mode == VThermPreset.ECO
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_set_temperature_locked_no_override(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """A locked VTherm ignores the manual change and starts no override"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60 | {CONF_LOCK_USERS: True, CONF_LOCK_AUTOMATIONS: True})
    entity.lock_manager.change_lock_state(True)
    await entity.async_set_temperature(temperature=23)
    assert entity.target_temperature == 19
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.timed_preset_manager.is_timed_preset_active is False
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_override_when_hvac_off(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Review focus 1: a change while off starts the override, the preset is back for the next turn on"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60)
    await entity.async_set_hvac_mode(VThermHvacMode_OFF)
    await entity.async_set_temperature(temperature=23)
    assert entity.timed_preset_manager.is_manual_override is True

    await expire_override(entity, 61)
    assert entity.requested_state.preset == VThermPreset.COMFORT
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == 19
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_repeated_set_temperature_keeps_original(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Review focus 5: repeated changes restart the timer and never lose the original preset"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60)
    for i, temp in enumerate([22, 23, 24]):
        entity._set_now(NOW_TZ + timedelta(minutes=5 * i))
        await entity.async_set_temperature(temperature=temp)

    tpm = entity.timed_preset_manager
    assert tpm._original_preset == VThermPreset.COMFORT
    assert tpm.timed_preset_end_time == NOW_TZ + timedelta(minutes=70)
    assert entity.target_temperature == 24

    await expire_override(entity, 71)
    assert entity.preset_mode == VThermPreset.COMFORT
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_override_during_timed_preset_resumes(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Case 3a end to end: the manual change applies during a timed boost, then boost resumes"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60)
    await entity.service_set_timed_preset("boost", 120)
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 21

    entity._set_now(NOW_TZ + timedelta(minutes=10))
    await entity.async_set_temperature(temperature=23)
    # Before this feature, a manual change during a timed preset was ignored
    assert entity.preset_mode == VThermPreset.NONE
    assert entity.target_temperature == 23

    await expire_override(entity, 71)
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 21

    await expire_override(entity, 121)
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == 19
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_override_expires_during_window_open(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Review focus 2: the override expires while the window is open, the window keeps precedence"""
    entity = await setup_vtherm_in_comfort(
        hass,
        OVERRIDE_60
        | {
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,
            CONF_WINDOW_ACTION: CONF_WINDOW_ECO_TEMP,
        },
    )
    await entity.async_set_temperature(temperature=23)
    assert entity.target_temperature == 23

    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_function = await send_window_change_event(entity, True, False, NOW_TZ, sleep=False)
        await try_function(None)
    assert entity.window_state == STATE_ON
    assert entity.target_temperature == 17

    await expire_override(entity, 61)
    assert entity.requested_state.preset == VThermPreset.COMFORT
    assert entity.target_temperature == 17

    with patch("homeassistant.helpers.condition.state", return_value=True):
        try_function = await send_window_change_event(entity, False, True, NOW_TZ + timedelta(minutes=62), sleep=False)
        await try_function(None)
    assert entity.window_state == STATE_OFF
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == 19
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_over_climate_follow_underlying_starts_override_and_echo_ignored(hass: HomeAssistant, skip_hass_states_is_state, skip_turn_on_off_heater, skip_send_event):
    """Review focus 4: a TRV setpoint change starts the override, the TRV echo after the revert does not start a new one"""
    temps = {VThermPreset.FROST: 7, VThermPreset.ECO: 16, VThermPreset.COMFORT: 17, VThermPreset.BOOST: 18}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_NOT_REGULATED_CONFIG | OVERRIDE_60,
    )
    await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, hvac_mode=VThermHvacMode_HEAT, hvac_action=HVACAction.OFF)

    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_hvac_mode"):
        entity = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps)
        assert entity
        entity._set_now(NOW_TZ)
        entity.set_follow_underlying_temp_change(True)

        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.COMFORT)
        assert entity.target_temperature == 17

        # The TRV acknowledges the heat mode and the comfort setpoint (inside the echo filter, ignored)
        await send_climate_change_event_with_temperature(
            entity, VThermHvacMode_HEAT, VThermHvacMode_HEAT, HVACAction.OFF, HVACAction.OFF, NOW_TZ, 17, True, "climate.mock_climate"
        )
        assert entity.preset_mode == VThermPreset.COMFORT

        # The TRV knob is turned 11 s later (outside the echo filter)
        await send_climate_change_event_with_temperature(
            entity, VThermHvacMode_HEAT, VThermHvacMode_HEAT, HVACAction.OFF, HVACAction.OFF, NOW_TZ + timedelta(seconds=11), 21, True, "climate.mock_climate"
        )
        assert entity.target_temperature == 21
        assert entity.preset_mode == VThermPreset.NONE
        assert entity.timed_preset_manager.is_manual_override is True

        # The override expires: back to comfort, the setpoint is sent to the TRV
        await expire_override(entity, 61)
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 17

        # The TRV still reports its previous manual setpoint (21, far from the 17 just sent) within the echo
        # filter window: it differs from the last sent setpoint so only the filter prevents a new override
        await send_climate_change_event_with_temperature(
            entity, VThermHvacMode_HEAT, VThermHvacMode_HEAT, HVACAction.OFF, HVACAction.OFF, NOW_TZ + timedelta(minutes=61, seconds=2), 21, True, "climate.mock_climate"
        )
        assert entity.preset_mode == VThermPreset.COMFORT
        assert entity.timed_preset_manager.is_timed_preset_active is False

        # Control case: the same 21 setpoint report arriving after the echo filter window is taken
        # as a manual change and starts an override, so only the filter prevented it above
        await send_climate_change_event_with_temperature(
            entity, VThermHvacMode_HEAT, VThermHvacMode_HEAT, HVACAction.OFF, HVACAction.OFF, NOW_TZ + timedelta(minutes=61, seconds=20), 21, True, "climate.mock_climate"
        )
        assert entity.preset_mode == VThermPreset.NONE
        assert entity.timed_preset_manager.is_manual_override is True

    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_select_preset_none_during_override_refreshes_attributes(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Review 1: selecting none during an override (state unchanged) clears the exposed attributes at once"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60)
    await entity.async_set_temperature(temperature=23)
    assert entity.extra_state_attributes["timed_preset_manager"]["is_manual_override"] is True

    await entity.async_set_preset_mode(VThermPreset.NONE)

    tpm = entity.extra_state_attributes["timed_preset_manager"]
    assert tpm["is_active"] is False
    assert tpm["is_manual_override"] is False
    state = hass.states.get(entity.entity_id)
    assert state.attributes["timed_preset_manager"]["is_active"] is False
    entity.remove_thermostat()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_select_invalid_preset_keeps_override(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Review 2: an unsupported preset raises and does not cancel the override"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60)
    await entity.async_set_temperature(temperature=23)
    assert entity.timed_preset_manager.is_manual_override is True

    with pytest.raises(ValueError):
        await entity.async_set_preset_mode(VThermPreset.ACTIVITY)

    assert entity.timed_preset_manager.is_manual_override is True
    assert entity.target_temperature == 23
    entity.remove_thermostat()


async def test_restore_manual_override_invalid_resume_end_time(hass: HomeAssistant):
    """Review 3: a corrupt resume record leaves the manager fully reset"""
    vtherm, manager = build_manager(hass)
    old_state = MagicMock()
    old_state.attributes = {
        "timed_preset_manager": {
            "is_active": True,
            "preset": str(VThermPreset.NONE),
            "original_preset": str(VThermPreset.ECO),
            "end_time": (NOW + timedelta(minutes=30)).isoformat(),
            "is_manual_override": True,
            "resume_preset": str(VThermPreset.BOOST),
            "resume_end_time": "not-a-date",
        }
    }
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time") as mock_track:
        manager.restore_state(old_state)
        mock_track.assert_not_called()

    assert manager.is_timed_preset_active is False
    assert manager.is_manual_override is False
    assert manager._timed_preset is None
    assert manager._original_preset is None
    assert manager._timed_preset_end_time is None
    assert manager._resume_preset is None


async def test_cancel_manual_override_event_reports_selected_preset(hass: HomeAssistant):
    """Review 4: the end event reports the newly selected preset"""
    vtherm, manager = build_manager(hass)
    with patch("custom_components.versatile_thermostat.feature_timed_preset_manager.async_track_point_in_time"):
        await manager.start_manual_override(VThermPreset.COMFORT)

    manager.cancel_manual_override_without_revert(VThermPreset.ECO)

    event = events_data(vtherm)[-1]
    assert event["type"] == "end"
    assert event["cause"] == "preset_selected"
    assert event["restored_preset"] == str(VThermPreset.ECO)
    vtherm.update_custom_attributes.assert_called()
    vtherm.async_write_ha_state.assert_called()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_restart_during_override_keeps_manual_target_and_reverts(hass: HomeAssistant, skip_hass_states_is_state, fake_underlying_switch):
    """Gap 5: after a restart with time remaining, the manual target is kept and the revert happens at the stored end time"""
    entity = await setup_vtherm_in_comfort(hass, OVERRIDE_60)
    await entity.async_set_temperature(temperature=23)
    stored_attributes = dict(entity.extra_state_attributes)
    stored_end_time = stored_attributes["timed_preset_manager"]["end_time"]
    assert stored_attributes["timed_preset_manager"]["is_manual_override"] is True
    entity.remove_thermostat()
    await hass.config_entries.async_remove(hass.config_entries.async_entries(DOMAIN)[0].entry_id)
    await hass.async_block_till_done()

    old_state = MagicMock()
    old_state.state = HVACMode.HEAT
    old_state.attributes = stored_attributes

    with patch("homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state", return_value=old_state):
        entity = await create_thermostat(hass, build_over_switch_entry(OVERRIDE_60, unique_id="uniqueId2"), "climate.theoverswitchmockname")
        assert entity
        await wait_for_local_condition(lambda: entity.is_ready is True)
    await hass.async_block_till_done()

    manager = entity.timed_preset_manager
    assert manager.is_manual_override is True
    assert manager.timed_preset_end_time.isoformat() == stored_end_time
    assert entity.requested_state.preset == VThermPreset.NONE
    assert entity.target_temperature == 23

    await expire_override(entity, 61)
    assert entity.preset_mode == VThermPreset.COMFORT
    assert entity.target_temperature == 19
    assert manager.is_timed_preset_active is False
    entity.remove_thermostat()
