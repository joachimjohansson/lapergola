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

# P:et: stam + skål med hål (ritas med jämn-udda fyllning)
def p_former():
    yt, yb, xl, xs = 92, 420, 150, 228      # topp, botten, vänster, stamkant
    r_ut, r_in = 104, 46
    cy = yt + r_ut                          # skålens mitt
    xc = 286                                # skålens rundning börjar här
    ytter = [(xl, yt), (xc, yt)]
    ytter += [(xc + r_ut*math.cos(a), cy + r_ut*math.sin(a)) for a in [-math.pi/2 + math.pi*i/48 for i in range(49)]]
    ytter += [(xs, cy + r_ut), (xs, yb), (xl, yb)]
    hal = [(xs, cy - r_in), (xc, cy - r_in)]
    hal += [(xc + r_in*math.cos(a), cy + r_in*math.sin(a)) for a in [-math.pi/2 + math.pi*i/32 for i in range(33)]]
    hal += [(xs, cy + r_in)]
    return ytter, hal

ytter, hal = p_former()
# P:et något mindre och centrerat, så att kvisten syns runt om
_xs = [x for x, _ in ytter]; _ys = [y for _, y in ytter]
_mx, _my = (min(_xs) + max(_xs)) / 2, (min(_ys) + max(_ys)) / 2
_skala = lambda pts: [(256 + (x - _mx) * .86, 256 + (y - _my) * .86) for x, y in pts]
ytter, hal = _skala(ytter), _skala(hal)

def svg():
    f = lambda pts: "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
    delar = [f'<rect width="{S}" height="{S}" fill="{BG}"/>',
             f'<path d="M{" L".join(f"{x:.1f} {y:.1f}" for x, y in stjalk)}" fill="none" stroke="{BLAD[2]}" stroke-width="9" stroke-linecap="round"/>']
    delar += [f'<path d="{f(p)}" fill="{c}"/>' for p, c in blads]
    delar += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="{OLIV}"/>' for (x, y), r in oliver]
    delar.append(f'<path d="{f(ytter)} {f(hal)}" fill="{GULD}" fill-rule="evenodd" stroke="{BG}" stroke-width="14" paint-order="stroke"/>')
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

assert len(ytter) > 50 and len(hal) > 30 and len(blads) == 9  # självtest av geometrin
UT.mkdir(parents=True, exist_ok=True)
(UT / "favicon.svg").write_text(svg(), encoding="utf-8")
stor = raster()
for namn, px in [("icon-512.png", 512), ("icon-192.png", 192), ("apple-touch-icon.png", 180), ("favicon-48.png", 48), ("favicon-32.png", 32)]:
    stor.resize((px, px), Image.LANCZOS).save(UT / namn, optimize=True)
stor.resize((256, 256), Image.LANCZOS).save(UT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("klart", sorted(p.name for p in UT.iterdir()))
