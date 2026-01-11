- [Wybór głównych atrybutów](#choosing-basic-attributes)
- [Wybór funkcji użytkowych](#choosing-the-features-to-use)

# Wybór głównych atrybutów

Wybierz menu "Główne".

![image](images/config-main.png)

| Atrybut | Opis | Nazwa atrybutu |
| ------- | ---- | -------------- |
| **Nazwa** | Nazwa encji (będzie to nazwa integracji i encji `climate`). | |
| **Czujnik temperatury** | Identyfikator encji czujnika dostarczającego temperaturę pomieszczenia, w którym zainstalowane jest urządzenie. | |
| **Czujnik ostatnio zaktualizowany (opcjonalny)** | Zapobiega awaryjnym wyłączeniom, gdy temperatura jest stabilna, a czujnik przestaje raportować. (patrz: [rozwiązywanie problemów](troubleshooting.md#why-does-my-versatile-thermostat-go-into-safety-mode)) | |
| **Czas cyklu** | Czas w minutach między każdym obliczeniem. Dla `Termostat na Przełączniku`: moduluje czas włączania. Dla `Termostat na Zaworze`: oblicza otwarcie zaworu. Dla `Termostat na Klimacie`: wykonuje sterowanie i przelicza współczynniki samoregulacji. W przypadku typów `Termostat na Przełączniku` i `Termostat na Zaworze` obliczenia wykonywane są w każdym cyklu. W razie zmiany warunków trzeba poczekać na kolejny cykl, aby zobaczyć efekt. Z tego powodu cykl nie powinien być zbyt długi. 5 minut to dobra wartość, ale należy ją dostosować do rodzaju ogrzewania. Im większa bezwładność, tym dłuższy powinien być cykl (patrz: [Przykłady dostrajania](tuning-examples.md). Jeśli cykl jest zbyt krótki, grzejnik może nigdy nie osiągnąć docelowej temperatury. Na przykład w przypadku pieca akumulacyjnego będzie uruchamiany niepotrzebnie. | `cycle_min` |
| **Moc urządzenia** | Aktywuje czujniki mocy/energii. Podaj całkowitą, jeśli wiele urządzeń (ta sama jednostka co inne VThermy i czujniki). (zobacz: funkcja redukcji mocy) | `device_power` |
| **Centralizowane dodatkowe parametry** | Używa zewnętrznej temperatury, min/maks/kroku temperatury z centralnej konfiguracji. | |
| **Centralne sterowanie** | Umożliwia centralne sterowanie termostatem. Patrz: [centralized control](#centralized-control) | `is_controlled_by_central_mode` |
| **Wyzwalacz głównego bojlera** | Pole wyboru, aby użyć tego VThermu jako wyzwalacza głównego bojlera. | `is_used_by_central_boiler` |

# Wybór funkcji użytkowych

Wybierz menu "Funkcje".

![image](images/config-features.png)

| Funkcja | Opis | Nazwa atrybutu |
| -------- | ---- | -------------- |
| **Z detekcją otwarcia** | Zatrzymuje ogrzewanie przy otwarciu drzwi/oken. (patrz: [zarządzanie otwarciami](feature-window.md)) | `is_window_configured` |
| **Z detekcją ruchu** | Dostosowuje temperaturę docelową przy wykryciu ruchu w pomieszczeniu. (patrz: [detekcja ruchu](feature-motion.md)) | `is_motion_configured` |
| **Z zarządzaniem mocą** | Zatrzymuje urządzenie przy przekroczeniu progu zużycia energii. (patrz: [zarządzanie redukcją obciążenia](feature-power.md)) | `is_power_configured` |
| **Z detekcją obecności** | Zmienia temperaturę docelową na podstawie obecności/nieobecności. Różni się od detekcji ruchu (dom vs pomieszczenie). (patrz: [zarządzanie obecnością](feature-presence.md)) | `is_presence_configured` |
| **Z AutoSTART/autoSTOP** | Tylko dla `Termostat na Klimacie`: zatrzymuje/załącza urządzenie na podstawie prognozy krzywej temperatury. (patrz: [zarządzanie autoSTARTem/autoSTOPem](feature-auto-start-stop.md)) | `is_window_auto_configured` |

> ![Tip](images/tips.png) _*Wskazówki*_
> 1. Lista dostępnych funkcji dostosowuje się do typu Twojego termostatu.
> 2. Gdy włączysz funkcję, zostanie dodana nowa pozycja w menu do jej konfiguracji.
> 3. Nie możesz zatwierdzić utworzenia termostatu, jeśli nie wszystkie parametry dla wszystkich włączonych funkcji zostały jeszcze skonfigurowane.

