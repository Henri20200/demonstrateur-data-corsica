<!--
  ÉTUDE — source éditoriale (compilée vers une page HTML déployée avec outputs/).
  BROUILLON COMPLET (20/07/2026) : les 6 sections et les 7 chapitres sont rédigés, au plan
  validé le même jour. Restent la relecture, le sous-titre à trancher et la compilation HTML.
  Passe du 23/07/2026 sur les sections 1, 2, 6 et le chapitre « 14 heures » : style
  dé-mécanisé (cf. docs/etude.retouche.md), phrase-guide de lecture avant la figure, et
  correction d'exactitude — produit SUR l'île n'est pas produit AVEC les ressources de
  l'île, les 84 % incluent un thermique à combustible importé. Les cinq autres chapitres
  n'ont PAS encore reçu la passe de style.
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

- Plus du quart de l'électricité corse vient de câbles sous-marins. Le reste est
  produit sur l'île — en grande partie par des centrales thermiques qui brûlent du
  combustible.
- À midi, le soleil fournit jusqu'à un tiers du courant. Mais à aucune heure moyenne
  d'été il ne dépasse le thermique.
- L'heure la plus verte pour consommer, c'est **14 heures**. C'est aussi l'heure où
  l'île dépend le moins de ses câbles.
- En juillet, la demande grimpe d'un cinquième par rapport à juin — surtout le soir.
  Pourtant, la pointe de l'année reste l'hiver.
- Au printemps, l'île bride parfois son propre solaire, faute de pouvoir l'absorber :
  le trop-plein d'énergie verte existe déjà.
- La Sardaigne voisine est, elle aussi, une île thermique — mais elle brûle du
  charbon là où la Corse tient au fioul et à l'eau de ses montagnes.

Tout ce qui suit repose sur des données publiques d'EDF et d'ENTSO-E, rafraîchies
chaque semaine. Chaque graphique porte sa source et sa date ; chaque chiffre est
revérifié à chaque mise à jour.

## 2. Pourquoi cette étude

En 2026, l'autonomie de la Corse se débat jusqu'au Parlement. Ce document ne parle
que d'autonomie électrique. De quoi le courant corse est-il fait, maintenant, au fil
de la journée et au fil des saisons, et à quel moment est-il le plus renouvelable et
le plus insulaire ? Il répond par des chiffres datés et vérifiables, et ne prend
parti sur rien d'autre.

La question mérite qu'on s'y arrête, parce que la Corse est une île peu reliée au
continent. Un grand réseau mutualise ses moyens sur des milliers de kilomètres ;
l'île, elle, doit équilibrer presque seule, à chaque instant, ce qu'elle produit et
ce qu'elle consomme. L'électricité ne se stocke pas. Son courant vient encore
largement de centrales thermiques qui brûlent du combustible, tandis que le soleil,
l'eau des montagnes et le vent, bien réels, restent contraints par la taille du
réseau.

Une chose nous a frappés en assemblant ces données : la part vraiment insulaire est
plus mince qu'on ne l'imagine. Plus du quart de l'électricité arrive par des câbles
sous-marins, depuis l'Italie via la Sardaigne. Et le thermique local tourne lui-même
à un combustible importé. Ne reste pleinement produit sur l'île que ce que donnent
les renouvelables et les barrages. C'est cette part que nous suivons de chapitre en
chapitre : quand elle monte, quand elle retombe.

Ce thermique n'a rien d'une abstraction comptable. Ce sont des centrales bien
réelles, aux portes d'Ajaccio et de Bastia, qui brûlent du fioul. Deux réalités très
concrètes s'y accrochent : l'air que respirent ces villes, et l'eau des montagnes
dont dépendent les barrages, que le climat raréfie.

Reste à dire ce que cette étude ne fait pas. Elle n'est pas exhaustive : elle
éclaire quelques questions précises, pas tout le système électrique corse. Elle ne
prescrit rien. Et elle ne parle que d'électricité, pas de transports ni de
chauffage.

