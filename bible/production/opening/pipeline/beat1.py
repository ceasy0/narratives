"""Beat 1 and the release, 00:00 to 00:42, in the woodcut look you kept (woodcut.py; FOUNDATIONS §4,
"The abstract look"; PLAN §4): shots 0100-0220 of shots.csv, the treatment's beats 1 and 2.

    blender -b --factory-startup -P beat1.py -- keys          key frames, small, on one sheet, to check the timeline
    blender -b --factory-startup -P beat1.py -- frames A B    film frames A to B-1 (any already done are skipped,
                                                              so several can run at once, and one can take the end of another's range)
    blender -b --factory-startup -P beat1.py -- assemble      the mp4 from the frames, and the flash check
    blender -b --factory-startup -P beat1.py -- check TC ...  single frames at full size, to look at (work/beat1/check/)

The timeline, from the shot list and the treatment:
- 00:00-00:10 (0100) the static comes up out of black, flowing left to right from the first frame
  (your note, 2026-10-16): the cuts fade in, the finest first.
- 00:10-00:14 (0110) the static at full strength, the same grain from edge to edge, flowing; no shape.
- 00:14-00:16 (0120) swells and eddies form in it.
- 00:16-00:26 (0130) the face rises under it: at the surface at 00:16, unmistakable by 00:26.
- 00:26-00:38 (0140) the picture holds while the sound draws in; the face all but still.
- 00:38:00 (0200) two frames: the sand pressed onto the face, its lines driven close and bent hard
  over every contour.
- 00:38:02 (0210) eight frames, on ones, and all at the same moment (your note, 2026-10-16): the
  camera beats in and settles back; the static is swept round the head, fastest at its rim, drawn in
  and shut behind it, taking the dark with it; and the white leaps onto the face.
- 00:38:02-00:39:00 (0220) the white grows over the face from where the light from above falls
  highest, fast at first, until the face is all white but for a few black cuts where its forms turn
  from the light (under the brows, the nose, the mouth); then it holds, alone on black, eyes closed.
The camera pushes in slowly from the first frame and comes to rest at 00:38 on the framing of the
style test's still; at the blast it beats once, in and back, then holds. Drawings are on twos
(each re-cut, so the lines boil at their edges); the release is on ones. Writes
work/beat1/frames/NNNN.png (film frames), work/beat1/beat1-0000-1007.mp4 and work/beat1/beat1-flash.txt.
"""
import math
import os
import pathlib
import subprocess
import sys
import time
import zlib

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402
import woodcut as WC  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = O.WORK / "beat1"
FRAMES_DIR = OUT / "frames"
FPS, TWOS = O.FPS, 2
END = O.frame("00:42")                            # a few seconds after the release
RELEASE = O.frame("00:38")                        # 0200: two frames pressed
BLAST = RELEASE + 2                               # 0210: eight frames blasted in
WHITE = O.frame("00:38:10")                       # 0220: the white face alone
GROW = (BLAST, O.frame("00:39:00"))               # the white growing over the face: from the blast's first frame, all white by 00:39:00
K = 4                                             # samples a side in each pixel, as the style test's
WHITE_SUN = Vector((-0.1, 0.45, 0.89)).normalized()   # the white face's light: high, from beyond the head, so the nose's underside and the upper lip are its shadows
WHITE_T = 0.5                                    # the white face's light below this is left black: under the brows, the nose's underside, the mouth
CENTRE = Vector((0.0, -0.02, 0.025))              # the middle of the face, for the whip to turn on and the blast to close on
WHIP = 1.5                                        # how far round the head the static is whipped by the blast's last frame, at the head's rim (radians): a sweep, short of a spiral
PULSE = 0.07                                      # the camera's beat at the release: how much closer


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def strength(t):
    """The static coming up out of black: from nothing on the first frame to full by 00:10, the
    finest cuts first."""
    return min(t / 10.0, 1.0) ** 0.55


def flow(t):
    """How far the static has flowed, in seconds at full speed: moving from the first frame (your
    note, 2026-10-16), and placed so that from 00:16 it lies as it did when it started still."""
    return t - 15.0


def growth(f):
    """How far the white has grown over the face: a leap on the blast's first frame, with the camera's
    beat and the whip (your note, 2026-10-16: all at the same moment), then slowing, all by 00:39:00."""
    x = min(1.0, max(0.0, (f - GROW[0] + 1) / (GROW[1] - GROW[0] + 1)))
    return 1 - (1 - x) ** 2


