"""Beat 1 and the release, 00:00 to 00:42, in the woodcut look you kept (woodcut.py; FOUNDATIONS §4,
"The abstract look"; PLAN §4): shots 0100-0220 of shots.csv, the treatment's beats 1 and 2.

    blender -b --factory-startup -P beat1.py -- keys          key frames, small, on one sheet, to check the timeline
    blender -b --factory-startup -P beat1.py -- frames A B    film frames A to B-1 (any already done are skipped,
                                                              so several can run at once, and one can take the end of another's range)
    blender -b --factory-startup -P beat1.py -- assemble      the mp4 from the frames, and the flash check
    blender -b --factory-startup -P beat1.py -- check TC ...  single frames at full size, to look at (work/beat1/check/)

The timeline, from the shot list and the treatment:
- 00:00-00:10 (0100) the static comes up out of black, flowing left to right from the first frame
  and already in its clumps, the swells and eddies it keeps (your notes, 2026-10-16 and 2026-10-17: it
  reads like an ocean drawn in black and white from the start, not a plain grain that takes shape later):
  the cuts fade in, the finest first.
- 00:10-00:16 (0110, 0120) the static at full strength, the same from edge to edge, flowing.
- 00:16-00:26 (0130) the face rises under it: at the surface at 00:16, unmistakable by 00:26. The sand
  piles round it as in the first render (your note, 2026-10-17: that edge, not the heap that followed it,
  which also threw a shadow under the chin), its lit side crossed by the lines and its far side dark, as
  that render had it (your note of the same day, with its clip: not the second test's fill of thin lines),
  and its bottom edge coming out of the sheet as the other edges do, since the light casts no shadow.
- 00:26-00:38 (0140) the picture holds while the sound draws in; the face all but still.
- 00:38:00 (0200) two frames: the sand pressed onto the face, its lines driven close and bent hard
  over every contour.
- 00:38:02-00:38:10 (0210) the whip, four drawings on twos, with the camera's beat on the first (your
  notes, 2026-10-17: no swirl; not in one instant; choppy as a cartoon and still one smooth action): the
  sheet is drawn in to the head and behind it, every line smeared along its path, the far corners
  emptying first, the lines crowding and bending as they close on the head, until nothing is left
  outside the face.
- 00:38:10-00:39:10 (0220) the lines come round either side of the head and land on the face, on twos,
  filling it white from its two sides in to the middle, fast at first, each line arriving a little
  before or after its neighbours, the face's own cuts giving way under them; outside the rims, a
  narrowing band of the lines still coming round, flowing in. Then the face holds, all white but for a
  few black cuts where its forms turn from the light (under the brows, the nose, the mouth), those cuts
  carrying the face's own lines so the mouth isn't a smooth hole; alone on black, eyes closed.
The camera pushes in slowly from the first frame and comes to rest at 00:38 on the framing of the
style test's still; on the whip's first frame it beats once, in, and settles back over half a second,
then holds. Drawings are on twos (each re-cut, so the lines boil at their edges); the release is on ones.
Writes work/beat1/frames/NNNN.png (film frames), work/beat1/beat1-0000-1007.mp4 and
work/beat1/beat1-flash.txt; with `half` after the command, a half-size test (960 x 540) into
work/beat1/half/ instead, about four times as fast.
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
HALF = "half" in ARGS
OUT = O.WORK / "beat1" / ("half" if HALF else "")
FRAMES_DIR = OUT / "frames"
W, H, K = (960, 540, 2) if HALF else (1920, 1080, 4)   # the frame, and samples a side in each pixel (the style test's four)
FPS, TWOS = O.FPS, 2
END = O.frame("00:42")                            # a few seconds after the release
RELEASE = O.frame("00:38")                        # 0200: two frames pressed
BLAST = RELEASE + 2                               # 0210: the whip's first frame
WHIP_N = 4                                        # the whip's drawings, on twos
LAND = (BLAST + 2 * WHIP_N, O.frame("00:39:10"))  # 0220: the lines landing on the face, on twos, from the whip's end until it's white
WHITE_SUN = Vector((-0.1, 0.45, 0.89)).normalized()   # the white face's light: high, from beyond the head, so the nose's underside and the upper lip are its shadows
WHITE_T = 0.5                                    # the white face's light below this is left black: under the brows, the nose's underside, the mouth
CENTRE = Vector((0.0, -0.02, 0.025))              # the middle of the face, for the whip to go in to
PULSE = 0.07                                      # the camera's beat at the whip: how much closer
WHIP_D = 1100.0                                   # how far in the sheet is drawn by the whip's last drawing (pixels at 1920): the far corners' distance, so nothing is left
BAND = 150.0                                      # the landing: how far outside the rims the lines coming round are drawn as it starts (pixels at 1920), narrowing to nothing
BAND_FLOW = 120.0                                 # and how far those lines travel in toward the head over the landing (pixels at 1920)
EDGE = 150.0                                      # the whip: the sheet's edge, as it's drawn in from the frame's, is ragged over this width (pixels at 1920), not a rule
SHADOW_CUTS = 0.7                                 # the white face's black cuts carry its own lines at this tone (your note, 2026-10-17: the mouth too smooth)

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


def landing(f):
    """How far the lines have landed on the face: from the whip's end, fast at first, all by 00:39:10."""
    x = min(1.0, max(0.0, (f - LAND[0] + 1) / (LAND[1] - LAND[0] + 1)))
    return 1 - (1 - x) ** 2


