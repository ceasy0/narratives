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
from mathutils import Matrix, Vector, noise
from bpy_extras import anim_utils

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402

RENDER = "render" in sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else False
random.seed(12)

F0, F1 = O.frame("03:42"), O.frame("04:43")       # 5328 .. 6792 (end exclusive)
T0 = O.frame("04:07")                             # the first footfall: t = 0
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
LEAF_FALL = (T("03:59"), T("04:03"))              # falls 2.9 m, like a feather; still until 04:07 (4 s)
# The unbroken shot, 03:42-04:07, low and right up next to the dead animal (your notes, 2026-10-14),
# looking straight across the band's path: the head decomposing in the centre of frame, the burrow
# beside it; then only the stump of the tree that grows there, centred, the forest beyond; the leaf
# falls into frame from above like a feather, in front of the stump, and as it comes down the view
# tips down a little, so the ground fills the frame and only legs will show. Square to the path,
# the runners can't be seen coming: their feet and legs come in from the right as they reach the
# leaf. As the first foot comes down on it, the view turns left with that runner and follows him.
CAM_FIXED = Vector((LEAF.x - 1.6, LEAF.y, 0.4))    # 40 cm up, 1.6 m from where the leaf lands, 3.4 m from the head
PITCH = (2.0, -9.0)                                # degrees: level-ish on the face and the tree, then tipped down
TIP_WAIT = 1.0                                     # s: the tip down starts this long after the leaf comes into frame
TIP_TIME = 2.6                                     # s: and takes this long, slowly, settling after the leaf lands
FIXED_LENS = 24.0
TRACK_IN = 0.12                                   # s: from the first footfall, the view takes up the lead runner's pace this smoothly
ACTION = T("04:08")                               # cut to the fast cuts of the run (SH1310-1316)
TRAVEL = T("04:15")                               # cut to the travelling camera (SH1320 on)

# The band's speed, m/s, at seconds from 04:07 (linear between the points), from your notes of
# 2026-10-15: a flat-out sprint from the cat until it's dead, a hard run after it, a sprint again
# to charge the other band, which only comes into frame once the charge has begun; through the
# clash they slow, and in SH1360 they're down to a walk, a little slower the further they go.
CHARGE = T("04:24")            # they charge: flat out again by CHARGE + 0.4
MEET = T("04:25:12")           # the clash
SPEED = [(-3, 7.0), (13, 7.0), (14.5, 4.5), (CHARGE - 0.2, 4.5), (CHARGE + 0.4, 7.0), (MEET - 0.2, 7.0),
         (MEET + 0.6, 3.0), (20, 3.0), (22, 2.0), (36, 1.5)]
OTHER_SPEED = 5.5              # m/s: the other band charges too, and slows as they meet
CATCH_SPEED = 9.0              # m/s: the two from the cat, running the band down again
# The travelling camera stays this far from the band's path. In these shots it only ever moves
# forward with them, slowly or fast, never in or out (your note, 2026-10-14): getting closer or
# wider is the lens.
CAM_DIST = 9.5
# Its lens, mm, at seconds from 04:07: the framings the earlier passes got by moving in and out
# (9 m for the cat, 6.5 m after it, 8.5 m for the clash, 10 m at the river), the small zoom in
# SH1360 once the trunk has passed, and a little more at the grave.
CAM_LENS = [(6, 35), (9.5, 35), (11, 37), (13.5, 37), (15, 51), (16.5, 51), (17.5, 39), (20.4, 39), (21.6, 43),
            (26.5, 43), (27.5, 48), (30.5, 48), (33, 33), (36, 33)]
CAM_MIN_SPEED = 0.5            # m/s: it never stops or goes back, however slowly it goes
# How far ahead of the band's centre the camera looks, m: it drops back to the rear for the
# cat (04:18-04:21), then up the line with the newborn (04:29-04:33), lets the line walk through the frame past the grave, then catches up.
CAM_AHEAD = [(3.5, 1.0), (9.5, 1.0), (11, -2.0), (12.6, -5.0), (13.6, -5.5), (15.6, 0.0), (16.5, 1.0), (20, 1.0), (22, -3.4), (26, 3.2), (30.5, -1.0), (33, 1.0), (36, 1.0)]
CAM_HEIGHT = 1.5
# The trunks that cross the lens, each a generation passing: (seconds from 04:07, where it stands
# along the path from the camera's own place then). Each stands in front of the camera at a depth
# that grows with the lens, so it fills the frame the same way whatever the zoom. The third is at
# the end of the clash, while the camera still moves briskly, so it's a quick wipe (it used to be
# in SH1360, where the camera now crawls); the fourth is the lone tree in the grass.
WIPES = [(8.8, -0.5), (15.5, 0.54), (19.4, -0.3), (26.0, -0.3)]
# Split up (your note, 2026-10-15): once past the leaf, each runner takes their own line through
# the trees, cutting round the trunks, the band spread 7 m across and 10 m along; they close up
# again as they charge (SPREAD_T). Per runner in BAND: (across, along) from the band's centre.
SPREAD = [(1.2, 4.6), (4.2, 1.6), (-1.0, 2.6), (2.5, 0.2), (5.5, -0.8), (0.6, -1.8), (3.6, -3.0),
          (-1.2, -2.4), (1.8, -4.4), (2.4, -5.2)]
SPREAD_T = (CHARGE - 0.8, CHARGE + 0.6)
CLEAR = 0.7                    # m: how close they pass a trunk


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
YC = {f: LEAF.y - LEAD + _dist[f] for f in FR}   # the band's centre; the lead runner (LEAD ahead) is on the leaf at 04:07

