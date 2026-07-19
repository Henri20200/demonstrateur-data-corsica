# Reconnaissance des données EDF — rapport validé (18/07/2026)

Rapport de reconnaissance des deux jeux EDF, **validé avant toute analyse**.
Aucun visuel ne doit être construit avant que les garde-fous ci-dessous soient
respectés. Tous les chiffres ont été vérifiés empiriquement (DuckDB sur le brut).

## État du pipeline

- Les 5 sources passent `fetch-data` durci ; `content_type` est écrit dans
  `data/raw/_manifest.json` (traçabilité auto-descriptive).
- **Hosts EDF migrés vers `opendata.edf.fr`** : l'ancien `opendata-corse-outremer.edf.fr`
  est une SPA morte (renvoyait du HTML en 200) ; `opendata-corse.edf.fr` a son
  catalogue déprécié (HTTP 410). Le portail Groupe est le host durable.
- Garde-fou `fetch._valider` : rejette une réponse HTML ou un CSV aux mauvaises
  colonnes → une page d'erreur ne peut plus recevoir un SHA-256 « légitime ».
  Couvert par tests (`tests/test_smoke.py`).

## Licences (récupérées sur la fiche opendata.edf.fr — chemin critique publication)

- **mix temps réel** : « Licence Ouverte / Open Licence version 2.0 » (Etalab).
- **courbe horaire** : « Licence Ouverte (Etalab) » (version non précisée sur la fiche).
- URL : https://www.etalab.gouv.fr/licence-ouverte-open-licence
- → Republication libre **avec attribution du producteur** (ce que `viz.export_html` impose).
  `sources.yaml` mis à jour ; le manifeste captera ces libellés au prochain fetch propre
  (avant mise en ligne de la vitrine).

## Jeu 1 — `edf_mix_temps_reel` (temps réel)

- **Volume** : ~1 344 lignes ; CSV `;` ; ~228 Ko. Toutes colonnes numériques en DOUBLE (0 NULL).
- **Colonnes (19)** : `date`, `date_jour`, `total`, `moteur_diesel`, `tac`,
  `hydraulique`, `micro_hydro`, `photovoltaique`, `eolien`, `bioenergies`,
  `liaisons`, `solde_stockage`, `statut`, `filiere_enr_distrib`,
  `filiere_thermique`, `part_enr_distrib`, `part_thermique`, `part_liaisons`,
  `part_hydraulique`.
