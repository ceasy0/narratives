"""Motion-capture test of the run (beat 13): the layout's grey runners swapped for rigged human
bodies running with real motion capture, in the travelling shot, lit, in EEVEE.

    blender -b --factory-startup -P band_mocap_test.py              the clip and its contact sheet (EEVEE, quick)
    blender -b --factory-startup -P band_mocap_test.py -- still     its middle frame only, to check
    blender -b --factory-startup -P band_mocap_test.py -- real      as real as we can: the scanned forest
                                                                    (forest.py), MakeHuman skins, hair and
                                                                    leather hides, Cycles at 1920x1080
    blender -b --factory-startup -P band_mocap_test.py -- real still     one frame of that, timed: the estimate
    blender -b --factory-startup -P band_mocap_test.py -- real build     build and save the .blend only
    blender -b --factory-startup -P band_mocap_test.py -- painted   the series' painted look (painted.py, Discussion
                                                                    006 round 4): the style test of the run, to
                                                                    work/styletest/run-<shot>.mp4 and its sheet
    blender -b --factory-startup -P band_mocap_test.py -- painted still      its middle frame only
    blender -b --factory-startup -P band_mocap_test.py -- painted reuse      from the people's paint already made
                                                                    (work/styletest/paint/run/)

The shot is the AI test's (ai_video_test.py's TAG, now 04:15:00-04:18:12): the travelling camera,
the band running left through the forest, the cat coming up behind them.

It opens the layout (work/layout/b12-13-layout.blend: run layout_b12_13.py first) and keeps its
travelling camera, its trees and its runners' paths: each grey runner's place, frame by frame, is
read back from the file, so the bodies run exactly where the layout puts them, and a new pass of
the layout carries through. The people come from humans.py: MPFB2 bodies, African, in hide
wraps, the girl about ten, the men who carry spears in the layout carrying them here. Each runs
a different CMU run, from a different point in its stride, so nobody runs in step; the clips are
shared out so each runner's stride stretches as little as it can. The feet are held still on
the ground by two-bone IK, so a stride stretched or shortened to the path doesn't slide.

Writes work/aitest/mocap-<shot>.mp4 (1280x720, clean, the same frames as the layout's
clean-<shot>.mp4), mocap-<shot>-sheet.png (six frames) and the .blend it rendered.
The clip is also meant as input for Runway's Aleph (ai_video_test.py): bodies with real weight,
in our camera and timing, give it far more to keep than stick figures.

In the painted look the people are painted as the style test's face is (face_test.py, accepted
2026-10-16): each body's skin, hide and hair baked into its own texture, its colour, its creases
and its form's hollows (painted.bake), painted over with real brush strokes by brush.py, and lit
live, the renderer's light turned into the painter's colours (painted.live_mat). The forest and
the ground stay shader-painted: the layout's trees have no texture layout for the brush.
"""
import math
import random
import subprocess
import sys
import time
import pathlib

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from bpy_extras import anim_utils

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402
import humans as H  # noqa: E402
import forest as FO  # noqa: E402
import painted as P  # noqa: E402
from ai_video_test import TAG  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STILL, REAL, BUILD = "still" in ARGS, "real" in ARGS, "build" in ARGS     # build: save the .blend, render nothing
PAINTED, REUSE = "painted" in ARGS, "reuse" in ARGS
KIND = "-real" if REAL else ""
random.seed(13)

A, B = (O.frame("%s:%s:%s" % (t[:2], t[2:4], t[4:])) for t in TAG.split("-"))   # the shot, end exclusive
PAD = 24                                             # frames of path either side of it
FRAMES = list(range(A - PAD, B + PAD))
OUT = O.WORK / ("styletest" if PAINTED else "aitest")
PAINT = OUT / "paint" / "run"                        # the people's bakes and paint
BRUSH = pathlib.Path(__file__).resolve().parent / "brush.py"
SHEET = [A + round(i * (B - 1 - A) / 5) for i in range(6)]

t_start = time.time()
bpy.ops.wm.open_mainfile(filepath=str(O.LAYOUT / "b12-13-layout.blend"))
scene = bpy.context.scene
col = scene.collection
cam = bpy.data.objects["CAM travelling"]
scene.camera = cam
for m in list(scene.timeline_markers):          # one camera only: the layout's markers switch cameras
    scene.timeline_markers.remove(m)

# The layout's ground rolls (layout_b12_13.py's height()): read off its mesh, straight down.
_BVH = BVHTree.FromObject(bpy.data.objects["Ground"], bpy.context.evaluated_depsgraph_get())


def ground_z(x, y):
    hit = _BVH.ray_cast(Vector((x, y, 50.0)), Vector((0, 0, -1)))[0]
    return hit.z if hit is not None else 0.0


def ground_many(xy):
    return np.array([ground_z(x, y) for x, y in xy])


