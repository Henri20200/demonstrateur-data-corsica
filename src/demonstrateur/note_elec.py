"""Note méthodologique du sujet électricité, exportée en HTML dans outputs/.

Usage :
    python -m demonstrateur.note_elec

Pendant de `note_air` pour l'autre sujet, et même régime : elle fait partie du livrable,
pas de la documentation interne. Elle se déploie avec les figures.

**Tout ce qu'elle affiche de chiffré est LU, jamais recopié** : heures couvertes, part
estimée, bornes et dates de collecte sont calculées sur les Parquet et la lignée de build
au moment de l'écriture. Les seuils réglementaires et le taux de dépendance de l'OREGES
sont importés de `figures`, où ils sont déjà définis — écrits ici aussi, ils finiraient
par diverger.

L'étude (`docs/etude.md`, chapitres 5 et 6) expose la même méthode en prose, pour qui la
lit en entier. Cette note s'adresse à qui veut vérifier sans lire l'étude : une page, les
licences, et des chiffres relus à chaque rafraîchissement.
"""

from __future__ import annotations

import sys

import duckdb

from .config import DATA_PROCESSED, OUTPUTS
from .figures import (
    ANNEE_VISEE,
    OREGES_CARBURANTS,
    OREGES_DEPENDANCE,
    SEUIL_CORSE,
    SEUIL_NATIONAL,
    SEUIL_VISE,
)
from .prepare import verifier_sorties
from .viz import PALETTE, SANS, date_collecte

COURBE = (DATA_PROCESSED / "edf_courbe_corse.parquet").as_posix()
MIX = (DATA_PROCESSED / "edf_mix_corse.parquet").as_posix()
ECRET = (DATA_PROCESSED / "edf_ecretement_corse.parquet").as_posix()
SARD_PATH = DATA_PROCESSED / "entsoe_sardaigne.parquet"


def _chiffres() -> dict:
    con = duckdb.connect()
    # Millésimes lus dans `annee_locale`, écrite par prepare depuis l'heure légale corse
    # établie contre le soleil (cf. sa docstring). Ni `extract` sur un horodatage à fuseau
    # — qui suivrait le fuseau de la SESSION, UTC sur le runner et Paris sur un poste
    # français, soit deux notes différentes pour la même donnée — ni une conversion écrite
    # ici : la convention se décide une fois, en préparation. Les heures couvertes se
    # comptent sur l'axe UTC, le seul où une heure vaut une heure : l'axe local en compte
    # 23 le dimanche de printemps et 25 celui d'automne.
    heures, an1, an2, estimees, sans_micro, couvertes = con.execute(f"""
        SELECT count(*),
               min(annee_locale),
               max(annee_locale),
               count(*) FILTER (WHERE lower(statut) LIKE 'estim%'),
               count(*) FILTER (WHERE micro_hydraulique_mw IS NULL),
               -- Heures que la période couvre, bornes comprises. C'est à elle que se
               -- compare le nombre de lignes retenues, et l'écart EST la limite publiée
               -- juste en dessous : écrit à la main, il se figerait le jour où la
               -- période s'allonge, dans une note qui promet de tout lire.
               datediff('hour', min(date_heure_utc), max(date_heure_utc)) + 1
        FROM '{COURBE}'""").fetchone()
    pas, mix_d1, mix_d2 = con.execute(f"""
        SELECT count(*),
               strftime(min(timezone('Europe/Paris', "date")), '%d/%m/%Y'),
               strftime(max(timezone('Europe/Paris', "date")), '%d/%m/%Y')
        FROM '{MIX}'""").fetchone()
    mois, ec1, ec2 = con.execute(
        f"SELECT count(*), min(annee), max(annee) FROM '{ECRET}'"
    ).fetchone()

    c = dict(
        heures=heures, an1=int(an1), an2=int(an2), estimees=estimees,
        validees=heures - estimees,
        part_estimee=round(100 * estimees / heures),
        couvertes=couvertes, manquantes=couvertes - heures,
        sans_micro=sans_micro, pas=pas, mix_d1=mix_d1, mix_d2=mix_d2,
        mois=mois, ec1=int(ec1), ec2=int(ec2),
        collecte_hist=date_collecte("edf_courbe_charge_horaire"),
        collecte_mix=date_collecte("edf_mix_temps_reel"),
        collecte_ecret=date_collecte("edf_ecretement_corse"),
        sard=None,
    )
    # La Sardaigne demande un jeton ENTSO-E : sans elle, le reste de la note tient —
    # elle disparaît alors du tableau plutôt que d'y figurer sans chiffres (comme
    # `figures` saute T6). Une ligne de tableau vide serait un sourçage qui ment.
    if SARD_PATH.exists():
        n, sa1, sa2 = con.execute(
            f"SELECT count(*), min(annee), max(annee) FROM '{SARD_PATH.as_posix()}'"
        ).fetchone()
        c["sard"] = dict(heures=n, an1=int(sa1), an2=int(sa2),
                         collecte=date_collecte("entsoe_sardaigne_2024"))
    return c


