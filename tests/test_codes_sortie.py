"""Le contrat de sortie des figures, et sa lecture par les deux workflows.

`python -m demonstrateur.figures` rend trois verdicts et non deux, depuis le 20/09/2026 :

    0                 génération normale — on publie ;
    CODE_FRAICHEUR    génération COMPLÈTE, T1 en « affichage suspendu » — on publie
                      quand même, et le run rougit en fin de parcours ;
    tout le reste     erreur technique — la chaîne s'arrête avant toute publication.

Ce fichier tient les trois parcours des deux côtés : ce que rend `main()`, et ce que le
`run:` des workflows en fait. Les deux moitiés sont nécessaires, et c'est la seconde qui
manquait. Le code, lui, disait déjà la bonne chose — il rendait 1 pour un relevé périmé ;
c'est d'en faire le MÊME 1 qu'une exception qui a mis les workflows devant un choix
impossible, et ils s'y sont partagés en deux défauts opposés :

  - le cron publiait T1 « affichage suspendu » (`continue-on-error: true`) puis lançait
    `pytest`, dont le verrou de fraîcheur échouait sur exactement cet âge, AVANT le
    commit et le déploiement. Le mode dégradé, décidé et documenté à trois endroits, ne
    pouvait donc pas atteindre la vitrine — et comme rien n'était publié, le gel du mix
    électrique emportait aussi les pages de l'air, qui n'y sont pour rien ;
  - le job `verrous` de la CI de PR, lui, avalait tout par un `|| true`. `outputs/` étant
    versionné, une exception de génération laissait les verrous relire les HTML du
    dernier commit du cron : le job pouvait passer au vert sur une PR qui casse une
    figure, c'est-à-dire attester l'inverse de ce pour quoi il existe.

Mesuré avant correction, sur les 92 publications du cron depuis le 27/08/2026 : aucune
au-delà de 24 h, une seule à 15,5 h (04/09, flux EDF figé depuis la veille) — soit un
cycle de rafraîchissement sous le seuil. Ce relevé borne, il ne conclut pas : il ne voit
que ce qui a été PUBLIÉ, et un run bloqué ne laisse pas de commit. Il rend seulement le
déclenchement peu probable, puisqu'il aurait fallu qu'une publication passe d'abord dans
la bande 18-24 h, qu'on n'y trouve pas. Seuls les journaux Actions le trancheraient.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import plotly.graph_objects as go
import pytest
import yaml

from demonstrateur import figures
from demonstrateur.config import OUTPUTS, ROOT

WORKFLOWS = ROOT / ".github" / "workflows"

# Constructeurs de figures qui rendent des valeurs EN PLUS de la figure : {nom: combien}.
# `fig_t1_soleil` n'y est pas, c'est lui qui porte l'âge du relevé et chaque test le pose.
# Ceux qui n'y figurent pas ne rendent que la figure ; un nouveau constructeur à valeurs
# multiples fera échouer le dépaquetage, ce qui est le signal voulu — pas un silence.
_VALEURS_EN_PLUS = {
    "fig_t10_pointes_estivales": 3,
    "fig_t4_heure_verte": 4,
    "fig_t7_dependance_perimetres": 1,
    "fig_t8_seuil_deconnexion": 2,
}


def _neutraliser(monkeypatch, age_h: float) -> list[str]:
    """Rend `figures.main()` exécutable sans données ET sans rien écrire dans outputs/.

    Les vrais constructeurs lisent les Parquet ; `export_html` écrit les fichiers que le
    cron committe ensuite — un test qui publierait un T1 d'âge inventé serait pire que le
    défaut qu'il surveille. Les deux sont donc remplacés, et le seul comportement laissé
    intact est celui qu'on éprouve : la décision de `main()` sur l'âge du relevé.

    Retourne la liste, remplie au fil de l'appel, des noms de visuels exportés.
    """
    absents = [nom for nom in _VALEURS_EN_PLUS if not hasattr(figures, nom)]
    assert not absents, f"constructeur(s) disparu(s) : {absents} — table à remettre à jour"

    exportes: list[str] = []
    monkeypatch.setattr(figures, "verifier_sorties", lambda: None)
    monkeypatch.setattr(figures, "export_html",
                        lambda fig, nom, *a, **k: exportes.append(nom))
    monkeypatch.setattr(figures, "fig_t1_soleil", lambda: (
        go.Figure(), "18 septembre à 14 h", "Estimé", age_h, "2026-09-18T12:00:00Z"))
    for nom in dir(figures):
        if nom.startswith("fig_") and nom != "fig_t1_soleil":
            extra = tuple([0.0] * _VALEURS_EN_PLUS.get(nom, 0))
            monkeypatch.setattr(
                figures, nom, lambda *a, _e=extra, **k: (go.Figure(), *_e) if _e else go.Figure()
            )
    return exportes


# --- Parcours 1 et 2 : ce que rend main() --------------------------------------------


def test_un_releve_frais_rend_zero(monkeypatch):
    """Parcours normal : rien à signaler, tout est publié."""
    exportes = _neutraliser(monkeypatch, age_h=0.5)
    assert figures.main() == 0
    assert "t1_soleil_live" in exportes


def test_un_releve_perime_rend_le_code_reserve_et_publie_quand_meme(monkeypatch):
    """Parcours dégradé : le code change, la génération non.

    Les deux moitiés comptent. Le code 2 est ce qui permet au workflow de distinguer ce
    cas d'une panne ; la génération complète est ce qui met en ligne l'avertissement que
    le lecteur doit voir. Un correctif qui rendrait 2 en s'arrêtant à T1 respecterait la
    lettre du contrat et perdrait tout ce pour quoi il a été écrit.
    """
    exportes = _neutraliser(monkeypatch, age_h=figures.FRAICHEUR_BLOQUER_H + 1)
    assert figures.main() == figures.CODE_FRAICHEUR
    assert "t1_soleil_live" in exportes
    assert len(exportes) > 5, (
        f"seulement {len(exportes)} visuels produits — le relevé périmé ne doit RIEN "
        "empêcher de se dessiner, il ne change que le code de sortie"
    )


def test_le_seuil_d_avertissement_ne_change_pas_le_code(monkeypatch):
    """Entre 12 h et 24 h : la page avertit, le run reste vert. C'est le cas du 04/09."""
    _neutraliser(monkeypatch, age_h=figures.FRAICHEUR_AVERTIR_H + 1)
    assert figures.main() == 0


