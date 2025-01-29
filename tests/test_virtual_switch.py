""" Test of virtual switch """

# pylint: disable=wildcard-import, unused-wildcard-import, protected-access

import pytest
from .commons import *
from unittest.mock import patch, call, MagicMock, PropertyMock

from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.versatile_thermostat.underlyings import UnderlyingSwitch
from custom_components.versatile_thermostat.thermostat_switch import ThermostatOverSwitch


@pytest.mark.parametrize(
    "is_inversed, vswitch_on_command, vswitch_off_command, expected_command_on, expected_data_on, expected_state_on, expected_command_off, expected_data_off, expected_state_off",
    [
        # Select
        (
            False,
            "select_option/option:comfort",
            "select_option/option:frost",
            "select_option",
            {"entity_id": "switch.test", "option": "comfort"},
            PRESET_COMFORT,
            "select_option",
            {"entity_id": "switch.test", "option": "frost"},
            PRESET_FROST_PROTECTION,
        ),
        # switch
        (False, "turn_on/:on", "turn_off/:off", "turn_on", {"entity_id": "switch.test", None: None}, STATE_ON, "turn_off", {"entity_id": "switch.test", None: None}, STATE_OFF),
    ],
)
def test_build_command(
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
):
    """Test the initialisation of a UnderlyingSwitch with some personnalisations commands"""

    vtherm = MagicMock(spec=ThermostatOverSwitch)
    type(vtherm).is_inversed = PropertyMock(return_value=is_inversed)

    assert vtherm.is_inversed == is_inversed
    under = UnderlyingSwitch(hass, vtherm, "switch.test", 0, 0, vswitch_on_command, vswitch_off_command)

    assert under.is_inversed == is_inversed

    assert under._on_command.get("command") == expected_command_on
    assert under._on_command.get("data") == expected_data_on
    assert under._on_command.get("state") == expected_state_on

    assert under._off_command.get("command") == expected_command_off
    assert under._off_command.get("data") == expected_data_off
    assert under._off_command.get("state") == expected_state_off
