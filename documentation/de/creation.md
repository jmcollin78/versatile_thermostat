# Wahl eines VTherm

- [Wahl eines VTherm](#wahl-eines-vtherm)
  - [Erstellen eines neuen Versatile Thermostats](#erstellen-eines-neuen-versatile-thermostats)
  - [Auswahl eines VTherm-Typs](#auswahl-eines-vtherm-typs)
    - [Zentrale Konfiguration](#zentrale-konfiguration)
    - [VTherm über einen Schalter](#vtherm-über-einen-schalter)
    - [VTherm über anderes Thermostat](#vtherm-über-anderes-thermostat)
    - [VTherm über Ventil](#vtherm-über-ventil)
  - [Wähle das Richtige aus](#wähle-das-richtige-aus)
  - [Referenzartikel](#referenzartikel)
  - [Nächster Schritt](#nächster-schritt)

> ![Tip](images/tips.png) _*Hinweise*_
>
> Es gibt drei Möglichkeiten, mit VTherms zu arbeiten:
> 1. Jedes Versatile Thermostat wird völlig unabhängig konfiguriert. Wählen Sie diese Option, wenn Sie keine zentralisierte Konfiguration oder Verwaltung wünschen.
> 2. Einige Aspekte werden zentral konfiguriert. So können Sie beispielsweise die Mindest-/Höchsttemperaturen, die Parameter für die Erkennung offener Fenster usw. in einer einzigen zentralen Instanz festlegen. Für jedes VTherm, das Sie konfigurieren, können Sie dann wählen, ob Sie die zentrale Konfiguration verwenden oder sie mit benutzerdefinierten Parametern überschreiben möchten.
> 3. Zusätzlich zur zentralen Konfiguration können alle VTherms über eine einzige `select`-Entity mit dem Namen `central_mode` gesteuert werden. Diese Funktion ermöglicht es Ihnen, alle VTherms gleichzeitig zu stoppen/starten/einen Frostschutz einzustellen usw.. Für jedes VTherm können Sie angeben, ob es diesem `central_mode` zugeordnet  ist.

## Erstellen eines neuen Versatile Thermostats

Klicken Sie auf "Integration hinzufügen" auf der Integrationsseite (oder klicken Sie auf 'Gerät hinzufügen' auf der Integrationsseite)

![image](images/add-an-integration.png)

dann nach "versatile thermostat"-Integration suchen:

![image](images/choose-integration.png)

und wählen Sie Ihren Thermostattyp:

![image](images/config-main0.png)

Die Konfiguration kann über die gleiche Schnittstelle geändert werden. Wählen Sie einfach den zu ändernden Thermostat aus, drücken Sie auf "Konfigurieren", und Sie können einige Parameter oder Einstellungen ändern.

Folgen Sie den Konfigurationsschritten, indem Sie die zu konfigurierende Menüoption auswählen.

> ![Tip](images/tips.png) _*Zentrale Konfiguration*_
> Die meisten Konfigurationsseiten (wichtigste Eigenschaften, TPI-Parameter, Temperaturvoreinstellungen, erweiterte Einstellungen...) haben ein Kästchen „Zentrale Konfiguration verwenden“: Ist es aktiviert, stammen diese Einstellungen aus dem _VTherm_ vom Typ „Zentrale Konfiguration“. Existiert eine zentrale Konfiguration, sind diese Kästchen standardmäßig aktiviert. Andernfalls sind sie deaktiviert, die Einstellungen werden in jedem _VTherm_ eingegeben, und das Aktivieren eines dieser Kästchen führt beim Speichern der Seite zu einem Fehler. Um Einstellungen zwischen mehreren _VTherm_ zu teilen, erstellen Sie zuerst die zentrale Konfiguration: Sie ist eindeutig und wird in der Typenliste angeboten, solange sie nicht existiert.

## Auswahl eines VTherm-Typs

### Zentrale Konfiguration
Mit dieser Option können Sie bestimmte sich wiederholende Aspekte für alle VTherms auf einmal konfigurieren, z. B:
1. Parameter für verschiedene Algorithmen (TPI, Erkennung offener Fenster, Bewegungserkennung, Stromsensoren für Ihr Haus, Präsenzerkennung). Diese Parameter gelten für alle VTherms. Sie müssen sie nur einmal in der „Zentralen Konfiguration“ eingeben. Mit dieser Konfiguration wird kein VTherm selbst erstellt, sondern es werden Parameter zentralisiert, die mühsam für jedes VTherm neu eingegeben werden müssten. Beachten Sie, dass Sie diese Parameter für einzelne VTherms außer Kraft setzen können, um sie bei Bedarf anzupassen.
2. Konfiguration zur Steuerung einer Zentralheizungsanlage,
3. Bestimmte erweiterte Parameter, wie z. B. Sicherheitseinstellungen.

### VTherm über einen Schalter
Dieser VTherm-Typ steuert einen Schalter, der einen Heizkörper ein- oder ausschaltet. Bei dem Schalter kann es sich um einen physischen Schalter handeln, der einen Heizkörper direkt steuert (häufig elektrisch), oder um einen virtuellen Schalter, der beim Ein- oder Ausschalten eine beliebige Aktion ausführen kann. Der letztere Typ kann zum Beispiel Pilotdrahtschalter oder DIY-Lösungen mit Dioden steuern. VTherm moduliert den Anteil der Zeit, in der der Heizkörper eingeschaltet ist (`on_percent`), um die gewünschte Temperatur zu erreichen. Wenn es kalt ist, schaltet er sich häufiger ein (bis zu 100 %); wenn es warm ist, wird die Einschaltzeit reduziert.

Die zugrundeliegenden Entitäten für diesen Typ sind `switches` oder `input_booleans`.

### VTherm über anderes Thermostat
Wenn Ihr Gerät durch eine `climate`-Entity in Home Assistant gesteuert wird und Sie nur Zugriff auf diese haben, sollten Sie diesen VTherm-Typ verwenden. In diesem Fall passt VTherm einfach die Zieltemperatur der zugrunde liegenden `climate`-Entity an.

Dieser Typ verfügt auch über fortschrittliche Selbstregulierungsfunktionen zur Anpassung des an das zugrundeliegende Gerät gesendeten Sollwerts, was dazu beiträgt, die Zieltemperatur schneller zu erreichen und eine schlechte interne Regelung abzumildern. Befindet sich beispielsweise das interne Thermometer des Geräts zu nahe am Heizelement, kann es fälschlicherweise annehmen, dass der Raum warm ist, während der Sollwert in anderen Bereichen bei weitem nicht erreicht wird.

Seit Version 6.8 kann dieser VTherm-Typ auch direkt über die Steuerung des Ventils geregelt werden. Ideal für steuerbare TRVs, wie Sonoff TRVZB, wird dieser Typ empfohlen, wenn Sie solche Geräte haben.

Die diesem VTherm-Typ zugrunde liegenden Einheiten sind ausschließlich `climate`.

### VTherm über Ventil
Wenn die einzige Entität, die zur Regelung der Temperatur Ihres Heizkörpers zur Verfügung steht, eine Entität des Typs `number` ist, sollten Sie den Typ `over_valve` verwenden. VTherm passt die Ventilöffnung auf der Grundlage der Differenz zwischen der Zieltemperatur und der tatsächlichen Raumtemperatur (und der Außentemperatur, falls verfügbar) an.

Dieser Typ kann für TRVs ohne eine zugehörige `climate`-Entity oder andere DIY-Lösungen verwendet werden, die eine `number`-Entity aufweisen.

## Wähle das Richtige aus

Der Typ kann nach der Erstellung des _VTherm_ nicht mehr geändert werden: Wählen Sie ihn nach dem gesteuerten Gerät und danach, wie es in Home Assistant erscheint.

| Gerät | Entity in Home Assistant | _VTherm_-Typ | Regelung |
|---|---|---|---|
| Thermostatventil (TRV) mit steuerbarer Ventilöffnung | `climate` und `number` für die Öffnung | [`over_climate`](over-climate.md) mit [direkter Ventilsteuerung](self-regulation.md#selbstregulierung-bei-direkter-ventilkontrolle) | durch _VTherm_: TPI oder Plugin-Algorithmus (SmartPI...) |
| Ventil allein, ohne `climate`-Entity | `number`, `input_number` | [`over_valve`](over-valve.md) | durch _VTherm_: TPI oder Plugin-Algorithmus |
| Einfaches TRV | `climate` | [`over_climate`](over-climate.md) | durch das Ventil, bei Bedarf korrigiert durch die [Selbstregulierung](self-regulation.md) |
| Wärmepumpe, Klimaanlage, HLK-System | `climate` | [`over_climate`](over-climate.md) | durch das Gerät, bei Bedarf korrigiert durch die [Selbstregulierung](self-regulation.md) |
| Elektrischer Heizkörper mit Schalter | `switch`, `input_boolean` | [`over_switch`](over-switch.md) | durch _VTherm_: TPI oder Plugin-Algorithmus |
| Elektrischer Heizkörper mit Steuerleitung (Fil Pilote) | `select`, `input_select` oder `climate`, mit [angepassten Befehlen](over-switch.md#befehlsanpassung) | [`over_switch`](over-switch.md) | durch _VTherm_: TPI oder Plugin-Algorithmus |
| Pelletofen | `switch` | [`over_switch`](over-switch.md) mit dem Plugin [VTherm Pellet stove](https://www.versatile-thermostat.org/de/plugins/#jmcollin78/vtherm_pellet_stove) | durch das Plugin |

Der [Gerätekatalog](https://www.versatile-thermostat.org/de/devices/) gibt für jedes getestete Gerät den empfohlenen Typ an.

Wenn mehrere Typen passen, entscheiden Sie nach der gewünschten Regelung. Regelt das Gerät selbst gut (Klimaanlage, manche Ventile), behält `over_climate` dessen Regelung bei. Soll _VTherm_ anhand Ihres eigenen Thermometers regeln, das dort platziert ist, wo Sie wohnen, wählen Sie `over_switch`, `over_valve` oder `over_climate` mit direkter Ventilsteuerung.

## Referenzartikel
Weitere Informationen zu diesen Begriffen finden Sie in diesem Artikel (auf Französisch): https://www.hacf.fr/optimisation-versatile-thermostat/#optimiser-vos-vtherm

## Nächster Schritt

[Auswahl der grundlegenden Attribute](base-attributes.md): dem _VTherm_ einen Namen geben, seine Temperatursensoren und die zu aktivierenden Funktionen wählen (Menüs „Wichtigste Eigenschaften“ und „Funktionen“).
