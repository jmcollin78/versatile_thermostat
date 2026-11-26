"""Test the AutoTpiManager class."""
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, timezone

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.versatile_thermostat.auto_tpi_manager import (
    AutoTpiManager,
    AutoTpiState,
    KINT_MAX_STEP,
    KINT_WINDOW_MIN_MINUTES,
    STORAGE_VERSION,
    STORAGE_KEY_PREFIX,
)
from custom_components.versatile_thermostat.const import (
    AUTO_TPI_EVENT,
    CONF_TPI_COEF_INT,
    CONF_TPI_COEF_EXT,
    CONF_NAME,
    CONF_THERMOSTAT_TYPE,
    CONF_THERMOSTAT_SWITCH,
    CONF_TEMP_SENSOR,
    CONF_EXTERNAL_TEMP_SENSOR,
    CONF_CYCLE_MIN,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_USE_WINDOW_FEATURE,
    CONF_USE_MOTION_FEATURE,
    CONF_USE_POWER_FEATURE,
    CONF_USE_PRESENCE_FEATURE,
    CONF_UNDERLYING_LIST,
    CONF_PROP_FUNCTION,
    PROPORTIONAL_FUNCTION_TPI,
    CONF_MINIMAL_ACTIVATION_DELAY,
    CONF_MINIMAL_DEACTIVATION_DELAY,
    CONF_AUTO_TPI_MODE,
    DOMAIN,
)
from custom_components.versatile_thermostat.prop_handler_tpi import TPIHandler
from custom_components.versatile_thermostat.prop_algo_tpi import TpiAlgorithm
from custom_components.versatile_thermostat.thermostat_prop import ThermostatProp
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_HEAT
from homeassistant.components.climate.const import HVACMode, PRESET_NONE
from .commons import MockConfigEntry, create_thermostat, send_temperature_change_event, send_ext_temperature_change_event

import logging
_LOGGER = logging.getLogger(__name__)

# Log test execution
@pytest.fixture(autouse=True)
def log_test_execution(request):
    """Log the start and end of each test."""
    _LOGGER.info("Starting test: %s", request.node.name)
    yield
    _LOGGER.info("Finished test: %s", request.node.name)

@pytest.fixture
def mock_hass():
    """Mock Home Assistant."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/test_path")
    hass.loop = MagicMock()
    hass.config_entries = MagicMock()
    return hass

@pytest.fixture
def mock_config_entry():
    """Mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {}
    return entry

@pytest.fixture
def mock_store():
    """Mock Storage."""
    with patch("custom_components.versatile_thermostat.auto_tpi_manager.Store") as mock_store_cls:
        store_instance = mock_store_cls.return_value
        store_instance.async_load = AsyncMock(return_value=None)
        store_instance.async_save = AsyncMock()
        yield store_instance

@pytest.fixture
def manager(mock_hass, mock_store, mock_config_entry):
    """Create a manager instance."""
    return AutoTpiManager(
        hass=mock_hass,
        config_entry=mock_config_entry,
        unique_id="test_id",
        name="test_name",
        cycle_min=5,
        coef_int=0.6,
        coef_ext=0.01,
        heater_heating_time=10,
    )


async def test_auto_tpi_mode_fires_local_event_name():
    """Test Auto TPI mode event uses the local event name."""
    thermostat = MagicMock()
    thermostat.entry_infos = {CONF_AUTO_TPI_MODE: True}
    thermostat._entry_infos = thermostat.entry_infos
    thermostat.prop_algorithm = None
    thermostat.tpi_coef_int = 0.5
    thermostat.tpi_coef_ext = 0.01
    thermostat.is_removed = False
    thermostat.entity_id = "climate.auto_tpi_test"
    thermostat.unique_id = "auto_tpi_test"
    thermostat.hass.config_entries.async_get_entry.return_value = None

    auto_tpi_manager = MagicMock()
    auto_tpi_manager._default_coef_int = 0.5
    auto_tpi_manager._default_coef_ext = 0.01
    auto_tpi_manager.learning_active = True
    auto_tpi_manager.start_learning = AsyncMock()
    auto_tpi_manager.stop_learning = AsyncMock()

    handler = TPIHandler(thermostat)
    handler._auto_tpi_manager = auto_tpi_manager

    await handler.async_set_auto_tpi_mode(True)

    thermostat.hass.bus.async_fire.assert_called_once_with(
        AUTO_TPI_EVENT,
        {
            "entity_id": "climate.auto_tpi_test",
            "auto_tpi_mode": True,
        },
    )


