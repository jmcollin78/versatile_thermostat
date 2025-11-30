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
## Release 8.0
> Toto je hlavní vydání. Přepisuje významnou část interních mechanismů Versatile Thermostat zavedením několika nových funkcí:
>    1. _požadovaný stav / aktuální stav_: VTherm nyní má 2 stavy. Požadovaný stav je stav požadovaný uživatelem (nebo Plánovačem). Aktuální stav je stav aktuálně aplikovaný na VTherm. Ten závisí na různých funkcích VTherm. Například uživatel může požadovat (požadovaný stav) zapnuté vytápění s předvolbou Komfort, ale protože bylo detekováno otevřené okno, je VTherm ve skutečnosti vypnutý. Tento duální management vždy zachovává požadavek uživatele a aplikuje výsledek různých funkcí na tento požadavek uživatele pro získání aktuálního stavu. To lépe zpracovává případy, kdy více funkcí chce zasahovat do stavu VTherm (např. otevření okna a omezení spotřeby energie). Také zajišťuje návrat k původnímu požadavku uživatele, když již neprobíhá žádná detekce.
>    2. _časové filtrování_: operace časového filtrování byla přepracována. Časové filtrování brání odesílání příliš mnoha příkazů na ovládané zařízení, aby se zabránilo nadměrné spotřebě baterie (např. TRV na baterie), příliš časté změně cílových teplot (tepelné čerpadlo, peleťový kotel, podlahové vytápění...). Nová operace je nyní následující: explicitní požadavky uživatele (nebo Plánovače) jsou vždy okamžitě zohledněny. Nejsou filtrovány. Pouze změny související s vnějšími podmínkami (např. teplota v místnosti) mohou být potenciálně filtrovány. Filtrování spočívá v opětovném odeslání požadovaného příkazu později a ne v ignorování příkazu, jak tomu bylo dříve. Parametr `auto_regulation_dtemp` umožňuje nastavení zpoždění.
>    3. _zlepšení hvac_action_: `hvac_action` odráží aktuální stav aktivace ovládaného zařízení. Pro typ `over_switch` odráží stav aktivace spínače, pro `over_valve` nebo regulaci ventilu je aktivní, když je otevření ventilu větší než minimální otevření ventilu (nebo 0, pokud není nakonfigurováno), pro `over_climate` odráží `hvac_action` podkladového `climate`, pokud je dostupné, nebo simulaci jinak.
>    4. _vlastní atributy_: organizace vlastních atributů dostupných v Nástrojích pro vývojáře / Stavy byla přeorganizována do sekcí v závislosti na typu VTherm a každé aktivované funkci. Více informací [zde](documentation/en/reference.md#custom-attributes).
>    5. _omezení spotřeby energie_: algoritmus omezení spotřeby energie nyní bere v úvahu vypnutí zařízení mezi dvěma měřeními spotřeby energie domácnosti. Předpokládejme, že máte zpětnou vazbu o spotřebě energie každých 5 minut. Pokud se radiátor vypne mezi 2 měřeními, pak zapnutí nového může být autorizováno. Dříve byly mezi 2 měřeními brány v úvahu pouze zapnutí. Jak dříve, další zpětná vazba o spotřebě energie může omezit více nebo méně.
>    6. _auto-start/stop_: auto-start/stop je užitečné pouze pro typ VTherm `over_climate` bez přímého ovládání ventilu. Tato volba byla odstraněna pro ostatní typy VTherm.
>    7. _VTherm UI Card_: všechny tyto úpravy umožnily významný vývoj [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card) pro integraci zpráv vysvětlujících aktuální stav (proč má můj VTherm tuto cílovou teplotu?) a zda probíhá časové filtrování - takže aktualizace podkladového stavu byla oddálena.
>    8. _zlepšení logů_: logy byly zlepšeny pro zjednodušení ladění. Logy ve formátu `--------------------> NEW EVENT: VersatileThermostat-Inversed ...` informují o události ovlivňující stav VTherm.
>
> ⚠️ **Varování**
>
> Toto hlavní vydání obsahuje změny způsobující nekompatibilitu s předchozí verzí:
> - `versatile_thermostat_security_event` byl přejmenován na `versatile_thermostat_safety_event`. Pokud vaše automatizace používají tuto událost, musíte je aktualizovat,
> - vlastní atributy byly přeorganizovány. Musíte aktualizovat své automatizace nebo Jinja šablony, které je používají,
> - [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card) musí být aktualizována na alespoň V2.0 pro kompatibilitu,
>
> **Navzdory 342 automatickým testům této integrace a péči věnované tomuto hlavnímu vydání nemohu zaručit, že její instalace nenaruší stavy vašich VTherm. Pro každý VTherm musíte po instalaci zkontrolovat předvolbu, hvac_mode a případně cílovou teplotu VTherm.**
>

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
19. [Příklady ladění](documentation/cs/tuning-examples.md)
20. [Algoritmy](documentation/cs/algorithms.md)
21. [Zámek / Odemknutí](documentation/cs/feature-lock.md)
22. [Referenční dokumentace](documentation/cs/reference.md)
23. [Řešení problémů](documentation/cs/troubleshooting.md)
24. [Poznámky k verzím](documentation/cs/releases.md)

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
