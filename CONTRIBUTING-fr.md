# Consignes de contribution

Contribuer à ce projet doit être aussi simple et transparent que possible, que ce soit :

- Signaler un bug
- Discuter de l'état actuel du code
- Soumettre un correctif
- Proposer de nouvelles fonctionnalités

## Github est utilisé pour tout

Github est utilisé pour héberger du code, pour suivre les problèmes et les demandes de fonctionnalités, ainsi que pour accepter les demandes d'extraction.

Les demandes d'extraction sont le meilleur moyen de proposer des modifications à la base de code.

1. Fourchez le dépôt et créez votre branche à partir de `master`.
2. Si vous avez modifié quelque chose, mettez à jour la documentation.
3. Assurez-vous que votre code peluche (en utilisant du noir).
4. Testez votre contribution.
5. Émettez cette pull request !

## Toutes les contributions que vous ferez seront sous la licence logicielle MIT

En bref, lorsque vous soumettez des modifications de code, vos soumissions sont considérées comme étant sous la même [licence MIT](http://choosealicense.com/licenses/mit/) qui couvre le projet. N'hésitez pas à contacter les mainteneurs si cela vous préoccupe.

## Signaler les bogues en utilisant les [issues] de Github (../../issues)

Les problèmes GitHub sont utilisés pour suivre les bogues publics.
Signalez un bogue en [ouvrant un nouveau problème](../../issues/new/choose) ; C'est si facile!

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

Ce composant personnalisé est basé sur les meilleures pratiques décrites ici [modèle d'intégration_blueprint](https://github.com/custom-components/integration_blueprint).

Il est livré avec un environnement de développement dans un conteneur, facile à lancer
si vous utilisez Visual Studio Code. Avec ce conteneur, vous aurez un stand alone
Instance de Home Assistant en cours d'exécution et déjà configurée avec le inclus
[`.devcontainer/configuration.yaml`](./.devcontainer/configuration.yaml)
déposer.

## Licence

En contribuant, vous acceptez que vos contributions soient autorisées sous sa licence MIT.