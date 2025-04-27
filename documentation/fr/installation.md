# Comment installer Versatile Thermostat ?

## HACS installation (recommendé)

1. Installez [HACS](https://hacs.xyz/). De cette façon, vous obtenez automatiquement les mises à jour.
2. L'intégration Versatile Thermostat est maintenant proposée directement depuis l'interface HACF (onglet intégrations),
3. recherchez et installez "Versatile Thermostat" dans HACS et cliquez sur "installer".
4. Redémarrez Home Assistant.
5. Ensuite, vous pouvez ajouter une intégration de Versatile Thermostat dans la page Paramètres / Intégrations. Vous ajoutez autant de thermostats dont vous avez besoin (généralement un par radiateur ou par groupe de radiateurs qui doivent être gérés ou par pompe dans le cas d'un chauffage centralisé)


## Installation manuelle

1. À l'aide de l'outil de votre choix, ouvrez le répertoire (dossier) de votre configuration HA (où vous trouverez `configuration.yaml`).
2. Si vous n'avez pas de répertoire (dossier) `custom_components`, vous devez le créer.
3. Dans le répertoire (dossier) `custom_components`, créez un nouveau dossier appelé `versatile_thermostat`.
4. Téléchargez _tous_ les fichiers du répertoire `custom_components/versatile_thermostat/` (dossier) dans ce référentiel.
5. Placez les fichiers que vous avez téléchargés dans le nouveau répertoire (dossier) que vous avez créé.
6. Redémarrez Home Assistant
7. Configurez la nouvelle intégration du Versatile Thermostat

