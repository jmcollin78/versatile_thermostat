# Příklady ladění

- [Příklady ladění](#příklady-ladění)
  - [Elektrické vytápění](#elektrické-vytápění)
  - [Ústřední vytápění (plynové nebo olejové)](#ústřední-vytápění-plynové-nebo-olejové)
  - [Teplotní senzor na baterie](#teplotní-senzor-na-baterie)
  - [Reaktivní teplotní senzor (napájený)](#reaktivní-teplotní-senzor-napájený)
  - [Moje presety](#moje-presety)

## Elektrické vytápění
- Cyklus: mezi 5 a 10 minutami,
- minimal_activation_delay_sec: 30 sekund

## Ústřední vytápění (plynové nebo olejové)
- Cyklus: mezi 30 a 60 minutami,
- minimal_activation_delay_sec: 300 sekund (kvůli době odezvy)

## Teplotní senzor na baterie
Tyto senzory jsou často pomalé a ne vždy posílají teplotní údaje, když je teplota stabilní. Proto by nastavení měla být volná, aby se zabránilo falešným pozitivům.

- safety_delay_min: 60 minut (protože tyto senzory jsou pomalé)
- safety_min_on_percent: 0.7 (70% - systém přejde do bezpečnostního režimu, pokud bylo topení zapnuto více než 70% času)
- safety_default_on_percent: 0.4 (40% - v bezpečnostním režimu udržujeme 40% času topení, aby se příliš nevychladilo)

Tato nastavení by měla být chápána takto:

> Pokud teploměr přestane posílat teplotní údaje na 1 hodinu a procento vytápění (``on_percent``) bylo větší než 70%, pak bude procento vytápění sníženo na 40%.

Neváhejte upravit tato nastavení podle vašeho konkrétního případu!

Důležité je nevzít příliš velké riziko s těmito parametry: předpokládejte, že jste delší dobu nepřítomni a baterie vašeho teploměru se vybíjejí, vaše topení bude běžet 40% času během celého období selhání.

Versatile Thermostat vám umožňuje být upozorněni, když se taková událost stane. Nastavte příslušná upozornění, jakmile začnete tento termostat používat. Viz (#notifications).

## Reaktivní teplotní senzor (napájený)
Napájený teploměr by měl být velmi pravidelný v posílání teplotních údajů. Pokud nepošle nic po dobu 15 minut, nejpravděpodobněji má problém a můžeme reagovat rychleji bez rizika falešného pozitivu.

- safety_delay_min: 15 minut
- safety_min_on_percent: 0.5 (50% - systém přejde do presetem ``security``, pokud bylo topení zapnuto více než 50% času)
- safety_default_on_percent: 0.25 (25% - v presetem ``security`` udržujeme 25% času topení)

## Moje presety
Toto je pouze příklad toho, jak používám preset. Můžete jej přizpůsobit vaší konfiguraci, ale může být užitečné pro pochopení jeho funkčnosti.

``Protimrazová ochrana``: 10°C
``Eco``: 17°C
``Komfort``: 19°C
``Boost``: 20°C

Když je přítomnost zakázána:
``Protimrazová ochrana``: 10°C
``Eco``: 16.5°C
``Komfort``: 17°C
``Boost``: 17.5°C

Detektor pohybu v mé kanceláři je nakonfigurován pro použití ``Boost``, když je detekován pohyb, a ``Eco`` jinak.

Bezpečnostní režim je nakonfigurován takto:

![Moje nastavení](images/my-tuning.png)