async def test_initialization(manager):
    """Test initialization with defaults."""
    assert manager._unique_id == "test_id"
    assert manager._name == "test_name"
    assert manager._cycle_min == 5
    assert manager.state.coeff_indoor_heat == 0.6
    assert manager.state.coeff_outdoor_heat == 0.01
    
    # Check storage initialization
    assert manager._store is not None

async def test_load_data_no_existing(manager, mock_store):
    """Test loading when no data exists."""
    mock_store.async_load.return_value = None
    
    await manager.async_load_data()
    
    # Should use defaults
    assert manager.state.coeff_indoor_heat == 0.6
    assert manager.state.coeff_outdoor_heat == 0.01
    assert manager.state.total_cycles == 0
    # Counters should be initialized with initial weight
    assert manager.state.coeff_indoor_autolearn == 1 

async def test_load_data_existing(manager, mock_store):
    """Test loading existing data."""
    existing_state = AutoTpiState(
        coeff_indoor_heat=0.3,
        coeff_outdoor_heat=0.05,
        total_cycles=100,
        coeff_indoor_autolearn=50,
        coeff_outdoor_autolearn=50
    )
    mock_store.async_load.return_value = existing_state.to_dict()
    
    await manager.async_load_data()
    
    assert manager.state.coeff_indoor_heat == 0.3
    assert manager.state.coeff_outdoor_heat == 0.05
    assert manager.state.total_cycles == 100
    assert manager.state.coeff_indoor_autolearn == 50

async def test_save_data(manager, mock_store):
    """Test saving data."""
    manager.state.total_cycles = 10
    await manager.async_save_data()
    
    mock_store.async_save.assert_called_once()
    saved_data = mock_store.async_save.call_args[0][0]
    assert saved_data["total_cycles"] == 10

async def test_update_state(manager):
    """Test updating transient state via update()."""
    await manager.update(
        room_temp=20.0,
        ext_temp=5.0,
        target_temp=21.0,
        hvac_mode="heat"
    )
    
    assert manager._current_temp_in == 20.0
    assert manager._current_temp_out == 5.0
    assert manager._current_target_temp == 21.0
    assert manager._current_hvac_mode == "heat"

async def test_should_learn_basic(manager):
    """Test _should_learn basic conditions."""
    manager.state.autolearn_enabled = True
    manager.state.last_power = 0.5  # 50%
    manager.state.previous_state = "heat"
    manager.state.last_order = 20
    manager.state.last_state = "heat"
    manager._current_temp_out = 0
    manager.state.last_temp_in = 19
    
    assert manager._should_learn() is True

async def test_should_learn_disabled(manager):
    """Test _should_learn when disabled."""
    manager.state.autolearn_enabled = False
    assert manager._should_learn() is False

async def test_should_learn_power_saturation(manager):
    """Test _should_learn power saturation."""
    manager.state.autolearn_enabled = True
    
    # 0%
    manager.state.last_power = 0.0
    assert manager._should_learn() is False
    
    # 100%
    manager.state.last_power = 1.0  # > 0.99
    assert manager._should_learn() is False

