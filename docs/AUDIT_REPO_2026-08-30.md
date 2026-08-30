# Audit code et architecture — demonstrateur-data-corsica

**Date :** 30 août 2026
**Branche / commit :** `master` @ `2ac62b9` (merge PR #45)
**Référentiel :** les invariants que le dépôt déclare lui-même (CLAUDE.md, docs/BRIEF.md) — traçabilité vérifiée et non seulement déclarée, staging puis bascule d'un bloc, aucun chemin en dur hors `config.py`, cron seul propriétaire d'`outputs/`, archive append-only, premier parent faisant foi.
**Périmètre :** `src/demonstrateur/`, `tests/`, `sources.yaml`, `.github/workflows/`, `pyproject.toml`. `data/` et `outputs/` lus, jamais modifiés.
**Précédent :** AUDIT_REPO_2026-08-05.md (commit `f1e78ca`, 15 constats) — chaque constat d'alors est resitué ; ce qui y figurait déjà est marqué « connu », jamais présenté comme une découverte.
**Nature :** lecture intégrale du code applicatif (7 350 lignes) et des tests (5 898 lignes), contrôles exécutés localement, aucune correction appliquée.
**Statut au 30/08/2026** : C-01 et C-05 fermés par #46. Les autres constats restent ceux de l'audit initial, qui n'est pas réécrit — un audit est un instantané daté, pas un backlog.

## Contrôles exécutés

| Contrôle | Résultat | Interprétation |
|---|---|---|
| `pytest` (suite complète, données locales) | **31 échecs, 192 réussites, 11 sautés, 2 erreurs** | Les 31 échecs sont des artefacts d'état local, PAS des défauts de master : `data/processed` date du 19/08 (`_build.json` : commit `67fa9bb4`), antérieur à la refonte d'horodatage du 23/08 — la colonne `annee_locale` n'y existe pas (`BinderException`), les fenêtres horaires y sont celles d'avant correction. Vérifié sur pièce (cf. C-06). |
| `ruff check src` | Propre | Aucun défaut sur les règles activées |
| `ruff format --check src` | 13 fichiers à reformater | Inchangé depuis le 05/08 (15 alors) — le formatage n'est toujours ni appliqué ni contrôlé en CI |
| Lignée ↔ disque | **2 Parquet hors lignée** (`air_temperature_jour`, `meteo_corse`) | Démonstration en direct du reliquat AUD-03 (cf. C-03) |
| Chemins en dur hors `config.py` | **Aucun** | `grep` sur `data/`, `outputs/` littéraux : zéro occurrence hors commentaires — l'invariant tient |
| Contradiction éditoriale publiée | **Confirmée sur les sorties du cron** (commit `3b4e87e`, 29/08) | `a0_note_methodologique.html` porte « qu'on en mesure le plus », `air_ozone.html` porte « plus souvent que la majorité des autres » (cf. C-01) |

## Synthèse

Depuis le 05/08, le dépôt a fermé plusieurs de ses constats les plus lourds : la CI de PR éprouve désormais les verrous sur données réelles dans l'environnement du cron (AUD-06, job `verrous` du 28/08), les cohortes air sont alignées et comptées depuis la donnée (AUD-02, PR #34 et suivantes), les métadonnées de stations sont vérifiées contre le référentiel certifié de leur producteur (AUD-05 pour l'essentiel), et deux chantiers neufs — archive des millésimes, reconstitution Git — arrivent avec une couverture de test remarquable (79 tests dédiés, ordre octets-avant-index, refus d'écrire hors référence).

Ce qui reste relève de deux familles. D'une part des **reliquats connus** (AUD-03, 04, 08, 09, 10, 11, 12, 14, 15), dont un seul a gagné en urgence : la fenêtre air 2020-2025, maintenant que l'été 2026 est clos. D'autre part — et c'est le motif central de cet audit — **la correction du 29/08 n'a pas été propagée partout** : la note méthodologique de l'air publie encore le superlatif que la page assemblée vient de retirer comme faux, et la note électricité publie encore le « le soir » que T2b a remesuré en « 14 h - 20 h » le 23/08. C'est le mécanisme d'AUD-07 qui se rejoue : quand une phrase vit à deux endroits et qu'un seul est verrouillé, la correction s'arrête au verrou.

| Niveau | Nombre | Dont connus du 05/08 |
|---|---:|---:|
| Critique | 0 | — |
| Élevé | 3 | 1 |
| Moyen | 8 | 5 |
| Faible | 3 | 2 |

---

## Constats

### C-01 — La note de l'air publie le superlatif que la page a retiré comme faux le 29/08

**Niveau : élevé — défaut réel (nouveau)**

Le 29/08, le titre d'A4 et l'encadré de conclusion de la page air ont été réécrits parce que « c'est à la campagne qu'on en mesure le plus » était faux — Bastia Montesoro dépasse 15,1 % de ses journées contre 10,4 % à Venaco ; le commentaire de `page_air.py:177-180` documente la correction, et la garde d'A4 (`figures_air.py:590-596`) ne tient plus que « la majorité ». Or `note_air.py:171-172` publie toujours : « c'est même à la campagne, loin des moteurs, qu'on en mesure le plus ». Vérifié sur les sorties du dernier passage du cron (commit `3b4e87e`) : les deux pages en ligne se contredisent — la note dit « le plus », la page dit « la majorité ».

La phrase de la note est ambiguë (elle peut se lire sur les concentrations moyennes, où le superlatif serait peut-être vrai), mais rien dans le dépôt ne calcule ni ne verrouille cette lecture-là — et le dépôt a précisément jugé le 29/08 que ce superlatif ne devait plus être publié.

**Impact :** contradiction entre deux textes publiés du même build, sur la phrase la plus corrigée du sujet ; c'est la caution méthodologique (la note) qui porte la version fausse.

**Test qui verrouillerait :** étendre `test_provenance.test_la_note_dit_ce_que_les_chiffres_ne_disent_pas` — soit interdire le superlatif et exiger la formulation « la majorité » (même famille que le verrou « jamais si tel producteur est en règle »), soit, mieux, dériver la phrase de `perimetre_a4()` comme le titre d'A4 l'est déjà. Le verrou de calcul existe (`test_l_air_de_campagne_n_est_pas_meilleur`) ; c'est le verrou de texte qui manque — les deux familles, comme le rappelle la mémoire du 22/08.

### C-02 — Un index de millésimes corrompu est remplacé en silence, puis commité

**Niveau : élevé — défaut réel (nouveau)**

`archive._charger` (`archive.py:150-159`) avale un `JSONDecodeError` et rend `{}` : « on repart d'un index vide plutôt que d'interrompre la chaîne ». Or `_sauver` (`archive.py:162-167`) écrit `_versions.json` par `write_text` direct — non atomique : un processus tué en pleine écriture laisse exactement le JSON tronqué que `_charger` avalera au run suivant. La suite est mécanique : chaque `enregistrer_version` repart d'un index vide, ré-observe toutes les sources « pour la première fois », redépose leurs octets sous des clés NEUVES (l'instant fait partie de la clé, `depot.py:156-172`), et le cron committe le registre reconstruit (`pipeline.yml`, étape commit, `git add data/archive/_versions.json` inconditionnel). Les ~1 445 intervalles de connaissance — « la seule partie qui ne se reconstruit pas après coup », dixit `archive.py:31` — disparaissent du fichier vivant sans un avertissement.

