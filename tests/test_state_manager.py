# pylint: disable=unused-argument, line-too-long, protected-access, too-many-lines
""" Test the Window management """
import logging
from unittest.mock import patch, PropertyMock, AsyncMock, MagicMock

from homeassistant.components.climate import HVACMode

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.state_manager import StateManager
from custom_components.versatile_thermostat.vtherm_state import VThermState
from custom_components.versatile_thermostat.vtherm_hvac_mode import VThermHvacMode_OFF, VThermHvacMode_HEAT, VThermHvacMode_COOL
from custom_components.versatile_thermostat.vtherm_preset import VThermPreset

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


async def test_state_manager_create(
    hass: HomeAssistant,
):
    """Test the StateManager class direclty"""
    state_manager = StateManager()
    assert state_manager is not None
    assert state_manager.current_state == VThermState(hvac_mode=VThermHvacMode_OFF, preset=VThermPreset.NONE, target_temperature=None)
    assert state_manager.requested_state == VThermState(hvac_mode=VThermHvacMode_OFF, preset=VThermPreset.NONE, target_temperature=None)
    assert state_manager.current_state.is_changed is True
    assert state_manager.requested_state.is_changed is True

    assert state_manager.current_state.is_preset_changed is True
    assert state_manager.current_state.is_target_temperature_changed is True
    assert state_manager.current_state.is_hvac_mode_changed is True

    state_manager.current_state.reset_changed()
    assert state_manager.current_state.is_changed is False
    assert state_manager.current_state.is_preset_changed is False
    assert state_manager.current_state.is_target_temperature_changed is False
    assert state_manager.current_state.is_hvac_mode_changed is False

    state_manager.current_state.force_changed()
    assert state_manager.current_state.is_changed is True
    assert state_manager.current_state.is_preset_changed is True
    assert state_manager.current_state.is_target_temperature_changed is True
    assert state_manager.current_state.is_hvac_mode_changed is True

    state_manager.current_state.reset_changed()
    state_manager.current_state.set_hvac_mode(VThermHvacMode_HEAT)
    assert state_manager.current_state.is_changed is True
    assert state_manager.current_state.is_preset_changed is False
    assert state_manager.current_state.is_target_temperature_changed is False
    assert state_manager.current_state.is_hvac_mode_changed is True

    state_manager.current_state.reset_changed()
    state_manager.current_state.set_target_temperature(22)
    assert state_manager.current_state.is_changed is True
    assert state_manager.current_state.is_preset_changed is False
    assert state_manager.current_state.is_target_temperature_changed is True
    assert state_manager.current_state.is_hvac_mode_changed is False

    state_manager.current_state.reset_changed()
    state_manager.current_state.set_preset(VThermPreset.ECO)
    assert state_manager.current_state.is_changed is True
    assert state_manager.current_state.is_preset_changed is True
    assert state_manager.current_state.is_target_temperature_changed is False
    assert state_manager.current_state.is_hvac_mode_changed is False

    json = state_manager.current_state.to_dict()
    assert json == {
       "hvac_mode": str(VThermHvacMode_HEAT),
       "preset": str(VThermPreset.ECO),
       "target_temperature": 22,
    }

    json["hvac_mode"] = str(VThermHvacMode_COOL)
    json["preset"] = str(VThermPreset.BOOST)
    json["target_temperature"] = 24

    restored_state = VThermState.from_dict(json)
    assert restored_state.hvac_mode == VThermHvacMode_COOL
    assert restored_state.preset == VThermPreset.BOOST
    assert restored_state.target_temperature == 24

async def test_vtherm_state_save_and_restor_newfmt(hass: HomeAssistant) -> None:
    """Test saving and restoring the VTherm states with new format"""
    vtherm = BaseThermostat(hass, "unique_id", "name", {})

    # Simulate changing the state
    vtherm.current_state.set_hvac_mode(VThermHvacMode_HEAT)
    vtherm.current_state.set_preset(VThermPreset.ECO)
    vtherm.current_state.set_target_temperature(22)

    vtherm.requested_state.set_hvac_mode(VThermHvacMode_COOL)
    vtherm.requested_state.set_preset(VThermPreset.COMFORT)
    vtherm.requested_state.set_target_temperature(23)

    # Save the state using Home Assistant's state mechanism
    state_dict = {
        "current_state": vtherm.current_state.to_dict(),
        "requested_state": vtherm.requested_state.to_dict(),
        "preset_mode": str(vtherm.current_state.preset),
        "temperature": vtherm.current_state.target_temperature,
    }

    # Simulate what Home Assistant does - store extra state data
    vtherm_restored = BaseThermostat(hass, "unique_id", "name", {})
    mock_state = MagicMock()
    mock_state.state = HVACMode.OFF
    mock_state.attributes = state_dict
    with patch.object(vtherm_restored, 'async_get_last_state', return_value=mock_state):
        # Create a new thermostat instance to simulate restoration
        await vtherm_restored.get_my_previous_state()


    # Check that the current state has been restored
    assert vtherm_restored.current_state.hvac_mode == VThermHvacMode_HEAT
    assert vtherm_restored.current_state.preset == VThermPreset.ECO
    assert vtherm_restored.current_state.target_temperature == 22

    # Check that the requested state has been restored
    assert vtherm_restored.requested_state.hvac_mode == VThermHvacMode_COOL
    assert vtherm_restored.requested_state.preset == VThermPreset.COMFORT
    assert vtherm_restored.requested_state.target_temperature == 23

