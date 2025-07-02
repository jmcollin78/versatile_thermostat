# Auto-Start / Auto-Stopp

- [Auto-Start / Auto-Stopp](#auto-start--auto-stop)
  - [Auto-Start/Stop konfigurieren](#auto-startstop-konfigurieren)
  - [Anwendung](#anwendung)

Mit dieser Funktion kann _VTherm_ ein Gerät stoppen, das nicht eingeschaltet sein muss, und es neu starten, wenn die Bedingungen es erfordern. Diese Funktion umfasst drei Einstellungen, welche die Geschwindigkeit des Stoppens und Wiedereinschaltens des Geräts bestimmen.
Ausschließlich für _VTherm_ des Typs `over_climate` reserviert, gilt er für den folgenden Anwendungsfall:
1. Ihr Gerät ist ständig eingeschaltet und verbraucht auch dann Strom, wenn keine Heizung (oder Kühlung) benötigt wird. Dies ist häufig bei Wärmepumpen (_WP_) der Fall, die auch im Standby-Modus Strom verbrauchen.
2. Die Temperaturbedingungen sind so, dass über einen längeren Zeitraum kein Heizen (oder Kühlen) erforderlich ist: Der Sollwert ist höher (oder niedriger) als die Raumtemperatur.
3. Die Temperatur steigt (oder fällt), bleibt stabil oder fällt (oder steigt) langsam.

In solchen Fällen ist es besser, das Gerät aufzufordern, sich auszuschalten, um unnötigen Stromverbrauch im Standby-Modus zu vermeiden.

## Auto-Start/Stop konfigurieren

Um diese Funktion zu nutzen, benötigen Sie:
1. Fügen Sie die Funktion `Mit Autostart und Stopp` im Menü 'Funktionen' hinzu.
2. Stellen Sie die Erkennungsstufe in der Option 'Auto-Start/Stopp' ein, die bei Aktivierung der Funktion erscheint. Wählen Sie die Erkennungsstufe zwischen 'Langsam', 'Mittel' und 'Schnell'. Bei der Einstellung 'Schnell' werden die Stopps und Neustarts häufiger durchgeführt.

![image](images/config-auto-start-stop.png)

Bei der Einstellung 'Langsam' vergehen etwa 30 Minuten zwischen einem Stopp und einem Neustart.
Bei der Einstellung 'Mittel' liegt der Schwellenwert bei etwa 15 Minuten, bei der Einstellung „Schnell“ bei 7 Minuten.

Beachten Sie, dass dies keine absoluten Werte sind, da der Algorithmus die Steigung der Raumtemperaturkurve berücksichtigt, um entsprechend zu reagieren. Es ist immer noch möglich, dass kurz nach einem Stopp ein Neustart erfolgt, wenn die Temperatur stark abfällt.

## Anwendung

Sobald die Funktion konfiguriert ist, verfügen Sie über eine neue Entity vom Typ `switch`, mit der Sie den automatischen Start/Stopp aktivieren oder deaktivieren können, ohne dabei die Konfiguration zu ändern. Diese Entity ist im _VTherm_-Gerät verfügbar und nennt sich `switch.<name>_enable_auto_start_stop`.

![image](images/enable-auto-start-stop-entity.png)

Aktivieren Sie das Kontrollkästchen, um Auto-Start und Auto-Stopp zuzulassen, und deaktivieren Sie es, um die Funktion zu deaktivieren.

Hinweis: Die Auto-Start/Stop-Funktion schaltet ein _VTherm_ nur dann wieder ein, wenn es durch diese Funktion ausgeschaltet wurde. Dies verhindert ungewollte oder unerwartete Aktivierungen. Selbstverständlich bleibt der ausgeschaltete Zustand auch nach einem Neustart des Home Assistant erhalten.

> ![Tip](images/tips.png) _*Hinweise*_
> 1. Der Erkennungsalgorithmus ist [hier](algorithms.md#auto-startstop-algorithm) beschrieben.
> 2. Einige Geräte (Heizkessel, Fußbodenheizung, _WP_, etc.) mögen es vielleicht nicht, wenn sie zu häufig gestartet/gestoppt werden. Wenn das der Fall ist, ist es vielleicht besser, die Funktion zu deaktivieren, wenn Sie wissen, dass das Gerät benutzt werden wird. Ich deaktiviere diese Funktion zum Beispiel tagsüber, wenn Anwesenheit erkannt wird, weil ich weiß, dass sich meine _WP_ oft einschalten wird. Nachts oder wenn niemand zu Hause ist, aktiviere ich die Start-Stopp-Automatik, da der Sollwert gesenkt wird und sie nur selten auslöst.
> 3. Wenn Sie die Versatile Thermostat UI-Karte verwenden (siehe [hier](additions.md#better-with-the-versatile-thermostat-ui-card)), ist ein Kontrollkästchen direkt auf der Karte sichtbar, um Auto-Start/Stopp zu deaktivieren, und ein _VTherm_, das durch Auto-Start/Stopp gestoppt wurde, wird durch dieses Symbol angezeigt: ![auto-start/stop icon](images/auto-start-stop-icon.png).