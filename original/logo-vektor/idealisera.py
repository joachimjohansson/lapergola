"""Bygger om PERGOLA-ordbilden geometriskt: vassa hörn och släta kurvor.

Utgår från potrace-spårningen av originalet (480x195 px) och gör för varje kontur:
1. tät punktlista -> hörn (snabb riktningsändring) och delar mellan hörnen
2. varje del delas i raka bitar och kurviga bitar efter krökningen
3. raka bitar anpassas till linjer; nästan vågräta/lodräta läggs exakt vågrätt/lodrätt,
   och linjer med nästan samma läge (t.ex. versalhöjd och baslinje) får exakt samma värde
4. hörn = skärningspunkten mellan två linjer (vasst); kurvor möter linjer tangentiellt (slätt)
5. kurvor delas i sina yttersta punkter (vågrät/lodrät tangent) och anpassas till kubiska
   bézierkurvor med låsta tangenter, så att de går mjukt över i linjerna

Kör: PYTHONPATH=<pylib> python idealisera.py <logo.png> <ut.json>
Skriver JSON med "d" (SVG-sökväg i originalets pixelkoordinater) och mått."""
import sys, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
import potrace

SRC, UT = Path(sys.argv[1]), Path(sys.argv[2])
K = 8
H_STEG = 0.05            # punktavstånd i originalets pixlar
HORN_VINKEL = 0.55       # radianer: riktningsändring som räknas som hörn
HORN_FONSTER = 0.9       # px före/efter
RAK_KROKNING = 0.03      # rad/px: rakare än så räknas som linje
MIN_BIT = 0.8            # px: kortare bitar slås ihop med grannen
SNAP_VINKEL = math.radians(5)
KLUSTER = 0.45           # px: linjer närmare än så får samma läge

# --- spåra originalet (samma förbehandling som logo_slutlig.py) ---
im = np.array(Image.open(SRC).convert("RGBA")).astype(float)
r, a = im[..., 0], im[..., 3]
Hh, Ww = r.shape
tack = np.clip((r - 4) / (132 - 4), 0, 1)
tack[(r > 170) | (a < 128)] = 0
tack[:24] = 0; tack[108:] = 0; tack[:, :24] = 0; tack[:, Ww-4:] = 0
stor = Image.fromarray((tack * 255).astype(np.uint8)).resize((Ww*K, Hh*K), Image.LANCZOS)
facit = np.array(stor) / 255 > 0.5
stor = np.array(stor.filter(ImageFilter.GaussianBlur(0.5 * K))) / 255
spar = potrace.Bitmap(~(stor > 0.5)).trace(turdsize=20, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                                          alphamax=1.0, opticurve=False)

def tat_lista(c):
    """Kurvan som jämnt fördelade punkter (originalets pixlar)."""
    rå = [(c.start_point.x / K, c.start_point.y / K)]
    for g in c.segments:
        p0 = rå[-1]
        if g.is_corner:
            rå += [(g.c.x / K, g.c.y / K), (g.end_point.x / K, g.end_point.y / K)]
        else:
            c1, c2, e = (g.c1.x / K, g.c1.y / K), (g.c2.x / K, g.c2.y / K), (g.end_point.x / K, g.end_point.y / K)
            for k in range(1, 41):
                u = k / 40; w = 1 - u
                rå.append(tuple(w**3*p0[i] + 3*w*w*u*c1[i] + 3*w*u*u*c2[i] + u**3*e[i] for i in (0, 1)))
    P = np.array(rå)
    if np.hypot(*(P[0] - P[-1])) < 1e-6: P = P[:-1]
    seg = np.diff(np.vstack([P, P[:1]]), axis=0)
    L = np.hypot(seg[:, 0], seg[:, 1]); s = np.concatenate([[0], np.cumsum(L)])
    tot = s[-1]; n = int(tot / H_STEG)
    t = np.linspace(0, tot, n, endpoint=False)
    Pc = np.vstack([P, P[:1]])
    x = np.interp(t, s, Pc[:, 0]); y = np.interp(t, s, Pc[:, 1])
    return np.stack([x, y], 1)