def pulse(f):
    """The camera's one beat at the release (your note, 2026-10-16): in over the blast's first two
    frames, back over the twelve after."""
    if f < BLAST:
        return 0.0
    if f < BLAST + 2:
        return ease((f - BLAST + 1) / 2.0)
    return 1.0 - ease((f - BLAST - 1) / 12.0)


def shape(t):
    """The swells and eddies forming as the flow starts."""
    return ease((t - 13.5) / 3.0)


def rise(t):
    """The nose's height above the sand: under it until 00:15, at the surface at 00:16, risen by
    00:26, then all but still to 00:38 (the style test's height at its still)."""
    if t < 15.0:
        return -0.012
    if t < 26.0:
        x = (t - 15.0) / 11.0
        return -0.012 + 0.060 * (1 - (1 - x) ** 2)
    return 0.048 + 0.0025 * ease((t - 26.0) / 12.0)


def aim(cam, f):
    """The camera: a slow push in from the first frame, coming to rest at 00:38 on the style test's
    still; held from the release but for its one beat."""
    e = ease(min(f, RELEASE) / RELEASE)
    target = Vector((0.0, -0.008, 0.0)).lerp(Vector((0.0, -0.014, 0.018)), e)
    tilt, dist = math.radians(16.0 + 3.25 * e), (1.20 - 0.325 * e) * (1 - PULSE * pulse(f))
    cam.location = target + Vector((0.006 * e, -math.sin(tilt) * dist, math.cos(tilt) * dist))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()


def read_png(path):
    """One of our own grey PNGs (8-bit, unfiltered rows) as greys in [0, 1]."""
    b = path.read_bytes()
    w, h = int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
    i, data = 8, b""
    while i < len(b):
        n = int.from_bytes(b[i:i + 4], "big")
        if b[i + 4:i + 8] == b"IDAT":
            data += b[i + 8:i + 8 + n]
        i += 12 + n
    a = np.frombuffer(zlib.decompress(data), np.uint8).reshape(h, w + 1)[:, 1:]
    return a.astype(np.float32) / 255


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    face = WC.face_depth()
    block = WC.build_sheet()
    block.data.attributes.new("bare", 'FLOAT_COLOR', 'POINT')
    data, lit = WC.materials()
    lit_bare = lit.copy()                                          # the white face's light falls on the face alone
    lit_bare.name = "Lit bare"
    next(n for n in lit_bare.node_tree.nodes if n.bl_idname == "ShaderNodeAttribute").attribute_name = "bare"
    bare = data.copy()                                             # and the face bare of the sand, as it is
    bare.name = "Bare"
    next(n for n in bare.node_tree.nodes if n.bl_idname == "ShaderNodeAttribute").attribute_name = "bare"
    cam = WC.setup(scene)
    white = bpy.data.objects.new("White light", bpy.data.lights.new("White light", 'SUN'))
    white.data.energy, white.data.angle = math.pi, 0.0
    white.rotation_euler = WHITE_SUN.to_track_quat('Z', 'Y').to_euler()
    scene.collection.objects.link(white)
    return scene, face, block, dict(data=data, lit=lit, lit_bare=lit_bare, bare=bare), cam


def set_bare(block, bare):
    """The face bare of the sand, for the Bare pass."""
    b = bare.reshape(-1)
    block.data.attributes["bare"].data.foreach_set("color", np.stack([b, b, b, np.ones_like(b)], -1).ravel())
    block.data.update()


def render(scene, block, mat, sun, name, w, h, k):
    block.data.materials.clear()
    block.data.materials.append(mat)
    for lamp in ("Raking light", "White light"):
        bpy.data.objects[lamp].hide_render = lamp != sun
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w * k, h * k, 100
    return WC.render_exr(scene, OUT / ("pass-%s-%d.exr" % (name, os.getpid())))   # each worker its own


