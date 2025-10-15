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

    ECO_AC = VThermPreset.ECO + PRESET_AC_SUFFIX
    COMFORT_AC = VThermPreset.COMFORT + PRESET_AC_SUFFIX
    BOOST_AC = VThermPreset.BOOST + PRESET_AC_SUFFIX


class VThermPresetAway(str):
    """The List of Preset used by VTherm"""

    FROST = PRESET_FROST_PROTECTION + PRESET_AWAY_SUFFIX
    ECO = PRESET_ECO + PRESET_AWAY_SUFFIX
    COMFORT = PRESET_COMFORT + PRESET_AWAY_SUFFIX
    BOOST = PRESET_BOOST + PRESET_AWAY_SUFFIX


HIDDEN_PRESETS = [VThermPreset.POWER, VThermPreset.SAFETY]