# ---------------------------------------------------------------- the layout's runners
def channel(ob, path, index):
    ad = ob.animation_data
    return anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves.find(path, index=index)


band = sorted((ob for ob in bpy.data.objects if ob.type == 'EMPTY' and ob.name + " body" in bpy.data.objects
               and not ob.name.startswith("Other band")), key=lambda ob: ob.name)
runners = []
for ob in band:
    stick = bpy.data.objects[ob.name + " body"]
    fx, fy = channel(ob, "location", 0), channel(ob, "location", 1)
    runners.append({"name": ob.name,
                    "sex": "girl" if ob.name == "Girl" else "woman" if ob.name.startswith("Woman") else "man",
                    "height": max(v.co.z for v in stick.data.vertices) / 0.995,     # the stand-in's head top is at 0.995 h
                    "spear": ob.name + " spear" in bpy.data.objects,
                    "xs": [fx.evaluate(f) for f in FRAMES], "ys": [fy.evaluate(f) for f in FRAMES]})
for ob in bpy.data.objects:                     # the stand-ins go, the other band's too
    if ob.type == 'EMPTY' and ob.name + " body" in bpy.data.objects:
        for o in [ob] + list(ob.children_recursive):
            o.hide_render = o.hide_viewport = True
print("runners", [(r["name"], r["sex"], round(r["height"], 2), r["spear"]) for r in runners])

# ---------------------------------------------------------------- people, and who runs which run
strides = {c: H.Stride(H.Motion(c)) for c in H.CLIPS}
inshot = slice(PAD, PAD + B - A)
for i, r in enumerate(runners):
    t = time.time()
    r["parts"] = H.person("Mocap " + r["name"], r["sex"], r["height"], seed=i + 1, real=REAL,
                          leather_maps=FO.texture("brown_leather") if REAL else None)
    rest = r["parts"]["rest"]
    leg = sum(np.linalg.norm(rest[b]["tail"] - rest[b]["head"]) for b in ("LeftUpLeg", "LeftLeg"))
    p = np.stack([r["xs"], r["ys"]], 1)[inshot]
    r["speed"] = float(np.mean(np.linalg.norm(np.diff(p, axis=0), axis=1)) * O.FPS)
    r["need"] = {c: r["speed"] / (leg / s.mo.leg() * s.speed) for c, s in strides.items()}   # its speed, against the mocap's
    print("made", r["name"], "%.1fs" % (time.time() - t))
free = list(H.CLIPS)
for r in sorted(runners, key=lambda r: -min(r["need"].values())):   # the hardest to match first (the girl)
    r["clip"] = min(free, key=lambda c: abs(math.log(r["need"][c])))
    free.remove(r["clip"])
rng = random.Random(5)
for r in runners:
    rig = r["parts"]["rig"]
    rt = H.Retarget(strides[r["clip"]], r["parts"]["rest"])
    info = H.run(rig, rt, FRAMES, r["xs"], r["ys"], phase0=rng.random(), fps=O.FPS, ground=ground_many)
    if r["spear"]:
        r["parts"]["spear"] = H.spear(rig, rt, "Mocap " + r["name"] + " spear")
    v, st, sx = (info[k][inshot] for k in ("speed", "steps", "stretch"))
    print("%-18s %-5s %.2f m  CMU %-6s  legs x%.2f  %.1f-%.1f m/s  %3.0f-%3.0f steps/min (mocap %3.0f)  "
          "stride x%.2f-%.2f  feet drift %.1f cm (unplanted %.1f)"
          % (r["name"], r["sex"], r["height"], r["clip"], rt.k, v.min(), v.max(), st.min(), st.max(),
             strides[r["clip"]].cadence, sx.min(), sx.max(), info["slide"], rt.slide()))

# ---------------------------------------------------------------- where the camera looks
LANE_X = float(np.mean([np.mean(r["xs"]) for r in runners]))
cam_at = []
for f in (A, B - 1):
    scene.frame_set(f)
    cam_at.append(cam.matrix_world.translation.copy())
Y0, Y1 = min(c.y for c in cam_at), max(c.y for c in cam_at)
CX = cam_at[0].x


