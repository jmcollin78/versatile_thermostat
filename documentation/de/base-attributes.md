- [Auswahl der grundlegenden Attribute](#auswahl-der-grundlegenden-attribute)
- [Auswahl der zu verwendenden Eigenschaften](#auswahl-der-zu-verwendenden-eigenschaften)

# Auswahl der grundlegenden Attribute

Wählen Sie das Menü "Hauptmerkmale".

![image](images/config-main.png)

| Attribut | Beschreibung | Attributname |
| --------- | ------------ | ------------ |
| **Name** | Name der Entity (dies wird der Name der Integration und der `climate`-Entity sein). | |
| **Temperatursensor** | Entity-ID des Sensors, der die Raumtemperatur liefert, wo das Gerät installiert ist. | |
| **Zuletzt aktualisierter Sensor (optional)** | Verhindert Sicherheitsabschaltungen, wenn Temperatur stabil und Sensor nicht mehr meldet. (siehe [troubleshooting](troubleshooting.md#why-does-my-versatile-thermostat-go-into-safety-mode)) | |
| **Zyklusdauer** | Dauer in Minuten zwischen jeder Berechnung. Für `over_switch`: moduliert Ein/Aus-Zeit. Für `over_valve`: berechnet Ventilöffnung. Für `over_climate`: führt Kontrollen durch und berechnet Selbstregulierungskoeffizienten neu. Bei den Typen `over_switch` und `over_valve` werden die Berechnungen bei jedem Zyklus durchgeführt. Wenn sich die Bedingungen ändern, werden diese erst im nächsten Zyklus sichtbar. Daher sollte der Zyklus nicht zu lang sein. 5 Minuten sind ein guter Wert, der jedoch an Ihren Heizungstyp angepasst werden sollte. Je größer die Trägheit ist, desto länger sollte der Zyklus sein. Siehe [Tuning-Beispiele](tuning-examples.md). Ist der Zyklus zu kurz, erreicht der Heizkörper möglicherweise nie die Zieltemperatur. Bei einer Speicherheizung beispielsweise wird sie unnötigerweise aktiviert. | `cycle_min` |
| **Geräteleistung** | Aktiviert Leistungs-/Energiesensoren. Gesamt angeben, wenn mehrere Geräte (gleiche Einheit wie andere VTherms und Sensoren). (siehe: Lastabwurf-Funktion) | `device_power` |
| **Zentralisierte zusätzliche Parameter** | Verwendet Außentemperatur, Min/Max/Schritt-Temperatur aus zentraler Konfiguration. | |
| **Zentralisierte Steuerung** | Ermöglicht zentralisierte Thermostatsteuerung. Siehe [centralized control](#centralized-control) | `is_controlled_by_central_mode` |
| **Zentraler Heizkessel-Trigger** | Aktivierungsfeld, um dieses VTherm als Trigger für zentralen Heizkessel zu verwenden. | `is_used_by_central_boiler` |

# Auswahl der zu verwendenden Eigenschaften

Wählen Sie das Menü "Eigenschaften".
![image](images/config-features.png)

| Eigenschaft | Beschreibung | Attributname |
| ------------ | ------------ | ------------ |
| **Mit Öffnungserkennung** | Stoppt Heizung bei Öffnung von Türen/Fenstern. (siehe [Öffnungsmanagement](feature-window.md)) | `is_window_configured` |
| **Mit Bewegungserkennung** | Passt Solltemperatur bei Bewegungserkennung im Raum an. (siehe [Bewegungserkennung](feature-motion.md)) | `is_motion_configured` |
| **Mit Energieverwaltung** | Stoppt Gerät bei Überschreitung des Stromverbrauchsschwellenwerts. (siehe [Energieverwaltung](feature-power.md)) | `is_power_configured` |
| **Mit Anwesenheitserkennung** | Ändert Solltemperatur basierend auf Anwesenheit/Abwesenheit. Unterscheidet sich von Bewegungserkennung (Wohnung vs Raum). (siehe [Anwesenheitserkennung](feature-presence.md)) | `is_presence_configured` |
| **Mit automatischem Start/Stopp** | Nur für `over_climate`: stoppt/startet Gerät basierend auf Temperaturkurvenvorhersage. (siehe [Start/Stopp-Automatik](feature-auto-start-stop.md)) | `is_window_auto_configured` |

> ![Tip](images/tips.png) _*Hinweise*_
> 1. Die Liste der verfügbaren Eigenschaften passt sich an Ihren VTherm-Typ an.
> 2. Wenn eine Eigenschaften aktiviert wurde, wird ein neuer Menüeintrag hinzugefügt, mit dem diese eigenschaft konfiguriert weird.
> 3. Sie können die Erstellung eines VTherms nicht abschließen, wenn nicht alle Parameter für alle aktivierten Funktionen konfiguriert wurden.
