- [Wybór głównych atrybutów](#choosing-basic-attributes)
- [Wybór funkcji użytkowych](#choosing-the-features-to-use)

# Wybór głównych atrybutów

Wybierz menu "Główne".

![image](images/config-main.png)

Podaj wymagane atrybuty główne. Te atrybuty są wspólne dla wszystkich termostatów VTherm:
1. Nazwa (będzie to zarówno nazwa integracji, jak i nazwa encji `climate`),
2. Identyfikator encji sensora temperatury, który dostarcza temperaturę pomieszczenia, w którym zainstalowany jest grzejnik,
3. Opcjonalna encja sensora podająca datę i godzinę ostatniego odczytu (last_seen). Jeśli jest dostępna, określ ją tutaj. Pomaga to zapobiec awaryjnemu wyłączeniu, gdy temperatura jest stabilna, a czujnik przestaje raportować przez długi czas (patrz [tutaj](troubleshooting.md#why-does-my-versatile-thermostat-go-into-safety-mode)),
4. Czas trwania cyklu w minutach. W każdym cyklu:
   1. dla `Termostat na Przełączniku`: VTherm włączy/wyłączy grzejnik, modulując proporcję czasu, w którym jest włączony,
   2. dla `Termostat na Zaworze`: VTherm obliczy nowy poziom otwarcia zaworu i wyśle go, jeśli uległ zmianie,
   3. dla `Termostat na Klimacie`: Cykl wykonuje podstawowe sterowanie i ponownie oblicza współczynniki samoregulacji. Cykl może skutkować nowym ustawieniem docelowej temperatury wysłanym do urządzeń podrzędnych lub regulacją otwarcia zaworu w przypadku sterowalnego TRV.
5. Moc urządzenia, która aktywuje sensory mocy i zużycia energii dla urządzenia. Jeśli wiele urządzeń jest powiązanych z tym samym termostatem VTherm, podaj tutaj całkowitą maksymalną moc wszystkich urządzeń. Jednostka mocy nie ma tu znaczenia. Ważne jest, aby wszystkie termostaty i wszystkie sensory mocy miały tę samą jednostkę (zobacz: funkcja redukcji mocy),
6. Opcja użycia dodatkowych parametrów z konfiguracji podstawowej:
   1. Sensor temperatury zewnętrznej,
   2. Minimalna/maksymalna temperatura oraz krok zmiany temperatury,
7. Opcja centralnego sterowania termostatem [patrz:](#centralized-control),
8. Pole wyboru, jeśli termostat ten jest używany do uruchamiania bojlera głównego.

> ![Tip](images/tips.png) _*Wskazówki*_
>  1. W przypadku typów `Termostat na Przełączniku` i `Termostat na Zaworze` obliczenia wykonywane są w każdym cyklu. W razie zmiany warunków trzeba poczekać na kolejny cykl, aby zobaczyć efekt. Z tego powodu cykl nie powinien być zbyt długi. 5 minut to dobra wartość, ale należy ją dostosować do rodzaju ogrzewania. Im większa bezwładność, tym dłuższy powinien być cykl (patrz: [Przykłady dostrajania](tuning-examples.md).
>  2. Jeśli cykl jest zbyt krótki, grzejnik może nigdy nie osiągnąć docelowej temperatury. Na przykład w przypadku pieca akumulacyjnego będzie uruchamiany niepotrzebnie.

# Wybór funkcji użytkowych

Wybierz menu "Funkcje".

![image](images/config-features.png)

Wybierz funkcje, których chcesz używać dla tego termostatu:
1. **Detekcja otwarcia** (drzwi, okna) zatrzymuje ogrzewanie, gdy wykryte zostanie otwarcie (patrz: [zarządzanie otwarciami](feature-window.md)),
2. **Detekcja ruchu:** VTherm może dostosować temperaturę docelową, gdy w pomieszczeniu wykryty zostanie ruchu (patrz: [detekcja ruchu](feature-motion.md)),
3. **Zarządzanie mocą:** VTherm może zatrzymać urządzenie, jeśli zużycie energii w domu przekroczy określony próg (patrz: [zarządzanie redukcją obciążenia](feature-power.md)),
4. **Detekcja obecności:** Jeśli masz zainstalowany sensor obecności, możesz użyć go do zmiany temperatury docelowej ( patrz: [zarządzanie obecnością](feature-presence.md). Zwróć uwagę na różnicę między tą funkcją a funkcją detekcji ruchu: obecność jest zazwyczaj używana w skali całego domu, podczas gdy detekcja ruchu dotyczy konkretnego pomieszczenia.
5. **AutoSTART/autoSTOP:** Tylko dla termostatów typu `Termostat na Klimacie`. Ta funkcja zatrzymuje urządzenie, gdy termostat wykryje, że nie będzie ono potrzebne przez pewien czas. Wykorzystuje krzywą temperatury do przewidywania, kiedy urządzenie znów będzie potrzebne, i załącza je ponownie w odpowiednim momencie (patrz: [zarządzanie autoSTARTem/autoSTOPem](feature-auto-start-stop.md)).

> ![Tip](images/tips.png) _*Wskazówki*_
> 1. Lista dostępnych funkcji dostosowuje się do typu Twojego termostatu.
> 2. Gdy włączysz funkcję, zostanie dodana nowa pozycja w menu do jej konfiguracji.
> 3. Nie możesz zatwierdzić utworzenia termostatu, jeśli nie wszystkie parametry dla wszystkich włączonych funkcji zostały jeszcze skonfigurowane.