# ---------------------------------------------------------------- the quick look (EEVEE, as in lookdev_leaf.py)
def quick_dress():
    """The layout's own trees given bark and leaves, lookdev-style ferns, litter and shrubs, a sky,
    a sun and haze: enough to judge the people by, in seconds a frame."""
    def material(name, build):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        build(nt, out)
        return m


    def noise(nt, scale, detail=6.0):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
        return n


    def leafy(nt, out, color, translucency, rough=0.6):
        """Green lit from both sides: Principled mixed with Translucent."""
        p = nt.nodes.new("ShaderNodeBsdfPrincipled")
        p.inputs["Roughness"].default_value = rough
        t = nt.nodes.new("ShaderNodeBsdfTranslucent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = translucency
        c = H.ramp(nt, noise(nt, 6.0, 4.0).outputs["Fac"], [(0.3, [v * 0.75 for v in color]), (0.7, [min(1, v * 1.2) for v in color])])
        nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
        nt.links.new(c.outputs["Color"], t.inputs["Color"])
        nt.links.new(p.outputs[0], mix.inputs[1])
        nt.links.new(t.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])


    def build_ground(nt, out):
        p = nt.nodes.new("ShaderNodeBsdfPrincipled")
        p.inputs["Roughness"].default_value = 0.92
        c = H.ramp(nt, noise(nt, 0.6, 3.0).outputs["Fac"], [(0.35, (0.12, 0.07, 0.035)), (0.5, (0.26, 0.16, 0.08)),
                                                             (0.62, (0.17, 0.14, 0.05)), (0.75, (0.32, 0.2, 0.1))])
        nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
        H.bump(nt, noise(nt, 30.0, 8.0).outputs["Fac"], 1.0, p, 0.02)
        nt.links.new(p.outputs[0], out.inputs["Surface"])


    def build_bark(nt, out):
        p = nt.nodes.new("ShaderNodeBsdfPrincipled")
        p.inputs["Roughness"].default_value = 0.85
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (6.0, 6.0, 0.8)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        v = nt.nodes.new("ShaderNodeTexVoronoi")
        v.feature = 'DISTANCE_TO_EDGE'
        v.inputs["Scale"].default_value = 6.0
        nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
        c = H.ramp(nt, noise(nt, 20.0).outputs["Fac"], [(0.3, (0.045, 0.035, 0.028)), (0.7, (0.15, 0.115, 0.085))])
        nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
        H.bump(nt, v.outputs["Distance"], 1.0, p, 0.02)
        nt.links.new(p.outputs[0], out.inputs["Surface"])


    def build_fur(nt, out):
        """The cat, still the layout's stand-in: a tawny coat, so it reads."""
        p = nt.nodes.new("ShaderNodeBsdfPrincipled")
        c = H.ramp(nt, noise(nt, 8.0).outputs["Fac"], [(0.35, H.srgb((0.42, 0.3, 0.16))), (0.65, H.srgb((0.6, 0.45, 0.26)))])
        nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Roughness"].default_value = 0.8
        p.inputs["Sheen Weight"].default_value = 0.6
        nt.links.new(p.outputs[0], out.inputs["Surface"])


    GROUND = material("Forest floor", build_ground)
    BARK = material("Bark", build_bark)
    CROWN = material("Crown", lambda nt, out: leafy(nt, out, (0.045, 0.1, 0.025), 0.25, 0.7))
    FERN = material("Fern", lambda nt, out: leafy(nt, out, (0.07, 0.17, 0.03), 0.45))
    LITTER = material("Leaf litter", lambda nt, out: leafy(nt, out, (0.2, 0.11, 0.045), 0.2, 0.75))
    FUR = material("Fur", build_fur)


    def assign(ob, *mats):
        ob.data.materials.clear()
        for m in mats:
            ob.data.materials.append(m)


    def tree_split(ob):
        """The layout's trees are trunks (cones) and crowns (balls), one or many to a mesh: a piece
        with many faces is a crown."""
        me = ob.data
        assign(ob, BARK, CROWN)
        bm = bmesh.new()
        bm.from_mesh(me)
        seen = set()
        for f in bm.faces:
            if f.index in seen:
                continue
            island, todo = [], [f]
            seen.add(f.index)
            while todo:
                g = todo.pop()
                island.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen:
                            seen.add(h.index)
                            todo.append(h)
            for g in island:
                g.material_index = 1 if len(island) > 14 else 0
                g.smooth = True
        bm.to_mesh(me)
        bm.free()


    for ob in list(bpy.data.objects):
        if ob.type != 'MESH' or ob.hide_render:
            continue
        if ob.name.startswith(("Tree", "The tree")):
            tree_split(ob)
        elif ob.name.startswith("Trunk"):                # the trunk that wipes across the lens
            assign(ob, BARK)
            for p in ob.data.polygons:
                p.use_smooth = True
        elif ob.name == "Ground":
            assign(ob, GROUND)
        elif ob.name.startswith("Ground cover"):
            ob.hide_render = True                      # ferns, litter and shrubs instead, below
        elif ob.name == "Big cat":
            assign(ob, FUR)
            for p in ob.data.polygons:
                p.use_smooth = True


    # ---------------------------------------------------------------- ferns and litter where the camera looks
    def frond(bm, base, yaw, length, lift, droop):
        """One fern frond: a thin rachis arching out and down, with leaflets in pairs along it."""
        rot = Matrix.Rotation(yaw, 3, 'Z')

        def at(s):
            return Vector((length * s, 0, length * (lift * math.sin(math.pi * 0.55 * s) - droop * s * s)))

        n = 14
        for i in range(n):
            p0, p1 = at(i / n), at((i + 1) / n)
            w = 0.004
            q = [base + rot @ (p0 + Vector((0, -w, 0))), base + rot @ (p0 + Vector((0, w, 0))),
                 base + rot @ (p1 + Vector((0, w, 0))), base + rot @ (p1 + Vector((0, -w, 0)))]
            bm.faces.new([bm.verts.new(v) for v in q])
        pairs = 14
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
        rr = random.Random(100 + k)
        bm = bmesh.new()
        count = rr.randint(6, 9)
        for i in range(count):
            frond(bm, Vector((0, 0, 0.02)), 2 * math.pi * i / count + rr.uniform(-0.3, 0.3),
                  rr.uniform(0.45, 0.75), rr.uniform(0.5, 0.8), rr.uniform(0.2, 0.45))
        me = bpy.data.meshes.new("Fern %d" % k)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(FERN)
        return me


    variants = [fern_variant(k) for k in range(6)]
    LANE = (LANE_X - 1.8, LANE_X + 2.1)              # where the runners go: kept clear
    placed = 0
    for _ in range(20000):
        x, y = random.uniform(CX + 1.0, CX + 55), random.uniform(Y0 - 30, Y1 + 30)
        if LANE[0] < x < LANE[1]:
            continue
        if abs(y - (Y0 + Y1) / 2) > (x - CX) * 0.75 + 8:   # well outside the frame
            continue
        near = x < LANE[0]                                # between the camera and the runners: few, and small
        if near and random.random() < 0.75:
            continue
        if y > 47 and random.random() < 0.6:              # thinner in the open woodland
            continue
        ob = bpy.data.objects.new("Fern", random.choice(variants))
        ob.location = (x, y, ground_z(x, y))
        ob.rotation_euler = (0, 0, random.uniform(0, 2 * math.pi))
        s = random.uniform(0.5, 0.8) if near else random.uniform(0.7, 1.4)
        ob.scale = (s, s, s)
        col.objects.link(ob)
        placed += 1
        if placed >= 1500:
            break
    print("ferns", placed)

    lit = bmesh.new()
    for _ in range(40000):
        x, y = random.uniform(CX + 0.5, LANE_X + 12), random.uniform(Y0 - 12, Y1 + 12)
        L, W, a = random.uniform(0.05, 0.11), random.uniform(0.02, 0.04), random.uniform(0, 2 * math.pi)
        m = Matrix.Translation((x, y, 0.004 + ground_z(x, y))) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(random.uniform(-0.3, 0.3), 4, 'X')
        q = [lit.verts.new(m @ Vector(v)) for v in ((-L / 2, 0, 0.003), (0, -W / 2, 0.0), (L / 2, 0, 0.004), (0, W / 2, 0.0))]
        lit.faces.new(q)
    litter_me = bpy.data.meshes.new("Leaf litter")
    lit.to_mesh(litter_me)
    lit.free()
    litter = bpy.data.objects.new("Leaf litter", litter_me)
    litter.data.materials.append(LITTER)
    col.objects.link(litter)

    shrub = bmesh.new()                                   # understory behind, so the eye doesn't run out to a bare horizon
    for _ in range(1400):
        x, y = random.uniform(CX + 14, CX + 110), random.uniform(Y0 - 70, Y1 + 70)
        r_ = random.uniform(0.5, 1.4)
        bmesh.ops.create_icosphere(shrub, subdivisions=2, radius=1.0,
                                   matrix=Matrix.Translation((x, y, r_ * 0.55 + ground_z(x, y))) @ Matrix.Diagonal((r_ * random.uniform(0.9, 1.6), r_, r_ * 0.8, 1)))
    shrubs_me = bpy.data.meshes.new("Understory")
    shrub.to_mesh(shrubs_me)
    shrub.free()
    for p in shrubs_me.polygons:
        p.use_smooth = True
    shrubs = bpy.data.objects.new("Understory", shrubs_me)
    shrubs.data.materials.append(CROWN)
    col.objects.link(shrubs)

    # ---------------------------------------------------------------- light and air (as in lookdev_leaf.py)
    world = scene.world
    world.use_nodes = True
    wn = world.node_tree
    for n in list(wn.nodes):
        wn.nodes.remove(n)
    wout = wn.nodes.new("ShaderNodeOutputWorld")
    sky = wn.nodes.new("ShaderNodeTexSky")
    sky.sky_type = 'MULTIPLE_SCATTERING'
    SUN_EL, SUN_AZ = math.radians(38), math.radians(60)        # high, from ahead of the band and to the camera's left
    sky.sun_elevation = SUN_EL
    sky.sun_rotation = SUN_AZ - math.pi / 2
    sky.sun_disc = False
    bg = wn.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.3
    wn.links.new(sky.outputs["Color"], bg.inputs["Color"])
    wn.links.new(bg.outputs[0], wout.inputs["Surface"])


    def build_haze(nt, out):
        v = nt.nodes.new("ShaderNodeVolumePrincipled")
        v.inputs["Density"].default_value = 0.004
        v.inputs["Anisotropy"].default_value = 0.45
        v.inputs["Color"].default_value = (0.9, 0.92, 1.0, 1)
        nt.links.new(v.outputs[0], out.inputs["Volume"])


    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((CX + 60, (Y0 + Y1) / 2, 15)) @ Matrix.Diagonal((150, 170, 30, 1)))
    hz = bpy.data.meshes.new("Haze")
    bm.to_mesh(hz)
    bm.free()
    haze = bpy.data.objects.new("Haze", hz)
    assign(haze, material("Haze", build_haze))
    col.objects.link(haze)

    sun_dir = Vector((math.cos(SUN_EL) * math.cos(SUN_AZ), math.cos(SUN_EL) * math.sin(SUN_AZ), math.sin(SUN_EL)))
    sd = bpy.data.lights.new("Sun", 'SUN')
    sd.energy = 6.0
    sd.angle = math.radians(1.2)
    sd.color = (1.0, 0.92, 0.8)
    sun = bpy.data.objects.new("Sun", sd)
    sun.rotation_euler = sun_dir.to_track_quat('Z', 'Y').to_euler()
    col.objects.link(sun)