def vinkel(v): return math.atan2(v[1], v[0])
def wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi

def analysera(P):
    n = len(P); idx = np.arange(n)
    m = int(HORN_FONSTER / H_STEG)
    fram = P[(idx + m) % n] - P; bak = P - P[(idx - m) % n]
    vrid = np.array([abs(wrap(vinkel(f) - vinkel(b))) for f, b in zip(fram, bak)])
    horn = [i for i in range(n) if vrid[i] > HORN_VINKEL and vrid[i] == max(vrid[(i + j) % n] for j in range(-m, m + 1))]
    # slå ihop hörn som ligger tätt (platå)
    horn2 = []
    for i in horn:
        if not horn2 or (i - horn2[-1]) > m: horn2.append(i)
    if len(horn2) > 1 and (horn2[0] + n - horn2[-1]) <= m: horn2.pop()
    q = int(0.5 / H_STEG); w = int(0.3 / H_STEG)
    rikt = np.array([vinkel(P[(i + w) % n] - P[(i - w) % n]) for i in range(n)])
    krok = np.array([wrap(rikt[(i + q) % n] - rikt[(i - q) % n]) / (2 * q * H_STEG) for i in range(n)])
    return horn2, rikt, krok

def bitar(P, horn, krok):
    """Delar konturen i bitar: (start, slut, 'L'|'C', start_är_hörn). Index cykliska, slut exklusivt."""
    n = len(P)
    rak = np.abs(krok) < RAK_KROKNING
    zon = int(HORN_FONSTER / H_STEG)
    gränser = sorted(horn) if horn else []
    if not gränser:
        # inga hörn: börja där etiketten byter
        byten = [i for i in range(n) if rak[i] != rak[i - 1]]
        start = byten[0] if byten else 0
        delar = [(start, start + n, False)]
    else:
        delar = [(gränser[k], gränser[(k + 1) % len(gränser)] + (n if k == len(gränser) - 1 else 0), True) for k in range(len(gränser))]
    ut = []
    for s0, s1, hornstart in delar:
        ii = [i % n for i in range(s0, s1)]
        lab = [bool(rak[i]) for i in ii]
        # nära hörn: ta etiketten från strax innanför zonen
        if hornstart and len(lab) > 2 * zon + 2:
            lab[:zon] = [lab[zon]] * zon
            lab[-zon:] = [lab[-zon - 1]] * zon
        # körningar
        körn = []
        for j, v in enumerate(lab):
            if körn and körn[-1][2] == v: körn[-1][1] = j + 1
            else: körn.append([j, j + 1, v])
        # slå ihop korta körningar
        ändrat = True
        while ändrat and len(körn) > 1:
            ändrat = False
            for k, (j0, j1, v) in enumerate(körn):
                if (j1 - j0) * H_STEG < MIN_BIT:
                    if k > 0: körn[k-1][1] = j1
                    else: körn[k+1][0] = j0
                    körn.pop(k); ändrat = True
                    # slå ihop grannar med samma etikett
                    k2 = 0
                    while k2 < len(körn) - 1:
                        if körn[k2][2] == körn[k2+1][2]:
                            körn[k2][1] = körn[k2+1][1]; körn.pop(k2+1)
                        else: k2 += 1
                    break
        for k, (j0, j1, v) in enumerate(körn):
            ut.append([s0 + j0, s0 + j1, "L" if v else "C", hornstart and k == 0])
    # för konturer utan hörn kan första och sista bit ha samma typ: slå ihop
    if len(ut) > 1 and ut[0][2] == ut[-1][2] and not ut[0][3]:
        ut[-1][1] = ut[0][1] + n; ut.pop(0)
    return ut

