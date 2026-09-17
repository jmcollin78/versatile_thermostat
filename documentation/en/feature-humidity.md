# External humidity sensor

VTherm can expose `current_humidity` from an external sensor for `over_switch`, `over_valve`, and `over_climate` thermostats.

Open **Humidity** from the thermostat configuration menu, enable the option, then select a sensor. Leaving the sensor empty uses the humidity sensor automatically detected on the same device as the configured room-temperature sensor. Disable the option to stop using external or detected sensors.

The selected source is read at startup and on every state change. Invalid, unavailable, and unknown values are exposed as unavailable humidity; humidity does not affect temperature regulation. For `over_climate`, when no external source is active, the underlying climate humidity remains in use.
