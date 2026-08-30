# Audit technique du dépôt demonstrateur-data-corsica

**Date de l’audit :** 5 août 2026
**Branche auditée :** master
**Commit audité :** f1e78ca
**Périmètre :** code Python, transformations de données, tests, workflows GitHub Actions, configuration, documentation et sorties HTML versionnées
**Nature de l’audit :** lecture statique, contrôles locaux et revue ciblée des résultats ; aucune correction du produit n’a été appliquée

## Synthèse technique

Le dépôt possède une base d’ingénierie sérieuse : provenance par empreinte SHA-256, validation des téléchargements avant certification, contrôles métier nombreux, gestion explicite des fuseaux horaires, sorties statiques sans CDN et séparation correcte des droits entre validation et publication.

Il n’est toutefois pas encore totalement aligné avec sa promesse éditoriale de démonstration reproductible. Les risques les plus importants ne sont pas des défauts classiques d’exécution ; ils concernent la portée des affirmations publiques, la définition des cohortes statistiques, la traçabilité exacte des figures composites et la capacité de la CI de pull request à rejouer les contrôles dépendants des données.

**Verdict : publication techniquement exploitable, mais validation éditoriale et méthodologique requise avant de présenter l’ensemble comme une preuve entièrement auditée.**

Répartition des constats :

| Niveau | Nombre | Lecture |
|---|---:|---|
| Critique | 0 | Aucun risque immédiat de compromission ou de perte massive identifié |
| Élevé | 7 | Peut invalider une affirmation publique, la provenance ou un garde-fou majeur |
| Moyen | 6 | Robustesse, accessibilité, performance ou maintenabilité significativement perfectibles |
| Faible | 2 | Dette de conception ou d’outillage à traiter sans urgence |

Les cinq priorités immédiates sont :

1. Réécrire ou sourcer les affirmations sur les alertes, communiqués et qualité globale de l’air.
2. Aligner les cohortes, dénominateurs et appariements statistiques des figures air.
3. Rendre la lignée de données exacte pour chaque sortie et empêcher la consommation de Parquet périmés.
4. Donner aux pull requests un jeu de données minimal permettant d’exécuter les tests de résultats.
5. Verrouiller l’environnement du pipeline planifié et éviter toute publication partielle suivie d’un statut d’échec.

## Contrôles exécutés

| Contrôle | Résultat | Interprétation |
|---|---|---|
| État Git avant création de ce rapport | Propre | Aucun changement de code ou de donnée introduit pendant l’audit |
| Tests Pytest | 107 réussis, 1 échec | Le seul échec observé porte sur une incohérence de date entre une sortie versionnée et la lignée locale ignorée |
| Ruff, règles configurées | Réussi | Aucun défaut signalé par le lint actuellement activé |
| Ruff, formatage | 15 fichiers à reformater | Le dépôt n’applique pas encore un formatage homogène |
| Ruff, revue ciblée élargie | Alertes de complexité et de robustesse | Trois fonctions dépassent une complexité cyclomatique de 10 ; analyse XML et quelques usages de zip à durcir |
| Recherche de secrets versionnés | Aucun secret évident trouvé | Contrôle textuel uniquement, pas un audit forensique |
| Audit visuel dans un navigateur | Non exécuté | Le navigateur intégré n’était pas disponible dans l’environnement |
| Scan CVE/SCA des dépendances | Non exécuté | Les versions ont été inventoriées, mais aucune base de vulnérabilités externe n’a été interrogée |

L’échec Pytest concerne le test de fraîcheur de la page d’accueil : [outputs/index.html](outputs/index.html) annonce une génération le 5 août 2026 à 03:42 UTC, tandis que le fichier local ignoré data/processed/_build.json indique le 4 août 2026 à 08:05 UTC. Cela ne prouve pas que la sortie publiée est fausse ; cela prouve que la sortie versionnée et l’état de build local peuvent se désynchroniser et rendre le contrôle non déterministe selon la machine.

## Périmètre et méthode

L’audit a couvert :

- environ 4 645 lignes de Python applicatif et 2 527 lignes de tests ;
- 37 sources déclarées ;
- environ 192,11 Mio de données brutes locales ;
- environ 14,27 Mio de données préparées, réparties dans 10 Parquet ;
- 20 sorties HTML et une copie mutualisée de Plotly d’environ 4,63 Mio ;
- les workflows de validation et de rafraîchissement planifié ;
- les affirmations publiques générées depuis le code et la documentation.

La revue a combiné :

- lecture de l’architecture et des chemins critiques collecte → préparation → figures → pages ;
- examen des requêtes DuckDB et de leurs dénominateurs ;
- comparaison des titres et sous-titres avec les calculs réellement exécutés ;
- vérification des mécanismes de lignée, d’empreinte et de fraîcheur ;
- exécution locale des tests et du lint ;
- inspection des politiques de publication et des permissions GitHub Actions.

