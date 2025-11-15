# Funkcja blokady

## Przegląd

Funkcja blokady zapobiega zmianom w konfiguracji termostatu z interfejsu użytkownika lub automatyzacji, utrzymując jednocześnie termostat w stanie gotowości do pracy.

## Konfiguracja

Funkcja blokady jest konfigurowana w ustawieniach termostatu, w sekcji "Blokada". Możesz zablokować:

- **Użytkownicy**: Zapobiega zmianom w interfejsie użytkownika Home Assistant.
- **Automatyzacje i integracje**: Zapobiega zmianom w automatyzacjach, skryptach i innych integracjach.

Możesz również użyć centralnej konfiguracji dla ustawień blokady.

## Użycie

Użyj tych usług, aby kontrolować stan blokady:

- `versatile_thermostat.lock` - Blokuje termostat
- `versatile_thermostat.unlock` - Odblokowuje termostat

Przykład automatyzacji:

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

## Stan blokady

Stan blokady jest:

- Widoczny w atrybutach `is_locked`, `lock_users` i `lock_automations` encji klimatyzacji
- Zachowywany po ponownym uruchomieniu Home Assistant
- Indywidualny dla każdego termostatu (każdy termostat ma swoją własną blokadę)

## Po zablokowaniu

**Zablokowane (z interfejsu użytkownika / automatyzacji / wywołań zewnętrznych):**

- Zmiany trybu HVAC (w tym włączanie/wyłączanie)
- Zmiany temperatury docelowej
- Zmiany ustawień wstępnych i usług konfiguracji ustawień wstępnych VTherm
- Zmiany stanu obecności za pośrednictwem usług VTherm
- Zmiany konfiguracji bezpieczeństwa za pośrednictwem usług VTherm
- Zmiany obejścia okna za pośrednictwem usług VTherm
- Tryby wentylatora/obracania/wentylacji, gdy są udostępniane przez VTherm

**Dozwolone (wewnętrzna logika VTherm, zawsze aktywna):**

- Wykrywanie i działania okien (wyłączanie lub tryb eco/mróz przy otwarciu, tylko wentylator, jeśli dotyczy, przywracanie zachowania po zamknięciu)
- Zabezpieczenia (np. ustawienia wstępne zabezpieczające przed przegrzaniem / mrozem, obsługa włączania/wyłączania zabezpieczeń)
- Zarządzanie mocą i przeciążeniem (w tym zachowanie `PRESET_POWER`)
- Automatyczne algorytmy regulacji (TPI / PI / PROP) i pętla sterowania
- Koordynacja centralna/nadrzędna/podrzędna i inne wewnętrzne automatyzacje VTherm

**Gwarancja zachowania:**

- Działania okien (na przykład: wyłączanie przy otwarciu, przywracanie po zamknięciu) działają nawet przy zablokowanym termostacie.

**Uwaga dotycząca implementacji:**

- Blokada jest egzekwowana przy wywołaniach zewnętrznych, podczas gdy VTherm wewnętrznie używa kontekstu Home Assistant, aby jego własne funkcje mogły nadal dostosowywać termostat, gdy jest zablokowany.

## Przypadki użycia

- Zapobieganie przypadkowym zmianom w okresach krytycznych
- Funkcja blokady rodzicielskiej