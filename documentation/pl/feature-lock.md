# Funkcja blokady

## Przegląd

> Funkcja blokady uniemożliwia modyfikacje termostatu z poziomu interfejsu użytkownika lub automatyzacji, przy jednoczesnym zachowaniu działania samego termostatu.

## Konfiguracja

Funkcja blokady jest konfigurowana w ustawieniach termostatu, w sekcji 'Blokada'. Możesz zablokować:

- **użytkowników**: zapobiega zmianom z poziomu interfejsu użytkownika Home Assistant.
- **automatyzacje i integracje**: zapobiega zmianom w automatyzacjach, skryptach i innych integracjach.

Możesz również skonfigurować opcjonalny **Kod blokady**:

- **Kod blokady**: 4-cyfrowy numeryczny `kod PIN` (np. '1234'). Jeśli kod został ustawiony, wówczas będzie on wymagany do blokowania i odblokowywania termostatu. Jest to opcjonalna funkcjonalność, zatem w przypadku braku jej konfiguracji, żaden kod nie będzie wymagany.

Możesz również wybrać centralną konfigurację dla ustawień blokady.

## Sposoby użycia

W celu sterowania stanem blokady użyj następujących usług:

- `versatile_thermostat.lock` - blokuje termostat
- `versatile_thermostat.unlock` - odblokowuje termostat (wymaga wartości `kod`, jeśli została ona skonfigurowana)

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

- Widoczny w atrybutach `is_locked`, `lock_users` i `lock_automations` encji klimatyzacji (`climate`)
- Zachowywany po ponownym uruchomieniu Home Assistanta (w tym kod PIN, jeśli został wcześniej ustawiony)
- Indywidualny dla każdego termostatu (każdy termostat ma swoją własną blokadę i opcjonalny kod PIN)

## Po zablokowaniu

**Zablokowane (z interfejsu użytkownika / automatyzacji / wywołań zewnętrznych w zależności od typu blokady w konfiguracji):**

- Zmiany trybu HVAC (w tym włączanie/wyłączanie)
- Zmiany temperatury docelowej
- Zmiany presetów i usług konfiguracji ustawień presetów _*VTherm*_
- Zmiany stanu obecności za pośrednictwem usług _*VTherm*_
- Zmiany trybu HVAC (w tym włączanie/wyłączanie)
- Zmiany temperatury docelowej
- Wywołanie usługi akcji HA

**Dozwolone (wewnętrzna logika _VTherm_, zawsze aktywna):**

- Detekcja stanów okien (wyłączanie lub tryb eko/mróz przy otwarciu, tylko wentylator, jeśli dotyczy, przywracanie zachowania po zamknięciu)
- Zabezpieczenia (np. presety zabezpieczające przed przegrzaniem lub mrozem, obsługa włączania/wyłączania zabezpieczeń)
- Zarządzanie mocą i przeciążeniem (w tym zachowanie `PRESET_POWER`)
- Automatyczne algorytmy regulacji (TPI / PI / PROP) i pętla sterowania
- Koordynacja centralna, nadrzędna lub podrzędna, a także inne wewnętrzne automatyzacje _*VTherm*_

**Gwarancja zachowania:**

- Reakcja na zmiany stanów okien (np: wyłączanie przy otwarciu, przywracanie po zamknięciu) działają nawet przy zablokowanym termostacie.

**Uwaga dotycząca implementacji:**

- Blokada jest aktywowana jedynie przy wywołaniach zewnętrznych. Operacje wewnętrzne (takie jak: `SafetyManager` lub `PowerManager`) z założenia omijają blokadę, ponieważ `StateManager` nadaje priorytet ich wynikowi nad żądaniami zewnętrznymi. Blokada zapobiega jedynie modyfikacji `requested_state` przez wywołania zewnętrzne.

## Zastosowanie

- Zapobieganie przypadkowym zmianom w okresach krytycznych
- Funkcja blokady dla dzieci
- Tymczasowe zapobieganie zmianom aktualnych ustawień przez `harmonogram`
- Zabezpieczenia przed nieautoryzowanym odblokowaniem (przy użyciu kodu PIN)
