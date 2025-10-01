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

### Konfigurieren der TPI-Algorithmusfaktoren

Wenn Sie einen Thermostat vom Typ `over_switch`, `over_valve` oder `over_climate` mit Selbstregulierung im Modus `Direkte Ventilsteuerung` ausgewählt haben und im Menü die Option "TPI" wählen, gelangen Sie auf diese Seite:

![image](images/config-tpi.png)

Folgendes muss angegeben werden:
1. der `coef_int`-Faktor des TPI-Algorithmus,
2. der `coef_ext`-Faktor des TPI-Algorithmus,
3. eine minimale aktivierungszeit in Sekunden,
4. eine minimale Deaktivierungszeit in Sekunden,
5. einen oberen Schwellenwert in °C (oder °K) für die Temperaturabweichung, bei dessen überschreiten der Algorithmus deaktiviert wird,,
6. einen unteren Schwellenwert in °C (oder °K) für die Temperaturabweichung, bei dessen Unterschreitung der Algorithmus wieder aktiviert wird.

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

Die erste Verzögerung (`minimal_activation_delay_sec`) in Sekunden ist die minimal zulässige Verzögerung zum Einschalten der Heizung.
Wenn die Berechnung zu einer Einschaltverzögerung führt, die kürzer als dieser Wert ist, bleibt die Heizung ausgeschaltet.
Wenn die Aktivierungszeit zu kurz ist, kann das Gerät aufgrund des schnellen Umschaltens nicht die Betriebstemperatur erreichen.

Gleichermaßen definiert die zweite Verzögerung (`minimal_deactivation_delay_sec`), ebenfalls in Sekunden, die minimal akzeptable Ausschaltzeit.
Ist die Ausschaltzeit kürzer als dieser Wert, wird die Heizung nicht ausgeschaltet.
Dadurch wird ein schnelles Flackern verhindert, das für die Temperaturregelung nur einen geringen Nutzen hat.

### Obere und untere Aktivierungsschwellen des Algorithmus

Seit Version 7.4 stehen zwei zusätzliche Schwellenwerte zur Verfügung.
Mit ihnen können Sie den TPI-Algorithmus selbst basierend auf der Differenz zwischen dem Sollwert und der aktuellen Temperatur deaktivieren (oder wieder aktivieren).

- Wenn die Temperatur steigt und die Differenz größer als der obere Schwellenwert ist, wird die Heizung ausgeschaltet (d. h. `on_percent` wird auf 0 gesetzt).
- Wenn die Temperatur sinkt und die Differenz kleiner als der untere Schwellenwert ist, wird die Heizung wieder eingeschaltet (d. h. `on_percent` wird durch den oben beschriebenen Algorithmus berechnet).

Diese beiden Schwellenwerte stoppen den Ein-/Aus-Zyklus, wenn die Temperatur den Sollwert überschreitet.
Eine Hysterese verhindert ein schnelles Umschalten.

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
1. Ist "Auto-Start/Stopp aktivieren" aus, dann stoppt es.
2. Wenn VTherm eingeschaltet und im Heizmodus ist, und wenn `error_accumulated` < `-error_threshold` -> ausschalten und HVAC-Modus speichern.
3. Wenn VTherm eingeschaltet und im Kühlmodus ist, und wenn `error_accumulated` > `error_threshold` -> ausschalten und HVAC-Modus speichern.
4. Wenn VTherm ausgeschaltet und der gespeicherte HVAC-Modus "Heizen" ist und `current_temperature + slope * dt <= target_temperature`, schaltet das Gerät ein und stellt den HVAC-Modus auf den gespeicherten Modus ein.
5. Wenn VTherm ausgeschaltet und der gespeicherte HVAC-Modus "Kühlen" ist und `current_temperature + slope * dt >= target_temperature`, schaltet das Gerät ein und stellt den HVAC-Modus auf den gespeicherten Modus ein.
6. `error_threshold` wird für langsame Erkennung auf `10 (° * min)`, für mittlere Erkennung auf `5` und für schnelle Erkennung auf `2` gesetzt.

`dt` wird für langsame Erkennung auf `30 min`, für mittlere Erkennung auf `15 min` und für schnelle Erkennung auf `7 min` gesetzt.

Details zur Function gibt es [hier](https://github.com/jmcollin78/versatile_thermostat/issues/585).