@pytest.mark.parametrize("hvac_mode,start_temp,end_temp", [("heat", 19.0, 18.5), ("cool", 23.0, 23.5)])
@pytest.mark.parametrize("continuous_kext", [False, True])
async def test_disabled_learning_does_not_report_cycle_failures(manager, mock_hass, hvac_mode, start_temp, end_temp, continuous_kext):
    """Completed cycles must not report failures for a stopped learning session."""
    manager.state.autolearn_enabled = False
    manager._continuous_kext = continuous_kext
    manager.state.coeff_indoor_autolearn = 30
    mock_hass.services = MagicMock(async_call=AsyncMock())

    for _ in range(2):
        await manager.update(room_temp=start_temp, ext_temp=5.0, target_temp=21.0, hvac_mode=hvac_mode)
        await manager.on_cycle_started(on_time_sec=300, off_time_sec=0, on_percent=1.0, hvac_mode=hvac_mode)
        manager.state.cycle_start_date = datetime.now(timezone.utc) - timedelta(minutes=5)
        manager._current_temp_in = end_temp
        await manager.on_cycle_completed()

    assert manager.state.total_cycles == 2
    assert manager.state.cycle_active is False
    assert manager.learning_active is False
    mock_hass.services.async_call.assert_not_called()


def _run_kint_window(manager, start_temp, end_temp, power=0.5, end_cycle_valid=True):
    """Open a Kint window at start_temp and close it at end_temp one window length later."""
    start = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
    window_min = max(KINT_WINDOW_MIN_MINUTES, manager.closed_loop_time_min)
    with patch("custom_components.versatile_thermostat.auto_tpi_manager.dt_util") as mock_dt:
        mock_dt.now.return_value = start
        manager.state.autolearn_enabled = True
        manager.state.last_state = "heat"
        manager.state.last_power = power
        manager._current_target_temp = 20.0
        manager._current_temp_in = start_temp
        manager._process_kint_window(True)
        opened = manager._kint_window_start

        mock_dt.now.return_value = start + timedelta(minutes=window_min)
        manager._current_temp_in = end_temp
        manager._process_kint_window(end_cycle_valid)
    return opened


async def test_kint_window_slow_rise_increases_kint(manager):
    """A rise slower than the target rate increases Kint by at most one bounded step."""
    manager.state.coeff_indoor_heat = 0.5

    opened = _run_kint_window(manager, start_temp=19.0, end_temp=19.05)

    assert opened is not None
    assert manager.state.coeff_indoor_heat == pytest.approx(0.5 * KINT_MAX_STEP)
    assert manager.state.last_learning_status == "learned_indoor_heat"
    assert manager.state.coeff_indoor_autolearn == 2


async def test_kint_window_fast_rise_decreases_kint(manager):
    """A rise faster than the target rate decreases Kint by at most one bounded step."""
    manager.state.coeff_indoor_heat = 0.5

    _run_kint_window(manager, start_temp=19.0, end_temp=19.9)

    assert manager.state.coeff_indoor_heat == pytest.approx(0.5 / KINT_MAX_STEP)


async def test_kint_window_not_opened_near_setpoint(manager):
    """No window starts when the gap to the setpoint is below the minimum gap."""
    manager.state.coeff_indoor_heat = 0.5

    opened = _run_kint_window(manager, start_temp=19.8, end_temp=19.8)

    assert opened is None
    assert manager.state.coeff_indoor_heat == 0.5


async def test_kint_window_reset_by_invalid_cycle(manager):
    """An invalid or saturated cycle closes the window without learning."""
    manager.state.coeff_indoor_heat = 0.5

    _run_kint_window(manager, start_temp=19.0, end_temp=19.05, end_cycle_valid=False)
    assert manager.state.coeff_indoor_heat == 0.5
    assert manager._kint_window_start is None

    _run_kint_window(manager, start_temp=19.0, end_temp=19.05, power=1.0)
    assert manager.state.coeff_indoor_heat == 0.5


