# Informacje o wydaniach

![New](images/new-icon.png)

>## Wydanie 8.2
> Dodano opcjonalną funkcję blokowania/odblokowania termostatu _*VTherm*_ za pomocą kodu PIN. Więcej informacji na ten temat znajduje się [tutaj](documentation/pl/feature-lock.md).

>## Wydanie 8.1
> - Dla `termostatu na klimacie` z bezpośrednim sterowaniem zaworem, do istniejącego już parametru `minimum_opening_degrees` dodano dwa nowe, następujące parametry:
>    - `opening_threshold`: wartość otwarcia zaworu, poniżej której zawór powinien być uważany za zamknięty (wówczas będzie obowiązywał parametr `max_closing_degree`),
>    - `max_closing_degree`: maksymalna wartość stopnia zamknięcia zaworu. Powyżej tej wartości zawór nigdy nie zostanie zamknięty. Ustaw wartość tego parametru na `100`, aby całkowicie zamknąć zawór, jeśli ogrzewanie jest już niepotrzebne,
>    - `minimum_opening_degrees`: minimalna wartość stopnia otwarcia zaworu dla każdego urządzenia bazowego po przekroczeniu progu `opening_threshold`, rozdzielona przecinkami. Domyślna wartość parametru: `0`. Przykład: 20, 25, 30. Po rozpoczęciu grzania zawór zacznie się otwierać z tą wartością i będzie się stale zwiększać, dopóki będzie potrzebne dalsze ogrzewanie.
>
> ![alt text](images/opening-degree-graph.png)
>
> Więcej informacji na ten temat można uzyskać, przegądając wątek dyskusyjny [#1220](https://github.com/jmcollin78/versatile_thermostat/issues/1220).


># Główne Wydanie 8.0:
>
> Ta wersja wymaga **szczególnej uwagi**. Przebudowano w niej znaczną część wewnętrznych mechanizmów integracji *Versatile Thermostat*, wprowadzając kilka nowych funkcji:
> 1. `Stan żądany` / `stan bieżący`: termostat _VTherm_ ma teraz 2 stany. `Stan żądany` to stan oczekiwany przez użytkownika (lub harmonogram). `Stan bieżący` to stan aktualny termostatu _VTherm_. Ten ostatni zależy od różnych funkcji VTherm. Np. użytkownik może zażądać (`stan żądany`) włączenia ogrzewania z ustawieniem Komfort, ale ponieważ wykryto otwarte okno, termostat _VTherm_ jest w rzeczywistości wyłączony. To podwójne zarządzanie zawsze zachowuje żądanie użytkownika i aplikuje wyniki różnych funkcji jako odpowiedź na żądanie użytkownika, aby w efekcie uzyskać `stan bieżący`. Takie rozwiązanie lepiej radzi sobie z przypadkami, gdy wiele funkcji chce oddziaływać na stan termostatu (np. otwieranie okna i wyłączanie zasilania). Zapewnia również powrót do pierwotnego `stanu żądanego`, gdy nie już żadnych innych zdarzeń oddziałujących na termostat (np. otwieranie okna i wyłączanie zasilania),
> 2. `Filtrowanie czasu`: operacja filtrowania czasu została znacznie poprawiona. Filtrowanie czasu zapobiega wysyłaniu zbyt wielu poleceń do urządzenia, co mogłoby prowadzić do nadmiernego zużycia baterii (np. termostatu zasilanego bateryjnie), a także zbyt częstej zmiany ustawień (pompy ciepła, pieca na pellet, ogrzewania podłogowego itp.). Nowa funkcja działa teraz następująco: jawne żądania użytkownika (lub harmonogramu) są zawsze natychmiast uwzględniane i **nie są one filtrowane**. Potencjalnie filtrowane są tylko zmiany związane z warunkami zewnętrznymi (np. temperaturą w pomieszczeniu). Filtrowanie polega na ponownym wysłaniu żądanego polecenia w późniejszym czasie, a nie na jego ignorowaniu, jak to miało miejsce dotychczas. Parametr `auto_regulation_dtemp` umożliwia dostosowanie opóźnienia.
> 3. Ulepszenie parametru `hvac_action`: parametr `hvac_action` odzwierciedla aktualny stan aktywacji sterowanego urządzenia. W przypadku typu `termostat na przełączniku` odzwierciedla on stan aktywacji przełącznika, w przypadku `termostatu na zaworze` pozostaje aktywny, gdy otwarcie zaworu jest większe, niż minimalne (lub 0, jeśli nie jest skonfigurowany). W przypadku `termostatu na klimacie` odzwierciedla on parametr `hvac_action` klimatu bazowego, jeśli jest dostępny, lub - w przeciwnym razie - jego symulację.
> 4. `Atrybuty własne`: organizacja atrybutów niestandardowych dostępnych w `Narzędzia deweloperskie -> Stany` została podzielona na sekcje w zależności od typu termostatu _VTherm_ i każdej aktywowanej funkcji.
> 5. `Redukcja mocy`: algorytm redukcji mocy uwzględnia teraz wyłączenie urządzeń między dwoma pomiarami zużycia energii w domu.
Załóżmy, że co 5 minut otrzymujesz informację zwrotną o zużyciu energii. Jeśli grzejnik zostanie wyłączony między dwoma pomiarami, włączenie nowego może zostać autoryzowane. Wcześniej uwzględniano tylko włączenia między dwoma pomiarami. Tak jak poprzednio, kolejny komunikat dotyczący zużycia energii prawdopodobnie spowoduje większą lub mniejszą redukcję mocy.
> 6. `AutoSTART/autoSTOP`: funkcja autoSTART/autoSTOP jest przydatna tylko dla typu `termostatu na klimacie` bez bezpośredniego sterowania zaworem. Opcja ta została usunięta z pozostałych typów termostatów.
> 7. Karta `VTherm UI Card`: wszystkie te modyfikacje pozwoliły na znaczną ewolucję karty `VTherm UI Card`, integrując komunikaty wyjaśniające aktualny stan (dlaczego mój VTherm ma taką temperaturę docelową?) oraz czy trwa filtrowanie czasu – w związku z czym aktualizacja stanu bazowego jest opóźniona.
> 8. Ulepszenia `logów`: ulepszono logi, aby znacząco uprościć debugowanie. Logi w formacie `---> NOWE ZDARZENIE: VersatileThermostat-Inversed ...` informują o zdarzeniu wpływającym na stan termostatu _VTherm_.
>
> ⚠️ **Ostrzeżenie**
>
> Ta wersja integracji zawiera zasadnicze zmiany w stosunku do wersji poprzedniej:
> - zmianie ulega nazwa zdarzenia z `versatile_thermostat_security_event` na `versatile_thermostat_safety_event`. Jeśli Twoja automatyzacja wykorzystuje to zdarzenie, konieczna jest jej aktualizacja,
> - atrybuty własne zostały całkowicie zreorganizowane. Wymagana jest odpowiednia aktualizacja Twoich automatyzacji lub szablonów _*Jinja*_, korzystających z tych atrybutów,
> - karta [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card) musi być zaktualizowana co najmniej do wersji `v2.0` aby zachować kompatybilność,
>
> **Pomimo 342 automatycznych testów tej integracji i maksymalnej staranności włożonej w wydanie nowej wersji, nie ma pewności, że jej instalacja nie zakłóci stanu czujników _VTherm_. Po instalacji aktualizacji, dla każdego sensora _VTherm_ należy sprawdzić ustawienia wstępne, tryb HVAC i ewentualnie ustawienie temperatury sensora _VTherm_.**
>





> * **Wydanie 7.1**:
>   - Przeprojektowanie funkcji redukcji obciążenia (zarządzanie energią). Redukcja obciążenia jest teraz obsługiwana centralnie (wcześniej każdy termostat _VTherm_ działał autonomicznie). Pozwala to na znacznie bardziej efektywne zarządzanie i priorytetyzację redukcji obciążenia na urządzeniach znajdujących się blisko wartości zadanej. Należy pamiętać, że aby to działało, musisz mieć scentralizowaną konfigurację z włączonym zarządzaniem energią. Więcej informacji [tutaj](./feature-power.md).

> * **Wydanie 6.8**:
>   - Dodano nową metodę regulacji dla termostatów typu `termostat na klimacie`. Metoda ta, nazwana 'bezpośrednie strowanie zaworem' (ang. _Direct Valve Control_), umożliwia bezpośrednie sterowanie zaworem TRV oraz ewentualne zastosowanie offsetu do kalibracji wewnętrznego termometru w Twoim TRV. Nowa metoda została przetestowana z Sonoff TRVZB i rozszerzona na inne typy TRV, w których zawór może być bezpośrednio sterowany poprzez encje liczbowe `number`. Więcej informacji [tutaj](over-climate.md#lauto-régulation) i [tutaj](self-regulation.md#auto-régulation-par-contrôle-direct-de-la-vanne).


## Pozostałe wydania

>  * **Wydanie 6.5**:
>    - Dodano nową funkcję autoSTART i autoSTOP dla `termostatu na klimacie` [#585](https://github.com/jmcollin78/versatile_thermostat/issues/585),
>    - Poprawiono obsługę sterowania przy uruchamianiu. Pozwala na zapamiętanie i ponowne przeliczenie stanu otwarcia po restarcie _Home Assistanta_ [#504](https://github.com/jmcollin78/versatile_thermostat/issues/504).


>  * **Wydanie 6.0**:
>    - Dodano encje domeny `number` do konfiguracji presetów temperatur [#354](https://github.com/jmcollin78/versatile_thermostat/issues/354),
>    - Całkowicie przeprojektowano menu konfiguracji, usuwając temperatury i dodając klasyczne menu zamiast ścieżki konfiguracji integracji [#354](https://github.com/jmcollin78/versatile_thermostat/issues/354).

>  * **Wydanie 5.4**:
>    - Dodano krok temperatury [#311](https://github.com/jmcollin78/versatile_thermostat/issues/311),
>    - Dodano progi regulacji dla `termostatu na zaworze`, aby zapobiec nadmiernemu drenażowi baterii w TRV [#338](https://github.com/jmcollin78/versatile_thermostat/issues/338),
>    - Dodano opcję użycia wewnętrznej temperatury TRV do wymuszenia autoregulacji [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348),
>    - Dodano funkcję _keep-alive_ dla `termostatu na przeączniku` [#345](https://github.com/jmcollin78/versatile_thermostat/issues/345).


<details>
<summary>Starsze wydania</summary>

>  * **Wydanie 5.3**: Dodano funkcję sterowania centralnym kotłem [#234](https://github.com/jmcollin78/versatile_thermostat/issues/234) - wiecej informacji [tutaj](#le-contrôle-dune-chaudière-centrale),
>    - Dodano możliwość wyłączenia trybu bezpiecznego dla zewnętrznego termometru [#343](https://github.com/jmcollin78/versatile_thermostat/issues/343),
>  * **Wydanie 5.2**: Dodano funkcję centralnego sterowania wszystkimi termostatami _VTherm_ [#158](https://github.com/jmcollin78/versatile_thermostat/issues/158).
>  * **Wydanie 5.1**: Ograniczenie wartości wysyłanych do zaworów i klimatyzacji.
>  * **Wydanie 5.0**: Dodano konfigurację centralną do łączenia konfigurowalnych atrybutów [#239](https://github.com/jmcollin78/versatile_thermostat/issues/239)
>  * **Wydanie 4.3**: Dodano tryb 'auto-wentylacja' dla `termostatu na klimacie`, aby aktywować wentylację przy znacznej różnicy temperatur [#223](https://github.com/jmcollin78/versatile_thermostat/issues/223).
>  * **Wydanie 4.2**:
>    - Nachylenie krzywej temperatury jest teraz liczone w °/godz. zamiast °/min. [#242](https://github.com/jmcollin78/versatile_thermostat/issues/242),
>    - Poprawiono automatyczne wykrywanie otwarć poprzez dodanie wygładzania krzywej temperatury.
>  * **Wydanie 4.1**: Dodano tryb regulacji `ekspert`, w którym użytkownik może określić własne parametry autoregulacji, zamiast korzystać z zaprogramowanych presetów [#194](https://github.com/jmcollin78/versatile_thermostat/issues/194).
>  * **Wydanie 4.0**:
>    - Dodano obsługę karty _Versatile Thermostat UI Card_. Patrz: [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card)
>    - Dodano tryb `Powolny` regulacji dla urządzeń grzewczych o dużej latencji [#168](https://github.com/jmcollin78/versatile_thermostat/issues/168),
>    - Zmieniono sposób obliczania mocy dla termostatu _VTherm_ z wieloma urządzeniami bazowymi [#146](https://github.com/jmcollin78/versatile_thermostat/issues/146).
>    - Dodano obsługę klimatyzacji i ogrzewania dla _VTherm_.
>  * **Wydanie 3.8**:
>    - Dodano funkcję autoregulacji dla `termostatu na klimacie` regulowanym przez urządzenie `cmilate`. Zobacz: [Auto-regulacja](#lauto-régulation) i [#129](https://github.com/jmcollin78/versatile_thermostat/issues/129).
>    - Dodano możliwość odwracania sterowania dla `termostatu na przełączniku`, aby obsłużyć **instalacje z przewodem sterującym** i diodą. [#124](https://github.com/jmcollin78/versatile_thermostat/issues/124).
>  * **Wydanie 3.7**:
>    - Dodano typ `termostatu na zaworze` do bezpośredniego sterowania zaworem _TRV_ lub innym tego typu urządzeniem do regulacji ogrzewania. Regulacja odbywa się poprzez dostosowanie procentu otwarcia zaworu: `0` - zawór zamknięty, `100` - zawór całkowicie otwarty. Zobacz: [#131](https://github.com/jmcollin78/versatile_thermostat/issues/131).
>    - Dodano funkcję obejścia dla detekcji otwarcia okna lub drzwi [#138](https://github.com/jmcollin78/versatile_thermostat/issues/138).
>    - Dodano obsługę języka słowackiego.
>  * **Wydanie 3.6**:
>    - Dodano parametr `motion_off_delay` w celu poprawy obsługi wykrywania ruchu [#116](https://github.com/jmcollin78/versatile_thermostat/issues/116), [#128](https://github.com/jmcollin78/versatile_thermostat/issues/128).
>    - Dodano tryb AC (klimatyzacja) dla `termostatu na przełączniku`.
>    - Przygotowano projekt na platformę **GitHub**, aby ułatwić nawiązywanie współpracy [#127](https://github.com/jmcollin78/versatile_thermostat/issues/127).
>  * **Wydanie 3.5**: Możliwość użycia wielu `termostatów na klimacie` [#113](https://github.com/jmcollin78/versatile_thermostat/issues/113).
>  * **Wydanie 3.4**: Poprawka błędu i udostępnienie presetu temperatur wstępnych dla trybu AC #103[#103](https://github.com/jmcollin78/versatile_thermostat/issues/103).
>  * **Wydanie 3.3**: Dodano tryb klimatyzacji (AC). Funkcja ta pozwala korzystać z trybu AC termostatu bazowego. Aby go użyć, należy zaznaczyć opcję `Tryb AC` i zdefiniować wartości temperatur dla presetów `„away”`.
>  * **Wydanie 3.2**: Dodano możliwość sterowania wieloma przełącznikami z jednego termostatu. W tym trybie przełączniki są uruchamiane z opóźnieniem, aby zminimalizować moc wymaganą w danym momencie (minimalizacja okresów nakładania się). Zobacz: [konfiguracja](#sélectionnez-des-entités-pilotées)
>  * **Wydanie 3.1**: Dodano detekcję otwarcia okna lub drzwi poprzez analizę spadku temperatury. Nowa funkcja automatycznie zatrzymuje grzejnik, gdy temperatura nagle spada. [Tryb Auto](#le-mode-auto)
>  * **Główne wydanie 3.0**: Dodano sprzęt termostatu i powiązane czujniki (binarny i niebinarny), co znacznie zbliżyło integrację do filozofii **Home Assistant** Od tech chwili masz bezpośredni dostęp do energii zużywanej przez grzejnik sterowany przez termostat oraz wiele innych czujników przydatnych w automatyzacjach.
>  * **Wydanie 2.3**: Dodano pomiar mocy i energii dla grzejnika sterowanego przez termostat.
>  * **Wydanie 2.2**: Dodano funkcję bezpieczeństwa (tryb _*bezpieczny*_), aby zapobiec pozostawieniu grzejnika w trybie grzania w nieskończoność w przypadku awarii termometru.
>  * **Główne wydanie 2.0**: Dodano `termostat na klimacie`, pozwalający przekształcić dowolny termostat w urządzeni _VTherm_ i uzyskać wszystkie jego funkcjonalności.

</details>

> ![Tip](images/tips.png) _*Kompletna lista zmian i aktualizacji dostępna jest [tutaj](https://github.com/jmcollin78/versatile_thermostat/releases/)*_.