Le fil principal se lit sans prérequis : une question, un graphique, ce qu'on y
voit, ce que ça change pour vous. Les définitions exactes, les nuances et les
limites attendent dans les encadrés « pour aller plus loin ». Deux lectures dans un
seul document, chacun s'arrête où il veut.

## 3. Ce que disent les données

<!-- PROVISOIRE (28/07) — carton d'ouverture du fil rouge (dépendance aux câbles).
     Position et opportunité à confirmer ; retirer la balise ou la déplacer si non retenu. -->
{{visuel:cadrage_dependance}}

### Maintenant

#### Ce que produit l'île, là, tout de suite

*Ouvrez la jauge : elle dit de quoi votre électricité est faite en ce moment.*

{{visuel:t1_soleil_live}}

Cette jauge est le seul visuel « en direct » de l'étude : elle affiche la part du
soleil dans l'électricité corse au dernier relevé, actualisé toutes les quinze
minutes par EDF. Un après-midi d'été ensoleillé, elle dépasse souvent le tiers ;
une fois la nuit tombée, elle revient à zéro — c'est le même système que racontent
les chapitres suivants, vu depuis l'instant présent.

Le réflexe à prendre : un coup d'œil avant de lancer ce qui peut attendre. Si la
jauge est haute, c'est le moment.

> **Pour aller plus loin — ce que compte exactement la jauge.** Le chiffre reprend
> la convention d'EDF pour le renouvelable « distribué » en direct : soleil, vent,
> bioénergies, petite hydraulique et la restitution des batteries — hors grands
> barrages et hors câbles. C'est la définition du producteur, conservée telle
> quelle pour l'instantané. Les comparaisons entre périodes, ailleurs dans
> l'étude, utilisent une définition légèrement plus stricte (sans les batteries),
> identique des deux côtés de chaque comparaison ; l'écart maximal observé entre
> les deux est resté sous les deux points (fenêtre de deux semaines examinée en
> juillet 2026).
>
> **La fraîcheur est surveillée, pas supposée.** Au-delà de 24 heures sans relevé,
> la figure affiche un avertissement ; au-delà de 48 heures, elle renonce
> d'elle-même au « en ce moment » et se dégrade en « au dernier relevé du… ». Une
> donnée en direct qui ne dit pas son âge ne mérite pas votre confiance.

### Au fil de la journée

#### Même à son zénith, le soleil ne détrône pas le fossile

*Suivons une journée d'été moyenne, heure par heure.*

{{visuel:t3_profil_horaire}}

L'été, à la mi-journée, le solaire culmine à 35 % du mix — et le thermique, même à
son creux, reste au-dessus : 43 %. À aucune heure moyenne d'été le soleil ne passe
devant. Le soir, le contraste est brutal : le solaire retombe à 6 %, le thermique
monte à 58 % et les câbles à 25 % — plus de huit dixièmes du
kilowattheure du soir sortent des moteurs et des câbles. (Toutes ces valeurs :
moyennes de juin à août, 2019-2024.)

Ce que ça change pour vous : les soirées d'été sont le moment le moins insulaire
et le moins renouvelable de la journée. Ce qui peut glisser vers l'après-midi y
gagne.

> **Pour aller plus loin — pourquoi ce plafond n'est pas un manque de panneaux.**
> Sur un réseau insulaire, les productions intermittentes (soleil et vent sans
> stockage) sont plafonnées réglementairement en puissance instantanée : 30 % à
> l'origine (arrêté du 23 avril 2008, modifié en 2010), seuil relevé depuis à 35 %
> puis 45 % en Corse. Au-delà, le gestionnaire déconnecte des producteurs — règle
> du « dernier arrivé, premier déconnecté » : c'est l'écrêtement, que raconte le
> chapitre du printemps. La sortie par le haut passe par le stockage (les
> installations couplées à des batteries échappent au plafond). Notre pic d'été à
> ~35 % évolue au voisinage de ces seuils ; les périmètres de calcul diffèrent :
> on y voit une cohérence, pas une preuve.
>
> **Attention au changement de focale.** Ce chapitre décrit l'été. Le suivant se
> calcule sur toute l'année : les pourcentages ne se comparent pas terme à terme
> d'un chapitre à l'autre.

