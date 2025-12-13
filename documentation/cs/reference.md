# Referenční dokumentace

- [Referenční dokumentace](#referenční-dokumentace)
  - [Přehled parametrů](#přehled-parametrů)
- [Senzory](#senzory)
- [Akce (Služby)](#akce-služby)
  - [Vynucení přítomnosti/obsazení](#vynucení-přítomnostiobsazení)
  - [Úprava přednastavené teploty](#úprava-přednastavené-teploty)
  - [Úprava bezpečnostních nastavení](#úprava-bezpečnostních-nastavení)
  - [Obejití kontroly okna](#obejití-kontroly-okna)
  - [Služby zamknutí / odemknutí](#služby-zamknutí--odemknutí)
  - [Change TPI Parameters](#change-tpi-parameters)
- [Události](#události)
- [Vlastní atributy](#vlastní-atributy)
- [State messages](#state-messages)

## Přehled parametrů

| Parametr                                  | Označení                                                     | "over switch" | "over climate"    | "over valve" | "central configuration" |
| ----------------------------------------- | ------------------------------------------------------------ | ------------- | ----------------- | ------------ | ----------------------- |
| ``name``                                  | Název                                                        | X             | X                 | X            | -                       |
| ``thermostat_type``                       | Typ termostatu                                               | X             | X                 | X            | -                       |
| ``temperature_sensor_entity_id``          | ID entity teplotního senzoru                                 | X             | X (auto-regulace) | X            | -                       |
| ``external_temperature_sensor_entity_id`` | ID entity externího teplotního senzoru                       | X             | X (auto-regulace) | X            | X                       |
| ``cycle_min``                             | Doba cyklu (minuty)                                          | X             | X                 | X            | -                       |
| ``temp_min``                              | Minimální povolená teplota                                   | X             | X                 | X            | X                       |
| ``temp_max``                              | Maximální povolená teplota                                   | X             | X                 | X            | X                       |
| ``device_power``                          | Výkon zařízení                                               | X             | X                 | X            | -                       |
| ``use_central_mode``                      | Povolit centralizované ovládání                              | X             | X                 | X            | -                       |
| ``use_window_feature``                    | S detekcí okna                                               | X             | X                 | X            | -                       |
| ``use_motion_feature``                    | S detekcí pohybu                                             | X             | X                 | X            | -                       |
| ``use_power_feature``                     | Se správou výkonu                                            | X             | X                 | X            | -                       |
| ``use_presence_feature``                  | S detekcí přítomnosti                                        | X             | X                 | X            | -                       |
| ``heater_entity1_id``                     | 1. topné těleso                                              | X             | -                 | -            | -                       |
| ``heater_entity2_id``                     | 2. topné těleso                                              | X             | -                 | -            | -                       |
| ``heater_entity3_id``                     | 3. topné těleso                                              | X             | -                 | -            | -                       |
| ``heater_entity4_id``                     | 4. topné těleso                                              | X             | -                 | -            | -                       |
| ``heater_keep_alive``                     | Interval obnovení spínače                                    | X             | -                 | -            | -                       |
| ``proportional_function``                 | Algoritmus                                                   | X             | -                 | -            | -                       |
| ``climate_entity1_id``                    | Podkladový termostat                                         | -             | X                 | -            | -                       |
| ``climate_entity2_id``                    | 2. podkladový termostat                                      | -             | X                 | -            | -                       |
| ``climate_entity3_id``                    | 3. podkladový termostat                                      | -             | X                 | -            | -                       |
| ``climate_entity4_id``                    | 4. podkladový termostat                                      | -             | X                 | -            | -                       |
| ``valve_entity1_id``                      | Podkladový ventil                                            | -             | -                 | X            | -                       |
| ``valve_entity2_id``                      | 2. podkladový ventil                                         | -             | -                 | X            | -                       |
| ``valve_entity3_id``                      | 3. podkladový ventil                                         | -             | -                 | X            | -                       |
| ``valve_entity4_id``                      | 4. podkladový ventil                                         | -             | -                 | X            | -                       |
| ``ac_mode``                               | Použití klimatizace (AC)?                                    | X             | X                 | X            | -                       |
| ``tpi_coef_int``                          | Koeficient pro rozdíl vnitřní teploty                        | X             | -                 | X            | X                       |
| ``tpi_coef_ext``                          | Koeficient pro rozdíl vnější teploty                         | X             | -                 | X            | X                       |
| ``frost_temp``                            | Teplota protimrazového presetem                              | X             | X                 | X            | X                       |
| ``window_sensor_entity_id``               | Senzor okna (id entity)                                      | X             | X                 | X            | -                       |
| ``window_delay``                          | Prodleva před vypnutím (sekundy)                             | X             | X                 | X            | X                       |
| ``window_auto_open_threshold``            | Vysoký práh poklesu pro automatickou detekci (°/min)         | X             | X                 | X            | X                       |
| ``window_auto_close_threshold``           | Nízký práh poklesu pro automatickou detekci uzavření (°/min) | X             | X                 | X            | X                       |
| ``window_auto_max_duration``              | Maximální doba automatického vypnutí (minuty)                | X             | X                 | X            | X                       |
| ``motion_sensor_entity_id``               | ID entity senzoru pohybu                                     | X             | X                 | X            | -                       |
| ``motion_delay``                          | Prodleva před zvážením pohybu (sekundy)                      | X             | X                 | X            | -                       |
| ``motion_off_delay``                      | Prodleva před koncem pohybu (sekundy)                        | X             | X                 | X            | X                       |
| ``motion_preset``                         | Preset pro použití při detekci pohybu                        | X             | X                 | X            | X                       |
| ``no_motion_preset``                      | Preset pro použití při žádném pohybu                         | X             | X                 | X            | X                       |
| ``power_sensor_entity_id``                | Senzor celkového výkonu (id entity)                          | X             | X                 | X            | X                       |
| ``max_power_sensor_entity_id``            | Senzor max výkonu (id entity)                                | X             | X                 | X            | X                       |
| ``power_temp``                            | Teplota během odlehčení zátěže                               | X             | X                 | X            | X                       |
| ``presence_sensor_entity_id``             | ID entity senzoru přítomnosti (true pokud je někdo přítomen) | X             | X                 | X            | -                       |
| ``minimal_activation_delay``              | Minimální doba aktivace                                      | X             | -                 | -            | X                       |
| ``minimal_deactivation_delay``            | Minimální doba deaktivace                                    | X             | -                 | -            | X                       |
| ``safety_delay_min``                      | Maximální prodleva mezi dvěma teplotními měřeními            | X             | -                 | X            | X                       |
| ``safety_min_on_percent``                 | Minimální procento výkonu pro vstup do bezpečnostního režimu | X             | -                 | X            | X                       |
| ``auto_regulation_mode``                  | Režim auto-regulace                                          | -             | X                 | -            | -                       |
| ``auto_regulation_dtemp``                 | Práh auto-regulace                                           | -             | X                 | -            | -                       |
| ``auto_regulation_period_min``            | Minimální období auto-regulace                               | -             | X                 | -            | -                       |
| ``inverse_switch_command``                | Invertovat příkaz spínače (pro spínače s pilotem)            | X             | -                 | -            | -                       |
| ``auto_fan_mode``                         | Automatický režim ventilátoru                                | -             | X                 | -            | -                       |
| ``auto_regulation_use_device_temp``       | Použití vnitřní teploty podkladového zařízení                | -             | X                 | -            | -                       |
| ``use_central_boiler_feature``            | Přidat ovládání centrálního kotle                            | -             | -                 | -            | X                       |
| ``central_boiler_activation_service``     | Služba aktivace kotle                                        | -             | -                 | -            | X                       |
| ``central_boiler_deactivation_service``   | Služba deaktivace kotle                                      | -             | -                 | -            | X                       |
| ``central_boiler_activation_delay_sec``   | Verzögerung bei der Aktivierung (Sekunden)                   | -             | -                 | -            | X                       |
| ``used_by_controls_central_boiler``       | Indikuje, zda VTherm ovládá centrální kotel                  | X             | X                 | X            | -                       |
| ``use_auto_start_stop_feature``           | Indikuje, zda je povolena funkce auto start/stop             | -             | X                 | -            | -                       |
| ``auto_start_stop_level``                 | Úroveň detekce pro auto start/stop                           | -             | X                 | -            | -                       |

# Senzory

S termostatem jsou k dispozici senzory pro vizualizaci upozornění a vnitřního stavu termostatu. Ty jsou k dispozici v entitách zařízení přidruženého k termostatu:

![image](images/thermostat-sensors.png)

V pořadí jsou:
1. hlavní entita ``climate`` pro ovládání termostatu,
2. entita umožňující funkci auto-start/stop,
3. entita umožňující _VTherm_ sledovat změny v podkladovém zařízení,
4. energie spotřebovaná termostatem (hodnota, která se neustále zvyšuje),
5. čas přijetí poslední vnější teploty,
6. čas přijetí poslední vnitřní teploty,
7. průměrný výkon zařízení během cyklu (pouze pro TPI),
8. čas strávený ve vypnutém stavu během cyklu (pouze TPI),
9. čas strávený v zapnutém stavu během cyklu (pouze TPI),
10. stav odlehčení zátěže,
11. procento výkonu během cyklu (pouze TPI),
12. stav přítomnosti (pokud je nakonfigurována správa přítomnosti),
13. bezpečnostní stav,
14. stav okna (pokud je nakonfigurována správa okna),
15. stav pohybu (pokud je nakonfigurována správa pohybu),
16. procento otevření ventilu (pro typ `over_valve`),

Přítomnost těchto entit závisí na tom, zda je přidružená funkce povolena.

Pro obarvení senzorů přidejte tyto řádky a podle potřeby je přizpůsobte ve vašem `configuration.yaml`:

```yaml
frontend:
  themes:
    versatile_thermostat_theme:
      state-binary_sensor-safety-on-color: "#FF0B0B"
      state-binary_sensor-power-on-color: "#FF0B0B"
      state-binary_sensor-window-on-color: "rgb(156, 39, 176)"
      state-binary_sensor-motion-on-color: "rgb(156, 39, 176)"
      state-binary_sensor-presence-on-color: "lightgreen"
      state-binary_sensor-running-on-color: "orange"
```

a vyberte téma ```versatile_thermostat_theme``` v konfiguraci panelu. Dostanete něco takového:

![image](images/colored-thermostat-sensors.png)

# Akce (Služby)

Tato vlastní implementace nabízí specifické akce (služby) pro usnadnění integrace s ostatními komponentami Home Assistant.

## Vynucení přítomnosti/obsazení
Tato služba vám umožňuje vynutit stav přítomnosti nezávisle na senzoru přítomnosti. To může být užitečné, pokud chcete spravovat přítomnost prostřednictvím služby spíše než senzoru. Například můžete použít svůj alarm pro vynucení nepřítomnosti, když je zapnut.

Kód pro volání této služby je následující:

```yaml
service: versatile_thermostat.set_presence
data:
    presence: "off"
target:
    entity_id: climate.my_thermostat
```

## Úprava přednastavené teploty
Tato služba je užitečná, pokud chcete dynamicky změnit přednastavenou teplotu. Místo přepínání presetů některé případy použití vyžadují úpravu teploty presetem. Tímto způsobem můžete zachovat plánovač nezměněný pro správu presetem při úpravě teploty presetem.
Pokud je upravený preset aktuálně vybrán, změna cílové teploty je okamžitá a bude aplikována v dalším výpočetním cyklu.

Můžete upravit jednu nebo obě teploty (při přítomnosti nebo nepřítomnosti) každého presetem.

Použijte následující kód pro nastavení teploty presetem:
```yaml
service: versatile_thermostat.set_preset_temperature
data:
    preset: boost
    temperature: 17.8
    temperature_away: 15
target:
    entity_id: climate.my_thermostat
```

Nebo pro změnu presetem pro režim klimatizace (AC) přidejte prefix `_ac` k názvu presetem takto:
```yaml
service: versatile_thermostat.set_preset_temperature
data:
    preset: boost_ac
    temperature: 25
    temperature_away: 30
target:
    entity_id: climate.my_thermostat
```

> ![Tip](images/tips.png) _*Poznámky*_
>
>    - Po restartu jsou presety resetovány na nakonfigurovanou teplotu. Pokud chcete, aby byla vaše změna trvalá, musíte upravit teplotu presetem v konfiguraci integrace.

## Úprava bezpečnostních nastavení
Tato služba vám umožňuje dynamicky upravit bezpečnostní nastavení popsaná zde [Pokročilá konfigurace](#pokročilá-konfigurace).
Pokud je termostat v režimu ``security``, nová nastavení se aplikují okamžitě.

Pro změnu bezpečnostních nastavení použijte následující kód:
```yaml
service: versatile_thermostat.set_safety
data:
    min_on_percent: "0.5"
    default_on_percent: "0.1"
    delay_min: 60
target:
    entity_id: climate.my_thermostat
```

## Obejití kontroly okna
Tato služba vám umožňuje povolit nebo zakázat obejití kontroly okna.
Umožňuje termostatu pokračovat v vytápění, i když je okno detekováno jako otevřené.
Když je nastaveno na ``true``, změny stavu okna již nebudou ovlivňovat termostat. Když je nastaveno na ``false``, termostat bude deaktivován, pokud je okno stále otevřené.

Pro změnu nastavení obejití použijte následující kód:
```yaml
service: versatile_thermostat.set_window_bypass
data:
    bypass: true
target:
    entity_id: climate.my_thermostat
```

## Služby zamknutí / odemknutí

Tyto služby umožňují uzamknout termostat, aby se zabránilo změnám konfigurace, nebo jej opět odemknout a povolit úpravy:

- `versatile_thermostat.lock` - Uzamkne termostat a brání změnám konfigurace
- `versatile_thermostat.unlock` - Odemkne termostat a znovu povolí změny konfigurace

Podrobnosti viz [Funkce zámku](feature-lock.md).
## Change TPI Parameters
All TPI parameters configurable here can be modified by a service. These changes are persistent and survive a restart. They are applied immediately and a thermostat update is performed instantly when parameters are changed.

Each parameter is optional. If it is not provided its current value is kept.

To change the TPI parameters use the following code:

```
action: versatile_thermostat.set_tpi_parameters
data:
  tpi_coef_int: 0.5
  tpi_coef_ext: 0.01
  minimal_activation_delay: 10
  minimal_deactivation_delay: 10
  tpi_threshold_low: -2
  tpi_threshold_high: 5
target:
  entity_id: climate.sonoff_trvzb
```

# Události
Klíčové události termostatu jsou oznámeny prostřednictvím sběrnice zpráv.
Jsou oznámeny následující události:

- ``versatile_thermostat_safety_event``: termostat vstupuje nebo opouští preset ``security``
- ``versatile_thermostat_power_event``: termostat vstupuje nebo opouští preset ``power``
- ``versatile_thermostat_temperature_event``: jedno nebo obě teplotní měření termostatu nebyly aktualizovány po dobu více než `safety_delay_min`` minut
- ``versatile_thermostat_hvac_mode_event``: termostat je zapnut nebo vypnut. Tato událost je také vysílána při spuštění termostatu
- ``versatile_thermostat_preset_event``: na termostatu je vybrán nový preset. Tato událost je také vysílána při spuštění termostatu
- ``versatile_thermostat_central_boiler_event``: událost indikující změnu stavu kotle
- ``versatile_thermostat_auto_start_stop_event``: událost indikující zastavení nebo restart provedené funkcí auto-start/stop

Pokud jste sledovali, když termostat přepne do bezpečnostního režimu, spustí se 3 události:
1. ``versatile_thermostat_temperature_event`` pro indikaci, že teploměr již neodpovídá,
2. ``versatile_thermostat_preset_event`` pro indikaci přepnutí na preset ``security``,
3. ``versatile_thermostat_hvac_mode_event`` pro indikaci potenciálního vypnutí termostatu

Každá událost nese klíčové hodnoty události (teploty, aktuální preset, aktuální výkon, ...) i stavy termostatu.

Tyto události můžete snadno zachytit v automatizaci, například pro upozornění uživatelů.

# Vlastní atributy

Pro úpravu algoritmu máte přístup k celému kontextu viděnému a vypočítanému termostatem prostřednictvím vyhrazených atributů. Tyto atributy můžete zobrazit (a použít) v sekci "Developer Tools / States" HA. Zadejte svůj termostat a uvidíte něco takového:
![image](images/dev-tools-climate.png)

Vlastní atributy jsou následující:

> see updated list on English version - please translate

| Atribut                            | Význam                                                                                                                 |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| ``hvac_modes``                     | Seznam režimů podporovaných termostatem                                                                                |
| ``temp_min``                       | Minimální teplota                                                                                                      |
| ``temp_max``                       | Maximální teplota                                                                                                      |
| ``preset_modes``                   | Presety viditelné pro tento termostat. Skryté presety zde nejsou zobrazeny                                             |
| ``temperature_actuelle``           | Aktuální teplota jak je hlášena senzorem                                                                               |
| ``temperature``                    | Cílová teplota                                                                                                         |
| ``action_hvac``                    | Akce aktuálně prováděná topným tělesem. Může být idle, heating                                                         |
| ``preset_mode``                    | Aktuálně vybraný preset. Může být jeden z 'preset_modes' nebo skrytý preset jako power                                 |
| ``[eco/confort/boost]_temp``       | Teplota nakonfigurovaná pro preset xxx                                                                                 |
| ``[eco/confort/boost]_away_temp``  | Teplota nakonfigurovaná pro preset xxx při deaktivované přítomnosti nebo not_home                                      |
| ``temp_power``                     | Teplota používaná během detekce ztráty                                                                                 |
| ``on_percent``                     | Vypočítané procento zapnutí algoritmem TPI                                                                             |
| ``on_time_sec``                    | Doba zapnutí v sekundách. Měla by být ```on_percent * cycle_min```                                                     |
| ``off_time_sec``                   | Doba vypnutí v sekundách. Měla by být ```(1 - on_percent) * cycle_min```                                               |
| ``cycle_min``                      | Výpočetní cyklus v minutách                                                                                            |
| ``function``                       | Algoritmus používaný pro výpočet cyklu                                                                                 |
| ``tpi_coef_int``                   | ``coef_int`` algoritmu TPI                                                                                             |
| ``tpi_coef_ext``                   | ``coef_ext`` algoritmu TPI                                                                                             |
| ``window_state``                   | Poslední známý stav senzoru okna. None pokud okno není nakonfigurováno                                                 |
| ``is_window_bypass``               | True pokud je povoleno obejití detekce otevřeného okna                                                                 |
| ``motion_state``                   | Poslední známý stav senzoru pohybu. None pokud detekce pohybu není nakonfigurována                                     |
| ``overpowering_state``             | Poslední známý stav senzoru přetížení. None pokud správa výkonu není nakonfigurována                                   |
| ``presence_state``                 | Poslední známý stav senzoru přítomnosti. None pokud detekce přítomnosti není nakonfigurována                           |
| ``safety_delay_min``               | Prodleva před aktivací bezpečnostního režimu při přestání posílat měření jedním ze dvou teplotních senzorů             |
| ``safety_min_on_percent``          | Procento vytápění, pod kterým termostat nepřepne do bezpečnostního režimu                                              |
| ``safety_default_on_percent``      | Procento vytápění používané při bezpečnostním režimu termostatu                                                        |
| ``last_temperature_datetime``      | Datum a čas v ISO8866 formátu posledního přijetí vnitřní teploty                                                       |
| ``last_ext_temperature_datetime``  | Datum a čas v ISO8866 formátu posledního přijetí vnější teploty                                                        |
| ``safety_state``                   | Bezpečnostní stav. True nebo false                                                                                     |
| ``minimal_activation_delay_sec``   | Minimální doba aktivace v sekundách                                                                                    |
| ``minimal_deactivation_delay_sec`` | Minimální doba deaktivace v sekundách                                                                                  |
| ``last_update_datetime``           | Datum a čas v ISO8866 formátu tohoto stavu                                                                             |
| ``friendly_name``                  | Název termostatu                                                                                                       |
| ``supported_features``             | Kombinace všech funkcí podporovaných tímto termostatem. Viz oficiální dokumentace climate integrace pro více informací |
| ``valve_open_percent``             | Procento otevření ventilu                                                                                              |
| ``regulated_target_temperature``   | Cílová teplota vypočítaná samo-regulací                                                                                |
| ``is_inversed``                    | True pokud je ovládání invertováno (pilot s diodou)                                                                    |
| ``is_controlled_by_central_mode``  | True pokud lze VTherm centrálně ovládat                                                                                |
| ``last_central_mode``              | Poslední použitý centrální režim (None pokud VTherm není centrálně ovládán)                                            |
| ``is_used_by_central_boiler``      | Indikuje, zda VTherm může ovládat centrální kotel                                                                      |
| ``auto_start_stop_enable``         | Indikuje, zda má VTherm povoleno auto start/stop                                                                       |
| ``auto_start_stop_level``          | Indikuje úroveň auto start/stop                                                                                        |
| ``hvac_off_reason``                | Indikuje důvod vypnutého stavu termostatu (hvac_off). Může být Window, Auto-start/stop, nebo Manual                    |
| ``last_change_time_from_vtherm``   | Datum a čas poslední změny provedené VTherm                                                                            |
| ``nb_device_actives``              | Počet podkladových zařízení viděných jako aktivní                                                                      |
| ``device_actives``                 | Seznam podkladových zařízení viděných jako aktivní                                                                     |


Tyto atributy budou vyžadovány, když budete potřebovat pomoc.

# State messages

The `specific_states.messages` custom attribute contains a list of message codes that explain the current state. Messages can be:
| Code                                | Meaning                                                                             |
| ----------------------------------- | ----------------------------------------------------------------------------------- |
| `overpowering_detected`             | An overpowering situation is detected                                               |
| `safety_detected`                   | A temperature measurement fault is detected that triggered VTherm safety mode       |
| `target_temp_window_eco`            | Window detection forced the target temperature to the Eco preset                    |
| `target_temp_window_frost`          | Window detection forced the target temperature to the Frost preset                  |
| `target_temp_power`                 | Power shedding forced the target temperature with the value configured for shedding |
| `target_temp_central_mode`          | The target temperature was forced by central mode                                   |
| `target_temp_activity_detected`     | The target temperature was forced by motion detection                               |
| `target_temp_activity_not_detected` | The target temperature was forced by no motion detection                            |
| `target_temp_absence_detected`      | The target temperature was forced by absence detection                              |

Note: these messages are available in the [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card) under the information icon.