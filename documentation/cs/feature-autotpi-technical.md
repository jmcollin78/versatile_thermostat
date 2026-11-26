# 🧠 Auto TPI: Podrobný technický průvodce

> [!NOTE]
> Tento dokument je určen pokročilým uživatelům, kteří chtějí pochopit, jak Auto TPI funguje. Pro jednodušší úvod viz [Uživatelská příručka Auto TPI](feature-autotpi.md).

---

## Obsah

1. [Algoritmus TPI](#algoritmus-tpi)
2. [Model místnosti a cílové koeficienty](#model-místnosti-a-cílové-koeficienty)
3. [Cyklus učení](#cyklus-učení)
4. [Učení Kint](#učení-kint)
5. [Učení Kext](#učení-kext)
6. [Průběžné učení Kext](#průběžné-učení-kext)
7. [Parametry a konstanty](#parametry-a-konstanty)
8. [Služby a API](#služby-a-api)
9. [Diagnostika a řešení problémů](#diagnostika-a-řešení-problémů)

---

## Algoritmus TPI

### Základní princip

Algoritmus **TPI** (Time Proportional & Integral) v každém cyklu vypočítá **procento výkonu**. Toto procento určuje, jak dlouho bude topení během cyklu aktivní (např. 60 % v 10minutovém cyklu = 6 minut topení).

### Základní vzorec

```
Power = (Kint × ΔT_indoor) + (Kext × ΔT_outdoor)
```

Kde:
- **Kint** (`tpi_coef_int`): Vnitřní koeficient, reaguje na odchylku od požadované hodnoty
- **Kext** (`tpi_coef_ext`): Vnější koeficient, kompenzuje tepelné ztráty
- **ΔT_indoor** = Požadovaná hodnota − Vnitřní teplota
- **ΔT_outdoor** = Požadovaná hodnota − Venkovní teplota

Výkon je omezen na 0–100 %. V režimu chlazení jsou rozdíly obráceny.

### Úloha koeficientů

| Koeficient | Úloha | Situace při učení |
|-------------|------|-------------------|
| **Kint** | Určuje **reaktivitu**: čím je vyšší, tím silněji topení reaguje na odchylku | Během **nárůstu teploty** (odchylka ≥ 0,3 °C na začátku okna, výkon mezi 0 a 100 %) |
| **Kext** | Kompenzuje **tepelné ztráty**: dodává výkon potřebný k udržení požadované hodnoty | Když je místnost **ustálená blízko požadované hodnoty** |

---

## Model místnosti a cílové koeficienty

Auto TPI se opírá o jednoduchý model místnosti (jedna tepelná kapacita, jedna ztráta směrem ven):

```
dT/dt = a × P − b × (T − T_ext)
```

- `a` (°C/h): rychlost nárůstu teploty při 100% výkonu, bez ztrát
- `b` (1/h): míra ztrát, převrácená hodnota časové konstanty místnosti
- `P`: topný výkon (0–1)

**Kext**: při požadované hodnotě je potřebný výkon `P = (b/a) × (Setpoint − T_ext)`. Ideální Kext je tedy `b/a`. S touto hodnotou samotný venkovní člen udrží požadovanou hodnotu a nezůstane žádná statická odchylka.

**Kint**: jakmile Kext kompenzuje ztráty, místnost stoupá rychlostí `a × Kint × odchylka`. Aby se odchylka uzavřela s časovou konstantou `T_cl`, musí být Kint `1 / (a × T_cl)`. Slabé topné těleso (malé `a`) tedy potřebuje větší Kint.

`T_cl` je cílová časová konstanta uzavřené smyčky. Odvozuje se od **doby ohřevu** topného tělesa:

```
T_cl = 2 × (heating_time + cycle / 2)     omezeno na [30 min, 180 min]
```

Pomalé topné těleso (dlouhá doba ohřevu) dává delší `T_cl`, tedy jemnější regulaci bez překmitu.

Ani `a` ani `b` není třeba znát: oba koeficienty se učí z pozorování malými kroky směrem k těmto cílům.

---

## Cyklus učení

Na konci každého TPI cyklu správce cyklus zkontroluje a aktualizuje učení.

### Záznam cyklu

Na začátku každého cyklu systém zaznamená vnitřní a venkovní teplotu, požadovanou hodnotu, výkon a režim HVAC. Na konci cyklu se použije skutečně aplikovaný výkon (po časových omezeních).

### Podmínky platnosti cyklu

Cyklus se pro učení ignoruje, pokud:

| Podmínka | Důvod |
|-----------|--------|
| Výkon ≤ 0 % nebo ≥ 100 % | Nasycený cyklus nic neříká o tom, jaký výkon použít |
| Cyklus kratší nebo delší, než se očekávalo | Přerušený cyklus nebo mezera v datech |
| Omezení výkonu během cyklu | Topení bylo omezeno jinou funkcí |
| Centrální kotel vypnut | Topné těleso netopilo |
| Zjištěna porucha vytápění | Topné těleso netopilo podle požadavku |
| První cyklus po zastavení | Chybí předchozí stav |
| Požadovaná hodnota změněna během cyklu | Cyklus mísí dva cíle |
| \|Požadovaná hodnota − T_ext\| < 1 °C (Kext) | Venkovní člen je příliš malý na to, aby se dal naučit |

### Konec relace

Relace se ukončí, jakmile je Kint naučen během **15 oken** a Kext během **50 cyklů**. Koeficienty se pak zapíší do konfigurace a odešle se oznámení.

---

## Učení Kint

Kint se učí v **oknech** několika po sobě jdoucích cyklů, nikdy ne z jediného cyklu: u 5minutového cyklu je změna teploty řádově stejná jako rozlišení čidla (často 0,1 °C).

### Pravidla oken

- Okno se otevře, když je místnost alespoň **0,3 °C** od požadované hodnoty, a to až **T_cl / 2** po poslední změně požadované hodnoty, změně režimu nebo neplatném cyklu (topné těleso na to potřebuje čas, aby zareagovalo).
- Každý cyklus okna musí být platný s výkonem mezi 0 a 100 %. Jinak se okno uzavře bez učení.
- Okno trvá nejméně **max(30 min, T_cl)**. Další okno začíná tam, kde předchozí skončilo, za stejné podmínky 0,3 °C.
- Okno se přijímá pouze podle své délky a počáteční odchylky. Nikdy nezáleží na naměřené změně teploty: jinak by se zachovala jen okna, kde šum zvýšil nárůst, a Kint by byl zkreslený.

### Vzorec aktualizace

```
mean_gap    = Setpoint − (T_start + T_end) / 2
target_rate = mean_gap / T_cl
rate        = (T_end − T_start) / duration
ratio       = target_rate / rate          (1.15 if rate ≤ 0)
Kint_new    = Kint × clamp(ratio, 1/1.15, 1.15)
```

Kint se mění nejvýše o ±15 % na okno a zůstává v rozsahu [0.01, 1.0]. Omezený krok konverguje k mediánu poměru: izolované okno narušené šumem nebo sluncem nemůže Kint výrazně posunout.

Pokud místnost během okna překročila požadovanou hodnotu (`mean_gap ≤ 0`), okno se nepoužije.

---

## Učení Kext

### Podmínka ustálení

Náběh po změně požadované hodnoty patří k Kint. Kext se učí pouze tehdy:
- nejméně **3 × T_cl** po poslední změně požadované hodnoty,
- a jakmile se místnost vrátila do **0,3 °C** od požadované hodnoty, nebo po **12 × T_cl**, aby šlo opravit i velmi chybný Kext (velká statická odchylka).

### Vzorec

Když je místnost ustálená a odchylka malá (|odchylka| ≤ 1 °C, nebo jakákoli odchylka nad požadovanou hodnotou při výkonu alespoň 10 %):

```
Kext_target = Kext + Kint × (ΔT_indoor / ΔT_outdoor)
```

Zbylá vnitřní odchylka se převede na venkovní výkon, který by ji odstranil. Kext_target je omezen na 1.2.

Vzorky nad požadovanou hodnotou se ignorují při velmi nízkém výkonu (místnost se přirozeně ochlazuje nebo ji ohřívá externí zdroj).

### Vyhlazování

Vzorky se kombinují **váženým průměrem**:

```
Kext_new = (Kext × n + Kext_target) / (n + 1)       n = počet vzorků, omezeno na 50
```

Nakonfigurovaný Kext nemá váhu: první vzorek jej nahradí, pak každý vzorek váží 1/(n+1). Pro pevnou veličinu dává průměr nejméně zašuměný odhad.

---

## Průběžné učení Kext

Je-li zapnuto **Průběžné učení Kext**, Kext se i po relaci dále upravuje, aby sledoval pomalé změny ztrát.

### Podmínky způsobilosti
- Alespoň jeden vzorek Kext z učební relace.
- Stejné podmínky cyklu a ustálení jako u učení Kext.

### Vzorec

```
Kext_new = Kext × (1 − α) + Kext_target × α        α = 0.04
```

Pevná váha umožňuje, aby Kext sledoval veličinu, která se pomalu mění. Nová hodnota se zapíše do konfigurace, pokud se změní o více než 0,001, a regulace ji okamžitě použije.

---

## Parametry a konstanty

### Nastavitelné parametry

| Parametr | Popis |
|-----------|-------------|
| `heater_heating_time` | Doba ohřevu topného tělesa (min). Určuje `T_cl`. |
| `auto_tpi_continuous_kext` | Průběžné učení Kext po relaci. |

### Interní konstanty

| Konstanta | Hodnota | Úloha |
|----------|-------|------|
| Minimální odchylka pro okno Kint | 0,3 °C | Kint se učí pouze tehdy, když má místnost odchylku, kterou je třeba uzavřít |
| Minimální délka okna | 30 min (nebo T_cl, je-li delší) | Několik kroků čidla na okno |
| Maximální krok Kint | ×1.15 / ÷1.15 | Omezený krok na okno |
| Meze Kint | 0.01 – 1.0 | |
| Počet oken Kint do konce relace | 15 | |
| Počet cyklů Kext do konce relace | 50 | |
| Ustálení Kext | 3 × T_cl, poté blízko požadované hodnoty (nebo 12 × T_cl) | Kext se během náběhu neučí |
| Maximální odchylka pro Kext | 1.0 °C | |
| Maximální Kext | 1.2 | |
| Alfa průběžného učení Kext | 0.04 | |

---

## Služby a API

### `versatile_thermostat.set_auto_tpi_mode`

Spustí nebo zastaví učební relaci.

| Parametr | Typ | Popis |
|-----------|------|-------------|
| `auto_tpi_mode` | boolean | `true` pro spuštění, `false` pro zastavení |
| `reinitialise` | boolean | `true` (výchozí): začít znovu od nakonfigurovaných koeficientů. `false`: pokračovat v předchozí relaci |

```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.living_room
data:
  auto_tpi_mode: true
  reinitialise: true
```

---

## Diagnostika a řešení problémů

### Diagnostický senzor

Entita: `sensor.<name>_auto_tpi_learning_state`

Stav: `active` během relace, jinak `off`.

| Atribut | Popis |
|-----------|-------------|
| `heating_cycles_count` | Celkový počet pozorovaných cyklů |
| `coeff_int_cycles` | Naučená okna Kint |
| `coeff_ext_cycles` | Naučené cykly Kext |
| `model_confidence` | Postup relace 0.0 – 1.0 |
| `calculated_coef_int` | Aktuální Kint |
| `calculated_coef_ext` | Aktuální Kext |
| `last_learning_status` | Výsledek posledního cyklu |
| `learning_start_dt` | Začátek relace |

### Běžné stavy učení

| Stav | Význam |
|--------|---------|
| `learned_indoor_heat` / `learned_indoor_cool` | Kint aktualizován na konci okna |
| `learned_outdoor_heat` / `learned_outdoor_cool` | Kext aktualizován |
| `kext_waiting_settling` | Kext čeká, až se místnost po změně požadované hodnoty ustálí |
| `kint_window_crossed_setpoint` | Místnost překročila požadovanou hodnotu během okna, okno nepoužito |
| `power_out_of_range(...)` | Výkon na 0 % nebo 100 %, cyklus ignorován |
| `cycle_gap_detected` / `cycle_too_short` | Nenormální délka cyklu, cyklus ignorován |
| `setpoint_changed_during_cycle` | Požadovaná hodnota změněna během cyklu |
| `outdoor_delta_too_small(...)` | Venkovní teplota příliš blízko požadované hodnoty |
| `gap_too_large_for_outdoor(...)` | Odchylka nad 1 °C, Kext se neučí |
| `cooling_down_naturally` / `warming_up_naturally` | Místnost se k požadované hodnotě vrací sama, Kext se nemění |
| `continuous_kext_learned_heat` / `continuous_kext_learned_cool` | Kext aktualizován průběžným učením |

### Řešení problémů

| Příznak | Pravděpodobná příčina | Postup |
|---------|--------------|--------|
| Kint nepostupuje | Žádný nárůst alespoň 0,3 °C při nenasyceném výkonu | Na několik hodin snižte požadovanou hodnotu o 1–2 °C a pak ji vraťte zpět |
| Překmit po každém náběhu | Doba ohřevu je pro topné těleso příliš krátká | Zvyšte dobu ohřevu a poté restartujte relaci |
| Pomalý náběh, bez překmitu | Doba ohřevu je příliš dlouhá | Snižte dobu ohřevu a poté restartujte relaci |
| Místnost je trvale pod nebo nad požadovanou hodnotou | Kext ještě není naučen, nebo se změnily ztráty | Nechte relaci doběhnout nebo zapněte průběžné učení Kext |
| Učení vůbec nepostupuje | Topení trvale na 100 % (extrémní mráz) | Počkejte na mírnější počasí |

### Soubor s perzistencí

**Umístění**: `.storage/versatile_thermostat.auto_tpi.<unique_id>`

Tento soubor obsahuje stav učení a obnoví se při restartu Home Assistant. Dokud není zaznamenán žádný cyklus učení, použijí se nakonfigurované koeficienty. Mimo učební relaci je referencí konfigurace: koeficient změněný v konfiguraci (možnosti nebo služba `set_tpi_parameters`) nahradí uložený.
