# Termostat typu `over_climate`

- [Termostat typu `over_climate`](#termostat-typu-over_climate)
  - [Předpoklady](#předpoklady)
  - [Konfigurace](#konfigurace)
    - [Podkladové entity](#podkladové-entity)
    - [AC režim](#ac-režim)
    - [Synchronization of the internal temperature of underlying entities](#synchronization-of-the-internal-temperature-of-underlying-entities)
    - [Samo-regulace](#samo-regulace)
    - [Auto-ventilátor (Auto ventilace)](#auto-ventilátor-auto-ventilace)
    - [Kompenzace vnitřní teploty podkladového vybavení](#kompenzace-vnitřní-teploty-podkladového-vybavení)
  - [Specifické funkce](#specifické-funkce)
  - [Sledování změn podkladové teploty](#sledování-změn-podkladové-teploty)

## Předpoklady

Instalace by měla vypadat takto:

![instalace `over_climate`](images/over-climate-schema.png)

1. Uživatel nebo automatizace, nebo Scheduler, nastaví setpoint prostřednictvím preset nebo přímo pomocí teploty.
2. Periodicky vnitřní teploměr (2), vnější teploměr (2b) nebo vnitřní teploměr zařízení (2c) pošle naměřenou teplotu. Vnitřní teploměr by měl být umístěn na relevantním místě pro pohodlí uživatele: ideálně uprostřed obytného prostoru. Vyhněte se umístění příliš blízko okna nebo zařízení.
3. Na základě hodnot setpointu, rozdílů a parametrů samo-regulace (viz [auto-regulace](self-regulation.md)), VTherm vypočítá setpoint k odeslání podkladové entitě `climate`.
4. Entita `climate` ovládá zařízení pomocí vlastního protokolu.
5. V závislosti na zvolených možnostech regulace může VTherm přímo ovládat otevření termostatického ventilu nebo kalibrovat zařízení tak, aby jeho vnitřní teplota odrážela teplotu místnosti.

## Konfigurace

Nejprve nakonfigurujte hlavní nastavení společná pro všechny _VTherm_ (viz [hlavní nastavení](base-attributes.md)).
Poté klikněte na možnost "Podkladové entity" z menu a uvidíte tuto konfigurační stránku:

![image](images/config-linked-entity2.png)

### Podkladové entity
V seznamu "Zařízení k ovládání" byste měli přidat entity `climate`, které budou ovládány VTherm. Akceptovány jsou pouze entity typu `climate`.

### AC režim

Můžete vybrat termostat `over_climate` pro ovládání klimatizace (reverzibilní nebo ne) zaškrtnutím políčka "AC režim". Pokud to zařízení umožňuje, budou dostupné režimy 'Vytápění' i 'Chlazení'.

### Synchronization of the internal temperature of underlying entities
This function allows for much better regulation as it synchronizes the internal thermometer of the underlying `climate` entities with the room temperature measured by _VTherm_. It is described [here](feature-sync_device_temp.md).

### Samo-regulace

V režimu `over_climate` zařízení používá vlastní regulační algoritmus: zapíná/vypíná a pozastavuje automaticky na základě setpointu přenášeného VTherm prostřednictvím své entity `climate`. Používá svůj vnitřní teploměr a přijatý setpoint.

V závislosti na zařízení se může tato vnitřní regulace lišit kvalitou. Závisí to velkou měrou na kvalitě zařízení, funkčnosti jeho vnitřního teploměru a jeho vnitřního algoritmu. Pro zlepšení zařízení, která regulují špatně, VTherm nabízí způsob úpravy setpointu, který posílá, zvýšením nebo snížením na základě teploty místnosti měřené VTherm, místo vnitřní teploty.

Možnosti samo-regulace jsou podrobně popsány [zde](self-regulation.md).

Aby se zabránilo přetížení podkladového zařízení (některá mohou nepříjemně pípat, jiná běží na baterie atd.), jsou k dispozici dva prahy pro omezení počtu požadavků:
1. Práh regulace: práh v ° (nebo %), pod kterým nebude odeslán nový setpoint. Pokud byl poslední setpoint 22°, další bude 22° ± práh regulace. Pokud se používá přímá regulace ventilu (`over_valve` nebo `over_climate` s přímou regulací ventilu), tato hodnota by měla být v procentech a neměla by být menší než 3% pro Sonoff TRVZB (jinak může Sonoff TRVZB ztratit kalibraci).
2. Minimální období regulace (v minutách): minimální časový interval, pod kterým nebude odeslán nový setpoint. Pokud byl poslední setpoint odeslán v 11:00, další nemůže být odeslán před 11:00 + minimální období regulace.

Nesprávné nastavení těchto prahů může zabránit správné samo-regulaci, protože nebudou odesílány nové setpointy.

### Auto-ventilátor (Auto ventilace)

Tento režim, zavedený ve verzi 4.3, nutí použití ventilace, pokud je rozdíl teplot významný. Aktivací ventilace dochází k rychlejší distribuci tepla, což pomáhá rychleji dosáhnout cílové teploty.
Můžete vybrat, kterou úroveň ventilace aktivovat z následujících možností: Nízká, Střední, Vysoká, Turbo.

Samozřejmě vaše podkladové zařízení musí mít ventilaci a musí být ovladatelná, aby to fungovalo. Pokud vaše zařízení neobsahuje režim Turbo, bude místo toho použit režim Vysoká. Jakmile se rozdíl teplot znovu zmenší, ventilace se přepne do "normálního" režimu, který závisí na vašem zařízení (v pořadí): `Mute`, `Auto`, `Low`. Bude vybrán první dostupný režim pro vaše zařízení.

### Kompenzace vnitřní teploty podkladového vybavení

Upozornění: Tato možnost nesmí být použita s regulací přímého ovládání ventilu, pokud byla poskytnuta kalibrační entita.

Někdy je vnitřní teploměr podkladového zařízení (TRV, klimatizace atd.) nepřesný do té míry, že samo-regulace nestačí. Stává se to, když je vnitřní teploměr umístěn příliš blízko zdroje tepla. Vnitřní teplota stoupá mnohem rychleji než teplota místnosti, což vede k selháním regulace.
Příklad:
1. Teplota místnosti je 18°, setpoint je 20°.
2. Vnitřní teplota zařízení je 22°.
3. Pokud VTherm pošle setpoint 21° (= 20° + 1° samo-regulace), zařízení nebude topit, protože jeho vnitřní teplota (22°) je vyšší než setpoint (21°).

Pro řešení tohoto problému byla ve verzi 5.4 přidána nová volitelná funkce: ![Použití vnitřní teploty](images/config-use-internal-temp.png)

Když je aktivována, tato funkce přidává rozdíl mezi vnitřní teplotou a teplotou místnosti k setpointu, aby vynutil vytápění.
Ve výše uvedeném příkladu je rozdíl +4° (22° - 18°), takže VTherm pošle 25° (21° + 4°) zařízení, což jej donutí topit.

Tento rozdíl se vypočítává pro každé podkladové zařízení, protože každé má svou vlastní vnitřní teplotu. Například VTherm připojený ke třem TRV, každý s vlastní vnitřní teplotou.

To má za následek mnohem efektivnější samo-regulaci, která se vyhýbá problémům s velkými rozdíly vnitřních teplot kvůli vadným senzorům.

Mějte však na paměti, že některé vnitřní teploty kolísají tak rychle a nepřesně, že úplně zkresí výpočet. V tomto případě je lepší tuto možnost zakázat.

Rady, jak správně upravit tato nastavení, najdete na stránce [samo-regulace](self-regulation.md).

> ![Upozornění](images/tips.png) _*Poznámky*_
> Je velmi vzácné potřebovat zaškrtnout toto políčko. Většinou samo-regulace problémy vyřeší. Výsledky vysoce závisí na zařízení a chování jeho vnitřní teploty.
> Tuto možnost byste měli používat pouze pokud všechny ostatní metody selhaly.

## Specifické funkce

Specifické funkce lze konfigurovat prostřednictvím dedikované možnosti v menu.

Specifické funkce, které vyžadují konfiguraci pro tento typ VTherm, jsou:
1. Auto-start/stop: Automatické spuštění a zastavení VTherm na základě předpovědí použití. Toto je popsáno zde: [funkce auto-start/stop](feature-auto-start-stop.md).
2. Pokud je zvolena regulace ventilu, konfigurace algoritmu TPI je přístupná z menu. Viz ([algoritmy](algorithms.md)).

## Sledování změn podkladové teploty

Někteří uživatelé chtějí pokračovat v používání svého zařízení jako dříve (bez _VTherm_). Například můžete chtít použít dálkové ovládání vaší _PAC_ nebo otočit knoflíkem na vaší _TRV_.
Pokud jste v tomto případě, byla do zařízení _VTherm_ přidána entita nazvaná `Follow underlying temp changes`:

![Sledování změn teploty](images/entity-follow-under-temp-change.png)

Když je tato entita 'On', všechny změny teploty nebo stavu provedené přímo na podkladovém zařízení se odrazí ve _VTherm_.

Buďte opatrní, pokud používáte tuto funkci, vaše zařízení je nyní ovládáno dvěma způsoby: _VTherm_ a přímo vámi. Příkazy mohou být protichůdné, což by mohlo vést ke zmatku ohledně stavu zařízení. _VTherm_ je vybaven mechanismem zpoždění, který zabraňuje smyčkám: uživatel dá setpoint, který je zachycen _VTherm_ a změní setpoint, ... Toto zpoždění může způsobit, že změna provedená přímo na zařízení bude ignorována, pokud jsou tyto změny příliš blízko v čase.

Některá zařízení (jako například Daikin) mění stav sama od sebe. Pokud je zaškrtnuté políčko, může to vypnout _VTherm_, když to není to, co jste chtěli.
Proto je lepší to nepoužívat. Generuje to hodně zmatku a mnoho žádostí o podporu.
