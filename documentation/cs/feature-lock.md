# Funkce zámku

## Přehled

Funkce zámku zabraňuje změnám konfigurace termostatu z uživatelského rozhraní nebo z automatizací, přičemž termostat zůstává plně funkční.

## Použití

Pro ovládání stavu zámku použijte následující služby:

- `versatile_thermostat.lock` - Uzamkne termostat
- `versatile_thermostat.unlock` - Odemkne termostat

Příklad automatizace:

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

## Stav zámku

Stav zámku je:

- Viditelný v atributu `is_locked` entity `climate`
- Zachován při restartech Home Assistanta
- Vztahuje se na každý termostat zvlášť (každý termostat má svůj vlastní zámek)

## Když je termostat uzamčen

**Blokované operace:**

- Změna režimu HVAC (topení / chlazení / vypnuto)
- Zapnutí / vypnutí
- Změna cílové teploty
- Změna předvoleb (presetů)
- Změna režimu ventilátoru a větrání
- Služby specifické pro VTherm (přítomnost, teplota presetů, bezpečnost, obejití detekce okna)

**Nadále funguje:**

- Regulace teploty a řídicí smyčka
- Bezpečnostní funkce (ochrana proti přehřátí, bezpečnostní režim)
- Automatické funkce (detekce otevřeného okna, detekce pohybu, správa výkonu)
- Aktualizace a měření ze senzorů

## Příklady použití

- Zabránění náhodným změnám během kritických období
- Dětský zámek pro zabránění nechtěným úpravám