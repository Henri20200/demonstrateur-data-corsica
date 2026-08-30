# Audit sécurité — demonstrateur-data-corsica

**Date :** 30 août 2026
**Branche / commit :** `master` @ `2ac62b9`
**Périmètre :** chaîne de collecte (`fetch`, `depot`, `archive`, `provenance`), les deux workflows GitHub Actions, `sources.yaml`, la gestion des secrets et l'intégrité de l'archive.
**Contexte :** pipeline de données ouvertes ; cron Actions qui télécharge, publie sur Scaleway et pousse sur `master`. Deux incidents passés : jeton ENTSO-E fuité dans un log CI (07/2026), cache Actions écrasant le manifeste versionné (22/07).
**Modèle de menace retenu :** dépôt **privé** (les PR de fork anonymes ne déclenchent pas les workflows) — le vecteur réaliste n'est donc pas la PR d'un inconnu mais **une dépendance compromise, un compte collaborateur compromis, ou un serveur/MITM sur une source**. Contrôles exécutés localement, aucune correction appliquée.
**Statut au 30/08/2026** : S-02 fermé par #48. Les autres constats restent ceux de l'audit initial, qui n'est pas réécrit — un audit est un instantané daté, pas un backlog.

## Synthèse

La discipline des secrets est parmi les meilleures que j'aie vues sur un dépôt de cette taille : les trois sorties d'un jeton (log, manifeste, réseau) sont tenues par des tests qui échouent bruyamment, l'en-tête inter-hôtes compris. Le SHA-256 est présent partout où une donnée est adoptée, et — point fort structurel — l'empreinte d'identité vit dans Git, si bien qu'une clé de stockage volée ne peut pas falsifier une archive **de façon indétectable**. La séparation PR / cron est correcte : le job de PR est en lecture seule et sans aucun secret.

Ce qui reste tient en une phrase : **les défenses couvrent l'exfiltration ciblée d'un jeton, pas l'exécution de code tiers avec les pleins pouvoirs du cron, ni le déni de service par une source hostile.** Le cron installe ses dépendances en dernières versions (pip, pas `uv.lock`) et s'exécute avec cinq secrets et le droit de pousser `master` ; le parseur XML expanse les entités internes (billion laughs confirmé sur ce poste) ; les téléchargements n'ont pas de plafond de taille.

| Gravité | Nombre |
|---|---:|
| Critique | 0 |
| Élevé | 2 |
| Moyen | 4 |
| Faible | 2 |

---

## Constats

### S-01 — Le cron exécute des dépendances non épinglées avec cinq secrets et le droit de push

**Gravité : élevé — chaîne d'approvisionnement (axe 4)**

**Scénario.** Qui : l'auteur d'un paquet compromis dans l'arbre de dépendances (direct — `pandas`, `duckdb`, `plotly`, `httpx`, `pyyaml` — ou transitif). Avec quoi : `pipeline.yml` installe par `python -m pip install -e . pytest` (`pipeline.yml`, étape « Installer le pipeline ») en **dernières versions**, `pyproject.toml` n'ayant que des bornes basses. Obtient : au prochain cron, du code arbitraire s'exécute dans un job qui porte simultanément `ENTSOE_TOKEN`, `GEODAIR_KEY`, `SCW_ACCESS_KEY/SECRET`, `ARCHIVE_ACCESS_KEY/SECRET` **et** `contents: write` (donc push sur `master`). L'exfiltration des cinq secrets et l'empoisonnement du dépôt sont à sa portée dans le même run. C'est l'impact maximal du dépôt, et il ne demande aucune interaction humaine.

Le choix « pip dernières versions » est **documenté et raisonné** (le job `verrous` doit éprouver les verrous dans l'environnement réel du cron ; `uv.lock` figerait un environnement qui ne prédit rien — cf. l'incident pandas/pytz du 28/08). Il n'est pas remis en cause ici : le problème n'est pas l'absence de lock, c'est l'absence de **borne** sur ce qu'un paquet compromis peut atteindre. Le job `verrous`, lui, tourne aussi en dernières versions mais **sans secret et sans write** — c'est exactement le bon dosage, et il montre que la séparation est possible.

**Verrou.** Réduire la surface plutôt que figer l'environnement : (1) scinder le cron — un job de **collecte** qui porte les jetons de sources (`ENTSOE_TOKEN`, `GEODAIR_KEY`) et **aucune** clé de dépôt, un job de **publication** qui porte `SCW_*`/`ARCHIVE_*` et ne voit jamais les jetons de sources ; aucun paquet ne verrait alors les cinq à la fois. (2) Passer les identifiants Scaleway à des **credentials OIDC courts** (`id-token: write` + rôle) plutôt que des secrets statiques (cf. S-08). (3) `pip install --require-hashes` sur un `requirements.txt` à hashes régénéré périodiquement, distinct de l'environnement de test — coûteux, à peser. Aucun test ne borne ceci : c'est une décision d'architecture de workflow.

