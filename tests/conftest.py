"""Global fixtures for integration_blueprint integration."""

# pylint: disable=line-too-long

# Fixtures allow you to replace functions with a Mock object. You can perform
# many options via the Mock to reflect a particular behavior from the original
# function that you want to see without going through the function's actual logic.
# Fixtures can either be passed into tests as parameters, or if autouse=True, they
# will automatically be used across all tests.
#
# Fixtures that are defined in conftest.py are available across all tests. You can also
# define fixtures within a particular test file to scope them locally.
#
# pytest_homeassistant_custom_component provides some fixtures that are provided by
# Home Assistant core. You can find those fixture definitions here:
# https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/pytest_homeassistant_custom_component/common.py
#
# See here for more info: https://docs.pytest.org/en/latest/fixture.html (note that
# pytest includes fixtures OOB which you can use as defined on this page)
from unittest.mock import patch
import zoneinfo
import asyncio
import os
import socket
from asyncio.runners import Runner, _State  # type: ignore

import homeassistant.util.dt as ha_dt
import pytest
import pytest_asyncio
# https://github.com/miketheman/pytest-socket/pull/275
from pytest_socket import socket_allow_hosts
from homeassistant.core import StateMachine

from custom_components.versatile_thermostat.config_flow import (
    VersatileThermostatBaseConfigFlow,
)
from custom_components.versatile_thermostat.const import (
    CONF_MAX_POWER_SENSOR,
    CONF_POWER_SENSOR,
    CONF_PRESET_POWER,
    CONF_USE_POWER_FEATURE,
)
from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.vtherm_api import VersatileThermostatAPI

from .commons import (
    FULL_CENTRAL_CONFIG,
    FULL_CENTRAL_CONFIG_WITH_BOILER,
    create_central_config,
)

# ...


if os.environ.get("FAST_VTHERM_TEST_SETUP", "1") != "0":
    # Ensure any ThreadPoolExecutor workers are daemonized so they don't block exit.
    try:
        import concurrent.futures.thread as futures_thread

        _orig_thread_factory = futures_thread.thread_factory

        def _daemon_thread_factory(*args, **kwargs):
            thread = _orig_thread_factory(*args, **kwargs)
            thread.daemon = True
            return thread

        futures_thread.thread_factory = _daemon_thread_factory  # type: ignore[assignment]
    except Exception:
        pass

    # Use the default Runner.close implementation for correctness; the daemonized
    # thread pool keeps teardown quick without extra patching here.


class NoopResolver:
    """Resolver that never touches the network and spawns no threads."""

    async def resolve(self, host, port=0, family=0):
        return [
            {
                "hostname": host,
                "host": "127.0.0.1",
                "port": port,
                "family": socket.AF_INET,
                "proto": 0,
                "flags": 0,
            }
        ]

    async def close(self):
        return None


def pytest_runtest_setup():
    """setup tests"""
    socket_allow_hosts(allowed=["localhost", "127.0.0.1", "::1"], allow_unix_socket=True)


async def _fast_async_get_time_zone(time_zone_str: str):
    """Resolve a timezone without using the event loop's default executor.

    Home Assistant's timezone helper uses `aiozoneinfo.async_get_time_zone()`, which
    normally calls `loop.run_in_executor(...)`. On Python 3.13 we've observed this
    can stall the HA pytest harness during fixture setup/teardown, so we resolve
    time zones directly via `zoneinfo.ZoneInfo` in-process for tests.
    """
    try:
        return zoneinfo.ZoneInfo(time_zone_str)
    except zoneinfo.ZoneInfoNotFoundError:
        return None


# Use the fast resolver during tests:
# - Patch `aiozoneinfo.async_get_time_zone` (source of truth for HA's `dt_util`)
# - Patch `homeassistant.util.dt._async_get_time_zone` (already-imported alias)
try:
    import aiozoneinfo

    aiozoneinfo.async_get_time_zone = _fast_async_get_time_zone
except ModuleNotFoundError:
    # Some dev/test environments may not have `aiozoneinfo` installed.
    # HA's internal helpers already provide a resolver path; for tests we still
    # patch `homeassistant.util.dt._async_get_time_zone` below.
    aiozoneinfo = None
ha_dt._async_get_time_zone = _fast_async_get_time_zone


pytest_plugins = "pytest_homeassistant_custom_component"  # pylint: disable=invalid-name


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations,
):  # pylint: disable=unused-argument
    """Enable all integration in tests"""
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch("homeassistant.components.persistent_notification.async_dismiss"):
        yield


@pytest.fixture(name="skip_turn_on_off_heater")
def skip_turn_on_off_heater():
    """Skip turning on and off the heater"""
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingEntity.turn_on"), patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingEntity.turn_off"
    ):
        yield


# This fixture is used to bypass the validate_input function in config_flow
# NOT USED Now (keeped for memory)
@pytest.fixture(name="skip_validate_input")
def skip_validate_input_fixture():
    """Skip the validate_input in config flow"""
    with patch.object(VersatileThermostatBaseConfigFlow, "validate_input"):
        yield


