# Funkcja Auto TPI


## Wstęp

Funkcja **Auto TPI** (lub samouczenia) stanowi istotny postęp w rozwoju integracji _*Termostat VTherm*_. Umożliwia ona termostatowi **automatyczny** dobór współczynników regulacji (`Kp` i `Ki`) poprzez analizę zachowania termicznego pomieszczenia.

W trybie TPI _*(Time Proportional & Integral)*_ termostat oblicza procent otwarcia lub czas grzania na podstawie różnicy między temperaturą docelową a temperaturą wewnętrzną (`Kp`) oraz wpływu temperatury zewnętrznej (`Ki`).

Znalezienie odpowiednich współczynników (`tpi_coef_int` i `tpi_coef_ext`) jest często skomplikowane i wymaga wielu prób. Od teraz **Auto TPI robi to za Ciebie.**

## Wymagania wstępne

Aby funkcja _*Auto TPI*_ działała efektywnie, potrzebne są:
1. **Niezawodny sensor temperatury**: Sensor nie może być narażony na bezpośredni wpływ źródła ciepła (nie umieszczaj go na grzejniku!).
2. **Sensor temperatury zewnętrznej**: Dokładny pomiar temperatury zewnętrznej jest niezbędny.
3. **Załączony tryb TPI**: Ta funkcja ma zastosowanie tylko w przypadku korzystania z algorytmu TPI (`termostat na przełączniku`, `termostat na zaworze` lub `termostat na klimacie` w trybie TPI).
4. **Prawidłowa konfiguracja zasilania**: Prawidłowo zdefiniuj parametry związane z czasem grzania (patrz poniżej).
5. **Optymalny rozruch (ważne)**: Aby funkcja uczenia działała efektywnie, zaleca się jej załączenie, gdy różnica między aktualną temperaturą a temperaturą docelową jest znacząca (**co najmniej 2°C**).
   * *Wskazówka*: Wychłodź pomieszczenie, załącz funkcję uczenia, a następnie przywróć żądane ustawienie docelowe (komfort termiczny).

## Konfiguracja

Automatyczna konfiguracja TPI jest zintegrowana z procesem konfiguracji TPI dla **każdego termostatu**.

> **Uwaga**: Automatycznej nauki TPI nie można skonfigurować z poziomu konfiguracji centralnej, ponieważ każdy termostat wymaga własnych parametrów uczenia.

1. Przejdź do konfiguracji jednostki VTherm (**Konfiguracja**).
2. Wybierz **Parametry TPI**.
3. **Ważne**: Aby uzyskać dostęp do parametrów lokalnych, należy wyłączyć opcję **Użyj centralnej konfiguracji TPI**.
4. U dołu następnego ekranu (Atrybuty TPI) zaznacz pole wyboru **Załącz naukę Auto TPI**.

Po dokonaniu tego wyboru pojawi się dedykowany kreator konfiguracji, składający się z kilku kroków:

### Krok 1: Informacje ogólne

