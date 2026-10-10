"""Genera texturas PBR procedurales (limpio / desgastado) para Madera, Acero y Bronce.
Salida: tools/tex/<mat>_<estado>_{color,orm,normal}.png
  orm = (R: oclusion, G: roughness, B: metallic)  -> formato glTF metallicRoughness."""
import numpy as np, os
from PIL import Image

rng = np.random.default_rng(7)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
os.makedirs(OUT, exist_ok=True)


def noise(h, w, cells_y, cells_x, seed=0):
    """Ruido de valores suave con celdas anisotropas."""
    r = np.random.default_rng(seed)
    g = r.random((cells_y + 3, cells_x + 3)).astype(np.float32)
    im = Image.fromarray(g).resize((w * (cells_x + 3) // cells_x, h * (cells_y + 3) // cells_y), Image.BICUBIC)
    a = np.asarray(im)
    oy, ox = a.shape[0] // (cells_y + 3), a.shape[1] // (cells_x + 3)
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


def normal_from_height(hm, strength):
    gy, gx = np.gradient(hm)  # filas hacia abajo
    nx, ny = -gx * strength, gy * strength  # +Y arriba (OpenGL / glTF)
    nz = np.ones_like(hm)
    l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    return np.stack([nx / l, ny / l, nz / l], -1) * .5 + .5


def save(name, color, rough, metal, height, nstrength):
    c = (np.clip(color, 0, 1) * 255).astype(np.uint8)
    orm = np.stack([np.ones_like(rough), rough, metal], -1)
    orm = (np.clip(orm, 0, 1) * 255).astype(np.uint8)
    n = (normal_from_height(height, nstrength) * 255).astype(np.uint8)
    for suf, arr in (("color", c), ("orm", orm), ("normal", n)):
        Image.fromarray(arr).save(f"{OUT}/{name}_{suf}.png", optimize=True)
    print("ok", name)


def mix(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


# ------------------------------------------------------------ MADERA (1024)
# Mitad izquierda = frente, mitad derecha = dorso (ver build_shield.py)
def wood(worn):
    S = 1024
    H = W = S
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    cols = np.zeros((H, W, 3), np.float32)
    hm = np.zeros((H, W), np.float32)
    rg = np.zeros((H, W), np.float32)
    for half in (0, 1):
        hw = W // 2
        x0 = half * hw
        lx = x[:, x0:x0 + hw] - x0
        nplank = 5
        pw = hw / nplank
        pid = np.floor(lx / pw).astype(int)
        px = (lx % pw) / pw
        sd = 11 + half * 5
        warp = fbm(H, hw, 3, 12, 4, seed=sd) * 7
        rings = np.sin(lx * .18 + warp * 3.0 + pid * 17) * .5 + .5
        fine = fbm(H, hw, 12, 90, 3, seed=sd + 40)
        grain = .55 * rings + .45 * fine
        tint = (rng.random(nplank + 1)[pid] - .5) * .18
        c = mix(np.array([.20, .105, .045]) + 0 * lx[..., None], np.array([.50, .30, .14]) + 0 * lx[..., None],
                norm01(grain) ** 1.1)
        c = c * (1 + tint[..., None])
        seam = np.minimum(px, 1 - px)
        groove = np.clip(1 - seam / .03, 0, 1)  # junta entre tablas
        c *= (1 - .65 * groove[..., None])
        h_ = grain * .25 - groove * .9
        r_ = .55 + .2 * fine - .1 * rings
        if worn:
            wr = fbm(H, hw, 6, 6, 5, seed=sd + 90)
            dry = np.clip((wr - .5) * 3, 0, 1)
            c = mix(c, np.array([.42, .36, .29]) + 0 * lx[..., None], dry * .75)  # madera seca/desvaida
            dirt = np.clip(fbm(H, hw, 20, 20, 4, seed=sd + 7) - .45, 0, 1) * 2
            c *= (1 - .35 * dirt[..., None])
            for _ in range(70):  # aranazos y grietas verticales
                xx, yy, ln = rng.integers(0, hw), rng.integers(0, H), rng.integers(30, 200)
                for t in range(ln):
                    yv, xv = yy + t, int(xx + np.sin(t * .05 + xx) * 2)
                    if 0 <= yv < H and 0 <= xv < hw:
                        c[yv, xv] *= .45
                        h_[yv, xv] -= .5
            r_ = .8 + .15 * fine + .1 * dry
            h_ = h_ + (wr - .5) * .5
        sl = slice(x0, x0 + hw)
        cols[:, sl], hm[:, sl], rg[:, sl] = c, h_, r_
    save(f"madera_{'desgastado' if worn else 'limpio'}", cols, rg, np.zeros_like(rg), hm, 9.0 if worn else 7.0)


# ------------------------------------------------------------ ACERO (512)
def steel(worn):
    S = 512
    brush = fbm(S, S, 2, 160, 3, seed=3)  # cepillado horizontal
    fine = fbm(S, S, 6, 6, 3, seed=5)
    c = np.ones((S, S, 3), np.float32) * np.array([.74, .76, .79]) * (.9 + .12 * brush[..., None])
    rough = .26 + .18 * brush + .04 * fine
    metal = np.ones((S, S), np.float32)
    h = brush * .12
    if worn:
        rust = norm01(fbm(S, S, 5, 5, 5, seed=22))
        rm = np.clip((rust - .62) * 5, 0, 1)
        speck = np.clip((norm01(fbm(S, S, 60, 60, 2, seed=2)) - .7) * 6, 0, 1)
        rm = np.clip(rm + speck * .6 * rust, 0, 1)
        c = mix(c * .8, np.array([.42, .19, .08]) + 0 * c, rm)
        dirt = np.clip(norm01(fbm(S, S, 14, 14, 4, seed=8)) - .5, 0, 1) * 2
        c *= (1 - .25 * dirt[..., None])
        rough = .5 + .25 * brush + .35 * rm
        metal = 1 - .7 * rm
        h = brush * .3 + rm * .6 + fbm(S, S, 40, 40, 3, seed=9) * .2
    for _ in range(40 if worn else 14):  # rayas
        xx, yy, ln, ang = rng.integers(0, S), rng.integers(0, S), rng.integers(20, 120), rng.uniform(-.5, .5)
        for t in range(ln):
            xv, yv = int(xx + t), int(yy + t * ang)
            if 0 <= xv < S and 0 <= yv < S:
                c[yv, xv] = np.minimum(c[yv, xv] * 1.15, 1)
                h[yv, xv] -= .25
    save(f"acero_{'desgastado' if worn else 'limpio'}", c, rough, metal, h, 3.0)


# ------------------------------------------------------------ BRONCE (512)
# Decal planar frontal: centro de textura = centro del emblema; 1 uv = 0.38 m
def bronze(worn):
    S = 512
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    u = (x + .5) / S - .5
    v = .5 - (y + .5) / S
    r = np.hypot(u, v)
    ang = np.arctan2(v, u)
    hammer = fbm(S, S, 22, 22, 3, seed=31)
    base, dark = np.array([.78, .48, .20]), np.array([.38, .20, .07])
    groove = np.zeros_like(r)
    for rr in (.07, .15, .23, .29):  # anillos grabados en la cupula
        groove = np.maximum(groove, np.clip(1 - np.abs(r - rr) / .006, 0, 1))
    groove = np.maximum(groove, np.clip(1 - np.abs(r - .335) / .007, 0, 1))
    rays = np.clip(1 - np.abs(np.sin(ang * 4)) * r / .012, 0, 1) * ((r > .345) & (r < .47))
    dots = np.clip(1 - np.abs(r - .43) / .012, 0, 1) * (np.sin(ang * 16) > .86)
    h = hammer * .10 - groove * .9 - rays * .6 + dots * .6
    c = mix(base * (.85 + .3 * hammer[..., None]), dark + 0 * base, np.clip(groove * .8 + rays * .6, 0, 1))
    rough = .32 + .12 * hammer + .25 * groove
    metal = np.ones((S, S), np.float32)
    if worn:
        pat = norm01(fbm(S, S, 6, 6, 5, seed=61))
        crev = np.clip(groove * 1.2 + rays * 1.2 + (pat - .55) * 3, 0, 1)
        c = mix(c * .8, np.array([.16, .42, .33]) + 0 * c, crev)  # cardenillo
        rough = .5 + .35 * crev
        metal = 1 - .75 * crev
        h = h + crev * .5
    save(f"bronce_{'desgastado' if worn else 'limpio'}", c, rough, metal, h, 4.0 if worn else 3.0)


if __name__ == "__main__":
    for w in (False, True):
        wood(w)
        steel(w)
        bronze(w)
