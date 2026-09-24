"""Construit ../index.html — la page de présentation servie sur www.methodes-revelations.fr.

Entrées, dans ce dossier :
  export_extrait.html  le HTML extrait de l'export Claude Design (« Vitrine - page de
                       présentation - standalone »), texte de référence
  logo_export.png      le logo tel qu'exporté (264×65, dernière ligne = trait parasite)

Ce que fait le script : réplique la projection d3.geoMercator().fitExtent en Python,
écrit le SVG en dur (animations CSS conservées), embarque le logo en data URI (rogné de
sa dernière ligne), remplace les polices distantes par celles du système, relève les
contrastes et tailles sous le seuil AA, et pose un <head> complet. Zéro script, zéro
ressource distante dans le résultat.

Les retouches éditoriales sont centralisées dans TEXTE_RETOUCHES.

Usage : python build_index.py   →   écrit ../index.html, à déposer tel quel dans le bucket.
"""
import base64
import math
import os
import struct
import zlib

ICI = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ICI, "export_extrait.html")
LOGO = os.path.join(ICI, "logo_export.png")
OUT = os.path.join(os.path.dirname(ICI), "index.html")

# --- projection Mercator, réplique de d3.geoMercator().fitExtent([[68,64],[W-68,H-64]], MultiPoint)
NODES = [
    ("ersa", "Cap Corse", 9.362, 43.001, 2.6),
    ("bast", "Bastia", 9.451, 42.700, 3.5),
    ("casa", "Casamozza", 9.532, 42.500, 1.7),
    ("aler", "Aléria", 9.513, 42.115, 2.3),
    ("sole", "Solenzara", 9.401, 41.858, 1.8),
    ("pove", "Porto-Vecchio", 9.279, 41.591, 2.8),
    ("boni", "Bonifacio", 9.159, 41.387, 2.6),
    ("prop", "Propriano", 8.903, 41.676, 2.2),
    ("ajac", "Ajaccio", 8.738, 41.927, 3.6),
    ("sago", "Sagone", 8.700, 42.112, 1.7),
    ("port", "Porto", 8.697, 42.259, 2.0),
    ("calv", "Calvi", 8.757, 42.567, 2.9),
    ("flor", "Saint-Florent", 9.302, 42.681, 2.0),
    ("cort", "Corte", 9.150, 42.308, 3.2),
    ("cint", "Monte Cintu", 8.943, 42.381, 2.4),
]
RING = ["ersa", "bast", "casa", "aler", "sole", "pove", "boni", "prop", "ajac", "sago", "port", "calv", "flor", "ersa"]
SPINE = [("cort", "cint"), ("cort", "bast"), ("cort", "ajac"), ("cort", "aler"), ("cint", "calv")]
EDGES = [(RING[i], RING[i + 1]) for i in range(len(RING) - 1)] + SPINE
LABELLED = {"bast": "r", "ajac": "l", "cort": "r", "cint": "l", "calv": "l", "pove": "r", "boni": "r"}
W, H = 520, 552
x0, y0, x1, y1 = 68, 64, W - 68, H - 64

raw = {}
for id_, name, lon, lat, mag in NODES:
    lam, phi = math.radians(lon), math.radians(lat)
    raw[id_] = (150 * lam, -150 * math.log(math.tan(math.pi / 4 + phi / 2)))
xs = [p[0] for p in raw.values()]
ys = [p[1] for p in raw.values()]
bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
w, h = x1 - x0, y1 - y0
k = min(w / (bx1 - bx0), h / (by1 - by0))
tx = x0 + (w - k * (bx1 + bx0)) / 2
ty = y0 + (h - k * (by1 + by0)) / 2
P = {id_: (round(k * p[0] + tx, 2), round(k * p[1] + ty, 2)) for id_, p in raw.items()}

STAR = "#F3E7CE"
CORE = "#FFFFFF"
LINE = "rgba(176,122,43,.62)"
LABEL = "rgba(243,231,206,.78)"

svg = []
svg.append(
    '<defs><radialGradient id="starGlow">'
    f'<stop offset="0%" stop-color="{CORE}" stop-opacity=".55"/>'
    f'<stop offset="100%" stop-color="{CORE}" stop-opacity="0"/>'
    "</radialGradient></defs>"
)
svg.append("<g>")
n_ring = len(RING) - 1
for i, (a, b) in enumerate(EDGES):
    (ax, ay), (bx, by) = P[a], P[b]
    spine = i >= n_ring
    attrs = (
        f'x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{LINE}" '
        f'stroke-width="{".7" if spine else "1.1"}" stroke-opacity="{".55" if spine else "1"}" '
        'stroke-linecap="round"'
    )
    if spine:
        attrs += ' stroke-dasharray="2 3"'
    svg.append(f'  <line class="draw" {attrs} style="animation-delay:{.25 + i * .1:.2f}s"/>')