* **Załącz Auto TPI**: Umożliwia załączenie lub wyłączenie uczenia.
* **Powiadomienie**: Jeśli ta opcja jest załączona, powiadomienie zostanie wysłane **tylko** po uznaniu procesu uczenia za zakończony (50 cykli na współczynnik).
* **Aktualizuj konfigurację**: Jeśli ta opcja jest zaznaczona, zapamiętane współczynniki TPI zostaną **automatycznie** zapisane w konfiguracji termostatu **tylko po uznaniu procesu uczenia za zakończony**. Jeśli ta opcja jest odznaczona, zapamiętane współczynniki będą używane do bieżącej regulacji TPI, ale nie są zapisywane w konfiguracji.
* **Ciągłe uczenie** (`auto_tpi_continuous_learning`): Jeśli ta opcja jest załączona, uczenie będzie kontynuowane w nieskończoność, nawet po zakończeniu początkowych 50 cykli. Pozwala to na ciągłe dostosowywanie się termostatu do stopniowych zmian temperatury otoczenia (np. zmian sezonowych, starzenia się budynku). Jeśli ta opcja jest zaznaczona, zapamiętane parametry zostaną zapisane w konfiguracji (jeśli zaznaczona jest również opcja **Aktualizuj konfigurację**) na koniec każdego cyklu, gdy model zostanie uznany za stabilny (np. po pierwszych 50 cyklach).
* **Wykrywanie zmian w reżimie**: Po załączeniu ciągłego uczenia system monitoruje ostatnie błędy nauki. W przypadku wykrycia **systematycznego błędu** (np. spowodowanego zmianą pory roku, izolacji lub systemu grzewczego), szybkość uczenia (alfa) jest **tymczasowo zwiększana** (do 3x, z ograniczeniem do 15%) w celu przyspieszenia adaptacji. Ta funkcja pomaga termostatowi szybko dostosować się do nowych warunków termicznych bez konieczności ręcznej interwencji.
* **Zapis wyuczonego współczynnika zewnętrznego** (`auto_tpi_keep_ext_learning`): Po załączeniu, współczynnik zewnętrzny (`Kext`) będzie kontynuował uczenie nawet po osiągnięciu 50 cykli, dopóki współczynnik wewnętrzny (`Kint`) nie osiągnie stabilności.
**Uwaga:** Konfiguracja jest zachowywana tylko wtedy, gdy oba współczynniki są stabilne.
* **Czas grzania/chłodzenia**: Zdefiniuj bezwładność grzejnika ([patrz: Konfiguracja termiczna](#thermal-configuration-critical)).
* **Próg współczynnika temperatury wewnętrznej**: Limity bezpieczeństwa dla współczynnika temperatury wewnętrznej (maks. 3,0). **Uwaga**: Jeśli ten limit zostanie zmieniony w procesie konfiguracji, nowa wartość zostanie **natychmiast** zastosowana do zapamiętanych współczynników, jeśli przekroczą one nowy limit (wymaga to ponownego uruchomienia integracji, co ma miejsce po zapisaniu modyfikacji za pomocą opcji).

* **Szybkość grzania** (`auto_tpi_heating_rate`): Docelowa szybkość wzrostu temperatury w °C/h. ([patrz: Konfiguracja parametrów](#heating-cooling-rate-configuration))
* **Szybkość chłodzenia** (`auto_tpi_cooling_rate`): Docelowa szybkość spadku temperatury w °C/h. ([patrz: Konfiguracja parametrów](#heating-cooling-rate-configuration))

    *Uwaga: Nie jest konieczne używawanie maksymalnej szybkości grzania/chłodzenia. Można bez problemu użyć niższej wartości, w zależności od rozmiaru systemu ogrzewania, **co jest zdecydowanie zalecane**.
Im bliżej maksymalnej wydajności, tym wyższy będzie współczynnik `Kint`, określony podczas procesu uczenia.*

    *Dlatego po zdefiniowaniu wydajności za pomocą usługi dedykowanej lub ręcznego jej oszacowania, należy użyć niższej szybkości grzania/chłodzenia.
**Najważniejsze, aby nie przekraczać wydajności grzejnika w pomieszczeniu.**
Np.: Jeśli zmierzona wydajność adiabatyczna wynosi 1,5°/h, to 1°/h to standardowa i rozsądna stała.*


### Krok 2: Metoda

Wybierz algorytm uczenia:
* **Średnia**: Prosta średnia ważona. Idealnie nadaje się do szybkiej, jednorazowej nauki (łatwe resetowanie).
* **EMA**: Zmienna Średnia Wykładnicza. Zdecydowanie zalecana jest do ciągłego, długoterminowego procesu uczenia i dostrajania systemu, ponieważ faworyzuje ona ostatnie wartości.

### Krok 3: Parametry metody

Skonfiguruj określone parametry dla wybranej metody:
* **Średnia**: Waga początkowa.
* **EMA**: Początkowa wartość alfa i tempo rozkładu.

### Konfiguracja termiczna (krytyczna)

Algorytm musi rozumieć responsywność systemu grzewczego.

#### `heater_heating_time` (Czas reakcji termicznej)
Jest to całkowity czas potrzebny na to, aby system miał mierzalny wpływ na temperaturę w pomieszczeniu.

Musi on obejmować:
* Czas nagrzewania grzejnika (bezwładność materiału).
* Czas propagacji ciepła w pomieszczeniu do czujnika.

**Sugerowane wartości:**

| Typ grzejnika | Sugerowana<br>wartość |
|---|---|
| Grzejnik elektryczny (konwektor), sensor w pobliżu | 2-5 min |
| Grzejnik bezwładnościowy (olejowy, żeliwny), sensor w pobliżu | 5-10 min |
| Ogrzewanie podłogowe lub duże pomieszczenie z oddalonym czujnikiem | 10-20 min |

> Nieprawidłowa wartość może zaburzyć obliczenia sprawności i uniemożliwić poprawne uczenie.

#### `heater_cooling_time` (Czas chłodzenia)
Czas potrzebny do schłodzenia grzejnika po zatrzymaniu. Służy do oszacowania, czy grzejnik jest „gorący”, czy „zimny” na początku cyklu za pomocą `cold_factor`. `cold_factor` koryguje bezwładność grzejnika i działa jak **filtr**: jeśli czas nagrzewania jest zbyt krótki w porównaniu z szacowanym czasem nagrzewania, uczenie dla tego cyklu zostanie zignorowane (aby zapobiec zakłóceniom).

### Konfiguracja szybkości grzania/chłodzenia

Algorytm wykorzystuje **Szybkość grzania/chłodzenia** (`auto_tpi_heating_rate`/`cooling_rate` w °C/h) jako punkt odniesienia do obliczenia współczynnika temperatury wewnętrznej (`Kint`). Wartość ta powinna reprezentować **pożądaną** lub **osiągalną** szybkość wzrostu lub spadku temperatury przy regulacji na poziomie 100%.

> **Kalibracja**: Tę wartość można automatycznie odczytać za pomocą usługi `Kalibracja wydajności` z historii termostatu w _*Home Assistancie*_.

Jeśli nie korzystasz z tej usługi, musisz ją ręcznie zdefiniować.

Chcemy oszacować tzw. wartość **adiabatyczną** (bez strat ciepła).
Aby oszacować ją samodzielnie, metoda jest dość prosta (przykład dla grzania):

***I - Najpierw ustalamy współczynnik chłodzenia*** (który powinien być dość zbliżony do współczynnika zewnętrznego regulacji TPI).

1) Schładzamy pomieszczenie, wyłączając ogrzewanie na określony czas (na przykład 1 godzinę) i mierzymy zmianę temperatury, którą nazwiemy `**ΔTcool = Tend - Tstart**` (np. jeśli temperatura wzrośnie z 19°C do 18°C ​​w ciągu 1 godziny, `ΔTcool` = -1).
Zanotujmy również czas, jaki upłynął między dwoma pomiarami, który nazwiemy `**Δtcool**` (w godzinach).
1) Obliczamy szybkość schładzania:
**`Rcool` = `ΔTcool` / `Δtcool`** (będzie wartością ujemną)
1) Następnie współczynnik chłodzenia:
`Tavg` = średnia między 2 zmierzonymi temperaturami
`Text` = temperatura zewnętrzna (zachowaj średnią, jeśli zmieniała się podczas pomiaru)

**`k` ≃ `-(Rcool / (Tavg - Text))`**

**Uwaga**: Możesz również użyć wartości `k` jako początkowego współczynnika zewnętrznego w konfiguracji TPI.

***II - Teraz możemy obliczyć pojemność adiabatyczną***

1) Grzanie trwa tyle samo, co chłodzenie, z termostatem ustawionym na 100% mocy.

***Ważne:** grzejnik musi być już gorący, dlatego najpierw należy uruchomić cykl grzania, aby osiągnąć maksymalną temperaturę.*

Aby zapewnić pełną wydajność grzejnika przez cały czas pomiaru, znacznie podnosimy żądaną temperaturę docelową.

Zanotuj temperaturę początkową, temperaturę docelową i czas pomiaru.

2) Obliczamy `Rheat`, czyli obserwowaną zmianę temperatury:

- **`ΔTheat = Tend - Tstart`**
- **`Δtheat`:** czas, jaki upłynął między dwoma pomiarami
- **`Rheat = ΔTheat / Δtheat`**

3) Możemy wreszcie obliczyć naszą pojemność adiabatyczną:
- **`Radiab = Rheat + k(Tavg − Text)`**

