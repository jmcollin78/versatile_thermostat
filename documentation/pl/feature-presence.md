# Zarządzanie obecnością / nieobecnością
- [Zarządzanie obecnością / nieobecnością](#presence--absence-management)
  - [Konfiguracja obecności / nieobecności](#configure-presence-or-absence)

## Konfiguracja obecności / nieobecności

Funkcja ta umożliwia dynamiczne dostosowanie ustawionych temperatur termostatu w zależności od wykrycia obecności (lub nieobecności). W tym celu należy skonfigurować temperaturę, która będzie używana dla każdego presetu, dla którego obecność będzie nieaktywna. Gdy czujnik obecności się wyłączy, temperatura ta będzie temperaturą docelową. Gdy ponownie się włączy, zostanie użyta „normalna” temperatura skonfigurowana dla tego presetu. Zobacz: [zarządzanie presetami](feature-presets.md).

Aby skonfigurować obecność, podaj poniższe dane:

![image](images/config-presence.png)

Do tego potrzebujesz jedynie skonfigurować czujnik obecności, którego stan musi być `on` lub `home`, jeśli ktoś jest obecny, albo `off` lub `not_home` w przeciwnym przypadku.

Temperatury są konfigurowane w encjach termostatu _VTherm_.

UWAGA: Grupy osób nie działają jako czujnik obecności. Nie są rozpoznawane jako czujnik obecności. Należy użyć szablonu opisanego [tutaj](troubleshooting.md#using-a-people-group-as-a-presence-sensor).

> ![Tip](images/tips.png) _*Wskazówki*_
>
> 1. Zmiana temperatury jest natychmiastowa i widoczna na panelu. Obliczenia uwzględnią nową temperaturę docelową przy następnym cyklu obliczeniowym.
> 2. Możesz użyć bezpośredniego czujnika `person.xxxx` lub grupy czujników Home Assistant. Czujnik obecności interpretuje stany `on` lub `home` jako obecność oraz `off` lub `not_home` jako nieobecność.
> 3. Aby ogrzać dom, gdy wszyscy są nieobecni, możesz dodać encję `input_boolean` do swojej grupy osób. Jeśli ustawisz tę encję `input_boolean` na `on` lub `true`, stan obecności zostanie wymuszony i zostaną użyte presety zdefiniowane dla stanu obecności. Możesz także ustawić tę encję `input_boolean` na `on` lub `true` za pomocą automatyzacji, na przykład gdy ktoś opuszcza jakąś strefę lub pojawia się w niej.

