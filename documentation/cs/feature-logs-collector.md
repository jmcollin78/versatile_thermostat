# Stažení starších protokolů - Diagnostika a řešení problémů

- [Stažení starších protokolů - Diagnostika a řešení problémů](#stažení-starších-protokolů---diagnostika-a-řešení-problémů)
  - [Proč načítat protokoly?](#proč-načítat-protokoly)
  - [Jak získat přístup k této funkci](#jak-získat-přístup-k-této-funkci)
  - [Volání akce z Home Assistant](#volání-akce-z-home-assistant)
    - [Možnost 1: Z uživatelského rozhraní (UI)](#možnost-1-z-uživatelského-rozhraní-ui)
    - [Možnost 2: Ze skriptu nebo automatizace](#možnost-2-ze-skriptu-nebo-automatizace)
  - [Dostupné parametry](#dostupné-parametry)
    - [Vysvětlení úrovní protokolu](#vysvětlení-úrovní-protokolu)
  - [Přijetí a stažení souboru](#přijetí-a-stažení-souboru)
  - [Formát a obsah souboru protokolu](#formát-a-obsah-souboru-protokolu)
  - [Praktické příklady](#praktické-příklady)
    - [Příklad 1: Ladění abnormální teploty během 30 minut](#příklad-1-ladění-abnormální-teploty-během-30-minut)
    - [Příklad 2: Ověření správné detekce přítomnosti](#příklad-2-ověření-správné-detekce-přítomnosti)
    - [Příklad 3: Kontrola všech termostatů v krátkém období](#příklad-3-kontrola-všech-termostatů-v-krátkém-období)
  - [Pokročilá konfigurace](#pokročilá-konfigurace)
  - [Tipy pro použití](#tipy-pro-použití)

## Proč načítat protokoly?

Protokoly (_log_ – deník událostí_) Versatile Thermostat zaznamenávají všechny změny a akce prováděné termostatem. Jsou užitečné pro:

- **Diagnózu poruch**: Pochopení, proč se termostat nechová podle očekávání
- **Analýzu abnormálního chování**: Ověření rozhodnutí termostatu v daném období
- **Ladění konfigurace**: Ověření správné detekce senzorů a akcí
- **Hlášení problému**: Poskytnutí historie vývojářům k pomoci při ladění

Funkce **stažení protokolů** poskytuje jednoduchý způsob, jak načíst protokoly ze specifického období filtrované podle vašich potřeb.

**Užitečný tip**: Při požadavku na podporu budete muset poskytnout protokoly od doby, kdy se váš problém vyskytl. Použití této funkce se doporučuje, protože protokoly se shromažďují nezávisle na úrovni protokolu konfigurované v Home Assistant (na rozdíl od nativního systému protokolování HA).

## Jak získat přístup k této funkci

Akce `versatile_thermostat.download_logs` je dostupná v Home Assistant prostřednictvím:

1. **Automatizace** (Scripts > Automations)
2. **Scripts** (Scripts > Scripts)
3. **Developer Controls** (Settings > Developer Tools > Services)
4. **Rozhraní ovládání některých integrací** (podle vaší verze Home Assistant)

## Volání akce z Home Assistant

### Možnost 1: Z uživatelského rozhraní (UI)

Volání akce z Developer Tools:

1. Přejděte na **Settings** (Nastavení) → **Developer Tools** (Vývojářské nástroje)
2. Karta **Actions** (dříve: **Services**) → vyberte `versatile_thermostat: Download logs`
3. Vyplňte požadované parametry (viz část níže)
4. Klikněte na **Call Service** (Zavolat službu)

Poté se zobrazí **trvalé oznámení** s odkazem na stažení souboru.

### Možnost 2: Ze skriptu nebo automatizace

Příklad volání v automatizaci nebo YAML skriptu:

```yaml
action: versatile_thermostat.download_logs
metadata: {}
data:
  entity_id: climate.obyvacak        # Volitelné: nahraďte vaším termostatem
  log_level: INFO                    # Volitelné: DEBUG (výchozí), INFO, WARNING, ERROR
  period_start: "2025-03-14T08:00:00" # Volitelné: formát ISO (datetime)
  period_end: "2025-03-14T10:00:00"   # Volitelné: formát ISO (datetime)
```

## Dostupné parametry

| Parametr       | Vyžadováno? | Možné hodnoty                        | Výchozí             | Popis                                                                             |
| -------------- | ----------- | ------------------------------------ | ------------------- | --------------------------------------------------------------------------------- |
| `entity_id`    | Ne          | `climate.xxx` nebo neuvádět          | Všechny VTherm      | Cílený konkrétní termostat. Pokud se neuvádí, zahrnují všechny termostaty.        |
| `log_level`    | Ne          | `DEBUG`, `INFO`, `WARNING`, `ERROR`  | `DEBUG`             | Minimální úroveň závažnosti. Všechny protokoly na této úrovni a výše se zahrnují. |
| `period_start` | Ne          | ISO datetime (např. `2025-03-14...`) | Před 60 minutami    | Začátek období extrakce. Formát ISO s datem a časem.                              |
| `period_end`   | Ne          | ISO datetime (např. `2025-03-14...`) | Nyní (aktuální čas) | Konec období extrakce. Formát ISO s datem a časem.                                |

### Vysvětlení úrovní protokolu

- **DEBUG**: Detailní zprávy diagnostiky (rychlost výpočtu TPI, mezilehlé hodnoty, atd.). Velmi podrobné.
- **INFO**: Obecné informace (změny stavu, rozhodnutí termostatu, aktivace funkcí).
- **WARNING**: Varování (nesplněné podmínky, detekované abnormální hodnoty).
- **ERROR**: Chyby (selhání čidla, nezpracované výjimky).

**Tip**: Začněte s `INFO` pro počáteční analýzu, poté přejděte na `DEBUG`, pokud potřebujete více detailů.

## Přijetí a stažení souboru

Po volání akce se zobrazí **trvalé oznámení** obsahující:

- Shrnutí exportu (termostat, období, úroveň, počet položek)
- **URL pro stažení** ke zkopírování/vložení do prohlížeče

URL je **absolutní podepsaný odkaz** (s autentizačním tokenem platným 24 hodin). Kvůli omezení frontendu Home Assistant **na odkaz nelze přímo kliknout** v oznámení — musíte jej **zkopírovat a vložit** do nové karty prohlížeče pro spuštění stahování.

Stažený soubor je soubor `.log` pojmenovaný například:
```
vtherm_logs_obyvacak_20250314_102500.log
```

Soubor je dočasně uložen na vašem serveru Home Assistant ve složce dostupné v místní síti (v `config/www/versatile_thermostat/`).

> **Poznámka**: Staré soubory protokolů (> 24h) jsou automaticky odstraněny ze serveru.

> **Důležité**: Aby byla URL pro stažení správná, musíte nakonfigurovat svou interní nebo externí URL v **Nastavení > Systém > Síť** v Home Assistant. Jinak může URL obsahovat interní IP adresu Docker kontejneru.

## Formát a obsah souboru protokolu

Soubor obsahuje:

1. **Záhlaví** s informacemi o exportu:
   ```
   ================================================================================
   Versatile Thermostat - Log Export
   Thermostat : Obývací pokoj (climate.obyvacak)
   Period     : 2025-03-14 08:00:00 → 2025-03-14 10:00:00 UTC
   Level      : INFO and above
   Entries    : 342
   Generated  : 2025-03-14 10:25:03 UTC
   ================================================================================
   ```

2. **Položky protokolu**, jednu na řádek, s:
   - Časové razítko (datum + čas UTC)
   - Úroveň (`[INFO]`, `[DEBUG]`, `[WARNING]`, `[ERROR]`)
   - Název modulu Python (kde byl protokol vygenerován)
   - Zpráva

Příklad položky:
```
2025-03-14 08:25:12.456 INFO    [base_thermostat    ] Obývací pokoj - Current temperature is 20.5°C
2025-03-14 08:30:00.001 INFO    [prop_algo_tpi      ] Obývací pokoj - TPI calculated on_percent=0.45
2025-03-14 08:30:00.123 WARNING [safety_manager     ] Obývací pokoj - No temperature update for 35 min
```

Potom můžete tento soubor **analyzovat** pomocí:
- Běžného textového editoru
- Python scriptu pro zpracování dat
- Nástroje jako `grep`, `awk`, `sed`, atd. pro ruční filtraci

## Praktické příklady

### Příklad 1: Ladění abnormální teploty během 30 minut

**Cíl**: Pochopit, proč termostat v obývacím pokoji špatně spravuje svou teplotu.

**Akce k volání**:
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.obyvacak
  log_level: DEBUG              # Chceme všechny detaily
  period_start: "2025-03-14T14:00:00"
  period_end: "2025-03-14T14:30:00"
```

**Analýza souboru**:
- Vyhledejte „Current temperature", „Target temperature" pro zobrazení vývoje
- Vyhledejte „TPI calculated" pro zobrazení výpočtu procenta aktivace
- Vyhledejte „WARNING" nebo „ERROR" pro identifikaci anomálií

---

### Příklad 2: Ověření správné detekce přítomnosti

**Cíl**: Ověřte, že senzor přítomnosti správně změnil stav termostatu.

**Akce k volání**:
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.kancelar
  log_level: INFO
  period_start: "2025-03-15T12:00:00"      # Začátek období (formát ISO)
  period_end: "2025-03-15T14:00:00"        # Konec období
```

**Analýza souboru**:
- Vyhledejte zprávy obsahující „presence" nebo „motion"
- Ověřte, že změny přednastavení jsou správně zaznamenány

---

### Příklad 3: Kontrola všech termostatů v krátkém období

**Cíl**: Načtení globální historie všech termostatů na jednu hodinu filtrovanou na varování a chyby.

**Akce k volání**:
```yaml
action: versatile_thermostat.download_logs
data:
  log_level: WARNING            # Žádné entity_id → všechny VTherm
  period_start: "2025-03-15T13:00:00"
  period_end: "2025-03-15T14:00:00"
```

**Analýza souboru**:
- Soubor bude obsahovat všechny protokoly WARNING a ERROR ze všech termostatů
- Užitečné pro kontrolu, že nedošlo k žádným abnormálním výstrahám

---

## Pokročilá konfigurace

Ve výchozím nastavení jsou protokoly uchovávány v paměti na **4 hodin** na vašem serveru Home Assistant. Tuto dobu můžete upravit v `configuration.yaml`:

```yaml
versatile_thermostat:
  log_buffer_max_age_hours: 6   # Uchovávat protokoly 6 hodin místo 4
```

Můžete zadat **jakékoli kladné celé číslo** (v hodinách) podle vašich potřeb. Zde jsou některé příklady s odhadem spotřeby paměti:

| Trvání   | 10 VTherm scénář | 20 VTherm scénář |
| -------- | ---------------- | ---------------- |
| **1 h**  | ~0,5-1 MB        | ~2-5 MB          |
| **2 h**  | ~1-2 MB          | ~4-10 MB         |
| **4 h**  | ~2-5 MB          | ~8-20 MB         |
| **6 h**  | ~3-7 MB          | ~12-30 MB        |
| **8 h**  | ~4-10 MB         | ~16-40 MB        |
| **24 h** | Max. 40-50 MB    | Max. 40-50 MB    |

> **Poznámka**: Zvýšení doby uchování spotřebuje více paměti na vašem serveru. Automatické zabezpečení omezuje celkovou spotřebu na max. ~40-50 MB.

---

## Tipy pro použití

1. **Začněte s úrovní INFO**: Méně šumu, snazší čtení
2. **Cílte konkrétní termostat**: Relevantnější než všechny VTherm
3. **Snižte období**: Místo 24h, stáhněte jen problematické období
4. **Použijte web pro analýzu**: Webové stránky [Versatile Thermostat](https://www.versatile-thermostat.org/) vám umožňují analyzovat vaše protokoly a vykreslit křivky. Jedná se o nezbytný doplněk k této funkci
5. **Použijte nástroje pro zpracování**: `grep`, `sed`, `awk` nebo Python pro analýzu velkých souborů
6. **Zachovejte záhlaví**: Užitečné pro poskytnutí kontextu při hlášení problému

---
