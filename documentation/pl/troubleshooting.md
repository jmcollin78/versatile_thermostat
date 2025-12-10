
# Usuwanie problemów

- [Usuwanie problemów](#usuwanie-problemów)
  - [System Heatzy](#system-heatzy)
  - [Grzejnik z przewodem sterującym (Nodon SIN-4-FP-21)](#grzejnik-z-przewodem-sterującym-nodon-sin-4-fp-21)
  - [System Netatmo](#system-netatmo)
  - [Gdy grzeje tylko pierwszy grzejnik](#gdy-grzeje-tylko-pierwszy-grzejnik)
  - [Grzejnik grzeje nawet po przekroczeniu zadanej temperatury lub nie grzeje, gdy temperatura w pomieszczeniu jest znacznie niższa od zadanej.](#grzejnik-grzeje-nawet-po-przekroczeniu-zadanej-temperatury-lub-nie-grzeje-gdy-temperatura-w-pomieszczeniu-jest-znacznie-niższa-od-zadanej)
    - [`Termostat na przełączniku` lub `termostat na zaworze`](#termostat-na-przełączniku-lub-termostat-na-zaworze)
    - [`Termostat na klimacie`](#termostat-na-klimacie)
  - [Dostosowanie parametrów detekcji otwarcia okna w trybie automatycznym](#dostosowanie-parametrów-detekcji-otwarcia-okna-w-trybie-automatycznym)
  - [Dlaczego _VTherm_ przechodzi w tryb *bezpieczny*?](#dlaczego-vtherm-przechodzi-w-tryb-bezpieczny)
    - [Jak wykryć tryb *bezpieczny*?](#jak-wykryć-tryb-bezpieczny)
    - [Jak zostać powiadomionym o wystąpieniu takiej sytuacji?](#jak-zostać-powiadomionym-o-wystąpieniu-takiej-sytuacji)
    - [Jak to naprawić?](#jak-to-naprawić)
  - [Grupa osób jako sensor obecności](#grupa-osób-jako-sensor-obecności)
  - [Aktywacja logów dla _*Versatile Thermostat*_](#aktywacja-logów-dla-versatile-thermostat)
  - [_VTherm_ nie śledzi zmian wartości zadanych wprowadzanych bezpośrednio na urządzeniu bazowym (`termostat na klimacie`)](#vtherm-nie-śledzi-zmian-wartości-zadanych-wprowadzanych-bezpośrednio-na-urządzeniu-bazowym-termostat-na-klimacie)
  - [_VTherm_ automatycznie przełącza się na tryb `Chłodzenie` lub `Grzanie`](#vtherm-automatycznie-przełącza-się-na-tryb-chłodzenie-lub-grzanie)
  - [Detekcja otwarcia okien nie zapobiega zmianom presetów](#detekcja-otwarcia-okien-nie-zapobiega-zmianom-presetów)
    - [Przykład pozornej niespójności](#przykład-pozornej-niespójności)


## System Heatzy

System Heatzy jest już natywnie wspierany przez integrację _VTherm_. Zobacz: [Szybki start](quick-start.md#heatzy-or-ecosy-or-similar-climate-entity).

Ta konfiguracja jest przechowywana wyłącznie w celach informacyjnych.

Użycie Heatzy lub Nodon jest możliwe pod warunkiem użycia wirtualnego przełącznika z tym modelem:

```yaml
- platform: template
  switches:
    chauffage_sdb:
      unique_id: chauffage_sdb
      friendly_name: Grzejnik w łazience
      value_template: "{{ is_state_attr('climate.lazienka', 'preset_mode', 'comfort') }}"
      icon_template: >-
        {% if is_state_attr('climate.lazienka', 'preset_mode', 'comfort') %}
          mdi:radiator
        {% elif is_state_attr('climate.lazienka', 'preset_mode', 'away') %}
          mdi:snowflake
        {% else %}
          mdi:radiator-disabled
        {% endif %}
      turn_on:
        service: climate.set_preset_mode
        entity_id: climate.lazienka
        data:
          preset_mode: "comfort"
      turn_off:
        service: climate.set_preset_mode
        entity_id: climate.lazienka
        data:
          preset_mode: "eco"
```


## Grzejnik z przewodem sterującym (Nodon SIN-4-FP-21)

System Nodon jest już natywnie wspierany przez integrację _VTherm_. Zobacz: [Szybki start](quick-start.md#heatzy-or-ecosy-or-similar-climate-entity).

Ta konfiguracja jest przechowywana wyłącznie w celach informacyjnych.

Podobnie jak w przypadku opisanego powyżej systemu Heatzy, można użyć wirtualnego przełącznika, który zmieni ustawienia grzejnika na podstawie stanu załączenia/wyłączenia termostatu _VTherm_.

Przykład:

```yaml
- platform: template
  switches:
    chauffage_chb_parents:
      unique_id: chauffage_chb_parents
      friendly_name: Ogrzewanie w sypialni
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

Jeszcze jeden, bardziej złożony przykład znajdziesz [tutaj](https://github.com/jmcollin78/versatile_thermostat/discussions/431#discussioncomment-11393065)

## System Netatmo

System oparty na termostatach TRV Netatmo nie współpracuje dobrze z _VTherm_. Dyskusję na temat konkretnego działania systemów Netatmo (w języku francuskim) można znaleźć [tutaj](https://forum.hacf.fr/t/vannes-netatmo-et-vtherm/56063).

Niektórym użytkownikom udało się jednak pomyślnie zintegrować _VTherm_ z **Netatmo** poprzez wprowadzenie wirtualnego przełącznika między _VTherm_ a jednostką `climate` Netatmo w następujący sposób:

```
(...)
```


## Gdy grzeje tylko pierwszy grzejnik

W ``termostacie na przełączniku``, jeśli wiele grzejników jest skonfigurowanych dla tego samego termostatu _VTherm_, ogrzewanie będzie uruchamiane sekwencyjnie, aby maksymalnie wygładzić szczyty zużycia mocy grzewczej.
Jest to całkowicie normalne i celowe. Opis znajduje się tutaj: [dla termostatu typu ```termostat na przełączniku```](over-switch.md#over_switch-type-thermostat)

## Grzejnik grzeje nawet po przekroczeniu zadanej temperatury lub nie grzeje, gdy temperatura w pomieszczeniu jest znacznie niższa od zadanej.

### `Termostat na przełączniku` lub `termostat na zaworze`
W przypadku `termostatu na przełączniku` lub `termostatu na zaworze`, ten problem wskazuje po prostu, że parametry algorytmu TPI nie są poprawnie skonfigurowane. Zobacz: [Algorytm TPI](algorithms.md#the-tpi-algorithm) i popraw ustwienia.

### `Termostat na klimacie`
W przypadku `termostatu na klimacie`, regulacja jest realizowana bezpośrednio przez urządzenie `climate`, a _VTherm_ tylko przesyła do niego ustawienia. Jeśli więc grzejnik grzeje, mimo że temperatura żądana została przekroczona, prawdopodobnie jego wewnętrzny pomiar temperatury jest błędny. Często zdarza się tak w przypadku termostatów i klimatyzatorów rewersyjnych z wewnętrznym czujnikiem temperatury, umieszczonym zbyt blisko elementu grzejnego (przez co zimą jest zbyt zimno).

Przykłady dyskusji na te tematy: [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348), [#316](https://github.com/jmcollin78/versatile_thermostat/issues/316), [#312](https://github.com/jmcollin78/versatile_thermostat/discussions/312), [#278](https://github.com/jmcollin78/versatile_thermostat/discussions/278)

Aby rozwiązać ten problem, _VTherm_ został wyposażony w funkcję samoregulacji, która pozwala mu dostosowywać wartość żądaną wysyłaną do urządzenia bazowego, aż do jej osiągnięcia. Funkcja ta kompensuje odchylenie wewnętrznych czujników temperatury. Jeśli odchylenie jest znaczne, regulacja również powinna być znacząca. Informacje na temat konfiguracji samoregulacji można znaleźć [tutaj](self-regulation.md).

## Dostosowanie parametrów detekcji otwarcia okna w trybie automatycznym

Jeśli nie możesz skonfigurować funkcji automatycznej detekcji otwarcia okna (patrz: [auto](feature-window.md#auto-mode)), możesz spróbować zmodyfikować parametry algorytmu wygładzania temperatury.
W rzeczywistości automatyczna detekcja otwarcia okna opiera się na obliczaniu nachylenia krzywej temperatury. Aby uniknąć artefaktów spowodowanych przez niedokładny czujnik temperatury, nachylenie to jest obliczane za pomocą temperatury wygładzonej algorytmem o nazwie Średnia Zmienna Wykładnicza (EMA).
Algorytm ten ma 3 parametry:
1. `lifecycle_sec`: czas trwania w sekundach uwzględniany przy wygładzaniu. Im wyższy, tym bardziej płynna będzie temperatura, ale wzrośnie również opóźnienie detekcji.
2. `max_alpha`: jeśli dwa odczyty temperatury są oddalone od siebie w czasie, drugi będzie miał znacznie większą wagę. Ten parametr ogranicza wagę odczytu, który następuje znacznie później, niż poprzedni. Wartość ta musi mieścić się w przedziale od 0 do 1. Im niższa, tym mniej odległe odczyty są brane pod uwagę. Wartość domyślna to 0,5, co oznacza, że ​​nowy odczyt temperatury nigdy nie będzie ważył więcej, niż połowę wartości EMA.
3. `precision`: liczba cyfr po przecinku uwzględniana przy obliczaniu EMA.

Aby zmienić te parametry, należy zmodyfikować plik `configuration.yaml` i dodać następującą sekcję (poniższe wartości są wartościami domyślnymi):

```yaml
versatile_thermostat:
  short_ema_params:
    max_alpha: 0.5
    halflife_sec: 300
    precision: 2
```

Te parametry są wrażliwe i dość trudne do regulacji. Używaj ich tylko wtedy, gdy wiesz, co robisz i jeśli odczyty temperatury nie zostały już wcześniej wygładzone w inny sposób.

## Dlaczego _VTherm_ przechodzi w tryb *bezpieczny*?

Tryb *bezpieczny* jest dostępny tylko dla typów _VTherm_ `termostat na przełączniku` oraz `termostat na zaworze`. Występuje, gdy jeden z dwóch termometrów (mierzący temperaturę w pomieszczeniu lub temperaturę zewnętrzną) nie wysłał wartości przez ponad `safety_delay_min` minut, a grzejnik grzał co najmniej przez `safety_min_on_percent`. Zobacz: [tryb *bezpieczny*](feature-advanced.md#safety-mode).

Ponieważ algorytm opiera się na pomiarach temperatury, jeśli nie są one już odbierane przez _VTherm_, istnieje ryzyko przegrzania lub nawet **pożaru**. Aby temu zapobiec, po wykryciu powyższych warunków, ogrzewanie jest ograniczone do parametru `safety_default_on_percent`. Wartość ta powinna być zatem rozsądnie niska (10% to całkiem dobra wartość). Pomaga to uniknąć ryzyka pożaru, jednocześnie zapobiegając całkowitemu wyłączeniu grzejnika (ryzyku zamarzania).

Wszystkie te parametry mozna ustawić w ostatnim oknie konfiguracji 'Ustawienia zaawansowane'.

### Jak wykryć tryb *bezpieczny*?
Pierwszym objawem jest nietypowo niska temperatura oraz krótki i stały czas nagrzewania w każdym cyklu.
Oto przykład:

![image](images/security-mode-symptome1.png)

Jeśli masz zainstalowaną kartę [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card), termostat _VTherm_ będzie wyglądał następująco:

![image](images/security-mode-symptome2.png)

Można również sprawdzić atrybuty termostatu _VTherm_ pod kątem dat ostatnio otrzymanych wartości. **Atrybuty są dostępne w 'Narzędzia deweloperskie -> Stany'**.

Przykład:

```yaml
safety_state: true
last_temperature_datetime: "2023-12-06T18:43:28.346010+01:00"
last_ext_temperature_datetime: "2023-12-06T13:04:35.164367+01:00"
last_update_datetime: "2023-12-06T18:43:28.351103+01:00"
...
safety_delay_min: 60
```

Widać z tego, że:
1. Termostat jest rzeczywiście w trybie *bezpiecznym* (`safety_state: true`),
2. Aktualny czas to: *06/12/2023 godz. 18:43:28* (`last_update_datetime: "2023-12-06T18:43:28.351103+01:00"`),
3. Czas ostatniego odczytu temperatury w pomieszczeniu to: *06/12/2023 godz. 18:43:28* (`last_temperature_datetime: "2023-12-06T18:43:28.346010+01:00"`), więc jest aktualny,
4. Czas ostatniego odczytu temperatury zewnętrznej to: *06/12/2023 godz. 13:04:35* (`last_ext_temperature_datetime: "2023-12-06T13:04:35.164367+01:00"`). Temperatura zewnętrzna została odczytana ponad 5 godzin później, niż temperatura w pomieszczeniu, co spowodowało załączenie trybu *bezpiecznego*, ponieważ próg załączenia tego trybu został ustawiony na 60 minut (`safety_delay_min: 60`).

### Jak zostać powiadomionym o wystąpieniu takiej sytuacji?
VTherm wysyła zdarzenie natychmiast po jego wystąpieniua oraz ponownie po zakończeniu alertu bezpieczeństwa. Można rejestrować te zdarzenia w automatyzacji i wysyłać powiadomienia, załączać światło, uruchamiać syrenę itp. Decyzja należy do Ciebie.

Informacje na temat obsługi zdarzeń generowanych przez VTherm można znaleźć w sekcji [Zdarzenia](reference.md#events).

### Jak to naprawić?
Zależy to od przyczyny problemu:
1. Jeśli czujnik jest uszkodzony, należy go naprawić (wymienić baterie, zmienić jego położenie, sprawdzić integrację pogodową, która podaje temperaturę zewnętrzną itp.),
2. Jeśli parametr `safety_delay_min` jest zbyt mały, może generować wiele fałszywych alertów. Prawidłowa wartość to około 60 minut, szczególnie w przypadku czujników temperatury zasilanych bateryjnie. Sprawdź: [ustawienia](tuning-examples.md#battery-powered-temperature-sensor),
3. Niektóre czujniki temperatury nie wysyłają pomiarów, jeśli temperatura się nie zmieniła. Jeśli więc temperatura pozostaje bardzo stabilna przez długi czas, może uruchomić się tryb *bezpieczny*. Nie stanowi to dużego problemu, ponieważ zostanie on wyłączony, gdy _VTherm_ otrzyma nową temperaturę. W niektórych termometrach (np. TuYA lub Zigbee) można wymusić maksymalne opóźnienie między dwoma pomiarami. Maksymalne opóźnienie powinno być ustawione na wartość niższą, niż `safety_delay_min`.
4. Gdy tylko temperatura zostanie ponownie odczytana, tryb *bezpieczny* wyłączy się, a poprzednie wartości zadane, temperatura docelowa i tryb zostaną przywrócone.
5. Jeśli zewnętrzny czujnik temperatury jest uszkodzony, można wyłączyć wyzwalanie trybu *bezpiecznego*, ponieważ ma to minimalny wpływ na wyniki. Aby to zrobić, zajrzyj [tutaj](feature-advanced.md#safety-mode).
6. some Zigbee sensors have an entity named Last Seen. They are often hidden and need to be enabled to be usable. Once enabled, you can configure it in the VTherm main configuration screen. See main configuration screen.


## Grupa osób jako sensor obecności

Niestety, grupy osób nie są rozpoznawane jako czujniki obecności. Dlatego nie można ich używać bezpośrednio w VTherm.
Rozwiązaniem jest utworzenie szablonu czujnika binarnego za pomocą poniższego kodu:

Plik `template.yaml`:

```yaml
- binary_sensor:
    - name: Obecność w domu
      unique_id: maison_occupee
      state: "{{is_state('person.person1', 'home') or is_state('person.person2', 'home') or is_state('input_boolean.force_presence', 'on')}}"
      device_class: occupancy
```

W tym przykładzie zwróć uwagę na użycie `input_boolean` o nazwie `force_presence`, która wymusza na czujniku stan `True`, wymuszając w ten sposób na każdym termostacie, który go używa, aktywację detekcji obecności. Można tego użyć na przykład do uruchomienia ogrzewania domu po wyjściu z pracy lub gdy w strefie zdefiniewanej w _Home Assistant_ znajduje się nierozpoznana osoba.

Plik `configuration.yaml`:

```yaml
...
template: !include templates.yaml
...
```

## Aktywacja logów dla _*Versatile Thermostat*_

Czasami konieczne jest włączenie logów, aby doprecyzować przyczyny błędów. Aby to zrobić, do pliku `logger.yaml` dopisz poniższy kod:

```yaml
default: xxxx
logs:
  custom_components.versatile_thermostat: info
```
Aby ta zmiana została uwzględniona, należy ponownie załadować konfigurację YAML ('**Narzędzia deweloperskie -> YAML -> Przeładuj całą konfigurację YAML**') lub ponownie uruchomić Home Assistant.

⚠️ **Uwaga**: w trybie debugowania integracja _Versatile Thermostat_ działa dość ślamazarnie i może szybko spowolnić Home Assistant lub przeciążyć dysk twardy. Jeśli przełączysz się w tryb debugowania w celu analizy problemów, zrób to tylko na czas potrzebny do odtworzenia błędu i natychmiast wyłącz tryb debugowania.

## _VTherm_ nie śledzi zmian wartości zadanych wprowadzanych bezpośrednio na urządzeniu bazowym (`termostat na klimacie`)

Zobacz szczegółowy opis tej funkcji [tutaj](over-climate.md#track-underlying-temperature-changes).

## _VTherm_ automatycznie przełącza się na tryb `Chłodzenie` lub `Grzanie`

Niektóre odwracalne pompy ciepła posiadają tryby, które pozwalają pompie ciepła samodzielnie decydować, czy ma grzać, czy chłodzić. Tryby te są oznaczone jako `Auto` lub `Grzanie-chłodzenie`, w zależności od marki urządzenia. Tych dwóch trybów nie należy używać z _VTherm_, ponieważ algorytmy _VTherm_ wymagają dokładnej wiedzy o tym, czy system pracuje w trybie grzania, czy chłodzenia, czego te tryby niestety nie zapewniają.

Należy używać wyłącznie następujących trybów: `Grzanie` [`Heat`], `Chłodzenie` [`Cool`], `Wył.` [`Off`] lub opcjonalnie `Wentylator` [`Fan`] (chociaż `Wentylator` [`Fan`] nie ma praktycznego zastosowania w _VTherm_).

## Detekcja otwarcia okien nie zapobiega zmianom presetów

Rzeczywiście, gdy okno jest otwarte, zmiany presetów są uwzględniane i jest to oczekiwane zachowanie.
Jeśli tryb działania jest ustawiony na _Wyłącz_ lub _Tylko wentylator_, zmiana ustawień wstępnych i regulacja temperatury docelowej są aplikowane natychmiast. Ponieważ urządzenie jest wyłączone lub pracuje tylko w trybie wentylatora, nie ma ryzyka przegrzania. Po przełączeniu urządzenia w tryb ogrzewania lub chłodzenia, presety zostaną zaaplikowane zgodnie z ich ustawieniem.

Jeśli tryb działania jest ustawiony na _Ochrona przed zamarzaniem_ lub _Eko_, ustawiana jest temperatura wstępna, **ale sama wartość presetu temperatury wstępnej pozostaje niezmieniona**. Pozwala to na zmianę presetu, gdy okno jest otwarte, bez zmiany samej temperatury zadanej, która pozostaje taka sama, jak ustawiono w trybie normalnej pracy.

### Przykład pozornej niespójności
Oto przykład pozornej niespójności stanu wywołany presetem:
1. **Stan początkowy**: Okno zamknięte, tryb działania ustawiony na _Ochrona przed zamarzaniem_, tryb Komfort i temperatura zadana 19°C.
2. **Okno otwiera się, a system czeka**: Preset pozostaje w trybie _Komfort_, **ale temperatura zadana zmienia się na 10°C** (ochrona przed zamarzaniem). Ten stan może wydawać się niespójny, ponieważ wyświetlany preset nie odpowiada zastosowanej temperaturze zadanej.
3. **Zmiana presetu na `Boost`** (przez użytkownika lub harmonogram): preset przełącza się na `Boost`, ale temperatura zadana pozostaje na poziomie 10°C (ochrona przed zamarzaniem). Ten stan również może wydawać się niespójny.
4. **Okno zamyka się**: Preset pozostaje w trybie `Boost`, a temperatura zadana zmienia się na 21°C (`Boost`). Niespójność znika, a zmiana presetu użytkownika zostaje poprawnie zaaplikowana.