# --- Parcours 3 : une exception de génération ne se confond avec rien -----------------


def test_le_code_de_fraicheur_n_est_pas_celui_d_une_exception():
    """1 est ce que Python rend sur une exception : le code réservé ne peut pas le valoir.

    Verrou d'une ligne pour l'invariant dont tout le reste dépend — si les deux sens
    reprenaient le même code, les `if` des deux workflows redeviendraient faux sans que
    rien d'autre ne bouge.
    """
    assert figures.CODE_FRAICHEUR not in (0, 1)


def test_une_figure_qui_casse_remonte_sans_code_de_sortie(monkeypatch):
    """Une exception traverse `main()` : elle ne devient jamais un code publiable.

    Et la vérification se fait avec les HTML du run précédent EN PLACE dans `outputs/` —
    c'est la situation réelle, ils y sont versionnés. Leur présence est précisément ce qui
    rendait le défaut invisible : la chaîne continuait, les verrous relisaient ces
    fichiers-là et la publication repartait avec eux.
    """
    assert (OUTPUTS / "t1_soleil_live.html").exists(), (
        "outputs/ vide : ce test perd son objet, qui est la présence d'anciens HTML"
    )
    _neutraliser(monkeypatch, age_h=0.5)

    def _casse():
        raise RuntimeError("figure cassée (simulée)")

    monkeypatch.setattr(figures, "fig_t3_profil", _casse)
    with pytest.raises(RuntimeError):
        figures.main()


# --- Les trois parcours vus par le `run:` des workflows -------------------------------

def _bash():
    # Le lanceur WSL de Windows n'exécute pas ces chemins Windows.
    # Même choix que test_publication : Git Bash sur Windows, bash du PATH ailleurs.
    if os.name == "nt":
        chemin = Path("C:/Program Files/Git/bin/bash.exe")
        return str(chemin) if chemin.is_file() else None
    return shutil.which("bash")


_BASH = _bash()
besoin_bash = pytest.mark.skipif(_BASH is None, reason="bash absent — snippet non jouable")


