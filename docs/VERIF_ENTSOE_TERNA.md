# Vérification sur pièce — ENTSO-E / Terna, zone IT-Sardinia

> **Établi le 22/08/2026**, avant la suite de l'étude énergie. C'est le verrou C3 de
> `docs/ORIENTATION_VITRINE_CORSE.md` — *définition · périmètre · unité · calendrier ·
> ruptures de série* — que le §4 de `docs/PREINSCRIPTION_ENERGIE.md` nomme
> `VERIF_ENTSOE_*` pour le domaine énergie.

Une comparaison Corse–Sardaigne n'entre pas dans une figure parce que deux colonnes portent
le même nom. La figure T6 est déjà publiée ; ce document ne la valide pas rétroactivement,
il dit ce qu'elle mesure réellement et ce qu'elle mesure de travers.

La vérification se fait contre **le bilan régional publié par Terna lui-même**, et non contre
un autre agrégateur : Terna est le producteur de la donnée qu'ENTSO-E republie, donc l'écart
entre les deux est un écart de mise en forme, pas de mesure. Deux millésimes ont été
confrontés, 2023 et 2024. S'y ajoute la définition officielle de l'article 16.1.b, qui dit ce
que le flux contient.

Pièces de la vérification :

| Pièce | Référence |
|---|---|
| Bilan régional Sardaigne 2023 | Terna, *Dati statistici sull'energia elettrica in Italia 2023*, ch. 8 « Elettricità nelle regioni », Tavola 21 et *Bilancio dell'energia elettrica* |
| Bilan régional Sardaigne 2024 | Terna, même publication, édition 2024 |
| Définition du flux | ENTSO-E, *Detailed Data Descriptions* v3r4, § « Aggregated generation per type », TR art. 16.1.b / 16.2.b |
| Donnée vérifiée | `entsoe_sardaigne_2019…2024.xml`, collectés les 22/07 et 31/07/2026, empreintes au manifeste |

---

## 1. Le point de contrôle

Reconstruction du dépôt (`_lignes_entsoe_horaires`, somme horaire) contre le bilan Terna, en
GWh. « Terna net » est la ligne *produzione netta* ; la production brute est rappelée parce
qu'elle tranche la question de la convention.

| Poste | ENTSO-E 2023 | Terna 2023 | Écart | ENTSO-E 2024 | Terna 2024 | Écart |
|---|---:|---:|---:|---:|---:|---:|
| **Total génération** | 12 057,2 | 11 901,3 | **+1,31 %** | 12 045,0 | 11 971,7 | **+0,61 %** |
| *(pour mémoire, Terna brut)* | | 12 563,1 | −4,03 % | | 12 632,2 | −4,65 % |
| Éolien `B19` | 1 904,1 | 1 912,3 | −0,43 % | 1 852,3 | 1 870,1 | −0,95 % |
| Solaire `B16` | 1 370,1 | 1 489,3 | **−8,00 %** | 1 700,8 | 1 800,3 | **−5,53 %** |
| Hydraulique `B10+B11+B12` | 462,2 | 478,0 | −3,30 % | 363,6 | 375,4 | −3,13 % |
| Thermique `B03+B04+B05+B06` | 7 306,1 | 8 020,4 | **−8,91 %** | 7 194,7 | 7 920,8 | **−9,17 %** |
| … le même **+ `B20`** | 7 926,5 | 8 020,4 | −1,17 % | 7 774,7 | 7 920,8 | −1,84 % |
| … **+ `B20` + `B01`/`B17`** | 8 320,7 | 8 020,4 | +3,74 % | 8 128,2 | 7 920,8 | +2,62 % |
| Pompage `B10` sens *OUT* | 248,4 | 246,1 | +0,93 % | 340,7 | 343,7 | −0,87 % |

Quatre choses sortent de ce tableau, et le reste du document les instruit : la convention est
bien le **net** ; le flux **manque du solaire** ; le poste `B20` **appartient au thermique** ;
et la série *OUT* de `B10` est bien le **pompage**, à 1 % près, deux années de suite.

---

## 2. Unité et sommation — vérifié

La *Detailed Data Description* de l'article 16.1.b est explicite :

> « Actual aggregated **Net** generation output (MW) per market time unit and per production
> type. […] The actual generation shall be computed as the **average of all available
> instantaneous Net generation output values on each market time unit**. »

