# Kdy použít a kdy nepoužít
Tento termostat dokáže ovládat 3 typy zařízení:
1. Radiátor, který funguje pouze v režimu zapnuto/vypnuto (nazývaný `thermostat_over_switch`). Minimální konfigurace požadovaná pro použití tohoto typu termostatu je:
   1. Zařízení jako radiátor (`switch` nebo ekvivalent),
   2. Teplotní senzor pro místnost (nebo input_number),
   3. Externí teplotní senzor (zvažte weather integraci, pokud ji nemáte).
2. Jiný termostat, který má své vlastní provozní režimy (nazývaný `thermostat_over_climate`). Pro tento typ termostatu vyžaduje minimální konfigurace:
   1. Zařízení – jako klimatizace, termostatický ventil – ovládané vlastní `climate` entitou.
3. Zařízení, které může přijmout hodnotu od 0 do 100% (nazývané `thermostat_over_valve`). Na 0 je vytápění vypnuto a na 100% je plně otevřeno. Tento typ umožňuje ovládání termostatického ventilu (např. Shelly ventil), který vystavuje entitu typu `number`, což umožňuje přímé ovládání otevření ventilu. Versatile Thermostat reguluje teplotu místnosti úpravou procenta otevření, používá jak vnitřní, tak vnější teplotní senzory a využívá TPI algoritmus popsaný níže.

