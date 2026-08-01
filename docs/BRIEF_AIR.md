# Brief — l'air corse : l'ozone

**Sujet arrêté le 31/07/2026.** Deuxième sujet du démonstrateur, traité pour lui-même.
Démarrage après la mise en ligne de l'étude électricité (septembre 2026) — *date butoir
à trancher*.

## Question fermée (figée le 31/07/2026, **recentrée le 01/08/2026**)
> Les jours où rien n'est signalé, quand l'air corse est-il le plus chargé en ozone —
> à quelle heure, à quelle saison, à quel endroit de l'île — et de combien s'alourdit-il
> quand il fait chaud ?

**Pourquoi « les jours où rien n'est signalé ».** Qualitair Corse produit des études de
qualité, et alerte par les médias régionaux quand un seuil est franchi : sur les épisodes,
la population *est* informée, et ce canal fonctionne. Deux registres se distinguent donc,
et un seul est vide :

- **l'épisode** — un seuil réglementaire est franchi, l'alerte part, les médias relaient.
  Rien à y ajouter, et prétendre le contraire serait présomptueux ;
- **le régime ordinaire** — l'air des jours où aucun seuil n'est approché, donc dont aucun
  communiqué ne parle. Par construction, un dispositif d'alerte ne peut rien en dire.

Le trou est vérifié sur les deux premières journées traitées, deux journées de juillet
parfaitement banales : le maximum horaire plafonne à 148,7 µg/m³ — loin des 180 du seuil
d'information — et pourtant l'objectif de qualité pour la santé (120 µg/m³ en maximum
journalier sur 8 heures) est franchi, par une station le 30/07 et deux le 31/07. Aucune
alerte, aucun article : il n'y avait rien à annoncer.

Titres-affirmations que l'analyse doit valider, invalider ou chiffrer :
1. « On dépasse les jours où personne n'alerte » (combien de journées franchissent
   l'objectif de qualité **sans** qu'aucun seuil d'information soit approché — l'écart
   chiffré entre ce qui est signalé et ce qui est mesuré ; c'est le titre qui définit
   le sujet)
2. « L'air se dégrade quand il fait beau » (de combien la charge s'alourdit les jours
   chauds : écart chiffré entre jours chauds et jours frais. Une **association**, jamais
   une cause — cf. la garde ci-dessous. C'est ce que Qualitair affirme en prose sans que
   personne le quantifie)
3. « Le pic n'est pas à l'heure de pointe » (heure du maximum d'ozone contre heure du
   maximum de NO₂, à station constante sur les cinq qui mesurent les deux)
4. « L'air de campagne n'est pas meilleur » (Venaco contre les stations urbaines de fond)
5. « L'été, le pire moment pour un effort en plein air se situe entre XX h et XX h »
   (conclusion actionnable — pendant de « l'heure la plus verte ». Elle change de nature
   avec le recentrage : ce n'est plus une consigne de crise, c'est une information du
   quotidien)

**Abandonné le 01/08/2026 : le décompte des dépassements du seuil d'information (180
µg/m³).** C'est le registre de l'alerte, celui qui fonctionne déjà, et il est presque
toujours vide en Corse. En faire un titre nous placerait en concurrence sur le seul terrain
où nous n'avons rien à apporter. Le décompte qui compte est celui de l'objectif de qualité,
franchi les jours ordinaires.

## Test du prompt (critère éliminatoire)
Un LLM généraliste sait déjà expliquer que l'ozone monte avec la chaleur. Ce qu'il ne
peut pas produire : le chiffre corse, daté d'hier, sur six stations nommées, croisé aux
températures relevées le même jour, avec l'empreinte des fichiers qui l'ont produit.
La fraîcheur et la lignée font le livrable, pas l'explication.

