"""Texturas PBR procedurales del escudo heraldico (numpy + Pillow).
Salida: fuente-3d/tex/<material>_<estado>_{color,orm,normal}.png   estado = envejecido | limpio
  orm = (R: oclusion, G: roughness, B: metallic)  -> formato glTF metallicRoughness.

Madera (1024):  mitad izquierda = frente (tablones verticales), mitad derecha = dorso.
Acero  (1024):  franja superior (filas 0-112) = marco, repetible 2 veces en U alrededor del perimetro;
                resto = decal planar frontal (u = x+0.5, v = (y+0.62)/1.2*0.85) para boss, ornamentos y remaches.
Bronce (512):   cuadrante sup-izq = rombo superior, sup-der = rombo inferior (decals 0.24 m -> 256 px),
                inf-izq = collar del boss (0.32 m -> 256 px), inf-der = liso (tachuelas)."""
import numpy as np, os
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(99)


def noise(h, w, cy, cx, seed=0):
    """Ruido de valores bicubico, periodico en ambos ejes (se puede repetir sin costuras)."""
    r = np.random.default_rng(seed)
    g = np.pad(r.random((cy, cx)).astype(np.float32), ((1, 2), (1, 2)), mode="wrap")
    im = Image.fromarray(g).resize((int(round(w * (cx + 3) / cx)), int(round(h * (cy + 3) / cy))), Image.BICUBIC)
    a = np.asarray(im)
    oy, ox = int(round(h / cy)), int(round(w / cx))
    return a[oy:oy + h, ox:ox + w]


def fbm(h, w, cy, cx, octaves=5, seed=0):
    t = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        t += amp * noise(h, w, max(1, cy * 2 ** o), max(1, cx * 2 ** o), seed + o)
        tot += amp
        amp *= .5
    return t / tot


def norm01(a):
    return (a - a.min()) / (a.max() - a.min() + 1e-9)


