"""Blender (headless): modela el escudo heraldico, UVs, materiales PBR y exporta assets/shield.glb
Uso: python fuente-3d/make_textures.py  y luego  blender -b -P fuente-3d/build_shield.py

Piezas -> material:
  Escudo_Madera : cuerpo de tablones (las vetas y juntas son textura)          -> Madera
  Escudo_Acero  : marco ancho, remaches, boss central, 4 ornamentos goticos     -> Acero
  Escudo_Bronce : 2 rombos decorativos, collar del boss, 4 tachuelas            -> Bronce"""
import bpy, bmesh, math, os
from mathutils import Vector

SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
TEX = os.path.join(SRC, "tex")
OUT = os.path.join(ROOT, "assets", "shield.glb")
bpy.ops.wm.read_factory_settings(use_empty=True)

HT = 0.018                      # semi-grosor de la madera
HW = 0.36                       # semi-ancho
Y_TOP, Y_CORNER, Y_SIDE, Y_TIP = 0.58, 0.40, 0.08, -0.62


def surf(x, y):
    """Superficie media: curvada en horizontal, con ligera caida hacia la punta."""
    return 0.08 * (1 - (x / 0.40) ** 2) - 0.03 * (y / 0.6) ** 2


def zt(x, y):
    return surf(x, y) + HT      # cara frontal de la madera


# ---------------------------------------------------------------- contorno heraldico
def top_y(x):
    return Y_CORNER + (Y_TOP - Y_CORNER) * (1 - abs(x) / HW) ** 1.6


def half_w(y):
    k = min(1.0, (Y_SIDE - y) / (Y_SIDE - Y_TIP))
    return HW * (1 - k ** 1.6)


def make_outline():
    R = []
    for i in range(9):                                  # borde superior: pico -> esquina
        x = HW * i / 8
        R.append((x, top_y(x)))
    for y in (0.30, 0.20):                              # lado recto
        R.append((HW, y))
    for i in range(13):                                 # lado curvo hasta la punta
        y = Y_SIDE + (Y_TIP - Y_SIDE) * i / 12
        R.append((half_w(y), y))
    L = [(-x, y) for (x, y) in R[-2:0:-1]]              # lado izquierdo (sin pico ni punta)
    return R + L


OUTL = make_outline()
N = len(OUTL)


def outline_frames():
    """Normal exterior 2D (con correccion de inglete) y longitud de arco acumulada por vertice."""
    nrm, arc, s = [], [], 0.0
    for i, (x, y) in enumerate(OUTL):
        p, q = OUTL[i - 1], OUTL[(i + 1) % N]
        def en(a, b):
            d = Vector((b[0] - a[0], b[1] - a[1])).normalized()
            return Vector((d.y, -d.x))
        n1, n2 = en(p, (x, y)), en((x, y), q)
        n = (n1 + n2).normalized()
        sc = 1.0 / max(0.6, n.dot(n1))
        nrm.append((n.x, n.y, sc))
        arc.append(s)
        s += math.hypot(q[0] - x, q[1] - y)
    return nrm, arc, s


NRM, ARC, PERIM = outline_frames()


class Mesh:
    def __init__(self, name):
        self.name, self.bm = name, bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def v(self, x, y, z):
        return self.bm.verts.new((x, y, z))

    def face(self, verts, uvfn, ref):
        """Crea la cara, asigna UV (funcion de la posicion o lista) y la orienta lejos de `ref`."""
        f = self.bm.faces.new(verts)
        for k, l in enumerate(f.loops):
            l[self.uv].uv = uvfn(l.vert.co, k) if callable(uvfn) else uvfn[k]
        f.normal_update()
        if f.normal.dot(f.calc_center_median() - Vector(ref)) < 0:
            f.normal_flip()
        return f

    def build(self):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.collection.objects.link(ob)
        return ob


def uv_wood_front(p, k):
    return ((p.x + HW) / (2 * HW) * 0.5, (p.y - Y_TIP) / (Y_TOP - Y_TIP))


