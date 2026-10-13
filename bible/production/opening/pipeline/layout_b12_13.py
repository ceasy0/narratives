"""Layout of beat 12 into beat 13 (03:42-04:36), in grey, at true scale.

    blender -b --factory-startup -P layout_b12_13.py            build the scene and save it
    blender -b --factory-startup -P layout_b12_13.py -- render  build, save, and render the playblast

Writes work/layout/b12-13-layout.blend and work/playblast/1200-1395-layout.mp4
(960x540, Workbench, with the timecode, shot number, camera and lens burned in).

The world, in metres, Z up. The camera always faces east (+X), so north (+Y) is
screen left and the band runs toward +Y. Scene frames are film frames.
Everything is a number below: change it and run the script again.
"""
import math
import random
import sys
import pathlib

import bpy
import bmesh
from mathutils import Matrix, Vector
from bpy_extras import anim_utils

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402

RENDER = "render" in sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else False
random.seed(12)

F0, F1 = O.frame("03:42"), O.frame("04:36")       # 5328 .. 6624 (end exclusive)
T0 = O.frame("04:00")                             # the first footfall: t = 0
FR = list(range(F0, F1 + 1))


def T(tc):
    """Seconds from 04:00 for a timecode."""
    return (O.frame(tc) - T0) / O.FPS


def fr(t):
    return T0 + t * O.FPS


def smooth(a, b, x):
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


# ---------------------------------------------------------------- the numbers
LENS = 35.0                    # mm, on a 36 mm sensor, for both cameras
LEAF = Vector((2.0, 1.6, 0.0))  # where the leaf lands; the band's lane runs over it
LANE_X = LEAF.x
LEAF_CAM = Vector((LEAF.x - 0.9, LEAF.y, 0.16))   # 0.9 m from the leaf, 16 cm off the ground
SKULL_CAM_A = Vector((-4.2, -0.3, 0.9))           # 03:42
SKULL_CAM_B = Vector((-3.4, -0.3, 0.9))           # 03:52, a slow push in
LEAF_FALL = (T("03:54"), T("03:57:14"))           # falls 1.3 m, settles; still until 04:00
PULL_BACK = (T("04:01:12"), T("04:03:12"))        # the low camera lifts and joins the run

# The band's speed, m/s, at seconds from 04:00 (linear between the points).
SPEED = [(-3, 5.0), (1.5, 5.0), (2.5, 4.5), (10, 4.5), (10.5, 3.5), (14, 3.5), (14.5, 4.0),
         (17, 4.0), (17.4, 3.0), (20, 3.0), (22, 1.8), (26, 1.8), (27, 1.6), (33, 1.6), (36, 1.2)]
# The tracking camera's distance from the lane, m, at seconds from 04:00.
CAM_DIST = [(3.5, 6.5), (9.5, 6.5), (11, 8.0), (13.5, 8.0), (15, 6.5), (16.5, 6.5), (17.5, 8.5), (20, 8.5), (22, 5.0), (26.5, 5.0), (27.5, 6.0),
            (30.5, 6.0), (33, 10.0), (36, 10.0)]
# How far ahead of the band's centre the camera looks, m: it drops back to the rear for the
# cat (04:10-04:14), then up the line with the newborn (04:22-04:26), lets the line walk through the frame past the grave, then catches up.
CAM_AHEAD = [(3.5, 1.0), (9.5, 1.0), (11, -2.0), (13.5, -2.0), (15, 1.0), (20, 1.0), (22, -3.4), (26, 3.2), (30.5, -1.0), (33, 1.0), (36, 1.0)]
CAM_HEIGHT = 1.5
ZONES = {"forest": (-25, 47), "woodland": (47, 86), "grassland": (86, 101), "dry": (101, 135)}
WIPES = [5.0, 8.0, 15.5, 21.0]  # seconds at which a trunk crosses the lens (a generation passes)


def curve(points, t, ease=False):
    if t <= points[0][0]:
        return points[0][1]
    for (a, va), (b, vb) in zip(points, points[1:]):
        if t <= b:
            return lerp(va, vb, smooth(a, b, t) if ease else (t - a) / (b - a))
    return points[-1][1]


# Band centre along the path: distance run since 04:00, by integrating SPEED.
DT = 1.0 / O.FPS
_dist = {}
_s = 0.0
for f in range(T0, F1 + 1):
    _dist[f] = _s
    _s += curve(SPEED, (f - T0) / O.FPS) * DT
_s = 0.0
for f in range(T0 - 1, F0 - 1, -1):
    _s -= curve(SPEED, (f - T0) / O.FPS) * DT
    _dist[f] = _s
LEAD = 3.0                                  # the lead runner is this far ahead of the centre
YC = {f: LEAF.y - LEAD + _dist[f] for f in FR}   # the lead runner's foot is on the leaf at 04:00


