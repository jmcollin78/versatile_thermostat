# Předvolby (Předkonfigurovaná nastavení)

- [Předvolby (Předkonfigurovaná nastavení)](#předvolby-předkonfigurovaná-nastavení)
  - [Konfigurace předkonfigurovaných teplot](#konfigurace-předkonfigurovaných-teplot)

## Konfigurace předkonfigurovaných teplot

Režim předvoleb umožňuje předkonfigurovat cílovou teplotu. Použito ve spojení se Scheduler (viz [scheduler](additions.md#the-scheduler-component)), budete mít výkonný a jednoduchý způsob optimalizace teploty vzhledem ke spotřebě elektřiny ve vašem domě. Spravované předvolby jsou následující:
 - **Eco**: zařízení je v úsporném režimu
 - **Comfort**: zařízení je v komfortním režimu
 - **Boost**: zařízení plně otevírá všechny ventily

Pokud se používá AC režim, můžete také konfigurovat teploty, když je zařízení v režimu klimatizace.

**None** (Žádná) je vždy přidána do seznamu režimů, protože je to způsob, jak nepoužívat předvolby, ale místo toho nastavit **manuální teplotu**.

Předvolby jsou konfigurovány přímo z entit _VTherm_ nebo z centrální konfigurace, pokud používáte centralizované ovládání. Při vytváření _VTherm_ budete mít různé entity, které vám umožní nastavit teploty pro každou předvolbu:

![presets](images/config-preset-temp.png).

Seznam entit se liší v závislosti na vašich volbách funkcí:
1. Pokud je aktivována funkce 'detekce přítomnosti', budete mít předvolby s verzí "nepřítomnost" předponou _abs_.
2. Pokud jste vybrali možnost _AC_, budete mít také předvolby pro 'klimatizaci' s předponou _clim_.

> ![Tip](images/tips.png) _*Poznámky*_
>
> 1. Když ručně změníte cílovou teplotu, předvolba se přepne na None (žádná předvolba).
> 2. Standardní předvolba `Away` je skrytá předvolba, kterou nelze přímo vybrat. Versatile Thermostat používá správu přítomnosti nebo detekci pohybu k automatickému a dynamickému přizpůsobení cílové teploty na základě přítomnosti v domě nebo aktivity v místnosti. Viz [správa přítomnosti](feature-presence.md).
> 3. Pokud používáte správu omezení zátěže, uvidíte skrytou předvolbu nazvanou `power`. Předvolba topného prvku je nastavena na "power", když jsou splněny podmínky přetížení a omezení zátěže je aktivní pro daný topný prvek. Viz [správa výkonu](feature-power.md).
> 4. Pokud používáte pokročilou konfiguraci, uvidíte předvolbu nastavenou na `safety`, pokud teplotu nebylo možné získat po určité době. Viz [Bezpečnostní režim](feature-advanced.md#safety-mode).
