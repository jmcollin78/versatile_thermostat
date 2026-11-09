# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

"""Test that external feature managers (provided by plugins) are refreshed on each cycle."""

from datetime import datetime, timedelta

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from pytest_homeassistant.common import MockConfigEntry

from custom_components.versatile_thermostat.base_manager import BaseFeatureManager
from custom_components.versatile_thermostat.thermostat_climate import (
    ThermostatOverClimate,
)
from custom_components.versatile_thermostat.vtherm_central_api import (
    VersatileThermostatAPI,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


class FakeExternalFeatureManager(BaseFeatureManager):
    """Minimal feature manager used to emulate an external plugin manager."""

    def __init__(self, thermostat) -> None:
        """Initialize the fake external feature manager."""
        super().__init__(thermostat, thermostat.hass, "fake_external_fm")
        self.post_init_calls = 0
        self.start_listening_calls = 0
        self.refresh_state_calls = 0

    def post_init(self, entry_infos) -> None:
        """Record the post_init call."""
        self.post_init_calls += 1

    async def start_listening(self) -> None:
        """Record the start_listening call."""
        self.start_listening_calls += 1

    async def refresh_state(self) -> bool:
        """Record the refresh_state call. Returns False (no change)."""
        self.refresh_state_calls += 1
        return False

    @property
    def is_configured(self) -> bool:
        """The fake manager is always configured."""
        return True

    @property
    def is_detected(self) -> bool:
        """The fake manager never detects anything."""
        return False


class FakeExternalPropFactory:
    """Minimal proportional algorithm factory used to emulate an external plugin."""

    name = "fake_external_prop"

    def create(self, thermostat):
        """Not used by these tests."""
        raise NotImplementedError


def _over_climate_entry() -> MockConfigEntry:
    """Build the over_climate entry used by the reload tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverClimateMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            "eco_temp": 17,
            "comfort_temp": 18,
            "boost_temp": 19,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
        },
    )


async def _setup_only_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Set up the only over_climate entry."""
    entry = _over_climate_entry()
    await create_and_register_mock_climate(
        hass=hass,
        unique_id="mock_climate",
        name="MockClimateName",
        fan_modes=["1", "2", "3", "auto"],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED
    return entry


class FakeExternalFeatureManagerFactory:
    """Minimal factory used to emulate an external feature manager plugin."""

    name = "fake_external_fm"

    def supports(self, thermostat) -> bool:
        """Only support over_climate thermostats (like the auto-fan plugin)."""
        return getattr(thermostat, "is_over_climate", False)

    def create(self, thermostat) -> FakeExternalFeatureManager:
        """Create the fake external feature manager."""
        return FakeExternalFeatureManager(thermostat)


async def test_external_feature_manager_refreshed_each_cycle(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """An external feature manager should be instantiated and refreshed on each cycle."""

    api = VersatileThermostatAPI.get_vtherm_api(hass)
    factory = FakeExternalFeatureManagerFactory()
    api.register_feature_manager(factory)

    try:
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="TheOverClimateMockName",
            unique_id="uniqueId",
            data={
                CONF_NAME: "TheOverClimateMockName",
                CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
                CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
                CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
                CONF_CYCLE_MIN: 5,
                CONF_TEMP_MIN: 15,
                CONF_TEMP_MAX: 30,
                "eco_temp": 17,
                "comfort_temp": 18,
                "boost_temp": 19,
                CONF_USE_WINDOW_FEATURE: False,
                CONF_USE_MOTION_FEATURE: False,
                CONF_USE_POWER_FEATURE: False,
                CONF_USE_PRESENCE_FEATURE: False,
                CONF_UNDERLYING_LIST: ["climate.mock_climate"],
                CONF_MINIMAL_ACTIVATION_DELAY: 30,
                CONF_MINIMAL_DEACTIVATION_DELAY: 0,
                CONF_SAFETY_DELAY_MIN: 5,
                CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            },
        )

        await create_and_register_mock_climate(
            hass=hass,
            unique_id="mock_climate",
            name="MockClimateName",
            fan_modes=["1", "2", "3", "auto"],
        )

        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        entity: ThermostatOverClimate = search_entity(
            hass, "climate.theoverclimatemockname", "climate"
        )
        assert entity
        assert isinstance(entity, ThermostatOverClimate)

        # 1. The external manager has been instantiated and registered
        assert "fake_external_fm" in entity._external_manager_names
        assert len(entity._external_managers) == 1
        fake_manager: FakeExternalFeatureManager = entity._external_managers[0]
        assert fake_manager in entity._managers
        assert fake_manager.post_init_calls >= 1

        tz = get_tz(hass)  # pylint: disable=invalid-name
        now: datetime = datetime.now(tz=tz)
        entity._set_now(now)

        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.COMFORT)

        now = now + timedelta(minutes=1)
        entity._set_now(now)
        await send_temperature_change_event(entity, 18, now)
        await send_ext_temperature_change_event(entity, 5, now)

        assert entity.is_ready is True

        # 2. Each control cycle must refresh the external manager
        with patch(
            "custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_fan_mode"
        ):
            before = fake_manager.refresh_state_calls
            await entity.async_control_heating(force=True)
            assert fake_manager.refresh_state_calls == before + 1

            await entity.async_control_heating(force=True)
            assert fake_manager.refresh_state_calls == before + 2
    finally:
        api.unregister_feature_manager("fake_external_fm")


async def test_reload_only_entry_keeps_feature_manager(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Reloading the only entry must keep the API and its feature manager registrations."""

    api = VersatileThermostatAPI.get_vtherm_api(hass)
    api.register_feature_manager(FakeExternalFeatureManagerFactory())

    try:
        entry = await _setup_only_entry(hass)

        assert await hass.config_entries.async_reload(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        assert VersatileThermostatAPI.get_vtherm_api(hass) is api
        assert api.list_feature_managers() == ["fake_external_fm"]

        entity: ThermostatOverClimate = search_entity(
            hass, "climate.theoverclimatemockname", "climate"
        )
        assert entity
        assert "fake_external_fm" in entity._external_manager_names
    finally:
        api.unregister_feature_manager("fake_external_fm")


async def test_reload_only_entry_keeps_prop_algorithm(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Reloading the only entry must keep the API and its proportional algorithm registrations."""

    api = VersatileThermostatAPI.get_vtherm_api(hass)
    factory = FakeExternalPropFactory()
    api.register_prop_algorithm(factory)

    try:
        entry = await _setup_only_entry(hass)

        assert await hass.config_entries.async_reload(entry.entry_id)
        assert entry.state is ConfigEntryState.LOADED

        assert VersatileThermostatAPI.get_vtherm_api(hass) is api
        assert api.list_prop_algorithms() == ["fake_external_prop"]
        assert api.get_prop_algorithm("fake_external_prop") is factory
    finally:
        api.unregister_prop_algorithm("fake_external_prop")


async def test_unload_last_entry_without_plugin_removes_api(
    hass: HomeAssistant, skip_hass_states_is_state, skip_send_event
):
    """Without any plugin registration, unloading the last entry still removes the API."""

    api = VersatileThermostatAPI.get_vtherm_api(hass)
    assert not api.list_feature_managers()
    assert not api.list_prop_algorithms()

    entry = await _setup_only_entry(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert DOMAIN not in hass.data
