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

F0, F1 = O.frame("03:42"), O.frame("04:42")       # 5328 .. 6768 (end exclusive)
T0 = O.frame("04:06")                             # the first footfall: t = 0
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
LENS = 35.0                    # mm, on a 36 mm sensor: the travelling camera
LEAF = Vector((2.0, 1.6, 0.0))  # where the leaf lands; the band's lane runs over it
LANE_X = LEAF.x
SKULL = Vector((LEAF.x + 1.8, LEAF.y, 0.0))       # where the head lies and the tree grows: straight ahead, past the lane
BURROW = SKULL + Vector((-0.5, -1.0, 0.0))        # the hole the small creature ran into (beat 11), beside the head
TREE_H = 8.0                   # the tree that grows there, m; we only ever see its stump
BRANCH = Vector((LEAF.x, LEAF.y, 3.0))            # the tip of its low branch, over the lane, above the frame
TREE_GROW = (T("03:54"), T("03:56:12"))           # a shoot, a sapling, a tree; then still
LEAF_LOOSE = (T("03:58"), T("03:59"))             # the leaf trembles on its stem, then lets go
LEAF_FALL = (T("03:59"), T("04:03"))              # falls 2.9 m, like a feather; still until 04:06 (3 s)
# The unbroken shot, 03:42-04:07, low and right up next to the dead animal (your notes, 2026-10-14),
# looking straight across the band's path: the head decomposing in the centre of frame, the burrow
# beside it; then only the stump of the tree that grows there, centred, the forest beyond; the leaf
# falls into frame from above like a feather, in front of the stump, and as it comes down the view
# tips down a little, so the ground fills the frame and only legs will show. Square to the path,
# the runners can't be seen coming: their feet and legs come in from the right as they reach the
# leaf. Then a jerk of a whip left after them.
CAM_FIXED = Vector((LEAF.x - 1.6, LEAF.y, 0.4))    # 40 cm up, 1.6 m from where the leaf lands, 3.4 m from the head
PITCH = (2.0, -9.0)                                # degrees: level-ish on the face and the tree, then tipped down
TIP_DOWN = (T("04:01:12"), T("04:03:06"))          # as the leaf comes down
FIXED_LENS = 24.0
WHIP = (T("04:06:03"), T("04:06:11"))             # a jerk left after the runners (8 frames, no ease-in), then runs with them
ACTION = T("04:07")                               # cut to the fast cuts of the run (SH1310-1316)
TRAVEL = T("04:12")                               # cut to the travelling camera (SH1320 on)

# The band's speed, m/s, at seconds from 04:00 (linear between the points).
SPEED = [(-3, 5.0), (1.5, 5.0), (2.5, 4.5), (10, 4.5), (10.5, 3.5), (14, 3.5), (14.5, 4.0),
         (17, 4.0), (17.4, 3.0), (20, 3.0), (22, 1.8), (26, 1.8), (27, 1.6), (33, 1.6), (36, 1.2)]
# The travelling camera's distance from the lane, m, at seconds from 04:00.
CAM_DIST = [(6, 9.5), (9.5, 9.5), (11, 9.0), (13.5, 9.0), (15, 6.5), (16.5, 6.5), (17.5, 8.5), (20, 8.5), (22, 5.0), (26.5, 5.0), (27.5, 6.0),
            (30.5, 6.0), (33, 10.0), (36, 10.0)]
