# pylint: disable=protected-access, unused-argument, line-too-long
""" Test the Power management """
from unittest.mock import patch, call, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timedelta
import asyncio
import logging

from homeassistant.components.number import SERVICE_SET_VALUE
from homeassistant.const import UnitOfPower
from vtherm_api import PowerCommandKind

from custom_components.versatile_thermostat.thermostat_switch import ThermostatOverSwitch
from custom_components.versatile_thermostat.thermostat_climate_valve import ThermostatOverClimateValve
from custom_components.versatile_thermostat.feature_power_manager import FeaturePowerManager
from custom_components.versatile_thermostat.underlyings import UnderlyingSwitch
from custom_components.versatile_thermostat.cycle_scheduler import CycleScheduler
from custom_components.versatile_thermostat.const import HVAC_OFF_REASON_SAFETY, HVAC_OFF_REASON_WINDOW_DETECTION

from custom_components.versatile_thermostat.prop_algo_tpi import TpiAlgorithm
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "is_over_climate, is_device_active, power, max_power, check_power_available",
    [
        # don't switch to overpower (power is enough)
        (False, False, 1000, 3000, True),
        # switch to overpower (power is not enough)
        (False, False, 2000, 3000, False),
        # don't switch to overpower (power is not enough but device is already on)
        (False, True, 2000, 3000, True),
        # Same with a over_climate
        # don't switch to overpower (power is enough)
        (True, False, 1000, 3000, True),
        # switch to overpower (power is not enough)
        (True, False, 2000, 3000, False),
        # don't switch to overpower (power is not enough but device is already on)
        (True, True, 2000, 3000, True),
        # Leave overpowering state
        # switch to not overpower (power is enough)
        (False, False, 1000, 3000, True),
        # don't switch to overpower (power is still not enough)
        (False, False, 2000, 3000, False),
        # keep overpower (power is not enough but device is already on)
        (False, True, 3000, 3000, False),
    ],
)
async def test_power_feature_manager(
    hass: HomeAssistant,
    is_over_climate,
    is_device_active,
    power,
    max_power,
    check_power_available,
):
    """Test the FeaturePresenceManager class direclty"""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # 1. creation
    power_manager = FeaturePowerManager(fake_vtherm, hass)

    assert power_manager is not None
    assert power_manager.is_configured is False
    assert power_manager.overpowering_state == STATE_UNAVAILABLE
    assert power_manager.name == "the name"

    assert len(power_manager._active_listener) == 0

    custom_attributes = {}
    power_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_power_configured"] is False
    assert custom_attributes.get("power_manager") is not None
    assert custom_attributes["power_manager"].get("device_power") == 0
    assert custom_attributes["power_manager"].get("mean_cycle_power") is None
    assert custom_attributes["power_manager"].get("power_sensor_entity_id") is None

    # 2. post_init
    vtherm_api.find_central_configuration = MagicMock()
    vtherm_api.central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
        }
    )
    assert vtherm_api.central_power_manager.is_configured

    power_manager.post_init(
        {
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 10,
            CONF_DEVICE_POWER: 1234,
        }
    )

    await power_manager.start_listening()

    assert power_manager.is_configured is True
    assert power_manager.overpowering_state == STATE_UNKNOWN

    custom_attributes = {}
    power_manager.add_custom_attributes(custom_attributes)
    assert custom_attributes["is_power_configured"] is True
    assert custom_attributes["power_manager"]["power_sensor_entity_id"] == "sensor.the_power_sensor"
    assert custom_attributes["power_manager"]["max_power_sensor_entity_id"] == "sensor.the_max_power_sensor"
    assert custom_attributes["power_manager"]["overpowering_state"] == STATE_UNKNOWN
    assert custom_attributes["power_manager"]["device_power"] == 1234
    assert custom_attributes["power_manager"]["power_temp"] == 10
    assert custom_attributes["power_manager"]["current_power"] is None
    assert custom_attributes["power_manager"]["current_max_power"] is None

    # 3. start listening
    await power_manager.start_listening()
    assert power_manager.is_configured is True
    assert power_manager.overpowering_state == STATE_UNKNOWN

    assert len(power_manager._active_listener) == 0  # no more listening

    # 4. test refresh and check_overpowering with the parametrized
    # fmt:off
    with patch("custom_components.versatile_thermostat.feature_central_power_manager.FeatureCentralPowerManager.current_max_power", new_callable=PropertyMock, return_value=max_power), \
        patch("custom_components.versatile_thermostat.feature_central_power_manager.FeatureCentralPowerManager.current_power", new_callable=PropertyMock, return_value=power):
    # fmt:on

        # Finish the mock configuration
        tpi_algo = TpiAlgorithm(0.6, 0.01, 5, 0, 0, "climate.vtherm")
        tpi_algo._on_percent = 1 # pylint: disable="protected-access"
        type(fake_vtherm).hvac_mode = PropertyMock(return_value=VThermHvacMode_HEAT)
        type(fake_vtherm).is_device_active = PropertyMock(return_value=is_device_active)
        type(fake_vtherm).is_over_climate = PropertyMock(return_value=is_over_climate)
        type(fake_vtherm).proportional_algorithm = PropertyMock(return_value=tpi_algo)
        type(fake_vtherm).nb_underlying_entities = PropertyMock(return_value=1)
        type(fake_vtherm).safe_on_percent = PropertyMock(return_value=1.0)
        fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

        ret, power_consumption_max = await power_manager.check_power_available()
        assert ret == check_power_available
        if is_device_active:
            assert power_consumption_max == 0
        else:
            assert power_consumption_max == 1234


async def test_power_manager_custom_attributes_use_configured_units(
    hass: HomeAssistant,
):
    """Diagnostic attributes must use the unit they advertise."""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)
    fake_vtherm.proportional_algorithm = None
    fake_vtherm.is_over_climate = True
    fake_vtherm.is_device_active = True

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
    vtherm_api.find_central_configuration = MagicMock(return_value=object())
    central_power_manager = vtherm_api.central_power_manager
    central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
            CONF_POWER_UNIT: POWER_UNIT_KILO_WATT,
        }
    )
    central_power_manager._current_power = 1500.0
    central_power_manager._current_max_power = 3000.0

    power_manager = FeaturePowerManager(fake_vtherm, hass)
    power_manager.post_init(
        {
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 10,
            CONF_DEVICE_POWER: 2.0,
            CONF_POWER_UNIT: POWER_UNIT_KILO_WATT,
        }
    )
    await power_manager.start_listening()

    custom_attributes = {}
    power_manager.add_custom_attributes(custom_attributes)
    attributes = custom_attributes["power_manager"]

    assert attributes["device_power"] == 2.0
    assert attributes["mean_cycle_power"] == 2.0
    assert attributes["power_unit"] == UnitOfPower.KILO_WATT
    assert attributes["current_power"] == 1.5
    assert attributes["current_max_power"] == 3.0
    assert attributes["central_power_unit"] == UnitOfPower.KILO_WATT


async def test_power_manager_checks_available_power_with_kilowatt_device(
    hass: HomeAssistant,
):
    """Availability checks use the Watts-normalized device power of a kW VTherm."""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    fake_vtherm.entity_id = "climate.kilowatt_vtherm"
    type(fake_vtherm).name = PropertyMock(return_value="kilowatt vtherm")
    type(fake_vtherm).is_device_active = PropertyMock(return_value=False)
    type(fake_vtherm).is_over_climate = PropertyMock(return_value=False)
    type(fake_vtherm).nb_underlying_entities = PropertyMock(return_value=1)
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
    vtherm_api.find_central_configuration = MagicMock(return_value=object())
    central_power_manager = vtherm_api.central_power_manager
    central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
            CONF_POWER_UNIT: POWER_UNIT_WATT,
        }
    )
    central_power_manager._current_power = 2000.0
    central_power_manager._current_max_power = 3500.0

    power_manager = FeaturePowerManager(fake_vtherm, hass)
    power_manager.post_init(
        {
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 10,
            CONF_DEVICE_POWER: 2.0,
            CONF_POWER_UNIT: POWER_UNIT_KILO_WATT,
        }
    )
    await power_manager.start_listening()

    available, startup_power = await power_manager.check_power_available()

    assert power_manager.device_power == 2000.0
    assert startup_power == 2000.0
    assert available is False


