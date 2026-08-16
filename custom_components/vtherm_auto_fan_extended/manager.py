"""Auto Fan feature manager for Versatile Thermostat over_climate thermostats.

This manager drives the ``fan_mode`` of the underlying climate from a set of
user-defined thresholds. For each ``fan_mode`` a ``number`` entity holds the
temperature gap above which that mode becomes a candidate; a ``select`` entity
holds the rest mode applied when the gap is below every active threshold; a
``switch`` entity enables or disables the whole feature. The manager reads
those entities and, at each cycle, applies the selected ``fan_mode`` to the
underlying climate.
"""

from __future__ import annotations

import re
from typing import Any, TYPE_CHECKING

from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant

from vtherm_api.log_collector import get_vtherm_logger, write_event_log

from .const import (
    ATTR_AUTO_FAN_SECTION,
    CONF_EXCLUSION_PATTERNS,
    CONF_TARGET_VTHERM,
    DEFAULT_EXCLUSION_PATTERNS,
    DOMAIN,
    FEATURE_MANAGER_AUTO_FAN,
    PLATFORM_NUMBER,
    PLATFORM_SELECT,
    PLATFORM_SENSOR,
    PLATFORM_SWITCH,
)
from .registry import add_entities_registry, entity_bucket, managers
from .selection import (
    compile_exclusion_patterns,
    compute_default_rest_mode,
    compute_default_thresholds,
    filter_participants,
    select_fan_mode,
)

if TYPE_CHECKING:
    from vtherm_api.interfaces import InterfaceThermostatRuntime

_LOGGER = get_vtherm_logger(__name__)