#### 14 heures : l'heure la plus verte — et la plus corse

*Si vous pouviez choisir l'heure du chauffe-eau, d'une lessive ou d'une recharge,
laquelle faudrait-il viser ?*

Les quatre bandes empilées font 100 % du courant, heure par heure. Les deux du bas,
renouvelables et barrages, sont la seule électricité pleinement insulaire ; viennent
ensuite les centrales thermiques, qui brûlent un combustible importé, puis tout en
haut les câbles sous-marins.

{{visuel:t4_heure_verte}}

Quatorze heures. Sur six ans de moyennes, c'est le moment où l'électricité corse est
la plus verte : 34 % viennent du soleil, du vent, des bioénergies et des petites
centrales au fil de l'eau, 48 % si l'on ajoute les grands barrages. Le classement ne
bouge pas : 14 heures, puis 15, puis 13. Il résiste au changement de définition du
renouvelable comme au changement de période, puisque 14 heures ressort aussi bien
sur 2019-2020 que sur 2021-2024.

Reste à mesurer ce que « la plus verte » veut dire. Entre son maximum de 5 heures du
matin et 14 heures, le thermique ne recule que de 44 à 36 %, soit près d'un cinquième
de moins. Il reste la première source de la journée : à aucune heure de l'année
moyenne, le renouvelable décentralisé ne passe devant lui. Ce n'est qu'en comptant les
grands barrages que le total renouvelable le dépasse, entre 11 heures et 16 heures.

C'est aussi l'heure où votre kilowattheure vient le plus de l'île, à condition de
s'entendre sur le mot. Regardez la bande du haut, celle des câbles sous-marins :
elle tombe à 15 % à 14 heures, son minimum de la journée, alors qu'elle dépasse le
tiers en pleine nuit. Les 84 % restants sortent bien de machines installées en
Corse. Mais 36 de ces 84 points sont thermiques, et le fioul qu'ils brûlent arrive
lui aussi par bateau. Si l'on ne compte que ce qui est produit avec des ressources
de l'île, il reste les 48 % de renouvelables et de barrages.

Décaler vers le début d'après-midi ce qui peut l'être, c'est donc consommer plus
renouvelable et plus local.

> **Pour aller plus loin — deux chiffres plutôt qu'un.** Le « renouvelable
> décentralisé » (34 %) regroupe le soleil, le vent, les bioénergies et la
> micro-hydraulique : des productions dispersées que personne ne pilote, qui donnent
> ce que la météo donne. Les grands barrages, eux, sont renouvelables mais
> pilotables : on les turbine quand le réseau en a besoin, et ils pèsent 14 % du mix
> à cette heure. Les compter à part évite de gonfler le chiffre. Vous ne lirez
> jamais ici « renouvelable » tout court.
>
> Le calcul est simple : la part d'une filière à 14 heures, c'est tout ce qu'elle a
> produit à cette heure-là en six ans, divisé par toute l'électricité appelée à cette
> heure-là. Soit 52 605 heures de données EDF, validées sur 2019-2020 et estimées à
> partir de 2021.
>
> Une hypothèse nous est restée sur les bras. Nous pensions qu'à 14 heures les
> moteurs des centrales tournaient au ralenti, et nous nous apprêtions à l'écrire. Le
> calcul dit l'inverse : en volume, le thermique est au plus bas vers 5 heures du
> matin, et il tient en journée un socle presque constant, autour de 104 MW. En part
> du mix, il frôle son plus bas à 14 heures : 36 %, contre 44 % à l'aube. Ce que
> le soleil de la mi-journée remplace d'abord, ce sont les importations. Entre
> 9 heures et 14 heures, elles reculent de 80 à 44 MW pendant que le thermique ne
> bouge pas. Ce qui s'améliore à 14 heures, c'est donc la composition de votre
> kilowattheure, pas l'activité de la centrale. Consommer à cette heure-là, c'est
> surtout consommer moins de câble.

