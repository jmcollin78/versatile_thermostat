# Leitlinien für Beiträge

Der Beitrag zu diesem Projekt sollte so einfach und transparent wie möglich sein, ganz gleich, ob es sich dabei um:

- Melden eines Fehlers
- Diskussion über den aktuellen Stand des Codes
- Einreichen einer Korrektur
- Vorschläge für neue Funktionen

handelt.

## GitHub wird für alles verwendet

GitHub wird verwendet, um Code zu hosten, Probleme und Funktionsanfragen zu verfolgen und Pull Requests anzunehmen.

Pull Requests (PRs) sind eine gute Möglichkeit, Änderungen an der Codebasis vorzuschlagen. Im Laufe seiner Geschichte hat das Versatile-Thermostat-Team viele PRs angenommen. Diese Beiträge haben wesentlich zum Erfolg des Projekts beigetragen. Wir sind der gesamten Community sehr dankbar für ihre Beiträge.

## Wie PRs geprüft werden

Mit dem Aufkommen von KI-Werkzeugen kann heute fast jeder eine PR vorbereiten. Manche sind von hoher Qualität und werden übernommen, andere können nicht angenommen werden.

Die Zahl der PRs ist stark gestiegen. Ihre Prüfung erfolgt größtenteils manuell und konzentriert sich auf zwei wesentliche Punkte:

- die Qualität der vorgeschlagenen Lösung;
- ihre Vereinbarkeit mit der Zukunftsvision und den geplanten Entwicklungen von Versatile Thermostat.

Eine PR, die ein sehr spezifisches Bedürfnis abdeckt — etwa das besondere Verhalten eines Geräts oder die individuelle Nutzung der Integration — kann nicht unbedingt angenommen werden. Insbesondere wenn sie die Komplexität erhöht und Risiken für andere Nutzer schafft, müssen die Vorteile gegen diese Folgen abgewogen werden.

Es ist nicht mehr möglich, jede eingehende PR im Detail zu prüfen. Deshalb müssen wir sie priorisieren und diejenigen bevorzugen, die einen konkreten Mehrwert für das Produkt oder die Community bieten.

Seit 2025 gibt es einen Mechanismus, mit dem jeder Erweiterungen entwickeln kann, ohne die Versatile-Thermostat-Integration zu verändern oder andere Nutzer einem Risiko auszusetzen: Plugins. Sie basieren auf dem Modul [`vtherm_api`](https://github.com/jmcollin78/vtherm_api).

Bitte prüfen Sie vor dem Einreichen einer PR, ob sich Ihr Anliegen stattdessen durch ein Plugin abdecken lässt, das nur die betroffenen Nutzer installieren.

Wenn Sie unsicher sind, ob eine Änderung sinnvoll ist oder angenommen werden könnte, wenden Sie sich bitte an den Maintainer, bevor Sie mit der Entwicklung beginnen. So kann der geplante Ansatz frühzeitig besprochen werden.

Eine abgelehnte PR kann enttäuschend sein, ist aber nicht persönlich gemeint: Die Entscheidung soll die Integration und die Nutzererfahrung für alle schützen. Vielen Dank für Ihr Verständnis.

## Eine Änderung vorschlagen

1. Forken Sie das Repo und erstellen Sie Ihren Zweig von  `master`.
2. Wenn Sie etwas geändert haben, aktualisieren Sie die Dokumentation.
3. Achten Sie darauf, dass Ihr Code mit Black formatiert ist.
4. Testen Sie Ihren Beitrag.
5. Reichen Sie Ihre PR ein.

## Alle Beiträge, die Sie leisten, stehen unter der MIT-Software-Lizenz

Kurz gesagt, wenn Sie Code-Änderungen einreichen, gelten diese als unter der gleichen [MIT-Lizenz] (http://choosealicense.com/licenses/mit/) stehend, die auch das Projekt abdeckt. Wenden Sie sich an die Betreuer, wenn das ein Problem ist.

## Fehler über die GitHub-[Issues](../../issues) melden

GitHub-Issues werden verwendet, um öffentliche Fehler (Bugs) zu verfolgen.
Melden Sie einen Fehler, indem Sie [ein neues Issue eröffnen](../../issues/new/choose).

## Verfassen von Fehlerberichten mit Details, Hintergrundinformationen und Beispielcode

**Große Fehlerberichte** haben meist:

- Eine kurze Zusammenfassung und/oder Hintergrundinformationen
- Schritte zur Reproduktion
  - Seien Sie genau!
  - Geben Sie, wenn möglich, Beispielcode an.
- Was Sie erwartet haben
- Was tatsächlich passiert
- Notizen (möglicherweise einschließlich der Gründe, warum Sie glauben, dass das Problem auftritt, oder Dinge, die Sie ausprobiert haben und die nicht funktioniert haben)

Die Leute *lieben* gründliche Fehlerberichte. Das ist kein Scherz.

## Verwenden Sie einen konsistenten Codingstil

Verwenden Sie [schwarz](https://github.com/ambv/black), um sicherzustellen, dass der Code dem Stil entspricht.

## Testen Sie Ihre Codeänderung

Diese benutzerdefinierte Komponente folgt den bewährten Praktiken aus dem [Integration Blueprint](https://github.com/custom-components/integration_blueprint).

Es wird mit einer Entwicklungsumgebung in einem Container geliefert, die leicht zu starten ist
wenn Sie Visual Studio Code verwenden. Dieser Container startet eine eigenständige
Home-Assistant-Instanz, die bereits mit der enthaltenen Datei
[`.devcontainer/configuration.yaml`](./.devcontainer/configuration.yaml) konfiguriert ist.

## Lizenz

Wenn Sie einen Beitrag leisten, stimmen Sie zu, dass Ihre Beiträge unter der MIT-Lizenz lizenziert werden.
