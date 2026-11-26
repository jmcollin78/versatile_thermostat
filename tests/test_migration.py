# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

"""Test the Security featrure"""

from unittest.mock import patch, call, PropertyMock, MagicMock
from datetime import timedelta, datetime
import logging
import asyncio

from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat import (
    _is_auto_start_stop_migration_eligible,
    _migrate_auto_start_stop_entry,
    async_migrate_auto_start_stop,
    async_migrate_entry,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "feature_enabled, marker_present, expected",
    [
        (False, False, False),
        (False, True, False),
        (True, False, True),
        (True, True, False),
    ],
)
def test_auto_start_stop_migration_eligibility(feature_enabled, marker_present, expected):
    """Migration only applies to enabled entries without a migration marker."""
    entry_data = {CONF_USE_AUTO_START_STOP_FEATURE: feature_enabled}
    if marker_present:
        entry_data[CONF_AUTO_START_STOP_MIGRATED_BY] = AUTO_START_STOP_MIGRATED_BY_VTHERM_AUTO_START_STOP

    assert _is_auto_start_stop_migration_eligible(entry_data) is expected


def _auto_start_stop_entry() -> MockConfigEntry:
    """Build an over_climate entry using the core auto-start/stop feature."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="autoStartStopMigrationId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_USE_AUTO_START_STOP_FEATURE: True,
            CONF_AUTO_START_STOP_LEVEL: AUTO_START_STOP_LEVEL_MEDIUM,
        },
    )


async def test_migration_writes_marker_and_clears_flag_but_keeps_level(hass: HomeAssistant):
    """The migration disables the core feature and keeps the level for the plugin."""
    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)

    assert await _migrate_auto_start_stop_entry(hass, entry) is True

    assert entry.data[CONF_USE_AUTO_START_STOP_FEATURE] is False
    assert entry.data[CONF_AUTO_START_STOP_MIGRATED_BY] == AUTO_START_STOP_MIGRATED_BY_VTHERM_AUTO_START_STOP
    assert entry.data[CONF_AUTO_START_STOP_LEVEL] == AUTO_START_STOP_LEVEL_MEDIUM


async def test_migration_is_idempotent(hass: HomeAssistant):
    """A second run on a marked entry writes nothing."""
    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    assert await _migrate_auto_start_stop_entry(hass, entry) is True
    migrated_data = dict(entry.data)

    assert await _migrate_auto_start_stop_entry(hass, entry) is False
    assert entry.data == migrated_data


async def test_migration_without_external_manager_leaves_entry_untouched(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """A thermostat the plugin does not cover keeps its core feature."""
    await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=["1", "2", "3", "auto"],
    )
    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await async_migrate_auto_start_stop(hass) == 0
    assert entry.data[CONF_USE_AUTO_START_STOP_FEATURE] is True
    assert CONF_AUTO_START_STOP_MIGRATED_BY not in entry.data


async def test_migration_failure_on_one_thermostat_does_not_block_others(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event, caplog):
    """A failing thermostat is logged and the remaining ones are still migrated."""
    from custom_components.versatile_thermostat.vtherm_central_api import (
        VersatileThermostatAPI,
    )
    from custom_components.versatile_thermostat import _migrate_auto_start_stop_entry

    await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=["1", "2", "3", "auto"],
    )

    first_entry = _auto_start_stop_entry()
    second_entry = _auto_start_stop_entry()
    second_entry.add_to_hass(hass)

    failing_entry = MagicMock()
    failing_entry.data = {
        CONF_NAME: "failing",
        CONF_USE_AUTO_START_STOP_FEATURE: True,
    }

    class _FakeEntity:
        """Minimal thermostat stand-in exposing what the migration reads."""

        def __init__(self, entry, external_manager):
            self.entity_id = f"climate.fake_{id(entry)}"
            self.device_info = {"model": DOMAIN}
            self.config_entry = entry
            self._external_manager = external_manager

        def get_feature_manager(self, name):
            return self._external_manager

    component = MagicMock()
    component.entities = [
        _FakeEntity(failing_entry, MagicMock()),
        _FakeEntity(second_entry, MagicMock()),
    ]
    hass.data["climate"] = component

    real_migrate = _migrate_auto_start_stop_entry

    async def _side_effect(hass_arg, entry):
        if entry is failing_entry:
            raise RuntimeError("boom")
        return await real_migrate(hass_arg, entry)

    with patch(
        "custom_components.versatile_thermostat._migrate_auto_start_stop_entry",
        side_effect=_side_effect,
    ), caplog.at_level(logging.ERROR):
        migrated = await async_migrate_auto_start_stop(hass)

    assert migrated == 1
    assert second_entry.data[CONF_AUTO_START_STOP_MIGRATED_BY] == AUTO_START_STOP_MIGRATED_BY_VTHERM_AUTO_START_STOP
    assert any("Error while migrating auto-start/stop" in r.message for r in caplog.records)


async def test_migrated_flag_survives_reload_and_has_no_uninstall_handler(hass: HomeAssistant):
    """Migration is durable: no reload and no uninstall handler re-enables the core feature."""
    import custom_components.versatile_thermostat as vtherm

    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    assert await _migrate_auto_start_stop_entry(hass, entry) is True

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    reloaded = hass.config_entries.async_get_entry(entry.entry_id)
    assert reloaded is not None
    assert reloaded.data[CONF_USE_AUTO_START_STOP_FEATURE] is False
    assert reloaded.data[CONF_AUTO_START_STOP_MIGRATED_BY] == AUTO_START_STOP_MIGRATED_BY_VTHERM_AUTO_START_STOP

    # The integration defines no removal hook, so an uninstall cannot restore the flag.
    assert not hasattr(vtherm, "async_remove_entry")


@pytest.mark.parametrize(
    "thermostat_type, device_power, expected_power_unit",
    [
        (CONF_THERMOSTAT_SWITCH, 99, POWER_UNIT_KILO_WATT),
        (CONF_THERMOSTAT_SWITCH, 100, POWER_UNIT_KILO_WATT),
        (CONF_THERMOSTAT_SWITCH, 101, POWER_UNIT_WATT),
        (CONF_THERMOSTAT_CENTRAL_CONFIG, None, POWER_UNIT_AUTO),
    ],
)
async def test_migration_freezes_power_unit_from_legacy_configuration(
    hass: HomeAssistant,
    thermostat_type,
    device_power,
    expected_power_unit,
):
    """Migration preserves the legacy unit heuristic, including its boundary."""
    data = {
        CONF_NAME: "migrationName",
        CONF_THERMOSTAT_TYPE: thermostat_type,
    }
    if device_power is not None:
        data[CONF_DEVICE_POWER] = device_power

    config_entry = MockConfigEntry(
        version=2,
        minor_version=3,
        domain=DOMAIN,
        title="Migration power unit",
        unique_id=f"migration-power-unit-{thermostat_type}-{device_power}",
        data=data,
    )
    config_entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, config_entry) is True
    assert config_entry.data[CONF_POWER_UNIT] == expected_power_unit


async def test_migration_removes_obsolete_auto_tpi_keys(hass: HomeAssistant):
    """Migration to 2.5 removes the Auto TPI settings that are no longer used and keeps the others."""
    data = {
        CONF_NAME: "migrationName",
        CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
        "auto_tpi_mode": True,
        "heater_heating_time": 15,
        "auto_tpi_continuous_kext": True,
        "auto_tpi_learning_type": "discovery",
        "auto_tpi_enable_advanced_settings": False,
        "heater_cooling_time": 20,
        "auto_tpi_calculation_method": "average",
        "auto_tpi_ema_alpha": 0.15,
        "auto_tpi_avg_initial_weight": 1,
        "auto_tpi_heating_rate": 0.3,
        "auto_tpi_cooling_rate": 1.0,
        "auto_tpi_aggressiveness": 1.0,
        "auto_tpi_ema_decay_rate": 0.08,
        "auto_tpi_continuous_kext_alpha": 0.04,
    }
    config_entry = MockConfigEntry(
        version=2,
        minor_version=4,
        domain=DOMAIN,
        title="Migration auto TPI",
        unique_id="migration-auto-tpi",
        data=data,
    )
    config_entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, config_entry) is True
    assert (config_entry.version, config_entry.minor_version) == (2, 5)
    for key in OBSOLETE_AUTO_TPI_KEYS:
        assert key not in config_entry.data
    assert config_entry.data["auto_tpi_mode"] is True
    assert config_entry.data["heater_heating_time"] == 15
    assert config_entry.data["auto_tpi_continuous_kext"] is True


# @pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_migration_security_safety(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the migration of security parameters to safety in English"""
    central_config_entry = MockConfigEntry(
        # old version is 2.0
        version=2,
        minor_version=0,
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: "migrationName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_UNDERLYING_LIST: ["switch.under1"],
            "security_delay_min": 61,
            "security_min_on_percent": 0.5,
            "security_default_on_percent": 0.2,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
        },
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverSwitch = search_entity(hass, "climate.migrationname", "climate")

    assert entity is not None

    assert entity.safety_manager.safety_min_on_percent == 0.5
    assert entity.safety_manager.safety_default_on_percent == 0.2
    assert entity.safety_manager.safety_delay_min == 61

    entity.remove_thermostat()