La perte n'est pas définitive (le fichier est versionné, un humain peut fouiller l'historique) mais rien ne la SIGNALE : le commentaire de `_charger` affirme que « la perte est signalée par l'absence d'historique », or aucun code ne regarde cette absence. C'est l'inverse exact de la philosophie du disjoncteur de volume, qui rougit le run pour bien moins.

**Impact :** le fichier dont le dépôt dit qu'il « fait foi » peut être silencieusement remplacé par un registre d'un jour, et la propriété append-only (« le registre ne se réécrit pas ») cesser d'être vraie sans qu'aucun verrou morde.

**Test qui verrouillerait :** (1) un index illisible fait ÉCHOUER la collecte (ou met le fichier en quarantaine `.corrompu` et rougit le run) — test : écrire un JSON tronqué, appeler `enregistrer_version`, exiger l'échec bruyant ; (2) garde « le registre ne rétrécit jamais » : avant `_sauver`, refuser un index qui compte moins de versions que le fichier en place (c'est l'invariant que `reconstitution.fusionner` respecte déjà à la main — `test_la_fusion_ne_retire_aucune_version_vivante` — mais que rien ne tient sur le chemin de la collecte).

### C-03 — Une sortie hors lignée reste consommable, et cette machine le démontre

**Niveau : élevé — connu (AUD-03), toujours ouvert, mesuré en direct**

