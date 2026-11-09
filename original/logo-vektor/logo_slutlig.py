"""Sätter ihop Pergola-loggan som vektor:
- ramarna som exakta rektanglar (uppmätta i originalet)
- PERGOLA spårad med potrace, sedan uträtad: nästan raka kurvor blir linjer, nästan vågräta/lodräta
  kanter rätas upp och kanter vid versalhöjd/baslinje läggs exakt på linjen
- TRATTORIA E VINO från undertext.json (Century Gothic, bokstav för bokstav på originalets platser)
Kör: PYTHONPATH=<pylib> python logo_slutlig.py <logo.png> <undertext.json> <ut-mapp>"""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
import potrace

SRC, UNDER, UT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
K, BLUR = 8, 0.6
GULD, TEXT, SVART = "#d2ab67", "#84744e", "#040405"

im = np.array(Image.open(SRC).convert("RGBA")).astype(float)
r, a = im[..., 0], im[..., 3]
H, W = r.shape
tack = np.clip((r - 4) / (132 - 4), 0, 1)
tack[(r > 170) | (a < 128)] = 0
tack[:24] = 0; tack[108:] = 0; tack[:, :24] = 0; tack[:, W-4:] = 0      # bara PERGOLA
stor = Image.fromarray((tack * 255).astype(np.uint8)).resize((W*K, H*K), Image.LANCZOS)
stor = np.array(stor.filter(ImageFilter.GaussianBlur(BLUR * K))) / 255
spar = potrace.Bitmap(~(stor > 0.5)).trace(turdsize=20, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                                          alphamax=0.8, opticurve=True, opttolerance=0.4)

def till_seg(c):
    s = (c.start_point.x / K, c.start_point.y / K)
    segs = []
    for g in c.segments:
        if g.is_corner:
            segs += [["L", (g.c.x / K, g.c.y / K)], ["L", (g.end_point.x / K, g.end_point.y / K)]]
        else:
            segs.append(["C", (g.c1.x / K, g.c1.y / K), (g.c2.x / K, g.c2.y / K), (g.end_point.x / K, g.end_point.y / K)])
    return s, segs

