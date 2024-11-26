#### Le démarrage / arrêt automatique
Cette fonction a été introduite en 6.5.0. Elle permet d'autoriser VTherm a stopper un équipement qui n'a pas besoin d'être allumé et de le redémarrer lorsque les conditions le réclame. Cette fonction est munie de 3 réglages qui permettent d'arrêter / relancer plus ou moins rapidement l'équipement.

Pour l'utiliser, vous devez :
1. Ajouter la fonction `Avec démmarrage et extinction automatique` dans le menu 'Fonctions',
2. Paramétrer le niveau de détection dans l'option 'Allumage/extinction automatique' qui s'affiche lorsque la fonction a été activée. Vous choisissez le niveau de détection entre 'Lent', 'Moyen' et 'Rapide'. Les arrêts/relances seront plus nombreux avec le niveau 'Rapide'.

Une fois paramétré, vous aurez maintenant une nouvelle entité de type `switch` qui vous permet d'autoriser ou non l'arrêt/relance automatique sans toucher à la configuration. Cette entité est disponible sur l'appareil VTherm et se nomme `switch.<name>_enable_auto_start_stop`. Cochez la pour autoriser le démarrage et extinction automatique.

L'algorithme de détection est décrit [ici](https://github.com/jmcollin78/versatile_thermostat/issues/585).