**Un second test, ajouté le 01/08/2026 : celui de l'existant.** Le premier écarte ce qu'un
modèle sait déjà dire ; celui-ci écarte ce qui est déjà publié. Qualitair Corse produit des
études de qualité — pesticides, métaux lourds, benzène, particules, air portuaire — mais
**aucune dédiée à l'ozone**, et leur page « Bilans et tendances » s'arrête à 2022, en PNG.
Refaire leur décompte annuel ne vaudrait rien ; en revanche personne ne chiffre ce qu'ils
énoncent en prose, personne ne publie de profil horaire, et personne ne dit à quelle heure
éviter de courir. S'y ajoute leur propre constat, rapporté par l'utilisateur : ces études
sont bonnes **et peu lues**. Le différenciant n'est donc pas de mieux mesurer — c'est de
rendre lisible en trois minutes ce qui dort dans des PDF, sur une donnée d'hier.

## Sources (vérifiées sur pièce le 31/07/2026)

**Mesures — LCSQA, « données temps réel », Licence Ouverte 2.0, sans jeton.**
Un CSV national par jour au format E2, publié le jour même, archivé sur le bucket
data.gouv depuis 2021. Mesures corses produites par Qualitair Corse, en µg/m³, moyennes
horaires. **Six stations mesurent l'ozone**, sur tout le gradient d'implantation :

| Station | Zone | Implantation | Influence |
|---|---|---|---|
| Ajaccio Canetto | ZAR Ajaccio | urbaine | fond |
| Ajaccio Confina 2 | ZAR Ajaccio | périurbaine | fond |
| Bastia Giraud | ZAR Bastia | urbaine | fond |
| Bastia Montesoro | ZAR Bastia | périurbaine | fond |
| Bastia La Marana | ZAR Bastia | périurbaine | industrielle |
| Venaco | ZR Corse | rurale régionale | fond |

Les deux stations « trafic » de l'île (Ajaccio Napoléon, Bastia Fango) ne mesurent pas
d'ozone : près des moteurs, le monoxyde d'azote le détruit. Ni SO₂ ni CO ne sont
mesurés en Corse.

**Températures — Météo-France, « données climatologiques de base — horaires »,
Licence Ouverte 2.0.** Un seul CSV compressé pour toute l'île, et non deux : pour ce jeu,
le producteur ne connaît ni 2A ni 2B, il publie la Corse sous l'ancien département « 20 »
(vérifié le 01/08/2026 — 57 postes, dont Ajaccio, Bastia, Corte et Vivario). Profondeur
pluri-décennale découpée en tranches, dont les deux dernières années réécrites chaque
jour. C'est le croisement multi-sources exigé par le BRIEF, et sans lui « de combien
monte-t-il quand il fait chaud » reste une impression.

**Historique — Agence européenne pour l'environnement (AEE), CC-BY. RETENU le
01/08/2026, à la place de Geod'air.** Même donnée, autre canal, **sans clé** : le namespace
des fichiers le dit — `FR.LCSQA-INERIS.AQ` — ce sont les mesures de Qualitair Corse
rapportées par le LCSQA, telles que la France les transmet à l'Europe. Un Parquet par
station et par polluant, url déterministe (`SPO-<station>_<polluant>.parquet`), et deux jeux
qui se raccordent bout à bout sans le moindre chevauchement : **E1a validé de 2013 au
01/01/2025**, puis le **flux continu jusqu'au jour même**. Douze entrées pour l'ozone,
8,78 Mo — contre les 26 Go qu'aurait coûtés le même historique par le flux national.

Trois choses que ce canal règle et que Geod'air ne réglait pas :

- **l'attente** : ni inscription, ni clé, ni quota, ni règle de bonne conduite ;
- **la frontière des deux régimes** : la colonne `Verification` déclare, ligne à ligne, ce
  qui est vérifié (1) et ce qui ne l'est pas encore (2, 3). Le brief annonçait une
  difficulté de maquette — une frontière à reconstituer et à écrire sur les figures ; le
  producteur la fournit ;
- **les frictions 2 et 3**, qui disparaissent : plus d'export en deux temps, plus d'UUID
  instable, et un format Parquet que DuckDB lit nativement.

