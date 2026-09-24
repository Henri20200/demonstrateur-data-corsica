"""Q7 : le report ENTSO-E exige une première mesure dans chaque période."""

import pytest

from demonstrateur.prepare import _lignes_entsoe_horaires


def _document(tmp_path, points, resolution="PT60M", periodes=1):
    periode = (
        "<Period><timeInterval><start>2026-01-01T00:00Z</start>"
        "<end>2026-01-01T02:00Z</end></timeInterval>"
        f"<resolution>{resolution}</resolution>"
        + "".join(
            f"<Point><position>{p}</position><quantity>{q}</quantity></Point>" for p, q in points
        )
        + "</Period>"
    )
    fichier = tmp_path / "entsoe.xml"
    fichier.write_text(
        '<GL_MarketDocument xmlns="urn:test"><TimeSeries>'
        "<inBiddingZone_Domain.mRID>zone</inBiddingZone_Domain.mRID>"
        "<MktPSRType><psrType>B16</psrType></MktPSRType><curveType>A03</curveType>"
        + (
            periode.replace("<position>2</position>", "<position>1</position>")
            if periodes == 2
            else ""
        )
        + periode
        + "</TimeSeries></GL_MarketDocument>",
        encoding="utf-8",
    )
    return fichier


@pytest.mark.parametrize("points,periodes", [([], 1), ([(2, 80)], 1), ([(2, 80)], 2)])
@pytest.mark.parametrize("resolution", ["PT60M", "PT15M"])
def test_une_periode_sans_mesure_initiale_est_refusee(tmp_path, points, periodes, resolution):
    fichier = _document(tmp_path, points, resolution, periodes)
    with pytest.raises(ValueError, match="position 1"):
        _lignes_entsoe_horaires(fichier)


@pytest.mark.parametrize("valeur", [0, 80])
def test_un_report_part_d_une_mesure_y_compris_zero(tmp_path, valeur):
    fichier = _document(tmp_path, [(1, valeur)], "PT15M")
    lignes = _lignes_entsoe_horaires(fichier)
    assert len(lignes) == 2
    assert [ligne["mw"] for ligne in lignes] == [valeur, valeur]
