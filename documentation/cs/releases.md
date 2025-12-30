# Poznámky k vydáním

![New](images/new-icon.png)

## Release 8.2
> Added a feature to lock / unlock a VTherm with an optional code. More information [here](documentation/cs/feature-lock.md)

## Release 8.1
> - For `over_climate` with regulation by direct valve control, two new parameters are added to the existing `minimum_opening_degrees`. The parameters are now the following:
>    - `opening_threshold`: the valve opening value under which the valve should be considered as closed (and then 'max_closing_degree' will apply),
>    - `max_closing_degree`: the closing degree maximum value. The valve will never be closed above this value. Set it to 100 to fully close the valve when no heating is needed,
>    - `minimum_opening_degrees`: the opening degree minimum value for each underlying device when ``opening_threshold` is exceeded, comma separated. Default to 0. Example: 20, 25, 30. When the heating starts, the valve will start opening with this value and will continuously increase as long as more heating is needed.
>
> ![alt text](images/opening-degree-graph.png)
> More informations can be found the discussion thread about this here: https://github.com/jmcollin78/versatile_thermostat/issues/1220


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

* **Release 7.4**:
- Added thresholds to enable or disable the TPI algorithm when the temperature exceeds the setpoint. This prevents the heater from turning on/off for short periods. Ideal for wood stoves that take a long time to heat up. See [TPI](documentation/en/algorithms.md#the-tpi-algorithm),
- Added a sleep mode for VTherms of type `over_climate` with regulation by direct valve control. This mode allows you to set the thermostat to off mode but with the valve 100% open. It is useful for long periods without heating if the boiler circulates water from time to time. Note: you must update the VTHerm UI Card to view this new mode. See [VTherm UI Card](documentation/en/additions.md#versatile-thermostat-ui-card).
(Need translation please)
* **Verze 7.2**:
- Nativní podpora zařízení ovládaných prostřednictvím entity `select` (nebo `input_select`) nebo `climate` pro _VTherm_ typu `over_switch`. Tato aktualizace činí vytváření virtuálních spínačů pro integraci Nodon, Heaty, eCosy atd. zastaralým. Více informací [zde](documentation/cs/over-switch.md#přizpůsobení-příkazů).
- Odkazy na dokumentaci: Verze 7.2 zavádí experimentální odkazy na dokumentaci z konfiguračních stránek. Odkaz je přístupný prostřednictvím ikony [![?](https://img.icons8.com/color/18/help.png)](https://github.com/jmcollin78/versatile_thermostat/blob/main/documentation/cs/over-switch.md#konfigurace). Tato funkce je v současnosti testována na některých konfiguračních stránkách.
* **Vydání 7.1**:
  - Přepracování funkce odlehčení zátěže (správa výkonu). Odlehčení zátěže je nyní řízeno centrálně (dříve byl každý _VTherm_ autonomní). To umožňuje mnohem efektivnější správu a prioritizaci odlehčení zátěže na zařízeních, která jsou blízko setpointu. Všimněte si, že musíte mít centralizovanou konfiguraci se zapnutou správou výkonu, aby to fungovalo. Více informací [zde](./feature-power.md).
* **Vydání 6.8**:
  - Přidána nová metoda regulace pro Versatile Termostaty typu `over_climate`. Tato metoda, nazývaná 'Přímé ovládání ventilu', umožňuje přímé ovládání ventilu TRV a případně offset pro kalibraci vnitřního teploměru vašeho TRV. Tato nová metoda byla testována se Sonoff TRVZB a rozšířena na další typy TRV, kde lze ventil přímo ovládat prostřednictvím entit `number`. Více informací [zde](over-climate.md#lauto-régulation) a [zde](self-regulation.md#auto-régulation-par-contrôle-direct-de-la-vanne).

## **Vydání 6.5** :
  - Přidána nová funkce pro automatické zastavení a restart `VTherm over_climate` [585](https://github.com/jmcollin78/versatile_thermostat/issues/585)
  - Vylepšeno zpracování otvorů při spuštění. Umožňuje zapamatovat a přepočítat stav otvoru při restartu Home Assistant [504](https://github.com/jmcollin78/versatile_thermostat/issues/504)

## **Vydání 6.0** :
  - Přidány entity domény `number` pro konfiguraci teplot presetů [354](https://github.com/jmcollin78/versatile_thermostat/issues/354)
  - Kompletní přepracování konfiguračního menu pro odstranění teplot a použití menu místo konfiguračního tunelu [354](https://github.com/jmcollin78/versatile_thermostat/issues/354)

## **Vydání 5.4** :
  - Přidán teplotní krok [#311](https://github.com/jmcollin78/versatile_thermostat/issues/311),
  - Přidány regulační prahy pro `over_valve` pro prevenci nadměrného vybíjení baterie pro TRV [#338](https://github.com/jmcollin78/versatile_thermostat/issues/338),
  - Přidána možnost použití vnitřní teploty TRV pro vynucení auto-regulace [#348](https://github.com/jmcollin78/versatile_thermostat/issues/348),
  - Přidána funkce keep-alive pro `over_switch` VTherms [#345](https://github.com/jmcollin78/versatile_thermostat/issues/345)

<details>
<summary>Starší vydání</summary>

> * **Vydání 5.3** : Přidána funkce pro ovládání centrálního kotle [#234](https://github.com/jmcollin78/versatile_thermostat/issues/234) - více informací zde: [Ovládání centrálního kotle](#le-contrôle-dune-chaudière-centrale). Přidána možnost deaktivace bezpečnostního režimu pro externí teploměr [#343](https://github.com/jmcollin78/versatile_thermostat/issues/343)
> * **Vydání 5.2** : Přidán `central_mode` pro centrální ovládání všech VTherms [#158](https://github.com/jmcollin78/versatile_thermostat/issues/158).
> * **Vydání 5.1** : Omezení hodnot posílaných do ventilů a do podkladové klimatické teploty.
> * **Vydání 5.0** : Přidána centrální konfigurace pro kombinování konfigurovatelných atributů [#239](https://github.com/jmcollin78/versatile_thermostat/issues/239).
> * **Vydání 4.3** : Přidán auto-ventilátor režim pro typ `over_climate` pro aktivaci ventilace při velkém teplotním rozdílu [#223](https://github.com/jmcollin78/versatile_thermostat/issues/223).
> * **Vydání 4.2** : Sklon teplotní křivky je nyní vypočítán v °/hodinu místo °/min [#242](https://github.com/jmcollin78/versatile_thermostat/issues/242). Opravena automatická detekce otevření přidáním vyhlazení teplotní křivky.
> * **Vydání 4.1** : Přidán **Expertní** regulační režim, kde uživatelé mohou specifikovat své vlastní parametry auto-regulace místo používání předprogramovaných [#194](https://github.com/jmcollin78/versatile_thermostat/issues/194).
> * **Vydání 4.0** : Přidána podpora pro **Versatile Thermostat UI Card**. Viz [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card). Přidán **Pomalý** regulační režim pro topná zařízení s pomalou latencí [#168](https://github.com/jmcollin78/versatile_thermostat/issues/168). Změněno jak **se vypočítává výkon** pro VTherms s více podkladovými zařízeními [#146](https://github.com/jmcollin78/versatile_thermostat/issues/146). Přidána podpora pro AC a Heat pro VTherms prostřednictvím spínače [#144](https://github.com/jmcollin78/versatile_thermostat/pull/144)
> * **Vydání 3.8**: Přidána funkce **auto-regulace** pro termostaty `over_climate` regulované podkladovou klimatizací. Viz [Auto-regulace](#lauto-régulation) a [#129](https://github.com/jmcollin78/versatile_thermostat/issues/129). Přidána **možnost invertovat ovládání** pro termostaty `over_switch` pro řešení instalací s pilotním vodičem a diodou [#124](https://github.com/jmcollin78/versatile_thermostat/issues/124).
> * **Vydání 3.7**: Přidán typ Versatile Thermostat `over_valve` pro přímé ovládání ventilu TRV nebo jakéhokoli jiného zařízení typu dimmer pro vytápění. Regulace se provádí přímo úpravou procenta otevření podkladové entity: 0 znamená, že ventil je vypnutý, 100 znamená, že ventil je plně otevřený. Viz [#131](https://github.com/jmcollin78/versatile_thermostat/issues/131). Přidána funkce obejití pro detekci otevření [#138](https://github.com/jmcollin78/versatile_thermostat/issues/138). Přidána podpora slovenského jazyka.
> * **Vydání 3.6**: Přidán parametr `motion_off_delay` pro vylepšení zpracování detekce pohybu [#116](https://github.com/jmcollin78/versatile_thermostat/issues/116), [#128](https://github.com/jmcollin78/versatile_thermostat/issues/128). Přidán AC režim (klimatizace) pro `over_switch` VTherm. Připraven GitHub projekt pro usnadnění příspěvků [#127](https://github.com/jmcollin78/versatile_thermostat/issues/127)
> * **Vydání 3.5**: Možné více termostatů v režimu "thermostat over climate" [#113](https://github.com/jmcollin78/versatile_thermostat/issues/113)
> * **Vydání 3.4**: Oprava chyb a vystavení teplot presetů pro AC režim [#103](https://github.com/jmcollin78/versatile_thermostat/issues/103)
> * **Vydání 3.3**: Přidán režim klimatizace (AC). Tato funkce vám umožňuje používat AC režim vašeho podkladového termostatu. Pro použití musíte zaškrtnout možnost "Použít AC režim" a definovat teplotní hodnoty pro presety a away presety.
> * **Vydání 3.2** : Přidána možnost ovládat více spínačů ze stejného termostatu. V tomto režimu jsou spínače spouštěny s prodlevou pro minimalizaci výkonu požadovaného v daném čase (minimalizace období překrývání). Viz [Konfigurace](#sélectionnez-des-entités-pilotées)
> * **Vydání 3.1** : Přidána detekce otevření okna/dveří poklesem teploty. Tato nová funkce automaticky zastaví radiátor, když teplota náhle klesne. Viz [Auto režim](#le-mode-auto)
> * **Hlavní vydání 3.0** : Přidáno zařízení termostatu a přidružené senzory (binární i nebinární). Mnohem blíže filozofii Home Assistant, nyní máte přímý přístup k energii spotřebované radiátorem řízeným termostatem a mnoha dalším senzorům užitečným pro vaše automatizace a dashboardy.
> * **Vydání 2.3** : Přidáno měření výkonu a energie pro radiátor řízený termostatem.
> * **Vydání 2.2** : Přidána bezpečnostní funkce pro prevenci ponechání radiátoru topícího donekonečna v případě selhání teploměru.
> * **Hlavní vydání 2.0** : Přidán termostat "over climate" umožňující transformovat jakýkoli termostat na Versatile Thermostat a získat všechny jeho funkce.

</details>

> ![Tip](images/tips.png) _*Poznámky*_
>
> Kompletní poznámky k vydáním jsou k dispozici na [GitHubu integrace](https://github.com/jmcollin78/versatile_thermostat/releases/).
