"""Note méthodologique du sujet air, exportée en HTML dans outputs/.

Usage :
    python -m demonstrateur.note_air

Elle fait partie du livrable, pas de la documentation interne : elle se déploie avec les
figures et se lit dans le même cadre. D'où le HTML plutôt qu'un markdown de `docs/`.

**Tout ce qu'elle affiche de chiffré est LU, jamais recopié** — dates de collecte prises
dans la lignée de build, effectifs et bornes calculés sur les Parquet au moment de
l'écriture. Une note méthodologique qui vieillit en silence est pire que pas de note :
elle donne la caution du sérieux à des chiffres faux.
"""

from __future__ import annotations

import sys

import duckdb

from .config import DATA_PROCESSED, OUTPUTS
from .prepare import verifier_sorties
from .viz import PALETTE, SANS, date_collecte

SERIE = (DATA_PROCESSED / "air_serie.parquet").as_posix()
METEO = (DATA_PROCESSED / "meteo_corse.parquet").as_posix()
MDA8 = (DATA_PROCESSED / "air_o3_mda8.parquet").as_posix()


def _chiffres() -> dict:
    con = duckdb.connect()
    air = con.execute(f"""
        SELECT count(*), count(DISTINCT station), min(date_locale), max(date_locale),
               count(*) FILTER (WHERE verification = 1)
        FROM '{SERIE}'""").fetchone()
    meteo = con.execute(f"""
        SELECT count(*), count(DISTINCT num_poste), min(date_locale), max(date_locale)
        FROM '{METEO}'""").fetchone()
    jours = con.execute(f"SELECT count(*) FROM '{MDA8}' WHERE valide").fetchone()[0]
    return dict(
        air_h=air[0], air_st=air[1], air_d1=air[2], air_d2=air[3], air_verif=air[4],
        meteo_h=meteo[0], meteo_p=meteo[1], meteo_d1=meteo[2], meteo_d2=meteo[3],
        jours=jours,
        collecte_air=date_collecte("aee_o3_venaco_continu"),
        collecte_meteo=date_collecte("meteo_horaire_corse"),
    )


def _html(c: dict) -> str:
    n = lambda v: f"{v:,}".replace(",", " ")  # noqa: E731 — séparateur de milliers français
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Note méthodologique — l'ozone en Corse</title>
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
<p class="chapeau">Note méthodologique — sujet « l'ozone en Corse ».
Données collectées le {c["collecte_air"]}.</p>

<h2>Ce que cette étude regarde</h2>
<p>L'ozone des <strong>jours ordinaires</strong> : ceux où aucun seuil d'alerte n'est
approché, et dont aucun communiqué ne parle. Les épisodes de pollution, eux, sont déjà
suivis et signalés par Qualitair Corse, qui alerte les médias régionaux quand un seuil est
franchi. Ce dispositif fonctionne ; cette étude ne s'y substitue pas. Elle regarde l'autre
moitié du temps.</p>

<h2>D'où viennent les mesures</h2>
<p>Toutes les mesures d'air sont produites par <strong>Qualitair Corse</strong>, l'association
agréée pour la surveillance de la qualité de l'air sur l'île. Elles transitent par le
LCSQA / Ineris, qui les transmet à l'Europe ; c'est par ce canal européen qu'elles sont
reprises ici. Autrement dit : ce ne sont pas d'autres mesures que les leurs, c'est le même
relevé pris à une autre porte.</p>
<div class="scroll"><table>
<tr><th>Jeu</th><th>Producteur</th><th>Licence</th><th>Collecté le</th></tr>
<tr><td>Ozone et dioxyde d'azote, {c["air_st"]} stations, mesures horaires</td>
    <td>Agence européenne pour l'environnement — mesures Qualitair Corse, rapportées par le
        LCSQA/Ineris</td>
    <td>CC-BY 4.0, attribution à l'AEE</td><td>{c["collecte_air"]}</td></tr>
<tr><td>Températures horaires, {c["meteo_p"]} postes corses</td>
    <td>Météo-France — données climatologiques de base</td>
    <td>Licence Ouverte 2.0 (Etalab)</td><td>{c["collecte_meteo"]}</td></tr>
</table></div>
<p><strong>{n(c["air_h"])} mesures horaires</strong> d'air, du {c["air_d1"]} au
{c["air_d2"]}, dont {n(c["air_verif"])} portent le statut « vérifié » du producteur — les
plus récentes ne l'ont pas encore, et c'est normal : la vérification vient après.
Côté températures, {n(c["meteo_h"])} relevés du {c["meteo_d1"]} au {c["meteo_d2"]}.</p>

