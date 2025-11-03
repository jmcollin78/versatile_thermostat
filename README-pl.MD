[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Versatile Thermostat

Ten plik README jest dostępny
w językach : [Angielski](README.md) | [Francuski](README-fr.md) | [Niemiecki](README-de.md) | [Czeski](README-cs.md) | [Polski](README-pl.md)

<p align="center">
<img src="https://github.com/jmcollin78/versatile_thermostat/blob/main/images/icon.png" />
</p>

> ![Tip](images/tips.png) Ta integracja termostatu ma na celu znaczne uproszczenie automatyzacji zarządzania ogrzewaniem. Ponieważ wszystkie typowe zdarzenia związane z ogrzewaniem (obecność w domu, wykrycie aktywności w pomieszczeniu, otwarte okno, wyłączenie zasilania) są natywnie zarządzane przez termostat, nie musisz zajmować się skomplikowanymi skryptami i automatyzacjami, aby zarządzać termostatami. ;-).

Ten niestandardowy komponent Home Assistanta jest ulepszoną i całkowicie przepisaną wersją komponentu „Awesome Thermostat” (patrz: [Github](https://github.com/dadge/awesome_thermostat)) z dodatkowymi funkcjami.

# Zrzuty ekranowe

Karta integracji Versatile Thermostat UI (dostępna na [Github](https://github.com/jmcollin78/versatile-thermostat-ui-card)) :

![Card1](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/1.png) ![Card2](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/7.png)

# Co nowego?
![New](images/new-icon.png)
> * **Wydanie 7.4**:
>
> - Dodano progi włączania i wyłączania algorytmu TPI, gdy temperatura przekroczy zadaną wartość. Zapobiega to włączaniu i wyłączaniu się grzejnika na krótkie okresy. Idealne rozwiązanie do pieców opalanych drewnem, które długo się nagrzewają. Patrz [TPI](documentation/en/algorithms.md#the-tpi-algorithm),
>
> - Dodano tryb uśpienia dla termostatów typu `termostat na klimacie` z regulacją poprzez bezpośrednie sterowanie zaworem. Ten tryb umożliwia ustawienie termostatu w trybie wyłączonym, ale z zaworem otwartym w 100%. Jest to przydatne podczas długich okresów bez ogrzewania, jeśli kocioł od czasu do czasu cyrkuluje wodę. Uwaga: aby wyświetlić ten nowy tryb, należy zaktualizować kartę interfejsu użytkownika. Patrz [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card).
>
> * **Wydanie 7.2**:
>
> - Natywna obsługa urządzeń sterowanych za pomocą encji `select` (lub `input_select`) lub `climate` dla typu `Termostat na Przełączniku`. Ta aktualizacja sprawia, że ​​tworzenie przełączników wirtualnych staje się przestarzałe w przypadku integracji Nodon, Heaty, eCosy itp. Więcej informacji [tutaj](documentation/en/over-switch.md#command-customization).
>
> - Linki do dokumentacji: wydanie 7.2 wprowadza eksperymentalne linki do dokumentacji wprost ze stron konfiguracji. Link jest dostępny za pomocą ikony [![?](https://img.icons8.com/color/18/help.png)](https://github.com/jmcollin78/versatile_thermostat/blob/main/documentation/en/over-switch.md#configuration). Funkcja ta jest obecnie testowana na niektórych stronach konfiguracyjnych.

# 🍻 Dziękuję za piwo! 🍻
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jmcollin78)

Wielkie podziękowania dla wszystkich moich piwnych sponsorów za ich donacje i wszelki formy zachęty. To bardzo wiele dla mnie znaczy i motywuje do dalszej pracy! Jeśli integracja ta pozwala Ci oszczędzać pieniądze, w zamian za to możesz kupić mi piwo. Z pewnością będę umiał to docenić!

# Słownik

  `VTherm`: Versatile Thermostat as referred to in this document

  `TRV`: Thermostatic Radiator Valve equipped with a valve. The valve opens or closes to allow hot water to pass.

  `AC`: Air Conditioning. An AC device cools instead of heats. Temperatures are reversed: Eco is warmer than Comfort, which is warmer than Boost. The algorithms take this information into account.

  `EMA`: Exponential Moving Average. Used to smooth sensor temperature measurements. It represents a moving average of the room's temperature and is used to calculate the slope of the temperature curve, which would be too unstable on the raw data.

  `slope`: The slope of the temperature curve, measured in ° (C or K)/h. It is positive when the temperature increases and negative when it decreases. This slope is calculated based on the `EMA`.

  `PAC`: Heat pump

  `HA`: Home Assistant

  `underlying`: the device controlled by `VTherm`

# Dokumentacja

The documentation is now divided into several pages for easier reading and searching:
1. [Introduction](documentation/en/presentation.md)
2. [Installation](documentation/en/installation.md)
3. [Quick start](documentation/en/quick-start.md)
4. [Choosing a VTherm type](documentation/en/creation.md)
5. [Basic attributes](documentation/en/base-attributes.md)
6. [Configuring a VTherm on a `switch`](documentation/en/over-switch.md)
7. [Configuring a VTherm on a `climate`](documentation/en/over-climate.md)
8. [Configuring a VTherm on a valve](documentation/en/over-valve.md)
9. [Presets](documentation/en/feature-presets.md)
10. [Window management](documentation/en/feature-window.md)
11. [Presence management](documentation/en/feature-presence.md)
12. [Motion management](documentation/en/feature-motion.md)
13. [Power management](documentation/en/feature-power.md)
14. [Auto start and stop](documentation/en/feature-auto-start-stop.md)
15. [Centralized control of all VTherms](documentation/en/feature-central-mode.md)
16. [Central heating control](documentation/en/feature-central-boiler.md)
17. [Advanced aspects, security mode](documentation/en/feature-advanced.md)
18. [Self-regulation](documentation/en/self-regulation.md)
19. [Tuning examples](documentation/en/tuning-examples.md)
20. [Algorithms](documentation/en/algorithms.md)
21. [Reference documentation](documentation/en/reference.md)
22. [Tuning examples](documentation/en/tuning-examples.md)
23. [Troubleshooting](documentation/en/troubleshooting.md)
24. [Release notes](documentation/en/releases.md)

# Trochę wyników...

**Stabilizacja temperatury skonfigurowana dzięki ustawieniom wstępnym**:

![image](documentation/en/images/results-1.png)

**Cykle Zał/Wył obliczane przez integrację `Termostat na Klimacie`**:

![image](documentation/en/images/results-2.png)

**Regulation with an `over_switch`**:

![image](documentation/en/images/results-4.png)

**Strong regulation in `over_climate`**:

![image](documentation/en/images/results-over-climate-1.png)

**Regulation with direct valve control in `over_climate`**:

![image](documentation/en/images/results-over-climate-2.png)

Enjoy!

# Contributions are welcome!

If you wish to contribute, please read the [contribution guidelines](CONTRIBUTING.md).

***

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