@pytest.mark.parametrize("persisted_unit", [POWER_UNIT_MEGA_WATT, POWER_UNIT_AUTO])
async def test_power_manager_falls_back_to_watt_for_an_invalid_persisted_unit(
    hass: HomeAssistant,
    persisted_unit,
) -> None:
    """Only W and kW are accepted for a VTherm persisted power unit."""
    power_manager = FeaturePowerManager(MagicMock(), hass)

    power_manager.post_init(
        {
            CONF_USE_POWER_FEATURE: True,
            CONF_DEVICE_POWER: 2.0,
            CONF_POWER_UNIT: persisted_unit,
        }
    )

    assert power_manager.power_unit == UnitOfPower.WATT
    assert power_manager.device_power == 2.0


async def test_power_feature_manager_reserves_startup_power_per_underlying_for_multi_underlyings(
    hass: HomeAssistant,
):
    """A multi-underlying VTherm must reserve startup power per underlying."""

    fake_vtherm = MagicMock(spec=BaseThermostat)
    fake_vtherm.entity_id = "climate.theoverswitchmockname"
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).is_device_active = PropertyMock(return_value=False)
    type(fake_vtherm).is_over_climate = PropertyMock(return_value=False)
    type(fake_vtherm).nb_underlying_entities = PropertyMock(return_value=4)
    type(fake_vtherm).safe_on_percent = PropertyMock(return_value=0.1)
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
    power_manager = FeaturePowerManager(fake_vtherm, hass)

    vtherm_api.find_central_configuration = MagicMock()
    vtherm_api.central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
        }
    )
    vtherm_api.central_power_manager._current_power = 730
    vtherm_api.central_power_manager._current_max_power = 1000

    power_manager.post_init(
        {
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 10,
            CONF_DEVICE_POWER: 1000,
        }
    )

    await power_manager.start_listening()

    ret, power_consumption_max = await power_manager.check_power_available("switch.one")
    assert ret is True
    assert power_consumption_max == 250

    power_manager.add_power_consumption_to_central_power_manager("switch.one")
    assert vtherm_api.central_power_manager.started_vtherm_total_power == 250
    assert len(vtherm_api.central_power_manager._started_vtherm_total_power_by_id) == 1  # pylint: disable=protected-access

    # Re-checking the same underlying must stay idempotent.
    ret, power_consumption_max = await power_manager.check_power_available("switch.one")
    assert ret is True
    assert power_consumption_max == 250

    power_manager.add_power_consumption_to_central_power_manager("switch.one")
    assert vtherm_api.central_power_manager.started_vtherm_total_power == 250
    assert len(vtherm_api.central_power_manager._started_vtherm_total_power_by_id) == 1  # pylint: disable=protected-access

    # A distinct underlying must be denied because only one 250W slice is available.
    ret, power_consumption_max = await power_manager.check_power_available("switch.two")
    assert ret is False
    assert power_consumption_max == 250

    power_manager.sub_power_consumption_to_central_power_manager("switch.one")
    assert vtherm_api.central_power_manager.started_vtherm_total_power == 0

    # Releasing the reservation multiple times must stay idempotent as well.
    power_manager.sub_power_consumption_to_central_power_manager("switch.one")
    assert vtherm_api.central_power_manager.started_vtherm_total_power == 0


async def _create_power_managed_underlyings(
    hass: HomeAssistant,
    entity_ids: list[str],
    states: list[str | None],
    current_power: float,
    max_power: float,
    is_inversed: bool = False,
):
    """Create underlying switches with the real power reservation managers."""
    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)
    vtherm_api.find_central_configuration = MagicMock(return_value=object())
    central_power_manager = vtherm_api.central_power_manager
    central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
        }
    )
    central_power_manager._current_power = current_power
    central_power_manager._current_max_power = max_power

    thermostat = MagicMock()
    thermostat.entity_id = "climate.multi_relay_test"
    thermostat.name = "multi relay test"
    thermostat.is_over_climate = False
    thermostat.is_inversed = is_inversed
    thermostat.nb_underlying_entities = len(entity_ids)
    thermostat.is_device_active = False
    thermostat.safe_on_percent = 1
    thermostat.async_get_last_state = AsyncMock(return_value=None)
    thermostat.async_underlying_entity_turn_off = AsyncMock()
    thermostat.update_states = AsyncMock()
    thermostat.requested_state.force_changed = MagicMock()

    power_manager = FeaturePowerManager(thermostat, hass)
    power_manager.post_init(
        {
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 10,
            CONF_DEVICE_POWER: 750,
        }
    )
    await power_manager.start_listening()
    thermostat.power_manager = power_manager

    for entity_id, state in zip(entity_ids, states):
        if state is not None:
            hass.states.async_set(entity_id, state)

    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    underlyings = [UnderlyingSwitch(hass, thermostat, entity_id, keep_alive_sec=0) for entity_id in entity_ids]
    for underlying in underlyings:
        underlying._is_initialized = True
    thermostat.underlying_entities = underlyings
    return thermostat, power_manager, central_power_manager, underlyings


@pytest.mark.parametrize(
    "is_inversed, heating_state",
    [(False, STATE_ON), (True, STATE_OFF)],
)
async def test_multi_underlying_turn_on_maintains_known_heating_relays_with_zero_startup_power(
    hass: HomeAssistant,
    is_inversed: bool,
    heating_state: str,
):
    """A 100% restart must not recount already-heating relays, including inverted ones."""
    _, power_manager, central_power_manager, underlyings = await _create_power_managed_underlyings(
        hass,
        ["switch.relay_one", "switch.relay_two", "switch.relay_three"],
        [heating_state] * 3,
        current_power=950,
        max_power=1000,
        is_inversed=is_inversed,
    )

    check_power = AsyncMock(wraps=power_manager.check_power_available)
    power_manager.check_power_available = check_power

    for underlying in underlyings:
        assert await underlying.turn_on() is True

    assert hass.services.async_call.await_count == 3
    assert check_power.await_args_list == [
        call("switch.relay_one"),
        call("switch.relay_two"),
        call("switch.relay_three"),
    ]
    assert central_power_manager.started_vtherm_total_power == 0
    assert power_manager.calculate_underlying_startup_power() == 250
    assert power_manager.calculate_underlying_startup_power("switch.relay_one") == 0
    assert power_manager.calculate_underlying_startup_power("switch.relay_two") == 0


@pytest.mark.parametrize(
    "state, is_inversed",
    [
        (STATE_OFF, False),
        (STATE_UNKNOWN, False),
        (STATE_UNAVAILABLE, False),
        (None, False),
        (STATE_ON, True),
    ],
)
async def test_multi_underlying_turn_on_checks_states_not_known_as_heating(
    hass: HomeAssistant,
    state: str | None,
    is_inversed: bool,
):
    """Stopped, missing and uncertain states retain conservative startup reservations."""
    _, _, central_power_manager, underlyings = await _create_power_managed_underlyings(
        hass,
        ["switch.relay_one", "switch.relay_two", "switch.relay_three"],
        [state, STATE_OFF, STATE_OFF],
        current_power=0,
        max_power=1000,
        is_inversed=is_inversed,
    )

    assert await underlyings[0].turn_on() is True

    assert hass.services.async_call.await_count == 1
    assert central_power_manager.get_started_vtherm_power("switch.relay_one") == 250


async def test_multi_underlying_active_and_stopped_relays_are_counted_individually(
    hass: HomeAssistant,
):
    """Each relay uses the common startup calculator with its own activity state."""
    _, _, central_power_manager, underlyings = await _create_power_managed_underlyings(
        hass,
        ["switch.relay_one", "switch.relay_two", "switch.relay_three"],
        [STATE_ON, STATE_OFF, STATE_OFF],
        current_power=400,
        max_power=1000,
    )
    central_power_manager.set_started_vtherm_power("switch.relay_one", 250)

    assert await underlyings[0].turn_on() is True
    assert await underlyings[1].turn_on() is True

    assert hass.services.async_call.await_count == 2
    assert central_power_manager.get_started_vtherm_power("switch.relay_one") == 250
    assert central_power_manager.get_started_vtherm_power("switch.relay_two") == 250
    assert central_power_manager.started_vtherm_total_power == 500


