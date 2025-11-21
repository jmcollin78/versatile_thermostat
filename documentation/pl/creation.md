# Wybór termostatu

- [Wybór termostatu](#choosing-a-vtherm)
  - [Tworzenie nowego termostatu](#creating-a-new-versatile-thermostat)
- [Wybór typu termostatu](#choosing-a-vtherm-type)
  - [Główna konfiguracja](#centralized-configuration)
  - [Termostat na przełączniku](#vtherm-over-a-switch)
  - [Termostat na innym termostacie](#vtherm-over-another-thermostat)
  - [Termostat na zaworze](#vtherm-over-a-valve)
- [Dokonywanie właściwych wyborów](#making-the-right-choice)
- [Odsyłacze](#reference-article)

> ![Tip](images/tips.png) _*Wskazówki*_
> 
> Istnieją trzy sposoby konfiguracji termostatu:
> 1. Każdy termostat jest w pełni konfigurowany niezależnie od pozostałych. Wybierz tę opcję, jeśli nie chcesz używać ani konfiguracji scentralizowanej, ani zarządzania.
> 2. Niektóre elementy są konfigurowane centralnie. Np. możesz zdefiniować minimalne/maksymalne temperatury, parametry detekcji otwartego okna itp. w jednej centralnej instancji. Dla każdego skonfigurowanego termostatu możesz następnie wybrać, czy używać konfiguracji scentralizowanej, czy zastąpić ją własnymi parametrami. 
> 3. Oprócz konfiguracji scentralizowanej wszystkie termostaty mogą być sterowane przez pojedynczą jednostkę `select` o nazwie `central_mode`. Ta funkcja pozwala zatrzymać/uruchomić/ustawić ochronę przed mrozem itp. jednocześnie dla wszystkich termostatów. Dla każdego termostatu możesz określić, czy ma być objęty działaniem `central_mode`.


## Tworzenie nowego termostatu

Wybierz 'Dodaj integrację' w oknie panelu integracji HA lub kliknij 'Dodaj urządzenie' w oknie integracji Vtherm...

![image](images/add-an-integration.png)

...i wyszukaj integrację 'Versatile Thermostat':

![image](images/choose-integration.png)

a następnie wybierz typ termostatu:

![image](images/config-main0.png)

Konfigurację można modyfikować za pomocą tego samego interfejsu. Wystarczy wybrać termostat do edycji i nacisnąć 'Konfiguruj'. Tutaj będzie można zmienić niektóre parametry lub ustawienia.


Postępuj zgodnie z krokami konfiguracji, wybierając z menu właściwą opcję konfiguracyjną.

# Wybór typu termostatu

## Główna konfiguracja
Ta opcja pozwala skonfigurować pewne powtarzalne elementy jednocześnie dla wszystkich termostatów, takie jak:
1. Parametry dla różnych algorytmów (TPI, detekcja otwartego okna, ruchu, czy obecności, sensory mocy). Parametry te obowiązują dla wszystkich termostatów. Wystarczy wprowadzić je raz w konfiguracji głównej (scentralizowanej). Ta konfiguracja nie tworzy samodzielnie termstatu, lecz centralizuje parametry, których ponowne wprowadzanie dla każdego termostatu byłoby uciążliwe. Zwróć uwagę, że możesz nadpisać te parametry na poszczególnych termostatach, aby móc je dostosować w razie potrzeby.
2. Konfiguracja sterowania centralnym systemem ogrzewania,
3. Niektóre zaawansowane parametry, takie jak ustawienia bezpieczeństwa.

## Termostat na przełączniku
Ten typ termostatu steruje przełącznikiem, który załącza lub wyłącza grzejnik. Przełącznik może być fizycznym przełącznikiem bezpośrednio sterującym grzejnikiem (często elektrycznym) lub przełącznikiem wirtualnym, który może wykonywać dowolne działanie po załączeniu lub wyłączeniu. Ten drugi typ może na przykład sterować przełącznikami przewodu sterującego z diodą lub własnymi rozwiązaniami DIY. Termostat reguluje proporcję czasu, przez jaki grzejnik jest załączony (`on_percent`), aby osiągnąć żądaną temperaturę. Jeśli jest zimno, włącza się częściej (do 100%); jeśli jest ciepło, skraca czas działania.

Podstawowymi encjami dla tego typu są encje `switch` lub `input_boolean`.

## Termostat na innym termostacie
Jeśli Twoje urządzenie jest sterowane przez encję `climate` w Home Assistant i masz dostęp tylko do niej, powinieneś użyć tego typu termostatu. W takim przypadku termostat po prostu dostosowuje docelową temperaturę z encji `climate`.

Ten typ zawiera również zaawansowane funkcje samoregulacji, które dostosowują wartość zadaną wysyłaną do urządzenia, pomagając szybciej osiągnąć docelową temperaturę i łagodząc słabą regulację wewnętrzną. Na przykład, jeśli wewnętrzny termometr urządzenia znajduje się zbyt blisko grzejnika, może błędnie zakładać, że pomieszczenie jest ogrzane, podczas gdy w innych punktach tego pomieszczenia żądana wartość temperatury nie została jeszcze osiągnięta.

Począwszy od wersji 6.8 ten typ termostatu może również regulować temperaturę bezpośrednio poprzez sterowanie zaworem. Idealny dla sterowalnych głowic termostatycznych (TRV), takich jak Sonoff TRVZB — ten typ jest zalecany, jeśli posiadasz takie urządzenia.

Podstawowymi encjami dla tego typu termostatu są wyłącznie encje `climate`.

## Termostat na zaworze
Jeśli jedyną dostępną encją do regulacji temperatury grzejnika jest encja typu `number`, powinieneś użyć typu `termostat na zaworze`. Termostat dostosowuje otwarcie zaworu na podstawie różnicy między temperaturą docelową a rzeczywistą temperaturą w pomieszczeniu (oraz temperaturą zewnętrzną, jeśli jest dostępna).

Ten typ może być używany dla głowic termostatycznych (TRV) bez powiązanej encji `climate` lub innych rozwiązań DIY udostępniających encję typu `number`.

# Dokonywanie właściwych wyborów
> ![Tip](images/tips.png) _*Jak wybrać typ?*_
>
> Wybór odpowiedniego typu jest kluczowy. Nie można go później zmienić za pomocą interfejsu konfiguracji. Aby dokonać właściwego wyboru, rozważ następujące zagadnienia:
> 1. **Jakiego rodzaju urządzeniem będę sterować?** Kieruj się poniższą kolejnością preferencji:
>    1. Jeśli masz sterowalną głowicę termostatyczną (TRV) w Home Assistant poprzez encję typu `number` (np. Shelly TRV), wybierz typ `termostat na zaworze`. Jest to najbardziej bezpośredni typ i zapewnia najlepszą regulację.
>    2. Jeśli masz grzejnik elektryczny (z przewodem sterującym z diodą), sterowany przez encję `switch` do jego załączania/wyłączania, preferowany jest typ `termostat na przełączniku`. Regulacja będzie realizowana przez termostat na podstawie temperatury mierzonej przez termometr w miejscu jego umieszczenia.
>    3. We wszystkich innych przypadkach użyj trybu `termostat na klimacie`. Zachowujesz swoją oryginalną encję `climate`, a termostat jedynie steruje stanem załączenia/wyłączenia oraz temperaturą docelową oryginalnego termostatu. Regulacja jest w tym przypadku realizowana przez oryginalny termostat. Ten tryb szczególnie dobrze sprawdza się w systemach klimatyzacji typu "wszystko w jednym" z funkcją rewersji, które są eksponowane jako encja `climate` w Home Assistant. Zaawansowana samoregulacja może szybciej osiągnąć wartość zadaną poprzez jej wymuszenie lub bezpośrednie sterowanie zaworem, jeśli to możliwe.
> 2. **Jakiego rodzaju regulacji oczekuję?** Jeśli sterowane urządzenie posiada własny wbudowany mechanizm regulacji (np. systemy HVAC, niektóre TRV) i działa on dobrze, wybierz `termostat na klimacie`. Dla TRV z zaworem sterowalnym w Home Assistant najlepszym wyborem będzie typ `termostat na klimacie` z samoregulacją `Bezpośrednie sterowanie zaworem`.


# Odsyłacze
Wiecej informacji (w jęz. francuskim) na temat omawianych tu zagadnień znajdziesz tutaj: https://www.hacf.fr/optimisation-versatile-thermostat/#optimiser-vos-vtherm
