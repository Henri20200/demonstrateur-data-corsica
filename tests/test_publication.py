"""D1–D3 : dépendances, identité du JavaScript et révision réellement publiée."""

import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
import pytest
import yaml

from demonstrateur import page_air, viz
from demonstrateur.config import ROOT


def _workflow(nom):
    return yaml.safe_load((ROOT / ".github" / "workflows" / nom).read_text(encoding="utf-8"))


def test_le_cron_et_la_validation_installent_le_meme_verrou():
    cron = _workflow("pipeline.yml")["jobs"]["rafraichir"]["steps"]
    validation = _workflow("validation.yml")["jobs"]["valider"]["steps"]
    for etapes in (cron, validation):
        installations = [e["run"] for e in etapes if "uv sync" in e.get("run", "")]
        assert len(installations) == 1
        assert "uv sync --locked --extra dev --python" in installations[0]
    assert any("GITHUB_PATH" in e.get("run", "") and ".venv/bin" in e["run"] for e in cron)
    verrous = _workflow("validation.yml")["jobs"]["verrous"]
    assert set(verrous["strategy"]["matrix"]["dependances"]) == {"verrouillees", "dernieres"}
    assert any(
        "uv pip install" in e.get("run", "") and "dernieres" in e.get("if", "")
        for e in verrous["steps"]
    )


def test_un_ancien_bundle_ne_survit_pas_dans_les_nouvelles_pages(tmp_path, monkeypatch):
    """D2 : jouer le vrai export avec le fichier stable déjà présent, comme en CI."""
    ancien = tmp_path / "plotly.min.js"
    ancien.write_text("// ancienne version", encoding="utf-8")
    monkeypatch.setattr(viz, "OUTPUTS", tmp_path)
    monkeypatch.setattr(page_air, "OUTPUTS", tmp_path)
    monkeypatch.setattr(page_air.fa, "phrase_actualite_courte", lambda: "")
    fig = go.Figure()
    fig.update_layout(title_text="Mesure", height=600, margin=dict(t=100, b=150))
    page = Path(viz.export_html(fig, "essai", "Source de test", "2026-09-21"))
    refs = re.findall(r'src="(plotly[^\"]*\.js)"', page.read_text(encoding="utf-8"))
    assert len(refs) == 1 and refs[0] != ancien.name
    contenu = (tmp_path / refs[0]).read_bytes()
    assert contenu == get_plotlyjs().encode("utf-8")
    assert hashlib.sha256(contenu).hexdigest() in refs[0]
    monkeypatch.setattr(page_air, "verifier_sorties", lambda: None)
    monkeypatch.setattr(page_air, "_blocs", lambda: [])
    monkeypatch.setattr(page_air, "date_collecte", lambda _source: "2026-09-21")
    assert page_air.main() == 0
    html_air = (tmp_path / "air_ozone.html").read_text(encoding="utf-8")
    assert html_air.count(f'src="{refs[0]}"') == 1


def test_une_mise_a_jour_du_bundle_change_son_url(tmp_path, monkeypatch):
    # Deux contenus successifs, indépendamment de la version annoncée du paquet.
    monkeypatch.setattr(viz, "get_plotlyjs", lambda: "// version 1", raising=False)
    ancien = viz.ecrire_bundle_plotly(tmp_path)
    monkeypatch.setattr(viz, "get_plotlyjs", lambda: "// version 2")
    nouveau = viz.ecrire_bundle_plotly(tmp_path)
    assert ancien != nouveau
    assert (tmp_path / ancien).read_text(encoding="utf-8") == "// version 1"
    assert (tmp_path / nouveau).read_text(encoding="utf-8") == "// version 2"
    (tmp_path / nouveau).write_text("altéré", encoding="utf-8")
    assert viz.ecrire_bundle_plotly(tmp_path) == nouveau
    assert (tmp_path / nouveau).read_text(encoding="utf-8") == "// version 2"


def _bash():
    if os.name == "nt":
        chemin = Path("C:/Program Files/Git/bin/bash.exe")
        return str(chemin) if chemin.is_file() else None
    return shutil.which("bash")


