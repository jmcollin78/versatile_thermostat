# Tuning-Beispiele

- [Tuning-Beispiele](#tuning-beispiele)
  - [Elektroheizung](#elektroheizung)
  - [Zentralheizung (Gas- oder Öl-Heizung)](#zentralheizung-gas-oder-öl-heizung)
  - [Batteriebetriebene Temperaturfühler](#batteriebetriebene-temperaturfühler)
  - [Reaktiver Temperatursensor (angeschlossen)](#reaktiver-temperatursensor-angeschlossen)
  - [Meine Voreinstellungen](#meine-voreinstellungen)

## Elektroheizung
- Zyklus: zwischen 5 und 10 Minuten,
- minimale_Aktivierungsverzögerung_sec: 30 Sekunden

## Zentralheizung (Gas- oder Öl-Heizung)
- Zyklus: zwischen 30 und 60 Minuten,
- minimale_Aktivierungsverzögerung_sec: 300 Sekunden (aufgrund der Reaktionszeit)

## Batteriebetriebene Temperaturfühler
Diese Sensoren sind oft träge und senden nicht immer Temperaturmesswerte, wenn die Temperatur stabil ist. Daher sollten die Einstellungen locker sein, um falsch positive Ergebnisse zu vermeiden.

- safety_delay_min: 60 Minuten (weil diese Sensoren träge sind)
- safety_min_on_percent: 0.7 (70% - das System geht in den Sicherheitsmodus, wenn die Heizung mehr als 70% der Zeit eingeschaltet war)
- safety_default_on_percent: 0.4 (40% - im Sicherheitsmodus wird eine Heizzeit von 40% beibehalten, um zu vermeiden, dass es zu kalt wird)

Diese Einstellungen sind wie folgt zu verstehen:

> Wenn das Thermometer 1 Stunde lang keine Temperaturmesswerte mehr sendet und der Heizprozentsatz (``on_percent``) größer als 70% war, dann wird der Heizprozentsatz auf 40% reduziert.

Sie können diese Einstellungen gerne an Ihren speziellen Fall anpassen!

Wichtig ist, dass Sie mit diesen Parametern nicht zu viel riskieren: Angenommen, Sie sind längere Zeit abwesend und die Batterien Ihres Thermometers sind leer, dann wird Ihr Heizgerät während der gesamten Ausfallzeit 40 % der Zeit laufen.

Mit Versatile Thermostat können Sie benachrichtigt werden, wenn ein solches Ereignis eintritt. Richten Sie die entsprechenden Benachrichtigungen ein, sobald Sie dieses Thermostat in Betrieb nehmen. Siehe (#Benachrichtigungen).

## Reaktiver Temperatursensor (angeschlossen)
Ein strombetriebenes Thermometer sollte sehr regelmäßig Temperaturmesswerte senden. Wenn es 15 Minuten lang nichts sendet, hat es höchstwahrscheinlich ein Problem, und wir können schneller reagieren, ohne das Risiko eines falschen Positivs.

- sicherheitsverzögerung_min: 15 Minuten
- safety_min_on_percent: 0.5 (50% - das System geht in die ``Sicherheit``-Voreinstellung, wenn die Heizung mehr als 50% der Zeit eingeschaltet war)
- safety_default_on_percent: 0.25 (25% - in der Voreinstellung ``Sicherheit`` werden 25% Heizzeit beibehalten)

## Meine Voreinstellungen
Dies ist nur ein Beispiel dafür, wie ich die Voreinstellung verwende. Sie können es an Ihre Konfiguration anpassen, aber es kann nützlich sein, um seine Funktionalität zu verstehen.

``Frostschutz``: 10°C
``Eco``: 17°C
``Komfort``: 19°C
``Boost``: 20°C

Bei deaktivierter Anwesenheit:
``Frostschutz``: 10°C
``Eco``: 16.5°C
``Komfort``: 17°C
``Boost``: 17.5°C

Der Bewegungsmelder in meinem Büro ist so konfiguriert, daß er ``Boost`` verwendet, wenn eine Bewegung erkannt wird, und ``Eco``, wenn nicht.

Der Sicherheitsmodus wird wie folgt konfiguriert:

![Meine Voreinstellungen](images/my-tuning.png)