### Au fil des saisons

#### L'été, la demande grimpe de 22 %

*Que voit-on arriver en juillet ?*

{{visuel:t2_demande_mensuelle}}

De juin à juillet, la demande moyenne d'électricité bondit de 231 à 281 mégawatts :
+22 % en un mois, la plus forte marche de l'année. L'été entier
se tient au-dessus du printemps. Mais la surprise est ailleurs : la saison la plus
haute reste l'hiver — 307 MW de moyenne. L'île a deux pics : le
chauffage d'hiver, et l'été.

Pour vous : quand on dit que l'île « sature » en été, voilà le chiffre exact du
surcroît — un cinquième de plus en un mois.

> **Pour aller plus loin — moyennes et pointes.** Ces 231, 281 et 307 MW sont des
> moyennes (toutes les heures du mois ou de la saison, années 2019-2024). Les
> pointes instantanées montent bien plus haut et ne se comparent pas à ces
> moyennes : quand un chiffre de puissance circule, vérifiez toujours de quelle
> famille il est — moyenne ou pointe, mois ou saison, quelle période.

#### Ce surcroît se joue surtout le soir

*Le surplus de juillet arrive à quelle heure ?*

{{visuel:t2b_surcroit_horaire}}

En comparant chaque heure de juillet à la même heure de juin, le surcroît est là
du matin au soir — positif aux 24 heures — mais il n'est pas uniforme : il culmine
en soirée (entre 16 h et 22 h) et reste fort en pleine nuit.

Pour vous : en juillet, la soirée cumule tout — le creux solaire et le surcroît de
demande. C'est là que le conseil du chapitre « 14 heures » vaut double.

> **Pour aller plus loin — pourquoi nous ne nommons pas la cause.** Touristes ?
> Climatisation nocturne ? Les deux arrivent ensemble en juillet, et ces données
> ne permettent pas de les départager — il faudrait croiser météo et fréquentation,
> hors du périmètre de cette étude. Nous montrons le « quand » ; le « pourquoi »
> reste ouvert, et chacun peut se faire son idée.

### La ressource bridée, et la voisine

#### C'est au printemps, pas en été, que la Corse bride son solaire

*Peut-on avoir trop de soleil ?*

{{visuel:t5_ecretement_solaire}}

Oui — et pas quand on croit. 81 % des heures de bridage du solaire se concentrent
de mars à juin, avec un pic en mai ; juillet et août comptent pour moins de 1 %.
Le mécanisme : au printemps, le soleil est déjà généreux mais la demande est
molle — le trop-plein menace l'équilibre du réseau, alors des producteurs sont
temporairement déconnectés. Le record : mai 2020, 141 heures de limitation pour le
producteur le plus exposé, un mois de confinement où la demande s'était effondrée.
Et la tendance monte — 54 heures sur l'année 2016, 356 en 2023 —
à mesure que le parc solaire grandit sous le plafond d'injection.

Pour vous : l'île connaît déjà des heures « trop vertes », du soleil refusé faute
de pouvoir l'absorber à cet instant. La question n'est plus seulement d'installer
des panneaux : c'est de stocker, et de consommer au bon moment.

> **Pour aller plus loin — ce que mesure « durée de bridage ».** La donnée EDF
> compte la durée maximale de limitation subie par UN producteur (le « dernier
> arrivé en file », déconnecté en premier) — pas l'énergie perdue par le système.
> Même au pire mois (mai 2020), 90,5 % de l'énergie intermittente proposée a été
> acceptée. Titrer « l'énergie verte perdue de la Corse » serait abusif : nous ne
> le faisons pas.
>
> **La Corse concentre l'essentiel du bridage des zones non interconnectées
> d'EDF** : 2 035 heures cumulées sur 2016-2023, contre 198 à La Réunion, 14 en
> Guadeloupe, 0 en Guyane et en Martinique — le revers de la croissance de son
> parc solaire sous le plafond d'injection (chapitre précédent).

