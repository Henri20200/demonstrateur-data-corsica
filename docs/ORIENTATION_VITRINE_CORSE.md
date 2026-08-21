# Orientation — Vitrine Corse

> **Note d'origine — migration du 21/08/2026.** Cette orientation a été élaborée
> initialement dans le dépôt `tourisme-corse` (commits `7d1ca84` pour la version 1,
> `9c3de7c` pour celle-ci). Elle devient **canonique ici à compter du présent commit**,
> parce que `demonstrateur-data-corsica` porte le produit public et les études que cette
> doctrine gouverne. `tourisme-corse` redevient un laboratoire thématique et ne porte plus
> la règle générale du projet : le document y est remplacé par un pointeur et **ne doit
> plus y être modifié**. Pas de miroir — deux copies actives finiraient par diverger.

**Version 2 — 21/08/2026.** Document de référence. Remplace `Nouvelle orientation du
projet — Vitrine Corse.md`, qui décrivait la bonne vision avec la mauvaise taille.

**Ce qui a changé entre les deux versions.** La première transformait une vision de long
terme en architecture immédiate : huit piliers thématiques, un socle de plusieurs dizaines
de séries, une page « La Corse aujourd'hui ». C'est la structure qu'appelait implicitement
l'appel à projet FEDER « Data & IA au service de l'intérêt général » — partenariats,
plateforme, interopérabilité, service public de la donnée. Cet appel a été examiné et
écarté le 21/08 : il donne accès à des données non publiques, donc il place le choix des
sujets sous la tutelle du financeur, et sa clause de pérennité fait d'un changement de
sujet une dette. La décision est cohérente ; il restait à retirer du projet les traces de
cette architecture. Les huit piliers en étaient une.

**Vision large, exécution étroite.** La vision ne bouge pas : comprendre la Corse par les
données, replacer les phénomènes dans leur histoire, les confronter à la Sardaigne ou aux
Baléares quand cela éclaire vraiment. Ce qui change est la manière de la construire — non
plus horizontalement, thème après thème, mais verticalement, étude après étude.

---

## 1. La question directrice

> Que se passe-t-il en Corse aujourd'hui, qu'est-ce qui est inhabituel, et qu'est-ce qui est
> réellement spécifique à l'île ?

Elle est inchangée. Ce sont les moyens qui se réduisent.

## 2. Ce que le projet n'est pas

Ni un portail open data, ni un catalogue d'indicateurs, ni un observatoire exhaustif, ni un
moteur de prévision. L'INSEE, l'ISTAT, IBESTAT, l'ADEC, l'ATC, l'AUE et Qualitair Corse
restent les sources de référence dans leur domaine. La valeur est ailleurs : croiser,
contextualiser, comparer, expliquer, rendre auditable.

**Et depuis cette version : ce n'est pas non plus un tableau de bord.** Le permanent est
rare ; le publié s'accumule sans dette.

---

## 3. Les six contraintes

### C1 — Profondeur avant largeur

La vitrine s'étend **étude par étude**. Aucun thème n'entre dans le périmètre permanent
avant qu'une première étude approfondie ait démontré qu'il apporte quelque chose que la
simple republication des données n'apporte pas.

Les huit domaines de la version 1 — population, logement, activité, tourisme, mobilités,
énergie, ressources, agriculture — ne sont pas des piliers. Ce sont des **domaines
potentiels d'étude**. Au démarrage, il en existe **un seul effectivement assumé et
maintenu**.

Raison : une personne seule répartie sur huit domaines produit dans chacun quelque chose de
moins profond qu'une publication institutionnelle, et se retrouve à concurrencer les
institutions sur leur terrain — ce que le §2 interdit. La largeur ne nourrit pas la
crédibilité, elle la dilue.

### C2 — Études avant dashboards

Une étude historique, une fois publiée et figée, **coûte presque zéro**. Un indicateur
« aujourd'hui » **coûte à perpétuité**. Ce ne sont pas les mêmes objets économiquement, et
ils ne se décident pas de la même façon.

Conséquence : le vivant est plafonné à **une dizaine d'indicateurs** au départ, pas
« quelques dizaines ». Chaque ajout au-delà en retire un.

### C3 — La comparaison est un instrument, pas un décor

