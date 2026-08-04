# Démonstrateur — analyse de données ouvertes corses

Des visualisations HTML datées et sourcées, construites sur des données publiques
corses, régénérées automatiquement, et vérifiables ligne à ligne.

Deux sujets traités à ce jour : **l'électricité corse** — de quoi le courant est fait,
au fil de la journée et des saisons, et quand il est le plus renouvelable — et
**l'ozone**, sur la qualité de l'air. Chaque sujet donne une page d'étude rédigée, ses
visuels interactifs et sa note méthodologique.

## Pourquoi les chiffres ne seront pas faux

C'est la seule question qui compte pour qui envisage de réutiliser ce travail. La
réponse ne tient pas à une promesse, elle tient à des mécanismes qu'on peut inspecter.

Chaque fichier téléchargé est **empreinté en SHA-256** et inscrit dans un manifeste
versionné, avec son URL, son producteur, sa licence et sa date de collecte. À chaque
exécution, les sources figées sont **re-vérifiées** contre cette empreinte : si un octet
a bougé, la chaîne s'arrête au lieu de publier. Aucun Parquet n'est construit depuis une
donnée non certifiée, et une **lignée de build** relie ensuite chaque figure aux données
exactes dont elle est tirée — c'est elle, et non la date du dernier téléchargement, qui
date les visuels.

Les résultats publiés sont **verrouillés par des tests**. Chaque nombre écrit dans les
études est tenu par une assertion : si une révision de la donnée source déplace un
chiffre, la suite casse et rien n'est publié. Une statistique réglementaire n'est jamais
déduite, elle est recopiée du guide de son producteur puis rejouée sur l'exemple chiffré
de ce guide — c'est ce contrôle, et non une relecture, qui a corrigé le calcul de la
moyenne 8 heures de l'ozone. Plusieurs figures refusent même de se dessiner quand la
donnée cesse de soutenir leur titre.

Enfin la chaîne **tourne toute seule**, toutes les six heures, et ne committe que ce qui
a réellement changé. L'historique du dépôt en est la trace.

## Sobriété

Les pages produites ne dépendent d'aucun service tiers : pas de CDN, pas de police
distante, pas d'appel réseau au chargement. Une seule copie de la bibliothèque
graphique est partagée par tous les visuels. Le dossier `outputs/` se déploie d'un bloc
sur n'importe quel hébergement statique, et s'intègre en iframe.

## Faire tourner la chaîne

    uv venv && uv pip install -e ".[dev]"

    fetch-data                          # télécharge, empreinte, écrit le manifeste
    python -m demonstrateur.prepare     # brut -> Parquet (DuckDB), écrit la lignée
    python -m demonstrateur.figures     # visuels électricité
    python -m demonstrateur.figures_air # visuels air, puis note_air et page_air
    python -m demonstrateur.compile_etude
    pytest                              # fumée + verrous de résultats

Ajouter une source de données, c'est ajouter une entrée dans `sources.yaml` — rien ne se
télécharge à la main. `docs/BRIEF.md` porte la question de départ et les critères de
« fini » ; `docs/RECONNAISSANCE.md`, les définitions verrouillées et les garde-fous ;
`CLAUDE.md`, l'architecture et les règles du dépôt.

    sources.yaml          manifeste des sources (URL, licence, producteur)
    data/raw/             brut téléchargé (non versionné) + _manifest.json (versionné)
    data/processed/       Parquet analysable (non versionné, régénérable)
    src/demonstrateur/    la chaîne : fetch -> prepare -> figures -> compile
    outputs/              le livrable, déployable d'un bloc
    docs/                 brief, reconnaissance, études, sources locales

## Licences

Le **code** est sous [EUPL-1.2](LICENSE), la licence publique de l'Union européenne.

Les **données** restent sous la licence de leur producteur : Licence Ouverte 2.0
(Etalab) sauf mention contraire, portée par `sources.yaml` et par le manifeste.
Réutilisation libre avec mention du producteur — ce que chaque visuel fait déjà,
puisque l'export refuse de produire une figure sans sa source.

## Sur l'assistance par IA

Ce dépôt a été écrit avec l'assistance d'un agent conversationnel ; `CLAUDE.md`, à la
racine, en porte les consignes. Autant le dire ici plutôt que le laisser découvrir.

Ce qui sépare ce travail d'une production générée n'est pas l'absence d'outil, c'est que
rien n'y est croyable sur parole. Les sources sont empreintées, les résultats verrouillés
par des tests, la lignée écrite, et ce qu'une IA a pu suggérer sans pièce à l'appui est
consigné dans `docs/SOURCES_LOCALES.md` comme piste à vérifier — jamais comme source.
Un exemple y est gardé, où un résumé automatique donnait une date qu'un article daté a
démentie.