async def test_migration_of_central_config(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the clean_central_config_doubon of base_thermostat"""
    central_config_entry = MockConfigEntry(
        version=2,
        minor_version=0,
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: CENTRAL_CONFIG_NAME,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CENTRAL_CONFIG,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_TPI_COEF_INT: 0.5,
            CONF_TPI_COEF_EXT: 0.02,
            CONF_MINIMAL_ACTIVATION_DELAY: 11,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 61,
            CONF_SAFETY_MIN_ON_PERCENT: 0.5,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.2,
            # The old central_boiler parameter
            "add_central_boiler_control": True,
            CONF_CENTRAL_BOILER_ACTIVATION_SRV: "switch.pompe_chaudiere/switch.turn_on",
            CONF_CENTRAL_BOILER_DEACTIVATION_SRV: "switch.pompe_chaudiere/switch.turn_off",
            CONF_CENTRAL_BOILER_ACTIVATION_DELAY_SEC: 10,
        },
    )

    central_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(central_config_entry.entry_id)
    assert central_config_entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.thecentralconfigmockname", "climate")

    assert entity is None

    assert count_entities(hass, "climate.thecentralconfigmockname", "climate") == 0

    # Test that VTherm API find the CentralConfig
    api = VersatileThermostatAPI.get_vtherm_api(hass)
    central_configuration = api.find_central_configuration()
    assert central_configuration is not None

    assert central_config_entry.data.get(CONF_USE_CENTRAL_BOILER_FEATURE) is True

    # Test that VTherm API have any central boiler entities
    # It should have been migrated and initialized
    assert api.central_boiler_manager.nb_active_device_for_boiler == 0
    assert api.central_boiler_manager.nb_active_device_for_boiler_threshold == 0  # the default value is 0


async def test_migration_offset_calibration_configured(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the migration of security parameters to safety in English"""
    config_entry = MockConfigEntry(
        # old version is 2.1
        version=2,
        minor_version=1,
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: "migrationName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_UNDERLYING_LIST: ["climate.under1", "climate.under2"],
            "safety_delay_min": 61,
            "safety_min_on_percent": 0.5,
            "safety_default_on_percent": 0.2,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_OFFSET_CALIBRATION_LIST: ["number.calib1", "number.calib2"],
            CONF_OPENING_DEGREE_LIST: ["number.opening1", "number.opening2"],
            CONF_CLOSING_DEGREE_LIST: ["number.closing1", "number.closing2"],
        },
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.migrationname", "climate")

    assert entity is not None

    new_config_entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    assert new_config_entry is not None
    assert new_config_entry.data.get(CONF_SYNC_DEVICE_INTERNAL_TEMP) is True
    assert new_config_entry.data.get(CONF_SYNC_WITH_CALIBRATION) is True
    assert new_config_entry.data.get(CONF_SYNC_ENTITY_LIST) == ["number.calib1", "number.calib2"]

    assert entity.has_sync_entities is True
    assert entity.is_sync_with_calibration is True
    assert entity.sync_entity_ids == ["number.calib1", "number.calib2"]

    entity.remove_thermostat()


async def test_migration_offset_calibration_not_configured(
    hass: HomeAssistant,
    skip_hass_states_is_state,
):
    """Tests the migration of security parameters to safety in English"""
    config_entry = MockConfigEntry(
        # old version is 2.1
        version=2,
        minor_version=1,
        domain=DOMAIN,
        title="TheCentralConfigMockName",
        unique_id="centralConfigUniqueId",
        data={
            CONF_NAME: "migrationName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_UNDERLYING_LIST: ["climate.under1", "climate.under2"],
            "safety_delay_min": 61,
            "safety_min_on_percent": 0.5,
            "safety_default_on_percent": 0.2,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_OFFSET_CALIBRATION_LIST: [],
            CONF_OPENING_DEGREE_LIST: ["number.opening1", "number.opening2"],
            CONF_CLOSING_DEGREE_LIST: [],
        },
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.migrationname", "climate")

    assert entity is not None

    new_config_entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    assert new_config_entry is not None
    assert new_config_entry.data.get(CONF_SYNC_DEVICE_INTERNAL_TEMP) is False
    assert new_config_entry.data.get(CONF_SYNC_WITH_CALIBRATION) is False
    assert new_config_entry.data.get(CONF_SYNC_ENTITY_LIST) is None

    assert entity.has_sync_entities is False
    assert entity.is_sync_with_calibration is False
    assert entity.sync_entity_ids == []

    entity.remove_thermostat()


async def test_migrated_thermostat_exposes_no_core_auto_start_stop_entity(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """A migrated entry creates neither the enable switch nor the stop-mode select."""
    await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=["1", "2", "3", "auto"],
    )

    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    # The migration keeps the flag enabled on purpose: the marker alone must win.
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_AUTO_START_STOP_MIGRATED_BY: AUTO_START_STOP_MIGRATED_BY_VTHERM_AUTO_START_STOP,
        },
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    switch_component = hass.data["switch"]
    select_component = hass.data["select"]

    assert not any((e.unique_id or "").endswith("_enable_auto_start_stop") for e in switch_component.entities)
    assert not any((e.unique_id or "").endswith("_auto_start_stop_stop_mode") for e in select_component.entities)


def _register_feature_entity(registry, entry, entity_id, unique_id):
    """Register one entity as if the core platform had created it."""
    return registry.async_get_or_create(
        entity_id.split(".", 1)[0],
        DOMAIN,
        unique_id,
        config_entry=entry,
        suggested_object_id=entity_id.split(".", 1)[1],
    )


async def test_cleanup_removes_entities_of_a_renamed_thermostat(hass: HomeAssistant):
    """The suffix match removes the entities even after the thermostat was renamed."""
    from homeassistant.helpers.entity_registry import async_get as async_get_registry
    from custom_components.versatile_thermostat import (
        _remove_core_auto_start_stop_entities,
    )

    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    registry = async_get_registry(hass)

    # Unique ids embed the device name, which changed on rename.
    _register_feature_entity(registry, entry, "switch.old_name_enable", "renamed_enable_auto_start_stop")
    _register_feature_entity(registry, entry, "select.old_name_mode", "renamed_auto_start_stop_stop_mode")

    assert await _remove_core_auto_start_stop_entities(hass, entry) == 2
    assert not any(e.config_entry_id == entry.entry_id for e in registry.entities.values())


async def test_cleanup_leaves_other_thermostats_untouched(hass: HomeAssistant):
    """The cleanup is scoped to the migrated entry."""
    from homeassistant.helpers.entity_registry import async_get as async_get_registry
    from custom_components.versatile_thermostat import (
        _remove_core_auto_start_stop_entities,
    )

    migrated_entry = _auto_start_stop_entry()
    migrated_entry.add_to_hass(hass)
    other_entry = _auto_start_stop_entry()
    other_entry.add_to_hass(hass)

    registry = async_get_registry(hass)
    _register_feature_entity(registry, migrated_entry, "switch.migrated_enable", "migrated_enable_auto_start_stop")
    _register_feature_entity(registry, other_entry, "switch.other_enable", "other_enable_auto_start_stop")

    assert await _remove_core_auto_start_stop_entities(hass, migrated_entry) == 1

    remaining = [e for e in registry.entities.values() if e.config_entry_id == other_entry.entry_id]
    assert len(remaining) == 1
    assert remaining[0].unique_id == "other_enable_auto_start_stop"


async def test_cleanup_without_created_entities_is_harmless(hass: HomeAssistant, caplog):
    """Nothing is removed and no error is logged when the feature never existed."""
    from custom_components.versatile_thermostat import (
        _remove_core_auto_start_stop_entities,
    )

    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)

    with caplog.at_level(logging.ERROR):
        assert await _remove_core_auto_start_stop_entities(hass, entry) == 0

    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


