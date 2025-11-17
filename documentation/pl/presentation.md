# Warunki stosowania integracji `Versatile Thermostat`
Termostat _VTherm_ może sterować 3 typami urządzeń:
1. Grzejnik działający wyłącznie w trybie `on`/`off` (nazywany też `termostatem na przełączniku`). Minimalna konfiguracja wymagana do użycia tego typu termostatu obejmuje:
   1. Urządzenie takie, jak grzejnik (`switch` lub odpowiednik),
   2. Czujnik temperatury dla pomieszczenia (lub `input_number`),
   3. Zewnętrzny czujnik temperatury (rozważ integrację pogodową, jeśli nie masz takiego czujnika).
2. Inny termostat posiadający własne tryby pracy (nazywany także `termostatem na klimacie`). Dla tego typu termostatu minimalna konfiguracja wymaga:
   1. Urządzenia – np. klimatyzacji, zaworu termostatycznego – sterowanego przez własną encję `climate`.
3. Urządzenie, które może przyjmować wartość od 0 do 100% (nazywane `termostatem na zaworze`). Przy wartości `0` ogrzewanie jest wyłączone, a przy `100%` zawór jest całkowicie otwarty. Ten typ pozwala sterować zaworem termostatycznym (np. zawór Shelly), który udostępnia encję typu `number`, umożliwiając bezpośrednie sterowanie stopniem otwarcia zaworu. Versatile Thermostat reguluje temperaturę w pomieszczeniu poprzez dostosowanie procentu otwarcia, wykorzystując zarówno czujniki temperatury wewnętrznej i zewnętrznej, jak i algorytm TPI opisany poniżej.

