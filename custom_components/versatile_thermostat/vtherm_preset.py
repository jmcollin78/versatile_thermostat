""" A custom data class to manage specific presets for VTherm. """

from .const import PRESET_SAFETY, PRESET_BOOST, PRESET_ECO, PRESET_COMFORT, PRESET_ACTIVITY, PRESET_POWER, PRESET_NONE, PRESET_FROST_PROTECTION, HIDDEN_PRESETS, VALID_PRESETS
# Liste des presets valides (à adapter selon ton projet)

class VThermPreset:
    """Data class to encapsulate a single preset value."""

    # Constants for all valid presets
    NONE = PRESET_NONE
    FROST = PRESET_FROST_PROTECTION
    ECO = PRESET_ECO
    COMFORT = PRESET_COMFORT
    BOOST = PRESET_BOOST
    SAFETY = PRESET_SAFETY
    POWER = PRESET_POWER
    ACTIVITY = PRESET_ACTIVITY

    def __init__(self, preset: str) -> None:
        self.preset = preset  # Utilise le setter pour valider

    @property
    def preset(self) -> str:
        """Get the current preset."""
        return self._preset

    @preset.setter
    def preset(self, value: str) -> None:
        """Set the preset, validating against allowed values.

        Args:
            value: New preset (str).

        Raises:
            ValueError: If value is not a valid preset.
        """
        if value not in VALID_PRESETS:
            raise ValueError(
                f"Invalid preset '{value}'. Must be one of: {sorted(VALID_PRESETS)}"
            )
        self._preset = value

    def is_hidden(self) -> bool:
        """Check if the preset is hidden."""
        return self._preset in HIDDEN_PRESETS

    def __eq__(self, other: object) -> bool:
        """Compare two VThermPreset objects for equality based on their preset."""
        if not isinstance(other, VThermPreset):
            return NotImplemented
        return self._preset == other._preset