Sardaigne en comparateur structurel principal, Baléares en comparateur thématique. Jamais
mécaniquement : avant d'ajouter un territoire, il faut pouvoir dire en quoi il change la
compréhension du phénomène. Une troisième courbe n'est pas un argument.

**Verrou préalable, non levé à ce jour.** Une comparaison Corse–Sardaigne n'entre pas dans
une figure parce que deux colonnes portent le même nom. Cinq points se vérifient avant :

> **définition · périmètre · unité · calendrier · ruptures de série**

Rien ne garantit que l'enquête INSEE de fréquentation et son équivalent ISTAT soient le
même appareil de mesure — univers des établissements, échantillonnage, traitement du non
hôtelier, politique de révision. Comparer deux taux, ce peut être comparer deux
définitions. **Un `VERIF_ISTAT_*` sur pièce est requis avant la première figure comparée**,
sur le modèle de `VERIF_FREQUENTATION_INSEE.md`. Pronostic à vérifier, pas à supposer : ce
qui survit à ce type de comparaison est rarement le niveau, souvent la forme — amplitude
saisonnière, date de bascule, dispersion inter-annuelle.

### C4 — Indépendance éditoriale, écrite avant le premier commanditaire

Une institution étudiée qui commande ensuite une étude n'est pas en conflit d'intérêts :
c'est la situation ordinaire de la recherche contractuelle, de l'audit et du conseil. Le
danger apparaît si elle peut acheter le résultat, sa formulation ou sa disparition.

Règles, arrêtées avant qu'il y ait de l'argent en jeu :

1. Une commande peut financer une nouvelle analyse, approfondir un sujet, ou produire un
   travail privé distinct. Elle **ne donne aucun droit de modification ou de retrait** sur
   les résultats publics déjà publiés.
2. Le commanditaire peut **signaler une erreur factuelle** ; il **ne valide pas les
   conclusions**.
3. Toute modification substantielle d'un contenu public reste **tracée**.
4. Une étude commandée destinée à être publique indique **clairement son commanditaire**.
5. Un travail confidentiel reste **séparé de la vitrine** et ne peut pas réécrire
   rétrospectivement ce qui y est publié.
6. **La question d'une étude est fixée et versionnée avant l'analyse.**

**Sur la règle 6 — la pré-inscription.** Elle traite le risque que les cinq premières
laissent passer. Personne ne demandera de modifier un résultat publié : c'est trop visible,
et la règle 3 suffit. Ce qui arrive réellement est l'**effet de sélection** — on choisit peu
à peu des sujets adjacents à l'argent, et on cesse de choisir ceux qui gêneraient un
prospect. Rien n'est modifié, donc rien n'est traçable, et la dérive reste invisible même
pour celui qui la commet. Fixer la question avant d'en connaître la réponse est la seule
parade qui ne coûte rien.

Elle reste **légère**. Cinq points suffisent, versionnés ou publiés avant l'analyse :

- la **question** ;
- les **données prévues** ;
- le **comparateur** envisagé, s'il y en a un ;
- le **critère d'arrêt** ;
- l'**intention de publier quel que soit le résultat**.

Pas un protocole académique de dix pages. Ce qui compte est la date, pas le volume.

Ces principes reprennent volontairement ceux de la charte de la donnée de la Collectivité —
transparence, ouverture, fiabilité, mise à jour — **sans entrer dans le dispositif
institutionnel** qui les accompagne.

### C5 — Hypothèse commerciale falsifiable

« Je publie des travaux excellents → je deviens crédible → on me commande des études » est
une **hypothèse**, pas un modèle économique. Le projet a exigé de chaque mesure une
baseline, un témoin et une barre chiffrée. La thèse commerciale subit le même traitement,
sans quoi le projet peut réussir intellectuellement et ne jamais exister économiquement.

L'expérience commerciale s'écrit **en même temps** que l'expérience éditoriale :

```
étude phare publiée
  → diffusion ciblée (presse, contacts directs)
  → conversations avec les acteurs concernés
  → mesure des demandes entrantes et des besoins exprimés
  → première proposition commerciale
```

**Critère d'échec, arrêté le 21/08/2026 :**

> Après **12 conversations** avec des organisations plausiblement commanditaires, et au plus
> tard le **31 janvier 2027**, si aucune n'a formulé — spontanément ou après discussion —
> une **question concrète qu'elle envisagerait de payer** pour faire traiter, l'hypothèse
> « la vitrine génère une activité d'études » est considérée comme **non validée**.

