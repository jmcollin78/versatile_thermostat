- [Výběr základních atributů](#výběr-základních-atributů)
- [Výběr funkcí k použití](#výběr-funkcí-k-použití)

# Výběr základních atributů

Vyberte menu "Hlavní atributy".

![image](images/config-main.png)

Zadejte povinné hlavní atributy. Tyto atributy jsou společné pro všechny VTherm:
1. Název (to bude jak název integrace, tak název entity `climate`),
2. ID entity teplotního senzoru, který poskytuje teplotu místnosti, kde je radiátor nainstalován,
3. Volitelný senzor entity poskytující datum a čas posledního zobrazení senzoru (`last_seen`). Pokud je dostupný, zadejte jej zde. Pomáhá předcházet bezpečnostním vypnutím, když je teplota stabilní a senzor přestane hlásit po dlouhou dobu (viz [zde](troubleshooting.md#why-does-my-versatile-thermostat-go-into-safety-mode)),
4. Trvání cyklu v minutách. V každém cyklu:
   1. Pro `over_switch`: VTherm zapne/vypne radiátor, moduluje podíl času, kdy je zapnutý,
   2. Pro `over_valve`: VTherm vypočítá novou úroveň otevření ventilu a pošle ji, pokud se změnila,
   3. Pro `over_climate`: Cyklus provádí základní kontroly a přepočítává koeficienty samo-regulace. Cyklus může mít za následek nový setpoint zaslaný podkladovým zařízením nebo úpravu otevření ventilu v případě ovladatelného TRV.
5. Výkon vybavení, který aktivuje senzory spotřeby energie a výkonu pro zařízení. Pokud je více zařízení propojeno se stejným VTherm, zadejte zde celkový maximální výkon všech zařízení. Jednotka výkonu zde není důležitá. Důležité je, aby všechny _VTherm_ a všechny výkonové senzory měly stejnou jednotku (viz: funkce omezení výkonu),
6. Možnost použít další parametry z centralizované konfigurace:
   1. Senzor venkovní teploty,
   2. Minimální/maximální teplota a velikost teplotního kroku,
7. Možnost centrálně ovládat termostat. Viz [centralizované ovládání](#centralized-control),
8. Zaškrtávací políčko, pokud je tento VTherm použit pro spuštění centrálního kotle.

> ![Tip](images/tips.png) _*Poznámky*_
>  1. U typů `over_switch` a `over_valve` se výpočty provádějí v každém cyklu. V případě změny podmínek budete muset počkat na další cyklus, abyste viděli změnu. Z tohoto důvodu by cyklus neměl být příliš dlouhý. **5 minut je dobrá hodnota**, ale měla by být upravena podle vašeho typu vytápění. Čím větší setrvačnost, tím delší by měl být cyklus. Viz [Příklady ladění](tuning-examples.md).
>  2. Pokud je cyklus příliš krátký, radiátor možná nikdy nedosáhne cílové teploty. Například u akumulačního ohřívače bude zbytečně aktivován.

# Výběr funkcí k použití

Vyberte menu "Funkce".

![image](images/config-features.png)

Vyberte funkce, které chcete použít pro tento VTherm:
1. **Detekce otevření** (dveře, okna) zastaví vytápění, když je detekováno otevření. (viz [správa otevření](feature-window.md)),
2. **Detekce pohybu**: VTherm může upravit cílovou teplotu, když je detekován pohyb v místnosti. (viz [detekce pohybu](feature-motion.md)),
3. **Správa výkonu**: VTherm může zastavit zařízení, pokud spotřeba energie ve vašem domě překročí práh. (viz [správa omezení zátěže](feature-power.md)),
4. **Detekce přítomnosti**: Pokud máte senzor indikující přítomnost nebo nepřítomnost ve vašem domě, můžete jej použít ke změně cílové teploty. Viz [správa přítomnosti](feature-presence.md). Poznamenejte rozdíl mezi touto funkcí a detekcí pohybu: přítomnost se obvykle používá na úrovni domova, zatímco detekce pohybu je více specifická pro místnost.
5. **Automatické spuštění/zastavení**: Pouze pro VTherm `over_climate`. Tato funkce zastaví zařízení, když VTherm detekuje, že nebude po nějakou dobu potřeba. Používá teplotní křivku k predikci, kdy bude zařízení znovu potřeba, a v tu dobu jej znovu zapne. Viz [správa automatického spuštění/zastavení](feature-auto-start-stop.md).

> ![Tip](images/tips.png) _*Poznámky*_
> 1. Seznam dostupných funkcí se přizpůsobuje vašemu typu VTherm.
> 2. Když povolíte funkci, přidá se nová položka menu pro její konfiguraci.
> 3. Nemůžete potvrdit vytvoření VTherm, pokud nebyly nakonfigurovány všechny parametry pro všechny povolené funkce.
