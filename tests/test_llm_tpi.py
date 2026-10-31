"""Boundary tests for TPI LLM tools, permissions, confirmation and readback."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError

from custom_components.versatile_thermostat import llm as module
from custom_components.versatile_thermostat.tpi_history import (
    async_load_history,
    history_sources,
)
from custom_components.versatile_thermostat.tpi_identification import (
    IdentificationError,
)

ENTITY = "climate.test"


@pytest.fixture
def setup_tools():
    thermostat = SimpleNamespace(
        proportional_function="tpi",
        entry_infos={},
        auto_tpi_manager=None,
        tpi_coef_int=0.3,
        tpi_coef_ext=0.02,
    )

    async def service(domain, name, data, **kwargs):
        thermostat.tpi_coef_int = data.get("tpi_coef_int", thermostat.tpi_coef_int)
        thermostat.tpi_coef_ext = data.get("tpi_coef_ext", thermostat.tpi_coef_ext)

    user = SimpleNamespace(
        is_admin=False,
        permissions=SimpleNamespace(check_entity=Mock(return_value=True)),
    )
    hass = SimpleNamespace(
        data={},
        auth=SimpleNamespace(async_get_user=AsyncMock(return_value=user)),
        services=SimpleNamespace(async_call=AsyncMock(side_effect=service)),
    )
    context = SimpleNamespace(
        context=Context(user_id="user"), language="fr", assistant="conversation"
    )
    with patch.object(
        module, "_get_vtherm_entity_ids", return_value=[ENTITY]
    ), patch.object(module, "get_thermostat", return_value=thermostat):
        yield hass, thermostat, context


async def call(setup, **args):
    hass, _, context = setup
    return await module.SetTPICoefficientsTool([ENTITY]).async_call(
        hass, SimpleNamespace(tool_args={"entity_id": ENTITY, **args}), context
    )


@pytest.mark.parametrize(
    "args",
    [{"coef_int": 0.32}, {"coef_ext": 0.022}, {"coef_int": 0.32, "coef_ext": 0.022}],
)
async def test_direct_partial_or_both_and_service_context(setup_tools, args):
    hass, _, context = setup_tools
    result = await call(setup_tools, **args)
    assert result.data["status"] == "success"
    assert result.data["previous"] == {"coef_int": 0.3, "coef_ext": 0.02}
    for key, value in args.items():
        assert result.data["applied"][key] == value
    hass.services.async_call.assert_awaited_once_with(
        "versatile_thermostat",
        "set_tpi_parameters",
        {"entity_id": ENTITY, **{f"tpi_{k}": v for k, v in args.items()}},
        blocking=True,
        context=context.context,
    )
    assert result.data["stage_number"] == 3


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"coef_int": -1},
        {"coef_int": 11},
        {"coef_ext": 1.1},
        {"coef_int": True},
        {"coef_ext": "nan"},
        {"coef_int": "inf"},
        {"coef_int": "bad"},
    ],
)
async def test_invalid_values_never_call_service(setup_tools, args):
    result = await call(setup_tools, **args)
    assert result.data["reason"] == "invalid_value"
    setup_tools[0].services.async_call.assert_not_awaited()


@pytest.mark.parametrize("authenticated,allowed", [(False, True), (True, False)])
async def test_permissions(setup_tools, authenticated, allowed):
    hass, _, context = setup_tools
    if not authenticated:
        context.context = Context()
    else:
        hass.auth.async_get_user.return_value.permissions.check_entity.return_value = (
            allowed
        )
    result = await call(setup_tools, coef_int=0.32)
    assert result.data["reason"] == "permission_denied"
    hass.services.async_call.assert_not_awaited()


async def test_large_change_requires_bound_confirmation(setup_tools):
    hass, thermostat, _ = setup_tools
    first = await call(
        setup_tools, coef_int=0.62, coef_ext=0.047, confirm_large_change=True
    )
    assert first.data["confirmation_required"] is True
    assert first.data["state_changed"] is False
    hass.services.async_call.assert_not_awaited()
    result = await call(
        setup_tools,
        coef_int=0.62,
        coef_ext=0.047,
        confirm_large_change=True,
        confirmation_token=first.data["confirmation_token"],
    )
    assert result.data["applied"] == {"coef_int": 0.62, "coef_ext": 0.047}
    assert result.data["state_changed"] is True
    assert thermostat.tpi_coef_int == 0.62


async def test_changed_request_cannot_reuse_confirmation(setup_tools):
    first = await call(setup_tools, coef_int=0.62)
    result = await call(
        setup_tools,
        coef_int=0.8,
        confirm_large_change=True,
        confirmation_token=first.data["confirmation_token"],
    )
    assert result.data["reason"] == "large_change_confirmation_required"
    setup_tools[0].services.async_call.assert_not_awaited()


async def test_current_values_changed_since_confirmation(setup_tools):
    first = await call(setup_tools, coef_int=0.62)
    setup_tools[1].tpi_coef_int = 0.31
    result = await call(
        setup_tools,
        coef_int=0.62,
        confirm_large_change=True,
        confirmation_token=first.data["confirmation_token"],
    )
    assert result.data["reason"] == "large_change_confirmation_required"


async def test_service_failure_unknown_application_and_locked_readback(setup_tools):
    hass = setup_tools[0]
    hass.services.async_call.side_effect = HomeAssistantError("failed")
    result = await call(setup_tools, coef_int=0.32)
    assert result.data["reason"] == "service_call_failed"
    assert result.data["state_changed"] is None
    hass.services.async_call.side_effect = (
        None  # e.g. lock silently ignores the service
    )
    with patch.object(module.asyncio, "sleep", new=AsyncMock()):
        result = await call(setup_tools, coef_int=0.32)
    assert result.data["reason"] == "readback_failed"
    assert result.data["applied"]["coef_int"] == 0.3


async def test_idempotent_write(setup_tools):
    result = await call(setup_tools, coef_int=0.3, coef_ext=0.02)
    assert result.data["status"] == "success"
    assert result.data["state_changed"] is False


async def test_exposure_rechecked_at_call_time(setup_tools):
    with patch.object(module, "_get_vtherm_entity_ids", return_value=[]):
        result = await call(setup_tools, coef_int=0.32)
    assert result.data["reason"] == "entity_not_exposed"
    setup_tools[0].services.async_call.assert_not_awaited()


@pytest.mark.parametrize(
    "tool_class,stage",
    [(module.CheckTPIOptimizationTool, 1), (module.AnalyzeTPICoefficientsTool, 2)],
)
async def test_read_tools_unsupported_type_explicit_and_no_service(
    setup_tools, tool_class, stage
):
    hass, _, context = setup_tools
    with patch.object(
        module,
        "history_sources",
        side_effect=IdentificationError("unsupported_thermostat_type"),
    ):
        result = await tool_class([ENTITY]).async_call(
            hass, SimpleNamespace(tool_args={"entity_id": ENTITY}), context
        )
    assert result.data["reason"] == "unsupported_thermostat_type"
    assert result.data["supported"] is False
    assert "pas encore disponible" in result.data["message"]
    assert result.data["stage_number"] == stage
    assert tool_class.annotations.read_only is True
    hass.services.async_call.assert_not_awaited()
    assert module.SetTPICoefficientsTool.annotations.read_only is False


async def test_recorder_query_bounded_to_fourteen_days():
    sources = {
        "temperature_source": "sensor.in",
        "external_temperature_source": "sensor.out",
        "heating_source": "switch.a",
        "heating_sources": ["switch.a", "switch.b"],
        "climate_source": ENTITY,
        "window_source": None,
        "safety_source": "binary_sensor.safety",
        "power_source": None,
    }
    recorder = SimpleNamespace(async_add_executor_job=AsyncMock(return_value={}))
    hass = SimpleNamespace(
        config=SimpleNamespace(components={"recorder"}),
        async_add_executor_job=AsyncMock(return_value=(None, {})),
    )
    with patch(
        "custom_components.versatile_thermostat.tpi_history.get_instance",
        return_value=recorder,
    ):
        await async_load_history(hass, sources)
    query = recorder.async_add_executor_job.call_args.args[0]
    from custom_components.versatile_thermostat.recorder_export import (
        read_recorder_history,
    )

    assert query.func is read_recorder_history
    assert query.args[2] - query.args[1] == timedelta(days=14)
    assert query.args[3] == [
        "sensor.in",
        "sensor.out",
        "binary_sensor.safety",
        ENTITY,
        "switch.a",
        "switch.b",
    ]


@pytest.mark.parametrize("over_switch", [False])
def test_unsupported_before_non_tpi(over_switch):
    with pytest.raises(IdentificationError, match="unsupported_thermostat_type"):
        history_sources(None, SimpleNamespace(is_over_switch=over_switch))


async def test_confirmation_expired(setup_tools):
    first = await call(setup_tools, coef_int=0.62)
    pending = setup_tools[0].data[module.TPI_TOOL_DATA]["confirmations"][
        ("user", ENTITY)
    ]
    pending["expires"] = 0
    result = await call(
        setup_tools,
        coef_int=0.62,
        confirm_large_change=True,
        confirmation_token=first.data["confirmation_token"],
    )
    assert result.data["reason"] == "large_change_confirmation_required"
    setup_tools[0].services.async_call.assert_not_awaited()


async def test_check_does_not_fit_or_bootstrap(setup_tools):
    hass, _, context = setup_tools
    with patch.object(module, "history_sources", return_value={}), patch.object(
        module,
        "async_load_history",
        new=AsyncMock(
            return_value=(
                None,
                {"history_available_days": 10, "history_usable_days": 9},
            )
        ),
    ), patch.object(module, "analyze_grid") as analysis:
        result = await module.CheckTPIOptimizationTool([ENTITY]).async_call(
            hass, SimpleNamespace(tool_args={"entity_id": ENTITY}), context
        )
    assert result.data["eligible"] is True
    assert result.data["state_changed"] is False
    analysis.assert_not_called()
    hass.services.async_call.assert_not_awaited()


async def test_direct_write_rejects_auto_tpi_without_history(setup_tools):
    setup_tools[1].entry_infos["auto_tpi_mode"] = True
    result = await call(setup_tools, coef_int=0.32)
    assert result.data["reason"] == "not_classic_tpi"
    setup_tools[0].services.async_call.assert_not_awaited()


async def test_successful_analysis_only_returns_proposal(setup_tools):
    hass, _, context = setup_tools
    hass.async_add_executor_job = AsyncMock(
        return_value={
            "status": "success",
            "proposed": {"coef_int": 0.35, "coef_ext": 0.025, "closed_loop_hours": 6},
            "warnings": [],
        }
    )
    with patch.object(
        module, "history_sources", return_value={"primary_resolution": 10}
    ), patch.object(
        module,
        "async_load_history",
        new=AsyncMock(
            return_value=(
                object(),
                {"history_available_days": 10, "history_usable_days": 9},
            )
        ),
    ):
        result = await module.AnalyzeTPICoefficientsTool([ENTITY]).async_call(
            hass, SimpleNamespace(tool_args={"entity_id": ENTITY}), context
        )
    assert result.data["proposed"]["coef_int"] == 0.35
    assert result.data["state_changed"] is False
    assert result.data["comparison"]["coef_int"]["previous"] == 0.3
    hass.services.async_call.assert_not_awaited()


async def test_recorder_missing_explicit_refusal():
    hass = SimpleNamespace(config=SimpleNamespace(components=set()))
    with pytest.raises(IdentificationError, match="recorder_unavailable"):
        await async_load_history(hass, {})
