# Inventaire des conventions

Relevé du 7 octobre 2026. Ce document recense les conventions dont dépendent les chiffres
publiés, jeu de données par jeu de données, et dit pour chacune ce qui la fonde.

Il fait suite à la correction des heures de l'air du 6 octobre 2026. Deux conventions posées
le 1er août, sans repère extérieur, avaient décalé d'une heure les heures publiées pendant
deux mois. La règle selon laquelle une vérification n'aboutit que si une contrainte
extérieure au système confirme l'interprétation date du 22 août 2026 ; elle n'avait pas été
appliquée après coup aux conventions plus anciennes.

Ce relevé est une lecture : rien n'a été recalculé ni revérifié pour l'établir. Les
confirmations déjà acquises sont reprises avec la portée que leur donnent les documents qui
les rapportent. Les décisions viennent ensuite, au tri.

C'est un **relevé partiel** : ce qui n'a pas été examiné est listé au § 8, et le tri
commencé le 7 octobre 2026 est consigné au § 10.

## Comment lire ce document

Chaque ligne relève de l'une de trois natures.

- **Convention de source** : la façon de lire ce que publie un producteur — fuseau horaire,
  début ou fin d'intervalle, unité, codes de qualité, périmètre d'un fichier. Elle reçoit
  l'un de trois statuts :
  - **vérifiée** : une référence extérieure au dépôt la confirme. La ligne dit ce que cette
    référence confirme, pour quel jeu et sur quelle période ;
  - **documentée** : seul un document du producteur la fonde ;
  - **non vérifiée** : aucun fondement n'a été retrouvé dans les éléments examinés. Ce
    statut ne dit pas que le résultat est faux.
- **Choix d'analyse** : une décision du projet (fenêtre, seuil de plateau, arrondi,
  appariement). Elle est présentée comme un choix. La ligne dit si elle est motivée par
  écrit et si sa sensibilité a été mesurée. Une référence qui fait le même choix ne suffit
  pas à en établir la pertinence ici.
- **Affirmation sur la méthode** : ce que nos pages disent de nos propres contrôles. Un
  document de producteur ne peut pas la fonder. Seule une preuve d'audit le peut : la
  correspondance entre l'affirmation et ce que le code et les tests font réellement.

Pour une définition de colonne (« la part est la filière divisée par le total »), une
identité exacte vérifiée sur les fichiers du producteur est retenue comme référence
extérieure : elle ne dépend pas de notre code. Elle ne confirme jamais un fuseau ni un
niveau. Cette règle est une proposition de ce relevé, à valider au tri.

La colonne « Test » dit ce qui tient la convention dans la suite automatique : une valeur
exacte, un intervalle, ou rien. Un test écrit à partir du même code fixe une convention ; il
ne la prouve pas.

La colonne « Porteurs » donne les figures et les textes qui en dépendent. Une ligne sans
porteur publié n'appelle pas de décision au tri.

Les codes de figure (A1 à A5 pour l'air, T1 à T10 pour l'électricité) sont ceux du code ;
ils n'apparaissent pas aux lecteurs, qui reconnaissent les figures à leur titre.

## Périmètre examiné

Examinés le 7 octobre 2026 :

- `src/demonstrateur/prepare.py`, en entier ;
- `src/demonstrateur/figures_air.py` et `src/demonstrateur/figures.py` : constantes,
  requêtes, seuils et gardes, sans relire chaque ligne de mise en forme ; T6b et T7 en
  détail ;
- les passages de méthode de `note_air.py`, `note_elec.py`, `accueil.py` et de
  `docs/etude.md` (§ 5 et 6), repérés par recherche ; le glossaire de `page_air.py` ;
- `docs/RECONNAISSANCE.md` ; `docs/VERIF_ENTSOE_TERNA.md`, § 1, 2, 6, 7 et 8 ;
  `docs/AUDIT_SAISONNIER.md`, section « Périmètre et conventions » ; `docs/BRIEF_AIR.md`,
  passages sur les fuseaux (lignes 145-156 et 252-269) ;
- les commentaires de `sources.yaml` pour l'air, la météo, les stations, la charge sarde,
  SAPEI et SARCO ;
- les noms et les assertions des tests ; `tests/test_horodatage_corse.py` lu en partie.

Les dates de pose viennent de `git log -S` sur `src/`. Ce qui n'a pas été examiné est
listé au § 8.

## 1. Air — conventions de source

