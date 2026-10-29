"""LLM/MCP tools for Versatile Thermostat.

Level 1:
- list VTherms
- get complete state
- diagnose a VTherm

Level 2A:
- set target temperature
- set preset mode
- set HVAC mode

The tools are exposed through Home Assistant's LLM API and can therefore be
published by Home Assistant's official MCP Server.

Read tools are marked read-only. Write tools are intentionally limited to the
standard Home Assistant climate services and only target VTherm entities exposed
to Assist.

Targeted at the Home Assistant LLM API available in October 2026.
"""

from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from typing import Any

import probatio

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.components.homeassistant import async_should_expose
from homeassistant.components.llm import LLMTools
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import llm

from .const import DOMAIN


READ_ONLY_ANNOTATIONS = llm.ToolAnnotations(
    read_only=True,
    destructive=False,
    idempotent=True,
    open_world=False,
)

WRITE_ANNOTATIONS = llm.ToolAnnotations(
    read_only=False,
    destructive=False,
    idempotent=True,
    open_world=False,
)

# Public VTherm documentation.
DOCS_FR = "https://www.versatile-thermostat.org/fr/"
DOCS_EN = "https://www.versatile-thermostat.org/en/"
REFERENCE_FR = "https://www.versatile-thermostat.org/fr/docs/reference/"
REFERENCE_EN = "https://www.versatile-thermostat.org/en/docs/reference/"
LOG_COLLECTOR_FR = (
    "https://www.versatile-thermostat.org/fr/docs/feature-logs-collector/"
)
LOG_COLLECTOR_EN = (
    "https://www.versatile-thermostat.org/en/docs/feature-logs-collector/"
)
LOG_ANALYZER = "https://www.versatile-thermostat.org/fr/debugger/"
OFFICIAL_REPOSITORY = "https://github.com/jmcollin78/versatile_thermostat"

# VTherm sections documented in the entity state attributes.
# Returning complete sections avoids duplicating the thermostat's internal
# decision logic in the LLM layer.
DIAGNOSTIC_SECTIONS = (
    "configuration",
    "current_state",
    "requested_state",
    "specific_states",
    "preset_temperatures",
    "presence_manager",
    "motion_manager",
    "power_manager",
    "window_manager",
    "safety_manager",
    "auto_start_stop_manager",
    "lock_manager",
    "heating_failure_detection",
    "vtherm_over_switch",
    "vtherm_over_climate",
    "vtherm_over_valve",
)


def _is_french(language: str | None) -> bool:
    """Return True when the request language is French."""
    return bool(language and language.lower().startswith("fr"))


def _support_resources(language: str | None) -> dict[str, Any]:
    """Return VTherm support resources in both French and English."""
    preferred_language = "fr" if _is_french(language) else "en"
    preferred_documentation = DOCS_FR if preferred_language == "fr" else DOCS_EN
    preferred_reference = REFERENCE_FR if preferred_language == "fr" else REFERENCE_EN
    preferred_log_collector = (
        LOG_COLLECTOR_FR if preferred_language == "fr" else LOG_COLLECTOR_EN
    )

    return {
        "preferred_language": preferred_language,
        "documentation": preferred_documentation,
        "reference": preferred_reference,
        "log_collector": preferred_log_collector,
        "documentation_fr": DOCS_FR,
        "documentation_en": DOCS_EN,
        "reference_fr": REFERENCE_FR,
        "reference_en": REFERENCE_EN,
        "log_collector_fr": LOG_COLLECTOR_FR,
        "log_collector_en": LOG_COLLECTOR_EN,
        "log_analyzer": LOG_ANALYZER,
        "official_repository": OFFICIAL_REPOSITORY,
        "log_download_action": "versatile_thermostat.download_logs",
        "guidance_fr": (
            "Pour un diagnostic complexe, consulter le site de documentation VTherm "
            "correspondant à la fonction concernée. Si l'état courant ne suffit "
            "pas, proposer l'export des logs avec versatile_thermostat.download_logs "
            "puis leur analyse avec l'analyseur de logs."
        ),
        "guidance_en": (
            "For complex troubleshooting, consult the VTherm documentation website "
            "for the feature involved. If the current state is not enough, suggest "
            "exporting logs with versatile_thermostat.download_logs and analyzing "
            "them with the log analyzer."
        ),
    }


def _json_safe(value: Any) -> Any:
    """Return a JSON-serializable representation of a Home Assistant value."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Enum):
        return _json_safe(value.value)

    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]

    return str(value)


def _section(attributes: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Return a nested VTherm state section, or an empty dict."""
    value = attributes.get(name)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return {}