#### Deux îles thermiques — mais la Sardaigne brûle du charbon

*Et la voisine, à douze kilomètres ?*

{{visuel:t6_corse_sardaigne}}

À périmètre comparable — la seule production locale de chacune —, les deux îles
restent dominées par le thermique : 55 % en Corse, 65 % en Sardaigne.
Mais le détail sépare deux mondes. Le
thermique sarde, c'est un tiers de charbon et un tiers de gaz de synthèse
industriel ; le corse, du fioul. Et chaque île a sa ressource : la Corse tire
28 % de ses montagnes (hydraulique) là où la Sardaigne n'en tire que 4 % —
mais la Sardaigne récolte 15 % de vent, quinze fois la part
corse.

Pour vous : deux îles voisines, deux systèmes — l'insularité n'est pas un destin
unique.

> **Pour aller plus loin — pourquoi « génération locale seule ».** La comparaison
> exclut les importations corses (27,8 % de la demande sur 2019-2024) : la
> Sardaigne, elle, exporte structurellement vers l'Italie par ses câbles. Inclure
> les imports d'un côté et pas de l'autre fausserait tout — on compare donc ce que
> chaque île produit, ramené à 100 %. Le thermique corse, ce sont les centrales au
> fioul du Vazzio (Ajaccio) et de Lucciana (Bastia) — leur remplacement est en
> cours, voir « Et maintenant ? ».
>
> **Les données sardes.** Plateforme de transparence d'ENTSO-E (le réseau des
> gestionnaires de réseaux européens), zone « IT-Sardinia », production réelle par
> filière 2019-2024, reconstruite au pas horaire puis agrégée comme les données
> corses (même fuseau). Les filières européennes sont rapprochées des catégories
> EDF ; le détail — dont le gaz de synthèse de la raffinerie sarde — est documenté
> dans la note de méthode, et les chiffres du titre sont verrouillés par des tests
> automatiques.

## 4. Et maintenant ?

Ces données décrivent le système d'aujourd'hui. Or il change — et les chantiers en
cours dessinent déjà la Corse électrique des prochaines années.

**Le grand basculement : le fioul remplacé.** À Ajaccio, la centrale du Vazzio —
l'une des dernières d'Europe à fonctionner au fioul lourd — doit être remplacée
d'ici fin 2027 par une centrale voisine, au Ricanto, brûlant de l'huile de colza.
EDF y investit 800 millions d'euros et annonce une part renouvelable qui passerait
« d'un tiers à deux tiers », avec des émissions de CO₂ réduites des deux tiers. À
Bastia, la centrale de Lucciana, plus récente, pourrait à son tour se convertir à la
biomasse. *(Source : EDF, novembre 2024.)*

**Mais « renouvelable » ne veut pas dire « autonome ».** Le colza du Ricanto —
environ 200 000 tonnes par an — sera importé : « la Corse seule ne dispose pas des
ressources nécessaires », reconnaît EDF. Et dans le même temps, le câble qui relie
l'île à la Sardaigne va être renforcé (300 à 400 millions d'euros). Le mix se
verdit ; la dépendance aux approvisionnements extérieurs, elle, demeure. Le fil
rouge de cette étude ne se dénoue pas avec la couleur du combustible.

**Un enjeu de proximité : l'air.** Remplacer une vieille centrale au fioul lourd aux
portes d'une ville n'est pas qu'une affaire de climat : c'est aussi une affaire d'air
respiré. Ces données ne mesurent pas la qualité de l'air — c'est un autre métier, et
d'autres sources — et elles ne disent rien du trafic maritime, qui pèse lui aussi sur
l'air des ports corses. Ce qu'elles situent, c'est la combustion : quand les
centrales tournent, et combien.

