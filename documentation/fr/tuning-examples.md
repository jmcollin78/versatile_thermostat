# Exemples de réglage

## Chauffage électrique
- cycle : entre 5 et 10 minutes,
- minimal_activation_delay_sec : 30 secondes

## Chauffage central (chauffage gaz ou fuel)
- cycle : entre 30 et 60 min,
- minimal_activation_delay_sec : 300 secondes (à cause du temps de réponse)

## Le capteur de température alimenté par batterie
- security_delay_min : 60 min (parce que ces capteurs sont paresseux)
- security_min_on_percent : 0,5 (50% - on passe en preset ``security`` si le radiateur chauffait plus de 50% du temps)
- security_default_on_percent : 0,1 (10% - en preset ``security``, on garde un fond de chauffe de 20% du temps)

Il faut comprendre ces réglages comme suit :

> Si le thermomètre n'envoie plus la température pendant 1 heure et que le pourcentage de chauffe (``on_percent``) était supérieur à 50 %, alors on ramène ce pourcentage de chauffe à 10 %.

A vous d'adapter ces réglages à votre cas !

Ce qui est important c'est de ne pas prendre trop de risque avec ces paramètres : supposez que vous êtes absent pour une longue période, que les piles de votre thermomètre arrivent en fin de vie, votre radiateur va chauffer 10% du temps pendant toute la durée de la panne.

Versatile Thermostat vous permet d'être notifié lorsqu'un évènement de ce type survient. Mettez en place, les alertes qui vont bien dès l'utilisation de ce thermostat. Cf. (#notifications)

## Capteur de température réactif (sur secteur)
- security_delay_min : 15 min
- security_min_on_percent : 0,7 (70% - on passe en preset ``security`` si le radiateur chauffait plus de 70% du temps)
- security_default_on_percent : 0,25 (25% - en preset ``security``, on garde un fond de chauffe de 25% du temps)

## Mes presets
Ceci est juste un exemple de la façon dont j'utilise le préréglage. A vous de vous adapter à votre configuration mais cela peut être utile pour comprendre son fonctionnement.
``Hors gel`` : 10 °C
``Éco`` : 17 °C
``Confort`` : 19 °C
``Boost`` : 20 °C

Lorsque la présence est désactivée :
``Hors gel`` : 10 °C
``Éco`` : 16,5 °C
``Confort`` : 17 °C
``Boost`` : 18 °C

Le détecteur de mouvement de mon bureau est configuré pour utiliser ``Boost`` lorsqu'un mouvement est détecté et ``Eco`` sinon.