## Jak to działa?

Auto TPI działa cyklicznie:

1. **Obserwacja**: W każdym cyklu (np. co 10 min.) termostat (który jest w trybie `HEAT` lub `COOL`) mierzy temperaturę na początku i na końcu cyklu, a także zużycie energii.
2. **Walidacja**: Sprawdza, czy cykl nadaje się do procesu uczenia:
   * Proces uczenia jest oparty na trybie `hvac_mode` termostatu (`HEAT` lub `COOL`), niezależnie od aktualnego stanu grzejnika (`heating`/`jałowy`).
   * Moc nie jest nasycona (z wyłączeniem zakresu od 0% do 100%).
   * Różnica temperatur jest znacząca.
   * System jest stabilny (bez kolejnych awarii).
   * Cykl nie został przerwany przez zanik zasilania ani otwarcie okna.
3. **Obliczanie (uczenie)**:
   * **Przypadek 1: Współczynnik temperatury wewnętrznej**. Jeśli temperatura zmieniła się znacząco w prawidłowym kierunku (> 0,05°C), obliczany jest stosunek między rzeczywistą ewolucją **(w całym cyklu, wliczając bezwładność)** a oczekiwaną ewolucją teoretyczną (skorygowaną o skalibrowaną wydajność). Dostosowuje `CoeffInt`, aby zmniejszyć różnicę.
   * **Przypadek 2: Współczynnik temperatury zewnętrznej**. Jeśli uczenie w warunkach pomieszczenia nie było możliwe (niespełnione warunki lub awaria), a uczenie jest istotne (znaczna różnica temperatur > 0,1°C), funkcja dostosowuje `CoeffExt` **progresywnie**, aby skompensować straty ciepła. Wzór pozwala na zwiększanie lub zmniejszanie tego współczynnika w zależności od potrzeb, aby osiągnąć stabilność.
