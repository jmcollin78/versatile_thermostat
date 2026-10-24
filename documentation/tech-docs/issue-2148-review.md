# Revue de l'issue #2148

**Issue :** [#2148 - When a VTherm is stopped by auto-start/stop the preset change is not visible](https://github.com/jmcollin78/versatile_thermostat/issues/2148)  
**Statut :** rapport approuve par l'utilisateur pour la specification et la conception le 2026-10-24 ; developpement non autorise.  
**Recommandation :** retenir le probleme, demander une reproduction instrumentee avant de fixer la couche a corriger.

## Resume et sources verifiees

@jmcollin78 signale qu'avec un VTherm mis sur `off` par auto-start/stop, changer le preset ne met a jour ni le preset ni la temperature cible visibles dans la carte VTherm UI. Desactiver auto-start/stop rend ensuite le nouveau preset et la nouvelle consigne visibles et pris en compte. Le probleme est rapporte sur la version 10.6.1 ; son caractere regressif est suspecte par l'auteur, non demontre.

- [Issue #2148](https://github.com/jmcollin78/versatile_thermostat/issues/2148) : ouverte, etiquettes `bug` et `P1`, sans commentaire, assignation, jalon, relation ou PR associee visible au moment de la revue. Aucune capture, trace ou description du type de VTherm n'est fournie.
- [manifest.json](../../custom_components/versatile_thermostat/manifest.json) : version locale `10.6.1`, conforme a la version citee ; cela ne prouve pas que la copie locale correspond exactement a l'installation du rapporteur.
- [base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py) : `async_set_preset_mode` valide et enregistre le preset demande, puis force `update_states`. Cette methode calcule le nouvel etat, affecte les attributs preset/temperature lorsqu'ils changent et appelle `async_write_ha_state`.
- [state_manager.py](../../custom_components/versatile_thermostat/state_manager.py) : l'auto-stop force le mode HVAC courant sur `off` sans effacer le mode demande ; le calcul du preset reprend normalement le preset demande, puis celui de la consigne utilise le preset courant. Les priorites puissance, securite, mode central, fenetre, presence, mouvement et preset temporise peuvent toutefois modifier ces valeurs.
- [feature_auto_start_stop_manager.py](../../custom_components/versatile_thermostat/feature_auto_start_stop_manager.py) : la detection d'arret lit la consigne courante ; la desactivation de la fonction force une nouvelle mise a jour de l'etat.
- [test_auto_start_stop.py](../../tests/test_auto_start_stop.py) : un scenario change `eco` vers `boost` apres auto-stop, mais attend que VTherm redemarre ; il ne couvre pas un changement de preset avec maintien durable sur `off` ni la valeur effectivement publiee dans l'entite HA.
- [test_auto_start_stop_stop_mode.py](../../tests/test_auto_start_stop_stop_mode.py) et [feature-auto-start-stop.md](../fr/feature-auto-start-stop.md) : le mode d'arret peut aussi etre `fan_only` ou `dry`, selon l'equipement ; l'issue mentionne explicitement `off`.

Aucun test d'integration ni essai sur une carte VTherm UI n'a ete execute pendant cette revue. Aucune recherche exhaustive de doublons dans les issues ou PR n'a ete effectuee ; aucun travail lie n'est indique sur la page de l'issue.

## Pertinence et perimetre propose

**Retenir, sous reserve d'identifier la couche defaillante.** La visibilite immediate de la consigne programmee pendant un arret automatique permet de comprendre le comportement futur du thermostat. L'issue est coherente avec l'auto-start/stop documente et priorisee `P1` par le depot. Le chemin du code inspecte suggere qu'une mise a jour devrait avoir lieu, ce qui interdit d'attribuer sans preuve le defaut a `StateManager` plutot qu'a la publication HA, a une combinaison d'options ou a la carte UI.

**Inclus :** reproduire `off` automatique, changer de preset sans provoquer un redemarrage, comparer `requested_state`, `current_state`, `preset_mode` et `temperature` de l'entite `climate` HA avec l'affichage de la carte ; corriger la couche responsable apres confirmation, puis tester l'affichage immediat et la reprise ulterieure. Couvrir au minimum `over_climate` si reproductible, et etendre aux autres types partageant le meme chemin uniquement si necessaire.

**Exclus :** changer l'algorithme d'arret ou les seuils de redemarrage sans demonstration de causalite ; forcer la remise en chauffe a chaque changement de preset ; refondre la carte UI, les autres motifs d'arret, les modes `fan_only`/`dry`, ou les integrations sous-jacentes hors besoin prouve. La carte UI est un composant externe : toute correction de ce cote necessitera un perimetre et un depot distincts.

## Impacts et risques

| Domaine / risque | Gravite | Probabilite | Mesure proposee |
| --- | --- | --- | --- |
| Consigne programmee invisible pendant l'arret, risque de mauvaise interpretation | Moyenne | Rapportee dans l'issue ; non reproduite ici | Verification des attributs HA et de la carte dans la meme sequence |
| Correction qui relance le chauffage alors que l'auto-stop doit rester actif | Haute | Plausible si on modifie la logique de mode ou de detection | Test avec preset modifie mais conditions d'auto-stop toujours presentes |
| Divergence entre etat demande, etat courant et attributs publies | Moyenne | Inconnue | Assertions des trois surfaces, y compris apres desactivation ou redemarrage automatique |
| Impact sur types de VTherm et priorites de fonctionnalites partagees | Moyenne | Conditionnelle au choix de la correction | Tests cibles puis tests voisins des modes et priorites concernees |
| Defaut uniquement dans la carte externe et non dans l'integration | Moyenne pour l'orientation du travail | Inconnue | Verifier l'etat brut de l'entite HA avant toute modification de l'integration |

**Securite et confidentialite :** aucune nouvelle collecte de donnees ni permission n'est envisagee. Pour diagnostiquer, des attributs et journaux expurges suffisent ; ne pas demander de secrets. **Compatibilite et migration :** conserver les services et attributs existants ; aucune migration, dependance ou modification de configuration n'est envisagee a ce stade. **Exploitation :** un test HA sur une instance de developpement et la carte, s'il est autorise ulterieurement, devra eviter toute action sur les equipements reels. **Documentation :** clarifier, si le comportement n'est pas deja explicite, que la consigne reste visible et editable pendant l'auto-stop ; ajouter une note de correction dans les notes de version selon les usages du depot.

## Alternatives et contournements

| Option | Avantage | Limite |
| --- | --- | --- |
| Corriger le calcul/publication de l'entite si ses attributs restent anciens | Traite la source d'etat pour tous les consommateurs | Risque de regression fonctionnelle ; doit etre confirme par un test |
| Corriger la carte si les attributs HA sont deja a jour | Correction localisee de l'affichage | Hors de ce depot ; ne regle pas une entite HA incorrecte |
| Desactiver temporairement auto-start/stop pour verifier la consigne | Contournement deja rapporte | Peut relancer le chauffage et ne constitue pas une correction |
| Forcer le redemarrage au changement de preset | Affiche indirectement les nouvelles valeurs | Change la regulation et peut allumer un equipement a tort ; a ecarter |

## Faits, hypotheses et decisions necessaires

**Faits :** l'issue decrit un ecart d'affichage avec `off` automatique en 10.6.1 ; la copie du code examinee contient un chemin de mise a jour de l'etat et des tests proches, mais pas le cas ou le VTherm reste arrete apres le changement de preset.

**Hypothese falsifiable :** dans le scenario qui reste `off`, le preset demande change mais une valeur publiee ou lue par la carte reste ancienne. Le controle le moins couteux est un scenario de test HA sur l'entite VTherm, avec un nouveau preset dont la consigne reste sous la temperature ambiante, comparant les deux etats internes aux attributs HA immediatement apres la commande. Si ces attributs sont a jour, la piste prioritaire devient la carte UI et non le calcul du thermostat.

**Questions ouvertes, non bloquantes pour valider la revue mais bloquantes pour choisir le correctif :** quel type de VTherm, quels presets et temperatures, quelle version de HA et de carte UI, et par quel service ou interaction le preset est-il modifie ? Les attributs bruts HA sont-ils incorrects ou seule la carte les masque-t-elle en mode `off` ? La reproduction persiste-t-elle avec mode central, fenetre, securite, presence ou preset temporise actifs ? Une version precedente connue fonctionnait-elle ?

## Suite et criteres de passage au developpement

1. Faire approuver explicitement ce rapport et autoriser la phase de specification et conception.
2. Obtenir un scenario reproductible et trancher, par inspection des etats et attributs HA, entre defaut de l'integration et defaut de carte. Si ce dernier est seul concerne, faire valider le changement de depot et de perimetre avant tout developpement.
3. Faire converger specification fonctionnelle et conception sur la visibilite du preset et de la consigne en mode `off`, les exceptions de priorite deja existantes, la non-relance involontaire et les criteres de tests.
4. Presenter les documents convergents, les risques residuels et demander une seconde autorisation explicite de developper.
5. Apres autorisation seulement, implementer et verifier au minimum : changement de preset restant en auto-stop `off`, attributs `climate`/carte selon la couche retenue, reprise ou desactivation ulterieure, et absence de regression du scenario existant de redemarrage au changement de preset.