# ---------------------------------------------------------------- scene set-up
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.data.scenes[0]
scene.name = "B12-13 layout"
scene.render.fps = O.FPS
scene.frame_start, scene.frame_end = F0, F1 - 1
scene.unit_settings.system = 'METRIC'
world = bpy.data.worlds.new("Sky")
scene.world = world
col = scene.collection


def obj_from_bm(name, bm, color, parent=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(name, me)
    ob.color = (color, color, color, 1.0) if isinstance(color, float) else color
    col.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def empty(name, parent=None):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = 0.2
    col.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def cone(bm, base, r1, r2, h, seg=8, rot=None):
    """A cone or cylinder standing on `base`, h tall."""
    m = Matrix.Translation(Vector(base) + Vector((0, 0, h / 2)))
    if rot is not None:
        m = Matrix.Translation(Vector(base)) @ rot @ Matrix.Translation((0, 0, h / 2))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=h, matrix=m)


def ball(bm, centre, scale, seg=10):
    m = Matrix.Translation(Vector(centre)) @ Matrix.Diagonal(Vector(scale).to_4d())
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(4, seg // 2), radius=1.0, matrix=m)


def key(ob, path, frames, values, index=-1, target=None):
    """Bulk keyframes, linear. `values` is one list (index>=0) or a list of per-axis lists."""
    idb = target or ob
    series = [values] if index >= 0 else values
    idb.keyframe_insert(path, frame=frames[0])
    ad = idb.animation_data
    bag = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    for i, vals in enumerate(series):
        ix = index if index >= 0 else i
        fc = bag.fcurves.find(path, index=ix) or bag.fcurves.new(path, index=ix)
        n = len(frames)
        while len(fc.keyframe_points) > 0:
            fc.keyframe_points.remove(fc.keyframe_points[0], fast=True)
        fc.keyframe_points.add(n)
        flat = [0.0] * (2 * n)
        flat[0::2] = [float(f) for f in frames]
        flat[1::2] = [float(v) for v in vals]
        fc.keyframe_points.foreach_set('co', flat)
        fc.keyframe_points.foreach_set('interpolation', [1] * n)   # linear
        fc.update()


def key_scale(ob, pairs):
    fs = [fr(t) for t, _ in pairs]
    vs = [v for _, v in pairs]
    key(ob, "scale", fs, [vs, vs, vs])


def key_grey(ob, pairs):
    fs = [fr(t) for t, _ in pairs]
    vs = [v for _, v in pairs]
    key(ob, "color", fs, [vs, vs, vs, [1.0] * len(vs)])


# ---------------------------------------------------------------- the ground
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=400)
ground = obj_from_bm("Ground", bm, 0.42)

# Small things on the ground, so the travelling camera has something to travel past.
for zone, (y0, y1) in ZONES.items():
    bm = bmesh.new()
    n = {"forest": 1100, "woodland": 700, "grassland": 1500, "dry": 500}[zone]
    for _ in range(n):
        x, y = random.uniform(-4, 45), random.uniform(y0, y1)
        if abs(x - LANE_X) < 1.5 and random.random() < 0.8:
            continue
        if zone == "forest":       # ferns
            cone(bm, (x, y, 0), random.uniform(.25, .45), 0.05, random.uniform(.3, .6), 6)
        elif zone == "woodland":   # brush and stones
            cone(bm, (x, y, 0), random.uniform(.15, .5), 0.1, random.uniform(.15, .7), 6)
        elif zone == "grassland":  # tufts
            cone(bm, (x, y, 0), random.uniform(.08, .2), 0.0, random.uniform(.3, .8), 5)
        else:                      # stones
            cone(bm, (x, y, 0), random.uniform(.15, .6), random.uniform(.1, .3), random.uniform(.1, .35), 5)
    cover = obj_from_bm("Ground cover, " + zone, bm, 0.33)
    if zone == "forest":           # bare until the ferns come back at 03:49
        a, b = fr(T("03:49")), fr(T("03:50:12"))
        key(cover, "scale", [a, b], [[1, 1], [1, 1], [0, 1]])


# ---------------------------------------------------------------- trees
def tree_mesh(bm, base, h, r):
    cone(bm, base, r, r * 0.6, h * 0.7, 8)
    ball(bm, (base[0], base[1], base[2] + h * 0.78), (h * 0.24, h * 0.24, h * 0.22), 8)


def spaced(n, xr, yr, gap, keep_out=()):
    pts = []
    tries = 0
    while len(pts) < n and tries < n * 60:
        tries += 1
        p = (random.uniform(*xr), random.uniform(*yr))
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > gap * gap for q in pts) and \
           all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > q[2] ** 2 for q in keep_out):
            pts.append(p)
    return pts


