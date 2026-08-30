# Faire consulter les visuels à quelqu'un d'extérieur

## Le lien

```
https://air-et-energie-en-corse.s3.fr-par.scw.cloud/index.html
```

Rien d'autre à faire : un navigateur suffit, pas de compte, pas d'installation.

**Le `/index.html` final est obligatoire.** La racine seule répond 403 : le bucket est privé
en *listage* (personne ne peut inventorier les fichiers), seuls les objets déposés par le
cron sont publics. C'est le comportement voulu, pas une panne.

## Ce qu'il voit

La page d'entrée mène aux deux études — l'électricité et l'ozone — chacune avec sa note
méthodologique. Les figures sont interactives (survol, zoom) et se lisent dans la page.

Chaque figure est aussi une page autonome (`t4_heure_verte.html`, `a2_ozone_et_chaleur.html`…)
qui s'intègre en `<iframe>` sans dépendance tierce, si l'interlocuteur veut en reprendre une.

## Avant d'envoyer le lien

La page d'entrée affiche en haut sa **date de compilation** : le destinataire la voit. Une
vitrine en retard se remarque donc à l'œil nu — vérifier cette date avant d'envoyer, surtout
si le cron a échoué depuis le dernier passage vert.

Au rafraîchissement, **Ctrl+F5** : les pages sont servies avec un cache de 300 s, sinon on
relit l'ancienne version et on croit à tort que le déploiement n'a rien fait.

La vitrine est déposée par le cron (`pipeline.yml`), après les verrous de résultats et
toutes les 6 h. Elle ne se met pas à jour à la main.

## Ce qu'on n'envoie pas

L'URL GitHub : le dépôt est privé, et la vitrine est la seule voie de diffusion. Pas
d'invitation au dépôt non plus.

## Point ouvert — l'URL courte

`https://air-et-energie-en-corse.s3-website.fr-par.scw.cloud` répond **404** (vérifié le
19/08/2026) : l'hébergement statique n'a pas été activé sur le bucket. C'est ce qui oblige à
écrire `/index.html` dans le lien.

Pour l'obtenir : console Scaleway → bucket `air-et-energie-en-corse` → Hébergement statique
→ document d'index `index.html`. L'URL S3 actuelle continuera de fonctionner.