async def test_kext_waits_for_settling_after_setpoint_change(manager):
    """Kext is not learned right after a setpoint change."""
    manager.state.autolearn_enabled = True
    manager.state.last_state = "heat"
    manager.state.last_order = 20.0
    manager.state.last_temp_in = 19.8
    manager.state.last_power = 0.5

    await manager.update(room_temp=19.8, ext_temp=5.0, hvac_mode="heat", target_temp=20.0)
    old_kext = manager.state.coeff_outdoor_heat
    await manager._perform_learning(19.8, 5.0)

    assert manager.state.last_learning_status == "kext_waiting_settling"
    assert manager.state.coeff_outdoor_heat == old_kext


async def test_kext_settling_requires_room_near_setpoint(manager):
    """After the settling time, Kext waits until the room came near the setpoint, or a long timeout."""
    start = datetime(2026, 1, 5, 6, 0, tzinfo=timezone.utc)
    t_cl = manager.closed_loop_time_min
    with patch("custom_components.versatile_thermostat.auto_tpi_manager.dt_util") as mock_dt:
        mock_dt.now.return_value = start
        await manager.update(room_temp=18.0, ext_temp=5.0, hvac_mode="heat", target_temp=20.0)

        mock_dt.now.return_value = start + timedelta(minutes=3.5 * t_cl)
        await manager.update(room_temp=19.2, ext_temp=5.0, hvac_mode="heat", target_temp=20.0)
        assert manager._is_settled_for_kext() is False

        await manager.update(room_temp=19.8, ext_temp=5.0, hvac_mode="heat", target_temp=20.0)
        assert manager._is_settled_for_kext() is True

        # A large static offset is still learned after the long timeout
        await manager.update(room_temp=18.0, ext_temp=5.0, hvac_mode="heat", target_temp=21.0)
        mock_dt.now.return_value = start + timedelta(minutes=3.5 * t_cl + 12.5 * t_cl)
        await manager.update(room_temp=19.0, ext_temp=5.0, hvac_mode="heat", target_temp=21.0)
        assert manager._is_settled_for_kext() is True


async def test_cycle_lifecycle(manager):
    """Test full cycle lifecycle."""
    # 1. Start Cycle
    await manager.on_cycle_started(
        on_time_sec=150,
        off_time_sec=150,
        on_percent=0.5,
        hvac_mode="heat"
    )
    
    assert manager.state.cycle_active is True
    assert manager.state.last_power == 0.5
    assert manager.state.last_state == "heat"

    # Simulate time passing (5 minutes) to satisfy cycle duration validation
    # cycle_min is 5 in fixture, so we set start date 5 mins ago
    manager.state.cycle_start_date = datetime.now(timezone.utc) - timedelta(minutes=5)

    # 2. Complete Cycle
    await manager.on_cycle_completed()

    assert manager.state.cycle_active is False
    assert manager.state.total_cycles == 1


async def test_update_state_with_boiler_off(manager):
    """Test updating state with central boiler off."""
    await manager.update(
        room_temp=20.0,
        ext_temp=5.0,
        target_temp=21.0,
        hvac_mode="heat",
        is_central_boiler_off=True
    )
    
    assert manager._central_boiler_off is True

async def test_should_learn_central_boiler_off(manager):
    """Test _should_learn when central boiler is off."""
    manager.state.autolearn_enabled = True
    manager.state.last_power = 0.5
    # Ensure other conditions are met
    manager.state.previous_state = "heat"
    manager.state.last_order = 20
    manager.state.last_state = "heat"
    manager._current_temp_out = 0
    manager.state.last_temp_in = 19
    
    manager._central_boiler_off = True
    assert manager._should_learn() is False
    assert manager._get_no_learn_reason() == "central_boiler_off"

async def test_should_learn_heating_failure(manager):
    """Test _should_learn when heating failure is detected."""
    manager.state.autolearn_enabled = True
    manager.state.last_power = 0.5
    # Ensure other conditions are met
    manager.state.previous_state = "heat"
    manager.state.last_order = 20
    manager.state.last_state = "heat"
    manager._current_temp_out = 0
    manager.state.last_temp_in = 19
    
    manager._current_is_heating_failure = True
    assert manager._should_learn() is False
    assert manager._get_no_learn_reason() == "heating_failure_detected"