Le critère ne porte pas sur un chiffre d'affaires, qui serait arbitraire à ce stade, mais
sur la **nature des réponses obtenues**. Il peut donc échouer proprement.

**Ce qu'il déclenche, et ce qu'il ne déclenche pas.** Il n'oblige pas à arrêter le projet.
Il oblige à **cesser de présenter ce mécanisme comme modèle économique** — donc à en
chercher un autre, ou à assumer que la vitrine est autre chose qu'une activité.

**Pourquoi ces deux nombres.** Douze conversations sortent de l'anecdote sans transformer le
projet en campagne commerciale à plein temps. Fin janvier laisse le temps de terminer
l'étude énergie, de la publier correctement, de la diffuser, et d'avoir des échanges après
la période de fin d'année.

**Surface de conversion.** Une publication optimisée pour produire des lecteurs alors que
l'hypothèse économique repose sur des commanditaires est une erreur de cible. Après avoir
lu une étude, un décideur doit comprendre sans effort qu'il peut demander :

- une étude analogue sur son territoire ou son problème ;
- l'approfondissement d'une étude publiée ;
- la construction d'un indicateur spécifique ;
- l'analyse de données qu'il détient et que la vitrine publique n'a pas.

Ni boutique, ni tarifs, ni catalogue artificiel. Mais « Vous avez une question territoriale
ou des données à analyser ? » doit **mener quelque part**.

### C6 — Règle d'arrêt

Les cinq contraintes précédentes disent ce qu'il ne faut pas faire. Aucune ne dit quand une
étude est finie, et « une étude remarquable » est une cible qui recule à mesure qu'on
avance.

Une étude est **terminée et publiable** quand les quatre conditions sont réunies :

1. **la question annoncée** — celle de la pré-inscription (C4.6) — a reçu une réponse
   étayée, **y compris négative** ;
2. les principaux **tests contradictoires raisonnables** ont été faits ;
3. les **limites** sont explicites ;
4. **ce qui n'a pas été fait** est écrit.

Le gel ÉTABLI / INCONNU du §7 s'applique au moment de publier.

> « Il reste des choses intéressantes à explorer » ne doit **jamais** empêcher de publier.

Une question restée ouverte devient l'étude suivante, pas un retard sur celle-ci.

---

## 4. La première verticale : l'énergie

Ce n'est pas un choix arbitraire — c'est le seul domaine où la preuve de profondeur existe
déjà :

- deux études publiées et vivantes (électricité, ozone), 38 sources empreintées en SHA-256,
  lignée `_build.json`, figures verrouillées par tests, cron 6 h ;
- un croisement mesuré : part hydraulique du mix corse de **12,3 % (2022) à 22,0 % (2023)**,
  thermique en sens inverse, **corrélation −0,95** — publié avec sa réserve, qui est
  l'argument le plus fort du travail : ces chiffres ne démontrent pas que la sécheresse en
  est la cause ;
- un angle daté et vérifiable, la PPE : seuil de déconnexion promis à 45 % pour 2023,
  toujours à 35 % ; Vazzio qui devait être « mis définitivement à l'arrêt » fin 2023 et
  tourne encore, son remplaçant prévu en 2028 ;
- une fenêtre qui se referme : la prochaine PPE se prépare vraisemblablement en
  **2026-2027**.

La comparaison sarde y apporte réellement quelque chose — deux systèmes insulaires non
interconnectés, deux mix, deux trajectoires.

**Le tourisme n'est pas jeté.** Il devient la deuxième candidate, et doit mériter son
entrée par C1. Le travail des derniers jours n'est pas perdu : le résidu de la baseline
calendaire par mois (**1,93 pt en cœur de saison, 2,97 pt aux épaules**) est exactement ce
qui autorise ou interdit d'écrire « inhabituel » ; et l'effet d'année local à la
Corse-du-Sud, absent de la Haute-Corse, est une question plus intéressante que « prévoir le
tourisme ». Ce sont des matériaux d'étude, pas un tableau de bord permanent.

---

## 5. Où vit quoi — deux dépôts, deux fonctions

Arrêté le 21/08/2026.

| Dépôt | Fonction |
|---|---|
| **`demonstrateur-data-corsica`** | produit public — vitrine, études publiées, chaîne de collecte, traçabilité, **et le présent document** |
| **`tourisme-corse`** | laboratoire thématique — investigations et données propres au tourisme |

