# Kalibrace ventilů (služba recalibrate_valves)

- [Kalibrace ventilů (služba recalibrate_valves)](#kalibrace-ventil%C5%AF-slu%C5%BEba-recalibrate_valves)
  - [Proč tato funkce?](#pro%C4%8D-tato-funkce)
  - [Jak to funguje](#jak-to-funguje)
  - [Omezení a požadavky](#omezen%C3%AD-a-po%C5%BEadavky)
  - [Konfigurace / přístup ke službě](#konfigurace--p%C5%99%C3%ADstup-ke-slu%C5%BEb%C4%9B)
  - [Parametry služby](#parametry-slu%C5%BEby)
  - [Podrobné chování](#podrobn%C3%A9-chov%C3%A1n%C3%AD)
  - [Příklady automatizací](#p%C5%99%C3%ADklady-automatizac%C3%AD)

## Proč tato funkce?

Služba `recalibrate_valves` provede jednoduchý kalibrační postup pro termostatické hlavice ventilů (TRV) ovládané VTherm v režimu regulace ventilů. Dočasně vynutí extrémní polohy ventilů (plně otevřeno a poté plně zavřeno), aby pomohla kalibrovat nastavení ventilu termostatu.

Tato služba je užitečná, pokud máte podezření na nesprávné hodnoty otevření/uzavření, po instalaci nebo údržbě zápasů nebo pokud radiátor topí i když je ventil hlášen jako zavřený.

⚠️ Skutečná kalibrace závisí na podkladovém zařízení ventilu. VTherm pouze posílá příkazy otevřít/uzavřít. Pokud zařízení nereaguje správně, kontaktujte výrobce TRV nebo použijte postup kalibrace výrobce.

⚠️ Kalibrace může snížit životnost baterie u bateriově napájených TRV. Používejte ji pouze pokud je to nutné.

## Jak to funguje

Služba provede následující kroky pro cílovou entitu:

1. Ověří, že cílová entita je `ThermostatClimateValve` (regulace ventilu). V opačném případě služba vrátí chybu.
2. Ověří, že každý podřízený ventil má konfigurované dvě `number` entity pro otevření a zavření. Chybějící entita způsobí odmítnutí operace.
3. Zapamatuje si `requested_state` termostatu.
4. Nastaví VTherm na OFF.
5. Počká `delay_seconds`.
6. Pro každý ventil: vynutí otevření na 100% (pošle namapovanou hodnotu na `number` entitu). Počká `delay_seconds`.
7. Pro každý ventil: vynutí zavření na 100% (pošle namapovanou hodnotu na `number` entitu). Počká `delay_seconds`.
8. Obnoví původní `requested_state` a aktualizuje stavy/atributy.

Během postupu VTherm posílá přímo hodnoty na `number` entity a obchází běžné prahové hodnoty algoritmu a ochrany. Služba běží na pozadí a okamžitě vrací `{"message": "calibrage en cours"}`.

Zpoždění mezi kroky určí volající. Služba přijímá hodnotu mezi `0` a `300` sekundami (0–5 minut). V praxi je vhodných 10–60 sekund v závislosti na rychlosti ventilu; 10 s je dobrý výchozí bod.

## Omezení a požadavky

- Služba je dostupná pouze pro termostaty `ThermostatClimateValve` (regulace ventilů).
- Každý podřízený ventil musí mít dvě `number` entity:
  - `opening_degree_entity_id` (příkaz otevřít)
  - `closing_degree_entity_id` (příkaz zavřít)
- `number` entity mohou mít atributy `min` a `max`; služba namapuje 0–100% lineárně do tohoto rozsahu. Pokud chybí `min`/`max`, použije se rozsah 0–100.
- Služba zabrání souběžnému spuštění pro stejnou entitu: pokud je kalibrace již spuštěna, nová žádost bude okamžitě odmítnuta.

## Konfigurace / přístup ke službě

Služba je registrována jako entity-service. Zavolejte ji cílením na entitu `climate` v Home Assistant.

Jméno služby: `versatile_thermostat.recalibrate_valves`

Příklad přes Developer Tools / Services:

```yaml
service: versatile_thermostat.recalibrate_valves
target:
  entity_id: climate.my_thermostat
data:
  delay_seconds: 30
```

Služba vrátí okamžitě:

```json
{"message": "calibrage en cours"}
```

## Parametry služby

| Parametr        | Typ     | Popis                                                                                             |
| --------------- | ------- | ------------------------------------------------------------------------------------------------- |
| `delay_seconds` | integer | Zpoždění (sekundy) po úplném otevření a po úplném zavření. Platný rozsah: 0–300 (doporučeno: 10). |

Schéma služby omezuje hodnotu na `0`–`300` sekund.

## Podrobné chování

- Operace běží jako background task. Volající obdrží okamžité potvrzení a průběh může sledovat v Home Assistant logu.
- Na konci operace je obnoven `requested_state` (HVAC režim, cílová teplota a predvolba pokud je přítomna) a stavy se aktualizují. VTherm by se měl vrátit do původního stavu, pokud jsou senzory stabilní.

## Příklady automatizací

1) Kalibrace jednou měsíčně (příklad):

Následující YAML spustí kalibraci v 03:00 prvního dne každého měsíce:

```yaml
alias: Měsíční kalibrace ventilů
trigger:
  - platform: time
    at: '03:00:00'
condition:
  - condition: template
    value_template: "{{ now().day == 1 }}"
  - condition: state
    entity_id: climate.my_thermostat
    state: 'off'
action:
  - service: versatile_thermostat.recalibrate_valves
    target:
      entity_id: climate.my_thermostat
    data:
      delay_seconds: 60
  - service: persistent_notification.create
    data:
      title: "🔧 Měsíční kalibrace spuštěna"
      message: "🔧 Byla spuštěna kalibrace ventilů pro climate.my_thermostat"
```

> ![Tip](images/tips.png) _*Doporučení*_
>
> - Otestujte kalibraci nejprve na jednom VTherm a zkontrolujte logy a hodnoty `number` před spuštěním pro více zařízení.
> - Nastavte `delay_seconds` na dostatečnou dobu, aby fyzický ventil dosáhl pozice (60 s je rozumný začátek pro většinu ventilů).
