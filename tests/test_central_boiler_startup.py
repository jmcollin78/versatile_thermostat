# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

"""Test that the central boiler device stays in sync with VTherm across restarts and reloads"""
import logging

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, UnitOfPower
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.versatile_thermostat import async_setup, reload_all_vtherm
from custom_components.versatile_thermostat.feature_central_boiler_manager import FeatureCentralBoilerManager
from custom_components.versatile_thermostat.vtherm_central_api import VersatileThermostatAPI

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

BOILER_ENTITY = "climate.kitchen"
ACTIVATE = f"{BOILER_ENTITY}/climate.set_temperature/temperature:23"
DEACTIVATE = f"{BOILER_ENTITY}/climate.set_temperature/temperature:11"
POWER_THRESHOLD = 1500
MANAGER_MODULE = "custom_components.versatile_thermostat.feature_central_boiler_manager"


def _build_manager(
    hass: HomeAssistant,
    *,
    power: float | None = 0.0,
    nb_active: int | None = 0,
    delay: int = 0,
    keep_alive: int = 0,
    activate: str = ACTIVATE,
    deactivate: str = DEACTIVATE,
) -> FeatureCentralBoilerManager:
    """Build a ready manager whose demand comes from mocked sensors. The power threshold is 1500 W, the number threshold is disabled"""
    manager = FeatureCentralBoilerManager(hass, MagicMock())
    manager._central_boiler_entity = MagicMock(entity_id="binary_sensor.central_boiler")
    manager.post_init(
        {
            CONF_CENTRAL_BOILER_ACTIVATION_SRV: activate,
            CONF_CENTRAL_BOILER_DEACTIVATION_SRV: deactivate,
            CONF_CENTRAL_BOILER_ACTIVATION_DELAY_SEC: delay,
            CONF_KEEP_ALIVE_BOILER_DELAY_SEC: keep_alive,
        }
    )
    manager._nb_active_device_number_entity = MagicMock(entity_id="sensor.nb", native_value=nb_active)
    manager._total_power_active_entity = MagicMock(entity_id="sensor.power", native_value=power, native_unit_of_measurement=UnitOfPower.WATT)
    manager._nb_active_device_threshold_number_entity = MagicMock(entity_id="number.nb", native_value=0)
    manager._total_power_active_threshold_number_entity = MagicMock(entity_id="number.power", native_value=POWER_THRESHOLD, native_unit_of_measurement=UnitOfPower.WATT)
    manager._is_ready = True
    return manager


def _set_demand(manager: FeatureCentralBoilerManager, power: float | None) -> None:
    """Change what the mocked demand sensors report"""
    manager._total_power_active_entity.native_value = power
    manager._nb_active_device_number_entity.native_value = 0 if power is not None else None


def _temperatures(calls) -> list:
    """The setpoints which have been sent to the boiler relay"""
    return [call.data["temperature"] for call in calls]


async def _fire_after(hass: HomeAssistant, seconds: int) -> None:
    """Move the time forward and let the timers run"""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds + 1))
    await hass.async_block_till_done()


async def test_boiler_entity_missing_defers_deactivate_until_it_appears(hass: HomeAssistant):
    """A missing boiler entity means no call and no recorded state. The deactivate is sent when the entity appears, with the demand unchanged"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    manager = _build_manager(hass)

    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()

    assert calls == []
    assert manager.is_on is None
    assert manager._last_activated_service is None

    hass.states.async_set(BOILER_ENTITY, "heat")
    await hass.async_block_till_done()

    assert _temperatures(calls) == ["11"]
    assert manager.is_on is False
    assert manager._last_activated_service is None  # keep-alive is disabled

    # the retry is done: other states of the boiler entity do not send anything more
    hass.states.async_set(BOILER_ENTITY, "off")
    await hass.async_block_till_done()
    assert len(calls) == 1


@pytest.mark.parametrize(
    "power, nb_active",
    [
        # the sensors have never been calculated
        (None, None),
        # only one of the sensors have been calculated
        (0.0, None),
        (None, 0),
    ],
)
async def test_boiler_entity_present_but_demand_not_populated_sends_nothing(hass: HomeAssistant, power, nb_active):
    """With the boiler entity available, no deactivate is sent while the demand is not known"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "heat")
    manager = _build_manager(hass, power=power, nb_active=nb_active)

    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()

    assert calls == []
    assert manager.is_on is None


