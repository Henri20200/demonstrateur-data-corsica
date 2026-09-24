"""Dossier public de reproduction d'un résultat, reconstruit avec les mêmes données."""

import csv
import hashlib
import html
import io
import json
import math
import tempfile
import zipfile
from pathlib import Path

import duckdb
import yaml

from . import calcul_demande
from .config import DATA_PROCESSED, DATA_RAW, OUTPUTS, SOURCES_FILE
from .prepare import verifier_sorties
from .provenance import verifier
from .viz import PALETTE, SANS

SOURCE = "edf_courbe_charge_horaire"
CSV = "demande-juin-juillet.csv"
ZIP = "verification-demande.zip"
PAGE = "verification-demande.html"


def _extraire(source: Path) -> bytes:
    tampon = io.StringIO(newline="")
    ecrivain = csv.DictWriter(tampon, fieldnames=calcul_demande.CHAMPS,
                             delimiter=";", lineterminator="\n")
    ecrivain.writeheader()
    with source.open(encoding="utf-8-sig", newline="") as flux:
        for ligne in csv.DictReader(flux, delimiter=";"):
            if ligne["territoire"] != "Corse":
                continue
            date = ligne["date_heure"]
            if int(date[:4]) in calcul_demande.ANNEES and date[5:7] in ("06", "07"):
                ecrivain.writerow({champ: ligne[champ] for champ in calcul_demande.CHAMPS})
    return tampon.getvalue().encode("utf-8")


def _page(preuve: dict) -> str:
    r, source = preuve["resultat"], preuve["source"]
    echappe = html.escape
    lignes = "".join(
        f"<tr><th scope='row'>{nom.capitalize()}</th><td>{r[nom]['heures']}</td>"
        f"<td>{r[nom]['moyenne_mw']:.6f}</td><td>{r[nom]['affiche_mw']}</td></tr>"
        for nom in ("juin", "juillet")
    )
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vérifier la hausse de demande entre juin et juillet</title>
<style>
body {{ margin:0; padding:2rem 1.2rem; font:17px/1.65 {SANS};
        color:{PALETTE["ink"]}; background:{PALETTE["page"]}; }}
main {{ max-width:52rem; margin:auto; }} h1 {{ font-size:2rem; line-height:1.2; }}
h2 {{ font-size:1.3rem; margin-top:2rem; }} a {{ color:{PALETTE["accent"]}; }}
.cle {{ font-size:1.2rem; padding:1rem; background:{PALETTE["surface"]};
        border-left:3px solid {PALETTE["accent"]}; }}
table {{ border-collapse:collapse; width:100%; font-size:15px; }}
th,td {{ text-align:left; padding:.65rem; border-bottom:1px solid {PALETTE["rule"]}; }}
.table {{ overflow:auto; }} code {{ overflow-wrap:anywhere; }}
pre {{ padding:1rem; overflow:auto; background:{PALETTE["surface"]}; }}
footer {{ border-top:1px solid {PALETTE["rule"]}; margin-top:2rem; padding-top:1rem; }}
</style></head><body><main>
<nav><a href="index.html">Accueil</a> · <a href="etude.html">L'électricité corse</a>
 · <a href="t0_note_methodologique.html">Note méthodologique</a></nav>
<h1>Retrouver les +{r["ecart_affiche_pct"]} % entre juin et juillet</h1>
<p class="cle">La demande moyenne de juillet dépasse celle de juin d'environ
{r["ecart_affiche_pct"]} %, sur les années 2019 à 2024 prises ensemble.</p>
<p>Ce dossier permet de contrôler un résultat précis de l'étude. Il contient les
mesures horaires utilisées, conservées dans leurs colonnes d'origine, et un calcul
autonome. Il ne constitue pas une validation externe de l'ensemble de l'étude.</p>
<p><a href="{ZIP}" download><strong>Télécharger les données et le calcul</strong></a>
— fichier ZIP, sans compte.</p>
<h2>1. Vérifier le périmètre</h2>
<p>Producteur : {echappe(source["producteur"])}. Données collectées le
{echappe(source["date_collecte"])}. Licence : {echappe(source["licence"])}.</p>
<p><a href="{echappe(source["url"], quote=True)}">Export CSV du producteur</a>.
Ce lien peut aujourd'hui fournir une version révisée. L'empreinte du fichier utilisé
ici est conservée dans le dossier ; le CSV joint en est un extrait limité à la Corse,
aux mois de juin et juillet et aux années 2019–2024.</p>
<p>Les statuts « validé » et « estimé » sont conservés, comme dans l'étude.
La colonne EDF <code>production_totale_mw</code> comprend les importations et sert
ici de mesure de la demande. Ses étiquettes horaires sont lues en heure légale corse,
sans convertir leur suffixe trompeur <code>+00:00</code>. Aucun changement d'heure
ne tombe en juin ou en juillet.</p>
<h2>2. Refaire le calcul</h2>
<p>Pour chaque mois, additionner les mesures horaires et diviser par le nombre
d'heures. Chaque heure a le même poids. On compare les moyennes de puissance en MW,
pas les volumes d'énergie des deux mois, dont la durée diffère.</p>
<div class="table"><table><thead><tr><th>Mois</th><th>Heures</th>
<th>Moyenne (MW)</th><th>Barre affichée (MW)</th></tr></thead>
<tbody>{lignes}</tbody></table></div>
<p>Sur les moyennes non arrondies : <strong>{r["ecart_pct"]:.6f} %</strong>.
Le graphique arrondit d'abord les deux barres au MW, puis son annotation au pour cent :</p>
<pre>100 × ({r["juillet"]["affiche_mw"]} − {r["juin"]["affiche_mw"]}) / {r["juin"]["affiche_mw"]}
≈ {r["ecart_affiche_pct"]} %</pre>
<p>Dans un tableur, ouvrir le CSV avec le séparateur point-virgule et le point
comme séparateur décimal, puis calculer la moyenne pour chaque mois.</p>
<p>Avec Python 3, décompresser le dossier et exécuter :</p>
<pre>python verifier_demande.py</pre>
<p>Le script utilise seulement la bibliothèque standard. Il vérifie l'empreinte
du CSV, l'absence de doublons et les 720 ou 744 heures attendues pour chaque
mois de chaque année, puis affiche les moyennes et l'écart. Il ne se connecte à aucun service.</p>
<h2>3. Lire les limites</h2>
<p>Cet écart ne mesure ni la part du tourisme ni celle de la climatisation.
Il ne décrit pas les pointes instantanées et ne prédit pas la consommation de 2026.
Une empreinte identifie un fichier ; elle ne garantit pas l'exactitude des mesures
du producteur. Les conventions et approximations complètes figurent dans la
<a href="t0_note_methodologique.html">note méthodologique</a>.</p>
<footer><p>Une réserve sur le calcul ou un usage à discuter :
<a href="mailto:contact@methodes-revelations.fr">contact@methodes-revelations.fr</a>
 · <a href="https://www.methodes-revelations.fr/">Méthodes &amp; Révélations</a>.</p>