@pytest.mark.parametrize("renamed", [False, True])
async def test_migration_saves_exact_entity_ids_before_removing_them(hass, renamed):
    """A later dedicated plugin entry can reuse the actual production IDs."""
    from homeassistant.helpers import entity_registry as er

    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    controls = {
        "switch": _register_feature_entity(
            registry, entry, "switch.thermostat_chambre_enable_auto_start_stop",
            "old_name_enable_auto_start_stop",
        ),
        "select": _register_feature_entity(
            registry, entry, "select.chambre_thermostat_chambre_auto_start_stop_stop_mode",
            "old_name_auto_start_stop_stop_mode",
        ),
    }
    if renamed:
        controls = {
            domain: registry.async_update_entity(control.entity_id, new_entity_id=f"{domain}.user_customized_control")
            for domain, control in controls.items()
        }
    expected = {domain: control.entity_id for domain, control in controls.items()}
    remove = registry.async_remove

    def remove_after_saving(entity_id):
        assert entry.data[CONF_AUTO_START_STOP_ENTITY_IDS] == expected
        remove(entity_id)

    with patch.object(registry, "async_remove", side_effect=remove_after_saving):
        assert await _migrate_auto_start_stop_entry(hass, entry) is True
    assert entry.data[CONF_AUTO_START_STOP_ENTITY_IDS] == expected
    assert all(registry.async_get(entity_id) is None for entity_id in expected.values())
    with patch.object(hass.config_entries, "async_update_entry") as update:
        assert await _migrate_auto_start_stop_entry(hass, entry) is False
        update.assert_not_called()