Typ `termostatu na klimacie` pozwala dodać wszystkie funkcje oferowane przez Versatile Thermostat do istniejącego sprzętu. Encja `climate` termostatu będzie sterować Twoją bazową encją `climate` – wyłączy ją, jeśli okna są otwarte, przełączy w tryb `Eco`, jeśli nikt nie jest obecny, itd. (patrz: [tutaj](#pourquoi-un-nouveau-thermostat-implémentation)).

Dla tego typu termostatu wszystkie cykle grzewcze są kontrolowane przez bazową encję `climate`, a nie przez sam termostat. Opcjonalna funkcja autoregulacji pozwala termostatom _VTherm_ dostosować temperaturę zadaną do encji bazowej, aby osiągnąć wartość docelową.

Instalacje z przewodowym sterowaniem z diodą aktywacyjną korzystają z opcji umożliwiającej odwrócenie sterowania `on`/`off` bazowego grzejnika. Aby to zrobić, użyj typu `termostat na przełączniku` i zaznacz opcję `Inwersja polecenia`.

# Kiedy dodać nowy termostat _VTherm_?
Komponent `Versatile Thermostat` obsługuje następujące przypadki:
- Konfiguracja poprzez standardowy graficzny interfejs integracji,
- Pełne wykorzystanie trybu presetu,
- Wyłączenie trybu presetu, gdy temperatura zostanie ustawiona ręcznie na termostacie,
- Wyłączenie/załączenie termostatu lub zmiana presetu, gdy drzwi lub okna zostaną otwarte/zamknięte po określonym czasie,
- Zmiana presetu, gdy w określonym czasie w pomieszczeniu zostanie wykryta aktywność lub jej brak,
- Wykorzystanie algorytmu TPI (_Time Proportional Interval_) dzięki [Argonaute],
- Dodanie zarządzania redukcją obciążenia lub regulacji, aby nie przekroczyć zdefiniowanej całkowitej mocy. Gdy maksymalna moc zostanie przekroczona, na encji `climate` ustawiane jest ukryty preset '`moc`'. Gdy moc spadnie poniżej maksimum, przywracane jest poprzedne ustawienie.
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

## Przełączniki z przewodem sterującym
Stosuje się je do sterowania grzejnikami elektrycznymi wyposażonymi w przewód sterujący z diodą. Są użyteczne dla [`termostatu na przełączniku`](over-switch.md) oraz dla celów [personalizacji polecenień](over-switch.md#la-personnalisation-des-commandes):

- [⭐ Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6828-nodon-module-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)
- [⭐ 4 x Nodon SIN-4-1-21 Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7050-nodon-pack-4x-modules-chauffage-fil-pilote-connecte-zigbee-30.html?domid=97)

## Zawory termostatyczne
Służą do sterowania grzejnika wodnego. Współpracują z [`termostatem na zaworze`](over-valve.md) lub [`termostatem na klimacie` z bezpośrednim sterowaniem zaworem](over-climate.md#thermostat-de-type-over_climate):

- [⭐ Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/6776-sonoff-tete-thermostatique-connectee-zigbee-30.html?domid=97) z [`termostatem na klimacie` z bezpośrednim sterowaniem zaworem](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 2 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7477-sonoff-pack-de-2x-tete-thermostatique-connectee-zigbee-30.html?domid=97) z [`termostatem na klimacie` z bezpośrednim sterowaniem zaworem](over-climate.md#thermostat-de-type-over_climate),
- [⭐ 4 x Sonoff TRVZB Zigbee](https://www.domadoo.fr/fr/chauffage-connecte/7478-sonoff-pack-de-4x-tete-thermostatique-connectee-zigbee-30.html?domid=97) z [`termostatem na klimacie` z bezpośrednim sterowaniem zaworem](over-climate.md#thermostat-de-type-over_climate),
- [Shelly BLU TRV BLE](https://www.domadoo.fr/fr/black-friday-domotique/7567-shelly-robinet-thermostatique-de-radiateur-a-commande-bluetooth-shelly-blu-trv-3800235264980.html?domid=97) z [`termostatem na zaworze`](over-valve.md),
- [Moes TRV Zigbee](https://www.domadoo.fr/fr/peripheriques/5783-moes-tete-thermostatique-intelligente-zigbee-30-brt-100-trv-blanc.html?domid=97) z [`termostatem na klimacie` (bez bezpośredniego sterowania zaworem)](over-climate.md#thermostat-de-type-over_climate)
- [Schneider Wiser TRV Zigbee](https://www.domadoo.fr/fr/controle-chauffage-clim/5497-schneider-electric-tete-de-vanne-thermostatique-connectee-zigbee-3606489582821.html?domid=97) z [`termostatem na klimacie` (bez bezpośredniego sterowania zaworem)](over-climate.md#thermostat-de-type-over_climate)

## Termostaty TRV niekompatybilne z integracją _Versatile Thermostat_
Niektóre termostaty typu TRV są niekompatybilne z integracją _Versatile Thermostat_. Dotyczy to następujących urządzeń:
1. Zawory _Danfoss POPP_ z informacją zwrotną o temperaturze. Niemożliwe jest wyłączenie tego zaworu, ponieważ ma wyłącznie samoregulację, co powoduje konflikty z termostatem _VTherm_.
2. Termostaty _Homematic_ (i prawdopodobnie Homematic IP) mają problemy z integracją _Versatile Thermostat_ z powodu ograniczeń protokołu RF. Problem szczególnie pojawia się przy próbie sterowania wieloma termostatami _Homematic_ jednocześnie w jednej instancji _VTherm_. Aby zmniejszyć obciążenie cyklu serwisowego, można np. grupować termostaty za pomocą procedur specyficznych dla _Homematic_ (np. używając termostatu ściennego) i pozwolić integracji _Versatile Thermostat_ sterować bezpośrednio tylko tym termostatem ściennym. Inną opcją jest sterowanie jednym termostatem i propagowanie zmian trybu oraz temperatury poprzez automatyzację.
3. Termostaty typu _Heatzy_, które nie obsługują poleceń `set_temperature`.
4. Termostaty typu _Rointe_ mają tendencję do samoczynnego wybudzania się. Pozostałe funkcje działają normalnie.
5. TRV takie jak _Aqara SRTS-A01_ i _MOES TV01-ZB_, które nie posiadają informacji zwrotnej o stanie `hvac_action`, aby określić, czy grzeją, czy nie. W związku z tym informacja zwrotna o stanie jest niedokładna, ale pozostałe funkcje wydają się działać.
6. Klimatyzatory _Airwell_ z integracją `Midea AC LAN`. Jeśli dwa polecenia _VTherm_ są wysyłane w czasie zbyt blisko siebie, klimatyzator sam się zatrzymuje.
7. Systemy klimatyzacji oparte na integracji _Overkiz_ nie działają. Wydaje się niemożliwe wyłączenie lub nawet zmiana temperatury w tych systemach.
8. Systemy grzewcze oparte na _Netatmo_ działają słabo. Harmonogramy _Netatmo_ kolidują z oprogramowaniem _VTherm_. Urządzenia _Netatmo_ stale wracają do trybu `Auto`, który jest słabo obsługiwany przez _VTherm_. W tym trybie _VTherm_ nie może bowiem określić, czy system grzeje, czy chłodzi, co uniemożliwia wybór właściwego algorytmu. Niektórzy użytkownicy zdołali uruchomić system, używając wirtualnego przełącznika pomiędzy _VTherm_ a systemem bazowym, ale stabilność nie jest gwarantowana. Przykład znajduje się w sekcji [Rozwiązywanie problemów](troubleshooting.md).

### Problemy z kompatybilnością TRV i możliwe obejścia

| Urządzenie / typ | Problem | Możliwe obejście |
|------------------|---------|------------------|
| **Danfoss POPP (z feedbackiem temperatury)** | Zawór sam się autoreguluje, nie da się go wyłączyć → konflikt z VTherm | Brak obejścia – niezalecane użycie |
| **Homematic / Homematic IP** | Ograniczenia protokołu RF, problemy przy sterowaniu wieloma termostatami jednocześnie | Grupowanie termostatów przez procedury Homematic (np. termostat ścienny) i sterowanie tylko nim; alternatywnie sterowanie jednym termostatem i propagowanie zmian przez automatyzację |
| **Heatzy** | Brak obsługi komend `set_temperature` | Brak obejścia – niezalecane użycie |
| **Rointe** | Samoczynne wybudzanie się urządzenia | Akceptacja tego zachowania – pozostałe funkcje działają normalnie |
| **Aqara SRTS-A01 / MOES TV01-ZB** | Brak feedbacku `hvac_action` → nie wiadomo, czy grzeją | Można używać, ale stan jest niedokładny; pozostałe funkcje działają |
| **Airwell (Midea AC LAN)** | Jeśli dwa polecenia VTherm są zbyt blisko siebie, klimatyzator sam się zatrzymuje | Wydłużenie odstępów między poleceniami |
| **Overkiz (klimatyzacja)** | Brak możliwości wyłączenia lub zmiany temperatury | Brak obejścia – niekompatybilne |
| **Netatmo (systemy grzewcze)** | Harmonogramy Netatmo kolidują z VTherm | Brak obejścia – niekompatybilne |

