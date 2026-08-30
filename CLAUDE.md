# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Le repo est en français (docstrings, commentaires, messages CLI). Garde cette langue
> dans le code et la doc que tu produis.

## Ce qu'est ce projet

Démonstrateur d'analyse de données ouvertes corses. Le livrable final : des
visualisations HTML datées et sourcées, déployables en iframe sans dépendance tierce
(`plotly.min.js` mutualisé dans `outputs/` — déployer le dossier d'un bloc).
Le repo lui-même est une preuve de sérieux — il doit rester propre et reproductible.

La question fermée (électricité corse : mix, profil horaire, saisonnalité) et les critères
de « fini » sont figés dans **`docs/BRIEF.md`** — lis-le avant toute décision de contenu ou
de périmètre. Le **« test du prompt »** y est le critère éliminatoire : si un LLM généraliste
pouvait produire le livrable en 15 min, ce n'est pas le bon livrable. Ce qui fait passer le
test : donnée fraîche (pas de 15 min) + pipeline récurrent + manifeste daté/empreinté.

## Commandes

```bash
# Installation (l'environnement .venv existe déjà)
uv pip install -e ".[dev]"          # + ".[insee]" si besoin de pynsee

# Pipeline, dans l'ordre
fetch-data                          # = python -m demonstrateur.fetch : télécharge sources.yaml -> data/raw/
python -m demonstrateur.prepare     # data/raw/*.csv.gz -> data/processed/*.parquet (via DuckDB)

# Qualité
pytest                              # fumée + résultats (les tests de résultats exigent
                                    # fetch-data + prepare ; sinon ils sont sautés)
pytest tests/test_smoke.py::test_sources_yaml_est_valide   # un seul test

# Millésimes déjà passés : les retrouver dans l'historique Git du manifeste
python -m demonstrateur.reconstitution              # rapport, n'écrit rien
python -m demonstrateur.reconstitution --ecrire     # pose data/archive/_versions.json
ruff check src                      # lint (line-length 100)
ruff format src
```

## Architecture

Pipeline linéaire en trois temps, un module par étape sous `src/demonstrateur/` :

**`fetch.py`** (`fetch-data`) → lit `sources.yaml`, télécharge chaque source en streaming,
calcule son empreinte SHA-256 (canonique quand une source réestampille une enveloppe
volatile à chaque requête, cf. `empreinte_ignore_xml`) et écrit **`data/raw/_manifest.json`**. Une `url` peut
référencer une variable d'environnement `${NOM}` (jeton d'API, ex. `${ENTSOE_TOKEN}`) :
expansion au téléchargement uniquement, jamais de secret dans le manifeste ni les logs.
Le même `${NOM}` vaut pour les **en-têtes HTTP** déclarés dans `entetes:` (jeton porté
hors de l'url, ex. l'`apikey:` de Geod'air) : le manifeste n'enregistre que le gabarit, et
un en-tête déclaré ne franchit jamais une redirection qui change d'hôte — httpx retire
`Authorization` de lui-même, pas un en-tête maison. Ces trois sorties possibles d'un
secret (log, manifeste, réseau) sont tenues par `tests/test_secrets.py`, pas par la
vigilance.
Formats validés : `csv`, `csv.gz`, `json`/`geojson` (`cle_attendue`), `xml`
(`racine_attendue` — une API en erreur peut renvoyer HTTP 200 avec un document d'erreur,
qu'il ne faut jamais empreinter comme donnée). Ce manifeste est
LE cœur de la traçabilité : il enregistre URL, producteur, licence, date de collecte et
taille. C'est le seul fichier de `data/` versionné (tout le reste est régénérable, donc
gitignoré). Politique de fraîcheur : une source `glissant: true` (mix temps réel) est
re-téléchargée à **chaque** run ; une source figée déjà présente n'est pas retéléchargée
mais son empreinte est **re-vérifiée à chaque run** (le fichier local doit correspondre au
manifeste, sinon échec bruyant : restaurer la donnée, ou `fetch-data --recertifier` pour
adopter délibérément de nouveaux octets) ; ses métadonnées (licence, producteur, URL) sont
resynchronisées depuis `sources.yaml`, et le manifeste est réécrit à chaque run. Un rafraîchissement qui
échoue conserve la donnée précédente (téléchargement en `.part`, remplacement atomique) ;
les échecs n'interrompent pas les autres sources (retour code 1 en fin de run).

**`prepare.py`** → DuckDB lit les `.csv.gz` directement (sans tout charger en mémoire) et
produit des Parquet dans `data/processed/`. Ajouter une transformation = une fonction ici,
appelée depuis `main()`. **Une statistique réglementaire ne se déduit pas, elle se recopie
depuis le guide de son producteur, et se verrouille sur l'exemple chiffré de ce guide** :
la moyenne glissante 8 h de l'ozone suit le § 5.3.3 du guide LCSQA/Ineris, et
`tests/test_ozone_8h.py` rejoue son tableau 26 — c'est lui qui a corrigé le calcul, pas
une relecture. Une sortie qui dérive d'une autre sortie (`air_o3_mda8.parquet`) lit son
amont dans le dossier de `dest`, donc le **staging** : `data/processed` contiendrait
encore le run précédent. Avant toute lecture, chaque brut est **vérifié contre son empreinte**
de manifeste (un Parquet ne dérive jamais d'une donnée non certifiée) ; la construction se fait
en **staging puis bascule d'un bloc** — pas de sortie publiée à moitié. `prepare` écrit
**`data/processed/_build.json`** : la lignée qui relie chaque sortie à ses sources, à sa propre
empreinte, au commit et à l'horodatage — elle date les figures et permet à `verifier_sorties()`
de refuser une sortie altérée avant publication.

**`viz.py`** → **toute figure destinée au livrable DOIT sortir par `export_html(fig, name, source, collecte)`**.
Cette fonction incruste le pied de page « Source … — données collectées le … » : le sourçage
n'est pas optionnel, il est câblé dans l'export. Récupère la date via
`date_collecte(source_id)`, qui la lit dans la **lignée de build** (`data/processed/_build.json`,
écrite par `prepare`), avec repli sur `_manifest.json` : la date affichée est celle de la donnée
réellement présente dans le Parquet, pas du dernier `fetch`.

**`config.py`** → tous les chemins (`DATA_RAW`, `DATA_PROCESSED`, `OUTPUTS`, `MANIFEST_FILE`,
`BUILD_FILE`, `SOURCES_FILE`) sont dérivés de `ROOT`. **Aucun chemin en dur ailleurs** — importer depuis
`config`. L'import crée les dossiers de données au besoin.

**`notebooks/`** = brouillons d'exploration uniquement. Ce qui part au livrable est reporté
dans `src/` pour rester reproductible. Ne pas dépendre d'un notebook dans le pipeline.

## Règles propres à ce repo

- **Ajouter une source de données** = ajouter une entrée dans `sources.yaml` (champs requis :
  `url`, `filename`, `licence`, `producteur` — le test de fumée les vérifie), puis `fetch-data`.
  Rien ne se télécharge « à la main ».
- **Les URL des sources peuvent changer** ; plusieurs sont marquées « à vérifier / à confirmer »
  dans `sources.yaml`. En cas d'échec de `fetch-data`, vérifier l'URL sur la fiche du jeu.
- **Ne jamais committer `data/raw/` ou `data/processed/`** (sauf `_manifest.json` et
  `data/archive/_versions.json`, cf. ci-dessous). Tout le reste se régénère depuis
  `sources.yaml`.
- **Chaque visuel cite sa source et sa date** — via `viz.export_html`, pas à la main.
- **Le cron est seul propriétaire d'`outputs/`.** Régénérer en local pour VÉRIFIER une figure
  est normal ; committer le résultat ne l'est pas. Une même figure sérialisée sous Windows
  écrit ses accents en clair là où le runner Linux les échappe en `\uXXXX` (plotly 6.9.0 des
  deux côtés — c'est l'environnement, pas la version). Committer une régénération locale
  fabrique donc un diff sur des fichiers dont le contenu n'a pas bougé, que le cron
  rebasculera au run suivant. Or « le rafraîchissement planifié ne committe que ce qui a
  réellement changé » est une propriété qu'on met en avant : ces diffs fantômes la
  décrédibilisent. Ce qui se committe à la main, c'est le CODE de la figure ; sa sortie
  arrive au prochain run. **Une exception, et une seule** : `outputs/etude.html` accompagne
  une modification de `docs/etude.md` dans le même commit, parce qu'un test les lie sans
  skip — cette page est du HTML de texte, pas du JSON Plotly, donc elle échappe au diff
  d'accents qui motive la règle.
- **Le cron est aussi le publieur.** Depuis le 06/08/2026, il synchronise `outputs/` vers le
  bucket Scaleway `air-et-energie-en-corse` (région `fr-par`) après les verrous de résultats :
  rien ne part en ligne si un verrou casse, mais une collecte partiellement en échec se
  déploie — c'est l'arbitrage déjà retenu pour T1 « affichage suspendu ». La vitrine ne se
  dépose donc pas plus à la main que les visuels ne se committent à la main. Sans les secrets
  `SCW_ACCESS_KEY` / `SCW_SECRET_KEY`, l'étape se saute avec un avertissement plutôt que de
  faire échouer le run.
- **Les millésimes se déposent hors du dépôt Git.** Depuis le 20/08/2026, chaque contenu
  distinct d'une source part dans un bucket d'archive **append-only** — clés immuables
  `archive/<source_id>/<AAAA>/<MM>/<instant>_<sha256>.<ext>`, jamais de `sync`, jamais de
  `--delete` — pendant que `data/archive/_versions.json`, versionné, dit quelle version la
  chaîne détenait entre quand et quand. Les deux moitiés sont nécessaires : l'index sans
  les octets promet une version que plus personne ne peut produire, les octets sans l'index
  ne disent pas à quelle date ils s'appliquaient. **Aucune rétention destructive** : rien
  n'est jamais supprimé ni échantillonné, une révision effacée aujourd'hui ne se
  récupérerait pas pour un backtest dans deux ans. Configuration par `ARCHIVE_BUCKET` +
  `ARCHIVE_ACCESS_KEY`/`ARCHIVE_SECRET_KEY`, qui priment sur `SCW_ACCESS_KEY`/`SCW_SECRET_KEY`
  — ces dernières servent aussi à `aws s3 sync --delete` pour la vitrine, donc une clé propre
  à l'archive est préférable : restreinte à son seul bucket, elle ne peut pas effacer la
  vitrine, et la clé de la vitrine ne peut pas atteindre l'archive. Configuration absente,
  la collecte continue et marque les versions `payload_archived: false`, reprises au run
  suivant. Configuration PRÉSENTE MAIS REFUSÉE, c'est autre chose et cela ne se confond
  plus depuis le 30/08/2026 : une erreur déterministe (requête impossible à former,
  401/403) arrête les dépôts pour tout le run et **rougit le run**, sans interrompre la
  collecte. Une panne revient, une clé malformée non — la traiter en panne l'a laissée
  tenir une journée derrière un cron vert. De même, l'avertissement de millésimes ne
  compte QUE les reprises réalisables (`versions_non_deposees`) ; ce que plus aucune
  reprise ne sauvera est un constat séparé (`versions_octets_perdus`), et l'état
  d'exploitation se lit sur `versions_courantes_sans_octets` — zéro = tout contenu
  détenu est durable. **Le bucket d'archive n'est jamais
  celui de la vitrine** — celle-ci est synchronisée avec `--delete`, qui l'effacerait, et
  `depot.configurer()` refuse explicitement ce cas.
- **L'historique d'avant l'archive se reconstitue depuis Git, pas depuis rien.**
  `data/raw/_manifest.json` est versionné depuis le 19/07/2026 : chaque passage du cron y a
  laissé l'empreinte de ce que chaque source disait ce jour-là. `reconstitution.py` en tire
  les intervalles de connaissance des versions antérieures au 20/08/2026 — 940 millésimes sur
  38 sources, que l'index n'aurait sinon jamais connus. Trois choses à savoir avant de s'en
  servir : (1) ces versions n'ont PAS d'octets et n'en auront jamais (`data/raw/` n'est pas
  versionné), d'où `payload_key: null` et `origine: "manifeste_git"` — `versions_sans_octets()`
  les liste, `versions_non_deposees()` les ignore, sans quoi le CI avertirait pour toujours de
  reprises impossibles ; (2) la ligne d'histoire qui fait foi est le **premier parent**, celle
  de l'intégration : mêler les branches fabrique des retours en arrière que la chaîne n'a
  jamais faits, et `--ecrire` refuse `--toutes-branches` ; (3) une source collectée sur une
  branche est datée de sa FUSION, donc tardivement plutôt que trop tôt — un backtest qui se
  croit informé plus tôt qu'en réalité fuit, l'inverse se prive seulement. Le registre ne se
  réécrit pas : une seconde exécution vient devant les versions vivantes sans en retirer une.
  **`--ecrire` part de `REF_FAISANT_AUTORITE` (`origin/master`), jamais de là où l'on se
  trouve**, et refuse si le commit parcouru n'est pas celui de cette référence — comparaison
  par COMMIT, parce qu'en CI on travaille en HEAD détachée, où le nom de branche ne prouve
  rien. Ce n'est pas de la rigueur de principe : lancé depuis une branche où `master` vient
  d'être fusionné, le premier parent traverse la fusion en un pas et saute tout ce que
  l'intégration a fait pendant ce temps — **969 millésimes au lieu de 1 410, mesuré le
  29/08/2026**, sans un mot dans le rapport.
- **Détenu n'est pas certifié.** Une source qui disparaît du manifeste garde son intervalle
  OUVERT : `version_connue_a` continue donc de rendre le dernier contenu détenu pendant le
  trou. C'est volontaire et c'est vrai — nous détenions bien ces octets — mais cela ne dit
  pas que la source figurait au manifeste, ni qu'elle y était certifiée, à cet instant. Le
  cas est réel : le 20/07/2026, six sources ENTSO-E ont quitté le manifeste le temps d'un
  run avant d'y revenir avec d'autres empreintes. Un usage qui exige la certification croise
  avec le manifeste de la date voulue (`reconstitution.instantanes`) ; l'index seul répond à
  « que détenions-nous », et à rien d'autre.
- **La traçabilité est vérifiée, pas seulement déclarée** : `fetch` re-contrôle chaque source
  figée à chaque run, `prepare` refuse un brut non certifié et écrit la lignée (`_build.json`),
  les figures datent d'après cette lignée. L'empreinte d'une source qui réestampille son
  enveloppe (ex. ENTSO-E) est **canonique** : `empreinte_ignore_xml` liste les **chemins XML
  précis** à neutraliser (`GL_MarketDocument/mRID`, `.../createdDateTime` — l'enveloppe de
  document, jamais les `mRID` imbriqués des TimeSeries, qui sont de la donnée), reproductible
  d'un téléchargement à l'autre. Calcul unique dans `provenance.py`.
- **Un verrou s'éprouve sur des données AVANT d'être fusionné.** Depuis le 28/08/2026 la
  CI de PR a deux jobs : `valider` (environnement d'`uv.lock`, sans données) et `verrous`,
  qui restaure le cache `data/raw` du pipeline en lecture seule, rejoue `prepare` → figures
  → pages, puis toute la suite **sauf les tests marqués `fraicheur`** — ceux-là mesurent la
  date du dernier passage du cron, pas le code. `verrous` tourne dans l'environnement du
  CRON (pip, dernières versions) et non sous `uv.lock`, sans quoi il ne prédirait rien :
  c'est un `pandas` sans `pytz` qui a suspendu la publication le 28/08, sous un `uv.lock`
  qui, lui, passait. Lire les deux ensemble : `valider` vert + `verrous` rouge =
  l'environnement a bougé, pas le code. Et ne PAS y recopier le
  `git checkout -- data/raw/_manifest.json` du pipeline : ce job ne collecte pas, le couple
  (octets, empreintes) du cache est cohérent, le manifeste versionné ne l'est plus avec ces
  octets-là.
- Licences des données : Licence Ouverte 2.0 (Etalab) sauf mention contraire ; réutilisation
  libre avec mention du producteur.
