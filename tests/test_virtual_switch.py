""" Test of virtual switch """

# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, line-too-long

from unittest.mock import patch, MagicMock, PropertyMock
import pytest

from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.versatile_thermostat.underlyings import UnderlyingSwitch
from custom_components.versatile_thermostat.thermostat_switch import ThermostatOverSwitch
from .commons import *


@pytest.mark.parametrize(
    "is_inversed, vswitch_on_command, vswitch_off_command, expected_command_on, expected_data_on, expected_state_on, expected_command_off, expected_data_off, expected_state_off, is_ok",
    [
        # Select (with stripping - trim)
        (
            False,
            " select_option/option:comfort ",
            "  select_option/option:frost      ",
            "select_option",
            {"entity_id": "switch.test", "option": "comfort"},
            VThermPreset.COMFORT,
            "select_option",
            {"entity_id": "switch.test", "option": "frost"},
            VThermPreset.FROST,
            True,
        ),
        # Inversed Select
        (
            True,
            "select_option/option:comfort",
            "select_option/option:eco",
            "select_option",
            {"entity_id": "switch.test", "option": "eco"},
            VThermPreset.ECO,
            "select_option",
            {"entity_id": "switch.test", "option": "comfort"},
            VThermPreset.COMFORT,
            True,
        ),
        # switch
        (False, "turn_on", "turn_off", "turn_on", {"entity_id": "switch.test"}, STATE_ON, "turn_off", {"entity_id": "switch.test"}, STATE_OFF, True),
        # inversed switch
        (True, "turn_on", "turn_off", "turn_off", {"entity_id": "switch.test"}, STATE_OFF, "turn_on", {"entity_id": "switch.test"}, STATE_ON, True),
        # Climate
        (
            False,
            "set_hvac_mode/hvac_mode:heat",
            "set_hvac_mode/hvac_mode:off",
            "set_hvac_mode",
            {"entity_id": "switch.test", "hvac_mode": "heat"},
            VThermHvacMode.HEAT,
            "set_hvac_mode",
            {"entity_id": "switch.test", "hvac_mode": "off"},
            VThermHvacMode.OFF,
            True,
        ),
        # Inversed Climate
        (
            True,
            "set_hvac_mode/hvac_mode:heat",
            "set_hvac_mode/hvac_mode:off",
            "set_hvac_mode",
            {"entity_id": "switch.test", "hvac_mode": "off"},
            VThermHvacMode.OFF,
            "set_hvac_mode",
            {"entity_id": "switch.test", "hvac_mode": "heat"},
            VThermHvacMode.HEAT,
            True,
        ),
        # Inversed switch without command personnalisations
        (
            True,
            None,
            None,
            "turn_off",
            {"entity_id": "switch.test"},
            STATE_OFF,
            "turn_on",
            {"entity_id": "switch.test"},
            STATE_ON,
            True,
        ),
        # Error cases invalid command
        (
            False,
            "select_ option/option:comfort",  # whitespace
            "select_option/option:frost",
            "select_option",
            {"entity_id": "switch.test", "option": "comfort"},
            VThermPreset.COMFORT,
            "select_option",
            {"entity_id": "switch.test", "option": "frost"},
            VThermPreset.FROST,
            False,
        ),
        (
            False,
            "select_option/option comfort",  # whitespace
            "select_option/option:frost",
            "select_option",
            {"entity_id": "switch.test", "option": "comfort"},
            VThermPreset.COMFORT,
            "select_option",
            {"entity_id": "switch.test", "option": "frost"},
            VThermPreset.FROST,
            False,
        ),
        (
            False,
            "select_option/option:com fort",  # whitespace
            "select_option/option:frost",
            "select_option",
            {"entity_id": "switch.test", "option": "comfort"},
            VThermPreset.COMFORT,
            "select_option",
            {"entity_id": "switch.test", "option": "frost"},
            VThermPreset.FROST,
            False,
        ),
    ],
)
async def test_build_command(
    hass,
    is_inversed,
    vswitch_on_command,
    vswitch_off_command,
    expected_command_on,
    expected_data_on,
    expected_state_on,
    expected_command_off,
    expected_data_off,
    expected_state_off,
    is_ok,
):
    """Test the initialisation of a UnderlyingSwitch with some personnalisations commands"""

    vtherm = MagicMock(spec=ThermostatOverSwitch)
    type(vtherm).is_inversed = PropertyMock(return_value=is_inversed)

    assert vtherm.is_inversed == is_inversed

    try:
        under = UnderlyingSwitch(hass, vtherm, "switch.test", 0, 0, vswitch_on_command, vswitch_off_command)
    except ValueError as e:
        if is_ok:
            pytest.fail(f"Initialization failed with ValueError: {e}")
        else:
            return

    if not is_ok:
        pytest.fail("There should be a ValueError")
        return

    assert under.is_inversed == is_inversed

    assert under._on_command.get("command") == expected_command_on
    assert under._on_command.get("data") == expected_data_on
    assert under._on_command.get("state") == expected_state_on

    assert under._off_command.get("command") == expected_command_off
    assert under._off_command.get("data") == expected_data_off
    assert under._off_command.get("state") == expected_state_off

    # Calling turn-on
    # fmt: off
    with patch.object(under, "check_overpowering", return_value=True), \
         patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    #fmt: on
        await under.turn_on()
        mock_service_call.assert_called_once_with("switch", expected_command_on, expected_data_on)

    # Calling turn-off
    #fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    #fmt: on
        await under.turn_off()
        mock_service_call.assert_called_once_with("switch", expected_command_off, expected_data_off)