def frame(f, ctx, drawn, w=1920, h=1080, k=K):
    """Film frame f: its drawing (remade only when it changes), its passes, its cut."""
    scene, face, block, mats, cam = ctx
    t38 = RELEASE / FPS
    if f < RELEASE:                                                # on twos
        m = f // TWOS
        td = m * TWOS / FPS
        key = ("static", m)
        args = dict(rise=rise(td), flow=flow(td), shape=shape(td))
    elif f < BLAST:                                                # pressed: driven close, bent hard
        m, td = f, t38
        key = ("pressed", f)
        args = dict(rise=rise(t38), flow=flow(t38), shape=0.0, bend=WC.BEND * (2.5 + (f - RELEASE)), sp=WC.SP * 0.65)   # pressed flat
    elif f < WHITE:                                                # the blast, on ones: streaming in
        m, td = f, t38
        key = ("blast", f)
        p = (f - BLAST + 1) / (WHITE - BLAST)
        args = dict(rise=rise(t38), flow=flow(t38) + 0.5 * (f - BLAST + 1), shape=1.0, bend=WC.BEND * (1 - 0.5 * p))
    else:                                                          # the white face: the sand gone
        m = f // TWOS
        key = ("white", m)
        args = dict(rise=rise(t38), flow=0.0, shape=0.0, bend=WC.BEND * 0.5)   # its cuts follow its forms gently
    if drawn.get("key") != key:
        t = time.time()
        Z, cut, grain, extra = WC.drawing(face, **args)
        WC.set_drawing(block, Z, cut, grain)
        set_bare(block, extra["bare"])
        drawn["key"] = key
        print("  drawing %s in %.1fs" % (key, time.time() - t))
    aim(cam, f)
    t = time.time()
    data = render(scene, block, mats["data"], None, "data", w, h, k)
    phi, s = data[..., 0] - 4000.0, data[..., 1] - 4000.0
    fill = None
    if f < RELEASE:
        light = render(scene, block, mats["lit"], "Raking light", "light", w, h, k)
        tone = WC.tone_of(data, light) * strength(td)
    elif f < BLAST:                                                # every contour, for a frame
        light = render(scene, block, mats["lit"], "Raking light", "light", w, h, k)
        tone = 0.75 * WC.ramp01(0.25, 1.0, light[..., 0] + WC.GLOW * data[..., 2])
    else:
        g = growth(f)
        bare = render(scene, block, mats["bare"], None, "bare", w, h, k)[..., 0] > 0.5
        tone = None
        if g < 1.0:                                                # the face's own cuts, giving way to the white
            light = render(scene, block, mats["lit"], "Raking light", "light", w, h, k)
            tone = np.where(bare, WC.tone_of(data, light) * (1 - g), 0.0)
        if f < WHITE:                                              # the whip: the static swung round the head, and drawn in
            p = (f - BLAST + 1) / (WHITE - BLAST)
            c = world_to_camera_view(scene, cam, CENTRE)
            cx, cy = c.x * w * k, (1 - c.y) * h * k
            yy, xx = np.mgrid[0:h * k, 0:w * k].astype(np.float32)
            dx, dy = xx - cx, yy - cy
            del xx, yy
            r = np.hypot(dx, dy) * (1920.0 / (w * k))               # pixels at 1920
            a = np.arctan2(dy, dx)
            th = WHIP * p ** 2 * WC.ramp01(300, 560, r) * (560 / np.maximum(r, 560)) ** 1.2   # a vortex: fastest just off the head, slower out from it, still inside it
            cs, sn = np.cos(th), np.sin(th)
            xs, ys = cx + dx * cs + dy * sn, cy - dx * sn + dy * cs   # where each point's static came from
            inside = (xs >= 0) & (xs <= w * k - 1) & (ys >= 0) & (ys <= h * k - 1)   # from off the frame, nothing
            ix = np.clip(np.rint(xs), 0, w * k - 1).astype(np.int32)
            iy = np.clip(np.rint(ys), 0, h * k - 1).astype(np.int32)
            del dx, dy, th, cs, sn, xs, ys
            ragged = 1 + 0.18 * np.sin(3 * a + 1.3 + 2 * p) + 0.09 * np.sin(7 * a - 0.4) + 0.05 * np.sin(13 * a + 2.1)
            reach = (330 + (1500 - 330) * (1 - p) ** 1.6) * ragged  # pixels at 1920: from past the corners to the head, torn
            swept = WC.ramp01(reach + 80, reach - 80, r) * inside
            del r, a, ragged, reach, inside
            static = WC.ramp01(WC.TONE[0], WC.TONE[1], light[..., 0][iy, ix] + WC.GLOW * data[..., 2][iy, ix]) * swept
            phi, s = np.where(bare, phi, phi[iy, ix]), np.where(bare, s, s[iy, ix])
            del ix, iy
            tone = np.where(bare, tone, static)
        if g > 0.0:                                                # the white, growing from where the light falls highest over all the face
            white = render(scene, block, mats["lit_bare"], "White light", "white", w, h, k)[..., 0]
            wb = white[bare]
            q0 = float((wb < WHITE_T).mean())                      # the share of the face that stays black
            T = float(np.quantile(wb, q0 + (1 - q0) * (1 - g)))    # the mark comes down through the face's own light, so the white grows evenly: the high places first, then all but the black share
            fill = np.where(bare, WC.ramp01(T - 0.05, T, white), 0.0)   # solid above the mark; below it black, in a few cuts: under the brows, the nose, the mouth
    print("  passes in %.1fs" % (time.time() - t))
    img = WC.cut(phi, s, tone, m, k) if tone is not None else None
    if fill is not None:
        fimg = WC.cut(phi, s, fill, m, k, 1.0, WC.WIDTH * 2.5)       # lines wide enough to run together: white
        img = fimg if img is None else np.maximum(img, fimg)
    return img