`verifier_sorties()` (`prepare.py:1471-1490`) contrôle les sorties QUE la lignée énumère ; elle ne rejette pas un Parquet excédentaire. Mesuré sur ce poste : `_build.json` (19/08, commit `67fa9bb4`) énumère 8 sorties, le disque en porte 10 — `air_temperature_jour.parquet` et `meteo_corse.parquet` sont hors lignée, et `figures_air.fig_a2_ozone_et_chaleur` lit le premier (`figures_air.py:33` et 428) après un `verifier_sorties()` qui passe au vert. Les consommateurs à `Path.exists()` demeurent : `figures.py:1089` (`SARD`), `note_elec.py:89` (`SARD_PATH`).

**Exposition, à dire honnêtement :** en CI, `data/processed` n'est PAS caché — le cron et le job `verrous` reconstruisent tout à chaque run, donc un Parquet orphelin ne peut pas y survivre d'un run à l'autre ; le risque effectif est local (poste de travail, builds interrompus, changements de branche — le cas mesuré ici). Mais l'invariant AFFICHÉ par CLAUDE.md (« un Parquet ne dérive jamais d'une donnée non certifiée », « refuser une sortie altérée avant publication ») est tenu par la structure du workflow, pas par le code : une sortie périmée n'est ni « altérée » ni certifiée, et elle se laisse lire.

**Impact :** une figure régénérée localement (le geste « VÉRIFIER une figure » que CLAUDE.md autorise) peut mélanger données du jour et données d'il y a dix jours sans aucun signal.

**Test qui verrouillerait :** `verifier_sorties()` liste les `*.parquet` du dossier et refuse tout fichier absent de la lignée (ou le met en quarantaine) ; test : poser un Parquet orphelin, exiger l'échec. C'est la recommandation AUD-03 première, toujours valable, et elle couvre aussi C-06 en partie.

### C-04 — La date affichée par une figure composite reste celle d'une seule source

**Niveau : moyen — connu (AUD-04), toujours ouvert**

Les cinq figures air affichent la date de `aee_o3_venaco_continu` seul (`figures_air.py:718`, `page_air.py:38`) alors qu'elles assemblent 12 sources AEE + la météo pour A2 (qui n'affiche QUE la date météo, `figures_air.py:724`) ; T6 affiche `entsoe_sardaigne_2024` en combinant EDF et ENTSO-E (`figures.py:1092`). La lignée (`_build.json`) contient pourtant, par sortie, la liste exacte des sources et leurs dates : la donnée pour calculer « collectées entre le X et le Y » existe déjà, elle n'est pas lue.

**Impact :** la date visible peut masquer une source plus ancienne — précisément le genre de détail qu'un client vérifierait.

**Test qui verrouillerait :** `date_collecte` acceptant une LISTE de sources et rendant min/max depuis la lignée ; test : deux sources aux dates distinctes → le pied porte la plage, pas l'une des deux.

### C-05 — T2b : le créneau du titre est écrit en dur, et la note électricité dit encore « le soir »

**Niveau : moyen — défaut réel (nouveau, séquelle de la correction du 23/08)**

Trois désalignements autour de la même figure :

