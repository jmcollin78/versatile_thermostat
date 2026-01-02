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

from typing import Any

from .vtherm_hvac_mode import VThermHvacMode
from .vtherm_preset import VThermPreset


class VThermState:
    """Simple state snapshot for a VTherm.

    The object is mutable; use set_state for a bulk update or assign
    attributes individually via properties. to_dict / from_dict help (de)serialization.
    """

    def __init__(self, hvac_mode: Any, target_temperature: float | None = None, preset: VThermPreset | None = None) -> None:
        if preset is not None and not isinstance(preset, str):
            raise ValueError(f"Invalid preset: {preset}. Should be an instance of VThermPreset.")

        self._hvac_mode: VThermHvacMode = hvac_mode if isinstance(hvac_mode, VThermHvacMode) else VThermHvacMode(str(hvac_mode))
        self._target_temperature: float | None = target_temperature
        self._preset: VThermPreset | None = preset
        self._is_hvac_mode_changed: bool = True
        self._is_target_temperature_changed: bool = True
        self._is_preset_changed: bool = True

    def set_state(
        self,
        hvac_mode: VThermHvacMode | None = None,
        target_temperature: float | None = None,
        preset: VThermPreset | None = None,
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
        if not isinstance(hvac_mode, VThermHvacMode):
            hvac_mode = VThermHvacMode(str(hvac_mode))

        self._is_hvac_mode_changed = self._is_hvac_mode_changed or self._hvac_mode != hvac_mode
        self._hvac_mode = hvac_mode

    def set_target_temperature(self, target_temperature: float | None) -> None:
        """Set the target temperature only.

        Args:
            target_temperature: New target temperature to set, or None.
        """
        self._is_target_temperature_changed = self._is_target_temperature_changed or self._target_temperature != target_temperature
        self._target_temperature = target_temperature

    def set_preset(self, preset: VThermPreset | None) -> None:
        """Set the preset only.

        Args:
            preset: New preset name to set, or None.
        """
        if preset is not None and not isinstance(preset, str):
            raise ValueError(f"Invalid preset: {preset}. Should be an instance of VThermPreset.")

        self._is_preset_changed = self._is_preset_changed or self._preset != preset
        self._preset = preset

    def force_changed(self) -> None:
        """Forcefully mark the state as changed."""
        self._is_hvac_mode_changed = True
        self._is_target_temperature_changed = True
        self._is_preset_changed = True

    @property
    def hvac_mode(self) -> VThermHvacMode:
        """Get or set the current HVAC mode."""
        return self._hvac_mode

    @property
    def target_temperature(self) -> float | None:
        """Get or set the current target temperature."""
        return self._target_temperature

    @property
    def preset(self) -> VThermPreset | None:
        """Get or set the current preset."""
        return self._preset

    @property
    def is_changed(self) -> bool:
        """Check if the state has changed."""
        return self._is_hvac_mode_changed or self._is_target_temperature_changed or self._is_preset_changed

    @property
    def is_hvac_mode_changed(self) -> bool:
        """Check if the HVAC mode has changed."""
        return self._is_hvac_mode_changed

    @property
    def is_target_temperature_changed(self) -> bool:
        """Check if the target temperature has changed."""
        return self._is_target_temperature_changed

    @property
    def is_preset_changed(self) -> bool:
        """Check if the preset has changed."""
        return self._is_preset_changed

    def reset_changed(self) -> None:
        """Reset the changed state."""
        self._is_hvac_mode_changed = False
        self._is_target_temperature_changed = False
        self._is_preset_changed = False

    def to_dict(self) -> dict[str, Any]:
        """Convert the state to a dictionary."""
        return {
            "hvac_mode": str(self._hvac_mode),
            "target_temperature": self._target_temperature,
            "preset": str(self._preset),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VThermState":
        """Create a VThermState from a dictionary."""
        hvac_mode = VThermHvacMode(data["hvac_mode"])
        target_temperature = data["target_temperature"]
        preset = VThermPreset(data["preset"]) if data["preset"] else None
        state = cls(hvac_mode, target_temperature, preset)
        return state

    def __str__(self) -> str:
        """Return a human readable representation of the state."""
        return f"VThermState(" f"hvac_mode={self._hvac_mode}, " f"target_temperature={self._target_temperature}, " f"preset={self._preset}, " f"is_changed={self.is_changed})"

    __repr__ = __str__

    def __eq__(self, other: object) -> bool:
        """Compare two VThermState instances for equality.

        Args:
            other: Another object to compare with.

        Returns:
            True if both states have the same hvac_mode, target_temperature, and preset.
        """
        if not isinstance(other, VThermState):
            return False

        return self._hvac_mode == other._hvac_mode and self._target_temperature == other._target_temperature and self._preset == other._preset

    def __ne__(self, other: object) -> bool:
        """Compare two VThermState instances for inequality."""
        return not self.__eq__(other)