Une valeur est donc un MW moyen sur son pas de marché, et sa somme sur des pas d'une heure
est un MWh **net**. C'est ce que fait `entsoe_sardaigne_to_parquet`, et le total tombe à
+1,3 % puis +0,6 % de la production nette de Terna, contre −4,0 % et −4,7 % de sa production
brute : la convention est confirmée par la mesure, pas seulement par le texte.

Côté corse, la convention est la même — la courbe EDF est nette des auxiliaires, ce que
signale d'ailleurs le photovoltaïque négatif sur 20 426 heures. Les deux barres de T6 sont
donc bien du net contre du net.

La ligne « couverture complète supposée » du §4 de la pré-inscription est levée : le Parquet
porte 8 760 heures par année simple et 8 784 par bissextile, aucune manquante, aucune en
double. **Mais cette complétude est obtenue par construction** — le report `A03` remplit les
positions non déclarées — donc elle ne dit rien de la qualité du remplissage. C'est l'objet
du §6.

---

## 3. Périmètre — quatre asymétries, dont trois pèsent

### 3.1 Le poste « autre » est du thermique

`B20` (*Other*) porte 3,97 % de la génération sarde sur six ans, soit 2 905,6 GWh. Il est
aujourd'hui rangé dans une filière `autre` que la Corse n'a pas, et T6 code donc un `autre`
corse à 0,0 en dur : la barre sarde porte un bloc de 4 % sans contrepartie ni explication.

Le bilan de Terna n'a que six lignes de production — hydro, thermique traditionnel,
géothermique, éolien, photovoltaïque, accumulation — et la géothermique sarde est vide. Tout
ce qui n'est ni hydro, ni vent, ni soleil, ni batterie est donc *nécessairement* dans le
thermique. L'arithmétique le confirme : sans `B20`, le thermique reconstruit manque 8,9 %
puis 9,2 % de la mesure Terna ; avec lui, l'écart tombe à 1,2 % et 1,8 %. Deux années
indépendantes, même conclusion.

Conséquence sur ce qui est publié :

| Filière (moyenne 2019-2024) | T6 aujourd'hui | `B20` reclassé |
|---|---:|---:|
| Thermique | 65,09 % | **69,06 %** |
| Hydraulique | 3,65 % | 3,65 % |
| Solaire | 9,08 % | 9,08 % |
| Éolien | 14,82 % | 14,82 % |
| Bioénergies | 3,39 % | 3,39 % |
| Autre | 3,97 % | **0,00 %** |

L'écart de thermique entre les deux îles passe de **9,7 à 13,7 points** (la Corse est à
55,40 %). Le titre « deux îles thermiques » n'en souffre pas ; la note qui chiffre le charbon
et l'IGCC non plus, puisque `B05` et `B03` valent 32,04 % et 31,76 % du total et ne bougent
pas.

### 3.2 La station de pompage gonfle l'hydraulique sarde

