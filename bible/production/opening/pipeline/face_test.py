"""The face in the series' painted look: one head, close, one expression (the style test, PLAN §9,
item 3; Discussion 006, round 4).

    blender -b --factory-startup -P face_test.py               bake, paint, render: stills, clip, sheet
    blender -b --factory-startup -P face_test.py -- still      the two stills only
    blender -b --factory-startup -P face_test.py -- reuse      the paint already made (work/styletest/paint/)
    blender -b --factory-startup -P face_test.py -- check      grey front and side views, to set the shape

The head is MPFB2's, shaped after Corbin's photos (work/face/, out of git) with its own sliders
(FACE below): long and lean, a narrow head, high cheekbones over hollow cheeks, a low straight
brow, deep-set eyes, a long straight nose, a full lower lip, a firm square jaw and chin, a long
neck. Then its forms are given more definition (your note, 2026-10-15: the models should have
it, not the shadows or the lines): the head is pushed away from a smoothed copy of itself, so its
ridges and hollows stand out (DEFINE). The hair is sculpted in locks, as Arcane's is: dark brown,
parted on his left, swept across the forehead and down to the jaw, as in the photos (hair()).
It's a likeness to judge the look by, not the design of the recurring face, which comes after
(PLAN §5). The eyes stay closed, as in the photos and as the Opening's face first is. The
expression is the Opening's last, which you've called right for it: one breath drawn in (05:00),
the nostrils widening, the lips parting a little, the chin lifting.

It's painted with real brush strokes (your note, 2026-10-15: genuinely painted, the shadows
painted on and soft): Blender bakes each surface's colour and the light that reaches it into the
surface's own texture (Cycles), brush.py paints that over with strokes that follow the form, big
brushes then small, and the camera sees the paint as it is. The light is fixed in the paint, as
a painter fixes it: a warm key high in front and across the nose, a cool fill, a rim from behind.
No outline. Against a dark, cool backdrop.

Writes work/styletest/face-neutral.png, face-breath.png, face-breath.mp4 and face-sheet.png, and
the paint in work/styletest/paint/.
"""
import importlib
import json
import math
import pathlib
import random
import subprocess
import sys
import time

import bpy
import numpy as np
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402
import humans as H  # noqa: E402
import painted as P  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STILL, CHECK, REUSE = "still" in ARGS, "check" in ARGS, "reuse" in ARGS
OUT = O.WORK / "styletest"
PAINT = OUT / "paint"
BRUSH = pathlib.Path(__file__).resolve().parent / "brush.py"
FPS = O.FPS
F0, BREATH, F1 = 1, (30, 66), 96                  # still, then one breath in over 1.5 s, held
SKIN_RES, HAIR_RES = 4096, 2048

# The head after the photos: MPFB target -> weight (0-1; each target is one side of a slider).
FACE = {"head-oval": 0.6, "head-scale-horiz-decr": 0.3, "head-scale-vert-incr": 0.2,
        "forehead-scale-vert-incr": 0.15,
        "eyebrows-trans-down": 0.1, "eyebrows-angle-down": 0.15,
        "l-eye-push1-in": 0.1, "r-eye-push1-in": 0.1,
        "nose-scale-vert-incr": 0.35, "nose-scale-depth-incr": 0.25, "nose-hump-decr": 0.25,
        "nose-point-up": 0.15, "nose-point-width-decr": 0.2,
        "mouth-lowerlip-volume-incr": 0.2, "mouth-cupidsbow-incr": 0.3, "mouth-upperlip-volume-decr": 0.05,
        "chin-prominent-incr": 0.5, "chin-height-incr": 0.25, "chin-width-incr": 0.2, "chin-bones-incr": 0.35,
        "l-cheek-bones-incr": 0.4, "r-cheek-bones-incr": 0.4,
        "l-cheek-volume-decr": 0.45, "r-cheek-volume-decr": 0.45,
        "l-cheek-inner-decr": 0.25, "r-cheek-inner-decr": 0.25,
        "neck-scale-vert-incr": 0.25, "neck-scale-horiz-decr": 0.15}