**La doctrine vit avec le produit public, pas avec le laboratoire.** Un laboratoire
thématique ne porte pas la règle générale du projet. Il n'en existe **qu'une copie active**
— celle-ci ; `tourisme-corse` n'en garde qu'un pointeur, et cesse de la modifier.

**Sur les branches :** la branche par défaut de `demonstrateur-data-corsica` est `master`,
celle de `tourisme-corse` est `main`. Ce document et les pré-inscriptions rejoignent
`master`. Le cron avance `master` plusieurs fois par jour, donc on ne cherche pas le
fast-forward à tout prix : un merge qui conserve intact le commit d'origine convient. Ce qui
doit survivre est le **hash**, pas une topologie linéaire.

La vitrine vit **dans `demonstrateur-data-corsica`**, parce que la chaîne éprouvée,
l'électricité, l'air, la publication et la lignée y sont déjà. Si la première verticale est
l'énergie, créer un dépôt de vitrine reviendrait à construire une enveloppe autour de ce qui
existe.

**Pas de troisième dépôt maintenant.** Et **pas de renommage immédiat** : le nom du dépôt
public se change quand l'objet public est stabilisé, pas avant. D'abord terminer la première
étude sous cette doctrine.

**Le passage du laboratoire à la vitrine est éditorial, pas technique.** Si `tourisme-corse`
produit un jour une étude digne d'entrer dans la vitrine, c'est **l'étude** qui migre, sous
une forme éditoriale stabilisée. Le pipeline tourisme ne devient pas pour autant une
dépendance permanente de la page d'accueil.

Cette séparation évite aussi de faire de la vitrine un monorepo de toutes les
expérimentations.

---

## 6. Les indicateurs vivants et leur état

Quelques indicateurs seulement, plafonnés (C2), et qui **prolongent l'étude** plutôt que de
couvrir un domaine.

Une donnée dont l'alimentation casse ne doit **jamais** rester affichée silencieusement
comme actuelle. Chaque indicateur porte un état, qui se calcule et ne se déclare pas :

```
source dans sa fenêtre normale
publication probablement en retard
collecte en échec
fraîcheur inconnue
```

avec, dans tous les cas, sa dernière observation et sa date.

C'est l'inverse d'une dette cachée : **la vitrine montre aussi l'état de son propre système
de mesure**, et une panne devient une information publiée au lieu d'un mensonge silencieux.

**La cadence attendue n'a pas le même sens partout** — c'est ce qui rend le quatrième état
nécessaire plutôt qu'embarrassant. Certaines sources ont une cadence fixe ; d'autres n'ont
qu'une **fenêtre** : l'INSEE tourisme publie à 5 à 7 semaines, ce qui est une fourchette
mesurée, pas un calendrier. Un système qui traduirait une cadence mal connue en alerte
fabriquerait de **fausses alertes**, c'est-à-dire exactement le bruit qui décrédibilise.
Quand la cadence n'est pas établie, l'état honnête est « inconnue », et il s'affiche.

**Coût réel de cette machine : un champ.** Le nécessaire existe déjà — empreinte SHA-256,
`first_observed_at`, `dernier_controle`, `superseded_at`, lignée, cron ; et `collecte.py`
distingue déjà « rien n'a changé » de « nous ne regardions pas ». Il manque **la cadence de
publication attendue par source** — valeur fixe, fenêtre, ou explicitement inconnue —, sans
laquelle « retard de la source » et « collecte en échec » sont indiscernables.

---

## 7. Format d'une étude

Trois niveaux de lecture, et une structure stable.

| Niveau | Contenu | Rubriques |
|---|---|---|
| 1 — le constat | une phrase immédiatement compréhensible | question, réponse courte, **ce qu'on ne sait pas** |
| 2 — la preuve | peu de figures, chacune avec une fonction | figures, comparaison, pourquoi cela compte |
| 3 — la méthode | de quoi refaire le calcul | source, période, fraîcheur, transformations, unités, limites, révisions |

Le citoyen s'arrête au niveau 1 ou 2 ; le décideur, le journaliste ou le chercheur descend
au niveau 3.

