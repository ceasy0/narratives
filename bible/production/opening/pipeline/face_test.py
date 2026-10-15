"""The face in the series' painted look: one head, close, one expression (the style test, PLAN §9,
item 3; Discussion 006, round 4).

    blender -b --factory-startup -P face_test.py               stills, the clip and its sheet
    blender -b --factory-startup -P face_test.py -- still      the two stills only
    blender -b --factory-startup -P face_test.py -- check      grey front and side views, to set the shape

The head is MPFB2's, shaped after Corbin's photos (work/face/, out of git) with its own sliders
(FACE below): long and lean, a narrow head, high cheekbones over hollow cheeks, a low straight
brow, deep-set eyes, a long straight nose, a full lower lip, a firm square jaw and chin, a long
neck; dark brown hair to the jaw, swept to one side. It's a likeness to judge the look by, not the
design of the recurring face, which comes after (PLAN §5). The eyes stay closed, as in the photos
and as the Opening's face first is. The expression is the Opening's last: one breath drawn in
(05:00), the nostrils widening, the lips parting a little, the chin lifting.

It's painted with painted.py: a skin from MakeHuman's light-skinned scan, painted over, warm in
the light and cool-violet in the shadow; a warm low sun from the front and side, a cool fill, a
rim from behind; a soft painted ground behind; the brush filter over all.

Writes work/styletest/face-neutral.png, face-breath.png, face-breath.mp4 and face-sheet.png.
"""
import importlib
import math
import pathlib
import subprocess
import sys
import time

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402
import humans as H  # noqa: E402
import painted as P  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STILL, CHECK = "still" in ARGS, "check" in ARGS
OUT = O.WORK / "styletest"
FPS = O.FPS
F0, BREATH, F1 = 1, (30, 66), 96                  # still, then one breath in over 1.5 s, held

# The head after the photos: MPFB target -> weight (0-1; each target is one side of a slider).
FACE = {"head-oval": 0.6, "head-scale-horiz-decr": 0.3, "head-scale-vert-incr": 0.2,
        "forehead-scale-vert-incr": 0.15,
        "eyebrows-trans-down": 0.1, "eyebrows-angle-down": 0.15,
        "l-eye-push1-in": 0.1, "r-eye-push1-in": 0.1,
        "nose-scale-vert-incr": 0.35, "nose-scale-depth-incr": 0.25, "nose-hump-decr": 0.25,
        "nose-point-up": 0.15, "nose-point-width-incr": 0.15,
        "mouth-lowerlip-volume-incr": 0.4, "mouth-cupidsbow-incr": 0.3, "mouth-upperlip-volume-decr": 0.05,
        "chin-prominent-incr": 0.5, "chin-height-incr": 0.25, "chin-width-incr": 0.2, "chin-bones-incr": 0.35,
        "l-cheek-bones-incr": 0.4, "r-cheek-bones-incr": 0.4,
        "l-cheek-volume-decr": 0.45, "r-cheek-volume-decr": 0.45,
        "l-cheek-inner-decr": 0.25, "r-cheek-inner-decr": 0.25,
        "neck-scale-vert-incr": 0.25, "neck-scale-horiz-decr": 0.15}
CLOSED = {"eye-left-closure": 1.0, "eye-right-closure": 1.0}       # baked in: the eyes stay shut
BREATH_IN = {"nose-left-dilatation": 0.8, "nose-right-dilatation": 0.8, "mouth-open": 0.09}
LIFT = {"Neck1": -4.0, "Head": -5.0}              # degrees about each bone's x: the chin up
HAIR, BROWS, LASHES = "short02", "eyebrow012", "eyelashes01"

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

# Stubble, as in the photos: a soft mask over the jaw, the chin and the upper lip, kept off the
# lips and stopping in front of the ears, measured from the eyes.
sets = H.vertex_sets(human, ["helper-l-eye", "helper-r-eye"])
pts = [human.matrix_world @ v.co for v in human.data.vertices]
E = sum((pts[i] for i in sets["helper-l-eye"] | sets["helper-r-eye"]), Vector()) / len(sets["helper-l-eye"] | sets["helper-r-eye"])


def ramp01(a, b, x):
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


mask = []
for p in pts:
    d = p - E
    m = ramp01(-0.045, -0.062, d.z) * ramp01(-0.15, -0.13, d.z)       # from under the nose to the jaw's edge
    m *= ramp01(0.06, 0.04, d.y)                                         # in front of the ears
    m *= 1 - ramp01(0.045, 0.06, abs(d.x)) * ramp01(-0.07, -0.04, d.z)  # up the cheeks only at the jaw
    lip = ((d.x / 0.028) ** 2 + ((d.z + 0.078) / 0.011) ** 2) ** 0.5
    m *= ramp01(0.85, 1.25, lip)                                         # not on the lips
    mask.append(m)
att = human.data.attributes.new("stubble", 'FLOAT', 'POINT')
att.data.foreach_set("value", mask)

rig = HS.add_builtin_rig(human, "cmu_mb")
for pb in rig.pose.bones:
    pb.rotation_mode = 'XYZ'
fitted = {}                                        # fitted after the rig, so they're rigged with it
for kind, what in (("eyes", "high-poly"), ("eyebrows", BROWS), ("eyelashes", LASHES), ("hair", HAIR)):
    ob = HS.add_mhclo_asset(str(H.mpfb_data(kind) / what / (what + ".mhclo")), human,
                            asset_type=kind.capitalize(), subdiv_levels=0)
    fitted[kind] = ob