CLOSED = {"eye-left-closure": 1.0, "eye-right-closure": 1.0}       # baked in: the eyes stay shut
BREATH_IN = {"nose-left-dilatation": 0.8, "nose-right-dilatation": 0.8, "mouth-open": 0.09}
LIFT = {"Neck1": -4.0, "Head": -5.0}              # degrees about each bone's x: the chin up
DEFINE = (0.25, 10)                                # how far the forms are pushed from their smoothed copy; how smooth
BROWS, LASHES = "eyebrow012", "eyelashes01"

t_start = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
HS, TS = H.mpfb()
SYSTEM = pathlib.Path(importlib.import_module(H.MPFB).__file__).parent / "data" / "targets"

md = TS.get_default_macro_info_dict()
md.update({"gender": 1.0, "age": 0.42, "muscle": 0.5, "weight": 0.36, "proportions": 0.6, "height": 0.6})   # about 21
md["race"] = {"african": 0.0, "asian": 0.0, "caucasian": 1.0}
human = HS.create_human(mask_helpers=True, macro_detail_dict=md)
for t, w in FACE.items():
    TS.load_target(human, TS.target_full_path(t), weight=w, name=t)
for t, w in CLOSED.items():
    TS.load_target(human, str(SYSTEM / "expression" / "units" / "caucasian" / (t + ".target.gz")), weight=w, name=t)
TS.bake_targets(human)

sets = H.vertex_sets(human, ["helper-l-eye", "helper-r-eye", "body", "scalp"])
MW = human.matrix_world.copy()
pts = [MW @ v.co for v in human.data.vertices]
eye_ix = sets["helper-l-eye"] | sets["helper-r-eye"]
E = sum((pts[i] for i in eye_ix), Vector()) / len(eye_ix)          # between the eyes


def ramp01(a, b, x):
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


# ---------------------------------------------------------------- definition in the forms
def define(k, iters):
    """Push the head away from a smoothed copy of itself (an unsharp mask on the shape), so its
    ridges and hollows (brow, cheekbones, nose, lips, jaw) read more clearly; fading out down the
    neck, and leaving the eyes' helpers alone."""
    me = human.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    body = np.zeros(n, bool)
    body[list(sets["body"])] = True
    ed = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ed)
    ed = ed.reshape(-1, 2)
    ed = ed[body[ed[:, 0]] & body[ed[:, 1]]]
    deg = np.bincount(ed.ravel(), minlength=n).astype(float)
    sm = co.copy()
    for _ in range(iters):
        acc = np.zeros_like(sm)
        np.add.at(acc, ed[:, 0], sm[ed[:, 1]])
        np.add.at(acc, ed[:, 1], sm[ed[:, 0]])
        has = deg > 0
        sm[has] += 0.5 * (acc[has] / deg[has, None] - sm[has])
    eyes = [sum((pts[i] for i in sets[g]), Vector()) / len(sets[g]) for g in ("helper-l-eye", "helper-r-eye")]
    w = np.array([ramp01(-0.2, -0.13, (p - E).z) * min(ramp01(0.02, 0.034, (p - c).length) for c in eyes)
                  for p in pts]) * body                 # not round the eyes, where the lids would part from them
    me.vertices.foreach_set("co", (co + k * w[:, None] * (co - sm)).ravel())
    me.update()


if not CHECK or "define" in ARGS:
    define(*DEFINE)
pts = [MW @ v.co for v in human.data.vertices]