**La toile de fond : un climat qui se tend.** Le réchauffement pèse sur la ressource
en eau de l'île. Selon l'hydrobiologiste Antoine Orsini (université de Corse), le
débit des cours d'eau a reculé de 25 à 30 % depuis le milieu des années 1980. Or
l'hydraulique fournit près du quart de l'électricité produite sur l'île : moins
d'eau, c'est mécaniquement plus de thermique. Le climat n'est pas qu'un décor
lointain — il touche directement le mix.

<!-- PROVISOIRE (28/07) — T7 illustre l'anticorrélation eau/thermique année par année.
     Position et opportunité à confirmer ; retirer la balise ou la déplacer si non retenu. -->
{{visuel:t7_hydro_secheresse}}

**Des pistes, au conditionnel.** Plusieurs leviers sont étudiés ou engagés pour
desserrer la contrainte : le stockage (batteries, et une station de pompage entre
deux barrages, qui turbine l'eau aux heures de forte demande et la remonte aux heures
creuses), la poursuite du solaire, le renforcement des interconnexions. Ce document
ne les évalue pas ; il constate qu'ils existent, et que la question posée par nos
données — produire plus local, consommer au bon moment — leur donne un sens concret.

**Ce que ces données ne disent pas.** Elles ne chiffrent pas le coût de l'électricité
corse — plus chère à produire que sur le continent, mais c'est une autre source.
Elles ne mesurent pas la qualité de l'air. Elles ne prédisent pas l'avenir. Elles
décrivent un présent, précisément et honnêtement. Le reste — les choix — ne se lit
pas dans un graphique.

## 5. La méthode en clair

Tout ce que ce document affirme peut se vérifier. Voici comment c'est fabriqué,
sans jargon.

**Trois étapes, toujours les mêmes.**

1. **Collecter.** Un programme télécharge chaque source directement chez son
   producteur. À l'arrivée, il calcule l'empreinte numérique du fichier (une
   signature dont le moindre octet modifié change la valeur) et consigne tout dans
   un manifeste : adresse, producteur, licence, date de collecte, taille,
   empreinte. Une réponse suspecte — une page d'erreur déguisée en fichier de
   données, cela arrive — est rejetée avant d'être enregistrée.
2. **Préparer.** Les fichiers bruts deviennent des tables propres : heures
   converties en heure locale, filtres et contrôles appliqués. Ces contrôles sont
   volontairement bloquants : une valeur absente est examinée (zéro réel, ou trou
   de collecte ?) au lieu d'être remplacée en silence ; une catégorie inconnue
   arrête tout au lieu de passer inaperçue ; un millésime incomplet fait échouer
   la préparation au lieu de fausser les moyennes.
3. **Dessiner.** Chaque figure sort par une seule porte, qui incruste d'office la
   source et la date de collecte au pied de l'image. Le sourçage n'est pas une
   bonne pratique qu'on essaie de tenir : il est câblé — une figure sans source ne
   peut pas exister ici.

**Le rafraîchissement est automatique.** La chaîne complète se relance chaque
semaine, sans intervention : données en temps réel re-téléchargées, visuels
regénérés, manifeste réécrit. Si une source échoue, sa version précédente est
conservée telle quelle — jamais de fichier à moitié remplacé.

**Chaque chiffre publié est verrouillé.** Tous les chiffres de ce document et des
visuels sont couverts par des tests automatiques : si une mise à jour des données
déplace un résultat — l'heure la plus verte cesse d'être 14 h, le bond de juillet
quitte les 22 % — la publication échoue, et l'écart doit être examiné avant toute
remise en ligne. Un chiffre affiché ici est revérifié à chaque rafraîchissement,
pas relevé une fois pour toutes.

**Les sources.**

| Donnée | Producteur | Période | Licence |
| --- | --- | --- | --- |
| Mix électrique corse en temps réel (pas de 15 min) | EDF (open data) | fenêtre glissante d'environ 14 jours | Licence Ouverte 2.0 (Etalab) |
| Production corse heure par heure, par filière | EDF (open data) | 2019-2024 | Licence Ouverte (Etalab) |
| Limitations imposées au photovoltaïque (écrêtement) | EDF (open data) | 2016-2023 | Licence Ouverte 2.0 (Etalab) |
| Production sarde par filière | ENTSO-E (plateforme de transparence des réseaux européens) | 2019-2024 | CC-BY 4.0 |