def _html(c: dict) -> str:
    n = lambda v: f"{v:,}".replace(",", " ")  # noqa: E731 — séparateur de milliers français
    virgule = lambda v: f"{v}".replace(".", ",")  # noqa: E731
    s = c["sard"]
    ligne_sard = "" if not s else f"""
<tr><td>Production sarde par filière, {n(s["heures"])} heures ({s["an1"]}-{s["an2"]})</td>
    <td>ENTSO-E, plateforme de transparence des réseaux européens — données Terna</td>
    <td>CC-BY 4.0, attribution à ENTSO-E</td><td>{s["collecte"]}</td></tr>"""
    phrase_sard = "" if not s else (
        f" La Sardaigne ajoute {n(s['heures'])} heures, de {s['an1']} à {s['an2']}.")
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Note méthodologique — l'électricité corse</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin:0; padding:2.2rem 1.4rem 3rem; background:{PALETTE["surface"]};
          color:{PALETTE["ink"]}; font-family:{SANS}; font-size:17px; line-height:1.62; }}
  main {{ max-width:47rem; margin:0 auto; }}
  h1 {{ font-size:1.75rem; line-height:1.25; margin:0 0 .3rem; }}
  h2 {{ font-size:1.16rem; margin:2.2rem 0 .6rem; padding-top:1.1rem;
        border-top:1px solid {PALETTE["rule"]}; }}
  p, li {{ margin:.55rem 0; }}
  .chapeau {{ color:{PALETTE["ink_soft"]}; font-size:1.03rem; margin-bottom:.4rem; }}
  table {{ border-collapse:collapse; width:100%; margin:.8rem 0; font-size:15.5px; }}
  th, td {{ text-align:left; padding:.55rem .6rem; border-bottom:1px solid {PALETTE["rule"]};
            vertical-align:top; }}
  th {{ font-weight:600; }}
  .scroll {{ overflow-x:auto; }}
  strong {{ font-weight:600; }}
  .cle {{ color:{PALETTE["accent"]}; font-weight:600; }}
</style></head><body><main>

<h1>Comment ces chiffres ont été obtenus</h1>
<p class="chapeau">Note méthodologique — sujet « de quoi est faite l'électricité corse ».
Données collectées le {c["collecte_hist"]}.</p>

<h2>Ce que cette étude regarde</h2>
<p>De quoi est fait le courant servi en Corse : quelle filière produit quoi, heure par
heure et saison par saison, et ce qui arrive par les câbles sous-marins. L'île n'est pas
raccordée au réseau français continental. EDF exploite son système électrique et en publie
les mesures. Ce sont celles-là.</p>
<p>Seule l'<strong>électricité</strong> est traitée. Les carburants, le fioul et le gaz du
chauffage sont hors sujet. La différence est grande : dans toute l'énergie consommée en
Corse, les carburants pèsent {virgule(OREGES_CARBURANTS)} % à eux seuls, et ils ne
contiennent aucun kilowattheure.</p>

<h2>D'où viennent les mesures</h2>
<p>Quatre jeux de données, tous publiés en accès libre, tous téléchargés par programme
chez leur producteur.</p>
<div class="scroll"><table>
<tr><th>Jeu</th><th>Producteur</th><th>Licence</th><th>Collecté le</th></tr>
<tr><td>Production corse heure par heure, par filière, {n(c["heures"])} heures
        ({c["an1"]}-{c["an2"]})</td>
    <td>EDF — Open Data Groupe EDF (Corse &amp; Outre-mer)</td>
    <td>Licence Ouverte (Etalab)</td><td>{c["collecte_hist"]}</td></tr>
