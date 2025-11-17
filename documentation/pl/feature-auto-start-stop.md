# AutoSTART / AutoSTOP

- [AutoSTART / AutoSTOP](#auto-start--auto-stop)
  - [Konfiguracja AutoSTART/AutoSTOP](#configure-auto-startstop)
  - [Zastosowanie](#usage)

Ta funkcja pozwala zatrzymać urządzenie, które nie musi być załączone, oraz ponownie je uruchomić, gdy warunki tego wymagają. Funkcja obejmuje trzy ustawienia kontrolujące, jak szybko urządzenie jest zatrzymywane i ponownie uruchamiane. Jest ona zarezerwowana wyłącznie dla `termostatu na klimacie` i ma zastosowanie w przypadku, gdy:
1. Twoje urządzenie jest stale zasilane i zużywa energię elektryczną nawet wtedy, gdy ogrzewanie (lub chłodzenie) nie jest potrzebne. Często dotyczy to pomp ciepła (_PAC_), które pobierają energię nawet w trybie czuwania.
2. Warunki termiczne są takie, że ogrzewanie (lub chłodzenie) nie jest potrzebne przez dłuższy czas: wartość zadana jest wyższa (lub niższa) niż temperatura w pomieszczeniu.
3. Temperatura rośnie (lub spada), pozostaje stabilna albo spada (lub rośnie) powoli.

W takich przypadkach lepiej jest wydać urządzeniu polecenie wyłączenia się, aby uniknąć niepotrzebnego zużycia energii w trybie czuwania.

## Konfiguracja AutoSTART/AutoSTOP

Aby skorzystać z tej funkcji, należy:
1. dodać funkcję `AutoSTART/AutoSTOP` z menu 'Funkcje',
2. ustawić poziom detekcji w opcji `AutoSTART/AutoSTOP`, która pojawia się po aktywacji funkcji. Wybierz poziom detekcji spośród opcji: `Powolny`, `Średni` i `Szybki`. Przy ustawieniu `Szybki` zatrzymania i ponowne uruchomienia będą następować częściej.

![image](images/config-auto-start-stop.png)

- Ustawienie `Bardzo powolny` pozwala na ustawienie odstępu około 60 minut pomiędzy zatrzymaniem a ponownym uruchomieniem.
- Ustawienie `Powolny` pozwala na odstep około 30 minut.
- Ustawienie `Średni` ustawia próg na około 15 minut.
- Ustawienie `Szybki` ustawia ten próg na 7 minut.The 'Very slow' setting allows about 60 minutes between a stop and a restart,

Należy pamiętać, że nie są to ustawienia absolutne, ponieważ algorytm uwzględnia nachylenie krzywej temperatury w pomieszczeniu, aby odpowiednio reagować. Nadal możliwe jest, że ponowne uruchomienie nastąpi wkrótce po zatrzymaniu, jeśli temperatura gwałtownie spadnie.

## Zastosowanie

Po skonfigurowaniu funkcji pojawi się nowa encja typu `switch`, która pozwala włączyć lub wyłączyć autoSTART/autoSTOP bez modyfikowania konfiguracji. Ta encja jest dostępna na termostacie _VTherm_ i nosi nazwę `switch.<name>_enable_auto_start_stop`.

![image](images/enable-auto-start-stop-entity.png)

Zaznacz pole wyboru, aby zezwolić na autoSTART i autoSTOP, lub pozostaw je niezaznaczone, aby wyłączyć tę funkcję.

**Uwaga:** Funkcja autoSTART/autoSTOP ponownie uruchomi termostat tylko wtedy, gdy została wcześniej wyłączona przez tę funkcję. Zapobiega to niepożądanym lub niespodziewanym aktywacjom. Naturalnie, stan wyłączenia jest zachowany nawet po ponownym uruchomieniu Home Assistanta.

> ![Tip](images/tips.png) _*Wskazówki*_
> 1. Algorytm detekcji został opisany [tutaj](algorithms.md#auto-startstop-algorithm).
> 2. Niektóre urządzenia (kotły, ogrzewanie podłogowe, pompy ciepła itp.) mogą nie tolerować zbyt częstego załączania/wyłączania. W takim przypadku lepiej wyłączyć tę funkcję, gdy wiadomo, że urządzenie będzie używane. Np. ja wyłączam tę funkcję w ciągu dnia, gdy wykrywana jest obecność, ponieważ wiem, że moja pompa ciepła będzie często się uruchamiać. Natomiast załączam autoSTART/autoSTOP w nocy lub gdy nikogo nie ma w domu, ponieważ wartość zadana jest obniżona i funkcja rzadko się aktywuje.
> 3. Jeśli korzystasz z karty interfejsu Versatile Thermostat (patrz: [tutaj](additions.md#better-with-the-versatile-thermostat-ui-card)), na karcie bezpośrednio widoczne jest pole wyłączenia autoSTART/autoSTOP, a termostat zatrzymany przez tę funkcję jest oznaczony ikoną ![auto-start/stop icon](images/auto-start-stop-icon.png).