Typ `over_climate` vám umožňuje přidat všechny funkce nabízené VersatileThermostat k vašemu stávajícímu vybavení. `Climate` entita VersatileThermostat bude ovládat vaši podkladovou `climate` entitu, vypne ji při otevřených oknech, přepne do Eco režimu, pokud nikdo není přítomen, atd. Viz [zde](#proč-nová-implementace-termostatu). Pro tento typ termostatu jsou všechny topné cykly ovládány podkladovou `climate` entitou a ne samotným Versatile Thermostat. Volitelná funkce auto-regulace umožňuje Versatile Thermostat upravit cílovou teplotu podkladové entity, aby dosáhl cílové teploty.

Instalace s pilotnáím drátem a aktivační diodou těží z možnosti, která umožňuje obrácení ovládání zapnuto/vypnuto podkladového radiátoru. K tomu použijte typ `over_switch` a zaškrtněte možnost "Invertovat příkaz".

# Proč nová implementace termostatu?

Tato komponenta, nazvaná __Versatile Thermostat__, spravuje následující případy použití:
- Konfigurace prostřednictvím standardního grafického rozhraní integrace (pomocí Config Entry flow),
- Plné využití **preset režimu**,
- Deaktivace preset režimu, když je teplota **nastavena ručně** na termostatu,
- Vypnutí/zapnutí termostatu nebo změna preset při **otevření/zavření dveří nebo oken** po určité době,
- Změna preset, když je **detekována aktivita** nebo není v místnosti po definovanou dobu,
- Použití algoritmu **TPI (Time Proportional Interval)** díky [[Argonaute](https://forum.hacf.fr/u/argonaute/summary)],
- Přidání správy **omezení zátěže** nebo regulace, aby se nepřekročila definovaná celková spotřeba. Když je překročena maximální spotřeba, skrytý preset "power" je nastaven na `climate` entitu. Když spotřeba klesne pod maximum, předchozí preset je obnoven.
- **Správa přítomnosti**. Tato funkce umožňuje dynamicky měnit preset teplotu na základě senzoru přítomnosti ve vašem domě.
- **Akce pro interakci s termostatem** z jiných integrací: můžete vynutit přítomnost/nepřítomnost pomocí služby a můžete dynamicky měnit preset teploty a upravovat bezpečnostní nastavení.
- Přidání senzorů pro zobrazení vnitřních stavů termostatu,
- Centralizované ovládání všech Versatile Thermostat pro jejich zastavení, nastavení všech na ochranu proti mrazu, vynucení všech do topného režimu (v zimě), vynucení všech do chladicího režimu (v létě).
- Ovládání centrálního topného kotle a VTherm, které musí tento kotel ovládat.
- Automatické spuštění/zastavení na základě predikce použití pro `over_climate`.

Všechny tyto funkce jsou konfigurovatelné buď centrálně, nebo individuálně podle vašich potřeb.

# Vybavení

Pro provoz _VTherm_ budete potřebovat nějaký hardware. Seznam níže není úplný, ale zahrnuje nejčastěji používaná zařízení, která jsou plně kompatibilní s Home Assistant a _VTherm_. Jedná se o affiliate odkazy na partnerský obchod [Domadoo](https://www.domadoo.fr/fr/?domid=97), který mi umožňuje získat malé procento, pokud nakoupíte prostřednictvím těchto odkazů. Objednávka z [Domadoo](https://www.domadoo.fr/fr/?domid=97) vám dává konkurenční ceny, záruku vrácení a velmi krátkou dobu dodání srovnatelnou s jinými velkými online prodejci. Jejich hodnocení 4,8/5 mluví samo za sebe.

⭐ : Nejpoužívanější a tedy nejlepší volba.

## Teploměry
Nezbytné v nastavení _VTherm_, externalizované zařízení pro měření teploty umístěné tam, kde žijete, zajišťuje spolehlivé, pohodlné a stabilní řízení teploty.

- [⭐ Sonoff SNZB Zigbee](https://www.domadoo.fr/fr/suivi-energie/6614-sonoff-capteur-de-temperature-et-d-humidite-zigbee-30-avec-ecran-6920075740004.html??domid=97)
- [⭐ 4 x Sonoff SNZB Zigbee](https://www.domadoo.fr/fr/suivi-energie/6968-sonoff-pack-4x-capteurs-de-temperature-et-d-humidite-zigbee-ecran.html?domid=97)
- [ Neo Tuya Zigbee](https://www.domadoo.fr/fr/produits-compatibles-jeedom/7564-neo-capteur-de-temperature-et-humidite-zigbee-30-tuya.html?domid=97)
- [ Moes Tuya Zigbee](https://www.domadoo.fr/fr/domotique/6667-moes-capteur-de-temperature-et-humidite-avec-ecran-zigbee-tuya.html?domid=97)

## Spínače
Pro přímé ovládání elektrického ohřívače. Použitelné s _VTherm_ [`over_switch`](over-switch.md):

- [⭐ Sonoff Power Switch 25 A Wifi](https://www.domadoo.fr/fr/peripheriques/5853-sonoff-commutateur-intelligent-wifi-haute-puissance-25a-6920075776768.html?domid=97)
- [⭐ Nodon SIN-4-1-20 Zigbee](https://www.domadoo.fr/fr/peripheriques/5688-nodon-micromodule-commutateur-multifonctions-zigbee-16a-3700313925188.html?domid=97)
- [Sonoff 4-channel Wifi](https://www.domadoo.fr/fr/peripheriques/5279-sonoff-commutateur-intelligent-wifi-433-mhz-4-canaux-6920075775815.html?domid=97)
- [Smart plug pro malá topná zařízení Zigbee](https://www.domadoo.fr/fr/peripheriques/5880-sonoff-prise-intelligente-16a-zigbee-30-version-fr.html?domid=97)

## Spínače pilotního drátu
Pro přímé ovládání elektrického ohřívače vybaveného pilotním drátem. Použitelné s _VTherm_ [`over_switch`](over-switch.md) a [přizpůsobenými příkazy](over-switch.md#la-personnalisation-des-commandes):

- [⭐ Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6828-nodon-module-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)
- [⭐ 4 x Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7050-nodon-pack-4x-modules-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)

## Termostatické ventily
Pro ovládání vodního radiátoru. Fungují s _VTherm_ [`over_valve`](over-valve.md) nebo [`over_climate s přímým ovládáním ventilu`](over-climate.md#thermostat-de-type-over_climate):

- [⭐ Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6776-sonoff-tete-thermostatique-connectee-zigbee-30.html?domid=97) s [`over_climate s přímým ovládáním ventilu`](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 2 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7477-sonoff-pack-de-2x-tete-thermostatique-connectee-zigbee-30.html?domid=97) s [`over_climate s přímým ovládáním ventilu`](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 4 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7478-sonoff-pack-de-4x-tete-thermostatique-connectee-zigbee-30.html?domid=97) s [`over_climate s přímým ovládáním ventilu`](over-climate.md#thermostat-de-type-over_climate),
- [Shelly BLU TRV BLE](https://www.domadoo.fr/fr/black-friday-domotique/7567-shelly-robinet-thermostatique-de-radiateur-a-commande-bluetooth-shelly-blu-trv-3800235264980.html?domid=97) s [`over_valve`](over-valve.md),
- [Moes TRV Zigbee](https://www.domadoo.fr/fr/peripheriques/5783-moes-tete-thermostatique-intelligente-zigbee-30-brt-100-trv-blanc.html?domid=97) s [`over_climate (bez přímého ovládání ventilu)`](over-climate.md#thermostat-de-type-over_climate)
- [Schneider Wiser TRV Zigbee](https://www.domadoo.fr/fr/controle-chauffage-clim/5497-schneider-electric-tete-de-vanne-thermostatique-connectee-zigbee-3606489582821.html?domid=97) s [`over_climate (bez přímého ovládání ventilu)`](over-climate.md#thermostat-de-type-over_climate)

## Nekompatibility
Některé termostaty typu TRV jsou známé jako nekompatibilní s Versatile Thermostat. To zahrnuje následující ventily:
1. Danfoss POPP ventily s teplotní zpětnou vazbou. Je nemožné tento ventil vypnout, protože se sám reguluje, což způsobuje konflikty s VTherm.
2. "Homematic" termostaty (a možná Homematic IP) jsou známé problémy s Versatile Thermostat kvůli omezením podkladového RF protokolu. Tento problém se obzvláště objevuje při pokusu ovládat více Homematic termostatů najednou v jedné VTherm instanci. Pro snížení zatížení cyklu služeb můžete například seskupit termostaty pomocí Homematic-specifických procedur (např. pomocí nástěnného termostatu) a nechat Versatile Thermostat ovládat pouze nástěnný termostat přímo. Další možností je ovládat jeden termostat a propagovat změny režimu a teploty prostřednictvím automatizace.
3. Termostaty typu Heatzy, které nepodporují příkazy `set_temperature`.
4. Termostaty typu Rointe mají tendenci se samy probouzet. Zbytek funguje normálně.
5. TRV jako Aqara SRTS-A01 a MOES TV01-ZB, kterým chybí zpětná vazba stavu `hvac_action` pro určení, zda topí nebo ne. Proto je zpětná vazba stavu nepřesná, ale zbytek se zdá funkční.
6. Klimatizace Airwell s integrací "Midea AC LAN". Pokud jsou dva VTherm příkazy příliš blízko u sebe, klimatizace se sama zastaví.
7. Klimatizace založené na integraci Overkiz nefungují. Zdá se nemožné tyto systémy vypnout nebo dokonce změnit teplotu.
8. Topné systémy založené na Netatmo fungují špatně. Rozvrhy Netatmo jsou v konfliktu s programováním _VTherm_. Zařízení Netatmo se neustále vracejí do režimu `Auto`, který je špatně spravován s _VTherm_. V tomto režimu nemůže _VTherm_ určit, zda systém topí nebo chladí, což znemožňuje výběr správného algoritmu. Někteří uživatelé se jim podařilo zprovoznit pomocí virtuálního spínače mezi _VTherm_ a podkladovým systémem, ale stabilita není zaručena. Příklad je uveden v sekci [řešení problémů](troubleshooting.md).
