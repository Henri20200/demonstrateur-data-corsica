# Brief du démonstrateur — cadre de travail

**Date butoir : fin août 2026** (rentrée = lancement de la prospection).

## Question fermée (figée le 18/07/2026)
> De quoi est faite l'électricité corse — maintenant, au fil de la journée,
> et au fil des saisons — et quand est-elle la plus renouvelable ?

Titres-affirmations que l'analyse doit valider, invalider ou chiffrer :
1. « En ce moment, votre kWh corse est fait de X % de soleil » (temps réel, 15 min)
2. « On voit les touristes arriver dans la courbe » (charge été vs printemps : +X %)
3. « À midi, l'île tourne au soleil ; le soir, elle tire sur l'Italie » (profil horaire)
4. « L'heure la plus verte pour consommer en Corse est XXhXX » (conclusion actionnable)


## Test du prompt (critère éliminatoire)
Si un LLM généraliste peut produire l'équivalent du livrable en 15 minutes,
ce n'est pas le bon livrable. Ici : donnée d'il y a 15 minutes + pipeline
récurrent + manifeste daté/empreinté → le test passe.

Critères de choix du jeu de données :
1. parle à un acheteur identifiable (collectivité, cabinet, fédération) ;
2. mis à jour régulièrement (le « daté, sourcé » doit se voir) ;
3. permet un « qu'est-ce que ça change pour vous » pédagogique ;
4. croisable avec une source nationale (INSEE, DVF) → démontrer l'assemblage multi-sources.

## Définition de « fini »
- [ ] une page interactive exportée en HTML déployable en iframe sans dépendance
      tierce (pas de CDN ; `plotly.min.js` mutualisé dans `outputs/`, à déployer d'un bloc)
- [ ] une note méthodologique : sources, dates de collecte, limites, licences
- [ ] ce repo public et propre (le repo EST une preuve de sérieux)
- [ ] mention de source visible sur chaque visuel

## Anti-dérive
Timebox : 3-4 semaines. Si ça déborde : réduire l'ambition, pas la deadline.