# How far ahead of the band's centre the camera looks, m: it drops back to the rear for the
# cat (04:10-04:14), then up the line with the newborn (04:22-04:26), lets the line walk through the frame past the grave, then catches up.
CAM_AHEAD = [(3.5, 1.0), (9.5, 1.0), (11, -2.0), (13.5, -2.0), (15, 1.0), (20, 1.0), (22, -3.4), (26, 3.2), (30.5, -1.0), (33, 1.0), (36, 1.0)]
CAM_HEIGHT = 1.5
ZONES = {"forest": (-25, 47), "woodland": (47, 86), "grassland": (86, 101), "dry": (101, 135)}
WIPES = [6.8, 9.0, 15.5, 21.0]  # seconds at which a trunk crosses the lens (a generation passes)


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
YC = {f: LEAF.y - LEAD + _dist[f] for f in FR}   # the band's centre; the lead runner (LEAD ahead) is on the leaf at 04:06


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
def in_view(x, y):
    """In front of the low locked camera, within 6 m: kept clear, so the ferns don't fill the frame."""
    d = Vector((x - CAM_FIXED.x, y - CAM_FIXED.y))
    a = Vector((1.0, 0.0))                                   # the camera faces east, square to the path
    return d.length < 6.0 and d.length > 0 and d.angle(a) < math.radians(45)


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
        if in_view(x, y):
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
    if zone == "forest":           # bare until the ferns come back at 03:51
        a, b = fr(T("03:51")), fr(T("03:52:12"))
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


# The forest the band runs through. Every tree here grows during 03:52-03:54,
# because the time-lapse camera sees it come up; the lane (x 0.6-3.2) is kept clear.
forest_trees = []
for x, y in spaced(150, (4.5, 62), (-28, 47), 3.0, keep_out=[(SKULL.x, SKULL.y, 6)]):
    h, r = random.uniform(11, 22), random.uniform(.2, .45)
    bm = bmesh.new()
    tree_mesh(bm, (0, 0, 0), h, r)
    ob = obj_from_bm("Tree", bm, random.uniform(.2, .3))
    ob.location = (x, y, 0)
    start = T("03:52") + random.uniform(0, 1.4)
    key_scale(ob, [(start - 1, 0.0), (start, 0.0), (start + 0.4, 0.25), (start + 1.0, 1.0)])
    forest_trees.append(ob)

bm = bmesh.new()
for x, y in spaced(32, (5, 60), (47, 86), 6.0):          # open woodland
    tree_mesh(bm, (x, y, 0), random.uniform(7, 14), random.uniform(.2, .4))
for x, y in spaced(4, (25, 60), (86, 100), 12.0):        # lone trees in the grass
    tree_mesh(bm, (x, y, 0), random.uniform(6, 9), .3)
far_trees = obj_from_bm("Trees beyond the forest", bm, 0.26)

# Forest on the other (west) side too, beyond where the travelling camera runs, so the shots from
# the far side of the band (SH1314-1316) look into trees; it grows with the rest.
west_trees = []
for x, y in spaced(60, (-40, -12), (-28, 47), 3.5):
    bm = bmesh.new()
    tree_mesh(bm, (0, 0, 0), random.uniform(11, 22), random.uniform(.2, .45))
    ob = obj_from_bm("Tree, west", bm, random.uniform(.2, .3))
    ob.location = (x, y, 0)
    start = T("03:52") + random.uniform(0, 1.4)
    key_scale(ob, [(start - 1, 0.0), (start, 0.0), (start + 0.4, 0.25), (start + 1.0, 1.0)])
    west_trees.append(ob)

# Ferns at the skull, which come first (03:51), before the trees; none in the camera's near view.
ferns = []
for x, y in spaced(70, (SKULL.x - 1.5, SKULL.x + 22), (SKULL.y - 11, SKULL.y + 11), 0.9, keep_out=[(SKULL.x, SKULL.y, 1.6)]):
    if in_view(x, y):
        continue
    bm = bmesh.new()
    cone(bm, (0, 0, 0), random.uniform(.3, .5), 0.05, random.uniform(.4, .7), 7)
    ob = obj_from_bm("Fern", bm, 0.3)
    ob.location = (x, y, 0)
    start = T("03:51") + random.uniform(0, 1.6)
    key_scale(ob, [(start - 1, 0.0), (start, 0.0), (start + 0.4, 1.0)])
    ferns.append(ob)