1. **Le titre n'est pas verrouillé.** « En juillet, la hausse est surtout marquée de 14 h à 20 h » est une constante (`figures.py:193`) ; le plateau, lui, est calculé et gardé — mais la garde accepte 12 h-21 h (`figures.py:174`), plus lâche que le titre, et l'annotation calculée `({h1}-{h2} h)` (`figures.py:188`) peut diverger du titre sans qu'aucun test tombe. Aucun « 14 h à 20 h » dans `tests/`. À comparer avec A5, dont le « 11 h à 18 h » est verrouillé à la borne près (`test_resultats.py:1370-1372`) — la règle du dépôt existe, elle n'est pas appliquée ici.
2. **La note électricité contredit la figure.** `note_elec.py:208` publie « La hausse de juillet est mesurée, et elle a lieu le soir » — le mot que T2b a précisément retiré le 23/08 (« la figure disait “le soir”… une fenêtre en partie fabriquée par l'ancien horodatage », `figures.py:150-153`). Le verrou de la note (`test_provenance.py:358`) tient « montrent quand, pas pourquoi », pas le « quand » lui-même.
3. **Le test parle encore l'ancienne langue.** `test_resultats.py:143` : « maximal le soir (16-22 h) » — l'assertion (pic dans 16-22) est compatible avec le plateau 14-20, mais le dépôt publie désormais deux fenêtres différentes pour le même phénomène selon le fichier qu'on lit.

**Impact :** même mécanisme que C-01 — une remesure actée d'un côté, l'ancien récit qui survit de l'autre.

**Test qui verrouillerait :** dériver le titre de T2b de `(h1, h2)` comme A4 dérive le sien de `perimetre_a4()` ; ajouter à `test_surcroit_juillet_le_soir` l'assertion que le plateau publié est 14-20 (bornes exactes, comme A5) ; aligner la phrase de la note sur la fenêtre calculée ou la faire pointer sur « l'après-midi et le début de soirée ».

### C-06 — Le verdict de pytest dépend d'un état local que rien ne date

**Niveau : moyen — défaut réel (variante d'un point déjà noté le 05/08)**

31 tests échouent sur ce poste, tous parce que `data/processed` a été bâti par `67fa9bb4` (19/08) alors que le code est à `2ac62b9` : `annee_locale` n'existe pas dans le Parquet local (`BinderException` brute), et les fenêtres horaires sont celles d'avant la correction de fuseau — d'où des messages du type « l'étude écrit “de 9 heures à 15 heures” » qui accusent l'étude quand c'est le Parquet qui est vieux. La lignée PORTE le commit qui l'a produite (`_build.json`, écrit par `prepare.py:1493-1502`) ; aucun test ne le lit.

**Impact :** un développeur qui lance `pytest` avant `prepare` obtient 31 rouges au diagnostic trompeur ; le réflexe de « voir casser un verrou » (mémoire du 27/08) perd sa valeur quand 31 verrous cassent pour une raison qui n'en est pas une. L'audit du 05/08 avait rencontré le phénomène (1 échec) ; il a grossi avec le nombre de verrous.

**Test qui verrouillerait :** une fixture de module dans `test_resultats.py` qui compare `_build.json["commit"]` à `git rev-parse HEAD` et SAUTE bruyamment (« données préparées par 67fa9bb4, code à 2ac62b9 — relancer prepare ») en cas d'écart. Skip et non échec : le cron et `verrous` régénèrent toujours avant pytest, seul le poste local est concerné.

### C-07 — La complétude météo se vérifie toujours par jour global, pas par poste

**Niveau : moyen — connu (AUD-08), toujours ouvert**

La garde de sortie 2 de `meteo_corse_to_parquet` compte `count(DISTINCT heure_locale)` par `date_locale` seule (`prepare.py:1326-1328`) : une journée où deux postes incomplets se complètent passe. `n_heures_temp` par poste existe dans le croisement (`prepare.py:1139`) mais aucun consommateur ne l'exige — la requête d'A2 (`figures_air.py:422-431`) n'a pas de condition dessus : un `t_max` calculé sur 6 heures de poste entrerait dans la moyenne d'une tranche.

**Impact :** garde-fou qui ne détecterait pas une future dégradation — le constat du 05/08 mot pour mot ; les données actuelles passent, c'est la capacité de détection qui manque.

**Test qui verrouillerait :** grouper la garde par `(num_poste, date_locale)` ; test : deux postes à 12 h chacun sur la même journée → échec. Et/ou exiger `n_heures_temp >= 23` dans A2, en le disant sur la figure.

### C-08 — La collecte n'a pas été durcie depuis le 05/08

**Niveau : moyen — connu (AUD-09), partiellement corrigé**

Ce qui a été fait, et bien fait : la non-fuite des secrets sur les trois sorties est désormais tenue par `tests/test_secrets.py` (log, manifeste, réseau — y compris le non-franchissement de redirection inter-hôtes, testé avec un client espion). Le reste du constat demeure :

- `_download` compare `netloc` seul (`fetch.py:222`) : une redirection HTTPS → HTTP sur le même hôte conserverait l'en-tête secret en clair — le schéma ne fait pas partie de l'origine de confiance ;
- aucun plafond de taille ni retry/backoff : `_valider` lit des JSON entiers en mémoire (`fetch.py:372`), un serveur qui répond 30 Go remplit le disque ;
- le manifeste s'écrit par `write_text` direct (`fetch.py:93-95`), sans `.tmp` + `replace` — `_ecrire_lignee` (`prepare.py:1514-1517`) montre pourtant le geste juste trois cents lignes plus loin ;
- `date.today()` (`fetch.py:178, 321, 324`) date les collectes dans le fuseau de la machine — sur le runner UTC c'est correct, sur ce poste une collecte de 00 h 30 serait datée de la veille UTC.

**Impact :** surface réseau du composant le plus exposé du dépôt ; aucun incident à ce jour, mais deux incidents passés (jeton en log, cache/manifeste) sont nés dans cette zone.

**Test qui verrouillerait :** dans `test_secrets.py`, une redirection `https://hote/...` → `http://hote/...` ne doit pas porter l'en-tête (même client espion, une réponse de plus) ; pour l'atomicité, un test qui tue l'écriture est difficile — le geste `.tmp`+`replace` se recopie de `_ecrire_lignee`, et c'est la revue qui le tient.

### C-09 — La fenêtre air 2020-2025 est close depuis hier, et rien ne force la décision

**Niveau : moyen — connu (AUD-10), devenu d'actualité**

`ANNEES = "BETWEEN 2020 AND 2025"` (`figures_air.py:50`), « Six étés » dans le périmètre publié (`figures_air.py:73`), et les tests verrouillent 2020-2025 en dur (`test_resultats.py:1356` et ailleurs). C'était un gel analytique légitime — six étés complets — mais l'été 2026 s'est achevé le 31/08 : la donnée du septième été existe, et AUCUN test ne signale que la fenêtre est restée figée par oubli plutôt que par décision (la recommandation AUD-10 « ajouter un test empêchant une fenêtre historique de rester figée » n'a pas été suivie). Par ailleurs `dvf_2a/2b_2024` et `communes_corse` sont toujours collectées (et DVF préparée, `prepare.py:1378`) sans qu'aucune figure ne les consomme — surface de collecte, de cache et de manifeste sans sortie.

**Impact :** dès septembre, « six étés de mesures » sera une fenêtre qui en ignore un septième disponible, sans que le lecteur sache si c'est un choix.

**Test qui verrouillerait :** un test `fraicheur` (la marque existe) qui échoue quand `max(date_locale)` de la série dépasse la borne haute de la fenêtre d'au moins un été complet — forçant à trancher : étendre la fenêtre, ou documenter le gel. Pour DVF/communes : décider (sortie planifiée, ou retrait de `sources.yaml`).

### C-10 — Reliquats éditoriaux d'AUD-01/05 : « le plus respirable » et « rien n'a été saisi à la main »

**Niveau : moyen — connu, partiellement corrigé**

- L'annotation d'A5 dit toujours « le plus respirable » (`figures_air.py:694`) — la recommandation AUD-01 (« le moins chargé en ozone ») n'a pas été appliquée à cette annotation, alors que la note de pied de la MÊME figure (`figures_air.py:308-309`) explique que ce creux est « moins chargé en ozone, pas plus pur ». La figure se corrige elle-même en petit caractère.
- `note_air.py:200` : « Rien n'a été téléchargé ni saisi à la main » — l'absolu que AUD-05 avait relevé. La note électricité a été corrigée en « Aucun FICHIER n'a été téléchargé ni saisi à la main » (`note_elec.py:253`) et nomme son chiffre recopié ; la note air garde la formule absolue alors que `STATIONS_AIR`, l'appariement et les seuils sont bien saisis à la main (sourcés et vérifiés, mais saisis).

**Test qui verrouillerait :** pour A5, interdire « respirable » dans les annotations (verrou de texte) ; pour la note air, aligner sur la formulation de la note élec et le tenir par le même test de provenance.

### C-11 — Accessibilité des figures isolées et iframes de l'étude : rien n'a bougé

**Niveau : moyen — connu (AUD-11, AUD-12), toujours ouvert**

`export_html` appelle `fig.write_html(full_html=True)` sans gabarit (`viz.py:419`) : pas de `lang`, pas de repli textuel, pas de `noscript`. Les titres d'iframe restent techniques (« Visualisation : t4_heure_verte », `compile_etude.py:66`). La page électricité assemble toujours par iframes (`compile_etude.py:61-67`) là où la page air montre le modèle à un seul contexte Plotly — l'écart de qualité entre les deux pages du même livrable est visible.

**Test qui verrouillerait :** pour les titres d'iframe, une table nom → titre éditorial vérifiée exhaustive (même mécanique que `test_toute_sortie_du_livrable_est_regeneree_par_le_cron`).

### C-12 — Commentaires et messages périmés qui contredisent le code

**Niveau : faible — défauts réels (nouveaux), correction triviale**

- `prepare.py:1071-1074` : le message d'erreur d'`o3_mda8_to_parquet` dit « doit être bâtie APRÈS air_corse.parquet » — l'amont réel est `air_serie.parquet` (ligne 1069) ; un opérateur suivrait la mauvaise piste.
- `prepare.py:1406` : « APRÈS air_o3_serie.parquet » — fichier qui n'existe pas (c'est `air_serie.parquet`).
- `pipeline.yml`, en-tête et commentaire du cache : « T1 avertit > 24 h et bloque > 48 h » — les seuils sont 12/24 depuis le 27/08 (`figures.py:62-63`). Deux occurrences.

