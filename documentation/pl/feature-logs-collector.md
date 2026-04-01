# Pobieranie starszych dzienników - Diagnostyka i rozwiązywanie problemów

- [Pobieranie starszych dzienników - Diagnostyka i rozwiązywanie problemów](#pobieranie-starszych-dzienników---diagnostyka-i-rozwiązywanie-problemów)
  - [Dlaczego pobierać dzienniki?](#dlaczego-pobierać-dzienniki)
  - [Jak uzyskać dostęp do tej funkcji](#jak-uzyskać-dostęp-do-tej-funkcji)
  - [Wywoływanie akcji z Home Assistant](#wywoływanie-akcji-z-home-assistant)
    - [Opcja 1: Z interfejsu użytkownika (UI)](#opcja-1-z-interfejsu-użytkownika-ui)
    - [Opcja 2: Ze skryptu lub automatyzacji](#opcja-2-ze-skryptu-lub-automatyzacji)
  - [Dostępne parametry](#dostępne-parametry)
    - [Wyjaśnienie poziomów dziennika](#wyjaśnienie-poziomów-dziennika)
  - [Odbieranie i pobieranie pliku](#odbieranie-i-pobieranie-pliku)
  - [Format i zawartość pliku dziennika](#format-i-zawartość-pliku-dziennika)
  - [Praktyczne przykłady](#praktyczne-przykłady)
    - [Przykład 1: Debugowanie anomalnej temperatury przez 30 minut](#przykład-1-debugowanie-anomalnej-temperatury-przez-30-minut)
    - [Przykład 2: Walidacja prawidłowego wykrycia obecności](#przykład-2-walidacja-prawidłowego-wykrycia-obecności)
    - [Przykład 3: Sprawdzenie wszystkich termostatów w krótkim okresie](#przykład-3-sprawdzenie-wszystkich-termostatów-w-krótkim-okresie)
  - [Zaawansowana konfiguracja](#zaawansowana-konfiguracja)
  - [Porady dotyczące użytkowania](#porady-dotyczące-użytkowania)

## Dlaczego pobierać dzienniki?

Dzienniki (_logi – log zdarzeń_) Versatile Thermostat rejestrują wszystkie zmiany i działania wykonywane przez termostat. Są przydatne do:

- **Diagnozowania awarii**: Zrozumienia, dlaczego termostat nie zachowuje się zgodnie z oczekiwaniami
- **Analizy abnormalnego zachowania**: Weryfikacji decyzji termostatu w danym okresie
- **Debugowania konfiguracji**: Walidacji prawidłowego wykrycia czujników i akcji
- **Zgłaszania problemu**: Dostarczenia historii programistom w celu wsparcia debugowania

Funkcja **pobierania dzienników** zapewnia prosty sposób pobierania dzienników z określonego okresu, filtrowanych zgodnie z Twoimi potrzebami.

**Przydatna wskazówka**: Przy żądaniu wsparcia będziesz musiał podać dzienniki od czasu, gdy problem się pojawił. Korzystanie z tej funkcji jest zalecane, ponieważ dzienniki są zbierane niezależnie od poziomu dziennika skonfigurowanego w Home Assistant (w przeciwieństwie do natywnego systemu logowania HA).

## Jak uzyskać dostęp do tej funkcji

Akcja `versatile_thermostat.download_logs` jest dostępna w Home Assistant poprzez:

1. **Automatyzacje** (Scripts > Automations)
2. **Skrypty** (Scripts > Scripts)
3. **Narzędzia dla programistów** (Settings > Developer Tools > Services)
4. **Interfejs kontroli niektórych integracji** (w zależności od wersji Home Assistant)

## Wywoływanie akcji z Home Assistant

### Opcja 1: Z interfejsu użytkownika (UI)

Aby wywołać akcję z Narzędzi dla programistów:

1. Przejdź do **Settings** (Ustawienia) → **Developer Tools** (Narzędzia dla programistów)
2. Karta **Actions** (wcześniej **Services**) → wybierz `versatile_thermostat: Download logs`
3. Wypełnij żądane parametry (patrz sekcja poniżej)
4. Kliknij **Call Service** (Wywołaj usługę)

Następnie wyświetli się **trwałe powiadomienie** z linkiem do pobrania pliku.

### Opcja 2: Ze skryptu lub automatyzacji

Przykład wywołania w automatyzacji lub skrypcie YAML:

```yaml
action: versatile_thermostat.download_logs
metadata: {}
data:
  entity_id: climate.salon        # Opcjonalnie: zastąp swoim termostatem
  log_level: INFO                 # Opcjonalnie: DEBUG (domyślnie), INFO, WARNING, ERROR
  period_start: "2025-03-14T08:00:00" # Opcjonalnie: format ISO (datetime)
  period_end: "2025-03-14T10:00:00"   # Opcjonalnie: format ISO (datetime)
```

## Dostępne parametry

| Parametr       | Wymagane? | Możliwe wartości                          | Domyślnie            | Opis                                                                                |
| -------------- | --------- | ----------------------------------------- | -------------------- | ----------------------------------------------------------------------------------- |
| `entity_id`    | Nie       | `climate.xxx` lub nie podawać             | Wszystkie VTherm     | Specjalny ukierunkowany termostat. Jeśli nie podano, obejmuje wszystkie termostaty. |
| `log_level`    | Nie       | `DEBUG`, `INFO`, `WARNING`, `ERROR`       | `DEBUG`              | Minimalny poziom ważności. Wszystkie dzienniki na tym poziomie i powyżej.           |
| `period_start` | Nie       | Format ISO datetime (np. `2025-03-14...`) | 60 minut temu        | Początek okresu ekstrakcji. Format ISO z datą i czasem.                             |
| `period_end`   | Nie       | Format ISO datetime (np. `2025-03-14...`) | Teraz (bieżący czas) | Koniec okresu ekstrakcji. Format ISO z datą i czasem.                               |

### Wyjaśnienie poziomów dziennika

- **DEBUG**: Szczegółowe komunikaty diagnostyczne (szybkość obliczania TPI, wartości pośrednie, itp.). Bardzo szczegółowe.
- **INFO**: Ogólne informacje (zmiany stanu, decyzje termostatu, aktywacje funkcji).
- **WARNING**: Ostrzeżenia (niewarunkowe warunki, wykryte anomalne wartości).
- **ERROR**: Błędy (awarie czujnika, nieobsługiwane wyjątki).

**Wskazówka**: Zacznij od `INFO` dla wstępnej analizy, a następnie przejdź na `DEBUG`, jeśli potrzebujesz więcej szczegółów.

## Odbieranie i pobieranie pliku

Po wywołaniu akcji wyświetli się **trwałe powiadomienie** zawierające:

- Podsumowanie eksportu (termostat, okres, poziom, liczba wpisów)
- **URL do pobrania** do skopiowania/wklejenia w przeglądarce

URL jest **absolutnym podpisanym linkiem** (z tokenem uwierzytelniającym ważnym 24 godziny). Z powodu ograniczenia frontendu Home Assistant **nie można kliknąć bezpośrednio na link** w powiadomieniu — należy go **skopiować i wkleić** do nowej karty przeglądarki, aby uruchomić pobieranie.

Pobrany plik to plik `.log` o nazwie np.:
```
vtherm_logs_salon_20250314_102500.log
```

Plik jest tymczasowo przechowywany na serwerze Home Assistant w folderze dostępnym przez sieć lokalną (w `config/www/versatile_thermostat/`).

> **Uwaga**: Stare pliki dzienników (> 24h) są automatycznie usuwane z serwera.

> **Ważne**: Aby URL do pobrania był prawidłowy, musisz skonfigurować swój wewnętrzny lub zewnętrzny URL w **Ustawienia > System > Sieć** w Home Assistant. W przeciwnym razie URL może zawierać wewnętrzny adres IP kontenera Docker.

## Format i zawartość pliku dziennika

Plik zawiera:

1. **Nagłówek** z informacjami o eksporcie:
   ```
   ================================================================================
   Versatile Thermostat - Log Export
   Thermostat : Salon (climate.salon)
   Period     : 2025-03-14 08:00:00 → 2025-03-14 10:00:00 UTC
   Level      : INFO and above
   Entries    : 342
   Generated  : 2025-03-14 10:25:03 UTC
   ================================================================================
   ```

2. **Wpisy dziennika**, jeden na wiersz, z:
   - Sygnaturą czasową (data + godzina UTC)
   - Poziomem (`[INFO]`, `[DEBUG]`, `[WARNING]`, `[ERROR]`)
   - Nazwą modułu Python (gdzie został wygenerowany dziennik)
   - Komunikatem

Przykładowy wpis:
```
2025-03-14 08:25:12.456 INFO    [base_thermostat    ] Salon - Current temperature is 20.5°C
2025-03-14 08:30:00.001 INFO    [prop_algo_tpi      ] Salon - TPI calculated on_percent=0.45
2025-03-14 08:30:00.123 WARNING [safety_manager     ] Salon - No temperature update for 35 min
```

Następnie możesz **analizować ten plik** za pomocą:
- Zwykłego edytora tekstowego
- Skryptu Python do przetwarzania danych
- Narzędzia takiego jak `grep`, `awk`, `sed`, itp. do filtracji ręcznej

## Praktyczne przykłady

### Przykład 1: Debugowanie anomalnej temperatury przez 30 minut

**Cel**: Zrozumienie, dlaczego termostat w salonie źle zarządza swoją temperaturą.

**Akcja do wywołania**:
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.salon
  log_level: DEBUG              # Chcemy wszystkie szczegóły
  period_start: "2025-03-14T14:00:00"
  period_end: "2025-03-14T14:30:00"
```

**Analiza pliku**:
- Wyszukaj „Current temperature", „Target temperature", aby zobaczyć ewolucję
- Wyszukaj „TPI calculated", aby zobaczyć obliczenie procentu aktywacji
- Wyszukaj „WARNING" lub „ERROR", aby zidentyfikować anomalie

---

### Przykład 2: Walidacja prawidłowego wykrycia obecności

**Cel**: Weryfikacja, że czujnik obecności prawidłowo zmienił stan termostatu.

**Akcja do wywołania**:
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.biuro
  log_level: INFO
  period_start: "2025-03-15T12:00:00"      # Początek okresu (format ISO)
  period_end: "2025-03-15T14:00:00"        # Koniec okresu
```

**Analiza pliku**:
- Wyszukaj wiadomości zawierające „presence" lub „motion"
- Sprawdź, czy zmiany presetów są prawidłowo rejestrowane

---

### Przykład 3: Sprawdzenie wszystkich termostatów w krótkim okresie

**Cel**: Pobieranie ogólnej historii wszystkich termostatów przez godzinę, filtrowanej do ostrzeżeń i błędów.

**Akcja do wywołania**:
```yaml
action: versatile_thermostat.download_logs
data:
  log_level: WARNING            # Brak entity_id → wszystkie VTherm
  period_start: "2025-03-15T13:00:00"
  period_end: "2025-03-15T14:00:00"
```

**Analiza pliku**:
- Plik będzie zawierać wszystkie dzienniki WARNING i ERROR ze wszystkich termostatów
- Przydatne do sprawdzenia, czy nie doszło do żadnych anomalnych alertów

---

## Zaawansowana konfiguracja

Domyślnie dzienniki są przechowywane w pamięci przez **4 godziny** na serwerze Home Assistant. Możliwy czas trwania można dostosować w `configuration.yaml`:

```yaml
versatile_thermostat:
  log_buffer_max_age_hours: 6   # Przechowuj dzienniki przez 6 godzin zamiast 4
```

Możesz określić **dowolną dodatnią liczbę całkowitą** (w godzinach) zgodnie ze swoimi potrzebami. Oto kilka przykładów z szacunkowym zużyciem pamięci:

| Czas trwania | Scenariusz 10 VTherm | Scenariusz 20 VTherm |
| ------------ | -------------------- | -------------------- |
| **1 h**      | ~0,5-1 MB            | ~2-5 MB              |
| **2 h**      | ~1-2 MB              | ~4-10 MB             |
| **4 h**      | ~2-5 MB              | ~8-20 MB             |
| **6 h**      | ~3-7 MB              | ~12-30 MB            |
| **8 h**      | ~4-10 MB             | ~16-40 MB            |
| **24 h**     | Limit 40-50 MB       | Limit 40-50 MB       |

> **Uwaga**: Zwiększenie czasu retencji zużywa więcej pamięci na serwerze. Automatyczna ochrona ogranicza całkowite zużycie do max. ~40-50 MB.

---

## Porady dotyczące użytkowania

1. **Zacznij od poziom INFO**: Mniej szumu, łatwiejsze do czytania
2. **Kieruj się konkretnym termostatem**: Bardziej istotne niż wszystkie VTherm
3. **Zmniejsz okres**: Zamiast 24h, pobierz tylko okres problematyczny
4. **Użyj witryny do analizy**: Witryna [Versatile Thermostat](https://www.versatile-thermostat.org/) pozwala analizować dzienniki i rysować krzywe. Jest to niezbędny suplement do tej funkcji
5. **Używaj narzędzi do przetwarzania**: `grep`, `sed`, `awk` lub Python do analizy dużych plików
6. **Zachowaj nagłówek**: Przydatne do dostarczenia kontekstu w przypadku zgłoszenia problemu

---
