"""Tests de la traçabilité AUD-01 : empreinte canonique (chemins précis), vérification,
construction atomique et lignée de build.

Auto-suffisants (tmp_path, pas de réseau ni de Parquet réel) : ils tournent dans `pytest`
sans dépendre de fetch-data + prepare, contrairement aux tests de résultats.
"""

import json
from pathlib import Path

import re

import pytest

from demonstrateur.config import OUTPUTS
from demonstrateur.provenance import EmpreinteDivergente, empreinte, verifier

# Réponse ENTSO-E miniature : enveloppe de document (mRID, createdDateTime) + un TimeSeries
# porteur de son PROPRE mRID (donnée stable) et d'une quantité.
_XML = """<?xml version="1.0" encoding="UTF-8"?>
<GL_MarketDocument xmlns="urn:test">
  <mRID>{doc}</mRID>
  <createdDateTime>{cree}</createdDateTime>
  <TimeSeries>
    <mRID>{ts}</mRID>
    <Period>
      <Point><position>1</position><quantity>{q}</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>
"""
# Chemins PRÉCIS : seule l'enveloppe de document, jamais les mRID imbriqués des TimeSeries.
IGNORE = {"empreinte_ignore_xml": ["GL_MarketDocument/mRID", "GL_MarketDocument/createdDateTime"]}


def _xml(tmp_path, nom, *, doc="d" * 32, cree="2026-01-01T00:00:00Z", ts="1", q="100"):
    p = tmp_path / nom
    p.write_text(_XML.format(doc=doc, cree=cree, ts=ts, q=q), encoding="utf-8")
    return p


def test_empreinte_canonique_ignore_enveloppe(tmp_path):
    """Même donnée, enveloppe de document différente (mRID + date) -> MÊME empreinte :
    le SHA-256 certifie la donnée, pas le transport."""
    a = _xml(tmp_path, "a.xml", doc="a" * 32, cree="2026-01-01T00:00:00Z")
    b = _xml(tmp_path, "b.xml", doc="b" * 32, cree="2026-07-20T13:56:21Z")
    assert empreinte(a, IGNORE) == empreinte(b, IGNORE)


def test_empreinte_canonique_sensible_a_la_donnee(tmp_path):
    """Une vraie différence de donnée (quantité) change l'empreinte canonique."""
    a = _xml(tmp_path, "a.xml", q="100")
    c = _xml(tmp_path, "c.xml", q="200")
    assert empreinte(a, IGNORE) != empreinte(c, IGNORE)


def test_empreinte_canonique_preserve_mrid_imbrique(tmp_path):
    """Ciblage par CHEMIN : le mRID d'un TimeSeries (donnée) n'est PAS neutralisé — deux
    documents qui n'en diffèrent QUE là ont des empreintes différentes (point 4 de la revue)."""
    a = _xml(tmp_path, "a.xml", ts="1")
    d = _xml(tmp_path, "d.xml", ts="9")
    assert empreinte(a, IGNORE) != empreinte(d, IGNORE)


def test_empreinte_brute_par_defaut(tmp_path):
    """Sans déclaration, l'empreinte porte sur les octets bruts : toute différence compte."""
    a = tmp_path / "a.csv"
    a.write_text("x;y\n1;2\n", encoding="utf-8")
    b = tmp_path / "b.csv"
    b.write_text("x;y\n1;3\n", encoding="utf-8")
    assert empreinte(a, {}) != empreinte(b, {})
    assert empreinte(a, {}) == empreinte(a, {})


def test_verifier_detecte_divergence(tmp_path):
    """verifier renvoie l'empreinte si elle correspond, lève sinon."""
    p = tmp_path / "d.csv"
    p.write_text("territoire;valeur\nCorse;1\n", encoding="utf-8")
    bon = empreinte(p, {})
    assert verifier(p, {"sha256": bon}) == bon
    with pytest.raises(EmpreinteDivergente):
        verifier(p, {"sha256": "0" * 64})


def test_verifier_lit_la_politique_de_l_entree(tmp_path):
    """verifier lit `empreinte_ignore_xml` DANS l'entrée de manifeste : prepare est ainsi
    découplé de sources.yaml."""
    a = _xml(tmp_path, "a.xml", doc="a" * 32)
    entree = {"sha256": empreinte(a, IGNORE),
              "empreinte_ignore_xml": IGNORE["empreinte_ignore_xml"]}
    b = _xml(tmp_path, "b.xml", doc="b" * 32, cree="2026-07-20T00:00:00Z")
    assert verifier(b, entree) == entree["sha256"]  # même donnée, enveloppe différente


