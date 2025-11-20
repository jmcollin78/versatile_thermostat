# Przykłady dostrajania układu

- [Przykłady dostrajania układu](#tuning-examples)
  - [Ogrzewanie elektryczne](#electric-heating)
  - [Centralne ogrzewanie (gazowe lub olejowe)](#central-heating-gas-or-oil-heating)
  - [Czujniki temperatur z bateryjnym zasilaniem](#battery-powered-temperature-sensor)
  - [Reaktywny czujnik temperatury (ze stałym zasilaniem)](#reactive-temperature-sensor-plugged-in)
  - [Własne presety](#my-presets)

## Ogrzewanie elektryczne
- Cykl: **pomiędzy `5` i `10` minut**,
- Minimalna zwłoka aktywacji `minimal_activation_delay_sec`: `30` **sekund**.

## Centralne ogrzewanie (gazowe lub olejowe)
- Cykl: **pomiędzy `30` i `60` minut**,
- Minimalna zwłoka aktywacji `minimal_activation_delay_sec`: `300` **sekund** (z powodu czasu odpowiedzi, spowodowanym pewną bezwładnością układu).

## Czujniki temperatur z bateryjnym zasilaniem
Czujniki te często działają dość wolno i nie zawsze wysyłają odczyty temperatury, gdy jest ona stabilna. Dlatego ustawienia powinny być w miarę swobodne, aby uniknąć pojawiania się fałszywych alarmów.

- bezpieczna zwłoka `safety_delay_min`: **60 minut** (z powodu bezwładności czujnika)
- bezpieczny procent `safety_min_on_percent`: **0.7** (70% - system przechodzi w tryb *bezpieczny*, gdy grzejnik był załączony przez ponad 70% czasu)
- domyślny bezpieczny procent `safety_default_on_percent`: **0.4** (40% - w trybie *bezpiecznym*, utrzymujemy 40% czasu grzania, aby uniknąć zbytniego wychłodzenia)

Takie ustawienia powinny być rozumiane następująco:

> Jeśli termometr przestanie wysyłać odczyty temperatury na 1 godzinę, a procent grzania (`on_percent`) będzie większy, niż `70%`, wówczas procent grzania zostanie zredukowany do `40%`.

![Tip](images/tips.png) Można swobodnie dostosować te ustawienia do swoich potrzeb!

Ważne jest, aby nie podejmować zbyt dużego ryzyka przy definiowaniu tych parametrów:
> Załóżmy, że nie będzie Cię przez dłuższy czas, a baterie Twojego termometru są rozładowane. Wówczas grzejnik będzie działał przez 40% czasu w trakcie całego okresu awarii.

Integracja _Termostat Versatile_ umożliwia otrzymywanie powiadomień o wystąpieniu takich zdarzeń. Dlatego wskazane jest skonfigurowanie odpowiednich alertów zaraz po instalacji i konfiguracji termostatu. Zobacz (#powiadomienia).

## Reaktywny czujnik temperatury (ze stałym zasilaniem)
Termometr zasilany energią elektryczną powinien bardzo regularnie wysyłać odczyty temperatury. Jeśli jednak nie wysyła on żadnych danych przez 15 minut, najprawdopodobniej wystąpiła awaria, a my możemy zareagować szybciej, bez ryzyka pojawiania się fałszywych alarmów.

- bezpieczna zwłoka `safety_delay_min`: **15 minut**
- bezpieczny procent `safety_min_on_percent`: **0.5** (50% - system przechodzi w tryb *bezpieczny*, gdy grzejnik był załączony przez ponad 50% czasu)
- domyślny bezpieczny procent `safety_default_on_percent`: **0.25** (25% - w trybie *bezpiecznym*, utrzymujemy 25% czasu grzania, aby uniknąć zbytniego wychłodzenia)


## Własne presety
Oto przykład, w jaki sposób można użyć ustawień presetów:

> ![Tip](images/tips.png)Można je zaadaptować do własnej konfiguracji systemu ogrzewania, ale może także służyć lepszemu zrozumieniu zasad ich fukcjonowania i wykorzystywania w integracji:

- ``Ochrona przed zamarzaniem``: **10°C**
- ``Eko``: **17°C**
- ``Komfort``: **19°C**
- ``Boost``: **20°C**

Gdy wyłączona jest detekcja obecności (lub ruchu), to:
- ``Ochrona przed zamarzaniem``: **10°C**
- ``Eko``: **16.5°C**
- ``Komfort``: **17°C**
- ``Boost``: **17.5°C**

Detektor ruchu jest skonfigurowany następująco:
- tryb ``Boost`` - z chwilą **wykrycia** ruchu,
- tryb ``Eko`` - gdy **brak** jest ruchu.

Tryb _*bezpieczny*_ jest skonfigurowany następująco:

![My settings](images/my-tuning.png)