async def test_multi_underlying_maintenance_preserves_reservation_for_next_relay_check(
    hass: HomeAssistant,
):
    """A maintained relay's reservation remains in the strict check for another relay."""
    thermostat, _, central_power_manager, underlyings = await _create_power_managed_underlyings(
        hass,
        ["switch.relay_one", "switch.relay_two", "switch.relay_three"],
        [STATE_ON, STATE_OFF, STATE_OFF],
        current_power=500,
        max_power=1000,
    )
    central_power_manager.set_started_vtherm_power("switch.relay_one", 250)

    assert await underlyings[0].turn_on() is True
    assert await underlyings[1].turn_on() is False

    assert hass.services.async_call.await_count == 1
    assert central_power_manager.get_started_vtherm_power("switch.relay_one") == 250
    assert central_power_manager.get_started_vtherm_power("switch.relay_two") == 0
    thermostat.requested_state.force_changed.assert_called_once()


async def test_multi_underlying_known_heating_still_obeys_inhibition(
    hass: HomeAssistant,
):
    """A known-heating relay cannot bypass the command gate."""
    _, _, central_power_manager, underlyings = await _create_power_managed_underlyings(
        hass,
        ["switch.relay_one", "switch.relay_two", "switch.relay_three"],
        [STATE_ON, STATE_OFF, STATE_OFF],
        current_power=0,
        max_power=1000,
    )
    underlyings[0].is_command_blocked = MagicMock(return_value=True)

    assert await underlyings[0].turn_on() is False

    assert hass.services.async_call.await_count == 0
    assert central_power_manager.started_vtherm_total_power == 0


async def test_multi_underlying_known_heating_propagates_service_failure(
    hass: HomeAssistant,
):
    """A service failure on a maintenance command is still propagated."""
    _, _, central_power_manager, underlyings = await _create_power_managed_underlyings(
        hass,
        ["switch.relay_one", "switch.relay_two", "switch.relay_three"],
        [STATE_ON, STATE_OFF, STATE_OFF],
        current_power=950,
        max_power=1000,
    )
    hass.services.async_call.side_effect = RuntimeError("service failed")

    with pytest.raises(RuntimeError, match="service failed"):
        await underlyings[0].turn_on()

    assert central_power_manager.started_vtherm_total_power == 0


async def test_mono_underlying_turn_on_keeps_existing_power_check(hass: HomeAssistant):
    """The maintenance exemption is limited to multi-underlying switches."""
    thermostat, power_manager, _, underlyings = await _create_power_managed_underlyings(
        hass,
        ["switch.single_relay"],
        [STATE_ON],
        current_power=1000,
        max_power=1000,
    )
    thermostat.is_device_active = True
    check_power = AsyncMock(wraps=power_manager.check_power_available)
    power_manager.check_power_available = check_power

    assert await underlyings[0].turn_on() is False

    check_power.assert_awaited_once_with("switch.single_relay")
    assert hass.services.async_call.await_count == 0
    assert power_manager.calculate_underlying_startup_power() == 0
    assert power_manager.calculate_underlying_startup_power("switch.single_relay") == 0


@pytest.mark.parametrize("current_power,allowed", [(7600, False), (7500, False), (7000, True)])
async def test_issue_2206_strict_startup_budget(hass: HomeAssistant, current_power, allowed):
    """The instantaneous 3500 W startup uses the existing strict 11000 W limit."""
    _, power_manager, _, underlyings = await _create_power_managed_underlyings(
        hass, ["switch.single_relay"], [STATE_OFF], current_power=current_power, max_power=11000
    )
    power_manager._device_power = 3500

    available, startup_power = await power_manager.check_power_available(underlyings[0].power_reservation_key)

    assert startup_power == 3500
    assert available is allowed


@pytest.mark.parametrize("proportional_function", [PROPORTIONAL_FUNCTION_TPI, "external_plugin"])
async def test_refusal_propagation_is_restricted_to_native_tpi(hass: HomeAssistant, proportional_function):
    """External proportional handlers retain their existing update_states call."""
    thermostat, _, _, underlyings = await _create_power_managed_underlyings(
        hass, ["switch.single_relay"], [STATE_OFF], current_power=1000, max_power=1000
    )
    thermostat.proportional_function = proportional_function

    assert await underlyings[0].turn_on() is False
    if proportional_function == PROPORTIONAL_FUNCTION_TPI:
        thermostat.update_states.assert_awaited_once_with(force=True, _control_heating=False)
    else:
        thermostat.update_states.assert_awaited_once_with(force=True)


@pytest.mark.parametrize("on_percent", [0.8, 1.0])
async def test_scheduler_abandons_real_command_gate_refusal(hass: HomeAssistant, on_percent):
    """The real command gate's False return cannot arm a cycle or turn on the next relay."""
    thermostat, power_manager, _, underlyings = await _create_power_managed_underlyings(
        hass, ["switch.relay_one", "switch.relay_two", "switch.relay_three"],
        [STATE_OFF, STATE_OFF, STATE_OFF], current_power=0, max_power=1000,
    )
    scheduler = CycleScheduler(hass, thermostat, underlyings, 300)
    underlyings[0].is_command_blocked = MagicMock(return_value=True)
    with patch.object(underlyings[1], "turn_on", wraps=underlyings[1].turn_on) as next_on, \
        patch.object(power_manager, "check_power_available", wraps=power_manager.check_power_available) as check_power, \
        patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later") as call_later:
        await scheduler.start_cycle(VThermHvacMode_HEAT, on_percent, force=True)

        next_on.assert_not_awaited()
        check_power.assert_not_awaited()
        thermostat.async_underlying_entity_turn_off.assert_awaited_once()
        call_later.assert_not_called()
        hass.services.async_call.assert_not_awaited()


@pytest.mark.parametrize(
    "entity_id,state,is_inversed,on_command,off_command,expected_on,expected_off",
    [
        ("switch.single_relay", STATE_ON, True, None, None, ("switch", "turn_off", {"entity_id": "switch.single_relay"}), ("switch", "turn_on", {"entity_id": "switch.single_relay"})),
        ("climate.virtual_relay", "off", False, "set_hvac_mode/hvac_mode:heat", "set_hvac_mode/hvac_mode:off", ("climate", "set_hvac_mode", {"entity_id": "climate.virtual_relay", "hvac_mode": "heat"}), ("climate", "set_hvac_mode", {"entity_id": "climate.virtual_relay", "hvac_mode": "off"})),
    ],
)
async def test_power_refusal_and_recovery_with_virtual_or_inverted_commands(
    hass: HomeAssistant, entity_id, state, is_inversed, on_command, off_command, expected_on, expected_off,
):
    """Refused and subsequently allowed commands keep their logical direction."""
    thermostat, _, central, _ = await _create_power_managed_underlyings(
        hass, [entity_id], [state], current_power=1000, max_power=1000, is_inversed=is_inversed
    )
    underlying = UnderlyingSwitch(hass, thermostat, entity_id, 0, on_command, off_command)
    underlying._is_initialized = True
    thermostat.underlying_entities = [underlying]

    await underlying.turn_off()
    assert await underlying.turn_on() is False
    assert hass.services.async_call.await_args_list == [call(*expected_off)]
    central._current_power = 0
    assert await underlying.turn_on() is True
    assert hass.services.async_call.await_args_list == [call(*expected_off), call(*expected_on)]


