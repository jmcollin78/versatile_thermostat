# When to Use and Not Use It
Termostat może sterować 3 typami urządzeń:
1. Grzejnik działający wyłącznie w trybie on/off (nazywany thermostat_over_switch). Minimalna konfiguracja wymagana do użycia tego typu termostatu obejmuje:
   1. Urządzenie takie jak grzejnik (`switch` lub odpowiednik),
   2. Czujnik temperatury dla pomieszczenia (lub `input_number`),
   3. Zewnętrzny czujnik temperatury (rozważ integrację pogodową, jeśli nie masz takiego czujnika).
2. Inny termostat posiadający własne tryby pracy (nazywany thermostat_over_climate). Dla tego typu termostatu minimalna konfiguracja wymaga:
   1. Urządzenia – np. klimatyzacji, zaworu termostatycznego – sterowanego przez własną encję climate.
3. Urządzenie, które może przyjmować wartość od 0 do 100% (nazywane `termostatem na zaworze`). Przy wartości `0` ogrzewanie jest wyłączone, a przy `100%` zawór jest całkowicie otwarty. Ten typ pozwala sterować zaworem termostatycznym (np. zawór Shelly), który udostępnia encję typu `number`, umożliwiając bezpośrednie sterowanie stopniem otwarcia zaworu. Versatile Thermostat reguluje temperaturę w pomieszczeniu poprzez dostosowanie procentu otwarcia, wykorzystując zarówno czujniki temperatury wewnętrznej i zewnętrznej, jak i algorytm TPI opisany poniżej.

