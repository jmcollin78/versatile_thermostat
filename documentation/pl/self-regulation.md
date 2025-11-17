# Samoregulacja

- [Samoregulacja](#self-regulation)
    - [Samoregulacja w trybie `Ekspert`](#self-regulation-in-expert-mode)
    - [Podsumowanie algorytmu samoregulacji](#summary-of-the-self-regulation-algorithm)


Funkcja samoregulacji jest dostępna tylko dla termostatu _VTherm_ typu `termostat na klimaciee`.

Istnieją dwa typowe przypadki zastosowań tej funkcji:
1. Jeśli Twoim urządzeniem bazowym jest termostat _TRV_ typu `climate`, a zaworem można sterować bezpośrednio w *Home Assistant* (np. *Sonoff TRVZB*), ta funkcja umożliwi termostatowi _VTherm_ bezpośrednie sterowanie otwarciem zaworu w celu regulacji temperatury. Otwarcie jest następnie obliczane za pomocą algorytmu typu _TPI_ (patrz: [tutaj](algorithms.md)).
2. W przeciwnym razie termostat _VTherm_ dostosuje ustawienie temperatury podane dla  urządzenia `climate`, aby zapewnić faktyczne osiągnięcie temperatury w pomieszczeniu zgodnie z ustawioną wartością.

## Konfiguracja

### Samoregulacja z bezpośrednim sterowaniem zaworem

Ten typ samoregulacji, nazwany 'Bezpośrednim sterowaniem zaworami', wymaga:
1. Encji typu `climate` pochodzącej z urządzenia bazowego _VTherm_.
2. Encji typu `number` do sterowania szybkością otwierania zaworu _TRV_.
3. Opcjonalnej encji typu `number` do kalibracji temperatury wewnętrznej urządzenia bazowego.
4. Opcjonalnej encji typu `number` do sterowania zamykaniem zaworu.

Gdy wybraną samoregulacją jest 'bezpośrednie sterowanie zaworem' `termostatu na klimacie`, pojawia się nowe okno konfiguracji o nazwie 'Konfiguracja regulacji zaworów':

![image](images/config-self-regulation-valve-1.png)

Pozwala ono skonfigurować ustawienia sterowania zaworem:

![image](images/config-self-regulation-valve-2.png)

Należy podać:
1. Tyle jednostek sterujących otwieraniem zaworu, ile jest urządzeń bazowych, w tej samej kolejności. Parametry te są **obowiązkowe**.
2. Tyle jednostek kalibracji temperatury, ile jest urządzeń bazowych, w tej samej kolejności. Parametry te są **opcjonalne**. Należy podać je **wszystkie** lub nie podawać **żadnych**. Zdecydowanie zaleca się ich użycie, jeśli są dostępne.
3. Tyle jednostek sterujących szybkością zamykania zaworu, ile jest urządzeń bazowych, w tej samej kolejności. Parametry te są **opcjonalne**. Należy podać je **wszystkie** lub nie podawać **żadnych**. Zdecydowanie zaleca się ich użycie, jeśli są dostępne.
4. Listę minimalnych wartości otwarcia zaworu, gdy zawór ma być otwarty. To pole jest listą liczb całkowitych. Jeśli zawór musi być otwarty, otworzy się co najmniej do tej wartości; w przeciwnym razie będzie całkowicie zamknięty (0). Zapewnia to wystarczający przepływ wody, gdy wymagane jest ogrzewanie, a jednocześnie pełne zamknięcie, gdy ogrzewanie nie jest potrzebne.

Algorytm obliczania współczynnika otwierania oparty jest na _TPI_, który opisano [tutaj](algorithms.md). Jest to ten sam algorytm, który jest używany dla `termostatu na przełączniku` i `termostatu na zaworze`.

Jeśli skonfigurowano jednostkę współczynnika zamykania zaworu, zostanie ona ustawiona na `100 - współczynnik otwierania`, aby wymusić przejście zaworu w określony stan. W przeciwnym razie zostanie ustawiona na `100`.

> ![Warning](images/tips.png) _*Wskazówki*_
> 1. Od wersji 7.2.2 możliwe jest użycie encji `stopień zamknięcia` zaworu Sonoff TRVZB.
> 2. Atrybut `hvac_action` zaworów termostatycznych Sonoff TRVZB jest zawodny. Jeśli temperatura wewnętrzna zaworu termostatycznego znacznie odbiega od temperatury w pomieszczeniu, encja `climate` może wskazywać, że zawór _TRV_ nie grzeje, nawet gdy otwieranie zaworu jest wymuszane przez _VTherm_. Ten problem nie ma wpływu, ponieważ encja `climate` zaworu _VTherm_ została poprawiona i uwzględnia stopień otwarcia zaworu przy ustawianiu atrybutu `hvac_action`. Problem ten można złagodzić, ale nie wyeliminować całkowicie, odpowiednio korygując konfigurację kalibracji temperatury.
> 3. Atrybut `valve_open_percent` zaworu _VTherm_ może nie być zgodny z wartością `stopień otwarcia` wysłaną do zaworu. Jeśli skonfigurowano minimalną wartość otwarcia lub użyto sterowania zamykaniem, zostanie dokonana korekta. Atrybut `valve_open_percent` reprezentuje *wartość surową*, obliczoną przez termostat _VTherm_. Wartość `stopnia otwarcia` wysłana do zaworu może zostać odpowiednio dostosowana.
 

### Inna samoregulacja

W drugim przypadku _*Versatile Thermostat*_ oblicza offset (przesunięcie) na podstawie następujących informacji:
1. Aktualnej różnicy między temperaturą rzeczywistą a temperaturą zadaną, zwanej *błędem brutto*.
2. Kumulacji błędów z przeszłości.
3. Różnicy między temperaturą zewnętrzną a temperaturą zadaną.

Te trzy informacje są łączone w celu obliczenia offsetu, który zostanie dodany do bieżącej temperatury zadanej i przesłany do urządzenia.

Samoregulacja jest konfigurowana za pomocą:
1. Stopnia regulacji:
   1. **Słaby** – dla małych potrzeb samoregulacji. W tym trybie maksymalny offset wyniesie `1,5°C`.
   2. **Średni** – dla średnich potrzeb samoregulacji. W tym trybie możliwy jest maksymalny offset `2°C`.
   3. **Silny** – dla dużych potrzeb samoregulacji. W tym trybie maksymalny offset wynosi `3°C`, a samoregulacja będzie silnie reagować na zmiany temperatury.
2. Progu samoregulacji: wartość, poniżej której nie zostanie zastosowana żadna nowa regulacja. Np. jeśli w chwili `t` offset wynosi `2°C`, a przy następnym obliczeniu offset wynosi `2,4°C`, regulacja nie zostanie wykonana. Zostanie zastosowana tylko wtedy, gdy różnica między dwoma offsetami będzie co najmniej równa temu progowi.
3. Minimalnego okresu między dwiema samoregulacjami: ta liczba, wyrażona w minutach, wskazuje czas między dwiema zmianami regulacji.

Te trzy parametry pozwalają dostosować regulację i uniknąć zbyt wielu zmian. Niektóre urządzenia, takie jak termostaty termostatyczne (TRV) lub kotły, nie lubią częstych zmian swoich ustawień.

> ![Tip](images/tips.png) _*Porady dotyczące konfiguracji*_
> 1. Nie uruchamiaj samoregulacji od razu. Obserwuj, jak działa naturalna regulacja urządzenia. Jeśli zauważysz, że ustawiona wartość nie jest osiągana lub jej osiągnięcie zajmuje zbyt dużo czasu, wówczas uruchom regulację.
> 2. Zacznij od słabej samoregulacji i utrzymuj oba parametry na wartościach domyślnych. Odczekaj kilka dni i sprawdź, czy sytuacja się poprawi.
> 3. Jeśli to nie wystarczy, przełącz się na średnią samoregulację i poczekaj na stabilizację.
> 4. Jeśli to nadal nie wystarczy, przełącz się na silną samoregulację.
> 5. Jeśli nadal nie jest to prawidłowe, musisz przejść do trybu *eksperckiego*, aby precyzyjnie dostosować parametry regulacji.

Samoregulacja wymusza na urządzeniu dalszą pracę poprzez regularną regulację ustawień.

#### Samoregulacja w *trybie eksperckim*

W trybie **eksperckim** możesz precyzyjnie dostosować parametry samoregulacji, aby osiągnąć cel i zoptymalizować wydajność. Algorytm oblicza różnicę między wartością zadaną a rzeczywistą temperaturą w pomieszczeniu. Różnica ta nazywana jest _*błędem*_.

Dostępne są następujące parametry regulacji:
1. `kp`: współczynnik stosowany do _*błędu brutto*_,
2. `ki`: współczynnik stosowany do _*błędów skumulowanych*_,
3. `k_ext`: współczynnik stosowany do różnicy między temperaturą wewnętrzną a temperaturą zewnętrzną,
4. `offset_max`: maksymalna korekta (offset), jaką może zastosować regulacja,
5. `stabilization_threshold`: próg stabilizacji, który po osiągnięciu _*błędu*_ resetuje _*błędy skumulowane*_ do zera (`0`),
6. `accumulated_error_threshold`: maksymalna wartość _*kumulacji błędów*_.

Podczas dostrajania należy wziąć pod uwagę następujące obserwacje:
1. `kp * error` zwróci wartość offsetu związaną z _*błędem brutto*_. Ten offset jest wprost proporcjonalny do _*błędu*_ i będzie wynosić zero (`0`) po osiągnięciu celu.
2. _*Kumulacja błędu*_ pomaga skorygować krzywą stabilizacji, nawet jeśli błąd nadal występuje. Błąd kumuluje się, a offset stopniowo rośnie, co powinno ustabilizować temperaturę wokół celu. Aby uzyskać zauważalny efekt, ten parametr nie powinien być zbyt mały. Średnia wartość to `30`.
3. `ki *accumd_error_threshold` zwróci maksymalny offset związany ze _*skumulowanym błędem*_.
4. `k_ext` umożliwia natychmiastową (bez czekania na _*skumulowane błędy*_) korektę, gdy temperatura zewnętrzna znacznie różni się od temperatury docelowej. Jeśli stabilizacja jest zbyt wysoka przy dużych różnicach temperatur, ten parametr może być zbyt wysoki. Powinien być regulowany do zera, aby umożliwić pierwszym dwóm offsetom wykonanie pracy.

Wstępnie zaprogramowane wartości są następujące:

**Powolna regulacja**:
```yaml
    kp: 0.2  # 20% bieżącego offsetu regulacji wewnętrznej spowodowane jest różnicą między temperaturą docelową a temperaturą aktualną pomieszczenia
    ki: 0.8 / 288.0  # 80% bieżącego offsetu regulacji wewnętrznej jest spowodowane średnim odchyleniem z ostatnich 24 godzin.
    k_ext: 1.0 / 25.0  # do offsetu zostanie dodany 1°C, gdy temperatura na zewnątrz będzie o 25°C niższa niż w pomieszczeniu.
    offset_max: 2.0  # limit ostatecznego offsetu: -2°C do +2°C
    stabilization_threshold: 0.0  # należy wyłączyć tę opcję, ponieważ w przeciwnym razie długoterminowy 'błąd skumulowany' będzie zawsze resetowany, gdy temperatura na krótko przekroczy lub będzie poniżej/powyżej wartości docelowej.
    accumulated_error_threshold: 2.0 * 288  # ta opcja pozwala na długoterminowy offset do 2°C w obu kierunkach.
```
**Słaba regulacja**:
```yaml
    kp: 0.2
    ki: 0.05
    k_ext: 0.05
    offset_max: 1.5
    stabilization_threshold: 0.1
    accumulated_error_threshold: 10
```
**Średnia regulacja**:
```yaml
    kp: 0.3
    ki: 0.05
    k_ext: 0.1
    offset_max: 2
    stabilization_threshold: 0.1
    accumulated_error_threshold: 20
```
**Silna regulacja**:

Zestaw parametrów, który nie uwzględnia temperatury zewnętrznej i koncentruje się na _*błędzie*_ temperatury wewnętrznej + _*błędzie skumulowanym*_. Powinno to działać w przypadku niskich temperatur zewnętrznych, które generują wysoki offset zewnętrzny.

```yaml
    kp: 0.4
    ki: 0.08
    k_ext: 0.0
    offset_max: 5
    stabilization_threshold: 0.1
    accumulated_error_threshold: 50
```
Aby użyć _*trybu eksperckiego*_, musisz zadeklarować wartości, których chcesz użyć dla każdego z tych parametrów w pliku `configuration.yaml` w poniższy sposób.
Oto przykład dla 'Ekstremalnej regulacji':

```yaml
versatile_thermostat:
    auto_regulation_expert:
        kp: 0.6
        ki: 0.1
        k_ext: 0.0
        offset_max: 10
        stabilization_threshold: 0.1
        accumulated_error_threshold: 80
```
Oczywiście należy przestawić tryb samoregulacji termostatu _VTherm_ w _*tryb ekspercki*_. Wszystkie termostaty _VTherm_ w _*trybie eksperckim*_ będą używać **tych samych parametrów**. Nie jest możliwe korzystanie z różnych ustawień eksperckich dla różnych termostatów _VTherm_.

Aby zastosować zmiany, należy **całkowicie zrestartować Home Assistant** lub skorzystać tylko z integracji _*Versatile Thermostat*_ (`Narzędzia deweloperskie -> YAML -> Przeładuj konfigurację -> Versatile Thermostat`).

> ![Tip](images/tips.png) _*Notes*_
>
> 1. W _*trybie esperckim*_ rzadko pojawia się potrzeba użycia opcji [kompensacji temperatury wewnętrznej urządzenia](over-climate.md#compensate-the-internal-temperature-of-the-underlying). Nieprzemyślane jej użycie mogłoby prowadzić do ustawienia ekstremalnie wysokich wartości temperatury docelowej.

## Podsumowanie algorytmu samoregulacji

Algorytm samoregulacji został szczegółowo opisany [tutaj](algorithms.md#the-auto-regulation-algorithm-without-valve-control).