def real_dress():
    """The scanned forest of forest.py. The layout's cat is a blob of three balls: in a real
    forest it would be all anyone saw, so it's left out until there's a real one."""
    print("forest", FO.dress(scene, cam, LANE_X, (A, B - 1)))
    bpy.data.objects["Big cat"].hide_render = True


def tone(m):
    """A material's middle colour, back on screen (sRGB): its colour ramp's, or its base colour."""
    ramps = [n for n in m.node_tree.nodes if n.type == 'VALTORGB']
    if ramps:
        els = ramps[0].color_ramp.elements
        c = [sum(e.color[i] for e in els) / len(els) for i in range(3)]
    else:
        c = list(next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs["Base Color"].default_value)[:3]
    return tuple(1.055 * v ** (1 / 2.4) - 0.055 if v > 0.0031308 else 12.92 * v for v in c)


def painted_dress():
    """The series' painted look (painted.py) over the quick dressing: the world's materials
    repainted in their own colours, a painted sky, a thin line round the people; the people
    themselves are painted with the brush (paint_people); the haze and the brush filter over the
    frame come at the render (P.finish)."""
    world = dict(coords='Object', rim_amount=0.0)

    def floor_colour(g, vec):
        """Earth with moss in it: brown, and olive in big soft patches."""
        patch = g.remap(g.noise(g.scale(vec, 0.07), 1.0, 3.0, 0.55, 0.3), 0.45, 0.62, 0.0, 1.0)
        return g.mix(patch, (*P.srgb((0.42, 0.29, 0.17)), 1.0), (*P.srgb((0.36, 0.38, 0.17)), 1.0))

    swaps = [
        ("Forest floor", lambda m: P.paint("Painted floor", (0.4, 0.28, 0.17), colour=floor_colour, scale=0.25, vary=0.2,
                                           shadow=(0.42, 0.38, 0.55), light=(1.12, 1.0, 0.82), edge=(0.1, 0.28), ao=0.3,
                                           ao_distance=0.8, **world)),
        ("Bark", lambda m: P.paint("Painted bark", (0.3, 0.22, 0.16), scale=1.2, vary=0.16, stroke=(30.0, 30.0, 3.0),
                                   shadow=(0.42, 0.38, 0.55), light=(1.15, 1.02, 0.85), edge=(0.1, 0.3), ao=0.35, **world)),
        ("Crown", lambda m: P.paint("Painted crown", (0.2, 0.34, 0.11), scale=0.5, vary=0.22, shadow=(0.32, 0.42, 0.55),
                                    light=(1.22, 1.12, 0.78), edge=(0.08, 0.26), ao=0.4, ao_distance=1.0, coords='Object',
                                    rim=(0.75, 0.9, 0.6), rim_amount=0.25)),
        ("Fern", lambda m: P.paint("Painted fern", (0.24, 0.42, 0.12), scale=3.0, vary=0.18, shadow=(0.35, 0.45, 0.55),
                                   light=(1.2, 1.1, 0.78), edge=(0.08, 0.26), **world)),
        ("Leaf litter", lambda m: P.paint("Painted litter", (0.48, 0.3, 0.15), scale=3.0, vary=0.2, **world)),
        ("Understory", lambda m: m),
        ("Fur", lambda m: P.paint("Painted fur", (0.62, 0.45, 0.26), scale=3.0, coords='Object')),
        ("Eye", lambda m: P.flat("Painted eye", (0.75, 0.7, 0.65))),
        ("Spear shaft", lambda m: P.paint("Painted shaft", (0.42, 0.3, 0.18), scale=3.0)),
        ("Stone point", lambda m: P.paint("Painted point", (0.28, 0.27, 0.26), scale=3.0)),
    ]
    for m in list(bpy.data.materials):
        for prefix, make in swaps:
            if m.name.startswith(prefix):
                new = make(m)
                if new is not m:
                    m.user_remap(new)
                break
    P.sky(scene, zenith=(0.38, 0.56, 0.8), horizon=(0.92, 0.86, 0.72), below=(0.3, 0.33, 0.25),
          clouds=(0.98, 0.95, 0.9), fill=(0.6, 0.7, 0.85), fill_strength=0.4)
    # Warm light up from the sunlit floor, soft and weak, as the face's rig has: the camera sees
    # the band's shadow side, and this models it instead of leaving it one flat value of the sky's
    # fill. It casts no shadow (the ground would block a light from below).
    bd = bpy.data.lights.new("Bounce", 'SUN')
    bd.energy, bd.color, bd.angle, bd.use_shadow = 0.6, P.srgb((1.0, 0.86, 0.72)), math.radians(40), False
    bounce = bpy.data.objects.new("Bounce", bd)
    el, az = math.radians(-25), math.radians(180)      # from below, on the camera's side
    bounce.rotation_euler = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))).to_track_quat('Z', 'Y').to_euler()
    col.objects.link(bounce)
    for r_ in runners:
        P.outline(r_["parts"]["body"], 0.008, (0.1, 0.06, 0.05))
    bpy.data.objects["Big cat"].hide_render = True        # the layout's blob, until there's a cat
    # The layout's crowns are faceted balls: rounded, and pushed into lumps, as painted foliage is.
    cloud = bpy.data.textures.new("Foliage lumps", 'CLOUDS')
    cloud.noise_scale, cloud.noise_depth = 1.4, 2
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or not ob.name.startswith(("Tree", "The tree")) or ob.hide_render:
            continue
        vg = ob.vertex_groups.new(name="crown")
        crown = {v for p in ob.data.polygons if p.material_index == 1 for v in p.vertices}
        if not crown:
            continue
        vg.add(list(crown), 1.0, 'REPLACE')
        trunk = {k for p in ob.data.polygons if p.material_index == 0 for k in p.edge_keys}
        cr = ob.data.attributes.get("crease_edge") or ob.data.attributes.new("crease_edge", 'FLOAT', 'EDGE')
        cr.data.foreach_set("value", [1.0 if e.key in trunk else 0.0 for e in ob.data.edges])   # the trunks keep their shape
        sub = ob.modifiers.new("Round", 'SUBSURF')
        sub.levels = sub.render_levels = 2
        dp = ob.modifiers.new("Lumps", 'DISPLACE')
        dp.texture, dp.texture_coords, dp.strength, dp.mid_level, dp.vertex_group = cloud, 'GLOBAL', 1.6, 0.5, "crown"