def anpassa_linje(Q):
    c = Q.mean(0); u, sv, vt = np.linalg.svd(Q - c); d = vt[0]
    a = vinkel(d)
    for ax in (0, math.pi / 2, math.pi, -math.pi / 2, -math.pi):
        if abs(wrap(a - ax)) < SNAP_VINKEL:
            d = np.array([math.cos(ax), math.sin(ax)]).round(12); break
    return c, d

def skärning(c1, d1, c2, d2):
    A = np.array([d1, -d2]).T
    if abs(np.linalg.det(A)) < 1e-9: return None
    t = np.linalg.solve(A, c2 - c1)
    return c1 + t[0] * d1

def projicera(p, c, d): return c + np.dot(p - c, d) * d

def bez(p0, p1, p2, p3, t):
    t = t[:, None]; w = 1 - t
    return w**3*p0 + 3*w*w*t*p1 + 3*w*t*t*p2 + t**3*p3

def anpassa_kurva(Q, p0, t0, p3, t3):
    """Kubisk bézier från p0 (tangent t0) till p3 (tangent t3) som följer punkterna Q."""
    L = np.r_[0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]; t = L / L[-1]
    ch = np.hypot(*(p3 - p0)); a = b = ch / 3
    for _ in range(8):
        w = 1 - t
        B0 = w**3; B1 = 3*w*w*t; B2 = 3*w*t*t; B3 = t**3
        base = (B0 + B1)[:, None] * p0 + (B2 + B3)[:, None] * p3
        X = np.stack([(B1[:, None] * t0).ravel(), (-B2[:, None] * t3).ravel()], 1)
        y = (Q - base).ravel()
        sol, *_ = np.linalg.lstsq(X, y, rcond=None)
        a, b = max(sol[0], 0.05 * ch), max(sol[1], 0.05 * ch)
        # parameterkorrigering: närmaste punkt på kurvan
        tt = np.linspace(0, 1, 400); C = bez(p0, p0 + a*t0, p3 - b*t3, p3, tt)
        t = tt[np.argmin(((Q[:, None, :] - C[None]) ** 2).sum(-1), 1)]
    return p0 + a * t0, p3 - b * t3