# The tree that grows where the head lay: a shoot, a sapling, a tree, in two seconds.
# Its low branch reaches out over the lane, and the leaf hangs from its tip.
bm = bmesh.new()
tree_mesh(bm, (0, 0, 0), TREE_H, 0.3)
fork = Vector((0, 0, 2.3))
tip = BRANCH - SKULL
reach = tip + Vector((0, 0, 0.12)) - fork
cone(bm, fork, 0.09, 0.03, reach.length, 6, rot=reach.to_track_quat('Z', 'Y').to_matrix().to_4x4())
ball(bm, tip + Vector((0, 0, 0.3)), (0.6, 0.6, 0.35), 8)                   # the branch's leaves
the_tree = obj_from_bm("The tree", bm, 0.5)
the_tree.location = SKULL
a = TREE_GROW[0]
key_scale(the_tree, [(a - 1, 0), (a, 0), (a + 0.5, 0.02), (a + 1.1, 0.12), (a + 1.9, 0.55), (a + 2.5, 1.0)])

# The burrow the small creature ran into at the end of beat 11, beside the head: a dark hole
# among a few roots, under the ash from 03:46 and the ferns from 03:51.
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, segments=12, radius=0.15, matrix=Matrix.Translation((0, 0, 0.01)))
for ang in (20, 140, 250):
    cone(bm, (0, 0, 0.03), 0.03, 0.015, 0.3, 5, rot=Matrix.Rotation(math.radians(ang), 4, 'Z') @ Matrix.Rotation(math.radians(84), 4, 'X'))
burrow = obj_from_bm("Burrow", bm, 0.12)
burrow.location = BURROW
key(burrow, "location", [fr(T("03:46")), fr(T("03:47"))], [0.0, -0.06], index=2)   # gone under the ash


# ---------------------------------------------------------------- the dead Triceratops
# A head 2.3 m long, lying on its side with the frill up, and the body behind it (south).
dead = empty("Dead Triceratops")
dead.location = SKULL
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
# 03:45-03:48 the flesh goes and the skull shows; 03:48-03:50:12 it sinks.
key_grey(head, [(T("03:45"), 0.3), (T("03:47:12"), 0.8)])
key_scale(head, [(T("03:45"), 1.0), (T("03:47:12"), 0.9)])
fs = [fr(T("03:45")), fr(T("03:48"))]
key(body, "scale", fs, [[1, 0.9], [1, 0.85], [1, 0.12]])
key(dead, "location", [fr(T("03:48")), fr(T("03:50:12"))], [0.0, -1.9], index=2)

# Ash, lying over the place from 03:45, gone under the green by 03:52.
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, segments=32, radius=40)
ash = obj_from_bm("Ash", bm, 0.62)
key(ash, "location", [fr(T("03:45")), fr(T("03:46:12")), fr(T("03:51")), fr(T("03:52"))],
    [-0.05, 0.02, 0.02, -0.05], index=2)

# The last of the falling fire, far off in the east, stopping by 03:45.
for i in range(16):
    bm = bmesh.new()
    cone(bm, (0, 0, 0), 0.5, 0.1, 26, 5, rot=Matrix.Rotation(math.radians(24), 4, 'X'))
    st = obj_from_bm("Fire", bm, 0.95)
    y = random.uniform(-70, 70)
    t0 = T("03:42") - 0.4 + (i / 16.0) ** 1.6 * 3.0          # thinning out
    key(st, "location", [fr(t0 - 5), fr(t0), fr(t0 + 0.7), fr(t0 + 5)],
        [[150] * 4, [y, y, y - 34, y - 34], [70, 70, -30, -30]])

# Animals pass as blurs (03:52:12, 03:53:06): each crosses the frame in a few frames.
for tc, x, d in (("03:52:12", 6.0, 1), ("03:53:06", 11.0, -1)):
    bm = bmesh.new()
    ball(bm, (0, 0, 0.8), (0.45, 1.1, 0.6), 8)
    an = obj_from_bm("Animal passing", bm, 0.2)
    t = T(tc)
    key(an, "location", [fr(t - 4), fr(t), fr(t + 0.25), fr(t + 4)],
        [[x] * 4, [-16 * d, -16 * d, 16 * d, 16 * d], [0] * 4])