- **Granularité** : 15 min. **Profondeur** : fenêtre glissante ~14 jours (pas d'historique).
- **Statut** : 100 % `Estimé`. **Unités** : MW. **Fuseau** : UTC.

## Jeu 2 — `edf_courbe_charge_horaire` (historique)

- **Volume** : 263 040 lignes = `total_count` (export complet, non tronqué) ; CSV `;` ; 24,8 Mo.
- **Colonnes (15)** : `territoire`, `statut`, `date_heure`, `production_totale_mw`,
  `thermique_mw`, `bagasse_charbon_mw`, `hydraulique_mw`, `micro_hydraulique_mw`,
  `photovoltaique_mw`, `eolien_mw`, `bioenergies_mw`, `geothermie_mw`,
  `importations_mw`, `stockage_mw`, `cout_moyen_de_production_eur_mwh`.
- **`territoire` (5 valeurs)** : Corse, Guadeloupe, Guyane, Martinique, Réunion —
  52 608 lignes chacune. **→ FILTRER `territoire = 'Corse'`.**
- **Filières non nulles pour la Corse** : thermique, hydraulique, photovoltaique,
  eolien, bioenergies, importations. **Vides en Corse** (Outre-mer, typées VARCHAR à
  l'import) : bagasse_charbon, geothermie, **stockage** → à caster/ignorer dans `prepare`.
- **`micro_hydraulique_mw` : rupture de série** — présente 2019-2023 (0 NULL), **absente
  en 2024** (NULL sur ~toute l'année). Voir « Données manquantes » ci-dessous.
- **Profondeur Corse** : horaire, **2019-01-01 00:00 → 2024-12-31 23:00 UTC**, 52 608 h (6 ans).
- **Statut Corse** : `Validé` 17 544 (~2 ans) + `Estimé` 35 064 (~4 ans).
- `cout_moyen_de_production_eur_mwh` : **hors périmètre** (cf. « vague 2 »).

## Définitions VERROUILLÉES (vérifiées empiriquement)

Sur le temps réel (écart max mesuré = 0.0000 sauf mention) :

- `filiere_thermique = moteur_diesel + tac`  (écart 0)
- **`filiere_enr_distrib = photovoltaique + eolien + bioenergies + micro_hydro + solde_stockage`**
  (écart 0) → **hors grande `hydraulique`, hors `liaisons` (imports)**. Le déstockage compte
  dans l'ENR (convention EDF).
- `part_X = filière_X / total × 100`  (écart 0). Somme des parts = 100 → `total` = **offre
  totale, imports inclus** (dénominateur des parts confirmé).
- Bouclage `total ≈ thermique + enr_distrib + hydraulique + liaisons` : médiane 0,1 MW
  (arrondis) ; **6 points > 3 MW dont un seul > 10** : **2026-07-17 11:00 UTC (= 13:00 local)**
  où `total` seul est corrompu (348,8 au lieu de ~450 ; filières saines, ni négatif).
  → geste `prepare` : **dropper la ligne via le bouclage > 50 MW** (robuste au fuseau).
- **Fuseau = UTC**, prouvé par la physique : pic PV à **11 h UTC = 13 h local** (été).

### ENR de comparaison « maintenant vs historique » — définition SYMÉTRIQUE

La colonne EDF `filiere_enr_distrib` a **5 termes** (avec stockage) ; l'historique n'a
**pas de stockage** (nul/absent en Corse). « Reproduire » la formule à l'identique donnerait
donc une définition à 4 termes d'un côté, 5 de l'autre → l'écart **n'est pas nul, il est
BORNÉ par le stockage** (mesuré : moy 0,09 pt, **max 1,85 pt** sur la fenêtre 14 j).

Pour tout **différentiel période-à-période**, définition identique des deux côtés, **stockage
exclu** :
`ENR_sym = photovoltaique(_mw) + eolien(_mw) + bioenergies(_mw) + micro_hydro(_mw)`
sur `total` / `production_totale_mw`. **Ne PAS inclure la grande `hydraulique`.**
Le chiffre live « en ce moment » (titre 1) garde `part_enr_distrib` d'EDF (leur convention).

### Correspondance temps réel ↔ historique

| temps réel            | historique Corse       |
|-----------------------|------------------------|
| `filiere_thermique` (=diesel+tac) | `thermique_mw`   |
| `hydraulique`         | `hydraulique_mw`       |
| `micro_hydro`         | `micro_hydraulique_mw` (absente 2024) |
| `photovoltaique`      | `photovoltaique_mw`    |
| `eolien`              | `eolien_mw`            |
| `bioenergies`         | `bioenergies_mw`       |
| `liaisons`            | `importations_mw`      |
| `solde_stockage`      | `stockage_mw` (nul Corse) |
| `total`               | `production_totale_mw` |

## Données manquantes & qualité (garde-fous `prepare`)

- **NULL dans un numérateur = jamais neutre s'il reste au dénominateur.** Sommer
  `pv+eol+bio+micro` SANS `coalesce` jette les 8 783 lignes 2024 (micro-hydro NULL toute
  l'année) du numérateur → l'ENR passe **sous** le solaire, **−5,8 pt à 14h sans lever
  d'erreur** : l'erreur qui *passe*, pas celle qui plante (elle serait partie en démo).
  **Règle `prepare` (pas un `coalesce` aveugle)** :
  1. **auditer les NULL par colonne** avant tout ratio ;
  2. par filière, trancher **zéro-vrai** (filière à l'arrêt = 0 MW → `coalesce(,0)` légitime)
     vs **donnée manquante** (panne de collecte → la ligne ne doit pas peser au dénominateur,
     sinon dilution) ;
  3. ne **jamais** coalescer aveuglément une **grande** filière : si le trou frappait le PV ou
     le thermique, `+0` fabriquerait un faux aplomb à deux chiffres.
  **Cas micro-hydro 2024** : `coalesce(,0)` est correct *ici* car le **bouclage 2024** prouve
  que `production_totale_mw` **exclut aussi** la micro (0,04 MW) — filière absente des deux
  côtés du ratio, donc pas de dilution. Contrôle automatique conservé : **ENR ≥ solaire à
  chaque heure** (0 violation).
  **À écrire sur la vitrine (note méthodo)** : « micro-hydraulique non décomptée en 2024
  (≈8 783 h), traitée comme 0 car exclue aussi du total » — un expert EDF qui connaît
  l'incident est rassuré de le voir écrit ; qu'il le découvre en posant la question coûte la salle.
- **Ligne aberrante temps réel** : cf. bouclage > 50 MW ci-dessus (drop).
- **Signe `solde_stockage`** : positif = décharge (restitution réseau, inclus dans l'ENR
  produite) ; charge (< 0) **non observée** sur la fenêtre 14 j — inférence, pas preuve.

## Garde-fous d'analyse (à respecter avant tout visuel)

1. **Trou 2025 → mi-2026** : historique jusqu'au 31/12/2024, temps réel depuis le 04/07/2026
   (~18 mois non couverts). **Deux vues distinctes**, jamais sur un même axe temps.
2. **Définition ENR** = piège n°1 : définition **symétrique** ci-dessus (exclut la grande
   hydraulique). Même définition des deux côtés pour tout « X % maintenant vs Y % en moyenne ».
3. **Étiqueter la grande hydraulique** : la métrique exclut le gros hydro (Rizzanese…) — le
   dire au mot près (« ENR distribuée, hors grande hydraulique ») et envisager l'affichage
   avec/sans, pour désamorcer l'objection avant qu'elle arrive.
4. **Conversion horaire tz-aware** (Europe/Paris : UTC+2 été / UTC+1 hiver). Le temps réel
   est en UTC (« en ce moment » = +2 h en été).
5. **Échanges** : sur l'historique 6 ans, `importations_mw` **peut être négatif** (min −27 MW,
   **607 h d'export**). « Tire sur l'Italie » vrai **en moyenne**, pas « en permanence » ; le
   temps réel 14 j d'été n'a montré aucun export.
6. **Populations comparables** (règle générale, pas cosmétique) : t3 (profil) est un récit
   **estival** ; t4 (heure verte) est une **conclusion annuelle** — filtre vérifié :
   `territoire='Corse'` sans clause de saison, 2019-2024, 12 mois, 2 192 obs à 14h. Deux %
   qu'un lecteur compare de tête doivent partager la **même population**, sinon la différence
   de population s'écrit **sur la figure**. C'est une **obligation** dès qu'une métrique en
   **contient** une autre (ENR distribuée ⊇ solaire) : sinon « 34 % ENR < 35 % solaire » se
   lit « ils ne savent pas compter », pas « nuance de périmètre ». **Corollaire : ne PAS poser
   t3 et t4 côte à côte** — adjacents, le lecteur soustrait avant de lire les étiquettes.
7. **Crédibilité sur l'historique, pas sur le live** : partie solide = courbe 6 ans (host
   stable, partiellement validée) ; partie fragile = temps réel (portail en fermeture, 100 %
   estimé, 14 j). Zone non interconnectée (EDF SEI) sans repli RTE → si le live tombe,
   dégrader proprement (« dernier relevé daté du… »).

## Verdicts du banc de vérification (test du prompt contre les vrais chiffres)

3 titres sur 4 passent ; **le titre 3 a été recadré** par le banc (le seul qui accrochait).

- **Titre 1 — « en ce moment, X % de soleil »** : ✅ accroche soutenable. Dernier relevé
  (18/07 16:00 local, estimé) = **35,6 % de soleil** (PV) ; ENR-EDF 36,5 %. Cadrage live.
- **Titre 2 — « on voit les touristes »** : ✅ VRAI. Été 265 MW > printemps 245 (**+8,5 %**) ;
  **bond juin→juillet +21,9 %** (231→281). Nuance : charge **bimodale**, hiver = max (307 MW).
- **Titre 3 — profil horaire** : ⚠️ recadré. Formulation retenue : *« À midi le solaire corse
  culmine à 35 % du mix, le soir il retombe à 6 % — mais à aucune heure il ne dépasse le
  thermique. »* (été, 13-15h : solaire 35 % / thermique 43 % ; 20-23h : solaire 6 % /
  thermique 58 %). « Câbles / interconnexions » dans le titre ; **SACOI/Sardaigne** en note.
- **Titre 4 — « l'heure la plus verte = XXhXX »** : ✅ **14h**, robuste (top 3 : 14h/15h/13h ;
  même heure aux deux définitions). ENR distribuée **34,4 %** (déf sym) / 48,1 % (avec grande
  hydro), **sur l'année 2019-2024** (filtre prouvé : aucune clause de saison, 2 192 obs à 14h).
  **Dérivation du chiffre** : à la 1re passe il sortait 28,6 % ; le +5,8 pt vient *entièrement*
  du `coalesce` du bug NULL micro-hydro 2024 — sans lui, 366/2192 obs de 14h (toute l'année
  2024) étaient jetées du numérateur ENR mais gardées au dénominateur. L'heure (14h) et le
  fuseau (local) sont **inchangés** entre les deux passes ; seul le numérateur a été corrigé.

## Addenda du 19/07/2026 (post-audit de fiabilité)

Décisions prises après l'audit du 19/07 (`audit/`), sans refonte analytique :
les résultats tiennent, on durcit fraîcheur, non-régression et formulations.

### Statuts EDF « Validé » / « Estimé » (explication complète — la vitrine n'en porte que la mention courte)

- **Périodes** : `Validé` = 2019-01-01 → 2020-12-31 (17 542 h traitées) ;
  `Estimé` = 2021-2024 (35 063 h, **66,7 %** des heures traitées). Vérifié sur le brut.
- **Mention portée par chaque visuel historique** (pied de figure, via `export_html(note=…)`) :
  « Données EDF estimées à partir de 2021 (2019-2020 validées). »
- **Robustesse directionnelle** (contrôle de l'audit, revérifié) : bond juin→juillet
  **+24,9 %** sur les années validées / **+20,6 %** sur les estimées ; heure la plus verte
  **14 h dans les deux sous-ensembles**. Attention à la lecture : ce découpage est
  **confondu avec la période** (2019-2020 vs 2021-2024, parc ENR en croissance) — il
  démontre que les directions tiennent, il n'isole PAS un effet de la qualité de mesure.

### Volume traité : 52 605 h (et non 52 608)

Le brut Corse compte 52 608 h ; `prepare` retire **3 lignes à 0 MW** (heure fantôme des
passages à l'heure d'été 2019, 2020 et 2024) via `production_totale_mw > 0`. Tout chiffre
« sur 2019-2024 » a donc pour dénominateur **52 605 heures**.

### Fraîcheur & traçabilité (remplace « au prochain fetch propre » de la section Licences)

- `edf_mix_temps_reel` est marqué `glissant: true` → **re-téléchargé à chaque run** ;
  les métadonnées du manifeste (licences…) sont **resynchronisées à chaque run** même
  sans re-téléchargement. Fait le 19/07 : les deux libellés « à confirmer » ont disparu.
- Visuel T1 : **avertissement** au-delà de 24 h ; au-delà de 48 h, le titre
  « en ce moment » est **bloqué** (titre dégradé « au dernier relevé », run en code 1).

## À banquer pour la vague 2

`cout_moyen_de_production_eur_mwh` (hors périmètre ici) alimenterait un angle
« coût de production corse vs péréquation tarifaire » (CSPE / charges de service public),
raccordable à l'axe loi de finances / CIIC. À garder en réserve.
