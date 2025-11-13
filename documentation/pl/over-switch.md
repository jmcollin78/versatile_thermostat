# Typ termostatu `Termostat na Przełączniku`

- [Typ termostatu `Termostat na Przełączniku`](#over_switch-type-thermostat)
  - [Wymagania wstępne](#prerequisites)
  - [Konfiguracja](#configuration)
    - [Podstawowe urządzenia](#the-underlying-devices)
    - [Podtrzymanie aktywności (keep-alive)](#keep-alive)
    - [Tryb AC](#ac-mode)
    - [Inwersja poleceń](#command-inversion)
    - [Dostosowywanie poleceń](#command-customization)


## Wymagania wstępne

Instalacja powinna wyglądać następująco:

![installation `over_switch`](images/over-switch-schema.png)

1. Ustawienia temperatury docelowej pomieszczenia mogą być realizowane przez użytkownika, automatyzacje, wcześniej zdefiniowany harmonogram, lub mogą pochodzić z ustawień wstępnych integracji.
2. Termometr wewnętrzny (2) lub termometr zewnętrzny (2b) okresowo odczytują temperaturę. Termometr wewnętrzny powinien być umieszczony w odpowiednim miejscu — najlepiej na środku pomieszczenia. Unikaj umieszczania go zbyt blisko okna, termostatu lub grzejnika.
3. Na podstawie wartości zadanych, różnicy temperatur oraz parametrów algorytmu **TPI** (zobacz: [TPI](algorithms.md#lalgorithme-tpi), termostat _VTherm_ obliczy procentowy czas włączenia.
4. Następnie w regularnych odstępach czasu termostat _VTherm_ będzie wydawał polecenia załączania i wyłączania dla encji podrzędnych typu `switch`, `select` lub `climate`.
5. Te encje podrzędne będą sterować fizycznym urządzeniem.
6. Fizyczny przełącznik będzie włączał lub wyłączał grzejnik.  

> Wartość `on-time` jest przeliczana przy każdym cyklu na nowo, co umozliwia regulację temperatury pomieszczenia.
>
> ![image](images/on-switch-diagram.png)

## Konfiguracja

First, configure the main settings common to all _VTherms_ (see [main settings](base-attributes.md)).
Then, click on the "Underlying Entities" option from the menu, and you will see this configuration page:

![image](images/config-linked-entity.png)

### Podstawowe urządzenia

In the "list of devices to control," you add the switches that will be controlled by VTherm. Only entities of type `switch`, `input_boolean`, `select`, `input_select`, or `climate` are accepted.

If one of the underlying devices is not a `switch`, then command customization is mandatory. By default, for `switch` entities, the commands are the standard switch on/off commands (`turn_on`, `turn_off`).

The algorithm currently available is TPI. See [algorithm](#algorithm).
If multiple entities are configured, the thermostat staggers the activations to minimize the number of switches on at any given time. This allows for better power distribution, as each radiator will turn on in turn.

VTherm will smooth the consumed power as much as possible by alternating activations. Example of staggered activations:

![image](images/multi-switch-activation.png)

Of course, if the requested power (`on_percent`) is too high, there will be an overlap of activations.

### Podtrzymanie aktywności (keep-alive)

Some equipment requires periodic activation to prevent a safety shutdown. Known as "keep-alive," this function can be activated by entering a non-zero number of seconds in the thermostat's keep-alive interval field. To disable the function or if in doubt, leave it empty or enter zero (default value).

### Tryb AC

It is possible to choose a `thermostat_over_switch` to control an air conditioner by checking the "AC Mode" box. In this case, only the cooling mode will be visible.

### Inwersja poleceń

If your equipment is controlled by a pilot wire with a diode, you may need to check the "Invert the Command" box. This will set the switch to `On` when you need to turn off the equipment and to `Off` when you need to turn it on. The cycle times will be inverted with this option.

### Dostosowywanie poeceń

This configuration section allows you to customize the on and off commands sent to the underlying device.
These commands are mandatory if one of the underlying devices is not a `switch` (for `switch` entities, standard on/off commands are used).

To customize the commands, click on `Add` at the bottom of the page for both the on and off commands:

![virtual switch](images/config-vswitch1.png)

Then, specify the on and off commands using the format `command[/attribute[:value]]`.
The available commands depend on the type of underlying device:

| Underlying Device Type      | Possible On Commands                  | Possible Off Commands                          | Applies To                        |
| --------------------------- | ------------------------------------- | ---------------------------------------------- | --------------------------------- |
| `switch` or `input_boolean` | `turn_on`                             | `turn_off`                                     | All switches                      |
| `select` or `input_select`  | `select_option/option:comfort`        | `select_option/option:frost_protection`        | Nodon SIN-4-FP-21 and similar (*) |
| `climate` (hvac_mode)       | `set_hvac_mode/hvac_mode:heat`        | `set_hvac_mode/hvac_mode:off`                  | eCosy (via Tuya Local)            |
| `climate` (preset)          | `set_preset_mode/preset_mode:comfort` | `set_preset_mode/preset_mode:frost_protection` | Heatzy (*)                        |

(*) Check the values accepted by your device in **Developer Tools / States** and search for your device. You will see the options it supports. They must be identical, including case sensitivity.

Of course, these examples can be adapted to your specific case.

Example for a Nodon SIN-4-FP-21:
![virtual switch Nodon](images/config-vswitch2.png)

Click "Validate" to confirm the modifications.

If the following error occurs:

> The command customization configuration is incorrect. It is required for non-switch underlying devices, and the format must be 'service_name[/attribute:value]'. More details in the README.

This means that one of the entered commands is invalid. The following rules must be followed:
1. Each command must follow the format `command[/attribute[:value]]` (e.g., `select_option/option:comfort` or `turn_on`) without spaces or special characters except `_`.
2. There must be as many commands as there are declared underlying devices, except when all underlying devices are `switch` entities, in which case command customization is not required.
3. If multiple underlying devices are configured, the commands must be in the same order. The number of on commands must equal the number of off commands and the number of underlying devices (in the correct order). It is possible to mix different types of underlying devices. As soon as one underlying device is not a `switch`, all commands for all underlying devices, including `switch` entities, must be configured.
