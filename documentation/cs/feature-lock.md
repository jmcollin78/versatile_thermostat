# Funkce zámku

## Přehled

> Funkce zamknutí brání změnám termostatu z uživatelského rozhraní nebo automatizací při zachování provozuschopnosti termostatu.

## Konfigurace

Funkce Zámek se konfiguruje v nastavení termostatu v části "Zámek". Můžete si vybrat, zda chcete uzamknout:

- **Uživatelé**: Zabraňuje změnám z uživatelského rozhraní Home Assistant.
- **Automatizace a integrace**: Zabraňuje změnám z automatizací, skriptů a dalších integrací.

Můžete také nakonfigurovat volitelný **Kód zámku**:

- **Kód zámku**: 4-místný číselný PIN (např. "1234"). Pokud je nastaven, tento kód je vyžadován pro zamknutí/odemknutí termostatu. Toto je volitelné a pokud není nakonfigurováno, není vyžadován žádný kód.

Můžete si také vybrat použití centrální konfigurace pro nastavení zámku.

## Použití

Pro ovládání stavu zámku použijte tyto služby:

- `versatile_thermostat.lock` - Zamkne termostat
- `versatile_thermostat.unlock` - Odemkne termostat (vyžaduje `code` pokud nastaveno)

Příklad automatizace:

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

Příklad automatizace odemykání s kódem:

```yaml
service: versatile_thermostat.unlock
target:
  entity_id: climate.my_thermostat
data:
  code: "1234"
```

## Stav zámku

Stav zámku je:

- Viditelný v atributech `is_locked`, `lock_users` a `lock_automations` klimatizační entity
- Zachován při restartu Home Assistant (včetně PIN kódu pokud nastaveno)
- Pro každý termostat zvlášť (každý termostat má svůj vlastní zámek a volitelný PIN kód)

## Při zamčení

**Blokováno (z UI / automatizací / externích volání):**

- Změny režimu HVAC (včetně zapnutí/vypnutí)
- Změny cílové teploty
- Změny předvoleb a konfigurační služby předvoleb VTherm
- Služba HA action

**Povoleno (interní logika VTherm, vždy aktivní):**

- Detekce a akce oken (vypnutí nebo eco/protimrazová ochrana při otevření, pouze ventilátor, pokud je to možné, obnovení chování při zavření)
- Ochrany zabezpečení (např. předvolby zabezpečení proti přehřátí / mrazu, správa zapnutí/vypnutí zabezpečení)
- Správa napájení a přetížení (včetně chování `PRESET_POWER`)
- Automatické regulační algoritmy (TPI / PI / PROP) a regulační smyčka
- Koordinace centrální/rodič/dítě a další interní automatizace VTherm

**Záruka chování:**

- Akce oken (například: vypnutí při otevření, obnovení při zavření) fungují i při zamčeném termostatu.

**Poznámka k implementaci:**

- Zámek je vynucen na externích voláních, které jsou jediné, které modifikují `requested_state`. Interní operace (jako ty ze `SafetyManager` nebo `PowerManager`) obcházejí zámek záměrně, protože `StateManager` upřednostňuje jejich výstup před externími požadavky. Zámek pouze brání externím voláním v modifikaci `requested_state`.

## Případy použití

- Zabránění náhodným změnám během kritických období
- Funkce dětského zámku
- Dočasné zabránění plánovači měnit aktuální nastavení
- Zabezpečení proti neoprávněnému odemknutí (pomocí PIN kódu)