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

## Jeu 1 — `edf_mix_temps_reel` (temps réel)

- **Volume** : ~1 344 lignes ; CSV `;` ; ~228 Ko.
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
- **Filières non nulles pour la Corse** : thermique, hydraulique, micro_hydraulique,
  photovoltaique, eolien, bioenergies, importations. **Nulles en Corse** (Outre-mer) :
  bagasse_charbon, geothermie, **stockage**.
- **Profondeur Corse** : horaire, **2019-01-01 00:00 → 2024-12-31 23:00 UTC**, 52 608 h (6 ans).
- **Statut Corse** : `Validé` 17 544 (~2 ans) + `Estimé` 35 064 (~4 ans).
- `cout_moyen_de_production_eur_mwh` : **hors périmètre** (cf. « vague 2 »).

## Définitions VERROUILLÉES (vérifiées, écart nul sauf mention)

Sur le temps réel (écart max mesuré = 0.0000, sauf bouclage) :

- `filiere_thermique = moteur_diesel + tac`
- **`filiere_enr_distrib = photovoltaique + eolien + bioenergies + micro_hydro + solde_stockage`**
  → **hors grande `hydraulique`, hors `liaisons` (imports)**. Le déstockage compte dans l'ENR.
- `part_X = filière_X / total × 100`
- Bouclage `total ≈ thermique + enr_distrib + hydraulique + liaisons` : médiane 0,1 MW
  (arrondis), **mais 6 points aberrants**, dont **2026-07-17 13:00 UTC** (total 348,8 vs
  filières 440, −91 MW). → contrôle qualité obligatoire dans `prepare`.
- **Fuseau = UTC**, prouvé : pic PV à **11 h UTC = 13 h local** (été). Pic de charge
  17 h UTC = 19 h local.

### Correspondance temps réel ↔ historique (pour croiser)

| temps réel            | historique Corse       |
|-----------------------|------------------------|
| `filiere_thermique` (=diesel+tac) | `thermique_mw`   |
| `hydraulique`         | `hydraulique_mw`       |
| `micro_hydro`         | `micro_hydraulique_mw` |
| `photovoltaique`      | `photovoltaique_mw`    |
| `eolien`              | `eolien_mw`            |
| `bioenergies`         | `bioenergies_mw`       |
| `liaisons`            | `importations_mw`      |
| `solde_stockage`      | `stockage_mw` (nul Corse) |
| `total`               | `production_totale_mw` |

**ENR distribuée reproductible sur l'historique** :
`photovoltaique_mw + eolien_mw + bioenergies_mw + micro_hydraulique_mw (+ stockage_mw=0)`
sur `production_totale_mw`. **Ne PAS inclure la grande `hydraulique_mw`**, sinon le chiffre
n'est plus comparable au `part_enr_distrib` du temps réel.

## Garde-fous d'analyse (à respecter avant tout visuel)

1. **Trou 2025 → mi-2026** : l'historique s'arrête au 31/12/2024, le temps réel démarre
   au 04/07/2026 (~18 mois non couverts). **Deux vues distinctes** (profil récent 14 j vs
   moyennes pluriannuelles) — jamais sur un même axe temps.
2. **Définition ENR** = piège n°1 : verrouillée ci-dessus (exclut la grande hydraulique).
   Un titre « X % maintenant vs Y % en moyenne » doit utiliser la MÊME définition des deux côtés.
3. **Stockage** : marginal en temps réel (≤ 5 MW, nul dans ~92 % des pas), nul dans
   l'historique Corse → aucun récit de tendance « stockage ».
4. **Conversion horaire tz-aware** (Europe/Paris : UTC+2 été / UTC+1 hiver). Sur un
   historique couvrant toutes les saisons, un offset fixe décalerait d'1 h la moitié de l'année.
   Le temps réel est bien en UTC (donc « en ce moment » = +2 h en été).
5. **Import permanent observé** : `liaisons` 22→141 MW, **jamais négatif** sur les 14 j d'été
   (aucun export). À reconfirmer sur l'historique avant tout titre sur les échanges.
6. **Crédibilité sur l'historique, pas sur le live** : la partie solide = courbe 6 ans
   (partiellement validée, host stable). La partie fragile = temps réel (portail en
   fermeture, 100 % estimé, 14 j). Traiter « en ce moment » comme accroche ; si la source
   live tombe, dégrader proprement (« dernier relevé daté du… ») car la Corse est une zone
   non interconnectée (EDF SEI) sans repli RTE.

## À banquer pour la vague 2

`cout_moyen_de_production_eur_mwh` (hors périmètre ici) alimenterait un angle
« coût de production corse vs péréquation tarifaire » (CSPE / charges de service public),
raccordable à l'axe loi de finances / CIIC. À garder en réserve.
