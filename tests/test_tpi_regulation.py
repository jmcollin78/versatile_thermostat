"""Effective regulation eligibility, independent of thermostat hardware type."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.versatile_thermostat.tpi_history import TPIHistory
from custom_components.versatile_thermostat.tpi_identification import (
    IdentificationError,
)
from .tpi_runtime import native_runtime


def thermostat(learning=False, continuous=False):
    return native_runtime(
        SimpleNamespace(proportional_function="tpi", entry_infos={}),
        learning,
        continuous,
    )


@pytest.mark.parametrize(
    "config", [{}, {"auto_tpi_mode": True}, {"auto_tpi_continuous_kext": True}]
)
def test_inactive_options_and_residual_data_are_accepted(config):
    t = thermostat(continuous=False)
    t.entry_infos = config
    t.auto_tpi_manager.state.coeff_outdoor_autolearn = 20
    t.auto_tpi_manager.state.coeff_outdoor_heat = 0.8
    result = TPIHistory.check_classic_tpi(t)
    assert result["compatible"] is True
    assert result["detected_regulation"] == "classic_tpi"
    assert result["continuous_kext_affects_regulation"] is False


@pytest.mark.parametrize(
    "change,criterion",
    [
        ("learning", "auto_tpi_learning_active"),
        ("continuous", "continuous_kext_can_update_coefficients"),
        ("smartpi", "non_tpi_algorithm_selected"),
        ("unknown", "missing_proportional_function"),
        ("handler", "unverified_tpi_runtime"),
        ("manager", "unverified_auto_tpi_state"),
        ("contradictory", "inconsistent_auto_tpi_state"),
    ],
)
def test_precise_refusals(change, criterion):
    t = thermostat()
    if change == "learning":
        t.auto_tpi_manager.state.autolearn_enabled = True
    elif change == "continuous":
        t.auto_tpi_manager._continuous_kext = True
    elif change == "smartpi":
        t.proportional_function = "smartpi"
    elif change == "unknown":
        del t.proportional_function
    elif change == "handler":
        t._algo_handler = None
    elif change == "manager":
        t.auto_tpi_manager = None
    else:
        t.auto_tpi_manager.state.autolearn_enabled = "off"
    with pytest.raises(IdentificationError) as exc:
        TPIHistory.check_classic_tpi(t)
    assert exc.value.regulation["blocking_criterion"] == criterion
    assert exc.value.regulation["compatible"] is False


async def test_native_handler_does_not_apply_continuous_learning_when_disabled():
    """Even a newly calculated Kext is not copied to the actual regulator."""
    t = thermostat(continuous=True)
    t.current_temperature = 20
    t.current_outdoor_temperature = 8
    t.target_temperature = 21
    t.vtherm_hvac_mode = "heat"
    t.power_manager = SimpleNamespace(is_overpowering_detected=False)
    t.tpi_coef_int, t.tpi_coef_ext = 0.3, 0.02
    t.recalculate = Mock()
    t.cycle_scheduler = SimpleNamespace(start_cycle=AsyncMock())
    t.on_percent = 0.5
    t.safe_on_percent = 0.5
    t.cycle_min = 5
    t.minimal_activation_delay = 0
    t.minimal_deactivation_delay = 0
    handler = t._algo_handler
    manager = t.auto_tpi_manager
    with patch.object(manager, "update", new=AsyncMock()), patch.object(
        manager,
        "calculate",
        new=AsyncMock(return_value={"tpi_coef_int": 2, "tpi_coef_ext": 0.8}),
    ), patch.object(handler, "_is_central_boiler_off", return_value=False):
        await handler.control_heating()
    assert t.prop_algorithm.tpi_coef_ext == 0.02
    assert t.tpi_coef_ext == 0.02
    t.recalculate.assert_not_called()
    t.cycle_scheduler.start_cycle.assert_awaited_once()
    manager.state.autolearn_enabled = True
    with patch.object(manager, "update", new=AsyncMock()), patch.object(
        manager,
        "calculate",
        new=AsyncMock(return_value={"tpi_coef_int": 2, "tpi_coef_ext": 0.8}),
    ), patch.object(handler, "_is_central_boiler_off", return_value=False):
        await handler.control_heating()
    assert t.prop_algorithm.tpi_coef_ext == 0.8
    assert t.tpi_coef_ext == 0.8
    t.recalculate.assert_called_once_with()
    assert t.cycle_scheduler.start_cycle.await_count == 2


@pytest.mark.parametrize(
    "missing", ["algorithm", "state", "continuous", "manager_link"]
)
def test_missing_runtime_information_is_never_assumed_inactive(missing):
    t = thermostat()
    if missing == "algorithm":
        t.prop_algorithm = None
    elif missing == "state":
        t.auto_tpi_manager.state = None
    elif missing == "continuous":
        t.auto_tpi_manager._continuous_kext = "off"
    else:
        t._algo_handler._auto_tpi_manager = None
    with pytest.raises(IdentificationError) as exc:
        TPIHistory.check_classic_tpi(t, allow_adaptive=True)
    assert exc.value.regulation["missing_information"]
    assert exc.value.regulation["detected_regulation"] != "auto_tpi"


@pytest.mark.parametrize(
    "learning,continuous", [(True, False), (False, True), (True, True)]
)
def test_adaptive_attempt_is_explicit_and_does_not_enable_write(learning, continuous):
    t = thermostat(learning, continuous)
    snapshot = TPIHistory.check_classic_tpi(t, allow_adaptive=True)
    assert snapshot["analysis_mode"] == "adaptive_exploratory"
    assert snapshot["compatible"] is False
    assert snapshot["model_limitation"]
    with pytest.raises(IdentificationError):
        TPIHistory.check_classic_tpi(t)


def test_contradictory_native_property_is_refused():
    from unittest.mock import PropertyMock
    from custom_components.versatile_thermostat.auto_tpi_manager import AutoTpiManager

    t = thermostat()
    with patch.object(
        AutoTpiManager, "learning_active", new_callable=PropertyMock, return_value=True
    ):
        with pytest.raises(IdentificationError) as exc:
            TPIHistory.check_classic_tpi(t, allow_adaptive=True)
    assert exc.value.regulation["blocking_criterion"] == "inconsistent_auto_tpi_state"


@pytest.mark.parametrize("hardware", ["over_switch", "over_valve"])
@pytest.mark.parametrize("continuous", [False, True])
@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_loaded_native_entity_uses_effective_runtime(
    hass, skip_hass_states_is_state, hardware, continuous
):
    from custom_components.versatile_thermostat import const as c
    from .commons import create_thermostat, MockConfigEntry

    entry = MockConfigEntry(
        domain=c.DOMAIN,
        title="regulation",
        unique_id="regulation",
        data={
            c.CONF_NAME: "regulation",
            c.CONF_THERMOSTAT_TYPE: (
                c.CONF_THERMOSTAT_SWITCH
                if hardware == "over_switch"
                else c.CONF_THERMOSTAT_VALVE
            ),
            c.CONF_TEMP_SENSOR: "sensor.inside",
            c.CONF_EXTERNAL_TEMP_SENSOR: "sensor.outside",
            c.CONF_CYCLE_MIN: 5,
            c.CONF_TEMP_MIN: 7,
            c.CONF_TEMP_MAX: 30,
            c.CONF_UNDERLYING_LIST: [
                "switch.heater" if hardware == "over_switch" else "number.valve"
            ],
            c.CONF_PROP_FUNCTION: "tpi",
            c.CONF_TPI_COEF_INT: 0.3,
            c.CONF_TPI_COEF_EXT: 0.02,
            c.CONF_AUTO_TPI_MODE: False,
            c.CONF_AUTO_TPI_CONTINUOUS_KEXT: continuous,
        },
    )
    entity = await create_thermostat(hass, entry, "climate.regulation")
    result = TPIHistory.check_classic_tpi(entity, allow_adaptive=True)
    assert result["auto_tpi_learning_active"] is False
    assert result["continuous_kext_enabled_at_runtime"] is continuous
    assert result["analysis_mode"] == (
        "adaptive_exploratory" if continuous else "fixed_coefficients"
    )
    assert entity.is_over_valve is (hardware == "over_valve")
    # Sensors/underlyings have not initialized in this lifecycle fixture.
    # Eligibility detection must still work; history retains its startup guard.
    with pytest.raises(IdentificationError, match="vtherm_not_initialized"):
        TPIHistory.resolve_sources(hass, entity)
