# Schnellstart

Auf dieser Seite werden die Schritte zur schnellen Einrichtung eines einfachen, aber betriebsbereiten _VTherm_ beschrieben. Gegliedert nach Gerätetypen.

- [Schnellstart](#quick-start)
  - [Nodon SIN-4-FP-21 oder ähnlich (Pilotdraht)](#nodon-sin-4-fp-21-oder-ähnlich-pilotdraht)
  - [Heatzy, eCosy, oder ähnlich (`climate`-Entity)](#heatzy-ecosy-oder-ähnlich-`climate`-entity)
  - [Einfache Schalter wie Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...](#einfache-schalter-wie-aqara-t1-nous-b2z-sonoff-zbmini-sonoff-pow-)
  - [Sonoff TRVZB oder ähnlich (TRV mit Ventilsteuerung)](#sonoff-trvzb-oder-ähnlich-trv-mit-ventilsteuerung)
  - [Reversible Wärmepumpen, Klimaanlagen oder Geräte, die über eine `climate`-Entity gesteuert werden](#reversible-wärmepumpen-klimaanlagen-oder-geräte-die-über-eine-climate-entity-gesteuert-werden)
- [Nächste Schritte](#nächste-schritte)
- [Aufruf zu Beiträgen](#aufruf-zu-beiträgen)

## Nodon SIN-4-FP-21 oder ähnlich (Pilotdraht)

Dieses Modul ermöglicht die Steuerung eines Heizkörpers über einen Pilotdraht. Es erscheint in _HA_ als eine `select`-Einheit, mit der Sie die anzuwendende Heizungsvoreinstellung auswählen können.

Das _VTherm_ regelt die Temperatur, indem es die Voreinstellung über benutzerdefinierte Befehle periodisch ändert, bis der Sollwert erreicht ist.

Damit dies funktioniert, muss die für die Heizungssteuerung verwendete Voreinstellung höher sein als die von Ihnen benötigte Höchsttemperatur (24°C ist ein guter Wert).

Für die Integration in _VTherm_, müssen Sie:
1. Erstelle ein _VTherm_ vom Typ `over_switch`. Siehe [Erstellen eines _VTherm_](creation.md),
2. Weisen Sie ihm die Hauptattribute zu (mindestens Name, Raumtemperaturfühler und Außentemperaturfühler). Siehe [Hauptattribute](base-attributes.md),
3. Weisen Sie ein oder mehrere zugehörige Geräte der Steuerung zu. Das zugehörige Gerät ist hier die `select`-Entität, die den Nodon steuert. Siehe [zugehörige Geräte](over-switch.md),
4. Stellen Sie benutzerdefinierte Ein/Aus-Befehle bereit (erforderlich für den Nodon). Siehe [Befehlsanpassung](over-switch.md#command-customization). Die benutzerdefinierten Befehle folgen dem Format `select_option/option:<preset>`, wie im Link angegeben.

Nach diesen vier Schritten haben Sie eine voll funktionsfähige _VTherm_, die Ihr Nodon oder ein ähnliches Gerät steuert.

## Heatzy, eCosy, oder ähnlich (`climate`-Entity)

Dieses Modul ermöglicht die Steuerung eines Heizkörpers, der in _HA_ als `climate`-Entity erscheint, und ermöglicht die Wahl der Heizungsvoreinstellung oder des Modus (Heizen / Kühlen / Aus).

Das _VTherm_ regelt die Temperatur, indem es das Gerät über benutzerdefinierte Befehle in regelmäßigen Abständen ein- und ausschaltet, bis der Sollwert erreicht ist.

Für die Integration in _VTherm_, müssen Sie:
1. Erstelle ein _VTherm_ vom Typ `over_switch`. Siehe [Erstellen eines _VTherm_](creation.md),
2. Weisen Sie ihm die Hauptattribute zu (mindestens Name, Raumtemperaturfühler und Außentemperaturfühler). Siehe [Hauptattribute](base-attributes.md),
3. Weisen Sie ein oder mehrere zugehörige Geräte der Steuerung zu. Das zugehörige Gerät ist hier die `climate`-Entity die die Heatzy oder eCosy steuert. Siehe [zugehörige Geräte](over-switch.md),
4. Stellen Sie benutzerdefinierte Ein/Aus-Befehle bereit (erforderlich). Siehe [Befehlsanpassung](over-switch.md#command-customization). Die benutzerdefinierten Befehle haben das Format `set_hvac_mode/hvac_mode:<mode>` oder `set_preset_mode/preset_mode:<preset>`, wie im Link angegeben.

Nach diesen vier Schritten haben Sie eine voll funktionsfähige _VTherm_, die Ihr Heatzy, eCosy, oder ähnliches Gerät steuert.

## Einfache Schalter wie Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...

Dieses Modul ermöglicht die Steuerung eines Heizkörpers über einen einfachen Schalter. Es erscheint in _HA_ als `switch`-Entität, die den Heizkörper direkt ein- oder ausschaltet.

Das _VTherm_ regelt die Temperatur durch periodisches Ein- und Ausschalten des Schalters, bis der Sollwert erreicht ist.

Für die Integration in _VTherm_, müssen Sie:
1. Erstelle ein _VTherm_ vom Typ `over_switch`. Siehe [Erstellen eines _VTherm_](creation.md),
2. Weisen Sie ihm die Hauptattribute zu (mindestens Name, Raumtemperaturfühler und Außentemperaturfühler). Siehe [Hauptattribute](base-attributes.md),
3. Weisen Sie ein oder mehrere zugehörige Geräte der Steuerung zu. Das zugehörige Gerät ist hier die `switch`-Entity die den Schalter steuert. Siehe [Zugehörige Geräte](over-switch.md).

Nach Abschluss dieser drei Schritte haben Sie ein voll funktionsfähiges _VTherm_, das Ihren `Schalter` oder ein ähnliches Gerät steuert.

## Sonoff TRVZB oder ähnlich (TRV mit Ventilsteuerung)

Diese Art von _TRV_-Gerät steuert die Öffnung eines Ventils, das mehr oder weniger heißes Wasser aus einem Heizkessel oder einer Wärmepumpe fließen lässt. Es erscheint in _HA_ als eine `climate`-Entity zusammen mit einer `number`-Entitäten die das Ventil steuern. Diese `number`-Entitäten können versteckt sein und müssen in einigen Fällen explizit hinzugefügt werden.

_VTherm_ passt den Öffnungsgrad des Ventils an, bis die Solltemperatur erreicht ist.

Für die Integration in _VTherm_, müssen Sie:
1. Erstelle ein _VTherm_ vom Typ `over_climate`. Siehe [Erstellen eines _VTherm_](creation.md),
2. Weisen Sie ihm die Hauptattribute zu (mindestens Name, Raumtemperaturfühler und Außentemperaturfühler). Siehe [Hauptattribute](base-attributes.md),
3. Weisen Sie ein oder mehrere zugehörige Geräte der Steuerung zu. Das zugehörige Gerät ist hier die `climate`-Entity die das TRV steuert. [Zugehörige Geräte](over-climate.md),
4. Geben Sie als Regelungsart nur `Direkte Ventilsteuerung` an. Nicht die Option `Zugehörige Temperatur kompensieren` auswählen. Siehe [Autoregulierung](over-climate.md#auto-regulation),
5. Geben Sie die Entitäten mit den Namen `Öffnungsgrad`, `Schließgrad` und `Kalibrierungsoffset` an. Siehe [Zugehörige Geräte](over-switch.md).

Damit dies funktioniert, muss der `Schließungsgrad` auf den Höchstwert (100 %) eingestellt sein. Aktivieren Sie die Option `Unterliegende Temperaturänderung folgen` erst, wenn Sie sich vergewissert haben, dass diese Grundkonfiguration ordnungsgemäß funktioniert.

Nach Abschluss dieser fünf Schritte haben Sie über ein voll funktionsfähiges _VTherm_, das Ihr Sonoff TRVZB oder ein ähnliches Gerät steuert.

## Reversible Wärmepumpen, Klimaanlagen oder Geräte, die über eine `climate`-Entity gesteuert werden

Reversible Wärmepumpen (heat pumps/HP) oder ähnliche Geräte werden in _HA_ als `climate`“-Entity dargestellt, so dass Sie die Heizungsvoreinstellung oder den Modus (Heizen / Kühlen / Aus) auswählen können).

_VTherm_ regelt die Temperatur, indem es die Zieltemperatur und den Modus des Geräts durch Befehle steuert, die an die zugehörige `climate`-Entity gesendet werden.

Für die Integration in _VTherm_, müssen Sie:
1. Erstelle ein _VTherm_ vom Typ `over_climate`. Siehe [Erstellen eines _VTherm_](creation.md),
2. Weisen Sie ihm die Hauptattribute zu (mindestens Name, Raumtemperaturfühler und Außentemperaturfühler). Siehe [Hauptattribute](base-attributes.md),
3. Weisen Sie ein oder mehrere zugehörige Geräte der Steuerung zu. Das zugehörige Gerät ist hier die `climate`-Entity  die die Wärmepumpe oder Klimaanlage steuert. Siehe [Zugehörige Geräte](over-climate.md),

Nach diesen drei Schritten haben Sie ein voll funktionsfähiges _VTherm_ zur Steuerung Ihrer Wärmepumpe, Klimaanlage oder eines ähnlichen Gerätes.

Um noch weiter zu gehen, kann eine Selbstregulierung erforderlich sein, je nachdem, wie gut Ihr Gerät funktioniert. Bei der Selbstregulierung passt _VTherm_ die Solltemperatur geringfügig an, um das Gerät zu veranlassen, mehr oder weniger zu heizen oder zu kühlen, bis der gewünschte Sollwert erreicht ist. Die Selbstregulierung wird hier im Detail erklärt: [Selbstregulierung](self-regulation.md).

# Nächste Schritte

Nach der Erstellung müssen Sie die voreingestellten Temperaturen konfigurieren. Siehe [Voreinstellungen](feature-presets.md) für eine minimale Konfiguration.
Sie können auch (optional, aber empfohlen) die spezielle UI-Karte für Ihre Dashboards installieren. (Siehe [VTHerm UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card))

Sobald diese minimale Einrichtung funktioniert - und nur dann, wenn sie korrekt funktioniert - können Sie zusätzliche Funktionen hinzufügen, wie z. B. die Anwesenheitserkennung, um zu verhindern, dass geheizt wird, wenn keine Person anwesend ist. Fügen Sie diese nach und nach hinzu und überprüfen Sie, ob _VTherm_ bei jedem Schritt korrekt reagiert, bevor Sie mit dem nächsten fortfahren.

Sie können dann zentrale Konfigurationen einrichten, um Einstellungen für alle _VTherm_-Instanzen gemeinsam zu nutzen. Den Zentralmodus für die einheitliche Steuerung aller _VTherms_ aktivieren ([zentrale Konfiguration](feature-central-mode.md)) oder eine zentrale Kesselsteuerung integrieren ([Zentralheizung](feature-central-boiler.md)). Diese Liste ist nicht vollständig - eine vollständige Liste der _VTherm_-Funktionen finden Sie im Inhaltsverzeichnis.

# Aufruf zu Beiträgen

Diese Seite ist offen für Beiträge. Fühlen Sie sich frei, zusätzliche Ausrüstung und minimale Konfigurationseinstellungen vorzuschlagen.