class AutoFanFeatureManager:
    """Feature manager implementing the threshold-based auto fan for a VTherm."""

    #: Recorder can only filter top-level keys, so all auto-fan attributes live
    #: under a single top-level section which is declared here.
    unrecorded_attributes = frozenset({ATTR_AUTO_FAN_SECTION})

    def __init__(self, thermostat: "InterfaceThermostatRuntime", hass: HomeAssistant):
        """Initialize the manager bound to a runtime thermostat."""
        self._vtherm = thermostat
        self._hass = hass
        self._name = thermostat.name

        # The last fan_mode we sent to the underlying (to avoid resending).
        self._last_sent_fan_mode: str | None = None
        # Latest evaluated values, exposed as custom attributes.
        self._last_dtemp: float | None = None
        self._selected_fan_mode: str | None = None
        # fan_modes for which a threshold number has already been created.
        self._created_number_fan_modes: set[str] = set()
        self._rest_select_created = False
        self._switch_created = False
        self._sensor_created = False
        # Cached device info used to attach the entities to the VTherm device.
        self._device_info: Any = None

        # Exclusion patterns (raw + compiled), read from the config entry.
        self._exclusion_patterns_raw: list[str] = []
        self._exclusion_patterns: list[re.Pattern[str]] = []

        self._active_listener: list = []

    # ------------------------------------------------------------------
    # Lifecycle (InterfaceFeatureManager contract)
    # ------------------------------------------------------------------
    def post_init(self, entry_infos: Any) -> None:
        """Register the manager and try to create its entities."""
        del entry_infos
        managers(self._hass)[self._vtherm.unique_id] = self
        _LOGGER.info(
            "%s - Auto fan plugin registered for VTherm %s",
            self,
            self._vtherm.unique_id,
        )
        self.ensure_entities()

    async def start_listening(self, force: bool = False) -> None:
        """Create the entities once the underlying fan_modes are known."""
        del force
        self.stop_listening()
        self.ensure_entities()

    def stop_listening(self) -> bool | None:
        """Remove all active listeners."""
        while self._active_listener:
            self._active_listener.pop()()
        return None

    async def refresh_state(self) -> bool:
        """Reconcile entities then evaluate and apply the fan mode."""
        _LOGGER.debug("%s - refresh_state called", self)
        # The underlying may not have published its fan_modes at startup: retry
        # the entity creation here so the auto fan can self-heal.
        self.ensure_entities()
        return await self._evaluate()

    def restore_state(self, old_state: Any) -> None:
        """No-op: the entities restore their own state on startup."""
        del old_state

    def add_listener(self, func) -> None:
        """Add a callback to be removed on stop."""
        self._active_listener.append(func)

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]) -> None:
        """Expose the auto fan attributes under a dedicated top-level section."""
        extra_state_attributes[ATTR_AUTO_FAN_SECTION] = {
            "enabled": self._enabled(),
            "current_gap": self._last_dtemp,
            "selected_fan_mode": self._selected_fan_mode,
            "sent_fan_mode": self._last_sent_fan_mode,
            "rest_mode": self._rest_mode(),
            "thresholds": self._current_thresholds(),
        }

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def name(self) -> str:
        """Logical name of the manager."""
        return FEATURE_MANAGER_AUTO_FAN

    @property
    def hass(self) -> HomeAssistant:
        """Home Assistant instance."""
        return self._hass

    @property
    def vtherm(self) -> "InterfaceThermostatRuntime":
        """The runtime thermostat bound to this manager."""
        return self._vtherm

    @property
    def vtherm_unique_id(self) -> str:
        """The unique_id of the bound VTherm."""
        return self._vtherm.unique_id

    @property
    def vtherm_name(self) -> str:
        """The name of the bound VTherm."""
        return self._name

    @property
    def available_fan_modes(self) -> list[str]:
        """The fan modes currently exposed by the underlying climate."""
        return list(self._vtherm.underlying_fan_modes or [])

    @property
    def device_info(self) -> Any:
        """Return the device info the entities attach to.

        Resolved once from the VTherm entity registry entry so the auto fan
        entities are grouped under the same device as the thermostat.
        """
        if self._device_info is not None:
            return self._device_info

        runtime_info = getattr(self._vtherm, "device_info", None)
        if runtime_info:
            self._device_info = runtime_info
            return self._device_info

        self._device_info = self._resolve_device_info()
        return self._device_info

    @property
    def is_fahrenheit(self) -> bool:
        """True when the HA environment uses Fahrenheit."""
        return self._temperature_unit == UnitOfTemperature.FAHRENHEIT

    @property
    def is_configured(self) -> bool:
        """True when the auto fan is enabled and has usable fan modes."""
        return self._enabled() and bool(self._vtherm.underlying_fan_modes)

    @property
    def is_detected(self) -> bool:
        """True when the auto fan currently drives a non-rest fan mode."""
        return (
            self._enabled()
            and self._last_sent_fan_mode is not None
            and self._last_sent_fan_mode != self._rest_mode()
        )

    # ------------------------------------------------------------------
    # Entity callbacks
    # ------------------------------------------------------------------
    async def on_config_changed(self) -> None:
        """Re-evaluate and apply the fan mode after a config entity changed."""
        await self._evaluate()
        self._vtherm.update_custom_attributes()
        self._vtherm.async_write_ha_state()

    # ------------------------------------------------------------------
    # Internal logic
    # ------------------------------------------------------------------
    @property
    def _temperature_unit(self) -> str:
        """Return the HA temperature unit."""
        return self._hass.config.units.temperature_unit

    def _read_exclusion_patterns_raw(self) -> list[str]:
        """Read the raw exclusion patterns from the plugin config entry.

        Falls back to the defaults when the config entry cannot be reached (for
        example during early startup or in unit tests).
        """
        config_entries = getattr(self._hass, "config_entries", None)
        if config_entries is not None:
            try:
                entries = config_entries.async_entries(DOMAIN)
            except Exception:  # pylint: disable=broad-except
                entries = []
            for entry in entries:
                if entry.data.get(CONF_TARGET_VTHERM) == self._vtherm.unique_id:
                    return list(
                        entry.data.get(
                            CONF_EXCLUSION_PATTERNS, DEFAULT_EXCLUSION_PATTERNS
                        )
                    )
        return list(DEFAULT_EXCLUSION_PATTERNS)

    def _refresh_exclusion_patterns(self) -> None:
        """Recompile the exclusion patterns when the raw list changed."""
        raw = self._read_exclusion_patterns_raw()
        if raw != self._exclusion_patterns_raw:
            self._exclusion_patterns_raw = raw
            self._exclusion_patterns = compile_exclusion_patterns(raw)

    def _bucket(self) -> dict[str, Any]:
        """Return the live entity bucket for this VTherm."""
        return entity_bucket(self._hass, self._vtherm.unique_id)

    def _current_thresholds(self) -> dict[str, float]:
        """Return the thresholds of the fan modes currently available."""
        numbers = self._bucket()["numbers"]
        fan_modes = self._vtherm.underlying_fan_modes or []
        thresholds: dict[str, float] = {}
        for fan_mode in fan_modes:
            entity = numbers.get(fan_mode)
            if entity is not None and entity.native_value is not None:
                thresholds[fan_mode] = float(entity.native_value)
        return thresholds

    def _rest_mode(self) -> str | None:
        """Return the effective rest fan mode."""
        fan_modes = self._vtherm.underlying_fan_modes or []
        select = self._bucket()["select"]
        if select is not None and select.current_option in fan_modes:
            return select.current_option
        # The configured rest mode disappeared (or no select yet): fall back.
        return compute_default_rest_mode(fan_modes)

    def _enabled(self) -> bool:
        """Return True when the auto fan switch is on."""
        switch = self._bucket()["switch"]
        return bool(switch.is_on) if switch is not None else False

    async def _evaluate(self) -> bool:
        """Evaluate the selection and apply it to the underlying if needed."""
        fan_modes = self._vtherm.underlying_fan_modes or []
        if not fan_modes or not self._enabled():
            return False

        target = self._vtherm.regulated_target_temperature
        if target is None:
            target = self._vtherm.target_temperature
        current = self._vtherm.current_temperature
        if target is None or current is None:
            return False

        dtemp = target - current
        thresholds = self._current_thresholds()
        rest_mode = self._rest_mode()
        hvac_mode = self._vtherm.vtherm_hvac_mode

        selected = select_fan_mode(dtemp, thresholds, rest_mode, hvac_mode)
        self._last_dtemp = dtemp
        self._selected_fan_mode = selected

        _LOGGER.debug(
            "%s - evaluate dtemp=%.2f thresholds=%s rest=%s hvac=%s -> %s",
            self,
            dtemp,
            thresholds,
            rest_mode,
            hvac_mode,
            selected,
        )

        if selected is None:
            return False

        # Guard against a fan_mode that no longer exists on the underlying.
        if selected not in fan_modes:
            _LOGGER.warning(
                "%s - selected fan mode %s is not available anymore, falling "
                "back to a valid mode",
                self,
                selected,
            )
            if rest_mode in fan_modes:
                selected = rest_mode
            elif fan_modes:
                selected = fan_modes[0]
            else:
                return False

        if selected != self._last_sent_fan_mode:
            write_event_log(
                _LOGGER,
                self._vtherm,
                f"Auto fan: setting underlying fan mode to '{selected}' "
                f"because delta temp is {dtemp:.2f}",
            )
            await self._vtherm.async_set_underlying_fan_mode(selected)
            self._last_sent_fan_mode = selected
            self._update_sensor(selected)
            return True

        return False

    def _update_sensor(self, fan_mode: str) -> None:
        """Push the sent fan_mode to the current-fan-mode sensor, if present."""
        sensor = self._bucket().get("sensor")
        if sensor is not None:
            sensor.update_fan_mode(fan_mode)

    def _resolve_device_info(self) -> Any:
        """Resolve the VTherm device info from the entity/device registries."""
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        ent_reg = er.async_get(self._hass)
        entry = ent_reg.async_get(self._vtherm.entity_id)
        if entry is None or entry.device_id is None:
            return None
        dev_reg = dr.async_get(self._hass)
        device = dev_reg.async_get(entry.device_id)
        if device is None:
            return None
        return {
            "identifiers": device.identifiers,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }

    def ensure_entities(self) -> None:
        """Create the auto fan entities as soon as they can be created.

        The switch and the current-fan-mode sensor do not depend on the fan
        modes and are created as soon as their platform callbacks are
        available. The threshold numbers and the rest select are created once
        the underlying fan_modes are available. This is called at each cycle so
        the entities self-heal when the underlying publishes (or changes) its
        fan_modes later, and the threshold numbers are reconciled against the
        exclusion patterns.
        """
        self._refresh_exclusion_patterns()

        registry = add_entities_registry(self._hass).get(self._vtherm.unique_id)
        if not registry:
            return

        switch_cb = registry.get(PLATFORM_SWITCH)
        if switch_cb is not None and not self._switch_created:
            self._create_switch(switch_cb)

        sensor_cb = registry.get(PLATFORM_SENSOR)
        if sensor_cb is not None and not self._sensor_created:
            self._create_sensor(sensor_cb)

        fan_modes = self._vtherm.underlying_fan_modes or []
        if not fan_modes:
            return

        number_cb = registry.get(PLATFORM_NUMBER)
        if number_cb is not None:
            self._reconcile_threshold_numbers(fan_modes, number_cb)

        select_cb = registry.get(PLATFORM_SELECT)
        if select_cb is not None and not self._rest_select_created:
            self._create_rest_select(fan_modes, select_cb)

    def _create_switch(self, add_entities) -> None:
        """Create the auto fan enable ``switch`` entity."""
        from .switch import AutoFanEnableSwitch  # local import to avoid a cycle

        add_entities([AutoFanEnableSwitch(self)])
        self._switch_created = True

    def _create_sensor(self, add_entities) -> None:
        """Create the current-fan-mode ``sensor`` entity."""
        from .sensor import AutoFanCurrentFanModeSensor  # local import (cycle)

        add_entities([AutoFanCurrentFanModeSensor(self)])
        self._sensor_created = True

    def _reconcile_threshold_numbers(self, fan_modes: list[str], add_entities) -> None:
        """Create numbers for participants and remove obsolete ones.

        A threshold ``number`` exists only for participant fan_modes (those not
        matched by an exclusion pattern) that are currently exposed by the
        underlying. Numbers whose fan_mode became excluded or disappeared are
        removed.
        """
        from .number import ThresholdNumber  # local import to avoid a cycle

        participants = filter_participants(fan_modes, self._exclusion_patterns)
        participant_set = set(participants)

        obsolete = self._created_number_fan_modes - participant_set
        for fan_mode in obsolete:
            self._remove_number(fan_mode)

        defaults = compute_default_thresholds(
            fan_modes, self._exclusion_patterns, self.is_fahrenheit
        )
        new_entities = []
        for fan_mode in participants:
            if fan_mode in self._created_number_fan_modes:
                continue
            new_entities.append(
                ThresholdNumber(
                    self,
                    fan_mode,
                    defaults.get(fan_mode, 0.0),
                    self._temperature_unit,
                )
            )
            self._created_number_fan_modes.add(fan_mode)

        if new_entities:
            add_entities(new_entities)

    def _remove_number(self, fan_mode: str) -> None:
        """Remove the threshold ``number`` entity of a fan_mode."""
        self._created_number_fan_modes.discard(fan_mode)
        entity = self._bucket()["numbers"].get(fan_mode)
        if entity is None:
            return
        create_task = getattr(self._hass, "async_create_task", None)
        if create_task is not None:
            create_task(self._async_remove_entity(entity))

    async def _async_remove_entity(self, entity) -> None:
        """Remove an entity from HA and from the entity registry."""
        from homeassistant.helpers import entity_registry as er

        entity_id = entity.entity_id
        await entity.async_remove(force_remove=True)
        ent_reg = er.async_get(self._hass)
        if entity_id and ent_reg.async_get(entity_id) is not None:
            ent_reg.async_remove(entity_id)

    def _create_rest_select(self, fan_modes: list[str], add_entities) -> None:
        """Create the rest-mode ``select`` entity."""
        from .select import RestModeSelect  # local import to avoid a cycle

        default_rest = compute_default_rest_mode(fan_modes)
        add_entities([RestModeSelect(self, default_rest)])
        self._rest_select_created = True

    def __str__(self) -> str:
        """Readable representation used in logs."""
        return f"AutoFanManager-{self._name}"
