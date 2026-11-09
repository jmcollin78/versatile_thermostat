# Consignes de contribution

Contribuer à ce projet doit être aussi simple et transparent que possible, que ce soit :

- Signaler un bug
- Discuter de l'état actuel du code
- Soumettre un correctif
- Proposer de nouvelles fonctionnalités

## GitHub est utilisé pour tout

GitHub est utilisé pour héberger le code, suivre les problèmes et les demandes de fonctionnalités, ainsi que pour accepter les demandes de fusion (pull requests, ou PR).

Les PR sont un excellent moyen de proposer des modifications au code. Au fil de son histoire, l'équipe Versatile Thermostat en a accepté un grand nombre, et ces contributions ont largement participé au succès du projet. Nous sommes très reconnaissants envers toute la communauté pour sa participation.

## Comment les PR sont examinées

Avec l'essor des outils d'intelligence artificielle, presque tout le monde peut aujourd'hui préparer une PR. Certaines sont de grande qualité et sont intégrées au projet ; d'autres ne peuvent pas l'être.

Le nombre de PR a fortement augmenté. Leur examen est essentiellement manuel et porte notamment sur deux points :

- la qualité de la solution proposée ;
- sa cohérence avec la vision et les orientations futures de Versatile Thermostat.

Une PR qui répond à un besoin très spécifique — par exemple le comportement particulier d'un appareil ou une manière d'utiliser l'intégration propre à une personne — ne peut pas nécessairement être acceptée. En particulier, si elle augmente la complexité du projet et crée un risque pour les autres utilisateurs, son bénéfice doit être évalué au regard de ces conséquences.

Il n'est désormais plus possible d'examiner en détail toutes les PR reçues. Nous devons donc les trier et privilégier celles qui apportent une réelle valeur au produit ou à la communauté.

Depuis 2025, un mécanisme permet à chacun de développer des évolutions sans modifier l'intégration Versatile Thermostat et sans faire courir de risque aux autres utilisateurs : les plugins. Ils s'appuient sur le module [`vtherm_api`](https://github.com/jmcollin78/vtherm_api).

Avant de proposer une PR, merci de vérifier si votre besoin pourrait plutôt être couvert par un plugin, installable uniquement par les utilisateurs concernés.

En cas de doute sur la pertinence d'une évolution ou sur ses chances d'être acceptée, contactez le mainteneur avant de commencer à la développer. Cela permettra de discuter de l'approche envisagée en amont.

Un refus de PR peut être décevant, mais il n'a rien de personnel : cette décision vise à préserver l'intégration et l'expérience de l'ensemble des utilisateurs. Merci de votre compréhension.

## Proposer une modification

1. Fourchez le dépôt et créez votre branche à partir de `master`.
2. Si vous avez modifié quelque chose, mettez à jour la documentation.
3. Vérifiez le formatage de votre code avec Black.
4. Testez votre contribution.
5. Soumettez votre PR.

## Toutes les contributions que vous ferez seront sous la licence logicielle MIT

En bref, lorsque vous soumettez des modifications de code, vos soumissions sont considérées comme étant sous la même [licence MIT](http://choosealicense.com/licenses/mit/) qui couvre le projet. N'hésitez pas à contacter les mainteneurs si cela vous préoccupe.

## Signaler les bogues en utilisant les [issues] de Github (../../issues)

Les problèmes GitHub servent à suivre les bogues publics.
Signalez un bogue en [ouvrant un nouveau problème](../../issues/new/choose).

## Rédiger des rapports de bogue avec des détails, un arrière-plan et un exemple de code

Les **rapports de bogues géniaux** ont tendance à avoir :

- Un résumé rapide et/ou un historique
- Étapes à reproduire
   - Être spécifique!
   - Donnez un exemple de code si vous le pouvez.
- Ce à quoi vous vous attendiez arriverait
- Que se passe-t-il réellement
- Notes (y compris éventuellement pourquoi vous pensez que cela pourrait se produire, ou des choses que vous avez essayées qui n'ont pas fonctionné)

Les gens *adorent* les rapports de bogues approfondis. Je ne plaisante même pas.

## Utilisez un style de codage cohérent

Utilisez [black](https://github.com/ambv/black) pour vous assurer que le code suit le style.

## Testez votre modification de code

Ce composant personnalisé suit les bonnes pratiques décrites dans le [modèle d'intégration](https://github.com/custom-components/integration_blueprint).

Il est livré avec un environnement de développement dans un conteneur, facile à lancer
si vous utilisez Visual Studio Code. Ce conteneur lance une instance autonome de
Home Assistant, déjà configurée avec le fichier
[`.devcontainer/configuration.yaml`](./.devcontainer/configuration.yaml).

## Licence

En contribuant, vous acceptez que vos contributions soient autorisées sous sa licence MIT.