Typ `termostatu na klimacie` pozwala dodać wszystkie funkcje oferowane przez Versatile Thermostat do istniejącego sprzętu. Encja `climate` termostatu będzie sterować Twoją bazową encją `climate` – wyłączy ją, jeśli okna są otwarte, przełączy w tryb `Eco`, jeśli nikt nie jest obecny, itd. (patrz: [tutaj](#pourquoi-un-nouveau-thermostat-implémentation).

Dla tego typu termostatu wszystkie cykle grzewcze są kontrolowane przez bazową encję `climate`, a nie przez sam termostat. Opcjonalna funkcja autoregulacji pozwala termostatom _VTherm_ dostosować temperaturę zadaną do encji bazowej, aby osiągnąć wartość docelową.

Instalacje z pilotem przewodowym i diodą aktywacyjną korzystają z opcji umożliwiającej odwrócenie sterowania `on`/`off` bazowego grzejnika. Aby to zrobić, użyj typu `termostat na przełączniku` i zaznacz opcję `Inwersja polecenia`.

# Dlaczego nowa implementacja termostatu?
Komponent `Versatile Thermostat` obsługuje następujące przypadki użycia:
- Konfiguracja poprzez standardowy graficzny interfejs integracji (przy użyciu Config Entry flow),
- Pełne wykorzystanie trybu ustawień wstępnych,
- Wyłączenie trybu ustawień wstępnych, gdy temperatura zostanie ustawiona ręcznie na termostacie,
- Wyłączenie/załączenie termostatu lub zmiana ustawień wstępnych, gdy drzwi lub okna zostaną otwarte/zamknięte po określonym czasie,
- Zmiana ustawienia wstępnego, gdy w określonym czasie w pomieszczeniu zostanie wykryta aktywność lub jej brak,
- Wykorzystanie algorytmu TPI (_Time Proportional Interval_) dzięki [Argonaute],
- Dodanie zarządzania redukcją obciążenia lub regulacji, aby nie przekroczyć zdefiniowanej całkowitej mocy. Gdy maksymalna moc zostanie przekroczona, na encji `climate` ustawiane jest ukryte ustawenie wstępne '`moc`'. Gdy moc spadnie poniżej maksimum, przywracane jest poprzedne ustawienie.
- Zarządzanie obecnością. Funkcja ta pozwala dynamicznie modyfikować temperaturę ustawienia na podstawie czujnika obecności w domu.
- Akcje do interakcji z termostatem z innych integracji: możesz wymusić obecność/nieobecność za pomocą usługi oraz dynamicznie zmieniać temperatury i modyfikować ustawienia bezpieczeństwa.
- Dodanie czujników do podglądu wewnętrznych stanów termostatu,
- Centralne sterowanie wszystkimi termostatami _Versatile Thermostat_: zatrzymanie wszystkich, ustawienie wszystkich w tryb ochrony przed mrozem, wymuszenie trybu grzania (zimą), wymuszenie trybu chłodzenia (latem).
- Sterowanie centralnym kotłem grzewczym oraz termostatami, kontrolującymi ten kocioł.
- Automatyczne uruchamianie/zatrzymywanie na podstawie prognozy użycia dla `termostatu na klimacie`.

Wszystkie te funkcje mogą być konfigurowane centralnie lub indywidualnie – w zależności od Twoich potrzeb.

# Urządzenia

Aby używać termostatów  _VTherm_, potrzebujesz odpowiednich urządzeń. Poniższa lista nie jest wyczerpująca, ale obejmuje najczęściej używane urządzenia, które są w pełni kompatybilne z Home Assistant i VTherm.
Są to linki partnerskie do sklepu [Domadoo](https://www.domadoo.fr/fr/?domid=97), co pozwala mi otrzymać niewielki procent prowizji, jeśli dokonasz zakupu przez te linki. Zamawiając w [Domadoo](https://www.domadoo.fr/fr/?domid=97), otrzymujesz konkurencyjne ceny, gwarancję zwrotu oraz bardzo krótki czas dostawy – porównywalny z innymi dużymi sprzedawcami internetowymi. Ich ocena 4.8/5 mówi sama za siebie. 

⭐ : Najczęściej używane, a więc najlepszy wybór.

## Termometry
Niezbędne w konfiguracji _VTherm_ – zewnętrzne urządzenie do pomiaru temperatury umieszczone we właściwym miejscu, zapewnia niezawodną, komfortową i stabilną kontrolę temperatury.

- [⭐ Sonoff SNZB Zigbee](https://www.domadoo.fr/fr/suivi-energie/6614-sonoff-capteur-de-temperature-et-d-humidite-zigbee-30-avec-ecran-6920075740004.html??domid=97)
- [⭐ 4 x Sonoff SNZB Zigbee](https://www.domadoo.fr/fr/suivi-energie/6968-sonoff-pack-4x-capteurs-de-temperature-et-d-humidite-zigbee-ecran.html?domid=97)
- [ Neo Tuya Zigbee](https://www.domadoo.fr/fr/produits-compatibles-jeedom/7564-neo-capteur-de-temperature-et-humidite-zigbee-30-tuya.html?domid=97)
- [ Moes Tuya Zigbee](https://www.domadoo.fr/fr/domotique/6667-moes-capteur-de-temperature-et-humidite-avec-ecran-zigbee-tuya.html?domid=97)

## Przełączniki
Służą do bezpośredniego sterowania grzejnikami elektrycznymi. Użyteczne dla [`termostatów na przełączniku`](over-switch.md):

- [⭐ Sonoff Power Switch 25 A Wifi](https://www.domadoo.fr/fr/peripheriques/5853-sonoff-commutateur-intelligent-wifi-haute-puissance-25a-6920075776768.html?domid=97)
- [⭐ Nodon SIN-4-1-20 Zigbee](https://www.domadoo.fr/fr/peripheriques/5688-nodon-micromodule-commutateur-multifonctions-zigbee-16a-3700313925188.html?domid=97)
- [Sonoff 4-channel Wifi](https://www.domadoo.fr/fr/peripheriques/5279-sonoff-commutateur-intelligent-wifi-433-mhz-4-canaux-6920075775815.html?domid=97)
- [Smart plug for small heating equipment Zigbee](https://www.domadoo.fr/fr/peripheriques/5880-sonoff-prise-intelligente-16a-zigbee-30-version-fr.html?domid=97)

## Pilot wire switches
To directly control an electric heater equipped with a pilot wire. Usable with _VTherm_ [`over_switch`](over-switch.md) and [customized commands](over-switch.md#la-personnalisation-des-commandes):

- [⭐ Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6828-nodon-module-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)
- [⭐ 4 x Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7050-nodon-pack-4x-modules-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)

## Thermostatic valves
To control a water radiator. Works with a _VTherm_ [`over_valve`](over-valve.md) or [`over_climate` with direct valve control](over-climate.md#thermostat-de-type-over_climate):

- [⭐ Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6776-sonoff-tete-thermostatique-connectee-zigbee-30.html?domid=97) with [`over_climate` with direct valve control](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 2 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7477-sonoff-pack-de-2x-tete-thermostatique-connectee-zigbee-30.html?domid=97) with [`over_climate` with direct valve control](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 4 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7478-sonoff-pack-de-4x-tete-thermostatique-connectee-zigbee-30.html?domid=97) with [`over_climate` with direct valve control](over-climate.md#thermostat-de-type-over_climate),
- [Shelly BLU TRV BLE](https://www.domadoo.fr/fr/black-friday-domotique/7567-shelly-robinet-thermostatique-de-radiateur-a-commande-bluetooth-shelly-blu-trv-3800235264980.html?domid=97) with [`over_valve`](over-valve.md),
- [Moes TRV Zigbee](https://www.domadoo.fr/fr/peripheriques/5783-moes-tete-thermostatique-intelligente-zigbee-30-brt-100-trv-blanc.html?domid=97) with [`over_climate` (without direct valve control)](over-climate.md#thermostat-de-type-over_climate)
- [Schneider Wiser TRV Zigbee](https://www.domadoo.fr/fr/controle-chauffage-clim/5497-schneider-electric-tete-de-vanne-thermostatique-connectee-zigbee-3606489582821.html?domid=97) with [`over_climate` (without direct valve control)](over-climate.md#thermostat-de-type-over_climate)

## Incompatibilities
Some TRV type thermostats are known to be incompatible with Versatile Thermostat. This includes the following valves:
1. Danfoss POPP valves with temperature feedback. It is impossible to turn off this valve as it auto-regulates itself, causing conflicts with VTherm.
2. "Homematic" thermostats (and possibly Homematic IP) are known to have issues with Versatile Thermostat due to the limitations of the underlying RF protocol. This problem particularly arises when trying to control multiple Homematic thermostats at once in a single VTherm instance. To reduce service cycle load, you can, for example, group thermostats using Homematic-specific procedures (e.g., using a wall-mounted thermostat) and let Versatile Thermostat control only the wall-mounted thermostat directly. Another option is to control a single thermostat and propagate mode and temperature changes via automation.
3. Heatzy type thermostats that do not support `set_temperature` commands.
4. Rointe type thermostats tend to wake up on their own. The rest works normally.
5. TRVs like Aqara SRTS-A01 and MOES TV01-ZB, which lack the `hvac_action` state feedback to determine whether they are heating or not. Therefore, state feedback is inaccurate, but the rest seems functional.
6. Airwell air conditioners with the "Midea AC LAN" integration. If two VTherm commands are too close together, the air conditioner stops itself.
7. Climates based on the Overkiz integration do not work. It seems impossible to turn off or even change the temperature on these systems.
8. Heating systems based on Netatmo perform poorly. Netatmo schedules conflict with _VTherm_ programming. Netatmo devices constantly revert to `Auto` mode, which is poorly managed with _VTherm_. In this mode, _VTherm_ cannot determine whether the system is heating or cooling, making it impossible to select the correct algorithm. Some users have managed to make it work using a virtual switch between _VTherm_ and the underlying system, but stability is not guaranteed. An example is provided in the [troubleshooting](troubleshooting.md) section.

