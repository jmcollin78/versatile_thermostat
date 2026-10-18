# Issue #2111 - Recalcul immediat au changement de mode HVAC

**Date :** 2026-10-18.
**Statut :** convergence documentaire atteinte ; validation humaine requise avant developpement.
**Reference :** [issue #2111](https://github.com/jmcollin78/versatile_thermostat/issues/2111).

**Documents associes :** [specification bilingue](issue-2111-specification.md), [conception bilingue](issue-2111-design.md), [rapport anglais](issue-2111-review-en.md).

## Decision et contexte

Traiter directement l'issue #2111 : forcer le recalcul au changement reel de mode HVAC effectif, en conservant integralement le filtre `dpercent`. Reutiliser le signal de transition existant et les mecanismes de forcement, sans ajouter de memoires du dernier mode calcule ou envoye.

Ce rapport remplace l'analyse precedente et ses recommandations incompatibles avec cette decision. En particulier, la recommandation de contourner `dpercent` lors d'une transition est retiree.

Le mainteneur indique que les petits mouvements peuvent provoquer une perte de calibrage des Sonoff TRVZB. Cette justification materielle est une contrainte fournie par le mainteneur, non une mesure reproduite dans cette session. Le filtre est une protection, pas seulement une optimisation de batterie.

## Faits verifies et sources

- L'issue rapporte une ouverture obsolete a 100 % lors des transitions de `sleep`, avec des etats de chauffe et une demande de pompe a chaleur injustifies. Configuration declaree : VTherm 10.5.1, HA 2026.10.1, Sonoff TRVZB via Zigbee2MQTT, periode minimale de 5 minutes.
- Le [commentaire du mainteneur du 18 octobre](https://github.com/jmcollin78/versatile_thermostat/issues/2111#issuecomment-6254039750) annonce le forcement du recalcul au changement de mode HVAC.
- [update_states](../../custom_components/versatile_thermostat/base_thermostat.py#L1768) connait le changement de mode effectif et appelle le recalcul puis le controle. Forcer uniquement le service utilisateur manquerait des transitions automatiques et pourrait forcer des demandes sans changement effectif.
- [recalculate](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L234) contourne la periode avec `force=True`, mais son filtre `dpercent` ne depend pas de `force` : cette separation doit rester inchangee.
- [L'envoi regule](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L308) dispose d'une autre temporisation. Le controle et le scheduler peuvent aussi appliquer la position : verifier les commandes du flux complet, pas seulement un appel de calcul.
- Aucune execution locale ou validation materielle n'a ete effectuee. Les constats de code sont statiques ; aucun resultat de test d'une autre implementation ne valide la nouvelle approche.

## Perimetre retenu

Inclure uniquement les thermostats `over_climate` avec regulation directe de vanne, et tous leurs changements reels de mode effectif, qu'ils soient manuels ou automatiques. Forcer le recalcul dans le traitement de la transition, puis permettre l'application sans attente de la periode minimale de la valeur effectivement retenue par les protections existantes.

Hors transition, maintenir les temporisations, les filtres, les conversions min/max, la deduplication et les appels forces preexistants. Ne pas propager un nouveau forcement general aux autres types de thermostat.

Exclure toute nouvelle politique de capteur absent, toute refonte de concurrence, tout changement de formule TPI ou de reglage materiel, toute nouvelle configuration et toute modification de l'environnement HA.

## Regles non negociables

1. Aucun contournement ajoute de `dpercent`, meme avec `force=True` ou a la sortie de sleep. Conserver les inegalites actuelles, y compris leur asymetrie aux bornes : pour un seuil de 5, une variation de -5 reste filtree, une variation de +5 ne l'est pas, sous les autres conditions du filtre.
2. Conserver l'exception existante de fermeture a 0 % et le traitement existant des petites ouvertures. Ne pas remplacer le filtre par un arrondi ou une nouvelle comparaison.
3. Conserver la semantique existante de sleep : ouverture logique de 100 %, soumise a la conversion materielle. Le chemin actuel de sleep ne passe pas par le filtre de variation de la branche TPI ; aucune nouvelle exception n'est ajoutee par ce correctif.
4. Exemple discriminant : a la sortie de `sleep 100 %`, si le calcul propose 98 % avec un seuil de 5, conserver 100 % et ne pas commander 98 %. Cet ecart intentionnel n'est pas le symptome de retard a corriger.
5. Ne jamais envoyer le resultat brut du TPI si le regulateur l'a filtre. L'inhibition et les autres protections restent prioritaires ; un forcement ne les autorise pas a etre contournees.
6. Sans donnees de calcul, conserver la politique actuelle, sans promettre une ouverture fraiche ni inventer une fermeture automatique. Les etats physiques ne sont pas des acquittements synchrones du service HA.

## Pertinence et recommandation

**Retenir cette approche locale.** Elle s'appuie sur une transition deja connue, limite les nouveaux etats internes et corrige l'attente temporelle sans supprimer une protection materielle. Sa simplicite ne constitue pas une preuve de non-regression.

L'application immediate de la valeur retenue doit etre explicitee dans la conception : un calcul force seul ne prouve pas que l'envoi ne sera pas retarde. Inversement, un appel de controle force ne doit ni utiliser une ouverture brute ni generaliser des effets sur les cycles des autres thermostats.

## Impacts et risques

| Risque                                             | Gravite potentielle | Probabilite / preuve                        | Mesure                                                                         |
| -------------------------------------------------- | ------------------- | ------------------------------------------- | ------------------------------------------------------------------------------ |
| Perte de calibrage si petits mouvements introduits | Elevee              | Contrainte materielle du mainteneur         | Filtre inchange et tests discriminants de sortie de sleep.                     |
| Ouverture obsolete malgre recalcul                 | Elevee              | Deux temporisations distinctes dans le code | Verifier application de la valeur retenue dans le flux complet.                |
| Extension du forcement aux autres thermostats      | Elevee              | Methode de transition partagee              | Condition strictement limitee a la regulation directe over_climate.            |
| Violation inhibition / securite                    | Elevee              | Risque d'integration, pas panne demontree   | Tests des portes de commande et transitions automatiques.                      |
| Commandes supplementaires et consommation batterie | Moyenne             | Plausible, non quantifiee                   | Forcer seulement les vraies transitions ; conserver deduplication et dpercent. |
| Concurrence, capteur absent, reprise               | Moyenne a elevee    | Limites preexistantes, non reproduites      | Tests cibles, sans refonte ni nouvelle politique.                              |

Pas de nouvelle exposition de donnees attendue, pas de migration ni de dependance nouvelle. Documenter l'exception de periode et le maintien de la protection de calibrage. Le cout batterie depend des commandes et mouvements effectifs, pas du recalcul logiciel lui-meme.

## Alternatives

- Forcer seulement le recalcul : changement court, mais application immediate a demontrer dans le flux complet.
- Forcer le traitement de transition dans le perimetre cible : approche recommandee, sous reserve du maintien des filtres et des protections ; ne pas forcer globalement tous les thermostats.
- Remettre seulement le cache a zero en OFF : insuffisant pour les transitions directes de sleep.
- Ajouter une memoire persistante de mode calcule/envoye ou contourner dpercent : hors approche retenue.

## Validation et suite

Verifier avant toute release : entree et sortie de sleep, `sleep -> off -> heat`, reprise a froid, petite variation protegee, fermeture a 0 %, bornes exactes de dpercent, absence de forcement sur mode inchange, retour a la cadence normale, ouverture identique, multi-vannes et min/max. Ajouter les transitions automatiques, COOL si supporte, inhibition, recalibrage et capteurs absents puis retablis. Verifier les types de thermostat exclus et executer la suite de regression sur l'implementation finale.

Une beta ciblee reste recommandee, avec traces des commandes Zigbee2MQTT et des ouvertures, etats de chauffe et chaudiere, observation du calibrage et de la cadence. Distinguer une ouverture maintenue intentionnellement par dpercent d'une ouverture obsolete par temporisation.

Le mainteneur a autorise dans le tour courant la correction des rapports, les specifications et la conception. La revue croisee des deux specialistes confirme le meme perimetre, la couverture des exigences et criteres d'acceptation, l'absence de contradiction documentaire bloquante et une solution techniquement realisable et testable. Les effets existants du forcement sur scheduler, callbacks et learning restent a verifier par les tests prevus ; la convergence documentaire ne vaut pas validation d'implementation.

Un nouvel accord explicite est requis avant le developpement. Aucune implementation ni publication n'est autorisee par ce rapport.