def _first_value(attributes: Mapping[str, Any], *keys: str) -> Any:
    """Return the first non-None attribute value among keys."""
    for key in keys:
        if (value := attributes.get(key)) is not None:
            return value
    return None


def _target_minus_current(attributes: Mapping[str, Any]) -> float | None:
    """Return target minus current temperature when both are numeric."""
    current = attributes.get("current_temperature")
    target = attributes.get("temperature")

    if (
        isinstance(current, (int, float))
        and not isinstance(current, bool)
        and isinstance(target, (int, float))
        and not isinstance(target, bool)
    ):
        return round(float(target) - float(current), 3)

    return None


def _compact_state(state: State) -> dict[str, Any]:
    """Return a compact climate/VTherm state snapshot."""
    attributes = state.attributes
    specific_states = _section(attributes, "specific_states")
    configuration = _section(attributes, "configuration")

    return {
        "entity_id": state.entity_id,
        "name": _json_safe(attributes.get("friendly_name")),
        "hvac_mode": state.state,
        "hvac_action": _json_safe(attributes.get("hvac_action")),
        "preset_mode": _json_safe(attributes.get("preset_mode")),
        "current_temperature": _json_safe(attributes.get("current_temperature")),
        "target_temperature": _json_safe(attributes.get("temperature")),
        "target_minus_current": _target_minus_current(attributes),
        "min_temperature": _json_safe(
            _first_value(attributes, "min_temp", "temp_min")
        ),
        "max_temperature": _json_safe(
            _first_value(attributes, "max_temp", "temp_max")
        ),
        "target_temperature_step": _json_safe(attributes.get("target_temp_step")),
        "hvac_modes": _json_safe(attributes.get("hvac_modes", [])),
        "preset_modes": _json_safe(attributes.get("preset_modes", [])),
        "thermostat_type": _json_safe(
            _first_value(configuration, "thermostat_type", "type")
        ),
        "messages": _json_safe(specific_states.get("messages", [])),
    }


def _get_vtherm_entity_ids(
    hass: HomeAssistant,
    llm_context: llm.LLMContext,
) -> list[str]:
    """Return loaded VTherm climate entity IDs exposed to Assist."""
    entity_registry = er.async_get(hass)
    entity_ids: set[str] = set()

    for config_entry in hass.config_entries.async_entries(DOMAIN):
        for registry_entry in er.async_entries_for_config_entry(
            entity_registry,
            config_entry.entry_id,
        ):
            entity_id = registry_entry.entity_id

            if not entity_id.startswith(f"{CLIMATE_DOMAIN}."):
                continue

            if hass.states.get(entity_id) is None:
                continue

            if not async_should_expose(
                hass,
                llm_context.assistant,
                entity_id,
            ):
                continue

            entity_ids.add(entity_id)

    return sorted(entity_ids)


def _state_or_error(
    hass: HomeAssistant,
    entity_id: str,
) -> tuple[State | None, llm.ToolResult | None]:
    """Return a state or a standardized tool error."""
    state = hass.states.get(entity_id)

    if state is None:
        return None, llm.ToolResult(
            data={
                "error": "Versatile Thermostat entity not found or not loaded",
                "entity_id": entity_id,
            },
            error=True,
        )

    return state, None


async def _control_permission_error(
    hass: HomeAssistant,
    llm_context: llm.LLMContext,
    entity_id: str,
) -> llm.ToolResult | None:
    """Return an error if the authenticated user cannot control the entity.

    Write tools intentionally require an authenticated user context. This keeps
    tool calls attributable and lets Home Assistant permissions apply.
    """
    context = llm_context.context

    if context is None or context.user_id is None:
        return llm.ToolResult(
            data={
                "error": (
                    "An authenticated Home Assistant user context is required "
                    "for VTherm write tools."
                ),
                "entity_id": entity_id,
            },
            error=True,
        )

    user = await hass.auth.async_get_user(context.user_id)
    if user is None:
        return llm.ToolResult(
            data={
                "error": "Authenticated Home Assistant user was not found.",
                "entity_id": entity_id,
            },
            error=True,
        )

    if not user.is_admin and not user.permissions.check_entity(
        entity_id, POLICY_CONTROL
    ):
        return llm.ToolResult(
            data={
                "error": "User is not allowed to control this VTherm entity.",
                "entity_id": entity_id,
            },
            error=True,
        )

    return None


