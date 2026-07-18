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

- **NULL micro-hydro 2024** : sommer `pv+eol+bio+micro` SANS `coalesce` jette les 8 783 lignes
  2024 du numérateur → l'ENR passe **sous** le solaire (impossible). Correctif :
  **`coalesce(colonne, 0)` sur toute somme de filières**. Validé par le **bouclage 2024**
  (`total` = somme des filières hors micro à 0,04 MW près) : la micro absente l'est **des deux
  côtés du ratio**, donc les parts ne sont pas biaisées. Contrôle automatique à garder :
  **ENR ≥ solaire à chaque heure** (0 violation après correctif).
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
6. **Étiqueter les périmètres** : le titre 3 (profil) est un récit **estival** ; le titre 4
   (heure verte) est une **conclusion annuelle**. Ne jamais juxtaposer un % d'été et un %
   annuel sans mention — sinon un lecteur voit une incohérence là où il y a deux périmètres.
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
  hydro), **sur l'année**. Périmètre d'affichage = année (étiqueté) — **reco, à confirmer**.

## À banquer pour la vague 2

`cout_moyen_de_production_eur_mwh` (hors périmètre ici) alimenterait un angle
« coût de production corse vs péréquation tarifaire » (CSPE / charges de service public),
raccordable à l'axe loi de finances / CIIC. À garder en réserve.