# Stubble, as in the photos: a soft mask over the jaw, the chin and the upper lip, kept off the
# lips and stopping in front of the ears, measured from the eyes.
mask = []
for p in pts:
    d = p - E
    m = ramp01(-0.045, -0.062, d.z) * ramp01(-0.15, -0.13, d.z)       # from under the nose to the jaw's edge
    m *= ramp01(0.06, 0.04, d.y)                                         # in front of the ears
    m *= 1 - ramp01(0.045, 0.06, abs(d.x)) * ramp01(-0.07, -0.04, d.z)  # up the cheeks only at the jaw
    lip = ((d.x / 0.028) ** 2 + ((d.z + 0.078) / 0.011) ** 2) ** 0.5
    m *= ramp01(0.85, 1.25, lip)                                         # not on the lips
    mask.append(m)
human.data.attributes.new("stubble", 'FLOAT', 'POINT').data.foreach_set("value", mask)
lips = [ramp01(1.15, 0.8, (((p - E).x / 0.028) ** 2 + (((p - E).z + 0.078) / 0.011) ** 2) ** 0.5) * ramp01(-0.01, -0.03, (p - E).y)
        for p in pts]                                                    # the lips, for their own colour
human.data.attributes.new("lip_tint", 'FLOAT', 'POINT').data.foreach_set("value", lips)

rig = HS.add_builtin_rig(human, "cmu_mb")
for pb in rig.pose.bones:
    pb.rotation_mode = 'XYZ'
fitted = {}                                        # fitted after the rig, so they're rigged with it
for kind, what in (("eyes", "high-poly"), ("eyebrows", BROWS), ("eyelashes", LASHES)):
    ob = HS.add_mhclo_asset(str(H.mpfb_data(kind) / what / (what + ".mhclo")), human,
                            asset_type=kind.capitalize(), subdiv_levels=0)
    fitted[kind] = ob
for t, w in BREATH_IN.items():
    TS.load_target(human, str(SYSTEM / "expression" / "units" / "caucasian" / (t + ".target.gz")), weight=0.0, name=t)
for p in human.data.polygons:
    p.use_smooth = True
sd = human.modifiers.new("Smooth", 'SUBSURF')
sd.levels, sd.render_levels = 1, 1