**Verrou :** aucun raisonnable ; c'est de la revue. Les trois se corrigent en cinq minutes.

### C-13 — Dette de maintenabilité : inchangée, en croissance mécanique

**Niveau : faible — connu (AUD-14, AUD-15), toujours ouvert**

`ROOT` déduit du chemin du module et `mkdir` à l'import (`config.py:5, 41-42`). `prepare.py` est passé de ~1 200 à 1 557 lignes, `figures.py` à 1 119 ; les connexions DuckDB ne sont jamais fermées (aucun `close()` ni contexte dans tout `src/`). `ruff format` reformaterait 13 fichiers et n'est pas contrôlé en CI — la commande figure pourtant dans CLAUDE.md. Aucun de ces points ne casse rien aujourd'hui ; tous renchérissent le troisième sujet (cf. Architecture).

### C-14 — Trois fichiers vivent hors de Git depuis des semaines

**Niveau : faible — hygiène**

`AUDIT_REPO_2026-08-05.md`, `docs/BRIEF_EAU.md` et `docs/VITRINE.md` sont non suivis (`git status`), le dernier écrit le 19/08. Le brief fait du dépôt « une preuve de sérieux » ; des documents de référence qui n'existent que sur un poste n'en font pas partie — et ne survivraient pas au poste. À committer (ou à écarter délibérément, mais alors les supprimer).