### S-02 — Une redirection HTTPS → HTTP sur le même hôte conserve l'en-tête secret

**Gravité : élevé — secrets, sortie réseau (axe 1)**

**Scénario.** Qui : un attaquant en position de MITM sur le chemin d'une source authentifiée par en-tête (Geod'air, `apikey:`), ou un serveur de source compromis. Avec quoi : `_download` ne renvoie l'en-tête que si `httpx.URL(courant).netloc == origine` (`fetch.py:222`) — la comparaison porte sur le **netloc seul, pas sur le schéma**. Une réponse `302` vers `http://<même hôte>/...` reste « même origine » pour ce test. Obtient : le jeton part **en clair sur HTTP**, interceptable passivement. C'est la fuite silencieuse par excellence — aucun message d'erreur, la collecte réussit.

La défense inter-hôtes est, elle, solide et testée (`test_le_jeton_ne_fuit_pas_apres_une_redirection`) ; c'est le **downgrade de schéma sur le même hôte** qui manque, et l'axe le demande explicitement.

**Verrou.** Faire du schéma une composante de l'origine de confiance : dans `_download`, exiger `httpx.URL(courant).scheme == "https"` **et** netloc identique pour porter l'en-tête, et refuser tout downgrade HTTPS→HTTP. Test dans `test_secrets.py` (le client espion existe déjà) : une étape `302` vers `http://api.exemple.fr/...` → l'assertion `vus[1][1] is None`, exactement comme le test inter-hôtes.

### S-03 — Le cloisonnement des clés Scaleway est optionnel, et rien ne l'exige

**Gravité : moyen — secrets, rayon de souffle (axe 1)**