4. **Aktualizacja**: Nowe współczynniki są wygładzane i zapisywane na potrzeby następnego cyklu.

### Bezpieczeństwo aktywacji
Aby uniknąć niezamierzonej aktywacji:
1. Usługa `set_auto_tpi_mode` odmawia załączenia uczenia, jeśli pole wyboru „Załącz uczenie Auto TPI” nie jest zaznaczone w konfiguracji termostatu.
2. Jeśli odznaczysz to pole w konfiguracji, gdy funcja uczenia była aktywna, zostanie ona automatycznie zatrzymana po ponownym załadowaniu integracji.

## Atrybuty i sensory

Dedykowany sensor `sensor.<thermostat_name>_auto_tpi_learning_state` umożliwia śledzenie stanu uczenia.

**Dostępne atrybuty:**

* `active`: Uczenie jest załączone.
* `heating_cycles_count`: Łączna liczba obserwowanych cykli.
* `coeff_int_cycles`: Liczba korekt współczynnika temperatury wewnętrznej.
* `coeff_ext_cycles`: Liczba korekt współczynnika temperatury zewnętrznej.
* `model_confidence`: Wskaźnik ufności (od 0,0 do 1,0) co do jakości ustawień. Ograniczony do 100% po 50 cyklach dla każdego współczynnika (nawet jeśli uczenie jest kontynuowane).
* `last_learning_status`: Przyczyna ostatniego sukcesu lub niepowodzenia (np. `learned_indoor_heat`, `power_out_of_range`).
* `calculated_coef_int` / `calculated_coef_ext`: Bieżące wartości współczynników.
* `learning_start_dt`: Data i godzina rozpoczęcia uczenia (przydatne w przypadku wykresów).

## Usługi

### Usługa kalibracji (`versatile_thermostat.auto_tpi_calibrate_capacity`)

Ta usługa szacuje **wydajność adiabatyczną** systemu (`max_capacity` w °C/h) poprzez analizę historii sensorów.

**Zasada działania:** Usługa wykorzystuje historię **sensorów** `temperature_slope` i `power_percent` do identyfikacji momentów, w których ogrzewanie działało z pełną mocą. Używa **75. percentyla** (bliższego wartości adiabatycznej, niż mediana) i stosuje **poprawkę `Kext`**: `Wydajność = P75 + Kext_config × ΔT`.