async def test_zero_before_vtherms_have_started_sends_nothing(hass: HomeAssistant):
    """At startup the sensors are calculated before the VTherms start: their 0 is decided only once the links are initialized"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "heat")
    manager = _build_manager(hass, power=0.0, nb_active=0)
    manager.notify_vtherms_starting()

    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()
    assert calls == []
    assert manager.is_on is None

    await manager.notify_vtherms_started()
    await hass.async_block_till_done()
    assert _temperatures(calls) == ["11"]
    assert manager.is_on is False

    # a second notification does nothing
    await manager.notify_vtherms_started()
    await hass.async_block_till_done()
    assert len(calls) == 1


async def test_reload_with_boiler_needed_sends_no_off(hass: HomeAssistant):
    """A reload keeps the manager and is_on=True. The new sensors must not turn the boiler off before the real demand is read"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "heat")
    manager = _build_manager(hass, power=1620.0, keep_alive=60)
    manager._is_on = True

    # the reload
    manager.post_init(
        {
            CONF_CENTRAL_BOILER_ACTIVATION_SRV: ACTIVATE,
            CONF_CENTRAL_BOILER_DEACTIVATION_SRV: DEACTIVATE,
            CONF_KEEP_ALIVE_BOILER_DELAY_SEC: 60,
        }
    )
    _set_demand(manager, None)
    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()
    assert calls == []
    assert manager.is_on is True

    # the real demand is read
    _set_demand(manager, 1620.0)
    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()
    assert calls == []
    assert manager.is_on is True

    # keep-alive still has the running command to send
    await manager._keep_alive_boiler(None)
    await hass.async_block_till_done()
    assert _temperatures(calls) == ["23"]


async def test_reload_with_changed_services_resends_the_state(hass: HomeAssistant):
    """If the reload changes the commands, the new device has never been commanded: the state is sent again"""
    calls = async_mock_service(hass, SWITCH_DOMAIN, "turn_on")
    hass.states.async_set("switch.new_boiler", "off")
    manager = _build_manager(hass, power=1620.0)
    manager._is_on = True

    manager.post_init(
        {
            CONF_CENTRAL_BOILER_ACTIVATION_SRV: "switch.new_boiler/switch.turn_on",
            CONF_CENTRAL_BOILER_DEACTIVATION_SRV: "switch.new_boiler/switch.turn_off",
        }
    )
    assert manager.is_on is None

    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert manager.is_on is True


async def test_demand_above_threshold_after_restart_activates_after_delay(hass: HomeAssistant):
    """The unknown demand is skipped, then the normal delayed activation takes place"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "off")
    manager = _build_manager(hass, power=None, nb_active=None, delay=120)

    await manager.calculate_central_boiler_state(None)
    assert manager._call_later_handle is None

    _set_demand(manager, 1620.0)
    await manager.calculate_central_boiler_state(None)
    assert manager._call_later_handle is not None
    assert calls == []
    assert manager.is_on is None

    await _fire_after(hass, 120)

    assert _temperatures(calls) == ["23"]
    assert manager.is_on is True
    assert manager._call_later_handle is None


async def test_boiler_entity_unavailable_when_delayed_activation_fires_is_retried(hass: HomeAssistant):
    """The activation is kept when the delay ends with an unavailable boiler entity, and is sent as soon as the entity is back"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "heat")
    manager = _build_manager(hass, power=1620.0, delay=120, keep_alive=60)

    await manager.calculate_central_boiler_state(None)
    hass.states.async_set(BOILER_ENTITY, "unavailable")
    await _fire_after(hass, 120)

    assert calls == []
    assert manager.is_on is None
    assert manager._last_activated_service is None
    assert manager._call_later_handle is None

    # still unavailable: a new calculation sends nothing and does not restart the delay
    await manager.calculate_central_boiler_state(None)
    assert calls == []
    assert manager._call_later_handle is None

    with patch(f"{MANAGER_MODULE}.send_vtherm_event") as mock_event:
        hass.states.async_set(BOILER_ENTITY, "heat")
        await hass.async_block_till_done()

    assert _temperatures(calls) == ["23"]
    assert manager.is_on is True
    assert manager._last_activated_service == manager._service_activate
    assert manager._call_later_handle is None
    mock_event.assert_called_once()
    assert mock_event.call_args.kwargs["data"] == {"central_boiler": True}