# ---------------------------------------------------------------- the people, painted with the brush
def fit_uv(ob, source, wrap=None):
    """A layout for the paint from one of the mesh's UV layers, filling the texture: a face
    across the layer's seam (the back of a wrap, whose u runs round it) is brought together by
    `wrap`, the layer's width, and the whole is scaled to fit, its shape kept so the strokes
    aren't stretched."""
    me = ob.data
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers[source].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    if wrap:
        for p in me.polygons:
            li = list(p.loop_indices)
            u = uv[li, 0]
            if u.max() - u.min() > wrap / 2:
                for i in li:
                    if uv[i, 0] < (u.max() + u.min()) / 2:
                        uv[i, 0] += wrap
    lo, hi = uv.min(0), uv.max(0)
    s = 0.98 / max(hi - lo)
    layer = me.uv_layers.new(name="Paint")
    layer.data.foreach_set("uv", ((uv - lo) * s + 0.01).ravel())
    me.uv_layers.active = layer
    layer.active_render = True


def skin_colour(base):
    """The skin's colour (sRGB) drifting as skin does: big soft patches of value, and a little
    warmer and cooler; no strokes, which the brush makes."""
    def build(g, uv):
        c = (*P.srgb(base), 1.0)
        hue = g.noise(uv, 5.0, 1.0, 0.4, 0.2)
        c = g.mix(hue, g.scale(c, (1.05, 1.0, 0.94)), g.scale(c, (0.95, 1.0, 1.05)))
        return g.scale(c, g.remap(g.noise(uv, 14.0, 2.0, 0.5, 0.3), 0.3, 0.7, 0.86, 1.12))
    return build