```yaml
service: versatile_thermostat.auto_tpi_calibrate_capacity
target:
entity_id: climate.my_thermostat
data:
start_date: "2023-11-01T00:00:00+00:00" # Opcjonalne. Domyślnie 30 dni przed datą „end_date”.
end_date: "2023-12-01T00:00:00+00:00" # Opcjonalne. Domyślnie teraz.
hvac_mode: heat # Wymagane. „heat” lub „cool”.
min_power_threshold: 0.95 # Opcjonalne. Próg mocy (0.0-1.0). Domyślnie 0.95 (100%).
save_to_config: true # Opcjonalne. Zapisz obliczoną wydajność w konfiguracji. Domyślnie false.
```

> **Wynik**: Wartość pojemności adiabatycznej (`max_capacity_heat`/`cool`) jest aktualizowana w atrybutach czujnika stanu uczenia.
>
> Usługa zwraca również następujące informacje w celu analizy jakości kalibracji:
> * **`capacity`**: Szacowana pojemność adiabatyczna (w °C/h).
> * **`observed_capacity`**: Surowy 75. percentyl (przed korektą Kext).
> * **`kext_compensation`**: Zastosowana wartość korekty (Kext × ΔT).
> * **`avg_delta_t`**: Średnia wartość ΔT użyta do korekty.
> * **`reliability`**: Wskaźnik niezawodności (w %) na podstawie liczby próbek i wariancji.
> * **`samples_used`**: Liczba próbek użytych po filtrowaniu.
> * **`outliers_removed`**: Liczba wyeliminowanych wartości odbiegających.
> * **`min_power_threshold`**: Użyty próg mocy.
> * **`period`**: Liczba dni analizowanej historii.
>
> Współczynniki TPI (`Kint`/`Kext`) są następnie zapamiętywane lub dostosowywane w standardowej pętli uczenia, wykorzystując je jako punkty odniesienia.

### Załączanie/wyłączanie uczenia (`versatile_thermostat.set_auto_tpi_mode`)

Ta usługa umożliwia sterowanie automatycznym zapamiętywaniem TPI bez konieczności konfigurowania termostatu.

#### Parametry

| Parametr | Typ | Domyślny | Opis |
|-----------|------|---------|------------|
| `auto_tpi_mode` | wartość logiczna | - | Załącza (`true`) lub wyłącza (`false`) uczenie |
| `reinitialise` | wartość logiczna | `true` | Kontroluje resetowanie danych podczas załączania uczenia |

#### Zachowanie parametru `reinitialise`

Parametr `reinitialise` określa sposób obsługi istniejących, wyuczonych już danych podczas załączania procesu uczenia:

- **`reinitialise: true`** (domyślnie): Czyści wszystkie dane wyuczone (współczynniki i liczniki) i rozpoczyna uczenie od nowa. Skalibrowane pojemności (`max_capacity_heat`/`cool`) są zachowywane.
- **`reinitialise: false`**: Wznawia proces uczenia zachowując wyuczone dotychczas, istniejące dane. Poprzednie współczynniki i liczniki są zachowywane, a uczenie jest kontynuowane od zachowanych wartości.

**Przykład użycia:** Umożliwia tymczasowe wyłączenie uczenia (np. podczas wakacji lub remontu), a następnie jego ponowne uruchomienie bez utraty osiągniętych postępów.

#### Przykłady

Rozpoczęcie nowego procesu uczenia (całkowity reset):
```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
entity_id: climate.my_thermostat
data:
auto_tpi_mode: true
reinitialise: true # lub pomiń, ponieważ jest to wartość domyślna
```

Wznowienie proces uczenia bez utraty danych:
```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
entity_id: climate.my_thermostat
data:
auto_tpi_mode: true
reinitialise: false # konieczne, aby uniknąć utraty dotychczas wyuczonych wartości danych
```