async def test_activation_on_unavailable_boiler_entity_without_delay_is_retried(hass: HomeAssistant):
    """The same retry applies to an immediate activation"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "unavailable")
    manager = _build_manager(hass, power=1620.0)
    manager._is_on = False

    await manager.calculate_central_boiler_state(None)
    assert calls == []
    assert manager.is_on is False

    hass.states.async_set(BOILER_ENTITY, "heat")
    await hass.async_block_till_done()

    assert _temperatures(calls) == ["23"]
    assert manager.is_on is True


async def test_demand_change_during_outage_restarts_the_activation_delay(hass: HomeAssistant):
    """A demand that drops during the outage cancels the retry: when it returns, the delay applies again"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "unavailable")
    manager = _build_manager(hass, power=1620.0, delay=120)
    manager._is_on = False

    await manager.calculate_central_boiler_state(None)
    await _fire_after(hass, 120)
    assert calls == []

    # the demand drops: is_on=False is already right, nothing is pending anymore
    _set_demand(manager, 100.0)
    await manager.calculate_central_boiler_state(None)
    assert manager._cancel_boiler_command_entity_listener is None

    hass.states.async_set(BOILER_ENTITY, "heat")
    await hass.async_block_till_done()
    assert calls == []
    assert manager.is_on is False

    # the demand comes back: it is a new activation
    _set_demand(manager, 1620.0)
    await manager.calculate_central_boiler_state(None)
    assert calls == []
    assert manager._call_later_handle is not None

    await _fire_after(hass, 120)
    assert _temperatures(calls) == ["23"]


async def test_boiler_entity_listener_is_neither_duplicated_nor_leaked(hass: HomeAssistant):
    """Only one listener exists while a command is pending, and it is removed by stop_listening"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    manager = _build_manager(hass)
    cancel = MagicMock()

    with patch(f"{MANAGER_MODULE}.async_track_state_change_event", return_value=cancel) as mock_track:
        await manager.calculate_central_boiler_state(None)
        await manager.calculate_central_boiler_state(None)
        mock_track.assert_called_once()
        assert mock_track.call_args.args[1] == [BOILER_ENTITY]
        cancel.assert_not_called()

        manager.stop_listening()
        cancel.assert_called_once()
        assert manager._cancel_boiler_command_entity_listener is None

        # stop_listening is idempotent
        manager.stop_listening()
        cancel.assert_called_once()

    # with a real listener: nothing is sent after the cleanup
    await manager.calculate_central_boiler_state(None)
    manager.stop_listening()
    hass.states.async_set(BOILER_ENTITY, "heat")
    await hass.async_block_till_done()
    assert calls == []
    assert manager.is_on is None


async def test_unloading_the_central_config_removes_the_boiler_entity_listener(hass: HomeAssistant, init_central_config_with_boiler_fixture):
    """Unloading the central configuration stops the pending retry"""
    manager = VersatileThermostatAPI.get_vtherm_api(hass).central_boiler_manager
    # switch.pompe_chaudiere is not registered in this test
    await hass.async_block_till_done()
    assert manager._cancel_boiler_command_entity_listener is not None

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await hass.config_entries.async_unload(entry.entry_id)

    assert manager._cancel_boiler_command_entity_listener is None


async def test_unset_service_is_not_blocked(hass: HomeAssistant):
    """With no deactivation service configured there is nothing to deliver: the state is recorded as before"""
    hass.states.async_set("switch.boiler", "off")
    manager = _build_manager(hass, activate="switch.boiler/switch.turn_on", deactivate=None)

    await manager.calculate_central_boiler_state(None)

    assert manager._service_deactivate == {}
    assert manager.is_on is False
    assert manager._cancel_boiler_command_entity_listener is None


async def test_normal_transitions_and_keep_alive_are_unchanged(hass: HomeAssistant):
    """on / off transitions, the or logic of thresholds, and the keep-alive once running"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "heat")
    manager = _build_manager(hass, power=0.0, keep_alive=60)

    # off
    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()
    assert _temperatures(calls) == ["11"]
    assert manager.is_on is False
    assert manager._last_activated_service == manager._service_deactivate

    # no change, no command
    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()
    assert len(calls) == 1

    # keep-alive resends the last command
    await manager._keep_alive_boiler(None)
    await hass.async_block_till_done()
    assert _temperatures(calls) == ["11", "11"]

    # on, by the power threshold
    _set_demand(manager, 1620.0)
    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()
    assert _temperatures(calls) == ["11", "11", "23"]
    assert manager.is_on is True
    assert manager._last_activated_service == manager._service_activate

    await manager._keep_alive_boiler(None)
    await hass.async_block_till_done()
    assert _temperatures(calls)[-1] == "23"

    # off again
    _set_demand(manager, 100.0)
    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()
    assert _temperatures(calls)[-1] == "11"
    assert manager.is_on is False

    # on, by the number of active devices only (or logic)
    manager._nb_active_device_threshold_number_entity.native_value = 1
    manager._nb_active_device_number_entity.native_value = 1
    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()
    assert _temperatures(calls)[-1] == "23"
    assert manager.is_on is True


