"""Characterization, not acceptance of an unselected product fix."""

# pylint: disable=protected-access,redefined-outer-name

from datetime import datetime, timedelta, timezone

import pytest
from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import ATTR_ENTITY_ID, EVENT_CALL_SERVICE, EVENT_STATE_CHANGED
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.versatile_thermostat.const import (
    AUTO_START_STOP_LEVEL_SLOW, CONF_AC_MODE, CONF_AUTO_REGULATION_MODE,
    CONF_AUTO_REGULATION_NONE, CONF_AUTO_START_STOP_LEVEL, CONF_CYCLE_MIN,
    CONF_EXTERNAL_TEMP_SENSOR, CONF_NAME, CONF_REPAIR_INCORRECT_STATE,
    CONF_TEMP_MAX, CONF_TEMP_MIN, CONF_TEMP_SENSOR, CONF_THERMOSTAT_CLIMATE,
    CONF_THERMOSTAT_TYPE, CONF_UNDERLYING_LIST, CONF_USE_AUTO_START_STOP_FEATURE,
    CONFIG_VERSION, CONFIG_MINOR_VERSION, DOMAIN,
)
from tests.commons import create_thermostat, send_temperature_change_event

from .bench import (ALLOWED_CLIMATE_TARGETS, DEVICE_ID, EXTERNAL_ID, ROOM_ID,
                    THERMOSTAT_ID, Journal, SimulatedClimate, decision_snapshot)


@pytest.fixture
async def device(hass):
    """The actual climate service registry dispatches to one fictitious entity."""
    assert await async_setup_component(hass, CLIMATE, {})
    journal = Journal()
    simulated = SimulatedClimate(hass, journal)
    simulated._attr_should_poll = False
    await hass.data[CLIMATE].async_add_entities([simulated])
    await hass.async_block_till_done()
    assert simulated.entity_id == DEVICE_ID
    yield simulated
    simulated.close()


async def call(hass, entity_id, service, **data):
    assert entity_id in ALLOWED_CLIMATE_TARGETS
    await hass.services.async_call(CLIMATE, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True)
    await hass.async_block_till_done()


@pytest.mark.parametrize("first,second,expected", [
    ("off", "heat", ["heat", "heat", "off"]),
    ("heat", "off", ["heat", "off", "heat"]),
])
async def test_double_immediate_and_delayed_out_of_order(hass, device, first, second, expected):
    await call(hass, DEVICE_ID, "set_hvac_mode", hvac_mode="heat")
    assert device.physical_mode == HVACMode.HEAT
    assert hass.states.get(DEVICE_ID).state == "heat"

    device.next_policy = "delay"
    await call(hass, DEVICE_ID, "set_hvac_mode", hvac_mode=first)
    device.next_policy = "delay"
    await call(hass, DEVICE_ID, "set_hvac_mode", hvac_mode=second)
    assert len(device.pending) == 2
    device.deliver(1)
    device.deliver(0)
    await hass.async_block_till_done()
    applied = [r.value for r in device.journal.records if r.stage == "device_apply"]
    assert applied == expected
    assert device.physical_mode == HVACMode(first)
    for cid in (1, 2, 3):
        stages = [r.stage for r in device.journal.records if r.command_id == cid]
        assert stages.index("handler_enter") < stages.index("accepted")
        assert stages.index("accepted") < stages.index("device_apply")
        assert stages.index("device_apply") < stages.index("ha_publish_faithful")
        if cid > 1:
            assert stages.index("handler_return") < stages.index("device_apply")


async def test_double_teardown_discards_pending(hass, device):
    device.next_policy = "delay"
    await call(hass, DEVICE_ID, "set_hvac_mode", hvac_mode="heat")
    assert len(device.pending) == 1
    device.close()
    assert not device.pending and device.physical_mode == HVACMode.OFF
    assert device.journal.records[-1].stage == "discarded_at_teardown"


async def test_double_loss_optimism_and_delayed_publication(hass, device):
    await call(hass, DEVICE_ID, "set_hvac_mode", hvac_mode="heat")
    device.optimistic = True
    device.next_policy = "drop"
    await call(hass, DEVICE_ID, "set_hvac_mode", hvac_mode="off")
    assert hass.states.get(DEVICE_ID).state == "off"
    assert device.physical_mode == HVACMode.HEAT
    assert any(r.stage == "lost_after_acceptance" for r in device.journal.records)

    device.optimistic = False
    device.publish_on_apply = False
    await call(hass, DEVICE_ID, "set_hvac_mode", hvac_mode="off")
    device.publish(HVACMode.HEAT, source="stale")
    await hass.async_block_till_done()
    assert hass.states.get(DEVICE_ID).state == "heat"
    assert device.physical_mode == HVACMode.OFF


