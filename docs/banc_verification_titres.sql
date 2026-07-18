-- ============================================================================
--  BANC DE VÉRIFICATION DES 4 TITRES — mix électrique corse
--  Méthodes & Révélations · démonstrateur-data-corsica
-- ----------------------------------------------------------------------------
--  Objet : pour CHAQUE titre-affirmation du BRIEF, sortir le chiffre décisif.
--          À EXÉCUTER AVANT tout visuel. Aucun Plotly tant que les 4 ne passent pas.
--  Lancer depuis la racine du repo :
--      duckdb < docs/banc_verification_titres.sql
--  (ou :  python -c "import duckdb;duckdb.connect().execute(open('docs/banc_verification_titres.sql').read())")
--
--  Réaligné sur le wording réel de BRIEF.md et corrigé de deux pièges attrapés
--  au premier passage :
--   * NULL micro_hydraulique 2024  -> coalesce(,0) sur TOUTE somme de filières,
--     sinon l'ENR passe sous le solaire. Contrôle de cohérence ENR>=solaire ci-dessous.
--   * ligne aberrante temps réel (total corrompu à 11:00 UTC) -> filtrée par le
--     BOUCLAGE (>50 MW), robuste au fuseau, plutôt qu'un timestamp en dur.
-- ============================================================================

-- Définitions (rappel) :
--   ENR symétrique (comparaison période-à-période, IDENTIQUE des 2 côtés, stockage exclu) :
--     PV + éolien + bioénergies + micro-hydraulique
--   ENR "live EDF" (accroche titre 1) : colonne part_enr_distrib (netting stockage inclus)
--   total / production_totale_mw = OFFRE totale (imports inclus) — cf. sanity 0.b

CREATE OR REPLACE VIEW tr AS
SELECT *, timezone('Europe/Paris', "date") AS loc
FROM read_csv_auto('data/raw/edf_mix_temps_reel.csv', delim=';', header=true)
WHERE abs(total-(filiere_thermique+filiere_enr_distrib+hydraulique+liaisons)) <= 50;  -- drop glitch

CREATE OR REPLACE VIEW hist AS
SELECT *, timezone('Europe/Paris', date_heure) AS loc
FROM read_csv_auto('data/raw/edf_courbe_charge_horaire.csv', delim=';', header=true)
WHERE territoire = 'Corse' AND production_totale_mw > 0;

-- ÉTAPE 0 — PRÉ-VOL -----------------------------------------------------------
-- 0.a  Les colonnes numériques doivent être DOUBLE (piège délimiteur ';' + décimale ',').
DESCRIBE SELECT * FROM tr;
-- 0.b  Somme des parts ~ 100 => total = offre totale (imports inclus) => dénominateur des %.
SELECT round(part_thermique+part_enr_distrib+part_hydraulique+part_liaisons,2) AS somme_parts
FROM tr ORDER BY "date" DESC LIMIT 1;
-- 0.c  COHÉRENCE : ENR distribuée >= solaire seul à CHAQUE heure (0 = OK). Attrape le bug NULL.
SELECT count(*) AS heures_incoherentes FROM (
  SELECT hour(loc) h,
         sum(coalesce(photovoltaique_mw,0)+coalesce(eolien_mw,0)+coalesce(bioenergies_mw,0)+coalesce(micro_hydraulique_mw,0)) enr,
         sum(coalesce(photovoltaique_mw,0)) sol
  FROM hist GROUP BY 1) WHERE enr < sol;

-- TITRE 1 — « en ce moment, votre kWh est fait de X % de soleil » (dernier relevé) --------
SELECT strftime(loc,'%Y-%m-%d %H:%M') AS instant_local, statut, total AS mw,
       round(100.0*photovoltaique/total,1)                                  AS pct_soleil,
       round(part_enr_distrib,1)                                            AS enr_live_edf,
       round(100.0*(photovoltaique+eolien+bioenergies+micro_hydro)/total,1) AS enr_sym
FROM tr ORDER BY "date" DESC LIMIT 1;
-- 1.bis  borne de l'écart déf-EDF (avec stockage) vs symétrique (sans) — non nul, borné.
SELECT round(avg(part_enr_distrib-100.0*(photovoltaique+eolien+bioenergies+micro_hydro)/total),3) AS ecart_moy_pts,
       round(max(abs(part_enr_distrib-100.0*(photovoltaique+eolien+bioenergies+micro_hydro)/total)),3) AS ecart_max_pts
FROM tr;

-- TITRE 2 — « on voit les touristes arriver » (été vs printemps) --------------------------
WITH s AS (
  SELECT CASE WHEN month(loc) IN (12,1,2) THEN '1_hiver' WHEN month(loc) IN (3,4,5) THEN '2_printemps'
              WHEN month(loc) IN (6,7,8) THEN '3_ete' ELSE '4_automne' END AS saison,
         production_totale_mw AS charge, month(loc) AS m
  FROM hist)
SELECT saison, round(avg(charge),1) AS demande_moy_mw,
       round(100.0*(avg(charge) FILTER(WHERE m=7)-avg(charge) FILTER(WHERE m=6))/avg(charge) FILTER(WHERE m=6),1) AS bond_juin_juillet_pct
FROM s GROUP BY saison ORDER BY saison;

-- TITRE 3 — « à midi le soleil culmine ; le soir il retombe, jamais devant le thermique » --
-- (parts par colonne unique : robustes au NULL micro). Fenêtre ÉTÉ, heure locale.
SELECT 'midi_13_15h' AS creneau,
       round(100.0*sum(photovoltaique_mw)/sum(production_totale_mw),1) AS solaire_pct,
       round(100.0*sum(thermique_mw)/sum(production_totale_mw),1)      AS thermique_pct,
       round(100.0*sum(importations_mw)/sum(production_totale_mw),1)   AS imports_pct
FROM hist WHERE month(loc) IN (6,7,8) AND hour(loc) IN (13,14,15)
UNION ALL
SELECT 'soir_20_23h',
       round(100.0*sum(photovoltaique_mw)/sum(production_totale_mw),1),
       round(100.0*sum(thermique_mw)/sum(production_totale_mw),1),
       round(100.0*sum(importations_mw)/sum(production_totale_mw),1)
FROM hist WHERE month(loc) IN (6,7,8) AND hour(loc) IN (20,21,22,23);

-- TITRE 4 — « l'heure la plus verte pour consommer est XXhXX » (argmax horaire, ANNÉE) ----
-- coalesce OBLIGATOIRE (NULL micro 2024). Déf symétrique (A) et avec grande hydro (B).
SELECT hour(loc) AS heure_locale,
       round(100.0*sum(coalesce(photovoltaique_mw,0)+coalesce(eolien_mw,0)+coalesce(bioenergies_mw,0)+coalesce(micro_hydraulique_mw,0))/sum(production_totale_mw),1) AS enr_sym_pct,
       round(100.0*sum(coalesce(photovoltaique_mw,0)+coalesce(eolien_mw,0)+coalesce(bioenergies_mw,0)+coalesce(micro_hydraulique_mw,0)+coalesce(hydraulique_mw,0))/sum(production_totale_mw),1) AS enr_avec_hydro_pct
FROM hist GROUP BY 1 ORDER BY enr_sym_pct DESC LIMIT 3;