async def test_demand_drop_still_cancels_a_pending_activation(hass: HomeAssistant):
    """A pending activation is cancelled by a demand drop and the deactivate is sent as before"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "heat")
    manager = _build_manager(hass, power=1620.0, delay=120)

    await manager.calculate_central_boiler_state(None)
    assert manager._call_later_handle is not None

    _set_demand(manager, 100.0)
    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()

    assert manager._call_later_handle is None
    assert _temperatures(calls) == ["11"]
    assert manager.is_on is False

    await _fire_after(hass, 120)
    assert len(calls) == 1


async def test_event_log_shows_the_total_power_values(hass: HomeAssistant, caplog):
    """The second part of the event log was not an f-string"""
    async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "heat")
    manager = _build_manager(hass, power=0.0)
    with caplog.at_level(logging.INFO):
        await manager.calculate_central_boiler_state(None)
        assert f"total_power= 0.0/{POWER_THRESHOLD}" in caplog.text

        _set_demand(manager, 1620.0)
        await manager.calculate_central_boiler_state(None)
        assert f"total_power= 1620.0/{POWER_THRESHOLD}" in caplog.text

    assert "{self." not in caplog.text


async def _create_heating_vtherm(hass: HomeAssistant, fake_underlying_switch):
    """Create a real VTherm which needs the boiler"""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 7,
            CONF_TEMP_MAX: 18,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: [fake_underlying_switch.entity_id],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_INVERSE_SWITCH: False,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: True,
            CONF_USE_TPI_CENTRAL_CONFIG: True,
            CONF_USE_PRESETS_CENTRAL_CONFIG: False,
            CONF_USE_ADVANCED_CENTRAL_CONFIG: True,
            CONF_USED_BY_CENTRAL_BOILER: True,
            CONF_DEVICE_POWER: 1500,
        },
    )
    return await create_thermostat(hass, entry, "climate.theoverswitchmockname", temps=default_temperatures)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.parametrize("reload_all", [False, True])
async def test_real_reload_with_boiler_needed_sends_no_off(hass: HomeAssistant, init_central_config_with_boiler_fixture, fake_underlying_switch, reload_all):
    """With real entities, reloading the central config while the boiler is needed never sends an off"""
    api = VersatileThermostatAPI.get_vtherm_api(hass)
    manager = api.central_boiler_manager

    # The temperature that the reloaded VTherm will read
    hass.states.async_set("sensor.mock_temp_sensor", "10")
    hass.states.async_set("sensor.mock_ext_temp_sensor", "5")

    pump = MockSwitch(hass, "pompe_chaudiere", "SwitchPompeChaudiere")
    await register_mock_entity(hass, pump, SWITCH_DOMAIN)
    await hass.async_block_till_done()

    entity = await _create_heating_vtherm(hass, fake_underlying_switch)
    manager._set_total_power_active_threshold(100)
    # set_native_value does not write the state: without this, no value could be restored by the reload
    manager._total_power_active_threshold_number_entity.async_write_ha_state()
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    await send_temperature_change_event(entity, 10, dt_util.now())
    await wait_for_local_condition(lambda: manager.is_on is True)
    assert pump.is_on

    central_entry = next(entry for entry in hass.config_entries.async_entries(DOMAIN) if entry.data.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG)

    real_init_vtherm_links = api.init_vtherm_links
    starting_during_reload = []

    async def calculate_then_init_vtherm_links(entry_id=None):
        """On a real system, the calculation started by the registration of the entities runs before the links are initialized"""
        starting_during_reload.append(manager._vtherms_starting)
        await manager.calculate_central_boiler_state(None)
        await real_init_vtherm_links(entry_id)

    with (
        patch.object(api, "init_vtherm_links", side_effect=calculate_then_init_vtherm_links),
        patch.object(manager, "call_service", wraps=manager.call_service) as spy,
    ):
        if reload_all:
            await reload_all_vtherm(hass)
        else:
            await hass.config_entries.async_reload(central_entry.entry_id)
        await hass.async_block_till_done()

        assert manager.total_power_active_for_boiler_threshold == 100
        entity = search_entity(hass, "climate.theoverswitchmockname", CLIMATE_DOMAIN)
        await wait_for_local_condition(lambda: entity.is_ready is True)
        await hass.async_block_till_done()

        for call in spy.call_args_list:
            assert call.args[0] != manager._service_deactivate, f"the boiler has been turned off during the reload: {spy.call_args_list}"

    assert starting_during_reload
    assert all(starting_during_reload) is reload_all
    assert manager._vtherms_starting is False
    assert manager.is_on is True
    entity.remove_thermostat()


async def test_boiler_state_is_decided_when_vtherms_have_started(hass: HomeAssistant):
    """While VTherms are being reloaded a low demand is only a partial one. The decision is taken when they have all started"""
    calls = async_mock_service(hass, CLIMATE_DOMAIN, "set_temperature")
    hass.states.async_set(BOILER_ENTITY, "heat")
    manager = _build_manager(hass, power=100.0)
    manager._is_on = True

    manager.notify_vtherms_starting()
    await manager.calculate_central_boiler_state(None)
    await hass.async_block_till_done()
    assert calls == []
    assert manager.is_on is True

    # the other VTherms are back: the boiler is needed and nothing has to be sent
    _set_demand(manager, 1620.0)
    await manager.notify_vtherms_started()
    await hass.async_block_till_done()
    assert calls == []
    assert manager.is_on is True

    # the same with a demand which is really low
    manager.notify_vtherms_starting()
    _set_demand(manager, 100.0)
    await manager.notify_vtherms_started()
    await hass.async_block_till_done()
    assert _temperatures(calls) == ["11"]
    assert manager.is_on is False


async def test_init_vtherm_links_notifies_vtherms_started(hass: HomeAssistant, init_central_config_with_boiler_fixture):
    """Only the initialization of all the VTherms notifies that they have started, not the one of a single entry"""
    api = VersatileThermostatAPI.get_vtherm_api(hass)
    manager = api.central_boiler_manager
    manager.notify_vtherms_starting()

    with patch.object(manager, "calculate_central_boiler_state") as mock_calculate:
        await api.init_vtherm_links("some_entry_id")
        assert manager._vtherms_starting is True
        mock_calculate.assert_not_called()

        await api.init_vtherm_links()
        assert manager._vtherms_starting is False
        mock_calculate.assert_called()


async def test_ha_startup_waits_for_vtherm_links_to_be_initialized(hass: HomeAssistant):
    """While HA starts, VT does not decide the boiler state. HA started initializes the links, which notifies that the VTherms have started"""
    hass.set_state(CoreState.starting)
    with patch("custom_components.versatile_thermostat.async_register_log_download_endpoint"):
        assert await async_setup(hass, {})

    manager = VersatileThermostatAPI.get_vtherm_api(hass).central_boiler_manager
    assert manager._vtherms_starting is True

    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert manager._vtherms_starting is False


async def test_setup_when_ha_is_running_does_not_keep_waiting(hass: HomeAssistant):
    """Installing the integration while HA runs initializes the links immediately"""
    with patch("custom_components.versatile_thermostat.async_register_log_download_endpoint"):
        assert await async_setup(hass, {})

    assert VersatileThermostatAPI.get_vtherm_api(hass).central_boiler_manager._vtherms_starting is False
