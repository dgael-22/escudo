"""Blender (headless): modela el escudo, UVs, materiales PBR y exporta assets/shield.glb
Uso: blender -b -P tools/build_shield.py"""
import bpy, bmesh, math, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "tools", "tex")
OUT = os.path.join(ROOT, "assets", "shield.glb")

bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------- forma
XMIN, XMAX, YMIN, YMAX = -0.40, 0.40, -0.56, 0.46
CY = -0.02          # centro del campo
N = 64              # segmentos del contorno
R = 6               # anillos del cuerpo
HALF_T = 0.02       # semi-grosor de la madera


def outline(n):
    """Contorno de escudo heraldico (heater) como polilinea star-shaped alrededor de (0,CY)."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        dx, dy = math.cos(a), math.sin(a)
        # distancia hasta el borde segun direccion: caja arriba, punta abajo
        if dy >= 0:   # mitad superior: casi rectangular con esquinas redondeadas
            p = 6.0
            r = 1.0 / (abs(dx / 0.40) ** p + abs(dy / (YMAX - CY)) ** p) ** (1 / p)
        else:         # mitad inferior: arcos que convergen en punta
            t = -dy
            # perfil: ancho = 0.40*(1-t^2.2*...) hasta punta
            def prof(y):  # semi-ancho en y<CY
                k = min(1.0, (CY - y) / (CY - YMIN))
                return 0.40 * (1 - k ** 1.7) ** 0.62
            lo, hi = 0.0, 2.0
            for _ in range(40):
                mid = (lo + hi) / 2
                y = CY + dy * mid
                if y < YMIN or abs(dx * mid) > prof(y):
                    hi = mid
                else:
                    lo = mid
            r = lo
        pts.append((dx * r, CY + dy * r))
    return pts


OUTL = outline(N)


def surf_z(x, y):
    """Superficie media del escudo: curvatura cilindrica + ligera inclinacion en Y."""
    return 0.12 * (1 - (x / 0.40) ** 2) * (1 - 0.30 * ((y - CY) / 0.55) ** 2) - 0.02


def new_obj(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


# ---------------------------------------------------------------- 1. cuerpo de madera
def build_body():
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    W, H = XMAX - XMIN, YMAX - YMIN

    def uv_front(x, y):
        return ((x - XMIN) / W * 0.5, (y - YMIN) / H)

    def uv_back(x, y):
        return (0.5 + (1 - (x - XMIN) / W) * 0.5, (y - YMIN) / H)

    def ring_verts(k, zsign):
        s = k / R
        vs = []
        for (x, y) in OUTL:
            px, py = x * s, CY + (y - CY) * s
            vs.append(bm.verts.new((px, py, surf_z(px, py) + zsign * HALF_T)))
        return vs

    cf = bm.verts.new((0, CY, surf_z(0, CY) + HALF_T))
    cb = bm.verts.new((0, CY, surf_z(0, CY) - HALF_T))
    front = [ring_verts(k, +1) for k in range(1, R + 1)]
    back = [ring_verts(k, -1) for k in range(1, R + 1)]

    def set_uv(face, fn):
        for l in face.loops:
            l[uv].uv = fn(l.vert.co.x, l.vert.co.y)

    for i in range(N):
        j = (i + 1) % N
        f = bm.faces.new((cf, front[0][i], front[0][j]))
        set_uv(f, uv_front)
        f = bm.faces.new((cb, back[0][j], back[0][i]))
        set_uv(f, uv_back)
        for k in range(R - 1):
            f = bm.faces.new((front[k][i], front[k + 1][i], front[k + 1][j], front[k][j]))
            set_uv(f, uv_front)
            f = bm.faces.new((back[k][j], back[k + 1][j], back[k + 1][i], back[k][i]))
            set_uv(f, uv_back)
        # pared del canto (queda oculta bajo el reborde de acero): UV colapsada sobre el borde frontal
        f = bm.faces.new((front[-1][i], back[-1][i], back[-1][j], front[-1][j]))
        set_uv(f, uv_front)
    # el cuerpo es una cascara cerrada; no hay vertices sueltos
    return new_obj("Escudo_Madera", bm)


# ---------------------------------------------------------------- 2. acero: reborde, flejes y remaches
def build_steel():
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # 2a. reborde (perfil cerrado barrido a lo largo del contorno)
    prof = [(-0.055, 0.026), (-0.025, 0.034), (0.010, 0.032), (0.032, 0.016),
            (0.032, -0.016), (0.010, -0.032), (-0.025, -0.034), (-0.055, -0.026)]
    rings = []
    for i, (x, y) in enumerate(OUTL):
        px, py = OUTL[(i + 1) % N][0] - OUTL[i - 1][0], OUTL[(i + 1) % N][1] - OUTL[i - 1][1]
        L = math.hypot(px, py)
        nx, ny = py / L, -px / L          # normal exterior 2D
        z0 = surf_z(x, y)
        rings.append([bm.verts.new((x + nx * d, y + ny * d, z0 + h)) for d, h in prof])
    P = len(prof)
    for i in range(N):
        j = (i + 1) % N
        for k in range(P):
            m = (k + 1) % P
            bm.faces.new((rings[i][k], rings[j][k], rings[j][m], rings[i][m]))

    # 2b. flejes en cruz siguiendo la curvatura (seccion rectangular)
    def strap(p0, p1, half_w, seg, thick=0.012):
        rs = []
        d = Vector((p1[0] - p0[0], p1[1] - p0[1])).normalized()
        nrm = Vector((-d.y, d.x))
        for s in range(seg + 1):
            t = s / seg
            x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
            ring = []
            for (w, h) in ((-half_w, 0.0), (half_w, 0.0), (half_w, thick), (-half_w, thick)):
                px, py = x + nrm.x * w, y + nrm.y * w
                ring.append(bm.verts.new((px, py, surf_z(px, py) + HALF_T - 0.002 + h)))
            rs.append(ring)
        for s in range(seg):
            for k in range(4):
                m = (k + 1) % 4
                bm.faces.new((rs[s][k], rs[s][m], rs[s + 1][m], rs[s + 1][k]))
        bm.faces.new(rs[0][::-1])
        bm.faces.new(rs[-1])

    strap((0, 0.40), (0, -0.50), 0.032, 18)      # vertical (palo)
    strap((-0.375, 0.0), (0.375, 0.0), 0.032, 18)  # horizontal (faja)

    # 2c. remaches (cupulas bajas)
    def rivet(x, y, z, r=0.017):
        res = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=r)
        bmesh.ops.scale(bm, vec=(1, 1, 0.6), verts=res["verts"])
        bmesh.ops.translate(bm, vec=(x, y, z), verts=res["verts"])
        # eliminar mitad inferior (invisible)
        low = [v for v in res["verts"] if v.co.z < z - 1e-4]
        bmesh.ops.delete(bm, geom=low, context="VERTS")

    for i in range(0, N, 5):             # 13 remaches sobre el reborde frontal
        x, y = OUTL[i]
        px, py = OUTL[(i + 1) % N][0] - OUTL[i - 1][0], OUTL[(i + 1) % N][1] - OUTL[i - 1][1]
        L = math.hypot(px, py)
        nx, ny = py / L, -px / L
        d, h = -0.035, 0.032
        rx, ry = x + nx * d, y + ny * d
        rivet(rx, ry, surf_z(x, y) + h)
    for t in (-0.32, -0.20, 0.20, 0.32):    # remaches en la faja
        rivet(t, 0, surf_z(t, 0) + HALF_T + 0.010)
    for t in (0.30, 0.18, -0.20, -0.35):    # remaches en el palo
        rivet(0, t, surf_z(0, t) + HALF_T + 0.010)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = new_obj("Escudo_Acero", bm)
    return ob


# ---------------------------------------------------------------- 3. bronce: placa estrellada + cupula
def build_bronze():
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    SC = 0.38                 # 1 uv = 0.38 m (ver make_textures.py)
    ZB = HALF_T + 0.012 - 0.002  # sobre el fleje

    def uvp(x, y):
        return (x / SC + 0.5, y / SC + 0.5)

    def zf(x, y, off):
        return surf_z(x, y) + off

    # placa estrella de 8 puntas (radio ext .19, int .12) con borde biselado
    pts = 16
    star = []
    for i in range(pts):
        a = 2 * math.pi * i / pts + math.pi / 8
        r = 0.19 if i % 2 == 0 else 0.125
        star.append((math.cos(a) * r, math.sin(a) * r))
    rings = []
    for k, (s, off) in enumerate(((0.0, ZB + 0.020), (0.55, ZB + 0.020), (0.92, ZB + 0.016), (1.0, ZB + 0.004))):
        if k == 0:
            rings.append([bm.verts.new((0, 0, zf(0, 0, off)))])
        else:
            rings.append([bm.verts.new((x * s, y * s, zf(x * s, y * s, off))) for (x, y) in star])
    for i in range(pts):
        j = (i + 1) % pts
        bm.faces.new((rings[0][0], rings[1][i], rings[1][j]))
        for k in range(1, len(rings) - 1):
            bm.faces.new((rings[k][i], rings[k + 1][i], rings[k + 1][j], rings[k][j]))
    # cupula (umbo)
    rad = 0.115
    base_z = zf(0, 0, ZB + 0.020)
    res = bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=10, radius=rad)
    bmesh.ops.scale(bm, vec=(1, 1, 0.55), verts=res["verts"])
    bmesh.ops.translate(bm, vec=(0, 0, base_z), verts=res["verts"])
    low = [v for v in res["verts"] if v.co.z < base_z - 1e-4]
    bmesh.ops.delete(bm, geom=low, context="VERTS")
    # corona de la cupula (pequeño anillo elevado)
    rr = bmesh.ops.create_circle(bm, cap_ends=False, radius=rad * 1.0, segments=24)

    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = uvp(l.vert.co.x, l.vert.co.y)
    # eliminar el circulo suelto (aristas sin cara)
    loose = [e for e in bm.edges if not e.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="EDGES")
    loosev = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loosev, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj("Escudo_Bronce", bm)


# ---------------------------------------------------------------- UV acero: smart project + empaquetado
def unwrap_steel(ob):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, correct_aspect=True)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------- materiales
def img(name, path, srgb):
    im = bpy.data.images.load(path)
    im.name = name
    im.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    im.pack()
    return im


def make_mat(name, key, normal_strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    c = nt.nodes.new("ShaderNodeTexImage")
    c.image = img(f"{name}_BaseColor", f"{TEX}/{key}_limpio_color.png", True)
    o = nt.nodes.new("ShaderNodeTexImage")
    o.image = img(f"{name}_ORM", f"{TEX}/{key}_limpio_orm.png", False)
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = img(f"{name}_Normal", f"{TEX}/{key}_limpio_normal.png", False)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = normal_strength
    nt.links.new(c.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(o.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    nt.links.new(n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


body, steel, bronze = build_body(), build_steel(), build_bronze()
unwrap_steel(steel)
for ob, (nm, key, ns) in ((body, ("Madera", "madera", 1.0)), (steel, ("Acero", "acero", 1.0)),
                          (bronze, ("Bronce", "bronce", 1.0))):
    ob.data.materials.append(make_mat(nm, key, ns))
    ob.data.name = ob.name

# ---------------------------------------------------------------- limpieza y export
for ob in (body, steel, bronze):
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.shade_smooth()
    ob.select_set(False)

# Orientacion: el escudo se modelo con Y arriba y frente hacia +Z. Se gira 90 grados en X
# (Blender es Z-up) y se APLICA la transformacion; al exportar queda de pie, de frente a +Z en glTF.
bpy.ops.object.select_all(action="DESELECT")
for ob in (body, steel, bronze):
    ob.select_set(True)
    ob.rotation_euler = (math.radians(90), 0, 0)
bpy.context.view_layer.objects.active = body
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

tris = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in (body, steel, bronze))
print("TRIS", {ob.name: sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in (body, steel, bronze)}, tris)

bpy.ops.object.select_all(action="SELECT")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_yup=True,
                          export_apply=True, export_image_format="AUTO", export_materials="EXPORT",
                          export_texcoords=True, export_normals=True, export_tangents=False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "tools", "shield.blend"))
print("EXPORTADO", OUT, os.path.getsize(OUT))