async def test_double_rejection_does_not_apply(hass, device):
    device.next_policy = "reject"
    with pytest.raises(HomeAssistantError, match="simulated rejection"):
        await call(hass, DEVICE_ID, "set_hvac_mode", hvac_mode="heat")
    assert device.physical_mode == HVACMode.OFF
    assert not any(r.stage == "accepted" for r in device.journal.records)


@pytest.mark.parametrize("scenario", ["combined", "temperature_same", "temperature_changed", "mode_same"])
async def test_natural_slow_service_characterization(hass, device, monkeypatch, request, scenario):
    """T-01/T-02: each starts from natural auto-stop with no injected fault."""
    journal = device.journal
    unexpected_targets = []

    def observe_service(event):
        data = event.data
        if data.get("domain") == CLIMATE:
            payload = dict(data.get("service_data", {}))
            target = payload.get(ATTR_ENTITY_ID)
            targets = [target] if isinstance(target, str) else list(target or [])
            if not targets or not set(targets) <= ALLOWED_CLIMATE_TARGETS:
                unexpected_targets.append(target)
            # Event callbacks are scheduled: observation is not service entry.
            journal.add("registry_observed", (data.get("service"), payload))

    def observe_state(event):
        if event.data.get("entity_id") in ALLOWED_CLIMATE_TARGETS:
            state = event.data.get("new_state")
            journal.add("ha_state_event", (event.data["entity_id"], state.state if state else None))

    remove_service = hass.bus.async_listen(EVENT_CALL_SERVICE, observe_service)
    request.addfinalizer(remove_service)
    remove_state = hass.bus.async_listen(EVENT_STATE_CHANGED, observe_state)
    request.addfinalizer(remove_state)
    remove_auto = hass.bus.async_listen(
        "versatile_thermostat_auto_start_stop_event",
        lambda event: journal.add("auto_start_stop_event", {
            key: event.data.get(key) for key in ("type", "hvac_mode", "saved_hvac_mode")
        }),
    )
    request.addfinalizer(remove_auto)
    entry = MockConfigEntry(domain=DOMAIN, title="Simulated VTherm", unique_id="issue2135-test-only",
        version=CONFIG_VERSION, minor_version=CONFIG_MINOR_VERSION,
        data={CONF_NAME: "issue2135_simulated_vtherm", CONF_TEMP_SENSOR: ROOM_ID,
              CONF_EXTERNAL_TEMP_SENSOR: EXTERNAL_ID, CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
              CONF_UNDERLYING_LIST: [DEVICE_ID], CONF_CYCLE_MIN: 5,
              CONF_TEMP_MIN: 15, CONF_TEMP_MAX: 30, CONF_AC_MODE: True,
              CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_NONE,
              CONF_USE_AUTO_START_STOP_FEATURE: True, CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_SLOW,
              CONF_REPAIR_INCORRECT_STATE: False})
    hass.states.async_set(ROOM_ID, "18", {"unit_of_measurement": "°C"})
    hass.states.async_set(EXTERNAL_ID, "12", {"unit_of_measurement": "°C"})
    vtherm = await create_thermostat(hass, entry, THERMOSTAT_ID)
    assert vtherm is not None and vtherm.entity_id == THERMOSTAT_ID
    assert vtherm.is_ready

    original_temp = vtherm.async_set_temperature
    original_mode = vtherm.async_set_hvac_mode
    underlying = vtherm._underlyings[0]
    original_underlying_mode = underlying.set_hvac_mode
    repair = vtherm.repair_incorrect_state_manager
    original_repair = repair.check_and_repair
    original_underlying_repair = underlying.check_and_repair
    assert not repair._is_configured and not repair.is_detected
    assert not vtherm.follow_underlying_temp_change

    def observe_snapshot(stage):
        # Diagnostics must not replace the result or exception of a real method.
        try:
            journal.add(stage, decision_snapshot(vtherm, device))
        except Exception as error:  # pylint: disable=broad-exception-caught
            journal.add("observer_error", (stage, type(error).__name__, str(error)))

    async def observe_temp(**kwargs):
        journal.add("vtherm_temperature_enter", dict(kwargs))
        try:
            return await original_temp(**kwargs)
        finally:
            observe_snapshot("vtherm_temperature_return")

    async def observe_mode(*args, **kwargs):
        journal.add("vtherm_mode_enter", (tuple(map(str, args)), dict(kwargs)))
        try:
            return await original_mode(*args, **kwargs)
        finally:
            observe_snapshot("vtherm_mode_return")

    async def observe_underlying_mode(*args, **kwargs):
        journal.add("underlying_mode_attempt", tuple(map(str, args)))
        try:
            result = await original_underlying_mode(*args, **kwargs)
        except Exception as error:
            journal.add("underlying_mode_error", type(error).__name__)
            raise
        journal.add("underlying_mode_return", result)
        return result

    async def observe_repair():
        journal.add("repair_enter", {"configured": repair._is_configured,
                                     "detected": repair.is_detected})
        result = await original_repair()
        journal.add("repair_return", result)
        return result

    async def observe_underlying_repair():
        journal.add("underlying_repair_enter")
        return await original_underlying_repair()

    monkeypatch.setattr(vtherm, "async_set_temperature", observe_temp)
    monkeypatch.setattr(vtherm, "async_set_hvac_mode", observe_mode)
    monkeypatch.setattr(underlying, "set_hvac_mode", observe_underlying_mode)
    monkeypatch.setattr(repair, "check_and_repair", observe_repair)
    monkeypatch.setattr(underlying, "check_and_repair", observe_underlying_repair)

    completed = False
    try:
        # Bootstrap through real services and naturally accumulated thermal error.
        now = datetime.now(timezone.utc)
        vtherm._set_now(now)
        await call(hass, THERMOSTAT_ID, "set_temperature", temperature=20.0)
        await call(hass, THERMOSTAT_ID, "set_hvac_mode", hvac_mode="heat")
        for temp in (20, 21, 22, 23, 24):
            now += timedelta(minutes=5)
            vtherm._set_now(now)
            await send_temperature_change_event(vtherm, temp, now, sleep=False)
            await hass.async_block_till_done()
            journal.add("bootstrap", decision_snapshot(vtherm, device))
            if vtherm.auto_start_stop_manager.is_auto_stop_detected:
                break

        before = decision_snapshot(vtherm, device)
        journal.add("precondition", before)
        assert before["R"] == "heat" and before["E"] == "off" and before["U"] == "off"
        assert before["H"] == "off" and before["P"] == "off" and before["stop"]
        assert any(r.stage == "auto_start_stop_event" and r.value["type"] == "stop"
               for r in journal.records)
        start = len(journal.records)
        if scenario == "combined":
            await call(hass, THERMOSTAT_ID, "set_temperature", temperature=20.0, hvac_mode="heat")
        elif scenario == "temperature_same":
            await call(hass, THERMOSTAT_ID, "set_temperature", temperature=20.0)
        elif scenario == "temperature_changed":
            await call(hass, THERMOSTAT_ID, "set_temperature", temperature=21.0)
        else:
            await call(hass, THERMOSTAT_ID, "set_hvac_mode", hvac_mode="heat")
        after = decision_snapshot(vtherm, device)
        journal.add("after_service", after)
        # HA's test helper triggers due timers; _set_now separately advances
        # VTherm's clock. Repair uses wall-clock UTC and is disabled here.
        wall_origin = datetime.now(timezone.utc)
        for seconds in (3, 301):
            vtherm._set_now(now + timedelta(seconds=seconds))
            async_fire_time_changed(hass, wall_origin + timedelta(seconds=seconds))
            await hass.async_block_till_done()
            journal.add(f"after_timer_advance_{seconds}s", decision_snapshot(vtherm, device))
        print("ISSUE2135_SCENARIO", scenario)
        print("ISSUE2135_PRE", before)
        for record in journal.records[start:]:
            print("ISSUE2135_TRACE", record)
        print("ISSUE2135_POST", after)
        # This is an evidence assertion, not an assertion that the incident is fixed.
        entry_stage = "vtherm_mode_enter" if scenario == "mode_same" else "vtherm_temperature_enter"
        assert any(r.stage == entry_stage for r in journal.records[start:])
        assert not any(r.stage == "underlying_repair_enter" for r in journal.records[start:])
        assert not any(r.stage == "observer_error" for r in journal.records)
        assert not unexpected_targets
        completed = True
    finally:
        if not completed:
            print("ISSUE2135_FAILURE_SCENARIO", scenario)
            for record in journal.records:
                print("ISSUE2135_FAILURE_TRACE", record)
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert all(entity.entity_id != THERMOSTAT_ID for entity in hass.data[CLIMATE].entities)
        state = hass.states.get(THERMOSTAT_ID)
        assert state is None or state.state == "unavailable"