def test_date_collecte_prefere_la_lignee(tmp_path, monkeypatch):
    """viz.date_collecte renvoie la date de la lignée (donnée réellement dans le Parquet),
    pas celle du manifeste ; repli sur le manifeste sans lignée."""
    from demonstrateur import viz

    manifest = tmp_path / "_manifest.json"
    manifest.write_text(json.dumps({"src": {"date_collecte": "2026-07-20"}}), encoding="utf-8")
    build = tmp_path / "_build.json"
    build.write_text(
        json.dumps({"sources": {"src": {"date_collecte": "2026-07-19"}}}), encoding="utf-8"
    )
    monkeypatch.setattr(viz, "MANIFEST_FILE", manifest)
    monkeypatch.setattr(viz, "BUILD_FILE", build)
    assert viz.date_collecte("src") == "2026-07-19"  # lignée de build
    build.unlink()
    assert viz.date_collecte("src") == "2026-07-20"  # repli manifeste


def test_flux_complet_brut_build_sortie(tmp_path, monkeypatch):
    """Flux complet (point 5) : brut divergent -> prepare refuse ; build réussi -> sortie
    + empreinte inscrites dans la lignée ; sortie altérée -> publication refusée."""
    from demonstrateur import prepare

    raw = tmp_path / "raw"
    raw.mkdir()
    proc = tmp_path / "processed"
    proc.mkdir()
    src = raw / "mini.csv"
    src.write_text("a,b\n1,2\n", encoding="utf-8")
    manifest = raw / "_manifest.json"
    manifest.write_text(
        json.dumps({"mini": {"filename": "mini.csv", "sha256": empreinte(src, {}),
                             "date_collecte": "2026-07-20"}}),
        encoding="utf-8",
    )
    build = proc / "_build.json"
    monkeypatch.setattr(prepare, "DATA_RAW", raw)
    monkeypatch.setattr(prepare, "DATA_PROCESSED", proc)
    monkeypatch.setattr(prepare, "MANIFEST_FILE", manifest)
    monkeypatch.setattr(prepare, "BUILD_FILE", build)
    monkeypatch.setattr(prepare, "_commit_courant", lambda: {"commit": "test", "arbre_modifie": False})

    def faux_build(dest):
        Path(dest).write_text("SORTIE-OK", encoding="utf-8")

    plan = [("mini.parquet", faux_build, ["mini"])]

    # build réussi -> sortie écrite + empreinte inscrite dans la lignée
    entrees = prepare._verifier_bruts(["mini"])
    sorties = prepare.construire(plan, entrees)
    prepare._ecrire_lignee(entrees, sorties)
    assert (proc / "mini.parquet").read_text(encoding="utf-8") == "SORTIE-OK"
    lignee = json.loads(build.read_text(encoding="utf-8"))
    assert lignee["sorties"]["mini.parquet"]["sources"] == ["mini"]
    assert lignee["sorties"]["mini.parquet"]["sha256"] == empreinte(proc / "mini.parquet", {})
    prepare.verifier_sorties()  # sorties conformes : ne lève pas

    # sortie altérée -> publication refusée
    (proc / "mini.parquet").write_text("ALTEREE", encoding="utf-8")
    with pytest.raises(EmpreinteDivergente):
        prepare.verifier_sorties()

    # brut divergent -> prepare refuse AVANT toute construction
    src.write_text("a,b\n9,9\n", encoding="utf-8")
    with pytest.raises(EmpreinteDivergente):
        prepare._verifier_bruts(["mini"])


def test_sorties_reelles_conformes_a_la_lignee():
    """Garde de publication sur les VRAIES sorties : si prepare a tourné, chaque Parquet sur
    disque correspond à la lignée. Fait échouer la CI (avant commit) si une sortie a dérivé —
    sinon sauté (pipeline non exécuté), comme les tests de résultats."""
    from demonstrateur.config import BUILD_FILE
    from demonstrateur.prepare import verifier_sorties

    if not BUILD_FILE.exists():
        pytest.skip("pas de lignée de build (prepare non lancé)")
    verifier_sorties()  # lève EmpreinteDivergente si une sortie ne correspond plus


def test_figures_refuse_sortie_alteree(monkeypatch):
    """Câblage de la garde dans figures.main() : une lignée divergente arrête TOUT avant
    le moindre export — l'appel local direct à figures est gardé, pas seulement la CI.
    Auto-suffisant : la garde est simulée divergente, aucun Parquet réel n'est requis."""
    from demonstrateur import figures

    exports = []
    monkeypatch.setattr(figures, "export_html", lambda *a, **k: exports.append(a))

    def _garde_divergente():
        raise EmpreinteDivergente("sortie altérée (simulée)")

    monkeypatch.setattr(figures, "verifier_sorties", _garde_divergente)
    with pytest.raises(EmpreinteDivergente):
        figures.main()
    assert exports == [], "figures a exporté malgré une lignée divergente"