**Fuseau : UTC+1 fixe, horodatage en FIN de période** — l'inverse du flux LCSQA. L'axe UTC
s'obtient donc en retirant **deux heures** : une pour revenir au début de période, une pour
quitter UTC+1. Établi sur pièce, et vérifié en continu : sur leurs heures communes, les deux
canaux coïncident à **0,00 µg/m³**. Un test rejoue cette comparaison à chaque run — c'est le
seul garde-fou sérieux, une erreur d'une heure ne se voyant sur aucune figure.

**Geod'air n'est pas abandonné** : le jour où la clé arrivera, deux canaux servant la même
donnée feront une vérification croisée gratuite. Ce qui suit reste donc valable si ce jour
vient. *La base de référence des données validées, alimentée par les AASQA depuis 2013,
accès par API sur inscription et clé, export filtrable par région (code Insee 94). Licence
Ouverte selon les CGU de l'Ineris, à deux conditions que le dépôt tient déjà : ne pas
altérer les données, citer la source et la date de dernière mise à jour. Deux réserves :
les logos Ineris et Prev'air sont des marques protégées — citer « Geod'air (Ineris / LCSQA) »
en toutes lettres, jamais le logo ; et la mention de source reste neutre, sans laisser
entendre que l'Ineris valide ce travail.* La même réserve de logo vaut pour l'AEE.

