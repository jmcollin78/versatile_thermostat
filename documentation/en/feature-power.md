# Power Management - Load Shedding

- [Power Management - Load Shedding](#power-management---load-shedding)
  - [Configure Power Management](#configure-power-management)

This feature allows you to regulate the electricity consumption of your heaters. Known as load shedding, this feature enables you to limit the electrical consumption of your heating device if overcapacity conditions are detected.
You will need a **sensor for the total instantaneous power consumption** of your home, as well as a **sensor for the maximum allowed power**.

The behavior of this feature is basic:
1. when the _VTherm_ is about to turn on a device,
2. it compares the last known value of the power consumption sensor with the last value of the maximum allowed power. If there is a remaining margin greater than or equal to the declared power of the _VTherm_'s devices, then the _VTherm_ and its devices will be turned on. Otherwise, they will remain off until the next cycle.

WARNING: This very basic operation **is not a safety function** but more of an optimization feature to manage consumption at the cost of heating performance. Overloads may occur depending on the frequency of updates from your consumption sensors, and the actual power used by your devices. Therefore, you must always maintain a safety margin.

Typical use case:
1. you have an electricity meter limited to 11 kW,
2. you occasionally charge an electric vehicle at 5 kW,
3. that leaves 6 kW for everything else, including heating,
4. you have 1 kW of other equipment running,
5. you have declared a sensor (`input_number`) for the maximum allowed power at 9 kW (= 11 kW - the reserve for other devices - margin)

If the vehicle is charging, the total power consumed is 6 kW (5+1), and a _VTherm_ will only turn on if its declared power is 3 kW max (9 kW - 6 kW).
If the vehicle is charging and another _VTherm_ of 2 kW is running, the total power consumed is 8 kW (5+1+2), and a _VTherm_ will only turn on if its declared power is 1 kW max (9 kW - 8 kW). Otherwise, it will wait until the next cycle.

If the vehicle is not charging, the total power consumed is 1 kW, and a _VTherm_ will only turn on if its declared power is 8 kW max (9 kW - 1 kW).

## Configure Power Management

If you have chosen the `With power detection` feature, configure it as follows:

![image](images/config-power.png)

1. the entity ID of the **instantaneous power consumption sensor** for your home,
2. the entity ID of the **maximum allowed power sensor**,
3. the temperature to apply if load shedding is activated.

Note that all power values must have the same units (kW or W, for example).
Having a **maximum allowed power sensor** allows you to adjust the maximum power over time using a scheduler or automation.

> ![Tip](images/tips.png) _*Notes*_
>
> 1. In case of load shedding, the radiator is set to the preset named `power`. This is a hidden preset, and you cannot select it manually.
> 2. Always keep a margin, as the maximum power may briefly be exceeded while waiting for the next cycle calculation, or due to unregulated equipment.
> 3. If you don't want to use this feature, uncheck it in the 'Functions' menu.
> 4. If a _VTherm_ controls multiple devices, the **electrical consumption of your heating** must match the sum of the powers.
> 5. If you are using the Versatile Thermostat UI card (see [here](additions.md#much-better-with-the-versatile-thermostat-ui-card)), load shedding is represented as follows: ![load shedding](images/power-exceeded-icon.png).