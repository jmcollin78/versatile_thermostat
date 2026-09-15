# Revue de l’issue #1938 — mode sommeil pour `over_valve`

- **Référence :** [issue #1938](https://github.com/jmcollin78/versatile_thermostat/issues/1938)
- **État vérifié :** ouverte ; libellés `enhancement`, `Vote needed` et `P1` ; aucun assigné, jalon, relation ou pull request associé.
- **Branche de développement indiquée par GitHub :** `1938-feature-request-implement-sleep-mode-for-vtherm-over_valve`, créée et actuellement annoncée comme trois commits en avance sur `main`. Ses commits visibles portent sur l’issue #1348, pas sur l’implémentation de #1938.
- **Date de revue :** 15 septembre 2026
- **Recommandation :** **retenir**. Le comportement sera aligné sur l’implémentation existante de `over_climate` avec régulation directe de vanne : thermostat arrêté, demande de vanne brute à 100 % et aucune demande de chauffage/chaudière centrale.

## 1. Résumé fidèle de l’issue

L’issue demande d’étendre le **Sleep Mode** aux VTherm de type `over_valve`. Ce mode est actuellement disponible uniquement pour un VTherm `over_climate` utilisant la régulation directe de vanne.

Le cas d’usage du demandeur est d’ouvrir les TRV à 100 % sans demander de chauffage à la chaudière centrale. Aujourd’hui, l’utilisateur doit retirer les TRV pour obtenir cet effet. La discussion d’origine [#1937](https://github.com/jmcollin78/versatile_thermostat/discussions/1937) confirme ce besoin ; le mainteneur a jugé l’idée pertinente et l’a transformée en issue. Aucun commentaire n’est présent dans l’issue elle-même au moment de cette revue. L’issue totalise huit votes visibles.

## 2. Sources et éléments vérifiés

### Sources GitHub

- [Issue #1938](https://github.com/jmcollin78/versatile_thermostat/issues/1938) : titre, description, état, libellés, votes, branche de développement et absence de relations/pull request.
- [Discussion #1937](https://github.com/jmcollin78/versatile_thermostat/discussions/1937) : cas d’usage, confirmation explicite par le mainteneur et retour positif de l’auteur.
- [Branche associée à #1938](https://github.com/jmcollin78/versatile_thermostat/tree/1938-feature-request-implement-sleep-mode-for-vtherm-over_valve) : trois commits visibles en avance sur `main`, dont le plus récent est relatif à #1348. Aucun élément public ne permet d’affirmer que #1938 y est déjà implémentée.

### Dépôt local

- [custom_components/versatile_thermostat/climate.py](../../custom_components/versatile_thermostat/climate.py#L128-L141) enregistre le service `set_hvac_mode_sleep` pour toutes les entités de l’intégration.
- [custom_components/versatile_thermostat/base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py#L915-L927) limite par défaut les modes HVAC à `HEAT`/`OFF` (ou `HEAT`/`COOL`/`OFF`) et [custom_components/versatile_thermostat/base_thermostat.py](../../custom_components/versatile_thermostat/base_thermostat.py#L2274-L2291) lève une erreur pour le service sommeil hors type pris en charge.
- [custom_components/versatile_thermostat/thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L341-L348), [custom_components/versatile_thermostat/thermostat_climate_valve.py](../../custom_components/versatile_thermostat/thermostat_climate_valve.py#L426-L447) apportent l’implémentation de référence : exposition du mode `SLEEP`, état `is_sleeping` et service qui sélectionne ce mode.
- [custom_components/versatile_thermostat/underlyings.py](../../custom_components/versatile_thermostat/underlyings.py#L1452-L1502) place la demande brute à 100 % dans le chemin de contrôle spécifique à `UnderlyingValveRegulation` lorsqu’un VTherm est endormi, sans considérer l’équipement comme actif. La demande est ensuite convertie par [custom_components/versatile_thermostat/underlyings.py](../../custom_components/versatile_thermostat/underlyings.py#L1519-L1543) : elle reste donc soumise à `max_opening_degrees` et aux limites de l’entité `number`.
- [custom_components/versatile_thermostat/thermostat_valve.py](../../custom_components/versatile_thermostat/thermostat_valve.py#L27-L68) ne redéfinit pas la liste des modes HVAC, `is_sleeping` ni le service sommeil. Il conserve ainsi la liste héritée et l’appel de service échoue via la classe de base.
- [custom_components/versatile_thermostat/thermostat_valve.py](../../custom_components/versatile_thermostat/thermostat_valve.py#L280-L356) et [custom_components/versatile_thermostat/underlyings.py](../../custom_components/versatile_thermostat/underlyings.py#L1323-L1364) montrent que `over_valve` transmet aujourd’hui la demande TPI à `UnderlyingValve`, sans chemin sommeil équivalent à `UnderlyingValveRegulation`.
- [tests/test_overclimate_valve.py](../../tests/test_overclimate_valve.py#L597-L777) couvre la transition `HEAT → SLEEP → HEAT` : mode Home Assistant affiché `OFF`, position de vanne forcée à 100 %, `is_sleeping` vrai, action HVAC `OFF` et zéro équipement actif.
- [tests/test_valve.py](../../tests/test_valve.py#L19-L120) vérifie que l’initialisation d’un `over_valve` n’expose actuellement que `HEAT` et `OFF`; aucun test sommeil pour ce type n’existe.
- [custom_components/versatile_thermostat/services.yaml](../../custom_components/versatile_thermostat/services.yaml#L132-L140) et [documentation/fr/reference.md](../fr/reference.md#L438-L446) restreignent encore la description utilisateur du sommeil à `over_climate` avec contrôle direct de vanne.
- [documentation/fr/over-valve.md](../fr/over-valve.md#L1-L74) décrit le cas d’usage d’une entité `number` de vanne, mais pas le mode sommeil.

## 3. Analyse de pertinence

### Faits établis

1. La fonctionnalité demandée n’est pas disponible pour `over_valve` : ce type n’expose pas `SLEEP`, ne déclare pas `is_sleeping` et son service sommeil hérité échoue.
2. La même expérience est déjà implémentée et testée pour `over_climate` avec contrôle direct de vanne.
3. Le besoin est cohérent avec la finalité documentée de `over_valve`, qui pilote une ou plusieurs entités `number` lorsque le TRV ne fournit pas d’entité `climate`.
4. Le mécanisme actuel de `over_climate` en sommeil sépare volontairement une demande de vanne brute à 100 % de l’activité de chauffage : les vannes reçoivent la commande résultante, tandis que l’action HVAC et les équipements actifs restent à l’arrêt. La commande physique peut être inférieure à 100 % si `max_opening_degrees` ou les bornes de l’entité la limitent.
5. Les paramètres de contrôle d’ouverture issus de #1348 sont déjà présents pour `over_valve` sur la branche examinée. Ils sont hors périmètre fonctionnel de #1938 et ne doivent pas être modifiés par cette évolution.

### Recommandation

**Retenir l’issue.** La valeur utilisateur est claire, les retours communautaires sont significatifs et un modèle fonctionnel existe déjà dans le même projet. La faisabilité paraît élevée, à condition de ne pas réutiliser aveuglément le chemin `UnderlyingValveRegulation`, qui est spécifique à l’architecture `over_climate`.

## 4. Périmètre proposé

### Inclus

- Rendre `SLEEP` disponible dans la liste des modes HVAC de `ThermostatOverValve` : `HEAT`, `SLEEP`, `OFF` (et `COOL`, `SLEEP`, `OFF` en mode climatisation, conformément à la convention existante).
- Faire aboutir le service `versatile_thermostat.set_hvac_mode_sleep` pour `over_valve` et le faire sélectionner `SLEEP`.
- Définir `is_sleeping` pour `over_valve` à partir du mode interne `SLEEP`.
- Pendant le sommeil, appliquer à toutes les vannes `number` sous-jacentes une demande brute de 100 %, puis conserver la conversion habituelle de contrôle d’ouverture. Ainsi, comme pour `over_climate`, `max_opening_degrees` et les limites de l’entité peuvent plafonner la commande physique.
- Conserver le thermostat présenté dans l’état HVAC `OFF`, avec `hvac_action` à `OFF`, aucun équipement actif et aucune demande transmise au contrôle de chaudière centrale.
- À la sortie de sommeil, restaurer le comportement de régulation normal (mode demandé, consigne et préréglage inchangés), puis renvoyer la commande TPI/vanne effective courante.
- Inclure les configurations `AC mode` : bien qu’atypique pour une vanne, cette option est proposée par `over_valve`; elle doit donc exposer `COOL`, `SLEEP`, `OFF` et respecter la même sémantique de sommeil.
- Ajouter des tests couvrant au minimum : disponibilité du mode, service dédié, transition `HEAT → SLEEP → HEAT`, demande brute à 100 %, commande plafonnée lorsque `max_opening_degrees` l’impose, états/action/activité, absence de sollicitation de chaudière, plusieurs vannes, `AC mode` et interaction avec les paramètres #1348.
- Mettre à jour la description du service, les traductions et toutes les documentations existantes concernées dans les cinq langues publiées : anglais, français, allemand, tchèque et polonais.

### Exclus

- Modifier le comportement de sommeil existant pour `over_climate` avec contrôle direct de vanne.
- Modifier les formules, la configuration ou les valeurs par défaut de `opening_threshold_degree`, `min_opening_degrees`, `max_opening_degrees` et `max_closing_degree` (#1348).
- Créer une entité `climate` factice ou une compatibilité spécifique à un fabricant de TRV.
- Ajouter un nouveau paramètre configurable au mode sommeil (par exemple un pourcentage d’ouverture autre que 100 %).
- Modifier l’état d’une installation Home Assistant durant l’analyse ou la phase de conception.

## 5. Impacts et risques

| Domaine                    | Impact / risque                                                                                                                                      | Gravité | Probabilité | Mesure proposée                                                                                 |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ----------- | ----------------------------------------------------------------------------------------------- |
| Fonctionnel                | La demande brute à 100 % ou la commande plafonnée attendue ne sont pas appliquées, ou les vannes restent ouvertes après la sortie de sommeil.        | Élevée  | Moyenne     | Tests de transitions, de plafonnement et commande explicite de remise en régulation.            |
| Chauffage central          | Le thermostat endormi est compté comme actif et déclenche la chaudière.                                                                              | Élevée  | Moyenne     | Garantir `hvac_action=OFF`, zéro équipement actif et tester l’intégration du boiler central.    |
| Compatibilité              | Une installation `over_valve` existante change de comportement hors sélection explicite de `SLEEP`.                                                  | Élevée  | Faible      | Ne modifier que les chemins associés au nouveau mode ; tests de non-régression `HEAT`/`OFF`.    |
| Paramètres #1348           | Le sommeil diverge de `over_climate` en contournant ou en appliquant différemment `max_opening_degrees`, ou ces paramètres sont cassés à la reprise. | Moyenne | Moyenne     | Réutiliser strictement la conversion existante et tester avec des paramètres non neutres.       |
| Multi-vannes               | Une seule vanne est ouverte, ou une vanne reçoit une valeur erronée.                                                                                 | Élevée  | Faible      | Test à plusieurs entités `number`, chacune vérifiée à 100 %.                                    |
| Énergie / confort          | L’utilisateur laisse les vannes ouvertes sans circulation d’eau ou avec un mode chaudière non anticipé.                                              | Moyenne | Moyenne     | Documenter précisément le cas d’usage et le fait que le sommeil ne réclame pas le chauffage.    |
| Documentation/UI           | Le service apparaît sur tous les VTherm mais son support réel reste ambigu.                                                                          | Faible  | Moyenne     | Corriger `services.yaml`, attributs de référence, pages par type et prérequis UI si nécessaire. |
| Sécurité / confidentialité | Aucun nouveau secret, accès réseau ou traitement de donnée personnelle.                                                                              | Faible  | Faible      | Aucune mesure particulière au-delà des pratiques existantes.                                    |

## 6. Alternatives examinées

1. **Utiliser un `over_climate` avec régulation directe de vanne.**
   - Avantage : le sommeil est déjà disponible.
   - Inconvénients : exige une entité `climate`, alors que le besoin porte précisément sur un TRV exposant seulement une entité `number`; ne répond pas nativement au cas d’usage.

2. **Retirer manuellement les TRV ou les ouvrir par une automatisation externe.**
   - Avantage : aucun développement de l’intégration.
   - Inconvénients : opération manuelle ou automatisation non intégrée, perte des états cohérents et risque de faire intervenir involontairement la chaudière.

3. **Étendre `over_valve` avec la sémantique sommeil existante.**
   - Avantages : expérience homogène, cas d’usage couvert sans équipement factice, forte réutilisation des règles d’état et de tests.
   - Inconvénient : demande un chemin de commande spécifique, car `UnderlyingValve` et `UnderlyingValveRegulation` n’ont pas le même cycle de vie.

## 7. Hypothèses, décisions nécessaires et questions ouvertes

### Décisions actées

1. La cohérence avec `over_climate` prime : le sommeil porte la demande brute à 100 %, mais ne contourne pas `max_opening_degrees` ni les bornes de l’entité. La vérification de [custom_components/versatile_thermostat/underlyings.py](../../custom_components/versatile_thermostat/underlyings.py#L1519-L1543) confirme que l’implémentation `over_climate` actuelle applique cette conversion après le passage en sommeil.
2. `AC mode` est inclus. Ce cas est potentiellement atypique, mais l’option est exposée par `over_valve`; elle doit donc rester fonctionnelle et cohérente avec les modes proposés par l’interface.
3. Toutes les documentations et traductions existantes concernées seront mises à jour dans les cinq langues publiées.

### Hypothèse restante à confirmer

- La persistance des consignes et préréglages à travers les transitions `HEAT → SLEEP → HEAT` doit être identique au comportement actuel de `over_climate`.

### Questions ouvertes non bloquantes

- La VTherm UI Card représente-t-elle déjà le mode `SLEEP` pour un type `over_valve`, ou une mise à jour coordonnée de cette dépendance est-elle requise ? L’issue et le dépôt examinés ne permettent pas de le déterminer.
- Les conditions de contrôle chaudière centralisées disposent-elles d’un test direct pour un `over_valve` endormi ? La couverture devra être vérifiée et complétée pendant la conception.

## 8. Critères de passage au développement

Le développement pourra démarrer après :

1. approbation explicite de ce rapport et du périmètre ;
2. validation fonctionnelle de la demande brute à 100 %, de son plafonnement identique à `over_climate` et de l’absence de demande chaudière ;
3. spécification approuvée décrivant les états, transitions, attributs, service et critères d’acceptation ;
4. conception technique approuvée distinguant clairement le chemin `over_valve` du mécanisme `UnderlyingValveRegulation` ;
5. plan de tests couvrant les cas unitaires et d’intégration listés ci-dessus ;
6. mise à jour planifiée des documentations et traductions existantes dans les cinq langues publiées, et vérification de la compatibilité UI résiduelle.

## 9. Suite proposée

Après validation explicite du rapport, produire une spécification fonctionnelle et une conception technique convergentes, puis les soumettre à validation avant toute implémentation. Aucun code, configuration, dépendance ou état d’environnement Home Assistant n’a été modifié durant cette revue.