async def test_initialization_reset_bug(manager):
    """Test that starting a new session resets coefficients even if reset_data is False."""
    # 1. Start learning (default coeffs are int=0.6, ext=0.01)
    await manager.start_learning(reset_data=True)
    
    # 2. Simulate learning changing the coefficients
    manager.state.coeff_indoor_heat = 0.5
    manager.state.coeff_outdoor_heat = 0.02
    
    # 3. Stop learning
    await manager.stop_learning()
    assert manager.state.autolearn_enabled is False
    
    # 4. Start learning again, treating it as a new session (was stopped)
    # We pass NEW target coefficients to simulate a config change
    # But we set reset_data=False (mimicking the "bug" condition where user didn't check reset)
    new_target_int = 0.8
    new_target_ext = 0.05
    
    await manager.start_learning(
        coef_int=new_target_int,
        coef_ext=new_target_ext,
        reset_data=False
    )
    
    # 5. Assertions
    # DESIRED BEHAVIOR (Fix): It resets to 0.8 and 0.05 because it was stopped
    # If the bug is present, this will fail (it will be 0.5 and 0.02)
    assert manager.state.coeff_indoor_heat == new_target_int
    assert manager.state.coeff_outdoor_heat == new_target_ext

async def test_update_realized_power(manager):
    """Test update_realized_power method."""
    manager.state.cycle_active = True
    manager.state.last_power = 0.8
    
    # Update with different value
    manager.update_realized_power(0.5)
    assert manager.state.last_power == 0.5
    
    # Update with same value (should log debug but change nothing)
    manager.update_realized_power(0.5)
    assert manager.state.last_power == 0.5