def pulse(f):
    """The camera's one beat at the release (your notes, 2026-10-16 and 2026-10-17): in on the whip's
    first frame, the same instant the sheet starts to go, and back over the twelve frames after."""
    if f < BLAST:
        return 0.0
    if f == BLAST:
        return 1.0
    return 1.0 - ease((f - BLAST) / 12.0)


def shape(t):
    """The static's swells and eddies: there from the first frame (your note, 2026-10-17: the clumps
    the static comes in with are the clumps it keeps)."""
    return 1.0


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
    still; held from the release but for its one beat on the whip's frame."""
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


def whip(data, light, bare, phi, s, tone, scene, cam, w, h, k, n):
    """The whip (your notes, 2026-10-17: no swirl, not in one instant, choppy as a cartoon and still one
    smooth action): drawing n of WHIP_N, on twos. The sheet is drawn in to the head and behind it: each
    point shows what lay further out along its line to the middle of the face, smeared over the distance
    it came since the last drawing, the far corners emptying first, the lines crowding and bending as
    they close on the head. The face keeps its own cuts."""
    c = world_to_camera_view(scene, cam, CENTRE)
    cx, cy = c.x * w * k, (1 - c.y) * h * k
    px = 1920.0 / (w * k)                                          # pixels at 1920 for each sample
    yy, xx = np.mgrid[0:h * k, 0:w * k].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    del xx, yy
    r = np.hypot(dx, dy)
    ux, uy = dx / np.maximum(r, 1.0), dy / np.maximum(r, 1.0)      # out from the middle of the face
    del dx, dy
    far = lambda q: WHIP_D / px * q ** 2                           # how far in the sheet has come, in samples: gathering speed
    d0, d1 = far(n / WHIP_N), far((n + 1) / WHIP_N)                 # since the last drawing, and now
    L = WC.ramp01(WC.TONE[0], WC.TONE[1], WC.lit(data, light))      # the sheet's cuts, where they lay
    mean, peak = np.zeros(r.shape, np.float32), np.zeros(r.shape, np.float32)
    N = 5
    for j in range(N):                                             # what the sheet was along the way: its mean (the smear) and its brightest
        d = d0 + (d1 - d0) * j / (N - 1)
        xs, ys = cx + ux * (r + d), cy + uy * (r + d)
        margin = np.minimum(np.minimum(xs, w * k - 1 - xs), np.minimum(ys, h * k - 1 - ys))   # to the frame's edge, where the sheet ends
        inside = np.clip(margin * px / EDGE + 0.7 * (WC.noise2(xs * px / 90.0, ys * px / 90.0, 13) - 0.5), 0.0, 1.0) * (margin > 0)   # the sheet's edge, ragged, and nothing from off the frame (a sample off it would draw the edge's own line as a spike)
        ix = np.clip(np.rint(xs), 0, w * k - 1).astype(np.int32)
        iy = np.clip(np.rint(ys), 0, h * k - 1).astype(np.int32)
        del xs, ys
        t = L[iy, ix] * inside
        mean += t / N
        np.maximum(peak, t, out=peak)
        if j == N - 1:                                             # the lines as they lie now: from where they came; past the sheet's edge, nothing
            phi_w, s_w, edge = phi[iy, ix], s[iy, ix], inside
        del ix, iy, inside, t
    del ux, uy, r, L
    streak = np.minimum(0.5 * mean + 0.5 * peak, 0.7) * edge       # never solid: lines, smeared
    del mean, peak, edge
    return np.where(bare, phi, phi_w), np.where(bare, s, s_w), np.where(bare, tone, streak)