# Where the travelling camera is along the path: CAM_AHEAD of the band's centre, but never going
# back and never slower than CAM_MIN_SPEED; where the band outruns it, it falls behind them.
CAM_Y = {}
for _f in range(int(fr(TRAVEL)) - 1, F1 + 1):
    _want = YC[_f] + curve(CAM_AHEAD, (_f - T0) / O.FPS, ease=True)
    CAM_Y[_f] = _want if _f - 1 not in CAM_Y else max(_want, CAM_Y[_f - 1] + CAM_MIN_SPEED * DT)


def Y(t):
    """The band's centre along the path, t seconds from 04:07."""
    return YC[int(round(fr(t)))]


# Where the country changes along the path: just ahead of the band as the shot of it begins
# (SH1330 open woodland at 04:17, SH1370 grassland at 04:29, SH1395 dry country at 04:37:12).
Y_WOOD, Y_GRASS, Y_DRY = Y(T("04:17")) + 2.4, Y(T("04:29")) + 1.3, Y(T("04:37:12")) + 1.8
ZONES = {"forest": (-25, Y_WOOD), "woodland": (Y_WOOD, Y_GRASS), "grassland": (Y_GRASS, Y_DRY), "dry": (Y_DRY, Y_DRY + 34)}
print("zones", {k: (round(a), round(b)) for k, (a, b) in ZONES.items()})

# The lie of the land (your note, 2026-10-15: the ground was too flat). Long swells up to about
# 2 m high and 40 m across, smaller rises, and bumps, from smooth noise; level round where the
# leaf lands, easing into the swells from 3 m to 14 m off, so the low camera there still sees it
# (and everything there stays at 0); and falling
# to the river, which runs north east of the path in the dry country (its near bank, RIVER_NEAR).
RIVER_NEAR = [(75, Y_DRY - 13), (34, Y_DRY - 5), (15, Y_DRY + 2), (12, Y_DRY + 11), (12, Y_DRY + 139)]
RIVER_WIDTH = 70.0
WATER = -1.0                                   # the river's level, m


def _swells(x, y):
    return (4.0 * noise.noise(Vector((x / 40.0, y / 40.0, 0.3))) + 1.5 * noise.noise(Vector((x / 13.0, y / 13.0, 1.7)))
            + 0.3 * noise.noise(Vector((x / 3.0, y / 3.0, 4.1))))


_AT_LEAF = _swells(LEAF.x, LEAF.y)


def river_x(y):
    """The near bank's x at y, or None where there's no river."""
    for (xa, ya), (xb, yb) in zip(RIVER_NEAR, RIVER_NEAR[1:]):
        if ya <= y <= yb:
            return lerp(xa, xb, (y - ya) / (yb - ya))
    return None


def height(x, y):
    """The ground's height at (x, y), m."""
    h = (_swells(x, y) - _AT_LEAF) * smooth(3.0, 14.0, math.hypot(x - LEAF.x, y - LEAF.y))
    bank = river_x(y)
    if bank is not None:                       # down a bank 6 m wide to the water, and up the far side
        h = lerp(h, WATER - 0.4, smooth(5.0, -1.0, bank - x) * (1 - smooth(-1.0, 5.0, x - bank - RIVER_WIDTH)))
    return h


def ground_along(x, y, half=3.0):
    """The ground's height at (x, y), averaged along the path `half` m either side, so a camera
    riding it doesn't jolt."""
    return sum(height(x, y + k * half / 3) for k in range(-3, 4)) / 7


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


GX, GY = (-120, 140), (-120, 320)               # the ground modelled at 1 m; flat and low beyond
_vs = [(x, y, height(x, y)) for y in range(GY[0], GY[1] + 1) for x in range(GX[0], GX[1] + 1)]
_w = GX[1] - GX[0] + 1
_fs = [(j * _w + i, j * _w + i + 1, (j + 1) * _w + i + 1, (j + 1) * _w + i)
       for j in range(GY[1] - GY[0]) for i in range(GX[1] - GX[0])]
me = bpy.data.meshes.new("Ground")
me.from_pydata(_vs, [], _fs)
me.shade_smooth()
ground = bpy.data.objects.new("Ground", me)
ground.color = (0.42, 0.42, 0.42, 1.0)
col.objects.link(ground)
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1200, matrix=Matrix.Translation((0, 0, WATER - 0.5)))
obj_from_bm("Ground beyond", bm, 0.42)

# Small things on the ground, so the travelling camera has something to travel past.
for zone, (y0, y1) in ZONES.items():
    bm = bmesh.new()
    n = int((y1 - y0) * {"forest": 15, "woodland": 18, "grassland": 100, "dry": 15}[zone])   # per metre of path
    for _ in range(n):
        x, y = random.uniform(-4, 45), random.uniform(y0, y1)
        if abs(x - LANE_X) < 1.5 and random.random() < 0.8:
            continue
        if in_view(x, y):
            continue
        if zone == "forest":       # ferns
            cone(bm, (x, y, height(x, y)), random.uniform(.25, .45), 0.05, random.uniform(.3, .6), 6)
        elif zone == "woodland":   # brush and stones
            cone(bm, (x, y, height(x, y)), random.uniform(.15, .5), 0.1, random.uniform(.15, .7), 6)
        elif zone == "grassland":  # tufts
            cone(bm, (x, y, height(x, y)), random.uniform(.08, .2), 0.0, random.uniform(.3, .8), 5)
        else:                      # stones
            cone(bm, (x, y, height(x, y)), random.uniform(.15, .6), random.uniform(.1, .3), random.uniform(.1, .35), 5)
    cover = obj_from_bm("Ground cover, " + zone, bm, 0.33)
    if zone == "forest":           # bare until the ferns come back at 03:51, up out of the ground
        a, b = fr(T("03:51")), fr(T("03:52:12"))
        key(cover, "location", [a, b], [-0.8, 0.0], index=2)


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
# because the time-lapse camera sees it come up; west of x 4.5 only the trees among the
# runners stand (with the people, below).
forest_trees = []
for x, y in spaced(int(2 * (Y_WOOD + 28)), (4.5, 62), (-28, Y_WOOD), 3.0, keep_out=[(SKULL.x, SKULL.y, 6)]):
    h, r = random.uniform(11, 22), random.uniform(.2, .45)
    bm = bmesh.new()
    tree_mesh(bm, (0, 0, 0), h, r)
    ob = obj_from_bm("Tree", bm, random.uniform(.2, .3))
    ob.location = (x, y, height(x, y) - 0.1)       # sunk a little, for the slope
    ob["r"] = r
    start = T("03:52") + random.uniform(0, 1.4)
    key_scale(ob, [(start - 1, 0.0), (start, 0.0), (start + 0.4, 0.25), (start + 1.0, 1.0)])
    forest_trees.append(ob)