La date de collecte, elle, vit au pied de chaque visuel — elle avance d'elle-même
avec le rafraîchissement hebdomadaire.

## 6. Définitions & limites

Ce que ce document ne dit pas est aussi cadré que ce qu'il dit. Les limites
ci-dessous ne sont pas des excuses : ce sont les bornes de validité exactes de
chaque affirmation.

**« Renouvelable » : toujours qualifié.** Le renouvelable décentralisé (34 % à
14 heures) regroupe solaire, éolien, bioénergies et petite hydraulique. Les grands
barrages, renouvelables mais pilotables, sont comptés à part (48 % en les
ajoutant). Ce document ne dit jamais « renouvelable » tout court : selon la
définition, le chiffre change presque du simple au double.

**Produit sur l'île n'est pas produit avec l'île.** Quand ce document dit qu'une
part est « produite sur l'île », il parle de l'endroit où tournent les machines,
pas de l'origine de l'énergie : les centrales thermiques corses brûlent un
combustible importé. Trois périmètres coexistent donc, et ce document les nomme à
chaque fois : ce qui arrive par les câbles, ce qui est produit sur l'île, ce qui
est produit avec les ressources de l'île. À 14 heures, cela donne 15 %, 84 % et
48 %.

**Données validées, données estimées.** EDF classe son historique : 2019-2020
« validé », 2021-2024 « estimé » — les deux tiers des heures. Contrôle fait : les
conclusions directionnelles tiennent dans les deux sous-ensembles (le bond de
juillet et le 14 heures ressortent des deux côtés). Chaque visuel historique porte
la mention.

**52 605 heures.** Les moyennes 2019-2024 reposent sur 52 605 heures : les 52 608
du fichier brut, moins trois lignes fantômes à zéro créées par les changements
d'heure (2019, 2020, 2024).

**La petite hydraulique manque en 2024.** La colonne micro-hydraulique disparaît
des données EDF sur toute l'année 2024 (environ 8 783 heures). Elle est traitée
comme nulle — après vérification que le total de production l'exclut aussi : le
calcul des parts n'en est pas faussé.

**Le bridage mesure une durée, pas une énergie.** La donnée d'écrêtement compte la
durée maximale de limitation subie par un producteur — pas l'énergie perdue par le
réseau (chapitre du printemps, encadré).

**La comparaison sarde est à génération locale seule.** Les importations corses en
sont exclues et le reste est ramené à 100 % (chapitre des deux îles, encadré). Les
données sardes viennent de la zone « IT-Sardinia » d'ENTSO-E ; la Corse n'est pas
une zone ENTSO-E — elle est incluse dans la France —, ses données viennent d'EDF.

**« La Corse importe » : en moyenne.** Sur six ans, l'île a aussi exporté par ses
câbles — 607 heures, à peine plus de 1 % du temps. Les affirmations d'importation
de ce document sont des moyennes, pas des permanences.

**Électricité ≠ énergie.** Ce document ne parle que d'électricité. L'énergie au
sens large — carburants des transports, fioul et gaz du chauffage — est hors
champ : « autonomie électrique » ne veut pas dire autonomie énergétique de l'île.

**Deux fenêtres temporelles, jamais mélangées.** L'historique s'arrête au
31 décembre 2024 ; le temps réel commence à l'été 2026. Les dix-huit mois entre
les deux ne sont pas couverts : aucun visuel ne les met sur un même axe.
L'écrêtement, lui, s'arrête à 2023, dernier millésime publié par EDF.

**Réutilisation.** Données sous licences ouvertes — Licence Ouverte (Etalab) pour
EDF, CC-BY 4.0 pour ENTSO-E : reproduction libre avec attribution du producteur.
Ce document applique la même règle : chaque visuel cite sa source et sa date.