@pytest.mark.parametrize(
    "current_overpowering_state, is_overpowering, new_overpowering_state, msg_sent",
    [
        # false -> false
        (STATE_OFF, False, STATE_OFF, False),
        # false -> true
        (STATE_OFF, True, STATE_ON, True),
        # true -> true
        (STATE_ON, True, STATE_ON, False),
        # true -> False
        (STATE_ON, False, STATE_OFF, True),
    ],
)
async def test_power_feature_manager_set_overpowering(
    hass,
    current_overpowering_state,
    is_overpowering,
    new_overpowering_state,
    msg_sent,
):
    """Test the set_overpowering method of FeaturePowerManager"""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    fake_vtherm.async_get_last_state = AsyncMock(return_value=None)

    vtherm_api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(hass)

    # 1. creation / init
    power_manager = FeaturePowerManager(fake_vtherm, hass)
    vtherm_api.find_central_configuration = MagicMock()
    vtherm_api.central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: "sensor.the_power_sensor",
            CONF_MAX_POWER_SENSOR: "sensor.the_max_power_sensor",
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 13,
        }
    )
    assert vtherm_api.central_power_manager.is_configured

    power_manager.post_init(
        {
            CONF_USE_POWER_FEATURE: True,
            CONF_PRESET_POWER: 10,
            CONF_DEVICE_POWER: 1234,
        }
    )

    await power_manager.start_listening()

    assert power_manager.is_configured is True
    assert power_manager.overpowering_state == STATE_UNKNOWN

    # overwrite overpowering state for the test
    power_manager._overpowering_state = current_overpowering_state

    # fmt:off
    with patch("custom_components.versatile_thermostat.feature_central_power_manager.FeatureCentralPowerManager.current_max_power", new_callable=PropertyMock, return_value=2000), \
        patch("custom_components.versatile_thermostat.feature_central_power_manager.FeatureCentralPowerManager.current_power", new_callable=PropertyMock, return_value=1000):
    # fmt:on
        # Finish mocking
        fake_vtherm.send_event = MagicMock()


        # Call set_overpowering
        await power_manager.set_overpowering(is_overpowering, 1234)

        assert power_manager.overpowering_state == new_overpowering_state

        if not is_overpowering:
            assert power_manager.overpowering_state == STATE_OFF

            if msg_sent:
                fake_vtherm.send_event.assert_has_calls(
                    [
                        call.fake_vtherm.send_event(
                            EventType.POWER_EVENT,
                            {
                                "type": "end",
                                "current_power": 1000,
                                "device_power": 1234,
                                "current_max_power": 2000,
                            },
                        ),
                    ]
                )
        # is_overpowering is True
        else:
            assert power_manager.overpowering_state == STATE_ON

            if current_overpowering_state == STATE_OFF:
                assert fake_vtherm.send_event.call_count == 1
            else:
                assert fake_vtherm.send_event.call_count == 0

            if msg_sent:
                fake_vtherm.send_event.assert_has_calls(
                    [
                        call.fake_vtherm.send_event(
                            EventType.POWER_EVENT,
                            {
                                "type": "start",
                                "current_power": 1000,
                                "device_power": 1234,
                                "current_max_power": 2000,
                                "current_power_consumption": 1234.0,
                            },
                        ),
                    ]
                )

        fake_vtherm.reset_mock()

    power_manager.stop_listening()
    await hass.async_block_till_done()


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_hvac_off(hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager, fake_underlying_switch: MockSwitch):
    """Test the Power management"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_POWER_UNIT: POWER_UNIT_WATT,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname", temps
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 19
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN
    assert entity.hvac_mode == VThermHvacMode_OFF

    now: datetime = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)

    # Send power mesurement
    # fmt:off
    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", 50),
            "sensor.the_max_power_sensor": State("sensor.the_max_power_sensor", 300),
        },
        State("unknown.entity_id", "unknown"),
    )
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
    # fmt: on
        await send_power_change_event(entity, 50, now)
        assert entity.power_manager.is_overpowering_detected is False

        # All configuration is not complete
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF # because power and max_power are set due to patch and side effects above.

        # Send power max mesurement
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)
        await send_max_power_change_event(entity, 300, now)
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF # because power and max_power are set due to patch and side effects above.

    # Send power max mesurement too low but VThermHvacMode is off
    side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 149))
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off:
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_max_power_change_event(entity, 149, datetime.now())
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is > power_max but we stay in Boost cause thermostat if Off
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.parametrize("on_percent", [0.66, 1.0])
@pytest.mark.parametrize("stop_kind", ["manual", "central", "inhibition"])
async def test_first_power_refusal_does_not_restart_cycle(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager,
    fake_underlying_switch: MockSwitch, on_percent, stop_kind,
):
    """The real first refusal must not restart or leave scheduler timers."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="RefusalThermostat",
        unique_id="refusal_thermostat",
        data={
            CONF_NAME: "RefusalThermostat",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 7,
            CONF_TEMP_MAX: 30,
            CONF_USE_POWER_FEATURE: True,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.0,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_DEVICE_POWER: 3500,
            CONF_POWER_UNIT: POWER_UNIT_WATT,
            CONF_PRESET_POWER: 13,
        },
    )
    periodic_callbacks = []

    def register_periodic(_hass, callback, interval):
        assert interval == timedelta(minutes=5)
        periodic_callbacks.append(callback)
        return MagicMock()

    with patch("custom_components.versatile_thermostat.thermostat_switch.async_track_time_interval", side_effect=register_periodic):
        entity = await create_thermostat(
            hass, entry, "climate.refusalthermostat", {"comfort": 18}
        )
    assert len(periodic_callbacks) == 1
    now = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    await send_temperature_change_event(entity, 11.9, now)
    scheduler = entity.cycle_scheduler
    await scheduler.cancel_cycle()
    await entity.async_underlying_entity_turn_off()
    central = VersatileThermostatAPI.get_vtherm_api().central_power_manager
    central._current_power = 7600
    central._current_max_power = 11000
    entity.requested_state.force_changed()
    entity.current_state.force_changed()

    handles = []
    starts = []
    active_starts = []
    violations = []
    original_start = scheduler.start_cycle
    cycle_started = AsyncMock()
    scheduler.register_cycle_start_callback(cycle_started)

    def register_timer(_hass, delay, callback):
        handle = {"delay": delay, "callback": callback, "active": True}
        handles.append(handle)

        def cancel():
            handle["active"] = False

        handle["cancel"] = cancel
        return cancel

    async def bounded_start(*args, **kwargs):
        starts.append((args, kwargs))
        if len(active_starts) >= 2:
            violations.append("nested start limit exceeded")
            raise RuntimeError(violations[-1])
        active_starts.append(True)
        try:
            return await original_start(*args, **kwargs)
        finally:
            active_starts.pop()

    with patch.object(scheduler, "start_cycle", side_effect=bounded_start), \
        patch.object(entity, "async_underlying_entity_turn_off", wraps=entity.async_underlying_entity_turn_off) as collective_off, \
        patch.object(scheduler, "_fire_underlying_power", wraps=scheduler._fire_underlying_power) as power_hook, \
        patch.object(entity, "send_event", wraps=entity.send_event) as send_event, \
        patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later", side_effect=register_timer):
        await scheduler.start_cycle(VThermHvacMode_HEAT, on_percent, force=True)

        assert collective_off.await_count == 1
        assert len(starts) == 1
        assert not [handle for handle in handles if handle["active"]]
        assert entity.total_energy == 0
        assert not entity.requested_state.is_changed
        assert not entity.current_state.is_changed
        assert all(args.args[0] != PowerCommandKind.CYCLE_START for args in power_hook.await_args_list)
        assert sum(args.args[0] == EventType.POWER_EVENT for args in send_event.call_args_list) == 1

        for attempt in range(3):
            if attempt == 1:
                entity.current_state.set_preset(VThermPreset.COMFORT)
                entity.current_state.set_target_temperature(18)
            if attempt == 0:
                await periodic_callbacks[0](now)
            else:
                await scheduler.start_cycle(VThermHvacMode_HEAT, on_percent, force=True)
            assert entity.vtherm_preset_mode == VThermPreset.POWER
            assert entity.target_temperature == 13
            assert not [handle for handle in handles if handle["active"]]
            assert entity.total_energy == 0

        assert collective_off.await_count == 4
        assert sum(args.args[0] == EventType.POWER_EVENT for args in send_event.call_args_list) == 1
        assert all(args.args[0] != PowerCommandKind.CYCLE_START for args in power_hook.await_args_list)

        central._current_power = 7000
        with patch.object(entity, "incremente_energy", wraps=entity.incremente_energy) as credit:
            await periodic_callbacks[0](now)
            for completed_cycles in range(1, 3):
                active = [handle for handle in handles if handle["active"]]
                assert {handle["cancel"] for handle in active} == {
                    timer for timer in (scheduler._tick_unsub, scheduler._cycle_end_unsub) if timer is not None
                }
                master = next(handle for handle in active if handle["cancel"] is scheduler._cycle_end_unsub)
                if scheduler._tick_unsub is not None:
                    tick = next(handle for handle in active if handle["cancel"] is scheduler._tick_unsub)
                    hass.states.async_set("switch.mock_switch", STATE_ON)
                    tick["active"] = False
                    elapsed = scheduler._active_on_time_sec + 0.1
                    scheduler._cycle_start_time -= elapsed
                    await tick["callback"](None)
                else:
                    elapsed = 0
                master["active"] = False
                scheduler._cycle_start_time -= scheduler._cycle_duration_sec - elapsed
                await master["callback"](None)
                assert credit.call_count == completed_cycles
            await scheduler.cancel_cycle()
            assert not [handle for handle in handles if handle["active"]]

        assert entity.power_manager.is_overpowering_detected is True
        assert entity.vtherm_preset_mode == VThermPreset.POWER
        assert entity.target_temperature == 13
        assert entity._prop_algorithm.on_percent > 0

        central._current_power = 0
        await central.calculate_shedding()
        assert entity.power_manager.is_overpowering_detected is False
        assert entity.vtherm_preset_mode == VThermPreset.COMFORT
        assert entity.target_temperature == 18
        assert scheduler._cycle_end_unsub is not None
        await scheduler.cancel_cycle()
        assert not [handle for handle in handles if handle["active"]]

        await entity.async_underlying_entity_turn_off()
        hass.states.async_set("switch.mock_switch", STATE_OFF)
        central._current_power = 7600
        check_started = asyncio.Event()
        finish_check = asyncio.Event()
        original_check = entity.power_manager.check_power_available

        async def delayed_check(*args, **kwargs):
            check_started.set()
            await finish_check.wait()
            return await original_check(*args, **kwargs)

        power_hook.reset_mock()
        with patch.object(entity.power_manager, "check_power_available", side_effect=delayed_check):
            pending = asyncio.create_task(scheduler.start_cycle(VThermHvacMode_HEAT, on_percent, force=True))
            await asyncio.wait_for(check_started.wait(), timeout=2)
            if stop_kind == "manual":
                await entity.async_set_hvac_mode(VThermHvacMode_OFF)
            elif stop_kind == "central":
                await entity.check_central_mode(CENTRAL_MODE_STOPPED, None)
            else:
                await entity.async_set_inhibition(True)
            finish_check.set()
            await asyncio.wait_for(pending, timeout=2)

        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert not [handle for handle in handles if handle["active"]]
        assert all(args.args[0] != PowerCommandKind.CYCLE_START for args in power_hook.await_args_list)
        central._current_power = 7000
        await entity.async_control_heating(force=True)
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert not [handle for handle in handles if handle["active"]]

    assert not violations
    assert len(starts) == 9
    assert cycle_started.await_count == 9
    assert not [handle for handle in handles if handle["active"]]


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_issue_2206_settled_refusal_preserves_window_priority_and_changes(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager,
    fake_underlying_switch: MockSwitch,
):
    """Serialized user changes and window OFF remain effective after refusal."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PriorityRefusalThermostat",
        unique_id="priority_refusal_thermostat",
        data={
            CONF_NAME: "PriorityRefusalThermostat",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 7,
            CONF_TEMP_MAX: 30,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_WINDOW_FEATURE: True,
            CONF_WINDOW_SENSOR: "binary_sensor.mock_window_sensor",
            CONF_WINDOW_DELAY: 0,
            CONF_WINDOW_ACTION: CONF_WINDOW_TURN_OFF,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.1,
            CONF_SAFETY_DEFAULT_ON_PERCENT: 0.0,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.0,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_DEVICE_POWER: 3500,
            CONF_POWER_UNIT: POWER_UNIT_WATT,
            CONF_PRESET_POWER: 13,
        },
    )
    entity = await create_thermostat(
        hass, entry, "climate.priorityrefusalthermostat", {"comfort": 18, "boost": 19}
    )
    now = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    await send_temperature_change_event(entity, 11.9, now)
    await entity.async_underlying_entity_turn_off()
    central = VersatileThermostatAPI.get_vtherm_api().central_power_manager
    central._current_power = 7600
    central._current_max_power = 11000
    scheduler = entity.cycle_scheduler
    handles = []

    def register_timer(_hass, delay, callback):
        handle = {"delay": delay, "callback": callback, "active": True}
        handles.append(handle)

        def cancel():
            handle["active"] = False

        handle["cancel"] = cancel
        return cancel

    with patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later", side_effect=register_timer), \
        patch.object(entity.underlying_entities[0], "turn_on", wraps=entity.underlying_entities[0].turn_on) as turn_on:
        await scheduler.start_cycle(VThermHvacMode_HEAT, 0.66, force=True)
        assert entity.power_manager.is_overpowering_detected
        assert entity.vtherm_preset_mode == VThermPreset.POWER
        assert not [handle for handle in handles if handle["active"]]

        await entity.async_set_temperature(temperature=20)
        assert entity.requested_state.target_temperature == 20
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        assert entity.requested_state.preset == VThermPreset.BOOST
        await entity.async_set_hvac_mode(VThermHvacMode_OFF)
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert entity.vtherm_preset_mode == VThermPreset.POWER
        assert entity.target_temperature == 13

        central._current_power = 0
        await entity.window_manager.update_window_state(STATE_ON)
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
        blocked_on_count = turn_on.await_count
        assert not [handle for handle in handles if handle["active"]]
        await central.calculate_shedding()
        assert not entity.power_manager.is_overpowering_detected
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert turn_on.await_count == blocked_on_count
        assert not [handle for handle in handles if handle["active"]]
        await entity.window_manager.update_window_state(STATE_OFF)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert entity.vtherm_preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert scheduler._cycle_end_unsub is not None
        assert {handle["cancel"] for handle in handles if handle["active"]} == {
            timer for timer in (scheduler._tick_unsub, scheduler._cycle_end_unsub) if timer is not None
        }

        now += timedelta(minutes=6)
        entity._set_now(now)
        assert await entity.safety_manager.refresh_and_update_if_changed()
        await hass.async_block_till_done()
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_SAFETY
        assert not [handle for handle in handles if handle["active"]]
        await entity.window_manager.update_window_state(STATE_ON)
        assert entity.hvac_off_reason == HVAC_OFF_REASON_SAFETY
        blocked_on_count = turn_on.await_count
        await send_ext_temperature_change_event(entity, 5, now, sleep=False)
        await send_temperature_change_event(entity, 11.9, now, sleep=False)
        await hass.async_block_till_done()
        assert not entity.safety_manager.is_safety_detected
        assert entity.vtherm_hvac_mode == VThermHvacMode_OFF
        assert entity.hvac_off_reason == HVAC_OFF_REASON_WINDOW_DETECTION
        assert turn_on.await_count == blocked_on_count
        assert not [handle for handle in handles if handle["active"]]
        await entity.window_manager.update_window_state(STATE_OFF)
        assert entity.vtherm_hvac_mode == VThermHvacMode_HEAT
        assert entity.vtherm_preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert scheduler._cycle_end_unsub is not None
        assert {handle["cancel"] for handle in handles if handle["active"]} == {
            timer for timer in (scheduler._tick_unsub, scheduler._cycle_end_unsub) if timer is not None
        }
        await entity.async_underlying_entity_turn_off()
        assert not [handle for handle in handles if handle["active"]]


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.parametrize("inconsistent", [False, True])
async def test_already_shedding_refusal_stops_real_multi_relay_cycle(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager, inconsistent,
):
    """An already shedding real multi-relay thermostat stops the earlier relay."""
    for switch_id in ("issue2206_one", "issue2206_two", "issue2206_three"):
        await register_mock_entity(hass, MockSwitch(hass, switch_id, switch_id), SWITCH_DOMAIN)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="MultiRefusalThermostat",
        unique_id="multi_refusal_thermostat",
        data={
            CONF_NAME: "MultiRefusalThermostat",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 7,
            CONF_TEMP_MAX: 30,
            CONF_USE_POWER_FEATURE: True,
            CONF_UNDERLYING_LIST: ["switch.issue2206_one", "switch.issue2206_two", "switch.issue2206_three"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.0,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_DEVICE_POWER: 6000,
            CONF_POWER_UNIT: POWER_UNIT_WATT,
            CONF_PRESET_POWER: 13,
        },
    )
    entity = await create_thermostat(hass, entry, "climate.multirefusalthermostat", {"comfort": 18})
    now = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    await send_temperature_change_event(entity, 11.9, now)
    scheduler = entity.cycle_scheduler
    await entity.async_underlying_entity_turn_off()
    central = VersatileThermostatAPI.get_vtherm_api().central_power_manager
    central._current_power = 9000
    central._current_max_power = 11000
    entity.power_manager._overpowering_state = STATE_ON
    entity.current_state.set_preset(VThermPreset.COMFORT if inconsistent else VThermPreset.POWER)
    entity.current_state.set_target_temperature(18 if inconsistent else 13)
    hass.states.async_set("switch.issue2206_one", STATE_ON)
    hass.states.async_set("switch.issue2206_two", STATE_OFF)
    hass.states.async_set("switch.issue2206_three", STATE_OFF)
    first, second, third = entity.underlying_entities

    with patch("homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock) as service_calls, \
        patch.object(first, "turn_on", wraps=first.turn_on) as first_on, \
        patch.object(second, "turn_on", wraps=second.turn_on) as second_on, \
        patch.object(third, "turn_on", wraps=third.turn_on) as third_on, \
        patch.object(entity, "async_underlying_entity_turn_off", wraps=entity.async_underlying_entity_turn_off) as collective_off, \
        patch.object(entity, "send_event", wraps=entity.send_event) as send_event, \
        patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later") as call_later:
        await scheduler.start_cycle(VThermHvacMode_HEAT, 1.0, force=True)

        first_on.assert_awaited_once()
        second_on.assert_awaited_once()
        third_on.assert_not_awaited()
        collective_off.assert_awaited_once()
        assert service_calls.await_args_list == [
            call("switch", "turn_on", {"entity_id": "switch.issue2206_one"}),
            call("switch", "turn_off", {"entity_id": "switch.issue2206_one"}),
            call("switch", "turn_off", {"entity_id": "switch.issue2206_two"}),
            call("switch", "turn_off", {"entity_id": "switch.issue2206_three"}),
        ]
        call_later.assert_not_called()
        assert scheduler._cycle_end_unsub is None
        assert scheduler._tick_unsub is None
        assert entity.vtherm_preset_mode == VThermPreset.POWER
        assert entity.target_temperature == 13
        assert entity.total_energy == 0
        assert not [args for args in send_event.call_args_list if args.args[0] == EventType.POWER_EVENT]


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_hvac_on(hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager, fake_underlying_switch: MockSwitch):
    """Test the Power management"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_POWER_UNIT: POWER_UNIT_WATT,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname", temps
    )
    assert entity

    now: datetime = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN
    assert entity.target_temperature == 19

    # make the heater heats
    await send_temperature_change_event(entity, 15, now)
    await send_ext_temperature_change_event(entity, 1, now)
    await hass.async_block_till_done()

    assert entity.power_percent > 0

    # Send power mesurement
    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", 50),
            "sensor.the_max_power_sensor": State("sensor.the_max_power_sensor", 300),
        },
        State("unknown.entity_id", "unknown"),
    )
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
    # fmt: on
        await send_power_change_event(entity, 50, datetime.now())
        # Send power max mesurement
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)
        await send_max_power_change_event(entity, 300, datetime.now())

        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF

    # Send power max mesurement too low and VThermHvacMode is on
    side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 49))
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active", new_callable=PropertyMock, return_value=True):
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_max_power_change_event(entity, 49, now)
        await wait_for_local_condition(lambda: entity.power_manager.is_overpowering_detected is True)
        assert entity.power_manager.is_overpowering_detected is True
        # All configuration is complete and power is > power_max we switch to POWER preset
        assert entity.vtherm_preset_mode == VThermPreset.POWER
        assert entity.preset_mode == VThermPreset.POWER
        assert entity.power_manager.overpowering_state is STATE_ON
        assert entity.target_temperature == 12

        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.POWER}),
                call.send_event(
                    EventType.POWER_EVENT,
                    {
                        "type": "start",
                        "current_power": 50,
                        "device_power": 100,
                        "current_max_power": 49,
                        "current_power_consumption": 100.0,
                    },
                ),
            ],
            any_order=True,
        )
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count >= 1 # can be call twice because is_device_active is patched to True

    # Send power mesurement low to unset power preset
    side_effects.add_or_update_side_effect("sensor.the_power_sensor", State("sensor.the_power_sensor", 48))
    side_effects.add_or_update_side_effect("sensor.the_max_power_sensor", State("sensor.the_max_power_sensor", 149))
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off:
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_power_change_event(entity, 48, now)
        assert entity.power_manager.is_overpowering_detected is False
        # All configuration is complete and power is < power_max, we restore previous preset
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.overpowering_state is STATE_OFF
        assert entity.target_temperature == 19

        assert mock_send_event.call_count == 2
        mock_send_event.assert_has_calls(
            [
                call.send_event(EventType.PRESET_EVENT, {"preset": VThermPreset.BOOST}),
                call.send_event(
                    EventType.POWER_EVENT,
                    {
                        "type": "end",
                        "current_power": 48,
                        "device_power": 100,
                        "current_max_power": 149,
                    },
                ),
            ],
            any_order=True,
        )
        # heater should be turned on
        assert mock_heater_on.call_count == 1
        assert mock_heater_off.call_count == 0


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_issue_2206_two_idle_cycles_keep_raw_energy_amount(
    hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager,
    fake_underlying_switch: MockSwitch, freezer,
):
    """Two minimum-ON idle cycles produce one existing-formula credit each."""
    freezer.move_to("2024-01-01T00:00:00Z")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="IdleEnergyThermostat",
        unique_id="idle_energy_thermostat",
        data={
            CONF_NAME: "IdleEnergyThermostat",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 7,
            CONF_TEMP_MAX: 30,
            CONF_USE_POWER_FEATURE: True,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.6,
            CONF_TPI_COEF_EXT: 0.0,
            CONF_MINIMAL_ACTIVATION_DELAY: 10,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_DEVICE_POWER: 3500,
            CONF_POWER_UNIT: POWER_UNIT_WATT,
            CONF_PRESET_POWER: 13,
        },
    )
    entity = await create_thermostat(hass, entry, "climate.idleenergythermostat", {"comfort": 18})
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.COMFORT)
    await send_temperature_change_event(entity, 18 - 0.02 / 0.6, NowClass.get_now(hass), sleep=False)
    scheduler = entity.cycle_scheduler
    await scheduler.cancel_cycle()
    handles = []

    def register_timer(_hass, delay, callback):
        handle = {"delay": delay, "callback": callback, "active": True}
        handles.append(handle)

        def cancel():
            handle["active"] = False

        handle["cancel"] = cancel
        return cancel

    underlying = entity.underlying_entities[0]
    with patch("custom_components.versatile_thermostat.cycle_scheduler.async_call_later", side_effect=register_timer), \
        patch.object(entity, "incremente_energy", wraps=entity.incremente_energy) as credit, \
        patch.object(underlying, "turn_on", wraps=underlying.turn_on) as turn_on:
        assert entity._prop_algorithm.on_percent == 0.02
        await scheduler.start_cycle(VThermHvacMode_HEAT, entity._prop_algorithm.on_percent, force=True)
        for completed_cycles in range(1, 3):
            assert scheduler._active_on_time_sec == 0
            assert scheduler._active_off_time_sec == 300
            active = [handle for handle in handles if handle["active"]]
            assert len(active) == 1
            assert active[0]["cancel"] is scheduler._cycle_end_unsub
            assert active[0]["delay"] == 300
            assert scheduler._tick_unsub is None
            freezer.tick(timedelta(seconds=300))
            active[0]["active"] = False
            await active[0]["callback"](None)
            assert credit.call_count == completed_cycles
            expected_energy = completed_cycles * 3500 * 0.02 * 5 / 60
            assert entity._total_energy == pytest.approx(expected_energy)
            assert entity.total_energy == round(expected_energy, 2)
            turn_on.assert_not_awaited()
        await scheduler.cancel_cycle()
        assert not [handle for handle in handles if handle["active"]]


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_power_management_energy_over_switch(hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager):
    """Test the Power management energy mesurement"""

    for switch_id in ["mock_switch1", "mock_switch2"]:
        switch = MockSwitch(hass, switch_id, switch_id + "_name")
        await register_mock_entity(hass, switch, SWITCH_DOMAIN)

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch1", "switch.mock_switch2"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_POWER_UNIT: POWER_UNIT_WATT,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname", temps
    )
    assert entity

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    assert entity.total_energy == 0
    assert entity.nb_underlying_entities == 2

    await wait_for_local_condition(lambda: entity.is_ready)

    # set temperature to 15 so that on_percent will be set
    with patch(
        "custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"
    ) as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off"
    ) as mock_heater_off:
        await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
        await entity.async_set_preset_mode(VThermPreset.BOOST)
        await send_temperature_change_event(entity, 15, datetime.now())

        await hass.async_block_till_done()

        assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.target_temperature == 19
        assert entity.current_temperature == 15
        assert tpi_algo.on_percent == 1

        assert entity.power_manager.device_power == 100.0

        assert mock_send_event.call_count == 2
        assert mock_heater_on.call_count == 2  # both switches turn on immediately at 100%
        assert mock_heater_off.call_count == 0

    with patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        entity.incremente_energy()
        assert entity.total_energy == round(100 * 5 / 60.0, 2)
        entity.incremente_energy()
        assert entity.total_energy == round(2 * 100 * 5 / 60.0, 2)

    scheduler = entity.cycle_scheduler
    assert scheduler.is_cycle_running
    with patch.object(entity, "incremente_energy", wraps=entity.incremente_energy) as mock_incremente_energy, patch.object(
        scheduler, "start_cycle", new_callable=AsyncMock
    ) as mock_start_cycle:
        await scheduler._on_master_cycle_end(None)

    mock_incremente_energy.assert_called_once()
    mock_start_cycle.assert_awaited_once_with(
        VThermHvacMode_HEAT,
        1,
        force=True,
        _from_cycle_end=True,
    )
    assert entity.total_energy == round(3 * 100 * 5 / 60.0, 2)

    # change temperature to a higher value
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        await send_temperature_change_event(entity, 18, datetime.now())
        assert tpi_algo.on_percent == 0.3
        assert entity.power_manager.mean_cycle_power == 30.0

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0

    with patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        entity.incremente_energy()
        assert round(entity.total_energy, 2) == round((3.0 + 0.3) * 100 * 5 / 60.0, 2)

        entity.incremente_energy()
        assert round(entity.total_energy, 2) == round((3.0 + 0.6) * 100 * 5 / 60.0, 2)

    # change temperature to a much higher value so that heater will be shut down
    with patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, patch(
        "custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on"
    ) as mock_heater_on, patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, patch(
        "custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active",
        new_callable=PropertyMock,
        return_value=True,
    ):
        await send_temperature_change_event(entity, 20, datetime.now())
        assert tpi_algo.on_percent == 0.0
        assert entity.power_manager.mean_cycle_power == 0.0

        assert mock_send_event.call_count == 0
        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count == 0

        entity.incremente_energy()
        # No change on energy
        assert round(entity.total_energy, 2) == round((3.0 + 0.6) * 100 * 5 / 60.0, 2)

        # Still no change
        entity.incremente_energy()
        assert round(entity.total_energy, 2) == round((3.0 + 0.6) * 100 * 5 / 60.0, 2)