# The sky: light, dark from 03:45, clear by 03:52.
sky = [(T("03:42"), 0.50), (T("03:45"), 0.10), (T("03:50:12"), 0.10), (T("03:52"), 0.66)]
key(None, "color", [fr(t) for t, _ in sky], [[v for _, v in sky]] * 3, target=world)


# ---------------------------------------------------------------- the leaf
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, segments=10, radius=1.0,
                        matrix=Matrix.Diagonal((0.06, 0.035, 1, 1)))   # 12 cm by 7 cm
leaf = obj_from_bm("Leaf", bm, 0.97)   # white in the playblast, so its motion reads at true size
lf, lloc, lrot = [], [[], [], []], [[], [], []]
la = LEAF_LOOSE[0]
ta, tb = LEAF_FALL
HANG = BRANCH - Vector((0, 0, 0.1))        # hanging under the branch tip
Z0 = HANG.z - 0.02
for f in FR:
    t = (f - T0) / O.FPS
    if t < la - 0.2:
        continue
    if t < ta:                             # on its stem: trembling harder and harder, then it lets go
        k = smooth(la, ta, t)
        ph = 2 * math.pi * 3.0 * (t - la)
        p = (HANG.x, HANG.y + 0.03 * k * math.sin(ph * 0.5), HANG.z - 0.02 * k)
        rot = (0.5 + 0.5 * k * math.sin(ph), 0.3 * k * math.sin(ph * 0.5), 0.0)
    elif t <= 0.04:                        # the slow fall, then stillness
        u = min(1.0, max(0.0, (t - ta) / (tb - ta)))
        sway = (1 - u) ** 0.5              # the swinging dies as it comes down, like a feather's
        ph = 2 * math.pi * 0.5 * (t - ta)
        z = Z0 * (1 - u) + 0.004 - 0.07 * sway * abs(math.sin(ph))
        drift = lerp(HANG.x, LEAF.x, smooth(0.0, 1.0, u))                # (none while the branch is over the landing place)
        p = (drift + 0.05 * sway * math.sin(ph * 0.5), LEAF.y + 0.45 * sway * math.sin(ph), max(z, 0.004))
        rot = (0.5 * (1 - u) + 0.6 * sway * math.sin(ph), 0.25 * sway * math.sin(ph * 0.5), 0.6 * u)
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
key_scale(leaf, [(la - 0.2, 0), (la - 0.15, 1), ((lf[-1] - T0) / O.FPS, 1), ((lf[-1] - T0) / O.FPS + DT, 0)])
leaf_at = {f: Vector((lloc[0][i], lloc[1][i], lloc[2][i])) for i, f in enumerate(lf)}

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
    return {"root": root, "body": body, "limbs": limbs, "h": h,
            "phase0": random.uniform(0, 2 * math.pi), "stride": random.uniform(0.88, 1.12)}   # no two in step


def animate(fig, frames, xs, ys, face=None, pose=None, visible=None):
    """Move a figure along (xs, ys) and swing its limbs by how far it has travelled.

    face: heading per frame (radians about Z, 0 = toward +Y). pose: per frame, None or a dict
    with 'z' (root height), 'lean' (radians, forward), 'legs' (radians, both legs), 'arms'
    (both arms), 'arm_l' (the left arm alone).
    """
    n = len(frames)
    face = face or [0.0] * n
    pose = pose or [None] * n
    loc = [[], [], []]
    rot = [[], [], []]
    swing = [[] for _ in range(4)]
    phase = fig.get("phase0", 0.0)
    for i in range(n):
        v = 0.0 if i == 0 else math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]) / DT
        run = min(1.0, max(0.0, (v - 1.6) / 2.9))             # 0 = a walk, 1 = a run
        cycle = lerp(1.5, 2.8, run) * fig.get("stride", 1.0)  # metres per full stride cycle
        phase += 2 * math.pi * v * DT / cycle
        amp = lerp(0.42, 0.8, run) * min(1.0, v / 1.0)
        p = pose[i] or {}
        s = math.sin(phase)
        legs = p.get("legs")
        swing[0].append(s * amp if legs is None else legs)
        swing[1].append(-s * amp if legs is None else legs)
        swing[2].append(-s * amp * 0.9 if "arms" not in p else p["arms"])
        swing[3].append(p["arm_l"] if "arm_l" in p else s * amp * 0.9 if "arms" not in p else p["arms"])
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


