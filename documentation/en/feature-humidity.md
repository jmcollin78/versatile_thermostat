# Humidity Control

- [Humidity Control](#humidity-control)
  - [Configure Humidity Control](#configure-humidity-control)
  - [How It Works](#how-it-works)

## Configure Humidity Control

If this feature is selected, it allows you to automatically switch your AC to DRY mode when humidity is too high and cooling is not needed. This feature is only available for AC mode thermostats (`over_climate` type) where the underlying AC device supports DRY mode.

To configure humidity control, fill out this form:

![image](images/config-humidity.png)

For this, you need to configure:
- A **humidity sensor** entity (sensor or input_number) that provides humidity as a percentage value
- A **humidity threshold** (default: 60%) - when humidity exceeds this value, DRY mode will be activated

You can use either:
- A specific humidity sensor for this VTherm, or
- The central humidity configuration (threshold only, sensor must be configured per VTherm)

## How It Works

When the AC is in COOL mode and the temperature is at or near the target (cooling is not actively needed), the system monitors the humidity level:

1. **If humidity exceeds the threshold** and cooling is not needed (`on_percent <= 0.05`), the AC automatically switches to **DRY mode** for efficient dehumidification.

2. **If temperature rises** and cooling becomes needed (`on_percent > 0.05`), the AC switches back to **COOL mode** to prioritize temperature control over humidity control.

This ensures that:
- Temperature control always takes priority when cooling is needed
- Energy-efficient dehumidification occurs when temperature is already at target
- The system automatically switches between COOL and DRY modes based on conditions

> ![Tip](images/tips.png) _*Notes*_
>
> 1. This feature only works with AC mode thermostats (`ac_mode` enabled).
> 2. The underlying AC device must support DRY mode for this feature to work.
> 3. The humidity sensor should provide values as a percentage (0-100%).
> 4. The default threshold of 60% is a good starting point, but you may want to adjust it based on your comfort preferences and local climate conditions.