async def test_vtherm_state_save_and_restor_oldfmt(hass: HomeAssistant) -> None:
    """Test saving and restoring the VTherm states with old format (ie retrocompatibility)"""
    # Save the state using Home Assistant's state mechanism
    state_dict = {
        "preset_mode": "eco",
        "temperature": 22,
    }

    # Simulate what Home Assistant does - store extra state data
    vtherm_restored = BaseThermostat(hass, "unique_id", "name", {})
    mock_state = MagicMock()
    mock_state.attributes = state_dict
    mock_state.state = HVACMode.HEAT
    with patch.object(vtherm_restored, 'async_get_last_state', return_value=mock_state):
        # Create a new thermostat instance to simulate restoration
        await vtherm_restored.get_my_previous_state()

    # Check that the current state has been restored
    assert vtherm_restored.current_state.hvac_mode == VThermHvacMode_HEAT
    assert vtherm_restored.current_state.preset == VThermPreset.ECO
    assert vtherm_restored.current_state.target_temperature == 22

    # Check that the requested state has been restored
    assert vtherm_restored.requested_state.hvac_mode == VThermHvacMode_HEAT
    assert vtherm_restored.requested_state.preset == VThermPreset.ECO
    assert vtherm_restored.requested_state.target_temperature == 22


@pytest.mark.parametrize(
    "is_over_climate,requested_hvac_mode,current_hvac_mode,last_central_mode,window_action,is_safety_detected,safety_default_percent,is_window_detected,is_auto_stop_detected,expected_result, expected_hvac_mode,expected_hvac_off_reason",
    # fmt: off
    [
        # Normal case -> no change
        # is_over_climate | requested_hvac_mode  | current_hvac_mode    | last_central_mode     | window_action         | is_safety_detected | safety_default_percent | is_window_detected | is_auto_stop_detected | expected_result | expected_hvac_mode | expected_hvac_off_reason
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   False,               0.1,                     False,               False,                  False,            VThermHvacMode_HEAT,     None),
        # Safety detected with over_climate=False et safety_default_percent=0 -> mode OFF
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   True,                0.0,                     False,               False,                  True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_SAFETY),
        # Safety detected with over_climate=False et safety_default_percent=10 -> mode HEAT
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   True,                0.1,                     False,               False,                  False,            VThermHvacMode_HEAT,     None),
        # Safety detected with over_climate=True -> mode OFF
        (True,              VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   True,                0.1,                     False,               False,                  True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_SAFETY),
        # Window detected and window_action = OFF and hvac_mode is HEAT -> mode OFF
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   False,               0.0,                     True,                False,                  True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_WINDOW_DETECTION),
        # Window detected and window_action = FAN_ONLY and hvac_mode is HEAT -> mode COOL
        (False,             VThermHvacMode_COOL,   VThermHvacMode_COOL,   CENTRAL_MODE_AUTO,      CONF_WINDOW_FAN_ONLY,   False,               0.0,                     True,                False,                  True,             VThermHvacMode_FAN_ONLY, None),
        # auto_start_stop_manager detected and hvac_mode is HEAT -> mode OFF
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               True,                   True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_AUTO_START_STOP),
        # auto_start_stop_manager detected and hvac_mode is OFF -> mode OFF but no hvac_off_reason
        (False,             VThermHvacMode_OFF,    VThermHvacMode_OFF,    CENTRAL_MODE_AUTO,      CONF_WINDOW_FAN_ONLY,   False,               0.0,                     False,               True,                   False,            VThermHvacMode_OFF,      HVAC_OFF_REASON_MANUAL),
        # last_central_mode is CENTRAL_MODE_COOL_ONLY and we are not Cooling
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_COOL_ONLY, CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  True,             VThermHvacMode_COOL,     None),
        # last_central_mode is CENTRAL_MODE_COOL_ONLY and we are COOLing
        (False,             VThermHvacMode_COOL,   VThermHvacMode_COOL,   CENTRAL_MODE_COOL_ONLY, CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  False,            VThermHvacMode_COOL,     None),
        # last_central_mode is CENTRAL_MODE_COOL_ONLY and we are OFF
        (False,             VThermHvacMode_OFF,   VThermHvacMode_OFF,     CENTRAL_MODE_COOL_ONLY, CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  False,            VThermHvacMode_OFF,      HVAC_OFF_REASON_MANUAL),
        # last_central_mode is CENTRAL_MODE_HEAT_ONLY and we are not Heating
        (False,             VThermHvacMode_COOL,   VThermHvacMode_COOL,   CENTRAL_MODE_HEAT_ONLY, CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  True,             VThermHvacMode_HEAT,     None),
        # last_central_mode is CENTRAL_MODE_HEAT_ONLY and we are Heating
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_HEAT_ONLY, CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  False,            VThermHvacMode_HEAT,     None),
        # last_central_mode is CENTRAL_MODE_HEAT_ONLY and we are OFF
        (False,             VThermHvacMode_OFF,   VThermHvacMode_OFF,     CENTRAL_MODE_HEAT_ONLY, CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  False,            VThermHvacMode_OFF,      HVAC_OFF_REASON_MANUAL),
        # last_central_mode is CENTRAL_MODE_FROST_PROTECTION and we are COOLing
        (False,             VThermHvacMode_COOL,   VThermHvacMode_COOL,   CENTRAL_MODE_FROST_PROTECTION, CONF_WINDOW_TURN_OFF,   False,        0.0,                     False,               False,                  True,             VThermHvacMode_HEAT,     None),
        # last_central_mode is CENTRAL_MODE_FROST_PROTECTION and we are Heating
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_FROST_PROTECTION, CONF_WINDOW_TURN_OFF,   False,        0.0,                     False,               False,                  False,            VThermHvacMode_HEAT,     None),
        # last_central_mode is CENTRAL_MODE_FROST_PROTECTION and we are OFF
        (False,             VThermHvacMode_OFF,   VThermHvacMode_OFF,     CENTRAL_MODE_FROST_PROTECTION, CONF_WINDOW_TURN_OFF,   False,        0.0,                     False,               False,                  False,            VThermHvacMode_OFF,      HVAC_OFF_REASON_MANUAL),
        # last_central_mode is STOPPED and we are HEATING -> OFF
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_STOPPED,   CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_CENTRAL_MODE),
        # last_central_mode is STOPPED and we are OFF -> no change
        (False,             VThermHvacMode_OFF,   VThermHvacMode_OFF,     CENTRAL_MODE_STOPPED,   CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  False,            VThermHvacMode_OFF,      HVAC_OFF_REASON_CENTRAL_MODE),
        ],
    # fmt: on
)
async def test_state_manager_calculate_hvac_mode(
    hass: HomeAssistant,
    is_over_climate: bool,
    requested_hvac_mode: VThermHvacMode,
    current_hvac_mode: VThermHvacMode,
    last_central_mode: str,
    window_action: str,
    is_safety_detected: bool,
    safety_default_percent: float,
    is_window_detected: bool,
    is_auto_stop_detected: bool,
    expected_result: bool,
    expected_hvac_mode: VThermHvacMode,
    expected_hvac_off_reason: str,
) -> None:
    """Test the state manager's HVAC mode calculation with various parameters."""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).is_over_climate = PropertyMock(return_value=is_over_climate)
    type(fake_vtherm).vtherm_hvac_modes = PropertyMock(return_value=[VThermHvacMode_HEAT, VThermHvacMode_COOL, VThermHvacMode_OFF, VThermHvacMode_FAN_ONLY])
    type(fake_vtherm).vtherm_preset_modes = PropertyMock(return_value=[VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.NONE, VThermPreset.FROST, VThermPreset.BOOST])
    type(fake_vtherm).is_sleeping = PropertyMock(return_value=False)
    type(fake_vtherm).hvac_off_reason = PropertyMock(return_value=None)

    # Mock set_hvac_off_reason method
    fake_vtherm.set_hvac_off_reason = MagicMock()

    state_manager = StateManager()
    state_manager.requested_state.set_state(hvac_mode=requested_hvac_mode, preset=VThermPreset.ECO, target_temperature=22)
    state_manager.current_state.set_state(hvac_mode=current_hvac_mode, preset=VThermPreset.ECO, target_temperature=22)
    state_manager.requested_state.reset_changed()
    state_manager.current_state.reset_changed()

    type(fake_vtherm).last_central_mode = PropertyMock(return_value=last_central_mode)

    fake_vtherm.safety_manager = MagicMock()
    type(fake_vtherm.safety_manager).is_safety_detected = PropertyMock(return_value=is_safety_detected)
    type(fake_vtherm.safety_manager).safety_default_on_percent = PropertyMock(return_value=safety_default_percent)

    fake_vtherm.window_manager = MagicMock()
    type(fake_vtherm.window_manager).is_window_detected = PropertyMock(return_value=is_window_detected)
    type(fake_vtherm.window_manager).window_action = PropertyMock(return_value=window_action)

    fake_vtherm.auto_start_stop_manager = MagicMock()
    type(fake_vtherm.auto_start_stop_manager).is_auto_stop_detected = PropertyMock(return_value=is_auto_stop_detected)

    ret = await state_manager.calculate_current_hvac_mode(fake_vtherm)
    assert ret is expected_result

    assert state_manager.current_state.hvac_mode == expected_hvac_mode

    if expected_hvac_off_reason is not None:
        fake_vtherm.set_hvac_off_reason.assert_called_with(expected_hvac_off_reason)
    else:
        fake_vtherm.set_hvac_off_reason.assert_not_called()
