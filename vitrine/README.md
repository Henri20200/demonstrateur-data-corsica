# Accueil de Méthodes & Révélations

Ce dossier versionne la page d’accueil de `www.methodes-revelations.fr`,
avec la constellation de la Corse et les trois emplacements d’études.
La copie locale d’origine reste dans le dossier frère
`demonstrateur-data-corsica-fichiers`.

## Fichiers

- `index.html` : page autonome à ouvrir dans un navigateur.
- `vitrine-mr-source/build_index.py` : générateur Python, sans dépendance externe.
- `vitrine-mr-source/export_extrait.html` : export de référence utilisé par le générateur.
- `vitrine-mr-source/logo_export.png` : logo incorporé dans la page générée.

## Régénérer la page

Depuis la racine du dépôt :

```shell
python vitrine/vitrine-mr-source/build_index.py
```

La commande réécrit uniquement `vitrine/index.html`. Les ajustements de texte
et de style sont centralisés dans `TEXTE_RETOUCHES` et `CSS_RETOUCHES` du
générateur. Le HTML final embarque le logo, le SVG et les animations CSS ;
il ne charge aucun script ni aucune ressource distante.

## Mise en ligne

Le commit et le push sauvegardent ces fichiers sur GitHub. Ils ne déploient
pas cet accueil : le pipeline existant publie les pages de l’étude depuis
`outputs/`, tandis que la publication de cette page de présentation reste
une opération distincte. Voir `../docs/VITRINE.md` pour l’hébergement.
