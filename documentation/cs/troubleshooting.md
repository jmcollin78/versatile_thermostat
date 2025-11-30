# Řešení problémů

- [Řešení problémů](#řešení-problémů)
  - [Použití Heatzy](#použití-heatzy)
  - [Použití radiátoru s pilotním drátem (Nodon SIN-4-FP-21)](#použití-radiátoru-s-pilotním-drátem-nodon-sin-4-fp-21)
  - [Použití systému Netatmo](#použití-systému-netatmo)
  - [Topí jen první radiátor](#topí-jen-první-radiátor)
  - [Radiátor topí, i když je překročena cílová teplota, nebo netopí, když je teplota místnosti výrazně pod cílem](#radiátor-topí-i-když-je-překročena-cílová-teplota-nebo-netopí-když-je-teplota-místnosti-výrazně-pod-cílem)
    - [Typ `over_switch` nebo `over_valve`](#typ-over_switch-nebo-over_valve)
    - [Typ `over_climate`](#typ-over_climate)
  - [Úprava parametrů detekce otevřených oken v auto režimu](#úprava-parametrů-detekce-otevřených-oken-v-auto-režimu)
  - [Proč můj Versatile Thermostat přechází do bezpečnostního režimu?](#proč-můj-versatile-thermostat-přechází-do-bezpečnostního-režimu)
    - [Jak detekovat bezpečnostní režim?](#jak-detekovat-bezpečnostní-režim)
    - [Jak být upozorněn, když se to stane?](#jak-být-upozorněn-když-se-to-stane)
    - [Jak to opravit?](#jak-to-opravit)
  - [Použití skupiny osob jako senzoru přítomnosti](#použití-skupiny-osob-jako-senzoru-přítomnosti)
  - [Povolení logů pro Versatile Thermostat](#povolení-logů-pro-versatile-thermostat)
  - [VTherm nesleduje změny setpointu provedené přímo na podkladovém zařízení (`over_climate`)](#vtherm-nesleduje-změny-setpointu-provedené-přímo-na-podkladovém-zařízení-over_climate)
  - [VTherm automaticky přepíná do režimu 'Chlazení' nebo 'Vytápění'](#vtherm-automaticky-přepíná-do-režimu-chlazení-nebo-vytápění)
  - [Detekce otevřených oken nebrání změnám preset](#detekce-otevřených-oken-nebrání-změnám-preset)
    - [Příklad:](#příklad)


## Použití Heatzy

Heatzy je nyní nativně podporováno _VTherm_. Viz [Rychlý start](quick-start.md#heatzy-ecosy-nebo-podobný-climate-entita).

Tato konfigurace je zachována pouze pro referenci.

Použití Heatzy nebo Nodon je možné za podmínky, že použijete virtuální spínač s tímto modelem:

```yaml
- platform: template
  switches:
    chauffage_sdb:
      unique_id: chauffage_sdb
      friendly_name: Bathroom heating
      value_template: "{{ is_state_attr('climate.bathroom', 'preset_mode', 'comfort') }}"
      icon_template: >-
        {% if is_state_attr('climate.bathroom', 'preset_mode', 'comfort') %}
          mdi:radiator
        {% elif is_state_attr('climate.bathroom', 'preset_mode', 'away') %}
          mdi:snowflake
        {% else %}
          mdi:radiator-disabled
        {% endif %}
      turn_on:
        service: climate.set_preset_mode
        entity_id: climate.bathroom
        data:
          preset_mode: "comfort"
      turn_off:
        service: climate.set_preset_mode
        entity_id: climate.bathroom
        data:
          preset_mode: "eco"
```
Díky @gael za tento příklad.

## Použití radiátoru s pilotním drátem (Nodon SIN-4-FP-21)

Nodon je nyní nativně podporováno _VTherm_. Viz [Rychlý start](quick-start.md#nodon-sin-4-fp-21-nebo-podobný-pilotní-drát).

Tato konfigurace je zachována pouze pro referenci.


Stejně jako u Heatzy výše můžete použít virtuální spínač, který změní preset vašeho radiátoru na základě stavu zapnuto/vypnuto VTherm.
Příklad:

```yaml
- platform: template
  switches:
    chauffage_chb_parents:
      unique_id: chauffage_chb_parents
      friendly_name: Chauffage chambre parents
      value_template: "{{ is_state('select.fp_chb_parents_pilot_wire_mode', 'comfort') }}"
      icon_template: >-
        {% if is_state('select.fp_chb_parents_pilot_wire_mode', 'comfort') %}
          mdi:radiator
        {% elif is_state('select.fp_chb_parents_pilot_wire_mode', 'frost_protection') %}
          mdi:snowflake
        {% else %}
          mdi:radiator-disabled
        {% endif %}
      turn_on:
        service: select.select_option
        target:
          entity_id: select.fp_chb_parents_pilot_wire_mode
        data:
          option: comfort
      turn_off:
        service: select.select_option
        target:
          entity_id: select.fp_chb_parents_pilot_wire_mode
        data:
          option: eco
```

Další složitější příklad je [zde](https://github.com/jmcollin78/versatile_thermostat/discussions/431#discussioncomment-11393065)

## Použití systému Netatmo

Systém založený na Netatmo TRV nefunguje dobře s _VTherm_. Můžete najít diskusi o specifickém chování Netatmo systémů (ve francouzštině) zde: [https://forum.hacf.fr/t/vannes-netatmo-et-vtherm/56063](https://forum.hacf.fr/t/vannes-netatmo-et-vtherm/56063).

Někteří uživatelé však úspěšně integrovali _VTherm_ s Netatmo pomocí virtuálního spínače mezi _VTherm_ a Netatmo entitou `climate`, takto:

```
TODO
```


## Topí jen první radiátor

V režimu `over_switch`, pokud je pro stejný VTherm nakonfigurováno více radiátorů, vytápění bude spuštěno postupně, aby se co nejvíce vyhladily špičky spotřeby.
To je zcela normální a záměrné. Je to popsáno zde: [Pro termostat typu ```thermostat_over_switch```](#pro-termostat-typu-thermostat_over_switch)

## Radiátor topí, i když je překročena cílová teplota, nebo netopí, když je teplota místnosti výrazně pod cílem

### Typ `over_switch` nebo `over_valve`
U VTherm typu `over_switch` nebo `over_valve` tento problém jednoduše indikuje, že parametry algoritmu TPI nejsou správně nakonfigurované. Viz [Algoritmus TPI](#algoritmus-tpi) pro optimalizaci nastavení.

### Typ `over_climate`
U VTherm typu `over_climate` je regulace řešena přímo podkladovým `climate` a VTherm mu jednoduše předává setpointy. Takže pokud radiátor topí, i když je překročena cílová teplota, je pravděpodobné, že jeho vnitřní měření teploty je zkreslené. To se často stává u TRV a reverzibilních klimatizací, které mají vnitřní teplotní senzor, buď příliš blízko topného prvku (takže je v zimě příliš chladno).

Příklady diskusí na tato témata: [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348), [#316](https://github.com/jmcollin78/versatile_thermostat/issues/316), [#312](https://github.com/jmcollin78/versatile_thermostat/discussions/312), [#278](https://github.com/jmcollin78/versatile_thermostat/discussions/278)

Pro vyřešení tohoto problému je VTherm vybaven funkcí zvanou samo-regulace, která mu umožňuje upravit setpoint zaslaný podkladovému zařízení, dokud není setpoint splněn. Tato funkce kompenzuje zkreslení vnitřních teplotních senzorů. Pokud je zkreslení značné, regulace by měla být také značná. Viz [Samo-regulace](self-regulation.md) pro konfiguraci samo-regulace.

## Úprava parametrů detekce otevřených oken v auto režimu

Pokud nemůžete nakonfigurovat funkci automatické detekce otevřených oken (viz [auto](feature-window.md#auto-mode)), můžete zkusit upravit parametry algoritmu vyhlazování teploty.
Automatická detekce otevřených oken je totiž založena na výpočtu sklonu teploty. Aby se zabránilo artefaktům způsobeným nepřesným teplotním senzorem, tento sklon se vypočítává pomocí teploty vyhlazené algoritmem nazvaným Exponential Moving Average (EMA).
Tento algoritmus má 3 parametry:
1. `lifecycle_sec`: doba v sekundách uvažovaná pro vyhlazování. Čím vyšší je, tím hladší bude teplota, ale také se zvýší zpoždění detekce.
2. `max_alpha`: pokud jsou dvě čtení teploty časově vzdálená, druhé bude mít mnohem větší váhu. Tento parametr omezuje váhu čtení, které přijde dlouho po předchozím. Tato hodnota musí být mezi 0 a 1. Čím nižší je, tím méně se berou v úvahu vzdálená čtení. Výchozí hodnota je 0.5, což znamená, že nové čtení teploty nikdy nebude vážit více než polovina klouzavého průměru.
3. `precision`: počet číslic za desetinnou čárkou zachovaných pro výpočet klouzavého průměru.

Pro změnu těchto parametrů musíte upravit soubor `configuration.yaml` a přidat následující sekci (hodnoty níže jsou výchozí hodnoty):

```yaml
versatile_thermostat:
  short_ema_params:
    max_alpha: 0.5
    halflife_sec: 300
    precision: 2
```

Tyto parametry jsou citlivé a poměrně obtížné na úpravu. Použijte je prosím pouze pokud víte, co děláte, a pokud vaše čtení teploty již nejsou vyhlazená.

## Proč můj Versatile Thermostat přechází do bezpečnostního režimu?

Bezpečnostní režim je dostupný pouze pro typy VTherm `over_switch` a `over_valve`. Nastává, když jeden ze dvou teploměrů (poskytujících buď teplotu místnosti nebo vnější teplotu) neposlal hodnotu více než `safety_delay_min` minut a radiátor topil alespoň `safety_min_on_percent`. Viz [bezpečnostní režim](feature-advanced.md#safety-mode)

Protože algoritmus spoléhá na měření teploty, pokud je VTherm už nedostává, existuje riziko přehřátí a požáru. Aby se tomu zabránilo, když jsou detekované výše uvedené podmínky, vytápění je omezeno na parametr `safety_default_on_percent`. Tato hodnota by proto měla být rozumně nízká (10% je dobrá hodnota). Pomáhá vyhnout se požáru při současném zabránění úplnému vypnutí radiátoru (riziko zamrznutí).

Všechny tyto parametry jsou konfigurovány na poslední stránce konfigurace VTherm: "Pokročilá nastavení".

### Jak detekovat bezpečnostní režim?
Prvním příznakem je neobvykle nízká teplota s krátkým a konzistentním časem vytápění během každého cyklu.
Příklad:

[security mode](images/security-mode-symptome1.png)

Pokud máte nainstalovanou [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card), postižený VTherm se zobrazí takto:

[security mode UI Card](images/security-mode-symptome2.png)

Můžete také zkontrolovat atributy VTherm pro data posledních přijatých hodnot. **Atributy jsou dostupné v Developer Tools / States**.

Příklad:

```yaml
safety_state: true
last_temperature_datetime: "2023-12-06T18:43:28.346010+01:00"
last_ext_temperature_datetime: "2023-12-06T13:04:35.164367+01:00"
last_update_datetime: "2023-12-06T18:43:28.351103+01:00"
...
safety_delay_min: 60
```

Můžeme vidět, že:
1. VTherm je skutečně v bezpečnostním režimu (`safety_state: true`),
2. Aktuální čas je 06/12/2023 v 18:43:28 (`last_update_datetime: "2023-12-06T18:43:28.351103+01:00"`),
3. Čas posledního příjmu teploty místnosti je 06/12/2023 v 18:43:28 (`last_temperature_datetime: "2023-12-06T18:43:28.346010+01:00"`), takže je aktuální,
4. Čas posledního příjmu vnější teploty je 06/12/2023 v 13:04:35 (`last_ext_temperature_datetime: "2023-12-06T13:04:35.164367+01:00"`). Vnější teplota má zpoždění více než 5 hodin, což spustilo bezpečnostní režim, protože práh je nastaven na 60 minut (`safety_delay_min: 60`).

### Jak být upozorněn, když se to stane?
VTherm pošle událost, jakmile se to stane, a znovu na konci bezpečnostního upozornění. Tyto události můžete zachytit v automatizaci a poslat upozornění, blikat světlem, spustit sirénu atd. To je na vás.

Pro zpracování událostí generovaných VTherm viz [Události](#události).

### Jak to opravit?
Závisí to na příčině problému:
1. Pokud je senzor vadný, měl by být opraven (vyměnit baterie, změnit jej, zkontrolovat weather integraci, která poskytuje vnější teplotu atd.),
2. Pokud je parametr `safety_delay_min` příliš malý, může generovat mnoho falešných upozornění. Správná hodnota je kolem 60 minut, zejména pokud máte teplotní senzory na baterie. Viz [moje nastavení](tuning-examples.md#battery-powered-temperature-sensor),
3. Některé teplotní senzory neposílají měření, pokud se teplota nezměnila. Takže pokud teplota zůstává velmi stabilní po dlouhou dobu, bezpečnostní režim se může spustit. To není velký problém, protože se deaktivuje, jakmile VTherm obdrží novou teplotu. Na některých teploměrech (např. TuYa nebo Zigbee) můžete vynutit maximální zpoždění mezi dvěma měřeními. Maximální zpoždění by mělo být nastaveno na hodnotu nižší než `safety_delay_min`,
4. Jakmile je teplota znovu přijata, bezpečnostní režim se vypne a předchozí preset, cílová teplota a hodnoty režimu budou obnoveny.
5. Pokud je vnější teplotní senzor vadný, můžete zakázat spuštění bezpečnostního režimu, protože má minimální dopad na výsledky. Viz [zde](feature-advanced.md#safety-mode).
6. some Zigbee sensors have an entity named Last Seen. They are often hidden and need to be enabled to be usable. Once enabled, you can configure it in the VTherm main configuration screen. See main configuration screen.


## Použití skupiny osob jako senzoru přítomnosti

Bohužel skupiny osob nejsou rozpoznány jako senzory přítomnosti. Proto je nemůžete použít přímo ve VTherm.
Obejití je vytvoření šablony binárního senzoru s následujícím kódem:

Soubor `template.yaml`:

```yaml
- binary_sensor:
    - name: maison_occupee
      unique_id: maison_occupee
      state: "{{is_state('person.person1', 'home') or is_state('person.person2', 'home') or is_state('input_boolean.force_presence', 'on')}}"
      device_class: occupancy
```

V tomto příkladu si všimněte použití `input_boolean` nazvaného `force_presence`, který nutí senzor na `True`, čímž nutí jakýkoli VTherm, který jej používá, mít aktivní přítomnost. To lze použít například pro spuštění předehřívání domu při odchodu z práce nebo když je v HA přítomna nerozpoznaná osoba.

Soubor `configuration.yaml`:

```yaml
...
template: !include templates.yaml
...
```

## Povolení logů pro Versatile Thermostat

Někdy budete muset povolit logy pro jemné doladění vaší analýzy. Upravte soubor `logger.yaml` v konfiguraci a nakonfigurujte logy takto:

```yaml
default: xxxx
logs:
  custom_components.versatile_thermostat: info
```
Musíte znovu načíst YAML konfiguraci (Developer Tools / YAML / Reload all YAML configuration) nebo restartovat Home Assistant, aby se tato změna projevila.

Pozor, v debug režimu je Versatile Thermostat velmi podrobný a může rychle zpomalit Home Assistant nebo nasytit váš pevný disk. Pokud přepnete do debug režimu pro analýzu anomálií, udělejte to pouze po dobu potřebnou k reprodukci chyby a debug režim okamžitě poté zakažte.

## VTherm nesleduje změny setpointu provedené přímo na podkladovém zařízení (`over_climate`)

Viz podrobnosti této funkce [zde](over-climate.md#track-underlying-temperature-changes).

## VTherm automaticky přepíná do režimu 'Chlazení' nebo 'Vytápění'

Některá reverzibilní tepelná čerpadla mají režimy, které umožňují tepelnému čerpadlu rozhodnout, zda topit nebo chladit. Tyto režimy jsou označeny jako 'Auto' nebo 'Heat_cool' v závislosti na značce. Tyto dva režimy by neměly být používány s _VTherm_, protože algoritmy _VTherm_ vyžadují explicitní znalost toho, zda je systém v režimu vytápění nebo chlazení, což tyto režimy neposkytují.

Měli byste používat pouze následující režimy: `Heat`, `Cool`, `Off` nebo volitelně `Fan` (ačkoli `Fan` nemá s _VTherm_ praktický účel).

## Detekce otevřených oken nebrání změnám preset

Skutečně, změny preset při otevřeném okně jsou brány v úvahu a to je očekávané chování.
Pokud je režim akce nastaven na _Vypnout_ nebo _Pouze ventilátor_, změna preset a úprava cílové teploty se aplikuje okamžitě. Protože je zařízení buď vypnuto nebo v režimu pouze ventilátoru, není riziko vytápění venku. Když se režim zařízení přepne na Vytápění nebo Chlazení, preset a teplota budou aplikovány a používány.

Pokud je režim akce nastaven na _Ochrana proti mrazu_ nebo _Eco_, teplota preset se aplikuje, **ale samotný preset zůstává nezměněn**. To umožňuje změny preset při otevřeném okně bez změny cílové teploty, která zůstává jak naprogramována v režimu akce.

### Příklad:
1. **Počáteční stav**: Okno zavřeno, režim akce nastaven na _Ochrana proti mrazu_, preset na Comfort a cílová teplota na 19°C.
2. **Okno se otevře a systém čeká**: Preset zůstává na Comfort, **ale cílová teplota se přepne na 10°C** (ochrana proti mrazu). Tento stav může vypadat nekonzistentně, protože zobrazený preset neodpovídá aplikované cílové teplotě.
3. **Změna preset na Boost** (uživatelem nebo Schedulerem): Preset se přepne na Boost, ale cílová teplota zůstává na 10°C (ochrana proti mrazu). Tento stav může také vypadat nekonzistentně.
4. **Okno se zavře**: Preset zůstává na Boost a cílová teplota se změní na 21°C (Boost). Nekonzistence zmizí a uživatelova změna preset se správně aplikuje.
