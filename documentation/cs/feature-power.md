# Správa výkonu - Omezení zátěže

- [Správa výkonu - Omezení zátěže](#správa-výkonu---omezení-zátěže)
    - [Příklad případu použití:](#příklad-případu-použití)
  - [Konfigurace správy výkonu](#konfigurace-správy-výkonu)

Tato funkce umožňuje regulovat elektrickou spotřebu vašich ohřívačů. Známá jako omezení zátěže, umožňuje omezit elektrickou spotřebu vašeho topného vybavení, pokud jsou detekované podmínky nadměrné spotřeby.
Budete potřebovat **senzor pro celkovou okamžitou spotřebu energie** vašeho domova a **senzor pro maximální povolenou spotřebu**.

Chování této funkce je následující:
1. Když je přijato nové měření spotřeby energie domova nebo maximální povolené spotřeby,
2. Pokud je překročena maximální spotřeba, centrální příkaz omezí zátěž všech aktivních zařízení počínaje těmi nejblíže k setpointu. To pokračuje, dokud není omezeno dostatek _VTherm_,
3. Pokud je k dispozici rezerva energie a některé _VTherm_ jsou omezeny, centrální příkaz znovu povolí co nejvíce zařízení, počínaje těmi nejdále od setpointu (v době, kdy byly omezeny).
4. Když se _VTherm_ spustí, provádí se kontrola k určení, zda je deklarovaná spotřeba dostupná. Pokud ne, _VTherm_ je uveden do režimu omezení.

**UPOZORNĚNÍ:** Toto **není bezpečnostní funkce**, ale optimalizační funkce pro správu spotřeby na úkor určitého zhoršení vytápění. Nadměrná spotřeba je stále možná v závislosti na frekvenci aktualizací vašeho senzoru spotřeby a skutečné spotřebě vašeho vybavení. Vždy udržujte bezpečnostní rezervu.

### Příklad případu použití:
1. Máte elektrický měřič omezený na 11 kW,
2. Občas nabíjíte elektrické vozidlo na 5 kW,
3. To ponechává 6 kW pro všechno ostatní, včetně vytápění,
4. Máte 1 kW jiných aktivních zařízení,
5. Deklarujete senzor (`input_number`) pro maximální povolenou spotřebu na 9 kW (= 11 kW - rezervovaná spotřeba pro jiná zařízení - bezpečnostní rezerva).

Pokud se vozidlo nabíjí, celková spotřebovaná energie je 6 kW (5 + 1) a _VTherm_ se zapne pouze pokud jeho deklarovaná spotřeba je maximálně 3 kW (9 kW - 6 kW).
Pokud se vozidlo nabíjí a další _VTherm_ o 2 kW je zapnutý, celková spotřebovaná energie je 8 kW (5 + 1 + 2) a _VTherm_ se zapne pouze pokud jeho deklarovaná spotřeba je maximálně 1 kW (9 kW - 8 kW). Jinak přeskočí svůj tah (cyklus).
Pokud se vozidlo nenabíjí, celková spotřebovaná energie je 1 kW a _VTherm_ se zapne pouze pokud jeho deklarovaná spotřeba je maximálně 8 kW (9 kW - 1 kW).

## Konfigurace správy výkonu

V centralizované konfiguraci, pokud jste vybrali funkci `S detekcí výkonu`, nakonfigurujte ji takto:

![image](images/config-power.png)

1. ID entity **senzoru pro celkovou okamžitou spotřebu energie** vašeho domova,
2. ID entity **senzoru pro maximální povolenou spotřebu**,
3. Teplotu k aplikaci, pokud je aktivováno omezení zátěže.

Ujistěte se, že všechny hodnoty výkonu používají stejné jednotky (např. kW nebo W).
Mít **senzor pro maximální povolenou spotřebu** vám umožní dynamicky upravovat maximální spotřebu pomocí scheduleru nebo automatizace.

Poznamenejte, že kvůli centralizovanému omezení zátěže není možné přepsat senzory spotřeby a maximální spotřeby na jednotlivých _VTherm_. Tato konfigurace musí být provedena v centralizovaných nastaveních. Viz [Centralizovaná konfigurace](./creation.md#centralized-configuration).

> ![Tip](images/tips.png) _*Poznámky*_
>
> 1. Během omezení zátěže je ohřívač nastaven na preset s názvem `power`. Toto je skrytý preset, který nemůže být ručně vybrán.
> 2. Vždy udržujte rezervu, protože maximální spotřeba může být krátce překročena při čekání na výpočet dalšího cyklu nebo kvůli neovládaným zařízením.
> 3. Pokud nechcete tuto funkci používat, odškrtněte ji v menu 'Funkce'.
> 4. Pokud jeden _VTherm_ ovládá více zařízení, **deklarovaná spotřeba topení** by měla odpovídat celkové spotřebě všech zařízení.
> 5. Pokud používáte Versatile Thermostat UI kartu (viz [zde](additions.md#better-with-the-versatile-thermostat-ui-card)), omezení zátěže je reprezentováno takto: ![load shedding](images/power-exceeded-icon.png).
> 6. Může být zpoždění až 20 sekund mezi přijetím nové hodnoty ze senzoru spotřeby energie a spuštěním omezení zátěže pro _VTherm_. Toto zpoždění zabraňuje přetížení Home Assistant, pokud jsou vaše aktualizace spotřeby velmi časté.