def hide_colour(base):
    """A hide: its colour in patches, worn lighter and darker (as humans.hide has it)."""
    def build(g, uv):
        c = (*P.srgb(base), 1.0)
        return g.scale(c, g.remap(g.noise(uv, 12.0, 4.0, 0.55, 0.2), 0.35, 0.68, 0.72, 1.18))
    return build


def hair_colour(base):
    """Close-cropped, tightly coiled hair: near black, a fine grain of lighter coils over it."""
    def build(g, uv):
        c = (*P.srgb(base), 1.0)
        return g.scale(c, g.remap(g.noise(uv, 40.0, 3.0, 0.6, 0.0), 0.35, 0.65, 0.75, 1.45))
    return build


# Each piece of a person: its colour, the texture's size, the occlusion distances (the creases;
# the form's hollows, for the body), and the brushes (radii in pixels, big to small).
PIECES = (("body", skin_colour, 1024, 0.012, 0.07, "20,10,5"),
          ("wrap", hide_colour, 512, 0.012, None, "14,7,4"),
          ("top", hide_colour, 512, 0.012, None, "14,7,4"),
          ("hair", hair_colour, 256, 0.008, None, "8,4,2"))
# The paint lit live (painted.live_mat), set to this scene's light as measured on the bodies in the
# middle frame (a white diffuse read through Shader to RGB): the sun is on the far side of the band,
# so the camera sees their shadow side, lit by the sky's even fill at about 0.18 over most of each
# body and by the warm bounce below, with the sun on the tops and the fronts from about 0.45 up to
# 1.4. So: the shadow in the sky's fill a lifted cool value, readable, deep only where nothing
# reaches; the turn to light through the bounce-lit planes, with the painter's warm note in it; a
# half-tone on the planes the sun grazes and full light, lightened well, only on those facing it.
LIVE = dict(shadow=(0.5, 0.38, 0.45), cool=((0.86, 0.77, 0.84), 0.05, 0.15), soft=(0.25, 0.55),
            steps=(0.6, 1.1, 0.6), light=(1.3, 1.18, 1.02), warm=((1.2, 0.9, 0.78), 0.35))