# The forest the band runs through. Every tree here grows during 03:50:12-03:52,
# because the time-lapse camera sees it come up; the lane (x 0.6-3.2) is kept clear.
forest_trees = []
for x, y in spaced(150, (4.5, 62), (-28, 47), 3.0):
    h, r = random.uniform(11, 22), random.uniform(.2, .45)
    bm = bmesh.new()
    tree_mesh(bm, (0, 0, 0), h, r)
    ob = obj_from_bm("Tree", bm, random.uniform(.2, .3))
    ob.location = (x, y, 0)
    start = T("03:50:12") + random.uniform(0, 0.9)
    key_scale(ob, [(start - 1, 0.0), (start, 0.0), (start + 0.25, 0.25), (start + 0.6, 1.0)])
    forest_trees.append(ob)

bm = bmesh.new()
for x, y in spaced(32, (5, 60), (47, 86), 6.0):          # open woodland
    tree_mesh(bm, (x, y, 0), random.uniform(7, 14), random.uniform(.2, .4))
for x, y in spaced(4, (25, 60), (86, 100), 12.0):        # lone trees in the grass
    tree_mesh(bm, (x, y, 0), random.uniform(6, 9), .3)
far_trees = obj_from_bm("Trees beyond the forest", bm, 0.26)

# Ferns at the skull, which come first (03:49), before the trees.
ferns = []
for x, y in spaced(70, (-1.5, 22), (-11, 11), 0.9, keep_out=[(0, 0, 1.6)]):
    bm = bmesh.new()
    cone(bm, (0, 0, 0), random.uniform(.3, .5), 0.05, random.uniform(.4, .7), 7)
    ob = obj_from_bm("Fern", bm, 0.3)
    ob.location = (x, y, 0)
    start = T("03:49") + random.uniform(0, 1.1)
    key_scale(ob, [(start - 1, 0.0), (start, 0.0), (start + 0.4, 1.0)])
    ferns.append(ob)

# The tree that grows where the head lay: a shoot, a sapling, a tree, in two seconds.
bm = bmesh.new()
tree_mesh(bm, (0, 0, 0), 18.0, 0.3)
the_tree = obj_from_bm("The tree", bm, 0.24)
a = T("03:52")
key_scale(the_tree, [(a - 1, 0), (a, 0), (a + 0.4, 0.02), (a + 0.9, 0.12), (a + 1.5, 0.55), (a + 2.0, 1.0)])


# ---------------------------------------------------------------- the dead Triceratops
# A head 2.3 m long, lying on its side with the frill up, and the body behind it (south).
dead = empty("Dead Triceratops")
bm = bmesh.new()
cone(bm, (0, -0.9, 0.55), 0.55, 0.12, 1.5, 10, rot=Matrix.Rotation(math.radians(-90), 4, 'X'))   # snout
frill = Matrix.Rotation(math.radians(-70), 4, 'X')
cone(bm, (0, -0.95, 0.5), 1.0, 0.9, 0.12, 14, rot=frill)                                          # frill, up
for sx in (-0.35, 0.35):                                                                          # brow horns
    cone(bm, (sx, -0.5, 0.75), 0.11, 0.0, 0.9, 6, rot=Matrix.Rotation(math.radians(-55), 4, 'X'))
cone(bm, (0, 0.45, 0.62), 0.07, 0.0, 0.3, 6)                                                      # nose horn
head = obj_from_bm("Head", bm, 0.3, parent=dead)
head.rotation_euler = (0, math.radians(-75), 0)            # tipped onto its side
head.location = (0, 0, 0.35)
bm = bmesh.new()
ball(bm, (0.3, -4.6, 0.9), (1.1, 3.2, 0.95), 12)           # the body, about 6.5 m of it
body = obj_from_bm("Body", bm, 0.3, parent=dead)
# 03:44-03:48 the flesh goes and the skull shows; 03:46:12-03:49 it sinks.
key_grey(head, [(T("03:44"), 0.3), (T("03:46"), 0.8)])
key_scale(head, [(T("03:44"), 1.0), (T("03:46"), 0.9)])
fs = [fr(T("03:44")), fr(T("03:47"))]
key(body, "scale", fs, [[1, 0.9], [1, 0.85], [1, 0.12]])
key(dead, "location", [fr(T("03:46:12")), fr(T("03:49"))], [0.0, -1.9], index=2)

# Ash, lying over the place from 03:44, gone under the green by 03:50.
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, segments=32, radius=40)
ash = obj_from_bm("Ash", bm, 0.62)
key(ash, "location", [fr(T("03:44")), fr(T("03:45:12")), fr(T("03:49")), fr(T("03:50"))],
    [-0.05, 0.02, 0.02, -0.05], index=2)

# The last of the falling fire, far off in the east, stopping by 03:44.
for i in range(16):
    bm = bmesh.new()
    cone(bm, (0, 0, 0), 0.5, 0.1, 26, 5, rot=Matrix.Rotation(math.radians(24), 4, 'X'))
    st = obj_from_bm("Fire", bm, 0.95)
    y = random.uniform(-70, 70)
    t0 = T("03:42") - 0.4 + (i / 16.0) ** 1.6 * 2.2          # thinning out
    key(st, "location", [fr(t0 - 5), fr(t0), fr(t0 + 0.7), fr(t0 + 5)],
        [[150] * 4, [y, y, y - 34, y - 34], [70, 70, -30, -30]])