def uv_planar_steel(p, k):
    return (p.x + 0.5, (p.y + 0.62) / 1.2 * 0.85)


# ---------------------------------------------------------------- 1. cuerpo de madera
def build_wood():
    m = Mesh("Escudo_Madera")
    RB = 4
    cf, cb = m.v(0, 0, zt(0, 0)), m.v(0, 0, surf(0, 0) - HT)
    F = [[m.v(x * k / RB, y * k / RB, surf(x * k / RB, y * k / RB) + HT) for (x, y) in OUTL] for k in range(1, RB + 1)]
    B = [[m.v(x * k / RB, y * k / RB, surf(x * k / RB, y * k / RB) - HT) for (x, y) in OUTL] for k in range(1, RB + 1)]
    ref = (0, 0, surf(0, 0))

    def uv_back(p, k):
        return (0.5 + (1 - (p.x + HW) / (2 * HW)) * 0.5, (p.y - Y_TIP) / (Y_TOP - Y_TIP))
    for i in range(N):
        j = (i + 1) % N
        m.face([cf, F[0][i], F[0][j]], uv_wood_front, ref)
        m.face([cb, B[0][i], B[0][j]], uv_back, ref)
        for k in range(RB - 1):
            m.face([F[k][i], F[k + 1][i], F[k + 1][j], F[k][j]], uv_wood_front, ref)
            m.face([B[k][i], B[k + 1][i], B[k + 1][j], B[k][j]], uv_back, ref)
        m.face([F[-1][i], B[-1][i], B[-1][j], F[-1][j]], uv_wood_front, ref)    # canto: queda bajo el marco
    return m.build()