Les données locales ont servi à vérifier certains effectifs et périmètres. Aucun téléchargement externe ni rafraîchissement de source n’a été lancé pendant l’audit.

## Architecture observée

| Couche | Composants principaux | Rôle |
|---|---|---|
| Déclaration | [sources.yaml](sources.yaml) | URLs, formats, fichiers, secrets éventuels et métadonnées de collecte |
| Collecte | [fetch.py](src/demonstrateur/fetch.py) | Téléchargement, validation, cache et manifeste SHA-256 |
| Préparation | [prepare.py](src/demonstrateur/prepare.py) | Normalisation et production des Parquet |
| Visualisation | [figures.py](src/demonstrateur/figures.py), [figures_air.py](src/demonstrateur/figures_air.py) | Calculs analytiques et figures Plotly |
| Assemblage | [compile_etude.py](src/demonstrateur/compile_etude.py), [page_air.py](src/demonstrateur/page_air.py), [accueil.py](src/demonstrateur/accueil.py) | Pages éditoriales et page d’entrée |
| Provenance | data/raw/_manifest.json et data/processed/_build.json | Empreintes des entrées et lignée des sorties préparées |
| Validation | [tests](tests), [.github/workflows/validation.yml](.github/workflows/validation.yml) | Tests unitaires, tests de résultats et hygiène de code |
| Publication | [.github/workflows/pipeline.yml](.github/workflows/pipeline.yml) | Rafraîchissement, génération et commit planifiés |

La chaîne est lisible et les responsabilités sont globalement bien séparées. Les principaux défauts apparaissent aux frontières : donnée préparée → figure, calcul → formulation éditoriale et validation PR → validation avec données.

## Points solides

### Provenance et intégrité

