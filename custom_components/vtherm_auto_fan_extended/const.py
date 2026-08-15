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

#: Unique ID of the target VTherm (absent for the global defaults entry).
CONF_TARGET_VTHERM = "target_vtherm_unique_id"

#: Selected auto fan level for a thermostat.
CONF_AUTO_FAN_MODE = "auto_fan_mode"

# ---------------------------------------------------------------------------
# Auto fan levels
# ---------------------------------------------------------------------------

CONF_AUTO_FAN_NONE = "auto_fan_none"
CONF_AUTO_FAN_LOW = "auto_fan_low"
CONF_AUTO_FAN_MEDIUM = "auto_fan_medium"
CONF_AUTO_FAN_HIGH = "auto_fan_high"
CONF_AUTO_FAN_TURBO = "auto_fan_turbo"

CONF_AUTO_FAN_MODES = [
    CONF_AUTO_FAN_NONE,
    CONF_AUTO_FAN_LOW,
    CONF_AUTO_FAN_MEDIUM,
    CONF_AUTO_FAN_HIGH,
    CONF_AUTO_FAN_TURBO,
]

# ---------------------------------------------------------------------------
# Business logic tuning
# ---------------------------------------------------------------------------

#: Temperature gap (°C) above which the auto fan is activated.
AUTO_FAN_DTEMP_THRESHOLD = 2

#: Fan modes considered as "deactivated" (weakest / silent modes).
AUTO_FAN_DEACTIVATED_MODES = ["mute", "auto", "low", "quiet", "1"]

# ---------------------------------------------------------------------------
# VTherm HVAC mode values (mirrored from the core)
# ---------------------------------------------------------------------------

VTHERM_HVAC_MODE_OFF = "off"
VTHERM_HVAC_MODE_HEAT = "heat"
VTHERM_HVAC_MODE_COOL = "cool"

# ---------------------------------------------------------------------------
# Default option values
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FAN_MODE = CONF_AUTO_FAN_HIGH

DEFAULT_OPTIONS: dict = {
    CONF_AUTO_FAN_MODE: DEFAULT_AUTO_FAN_MODE,
}

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

SERVICE_SET_AUTO_FAN_MODE = "set_auto_fan_mode"

#: Human friendly service values mapped to internal levels.
SERVICE_AUTO_FAN_LEVELS = {
    "None": CONF_AUTO_FAN_NONE,
    "Low": CONF_AUTO_FAN_LOW,
    "Medium": CONF_AUTO_FAN_MEDIUM,
    "High": CONF_AUTO_FAN_HIGH,
    "Turbo": CONF_AUTO_FAN_TURBO,
}

# ---------------------------------------------------------------------------
# Attributes
# ---------------------------------------------------------------------------

#: Top-level attribute section exposed by the manager (recorder can only
#: filter top-level keys, so all auto-fan attributes live under this section).
ATTR_AUTO_FAN_SECTION = "auto_fan"

# ---------------------------------------------------------------------------
# Internal data keys (hass.data[DOMAIN])
# ---------------------------------------------------------------------------

DATA_FACTORY_REGISTERED = "factory_registered"
DATA_SERVICES_REGISTERED = "services_registered"

#: Registry of live AutoFanFeatureManager instances keyed by VTherm unique_id.
DATA_MANAGERS = "managers"