# ---------------------------------------------------------------- the hair, in locks
def hair(n_locks=120, seed=3):
    """Locks of hair grown over the scalp: parted on his left, those right of the part swept
    across the forehead and down past the temple, the rest falling to the jaw at the sides and the
    nape at the back, each lying on the ones beneath; every lock a tapered band, thick at the
    root, to a point. Its UVs give each lock a cell of its own, along its length running up the
    texture, so it can be painted along the strands. Rigged to the head."""
    rng = random.Random(seed)
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(human, dg)
    inv = MW.inverted()
    nm = MW.to_3x3().inverted().transposed()

    def nearest(p):
        q, n_, _, d = bvh.find_nearest(inv @ p)
        return MW @ q, (nm @ n_).normalized(), d

    scalp = [i for i in sets["scalp"] if i in sets["body"]]
    roots = []
    for i in rng.sample(scalp, len(scalp)):
        p = pts[i]
        if all((p - q).length > 0.012 for q in roots):
            roots.append(p)
        if len(roots) >= n_locks:
            break
    part_x = E.x + 0.03                                 # his left (+X)
    verts, faces, uvs, along, shade = [], [], [], [], []
    cols = 16
    rows = math.ceil(len(roots) / cols)
    seg = 7
    for k, r in enumerate(sorted(roots, key=lambda p: -p.z)):    # crown first, so the outer locks lie over them
        _, n0, _ = nearest(r)
        side = 1.0 if r.x > part_x else -1.0
        if r.y > E.y + 0.1:                             # the back, to the nape
            d = Vector((0.2 * side, 0.6, -0.8))
            end_z = E.z - 0.13
        elif side < 0:                                  # right of the part: over the top, across the forehead, down the right
            d = Vector((-1.0, -0.12 if r.y < E.y + 0.04 else 0.05, -0.15))
            end_z = E.z - 0.085 + rng.uniform(-0.015, 0.015)
        else:                                           # left of the part: down the left, behind the ear
            d = Vector((1.0, 0.2, -0.4))
            end_z = E.z - 0.085 + rng.uniform(-0.015, 0.015)
        lift = 0.005 + 0.022 * (k / len(roots)) + rng.uniform(0, 0.004)   # each lock over the last: volume
        wave = 40.0 * r.x + 30.0 * r.y                 # neighbours wave together, as combed hair does
        p = r - n0 * 0.003                              # rooted in the scalp
        path, norms = [p.copy()], [n0]
        for i in range(60):
            q, nq, _ = nearest(p)
            d = (d - nq * d.dot(nq) * 0.8).normalized()                      # along the head, not into it
            d = (d + Vector((0, 0, -1)) * (0.015 + 0.012 * i)).normalized()  # falling more as it goes
            d = (d + d.cross(nq).normalized() * 0.07 * math.sin(0.28 * i + wave)).normalized()   # a slight wave
            p = p + d * 0.008
            q, nq, _ = nearest(p)
            if (p - q).dot(nq) < lift:
                p = q + nq * lift
            if p.y < E.y - 0.03 and abs(p.x - E.x) < 0.065 and p.z < E.z + 0.03:
                p.z = E.z + 0.03                       # off the eyes
            path.append(p.copy())
            norms.append(nq)
            if p.z < end_z and i > 6:
                break
        width = rng.uniform(0.02, 0.034)
        cx, cy = k % cols, k // cols
        n = len(path)
        base = len(verts)
        tone = rng.uniform(0.85, 1.15)
        for j, (c, nq) in enumerate(zip(path, norms)):
            u = j / (n - 1)
            t = (path[min(j + 1, n - 1)] - path[max(j - 1, 0)]).normalized()
            s = t.cross(nq).normalized()
            w = width * (1 - u ** 1.6) * (0.75 + 0.25 * min(1.0, u * 6)) + 0.0004
            for a in range(seg + 1):
                ang = 2 * math.pi * a / seg
                verts.append(tuple(c + s * (0.5 * w * math.cos(ang)) + nq * (0.33 * w * math.sin(ang))))
                uvs.append(((cx + 0.05 + 0.9 * a / seg) / cols, (cy + 0.03 + 0.94 * u) / rows))
                along.append(u)
                shade.append(tone)
        for j in range(n - 1):
            for a in range(seg):
                i0 = base + j * (seg + 1) + a
                faces.append((i0, i0 + seg + 1, i0 + seg + 2, i0 + 1))      # wound to face outward
    me = bpy.data.meshes.new("Hair locks")
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    loops = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", loops)
    uv.data.foreach_set("uv", np.array(uvs)[loops].ravel())
    me.attributes.new("along", 'FLOAT', 'POINT').data.foreach_set("value", along)
    me.attributes.new("shade", 'FLOAT', 'POINT').data.foreach_set("value", shade)
    me.shade_smooth()
    ob = bpy.data.objects.new("Hair locks", me)
    scene.collection.objects.link(ob)
    mw = ob.matrix_world.copy()
    ob.parent, ob.parent_type, ob.parent_bone = rig, 'BONE', "Head"
    bpy.context.view_layer.update()
    ob.matrix_world = mw
    print("hair: %d locks" % len(roots))
    return ob


bpy.context.view_layer.update()
locks = hair()
print("head built in %.0fs" % (time.time() - t_start))


