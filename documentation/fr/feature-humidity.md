# Capteur d’humidité externe

VTherm peut exposer `current_humidity` depuis un capteur externe pour les thermostats `over_switch`, `over_valve` et `over_climate`.

Ouvrez **Humidité** dans le menu de configuration, activez l’option puis sélectionnez un capteur. Si le sélecteur reste vide, VTherm utilise le capteur d’humidité détecté automatiquement sur le même appareil que le capteur de température ambiante. Désactivez l’option pour ne plus utiliser de capteur externe ou détecté.

La source est lue au démarrage et à chaque changement d’état. Une valeur invalide, indisponible ou inconnue donne une humidité indéfinie et n’affecte jamais la régulation. Pour `over_climate`, sans source externe, l’humidité de l’entité sous-jacente reste utilisée.