@pytest.fixture(name="skip_hass_states_get")
def skip_hass_states_get_fixture():
    """Skip the get state in HomeAssistant"""
    with patch.object(StateMachine, "get"):
        yield


@pytest.fixture(name="skip_control_heating")
def skip_control_heating_fixture():
    """Skip the control_heating of VersatileThermostat"""
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.async_control_heating"):
        yield


@pytest.fixture(name="skip_find_underlying_climate")
def skip_find_underlying_climate_fixture():
    """Skip the find_underlying_climate of VersatileThermostat"""
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.find_underlying_climate"):
        yield


@pytest.fixture(name="skip_hass_states_is_state")
def skip_hass_states_is_state_fixture():
    """Skip the is_state in HomeAssistant"""
    with patch.object(StateMachine, "is_state", return_value=False):
        yield


@pytest.fixture(name="skip_send_event")
def skip_send_event_fixture():
    """Skip the send_event in BaseThermostat"""
    with patch.object(BaseThermostat, "send_event"):
        yield


@pytest.fixture(autouse=True)
def isolate_singleton_state():
    """
    Cette fixture s'exécute AVANT et APRÈS chaque test,
    garantissant un état propre pour MonSingleton.
    """
    # 1. Setup : Le test s'exécute ici.
    yield

    # 2. Teardown : Exécuté après que le test soit terminé.
    # On force la réinitialisation de l'instance unique
    # reset API to avoid side effects between tests
    VersatileThermostatAPI.reset_vtherm_api()


@pytest.fixture(autouse=True)
async def cleanup_event_loop_tasks():
    """
    Cancel any lingering asyncio tasks so pytest can shut down the loop quickly.

    Some Home Assistant helpers schedule work far in the future; without
    cancellation the event loop close in pytest_asyncio can block waiting on
    those handles, dragging out teardown.
    """
    # Skipping the cleanup avoids occasional hangs between tests; set
    # SKIP_LOOP_CLEANUP=0 to re-enable the aggressive task cancellation.
    if os.environ.get("SKIP_LOOP_CLEANUP", "1") == "1":
        yield
        return
    if os.environ.get("DEBUG_TASK_DUMP") == "1":
        print("[fast-teardown] cleanup_event_loop_tasks: setup")

    yield

    if os.environ.get("DEBUG_TASK_DUMP") == "1":
        print("[fast-teardown] cleanup_event_loop_tasks: teardown start")

    loop = asyncio.get_running_loop()
    pending = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task(loop) and not task.done()]

    # Cancel any scheduled timer handles to avoid long waits on shutdown
    scheduled = [handle for handle in list(getattr(loop, "_scheduled", ())) if not handle.cancelled()]
    for handle in scheduled:
        handle.cancel()

    # Stop the loop's default executor to prevent lingering worker threads.
    executor = getattr(loop, "_default_executor", None)
    if executor:
        if os.environ.get("DEBUG_TASK_DUMP") == "1":
            print(f"[fast-teardown] cancelling default executor {executor}")
        executor.shutdown(wait=False, cancel_futures=True)
        loop._default_executor = None  # type: ignore[attr-defined]

    for task in pending:
        task.cancel()

    if pending:
        # Wait for cancellation to propagate to any lingering tasks, but do not
        # allow a hang if a task ignores cancellation.
        await asyncio.gather(*pending, return_exceptions=True)

    # Drop cancelled handles so the loop sees a clean schedule for the next test
    try:
        loop._scheduled = tuple(h for h in getattr(loop, "_scheduled", ()) if not h.cancelled())  # type: ignore[attr-defined]
    except Exception:
        pass

    if os.environ.get("DEBUG_TASK_DUMP") == "1":
        print(f"[fast-teardown] pending_tasks={len(pending)} scheduled_handles={len(scheduled)}")


@pytest.fixture(autouse=True)
def disable_async_resolver(disable_mock_zeroconf_resolver):
    """
    Force Home Assistant to skip the AsyncResolver/pycares path during tests.

    The default mock resolver in the HA test plugin spins up a pycares worker
    thread that can linger and slow down teardown. Using the threaded resolver
    keeps teardown fast and avoids those lingering threads.
    """
    yield


@pytest.fixture
def disable_mock_zeroconf_resolver():
    """Override HA plugin fixture; resolver is already patched to threaded."""
    yield


@pytest_asyncio.fixture(autouse=True)
async def mock_zeroconf_resolver():
    """
    Override the HA test plugin's resolver fixture to avoid aiodns/pycares.

    We patch the resolver factory to return a resolver that does not hit the
    network and does not spin worker threads that linger at teardown.
    """
    with patch(
        "homeassistant.helpers.aiohttp_client._async_make_resolver",
        lambda loop=None: NoopResolver(),
    ):
        yield


@pytest.fixture(autouse=True)
def force_threaded_resolver(monkeypatch):
    """
    Patch HA's resolver factory to use the thread-free NoopResolver.

    This avoids the pycares worker thread and speeds up teardown.
    """
    monkeypatch.setattr(
        "homeassistant.helpers.aiohttp_client._async_make_resolver",
        lambda loop: NoopResolver(),
    )
    yield


