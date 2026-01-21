[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

# Versatile Thermostat

Tento README soubor je k dispozici v následujících
jazycích: [Angličtina](README.md) | [Francouzština](README-fr.md) | [Němčina](README-de.md) | [Čeština](README-cs.md)

<p align="center">
<img src="https://github.com/jmcollin78/versatile_thermostat/blob/main/images/icon.png" />
</p>

> ![Tip](images/tips.png) Tato termostatická integrace má za cíl výrazně zjednodušit vaše automatizace kolem správy vytápění. Protože všechny typické události kolem vytápění (nikdo doma?, detekována aktivita v místnosti?, otevřené okno?, omezení spotřeby energie?) jsou nativně spravovány termostatem, nemusíte se zabývat komplikovanými skripty a automatizacemi pro správu vašich termostatů. ;-).

Tato vlastní komponenta pro Home Assistant je vylepšením a kompletním přepsáním komponenty "Awesome thermostat" (viz [Github](https://github.com/dadge/awesome_thermostat)) s přidanými funkcemi.

# Snímky obrazovky

Versatile Thermostat UI Card (K dispozici na [Github](https://github.com/jmcollin78/versatile-thermostat-ui-card)) :

![Card1](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/1.png) ![Card2](https://github.com/jmcollin78/versatile-thermostat-ui-card/raw/master/assets/7.png)

# Co je nového?
![Nové](images/new-icon.png)

## Release 8.6
> 1. přidán parametr `max_opening_degrees` pro VTherms typu `over_climate_valve` umožňující omezit maximální procento otevření každého ventilu pro řízení průtoku horké vody a optimalizaci spotřeby energie.
> 2. přidána funkce překalibrace ventilů pro _VTherm_ `over_climate_valve`, která umožňuje vynutit maximální otevření a poté maximální zavření za účelem pokusu o překalibraci TRV. Více informací [zde](documentation/cs/feature-recalibrate-valves.md).

## Release 8.5
> 1. přidána detekce poruchy vytápění pro VTherms používající algoritmus TPI. Tato funkce detekuje dva typy anomálií:
>    - **porucha vytápění**: radiátor silně topí (vysoké on_percent), ale teplota nestoupá,
>    - **porucha chlazení**: radiátor netopí (on_percent na 0), ale teplota stále stoupá.
>
> Tyto anomálie mohou naznačovat otevřené okno, vadný radiátor nebo externí zdroj tepla. Funkce odesílá události, které lze použít ke spuštění automatizací (oznámení, výstrahy atd.). Více informací [zde](documentation/cs/feature-heating-failure-detection.md).

## Release 8.4
> 1. added auto TPI (experimental). This new feature allows automatically calculating the best coefficients for the TPI algorithm. More information [here](./auto_tpi_internal_doc.md)
> 2. added a temperature synchronization function for a device controlled in `over_climate` mode. Depending on your device's capabilities, _VTherm_ can control an offset calibration entity or directly an external temperature entity. More information [here](documentation/en/feature-sync_device_temp.md),
> 3. added a feature named "timed preset" which aims to select a preset for a certain duration and come back to the previous preset after the expiration of the delay. The new feature is totally described [here](documentation/cs/feature-timed-preset.md).

## Release 8.3
1. Addition of a configurable delay before activating the central boiler.
2. Addition of a trigger for the central boiler when the total activated power exceeds a threshold. To make this feature work you must:
   - Configure the power threshold that will trigger the boiler. This is a new entity available in the `central configuration` device.
   - Configure the power values of the VTherms. This can be found on the first configuration page of each VTherm.
   - Check the `Used by central boiler` box.

Each time a VTherm is activated, its configured power is added to the total and, if the threshold is exceeded, the central boiler will be activated after the delay configured in item 1.

The previous counter for the number of activated devices and its threshold still exist. To disable one of the thresholds (the power threshold or the activated-devices count threshold), set it to zero. As soon as either of the two non-zero thresholds is exceeded, the boiler is activated. Therefore a logical "or" is applied between the two thresholds.

More informations [here](documentation/cs/feature-central-boiler.md).

# 🍻 Děkuji za piva 🍻
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jmcollin78)

Velké díky všem mým donátorům za jejich příspěvky a povzbuzování. Je to pro mě velmi potěšující a motivuje mě to pokračovat! Pokud vám tato integrace pomohla ušetřit, kupte mi malé pivo na oplátku, budu vám velmi vděčný!

# Slovník

  `VTherm` : Versatile Thermostat v následujícím textu tohoto dokumentu

  `TRV` : termostatická hlavice vybavená ventilem. Ventil se otevírá nebo zavírá, čímž umožňuje průchod teplé vody

  `AC` : klimatizace. Zařízení je AC, pokud chladí. Teploty jsou pak obrácené: Eco je teplejší než Komfort, který je teplejší než Boost. Algoritmy tuto informaci berou v úvahu.

  `EMA` : Exponential Moving Average. Používá se k vyhlazení měření teplot senzorů. Odpovídá klouzavému průměru teploty místnosti. Používá se k výpočtu sklonu křivky teploty (slope), který by byl na surové křivce příliš nestabilní.

  `slope` : sklon křivky teploty. Měří se v °(C nebo K)/h. Je pozitivní, pokud teplota stoupá, a negativní, pokud klesá. Tento sklon se počítá na `EMA`

  `PAC` : tepelné čerpadlo

  `HA` : Home Assistant

  `underlying`: zařízení ovládané `VTherm`

# Dokumentace

Dokumentace je nyní rozdělena do několika stránek pro snadnější čtení a vyhledávání:
1. [Úvod](documentation/cs/presentation.md)
2. [Instalace](documentation/cs/installation.md)
3. [Rychlý start](documentation/cs/quick-start.md)
4. [Výběr typu VTherm](documentation/cs/creation.md)
5. [Základní atributy](documentation/cs/base-attributes.md)
6. [Konfigurace VTherm na `spínači`](documentation/cs/over-switch.md)
7. [Konfigurace VTherm na `klimatizaci`](documentation/cs/over-climate.md)
8. [Konfigurace VTherm na ventilu](documentation/cs/over-valve.md)
9. [Předvolby](documentation/cs/feature-presets.md)
10. [Správa oken](documentation/cs/feature-window.md)
11. [Správa přítomnosti](documentation/cs/feature-presence.md)
12. [Správa pohybu](documentation/cs/feature-motion.md)
13. [Správa energie](documentation/cs/feature-power.md)
14. [Auto start a stop](documentation/cs/feature-auto-start-stop.md)
15. [Centralizované řízení všech VTherm](documentation/cs/feature-central-mode.md)
16. [Řízení ústředního vytápění](documentation/cs/feature-central-boiler.md)
17. [Pokročilé aspekty, bezpečnostní režim](documentation/cs/feature-advanced.md)
18. [Samoregulace](documentation/cs/self-regulation.md)
19. [Lock / Unlock](documentation/en/feature-lock.md)
20. [Temperature synchronisation](documentation/en/feature-sync_device_temp.md)
21. [Timed preset](documentation/en/feature-timed-preset.md)
22. [Příklady ladění](documentation/cs/tuning-examples.md)
23. [Algoritmy](documentation/cs/algorithms.md)
24. [Zámek / Odemknutí](documentation/cs/feature-lock.md)
25. [Referenční dokumentace](documentation/cs/reference.md)
26. [Řešení problémů](documentation/cs/troubleshooting.md)
27. [Poznámky k verzím](documentation/cs/releases.md)
28. [Detekce poruchy vytápění](documentation/cs/feature-heating-failure-detection.md)

# Některé výsledky

**Stabilita teploty kolem cíle nakonfigurovaného předvolbou**:

![image](documentation/en/images/results-1.png)

**Cykly zapnutí/vypnutí vypočítané integrací `over_climate`**:

![image](documentation/en/images/results-2.png)

**Regulace s `over_switch`**:

![image](documentation/en/images/results-4.png)

**Silná regulace v `over_climate`**:

![image](documentation/en/images/results-over-climate-1.png)

**Regulace s přímým řízením ventilu v `over_climate`**:

![image](documentation/en/images/results-over-climate-2.png)

# Some comments on the integration
|                                             |                                             |                                             |
| ------------------------------------------- | ------------------------------------------- | ------------------------------------------- |
| ![testimonial 1](images/testimonials-1.png) | ![testimonial 2](images/testimonials-2.png) | ![testimonial 3](images/testimonials-3.png) |
| ![testimonial 4](images/testimonials-4.png) | ![testimonial 5](images/testimonials-5.png) | ![testimonial 6](images/testimonials-6.png) |

Užijte si to!

# ⭐ Star history

[![Star History Chart](https://api.star-history.com/svg?repos=jmcollin78/versatile_thermostat&type=Date)](https://star-history.com/#jmcollin78/versatile_thermostat&Date)

# Příspěvky jsou vítány!

Pokud si přejete přispět, přečtěte si prosím [pokyny pro přispívání](CONTRIBUTING-cs.md).

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
