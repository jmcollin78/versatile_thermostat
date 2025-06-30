# `Thermostat_over_valve` Thermostattyp

> ![Vorsicht](images/tips.png) _*Hinweis*_
> 1. Der `over_valve`-Typ wird oft mit dem `over_climate`-Typ verwechselt, der mit automatischer Regelung und direkter Ventilsteuerung ausgestattet ist.
> 2. Sie sollten diesen Typ nur dann wählen, wenn Sie für Ihr _TRV_ im Home Assistant keine zugehörige `climate`-Entity haben und wenn Sie nur eine Entity vom Typ `number` haben, um den Öffnungsgrad des Ventils zu steuern. Der Typ `over_climate` mit automatischer Regulierung des Ventils ist viel leistungsfähiger als der Typ `over_valve`.

## Voraussetzungen

Die Installation sollte ähnlich wie bei der VTherm-Einrichtung `over_switch` sein, mit dem Unterschied, dass das gesteuerte Gerät direkt das Ventil eines _TRV_ ist:

![Installation `over_valve`](images/over-valve-schema.png)

1. Der Benutzer, die Automatisierung oder der Scheduler stellen einen Sollwert über eine Voreinstellung oder direkt über eine Temperatur ein.
2. Das Innenthermometer (2) oder das Außenthermometer (2b) oder das Gerätenthermometer (2c) sendet in regelmäßigen Abständen die gemessene Temperatur. Das Innenthermometer sollte an einer für den Komfort des Benutzers geeigneten Stelle angebracht werden: idealerweise in der Mitte des Wohnraums. Vermeiden Sie es, es zu nahe an einem Fenster oder in der Nähe des Geräts zu platzieren.
3. Ausgehend von den Sollwerten, den verschiedenen Temperaturen und den Parametern des TPI-Algorithmus (siehe [TPI](algorithms.md#lalgorithme-tpi)) berechnet VTherm den Öffnungsprozentsatz des Ventils.
4. Sie ändert dann den Wert der dazugehörigen `number`-Entities.
5. Diese dazugehörigen `number`-Entities steuern die Öffnungsrate des Ventils vom _TRV_.
6. Dadurch wird die Heizleistung des Heizkörpers reguliert.

> Die Öffnungsrate wird bei jedem Zyklus neu berechnet, was die Raumtemperaturregulierung ermöglicht.

## Konfiguration

Zuerst konfigurieren Sie die Haupteinstellungen, die für alle _VTherms_ gelten (siehe [Haupteinstellungen](base-attributes.md)).
Dann klicken Sie auf die Option „Zugehörige Entities“ aus dem Menü, dann sehen Sie diese Konfigurationsseite, Sie sollten die `number`-Entities hinzufügen, die von VTherm kontrolliert werden. Es werden nur `number` oder `input_number` Entitäten akzeptiert.

![image](images/config-linked-entity3.png)

Der derzeit verfügbare Algorithmus ist TPI. Siehe [Algorithmus](#algorithm).

Es ist möglich, einen `Thermostat_over_valve` zur Steuerung einer Klimaanlage zu wählen, indem man das Kästchen "AC Mode" aktiviert. In diesem Fall wird nur der Kühlmodus angezeigt.