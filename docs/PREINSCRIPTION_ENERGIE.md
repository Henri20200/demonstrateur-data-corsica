# Pré-inscription — étude énergie

> **État des connaissances lors de la pré-inscription — 21 août 2026.**
> Cette étude prolonge une exploration déjà engagée ; les résultats antérieurs connus sont
> déclarés ci-dessous.

Cette ligne est le point le plus important du document. Sans elle, la pré-inscription
donnerait rétrospectivement une apparence prospective à des hypothèses déjà informées par
les résultats — c'est-à-dire exactement la tricherie qu'elle est censée empêcher. La règle
C4.6 de la doctrine demande de fixer la question avant l'analyse ; elle ne demande pas de
faire semblant que l'analyse commence aujourd'hui.

**Document de référence, situé dans l'autre dépôt :**
`tourisme-corse/docs/ORIENTATION_VITRINE_CORSE.md`, version 2 du 21/08/2026. Les renvois
« C1 … C6 » et « §8 de l'orientation » qui suivent y pointent. La répartition vient du §5 de
cette doctrine — `demonstrateur-data-corsica` porte le produit public et les études,
`tourisme-corse` le laboratoire tourisme —, ce qui laisse pour l'instant la doctrine dans un
dépôt et l'étude qu'elle gouverne dans l'autre. Point à trancher, pas ici.

---

## 1. Question de l'étude

> Le système électrique corse est-il en train de suivre une trajectoire compatible avec les
> objectifs qui lui sont assignés, et qu'apprend la comparaison avec la Sardaigne sur ce qui
> relève réellement des contraintes insulaires ?

Elle combine situation actuelle, trajectoire, politique publique et comparateur, sans
présumer du résultat. Elle est plus étroite que « analyser l'énergie en Corse » et plus
large qu'une vérification d'objectif isolée.

---

## 2. Ce qui est déjà connu au 21 août 2026

Rien de ce qui suit ne pourra être présenté comme une découverte de cette étude.

**Mix et hydraulique**

- Part hydraulique du mix corse, 2019-2024 : 15,5 / 19,9 / 19,8 / **12,3** / **22,0** /
  19,2 %. Rapport 1,79 entre l'année la plus pauvre et la plus riche.
- Part thermique en sens inverse : 41,8 / 36,0 / 39,3 / **47,5** / 34,8 / 40,1 %.
  Corrélation **−0,95** entre les deux parts.
- Réserve déjà écrite sur la figure T9 : ces chiffres ne démontrent pas que la sécheresse en
  est la cause. Aucune mesure de pluie dans ces données, et un barrage de montagne intègre
  plusieurs mois de stock. Le lien avec la sécheresse est une hypothèse extérieure.
- Étude « De quoi est faite l'électricité corse » publiée, avec sa note méthodologique.
- T4 : sur la seule donnée de production, l'heure la plus verte est **14 h**.

**Comparaison Corse–Sardaigne — déjà construite et publiée (T6)**

- Mix de génération, moyenne 2019-2024, **à périmètre égal** : génération locale seule, les
  **27,8 % d'imports corses exclus** et le reste renormalisé ; la Sardaigne, exportatrice
  via SAPEI/SACOI, n'importe pas.
- Résultats déjà acquis : la Sardaigne (dix fois plus grande) fait **32 % de son courant au
  charbon et 32 % au gaz de synthèse (IGCC)**, quasi absents en Corse ; elle a **quinze fois
  plus d'éolien** ; la Corse compense par la grande hydraulique et les câbles.
- Limite déjà notée sur la figure : **Corse estimée à partir de 2021**.
- Source : ENTSO-E / Terna, `documentType=A75`, `processType=A16`, zone IT-Sardinia,
  six millésimes 2019-2024, `entsoe_sardaigne.parquet` dans la lignée `_build.json`.

**PPE et objectifs**