---

## Choix assumés documentés — ne pas re-signaler

Relevés comme écarts possibles, puis vérifiés DOCUMENTÉS avec leur justification ; ils ne comptent pas comme défauts :

- **Environnement du cron non épinglé** (pip dernières versions, pas `uv.lock` — AUD-13). Arbitrage inversé mais raisonné : le job `verrous` éprouve désormais chaque PR dans CET environnement (`validation.yml`, trois choix commentés), et l'écart `valider` vert / `verrous` rouge est promu outil de diagnostic. Réserve maintenue : c'est de la détection, pas de la prévention — l'incident pandas/pytz du 28/08 s'est produit ENTRE deux PR, et un cron peut encore casser seul. `plotly` est épinglé, lui, pour la stabilité des sorties.
- **Publication d'une collecte partiellement en échec** (AUD-13) : arbitrage « affichage suspendu » écrit dans CLAUDE.md et dans le workflow ; l'échec est re-signalé en fin de run.
- **Intervalle laissé OUVERT quand une source quitte le manifeste** : documenté trois fois (CLAUDE.md, `archive.py:487-496`, testé par `test_une_source_disparue_du_manifeste_garde_son_intervalle_ouvert`), avec le chemin pour qui exige la certification.
- **Premier parent faisant foi, écriture refusée ailleurs** : documenté, mesuré (969 vs 1 410), testé.
- **Fenêtre T6 2019-2024, B20 en thermique, STEP hors total** : chacun avec sa preuve chiffrée en commentaire et son verrou.
- **`_last_checked.json` non versionné** : justifié par la propriété « ne committe que ce qui a changé ».

## Cohérence tests ↔ code : ce qui est verrouillé, ce qui ne l'est pas

