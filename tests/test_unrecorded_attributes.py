# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

"""Test that the volatile custom attribute sections are excluded from the recorder history."""

from custom_components.versatile_thermostat.base_thermostat import BaseThermostat
from custom_components.versatile_thermostat.thermostat_climate import ThermostatOverClimate


# Section top-level keys shared by all VTherm types
COMMON_EXCLUDED_SECTIONS = {
    "configuration",
    "preset_temperatures",
    "specific_states",
    "presence_manager",
    "power_manager",
    "motion_manager",
    "window_manager",
    "safety_manager",
    "lock_manager",
    "timed_preset_manager",
    "heating_failure_detection_manager",
    "repair_incorrect_state_manager",
}


def test_base_thermostat_excludes_attribute_sections():
    """The recorder must skip every volatile custom attribute section on the base thermostat."""
    excluded = BaseThermostat._entity_component_unrecorded_attributes
    for section in COMMON_EXCLUDED_SECTIONS:
        assert section in excluded, f"Section '{section}' should be excluded from the recorder"


def test_over_climate_excludes_specific_sections():
    """The over_climate thermostat must also exclude its own sections."""
    excluded = ThermostatOverClimate._entity_component_unrecorded_attributes
    for section in COMMON_EXCLUDED_SECTIONS | {"vtherm_over_climate", "auto_start_stop_manager"}:
        assert section in excluded, f"Section '{section}' should be excluded from the recorder"


def test_recorded_semantic_sections_are_kept():
    """current_state / requested_state must stay recorded for history."""
    excluded = BaseThermostat._entity_component_unrecorded_attributes
    assert "current_state" not in excluded
    assert "requested_state" not in excluded
