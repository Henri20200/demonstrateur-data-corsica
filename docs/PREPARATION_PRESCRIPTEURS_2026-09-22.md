# Préparation d'une présentation aux prescripteurs — 22 septembre 2026

**État : corrections et aperçu préparés localement ; aucune publication effectuée.**
Ce compte rendu décrit cette session. Il ne reprend pas comme preuves les exécutions
en production relatées par les audits précédents.

## Cadrage corrigé par le porteur

Méthodes & Révélations dispose d'une vitrine et d'un contact :
https://www.methodes-revelations.fr/ — contact@methodes-revelations.fr.
Ces informations ont été fournies par l'utilisateur le 22 septembre. Le site externe
n'a pas été consulté ni modifié pendant cette session.

Le constat initial d'absence d'identification du porteur était trop large. Le travail
effectué concerne l'accueil du démonstrateur, qui donne désormais ce contexte et ce
contact, explique les usages possibles des études et propose un résultat à vérifier.
Une clarification sur l'éventuelle refonte de la vitrine externe a été demandée ;
elle n'a pas été supposée autorisée.

## Changements réalisés

- **Traçabilité, A3 :** refus des lignées vides ou incomplètes, des sorties sans source
  déclarée et de tout Parquet présent hors de la génération vérifiée. Le refus ne
  supprime aucun fichier. Une source absente d'une lignée existante ne peut plus
  emprunter la date d'un autre téléchargement.
- **Présentation :** accueil organisé autour des deux études, d'un résultat vérifiable
  et du contact. Présentation en deux colonnes sur écran large, une colonne sur petit
  écran ; ressources embarquées locales. Le lien vers la vitrine ne charge pas de
  ressource extérieure à l'ouverture de la page.
- **Dates :** distinction entre compilation des pages, observations historiques
  2019–2024, bridage solaire jusqu'en 2023 et dernier relevé de la jauge.
- **Preuve consultable :** page et ZIP de vérification du résultat juin-juillet,
  reliés à l'accueil, à l'étude et à sa note. Leur génération est intégrée aux deux
  workflows, avant les tests de résultats.
- **Tests locaux :** sélection de Git Bash sur Windows pour les tests des workflows,
  comme le faisaient déjà les tests de publication. La découverte pytest est limitée
  au dossier tests pour ne pas parcourir les copies d'audit et les anciens temporaires.
- Les corrections du lot de stabilisation précédent ont été conservées et incluses
  dans la reconstruction et la suite complète.

## Vérifications effectivement exécutées pour le premier lot

Copie isolée : audit/prescripteurs-20260922/.
Les 53 fichiers du manifeste local de la précédente stabilisation ont été copiés
explicitement. Aucune collecte réseau, lecture de fichier de secrets, utilisation
de compte ou opération de déploiement n'a été effectuée.

La reconstruction a produit **12 Parquet à partir de 49 sources vérifiées**, puis les
figures, notes, étude, dossier de preuve et accueil. La couverture air 2020–2025 passe.
La jauge électrique est en mode « affichage suspendu », attendu avec ce cache ancien.
Cela ne décrit pas l'état actuel du site en ligne.

**Suite complète du premier lot : 382 tests réussis, aucun sauté, un test de fraîcheur exclu**
(pytest tests -m "not fraicheur"). Le verrou de fraîcheur ne peut pas attester
d'une collecte actuelle à partir d'une copie ancienne. Ruff passe également.
Le contrôle Git des espaces parasites passe avec la convention CRLF de Windows,
après autorisation de lecture hors de l'environnement isolé. Aucun réglage Git
n'a été enregistré ; les modifications antérieures restent présentes.

Deux obstacles d'environnement ont précédé ce résultat : le dossier temporaire
Windows était inaccessible, puis les tests de workflow choisissaient le lanceur WSL.
Les tests ont été relancés avec des dossiers dédiés au projet et Git Bash. La collecte
pytest a aussi été bornée à tests après un refus d'accès à un ancien temporaire.
Les dossiers refusés n'ont pas été ouverts autrement ni supprimés.

Les versions installées des dépendances principales correspondent à uv.lock :
pandas 2.3.3, DuckDB 1.5.4, Plotly 6.9.0, HTTPX 0.28.1, PyYAML 6.0.3,
defusedxml 0.7.1 et pytest 9.1.1. Le parcours CI des dernières versions n'a pas été lancé.
Les avertissements NumPy/pandas dans les tests de fuseau restent présents ; ils ne
font pas échouer cette validation.

## Résultat rendu reproductible

L'extrait EDF contient **8 784 mesures horaires** :

| Mois | Heures | Moyenne (MW) | Barre affichée (MW) |
|---|---:|---:|---:|
| Juin | 4 320 | 230,870693 | 231 |
| Juillet | 4 464 | 281,415837 | 281 |

L'écart sur les moyennes non arrondies vaut **21,893270 %**. L'annotation du
graphique, calculée sur les deux barres arrondies au MW, affiche **+22 %**.
Le calcul autonome et les données préparées pour le graphique concordent.

Le ZIP contient le CSV, sa provenance, un script Python 3 utilisant seulement la
bibliothèque standard et un mode d'emploi. Son test le décompresse et rejoue le calcul
sans importer le projet ; il vérifie aussi qu'une altération du CSV est refusée.
La source utilisée a été collectée le 22 juillet 2026 et couvre 2019–2024.

## Lot complémentaire ozone, après examen de la capture

Le « go » suivant l'examen de la capture autorise les quatre corrections locales
proposées. La capture montrait un chevauchement du sous-titre et de la première barre ;
elle ne permettait pas de certifier les calculs ni le contenu hors de son cadrage.

