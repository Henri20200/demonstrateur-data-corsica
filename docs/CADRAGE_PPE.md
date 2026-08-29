# Cadrage — la PPE de Corse comme horizon

**Cadré le 04/08/2026.** Ce document fixe l'horizon du fil rouge autonomie. Il ne remplace
pas `BRIEF.md` (question fermée de l'électricité) : il dit *pour quand* et *pour qui* ces
chiffres comptent, et ce qu'il reste à mesurer.

## La distinction qui tient tout

La Programmation pluriannuelle de l'énergie de Corse est **l'horizon** du travail, pas son
**commanditaire**.

- **Horizon** — la PPE est le moment et le lieu où ces chiffres sont lus par des gens qui
  décident. Ça fixe une date utile et un registre. Ni la question, ni la méthode, ni le
  sommaire n'en dépendent.
- **Commanditaire** — on produirait ce que la PPE réclame, structuré sur ses rubriques.
  C'est ce qui a été écarté le 31/07/2026 : se donner une finalité, c'est laisser un agenda
  extérieur choisir les sujets, et le biais de sélection est un parti pris qu'aucune rigueur
  sur les chiffres ne rattrape.

Conséquence directe : **le livrable ne plaide rien.** Il confronte des objectifs publics
chiffrés à la trajectoire mesurée, dans des périmètres écrits. Aucune position sur le statut
de l'île, aucune prescription. Le sommaire est fixé par un document officiel, pas par nous —
c'est précisément ce qui rend le travail descriptif tout en le rendant utile.

## Ce que la PPE est, et quand elle se joue

Instituée pour les zones non interconnectées par l'article 203 II de la loi du 17 août 2015,
la PPE de Corse est **distincte de la PPE nationale** et **co-élaborée** par le président du
**Conseil exécutif** de Corse et le représentant de l'État. Elle est adoptée par décret, après
délibération de l'**Assemblée de Corse** valant avis.

> « Président de la Collectivité » ne désigne personne : la Collectivité de Corse a deux
> présidences, celle du Conseil exécutif et celle de l'Assemblée. Elles n'interviennent pas
> au même moment de la PPE — l'exécutif co-élabore le projet (art. L. 141-5 III du code de
> l'énergie), l'Assemblée délibère ensuite pour avis. Confondre les deux effacerait
> précisément l'étape délibérative. Formulation alignée sur `FRISE_PPE.md`.

- Décret n° 2015-1697 du **18 décembre 2015**, modifié le **13 décembre 2019**, puis par le
  **décret n° 2023-554 du 30 juin 2023** (JO du 2 juillet 2023).
- Périodes : **2016-2018 / 2019-2023**, puis **2019-2023 / 2024-2028** pour la révision.
- La révision complète a été adoptée par l'Assemblée de Corse en **avril 2021**. Ce qui a
  effectivement été publié est une **révision simplifiée**, adoptée par l'Assemblée le
  30 mars 2023 et prise par le décret du 30 juin 2023 : elle relève les objectifs de
  puissance et ouvre la centrale du Ricanto aux bioliquides, mais ne réécrit pas la
  programmation d'ensemble. **Le décret de 2015 reste le texte de base**, et ses échéances
  restent 2018 et 2023.

**2028 n'est donc pas une date de révision : c'est le terme de la période en cours.** La
programmation de l'après-2028 se prépare pendant sa concertation — soit, au vu du cycle
précédent (concertation publique en juin-juillet 2018 pour une approbation visée à un an),
**en 2026-2027**. La fenêtre utile est maintenant, pas dans deux ans.

## Question fermée du fil autonomie (figée le 04/08/2026)

> La Corse a-t-elle tenu les objectifs électriques que sa propre programmation s'était
> fixés — et si non, qu'est-ce qui a bougé à la place ?

On ne retient que des cibles **dont l'échéance est passée**. Rien à pronostiquer : ou bien
la cible est atteinte, ou bien elle ne l'est pas, et la donnée le dit.

## Les cibles, citées de leur producteur

Toutes tirées du rapport de PPE à l'Assemblée de Corse (2016-2018 / 2019-2023), sauf la
dernière ligne, qui vient du **rapport annexé au décret** — un autre document, cité à part
en fin de page. **Une cible se recopie, elle ne se déduit pas** — même règle que la moyenne
8 h de l'ozone.

| Cible officielle | Périmètre | Échéance | Ce que le pipeline mesure |
|---|---|---|---|
| « près de **87 %** de sa consommation totale d'énergie primaire » vient de l'extérieur | énergie primaire | constat 2014 | T7 — 86,1 % en 2020 (OREGES) |
| seuil de déconnexion porté « à **35 %** en 2018, puis de **45 %** en 2023 » | ENR variables, électricité | 2018 et 2023 | T8 (heures au-dessus de 35 %), T5 (écrêtement) — **non tenu**, cf. ci-dessous |
| consommation d'électricité **2 254 GWh** (2015) → **2 614 GWh** en 2025 | électricité | 2025 | `edf_courbe_corse` 2019-2024 |
| pointe **502 MW** (2015) → **583 MW** en 2025 | électricité | 2025 | `edf_courbe_corse` |
| ENR garanties **+148 %** : petite hydraulique +12 MW, bois-énergie et bio-déchets +7 MW, PV et éolien avec stockage +30 MW | puissance installée | 2023 | registre EDF (étude carte solaire) |
| ENR intermittentes **+38 %** : PV sans stockage +20 MW, solaire thermodynamique +12 MW, éolien +12 MW | puissance installée | 2023 | registre EDF |
| Vazzio : dérogation de 18 000 h entre 2020 et 2023, puis « l'installation devra être mise définitivement à l'arrêt » | thermique | 2023 | hors pipeline — fait à sourcer |
| « Ces mesures devraient porter la part des énergies renouvelables à **22 %** de la consommation d'énergie finale en 2023, et **40 %** de la production d'électricité » | énergie finale / **production nette livrée au réseau** | 2023 | `edf_courbe_corse` — **38,4 % en 2023**, cf. ci-dessous |

Cibles **relevées** par le décret du 30 juin 2023 (art. 1er), en puissance additionnelle
**depuis 2015** — à confronter au registre EDF, et non aux cibles de 2015 qu'elles remplacent :

| Filière | Cible 2015 | Cible 2023 |
|---|---|---|
| Solaire photovoltaïque au sol | +20 MW (sans stockage) | **+100 MW** |
| Solaire photovoltaïque en toiture > 500 kW | — | **+10 MW** |
| Éolien | +12 MW (sans stockage) | **+32 MW** |
| Petite hydroélectricité | +12 MW | +12 MW |
| Biomasse et biodéchets | +7 MW | +7 MW |

Le décret ouvre par ailleurs la centrale du Ricanto aux bioliquides (art. 2), prévoit que
l'électrification des ports d'Ajaccio et de Bastia « *peut être directe ou recourir à
l'hydrogène* » (art. 3), et fixe la fin des réseaux GPL au **31 décembre 2038**.

### Les 40 % d'ENR électriques en 2023 : le périmètre est écrit, donc mesurable

Vérifié le 27/08/2026. La phrase figure page 13 du **rapport annexé au décret**, pas dans
le rapport à l'Assemblée ni dans le décret lui-même, qui ne portent aucun « 40 % ». Sa
figure 7 la range en colonne « PPE » face aux objectifs nationaux : le national vise 40 %
de la production électrique en **2030**, la Corse s'est donné le même chiffre pour **2023**.

Le registre compte : « Ces mesures **devraient porter**… » est une conséquence attendue au
conditionnel, pas une prescription comme les +148 % ou les +38 %. La formulation se recopie
avec le chiffre.

**Le dénominateur est écrit, et c'est ce qui rend la cible mesurable.** Page 10 du même
rapport : « En 2014, la production électrique d'origine renouvelable représente **32 % de la
production nette livrée au réseau** ». Sa figure 6 chiffre ce dénominateur — production
nette **2 127 GWh**, dont **632 GWh d'interconnexions (29,7 %)**. Les imports sont donc
**dans** le dénominateur. Notre donnée EDF suit exactement ce découpage :
`production_totale_mw` est la somme des sept postes, importations comprises (identité
vérifiée à 0,1 GWh près sur chaque année 2019-2024).

Mesuré sur ce périmètre, ENR = hydraulique + micro-hydraulique + photovoltaïque + éolien +
bioénergies :

| | 2014* | 2019 | 2020 | 2021 | 2022 | **2023** | 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ENR / production nette | 31,7 % | 27,5 % | 34,2 % | 34,1 % | 26,6 % | **38,4 %** | 32,7 % |

\* valeur du rapport (source EDF) ; les autres calculées sur `edf_courbe_corse`
(build `71338c8`).

**La cible n'est pas atteinte en 2023 : 38,4 % contre 40 %.** Deux réserves à porter avec
le chiffre. D'abord la volatilité : 26,6 % en 2022, 38,4 % en 2023, onze points d'écart —
le rapport lui-même prévient de « la forte fluctuation de la production d'électricité
d'origine renouvelable due à la prépondérance de l'hydroélectricité ». Un verdict sur la
seule année d'échéance porte cette fragilité. Ensuite, 2021-2024 sont des millésimes EDF
**estimés**, 2019-2020 seuls étant validés.

### Le point qui porte le sujet — et il est déjà établi

La PPE prévoyait de relever le seuil de déconnexion **à 45 % en 2023**. Il ne l'a pas été :
le seuil applicable reste **35 %**, et c'est lui qui produit l'écrêtement visible en T5.

Ce constat ne repose pas sur une lecture unique. Trois sources, dont le texte qui fait foi :

1. `figures.py` le tenait déjà de la **Lettre OREGES 2021, p. 8**, avec son fondement
   réglementaire — l'**arrêté du 23 avril 2008 modifié**, qui autorise le gestionnaire à
   déconnecter les installations intermittentes sans stockage dès 30 % de la puissance
   transitant sur le réseau, la Corse bénéficiant d'un seuil relevé à 35 %.
2. Le **rapport de PPE à l'Assemblée** annonce « *un accroissement progressif du seuil de
   déconnexion à 35 % en 2018 et 45 % en 2023* ».
3. Surtout, l'**article 4 du décret n° 2015-1697, dans sa version consolidée en vigueur**
   (dernière modification : 3 juillet 2023) : « *En Corse, le seuil de déconnexion des
   installations de production mettant en œuvre de l'énergie fatale à caractère aléatoire
   mentionné à l'article L. 141-9 du code de l'énergie est fixé à 35 % en 2018.* » Les 45 %
   y restent un objectif pour 2023, jamais un seuil applicable.

**Le fait le plus net tient à une date.** La révision de juin 2023 est intervenue l'année
même de l'échéance des 45 %. Elle a relevé les objectifs de puissance — le photovoltaïque au
sol passe de +20 à +100 MW — mais **elle n'a pas touché au seuil de déconnexion**. Le
plafond qui produit l'écrêtement de T5 est donc, à ce jour, celui fixé pour 2018.

C'est le même geste que le contrôle croisé OREGES sur T7, et il vaut la même chose : un
lecteur institutionnel ne peut pas renvoyer le chiffre à une interprétation maison.

### Le second écart : le Vazzio, cinq ans après son arrêt annoncé

La PPE de 2015 est explicite : passé le quota de 18 000 heures de dérogation couvrant
2020-2023, « *l'installation devra être mise définitivement à l'arrêt* ». **La centrale
fonctionne toujours en 2026** — le ministère parlait encore en 2023 de « *la vétusté de la
centrale actuelle du Vazzio* », et elle reste l'une des dernières de France au fioul lourd.

Son remplaçant explique le décalage sans l'effacer. La centrale du **Ricanto** :

- **130 MW**, huit moteurs, alimentés en **bioliquides** — huile de colza ou de tournesol ;
- environ **20 % de la consommation annuelle de l'île**, jusqu'à **40 % la nuit** ;
- près de **800 M€**, chantier lancé le **22 novembre 2024** ;
- **mise en service prévue en 2028**, livraison annoncée au second semestre 2027 ;
- à l'été 2026, les moteurs sont en cours d'installation, au rythme d'un par semaine.

Le choix des bioliquides a été arrêté par l'Assemblée de Corse le **30 mars 2023** — la même
délibération que la révision simplifiée. Un risque d'arrêt du projet a existé : à l'été 2024,
l'arrêté ministériel fixant le tarif de rachat n'était pas publié, ce qui menaçait le
calendrier. Il a été levé, la CRE ayant salué l'aboutissement du projet.

**Ce que ça donne, factuellement : une installation dont l'arrêt définitif était programmé
pour fin 2023 assurera la production jusqu'en 2028 au moins.** Cinq ans. Ce n'est pas un
manquement à imputer à quiconque — construire 130 MW prend le temps que ça prend — mais
c'est un écart daté entre une programmation et sa réalisation, et il se dit sans
commentaire. Il touche aussi le sujet de proximité déjà identifié : le thermique de nos
courbes, c'est le Vazzio et Lucciana.

**2028 est donc trois fois structurante** : terme de la période de programmation, mise en
service du Ricanto, et horizon cité dans le débat public local. La date que l'utilisateur
avait en tête tenait, même si le motif n'était pas celui qu'on croyait.

Nuance à ne jamais perdre, déjà écrite dans le code : **ce n'est pas un mur physique mais un
droit de débrancher.** La part réelle peut dépasser le seuil — c'est précisément ce que T8
montre.

## Ce qu'il faut vérifier avant de figer

*Vérifié le 04/08/2026 et clos : la révision a bien été publiée, mais sous forme simplifiée
(décret n° 2023-554 du 30 juin 2023). Aucune programmation propre à 2024-2028 n'a été prise :
le décret de 2015 reste le texte de base, avec ses échéances 2018 et 2023. La cible
d'environ 62 % d'ENR électriques en 2028, vue en source secondaire, ne figure dans aucun des
textes lus — **ne pas la reprendre**.*

*Vérifié le 04/08/2026 et clos : le Vazzio devait s'arrêter fin 2023 ; il tourne encore, et
son remplaçant n'entrera pas en service avant 2028. Voir ci-dessous.*

**Rien n'est plus ouvert à ce stade du cadrage.** Ce qui suit relève de la rédaction, pas de
la vérification préalable.

## Test du prompt

Rapprocher le paragraphe « seuil de déconnexion » d'une PPE de 2015 d'une série horaire EDF
2019-2024 empreintée, dans un périmètre écrit, n'est pas à portée d'un LLM généraliste en
quinze minutes. Le différenciant tient aux trois mêmes piliers : donnée fraîche, pipeline
récurrent, manifeste daté et empreinté.

## Définition de « fini »

- [ ] chaque cible citée textuellement, avec son périmètre et sa source
- [ ] chaque confrontation cible/mesure verrouillée par un test, comme le contrôle croisé
      OREGES l'est déjà (36,0 / 29,8 contre leurs 36 / 29,8)
- [ ] les trois vérifications ci-dessus tranchées, ou l'affirmation retirée
- [ ] aucune phrase prescriptive, aucune position sur le statut de l'île

## Anti-dérive

Ce cadrage ne rouvre pas le sujet air, qui reste traité pour lui-même et ne parle pas à la
PPE. Il ne rouvre pas non plus la question de la publication : l'assemblage se déduira de
l'objectif une fois celui-ci tenu.

## Sources

- PPE pour la Corse, **rapport annexé au décret** (73 p.) — la cible des 40 % d'ENR
  électriques y est p. 13, le dénominateur p. 10 —
  <https://www.ecologie.gouv.fr/sites/default/files/documents/PPE%20Corse%20-%20Rapport.pdf>
- PPE pour la Corse 2016-2018 / 2019-2023, rapport à l'Assemblée de Corse —
  <https://www.aue.corsica/attachment/649449/>
- Programmation pluriannuelle de l'énergie, DREAL Corse —
  <https://www.corse.developpement-durable.gouv.fr/programmation-pluriannuelle-de-l-energie-ppe-r621.html?lang=fr>
- Révision de la PPE pour la Corse (2019-2023 / 2024-2028), AUE —
  <https://www.aue.corsica/Revision-de-la-Programmation-Pluriannuelle-de-l-Energie-pour-la-Corse-2019-2023-2024-2028_a272.html>
- Décret n° 2015-1697 du 18 décembre 2015 relatif à la PPE de Corse, **version consolidée**
  (art. 4 : seuil de déconnexion) — <https://www.legifrance.gouv.fr/loda/id/JORFTEXT000031645870>
- Décret n° 2023-554 du 30 juin 2023 portant modification du décret n° 2015-1697 —
  <https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047774402>
- Publication de la révision simplifiée de la PPE pour la Corse, communiqué du ministère —
  <https://www.ecologie.gouv.fr/presse/publication-revision-simplifiee-programmation-pluriannuelle-lenergie-corse>
- Arrêté du 23 avril 2008 modifié (seuil de déconnexion des ENR variables) et Lettre OREGES
  2021, p. 8 — déjà cités dans `figures.py`, en tête de `fig_t8_seuil_deconnexion`.
- Centrale du Ricanto, page projet EDF PEI — <https://pei.edf.fr/nos-implantations/projet-corse-centrale-du-ricanto>
- Lancement du chantier de la centrale bioénergie du Ricanto, communiqué EDF du 22/11/2024 —
  <https://www.edf.fr/groupe-edf/espaces-dedies/journalistes/tous-les-communiques-de-presse/le-groupe-edf-lance-le-chantier-de-construction-de-la-centrale-bioenergie-du-ricanto-en-corse>
- Délibération CRE du 4 avril 2024 (taux de rémunération, Ricanto) —
  <https://www.cre.fr/fileadmin/Documents/Deliberations/2024/240404_2024-67_Taux_Ricanto.pdf>

> Les faits relatifs au Ricanto et au Vazzio sont **à re-vérifier juste avant publication** :
> ce sont des faits vivants (calendrier de chantier, date de mise en service), pas des
> constats clos. Même règle que pour toute actualité citée en intro.