def _temperature_range(attributes: Mapping[str, Any]) -> tuple[float | None, float | None]:
    """Return the entity-specific target temperature range."""
    minimum = _first_value(attributes, "min_temp", "temp_min")
    maximum = _first_value(attributes, "max_temp", "temp_max")

    min_value = (
        float(minimum)
        if isinstance(minimum, (int, float)) and not isinstance(minimum, bool)
        else None
    )
    max_value = (
        float(maximum)
        if isinstance(maximum, (int, float)) and not isinstance(maximum, bool)
        else None
    )

    return min_value, max_value


def _write_result(
    *,
    action: str,
    requested: dict[str, Any],
    state: State | None,
) -> llm.ToolResult:
    """Return a consistent successful write result."""
    return llm.ToolResult(
        data={
            "success": True,
            "action": action,
            "requested": _json_safe(requested),
            "state_after_call": _compact_state(state) if state else None,
            "note": (
                "VTherm can subsequently adjust the effective state according to "
                "its configured rules (preset, central mode, window, power, safety, "
                "auto-start/stop, regulation, etc.)."
            ),
        }
    )


class ListVThermsTool(llm.Tool):
    """List Versatile Thermostat entities exposed to Assist."""

    name = f"{DOMAIN}__list_vtherms"
    title = "List VTherms / Lister les VTherm"
    description = (
        "EN: List Versatile Thermostat climate entities available to the assistant "
        "with a compact state summary. "
        "FR: Liste les entités climate Versatile Thermostat disponibles pour "
        "l'assistant avec un résumé de leur état. Read-only / lecture seule."
    )
    integration = DOMAIN
    annotations = READ_ONLY_ANNOTATIONS

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> llm.ToolResult:
        """List available VTherms."""
        thermostats = [
            _compact_state(state)
            for entity_id in _get_vtherm_entity_ids(hass, llm_context)
            if (state := hass.states.get(entity_id)) is not None
        ]

        return llm.ToolResult(
            data={
                "count": len(thermostats),
                "thermostats": thermostats,
            }
        )


