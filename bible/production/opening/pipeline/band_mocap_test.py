"""Motion-capture test of the run (beat 13): the layout's grey runners swapped for rigged human
bodies running with real motion capture, in the travelling shot, lit, in EEVEE.

    blender -b --factory-startup -P band_mocap_test.py              the clip and its contact sheet (EEVEE, quick)
    blender -b --factory-startup -P band_mocap_test.py -- still     its middle frame only, to check
    blender -b --factory-startup -P band_mocap_test.py -- real      as real as we can: the scanned forest
                                                                    (forest.py), MakeHuman skins, hair and
                                                                    leather hides, Cycles at 1920x1080
    blender -b --factory-startup -P band_mocap_test.py -- real still     one frame of that, timed: the estimate
    blender -b --factory-startup -P band_mocap_test.py -- real build     build and save the .blend only

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
from bpy_extras import anim_utils

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402
import humans as H  # noqa: E402
import forest as FO  # noqa: E402
from ai_video_test import TAG  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STILL, REAL, BUILD = "still" in ARGS, "real" in ARGS, "build" in ARGS     # build: save the .blend, render nothing
KIND = "-real" if REAL else ""
random.seed(13)

A, B = (O.frame("%s:%s:%s" % (t[:2], t[2:4], t[4:])) for t in TAG.split("-"))   # the shot, end exclusive
PAD = 24                                             # frames of path either side of it
FRAMES = list(range(A - PAD, B + PAD))
OUT = O.WORK / "aitest"
SHEET = [A + round(i * (B - 1 - A) / 5) for i in range(6)]

t_start = time.time()
bpy.ops.wm.open_mainfile(filepath=str(O.LAYOUT / "b12-13-layout.blend"))
scene = bpy.context.scene
col = scene.collection
cam = bpy.data.objects["CAM travelling"]
scene.camera = cam
for m in list(scene.timeline_markers):          # one camera only: the layout's markers switch cameras
    scene.timeline_markers.remove(m)


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
    info = H.run(rig, rt, FRAMES, r["xs"], r["ys"], phase0=rng.random(), fps=O.FPS)
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
        ob.location = (x, y, 0)
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
        m = Matrix.Translation((x, y, 0.004)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Rotation(random.uniform(-0.3, 0.3), 4, 'X')
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
                                   matrix=Matrix.Translation((x, y, r_ * 0.55)) @ Matrix.Diagonal((r_ * random.uniform(0.9, 1.6), r_, r_ * 0.8, 1)))
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


t_dress = time.time()
if REAL:
    real_dress()
else:
    quick_dress()
print("dressed in %.0fs" % (time.time() - t_dress))


# ---------------------------------------------------------------- camera: focus on the band
cd = cam.data
cd.dof.use_dof = True
cd.dof.aperture_fstop = 4.0
for f in range(A - 2, B + 2):
    scene.frame_set(f)
    i = f - FRAMES[0]
    centre = Vector((LANE_X, float(np.mean([r["ys"][i] for r in runners])), 1.0))
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
name = "mocap-%s%s" % (TAG, KIND)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (name + ".blend")))
print("built in %.0fs; saved %s" % (time.time() - t_start, OUT / (name + ".blend")))

if BUILD:
    pass
elif STILL:
    mid = (A + B) // 2
    scene.frame_set(mid)
    r.image_settings.media_type = 'IMAGE'
    r.image_settings.file_format = 'PNG'
    r.filepath = str(OUT / ("mocap-still-%s%s.png" % (O.timecode(mid).replace(":", ""), KIND)))
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
