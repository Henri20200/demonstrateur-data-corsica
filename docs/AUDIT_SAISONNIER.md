# Audit saisonnier de la courbe de charge corse

*Les tableaux qui fondent le chapitre « En été, les heures les plus chargées gagnent
64 MW en six ans » et la figure T10.*

Ce document ne se saisit pas à la main. Il se régénère :

```bash
python -m demonstrateur.prepare          # si data/processed n'est pas à jour
python -m demonstrateur.audit_saisonnier # imprime exactement les tableaux ci-dessous
```

`tests/test_audit_saisonnier.py` rejoue cette commande et vérifie que chaque tableau
figure **verbatim** dans cette page. Une donnée EDF qui bougerait ferait donc échouer la
suite de tests, plutôt que de laisser ce document se désaligner en silence.

## Périmètre et conventions

Source : `data/processed/edf_courbe_corse.parquet`, construit par
`demonstrateur.prepare` depuis la courbe de charge horaire EDF (Corse & Outre-mer),
filtrée sur la Corse. Le brut est vérifié contre son empreinte de manifeste avant toute
lecture, et la lignée est écrite dans `data/processed/_build.json`.

**Heure légale corse.** L'étiquette `+00:00` de ce jeu est fausse : il porte l'heure
légale corse, établi le 23/08/2026 par trois mesures indépendantes (cf.
`docs/VERIF_ENTSOE_TERNA.md` § 5). Les colonnes `annee_locale`, `mois_local` et
`heure_locale` en dérivent, et les six heures qui n'existent pas en heure légale
(02 h des dimanches de passage à l'heure d'été) sont retirées. Tout ce qui suit est donc
calculé sur l'heure locale corrigée, jamais sur l'étiquette publiée.

**Saisons.** L'été est juin-septembre ; le découpage est sans effet sur le résultat,
juillet-août seuls, juin-septembre et mai-octobre donnant les six mêmes maxima. L'hiver
est décembre-février et porte le millésime de son mois de décembre : l'hiver 2023/24 est
décembre 2023 plus janvier et février 2024. Un hiver est dit complet au-delà de 2 100
heures (décembre + janvier + février ≈ 2 160 ; un mois seul ≈ 744).

**Statut des valeurs.** EDF classe 2019-2020 comme validées et 2021-2024 comme estimées.
La traçabilité des fichiers ne dit rien du statut des valeurs qu'ils contiennent : les
deux sont distincts, et une étiquette de statut constante ne prouve pas l'homogénéité de
la méthode d'estimation sur toute la période.

## Tableaux

**Étés (juin-septembre)**

| Été | heures | maximum | moy. 20 h hautes | médiane | heures ≥ 380 MW |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2019 | 2928 | 371.4 | 365.7 | 249.9 | 0 |
| 2020 | 2928 | 376.5 | 363.1 | 235.3 | 0 |
| 2021 | 2928 | 389.1 | 380.0 | 259.0 | 9 |
| 2022 | 2928 | 406.9 | 401.2 | 273.8 | 111 |
| 2023 | 2928 | 433.4 | 418.7 | 257.0 | 141 |
| 2024 | 2928 | 435.3 | 417.8 | 251.4 | 102 |

**Quantiles des heures d'été (MW)**

| Été | médiane | q75 | q90 | q99 | maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2019 | 249.9 | 299.1 | 325.2 | 358.7 | 371.4 |
| 2020 | 235.3 | 276.5 | 316.2 | 353.7 | 376.5 |
| 2021 | 259.0 | 294.1 | 330.9 | 368.8 | 389.1 |
| 2022 | 273.8 | 317.4 | 354.5 | 393.7 | 406.9 |
| 2023 | 257.0 | 304.1 | 355.8 | 406.6 | 433.4 |
| 2024 | 251.4 | 309.1 | 350.3 | 404.6 | 435.3 |
| **2019 → 2024** | **+1.5** | **+10.1** | **+25.0** | **+45.9** | **+63.9** |

**Hivers (décembre-février, millésimés par leur décembre)**

| Hiver | heures | complet | maximum | mois du maximum |
| --- | ---: | ---: | ---: | ---: |
| 2018/19 | 1416 | non — écarté | 473.1 | janvier |
| 2019/20 | 2184 | oui | 426.1 | janvier |
| 2020/21 | 2160 | oui | 477.5 | janvier |
| 2021/22 | 2160 | oui | 447.7 | janvier |
| 2022/23 | 2160 | oui | 467.9 | février |
| 2023/24 | 2184 | oui | 421.6 | janvier |
| 2024/25 | 744 | non — écarté | 434.5 | décembre |

**Écart été − hiver précédent (hivers complets)**

| Été | pointe de l'été | pointe de l'hiver précédent | écart |
| --- | ---: | ---: | ---: |
| 2020 | 376.5 | 426.1 | -49.6 |
| 2021 | 389.1 | 477.5 | -88.5 |
| 2022 | 406.9 | 447.7 | -40.8 |
| 2023 | 433.4 | 467.9 | -34.5 |
| 2024 | 435.3 | 421.6 | +13.8 |

**Petite hydraulique : périmètre du total**

| Année | heures sans valeur | moyenne annuelle | plus fort écart absolu aux 20 h d'été hautes |
| --- | ---: | ---: | ---: |
| 2019 | 0 | 4.91 | 0.22 |
| 2020 | 0 | 7.06 | 1.57 |
| 2021 | 0 | 7.78 | 0.44 |
| 2022 | 0 | 5.43 | 0.19 |
| 2023 | 0 | 8.00 | 0.29 |
| 2024 | 8783 | — | — |
