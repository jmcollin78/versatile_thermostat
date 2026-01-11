# Konfiguracja zaawansowana

- [Konfiguracja zaawansowana](#advanced-configuration)
  - [Ustawienia zaawansowane](#advanced-settings)
    - [Tryb bezpieczny](#safety-mode)

Ustawienia te udoskonalają działanie termostatu, w szczególności mechanizm bezpieczeństwa dla termostatów. Brak sensorów temperatury (pokojowych lub zewnętrznych) może stanowić zagrożenie dla Twojego domu. Na przykład, jeśli czujnik temperatury utknie na wartości 10°C, urządzenia typu `Termostat na Klimacie` lub `Termostat na Zaworze` będą wymuszać maksymalne ogrzewanie, co może prowadzić do przegrzania pomieszczenia, a nawet uszkodzenia mienia, w najgorszym przypadku stwarzając ryzyko pożaru.

Aby temu zapobiec, VTherm zapewnia regularne raportowanie wartości odczytywanych z termometrów. Jeśli tak się nie dzieje, VTherm przełącza się w specjalny tryb zwany 'Trybem Bezpiecznym' (Safety Mode). Ten tryb gwarantuje minimalne ogrzewanie, aby zapobiec przeciwnemu ryzyku całkowitego braku ogrzewania np. w środku zimy.

Problem polega na tym, że niektóre termometry — szczególnie zasilane bateryjnie — wysyłają aktualizacje temperatury tylko wtedy, gdy wartość się zmienia. Zatem całkiem możliwe jest, że przez wiele godzin nie nadejdą żadne aktualizacje temperatury, mimo że termometr działa poprawnie. Poniższe parametry pozwalają na precyzyjne dostrojenie progów aktywacji Trybu Bezpiecznego.

Jeśli Twój termometr posiada atrybut `last seen`, wskazujący czas ostatniego kontaktu, możesz określić go w głównych atrybutach VTherm, aby znacznie ograniczyć fałszywe aktywacje Trybu Bezpiecznego (patrz: [konfiguracja](base-attributes.md#choosing-base-attributes) oraz [rozwiązywanie problemów](troubleshooting.md#why-does-my-versatile-thermostat-switch-to-safety-mode)).

Dla `termostatu na klimacie` z samoregulacją Tryb Bezpieczny jest niedostępny. W takim przypadku nie ma zagrożenia, istnieje jedynie ryzyko błędnej temperatury.

## Ustawienia zaawansowane

Ekran konfiguracji zaawansowanej wygląda następujaco:

![image](images/config-advanced.png)

### Tryb bezpieczny

| Parametr | Opis | Wartość domyślna | Nazwa atrybutu |
| --------- | ---- | ---------------- | -------------- |
| **Maksymalne opóźnienie** | Maksymalny czas pomiędzy dwoma pomiarami temperatury, po którym termostat VTherm przełącza się na Tryb Bezpieczny (Safety Mode). | 60 minut | `safety_delay_min` |
| **Minimalna wartość `on_percent`** | Minimalna wartość `on_percent`, poniżej której Tryb Bezpieczny nie zostanie aktywowany. Zapobiega aktywacji, jeśli grzejnik nie nagrzewa się wystarczająco (ryzyko przegrzania/niedogrzania bez fizycznego zagrożenia). `0.00` zawsze uruchamia, `1.00` wyłącza. | 0.5 (50%) | `safety_min_on_percent` |
| **Domyślna wartość `on_percent` w Trybie Bezpiecznym** | Wartość `on_percent` w Trybie Bezpiecznym. `0` wyłącza termostat, `0.1` utrzymuje minimalne ogrzewanie, aby zapobiec wychłodzeniu przy awarii termometru. | 0.1 (10%) | `safety_default_on_percent` |

Możliwe jest wyłączenie Trybu Bezpiecznego uruchamianego przez brak danych z termometru zewnętrznego. Ponieważ termometr zewnętrzny zazwyczaj ma niewielki wpływ na regulację (w zależności od konfiguracji), jego niedostępność może nie być krytyczna. Aby to zrobić, dodaj poniższe linie kodu do pliku  `configuration.yaml`:

```yaml
versatile_thermostat:
...
    safety_mode:
        check_outdoor_sensor: false
```

Domyślnie termometr zewnętrzny może uruchomić _*tryb bezpieczny*_ (_safety mode_), jeśli przestanie wysyłać dane. Pamiętaj, że Home Assistant musi zostać ponownie uruchomiony, aby te zmiany zaczęły obowiązywać. To ustawienie dotyczy wszystkich termostatów, które współdzielą termometr zewnętrzny.

> ![Tip](images/tips.png) _*Wskazówki*_
> 1. Gdy czujnik temperatury wznowi raportowanie, preset zostanie przywrócony do poprzedniej wartości.
> 2. Wymagane są dwa źródła temperatury: wewnętrzne i zewnętrzne. Oba muszą raportować wartości, w przeciwnym razie termostat przełączy się na tryb bezpieczny.
> 3. Dostępna jest akcja umożliwiająca dostosowanie trzech parametrów bezpieczeństwa. Może to pomóc w dopasowaniu Trybu Bezpiecznego do Twoich potrzeb.
> 4. W normalnym użytkowaniu `safety_default_on_percent` powinno być niższe niż `safety_min_on_percent`.
> 5. Jeśli korzystasz z karty interfejsu Versatile Thermostat (patrz: [tutaj](additions.md#better-with-the-versatile-thermostat-ui-card)), karta termostatu w Trybie Bezpiecznym jest pokrywana szarym tłem, wskazując błąd odczytu temperatury oraz czas od ostatniej aktualizacji jej wartości:
>
> ![safety mode](images/safety-mode-icon.png).
