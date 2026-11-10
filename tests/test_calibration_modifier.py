# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines, redefined-outer-name, wildcard-import, unused-wildcard-import, invalid-name
"""Test the calibration offset modifier offered to the external feature managers: a plugin adjusts the offset an
over_climate thermostat writes to the calibration entity of its device."""

import logging
from datetime import datetime

from homeassistant.core import HomeAssistant

from vtherm_api import CalibrationOffsetRequest

from custom_components.versatile_thermostat.thermostat_climate import ThermostatOverClimate

from .commons import *
from .const import *
from .fake_plugin import FakePluginManager, FaultyConfiguredMixin, register_plugin
from .test_underlying_hooks import record_services

logging.getLogger().setLevel(logging.DEBUG)

CALIBRATION = "number.mock_offset_calibration"
CLIMATE = "climate.mock_climate"


class Modifier(FakePluginManager):
    """Records the requests and returns what the class says"""

    result = None

    def adjust_calibration_offset(self, request: CalibrationOffsetRequest):
        self.events.append(("offset", self.plugin_name, request))
        return self.compute(request)

    def compute(self, request):
        """The adjusted offset. None keeps the value"""
        return self.result


class InvertedSign(Modifier):
    """A device which reads the offset with the opposite sign: the plugin recomputes the offset from the raw data"""

    def compute(self, request):
        return request.local_temperature + request.current_offset - request.room_temperature


class PlusOne(Modifier):
    """Adds one to the proposed offset"""

    def compute(self, request):
        return request.offset + 1


class Times2(Modifier):
    """Doubles the proposed offset"""

    def compute(self, request):
        return request.offset * 2


class Raising(Modifier):
    """Raises"""

    def compute(self, request):
        raise RuntimeError("boom offset")


class FaultyPlusOne(FaultyConfiguredMixin, PlusOne):
    """is_configured raises"""


def entry(with_calibration: bool = True) -> MockConfigEntry:
    """An over_climate which synchronizes the temperature of its device"""
    return MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        version=2,
        minor_version=2,
        data={
            CONF_NAME: "TheOverClimateMockName",
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
            CONF_UNDERLYING_LIST: [CLIMATE],
            CONF_AC_MODE: False,
            CONF_SYNC_DEVICE_INTERNAL_TEMP: True,
            CONF_SYNC_WITH_CALIBRATION: with_calibration,
            CONF_SYNC_ENTITY_LIST: [CALIBRATION],
            CONF_USE_PRESENCE_FEATURE: False,
            CONF_USE_WINDOW_FEATURE: False,
            CONF_USE_MOTION_FEATURE: False,
            CONF_USE_POWER_FEATURE: False,
        }
        | MOCK_DEFAULT_CENTRAL_CONFIG
        | MOCK_ADVANCED_CONFIG,
    )


async def create_vtherm(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, with_calibration: bool = True, offset: float = 0, local_temp: float = 15, room_temp: float = 18):
    """Create the VTherm over a device which reads local_temp, with the calibration entity at offset. The plugins have to be registered before"""
    fake_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {})
    calibration = await create_and_register_mock_number(hass, "mock_offset_calibration", "MockOffsetCalibration", offset, -12, 12, 0.5)
    vtherm: ThermostatOverClimate = await create_thermostat(hass, entry(with_calibration), "climate.theoverclimatemockname")
    vtherm._set_now(datetime.now(tz=get_tz(hass)))
    fake_ext_temp_sensor.set_native_value(18)
    fake_climate.set_current_temperature(local_temp)
    fake_temp_sensor.set_native_value(room_temp)
    await hass.async_block_till_done()
    await wait_for_local_condition(lambda: vtherm.current_temperature == room_temp)
    # the automatic synchronizations of the creation are over: start again from a known state
    calibration.set_native_value(offset)
    await hass.async_block_till_done()
    return vtherm, fake_climate, calibration


async def synchronize(hass: HomeAssistant, vtherm, events: list) -> list:
    """Synchronize the device temperature. Returns the values written to the calibration entity"""
    events.clear()
    with record_services(events):
        await vtherm.synchronize_device_temperature()
        await hass.async_block_till_done()
    return [e[4]["value"] for e in events if e[0] == "service" and e[3] == CALIBRATION]


def requests(events: list) -> list[CalibrationOffsetRequest]:
    """The requests received by the managers"""
    return [e[2] for e in events if e[0] == "offset"]


async def test_no_manager_unchanged(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Without plugin the offset is room - (local - current_offset), clamped and rounded"""
    vtherm, _, _ = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)
    assert vtherm._external_managers == []
    events: list = []

    assert await synchronize(hass, vtherm, events) == [3.0]


async def test_request_content(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The request carries the offset of the core, the raw data of the device and the limits of the entity"""
    events = register_plugin(hass, Modifier, "modifier")
    vtherm, _, _ = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor, offset=2, local_temp=15)

    written = await synchronize(hass, vtherm, events)

    (request,) = requests(events)
    assert request.climate_entity_id == CLIMATE
    assert request.calibration_entity_id == CALIBRATION
    assert request.offset == 5.0  # 18 - (15 - 2)
    assert request.requested_offset == 5.0
    assert request.current_offset == 2.0
    assert request.local_temperature == 15
    assert request.room_temperature == 18
    assert request.min_offset == -12
    assert request.max_offset == 12
    assert request.step == 0.5
    # None keeps the value of the core
    assert written == [5.0]


