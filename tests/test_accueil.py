"""Verrous de la page d'entrée `outputs/index.html`.

À la différence de `outputs/etude.html`, la page d'accueil ne peut pas être verrouillée
par une comparaison octet à octet : elle porte la date de compilation, le commit et le
compteur d'actualisations, qui changent à chaque run planifié. Ce sont donc ses PROMESSES
qu'on tient ici — celles qui la rendraient menteuse si elles cessaient d'être vraies.
"""

import datetime as dt
import json
import re

import pytest

from demonstrateur.accueil import _manifeste
from demonstrateur.config import BUILD_FILE, MANIFEST_FILE, OUTPUTS

INDEX = OUTPUTS / "index.html"

besoin_page = pytest.mark.skipif(
    not INDEX.exists(), reason="page non générée — lancer `python -m demonstrateur.accueil`"
)


@besoin_page
def test_accueil_ne_mene_qu_a_des_pages_presentes():
    """Une porte d'entrée qui mène à un 404 est pire que pas de porte. Le dossier
    `outputs/` étant déployé d'un bloc, tout lien interne doit y trouver sa cible."""
    page = INDEX.read_text(encoding="utf-8")
    cibles = set(re.findall(r'href="(?!https?:)([^"#]+\.html)"', page))
    assert cibles, "aucun lien interne — la page d'entrée ne mène nulle part"
    for cible in sorted(cibles):
        assert (OUTPUTS / cible).exists(), (
            f"la page d'entrée mène à {cible}, absent d'outputs/ — le dossier se déploie "
            "d'un bloc, le lien serait mort en ligne"
        )


@besoin_page
def test_accueil_ne_depend_d_aucun_service_tiers():
    """Argument affiché sur la page elle-même : « aucun appel réseau au chargement ».
    Une police distante ou une bibliothèque appelée ailleurs le démentirait — et c'est
    exactement ce qui a été reproché à la vitrine précédente."""
    page = INDEX.read_text(encoding="utf-8")
    externes = re.findall(r'(?:href|src)="(https?://[^"]+)"', page)
    assert not externes, (
        f"la page charge des ressources tierces : {externes} — elle affirme pourtant "
        "ne dépendre d'aucun service tiers"
    )


@besoin_page
def test_accueil_annonce_le_vrai_compte_des_sources():
    """Le nombre de sources et de producteurs est écrit en toutes lettres dans la page.
    S'il se désynchronise du manifeste, la preuve affichée devient fausse — et c'est
    précisément la preuve que la page prétend rendre vérifiable."""
    page = INDEX.read_text(encoding="utf-8")
    _, n_sources, n_prod = _manifeste()
    attendu = f"Les {n_sources} sources, leurs {n_prod} producteurs"
    assert attendu in page, (
        f"la page n'annonce pas « {attendu} » — le manifeste compte {n_sources} sources "
        f"et {n_prod} producteurs ; relancer `python -m demonstrateur.accueil`"
    )


@besoin_page
def test_toutes_les_empreintes_du_manifeste_sont_affichees():
    """La page affiche les empreintes tronquées à 12 caractères. Chacune doit être là :
    un manifeste partiellement publié laisserait croire à une traçabilité complète."""
    page = INDEX.read_text(encoding="utf-8")
    sources = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    manquantes = [i for i, s in sources.items() if s["sha256"][:12] not in page]
    assert not manquantes, f"empreintes absentes de la page : {manquantes}"


@besoin_page
def test_cachet_de_fraicheur_porte_une_date_exploitable():
    """L'âge est recalculé à la lecture par le navigateur, à partir de `data-genere`.
    Si cette date n'est pas analysable, le script se tait et la page perd son cachet
    sans rien dire — panne silencieuse, exactement ce qu'on veut éviter."""
    page = INDEX.read_text(encoding="utf-8")
    m = re.search(r'data-genere="([^"]+)"', page)
    assert m, "le cachet de fraîcheur ne porte pas de date de compilation"
    horodatage = dt.datetime.fromisoformat(m.group(1))  # lève si non analysable
    assert horodatage.tzinfo is not None, (
        "date de compilation sans fuseau : l'âge calculé chez le lecteur dériverait "
        "de plusieurs heures selon sa position"
    )
    if BUILD_FILE.exists():
        attendu = json.loads(BUILD_FILE.read_text(encoding="utf-8"))["genere_le"]
        assert m.group(1) == attendu, (
            "la date affichée n'est plus celle de la lignée de build — la page annoncerait "
            "une fraîcheur qu'elle n'a pas ; relancer `python -m demonstrateur.accueil`"
        )