`B10` est du turbinage de station de pompage. Sur six ans il **restitue** 1 110,9 GWh et en
**consomme** 1 328,4 pour les produire — un rendement de cycle de 0,84, cohérent avec la
technologie, et la preuve que les deux séries sont bien les deux sens d'un même ouvrage. La
série *OUT* recoupe la ligne « Energia destinata ai pompaggi » de Terna à 0,9 % près en 2023
comme en 2024. (La donnée ne nomme aucune installation ; le complexe réversible du Taloro,
entre les lacs de Gusana et de Cucchinadorza, est le candidat évident, mais ce n'est pas
vérifié ici et rien dans la suite n'en dépend.)

Terna range lui aussi cette restitution dans l'hydroélectrique, donc la correspondance du
dépôt n'est pas fautive. Ce qui l'est, c'est la lecture : **1,52 des 3,65 points
d'hydraulique sarde — 42 % de la barre — ne sont pas de la production, mais du stockage
rendu.** L'hydraulique primaire sarde vaut 2,14 %. La Corse, elle, n'a aucune STEP
(`stockage_mw` est vide dans la courbe EDF), et son hydraulique est à 27,95 % : la
comparaison oppose donc 28 % de production à 2 % de production plus 1,5 % de restitution.

### 3.3 La micro-hydraulique corse n'a pas de contrepartie

Elle pèse 290,8 GWh, soit 10,47 % de l'hydraulique corse et **2,93 points** de la barre corse
de T6. Le flux sarde ne distingue pas d'équivalent, et les petites installations n'y sont pas
nécessairement remontées (§3.4). Ces 2,9 points sont donc comptés d'un côté et inconnus de
l'autre.

### 3.4 Le solaire diffus manque côté sarde

C'est l'écart le plus net du tableau du §1 : −8,00 % en 2023, −5,53 % en 2024. L'article
16.1.b ne fixe aucun seuil de puissance, mais laisse une latitude explicite :

> « The actual generation of **small-scale units might be estimated** if no real-time
> measurement devices exist. »

L'ordre de grandeur de ce que cette latitude laisse tomber se lit dans le parc lui-même :
Terna recense en Sardaigne **59 465 installations photovoltaïques pour 1 360 MW**, soit 23 kW
en moyenne. Le flux capte 92,0 % de l'énergie solaire réelle en 2023 et 94,5 % en 2024 — les
MW sont concentrés dans quelques grandes centrales — mais il en manque, et **la part
manquante n'est pas la même d'une année à l'autre**. Deux points ne font pas une tendance :
ce qu'ils établissent, c'est que le solaire sarde du dépôt est un plancher dont l'écart au
réel bouge, donc qu'on ne peut pas lire une évolution de ce poste sans mesurer cet écart sur
chaque année lue.

L'éolien, lui, tient à 0,4 % et 1,0 % : il est fait de parcs, pas de toitures.

### 3.5 Ce qui est symétrique, et qu'il n'était pas acquis de trouver tel

Le photovoltaïque corse est négatif 20 426 heures sur 52 602 — consommation des auxiliaires
la nuit. On pouvait craindre que la barre corse soit du net d'auxiliaires face à un sarde
brut. Elle ne l'est pas : la part solaire corse vaut **15,46 % en net contre 15,58 % en ne
comptant que les heures positives**, soit 0,12 point. L'asymétrie existe, elle est mesurée,
elle est négligeable. Côté sarde, la même chose passe par les séries *OUT* de `B16`, qui
totalisent 2,6 GWh sur six ans — 0,04 % du solaire.

---

## 4. Définition — la correspondance code par code

`PSR_VERS_FILIERE` de `prepare.py`, confronté au schéma EDF (`edf_courbe_charge_horaire`) et
au bilan Terna.

| Code ENTSO-E | Libellé | Filière du dépôt | Contrepartie EDF | Verdict |
|---|---|---|---|---|
| `B03` `B05` `B06` | IGCC · houille · fioul | thermique | `thermique_mw` | correspond ; la nature des combustibles diffère, c'est le propos de la figure |
| `B04` | gaz fossile | thermique | `thermique_mw` | correspond ; 1,0 GWh, apparu la dernière heure de 2024 |
| `B20` | *Other* | `autre` | aucune | **à reclasser en thermique** (§3.1) |
| `B01` `B17` | biomasse · déchets | bioénergies | `bioenergies_mw` | correspond au classement EDF ; Terna les compte dans son thermique, ce qui explique le résidu de +2,6 / +3,7 % du §1 |
| `B11` `B12` | fil de l'eau · réservoir | hydraulique | `hydraulique_mw` | correspond |
| `B10` | STEP, turbinage | hydraulique | aucune (`stockage_mw` vide) | correspond au classement Terna, **mais 42 % de la barre hydro sarde** (§3.2) |
| — | — | — | `micro_hydraulique_mw` | **sans contrepartie sarde** : 2,93 pt de la barre corse (§3.3) |
| `B16` | solaire | solaire | `photovoltaique_mw` | correspond, **amputé de 5 à 8 %** (§3.4) |
| `B18` `B19` | éolien | éolien | `eolien_mw` | correspond ; `B18` (en mer) jamais présent |
| `B09` | géothermie | `autre` | `geothermie_mw` (vide) | série présente depuis le 19/08/2024, **constante à 0** ; Terna confirme « — » |
| `B25` | stockage | `autre` | aucune | dernière heure de 2024, valeur 0 ; Terna publie pourtant 1,5 puis 5,4 GWh d'accumulation |
| `B02` `B07` `B08` `B13` `B14` `B15` | tourbe, houle, marée, nucléaire, autre ENR | mappés | — | jamais présents, sauf `B15` la dernière heure de 2024, à 0 |

Aucun code non mappé : la garde de `prepare.py` qui lève sur un code inconnu n'a jamais eu à
se déclencher, et elle reste utile pour la suite (2025 en ajoutera).

---

## 5. Calendrier — le seul point que cette vérification avait d'abord raté

> **Rédigé une première fois le 22/08/2026 sur la foi d'un commentaire de code, puis
> corrigé le même jour sur mesure.** La version initiale concluait « vérifié » : elle
> reprenait la ligne « fait » du §4 de la pré-inscription et l'argument, exact mais hors
> sujet, qu'Europe/Rome et Europe/Paris partagent le même décalage. Les deux fuseaux
> coïncident bien — mais le code ne faisait pas la conversion. Un verrou qu'on déclare
> tenu parce qu'un commentaire l'affirme n'est pas un verrou ; c'est l'erreur même que ce
> document reproche ailleurs.

**Les deux Parquet ne portent pas le même type**, et c'est de là que tout vient. La courbe
EDF arrive horodatée `+00:00` — de l'UTC explicite, correctement lu en `TIMESTAMP WITH TIME
ZONE`. Le flux ENTSO-E, lui, est écrit par `prepare` en `TIMESTAMP` **naïf** portant de
l'UTC. Or `timezone('Europe/Rome', x)` ne fait pas la même chose sur l'un et sur l'autre :
sur un instant daté il **convertit** et rend du local ; sur un naïf il **interprète** — il
décrète que la valeur était déjà à Rome — et rend un instant daté, dont `extract()` relit
ensuite l'heure dans le fuseau de la machine. Sur un poste réglé à l'heure de Rome,
l'aller-retour est l'identité.

Conséquence mesurée : `heure_locale` valait l'**heure UTC** côté sarde, décalée d'une heure
l'hiver et de deux l'été. Le pic solaire tombait à 11 h — impossible à 9° de longitude, où
la Corse pique à 14 h. Aucune figure publiée ne lisait cette colonne, donc rien de faux
n'est paru ; mais c'est exactement celle qu'un profil horaire Corse–Sardaigne aurait lue en
premier.

Après correction — dire que le naïf est de l'UTC, *puis* convertir — la fenêtre solaire
sarde se pose sur le soleil réel :

| Mois | Solaire sarde non nul | Lever / coucher réels |
|---|---|---|
| janvier | 8 h → 17 h | 07 h 50 → 17 h 10 |
| juillet | 6 h → 20 h | 06 h 00 → 21 h 15 |

C'est la vérification qui compte, parce qu'elle ne dépend d'aucune convention déclarée :
le soleil se lève quand il se lève.

**Deux conséquences pour la suite.** D'abord l'année elle-même : `extract('year')` sur un
instant daté se lit dans le fuseau de la **machine**, donc la borne de T6 aurait découpé
autrement ici et sur le runner d'intégration, qui tourne en UTC. Les deux côtés déclarent
maintenant explicitement l'année civile **locale** — seule définition qui vaille pour deux
îles au même fuseau. Ensuite le bord d'année demeure, mais symétrique : une heure sur 8 760,
soit 0,011 %, et elle tombe hors de la fenêtre des deux côtés.

**Et un défaut du côté corse, que le même fil a fini par isoler.** Le profil solaire corse de
juillet a son centre de masse à 15,2 h contre 12,9 h côté sarde, à longitude égale. L'ancre
qui tranche est extérieure aux deux : le **rayonnement global mesuré au pyranomètre** par
Météo-France (`GLO`), disponible à Ajaccio, Bastia et Corte depuis 2020 — autre producteur,
autre instrument, même soleil.

Le pyranomètre se valide d'abord tout seul : lu en UTC, son maximum tombe à 13 h 00 en
janvier et 13 h 55 en juillet, soit une demi-heure après le midi solaire de 9° E — la
signature d'un cumul horaire daté par la **fin** de son intervalle. Ensuite, corrélation
instant contre instant, par régime d'heure légale :

| Série | Décalage optimal, hiver (CET) | Décalage optimal, été (CEST) |
|---|---:|---:|
| Sardaigne (ENTSO-E) | **+1 h** | **+1 h** |
| Corse (EDF) | **0 h** | **−1 h** |

La Sardaigne ne bouge pas d'une saison à l'autre : son décalage constant dit simplement
qu'elle date ses heures par le **début** de l'intervalle quand Météo-France les date par la
fin. C'est aussi le **témoin** qui disculpe le pyranomètre — si la météo dérivait avec
l'heure d'été, la Sardaigne dériverait avec elle.

La Corse, seule, se déplace d'exactement **une heure entre l'hiver et l'été**. Aucun parc, ni
orientation, ni ombrage de relief ne produit un saut discret calé sur un changement d'heure
légale : c'est une convention humaine, donc un traitement d'horodatage.

**Ce qui était établi le 22/08, et ce qui l'est depuis le 23.** Ce paragraphe s'arrêtait
volontairement à un constat sobre — un décalage saisonnier face à une ancre indépendante — et
rangeait la cause parmi les hypothèses : que la courbe EDF porte de l'heure locale sous un
suffixe `+00:00`. Deux mesures faites le lendemain l'en sortent.

**Le saut est discret, et il l'est dix fois.** Trois semaines avant, trois semaines après
chacune des dix bascules d'heure légale de 2020-2024 : le décalage optimal corse saute de
∓1 h à chaque fois (0,66 à 1,11 h ; moyenne 0,95 h), le témoin sarde de ±0,1 h. Même saison,
même parc, même soleil de part et d'autre du week-end. Une propriété du parc ne se
synchronise pas dix fois de suite sur une convention humaine.

**Et la structure du fichier le dit sans le soleil.** Sur 52 608 heures, les *trois seules*
lignes à production nulle tombent à 02 h des dimanches de passage à l'heure d'été — l'heure
qui n'existe pas en heure légale. Une série réellement en UTC n'a rien de singulier ce
jour-là.

Le témoin sarde fixe le reste. ENTSO-E date par le début de l'intervalle, Météo-France par la
fin : d'où le +1 h constant de la Sardaigne. La Corse demande 0 h l'hiver et −1 h l'été,
c'est-à-dire exactement ce que donne une étiquette d'heure légale, datée par le début de
l'intervalle, une fois ramenée en UTC. Aucune autre convention à décalage fixe ne rend compte
des deux régimes à la fois.

> **La courbe horaire d'EDF porte l'heure légale corse ; son suffixe `+00:00` est faux.**

La réparation reste celle qui avait été arrêtée *avant* cette conclusion, et c'est bon
signe : la correction se fait là où la convention est interprétée — dans `prepare` —, le brut
se conserve à côté de l'interprété, et on ne « retire pas une heure l'été » dans une figure.
`edf_courbe_corse.parquet` porte désormais `horodatage_publie` (l'étiquette telle qu'EDF la
publie), `date_heure_locale` (l'heure légale, colonne de référence) et `date_heure_utc`
(l'instant, c'est-à-dire l'interprétation). Deux gardes : un suffixe autre que `+00:00` fait
échouer la préparation, et les heures inexistantes sont retirées par aller-retour heure légale
-> instant -> heure légale, jamais par une liste de dimanches écrite à la main.

**Le périmètre est plus étroit qu'annoncé.** Le jeu voisin `edf_mix_temps_reel`, du même
producteur, est bien en UTC : son pic d'étiquette brute tombe à 11 h 30 pour un midi solaire
à 11 h 28 UTC. T1 n'a jamais été fausse. Une convention se vérifie par jeu de données, jamais
par producteur — c'est le corollaire de tout ce document.

**Quatre verrous indépendants** tiennent maintenant la lecture, dans
`tests/test_horodatage_corse.py`, choisis pour que leur erreur ne puisse pas être corrélée à
celle de la chaîne : le comportement aux bascules d'heure légale ; la stabilité sous un fuseau
de session hostile (UTC, Kiritimati, Niue) ; la cohérence au pyranomètre, témoin sarde
compris ; le midi solaire calculé en astronomie pure. Le premier test du fichier juge
l'**ancre** et non la courbe — le pyranomètre doit tomber sur le midi solaire, mesuré à 0,13 h
près sur douze mois — pour qu'un repère faux n'accuse jamais une série juste.

**Ce que cela déplace.** T6 n'est pas concernée : elle somme des années entières. T2b, T3 et
T4, si. Le zénith solaire d'été passe de 15 h à 13 h — le midi solaire corse en heure d'été
est à 13 h 25 —, « l'heure la plus verte est 14 h » devient un créneau de 12 à 13 heures, et
sept verrous de texte ont cassé d'un coup. Les fenêtres de l'étude ont été **remesurées** et
non translatées : la nuit va de 23 h à 7 h, la mi-journée d'été de 12 h à 13 h, le soir d'été
de 18 h à 21 h.

Un point du 22/08 est en revanche devenu faux et se corrige ici : « la fenêtre corse de T6
n'est bornée nulle part dans le code ». Elle l'est depuis `fe4ee87` — `FENETRE_T6` borne les
deux côtés et un verrou casse si les deux périodes divergent. L'heure de 2025 qui traînait
dans le Parquet a d'ailleurs disparu d'elle-même : elle était l'artefact de la conversion
corrigée ici, la dernière heure de 2024 basculant au 1ᵉʳ janvier suivant.

Dernier point, qui appartient au chantier suivant : **ce déplacement est identique avant et
après la bascule « Estimé »** — optimum 0 h l'hiver et −1 h l'été aussi bien sur l'année
validée 2020 que sur les quatre années estimées. Il ne dit donc rien du statut. L'heure
inexistante, elle, en dit quelque chose : cf. § 8.

---

## 6. Ruptures de série — trois, dont une seule pèse

### 6.1 Le report `A03` n'est pas un détail de format

Toutes les séries sont en `curveType A03` : une position non déclarée reconduit la dernière
valeur connue. Le parseur applique la règle correctement — c'est la règle elle-même qui
laisse au producteur la liberté de ne rien dire pendant longtemps.

Part de l'énergie annuelle issue d'une valeur reconduite plutôt que déclarée :

| Code | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---:|---:|---:|---:|---:|---:|
| `B16` solaire | 0,6 % | 0,4 % | 0,3 % | 0,6 % | 0,6 % | 0,5 % |
| `B19` éolien | 1,1 % | 1,1 % | 1,2 % | 0,9 % | 1,0 % | 1,1 % |
| `B05` houille | 19,9 % | 21,2 % | 15,8 % | 14,8 % | 26,9 % | 19,7 % |
| `B03` IGCC | 27,1 % | 29,8 % | 46,0 % | 51,9 % | **56,8 %** | 57,7 % |
| `B01` biomasse | 77,4 % | 80,9 % | 75,5 % | 73,9 % | 73,9 % | 79,6 % |
| `B06` fioul | 89,7 % | 90,9 % | 87,0 % | 88,1 % | 89,9 % | 88,0 % |

Ce n'est pas alarmant en soi : une centrale à l'arrêt se déclare une fois et se tait, et la
majorité des longs blocs valent **zéro** — 2 233 heures pour `B09`, 1 490 pour `B06` en 2024,
483 pour `B03` en 2023, toutes à 0 MW. Le report est alors fidèle.

La quantité qui compte est donc l'énergie issue d'un bloc **long et non nul**, une valeur
tenue constante 24 heures ou plus à un niveau non nul :

> **2 747 GWh sur 73 258, soit 3,75 % de l'énergie sarde des six ans.**

Elle est concentrée sur trois codes : `B06` (56,2 % de sa propre énergie), `B01` (32,1 %),
`B03` (5,2 %, mais d'un poste qui pèse 32 % du mix, d'où 1,65 point du total). Les plus longs
blocs non nuls tiennent 776 heures à 16 MW (`B06`, janvier 2024), 278 heures à 18 MW (`B01`,
avril 2023), 234 heures à 20 MW (`B11`, février 2019).

C'est du même ordre que le résidu du §1 : le thermique reconstruit dépasse Terna de 2,6 à
3,7 % quand on y met les bioénergies, et ce sont précisément `B01`, `B06` et `B03` qui
portent le report. Les deux mesures se recoupent.

### 6.2 La dernière heure de 2024 change de régime

Le fichier 2024 bascule en pas de 15 minutes le 31 décembre, et sa **dernière heure**
introduit d'un coup cinq codes absents des cinq années précédentes : `B04`, `B09`, `B15`,
`B17`, `B25`. Aucun ne porte plus de 1,0 GWh sur l'année. C'est la préparation de l'unité de
marché à 15 minutes, pas un changement de parc.

La conséquence pratique est ailleurs : la nomenclature s'est enrichie à partir de 2025. Le
gaz fossile se déclare désormais séparément de l'IGCC, les déchets de la biomasse, le
stockage à part. **Toute extension de la fenêtre au-delà de 2024 comparera donc des années à
dix postes à des années à quinze**, et la répartition interne du thermique sarde changera de
sens sans que la donnée ait changé.

### 6.3 Le solaire bascule en sens *OUT* au crépuscule

À partir de 2021, `B16` apparaît aussi en `outBiddingZone`, et sa série *IN* cesse de couvrir
toute l'année : 11 heures découvertes en 2021, 394 en 2022, 927 en 2023, 1 269 en 2024. La
vérification est nette : **aucune de ces heures n'est absente des deux sens à la fois**. Le
solaire est toujours déclaré, tantôt comme production, tantôt comme consommation
d'auxiliaires — les heures locales concernées sont pour l'essentiel 17 h à 19 h, ce qui est
cohérent. Le
parseur écarte le sens *OUT*, donc ces heures valent 0 au lieu d'un petit négatif : 2,6 GWh
sur 6 654, soit 0,04 % du solaire sarde.

---

## 7. Ce que la vérification change dans ce qui est publié

Les quatre premiers points sont **appliqués** sur cette branche ; les deux derniers restent
ouverts.

1. **`B20` → `thermique`** dans `PSR_VERS_FILIERE` — fait (`fe4ee87`). Le thermique sarde
   passe de 65,09 à 69,06 %, la filière `autre` disparaît de la figure, et le verrou
   `test_sardaigne_thermique_domine` a suivi.
2. **La fenêtre corse de T6 bornée** à 2019-2024 — fait (`fe4ee87`). `FENETRE_T6` borne les
   deux côtés et un verrou casse si les deux périodes divergent : la propriété tenue est que
   les deux barres couvrent la même période, pas que la requête soit juste aujourd'hui.
3. **« La Sardaigne (10× plus grande) »** — retiré (`69c4dc5`), sans remplaçant chiffré. Les
   trois rapports disponibles sont **7,4×** en génération électrique (mesuré ici, moyenne six
   ans), **4,5×** en population et **2,8×** en superficie. Aucun ne vaut 10, et aucun
   multiplicateur unique ne décrit cet écart : la note est redevenue qualitative.
4. **« Elle a 15 fois plus d'éolien »** tient : 15,6× en part de mix, ce qui est bien ce que
   la figure donne à lire. En énergie absolue, le rapport est de 115×.
5. **La barre hydraulique sarde** mélange 2,14 % de production et 1,52 % de stockage rendu,
   face à une Corse qui n'a pas de STEP. À trancher : séparer le segment, ou l'écrire.
6. **Le solaire sarde est un plancher, pas une mesure** : 8,0 % manquants en 2023, 5,5 % en
   2024. L'écart n'étant pas constant, toute lecture d'évolution sur ce poste doit d'abord
   le mesurer année par année.

S'y ajoutent deux défauts déjà connus et déclarés au §2 de la pré-inscription, que cette
vérification n'a pas traités : le pied de T6 ne porte que la date d'`entsoe_sardaigne_2024`
alors que la figure combine deux sources, et la Sardaigne est testée par simple existence de
son Parquet plutôt que par appartenance à la lignée du build courant.

---

## 8. Ce qui n'a pas été vérifié

- **2019 à 2022 n'ont pas été confrontés à Terna.** Deux millésimes l'ont été, et ils
  concordent ; rien ne garantit que les quatre autres se comportent pareil, en particulier
  sur le solaire, dont l'écart bouge d'une année à l'autre.
- **Le contenu réel de `B20` n'est pas nommé.** Qu'il soit thermique est établi par le solde
  du bilan Terna, sur deux années ; ce qui brûle exactement ne l'est pas. Le flux
  « génération par unité de production » (art. 16.1.a) le dirait, il n'a pas été interrogé.
- **Le statut « estimé » de la courbe corse n'est pas levé — c'est une limite explicite.**
  Il couvre 2021 à 2024, soit 35 060 heures sur 52 602, **66,7 % de la barre corse**. La
  limite, telle qu'elle doit être portée :

  > La cohérence horaire du photovoltaïque EDF classé « Estimé » est confirmée par
  > comparaison au rayonnement solaire mesuré indépendamment par Météo-France. Cette
  > validation **ne porte pas sur les niveaux annuels par filière** utilisés dans la
  > comparaison Corse–Sardaigne ; ceux-ci restent à recouper avec un bilan électrique
  > indépendant.

  Ce qui est acquis : les années estimées suivent le rayonnement mesuré à r = 0,963 l'été et
  0,926 l'hiver, contre 0,981 et 0,973 pour la seule année validée disponible (2020). Une
  série grossièrement reconstruite ne ferait pas cela. Ce qui ne l'est pas : T6 ne lit ni la
  forme horaire ni le photovoltaïque, mais des **sommes annuelles** dominées par le thermique
  et l'hydraulique — **un biais multiplicatif annuel passerait entièrement au travers de ce
  test**. Deux mesures internes complètent le tableau sans rien valider : la bascule est
  annuelle et non observation par observation (dernière heure validée, 1ᵉʳ janvier 2021 à
  00 h), et les tests de signature — granularité, valeurs distinctes, répétitions, part de
  négatifs — ne trouvent aucune trace de reconstruction grossière. Absence de rupture visible
  n'est pas validation : des estimations ne se contrôlent pas avec elles-mêmes.

  **Un fait nouveau, du 23/08/2026, et il ne porte pas sur les niveaux mais sur la grille du
  temps.** Les six dimanches de passage à l'heure d'été portent chacun une ligne étiquetée
  02 h — une heure qui n'existe pas en heure légale corse. EDF la publie à **zéro** en 2019,
  2020 et 2024 ; il la publie **remplie**, à 246, 253 et 200 MW, en 2021, 2022 et 2023, trois
  années estimées. Trois heures sur 35 060 ne déplacent aucun total : ce n'est pas une preuve
  que les niveaux annuels soient faux. C'est la preuve que l'estimation **intervient sur la
  structure temporelle de la série** et produit une valeur là où il n'y a pas eu d'heure.
  Elle interdit donc de lever le verrou par simple ressemblance statistique : une série qui
  ressemble à la réalité aux endroits où on la regarde peut avoir été fabriquée aux endroits
  où on ne la regarde pas. Le recoupement annuel indépendant reste le seul chemin.
- **Terna révise ses statistiques régionales.** Les chiffres 2023 utilisés ici sont ceux de
  l'édition 2023 ; une édition ultérieure peut les corriger.
- **Les données de puissance installée (art. 14.1.a) n'ont pas été touchées** — le dépôt ne
  s'en sert pas, et l'écart de périmètre relevé dans la presse sur l'hydraulique corse
  (« 20 à 25 % ») reste à trancher de ce côté-là, pas de celui-ci.

---

## 9. Refaire la vérification

Les mesures de ce document se rejouent depuis les bruts empreintés, sans réseau :

```bash
fetch-data && python -m demonstrateur.prepare     # jeton ENTSOE_TOKEN requis
pytest tests/test_resultats.py -k sardaigne
```

Les inventaires du §1 et du §6 se reconstruisent avec `_lignes_entsoe_horaires`, en sommant
les `mw` par code — un MW moyen sur une heure valant un MWh — puis en comparant aux tables
ci-dessus. Les fichiers portent leurs empreintes au manifeste :

| Source | Collecte | SHA-256 (préfixe) |
|---|---|---|
| `entsoe_sardaigne_2019` | 22/07/2026 | `dbe718267f606da9…` |
| `entsoe_sardaigne_2020` | 22/07/2026 | `1c05e36f7ddbb16f…` |
| `entsoe_sardaigne_2021` | 22/07/2026 | `0f48332b0ee2b183…` |
| `entsoe_sardaigne_2022` | 31/07/2026 | `751d7fc4c730fc8b…` |
| `entsoe_sardaigne_2023` | 22/07/2026 | `57e55a74cc0419f7…` |
| `entsoe_sardaigne_2024` | 22/07/2026 | `16adf57760568d72…` |
| `edf_courbe_charge_horaire` | 22/07/2026 | `787ee649f4d66aca…` |