<tr><td>Mix électrique corse en temps réel, pas de 15 minutes</td>
    <td>EDF — Open Data Groupe EDF (production corse temps réel)</td>
    <td>Licence Ouverte 2.0 (Etalab)</td><td>{c["collecte_mix"]}</td></tr>
<tr><td>Limitations imposées au photovoltaïque, {c["mois"]} mois ({c["ec1"]}-{c["ec2"]})</td>
    <td>EDF — Open Data Groupe EDF (limitations sûreté système)</td>
    <td>Licence Ouverte 2.0 (Etalab)</td><td>{c["collecte_ecret"]}</td></tr>{ligne_sard}
</table></div>
<p>L'historique corse couvre <strong>{n(c["heures"])} heures</strong>, de {c["an1"]} à
{c["an2"]}.{phrase_sard} Le temps réel ne garde que les deux dernières semaines : au
dernier téléchargement, {n(c["pas"])} relevés de 15 minutes, du {c["mix_d1"]} au
{c["mix_d2"]}. Il est retéléchargé à chaque exécution.</p>
<p>Un cinquième chiffre est <strong>recopié, pas calculé</strong> : le taux de dépendance
énergétique de {virgule(OREGES_DEPENDANCE)} %. Il vient de la Lettre de l'OREGES de Corse
(Agence d'aménagement durable, d'urbanisme et d'énergie de la Corse), édition 2021,
données 2020. Il couvre toute l'énergie, pas seulement l'électricité. Les données EDF ne
permettent pas de le recalculer.</p>

<h2>Comment les chiffres sont calculés</h2>
<p>Une part de mix se calcule toujours pareil : les mégawatts d'une filière, divisés par
la production totale, <strong>sur les mêmes heures</strong>. Les producteurs datent leurs
mesures en temps universel. Elles sont converties en heure locale avant d'être regroupées
par heure, par mois ou par année.</p>
<p>Deux définitions comptent. Elles sont écrites sur les figures.</p>
<ul>
<li><span class="cle">Renouvelable décentralisé</span> : solaire, éolien, bioénergies et
    petite hydraulique. Les grands barrages sont comptés à part. Avec eux, le chiffre est
    presque le double. C'est pourquoi cette étude ne dit jamais « renouvelable » tout
    court.</li>
<li><span class="cle">Génération locale seule</span> : pour la comparaison avec la
    Sardaigne, les importations corses sont retirées et le reste ramené à 100 %. La
    Sardaigne exporte, et les données européennes ne lui donnent pas d'importations. Sans
    ce calage, les deux barres ne diraient pas la même chose.</li>
</ul>
<p>Le seuil qui permet de débrancher une installation solaire ou éolienne sans stockage
est lui aussi recopié. Il vient de l'arrêté du 23 avril 2008 : {SEUIL_NATIONAL} %
ailleurs, {SEUIL_CORSE} % en Corse. Le relèvement à {SEUIL_VISE} %, prévu pour
{ANNEE_VISEE}, n'a jamais eu lieu.</p>
<p>Deux titres tiennent à un fait que la donnée pourrait démentir : le solaire ne dépasse
jamais le thermique, même au plus haut ; l'hydraulique et le thermique varient en sens
inverse. Les deux sont revérifiés à chaque mise à jour. Si l'un devient faux, la figure
n'est pas dessinée.</p>

<h2>Ce que ces chiffres ne disent pas</h2>
<ul>
<li><strong>Pourquoi la demande augmente l'été.</strong> La hausse de juillet est mesurée,
    et elle a lieu le soir. Mais résidents, visiteurs et climatisation ne se distinguent
    pas dans une donnée de production. Ces figures montrent quand, pas pourquoi.</li>
<li><strong>Que la sécheresse fait baisser l'hydraulique.</strong> Les années les plus
    pauvres en eau sont les plus riches en thermique, c'est mesuré. La sécheresse, elle,
    vient d'une source extérieure : ces données ne contiennent aucune mesure de pluie, et
    un barrage garde plusieurs mois d'avance.</li>
<li><strong>Si une installation respecte le seuil.</strong> Le plafond ne vise que les
    installations sans batterie ; celles qui en ont une y échappent. Or la donnée EDF
    additionne les deux sans les distinguer. Ces courbes montrent donc à quel point
    l'ensemble du réseau s'approche du plafond, jamais si tel producteur est en règle.</li>
<li><strong>Ce qui est produit avec les ressources de l'île.</strong> Produit sur l'île
    n'est pas produit avec l'île : les centrales thermiques corses brûlent un combustible
    importé. Il y a trois périmètres — ce qui arrive par les câbles, ce qui est produit
    sur l'île, ce qui est produit avec ses ressources. Chaque figure dit lequel elle
    emploie.</li>
</ul>

<h2>Les approximations, assumées</h2>
<ul>
<li><strong>Deux tiers des heures sont estimées.</strong> EDF classe son historique :
    {n(c["validees"])} heures « validé », {n(c["estimees"])} « estimé », soit
    {c["part_estimee"]} %. Les conclusions ont été vérifiées séparément sur chaque
    moitié. Chaque visuel historique porte la mention.</li>
<li><strong>{n(c["heures"])} heures retenues.</strong> De {c["an1"]} à {c["an2"]}, soit
    {c["an2"] - c["an1"] + 1} années pleines, la période couvre {n(c["couvertes"])} heures.
    Il en manque {c["manquantes"]}. Elles tombent aux passages à l'heure d'été, quand on
    saute de deux heures du matin à trois : ces heures-là n'ont pas existé, et le fichier
    d'EDF les porte tout de même, à production nulle. Elles sont retirées avant calcul.
    Le total retenu sert de dénominateur à toutes les parts publiées.</li>
<li><strong>La petite hydraulique manque sur la dernière année.</strong> Sa colonne
    disparaît des données EDF sur {n(c["sans_micro"])} heures. Elle est comptée comme
    nulle : vérification faite, le total de production l'exclut aussi. Les parts restent
    justes.</li>
<li><strong>Le bridage se compte en heures, pas en électricité perdue.</strong> La donnée
    d'écrêtement dit combien de temps, au plus, un producteur a été bridé dans le mois.
    Elle ne dit pas combien de kilowattheures cela représente.</li>
<li><strong>Le seuil est instantané, nos mesures sont horaires.</strong> Une pointe de
    quelques minutes se noie dans la moyenne de son heure et n'apparaît nulle part. Les
    dépassements comptés ici sont donc un minimum : les vrais sont plus nombreux.</li>
<li><strong>Trois périodes, jamais mélangées.</strong> L'historique s'arrête fin
    {c["an2"]}, le temps réel commence à l'été 2026, l'écrêtement s'arrête en {c["ec2"]},
    dernier millésime publié. Aucun visuel n'en met deux sur le même axe.</li>
</ul>

<h2>Refaire ces chiffres</h2>
<p>Aucun fichier n'a été téléchargé ni saisi à la main. Chaque source est déclarée dans un
fichier de configuration, avec sa licence et son producteur. À la collecte, son empreinte
numérique est enregistrée, puis revérifiée à chaque exécution : une donnée modifiée depuis
fait échouer la préparation. Les contrôles sont bloquants. Une valeur absente est
examinée, jamais remplacée en silence ; une catégorie inconnue ou une année incomplète
arrête tout. Enfin, chaque chiffre publié est protégé par un test. S'il cesse d'être vrai,
le test le signale avant la mise en ligne.</p>

<h2>Citer</h2>
<p>Production corse et limitations : EDF, Open Data Groupe EDF (Licence Ouverte, Etalab).
Production sarde : ENTSO-E, plateforme de transparence, données Terna (CC-BY 4.0).
Dépendance énergétique : OREGES de Corse / AUE, Lettre 2021. Ces organismes ne sont pas
associés à cette étude et n'en ont pas validé les conclusions.</p>

</main></body></html>
"""


def main() -> int:
    verifier_sorties()
    dest = OUTPUTS / "t0_note_methodologique.html"
    # newline="\n" : sans lui, `write_text` traduit les fins de ligne selon la plateforme
    # et la page écrite sous Windows diffère de celle du runner Linux sur chaque ligne
    # (cf. la règle « le cron est seul propriétaire d'outputs/ » dans CLAUDE.md).
    dest.write_text(_html(_chiffres()), encoding="utf-8", newline="\n")
    print(f"[ok] {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