bm = bmesh.new()
woodland = []
for x, y in spaced(int(0.8 * (Y_GRASS - Y_WOOD)), (5, 60), (Y_WOOD, Y_GRASS), 6.0):   # open woodland
    h, r = random.uniform(7, 14), random.uniform(.2, .4)
    tree_mesh(bm, (x, y, height(x, y) - 0.1), h, r)
    woodland.append((x, y, r))
for x, y in spaced(4, (25, 60), (Y_GRASS, Y_DRY - 1), 12.0):   # lone trees in the grass
    tree_mesh(bm, (x, y, height(x, y) - 0.1), random.uniform(6, 9), .3)
far_trees = obj_from_bm("Trees beyond the forest", bm, 0.26)

# Forest on the other (west) side too, beyond where the travelling camera runs, so the shots from
# the far side of the band (SH1314-1316) look into trees; it grows with the rest.
west_trees = []
for x, y in spaced(int(0.8 * (Y_WOOD + 28)), (-40, -12), (-28, Y_WOOD), 3.5):
    bm = bmesh.new()
    tree_mesh(bm, (0, 0, 0), random.uniform(11, 22), random.uniform(.2, .45))
    ob = obj_from_bm("Tree, west", bm, random.uniform(.2, .3))
    ob.location = (x, y, height(x, y) - 0.1)       # sunk a little, for the slope
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
    ob.location = (x, y, height(x, y) - 0.1)       # sunk a little, for the slope
    start = T("03:51") + random.uniform(0, 1.6)
    key_scale(ob, [(start - 1, 0.0), (start, 0.0), (start + 0.4, 1.0)])
    ferns.append(ob)

# The floor round the leaf (your note, 2026-10-15: it shouldn't be the only leaf on the ground):
# fallen leaves, twigs and grass all through the near view, and low bushes further off, clear of
# the stump. They come with the green, 03:51-03:53, as the ash goes under.
REST_Z = 0.02                  # the leaf comes to rest on top of the litter


def near_floor(x, y, margin=1.0):
    """On the ground the locked camera sees (24 mm: about 37 degrees either side), with a margin."""
    return x > CAM_FIXED.x + 0.25 and abs(y - CAM_FIXED.y) < 0.8 * (x - CAM_FIXED.x) + margin


def floor_points(n, x1):
    """n points on that floor out to x1, as many to the square metre near as far."""
    pts = []
    while len(pts) < n:
        x = random.uniform(CAM_FIXED.x, x1)
        y = CAM_FIXED.y + random.uniform(-1, 1) * (0.8 * (x1 - CAM_FIXED.x) + 1.0)
        if near_floor(x, y):
            pts.append((x, y))
    return pts


litter = []
for grey, n in ((0.34, 900), (0.27, 900), (0.21, 600)):          # leaves, 8-14 cm, three shades, darker than the leaf
    bm = bmesh.new()
    for x, y in floor_points(n, 9.0):
        m = (Matrix.Translation((x, y, height(x, y) + random.uniform(0.003, 0.012)))
             @ Matrix.Rotation(random.uniform(0, 2 * math.pi), 4, 'Z') @ Matrix.Rotation(random.uniform(-0.1, 0.1), 4, 'X')
             @ Matrix.Diagonal((random.uniform(0.04, 0.07), random.uniform(0.022, 0.04), 1, 1)))
        bmesh.ops.create_circle(bm, cap_ends=True, segments=7, radius=1.0, matrix=m)
    litter.append(obj_from_bm("Litter", bm, grey))
bm = bmesh.new()
for x, y in floor_points(160, 9.0):                                # twigs
    if (Vector((x, y)) - LEAF.xy).length < 0.2:
        continue
    r = random.uniform(0.004, 0.012)
    cone(bm, (x, y, height(x, y) + r), r, r * 0.6, random.uniform(0.12, 0.6), 4,
         rot=Matrix.Rotation(random.uniform(0, 2 * math.pi), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'Y'))
litter.append(obj_from_bm("Twigs", bm, 0.17))
bm = bmesh.new()
for x, y in floor_points(320, 9.0):                                # grass, in tufts
    if (Vector((x, y)) - LEAF.xy).length < 0.3:
        continue
    for _ in range(random.randint(3, 6)):
        cone(bm, (x + random.uniform(-0.03, 0.03), y + random.uniform(-0.03, 0.03), height(x, y)), 0.006, 0.0,
             random.uniform(0.08, 0.3), 3,
             rot=Matrix.Rotation(random.uniform(0, 2 * math.pi), 4, 'Z') @ Matrix.Rotation(random.uniform(0.1, 0.45), 4, 'X'))