def run_frames(a, b):
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    todo = [f for f in range(a, b) if not (FRAMES_DIR / ("%04d.png" % f)).exists()]
    if not todo:
        print("frames %d-%d: all done" % (a, b - 1))
        return
    ctx = build()
    drawn, t0 = {}, time.time()
    for n, f in enumerate(todo):
        path = FRAMES_DIR / ("%04d.png" % f)
        if path.exists():                                          # another worker has done it since
            continue
        t = time.time()
        part = path.with_suffix(".%d.part" % os.getpid())          # written whole, then renamed: never half a frame
        WC.write_png(part, frame(f, ctx, drawn))
        os.replace(part, path)
        print("frame %d (%s) in %.0fs; %d of %d, %.0f min left" % (f, O.timecode(f), time.time() - t, n + 1, len(todo),
              (time.time() - t0) / (n + 1) * (len(todo) - n - 1) / 60), flush=True)


KEYS = ["00:01", "00:05", "00:09", "00:12", "00:15", "00:17", "00:20", "00:23", "00:26", "00:32", "00:37:23",
        "00:38:00", "00:38:01", "00:38:02", "00:38:04", "00:38:06", "00:38:08", "00:38:10", "00:38:14", "00:38:18", "00:39:02"]


def run_keys():
    """Key frames at 960 x 540, two samples a side, on one sheet with their timecodes' order."""
    ctx = build()
    keys = OUT / "keys"
    keys.mkdir(parents=True, exist_ok=True)
    tiles = []
    for tc in KEYS:
        f = O.frame(tc)
        t = time.time()
        img = frame(f, ctx, {}, 960, 540, 2)
        WC.write_png(keys / ("%04d.png" % f), img)
        tiles.append(img[::2, ::2])
        print("key %s in %.0fs" % (tc, time.time() - t))
    rows = [np.concatenate(tiles[i:i + 3] + [np.zeros_like(tiles[0])] * (3 - len(tiles[i:i + 3])), 1)
            for i in range(0, len(tiles), 3)]
    WC.write_png(OUT / "beat1-keys.png", np.concatenate(rows, 0))
    print("sheet", OUT / "beat1-keys.png")


def run_assemble():
    paths = [FRAMES_DIR / ("%04d.png" % f) for f in range(END)]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        print("missing %d frames, e.g. %s" % (len(missing), missing[:5]))
        sys.exit(1)
    clip = OUT / ("beat1-0000-%04d.mp4" % (END - 1))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(FRAMES_DIR / "%04d.png"),
                    "-frames:v", str(END), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(clip)], check=True)
    print("clip", clip)
    report = WC.flash_check((read_png(p) for p in paths), FPS)
    (OUT / "beat1-flash.txt").write_text(report + "\n", encoding="utf-8")
    print(report.split("\n\nframe")[0])


OUT.mkdir(parents=True, exist_ok=True)
if "check" in ARGS:
    ctx = build()
    (OUT / "check").mkdir(exist_ok=True)
    for tc in ARGS[ARGS.index("check") + 1:]:
        t = time.time()
        WC.write_png(OUT / "check" / ("%s.png" % tc.replace(":", "")), frame(O.frame(tc), ctx, {}))
        print("check %s in %.0fs" % (tc, time.time() - t))
elif "keys" in ARGS:
    run_keys()
elif "frames" in ARGS:
    i = ARGS.index("frames")
    run_frames(int(ARGS[i + 1]), min(int(ARGS[i + 2]), END))
elif "assemble" in ARGS:
    run_assemble()
else:
    print(__doc__)
