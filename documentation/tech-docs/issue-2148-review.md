# Revue de l'issue #2148

**Issue :** [#2148 - When a VTherm is stopped by auto-start/stop the preset change is not visible](https://github.com/jmcollin78/versatile_thermostat/issues/2148)
**Statut :** rapport approuve pour specification et conception le 2026-10-24 ; seul le test de reproduction a ete autorise et realise. Correctif non autorise.
**Recommandation actuelle :** differer tout correctif ; reprendre le diagnostic seulement si le probleme reapparait avec des traces comparables.

## Resume et sources verifiees

@jmcollin78 signale qu'avec un VTherm mis sur `off` par auto-start/stop, changer le preset ne met a jour ni le preset ni la temperature cible visibles dans la carte VTherm UI. Desactiver auto-start/stop rend ensuite le nouveau preset et la nouvelle consigne visibles et pris en compte. Le probleme est rapporte sur la version 10.6.1 ; son caractere regressif est suspecte par l'auteur, non demontre.

- [Issue #2148](https://github.com/jmcollin78/versatile_thermostat/issues/2148) : ouverte, etiquettes `bug` et `P1`, sans commentaire, assignation, jalon, relation ou PR associee visible au moment de la revue. Aucune capture, trace ou description du type de VTherm n'est fournie.
- [manifest.json](../../custom_components/versatile_thermostat/manifest.json) : version locale `10.6.1`, conforme a la version citee ; cela ne prouve pas que la copie locale correspond exactement a l'installation du rapporteur.
- [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) : `async_set_preset_mode` valide et enregistre le preset demande, puis force `update_states`. Cette methode calcule le nouvel etat, affecte les attributs preset/temperature lorsqu'ils changent et appelle `async_write_ha_state`.
- [state_manager.py](../../custom_components/versatile_thermostat/state_manager.py) : l'auto-stop force le mode HVAC courant sur `off` sans effacer le mode demande ; le calcul du preset reprend normalement le preset demande, puis celui de la consigne utilise le preset courant. Les priorites puissance, securite, mode central, fenetre, presence, mouvement et preset temporise peuvent toutefois modifier ces valeurs.
- [feature_auto_start_stop_manager.py](../../custom_components/versatile_thermostat/feature_auto_start_stop_manager.py) : la detection d'arret lit la consigne courante ; la desactivation de la fonction force une nouvelle mise a jour de l'etat.
- [test_auto_start_stop.py](../../tests/test_auto_start_stop.py) : le scenario historique `eco` vers `boost` attend une reprise. Un nouveau test parametre couvre maintenant le changement de preset avec maintien sur `off`, avec et sans inhibition, en comparant les etats internes et l'entite HA.
- [test_auto_start_stop_stop_mode.py](../../tests/test_auto_start_stop_stop_mode.py) et [feature-auto-start-stop.md](../fr/feature-auto-start-stop.md) : le mode d'arret peut aussi etre `fan_only` ou `dry`, selon l'equipement ; l'issue mentionne explicitement `off`.

Aucune recherche exhaustive de doublons dans les issues ou PR n'a ete effectuee ; aucun travail lie n'etait indique sur la page de l'issue lors de la consultation initiale.

### Bilan du diagnostic du 2026-10-24

- Le test HA `test_auto_start_stop_off_preset_change_updates_climate_state` passe dans ses deux variantes (`auto-stop` et `inhibited-auto-stop`) : `eco` / 17 °C devient `frost` / 7 °C dans les etats demande, effectif et HA, tandis que `off` persiste. L'inhibition prioritaire change le motif effectif d'arret sans effacer la detection auto-stop. Le test ne verifie pas le rendu de la carte ni les commandes aux equipements sous-jacents.
- Dans l'instance locale, les logs et le recorder ont confirme `eco` / 17 °C -> `comfort` / 19 °C en restant sur `off` a 23 °C ambiants. Un autre changement vers `boost` / 20 °C a provoque une reprise legitime en `heat`. L'utilisateur n'a pas constate le bug sur la carte ; son rendu n'a pas ete capture independamment.
- L'utilisateur indique ne pas reproduire non plus le probleme sur son installation de production. Aucun journal ni snapshot d'un incident reproduit n'a ete fourni ; ce retour n'est pas une preuve que le defaut initial a disparu.

**Conclusion :** ni le test ni les essais locaux et de production rapportes n'identifient une couche fautive. Ne modifier ni le calcul ni la carte sur la seule base de l'issue initiale.

## Pertinence et perimetre propose

**Differer le correctif, conserver le signalement.** La visibilite immediate de la consigne programmee pendant un arret automatique reste importante. L'issue etait etiquetee `P1` lors de la consultation initiale, mais aucune sequence defaillante n'a ete reproduite. Il serait premature d'attribuer le probleme au calcul, a la publication HA ou a la carte UI.

**Inclus :** reproduire `off` automatique, changer de preset sans provoquer un redemarrage, comparer `requested_state`, `current_state`, `preset_mode` et `temperature` de l'entite `climate` HA avec l'affichage de la carte ; corriger la couche responsable apres confirmation, puis tester l'affichage immediat et la reprise ulterieure. Couvrir au minimum `over_climate` si reproductible, et etendre aux autres types partageant le meme chemin uniquement si necessaire.

**Exclus :** changer l'algorithme d'arret ou les seuils de redemarrage sans demonstration de causalite ; forcer la remise en chauffe a chaque changement de preset ; refondre la carte UI, les autres motifs d'arret, les modes `fan_only`/`dry`, ou les integrations sous-jacentes hors besoin prouve. La carte UI est un composant externe : toute correction de ce cote necessitera un perimetre et un depot distincts.

## Impacts et risques

| Domaine / risque                                                                 | Gravite                               | Probabilite                                                | Mesure proposee                                                                         |
| -------------------------------------------------------------------------------- | ------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Consigne programmee invisible pendant l'arret, risque de mauvaise interpretation | Moyenne                               | Rapportee dans l'issue ; non reproduite ici                | Verification des attributs HA et de la carte dans la meme sequence                      |
| Correction qui relance le chauffage alors que l'auto-stop doit rester actif      | Haute                                 | Plausible si on modifie la logique de mode ou de detection | Test avec preset modifie mais conditions d'auto-stop toujours presentes                 |
| Divergence entre etat demande, etat courant et attributs publies                 | Moyenne                               | Inconnue                                                   | Assertions des trois surfaces, y compris apres desactivation ou redemarrage automatique |
| Impact sur types de VTherm et priorites de fonctionnalites partagees             | Moyenne                               | Conditionnelle au choix de la correction                   | Tests cibles puis tests voisins des modes et priorites concernees                       |
| Defaut uniquement dans la carte externe et non dans l'integration                | Moyenne pour l'orientation du travail | Inconnue                                                   | Verifier l'etat brut de l'entite HA avant toute modification de l'integration           |

**Securite et confidentialite :** aucune nouvelle collecte de donnees ni permission n'est envisagee. Pour diagnostiquer, des attributs et journaux expurges suffisent ; ne pas demander de secrets. **Compatibilite et migration :** conserver les services et attributs existants ; aucune migration, dependance ou modification de configuration n'est envisagee a ce stade. **Exploitation :** un test HA sur une instance de developpement et la carte, s'il est autorise ulterieurement, devra eviter toute action sur les equipements reels. **Documentation :** clarifier, si le comportement n'est pas deja explicite, que la consigne reste visible et editable pendant l'auto-stop ; ajouter une note de correction dans les notes de version selon les usages du depot.

## Alternatives et contournements

| Option                                                                      | Avantage                                            | Limite                                                                |
| --------------------------------------------------------------------------- | --------------------------------------------------- | --------------------------------------------------------------------- |
| Corriger le calcul/publication de l'entite si ses attributs restent anciens | Traite la source d'etat pour tous les consommateurs | Risque de regression fonctionnelle ; doit etre confirme par un test   |
| Corriger la carte si les attributs HA sont deja a jour                      | Correction localisee de l'affichage                 | Hors de ce depot ; ne regle pas une entite HA incorrecte              |
| Desactiver temporairement auto-start/stop pour verifier la consigne         | Contournement deja rapporte                         | Peut relancer le chauffage et ne constitue pas une correction         |
| Forcer le redemarrage au changement de preset                               | Affiche indirectement les nouvelles valeurs         | Change la regulation et peut allumer un equipement a tort ; a ecarter |

## Faits, hypotheses et decisions necessaires

**Faits :** l'issue decrit un ecart d'affichage avec `off` automatique en 10.6.1. Le test ajoute et les observations locales montrent des changements correctement publies pendant un arret persistant ; le rapporteur n'a pas retrouve le defaut en production. Le motif d'une eventualite precedente demeure inconnu.

**Hypothese encore ouverte :** une combinaison non presente dans les essais (priorite, etat transitoire, version ou carte) pourrait differer le calcul ou l'affichage. Le seul arret automatique `off`, meme associe a une inhibition dans le test, ne suffit pas a reproduire l'ecart. Si le defaut revient, comparer sur une meme sequence horodatee `requested_state`, `current_state`, les attributs HA et la carte avant d'attribuer la cause.

**Questions ouvertes, non bloquantes pour valider la revue mais bloquantes pour choisir le correctif :** quel type de VTherm, quels presets et temperatures, quelle version de HA et de carte UI, et par quel service ou interaction le preset est-il modifie ? Les attributs bruts HA sont-ils incorrects ou seule la carte les masque-t-elle en mode `off` ? La reproduction persiste-t-elle avec mode central, fenetre, securite, presence ou preset temporise actifs ? Une version precedente connue fonctionnait-elle ?

## Suite et criteres de passage au developpement

1. Rapport, specification et conception etablis ; seule l'ecriture du test de reproduction a ete autorisee. Aucun correctif n'est engage.
2. Lors d'une nouvelle occurrence, relever horodatage, type et versions VTherm/HA/carte, commande ou geste, preset et consigne avant/apres, temperature ambiante, `is_ready`, mode demande/effectif, motif d'arret, inhibition, securite, surpuissance, mode central, preset temporise, ainsi que l'etat brut HA et l'affichage de la carte. Expurger les donnees sensibles.
3. Identifier la premiere divergence entre demande, etat effectif, publication HA et carte ; si seule la carte diverge, faire approuver son depot et son perimetre separes. Les priorites ne doivent pas etre modifiees sur simple supposition.
4. Mettre alors a jour les documents selon la preuve recueillie, obtenir une autorisation explicite de correctif et seulement ensuite implementer avec un test echouant sur le defaut confirme et les regressions pertinentes.