# ---------------------------------------------------------------- 2. acero: marco, boss, ornamentos, remaches
def build_steel():
    m = Mesh("Escudo_Acero")
    # 2a. marco ancho (perfil cerrado barrido por el contorno; U = 2 repeticiones de la franja del atlas)
    prof = [(-.075, .020), (-.060, .036), (-.015, .040), (.008, .028), (.012, 0.0), (.008, -.028), (-.015, -.036), (-.060, -.030)]
    P = len(prof)
    rings = []
    for i, (x, y) in enumerate(OUTL):
        nx, ny, sc = NRM[i]
        z0 = surf(x, y)
        rings.append([m.v(x + nx * d * sc, y + ny * d * sc, z0 + h) for d, h in prof])
    for i in range(N):
        j = (i + 1) % N
        ui = ARC[i] / PERIM * 2
        uj = (ARC[j] / PERIM * 2) if j else 2.0
        cen = sum((v.co for v in rings[i]), Vector()) / P
        for k in range(P):
            q = (k + 1) % P
            vk, vq = .995 - .105 * k / P, .995 - .105 * (k + 1) / P
            m.face([rings[i][k], rings[j][k], rings[j][q], rings[i][q]], [(ui, vk), (uj, vk), (uj, vq), (ui, vq)], cen)

    # 2b. boss central (superficie de revolucion; sigue la curvatura de la madera)
    prof_b = [(0, .095), (.03, .093), (.06, .087), (.085, .075), (.10, .058), (.11, .040), (.115, .028),
              (.12, .020), (.125, .012), (.13, -.004)]
    SB = 48
    lat = []
    for r, h in prof_b:
        if r == 0:
            lat.append([m.v(0, 0, zt(0, 0) + h)])
        else:
            lat.append([m.v(r * math.cos(2 * math.pi * i / SB), r * math.sin(2 * math.pi * i / SB),
                            zt(r * math.cos(2 * math.pi * i / SB), r * math.sin(2 * math.pi * i / SB)) + h)
                        for i in range(SB)])
    rb = (0, 0, zt(0, 0) - .1)
    for k in range(len(prof_b) - 1):
        for i in range(SB):
            j = (i + 1) % SB
            if k == 0:
                m.face([lat[0][0], lat[1][i], lat[1][j]], uv_planar_steel, rb)
            else:
                m.face([lat[k][i], lat[k + 1][i], lat[k + 1][j], lat[k][j]], uv_planar_steel, rb)

    # 2c. cuatro ornamentos goticos puntiagudos (placa fina, contorno en punta de lanza con pas laterales)
    Rh = [(.028, .12), (.018, .16), (.020, .20), (.050, .215), (.085, .235), (.060, .250), (.030, .255), (.026, .290), (0.0, .345)]
    poly = Rh + [(-x, y) for (x, y) in Rh[-2::-1]]
    poly = [(x * 1.15, y * 1.15) for (x, y) in poly]      # ornamentos algo mas grandes
    for ang in (90, 0, 270, 180):
        a = math.radians(ang)
        al, pe = Vector((math.cos(a), math.sin(a))), Vector((-math.sin(a), math.cos(a)))
        top, bot = [], []
        for (px_, py_) in poly:
            q = al * py_ + pe * px_
            top.append(m.v(q.x, q.y, zt(q.x, q.y) + .010))
            bot.append(m.v(q.x, q.y, zt(q.x, q.y) - .002))
        ref = (al.x * .25, al.y * .25, -.05)
        f = m.face(top, uv_planar_steel, ref)
        bmesh.ops.triangulate(m.bm, faces=[f], ngon_method="EAR_CLIP")
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            m.face([top[i], top[j], bot[j], bot[i]], uv_planar_steel, ref)

    # 2d. remaches repartidos por el marco (cada ~8.5 cm de perimetro)
    def rivet(x, y, z, r=.0125):
        res = bmesh.ops.create_uvsphere(m.bm, u_segments=8, v_segments=4, radius=r)
        bmesh.ops.scale(m.bm, vec=(1, 1, .65), verts=res["verts"])
        bmesh.ops.translate(m.bm, vec=(x, y, z), verts=res["verts"])
        bmesh.ops.delete(m.bm, geom=[v for v in res["verts"] if v.co.z < z - 1e-4], context="VERTS")
        for f in m.bm.faces:
            if (f.calc_center_median() - Vector((x, y, z))).length < r * 1.5:
                for l in f.loops:
                    l[m.uv].uv = uv_planar_steel(l.vert.co, 0)
    nriv = int(PERIM / .085)
    for t in range(nriv):
        s = (t + .5) * PERIM / nriv
        i = max(k for k in range(N) if ARC[k] <= s)
        j = (i + 1) % N
        seg = (ARC[j] if j else PERIM) - ARC[i]
        f = (s - ARC[i]) / seg
        x = OUTL[i][0] + (OUTL[j][0] - OUTL[i][0]) * f
        y = OUTL[i][1] + (OUTL[j][1] - OUTL[i][1]) * f
        nx = NRM[i][0] * (1 - f) + NRM[j][0] * f
        ny = NRM[i][1] * (1 - f) + NRM[j][1] * f
        nl = math.hypot(nx, ny)
        px, py = x - .040 * nx / nl, y - .040 * ny / nl
        rivet(px, py, surf(px, py) + .040 + .003)
    return m.build()


