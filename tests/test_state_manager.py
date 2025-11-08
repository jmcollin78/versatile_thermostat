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

        # is_over_climate | requested_hvac_mode  | current_hvac_mode    | last_central_mode     | window_action         | is_safety_detected | safety_default_percent | is_window_detected | is_auto_stop_detected | expected_result | expected_hvac_mode | expected_hvac_off_reason
        # Window detected and window_action = FAN_ONLY but FAN_ONLY not supported -> mode OFF
        # Not tested cause FAN_ONLY is supported
        # (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_FAN_ONLY,   False,               0.0,                     True,                False,                  True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_WINDOW_DETECTION),
        # Safety detected with over_climate=False et safety_default_percent=10 AND window detected -> Safety has priority, mode HEAT
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   True,                0.1,                     True,                False,                  True,            VThermHvacMode_OFF,      HVAC_OFF_REASON_WINDOW_DETECTION),
        # Safety detected with over_climate=True AND window detected -> Safety has priority, mode OFF
        (True,              VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   True,                0.1,                     True,                False,                  True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_SAFETY),
        # Safety detected AND auto_start_stop detected -> Safety has priority
        (True,              VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   True,                0.1,                     False,               True,                   True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_SAFETY),
        # Window detected AND auto_start_stop detected -> Window has priority
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   False,               0.0,                     True,                True,                   True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_WINDOW_DETECTION),
        # Safety detected AND window detected AND auto_start_stop detected -> Safety has priority
        (True,              VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_AUTO,      CONF_WINDOW_TURN_OFF,   True,                0.1,                     True,                True,                   True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_SAFETY),
        # Central mode STOPPED has priority over all other conditions
        (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_STOPPED,   CONF_WINDOW_TURN_OFF,   True,                0.1,                     True,                True,                   True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_CENTRAL_MODE),
        # Not tested cause COOL is supported
        # last_central_mode is CENTRAL_MODE_COOL_ONLY but COOL mode not supported -> OFF
        # (False,             VThermHvacMode_HEAT,   VThermHvacMode_HEAT,   CENTRAL_MODE_COOL_ONLY, CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_CENTRAL_MODE),
        # last_central_mode is CENTRAL_MODE_HEAT_ONLY but HEAT mode not supported -> OFF
        # (False,             VThermHvacMode_COOL,   VThermHvacMode_COOL,   CENTRAL_MODE_HEAT_ONLY, CONF_WINDOW_TURN_OFF,   False,               0.0,                     False,               False,                  True,             VThermHvacMode_OFF,      HVAC_OFF_REASON_CENTRAL_MODE),
        # last_central_mode is CENTRAL_MODE_FROST_PROTECTION but FROST preset not supported -> OFF
        # (False,             VThermHvacMode_COOL,   VThermHvacMode_COOL,   CENTRAL_MODE_FROST_PROTECTION, CONF_WINDOW_TURN_OFF,   False,        0.0,                     False,               False,                  True,             VThermHvacMode_OFF,     None),
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


