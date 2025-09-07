# Centralizované ovládání

- [Centralizované ovládání](#centralizované-ovládání)
  - [Konfigurace centralizovaného ovládání](#konfigurace-centralizovaného-ovládání)
  - [Použití](#použití)

Tato funkce vám umožňuje ovládat všechny vaše _VTherm_ z jednoho kontrolního bodu.
Typický případ použití je, když odjíždíte na delší období a chcete nastavit všechny vaše _VTherm_ na protimrazovou ochranu, a když se vrátíte, chcete je nastavit zpět do jejich původního stavu.

Centralizované ovládání se provádí ze speciálního _VTherm_ nazývaného centralizovaná konfigurace. Viz [zde](creation.md#centralized-configuration) pro více informací.

## Konfigurace centralizovaného ovládání

Pokud jste nastavili centralizovanou konfiguraci, budete mít novou entitu s názvem `select.central_mode`, která vám umožní ovládat všechny _VTherm_ jednou akcí.

![central_mode](images/central-mode.png)

Tato entita se objevuje jako seznam voleb obsahující následující možnosti:
1. `Auto`: 'normální' režim, kde každý _VTherm_ funguje autonomně,
2. `Stopped`: všechny _VTherm_ jsou vypnuty (`hvac_off`),
3. `Heat only`: všechny _VTherm_ jsou nastaveny do režimu vytápění, pokud je podporován, jinak jsou zastaveny,
4. `Cool only`: všechny _VTherm_ jsou nastaveny do režimu chlazení, pokud je podporován, jinak jsou zastaveny,
5. `Frost protection`: všechny _VTherm_ jsou nastaveny do režimu protimrazové ochrany, pokud je podporován, jinak jsou zastaveny.

## Použití

Aby _VTherm_ byl ovladatelný centrálně, jeho konfigurační atribut s názvem `use_central_mode` musí být true. Tento atribut je dostupný na konfigurační stránce `Hlavní atributy`.

![central_mode](images/use-central-mode.png)

To znamená, že můžete ovládat všechny _VTherm_ (ty výslovně určené) jediným ovládáním.
