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
Licence Ouverte 2.0.** CSV compressés par département (2A, 2B), profondeur pluri-
décennale, actualisation quotidienne sur les deux dernières années. C'est le croisement
multi-sources exigé par le BRIEF, et sans lui « de combien monte-t-il quand il fait
chaud » reste une impression.

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
- **Le climat.** L'ozone est le point où l'air et le climat se touchent : il se forme sous
  la chaleur. Les gaz à effet de serre restent hors champ.

## Garde-fous méthodologiques

- **Les valeurs du flux temps réel sont brutes et non validées.** Le 30/07/2026, Bastia
  Giraud porte un code de validité négatif sur ses relevés d'ozone. Le filtre sur la
  validité se pose avant tout calcul, et se verrouille par un test.
- **Deux métriques réglementaires cohabitent** : le seuil d'information-recommandation
  (180 µg/m³ en moyenne horaire) et l'objectif de qualité pour la santé (120 µg/m³ sur
  8 heures glissantes). Elles ne comptent pas la même chose ; jamais dans la même figure.
  Les deux valeurs sont à re-sourcer sur le texte réglementaire avant écriture.
- **La moyenne glissante sur 8 heures n'est servie par aucune des deux sources.** Ni le
  flux temps réel, ni l'API Geod'air, qui s'arrête aux moyennes horaires, aux maximums
  horaires journaliers, aux moyennes journalières et annuelles. Elle se recalcule dans
  `prepare` — donc elle se verrouille par un test, sous peine d'annoncer un chiffre
  « réglementaire » qui ne correspond à aucun décompte officiel.
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

Trois frictions à lever dans `fetch.py`, aucune rédhibitoire :

1. **La clé passe par un en-tête HTTP** (`apikey:`), là où le dépôt ne sait injecter
   `${VAR}` que dans l'URL. À étendre aux en-têtes — et à ne jamais journaliser : une
   commande curl affichée en entier suffirait à rejouer l'incident ENTSO-E.
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