for t, w in BREATH_IN.items():
    TS.load_target(human, str(SYSTEM / "expression" / "units" / "caucasian" / (t + ".target.gz")), weight=0.0, name=t)
for p in human.data.polygons:
    p.use_smooth = True
sd = human.modifiers.new("Smooth", 'SUBSURF')
sd.levels, sd.render_levels = 1, 2
print("head built in %.0fs" % (time.time() - t_start))


def picture(ob):
    """The image texture a fitted asset's own material uses (for its colour and cut-out)."""
    for m in ob.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and "normal" not in n.image.name.lower():
                    return n.image
    return None


def wear(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


# ---------------------------------------------------------------- paint
if not CHECK:
    skin_img = bpy.data.images.load(str(H.mpfb_data("skins") / "young_caucasian_male" / "young_lightskinned_male_diffuse.png"))
    def skin_colour(g, uv):
        tex = g.new("ShaderNodeTexImage", {"Vector": uv}, image=skin_img).outputs["Color"]
        col = g.mix(0.5, (*P.srgb((0.9, 0.72, 0.64)), 1.0), tex)
        amt = g.math('MULTIPLY', g.new("ShaderNodeAttribute", attribute_name="stubble").outputs["Fac"], 0.42)
        return g.mix(amt, col, g.scale(col, (0.68, 0.66, 0.72)))     # painted as a soft cool tone, as stubble reads

    skin = P.paint("Painted skin", (0.9, 0.72, 0.64), colour=skin_colour, shadow=(0.55, 0.38, 0.48),
                   light=(1.04, 0.99, 0.93), scale=3.0, vary=0.06, strokes=0.6, edge=(0.2, 0.36), spec=0.04, ao=0.45,
                   ao_distance=0.04, rim=(0.62, 0.74, 1.0), rim_amount=0.22)
    wear(human, skin)
    hair_img = picture(fitted["hair"])
    wear(fitted["hair"], P.paint("Painted hair", (0.24, 0.155, 0.1), shadow=(0.42, 0.36, 0.5),
                                 light=(1.25, 1.12, 0.98), scale=2.5, vary=0.12, edge=(0.12, 0.32),
                                 spec=0.12, spec_color=(0.85, 0.66, 0.46), ao=0.3, ao_distance=0.05,
                                 alpha_image=hair_img, alpha_cut=0.5, rim_amount=0.25, streaks=(70.0, 3.0)))
    for kind in ("eyebrows", "eyelashes"):
        wear(fitted[kind], P.paint("Painted " + kind, (0.22, 0.14, 0.09), shadow=(0.6, 0.55, 0.65),
                                   light=(1.1, 1.05, 1.0), vary=0.05, alpha_image=picture(fitted[kind]),
                                   alpha_cut=0.45, rim_amount=0.0, ao=0.0))
    wear(fitted["eyes"], P.flat("Eye", (0.85, 0.82, 0.78)))
    P.outline(human, 0.0006, (0.22, 0.11, 0.1))
else:
    for ob in [human] + list(fitted.values()):
        wear(ob, P.paint("Clay", (0.75, 0.72, 0.7), shadow=(0.45, 0.45, 0.5), vary=0.0, strokes=0.0, rim_amount=0.0))
    fitted["hair"].hide_render = True                 # the shape alone

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

# ---------------------------------------------------------------- camera, light, ground
scene.frame_set(F0)
bpy.context.view_layer.update()
eyes = E                                            # between the eyes
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
cam.location = eyes + Vector((0.5, -0.95, 0.0))
cam.rotation_euler = (eyes + Vector((0.035, 0.0, -0.045)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cd.dof.focus_distance = (eyes - cam.location).length - 0.03


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
# camera is on the head's left. The key is on the far side, so the near cheek turns into shadow.
sun("Morning sun", 4.0, (1.0, 0.86, 0.68), 20, 235)       # low, warm, from the front and the face's right
sun("Sky fill", 0.5, (0.62, 0.72, 1.0), 15, 320)          # cool and dim, from the camera's side
sun("Rim", 2.2, (1.0, 0.9, 0.78), 25, 60)                 # from behind on the camera's side, along the edge
P.sky(scene, zenith=(0.42, 0.5, 0.66), horizon=(0.88, 0.74, 0.6), below=(0.78, 0.66, 0.56),
      clouds=(0.93, 0.83, 0.72), fill=(0.6, 0.66, 0.8), fill_strength=0.3, soft=0.35)

r = scene.render
r.resolution_x, r.resolution_y, r.resolution_percentage = (900, 1200, 100) if CHECK else (1920, 1080, 100)
P.eevee(scene, 64)
if CHECK:
    r.use_compositing = False
else:
    P.finish(scene, brush=5, uniformity=4, sharpness=0.5, bloom=0.2)
r.use_stamp = False
scene.frame_start, scene.frame_end = F0, F1
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "face.blend"))
print("built in %.0fs" % (time.time() - t_start))

r.image_settings.media_type = 'IMAGE'
r.image_settings.file_format = 'PNG'
if CHECK:
    for name, off in (("front", Vector((0, -1.2, 0))), ("side", Vector((-1.2, 0, 0)))):
        cam.location = eyes + off
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