svg.append("</g>")
svg.append('<g class="stars">')
for i, (id_, name, lon, lat, mag) in enumerate(NODES):
    x, y = P[id_]
    r = mag * 1.45
    svg.append(
        f'  <circle class="halo" cx="{x}" cy="{y}" r="{r * 2.8:.2f}" fill="url(#starGlow)" '
        f'style="animation-delay:{i * .43:.2f}s"/>'
    )
    svg.append(
        f'  <circle class="tw" cx="{x}" cy="{y}" r="{r:.2f}" fill="{STAR}" '
        f'style="animation-delay:{i * .37:.2f}s"/>'
    )
    svg.append(f'  <circle cx="{x}" cy="{y}" r="{r * .38:.2f}" fill="{CORE}"/>')
    if id_ in LABELLED:
        right = LABELLED[id_] == "r"
        lx = x + (r + 10 if right else -(r + 10))
        svg.append(
            f'  <text class="lbl" x="{lx:.2f}" y="{y + 3.2:.2f}" '
            f'text-anchor="{"start" if right else "end"}" fill="{LABEL}">{name}</text>'
        )
svg.append("</g>")
SVG = "\n".join(svg)


# --- logo : rogner la dernière ligne (un trait #D9D2BF parasite dans l'export), sans PIL
def png_rogner_derniere_ligne(donnees: bytes) -> bytes:
    pos, idat, w, h, ct = 8, b"", 0, 0, 0
    while pos < len(donnees):
        (ln,) = struct.unpack(">I", donnees[pos : pos + 4])
        typ, corps = donnees[pos + 4 : pos + 8], donnees[pos + 8 : pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", corps[:10])
            assert bd == 8, "profondeur inattendue"
        if typ == b"IDAT":
            idat += corps
        pos += 12 + ln
    bpp = {6: 4, 2: 3, 0: 1, 4: 2}[ct]
    stride = w * bpp + 1
    brut = zlib.decompress(idat)
    lignes, prec = [], bytearray(w * bpp)
    for y in range(h):
        f = brut[y * stride]
        ligne = bytearray(brut[y * stride + 1 : (y + 1) * stride])
        for i in range(len(ligne)):
            a = ligne[i - bpp] if i >= bpp else 0
            b = prec[i]
            c = prec[i - bpp] if i >= bpp else 0
            if f == 1:
                ligne[i] = (ligne[i] + a) & 255
            elif f == 2:
                ligne[i] = (ligne[i] + b) & 255
            elif f == 3:
                ligne[i] = (ligne[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                ligne[i] = (ligne[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        lignes.append(bytes(ligne))
        prec = ligne
    lignes = lignes[:-1]  # la ligne parasite

    def chunk(typ, corps):
        return struct.pack(">I", len(corps)) + typ + corps + struct.pack(">I", zlib.crc32(typ + corps) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, len(lignes), 8, ct, 0, 0, 0)
    data = zlib.compress(b"".join(b"\x00" + l for l in lignes), 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", data) + chunk(b"IEND", b"")


logo_png = png_rogner_derniere_ligne(open(LOGO, "rb").read())
logo = base64.b64encode(logo_png).decode()

# --- page : le texte de l'export et les retouches éditoriales validées
page = open(SRC, encoding="utf-8").read()
body = page[page.index('<div class="page">') : page.index("<script>")]
body = body.replace(
    '<img src="e3a65591-e7df-403e-9d67-7a69d12604a1"',
    f'<img src="data:image/png;base64,{logo}" width="264" height="64"',
)
old_svg = '<div class="plate"><svg viewBox="0 0 520 552" preserveAspectRatio="xMidYMid meet"></svg></div>'
assert old_svg in body
body = body.replace(
    old_svg,
    '<div class="plate"><svg viewBox="0 0 520 552" preserveAspectRatio="xMidYMid meet" role="img" '
    'aria-label="Carte de la Corse dessinée en constellation à partir de lieux réels de l’île">\n'
    f"{SVG}\n</svg></div>",
)
TEXTE_RETOUCHES = [
    # L'étude porte sur la composition du courant, pas sur la consommation.
    (
        "Deux volets : consommation électrique journalière et ozone.",
        "Deux parties : de quoi est faite l'électricité corse, et l'ozone.",
    ),
    (
        "Analyse de données et machine learning appliqués à un territoire. "
        "Premier volet publié : l'électricité et l'air.",
        "Analyse de données et machine learning appliqués à la Corse. "
        "Première étude publiée : électricité et qualité de l’air.",
    ),
    # La légende englobe les différents lieux représentés.
    (
        "Chaque étoile est un port, un cap ou un sommet réel de l'île.",
        "Une constellation dessinée à partir de lieux de Corse.",
    ),
]
for old, new in TEXTE_RETOUCHES:
    assert old in body, old
    body = body.replace(old, new)

css = page[page.index("<style>\n:root{") : page.index("</style>\n</head>") + len("</style>")]
CSS_RETOUCHES = [
    (
        "--pacioli-font-serif:'Cormorant Garamond',Georgia,serif;"
        "--pacioli-font-sans:'Inter',-apple-system,system-ui,sans-serif;"
        "--pacioli-font-mono:'JetBrains Mono','Consolas',monospace;",
        "--pacioli-font-serif:Georgia,'Times New Roman',serif;"
        "--pacioli-font-sans:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;"
        "--pacioli-font-mono:Consolas,Menlo,monospace;",
    ),
    # contraste AA (4,5:1 sur les deux fonds) : gris des libellés 2,86 → 4,69 ;
    # liens : une teinte propre 4,74, l'or du titre (gros texte, 3,29 ≥ 3) ne bouge pas
    ("--pacioli-ink-muted:#8A8FA0;", "--pacioli-ink-muted:#666B7E;--pacioli-link:#8F621D;"),
    # (« a{color:… » couvre aussi « footer .contact a{color:… », d'où la 2e ligne sur la bordure seule)
    ("a{color:var(--pacioli-monetary);", "a{color:var(--pacioli-link);"),
    ("font-weight:600;border-bottom:1px solid var(--pacioli-monetary)}", "font-weight:600;border-bottom:1px solid var(--pacioli-link)}"),
    # plancher 12 px pour les libellés en capitales, 14 px pour la prose des cartes
    (".eyebrow{font-family:var(--pacioli-font-mono);font-size:11px;", ".eyebrow{font-family:var(--pacioli-font-mono);font-size:12px;"),
    # La signature est une image : son agrandissement reste proportionnel et borné
    # à la largeur disponible sur téléphone. Le bandeau gagne en lisibilité.
    (
        "header.top img{display:block;height:64px;width:auto}",
        "header.top img{display:block;width:330px;max-width:100%;height:auto}\n"
        "header.top .eyebrow{font-size:14px;letter-spacing:.16em;white-space:normal}",
    ),
    (".lbl{font-family:var(--pacioli-font-mono);font-size:9.5px;", ".lbl{font-family:var(--pacioli-font-mono);font-size:11px;"),
    ("text-transform:uppercase;color:var(--pacioli-ink-muted)}\nfooter .contact{font-size:13px;",
     "text-transform:uppercase;color:var(--pacioli-ink-muted)}\nfooter .contact{font-size:16px;min-width:0;overflow-wrap:anywhere;"),
    (
        "flex-wrap:wrap;font-family:var(--pacioli-font-mono);font-size:10px;letter-spacing:.16em;",
        "flex-wrap:wrap;font-family:var(--pacioli-font-mono);font-size:14px;letter-spacing:.10em;",
    ),
    (".study .status{font-family:var(--pacioli-font-mono);font-size:10px;", ".study .status{font-family:var(--pacioli-font-mono);font-size:12px;"),
    (".study p{font-size:13.5px;", ".study p{font-size:14px;"),
    (".study .go{margin-top:auto;padding-top:6px;font-family:var(--pacioli-font-mono);font-size:11px;",
     ".study .go{margin-top:auto;padding-top:6px;font-family:var(--pacioli-font-mono);font-size:12px;"),
    # repli uni si color-mix() est inconnu du navigateur : les étoiles restent sur fond sombre
    ("overflow:hidden;background:radial-gradient(", "overflow:hidden;background:var(--pacioli-ink);background:radial-gradient("),
    # règle morte : aucun élément .themes dans la page
    (
        ".themes{display:flex;flex-wrap:wrap;gap:8px;padding:0;margin:0;list-style:none}\n"
        ".themes li{font-family:var(--pacioli-font-mono);font-size:10.5px;letter-spacing:.16em;"
        "text-transform:uppercase;padding:5px 11px;border-radius:50px;background:var(--pacioli-rule-soft);"
        "color:var(--pacioli-ink-soft)}\n",
        "",
    ),
    (
        "@keyframes draw{to{stroke-dashoffset:0}}",
        "@keyframes draw{to{stroke-dashoffset:0}}\n"
        "@media (prefers-reduced-motion:reduce){.tw,.halo{animation:none}.draw{animation:none;stroke-dashoffset:0}}",
    ),
    # téléphone : dans l'export, la règle « une colonne » précède « trois colonnes » (même
    # poids, la dernière gagne) → les cartes restaient sur trois colonnes de 70 px ; et les
    # bandeaux en capitales, insécables, débordaient de l'écran. Rejoué en fin de feuille.
    (
        "</style>",
        "@media (max-width:820px){.studies{grid-template-columns:minmax(0,1fr)}.eyebrow{white-space:normal}}\n</style>",
    ),
]
for old, new in CSS_RETOUCHES:
    assert old in css, old[:70]
    css = css.replace(old, new)

head = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Méthodes &amp; Révélations</title>
<meta name="description" content="Études de données sur la Corse. Analyse de données et machine learning appliqués à la Corse. Première étude publiée : électricité et qualité de l’air.">
<link rel="canonical" href="https://www.methodes-revelations.fr/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Méthodes &amp; Révélations">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="Méthodes &amp; Révélations — Études de données sur la Corse">
<meta property="og:description" content="Analyse de données et machine learning appliqués à la Corse. Première étude publiée : électricité et qualité de l’air.">
<meta property="og:url" content="https://www.methodes-revelations.fr/">
"""
html = head + css + "\n</head>\n<body>\n" + body.rstrip() + "\n</body>\n</html>\n"
assert "<script" not in html and "fonts.g" not in html
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)
print("écrit", OUT, len(html.encode()), "octets")
