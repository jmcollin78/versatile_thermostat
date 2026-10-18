# Revue de la PR #2113 - Correctif de l'issue #2111

**Statut :** retenir le principe ; differer la fusion, revalidation apres resolution du conflit obligatoire.
**Issue :** [#2111](https://github.com/jmcollin78/versatile_thermostat/issues/2111)
**PR :** [#2113](https://github.com/jmcollin78/versatile_thermostat/pull/2113)
**Revue actualisee :** 2026-10-18 ; remplace la conclusion moins conditionnelle du 2026-10-13.
**Commit de PR examine :** `f19d5aa8e6ec2c0dee45af71f632748b8aa4c1fd`.
**Base GitHub annoncee :** `d61ba711d0d1564a33d97131e50517f90e88ad7e` (`main`).
**Methode :** revue statique du diff distant, du fichier au commit de PR et des chemins locaux pertinents. Aucun checkout, test execute, ni changement de code, de configuration ou d'etat Home Assistant. La revision exacte du workspace n'a pas ete verifiee par Git.

## Conclusion pour le mainteneur

Aucune regression certaine introduite par le diff n'a ete etablie dans les chemins consultes. Cela ne constitue pas une preuve d'absence de regression. Le correctif est localise et coherent pour les transitions nominales avec temperatures disponibles ; il ne justifie pas une approbation inconditionnelle.

Ne pas fusionner en l'etat : GitHub annonce `mergeable: false`, `mergeable_state: dirty`. Exiger une nouvelle revue du resultat de resolution, des tests sur cette revision et une beta ciblee. Les risques principaux sont la concurrence des commandes, la reprise avec donnees absentes et les interactions avec les protections actuelles. Ils ne sont pas tous des defauts nouveaux de cette PR.

## Resume et discussions verifies

L'issue concerne VTherm 10.5.1, HA 2026.10.1 et des Sonoff TRVZB via Zigbee2MQTT, en `over_climate` avec regulation directe et periode minimale de 5 minutes. Les transitions vers/depuis `sleep` peuvent garder une ouverture obsolete a 100 %, un `hvac_action: heating` et un comptage actif injustifies. Une automatisation de pompe a chaleur a effectivement reagit a cet etat selon le declarant.

La PR ajoute deux memoires de mode, pour le dernier calcul et le dernier passage dans l'envoi. Un changement de mode contourne les filtres de periode et de variation d'ouverture. Elle change deux fichiers : production +13/-3 lignes, tests +211 lignes (cinq tests).

- @jmcollin78, 13 octobre : souligne la sensibilite de la boucle, demande une beta separee et une observation reelle ; cite la premiere version de ce rapport.
- @JMBO1701, 14 octobre : propose 13 Sonoff TRVZB, plusieurs transitions quotidiennes et un retour apres une a deux semaines. C'est une proposition de test, pas un resultat de beta.
- @jmcollin78, 18 octobre : annonce 10.6.1 et demande de resoudre le conflit avant publication d'une beta.
- Les API de reviews et de commentaires inline renvoient des listes vides au moment de la consultation. Aucun autre retour materiel n'a ete trouve dans les trois commentaires accessibles.

## Constats classes

### 1. Priorite haute : la revision a integrer n'est pas encore validable

**Fait et bloqueur de fusion, pas bug de regulation demontre.** Le conflit est confirme par l'API, pas uniquement par le commentaire du mainteneur. La CI du commit du 13 octobre ne couvre pas le resultat encore inexistant de sa resolution sur la base actuelle.

Le chemin a depuis evolue avec l'inhibition [#2101](https://github.com/jmcollin78/versatile_thermostat/pull/2101), commit `be64352685510dbca9f88252ca2a50aea3bf7077`. Le bootstrap des vannes [#2096](https://github.com/jmcollin78/versatile_thermostat/pull/2096), corrigeant #2049, est egalement une dependance fonctionnelle a preserver, mais precede la PR.

**Action :** ne pas resoudre le conflit en remplacant le fichier actuel par celui de la branche de PR. Conserver les protections et verifier le diff obtenu. La localisation exacte des conflits n'a pas ete determinee ici.

### 2. Priorite moyenne : la garantie de sortie de sleep suppose un calcul disponible

**Limite etablie par lecture, comportement preexistant ; pas une regression nouvelle prouvee.** Dans [recalculate](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L234), si `safe_on_percent` vaut `None`, le code conserve `_valve_open_percent` et retourne sans memoriser le nouveau mode de calcul. Dans [TPI](../../custom_components/versatile_thermostat/prop_algo_tpi.py#L83), une consigne ou temperature courante absente rend le resultat indisponible.

Ainsi, apres `sleep`, un calcul indisponible peut laisser 100 % en cache. Si la consigne existe, le nouvel envoi peut utiliser ce cache ; si elle manque aussi, l'envoi retourne avant toute commande, y compris en OFF dans cette methode. D'autres chemins peuvent encore arreter le dispositif : ne pas en deduire que OFF est globalement inefficace.

Une simple valeur HA `unavailable` n'implique pas necessairement `_cur_temp = None` : le traitement du capteur peut conserver une ancienne mesure. L'occurrence exacte de ce scenario en production n'est pas demontree.

**Action :** tester la sortie de sleep avec `on_percent is None`, puis le retour du capteur ; decider explicitement du comportement attendu. Ne pas promettre une ouverture fraichement calculee dans tous les cas. Ne pas imposer ici une fermeture systematique qui changerait la politique existante.

### 3. Priorite moyenne : le filtre dpercent n'est pas teste de facon discriminante

**Lacune de couverture verifiee.** Les nouveaux tests utilisent `dpercent = 0.5` et des ouvertures entieres 0/40/100. Le test de non-changement de mode reste dans la periode : le premier filtre suffit a le faire reussir, meme si le filtre dpercent etait casse. Il ne prouve donc pas la preservation des deux filtres annoncee dans la description.

**Action :** ajouter une verification avec un seuil significatif, par exemple 5 points : periode expiree, petite variation positive non nulle filtree a mode constant ; puis transition `heat 98 % -> sleep 100 % -> heat 98 %`, qui doit contourner ce filtre et revenir a 98 %. Verifier aussi la fermeture a 0 %, independamment du filtre, et la reprise du filtrage apres transition.

### 4. Risque a consequence elevee : un mode memorise n'est pas un acquittement materiel

**Fait structurel et risque non reproduit.** `_last_sent_hvac_mode` est affecte apres plusieurs `await` et relit le mode courant, sans capturer une revision de la demande. Une autre chaine peut changer ce mode pendant l'envoi. Les nouveaux tests attendent la fin des taches entre chaque transition : ils ne testent pas cet entrelacement.

Les services de [UnderlyingEntity](../../custom_components/versatile_thermostat/underlyings.py#L225) peuvent absorber une erreur ou supprimer une commande via la porte d'inhibition. [set_valve_open_percent](../../custom_components/versatile_thermostat/underlyings.py#L1435) deduplique selon un cache modifie avant l'envoi. La memoire de mode ne garantit donc ni le succes du service ni la position physique. Ces mecanismes preexistent ; la nouvelle memoire ajoute une condition de filtrage a verifier, pas une preuve de panne.

**Action :** test d'entrelacement deterministe, avec service suspendu, changement de mode concurrent et au moins deux vannes ; verifier la convergence vers la derniere demande. Couvrir un echec de service et une commande bloquee, sans supposer que le simple retour de coroutine constitue un acquittement.

## Ce que le correctif preserve ou change

| Surface                                      | Analyse statique                                                                     | Reserve                                                                                                   |
| -------------------------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| `heat -> sleep`                              | Le calcul passe immediatement a 100 %, meme dans la periode.                         | 100 % logique reste soumis a la conversion min/max des vannes.                                            |
| `sleep -> heat`, piece chaude                | Le TPI peut calculer 0 et l'envoi ne patiente plus.                                  | Donnees de calcul disponibles ; retours materiels non instantanes.                                        |
| `sleep -> off -> heat`                       | Chaque mode est distingue ; la valeur de sleep peut etre remplacee avant la reprise. | Tester aussi une piece froide et un resultat indisponible.                                                |
| `off -> heat` sans sleep                     | Le calcul devient immediat lui aussi.                                                | Extension de comportement voulue par la PR, au-dela du seul symptome sleep.                               |
| Changements HVAC automatiques                | Le mode effectif est utilise, pas seulement l'appel utilisateur.                     | Fenetre, central, securite et inhibition a couvrir.                                                       |
| Mode constant stabilise                      | Les conditions de periode et dpercent restent presentes.                             | Les cinq tests ne prouvent pas toutes les bornes ni la reprise apres transition.                          |
| Demande identique repetee                    | La comparaison ne force pas de nouveau calcul pour un mode deja memorise.            | Les autres appels `force=True` preexistants restent possibles.                                            |
| Ouverture identique apres changement de mode | La memoire de calcul est mise a jour meme sans changement de pourcentage.            | Bon point : evite de detecter indefiniment une transition. L'horodatage du calcul n'est alors pas avance. |
| Envoi physique                               | Les caches des sous-jacents dedupliquent encore une ouverture identique.             | Il est inexact de dire que chaque transition produit toujours une commande physique.                      |
| TPI, seuil de fermeture, min/max             | Aucun changement de formule ou de conversion dans le diff.                           | Recalcul plus tot ; essais avec plusieurs vannes et bornes non triviales requis.                          |
| Autres types de thermostat                   | Pas de modification directe de leur code.                                            | Suite globale apres rebase pour les interactions partagees.                                               |

### Deux chemins de commande a ne pas confondre

Le controle `ThermostatOverClimate.async_control_heating()` appelle l'envoi regule puis la chaine de controle de base. Le handler proportionnel peut ensuite appeler [CycleScheduler._apply_valve_command](../../custom_components/versatile_thermostat/cycle_scheduler.py#L409), qui appelle aussi `set_valve_open_percent()`.

Il serait donc errone de deduire une vanne bloquee uniquement du retour anticipe de `_send_regulated_temperature()`. Les tests doivent observer les services effectivement emis dans le flux complet, pas seulement simuler cette methode. La deduplication des sous-jacents limite normalement les doubles commandes.

Les horodatages de calcul et d'envoi ne constituent pas une transaction : un calcul sans changement de valeur conserve son ancien horodatage, alors qu'un passage d'envoi hors OFF avance le sien meme sans commande nouvelle. Une transition avec ouverture inchangee peut donc desynchroniser ces delais. Verifier la premiere mise a jour suivante ; aucun blocage nouveau n'est prouve ici, notamment a cause du second chemin ci-dessus.

## Evaluation des risques et impacts

La probabilite n'est pas quantifiable sans execution et observations terrain. Les niveaux ci-dessous decrivent les consequences, pas une prediction de panne.

| Risque                                                          | Gravite potentielle | Probabilite / preuve                                                                     | Mesure                                                  |
| --------------------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Chauffe ou demande chaudiere persistante apres reprise          | Elevee              | Bug initial rapporte ; variante sans donnees non reproduite                              | Matrice de transitions + capteurs + retour chaudiere.   |
| Commandes concurrentes ou couple ouverture/fermeture incoherent | Elevee              | Hypothese ; entrelacement non teste dans le diff                                         | Test suspendant les services + beta multi-vannes.       |
| Regression inhibition / reprise apres inhibition                | Elevee              | Integration non validee apres conflit ; porte centrale toujours presente dans le code lu | Rejouer les tests inhibition sur la revision finale.    |
| Augmentation des commandes lors de bascules rapides             | Moyenne             | Contournement des delais explicite ; volume reel depend des caches                       | Compter les services et messages Zigbee2MQTT.           |
| Perte de filtrage ou retard apres transition                    | Moyenne             | Conditions lues, couverture partielle                                                    | Tests periode/dpercent et horloges desynchronisees.     |
| Initialisation, restauration sleep, recalibrage                 | Moyenne a elevee    | Pas de nouveau resultat d'execution                                                      | Rejouer les tests correspondants et redemarrer en beta. |

**Securite/confidentialite :** pas de nouvel acces, stockage, reseau ou secret dans le diff. Le risque pertinent est operationnel (chauffage, debit et commandes physiques), pas une nouvelle exposition de donnees.

**Compatibilite/migration :** deux attributs volatils internes, sans schema ni migration de configuration. Le mode COOL est expose pour les configurations AC, mais les nouveaux tests mettent `AC_MODE=False` : ne pas annoncer une validation COOL.

**Exploitation/documentation :** une beta isolee facilite l'attribution des anomalies et le retour a 10.6.1. Documenter l'exception de cadence sur changement de mode et les conditions de validite du calcul ; aucune modification de documentation utilisateur ou de release n'a ete faite ici.

## Tests : preuves et lacunes

L'API des checks du commit examine annonce `testu: success`, style/HACS/Validate reussis et `Run tests: skipped`. Il existe donc bien un job de tests reussi ; le job saute n'autorise pas a dire que tous les tests ont ete ignores. Le detail du nombre execute n'a pas ete extrait des logs. Les **767 passes / 2 ignores** et l'echec des trois premiers tests sans correctif restent des declarations du contributeur, non reproduites dans cette revue.

Les cinq tests ajoutent une valeur reelle : ils observent les nombres d'ouverture/fermeture, et pour certaines sorties de sleep les etats de chauffe et d'activite. Ils ne testent pas une chaudiere centrale effective ni un delai de retour Zigbee2MQTT. Leur helper force directement les deux horodatages, ce qui reproduit le verrou temporel mais pas son etablissement naturel en conditions reelles.

### Verifications prioritaires avant beta

1. Resoudre le conflit sans perte des changements actuels, puis rejouer les cinq tests et la suite existante de regulation, notamment le test de periode minimale.
2. Ajouter les tests discriminants de dpercent et de reprise de cadence ; tester petite variation, zero, 100 %, et ouverture identique au changement de mode.
3. Tester la derniere demande gagnante avec services suspendus et plusieurs vannes ; distinguer appels successifs rapides et appels reellement concurrents.
4. Tester l'absence puis le retour de temperature, et verifier que OFF conserve ses garanties via le flux complet.
5. Rejouer inhibition, recalibrage, redemarrage avec degres unknown (#2049), fenetre, securite, central et suite globale sur le commit final. Ajouter une transition sleep dans ces matrices lorsqu'elle n'est pas couverte.
6. Tester `cool -> sleep -> cool` si cette configuration est declaree supportee dans la release.

### Protocole beta propose

- Revision immuable rebassee sur la version stable actuelle, identifiee dans le retour de test ; aucune autre correction fonctionnelle melangee.
- Une a deux semaines sur les 13 TRV proposees, avec transitions quotidiennes et exercice hebdomadaire, plus un redemarrage controle.
- Relever mode demande/effectif, temperatures, `on_percent`, ouverture logique, deux nombres physiques, `hvac_action`, appareils actifs, chaudiere et chronologie des commandes Zigbee2MQTT.
- Exiger une fermeture coherente avec la conversion configuree lors du retour dans une piece chaude, puis la convergence des attributs apres retour des etats physiques. Ne pas exiger un retour radio synchrone au service HA.
- Aucun ordre de vanne parasite a mode constant, aucun ordre pendant inhibition hors transaction autorisee, reprise correcte a sa levee.
- Arreter la beta en cas de chauffe persistante injustifiee, de position finale contraire a la derniere demande ou de violation d'inhibition ; conserver les traces et revenir a la stable.

## Alternatives examinees

| Option                                             | Avantage                                                                 | Inconvenient / recommendation                                                                                                                 |
| -------------------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Conserver les deux memoires de mode                | Exception locale dans la classe proprietaire ; distingue calcul et envoi | Option raisonnable ; revalider concurrence, filtres et limites avant fusion.                                                                  |
| Forcer `update_states(force=True)` autour de sleep | Intention courte et centralisee                                          | Le force se propage au controle/scheduler ; le filtre dpercent actuel ne teste pas force. Pas une simplification automatiquement equivalente. |
| Mettre le cache a zero en OFF                      | Evite une reouverture obsolete apres OFF dans certains cas               | Ne corrige pas toutes les transitions directes de sleep ; insuffisant seul.                                                                   |
| Limiter le contournement a sleep                   | Reduit le changement de cadence hors sleep                               | Doit encore gerer sleep -> off -> heat et toute reprise avec cache obsolete ; demande une conception validee, pas un ajustement opportuniste. |
| Automatisation verifiant aussi `on_percent > 0`    | Contournement de pompe a chaleur deja utilise par le declarant           | Ne corrige pas la vanne ; ne pas en faire une solution generale pour la chaudiere du projet.                                                  |

## Perimetre et questions de decision

**Inclus propose :** regulateur direct de vanne, transitions effectives HVAC, valeur a recalculer et appliquer immediatement quand les donnees existent, conservation du filtrage hors transition et des protections.

**Exclus :** refonte de concurrence de tout le thermostat, changement de TPI, nouvelle politique de securite sans temperature, autres types de thermostat et modification d'environnement HA. Un defaut reproductible decouvert sur ces surfaces doit etre qualifie avant toute extension du perimetre.

Questions a trancher :

1. Le mainteneur confirme-t-il l'exception de cadence pour toutes les transitions effectives, y compris les reprises automatiques hors sleep ?
2. Quel comportement accepte-t-on a la sortie de sleep si le calcul est indisponible : conserver la politique existante en le documentant, ou traiter cela dans un changement distinct ?
3. Qui fournit les traces beta et valide la chaudiere ainsi que la reprise apres redemarrage/inhibition ?

## Suite et criteres de passage

**Recommandation : retenir le correctif, differer la fusion.** Le conflit et la validation de sa resolution sont des bloqueurs factuels. Les limites ci-dessus sont des demandes de preuve ou de clarification, pas des regressions nouvelles presentees comme demontrees.

Apres approbation explicite de ce rapport, faire converger specification et conception sur le perimetre et les cas limites. Presenter leurs resultats et obtenir un second accord explicite avant tout developpement. Aucun agent de developpement n'a ete lance.

Passage a la fusion seulement apres revue du commit final, tests prioritaires et suite globale reussis, decisions de comportement explicites et retour beta documente satisfaisant les criteres ci-dessus.

## Sources

- [Issue #2111](https://github.com/jmcollin78/versatile_thermostat/issues/2111), [PR #2113](https://github.com/jmcollin78/versatile_thermostat/pull/2113), leurs descriptions et commentaires accessibles.
- [Metadonnees PR](https://api.github.com/repos/jmcollin78/versatile_thermostat/pulls/2113), [diff](https://patch-diff.githubusercontent.com/raw/jmcollin78/versatile_thermostat/pull/2113.diff), [checks du commit](https://api.github.com/repos/jmcollin78/versatile_thermostat/commits/f19d5aa8e6ec2c0dee45af71f632748b8aa4c1fd/check-runs).
- [Version exacte du regulateur dans la PR](https://github.com/jmcollin78/versatile_thermostat/blob/f19d5aa8e6ec2c0dee45af71f632748b8aa4c1fd/custom_components/versatile_thermostat/thermostat_climate_valve.py#L244).
- Code local : [update_states](../../custom_components/versatile_thermostat/base_thermostat.py#L1768), [controle over_climate](../../custom_components/versatile_thermostat/thermostat_climate.py#L856), [recalcul proportionnel](../../custom_components/versatile_thermostat/thermostat_prop.py#L223), [handler TPI](../../custom_components/versatile_thermostat/prop_handler_tpi.py#L355).
- Tests locaux consultes : [periode minimale](../../tests/test_overclimate_valve.py#L782), [inhibition avec regulation](../../tests/test_inhibition.py#L942), [concurrence pendant sortie d'inhibition](../../tests/test_inhibition.py#L1426).

**Limites de verification :** outils d'execution terminal/Python indisponibles dans cette session ; aucun pytest, reproducteur dynamique ou essai materiel execute. Les liens locaux documentent le code lu, pas le resultat garanti d'une future resolution de conflit.