- Le manifeste conserve l’identité, l’empreinte et la date de collecte des sources.
- Les contenus sont validés avant d’être certifiés dans le manifeste.
- La préparation produit une lignée de build par Parquet et recalcule les empreintes.
- Les identifiants Plotly sont déterministes, ce qui évite des diffs aléatoires entre deux générations identiques ; voir [viz.py, lignes 157 à 162](src/demonstrateur/viz.py#L157).

### Qualité des transformations

- Les conventions temporelles des sources sont documentées avec un niveau de précision inhabituel.
- La grille horaire de l’ozone et le calcul MDA8 font l’objet de gardes dédiées.
- Un exemple réglementaire LCSQA est rejoué dans les tests.
- De nombreuses affirmations de figures sont protégées par des tests métier ou des erreurs explicites lorsque le titre deviendrait faux.

### Sécurité et déploiement

- Aucun Plotly n’est chargé depuis un CDN ; les pages restent autonomes par rapport à un tiers.
- Les secrets déclarés ne sont pas destinés à être écrits dans le manifeste ou les messages.
- Le workflow de validation n’a pas de droit d’écriture, alors que le pipeline de publication porte explicitement ce droit.
- Le pipeline sérialise les rafraîchissements afin de réduire les conflits de commit.

### Documentation

- Les commentaires expliquent les décisions statistiques et les pièges de fuseau.
- Les notes méthodologiques rendent visibles de nombreuses limites de périmètre.
- Le dépôt cherche activement à distinguer données mesurées, estimations et chiffres recopiés.

## Registre priorisé des constats

| ID | Niveau | Domaine | Résumé |
|---|---|---|---|
| AUD-01 | Élevé | Éditorial / preuve | Des affirmations sur les alertes, communiqués et la qualité de l’air dépassent les données calculées |
| AUD-02 | Élevé | Statistiques | Les cohortes et unités de comptage des figures air ne sont pas toujours comparables ou appariées |
| AUD-03 | Élevé | Lignée | Un Parquet ancien mais encore présent peut être consommé hors de la lignée courante |
| AUD-04 | Élevé | Provenance | Les figures composites affichent la date d’une seule source |
| AUD-05 | Élevé | Gouvernance des données | Des métadonnées et valeurs manuelles échappent au catalogue de sources |
| AUD-06 | Élevé | CI | Une pull request propre ne rejoue pas une part importante des tests dépendants des données |
| AUD-07 | Élevé | Cohérence publique | Plusieurs textes, sous-titres et calculs se contredisent |
| AUD-08 | Moyen | Qualité météo | Le contrôle de complétude horaire n’est pas effectué par poste |
| AUD-09 | Moyen | Collecte / sécurité | Redirections, reprises, taille de réponse et écriture du manifeste sont à durcir |
| AUD-10 | Moyen | Périmètre | Une partie des données collectées ou préparées n’est pas utilisée, et l’air est figé à 2025 |
| AUD-11 | Moyen | Accessibilité | Les figures HTML autonomes ont peu de sémantique et peu de solution de repli |
| AUD-12 | Moyen | Performance | La page électricité multiplie les contextes Plotly via les iframes |
| AUD-13 | Moyen | Reproductibilité CI/CD | Le cron n’utilise pas le verrou de dépendances et peut publier avant de signaler un échec |
| AUD-14 | Faible | Portabilité | La racine du dépôt est déduite du chemin du package et des dossiers sont créés à l’import |
| AUD-15 | Faible | Maintenabilité | Fichiers volumineux, connexions non fermées et outillage qualité incomplet |

## Constats détaillés

### AUD-01 — Les affirmations sur les alertes et la qualité globale de l’air dépassent les mesures

**Niveau : élevé**

La figure A1 calcule deux choses : le nombre de dépassements de l’objectif de qualité MDA8 et le nombre de jours où un maximum horaire atteint le seuil réglementaire d’information. Le calcul est explicite dans [figures_air.py, lignes 113 à 139](src/demonstrateur/figures_air.py#L113).

Le texte public va plus loin en affirmant qu’aucune journée n’a fait l’objet d’une alerte, d’un communiqué ou d’un article ; voir [page_air.py, lignes 153 à 157](src/demonstrateur/page_air.py#L153). L’absence de franchissement d’un seuil dans la série de mesures ne démontre pas l’absence de communication publique. Une alerte peut aussi résulter d’une autre procédure, d’une prévision, d’une autre station, d’un autre polluant ou d’une décision préfectorale.

La figure A5 qualifie par ailleurs le minimum d’ozone de moment « le plus respirable » dans [figures_air.py, ligne 438](src/demonstrateur/figures_air.py#L438), alors que le dépôt reconnaît lui-même que le NO2 peut culminer à cette heure. Une seule composante de la qualité de l’air ne suffit pas à qualifier l’air dans son ensemble.

**Impact :** le lecteur peut interpréter une absence de seuil mesuré comme une absence d’événement public ou comme une recommandation sanitaire globale.

**Recommandations :**

- remplacer « aucune alerte, aucun communiqué, aucun article » par une formulation limitée au calcul, par exemple « aucun maximum horaire de la série n’atteint le seuil d’information » ;
- si la communication publique doit rester dans le récit, ajouter une source et une méthode de recherche des arrêtés, communiqués et archives ;
- remplacer « le plus respirable » par « le moins chargé en ozone » ;
- ajouter un registre des affirmations reliant chaque phrase publique à sa métrique, son périmètre et son test.

**Critère d’acceptation :** aucune phrase publique ne doit affirmer davantage que ce que sa donnée ou sa source documentaire permet d’établir.

### AUD-02 — Les cohortes et unités statistiques des figures air ne sont pas suffisamment alignées

**Niveau : élevé**

Trois écarts ont été observés.

1. **Couverture très inégale entre stations.** Sur la fenêtre d’été 2020-2025, Confina ne dispose que de 180 journées valides, contre environ 520 à 544 pour les autres stations. Les taux réduisent une partie du biais, mais la comparabilité temporelle reste fragile si les années couvertes diffèrent.
2. **Unité A2 mal nommée.** La requête compte les lignes du croisement station × date, puis affiche cet effectif comme des « jours » ; voir [figures_air.py, lignes 193 à 201](src/demonstrateur/figures_air.py#L193). Il s’agit de journées-stations, pas de jours calendaires uniques.
3. **A3 n’impose pas l’appariement O3/NO2 au même instant.** La requête moyenne chaque polluant indépendamment par heure après avoir seulement exclu Venaco ; voir [figures_air.py, lignes 279 à 290](src/demonstrateur/figures_air.py#L279). Les lignes réellement disponibles sont différentes — 42 533 mesures NO2 contre 43 314 mesures O3 dans les données locales — et le filtre aboutit à quatre stations de fond effectivement communes, alors que le sous-titre en annonce cinq dans [figures_air.py, lignes 92 à 97](src/demonstrateur/figures_air.py#L92).

Le résultat descriptif actuel — pic moyen du NO2 vers 7 h et de l’O3 vers 15 h — reste plausible et stable dans le jeu local. Le problème est la définition de l’échantillon, pas nécessairement la direction du résultat.

**Impact :** dénominateurs ambigus, pondération implicite des stations les mieux couvertes et comparaison de polluants sur des échantillons différents.

**Recommandations :**

- publier un tableau de couverture par station et année ;
- nommer les effectifs A2 « journées-stations », ou agréger d’abord au jour calendaire selon une règle documentée ;
- construire A3 sur l’intersection exacte station × horodatage où O3 et NO2 sont tous deux valides ;
- choisir explicitement une pondération par mesure, par station ou par station-année ;
- générer le nombre de stations depuis la requête au lieu de l’écrire en constante.

**Critère d’acceptation :** chaque figure précise unité, cohorte, dénominateur, couverture et règle de pondération ; les sous-titres sont dérivés du même jeu que les courbes.

### AUD-03 — Des sorties préparées périmées peuvent échapper à la lignée courante

**Niveau : élevé**

La fonction de vérification contrôle les sorties énumérées par data/processed/_build.json ; voir [prepare.py, lignes 1123 à 1143](src/demonstrateur/prepare.py#L1123). Elle ne rejette pas les Parquet supplémentaires présents dans data/processed.

Or les producteurs de figures et de notes décident parfois d’utiliser une donnée optionnelle en testant seulement son existence. C’est le cas de la Sardaigne dans [figures.py, lignes 775 à 790](src/demonstrateur/figures.py#L775) et [note_elec.py, lignes 82 à 84](src/demonstrateur/note_elec.py#L82). Si le plan courant ne peut plus construire ce Parquet mais qu’une ancienne copie demeure, cette copie peut être relue sans appartenir à la lignée validée du build courant.

La préparation utilise bien un répertoire de staging, mais remplace ensuite les fichiers un par un. Une interruption entre deux remplacements peut donc laisser un ensemble mixte de générations avant que la lignée finale soit cohérente.

**Impact :** une figure peut être fraîche en apparence tout en mélangeant une sortie courante et une sortie ancienne.

**Recommandations :**

- faire de _build.json une liste exhaustive : rejeter ou mettre en quarantaine toute sortie consommable qui n’y figure pas ;
- remplacer les tests Path.exists par une résolution via une API de lignée, par exemple require_output(nom) ;
- enregistrer pour chaque sortie HTML la liste exacte des Parquet et sources effectivement lus ;
- publier data/processed comme une génération immuable, puis basculer un pointeur de génération atomiquement ;
- ajouter un test avec un Parquet optionnel ancien présent mais absent du build courant.

**Critère d’acceptation :** aucun consommateur ne peut ouvrir un artefact préparé sans vérifier simultanément son appartenance et son empreinte dans la génération courante.

### AUD-04 — La date affichée par une figure composite ne représente pas toutes ses sources

**Niveau : élevé**

Les cinq figures air historiques s’appuient sur un Parquet construit à partir de 22 sources AEE, mais utilisent toutes la date de collecte d’une seule source, aee_o3_venaco_continu ; voir [figures_air.py, lignes 460 à 475](src/demonstrateur/figures_air.py#L460). A2 ajoute la météo, mais son pied utilise uniquement la date météo.

La figure Corse–Sardaigne combine EDF et ENTSO-E, alors que son pied prend uniquement la date entsoe_sardaigne_2024 dans [figures.py, lignes 775 à 786](src/demonstrateur/figures.py#L775). La figure de dépendance combine des données EDF et des valeurs OREGES recopiées, mais affiche la date EDF dans [figures.py, lignes 737 à 748](src/demonstrateur/figures.py#L737).

**Impact :** la date visible peut masquer une source plus ancienne, partielle ou absente.

**Recommandations :**

- calculer une provenance par figure à partir des Parquet réellement lus ;
- afficher une plage de collecte ou la date la plus ancienne lorsque plusieurs sources contribuent ;
- distinguer « données mesurées jusqu’au », « source documentaire publiée en » et « page générée le » ;
- exposer une fiche de provenance détaillée derrière chaque figure.

**Critère d’acceptation :** la fraîcheur visible est une fonction de toutes les dépendances de la figure, jamais d’un identifiant choisi manuellement.

### AUD-05 — Des données manuelles importantes échappent au catalogue de sources

**Niveau : élevé**

Le dépôt contient des valeurs ou métadonnées recopiées directement dans le code :

- coordonnées, altitudes et dates de stations dans [prepare.py, à partir de la ligne 458](src/demonstrateur/prepare.py#L458) ;
- valeurs OREGES 2020 dans [figures.py, lignes 400 à 418](src/demonstrateur/figures.py#L400) ;
- seuils réglementaires dans [figures_air.py, lignes 42 à 49](src/demonstrateur/figures_air.py#L42) et dans la partie électricité ;
- interprétations juridiques ou chronologiques utilisées par T8.

Cette pratique n’est pas nécessairement mauvaise : une valeur documentaire peut légitimement être recopiée. Elle contredit toutefois les formulations absolues « tout est lu, jamais recopié » et « aucun fichier téléchargé ni saisi à la main » présentes notamment dans [note_air.py, lignes 1 à 10](src/demonstrateur/note_air.py#L1), [note_air.py, ligne 152](src/demonstrateur/note_air.py#L152) et [note_elec.py, ligne 232](src/demonstrateur/note_elec.py#L232).

**Impact :** la promesse de reproductibilité est plus forte que le mécanisme réel ; les valeurs manuelles n’ont ni empreinte documentaire ni processus uniforme de révision.

**Recommandations :**

- déclarer les sources documentaires et tables de référence dans un registre versionné ;
- déplacer les constantes de données vers des fichiers structurés avec source, page, date de vérification et responsable ;
- distinguer explicitement données téléchargées, valeurs documentaires recopiées et hypothèses éditoriales ;
- tester la fraîcheur ou au minimum la date de révision des références réglementaires.

**Critère d’acceptation :** toute valeur non calculée possède une provenance auditable et la communication décrit honnêtement son mode d’acquisition.

### AUD-06 — La CI de pull request saute une grande partie des tests de résultats

**Niveau : élevé**

data/processed est ignoré par Git dans [.gitignore](.gitignore). Les tests de [test_resultats.py](tests/test_resultats.py) utilisent de nombreux marqueurs skipif lorsque les Parquet sont absents. Sur un checkout propre comparable à une pull request, 53 tests dépendants des données peuvent être sautés sur 108 tests collectés.

Le workflow [validation.yml, lignes 46 à 53](.github/workflows/validation.yml#L46) exécute bien Ruff et Pytest, mais ne restaure ni ne construit les données nécessaires à ces contrôles. Les gardes les plus importantes ne protègent donc réellement que le cron, qui dispose du cache de données.

Par ailleurs, certains tests recopient leurs propres requêtes au lieu d’appeler la logique de production. Le test du pic O3/NO2 omet par exemple le filtre influence = Fond et la fenêtre 2020-2025 utilisés par la figure ; comparer [test_resultats.py, lignes 747 à 770](tests/test_resultats.py#L747) avec [figures_air.py, lignes 279 à 283](src/demonstrateur/figures_air.py#L279). Un test peut donc rester vert pendant que la requête publiée évolue.

**Impact :** une pull request peut casser un résultat analytique sans que le contrôle obligatoire le voie.

**Recommandations :**

- versionner un petit jeu de fixtures synthétiques couvrant tous les invariants ;
- séparer tests unitaires de transformation, tests de contrat de source et tests d’intégration sur données réelles ;
- faire échouer la CI si un nombre inattendu de tests est sauté ;
- centraliser les requêtes ou fonctions analytiques afin que figures et tests utilisent la même implémentation ;
- conserver dans le cron une validation sur les données complètes.

**Critère d’acceptation :** la CI de PR exécute les gardes de logique sans accès aux données privées ou volumineuses, et aucun skip dépendant des données ne passe silencieusement.

### AUD-07 — Plusieurs contradictions sont visibles dans les contenus publics

**Niveau : élevé**

Trois contradictions concrètes ont été relevées :

- [docs/etude.md, ligne 159](docs/etude.md#L159) indique que le seuil a été relevé jusqu’à 45 % en Corse, alors que T8 le qualifie de seuil visé « jamais entré en vigueur » dans [figures.py, lignes 568 à 574](src/demonstrateur/figures.py#L568) ;
- le sous-titre A3 annonce cinq stations dans [figures_air.py, ligne 93](src/demonstrateur/figures_air.py#L93), tandis que les données filtrées de fond en fournissent quatre effectivement communes ;
- A2 annonce « le poste météo le plus proche de chaque station » dans [figures_air.py, ligne 84](src/demonstrateur/figures_air.py#L84), alors que le commentaire de conception précise que Venaco est volontairement appariée à Vivario, plus éloignée qu’un autre poste jugé moins représentatif ; voir [figures_air.py, lignes 14 à 17](src/demonstrateur/figures_air.py#L14).

**Impact :** le lecteur ne peut pas déterminer quelle version est normative ; une contradiction éditoriale affaiblit les calculs pourtant bien contrôlés.

**Recommandations :**

- créer une source unique pour les seuils, statuts juridiques et nombres de stations ;
- générer les sous-titres depuis les résultats ou métadonnées ;
- remplacer « le plus proche » par « le poste de référence apparié » et expliquer le choix ;
- ajouter des tests de cohérence entre documentation, constantes et textes produits.

**Critère d’acceptation :** une même notion ne peut être publiée avec deux valeurs ou statuts différents dans le même build.

### AUD-08 — Le contrôle de complétude météo est global au jour, pas par poste

**Niveau : moyen**

La sortie météo contient plusieurs postes. Pourtant, la garde compte les heures distinctes uniquement par date, sans num_poste ; voir [prepare.py, lignes 980 à 990](src/demonstrateur/prepare.py#L980). Une journée peut donc sembler complète dès lors que l’union de tous les postes couvre au moins 23 heures, même si un poste utilisé par A2 a une série incomplète.

Le croisement conserve n_heures_temp par poste et par jour dans [prepare.py, lignes 793 à 810](src/demonstrateur/prepare.py#L793), mais aucune garde bloquante n’exploite cette colonne avant la figure.

Dans les données locales examinées, les journées actuellement sélectionnées par le croisement sont complètes. Le constat porte sur la capacité du garde-fou à détecter une future dégradation.

**Recommandations :**

- grouper la garde par num_poste et date_locale ;
- calculer l’effectif attendu selon le changement d’heure local ;
- rejeter ou marquer invalide chaque journée-poste incomplète ;
- tester explicitement le cas où deux postes incomplets se complètent artificiellement.

### AUD-09 — La collecte doit être durcie sur les redirections et les pannes réseau

**Niveau : moyen**

La collecte manuelle des redirections compare uniquement netloc avant de renvoyer un en-tête secret ; voir [fetch.py, lignes 209 à 237](src/demonstrateur/fetch.py#L209). Une redirection du même hôte de HTTPS vers HTTP conserverait donc le secret. Le schéma doit faire partie de l’origine de confiance, et toute baisse de sécurité doit être interdite.

La collecte utilise un timeout de 180 secondes, mais pas de stratégie explicite de retry avec backoff, pas de plafond de taille téléchargée et pas de streaming borné. Les 37 sources sont traitées séquentiellement. Le manifeste est écrit directement par write_text dans [fetch.py, lignes 88 à 94](src/demonstrateur/fetch.py#L88), sans fichier temporaire suivi d’un remplacement atomique.

L’analyse XML réseau utilise xml.etree.ElementTree dans [fetch.py, ligne 57](src/demonstrateur/fetch.py#L57), ce que les règles de sécurité élargies signalent pour des contenus non fiables. Enfin, date.today est utilisée pour dater des collectes dans [fetch.py, lignes 177 et 320](src/demonstrateur/fetch.py#L177), ce qui rend le résultat dépendant du fuseau de la machine.

**Recommandations :**

- comparer schéma, hôte et port ; interdire HTTPS → HTTP ;
- retirer tout secret après la première origine non strictement identique ;
- ajouter retry borné, backoff avec jitter, streaming et taille maximale par source ;
- écrire le manifeste dans un fichier temporaire, fsync si nécessaire, puis remplacer atomiquement ;
- utiliser un parseur XML durci ou imposer une validation stricte de taille et de structure ;
- utiliser une date UTC explicite ;
- paralléliser seulement avec une limite faible et un contrôle par domaine.

### AUD-10 — Le périmètre déclaré et les données réellement utilisées divergent

**Niveau : moyen**

Toutes les figures air appliquent une fenêtre fixe 2020-2025 via [figures_air.py, ligne 50](src/demonstrateur/figures_air.py#L50), alors que la série préparée locale atteint le 4 août 2026. Ce choix peut être légitime pour conserver six étés complets, mais il doit être présenté comme un gel analytique intentionnel et non comme la totalité de la donnée disponible.

Le pipeline produit air_corse.parquet depuis la source LCSQA temps réel, mais les figures historiques lisent les Parquet AEE. Les sources DVF et communes sont également collectées ou préparées sans alimenter les sorties auditées. Cette surface inutilisée augmente le coût de collecte, de cache et de maintenance.

**Recommandations :**

- documenter explicitement pourquoi 2026 est exclu et prévoir le basculement après clôture de l’été ;
- ajouter un test empêchant une fenêtre historique de rester figée par oubli ;
- supprimer, isoler ou affecter clairement les sources inutilisées à une sortie planifiée ;
- publier une matrice source → Parquet → figure pour révéler immédiatement les branches mortes.

### AUD-11 — Les figures HTML autonomes ont une accessibilité limitée

**Niveau : moyen**

La fonction générique appelle directement fig.write_html avec full_html = true dans [viz.py, lignes 138 à 162](src/demonstrateur/viz.py#L138). Les 15 figures individuelles examinées ne disposent pas systématiquement d’un titre de document utile, d’une langue explicite, d’un résumé sémantique, d’un tableau de données ou d’un repli noscript.

La page assemblée électricité produit des titres d’iframe à partir des noms de fichiers, par exemple « Visualisation : t4_heure_verte » dans [compile_etude.py, lignes 61 à 66](src/demonstrateur/compile_etude.py#L61). Ce libellé est technique et peu utile pour un lecteur d’écran.

La page air assemblée est mieux conçue : elle possède lang = fr, un titre et une seule inclusion de Plotly. Néanmoins, l’absence de test navigateur a empêché de confirmer navigation clavier, focus visible, contraste réel, zoom et comportement mobile.

**Recommandations :**

- envelopper les figures autonomes dans un gabarit HTML contrôlé ;
- ajouter lang, title, résumé textuel, tableau de valeurs essentiel et noscript ;
- générer des titres d’iframe à partir du titre éditorial de la figure ;
- tester clavier, lecteur d’écran, zoom 200 %, contraste et deux largeurs mobiles ;
- rendre les données clés accessibles sans interaction au survol.

### AUD-12 — Les iframes de la page électricité multiplient le coût d’exécution de Plotly

**Niveau : moyen**

La page d’étude assemble les visuels dans des iframes ; voir [compile_etude.py, lignes 10 à 15](src/demonstrateur/compile_etude.py#L10). La copie de plotly.min.js est mutualisée sur disque et peut être servie depuis le cache HTTP, mais chaque iframe crée un contexte JavaScript distinct qui doit analyser et initialiser Plotly.

La page air montre déjà une meilleure architecture : plusieurs blocs Plotly dans un document unique et une seule balise script ; voir [page_air.py, lignes 149 à 163](src/demonstrateur/page_air.py#L149).

**Impact :** temps d’initialisation, mémoire et coût mobile supérieurs, avec une navigation clavier fragmentée.

**Recommandations :**

- appliquer à l’étude électricité le modèle d’assemblage de la page air ;
- charger Plotly une seule fois par page ;
- conserver les HTML individuels uniquement comme artefacts secondaires ;
- mesurer poids transféré, temps d’interactivité et mémoire sur mobile avant/après.

### AUD-13 — Le pipeline planifié n’est pas strictement reproductible et peut publier partiellement

**Niveau : moyen**

Un fichier uv.lock cohérent est présent, mais le cron installe le projet avec python -m pip install -e . pytest dans [pipeline.yml, lignes 37 à 44](.github/workflows/pipeline.yml#L37). Les dépendances directes n’ont que des bornes basses dans [pyproject.toml, lignes 10 à 26](pyproject.toml#L10). Un nouveau paquet compatible en apparence peut donc modifier les calculs ou le HTML sans changement du dépôt.

Les étapes de collecte et de figures électricité utilisent continue-on-error dans [pipeline.yml, lignes 76 à 96](.github/workflows/pipeline.yml#L76). Le workflow exécute ensuite les tests, committe et pousse les sorties, puis signale l’échec seulement après le push dans [pipeline.yml, lignes 125 à 147](.github/workflows/pipeline.yml#L125).

Cette politique est compréhensible pour publier un visuel de fraîcheur dégradée, mais elle mélange deux états : « publication volontairement dégradée » et « pipeline en échec ». Elle peut aussi publier un sous-ensemble de sources actualisées sans registre explicite de complétude.

**Recommandations :**

- installer avec uv.lock et uv run --frozen ou l’équivalent ;
- définir une politique formelle de publication partielle par source et par sortie ;
- enregistrer dans la page et la lignée quelles sources ont échoué pendant le build ;
- distinguer un statut dégradé attendu d’une erreur technique ;
- décider avant le commit si le build est publiable, puis pousser seulement cet état.

### AUD-14 — La résolution des chemins limite la portabilité du package

**Niveau : faible**

[config.py, ligne 5](src/demonstrateur/config.py#L5) déduit la racine du projet depuis l’emplacement du module installé. Cette hypothèse fonctionne dans un checkout éditable, mais devient fragile dans une roue installée ailleurs. Le module crée en outre data/raw, data/processed et outputs dès son import dans [config.py, lignes 24 à 25](src/demonstrateur/config.py#L24).

**Recommandations :**

- accepter une racine via argument CLI ou variable dédiée ;
- éviter les écritures à l’import ;
- créer les dossiers seulement dans les commandes qui en ont besoin ;
- tester une installation wheel dans un répertoire temporaire.

### AUD-15 — La maintenabilité gagnerait à être renforcée avant extension du périmètre

**Niveau : faible**

Les fichiers prepare.py, figures.py, figures_air.py et fetch.py concentrent beaucoup de responsabilités. Les contrôles élargis de Ruff signalent une complexité supérieure à 10 pour compile_etude.compiler, fetch._valider et fetch.main.

Plusieurs connexions DuckDB sont créées sans gestionnaire de contexte explicite, notamment dans [prepare.py](src/demonstrateur/prepare.py), [figures.py](src/demonstrateur/figures.py), [figures_air.py](src/demonstrateur/figures_air.py) et les notes. CPython les libère généralement, mais une fermeture déterministe est préférable pour les exécutions longues et les tests Windows.

Le workflow ne vérifie pas le formatage, le typage, la couverture ni les vulnérabilités. Le contrôle ruff format --check indique actuellement 15 fichiers à reformater.

**Recommandations :**

- extraire les requêtes analytiques dans des fonctions testables sans rendu ;
- séparer collecte HTTP, validation de format et gestion du manifeste ;
- fermer explicitement les connexions DuckDB ;
- ajouter ruff format --check à la CI ;
- introduire progressivement un contrôle de types et un seuil de couverture ciblé ;
- ajouter un scan SCA régulier et une politique de mise à jour des dépendances.

## Plan d’action recommandé

### P0 — Avant de renforcer la communication publique

| Action | Constats couverts | Livrable attendu |
|---|---|---|
| Corriger les formulations non démontrées et les contradictions | AUD-01, AUD-07 | Textes publics limités aux preuves disponibles, tests de cohérence |
| Refaire les cohortes air | AUD-02, AUD-08 | Fonctions analytiques communes, couverture publiée, appariement exact |
| Rendre la lignée exhaustive et spécifique à chaque sortie | AUD-03, AUD-04 | Résolution obligatoire via le build et provenance multi-source |
| Donner des fixtures à la CI de PR | AUD-06 | Gardes métier exécutées sans données complètes |
| Verrouiller et clarifier la publication partielle | AUD-13 | Installation figée et décision de publication avant push |

### P1 — Robustesse et qualité de service

1. Déplacer les valeurs documentaires vers un registre de provenance.
2. Corriger la complétude météo par poste.
3. Durcir les redirections, retries, tailles et écritures atomiques.
4. Ajouter un gabarit accessible pour les figures autonomes.
5. Consolider la page électricité dans un seul contexte Plotly.

### P2 — Réduction de dette

1. Décider du sort des sources et Parquet inutilisés.
2. Paramétrer la racine de travail et supprimer les écritures à l’import.
3. Refactorer les grands modules et fermer les connexions.
4. Ajouter formatage, typage progressif, couverture et scan de dépendances.
5. Tenir à jour les compteurs, cartes de lignée et documents d’architecture.

## Proposition de séquencement

### Lot 1 — Vérité éditoriale et définitions

Durée indicative : courte. Réviser les textes, statuts réglementaires, unités et sous-titres. Ajouter les tests de cohérence correspondants. Ce lot réduit immédiatement le risque de publication trompeuse sans changer les sources.

### Lot 2 — Noyau analytique partagé

Durée indicative : moyenne. Extraire les requêtes de production dans des fonctions réutilisées par les figures et les tests. Corriger appariements, pondérations et complétude. Ajouter les fixtures minimales.

### Lot 3 — Provenance et publication

Durée indicative : moyenne. Introduire une génération immuable, une lignée par sortie et une politique de publication partielle. Verrouiller l’environnement du cron.

### Lot 4 — Expérience et maintenance

Durée indicative : moyenne. Accessibilité, consolidation Plotly, découpage des modules et nouveaux contrôles qualité.

## Questions à trancher

1. Le produit veut-il raconter strictement ce que prouvent les séries, ou également documenter les communications publiques et décisions réglementaires ? Le second choix exige des sources documentaires supplémentaires.
2. Pour les comparaisons entre stations, la cible statistique est-elle une moyenne des mesures, une moyenne des stations ou une moyenne des stations-années ? Ces estimands ne répondent pas exactement à la même question.
3. Une publication partielle après échec de collecte est-elle une fonction attendue du produit ? Si oui, son état dégradé doit devenir un résultat explicite, testé et visible.
4. Les données 2026 doivent-elles rejoindre les figures air dès maintenant, ou seulement après la clôture de l’été ? La règle doit être codée et documentée.
5. DVF, communes et LCSQA temps réel appartiennent-ils à une prochaine fonctionnalité identifiée ? Sinon, les retirer réduirait sensiblement la surface opérationnelle.

## Limites de l’audit

- Aucun test visuel, clavier ou responsive n’a pu être réalisé dans un navigateur.
- Aucun téléchargement n’a été relancé ; l’audit a utilisé les données présentes localement.
- Aucun scan externe de vulnérabilités, licences ou dépendances transitives n’a été effectué.
- Les affirmations réglementaires ont été évaluées pour leur cohérence interne au dépôt, pas revérifiées juridiquement sur les sources officielles pendant cette passe.
- Les performances ont été estimées à partir de l’architecture et des tailles de fichiers, sans profilage navigateur ou réseau.
- L’échec de fraîcheur observé dépend de l’état local ignoré de data/processed ; il doit être reproduit dans une CI contrôlée avant d’être classé comme régression.

## Conclusion

Le dépôt se distingue positivement par son souci de traçabilité, ses gardes métier et la qualité de ses commentaires. Sa faiblesse principale est un décalage entre une mécanique de données souvent rigoureuse et des formulations publiques ou métadonnées de provenance parfois plus affirmatives que cette mécanique.

La meilleure prochaine étape n’est pas une refonte générale. Elle consiste à consolider trois contrats : **ce qu’une phrase prétend**, **l’échantillon exact qui la soutient** et **la liste exhaustive des sources qui ont produit la sortie**. Une fois ces contrats partagés par le code, les tests et les pages, le dépôt pourra raisonnablement revendiquer une démonstration reproductible de bout en bout.
