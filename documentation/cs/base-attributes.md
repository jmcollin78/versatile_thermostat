- [Výběr základních atributů](#výběr-základních-atributů)
- [Výběr funkcí k použití](#výběr-funkcí-k-použití)

# Výběr základních atributů

Vyberte menu "Hlavní atributy".

![image](images/config-main.png)

| Atribut | Popis | Název atributu |
| ------- | ----- | -------------- |
| **Název** | Název entity (toto bude název integrace a entity `climate`). | |
| **Teplotní senzor** | ID entity senzoru poskytujícího teplotu místnosti, kde je zařízení nainstalováno. | |
| **Senzor poslední aktualizace (volitelný)** | Zabraňuje bezpečnostním vypnutím, když je teplota stabilní a senzor přestane hlásit. (viz [řešení problémů](troubleshooting.md#why-does-my-versatile-thermostat-go-into-safety-mode)) | |
| **Délka cyklu** | Délka v minutách mezi každým výpočtem. Pro `over_switch`: moduluje čas zapnutí. Pro `over_valve`: počítá otevření ventilu. Pro `over_climate`: provádí kontroly a přepočítává koeficienty samo-regulace. U typů `over_switch` a `over_valve` se výpočty provádějí v každém cyklu. V případě změny podmínek budete muset počkat na další cyklus, abyste viděli změnu. Z tohoto důvodu by cyklus neměl být příliš dlouhý. 5 minut je dobrá hodnota, ale měla by být upravena podle vašeho typu vytápění. Čím větší setrvačnost, tím delší by měl být cyklus. Viz [Příklady ladění](tuning-examples.md). Pokud je cyklus příliš krátký, radiátor možná nikdy nedosáhne cílové teploty. Například u akumulačního ohřívače bude zbytečně aktivován. | `cycle_min` |
| **Výkon zařízení** | Aktivuje senzory výkonu/energie. Zadejte celkový, pokud více zařízení (stejná jednotka jako ostatní VThermy a senzory). (viz: funkce omezení výkonu) | `device_power` |
| **Centralizované dodatečné parametry** | Používá venkovní teplotu, min/max/krok teploty z centralizované konfigurace. | |
| **Centralizované ovládání** | Umožňuje centralizované ovládání termostatu. Viz [centralizované ovládání](#centralized-control) | `is_controlled_by_central_mode` |
| **Spouštěč centrálního kotle** | Zaškrtávací políčko pro použití tohoto VThermu jako spouštěče centrálního kotle. | `is_used_by_central_boiler` |

# Výběr funkcí k použití

Vyberte menu "Funkce".

![image](images/config-features.png)

| Funkce | Popis | Název atributu |
| ------- | ----- | -------------- |
| **S detekcí otevření** | Zastaví vytápění při otevření dveří/oken. (viz [správa otevření](feature-window.md)) | `is_window_configured` |
| **S detekcí pohybu** | Upraví cílovou teplotu při detekci pohybu v místnosti. (viz [detekce pohybu](feature-motion.md)) | `is_motion_configured` |
| **S správou výkonu** | Zastaví zařízení při překročení prahu spotřeby energie. (viz [správa omezení zátěže](feature-power.md)) | `is_power_configured` |
| **S detekcí přítomnosti** | Změní cílovou teplotu na základě přítomnosti/nepřítomnosti. Liší se od detekce pohybu (dům vs místnost). (viz [správa přítomnosti](feature-presence.md)) | `is_presence_configured` |
| **S automatickým spuštěním/zastavením** | Pouze pro `over_climate`: zastaví/spustí zařízení na základě predikce teplotní křivky. (viz [správa automatického spuštění/zastavení](feature-auto-start-stop.md)) | `is_window_auto_configured` |

> ![Tip](images/tips.png) _*Poznámky*_
> 1. Seznam dostupných funkcí se přizpůsobuje vašemu typu VTherm.
> 2. Když povolíte funkci, přidá se nová položka menu pro její konfiguraci.
> 3. Nemůžete potvrdit vytvoření VTherm, pokud nebyly nakonfigurovány všechny parametry pro všechny povolené funkce.