@pytest.mark.parametrize(
    "current_hvac_mode,requested_preset,current_preset,is_overpowering_detected,is_safety_detected,last_central_mode,expected_result,expected_preset",
    # fmt: off
    [
        # Normal case -> no change
        # current_hvac_mode | requested_preset  | current_preset   | is_overpowering_detected | is_safety_detected | last_central_mode          | expected_result | expected_preset
        (VThermHvacMode_HEAT, VThermPreset.ECO,   VThermPreset.ECO,  False,                     False,               CENTRAL_MODE_AUTO,           False,            VThermPreset.ECO),
        # Change preset -> change expected
        (VThermHvacMode_HEAT, VThermPreset.BOOST, VThermPreset.ECO,  False,                     False,               CENTRAL_MODE_AUTO,           True,             VThermPreset.BOOST),
        # Overpowering detected and hvac_mode != OFF -> preset POWER
        (VThermHvacMode_HEAT, VThermPreset.ECO,   VThermPreset.ECO,  True,                      False,               CENTRAL_MODE_AUTO,           True,             VThermPreset.POWER),
        # Overpowering detected but hvac_mode = OFF -> no change (preset stays requested)
        (VThermHvacMode_OFF,  VThermPreset.ECO,   VThermPreset.ECO,  True,                      False,               CENTRAL_MODE_AUTO,           False,            VThermPreset.ECO),
        # Safety detected and hvac_mode != OFF -> preset SAFETY
        (VThermHvacMode_HEAT, VThermPreset.ECO,   VThermPreset.ECO,  False,                     True,                CENTRAL_MODE_AUTO,           True,             VThermPreset.SAFETY),
        # Safety detected but hvac_mode = OFF -> no change (preset stays requested)
        (VThermHvacMode_OFF,  VThermPreset.ECO,   VThermPreset.ECO,  False,                     True,                CENTRAL_MODE_AUTO,           False,            VThermPreset.ECO),
        # Overpowering has priority over safety
        (VThermHvacMode_HEAT, VThermPreset.ECO,   VThermPreset.ECO,  True,                      True,                CENTRAL_MODE_AUTO,           True,             VThermPreset.POWER),
        # Central mode FROST_PROTECTION and hvac_mode = HEAT -> preset FROST
        (VThermHvacMode_HEAT, VThermPreset.ECO,   VThermPreset.ECO,  False,                     False,               CENTRAL_MODE_FROST_PROTECTION, True,           VThermPreset.FROST),
        # Central mode FROST_PROTECTION but hvac_mode != HEAT -> no FROST preset
        (VThermHvacMode_COOL, VThermPreset.ECO,   VThermPreset.ECO,  False,                     False,               CENTRAL_MODE_FROST_PROTECTION, False,          VThermPreset.ECO),
        # Central mode FROST_PROTECTION but hvac_mode = OFF -> no FROST preset
        (VThermHvacMode_OFF,  VThermPreset.ECO,   VThermPreset.ECO,  False,                     False,               CENTRAL_MODE_FROST_PROTECTION, False,          VThermPreset.ECO),
    ],
    # fmt: on
)
async def test_state_manager_calculate_current_preset(
    hass: HomeAssistant,
    current_hvac_mode: VThermHvacMode,
    requested_preset: VThermPreset,
    current_preset: VThermPreset,
    is_overpowering_detected: bool,
    is_safety_detected: bool,
    last_central_mode: str,
    expected_result: bool,
    expected_preset: VThermPreset,
) -> None:
    """Test the state manager's preset calculation with various parameters."""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).vtherm_hvac_mode = PropertyMock(return_value=current_hvac_mode)
    type(fake_vtherm).vtherm_preset_modes = PropertyMock(
        return_value=[VThermPreset.ECO, VThermPreset.COMFORT, VThermPreset.NONE, VThermPreset.FROST, VThermPreset.BOOST, VThermPreset.POWER, VThermPreset.SAFETY]
    )

    state_manager = StateManager()
    state_manager.requested_state.set_state(hvac_mode=VThermHvacMode_HEAT, preset=requested_preset, target_temperature=22)
    state_manager.current_state.set_state(hvac_mode=current_hvac_mode, preset=current_preset, target_temperature=22)
    state_manager.requested_state.reset_changed()
    state_manager.current_state.reset_changed()

    type(fake_vtherm).last_central_mode = PropertyMock(return_value=last_central_mode)

    # Mock power manager
    fake_vtherm.power_manager = MagicMock()
    type(fake_vtherm.power_manager).is_overpowering_detected = PropertyMock(return_value=is_overpowering_detected)

    # Mock safety manager
    fake_vtherm.safety_manager = MagicMock()
    type(fake_vtherm.safety_manager).is_safety_detected = PropertyMock(return_value=is_safety_detected)

    ret = await state_manager.calculate_current_preset(fake_vtherm)
    assert ret is expected_result
    assert state_manager.current_state.preset == expected_preset


