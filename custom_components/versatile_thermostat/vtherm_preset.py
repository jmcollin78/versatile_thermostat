""" A custom data class to manage specific presets for VTherm. """

from homeassistant.components.climate.const import PRESET_NONE, PRESET_BOOST, PRESET_ECO, PRESET_COMFORT, PRESET_ACTIVITY

# from .const import PRESET_SAFETY, PRESET_POWER, PRESET_FROST_PROTECTION

# Liste des presets valides (à adapter selon ton projet)
PRESET_POWER = "power"
PRESET_SAFETY = "security"
PRESET_FROST_PROTECTION = "frost"

PRESET_TEMP_SUFFIX = "_temp"
PRESET_AC_SUFFIX = "_ac"
PRESET_AWAY_SUFFIX = "_away"


# Constants for all VTherm presets
class VThermPreset(str):
    """The List of Preset used by VTherm"""

    NONE = PRESET_NONE
    FROST = PRESET_FROST_PROTECTION
    ECO = PRESET_ECO
    COMFORT = PRESET_COMFORT
    BOOST = PRESET_BOOST
    SAFETY = PRESET_SAFETY
    POWER = PRESET_POWER
    ACTIVITY = PRESET_ACTIVITY


class VThermPresetWithAC(str):
    """Supplementary preset for AC hvac mode"""

    ECO = VThermPreset.ECO + PRESET_AC_SUFFIX
    COMFORT = VThermPreset.COMFORT + PRESET_AC_SUFFIX
    BOOST = VThermPreset.BOOST + PRESET_AC_SUFFIX
    FROST = VThermPreset.FROST + PRESET_AC_SUFFIX


class VThermPresetWithAway(str):
    """The List of Preset of Away type used by VTherm"""

    FROST = VThermPreset.FROST + PRESET_AWAY_SUFFIX
    ECO = VThermPreset.ECO + PRESET_AWAY_SUFFIX
    COMFORT = VThermPreset.COMFORT + PRESET_AWAY_SUFFIX
    BOOST = VThermPreset.BOOST + PRESET_AWAY_SUFFIX


class VThermPresetWithACAway(str):
    """The List of Preset for Ac and Away used by VTherm"""

    FROST = VThermPreset.FROST + PRESET_AC_SUFFIX + PRESET_AWAY_SUFFIX
    ECO = VThermPreset.ECO + PRESET_AC_SUFFIX + PRESET_AWAY_SUFFIX
    COMFORT = VThermPreset.COMFORT + PRESET_AC_SUFFIX + PRESET_AWAY_SUFFIX
    BOOST = VThermPreset.BOOST + PRESET_AC_SUFFIX + PRESET_AWAY_SUFFIX


HIDDEN_PRESETS = [VThermPreset.POWER, VThermPreset.SAFETY]
