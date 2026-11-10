# Calendar scheduling

- [Calendar scheduling](#calendar-scheduling)
  - [Purpose](#purpose)
  - [Configuration](#configuration)
  - [Preheat](#preheat)
  - [Behaviour](#behaviour)
  - [Custom attributes](#custom-attributes)

## Purpose

A _VTherm_ follows a Home Assistant `calendar` entity: one preset is applied while an event is running and another one when it ends. With a preheat gradient, the heating starts early enough for the room to be warm when the event starts.

All the events of the calendar are used. Overlapping and contiguous events are handled as one, and an all-day event runs from midnight to midnight.

## Configuration

Select **Use calendar scheduling** in the features, then open the **Calendar scheduling** menu:

| Parameter | Description | Attribute Name |
| --------- | ----------- | -------------- |
| **Calendar** | The `calendar` entity to follow. | `calendar_entity_id` |
| **Preset during an event** | Applied when the preheat or the event starts. Default `comfort`. | `calendar_event_preset` |
| **Preset after an event** | Applied when the event ends. **Previous preset** restores the preset which was active before the event. Default `eco`. | `calendar_end_preset` |
| **Preheat gradient** | Temperature gained by the room per hour of heating. `0` disables the preheat. | `calendar_preheat_gradient` |
| **Maximum preheat duration** | The preheat never starts earlier than this duration before an event, in minutes. Default `240`. | `calendar_max_preheat_min` |

## Preheat

The preheat starts `(temperature of the event preset - room temperature) / gradient` hours before the event. With a gradient of 3°/h, a room at 15° and an event preset at 21°, the heating starts 2 hours before the event.

- The start is planned again at each room temperature change, until the preheat has started.
- A started preheat is kept until the event ends, even if the room heats faster than predicted.
- An event known too late is preheated at once. `estimated_ready_time` gives the time at which the room should be warm.
- The preheat only applies when the _VTherm_ is in `heat` mode. A stopped _VTherm_ is never started: it only receives the presets.

The gradient is a fixed value: choose a pessimistic one, measured on a cold day.

## Behaviour

- The calendar is read every 15 minutes, at each change of the calendar entity and at each planned transition. Events are visible to _VTherm_ when the calendar integration has synchronised them.
- **Removed event**: the heating goes on until the event is still missing 15 minutes later, so an event which disappears during a synchronisation does not stop the heating. An event moved onto its previous time span is followed without interruption.
- **Unavailable calendar**: the events already known are kept and run until their known end.
- **Manual change**: the presets are only applied when the preheat starts and when the event ends. A preset or a temperature changed in between is kept until the next transition.
- **Timed preset and manual override**: they keep the priority and return to the scheduled preset when they end.
- **Restart**: a running preheat or event goes on after a restart of Home Assistant.
- Window, safety, power and central mode management keep their priority over the scheduled preset.

## Custom attributes

`is_calendar_configured` is `true` when the feature is configured. The `calendar_manager` section contains:

| Attribute | Meaning |
| --------- | ------- |
| `state` | `idle`, `preheat` or `event` |
| `is_calendar_available` | `false` if the last read of the calendar failed |
| `event_start`, `event_end` | The event being preheated or running |
| `previous_preset` | The preset restored at the end of the event with the **Previous preset** option |
| `missing_since` | The time since which the running event is missing from the calendar |
| `estimated_ready_time` | The estimated time at which the room reaches the temperature of the event preset |
| `next_event_start`, `preheat_start` | The next event and the planned start of its preheat |
