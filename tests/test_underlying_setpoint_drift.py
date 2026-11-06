# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

"""Test that an over_climate VTherm resends its regulated temperature when the underlying setpoint
has been changed outside of VTherm and the change is not followed"""

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.thermostat_climate import ThermostatOverClimate

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def _create_regulated_vtherm(hass: HomeAssistant, now: datetime, step: float = 0.1):
    """Create a regulated over_climate VTherm (medium regulation, dtemp=0.5, period_min=2) in HEAT
    and returns the VTherm, the mock underlying and the regulated temperature sent to it"""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverClimateMockName",
        unique_id="uniqueId",
        data=PARTIAL_CLIMATE_CONFIG,
    )

    fake_underlying_climate = await create_and_register_mock_climate(hass, "mock_climate", "MockClimateName", {}, step=step)

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    entity: ThermostatOverClimate = search_entity(hass, "climate.theoverclimatemockname", "climate")
    assert entity
    assert entity.is_regulated is True
    assert entity._follow_underlying_temp_change is False

    entity._set_now(now)
    await entity.async_set_hvac_mode(VThermHvacMode_HEAT)
    await send_temperature_change_event(entity, 15, now)
    await send_ext_temperature_change_event(entity, 10, now)
    # Setting the target temperature forces the regulation send
    await entity.async_set_temperature(temperature=17)
    await hass.async_block_till_done()

    under = entity.underlying_entity(0)
    sent = under.last_sent_temperature
    assert sent is not None
    assert fake_underlying_climate.target_temperature == sent

    return entity, fake_underlying_climate, sent


async def _change_setpoint_on_device(hass: HomeAssistant, fake_underlying_climate, temperature: float):
    """Simulate a setpoint changed on the device itself (local control, own schedule, restart)"""
    fake_underlying_climate._attr_target_temperature = temperature
    fake_underlying_climate.async_write_ha_state()
    await hass.async_block_till_done()


async def test_regulated_temperature_resent_after_underlying_setpoint_drift(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """The underlying setpoint is changed on the device. The next regulation cycle must resend the regulated temperature
    even if the regulated temperature itself did not change (dtemp < auto_regulation_dtemp)"""
    now: datetime = datetime.now(tz=get_tz(hass))
    entity, fake_underlying_climate, sent = await _create_regulated_vtherm(hass, now - timedelta(minutes=20))
    under = entity.underlying_entity(0)

    drifted = sent - 1.5
    await _change_setpoint_on_device(hass, fake_underlying_climate, drifted)
    assert under.underlying_target_temperature == drifted

    # Next cycle after auto_regulation_period_min, same room and outdoor temperatures
    entity._set_now(now - timedelta(minutes=15))
    await entity.async_control_heating()
    await hass.async_block_till_done()

    assert abs(under.last_sent_temperature - sent) < entity._auto_regulation_dtemp
    assert fake_underlying_climate.target_temperature == under.last_sent_temperature
    assert under.underlying_target_temperature != drifted

    entity.remove_thermostat()


@pytest.mark.parametrize("step", [0.5, 0.1])
async def test_underlying_setpoint_within_step_not_resent(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event, step):
    """A difference not greater than the underlying step (device rounding) is not a drift, including steps like 0.1 that are inexact in floating point"""
    now: datetime = datetime.now(tz=get_tz(hass))
    entity, fake_underlying_climate, sent = await _create_regulated_vtherm(hass, now - timedelta(minutes=20), step=step)
    under = entity.underlying_entity(0)

    await _change_setpoint_on_device(hass, fake_underlying_climate, sent - step)

    entity._set_now(now - timedelta(minutes=15))
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_temperature") as mock_set_temperature:
        await entity.async_control_heating()
        await hass.async_block_till_done()

    mock_set_temperature.assert_not_called()
    assert fake_underlying_climate.target_temperature == sent - step

    entity.remove_thermostat()


async def test_underlying_setpoint_drift_not_resent_before_confirmation(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """Just after a command, the underlying may not have confirmed it yet: this is not a drift"""
    now: datetime = datetime.now(tz=get_tz(hass))
    entity, fake_underlying_climate, sent = await _create_regulated_vtherm(hass, now - timedelta(minutes=20))
    under = entity.underlying_entity(0)

    await _change_setpoint_on_device(hass, fake_underlying_climate, sent - 1.5)

    entity._set_now(now - timedelta(minutes=15))
    under._last_command_sent_datetime = now - timedelta(minutes=15, seconds=1)
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_temperature") as mock_set_temperature:
        await entity.async_control_heating()
        await hass.async_block_till_done()

    mock_set_temperature.assert_not_called()

    entity.remove_thermostat()


async def test_underlying_setpoint_drift_not_resent_when_followed(hass: HomeAssistant, skip_hass_states_is_state, skip_send_event):
    """With follow_underlying_temp_change, the change on the device is handled by the tracking, not overwritten"""
    now: datetime = datetime.now(tz=get_tz(hass))
    entity, fake_underlying_climate, sent = await _create_regulated_vtherm(hass, now - timedelta(minutes=20))
    entity.set_follow_underlying_temp_change(True)

    entity._set_now(now - timedelta(minutes=15))
    with patch("custom_components.versatile_thermostat.underlyings.UnderlyingClimate.set_temperature") as mock_set_temperature:
        await _change_setpoint_on_device(hass, fake_underlying_climate, sent - 1.5)
        await entity.async_control_heating()
        await hass.async_block_till_done()

    mock_set_temperature.assert_not_called()

    entity.remove_thermostat()
