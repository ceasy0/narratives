"""Look test of the leaf shot (SH1250): the layout taken from grey to the final look.

    blender -b --factory-startup -P lookdev_leaf.py               three stills, 1920x1080
    blender -b --factory-startup -P lookdev_leaf.py -- clip       and the clip, 04:00:12-04:04:12, 1280x720
    blender -b --factory-startup -P lookdev_leaf.py -- nocloth    the leaf without the cloth simulation

It opens the layout (work/layout/b12-13-layout.blend: run layout_b12_13.py first) and keeps its
camera, the leaf's path and the trees, so the look test is the layout's own shot. Everything
else is swapped: the grey stand-ins go, and in come real materials, a low sun with haze in the
air, ferns, a rebuilt trunk for the tree, and a leaf with a real outline that is a cloth
simulation pinned along its midrib, so it bends and flutters as it falls. EEVEE, which is what
most of the Opening renders in (PLAN §2). Writes work/lookdev/.
"""
import math
import random
import sys
import pathlib

import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CLIP, CLOTH = "clip" in ARGS, "nocloth" not in ARGS
random.seed(7)

T0 = O.frame("04:06")                      # the first footfall (the layout's t = 0)
LEAF_LOOSE = O.frame("03:58")              # the leaf starts to tremble on its stem
STILLS = ["04:01:16", "04:02:06", "04:03:12"]   # just in frame; mid-fall in front of the stump; landed
CLIP_RANGE = (O.frame("04:00:12"), O.frame("04:04:12"))
OUT = O.WORK / "lookdev"

bpy.ops.wm.open_mainfile(filepath=str(O.LAYOUT / "b12-13-layout.blend"))
scene = bpy.context.scene
col = scene.collection
cam = bpy.data.objects["CAM unbroken"]
scene.camera = cam
for m in list(scene.timeline_markers):      # one camera only: the layout's markers switch cameras
    scene.timeline_markers.remove(m)
CAM = cam.matrix_world.translation.copy()
scene.frame_set(T0)
CAM = cam.matrix_world.translation.copy()
leaf = bpy.data.objects["Leaf"]
hero = bpy.data.objects["The tree"]
SKULL = hero.location.copy()
LEAF_AT = Vector((CAM.x + 1.6, CAM.y, 0.0))     # where the leaf lands (the layout's numbers)

# ---------------------------------------------------------------- clear the stand-ins
keep = ("Ground", "Tree", "The tree", "Leaf", "CAM ")
for ob in list(bpy.data.objects):
    if ob.name == "Ground cover" or ob.name.startswith("Ground cover") or not ob.name.startswith(keep):
        bpy.data.objects.remove(ob, do_unlink=True)


# ---------------------------------------------------------------- materials
def material(name, build):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    build(nt, out)
    return m


