"""Auto Fan feature manager for Versatile Thermostat over_climate thermostats.

This manager reproduces the historical ``auto-fan`` behavior that used to be
hard-coded in the VTherm core ``ThermostatOverClimate``. It maps a logical fan
level (none/low/medium/high/turbo) onto a real ``fan_mode`` of the underlying
climate and drives it depending on the temperature gap at each cycle.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.event import (
    async_track_state_change_event,
    EventStateChangedData,
)

from vtherm_api.log_collector import get_vtherm_logger

from .const import (
    ATTR_AUTO_FAN_SECTION,
    AUTO_FAN_DEACTIVATED_MODES,
    AUTO_FAN_DTEMP_THRESHOLD,
    CONF_AUTO_FAN_HIGH,
    CONF_AUTO_FAN_LOW,
    CONF_AUTO_FAN_MEDIUM,
    CONF_AUTO_FAN_MODE,
    CONF_AUTO_FAN_NONE,
    CONF_AUTO_FAN_TURBO,
    DATA_MANAGERS,
    DOMAIN,
    FEATURE_MANAGER_AUTO_FAN,
    SERVICE_AUTO_FAN_LEVELS,
    VTHERM_HVAC_MODE_COOL,
    VTHERM_HVAC_MODE_HEAT,
    VTHERM_HVAC_MODE_OFF,
)

if TYPE_CHECKING:
    from vtherm_api.interfaces import InterfaceThermostatRuntime

_LOGGER = get_vtherm_logger(__name__)


class AutoFanFeatureManager:
    """Feature manager implementing the auto-fan behavior for a single VTherm."""

    #: Recorder can only filter top-level keys, so all auto-fan attributes live
    #: under a single top-level section which is declared here.
    unrecorded_attributes = frozenset({ATTR_AUTO_FAN_SECTION})

    def __init__(self, thermostat: "InterfaceThermostatRuntime", hass: HomeAssistant):
        """Initialize the manager bound to a runtime thermostat."""
        self._vtherm = thermostat
        self._hass = hass
        self._name = thermostat.name

        # The fan level configured for this VTherm.
        self._auto_fan_mode: str = CONF_AUTO_FAN_NONE
        # The current fan level (can be changed at runtime by a service call).
        self._current_auto_fan_mode: str = CONF_AUTO_FAN_NONE
        # The real underlying fan_mode used when the auto fan is activated.
        self._auto_activated_fan_mode: str | None = None
        # The real underlying fan_mode used when the auto fan is deactivated.
        self._auto_deactivated_fan_mode: str | None = None
        # The last fan_mode we sent to the underlying (to avoid resending).
        self._last_sent_fan_mode: str | None = None

        self._active_listener: list = []

    # ------------------------------------------------------------------
    # Lifecycle (InterfaceFeatureManager contract)
    # ------------------------------------------------------------------
    def post_init(self, entry_infos: Any) -> None:
        """Initialize the manager from its resolved configuration.

        The auto-fan configuration lives in this plugin's own config entries
        (keyed by the VTherm ``unique_id``). As a migration fallback, the old
        ``auto_fan_mode`` key possibly still present in the VTherm entry is used.
        """
        level = self._resolve_level(entry_infos)
        self._auto_fan_mode = level
        self._current_auto_fan_mode = level
        # Register this manager so services can reach it.
        self._registry()[self._vtherm.unique_id] = self
        _LOGGER.debug("%s - Auto fan manager initialized with level %s", self, level)

    async def start_listening(self, force: bool = False) -> None:
        """Compute the fan mapping and subscribe to VTherm state changes.

        The core does not call ``refresh_state`` on external managers at every
        cycle and over_climate thermostats have no cycle scheduler. Instead we
        re-evaluate the auto fan whenever the VTherm publishes a new state,
        which happens at each control cycle.
        """
        self.stop_listening()
        self.choose_auto_fan_mode(self._auto_fan_mode)
        self._active_listener.append(
            async_track_state_change_event(
                self._hass,
                [self._vtherm.entity_id],
                self._async_vtherm_state_changed,
            )
        )

    def stop_listening(self) -> bool | None:
        """Remove all active listeners."""
        while self._active_listener:
            self._active_listener.pop()()
        return None

    async def refresh_state(self) -> bool:
        """Re-evaluate and apply the auto fan mode. Returns True on change."""
        return await self._send_auto_fan_mode()

    def restore_state(self, old_state: Any) -> None:
        """Restore the current auto fan level from a previous HA state."""
        if old_state is None:
            return
        section = old_state.attributes.get(ATTR_AUTO_FAN_SECTION)
        if isinstance(section, dict):
            restored = section.get("current_auto_fan_mode")
            if restored:
                self._auto_fan_mode = restored
                self._current_auto_fan_mode = restored

    def add_listener(self, func) -> None:
        """Add a callback to be removed on stop."""
        self._active_listener.append(func)

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]) -> None:
        """Expose the auto fan attributes under a dedicated top-level section."""
        extra_state_attributes[ATTR_AUTO_FAN_SECTION] = {
            "auto_fan_mode": self._auto_fan_mode,
            "current_auto_fan_mode": self._current_auto_fan_mode,
            "auto_activated_fan_mode": self._auto_activated_fan_mode,
            "auto_deactivated_fan_mode": self._auto_deactivated_fan_mode,
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
    def is_configured(self) -> bool:
        """True when an actual fan level is configured."""
        return self._auto_fan_mode != CONF_AUTO_FAN_NONE

    @property
    def is_detected(self) -> bool:
        """True when the auto fan is currently activating the underlying."""
        return (
            self._auto_activated_fan_mode is not None
            and self._last_sent_fan_mode == self._auto_activated_fan_mode
        )

    @property
    def auto_fan_mode(self) -> str:
        """The configured auto fan level."""
        return self._auto_fan_mode

    # ------------------------------------------------------------------
    # Service entry point
    # ------------------------------------------------------------------
    async def async_set_auto_fan_mode(self, auto_fan_mode: str) -> None:
        """Change the auto fan level at runtime and re-apply it.

        Accepts either an internal level (``auto_fan_high``) or a historical
        human-readable value (``High``) so the same entry point can be used by
        the plugin and by the legacy ``versatile_thermostat.set_auto_fan_mode``
        core service.
        """
        level = SERVICE_AUTO_FAN_LEVELS.get(auto_fan_mode, auto_fan_mode)
        _LOGGER.info("%s - Setting auto fan mode to %s", self, level)
        self._auto_fan_mode = level
        self.choose_auto_fan_mode(level)
        await self._send_auto_fan_mode()
        self._vtherm.update_custom_attributes()
        self._vtherm.async_write_ha_state()

    # ------------------------------------------------------------------
    # Internal logic
    # ------------------------------------------------------------------
    @callback
    def _async_vtherm_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Re-evaluate the auto fan when the VTherm publishes a new state."""
        del event
        self._hass.async_create_task(self._send_auto_fan_mode())

    def _resolve_level(self, entry_infos: Any) -> str:
        """Resolve the effective auto fan level for this VTherm.

        Priority: per-thermostat plugin entry > global defaults entry >
        legacy ``auto_fan_mode`` in the VTherm entry > ``auto_fan_none``.
        """
        from .const import DEFAULT_AUTO_FAN_MODE  # local import to ease testing

        unique_id = self._vtherm.unique_id
        global_level: str | None = None
        per_level: str | None = None

        for entry in self._hass.config_entries.async_entries(DOMAIN):
            data = {**entry.data, **(entry.options or {})}
            target = data.get("target_vtherm_unique_id")
            if target is None:
                global_level = data.get(CONF_AUTO_FAN_MODE, global_level)
            elif target == unique_id:
                per_level = data.get(CONF_AUTO_FAN_MODE, per_level)

        if per_level is not None:
            return per_level
        if global_level is not None:
            return global_level

        # Migration fallback: read the legacy key from the VTherm entry.
        if isinstance(entry_infos, dict):
            legacy = entry_infos.get(CONF_AUTO_FAN_MODE)
            if legacy is not None:
                return legacy

        # No plugin entry configured for this VTherm.
        if self._has_any_entry():
            return CONF_AUTO_FAN_NONE
        return DEFAULT_AUTO_FAN_MODE

    def _has_any_entry(self) -> bool:
        """True when at least one plugin config entry exists."""
        return bool(self._hass.config_entries.async_entries(DOMAIN))

    def _registry(self) -> dict[str, "AutoFanFeatureManager"]:
        """Return the shared registry of live managers."""
        return self._hass.data.setdefault(DOMAIN, {}).setdefault(DATA_MANAGERS, {})

    async def _send_auto_fan_mode(self) -> bool:
        """Apply the fan mode if the temperature gap crosses the threshold.

        Returns True if a fan mode has been sent to the underlying.
        """
        if self._auto_fan_mode == CONF_AUTO_FAN_NONE or not self._auto_activated_fan_mode:
            return False

        target = self._vtherm.regulated_target_temperature
        if target is None:
            target = self._vtherm.target_temperature
        current = self._vtherm.current_temperature
        if target is None or current is None:
            return False

        dtemp = target - current
        should_activate = (
            dtemp >= AUTO_FAN_DTEMP_THRESHOLD or dtemp <= -AUTO_FAN_DTEMP_THRESHOLD
        )

        # Deal with heating / cooling coherence.
        hvac_mode = self._vtherm.vtherm_hvac_mode
        if (
            (hvac_mode == VTHERM_HVAC_MODE_COOL and dtemp > 0)
            or (hvac_mode == VTHERM_HVAC_MODE_HEAT and dtemp < 0)
            or (hvac_mode == VTHERM_HVAC_MODE_OFF)
        ):
            should_activate = False

        if should_activate:
            if self._last_sent_fan_mode != self._auto_activated_fan_mode:
                _LOGGER.info(
                    "%s - Activate the auto fan mode with %s because delta temp is %.2f",
                    self,
                    self._auto_activated_fan_mode,
                    dtemp,
                )
                await self._vtherm.async_set_underlying_fan_mode(
                    self._auto_activated_fan_mode
                )
                self._last_sent_fan_mode = self._auto_activated_fan_mode
                return True
            return False

        if (
            self._auto_deactivated_fan_mode is not None
            and self._last_sent_fan_mode not in AUTO_FAN_DEACTIVATED_MODES
        ):
            _LOGGER.info(
                "%s - Deactivate the auto fan mode with %s because delta temp is %.2f",
                self,
                self._auto_deactivated_fan_mode,
                dtemp,
            )
            await self._vtherm.async_set_underlying_fan_mode(
                self._auto_deactivated_fan_mode
            )
            self._last_sent_fan_mode = self._auto_deactivated_fan_mode
            return True

        return False

    def choose_auto_fan_mode(self, auto_fan_mode: str) -> None:
        """Map a logical fan level onto real underlying fan modes.

        Adapts to the number of available speeds on the underlying climate.
        """
        self._current_auto_fan_mode = auto_fan_mode

        fan_modes = self._vtherm.underlying_fan_modes or []

        if auto_fan_mode == CONF_AUTO_FAN_NONE or not fan_modes:
            self._auto_activated_fan_mode = None
            self._auto_deactivated_fan_mode = None
            return

        def find_fan_mode(modes: list[str], fan_mode: str) -> str | None:
            """Return the fan_mode if it exists in modes, else None."""
            try:
                return fan_mode if modes.index(fan_mode) >= 0 else None
            except ValueError:
                return None

        def determine_fan_mode_contains_speed(modes: list[str]) -> bool:
            """Determine if the modes contain speed values ("low"/"1")."""
            for val in ["low", "1"]:
                if find_fan_mode(modes, val):
                    return True
            return False

        def fix_order_speed_modes(speed_modes: list) -> list:
            """Reverse the list if it is ordered from high to low speed."""
            index = -1
            if "low" in speed_modes:
                index = speed_modes.index("low")
            elif "1" in speed_modes:
                index = speed_modes.index("1")

            if index > -1 and index >= len(speed_modes) / 2:
                speed_modes.reverse()

            return speed_modes

        # Remove special modes like "auto".
        speed_modes = [mode for mode in fan_modes if mode not in ["auto"]]

        num_speeds = len(speed_modes)
        if num_speeds == 0:
            self._auto_activated_fan_mode = None
            return

        # Assume speed_modes are ordered from low to high speed.
        speed_modes = fix_order_speed_modes(speed_modes)

        target_index = -1

        if determine_fan_mode_contains_speed(fan_modes) is False:
            self._auto_activated_fan_mode = None
            _LOGGER.warning(
                "%s - choose_auto_fan_mode cannot define value because "
                "fan_modes=%s doesn't contain speed values",
                self,
                fan_modes,
            )
            return

        if auto_fan_mode == CONF_AUTO_FAN_LOW:
            target_index = num_speeds - 4 if num_speeds >= 4 else 0
        elif auto_fan_mode == CONF_AUTO_FAN_MEDIUM:
            target_index = num_speeds - 3 if num_speeds >= 4 else 1
        elif auto_fan_mode == CONF_AUTO_FAN_HIGH:
            target_index = num_speeds - 2 if num_speeds >= 4 else 2
        elif auto_fan_mode == CONF_AUTO_FAN_TURBO:
            target_index = num_speeds - 1

        if 0 <= target_index < num_speeds:
            self._auto_activated_fan_mode = speed_modes[target_index]
        else:
            self._auto_activated_fan_mode = None

        self._auto_deactivated_fan_mode = None
        for val in AUTO_FAN_DEACTIVATED_MODES:
            if find_fan_mode(fan_modes, val):
                self._auto_deactivated_fan_mode = val
                break

        _LOGGER.info(
            "%s - choose_auto_fan_mode found current=%s activated=%s deactivated=%s",
            self,
            self._current_auto_fan_mode,
            self._auto_activated_fan_mode,
            self._auto_deactivated_fan_mode,
        )

    def __str__(self) -> str:
        """Readable representation used in logs."""
        return f"AutoFanManager-{self._name}"
