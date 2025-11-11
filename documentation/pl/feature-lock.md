# Funkcja blokady (Lock)

## Przegląd

- Funkcja blokady uniemożliwia zewnętrzne zmiany konfiguracji termostatu (interfejs UI, automatyzacje, sceny, integracje zewnętrzne), przy zachowaniu pełnego działania wewnętrznej logiki VTherm.
- Stan blokady jest dostępny jako atrybut `is_locked` encji climate.
- Blokada jest konfigurowana per-termometr i jej stan jest zachowywany pomiędzy restartami Home Assistant.

## Sterowanie

Użyj poniższych usług do sterowania blokadą:

- `versatile_thermostat.lock` – włącza blokadę termostatu.
- `versatile_thermostat.unlock` – wyłącza blokadę termostatu.

Przykład automatyzacji:

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.moj_termostat
```

## Stan blokady

- Aktualny stan blokady jest widoczny w atrybucie `is_locked` encji climate.
- Stan blokady jest trwały (zachowywany przy restarcie).
- Każdy termostat posiada własną, niezależną blokadę.

## Co jest blokowane, gdy termostat jest zablokowany

Zewnętrzne wywołania (np. z UI, automatyzacji, scen, integracji) nie mogą:

- Zmieniać trybu HVAC (w tym włączać/wyłączać).
- Zmieniać temperatury zadanej.
- Zmieniać trybu nastawy (preset) ani używać usług konfiguracji presetów VTherm.
- Zmieniać stanu obecności przy użyciu usług VTherm.
- Zmieniać konfiguracji bezpieczeństwa przy użyciu usług VTherm.
- Zmieniać ustawienia pominięcia detekcji okna (window bypass) przy użyciu usług VTherm.
- Zmieniać trybów wentylatora/oscylacji, jeżeli są dostępne poprzez VTherm.

Ograniczenia dotyczą wyłącznie zewnętrznych wywołań; mechanizmy wewnętrzne VTherm pozostają aktywne.

## Co pozostaje aktywne przy włączonej blokadzie

Nawet przy aktywnej blokadzie działają w pełni wewnętrzne mechanizmy VTherm, w szczególności:

- Detekcja okna i powiązane akcje:
  - wyłączenie na otwarcie okna,
  - obniżenie do trybu eco/frost,
  - przełączenie na tryb „fan only” (jeśli dostępny),
  - przywrócenie poprzedniego stanu po zamknięciu okna.
- Mechanizmy bezpieczeństwa (np. ochrona przed przegrzaniem, tryby bezpieczeństwa).
- Zarządzanie mocą i ograniczanie przeciążenia (w tym zachowanie powiązane z PRESET_POWER).
- Automatyczne algorytmy regulacji (TPI / PI / PROP) oraz wewnętrzna pętla sterowania.
- Centralna koordynacja, tryby nadrzędne/podrzędne i współpraca wielu termostatów realizowana przez VTherm.

## Uwagi dotyczące zachowania

- Blokada dotyczy wyłącznie zewnętrznych zmian; wewnętrzne działania VTherm są wykonywane niezależnie od stanu blokady.
- Akcje związane z detekcją okna (np. wyłączenie przy otwarciu, przywrócenie po zamknięciu) działają poprawnie również wtedy, gdy termostat jest zablokowany.