def noise(nt, scale, detail=6.0, coord="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs[coord], n.inputs["Vector"])
    return n


def ramp(nt, src, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, c in stops[1:-1]:
        e = els.new(pos)
        e.color = (*c, 1)
    nt.links.new(src, r.inputs["Fac"])
    return r


def bump(nt, src, strength, bsdf):
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    nt.links.new(src, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])


def leafy(nt, out, color, translucency, rough=0.55):
    """A green thing lit from both sides: Principled mixed with Translucent, so it glows against the sun."""
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Roughness"].default_value = rough
    t = nt.nodes.new("ShaderNodeBsdfTranslucent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = translucency
    n = noise(nt, 6.0, 4.0)
    c = ramp(nt, n.outputs["Fac"], [(0.3, [v * 0.75 for v in color]), (0.7, [min(1, v * 1.2) for v in color])])
    nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(c.outputs["Color"], t.inputs["Color"])
    nt.links.new(p.outputs[0], mix.inputs[1])
    nt.links.new(t.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return p


def build_ground(nt, out):
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Roughness"].default_value = 0.92
    big = noise(nt, 0.6, 3.0)
    small = noise(nt, 30.0, 8.0)
    c = ramp(nt, big.outputs["Fac"], [(0.35, (0.12, 0.07, 0.035)), (0.5, (0.26, 0.16, 0.08)),
                                      (0.62, (0.17, 0.14, 0.05)), (0.75, (0.32, 0.2, 0.1))])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = 'RGBA', 'MULTIPLY'
    mix.inputs[0].default_value = 0.25
    a, b = [i for i in mix.inputs if i.type == 'RGBA'][:2]
    nt.links.new(c.outputs["Color"], a)
    nt.links.new(small.outputs["Color"], b)
    nt.links.new([o for o in mix.outputs if o.type == 'RGBA'][0], p.inputs["Base Color"])
    bump(nt, small.outputs["Fac"], 1.0, p)
    nt.links.new(p.outputs[0], out.inputs["Surface"])


def build_bark(nt, out):
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Roughness"].default_value = 0.85
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeMapping")
    sep.inputs["Scale"].default_value = (6.0, 6.0, 0.8)          # fissures run up the trunk
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    v = nt.nodes.new("ShaderNodeTexVoronoi")
    v.feature = 'DISTANCE_TO_EDGE'
    v.inputs["Scale"].default_value = 6.0
    nt.links.new(sep.outputs["Vector"], v.inputs["Vector"])
    n = noise(nt, 20.0, 6.0)
    c = ramp(nt, n.outputs["Fac"], [(0.3, (0.045, 0.035, 0.028)), (0.7, (0.15, 0.115, 0.085))])
    nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
    bump(nt, v.outputs["Distance"], 1.0, p)
    nt.links.new(p.outputs[0], out.inputs["Surface"])


GROUND = material("Forest floor", build_ground)
BARK = material("Bark", build_bark)
CROWN = material("Crown", lambda nt, out: leafy(nt, out, (0.045, 0.1, 0.025), 0.25, 0.7))
FERN = material("Fern", lambda nt, out: leafy(nt, out, (0.07, 0.17, 0.03), 0.45))
LEAF = material("Leaf", lambda nt, out: leafy(nt, out, (0.42, 0.4, 0.06), 0.55, 0.45))
LITTER = material("Leaf litter", lambda nt, out: leafy(nt, out, (0.2, 0.11, 0.045), 0.2, 0.75))


def assign(ob, *mats):
    ob.data.materials.clear()
    for m in mats:
        ob.data.materials.append(m)


# ---------------------------------------------------------------- trees: smooth, barked, leafy
def tree_split(ob):
    """The layout's trees are a trunk and a crown in one mesh: crown faces (above 0.55 h) get material 2."""
    me = ob.data
    assign(ob, BARK, CROWN)
    zs = [v.co.z for v in me.vertices]
    h = max(zs) if zs else 1
    for p in me.polygons:
        p.use_smooth = True
        p.material_index = 1 if p.center.z > 0.5 * h else 0


for ob in bpy.data.objects:
    if ob.type == 'MESH' and ob.name.startswith("Tree"):
        tree_split(ob)


def hero_mesh():
    """The tree where the head lay, rebuilt finer: a flared, tapering trunk in 24 sides, the low
    branch over the lane, and a crown; same height and branch as the layout's."""
    h = 8.0
    bm = bmesh.new()
    rings = []
    for k in range(13):
        z = h * 0.72 * (k / 12) ** 1.2
        r = 0.18 + 0.12 * (1 - k / 12) + 0.22 * math.exp(-z / 0.25)        # taper, and a root flare
        ring = []
        for j in range(24):
            a = 2 * math.pi * j / 24
            wob = 1 + 0.06 * math.sin(3 * a + k) + 0.04 * math.sin(7 * a)    # not a perfect cylinder
            ring.append(bm.verts.new((r * wob * math.cos(a), r * wob * math.sin(a), z)))
        rings.append(ring)
    for ra, rb in zip(rings, rings[1:]):
        for j in range(24):
            bm.faces.new((ra[j], ra[(j + 1) % 24], rb[(j + 1) % 24], rb[j]))
    bm.faces.new(list(reversed(rings[0])))
    tip = Vector((LEAF_AT.x, LEAF_AT.y, 3.0)) - SKULL
    fork = Vector((0, 0, 2.3))
    reach = tip + Vector((0, 0, 0.12)) - fork
    m = Matrix.Translation(fork) @ reach.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Translation((0, 0, reach.length / 2))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.09, radius2=0.03, depth=reach.length, matrix=m)
    for f in bm.faces:
        f.material_index = 0                                                 # trunk and branch: bark
    for c, s in ((Vector((0, 0, h * 0.8)), (h * 0.26, h * 0.26, h * 0.2)), (tip + Vector((0, 0, 0.3)), (0.6, 0.6, 0.35))):
        made = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal(Vector(s).to_4d()))
        for v in made["verts"]:
            for f in v.link_faces:
                f.material_index = 1                                         # crowns: leaves
    me = bpy.data.meshes.new("The tree, fine")
    bm.to_mesh(me)
    bm.free()
    return me


old = hero.data
hero.data = hero_mesh()
bpy.data.meshes.remove(old)
assign(hero, BARK, CROWN)
for p in hero.data.polygons:
    p.use_smooth = True

assign(bpy.data.objects["Ground"], GROUND)


# ---------------------------------------------------------------- ferns
def frond(bm, base, yaw, length, lift, droop):
    """One fern frond: a thin rachis arching out and down, with separate leaflets (pinnae) in
    pairs along it, longest in the middle, so it reads as a fern, not a leaf."""
    rot = Matrix.Rotation(yaw, 3, 'Z')

    def at(s):
        return Vector((length * s, 0, length * (lift * math.sin(math.pi * 0.55 * s) - droop * s * s)))

    n = 18
    for i in range(n):                                           # the rachis, a thin strip
        p0, p1 = at(i / n), at((i + 1) / n)
        w = 0.004
        q = [base + rot @ (p0 + Vector((0, -w, 0))), base + rot @ (p0 + Vector((0, w, 0))),
             base + rot @ (p1 + Vector((0, w, 0))), base + rot @ (p1 + Vector((0, -w, 0)))]
        bm.faces.new([bm.verts.new(v) for v in q])
    pairs = 16
    for i in range(pairs):
        s = 0.1 + 0.88 * i / (pairs - 1)
        w = 0.3 * length * math.sin(math.pi * min(1.0, s * 1.1)) ** 0.6 * (1 - 0.35 * s)
        step = length * 0.88 / pairs
        c = at(s)
        for side in (-1, 1):
            tip = c + Vector((0.35 * w, side * w, -0.25 * w))
            q = [base + rot @ (c + Vector((-0.42 * step, 0, 0))), base + rot @ (c + Vector((0.42 * step, 0, 0))),
                 base + rot @ (tip + Vector((0.12 * step, 0, 0))), base + rot @ (tip + Vector((-0.12 * step, 0, 0)))]
            bm.faces.new([bm.verts.new(v) for v in q])


def fern_variant(k):
    rng = random.Random(100 + k)
    bm = bmesh.new()
    count = rng.randint(6, 9)
    for i in range(count):
        frond(bm, Vector((0, 0, 0.02)), 2 * math.pi * i / count + rng.uniform(-0.3, 0.3),
              rng.uniform(0.45, 0.75), rng.uniform(0.5, 0.8), rng.uniform(0.2, 0.45))
    me = bpy.data.meshes.new("Fern %d" % k)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(FERN)
    return me


variants = [fern_variant(k) for k in range(6)]
placed = 0
for _ in range(9000):
    x, y = CAM.x + random.uniform(0.6, 45.0), CAM.y + random.uniform(-30, 30)
    if abs(y - CAM.y) > (x - CAM.x) * 0.95 + 1.5:             # outside the frame: skip
        continue
    if x < SKULL.x + 0.6 and abs(y - CAM.y) < 1.1:             # the view to the stump and the leaf stays open
        continue
    if (Vector((x, y)) - SKULL.xy).length < 0.6:
        continue
    near = (x - CAM.x) < 6
    if near and random.random() < 0.5:
        continue
    ob = bpy.data.objects.new("Fern", random.choice(variants))
    ob.location = (x, y, 0)
    ob.rotation_euler = (0, 0, random.uniform(0, 2 * math.pi))
    s = random.uniform(0.7, 1.3)
    ob.scale = (s, s, s)
    col.objects.link(ob)
    placed += 1
    if placed >= 900:
        break
print("ferns", placed)

# Understory: low shrubs and saplings through the forest, so the eye doesn't run out to a bare horizon.
shrub_bm = bmesh.new()
for _ in range(1600):
    x, y = CAM.x + random.uniform(9, 110), CAM.y + random.uniform(-90, 90)
    if abs(y - CAM.y) > (x - CAM.x) * 0.95 + 2:
        continue
    r_ = random.uniform(0.5, 1.4)
    bmesh.ops.create_icosphere(shrub_bm, subdivisions=2, radius=1.0,
                               matrix=Matrix.Translation((x, y, r_ * 0.55)) @ Matrix.Diagonal((r_ * random.uniform(0.9, 1.6), r_, r_ * 0.8, 1)))
shrubs_me = bpy.data.meshes.new("Understory")
shrub_bm.to_mesh(shrubs_me)
shrub_bm.free()
for p in shrubs_me.polygons:
    p.use_smooth = True
shrubs = bpy.data.objects.new("Understory", shrubs_me)
shrubs.data.materials.append(CROWN)
col.objects.link(shrubs)

# Leaf litter on the forest floor near the camera: old leaves, brown, curled, every way up.
lit = bmesh.new()
for _ in range(22000):
    x, y = CAM.x + random.uniform(0.5, 12), CAM.y + random.uniform(-8, 8)
    if abs(y - CAM.y) > (x - CAM.x) * 0.95 + 0.8:
        continue
    L, W, a = random.uniform(0.05, 0.11), random.uniform(0.02, 0.04), random.uniform(0, 2 * math.pi)
    m = Matrix.Translation((x, y, 0.004)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(random.uniform(-0.3, 0.3), 4, 'X')
    q = [lit.verts.new(m @ Vector(v)) for v in ((-L / 2, 0, 0.003), (0, -W / 2, 0.0), (L / 2, 0, 0.004), (0, W / 2, 0.0))]
    lit.faces.new(q)
litter_me = bpy.data.meshes.new("Leaf litter")
lit.to_mesh(litter_me)
lit.free()
litter = bpy.data.objects.new("Leaf litter", litter_me)
litter.data.materials.append(LITTER)
col.objects.link(litter)


# ---------------------------------------------------------------- the leaf, as cloth
def leaf_mesh():
    """A leaf 12 cm long along X: a pointed oval with a short stem, a midrib, and its halves cupped."""
    bm = bmesh.new()
    nu, nv = 24, 8
    grid = []
    for i in range(nu + 1):
        u = i / nu
        half = 0.036 * math.sin(math.pi * u ** 0.85) ** 0.85
        row = []
        for j in range(nv + 1):
            v = -1 + 2 * j / nv
            z = 0.008 * v * v - 0.002 * (1 - abs(v)) + 0.006 * (u - 0.5) ** 2
            row.append(bm.verts.new(((u - 0.5) * 0.12, v * max(half, 0.0008), z)))
        grid.append(row)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    stem = [bm.verts.new((-0.06 - 0.018 * s, 0.0004 * (1 - s), -0.002 * s)) for s in (0.0, 1.0)]
    stem2 = [bm.verts.new((-0.06 - 0.018 * s, -0.0004 * (1 - s) - 0.0006, -0.002 * s)) for s in (0.0, 1.0)]
    bm.faces.new((stem[0], stem[1], stem2[1], stem2[0]))
    me = bpy.data.meshes.new("Leaf, fine")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me, nu, nv


old = leaf.data
me, nu, nv = leaf_mesh()
leaf.data = me
bpy.data.meshes.remove(old)
assign(leaf, LEAF)
leaf.color = (1, 1, 1, 1)
if CLOTH:
    pin = leaf.vertex_groups.new(name="midrib")
    for vtx in me.vertices:
        u = (vtx.co.x + 0.06) / 0.12
        w = max(0.0, 1.0 - abs(vtx.co.y) / 0.012)                         # the midrib holds the shape
        pin.add([vtx.index], max(w, 1.0 if u < 0.05 else 0.0), 'REPLACE')
    cl = leaf.modifiers.new("Cloth", 'CLOTH')
    st = cl.settings
    st.quality = 12
    st.mass = 0.0004
    st.air_damping = 6.0
    st.tension_stiffness = st.compression_stiffness = 20.0
    st.shear_stiffness = 10.0
    st.bending_stiffness = 0.6
    st.vertex_group_mass = "midrib"
    st.pin_stiffness = 2.0
    st.effector_weights.gravity = 0.0                               # the fall is the keyed path; the cloth is the flutter
    cache = cl.point_cache
    cache.frame_start, cache.frame_end = LEAF_LOOSE, T0 + 2


# ---------------------------------------------------------------- light and air
world = scene.world
world.use_nodes = True
wn = world.node_tree
for n in list(wn.nodes):
    wn.nodes.remove(n)
wout = wn.nodes.new("ShaderNodeOutputWorld")
sky = wn.nodes.new("ShaderNodeTexSky")
sky.sky_type = 'MULTIPLE_SCATTERING'
SUN_EL, SUN_AZ = math.radians(38), math.radians(60)                # from ahead and to the left, high enough to reach the clearing
sky.sun_elevation = SUN_EL
sky.sun_rotation = SUN_AZ - math.pi / 2
sky.sun_disc = False
bg = wn.nodes.new("ShaderNodeBackground")
bg.inputs["Strength"].default_value = 0.2
wn.links.new(sky.outputs["Color"], bg.inputs["Color"])
wn.links.new(bg.outputs[0], wout.inputs["Surface"])
# Morning haze, so the sun's shafts show between the trunks: a volume in a box round the scene
# (a world volume in EEVEE is endless and swallows the sky's light).
def build_haze(nt, out):
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = 0.004
    v.inputs["Anisotropy"].default_value = 0.45
    v.inputs["Color"].default_value = (0.9, 0.92, 1.0, 1)
    nt.links.new(v.outputs[0], out.inputs["Volume"])


HAZE = material("Haze", build_haze)
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((CAM.x + 60, CAM.y, 15)) @ Matrix.Diagonal((150, 170, 30, 1)))
hz = bpy.data.meshes.new("Haze")
bm.to_mesh(hz)
bm.free()
haze = bpy.data.objects.new("Haze", hz)
assign(haze, HAZE)
col.objects.link(haze)

sun_dir = Vector((math.cos(SUN_EL) * math.cos(SUN_AZ), math.cos(SUN_EL) * math.sin(SUN_AZ), math.sin(SUN_EL)))
sd = bpy.data.lights.new("Sun", 'SUN')
sd.energy = 6.0
sd.angle = math.radians(1.2)
sd.color = (1.0, 0.92, 0.8)
sun = bpy.data.objects.new("Sun", sd)
sun.rotation_euler = sun_dir.to_track_quat('Z', 'Y').to_euler()
col.objects.link(sun)

# ---------------------------------------------------------------- camera and render
cd = cam.data
cd.dof.use_dof = True
cd.dof.focus_object = leaf
cd.dof.aperture_fstop = 4.0
r = scene.render
r.engine = 'BLENDER_EEVEE'
r.use_stamp = False
r.film_transparent = False
e = scene.eevee
e.use_raytracing = True
e.use_shadows = True
e.use_volumetric_shadows = True
e.volumetric_tile_size = '4'
e.volumetric_end = 80.0
e.use_fast_gi = True
scene.view_settings.view_transform = 'AgX'
for look in ('AgX - Punchy', 'AgX - Medium High Contrast', 'None'):
    try:
        scene.view_settings.look = look
        break
    except TypeError:
        continue
print("look", scene.view_settings.look)
scene.view_settings.exposure = 0.0

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "leaf-lookdev.blend"))
print("saved", OUT / "leaf-lookdev.blend")


