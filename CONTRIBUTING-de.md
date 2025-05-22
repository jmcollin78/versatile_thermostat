# Leitlinien für Beiträge

Der Beitrag zu diesem Projekt sollte so einfach und transparent wie möglich sein, ganz gleich, ob es sich dabei um:

- Melden eines Fehlers
- Diskussion über den aktuellen Stand des Codes
- Einreichen einer Korrektur
- Vorschläge für neue Funktionen

handelt.

## Github wird für alles verwendet

Github wird verwendet, um Code zu hosten, um Probleme und Funktionsanfragen zu verfolgen und um Pull Requests zu akzeptieren.

Pull Requests sind der beste Weg, um Änderungen an der Codebasis vorzuschlagen.

1. Forken Sie das Repo und erstellen Sie Ihren Zweig von `master`.
2. Wenn Sie etwas geändert haben, aktualisieren Sie die Dokumentation.
3. Vergewissern Sie sich, dass sich Ihr Code färbt (in Schwarz).
4. Testen Sie Ihren Beitrag.
5. Erstellen Sie einen Pull Request!

## Alle Beiträge, die Sie leisten, stehen unter der MIT-Software-Lizenz

Kurz gesagt, wenn Sie Code-Änderungen einreichen, gelten diese als unter der gleichen [MIT-Lizenz] (http://choosealicense.com/licenses/mit/) stehend, die auch das Projekt abdeckt. Wenden Sie sich an die Betreuer, wenn das ein Problem ist.

## Fehlermeldungen benutzen Github's [issues](../../issues)

GitHub-Issues werden verwendet, um öffentliche Fehler (Bugs) zu verfolgen.
Melden Sie einen Fehler, indem Sie [ein neues Problem öffnen](../../issues/new/choose); so einfach ist das!

## Verfassen von Fehlerberichten mit Details, Hintergrundinformationen und Beispielcode

**Große Fehlerberichte** haben meist:

- Eine kurze Zusammenfassung und/oder Hintergrundinformationen
- Schritte zur Reproduktion
  - Seien Sie genau!
  - Geben Sie, wenn möglich, Beispielcode an.
- Was Sie erwartet haben
- Was tatsächlich passiert ist
- Notizen (möglicherweise einschließlich der Gründe, warum Sie glauben, dass das Problem auftritt, oder Dinge, die Sie ausprobiert haben und die nicht funktioniert haben)

Die Leute *lieben* gründliche Fehlerberichte. Das ist kein Scherz.

## Verwenden Sie einen konsistenten Codingstil

Verwenden Sie [schwarz](https://github.com/ambv/black), um sicherzustellen, dass der Code dem Stil entspricht.

## Testen Sie Ihre Codeänderung

Diese benutzerdefinierte Komponente basiert auf den hier beschriebenen bewährten Praktiken [integration_blueprint template] (https://github.com/custom-components/integration_blueprint).

Es wird mit einer Entwicklungsumgebung in einem Container geliefert, die leicht zu starten ist
wenn Sie Visual Studio Code verwenden. Mit diesem Container haben Sie eine eigenständige
Home Assistant-Instanz, mit der bereits enthaltenen
[`.devcontainer/configuration.yaml`](./.devcontainer/configuration.yaml)
Datei.

## Lizenz

Wenn Sie einen Beitrag leisten, stimmen Sie zu, dass Ihre Beiträge unter der MIT-Lizenz lizenziert werden.