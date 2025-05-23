# Wahl eines VTherm

- [Wahl eines VTherm](#wahl-eines-vtherm)
  - [Erstellen eines neuen Versatile Thermostats](#erstellen-eines-neuen-versatile-thermostats)
- [Auswahl eines VTherm-Typs](#auswahl-eines-vtherm-typs)
  - [Zentrale Konfiguration](#zentrale-konfiguration)
  - [VTherm über einen Schalter](#vtherm-über-einen-schalter)
  - [VTherm über anderes Thermostat](#vtherm-über-anderes-Thermostat)
  - [VTherm über Ventil](#vtherm-über-ventil)
- [Wähle das Richtige aus](#wähle-das-richtige-aus)
- [Referenzartikel](#referenzartikel)

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

# Auswahl eines VTherm-Typs

## Zentrale Konfiguration
Mit dieser Option können Sie bestimmte sich wiederholende Aspekte für alle VTherms auf einmal konfigurieren, z. B:
1. Parameter für verschiedene Algorithmen (TPI, Erkennung offener Fenster, Bewegungserkennung, Stromsensoren für Ihr Haus, Präsenzerkennung). Diese Parameter gelten für alle VTherms. Sie müssen sie nur einmal in der „Zentralen Konfiguration“ eingeben. Mit dieser Konfiguration wird kein VTherm selbst erstellt, sondern es werden Parameter zentralisiert, die mühsam für jedes VTherm neu eingegeben werden müssten. Beachten Sie, dass Sie diese Parameter für einzelne VTherms außer Kraft setzen können, um sie bei Bedarf anzupassen.
2. Konfiguration zur Steuerung einer Zentralheizungsanlage,
3. Bestimmte erweiterte Parameter, wie z. B. Sicherheitseinstellungen.

## VTherm über einen Schalter
Dieser VTherm-Typ steuert einen Schalter, der einen Heizkörper ein- oder ausschaltet. Bei dem Schalter kann es sich um einen physischen Schalter handeln, der einen Heizkörper direkt steuert (häufig elektrisch), oder um einen virtuellen Schalter, der beim Ein- oder Ausschalten eine beliebige Aktion ausführen kann. Der letztere Typ kann zum Beispiel Pilotdrahtschalter oder DIY-Lösungen mit Dioden steuern. VTherm moduliert den Anteil der Zeit, in der der Heizkörper eingeschaltet ist (`on_percent`), um die gewünschte Temperatur zu erreichen. Wenn es kalt ist, schaltet er sich häufiger ein (bis zu 100 %); wenn es warm ist, wird die Einschaltzeit reduziert.

Die zugrundeliegenden Entitäten für diesen Typ sind `switches` oder `input_booleans`.

## VTherm über anderes Thermostat
Wenn Ihr Gerät durch eine `climate`-Entity in Home Assistant gesteuert wird und Sie nur Zugriff auf diese haben, sollten Sie diesen VTherm-Typ verwenden. In diesem Fall passt VTherm einfach die Zieltemperatur der zugrunde liegenden `climate`-Entity an.

Dieser Typ verfügt auch über fortschrittliche Selbstregulierungsfunktionen zur Anpassung des an das zugrundeliegende Gerät gesendeten Sollwerts, was dazu beiträgt, die Zieltemperatur schneller zu erreichen und eine schlechte interne Regelung abzumildern. Befindet sich beispielsweise das interne Thermometer des Geräts zu nahe am Heizelement, kann es fälschlicherweise annehmen, dass der Raum warm ist, während der Sollwert in anderen Bereichen bei weitem nicht erreicht wird.

Seit Version 6.8 kann dieser VTherm-Typ auch direkt über die Steuerung des Ventils geregelt werden. Ideal für steuerbare TRVs, wie Sonoff TRVZB, wird dieser Typ empfohlen, wenn Sie solche Geräte haben.

Die diesem VTherm-Typ zugrunde liegenden Einheiten sind ausschließlich `climate`.

## VTherm über Ventil
Wenn die einzige Entität, die zur Regelung der Temperatur Ihres Heizkörpers zur Verfügung steht, eine Entität des Typs `number` ist, sollten Sie den Typ `over_valve` verwenden. VTherm passt die Ventilöffnung auf der Grundlage der Differenz zwischen der Zieltemperatur und der tatsächlichen Raumtemperatur (und der Außentemperatur, falls verfügbar) an.

Dieser Typ kann für TRVs ohne eine zugehörige `climate`-Entity oder andere DIY-Lösungen verwendet werden, die eine `number`-Entity aufweisen.

# Wähle das Richtige aus
> ![Tip](images/tips.png) _*Wie man den Typ wählt*_
> Die Wahl des richtigen Typs ist entscheidend. Sie kann später nicht über die Konfigurationsschnittstelle geändert werden. Um die richtige Wahl zu treffen, sollten Sie die folgenden Fragen berücksichtigen:
> 1. **Welche Art von Geräten werde ich kontrollieren?** Befolgen Sie diese Reihenfolge:
>    1. Wenn Sie ein steuerbares Thermostatventil (TRV) in Home Assistant über eine `number`-Entity haben (z. B. ein Shelly TRV), wählen Sie den Typ „over_valve“. Dies ist der direkteste Typ und gewährleistet die beste Regulierung.
>    2. Wenn Sie einen elektrischen Heizkörper (mit oder ohne Pilotdraht) haben, der über einen Schalter ein- und ausgeschaltet wird, ist der Typ `over_switch` vorzuziehen. Die Regelung erfolgt durch das Versatile Thermostat auf der Grundlage der von Ihrem Thermometer an seinem Aufstellungsort gemessenen Temperatur.
>    3. In allen anderen Fällen sollten Sie den `over_climate`-Modus verwenden. Sie behalten Ihre ursprüngliche `climate`-Entity bei, und das Versatile Thermostat steuert "nur" den Ein-/Aus-Zustand und die Zieltemperatur Ihres ursprünglichen Thermostats. Die Regelung wird in diesem Fall von Ihrem ursprünglichen Thermostat übernommen. Dieser Modus eignet sich besonders für reversible All-in-One-Klimaanlagen, die in Home Assistant als `climate`-Entity angezeigt werden. Die erweiterte Selbstregulierung kann den Sollwert schneller erreichen, indem sie den Sollwert erzwingt oder das Ventil direkt steuert, wenn dies möglich ist.
> 2. **Welche Art der Regulierung möchte ich?** Wenn die gesteuerten Geräte über einen eigenen eingebauten Regulierungsmechanismus verfügen (z. B. HLK-Systeme, bestimmte TRVs) und dieser gut funktioniert, wählen Sie `over_climate`. Für TRVs mit einem steuerbaren Ventil in Home Assistant ist der Typ `over_climate` mit der Selbstregulierung `Direct Valve Control` die beste Wahl.

# Referenzartikel
Weitere Informationen zu diesen Begriffen finden Sie in diesem Artikel (auf Französisch): https://www.hacf.fr/optimisation-versatile-thermostat/#optimiser-vos-vtherm