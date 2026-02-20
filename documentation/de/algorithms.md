# Die verschiedenen benutzten Algorithmen

- [Die verschiedenen benutzten Algorithmen](#die-verschiedenen-benutzten-algorithmen)
  - [Der TPI-Algorithmus](#der-tpi-algorithmus)
    - [Konfigurieren der TPI-Algorithmusfaktoren](#konfigurieren-der-tpi-algorithmusfaktoren)
    - [Prinzip](#prinzip)
    - [Mindestverzögerung bei Aktivierung oder Deaktivierung](#mindestverzögerung-bei-aktivierung-oder-deaktivierung)
    - [Obere und untere Aktivierungsschwellen des Algorithmus](#obere-und-untere-aktivierungsschwellen-des-algorithmus)
  - [Der Selbstregulierungsalgorithmus (ohne Ventilsteuerung)](#der-selbstregulierungsalgorithmus-ohne-ventilsteuerung)
  - [Der Algorithmus der Auto-Start/Stopp-Funktion](#der-algorithmus-der-auto-startstopp-funktion)

## Der TPI-Algorithmus

TPI ist nur für _VTherm_ anwendbar, welche die Regelung selbst durchführen. Dies betrifft folgende _VTherm_-Typen:
1. `over_switch`,
2. `over_valve`,
3. `over_climate` mit direkter Ventilsteuerung.

`over_climate` mit Selbstregulierung, die das Ventil nicht direkt steuern, haben keinen TPI-Algorithmus integriert; daher ist dieses Kapitel für sie nicht anwendbar.

### Konfigurieren der TPI-Algorithmusfaktoren

Wenn das _Vtherm_ über ein TPI verfügt und im Menü die Option "TPI" ausgewählt wird, gelangt man auf diese Seite:

![image](images/config-tpi.png)

### Konfigurationseinstellungen

| Parameter | Beschreibung | Attributname |
|-----------|--------------|--------------|
| **Interner Koeffizient** | Der `coef_int`-Faktor des TPI-Algorithmus. | `tpi_coef_int` |
| **Externer Koeffizient** | Der `coef_ext`-Faktor des TPI-Algorithmus. | `tpi_coef_ext` |
| **Aktivierungsverzögerung** | Minimale Aktivierungszeit in Sekunden. | `minimal_activation_delay` |
| **Deaktivierungsverzögerung** | Minimale Deaktivierungszeit in Sekunden. | `minimal_deactivation_delay` |
| **Hoher Schwellenwert** | Temperaturabweichung (°C oder K), bei deren Überschreitung der Algorithmus deaktiviert wird. | `tpi_threshold_high` |
| **Niedriger Schwellenwert** | Temperaturabweichung (°C oder K), bei deren Unterschreitung der Algorithmus wieder aktiviert wird. | `tpi_threshold_low` |


### Prinzip

Der TPI-Algorithmus berechnet den Prozentsatz für Ein- und Ausschalten des Heizkörpers in jedem Zyklus anhand der Zieltemperatur, der aktuellen Raumtemperatur und der aktuellen Außentemperatur. Dieser Algorithmus ist nur für Versatile Thermostate anwendbar, die im Modus `over_switch` und `over_valve` betrieben werden.

Der Prozentsatz wird anhand dieser Formel berechnet:

    on_percent = coef_int * (ziel_temperatur - aktuelle_temperatur) + coef_ext * (ziel_temperatur - aussen_temperature)
    Danach stellt der Algorithmus sicher, dass 0 <= on_percent <= 1 gilt.

Die Standardwerte für `coef_int` und `coef_ext` sind `0,6` bzw. `0,01`. Diese Standardwerte eignen sich für einen gedämmten Durchschnittsraum.

Beachten Sie folgendes bei der Anpassung der Faktoren:
1. **Wenn die Zieltemperatur nach der Stabilisierung nicht erreicht wird**, erhöhen Sie `coef_ext` (der Wert für `on_percent` ist zu niedrig).
2. **Wenn die Zieltemperatur nach der Stabilisierung überschritten wird**, verringern Sie `coef_ext` (der Wert für `on_percent` ist zu hoch).
3. **Wenn das Erreichen der Zieltemperatur zu langsam ist**, erhöhen Sie `coef_int`, um dem Heizelement mehr Leistung zuzuführen.
4. **Wenn das Erreichen der Zieltemperatur zu schnell ist und Schwankungen** um den Zielwert auftreten, verringern Sie `coef_int`, um dem Heizelement weniger Leistung zuzuführen.

Im Modus `over_valve` wird der Wert `on_percent` in einen Prozentsatz (0 bis 100 %) umgewandelt und steuert direkt den Öffnungsgrad des Ventils.

### Mindestverzögerung bei Aktivierung oder Deaktivierung

Die erste Verzögerung (`minimal_activation_delay_sec`) in Sekunden ist die minimal zulässige Verzögerung zum Einschalten der Heizung. Wenn die Berechnung eine Einschaltverzögerung ergibt, die unter diesem Wert liegt, bleibt die Heizung ausgeschaltet. Wenn die Einschaltzeit zu kurz ist, kann das Gerät aufgrund des schnellen Umschaltens nicht auf Temperatur kommen.

Das Gleiche gilt für zweite Verzögerung (`minimal_deactivation_delay_sec`), ebenfalls in Sekunden, hier jedoch für die Ausschaltdauer. Ist die Ausschaltzeit kürzer als dieser Wert, wird die Heizung nicht ausgeschaltet. Dadurch wird ein schnelles Flackern verhindert, das für die Temperaturregelung nur einen geringen Nutzen hat.

### Obere und untere Aktivierungsschwellwerte des Algorithmus

Seit Version 7.4 stehen zwei zusätzliche Schwellenwerte zur Verfügung. Mit ihnen kann der TPI-Algorithmus selbst je nach Abweichung zwischen Sollwert und aktuellen Temperatur ausgeschalter (bzw. eingeschaltet) werden.

Wenn die Temperatur steigt und die Abweichung größer als der obere Schwellenwert ist, wird die Heizung ausgeschaltet (d. h. `on_percent` wird auf 0 gesetzt).
Wenn die Temperatur sinkt und die Abweichung unter dem unteren Schwellenwert liegt, wird die Heizung wieder eingeschaltet (d. h. `on_percent` wird durch den oben beschriebenen Algorithmus berechnet).

Mit diese beiden Schwellenwerte kann der Ein-/Ausschaltzyklus unterbrochen werden, sobald die Temperatur den Sollwert überschreitet. Eine Hysterese verhindert ein schnelles Umschalten.

Beispiele:
1. Angenommen, der Sollwert beträgt 20 °C, der obere Schwellenwert 2 °C und der untere Schwellenwert 1 °C.
2. Wenn die Temperatur über 22 °C (Sollwert + oberer Schwellenwert) steigt, wird „on_percent“ auf 0 gesetzt.
3. Wenn die Temperatur unter 21 °C (Sollwert + unterer Schwellenwert) fällt, wird „on_percent“ neu berechnet.

> ![Tip](images/tips.png) _*Notes*_
> 1. Lassen Sie beide Werte auf 0, wenn Sie keine Schwellenwerte verwenden möchten. Dadurch wird das Verhalten vor Version 7.4 wiederhergestellt.
> 2. Beide Werte sind erforderlich. Wenn Sie einen Wert auf 0 belassen, wird kein Schwellenwert angewendet. Tatsächlich sind beide für einen korrekten Betrieb erforderlich.
> 3. Im Kühlmodus werden die Tests umgekehrt, aber das Prinzip bleibt dasselbe.
> 4. Der obere Schwellenwert sollte immer größer als der untere Schwellenwert sein, auch im Kühlmodus.

## Der Selbstregulierungsalgorithmus (ohne Ventilsteuerung)

Der Selbstregulierungsalgorithmus lässt sich wie folgt zusammenfassen:

1. Definiere die Zieltemperatur als VTherm-Sollwert.
2. Wenn die Selbstregelung aktiviert ist:
   1. Berechne die geregelte Temperatur (gültig für einen VTherm).
   2. Verwende diese Temperatur als Zielwert.
3. Für jedes zugeordnete Gerät des VTherm:
     1. Wenn "Interne Temperatur verwenden" aktiviert ist:
          1. Berechne die Kompensation (`trv_internal_temp - room_temp`).
     2. Addiere den Offset zur Zieltemperatur.
     3. Sende die Zieltemperatur (= regulated_temp + (internal_temp - room_temp)) an das zugeordnete Gerät.

## Der Algorithmus der Auto-Start/Stopp-Funktion

Der in der Auto-Start/Stopp-Funktion verwendete Algorithmus funktioniert wie folgt:
1. Wenn `Auto-Start/Stopp` nicht aktiviert ist, dann wird es abgeschaltet.
2. Wenn `VTherm` eingeschaltet ist und sich im Modus `Heizen` befindet, gilt: Wenn `error_accumulated` < `-error_threshold` -> ausschalten und `HVAC`-Modus speichern.
3. Wenn `VTherm` eingeschaltet und der Modu `Kühlen` aktiv ist, gilt: Eenn `error_accumulated` > `error_threshold` -> ausschalten und `HVAC`-Modus speichern.
4. Wenn `VTherm` ausgeschaltet ist und der gespeicherte `HVAC`-Modus `Heizen` ist, sowie `current_temperature + slope * dt <= target_temperature`, dann schaltet das Gerät ein und stellt `HVAC` auf den gespeicherten Modus ein.
5. Wenn `VTherm` ausgeschaltet und der gespeicherte `HVAC`-Modus "Kühlen" ist, sowie `current_temperature + slope * dt >= target_temperature`, schaltet das Gerät ein und stellt `HVAC` auf den gespeicherten Modus ein.

`error_threshold` ist im langsamen Modus auf `10 (° * min)`, im mittleren Modus auf `5` und im schnellen Modus auf `2` festgelegt.

`dt` wird für langsame Erkennung auf `30 min`, für mittlere Erkennung auf `15 min` und für schnelle Erkennung auf `7 min` gesetzt.

Details zur Function gibt es [hier](https://github.com/jmcollin78/versatile_thermostat/issues/585).