- Décret du 18 décembre 2015, retouché en 2019 puis en juin 2023, jamais remplacé.
- Seuil de déconnexion : **35 % en Corse** (arrêté du 23 avril 2008 ; 30 % ailleurs). Le
  relèvement à **45 % visé pour 2023 n'est jamais entré en vigueur** — et la Corse
  dépassait déjà le seuil avant l'échéance (T8). La modification de juin 2023 a relevé
  d'autres objectifs (solaire au sol de +20 à +100 MW) sans toucher au seuil.
- Vazzio : quota d'heures jusqu'en 2023, puis « mise définitivement à l'arrêt ». La centrale
  tourne encore. Ricanto : 130 MW, huit moteurs à bioliquides, environ 800 M€, chantier
  ouvert en novembre 2024, mise en service prévue **2028**.
- **2028 est la fin de la période en cours, pas la date de la prochaine révision.** La
  prochaine PPE se prépare vraisemblablement en 2026-2027.

**Chiffres et écarts déjà repérés, non tranchés**

- Un écart de périmètre non élucidé : la presse locale donne l'hydraulique à « 20 à 25 % »,
  nos données mesurent 12,3 à 22,0 % selon les années, moyenne autour de 18 %. Explication
  probable — puissance installée plutôt que production, ou micro-hydraulique incluse. **À
  trancher, pas à supposer.**
- Un chiffre à ne pas reprendre : environ 62 % d'électricité renouvelable en 2028, qui
  circule dans la presse et ne figure dans aucun texte officiel lu à ce jour.
- Un piège de vocabulaire : **énergie primaire ≠ électricité seule.** C'est ce qui fait dire
  « 86 % de dépendance » ici et « 68 % » là sans que personne ait tort.

**Défauts connus de la chaîne, déclarés pour ne pas être « découverts » en route**

Relevés par l'audit du 05/08/2026, et qui touchent précisément la comparaison sarde :

- la figure T6 combine EDF et ENTSO-E, mais **son pied ne porte que la date de
  `entsoe_sardaigne_2024`** ;
- la Sardaigne est traitée comme une source optionnelle testée par simple existence : si le
  plan courant ne peut plus construire son parquet mais qu'une ancienne copie demeure,
  **cette copie peut être relue sans appartenir à la lignée validée du build courant** ;
- la figure de dépendance combine des données EDF et des valeurs OREGES recopiées à la
  main, en affichant la date EDF.

**Infrastructure disponible** : 38 sources empreintées en SHA-256, lignée `_build.json`,
figures verrouillées par tests, cron 6 h, publication automatique.

---

## 3. Ce que l'étude cherchera encore à établir

- La **trajectoire réelle contre les objectifs dont l'échéance est passée** — et seulement
  ceux-là. On ne mesure pas 2028.
- Le **rôle respectif des filières** et son évolution dans le temps, au-delà de la moyenne
  2019-2024 déjà publiée.
- La **dépendance extérieure**, avec sa définition explicitée plutôt que supposée.
- La **variabilité et l'intermittence**, et ce qu'elles imposent au système.
- Ce que la comparaison sarde apprend sur la **part de l'insularité contre la part du
  choix** : deux îles non interconnectées au continent n'ont pas le même mix, et la question
  est de savoir ce qui, dans l'écart, relève de la contrainte et ce qui relève de décisions.
- Si l'écart hydraulique presse / mesure est bien un **effet de périmètre**.

---

## 4. Données et comparaison prévues

**Corse** — EDF Open Data : `edf_mix_temps_reel`, `edf_courbe_charge_horaire`,
`edf_ecretement_corse` ; météo horaire ; valeurs OREGES, à signaler comme recopiées.

**Sardaigne** — ENTSO-E / Terna, six millésimes 2019-2024. Génération métrée, **sans
imports**. Requiert un jeton `ENTSOE_TOKEN`.

**Verrou C3 — partiellement levé, partiellement ouvert.** À déclarer honnêtement :

