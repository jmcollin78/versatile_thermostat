# Wie installiert man Versatile Thermostat?

## HACS Installation (Empfohlen)

1. Installieren Sie [HACS](https://hacs.xyz/). Auf diese Weise erhalten Sie automatisch Updates.
2. Die Integration von Versatile Thermostat ist jetzt direkt über die HACS-Schnittstelle (Integrationen) verfügbar.
3. Suchen Sie in HACS nach "Versatile Thermostat" und klicken sie auf "Installieren".
4. Home Assistant neu starten.
5. Dann können Sie auf der Seite Einstellungen/Integrationen eine Integration für ein Versatile Thermostat hinzufügen. Fügen Sie so viele Thermostate wie nötig hinzu (in der Regel einen pro Heizkörper oder Gruppe von Heizkörpern, die gesteuert werden müssen, oder pro Pumpe im Falle eines Zentralheizungssystems).

## Manuelle Installation

1. Öffnen Sie mit dem Werkzeug Ihrer Wahl das Konfigurationsverzeichnis des Home Assistant (dort finden Sie die Datei `configuration.yaml`).
2. Wenn Sie kein Verzeichnis `custom_components` haben, müssen Sie eines erstellen.
3. Erstellen Sie innerhalb des Verzeichnisses `custom_components` einen neuen Ordner mit dem Namen `versatile_thermostat`.
4. Laden Sie _alle_ Dateien aus dem Verzeichnis (Ordner) `custom_components/versatile_thermostat/` in diesem Repository herunter.
5. Legen Sie die heruntergeladenen Dateien in den neu erstellten Ordner.
6. Home Assistant neu starten.
7. Konfigurieren Sie die neue Versatile Thermostat-Integration.