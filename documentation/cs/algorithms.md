# Různé používané algoritmy

- [Různé používané algoritmy](#různé-používané-algoritmy)
  - [Algoritmus TPI](#algoritmus-tpi)
    - [Konfigurace koeficientů algoritmu TPI](#konfigurace-koeficientů-algoritmu-tpi)
    - [Princip](#princip)
  - [Algoritmus samo-regulace (bez ovládání ventilu)](#algoritmus-samo-regulace-bez-ovládání-ventilu)
  - [Algoritmus funkce auto-start/stop](#algoritmus-funkce-auto-startstop)

## Algoritmus TPI

### Konfigurace koeficientů algoritmu TPI

Pokud jste vybrali termostat typu `over_switch`, `over_valve` nebo `over_climate` se samo-regulací v režimu `Přímé ovládání ventilu` a zvolíte možnost "TPI" v menu, dostanete se na tuto stránku:

![image](images/config-tpi.png)

Musíte zadat:
1. koeficient `coef_int` pro algoritmus TPI,
2. koeficient `coef_ext` pro algoritmus TPI.

### Princip

Algoritmus TPI vypočítá procento Zapnuto vs Vypnuto pro radiátor v každém cyklu, používaje cílovou teplotu, aktuální teplotu místnosti a aktuální venkovní teplotu. Tento algoritmus je použitelný pouze pro Versatile Thermostaty pracující v režimech `over_switch` a `over_valve`.

Procento se vypočítá pomocí tohoto vzorce:

    on_percent = coef_int * (cílová_teplota - aktuální_teplota) + coef_ext * (cílová_teplota - venkovní_teplota)
    Poté algoritmus zajistí, že 0 <= on_percent <= 1.

Výchozí hodnoty pro `coef_int` a `coef_ext` jsou `0.6` a `0.01`. Tyto výchozí hodnoty jsou vhodné pro standardní dobře izolovanou místnost.

Při úpravě těchto koeficientů mějte na paměti následující:
1. **Pokud cílová teplota není dosažena** po stabilizaci, zvyšte `coef_ext` (`on_percent` je příliš nízký),
2. **Pokud je cílová teplota překročena** po stabilizaci, snižte `coef_ext` (`on_percent` je příliš vysoký),
3. **Pokud je dosažení cílové teploty příliš pomalé**, zvyšte `coef_int` pro poskytnutí více výkonu ohřívači,
4. **Pokud je dosažení cílové teploty příliš rychlé a dochází k oscilacím** kolem cíle, snižte `coef_int` pro poskytnutí menšího výkonu radiátoru.

V režimu `over_valve` se hodnota `on_percent` převede na procento (0 až 100%) a přímo ovládá úroveň otevření ventilu.

## Algoritmus samo-regulace (bez ovládání ventilu)

Algoritmus samo-regulace lze shrnout následovně:

1. Inicializace cílové teploty jako setpoint VTherm,
2. Pokud je samo-regulace povolena:
   1. Vypočítání regulované teploty (platné pro VTherm),
   2. Použití této teploty jako cíle,
3. Pro každé podkladové zařízení VTherm:
     1. Pokud je zaškrtnuto "Použít vnitřní teplotu":
          1. Vypočítání kompenzace (`trv_internal_temp - room_temp`),
     2. Přidání offsetu k cílové teplotě,
     3. Odeslání cílové teploty (= regulated_temp + (internal_temp - room_temp)) podkladovému zařízení.

## Algoritmus funkce auto-start/stop

Algoritmus používaný ve funkci auto-start/stop funguje následovně:
1. Pokud je "Povolit auto-start/stop" vypnuto, zde končíme.
2. Pokud je VTherm zapnutý a v režimu vytápění, když `error_accumulated` < `-error_threshold` -> vypnout a uložit HVAC režim.
3. Pokud je VTherm zapnutý a v režimu chlazení, když `error_accumulated` > `error_threshold` -> vypnout a uložit HVAC režim.
4. Pokud je VTherm vypnutý a uložený HVAC režim je vytápění, a `current_temperature + slope * dt <= target_temperature`, zapnout a nastavit HVAC režim na uložený režim.
5. Pokud je VTherm vypnutý a uložený HVAC režim je chlazení, a `current_temperature + slope * dt >= target_temperature`, zapnout a nastavit HVAC režim na uložený režim.
6. `error_threshold` je nastaven na `10 (° * min)` pro pomalou detekci, `5` pro střední a `2` pro rychlou.

`dt` je nastaven na `30 min` pro pomalou, `15 min` pro střední a `7 min` pro rychlou úroveň detekce.

Funkce je podrobně popsána [zde](https://github.com/jmcollin78/versatile_thermostat/issues/585).