_at = [LEAF_LOOSE - 1]


def advance_to(f):
    """The cloth is a simulation: step through every frame from its start, in order."""
    if f < _at[0]:
        _at[0] = LEAF_LOOSE - 1
    for k in range(max(_at[0] + 1, LEAF_LOOSE - 1), f + 1):
        scene.frame_set(k)
    _at[0] = f


# stills, at full size
r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
e.taa_render_samples = 96
r.use_motion_blur = False
r.image_settings.media_type = 'IMAGE'
r.image_settings.file_format = 'PNG'
for tc in STILLS:
    advance_to(O.frame(tc))
    r.filepath = str(OUT / ("leaf-" + tc.replace(":", "") + ".png"))
    bpy.ops.render.render(write_still=True)
    print("still", r.filepath)

if CLIP:
    r.resolution_x, r.resolution_y = 1280, 720
    e.taa_render_samples = 48
    r.use_motion_blur = True
    r.motion_blur_shutter = 0.5
    scene.frame_start, scene.frame_end = CLIP_RANGE[0], CLIP_RANGE[1] - 1
    advance_to(CLIP_RANGE[0] - 1)
    r.image_settings.media_type = 'VIDEO'
    r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format, r.ffmpeg.codec = 'MPEG4', 'H264'
    r.ffmpeg.constant_rate_factor = 'HIGH'
    r.filepath = str(OUT / "leaf-lookdev.mp4")
    bpy.ops.render.render(animation=True)
    print("clip", r.filepath)