def bygg_kontur(P):
    n = len(P)
    horn, rikt, krok = analysera(P)
    bs = bitar(P, [], krok)   # hörnen avgörs i vassa_hörn: korta kurvor i skarpa vinklar
    pts = lambda i0, i1: P[[i % n for i in range(i0, i1)]]
    # linjer
    for b in bs:
        if b[2] == "L":
            Q = pts(b[0], b[1]); trim = min(int(0.3 / H_STEG), len(Q) // 4)
            b.append(anpassa_linje(Q[trim:len(Q) - trim] if len(Q) > 2 * trim + 2 else Q))
        else:
            b.append(None)
    return bs, horn, rikt

# --- första passet: alla konturer, alla linjer ---
konturer = []
for c in spar:
    P = tat_lista(c)
    bs, horn, rikt = bygg_kontur(P)
    konturer.append((P, bs, horn, rikt))

# --- kluster: vågräta linjers y och lodräta linjers x får gemensamma värden ---
def klustra(värden):
    ordn = sorted(range(len(värden)), key=lambda i: värden[i]); grupper = []
    for i in ordn:
        if grupper and värden[i] - värden[grupper[-1][-1]] < KLUSTER: grupper[-1].append(i)
        else: grupper.append([i])
    ut = list(värden)
    for g in grupper:
        m = float(np.mean([värden[i] for i in g]))
        for i in g: ut[i] = m
    return ut
for axel, kolla in ((1, lambda d: abs(d[1]) < 1e-9), (0, lambda d: abs(d[0]) < 1e-9)):
    refs = [(k, j) for k, (_, bs, _, _) in enumerate(konturer) for j, b in enumerate(bs) if b[2] == "L" and kolla(b[4][1])]
    nya = klustra([konturer[k][1][j][4][0][axel] for k, j in refs])
    for (k, j), v in zip(refs, nya):
        c, d = konturer[k][1][j][4]; c = c.copy(); c[axel] = v; konturer[k][1][j][4] = (c, d)

# --- andra passet: hörnpunkter, övergångar och kurvor ---
HORN_KURVA = 6.0         # px: kortare kurva mellan två linjer i skarp vinkel blir ett vasst hörn

def vassa_hörn(bs, P):
    """Korta kurvor i skarpa vinklar är avrundade hörn i originalet: ersätt dem med ett vasst hörn.
    Mellan två linjer blir hörnet linjernas skärning; mot en lång kurva möts de i en spets."""
    n = len(P)
    def rikt_vid(b, slut):
        if b[2] == "L": return b[4][1]
        i0, i1 = b[0], b[1]; m = min(int(1.0 / H_STEG), (i1 - i0) // 2)
        a, c = (P[(i1 - m) % n], P[(i1 - 1) % n]) if slut else (P[i0 % n], P[(i0 + m) % n])
        v = c - a; return v / max(np.hypot(*v), 1e-9)
    ändrat = True
    while ändrat and len(bs) > 2:
        ändrat = False
        for k in range(len(bs)):
            cur, prev, nxt = bs[k], bs[k - 1], bs[(k + 1) % len(bs)]
            if cur[2] != "C" or (cur[1] - cur[0]) * H_STEG >= HORN_KURVA: continue
            if prev[2] == "C" and nxt[2] == "C": continue
            d1, d2 = rikt_vid(prev, True), rikt_vid(nxt, False)
            vink = math.degrees(math.acos(max(-1, min(1, abs(float(np.dot(d1, d2)))))))
            if vink < 40: continue
            mitt = (cur[0] + cur[1]) // 2
            if prev[2] == "C": prev[1] = mitt
            if nxt[2] == "C" or k + 1 < len(bs): nxt[0] = mitt if nxt[2] == "C" else cur[0]
            nxt[3] = True
            bs.pop(k); ändrat = True; break
    return bs

def sökväg(P, bs, rikt):
    n = len(P)
    bs = vassa_hörn(bs, P)
    pts = lambda i0, i1: P[[i % n for i in range(i0, i1)]]
    nb = len(bs)
    # punkt och tangent vid början av varje bit
    start_p, start_t_in, start_t_ut = [], [], []
    for k in range(nb):
        cur, prev = bs[k], bs[k - 1]
        i = cur[0] % n
        if cur[3] or True:
            pass
        if cur[2] == "L" and prev[2] == "L":
            p = skärning(prev[4][0], prev[4][1], cur[4][0], cur[4][1])
            if p is None: p = projicera(P[i], *cur[4])
        elif cur[2] == "L":
            p = projicera(P[i], *cur[4])
        elif prev[2] == "L":
            p = projicera(P[i], *prev[4])
        else:
            p = P[i].copy()
        start_p.append(p)
    def riktning_l(b, ref):
        c, d = b[4]
        return d if np.dot(d, ref) >= 0 else -d
    ut = [f"M{start_p[0][0]:.3f} {start_p[0][1]:.3f}"]
    for k in range(nb):
        cur = bs[k]; p0 = start_p[k]; p3 = start_p[(k + 1) % nb]
        if cur[2] == "L":
            ut.append(f"L{p3[0]:.3f} {p3[1]:.3f}"); continue
        Q = pts(cur[0], cur[1])
        prev, nxt = bs[k - 1], bs[(k + 1) % nb]
        hornslut = nxt[3]
        # tangenter vid ändarna
        m = int(0.8 / H_STEG)
        if prev[2] == "L" and not cur[3]: t0 = riktning_l(prev, Q[min(m, len(Q)-1)] - Q[0])
        else: v = Q[min(m, len(Q)-1)] - Q[0]; t0 = v / np.hypot(*v)
        if nxt[2] == "L" and not hornslut: t3 = riktning_l(nxt, Q[-1] - Q[max(-m, -len(Q))])
        else: v = Q[-1] - Q[max(-m, -len(Q))]; t3 = v / np.hypot(*v)
        # dela i ytterpunkter (vågrät/lodrät tangent), minst 1 px från ändarna
        delpunkter = []
        rr = np.array([rikt[i % n] for i in range(cur[0], cur[1])])
        kant = int(1.0 / H_STEG)
        for ax in (0, math.pi / 2, math.pi, -math.pi / 2):
            diff = np.array([wrap(x - ax) for x in rr])
            for j in range(kant, len(diff) - kant):
                if diff[j - 1] < 0 <= diff[j] or diff[j - 1] > 0 >= diff[j]:
                    if abs(diff[j]) < 0.3: delpunkter.append((j, ax))
        delpunkter.sort()
        bitar_ = []; j0, pa, ta = 0, p0, t0
        for j, ax in delpunkter:
            tj = np.array([math.cos(ax), math.sin(ax)]).round(12)
            pj = Q[j].copy()
            bitar_.append((Q[j0:j + 1], pa, ta, pj, tj)); j0, pa, ta = j, pj, tj
        bitar_.append((Q[j0:], pa, ta, p3, t3))
        for Qd, a0, ta0, a3, ta3 in bitar_:
            c1, c2 = anpassa_kurva(Qd, a0, ta0, a3, ta3)
            ut.append(f"C{c1[0]:.3f} {c1[1]:.3f} {c2[0]:.3f} {c2[1]:.3f} {a3[0]:.3f} {a3[1]:.3f}")
    return "".join(ut) + "Z"

D = "".join(sökväg(P, bs, rikt) for P, bs, horn, rikt in konturer)

# --- kontroll mot originalet ---
def rita(d):
    import re
    lager = np.zeros(facit.shape, bool)
    tok = re.findall(r"[MLCZ]|-?[\d.]+", d); i = 0; poly = []; cur = None
    def num():
        nonlocal i; v = float(tok[i]); i += 1; return v
    polys = []
    while i < len(tok):
        t = tok[i]; i += 1
        if t == "M": cur = (num(), num()); poly = [cur]
        elif t == "L": cur = (num(), num()); poly.append(cur)
        elif t == "C":
            c1 = (num(), num()); c2 = (num(), num()); e = (num(), num())
            for k in range(1, 25):
                u = k / 24; w = 1 - u
                poly.append(tuple(w**3*cur[j] + 3*w*w*u*c1[j] + 3*w*u*u*c2[j] + u**3*e[j] for j in (0, 1)))
            cur = e
        elif t == "Z": polys.append(poly)
    for p in polys:
        L = Image.new("1", (facit.shape[1], facit.shape[0]), 0)
        ImageDraw.Draw(L).polygon([(x*K, y*K) for x, y in p], fill=1)
        lager ^= np.array(L)
    return lager
lager = rita(D)
iou = (lager & facit).sum() / (lager | facit).sum()
info = {"d": D, "iou": float(iou), "konturer": len(konturer),
        "hörn": [len(h) for _, _, h, _ in konturer], "bitar": [[b[2] for b in bs] for _, bs, _, _ in konturer]}
UT.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
print(f"konturer {len(konturer)}, IoU {iou:.3f}")
for k, (_, bs, h, _) in enumerate(konturer):
    print(k, "hörn", len(h), "".join(b[2] for b in bs))
# granskningsbild: ny form i guld, originalets kant i rött
inre = facit[1:-1, 1:-1] & facit[:-2, 1:-1] & facit[2:, 1:-1] & facit[1:-1, :-2] & facit[1:-1, 2:]
kant = facit.copy(); kant[1:-1, 1:-1] &= ~inre
bild = np.zeros(facit.shape + (3,), np.uint8); bild[:] = (4, 4, 5)
bild[lager] = (132, 116, 78); bild[kant] = (255, 40, 40)
Image.fromarray(bild[66*K:110*K, 40*K:440*K]).save(UT.with_suffix(".png"))
assert iou > 0.95, "för stor avvikelse från originalet"