PF = [f for f in FR if f >= fr(T("04:04"))]        # people exist from 04:04 (they are far off, right)
PT = [(f - T0) / O.FPS for f in PF]

# The band: ten people. (name, height m, lateral place in the pack, place along it, spear)
# Along: + is ahead (left). From 04:20 to 04:22 they fall into a single line, 0.9 m apart.
BAND = [("Lead man", 1.72, 0.0, 3.0, True), ("Woman A", 1.60, 0.7, 2.2, False),
        ("Woman B", 1.62, -0.6, 1.5, False), ("Woman C (centre)", 1.58, 0.2, 0.3, False),
        ("Man D", 1.74, 1.0, -0.2, True), ("Girl", 1.30, -0.3, -0.9, False),
        ("Woman E", 1.62, 0.6, -1.6, False), ("Man F", 1.68, -0.7, -2.2, True),
        ("Man G (rear)", 1.73, 0.4, -3.0, True), ("Man H (rear)", 1.70, -0.4, -3.6, True)]
LINE = {0: 2.7, 1: 3.6, 2: 1.8, 3: 0.9, 4: 0.0, 5: -0.9, 6: -1.8, 7: -2.7, 8: -3.6}   # index 9 falls at the clash
CAT_T = (T("04:16"), T("04:20"))
CLASH_T = (T("04:23"), T("04:26"))
BABY_T = (T("04:28"), T("04:32"))
GRAVE_T = (T("04:33"), T("04:36:12"))
GRAVE_WHO = 2
GRAVE_PULLER = 7               # Man F, walking up the line behind her, takes her arm and pulls her up and on
_y_grave = YC[int(fr(GRAVE_T[0]))] + LINE[GRAVE_WHO]
GRAVE_UP = next((f - T0) / O.FPS for f in FR if f > fr(GRAVE_T[0]) and YC[f] + LINE[GRAVE_PULLER] >= _y_grave - 0.4)
GLANCE = (T("04:07:16"), T("04:08:10"))   # the lead man looks back over his shoulder (SH1311)
people = []
band_paths = {}
# Each runner wanders in the pack (across and along, on two slow waves of its own), so the band
# is a crowd, not a formation (your note, 2026-10-14); it settles as they fall into a line.
WANDER = [[random.uniform(0, 2 * math.pi) for _ in range(4)] for _ in BAND]
for i, (name, h, dx, dy, spear) in enumerate(BAND):
    fig = figure(name, h, 0.72 if "Woman" in name or name == "Girl" else 0.6, spear)
    xs, ys, face, pose = [], [], [], []
    stopped = None
    for f, t in zip(PF, PT):
        u = smooth(20, 22, t)
        x = LANE_X + lerp(dx, 0.12 * (i % 2) - 0.06, u)
        y = YC[f] + lerp(dy, LINE.get(i, dy), u)
        ph, w = WANDER[i], 1.0 - 0.75 * u
        if i == 0:                                                    # the lead runner keeps to the leaf
            w *= smooth(0.5, 3.0, t)
        x += w * (0.3 * math.sin(0.8 * t + ph[0]) + 0.15 * math.sin(2.1 * t + ph[1]))
        y += w * (0.7 * math.sin(0.5 * t + ph[2]) + 0.3 * math.sin(1.4 * t + ph[3]))
        x = min(x, SKULL.x - 0.75 * (1 - smooth(0.6, 1.5, abs(y - SKULL.y))))           # round the tree,
        x = max(x, CAM_FIXED.x + 0.5 * (1 - smooth(0.3, 1.0, abs(y - CAM_FIXED.y))))   # and past the camera
        a, p = 0.0, None
        if i == 0:                                                    # a look back at what's after them
            a = 0.8 * smooth(GLANCE[0], GLANCE[0] + 0.25, t) * (1 - smooth(GLANCE[1] - 0.25, GLANCE[1], t))
        if i == GRAVE_PULLER and GRAVE_UP - 0.4 < t < GRAVE_UP + 0.9:  # reaches down for her arm
            k = smooth(GRAVE_UP - 0.4, GRAVE_UP, t) * (1 - smooth(GRAVE_UP + 0.5, GRAVE_UP + 0.9, t))
            x -= 0.35 * k
            p = {"arm_l": -1.1 * k, "lean": 0.25 * k}
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
            beside = YC[f] + LINE[GRAVE_PULLER] + 0.5                 # pulled along at his side
            if t < GRAVE_UP + 0.5:
                x = lerp(x, stopped[0], smooth(GRAVE_T[0] - 0.4, GRAVE_T[0], t))
                y = lerp(stopped[1], beside, smooth(GRAVE_UP, GRAVE_UP + 0.5, t))   # yanked up and on
                a = math.radians(90) * k                              # she turns to the grave, on our side
                p = {"z": -0.42 * h * k, "lean": 0.5 * k, "legs": 1.5 * k, "arms": -0.9 * k}
            else:                                                     # she walks on with him, and looks back once
                tt = t - (GRAVE_UP + 0.5)
                y = beside
                x = lerp(stopped[0], LANE_X - 0.45, smooth(0, 1.0, tt))
                a = math.radians(150) * smooth(0.3, 0.6, tt) * (1 - smooth(1.0, 1.4, tt))
        xs.append(x)
        ys.append(y)
        face.append(a)
        pose.append(p)
    animate(fig, PF, xs, ys, face, pose, visible=[(T("04:03"), 0), (T("04:04"), 1)])
    people.append(fig)
    band_paths[i] = (xs, ys)