Zatrzymanie procesu uczenia:
```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.my_thermostat
data:
  auto_tpi_mode: false
  reinitialise: false
```
Po zatrzymaniu procesu uczenia:
- Uczenie jest **wyłączone**, ale wyuczone dane pozostają **widoczne** w atrybutach encji `auto_tpi_learning_state`.
- Regulacja wykorzystuje współczynniki **konfiguracyjne** (a nie współczynniki wyuczone)

## Metoda obliczania średniej ważonej

Metoda **średniej ważonej** to proste i skuteczne podejście do uczenia współczynników TPI. Jest szczególnie przydatna do szybkiego, jednorazowego uczenia lub gdy chcesz łatwo zresetować współczynniki.

### Zachowanie

Metoda średniej ważonej oblicza średnią ważoną między istniejącymi współczynnikami a nowo obliczonymi wartościami. Podobnie jak metoda EMA, stopniowo zmniejsza wpływ nowych cykli w miarę postępu uczenia, ale stosuje inne podejście.

**Kluczowa cecha**: Wraz ze wzrostem liczby cykli, waga istniejącego współczynnika rośnie w porównaniu z nowym współczynnikiem. Oznacza to, że wpływ nowych cykli stopniowo maleje w miarę postępu uczenia.


### Parametry

| Parametr | Opis | Domyślne |
|-----------|------------|--------|
| **Waga początkowa**<br>(`avg_initial_weight`) | Początkowa waga nadawana<br>współczynnikom konfiguracji<br>podczas uruchamiania | 1 |

### Wzór

```yaml
avg_coeff = ((old_coeff × weight_old) + coeff_new) / (weight_old + 1)
```

gdzie:
- `old_coeff` to aktualny współczynnik
- `coeff_new` to nowy współczynnik obliczony dla tego cyklu
- `weight_old` to liczba cykli uczenia, które zostały już wykonane (minimalnie 1)

**Przykład ewolucji wag**:
- Cykl 1: weight_old = 1 → nowy współczynnik ma wagę 50%
- Cykl 10: weight_old = 10 → nowy współczynnik ma wagę ~9%
- Cykl 50: weight_old = 50 → nowy współczynnik ma wagę ~2%

### Główne cechy

1. **Prostota**: Metoda jest łatwa do zrozumienia
2. **Łatwy reset**: Współczynniki można łatwo zresetować, ponownie uruchamiając uczenie.
3. **Uczenie progresywne**: Wpływ nowych cykli maleje z czasem, stopniowo stabilizując współczynniki.
4. **Szybka konwergencja**: Metoda osiąga stabilność po około 50 cyklach.

### Porównanie z EMA

| Aspekt | Średnia ważona | EMA |
|--------|------------------|-----|
| **Złożoność** | Prosta | Bardziej złożona |
| **Mechanizm redukcji** | Waga oparta na liczbie cykli | Adaptacja alfa z rozkładem |
| **Stabilność** | Stabilna po 50 cyklach | Stabilna po 50 cyklach z rozkładem alfa |
| **Ciągła adaptacja** | Mniej odpowiednia | Bardziej odpowiednia (lepsza do stopniowych zmian) |
| **Reset** | Bardzo łatwa | Łatwa |

### Zalecenia dotyczące użycia

1. **Początkowe uczenie**: Metoda średniej ważonej doskonale nadaje się do szybkiego, początkowego uczenia
2. **Jednorazowe korekty**: Idealna, gdy chcesz dostosować współczynniki tylko raz
3. **Stabilne środowiska**: Dobrze nadaje się do względnie stabilnych środowisk termicznych

### Przykład progresji

| Cykl | Stara<br>waga | Nowa<br>waga | Nowy<br>współczynnik | Wynik |
|-------|--------------|-----------|----------|---------|
| 1 | 1 | 1 | 0,15 | (0,10 × 1 + 0,15 × 1) / 2 = 0,125 |
| 2 | 2 | 1 | 0,18 | (0,125 × 2 + 0,18 × 1) / 3 = 0,142 |
| 10 | 10 | 1 | 0,20 | (0,175 × 10 + 0,20 × 1) / 11 = 0,177 |
| 50 | 50 | 1 | 0,19 | (0,185 × 50 + 0,19 × 1) / 51 = 0,185 |