def paint_people():
    """Each runner's skin, hide and hair baked (the colour, the creases, the form's hollows),
    painted with brush strokes by brush.py and lit live, as the face is. Baked standing (the
    rig at rest) and alone, the forest and the others hidden, so nothing of the pose or the
    scene is in the paint; -- reuse takes the paint already made."""
    PAINT.mkdir(parents=True, exist_ok=True)
    strokes = OUT / "paint" / "strokes.png"       # the face's stroke map, which breaks a shadow's edge along strokes
    if not strokes.exists():
        subprocess.run(["py", str(BRUSH), "strokes", str(strokes), "2048"], check=True)
    shown = [ob for ob in bpy.data.objects if ob.type == 'MESH' and not ob.hide_render]
    t0 = time.time()
    for r_ in runners:
        tag = r_["name"].lower().replace(" ", "-")
        parts = r_["parts"]
        mine = {parts[k] for k, _, _, _, _, _ in PIECES if k in parts}
        for ob in shown:
            ob.hide_render = ob not in mine
        parts["rig"].data.pose_position = 'REST'
        for part, colour, size, ao_d, form_d, radii in PIECES:
            if part not in parts:
                continue
            ob = parts[part]
            base = tone(ob.data.materials[0])
            if "Paint" not in ob.data.uv_layers:
                if part == "hair":
                    fit_uv(ob, 0)                                   # the scalp's corner of MPFB's layout, filling its texture
                elif part in ("wrap", "top"):
                    fit_uv(ob, "rest", wrap=2 * math.pi * 0.16)     # the wrap's own layout: round it and up it (humans.piece)
            png = PAINT / ("%s-%s.png" % (tag, part))
            if not (REUSE and png.exists()):
                src = P.bake(scene, ob, colour(base), size, "%s-%s" % (tag, part), PAINT, ao_d, form_distance=form_d, margin=16)
                t = time.time()
                subprocess.run(["py", str(BRUSH), str(src["base"]), str(src["base"]), str(png), "--palette", "skin", "--radii", radii,
                                "--ao", str(src["ao"]), "--unlit", "--bristles", "0.05", "--threshold", "8"]
                               + (["--form", str(src["form"])] if "form" in src else []), check=True)
                print("painted %s in %.0fs" % (png.name, time.time() - t))
            ob.data.materials[0] = P.live_mat("Painted %s %s" % (r_["name"], part), png, edge=(strokes, 0.2), **LIVE)   # the outline's slot kept
        parts["rig"].data.pose_position = 'POSE'
    for ob in shown:
        ob.hide_render = False
    print("people painted in %.0fs" % (time.time() - t0))


t_dress = time.time()
if REAL:
    real_dress()
else:
    quick_dress()
    if PAINTED:
        painted_dress()
        paint_people()
print("dressed in %.0fs" % (time.time() - t_dress))


