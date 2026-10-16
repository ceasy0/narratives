"""The woodcut look of the Opening's beats 1-4, after Paul Nash's Genesis (1924): the style test
(PLAN §4, "The woodcut, made"; FOUNDATIONS §4, "The abstract look"; REFERENCES, beat 1).

    blender -b --factory-startup -P woodcut_test.py               the still, the clip, the flash check
    blender -b --factory-startup -P woodcut_test.py -- still      the still only
    blender -b --factory-startup -P woodcut_test.py -- clip       the clip and the flash check only
    blender -b --factory-startup -P woodcut_test.py -- preview    one small frame, to tune by
    blender -b --factory-startup -P woodcut_test.py -- fresh      take the head again from face_test's .blend

Beat 1 at about 0:26: the face rising under the flowing static, unmistakable by now. Everything
is cut white out of black. The static is a sheet of sand, and the face (face_test.py's head,
appended read-only from a copy of its .blend; eyes closed, no hair) pushes up through it, its
mask first, the sand smoothing its small forms and piling round it. One raking light, from beyond
the head and to the left, catches the forms.

Blender gives the cut its two inputs (Cycles, one sample a point, so every value is exact):
- where each point of the sheet lies among the cuts: the cut lines run with the static's flow,
  left to right with slow eddies in it, and each is pushed across the flow by the height under
  it, so the lines bend over the face's contours as Nash's bend over his swells;
- how much light reaches it: the raking sun on the static's own grain, with a little of the
  grain's own light, so the shadows are black and the lit planes white.
The cut (numpy, here) turns those into white lines: as wide as the light, tapering at each end
like a graver's stroke, short in the static and long over the face, each edge gouged on its own.
Nothing outlines the face; it's seen by how the lines bend over it and how wide the light makes
them. Where they'd crowd closer than a hand could cut, every other line gives way.

On twos: the sheet, the flow, the rise and the cut change twelve times a second, and each
drawing is re-cut with a new seed, so the lines boil a little at their edges, like hand-drawn
animation; the lines stay where they are, so the big black and white masses hold still. The
camera moves smoothly on every frame. Then the flash check: frame-to-frame luminance change,
against the general flash limits (WCAG 2.3.1; Ofcom's thresholds are the same, over more area).

The look itself is in woodcut.py. Writes work/woodcut/woodcut-still.png (1920x1080), woodcut-clip.mp4 and its frames,
woodcut-board.png (the still beside Nash's two), woodcut-flash.txt.
"""
import math
import pathlib
import subprocess
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402
import woodcut as WC  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW, FRESH = "preview" in ARGS, "fresh" in ARGS
DO_STILL = "still" in ARGS or not ("clip" in ARGS or PREVIEW)
DO_CLIP = "clip" in ARGS or not ("still" in ARGS or PREVIEW)
OUT = WC.BASE
REFS = O.OPENING / "references" / "img"
NASH = [REFS / "01-nash-face-of-the-waters-wellcome.jpg", REFS / "02-nash-light-from-darkness-wellcome.jpg"]
FPS = O.FPS
FRAMES, TWOS = 2 * FPS, 2                         # two seconds, a new drawing every second frame
STILL_AT = FPS                                    # the still is the clip's middle drawing
W, H = (960, 540) if PREVIEW else (1920, 1080)
K_CLIP, K_STILL = (2, 2) if PREVIEW else (4, 4)   # samples a side in each pixel, for the cut's edges
RISE = (0.048, 0.0025)                            # the nose's height above the sand, and how much it rises a second


def aim(cam, f):
    """The camera on frame f: smooth, on every frame. A slow push in, drifting a little left and
    lifting, looking down on the face from just past its chin."""
    u = f / FRAMES
    target = Vector((0.004 - 0.008 * u, -0.014, 0.018))
    tilt, dist = math.radians(18 + 2.5 * u), 0.90 - 0.05 * u
    cam.location = target + Vector((0.012 * u, -math.sin(tilt) * dist, math.cos(tilt) * dist))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()


# ---------------------------------------------------------------- run
t_start = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
OUT.mkdir(parents=True, exist_ok=True)
FACE = WC.face_depth(FRESH)
block = WC.build_sheet()
DATA, LIT = WC.materials()
cam = WC.setup(scene)
print("built in %.0fs" % (time.time() - t_start))


def frame(f, K, drawn):
    """Frame f at K samples a side; the drawing is remade only when it changes (on twos)."""
    m = f // TWOS
    if drawn.get("m") != m:
        t = time.time()
        t_ = m * TWOS / FPS
        Z, cut, grain, _ = WC.drawing(FACE, RISE[0] + RISE[1] * t_, t_)
        WC.set_drawing(block, Z, cut, grain)
        drawn["m"] = m
        print("  drawing %d in %.1fs" % (m, time.time() - t))
    aim(cam, f)
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = W * K, H * K, 100
    t = time.time()
    block.data.materials.clear()
    block.data.materials.append(DATA)
    data = WC.render_exr(scene, OUT / "pass-data.exr")
    block.data.materials.clear()
    block.data.materials.append(LIT)
    light = WC.render_exr(scene, OUT / "pass-light.exr")
    print("  passes in %.1fs; light %s" % (time.time() - t, np.percentile(light[..., 0], [1, 50, 99, 99.9]).round(3)))
    if PREVIEW:
        WC.write_png(OUT / "woodcut-preview-light.png", np.clip(light[::K, ::K, 0] / 1.3, 0, 1) ** (1 / 2.2))
    return WC.cut(data[..., 0] - 4000.0, data[..., 1] - 4000.0, WC.tone_of(data, light), m, K)


if PREVIEW:
    img = frame(STILL_AT, K_STILL, {})
    WC.write_png(OUT / "woodcut-preview.png", img)
    print("preview in %.0fs" % (time.time() - t_start))
    sys.exit(0)
if DO_STILL:
    t = time.time()
    still = OUT / "woodcut-still.png"
    WC.write_png(still, frame(STILL_AT, K_STILL, {}))
    print("still in %.0fs" % (time.time() - t))
    board = OUT / "woodcut-board.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(still), "-i", str(NASH[0]), "-i", str(NASH[1]),
                    "-filter_complex", "[0]scale=-2:1080,format=gray[a];[1]scale=-2:1080,format=gray[b];"
                    "[2]scale=-2:1080,format=gray[c];[a][b][c]hstack=3", str(board)], check=True)
    print("board", board)
if DO_CLIP:
    frames_dir = OUT / "frames"
    frames_dir.mkdir(exist_ok=True)
    drawn, frames = {}, []
    t = time.time()
    for f in range(FRAMES):
        img = frame(f, K_CLIP, drawn)
        frames.append(img)
        WC.write_png(frames_dir / ("%04d.png" % f), img)
        print("frame %d/%d, %.0fs so far" % (f + 1, FRAMES, time.time() - t))
    print("frames %.0fs, %.1fs a frame" % (time.time() - t, (time.time() - t) / FRAMES))
    clip = OUT / "woodcut-clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames_dir / "%04d.png"),
                    "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(clip)], check=True)
    print("clip", clip)
    report = WC.flash_check([np.round(f * 255) / 255 for f in frames], FPS)
    (OUT / "woodcut-flash.txt").write_text(report + "\n", encoding="utf-8")
    print(report.split("\n\nframe")[0])
print("done in %.0fs" % (time.time() - t_start))
