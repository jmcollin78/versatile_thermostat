"""History export permissions, paging and native Recorder integration."""

from datetime import datetime, timedelta, UTC
from functools import partial
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import Context, State
from custom_components.versatile_thermostat import llm as module
from custom_components.versatile_thermostat.recorder_export import (
    async_export_history,
    read_recorder_history,
)

ENTITY = "climate.test"
START = datetime(2026, 10, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-10-01", "2026-10-02"),
        ("bad", START.isoformat()),
        (START.isoformat(), START.isoformat()),
        (START.isoformat(), (START + timedelta(days=15)).isoformat()),
        ("2099-01-01T00:00:00Z", "2099-01-02T00:00:00Z"),
    ],
)
async def test_bad_dates(start, end):
    hass = SimpleNamespace(config=SimpleNamespace(components={"recorder"}))
    with pytest.raises(ValueError):
        await async_export_history(hass, ENTITY, start, end, 0, 500)


async def test_pages():
    states = [
        State(
            ENTITY,
            "heat",
            {"temperature": 19 + i, "secret": "omit"},
            last_updated=START + timedelta(minutes=i),
        )
        for i in range(3)
    ]

    async def execute(fn):
        return fn()

    hass = SimpleNamespace(config=SimpleNamespace(components={"recorder"}))
    recorder = SimpleNamespace(async_add_executor_job=AsyncMock(side_effect=execute))
    with patch(
        "custom_components.versatile_thermostat.recorder_export.get_instance",
        return_value=recorder,
    ), patch(
        "custom_components.versatile_thermostat.recorder_export.history.get_significant_states",
        return_value={ENTITY: states},
    ) as query:
        first = await async_export_history(
            hass,
            ENTITY,
            START.isoformat(),
            (START + timedelta(days=7)).isoformat(),
            0,
            2,
        )
        last = await async_export_history(
            hass,
            ENTITY,
            START.isoformat(),
            (START + timedelta(days=7)).isoformat(),
            first["next_offset"],
            2,
        )
    assert first["pagination_complete"] is False
    assert last["next_offset"] is None
    assert last["rows"][0]["attributes"]["temperature"] == 21
    assert first["rows"][0]["attributes"]["current_temperature"] is None
    assert "secret" not in first["rows"][0]["attributes"]
    assert query.call_args.kwargs["significant_changes_only"] is False


@pytest.mark.parametrize(
    "exposed,authenticated,allowed",
    [(False, True, True), (True, False, True), (True, True, False), (True, True, True)],
)
async def test_permissions(exposed, authenticated, allowed):
    user = SimpleNamespace(
        is_admin=False,
        permissions=SimpleNamespace(check_entity=Mock(return_value=allowed)),
    )
    hass = SimpleNamespace(
        auth=SimpleNamespace(async_get_user=AsyncMock(return_value=user))
    )
    context = SimpleNamespace(
        context=Context(user_id="user" if authenticated else None)
    )
    args = {
        "entity_id": ENTITY,
        "start_time": START.isoformat(),
        "end_time": (START + timedelta(days=7)).isoformat(),
    }
    with patch.object(
        module, "_get_vtherm_entity_ids", return_value=[ENTITY] if exposed else []
    ), patch.object(
        module, "async_export_history", new=AsyncMock(return_value={"rows": []})
    ) as export:
        result = await module.GetVThermHistoryTool([ENTITY]).async_call(
            hass, SimpleNamespace(tool_args=args), context
        )
    if exposed and authenticated and allowed:
        assert result.data == {"rows": []}
        assert user.permissions.check_entity.call_args.args[1] == "read"
    else:
        assert result.error
        export.assert_not_awaited()
    assert module.GetVThermHistoryTool.annotations.read_only


@pytest.mark.freeze_time("2026-10-01 00:00:00")
async def test_native_recorder(recorder_mock, hass, freezer):
    from pytest_homeassistant_custom_component.components.recorder.common import (
        async_wait_recording_done,
    )

    freezer.move_to(START)
    hass.states.async_set(
        ENTITY, "heat", {"current_temperature": 18, "temperature": 20}
    )
    await async_wait_recording_done(hass)
    freezer.move_to(START + timedelta(minutes=2))
    hass.states.async_set(
        ENTITY, "heat", {"current_temperature": 19, "temperature": 20}
    )
    await async_wait_recording_done(hass)
    freezer.move_to(START + timedelta(minutes=4))
    result = await async_export_history(
        hass,
        ENTITY,
        START.isoformat(),
        (START + timedelta(minutes=4)).isoformat(),
        0,
        500,
    )
    assert [r["attributes"]["current_temperature"] for r in result["rows"]] == [18, 19]
    assert result["pagination_complete"]


@pytest.fixture
def mock_recorder_before_hass(recorder_db_url):
    """Prepare Recorder before the project autouse HA fixture."""


async def test_missing_recorder():
    hass = SimpleNamespace(config=SimpleNamespace(components=set()))
    with pytest.raises(ValueError, match="recorder_unavailable"):
        await async_export_history(
            hass,
            ENTITY,
            START.isoformat(),
            (START + timedelta(days=1)).isoformat(),
            0,
            500,
        )


