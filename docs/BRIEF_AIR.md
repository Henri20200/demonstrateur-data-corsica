# Brief — l'air corse : l'ozone

**Sujet arrêté le 31/07/2026.** Deuxième sujet du démonstrateur, traité pour lui-même.
Démarrage après la mise en ligne de l'étude électricité (septembre 2026) — *date butoir
à trancher*.

## Question fermée (figée le 31/07/2026)
> Quand l'air corse est-il le plus chargé en ozone — à quelle heure, à quelle saison,
> à quel endroit de l'île — et de combien monte-t-il quand il fait chaud ?

Titres-affirmations que l'analyse doit valider, invalider ou chiffrer :
1. « L'air se dégrade quand il fait beau » (le pic d'ozone suit le soleil, pas les
   moteurs : écart entre jours chauds et jours frais, et nombre de dépassements du
   seuil d'information sur la profondeur retenue)
2. « Le pic n'est pas à l'heure de pointe » (heure du maximum d'ozone contre heure du
   maximum de NO₂)
3. « L'air de campagne n'est pas meilleur » (Venaco contre les stations urbaines)
4. « L'été, le pire moment pour un effort en plein air se situe entre XX h et XX h »
   (conclusion actionnable — pendant de « l'heure la plus verte »)

## Test du prompt (critère éliminatoire)
Un LLM généraliste sait déjà expliquer que l'ozone monte avec la chaleur. Ce qu'il ne
peut pas produire : le chiffre corse, daté d'hier, sur six stations nommées, croisé aux
températures relevées le même jour, avec l'empreinte des fichiers qui l'ont produit.
La fraîcheur et la lignée font le livrable, pas l'explication.

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

**Historique — Geod'air (LCSQA / Ineris), Licence Ouverte.** La base de référence des
données **validées**, alimentée par les AASQA depuis 2013. Accès par API, sur inscription
et clé. L'export se filtre par région (code Insee 94 pour la Corse), par station et par
influence : six stations sur plusieurs années pèsent quelques dizaines de Mo. Les conditions
générales de l'Ineris placent ces données sous Licence Ouverte, à deux conditions que le
dépôt tient déjà — ne pas les altérer, citer la source et la date de dernière mise à jour.
Deux réserves à respecter : les logos Ineris et Prev'air sont des marques protégées, donc
citer « Geod'air (Ineris / LCSQA) » en toutes lettres et jamais le logo ; et la mention de
source reste neutre, sans laisser entendre que l'Ineris valide ce travail.

**Qualitair Corse** — l'AASQA agréée pour l'île. Son portail n'affiche aucune licence :
écarté comme source de données tant qu'elle n'est pas écrite noir sur blanc. Reste
citable en prose (bilans, billets d'épisode) comme n'importe quelle source documentaire.

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
- **Les deux sources ne sont pas à la même heure.** Météo-France publie en UTC, le flux
  LCSQA en heure légale française. Ce n'est pas une supposition : les deux dimanches de
  changement d'heure comptent 24 heures dans le fichier météo, quand l'heure légale en
  compte 23 et 25 — seule une échelle à décalage fixe fait ça. La conversion est faite une
  fois pour toutes dans `prepare`. Reste un piège pour le croisement à venir : le dimanche
  du retour à l'heure d'hiver, 2 h du matin existe deux fois. La jointure se fera donc sur
  l'axe UTC et jamais sur l'étiquette locale, sous peine de compter cette heure en double.
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
- **L'appariement station d'air ↔ poste météo est tranché (01/08/2026)**, et il est
  *nominatif* : six lignes écrites à la main dans `prepare.py`, pas un calcul de distance.
  D'abord parce que le flux LCSQA ne porte **aucune coordonnée** — un appariement
  automatique exigerait une source de plus, pour un résultat qui n'aurait de mieux que
  l'apparence de l'objectivité. Ensuite parce que le critère qui compte n'est pas la
  distance mais la similarité de **régime thermique**.
- **Venaco va à Vivario, et non à Corte** — contre le plus proche, en distance comme en
  altitude. Corte est encaissée : sa cuvette creuse l'amplitude diurne, très nettement
  l'été, et le changement de régime se sent dès Saint-Pierre-de-Venaco, entre les deux.
  La nuance est décisive. Un biais d'altitude *constant* serait inoffensif ici : il
  décalerait l'axe des températures sans toucher à la **pente** de la relation
  ozone/chaleur, seule chose que le titre n° 1 mesure. Une amplitude différente n'est pas
  un décalage — l'écart avec Venaco varie selon l'heure et la saison, et déforme
  exactement ce qu'on cherche à établir.
- **Le poste appelé « BASTIA » n'est pas à Bastia.** Les codes commune portés par
  `num_poste` le disent : 20148 = 2B148 = Lucciana, c'est l'aéroport de Poretta, dans la
  plaine de la Marana ; Bastia ville, c'est « BASTIA_SAPC », 20033 = 2B033. Les deux
  stations urbaines vont donc à la ville et la station de la Marana au poste de la plaine.
  S'y fier au nom mettrait le thermomètre de la plaine au pied des analyseurs urbains.
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
- [ ] une page interactive exportée en HTML déployable en iframe sans dépendance tierce
- [ ] chaque visuel cite sa source et sa date, par `viz.export_html`
- [ ] les sources entrent par `sources.yaml`, avec licence et producteur ; rien à la main
- [ ] les affirmations chiffrées sont verrouillées par des tests de résultats
- [ ] une note méthodologique : sources, dates de collecte, limites, licences

## Anti-dérive
Un sujet à la fois. Si ça déborde : réduire l'ambition, pas la rigueur. L'ozone est le
sujet ; les particules, le trafic maritime et le climat ne sont pas des extensions
naturelles, ce sont d'autres briefs.