async def test_called_only_in_calibration_mode(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Without calibration the room temperature is sent to the device: the plugin is not asked"""
    events = register_plugin(hass, Modifier, "modifier")
    vtherm, _, _ = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor, with_calibration=False)

    written = await synchronize(hass, vtherm, events)

    assert requests(events) == []
    # the room temperature, clamped to the maximum of the entity
    assert written == [12]


async def test_not_called_when_the_data_is_missing(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """No local temperature: no offset, no call"""
    events = register_plugin(hass, Modifier, "modifier")
    vtherm, fake_climate, _ = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)
    fake_climate.set_current_temperature(None)
    await hass.async_block_till_done()

    written = await synchronize(hass, vtherm, events)

    assert requests(events) == []
    assert written == []


async def test_inverted_sign(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A device with the opposite sign receives the offset recomputed by the plugin from current_offset"""
    events = register_plugin(hass, InvertedSign, "inverted")
    vtherm, fake_climate, calibration = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor, offset=0, local_temp=15)

    # the core would write +3, the device needs -3
    assert await synchronize(hass, vtherm, events) == [-3.0]
    assert requests(events)[0].offset == 3.0

    # the device applied -3 with the opposite sign: it now reads 18, and the offset is the right one
    calibration.set_native_value(-3)
    fake_climate.set_current_temperature(18)
    await hass.async_block_till_done()
    assert await synchronize(hass, vtherm, events) == []
    assert requests(events)[0].current_offset == -3.0


async def test_chain_order(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Each manager receives the value left by the previous one, in the order of registration, and None keeps the value"""
    events = register_plugin(hass, PlusOne, "a_plus")
    register_plugin(hass, Modifier, "b_none", events=events)
    register_plugin(hass, Times2, "c_times", events=events)
    vtherm, _, _ = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)

    written = await synchronize(hass, vtherm, events)

    assert [e[1] for e in events if e[0] == "offset"] == ["a_plus", "b_none", "c_times"]
    first, second, third = requests(events)
    assert (first.offset, second.offset, third.offset) == (3.0, 4.0, 4.0)
    assert first.requested_offset == second.requested_offset == third.requested_offset == 3.0
    assert written == [8.0]


async def test_clamp_and_round(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """The result is clamped to min..max and rounded to the step"""
    events = register_plugin(hass, Modifier, "modifier")
    vtherm, _, calibration = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)

    for result, expected in [(30, 12.0), (-20, -12.0), (1.26, 1.5), (1.24, 1.0), (-0.3, -0.5), (12, 12.0)]:
        Modifier.result = result
        calibration.set_native_value(0)
        await hass.async_block_till_done()
        assert await synchronize(hass, vtherm, events) == [expected], result
    Modifier.result = None


async def test_no_write_when_equal_to_the_current_offset(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """Nothing is written when the final offset is the current one, even if the core wanted to write"""
    events = register_plugin(hass, Modifier, "modifier")
    vtherm, _, _ = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor, offset=2)

    # the core wants 4, the plugin keeps 2
    Modifier.result = 2.0
    assert await synchronize(hass, vtherm, events) == []
    # the plugin gets to 2.2 which is rounded to the step 2.0
    Modifier.result = 2.2
    assert await synchronize(hass, vtherm, events) == []
    Modifier.result = None


async def test_exception_is_isolated(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A failing manager is logged, the next one receives the value it had"""
    events = register_plugin(hass, Raising, "a_raising")
    register_plugin(hass, PlusOne, "b_plus", events=events)
    vtherm, _, _ = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)
    caplog.clear()

    written = await synchronize(hass, vtherm, events)

    assert requests(events)[1].offset == 3.0
    assert written == [4.0]
    assert "boom offset" in caplog.text


async def test_invalid_values_are_ignored(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A result which is not a finite number is logged and ignored"""
    events = register_plugin(hass, Modifier, "modifier")
    vtherm, _, calibration = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)

    for invalid in (float("nan"), float("inf"), "2", True, [1]):
        Modifier.result = invalid
        calibration.set_native_value(0)
        await hass.async_block_till_done()
        caplog.clear()
        assert await synchronize(hass, vtherm, events) == [3.0], invalid
        assert "invalid calibration offset" in caplog.text
    Modifier.result = None


async def test_unconfigured_and_faulty_is_configured_are_isolated(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor, caplog):
    """A manager which is not configured, or whose is_configured raises, is not called"""
    events = register_plugin(hass, PlusOne, "a_unconfigured", configured=False)
    register_plugin(hass, FaultyPlusOne, "b_faulty", events=events)
    register_plugin(hass, Modifier, "c_good", events=events)
    vtherm, _, _ = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)
    caplog.clear()

    written = await synchronize(hass, vtherm, events)

    assert [e[1] for e in events if e[0] == "offset"] == ["c_good"]
    assert written == [3.0]
    assert "Error while reading is_configured" in caplog.text


async def test_manager_without_the_contract_is_not_called(hass: HomeAssistant, fake_temp_sensor, fake_ext_temp_sensor):
    """A manager which does not implement adjust_calibration_offset changes nothing"""
    events = register_plugin(hass, FakePluginManager, "plain")
    vtherm, _, _ = await create_vtherm(hass, fake_temp_sensor, fake_ext_temp_sensor)

    assert await synchronize(hass, vtherm, events) == [3.0]
