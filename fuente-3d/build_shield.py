"""Blender (headless): modela el escudo circular, UVs, materiales PBR y exporta assets/shield.glb
Uso: blender -b -P fuente-3d/build_shield.py     (antes: python fuente-3d/make_textures.py)

Piezas -> material:
  Escudo_Madera : disco trasero                                  -> Madera
  Escudo_Cuero  : 12 paneles frontales (escamas por normal map)  -> Cuero
  Escudo_Bronce : reborde, 12 radios, medallon solar, adornos    -> Bronce
  Escudo_Acero  : remaches y anillo fino                         -> Acero"""
import bpy, bmesh, math, os
from mathutils import Vector

SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
TEX = os.path.join(SRC, "tex")
OUT = os.path.join(ROOT, "assets", "shield.glb")

bpy.ops.wm.read_factory_settings(use_empty=True)

R = 0.5          # radio del escudo
HT = 0.015       # semi-grosor de la madera
N = 72           # segmentos angulares


def surf(r):
    """Superficie media: ligera cupula."""
    return 0.05 * (1 - (r / R) ** 2)


def zt(r):
    return surf(r) + HT      # cara frontal de la madera


class Mesh:
    def __init__(self, name):
        self.name, self.bm = name, bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def v(self, x, y, z):
        return self.bm.verts.new((x, y, z))

    def face(self, verts, uvfn, ref):
        """Crea la cara, asigna UV (uvfn(vertex, indice) -> (u,v)) y la orienta lejos de `ref`."""
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


# ---------------------------------------------------------------- 1. Madera (trasera, disco)
def build_wood():
    m = Mesh("Escudo_Madera")
    RB = 5
    planar = lambda p, k: (p.x / (2 * R) + .5, p.y / (2 * R) + .5)
    cf, cb = m.v(0, 0, zt(0)), m.v(0, 0, surf(0) - HT)
    ring = lambda k, s: [m.v(R * k / RB * math.cos(2 * math.pi * i / N), R * k / RB * math.sin(2 * math.pi * i / N),
                             surf(R * k / RB) + s * HT) for i in range(N)]
    F = [ring(k, 1) for k in range(1, RB + 1)]
    B = [ring(k, -1) for k in range(1, RB + 1)]
    ref = (0, 0, surf(0))
    for i in range(N):
        j = (i + 1) % N
        m.face([cf, F[0][i], F[0][j]], planar, ref)
        m.face([cb, B[0][i], B[0][j]], planar, ref)
        for k in range(RB - 1):
            m.face([F[k][i], F[k + 1][i], F[k + 1][j], F[k][j]], planar, ref)
            m.face([B[k][i], B[k + 1][i], B[k + 1][j], B[k][j]], planar, ref)
        m.face([F[-1][i], B[-1][i], B[-1][j], F[-1][j]], planar, ref)   # canto (queda bajo el reborde)
    return m.build()


# ---------------------------------------------------------------- 2. Cuero: 12 paneles radiales
def build_leather():
    m = Mesh("Escudo_Cuero")
    r0, r1, gap, th, NR, NT = 0.25, 0.43, 0.032, 0.014, 4, 4
    for p in range(12):
        ta = math.radians(30 * p)
        phi = ta + math.radians(15)
        ca, sa = math.cos(phi), math.sin(phi)

        def uvf(q, k, ca=ca, sa=sa):
            s, xp = q.x * ca + q.y * sa, -q.x * sa + q.y * ca
            return (.5 + xp / .80, s / .80)       # patron repetible (REPEAT); celda de escama ~5 cm

        top, bot = [], []
        for ir in range(NR + 1):
            r = r0 + (r1 - r0) * ir / NR
            d = math.asin(gap / r)
            rt, rb = [], []
            for it in range(NT + 1):
                a = ta + d + (math.radians(30) - 2 * d) * it / NT
                x, y = r * math.cos(a), r * math.sin(a)
                rt.append(m.v(x, y, zt(r) + th))
                rb.append(m.v(x, y, zt(r) - .002))
            top.append(rt); bot.append(rb)
        ref = (.34 * ca, .34 * sa, 0)
        for ir in range(NR):
            for it in range(NT):
                m.face([top[ir][it], top[ir + 1][it], top[ir + 1][it + 1], top[ir][it + 1]], uvf, ref)
        for it in range(NT):      # paredes inicial / final (radial)
            m.face([top[0][it], top[0][it + 1], bot[0][it + 1], bot[0][it]], uvf, ref)
            m.face([top[NR][it], top[NR][it + 1], bot[NR][it + 1], bot[NR][it]], uvf, ref)
        for ir in range(NR):      # paredes laterales
            for t in (0, NT):
                m.face([top[ir][t], top[ir + 1][t], bot[ir + 1][t], bot[ir][t]], uvf, ref)
    return m.build()