# --- Note méthodologique : le sourçage s'y vérifie, il ne s'y déclare pas -------------
NOTE = OUTPUTS / "a0_note_methodologique.html"

besoin_note = pytest.mark.skipif(
    not NOTE.exists(), reason="note absente — lancer python -m demonstrateur.note_air"
)


def _texte_note() -> str:
    """Texte de la note, balises retirées et espaces normalisés.

    Chercher une phrase dans le HTML brut rendrait ces tests dépendants du formatage :
    un retour à la ligne d'éditeur ou un <strong> au milieu d'une phrase suffirait à les
    faire tomber sans que le livrable ait changé. Ce qui doit être vérifié, c'est ce que
    le lecteur lit.
    """
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", NOTE.read_text(encoding="utf-8")))


@besoin_note
def test_la_note_porte_licences_producteurs_et_date():
    """La définition de « fini » du BRIEF_AIR exige sources, dates, limites et licences.

    Une note méthodologique est le seul endroit du livrable où l'on puisse vérifier d'un
    coup d'œil que rien n'a été emprunté sans le dire. Ce test refuse qu'une mention
    disparaisse à la faveur d'une réécriture — le cas typique étant l'allègement d'un
    paragraphe jugé trop long.
    """
    h = _texte_note()
    for mention in ("CC-BY", "Licence Ouverte", "Qualitair Corse", "Météo-France",
                    "Agence européenne pour l'environnement", "LCSQA"):
        assert mention in h, f"mention obligatoire absente de la note : {mention}"
    assert re.search(r"collectées le \d{4}-\d{2}-\d{2}", h), (
        "la note doit porter une date de collecte, et la tenir de la lignée de build"
    )
    assert "n'en ont pas validé les conclusions" in h, (
        "la note doit dire que les producteurs ne cautionnent pas l'étude — le brief "
        "l'exige pour l'Ineris, et la même réserve vaut pour l'AEE et Météo-France"
    )


@besoin_note
def test_la_note_dit_ce_que_les_chiffres_ne_disent_pas():
    """Les trois limites que le brief interdit de taire.

    Ce sont elles qui distinguent une note méthodologique d'un argumentaire : sans la
    première, l'étude laisserait croire qu'elle démontre une causalité qu'elle n'établit
    pas.
    """
    h = _texte_note()
    assert "coïncidence" in h and "pas une cause" in h, (
        "la note doit énoncer que l'association mesurée n'est pas une causalité"
    )
    assert "ne porte pas d'étiquette d'origine" in h, (
        "la note doit dire que l'origine de l'ozone n'est pas déterminable ici"
    )
    assert "Vivario" in h, (
        "la note doit nommer le poste météo retenu pour Venaco — l'approximation "
        "s'assume par écrit, elle ne se devine pas"
    )


PAGE = OUTPUTS / "air_ozone.html"

besoin_page = pytest.mark.skipif(
    not PAGE.exists(), reason="page absente — lancer python -m demonstrateur.page_air"
)


@besoin_page
def test_la_page_ne_depend_d_aucun_service_tiers():
    """Le BRIEF exige un livrable déployable en iframe SANS dépendance tierce.

    Un CDN qui s'ajoute est la régression silencieuse type : la page continue de
    s'afficher sur le poste du développeur, et casse le jour où elle est déployée derrière
    un réseau fermé — ou pire, elle expose les lecteurs à un tiers. Toutes les ressources
    doivent être locales à outputs/, qui se déploie d'un bloc.
    """
    h = PAGE.read_text(encoding="utf-8")
    externes = [s for s in re.findall(r'(?:src|href)="([^"]+)"', h)
                if s.startswith(("http://", "https://", "//"))]
    assert not externes, f"ressources tierces référencées : {externes}"
    for local in re.findall(r'(?:src|href)="([^"]+)"', h):
        assert (OUTPUTS / local).exists(), f"ressource locale manquante : {local}"
    assert h.count('src="plotly.min.js"') == 1, (
        "plotly.min.js doit être chargé UNE fois pour les cinq graphiques"
    )


@besoin_page
def test_la_page_reste_lisible_en_trois_minutes():
    """Le brief fixe un plafond de lecture, et c'est un critère de « fini ».

    Sans garde, une page grossit paragraphe après paragraphe sans que personne décide.
    Le brief tranche à l'avance : si ça déborde, on retranche un titre — on n'abrège ni
    les sources ni la note.
    """
    h = PAGE.read_text(encoding="utf-8")
    prose = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[\s\S]*?</\1>", " ", h))
    mots = len(prose.split())
    assert mots < 700, (
        f"{mots} mots de prose, soit plus de trois minutes de lecture — retrancher une "
        "section plutôt qu'abréger les mentions de source"
    )
    assert len(re.findall(r'class="plotly-graph-div"', h)) == 5, (
        "les cinq titres du brief doivent être représentés"
    )
