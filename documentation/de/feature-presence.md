# Anwesenheits-/Abwesenheitsverwaltung

- [Anwesenheits-/Abwesenheitsverwaltung](#anwesenheits-abwesenheitsverwaltung)
  - [Anwesenheit (oder Abwesenheit) konfigurieren](#anwesenheit-oder-abwesenheit-konfigurieren)

## Anwesenheit (oder Abwesenheit) konfigurieren

Wenn diese Funktion ausgewählt ist, können Sie die voreingestellten Temperaturen des Thermostats dynamisch anpassen, wenn eine Anwesenheit (oder Abwesenheit) festgestellt wird. Dazu müssen Sie die Temperatur konfigurieren, die für jede Voreinstellung verwendet werden soll, wenn die Anwesenheit aufgehoben ist. Wenn der Anwesenheitssensor abschaltet, werden diese Temperaturen angewendet. Wenn er sich wieder einschaltet, wird die für die Voreinstellung konfigurierte "normale" Temperatur verwendet. Siehe [Anwesenheitsverwaltung](feature-presets.md).

Um die Präsenz zu konfigurieren, füllen Sie dieses Formular aus:

![image](images/config-presence.png)

Dazu müssen Sie lediglich einen **Anwesenheitssensor** konfigurieren, dessen Zustand `ein` oder `zu Hause` sein muss, wenn jemand anwesend ist, oder andernfalls `aus` oder `nicht zu Hause`.

Die Temperaturen werden in den Entities des Gerätes konfiguriert, das Ihrem _VTherm_ entspricht (Einstellungen/Integration/Versatile Thermostat/das VTherm).

ACHTUNG: Personengruppen funktionieren nicht als Anwesenheitssensor. Sie werden nicht als Anwesenheitssensor erkannt. Sie müssen eine Vorlage verwenden, wie sie hier beschrieben ist [Verwendung einer Personengruppe als Anwesenheitssensor](troubleshooting.md#using-a-people-group-as-a-presence-sensor).

> ![Tip](images/tips.png) _*Hinweise*_
>
> 1. Die Temperaturänderung erfolgt sofort und wird auf dem Bedienfeld angezeigt. Die Berechnung berücksichtigt die neue Solltemperatur bei der nächsten Zyklusberechnung.
> 2. Sie können den direkten Person.xxxx-Sensor oder eine Home Assistant-Sensorgruppe verwenden. Der Anwesenheitssensor behandelt die Zustände `ein` oder `zu hause` als anwesend und `aus` oder `nicht zuhause` als abwesend.
> 3. Um Ihr Haus vorzuheizen, wenn alle abwesend sind, können Sie Ihrer Personengruppe eine `input_boolean` Entity hinzufügen. Wenn Sie diese `input_boolean` auf `Ein` setzen, wird der Anwesenheitssensor auf `Ein` gesetzt und die Voreinstellungen mit Anwesenheit werden verwendet. Sie können diesen `input_boolean` auch über eine Automation auf `Ein` setzen, z.B. wenn Sie eine Zone verlassen, um Ihr Haus vorzuheizen.