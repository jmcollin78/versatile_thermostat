# Gestion de la présence / absence

## Configurer la présence (ou l'absence)

Si sélectionnée en première page, cette fonction vous permet de modifier dynamiquement la température de tous les préréglages du thermostat configurés lorsque personne n'est à la maison ou lorsque quelqu'un rentre à la maison. Pour cela, vous devez configurer la température qui sera utilisée pour chaque préréglage lorsque la présence est désactivée. Lorsque le capteur de présence s'éteint, ces températures seront utilisées. Lorsqu'il se rallume, la température "normale" configurée pour le préréglage est utilisée. Voir [gestion des préréglages](#configure-the-preset-temperature).
Pour configurer la présence remplissez ce formulaire :

![image](images/config-presence.png)

Pour cela, vous devez configurer :
1. Un **capteur d'occupation** dont l'état doit être 'on' ou 'home' si quelqu'un est présent ou 'off' ou 'not_home' sinon,
2. La **température utilisée en Eco** prédéfinie en cas d'absence,
3. La **température utilisée en Confort** préréglée en cas d'absence,
4. La **température utilisée en Boost** préréglée en cas d'absence

Si le mode AC est utilisé, vous pourrez aussi configurer les températures lorsque l'équipement en mode climatisation.

ATTENTION : les groupes de personnes ne fonctionnent pas en tant que capteur de présence. Ils ne sont pas reconnus comme un capteur de présence. Vous devez utiliser, un template comme décrit ici [Utilisation d'un groupe de personnes comme capteur de présence](#utilisation-dun-groupe-de-personnes-comme-capteur-de-présence).

> ![Astuce](images/tips.png) _*Notes*_
> 1. le changement de température est immédiat et se répercute sur le volet avant. Le calcul prendra en compte la nouvelle température cible au prochain calcul du cycle,
> 2. vous pouvez utiliser le capteur direct person.xxxx ou un groupe de capteurs de Home Assistant. Le capteur de présence gère les états ``on`` ou ``home`` comme présents et les états ``off`` ou ``not_home`` comme absents.