def _etape_des_figures(workflow: str) -> str:
    """Le script shell que le workflow exécute réellement pour produire les figures.

    `demonstrateur.figures` et rien d'autre : sans la borne de fin, le motif attrape aussi
    `demonstrateur.figures_air`, qui est un autre producteur et un autre contrat.
    """
    contenu = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    etapes = [e for job in contenu["jobs"].values() for e in job["steps"]
              if re.search(r"demonstrateur\.figures(?![\w.])", e.get("run") or "")]
    assert len(etapes) == 1, f"{workflow} : {len(etapes)} étapes lancent les figures, 1 attendue"
    assert not etapes[0].get("continue-on-error"), (
        f"{workflow} : l'étape des figures tolère TOUS les codes — c'est le défaut même "
        "qui laissait une exception de génération traverser la chaîne"
    )
    return etapes[0]["run"]


def _jouer(script: str, code_figures: int, tmp_path) -> tuple[int, str, list[str]]:
    """Exécute le script du workflow avec un faux `python` qui rend le code demandé.

    `bash -e`, comme GitHub : sans le `-e`, un `exit` manquant passerait inaperçu ici et
    pas en ligne. Le faux `python` n'échoue que sur l'appel aux FIGURES — les modules
    suivants réussissent, sans quoi on mesurerait l'arrêt du mauvais maillon, et
    `figures_air` en est un (d'où le motif borné à la fin de la ligne). Il note chaque
    appel : ce journal dit si la chaîne a continué, et jusqu'où.
    """
    faux = tmp_path / "bin"
    faux.mkdir()
    journal = tmp_path / "appels.txt"
    (faux / "python").write_text(
        "#!/bin/sh\n"
        f'echo "$*" >> "{journal.as_posix()}"\n'
        'case "$*" in\n'
        f"  *demonstrateur.figures) exit {code_figures} ;;\n"
        "esac\n"
        "exit 0\n",
        encoding="utf-8", newline="\n",
    )
    os.chmod(faux / "python", 0o755)
    fichier = tmp_path / "etape.sh"
    fichier.write_text(script, encoding="utf-8", newline="\n")

    env = {**os.environ, "PATH": f"{faux.as_posix()}{os.pathsep}{os.environ['PATH']}"}
    res = subprocess.run([_BASH, "-e", fichier.as_posix()], env=env,
                         capture_output=True, text=True)
    appels = journal.read_text(encoding="utf-8").splitlines() if journal.exists() else []
    return res.returncode, res.stdout + res.stderr, appels


@besoin_bash
@pytest.mark.parametrize("workflow", ["pipeline.yml", "validation.yml"])
@pytest.mark.parametrize("code", [0, figures.CODE_FRAICHEUR])
def test_les_workflows_publient_sur_zero_et_sur_le_code_de_fraicheur(workflow, code, tmp_path):
    """0 et le code réservé laissent la chaîne aller jusqu'au bout — la moitié « on publie ».

    Paramétré depuis `figures.CODE_FRAICHEUR` et non sur un 2 écrit ici : les workflows,
    eux, portent le chiffre en dur dans leur shell. C'est ce qui fait de ce test le point
    où les deux se rencontrent — déplacer la constante côté Python sans toucher aux
    workflows fait échouer ce cas, au lieu de laisser deux définitions diverger.
    """
    script = _etape_des_figures(workflow)
    rc, sortie, appels = _jouer(script, code, tmp_path)
    assert rc == 0, f"{workflow} : code {code} a arrêté l'étape\n{sortie}"
    assert len(appels) == script.count("python -m demonstrateur."), (
        f"{workflow} : {len(appels)} module(s) lancé(s) sur "
        f"{script.count('python -m demonstrateur.')} — la chaîne s'est interrompue"
    )


@besoin_bash
@pytest.mark.parametrize("workflow", ["pipeline.yml", "validation.yml"])
def test_les_workflows_s_arretent_sur_une_erreur_technique(workflow, tmp_path):
    """Tout autre code arrête l'étape, et rien de ce qui suit ne tourne.

    L'assertion sur le journal est le cœur : ce qui a permis à une exception de passer
    n'est pas que le run restait vert, c'est que les MODULES SUIVANTS continuaient de
    tourner sur les anciens HTML.
    """
    script = _etape_des_figures(workflow)
    rc, sortie, appels = _jouer(script, 1, tmp_path)
    assert rc != 0, f"{workflow} : une erreur technique n'arrête pas l'étape\n{sortie}"
    assert appels == ["-m demonstrateur.figures"], (
        f"{workflow} : la chaîne a continué après l'échec — {appels}"
    )


# --- Le verrou de fraîcheur est séparé, non bloquant, et rejoint le signal final ------


