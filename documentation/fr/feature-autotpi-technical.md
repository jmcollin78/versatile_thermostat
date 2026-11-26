# 🧠 Auto TPI : Guide technique approfondi

> [!NOTE]
> Ce document est destiné aux utilisateurs avancés qui souhaitent comprendre en détail le fonctionnement d'Auto TPI. Pour une introduction plus simple, consultez le [Guide utilisateur Auto TPI](feature-autotpi.md).

---

## Table des matières

1. [L'algorithme TPI](#lalgorithme-tpi)
2. [Modèle de pièce et coefficients cibles](#modèle-de-pièce-et-coefficients-cibles)
3. [Cycle d'apprentissage](#cycle-dapprentissage)
4. [Apprentissage de Kint](#apprentissage-de-kint)
5. [Apprentissage de Kext](#apprentissage-de-kext)
6. [Apprentissage continu du Kext](#apprentissage-continu-du-kext)
7. [Paramètres et constantes](#paramètres-et-constantes)
8. [Services et API](#services-et-api)
9. [Diagnostic et dépannage](#diagnostic-et-dépannage)

---

## L'algorithme TPI

### Principe fondamental

L'algorithme **TPI** (Time Proportional & Integral) calcule un **pourcentage de puissance** à chaque cycle. Ce pourcentage détermine la durée pendant laquelle le chauffage sera actif durant le cycle (ex. : 60 % sur un cycle de 10 minutes = 6 minutes de chauffe).

### Formule de base

```
Power = (Kint × ΔT_indoor) + (Kext × ΔT_outdoor)
```

Où :
- **Kint** (`tpi_coef_int`) : coefficient intérieur, réagit à l'écart avec la consigne
- **Kext** (`tpi_coef_ext`) : coefficient extérieur, compense les pertes thermiques
- **ΔT_indoor** = consigne − température intérieure
- **ΔT_outdoor** = consigne − température extérieure

La puissance est limitée à 0–100 %. En mode refroidissement, les écarts sont inversés.

### Rôle des coefficients

| Coefficient | Rôle | Situation d'apprentissage |
|-------------|------|---------------------------|
| **Kint** | Règle la **réactivité** : plus il est élevé, plus le chauffage réagit fortement à un écart | Pendant une **montée en température** (écart ≥ 0,3°C au début d'une fenêtre, puissance entre 0 et 100 %) |
| **Kext** | Compense les **pertes thermiques** : il fournit la puissance nécessaire pour maintenir la consigne | Lorsque la pièce est **stabilisée autour de la consigne** |

---

## Modèle de pièce et coefficients cibles

Auto TPI s'appuie sur un modèle simple de pièce (une capacité thermique, une perte vers l'extérieur) :

```
dT/dt = a × P − b × (T − T_ext)
```

- `a` (°C/h) : vitesse de montée en température à 100 % de puissance, sans pertes
- `b` (1/h) : vitesse de perte, inverse de la constante de temps de la pièce
- `P` : puissance de chauffe (0–1)

**Kext** : à la consigne, la puissance nécessaire est `P = (b/a) × (Consigne − T_ext)`. Le Kext idéal est donc `b/a`. Avec cette valeur, le seul terme extérieur maintient la consigne et aucun écart statique ne subsiste.

**Kint** : une fois que Kext compense les pertes, la pièce monte à `a × Kint × écart`. Pour combler l'écart avec une constante de temps `T_cl`, Kint doit valoir `1 / (a × T_cl)`. Un émetteur peu puissant (petit `a`) nécessite donc un Kint plus grand.

`T_cl` est la constante de temps cible en boucle fermée. Elle est dérivée du **temps de chauffe** de l'émetteur :

```
T_cl = 2 × (heating_time + cycle / 2)     bornée à [30 min, 180 min]
```

Un émetteur lent (temps de chauffe long) donne un `T_cl` plus grand, donc une régulation plus douce qui ne dépasse pas la consigne.

Ni `a` ni `b` n'ont besoin d'être connus : les deux coefficients sont appris à partir des observations, par petits pas, vers ces cibles.

---

## Cycle d'apprentissage

À la fin de chaque cycle TPI, le gestionnaire vérifie le cycle et met à jour l'apprentissage.

### Photographie du cycle

Au début de chaque cycle, le système enregistre les températures intérieure et extérieure, la consigne, la puissance et le mode HVAC. À la fin du cycle, c'est la puissance effectivement appliquée (après les contraintes de temporisation) qui est utilisée.

### Conditions de validation d'un cycle

Un cycle est ignoré pour l'apprentissage si :

| Condition | Raison |
|-----------|--------|
| Puissance ≤ 0 % ou ≥ 100 % | Un cycle saturé ne dit rien sur la puissance à appliquer |
| Cycle plus court ou plus long que prévu | Cycle interrompu ou trou dans les données |
| Délestage pendant le cycle | Le chauffage a été limité par une autre fonctionnalité |
| Chaudière centrale éteinte | L'émetteur n'a pas chauffé |
| Défaut de chauffe détecté | L'émetteur n'a pas chauffé comme demandé |
| Premier cycle après un arrêt | Pas d'état précédent |
| Consigne modifiée pendant le cycle | Le cycle mélange deux cibles |
| \|Consigne − T_ext\| < 1°C (Kext) | Le terme extérieur est trop petit pour être appris |

### Fin de session

La session se termine lorsque Kint a été appris sur **15 fenêtres** et Kext sur **50 cycles**. Les coefficients sont alors écrits dans la configuration et une notification est envoyée.

---

## Apprentissage de Kint

Kint est appris sur des **fenêtres** de plusieurs cycles consécutifs, jamais sur un seul cycle : sur un cycle de 5 minutes, la variation de température est du même ordre que la résolution du capteur (souvent 0,1°C).

### Règles des fenêtres

- Une fenêtre s'ouvre lorsque la pièce est à au moins **0,3°C** de la consigne, et seulement **T_cl / 2** après le dernier changement de consigne, de mode ou cycle invalide (l'émetteur a besoin de ce temps pour réagir).
- Chaque cycle de la fenêtre doit être valide avec une puissance comprise entre 0 et 100 %. Sinon, la fenêtre est fermée sans apprentissage.
- Une fenêtre dure au moins **max(30 min, T_cl)**. La fenêtre suivante commence là où la précédente se termine, sous la même condition de 0,3°C.
- Une fenêtre est acceptée uniquement sur sa durée et son écart de départ. Elle ne dépend jamais de la variation de température mesurée : sinon, seules les fenêtres où le bruit a augmenté la montée seraient conservées, ce qui biaiserait Kint.

### Formule de mise à jour

```
mean_gap    = Setpoint − (T_start + T_end) / 2
target_rate = mean_gap / T_cl
rate        = (T_end − T_start) / duration
ratio       = target_rate / rate          (1.15 if rate ≤ 0)
Kint_new    = Kint × clamp(ratio, 1/1.15, 1.15)
```

Kint varie d'au plus ±15 % par fenêtre et reste dans [0,01 ; 1,0]. Un pas borné converge vers la médiane du ratio : une fenêtre isolée perturbée par le bruit ou par le soleil ne peut pas beaucoup déplacer Kint.

Si la pièce a franchi la consigne pendant la fenêtre (`mean_gap ≤ 0`), la fenêtre n'est pas utilisée.

---

## Apprentissage de Kext

### Condition de stabilisation

La montée après un changement de consigne relève de Kint. Kext n'est appris que :
- au moins **3 × T_cl** après le dernier changement de consigne,
- et une fois la pièce revenue à moins de **0,3°C** de la consigne, ou après **12 × T_cl**, afin qu'un Kext très faux (grand écart statique) puisse encore être corrigé.

### Formule

Lorsque la pièce est stabilisée et que l'écart est faible (|écart| ≤ 1°C, ou tout écart au-dessus de la consigne tant que la puissance est d'au moins 10 %) :

```
Kext_target = Kext + Kint × (ΔT_indoor / ΔT_outdoor)
```

L'écart intérieur restant est converti en puissance extérieure qui le supprimerait. `Kext_target` est limité à 1,2.

Les échantillons au-dessus de la consigne sont ignorés lorsque la puissance est très faible (la pièce se refroidit naturellement, ou une source externe la chauffe).

### Lissage

Les échantillons sont combinés par une **moyenne pondérée** :

```
Kext_new = (Kext × n + Kext_target) / (n + 1)       n = number of samples, capped at 50
```

Le Kext configuré n'a pas de poids : le premier échantillon le remplace, puis chaque échantillon pèse 1/(n+1). Pour une grandeur fixe, la moyenne donne l'estimation la moins bruitée.

---

## Apprentissage continu du Kext

Lorsque l'**Apprentissage continu du Kext** est activé, Kext continue d'être ajusté après la session, pour suivre les lentes variations des pertes thermiques.

### Conditions d'éligibilité
- Au moins un échantillon de Kext issu d'une session d'apprentissage.
- Mêmes conditions de cycle et de stabilisation que pour l'apprentissage de Kext.

### Formule

```
Kext_new = Kext × (1 − α) + Kext_target × α        α = 0.04
```

Un poids fixe permet à Kext de suivre une grandeur qui dérive lentement. La nouvelle valeur est écrite dans la configuration lorsqu'elle change de plus de 0,001.

---

## Paramètres et constantes

### Paramètres configurables

| Paramètre | Description |
|-----------|-------------|
| `heater_heating_time` | Temps de chauffe de l'émetteur (min). Fixe `T_cl`. |
| `auto_tpi_continuous_kext` | Apprentissage continu du Kext après la session. |

### Constantes internes

| Constante | Valeur | Rôle |
|-----------|--------|------|
| Écart minimum pour une fenêtre de Kint | 0,3°C | Kint n'est appris que lorsque la pièce a un écart à combler |
| Durée minimum d'une fenêtre | 30 min (ou T_cl si plus long) | Plusieurs pas du capteur par fenêtre |
| Pas maximum de Kint | ×1,15 / ÷1,15 | Pas borné par fenêtre |
| Bornes de Kint | 0,01 – 1,0 | |
| Fenêtres de Kint pour terminer la session | 15 | |
| Cycles de Kext pour terminer la session | 50 | |
| Stabilisation de Kext | 3 × T_cl, puis proche de la consigne (ou 12 × T_cl) | Kext n'est pas appris pendant une montée |
| Écart maximum pour Kext | 1,0°C | |
| Kext maximum | 1,2 | |
| Alpha de l'apprentissage continu du Kext | 0,04 | |

---

## Services et API

### `versatile_thermostat.set_auto_tpi_mode`

Démarre ou arrête une session d'apprentissage.

| Paramètre | Type | Description |
|-----------|------|-------------|
| `auto_tpi_mode` | booléen | `true` pour démarrer, `false` pour arrêter |
| `reinitialise` | booléen | `true` (par défaut) : repart des coefficients configurés. `false` : reprend la session précédente |

```yaml
service: versatile_thermostat.set_auto_tpi_mode
target:
  entity_id: climate.living_room
data:
  auto_tpi_mode: true
  reinitialise: true
```

---

## Diagnostic et dépannage

### Capteur de diagnostic

Entité : `sensor.<name>_auto_tpi_learning_state`

État : `active` pendant une session, `off` sinon.

| Attribut | Description |
|----------|-------------|
| `heating_cycles_count` | Total des cycles observés |
| `coeff_int_cycles` | Fenêtres Kint apprises |
| `coeff_ext_cycles` | Cycles Kext appris |
| `model_confidence` | Avancement de la session 0,0 – 1,0 |
| `calculated_coef_int` | Kint actuel |
| `calculated_coef_ext` | Kext actuel |
| `last_learning_status` | Résultat du dernier cycle |
| `learning_start_dt` | Début de la session |

### Statuts d'apprentissage courants

| Statut | Signification |
|--------|---------------|
| `learned_indoor_heat` / `learned_indoor_cool` | Kint mis à jour à la fin d'une fenêtre |
| `learned_outdoor_heat` / `learned_outdoor_cool` | Kext mis à jour |
| `kext_waiting_settling` | Kext attend que la pièce se stabilise après un changement de consigne |
| `kint_window_crossed_setpoint` | La pièce a franchi la consigne pendant la fenêtre, fenêtre non utilisée |
| `power_out_of_range(...)` | Puissance à 0 % ou 100 %, cycle ignoré |
| `cycle_gap_detected` / `cycle_too_short` | Durée de cycle anormale, cycle ignoré |
| `setpoint_changed_during_cycle` | Consigne modifiée pendant le cycle |
| `outdoor_delta_too_small(...)` | Température extérieure trop proche de la consigne |
| `gap_too_large_for_outdoor(...)` | Écart supérieur à 1°C, Kext non appris |
| `cooling_down_naturally` / `warming_up_naturally` | La pièce revient seule vers la consigne, Kext inchangé |
| `continuous_kext_learned_heat` / `continuous_kext_learned_cool` | Kext mis à jour par l'apprentissage continu |

### Dépannage

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| Kint ne progresse pas | Aucune montée d'au moins 0,3°C avec une puissance non saturée | Baisser la consigne de 1 à 2°C pendant quelques heures, puis la remonter |
| Dépassement après chaque montée | Temps de chauffe trop court pour l'émetteur | Augmenter le temps de chauffe, puis relancer une session |
| Montée lente, sans dépassement | Temps de chauffe trop long | Diminuer le temps de chauffe, puis relancer une session |
| Pièce toujours sous ou au-dessus de la consigne | Kext pas encore appris, ou pertes modifiées | Laisser la session se terminer, ou activer l'apprentissage continu du Kext |
| Aucun progrès d'apprentissage | Chauffage toujours à 100 % (grand froid) | Attendre un temps plus doux |

### Fichier de persistance

**Emplacement** : `.storage/versatile_thermostat.auto_tpi.<unique_id>`

Ce fichier contient l'état de l'apprentissage et est restauré au redémarrage de Home Assistant. Tant qu'aucun cycle d'apprentissage n'a été enregistré, les coefficients configurés sont utilisés.