**« Ce que l'on ne sait pas » appartient au niveau 1**, pas au niveau 3. L'honnêteté est la
différenciation : enterrée dans la méthode, elle n'est visible que du lecteur qui en a le
moins besoin. Et le niveau 3 n'est pas de la documentation — c'est la surface où un
prospect décide d'appeler.

**Trois statuts, toujours distingués :** ÉTABLI (ce que les données démontrent) /
INTERPRÉTATION (ce que les résultats suggèrent raisonnablement) / HYPOTHÈSE (ce qui
pourrait expliquer sans être démontré). Un résultat statistique ne se rebaptise pas avec un
mécanisme non établi.

**Droit au résultat négatif.** Une étude peut conclure qu'un phénomène est stable, qu'il n'y
a pas de signal, que deux territoires ne sont pas comparables, que l'hypothèse initiale est
fausse, ou que la donnée ne permet pas de répondre. Montrer qu'il n'y a rien à conclure est
une composante de la crédibilité, pas un échec. Ce droit ne survit que si « rien
d'inhabituel » peut être publié — ce qui suppose de savoir ce qu'« inhabituel » veut dire,
c'est-à-dire une dispersion mesurée.

---

## 8. Dire « inhabituel » a un prix

C'est le point où la version 1 se contredisait : elle rétrogradait la prévision (§17) tout
en faisant de « qu'est-ce qui est inhabituel ? » un critère de succès (§29). Or affirmer
qu'une valeur est inhabituelle est une affirmation sur une distribution : il faut un modèle
de l'habituel et sa dispersion. C'est le même problème que la prévision à un pas, présenté
autrement.

Donc, sans exception : **aucun indicateur dérivé — écart à la normale, percentile
historique, indice de tension, indice de saturation — ne se publie sans sa période de
référence, le nul contre lequel il est mesuré, et l'effectif indépendant qui le soutient.**
Faute de quoi ce sont des constructions, pas des mesures. Ce sont précisément celles qui
ont l'air rigoureuses.

La prévision, elle, reste possible mais conditionnelle : cible réellement variable,
variabilité structurée, information disponible assez tôt, gain supérieur à une baseline
simple, et rattachement à une décision. Sinon, le descriptif suffit.

---

## 9. Traçabilité

Chaque donnée suivie durablement se relie à sa source, son URL, sa date de collecte, son
empreinte, son millésime, son statut, ses révisions, et la transformation qui mène à
l'indicateur publié. La question à laquelle cette architecture répond :

> Que savions-nous réellement à la date où une analyse a été publiée ?

Les producteurs révisent leurs séries et leurs schémas — le 04/06/2026 l'INSEE a renommé
deux mesures et cessé de diffuser `DAYS_STAY`. Les millésimes sont une information, pas une
précaution technique.

---

## 10. Critère de succès

Deux critères, et ils sont **indépendants**.

**Éditorial** — la capacité à répondre régulièrement et rigoureusement à trois questions :
qu'est-ce qui change actuellement en Corse ; qu'est-ce qui est inhabituel par rapport à son
histoire ; qu'est-ce qui lui est réellement spécifique face à un territoire pertinent.

**Commercial** — le critère de C5 : 12 conversations, 31 janvier 2027.

Le premier peut être atteint pendant que le second échoue. C'est précisément ce qu'il faut
pouvoir constater — c'est ce qui empêche de sauver artificiellement la thèse commerciale
parce que l'étude reçoit de bons retours.

---

## 11. Ce qui n'est pas tranché dans ce document

- **Quels indicateurs vivants** composent la dizaine de C2. Ils doivent sortir de l'étude
  énergie, pas la précéder.
- **La comparaison sarde** reste bloquée sur le `VERIF_ISTAT_*` de C3 — travail à faire,
  pas décision à prendre.
- **La deuxième verticale** n'est pas choisie. Le tourisme est candidat, pas retenu.
- **La cartographie des micro-régions**, nécessaire à toute étude touristique fine, n'a pas
  de source : `DS_TOUR_FREQ` s'arrête au département, vérifié et négatif.
- **Le sort du fichier `Nouvelle orientation du projet — Vitrine Corse.md`** : il n'a jamais
  été commité, donc git n'en conserve rien. Le supprimer maintenant le détruirait. Trois
  options — le committer puis le retirer dans un commit suivant (l'histoire le garde, HEAD
  ne l'a plus), le déplacer dans une archive datée, ou le supprimer en acceptant la perte.
