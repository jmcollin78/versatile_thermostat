# Szybki Start

Ta strona przedstawia kroki potrzebne do szybkiego skonfigurowania podstawowego, ale poprawnie działającego termostatu _VTherm_.  
Struktura jest podzielona według typu urządzenia.


- [Szybki start](#quick-start)
  - [Nodon SIN-4-FP-21 lub podobne (przewodowe sterowanie z diodą aktywacyjną)](#nodon-sin-4-fp-21-or-similar-pilot-wire)
  - [Heatzy, eCosy, lub podobne (sterowane encją `climate`)](#heatzy-ecosy-or-similar-climate-entity)
  - [Zwykły przełącznik w rodzaju Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...](#simple-switch-such-as-aqara-t1-nous-b2z-sonoff-zbmini-sonoff-pow-)
  - [Sonoff TRVZB lub podobne (TRV ze sterowaniem zaworem)](#sonoff-trvzb-or-similar-trv-with-valve-control)
  - [Odwracalne jednostki HP, klimatyzatory, lub inne urządzenia sterowane encją `climate`](#reversible-hp-units-air-conditioning-or-devices-controlled-via-a-climate-entity)
- [Następne kroki](#next-steps)
- [Zaproszenie do współpracy](#call-for-contributions)

## Nodon SIN-4-FP-21 lub podobne (przewodowe steroewanie z diodą)

Moduł ten pozwala sterować grzejnik przewodem sterowania. Pojawia się w _HA_ jako encja typu `select` pozwalająca wybrać preset ogrzewania.

_VTherm_ będzie regulować temperaturę poprzez okresową zmianę presetu za pomocą dostosowanych poleceń, aż do osiągnięcia wartości żądanej.

Aby to się udało, preset używany do sterowania ogrzewaniem musi być wyższy, niż maksymalna temperatura oczekiwana (dobrym wyborem jest np. **24°C**).

Aby zintegrować urządzenie z _VTherm_, należy wykonać następujące kroki:
1. Utwórz termostat _VTherm_ typu `termostat na przełączniku`. Zobacz: [Wybór termostatu](creation.md).
2. Przypisz mu główne atrybuty (nazwa, czujnik temperatury w pomieszczeniu oraz czujnik temperatury zewnętrznej). Zobacz: [Wybór głównych atrybutów](base-attributes.md)  
3. Przypisz jedno lub więcej urządzeń podrzędnych do sterowania. Urządzeniem podrzędnym w tym przypadku jest encja `select`, która steruje urządzeniem. Zobacz: [urządzenia](over-switch.md).  
4. Podaj własne polecenia `on`/`off` (obowiązkowe dla urządzenia). Zobacz: [dosotsowywanie poleceń](over-switch.md#command-customization). Polecenia niestandardowe mają format: `select_option/option:<preset>`, zgodnie z opisem w dokumentacji.
Po wykonaniu tych czterech kroków będziesz mieć w pełni funkcjonalny termostat _VTherm_, który będzie sterował Twoim Nodonem lub innym podobnym urządzeniem.

## Heatzy, eCosy, lub podobne (sterowane encją `climate`)

Moduł ten pozwala sterować grzejnikiem, który w **Home Assistant** pojawia się jako encja `climate`, umożliwiając wybór presetu grzania lub trybu (**Heat / Cool / Off**).

Termostat _VTherm_ będzie regulować temperaturę poprzez załączanie/wyłączanie urządzenia za pomocą dostosowanych poleceń w regularnych odstępach czasu, aż do osiągnięcia wartości żądanej.

Aby zintegrować urządzenie z VTherm, należy wykonać następujące kroki:
1. Utwórz termostat _VTherm_ typu `termostat na przełączniku`. Zobacz: [Wybór termostatu](creation.md)  
2. Przypisz mu główne atrybuty (nazwa, czujnik temperatury w pomieszczeniu oraz czujnik temperatury zewnętrznej). Zobacz: [Wybór głównych atrybutów](base-attributes.md).   
3. Przypisz jedno lub więcej urządzeń podrzędnych do sterowania. Urządzeniem podrzędnym w tym przypadku jest encja `climate`, która steruje urządzeniem **Heatzy** lub **eCosy**. Zobacz: [urządzenia](over-switch.md).  
4. Podaj własne polecenia `on`/`off` (obowiązkowe). Zobacz: [dosotsowywanie poleceń](over-switch.md#command-customization). Polecenia niestandardowe mają format: `set_hvac_mode/hvac_mode:<mode>`, zgodnie z opisem w dokumentacji.

Po wykonaniu tych czterech kroków będziesz mieć w pełni funkcjonalny termostat _VTherm_, sterujący Twoim urządzeniem _Heatzy_, _eCosy_ lub podobnym.

## Zwykły przełącznik w rodzaju Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...

Moduł ten pozwala sterować grzejnik zwykłym przełącznikiem. Pojawai się on w _HA_ jako encja `switch`, bezpośrednio załączająca lub wyłączająca grzejnik.

Termostat _VTherm_ będzie regulować temperaturę poprzez okresowe załączanie/wyłączanie urządzenia do momentu osiągnięcia temperatury docelowej.

Aby zintegrować urządzenie z **VTherm**, należy wykonać następujące kroki:
1. Utwórz termostat _VTherm_ typu `termostat na przełączniku`. Zobacz: [Wybór termostatu](creation.md)    
2. Przypisz mu główne atrybuty (nazwa, czujnik temperatury w pomieszczeniu oraz czujnik temperatury zewnętrznej). Zobacz: [Wybór głównych atrybutów](base-attributes.md).  
3. Przypisz jedno lub więcej urządzeń podrzędnych do sterowania. Urządzeniem podrzędnym w tym przypadku jest encja `switch`, która steruje przełącznikiem. Zobacz: [urządzenia](over-switch.md). 

Po wykonaniu tych trzech kroków będziesz mieć w pełni funkcjonalny termostat _VTherm_, sterujący Twoim przełącznikiem lub podobnym urządzeniem.

## Sonoff TRVZB lub podobne (TRV ze sterowaniem zaworem)

Ten typ _TRV_ steruje otwarciem zaworu that pozwala na przepływ większej lub mniejszej ilości ciepłej wody z kotła lub pompy ciepła. Widoczny jest w _HA_ jako encja `climate` wraz z encjami typu `number`, sterującymi zaworem. Encje typu `number` mogą być niewidoczne (ukryte) i w niektórych przypadkach konieczne może być ich jawne dodanie.

**VTherm** dostosowuje stopień otwarcia zaworu aż do osiągnięcia temperatury zadanej.

Aby zintegrować urządzenie z VTherm, należy wykonać następujące kroki:
1. Utwórz termostat _VTherm_ typu `termostat na klimacie`. Zobacz: [Wybór termostatu](creation.md)    
2. Przypisz mu główne atrybuty (nazwa, czujnik temperatury w pomieszczeniu oraz czujnik temperatury zewnętrznej). Zobacz: [Wybór głównych atrybutów](base-attributes.md). 
3. Przypisz jedno lub więcej urządzeń podrzędnych do sterowania. Urządzeniem podrzędnym w tym przypadku jest encja `climate`, która steruje TRV. Zobacz: [urządzenia](over-switch.md).  
4. Określ typ regulacji jako **Bezposrednie sterowanie zaworem**. Pozostaw niezaznaczoną opcję **Kompensacja temperatury podstawowej**. Zobacz [samoregulacja](over-climate.md#auto-regulation).  
5. Podaj encje typu `number` o nazwach `opening_degree`, `closing_degree` oraz `calibration_offset`. Zobacz: [urządzenia](over-switch.md). 


### Ważne uwagi
- Stopień zamknięcia (`closing_degree`) musi być ustawiony na maksimum (`100%`).  
- Nie włączaj od razu opcji `Podążaj za zmianą temperatury`, dopóki nie zweryfikujesz, że podstawowa konfiguracja działa poprawnie.  

Po wykonaniu tych pięciu kroków będziesz mieć w pełni funkcjonalny termostat _VTherm_, który będzie sterował Twoim **Sonoff TRVZB** lub podobny urządzeniem.


## Odwracalne jednostki HP, klimatyzatory, lub inne urządzenia sterowane encją `climate`

Odwracalne pompy ciepła (HP) lub podobne urządzenia, reprezentowane są w _HA_ jako encje `climate`, umożliwiając wybór presetu grzania lub trybu (**Heat / Cool / Off**)

Termostat _VTherm_ będzie regulować temperaturę porównując temperaturę docelową z trybem pracy urządzenia za pomocą poleceń dostosowanych do encji `climate`.

Aby zintegrować urządzenie z _VTherm_, należy wykonać następujące kroki:
1. Utwórz termostat _VTherm_ typu `termostat na klimacie`. Zobacz: [Wybór termostatu](creation.md)    
2. Przypisz mu główne atrybuty (nazwa, czujnik temperatury w pomieszczeniu oraz czujnik temperatury zewnętrznej). Zobacz: [Wybór głównych atrybutów](base-attributes.md). 
3. Zdefiniuj jedno lub więcej urządzeń podrzędnych do sterowania. Urządzeniem podrzędnym w tym przypadku jest encja `climate`, która zarządza pompą ciepła lub klimatyzatorem. Zobacz: [urządzenia](over-climate.md)

Po wykonaniu tych trzech kroków będziesz mieć w pełni funkcjonalny termostat _VTherm_, sterujący Twoją pompą ciepła, klimatyzatorem lub podobnym urządzeniem.

Idąc dalej, może być konieczna **samoregulacja**, w zależności od tego, jak dobrze działa Twoje urządzenie.  
Samoregulacja polega na tym, że termostat _VTherm_ delikatnie dostosowuje temperaturę docelową, aby zachęcić urządzenie do grzania lub chłodzenia bardziej lub mniej, aż do osiągnięcia wartości żądanej.  

Szczegółowe informacje na temat samoregulacji znajdziesz [tutaj:](self-regulation.md)

# Następne kroki

Po utworzeniu termostatu _VTherm_ należy skonfigurować temperatury dla presetów. Zobacz: [Presety](feature-presets.md) dla minimalnej konfiguracji.  
Możesz także (opcjonalnie, ale zalecane) zainstalować dedykowaną kartę [Versatile Thermostat UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card).  

## Rozszerzanie konfiguracji
Gdy minimalna konfiguracja działa poprawnie — i tylko wtedy, gdy działa prawidłowo — możesz dodawać kolejne funkcje, takie jak:
- **Wykrywanie obecności** – aby uniknąć ogrzewania, gdy nikogo nie ma w pomieszczeniu.  
- Dodawaj funkcje pojedynczo, sprawdzając, czy _VTherm_ reaguje poprawnie na każdym etapie, zanim przejdziesz dalej.  

## Konfiguracja centralna
Możesz następnie skonfigurować ustawienia centralne, aby:
- **Udostępniać konfiguracje** pomiędzy wszystkimi instancjami _VTherm_,  
- Włączyć **tryb centralny** dla jednolitego sterowania wszystkimi termostatami _VTherm_ ([zobacz: ](feature-central-mode.md),  
- Zintegrować **sterowanie kotłem głównym** ([zobacz: ](feature-central-boiler.md).  

To nie jest pełna lista — zobacz spis treści, aby poznać wszystkie funkcje _VTherm_.  


# Zaproszenie do współpracy

Ta strona jest otwarta na współpracę. Możesz swobodnie proponować sprawdzone, dodatkowe urządzenia oraz ich minimalne konfiguracje.
