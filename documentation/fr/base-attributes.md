- [Choix des attributs de base](#choix-des-attributs-de-base)
- [Choix des fonctions utilisées](#choix-des-fonctions-utilisées)

# Choix des attributs de base

Choisisez le menu "Principaux attributs".

![image](images/config-main.png)

| Attribut | Description | Nom d'attribut |
| --------- | ----------- | -------------- |
| **Nom** | Nom de l'entité (cela sera le nom de l'intégration et de l'entité `climate`). | |
| **Capteur de température** | Identifiant du capteur donnant la température de la pièce où l'appareil est installé. | |
| **Capteur dernière mise à jour (optionnel)** | Évite les mises en sécurité quand la température est stable et que le capteur ne remonte plus. (cf. [troubleshooting](troubleshooting.md#pourquoi-mon-versatile-thermostat-se-met-en-securite-)) | |
| **Durée de cycle** | Durée en minutes entre chaque calcul. Pour `over_switch` : modulation du temps allumé. Pour `over_valve` : calcul ouverture vanne. Pour `over_climate` : contrôles et recalcul coefficients auto-régulation. Avec les types `over_switch` et `over_valve`, les calculs sont effectués à chaque cycle. Donc en cas de changement de conditions, il faudra attendre le prochain cycle pour voir un changement. Pour cette raison, le cycle ne doit pas être trop long. 5 min est une bonne valeur mais doit être adapté à votre type de chauffage. Plus l'inertie est grande et plus le cycle doit être long. Cf. [Exemples de réglages](tuning-examples.md). Si le cycle est trop court, l'appareil ne pourra jamais atteindre la température cible. Pour le radiateur à accumulation par exemple il sera sollicité inutilement. | `cycle_min` |
| **Puissance de l'équipement** | Active capteurs puissance/énergie. Indiquer total si plusieurs équipements (même unité que autres VTherm et capteurs). (cf. fonction de délestage) | `device_power` |
| **Paramètres complémentaires centralisés** | Utilise température extérieure, min/max/pas de température de la configuration centrale. | |
| **Contrôle centralisé** | Permet contrôle centralisé du thermostat. Cf [controle centralisé](#le-contrôle-centralisé) | `is_controlled_by_central_mode` |
| **Déclencheur de chaudière centrale** | Case à cocher pour utiliser ce VTherm comme déclencheur de chaudière centrale. | `is_used_by_central_boiler` |

# Choix des fonctions utilisées

Choisissez le menu "Fonctions".

![image](images/config-features.png)

| Fonction | Description | Nom d'attribut |
| --------- | ----------- | -------------- |
| **Avec détection d'ouvertures** | Stoppe le chauffage à l'ouverture de portes/fenêtres. (cf. [gestion des ouvertures](feature-window.md)) | `is_window_configured` |
| **Avec détection de mouvement** | Adapte la consigne de température à la détection de mouvement dans la pièce. (cf. [détection du mouvement](feature-motion.md)) | `is_motion_configured` |
| **Avec gestion de la puissance** | Stoppe l'équipement si la puissance consommée dépasse un seuil. (cf. [gestion du délestage](feature-power.md)) | `is_power_configured` |
| **Avec détection de présence** | Change la température de consigne selon présence/absence. Diffère de la détection de mouvement (habitation vs pièce). (cf. [gestion de la présence](feature-presence.md)) | `is_presence_configured` |
| **Avec arrêt/démarrage automatique** | Pour `over_climate` uniquement : arrête/rallume l'équipement selon prévision via courbe de température. (cf. [gestion de l'arrêt/démarrage automatique](feature-auto-start-stop.md)) | `is_window_auto_configured` |


> ![Astuce](images/tips.png) _*Notes*_
> 1. La liste des fonctions disponibles s'adapte à votre type de VTherm.
> 2. Lorsque vous cochez une fonction, une nouvelle entrée menu s'ajoute pour configurer la fonction.
> 3. Vous ne pourrez pas valider la création d'un VTherm si tous les paramètres de toutes les fonctions n'ont pas été saisis.