grass = obj_from_bm("Grass", bm, 0.4)
bm = bmesh.new()
bush_at = []
for x, y in spaced(16, (4.6, 11), (CAM_FIXED.y - 8, CAM_FIXED.y + 8), 1.6):   # low bushes, clear of the stump
    if not near_floor(x, y, 0.5) or abs(y - SKULL.y) < 1.3:
        continue
    sz = random.uniform(0.35, 0.8)
    for _ in range(3):
        ball(bm, (x + random.uniform(-.3, .3) * sz, y + random.uniform(-.3, .3) * sz, height(x, y) + 0.55 * sz),
             (sz * random.uniform(.7, 1), sz * random.uniform(.7, 1), 0.6 * sz), 8)
    bush_at.append((x, y, sz))
bushes = obj_from_bm("Bushes", bm, 0.3)
for ob in litter:
    key(ob, "location", [fr(T("03:51")), fr(T("03:53"))], [-0.03, 0.0], index=2)
for ob in (grass, bushes):                        # up out of the ground, wherever it lies
    key(ob, "location", [fr(T("03:51:12")), fr(T("03:53:12"))], [-1.0, 0.0], index=2)

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
_vs, _fs, _ix = [], [], {}                      # lying on the ground, 40 m round the head, every 2 m
for j in range(-20, 21):
    for i in range(-20, 21):
        if i * i + j * j <= 400:
            _ix[i, j] = len(_vs)
            _vs.append((SKULL.x + 2 * i, SKULL.y + 2 * j, height(SKULL.x + 2 * i, SKULL.y + 2 * j)))
_fs = [(_ix[i, j], _ix[i + 1, j], _ix[i + 1, j + 1], _ix[i, j + 1]) for (i, j) in _ix
       if (i + 1, j) in _ix and (i + 1, j + 1) in _ix and (i, j + 1) in _ix]
me = bpy.data.meshes.new("Ash")
me.from_pydata(_vs, [], _fs)
ash = bpy.data.objects.new("Ash", me)
ash.color = (0.62, 0.62, 0.62, 1.0)
col.objects.link(ash)
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
        [[x] * 4, [-16 * d, -16 * d, 16 * d, 16 * d], [height(x, v) for v in (-16 * d, -16 * d, 16 * d, 16 * d)]])

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
        z = Z0 * (1 - u) + REST_Z - 0.07 * sway * abs(math.sin(ph))
        drift = lerp(HANG.x, LEAF.x, smooth(0.0, 1.0, u))                # (none while the branch is over the landing place)
        p = (drift + 0.05 * sway * math.sin(ph * 0.5), LEAF.y + 0.45 * sway * math.sin(ph), max(z, REST_Z))
        rot = (0.5 * (1 - u) + 0.6 * sway * math.sin(ph), 0.25 * sway * math.sin(ph * 0.5), 0.6 * u)
    else:                                  # whipped up and away by the feet
        w = t - 0.04
        p = (LEAF.x - 0.25 * w, LEAF.y + 3.2 * w + 1.5 * w * w, REST_Z + 2.6 * w - 2.2 * w * w)
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

# When the leaf first comes into the locked frame (below its top edge, at the leaf's depth), and
# the tip down that follows TIP_WAIT later and takes TIP_TIME (your notes, 2026-10-14).
_half_v = math.atan(36.0 * 9 / 16 / 2 / FIXED_LENS)
_in = next((f - T0) / O.FPS for f in lf if leaf_at[f].z <
           CAM_FIXED.z + (leaf_at[f].x - CAM_FIXED.x) * math.tan(_half_v + math.radians(PITCH[0])))
TIP_DOWN = (_in + TIP_WAIT, _in + TIP_WAIT + TIP_TIME)
print("leaf in frame at", O.timecode(int(fr(_in))), "| tip down", O.timecode(int(fr(TIP_DOWN[0]))), "to", O.timecode(int(fr(TIP_DOWN[1]))))

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
        sprint = smooth(4.6, 7.0, v)                          # and on to flat out
        cycle = lerp(lerp(1.5, 2.8, run), 3.6, sprint) * fig.get("stride", 1.0)   # metres per full stride cycle
        phase += 2 * math.pi * v * DT / cycle
        amp = lerp(lerp(0.42, 0.8, run), 1.05, sprint) * min(1.0, v / 1.0)
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
        loc[2].append(height(xs[i], ys[i]) + p.get("z", 0.0) + bob)
        rot[0].append(-(p.get("lean", lerp(lerp(0.04, 0.2, run), 0.32, sprint))))
        rot[1].append(p.get("roll", 0.0))
        rot[2].append(face[i])
    key(fig["root"], "location", frames, loc)
    key(fig["root"], "rotation_euler", frames, rot)
    for lm, sw in zip(fig["limbs"], swing):
        key(lm, "rotation_euler", frames, sw, index=0)
    if visible:
        key_scale(fig["root"], visible)


PF = [f for f in FR if f >= fr(T("04:05"))]        # people exist from 04:05 (they are far off, right)
PT = [(f - T0) / O.FPS for f in PF]

# The band: ten people. (name, height m, lateral place in the pack, place along it, spear)
# Along: + is ahead (left). From 04:27 to 04:29 they fall into a single line, 0.9 m apart.
BAND = [("Lead man", 1.72, 0.0, 3.0, True), ("Woman A", 1.60, 0.7, 2.2, False),
        ("Woman B", 1.62, -0.6, 1.5, False), ("Woman C (centre)", 1.58, 0.2, 0.3, False),
        ("Man D", 1.74, 1.0, -0.2, True), ("Girl", 1.30, -0.3, -0.9, False),
        ("Woman E", 1.62, 0.6, -1.6, False), ("Man F", 1.68, -0.7, -2.2, True),
        ("Man G (rear)", 1.73, 0.4, -3.0, True), ("Man H (rear)", 1.70, -0.4, -3.6, True)]