@pytest.mark.parametrize(
    "current_preset,requested_temp,current_temp,is_window_detected,window_action,is_absence_detected,is_motion_detected,motion_preset,ac_mode,expected_result,expected_temp",
    # fmt: off
    [
        # Normal case -> no change (requested temp is used)
        # current_preset | requested_temp | current_temp | is_window_detected | window_action         | is_absence_detected | is_motion_detected | motion_preset      | ac_mode | expected_result | expected_temp
        (VThermPreset.ECO, 22.0,            20.0,          False,               CONF_WINDOW_TURN_OFF, False,                  False,               VThermPreset.ECO,   False,      True,             18.0),  # ECO temp
        # Window detected with FROST action -> use FROST temp
        (VThermPreset.ECO, 22.0,            20.0,          True,                CONF_WINDOW_FROST_TEMP, False,                False,               VThermPreset.ECO,   False,      True,             7.0),   # FROST temp
        # Window detected with ECO action -> use ECO temp
        (VThermPreset.ECO, 22.0,            20.0,          True,                CONF_WINDOW_ECO_TEMP, False,                  False,               VThermPreset.ECO,   False,      True,             18.0),  # ECO temp
        # Window detected with TURN_OFF action -> no temperature change from window
        (VThermPreset.ECO, 22.0,            20.0,          True,                CONF_WINDOW_TURN_OFF, False,                  False,               VThermPreset.ECO,   False,      True,             18.0),  # ECO temp
        # Absence detected -> use preset temperature (away mode)
        (VThermPreset.ECO, 22.0,            20.0,          False,               CONF_WINDOW_TURN_OFF, True,                   False,               VThermPreset.ECO,   False,      True,             16.0),  # ECO_AWAY temp
        # Motion detected with ACTIVITY preset -> use motion preset temp
        (VThermPreset.ACTIVITY, 22.0,       20.0,          False,               CONF_WINDOW_TURN_OFF, False,                  True,                VThermPreset.BOOST, False,      True,             23.0),  # Boost temp
        # Motion detected but not ACTIVITY preset -> no motion impact
        (VThermPreset.ECO, 22.0,            20.0,          False,               CONF_WINDOW_TURN_OFF, False,                  True,                VThermPreset.ECO,   False,      True,             18.0),  # ECO temp
        # No preset, use requested temp directly
        (VThermPreset.NONE, 22.0,           20.0,          False,               CONF_WINDOW_TURN_OFF, False,                  False,               None,               False,      True,             22.0),  # Requested temp
        # No preset, no requested temp, AC mode -> use max temp
        (VThermPreset.NONE, None,           20.0,          False,               CONF_WINDOW_TURN_OFF, False,                  False,               None,               True,       True,             35.0),  # Max temp (AC)
        # No preset, no requested temp, heating mode -> use min temp
        (VThermPreset.NONE, None,           20.0,          False,               CONF_WINDOW_TURN_OFF, False,                  False,               None,               False,      True,             7.0),   # Min temp
        # Window has priority over absence
        (VThermPreset.ECO, 22.0,            20.0,          True,                CONF_WINDOW_ECO_TEMP, True,                   False,               VThermPreset.ECO,   False,      True,             16.0),  # ECO temp away (window priority)
        # Window has priority over motion
        (VThermPreset.ACTIVITY, 22.0,       20.0,          True,                CONF_WINDOW_FROST_TEMP, False,                True,                VThermPreset.FROST, False,      True,             7.0),   # FROST temp (window priority)
        # Absence has priority over motion
        (VThermPreset.ACTIVITY, 22.0,       20.0,          False,               CONF_WINDOW_TURN_OFF, True,                   True,                VThermPreset.COMFORT,   False,  True,             16.1),  # COMFORT_AWAY temp
        # SAFETY preset -> use requested preset temp
        (VThermPreset.SAFETY, 22.0,         20.0,          False,               CONF_WINDOW_TURN_OFF, False,                  False,               VThermPreset.ECO,   False,      True,             18.0),  # ECO temp (hard coded in test as requested_preset)
        # No change case -> same temp
        (VThermPreset.ECO, 18.0,            18.0,          False,               CONF_WINDOW_TURN_OFF, False,                  False,               VThermPreset.ECO,   False,      False,            18.0),  # No change
    ],
    # fmt: on
)
async def test_state_manager_calculate_current_target_temperature(
    hass: HomeAssistant,
    current_preset: VThermPreset,
    requested_temp: float,
    current_temp: float,
    is_window_detected: bool,
    window_action: str,
    is_absence_detected: bool,
    is_motion_detected: bool,
    motion_preset: VThermPreset,
    ac_mode: bool,
    expected_result: bool,
    expected_temp: float,
) -> None:
    """Test the state manager's target temperature calculation with various parameters."""
    fake_vtherm = MagicMock(spec=BaseThermostat)
    type(fake_vtherm).name = PropertyMock(return_value="the name")
    type(fake_vtherm).vtherm_preset_mode = PropertyMock(return_value=current_preset)
    type(fake_vtherm).ac_mode = PropertyMock(return_value=ac_mode)
    type(fake_vtherm).min_temp = 7
    type(fake_vtherm).max_temp = 35

    # Mock find_preset_temp method with predefined temperatures
    def mock_find_preset_temp(preset):
        preset_temps = {
            VThermPreset.ECO: 18.0,
            VThermPreset.COMFORT: 21.0,
            VThermPreset.BOOST: 23.0,
            VThermPreset.FROST: 7.0,
        }
        preset_temps_away = {
            VThermPreset.ECO: 16.0,
            VThermPreset.COMFORT: 16.1,
            VThermPreset.BOOST: 16.2,
            VThermPreset.FROST: 7.0,  # doesn't exists normally but needed for test
        }

        if preset == VThermPreset.SAFETY:
            raise ValueError("Safety preset is not allowed")

        if is_absence_detected:
            return preset_temps_away.get(preset, 20.0)
        else:
            return preset_temps.get(preset, 20.0)

    fake_vtherm.find_preset_temp = MagicMock(side_effect=mock_find_preset_temp)

    # Mock is_preset_configured method
    fake_vtherm.is_preset_configured = MagicMock(return_value=True)

    state_manager = StateManager()
    state_manager.requested_state.set_state(hvac_mode=VThermHvacMode_HEAT, preset=VThermPreset.ECO, target_temperature=requested_temp)
    state_manager.current_state.set_state(hvac_mode=VThermHvacMode_HEAT, preset=current_preset, target_temperature=current_temp)
    state_manager.requested_state.reset_changed()
    state_manager.current_state.reset_changed()

    # Mock window manager
    fake_vtherm.window_manager = MagicMock()
    type(fake_vtherm.window_manager).is_window_detected = PropertyMock(return_value=is_window_detected)
    type(fake_vtherm.window_manager).window_action = PropertyMock(return_value=window_action)

    # Mock presence manager
    fake_vtherm.presence_manager = MagicMock()
    type(fake_vtherm.presence_manager).is_absence_detected = PropertyMock(return_value=is_absence_detected)

    # Mock motion manager
    fake_vtherm.motion_manager = MagicMock()
    type(fake_vtherm.motion_manager).is_motion_detected = PropertyMock(return_value=is_motion_detected)
    fake_vtherm.motion_manager.get_current_motion_preset = MagicMock(return_value=motion_preset)

    ret = await state_manager.calculate_current_target_temperature(fake_vtherm)
    assert ret is expected_result
    assert state_manager.current_state.target_temperature == expected_temp