# Animals pass as blurs (03:50:12, 03:51:06): each crosses the frame in a few frames.
for tc, x, d in (("03:50:12", 6.0, 1), ("03:51:06", 9.0, -1)):
    bm = bmesh.new()
    ball(bm, (0, 0, 0.8), (0.45, 1.1, 0.6), 8)
    an = obj_from_bm("Animal passing", bm, 0.2)
    t = T(tc)
    key(an, "location", [fr(t - 4), fr(t), fr(t + 0.25), fr(t + 4)],
        [[x] * 4, [-16 * d, -16 * d, 16 * d, 16 * d], [0] * 4])

# The sky: light, dark from 03:44, clear from 03:49.
sky = [(T("03:42"), 0.50), (T("03:44"), 0.10), (T("03:49"), 0.10), (T("03:50:12"), 0.66)]
key(None, "color", [fr(t) for t, _ in sky], [[v for _, v in sky]] * 3, target=world)


# ---------------------------------------------------------------- the leaf
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, segments=10, radius=1.0,
                        matrix=Matrix.Diagonal((0.06, 0.035, 1, 1)))   # 12 cm by 7 cm
leaf = obj_from_bm("Leaf", bm, 0.08)
lf, lloc, lrot = [], [[], [], []], [[], [], []]
ta, tb = LEAF_FALL
for f in FR:
    t = (f - T0) / O.FPS
    if t < ta - 0.5:
        continue
    if t <= 0.04:                          # the slow fall, then stillness
        u = min(1.0, max(0.0, (t - ta) / (tb - ta)))
        sway = (1 - u) ** 0.8              # the rocking dies as it comes down
        ph = 2 * math.pi * 0.85 * (t - ta)
        z = 1.35 * (1 - u) ** 1.15 + 0.004 - 0.03 * sway * abs(math.sin(ph))
        p = (LEAF.x + 0.04 * sway * math.sin(ph * 0.5), LEAF.y + 0.24 * sway * math.sin(ph), max(z, 0.004))
        rot = (0.95 * sway * math.cos(ph), 0.25 * sway * math.sin(ph * 0.5), 0.6 * u)
    else:                                  # whipped up and away by the feet
        w = t - 0.04
        p = (LEAF.x - 0.25 * w, LEAF.y + 3.2 * w + 1.5 * w * w, 0.004 + 2.6 * w - 2.2 * w * w)
        rot = (14 * w, 9 * w, 0.6 + 6 * w)
        if p[2] < 0 or w > 1.4:
            break
    lf.append(f)
    for i in range(3):
        lloc[i].append(p[i])
        lrot[i].append(rot[i])
key(leaf, "location", lf, lloc)
key(leaf, "rotation_euler", lf, lrot)
key_scale(leaf, [(ta - 0.6, 1), ((lf[-1] - T0) / O.FPS, 1), ((lf[-1] - T0) / O.FPS + DT, 0)])

for i in range(7):                         # the kick of dust
    bm = bmesh.new()
    ball(bm, (0, 0, 0), (1, 1, 0.8), 6)
    d = obj_from_bm("Dust", bm, 0.6)
    t = 0.04 + i * 0.05
    y = LEAF.y + random.uniform(-0.2, 0.5)
    x = LEAF.x + random.uniform(-0.3, 0.3)
    key(d, "location", [fr(t), fr(t + 1.0)], [[x, x], [y, y + 0.9], [0.05, 0.45]])
    key_scale(d, [(t - 1, 0), (t, 0), (t + 0.12, 0.05), (t + 0.6, 0.14), (t + 1.0, 0.0)])


# ---------------------------------------------------------------- people
def figure(name, height, grey, spear=False):
    """A stand-in person at true scale, feet on the root's origin, facing +Y."""
    h = height
    root = empty(name)
    bm = bmesh.new()
    cone(bm, (0, 0, 0.50 * h), 0.085 * h, 0.105 * h, 0.33 * h, 8)        # torso
    ball(bm, (0, 0, 0.92 * h), (0.062 * h, 0.07 * h, 0.075 * h), 8)       # head
    cone(bm, (0, 0.045 * h, 0.90 * h), 0.02 * h, 0.0, 0.05 * h, 4,
         rot=Matrix.Rotation(math.radians(-90), 4, 'X'))                  # a nose, so facing reads
    body = obj_from_bm(name + " body", bm, grey, parent=root)
    limbs = []
    for kind, x, top, length, r in (("leg", 0.055, 0.50, 0.50, 0.04), ("leg", -0.055, 0.50, 0.50, 0.04),
                                    ("arm", 0.125, 0.81, 0.40, 0.027), ("arm", -0.125, 0.81, 0.40, 0.027)):
        bm = bmesh.new()
        cone(bm, (0, 0, -length * h), r * h * 0.8, r * h, length * h, 6)
        lm = obj_from_bm(name + " " + kind, bm, grey, parent=root)
        lm.location = (x * h, 0, top * h)
        limbs.append(lm)
    if spear:
        bm = bmesh.new()
        cone(bm, (0.2 * h, -0.9, 0.62 * h), 0.012, 0.012, 2.0, 5, rot=Matrix.Rotation(math.radians(-80), 4, 'X'))
        obj_from_bm(name + " spear", bm, 0.15, parent=body)
    return {"root": root, "body": body, "limbs": limbs, "h": h}