LINE = {0: 2.7, 1: 3.6, 2: 1.8, 3: 0.9, 4: 0.0, 5: -0.9, 6: -1.8, 7: -2.7, 8: -3.6}   # index 9 falls at the clash
CAT_T = (T("04:17"), T("04:21"))
# The cat (your note, 2026-10-14: a fight would look awkward): it runs down the last but one,
# Man G, leaps and drags him down from behind; the last, Man H, turns back, kills it with one
# thrust of his spear, hauls Man G up, and the two run on and catch the band up. Nobody stops.
SEIZED, RESCUER = 8, 9
GRAB = CAT_T[0] + 1.6                      # the leap lands
KILL = GRAB + 0.7                          # the spear
UP = KILL + 0.3                            # the hand up
CLASH_T = (T("04:24"), T("04:27"))
BABY_T = (T("04:29"), T("04:33"))
GRAVE_T = (T("04:34"), T("04:37:12"))
GRAVE_WHO = 2
GRAVE_PULLER = 7               # Man F, walking up the line behind her, takes her arm and pulls her up and on
_y_grave = YC[int(fr(GRAVE_T[0]))] + LINE[GRAVE_WHO]
GRAVE_UP = next((f - T0) / O.FPS for f in FR if f > fr(GRAVE_T[0]) and YC[f] + LINE[GRAVE_PULLER] >= _y_grave - 0.4)
GLANCE = (T("04:08:16"), T("04:09:10"))   # the lead man looks back over his shoulder (SH1311)
# Trees among the runners, from just past the leaf to where they close up to charge: closer in
# the forest, further apart in the open woodland, and none where the cat comes down on the last men.
_grab_at = (LANE_X + SPREAD[SEIZED][0], Y(GRAB) + SPREAD[SEIZED][1], 4.0)
among = []
for (y0, y1), gap, hr in (((LEAF.y + 7, Y_WOOD), 4.0, (11, 20)), ((Y_WOOD, Y(SPREAD_T[0]) - 3), 6.5, (7, 14))):
    for x, y in spaced(60, (LANE_X - 2.4, 4.5), (y0, y1), gap, keep_out=[_grab_at]):
        h, r = random.uniform(*hr), random.uniform(.2, .4)
        bm = bmesh.new()
        tree_mesh(bm, (0, 0, 0), h, r)
        ob = obj_from_bm("Tree, among the runners", bm, random.uniform(.2, .3))
        ob.location = (x, y, height(x, y) - 0.1)
        ob["r"] = r
        start = T("03:52") + random.uniform(0, 1.4)
        key_scale(ob, [(start - 1, 0.0), (start, 0.0), (start + 0.4, 0.25), (start + 1.0, 1.0)])
        among.append(ob)
forest_trees += among

