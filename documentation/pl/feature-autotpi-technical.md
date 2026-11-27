# 🧠 Auto TPI: Pogłębiony przewodnik techniczny

> [!NOTE]
> Ten dokument jest przeznaczony dla zaawansowanych użytkowników, którzy chcą szczegółowo zrozumieć działanie Auto TPI. Bardziej przystępne wprowadzenie znajduje się w [Przewodniku użytkownika Auto TPI](feature-autotpi.md).

---

## Spis treści

1. [Algorytm TPI](#algorytm-tpi)
2. [Model pomieszczenia i współczynniki docelowe](#model-pomieszczenia-i-współczynniki-docelowe)
3. [Cykl uczenia](#cykl-uczenia)
4. [Uczenie Kint](#uczenie-kint)
5. [Uczenie Kext](#uczenie-kext)
6. [Ciągłe uczenie Kext](#ciągłe-uczenie-kext)
7. [Parametry i stałe](#parametry-i-stałe)
8. [Usługi i API](#usługi-i-api)
9. [Diagnostyka i rozwiązywanie problemów](#diagnostyka-i-rozwiązywanie-problemów)

---

## Algorytm TPI

### Podstawowa zasada

Algorytm **TPI** (Time Proportional & Integral) oblicza **procent mocy** w każdym cyklu. Procent ten określa, jak długo grzejnik będzie aktywny w trakcie cyklu (np. 60% w 10-minutowym cyklu = 6 minut grzania).

### Podstawowy wzór

```
Power = (Kint × ΔT_indoor) + (Kext × ΔT_outdoor)
```

Gdzie:
- **Kint** (`tpi_coef_int`): Współczynnik wewnętrzny, reaguje na odchylenie od nastawy
- **Kext** (`tpi_coef_ext`): Współczynnik zewnętrzny, kompensuje straty cieplne
- **ΔT_indoor** = Nastawa − Temperatura wewnętrzna
- **ΔT_outdoor** = Nastawa − Temperatura zewnętrzna

Moc jest ograniczona do 0–100%. W trybie chłodzenia różnice są odwrócone.

### Rola współczynników

| Współczynnik | Rola | Sytuacja uczenia |
|-------------|------|-------------------|
| **Kint** | Określa **reaktywność**: im wyższy, tym mocniej ogrzewanie reaguje na odchylenie | Podczas **wzrostu temperatury** (odchylenie ≥ 0,3°C na początku okna, moc między 0 a 100%) |
| **Kext** | Kompensuje **straty cieplne**: dostarcza moc potrzebną do utrzymania nastawy | Gdy pomieszczenie jest **ustabilizowane blisko nastawy** |

---

## Model pomieszczenia i współczynniki docelowe

Auto TPI opiera się na prostym modelu pomieszczenia (jedna pojemność cieplna, jedna strata na zewnątrz):

```
dT/dt = a × P − b × (T − T_ext)
```

- `a` (°C/h): szybkość wzrostu temperatury przy 100% mocy, bez strat
- `b` (1/h): szybkość strat, odwrotność stałej czasowej pomieszczenia
- `P`: moc grzewcza (0–1)

**Kext**: przy nastawie potrzebna moc wynosi `P = (b/a) × (Setpoint − T_ext)`. Idealny Kext to zatem `b/a`. Przy tej wartości sam człon zewnętrzny utrzymuje nastawę i nie pozostaje żadne statyczne odchylenie.

**Kint**: gdy Kext kompensuje straty, pomieszczenie rośnie z szybkością `a × Kint × odchylenie`. Aby zmniejszyć odchylenie ze stałą czasową `T_cl`, Kint musi wynosić `1 / (a × T_cl)`. Słabe źródło ciepła (małe `a`) potrzebuje więc większego Kint.

`T_cl` to docelowa stała czasowa pętli zamkniętej. Wyprowadza się ją z **czasu nagrzewania** źródła ciepła:

```
T_cl = 2 × (heating_time + cycle / 2)     ograniczone do [30 min, 180 min]
```

Wolne źródło ciepła (długi czas nagrzewania) daje dłuższe `T_cl`, a więc łagodniejszą regulację bez przekroczenia nastawy.

Nie trzeba znać ani `a`, ani `b`: oba współczynniki są uczone z obserwacji, małymi krokami, w kierunku tych celów.

---

## Cykl uczenia

Na końcu każdego cyklu TPI menedżer sprawdza cykl i aktualizuje uczenie.

### Migawka cyklu

Na początku każdego cyklu system zapisuje temperatury wewnętrzną i zewnętrzną, nastawę, moc i tryb HVAC. Na końcu cyklu wykorzystywana jest faktycznie zastosowana moc (po ograniczeniach czasowych).

### Warunki ważności cyklu

Cykl jest ignorowany przy uczeniu, jeśli:

| Warunek | Powód |
|-----------|--------|
| Moc ≤ 0% lub ≥ 100% | Cykl nasycony nic nie mówi o mocy, którą należy zastosować |
| Cykl krótszy lub dłuższy niż oczekiwano | Przerwany cykl lub luka w danych |
| Ograniczenie mocy w trakcie cyklu | Ogrzewanie zostało ograniczone przez inną funkcję |
| Kocioł centralny wyłączony | Grzejnik nie grzał |
| Wykryto awarię ogrzewania | Grzejnik nie grzał zgodnie z żądaniem |
| Pierwszy cykl po zatrzymaniu | Brak poprzedniego stanu |
| Nastawa zmieniona w trakcie cyklu | Cykl łączy dwa cele |
| \|Nastawa − T_ext\| < 1°C (Kext) | Człon zewnętrzny jest zbyt mały, by go nauczyć |

### Koniec sesji

Sesja kończy się, gdy Kint zostanie nauczony w ciągu **15 okien**, a Kext w ciągu **50 cykli**. Współczynniki są wtedy zapisywane w konfiguracji i wysyłane jest powiadomienie.

---

## Uczenie Kint

Kint uczy się w **oknach** kilku kolejnych cykli, nigdy na podstawie pojedynczego cyklu: przy 5-minutowym cyklu zmiana temperatury jest tego samego rzędu co rozdzielczość czujnika (często 0,1°C).

### Zasady okien

- Okno otwiera się, gdy pomieszczenie jest oddalone od nastawy o co najmniej **0,3°C**, i dopiero **T_cl / 2** po ostatniej zmianie nastawy, zmianie trybu, cyklu przy 0% lub nieprawidłowym cyklu (źródło ciepła potrzebuje tego czasu, aby zareagować). Cykl przy 100% zamyka okno bez ponownego uruchamiania tego opóźnienia: źródło ciepła już pracuje.
- Każdy cykl okna musi być prawidłowy, z mocą między 0 a 100%. W przeciwnym razie okno jest zamykane bez uczenia.
- Czas trwania okna ustala się w chwili jego otwarcia na podstawie szybkości wzrostu zmierzonej w ciągu poprzednich 20 minut, tak aby okno obejmowało około 0,3°C zmiany: od 10 minut (i co najmniej 2 cykle) przy szybkim wzroście do **max(30 min, T_cl)** przy wolnym. Wykorzystuje wyłącznie dane starsze niż okno, więc nigdy nie zależy od zmiany, którą okno mierzy. Następne okno zaczyna się tam, gdzie kończy się poprzednie, na tym samym warunku 0,3°C.
- Okno jest akceptowane wyłącznie na podstawie swojego czasu trwania i początkowego odchylenia. Nigdy nie zależy od zmierzonej zmiany temperatury: w przeciwnym razie zachowane byłyby tylko okna, w których szum zwiększył wzrost, co zniekształciłoby Kint.

### Wzór aktualizacji

```
mean_gap    = Setpoint − (T_start + T_end) / 2
target_rate = mean_gap / T_cl
rate        = (T_end − T_start) / duration
ratio       = target_rate / rate          (1.15 if rate ≤ 0)
Kint_new    = Kint × clamp(ratio, 1/1.15, 1.15)
```

Kint zmienia się najwyżej o ±15% na okno i pozostaje w przedziale [0.01, 1.0]. Ograniczony krok zbiega do mediany stosunku: pojedyncze okno zakłócone szumem lub słońcem nie może mocno przesunąć Kint.

Jeśli pomieszczenie przekroczyło nastawę w trakcie okna (`mean_gap ≤ 0`), okno nie jest wykorzystywane.

---

## Uczenie Kext

### Warunek stabilizacji

Wzrost po zmianie nastawy należy do Kint. Kext jest uczony tylko:
- co najmniej **3 × T_cl** po ostatniej zmianie nastawy,
- oraz gdy temperatura wróciła w granice **0,3°C** od nastawy lub po **12 × T_cl**, aby nadal dało się skorygować bardzo błędny Kext (duże statyczne odchylenie).

### Wzór

Gdy pomieszczenie jest ustabilizowane, a odchylenie jest małe (|odchylenie| ≤ 1°C lub dowolne odchylenie powyżej nastawy, gdy moc wynosi co najmniej 10%):

```
Kext_target = Kext + Kint × (ΔT_indoor / ΔT_outdoor)
```

Pozostałe wewnętrzne odchylenie jest przeliczane na moc zewnętrzną, która by je usunęła. Kext_target jest ograniczony do 1.2.

Próbki powyżej nastawy są ignorowane, gdy moc jest bardzo niska (pomieszczenie naturalnie stygnie lub jest ogrzewane przez zewnętrzne źródło).

### Wygładzanie

Próbki są łączone za pomocą **średniej ważonej**:

```
Kext_new = (Kext × n + Kext_target) / (n + 1)       n = liczba próbek, ograniczona do 50
```

Skonfigurowany Kext nie ma wagi: pierwsza próbka go zastępuje, a każda kolejna waży 1/(n+1). Dla stałej wielkości średnia daje najmniej zaszumiony szacunek.

---

## Ciągłe uczenie Kext

Gdy **Continuous Kext Learning** jest włączone, Kext jest nadal dostosowywany po sesji, aby śledzić powolne zmiany strat.

### Warunki kwalifikacji
- Co najmniej jedna próbka Kext z sesji uczenia.
- Te same warunki cyklu i stabilizacji co przy uczeniu Kext.

### Wzór

```
Kext_new = Kext × (1 − α) + Kext_target × α        α = 0.04
```

Stała waga pozwala Kext podążać za wielkością, która powoli się zmienia. Nowa wartość jest zapisywana w konfiguracji, gdy zmieni się o więcej niż 0.001, a regulacja natychmiast ją wykorzystuje.

---

## Parametry i stałe

### Parametry konfigurowalne

| Parametr | Opis |
|-----------|-------------|
| `heater_heating_time` | Czas nagrzewania źródła ciepła (min). Określa `T_cl`. |
| `auto_tpi_continuous_kext` | Ciągłe uczenie Kext po zakończeniu sesji. |

### Stałe wewnętrzne

| Stała | Wartość | Rola |
|----------|-------|------|
| Minimalne odchylenie dla okna Kint | 0.3°C | Kint jest uczony tylko wtedy, gdy pomieszczenie ma odchylenie do zmniejszenia |
| Czas trwania okna | 10 min do max(30 min, T_cl), ustalany na podstawie poprzedniej szybkości wzrostu | Około 0.3°C zmiany na okno |
| Maksymalny krok Kint | ×1.15 / ÷1.15 | Ograniczony krok na okno |
| Granice Kint | 0.01 – 1.0 | |
| Okna Kint do zakończenia sesji | 15 | |
| Cykle Kext do zakończenia sesji | 50 | |
| Stabilizacja Kext | 3 × T_cl, potem blisko nastawy (lub 12 × T_cl) | Kext nie jest uczony podczas wzrostu |
| Maksymalne odchylenie dla Kext | 1.0°C | |
| Maksymalny Kext | 1.2 | |
| Alfa ciągłego Kext | 0.04 | |

---

## Usługi i API

### `versatile_thermostat.set_auto_tpi_mode`

Uruchamia lub zatrzymuje sesję uczenia.

| Parametr | Typ | Opis |
|-----------|-----|-------------|
| `auto_tpi_mode` | boolean | `true`, aby uruchomić, `false`, aby zatrzymać |
| `reinitialise` | boolean | `true` (domyślnie): zacznij od nowa od skonfigurowanych współczynników. `false`: wznów poprzednią sesję |

```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.living_room
data:
  auto_tpi_mode: true
  reinitialise: true
```

---

## Diagnostyka i rozwiązywanie problemów

### Czujnik diagnostyczny

Encja: `sensor.<name>_auto_tpi_learning_state`

Stan: `active` podczas sesji, w przeciwnym razie `off`.

| Atrybut | Opis |
|-----------|-------------|
| `heating_cycles_count` | Łączna liczba zaobserwowanych cykli |
| `coeff_int_cycles` | Nauczone okna Kint |
| `coeff_ext_cycles` | Nauczone cykle Kext |
| `model_confidence` | Postęp sesji 0.0 – 1.0 |
| `calculated_coef_int` | Bieżący Kint |
| `calculated_coef_ext` | Bieżący Kext |
| `last_learning_status` | Wynik ostatniego cyklu |
| `learning_start_dt` | Początek sesji |

### Typowe statusy uczenia

| Status | Znaczenie |
|--------|---------|
| `learned_indoor_heat` / `learned_indoor_cool` | Kint zaktualizowany na końcu okna |
| `learned_outdoor_heat` / `learned_outdoor_cool` | Kext zaktualizowany |
| `kext_waiting_settling` | Kext czeka, aż pomieszczenie się ustabilizuje po zmianie nastawy |
| `kint_window_crossed_setpoint` | Pomieszczenie przekroczyło nastawę w trakcie okna, okno nie zostało użyte |
| `power_out_of_range(...)` | Moc na poziomie 0% lub 100%, cykl zignorowany |
| `cycle_gap_detected` / `cycle_too_short` | Nieprawidłowy czas trwania cyklu, cykl zignorowany |
| `setpoint_changed_during_cycle` | Nastawa zmieniona w trakcie cyklu |
| `outdoor_delta_too_small(...)` | Temperatura zewnętrzna zbyt bliska nastawy |
| `gap_too_large_for_outdoor(...)` | Odchylenie powyżej 1°C, Kext nie nauczony |
| `cooling_down_naturally` / `warming_up_naturally` | Pomieszczenie wraca do nastawy samo, Kext bez zmian |
| `continuous_kext_learned_heat` / `continuous_kext_learned_cool` | Kext zaktualizowany przez ciągłe uczenie |

### Rozwiązywanie problemów

| Objaw | Prawdopodobna przyczyna | Działanie |
|---------|--------------|--------|
| Kint nie postępuje | Brak wzrostu o co najmniej 0.3°C przy nienasyconej mocy | Obniż nastawę o 1–2°C na kilka godzin, a następnie przywróć |
| Przekroczenie po każdym wzroście | Czas nagrzewania za krótki dla źródła ciepła | Zwiększ czas nagrzewania, a następnie uruchom sesję ponownie |
| Wolny wzrost, brak przekroczenia | Czas nagrzewania za długi | Zmniejsz czas nagrzewania, a następnie uruchom sesję ponownie |
| Pomieszczenie zawsze poniżej lub powyżej nastawy | Kext jeszcze nie nauczony lub straty się zmieniły | Pozwól sesji się zakończyć lub włącz ciągłe uczenie Kext |
| Uczenie w ogóle nie postępuje | Ogrzewanie stale na 100% (ekstremalny mróz) | Poczekaj na łagodniejszą pogodę |

### Plik trwałości

**Lokalizacja**: `.storage/versatile_thermostat.auto_tpi.<unique_id>`

Plik zawiera stan uczenia i jest przywracany po ponownym uruchomieniu Home Assistant. Gdy nie zarejestrowano jeszcze żadnego cyklu uczenia, używane są skonfigurowane współczynniki. Poza sesją uczenia konfiguracja jest punktem odniesienia: współczynnik zmieniony w konfiguracji (opcje lub usługa `set_tpi_parameters`) zastępuje zapisany.