# The cat: lion-sized, what the band is running from. It is after them from before the leaf,
# far back (glimpsed in SH1313), closes from behind (the right) at 04:10, springs, goes down
# and is left behind.
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
    gap = curve([(-1.0, 34.0), (CAT_T[0] - 0.5, 16.0)], t)            # gaining on them
    gap = lerp(gap, 2.2, smooth(CAT_T[0] - 0.5, CAT_T[0] + 1.3, t))   # closing from behind
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
key_scale(cat, [(-1.2, 0), (-1.0, 1)])

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


def key_lens(cam, frames, lenses):
    key(None, "lens", frames, lenses, index=0, target=cam.data)


# Camera 1, 03:42-04:07, one unbroken shot, low, right up next to the dead animal, square to the
# band's path. It doesn't move but to tip down a little with the leaf; then the feet come over it
# and it jerks left after the runners and runs with them.
cam1 = camera("CAM unbroken")
f1 = [f for f in FR if f < fr(ACTION)]
pos, tgt = [], []
for f in f1:
    t = (f - T0) / O.FPS
    pitch = math.radians(lerp(PITCH[0], PITCH[1], smooth(TIP_DOWN[0], TIP_DOWN[1], t)))
    g = CAM_FIXED + Vector((math.cos(pitch), 0.0, math.sin(pitch))) * 6.0
    if t > WHIP[0]:                                                              # the whip: off at once, at
        u = min(1.0, (t - WHIP[0]) / (WHIP[1] - WHIP[0]))                         # full speed, easing only
        u = 1 - (1 - u) ** 3                                                      # into the runners
        ahead = Vector((LANE_X, YC[f] + LEAD + 1.0, 0.9))                        # just ahead of the lead runner,
        d0, d1 = (g - CAM_FIXED).normalized(), (ahead - CAM_FIXED).normalized()  # always left of the leaf
        g = CAM_FIXED + d0.slerp(d1, u) * 4.0
    pos.append(CAM_FIXED)
    tgt.append(g)
key_camera(cam1, f1, pos, tgt)
key_lens(cam1, f1, [FIXED_LENS] * len(f1))