def animate(fig, frames, xs, ys, face=None, pose=None, visible=None):
    """Move a figure along (xs, ys) and swing its limbs by how far it has travelled.

    face: heading per frame (radians about Z, 0 = toward +Y). pose: per frame, None or a dict
    with 'z' (root height), 'lean' (radians, forward), 'legs' (radians, both legs), 'still'.
    """
    n = len(frames)
    face = face or [0.0] * n
    pose = pose or [None] * n
    loc = [[], [], []]
    rot = [[], [], []]
    swing = [[] for _ in range(4)]
    phase = 0.0
    for i in range(n):
        v = 0.0 if i == 0 else math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]) / DT
        run = min(1.0, max(0.0, (v - 1.6) / 2.9))             # 0 = a walk, 1 = a run
        cycle = lerp(1.5, 2.8, run)                           # metres per full stride cycle
        phase += 2 * math.pi * v * DT / cycle
        amp = lerp(0.42, 0.8, run) * min(1.0, v / 1.0)
        p = pose[i] or {}
        s = math.sin(phase)
        legs = p.get("legs")
        swing[0].append(s * amp if legs is None else legs)
        swing[1].append(-s * amp if legs is None else legs)
        swing[2].append(-s * amp * 0.9 if "arms" not in p else p["arms"])
        swing[3].append(s * amp * 0.9 if "arms" not in p else p["arms"])
        bob = 0.035 * run * abs(math.cos(phase)) * fig["h"] / 1.7
        loc[0].append(xs[i])
        loc[1].append(ys[i])
        loc[2].append(p.get("z", 0.0) + bob)
        rot[0].append(-(p.get("lean", lerp(0.04, 0.2, run))))
        rot[1].append(p.get("roll", 0.0))
        rot[2].append(face[i])
    key(fig["root"], "location", frames, loc)
    key(fig["root"], "rotation_euler", frames, rot)
    for lm, sw in zip(fig["limbs"], swing):
        key(lm, "rotation_euler", frames, sw, index=0)
    if visible:
        key_scale(fig["root"], visible)


PF = [f for f in FR if f >= fr(T("03:58"))]        # people exist from 03:58 (they are far off, right)
PT = [(f - T0) / O.FPS for f in PF]

# The band: ten people. (name, height m, lateral place in the pack, place along it, spear)
# Along: + is ahead (left). From 04:20 to 04:22 they fall into a single line, 0.9 m apart.
BAND = [("Lead man", 1.72, 0.0, 3.0, True), ("Woman A", 1.60, 0.7, 2.2, False),
        ("Woman B", 1.62, -0.6, 1.5, False), ("Woman C (centre)", 1.58, 0.2, 0.3, False),
        ("Man D", 1.74, 1.0, -0.2, True), ("Girl", 1.30, -0.3, -0.9, False),
        ("Woman E", 1.62, 0.6, -1.6, False), ("Man F", 1.68, -0.7, -2.2, True),
        ("Man G (rear)", 1.73, 0.4, -3.0, True), ("Man H (rear)", 1.70, -0.4, -3.6, True)]
