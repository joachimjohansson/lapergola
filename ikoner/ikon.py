"""Favicon för Pergola: guld-P framför en olivkvist. En geometri, ut som SVG och PNG/ICO.
Kör: python -I ikon.py <ut-mapp>"""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw

UT = Path(sys.argv[1])
S = 512
BG, GULD = "#151b16", "#c9a462"
BLAD = ["#6f7d5f", "#8a9677", "#5c6a4f"]
OLIV = "#3d3346"

def bezier(p0, p1, p2, t):
    return tuple((1-t)**2*a + 2*(1-t)*t*b + t*t*c for a, b, c in zip(p0, p1, p2))

def blad(bas, vinkel, langd, bredd, n=24):
    """Bladform (lins) från bas i given vinkel, som polygonpunkter."""
    dx, dy = math.cos(vinkel), math.sin(vinkel)
    nx, ny = -dy, dx
    sida1, sida2 = [], []
    for i in range(n + 1):
        t = i / n
        cx, cy = bas[0] + dx*langd*t, bas[1] + dy*langd*t
        w = bredd/2 * math.sin(math.pi * t) ** 0.85
        sida1.append((cx + nx*w, cy + ny*w))
        sida2.append((cx - nx*w, cy - ny*w))
    return sida1 + sida2[::-1]

# Kvisten: en böjd stjälk från nere till vänster upp till höger, blad växelvis
P0, P1, P2 = (46, 474), (220, 330), (452, 74)
stjalk = [bezier(P0, P1, P2, i/40) for i in range(41)]
blads = []
for k, t in enumerate([0.10, 0.22, 0.34, 0.46, 0.58, 0.70, 0.82, 0.93]):
    x, y = bezier(P0, P1, P2, t)
    x2, y2 = bezier(P0, P1, P2, min(t + .01, 1))
    rikt = math.atan2(y2 - y, x2 - x)
    sida = 1 if k % 2 else -1
    blads.append((blad((x, y), rikt + sida*0.8, 138 - k*6, 50), BLAD[k % 3]))
blads.append((blad(P2, math.atan2(P2[1]-P1[1], P2[0]-P1[0]), 56, 34), BLAD[1]))
oliver = [((372, 300), 17), ((108, 380), 15)]

# P:et från vektorloggan (original/logo-vektor/pergola-ordbild.svg): de två konturerna längst till vänster
import re
ORD = Path(__file__).resolve().parent.parent / "original" / "logo-vektor" / "pergola-ordbild.svg"
_d = re.search(r'<path d="([^"]+)" fill="#84744e" fill-rule="evenodd"', ORD.read_text(encoding="utf-8")).group(1)
_del = re.findall(r"M[^M]*", _d)
def _bbox(sp):
    n = list(map(float, re.findall(r"-?[\d.]+", sp))); return min(n[0::2]), max(n[0::2]), min(n[1::2]), max(n[1::2])
P_DEL = [sp for sp in _del if _bbox(sp)[0] < 100 and _bbox(sp)[1] < 97]   # P:ets ytterkontur och hål
assert len(P_DEL) == 2, f"hittade {len(P_DEL)} konturer för P"
_x0 = min(_bbox(sp)[0] for sp in P_DEL); _x1 = max(_bbox(sp)[1] for sp in P_DEL)
_y0 = min(_bbox(sp)[2] for sp in P_DEL); _y1 = max(_bbox(sp)[3] for sp in P_DEL)
P_SKALA = 340 / (_x1 - _x0)
P_TX = 256 - (_x0 + _x1) / 2 * P_SKALA
P_TY = 256 - (_y0 + _y1) / 2 * P_SKALA
P_D = "".join(P_DEL)

def p_polygoner():
    """P:ets konturer som punktlistor i ikonens koordinater (kurvor uppdelade i 16 steg)."""
    polys = []
    for sp in P_DEL:
        tok = re.findall(r"[MLCZ]|-?[\d.]+", sp); i = 0; pts = []
        def num():
            nonlocal i; v = float(tok[i]); i += 1; return v
        cmd = None
        while i < len(tok):
            if tok[i] in "MLCZ": cmd = tok[i]; i += 1
            if cmd == "Z": break
            if cmd in "ML": pts.append((num(), num()))
            elif cmd == "C":
                c1 = (num(), num()); c2 = (num(), num()); e = (num(), num()); p0 = pts[-1]
                for k in range(1, 17):
                    u = k / 16; w = 1 - u
                    pts.append(tuple(w**3*p0[j] + 3*w*w*u*c1[j] + 3*w*u*u*c2[j] + u**3*e[j] for j in (0, 1)))
        polys.append([(x * P_SKALA + P_TX, y * P_SKALA + P_TY) for x, y in pts])
    return polys

ytter, hal = sorted(p_polygoner(), key=len, reverse=True)   # ytterkonturen har flest punkter

def svg():
    f = lambda pts: "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
    delar = [f'<rect width="{S}" height="{S}" fill="{BG}"/>',
             f'<path d="M{" L".join(f"{x:.1f} {y:.1f}" for x, y in stjalk)}" fill="none" stroke="{BLAD[2]}" stroke-width="9" stroke-linecap="round"/>']
    delar += [f'<path d="{f(p)}" fill="{c}"/>' for p, c in blads]
    delar += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="{OLIV}"/>' for (x, y), r in oliver]
    delar.append(f'<path d="{P_D}" transform="translate({P_TX:.2f} {P_TY:.2f}) scale({P_SKALA:.4f})" fill="{GULD}" fill-rule="evenodd" stroke="{BG}" stroke-width="{14 / P_SKALA:.3f}" paint-order="stroke"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}">' + "".join(delar) + "</svg>\n"

def raster(storlek=2048):
    k = storlek / S
    sk = lambda pts: [(x*k, y*k) for x, y in pts]
    im = Image.new("RGB", (storlek, storlek), BG)
    d = ImageDraw.Draw(im)
    d.line(sk(stjalk), fill=BLAD[2], width=int(9*k), joint="curve")
    for p, c in blads:
        d.polygon(sk(p), fill=c)
    for (x, y), r in oliver:
        d.ellipse([(x-r)*k, (y-r)*k, (x+r)*k, (y+r)*k], fill=OLIV)
    # mörk kontur runt P:et så att det lossnar från bladen, sedan guldet
    mask = Image.new("L", im.size, 0)
    md = ImageDraw.Draw(mask)
    md.polygon(sk(ytter), fill=255); md.polygon(sk(hal), fill=0)
    kontur = Image.new("L", im.size, 0)
    kd = ImageDraw.Draw(kontur)
    kd.polygon(sk(ytter), fill=255, outline=255, width=int(14*k))
    kd.polygon(sk(hal), fill=0)
    kd.line(sk(hal) + sk(hal[:1]), fill=255, width=int(14*k))
    im.paste(BG, mask=kontur)
    im.paste(GULD, mask=mask)
    return im

assert len(ytter) > len(hal) > 8 and len(blads) == 9  # självtest av geometrin
UT.mkdir(parents=True, exist_ok=True)
(UT / "favicon.svg").write_text(svg(), encoding="utf-8")
stor = raster()
for namn, px in [("icon-512.png", 512), ("icon-192.png", 192), ("apple-touch-icon.png", 180), ("favicon-48.png", 48), ("favicon-32.png", 32)]:
    stor.resize((px, px), Image.LANCZOS).save(UT / namn, optimize=True)
stor.resize((256, 256), Image.LANCZOS).save(UT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("klart", sorted(p.name for p in UT.iterdir()))