@pytest.fixture(autouse=True)
def fast_shutdown_default_executor(monkeypatch):
    """Short-circuit shutdown of default executor to avoid long teardown waits."""

    async def _fast_shutdown(self, *_args, **_kwargs):  # type: ignore[override]
        # Cancel any executor jobs by closing the executor immediately
        executor = getattr(self, "_default_executor", None)
        if executor:
            if os.environ.get("DEBUG_TASK_DUMP") == "1":
                print(f"[fast-exec] shutting down default executor {executor}")
            executor.shutdown(wait=False, cancel_futures=True)
            self._default_executor = None  # type: ignore[attr-defined]
        return None

    monkeypatch.setattr(
        asyncio.BaseEventLoop,
        "shutdown_default_executor",
        _fast_shutdown,
        raising=False,
    )
    yield


@pytest.fixture(autouse=True)
def debug_thread_dump():
    """Optionally log lingering threads to diagnose teardown stalls."""
    yield

    if os.environ.get("DEBUG_THREAD_DUMP") == "1":
        import threading

        threads = threading.enumerate()
        print(f"[fast-teardown] threads={threads}")


if os.environ.get("DEBUG_THREAD_DUMP") == "1":
    import atexit
    import threading

    def _dump_threads_at_exit():
        print(f"[fast-exit] threads={threading.enumerate()}")

    atexit.register(_dump_threads_at_exit)


def pytest_sessionfinish(session, exitstatus):  # pylint: disable=unused-argument
    """Optional debug hook to see if pytest completes cleanly."""
    if os.environ.get("DEBUG_THREAD_DUMP") == "1":
        print(f"[fast-sessionfinish] exitstatus={exitstatus}")


if os.environ.get("DEBUG_THREAD_DUMP") == "1":
    # Periodically dump stack traces to help diagnose hangs during teardown.
    try:
        import faulthandler

        faulthandler.dump_traceback_later(30, repeat=True)
    except Exception:  # pragma: no cover
        pass


@pytest.fixture(autouse=True)
def verify_cleanup():
    """Override HA plugin's verify_cleanup to avoid long teardown waits."""
    yield


@pytest.fixture(autouse=True)
def enable_event_loop_debug():
    """Disable HA plugin's event loop debug toggling for speed."""
    yield


@pytest.fixture(autouse=True)
def patch_time_helpers(monkeypatch):
    """
    Stub out Home Assistant time-based helpers to avoid scheduling background timers.

    Tests don't need real time progression; replacing these helpers prevents
    a buildup of scheduled callbacks that would otherwise slow teardown.
    """

    def _noop_track_time_interval(hass, action, interval, **kwargs):
        return lambda: None

    def _noop_track_state_change_event(hass, entity_ids, action, **kwargs):
        return lambda: None

    def _noop_async_call_later(hass, delay, action, **kwargs):
        return lambda: None

    monkeypatch.setattr(
        "homeassistant.helpers.event.async_track_time_interval",
        _noop_track_time_interval,
    )
    monkeypatch.setattr(
        "homeassistant.helpers.event.async_track_state_change_event",
        _noop_track_state_change_event,
    )
    monkeypatch.setattr(
        "homeassistant.helpers.event.async_call_later",
        _noop_async_call_later,
    )
    yield


@pytest.fixture(autouse=True)
def register_dummy_services(hass):
    """Register no-op climate services to avoid ServiceNotFound during fast tests."""

    async def _noop_service(call):
        return None

    hass.services.async_register("climate", "set_temperature", _noop_service)
    hass.services.async_register("climate", "set_hvac_mode", _noop_service)
    hass.services.async_register("switch", "turn_on", _noop_service)
    hass.services.async_register("switch", "turn_off", _noop_service)
    yield


@pytest.fixture(autouse=True)
def fast_hass_stop(monkeypatch):
    """Prevent hass.stop teardown from waiting on lingering tasks."""

    async def _fast_stop(self, *args, **kwargs):  # type: ignore[override]
        return None

    monkeypatch.setattr("homeassistant.core.HomeAssistant.async_stop", _fast_stop)
    yield


@pytest.fixture(name="init_vtherm_api")
def init_vtherm_api_fixture(hass):
    """Initialize the VTherm API"""
    VersatileThermostatAPI.get_vtherm_api(hass)
    yield


@pytest.fixture(name="init_central_config")
async def init_central_config_fixture(hass, init_vtherm_api):  # pylint: disable=unused-argument
    """Initialize the VTherm API"""
    await create_central_config(hass, FULL_CENTRAL_CONFIG)

    yield


@pytest.fixture(name="init_central_config_with_boiler_fixture")
async def init_central_config_with_boiler_fixture(hass, init_vtherm_api):  # pylint: disable=unused-argument
    """Initialize the VTherm API"""
    await create_central_config(hass, FULL_CENTRAL_CONFIG_WITH_BOILER)

    yield


@pytest.fixture(name="init_central_power_manager")
async def init_central_power_manager_fixture(hass, init_central_config):  # pylint: disable=unused-argument
    """Initialize the central power_manager"""
    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # 1. creation / init
    vtherm_api.central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
        }
    )
    assert vtherm_api.central_power_manager.is_configured

    yield
