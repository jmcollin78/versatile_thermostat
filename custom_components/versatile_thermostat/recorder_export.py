"""Shared raw Recorder reads and paginated VTherm client-side exports."""

from datetime import timedelta

from homeassistant.components.recorder import get_instance, history
from homeassistant.util import dt as dt_util

# Only recorded climate fields: never substitute today's state/configuration.
RECORDED_ATTRIBUTES = (
    "current_temperature",
    "temperature",
    "target_temp_low",
    "target_temp_high",
    "hvac_action",
    "preset_mode",
    "unit_of_measurement",
)


def read_recorder_history(hass, start, end, entity_ids):
    """Read raw State objects for export and TPI, in the Recorder executor.

    Callers select authorized sources and validate their UTC period. Preserve
    recorded attributes, unknown states and original timestamps, including the
    carried initial state. Export serialization and TPI resampling stay separate.
    """
    states = history.get_significant_states(
        hass,
        # Recorder uses a strict lower bound; include events exactly at start.
        start - timedelta(microseconds=1),
        end_time=end,
        entity_ids=entity_ids,
        include_start_time_state=True,
        significant_changes_only=False,
        minimal_response=False,
        no_attributes=False,
    )
    return {
        entity_id: sorted(values, key=lambda state: state.last_updated)
        for entity_id, values in states.items()
    }


async def async_export_history(hass, entity_id, start, end, offset, limit):
    """Query Recorder in its executor and serialize there, never on the loop."""
    if "recorder" not in hass.config.components:
        raise ValueError("recorder_unavailable")
    start = dt_util.parse_datetime(start)
    end = dt_util.parse_datetime(end)
    if start is None or end is None or start.tzinfo is None or end.tzinfo is None:
        raise ValueError("timezone_required")
    start, end = dt_util.as_utc(start), dt_util.as_utc(end)
    if not start < end or end - start > timedelta(days=14):
        raise ValueError("invalid_period_max_14_days")
    if end > dt_util.utcnow():
        raise ValueError("future_period")

    def load():
        states = read_recorder_history(hass, start, end, [entity_id]).get(entity_id, [])
        page = states[offset : offset + limit]
        rows = [
            {
                "timestamp": max(start, state.last_updated).isoformat(),
                "state": state.state,
                "attributes": {
                    key: state.attributes.get(key) for key in RECORDED_ATTRIBUTES
                },
            }
            for state in page
        ]
        next_offset = offset + len(page) if offset + len(page) < len(states) else None
        return {
            "entity_id": entity_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "timezone": "UTC",
            "rows": rows,
            "offset": offset,
            "total_rows": len(states),
            "next_offset": next_offset,
            "pagination_complete": next_offset is None,
            "state_changed": False,
            "semantics": (
                "Recorded state/attribute changes, not regular samples. "
                "Recorder may provide a carried state at start_time. "
                "Null fields were not recorded. unknown/unavailable remain explicit. "
                "Retention, exclusions and gaps can limit history; completeness is unknown. "
                "Keep the same entity/start/end/limit and use next_offset until null. "
                "The client creates CSV or plots; never invent missing samples."
            ),
        }

    return await get_instance(hass).async_add_executor_job(load)