async def test_update_realized_power_no_cycle(manager):
    """Test update_realized_power when no cycle is active."""
    manager.state.cycle_active = False
    manager.state.last_power = 0.8
    
    # Should NOT update
    manager.update_realized_power(0.5)
    assert manager.state.last_power == 0.8


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_auto_tpi_realized_power_integration(
    hass: HomeAssistant, skip_hass_states_is_state: None
):
    """Test that initialized AutoTpiManager correctly receives realized power updates in integration."""
    
    # 1. Configure Thermostat with TPI and AutoTPI
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="AutoTpiTest",
        unique_id="auto_tpi_test_realized",
        data={
            CONF_NAME: "AutoTpiTest",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,  # 300 seconds
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,      # 10% of 300s
            CONF_MINIMAL_DEACTIVATION_DELAY: 30,    # 10% of 300s
            CONF_AUTO_TPI_MODE: True,
        },
    )

    # Setup initial states
    hass.states.async_set("switch.mock_switch", "off")
    hass.states.async_set("sensor.mock_temp_sensor", "18.0")
    hass.states.async_set("sensor.mock_ext_temp_sensor", "10.0")

    entity: ThermostatProp = await create_thermostat(
        hass, entry, "climate.autotpitest_realized"
    )
    assert entity
    assert entity._algo_handler
    assert entity._algo_handler._auto_tpi_manager
    manager = entity._algo_handler._auto_tpi_manager
    
    # Force startup done to allow control_heating
    entity._startup_done = True
    assert entity._startup_done
    
    # Ensure cycle is active so updates are processed
    manager.state.cycle_active = True
    
    # ---------------------------------------------------------
    # Case 1: Minimal Activation Delay (Forced OFF)
    # ---------------------------------------------------------
    # Request very low power (1%). Min activation is 10%. Should be forced to 0.
    
    # Setup conditions
    now = datetime.now()
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    assert entity.hvac_mode == HVACMode.HEAT
    
    await entity.async_set_preset_mode(PRESET_NONE)
    await entity.async_set_temperature(temperature=20.0)
    
    # Target 20, Current 19.98 (Delta 0.02), Ext 20 (Delta 0)
    # Coef_int=0.5 -> 0.5 * 0.02 = 0.01 (1%)
    # Coef_ext=0.01 * 0 = 0
    # Total = 1%. 3s < 30s. Forced to 0.
    
    await send_temperature_change_event(entity, 19.98, now)
    await send_ext_temperature_change_event(entity, 20.0, now) # No external contribution
    
    await entity.async_control_heating()
    
    assert entity.on_percent == 0.01 # The requested power is still 1%
    
    # 1% is below the minimal activation delay (10%), so e_eff is 0.0
    # Bypass scheduler tick loops, just spoof cycle validation variables
    from homeassistant.util import dt as dt_util
    
    manager.state.cycle_start_date = dt_util.now() - timedelta(minutes=5)
    manager.state.current_cycle_params = {"on_time_sec": 0, "off_time_sec": 300}
    manager.state.cycle_active = True
    
    await manager.on_cycle_completed(0.0) 
    assert manager.state.last_power == 0.0 # Realized power is 0%
    
    # ---------------------------------------------------------
    # Case 2: Minimal Deactivation Delay (Forced ON)
    # ---------------------------------------------------------
    # Request high power (95%). Min deactivation is 10% (30s).
    # 95% means 5% off = 15s. 15s < 30s. Forced to 100%.
    
    # Target 20. Current 18.1 (Delta 1.9).
    # Coef_int=0.5 * 1.9 = 0.95 (95%)
    await send_temperature_change_event(entity, 18.1, now)
    
    await entity.async_control_heating()
    
    assert abs(entity.on_percent - 0.95) < 0.001 # Requested 95%
    
    # 95% means 5% off which is below min deactivation delay (10%), so e_eff is 1.0 (forced ON)
    manager.state.cycle_start_date = dt_util.now() - timedelta(minutes=5)
    manager.state.current_cycle_params = {"on_time_sec": 300, "off_time_sec": 0}
    manager.state.cycle_active = True
    
    await manager.on_cycle_completed(1.0)
    assert manager.state.last_power == 1.0 # Realized 100%
    
    # ---------------------------------------------------------
    # Case 3: Max On Percent Clamping
    # ---------------------------------------------------------
    # Set max_on_percent to 0.5
    entity._max_on_percent = 0.5
    
    # Request 95% again.
    # Should be clamped to 50% by thermostat_prop.on_percent
    # 50% is 150s. Delays are 30s. No timing forcing.
    
    # We need to force a recalculation/control heating
    # Just calling control_heating again with same temps
    await entity.async_control_heating()
    
    assert entity.on_percent == 0.5 # Clamped
    
    # 50% is not forced by min delays, so e_eff equals clamped requested on_percent
    manager.state.cycle_start_date = dt_util.now() - timedelta(minutes=5)
    manager.state.current_cycle_params = {"on_time_sec": 150, "off_time_sec": 150}
    manager.state.cycle_active = True
    
    await manager.on_cycle_completed(0.5)
    assert manager.state.last_power == 0.5 # Realized matches clamped


class _FakeTpiThermostat:
    """Minimal thermostat double exposing what TPIHandler reads."""

    def __init__(self, coef_int, coef_ext, room_temp, ext_temp, target_temp):
        self.prop_algorithm = TpiAlgorithm(coef_int, coef_ext, "climate.fake_tpi")
        self.tpi_coef_int = coef_int
        self.tpi_coef_ext = coef_ext
        self.current_temperature = room_temp
        self.current_outdoor_temperature = ext_temp
        self.target_temperature = target_temp
        self.vtherm_hvac_mode = VThermHvacMode_HEAT
        self.cycle_min = 30
        self.minimal_activation_delay = 300
        self.minimal_deactivation_delay = 300
        self.is_used_by_central_boiler = False
        self.entity_id = "climate.fake_tpi"
        self.entry_infos = {CONF_AUTO_TPI_MODE: True}
        self.power_manager = SimpleNamespace(is_overpowering_detected=False)
        self.cycle_scheduler = SimpleNamespace(start_cycle=AsyncMock())

    @property
    def on_percent(self):
        """Effective on_percent, as read by the handler."""
        return self.prop_algorithm.on_percent

    def recalculate(self, force=False):
        """Recompute the algorithm demand from the current temperatures."""
        self.prop_algorithm.calculate(
            self.target_temperature,
            self.current_temperature,
            self.current_outdoor_temperature,
            None,
            self.vtherm_hvac_mode,
        )


