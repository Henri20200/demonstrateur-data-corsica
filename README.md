# Démonstrateur — analyse de données ouvertes corses

Des visualisations HTML datées et sourcées, construites sur des données publiques
corses, régénérées automatiquement, et vérifiables ligne à ligne.

Deux sujets traités à ce jour : **l'électricité corse** — de quoi le courant est fait,
au fil de la journée et des saisons, et quand il est le plus renouvelable — et
**l'ozone**, sur la qualité de l'air. Chaque sujet donne une page d'étude rédigée, ses
visuels interactifs et sa note méthodologique.

## Comment les résultats sont contrôlés

C'est la seule question qui compte pour qui envisage de réutiliser ce travail. La
réponse ne tient pas à une promesse, elle tient à des mécanismes qu'on peut inspecter.

Chaque fichier téléchargé est **empreinté en SHA-256** et inscrit dans un manifeste
versionné, avec son URL, son producteur, sa licence et sa date de collecte. À chaque
exécution, les sources figées sont **re-vérifiées** contre cette empreinte : si un octet
a bougé, la chaîne s'arrête au lieu de publier. Les bruts déclarés sont contrôlés avant
préparation, et une **lignée de build** relie ensuite chaque figure aux données
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

Le livrable comporte aussi un **dossier de vérification téléchargeable** du résultat
« +22 % entre juin et juillet » : extrait EDF, provenance et script Python autonome
sans dépendances ni réseau. La page indique la différence entre la date de compilation
et la période des observations. Le site du porteur est
[Méthodes & Révélations](https://www.methodes-revelations.fr/) ;
contact : contact@methodes-revelations.fr.

## Faire tourner la chaîne

    uv sync --locked --extra dev

    uv run --no-sync fetch-data                         # collecte et manifeste
    uv run --no-sync python -m demonstrateur.prepare    # Parquet et lignée
    uv run --no-sync python -m demonstrateur.figures    # visuels électricité
    uv run --no-sync python -m demonstrateur.figures_air
    uv run --no-sync python -m demonstrateur.note_elec
    uv run --no-sync python -m demonstrateur.note_air
    uv run --no-sync python -m demonstrateur.page_air
    uv run --no-sync python -m demonstrateur.compile_etude
    uv run --no-sync python -m demonstrateur.preuve_demande
    uv run --no-sync python -m demonstrateur.accueil
    uv run --no-sync pytest                             # fumée + verrous de résultats

    python -m http.server -d outputs 8000   # http://127.0.0.1:8000/etude.html

L'étude se lit par ce serveur local, pas par un double-clic : la page assemble ses
figures en `<iframe>` relatives qui tirent le bundle Plotly mutualisé d'`outputs/`,
et un `file://` les bloque.

Le cron utilise le même `uv.lock` que la validation. La CI vérifie également, dans un
parcours séparé, les dernières dépendances autorisées avant leur adoption. Chaque nouveau
bundle JavaScript porte son SHA-256 dans son nom pour rendre le cache navigateur fiable.

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