**Uwaga**: Po 50 cyklach współczynnik uznaje się za stabilny, a proces uczenia zatrzymuje się (chyba, że załączono uczenie ciągłe). Na tym etapie nowy współczynnik ma zaledwie około 2% wagi w średniej.

## Adaptacyjna metoda obliczania EMA

Metoda EMA (zmiennej średniej wykładniczej) wykorzystuje współczynnik **alfa**, który określa wpływ każdego nowego cyklu na wyuczone współczynniki.

### Zachowanie

W miarę upływu cykli **alfa stopniowo maleje**, aby ustabilizować proces uczenia:

| Cykle | Alfa (przy α₀=0,2, k=0,1) | Wpływ nowego cyklu |
|--------|----------------------------|------------------------|
| 0 | 0,20 | 20% |
| 10 | 0,10 | 10% |
| 50 | 0,033 | 3,3% |
| 100 | 0,018 | 1,8% |

### Parametry

| Parametr | Opis | Domyślne |
|-----------|------------|---------|
| **Początkowa wartość alfa** (`ema_alpha`) | Wpływ na rozruch | 0,2 (20%) |
| **Tempo rozkładu** (`ema_decay_rate`) | Prędkość stabilizacji | 0,1 |

### Wzór

```yaml
alpha(n) = alpha_initial / (1 + decay_rate × n)
```
gdzie `n` to liczba cykli uczenia.

### Przypadki szczególne

- **decay_rate = 0**: Wartość alfa pozostaje stała (klasyczne zachowanie EMA)
- **decay_rate = 1, alpha = 1**: Odpowiednik metody „średniej ważonej”

### Zalecenia

| Sytuacja | Alfa (`ema_alpha`) | Tempo rozkładu (`ema_decay_rate`) |
|---|---|---|
| **Początkowe uczenie** | `0,15` | `0,08` |
| **Uczenie dostrajające** | `0,08` | `0,12` |
| **Ciągłe uczenie** | `0,05` | `0,02` |


**Objaśnienia:**

  - **Początkowe uczenie:**

    * Alfa:* 0,15 (15% wagi początkowej)
      * Przy tych parametrach system pamięta głównie ostatnich 20 cykli*
        * Cykl 1: α = 0,15 (silna reaktywność początkowa)
        * Cykl 10: α = 0,083 (zaczyna się stabilizować)
        * Cykl 25: α = 0,050 (zwiększone filtrowanie)
        * Cykl 50: α = 0,036 (odporność końcowa)
        * Tempo rozkładu:* 0,08
          * Umiarkowany rozkład, umożliwiający szybką adaptację do pierwszych 10 cykli,
          * Optymalna równowaga między szybkością (unikanie stagnacji) a stabilnością (unikanie nadmiernej regulacji)


 - **Nauka precyzyjnego dostrajania**

   * Alfa:* 0,08 (8% wagi początkowej),
     * Dzięki tym parametrom system pamięta głównie ostatnich 50 cykli*,
     * Konserwatywny start (współczynniki już dobre),
     * Unika brutalnych, nadmiernych korekt:
       * Cykl 1: α = 0,08
       * Cykl 25: α = 0,024
       * Cykl 50: α = 0,013
       * Tempo rozkładu:* 0,12
          * Szybszy rozkład, niż początkowe uczenie,
          * Zbieżność w kierunku bardzo silnego filtrowania (stabilność),
          * Główna adaptacja w pierwszych 15 cyklach.


- **Ciągłe uczenie**

  * Alfa* = 0,05 (5% początkowej wagi)
    * Dzięki tym parametrom system pamięta głównie ostatnich 100 cykli*,
    * Bardzo konserwatywny, aby zapobiec dryftowi,
    * Umiarkowana reaktywność na stopniowe zmiany:
      * Cykl 1: α = 0,05
      * Cykl 50: α = 0,025
      * Cykl 100: α = 0,017
      * Cykl 200: α = 0,011
      * Tempo rozkładu:* 0,02
        * Bardzo powolny rozkład (długotrwała nauka), 
        * Zachowuje zdolność adaptacji nawet po setkach cykli,
        * Nadaje się do zmian sezonowych (zima/lato).

