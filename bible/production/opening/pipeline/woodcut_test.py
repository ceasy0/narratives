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
like a graver's stroke, short in the static and long over the face, with gouged, uneven edges.
Nothing outlines the face; it's seen by how the lines bend over it and how wide the light makes
them. Where the lines would crowd closer than the hand could cut, they're left black.

On twos: the sheet, the flow, the rise and the cut change twelve times a second, and each
drawing is re-cut with a new seed, so the lines boil a little at their edges, like hand-drawn
animation; the lines stay where they are, so the big black and white masses hold still. The
camera moves smoothly on every frame. Then the flash check: frame-to-frame luminance change,
against the general flash limits (WCAG 2.3.1; Ofcom's thresholds are the same, over more area).

Writes work/woodcut/woodcut-still.png (1920x1080), woodcut-clip.mp4 and its frames,
woodcut-board.png (the still beside Nash's two), woodcut-flash.txt.
"""
import math
import pathlib
import shutil
import struct
import subprocess
import sys
import time
import zlib

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW, FRESH = "preview" in ARGS, "fresh" in ARGS
DO_STILL = "still" in ARGS or not ("clip" in ARGS or PREVIEW)
DO_CLIP = "clip" in ARGS or not ("still" in ARGS or PREVIEW)
OUT = O.WORK / "woodcut"
SRC = O.WORK / "styletest" / "face.blend"         # face_test.py's head: copied, never written
SNAP = OUT / "face-src.blend"
REFS = O.OPENING / "references" / "img"
NASH = [REFS / "01-nash-face-of-the-waters-wellcome.jpg", REFS / "02-nash-light-from-darkness-wellcome.jpg"]
FPS = O.FPS
FRAMES, TWOS = 2 * FPS, 2                         # two seconds, a new drawing every second frame
STILL_AT = FPS                                    # the still is the clip's middle drawing
W, H = (960, 540) if PREVIEW else (1920, 1080)
K_CLIP, K_STILL = (2, 2) if PREVIEW else (3, 4)   # samples a side in each pixel, for the cut's edges

# The block (metres; the face is about 0.24 m from chin to hairline)
SP = 0.0021                                       # the cuts' spacing: about eight pixels at this framing
BEND = 0.70                                       # how far a line is pushed across the flow by the height under it
SUN = Vector((-0.38, 0.80, 0.46)).normalized()    # toward the one light: beyond the head and to the left; 26 degrees up
GLOW = 0.10                                       # the static's own light, under the sun's
V_GRAIN, V_SWELL, V_EDDY = 0.05, 0.015, 0.03      # how fast the flow carries each (m/s), left to right
SWELL = (0.010, 0.12, 0.024)                      # the static's swells: height, length, breadth (m)
RISE = (0.048, 0.0025)                            # the nose's height above the sand, and how much it rises a second
SKIRT = (16, 0.6)                                 # the sand piled round the face: how far (cells of 0.5 mm), how high
# The cut
WIDTH = 0.42                                      # half-width of a line in full light, in spacings
THINNEST = 1.1                                    # the finest line a graver cuts, in pixels at 1920; thinner isn't cut
TONE = (0.38, 0.92)                               # light below the first is black; above the second, the widest cut
STROKE, STROKE_FACE = (5.0, 24.0), 2.5            # stroke lengths in spacings; how much longer over the face
INK, PAPER = 0.035, 0.92                          # the print's black and white, as on screen

def ramp01(a, b, x):
    u = np.clip((x - a) / (b - a), 0.0, 1.0)
    return u * u * (3 - 2 * u)


def hash2(ix, iy, seed):
    """A repeatable random number in [0, 1) for each pair of integer arrays."""
    h = (np.asarray(ix, np.int64) * 73856093) ^ (np.asarray(iy, np.int64) * 19349663) ^ (seed * 83492791 + 2654435769)
    h = (h & 0xFFFFFFFF).astype(np.uint32)
    for m in (0x7FEB352D, 0x846CA68B):
        h ^= h >> np.uint32(16)
        h *= np.uint32(m)
    h ^= h >> np.uint32(16)
    return h.astype(np.float32) / np.float32(4294967296.0)


def noise2(x, y, seed, octaves=2):
    """Smooth value noise in [0, 1), a few octaves, each turned a little so no grid shows."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        a = 0.6 * o + 0.3
        u, v = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        iu, iv = np.floor(u), np.floor(v)
        fu, fv = u - iu, v - iv
        fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
        iu, iv = iu.astype(np.int64), iv.astype(np.int64)
        s = seed * 31 + o
        n = ((hash2(iu, iv, s) * (1 - fu) + hash2(iu + 1, iv, s) * fu) * (1 - fv)
             + (hash2(iu, iv + 1, s) * (1 - fu) + hash2(iu + 1, iv + 1, s) * fu) * fv)
        total, norm = total + amp * n, norm + amp
        amp *= 0.5
        x, y = x * 2.03, y * 2.03
    return total / norm


def blur(a, sigma):
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    for axis in (0, 1):
        p = np.pad(a, [(r, r) if i == axis else (0, 0) for i in (0, 1)], mode='edge')
        n = a.shape[axis]
        a = sum(k[i] * (p[i:i + n] if axis == 0 else p[:, i:i + n]) for i in range(2 * r + 1))
    return a


# ---------------------------------------------------------------- the face, as heights
def face_depth():
    """How far forward each point of face_test's head stands, looking at it straight on: rays from
    in front over a 0.5 mm grid. The head is appended from a copy of face_test's .blend, so that
    file is only ever read."""
    cache = OUT / "face-depth.npz"
    if cache.exists() and not FRESH:
        z = np.load(cache)
        return z["D"], float(z["dx"]), float(z["u0"]), float(z["v0"])
    if FRESH or not SNAP.exists():
        shutil.copy2(SRC, SNAP)
    with bpy.data.libraries.load(str(SNAP), link=False) as (src, dst):
        dst.objects = [n for n in ("Human", "Human.rig", "Human.high-poly") if n in src.objects]
    for ob in dst.objects:
        bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    human, eyes = bpy.data.objects["Human"], bpy.data.objects["Human.high-poly"]
    ev = eyes.evaluated_get(dg)
    em = ev.to_mesh()
    E = sum((eyes.matrix_world @ v.co for v in em.vertices), Vector()) / len(em.vertices)   # between the eyes
    ev.to_mesh_clear()
    bvh = BVHTree.FromObject(human, dg)
    MW = human.matrix_world.copy()
    inv = MW.inverted()
    ray = (inv.to_3x3() @ Vector((0, 1, 0))).normalized()
    dx, u0, v0 = 0.0005, -0.15, -0.21
    us = u0 + dx * np.arange(601)
    vs = v0 + dx * np.arange(761)
    D = np.full((len(vs), len(us)), -1.0, np.float32)
    t = time.time()
    for j, v in enumerate(vs):
        for i, u in enumerate(us):
            hit = bvh.ray_cast(inv @ Vector((E.x + u, E.y - 0.5, E.z + v)), ray)[0]
            if hit is not None:
                D[j, i] = E.y - (MW @ hit).y
    print("face depth: %d rays in %.0fs; nose %.3f m in front of the eyes" % (D.size, time.time() - t, D.max()))
    for ob in list(dst.objects):
        bpy.data.objects.remove(ob)
    np.savez(cache, D=D, dx=dx, u0=u0, v0=v0)
    return D, dx, u0, v0


# ---------------------------------------------------------------- the sheet
def axis(lo, hi, flo, fhi, fine, coarse):
    """Grid lines from lo to hi, fine between flo and fhi (the face), coarse outside."""
    return np.concatenate([np.arange(lo, flo, coarse), np.arange(flo, fhi, fine), np.arange(fhi, hi + 1e-9, coarse)])


XS = axis(-0.42, 0.42, -0.13, 0.13, 0.00045, 0.0012)
YS = axis(-0.30, 0.34, -0.20, 0.16, 0.00045, 0.0012)
X, Y = np.meshgrid(XS.astype(np.float32), YS.astype(np.float32))


def sample(A, dx, u0, v0, x, y):
    """Bilinear lookup of grid A (origin u0, v0; cell dx) at x, y; zero outside."""
    fi, fj = (x - u0) / dx, (y - v0) / dx
    inside = (fi >= 0) & (fj >= 0) & (fi < A.shape[1] - 1) & (fj < A.shape[0] - 1)
    i0 = np.clip(np.floor(fi).astype(np.int64), 0, A.shape[1] - 2)
    j0 = np.clip(np.floor(fj).astype(np.int64), 0, A.shape[0] - 2)
    a, b = np.clip(fi - i0, 0, 1), np.clip(fj - j0, 0, 1)
    v = ((A[j0, i0] * (1 - a) + A[j0, i0 + 1] * a) * (1 - b) + (A[j0 + 1, i0] * (1 - a) + A[j0 + 1, i0 + 1] * a) * b)
    return np.where(inside, v, 0.0).astype(np.float32)


def drawing(t, face):
    """The block at time t: the sheet's heights, the cut's coordinates and the static's grain."""
    D, dx, u0, v0 = face
    level = D.max() - (RISE[0] + RISE[1] * t)
    v = v0 + dx * np.arange(D.shape[0])[:, None]
    u = u0 + dx * np.arange(D.shape[1])[None, :]
    D = D - 0.035 * ramp01(0.04, 0.10, v) - 0.02 * ramp01(0.055, 0.075, np.abs(u))   # the skull and the sides sink: the face's mask comes up
    r = 0.0025                                                     # the sand rounds the face's edges
    F = r * np.log1p(np.exp(np.clip((D - level) / r, -60, 60)))
    F = blur(F, 2.0)                                               # and smooths its small forms
    F = np.maximum(F, SKIRT[1] * blur(F, SKIRT[0]))                # and piles against it
    Fs = sample(F, dx, u0, v0, X, Y)
    out = ramp01(0.0, 0.006, Fs)                                   # where the face is out of the sand
    swell = SWELL[0] * (noise2((X - V_SWELL * t) / SWELL[1], Y / SWELL[2], 1) - 0.5) * (1 - 0.75 * out)
    Z = Fs + swell
    eddy = 0.008 * (noise2((X - V_EDDY * t) / 0.09, Y / 0.07, 2) - 0.5) * (1 - 0.6 * out)
    phi = (Y - BEND * Z + eddy) / SP
    s = (X - V_GRAIN * t) / SP / (1 + (STROKE_FACE - 1) * out)
    g = noise2((X - V_GRAIN * t) / 0.03, Y / 0.011, 3)
    grain = (0.66 + 0.45 * g) * (1 - out) + (0.95 + 0.15 * g) * out
    return Z, np.stack([phi, s, np.zeros_like(s)], -1), grain


def build_sheet():
    nx, ny = len(XS), len(YS)
    me = bpy.data.meshes.new("Block")
    me.vertices.add(nx * ny)
    me.vertices.foreach_set("co", np.stack([X, Y, np.zeros_like(X)], -1).ravel())
    i = (np.arange(ny - 1)[:, None] * nx + np.arange(nx - 1)[None, :]).ravel()
    quads = np.stack([i, i + 1, i + 1 + nx, i + nx], -1).ravel()
    me.loops.add(len(quads))
    me.loops.foreach_set("vertex_index", quads.astype(np.int32))
    me.polygons.add(len(i))
    me.polygons.foreach_set("loop_start", np.arange(0, len(quads), 4, dtype=np.int32))
    me.update(calc_edges=True)
    me.shade_smooth()
    me.attributes.new("cut", 'FLOAT_VECTOR', 'POINT')
    me.attributes.new("grain", 'FLOAT_COLOR', 'POINT')
    ob = bpy.data.objects.new("Block", me)
    bpy.context.scene.collection.objects.link(ob)
    print("block: %d x %d points" % (nx, ny))
    return ob


def set_drawing(ob, Z, cut, grain):
    me = ob.data
    me.vertices.foreach_set("co", np.stack([X, Y, Z], -1).ravel())
    me.attributes["cut"].data.foreach_set("vector", cut.reshape(-1).astype(np.float32) + 4000.0)   # kept positive
    g = grain.reshape(-1)
    me.attributes["grain"].data.foreach_set("color", np.stack([g, g, g, np.ones_like(g)], -1).ravel())
    me.update()


def materials():
    """Two looks at the block: its cut coordinates as light (exact, unlit), and the light on its grain."""
    data = bpy.data.materials.new("Cut data")
    lit = bpy.data.materials.new("Lit grain")
    for m in (data, lit):
        m.use_nodes = True
        m.node_tree.nodes.clear()
        m.cycles.emission_sampling = 'NONE'                        # not a light: the block is two million triangles
    nt = data.node_tree
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = "cut"
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(a.outputs["Vector"], em.inputs["Color"])
    nt.links.new(em.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    nt = lit.node_tree
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = "grain"
    di = nt.nodes.new("ShaderNodeBsdfDiffuse")
    nt.links.new(a.outputs["Color"], di.inputs["Color"])
    em = nt.nodes.new("ShaderNodeEmission")                        # the static's own faint light
    nt.links.new(a.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = GLOW
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(di.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    return data, lit


def setup(scene):
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for dv in prefs.devices:
        dv.use = dv.type == 'OPTIX'
    c = scene.cycles
    c.device = 'GPU'
    c.samples = 1
    c.use_adaptive_sampling = False
    c.use_denoising = False
    c.max_bounces = 0                                              # the sun's direct light only
    c.pixel_filter_type = 'BOX'
    c.filter_width = 0.01                                          # one exact point a sample
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    s = scene.render.image_settings
    s.media_type = 'IMAGE'
    s.file_format = 'OPEN_EXR'
    s.color_depth = '32'
    s.exr_codec = 'NONE'
    s.color_mode = 'RGB'
    sun = bpy.data.objects.new("Raking light", bpy.data.lights.new("Raking light", 'SUN'))
    sun.data.energy, sun.data.angle = math.pi, 0.0                 # a white plane square to it reads 1
    sun.rotation_euler = SUN.to_track_quat('Z', 'Y').to_euler()
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.data.lens, cam.data.sensor_width, cam.data.clip_start = 60.0, 36.0, 0.05
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def aim(cam, f):
    """The camera on frame f: smooth, on every frame. A slow push in, drifting a little left and
    lifting, looking down on the face from just past its chin."""
    u = f / FRAMES
    target = Vector((0.004 - 0.008 * u, -0.014, 0.018))
    tilt, dist = math.radians(18 + 2.5 * u), 0.90 - 0.05 * u
    cam.location = target + Vector((0.012 * u, -math.sin(tilt) * dist, math.cos(tilt) * dist))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()


def render_exr(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    path.unlink()
    return a.reshape(h, w, 4)[::-1, :, :3]


# ---------------------------------------------------------------- the cut
N0, NN = -600, 1200                    # the line numbers the tables cover
A0, NA = -6000, 12000                  # and the cells along each line
S0, NS = -2000, 4000                   # and the strokes along each line


class Hand:
    """The cutter. For the block, fixed: each line's small offset from even spacing, each
    stroke's length, start and weight. For each drawing, new: the wobble of the hand along a line,
    where each stroke ends to within a little, and the gouged edges."""

    def __init__(self, seed):
        r = np.random.default_rng(seed)
        self.jit, self.len, self.off = r.random(NN, np.float32), r.random(NN, np.float32), r.random(NN, np.float32)
        self.wgt = r.random((NN, 64), np.float32)
        self.seed = seed

    def recut(self, drawing):
        if getattr(self, "drawing", None) == drawing:
            return
        self.drawing = drawing
        r = np.random.default_rng((self.seed, drawing))
        self.wob, self.edge, self.nick = (r.random((NN, NA), np.float32) for _ in range(3))
        self.shift = r.random(NN, np.float32)


def along(tab, row, x):
    i = np.floor(x)
    f = x - i
    f = f * f * (3 - 2 * f)
    i = np.clip(i.astype(np.int64) - A0, 0, NA - 2)
    a, b = tab[row, i], tab[row, i + 1]
    return a + (b - a) * f


def cut_set(phi, s, tone, thin, width, hand, stroke):
    """White where a cut is: lines along phi's level sets, strokes along s, each line checked
    against the three nearest."""
    white = np.zeros(phi.shape, bool)
    base = np.floor(phi).astype(np.int64)
    for k in (-1, 0, 1):
        n = base + k
        row = np.clip(n - N0, 0, NN - 1)
        centre = n + 0.5 + (hand.jit[row] - 0.5) * 0.45 + (along(hand.wob, row, s / 7.0) - 0.5) * 0.12
        d = np.abs(phi - centre)
        L = stroke[0] + (stroke[1] - stroke[0]) * hand.len[row]
        x = s / L + hand.off[row] * 7.0 + (hand.shift[row] - 0.5) * 0.08
        seg = np.floor(x)
        u = (x - seg) / 0.88                                       # the last eighth of each stroke's room is a gap
        prof = np.where(u < 0.18, np.sqrt(np.clip(u / 0.18, 0, 1)), np.clip((1 - u) / 0.82, 0, 1) ** 0.7)
        wgt = 0.7 + 0.6 * hand.wgt[row, seg.astype(np.int64) % 64]
        edge = (1 + 0.32 * (along(hand.edge, row, s * 1.6) * 2 - 1)
                + 0.28 * (along(hand.nick, row, s * 5.0) * 2 - 1))
        w = width * tone * prof * wgt * edge
        white |= d < np.where(w > 0.6 * thin, np.maximum(w, thin), 0.0)
    return white


HAND = Hand(1)


def cut(data, light, drawing, K):
    """The print, at W x H, from the passes at K samples a side."""
    t0 = time.time()
    phi, s = data[..., 0] - 4000.0, data[..., 1] - 4000.0
    tone = ramp01(TONE[0], TONE[1], light[..., 0])
    gy, gx = np.gradient(phi)
    per = 1920 / W / (np.hypot(gx, gy) * K + 1e-6)                 # the spacing on screen, in pixels at 1920
    tone *= np.where(per > 0.8 / K, ramp01(2.2, 3.4, per), 1.0)    # too close to cut: left black (not at a fold)
    HAND.recut(drawing)
    lit = tone > 1e-3
    white = np.zeros(phi.shape, bool)
    white[lit] = cut_set(phi[lit], s[lit], tone[lit], 0.5 * THINNEST / per[lit], WIDTH, HAND, STROKE)
    cov = white.reshape(H, K, W, K).mean(axis=(1, 3))
    print("  cut in %.1fs (%.0f%% lit)" % (time.time() - t0, 100 * lit.mean()))
    return INK + (PAPER - INK) * cov


def write_png(path, img):
    """An 8-bit grey PNG (Blender's own saving would put its colour management on it)."""
    a = np.clip(np.round(img * 255), 0, 255).astype(np.uint8)
    h, w = a.shape
    raw = b"".join(b"\x00" + row.tobytes() for row in a)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- the flash check
def lum(v):
    """Relative luminance of an sRGB grey."""
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def flash_check(frames):
    """General flashes: a pair of opposing changes of 10% or more of the maximum relative luminance,
    the darker below 0.8, over 25% of any 10-degree field (WCAG 2.3.1's 341 x 256 at 1024 x 768,
    so 639 x 360 here; Ofcom's 25% of the screen is the looser of the two) -- at most three a second.
    Each pixel's changes are followed from extreme to extreme, so a slow change still counts."""
    Y = [lum(f.astype(np.float32)) for f in frames]
    h, w = Y[0].shape
    fw, fh = round(w * 341 / 1024), round(h * 256 / 768)
    lo, hi = Y[0].copy(), Y[0].copy()
    state = np.zeros((h, w), np.int8)
    rows, worst, ends = [], (0.0, 0), []
    for i in range(1, len(Y)):
        y = Y[i]
        lo, hi = np.minimum(lo, y), np.maximum(hi, y)
        up = (state != 1) & (y - lo >= 0.1) & (lo < 0.8)
        down = (state != -1) & (hi - y >= 0.1) & (y < 0.8)
        state[up], state[down] = 1, -1
        lo[up | down], hi[up | down] = y[up | down], y[up | down]
        best = 0.0
        for m in (up, down):                                       # the worst 10-degree field, each way
            c = np.pad(m.astype(np.float32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
            a = (c[fh:, fw:] - c[:-fh, fw:] - c[fh:, :-fw] + c[:-fh, :-fw])[::20, ::20] / (fw * fh)
            best = max(best, float(a.max()))
        mean_change = float(np.abs(y - Y[i - 1]).mean())
        rows.append((i, float(up.mean()), float(down.mean()), best, mean_change, float(Y[i].mean())))
        ends.append(best >= 0.25)
        worst = max(worst, (best, i))
    per_sec = max(sum(ends[j:j + FPS]) for j in range(max(1, len(ends) - FPS + 1))) / 2.0
    # where the change is: at the lines' edges, or inside the masses?
    edge_share = []
    for i in range(1, len(frames)):
        a, b = frames[i - 1] > 0.5, frames[i] > 0.5
        changed = a != b
        if changed.any():
            p = np.pad(a, 2, mode='edge')
            mixed = np.zeros_like(a)
            for dy in range(5):
                for dx in range(5):
                    mixed |= p[dy:dy + a.shape[0], dx:dx + a.shape[1]] != a
            edge_share.append(float((changed & mixed).sum() / changed.sum()))
    means = [r[5] for r in rows]
    lines = ["Flash check, %s, %d frames at %d fps (%dx%d)" % (time.strftime("%Y-%m-%d %H:%M"), len(frames), FPS, w, h),
             "",
             "Frame mean relative luminance: %.3f to %.3f (largest frame-to-frame step %.4f)"
             % (min(means), max(means), max(abs(a - b) for a, b in zip(means, means[1:])) if len(means) > 1 else 0.0),
             "Largest share of the screen changing by 10%% or more in one direction: %.1f%% brighter, %.1f%% darker"
             % (100 * max(r[1] for r in rows), 100 * max(r[2] for r in rows)),
             "Largest share of any 10-degree field (%dx%d) in one transition: %.1f%% (frame %d); the limit is 25%%"
             % (fw, fh, 100 * worst[0], worst[1]),
             "Frames with a general-flash transition: %d; worst 1-second window: %.1f flashes (limit 3)"
             % (sum(ends), per_sec),
             "Changed pixels within 2 px of a line's edge in the frame before: %.1f%% (mean), %.1f%% (worst frame)"
             % (100 * np.mean(edge_share), 100 * min(edge_share)) if edge_share else "No pixel changed",
             "Verdict: %s" % ("PASSES the general flash limits" if per_sec <= 3 and worst[0] < 0.25 else
                              "FAILS the general flash limits"),
             "",
             "frame  brighter%  darker%  worst-field%  mean|dY|  meanY"]
    lines += ["%5d  %8.2f  %7.2f  %11.2f  %8.4f  %.3f" % (i, 100 * u, 100 * d, 100 * b, m, y) for i, u, d, b, m, y in rows]
    return "\n".join(lines)


# ---------------------------------------------------------------- run
t_start = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS
OUT.mkdir(parents=True, exist_ok=True)
FACE = face_depth()
block = build_sheet()
DATA, LIT = materials()
cam = setup(scene)
print("built in %.0fs" % (time.time() - t_start))


def frame(f, K, drawn):
    """Frame f at K samples a side; the drawing is remade only when it changes (on twos)."""
    m = f // TWOS
    if drawn.get("m") != m:
        t = time.time()
        set_drawing(block, *drawing(m * TWOS / FPS, FACE))
        drawn["m"] = m
        print("  drawing %d in %.1fs" % (m, time.time() - t))
    aim(cam, f)
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = W * K, H * K, 100
    t = time.time()
    block.data.materials.clear()
    block.data.materials.append(DATA)
    data = render_exr(scene, OUT / "pass-data.exr")
    block.data.materials.clear()
    block.data.materials.append(LIT)
    light = render_exr(scene, OUT / "pass-light.exr")
    print("  passes in %.1fs; light %s" % (time.time() - t, np.percentile(light[..., 0], [1, 50, 99, 99.9]).round(3)))
    if PREVIEW:
        write_png(OUT / "woodcut-preview-light.png", np.clip(light[::K, ::K, 0] / 1.3, 0, 1) ** (1 / 2.2))
    return cut(data, light, m, K)


if PREVIEW:
    img = frame(STILL_AT, K_STILL, {})
    write_png(OUT / "woodcut-preview.png", img)
    print("preview in %.0fs" % (time.time() - t_start))
    sys.exit(0)
if DO_STILL:
    t = time.time()
    still = OUT / "woodcut-still.png"
    write_png(still, frame(STILL_AT, K_STILL, {}))
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
        write_png(frames_dir / ("%04d.png" % f), img)
        print("frame %d/%d, %.0fs so far" % (f + 1, FRAMES, time.time() - t))
    print("frames %.0fs, %.1fs a frame" % (time.time() - t, (time.time() - t) / FRAMES))
    clip = OUT / "woodcut-clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames_dir / "%04d.png"),
                    "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(clip)], check=True)
    print("clip", clip)
    report = flash_check([np.round(f * 255) / 255 for f in frames])
    (OUT / "woodcut-flash.txt").write_text(report + "\n", encoding="utf-8")
    print(report.split("\n\nframe")[0])
print("done in %.0fs" % (time.time() - t_start))