**Qualitair Corse** — l'AASQA agréée pour l'île. Son portail n'affiche aucune licence :
écarté comme source de données tant qu'elle n'est pas écrite noir sur blanc. Reste
citable en prose (bilans, billets d'épisode) comme n'importe quelle source documentaire.

**Posture à leur égard, arrêtée le 01/08/2026 — elle engage la note méthodologique.**
Ce sont **leurs analyseurs qui produisent nos mesures** : les données corses du flux LCSQA
sortent de leur réseau. L'étude ne comble donc aucune lacune de leur part et ne prétend pas
mieux mesurer — elle occupe un créneau que leur mandat ne couvre pas, celui du régime
ordinaire, là où le leur couvre l'épisode et l'alerte. Ils sont cités en toutes lettres,
comme producteurs de la donnée et comme source documentaire du texte. Rien dans le livrable
ne doit se lire comme un reproche, ni laisser croire qu'une information serait tue : sur les
épisodes, leur alerte par les médias régionaux fonctionne et informe réellement.

## Ce que ces données ne diront pas

- **D'où vient l'ozone.** Une concentration ne porte pas d'étiquette d'origine. La part
  formée hors de l'île — l'écho aux 27,8 % d'électricité importée est tentant — se cite,
  sourcée, mais ne se chiffre pas ici. La chiffrer demanderait un modèle, pas des mesures.
- **Ce qui a causé un pic.** Le Vazzio, Lucciana, les navires : rien dans ces mesures ne
  les désigne. Bastia La Marana est classée « industrielle » ; ce mot décrit l'implantation
  de la station, pas la provenance de ce qu'elle mesure. Cette étude referme la dette de
  la §4 de l'étude électricité — elle ne la retourne pas en accusation.
- **Que la chaleur *cause* l'ozone** (garde ajoutée le 01/08/2026). Le mécanisme, lui, est
  établi et ne relève pas de la corrélation : l'ozone du bas de l'atmosphère n'est émis par
  rien, il se fabrique sur place quand les oxydes d'azote et les composés organiques volatils
  réagissent **sous le rayonnement ultraviolet** — réaction reproduite en laboratoire depuis
  les années 1950. Mais le moteur est le soleil, pas le thermomètre. La température n'agit
  qu'indirectement : elle accélère les réactions, augmente les composés volatils émis par la
  végétation (l'isoprène des chênes et des pins y est très sensible), et décompose un composé
  qui stocke les oxydes d'azote pour les relâcher à la chaleur. Surtout, **tout arrive
  ensemble** : les jours chauds sont les jours anticycloniques — ciel dégagé, air stagnant,
  pas de vent pour disperser. Chaleur, ensoleillement et absence de brassage varient de
  concert, et rien dans des mesures de concentration ne permet de démêler leurs parts.
  Ce que l'étude produit est donc une **association**, et elle s'énonce comme telle :
  « les jours à 30 °C, on relève X µg/m³ de plus que les jours à 20 °C » — jamais « la
  chaleur fait monter l'ozone de X ». Le thermomètre est le marqueur d'un type de temps, pas
  un facteur agissant seul. Ce n'est pas une perte pour le titre n° 4 : qui se demande s'il
  peut courir ce soir n'a pas besoin de savoir *pourquoi* l'air est chargé.
- **2022 le montre en grandeur nature.** Cette année-là, deux causes candidates ont bougé
  ensemble. Il a fait chaud et sec — et le thermique est monté à **47,5 % du mix contre
  34,8 % l'année suivante**, parce que les barrages étaient au plus bas : **12,3 %
  d'hydraulique, le creux de la série 2019-2024** (chiffres tirés de notre propre
  `edf_courbe_corse.parquet`, donc vérifiables par test). Plus de chaleur *et* plus de
  précurseurs la même année : un surcroît d'ozone en 2022 serait indémêlable. L'exemple se
  cite en prose — il dit mieux que n'importe quelle mise en garde abstraite pourquoi cette
  étude mesure sans attribuer, et il relie le sujet air à l'étude électricité sans rien lui
  faire dire de plus que ce qu'elle montre.
- **Le climat.** L'ozone est le point où l'air et le climat se touchent : sa formation
  demande du soleil et se trouve favorisée par la chaleur. Les gaz à effet de serre restent
  hors champ.

## Garde-fous méthodologiques

- **Les valeurs du flux temps réel sont brutes et non validées.** Le 30/07/2026, Bastia
  Giraud porte un code de validité négatif sur ses relevés d'ozone. Le filtre sur la
  validité se pose avant tout calcul, et se verrouille par un test.
- **Deux métriques réglementaires cohabitent**, et les deux valeurs sont désormais
  **re-sourcées sur le texte** (art. R221-1 du code de l'environnement, vérifié le
  01/08/2026) : le seuil de recommandation et d'information vaut « 180 µg/m³ en moyenne
  horaire » ; l'objectif de qualité pour la santé vaut « 120 µg/m³ pour le maximum
  journalier de la moyenne sur huit heures, pendant une année civile ». Le même article
  porte le seuil d'alerte (240 µg/m³ en moyenne horaire) et une **valeur cible** distincte
  de l'objectif de qualité — même 120 µg/m³, mais « à ne pas dépasser plus de vingt-cinq
  jours par année civile en moyenne calculée sur trois ans ». Trois décomptes différents
  derrière deux chiffres : ne jamais les mêler dans une figure, ni dans une phrase.
- **La moyenne glissante sur 8 heures n'est servie par aucune des deux sources.** Ni le
  flux temps réel, ni l'API Geod'air, qui s'arrête aux moyennes horaires. Elle est donc
  recalculée dans `prepare` — **fait le 01/08/2026**, et la règle n'y est pas déduite mais
  recopiée du guide du producteur : LCSQA/Ineris, *Guide Calcul des statistiques relatives
  à la Qualité de l'Air*, Ineris-219621-2801775-v1.0 (mars 2024), § 5.3.3 et 5.3.4.
  Moyenne des heures **valides** parmi l'heure et les sept précédentes, divisée par leur
  nombre et non par 8 ; valide à partir de 6 heures ; maximum journalier valide à partir
  de 18 moyennes sur 24. Le verrou est le **tableau 26 du guide** — deux journées d'ozone
  déjà calculées par le producteur — rejoué à l'identique dans `tests/test_ozone_8h.py`.
  Il a servi tout de suite : il a établi qu'une moyenne glissante existe à **chaque heure
  du jour**, y compris aux heures dont la mesure propre est invalide (le guide en donne
  l'exemple à 13 h). Ne les calculer qu'aux heures mesurées faisait tomber son décompte de
  13 à 11, sous les 18 requis — des journées parfaitement opposables auraient été rejetées.
  Deux pièges de plus, tenus par le même fichier : le guide étiquette ses heures à la FIN
  (01 h → 24 h) là où le flux LCSQA les étiquette au DÉBUT (00 h → 23 h), et la fenêtre
  doit porter sur le TEMPS et non sur les lignes, sans quoi trois heures manquantes la
  font remonter jusqu'au matin.
- **Le calcul glissant impose un axe UTC sur l'air**, ajouté le 01/08/2026, symétrique de
  celui de la météo. Sur l'étiquette locale, une fenêtre de 8 heures se raccourcit en mars
  et compte double en octobre. Le jour d'attribution, lui, reste **local** : c'est la
  journée vécue qui a un sens, pas le découpage UTC.
- **Aucune des sources n'est en heure légale** (établi le 01/08/2026, après correction).
  Météo-France publie en **UTC**, le flux LCSQA en **UTC+1 fixe**. Le brief a longtemps
  affirmé « heure légale » pour le LCSQA, sur la foi d'une observation qui écartait l'UTC
  mais s'accommodait tout aussi bien d'UTC+1 : le fichier publiait 19:00 quand il était
  20 h 07 locale. Le test qui tranche est celui déjà appliqué à la météo — aux deux
  dimanches de changement d'heure, le flux publie **24 heures**, de 00:00 à 23:00, sans
  doublon, là où une heure légale en compterait 23 et 25 (vérifié sur les archives des
  30/03 et 26/10/2025). L'axe UTC du flux d'air se construit donc par **soustraction d'une
  heure**, non par conversion de fuseau : l'ancien calcul était juste en hiver et faux d'une
  heure en été. L'heure **légale** se déduit ensuite de l'axe UTC — c'est celle que vivent
  les gens, donc celle des titres, et elle ne se lit pas dans le brut.
- **Ce que la correction change, et ce qu'elle épargne.** La jointure avec les températures
  — que ce brief exige justement sur l'axe UTC — était décalée d'une heure en été, comme
  l'attribution du jour pour l'heure de minuit. La moyenne glissante sur 8 heures, elle,
  était juste : un décalage constant ne déforme pas une fenêtre. En revanche une journée de
  brut ne recouvre plus une journée locale : elle donne 23 heures du jour J et une heure du
  jour J+1, ce qui suffit encore à un maximum journalier opposable (23 heures ≥ 18) mais
  produit une journée résiduelle, correctement marquée invalide.
- **Le piège du retour à l'heure d'hiver tombe** avec cette correction : en fuseau fixe,
  2 h du matin n'existe jamais deux fois dans le brut. La garde a donc changé d'objet —
  elle vérifie désormais que la grille horaire reste **régulière**, un horodatage par heure
  sans trou ni doublon. Si le producteur basculait un jour en heure légale, le dimanche de
  mars perdrait une heure et celui d'octobre en doublerait une : le build s'arrêterait ce
  jour-là, au lieu de laisser filer un axe faux pendant des mois — ce qui vient d'arriver.
- **Le fichier météo a ses propres réserves**, du même genre que le flux temps réel. Son
  code qualité `QT` distingue la donnée validée de la douteuse en cours de vérification :
  il se filtre avant tout calcul. Et sa dernière journée est tronquée — le fichier
  s'arrête aux petites heures du jour de publication, si bien qu'une « journée » de
  quatre heures fausserait n'importe quel maximum journalier. Le croisement porte donc
  sur la dernière journée complète commune aux deux sources.
- **Ce « commun » n'existait pas, et a été construit le 01/08/2026.** Les deux producteurs
  ne publient pas au même rythme : le flux d'air offrait J-1 quand la dernière journée
  météo complète était J-2, si bien que les deux Parquet **sortis du même run n'avaient
  aucune journée en partage** — zéro, structurellement, et non par accident de calendrier.
  Le flux LCSQA est donc passé de `date_url: hier` à `avant-hier`, ce qui les aligne (1
  journée commune au lieu de 0, vérifié). Un jour de fraîcheur en moins ne coûte rien face
  à une dataviz de référence arrêtée en 2023 ; ne jamais pouvoir croiser, si. La garde
  qui refusera une jointure vide reste due, au moment d'écrire le croisement : un
  producteur en retard ramènerait le commun à zéro sans prévenir.
- **L'appariement station d'air ↔ poste météo est tranché (01/08/2026).** Le flux LCSQA ne
  porte aucune coordonnée ; elles viennent donc du **référentiel du même producteur** —
  LCSQA/Ineris, « Dataset D : métadonnées des stations de mesures », feuille
  `AirQualityStations`, Licence Ouverte 2.0, publié dans le même jeu data.gouv que le flux.
  Les positions ne sont donc plus relevées à la main mais déclarées par celui qui mesure.

  | Station | Alt. | Poste retenu | Distance |
  |---|---|---|---|
  | Ajaccio Canetto | 39 m | Milelli | 1,97 km |
  | Ajaccio Confina 2 | 70 m | Campo dell'Oro | 3,31 km |
  | Bastia Giraud | 60 m | Bastia ville | 0,72 km |
  | Bastia Montesoro | 15 m | Bastia ville | 3,76 km |
  | Bastia La Marana | 15 m | Poretta (Lucciana) | 0,93 km |
  | Venaco | 653 m | Vivario | 9,86 km |

- **Un seul critère, des résultats parfois opposés.** Les deux postes d'Ajaccio diffèrent de
  2,6 °C sur les maxima d'été quand les écarts d'altitude en jeu pèsent au plus 0,3 °C de
  gradient : l'altitude ne départage pas, ce sont la proximité et l'exposition qui décident —
  Campo dell'Oro est une aire aéroportuaire que la brise de golfe ventile, les Milelli un
  replat d'oliveraie abrité 80 m plus haut. D'où deux postes différents pour deux stations
  distantes de 5,6 km. C'est la cohérence du *critère* qui compte, pas celle du résultat.
- **Venaco va à Vivario, et non à Corte**, pourtant plus proche (5,84 km contre 9,86). Corte
  est encaissée : sa cuvette creuse l'amplitude diurne, très nettement l'été, et le changement
  de régime se sent dès Saint-Pierre-de-Venaco. Mesuré sur 152 journées d'été : **17,0 °C
  d'amplitude à Corte contre 15,4 à Vivario**, et un écart entre les deux qui passe de 1,8 °C
  sur les minima à 3,4 sur les maxima. Un biais qui se *déforme* au fil du jour, là où un
  simple décalage d'altitude serait resté inoffensif — c'est précisément ce qui casserait la
  relation ozone/température. L'altitude confirme : +120 m vers Vivario, −303 m vers Corte.
- **Le poste appelé « BASTIA » n'est pas à Bastia** — 20148 = 2B148 = Lucciana, l'aéroport de
  Poretta, à 18,5 km de Bastia ville (« BASTIA_SAPC », 2B033). Le référentiel des stations
  place « Bastia La Marana » sur cette même commune de Lucciana : les deux se répondent à
  0,93 km et 5 m d'altitude près.
- **Confina 2 ne mesure que depuis le 31/01/2024**, quand les cinq autres stations remontent
  à 2006-2011. Sur un historique partant de 2020, elle portera deux ans contre sept : toute
  figure comparant les stations doit l'écrire, sous peine de faire passer une série courte
  pour une série trouée. (La fiche publique de Qualitair annonce le 01/08/2023, et omet
  l'ozone que son propre flux publie — le référentiel fait foi.)
- **La figure nomme le poste, jamais la commune de la station d'air.** « Ozone à Venaco,
  température relevée à Vivario » est exact ; « température à Venaco » serait faux. C'est
  une approximation assumée, pas une équivalence — et le titre n° 3 (ville contre
  campagne) n'en dépend pas du tout, puisqu'il compare des concentrations sans température.
- **Comparer ce qui est comparable.** Ville contre campagne se joue entre stations « de
  fond » ; y mêler la station industrielle ou les stations trafic mélangerait les
  populations. Le périmètre s'écrit sur la figure.
- **Les poussières sahariennes** dégradent l'air sans aucune combustion locale. Sans
  effet sur l'ozone, mais dirimant si une figure PM s'ajoute.

## Architecture des sources (actée le 31/07/2026)

Le flux temps réel est national : **12,7 Mo et 48 000 lignes par jour**, dont la Corse fait
environ 1 %. Reconstituer six ans par ce canal reviendrait à rapatrier près de 26 Go, puis
à les relire à chaque vérification d'empreinte. L'export Geod'air filtré sur la région règle
le problème. D'où le découpage, qui épouse la politique de fraîcheur déjà en place :

- **Geod'air = source figée.** L'historique se télécharge une fois, puis se re-vérifie par
  empreinte à chaque run sans être retéléchargé. Le cron n'appelle jamais l'API. C'est aussi
  ce qu'exige la règle de bonne conduite de Geod'air : une interrogation par date, heure,
  polluant et type de statistique, sous peine de suspension du compte.
- **LCSQA sur data.gouv = source glissante.** La fraîcheur, sans clé ni quota. La page de
  l'API y renvoie elle-même pour les moyennes horaires actualisées.

Météo-France découpe ses fichiers exactement de la même façon, sans qu'on ait à forcer
quoi que ce soit : les deux dernières années dans un fichier réécrit chaque jour, le passé
clos dans un autre. Seul le premier est déclaré (`meteo_horaire_corse`, 27 Mo, glissant).

**Profondeur arrêtée le 01/08/2026 : du 01/01/2020 à hier.** Deux constats l'ont décidée.

Le premier : *le flux temps réel n'accumule rien*. Son fichier porte un nom fixe, écrasé
à chaque run — `air_corse.parquet` pèse 7 Ko, une seule journée. Il n'est donc pas un
historique en formation, c'est un point de fraîcheur, un seul. **Geod'air porte la
totalité du contenu analytique des quatre titres-affirmations**, et sa profondeur décide
de ce que l'étude peut dire.

Le second : *le choix est binaire, pas graduel*. Rester à 2025 laisse le fichier météo
glissant suffire ; remonter d'un seul mois avant impose `previous-2020-2024`, 82 Mo en
bloc. Et une fois ces 82 Mo payés, s'arrêter à 2022 ou 2023 coûterait le même prix pour
deux ou trois étés de moins. La coupure du producteur météo tombe donc exactement où il
faut, et le raccord `previous` + `latest` se fait sans trou.

Ce que la profondeur longue achète : sept étés au lieu de deux, dont un en cours. Les
deux titres qui en dépendent sont le décompte de dépassements du seuil d'information et
le créneau horaire estival — soit la seule affirmation qui promet un chiffre officiel et
la seule conclusion actionnable. Le risque n'est pas théorique : le 31/07/2026, le maximum
insulaire plafonnait à 148,7 µg/m³ (Bastia Montesoro), sous le seuil de 180. Sur dix-neuf
mois, « zéro dépassement » était un résultat possible.

Réserve assumée : 2020 est une année de confinements, où l'ozone urbain a plutôt monté,
faute de monoxyde d'azote pour le détruire. Sans effet sur des titres qui ne comparent pas
les années entre elles — mais à signaler si un décompte annuel apparaît.

`previous-2020-2024` a été **vérifié sur pièce le 01/08/2026** — HTTP 200, 81,9 Mo,
206 colonnes, `NUM_POSTE`/`NOM_USUEL`/`AAAAMMJJHH`/`T`/`QT` présentes, première ligne
AJACCIO au 01/01/2020 à 00 h. Il n'est pas déclaré pour autant : tant que Geod'air n'est
pas là, ce seraient 82 Mo dont l'empreinte serait re-vérifiée à chaque run pour rien. Le
jour venu, c'est une entrée figée de plus — même url, même format.

Deux inconnues ne se lèveront qu'avec la clé, et toutes deux touchent la maquette autant
que le pipeline. **Où s'arrête le validé** : Geod'air consolide a posteriori, et le flux
temps réel ne comble pas le trou entre sa dernière date et hier — l'étude aura donc deux
régimes, un historique validé et un point de fraîcheur brut, dont la frontière s'écrit sur
les figures. **L'âge des stations** : « Ajaccio Confina 2 » porte un ordinal qui sent le
remplacement ; si elle est plus jeune que 2020, une figure à six stations aura des séries
tronquées, et il faudra soit écrire la profondeur par station, soit couper au plus petit
dénominateur commun pour ce qui compare les stations entre elles.

L'export demandera **O₃ et NO₂** à la maille horaire, en une interrogation sur la région :
le titre n° 2 repose sur le NO₂, et un second export serait une seconde interrogation là
où la règle de bonne conduite pousse à l'inverse. Le relevé du 31/07/2026 confirme que ce
périmètre suffit — les cinq stations urbaines et périurbaines mesurent les deux polluants,
ce qui permet de jouer le titre n° 2 à station constante, même lieu et même heure. Venaco
n'a pas de NO₂, et n'a pas d'heure de pointe non plus.

Trois frictions à lever dans `fetch.py`, aucune rédhibitoire :

1. ~~**La clé passe par un en-tête HTTP** (`apikey:`), là où le dépôt ne sait injecter
   `${VAR}` que dans l'URL.~~ **Levée le 01/08/2026** : champ `entetes:` dans
   `sources.yaml`, `${NOM}` expansé au seul moment du téléchargement, gabarit seul au
   manifeste. Un secret a trois sorties possibles — le log, le manifeste versionné, et le
   réseau si une redirection emmène l'en-tête chez un tiers. Les trois sont tenues par
   `tests/test_secrets.py`, et chacune a été vérifiée par mutation : sans le correctif, le
   test correspondant échoue. La troisième n'était pas au programme et méritait de l'être —
   httpx retire l'en-tête `Authorization` quand l'origine change, mais pas un `apikey:`
   maison : le jeton serait parti chez le CDN, sans un message d'erreur pour le dire.
2. **L'export se fait en deux temps** : une requête de génération qui renvoie un
   identifiant, puis un téléchargement à réessayer jusqu'à ce que le fichier soit prêt.
   L'URL finale porte un UUID et n'est pas stable ; c'est l'URL de commande, elle
   parfaitement déterministe, qui figure dans `sources.yaml`.
3. **Geod'air consolide ses données a posteriori.** Un export refait plus tard peut
   légitimement différer de l'original : c'est le cas que `--recertifier` traite déjà.

## Définition de « fini »

**Forme du livrable, arrêtée le 01/08/2026** — elle découle directement du recentrage :
si le contenu existe déjà mais reste peu lu, alors la forme *est* l'apport.

- [ ] **court** : la page se parcourt en trois minutes. Si elle déborde, retrancher un
      titre — jamais abréger les sources ni la note méthodologique
- [ ] **accessible au plus grand nombre** : prose pédagogique, sans jargon ni technicité de
      style. Le sérieux vient de la précision et des sources, jamais du vocabulaire — même
      exigence que l'étude électricité, y compris dans les passages les plus techniques
- [ ] **sourcé à vue** : chaque chiffre porte d'où il vient, sans qu'il faille chercher

- [ ] une page interactive exportée en HTML déployable en iframe sans dépendance tierce
- [ ] chaque visuel cite sa source et sa date, par `viz.export_html`
- [ ] les sources entrent par `sources.yaml`, avec licence et producteur ; rien à la main
- [ ] les affirmations chiffrées sont verrouillées par des tests de résultats
- [ ] une note méthodologique : sources, dates de collecte, limites, licences

## Anti-dérive
Un sujet à la fois. Si ça déborde : réduire l'ambition, pas la rigueur. L'ozone est le
sujet ; les particules, le trafic maritime et le climat ne sont pas des extensions
naturelles, ce sont d'autres briefs.