def wear(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


def picture(ob):
    """The image texture a fitted asset's own material uses (for its cut-out)."""
    for m in ob.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and "normal" not in n.image.name.lower():
                    return n.image
    return None


# ---------------------------------------------------------------- the breath
for t, w in BREATH_IN.items():
    k = human.data.shape_keys.key_blocks[t]
    for f, v in ((F0, 0.0), (BREATH[0], 0.0), (BREATH[1], w), (F1, w)):
        k.value = v
        k.keyframe_insert("value", frame=f)
for bone, deg in LIFT.items():
    pb = rig.pose.bones[bone]
    for f, v in ((F0, 0.0), (BREATH[0], 0.0), (BREATH[1], deg), (F1, deg)):
        pb.rotation_euler = Euler((math.radians(v), 0, 0))
        pb.keyframe_insert("rotation_euler", frame=f)

# ---------------------------------------------------------------- camera, light, backdrop
scene.frame_set(F0)
bpy.context.view_layer.update()
cd = bpy.data.cameras.new("Close")
cam = bpy.data.objects.new("Close", cd)
scene.collection.objects.link(cam)
scene.camera = cam
if CHECK:
    cd.type = 'ORTHO'
    cd.ortho_scale = 0.42
else:
    cd.lens, cd.sensor_width = 85.0, 36.0
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 2.8
# The left three-quarter view, as in the third photo, a little below the eyes.
cam.location = E + Vector((0.5, -0.95, 0.0))
cam.rotation_euler = (E + Vector((0.035, 0.0, -0.045)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cd.dof.focus_distance = (E - cam.location).length - 0.03


def sun(name, energy, colour, elevation, azimuth, angle=2.0):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy, ld.color, ld.angle = energy, P.srgb(colour), math.radians(angle)
    ob = bpy.data.objects.new(name, ld)
    d = Vector((math.cos(math.radians(elevation)) * math.cos(math.radians(azimuth)),
                math.cos(math.radians(elevation)) * math.sin(math.radians(azimuth)),
                math.sin(math.radians(elevation))))
    ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    scene.collection.objects.link(ob)
    return ob


# Azimuth from +X (the head's left), counter-clockwise; the face looks toward -Y (270), and the
# camera is on the head's left. As on Vi: the key high and nearly in front, so the face is mostly
# in light and the shadows fall soft under the brow, the nose, the lips and the jaw; a cool fill;
# a rim from behind along the hair. Soft (wide suns), as you asked of the shadows.
sun("Morning sun", 3.4, (1.0, 0.93, 0.84), 50, 262, angle=12.0)
sun("Sky fill", 0.35, (0.62, 0.74, 0.86), 15, 215, angle=25.0)
sun("Rim", 2.4, (0.96, 0.9, 0.82), 30, 110, angle=6.0)
sun("Bounce", 0.6, (1.0, 0.9, 0.8), -12, 275, angle=30.0)      # warm light up from below, lifting the shadow under the eyes
P.sky(scene, zenith=(0.07, 0.11, 0.13), horizon=(0.13, 0.18, 0.19), below=(0.08, 0.11, 0.12),  # dark teal, as behind Vi
      clouds=(0.16, 0.21, 0.22), fill=(0.6, 0.7, 0.78), fill_strength=0.3, soft=0.35)


# ---------------------------------------------------------------- bake and paint
def node_mat(name, build):
    m, g, out = P.material(name)
    shader = build(g)
    g.nt.links.new(shader, out.inputs["Surface"])
    return m, g


def skin_colour(g, uv):
    skin_img = bpy.data.images.get("skin scan") or bpy.data.images.load(
        str(H.mpfb_data("skins") / "young_caucasian_male" / "young_lightskinned_male_diffuse.png"))
    skin_img.name = "skin scan"
    tex = g.new("ShaderNodeTexImage", {"Vector": uv}, image=skin_img).outputs["Color"]
    col = g.mix(0.15, (*P.srgb((0.88, 0.79, 0.73)), 1.0), tex)     # pale and muted, as Vi; little of the scan, whose pores read as dirt
    amt = g.math('MULTIPLY', g.new("ShaderNodeAttribute", attribute_name="stubble").outputs["Fac"], 0.3)
    col = g.mix(amt, col, g.scale(col, (0.72, 0.7, 0.75)))        # stubble, a soft cool tone
    lip = g.new("ShaderNodeAttribute", attribute_name="lip_tint").outputs["Fac"]
    return g.mix(g.math('MULTIPLY', lip, 0.8), col, g.scale(col, (0.8, 0.58, 0.56)))   # lips their own, darker rose, as Vi's


def hair_colour(g, uv):
    a = g.new("ShaderNodeAttribute", attribute_name="along").outputs["Fac"]
    sh = g.new("ShaderNodeAttribute", attribute_name="shade").outputs["Fac"]
    col = g.mix(g.remap(a, 0.2, 1.0, 0.0, 1.0), (*P.srgb((0.24, 0.15, 0.09)), 1.0), (*P.srgb((0.44, 0.31, 0.19)), 1.0))
    return g.scale(col, sh)                         # darker at the root, lighter to the ends, as in the photos


def bake(ob, colour, size, name, ao_distance=0.015):
    """Bake ob's colour (EMIT) and the light that reaches it (DIFFUSE, light only) into its UVs;
    save both as half floats for the painter."""
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for dv in prefs.devices:
        dv.use = dv.type == 'OPTIX'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 48
    img = bpy.data.images.new(name + " bake", size, size, float_buffer=True, alpha=False)
    out = {}
    scene.world.light_settings.distance = ao_distance
    for kind in ("base", "light", "ao"):
        if kind == "base":
            m, g = node_mat(name + " base", lambda g: g.new("ShaderNodeEmission", {"Color": colour(g, g.new("ShaderNodeTexCoord").outputs["UV"]), "Strength": 1.0}).outputs[0])
        else:
            m, g = node_mat(name + " " + kind, lambda g: g.new("ShaderNodeBsdfDiffuse", {"Color": (1, 1, 1, 1)}).outputs[0])
        tn = g.new("ShaderNodeTexImage", image=img)
        g.nt.nodes.active = tn
        keep = list(ob.data.materials)
        wear(ob, m)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        t = time.time()
        if kind == "base":
            bpy.ops.object.bake(type='EMIT', margin=24, use_clear=True)
        elif kind == "ao":                          # occlusion close in: the creases
            bpy.ops.object.bake(type='AO', margin=24, use_clear=True)
        else:
            bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=24, use_clear=True)
        a = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(a)
        np.save(PAINT / ("%s-%s.npy" % (name, kind)), a.reshape(size, size, 4).astype(np.float16))
        out[kind] = PAINT / ("%s-%s.npy" % (name, kind))
        ob.data.materials.clear()
        for mm in keep:
            ob.data.materials.append(mm)
        print("baked %s %s in %.0fs" % (name, kind, time.time() - t))
    return out


def region():
    """The UV polygons of the head, neck and shoulders, where the fine brushes go."""
    me = human.data
    uv = me.uv_layers.active.data
    polys = []
    for p in me.polygons:
        if all(v in sets["body"] and pts[v].z > E.z - 0.32 for v in p.vertices):
            polys.append([tuple(uv[li].uv) for li in p.loop_indices])
    path = PAINT / "skin-region.json"
    json.dump(polys, open(path, "w"))
    return path


def painted_mat(name, png):
    img = bpy.data.images.load(str(png))
    m, g, out = P.material(name)
    uv = g.new("ShaderNodeTexCoord").outputs["UV"]
    em = g.new("ShaderNodeEmission", {"Color": g.new("ShaderNodeTexImage", {"Vector": uv}, image=img).outputs["Color"], "Strength": 1.0})
    g.nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


if CHECK:
    clay = P.paint("Clay", (0.75, 0.72, 0.7), shadow=(0.45, 0.45, 0.5), vary=0.0, strokes=0.0, rim_amount=0.0,
                   crease=0.0, grain=0.0, half=None, hard=0.25)
    for ob in [human, locks] + list(fitted.values()):
        wear(ob, clay)
else:
    PAINT.mkdir(parents=True, exist_ok=True)
    skin_png, hair_png = PAINT / "skin-painted.png", PAINT / "hair-painted.png"
    cutouts = {kind: picture(fitted[kind]) for kind in ("eyebrows", "eyelashes")}   # before the bake's stand-ins replace them
    if not (REUSE and skin_png.exists() and hair_png.exists()):
        for ob in [human, locks] + list(fitted.values()):          # something to cast shadows while baking
            wear(ob, P.flat("Bake stand-in", (0.8, 0.8, 0.8)))
        sk = bake(human, skin_colour, SKIN_RES, "skin", 0.012)
        hb = bake(locks, hair_colour, HAIR_RES, "hair", 0.02)
        reg = region()
        for (src, png, pal, radii, extra) in ((sk, skin_png, "skin", "10,5,3,2", ["--region", str(reg), "--bristles", "0", "--threshold", "10"]),
                                              (hb, hair_png, "hair", "8,4,2", ["--along", "v"])):
            t = time.time()
            subprocess.run(["py", str(BRUSH), str(src["base"]), str(src["light"]), str(png), "--palette", pal,
                            "--radii", radii, "--ao", str(src["ao"])] + extra, check=True)
            print("painted %s in %.0fs" % (png.name, time.time() - t))
    wear(human, painted_mat("Painted skin", skin_png))
    wear(locks, painted_mat("Painted hair", hair_png))
    for kind, col in (("eyebrows", (0.17, 0.12, 0.1)), ("eyelashes", (0.1, 0.07, 0.06))):
        m, g, out = P.material("Painted " + kind)
        tex = g.new("ShaderNodeTexImage", {"Vector": g.new("ShaderNodeTexCoord").outputs["UV"]}, image=cutouts[kind])
        em = g.new("ShaderNodeEmission", {"Color": (*P.srgb(col), 1.0), "Strength": 1.0})
        tr = g.new("ShaderNodeBsdfTransparent")
        a = g.remap(tex.outputs["Alpha"], 0.05, 0.45, 0.0, 1.0, smooth=False)     # full, as his brows are
        g.nt.links.new(g.new("ShaderNodeMixShader", [a, tr.outputs[0], em.outputs[0]]).outputs[0], out.inputs["Surface"])
        wear(fitted[kind], m)
    wear(fitted["eyes"], P.flat("Eye", (0.85, 0.82, 0.78)))

r = scene.render
r.resolution_x, r.resolution_y, r.resolution_percentage = (900, 1200, 100) if CHECK else (1920, 1080, 100)
P.eevee(scene, 64)
r.use_compositing = False                          # the paint is in the surfaces; nothing over the frame
r.use_stamp = False
scene.frame_start, scene.frame_end = F0, F1
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "face.blend"))
print("built in %.0fs" % (time.time() - t_start))

r.image_settings.media_type = 'IMAGE'
r.image_settings.file_format = 'PNG'
if CHECK:
    for name, off in (("front", Vector((0, -1.2, 0))), ("side", Vector((-1.2, 0, 0)))):
        cam.location = E + off
        cam.rotation_euler = (-off).to_track_quat('-Z', 'Y').to_euler()
        r.filepath = str(OUT / ("face-check-%s.png" % name))
        bpy.ops.render.render(write_still=True)
    sys.exit(0)
for name, f in (("neutral", F0), ("breath", F1)):
    scene.frame_set(f)
    r.filepath = str(OUT / ("face-%s.png" % name))
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print("still", r.filepath, "%.1fs" % (time.time() - t))
if not STILL:
    frames = OUT / "face-breath"
    frames.mkdir(exist_ok=True)
    r.filepath = str(frames / "######")
    t = time.time()
    bpy.ops.render.render(animation=True)
    print("frames %.0fs, %.1fs a frame" % (time.time() - t, (time.time() - t) / (F1 - F0 + 1)))
    clip = OUT / "face-breath.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-start_number", str(F0),
                    "-i", str(frames / "%06d.png"), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(clip)],
                   check=True)
    print("clip", clip)