LINE = {0: 2.7, 1: 3.6, 2: 1.8, 3: 0.9, 4: 0.0, 5: -0.9, 6: -1.8, 7: -2.7, 8: -3.6}   # index 9 falls at the clash
CAT_T = (T("04:10"), T("04:14"))
CLASH_T = (T("04:17"), T("04:20"))
BABY_T = (T("04:22"), T("04:26"))
GRAVE_T = (T("04:27"), T("04:30:12"))
GRAVE_UP = 29.4
GRAVE_WHO = 2
people = []
band_paths = {}
for i, (name, h, dx, dy, spear) in enumerate(BAND):
    fig = figure(name, h, 0.72 if "Woman" in name or name == "Girl" else 0.6, spear)
    xs, ys, face, pose = [], [], [], []
    stopped = None
    for f, t in zip(PF, PT):
        u = smooth(20, 22, t)
        x = LANE_X + lerp(dx, 0.12 * (i % 2) - 0.06, u)
        y = YC[f] + lerp(dy, LINE.get(i, dy), u)
        a, p = 0.0, None
        if i in (8, 9) and CAT_T[0] + 1.0 < t < CAT_T[1] - 0.5:      # the rear guard turns on the cat
            a = math.pi * smooth(CAT_T[0] + 1.0, CAT_T[0] + 1.3, t) * (1 - smooth(CAT_T[1] - 0.9, CAT_T[1] - 0.5, t))
            p = {"arms": -1.9, "lean": 0.0}
        if i == 9 and t > 18.5:                                       # one of ours goes down at the clash
            if stopped is None:
                stopped = (x, y)
            k = smooth(18.5, 18.9, t)
            x, y = stopped
            p = {"lean": -1.45 * k, "z": 0.12 * k, "legs": 0.0, "arms": 0.3}
        if i == GRAVE_WHO and t >= GRAVE_T[0]:                                # the woman at the grave
            if stopped is None:
                stopped = (x - 0.7, y)
            k = smooth(GRAVE_T[0], GRAVE_T[0] + 0.5, t) * (1 - smooth(GRAVE_UP, GRAVE_UP + 0.5, t))
            if t < GRAVE_UP + 0.5:
                x, y = lerp(x, stopped[0], smooth(GRAVE_T[0] - 0.4, GRAVE_T[0], t)), stopped[1]
                a = math.radians(90) * k                              # she turns to the grave, on our side
                p = {"z": -0.42 * h * k, "lean": 0.5 * k, "legs": 1.5 * k, "arms": -0.9 * k}
            else:                                                     # she walks on, and looks back once
                tt = t - (GRAVE_UP + 0.5)
                y = stopped[1] + 1.75 * tt
                x = lerp(stopped[0], LANE_X, smooth(0, 1.5, tt))
                a = math.radians(150) * smooth(0.5, 0.8, tt) * (1 - smooth(1.2, 1.6, tt))
        xs.append(x)
        ys.append(y)
        face.append(a)
        pose.append(p)
    animate(fig, PF, xs, ys, face, pose, visible=[(T("03:57"), 0), (T("03:58"), 1)])
    people.append(fig)
    band_paths[i] = (xs, ys)

# The cat: lion-sized, from behind (the right), 04:10-04:14; it goes down and is left behind.
bm = bmesh.new()
ball(bm, (0, 0, 0.78), (0.3, 0.95, 0.36), 10)
ball(bm, (0, 1.0, 0.95), (0.2, 0.24, 0.2), 8)
for sx in (-0.2, 0.2):
    for sy in (-0.6, 0.65):
        cone(bm, (sx, sy, 0), 0.07, 0.09, 0.7, 5)
cat = obj_from_bm("Big cat", bm, 0.16)
cl, cr = [[], [], []], [[], [], []]
down_at = None
for f, t in zip(PF, PT):
    rear = YC[f] - 3.6
    gap = lerp(16, 2.2, smooth(CAT_T[0] - 0.5, CAT_T[0] + 1.3, t))    # closing from behind
    gap = lerp(gap, 0.9, smooth(CAT_T[0] + 2.4, CAT_T[0] + 3.0, t))   # the spring
    y = rear - gap
    z = 0.9 * math.sin(math.pi * smooth(CAT_T[0] + 2.4, CAT_T[0] + 3.1, t))
    roll = 0.0
    if t > CAT_T[0] + 3.1:                                            # speared: down, and still
        if down_at is None:
            down_at = y
        k = smooth(CAT_T[0] + 3.1, CAT_T[0] + 3.4, t)
        y, z, roll = down_at + 0.8 * k, 0.0, 1.5 * k
    for i, v in enumerate((LANE_X + 0.1, y, z)):
        cl[i].append(v)
    for i, v in enumerate((0.0, roll, 0.0)):
        cr[i].append(v)
key(cat, "location", PF, cl)
key(cat, "rotation_euler", PF, cr)
key_scale(cat, [(CAT_T[0] - 2, 0), (CAT_T[0] - 1.5, 1)])

# The other band: six, coming the other way (left to right), met at 04:18:05.
MEET = 18.2
ymeet = YC[int(fr(MEET))]
for j, (dx, dy, falls) in enumerate([(0.9, 0.0, False), (-0.5, 1.2, True), (0.3, 2.3, False),
                                     (-0.9, 3.1, False), (0.6, 4.2, True), (-0.2, 5.4, False)]):
    fig = figure("Other band %d" % (j + 1), random.uniform(1.6, 1.76), 0.22, spear=True)
    xs, ys, face, pose = [], [], [], []
    stopped = None
    for f, t in zip(PF, PT):
        x, y = LANE_X + dx, ymeet + dy - 3.0 * (t - MEET) + 0.5
        p = None
        if falls and t > MEET + 0.2 + 0.2 * j:
            if stopped is None:
                stopped = (x, y)
            k = smooth(MEET + 0.2 + 0.2 * j, MEET + 0.6 + 0.2 * j, t)
            x, y = stopped
            p = {"lean": -1.45 * k, "z": 0.12 * k, "legs": 0.0, "arms": 0.3}
        elif MEET - 0.8 < t < MEET + 0.8:
            p = {"arms": -1.7}
        xs.append(x)
        ys.append(y)
        face.append(math.pi)
        pose.append(p)
    animate(fig, PF, xs, ys, face, pose, visible=[(CLASH_T[0] - 4, 0), (CLASH_T[0] - 3.5, 1)])

