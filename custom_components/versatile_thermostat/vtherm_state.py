"""State container for Versatile Thermostat.

This lightweight data class is intended to group together the minimal
public state we may want to persist, serialize, expose via services
or exchange between managers (for example during algorithms decisions
or for debug tooling).

Attributes:
    hvac_mode: Current HVAC mode of the thermostat (e.g. 'heat', 'off', 'cool', 'sleep').
    target_temperature: The active target temperature (can be None when mode does not use a temperature, e.g. 'off').
    preset: The current preset name (e.g. 'eco', 'comfort', 'boost', 'away') or None if not in a preset.
"""
from __future__ import annotations

from typing import Optional, Any

from .vtherm_hvac_mode import VThermHvacMode
from .vtherm_preset import VThermPreset

class VthermState:
    """Simple state snapshot for a VTherm.

    The object is mutable; use set_state for a bulk update or assign
    attributes individually via properties. to_dict / from_dict help (de)serialization.
    """

    def __init__(self, hvac_mode: VThermHvacMode, target_temperature: Optional[float] = None, preset: Optional[VThermPreset] = None) -> None:
        self._hvac_mode: VThermHvacMode = hvac_mode
        self._target_temperature: Optional[float] = target_temperature
        self._preset: Optional[VThermPreset] = preset
        self._is_changed: bool = False

    def set_state(
        self,
        hvac_mode: Optional[VThermHvacMode] = None,
        target_temperature: Optional[float] = None,
        preset: Optional[VThermPreset] = None,
    ) -> None:
        """Update only the attributes provided (not None).

        Args:
            hvac_mode: New HVAC mode to set (if not None).
            target_temperature: New target temperature (if not None).
            preset: New preset (if not None).
        """
        if hvac_mode is not None:
            self.set_hvac_mode(hvac_mode)
        if target_temperature is not None:
            self.set_target_temperature(target_temperature)
        if preset is not None:
            self.set_preset(preset)

    def set_hvac_mode(self, hvac_mode: VThermHvacMode) -> None:
        """Set the HVAC mode only.

        Args:
            hvac_mode: New HVAC mode to set (e.g. 'heat', 'off', 'cool', 'sleep').
        """
        self._is_changed = self._is_changed or self._hvac_mode != hvac_mode
        self._hvac_mode = hvac_mode

    def set_target_temperature(self, target_temperature: Optional[float]) -> None:
        """Set the target temperature only.

        Args:
            target_temperature: New target temperature to set, or None.
        """
        self._is_changed = self._is_changed or self._target_temperature != target_temperature
        self._target_temperature = target_temperature

    def set_preset(self, preset: Optional[VThermPreset]) -> None:
        """Set the preset only.

        Args:
            preset: New preset name to set, or None.
        """
        self._is_changed = self._is_changed or self._preset != preset
        self._preset = preset

    @property
    def hvac_mode(self) -> VThermHvacMode:
        """Get or set the current HVAC mode."""
        return self._hvac_mode

    @property
    def target_temperature(self) -> Optional[float]:
        """Get or set the current target temperature."""
        return self._target_temperature

    @property
    def preset(self) -> Optional[VThermPreset]:
        """Get or set the current preset."""
        return self._preset

    @property
    def is_changed(self) -> bool:
        """Check if the state has changed."""
        return self._is_changed

    def reset_changed(self) -> None:
        """Reset the changed state."""
        self._is_changed = False

    def to_dict(self) -> dict[str, Any]:
        """Convert the state to a dictionary."""
        return {
            "hvac_mode": self._hvac_mode,
            "target_temperature": self._target_temperature,
            "preset": self._preset,
        }

    def __str__(self) -> str:
        """Return a human readable representation of the state."""
        return (
            f"VthermState("
            f"hvac_mode={self._hvac_mode}, "
            f"target_temperature={self._target_temperature}, "
            f"preset={self._preset}, "
            f"is_changed={self._is_changed})"
        )

    __repr__ = __str__