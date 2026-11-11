# Revue commune des issues #2219 et #2223 : securite et adoption des sous-jacents

## Statut et recommandation

- Date de revue : 10 novembre 2026.
- Jalon : documents communs valides par le mainteneur ; developpement et validation automatisee autorises sur une branche dediee.
- **Autorisation du 10 novembre 2026 :** le mainteneur demande de creer une nouvelle branche, committer les trois documents et lancer le developpement. Cet accord porte sur la specification v0.3 et la conception v0.2 convergentes, sans nouvelle API ni changement de plugin. Aucun push, deploiement ou commande d'equipement reel n'est autorise.
- **Accord utilisateur du 10 novembre 2026 :** "Go pour spec", en reponse a la demande d'approbation du rapport commun et d'autorisation de specification/conception. Cet accord ne vaut pas autorisation de developpement.
- **Regroupement demande par le mainteneur :** traiter #2219 et #2223 comme une seule demande, avec un rapport, une specification, une conception, une implementation et une campagne finale de tests communs. Cette precision de perimetre ne vaut pas approbation du rapport ni autorisation de specification/conception ou de developpement.
- **Recommandation : retenir la demande commune**, en corrigeant la decision de reparation lorsque le parent est OFF et en documentant un amorcage passif a trois etats, sans nouvelle interface publique.
- **Nouvelle proposition du mainteneur du 10 novembre 2026 :** initialiser `_is_on_part_running` a `None` ; une commande ON/OFF l'initialise, ou le premier etat logique connu du sous-jacent est adopte tant que l'attente reste `None`. Repair ne fait rien tant que cette attente est inconnue. Cette piste remplace la preference initiale pour une methode publique et vise a eviter des changements `vtherm_api` et la republication des plugins ; ces changements ne sont pas autorises dans la solution proposee.
- **Precision du mainteneur du 10 novembre 2026 :** #2221 a ete fermee par lui car jugee incomplete. Elle ne constitue ni une solution validee ni une correction dont la validation future peut etre supposee.
- Le nom de ce rapport est conserve pour stabiliser les liens ; son contenu couvre desormais les deux issues. Aucun second rapport n'est prevu pour #2219.
- L'implementation du perimetre valide et ses tests automatises simules sont autorises. Les changements de configuration, de dependances, de `vtherm_api` ou de plugins, ainsi que toute intervention sur une instance Home Assistant ou un equipement reel, restent exclus.
- Les mentions anterieures d'autorisation de developpement encore attendue retracent les phases documentaires precedentes ; le present accord les remplace sans certifier une implementation encore a realiser.

## References et resume de la demande commune