# The newborn, passed up the line from the rear to the front, 04:22-04:26.
bm = bmesh.new()
ball(bm, (0, 0, 0), (0.11, 0.24, 0.1), 8)
baby = obj_from_bm("Newborn", bm, 0.9)
order = sorted(LINE, key=lambda i: LINE[i])            # rear to front
bf, bl = [], [[], [], []]
for f, t in zip(PF, PT):
    if not (BABY_T[0] - 0.2 <= t <= BABY_T[1] + 0.2):
        continue
    u = min(1.0, max(0.0, (t - BABY_T[0]) / (BABY_T[1] - BABY_T[0]))) * (len(order) - 1)
    a, b = order[int(min(u, len(order) - 2))], order[int(min(u, len(order) - 2)) + 1]
    k = smooth(0.25, 0.75, u - int(min(u, len(order) - 2)))           # held, then handed on
    ia = PF.index(f)
    bf.append(f)
    bl[0].append(lerp(band_paths[a][0][ia], band_paths[b][0][ia], k) - 0.22)
    bl[1].append(lerp(band_paths[a][1][ia], band_paths[b][1][ia], k))
    bl[2].append(1.12 + 0.1 * math.sin(math.pi * k))
key(baby, "location", bf, bl)
key_scale(baby, [(BABY_T[0] - 0.3, 0), (BABY_T[0] - 0.2, 1), (BABY_T[1] + 0.1, 1), (BABY_T[1] + 0.2, 0)])

# The small grave, at the edge of the path on the camera's side.
gi = PF.index(int(fr(GRAVE_T[0])))
grave_pos = (band_paths[GRAVE_WHO][0][gi] - 0.75, band_paths[GRAVE_WHO][1][gi], 0)
bm = bmesh.new()
ball(bm, grave_pos, (0.3, 0.5, 0.16), 10)
grave = obj_from_bm("Small grave", bm, 0.22)

# ---------------------------------------------------------------- the river (04:30)
# It runs north (to the left), east of the path: it comes in from the far right and
# runs alongside from about y = 104. Banks green: reeds, trees, hippos in the shallows.
near = [(75, 88), (34, 96), (15, 103), (12, 112), (12, 240)]
bm = bmesh.new()
vs = [bm.verts.new((x, y, 0.02)) for x, y in near] + [bm.verts.new((x + 70, y, 0.02)) for x, y in reversed(near)]
bm.faces.new(vs)
river = obj_from_bm("River", bm, 0.14)
bm = bmesh.new()
for (xa, ya), (xb, yb) in zip(near, near[1:]):
    for _ in range(int(math.hypot(xb - xa, yb - ya) * 3.5)):
        u = random.random()
        cone(bm, (lerp(xa, xb, u) - random.uniform(0, 2.5), lerp(ya, yb, u) + random.uniform(-1, 1), 0),
             random.uniform(.05, .12), 0.0, random.uniform(1.5, 3.2), 4)       # reeds and papyrus
for y in range(100, 240, 9):
    tree_mesh(bm, (random.uniform(7.5, 9.5), y + random.uniform(-3, 3), 0), random.uniform(6, 11), .25)
    tree_mesh(bm, (84 + random.uniform(0, 5), y + random.uniform(-3, 3), 0), random.uniform(6, 11), .25)
reeds = obj_from_bm("Reeds and bank trees", bm, 0.3)
bm = bmesh.new()
for x, y in ((14.5, 108), (16, 111), (15, 118), (18, 124)):
    ball(bm, (x, y, 0.0), (0.75, 1.9, 0.75), 10)                             # hippos, 3.8 m
hippos = obj_from_bm("Hippos", bm, 0.2)

# ---------------------------------------------------------------- the trunks that wipe the frame
bm = bmesh.new()
for t in WIPES:
    f = int(fr(t))
    cone(bm, (LANE_X - curve(CAM_DIST, t, ease=True) + 1.2, YC[f] + 0.5, 0), 0.5, 0.42, 22, 10)
wipes = obj_from_bm("Trunks that cross the lens", bm, 0.12)


# ---------------------------------------------------------------- cameras
def camera(name):
    cd = bpy.data.cameras.new(name)
    cd.lens, cd.sensor_width, cd.clip_start, cd.clip_end = LENS, 36.0, 0.03, 2000
    ob = bpy.data.objects.new(name, cd)
    col.objects.link(ob)
    return ob


