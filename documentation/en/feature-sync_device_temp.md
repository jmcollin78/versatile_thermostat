# Internal Device Temperature Synchronization

- [Internal Device Temperature Synchronization](#internal-device-temperature-synchronization)
  - [Principle](#principle)
  - [Prerequisites](#prerequisites)
  - [Configuration](#configuration)
  - [Synchronization Mode](#synchronization-mode)
    - [Mode 1: Using a Calibration Entity](#mode-1-using-a-calibration-entity)
      - [Mode 2: Direct Copy of External Temperature](#mode-2-direct-copy-of-external-temperature)

## Principle

This function allows synchronizing the internal temperature of underlying devices in two different ways for a `over_climate` type VTherm. Basically, it allows using a remote thermometer if your device supports it. It is particularly useful for thermostatic radiator valves (TRV) that have their own integrated temperature sensor. It will greatly improve the internal regulation of underlying `over_climate` type devices that support it.

The two available synchronization modes are:
1. Mode 1 - **Use calibration offset**: VTherm uses the device's internal calibration offset entity to compensate for the difference with the room temperature,
2. Mode 2 - **Synchronize temperature directly with the device**: VTherm sends the room temperature directly to the device so that it uses it in its own regulation.

The choice will depend on what your underlying device can do.
For example:
1. the Sonoff TRVZB can do both. You will use either the calibration offset via the exposed entity with a compass, or the named external temperature (`external_temperature_input`). Be careful to set the `sensor_select` option to `external` in this case,
2. the Aqara W600 only has the calibration entity (the icon is a compass by default)

## Prerequisites

This function requires:
1. a `over_climate` type VTherm,
2. for mode 1: a device that supports the `local_temperature_calibration` entity or equivalent allowing to calibrate its internal temperature,
3. for mode 2: a device that supports the `external_temperature_input` entity or equivalent.

> ![Tip](images/tips.png) _*Notes*_
> - This function is not available for `over_switch` or `over_valve` type VTherms which do not have an underlying climate device.
> - Check your devices' compatibility to choose the right mode.

## Configuration

The configuration of this function is done in two steps.

In the underlying configuration, you indicate that your devices are equipped with one of the 2 internal temperature synchronization functions by checking the appropriate option:

![image](images/config-synchronize-device-temp.png)

This adds a menu called `Synchronisation de la température de l'appareil` that must be configured:

![image](images/config-synchro.png)

You must check the `Application d'un calibrage` option to choose option 1. Otherwise option 2 will be applied.
Then you provide the list of entities to control:
1. either the list of `local_temperature_calibration` entities if you are in case 1,
2. or the list of `external_temperature_input` entities if you are in case 2.

The entities must be in the order of declaration of the underlying devices and there must be the same number.

> ![Tip](images/tips.png) _*Notes*_
> - The two modes are mutually exclusive. You can only activate one at a time.
> - It is not possible to mix two synchronization methods within the same _VTherm_. You must use 2 _VTherms_ if you need to.
> - In the case of method 2, your device may need additional configuration. Since this configuration is device-dependent, it is not handled by _VTherm_. For example, on the Sonoff TRVZB, the `select.xxx_sensor_select` option must be set to `external`.

## Synchronization Mode

### Mode 1: Using a Calibration Entity

In this method, you must provide the `number` entity that allows calibrating the temperature offset of your device. This entity is generally named `local_temperature_calibration` or `temperature_calibration_offset`.

VTherm:
1. retrieves the device's internal temperature,
2. calculates the necessary offset: `offset = room_temperature - internal_temperature`,
3. sends this offset to the provided calibration entity via the `number.set_value` service.

**Example**:
- Room temperature (external sensor): 19°C
- TRV internal temperature: 21°C
- Calculated offset: 19°C - 21°C = -2°C
- The -2°C offset is added to the current offset and is sent to the `number.salon_trv_local_temperature_calibration` entity

**Advantages**:
- The device regulates with the actual room temperature,
- Avoids oscillations due to compensation,
- Works with all devices exposing a calibration `number` entity,
- The calibration is sent each time a new temperature is received from the room sensor independently of the _VTherm_ calculation cycle.

### Mode 2: Direct Copy of External Temperature

In this method, VTherm directly sends the room temperature to the device using the `external_temperature_input` entity or equivalent.

VTherm:
1. retrieves the room temperature from its external sensor,
2. calls `number.set_value` with the room temperature as value

**Example**:
- VTherm target temperature: 20°C
- Room temperature: 19°C
- VTherm sends: `number.set_value(19)` on the `external_temperature_input` entity
- The device directly receives the room temperature

**Advantages**:
- Simplest method,
- Works with certain devices that accept the `external_temperature_input` parameter,
- The device can directly use this temperature for its regulation,
- The temperature is sent each time a new temperature is received from the room sensor independently of the _VTherm_ calculation cycle.


**Disadvantages**:
- **Few devices support this method**: few devices have this option,
- Mainly works with certain specific Zigbee devices (e.g., Sonoff TRVZB),
- The use of this temperature is often related to another configuration.
