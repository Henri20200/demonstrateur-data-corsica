# Brief du sujet eau — cadre de travail

**Statut : reconnaissance faite le 13/08/2026. Sujet NON lancé.**
Rien n'est décidé tant que la question fermée n'est pas écrite (§ 1).
Calendrier : après le 30/09/2026 — la date butoir de la prospection prime.

## 1. Question fermée — À TRANCHER

Deux candidates sont sorties de la reconnaissance. Elles ne racontent pas la même
chose et n'engagent pas les mêmes sources. Le choix est éditorial, pas technique.

**A — Le contraste des régimes.**
Une île, deux hydrologies opposées : les grands fleuves de l'Est sous influence
de la fonte des neiges, les petits cours d'eau des extrémités en régime pluvial
méditerranéen à étiage estival extrême. Source unique (Hub'Eau hydrométrie),
échantillonnage résolu (§ 3), profondeur jusqu'à 65 ans.

**B — Le couplage eau / électricité.**
Le même mètre cube sert en séquence : turbiné à Calacuccia, prélevé 40 km en aval
à Rizzale pour l'agriculture et l'eau potable. Deux sources de cadences
différentes (§ 2), et un raccord direct au fil rouge autonomie électrique.

À écrire ici, en une phrase, avant la première ligne de code.
Puis les titres-affirmations que l'analyse devra valider, invalider ou chiffrer.

## 2. Sources — vérifiées le 13/08/2026

**Hub'Eau hydrométrie** — plateforme HYDRO du ministère (SCHAPI / DREAL).
API REST, JSON. 98 stations en Corse, 62 en service, **33 en débit temps réel**.

| | |
|---|---|
| temps réel (`observations_tr`) | pas de 5 min, brut, non validé, profondeur 1 mois |
| journalier validé (`obs_elab`, QmnJ) | **retard de 1 jour sur 31 stations / 33** |
| profondeur | 1960 pour les plus anciennes (23 872 jours sur le Vecchio) |
| plafond API | 20 000 enregistrements → paginer les séries longues |

**Hub'Eau prélèvements (BNPE)** — 1 006 ouvrages en Corse, volumes annuels par
usage, séries 2012 → 2023. Cadence annuelle, retard 2 à 3 ans.

Répartition 2023, en m³ : eau turbinée 982 893 821 · eau potable 38 851 858 ·
irrigation 30 231 340 · canaux 3 133 980 · industrie 233 908.

> **Piège à ne jamais franchir.** L'eau turbinée n'est pas consommée : elle
> retourne au cours d'eau. Elle ne se compare pas aux quatre autres postes et ne
> s'agrège pas avec eux en « total prélevé ». Si un visuel les met côte à côte,
> le périmètre s'écrit sur la figure.

**Écartée : OEHC en open data.** Le seul jeu publié est une couche géographique
de 12 barrages, modifiée le 27/01/2014, sans niveau ni volume ; l'API de
data.corsica répond 410 sur ce jeu. Non réutilisable.

**Écartée : SISPEA / couche service.** Rendements de réseau, prix, indicateurs
par service : annuel, déclaratif, 2 à 3 ans de retard, taux de réponse variable.
Incompatible avec l'argument de fraîcheur.

## 3. Échantillonnage — résolu

Le choix des stations ne se fait pas à la carte. Il suit la **typologie COLONNA
(2021), tableau XVI** — synthèse des trois typologies ORSINI (2008), construites
par ACP sur 24 rivières couvrant près de 70 % de l'île.

Croisement fait : **les 10 groupes ont au moins une station en débit temps réel**,
25 stations sur 33 sont classées.

Deux points restent ouverts :
- 7 affectations reposent sur la position de la station (Golo et Tavignano sont
  classés par tronçon, pas par rivière). Inférence à faire valider.
- L'en-tête du groupe 1 annonce un point culminant < 2 500 m alors que ses membres
  sont à 2 700 m (Monte Cinto, Monte Rotondo). Imprécision du tableau publié.

## 4. Contrôles à passer avant toute figure

- [ ] **NULL vs zéro.** Vérifié le 13/08 : le temps réel affiche `0` là où la série
      validée dit `NULL` (Regino, Baraci, Bala). Ne jamais tracer un zéro temps réel
      sans le confronter au QmnJ du jour.
- [ ] **Stations sous influence.** Le Prunelli à Tolla affiche 252 l/s constants sur
      8 jours — débit réservé, pas hydrologie. La Bravona au site barrage affiche
      des valeurs incohérentes avec son débit moyen publié. À qualifier.
- [ ] **Comparer ce qui se compare.** Le coefficient mensuel de débit (C1…C12,
      rapport du débit spécifique mensuel au débit spécifique annuel) est sans
      dimension, donc comparable entre rivières de tailles différentes. Valeurs
      publiées de référence : C5 = 1,45 (Golo, Tavignano) ; C9 = 0,14 (Alisu,
      Luri, Ortolo).
- [ ] **Verrouiller sur un exemple chiffré publié**, comme la moyenne 8 h de
      l'ozone l'est sur le tableau 26 du guide LCSQA.

## 5. Test du prompt

Donnée à 5 minutes sur 33 stations + série journalière validée à J-1 + typologie
publiée pour l'échantillonnage + manifeste daté et empreinté. Le test passe.

Ce qui ne le passerait pas : citer les conclusions des thèses. Un résultat publié
se **recalcule** depuis Hub'Eau, la thèse servant de référence de méthode et de
point de contrôle.

## 6. Définition de « fini »

Identique au brief principal — page HTML sans dépendance tierce, note
méthodologique, source visible sur chaque visuel — plus, propre à ce sujet :

- [ ] le périmètre de chaque groupe de la typologie est écrit sur la figure
- [ ] l'écart de cadence entre ressource (5 min) et destination (annuelle, J-3 ans)
      est énoncé, pas masqué
- [ ] les stations retenues sont justifiées par le tableau XVI, pas par la carte

## 7. Bibliographie vérifiée

| Référence | Accès |
|---|---|
| COLONNA F. (2021), *Les conséquences du changement climatique sur les ressources en eau et le peuplement piscicole des cours d'eau de Corse*, thèse, Università di Corsica, dir. A. Orsini | PDF libre, HAL `tel-03895889` |
| ORSINI S. (2020), *Modification des paramètres abiotiques et biotiques du Rizzanese : impact de l'aménagement hydroélectrique et/ou des conséquences du changement climatique*, thèse, dir. A. Orsini | PDF libre, HAL `tel-03670551` |
| ORSINI A. (1986), thèse, Aix-Marseille 3, dir. J. Giudicelli | notice seule |
| DAAGI W. (2012), *L'encadrement juridique de la production et de la distribution de l'eau : l'exemple de la Corse*, thèse, dir. J.-F. Poli et A. Orsini | résumé seul, non diffusée |
| ORSINI A. (2022), *Les eaux douces de Corse*, 8Studios Scamaroni, 272 p., ISBN 9782955134016 | bibliothèque |
| BRIGODE P. *et al.* (2019), « Une cartographie de l'écoulement des rivières de Corse », *La Houille Blanche* 105(1), 68-77 | doi 10.1051/lhb/2019009 |

Licences : les thèses HAL sont sous autorisation de diffusion HAL, pas Creative
Commons — citation oui, redistribution et reprise de figures non.

## 8. Chaîne Calacuccia → plaine, établie le 13/08/2026

Barrage de Calacuccia (EDF, 1968, 72 m, 23,4 Mm³) — vocation déclarée au CFBR :
hydroélectricité seule. Alimente Corscia et Castirla, 57 MW.

L'eau turbinée redescend le Golo sur 40 km jusqu'à la prise de Rizzale, commune
de Prunelli-di-Casacconi, **exploitée par l'OEHC**. De là, canal à ciel ouvert
(3 m³/s nominal) et conduite Ø1800 vers la réserve de Guazza, qui dessert les
terres agricoles du nord de la Plaine orientale, la station de pompage de
Casamozza, et **en période estivale l'agglomération de Bastia**.

Chantier de sécurisation voté : 3,3 M€ HT (État-PEI 47 %, Collectivité 37 %,
Agence de l'eau 16 %), avec restauration de la continuité biologique.

## 9. Anti-dérive

Le sujet est **faisable**, ce n'est pas une raison de le lancer. Le risque n'est
plus l'accès à la donnée, c'est d'attaquer avant d'avoir la question fermée : une
figure sort en une soirée, un chantier ouvert reste ouvert six semaines. Deux
études finies valent mieux que deux études finies plus une amorce.