- Titre ancré en haut de la figure A4, marge supérieure augmentée et hauteur adaptée
  aux étiquettes sur deux lignes. Les contrôles de gabarit passent ; le rendu navigateur
  n'a pas été observé.
- Chaque barre affiche désormais les jours en dépassement et les jours valides,
  en plus du pourcentage. Les effectifs et les étés disponibles viennent du même
  périmètre de données que les barres.
- Définition visible : maximum journalier de la moyenne glissante sur huit heures,
  strictement supérieur à 120 µg/m³. La note liée précise les règles déjà appliquées :
  au moins six mesures horaires par moyenne et dix-huit moyennes valides par journée.
  Le calcul des moyennes et le seuil n'ont pas été modifiés.
- Période plus courte de Confina 2 affichée ; réserve explicite sur la comparaison
  de pourcentages portant sur des périodes différentes.
- Conclusion limitée aux stations comparées et à l'ozone, avec retrait de l'explication
  causale de l'encart. Suppression des formulations absolues « personne n'en émet »
  dans la page et « aucune source ne l'émet » dans la note liée.

La figure individuelle, la page assemblée et la note ont été régénérées uniquement
dans l'aperçu isolé. **72 tests ciblés réussissent**, couvrant le calcul sur huit heures,
les effectifs, la provenance, les gabarits et la navigation ; Ruff passe sur les fichiers
modifiés. Le premier passage avait révélé une incompatibilité du gabarit de note avec
le substitut de données utilisé par les tests de navigation ; le nom de station est
désormais préparé avec les autres libellés, et la nouvelle exécution passe entièrement.
La suite complète de 382 tests mentionnée plus haut précède ce lot complémentaire.

Résultats sur le **cache air collecté le 12 septembre 2026**, conservant les observations
des étés 2020–2025. La capture du site indiquait une collecte au 22 septembre : cet aperçu
ne prétend pas utiliser cette version plus récente, qui n'a pas été téléchargée.

| Station | Jours en dépassement / jours valides | Part | Étés disponibles |
|---|---:|---:|---|
| Bastia Montesoro | 82 / 544 | 15,07 % | 2020–2025 |
| Venaco | 54 / 520 | 10,38 % | 2020–2025 |
| Bastia Giraud | 25 / 538 | 4,65 % | 2020–2025 |
| Ajaccio Confina 2 | 4 / 180 | 2,22 % | 2024–2025 |
| Ajaccio Canetto | 8 / 532 | 1,50 % | 2020–2025 |

Aperçus de ce lot : audit/prescripteurs-20260922/outputs/air_ozone.html,
a4_campagne_contre_ville.html et a0_note_methodologique.html dans le même dossier.
Aucun commit, push ou déploiement n'a été effectué pour ce lot.

## Préparation de la publication demandée ensuite

Après l'accord « les deux » pour le contrôle visuel et la mise en ligne, le correctif
ozone a été isolé dans audit/publication-ozone-20260922/correctif-ozone.patch. Il porte
sur quatre fichiers : figures_air.py, note_air.py, les seuls passages ozone de page_air.py
et test_effectifs_ozone.py. Les modifications antérieures de stabilisation, de bundle
JavaScript, d'accueil et de dossier de preuve ne sont pas incorporées dans ce patch.

La copie de vérification part du commit local 413268030be6 ; ce commit n'a pas été
comparé à la branche distante actuelle. Les pages air y ont été régénérées avec le cache
local déjà autorisé. **48 tests ciblés passent sur ce lot isolé**, en complément des
72 contrôles du projet complet relatés plus haut. L'application du patch a aussi été
vérifiée avec un index temporaire distinct de celui du travail en cours.

La nouvelle tentative de connexion au navigateur intégré a encore renvoyé
« Browser is not available: iab » ; aucun navigateur n'était proposé par l'outil.
Le contrôle visuel n'est donc toujours pas effectué.

Le workflow local existant collecte, archive, régénère l'ensemble du site puis le
synchronise vers Scaleway avec suppression des fichiers devenus absents d'outputs/.
Un accord spécifique pour l'authentification GitHub et les secrets utilisés par ce
workflow a été demandé conformément aux consignes AGENTS.md transmises par l'utilisateur.
À ce stade, aucune connexion authentifiée, lecture de valeur secrète, création de
commit, opération distante ou publication n'a été effectuée pendant cette préparation.

## Limites et clôture restante

- **Recette visuelle ordinateur et téléphone : autorisée, mais bloquée par
  l'indisponibilité du navigateur intégré.** Après le « go » de l'utilisateur,
  l'initialisation a renvoyé « Browser is not available: iab » et la liste des
  navigateurs disponibles était vide. Aucun serveur d'aperçu n'a été lancé ni aucun
  autre navigateur utilisé. Le rendu, la navigation et le téléchargement du ZIP
  dans un navigateur restent à vérifier ; aucun résultat visuel n'est revendiqué.
- Intégration Git, validation CI distante et contrôle après déploiement restent à
  effectuer. Cette session n'a ni créé de commit ni poussé de branche.
- A4 (bascule de plusieurs fichiers), A5 (recherche autonome des bruts) et D4
  (conservation du journal d'archive lors d'un échec aval) ne sont pas fermés par ce lot.
  La reconstruction isolée limite la réutilisation d'anciens fichiers ; elle ne
  remplace pas leur correction générale.
- La revue par les prescripteurs doit encore apprécier l'utilité et la méthode.
  Les tests établissent des propriétés techniques, pas une validation externe.

Aperçus locaux :
audit/prescripteurs-20260922/outputs/index.html et
audit/prescripteurs-20260922/outputs/verification-demande.html.
