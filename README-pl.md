[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# VTherm
### (dawniej: _*Versatile Thermostat*_)

Ten plik README dostępny jest
w językach : [Angielski](README.md) | [Francuski](README-fr.md) | [Niemiecki](README-de.md) | [Czeski](README-cs.md) | [Polski](README-pl.md)
<div><br></div>
<p align="center">
<img src="https://github.com/jmcollin78/versatile_thermostat/blob/main/images/icon.png" />
</p>

> ![Tip](images/tips.png) **VTherm** to wysoce konfigurowalny wirtualny termostat, który przekształca każde urządzenie grzewcze (grzejniki, klimatyzatory, pompy ciepła itp.) w inteligentny i adaptacyjny system. Umożliwia on konsolidację i centralne kontrolowanie wielu różnych systemów grzewczych, jednocześnie automatycznie optymalizując zużycie energii. Dzięki zaawansowanym algorytmom (TPI, auto-TPI) i możliwościach uczenia się, termostat dostosowuje się do Twojego domu 🏠 i Twoich zwyczajów, zapewniając optymalny komfort i znaczne zmniejszenie rachunków za ogrzewanie 💰.
> Integracja termostatyczna ma na celu znaczne uproszczenie automatyzacji zarządzania ogrzewaniem. Ponieważ wszystkie typowe zdarzenia związane z ogrzewaniem (obecność w domu, wykrycie aktywności w pomieszczeniu, otwarte okno, wyłączenie zasilania, itp.) są natywnie zarządzane przez termostat, nie musisz zajmować się skomplikowanymi skryptami i automatyzacjami, aby zarządzać termostatami. 😉

Ten niestandardowy komponent Home Assistanta jest ulepszoną i napisaną całkowicie od nowa wersją komponentu „Awesome Thermostat” (patrz: [Github](https://github.com/dadge/awesome_thermostat)) z dodatkowymi funkcjami.

# Dokumentacja
Cała dokumentacja jest dostępna na [Versatile Thermostat Web site](https://www.versatile-thermostat.org/).

# Zrzuty ekranu
Karta integracji VTherm UI (dostępna na [Github](https://github.com/jmcollin78/versatile-thermostat-ui-card)) :

![Card1](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/1.png) ![Card2](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/7.png)

# Co nowego?
![New](images/new-icon.png)

## Wydanie 9.3
> 1. **Wykrywanie zablokowanych zaworów**: Znaczne ulepszenie wykrywania awarii ogrzewania. Gdy anomalia zostanie wykryta na termostatach typu `over_climate_valve`, termostat diagnozuje teraz, czy problem jest spowodowany zablokowanym zaworem TRV (zablokowany otwarty lub zamknięty), porównując stan poleceń ze stanem rzeczywistym. Informacja ta - `root_cause` - jest wysyłana w zdarzeniu anomalii, umożliwiając podjęcie odpowiednich działań (powiadomienie, odzyskanie zaworu itp.). Więcej informacji [tutaj](documentation/pl/feature-heating-failure-detection.md),
> 2. **Automatyczne ponowne zablokowanie po odblokowaniu**: Dodano parametr `auto_relock_sec` do funkcji blokady. Gdy jest skonfigurowany, termostat automatycznie się blokuje ponownie po określonej liczbie sekund po odblokowaniu. Tę funkcję można całkowicie wyłączyć, ustawiając wartość 0. Domyślnie automatyczne ponowne zablokowanie jest ustawione na 30 sekund dla zwiększonego bezpieczeństwa. Więcej informacji [tutaj](documentation/pl/feature-lock.md),
> 3. **Ponowne wysyłanie poleceń**: Nowa funkcja do automatycznego wykrywania i korygowania rozbieżności między pożądanym stanem termostatu a rzeczywistym stanem urządzeń podrzędnych. Jeśli polecenie nie jest prawidłowo zastosowane do urządzenia, jest wysyłane ponownie. Zwiększa to niezawodność systemu w niestabilnych środowiskach lub z zawodnymi urządzeniami. Więcej informacji [tutaj](documentation/pl/feature-advanced.md),
> 4. **Przywrócenie ustawienia czasowego po ponownym uruchomieniu**: Skonfigurowane ustawienie czasowe jest teraz prawidłowo przywracane po ponownym uruchomieniu termostatu lub Home Assistant. To ustawienie będzie działać normalnie po ponownym uruchomieniu. Więcej informacji [tutaj](documentation/pl/feature-timed-preset.md),
> 5. **Zwiększona precyzja kontroli mocy**: Próg aktywacji kotła (`power_activation_threshold`) akceptuje teraz wartości dziesiętne (0,1, 0,5 itp.) dla dokładniejszej kontroli mocy aktywacji. Zapewnia to większą elastyczność w optymalizacji zużycia energii. Więcej informacji [tutaj](documentation/pl/feature-power.md),
> 6. **Ulepszenia dostępności czujników**: Lepsza obsługa określania dostępności czujnika temperatury przy użyciu metadanych `last_updated` Home Assistant, ulepszone wykrywanie utraty sygnału czujnika,

## Wydanie 9.2 - wersja stabilna
> 1. Nowy sposób zarządzania cyklami ogrzewania/zatrzymania dla VTherm `na przełączniku`. Obecny algorytm ma pewną zwłokę czasową, a pierwsze cykle nie są optymalne. To zaburza TPI i w szczególności algorytm auto-TPI. Nowy `Terminarz cykli` rozwiązuje te niedogodności. Ta zmiana jest dla Ciebie całkowicie przezroczysta.
> 2. Kolektor dzienników. Twoje żądania wsparcia często zawodzą ze względu na brak możliwości dostarczenia dzienników w odpowiednim okresie, skoncentrowanych na termostacie z błędem i na właściwym poziomie dziennika. To kwestia błędów szczególnie trudno reprodukowalnych. Kolektor dzienników ma na celu rozwiązanie tego problemu. Zbiera on dzienniki w tle na maksymalnym poziomie szczegółowości, a akcja (dawniej usługa) umożliwia ich wyodrębnienie do pliku. Można je pobrać i dołączyć do żądania wsparcia. Analizator dzienników powiązany ze stroną internetową - uruchomiony w wersji 9.1 (patrz poniżej) - dostosowuje się tak, aby mógł przetwarzać te dzienniki. Więcej informacji na temat kolektora dzienników [tutaj](documentation/pl/feature-logs-collector.md).
> 3. Stabilizacja wersji 9.x. Wersja główna 9 przyniosła wiele zmian, które spowodowały kilka anomalii. Ta wersja zawiera ostatnie poprawki związane z wersją 9.

## Wydanie 9.1
> 1. Nowe logo. Zainspirowane pracami @Krzysztonek (zobacz [tutaj](https://github.com/jmcollin78/versatile_thermostat/pull/1598)), VTherm korzysta z nowej funkcji wprowadzonej w [HA 2026.03](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api/), aby zmienić swoje logo. Cały zespół ma nadzieję, że nowa wersja przypadnie Wam do gustu. Miłego korzystania!
> 2. Strona internetowa stworzona przez @bontiv rozwiązuje jeden z głównych problemów VTherm: dokumentację. Strona umożliwia także analizę logów! Przekaż swoje logi (w trybie debug), a będziesz mógł je analizować, przybliżać widok dla konkretnego termostatu, wybranego okresu, filtrować interesujące dane itd. Zachęcamy do odkrycia tej pierwszej wersji tutaj: [Versatile Thermostat Web site](https://www.versatile-thermostat.org/). Ogromne podziękowania dla @bontiv za tę świetną realizację.
> 3. Oficjalna publikacja funkcji auto-TPI. Funkcja ta oblicza optymalne wartości współczynników dla algorytmu [TPI](documentation/fr/algorithms.md#lalgorithme-tpi). Warto podkreślić niesamowitą pracę @KipK oraz @gael1980 w tym zakresie. Jeśli chcesz z niej korzystać, koniecznie przeczytaj dokumentację.
> 4. VTherm opiera się teraz na stanie raportowanym przez urządzenia podrzędne w HA. Dopóki wszystkie urządzenia podrzędne nie mają znanego stanu w HA, VTherm pozostaje wyłączony.

## 🍻 Dziękuję za piwo! 🍻
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jmcollin78)

Wielkie podziękowania dla wszystkich moich 'piwnych' sponsorów za ich donacje i wszelkie formy zachęty. To bardzo wiele dla mnie znaczy i motywuje do dalszej pracy! Jeśli integracja ta pozwala Ci oszczędzać pieniądze, w zamian za to możesz kupić mi piwo. Z pewnością będę umiał to docenić!

# Słownik

  `VTherm`: Versatile Thermostat, jako odnośnik do dokumentacji.

  `TRV`: Termostatyczny Zawór Grzejnikowy (_ang: Thermostatic Radiator Valve_) wyposażony w zawór. Zawór, otwierając się lub zamykając, umożliwia kontrolę przepływu ciepłej wody.

  `AC`: Klimatyzacja Powietrza. Urządzenie AC chłodzi lub grzeje. Oznaczenie temperatur: Tryb Eko jest cieplejszy niż Komfort, który z kolei jest cieplejszy niż tzw. Boost. Algorytmy integracji biorą to pod uwagę.

  `EMA`: Średnia Zmienna Wykładnicza. Służy do wygładzania pomiarów temperatury z czujnika. Reprezentuje zmienną średnią temperaturę w pomieszczeniu i służy do obliczania nachylenia krzywej temperatury, co byłoby zbyt niestabilne w przypadku danych surowych.

  `slope`: Nachylenie krzywej temperatury, mierzone w stopniach (°C lub °K)/h. Jest dodatnie, gdy temperatura rośnie, i ujemne, gdy spada. Nachylenie to oblicza się na podstawie `EMA`.

  `PAC`: Pompa ciepła

  `HA`: Home Assistant

  `underlying`: Urządzenie sterowane integracją `Versatile Thermostat`

# Dokumentacja

Dla wygody Użytkownika, a także w celu dostępu do pomocy kontekstowej podczas konfiguracji, dokumentacja podzielona jest na rozdziały i sekcje:
1. [Wprowadzenie](documentation/pl/presentation.md)
2. [Instalacja](documentation/pl/installation.md)
3. [Szybki start](documentation/pl/quick-start.md)
4. [Wybór typu termostatu](documentation/pl/creation.md)
5. [Atrybuty podstawowe](documentation/pl/base-attributes.md)
6. [Konfigurowanie `termostatu na przełączniku`](documentation/pl/over-switch.md)
7. [Konfigurowanie `termostatu na klimacie`](documentation/pl/over-climate.md)
8. [Konfigurowanie `termostatu na zaworze`](documentation/pl/over-valve.md)
9. [Ustawienia presetów](documentation/pl/feature-presets.md)
10. [Zarządzanie oknami](documentation/pl/feature-window.md)
11. [Zarządzanie obecnością](documentation/pl/feature-presence.md)
12. [Zarządzanie ruchem](documentation/pl/feature-motion.md)
13. [Zarządzanie mocą/zasilaniem](documentation/pl/feature-power.md)
14. [AutoSTART i autoSTOP](documentation/pl/feature-auto-start-stop.md)
15. [Scentralizowane zarządzanie wszystkimi termostatami _VTherm_](documentation/pl/feature-central-mode.md)
16. [Sterowanie kotłem centralnym](documentation/pl/feature-central-boiler.md)
17. [Zaawansowane ustawienia, tryb bezpieczny](documentation/pl/feature-advanced.md)
18. [Samoregulacja](documentation/pl/self-regulation.md)
19. [Uczenie Auto TPI](documentation/pl/feature-autotpi.md)
20. [Dokumentacja techniczna Auto TPI](documentation/pl/feature-autotpi-technical.md)
21. [Algorytmy](documentation/pl/algorithms.md)
22. [Funkcja blokady](documentation/pl/feature-lock.md)
23. [Synchronizacja temperatury](documentation/pl/feature-sync_device_temp.md)
24. [Preset czasowy](documentation/pl/feature-timed-preset.md)
25. [Dokumentacja referencyjna](documentation/pl/reference.md)
24. [Przykłady dostrajania układu](documentation/pl/tuning-examples.md)
25. [Usuwanie problemów](documentation/pl/troubleshooting.md)
26. [Informacje o wersjach](documentation/pl/releases.md)
27. [Wykrywanie awarii ogrzewania](documentation/pl/feature-heating-failure-detection.md)

---
# Kilka przykładów...

**Stabilizacja temperatury skonfigurowana dzięki ustawieniu presetu**:

![image](documentation/en/images/results-1.png)
<h1></h1>

**Cykle Zał/Wył obliczane przez integrację `Termostat na Klimacie`**:

![image](documentation/en/images/results-2.png)
<h1></h1>

**Regulacja `Termostatem na Przełączniku`**:

![image](documentation/en/images/results-4.png)
<h1></h1>

**Regulacja `Termostatem na Klimacie`**:

![image](documentation/en/images/results-over-climate-1.png)
<h1></h1>

**Regulacja `Termostatem na Klimacie` z bezpośrednim sterowaniem zaworu**:

![image](documentation/en/images/results-over-climate-2.png)
<h1></h1>


## Ciesz się i korzystaj!


## Wybrane komentarze do integracji `Versatile Thermostat`
|                                             |                                             |                                             |
| ------------------------------------------- | ------------------------------------------- | ------------------------------------------- |
| ![testimonial 1](images/testimonials-1.png) | ![testimonial 2](images/testimonials-2.png) | ![testimonial 3](images/testimonials-3.png) |
| ![testimonial 4](images/testimonials-4.png) | ![testimonial 5](images/testimonials-5.png) | ![testimonial 6](images/testimonials-6.png) |

# ⭐ Historia gwiazdek

[![Star History Chart](https://api.star-history.com/svg?repos=jmcollin78/versatile_thermostat&type=Date)](https://star-history.com/#jmcollin78/versatile_thermostat&Date)

## Współpraca mile widziana!

Chciałbyś wnieść swój wkład do projektu? Zapoznaj się z [zasadami współpracy](CONTRIBUTING-pl.md).



[versatile_thermostat]: https://github.com/jmcollin78/versatile_thermostat
[buymecoffee]: https://www.buymeacoffee.com/jmcollin78
[buymecoffeebadge]: https://img.shields.io/badge/Buy%20me%20a%20beer-%245-orange?style=for-the-badge&logo=buy-me-a-beer
[commits-shield]: https://img.shields.io/github/commit-activity/y/jmcollin78/versatile_thermostat.svg?style=for-the-badge
[commits]: https://github.com/jmcollin78/versatile_thermostat/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacs_badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/jmcollin78/versatile_thermostat.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Joakim%20Sørensen%20%40ludeeus-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jmcollin78/versatile_thermostat.svg?style=for-the-badge
[releases]: https://github.com/jmcollin78/versatile_thermostat/releases