| Point | État |
|---|---|
| périmètre (imports exclus, renormalisation) | **fait**, visible dans le sous-titre de T6 |
| calendrier / fuseau (Europe/Rome = Europe/Paris) | **fait**, documenté dans `sources.yaml` |
| correspondance des catégories de production ENTSO-E ↔ EDF | **à faire** |
| unités et sommation horaire → MWh | **à vérifier** (couverture complète supposée) |
| ruptures de série sur six ans | **à faire** |
| « Corse estimée à partir de 2021 » | **faiblesse connue, à quantifier** |

**Correction au document d'orientation.** C3 nomme le verrou `VERIF_ISTAT_*` : c'est
l'instrument du **tourisme**. Pour l'énergie, le comparateur est ENTSO-E / Terna, donc le
document à produire est un **`VERIF_ENTSOE_*`**. Le principe vaut, le nom était celui de
l'autre domaine.

Toute donnée ajoutée après la présente date doit être **visible dans l'historique** du
dépôt.

---

## 5. Tests contradictoires et critères d'interprétation

Fixés maintenant, pour qu'une étude sur la PPE ne soit pas conçue pour confirmer une thèse.

1. **Chercher explicitement les périodes qui contredisent le constat principal**, et les
   publier si elles existent.
2. **Tester si une différence Corse/Sardaigne disparaît après normalisation pertinente** —
   par habitant, par MWh produit, par km². Une différence qui ne survit pas à sa
   normalisation n'est pas un fait sur les territoires.
3. **Distinguer corrélation, synchronisme et causalité.** Cas concret déjà en main : la
   corrélation −0,95 entre parts hydraulique et thermique porte sur **deux parts d'un total
   contraint à 100 %**. Si l'hydraulique baisse, quelque chose doit monter — le nul n'est
   donc pas zéro. Ce qui reste informatif est **que ce soit spécifiquement le thermique** qui
   compense, plutôt que les imports ou les autres filières. C'est cela qu'il faut mesurer,
   et le −0,95 ne doit pas être présenté comme une découverte tant que la part mécanique
   n'est pas retirée.
4. **Ne jamais qualifier une valeur d'« inhabituelle » sans distribution historique**, sa
   période de référence et son effectif (§8 de l'orientation).
5. **Ne pas mesurer une cible dont l'échéance n'est pas passée.** 2028 n'est pas mesurable.
6. Séparer ce qui est **ÉTABLI**, ce qui est **INTERPRÉTATION**, ce qui est **HYPOTHÈSE**.

---

## 6. Règle d'arrêt et intention de publication

L'étude est terminée quand les quatre conditions de C6 sont réunies :

1. la question pré-inscrite au §1 a reçu une **réponse étayée**, y compris négative ;
2. les principaux **tests contradictoires raisonnables** du §5 ont été effectués ;
3. les **limites** sont explicites ;
4. **ce qui n'a pas été fait** est consigné.

« Il reste des choses intéressantes à explorer » n'empêche pas de publier.

**Intention de publication, quel que soit le résultat** — y compris :

- si la comparaison sarde s'avère finalement **peu informative** une fois les périmètres et
  les catégories alignés ;
- si la trajectoire **ne permet pas de conclure** sur la compatibilité avec les objectifs ;
- si l'écart de périmètre sur l'hydraulique explique platement la divergence avec la presse.

---

## 7. Ce que cette pré-inscription n'est pas

Ce n'est pas un protocole d'analyse : elle ne fixe ni les méthodes statistiques, ni les
figures, ni le plan de l'étude. Elle fixe **une question, une frontière de connaissance
datée, des tests contradictoires et une règle d'arrêt** — le minimum pour que la sélection
des sujets et le glissement des conclusions restent visibles.

Sa valeur tient entièrement à sa **date** et au fait qu'elle précède le travail restant. Une
modification ultérieure est permise, mais elle doit apparaître comme telle dans
l'historique : on ne réécrit pas une pré-inscription, on la complète en la datant.
