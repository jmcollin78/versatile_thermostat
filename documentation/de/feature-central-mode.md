# Zentralisierte Steuerung

- [Zentralisierte Steuerung](#Zentralisierte Steuerung)
  - [Konfiguration der zentralisierten Steuerung](#Konfiguration-der-zentralisierten-steuerung)
  - [Anwendung](#anwendung)

Mit dieser Funktion können Sie alle Ihre _VTherms_ von einem einzigen Kontrollpunkt aus steuern.
Ein typischer Anwendungsfall ist, wenn Sie für längere Zeit verreisen und alle Ihre _VTherms_ auf Frostschutz stellen wollen, und wenn Sie zurückkommen, wollen Sie sie wieder in den Ausgangszustand versetzen.

Die zentrale Steuerung erfolgt über ein spezielles _VTherm_, die sogenannte zentralisierte Konfiguration. Siehe [hier](creation.md#centralized-configuration) für weitere Informationen.

## Konfiguration der zentralisierten Steuerung

Wenn Sie eine zentralisierte Konfiguration eingerichtet haben, verfügen Sie über eine neue Entität namens `select.central_mode`, die es Ihnen ermöglicht, alle _VTherms_ mit einer einzigen Aktion zu steuern.

![Zentralisierte Steuerung](images/central-mode.png)

Diese Entität erscheint als eine Liste von Auswahlmöglichkeiten, die die folgenden Optionen enthält:
1. `Auto`: der 'normale' Modus, in dem jedes _VTherm_ autonom arbeitet,
2. `Gestoppt`: alle _VTherms_ sind ausgeschaltet (`hvac_off`),
3. `Nur Heizen`: alle _VTherms_ werden in den Heizmodus versetzt, wenn dies unterstützt wird, andernfalls werden sie angehalten,
4. `Nur Kühlen`: alle _VTherms_ werden in den Kühlmodus versetzt, wenn dies unterstüzt wird, andernfalls werden sie angehalten,
5. `Frostschutz`: alle _VTherms_ werden in den Frostschutzmodus versetzt, wenn dies unterstüzt wird, andernfalls werden sie angehalten.

## Anwendung

Damit ein _VTherm_ zentral gesteuert werden kann, muss sein Konfigurationsattribut mit dem Namen `use_central_mode` true sein. Dieses Attribut ist auf der Konfigurationsseite `Hauptattribute` verfügbar.

![Zentralmodus](images/use-central-mode.png)

Das bedeutet, dass Sie alle _VTherms_ (die explizit genannten) mit einem einzigen Steuerelement steuern können.