def land(data, light, bare, white, phi, s, tone, w, k, p):
    """After the whip (your note, 2026-10-17): the lines come round either side of the head and land on
    the face, filling it white from its two sides in to the middle, each line arriving a little before
    or after its neighbours; the face's own cuts give way under them. Outside the rims, a narrowing
    band of the lines still coming round. Returns the tone of the cuts and the white's fill."""
    Hh, Ww = bare.shape
    px = 1920.0 / (w * k)
    cols = np.broadcast_to(np.arange(Ww, dtype=np.int32)[None, :], bare.shape)
    far = np.int32(4 * Ww)
    nl = np.maximum.accumulate(np.where(bare, -far, cols), axis=1)            # along each row: the last column outside the face to the left
    nr = np.minimum.accumulate(np.where(bare, far, cols)[:, ::-1], axis=1)[:, ::-1]   # and the first to the right
    dl, dr = (cols - nl).astype(np.float32), (nr - cols).astype(np.float32)   # so each span of the face fills from its own rims, whatever else lies on the row
    d = np.minimum(dl, dr) - 0.5                                   # samples in from the nearer rim
    u = d / np.maximum((dl + dr) / 2.0, 1.0)                       # 0 at the rims, 1 on the middle line
    bl = np.maximum.accumulate(np.where(bare, cols, -far), axis=1)             # outside the face: the nearest of it to the left
    br = np.minimum.accumulate(np.where(bare, cols, far)[:, ::-1], axis=1)[:, ::-1]   # and to the right
    dout = np.minimum(cols - bl, br - cols).astype(np.float32)     # samples out from the nearer rim
    inward = np.where(br - cols < cols - bl, -1.0, 1.0)            # toward the face: left of it, further out is further left
    del nl, nr, dl, dr, bl, br
    jit = 0.25 * (WC.hash2(np.floor(phi).astype(np.int64), 0, 11) - 0.5) + 0.3 * (WC.noise2(phi / 10.0, s / 40.0, 12) - 0.5)   # each line lands in its own time, and the front wanders over the rows: never a straight wall of line ends (the third test's seam down the forehead), still two fronts coming in
    front = 1.35 * p
    cover = WC.ramp01(front + 0.06, front - 0.06, u + jit) * bare   # landed: the white, where the lines have come in to
    fill = np.where(bare, WC.ramp01(WHITE_T - 0.05, WHITE_T, white), 0.0) * cover   # solid, but for the few black cuts: under the brows, the nose, the mouth
    if os.environ.get("BEAT1_DEBUG"):                              # the landing's parts, to look at (work/.../debug/)
        dbg = OUT / "debug"
        dbg.mkdir(exist_ok=True)
        for name, a in (("u", np.clip(u, 0.0, 1.0)), ("jit", jit + 0.5), ("cover", cover), ("white", white), ("fill", fill), ("bare", bare.astype(np.float32)), ("tone", tone), ("dout", np.clip(dout / 200.0, 0.0, 1.0))):
            WC.write_png(dbg / ("%s-%.2f.png" % (name, p)), a[::k, ::k])
    del u, jit
    width = max(BAND * (1 - p) / px, 1.0)
    band = (~bare) & (dout < width)                                # outside the rims, the lines still coming round
    shift = inward * (BAND_FLOW * (1 - p) / px)                    # those lines flow in toward the head: each shows what lay further out
    ix = np.clip(np.rint(cols + shift), 0, Ww - 1).astype(np.int32)
    iy = np.broadcast_to(np.arange(Hh, dtype=np.int32)[:, None], ix.shape)
    coming = WC.ramp01(WC.TONE[0], WC.TONE[1], WC.lit(data, light)[iy, ix]) * WC.ramp01(width, 0.15 * width, dout)
    del ix, iy, shift, inward, dout, cols
    tone = np.where(bare, tone * (1 - cover), np.where(band, coming, 0.0))
    return tone, fill


def frame(f, ctx, drawn, w=W, h=H, k=K):
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
    elif f < LAND[1]:                                              # the whip and the landing, on twos: the sheet in flight
        m, td = f // TWOS, t38
        key = ("release", m)
        p = (m * TWOS - BLAST + 1) / (LAND[1] - BLAST)
        args = dict(rise=rise(t38), flow=flow(t38) + 0.5 * (m * TWOS - BLAST + 1), shape=1.0, bend=WC.BEND * (1 - 0.5 * p))
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
        tone = 0.75 * WC.ramp01(0.25, 1.0, light[..., 0] + WC.GLOW * WC.unpack(data)[0])
    else:
        bare = render(scene, block, mats["bare"], None, "bare", w, h, k)[..., 0] > 0.5
        white = render(scene, block, mats["lit_bare"], "White light", "white", w, h, k)[..., 0]
        light = render(scene, block, mats["lit"], "Raking light", "light", w, h, k)
        tone = np.where(bare, WC.tone_of(data, light), 0.0)        # the face's own cuts, until the white covers them
        if f < LAND[0]:                                            # the whip, on twos
            phi, s, tone = whip(data, light, bare, phi, s, tone, scene, cam, w, h, k, (f - BLAST) // TWOS)
        elif f < LAND[1]:                                          # the landing, on twos
            tone, fill = land(data, light, bare, white, phi, s, tone, w, k, landing(m * TWOS))
        else:                                                      # the white face: its black cuts carry its own lines
            fill = np.where(bare, WC.ramp01(WHITE_T - 0.05, WHITE_T, white), 0.0)
            tone = np.where(bare & (fill < 0.5), tone * SHADOW_CUTS, 0.0)
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
        "00:38:00", "00:38:02", "00:38:04", "00:38:06", "00:38:08", "00:38:10", "00:38:14", "00:38:18", "00:38:23", "00:39:12"]


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
    clip = OUT / ("beat1-%s0000-%04d.mp4" % ("half-" if HALF else "", END - 1))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(FRAMES_DIR / "%04d.png"),
                    "-frames:v", str(END), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(clip)], check=True)
    print("clip", clip)
    report = WC.flash_check((read_png(p) for p in paths), FPS)
    (OUT / ("beat1-half-flash.txt" if HALF else "beat1-flash.txt")).write_text(report + "\n", encoding="utf-8")
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
