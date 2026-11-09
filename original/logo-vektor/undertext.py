"""Bygger "TRATTORIA E VINO" med ett riktigt typsnitt, bokstav för bokstav på originalets platser,
och mäter hur väl olika typsnitt täcker originalet. Skriver bästa som SVG-sökväg.
Kör: PYTHONPATH=<pylib> python undertext.py <logo.png> <ut.json>"""
import sys, json, os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.basePen import BasePen

class PolyPen(BasePen):
    def __init__(self, gs):
        super().__init__(gs); self.polys = []; self.cur = []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, a, b, c):
        p0 = self.cur[-1]
        for k in range(1, 9):
            u = k / 8; w = 1 - u
            self.cur.append(tuple(w**3*p0[i] + 3*w*w*u*a[i] + 3*w*u*u*b[i] + u**3*c[i] for i in (0, 1)))
    def _qCurveToOne(self, a, b):
        p0 = self.cur[-1]
        for k in range(1, 9):
            u = k / 8; w = 1 - u
            self.cur.append(tuple(w*w*p0[i] + 2*w*u*a[i] + u*u*b[i] for i in (0, 1)))
    def _closePath(self):
        if len(self.cur) > 2: self.polys.append(self.cur)
        self.cur = []
    _endPath = _closePath

K = 8
TEXT = "TRATTORIAEVINO"
im = np.array(Image.open(sys.argv[1]).convert("RGBA")).astype(float)
r = im[..., 0]
tack = np.clip((r - 4) / (132 - 4), 0, 1)
tack[(r > 170) | (im[..., 3] < 128)] = 0
Y0, Y1 = 110, 136
zon = tack[Y0:Y1]
kol = zon.max(0) > 0.25
runs, inne = [], None
for x, v in enumerate(kol):
    if v and inne is None: inne = x
    if not v and inne is not None: runs.append((inne, x)); inne = None
runs = [(a, b) for a, b in runs if 30 < a < 450]
assert len(runs) == len(TEXT), f"hittade {len(runs)} bokstäver"
rader = np.nonzero(zon.max(1) > 0.25)[0]
# kanter i subpixel: där täckningen passerar 0.5 i 8x
stor = np.array(Image.fromarray((tack * 255).astype(np.uint8)).resize((im.shape[1]*K, im.shape[0]*K), Image.LANCZOS)) / 255
facit = stor > 0.5
bokst = []
for (a, b), ch in zip(runs, TEXT):
    del_ = facit[Y0*K:Y1*K, a*K-K:b*K+K]
    ys, xs = np.nonzero(del_)
    bokst.append((ch, (a*K-K + xs.min()) / K, (a*K-K + xs.max() + 1) / K, (Y0*K + ys.min()) / K, (Y0*K + ys.max() + 1) / K))
topp = np.median([t for _, _, _, t, _ in bokst]); botten = np.median([u for *_, u in bokst])
caph = botten - topp
print(f"versalhöjd {caph:.2f} px, topp {topp:.2f}, botten {botten:.2f}")

def rendera(polys):
    lager = np.zeros(facit.shape, bool)
    for p in polys:
        L = Image.new("1", (facit.shape[1], facit.shape[0]), 0)
        ImageDraw.Draw(L).polygon([(x*K, y*K) for x, y in p], fill=1)
        lager ^= np.array(L)
    return lager

def glyfer(fontfil, idx=0):
    f = TTFont(fontfil, fontNumber=idx)
    gs = f.getGlyphSet(); cmap = f.getBestCmap()
    return gs, cmap

def bygg(fontfil):
    gs, cmap = glyfer(fontfil)
    hH = BoundsPen(gs); gs[cmap[ord("H")]].draw(hH)
    cap = hH.bounds[3] - hH.bounds[1]
    s = caph / cap
    delar = []; pp = PolyPen(gs)
    for ch, x0, x1, *_ in bokst:
        g = gs[cmap[ord(ch)]]
        bp = BoundsPen(gs); g.draw(bp)
        gx0, gy0, gx1, gy1 = bp.bounds
        dx0 = (x0 + x1) / 2 - (gx0 + gx1) / 2 * s
        # finjustera sidled per bokstav: välj förskjutningen som täcker originalet bäst
        fon = np.zeros(facit.shape, bool); fon[Y0*K:Y1*K, int((x0-3)*K):int((x1+3)*K)] = True
        bast_dx, bast_v = dx0, -1
        for steg in range(-12, 13):
            dx = dx0 + steg / K
            tp = PolyPen(gs); g.draw(TransformPen(tp, (s, 0, 0, -s, dx, botten)))
            rr = rendera(tp.polys) & fon; ff = facit & fon
            v = (rr & ff).sum() / max((rr | ff).sum(), 1)
            if v > bast_v: bast_v, bast_dx = v, dx
        dx = bast_dx
        pen = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        g.draw(TransformPen(pen, (s, 0, 0, -s, dx, botten)))
        delar.append(pen.getCommands())
        g.draw(TransformPen(pp, (s, 0, 0, -s, dx, botten)))
    return " ".join(delar), pp.polys

kand = {
    "Century Gothic": "C:/Windows/Fonts/GOTHIC.TTF",
}
lok = os.path.expandvars(r"%LOCALAPPDATA%/Microsoft/Windows/Fonts")
for vikt in ["ExtraLight", "Light", "Regular"]:
    p = Path(lok) / f"Montserrat-{vikt}.ttf"
    if p.exists(): kand[f"Montserrat {vikt}"] = str(p)

zonmask = np.zeros(facit.shape, bool); zonmask[Y0*K:Y1*K] = True
ref = facit & zonmask
res = {}
for namn, fil in kand.items():
    d, polys = bygg(fil)
    r_ = rendera(polys) & zonmask
    iou = (r_ & ref).sum() / (r_ | ref).sum()
    res[namn] = (iou, d)
    print(f"{namn:22s} IoU {iou:.3f}")
bast = max(res, key=lambda n: res[n][0])
print("bäst:", bast)
Path(sys.argv[2]).write_text(json.dumps({"font": bast, "iou": res[bast][0], "d": res[bast][1]}), encoding="utf-8")
assert res[bast][0] > 0.6

# Kontrollbild: rött = originalet, grönt = typsnittet
r_ = rendera(bygg(kand[bast])[1])
jmf = np.stack([facit*255, r_*255, np.zeros_like(facit, dtype=np.uint8)], -1).astype(np.uint8)
Image.fromarray(jmf[Y0*K:Y1*K, 90*K:390*K]).save("undertext_kontroll.png")