def _git(dossier, *args):
    resultat = subprocess.run(
        ["git", "-C", str(dossier), *args], capture_output=True, text=True, check=True
    )
    return resultat.stdout.strip()


@pytest.mark.skipif(_bash() is None, reason="bash absent")
@pytest.mark.parametrize("avance", ["non", "avant_controle", "avant_push"])
@pytest.mark.parametrize("changement", [False, True])
def test_la_publication_refuse_une_revision_distante_nouvelle(tmp_path, avance, changement):
    """D3 : un vrai remote avance avant le contrôle, ou entre contrôle et push.

    Seule l'adresse réseau est redirigée ; le run du workflow exécute les vrais git.
    L'ancien rebase poussait des sorties calculées avant cette nouvelle révision.
    """
    distant = tmp_path / "distant.git"
    _git(tmp_path, "init", "--bare", str(distant))
    travail = tmp_path / "travail"
    travail.mkdir()
    _git(travail, "init", "-b", "master")
    _git(travail, "config", "user.name", "Test")
    _git(travail, "config", "user.email", "test@example.test")
    (travail / "outputs").mkdir()
    (travail / "outputs" / "index.html").write_text("ancien", encoding="utf-8")
    (travail / "data" / "raw").mkdir(parents=True)
    (travail / "data" / "raw" / "_manifest.json").write_text("{}", encoding="utf-8")
    (travail / "code.txt").write_text("code testé", encoding="utf-8")
    _git(travail, "add", ".")
    _git(travail, "commit", "-m", "initial")
    initial = _git(travail, "rev-parse", "HEAD")
    _git(travail, "push", str(distant), "HEAD:master")
    # Préparer une révision concurrente sur une autre branche, sans modifier le checkout.
    _git(travail, "switch", "-c", "concurrente")
    (travail / "code.txt").write_text("code nouveau non testé", encoding="utf-8")
    _git(travail, "add", "code.txt")
    _git(travail, "commit", "-m", "révision concurrente")
    avance_sha = _git(travail, "rev-parse", "HEAD")
    _git(travail, "push", str(distant), "HEAD:concurrente")
    _git(travail, "switch", "master")
    if avance == "avant_controle":
        _git(distant, "update-ref", "refs/heads/master", avance_sha)
    if changement:
        (travail / "outputs" / "index.html").write_text("nouveau", encoding="utf-8")

    etapes = _workflow("pipeline.yml")["jobs"]["rafraichir"]["steps"]
    script = next(e["run"] for e in etapes if e.get("name", "").startswith("Committer"))
    # Intercepter aussi pull/fetch pour que l'ancien script puisse être éprouvé hors réseau.
    prelude = """git() {
  case "$1" in
    ls-remote|push|pull|fetch)
      local action="$1"
      shift
      if [ "$action" = push ] && [ "$AVANCE" = avant_push ]; then
        command git -C "$DISTANT_TEST" update-ref refs/heads/master "$AVANCE_SHA"
      fi
      local args=()
      for arg in "$@"; do
        case "$arg" in
          https://*) args+=("$DISTANT_TEST") ;;
          *) args+=("$arg") ;;
        esac
      done
      command git "$action" "${args[@]}"
      ;;
    *) command git "$@" ;;
  esac
}
"""
    env = {
        **os.environ,
        "GITHUB_SHA": initial,
        "GITHUB_REPOSITORY": "exemple/test",
        "JETON": "factice",
        "DISTANT_TEST": distant.as_posix(),
        "AVANCE": avance,
        "AVANCE_SHA": avance_sha,
    }
    resultat = subprocess.run(
        [_bash(), "-e", "-c", prelude + script],
        cwd=travail,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    refus = avance == "avant_controle" or (avance == "avant_push" and changement)
    assert (resultat.returncode != 0) is refus, resultat.stdout + resultat.stderr
    publie = _git(distant, "rev-parse", "refs/heads/master")
    if refus:
        assert publie == avance_sha
    else:
        assert publie == _git(travail, "rev-parse", "HEAD")
        if changement:
            assert _git(distant, "rev-parse", "master^") == initial
