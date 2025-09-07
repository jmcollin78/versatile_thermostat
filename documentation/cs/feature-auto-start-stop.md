# Automatické spuštění / Automatické zastavení

- [Automatické spuštění / Automatické zastavení](#automatické-spuštění--automatické-zastavení)
  - [Konfigurace automatického spuštění/zastavení](#konfigurace-automatického-spuštěnízastavení)
  - [Použití](#použití)

Tato funkce umožňuje _VTherm_ zastavit zařízení, které nepotřebuje být zapnuté, a restartovat jej, když podmínky to vyžadují. Tato funkce zahrnuje tři nastavení, která kontrolují, jak rychle je zařízení zastaveno a restartováno.
Výhradně vyhrazeno pro _VTherm_ typu `over_climate`, vztahuje se na následující případ použití:
1. Vaše zařízení je trvale napájeno a spotřebovává elektřinu i když není potřeba vytápění (nebo chlazení). To je často případ tepelných čerpadel (_PAC_), která spotřebovávají energii i v pohotovostním režimu.
2. Teplotní podmínky jsou takové, že vytápění (nebo chlazení) není potřeba po dlouhou dobu: setpoint je vyšší (nebo nižší) než teplota místnosti.
3. Teplota stoupá (nebo klesá), zůstává stabilní, nebo klesá (nebo stoupá) pomalu.

V takových případech je lepší požádat zařízení, aby se vypnulo, aby se zabránilo zbytečné spotřebě energie v pohotovostním režimu.

## Konfigurace automatického spuštění/zastavení

Pro použití této funkce musíte:
1. Přidat funkci `S automatickým spuštěním a zastavením` v menu 'Funkce'.
2. Nastavit úroveň detekce v možnosti 'Automatické spuštění/zastavení', která se objeví, když je funkce aktivována. Vyberte úroveň detekce mezi 'Pomalá', 'Střední' a 'Rychlá'. S nastavením 'Rychlá' budou zastavení a restarty probíhat častěji.

![image](images/config-auto-start-stop.png)

Nastavení 'Velmi pomalá' umožňuje asi 60 minut mezi zastavením a restartem,
Nastavení 'Pomalá' umožňuje asi 30 minut mezi zastavením a restartem,
Nastavení 'Střední' nastavuje práh na asi 15 minut a nastavení 'Rychlá' jej pokládá na 7 minut.

Všimněte si, že toto nejsou absolutní nastavení, protože algoritmus bere v úvahu sklon křivky teploty místnosti, aby odpovídajícím způsobem reagoval. Stále je možné, že restart nastane krátce po zastavení, pokud teplota výrazně klesne.

## Použití

Jakmile je funkce nakonfigurována, budete mít nyní novou entitu typu `switch`, která vám umožní povolit nebo zakázat automatické spuštění/zastavení bez úpravy konfigurace. Tato entita je dostupná na zařízení _VTherm_ a má název `switch.<n>_enable_auto_start_stop`.

![image](images/enable-auto-start-stop-entity.png)

Zaškrtněte políčko pro povolení automatického spuštění a zastavení a nechte jej nezaškrtnuté pro deaktivaci funkce.

Poznámka: Funkce automatického spuštění/zastavení znovu zapne _VTherm_ pouze pokud byl vypnut touto funkcí. To zabraňuje nežádoucím nebo neočekávaným aktivacím. Přirozeně je vypnutý stav zachován i po restartu Home Assistant.

> ![Tip](images/tips.png) _*Poznámky*_
> 1. Algoritmus detekce je popsán [zde](algorithms.md#auto-startstop-algorithm).
> 2. Některá zařízení (kotle, podlahové vytápění, _PAC_, atd.) nemusí mít ráda příliš časté spuštění/zastavení. Pokud je to případ, může být lepší deaktivovat funkci, když víte, že bude zařízení použito. Například deaktivuji tuto funkci během dne, když je detekována přítomnost, protože vím, že moje _PAC_ se často zapne. Povolit automatické spuštění/zastavení v noci nebo když nikdo není doma, protože setpoint je snížen a zřídka se spouští.
> 3. Pokud používáte UI kartu Versatile Thermostat (viz [zde](additions.md#better-with-the-versatile-thermostat-ui-card)), zaškrtávací políčko je přímo viditelné na kartě pro deaktivaci automatického spuštění/zastavení a _VTherm_ zastavený automatickým spuštěním/zastavením je označen ikonou: ![ikona automatického spuštění/zastavení](images/auto-start-stop-icon.png).