def test_le_cron_separe_les_verrous_de_code_et_le_verrou_d_exploitation():
    """Le contrat côté cron, en trois pièces qui ne tiennent qu'ensemble.

    Les verrous de résultats restent bloquants et excluent `fraicheur` ; la fraîcheur se
    joue à part, sans retenir la publication ; son échec rejoint le signalement final,
    qui rougit le run une fois la vitrine à jour. Retirer une seule des trois ramène le
    défaut : le blocage d'avant si le marqueur revient dans le verrou bloquant, un cron
    vert sur un relevé périmé si le signalement final cesse de le lire.
    """
    contenu = yaml.safe_load((WORKFLOWS / "pipeline.yml").read_text(encoding="utf-8"))
    etapes = contenu["jobs"]["rafraichir"]["steps"]
    par_run = {e.get("run", ""): e for e in etapes}

    bloquants = [e for run, e in par_run.items()
                 if run.strip().startswith("pytest") and "not fraicheur" in run]
    assert len(bloquants) == 1, "le verrou de résultats doit exclure le marqueur fraicheur"
    assert not bloquants[0].get("continue-on-error"), "les verrous de résultats sont bloquants"

    fraicheur = [e for run, e in par_run.items()
                 if run.strip() == "pytest -m fraicheur" or run.strip().endswith("-m fraicheur")]
    assert len(fraicheur) == 1, "le verrou de fraîcheur doit se jouer dans une étape à lui"
    assert fraicheur[0].get("continue-on-error") is True, (
        "le verrou de fraîcheur ne doit pas retenir la publication — c'est ce blocage qui "
        "rendait l'« affichage suspendu » inatteignable"
    )
    identifiant = fraicheur[0].get("id")
    assert identifiant, "l'étape de fraîcheur a besoin d'un id pour être lue en fin de run"

    final = [e for e in etapes if f"steps.{identifiant}.outcome" in (e.get("if") or "")]
    assert final, (
        f"aucune étape finale ne lit `steps.{identifiant}.outcome` — un relevé périmé "
        "serait publié derrière un cron vert"
    )
    assert "exit 1" in final[-1].get("run", ""), "le signalement final doit rougir le run"


def test_le_signalement_arrive_apres_la_publication():
    """L'ordre EST le contrat, et sa présence ne le prouve pas.

    Le signalement rougit le run par `exit 1`, ce qui fait échouer le job et SAUTER tout
    ce qui vient après. Remonté avant le commit, il n'annoncerait plus un régime dégradé
    publié : il l'empêcherait — la vitrine ne bougerait pas, l'air non plus, et on aurait
    reconstruit T3 à l'identique sous un autre habillage. Le test d'à côté vérifiait que
    le signal existe et qu'il rougit ; celui-ci vérifie qu'il arrive en dernier, ce qu'un
    déplacement d'étape défaisait sans faire tomber une seule assertion.

    Les étapes se retrouvent par ce qu'elles FONT (pousser, synchroniser, lire l'issue du
    verrou), jamais par leur libellé : un titre se réécrit sans rien changer à la chaîne.
    """
    contenu = yaml.safe_load((WORKFLOWS / "pipeline.yml").read_text(encoding="utf-8"))
    etapes = contenu["jobs"]["rafraichir"]["steps"]

    def _rang(intitule: str, predicat) -> int:
        trouves = [i for i, e in enumerate(etapes) if predicat(e)]
        assert len(trouves) == 1, f"{intitule} : {len(trouves)} étape(s) trouvée(s), 1 attendue"
        return trouves[0]

    fraicheur = _rang("verrou de fraîcheur", lambda e: e.get("id") == "fraicheur")
    commit = _rang("commit des visuels", lambda e: "git push" in (e.get("run") or ""))
    vitrine = _rang("déploiement", lambda e: "aws s3 sync" in (e.get("run") or ""))
    signal = _rang("signalement final",
                   lambda e: "steps.fraicheur.outcome" in (e.get("if") or ""))

    assert fraicheur < commit < vitrine < signal, (
        "ordre des étapes du cron cassé — mesuré : fraîcheur=" f"{fraicheur}, commit={commit}, "
        f"vitrine={vitrine}, signalement={signal}. Le contrat est « on publie, PUIS on "
        "signale » : tout signalement placé avant le commit ou le déploiement les annule."
    )
    assert signal == len(etapes) - 1, (
        f"le signalement est en position {signal} sur {len(etapes)} étapes — il doit être "
        "la dernière, sinon son `exit 1` emporte ce qui le suit"
    )
