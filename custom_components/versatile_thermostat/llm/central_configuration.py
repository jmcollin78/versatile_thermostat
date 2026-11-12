"""Read-only, scoped central configuration snapshots for native LLM tools."""

import math
from collections.abc import Mapping

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.config_entries import ConfigEntryState

from ..const import CONF_THERMOSTAT_CENTRAL_CONFIG, CONF_THERMOSTAT_TYPE, DOMAIN
from .diagnostics import _target

# Deliberate projection, never a raw ConfigEntry dump. In particular, lock codes,
# arbitrary plugin data, boiler service strings and templates are not exported.
GROUP_FIELDS = {
    "main": (
        "external_temperature_sensor_entity_id",
        "temp_min",
        "temp_max",
        "step_temperature",
    ),
    "tpi": (
        "tpi_coef_int",
        "tpi_coef_ext",
        "minimal_activation_delay",
        "minimal_deactivation_delay",
        "tpi_threshold_low",
        "tpi_threshold_high",
        "auto_tpi_mode",
    ),
    "window": (
        "window_delay",
        "window_off_delay",
        "window_auto_open_threshold",
        "window_auto_close_threshold",
        "window_auto_max_duration",
        "window_action",
    ),
    "motion": ("motion_delay", "motion_off_delay", "motion_preset", "no_motion_preset"),
    "power": (
        "power_sensor_entity_id",
        "max_power_sensor_entity_id",
        "power_unit",
        "power_temp",
    ),
    "presence": ("presence_sensor_entity_id",),
    "presets": (),  # Live temperatures are Number entities, not ConfigEntry values.
    "advanced": (
        "safety_delay_min",
        "safety_min_on_percent",
        "safety_default_on_percent",
        "repair_incorrect_state",
        "manual_override_duration_min",
    ),
    "lock": ("lock_users", "lock_automations", "auto_relock_sec"),
}