def avst_linje(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    L = max(((bx-ax)**2 + (by-ay)**2) ** .5, 1e-9)
    return abs((bx-ax)*(ay-py) - (ax-px)*(by-ay)) / L

kurvor = [till_seg(c) for c in spar]
allay = [p[1] for s, segs in kurvor for g in segs for p in [g[-1]]]
TOPP = np.percentile(allay, 2); BOTTEN = np.percentile(allay, 98)

def putsa(start, segs):
    # 1) nästan raka kurvor -> linjer
    pts = [start]; ut = []
    for g in segs:
        p0 = pts[-1]
        if g[0] == "C" and max(avst_linje(g[1], p0, g[3]), avst_linje(g[2], p0, g[3])) < 0.18:
            g = ["L", g[3]]
        ut.append(g); pts.append(g[-1])
    # 2) slå ihop följande linjer på samma räta linje
    rad = [ut[0]]
    for g in ut[1:]:
        if g[0] == "L" and rad[-1][0] == "L":
            p0 = start if len(rad) == 1 else rad[-2][-1]
            if avst_linje(rad[-1][1], p0, g[1]) < 0.12:
                rad[-1] = g; continue
        rad.append(g)
    # 3) räta upp: punkter nära topp/baslinje läggs exakt där; korta avvikelser i vågräta/lodräta linjer tas bort
    def snap(p):
        x, y = p
        if abs(y - TOPP) < 0.45: y = TOPP
        if abs(y - BOTTEN) < 0.45: y = BOTTEN
        return (x, y)
    start = snap(start)
    rad = [[g[0], *g[1:-1], snap(g[-1])] for g in rad]
    pts = [start] + [g[-1] for g in rad]
    for i, g in enumerate(rad):
        if g[0] != "L": continue
        p0, p1 = pts[i], pts[i+1]
        dx, dy = p1[0]-p0[0], p1[1]-p0[1]
        if abs(dx) > 1.5 and abs(dy) < 0.6:                    # vågrät
            y = (p0[1] + p1[1]) / 2 if p0[1] not in (TOPP, BOTTEN) and p1[1] not in (TOPP, BOTTEN) else (p0[1] if p0[1] in (TOPP, BOTTEN) else p1[1])
            pts[i] = (p0[0], y); pts[i+1] = (p1[0], y)
        elif abs(dy) > 1.5 and abs(dx) < 0.6:                  # lodrät
            x = (p0[0] + p1[0]) / 2
            pts[i] = (x, p0[1]); pts[i+1] = (x, p1[1])
    start = pts[0]
    rad = [[g[0], *g[1:-1], pts[i+1]] for i, g in enumerate(rad)]
    # kurvornas stödpunkter följer med när ändpunkterna flyttas (kort avstånd, ingen omräkning)
    return start, rad, pts

def f(v): return f"{v:.2f}".rstrip("0").rstrip(".")
def d_av(start, rad):
    d = [f"M{f(start[0])} {f(start[1])}"]
    for g in rad:
        d.append(g[0] + " ".join(f"{f(x)} {f(y)}" for x, y in g[1:]))
    return "".join(d) + "Z"

putsade = [putsa(s, segs) for s, segs in kurvor]
pergola_d = "".join(d_av(s, rad) for s, rad, _ in putsade)
under = json.loads(UNDER.read_text(encoding="utf-8"))
under_d = under["d"]

# Tre lager med samma mått, 460 x 175, förskjutna 10 px: bakre guldram, svart ruta, främre guldram (2 px kanter).
# Uppmätt pixel för pixel i originalet; allt utanför är genomskinligt.
ram = lambda x, y: f'<path d="M{x} {y}h460v175h-460zM{x+2} {y+2}v171h456v-171z" fill="{GULD}" fill-rule="evenodd"/>'
ramar = ram(0, 0) + f'<rect x="10" y="10" width="460" height="175" fill="{SVART}"/>' + ram(20, 20)
text = f'<path d="{pergola_d}" fill="{TEXT}" fill-rule="evenodd"/><path d="{under_d}" fill="{TEXT}"/>'
UT.mkdir(parents=True, exist_ok=True)
(UT / "pergola-logo.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W*2}" height="{H*2}">{ramar}{text}</svg>\n', encoding="utf-8")
x0, y0, x1, y1 = 40, 68, 440, 133
(UT / "pergola-ordbild.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{(x1-x0)*3}" height="{(y1-y0)*3}">{text}</svg>\n', encoding="utf-8")
(UT / "pergola-ordbild-svart.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{(x1-x0)*3}" height="{(y1-y0)*3}">'
    + text.replace(TEXT, "#151b16") + "</svg>\n", encoding="utf-8")

# självtest: den putsade PERGOLA ska fortfarande täcka originalet väl
facit = (np.array(Image.fromarray((tack * 255).astype(np.uint8)).resize((W*K, H*K), Image.LANCZOS)) / 255) > 0.5
lager = np.zeros(facit.shape, bool)
for s, rad, pts in putsade:
    poly = [s]
    for g in rad:
        if g[0] == "L": poly.append(g[1])
        else:
            p0 = poly[-1]; c1, c2, e = g[1], g[2], g[3]
            for k in range(1, 13):
                u = k / 12; w = 1 - u
                poly.append(tuple(w**3*p0[i] + 3*w*w*u*c1[i] + 3*w*u*u*c2[i] + u**3*e[i] for i in (0, 1)))
    L = Image.new("1", (W*K, H*K), 0); ImageDraw.Draw(L).polygon([(x*K, y*K) for x, y in poly], fill=1)
    lager ^= np.array(L)
iou = (lager & facit).sum() / (lager | facit).sum()
print(f"PERGOLA: {len(putsade)} konturer, IoU mot originalet {iou:.3f}; undertext ({under['font']}) IoU {under['iou']:.3f}")
print(f"topp {TOPP:.2f} baslinje {BOTTEN:.2f}")
assert iou > 0.9

# Granskningsbild: vektorn i 8x (guld) med originalets kant som röd kontur ovanpå
from PIL import ImageChops
v = Image.fromarray((lager * 255).astype(np.uint8))
o = Image.fromarray((facit * 255).astype(np.uint8))
kant = ImageChops.subtract(o, o.filter(ImageFilter.MinFilter(3)))
bild = Image.new("RGB", v.size, (4, 4, 5))
bild.paste((132, 116, 78), mask=v)
bild.paste((255, 40, 40), mask=kant)
bild.crop((40*K, 66*K, 440*K, 110*K)).save("granska.png")
