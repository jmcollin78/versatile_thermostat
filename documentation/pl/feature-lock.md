# Funkcja blokady

## Przegląd

> Funkcja blokady uniemożliwia modyfikacje termostatu z interfejsu użytkownika lub automatyzacji, przy jednoczesnym zachowaniu działania termostatu.

## Konfiguracja

Funkcja blokady jest konfigurowana w ustawieniach termostatu, w sekcji "Blokada". Możesz zablokować:

- **Użytkownicy**: Zapobiega zmianom w interfejsie użytkownika Home Assistant.
- **Automatyzacje i integracje**: Zapobiega zmianom w automatyzacjach, skryptach i innych integracjach.

Możesz również skonfigurować opcjonalny **Kod blokady**:

- **Kod blokady**: 4-cyfrowy numeryczny kod PIN (np. "1234"). Jeśli ustawiony, ten kod jest wymagany do blokowania/odblokowywania termostatu. Jest to opcjonalne, a jeśli nie skonfigurowane, nie jest wymagany żaden kod.

Możesz również wybrać centralną konfigurację dla ustawień blokady.

## Użycie

Użyj tych usług, aby kontrolować stan blokady:

- `versatile_thermostat.lock` - Blokuje termostat
- `versatile_thermostat.unlock` - Odblokowuje termostat (wymaga `code`, jeśli skonfigurowany)

Przykład automatyzacji blokowania:

```yaml
service: versatile_thermostat.lock
target:
  entity_id: climate.my_thermostat
```

Przykład automatyzacji odblokowywania z kodem:

```yaml
service: versatile_thermostat.unlock
target:
  entity_id: climate.my_thermostat
data:
  code: "1234"
```

## Stan blokady

Stan blokady jest:

- Widoczny w atrybutach `is_locked`, `lock_users` i `lock_automations` encji klimatyzacji
- Zachowywany po ponownym uruchomieniu Home Assistant (w tym kod PIN, jeśli ustawiony)
- Indywidualny dla każdego termostatu (każdy termostat ma swoją własną blokadę i opcjonalny kod PIN)

## Po zablokowaniu

**Zablokowane (z interfejsu użytkownika / automatyzacji / wywołań zewnętrznych w zależności od typu blokady w konfiguracji):**

- Zmiany trybu HVAC (w tym włączanie/wyłączanie)
- Zmiany temperatury docelowej
- Zmiany ustawień wstępnych i usług konfiguracji ustawień wstępnych VTherm
- Zmiany stanu obecności za pośrednictwem usług VTherm
- Zmiany trybu HVAC (w tym włączanie/wyłączanie)
- Zmiany temperatury docelowej
- Zmiany presetów i usług konfiguracji presetów VTherm
- Wywołanie usługi akcji HA

**Dozwolone (wewnętrzna logika VTherm, zawsze aktywna):**

- Wykrywanie i działania okien (wyłączanie lub tryb eco/mróz przy otwarciu, tylko wentylator, jeśli dotyczy, przywracanie zachowania po zamknięciu)
- Zabezpieczenia (np. ustawienia wstępne zabezpieczające przed przegrzaniem / mrozem, obsługa włączania/wyłączania zabezpieczeń)
- Zarządzanie mocą i przeciążeniem (w tym zachowanie `PRESET_POWER`)
- Automatyczne algorytmy regulacji (TPI / PI / PROP) i pętla sterowania
- Koordynacja centralna/nadrzędna/podrzędna i inne wewnętrzne automatyzacje VTherm

**Gwarancja zachowania:**

- Działania okien (na przykład: wyłączanie przy otwarciu, przywracanie po zamknięciu) działają nawet przy zablokowanym termostacie.

**Uwaga dotycząca implementacji:**

- Blokada jest egzekwowana przy wywołaniach zewnętrznych, które są jedynymi modyfikującymi `requested_state`. Operacje wewnętrzne (takie jak te z `SafetyManager` lub `PowerManager`) omijają blokadę z założenia, ponieważ `StateManager` nadaje priorytet ich wynikowi nad żądaniami zewnętrznymi. Blokada zapobiega jedynie modyfikacji `requested_state` przez wywołania zewnętrzne.

## Przypadki użycia

- Zapobieganie przypadkowym zmianom w okresach krytycznych
- Funkcja blokady dla dzieci
- Tymczasowe zapobieganie schedulerowi zmiany aktualnych ustawień
- Zabezpieczenia przed nieautoryzowanym odblokowaniem (przy użyciu kodu PIN)