async def test_power_management_energy_over_climate(
    hass: HomeAssistant, fake_temp_sensor: MockTemperatureSensor, fake_ext_temp_sensor: MockTemperatureSensor, fake_underlying_climate: MockClimate
):
    """Test the Power management for a over_climate thermostat"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    # Starts off
    fake_underlying_climate.set_hvac_mode(VThermHvacMode_OFF)
    fake_underlying_climate.set_hvac_action(HVACAction.OFF)

    # the_mock_underlying = MockClimate(hass=hass, unique_id="mock_climate", name="TheMockClimate")
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
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_POWER_UNIT: POWER_UNIT_WATT,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(hass, entry, "climate.theoverclimatemockname", temps)
    assert entity
    assert entity.is_over_climate

    assert entity.total_energy == 0
    assert entity.hvac_mode == VThermHvacMode_OFF
    assert entity.hvac_action == HVACAction.OFF

    now = datetime.now(tz=get_tz(hass))
    entity._set_now(now)

    # 1. Start heating
    now = now + timedelta(minutes=3)
    entity._set_now(now)

    await send_temperature_change_event(entity, 15, now)
    fake_temp_sensor.set_native_value(15)
    await hass.async_block_till_done()

    await entity.async_set_preset_mode(VThermPreset.BOOST)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await hass.async_block_till_done()

    await wait_for_local_condition(lambda: fake_underlying_climate.hvac_mode == VThermHvacMode_HEAT and fake_underlying_climate.hvac_action == HVACAction.HEATING)
    await wait_for_local_condition(lambda: entity.hvac_mode == VThermHvacMode_HEAT and entity.hvac_action == HVACAction.HEATING)

    # assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    # assert entity.hvac_action is HVACAction.OFF
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.target_temperature == 19
    assert entity.current_temperature == 15

    assert entity.power_manager.mean_cycle_power == 100.0  # fully active yet
    assert entity.is_device_active is True

    # We have the start event and not the end event
    assert entity._underlying_climate_mean_power_cycle == 100.0
    assert (entity._underlying_climate_start_hvac_action_date - now).total_seconds() < 1

    # 2. wait a few and increment energy
    now = now + timedelta(minutes=3)
    entity._set_now(now)
    entity.incremente_energy()
    assert entity.total_energy == 5  # Vtherm is heating 100 w x 3 min / 60
    assert entity._underlying_climate_start_hvac_action_date == now

    # 3. wait a few and send a climate_change event with HVACAction=IDLE (end of heating)
    now = now + timedelta(minutes=10)
    entity._set_now(now)
    fake_underlying_climate.set_hvac_action(HVACAction.IDLE)
    await send_climate_change_event(
        entity,
        new_hvac_mode=VThermHvacMode_HEAT,
        old_hvac_mode=VThermHvacMode_HEAT,
        new_hvac_action=HVACAction.IDLE,
        old_hvac_action=HVACAction.HEATING,
        date=now,
        underlying_entity_id="climate.mock_climate",
    )
    # We have the end event -> we should have some power and on_percent
    assert entity._underlying_climate_start_hvac_action_date is None

    # 3 minutes at 100 W
    assert entity.total_energy == round(5 + 100 * 10 / 60, 2)

    assert entity.is_device_active is False
    assert entity._underlying_climate_start_hvac_action_date is None

    # Test the re-increment
    entity.incremente_energy()
    assert entity.total_energy == round(5 + 100 * 10 / 60, 2)  # No change

    entity.remove_thermostat()


async def test_power_management_turn_off_while_shedding(hass: HomeAssistant, skip_hass_states_is_state, init_central_power_manager, fake_underlying_switch: MockSwitch):
    """Test the Power management and that we can turn off a Vtherm that
    is in overpowering state"""

    temps = {
        "eco": 17,
        "comfort": 18,
        "boost": 19,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            CONF_NAME: "TheOverSwitchMockName",
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_SWITCH,
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: True,
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.01,
            CONF_MINIMAL_ACTIVATION_DELAY: 30,
            CONF_MINIMAL_DEACTIVATION_DELAY: 0,
            CONF_SAFETY_DELAY_MIN: 5,
            CONF_SAFETY_MIN_ON_PERCENT: 0.3,
            CONF_DEVICE_POWER: 100,
            CONF_PRESET_POWER: 12,
        },
    )

    entity: ThermostatOverSwitch = await create_thermostat(hass, entry, "climate.theoverswitchmockname", temps)
    assert entity

    now: datetime = NowClass.get_now(hass)
    VersatileThermostatAPI.get_vtherm_api()._set_now(now)

    tpi_algo = entity._prop_algorithm
    assert tpi_algo

    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await entity.async_set_preset_mode(VThermPreset.BOOST)
    assert entity.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert entity.preset_mode == VThermPreset.BOOST
    assert entity.power_manager.overpowering_state is STATE_UNKNOWN
    assert entity.target_temperature == 19

    # make the heater heats
    await send_temperature_change_event(entity, 15, now)
    await send_ext_temperature_change_event(entity, 1, now)
    await hass.async_block_till_done()

    assert entity.power_percent > 0

    side_effects = SideEffects(
        {
            "sensor.the_power_sensor": State("sensor.the_power_sensor", 50),
            "sensor.the_max_power_sensor": State("sensor.the_max_power_sensor", 49),
        },
        State("unknown.entity_id", "unknown"),
    )

    # 1. Set VTherm to overpowering
    # Send power max mesurement too low and VThermHvacMode is on and device is active
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event"), \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active", new_callable=PropertyMock, return_value=True):
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await send_max_power_change_event(entity, 49, now)
        assert entity.power_manager.is_overpowering_detected is True
        # All configuration is complete and power is > power_max we switch to POWER preset
        assert entity.preset_mode == VThermPreset.POWER
        assert entity.power_manager.overpowering_state is STATE_ON
        assert entity.target_temperature == 12

        assert mock_heater_on.call_count == 0
        assert mock_heater_off.call_count >= 1 # should be 1 but is_device_active is patched to True so can be called twice

    # 2. Turn-off Vtherm
    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
        patch("custom_components.versatile_thermostat.base_thermostat.BaseThermostat.send_event") as mock_send_event, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_on") as mock_heater_on, \
        patch("custom_components.versatile_thermostat.underlyings.UnderlyingSwitch.turn_off") as mock_heater_off, \
        patch("custom_components.versatile_thermostat.thermostat_switch.ThermostatOverSwitch.is_device_active", new_callable=PropertyMock, return_value=True):
    # fmt: on
        now = now + timedelta(seconds=30)
        VersatileThermostatAPI.get_vtherm_api()._set_now(now)

        await entity.async_set_hvac_mode(VThermHvacMode_OFF)
        await wait_for_local_condition(lambda: entity.hvac_mode == VThermHvacMode_OFF)
        assert entity.hvac_mode == VThermHvacMode_OFF
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.is_overpowering_detected is False

        await VersatileThermostatAPI.get_vtherm_api().central_power_manager._do_immediate_shedding()
        await wait_for_local_condition(lambda: entity.power_manager.is_overpowering_detected is False)

        # VTherm is off and overpowering if off also
        assert entity.hvac_mode == VThermHvacMode_OFF
        assert entity.preset_mode == VThermPreset.BOOST
        assert entity.power_manager.is_overpowering_detected is False
        assert entity.power_manager.overpowering_state is STATE_OFF
        assert entity.target_temperature == 19

    entity.remove_thermostat()


async def test_power_management_over_climate_valve(
    hass: HomeAssistant, fake_temp_sensor: MockTemperatureSensor, fake_ext_temp_sensor: MockTemperatureSensor, fake_underlying_climate: MockClimate, fake_opening_degree: MockNumber
):
    """Test the power and energy calculation for over_climate_valve thermostat"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        version=2,
        minor_version=2,
        data={
            CONF_NAME: "TheOverClimateValveMockName",
            CONF_TEMP_SENSOR: "sensor.mock_temp_sensor",
            CONF_CYCLE_MIN: 5,
            CONF_DEVICE_POWER: 1,
            CONF_USE_MAIN_CENTRAL_CONFIG: False,
            CONF_USE_CENTRAL_MODE: False,
            CONF_THERMOSTAT_TYPE: CONF_THERMOSTAT_CLIMATE,
            CONF_EXTERNAL_TEMP_SENSOR: "sensor.mock_ext_temp_sensor",
            CONF_TEMP_MIN: 15,
            CONF_TEMP_MAX: 30,
            CONF_STEP_TEMPERATURE: 0.1,
            CONF_UNDERLYING_LIST: ["climate.mock_climate"],
            CONF_AC_MODE: False,
            CONF_AUTO_REGULATION_MODE: CONF_AUTO_REGULATION_VALVE,
            CONF_AUTO_REGULATION_DTEMP: 0.5,
            CONF_AUTO_REGULATION_PERIOD_MIN: 2,
            CONF_AUTO_FAN_MODE: CONF_AUTO_FAN_HIGH,
            CONF_AUTO_REGULATION_USE_DEVICE_TEMP: False,
            CONF_PROP_FUNCTION: PROPORTIONAL_FUNCTION_TPI,
            CONF_TPI_COEF_INT: 0.3,
            CONF_TPI_COEF_EXT: 0.1,
            CONF_OPENING_DEGREE_LIST: ["number.mock_opening_degree"],
            CONF_CLOSING_DEGREE_LIST: [],
            CONF_SYNC_ENTITY_LIST: [],
            CONF_SYNC_WITH_CALIBRATION: False,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: False,
        }
        | MOCK_DEFAULT_FEATURE_CONFIG
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )

    # mock_get_state will be called for each OPENING/CLOSING/OFFSET_CALIBRATION list
    fake_opening_degree.set_native_value(10)
    fake_opening_degree.set_min_value(0)
    fake_opening_degree.set_max_value(100)

    # 1. initialize the VTherm
    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)

    vtherm: ThermostatOverClimateValve = await create_thermostat(hass, entry, "climate.theoverclimatevalvemockname", temps=default_temperatures)

    assert vtherm
    vtherm._set_now(now)
    assert isinstance(vtherm, ThermostatOverClimateValve)

    assert vtherm.name == "TheOverClimateValveMockName"
    assert vtherm.is_over_climate is True
    assert vtherm.have_valve_regulation is True

    assert vtherm.hvac_action is HVACAction.OFF
    assert vtherm.vtherm_hvac_mode is VThermHvacMode_OFF

    assert vtherm.is_initialized is True

    assert vtherm.is_device_active is False
    assert vtherm.valve_open_percent == 0

    # the underlying set temperature call but no call to valve yet because VTherm is off
    await wait_for_local_condition(lambda: fake_opening_degree.native_value == 0)

    assert vtherm.nb_device_actives == 0

    assert vtherm.total_energy == 0.0
    assert vtherm.power_manager.mean_cycle_power == 0.0

    assert fake_underlying_climate.hvac_mode == VThermHvacMode_OFF
    assert fake_underlying_climate.hvac_action == HVACAction.OFF

    # 2. Turn on the VTherm and make heating
    now = now + timedelta(minutes=1)
    vtherm._set_now(now)

    fake_temp_sensor.set_native_value(18)
    fake_ext_temp_sensor.set_native_value(18)
    await hass.async_block_till_done()
    # await send_temperature_change_event(vtherm, 18, now, True)
    # await send_ext_temperature_change_event(vtherm, 18, now, True)
    await wait_for_local_condition(lambda: vtherm.current_temperature == 18 and vtherm.current_outdoor_temperature == 18)

    await vtherm.async_set_hvac_mode(VThermHvacMode_HEAT)
    await vtherm.async_set_preset_mode(VThermPreset.COMFORT)  # 19
    await wait_for_local_condition(lambda: vtherm.proportional_algorithm.on_percent == 0.4)  # 0.4 = (19-18)*0.3 + (19-18)*0.1

    await wait_for_local_condition(lambda: fake_opening_degree.native_value == 40)
    await wait_for_local_condition(lambda: vtherm._underlyings_valve_regulation[0].state_manager.get_state("number.mock_opening_degree").state == "40.0")

    assert vtherm.hvac_action is HVACAction.HEATING
    assert vtherm.vtherm_hvac_mode is VThermHvacMode_HEAT
    assert vtherm.total_energy == 0.0
    assert vtherm.power_manager.mean_cycle_power == 1000 * 0.4  # device_power(W) * on_percent

    await wait_for_local_condition(lambda: fake_underlying_climate.hvac_mode == HVACMode.HEAT, 5)
    await wait_for_local_condition(lambda: fake_underlying_climate.hvac_action == HVACAction.HEATING, 10)
    await wait_for_local_condition(lambda: vtherm._underlying_climate_start_hvac_action_date is not None)

    # 3. simulate a cycle that should calculate energy
    now = now + timedelta(minutes=5)
    vtherm._set_now(now)

    await vtherm.async_control_heating()
    assert vtherm.total_energy == 33.33  # 5 minutes (1/12 hour) at 0.4 power -> 0.4/12=0.0333 rounded to 0.03 in Wh
    assert vtherm.power_manager.mean_cycle_power == 1000 * 0.4  # device_power * on_percent

    # 4. limit the power by changing the room temperature closer to target
    now = now + timedelta(minutes=2)
    vtherm._set_now(now)
    fake_temp_sensor.set_native_value(18.5)
    # await send_temperature_change_event(vtherm, 18.5, now, True)
    await wait_for_local_condition(lambda: vtherm.proportional_algorithm.on_percent == 0.25) # 0.25 = (19-18.5)*0.3 + (19-18)*0.1

    # Simulate a cycle
    await vtherm.async_control_heating()
    assert vtherm.total_energy == 33.33 + 13.34  # 2 minutes (1/30 hour) at 0.25 power -> 0.25/30=0.0083 rounded to 0.01 in Wh
    assert vtherm.power_manager.mean_cycle_power == 1000 * 0.25  # device_power * on_percent

    # 5. Turn off the VTherm after 3 minutes of heating
    now = now + timedelta(minutes=3)
    vtherm._set_now(now)

    await vtherm.async_set_hvac_mode(VThermHvacMode_OFF)
    # Simulate the underlying climate starting heating
    # await send_climate_change_event(
    #     vtherm,
    #     new_hvac_mode=VThermHvacMode_OFF,
    #     old_hvac_mode=VThermHvacMode_HEAT,
    #     new_hvac_action=HVACAction.OFF,
    #     old_hvac_action=HVACAction.HEATING,
    #     date=now,
    #     underlying_entity_id="climate.mock_climate",
    # )

    await wait_for_local_condition(lambda: vtherm.proportional_algorithm.on_percent == 0.0)

    assert vtherm.total_energy == 59.17  # 0.03 + 0.02 + 0.01 in Wh
    assert vtherm.power_manager.mean_cycle_power == 0.0
    assert vtherm.valve_open_percent == 0

    vtherm.remove_thermostat()
