# Revue de l'issue #2136

**Statut :** rapport, specification et conception approuves ; correction implementee, tests cibles valides.
**Issue :** [#2136 - Window sensor removal (template.reload) raises AttributeError](https://github.com/jmcollin78/versatile_thermostat/issues/2136)
**Auteur :** @frmelle
**Date de revue :** 2026-10-21
**Recommandation :** retenir une correction ciblee du cycle de vie du capteur de fenetre.

## Resume fidele

L'auteur signale, avec VTherm 10.6.1 et egalement sur `main` selon ses verifications, une exception lors de chaque appel a `template.reload`. Ses sept VTherm `over_climate` utilisent des capteurs de fenetre template. Le rechargement retire puis recree ces entites ; leur retrait produit un evenement dont `new_state` vaut `None`.

Le callback `_window_sensor_changed` lit `new_state.state` pour choisir le delai avant d'executer sa garde contre `None`. La trace fournie indique exactement cette lecture. L'auteur attend l'absence d'erreur et une detection toujours fonctionnelle apres le rechargement. Il propose de deplacer la garde et signale separement l'utilisation de `@callback` sur une coroutine.

L'auteur rapporte huit erreurs par rechargement pour sept instances identifiees, sur trois rechargements. Cette difference de comptage n'est pas expliquee par les elements fournis ; elle ne remet pas en cause le defaut reproduit. Le journal complet est propose sur demande, mais n'est pas joint.

## Sources et elements verifies

- Description complete et commentaires de [l'issue #2136](https://github.com/jmcollin78/versatile_thermostat/issues/2136), consultes via l'outil GitHub et la page publique. Aucun commentaire n'est present au moment de la consultation.
- La page publique indique une issue ouverte, sans etiquette, assignation, jalon, relation ni branche ou pull request associee. Il ne s'agit pas d'une recherche exhaustive de tous les travaux du depot.
- [feature_window_manager.py](../../custom_components/versatile_thermostat/feature_window_manager.py#L179) : callback, garde tardive, choix des delais, annulation et creation du timer, fermeture `try_window_condition` et application de l'etat.
- [feature_window_manager.py](../../custom_components/versatile_thermostat/feature_window_manager.py#L124) : abonnement par identifiant de capteur et arret des listeners.
- [feature_window_manager.py](../../custom_components/versatile_thermostat/feature_window_manager.py#L156) : `refresh_state` ignore deja les entites absentes et les etats `unknown` et `unavailable`.
- [test_window_feature_manager.py](../../tests/test_window_feature_manager.py#L128) : tests parametres voisins de rafraichissement ; recherche des appels directs au callback et de leurs callbacks differes dans le meme fichier.
- [test_window.py](../../tests/test_window.py) et [commons.py](../../tests/commons.py#L1181) : recherche des usages du callback retourne pour simuler l'expiration des delais. Ces usages rendent necessaire une attention a ce contrat de test.
- [pyproject.toml](../../pyproject.toml) et [setup.cfg](../../setup.cfg) : utilisation de pytest avec mode asyncio automatique.
- [#1902](https://github.com/jmcollin78/versatile_thermostat/issues/1902) : erreur de calcul de pourcentage de vanne sur valeur absente, corrigee par [#1903](https://github.com/jmcollin78/versatile_thermostat/pull/1903), distincte du retrait d'un capteur de fenetre.
- [#1987](https://github.com/jmcollin78/versatile_thermostat/issues/1987) : action hors-gel en refroidissement, corrigee par [#1994](https://github.com/jmcollin78/versatile_thermostat/pull/1994), distincte du present defaut.

### Verification executee

Le corps reel de `_window_sensor_changed` a ete extrait par AST et execute avec un evenement minimal contenant `old_state.state = "off"` et `new_state = None`. Seuls les annotations, le decorateur et la journalisation ont ete neutralises pour permettre une execution autonome, sans importer Home Assistant.

**Resultat :** `AttributeError: 'NoneType' object has no attribute 'state'`, a la ligne 220 du callback. L'hypothese locale est donc confirmee : la garde tardive laisse passer une lecture invalide avant toute planification de timer.

**Limites :** ce controle ne constitue ni un test d'integration HA, ni une reproduction de `template.reload`, ni une validation du comportement du decorateur. Aucun service HA n'a ete appele. Aucun code, configuration ou dependance n'a ete modifie. La suite pytest n'a pas ete executee pendant cette revue.

## Pertinence et recommandation

**Retenir.** Le probleme est une erreur de programmation prouvee sur un evenement de cycle de vie legitime, pas une configuration utilisateur incorrecte. La correction appartient au gestionnaire partage des fenetres et ne doit pas etre reservee aux thermostats `over_climate` ou aux capteurs template.

La faisabilite apparente est bonne : le point d'entree et les tests voisins existent. La suppression de l'exception est locale ; la reprise et le sort d'une temporisation en cours doivent cependant etre specifies pour ne pas livrer une correction seulement cosmetique.

La proposition de code de l'auteur n'est pas applicable telle quelle : elle retourne `try_window_condition` avant sa definition, ce qui introduit un `UnboundLocalError` sur les branches de retour anticipe. En outre, donner une valeur par defaut a `delay` ne rend pas la fermeture sure lorsqu'elle dereference encore un `new_state` ou un `old_state` absent.

## Perimetre propose

### Inclus, sous reserve de validation

- Verifier l'existence des etats avant toute lecture de leur attribut `state`.
- Ne pas interpreter la disparition du capteur comme une fermeture de fenetre ou comme une demande de changement HVAC.
- Definir explicitement le traitement de la recreation du capteur et garantir la reprise sans rechargement manuel de VTherm.
- Definir et tester le sort du timer actif lors d'un retrait et de la reprise, sans callback dangereux ni action fondee sur une observation devenue obsolete.
- Preserver les delais distincts d'ouverture et de fermeture, le bypass, les actions configurees et le traitement des changements d'attributs sans changement d'etat.
- Ajouter les regressions dans les fichiers de tests existants, avec au moins un scenario passant par les evenements HA plutot qu'uniquement par un appel direct.
- Documenter les decisions dans les futures specifications et conception ; prevoir une mention de correction selon les pratiques de publication du projet.

### Exclus

- Refonte generale des callbacks de tous les managers ou de la journalisation HA.
- Modification des templates utilisateur, du service `template.reload`, des capteurs physiques ou des integrations de vannes.
- Nouvelle politique globale de securite chauffage pour les capteurs durablement indisponibles.
- Modification des algorithmes de detection automatique par pente de temperature, des schemas de configuration ou des dependances.
- Correction de `@callback` dans ce lot sans verification du contrat HA et decision explicite de perimetre. L'observation secondaire reste a instruire separement ; elle n'est pas necessaire pour prouver la cause racine.

## Impacts et risques

| Domaine / risque                                                 | Gravite                                                | Probabilite estimee                              | Mesure proposee                                                                                  |
| ---------------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| Exception a chaque retrait d'un capteur suivi                    | Moyenne                                                | Certaine pour l'entree reproduite                | Garde avant dereferencement et test de retrait                                                   |
| Etat fenetre obsolete apres recreation avec un etat different    | Haute, selon l'action chauffage                        | Plausible ; effet utilisateur non reproduit      | Specification de reprise et tests dans les deux sens                                             |
| Timer anterieur restant actif durant la disparition du capteur   | Moyenne a haute, selon l'action                        | Conditionnelle a un delai en cours ; non mesuree | Tests retrait pendant ouverture et fermeture differees                                           |
| Regression des delais ou du bypass sur le gestionnaire partage   | Moyenne                                                | Faible si changement local et tests adaptes      | Tests voisins et verification des actions HVAC                                                   |
| Regression du contrat de callback retourne utilise par les tests | Faible en production, moyenne pour la validation       | Plausible si retour anticipe modifie             | Adapter uniquement les assertions concernees, garder les callbacks valides testables             |
| Bruit repetitif et attribution difficile dans les journaux       | Moyenne                                                | Rapportee a chaque rechargement                  | Supprimer l'exception attendue ; conserver un contexte thermostat/capteur dans les traces utiles |
| Securite et confidentialite                                      | Aucun nouveau risque identifie pour le correctif local | Non applicable                                   | Aucun secret ou journal utilisateur complet necessaire a ce stade                                |

**Compatibilite :** surface partagee par les types de VTherm utilisant un capteur de fenetre ; conserver l'API et les reglages existants. Aucune migration de donnees ou modification de dependance n'est envisagee.

**Exploitation :** aucune action sur l'environnement HA pendant cette phase. Un essai manuel de rechargement, s'il devient necessaire, exigera un environnement de test autorise. Le correctif ne doit pas imposer un redemarrage apres chaque rechargement de templates.

**Documentation :** pas de nouvelle option utilisateur prevue. Les regles de conservation et de reprise d'etat devront etre explicites dans les documents de specification et de conception.

## Alternatives examinees

| Option                                            | Avantage                                                   | Limite                                                                                                      | Recommandation                                         |
| ------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Deplacer uniquement la garde existante            | Diff minimal, supprime le premier dereferencement invalide | Ignore toujours la recreation et ne definit pas les timers ; fermeture retournee potentiellement dangereuse | Insuffisant pour garantir tout le comportement attendu |
| Garde sure et traitement cible du retrait/reprise | Couvre le cycle complet, sans refonte                      | Exige des decisions fonctionnelles et quelques regressions supplementaires                                  | Option recommandee                                     |
| Transformer une absence en `off`                  | Simplifie artificiellement le chemin normal                | Confond absence de mesure et fenetre fermee, risque de reprise du chauffage                                 | A ecarter                                              |
| Retirer seulement `@callback`                     | Peut modifier la gestion des taches et erreurs             | Ne supprime pas la lecture de `None.state` ; effet exact non verifie                                        | Ne constitue pas une correction de la cause racine     |
| Eviter provisoirement `template.reload`           | Evite le declencheur rapporte                              | Empeche un usage HA normal et ne corrige pas le defaut                                                      | Contournement temporaire seulement, non teste          |

## Hypotheses et questions ouvertes

### Faits

- La lecture precede la garde et l'exception est reproduite en isolation.
- Le code actuel ignore les evenements avec `old_state = None` sans planifier de nouvelle verification.
- Le callback differe utilise aussi les etats captures ; il doit rester sur en cas d'evolution du chemin de retour.

### Propositions a valider pendant la specification

1. Conserver le dernier etat de fenetre confirme pendant le retrait, plutot que fabriquer une fermeture.
2. Annuler la temporisation devenue obsolete et repartir d'une observation valide lors de la recreation, avec le delai correspondant. La conception devra couvrir une recreation identique a l'etat memorise comme une recreation differente.
3. Ne pas elargir implicitement ce correctif a une nouvelle semantique generale de `unknown` et `unavailable` ; couvrir leur presence dans la sequence de rechargement et expliciter toute adaptation necessaire avant le developpement.

### Inconnues et limites

- Version exacte de Home Assistant du rapporteur et journal complet non fournis.
- Origine du huitieme bloc d'erreur non etablie ; non bloquante pour le defaut local.
- Lien causal entre `@callback` et le format de l'erreur non demontre dans cette revue. Ne pas promettre que retirer le decorateur fournit automatiquement de meilleures traces.
- Aucun doublon n'est identifie parmi les deux tickets cites ; recherche exhaustive des issues et PR non effectuee.
- Les regles de reprise et de timer ci-dessus sont des recommandations, pas des decisions utilisateur deja approuvees. Elles doivent etre resolues avant toute autorisation de developpement.

## Criteres de passage au developpement

1. Rapport explicitement approuve par l'utilisateur, avec autorisation de specification et de conception.
2. Specifications et conception convergentes sur le retrait, la recreation, les timers, le bypass et les etats non exploitables ; aucune question bloquante restante.
3. Scenarios d'acceptation definis : suppression avec `new_state = None`, creation avec `old_state = None`, suppression/recreation repetee, recreation identique ou differente, delai actif dans les deux sens, bypass et absence de changement d'etat.
4. Les tests doivent verifier l'absence d'exception, l'absence de commande HVAC injustifiee pendant le retrait, la reprise apres delai et l'absence de timer obsolete ou de listener duplique.
5. Verification par `pytest tests/test_window_feature_manager.py tests/test_window.py`, avec adaptation ciblee si le contrat de retour du callback change.
6. Resultats finaux presentes a l'utilisateur et autorisation explicite distincte de demarrer le developpement.

## Suite du processus

L'utilisateur a approuve le rapport et autorise specification et conception par son message du 2026-10-21 : « Go pour spec, conception et implémentation ». Cet accord a permis les delegations documentaires aux agents disponibles « Rédacteur de spécifications » et « Conception logicielle détaillée ». Conformement au processus impose, il ne remplace pas la validation distincte des resultats finaux apres leur presentation.

### Documents produits

- [Specification fonctionnelle bilingue](issue-2136-specification.md).
- [Conception technique et matrice de couverture](issue-2136-design.md).

### Convergence obtenue au cycle 2/3

Le premier cycle a identifie une divergence sur `refresh_state` : une interdiction absolue de contourner les delais aurait modifie son contrat immediat d'initialisation, deja couvert par les tests existants. Le second cycle a borne la garantie au flux evenementiel de retrait et de reprise, qui ne doit pas appeler `refresh_state`. Son contrat d'initialisation reste inchange.

Les deux agents ont explicitement confirme le meme perimetre, la couverture des exigences et criteres d'acceptation, l'absence de contradiction technique bloquante et une solution realisable et testable. La conception couvre les exigences FR-001 a FR-016 et les criteres AC-001 a AC-014.

### Choix candidats soumis a validation finale

1. Conserver le dernier etat accepte pendant le retrait ou un etat transitoire `unknown`/`unavailable`, dans l'instance vivante ; ne pas fabriquer de fermeture ni de nouvelle commande HVAC.
2. Invalider l'observation en attente puis annuler son timer. Une generation privee distincte de `dearm_window_timer` rend inertes les anciennes fermetures, meme deja capturees.
3. A la reprise exploitable, comparer a l'etat conserve : aucun changement effectif s'il est identique ; sinon respecter le delai directionnel d'ouverture ou de fermeture.
4. Preserver bypass, timer valide lors des changements d'attributs seuls, unicite du listener et fermetures async callable, avec une fermeture sans effet pour les branches ignorees.
5. Conserver le rafraichissement immediat d'initialisation et exclure le retrait de `@callback`, toute nouvelle option et toute politique globale d'indisponibilite durable.

Aucune question technique bloquante ne subsiste dans ce perimetre. Les choix precedents ont ete approuves par l'utilisateur avant l'implementation.

### Validation et risques residuels

Les agents ont effectue des controles documentaires cibles apres leurs editions. Aucun code, test, configuration, dependance ni environnement HA n'a ete modifie pendant la specification et la conception. La version HA exacte du rapporteur et son journal complet restent inconnus.

### Developpement et verification

Apres presentation des documents convergents, l'utilisateur a autorise explicitement le developpement puis la substitution de l'agent prescrit `developpement-ha-integration`, indisponible, par « Développement d’intégrations Home Assistant ». Le travail lui a ete delegue dans le perimetre approuve.

- [Gestionnaire de fenetre](../../custom_components/versatile_thermostat/feature_window_manager.py) : protection des etats absents ou inexploitable, conservation de l'etat confirme, reprise temporisee et generation invalidant les fermetures obsoletes.
- [Tests du gestionnaire](../../tests/test_window_feature_manager.py) : evenements emis via le bus HA, delais directionnels, suppression/recreation, timer obsolete, etats inexploitable, attributs seuls et cycle de vie du listener.
- `rtk pytest -q tests/test_window_feature_manager.py tests/test_window.py` : 67 tests reussis, aucun echec (relance independante apres delegation).
- `rtk git diff --check` : aucun defaut d'espacement signale par le delegue.

Le contrat immediat de `refresh_state` et le decorateur `@callback` sont inchanges. Aucun service `template.reload` reel ni environnement utilisateur n'a ete actionne : le scenario est couvert par simulation d'evenements via le bus HA, pas par une verification sur l'installation du rapporteur.