class CentralConfigurationSnapshot:
    """Carry authorized targets, central entry and their observed configuration."""

    def __init__(self, hass, user, targets):
        self.hass = hass
        self.user = user
        self.targets = targets
        entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.data.get(CONF_THERMOSTAT_TYPE) == CONF_THERMOSTAT_CENTRAL_CONFIG
        ]
        # Match find_central_configuration's eligibility; do not equate a stored
        # disabled/failed entry with the central configuration used by VTherm.
        active = [
            entry
            for entry in entries
            if entry.disabled_by is None
            and entry.state
            not in (
                ConfigEntryState.FAILED_UNLOAD,
                ConfigEntryState.SETUP_ERROR,
                ConfigEntryState.MIGRATION_ERROR,
                ConfigEntryState.SETUP_RETRY,
            )
        ]
        self.ambiguous = len(active) > 1 or (not active and len(entries) > 1)
        self.entry = (
            None
            if self.ambiguous
            else (active[0] if active else next(iter(entries), None))
        )
        self.configured = bool(entries)
        self.active = None if self.ambiguous else bool(active)

    @classmethod
    async def async_create(cls, hass, context, entity_ids):
        """Read configuration only after checking current exposure and READ rights."""
        # A failed optional central read must not discard the ordinary diagnosis.
        try:
            return await cls._async_create(hass, context, entity_ids)
        except Exception:  # No private exception text in the public snapshot.
            return None

    @classmethod
    async def _async_create(cls, hass, context, entity_ids):
        auth_context = context.context
        if auth_context is None or auth_context.user_id is None:
            return None
        user = await hass.auth.async_get_user(auth_context.user_id)
        if user is None:
            return None
        targets = {}
        for entity_id in entity_ids:
            if not user.is_admin and not user.permissions.check_entity(
                entity_id, POLICY_READ
            ):
                continue
            target, error = _target(hass, context, entity_id)
            if not error and target is not None:
                targets[entity_id] = target[3]
        return cls(hass, user, targets) if targets else None

    @staticmethod
    def unavailable():
        """Unknown is distinct from confirmed absence; disclose no entry data."""
        return {
            "status": "unavailable",
            "configured": None,
            "reason": "central_context_unavailable",
        }

    @staticmethod
    def project(data, fields):
        """Copy only reviewed scalar fields, keeping missing data missing."""
        return {
            key: value
            for key in fields
            if key in data
            and (
                (value := data[key]) is None
                or type(value) in (str, bool, int)
                or (type(value) is float and math.isfinite(value))
            )
        }

    def thermostat(self, entity_id, *, detail=False):
        """Report runtime flags, separately from mode and boiler participation."""
        if entity_id not in self.targets:
            return self.unavailable()
        entity = self.targets[entity_id]
        info = entity.entry_infos
        state = self.hass.states.get(entity_id)
        attributes = state.attributes
        configuration = attributes.get("configuration", {})
        specific = attributes.get("specific_states", {})
        inheritance = {
            group: info.get(f"use_{group}_central_config", False) is True
            for group in GROUP_FIELDS
        }
        result = {
            "inheritance": inheritance,
            "uses_central_configuration": (
                bool(self.active and any(inheritance.values()))
                if self.active is not None
                else None
            ),
            "is_controlled_by_central_mode": configuration.get(
                "is_controlled_by_central_mode"
            ),
            "last_central_mode": specific.get("last_central_mode"),
            "is_used_by_central_boiler": configuration.get("is_used_by_central_boiler"),
            "source": "loaded_thermostat.entry_infos",
        }
        if detail:
            result["effective_settings"] = {
                group: self.project(info, fields)
                for group, fields in GROUP_FIELDS.items()
                if inheritance[group]
            }
            if inheritance["presets"]:
                presets = attributes.get("preset_temperatures", {})
                result["effective_preset_temperatures"] = (
                    self.project(
                        presets,
                        (
                            "frost_temp",
                            "eco_temp",
                            "comfort_temp",
                            "boost_temp",
                            "frost_away_temp",
                            "eco_away_temp",
                            "comfort_away_temp",
                            "boost_away_temp",
                            "eco_cool_temp",
                            "comfort_cool_temp",
                            "boost_cool_temp",
                            "eco_cool_away_temp",
                            "comfort_cool_away_temp",
                            "boost_cool_away_temp",
                        ),
                    )
                    if isinstance(presets, Mapping)
                    else {}
                )
        return result

    def as_dict(self, entity_id=None):
        """Central settings: admins see reviewed groups, other users only inherited groups."""
        target_ids = [entity_id] if entity_id is not None else list(self.targets)
        groups = (
            set(GROUP_FIELDS)
            if self.user.is_admin
            else {
                group
                for target_id in target_ids
                if target_id in self.targets
                for group, inherited in self.thermostat(target_id)[
                    "inheritance"
                ].items()
                if inherited
            }
        )
        result = {
            "status": "ambiguous" if self.ambiguous else "success",
            "configured": self.configured,
            "active": self.active,
            "config_entry_id": self.entry.entry_id if self.entry else None,
            "name": (
                self.project(self.entry.data, ("name",)).get("name")
                if self.entry
                else None
            ),
            "features": (
                self.project(
                    self.entry.data,
                    (
                        "use_window_feature",
                        "use_motion_feature",
                        "use_power_feature",
                        "use_presence_feature",
                        "use_central_boiler_feature",
                    ),
                )
                if self.entry and self.user.is_admin
                else {}
            ),
            "boiler_settings": (
                self.project(
                    self.entry.data,
                    (
                        "central_boiler_activation_delay_sec",
                        "keep_alive_boiler_delay_sec",
                    ),
                )
                if self.entry and self.user.is_admin
                else {}
            ),
            "settings_scope": (
                "reviewed_fields" if self.user.is_admin else "inherited_groups_only"
            ),
            "settings": (
                {
                    group: self.project(self.entry.data, GROUP_FIELDS[group])
                    for group in GROUP_FIELDS
                    if group in groups
                }
                if self.entry
                else {}
            ),
            "source": "central_config_entry.data",
            "note": "Configured central values and loaded effective values can differ during reload. Preset temperatures come from the thermostat state; central and effective power units may differ. No raw configuration, secrets, service strings or templates are exported.",
        }
        if entity_id is not None:
            result["thermostat"] = self.thermostat(entity_id, detail=True)
        return result