# ---------------------------------------------------------------- camera: focus on the band
cd = cam.data
cd.dof.use_dof = True
cd.dof.aperture_fstop = 4.0
for f in range(A - 2, B + 2):
    scene.frame_set(f)
    i = f - FRAMES[0]
    cy = float(np.mean([r["ys"][i] for r in runners]))
    centre = Vector((LANE_X, cy, 1.0 + ground_z(LANE_X, cy)))
    view = cam.matrix_world.to_3x3() @ Vector((0, 0, -1))
    cd.dof.focus_distance = max(1.0, (centre - cam.matrix_world.translation).dot(view))
    cd.dof.keyframe_insert("focus_distance", frame=f)

# ---------------------------------------------------------------- render
r = scene.render
r.use_stamp = False
r.film_transparent = False
r.use_motion_blur = True
r.motion_blur_shutter = 0.5
if REAL:                                        # Cycles on the GPU (OptiX): path traced, denoised
    r.engine = 'CYCLES'
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'OPTIX'
    c = scene.cycles
    c.device = 'GPU'
    c.samples, c.adaptive_threshold = 256, 0.015
    c.use_denoising, c.denoiser = True, 'OPTIX'
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 8, 3, 3
    c.transmission_bounces, c.volume_bounces, c.transparent_max_bounces = 6, 1, 32   # leaves are cut-outs
    c.caustics_reflective = c.caustics_refractive = False
    c.dicing_camera = cam
    r.use_persistent_data = True                # the scene is built once, not every frame
else:
    r.engine = 'BLENDER_EEVEE'
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1280, 720, 100
    e = scene.eevee
    e.taa_render_samples = 64
    e.use_raytracing = True
    e.use_shadows = True
    e.use_volumetric_shadows = True
    e.volumetric_tile_size = '4'
    e.volumetric_end = 80.0
    e.use_fast_gi = True
if PAINTED:
    P.eevee(scene, 32)
    scene.eevee.use_volumetric_shadows = True
    P.finish(scene, haze=(0.72, 0.8, 0.8), mist=(14.0, 110.0), haze_amount=0.35)
else:
    scene.view_settings.view_transform = 'AgX'
    for look in ('AgX - Medium High Contrast', 'None'):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue
OUT.mkdir(parents=True, exist_ok=True)
scene.frame_start, scene.frame_end = A, B - 1
scene.frame_set(A)
name = ("run-%s" % TAG) if PAINTED else ("mocap-%s%s" % (TAG, KIND))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (name + ".blend")))
print("built in %.0fs; saved %s" % (time.time() - t_start, OUT / (name + ".blend")))

if BUILD:
    pass
elif STILL:
    mid = (A + B) // 2
    scene.frame_set(mid)
    r.image_settings.media_type = 'IMAGE'
    r.image_settings.file_format = 'PNG'
    tc = O.timecode(mid).replace(":", "")
    r.filepath = str(OUT / (("run-still-%s.png" % tc) if PAINTED else ("mocap-still-%s%s.png" % (tc, KIND))))
    t = time.time()
    bpy.ops.render.render(write_still=True)
    took = time.time() - t
    print("still %s in %.1fs; the clip (%d frames) would take about %.0f min" % (r.filepath, took, B - A, took * (B - A) / 60))
else:
    # Frames first, as PNGs in their own folder; a frame already there is skipped, so a long
    # render that stops resumes where it stopped. Then ffmpeg makes the clip.
    frames = OUT / name
    frames.mkdir(exist_ok=True)
    r.image_settings.media_type = 'IMAGE'
    r.image_settings.file_format = 'PNG'
    r.use_overwrite, r.use_placeholder = False, True
    r.filepath = str(frames / "######")
    todo = sum(not (frames / ("%06d.png" % f)).exists() for f in range(A, B))
    t = time.time()
    bpy.ops.render.render(animation=True)
    took = time.time() - t
    print("frames %s: %d rendered in %.0fs, %.1fs a frame" % (frames, todo, took, took / max(todo, 1)))
    clip = OUT / (name + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(O.FPS), "-start_number", str(A),
                    "-i", str(frames / "%06d.png"), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(clip)],
                   check=True)
    print("clip", clip)
    # The contact sheet: six frames, three by two, each with its film timecode.
    tc = ("%{eif\\:floor((" + str(A) + "+n)/1440)\\:d\\:2}\\:%{eif\\:mod(floor((" + str(A) + "+n)/24)\\,60)\\:d\\:2}"
          "\\:%{eif\\:mod(" + str(A) + "+n\\,24)\\:d\\:2}")
    pick = "+".join("eq(n\\,%d)" % (f - A) for f in SHEET)
    vf = ("drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='" + tc + "':x=14:y=12:fontsize=30:"
          "fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=6,select='" + pick + "',scale=640:-1,"
          "tile=3x2:padding=4:color=black")
    sheet = OUT / (name + "-sheet.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-vf", vf, "-frames:v", "1", str(sheet)], check=True)
    print("sheet", sheet)
