"""Central configuration is included without leaking unrelated settings or secrets."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Context, State

from custom_components.versatile_thermostat import llm
from custom_components.versatile_thermostat.llm import diagnostics

ENTITY = "climate.test"


@pytest.fixture
def central_setup(monkeypatch):
    central = SimpleNamespace(
        domain="versatile_thermostat",
        entry_id="central",
        disabled_by=None,
        state=ConfigEntryState.LOADED,
        data={
            "thermostat_type": "thermostat_central_config",
            "name": "Central",
            "tpi_coef_int": 0.6,
            "tpi_coef_ext": 0.01,
            "temp_min": 7,
            "lock_code": "SECRET",
            "password": "SECRET",
            "lock_users": True,
        },
    )
    local = SimpleNamespace(domain="versatile_thermostat", entry_id="local", data={})
    thermostat = SimpleNamespace(
        unique_id="uid",
        name="Test",
        entry_infos={
            "use_tpi_central_config": True,
            "use_lock_central_config": True,
            "tpi_coef_int": 0.6,
            "tpi_coef_ext": 0.01,
            "lock_code": "SECRET",
            "lock_users": True,
        },
    )
    registry_entry = SimpleNamespace(
        domain="climate",
        platform="versatile_thermostat",
        config_entry_id="local",
        unique_id="uid",
    )
    registry = SimpleNamespace(async_get=Mock(return_value=registry_entry))
    monkeypatch.setattr(diagnostics.er, "async_get", lambda hass: registry)
    exposed = Mock(return_value=True)
    monkeypatch.setattr(diagnostics, "async_should_expose", exposed)
    monkeypatch.setattr(llm, "_get_vtherm_entity_ids", lambda hass, context: [ENTITY])
    states = {
        ENTITY: State(
            ENTITY,
            "heat",
            {
                "configuration": {
                    "is_controlled_by_central_mode": True,
                    "is_used_by_central_boiler": False,
                },
                "specific_states": {"last_central_mode": "Auto"},
                "preset_temperatures": {"eco_temp": 17},
            },
        )
    }
    entries = [local, central]
    user = SimpleNamespace(
        is_admin=True, permissions=SimpleNamespace(check_entity=Mock(return_value=True))
    )
    hass = SimpleNamespace(
        states=SimpleNamespace(get=states.get),
        data={"climate": SimpleNamespace(get_entity=Mock(return_value=thermostat))},
        config_entries=SimpleNamespace(
            async_entries=Mock(return_value=entries),
            async_get_entry=Mock(return_value=local),
        ),
        auth=SimpleNamespace(async_get_user=AsyncMock(return_value=user)),
        services=SimpleNamespace(async_call=AsyncMock()),
    )
    context = SimpleNamespace(
        assistant="conversation", language="fr", context=Context(user_id="user")
    )
    return SimpleNamespace(
        hass=hass,
        context=context,
        central=central,
        local=local,
        thermostat=thermostat,
        entries=entries,
        user=user,
        states=states,
        exposed=exposed,
        registry_entry=registry_entry,
    )


async def invoke(setup, name):
    tool = (
        llm.ListVThermsTool()
        if name == "list"
        else (
            llm.DiagnoseVThermTool([ENTITY])
            if name == "diagnose"
            else llm.GetVThermStatusTool([ENTITY])
        )
    )
    result = await tool.async_call(
        setup.hass,
        SimpleNamespace(tool_args={} if name == "list" else {"entity_id": ENTITY}),
        setup.context,
    )
    setup.hass.services.async_call.assert_not_awaited()
    return result.data


@pytest.mark.parametrize("tool", ["list", "status", "diagnose"])
async def test_central_present_and_inherited_values(central_setup, tool):
    data = await invoke(central_setup, tool)
    central = data["central_configuration"]
    assert central["configured"] is True
    assert central["active"] is True
    assert central["settings"]["tpi"]["tpi_coef_int"] == 0.6
    usage = (
        data["thermostats"][0]["central_configuration"]
        if tool == "list"
        else central["thermostat"]
    )
    assert usage["uses_central_configuration"] is True
    assert usage["inheritance"]["tpi"] is True
    assert usage["inheritance"]["main"] is False
    assert usage["is_controlled_by_central_mode"] is True
    assert usage["last_central_mode"] == "Auto"
    assert usage["is_used_by_central_boiler"] is False
    assert "SECRET" not in json.dumps(data)


async def test_no_central_configuration(central_setup):
    central_setup.entries.remove(central_setup.central)
    data = await invoke(central_setup, "diagnose")
    assert data["central_configuration"]["configured"] is False
    assert data["central_configuration"]["settings"] == {}
    assert data["central_configuration"]["thermostat"]["inheritance"]["tpi"] is True
    assert (
        data["central_configuration"]["thermostat"]["uses_central_configuration"]
        is False
    )


async def test_mode_participation_does_not_imply_inheritance(central_setup):
    central_setup.thermostat.entry_infos = {}
    data = await invoke(central_setup, "diagnose")
    usage = data["central_configuration"]["thermostat"]
    assert usage["is_controlled_by_central_mode"] is True
    assert usage["uses_central_configuration"] is False


@pytest.mark.parametrize(
    "scenario",
    ["anonymous", "missing_user", "denied", "unexposed", "foreign", "orphan"],
)
async def test_central_settings_require_authorized_loaded_target(
    central_setup, scenario
):
    if scenario == "anonymous":
        central_setup.context.context = None
    elif scenario == "missing_user":
        central_setup.hass.auth.async_get_user.return_value = None
    elif scenario == "denied":
        central_setup.user.is_admin = False
        central_setup.user.permissions.check_entity.return_value = False
    elif scenario == "unexposed":
        central_setup.exposed.return_value = False
    elif scenario == "foreign":
        central_setup.registry_entry.platform = "other"
    else:
        central_setup.hass.data["climate"].get_entity.return_value = None
    data = await invoke(central_setup, "status")
    assert data["central_configuration"]["configured"] is None
    assert "settings" not in data["central_configuration"]
    central_setup.hass.config_entries.async_entries.assert_not_called()


async def test_nonadmin_sees_only_used_groups(central_setup):
    central_setup.user.is_admin = False
    data = await invoke(central_setup, "diagnose")
    assert set(data["central_configuration"]["settings"]) == {"tpi", "lock"}
    central_setup.user.permissions.check_entity.assert_called_with(ENTITY, "read")


async def test_disabled_central_is_present_but_not_used(central_setup):
    central_setup.central.disabled_by = "user"
    data = await invoke(central_setup, "diagnose")
    central = data["central_configuration"]
    assert central["configured"] is True
    assert central["active"] is False
    assert central["thermostat"]["uses_central_configuration"] is False


async def test_presets_are_effective_values_not_stale_entry_data(central_setup):
    central_setup.thermostat.entry_infos["use_presets_central_config"] = True
    central_setup.central.data["eco_temp"] = 5
    data = await invoke(central_setup, "diagnose")
    assert data["central_configuration"]["thermostat"][
        "effective_preset_temperatures"
    ] == {"eco_temp": 17}
    assert "eco_temp" not in data["central_configuration"]["settings"].get(
        "presets", {}
    )


async def test_power_units_keep_central_and_effective_values_separate(central_setup):
    central_setup.central.data["power_unit"] = "auto"
    central_setup.thermostat.entry_infos.update(
        use_power_central_config=True, power_unit="kW"
    )
    data = await invoke(central_setup, "diagnose")
    central = data["central_configuration"]
    assert central["settings"]["power"]["power_unit"] == "auto"
    assert central["thermostat"]["effective_settings"]["power"]["power_unit"] == "kW"


async def test_multiple_active_centrals_do_not_guess(central_setup):
    central_setup.entries.append(
        SimpleNamespace(**{**vars(central_setup.central), "entry_id": "other"})
    )
    data = await invoke(central_setup, "diagnose")
    assert data["central_configuration"]["status"] == "ambiguous"
    assert data["central_configuration"]["active"] is None
    assert data["central_configuration"]["settings"] == {}


async def test_list_does_not_disclose_unreadable_thermostat_inheritance(
    central_setup, monkeypatch
):
    other = "climate.hidden_details"
    monkeypatch.setattr(
        llm, "_get_vtherm_entity_ids", lambda hass, context: [ENTITY, other]
    )
    central_setup.states[other] = State(other, "heat")
    central_setup.user.is_admin = False
    central_setup.user.permissions.check_entity.side_effect = (
        lambda entity_id, policy: entity_id == ENTITY
    )
    data = await invoke(central_setup, "list")
    assert data["thermostats"][1]["central_configuration"]["configured"] is None
    assert "inheritance" not in data["thermostats"][1]["central_configuration"]


async def test_central_read_failure_preserves_state_diagnosis(central_setup):
    central_setup.hass.config_entries.async_entries.side_effect = RuntimeError(
        "private failure"
    )
    data = await invoke(central_setup, "diagnose")
    assert data["central_configuration"]["configured"] is None
    assert data["current"]["entity_id"] == ENTITY
    assert "private failure" not in json.dumps(data)


async def test_central_fields_are_projected_not_config_dump(central_setup):
    central_setup.central.data.update(
        use_central_boiler_feature=True,
        central_boiler_activation_delay_sec=60,
        central_boiler_activation_service="SECRET",
        failure_detection_enable_template="SECRET",
        custom_plugin={"token": "SECRET"},
    )
    data = await invoke(central_setup, "status")
    central = data["central_configuration"]
    assert central["features"]["use_central_boiler_feature"] is True
    assert central["boiler_settings"]["central_boiler_activation_delay_sec"] == 60
    assert "SECRET" not in json.dumps(data)


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_loaded_ha_thermostat_reports_actual_central_merge(
    hass, init_vtherm_api, fake_underlying_switch, monkeypatch
):
    """Exercise real registry, central ConfigEntry and BaseThermostat merge."""
    from pytest_homeassistant.common import MockConfigEntry
    from .commons import (
        FULL_CENTRAL_CONFIG,
        FULL_SWITCH_CONFIG,
        create_central_config,
        create_thermostat,
    )

    await create_central_config(hass, {**FULL_CENTRAL_CONFIG, "tpi_coef_int": 0.72})
    local = MockConfigEntry(
        domain="versatile_thermostat",
        title="Central Test",
        unique_id="central-test",
        data={
            **FULL_SWITCH_CONFIG,
            "name": "Central Test",
            "use_main_central_config": True,
            "use_tpi_central_config": True,
            "tpi_coef_int": 0.11,
            "use_window_feature": False,
            "use_motion_feature": False,
            "use_presence_feature": False,
            "use_power_feature": False,
        },
    )
    thermostat = await create_thermostat(hass, local, "climate.central_test")
    assert thermostat.entry_infos["tpi_coef_int"] == 0.72
    monkeypatch.setattr(diagnostics, "async_should_expose", lambda *args: True)
    monkeypatch.setattr(
        hass.auth,
        "async_get_user",
        AsyncMock(return_value=SimpleNamespace(is_admin=True)),
    )
    context = SimpleNamespace(
        assistant="conversation", language="fr", context=Context(user_id="user")
    )
    result = await llm.DiagnoseVThermTool([thermostat.entity_id]).async_call(
        hass, SimpleNamespace(tool_args={"entity_id": thermostat.entity_id}), context
    )
    central = result.data["central_configuration"]
    assert central["configured"] is True
    assert central["active"] is True
    assert central["settings"]["tpi"]["tpi_coef_int"] == 0.72
    assert central["thermostat"]["effective_settings"]["tpi"]["tpi_coef_int"] == 0.72
    assert local.data["tpi_coef_int"] == 0.11
