# Typ termostatu: `Termostat na Przełączniku`

- [Typ termostatu: `Termostat na Przełączniku`](#typ-termostatu-termostat-na-przełączniku)
  - [Wymagania wstępne](#wymagania-wstępne)
  - [Konfiguracja](#konfiguracja)
    - [Podstawowe urządzenia](#podstawowe-urządzenia)
    - [Podtrzymanie aktywności (keep-alive)](#podtrzymanie-aktywności-keep-alive)
    - [Tryb AC](#tryb-ac)
    - [Inwersja poleceń](#inwersja-poleceń)
    - [Dostosowywanie poleceń](#dostosowywanie-poeceń)


## Wymagania wstępne

Instalacja powinna wyglądać następująco:

![installation `over_switch`](images/over-switch-schema.png)

1. Ustawienia temperatury docelowej pomieszczenia mogą być realizowane przez użytkownika, automatyzacje, wcześniej zdefiniowany harmonogram, lub mogą pochodzić z presetów w samej integracji.
2. Termometr wewnętrzny (2) lub termometr zewnętrzny (2b) okresowo odczytują temperaturę. Termometr wewnętrzny powinien być umieszczony w odpowiednim miejscu — najlepiej na środku pomieszczenia. Unikaj umieszczania go zbyt blisko okna, termostatu lub grzejnika.
3. Na podstawie wartości zadanych, różnicy temperatur oraz parametrów algorytmu **TPI** (zobacz: [TPI](algorithms.md#lalgorithme-tpi), termostat _VTherm_ obliczy procentowy czas włączenia.
4. Następnie w regularnych odstępach czasu termostat _VTherm_ będzie wydawał polecenia załączania i wyłączania dla encji podrzędnych typu `switch`, `select` lub `climate`.
5. Te encje podrzędne będą sterować fizycznym urządzeniem.
6. Fizyczny przełącznik będzie włączał lub wyłączał grzejnik.

Wartość `on-time` jest przeliczana przy każdym cyklu na nowo, co umozliwia regulację temperatury pomieszczenia.

![image](images/over-switch-diagram.png)

Ten schemat pokazuje, że VTherm działa cyklicznie – każdorazowo mierzy temperaturę, oblicza czas włączenia i steruje urządzeniem. Dzięki temu możliwe jest precyzyjne utrzymanie komfortu cieplnego w pomieszczeniu, bez przegrzewania ani wychładzania.

## Konfiguracja

W pierwszej kolejności skonfiguruj ustawienia główne, wspólne dla wszystkich termostatów _VTherm_ (patrz: [ustawienia główne](base-attributes.md)). Następnie wybierz z menu opcję "Encje podstawowe", a zobaczysz poniższy ekran konfiguracji:

![image](images/config-linked-entity.png)

### Podstawowe urządzenia

Do listy "Sterowane urządzenia" dodaj encje, które mają być sterowane termostatem. Akceptowane są tu jedynie encje typu `switch`, `input_boolean`, `select`, `input_select`, lub `climate`.

Jeśli jedno z urządzeń podrzędnych nie jest przełącznikiem, wówczas dostosowanie poleceń jest obowiązkowe. Domyślnie dla encji typu `switch` polecenia to standardowe komendy `włącz`/`wyłącz` (`turn_on`, `turn_off`).

Aktualnie dostępny algorytm to TPI. Zobacz: [algorytm](#algorithm). Jeśli skonfigurowano wiele encji, termostat przeplata ich aktywacje, aby zminimalizować liczbę jednocześnie włączonych przełączników. Pozwala to na lepsze rozłożenie mocy, ponieważ każdy grzejnik włącza się po kolei.

VTherm będzie jak najlepiej wygładzać zużycie energii poprzez naprzemienne aktywacje.
Oto przykład przeplatania aktywacji:

![image](images/multi-switch-activation.png)

Oczywiście, jeśli żądana moc (`on_percent`) jest zbyt wysoka, nastąpi nakładanie się aktywacji.


### Podtrzymanie aktywności (keep-alive)

Niektóre urządzenia wymagają okresowej aktywacji, aby zapobiegać wyłączeniu awaryjnemu. Funkcja ta, znana jako 'podtrzymywanie aktywności (keep-alive)', może zostać aktywowana poprzez wprowadzenie wartości innej niż zero w polu interwału utrzymywania aktywności termostatu. Aby wyłączyć tę funkcję lub w razie wątpliwości, pozostaw to pole puste lub wpisz zero (wartość domyślna).

### Tryb AC

Można wybrać `termostat na przełączniku` do sterowania klimatyzatorem, zaznaczając pole `Tryb AC`. W takim przypadku widoczny będzie tylko tryb chłodzenia.


### Inwersja poleceń

Jeśli urządzenie jest sterowane przewodem sterującym z diodą, może być konieczne zaznaczenie pola 'Odwróć polecenie'. Spowoduje to ustawienie przełącznika w pozycji załączonej, gdy urządzenie jest wyłączane, i w pozycji wyłączonej, gdy jest załączane. Po wybraniu tej opcji czasy cykli zostaną odwrócone.


### Dostosowywanie poleceń

Ta sekcja konfiguracji umożliwia dostosowanie poleceń włączania i wyłączania wysyłanych do urządzenia bazowego. Polecenia te są obowiązkowe, jeśli jedno z urządzeń bazowych nie jest przełącznikiem `switch` (w przypadku przełączników używane są standardowe polecenia włączania/wyłączania (`turn_on` i `turn_off`).

Aby dostosować polecenia, kliknij „Dodaj” u dołu okna, zarówno dla poleceń włączania, jak i wyłączania:

![virtual switch](images/config-vswitch1.png)

Następnie określ polecenia włączania i wyłączania, używając formatu `polecenie[/atrybut[:wartość]]`
Dostępne polecenia zależą od typu urządzenia bazowego:

| Typ urządzenia bazowego      | Polecenie załączenia                  | Poleenie wyłączenia                            | Zastosowanie                    |
| ---------------------------- | ------------------------------------- | ---------------------------------------------- | ------------------------------- |
| `switch` lub `input_boolean` | `turn_on`                             | `turn_off`                                     | Wszystkie przełączniki          |
| `select` lub `input_select`  | `select_option/option:comfort`        | `select_option/option:frost_protection`        | Nodon SIN-4-FP-21 i podobne (*) |
| `climate` (hvac_mode)        | `set_hvac_mode/hvac_mode:heat`        | `set_hvac_mode/hvac_mode:off`                  | eCosy (via Tuya Local)          |
| `climate` (preset)           | `set_preset_mode/preset_mode:comfort` | `set_preset_mode/preset_mode:frost_protection` | Heatzy (*)                      |

(*) To use this case, it is important to ensure that the state of the underlying entity matches the preset. Otherwise, VTherm has no way of knowing whether your equipment is on or off. To verify this, go to Developer Tools / States, search for your underlying entity, and check if its state matches the name of a preset. If you see 'heat', 'off', or 'cool', these are not presets, and this configuration will not work. In this case, you must use a virtual switch. Examples of virtual switches can be found on the troubleshooting page. If you insist on using this configuration, carefully check the values accepted by your equipment in Developer Tools / States and search for your equipment. You will see the options it accepts. They must be identical, including case sensitivity.
Oczywiście, przykłady te można dostosować do Twojego konkretnego przypadku.

Przykład dla Nodon SIN-4-FP-21:

![virtual switch Nodon](images/config-vswitch2.png)


Kliknij 'Zatwierdź' aby potwierdzić zmiany.

Jeśli pojawi się błąd:
> Konfiguracja dostosowywania polecenia jest nieprawidłowa. Jest ona wymagana dla urządzeń bazowych innych niż przełączniki, a format musi być następujący: `nazwa_usługi[/atrybut:wartość]`. Więcej szczegółów w pliku README.

oznacza to, że jedno z wprowadzonych poleceń jest nieprawidłowe.
Należy przestrzegać następujących zasad:
1. Każde polecenie musi być zgodne z formatem `polecenie[/atrybut[:wartość]]` (np. `select_option/option:comfort` lub `turn_on`) bez spacji ani znaków specjalnych z wyjątkiem _.
2. Poleceń musi być tyle, ile zadeklarowanych urządzeń bazowych, z wyjątkiem sytuacji, gdy wszystkie urządzenia bazowe są przełącznikami. W takim przypadku dostosowywanie poleceń nie jest wymagane.
3. W przypadku konfiguracji wielu urządzeń bazowych polecenia muszą być podane w tej samej kolejności. Liczba poleceń `on` musi być równa liczbie poleceń `off` i liczbie urządzeń bazowych (w odpowiedniej kolejności). Możliwe jest mieszanie różnych typów urządzeń bazowych. Gdy chociaż jedno z urządzeń bazowych nie jest przełącznikiem `switch`, wszystkie polecenia dla wszystkich urządzeń bazowych, w tym przełączników, muszą zostać skonfigurowane.
