"""A controllable fictitious climate; P is never inferred from HA state H."""

# pylint: disable=abstract-method,protected-access

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.exceptions import HomeAssistantError

from tests.commons import MockClimate


DEVICE_ID = "climate.issue2135_simulated_device"
THERMOSTAT_ID = "climate.issue2135_simulated_vtherm"
ROOM_ID = "sensor.issue2135_simulated_room"
EXTERNAL_ID = "sensor.issue2135_simulated_outside"
ALLOWED_CLIMATE_TARGETS = frozenset({DEVICE_ID, THERMOSTAT_ID})


@dataclass(frozen=True)
class Record:
    seq: int
    time: float
    stage: str
    command_id: int | None
    value: object


class Journal:
    """Append-only sequence with monotonic time; values are copied at capture."""

    def __init__(self):
        self.started = monotonic()
        self.records: list[Record] = []

    def add(self, stage, value=None, command_id=None):
        self.records.append(Record(len(self.records) + 1, monotonic() - self.started,
                                   stage, command_id, value))


class SimulatedClimate(MockClimate):
    """Service acceptance, appliance application and HA publication are separate.

    Manual queues are deliberate suspension points; no background tasks are
    created by the double. A dropped command is accepted but not applied.
    """

    def __init__(self, hass, journal: Journal):
        super().__init__(hass, "issue2135_simulated_device", "Simulated device")
        self.journal = journal
        self.physical_mode = HVACMode.OFF
        self.physical_temperature = 20.0
        self.pending: list[tuple[int, HVACMode]] = []
        self.next_policy = "immediate"
        self.optimistic = False
        self.publish_on_apply = True
        self.command_id = 0

    async def async_set_hvac_mode(self, hvac_mode):
        self.command_id += 1
        cid = self.command_id
        mode = HVACMode(hvac_mode)
        self.journal.add("handler_enter", str(mode), cid)
        policy, self.next_policy = self.next_policy, "immediate"
        if policy == "reject":
            self.journal.add("handler_reject", str(mode), cid)
            raise HomeAssistantError("simulated rejection")
        self.journal.add("accepted", str(mode), cid)
        if self.optimistic:
            self.publish(mode, cid, "optimistic")
        if policy == "drop":
            self.journal.add("lost_after_acceptance", str(mode), cid)
        elif policy == "delay":
            self.pending.append((cid, mode))
            self.journal.add("queued", str(mode), cid)
        elif policy == "immediate":
            self.apply(cid, mode)
        else:
            raise ValueError(f"unknown simulated policy {policy}")
        self.journal.add("handler_return", str(mode), cid)

    async def async_set_temperature(self, **kwargs):
        value = kwargs.get(ATTR_TEMPERATURE)
        self.journal.add("temperature_handler", value)
        if value is not None:
            self.physical_temperature = value
            self._attr_target_temperature = value
            self.async_write_ha_state()

    def apply(self, cid, mode):
        self.physical_mode = mode
        self.journal.add("device_apply", str(mode), cid)
        if self.publish_on_apply:
            self.publish(mode, cid, "faithful")

    def deliver(self, index=0):
        cid, mode = self.pending.pop(index)
        self.apply(cid, mode)

    def publish(self, mode, cid=None, source="manual"):
        self._attr_hvac_mode = mode
        self._calculate_hvac_action()
        self.async_write_ha_state()
        self.journal.add("ha_publish_" + source, str(mode), cid)

    def close(self):
        for cid, mode in self.pending:
            self.journal.add("discarded_at_teardown", str(mode), cid)
        self.pending.clear()


def decision_snapshot(vtherm, simulated: SimulatedClimate):
    """Sample existing values; no decision or protection is replaced."""
    requested = vtherm.requested_state
    current = vtherm.current_state
    underlying = vtherm._underlyings[0]
    cached = underlying._state_manager.get_state(DEVICE_ID)
    observed = vtherm.hass.states.get(DEVICE_ID)
    algo = vtherm.auto_start_stop_manager._auto_start_stop_algo
    return {
        "R": str(requested.hvac_mode),
        "R_temperature": requested.target_temperature,
        "R_flags": (requested.is_hvac_mode_changed, requested.is_target_temperature_changed,
                    requested.is_preset_changed),
        "E": str(current.hvac_mode),
        "U": str(vtherm.get_underlying_hvac_mode(current.hvac_mode)),
        "stop": vtherm.auto_start_stop_manager.is_auto_stop_detected,
        "accumulated_error": algo.accumulated_error,
        "slope": vtherm.last_temperature_slope,
        # The decorated property raises in this product version; this is the
        # same flag check_and_repair actually reads, not a substituted decision.
        "repair_configured": vtherm.repair_incorrect_state_manager._is_configured,
        "repair_detected": vtherm.repair_incorrect_state_manager.is_detected,
        "follow_temperature": vtherm.follow_underlying_temp_change,
        "H": observed.state if observed else None,
        "H_cache": cached.state if cached else None,
        "P": str(simulated.physical_mode),
    }