**Scénario.** Qui : quiconque met la main sur `SCW_ACCESS_KEY/SECRET` (via S-01, un log, une mauvaise manip). Avec quoi : `depot.configurer` retombe sur `SCW_*` quand `ARCHIVE_*` n'est pas fourni (`depot.py:325-328`). Les secrets `ARCHIVE_ACCESS_KEY/SECRET` sont **optionnels** (« préférable », dit CLAUDE.md) et vraisemblablement absents en l'état. Obtient : **une seule clé** sert alors la vitrine (`aws s3 sync --delete`, donc droit d'effacer) **et** l'archive, et — selon les droits IAM du token côté Scaleway, que le dépôt ne peut pas voir — potentiellement tous les buckets du projet. Le « cloisonnement » que CLAUDE.md affirme devient une propriété qui n'existe que si le compte a été configuré pour, sans que rien ne le vérifie.

Ce qui EST tenu : `configurer()` refuse `ARCHIVE_BUCKET == BUCKET_VITRINE` (`depot.py:331`, `test_le_bucket_de_la_vitrine_est_refuse`), et la priorité clé-dédiée est testée. Mais ces gardes protègent d'une **erreur de configuration**, pas d'une **clé trop large** : elles ne peuvent pas constater qu'une clé restreinte est effectivement en place.

**Verrou.** Configuration, pas code : créer une clé Scaleway restreinte au seul bucket d'archive et la poser en `ARCHIVE_*` (le garde-fou cesse d'être une condition dans le code pour devenir une propriété du compte, comme la docstring l'appelle de ses vœux). Côté code, un garde-fou de défiance possible : si `ARCHIVE_*` est absent **en CI** (`GITHUB_ACTIONS=true`), émettre un `::warning::` — le dépôt aime déjà rougir les configurations dégradées (disjoncteur de volume, vitrine non déployée).

### S-04 — Le parseur XML expanse les entités internes (billion laughs) → déni de service du runner

**Gravité : moyen — entrées non fiables (axe 3)**

**Scénario.** Qui : un serveur de source XML compromis, ou un MITM (ENTSO-E). Avec quoi : `xml.etree.ElementTree` est utilisé dans `fetch` (`_racine_xml`, `_valider`), `prepare` (`_lignes_entsoe_horaires`, `_points_flux_entsoe`) et `provenance` (`_empreinte_canonique_xml`), sans `defusedxml`. **Vérifié sur ce poste** : ET expanse les entités internes générales (un `<!ENTITY>` en cascade produit l'explosion classique) — un document « billion laughs » de quelques kilo-octets sature la mémoire à la lecture. Obtient : OOM ou blocage du runner jusqu'au timeout de 25 min ; le pipeline échoue, la publication est suspendue (déni de service, pas d'exfiltration).

À dire honnêtement, dans les deux sens : (1) **l'XXE externe est refusé** — même test sur ce poste, une entité `SYSTEM "file:///..."` lève `ParseError: undefined entity` : pas de lecture de fichiers ni de SSRF, expat ne résout pas les entités externes. Le risque se limite donc au DoS. (2) La source est authentifiée en HTTPS, le vecteur réaliste est étroit (serveur compromis ou MITM TLS). Mais l'axe pose précisément « les octets téléchargés sont hostiles », et le premier geste de `_valider` est déjà de parser cet octet-là.

**Verrou.** Remplacer `import xml.etree.ElementTree as ET` par `defusedxml.ElementTree` (ajouté aux dépendances) partout où l'on parse un octet téléchargé — API identique, il refuse les bombes d'entités. Test : un XML billion-laughs miniature passé à `_valider` / `_racine_xml` doit lever proprement (`EntitiesForbidden`), pas consommer la mémoire.

### S-05 — Le nom de fichier d'une source n'est pas validé contre la traversée de chemin

**Gravité : moyen — entrées non fiables (axe 3)**

**Scénario.** Qui : un collaborateur dont le compte est compromis, ou une PR malveillante fusionnée (le dépôt est privé mais multi-contributeur : incident d'attribution GitHub connu). Avec quoi : `dest = DATA_RAW / meta["filename"]` (`fetch.py:485`) construit le chemin d'écriture directement depuis le champ `filename` de `sources.yaml`, sans vérifier qu'il reste sous `DATA_RAW`. Un `filename: "../../.github/workflows/pipeline.yml"` (ou tout chemin relatif remontant) ferait écrire le contenu téléchargé **hors** de `data/raw`. Obtient : écriture arbitraire dans l'arbre du runner au prochain cron — y compris un fichier que le `git add outputs data/raw/_manifest.json` n'attrape pas, mais qu'un attaquant place à un endroit exécuté.

C'est un vecteur de second ordre (il faut d'abord altérer `sources.yaml`, versionné et relu), mais `sources.yaml` est justement une **entrée** au sens de l'axe, et rien dans le code ne pose la barrière.

**Verrou.** Dans `fetch`, résoudre puis vérifier l'appartenance : `dest = (DATA_RAW / meta["filename"]).resolve()` doit être relatif à `DATA_RAW.resolve()`, sinon échec. Test dans `test_smoke` (`test_sources_yaml_est_valide` itère déjà chaque source) : refuser tout `filename` contenant `/`, `\` ou `..`, ou dont la résolution sort de `DATA_RAW`.

### S-06 — L'append-only de l'archive n'est pas garanti par le bucket : une clé volée peut détruire

**Gravité : moyen — intégrité (axe 5)**

**Scénario.** Qui : le porteur d'une clé d'archive volée (via S-01 ou S-03). Avec quoi : le code n'écrit que des PUT de clés neuves (`depot.deposer`), mais « append-only » n'est qu'une **discipline côté client** — rien dans le code (et vraisemblablement rien côté bucket) ne configure un Object Lock / WORM ni le versioning S3. Obtient : avec un droit d'écriture, il peut **écraser** (même clé → réécriture) ou **supprimer** les objets de l'archive, et la clé vitrine peut effacer la vitrine via `--delete`. L'archive patrimoniale — « aucune rétention destructive », dit CLAUDE.md — est détruisible en une commande.

**Le point fort à porter au crédit du dépôt, et il est réel :** la **falsification indétectable** est impossible. Le SHA-256 d'identité vit dans `_versions.json` et `_manifest.json`, tous deux **versionnés dans Git** ; la relecture d'un objet passe par `provenance.empreinte` (`depot.py:166-169` le dit explicitement), qui rejette tout contenu dont l'empreinte ne correspond pas à ce que Git déclare. Un attaquant qui a la clé S3 mais pas Git peut donc **détruire** (disponibilité) mais pas **substituer un faux qui passe pour vrai** (intégrité). C'est exactement la bonne moitié à avoir sécurisée.

**Verrou.** Configuration du compte : activer le **versioning** et/ou l'**Object Lock (mode gouvernance)** sur le bucket d'archive, avec une clé d'écriture qui ne porte pas le droit `DeleteObjectVersion`. C'est hors code — à documenter comme prérequis de déploiement à côté de la règle « bucket distinct de la vitrine ». Le SHA dans Git reste le filet de détection ; le bucket devient le filet de prévention.

### S-07 — Téléchargement sans plafond de taille, et gzip décompressé sans borne

**Gravité : faible — entrées non fiables / DoS (axe 3)**

**Scénario.** Qui : un serveur de source compromis. Avec quoi : `_download` écrit `r.iter_bytes()` sans limite d'octets (`fetch.py:234-236`) — une réponse en flux quasi-infini remplit le disque du runner ; et DuckDB lit les `.csv.gz` directement (`prepare`), une bombe gzip (petit fichier → téraoctets) faisant tourner la requête jusqu'au timeout. Obtient : épuisement disque ou temps → échec du run (déni de service, borné à 25 min par le timeout du job).

**Verrou.** Un plafond d'octets dans `_download` (par ex. couper et échouer au-delà d'un seuil par source, déclaré dans `sources.yaml` ou global), qui protège aussi de la bombe gzip en amont de DuckDB. Le timeout de job limite déjà le rayon ; le plafond rend l'échec propre et immédiat plutôt que lent.

### S-08 — Secrets statiques long-vécus, sans OIDC ni protection d'environnement sur le job qui push master

**Gravité : faible — durcissement (axes 1, 2)**

**Scénario.** Les identifiants Scaleway sont des secrets statiques (`secrets.SCW_*`, `ARCHIVE_*`) sans rotation automatique ; le workflow ne demande jamais `id-token` (pas d'OIDC). Le job qui pousse `master` et déploie n'est pas rattaché à un `environment:` GitHub (donc pas de règle de protection, pas de reviewers requis, pas de restriction de branche au niveau environnement). Conséquence : une fuite (S-01/S-03) donne un accès qui dure jusqu'à rotation manuelle, et aucune barrière GitHub ne s'interpose entre l'exécution et le push/déploiement.

**Verrou.** Configuration : credentials OIDC courts pour Scaleway si le fournisseur le permet (sinon rotation périodique documentée) ; rattacher le job de publication à un `environment:` avec restriction à `master`. Aucun test ne couvre ceci — c'est de la configuration de dépôt.

---

## Axes examinés et sains (une ligne chacun)

- **Séparation PR / cron (axe 2) :** `validation.yml` se déclenche sur `pull_request` (pas `pull_request_target`), en `contents: read` et **sans aucun secret custom** ; `pipeline.yml` ne se déclenche que sur `schedule`/`workflow_dispatch` — une PR ne voit donc jamais un jeton ni n'obtient de droit d'écriture. **Correct.**
- **Injection dans les `run:` (axe 2) :** aucune interpolation `${{ }}` non fiable n'entre dans un `run:` — seules des valeurs contrôlées par GitHub (`steps.*.outcome`, `github.base_ref` d'un dépôt privé) et des `hashFiles()` y figurent. **Sain.**
- **Les trois sorties d'un secret (axe 1) :** log, manifeste et réseau — en-têtes `entetes:` compris et redirection **inter-hôtes** comprise — sont tenus par `tests/test_secrets.py` avec un client espion. **Solide** (seul le downgrade de schéma manque, cf. S-02).
- **XXE externe (axe 3) :** vérifié sur ce poste — expat ne résout pas les entités externes `SYSTEM`, donc pas de lecture de fichiers ni de SSRF via XML (le résiduel est le DoS, S-04).
- **SHA-256 partout où une donnée est adoptée (axe 5) :** `fetch` certifie puis re-vérifie à chaque run, `prepare` refuse un brut non certifié, `verifier_sorties` re-contrôle avant publication, le PUT S3 signe `x-amz-content-sha256`. **Complet.**
- **Hygiène du dépôt :** `.env*` gitignorés (leçon d'un incident), contenu de `data/` non versionné, seuls `_manifest.json` et `_versions.json` suivis — aucun secret ni octet brut ne part sur GitHub.

## Priorisation

1. **S-01** (scinder les secrets du cron) et **S-02** (schéma dans l'origine de confiance) d'abord : le premier borne l'impact maximal, le second ferme une fuite silencieuse à correction triviale et testable.
2. **S-03**, **S-06**, **S-08** ensemble : ce sont trois facettes d'une même décision — poser des clés Scaleway étroites, versionnées/verrouillées côté bucket, courtes si possible. Configuration de compte, pas de code.
3. **S-04** (`defusedxml`) et **S-05** (garde de chemin) : deux correctifs de code ciblés, chacun avec son test, contre les octets hostiles de l'axe 3.
4. **S-07** : plafond de taille, quand le durcissement réseau de S-02 sera fait (même fonction).

## Ce que cet audit n'a pas fait

- Aucun scan de vulnérabilités (CVE/SCA) de l'arbre de dépendances réel — S-01 est raisonné sur le mécanisme, pas sur un paquet nommé.
- Aucune vérification des **droits IAM réels** des clés Scaleway ni de la configuration du bucket (Object Lock, versioning) : hors de portée du code, ce sont des propriétés du compte — d'où S-03/S-06/S-08 formulés comme prérequis à vérifier côté Scaleway/GitHub.
- Pas de test dynamique contre un vrai serveur hostile : billion laughs et XXE ont été reproduits en local sur `xml.etree`, le reste est établi par lecture.