<h2>Comment les chiffres sont calculés</h2>
<p>Deux repères réglementaires reviennent, et ils <strong>ne comptent pas la même
chose</strong> :</p>
<ul>
<li><span class="cle">120 µg/m³</span> — l'objectif de qualité pour la santé. Il porte sur le
    plus fort niveau de la journée, calculé en moyenne sur huit heures glissantes.</li>
<li><span class="cle">180 µg/m³</span> — le seuil à partir duquel le public est informé. Il
    porte sur une simple moyenne d'une heure.</li>
</ul>
<p>La moyenne sur huit heures n'est publiée par aucune des sources : elle est recalculée
ici, en suivant à la lettre le guide du producteur (LCSQA/Ineris, guide de calcul des
statistiques de qualité de l'air). Une journée n'est retenue que si elle réunit assez de
mesures valides pour que son maximum soit opposable — <strong>{n(c["jours"])} journées</strong>
le sont. Le calcul est vérifié contre l'exemple chiffré publié dans ce guide.</p>
<p>Les heures signalées comme douteuses par les producteurs sont écartées avant tout calcul,
côté air comme côté température.</p>

<h2>Ce que ces chiffres ne disent pas</h2>
<ul>
<li><strong>Que la chaleur fabrique l'ozone.</strong> Les journées chaudes en portent
    davantage, c'est mesuré. Mais les jours chauds sont aussi les jours ensoleillés et sans
    vent, et rien dans des mesures de concentration ne permet de démêler ce qui revient à
    l'un ou à l'autre. On lit une <strong>coïncidence</strong>, pas une cause.</li>
<li><strong>D'où vient cet ozone.</strong> Une concentration ne porte pas d'étiquette
    d'origine. Une part se forme loin de l'île et y arrive avec le vent ; la chiffrer
    demanderait un modèle, pas des mesures.</li>
<li><strong>Ce qui a causé un pic.</strong> Aucune de ces mesures ne désigne une
    installation, un navire ou une route.</li>
</ul>

<h2>Les approximations, assumées</h2>
<ul>
<li><strong>Le thermomètre n'est pas au pied de l'analyseur.</strong> Chaque station d'air a
    été rapprochée du poste météo dont le climat ressemble le plus au sien — pas
    nécessairement le plus proche. Pour Venaco, seule station de campagne, c'est Vivario :
    Corte est plus près, mais sa cuvette encaissée creuse les écarts de température d'une
    façon qui fausserait la comparaison. Chaque figure nomme le poste utilisé.</li>
<li><strong>Une station est récente.</strong> Ajaccio Confina 2 ne mesure que depuis
    janvier 2024, quand les cinq autres remontent à 2006-2011. Ses effectifs sont donc plus
    faibles, ce que les figures indiquent au survol.</li>
<li><strong>Les figures portent toutes le même périmètre</strong> — étés 2020 à 2025,
    stations dites « de fond », journées valides — pour que deux chiffres pris sur deux
    figures puissent se lire l'un à côté de l'autre.</li>
</ul>

<h2>Refaire ces chiffres</h2>
<p>Rien n'a été téléchargé ni saisi à la main. Chaque source est déclarée dans un fichier de
configuration, avec sa licence et son producteur ; à la collecte, son empreinte numérique
est enregistrée et re-vérifiée à chaque exécution — une donnée qui aurait changé sous nos
pieds ferait échouer la préparation plutôt que de passer inaperçue. Chaque chiffre publié
est par ailleurs verrouillé par un test : si l'un d'eux cessait d'être vrai, c'est la phrase
qu'il faudrait réécrire, et le test le dirait avant la mise en ligne.</p>

<h2>Citer</h2>
<p>Mesures : Qualitair Corse, via l'Agence européenne pour l'environnement (CC-BY 4.0) et le
LCSQA / Ineris. Températures : Météo-France (Licence Ouverte 2.0). Ces organismes ne sont
pas associés à cette étude et n'en ont pas validé les conclusions.</p>

</main></body></html>
"""


def main() -> int:
    verifier_sorties()
    dest = OUTPUTS / "a0_note_methodologique.html"
    dest.write_text(_html(_chiffres()), encoding="utf-8")
    print(f"[ok] {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