@pytest.mark.parametrize("remembered_switch", [None, "switch.remembered_custom_id"])
async def test_delegated_entry_recovers_missing_ids_without_overwriting(hass, remembered_switch):
    """Retained deleted rows repair test installations that delegated earlier."""
    from homeassistant.helpers import entity_registry as er

    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    switch = _register_feature_entity(
        registry, entry, "switch.old_auto_start_stop", "old_name_enable_auto_start_stop",
    )
    select = _register_feature_entity(
        registry, entry, "select.old_stop_mode", "old_name_auto_start_stop_stop_mode",
    )
    for control in (switch, select):
        registry.async_remove(control.entity_id)
    data = {
        **entry.data,
        CONF_USE_AUTO_START_STOP_FEATURE: False,
        CONF_AUTO_START_STOP_MIGRATED_BY: AUTO_START_STOP_MIGRATED_BY_VTHERM_AUTO_START_STOP,
    }
    if remembered_switch is not None:
        data[CONF_AUTO_START_STOP_ENTITY_IDS] = {"switch": remembered_switch}
    hass.config_entries.async_update_entry(entry, data=data)

    assert await _migrate_auto_start_stop_entry(hass, entry) is True
    assert entry.data[CONF_AUTO_START_STOP_ENTITY_IDS] == {
        "switch": remembered_switch or switch.entity_id,
        "select": select.entity_id,
    }
    assert entry.data[CONF_USE_AUTO_START_STOP_FEATURE] is False
    assert entry.data[CONF_AUTO_START_STOP_LEVEL] == AUTO_START_STOP_LEVEL_MEDIUM
    assert await _migrate_auto_start_stop_entry(hass, entry) is False