**Verrouillé, vérifié sur pièce :** T2 « +22 % » (`test_bond_juin_juillet`, à l'arrondi près), A5 « 11 h-18 h » (bornes exactes), les chiffres en dur de l'étude (231/281/307, 36/43/16, 6/58/25…), le gabarit de largeur des titres (étalonné sur rendu réel), la non-retouche d'`etude.html` (comparaison au rendu de la source), l'enrôlement au cron de tout module écrivant dans `outputs/` (`test_toute_sortie_du_livrable_est_regeneree_par_le_cron`), les trois sorties d'un secret, l'invariance au fuseau de session des chiffres publiés (`test_v2`, deux fuseaux), le tableau 26 du guide LCSQA, l'ordre octets-avant-index de l'archive, le refus du bucket vitrine, le disjoncteur de volume.

**Non verrouillé (propriétés annoncées sans test) :** le titre de T2b « 14 h à 20 h » (C-05) ; le superlatif de la note air (C-01) ; « le registre ne se réécrit pas » sur le chemin de la collecte (C-02 — tenu côté `reconstitution`, pas côté `archive`) ; « bascule d'un bloc » au sens fort — aucun test ne pose un Parquet orphelin devant `verifier_sorties` (C-03, le test manquant d'AUD-03) ; la complétude météo par poste (C-07).

## Architecture : ce qui rendra le sujet eau facile, et ce qui le rendra pénible

**Ce qui aidera.** Le pipeline linéaire est sain : ajouter une source = une entrée `sources.yaml` (validée par la fumée), une fonction dans `prepare` enrôlée au plan, et la lignée suit toute seule. Deux gardes structurelles joueront d'office pour l'eau : le test qui force tout producteur d'`outputs/` à être appelé par le cron, et le job `verrous` qui éprouvera ses verrous sur données avant fusion. L'archive et la reconstitution sont génériques — une source d'eau glissante serait millésimée sans une ligne de code.

**Ce qui coûtera.** Le sujet air a été construit en RECOPIANT la structure du sujet électricité, pas en la factorisant : `figures_air`/`figures`, `note_air`/`note_elec` (leurs blocs `<style>` de 18 lignes sont identiques octet pour octet — mesuré), `page_air`/`compile_etude` (deux assembleurs de philosophies différentes, iframes contre blocs). Un sujet eau au même modèle ajouterait un troisième exemplaire de chaque, et toute correction transversale (cf. C-01 : une phrase corrigée dans la page, oubliée dans la note) devrait se faire en trois points. S'y ajoutent : `_plan_construction` à six booléens positionnels (`prepare.py:1385`) qui en appellerait huit ; `prepare.py` à 1 557 lignes où les fonctions de l'eau s'empileraient ; et les dates de figures composites (C-04) qui se poseront immédiatement pour l'eau (piézométrie + pluie + débits).

**Le geste utile avant l'eau, si un seul devait être fait :** extraire un gabarit commun de note méthodologique (structure HTML + style + le couple `_chiffres()`/`_html()`) et un gabarit de page assemblée sur le modèle de `page_air`. C'est le lot 4 de l'audit du 05/08, devenu la condition du troisième sujet.

## Ce que cet audit n'a pas fait

- Aucun test navigateur (clavier, contraste rendu, mobile) — même limite que le 05/08.
- Aucun téléchargement ni rafraîchissement : les données locales datent du 19/08, ce qui a été retourné en mesure (C-03, C-06) plutôt qu'en verdict sur master.
- Les 31 échecs pytest ont été échantillonnés (2 examinés en détail), pas dépouillés un par un : la cause commune (colonne `annee_locale` absente du Parquet du 19/08) est établie, une cause minoritaire distincte n'est pas exclue.
- Pas de scan de vulnérabilités des dépendances ; `docs/etude.md` et les contenus hors périmètre n'ont été lus que là où un test les référence.

## Conclusion

Le dépôt a tenu ses promesses les plus difficiles — la CI éprouve désormais ce qu'elle affirme, l'archive est née testée — et ses défauts d'aujourd'hui sont d'une autre nature qu'au 05/08 : ce ne sont plus des mécanismes manquants, ce sont des **propagations inachevées** (C-01, C-05, C-12) et des **filets annoncés que rien n'exerce** (C-02, C-03, C-07). La prochaine marche n'est pas un chantier : c'est de finir les corrections du 23 et du 29/08 partout où leurs phrases vivent, puis de donner à l'index des millésimes le même niveau de paranoïa que le dépôt a déjà offert à ses secrets et à ses titres.