# Camera 2, 04:01-04:06: fast cuts of the run, to show they're running from something.
# The first runs with them at their feet; after it, each shot is a camera planted in one place
# that turns to follow the runners and whips as they go by (your notes, 2026-10-14). Per shot:
# whom it follows; when in the shot they're abeam of it (0 = the first frame, 1 = the last;
# None = it runs with them, keeping the same place beside them); where it stands, from that runner
# at that moment (across, along, up; across is toward the camera's side, west); the height it
# looks at on them; and the lens. A target of None follows the runner; a fixed point (from the
# same moment) holds there while they run out of frame.
CUTS = {"1310": (3, None, (-1.3, 0.1, 1.45), 1.42, None, 50),     # a face, close, running with her (the centre woman)
        "1311": (0, 0.5, (-2.5, 0.0, 1.6), 1.55, None, 35),       # the lead man as he passes, looking back
        "1312": (3, 0.5, (-14.0, 0.0, 4.5), 1.0, None, 35),       # wide and high: the band through the forest
        "1313": (9, 0.2, (-3.5, 1.0, 1.5), 1.0, (5.0, -16.0), 35),  # back past the rear: something in the trees
        # 1314-1316 from the other side of the band (your note, 2026-10-14): they run to the right of frame
        "1314": (5, 0.5, (3.0, 0.0, 1.1), 0.95, None, 50),        # the girl, running hard
        "1315": (7, 0.5, (2.2, 0.0, 0.6), 0.8, None, 28),         # spears and legs, low
        "1316": (4, 1.0, (1.2, 1.0, 1.3), 1.2, None, 24)}         # they come at the lens and stream past it
cam2 = camera("CAM action")
f2, pos, tgt, lens = [], [], [], []
for sh in O.shots():
    if sh["shot"] not in CUTS:
        continue
    who, when, off, look_z, hold, mm = CUTS[sh["shot"]]
    xs, ys = band_paths[who]
    k = int(round(lerp(sh["start"], sh["end"] - 1, when or 0))) - PF[0]
    stand = Vector((xs[k] + off[0], ys[k] + off[1], off[2]))
    for tr in forest_trees + west_trees:                       # never inside a trunk: step along the path
        d = Vector((stand.x - tr.location.x, stand.y - tr.location.y))
        if d.length < 1.0:
            stand.y += (1.0 - d.length) * (1 if d.y >= 0 else -1) + 0.2
    for f in range(sh["start"], sh["end"]):
        i = f - PF[0]
        f2.append(f)
        pos.append(stand if when is not None else Vector((xs[i] + off[0], ys[i] + off[1], off[2])))
        tgt.append(Vector((xs[k] + hold[0], ys[k] + hold[1], look_z)) if hold else Vector((xs[i], ys[i], look_z)))
        lens.append(mm)
key_camera(cam2, f2, pos, tgt)
key_lens(cam2, f2, lens)
assert f2[0] == fr(ACTION) and f2[-1] == fr(TRAVEL) - 1

# Camera 3, 04:06-04:36: travelling beside the band, looking east, a little ahead of the centre.
cam3 = camera("CAM travelling")
f3 = [f for f in FR if f >= fr(TRAVEL)]
pos, tgt = [], []
for f in f3:
    t = (f - T0) / O.FPS
    d = curve(CAM_DIST, t, ease=True)
    y = YC[f] + curve(CAM_AHEAD, t, ease=True)
    pos.append(Vector((LANE_X - d, y, CAM_HEIGHT)))
    tgt.append(Vector((LANE_X, y, 1.3)))
key_camera(cam3, f3, pos, tgt)

# One marker per shot, each bound to its camera: the burn-in reads its name.
for sh in O.shots():
    if F0 <= sh["start"] < F1:
        m = scene.timeline_markers.new("SH" + sh["shot"], frame=sh["start"])
        m.camera = cam1 if sh["start"] < fr(ACTION) else cam2 if sh["start"] < fr(TRAVEL) else cam3
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
r.use_stamp_note, r.stamp_note_text = True, "Opening layout, beats 12-13, grey, sixth pass"
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
