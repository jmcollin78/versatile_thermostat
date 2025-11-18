# Wstępna konfiguracja ustawień

- [Ustawienia wstępne](#presets-pre-configured-settings)
  - [Ustawienia wstępnie skonfigurowanych temperatur](#configure-pre-configured-temperatures)

## Ustawienia wstępnie skonfigurowanych temperatur

Tryb ustawień wstępnych pozwala na wstępne skonfigurowanie temperatury docelowej. Używany w połączeniu z Harmonogramem (patrz: [harmonogram](additions.md#the-scheduler-component)), daje potężny ale prosty sposób na optymalizację temperatury względem zużycia energii elektrycznej w Twoim domu. Oto lista zarządzalnych ustawień wstępnych:
 - **Eko**: urządzenie działa w trybie oszczędzania energii
 - **Komfort**: urządzenie działa w trybie komfortu
 - **Wzmocnienie**: urządzenie całkowicie otwiera wszystkie zawory
 - **Brak**: jest zawsze dodawany do listy trybów jako sposób na pominięcie innych ustawień i **ręczne ustawienie temperatury**.

Jeśli używany jest tryb klimatyzacji (AC), możesz również skonfigurować temperatury dla pracy urządzenia w trybie chłodzenia.

Ustawienia wstępne konfigurowane są bezpośrednio z encji _VTherm_ lub z konfiguracji głównej, jeśli korzystasz ze scentralizowanego sterowania. Po utworzeniu termostatu będziesz mieć do dyspozycji różne encje umożliwiające ustawienie temperatur osobno dla każdego ustawienia wstępnego:

![presets](images/config-preset-temp.png).

Lista encji różni się w zależności od wybranych funkcji:
1. Jeśli funkcja 'wykrywania obecności' jest aktywna, będziesz mieć do dyspozycji ustawienia wstępne z wersją 'nieobecności' poprzedzoną prefiksem _abs_.
2. Jeśli wybrałeś opcję `AC`, będziesz mieć również do dyspozycji ustawienia wstępne dla 'klimatyzacji' poprzedzone prefiksem _clim_.

> ![Tip](images/tips.png) _*Wskazówki*_
>
> 1. Gdy ręcznie zmienisz temperaturę docelową, ustawienie wstępne przełącza się na `Brak`.
> 2. Standardowe ustawienie wstępne `Away` jest ustawieniem ukrytym, którego nie można wybrać bezpośrednio. Integracja Versatile Thermostat używa zarządzania obecnością lub wykrywania ruchu, aby automatycznie i dynamicznie dostosować temperaturę docelową w zależności od obecności w domu lub aktywności w pomieszczeniu. Zobacz: [zarządzanie obecnością](feature-presence.md).
> 3. Jeśli korzystasz z zarządzania redukcją obciążenia, zobaczysz ukryte ustawienie wstępne o nazwie `moc`. Ustawienie wstępne elementu grzewczego ustawiane jest na `moc`, gdy występują warunki przeciążenia i aktywna jest redukcja obciążenia dla tego elementu grzewczego. Zobacz [zarządzanie energią](feature-power.md).
> 4. Jeśli korzystasz z zaawansowanej konfiguracji, zobaczysz ustawienie wstępne `bezpieczeństwo`, jeśli temperatura nie mogła zostać pobrana po określonym opóźnieniu. Zobacz: [tryb bezpieczeństwa](feature-advanced.md#safety-mode).
