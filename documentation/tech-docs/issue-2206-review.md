# Revue de l'issue #2206

## Reference et recommandation

- Issue : [#2206 - Energy sensor: burst of identical cycle increments during overpowering](https://github.com/jmcollin78/versatile_thermostat/issues/2206).
- Revue : 2026-11-16. Statut : analyse approuvee pour specification et conception ; convergence documentaire atteinte, perimetre final et developpement en attente de validation humaine. Aucun correctif implemente.
- Recommandation : **retenir l'anomalie et reevaluer la priorite P2**. Le probleme ne se limite pas a l'affichage : la reentrance du controle de chauffe et les rafales de fins de cycle affectent aussi l'ordonnancement, les callbacks Auto TPI et les publications HA. Une chauffe physique incorrecte n'est toutefois pas demontree.

## Resume du signalement

## Jalon specification et conception du 2026-11-16

L'utilisateur a explicitement autorise la specification et la conception, avec une priorite supplementaire : rechercher la plus petite cause et la solution la moins risquee dans cette partie critique. Les documents suivants sont des propositions convergentes, pas une autorisation de developper :

- [Specification fonctionnelle 0.2 FR/EN](issue-2206-specification.md).
- [Conception detaillee 0.2 FR/EN](issue-2206-design.md).

**Option A recommandee :** supprimer le rappel positif du controle de chauffe depuis le refus TPI, sans supprimer la propagation du preset, de la consigne et des priorites. Ensuite, consommer le retour explicite `False` de `turn_on()` et remonter l'abandon jusqu'a `start_cycle`, avant toute nouvelle commande ON, marquage ON, installation de tick/fin ou hook puissance post-refus. Si le refus survient alors que le delestage etait deja actif, nettoyer le cycle encore courant avec l'OFF collectif existant ; ne pas laisser un autre relais ON sans arret programme. Le premier refus conserve son OFF collectif, sans le doubler inutilement. La reprise utilise le controle periodique et la vraie sortie centrale existants.

Surface envisagee : quatre fichiers, six fonctions existantes et un auxiliaire prive. Aucun changement de seuil, reservation, formule energetique, machine d'etat, handler TPI ou schema persiste. Pas de verrou, tache differee, generation de timers ni remaniement general de l'annulation. Une comparaison locale d'identite de `_states` sert seulement a eviter que le nettoyage du refus annule un cycle remplacant ; elle n'est pas une garantie generale de concurrence.

**Reduction proposee par rapport aux sections initiales ci-dessous :** le montant energetique brut/applique, notamment les 5,833 Wh a 0 % applique, est reporte dans un lot distinct P1. La defense generale contre remplacements suspendus, hooks reentrants, doubles annulations, callbacks deja distribues et retrait pendant operation suspendue est exclue du lot A. Ces courses restent des risques residuels, pas des problemes demontres resolus. Le lot vise les rafales issues du refus reel a partir d'un ordonnanceur sans timers deja orphelins. L'abandon peut aussi interrompre une tentative deja delestee et attendre le prochain controle legitime : ce comportement et les reductions demandent une validation finale explicite.

La premiere conception, plus large, a ete ecartee lors de la convergence pour limiter la surface de regression. Au terme de trois cycles au maximum, les deux agents confirment explicitement le meme perimetre A, la couverture conceptuelle des 12 exigences, 9 regles et 13 criteres, l'absence de contradiction bloquante et la faisabilite/testabilite statiques. Aucun test applicatif n'a ete execute ; la cause et le correctif ne sont donc pas prouves par execution. Les guides HA demandes par l'agent de conception etaient inaccessibles via MCP ; aucun controle HA n'a ete effectue.

**Gate obligatoire du futur developpement :** reproduction bornee du premier refus avec vrais sous-jacent/gestionnaire/propagation/TPI/scheduler, handles distincts et decompte des timers actifs. Couvrir partiel/100 %, mono/multi, deja deleste coherent/incoherent, OFF pendant refus, gates, retours `None` et erreurs, reprise et callbacks legitimes. Un timer actif non reference apres le premier refus falsifie l'option A : revenir au chemin local et demander un nouvel arbitrage avant tout elargissement. Ni l'idempotence du seul deuxieme refus ni une baisse des logs ne suffisent.

**Action suivante :** faire approuver les documents 0.2, l'option A et ses exclusions, le report P1 et l'abandon propre, puis obtenir une autorisation distincte de developper. Les sections suivantes conservent le diagnostic et les recommandations initiales ; lorsqu'elles proposent un perimetre plus large, la proposition finale de ce jalon est celle soumise a validation.

## Signalement initial

Le rapporteur utilise un `over_switch` TPI de 3 500 W, cycle de cinq minutes, avec un unique sous-jacent `climate.zone_studio` pilote par commandes virtuelles. Le seuil de puissance est 11 000 ; la mesure provient de la puissance apparente Linky. Le preset de delestage vaut 13 degres et la duree minimale d'activation dix secondes.

L'anomalie, initialement signalee sous 10.6.2 avec HA 2026.11.0, persiste selon les commentaires sous 10.6.4 et 10.6.5 avec HA 2026.11.1. Des increments d'energie en rafale commencent pendant le delestage et peuvent persister apres sa fin. Un second VTherm de 750 W est egalement concerne selon le rapporteur. Le dernier commentaire fournit deux exports du 16 novembre : boucle de controle pendant le delestage puis rafales d'energie avec cycles a zero chauffe appliquee.

Les volumes annonces (12 399 repetitions, environ 20 500 changements d'etat en onze minutes, hausses apres restauration) proviennent du commentaire de l'auteur ; ils n'ont pas ete recalcules sur les fichiers complets.

## Sources et limites

- Description, commentaires et metadonnees accessibles de l'issue consultes. Etiquettes affichees : `P2` et `question`. Aucun lien de developpement ni relation formelle affiche ; cela ne constitue pas une recherche exhaustive de doublons.
- Deux extraits joints par l'utilisateur : `...201556.log`, a partir de 20:11:36 UTC, et `...202615.log`, a partir de 20:21:51 UTC. Les en-tetes annoncent respectivement 83 200 et 99 662 entrees. Les pieces jointes sont fournies sous forme resumee, avec configuration omise : ni analyse exhaustive ni inspection du graphique realisees.
- Code local : [underlyings.py](../../custom_components/versatile_thermostat/underlyings.py), [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py), [state_manager.py](../../custom_components/versatile_thermostat/state_manager.py), [vtherm_state.py](../../custom_components/versatile_thermostat/vtherm_state.py), [prop_handler_tpi.py](../../custom_components/versatile_thermostat/prop_handler_tpi.py), [cycle_scheduler.py](../../custom_components/versatile_thermostat/cycle_scheduler.py), [thermostat_switch.py](../../custom_components/versatile_thermostat/thermostat_switch.py), [feature_power_manager.py](../../custom_components/versatile_thermostat/feature_power_manager.py).
- Le manifeste local annonce 10.6.6. Les fichiers publics `underlyings.py` et `cycle_scheduler.py` du tag `10.6.5` ont aussi ete consultes : les chemins critiques de refus, de demarrage force, de creation des timers et d'increment y sont presents. Les autres fichiers n'ont pas tous ete compares a ce tag.
- Documents locaux consultes : [revue #2109](issue-2109-review.md), limitee au point 1.1 et excluant explicitement les rafales du point 1.2 ; [revue #2145](issue-2145-review.md), concernant surtout la puissance marginale de relais deja actifs, pas cette reentrance.
- Tests consultes : [test_cycle_scheduler.py](../../tests/test_cycle_scheduler.py), notamment `TestMasterCycleEnd`. Ces tests verifient un increment par invocation du callback, sans simuler une generation perimee de timer ni le refus reentrant reel. Aucune execution de test : aucun outil terminal/runtime disponible dans cette session. Aucun environnement HA modifie.

## Diagnostic : faits verifies

### 1. Le refus de demarrage est normal, sa reaction ne l'est pas

Le premier extrait donne `current_power=7600`, `startup_power=3500`, `max_power=11000`, sans reservation pendante. Le controle strict demande `7600 + 3500 < 11000`, ce qui est faux. Il ne faut donc pas corriger le probleme en autorisant ce demarrage ou en moyennant la puissance instantanee par le taux TPI.

Le preset `power` ne signifie pas un arret HVAC : le gestionnaire d'etat conserve `heat` et impose une consigne reduite. A 11,9 degres pour une consigne de 13, le premier extrait montre une demande TPI de 66 %, soit 198 s de chauffe sur 300 s. Le scheduler tente donc encore un demarrage qui sera refuse tant que la puissance manque.

### 2. Un chemin de reentrance directe est present

La chaine d'appels verifiee dans le code local est :

```text
CycleScheduler.start_cycle(...)
  -> _start_cycle_switch(...) -> _tick(initial=True)
  -> UnderlyingSwitch.turn_on()
  -> check_overpowering() -> set_overpowering(True)
  -> requested_state.force_changed()
  -> update_states(force=True)
  -> recalculate() -> async_control_heating(force=True)
  -> TPIHandler.control_heating(...)
  -> CycleScheduler.start_cycle(..., force=True)
```

`set_overpowering(True)` est deja idempotent : lorsque le delestage est actif, il retourne sans refaire la transition. Mais `UnderlyingSwitch.turn_on()` force quand meme le recalcul d'etat apres **chaque** refus. L'idempotence de ce seul gestionnaire ne suffit donc pas.

Les indicateurs `current_state.is_*_changed` restent positionnes jusqu'a la fin de `update_states()`, apres l'attente de `async_control_heating()`. Les setters de `VThermState` conservent un indicateur deja vrai avec un OU logique. Un appel imbrique peut ainsi voir encore le meme preset et la meme consigne comme modifies, avant que l'appel parent n'ait atteint `reset_changed()`.

Les gardes `_is_starting` et `_is_cancelling` ne verrouillent pas les transitions. Elles alimentent `is_cycle_running`, mais la branche evitant un nouveau demarrage est conditionnee par `not force`. Le chemin fautif passe precisement avec `force=True`.

Cette chaine correspond a l'ordre des messages du premier extrait. Elle constitue un diagnostic fortement etaye, mais n'a pas ete reproduite en execution dans cette session.

### 3. L'energie est creditee par callback, pas par temps effectivement ecoule

`_on_master_cycle_end()` teste seulement `is_cycle_running`, appelle `incremente_energy()`, puis redemarre avec `force=True` et `_from_cycle_end=True`. Il n'identifie pas la generation du timer appele et ne verifie pas qu'un cycle complet vient de se terminer. `repeat=True` dans le commentaire est coherent avec ce chemin automatique, et non uniquement avec des mises a jour de preset.

`ThermostatOverSwitch.incremente_energy()` utilise `mean_cycle_power * cycle_min / 60`. Or `mean_cycle_power` utilise le taux **brut de l'algorithme**, pas le taux effectivement applique par le scheduler. Le deuxieme extrait et le dernier commentaire indiquent une demande de 2 %, appliquee a 0 % :

```text
300 s * 0,02 = 6 s < minimum d'activation de 10 s
=> on_time_sec = 0, off_time_sec = 300
3500 W * 0,02 * 5 min / 60 = 5,833333 Wh
```

Cela explique exactement les increments de 5,833 Wh alors que le cycle applique zero chauffe. Deux anomalies s'additionnent : un nombre anormal de callbacks, et une energie fondee sur une demande non executee. Meme sans rafale, cette derniere incoherence peut produire un petit surcomptage par cycle.

Contrairement a la formulation du commentaire, **l'annulation seule n'incremente pas directement l'energie** dans le code consulte : c'est le callback de fin de cycle qui le fait.

## Persistance apres delestage : hypothese principale

Le scheduler attend `under.turn_on()` avant d'installer ses timers. Un demarrage reentrant peut annuler le cycle parent alors que ses timers n'existent pas encore. Si plusieurs appels imbriques reprennent ensuite, chacun peut installer un timer et ecraser `_cycle_end_unsub` et `_tick_unsub`, uniques references d'annulation. Les timers precedents deviennent alors orphelins du point de vue du scheduler.

Un ancien callback ne porte aucune generation de cycle. Tant qu'un cycle quelconque est actif, il peut crediter l'energie et redemarrer un nouveau cycle. De nombreux timers survivants peuvent ainsi entretenir des rafales, y compris apres disparition du manque de puissance et a zero chauffe appliquee.

**Niveau de preuve :** la vulnerabilite structurelle est visible dans le code ; le mecanisme exact de sortie de l'imbrication et le nombre de timers survivants ne sont pas observes dans les extraits. `_tick()` intercepte les exceptions de `turn_on()` : une erreur de profondeur de recursion est une possibilite, pas un fait constate. Ne pas affirmer qu'une telle exception figure dans les logs sans consulter le fichier complet.

**Verification discriminante a realiser :** utiliser un faux sous-jacent qui redemarre le scheduler une seule fois depuis son premier `turn_on()`, puis laisse les deux appels revenir. Compter les timers encore actifs. Declencher ensuite l'ancien callback apres remplacement du cycle et verifier s'il incremente l'energie ou redemarre le cycle courant. Ce test borne permet de confirmer ou de refuter l'hypothese sans provoquer une recursion illimitee.

L'augmentation observee a la restauration HA reste une question distincte : les extraits ne permettent pas d'attribuer le saut au recorder, a la restauration, ou a des publications differant du total interne. Ne pas conclure a un deuxieme credit volontaire au demarrage sans preuve.

## Perimetre propose

Inclus : reproduction bornee de la reentrance sur refus de puissance ; traitement idempotent des refus repetes sans cycle recursif ; cycle de vie des timers resistant aux appels imbriques et callbacks perimes ; unicite des fins de cycle et du credit d'energie ; energie coherente avec la chauffe appliquee, notamment sous le minimum d'activation ; tests de sortie du delestage et d'arret/rechargement.

Exclus : modification des seuils, des priorites de delestage ou des coefficients TPI ; suppression generale de la chauffe au preset `power` ; desactivation arbitraire des callbacks de plugins ; correction automatique des statistiques historiques ; reparation du saut a la restauration sans reproduction ; changement global de modele de mesure electrique. Le mauvais libelle `total_energy_unit=W` mentionne dans l'issue doit etre verifie et cadre separement, pas confondu avec la rafale.

## Impacts et risques

| Impact ou risque                                     | Gravite                | Probabilite / niveau de preuve                                 | Mesure proposee                                            |
| ---------------------------------------------------- | ---------------------- | -------------------------------------------------------------- | ---------------------------------------------------------- |
| Statistiques d'energie fortement fausses             | Haute pour les donnees | Rafales visibles ; totaux historiques rapportes                | Un seul credit par cycle valide ; pas de migration aveugle |
| Charge CPU, recorder, memoire des logs               | Moyenne a haute        | Haute pendant la boucle ; cout machine non mesure              | Borner controle et timers ; verifier les publications      |
| Perturbation du controle de chauffe et d'Auto TPI    | Haute potentielle      | Annulations visibles ; chauffe physique incorrecte non prouvee | Tester commandes appliquees, reprise et callbacks          |
| Desactivation du delestage pour contourner           | Haute potentielle      | Depend de l'installation                                       | Ne pas proposer sans protection externe adaptee            |
| Verrou async tenu pendant un rappel reentrant        | Haute                  | Risque de conception                                           | Ne pas attendre le meme verrou depuis son propre callback  |
| Double comptage ou perte d'energie aux interruptions | Moyenne                | Possible avec une correction partielle                         | Definir le traitement temporel des interruptions           |

Compatibilite : viser aucun changement de configuration ni d'API publique ; conserver les commandes virtuelles, relais inverses, multi-relais et hooks externes. Le schema persiste ne devrait pas changer, sous reserve de la conception. Documentation : notes de version et limites de l'estimation energetique a mettre a jour lors du correctif. Confidentialite : journaux contenant des identifiants d'entites et habitudes d'occupation ; ne pas recopier une configuration ou un identifiant Linky complet. Aucun probleme de securite informatique exploitable n'est demontre. Les VA Linky et W configures ne constituent pas une mesure physique identique ni une garantie de protection electrique.

## Alternatives et contournements

- Corriger seulement `incremente_energy()` : reduit un symptome, mais laisse les cycles, callbacks et publications en rafale. Insuffisant.
- Eviter le recalcul reentrant seulement sur refus deja traite : cible le declencheur, mais laisse d'autres appels imbriques ou timers perimes possibles. A combiner avec des invariants du scheduler.
- Utiliser generation de cycle, invalidation des anciens callbacks et traitement differe/coalescent des commandes reentrantes : option recommandee a etudier en conception ; attention a ne pas perdre une vraie commande d'arret ou de securite.
- Redemarrage HA : interruption temporaire de l'etat en memoire rapportee par l'auteur, sans prevention de recurrence ni reparation des statistiques. Rechargement de l'integration non verifie comme contournement fiable.
- Masquer le capteur d'energie ou reduire le niveau de logs : ne supprime pas la boucle. Augmenter encore la retention des logs peut accroitre la memoire sans conserver le debut d'incident si le tampon est sature.

## Decisions et passage au developpement

Questions ouvertes : confirmer par reproduction les timers survivants ; examiner les erreurs presentes dans les exports complets ; determiner si le saut de restauration necessite un ticket distinct. Le declencheur initial precedent 20:11:36 n'est pas disponible dans les extraits. Ces limites n'empechent pas de specifier une reproduction ciblee, mais interdisent de presenter un correctif comme deja valide.

1. Obtenir l'approbation explicite du present rapport et du perimetre propose avant specification et conception.
2. Faire converger les documents specialises, notamment sur les appels reentrants, les priorites d'arret et la base temporelle du calcul d'energie. Un simple verrou ne suffit pas a definir le comportement.
3. Exiger une reproduction bornee avant correction ; un refus repete deja traite ne doit pas entretenir d'appels imbriques ; un ancien timer ne doit ni crediter ni relancer le cycle courant.
4. Verifier qu'un cycle de 300 s n'est credite qu'une fois ; une demande de 2 % rejetee par le minimum de 10 s n'ajoute pas 5,833 Wh ; sortie de delestage, arret, reprise, hooks et cas multi-relais restent coherents.
5. Obtenir une autorisation distincte sur les specifications et la conception avant toute implementation. Aucune specification detaillee ni implementation n'est autorisee par ce rapport seul.