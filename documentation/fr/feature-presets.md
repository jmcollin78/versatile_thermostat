# Les pre-réglages (preset)

## Configurer les températures préréglées

Le mode préréglé (preset) vous permet de préconfigurer la température ciblée. Utilisé en conjonction avec Scheduler (voir [scheduler](#even-better-with-scheduler-component) vous aurez un moyen puissant et simple d'optimiser la température par rapport à la consommation électrique de votre maison. Les préréglages gérés sont les suivants :
 - **Eco** : l'appareil est en mode d'économie d'énergie
 - **Confort** : l'appareil est en mode confort
 - **Boost** : l'appareil tourne toutes les vannes à fond

 Si le mode AC est utilisé, vous pourrez aussi configurer les températures lorsque l'équipement en mode climatisation.

**Aucun** est toujours ajouté dans la liste des modes, car c'est un moyen de ne pas utiliser les preset mais une **température manuelle** à la place.

Les pré-réglages se font (depuis v6.0) directement depuis les entités du VTherm ou de la configuration centrale si vous utilisez la configuration centrale.

> ![Astuce](images/tips.png) _*Notes*_
>  1. En modifiant manuellement la température cible, réglez le préréglage sur Aucun (pas de préréglage). De cette façon, vous pouvez toujours définir une température cible même si aucun préréglage n'est disponible.
>  2. Le préréglage standard ``Away`` est un préréglage caché qui n'est pas directement sélectionnable. Versatile Thermostat utilise la gestion de présence ou la gestion de mouvement pour régler automatiquement et dynamiquement la température cible en fonction d'une présence dans le logement ou d'une activité dans la pièce. Voir [gestion de la présence](#configure-the-presence-management).
>  3. Si vous utilisez la gestion du délestage, vous verrez un préréglage caché nommé ``power``. Le préréglage de l'élément chauffant est réglé sur « puissance » lorsque des conditions de surpuissance sont rencontrées et que le délestage est actif pour cet élément chauffant. Voir [gestion de l'alimentation](#configure-the-power-management).
>  4. si vous utilisez la configuration avancée, vous verrez le préréglage défini sur ``sécurité`` si la température n'a pas pu être récupérée après un certain délai
>  5. Si vous ne souhaitez pas utiliser le préréglage, indiquez 0 comme température. Le préréglage sera alors ignoré et ne s'affichera pas dans le composant front