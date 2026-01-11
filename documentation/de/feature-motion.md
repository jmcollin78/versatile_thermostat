# Erkennung von Bewegung oder Aktivität

- [Erkennung von Bewegung oder Aktivität](#erkennung-von-bewegung-oder-aktivität)
  - [Aktivitätsmodus oder Bewegungserkennung konfigurieren](#aktivitätsmodus-oder-bewegungserkennung-konfigurieren)
  - [Anwendung](#Anwendung)

Mit dieser Funktion können Sie die Voreinstellungen ändern, wenn in einem Raum eine Bewegung erkannt wird. Wenn Sie Ihr Büro nicht heizen möchten, wenn der Raum unbesetzt ist, sondern nur, wenn der Raum besetzt ist, benötigen Sie einen Bewegungs- (oder Präsenz-) Sensor im Raum und konfigurieren diese Funktion.

Diese Funktion wird oft mit der Anwesenheitsfunktion verwechselt. Sie ergänzen sich, sind aber nicht austauschbar. Die `Bewegungs`-Funktion ist auf einen Raum beschränkt, der mit einem Bewegungsmelder ausgestattet ist, während die `Anwesenheits`-Funktion für die gesamte Wohnung gedacht ist.

## Aktivitätsmodus oder Bewegungserkennung konfigurieren

Wenn Sie die Funktion `Mit Bewegungserkennung` gewählt haben:

![image](images/config-motion.png)

Das brauchen wir::

| Parameter | Beschreibung | Attributname |
|-----------|-------------|--------------|
| **Bewegungsmelder** | Entitäts-ID eines Bewegungssensors. Der Zustand des Weg- und/oder Geschwindigkeitsgebers muss "ein" (Bewegung erkannt) oder "aus" (keine Bewegung erkannt) sein. | `motion_sensor_entity_id` |
| **Erkennungsverzögerung** | Verzögerung in Sekunden, die festlegt, wie lange wir auf die Bestätigung der Bewegung warten, bevor wir die Bewegung berücksichtigen. Dieser Parameter kann **größer sein als die Verzögerung Ihres Bewegungssensors**, andernfalls wird die Erkennung bei jeder vom Sensor erkannten Bewegung erfolgen. | `motion_delay_sec` |
| **Inaktivitätsverzögerung** | Verzögerung in Sekunden, die festlegt, wie lange wir auf die Bestätigung warten, dass kein Auftrag vorliegt, bevor wir den Auftrag nicht mehr berücksichtigen. | `motion_off_delay_sec` |
| **Voreinstellung "Bewegung"** | Wir verwenden die Temperatur dieser Voreinstellung, wenn eine Aktivität erkannt wird. | `motion_preset` |
| **Voreinstellung "keine Bewegung"** | Wir werden die Temperatur dieser zweiten Voreinstellung verwenden, wenn keine Aktivität erkannt wird. | `no_motion_preset` |

## Anwendung

Um einem _VTherm_ mitzuteilen, dass es auf den Bewegungsmelder hören soll, müssen Sie es auf die spezielle Voreinstellung 'Aktivität' einstellen. Wenn Sie die Versatile Thermostat UI-Karte installiert haben (siehe [hier](additions.md#much-better-with-the-versatile-thermostat-ui-card)), wird diese Voreinstellung wie folgt angezeigt: ![Aktivitätsvoreinstellung](images/activity-preset-icon.png).

Sie können dann auf Wunsch ein _VTherm_ in den Bewegungserkennungsmodus versetzen.

Das Verhalten wird wie folgt sein:
- Wir haben einen Raum mit einem Thermostat, der auf Aktivitätsmodus eingestellt ist, der gewählte "Bewegungs"-Modus ist Komfort (21,5°C), der gewählte "Keine Bewegung"-Modus ist Eco (18,5°C), und die Bewegungsverzögerung beträgt 30 Sekunden bei Erkennung und 5 Minuten bei Ende der Erkennung.
- Der Raum war eine Zeit lang leer (keine Aktivität festgestellt), die Solltemperatur in diesem Raum beträgt 18,5°C.
- Jemand betritt den Raum, und eine Aktivität wird erkannt, wenn die Bewegung mindestens 30 Sekunden lang anhält. Die Temperatur steigt dann auf 21,5°C an.
- Wenn die Bewegung weniger als 30 Sekunden anhält (schneller Durchgang), bleibt die Temperatur bei 18,5°C.
- Man stelle sich vor, dass die Temperatur auf 21,5° gestiegen ist und die Person den Raum verlässt, wird die Temperatur nach 5 Minuten wieder auf 18,5°C eingestellt.
- wenn die Person vor Ablauf der 5 Minuten zurückkehrt, bleibt die Temperatur bei 21,5°C.

> ![Tip](images/tips.png) _*Hinweise*_
> 1. Wie bei anderen Voreinstellungen wird auch `Aktivität` nur angeboten, wenn sie korrekt konfiguriert ist. Mit anderen Worten, alle 4 Konfigurationsschlüssel müssen gesetzt sein.
> 2. Wenn Sie die Versatile Thermostat UI-Karte verwenden (siehe [hier](additions.md#much-better-with-the-versatile-thermostat-ui-card)), wird die Bewegungserkennung wie folgt dargestellt: ![Bewegung](images/motion-detection-icon.png).