[Issue #2219](https://github.com/jmcollin78/versatile_thermostat/issues/2219), "[Safety] Internal state repair must not turn heating ON while VTherm is OFF" : ouverte lors de la consultation, etiquettes `bug` et `P0`.

Le mode OFF du thermostat parent doit interdire une reparation ON, meme si le sous-jacent conserve une ancienne intention ON. Si le sous-jacent est observe ON, la reparation doit viser OFF avant tout retour anticipe pour egalite entre attente et observation. Une observation inconnue ne prouve pas l'arret physique ; un mode parent inconnu n'autorise pas ON. Un passage du parent a OFF pendant une verification asynchrone doit invalider une action ON preparee auparavant.

#2219 rapporte un fonctionnement nocturne inattendu d'un poele et une reproduction isolee d'une decision de reparation dangereuse. Le lien causal complet avec l'incident reel et la formation de l'etat incoherent ne sont pas etablis. Sa reproduction a la version inspectee utilise un ancien chemin de decision ; la revision locale doit etre traitee a partir de son implementation actuelle, decrite ci-dessous.

[Issue #2223](https://github.com/jmcollin78/versatile_thermostat/issues/2223), "[Feature] Expose a public adoption contract for underlying switches" : ouverte, etiquette `enhancement`, assignee a `jmcollin78`, sans jalon ni branche ou PR affichee lors de la consultation.

Une integration externe regulant un VTherm `over_switch` doit pouvoir adopter un etat logique ON/OFF deja connu sans envoyer une commande physique. Cette adoption ne constitue pas une nouvelle transition. La reparation doit ensuite respecter l'etat adopte jusqu'a une commande ulterieure du VTherm, sans confondre un etat inconnu avec OFF et sans affaiblir la securite parent OFF de #2219.

L'auteur decrit une analyse des sources de VTherm 10.6.4, commit `bdef348b579b14d306291bb89099be01d9d2bc12`, avec HA 2026.11.0. Il ne revendique pas de reproduction du cycle complet sur une installation ou un equipement reel.

**Commentaire consulte :** @jmcollin78 propose d'etudier une alternative consistant a initialiser `_is_on_part_running` avec l'etat du switch au demarrage.

**Precision en conversation :** l'amorcage propose est differe, avec `None` comme attente non initialisee. Il ne consiste ni a lire une seule fois dans le constructeur, ni a adopter chaque changement en exploitation. La proposition convergente etablit l'attente de commande juste avant l'appel de service admissible, sans annoncer un ordre bloque comme applique ; une erreur apres appel conserve une intention emise non confirmee, pas une preuve d'application.

**Probleme commun :** distinguer l'observation reelle, l'etat attendu issu d'une commande ou d'une adoption, et l'intention effective de reparation apres application des contraintes de securite. Parent HEAT ne signifie pas automatiquement relais ON : les phases OFF, l'inhibition et les contraintes de regulation restent applicables.

## Sources et elements verifies

- Description, commentaire et metadonnees de [#2223](https://github.com/jmcollin78/versatile_thermostat/issues/2223), consultes le 10 novembre 2026.
- [#2219](https://github.com/jmcollin78/versatile_thermostat/issues/2219), ouverte, etiquettes `bug` et `P0` : demande un invariant de securite empechant une reparation ON lorsque le parent est OFF. La PR #2221 qui y est liee est fermee et jugee incomplete par le mainteneur.
- [PR #2221](https://github.com/jmcollin78/versatile_thermostat/pull/2221), description et diff consultes : proposition historique rejetee comme incomplete, et non solution retenue. La fermeture et son motif sont confirmes par le mainteneur dans cette conversation le 10 novembre 2026. Ses assertions de tests ne sont pas verifiees par cette revue. Sa description presente un lien causal avec l'incident plus affirmatif que #2219 ; cette causalite n'est pas retenue comme un fait etabli ici. Aucune validation future de cette PR n'est presumee.
- Revision locale : `5151bfef2fa5daa0bdd53007030f1d578a5362b3`. Arbre de travail propre avant creation de ce rapport. Ce n'est pas la revision 10.6.4 citee dans le ticket.
- [UnderlyingSwitch](../../custom_components/versatile_thermostat/underlyings.py#L376) : initialisation, lecture d'etat, commandes, keep-alive, resynchronisation d'inhibition et reparation.
- [Initialisation des sous-jacents](../../custom_components/versatile_thermostat/underlyings.py#L153) et [cache des etats](../../custom_components/versatile_thermostat/underlying_state_manager.py) : reception asynchrone de l'etat initial et des changements ulterieurs.
- [Gestionnaire de reparation](../../custom_components/versatile_thermostat/feature_repair_incorrect_state_manager.py) : activation optionnelle, readiness, delai initial, delegation aux sous-jacents et pause apres reparations consecutives.
- [Test du gestionnaire](../../tests/test_repair_incorrect_state_manager.py), [tests d'indisponibilite](../../tests/test_underlying_unavailable.py), [tests d'inhibition](../../tests/test_inhibition.py) et [tests de hooks](../../tests/test_underlying_hooks.py) : points de depart identifies pour la couverture ciblee.
- [Documentation technique des sous-jacents](underlyings.md) : document existant a faire evoluer avec le contrat retenu ; les sources sont prioritaires en cas d'ecart avec cette documentation.

La consultation couvre #2219 et #2223 comme sources du besoin commun, et #2221 uniquement comme proposition historique incomplete ; elle ne prouve pas l'absence de doublon dans tout le depot. Les integrations tierces et leurs cycles d'adoption n'ont pas ete audites exhaustivement.

## Analyse locale

### Faits observes dans les sources

1. `_is_on_part_running` est initialise a `False`. `turn_on()` et `turn_off()` le mettent a jour apres l'appel de service reussi ; un appel bloque ne suit pas ce chemin.
2. `UnderlyingSwitch.check_and_repair()` utilise directement ce drapeau comme etat attendu. Avec attendu OFF et etat reel ON, il appelle `turn_off()`.
3. La revision locale ne contient pas le garde-fou parent OFF demande par #2219, ni dans cette methode ni dans le gestionnaire qui la delegue. `check_initial_state()` protege le demarrage parent OFF, mais ne constitue pas un garde-fou de chaque reparation.
4. `is_device_active` renvoie `None` avant initialisation ou en l'absence d'un objet d'etat. Apres initialisation, il compare seulement la chaine observee a l'etat ON configure : `unknown`, `unavailable` ou une valeur non reconnue peuvent donc donner `False`.
5. Le cache conserve aussi les changements vers `unknown` et `unavailable`. Il ne faut pas se fier a la docstring de `_set_state`, qui dit encore qu'ils sont ignores.
6. La premiere initialisation est differee jusqu'a un etat disponible ; les notifications initiales sont programmees de facon asynchrone. Une lecture unique dans le constructeur peut preceder cette disponibilite.
7. `async_inhibition_resync()` recopie deja l'etat observe dans le drapeau, mais sa semantique et son rearmement du keep-alive sont lies a l'inhibition ; ce n'est pas un contrat general d'adoption.
8. Le keep-alive consulte aussi `_is_on_part_running`. Modifier le drapeau influence donc les commandes periodiques futures, meme si l'adoption elle-meme n'en emet aucune.
9. `build_command()` gere l'inversion et des commandes/etats virtuels. Le contrat doit porter sur l'activite logique, pas uniquement sur les chaines HA `on` et `off`.
10. Le retour anticipe de `check_and_repair()` couvre deja une attente `None`. En revanche, le ternaire du keep-alive l'assimilerait a `False`, et la resynchronisation d'inhibition utilise `is True` : ces chemins doivent preserver l'incertitude et ne pas fabriquer OFF.

### Hypothese et verification discriminante

**Hypothese locale commune :** utiliser directement un etat attendu non reconcilie avec l'adoption et l'autorite du parent permet deux erreurs opposees : arreter un relais ON legitime apres adoption passive, ou rallumer un relais a partir d'une attente ON perimee lorsque le parent est OFF. Une solution commune doit synchroniser l'attente lors de l'adoption et appliquer la securite parent OFF a l'intention effective de reparation. Initialiser le drapeau seul ou ajouter un garde-fou OFF seul ne couvre pas les deux besoins. Une lecture ponctuelle trop precoce ou une adoption tardive apres une commande peuvent aussi laisser subsister ou creer un conflit.

Verification economique tentee : executer en memoire les methodes reelles extraites des sources, avec observations construites et commandes remplacees par des mocks. Comparer attendu OFF/observe ON puis attendu ON/observe ON ; verifier aussi la lecture d'etats inconnus apres initialisation et le cas parent OFF/attendu ON/observe OFF. L'outil a retourne `outcome_unknown`, sans sortie enregistree : aucun resultat d'execution n'est donc etabli. La sonde ne contient aucun appel de service reel.

Cette sonde ne remplacera pas les tests du cycle HA complet : attente initiale `None`, premier etat connu ou commande, et reparation via le gestionnaire devenu eligible.

## Pertinence et faisabilite

La demande commune est coherente avec l'architecture `over_switch` et la regulation externe. Les deux issues touchent le meme chemin de decision et des etats partages ; les traiter ensemble limite les corrections contradictoires et permet une validation finale commune. La solution doit separer une observation adoptee d'un ordre physique, eviter les ecritures privees par les plugins et conserver la reparation automatique sans chauffage non demande.

Une evolution locale de `UnderlyingSwitch` parait faisable sans migration, nouvelle dependance, modification de `vtherm_api` ni republication de plugin. Le contrat supporte serait le cycle de vie documente d'amorcage, et non une methode publique supplementaire. Ce sont des hypotheses de conception, pas des garanties de compatibilite deja testees ; la conception doit verifier tous les lecteurs du drapeau et l'ordre des callbacks/commandes.

## Perimetre propose

- Inclure la correction de securite de #2219 dans la meme solution que l'adoption de #2223, sans attendre ni supposer la validation de #2221.
- Initialiser l'attente de chaque `UnderlyingSwitch` a `None` ; l'initialiser par une commande ou adopter une observation logique courante connue seulement si l'attente vaut encore `None`. Une fois connue, l'attente ne suit plus les derives observees.
- Tant que l'attente vaut `None`, ne rien emettre depuis repair ni keep-alive sur sa seule base ; conserver separement la securite initiale existante. Une fois l'attente connue, donner priorite au parent OFF avant la comparaison attendu/observe, sans deduire ON d'un parent inconnu et en revalidant apres preparation asynchrone.
- Documenter ce contrat de cycle de vie pour les sous-jacents `over_switch`, incluant ON, OFF et l'attente d'un etat disponible et interpretable, sans appel supplementaire d'un integrateur, nouvelle interface ou modification de `vtherm_api`.
- Faire de l'adoption une synchronisation logique sans service physique, sans notification de nouvelle transition ni reinitialisation des durees minimales comme si une commande venait d'etre emise.
- Conserver les commandes VTherm ulterieures comme autorite sur l'etat attendu. Definir comment une observation ou un rappel initial tardif ne peut pas ecraser une intention plus recente.
- Preserver inversion, switch virtuel, inhibition, keep-alive, reservations de puissance et ordonnanceur ; ne pas transformer chaque evenement HA en nouvelle intention adoptee.
- Rendre les tentatives et suppressions de reparation diagnostiquables : mode parent, mode du sous-jacent, attente effective, observation et direction de commande, sans saturation des journaux.
- Prevoir une seule campagne finale de tests commune : adoption puis reparation reellement eligible, commandes ulterieures et matrice de securite parent OFF. Conserver les verifications ciblees pendant le developpement, sans dupliquer deux campagnes completes par ticket.
- Completer la documentation technique existante avec le cycle de vie, sa disponibilite et ses limites ; documenter le changement d'amorcage pour tous les `over_switch`, y compris sans plugin.

**Exclusions :** nouvelle interface publique d'adoption, modification de `vtherm_api` ou republication de plugins pour ce besoin, modification de plugins tiers, regulation specifique aux poeles, refonte generale de l'API ou des etats, migration de configuration, desactivation de la reparation, changement global de la semantique d'annulation des cycles, commande d'un equipement reel.

**Securite incluse dans le perimetre commun :** #2219 n'est plus une dependance exterieure a resoudre separement. Sa correction et les garanties d'adoption de #2223 sont concues ensemble et doivent etre implementees puis testees ensemble. #2221 reste une proposition fermee comme incomplete, sans approche imposee ni validation future presumee. Le mainteneur a valide les documents et autorise ce developpement le 10 novembre 2026.

## Impacts et risques

Estimations qualitatives, sans mesure de frequence en production.

| Risque ou impact                                                                                | Gravite                          | Probabilite estimee                          | Traitement propose                                                                                                                                                |
| ----------------------------------------------------------------------------------------------- | -------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Adoption ON permettant une reparation ON alors que le parent est OFF                            | Critique : chauffage non demande | Plausible sans garde-fou, frequence inconnue | Parent OFF prioritaire sur toute intention adoptee ; couvrir #2219 dans la solution commune avec observe ON et OFF, sans presumer de solution validee dans #2221. |
| Etat inconnu pris pour OFF, ou etat virtuel mal interprete                                      | Elevee                           | Plausible d'apres la comparaison actuelle    | Accepter seulement un etat logique connu ; absence de mutation lors du report ; tests apres initialisation et au retour de disponibilite.                         |
| Adoption automatique repetee masquant une derive au lieu de la reparer                          | Elevee                           | Plausible si branchee a chaque evenement     | Adoption explicite ou amorcage unique strictement borne ; ne pas suivre automatiquement tout changement.                                                          |
| Notification initiale tardive ecrasant une commande recente                                     | Elevee                           | Possible, callbacks asynchrones              | Regle d'ordre et d'autorite a formaliser ; tests de commande avant et apres adoption.                                                                             |
| Parent passant a OFF pendant une preparation asynchrone de reparation ON                        | Critique : chauffage non demande | Possible, entrelacement a verifier           | Revalidation de l'autorite parent avant emission selon le modele de synchronisation existant ; test deterministe du changement de mode.                           |
| Modification des futures commandes keep-alive, de l'inhibition ou des reservations de puissance | Elevee                           | Possible : etat partage                      | Distinguer observation, commande et droits de commande ; tests cibles, sans contournement des contraintes existantes.                                             |
| Fausse transition redemarrant une duree minimale ou une comptabilisation                        | Moyenne a elevee                 | Inconnue pour les tiers                      | Aucune notification de commande sur adoption ; expliciter les responsabilites du consommateur.                                                                    |
| Changement de comportement au demarrage pour tous les VTherm `over_switch`                      | Moyenne                          | Certaine avec l'amorcage propose             | Documenter le cycle de vie et tester le demarrage avec/sans plugin, precoce/tardif, sans nouvel appel d'integration.                                              |
| Cout de coordination d'une nouvelle interface avec les plugins                                  | Moyenne                          | Evite par le choix propose, a verifier       | Ne pas ajouter d'API ; verifier que le cycle de vie suffit sans changement de `vtherm_api` ni republication des consommateurs.                                    |

Securite/confidentialite : aucun nouveau canal reseau, secret, stockage ou droit HA n'est requis a ce stade. Le risque principal est la commande involontaire d'un actionneur, pas une fuite de donnees. Aucune conclusion d'audit global de securite n'est revendiquee.

Compatibilite et exploitation : valider switch normal, inverse, virtuel et plusieurs sous-jacents ; verifier le demarrage tardif et le rechargement. Une adoption ne prouve pas un allumage physique et ne fournit pas son horodatage historique. La stabilite de l'API et les versions couvertes devront etre documentees. Aucune migration n'est anticipee pour un etat uniquement en memoire.

## Alternatives examinees

Les options d'adoption ci-dessous doivent toutes etre combinees au traitement complet de la securite de #2219. Corriger uniquement OFF ou uniquement l'adoption ne satisfait pas la demande commune. Deux correctifs independants avec campagnes finales dupliquees ne sont pas l'organisation retenue ; cela n'interdit pas plusieurs changements locaux ni leurs verifications ciblees au sein de la meme implementation.

1. **Attente initiale `None`, puis premiere commande ou premier etat connu.** Piste privilegiee apres la proposition du mainteneur : contrat de cycle de vie sans nouvelle API ni appel du plugin. Aucun repair tant que l'attente est inconnue ; adoption automatique seulement tant qu'elle reste inconnue, sans ecraser une commande. Verifier keep-alive, inhibition, etats virtuels, ordre des callbacks et securite initiale/parent OFF. Cette cible couvre aussi les VTherm sans integration externe.
2. **Contrat public explicite lisant un etat connu.** Preference initiale abandonnee au profit de l'amorcage ci-dessus : impose une interface et la coordination de ses consommateurs, sans necessite etablie pour ce besoin. Pas de modification des contrats partages ou des plugins retenue.
3. **Lire l'etat dans le constructeur uniquement.** Tres petit changement, mais insuffisant pour l'arrivee tardive d'une entite ; une conversion booleenne peut adopter un inconnu comme OFF. Non recommande seul.
4. **Reutiliser directement la resynchronisation d'inhibition.** Code proche, mais contrat semantiquement incorrect pour un consommateur general et effets sur le keep-alive ; un partage interne eventuel reste a evaluer, pas l'exposition de ce chemin tel quel.
5. **Desactiver la reparation ou ecrire le champ prive depuis le plugin.** Contournements rejetes par les criteres du ticket ; perte de protection ou couplage non supporte.

## Decisions et questions ouvertes

- **Decision de perimetre du mainteneur :** #2219 et #2223 forment une seule demande ; #2221 est une ancienne proposition fermee, pas une troisieme demande ni une solution acquise. Une seule campagne finale commune est prevue, en conservant les verifications ciblees intermediaires.
- **Proposition convergente validee :** attente initiale `None`, puis premiere commande admissible ou premier etat connu. La preference pour une API explicite est abandonnee ; le mainteneur a autorise sa mise en oeuvre dans le perimetre commun.
- **Arbitrage de commande :** E conservee pendant preparation, etablie juste avant appel de service admissible, conservee comme intention non confirmee sur erreur, jamais reecrite par un retour obsolete. Un blocage/refus avant appel n'etablit pas E ; l'amorcage reste possible si None. Adoption atomique du cache courant uniquement si E est encore None.
- **Politique d'attente proposee :** retour automatique au premier etat logique connu, sans nouvel appel d'integration. `None`, `unknown`, `unavailable` et valeurs hors paire ON/OFF ne constituent pas une observation adoptable. Pas de readoption permanente apres amorcage.
- **Arbitrage de securite :** garde initiale distincte apres connaissance logique, veto parent OFF avant comparaison sur attente connue, interdiction ON sous parent inconnu et invalidation des tentatives devenues obsoletes. Un retrait logique de l'autorisation ON ne signifie pas qu'un OFF physique a ete execute ; retour HEAT seul sans nouvelle commande valide ne ressuscite pas une attente ON retiree.
- **Contrainte de conception :** rester local au coeur et au cycle de vie de `UnderlyingSwitch`, sans nouvelle interface d'adoption ni modification des protocoles `vtherm_api` ou des plugins.
- **Inconnus :** reproduction en production, consommateurs exacts du futur contrat, compatibilite de toutes les versions tierces et causalite de l'incident rapporte dans #2219.

## Resultats de convergence

- [Specification commune v0.3 FR/EN](issue-2219-2223-specification.md) et [conception commune v0.2](issue-2219-2223-design.md), apres deux cycles de convergence, le 10 novembre 2026.
- Le `Redacteur de specifications` et `Conception logicielle detaillee` confirment explicitement : meme perimetre ; couverture des 14 exigences, 10 regles et 16 criteres ; absence de contradiction bloquante ; faisabilite et testabilite sous reserve de verification de l'implementation.
- La conception utilise des protections privees d'ordre des tentatives et de retrait ON, ainsi que des raccordements cibles de resolution du mode et de phase OFF sans commande. Aucun nouveau contrat public, changement `vtherm_api` ou plugin n'est prevu ; pas de refonte du scheduler.
- Divergence V6 resolue : retrait des nouveaux calculs de durees minimales via historique et des reports sur historique absent. Preserver les protections chez leurs proprietaires existants, sans nouvelle politique repair/keep-alive ni garantie sur un cooldown prive tiers.
- Un seul bilan final doit couvrir les 16 scenarios et leurs variantes pour les deux issues ; les verifications ciblees pendant developpement restent necessaires. Les scenarios ne sont pas encore executes.
- Risques residuels : commande deja remise a HA non annulable, aucun delai d'arret physique garanti, ordre asynchrone et reservations de puissance a verifier par tests, services virtuels potentiellement non idempotents, protections privees tierces non auditees.
- Aucune question documentaire bloquante restante identifiee. La version de livraison reste a renseigner lors de la release. Apres convergence des agents, le mainteneur a valide les arbitrages et autorise explicitement le developpement ; cet accord humain, pas la seule convergence, ouvre la phase d'implementation.

## Verification et criteres de passage

Etat de verification : analyse statique effectuee ; tentative de sonde isolee sans resultat exploitable (`outcome_unknown`). Aucun succes d'execution n'est revendique. Aucun test de la suite HA n'a ete lance et aucun resultat de test rapporte dans un ticket ou une PR n'est revendique comme verifie localement.

Les futurs criteres d'acceptation communs devront couvrir :

1. Attente initiale `None`, puis amorcage passif ON et OFF au premier etat logique connu, sans appel d'integration, appel physique, evenement de transition ou ecriture privee par un consommateur.
2. Parent HEAT, relais deja ON, adoption passive puis gestionnaire de reparation eligible : aucun OFF contradictoire.
3. Etat absent, `unknown`, `unavailable` et valeur non reconnue : attente initiale restant `None`, aucun repair ni keep-alive deduit de cette attente ; resolution automatique au premier etat connu si aucune commande ne l'a deja initialisee.
4. Commandes VTherm ON puis OFF apres adoption : nouvelle attente respectee par la reparation ; une adoption initiale tardive ne les ecrase pas.
5. Attente connue : parent OFF prioritaire, que l'attente soit ON ou OFF et que l'observation soit ON, OFF ou indisponible ; pas de reparation ON. Attente `None` : repair inactif, securite initiale conservee et reevaluation apres amorcage. Inclure la transition vers OFF pendant un chemin asynchrone si ce chemin peut emettre ON.
6. Non-regressions sur inversion, commandes virtuelles, plusieurs relais, keep-alive, inhibition, limites de puissance et phases OFF de regulation ; tests du delai initial et de la pause/reprise des reparations conserves.
7. Mode parent inconnu sans autorisation ON implicite ; retour de disponibilite reevalue sans faux acquittement d'arret. Parent HEAT avec un relais intentionnellement OFF ne force pas ON et ne contourne pas les durees minimales ou le cooldown.
8. Journaux de tentative ou de suppression identifiant le mode parent, le mode sous-jacent, l'intention effective, l'observation et la direction de commande ; pas d'affirmation de reparation physique non prouvee.

**Organisation de validation :** une matrice trace les exigences des deux issues vers leurs scenarios dans une campagne finale commune, sans reduire les garanties a un seul test. Les verifications ciblees pendant le developpement restent necessaires pour localiser les regressions ; aucun equipement reel ne doit etre energise par les tests.

Suite obligatoire :

1. Approbation du present rapport commun #2219/#2223 et autorisation de specification/conception obtenues le 10 novembre 2026 par l'accord "Go pour spec" ; le regroupement seul n'avait pas constitue cet accord.
2. Specification et conception communes produites par les deux agents ; convergence explicite sur perimetre, couverture, absence de contradiction, faisabilite et testabilite obtenue en deux cycles sur trois maximum.
3. Documents convergents, decisions et risques residuels presentes ; autorisation explicite distincte de developpement recue le 10 novembre 2026, avec creation de branche et commit documentaire demandes.
4. Delegation au sous-agent `Developpement d'integrations Home Assistant` sur cette base validee, sans intervention sur un equipement reel ; toute extension du perimetre devra etre soumise au mainteneur.