# Konfiguracja zaawansowana

- [Konfiguracja zaawansowana](#konfiguracja-zaawansowana)
  - [Dlaczego ta funkcja?](#dlaczego-ta-funkcja)
  - [Kontekst bezpieczeństwa](#kontekst-bezpieczeństwa)
  - [Zasada działania trybu bezpieczeństwa](#zasada-działania-trybu-bezpieczeństwa)
    - [Co to jest tryb bezpieczeństwa?](#co-to-jest-tryb-bezpieczeństwa)
    - [Kiedy się aktywuje?](#kiedy-się-aktywuje)
    - [Ograniczenia](#ograniczenia)
  - [Konfiguracja](#konfiguracja)
  - [Parametry bezpieczeństwa](#parametry-bezpieczeństwa)
  - [Udostępniane atrybuty](#udostępniane-atrybuty)
  - [Dostępne akcje](#dostępne-akcje)
  - [Globalna konfiguracja zaawansowana](#globalna-konfiguracja-zaawansowana)
  - [Praktyczne porady](#praktyczne-porady)
  - [Naprawa nieprawidłowego stanu urządzenia](#naprawa-nieprawidłowego-stanu-urządzenia)
    - [Dlaczego ta funkcja?](#dlaczego-ta-funkcja-1)
    - [Przypadki użycia](#przypadki-użycia)
    - [Zasada działania](#zasada-działania)
    - [Konfiguracja](#konfiguracja-1)
    - [Parametry](#parametry)
    - [Udostępniane atrybuty](#udostępniane-atrybuty-1)
    - [Ograniczenia i bezpieczeństwo](#ograniczenia-i-bezpieczeństwo)

## Dlaczego ta funkcja?

Zaawansowana konfiguracja _VTherm_ oferuje niezbędne narzędzia do zapewnienia bezpieczeństwa i niezawodności systemu grzewczego. Te parametry pozwalają zarządzać sytuacjami, w których czujniki temperatury nie komunikują się prawidłowo, co mogłoby prowadzić do niebezpiecznych lub nieskutecznych poleceń.

## Kontekst bezpieczeństwa

Brak lub nieprawidłowe działanie czujnika temperatury może być **bardzo niebezpieczne** dla twojego domu. Rozważ ten konkretny przykład:

- Czujnik temperatury utknął na wartości 10°
- Twój _VTherm_ typu `over_climate` lub `over_valve` wykrywa bardzo niską temperaturę
- Wydaje polecenie maksymalnego grzania urządzeń
- **Wynik**: pokój się znacznie przegrzewa

Konsekwencje mogą wahać się od zwykłych szkód materialnych po poważniejsze zagrożenia, takie jak pożar lub wybuch (w przypadku uszkodzonego grzejnika elektrycznego).

## Zasada działania trybu bezpieczeństwa

### Co to jest tryb bezpieczeństwa?

Tryb bezpieczeństwa to mechanizm ochronny, który wykrywa, gdy czujniki temperatury nie reagują regularnie. Gdy zostanie wykryta brak danych, _VTherm_ aktywuje specjalny tryb, który:

1. **Zmniejsza natychmiastowe ryzyko**: system nie wydaje już poleceń maksymalnej mocy
2. **Utrzymuje minimalne grzanie**: zapewnia, że dom nie styga nadmiernie
3. **Cię ostrzega**: poprzez zmianę stanu termostatu, widoczną w Home Assistant

### Kiedy się aktywuje?

Tryb bezpieczeństwa się aktywuje, gdy:

- **Brakuje temperatury wewnętrznej**: od ustawionego maksymalnego opóźnienia nie otrzymano żadnych pomiarów
- **Brakuje temperatury zewnętrznej**: od ustawionego maksymalnego opóźnienia nie otrzymano żadnych pomiarów (opcjonalnie)
- **Czujnik zablokowany**: czujnik nie wysyła już zmian wartości (typowe zachowanie czujników zasilanych baterią)

Szczególnym wyzwaniem są czujniki zasilane baterią, które wysyłają dane tylko gdy wartość **się zmienia**. Jest zatem możliwe nieprzyjęcie aktualizacji przez wiele godzin bez rzeczywistej awarii czujnika. Dlatego parametry są konfigurowalne, aby dostosować detekcję do twojej instalacji.

### Ograniczenia

- **_VTherm_ typu `over_climate` autoregulatora**: tryb bezpieczeństwa jest automatycznie wyłączony. Nie ma ryzyka, jeśli urządzenie reguluje się samo (utrzymuje własną temperaturę). Jedynym ryzykiem jest niekomfortowa temperatura, nie zagrożenie fizyczne.

## Konfiguracja

Aby skonfigurować zaawansowane parametry bezpieczeństwa:

1. Otwórz konfigurację swojego _VTherm_
2. Przejdź do parametrów konfiguracji ogólnej
3. Przewiń w dół do sekcji "Konfiguracja zaawansowana"

Formularz konfiguracji zaawansowanej wygląda następująco:

![image](images/config-advanced.png)

> ![Porada](images/tips.png) _*Rada*_
>
> Jeśli termometr ma atrybut `last_seen` lub podobny, który podaje czas ostatniego kontaktu, **skonfiguruj ten atrybut** w głównych wyborach twojego _VTherm_. To znacznie ulepsza detekcję i zmniejsza fałszywe alarmy. Zobacz [konfiguracja atrybutów podstawowych](base-attributes.md#wybór-atrybutów-podstawowych) i [rozwiązywanie problemów](troubleshooting.md#dlaczego-mój-versatile-thermostat-przechodzi-w-tryb-bezpieczeństwa-) aby uzyskać więcej szczegółów.

## Parametry bezpieczeństwa

| Parametr | Opis | Wartość domyślna | Nazwa atrybutu |
| --- | --- | --- | --- |
| **Maksymalne opóźnienie przed trybem bezpieczeństwa** | Maksymalne dopuszczalne opóźnienie między dwoma pomiarami temperatury zanim _VTherm_ wejdzie w tryb bezpieczeństwa. Jeśli po tym opóźnieniu nie będzie otrzymany nowy pomiar, tryb bezpieczeństwa się aktywuje. | 60 minut | `safety_delay_min` |
| **Minimalna wartość progu `on_percent` dla bezpieczeństwa** | Minimalna wartość procentowa `on_percent` poniżej której tryb bezpieczeństwa się nie aktywuje. Unika aktywacji trybu bezpieczeństwa, gdy grzejnik pracuje bardzo mało (`on_percent` niski), ponieważ nie ma natychmiastowego ryzyka przegrzania. `0.00` zawsze aktywuje tryb, `1.00` go całkowicie wyłącza. | 0.5 (50%) | `safety_min_on_percent` |
| **Domyślna wartość `on_percent` w trybie bezpieczeństwa** | Moc grzewcza używana, gdy termostat jest w trybie bezpieczeństwa. `0` całkowicie wyłącza grzanie (ryzyko zamarzania), `0.1` utrzymuje minimalne grzanie, aby zapobiec zamarzaniu w przypadku długotrwałego awarii termometru. | 0.1 (10%) | `safety_default_on_percent` |

## Udostępniane atrybuty

Gdy tryb bezpieczeństwa jest aktywny, _VTherm_ udostępniają następujące atrybuty:

```yaml
safety_mode: "on"                # "on" lub "off"
safety_delay_min: 60             # Skonfigurowane opóźnienie w minutach
safety_min_on_percent: 0.5       # Próg on_percent (0.0 do 1.0)
safety_default_on_percent: 0.1   # Moc w trybie bezpieczeństwa (0.0 do 1.0)
last_safety_event: "2024-03-20 14:30:00"  # Czas ostatniego zdarzenia
```

## Dostępne akcje

Akcja _VTherm_ umożliwia dynamiczną rekonfigurację 3 parametrów bezpieczeństwa bez ponownego uruchamiania Home Assistant:

- **Usługa**: `versatile_thermostat.set_safety_parameters`
- **Parametry**:
  - `entity_id`: _VTherm_ do rekonfiguracji
  - `safety_delay_min`: nowe opóźnienie (minuty)
  - `safety_min_on_percent`: nowy próg (0.0 do 1.0)
  - `safety_default_on_percent`: nowa moc (0.0 do 1.0)

To pozwala dynamicznie dostosować czułość trybu bezpieczeństwa zgodnie z twoim użytkowaniem (na przykład zmniejszyć opóźnienie, gdy ludzie są w domu, lub zwiększyć, gdy dom jest niezamieszkały).

## Globalna konfiguracja zaawansowana

Można wyłączyć sprawdzanie **czujnika temperatury zewnętrznej** dla trybu bezpieczeństwa. Czujnik zewnętrzny ma zwykle mały wpływ na regulację (w zależności od twojej konfiguracji) i może być nieobecny bez zagrożenia bezpieczeństwa domu.

Aby to zrobić, dodaj następujące linie do `configuration.yaml`:

```yaml
versatile_thermostat:
  safety_mode:
    check_outdoor_sensor: false
```

> ![Ważne](images/tips.png) _*Ważne*_
>
> - Ta zmiana jest **wspólna dla wszystkich _VTherm_** w systemie
> - Wpływa na detekcję termometru zewnętrznego dla wszystkich termostatów
> - **Home Assistant musi być uruchomiony ponownie**, aby zmiany weszły w życie
> - Domyślnie termometr zewnętrzny może aktywować tryb bezpieczeństwa, jeśli przestanie wysyłać dane

## Praktyczne porady

> ![Porada](images/tips.png) _*Uwagi i najlepsze praktyki*_

1. **Przywrócenie po naprawie**: Gdy czujnik temperatury powróci do życia i ponownie będzie wysyłać dane, tryb ustawienia zostanie przywrócony do jego poprzedniej wartości.

2. **Wymagane dwie temperatury**: System wymaga zarówno temperatury wewnętrznej, jak i zewnętrznej, aby działać prawidłowo. Jeśli brakuje jednej z nich, termostat wejdzie w tryb bezpieczeństwa.

3. **Relacja między parametrami**: Do naturalnego działania wartość `safety_default_on_percent` powinna być **mniejsza niż** `safety_min_on_percent`. Na przykład: `safety_min_on_percent = 0.5` i `safety_default_on_percent = 0.1`.

4. **Dostosowanie do twojego czujnika**:
   - Jeśli masz **fałszywe alarmy**, zwiększ opóźnienie (`safety_delay_min`) lub zmniejsz `safety_min_on_percent`
   - Jeśli masz czujniki zasilane baterią, zwiększ opóźnienie dalej (np.: 2-4 godziny)
   - Jeśli używasz atrybutu `last_seen`, opóźnienie można zmniejszyć (system jest dokładniejszy)

5. **Wizualizacja w interfejsie użytkownika**: Jeśli używasz [karty _Versatile Thermostat UI_](additions.md#lepiej-z-kartą-versatile-thermostat-ui), _VTherm_ w trybie bezpieczeństwa jest wizualnie wskazany przez:
   - Szarawy zasłon na termostacie
   - Wyświetlenie uszkodzonego czujnika
   - Czas, który upłynął od ostatniej aktualizacji

   ![Tryb bezpieczeństwa](images/safety-mode-icon.png).

## Naprawa nieprawidłowego stanu urządzenia

### Dlaczego ta funkcja?

Przy użyciu _VTherm_ z urządzeniami grzewczymi (`over_switch`, `over_valve`, `over_climate`, `over_climate_valve`), może się zdarzyć, że urządzenie nie będzie prawidłowo wykonywać polecenie wysłane przez termostat. Na przykład:

- Zablokowany przekaźnik, który nie przełącza się do wymaganego stanu
- Zawór termostatyczny, który nie wykonuje poleceń
- Tymczasowa utrata komunikacji z urządzeniem
- Urządzenie, które zbyt długo reaguje

Funkcja **"Naprawa nieprawidłowego stanu"** wykrywa te sytuacje i automatycznie ponownie wysyła polecenie, aby zsynchronizować rzeczywisty stan z pożądanym stanem.

### Przypadki użycia

Ta funkcja jest szczególnie przydatna dla:

- **Niestabilne przekaźniki**: przekaźniki, które się zawierają lub nie zawsze się prawidłowo przełączają
- **Przerywaną komunikację Zigbee/WiFi**: urządzenia, które czasem tracą połączenie
- **Powolne zawory**: zawory termostatyczne, które powoli reagują na polecenia
- **Uszkodzone urządzenia**: grzejniki elektryczne lub zawory, które nie reagują na polecenia
- **Pompy ciepła**: aby upewnić się, że pompa ciepła prawidłowo wykonuje polecenia grzewcze/chłodzące

### Zasada działania

W każdym cyklu sterowania termostatem funkcja:

1. **Porównuje stany**: sprawdza, czy rzeczywisty stan każdego urządzenia odpowiada wysłanemu poleceniu
2. **Wykrywa niewielkie różnice**: jeśli urządzenie nie wykonało polecenia, to jest różnica
3. **Ponownie wysyła polecenie**: jeśli zostanie wykryta różnica, ponownie wysyła polecenie, aby zsynchronizować stan
4. **Liczy próby**: liczba kolejnych napraw jest ograniczona, aby uniknąć pętli nieskończonych
5. **Steruje opóźnieniem aktywacji**: funkcja aktywuje się tylko po opóźnieniu minimalnym, aby urządzenia mogły zakończyć inicjalizację

### Konfiguracja

Ta funkcja jest konfigurowana w interfejsie konfiguracji _VTherm_:

1. Otwórz konfigurację swojego _VTherm_
2. Przejdź do parametrów konfiguracji ogólnej
3. Przewiń w dół do sekcji "Konfiguracja zaawansowana"
4. Włącz opcję **"Napraw nieprawidłowy stan urządzenia"**

### Parametry

| Parametr | Opis | Wartość domyślna |
| --- | --- | --- |
| **Napraw nieprawidłowy stan** | Włącza lub wyłącza automatyczną detekcję i naprawę różnic stanu. Gdy włączone, każda wykryta różnica powoduje ponowne wysłanie polecenia. | Wyłączono |

> ![Porada](images/tips.png) _*Wewnętrzne parametry systemu*_
>
> Niektóre parametry są konfigurowane na poziomie systemu i nie można ich modyfikować:
> - **Minimalne opóźnienie przed aktywacją**: 30 sekund po uruchomieniu termostatu (umożliwia inicjalizację wszystkich urządzeń)
> - **Maksymalne kolejne próby**: 5 kolejnych napraw przed tymczasowym zatrzymaniem
> - **Opóźnienie resetowania**: licznik napraw resetuje się, gdy urządzenia powracają do prawidłowego stanu

### Udostępniane atrybuty

Gdy funkcja naprawy jest włączona, _VTherm_ udostępniają następujący atrybut:

```yaml
repair_incorrect_state_manager:
  consecutive_repair_count: 2       # Liczba wykonanych kolejnych napraw
  max_attempts: 5                   # Szczytu przed tymczasowym zatrzymaniem
  min_delay_after_init_sec: 30      # Minimalne opóźnienie przed aktywacją
is_repair_incorrect_state_configured: true  # Stan funkcji
```

Licznik `consecutive_repair_count` pozwala ci:
- Diagnozować częste problemy sprzętowe
- Identyfikować uszkodzone urządzenia
- Monitorować stabilność instalacji

### Ograniczenia i bezpieczeństwo

> ![Ważne](images/tips.png) _*Ważne*_

1. **Brak zmiany zachowania**: Ta funkcja nie zmienia logiki grzewczej. Jedynie zapewnia prawidłowe wykonanie poleceń.

2. **Bezpieczny limit**: Maksymalna liczba kolejnych prób (5) zapobiega pętlom nieskończonym. Jeśli ten limit zostanie osiągnięty, błąd jest rejestrowany, a naprawa zostaje tymczasowo zatrzymana.

3. **Opóźnienie uruchomienia**: Funkcja aktywuje się tylko po 30 sekundach, aby wszystkie urządzenia zdążyły się całkowicie zainicjować.

4. **Mające zastosowanie do wszystkich typów _VTherm_**: Ta funkcja pracuje dla wszystkich typów `over_switch`, `over_valve`, `over_climate` i `over_climate_valve` (`over_climate` z bezpośrednią regulacją zaworu). Dla ostatnich sprawdzany jest stan bazowego `climate`, jak i stan otwarcia zaworu.

5. **Symptomy nadmiernej aktywności**: Jeśli regularnie widzisz komunikaty ostrzeżenia o naprawie, oznacza to problem sprzętowy:
   - Sprawdź połączenie urządzenia
   - Sprawdź stabilność sieci (Zigbee/WiFi)
   - Ręcznie przetestuj urządzenie za pośrednictwem Home Assistant
   - Rozważ wymianę, jeśli problem się utrzymuje

6. **Resetowanie licznika**: Licznik automatycznie resetuje się, gdy urządzenia powracają do prawidłowego stanu, umożliwiając nowe próby w przypadku przerywających się problemów.

7. **Regularne ponowienie**: Po 5 nieudanych próbach naprawy, naprawa wstrzymuje się, aby uniknąć pętli nieskończonych. Wznawia się po 10 cyklach bez naprawy, umożliwiając nowe próby w przypadku przerywających się problemów.