def aim(pos, target):
    return (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()


def key_camera(cam, frames, positions, targets):
    loc, rot = [[], [], []], [[], [], []]
    for p, tg in zip(positions, targets):
        e = aim(p, tg)
        for i in range(3):
            loc[i].append(p[i])
            rot[i].append(e[i])
    key(cam, "location", frames, loc)
    key(cam, "rotation_euler", frames, rot)


# Camera 1, 03:42-03:54: locked on the dead face, a slow push in; it tips up with the tree.
cam1 = camera("CAM skull time-lapse")
f1 = [f for f in FR if f < fr(T("03:54"))]
pos, tgt = [], []
for f in f1:
    t = (f - T0) / O.FPS
    p = SKULL_CAM_A.lerp(SKULL_CAM_B, smooth(T("03:42"), T("03:52"), t))
    pos.append(p)
    tgt.append((0.0, 0.1, 0.75 + 1.3 * smooth(T("03:52:06"), T("03:54"), t)))
key_camera(cam1, f1, pos, tgt)

# Camera 2, 03:54-04:36: on the ground for the leaf and the feet, then up and away with the band.
cam2 = camera("CAM leaf and run")
f2 = [f for f in FR if f >= fr(T("03:54"))]
pos, tgt = [], []
ta, tb = LEAF_FALL
for f in f2:
    t = (f - T0) / O.FPS
    # on the ground: tilting down with the leaf, then holding on it
    u = smooth(ta, tb, t)
    lp = Vector(LEAF_CAM)
    lt = Vector((LEAF.x, LEAF.y, lerp(0.95, 0.2, u)))
    # travelling: beside the band, looking east, a little ahead of the centre
    d = curve(CAM_DIST, t, ease=True)
    y = YC[f] + curve(CAM_AHEAD, t, ease=True)
    tp = Vector((LANE_X - d, y, CAM_HEIGHT))
    tt = Vector((LANE_X, y, 1.3))
    w = smooth(PULL_BACK[0], PULL_BACK[1], t)
    pos.append(lp.lerp(tp, w))
    tgt.append(lt.lerp(tt, w))
key_camera(cam2, f2, pos, tgt)

# One marker per shot, each bound to its camera: the burn-in reads its name.
for sh in O.shots():
    if F0 <= sh["start"] < F1:
        m = scene.timeline_markers.new("SH" + sh["shot"], frame=sh["start"])
        m.camera = cam1 if sh["start"] < fr(T("03:54")) else cam2
scene.camera = cam1

# ---------------------------------------------------------------- the playblast look
r = scene.render
r.engine = 'BLENDER_WORKBENCH'
r.resolution_x, r.resolution_y, r.resolution_percentage = 960, 540, 100
sh = scene.display.shading
sh.light, sh.color_type = 'STUDIO', 'OBJECT'
sh.show_shadows, sh.shadow_intensity = True, 0.35
sh.show_cavity, sh.cavity_type = True, 'WORLD'
sh.show_object_outline = True
scene.display.light_direction = (0.35, -0.45, 0.82)
scene.display.render_aa = '8'
r.use_stamp = True
for a in ("date", "render_time", "filename", "scene", "memory", "hostname", "frame_range", "sequencer_strip"):
    setattr(r, "use_stamp_" + a, False)
r.use_stamp_time = r.use_stamp_frame = r.use_stamp_marker = r.use_stamp_camera = r.use_stamp_lens = True
r.use_stamp_note, r.stamp_note_text = True, "Opening layout, beats 12-13, grey"
r.use_stamp_labels = True
r.stamp_font_size = 15
r.stamp_background = (0, 0, 0, 0.6)
r.image_settings.media_type = 'VIDEO'
r.image_settings.file_format = 'FFMPEG'
r.ffmpeg.format, r.ffmpeg.codec = 'MPEG4', 'H264'
r.ffmpeg.constant_rate_factor = 'HIGH'
r.ffmpeg.gopsize = 12
out = O.PLAYBLAST / "1200-1395-layout.mp4"
r.filepath = str(out)

O.LAYOUT.mkdir(parents=True, exist_ok=True)
O.PLAYBLAST.mkdir(parents=True, exist_ok=True)
scene.frame_set(F0)
bpy.ops.wm.save_as_mainfile(filepath=str(O.LAYOUT / "b12-13-layout.blend"))
print("saved", O.LAYOUT / "b12-13-layout.blend")

still = [a for a in sys.argv if a.startswith("still=")]
if still:                                   # still=03:55:00,04:00:06  -> PNGs beside the playblast
    r.image_settings.media_type = 'IMAGE'
    r.image_settings.file_format = 'PNG'
    for tc in still[0][6:].split(","):
        scene.frame_set(O.frame(tc))
        r.filepath = str(O.PLAYBLAST / "stills" / ("b12-13-" + tc.replace(":", "") + ".png"))
        bpy.ops.render.render(write_still=True)
elif RENDER:
    bpy.ops.render.render(animation=True)
    print("playblast", out)