# ---------------------------------------------------------------- 3. bronce: rombos, collar del boss, tachuelas
def build_bronze():
    m = Mesh("Escudo_Bronce")

    def diamond(cx, cy, hw, hh, qu, qv):
        """Placa romboidal biselada. Decal 0.24 m en el cuadrante (qu,qv) del atlas de 512."""
        uvf = lambda p, k: (qu + (p.x - cx) / .24 * .5, qv + (p.y - cy) / .24 * .5)
        outer = [(cx, cy + hh), (cx + hw, cy), (cx, cy - hh), (cx - hw, cy)]
        s = .86
        inner = [(cx + (x - cx) * s, cy + (y - cy) * s) for (x, y) in outer]
        o = [m.v(x, y, surf(x, y) + HT - .001) for (x, y) in outer]
        n = [m.v(x, y, surf(x, y) + HT + .014) for (x, y) in inner]
        ref = (cx, cy, -.1)
        for i in range(4):
            j = (i + 1) % 4
            m.face([o[i], o[j], n[j], n[i]], uvf, ref)
        m.face(n, uvf, ref)
    diamond(0, .38, .075, .095, .25, .75)          # superior
    diamond(0, -.40, .07, .09, .75, .75)           # inferior

    # collar del boss (anillo con perfil de 4 puntos)
    pr = [(.122, -.004), (.126, .014), (.150, .014), (.156, -.004)]
    SB = 48
    col = [[m.v(r * math.cos(2 * math.pi * i / SB), r * math.sin(2 * math.pi * i / SB),
                zt(r * math.cos(2 * math.pi * i / SB), r * math.sin(2 * math.pi * i / SB)) + h)
            for i in range(SB)] for r, h in pr]
    uvc = lambda p, k: ((p.x / .32 + .5) * .5, (p.y / .32 + .5) * .5)
    for k in range(3):
        for i in range(SB):
            j = (i + 1) % SB
            m.face([col[k][i], col[k + 1][i], col[k + 1][j], col[k][j]], uvc, (0, 0, -.1))

    # tachuelas de bronce en cada ornamento
    for ang in (90, 0, 270, 180):
        a = math.radians(ang)
        x, y = .21 * math.cos(a), .21 * math.sin(a)
        z = zt(x, y) + .010 + .003
        res = bmesh.ops.create_uvsphere(m.bm, u_segments=8, v_segments=4, radius=.014)
        bmesh.ops.scale(m.bm, vec=(1, 1, .65), verts=res["verts"])
        bmesh.ops.translate(m.bm, vec=(x, y, z), verts=res["verts"])
        bmesh.ops.delete(m.bm, geom=[v for v in res["verts"] if v.co.z < z - 1e-4], context="VERTS")
        for f in m.bm.faces:
            if (f.calc_center_median() - Vector((x, y, z))).length < .02:
                for l in f.loops:
                    l[m.uv].uv = (.8 + (l.vert.co.x - x) * 2, .15 + (l.vert.co.y - y) * 2)
    return m.build()


# ---------------------------------------------------------------- materiales
def img(name, path, srgb):
    im = bpy.data.images.load(path)
    im.name = name
    im.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    im.pack()
    return im


def make_mat(name, key):
    mt = bpy.data.materials.new(name)
    mt.use_nodes = True
    nt = mt.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    c, o, n = (nt.nodes.new("ShaderNodeTexImage") for _ in range(3))
    c.image = img(f"{name}_BaseColor", f"{TEX}/{key}_color.png", True)
    o.image = img(f"{name}_ORM", f"{TEX}/{key}_orm.png", False)
    n.image = img(f"{name}_Normal", f"{TEX}/{key}_normal.png", False)
    sep, nm = nt.nodes.new("ShaderNodeSeparateColor"), nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(c.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(o.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    nt.links.new(n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mt


body, steel, bronze = build_wood(), build_steel(), build_bronze()
objs = [body, steel, bronze]

for ob, (nm, key) in zip(objs, (("Madera", "madera_envejecido"), ("Acero", "acero_envejecido"), ("Bronce", "bronce_envejecido"))):
    ob.data.materials.append(make_mat(nm, key))
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.mesh.delete_loose()
    bpy.ops.object.mode_set(mode="OBJECT")
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(45))
    except Exception:
        bpy.ops.object.shade_smooth()
    ob.select_set(False)

# Orientacion: modelado con +Z al frente; giro de 90 grados en X aplicado (Blender es Z-up, glTF Y-up)
bpy.ops.object.select_all(action="DESELECT")
for ob in objs:
    ob.select_set(True)
    ob.rotation_euler = (math.radians(90), 0, 0)
bpy.context.view_layer.objects.active = body
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

tris = {ob.name: sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in objs}
print("TRIS", tris, sum(tris.values()))

bpy.ops.object.select_all(action="SELECT")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True,
                          export_apply=True, export_image_format="JPEG", export_jpeg_quality=85,
                          export_materials="EXPORT", export_texcoords=True, export_normals=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SRC, "escudo.blend"))
print("EXPORTADO", OUT, os.path.getsize(OUT))