@pytest.mark.parametrize("args", [{"limit": 501}, {"limit": 0}, {"offset": -1}])
async def test_invalid_paging(args):
    result = await module.GetVThermHistoryTool([ENTITY]).async_call(
        None,
        SimpleNamespace(
            tool_args={
                "entity_id": ENTITY,
                "start_time": START.isoformat(),
                "end_time": (START + timedelta(days=1)).isoformat(),
                **args,
            }
        ),
        None,
    )
    assert result.data["error"] == "invalid_parameters"


def test_shared_reader_preserves_raw_states_and_query_semantics():
    """TPI needs full sensor attributes and subminute event timestamps."""
    early = State(
        "sensor.inside",
        "20",
        {"unit_of_measurement": "°C", "extra": "kept"},
        last_updated=START,
    )
    late = State(
        "sensor.inside", "unavailable", last_updated=START + timedelta(seconds=30)
    )
    heater = State("switch.heater", "on", last_updated=START - timedelta(minutes=1))
    with patch(
        "custom_components.versatile_thermostat.recorder_export.history.get_significant_states",
        return_value={"sensor.inside": [late, early], "switch.heater": [heater]},
    ) as query:
        result = read_recorder_history(
            None, START, START + timedelta(days=14), ["sensor.inside", "switch.heater"]
        )
    assert result["sensor.inside"] == [early, late]
    assert result["sensor.inside"][0] is early
    assert result["sensor.inside"][0].attributes["extra"] == "kept"
    assert result["sensor.inside"][1].state == "unavailable"
    assert result["switch.heater"][0].last_updated == START - timedelta(minutes=1)
    assert query.call_args.args[1] == START - timedelta(microseconds=1)
    assert query.call_args.kwargs == {
        "end_time": START + timedelta(days=14),
        "entity_ids": ["sensor.inside", "switch.heater"],
        "include_start_time_state": True,
        "significant_changes_only": False,
        "minimal_response": False,
        "no_attributes": False,
    }


@pytest.mark.freeze_time("2026-10-01 00:00:00")
async def test_export_and_tpi_share_native_boundary_events(
    recorder_mock, hass, freezer
):
    """One real Recorder supplies identical boundary states to both consumers."""
    import numpy as np
    from homeassistant.components.recorder import get_instance
    from pytest_homeassistant_custom_component.components.recorder.common import (
        async_wait_recording_done,
    )
    from custom_components.versatile_thermostat.tpi_history import TPIHistory

    sources = {
        "temperature_source": "sensor.inside",
        "external_temperature_source": "sensor.outside",
        "heating_source": "switch.heater",
        "climate_source": ENTITY,
        "window_source": "binary_sensor.window",
        "safety_source": "binary_sensor.safety",
        "power_source": None,
        "inverse_switch": False,
        "primary_resolution": 10,
    }
    freezer.move_to(START - timedelta(minutes=1))
    hass.states.async_set("sensor.inside", "19", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.outside", "8", {"unit_of_measurement": "°C"})
    hass.states.async_set("switch.heater", "off")
    hass.states.async_set(
        ENTITY, "heat", {"current_temperature": 19, "temperature": 20}
    )
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set("binary_sensor.safety", "off")
    await async_wait_recording_done(hass)
    freezer.move_to(START)
    hass.states.async_set("sensor.inside", "20", {"unit_of_measurement": "°C"})
    hass.states.async_set("switch.heater", "on")
    # Attribute-only changes must survive on the climate too.
    hass.states.async_set(
        ENTITY, "heat", {"current_temperature": 20, "temperature": 20}
    )
    await async_wait_recording_done(hass)
    for seconds, state in [(30, "off"), (60, "unavailable"), (90, "on")]:
        freezer.move_to(START + timedelta(seconds=seconds))
        hass.states.async_set("switch.heater", state)
        await async_wait_recording_done(hass)
    end = START + timedelta(minutes=2)
    freezer.move_to(end)
    raw = await get_instance(hass).async_add_executor_job(
        partial(
            read_recorder_history,
            hass,
            START,
            end,
            [
                value
                for key, value in sources.items()
                if key.endswith("_source") and value
            ],
        )
    )
    exported = await async_export_history(
        hass, ENTITY, START.isoformat(), end.isoformat(), 0, 500
    )
    assert [row["attributes"]["current_temperature"] for row in exported["rows"]] == [
        state.attributes["current_temperature"] for state in raw[ENTITY]
    ]
    assert any(
        row["attributes"]["current_temperature"] == 20
        and row["timestamp"] == START.isoformat()
        for row in exported["rows"]
    )
    grid, _ = TPIHistory(None, sources).build_grid(raw, START, end)
    np.testing.assert_equal(grid.temp_in, [20, 20])
    np.testing.assert_equal(grid.heater, [0.5, np.nan])
    full_grid, _ = await TPIHistory(hass, sources).async_load()
    selected = (full_grid.time >= START.timestamp() / 60) & (
        full_grid.time < end.timestamp() / 60
    )
    np.testing.assert_equal(full_grid.temp_in[selected], grid.temp_in)
    np.testing.assert_equal(full_grid.heater[selected], grid.heater)