# ---------------------------------------------------------------- 3. Bronce
def build_bronze():
    m = Mesh("Escudo_Bronce")
    # 3a. reborde: perfil cerrado barrido alrededor del circulo (UV: u = vuelta completa, v = franja superior del atlas)
    prof = [(-.065, .032), (-.045, .052), (-.005, .060), (.025, .045), (.030, .0), (.025, -.030), (-.005, -.040), (-.045, -.034)]
    P = len(prof)
    rings = []
    for i in range(N):
        a = 2 * math.pi * i / N
        c, s = math.cos(a), math.sin(a)
        rings.append([m.v((R + d) * c, (R + d) * s, h) for d, h in prof])
    for i in range(N):
        j = (i + 1) % N
        cen = Vector((sum(v.co.x for v in rings[i]), sum(v.co.y for v in rings[i]), sum(v.co.z for v in rings[i]))) / P
        for k in range(P):
            q = (k + 1) % P
            vk, vq = .995 - .09 * k / P, .995 - .09 * (k + 1) / P
            uvs = [(i / N, vk), ((i + 1) / N, vk), ((i + 1) / N, vq), (i / N, vq)]
            m.face([rings[i][k], rings[j][k], rings[j][q], rings[i][q]], uvs, cen)

    # 3b. 12 radios arqueados (seccion trapezoidal, region compartida del atlas)
    L0, L1, SEG = 0.20, 0.44, 6
    for p in range(12):
        th = math.radians(30 * p)
        c, s = math.cos(th), math.sin(th)
        pc, ps = -s, c
        st = []
        for i in range(SEG + 1):
            r = L0 + (L1 - L0) * i / SEG
            zb = zt(r) - .002
            pts = []
            for (w, h) in ((-.028, 0), (-.022, .026), (.022, .026), (.028, 0)):
                pts.append((m.v(r * c + pc * w, r * s + ps * w, zb + h), .05 + w / .056 * .10, (r - L0) / (L1 - L0) * .87))
            st.append(pts)
        for i in range(SEG):
            ref = ((L0 + (L1 - L0) * i / SEG) * c, (L0 + (L1 - L0) * i / SEG) * s, -.05)
            for k in range(3):
                a, b = st[i][k], st[i][k + 1]
                a2, b2 = st[i + 1][k], st[i + 1][k + 1]
                m.face([a[0], b[0], b2[0], a2[0]], [(a[1], a[2]), (b[1], b[2]), (b2[1], b2[2]), (a2[1], a2[2])], ref)

    # 3c. medallon solar: superficie de revolucion (decal planar frontal en el atlas)
    base = zt(0)
    prof2 = [(0, .085), (.03, .083), (.07, .075), (.11, .062), (.145, .045), (.162, .035), (.164, .028),
             (.178, .028), (.18, .018), (.215, .018), (.217, .008), (.22, 0)]
    SB = 48
    dec = lambda p, k: (.12 + (p.x / .44 + .5) * .5, (p.y / .44 + .5) * .5)
    lat = [[m.v(r * math.cos(2 * math.pi * i / SB), r * math.sin(2 * math.pi * i / SB), base + h) for i in range(SB)]
           if r > 0 else [m.v(0, 0, base + h)] for r, h in prof2]
    for k in range(len(prof2) - 1):
        for i in range(SB):
            j = (i + 1) % SB
            if k == 0:
                m.face([lat[0][0], lat[1][i], lat[1][j]], dec, (0, 0, base - .1))
            else:
                m.face([lat[k][i], lat[k + 1][i], lat[k + 1][j], lat[k][j]], dec, (0, 0, base - .1))

    # 3d. adornos curvos simetricos (superior e inferior, rotados 180 grados) + bulbo
    def claw(bottom):
        def pos(x, y, z):
            return (-x, -y, z) if bottom else (x, y, z)

        def uvf(q, k):
            x, y = (-q.x, -q.y) if bottom else (q.x, q.y)
            v = (y + .8) / .4 * .42 if bottom else .45 + (y - .4) / .45 * .42
            return (.64 + (x + .15) / .30 * .35, v)
        z0 = surf(.46) + HT + .035
        prongs = [((0, .47), (0, .54), (0, .61), (0, .72)),
                  ((0, .50), (-.08, .54), (-.12, .60), (-.06, .69)),
                  ((0, .50), (.08, .54), (.12, .60), (.06, .69))]
        for P0, P1, P2, P3 in prongs:
            rg, T = [], 10
            for t_i in range(T + 1):
                t = t_i / T
                b = [(1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t ** 2 * (1 - t), t ** 3]
                x = sum(b[q] * pt[0] for q, pt in enumerate((P0, P1, P2, P3)))
                y = sum(b[q] * pt[1] for q, pt in enumerate((P0, P1, P2, P3)))
                dx = 3 * ((1 - t) ** 2 * (P1[0] - P0[0]) + 2 * t * (1 - t) * (P2[0] - P1[0]) + t ** 2 * (P3[0] - P2[0]))
                dy = 3 * ((1 - t) ** 2 * (P1[1] - P0[1]) + 2 * t * (1 - t) * (P2[1] - P1[1]) + t ** 2 * (P3[1] - P2[1]))
                Tn = Vector((dx, dy, .04)).normalized()
                n1 = Tn.cross(Vector((0, 0, 1))).normalized()
                n2 = Tn.cross(n1).normalized()
                rad = .036 * (1 - t) ** .8 + .006
                ctr = Vector((x, y, z0 + .03 * t))
                ring_ = []
                for sd in range(6):
                    ang = 2 * math.pi * sd / 6
                    q = ctr + (n1 * math.cos(ang) + n2 * math.sin(ang)) * rad
                    ring_.append(m.v(*pos(q.x, q.y, q.z)))
                rg.append((ring_, pos(*ctr)))
            for t_i in range(T):
                for sd in range(6):
                    q = (sd + 1) % 6
                    m.face([rg[t_i][0][sd], rg[t_i][0][q], rg[t_i + 1][0][q], rg[t_i + 1][0][sd]], uvf, rg[t_i][1])
        # bulbo de base
        res = bmesh.ops.create_uvsphere(m.bm, u_segments=12, v_segments=5, radius=.05)
        bmesh.ops.scale(m.bm, vec=(1, 1, .7), verts=res["verts"])
        bmesh.ops.translate(m.bm, vec=pos(0, .485, z0 + .005), verts=res["verts"])
        bmesh.ops.delete(m.bm, geom=[v for v in res["verts"] if v.co.z < z0 + .005 - 1e-4], context="VERTS")
        bc = Vector(pos(0, .485, z0 + .005))
        for f in m.bm.faces:
            if (f.calc_center_median() - bc).length < .06:
                for l in f.loops:
                    l[m.uv].uv = uvf(l.vert.co, 0)
    claw(False)
    claw(True)
    return m.build()


# ---------------------------------------------------------------- 4. Acero: remaches + anillo fino
def build_steel():
    m = Mesh("Escudo_Acero")

    def rivet(x, y, z, r=.014):
        res = bmesh.ops.create_uvsphere(m.bm, u_segments=8, v_segments=4, radius=r)
        bmesh.ops.scale(m.bm, vec=(1, 1, .65), verts=res["verts"])
        bmesh.ops.translate(m.bm, vec=(x, y, z), verts=res["verts"])
        bmesh.ops.delete(m.bm, geom=[v for v in res["verts"] if v.co.z < z - 1e-4], context="VERTS")
    for i in range(24):                    # remaches sobre el reborde
        a = 2 * math.pi * (i + .5) / 24
        rivet((R - .025) * math.cos(a), (R - .025) * math.sin(a), .057)
    for p in range(12):                    # un remache por radio
        a = math.radians(30 * p)
        r = .335
        rivet(r * math.cos(a), r * math.sin(a), zt(r) + .026 + .002)
    # anillo fino alrededor del medallon (perfil 4 puntos, revolucion)
    pr = [(.225, 0), (.228, .010), (.242, .010), (.245, 0)]
    ring = [[m.v(r * math.cos(2 * math.pi * i / 48), r * math.sin(2 * math.pi * i / 48), zt(r) - .002 + h)
             for i in range(48)] for r, h in pr]
    for k in range(3):
        for i in range(48):
            j = (i + 1) % 48
            m.face([ring[k][i], ring[k + 1][i], ring[k + 1][j], ring[k][j]], [(0, 0)] * 4, (0, 0, -.1))
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


body, leather, bronze, steel = build_wood(), build_leather(), build_bronze(), build_steel()
objs = [body, leather, bronze, steel]

# UVs del acero (piezas pequenas): smart project + empaquetado
bpy.context.view_layer.objects.active = steel
steel.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.004)
bpy.ops.uv.pack_islands(margin=.004)
bpy.ops.object.mode_set(mode="OBJECT")
steel.select_set(False)

for ob, (nm, key) in zip(objs, (("Madera", "madera"), ("Cuero", "cuero"), ("Bronce", "bronce_envejecido"), ("Acero", "acero"))):
    ob.data.materials.append(make_mat(nm, key))
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.mesh.delete_loose()
    bpy.ops.object.mode_set(mode="OBJECT")
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(50))
    except Exception:
        bpy.ops.object.shade_smooth()
    ob.select_set(False)

# Orientacion: modelado con +Z al frente; se gira 90 grados en X y se aplica para que en glTF quede de pie, mirando a +Z
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
                          export_apply=True, export_image_format="JPEG", export_jpeg_quality=85, export_materials="EXPORT",
                          export_texcoords=True, export_normals=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SRC, "escudo.blend"))
print("EXPORTADO", OUT, os.path.getsize(OUT))
