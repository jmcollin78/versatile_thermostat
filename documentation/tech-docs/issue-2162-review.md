# Revue de l’issue #2162 — Fermeture puis ouverture au démarrage

## Synthèse explicative — Français

**Périmètre : fermeture complète au démarrage, puis ouverture à la valeur calculée, hors mode sommeil.** Cette explication ne lance aucune phase de spécification, de conception ou de développement.

### Pourquoi VTherm ferme-t-il d’abord la vanne ?

Le mécanisme de bootstrap ajouté pour [#2049](https://github.com/jmcollin78/versatile_thermostat/issues/2049) peut provoquer cette séquence. Au démarrage, si un degré d’ouverture ou de fermeture est exactement `unknown`, `_seed_unknown_degrees_once()` calcule volontairement une paire avec **une demande de zéro, sans consulter le besoin de chauffage TPI**. Après validation des états et des bornes, il écrit uniquement les cibles `unknown`. Avec les limites usuelles et les deux degrés inconnus, cela envoie **ouverture 0 / fermeture 100** : [calcul du bootstrap](../../custom_components/versatile_thermostat/underlyings.py#L1680-L1702), [écriture des cibles](../../custom_components/versatile_thermostat/underlyings.py#L1725-L1760).

### À quoi sert cette première commande ?

Elle évite un blocage : VTherm attend des états de degré connus avant de réguler, mais certaines entités ne deviennent numériques qu’après une écriture. La commande d’amorçage permet de déclencher ces retours, puis de reprendre l’initialisation normale. **Une première écriture sert à sortir de `unknown` ; choisir zéro est une décision logicielle, pas une nécessité physique de calibration.** Ce chemin ne lance pas de procédure de calibration.

### Pourquoi la vanne s’ouvre-t-elle ensuite à la bonne valeur ?

Après réception des états initiaux requis, l’underlying termine son contrôle initial et peut notifier le thermostat. Une fois prêt, VTherm applique son état demandé, recalcule le besoin et envoie l’ouverture correspondante : [notification au thermostat](../../custom_components/versatile_thermostat/underlyings.py#L132-L152), [finalisation du démarrage](../../custom_components/versatile_thermostat/base_thermostat.py#L645-L683).

**Degrés inconnus → commande d’amorçage à zéro → retours numériques → initialisation terminée → calcul TPI → ouverture correcte.**

### Est-ce normal et comment le confirmer ?

**C’est conforme au comportement programmé lorsque le bootstrap s’applique ; ce n’est pas une fermeture obligatoire à chaque démarrage.** Si les degrés sont déjà numériques, ce bootstrap ne les réécrit pas et il faut rechercher une autre commande de fermeture. Les retours étant asynchrones, aucun délai fixe entre fermeture et ouverture n’est garanti.

Le code prouve l’existence de ce mécanisme, pas son exécution sur le redémarrage personnel observé. Pour le confirmer, corréler les états initiaux `unknown`, les lignes `Valve-regulation seed_attempted … with value 0` sur l’ouverture et `… with value 100` sur la fermeture, puis les retours d’initialisation et les commandes d’ouverture calculées. Les attributs `seed_attempted` joints à #2162 attestent de tentatives de bootstrap sur cette instance, mais ne suffisent pas à reconstituer la chronologie ni à prouver un déplacement mécanique.

## Explanatory summary — English

**Scope: full closure at startup, followed by opening to the calculated value, excluding sleep mode.** This explanation does not initiate any specification, design or development phase.

### Why does VTherm close the valve first?

The bootstrap mechanism added for [#2049](https://github.com/jmcollin78/versatile_thermostat/issues/2049) can produce this sequence. At startup, if an opening or closing degree is exactly `unknown`, `_seed_unknown_degrees_once()` deliberately calculates a pair using **zero demand, without consulting the TPI heating demand**. After validating states and bounds, it writes only to the `unknown` targets. With standard limits and both degrees unknown, this sends **opening 0 / closing 100**: [bootstrap calculation](../../custom_components/versatile_thermostat/underlyings.py#L1680-L1702), [target writes](../../custom_components/versatile_thermostat/underlyings.py#L1725-L1760).

### What is the purpose of this first command?

It prevents a deadlock: VTherm waits for known degree states before regulating, but some entities only become numeric after a write. The bootstrap command can trigger those state updates, allowing normal initialization to resume. **An initial write is used to leave `unknown`; choosing zero is a software decision, not a physical calibration requirement.** This code path does not start a calibration procedure.

### Why does the valve then open to the correct value?

After the required initial states have been received, the underlying completes its initial check and can notify the thermostat. Once ready, VTherm applies its requested state, recalculates demand and sends the corresponding opening: [thermostat notification](../../custom_components/versatile_thermostat/underlyings.py#L132-L152), [startup completion](../../custom_components/versatile_thermostat/base_thermostat.py#L645-L683).

**Unknown degrees → zero-demand bootstrap command → numeric state updates → initialization complete → TPI calculation → correct opening.**

### Is this normal, and how can it be confirmed?

**It matches the programmed behavior when the bootstrap applies; it is not a mandatory closure on every startup.** If the degrees are already numeric, this bootstrap does not overwrite them, and another closing command must be investigated. Since state updates are asynchronous, no fixed delay between closure and opening is guaranteed.

The code establishes that this mechanism exists, not that it ran during the personally observed restart. To confirm it, correlate the initial `unknown` states, the `Valve-regulation seed_attempted … with value 0` opening log and the `… with value 100` closing log, followed by initialization updates and calculated opening commands. The `seed_attempted` attributes attached to #2162 record bootstrap attempts for that instance, but cannot by themselves reconstruct the timeline or prove mechanical movement.

---

## Analyse courante — périmètre précisé le 2026-10-31

**Demande utilisateur : comprendre uniquement la fermeture complète au démarrage, suivie d’une ouverture à la bonne valeur, hors mode sommeil. Aucune spécification, conception ni implémentation n’est demandée ou autorisée.** Le diagnostic de température basse discuté dans la première analyse ne répond pas à cette séquence précise. L’analyse précédente est conservée plus bas comme historique, et non comme périmètre courant.

### Conclusion ciblée

**Il existe une fermeture volontaire de bootstrap, indépendante du besoin de chauffage, lorsque les degrés de vanne sont `unknown`.** Elle provient du mécanisme ajouté pour [#2049](https://github.com/jmcollin78/versatile_thermostat/issues/2049), et n’est pas réservée au sommeil. Elle utilise une demande de zéro, même si le thermostat est restauré en chauffage et doit finalement ouvrir à une valeur positive.

Cette fermeture peut donc être **normale au sens du comportement actuellement programmé**, sans être une nécessité physique de calibration ni un passage systématique de toute régulation. Le choix de zéro est une politique d’amorçage explicite ; ce n’est pas le résultat du TPI à cet instant.

Le mécanisme est démontré par lecture du code. Son exécution sur le redémarrage personnel de l’utilisateur reste à confirmer par les états initiaux et les journaux. Les attributs publiés dans #2162 comportent `seed_attempted` pour les deux degrés : le mécanisme a été tenté sur cette instance, mais cet instantané ne date pas les mouvements et ne documente pas l’installation de l’utilisateur.

### 1. Pourquoi une première écriture est nécessaire dans ce cas

Le problème traité par #2049 était un blocage : les entités de degré restent `unknown` après redémarrage ; VTherm attend leur initialisation avant la régulation normale ; certaines de ces entités ne deviennent numériques qu’après une écriture.

La solution retenue est d’envoyer une première commande bornée pour déclencher un retour d’état, puis de laisser le flux normal initialiser le thermostat. Le [rapport #2049](issue-2049-review.md#L28-L37) explique cette boucle et la [décision DEC-001](issue-2049-specification.md#L135-L140) impose une demande zéro, jamais la demande courante.

Il faut distinguer deux choses : **une écriture sert à sortir de `unknown` ; choisir une fermeture pour cette écriture est une décision logicielle.** Rien dans ce chemin ne lance une procédure de calibration.

### 2. Qui commande effectivement la fermeture

Dans [le démarrage de l’underlying de vanne](../../custom_components/versatile_thermostat/underlyings.py#L1659-L1662), `async_startup()` installe les listeners puis appelle `_seed_unknown_degrees_once()`.

Cette routine :

1. lit l’état des degrés ouverture/fermeture configurés ;
2. refuse le seed si une cible est absente, indisponible ou invalide ;
3. ne fait rien si toutes les cibles sont déjà numériques ;
4. si au moins une cible est exactement `unknown`, valide les bornes et calcule une paire avec **`brut_valve_open_percent=0`**, sans consulter la demande TPI ;
5. envoie les valeurs uniquement aux cibles `unknown`, au plus une fois par cible dans ce bootstrap.

Sources : [calcul de la paire de seed](../../custom_components/versatile_thermostat/underlyings.py#L1680-L1723), [sélection et écriture des cibles](../../custom_components/versatile_thermostat/underlyings.py#L1725-L1760), [appel du service numérique](../../custom_components/versatile_thermostat/underlyings.py#L265-L281).

Avec les bornes usuelles `max_closing_degree=100`, le [calcul de conversion](../../custom_components/versatile_thermostat/opening_degree_algorithm.py#L47-L78) donne **ouverture 0 / fermeture 100** pour cette demande zéro. Lorsque les deux degrés sont `unknown`, les deux consignes sont donc écrites. Si une seule cible est inconnue, seule celle-ci est écrite ; il ne faut pas présumer que la paire entière est systématiquement envoyée. Avec une limite de fermeture différente, la commande de demande zéro n’est pas nécessairement une fermeture complète.

### 3. Pourquoi l’ouverture correcte vient après

La séquence nominale compatible avec la fermeture décrite, pour une demande de chauffage positive, est la suivante :

| Étape | Action et cause                                                                                                                                                          |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1     | Le démarrage parent restaure les états demandés/effectifs et lit les températures disponibles. Les vannes non initialisées empêchent encore la régulation normale.       |
| 2     | Le démarrage des underlyings de vanne lance le seed à demande zéro sur les degrés `unknown` : c’est la première commande de fermeture.                                   |
| 3     | L’intégration sous-jacente publie des degrés numériques. Le gestionnaire d’état reçoit ces retours ; l’acceptation du service ne suffit pas à elle seule.                |
| 4     | Quand tous les degrés requis ont un état initialisé, l’underlying passe son contrôle initial puis peut notifier le thermostat.                                           |
| 5     | Quand le thermostat est prêt, sa finalisation rafraîchit les gestionnaires, applique l’état demandé et recalcule la régulation.                                          |
| 6     | Le TPI détermine le besoin, la régulation retient le pourcentage et le chemin normal de commande envoie les degrés correspondants : c’est l’ouverture à la bonne valeur. |

Sources : [restauration et lecture des températures](../../custom_components/versatile_thermostat/base_thermostat.py#L561-L638), [démarrage des vannes après le parent](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L150-L161), [réception puis contrôle initial et notification parent](../../custom_components/versatile_thermostat/underlyings.py#L132-L152), [finalisation du thermostat](../../custom_components/versatile_thermostat/base_thermostat.py#L645-L683), [entrée du calcul TPI](../../custom_components/versatile_thermostat/thermostat_prop.py#L223-L234), [application par le scheduler](../../custom_components/versatile_thermostat/cycle_scheduler.py#L504-L517), [conversion et envoi de la paire](../../custom_components/versatile_thermostat/underlyings.py#L1811-L1834).

**Point de séquencement important :** `check_initial_state()` de l’underlying précède la notification au parent qui peut terminer l’initialisation globale. Si le besoin n’a pas encore été calculé, ce contrôle initial ne l’invente pas : en chauffage, il constate une commande nulle/non calculée et ne force pas l’ouverture. Le calcul et l’envoi normaux arrivent ensuite. Si un pourcentage positif est déjà disponible, le contrôle initial peut lui-même l’envoyer. Voir [la branche de chauffage du contrôle initial](../../custom_components/versatile_thermostat/underlyings.py#L1595-L1632).

Les callbacks et retours d’état sont asynchrones : ce tableau décrit le scénario de bootstrap, pas une chronologie matérielle garantie à la milliseconde ni un délai fixe entre fermeture et ouverture. Sans retour initialisé, l’étape de régulation peut rester bloquée.

### 4. Ce qui ne suffit pas à prouver une fermeture physique

`_valve_open_percent` démarre à `None` et [son getter expose alors zéro](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L354-L360). **Lire ou afficher ce zéro ne commande pas à lui seul la vanne.** Il faut identifier un appel d’écriture pour expliquer un mouvement réel.

De même, `check_initial_state()` ne ferme pas systématiquement une vanne restaurée en chauffage. Sa branche de fermeture dépend d’un mode effectif `off` et d’une ouverture supérieure au seuil ; elle envoie alors le seuil configuré, pas nécessairement zéro : [branche OFF](../../custom_components/versatile_thermostat/underlyings.py#L1634-L1644). Si les degrés sont déjà numériques et qu’un mouvement survient néanmoins, il faut rechercher cette branche, une commande d’arrêt ou une commande normale à zéro, plutôt qu’incriminer le seed sans preuve. Aucun passage transitoire obligatoire par `off` n’a été démontré ici.

### 5. Comment confirmer la cause sans modifier le système

Dans un journal de démarrage déjà disponible, corréler pour la même vanne :

- les états initiaux des deux entités de degré, notamment `unknown` ;
- les lignes `Valve-regulation seed_attempted for ... with value 0` sur l’ouverture et `... with value 100` sur la fermeture, avec les bornes usuelles ;
- les retours numériques, puis `All underlying states are now initialized` et la finalisation `init_underlyings_completed` ;
- le calcul du pourcentage et les envois normaux, notamment `Setting valve ouverture percent to ...` ou `TPI says ... heating needed`, puis `I have sent opening_degree=... closing_degree=...`.

Une ligne `seed_attempted` décrit une tentative de service et non la preuve du déplacement mécanique. Le tableau d’attributs `seed_targets` permet de distinguer `seed_attempted`, `already_numeric` et les motifs de refus, mais pas de reconstituer seul la chronologie. Un refus par inhibition ou une erreur du service reste également à distinguer d’un envoi appliqué.

### 6. Décision à ce stade

**Rester en analyse explicative.** Le bootstrap à zéro fournit une cause logicielle concrète et indépendante du sommeil pour « fermeture puis ouverture calculée ». Il faut vérifier sa trace sur le redémarrage observé avant de déclarer ce diagnostic confirmé sur cette installation.

Pas de correction proposée à appliquer, pas de configuration modifiée, pas de test exécuté et pas de demande d’autorisation de lancer des spécifications ou du développement. Retirer le bootstrap sans analyse risquerait de réintroduire le blocage de #2049 ; ce risque explique le mécanisme existant, sans préjuger d’une éventuelle évolution future.

---

## Historique — première analyse, remplacée par le périmètre ci-dessus

Les constats suivants documentent la première lecture de l’issue. Les propositions de suite et le cas sommeil qu’ils contiennent sont **hors du périmètre courant** demandé par l’utilisateur.

| Métadonnée                         | Valeur                                                                                                                                                                     |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Issue                              | [#2162 — One TRVZB open up to 100% then goes to correct values during startup of HA](https://github.com/jmcollin78/versatile_thermostat/issues/2162)                       |
| Date de consultation               | 2026-10-31                                                                                                                                                                 |
| Statut                             | Analyse documentaire et statique terminée ; validation utilisateur attendue                                                                                                |
| Version signalée / manifeste local | `10.6.2` / `10.6.3`                                                                                                                                                        |
| État GitHub consulté               | Ouverte, assignée à `jmcollin78`, étiquettes `bug`, `P2`, `question` ; aucune PR directement associée affichée                                                             |
| Recommandation                     | **Demander des précisions pour le cas initial ; retenir séparément l’investigation du transitoire en mode sommeil. Ne pas assimiler automatiquement cette issue à #2159.** |

## 1. Résumé fidèle et évolution du diagnostic

### Cas A — Signalement initial de @robygi

L’installation comprend une configuration centrale et onze Sonoff TRVZB associés à Zigbee2MQTT, pilotés par des thermostats `over_climate` avec contrôle direct des vannes. Au redémarrage de Home Assistant, la vanne du bureau s’ouvre à 100 %, puis revient à 0 % après environ quatre à cinq minutes. La température affichée remonte simultanément depuis une valeur basse. L’auteur ne constate le phénomène que sur cette vanne et s’interroge sur sa configuration ou son automatisation mensuelle de calibration.

Les attributs joints décrivent notamment :

- `hvac_mode=heat`, `preset=eco`, consigne effective 18 °C, température courante 19,2 °C ;
- `is_sleeping=false`, `follow_underlying_temp_change=false` ;
- TPI : coefficients intérieur `0.6`, extérieur `0.01`, seuils TPI à zéro ;
- période minimale de régulation de cinq minutes, seuil de variation de 10 %, cycle de dix-huit minutes ;
- ouverture et puissance revenues à zéro ;
- diagnostics `seed_attempted` pour les deux degrés ouverture/fermeture.

**Limite :** il s’agit d’un instantané, pas d’une preuve de l’état exact à chaque instant du démarrage.

### Cas B — Observation distincte de @bontiv

- @bontiv confirme d’abord entendre des mouvements de vannes au redémarrage.
- Dans son commentaire le plus récent consulté, il précise que **son cas est différent** : tous ses thermostats sont en `sleep`, puis toutes les vannes passent à 0 % avant de revenir à 100 % au redémarrage.
- @bontiv indique également avoir examiné le journal de @robygi dans le débogueur : le capteur de pièce annoncerait d’abord **9,7 °C**, puis **19,4 °C**. Il attribue l’ouverture à la demande de chauffage résultante et demande la marque et le modèle du thermomètre.
- @jmcollin78 indique prendre en charge le ticket en parallèle du correctif de [#2159](https://github.com/jmcollin78/versatile_thermostat/issues/2159).

Ces commentaires font évoluer le diagnostic : **le cas A est un épisode 100 % → 0 % associé à une température basse ; le cas B est un épisode 0 % → 100 % en sommeil.** Le second ne constitue pas une reproduction à l’identique du premier.

## 2. Sources et niveau de preuve

### Sources externes consultées

1. [Issue #2162](https://github.com/jmcollin78/versatile_thermostat/issues/2162) : description, attributs, commentaires et métadonnées accessibles à la consultation.
2. [Issue #2159](https://github.com/jmcollin78/versatile_thermostat/issues/2159) : régression après #2141 avec suivi sous-jacent actif ; affichée clôturée par fusion de la [PR #2161](https://github.com/jmcollin78/versatile_thermostat/pull/2161) lors de la consultation. Le diff de cette PR n’a pas été audité dans cette revue.
3. [Journal joint à #2162](https://github.com/user-attachments/files/34177001/vtherm_logs_vt_termostato_studio_20261030_103312.log) : tentative de récupération, mais la redirection vers le fichier brut n’a pas fourni de contenu exploitable avec les outils disponibles. **Aucune lecture directe ni chronologie du journal brut n’est revendiquée.** Les valeurs 9,7/19,4 °C restent une observation rapportée par @bontiv, non revérifiée indépendamment ici.
4. Les captures restent accessibles dans l’issue ; aucune mesure indépendante n’en a été extraite pour ce rapport.

### Sources locales effectivement examinées

- [Manifeste](../../custom_components/versatile_thermostat/manifest.json) : version locale `10.6.3`.
- [Démarrage et restauration](../../custom_components/versatile_thermostat/base_thermostat.py#L561-L755), [température exposée](../../custom_components/versatile_thermostat/base_thermostat.py#L1137-L1139) et [réception du capteur](../../custom_components/versatile_thermostat/base_thermostat.py#L2338-L2350).
- [Entrées du calcul proportionnel](../../custom_components/versatile_thermostat/thermostat_prop.py#L223-L234) et [calcul TPI](../../custom_components/versatile_thermostat/prop_algo_tpi.py#L75-L150).
- [Démarrage des vannes](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L150-L161), [recalcul](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L236-L275) et [envoi des commandes](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L295-L333).
- [Réconciliation initiale des vannes](../../custom_components/versatile_thermostat/underlyings.py#L1580-L1645) et [seed des degrés inconnus](../../custom_components/versatile_thermostat/underlyings.py#L1659-L1745).
- [Filtrage des commandes](../../custom_components/versatile_thermostat/valve_command.py#L28-L106), [EMA](../../custom_components/versatile_thermostat/ema.py#L46-L102) et [suivi des modes sous-jacents actuel](../../custom_components/versatile_thermostat/thermostat_climate.py#L824-L883).
- [Tests du bootstrap](../../tests/test_check_initial_state.py#L13-L175) et [test du mode sommeil](../../tests/test_overclimate_valve.py#L700-L770).
- [Documentation utilisateur](../fr/over-climate.md#L56-L70) et [contrat du mode sommeil](../fr/over-climate.md#L119-L121).
- [Revue #2049](issue-2049-review.md), [spécification #2049](issue-2049-specification.md#L135-L140), [revue #2159](issue-2159-review.md), [revue post-développement #2159](issue-2159-post-dev-review.md).

**Méthode et limites :** lecture statique uniquement. Pas de test exécuté, pas de reproduction matérielle, pas de commande Home Assistant, pas d’inspection de l’historique Git pour dater précisément l’introduction des mécanismes. Les résultats d’exécution mentionnés dans des rapports antérieurs ne sont pas des validations réalisées pour #2162. Le code `10.6.2` exact installé chez l’auteur n’a pas été comparé au code local `10.6.3`.

## 3. Analyse technique

### 3.1 Une mesure numérique basse suffit à expliquer une demande de 100 %

Au démarrage, `BaseThermostat.async_startup()` lit l’état disponible du capteur de pièce. `_async_update_temp()` accepte une valeur convertible en nombre fini ; il ne rejette pas 9,7 °C au seul motif qu’un redémarrage vient d’avoir lieu. `current_temperature` expose directement `_cur_temp`.

`ThermostatProp.recalculate()` transmet **la température brute `_cur_temp`** au calcul proportionnel, pas `_ema_temp`. Avec les coefficients déclarés, en chauffage et sans seuil TPI actif :

$$p=\operatorname{clamp}_{[0,1]}\left(0{,}6\,(T_{cible}-T_{pièce})+0{,}01\,(T_{cible}-T_{ext})\right).$$

À titre d’illustration statique, pour une consigne de 18 °C et la température extérieure 15,6 °C de l’instantané :

- à 9,7 °C : contribution intérieure `4.98`, donc saturation à 100 % ;
- à 19,4 °C : résultat avant saturation `-0.816`, donc 0 %.

Il ne s’agit pas d’un rejeu du journal : ces valeurs illustrent la cohérence du commentaire avec le code et la configuration. Les consignes et températures extérieures contemporaines du phénomène restent à relever.

**Conclusion pour A :** une mesure de pièce initialement trop basse est une explication fortement étayée par le commentaire et cohérente avec l’algorithme. Cela ne prouve ni une panne matérielle du thermomètre, ni l’absence de problème dans une entité template, une restauration d’état, une unité ou une intégration qui fournit cette mesure.

### 3.2 Le délai de quatre à cinq minutes est compatible avec la configuration

Le recalcul de `ThermostatOverClimateValve` et le filtre des commandes utilisent une période minimale de régulation. L’instantané indique cinq minutes ; un recalcul différé peut être planifié. Cela peut prolonger une commande initiale même si la mesure se corrige entre-temps.

**Hypothèse, pas chronologie prouvée :** cette période contribue au délai observé. Il faut relever les horodatages du premier calcul, de la mesure corrigée et de l’envoi à zéro avant de l’affirmer. Les durées minimales de 300 secondes et le cycle de dix-huit minutes ne suffisent pas, à eux seuls, à attribuer ce délai.

### 3.3 L’EMA ne doit pas être confondue avec la mesure utilisée par le TPI

L’EMA initialise sa première valeur à la mesure reçue, puis la lisse. Elle est calculée en parallèle de `_cur_temp`. **Dans le chemin local examiné, elle n’est pas l’entrée de température du TPI.** Il serait donc injustifié d’attribuer directement les cinq minutes d’ouverture à « l’inertie de l’EMA », ou la remontée de `current_temperature` à un lissage VTherm. Il faut identifier exactement la série affichée sur la capture et la source du capteur.

### 3.4 En sommeil, 100 % est le comportement attendu ; la fermeture transitoire est à expliquer

Le contrat documenté du mode `sleep` est de maintenir la vanne complètement ouverte sans déclarer une activité de chauffage VTherm. Ce comportement existe à plusieurs niveaux :

- `UnderlyingValveRegulation.check_initial_state()` envoie 100 % si `is_sleeping` ;
- `ThermostatOverClimateValve.recalculate()` utilise `on_percent=1.0` en sommeil ;
- `ValveCommandMixin.apply_valve_command_percent()` retient 100 % en sommeil ;
- le test du mode sommeil attend ouverture 100, fermeture 0 et `hvac_action=off`.

**Pour le cas B, le défaut potentiel n’est donc pas le retour à 100 %, mais la fermeture intermédiaire à 0 %.** Supprimer l’ouverture finale casserait le contrat existant.

### 3.5 Le bootstrap #2049 est une piste concrète pour cette fermeture

Dans le code local, `UnderlyingValveRegulation.async_startup()` installe les listeners puis appelle `_seed_unknown_degrees_once()`. Si les cibles sont numériques ou exactement `unknown` et les bornes valides, le seed calcule la paire avec une demande **zéro**, puis écrit uniquement les cibles `unknown`. Ce chemin ne comporte pas de branche spécifique `is_sleeping`.

Un scénario candidat pour B est donc :

1. mode sommeil restauré ; degrés de vanne `unknown` ;
2. bootstrap de fermeture à demande zéro ;
3. retours numériques, initialisation normale ;
4. réconciliation en sommeil vers 100 %.

**Niveau de preuve :** les mécanismes de fermeture et d’ouverture sont établis par lecture ; leur ordre effectif et leur rôle dans l’installation de @bontiv ne sont pas reproduits. Si les degrés sont déjà numériques au démarrage, le seed ne les réécrit pas : il faudra alors chercher un autre chemin de fermeture. Les commandes de degrés sont des consignes ; elles ne constituent pas une mesure indépendante de la position mécanique réelle.

Les attributs de @robygi montrent bien des tentatives de seed, mais **un seed à demande zéro n’explique pas directement une ouverture à 100 % en mode `heat`**. Sa présence ne suffit pas à fusionner A et B.

### 3.6 Lien avec #2159 et changements récents

Le cas #2159 portait sur une boucle de changements HVAC avec `follow_underlying_temp_change` actif, après #2141. Le cas A de #2162 annonce `follow_underlying_temp_change=false`, une version `10.6.2` et une seule excursion avant stabilisation. La branche locale d’adoption HVAC est conditionnée par le suivi actif.

**Aucun lien causal direct avec le défaut de suivi de #2159 n’est démontré pour A.** Le voisinage des chemins de démarrage justifie des tests communs, pas une attribution automatique. L’état `false` de l’instantané ne prouve toutefois pas toute la chronologie du démarrage.

Pour B, le seed introduit au titre de #2049 est une piste plus directement liée à une fermeture initiale. La date d’introduction exacte, les versions réellement affectées et une éventuelle interaction avec d’autres changements restent à vérifier dans l’historique et par reproduction.

Les rapports locaux de #2159 comportent des constats historiques ; ils ne décrivent pas nécessairement l’état courant. Le code local contient notamment déjà une garde refusant le suivi d’un mode identique au mode effectif, contrairement au constat ancien E-1. Cette revue ne réouvre pas ce constat comme défaut actuel.

## 4. Pertinence, périmètre et recommandation

### Décision recommandée

**Conserver l’issue ouverte pour clarification, avec deux axes explicitement séparés.**

- **A — Demander des précisions / diagnostiquer la source de température.** Pas de correctif TPI justifié à ce stade. Ne pas conclure catégoriquement « ce n’est pas VTherm » sans vérifier la chaîne de mesure et le journal brut.
- **B — Retenir une investigation ciblée du transitoire de démarrage en sommeil.** L’interaction seed à zéro / restauration à 100 % est une hypothèse logicielle précise et testable. Elle peut justifier une issue distincte pour éviter une clôture ambiguë.

### Inclus dans la suite proposée

1. Obtenir et corréler les états et commandes de démarrage des deux cas.
2. Reproduire B avec degrés numériques puis `unknown`, ouverture seule ou paire ouverture/fermeture, mode sommeil effectivement restauré.
3. Si la causalité est confirmée, décider si le bootstrap de fermeture reste acceptable en sommeil ou si son contrat doit évoluer.
4. Préserver la disponibilité des vannes sans retour initial et les garanties de validation des bornes de #2049.
5. Ajouter des tests de non-régression et préciser la documentation si un comportement change.

### Exclus

- Refondre le TPI, l’EMA ou les coefficients pour masquer une mesure de démarrage erronée.
- Ajouter arbitrairement une temporisation globale ou une plage de température « plausible ».
- Supprimer le mode sommeil ou son ouverture complète.
- Modifier les réglages de l’installation, déclencher un calibrage ou commander les vannes pendant l’analyse.
- Garantir une correction matérielle ou une résolution de #2162 par le seul patch #2159.

## 5. Impacts et risques

| Impact / risque                                                                               | Gravité                                               | Probabilité / preuve                                   | Précaution                                                                                          |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| Demande indue de chaleur après une mesure initiale erronée                                    | Moyenne ; potentiellement élevée selon l’installation | Épisode rapporté ; origine de mesure non confirmée     | Corréler capteur, consigne, calcul et commande ; ne pas masquer une mesure valide réellement basse. |
| Fermeture/réouverture inutile en sommeil : bruit, batterie, sollicitation mécanique et Zigbee | Faible à moyenne                                      | Observée par @bontiv ; mécanisme exact non confirmé    | Tester la séquence des services, pas seulement la position finale.                                  |
| Rupture du contrat #2049 en changeant le seed                                                 | Élevée : thermostat pouvant rester non prêt           | Possible si le bootstrap est supprimé sans alternative | Conserver l’autorité du gestionnaire d’état et l’attente de vrais retours numériques.               |
| Régression du sommeil ou d’un démarrage en arrêt/chauffage                                    | Moyenne à élevée                                      | Possible lors d’un changement générique                | Matrice de modes et de disponibilités, avec bornes non standard.                                    |
| Rejet d’un vrai besoin de chauffage par filtre arbitraire au démarrage                        | Élevée                                                | Possible avec un contournement global                  | Ne pas imposer de délai ni de seuil physique universel sans spécification.                          |
| Diagnostic erroné par confusion entre A, B et #2159                                           | Moyenne                                               | Élevée sans séparation des scénarios                   | Conserver des preuves et critères distincts.                                                        |
| Exposition de données domestiques dans les journaux publiés                                   | Moyenne                                               | Possible                                               | Demander un extrait minimal et expurgé ; ne pas inclure de secrets ou d’export complet.             |

**Compatibilité et migration :** aucun changement de dépendance, schéma de configuration ou migration n’est justifié par cette analyse. Si le seed doit dépendre du mode, cela modifiera la décision normative `DEC-001` de #2049 (« demande zéro, jamais la demande courante ») : spécification et conception devront être mises à jour ensemble avant implémentation. Les installations autres que Sonoff ne doivent pas être exclues artificiellement d’un mécanisme générique.

**Exploitation et documentation :** conserver des diagnostics distincts pour seed, demande TPI, mode restauré et commande effectivement envoyée ; expliquer que `sleep` signifie vanne ouverte et non chauffage actif. La calibration mensuelle n’est ni incriminée ni exonérée sans vérifier son exécution.

## 6. Alternatives examinées

| Alternative                                                      | Avantages                                         | Inconvénients / position                                                                                                  |
| ---------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Corriger la source de température au démarrage si A est confirmé | Traite la cause sans modifier la régulation       | Nécessite le détail du capteur et de son intégration ; priorité pour A.                                                   |
| Conserver le seed à zéro et documenter le transitoire en sommeil | Préserve le contrat #2049 et son bootstrap simple | Conserve le bruit et les mouvements ; option fonctionnelle à faire accepter, pas correction du transitoire.               |
| Adapter la valeur de seed au sommeil, sous les mêmes contrôles   | Pourrait éviter une fermeture avant réouverture   | Change #2049 ; vérifier restauration, bornes, cibles partielles et retours avant décision. Piste, pas conception validée. |
| Supprimer le seed ou simplement l’ignorer en sommeil             | Évite son écriture de fermeture                   | Peut empêcher toute initialisation si les degrés restent `unknown` ; non recommandé sans autre mécanisme démontré.        |
| Bloquer toute régulation quelques minutes après redémarrage      | Simple en apparence                               | Retarde aussi un chauffage légitime, ne qualifie pas les données et ne règle pas forcément B ; déconseillé.               |
| Désactiver le suivi sous-jacent                                  | Contournement connu pour #2159                    | Déjà désactivé dans l’instantané de A ; aucune valeur démontrée pour #2162.                                               |

## 7. Questions ouvertes et éléments à demander

### Pour A

1. Quelle entité fournit la température de pièce ? Marque, modèle, intégration, unité, éventuel template ou facteur de conversion ?
2. Cette entité elle-même publie-t-elle 9,7 °C puis 19,4 °C, ou seule une courbe dérivée présente-t-elle ce saut ? Fournir ses états et attributs autour du redémarrage.
3. Fournir un extrait lisible du journal depuis avant le démarrage jusqu’au retour à zéro, avec mesures, consignes, mode, calcul TPI, seed et commandes de degrés horodatés.
4. Quelles versions de Home Assistant, Zigbee2MQTT et firmware TRVZB ? Le phénomène persiste-t-il sur la version incluant #2159 ? Une amélioration seule ne prouverait pas la même cause.
5. L’automatisation de calibration ou d’autres automatisations se sont-elles exécutées pendant cet intervalle ?

### Pour B

1. Quelles versions exactes, quels états restaurés demandés/effectifs, et quels degrés `unknown`, `unavailable` ou numériques au démarrage ?
2. La fermeture est-elle précédée d’un `seed_attempted` ? Quelles valeurs d’ouverture et de fermeture ont réellement été envoyées et dans quel ordre ?
3. Le transitoire existe-t-il aussi quand les deux degrés sont numériques ? Toutes les vannes de cette installation réagissent-elles de la même façon dans ces conditions ?
4. Après confirmation du mécanisme, souhaite-t-on interdire la fermeture transitoire en sommeil, ou accepter et documenter le bootstrap existant ?

**Bloqueurs :** absence de lecture indépendante du journal pour certifier A ; absence de reproduction de la séquence de B et de décision sur le contrat de seed pour autoriser son évolution. Ces limites n’empêchent pas de valider le présent rapport comme base d’investigation.

## 8. Vérifications et tests à prévoir

Les tests existants ont été lus, **pas exécutés** :

- bootstrap sur cible `unknown`, refus en cas de bornes invalides ou de cible `unavailable`, budget one-shot et absence de readiness sans retour numérique : [tests de bootstrap](../../tests/test_check_initial_state.py#L13-L175) ;
- passage volontaire en sommeil, ouverture complète et absence d’activité VTherm : [test du sommeil](../../tests/test_overclimate_valve.py#L700-L770).

Les premiers neutralisent `check_initial_state()` dans plusieurs cas ; le second teste un changement de mode, pas la séquence complète d’un redémarrage avec degrés inconnus. Ils ne constituent donc pas une preuve d’absence de fermeture transitoire au restart.

Matrice de validation proposée, à détailler après accord :

| Scénario                                                                        | Vérification attendue                                                                                 |
| ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `heat`, mesure valide basse puis mesure au-dessus de la consigne                | Demande TPI cohérente ; distinguer température brute et EMA ; expliquer l’attente de régulation.      |
| `heat`, température initiale déjà supérieure à la consigne                      | Aucune ouverture à 100 % sans autre cause identifiée.                                                 |
| `sleep` restauré, degrés déjà numériques à 100/0                                | Identifier tout envoi de fermeture ; pas de seed sur cible numérique.                                 |
| `sleep` restauré, un ou deux degrés `unknown`                                   | Enregistrer toute la séquence seed → retour → réconciliation, puis comparer au contrat décidé.        |
| Une seule cible configurée, bornes non standard, degré indisponible ou invalide | Préserver la conversion, le refus atomique des paires non éligibles et l’absence de fausse readiness. |
| Arrêt et chauffage après bootstrap ; suivi actif et inactif                     | Pas de régression de #2049 ni des protections #2141/#2159.                                            |
| Retours numériques retardés ou absents, inhibition active                       | Pas de répétition non bornée, de contournement d’inhibition ni d’initialisation artificielle.         |

Toute affirmation d’absence de mouvement physique devra être confirmée sur TRVZB ; un test de service prouve l’ordre des consignes, pas la position mécanique.

## 9. Suite du processus et critères de passage

1. **Soumettre ce rapport à validation explicite.** Aucun développement n’est autorisé par le présent document.
2. Après accord, faire produire des spécifications et une conception convergentes sur le périmètre retenu, en distinguant A et B ; ne pas engager de correction de B avant confirmation et décision sur son bootstrap.
3. Avant développement : obtenir une reproduction ciblée ou une preuve causale suffisante, décider le comportement du seed en sommeil, préserver les garanties de #2049 et fixer des critères portant sur les commandes intermédiaires autant que sur l’état final.
4. Soumettre les documents convergents à une **seconde autorisation explicite** avant de déléguer l’implémentation.

**Bilan :** l’hypothèse d’un lien avec les changements récents mérite une vérification ciblée du bootstrap pour le cas sommeil. En revanche, les éléments consultés ne démontrent pas que le symptôme initial de #2162 est une régression de #2159. L’explication prioritaire de ce symptôme reste la température basse de démarrage rapportée dans le dernier diagnostic, à vérifier sur la source réelle et le journal brut.