</footer></main></body></html>
"""


def main() -> int:
    build = verifier_sorties()
    info = build["sources"][SOURCE]
    source = DATA_RAW / info["filename"]
    verifier(source, info)
    extrait = _extraire(source)
    with tempfile.TemporaryDirectory(prefix="preuve-demande-", dir=OUTPUTS) as dossier:
        csv_path = Path(dossier) / CSV
        csv_path.write_bytes(extrait)
        resultat = calcul_demande.calculer(csv_path)
    courbe = DATA_PROCESSED / "edf_courbe_corse.parquet"
    with duckdb.connect() as con:
        annees = con.execute(
            "SELECT DISTINCT annee_locale FROM read_parquet(?) ORDER BY 1", [str(courbe)]
        ).fetchall()
        if tuple(a[0] for a in annees) != calcul_demande.ANNEES:
            raise ValueError("La période de l'étude a changé : revoir le dossier de vérification.")
        moyennes = dict(con.execute(
            "SELECT mois_local, avg(production_totale_mw) FROM read_parquet(?) "
            "WHERE mois_local IN (6, 7) GROUP BY 1", [str(courbe)]
        ).fetchall())
    for mois, nom in ((6, "juin"), (7, "juillet")):
        if not math.isclose(resultat[nom]["moyenne_mw"], moyennes[mois], abs_tol=1e-7):
            raise ValueError("L'extrait source ne reproduit pas les données de la figure.")
    if resultat["ecart_affiche_pct"] != 22:
        raise ValueError("Le résultat de l'étude a changé : revoir les textes avant publication.")
    declaration = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))["sources"][SOURCE]
    preuve = {
        "perimetre": "Corse, juin et juillet 2019-2024, toutes les heures, validé et estimé",
        "source": {**info, **{k: declaration[k] for k in ("url", "licence", "producteur")}},
        "extrait_sha256": hashlib.sha256(extrait).hexdigest(),
        "resultat": resultat,
        "generation": {k: build.get(k) for k in ("genere_le", "commit", "arbre_modifie")},
    }
    fichiers = {
        CSV: extrait,
        "verifier_demande.py": Path(calcul_demande.__file__).read_bytes(),
        "provenance.json": json.dumps(preuve, ensure_ascii=False, indent=2).encode("utf-8"),
        "LIRE-MOI.txt": (
            "Méthodes & Révélations — vérifier le résultat juin-juillet 2019-2024.\n"
            "Décompresser les quatre fichiers ensemble.\n"
            "Tableur : CSV séparé par ; et nombres décimaux avec un point.\n"
            "Python 3, sans dépendances ni réseau : python verifier_demande.py\n"
            "provenance.json identifie la source, l'extrait et la génération.\n"
            "L'extrait conserve les colonnes EDF pour la Corse, juin-juillet 2019-2024.\n"
            "Ne pas convertir le suffixe horaire +00:00 : calendrier local corse.\n"
            "Source : EDF — Open Data Groupe EDF. Licence Ouverte (Etalab).\n"
            "Écart de puissance moyenne, sans attribution au tourisme ou à la climatisation.\n"
            "Contact : contact@methodes-revelations.fr\n"
        ).encode("utf-8"),
    }
    with zipfile.ZipFile(OUTPUTS / ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for nom, contenu in fichiers.items():
            # Une nouvelle exécution à données égales ne change pas les dates internes du ZIP.
            entree = zipfile.ZipInfo(nom, date_time=(1980, 1, 1, 0, 0, 0))
            entree.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entree, contenu)
    (OUTPUTS / PAGE).write_text(_page(preuve), encoding="utf-8", newline="\n")
    print(f"[ok] {PAGE} et {ZIP} — résultat et extrait source concordants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