async def test_control_heating_recalculates_demand_after_auto_tpi_coef_sync():
    """The cycle must use a demand computed with the synchronized coefficients."""
    thermostat = _FakeTpiThermostat(0.6, 0.01, room_temp=19.1, ext_temp=9.3, target_temp=21.5)
    # Demand cached with the configured coefficients: saturated at 100%
    thermostat.recalculate()
    assert thermostat.on_percent == 1.0

    auto_tpi_manager = MagicMock()
    auto_tpi_manager.learning_active = True
    auto_tpi_manager.update = AsyncMock()
    auto_tpi_manager.calculate = AsyncMock(return_value={CONF_TPI_COEF_INT: 0.068, CONF_TPI_COEF_EXT: 0.0088})

    handler = TPIHandler(thermostat)
    handler._auto_tpi_manager = auto_tpi_manager

    await handler.control_heating(force=True)

    assert thermostat.prop_algorithm.tpi_coef_int == 0.068
    assert thermostat.prop_algorithm.tpi_coef_ext == 0.0088
    # 0.068 * 2.4 + 0.0088 * 12.2 = 0.27
    thermostat.cycle_scheduler.start_cycle.assert_awaited_once_with(VThermHvacMode_HEAT, 0.27, True)


async def test_added_to_hass_applies_learned_coefs_to_algorithm():
    """Restored learned coefficients must reach the algorithm, not only the thermostat."""
    thermostat = _FakeTpiThermostat(0.6, 0.01, room_temp=19.1, ext_temp=9.3, target_temp=21.5)

    auto_tpi_manager = MagicMock()
    auto_tpi_manager.learning_active = True
    auto_tpi_manager.async_load_data = AsyncMock()
    auto_tpi_manager.get_calculated_params.return_value = {CONF_TPI_COEF_INT: 0.068, CONF_TPI_COEF_EXT: 0.0088}

    handler = TPIHandler(thermostat)
    handler._auto_tpi_manager = auto_tpi_manager

    await handler.async_added_to_hass()

    assert thermostat.tpi_coef_int == 0.068
    assert thermostat.tpi_coef_ext == 0.0088
    assert thermostat.prop_algorithm.tpi_coef_int == 0.068
    assert thermostat.prop_algorithm.tpi_coef_ext == 0.0088

    # The first demand computation uses the learned coefficients
    thermostat.recalculate()
    assert thermostat.on_percent == 0.27


async def test_climate_publishes_auto_tpi_diagnostics_entity(hass: HomeAssistant, skip_hass_states_is_state):
    """The climate publishes the Auto TPI learning sensor as its regulation diagnostics entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="AutoTpiDiag",
        unique_id="auto_tpi_diag",
        version=2,
        minor_version=5,
        data={
            CONF_NAME: "AutoTpiDiag",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 30,
            CONF_AUTO_TPI_MODE: True,
        },
    )

    entity: ThermostatProp = await create_thermostat(hass, entry, "climate.autotpidiag")
    assert entity

    entity.update_custom_attributes()
    diagnostic_entity_id = entity.extra_state_attributes["specific_states"]["regulation_diagnostics"]
    assert diagnostic_entity_id is not None
    assert diagnostic_entity_id.startswith("sensor.")
    assert hass.states.get(diagnostic_entity_id) is not None