| N° | Jeu | Convention | Code et date de pose | Document du producteur | Référence extérieure : ce qu'elle confirme | Test | Porteurs | Statut |
|---|---|---|---|---|---|---|---|---|
| A-1 | AEE, jeu validé E1a (`aee_*_valide`, 2013 au 01/01/2026) | `Start` marque le début de l'heure, en UTC+1 fixe ; une heure est retirée pour obtenir l'UTC | `prepare.py:906` ; posée le 01/08 (`8716fe1`), corrigée le 06/10 (`f002e21`) | Guide de téléchargement de l'AEE, p. 18 ; aide Parquet du service | Aucune pour ce jeu. Le repère du 06/10 porte sur le flux LCSQA (A-7). L'accord des valeurs AEE et LCSQA (A-2) ne couvre que des journées de 2026, toutes dans le jeu continu | `test_horodatage_air.py` : conversion sur des dates explicites, qui fixe la convention. `test_le_pic_d_ozone_suit_celui_du_no2` : 8 h et 16 h exacts, qui fixe le résultat | A1 à A5, page air, note air : les étés 2020-2025 viennent tous de ce jeu | documentée |
| A-2 | AEE, jeu continu E2a (`aee_*_continu`, 2026) | Même convention que A-1 | `prepare.py:906` ; mêmes dates | Mêmes documents | Indirecte : les valeurs AEE converties coïncident heure par heure avec celles du flux LCSQA, dont l'UTC est confirmé (A-7). Portée : la journée du flux présente à chaque exécution | `test_la_serie_aee_et_le_flux_lcsqa_coincident` : écart nul | Encart d'actualité 2026 (page, note) | vérifiée |
| A-3 | AEE, E1a et E2a | Mesures gardées : `Validity > 0` et valeur non nulle | `prepare.py:924` ; 01/08 (`8716fe1`) | Signification des codes `Validity` non citée dans les éléments examinés | — | Aucun sur l'AEE ; `test_air_corse_ne_garde_que_des_mesures_valides` porte sur le flux LCSQA | A1 à A5, note | non vérifiée |
| A-4 | AEE, E1a et E2a | Statut « vérifié » : `Verification = 1` ; 2 = préliminaire, 3 = non vérifié | `prepare.py:909` ; `sources.yaml:594` ; 01/08 | Signification énoncée dans `sources.yaml`, sans document du producteur cité | — | Aucun | Note air : nombre de mesures « vérifiées » et borne du « vérifié » | non vérifiée |
| A-5 | Référentiel des stations (`STATIONS_AIR`) | Implantation et influence de chaque station ; périmètre de six stations d'ozone | `prepare.py:806` ; 01/08 (`c51b69e`) | Référentiel LCSQA « Dataset D », relevé le 01/08/2026 | Référentiel Geod'air du producteur (`geodair_stations`) : confirme que la recopie est fidèle (mise en service, implantation, altitude, coordonnées), au jour de chaque exécution. Influence contrôlée contre le dernier flux LCSQA. L'historique d'influence n'est pas publié par le producteur | `test_stations_air.py` : 9 tests, valeurs exactes | A1, A4 (libellés, « seule station rurale »), note (profondeur des stations, Confina 2 depuis 2024) | vérifiée |
| A-6 | Flux LCSQA (`lcsqa_temps_reel`) | Périmètre `Organisme = 'QUALITAIR CORSE'` ; mesures gardées si `validité > 0` | `prepare.py:720` et `:750` ; 31/07 (`f179666`) | Codes de validité non cités. Audit du brut du 30/07 : les 18 lignes à −1 sont toutes vides | — | `test_air_corse_ne_garde_que_des_mesures_valides` | Aucun chiffre publié. Porteur indirect : le contrôle croisé qui confirme A-2 compare les valeurs AEE à celles que ce filtre garde | non vérifiée |
| A-7 | Flux LCSQA | « Date de début » = début de l'heure, en UTC | `prepare.py:734` ; 31/07 (`f179666`), corrigée le 06/10 (`f002e21`) | Note LCSQA DRC-18-174316-08157A, p. 6 | Fichier du jour du 06/10/2026, écrit à 10:30 UTC : l'outre-mer, publié en heure locale à décalage fixe, et la métropole s'arrêtent tous à 09:00 UTC si la métropole est en UTC. Portée : ce fichier, ce jour. Le repère ne se rejoue pas : un fichier complet couvre la journée locale de chaque organisme | `test_le_flux_lcsqa_est_deja_en_utc` : régularité de la grille, qui ne distingue pas UTC d'UTC+1 (sa docstring le dit) ; `test_horodatage_air.py` | Aucun chiffre publié ; confirme A-2 | vérifiée |
| A-8 | Météo-France, les deux fichiers (`meteo_horaire_corse_2020_2024`, `meteo_horaire_corse`) | `AAAAMMJJHH` en UTC | `prepare.py:1247` ; 01/08 (`5ec249e`) | Non cité pour le fuseau | Pyranomètres (`GLO`) des trois postes corses, lus en UTC avec le cumul daté en fin d'heure : ils tombent sur le midi solaire, calculé par astronomie, à 0,13 h près sur les douze mois (mesure du 23/08/2026). Portée : les deux fichiers réunis, 2020-2026, colonne `GLO` ; la température partage la même colonne de date | `test_v4_le_pyranometre_tombe_sur_le_midi_solaire` : tolérance de 0,25 h par mois | A2, croisement ozone × température | vérifiée |
| A-9 | Météo-France | Codes qualité : `QT` 0, 1 et 9 gardés, 2 écarté, code inconnu = arrêt | `prepare.py:68-69` ; 01/08 (`5ec249e`) | `H_descriptif_champs.csv`, relevé le 01/08/2026 | — | `test_meteo_corse_ne_garde_que_des_mesures_fiables` | A2 ; note air (« heures douteuses écartées ») | documentée |
| A-10 | Météo-France | `T` est la température sous abri instantanée, en °C | `sources.yaml:512-513` | Énoncé dans `sources.yaml`, sans document cité | — | `test_meteo_corse_cycle_diurne_physique` : heure la plus chaude entre 13 h et 18 h, la plus froide entre 3 h et 8 h (intervalles) | A2 | non vérifiée |
| A-11 | Calcul de la moyenne sur 8 h de l'ozone | Moyenne des heures valides parmi l'heure h et les sept précédentes, divisée par leur nombre, valide à partir de 6 ; maximum journalier valide à partir de 18 moyennes ; grille horaire complète ; fenêtre mesurée en temps et non en lignes | `prepare.py:974-1051` ; 01/08 (`81fca88`) | Guide LCSQA/Ineris « Calcul des statistiques relatives à la qualité de l'air », Ineris-219621-2801775-v1.0 (mars 2024), § 5.3.3 et 5.3.4 | Tableau 26 du guide, exemple chiffré, rejoué à l'identique. Portée : l'arithmétique de la journée, pas le fuseau de la journée (A-12) | `test_ozone_8h.py` : valeurs exactes du tableau 26 | A1, A2, A4, note (journées valides) | vérifiée |
| A-12 | Calcul de la moyenne sur 8 h | Jour de rattachement : la moyenne dont la dernière heure, étiquetée au début, est d revient au jour LOCAL de d, en heure légale (UTC+2 l'été) | `prepare.py:997-1030` ; 01/08 (`81fca88`) | Le guide date ses heures en fin de période (01 h → 24 h). Le fuseau dans lequel il découpe la journée n'est pas précisé dans les éléments examinés. `BRIEF_AIR.md:253-255` fait du jour local un choix : « c'est la journée vécue qui a un sens » | Le tableau 26 confirme l'ordre des heures dans la journée, pas son fuseau. Que nos décomptes de dépassements suivent le découpage réglementaire n'est pas établi | `test_ozone_8h.py`, sur des heures sans fuseau | A1, A2, A4, note | non vérifiée |
| A-13 | Seuils réglementaires | 120 µg/m³ sur le maximum journalier de la moyenne 8 h (objectif de qualité) ; 180 µg/m³ en moyenne horaire (seuil d'information) | `figures_air.py:46-47` ; 01/08 (`f0c05c7`) | Article R221-1 du code de l'environnement, vérifié le 01/08/2026 | — | `test_les_deux_seuils_ne_se_confondent_pas` ; `test_le_titre_d_a1_ne_confond_pas_information_et_alerte` | A1, A4, note, glossaire de la page | documentée |
| A-14 | Seuils réglementaires | Un dépassement de l'objectif exige un maximum strictement supérieur à 120 | `figures_air.py:514` ; 01/08 (`f0c05c7`) | Énoncé par la note (`note_air.py:234`), source non citée dans les éléments examinés | — | Aucun sur le caractère strict | A1, A4, note | non vérifiée |

## 2. Air — choix d'analyse

| N° | Choix | Code et date de pose | Motivation écrite | Sensibilité mesurée | Test | Porteurs |
|---|---|---|---|---|---|---|
| AC-1 | Fenêtre : étés 2020 à 2025, de juin à août | `figures_air.py:49` et `:55` ; juin-août le 01/08 (`f0c05c7`), bornes écrites une fois le 31/08 (`f87f1b2`) | Fenêtre figée et encart d'actualité à part : décision C-09 (`docs/AUDIT_REPO_2026-08-30.md`). « Été = juin à août » n'est pas motivé dans les éléments examinés | Non | `test_couverture_air.py` (couverture de la fenêtre) | A1 à A5, page, note |
| AC-2 | Périmètre « de fond » : influence `Fond` seulement, ce qui écarte Bastia La Marana | `figures_air.py:60`, `:72`, `:199` ; 01/08 (`f0c05c7`) | Oui : comparer des populations comparables (`note_air.py`, BRIEF_AIR) | Non | L'influence de chaque station est contrôlée (A-5) ; le filtre lui-même n'a pas de test retrouvé | A1 à A5 |
| AC-3 | A1 sans Ajaccio Confina 2, ouverte en 2024 | `figures_air.py:71-73` ; 24/08 (`544e6f6`) | Oui : 180 journées contre 520 à 544, la longueur de barre classait deux stations à l'envers | Le total de journées distinctes ne change pas (testé) | `test_a1_ecarte_la_station_recente_sans_perdre_une_journee` | A1, note |
| AC-4 | A3 : stations où les deux polluants sont mesurés, sans Venaco ; profil = moyenne de toutes les heures valides, stations confondues | `figures_air.py:60` et `:795-797` ; 01/08 | Périmètre motivé. La pondération par nombre de mesures (une station plus complète pèse plus) n'est pas motivée | Mesure du 06/10/2026, faite hors de la chaîne et rejouée par aucun test : moyenne et médiane culminent à 8 h ; heure du maximum matinal par journée-station : 8 h dans 34,5 % des cas, entre 7 h et 9 h dans 72 % | `test_le_pic_d_ozone_suit_celui_du_no2` : 8 h et 16 h exacts | A3, page, note de correction |
| AC-5 | A5 : créneau le plus chargé = heures à au moins 95 % du maximum du profil moyen | `figures_air.py:920` ; 01/08 (`f0c05c7`) | Non retrouvée. T2b, côté électricité, prend 97 % | Non | `test_le_pire_creneau_estival_est_l_apres_midi` : 12 h et 19 h exacts | A5 (titre), page, note de correction |
| AC-6 | A2 : tranches de température maximale du jour (< 25, 25-30, 30-35, ≥ 35 °C) ; moyenne des maxima d'ozone par couple station-jour | `figures_air.py:698-704` ; 01/08 (`f0c05c7`) | Pondération motivée (le libellé compte des relevés, pas des jours). Bornes des tranches non motivées | Non | `test_l_ozone_monte_avec_la_chaleur_mais_plafonne` : ordre des tranches | A2 (titre « jusqu'à 35 °C »), page |
| AC-7 | A2 : la complétude de la température n'est pas exigée poste par poste. `n_heures_temp` est produite mais pas utilisée ; la garde météo des journées incomplètes compte les heures tous postes confondus | `prepare.py:1137-1153` et `:1329-1331` | `prepare.py:1120-1121` renvoie ce choix à la figure, qui ne le fait pas | Non | Aucun | A2 |
| AC-8 | Appariement de chaque station au poste météo jugé le plus semblable (Vivario et non Corte pour Venaco) | `prepare.py:836-850` ; 01/08 (`2089e9a`) | Oui, en détail (`prepare.py:823-849`) : exposition, cuvette de Corte, amplitudes mesurées | Écarts entre postes mesurés (Ajaccio 2,6 °C, Corte-Vivario 3,4 °C sur les maxima) | Tests d'appariement, valeurs exactes | A2, note |
| AC-9 | A4 : taux = dépassements ÷ journées valides, par station, sur des périodes différentes (Confina 2 : 2024-2025) | `figures_air.py:191-199` | Oui : périmètre et étés affichés sur la figure | Non | `test_effectifs_ozone.py` | A4, page, note |
| AC-10 | Seuil d'information « atteint » = moyenne horaire ≥ 180 (et non > 180) | `figures_air.py:504` | Implicite : la comparaison large rend plus exigeant le contrôle de l'affirmation « jamais atteint » | Sans objet | Garde de figure (arrêt) | A1, note |
| AC-11 | Arrondis : pourcentages à l'entier ; µg/m³ à l'entier dans les titres et étiquettes | `figures_air.py:265-268`, `:726`, `:867` | Oui pour les pourcentages (même précision que l'étiquette de barre) | Sans objet | — | A2, A4, A5, page, note de correction |
| AC-12 | Encart d'actualité : journées calendaires où au moins une station de fond dépasse l'objectif | `figures_air.py:279-315` | Oui (`figures_air.py:290-293`) | Sans objet | — | Page, note |

## 3. Électricité — conventions de source

| N° | Jeu | Convention | Code et date de pose | Document du producteur | Référence extérieure : ce qu'elle confirme | Test | Porteurs | Statut |
|---|---|---|---|---|---|---|---|---|
| E-1 | EDF temps réel (`edf_mix_temps_reel`) | `date` en UTC | `prepare.py:148` ; 19/07 (`ad58ad1`) | — | Le soleil : pic photovoltaïque brut à 11 h 30, midi solaire à 11 h 28 UTC (`RECONNAISSANCE.md`). Portée : ce jeu, fenêtre de 14 jours de juillet 2026 | Aucun retrouvé | T1 (heure du relevé), accueil | vérifiée |
| E-2 | EDF temps réel | Thermique = diesel + TAC ; ENR distribuée d'EDF = PV + éolien + bioénergies + micro-hydraulique + déstockage ; part = filière ÷ total ; total = offre totale, imports compris | `RECONNAISSANCE.md`, « Définitions verrouillées » ; 18/07 | — | Identités exactes sur le brut (écart nul) | Aucun retrouvé | T1 | vérifiée |
| E-3 | EDF courbe horaire (`edf_courbe_charge_horaire`) | L'étiquette `+00:00` est fausse : le jeu porte l'heure légale corse ; les six heures qui n'existent pas en heure légale sont retirées | `prepare.py:211-260` ; 23/08 | — | Trois repères indépendants (`VERIF_ENTSOE_TERNA.md` § 5) : pyranomètre `GLO` de Météo-France ; comportement aux dix bascules d'heure 2020-2024 ; les trois seules lignes à production nulle tombent à 02 h des dimanches de printemps. Plus le midi solaire astronomique. Portée : 2019-2024 | `test_horodatage_corse.py` : V1 à V4 | T2b, T3, T4, T8, T10, étude, note | vérifiée |
| E-4 | EDF courbe horaire | Valeurs en MW moyens sur l'heure, nettes des auxiliaires ; une somme d'heures donne des MWh | `VERIF_ENTSOE_TERNA.md` § 2 | — | Indice interne seulement : le photovoltaïque est négatif la nuit (20 426 h). Aucune confrontation des niveaux (§ 8) | Aucun | Toutes les parts et sommes de l'électricité | non vérifiée |
| E-5 | EDF courbe horaire | Niveaux annuels par filière, dont 66,7 % des heures au statut « estimé » (2021-2024) | — | Statut « validé » / « estimé » publié par EDF | Partielle (`VERIF_ENTSOE_TERNA.md` § 8) : la forme horaire du photovoltaïque suit le rayonnement mesuré (r = 0,963 l'été) ; le thermique ne montre pas de rupture face aux émissions vérifiées (§ 10). Les niveaux absolus n'ont aucune validation indépendante | `test_seqe_thermique.py`, `test_sarco.py` | T2, T6, T7, T9, étude, note | non vérifiée — limite déjà publiée |
| E-6 | EDF courbe horaire | Micro-hydraulique absente en 2024, comptée 0 | `prepare.py:244` ; 19/07 (`ad58ad1`) | — | Bouclage 2024 sur le brut : le total publié l'exclut aussi | Garde « ENR ≥ solaire » dans `prepare` | T4, étude (« La petite hydraulique manque dans les données 2024 ») | vérifiée |
| E-7 | EDF écrêtement (`edf_ecretement_corse`) | « Durée (h) » = durée maximale de limitation subie par un producteur, et non énergie perdue ; taux absent avant 2019 | `prepare.py:297-337` ; 20/07 | Sens de la colonne énoncé dans `RECONNAISSANCE.md` sans document cité | — | Tests T5 sur les valeurs | T5, étude | non vérifiée |
| E-8a | ENTSO-E, génération sarde (A75) | Valeur = MW moyen net sur le pas de marché ; la somme des heures donne des MWh nets | `prepare.py:340-412` ; 20/07 (`c26b26a`) | ENTSO-E, *Detailed Data Descriptions* v3r4, art. 16.1.b | Bilan régional de Terna : total à +1,31 % (2023) et +0,61 % (2024) de la production nette, contre −4 % de la brute. Confirme la convention « net » et la sommation, sur les totaux annuels. Portée : 2023 et 2024 ; 2019 à 2022 non confrontés | Tests T6 | T6, T6b, étude | vérifiée |
| E-8b | ENTSO-E, génération sarde (A75) | Report `A03` : une position non déclarée reconduit la dernière valeur connue, jusqu'à la fin de la période | `prepare.py:390-407` ; 20/07 (`c26b26a`) | Règle énoncée dans `RECONNAISSANCE.md` et `VERIF_ENTSOE_TERNA.md` § 6.1, sans document ENTSO-E cité | Recoupement, pas confirmation isolée : l'énergie issue de blocs reconduits longs et non nuls (3,75 % de l'énergie sarde sur six ans, surtout `B06`, `B01`, `B03`) est du même ordre que l'excédent du thermique reconstruit sur Terna (+2,6 à +3,7 %) | `test_entsoe.py` : fixe la règle | T6, T6b, étude | non vérifiée |
| E-8c | ENTSO-E, génération sarde (A75) | Seules les séries `inBiddingZone` sont de la production ; le sens `OUT` (pompage, auxiliaires) est écarté | `prepare.py:371-372` ; 20/07 (`c26b26a`) | — | Bilan Terna : la série `OUT` de `B10` égale le pompage à 1 % près, en 2023 et 2024. Pour `B16`, le passage au sens `OUT` au crépuscule est un constat interne (aucune heure absente des deux sens), qui pèse 0,04 % du solaire. Portée de la confirmation : `B10` seulement | Aucun | T6, T6b | vérifiée |
| E-8d | ENTSO-E, génération sarde (A75) | Pas de 15 minutes ramenés à l'heure par la moyenne des sous-pas | `prepare.py:358-359` et `:404-411` | Découle de E-8a (MW moyen par pas) | — | Aucun | T6, T6b ; seul le fichier 2024 est concerné, qui passe au pas de 15 minutes le 31 décembre (`VERIF_ENTSOE_TERNA.md` § 6.2) | documentée |
| E-9 | ENTSO-E | Code `B20` rangé au thermique | `prepare.py:84` ; 22/08 (`fe4ee87`) | — | Bilan Terna : sans `B20` le thermique manque 8,9 % (2023) et 9,2 % (2024), avec lui 1,2 % et 1,8 %. Portée : 2023-2024 ; le combustible réel de `B20` n'est pas nommé | `test_sardaigne_thermique_domine` | T6, étude | vérifiée |
| E-10 | ENTSO-E | `B10` en sens sortant = pompage de STEP | `prepare.py:441-447` ; 27/08 | — | Bilan Terna : à 1 % près, deux années de suite | `test_la_step_sarde_est_hors_de_l_hydraulique_et_hors_du_total` | T6 | vérifiée |
| E-11 | ENTSO-E | Fuseau : UTC ; heure locale par Europe/Rome | `prepare.py:483-487` ; 22/08 (`6182eef`) | UTC déclaré par ENTSO-E | Le soleil : lever et coucher | `test_heure_locale_sarde_est_bien_locale` | T6b, T8, étude | vérifiée |
| E-16 | ENTSO-E, charge sarde (A65) | Charge réalisée = puissance qui transite sur le réseau sarde, prise comme dénominateur du seuil côté sarde | `prepare.py:434-438` ; `sources.yaml:241-248` | Définition du document A65 non citée dans les éléments examinés | — | `test_t6_le_seuil_corse_est_depasse_bien_plus_souvent_en_sardaigne` : 52 % en 2024 (arrondi exact) | T6b, étude | non vérifiée |
| E-12 | ENTSO-E, flux SARCO (A11) | Deux sens bruts, sans solde stocké ; positions déclarées distinguées du report | `prepare.py:507-630` ; 23/08 | — | Soldes publiés par EDF SEI (393, 418 et 396 GWh pour 2020, 2021 et 2023, `VERIF_ENTSOE_TERNA.md` § 9) | `test_sarco.py` | Étude (vérification des imports) | vérifiée |
| E-13 | Registre SEQE-UE | Trois installations corses par identifiant, filtre France obligatoire, 2019-2024, tCO2e | `prepare.py:51` ; 23/08 (`1246725`) | Registre européen des quotas | — | `test_seqe_thermique.py` | Étude (vérification du thermique) | documentée |
| E-14 | Seuils de déconnexion | 30 % hors Corse, 35 % en Corse, 45 % visé pour 2023 et jamais entré en vigueur | `figures.py:48-62` ; 04/08 (`af73c13`) | Arrêté du 23 avril 2008 modifié ; Lettre de l'OREGES 2021, p. 8 ; l'étude cite aussi la révision de juin 2023 | — | `test_le_seuil_de_deconnexion_est_deja_largement_franchi` | T6b, T8, note, étude | documentée |
| E-15 | Lettre de l'OREGES 2021 (données 2020) | Parts par énergie, taux de dépendance 86,1 %, carburants 39,9 % | `figures.py:707-725` ; 04/08 (`af73c13`) | Lettre de l'OREGES 2021, p. 4 | Contrôle croisé 2020 : les parts thermique (36 %) et liaisons (29,8 %) publiées par l'OREGES se retrouvent à 0,5 point près sur la courbe EDF. L'OREGES peut reposer sur la même donnée EDF : cohérence, pas indépendance | `test_le_controle_croise_2020_recolle_a_la_publication_de_l_oreges` | T7, note, étude | documentée |

## 4. Électricité — choix d'analyse

| N° | Choix | Code et date de pose | Motivation écrite | Sensibilité mesurée | Test | Porteurs |
|---|---|---|---|---|---|---|
| EC-1 | « Demande » = production totale de la courbe EDF, imports compris | `figures.py:133` | Le mot n'est pas discuté dans les éléments examinés | Non | `test_bond_juin_juillet` | T2, T2b, T10, étude |
| EC-2 | « Été » : juin à août pour T3 ; juin à septembre pour T10. Hiver : décembre à février, au millésime de décembre | `figures.py:245`, `:993-994` | T10 : oui (`AUDIT_SAISONNIER.md`) ; T3 : non retrouvée | T10 : mêmes six maxima avec juillet-août, juin-septembre et mai-octobre | Tests T10 | T3, T10, étude |
| EC-3 | T2b : plateau du surcroît de juillet = heures à au moins 97 % du maximum | `figures.py:193` ; 23/08 (`fb6b4d8`) | Oui : « le seuil est un choix, la fenêtre non » | Non | `test_surcroit_juillet_l_apres_midi` : 14 h et 20 h exacts | T2b, note |
| EC-4 | Seuil de déconnexion appliqué à (PV + éolien) ÷ production totale horaire, valeurs négatives ramenées à 0 ; installations avec stockage comprises ; heure comptée si la part dépasse strictement 35 | `figures.py:528-555`, `:855-862` | La note publie la limite des installations avec stockage (`note_elec.py:223-226`). Moyenne horaire au lieu d'une valeur instantanée, et stricte inégalité : non motivées | Non | Tests T8 et T6b | T6b, T8, note, étude |
| EC-5 | Fenêtre 2019-2024 pour la courbe ; T6 bornée des deux côtés par `FENETRE_T6` | `figures.py:453` ; 22/08 (`fe4ee87`) | Oui (`VERIF_ENTSOE_TERNA.md` § 7) | Sans objet | `test_t6_compare_bien_deux_fois_la_meme_periode` | T6, T8, T9, T10 |
| EC-6 | T6 : génération locale corse seule, imports retirés et reste ramené à 100 % ; STEP sarde hors du total | `figures.py:568-593` ; 27/08 | Oui (`note_elec.py:199-202`, `VERIF_ENTSOE_TERNA.md` § 3.2) | Sans objet | Tests T6 | T6, note, étude |
| EC-7 | ENR « symétrique » (PV + éolien + bioénergies + micro-hydraulique, sans stockage ni grande hydraulique) pour les comparaisons entre périodes ; T1 garde la définition d'EDF | `prepare.py:150`, `:244` | Oui (`RECONNAISSANCE.md`) | Écart borné par le stockage : 0,09 point en moyenne, 1,85 au plus | `test_creneau_le_plus_vert_autour_de_midi` | T1, T4, étude |
| EC-8 | Valeurs négatives des filières ramenées à 0 dans les parts | `figures.py:313-316`, `:547`, `:553` | Oui (`RECONNAISSANCE.md`, auxiliaires la nuit) | 2 750 h d'agrégat négatif, part minimale −1,39 % | — | T4, T6b, T8 |
| EC-9 | Temps réel : ligne retirée si le total s'écarte de plus de 50 MW de la somme des filières | `prepare.py:142` ; 19/07 (`ad58ad1`) | Oui : une ligne corrompue relevée (`RECONNAISSANCE.md`) | Six points au-delà de 3 MW, un seul au-delà de 10 | — | T1 |
| EC-10 | Fraîcheur de T1 : avertissement au-delà de 12 h, blocage au-delà de 24 h | `figures.py:64-65` ; 27/08 (`ac60f47`) | Oui (cadence mesurée de 5 à 7 h) | Sans objet | `test_fraicheur_temps_reel` (marqué `fraicheur`) | T1 |
| EC-11 | T10 : pointe, moyenne des 20 heures les plus chargées, médiane ; hiver complet au-delà de 2 100 heures | `figures.py:1050-1067` ; 06/09 (`69dc439`) | Oui (`AUDIT_SAISONNIER.md`) | Quantiles mesurés (`test_t10_la_hausse_croit_avec_le_quantile`) | Tests T10 | T10, étude |
| EC-12 | T6b : dénominateur corse = production totale, imports compris, lue comme « la puissance transitant sur le réseau » de l'arrêté ; côté sarde, deux bornes rendues (génération et charge) | `figures.py:528-562` | Oui (`figures.py:535-540`) : la conclusion ne dépend pas du choix, son amplitude oui | Les deux bornes sont publiées | `test_t6_le_seuil_corse_est_depasse_bien_plus_souvent_en_sardaigne` | T6b, étude |
| EC-13 | T7 : électricité « importée » = thermique (combustible importé) + câbles, sur toute la courbe 2019-2024 ; face à l'énergie de l'OREGES, année 2020 | `figures.py:749-760` ; 04/08 (`af73c13`) | Oui : deux périmètres emboîtés, chaque barre écrit sa base (`figures.py:744-746`). L'écart de période (2019-2024 contre 2020) n'est pas discuté dans les éléments examinés | Contrôle croisé 2020 (E-15) | `test_la_dependance_electrique_est_bien_en_deca_du_taux_energetique` : entre 66 et 70 % | T7, note, étude |

## 5. Affirmations sur la méthode

| N° | Affirmation publiée | Où | Preuve d'audit retrouvée | État |
|---|---|---|---|---|
| M-1 | « Chaque chiffre publié est reconstruit depuis les données à chaque exécution et comparé à ce que le document affirme. Un écart interrompt la publication » | `note_elec.py:304-306` | Aucune table de correspondance entre les chiffres publiés et les tests. Les tests de `test_resultats.py` couvrent beaucoup de chiffres de l'étude, mais leur exhaustivité n'a pas été établie | sans preuve |
| M-2 | « Les conclusions ont été vérifiées séparément sur chaque moitié » (heures « validées » et « estimées ») | `note_elec.py:238-239` | `RECONNAISSANCE.md`, 19/07 : deux résultats (bond de juillet, heure la plus verte) sur les deux sous-ensembles. Ce contrôle précède la correction du fuseau du 23/08, qui a déplacé l'heure la plus verte. « Moitié » désigne un tiers et deux tiers | partielle |
| M-3 | « Nous avons vérifié séparément les deux périodes : […] la hausse de juillet et le maximum renouvelable autour de midi apparaissent dans les deux » | `docs/etude.md:656-658` | Même contrôle du 19/07. Il portait sur l'heure de 14 h, devenue le créneau de midi après le 23/08. Refait depuis ? Non retrouvé | partielle |
| M-4 | « Quatre tests automatiques la tiennent » (le fuseau de la courbe EDF) | `note_elec.py:297` | `test_horodatage_corse.py` : quatre verrous, V1 à V4, en six fonctions | conforme |
| M-5 | « Les deux sont revérifiés à chaque mise à jour. Si l'un devient faux, la figure n'est pas dessinée » | `note_elec.py:208-211` | Tests bloquants `test_solaire_sous_thermique_ete` et `test_t9_hydro_secheresse`. Une garde dans `figures.py` qui empêcherait le dessin n'a pas été recherchée | à établir |
| M-6 | Empreintes revérifiées à chaque exécution ; contrôles de données bloquants | `note_elec.py:266-271` ; `note_air.py` (« Refaire ces chiffres ») ; `docs/etude.md:584-590` | `prepare._verifier_bruts` ; ordre des étapes tenu par `tests/test_codes_sortie.py` | conforme |
| M-7 | « Une valeur absente est examinée, jamais remplacée en silence » ; « une valeur manquante […] n'est pas corrigée automatiquement » | `note_elec.py:270` ; `docs/etude.md:588-590` | Trois remplacements existent, tous documentés : micro-hydraulique 2024 à 0 (E-6), report `A03` d'ENTSO-E (E-8b), négatifs ramenés à 0 (EC-8). Le report `A03` est automatique. Qu'aucun autre remplacement n'existe n'a pas été établi | partielle |
| M-8 | « Le calcul est vérifié contre l'exemple chiffré publié dans ce guide » | `note_air.py:235` | `test_ozone_8h.py`, tableau 26 | conforme |
| M-9 | « Les heures signalées comme douteuses par les producteurs sont écartées avant tout calcul, côté air comme côté température » | `note_air.py:236-237` | Température : `QT = 2` écarté (A-9). Air : `Validity > 0`, dont les codes ne sont pas documentés dans les éléments examinés (A-3) | partielle |
| M-10 | « Les tests contrôlent la cohérence des résultats avant publication » | `accueil.py:228` | Verrous bloquants avant publication, ordre tenu par `tests/test_codes_sortie.py` | conforme |
| M-11 | « Les principaux résultats sont également contrôlés automatiquement. Si une mise à jour modifie sensiblement un chiffre […] la publication est interrompue » | `docs/etude.md:603-606` | Les deux exemples cités sont tenus par des tests (`test_bond_juin_juillet`, `test_creneau_le_plus_vert_autour_de_midi`) | conforme pour les exemples cités |
| M-12 | « Plusieurs contrôles indépendants ont permis de confirmer que les heures doivent être interprétées comme des heures légales en Corse » | `docs/etude.md:663-664` | `VERIF_ENTSOE_TERNA.md` § 5 ; `test_horodatage_corse.py` | conforme |

## 6. Définitions publiées dans le glossaire de la page air

| N° | Terme | Définition publiée (`page_air.py`) | Convention qu'elle résume | Écart |
|---|---|---|---|---|
| G-1 | Objectif de qualité | « 120 µg/m³ d'ozone, mesuré sur les huit heures les plus chargées de la journée » (`:135-139`) | A-11 : maximum des moyennes glissantes sur huit heures consécutives | « consécutives » n'est pas dit : la phrase peut se lire comme les huit heures les plus élevées, où qu'elles tombent |
| G-2 | Seuil d'information | « 180 µg/m³ sur une heure […] En Corse, il n'est presque jamais atteint » (`:140-143`) | A-13 ; A1 : jamais atteint sur les étés 2020-2025 | Le constat porte sur les étés 2020-2025 ; il ne fonde pas « presque jamais » hors de cette fenêtre |
| G-3 | Station de fond | « Un appareil de mesure placé loin d'une route ou d'une usine » (`:144-147`) | A-5 : influence « Fond » du classement du producteur | Simplification : le classement dit l'absence d'influence directe d'une source, pas une distance |
| G-4 | Journée valide | « Une journée où l'appareil a suffisamment mesuré […] Les journées trop incomplètes sont écartées » (`:148-150`) | A-11 : au moins 18 moyennes sur 8 h valides | Aucun |

## 7. Contradictions et points d'attention

Contradictions relevées :

- **C-1, texte publié.** `note_elec.py:242-244` dit des six heures retirées que « le
  fichier d'EDF les porte tout de même, à production nulle ». La même note, plus bas
  (`note_elec.py:300` et suivantes), `docs/RECONNAISSANCE.md` et `VERIF_ENTSOE_TERNA.md`
  § 8 disent le contraire : trois de ces heures sont à zéro (2019, 2020, 2024) et trois
  portent 246, 253 et 200 MW (2021, 2022, 2023). L'étude (`docs/etude.md:675-676`) est
  exacte.
- **C-2, texte interne.** La docstring de `meteo_corse_to_parquet` (`prepare.py:1203-1206`)
  dit que « le flux LCSQA, lui, publie en heure légale » et qu'une erreur de fuseau
  « décalerait le pic de deux heures ». C'est l'état d'avant le 06/10 : le flux LCSQA est
  en UTC (A-7). Non publié.
- **C-3, texte interne.** `sources.yaml:513` fonde l'UTC de Météo-France sur une analogie :
  « comme les sources EDF ». La courbe historique d'EDF est en heure légale (E-3). La
  convention météo est vérifiée par ailleurs (A-8) ; c'est le raisonnement écrit qui est faux.

Points d'attention :

- **P-1, borne d'année du jeu AEE validé.** Le fichier `aee_o3_venaco_valide` va de `Start`
  = 01/01/2013 01:00 à `Start` = 01/01/2026 00:00, en UTC+1. La convention retenue (début
  d'heure en UTC+1) implique que l'AEE découpe ses années en UTC. L'ancienne lecture (fin
  d'heure, année civile en UTC+1) expliquerait la même borne. Cette observation ne
  départage donc pas les deux lectures ; elle concerne A-1, qui n'a pas de référence
  extérieure. La présentation de cette borne dans la note air (« s'arrête au 2026-01-01 »)
  attend le résultat d'A-1 : toute reformulation supposerait établi l'un des deux
  découpages.
- **P-2, deux définitions de l'été.** Juin à août pour l'air et T3, juin à septembre pour
  T10. La sensibilité n'est mesurée que pour T10.
- **P-3, deux seuils de plateau.** 95 % pour A5, 97 % pour T2b.
- **P-4, complétude de la température** (AC-7) : une journée partielle d'un poste peut
  fournir un maximum journalier à A2 sans que rien ne le signale.

## 8. Reste à couvrir

Non examinés, ou examinés seulement en surface, dans ce relevé :

- dans `figures.py`, le détail de T5 (écrêtement) au-delà de la convention E-7 ;
- la prose de `page_air.py` hors du glossaire ; les entrées « ozone » et « dioxyde
  d'azote » du glossaire, qui relèvent de la chimie et non d'une convention ;
  `preuve_demande.py` ; `compile_etude.py` ;
- `docs/etude.md` hors des § 5 et 6 ;
- `docs/BRIEF_AIR.md` hors des passages sur les fuseaux, `docs/BRIEF.md` et
  `docs/SOURCES_LOCALES.md`, où vivent des choix fondateurs ;
- les flux SAPEI (`entsoe_sapei_2024_*`) : lus par
  `test_t6_les_episodes_sardes_coincident_avec_l_export`, qui tient une phrase de l'étude
  (§ sur la Sardaigne) ; leur lecture n'a pas été examinée ;
- les sources sans porteur publié repéré : DVF (construit par `prepare`, lu par aucune
  figure) et `communes_corse` ;
- `docs/VERIF_ENTSOE_TERNA.md` § 3 à 5, 9 et 10 : repris par leurs conclusions, non relus
  en entier ;
- `fetch.py` et `provenance.py` : conventions de traçabilité, sans calcul publié. Hors
  périmètre sauf décision contraire.

## 9. À trier

Entrent au tri les lignes dont dépend un chiffre ou une affirmation publiée, ou une preuve
qui sert à les valider. Chacune appelle une décision : chercher une référence extérieure,
écrire la limite dans la note, ou renvoyer à plus tard.

- air, conventions de source : A-1, A-3, A-4, A-6 (porteur indirect, par A-2), A-9, A-10,
  A-12, A-13, A-14 ;
- électricité, conventions de source : E-4, E-5, E-7, E-8b, E-8d, E-13, E-14, E-15, E-16 ;
- affirmations sur la méthode : M-1, M-2, M-3, M-5, M-7, M-9 ;
- définitions publiées : G-1, G-2, G-3. Le glossaire compte dans le plafond de 700 mots de
  la page air (`_mots_de_prose` ne retire que les scripts, les styles et la navigation),
  et la page en comptait 699 le 06/10 : tout mot ajouté se compense ;
- contradiction dans un texte publié : C-1 ;
- choix sans motivation écrite dont dépend une figure ou un titre : AC-1 (« été = juin à
  août »), AC-4 (pondération), AC-5 (95 %), AC-6 (bornes des tranches), AC-7, EC-1,
  EC-4, EC-13 (écart de période).

Les contradictions C-2 et C-3 portent sur des textes internes, sans porteur publié.

## 10. Décisions du tri

Premier tri, le 7 octobre 2026, consacré à l'air. Une décision fixe ce qu'il faut chercher ;
le statut ne change qu'une fois la recherche faite.

| Ligne | Décision | Statut à ce jour |
|---|---|---|
| A-1 | Chercher une confirmation extérieure propre au jeu validé E1a, qui départage les deux lectures de l'heure (début d'heure en UTC+1, ou fin d'heure). Les journées de 2026 du flux continu et les bornes annuelles seules ne suffisent pas. Traitée en premier | documentée |
| A-12 | Chercher la référence qui définit le rattachement journalier officiel, en distinguant le fuseau du jour et l'étiquetage de la dernière heure de la fenêtre. Le choix de la « journée vécue » reste distinct de toute affirmation de conformité réglementaire | non vérifiée |
| A-3 | Retrouver la définition officielle des codes `Validity`, applicable aux deux jeux. Distinguer valeur absente et valeur égale à zéro dans la règle « valeur non nulle » | non vérifiée |
| A-4 | Retrouver la définition officielle des codes `Verification` et sa portée sur E1a et E2a. Une documentation retrouvée donnera le statut « documentée », sans valoir confirmation indépendante | non vérifiée |
| AC-7 | Retenu pour la suite du tri de l'air : la complétude de la température peut affecter les maxima journaliers et leur classement dans A2 | choix non motivé |
| G-2 | Borner la phrase du glossaire à la période étudiée | écart ouvert |
| C-1 | Corriger séparément le texte publié : « Le fichier d'EDF contient néanmoins ces six heures ; seules trois portent une production nulle. » | correction engagée |
| P-1 | La reformulation de la borne au 1er janvier 2026 attend le résultat d'A-1 | en attente |

Ajustements du relevé décidés au même tri : A-6 reçoit son porteur indirect, et la règle
d'entrée au tri couvre désormais les preuves de validation ; E-8 est scindée en quatre
lignes (E-8a à E-8d), parce que l'accord des totaux annuels avec Terna ne démontre pas
séparément les règles de report, de sens et de pas de temps.

La règle sur les identités exactes (§ « Comment lire ce document ») reste à valider.
