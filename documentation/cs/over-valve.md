# Termostat typu `thermostat_over_valve`

> ![Pozornost](images/tips.png) _*Poznámky*_
> 1. Typ `over_valve` je často zaměňován s typem `over_climate` vybaveným auto-regulací a přímým ovládáním ventilu.
> 2. Tento typ byste měli volit pouze když nemáte přidruženou entitu `climate` pro vaši _TRV_ v Home Assistant a pokud máte pouze entitu typu `number` pro ovládání procenta otevření ventilu. `over_climate` s auto-regulací na ventilu je mnohem výkonnější než typ `over_valve`.

## Předpoklady

Instalace by měla být podobná nastavení VTherm `over_switch`, kromě toho, že ovládané zařízení je přímo ventil _TRV_:

![instalace `over_valve`](images/over-valve-schema.png)

1. Uživatel nebo automatizace, nebo Scheduler, nastaví setpoint prostřednictvím preset nebo přímo pomocí teploty.
2. Periodicky vnitřní teploměr (2) nebo vnější teploměr (2b) nebo vnitřní teploměr zařízení (2c) pošle naměřenou teplotu. Vnitřní teploměr by měl být umístěn na relevantním místě pro pohodlí uživatele: ideálně uprostřed obytného prostoru. Vyhněte se umístění příliš blízko okna nebo příliš blízko zařízení.
3. Na základě hodnot setpointu, různých teplot a parametrů algoritmu TPI (viz [TPI](algorithms.md#lalgorithme-tpi)), VTherm vypočítá procento otevření ventilu.
4. Poté upraví hodnotu podkladových entit `number`.
5. Tyto podkladové entity `number` budou ovládat míru otevření ventilu na _TRV_.
6. To bude regulovat vytápění radiátoru.

> Míra otevření se přepočítává každý cyklus, což umožňuje regulaci teploty místnosti.

## Konfigurace

Nejprve nakonfigurujte hlavní nastavení společná pro všechny _VTherm_ (viz [hlavní nastavení](base-attributes.md)).
Poté klikněte na možnost "Podkladové entity" z menu a uvidíte tuto konfigurační stránku, měli byste přidat entity `number`, které budou ovládány VTherm. Akceptovány jsou pouze entity `number` nebo `input_number`.

![image](images/config-linked-entity3.png)

Aktuálně dostupný algoritmus je TPI. Viz [algoritmus](#algorithm).

Je možné vybrat `thermostat_over_valve` pro ovládání klimatizace zaškrtnutím políčka "AC režim". V tomto případě bude viditelný pouze chladicí režim.
