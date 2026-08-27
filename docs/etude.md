<!--
  ÉTUDE — source éditoriale (compilée vers une page HTML déployée avec outputs/).
  BROUILLON COMPLET (20/07/2026) : les 6 sections et les 7 chapitres sont rédigés, au plan
  validé le même jour. Restent la relecture, le sous-titre à trancher et la compilation HTML.
  Passe du 23/07/2026 sur les sections 1, 2, 6 et le chapitre « 14 heures » : style
  dé-mécanisé (cf. docs/etude.retouche.md), phrase-guide de lecture avant la figure, et
  correction d'exactitude — produit SUR l'île n'est pas produit AVEC les ressources de
  l'île, les 84 % incluent un thermique à combustible importé.
  Passe du 30/07/2026 sur les cinq chapitres restants (T3, T2, T2b, T5, T6) : gabarit
  dé-uniformisé (lede italique supprimé en T3/T2b, phrase-guide passée avant la figure en
  T3), refrain « Pour vous : » fondu dans la prose, tirets cadratins rationnés, chutes de
  paragraphe désamorcées, et deux traces d'enquête à la première personne (arbitrage du
  titre en T5, catalogue ENTSO-E sans zone corse en T6). Les chiffres cités sont
  inchangés — ce sont ceux que verrouillent les tests. Hors passe à ce jour : la
  section 4 (six amorces en gras d'affilée).
  Passe du 23/08/2026 sur les chapitres « midi » (ex-« 14 heures »), T3 et T2b : la courbe
  horaire d'EDF porte l'heure légale corse sous une étiquette `+00:00`, ce qui décalait
  toute heure de la journée d'une heure l'hiver et de deux l'été. Sept verrous de texte ont
  cassé ; les fenêtres ont été REMESURÉES sur la donnée corrigée, jamais translatées — la
  nuit va désormais de 23 h à 7 h, la mi-journée d'été de 12 h à 13 h, le soir d'été de
  18 h à 21 h, et « l'heure la plus verte » devient un créneau, les deux définitions du
  renouvelable ne culminant pas à la même heure.
  Conventions de compilation :
    - {{visuel:nom}}  -> iframe de outputs/nom.html (plotly.min.js mutualisé)
    - blockquote débutant par **Pour aller plus loin** -> encadré repliable (couche initié)
  Règles d'écriture (mémoire projet) : style toujours accessible, y compris couche initié ;
  neutralité sans tiédeur (faits à l'indicatif, zéro prescription politique) ; chiffres en
  prose = uniquement des faits clos verrouillés par tests (verrous « test_etude_* » ajoutés
  le 20/07/2026 dans tests/test_resultats.py — suite complète verte).
-->

# De quoi est faite l'électricité corse ?

*Le soleil, le fioul, les barrages, les câbles : ce qui compose le courant, et quand.*

## 1. L'essentiel en 30 secondes

- Plus du quart de l'électricité consommée en Corse arrive par des câbles
  sous-marins. Le reste est produit sur l'île, en grande partie par des centrales
  thermiques qui brûlent du combustible.
- À midi, le soleil fournit jusqu'à un tiers du courant. Mais même en été, il ne
  dépasse pas le thermique en moyenne.
- Le créneau où l'électricité est la plus renouvelable est entre 12 et 13 heures.
  C'est aussi le moment où la Corse dépend le moins des câbles qui la relient à
  l'extérieur.
- En juillet, la demande augmente de 22 % par rapport à juin, surtout de l'après-midi
  au début de soirée. Mais la consommation la plus forte de l'année reste celle de
  l'hiver.
- Au printemps, la Corse doit parfois limiter sa production solaire parce que le
  réseau ne peut pas tout absorber. Il existe donc déjà, à certains moments, un
  surplus d'énergie renouvelable.
- La Sardaigne voisine fonctionne beaucoup plus souvent que la Corse avec une forte
  part de solaire et d'éolien. Elle produit aussi bien plus d'électricité qu'elle n'en
  consomme, et en exporte.

Tout ce qui suit repose sur des données publiques d'EDF et d'ENTSO-E, mises à jour
plusieurs fois par jour. Chaque graphique indique sa source et sa date. Les chiffres
sont recalculés et vérifiés à chaque mise à jour.

## 2. Pourquoi cette étude

En 2026, la question de l'autonomie de la Corse est débattue jusqu'au Parlement.
Cette étude s'intéresse uniquement à un aspect : l'autonomie électrique.

D'où vient l'électricité consommée en Corse ? Comment sa composition change-t-elle au
cours de la journée et des saisons ? À quel moment repose-t-elle le plus sur les
énergies renouvelables et sur les ressources de l'île ?

L'objectif est de répondre à ces questions avec des chiffres datés et vérifiables,
sans prendre position sur les autres dimensions du débat.

La Corse présente une situation particulière. Contrairement aux grands réseaux
continentaux, qui peuvent s'appuyer sur de nombreux moyens de production répartis sur
un vaste territoire, l'île dispose de connexions limitées avec l'extérieur. À chaque
instant, il faut donc maintenir l'équilibre entre l'électricité disponible et celle
qui est consommée.

Une grande partie de l'électricité est encore produite par des centrales thermiques
qui brûlent du combustible. Le solaire, l'hydroélectricité et l'éolien occupent une
place importante, mais leur développement et leur utilisation dépendent aussi des
capacités d'un réseau électrique de petite taille.

Les données montrent également qu'une part importante de l'électricité consommée en
Corse dépend de l'extérieur. Plus du quart arrive par des câbles sous-marins reliés à
l'Italie via la Sardaigne. Les centrales thermiques de l'île fonctionnent elles-mêmes
avec du combustible importé.

La production qui repose directement sur les ressources disponibles en Corse vient
donc principalement du soleil, de l'eau et du vent. C'est cette part que nous suivrons
au fil des chapitres : à quels moments elle augmente, et à quels moments elle diminue.

Derrière les chiffres du thermique, il y a aussi des installations concrètes : les
centrales situées près d'Ajaccio et de Bastia, qui fonctionnent au fioul. Deux sujets
sont directement liés au système électrique actuel : les émissions de ces centrales et
la disponibilité de l'eau utilisée pour la production hydroélectrique.

Cette étude n'a pas vocation à décrire tout le système électrique corse. Elle se
concentre sur quelques questions précises et ne cherche pas à proposer une politique
énergétique. Elle porte uniquement sur l'électricité, et non sur les transports ou les
autres usages de l'énergie.

Le fil principal peut se lire sans connaissance technique préalable : une question, un
graphique, puis une explication de ce qu'il montre. Les définitions précises, les
nuances méthodologiques et les limites sont regroupées dans des encadrés « pour aller
plus loin ». Chacun peut ainsi choisir son niveau de lecture.

## 3. Ce que disent les données

Avant de regarder d'où vient l'électricité corse au fil de la journée, il faut
distinguer deux chiffres.

{{visuel:t7_dependance_perimetres}}

Le premier concerne toute l'énergie consommée en Corse : électricité, carburants des
transports et chauffage. En 2020, 86 % venaient de l'extérieur.

Le second concerne uniquement l'électricité, qui est le sujet de cette étude. Entre
2019 et 2024, 68 % de l'électricité consommée en Corse dépendait de l'extérieur :
environ 28 % arrivait directement par les câbles sous-marins, tandis que 40 % était
produit sur l'île par des centrales thermiques utilisant du combustible importé.

Les deux chiffres ne portent donc pas sur le même périmètre. Pour la suite, nous nous
concentrerons uniquement sur l'électricité et sur la façon dont elle est produite au fil
des heures et des saisons.

### Au dernier relevé

#### Quelle part de l'électricité corse vient du soleil ?

*La jauge indique la part du solaire au dernier relevé disponible.*

{{visuel:t1_soleil_live}}

Cette jauge montre la part du solaire dans l'électricité produite en Corse au dernier
relevé disponible. L'heure du relevé est indiquée sous le titre.

EDF publie de nouvelles données toutes les quinze minutes et nous les récupérons
plusieurs fois par jour. La jauge reflète donc une situation récente. Elle peut
dépasser 30 % au milieu d'une journée d'été ensoleillée et revient naturellement à
zéro la nuit.

Cette mesure donne une photo à un instant précis. Elle ne permet pas, à elle seule, de
déterminer le meilleur moment pour consommer de l'électricité renouvelable. Pour cela,
le chapitre consacré à midi compare les différentes heures de la journée sur six
années de données.

> **Pour aller plus loin — que mesure exactement la jauge ?** Pour cet indicateur en
> temps réel, nous reprenons la définition utilisée par EDF pour les énergies
> renouvelables « distribuées » : solaire, éolien, bioénergies, petite hydraulique et
> restitution des batteries. Les grands barrages et les échanges par câble ne sont pas
> inclus.
>
> Dans les comparaisons entre périodes présentées plus loin, nous utilisons une
> définition légèrement différente, qui exclut les batteries. Ce choix permet de
> comparer les périodes sur une base identique. Sur les deux semaines vérifiées en
> juillet 2026, la différence entre les deux méthodes est restée inférieure à deux
> points.
>
> **Comment savoir si la donnée est encore récente ?** La jauge affiche l'âge du
> dernier relevé, recalculé au moment où vous ouvrez la page. Au-delà de 12 heures,
> elle signale que la donnée est ancienne ; au-delà de 24 heures, qu'elle est trop
> ancienne pour représenter la situation actuelle.

### Au fil de la journée

#### Même à son zénith, le soleil ne détrône pas le fossile

Une journée d'été moyenne, heure par heure : chaque courbe montre la part d'une
source d'électricité au fil de la journée.

{{visuel:t3_profil_horaire}}

À la mi-journée, entre 12 et 13 heures, le solaire atteint son maximum : 36 % de
l'électricité corse. C'est aussi le moment où le thermique est au plus bas, à 43 %. Il
reste donc la première source d'électricité. Même en été, le solaire ne passe devant à
aucune heure de la journée.

Entre 18 et 21 heures, sa part retombe à 6 %. Le thermique remonte à 58 % et les
câbles à 25 %. Ensemble, ils fournissent alors plus de 80 % de l'électricité.

(Moyennes de juin à août, 2019-2024.)

> **Pour aller plus loin — le plafond qui limite le solaire.** Sur un réseau
> insulaire, les productions intermittentes (soleil et vent sans stockage) sont
> plafonnées en puissance instantanée : 30 % à l'origine (arrêté du 23 avril 2008,
> modifié en 2010), 35 % en Corse depuis 2018. La programmation visait 45 % en 2023,
> mais la révision de juin 2023 n'a pas touché à l'article qui fixe le seuil : celui
> qui s'applique est resté 35 %. Au-delà, le gestionnaire déconnecte des producteurs,
> selon la règle du « dernier arrivé, premier déconnecté » : c'est l'écrêtement, que
> raconte le chapitre du printemps. Les installations couplées à des batteries, elles,
> échappent au plafond. Notre pic d'été à ~36 % évolue au voisinage de ce seuil, mais
> les périmètres de calcul diffèrent : cette proximité n'a pas valeur de démonstration.
>
> Ces chiffres concernent l'été. Dans le chapitre suivant, les calculs portent sur
> toute l'année.

#### Midi : plus de renouvelable, moins d'électricité importée

*À quelle heure vaut-il mieux faire tourner un chauffe-eau, une machine à laver ou
recharger un véhicule ?*

{{visuel:t4_heure_verte}}

Autour de midi, la part des énergies renouvelables atteint son maximum.

Entre 12 et 13 heures, le solaire, l'éolien, les bioénergies et la petite hydraulique
fournissent environ 35 % de l'électricité. En ajoutant les grands barrages, la part
renouvelable atteint 48 %.

C'est également à ce moment que la Corse utilise le moins d'électricité importée par
les câbles sous-marins : leur part descend autour de 15 %, contre plus d'un tiers
pendant une partie de la nuit.

Le thermique reste toutefois important. Autour de midi, il représente encore environ
36 % de l'électricité.

Ces chiffres permettent une distinction utile. Autour de midi, environ 84 % de
l'électricité est produite en Corse. Mais cela ne signifie pas que 84 % repose sur des
ressources corses : environ 36 points viennent du thermique, alimenté par un combustible
importé. Si l'on ne compte que les renouvelables et les barrages, la part produite à
partir de ressources de l'île est d'environ 48 %.

Pour les usages qui peuvent être décalés dans la journée, la période autour de midi
est donc celle où l'électricité est en moyenne la plus renouvelable et la moins
dépendante des importations par câble.

(Moyennes 2019-2024.)

> **Pour aller plus loin — deux chiffres plutôt qu'un.** Le « renouvelable
> décentralisé » (35 %) regroupe le soleil, le vent, les bioénergies et la
> micro-hydraulique : des productions variables, dépendant principalement des
> conditions météorologiques. Les grands barrages, eux, sont renouvelables mais
> pilotables : on les turbine quand le réseau en a besoin, et ils pèsent 14 % du mix
> sur ce créneau. Les compter à part évite de gonfler le chiffre.
>
> Le maximum se situe entre 12 et 13 heures. Selon que l'on inclut ou non les grands
> barrages, l'une ou l'autre heure arrive légèrement en tête. L'écart est trop faible
> pour qu'il soit utile de privilégier précisément 12 h ou 13 h.
>
> Le calcul est simple : la part d'une filière à midi, c'est tout ce qu'elle a produit
> à ces heures-là en six ans, divisé par toute l'électricité appelée à ces heures-là.
> Soit 52 602 heures de données EDF, validées sur 2019-2020 et estimées à partir
> de 2021.
>
> Un résultat moins intuitif apparaît dans les données : à midi, le solaire réduit
> surtout les importations, pas la production thermique. Entre 8 et 13 heures, les
> importations passent d'environ 77 à 43 MW, tandis que la production thermique reste
> proche de 107 MW. La baisse de sa part dans le mix vient donc surtout de
> l'augmentation de la production renouvelable, et non d'un fort ralentissement des
> centrales thermiques.

### Au fil des saisons

#### En juillet, la demande augmente de 22 %

*Comment la consommation d'électricité évolue-t-elle au cours de l'année ?*

{{visuel:t2_demande_mensuelle}}

De juin à juillet, la demande moyenne passe de 231 à 281 MW, soit une hausse de 22 %
en un mois. C'est la plus forte augmentation entre deux mois consécutifs de l'année.

La consommation reste élevée en août, puis diminue en septembre et en octobre.

Mais les niveaux les plus élevés sont observés en hiver. La demande moyenne atteint
environ 307 MW en hiver, notamment en raison des besoins de chauffage. La Corse
connaît donc une hausse importante de sa consommation en été, mais l'hiver reste la
période où la demande est la plus forte.

> **Pour aller plus loin — moyenne et pointe de consommation.** Les valeurs présentées
> ici sont des moyennes mensuelles, calculées à partir des données 2019-2024. Elles ne
> correspondent pas aux pointes de consommation, qui peuvent être beaucoup plus
> élevées pendant quelques heures.
>
> Lorsqu'on compare des chiffres de puissance, il faut donc distinguer une moyenne
> mensuelle ou saisonnière d'une pointe observée à un instant donné.

#### En juillet, la hausse est surtout marquée de 14 h à 20 h

{{visuel:t2b_surcroit_horaire}}

À toutes les heures de la journée, la demande moyenne est plus élevée en juillet qu'en
juin. Mais l'écart est particulièrement important de 14 h à 20 h, avec un maximum vers
17 h.

La hausse commence à s'accentuer dans la matinée, atteint environ 70 MW
supplémentaires pendant l'après-midi et le début de soirée, puis diminue
progressivement pendant la nuit. Elle est la plus faible vers 7 h.

Cette période recouvre en partie les heures de forte production solaire, mais elle se
prolonge aussi en soirée, lorsque la production solaire diminue fortement.

> **Pour aller plus loin — qu'est-ce qui explique cette hausse ?** Ces données
> permettent de voir quand la consommation augmente, mais pas d'en déterminer la
> cause. Le tourisme, la climatisation, les températures ou d'autres facteurs peuvent
> intervenir simultanément.
>
> Pour mesurer leur rôle respectif, il faudrait croiser les données électriques avec
> des données météorologiques et de fréquentation. Ce n'est pas fait ici.

### La production solaire parfois limitée

#### C'est au printemps, pas en été, que la Corse bride son solaire

*À quels moments la production photovoltaïque doit-elle être limitée ?*

{{visuel:t5_ecretement_solaire}}

Les limitations se concentrent surtout au printemps. Entre 2016 et 2023, 81 % des
heures de bridage observées ont eu lieu de mars à juin. Juillet et août représentent, à
l'inverse, moins de 1 % du total.

Le mois le plus marqué est mai 2020, avec 141 heures de limitation pour le producteur
le plus concerné. Cette période correspond au premier confinement, pendant lequel la
demande d'électricité était particulièrement faible.

Les limitations sont également devenues plus fréquentes sur la période étudiée :
54 heures en 2016 contre 356 heures en 2023.

Ces chiffres montrent qu'à certains moments, le réseau corse ne peut pas accepter
toute la production solaire disponible. Ils ne permettent toutefois pas de mesurer
directement la quantité d'électricité qui aurait pu être produite en plus.

> **Pour aller plus loin — que mesure exactement le bridage ?** La donnée publiée par
> EDF indique la durée maximale pendant laquelle un producteur photovoltaïque a été
> limité au cours du mois. Elle ne mesure donc ni le nombre total d'installations
> concernées, ni la quantité d'énergie non produite.
>
> Même en mai 2020, le mois le plus marqué de la période, 90,5 % de l'énergie
> intermittente disponible a été acceptée par le réseau.
>
> Sur 2016-2023, la Corse totalise 2 035 heures de limitation, contre 198 à La Réunion
> et 14 en Guadeloupe ; aucune n'est recensée dans ces données pour la Guyane et la
> Martinique.

#### La Sardaigne dépasse beaucoup plus souvent le niveau de 35 %

*Un réseau insulaire peut-il fonctionner avec beaucoup plus de solaire et d'éolien ?*

{{visuel:t6b_seuil_35}}

En Corse, le gestionnaire peut limiter certaines productions solaires et éoliennes sans
stockage afin de maintenir leur part instantanée sous le seuil réglementaire de 35 %.

Les données disponibles ne permettent pas d'isoler exactement ces installations. Nous
mesurons donc un indicateur plus large : la part cumulée de l'ensemble du solaire et de
l'éolien.

En 2024, la part cumulée du solaire et de l'éolien a dépassé 35 % pendant environ 15 % des
heures en Corse. En Sardaigne, selon le dénominateur retenu, cette proportion se situe
entre 36 et 52 %.

En Sardaigne, ces dépassements ne sont pas ponctuels : ils durent huit heures en médiane,
et le plus long de 2024 a dépassé trois jours.

Les deux systèmes électriques sont très différents. La Sardaigne produit chaque année
environ 45 % de plus qu'elle ne consomme, alors que la Corse reçoit plus du quart de son
électricité par les câbles sous-marins.

La Corse tire environ un quart de sa production locale de ses barrages, contre presque
rien en Sardaigne. À l'inverse, l'éolien représente environ 16 % en Sardaigne contre 2 %
en Corse. Le solaire occupe une place proche dans les deux cas : 16 % en Corse et 14 % en
Sardaigne.

Les flux de SAPEI permettent aussi de voir ce qui se passe pendant ces périodes. Pendant
les heures où solaire et éolien dépassent 35 %, SAPEI est en
export 96 % du temps. Le flux moyen atteint 530 MW, contre 86 MW pendant les autres
heures, tandis que la consommation sarde varie peu. Une partie de la production
supplémentaire est donc évacuée vers le continent.

Cette comparaison ne montre pas que la Corse pourrait relever son seuil à conditions
inchangées. Les deux réseaux diffèrent notamment par leurs interconnexions et par leur
équilibre entre production et consommation. Elle montre seulement que 35 % n'est pas une
limite générale propre à tous les réseaux insulaires.

> **Pour aller plus loin — pourquoi deux courbes pour la Sardaigne ?** La règle corse
> rapporte la production solaire et éolienne à « la puissance transitant sur le réseau ».
> En Corse, cette quantité est celle qui alimente la consommation de l'île, importations
> comprises. En Sardaigne, les deux ne coïncident pas : l'île produit bien plus qu'elle
> ne consomme. Nous donnons donc les deux calculs plutôt que d'en choisir un
> arbitrairement. L'écart entre eux est important, mais il ne change pas la conclusion :
> même le calcul le plus bas place la Sardaigne nettement au-dessus de la Corse.
>
> Les données corses viennent d'EDF, les données sardes d'ENTSO-E, qui publie les données
> du système électrique européen. L'analyse des flux porte sur SAPEI, principale liaison
> entre la Sardaigne et le continent italien ; les liaisons SACOI et SARCO ne sont pas
> incluses.
>
> Ni l'une ni l'autre source ne permet de distinguer les installations équipées de
> stockage, que la règle corse exclut du calcul. Les parts présentées ici portent donc sur
> l'ensemble du parc solaire et éolien, et non sur le périmètre réglementaire exact.

Pour situer cette comparaison, voici comment se répartit la production locale des deux
îles en 2024.

{{visuel:t6_corse_sardaigne}}

## 4. Et maintenant ?

Le système électrique corse est en train d'évoluer. Plusieurs projets engagés
aujourd'hui modifieront sa production dans les prochaines années.

À Ajaccio, la centrale du Vazzio doit être remplacée par une nouvelle centrale au
Ricanto. Prévue pour fonctionner à l'huile de colza, elle doit remplacer le fioul
lourd. EDF prévoit une mise en service d'ici fin 2027 et annonce une forte baisse des
émissions de CO₂. À Bastia, une conversion de la centrale de Lucciana à la biomasse
est également envisagée. *(Source : EDF, novembre 2024.)*

Ce changement réduirait l'utilisation de combustibles fossiles, mais pas
nécessairement la dépendance aux approvisionnements extérieurs. Le colza destiné au
Ricanto — environ 200 000 tonnes par an — devra en grande partie être importé : selon
EDF, « la Corse seule ne dispose pas des ressources nécessaires ». Dans le même temps,
la liaison électrique avec la Sardaigne doit être renforcée.

Il faut donc distinguer deux choses : produire l'électricité en Corse et la produire à
partir de ressources disponibles en Corse. Les deux ne se confondent pas.

La question de la qualité de l'air est également liée aux centrales thermiques,
notamment autour d'Ajaccio et de Bastia. Les données utilisées dans cette étude ne
permettent toutefois pas de mesurer leur effet sur la pollution de l'air, ni de le
distinguer de celui d'autres sources comme le trafic maritime.

### L'hydraulique varie fortement selon les années

Les barrages jouent un rôle important dans la production corse : ils fournissent environ
un quart de ce que l'île produit elle-même. Mais leur contribution varie beaucoup d'une
année à l'autre.

{{visuel:t9_hydro_secheresse}}

Entre 2019 et 2024, la grande hydraulique représente selon les années 12 à 22 % de
l'électricité consommée. Le thermique évolue dans le sens inverse : lorsque la part de
l'hydraulique est faible, sa part tend à être plus élevée.

Le contraste est particulièrement marqué en 2022 : l'hydraulique tombe à 12 %, son
niveau le plus bas de la période, tandis que le thermique atteint 48 %, son niveau le
plus élevé. En 2023, l'hydraulique remonte à 22 % et le thermique descend à 35 %.

Cette relation est très forte sur les six années observées, mais elle ne suffit pas à
démontrer que le manque d'eau provoque directement la hausse du thermique. Le
graphique ne contient aucune donnée sur les précipitations ou le niveau des barrages.
Pour établir ce lien, il faudrait ajouter ces données à l'analyse.

### Plusieurs évolutions sont déjà engagées

Batteries, stockage hydraulique, nouvelles installations solaires et renforcement des
câbles avec l'extérieur font partie des solutions envisagées ou déjà engagées.

Cette étude ne cherche pas à déterminer laquelle est préférable. Elle montre simplement
les contraintes auxquelles elles répondent : production solaire parfois limitée au
printemps, forte dépendance au thermique, variations de l'hydraulique et recours
important aux interconnexions.

### Ce que ces données ne disent pas

Cette étude ne mesure pas le coût de production de l'électricité en Corse ni la qualité
de l'air. Elle ne permet pas non plus de prévoir précisément l'évolution du système
électrique. Ces questions nécessitent d'autres données et d'autres analyses.

## 5. La méthode en clair

Les données de cette étude sont téléchargées directement auprès de leurs producteurs,
puis préparées et contrôlées automatiquement.

Trois étapes sont appliquées à chaque mise à jour.

- **Collecter les données.** Les fichiers sont téléchargés directement depuis EDF ou
  ENTSO-E. Leur origine, leur date de collecte et leur licence sont enregistrées. Les
  fichiers incomplets ou incorrects sont rejetés.
- **Préparer et contrôler.** Les données sont mises dans un format commun, les heures
  sont harmonisées et plusieurs contrôles vérifient leur cohérence. Une valeur
  manquante ou une catégorie inconnue n'est pas corrigée automatiquement : elle doit
  d'abord être examinée.
- **Produire les graphiques.** Les figures sont générées automatiquement à partir des
  données préparées. La source et la date de collecte sont ajoutées à chaque graphique.

Les données sont mises à jour plusieurs fois par jour. Si une source n'est
temporairement pas disponible, la dernière version complète est conservée plutôt que
d'utiliser un fichier incomplet.

Les principaux résultats sont également contrôlés automatiquement. Si une mise à jour
modifie sensiblement un chiffre utilisé dans le document — par exemple les 22 % de
hausse en juillet ou le créneau autour de midi — la publication est interrompue jusqu'à
vérification.

Cela permet d'éviter qu'une modification des données ou du traitement change
silencieusement les conclusions présentées ici.

### Les principales sources

| Donnée | Producteur | Période | Licence |
| --- | --- | --- | --- |
| Mix électrique corse en temps réel | EDF | environ 14 derniers jours | Licence Ouverte 2.0 |
| Production électrique corse par filière | EDF | 2019-2024 | Licence Ouverte |
| Limitations du photovoltaïque | EDF | 2016-2023 | Licence Ouverte 2.0 |
| Production électrique de la Sardaigne | ENTSO-E | 2019-2024 | CC-BY 4.0 |

La date de collecte utilisée apparaît au bas de chaque graphique.

## 6. Définitions et limites

Quelques précisions sont nécessaires pour interpréter correctement les chiffres de
cette étude.

### Deux façons de compter les renouvelables

Le renouvelable décentralisé regroupe le solaire, l'éolien, les bioénergies et la
petite hydraulique. Autour de midi, il représente environ 35 % de l'électricité.

En ajoutant les grands barrages, également renouvelables mais pilotables, cette part
atteint environ 48 %.

Les deux valeurs sont donc précisées lorsqu'elles sont utilisées.

### Produire en Corse ne signifie pas utiliser une ressource corse

Une centrale thermique située en Corse produit bien son électricité sur l'île, mais
elle utilise un combustible importé.

Le document distingue donc :

- l'électricité importée par les câbles ;
- l'électricité produite en Corse ;
- l'électricité produite en Corse à partir de ressources locales.

Autour de midi, ces distinctions sont importantes : environ 15 % de l'électricité
arrive par les câbles, tandis que 48 % proviennent des renouvelables et des barrages
de l'île.

### Une partie des données EDF est estimée

EDF classe les données 2019-2020 comme validées et celles de 2021-2024 comme estimées.

Nous avons vérifié séparément les deux périodes : les principaux résultats présentés
dans cette étude, notamment la hausse de juillet et le maximum renouvelable autour de
midi, apparaissent dans les deux.

### Les heures ont nécessité une vérification particulière

Les données historiques d'EDF comportent une ambiguïté sur le fuseau horaire utilisé.
Plusieurs contrôles indépendants ont permis de confirmer que les heures doivent être
interprétées comme des heures légales en Corse.

Cette vérification a conduit à corriger une première version de l'étude qui situait à
tort certains résultats deux heures plus tard.

Les détails de cette vérification sont disponibles dans la note méthodologique.

### Quelques heures particulières ont été exclues

Les calculs 2019-2024 utilisent 52 602 heures de données.

Six heures correspondant aux passages à l'heure d'été ont été retirées car leur
traitement dans les fichiers EDF n'est pas cohérent d'une année à l'autre.

### La petite hydraulique manque dans les données 2024

La catégorie « petite hydraulique » n'apparaît plus dans les données EDF pour 2024.
Les vérifications effectuées montrent qu'elle n'est pas non plus incluse dans le total
publié pour cette année.

Cette absence est donc prise en compte dans les calculs plutôt que corrigée
artificiellement.

### Le bridage solaire est mesuré en heures

Les données sur les limitations photovoltaïques indiquent une durée de limitation, et
non une quantité d'électricité perdue.

Elles permettent donc de savoir quand les limitations sont fréquentes, mais pas de
calculer directement l'énergie qui aurait pu être produite.

### Corse et Sardaigne : les échanges sont retirés

Pour comparer les deux îles, seules leurs productions locales sont prises en compte.
Les importations et exportations sont exclues.

Les données corses viennent d'EDF et les données sardes d'ENTSO-E.

### La Corse n'importe pas à chaque instant

Sur l'ensemble des six années étudiées, la Corse importe davantage d'électricité
qu'elle n'en exporte. Elle a cependant également exporté pendant 607 heures, soit un
peu plus de 1 % du temps.

Lorsque ce document parle de dépendance aux câbles, il s'agit donc d'une situation
moyenne, pas d'une règle valable à chaque heure.

### Cette étude porte uniquement sur l'électricité

Les carburants utilisés dans les transports et les combustibles utilisés directement
pour le chauffage ne sont pas inclus.

L'autonomie électrique et l'autonomie énergétique sont donc deux questions
différentes.

### Les périodes couvertes ne sont pas toutes les mêmes

Les données historiques de production couvrent 2019 à 2024. Les données en temps réel
utilisées par la jauge commencent en 2026. La période intermédiaire n'est pas utilisée
pour relier les deux séries.

Les données sur le bridage photovoltaïque s'arrêtent quant à elles en 2023, dernière
année disponible dans la source utilisée.

### Sources et réutilisation

Les données EDF et ENTSO-E utilisées ici sont publiées sous licences ouvertes. Chaque
graphique indique sa source et la date à laquelle les données ont été collectées.
