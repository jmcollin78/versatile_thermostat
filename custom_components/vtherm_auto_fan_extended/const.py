"""Constants for the vtherm_auto_fan_extended integration."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Integration identity
# ---------------------------------------------------------------------------

DOMAIN = "vtherm_auto_fan_extended"
NAME = "Versatile Thermostat Auto Fan"

#: Name used to register the feature manager factory in VThermAPI.
FEATURE_MANAGER_AUTO_FAN = "auto_fan"

# ---------------------------------------------------------------------------
# VTherm core keys (mirrored here to keep the plugin decoupled from the core)
# ---------------------------------------------------------------------------

#: Key holding the thermostat type in a VTherm config entry.
CONF_THERMOSTAT_TYPE = "thermostat_type"

#: Value of ``CONF_THERMOSTAT_TYPE`` for an over_climate thermostat.
CONF_THERMOSTAT_CLIMATE = "thermostat_over_climate"

# ---------------------------------------------------------------------------
# Config entry keys
# ---------------------------------------------------------------------------

#: Unique ID of the target VTherm.
CONF_TARGET_VTHERM = "target_vtherm_unique_id"

#: Regular-expression patterns excluding fan_modes from threshold creation.
CONF_EXCLUSION_PATTERNS = "exclusion_patterns"

# ---------------------------------------------------------------------------
# VTherm HVAC mode values (mirrored from the core)
# ---------------------------------------------------------------------------

VTHERM_HVAC_MODE_OFF = "off"
VTHERM_HVAC_MODE_HEAT = "heat"
VTHERM_HVAC_MODE_COOL = "cool"

# ---------------------------------------------------------------------------
# Threshold-based auto fan model
# ---------------------------------------------------------------------------

#: A threshold of 0 means the fan_mode does not participate in the auto fan.
THRESHOLD_DISABLED = 0.0

#: Number entity bounds (temperature gap).
THRESHOLD_MIN = 0.0
THRESHOLD_MAX = 10.0
THRESHOLD_STEP = 0.1

#: Default threshold repartition bounds, by temperature unit.
DEFAULT_THRESHOLD_START_CELSIUS = 1.0
DEFAULT_THRESHOLD_END_CELSIUS = 3.0
DEFAULT_THRESHOLD_START_FAHRENHEIT = 2.0
DEFAULT_THRESHOLD_END_FAHRENHEIT = 6.0

#: Fan modes that never participate as an activation speed are detected with
#: regular-expression patterns matched with ``re.fullmatch`` (case-insensitive).
#: A fixed string matches only that exact fan_mode; use wildcards for a partial
#: match (e.g. ``.*auto.*`` catches ``auto``, ``auto_low``, ``3d_auto``). This
#: list is the default value of the ``exclusion_patterns`` config option and can
#: be edited by the user.
DEFAULT_EXCLUSION_PATTERNS = [
    r".*auto.*",
    "off", "none", "on",
    "sleep", "night",
    "focus", "diffuse",
    "dry_fan", "circulate", "fresh_air",
    "schedule", "programmed",
]

#: Priority order used to pick a default rest fan_mode.
REST_MODE_PRIORITY = ["sleep", "quiet", "silent", "auto", "min", "minimum", "off"]

#: Most exhaustive list of known fan_modes, useful for detection and tests.
EXTRA_FAN_MODES = [
    # Standard HA
    "off", "auto", "low", "medium", "high", "top", "focus", "diffuse",
    # Silent / Night
    "quiet", "silent", "sleep", "night", "min", "minimum",
    # Boost
    "turbo", "powerful", "strong", "jet", "max", "maximum", "boost",
    # Comfort & varied
    "breeze", "natural", "wind", "eco", "econo", "3d", "3d_auto",
    # Air purifiers & HRV
    "favorite", "custom", "circulate", "fresh_air", "auto_clean", "dry_fan",
    # US / continuous thermostats
    "on", "schedule", "programmed",
    # Aliases & raw levels
    "middle", "mid", "lowest", "highest",
    "1", "2", "3", "4", "5", "6", "7",
]

# ---------------------------------------------------------------------------
# Attributes
# ---------------------------------------------------------------------------

#: Top-level attribute section exposed by the manager (recorder can only
#: filter top-level keys, so all auto-fan attributes live under this section).
ATTR_AUTO_FAN_SECTION = "auto_fan"

# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

#: Platform sub-keys used inside the shared add_entities registry.
PLATFORM_NUMBER = "number"
PLATFORM_SELECT = "select"
PLATFORM_SWITCH = "switch"
PLATFORM_SENSOR = "sensor"

#: Default state of the auto fan enable switch on first creation.
DEFAULT_AUTO_FAN_ENABLED = True

#: Entity unique_id / object_id building blocks.
ENTITY_THRESHOLD_PREFIX = "fan_mode_threshold"
ENTITY_REST_MODE_SUFFIX = "auto_fan_rest_mode"
ENTITY_ENABLE_SUFFIX = "auto_fan_enable"
ENTITY_CURRENT_FAN_MODE_SUFFIX = "auto_fan_current_fan_mode"

# ---------------------------------------------------------------------------
# Internal data keys (hass.data[DOMAIN])
# ---------------------------------------------------------------------------

DATA_FACTORY_REGISTERED = "factory_registered"

#: Registry of live AutoFanFeatureManager instances keyed by VTherm unique_id.
DATA_MANAGERS = "managers"

#: Registry of async_add_entities callbacks keyed by VTherm unique_id then by
#: platform, so the manager can create its entities dynamically once the
#: underlying fan_modes are known.
DATA_ADD_ENTITIES = "add_entities"

#: Registry of live entities keyed by VTherm unique_id. Each bucket holds the
#: threshold ``number`` entities (by fan_mode), the rest-mode ``select`` and the
#: enable ``switch`` so the manager can read their values.
DATA_ENTITIES = "entities"