async def test_identity_capture_prefers_current_rows_to_deleted_history(hass):
    from homeassistant.helpers import entity_registry as er

    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = _register_feature_entity(
        registry, entry, "switch.before_rename", "old_name_enable_auto_start_stop",
    )
    registry.async_remove(old.entity_id)
    current = _register_feature_entity(
        registry, entry, "switch.current_name", "new_name_enable_auto_start_stop",
    )
    assert await _migrate_auto_start_stop_entry(hass, entry) is True
    assert entry.data[CONF_AUTO_START_STOP_ENTITY_IDS] == {"switch": current.entity_id}


async def test_identity_capture_and_cleanup_ignore_unrelated_owners(hass):
    from homeassistant.helpers import entity_registry as er

    entry = _auto_start_stop_entry()
    other = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    other.add_to_hass(hass)
    registry = er.async_get(hass)
    foreign = registry.async_get_or_create(
        "switch", "another_integration", "same_suffix_enable_auto_start_stop",
        config_entry=entry,
    )
    other_control = _register_feature_entity(
        registry, other, "select.other_thermostat", "other_auto_start_stop_stop_mode",
    )
    assert await _migrate_auto_start_stop_entry(hass, entry) is True
    assert entry.data[CONF_AUTO_START_STOP_ENTITY_IDS] == {}
    assert registry.async_get(foreign.entity_id) == foreign
    assert registry.async_get(other_control.entity_id) == other_control


async def test_remembered_ids_do_not_prevent_retrying_incomplete_cleanup(hass):
    from homeassistant.helpers import entity_registry as er

    entry = _auto_start_stop_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    control = _register_feature_entity(
        registry, entry, "switch.waiting_for_cleanup", "old_name_enable_auto_start_stop",
    )
    hass.config_entries.async_update_entry(entry, data={
        **entry.data,
        CONF_USE_AUTO_START_STOP_FEATURE: False,
        CONF_AUTO_START_STOP_MIGRATED_BY: AUTO_START_STOP_MIGRATED_BY_VTHERM_AUTO_START_STOP,
        CONF_AUTO_START_STOP_ENTITY_IDS: {"switch": control.entity_id},
    })
    with patch.object(hass.config_entries, "async_update_entry") as update:
        assert await _migrate_auto_start_stop_entry(hass, entry) is False
        update.assert_not_called()
    assert registry.async_get(control.entity_id) is None
