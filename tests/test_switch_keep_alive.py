"""Test the switch keep-alive feature."""
# pylint: disable=redefined-outer-name, line-too-long, protected-access
import logging
from collections.abc import AsyncGenerator, Callable, Awaitable
from dataclasses import dataclass
from unittest.mock import ANY, _Call, AsyncMock, MagicMock, call, patch
from datetime import datetime, timedelta, timezone
from typing import cast

from homeassistant.exceptions import ServiceNotFound

from custom_components.versatile_thermostat.feature_repair_incorrect_state_manager import FeatureRepairIncorrectStateManager
from custom_components.versatile_thermostat.underlyings import UnderlyingSwitch
from custom_components.versatile_thermostat.keep_alive import BackoffTimer
from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize("inverse, custom", [(False, False), (True, False), (False, True), (True, True)])
@pytest.mark.parametrize("turn_on", [False, True])
async def test_switch_command_timestamps_actual_service(hass: HomeAssistant, inverse, custom, turn_on):
    """Successful normal, inverse and custom commands timestamp the direct service call."""
    now = datetime.now(timezone.utc)
    thermostat = MagicMock()
    thermostat.now = now
    thermostat.is_inversed = inverse
    switch = UnderlyingSwitch(hass, thermostat, "switch.test", 0, "open/position:on" if custom else None, "close/position:off" if custom else None)
    with patch.object(switch, "check_overpowering", new=AsyncMock(return_value=True)), patch("homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock) as service:
        await (switch.turn_on() if turn_on else switch.turn_off())
    expected = switch._on_command if turn_on else switch._off_command
    service.assert_awaited_once_with("switch", expected["command"], expected["data"])
    assert switch.last_command_sent_datetime == now
    assert switch._is_on_part_running is turn_on


@pytest.mark.parametrize("turn_on, failure", [(turn_on, failure) for turn_on in (False, True) for failure in ("blocked", "missing", "error", "rearm")] + [(True, "power")])
async def test_switch_command_timestamp_failures(hass: HomeAssistant, turn_on, failure):
    """A failed or blocked send does not timestamp; a failure after success does."""
    now = datetime.now(timezone.utc)
    thermostat = MagicMock()
    thermostat.now = now
    thermostat.is_inversed = False
    thermostat.update_states = AsyncMock()
    switch = UnderlyingSwitch(hass, thermostat, "switch.test", 0)
    original = switch.last_command_sent_datetime
    error = ServiceNotFound("switch", "turn_on") if failure == "missing" else RuntimeError("service failure")
    with (
        patch.object(switch, "is_command_blocked", return_value=failure == "blocked"),
        patch.object(switch, "check_overpowering", new=AsyncMock(return_value=failure != "power")),
        patch.object(switch._keep_alive, "set_async_action", side_effect=error if failure == "rearm" else None),
        patch("homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock, side_effect=error if failure in ("missing", "error") else None) as service,
    ):
        if failure in ("error", "rearm"):
            with pytest.raises(RuntimeError):
                await (switch.turn_on() if turn_on else switch.turn_off())
        else:
            await (switch.turn_on() if turn_on else switch.turn_off())
    assert switch.last_command_sent_datetime == (now if failure == "rearm" else original)
    assert service.await_count == int(failure not in ("blocked", "power"))


async def test_keep_alive_renews_manager_grace(hass: HomeAssistant):
    """Repeated successful keep-alive sends postpone only this switch's check."""
    now = datetime.now(timezone.utc)
    thermostat = MagicMock()
    thermostat.now = now
    thermostat.name = "thermostat"
    thermostat.is_ready = True
    thermostat.is_inversed = False
    switch = UnderlyingSwitch(hass, thermostat, "switch.test", 0)
    switch._is_on_part_running = True
    thermostat.all_underlying_entities = [switch]
    manager = FeatureRepairIncorrectStateManager(thermostat, hass)
    manager.post_init({CONF_REPAIR_INCORRECT_STATE: True})
    manager._ready_start_time = now - timedelta(seconds=31)
    with (
        patch("homeassistant.core.StateMachine.get", return_value=State("switch.test", "on")),
        patch("homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock) as service,
        patch.object(switch, "check_overpowering", new=AsyncMock(return_value=True)),
        patch.object(switch, "check_and_repair", new=AsyncMock(return_value=True)) as check,
    ):
        for elapsed in (0, 9, 18):
            thermostat.now = now + timedelta(seconds=elapsed)
            await switch._keep_alive_callback()
            assert switch.last_command_sent_datetime == thermostat.now
            assert await manager.check_and_repair() is False
        check.assert_not_awaited()
        assert service.await_count == 3
        thermostat.now = now + timedelta(seconds=28)
        assert await manager.check_and_repair() is True
        check.assert_awaited_once()


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return common test data"""
    return MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_HEATER_KEEP_ALIVE: 1,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.1,
        },
    )


@dataclass
class CommonMocks:
    """Common mocked objects used by most test cases"""

    config_entry: MockConfigEntry
    hass: HomeAssistant
    thermostat: ThermostatOverSwitch
    mock_is_state: MagicMock
    mock_get_state: MagicMock
    mock_service_call: MagicMock
    mock_async_track_time_interval: MagicMock
    mock_send_event: MagicMock


@pytest.fixture
async def common_mocks(
    config_entry: MockConfigEntry,
    hass: HomeAssistant,
) -> AsyncGenerator[CommonMocks, None]:
    """Create and destroy a ThermostatOverSwitch as a test fixture"""
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call, \
        patch("homeassistant.core.StateMachine.is_state", return_value=False) as mock_is_state, \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.keep_alive.async_track_time_interval") as mock_async_track_time_interval:
    # fmt: on
        thermostat = cast(ThermostatOverSwitch, await create_thermostat(
            hass, config_entry, "climate.theoverswitchmockname"
        ))
        with patch("homeassistant.core.StateMachine.get") as mock_get_state:
            mock_get_state.return_value.state = "off"
            yield CommonMocks(
                config_entry=config_entry,
                hass=hass,
                thermostat=thermostat,
                mock_is_state=mock_is_state,
                mock_get_state=mock_get_state,
                mock_service_call=mock_service_call,
                mock_async_track_time_interval=mock_async_track_time_interval,
                mock_send_event=mock_send_event,
            )
        # Clean the entity
        thermostat.remove_thermostat()


class TestKeepAlive:
    """Tests for the switch keep-alive feature"""

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        """Initialise test case data before the execution of each test case method."""
        self._prev_service_calls: list[_Call] = []
        self._prev_atti_call_count = 0  # atti: async_time_track_interval
        self._prev_atti_callback: Callable[[datetime], Awaitable[None]] | None = None

    def _assert_service_call(
        self, cm: CommonMocks, expected_additional_calls: list[_Call]
    ):
        """Assert that hass.services.async_call() was called with the expected arguments,
        cumulatively over the course of long test cases."""
        self._prev_service_calls.extend(expected_additional_calls)
        cm.mock_service_call.assert_has_calls(self._prev_service_calls)

    def _assert_async_mock_track_time_interval(
        self, cm: CommonMocks, expected_additional_calls: int
    ):
        """Assert that async_track_time_interval() was called the expected number of times
        with the expected arguments, cumulatively over the course of long test cases."""
        self._prev_atti_call_count += expected_additional_calls
        assert (
            cm.mock_async_track_time_interval.call_count == self._prev_atti_call_count
        )
        interval = timedelta(seconds=cm.config_entry.data[CONF_HEATER_KEEP_ALIVE])
        cm.mock_async_track_time_interval.assert_called_with(cm.hass, ANY, interval)
        keep_alive_callback = cm.mock_async_track_time_interval.call_args.args[1]
        assert callable(keep_alive_callback)
        self._prev_atti_callback = keep_alive_callback

    async def _assert_multipe_keep_alive_callback_calls(
        self, cm: CommonMocks, n_calls: int
    ):
        """Call the keep-alive callback a few times as if `async_track_time_interval()` had
        done it, and assert that this triggers further calls to `async_track_time_interval()`.
        """
        old_callback = self._prev_atti_callback
        assert (
            old_callback
        ), "The keep-alive callback should have been called before, but it wasn't."
        interval = timedelta(seconds=cm.config_entry.data[CONF_HEATER_KEEP_ALIVE])
        for _ in range(n_calls):
            await old_callback(datetime.fromtimestamp(0))
            self._prev_atti_call_count += 1
            assert (
                cm.mock_async_track_time_interval.call_count
                == self._prev_atti_call_count
            )
            cm.mock_async_track_time_interval.assert_called_with(cm.hass, ANY, interval)
            new_callback = cm.mock_async_track_time_interval.call_args.args[1]
            assert new_callback is not old_callback
            assert new_callback.__qualname__ == old_callback.__qualname__
            old_callback = new_callback

        self._prev_atti_callback = old_callback

    @pytest.mark.parametrize("expected_lingering_tasks", [True])
    @pytest.mark.parametrize("expected_lingering_timers", [True])
    async def test_switch_keep_alive_startup(self, common_mocks: CommonMocks, fake_underlying_switch: MockSwitch):
        """Test that switch keep-alive service calls are made at startup time."""

        thermostat = common_mocks.thermostat
        await thermostat.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert thermostat.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert thermostat.target_temperature == 15
        assert thermostat.is_device_active is False

        # When the keep-alive feature is enabled, regular calls to the switch
        # turn_on / turn_off methods are _scheduled_ at start up.
        self._assert_async_mock_track_time_interval(common_mocks, 1)

        # Those keep-alive calls are scheduled but until the callback is called,
        # no service calls are made to the SERVICE_TURN_OFF home assistant service.
        self._assert_service_call(common_mocks, [])

        # Call the keep-alive callback a few times (as if `async_track_time_interval`
        # had done it) and assert that the callback function is replaced each time.
        await self._assert_multipe_keep_alive_callback_calls(common_mocks, 2)

        # Every time the keep-alive callback is called, the home assistant switch
        # turn on/off service should be called too.
        self._assert_service_call(
            common_mocks,
            [
                call("switch", SERVICE_TURN_OFF, {"entity_id": "switch.mock_switch"}),
                call("switch", SERVICE_TURN_OFF, {"entity_id": "switch.mock_switch"}),
            ],
        )

    @pytest.mark.parametrize("expected_lingering_tasks", [True])
    @pytest.mark.parametrize("expected_lingering_timers", [True])
    async def test_switch_keep_alive(self, common_mocks: CommonMocks, fake_underlying_switch: MockSwitch):
        """Test that switch keep-alive service calls are made during thermostat operation."""

        hass = common_mocks.hass
        thermostat = common_mocks.thermostat

        await thermostat.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert thermostat.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert thermostat.target_temperature == 15
        assert thermostat.is_device_active is False

        tz = get_tz(hass)  # pylint: disable=invalid-name
        now = datetime.now(tz)
        event_timestamp = now - timedelta(minutes=4)

        # 1. Decrease the temperature to activate the heater switch

        await send_temperature_change_event(thermostat, 14, event_timestamp)

        # async_track_time_interval() should have been called twice: once at startup
        # while the switch was turned off, and once when the switch was turned on.
        self._assert_async_mock_track_time_interval(common_mocks, 2)

        # The keep-alive callback hasn't been called yet, so the only service
        # call so far is to SERVICE_TURN_ON as a result of the switch turn_on()
        # method being called when the target temperature increased.
        self._assert_service_call(
            common_mocks,
            [call("switch", SERVICE_TURN_ON, {"entity_id": "switch.mock_switch"})],
        )
        common_mocks.mock_is_state.return_value = True

        # Call the keep-alive callback a few times (as if `async_track_time_interval`
        # had done it) and assert that the callback function is replaced each time.
        await self._assert_multipe_keep_alive_callback_calls(common_mocks, 2)

        # Every time the keep-alive callback is called, the home assistant switch
        # turn on/off service should be called too.
        self._assert_service_call(
            common_mocks,
            [
                call("switch", SERVICE_TURN_ON, {"entity_id": "switch.mock_switch"}),
                call("switch", SERVICE_TURN_ON, {"entity_id": "switch.mock_switch"}),
            ],
        )

        # 2. Increase the temperature to deactivate the heater switch

        # Cancel the existing cycle so the new cycle with on_time_sec=0 can start
        await thermostat.cycle_scheduler.cancel_cycle()

        await send_temperature_change_event(thermostat, 20, event_timestamp)

        # The zero-percent cycle turns the underlying switch off and rearms keep-alive.
        self._assert_async_mock_track_time_interval(common_mocks, 1)

        # turn_off() should have triggered a call to the SERVICE_TURN_OFF service.
        self._assert_service_call(
            common_mocks,
            [call("switch", SERVICE_TURN_OFF, {"entity_id": "switch.mock_switch"})],
        )
        common_mocks.mock_is_state.return_value = False

        # Call the keep-alive callback a few times (as if `async_track_time_interval`
        # had done it) and assert that the callback function is replaced each time.
        await self._assert_multipe_keep_alive_callback_calls(common_mocks, 2)

        # Every time the keep-alive callback is called, the home assistant switch
        # turn on/off service should be called too.
        self._assert_service_call(
            common_mocks,
            [
                call("switch", SERVICE_TURN_OFF, {"entity_id": "switch.mock_switch"}),
                call("switch", SERVICE_TURN_OFF, {"entity_id": "switch.mock_switch"}),
            ],
        )


class TestBackoffTimer:
    """Test the keep_alive.BackoffTimer helper class."""

    def test_exponential_period_increase(self):
        """Test that consecutive calls to is_ready() produce increasing wait periods."""
        with patch(
            "custom_components.versatile_thermostat.keep_alive.monotonic"
        ) as mock_monotonic:
            timer = BackoffTimer(
                multiplier=2,
                lower_limit_sec=30,
                upper_limit_sec=86400,
                initially_ready=True,
            )
            mock_monotonic.return_value = 100
            assert timer.is_ready()
            mock_monotonic.return_value = 129
            assert not timer.is_ready()
            mock_monotonic.return_value = 130
            assert timer.is_ready()
            mock_monotonic.return_value = 188
            assert not timer.is_ready()
            mock_monotonic.return_value = 189
            assert not timer.is_ready()
            mock_monotonic.return_value = 190
            assert timer.is_ready()
            mock_monotonic.return_value = 309
            assert not timer.is_ready()

    def test_the_upper_limit_option(self):
        """Test the timer.in_progress property and the effect of timer.reset()."""
        with patch(
            "custom_components.versatile_thermostat.keep_alive.monotonic"
        ) as mock_monotonic:
            timer = BackoffTimer(
                multiplier=2,
                lower_limit_sec=30,
                upper_limit_sec=50,
                initially_ready=True,
            )
            mock_monotonic.return_value = 100
            assert timer.is_ready()
            mock_monotonic.return_value = 129
            assert not timer.is_ready()
            mock_monotonic.return_value = 130
            assert timer.is_ready()
            mock_monotonic.return_value = 178
            assert not timer.is_ready()
            mock_monotonic.return_value = 179
            assert not timer.is_ready()
            mock_monotonic.return_value = 180
            assert timer.is_ready()
            mock_monotonic.return_value = 229
            assert not timer.is_ready()
            mock_monotonic.return_value = 230
            assert timer.is_ready()

    def test_the_lower_limit_option(self):
        """Test the timer.in_progress property and the effect of timer.reset()."""
        with patch(
            "custom_components.versatile_thermostat.keep_alive.monotonic"
        ) as mock_monotonic:
            timer = BackoffTimer(
                multiplier=0.5,
                lower_limit_sec=30,
                upper_limit_sec=50,
                initially_ready=True,
            )
            mock_monotonic.return_value = 100
            assert timer.is_ready()
            mock_monotonic.return_value = 129
            assert not timer.is_ready()
            mock_monotonic.return_value = 130
            assert timer.is_ready()
            mock_monotonic.return_value = 158
            assert not timer.is_ready()
            mock_monotonic.return_value = 159
            assert not timer.is_ready()
            mock_monotonic.return_value = 160
            assert timer.is_ready()

    def test_initial_is_ready_result(self):
        """Test that the first call to is_ready() produces the initially_ready option value."""
        with patch(
            "custom_components.versatile_thermostat.keep_alive.monotonic"
        ) as mock_monotonic:
            for initial in [True, False]:
                timer = BackoffTimer(
                    multiplier=2,
                    lower_limit_sec=30,
                    upper_limit_sec=86400,
                    initially_ready=initial,
                )
                mock_monotonic.return_value = 100
                assert timer.is_ready() == initial
                assert not timer.is_ready()

    def test_in_progress_and_reset(self):
        """Test the timer.in_progress property and the effect of timer.reset()."""
        with patch(
            "custom_components.versatile_thermostat.keep_alive.monotonic"
        ) as mock_monotonic:
            timer = BackoffTimer(
                multiplier=2,
                lower_limit_sec=30,
                upper_limit_sec=86400,
                initially_ready=True,
            )
            mock_monotonic.return_value = 100
            assert not timer.in_progress
            assert timer.is_ready()
            assert timer.in_progress
            assert not timer.is_ready()
            timer.reset()
            assert not timer.in_progress
            assert timer.is_ready()
            assert timer.in_progress
            assert not timer.is_ready()
