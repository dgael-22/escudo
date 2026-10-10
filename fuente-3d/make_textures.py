"""Texturas PBR procedurales del escudo (numpy + Pillow).
Salida en fuente-3d/tex/<material>_{color,orm,normal}.png
  orm = (R: oclusion, G: roughness, B: metallic)  -> formato glTF metallicRoughness.

Materiales:  madera (1024)  cuero (512, escamas)  acero (512)  bronce envejecido / limpio (1024, atlas)
Atlas del bronce (1024 x 1024; v hacia arriba, fila = (1-v)*1024):
  reborde (trenza):        filas 0-102, todo el ancho
  radios (compartido):     x 0-102,   filas 133-1024
  medallon solar (decal):  x 123-635, filas 512-1024   (0.44 m -> 512 px, centro de la textura = centro del escudo)
  adornos sup./inf.:       x 655-1015, filas 133-1024"""
import numpy as np, os
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(2024)


def noise(h, w, cells_y, cells_x, seed=0):
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


def mix(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


def normal_from_height(hm, strength):
    gy, gx = np.gradient(hm)
    nx, ny = -gx * strength, gy * strength   # +Y arriba (convencion OpenGL de glTF)
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


# ---------------------------------------------------------------- MADERA oscura (1024), trasera
def wood():
    S = 1024
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    nplank = 6
    pw = S / nplank
    pid = np.floor(x / pw).astype(int)
    px = (x % pw) / pw
    warp = fbm(S, S, 3, 14, 4, seed=5) * 8
    rings = np.sin(x * .16 + warp * 3 + pid * 23) * .5 + .5
    fine = fbm(S, S, 14, 100, 3, seed=45)
    grain = norm01(.55 * rings + .45 * fine)
    tint = (rng.random(nplank + 1)[pid] - .5) * .25
    c = mix(np.array([.075, .04, .022]) + 0 * x[..., None], np.array([.30, .17, .085]) + 0 * x[..., None], grain ** 1.2)
    c *= (1 + tint[..., None])
    seam = np.clip(1 - np.minimum(px, 1 - px) / .025, 0, 1)
    c *= (1 - .7 * seam[..., None])
    dirt = np.clip(fbm(S, S, 8, 8, 4, seed=77) - .5, 0, 1) * 2
    c *= (1 - .35 * dirt[..., None])
    h = grain * .25 - seam * .9
    for _ in range(50):                         # aranazos
        xx, yy, ln = rng.integers(0, S), rng.integers(0, S), rng.integers(30, 220)
        for t in range(ln):
            yv, xv = yy + t, int(xx + np.sin(t * .05 + xx) * 2)
            if 0 <= yv < S and 0 <= xv < S:
                c[yv, xv] *= .55
                h[yv, xv] -= .4
    rough = .68 + .2 * fine
    save("madera", c, rough, np.zeros_like(rough), h, 8.0)


# ---------------------------------------------------------------- CUERO oscuro con escamas (512)
# Todos los paneles comparten la misma region UV (solape intencional); las puntas miran hacia +v (hacia el borde).
def leather():
    S = 512
    Y, X = np.mgrid[0:S, 0:S].astype(np.float32)
    h = np.zeros((S, S), np.float32)
    edge = np.zeros((S, S), np.float32)
    covered = np.zeros((S, S), bool)
    cw, ch = 32, 16
    for j in range(S // ch + 3):                # de arriba (borde) hacia abajo: las de abajo tapan a las de arriba
        cy = j * ch - 6
        for i in range(-1, S // cw + 2):
            cx = i * cw + (cw // 2 if j % 2 else 0)
            y0, y1, x0, x1 = max(cy - 34, 0), min(cy + 20, S), max(cx - 20, 0), min(cx + 20, S)
            if y0 >= y1 or x0 >= x1:
                continue
            dx = (X[y0:y1, x0:x1] - cx) / 16.0
            dy = cy - Y[y0:y1, x0:x1]
            dyn = np.where(dy > 0, dy / 24.0, dy / 17.0)
            d = np.where(dy > 0, np.abs(dx) + dyn * .75, np.sqrt(dx ** 2 + dyn ** 2))
            m = d < 1
            h[y0:y1, x0:x1][m] = ((1 - d) ** .55)[m]
            edge[y0:y1, x0:x1][m] = d[m]
            covered[y0:y1, x0:x1][m] = True
    grain = fbm(S, S, 40, 40, 3, seed=14)
    t = np.clip((edge - .7) * 3.2, 0, 1) * covered
    c = mix(np.array([.045, .035, .027]) * (.8 + .6 * grain[..., None]), np.array([.50, .37, .17]) + 0 * grain[..., None], t)
    c = np.where(covered[..., None], c, np.array([.015, .012, .01]))
    rough = .5 + .2 * grain + .15 * t
    save("cuero", c, rough, np.zeros_like(rough), h * .7 + grain * .05, 5.0)


# ---------------------------------------------------------------- ACERO oscuro (512)
def steel():
    S = 512
    brush = fbm(S, S, 2, 160, 3, seed=3)
    fine = fbm(S, S, 6, 6, 3, seed=5)
    c = np.ones((S, S, 3), np.float32) * np.array([.42, .43, .46]) * (.85 + .3 * brush[..., None])
    c *= (1 - .2 * np.clip(fbm(S, S, 12, 12, 4, seed=8) - .5, 0, 1)[..., None] * 2)
    rough = .38 + .2 * brush + .06 * fine
    h = brush * .15
    for _ in range(30):
        xx, yy, ln, a = rng.integers(0, S), rng.integers(0, S), rng.integers(20, 120), rng.uniform(-.5, .5)
        for t in range(ln):
            xv, yv = int(xx + t), int(yy + t * a)
            if 0 <= xv < S and 0 <= yv < S:
                c[yv, xv] = np.minimum(c[yv, xv] * 1.3, 1)
                h[yv, xv] -= .25
    save("acero", c, rough, np.ones((S, S), np.float32), h, 3.0)


# ---------------------------------------------------------------- BRONCE (1024), atlas
def bronze(aged):
    S = 1024
    Y, X = np.mgrid[0:S, 0:S].astype(np.float32)
    hammer = fbm(S, S, 40, 40, 3, seed=31)
    groove = np.zeros((S, S), np.float32)
    ridge = np.zeros((S, S), np.float32)
    # reborde: cuerda trenzada (110 repeticiones alrededor)
    rim = Y < 103
    rope = np.sin(X / (S / 110.0) * 2 * np.pi - Y * .35) * .5 + .5
    ridge = np.where(rim, rope, ridge)
    groove = np.where(rim, np.clip(1 - rope * 2.2, 0, 1), groove)
    # radios: filetes laterales y cheurones centrales
    sp = (X < 102) & (Y >= 133)
    lx, ly = X / 102.0, (S - Y) / 891.0
    side = np.clip(1 - np.abs(np.abs(lx - .5) - .36) / .03, 0, 1)
    chev = np.abs(((ly / .05) % 1) - .5 - np.abs(lx - .5) * .9)
    chv = np.clip(1 - chev / .05, 0, 1) * (np.abs(lx - .5) < .3)
    groove = np.where(sp, np.maximum(side, chv), groove)
    # medallon solar: anillos, rayos, dientes y estrella central (coinciden con el perfil del modelo)
    bx0, by0 = 123, 512
    bm = (X >= bx0) & (X < bx0 + 512) & (Y >= by0)
    px = (X - bx0 - 256) / 512.0 * 0.44
    py = (256 - (Y - by0)) / 512.0 * 0.44
    r, ang = np.hypot(px, py), np.arctan2(py, px)
    g = np.zeros((S, S), np.float32)
    for rr in (.03, .07, .11, .145, .162, .178, .215):
        g = np.maximum(g, np.clip(1 - np.abs(r - rr) / .0025, 0, 1))
    g = np.maximum(g, np.clip(1 - np.abs(np.sin(ang * 8)) / .04, 0, 1) * ((r > .075) & (r < .14)))
    teeth = (np.abs(np.sin(ang * 24)) > .93) & (r > .18) & (r < .212)
    star = np.clip(1 - (r - .028 * (1 + .45 * np.cos(ang * 8))) / .004, 0, 1) * (r < .05)
    g = np.maximum(g, np.maximum(teeth * 1.0, star))
    groove = np.where(bm, g, groove)
    h = hammer * .08 - groove * .8 + ridge * .35
    if aged:
        base, dark = np.array([.42, .30, .13]), np.array([.10, .065, .03])
    else:
        base, dark = np.array([.86, .60, .27]), np.array([.40, .24, .09])
    c = mix(base * (.82 + .35 * hammer[..., None]), dark + 0 * base, np.clip(groove * .85, 0, 1))
    c *= (1 - .22 * ((1 - ridge) * rim)[..., None])
    rough = .32 + .12 * hammer + .22 * groove
    metal = np.ones((S, S), np.float32)
    if aged:
        pat = norm01(fbm(S, S, 7, 7, 5, seed=61))
        dirt = np.clip(norm01(fbm(S, S, 18, 18, 4, seed=9)) - .45, 0, 1) * 1.8
        crev = np.clip(groove * 1.0 + (pat - .62) * 3, 0, 1)
        c = mix(c, np.array([.16, .30, .24]) + 0 * c, crev * .6)       # cardenillo (patina verde)
        c *= (1 - .35 * dirt[..., None])
        rough = .55 + .3 * crev + .1 * dirt
        metal = 1 - .7 * crev
        h = h + crev * .4
    else:
        rough = .16 + .08 * hammer + .12 * groove
    save("bronce_" + ("envejecido" if aged else "limpio"), c, rough, metal, h, 4.0 if aged else 3.0)


if __name__ == "__main__":
    wood(); leather(); steel(); bronze(True); bronze(False)