# What they cut round: (x, y, how near its centre they come), filed by 4 m of path.
OBST = {}
for x, y, r in ([(ob.location.x, ob.location.y, ob["r"] + CLEAR) for ob in forest_trees if ob.location.x < 10]
                + [(x, y, r + CLEAR) for x, y, r in woodland if x < 10] + [(x, y, sz + 0.25) for x, y, sz in bush_at]):
    OBST.setdefault(int(y // 4), []).append((x, y, r))
_side = {}


def dodge(x, y, who):
    """Swerve round whatever stands in the way, passing on the side first nearer it, easing in and
    out over 2 m of path either side."""
    for b in (int(y // 4) - 1, int(y // 4), int(y // 4) + 1):
        for ox, oy, r in OBST.get(b, ()):
            d = abs(y - oy)
            if d < 2.2 and abs(x - ox) < r:
                sgn = _side.setdefault((who, ox, oy), 1 if x >= ox else -1)
                x = ox + sgn * lerp(sgn * (x - ox), r, 1 - smooth(0.4, 2.2, d))
    return x


people = []
band_paths = {}
caught = {}
# Each runner wanders (across and along, on two slow waves of its own), so the band is a crowd,
# not a formation (your note, 2026-10-14), the more so while they're split up; it settles as they
# close up to charge, and again as they fall into a line.
WANDER = [[random.uniform(0, 2 * math.pi) for _ in range(4)] for _ in BAND]
for i, (name, h, dx, dy, spear) in enumerate(BAND):
    fig = figure(name, h, 0.72 if "Woman" in name or name == "Girl" else 0.6, spear)
    xs, ys, face, pose = [], [], [], []
    stopped = held = chase = None
    for f, t in zip(PF, PT):
        u = smooth(20, 22, t)
        s = smooth(LEAF.y + 1.5, LEAF.y + 8.0, YC[f] + dy) * (1 - smooth(*SPREAD_T, t))   # split up past the leaf
        x = LANE_X + lerp(lerp(dx, SPREAD[i][0], s), 0.12 * (i % 2) - 0.06, u)
        y = YC[f] + lerp(lerp(dy, SPREAD[i][1], s), LINE.get(i, dy), u)
        ph, w = WANDER[i], (1.0 - 0.75 * u) * (1.0 + s)
        if i == 0:                                                    # the lead runner keeps to the leaf
            w *= smooth(0.5, 3.0, t)
        x += w * (0.3 * math.sin(0.8 * t + ph[0]) + 0.15 * math.sin(2.1 * t + ph[1]))
        y += w * (0.7 * math.sin(0.5 * t + ph[2]) + 0.3 * math.sin(1.4 * t + ph[3]))
        x = dodge(x, y, i)                                                              # round the trees,
        x = min(x, SKULL.x - 0.75 * (1 - smooth(0.6, 1.5, abs(y - SKULL.y))))           # the stump,
        x = max(x, CAM_FIXED.x + 0.5 * (1 - smooth(0.3, 1.0, abs(y - CAM_FIXED.y))))   # and past the camera
        a, p = 0.0, None
        if i == 0:                                                    # a look back at what's after them
            a = 0.8 * smooth(GLANCE[0], GLANCE[0] + 0.25, t) * (1 - smooth(GLANCE[1] - 0.25, GLANCE[1], t))
        if i == GRAVE_PULLER and GRAVE_UP - 0.4 < t < GRAVE_UP + 0.9:  # reaches down for her arm
            k = smooth(GRAVE_UP - 0.4, GRAVE_UP, t) * (1 - smooth(GRAVE_UP + 0.5, GRAVE_UP + 0.9, t))
            x -= 0.35 * k
            p = {"arm_l": -1.1 * k, "lean": 0.25 * k}
        if spear and CHARGE - 0.1 < t < MEET + 0.4:                  # spears levelled for the charge
            p = {"arms": -1.6, "lean": 0.3}
        if i == SEIZED and t > GRAB:                                  # dragged down from behind, then hauled up
            if held is None:
                held = (x, y)
            down = smooth(GRAB, GRAB + 0.25, t) * (1 - smooth(UP, UP + 0.5, t))
            if t < UP + 0.2:
                x, y = held[0], held[1] - 0.6 * smooth(GRAB, KILL, t)
            if down > 0.01:
                p = {"lean": -1.3 * down, "z": 0.1 * down, "legs": 0.3 * down, "arms": 0.9 * down}
        if i == RESCUER and GRAB - 0.4 < t:                           # turns back, kills it, hauls him up
            k_ = f - PF[0]
            sx, sy = band_paths[SEIZED][0][k_], band_paths[SEIZED][1][k_]
            side = (sx + 0.55, sy + 0.9)                              # beside him, between him and the band
            reach = smooth(GRAB - 0.4, GRAB + 0.3, t)
            if t < UP + 0.2:
                x, y = lerp(x, side[0], reach), lerp(y, side[1], reach)
            a = math.pi * smooth(GRAB - 0.2, GRAB + 0.1, t) * (1 - smooth(UP + 0.2, UP + 0.6, t))
            if KILL - 0.35 < t < KILL + 0.2:                          # the thrust
                p = {"arms": -1.9, "lean": 0.45}
            elif UP - 0.05 < t < UP + 0.6:                            # the hand up
                p = {"arm_l": -1.1, "lean": 0.3}
        if i in (SEIZED, RESCUER) and t >= UP + 0.2:                  # then the two run the band down again,
            if chase is None:                                         # flat out, from where they are
                chase = [xs[-1], ys[-1]]
            chase[1] = min(y, chase[1] + CATCH_SPEED * smooth(UP + 0.2, UP + 1.0, t) * DT)
            chase[0] += max(-2.0 * DT, min(2.0 * DT, x - chase[0]))
            if chase[1] >= y and i not in caught:
                caught[i] = t
            x, y = chase
        if i == 9 and t > MEET + 0.3:                                 # one of ours goes down at the clash
            if stopped is None:
                stopped = (x, y)
            k = smooth(MEET + 0.3, MEET + 0.7, t)
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
    animate(fig, PF, xs, ys, face, pose, visible=[(T("04:04"), 0), (T("04:05"), 1)])
    people.append(fig)
    band_paths[i] = (xs, ys)

# The cat: lion-sized, what the band is running from. It is after them from before the leaf, far
# back; in SH1313 it's charging, closing about 7 m a second (your note, 2026-10-14: faster); it
# trails them, catches them from behind (the right) at 04:18:14, springs, goes down and is left
# behind; it cuts round the trees as they do. It bounds as it runs: up and down, nose rocking, at a gallop's rate.
bm = bmesh.new()
ball(bm, (0, 0, 0.78), (0.3, 0.95, 0.36), 10)
ball(bm, (0, 1.0, 0.95), (0.2, 0.24, 0.2), 8)
for sx in (-0.2, 0.2):
    for sy in (-0.6, 0.65):
        cone(bm, (sx, sy, 0), 0.07, 0.09, 0.7, 5)
cat = obj_from_bm("Big cat", bm, 0.16)
cl, cr = [[], [], []], [[], [], []]
down_at = None
xs8, ys8 = band_paths[SEIZED]
for f, t in zip(PF, PT):
    idx = f - PF[0]
    rear = YC[f] - 3.6
    gap = curve([(-1.0, 40.0), (3.6, 26.0), (5.2, 15.0), (CAT_T[0] - 0.5, 10.0)], t)   # the charge, then on their heels
    x, y = dodge(LANE_X + 0.1, rear - gap, "cat"), rear - gap
    k = smooth(CAT_T[0] - 0.5, GRAB, t)                               # runs him down
    x, y = lerp(x, xs8[idx], k), lerp(y, ys8[idx] - 0.7, k)
    run = 1 - smooth(GRAB - 0.1, GRAB, t)
    z = run * 0.18 * abs(math.sin(math.pi * 2.6 * t))                 # the gallop
    z += 0.6 * math.sin(math.pi * smooth(GRAB - 0.45, GRAB, t)) * run  # the leap
    nose = run * 0.12 * math.sin(2 * math.pi * 2.6 * t)
    roll = 0.0
    if t >= GRAB:                                                     # on him, from behind
        x, y, z = xs8[idx], ys8[idx] - 0.5, 0.3
        nose = 0.35 + 0.1 * math.sin(2 * math.pi * 4 * t)
    if t >= KILL:                                                     # speared: rolls off, and lies still
        if down_at is None:
            down_at = (x, y)
        kk = smooth(KILL, KILL + 0.3, t)
        x, y, z, roll, nose = down_at[0] + 0.4 * kk, down_at[1] - 0.4 * kk, 0.0, 1.5 * kk, 0.0
    z += height(x, y)
    for i, v in enumerate((x, y, z)):
        cl[i].append(v)
    for i, v in enumerate((nose, roll, 0.0)):
        cr[i].append(v)
key(cat, "location", PF, cl)
key(cat, "rotation_euler", PF, cr)
key_scale(cat, [(-1.2, 0), (-1.0, 1)])

# The other band: six, coming the other way (left to right), charging too, and slowing as they
# meet ours at MEET.
ymeet = YC[int(fr(MEET))]
_o, _run = {}, 0.0
for f in range(int(fr(MEET)), F1 + 1):
    _o[f] = _run
    _run += curve([(MEET - 0.4, OTHER_SPEED), (MEET + 0.5, 1.5)], (f - T0) / O.FPS) * DT
_run = 0.0
for f in range(int(fr(MEET)) - 1, F0 - 1, -1):
    _run -= curve([(MEET - 0.4, OTHER_SPEED), (MEET + 0.5, 1.5)], (f - T0) / O.FPS) * DT
    _o[f] = _run
other_paths = []
for j, (dx, dy, falls) in enumerate([(0.9, 0.0, False), (-0.5, 1.2, True), (0.3, 2.3, False),
                                     (-0.9, 3.1, False), (0.6, 4.2, True), (-0.2, 5.4, False)]):
    fig = figure("Other band %d" % (j + 1), random.uniform(1.6, 1.76), 0.22, spear=True)
    xs, ys, face, pose = [], [], [], []
    stopped = None
    for f, t in zip(PF, PT):
        x, y = LANE_X + dx, ymeet + dy - _o[f] + 0.5
        p = None
        if falls and t > MEET + 0.2 + 0.2 * j:
            if stopped is None:
                stopped = (x, y)
            k = smooth(MEET + 0.2 + 0.2 * j, MEET + 0.6 + 0.2 * j, t)
            x, y = stopped
            p = {"lean": -1.45 * k, "z": 0.12 * k, "legs": 0.0, "arms": 0.3}
        elif MEET - 1.5 < t < MEET + 0.8:
            p = {"arms": -1.7, "lean": 0.3}
        xs.append(x)
        ys.append(y)
        face.append(math.pi)
        pose.append(p)
    animate(fig, PF, xs, ys, face, pose, visible=[(CLASH_T[0] - 4, 0), (CLASH_T[0] - 3.5, 1)])
    other_paths.append((xs, ys))

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
    bl[2].append(height(bl[0][-1], bl[1][-1]) + 1.12 + 0.1 * math.sin(math.pi * k))
key(baby, "location", bf, bl)
key_scale(baby, [(BABY_T[0] - 0.3, 0), (BABY_T[0] - 0.2, 1), (BABY_T[1] + 0.1, 1), (BABY_T[1] + 0.2, 0)])

# The small grave, at the edge of the path on the camera's side.
gi = PF.index(int(fr(GRAVE_T[0])))
grave_pos = (band_paths[GRAVE_WHO][0][gi] - 0.75, band_paths[GRAVE_WHO][1][gi])
grave_pos = (*grave_pos, height(*grave_pos))
bm = bmesh.new()
ball(bm, grave_pos, (0.3, 0.5, 0.16), 10)
grave = obj_from_bm("Small grave", bm, 0.22)

# ---------------------------------------------------------------- the river (04:30)
# It runs north (to the left), east of the path: it comes in from the far right and
# runs alongside from just past where the dry country begins. Banks green: reeds, trees, hippos
# in the shallows.
near = RIVER_NEAR
bm = bmesh.new()
vs = [bm.verts.new((x, y, WATER)) for x, y in near] + [bm.verts.new((x + RIVER_WIDTH, y, WATER)) for x, y in reversed(near)]
bm.faces.new(vs)
river = obj_from_bm("River", bm, 0.14)
bm = bmesh.new()
for (xa, ya), (xb, yb) in zip(near, near[1:]):
    for _ in range(int(math.hypot(xb - xa, yb - ya) * 3.5)):
        u = random.random()
        rx, ry = lerp(xa, xb, u) - random.uniform(0, 2.5), lerp(ya, yb, u) + random.uniform(-1, 1)
        cone(bm, (rx, ry, height(rx, ry)),
             random.uniform(.05, .12), 0.0, random.uniform(1.5, 3.2), 4)       # reeds and papyrus
for y in range(int(Y_DRY) - 1, int(Y_DRY) + 139, 9):
    for bx in (random.uniform(7.5, 9.5), 84 + random.uniform(0, 5)):
        by = y + random.uniform(-3, 3)
        tree_mesh(bm, (bx, by, height(bx, by) - 0.1), random.uniform(6, 11), .25)
reeds = obj_from_bm("Reeds and bank trees", bm, 0.3)
bm = bmesh.new()
for x, y in ((14.5, Y_DRY + 7), (16, Y_DRY + 10), (15, Y_DRY + 17), (18, Y_DRY + 23)):
    ball(bm, (x, y, WATER), (0.75, 1.9, 0.75), 10)                             # hippos, 3.8 m
hippos = obj_from_bm("Hippos", bm, 0.2)

# ---------------------------------------------------------------- the trunks that wipe the frame
for t, rel in WIPES:
    f = int(fr(t))
    bm = bmesh.new()
    cone(bm, (0, 0, 0), 0.5, 0.42, 22, 10)
    trunk = obj_from_bm("Trunk that crosses the lens", bm, 0.12)
    tx, ty = LANE_X - CAM_DIST + 1.2 * curve(CAM_LENS, t, ease=True) / 35.0, CAM_Y[f] + rel
    trunk.location = (tx, ty, height(tx, ty) - 0.1)


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


# Camera 1, 03:42-04:08, one unbroken shot, low, right up next to the dead animal, square to the
# band's path. It doesn't move but to tip down a little with the leaf; then, as the first foot
# comes down on the leaf, it turns left with that runner and follows him (your note, 2026-10-15):
# at once, taking up his pace over TRACK_IN, smoothly, with a little room ahead of him, and up
# from the ground to his legs.
cam1 = camera("CAM unbroken")
f1 = [f for f in FR if f < fr(ACTION)]
lead_x, lead_y = band_paths[0]
pos, tgt = [], []
for f in f1:
    t = (f - T0) / O.FPS
    pitch = math.radians(lerp(PITCH[0], PITCH[1], smooth(TIP_DOWN[0], TIP_DOWN[1], t)))
    yaw = 0.0
    if t > 0:
        k = f - PF[0]
        d = Vector((lead_x[k] - CAM_FIXED.x, lead_y[k] + 0.4 * smooth(0.1, 0.6, t) - CAM_FIXED.y))
        yaw = math.atan2(d.y, d.x) * smooth(0, TRACK_IN, t)
        pitch = lerp(pitch, math.atan2(0.45 + height(lead_x[k], lead_y[k]) - CAM_FIXED.z, d.length), smooth(0, 0.4, t))
    pos.append(CAM_FIXED)
    tgt.append(CAM_FIXED + Vector((math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))) * 4.0)
key_camera(cam1, f1, pos, tgt)
key_lens(cam1, f1, [FIXED_LENS] * len(f1))

# Camera 2, 04:08-04:15: fast cuts of the run, to show they're running from something.
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
        "1314": (5, 0.5, (4.0, 2.0, 1.2), 1.0, None, 28),         # the girl, running hard, wider, from ahead of her
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
    stand.z = off[2] + height(stand.x, stand.y)                # its height is above the ground where it stands
    for f in range(sh["start"], sh["end"]):
        i = f - PF[0]
        f2.append(f)
        pos.append(stand if when is not None else
                   Vector((xs[i] + off[0], ys[i] + off[1], off[2] + ground_along(xs[i] + off[0], ys[i] + off[1], 1.0))))
        tgt.append(Vector((xs[k] + hold[0], ys[k] + hold[1], look_z + height(xs[k] + hold[0], ys[k] + hold[1]))) if hold
                   else Vector((xs[i], ys[i], look_z + height(xs[i], ys[i]))))
        lens.append(mm)
key_camera(cam2, f2, pos, tgt)
key_lens(cam2, f2, lens)
# No trunk where a camera stands or runs.
for tr in list(among):
    if any((p.xy - tr.location.xy).length < 0.9 for p in pos):
        among.remove(tr)
        forest_trees.remove(tr)
        bpy.data.objects.remove(tr)
print("trees among the runners", len(among))
assert f2[0] == fr(ACTION) and f2[-1] == fr(TRAVEL) - 1

# Camera 3, 04:15-04:43: travelling beside the band, looking east, a little ahead of the centre.
cam3 = camera("CAM travelling")
f3 = [f for f in FR if f >= fr(TRAVEL)]
pos, tgt = [], []
for f in f3:
    t = (f - T0) / O.FPS
    y = CAM_Y[f]
    pos.append(Vector((LANE_X - CAM_DIST, y, CAM_HEIGHT + ground_along(LANE_X - CAM_DIST, y))))   # 1.5 m above its ground
    tgt.append(Vector((LANE_X, y, 1.3 + ground_along(LANE_X, y))))
key_camera(cam3, f3, pos, tgt)
key_lens(cam3, f3, [curve(CAM_LENS, (f - T0) / O.FPS, ease=True) for f in f3])

# When the other band first comes into the travelling camera's frame, against the charge.
_seen = next(((f - T0) / O.FPS for f in f3 if f >= fr(CLASH_T[0] - 3.5) for xs_, ys_ in other_paths
              if abs(math.atan2(ys_[f - PF[0]] - CAM_Y[f], xs_[f - PF[0]] - (LANE_X - CAM_DIST)))
              < math.atan(18.0 / curve(CAM_LENS, (f - T0) / O.FPS, ease=True))), None)
print("charge", O.timecode(int(fr(CHARGE))), "| other band in frame", O.timecode(int(fr(_seen))),
      "| they meet", O.timecode(int(fr(MEET))))
print("the two from the cat catch the band up", {BAND[i][0]: O.timecode(int(fr(t))) for i, t in caught.items()})

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
r.use_stamp_note, r.stamp_note_text = True, "Opening layout, beats 12-13, grey, fourteenth pass"
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
elif [a for a in sys.argv if a.startswith("clean=")]:
    # clean=04:15:00-04:18:12 -> work/aitest/clean-<range>.mp4 and its first and last frames,
    # with no burn-in, as input for the AI video tests (ai_video_test.py)
    rng = [a for a in sys.argv if a.startswith("clean=")][0][6:]
    a_, b_ = (O.frame(x) for x in rng.split("-"))
    r.use_stamp = False
    d = O.WORK / "aitest"
    d.mkdir(parents=True, exist_ok=True)
    tag = rng.replace(":", "")
    r.image_settings.media_type = 'IMAGE'
    r.image_settings.file_format = 'PNG'
    for f_, name in ((a_, "first"), (b_ - 1, "last")):
        scene.frame_set(f_)
        r.filepath = str(d / ("clean-%s-%s.png" % (tag, name)))
        bpy.ops.render.render(write_still=True)
    r.image_settings.media_type = 'VIDEO'
    r.image_settings.file_format = 'FFMPEG'
    scene.frame_start, scene.frame_end = a_, b_ - 1
    r.filepath = str(d / ("clean-%s.mp4" % tag))
    bpy.ops.render.render(animation=True)
    print("clean", r.filepath)
elif RENDER:
    bpy.ops.render.render(animation=True)
    print("playblast", out)