def mix(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


def normal_from_height(hm, strength):
    gy, gx = np.gradient(hm)
    nx, ny = -gx * strength, gy * strength      # +Y arriba (OpenGL / glTF)
    nz = np.ones_like(hm)
    l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    return np.stack([nx / l, ny / l, nz / l], -1) * .5 + .5


def save(name, color, rough, metal, height, nstrength):
    c = (np.clip(color, 0, 1) * 255).astype(np.uint8)
    orm = (np.clip(np.stack([np.ones_like(rough), rough, metal], -1), 0, 1) * 255).astype(np.uint8)
    n = (normal_from_height(height, nstrength) * 255).astype(np.uint8)
    for suf, arr in (("color", c), ("orm", orm), ("normal", n)):
        Image.fromarray(arr).save(f"{OUT}/{name}_{suf}.png", optimize=True)
    print("ok", name)


def scratches(c, h, count, length, amt, light=True, seed=0, wrap_x=False):
    r = np.random.default_rng(seed)
    H, W = h.shape
    for _ in range(count):
        xx, yy, ln, ang = r.integers(0, W), r.integers(0, H), r.integers(*length), r.uniform(-.35, .35)
        for t in range(ln):
            xv, yv = int(xx + t), int(yy + t * ang)
            if wrap_x:
                xv %= W
            if 0 <= xv < W and 0 <= yv < H:
                c[yv, xv] = np.minimum(c[yv, xv] * (1.35 if light else .55), 1)
                h[yv, xv] -= amt


def vcracks(c, h, count, length, amt, seed=0):
    r = np.random.default_rng(seed)
    H, W = h.shape
    for _ in range(count):
        xx, yy, ln = r.integers(0, W), r.integers(0, H), r.integers(*length)
        for t in range(ln):
            yv, xv = yy + t, int(xx + np.sin(t * .07 + xx) * 2)
            if 0 <= yv < H and 0 <= xv < W:
                c[yv, xv] *= .4
                h[yv, xv] -= amt


# ---------------------------------------------------------------- MADERA (1024)
def wood(aged):
    S = 1024
    H = W = S
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    cols = np.zeros((H, W, 3), np.float32)
    hm = np.zeros((H, W), np.float32)
    rg = np.zeros((H, W), np.float32)
    dark = np.array([.075, .042, .024]) if aged else np.array([.13, .07, .04])
    light = np.array([.34, .20, .105]) if aged else np.array([.52, .32, .17])
    for half, nplank in ((0, 6), (1, 5)):
        hw = W // 2
        x0 = half * hw
        lx = x[:, x0:x0 + hw] - x0
        wd = np.random.default_rng(10 + half).uniform(.75, 1.25, nplank)
        edges = np.concatenate([[0], np.cumsum(wd) / wd.sum() * hw])
        pid = np.clip(np.searchsorted(edges, lx, side="right") - 1, 0, nplank - 1)
        px = (lx - edges[pid]) / (edges[pid + 1] - edges[pid])
        sd = 20 + half * 9
        warp = fbm(H, hw, 3, 12, 4, seed=sd) * 8
        phase = np.random.default_rng(sd).uniform(0, 40, nplank)[pid]
        rings = np.sin(lx * .17 + warp * 3 + phase) * .5 + .5
        fine = fbm(H, hw, 12, 96, 3, seed=sd + 40)
        grain = norm01(.55 * rings + .45 * fine)
        tint = (np.random.default_rng(sd + 3).random(nplank)[pid] - .5) * .3
        c = mix(dark + 0 * lx[..., None], light + 0 * lx[..., None], grain ** 1.15) * (1 + tint[..., None])
        seam = np.clip(1 - np.minimum(px, 1 - px) / .018, 0, 1)      # junta entre tablones
        c *= (1 - .75 * seam[..., None])
        h_ = grain * .22 - seam * 1.0
        r_ = .55 + .2 * fine - .1 * rings
        if aged:
            wr = fbm(H, hw, 6, 6, 5, seed=sd + 90)
            dry = np.clip((wr - .5) * 3, 0, 1)
            c = mix(c, np.array([.30, .24, .18]) + 0 * lx[..., None], dry * .55)
            dirt = np.clip(fbm(H, hw, 18, 18, 4, seed=sd + 7) - .45, 0, 1) * 2
            c *= (1 - .45 * dirt[..., None])
            edge_wear = np.clip(1 - np.minimum(px, 1 - px) / .05, 0, 1) * fbm(H, hw, 30, 30, 3, seed=sd + 5)
            c *= (1 - .3 * edge_wear[..., None])
            vcracks(c, h_, 40, (60, 320), .6, seed=sd + 1)
            scratches(c, h_, 80, (15, 90), .3, light=True, seed=sd + 2)
            for _ in range(5):                           # grietas / astillas cortas transversales
                xx, yy, ln = rng.integers(10, hw - 60), rng.integers(40, H - 40), rng.integers(30, 70)
                for t in range(ln):
                    xv, yv = xx + t, int(yy + np.sin(t * .3) * 3)
                    c[yv, xv] *= .3
                    h_[yv, xv] -= .8
            r_ = .78 + .15 * fine + .1 * dry
            h_ = h_ + (wr - .5) * .5
        else:
            scratches(c, h_, 15, (15, 60), .1, light=True, seed=sd + 2)
            r_ = .5 + .15 * fine
        sl = slice(x0, x0 + hw)
        cols[:, sl], hm[:, sl], rg[:, sl] = c, h_, r_
    save("madera_" + ("envejecido" if aged else "limpio"), cols, rg, np.zeros_like(rg), hm, 8.0 if aged else 6.0)


# ---------------------------------------------------------------- ACERO (1024)
def steel(aged):
    S = 1024
    Y, X = np.mgrid[0:S, 0:S].astype(np.float32)
    u, v = (X + .5) / S, 1 - (Y + .5) / S
    xm, ym = u - .5, v / .85 * 1.2 - .62                       # metros (region planar)
    hammer = fbm(S, S, 48, 48, 3, seed=31)
    brush = fbm(S, S, 3, 220, 3, seed=3)
    r = np.hypot(xm, ym)
    low = Y >= 154
    ax = np.clip(1 - np.abs(xm) / .0035, 0, 1) * ((np.abs(ym) > .12) & (np.abs(ym) < .34))
    ay = np.clip(1 - np.abs(ym) / .0035, 0, 1) * ((np.abs(xm) > .12) & (np.abs(xm) < .34))
    rings = np.zeros_like(r)
    for rr in (.045, .085, .118):
        rings = np.maximum(rings, np.clip(1 - np.abs(r - rr) / .0025, 0, 1))
    groove = np.where(low, np.maximum(np.maximum(ax, ay), rings), 0)
    strip = Y < 113                                            # marco: lineas en los extremos del perfil
    edge = np.clip(1 - np.abs(Y - 20) / 3, 0, 1) + np.clip(1 - np.abs(Y - 92) / 3, 0, 1)
    groove = np.where(strip, np.clip(edge, 0, 1), groove)
    if aged:
        base = np.array([.34, .33, .33])
        rust = norm01(fbm(S, S, 5, 5, 5, seed=22))
        rm = np.clip((rust - .64) * 3.5, 0, 1)
        speck = np.clip((norm01(fbm(S, S, 64, 64, 2, seed=2)) - .72) * 6, 0, 1)
        rm = np.clip(rm + speck * .6 * rust, 0, 1)
        c = mix(base * (.75 + .5 * hammer[..., None]) * (.9 + .15 * brush[..., None]),
                np.array([.42, .20, .09]) + 0 * hammer[..., None], rm * .6)
        dirt = np.clip(norm01(fbm(S, S, 16, 16, 4, seed=8)) - .5, 0, 1) * 2
        c *= (1 - .22 * dirt[..., None])
        c = mix(c, c * .4, groove)
        rough = .6 + .2 * brush + .25 * rm
        metal = 1 - .65 * rm
        h = hammer * .18 + rm * .5 - groove * .8 + brush * .1
        scratches(c, h, 120, (20, 140), .25, light=True, seed=5, wrap_x=True)
    else:
        base = np.array([.56, .58, .62])
        c = mix(base * (.9 + .15 * brush[..., None]), base * .45, groove)
        rough = .26 + .16 * brush + .1 * groove
        metal = np.ones((S, S), np.float32)
        h = hammer * .05 + brush * .08 - groove * .8
        scratches(c, h, 25, (20, 90), .1, light=True, seed=5, wrap_x=True)
    save("acero_" + ("envejecido" if aged else "limpio"), c, rough, metal, h, 3.5)


# ---------------------------------------------------------------- BRONCE (512)
def bronze(aged):
    S = 512
    Y, X = np.mgrid[0:S, 0:S].astype(np.float32)
    hammer = fbm(S, S, 24, 24, 3, seed=41)
    groove = np.zeros((S, S), np.float32)
    ridge = np.zeros((S, S), np.float32)

    def quad(cx0, cy0):
        return (X >= cx0) & (X < cx0 + 256) & (Y >= cy0) & (Y < cy0 + 256)

    def fleur(px, py):
        """Flor de lis en metros (px, py), py hacia arriba."""
        m = ((px / .011) ** 2 + ((py - .006) / .036) ** 2) < 1
        for sgn in (-1, 1):
            cx, cy = sgn * .022, .003
            a = np.radians(sgn * 38)
            xr = (px - cx) * np.cos(a) + (py - cy) * np.sin(a)
            yr = -(px - cx) * np.sin(a) + (py - cy) * np.cos(a)
            m |= ((xr / .008) ** 2 + (yr / .024) ** 2) < 1
        m |= (np.abs(py + .022) < .004) & (np.abs(px) < .028)
        m |= (np.abs(px) < .006) & (py < -.022) & (py > -.045)
        return m
    for (cx0, cy0, hw, hh) in ((0, 0, .075, .095), (256, 0, .07, .09)):          # rombos superior / inferior
        q = quad(cx0, cy0)
        px = (X - cx0 - 128) * .48 / 512
        py = (128 - (Y - cy0)) * .48 / 512
        diam = np.abs(px) / hw + np.abs(py) / hh
        gl = np.maximum(np.clip(1 - np.abs(diam - .80) / .035, 0, 1), np.clip(1 - np.abs(diam - .92) / .02, 0, 1))
        groove = np.where(q, gl, groove)
        ridge = np.where(q, np.maximum(ridge, fleur(px, py) * 1.0), ridge)
    q = quad(0, 256)                                                              # collar del boss
    px = (X / 256 - .5) * .32
    py = (.5 - (Y - 256) / 256) * .32
    rr, ang = np.hypot(px, py), np.arctan2(py, px)
    teeth = (np.abs(np.sin(ang * 18)) > .5) * np.clip(1 - np.abs(rr - .139) / .012, 0, 1)
    groove = np.where(q, np.maximum(teeth * .6, np.clip(1 - np.abs(rr - .128) / .002, 0, 1)), groove)
    h = hammer * .08 - groove * .7 + ridge * .5
    if aged:
        base, dark = np.array([.40, .29, .13]), np.array([.10, .065, .03])
    else:
        base, dark = np.array([.85, .58, .26]), np.array([.40, .24, .09])
    c = mix(base * (.82 + .35 * hammer[..., None]), dark + 0 * base, np.clip(groove * .85, 0, 1))
    c = c * (1 + .2 * ridge[..., None])
    rough = .3 + .12 * hammer + .22 * groove
    metal = np.ones((S, S), np.float32)
    if aged:
        pat = norm01(fbm(S, S, 6, 6, 5, seed=61))
        dirt = np.clip(norm01(fbm(S, S, 14, 14, 4, seed=9)) - .45, 0, 1) * 1.8
        crev = np.clip(groove * 1.0 + (pat - .55) * 3, 0, 1)
        c = mix(c, np.array([.16, .30, .24]) + 0 * c, crev * .65)      # patina verde
        c *= (1 - .35 * dirt[..., None])
        rough = .55 + .3 * crev + .1 * dirt
        metal = 1 - .6 * crev
        h = h + crev * .4
    else:
        rough = .16 + .08 * hammer + .12 * groove
    save("bronce_" + ("envejecido" if aged else "limpio"), c, rough, metal, h, 4.0)


if __name__ == "__main__":
    for a in (True, False):
        wood(a)
        steel(a)
        bronze(a)
