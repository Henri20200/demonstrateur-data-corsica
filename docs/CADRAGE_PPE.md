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
la PPE de Corse est **distincte de la PPE nationale** et **co-élaborée** par le président de
la Collectivité et le représentant de l'État. Elle est adoptée par décret, après délibération
de l'Assemblée de Corse valant avis.

- Décret n° 2015-1697 du **18 décembre 2015**, modifié par décret du **13 décembre 2019**.
- Périodes : **2016-2018 / 2019-2023**, puis **2019-2023 / 2024-2028** pour la révision.
- La révision a été adoptée par l'Assemblée de Corse en **avril 2021**. En avril 2023, la
  presse spécialisée la décrivait encore comme attendue.

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

Toutes tirées du rapport de PPE à l'Assemblée de Corse (2016-2018 / 2019-2023). **Une cible
se recopie, elle ne se déduit pas** — même règle que la moyenne 8 h de l'ozone.

| Cible officielle | Périmètre | Échéance | Ce que le pipeline mesure |
|---|---|---|---|
| « près de **87 %** de sa consommation totale d'énergie primaire » vient de l'extérieur | énergie primaire | constat 2014 | T7 — 86,1 % en 2020 (OREGES) |
| seuil de déconnexion porté « à **35 %** en 2018, puis de **45 %** en 2023 » | ENR variables, électricité | 2018 et 2023 | T8 (heures au-dessus de 35 %), T5 (écrêtement) — **non tenu**, cf. ci-dessous |
| consommation d'électricité **2 254 GWh** (2015) → **2 614 GWh** en 2025 | électricité | 2025 | `edf_courbe_corse` 2019-2024 |
| pointe **502 MW** (2015) → **583 MW** en 2025 | électricité | 2025 | `edf_courbe_corse` |
| ENR garanties **+148 %** : petite hydraulique +12 MW, bois-énergie et bio-déchets +7 MW, PV et éolien avec stockage +30 MW | puissance installée | 2023 | registre EDF (étude carte solaire) |
| ENR intermittentes **+38 %** : PV sans stockage +20 MW, solaire thermodynamique +12 MW, éolien +12 MW | puissance installée | 2023 | registre EDF |
| Vazzio : dérogation de 18 000 h entre 2020 et 2023, puis « l'installation devra être mise définitivement à l'arrêt » | thermique | 2023 | hors pipeline — fait à sourcer |

### Le point qui porte le sujet — et il est déjà établi

La PPE prévoyait de relever le seuil de déconnexion **à 45 % en 2023**. Il ne l'a pas été :
le seuil applicable reste **35 %**, et c'est lui qui produit l'écrêtement visible en T5.

Ce constat ne repose pas sur une lecture unique. `figures.py` le tenait déjà de la **Lettre
OREGES 2021, p. 8**, avec son fondement réglementaire — l'**arrêté du 23 avril 2008 modifié**,
qui autorise le gestionnaire à déconnecter les installations intermittentes sans stockage dès
30 % de la puissance transitant sur le réseau, la Corse bénéficiant d'un seuil relevé à 35 %.
La lecture du **rapport de PPE lui-même** (« *un accroissement progressif du seuil de
déconnexion à 35 % en 2018 et 45 % en 2023* ») le **confirme indépendamment, au document
primaire**. Deux sources, deux producteurs, même trajectoire annoncée — et une échéance
passée sans effet.

C'est le même geste que le contrôle croisé OREGES sur T7, et il vaut la même chose : un
lecteur institutionnel ne peut pas renvoyer le chiffre à une interprétation maison.

Nuance à ne jamais perdre, déjà écrite dans le code : **ce n'est pas un mur physique mais un
droit de débrancher.** La part réelle peut dépasser le seuil — c'est précisément ce que T8
montre.

## Ce qu'il faut vérifier avant de figer

1. **La révision 2024-2028 a-t-elle été publiée par décret ?** Non confirmé. Une source
   secondaire évoque une signature attendue à mi-2025 et une cible d'environ 62 % d'ENR dans
   l'électricité en 2028 — **ne pas reprendre ces chiffres** tant qu'ils ne sont pas lus dans
   le document lui-même.
2. **L'arrêt du Vazzio** : effectif ou non, et son remplacement (cycle combiné d'environ
   250 MW en région ajaccienne). Fait local, donc sourcé à la rédaction, jamais de mémoire.

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

- PPE pour la Corse 2016-2018 / 2019-2023, rapport à l'Assemblée de Corse —
  <https://www.aue.corsica/attachment/649449/>
- Programmation pluriannuelle de l'énergie, DREAL Corse —
  <https://www.corse.developpement-durable.gouv.fr/programmation-pluriannuelle-de-l-energie-ppe-r621.html?lang=fr>
- Révision de la PPE pour la Corse (2019-2023 / 2024-2028), AUE —
  <https://www.aue.corsica/Revision-de-la-Programmation-Pluriannuelle-de-l-Energie-pour-la-Corse-2019-2023-2024-2028_a272.html>
- Arrêté du 23 avril 2008 modifié (seuil de déconnexion des ENR variables) et Lettre OREGES
  2021, p. 8 — déjà cités dans `figures.py`, en tête de `fig_t8_seuil_deconnexion`.
