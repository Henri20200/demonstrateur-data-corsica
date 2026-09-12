# Faire consulter les études à quelqu'un d'extérieur

## Le lien

```
https://www.methodes-revelations.fr/
```

C'est la page de présentation. Elle mène à l'étude par son bouton « Consulter l'étude ».
Rien d'autre à faire : un navigateur suffit, pas de compte, pas d'installation.
`https://methodes-revelations.fr/` (sans `www`) y redirige.

Pour pointer directement l'étude, sans passer par la page :

```
https://air-et-energie-en-corse.s3.fr-par.scw.cloud/index.html
```

**Là, le `/index.html` final est obligatoire.** La racine seule répond 403 : le bucket est
privé en *listage* (personne ne peut inventorier les fichiers), seuls les objets déposés par
le cron sont publics. C'est le comportement voulu, pas une panne.

## Ce qu'il voit

La page d'entrée de l'étude mène aux deux volets — l'électricité et l'ozone — chacun avec
sa note méthodologique. Les figures sont interactives (survol, zoom) et se lisent dans la
page.

Chaque figure est aussi une page autonome (`t4_heure_verte.html`, `a2_ozone_et_chaleur.html`…)
qui s'intègre en `<iframe>` sans dépendance tierce, si l'interlocuteur veut en reprendre une.

## Avant d'envoyer le lien

La page d'entrée de l'étude affiche en haut sa **date de compilation** : le destinataire la
voit. Une vitrine en retard se remarque donc à l'œil nu — vérifier cette date avant
d'envoyer, surtout si le cron a échoué depuis le dernier passage vert.

Au rafraîchissement, **Ctrl+F5** : les pages de l'étude sont servies avec un cache de 300 s,
sinon on relit l'ancienne version et on croit à tort que le déploiement n'a rien fait.

L'étude est déposée par le cron (`pipeline.yml`), après les verrous de résultats et toutes
les 6 h. Elle ne se met pas à jour à la main.

## Le dépôt GitHub

Public depuis le 03/09/2026. Il peut accompagner le lien pour un lecteur technique — le
BRIEF en fait une preuve de sérieux — mais il n'est pas la voie de lecture : on lit
l'étude sur la vitrine, on vérifie sur le dépôt.

## Où vit la page de présentation

Hors dépôt. Projet Scaleway `methodes-revelations` (distinct du projet de l'étude) :
bucket `methodes-revelations` (privé en listage, objets publics par bucket policy, Bucket
Website activé) devant lequel un pipeline Edge Services porte le domaine
`www.methodes-revelations.fr` et son certificat HTTPS, sans cache. Le DNS est chez Gandi
(`www` en CNAME vers le pipeline, apex en redirection web vers `www`).

Mettre la page à jour = déposer un nouvel `index.html` dans le bucket, à la main. Rien à
purger. Le fichier et son script de construction sont dans le dossier frère
`demonstrateur-data-corsica-fichiers`.

## Point ouvert — l'URL courte de l'étude

`https://air-et-energie-en-corse.s3-website.fr-par.scw.cloud` répond **404** (vérifié le
12/09/2026) : l'hébergement statique n'a pas été activé sur le bucket de l'étude. C'est ce
qui oblige à écrire `/index.html` dans son lien direct.

Pour l'obtenir : console Scaleway → bucket `air-et-energie-en-corse` → Paramètres →
Bucket Website → document d'index `index.html`. L'URL actuelle continuera de fonctionner.