class GetVThermStatusTool(llm.Tool):
    """Return the complete current Home Assistant state of one VTherm."""

    name = f"{DOMAIN}__get_status"
    title = "Get VTherm status / État VTherm"
    description = (
        "EN: Return the complete current Home Assistant state and all attributes "
        "of one Versatile Thermostat. "
        "FR: Retourne l'état Home Assistant courant complet et tous les attributs "
        "d'un Versatile Thermostat. Read-only / lecture seule."
    )
    integration = DOMAIN
    annotations = READ_ONLY_ANNOTATIONS

    def __init__(self, entity_ids: list[str]) -> None:
        """Initialize the tool."""
        self.parameters = probatio.Schema(
            {
                probatio.Required(
                    "entity_id",
                    description=(
                        "VTherm climate entity ID / entity_id climate du VTherm"
                    ),
                ): probatio.In(entity_ids),
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> llm.ToolResult:
        """Return the full state of one VTherm."""
        data = self.parameters(tool_input.tool_args)
        entity_id = data["entity_id"]

        state, error = _state_or_error(hass, entity_id)
        if error is not None:
            return error

        assert state is not None

        return llm.ToolResult(
            data={
                "entity_id": entity_id,
                "state": state.state,
                "last_changed": state.last_changed.isoformat(),
                "last_updated": state.last_updated.isoformat(),
                "attributes": _json_safe(dict(state.attributes)),
            }
        )


class DiagnoseVThermTool(llm.Tool):
    """Return structured VTherm diagnostic information."""

    name = f"{DOMAIN}__diagnose"
    title = "Diagnose VTherm / Diagnostiquer VTherm"
    description = (
        "EN: Debug, diagnose or troubleshoot a Versatile Thermostat. Return a "
        "structured read-only snapshot explaining heating/idle/off decisions, "
        "power shedding, safety, windows, presence, motion, auto-start/stop and "
        "underlying entities. "
        "FR: Déboguer, diagnostiquer ou dépanner un Versatile Thermostat. Retourne "
        "un état structuré en lecture seule expliquant chauffe/idle/off, délestage, "
        "sécurité, fenêtres, présence, mouvement, auto-start/stop et sous-jacents. "
        "Prefer specific_states.messages and reason fields over guessing."
    )
    integration = DOMAIN
    annotations = READ_ONLY_ANNOTATIONS

    def __init__(self, entity_ids: list[str]) -> None:
        """Initialize the tool."""
        self.parameters = probatio.Schema(
            {
                probatio.Required(
                    "entity_id",
                    description=(
                        "VTherm climate entity ID / entity_id climate du VTherm"
                    ),
                ): probatio.In(entity_ids),
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> llm.ToolResult:
        """Return a structured diagnostic snapshot."""
        data = self.parameters(tool_input.tool_args)
        entity_id = data["entity_id"]

        state, error = _state_or_error(hass, entity_id)
        if error is not None:
            return error

        assert state is not None
        attributes = state.attributes
        specific_states = _section(attributes, "specific_states")

        sections = {
            section_name: section
            for section_name in DIAGNOSTIC_SECTIONS
            if (section := _section(attributes, section_name))
        }

        return llm.ToolResult(
            data={
                "entity_id": entity_id,
                "name": _json_safe(attributes.get("friendly_name")),
                "availability": state.state
                not in (STATE_UNAVAILABLE, STATE_UNKNOWN),
                "current": _compact_state(state),
                "reasons": {
                    "messages": specific_states.get("messages", []),
                    "hvac_off_reason": specific_states.get("hvac_off_reason"),
                    "hvac_mode_reason": specific_states.get("hvac_mode_reason"),
                    "should_device_be_active": specific_states.get(
                        "should_device_be_active"
                    ),
                    "device_actives": specific_states.get("device_actives", []),
                    "unavailable_underlying_entities": specific_states.get(
                        "unavailable_underlying_entities",
                        [],
                    ),
                    "temperature_slope": specific_states.get("temperature_slope"),
                    "is_sleeping": specific_states.get("is_sleeping"),
                    "is_recalculate_scheduled": specific_states.get(
                        "is_recalculate_scheduled"
                    ),
                },
                "feature_flags": {
                    "is_presence_configured": bool(
                        attributes.get("is_presence_configured", False)
                    ),
                    "is_motion_configured": bool(
                        attributes.get("is_motion_configured", False)
                    ),
                    "is_power_configured": bool(
                        attributes.get("is_power_configured", False)
                    ),
                    "is_window_configured": bool(
                        attributes.get("is_window_configured", False)
                    ),
                    "is_window_auto_configured": bool(
                        attributes.get("is_window_auto_configured", False)
                    ),
                    "is_safety_configured": bool(
                        attributes.get("is_safety_configured", False)
                    ),
                    "is_auto_start_stop_configured": bool(
                        attributes.get("is_auto_start_stop_configured", False)
                    ),
                    "is_over_switch": bool(
                        attributes.get("is_over_switch", False)
                    ),
                    "is_over_valve": bool(attributes.get("is_over_valve", False)),
                    "is_over_climate": bool(
                        attributes.get("is_over_climate", False)
                    ),
                    "is_over_climate_valve": bool(
                        attributes.get("is_over_climate_valve", False)
                    ),
                },
                "sections": _json_safe(sections),
                "support_resources": _support_resources(llm_context.language),
                "last_changed": state.last_changed.isoformat(),
                "last_updated": state.last_updated.isoformat(),
            }
        )


class SetVThermTemperatureTool(llm.Tool):
    """Set the target temperature of one exposed VTherm."""

    name = f"{DOMAIN}__set_temperature"
    title = "Set VTherm temperature / Régler la température VTherm"
    description = (
        "EN: Set the target temperature of one Versatile Thermostat using the "
        "standard Home Assistant climate.set_temperature service. "
        "FR: Règle la température de consigne d'un Versatile Thermostat via le "
        "service standard Home Assistant climate.set_temperature. "
        "This changes Home Assistant state / modifie l'état Home Assistant."
    )
    integration = DOMAIN
    annotations = WRITE_ANNOTATIONS

    def __init__(self, entity_ids: list[str]) -> None:
        """Initialize the tool."""
        self.parameters = probatio.Schema(
            {
                probatio.Required(
                    "entity_id",
                    description=(
                        "VTherm climate entity ID / entity_id climate du VTherm"
                    ),
                ): probatio.In(entity_ids),
                probatio.Required(
                    "temperature",
                    description=(
                        "Target temperature / température cible. The value must "
                        "be inside the entity min/max range."
                    ),
                ): probatio.Coerce(float),
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> llm.ToolResult:
        """Set target temperature."""
        data = self.parameters(tool_input.tool_args)
        entity_id = data["entity_id"]
        temperature = float(data["temperature"])

        state, error = _state_or_error(hass, entity_id)
        if error is not None:
            return error

        assert state is not None

        if permission_error := await _control_permission_error(
            hass, llm_context, entity_id
        ):
            return permission_error

        minimum, maximum = _temperature_range(state.attributes)

        if minimum is not None and temperature < minimum:
            return llm.ToolResult(
                data={
                    "error": "Requested temperature is below the VTherm minimum.",
                    "entity_id": entity_id,
                    "requested_temperature": temperature,
                    "minimum_temperature": minimum,
                },
                error=True,
            )

        if maximum is not None and temperature > maximum:
            return llm.ToolResult(
                data={
                    "error": "Requested temperature is above the VTherm maximum.",
                    "entity_id": entity_id,
                    "requested_temperature": temperature,
                    "maximum_temperature": maximum,
                },
                error=True,
            )

        try:
            await hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_TEMPERATURE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_TEMPERATURE: temperature,
                },
                blocking=True,
                context=llm_context.context,
            )
        except HomeAssistantError as err:
            return llm.ToolResult(
                data={
                    "error": f"Failed to set VTherm temperature: {err}",
                    "entity_id": entity_id,
                    "requested_temperature": temperature,
                },
                error=True,
            )

        return _write_result(
            action="set_temperature",
            requested={
                "entity_id": entity_id,
                "temperature": temperature,
            },
            state=hass.states.get(entity_id),
        )


class SetVThermPresetTool(llm.Tool):
    """Set the preset mode of one exposed VTherm."""

    name = f"{DOMAIN}__set_preset"
    title = "Set VTherm preset / Régler le preset VTherm"
    description = (
        "EN: Set a visible preset mode of one Versatile Thermostat using "
        "climate.set_preset_mode. "
        "FR: Sélectionne un preset visible d'un Versatile Thermostat via "
        "climate.set_preset_mode. The preset must be present in preset_modes."
    )
    integration = DOMAIN
    annotations = WRITE_ANNOTATIONS

    def __init__(self, entity_ids: list[str]) -> None:
        """Initialize the tool."""
        self.parameters = probatio.Schema(
            {
                probatio.Required(
                    "entity_id",
                    description=(
                        "VTherm climate entity ID / entity_id climate du VTherm"
                    ),
                ): probatio.In(entity_ids),
                probatio.Required(
                    "preset",
                    description=(
                        "Visible VTherm preset, e.g. eco, comfort, boost, frost, "
                        "activity, none / preset visible du VTherm"
                    ),
                ): str,
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> llm.ToolResult:
        """Set preset mode."""
        data = self.parameters(tool_input.tool_args)
        entity_id = data["entity_id"]
        preset = data["preset"]

        state, error = _state_or_error(hass, entity_id)
        if error is not None:
            return error

        assert state is not None

        if permission_error := await _control_permission_error(
            hass, llm_context, entity_id
        ):
            return permission_error

        preset_modes = state.attributes.get("preset_modes")
        allowed_presets = (
            [str(item) for item in preset_modes]
            if isinstance(preset_modes, (list, tuple))
            else []
        )

        if preset not in allowed_presets:
            return llm.ToolResult(
                data={
                    "error": "Preset is not available on this VTherm.",
                    "entity_id": entity_id,
                    "requested_preset": preset,
                    "allowed_presets": allowed_presets,
                },
                error=True,
            )

        try:
            await hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_PRESET_MODE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_PRESET_MODE: preset,
                },
                blocking=True,
                context=llm_context.context,
            )
        except HomeAssistantError as err:
            return llm.ToolResult(
                data={
                    "error": f"Failed to set VTherm preset: {err}",
                    "entity_id": entity_id,
                    "requested_preset": preset,
                },
                error=True,
            )

        return _write_result(
            action="set_preset",
            requested={
                "entity_id": entity_id,
                "preset": preset,
            },
            state=hass.states.get(entity_id),
        )


class SetVThermHvacModeTool(llm.Tool):
    """Set the HVAC mode of one exposed VTherm."""

    name = f"{DOMAIN}__set_hvac_mode"
    title = "Set VTherm HVAC mode / Régler le mode HVAC VTherm"
    description = (
        "EN: Set the HVAC mode of one Versatile Thermostat using "
        "climate.set_hvac_mode. "
        "FR: Règle le mode HVAC d'un Versatile Thermostat via "
        "climate.set_hvac_mode. The mode must be present in hvac_modes."
    )
    integration = DOMAIN
    annotations = WRITE_ANNOTATIONS

    def __init__(self, entity_ids: list[str]) -> None:
        """Initialize the tool."""
        self.parameters = probatio.Schema(
            {
                probatio.Required(
                    "entity_id",
                    description=(
                        "VTherm climate entity ID / entity_id climate du VTherm"
                    ),
                ): probatio.In(entity_ids),
                probatio.Required(
                    "hvac_mode",
                    description=(
                        "HVAC mode supported by the VTherm, e.g. heat, cool, off "
                        "/ mode HVAC supporté par le VTherm"
                    ),
                ): str,
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> llm.ToolResult:
        """Set HVAC mode."""
        data = self.parameters(tool_input.tool_args)
        entity_id = data["entity_id"]
        hvac_mode = data["hvac_mode"]

        state, error = _state_or_error(hass, entity_id)
        if error is not None:
            return error

        assert state is not None

        if permission_error := await _control_permission_error(
            hass, llm_context, entity_id
        ):
            return permission_error

        hvac_modes = state.attributes.get("hvac_modes")
        allowed_modes = (
            [str(item) for item in hvac_modes]
            if isinstance(hvac_modes, (list, tuple))
            else []
        )

        if hvac_mode not in allowed_modes:
            return llm.ToolResult(
                data={
                    "error": "HVAC mode is not available on this VTherm.",
                    "entity_id": entity_id,
                    "requested_hvac_mode": hvac_mode,
                    "allowed_hvac_modes": allowed_modes,
                },
                error=True,
            )

        try:
            await hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_HVAC_MODE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_HVAC_MODE: hvac_mode,
                },
                blocking=True,
                context=llm_context.context,
            )
        except HomeAssistantError as err:
            return llm.ToolResult(
                data={
                    "error": f"Failed to set VTherm HVAC mode: {err}",
                    "entity_id": entity_id,
                    "requested_hvac_mode": hvac_mode,
                },
                error=True,
            )

        return _write_result(
            action="set_hvac_mode",
            requested={
                "entity_id": entity_id,
                "hvac_mode": hvac_mode,
            },
            state=hass.states.get(entity_id),
        )


def _assistant_prompt(language: str | None) -> str:
    """Return instructions in the request language, with FR/EN tool semantics."""
    if _is_french(language):
        return (
            "Les outils Versatile Thermostat acceptent les demandes en français "
            "ou en anglais. Pour comprendre un comportement, commencer par "
            "versatile_thermostat__diagnose. Considérer specific_states.messages, "
            "hvac_off_reason et hvac_mode_reason comme les informations de "
            "diagnostic VTherm prioritaires et ne pas inventer de cause absente "
            "des données. Pour un debug ou diagnostic complexe, consulter si "
            "possible le site de documentation FR/EN indiqué dans support_resources "
            "selon la langue de la demande, et rappeler que l'analyseur de logs est disponible à "
            f"{LOG_ANALYZER}. Les outils set_temperature, set_preset et "
            "set_hvac_mode modifient réellement le VTherm : utiliser uniquement "
            "l'outil correspondant à la demande explicite de l'utilisateur et "
            "ne jamais remplacer une demande de diagnostic par une modification."
        )

    return (
        "Versatile Thermostat tools understand requests in English or French. "
        "For behavior analysis, start with versatile_thermostat__diagnose. Treat "
        "specific_states.messages, hvac_off_reason and hvac_mode_reason as the "
        "primary VTherm diagnostic information and do not invent causes that are "
        "not supported by returned data. For complex debugging or troubleshooting, "
        "consult the FR/EN documentation website from support_resources matching the "
        "user request language when possible, and mention the log analyzer available at "
        f"{LOG_ANALYZER}. The set_temperature, set_preset and set_hvac_mode tools "
        "really modify the VTherm: use them only when the user explicitly asks "
        "for the corresponding change, and never turn a diagnostic request into "
        "a modification."
    )


@callback
def async_get_tools(
    hass: HomeAssistant,
    llm_context: llm.LLMContext,
    api_id: str,
) -> LLMTools | None:
    """Return VTherm LLM tools for Home Assistant's Assist API."""
    if api_id != llm.LLM_API_ASSIST:
        return None

    entity_ids = _get_vtherm_entity_ids(hass, llm_context)
    if not entity_ids:
        return None

    return LLMTools(
        tools=[
            ListVThermsTool(),
            GetVThermStatusTool(entity_ids),
            DiagnoseVThermTool(entity_ids),
            SetVThermTemperatureTool(entity_ids),
            SetVThermPresetTool(entity_ids),
            SetVThermHvacModeTool(entity_ids),
        ],
        prompt=_assistant_prompt(llm_context.language),
    )
