"""The face in the series' painted look: one head, close, one expression (the style test, PLAN §9,
item 3; Discussion 006, round 4).

    blender -b --factory-startup -P face_test.py               bake, paint, render: stills, clip, sheet
    blender -b --factory-startup -P face_test.py -- still      the two stills only
    blender -b --factory-startup -P face_test.py -- reuse      the paint already made (work/styletest/paint/)
    blender -b --factory-startup -P face_test.py -- check      grey front and side views, to set the shape
    blender -b --factory-startup -P face_test.py -- baked      the light painted into the textures, as before

The head is MPFB2's, shaped after Corbin's photos (work/face/, out of git) with its own sliders
(FACE below): long and lean, a narrow head, high cheekbones over hollow cheeks, a low straight
brow, deep-set eyes, a long straight nose, a full lower lip, a firm square jaw and chin, a long
neck. Then its forms are given more definition (your note, 2026-10-15: the models should have
it, not the shadows or the lines): the head is pushed away from a smoothed copy of itself, so its
ridges and hollows stand out (DEFINE). The hair is sculpted in locks, as Arcane's is: dark brown,
parted on his left, swept across the forehead and down to the jaw, as in the photos (hair()).
It's a likeness to judge the look by, not the design of the recurring face, which comes after
(PLAN §5). The eyes stay closed, as in the photos and as the Opening's face first is. The
expression is the Opening's last, which you've called right for it: one breath drawn in (05:00),
the nostrils widening, the lips parting a little, the chin lifting.

It's painted with real brush strokes (your note, 2026-10-15: genuinely painted): Blender bakes
each surface's colour into the surface's own texture (Cycles), and brush.py paints that over with
strokes that follow the form, big brushes then small. The light isn't in the paint (your note,
2026-10-15: the shadows real, not painted): the renderer lights the head live, and its light, cast
shadows and all, is turned into the painter's colours, a cooler, darker paint in shadow and a
short soft turn between (live_mat). The sun comes in through a window on his right, so one side
of his face is lit and the other is in its own shadow, and the window's bars cast theirs; a weak
cool fill; a rim from behind. face-front-raw.png is the same light shaded plainly, for comparison.
-- baked: the earlier way, the light baked into the paint as a painter fixes it.
No outline. Against a dark, cool backdrop. Over the paint, as a face has (your note, 2026-10-15),
very light marks: freckles, two small moles, a faint birthmark, a thin pale scar.

Writes work/styletest/face-front.png (straight on, as your frame of Vi), face-neutral.png and
face-breath.png (the left three-quarter), face-breath.mp4 and face-sheet.png, and the paint in
work/styletest/paint/.
"""
import importlib
import json
import math
import pathlib
import random
import subprocess
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Euler, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402
import humans as H  # noqa: E402
import painted as P  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STILL, CHECK, REUSE = "still" in ARGS, "check" in ARGS, "reuse" in ARGS
LIVE = "baked" not in ARGS                         # the light from the renderer, not painted in (your note, 2026-10-15)
OUT = O.WORK / "styletest"
PAINT = OUT / "paint"
BRUSH = pathlib.Path(__file__).resolve().parent / "brush.py"
FPS = O.FPS
F0, BREATH, F1 = 1, (30, 66), 96                  # still, then one breath in over 1.5 s, held
SKIN_RES, HAIR_RES = 4096, 2048

# The head after the photos: MPFB target -> weight (0-1; each target is one side of a slider).
FACE = {"head-oval": 0.6, "head-scale-horiz-decr": 0.3, "head-scale-vert-incr": 0.2,
        "forehead-scale-vert-incr": 0.15,
        "eyebrows-trans-down": 0.1, "eyebrows-angle-down": 0.15,
        "l-eye-push1-in": 0.1, "r-eye-push1-in": 0.1,
        "nose-scale-vert-incr": 0.35, "nose-scale-depth-incr": 0.25, "nose-hump-decr": 0.25,
        "nose-point-up": 0.15, "nose-point-width-decr": 0.2,
        "mouth-lowerlip-volume-incr": 0.2, "mouth-cupidsbow-incr": 0.3, "mouth-upperlip-volume-decr": 0.05,
        "chin-prominent-incr": 0.5, "chin-height-incr": 0.25, "chin-width-incr": 0.2, "chin-bones-incr": 0.35,
        "l-cheek-bones-incr": 0.4, "r-cheek-bones-incr": 0.4,
        "l-cheek-volume-decr": 0.45, "r-cheek-volume-decr": 0.45,
        "l-cheek-inner-decr": 0.25, "r-cheek-inner-decr": 0.25,
        "neck-scale-vert-incr": 0.25, "neck-scale-horiz-decr": 0.15}
CLOSED = {"eye-left-closure": 0.08, "eye-right-closure": 0.08}     # open naturally for the test (your call, 2026-10-16); 1.0 shuts them, as the Opening's face is
EYE_COLOUR = ((0.42, 0.33, 0.16), (0.3, 0.17, 0.08))   # the iris: hazel, with a brown ring round the pupil (yours, 2026-10-16)
BREATH_IN = {"nose-left-dilatation": 0.8, "nose-right-dilatation": 0.8, "mouth-open": 0.09}
LIFT = {"Neck1": -4.0, "Head": -5.0}              # degrees about each bone's x: the chin up
DEFINE = (0.25, 10)                                # how far the forms are pushed from their smoothed copy; how smooth
PLANES = (0.5, 0.75, 0.018)                        # how far the forms are flattened onto their planes; how much the shading follows them; their size (m)
BROWS, LASHES = "eyebrow012", "eyelashes01"
STUBBLE = 0.0                                      # how much stubble shows (0.3 for the photos' light stubble; 0: clean-shaven, your call, 2026-10-16)

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

sets = H.vertex_sets(human, ["helper-l-eye", "helper-r-eye", "body", "scalp"])
MW = human.matrix_world.copy()
pts = [MW @ v.co for v in human.data.vertices]
eye_ix = sets["helper-l-eye"] | sets["helper-r-eye"]
E = sum((pts[i] for i in eye_ix), Vector()) / len(eye_ix)          # between the eyes


def ramp01(a, b, x):
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


def nose(p):
    """The nose, from the bridge to the nostrils."""
    d = p - E
    return ramp01(0.028, 0.012, abs(d.x)) * ramp01(0.006, -0.008, d.z) * ramp01(-0.074, -0.06, d.z) * ramp01(0.0, -0.015, d.y)


# ---------------------------------------------------------------- definition in the forms
def define(k, iters):
    """Push the head away from a smoothed copy of itself (an unsharp mask on the shape), so its
    ridges and hollows (brow, cheekbones, nose, lips, jaw) read more clearly; fading out down the
    neck, and leaving the eyes' helpers alone."""
    me = human.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    body = np.zeros(n, bool)
    body[list(sets["body"])] = True
    ed = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ed)
    ed = ed.reshape(-1, 2)
    ed = ed[body[ed[:, 0]] & body[ed[:, 1]]]
    deg = np.bincount(ed.ravel(), minlength=n).astype(float)
    sm = co.copy()
    for _ in range(iters):
        acc = np.zeros_like(sm)
        np.add.at(acc, ed[:, 0], sm[ed[:, 1]])
        np.add.at(acc, ed[:, 1], sm[ed[:, 0]])
        has = deg > 0
        sm[has] += 0.5 * (acc[has] / deg[has, None] - sm[has])
    eyes = [sum((pts[i] for i in sets[g]), Vector()) / len(sets[g]) for g in ("helper-l-eye", "helper-r-eye")]
    w = np.array([ramp01(-0.2, -0.13, (p - E).z) * min(ramp01(0.015, 0.05, (p - c).length) for c in eyes)
                  * (1 + 0.6 * nose(p)) for p in pts]) * body   # fading out round the eyes; the nose more (your note)
    me.vertices.foreach_set("co", (co + k * w[:, None] * (co - sm)).ravel())
    me.update()
    nrm = np.empty(n * 3)
    me.vertices.foreach_get("normal", nrm)
    ridge = np.sum((co - sm) * nrm.reshape(-1, 3), axis=1)               # how far each point stands out of the smoothed form
    face = np.array([ramp01(-0.15, -0.12, (p - E).z) * ramp01(0.03, 0.0, (p - E).y) for p in pts]) * body
    top = np.percentile(ridge[face > 0.5], 97) if (face > 0.5).any() else 1.0
    low = -np.percentile(ridge[face > 0.5], 4) if (face > 0.5).any() else 1.0
    return np.clip(ridge / max(top, 1e-6), 0, 1) * face, np.clip(-ridge / max(low, 1e-6), 0, 1) * face


RIDGE, HOLLOW = define(*DEFINE) if (not CHECK or "define" in ARGS) else (np.zeros(len(human.data.vertices)),) * 2


def planes(flatten, size, lam=1.0, seed=1):
    """Vi's face is built in planes (your note, 2026-10-15: a slightly blocky look in the nose's ridge,
    the lips, the chin, under the eyes, the ears). The head's surface is grouped into small flat
    patches, by where each face is and which way it faces (k-means), the forms flattened part way
    onto them, so they meet in soft creases as a sculptor's planes do. Not round the eyes, and
    fading out down the neck. Returns each face's plane, for the shading."""
    me = human.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    eyes = [sum((pts[i] for i in sets[g]), Vector()) / len(sets[g]) for g in ("helper-l-eye", "helper-r-eye")]
    def gentle(p):                                  # the lips and the nose's tip and wings keep most of their roundness
        d = p - E
        lips = ramp01(1.4, 0.9, ((d.x / 0.028) ** 2 + ((d.z + 0.078) / 0.011) ** 2) ** 0.5)
        tip = ramp01(0.03, 0.018, abs(d.x)) * ramp01(-0.042, -0.05, d.z) * ramp01(-0.075, -0.066, d.z)
        return 1 - 0.7 * max(lips, tip)

    w = np.array([ramp01(E.z - 0.2, E.z - 0.15, p.z) * min(ramp01(0.014, 0.024, (p - c).length) for c in eyes) * gentle(p)
                  for p in pts])
    body = np.zeros(n, bool)
    body[list(sets["body"])] = True
    w *= body
    sel = [pl.index for pl in me.polygons if all(body[v] for v in pl.vertices) and max(w[v] for v in pl.vertices) > 0]
    C = np.array([tuple(me.polygons[f].center) for f in sel])
    N = np.array([tuple(me.polygons[f].normal) for f in sel])
    A = np.array([me.polygons[f].area for f in sel])
    X = np.hstack([C / size, N * lam])
    rng = np.random.default_rng(seed)
    seeds, d = [int(rng.integers(len(C)))], np.full(len(C), np.inf)
    while True:                                     # seeds about one plane's size apart
        d = np.minimum(d, np.linalg.norm(C - C[seeds[-1]], axis=1))
        j = int(d.argmax())
        if d[j] < size:
            break
        seeds.append(j)
    K = X[seeds].copy()
    for _ in range(15):
        lab = ((X[:, None, :] - K[None, :, :]) ** 2).sum(-1).argmin(1)
        for k in range(len(K)):
            m = lab == k
            if m.any():
                a = A[m][:, None]
                nk = (N[m] * a).sum(0)
                K[k] = np.concatenate([(C[m] * a).sum(0) / a.sum() / size, nk / (np.linalg.norm(nk) + 1e-12) * lam])
    Ck, Nk = K[:, :3] * size, K[:, 3:] / lam
    Nk /= np.linalg.norm(Nk, axis=1, keepdims=True) + 1e-12
    V = np.concatenate([np.array(me.polygons[f].vertices) for f in sel])
    L = np.concatenate([np.full(len(me.polygons[f].vertices), lab[i]) for i, f in enumerate(sel)])
    for _ in range(2):                              # each point toward the planes of the faces round it
        proj = co[V] - Nk[L] * ((co[V] - Ck[L]) * Nk[L]).sum(1)[:, None]
        tgt, cnt = np.zeros_like(co), np.zeros(n)
        np.add.at(tgt, V, proj)
        np.add.at(cnt, V, 1.0)
        has = cnt > 0
        co[has] += flatten * w[has, None] * (tgt[has] / cnt[has, None] - co[has])
    me.vertices.foreach_set("co", co.ravel())
    me.update()
    print("planes: %d faces in %d planes" % (len(sel), len(K)))
    return {f: Nk[lab[i]] for i, f in enumerate(sel)}, w


def plane_shading(face_plane, w, amount):
    """The shading follows the planes: each point's normal turned toward the planes round it, so
    across a plane the light is even and it turns where the planes meet, in a short soft crease, as
    on Vi, instead of rolling round the whole form."""
    me = human.data
    n = len(me.vertices)
    vn = np.empty(n * 3)
    me.vertices.foreach_get("normal", vn)
    vn = vn.reshape(-1, 3)
    acc, cnt = np.zeros((n, 3)), np.zeros(n)
    for f, nk in face_plane.items():
        for v in me.polygons[f].vertices:
            acc[v] += nk
            cnt[v] += 1
    has = cnt > 0
    pn = acc[has] / np.linalg.norm(acc[has], axis=1, keepdims=True).clip(1e-12)
    a = (amount * w[has])[:, None]
    vn[has] = (1 - a) * vn[has] + a * pn
    vn /= np.linalg.norm(vn, axis=1, keepdims=True).clip(1e-12)
    me.normals_split_custom_set_from_vertices([tuple(v) for v in vn])


PLANE_OF, PLANE_W = planes(PLANES[0], PLANES[2]) if (not CHECK or "define" in ARGS) else ({}, None)
pts = [MW @ v.co for v in human.data.vertices]

# Stubble, as in the photos: a soft mask over the jaw, the chin and the upper lip, kept off the
# lips and stopping in front of the ears, measured from the eyes.
mask = []
for p in pts:
    d = p - E
    m = ramp01(-0.045, -0.062, d.z) * ramp01(-0.15, -0.13, d.z)       # from under the nose to the jaw's edge
    m *= ramp01(0.06, 0.04, d.y)                                         # in front of the ears
    m *= 1 - ramp01(0.045, 0.06, abs(d.x)) * ramp01(-0.07, -0.04, d.z)  # up the cheeks only at the jaw
    lip = ((d.x / 0.028) ** 2 + ((d.z + 0.078) / 0.011) ** 2) ** 0.5
    m *= ramp01(0.85, 1.25, lip)                                         # not on the lips
    mask.append(m)
human.data.attributes.new("stubble", 'FLOAT', 'POINT').data.foreach_set("value", mask)
lips = [ramp01(1.15, 0.8, (((p - E).x / 0.028) ** 2 + (((p - E).z + 0.078) / 0.011) ** 2) ** 0.5) * ramp01(-0.01, -0.03, (p - E).y)
        for p in pts]                                                    # the lips, for their own colour
human.data.attributes.new("lip_tint", 'FLOAT', 'POINT').data.foreach_set("value", lips)
upper = [l * ramp01(-0.08, -0.074, (p - E).z) for l, p in zip(lips, pts)]
human.data.attributes.new("upper_lip", 'FLOAT', 'POINT').data.foreach_set("value", upper)
EYES = [sum((pts[i] for i in sets[g]), Vector()) / len(sets[g]) for g in ("helper-l-eye", "helper-r-eye")]


def under_eye(p):
    """Below each closed eye, where the lids' hollow takes a shadow a painter would leave light."""
    return max(ramp01(1.0, 0.45, (((p - c).x / 0.026) ** 2 + (((p - c).z + 0.014) / 0.013) ** 2) ** 0.5)
               * ramp01(0.015, 0.0, (p - c).y) for c in EYES)


def warmth(p):
    """Where a painter warms the skin: the cheeks, the nose's tip, the ears."""
    d = p - E
    cheeks = max(ramp01(1.0, 0.2, (((p - c).x - 0.012 * (1 if c.x > E.x else -1)) ** 2 + ((p - c).z + 0.035) ** 2) ** 0.5 / 0.024)
                 for c in EYES)
    nose = ramp01(1.0, 0.2, ((d.x ** 2 + (d.z + 0.045) ** 2) ** 0.5) / 0.014) * ramp01(-0.02, -0.04, d.y)
    ears = ramp01(0.06, 0.072, abs(d.x)) * ramp01(-0.06, -0.035, d.z) * ramp01(0.04, 0.0, d.z)
    return max(cheeks, nose, ears)


def upper_lid(p):
    """The closed upper lids, painted smooth (your note: they looked patchy)."""
    return max(ramp01(0.02, 0.015, (p - c).length) * ramp01(c.z - 0.005, c.z - 0.001, p.z) * ramp01(0.004, -0.004, (p - c).y)
               for c in EYES)


def freckles(p):
    """Where freckles fall: across the nose and the cheeks under the eyes."""
    d = p - E
    cheeks = max(ramp01(1.0, 0.35, (((p - c).x / 0.028) ** 2 + (((p - c).z + 0.026) / 0.015) ** 2) ** 0.5) for c in EYES)
    bridge = ramp01(0.016, 0.008, abs(d.x)) * ramp01(-0.052, -0.04, d.z) * ramp01(0.0, -0.012, d.z)
    return max(cheeks, bridge) * ramp01(0.0, -0.02, d.y)


human.data.attributes.new("under_eye", 'FLOAT', 'POINT').data.foreach_set("value", [under_eye(p) for p in pts])
human.data.attributes.new("lid_region", 'FLOAT', 'POINT').data.foreach_set("value", [upper_lid(p) for p in pts])
human.data.attributes.new("freckles", 'FLOAT', 'POINT').data.foreach_set("value", [freckles(p) for p in pts])
human.data.attributes.new("warmth", 'FLOAT', 'POINT').data.foreach_set("value", [warmth(p) for p in pts])

rig = HS.add_builtin_rig(human, "cmu_mb")
for pb in rig.pose.bones:
    pb.rotation_mode = 'XYZ'
fitted = {}                                        # fitted after the rig, so they're rigged with it
for kind, what in (("eyes", "high-poly"), ("eyebrows", BROWS), ("eyelashes", LASHES)):
    ob = HS.add_mhclo_asset(str(H.mpfb_data(kind) / what / (what + ".mhclo")), human,
                            asset_type=kind.capitalize(), subdiv_levels=0)
    fitted[kind] = ob
for t, w in BREATH_IN.items():
    TS.load_target(human, str(SYSTEM / "expression" / "units" / "caucasian" / (t + ".target.gz")), weight=0.0, name=t)


def painter_masks():
    """One colour per point for the painter: red, the shade under the eyes to leave light; green,
    the ridges of the forms, where highlights go; blue, the line of the closed lids, where the lashes
    meet the skin, painted bold and dark, as Vi's lids are."""
    from mathutils.kdtree import KDTree
    lash = fitted["eyelashes"]
    lv = [lash.matrix_world @ v.co for v in lash.data.vertices]
    kd = KDTree(len(lv))
    for i, v in enumerate(lv):
        kd.insert(v, i)
    kd.balance()
    cols = []
    for i, p in enumerate(pts):
        lid = ramp01(0.0028, 0.0008, kd.find(p)[2])
        near_eye = min((p - c).length for c in EYES)
        cols.extend((under_eye(p), float(RIDGE[i]) * ramp01(0.016, 0.026, near_eye), lid, 1.0))
    human.data.attributes.new("paint_masks", 'FLOAT_COLOR', 'POINT').data.foreach_set("color", cols)
    hollow = [float(HOLLOW[i]) * ramp01(0.016, 0.028, min((p - c).length for c in EYES)) for i, p in enumerate(pts)]
    human.data.attributes.new("hollow", 'FLOAT', 'POINT').data.foreach_set("value", hollow)   # the forms' hollows, away from the eyes
    # and a second: red, the lips (where to look for their edge); green, the closed lids; blue, the nose
    cols = [v for l, p in zip(lips, pts) for v in (l, upper_lid(p), nose(p), 1.0)]
    human.data.attributes.new("paint_masks2", 'FLOAT_COLOR', 'POINT').data.foreach_set("color", cols)


painter_masks()
for p in human.data.polygons:
    p.use_smooth = True
if PLANE_OF:
    plane_shading(PLANE_OF, PLANE_W, PLANES[1])
sd = human.modifiers.new("Smooth", 'SUBSURF')
sd.levels, sd.render_levels = 1, 1
sd.use_custom_normals = True                       # the planes' shading kept through the smoothing
SCAN_UV = human.data.uv_layers[0].name             # MPFB's own layout, which the skin scan is painted in


def head_uv():
    """A layout for the paint that gives the head most of the texture (your note, 2026-10-16: the
    skin looked blurry, not in focus). MPFB's own gives the whole face about 450 pixels of 4096,
    one to each pixel of a close-up, so the finest brushwork lands as a smear; here the head's
    island (the face, the scalp, the ears, the neck) fills the texture from a sixth of the way
    across, three to four times as fine, and the rest of the body shrinks into the corner."""
    me = human.data
    n = len(me.loops)
    src = np.empty(n * 2)
    me.uv_layers[SCAN_UV].data.foreach_get("uv", src)
    src = src.reshape(-1, 2)
    lv = np.empty(n, np.int64)
    me.loops.foreach_get("vertex_index", lv)
    parent = list(range(len(me.polygons)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    seen = {}
    for pl in me.polygons:                          # faces joined where they share an edge and its place in the layout
        li = list(pl.loop_indices)
        for j in range(len(li)):
            a, b = li[j], li[(j + 1) % len(li)]
            key = tuple(sorted(((int(lv[a]), tuple(np.round(src[a], 5))), (int(lv[b]), tuple(np.round(src[b], 5))))))
            if key in seen:
                parent[find(pl.index)] = find(seen[key])
            else:
                seen[key] = pl.index
    nose = min(range(len(pts)), key=lambda i: (pts[i] - (E + Vector((0.0, -0.06, -0.045)))).length)
    island = find(next(pl.index for pl in me.polygons if nose in pl.vertices))
    head = np.zeros(n, bool)
    for pl in me.polygons:
        if find(pl.index) == island:
            head[list(pl.loop_indices)] = True
    lo, hi = src[head].min(0), src[head].max(0)
    s = min(0.815 / (hi[0] - lo[0]), 0.99 / (hi[1] - lo[1]))
    out = src * 0.17                                # the body, small, in the corner
    out[head] = (src[head] - lo) * s + np.array((0.18, 0.005))
    layer = me.uv_layers.new(name="Paint")
    layer.data.foreach_set("uv", out.ravel())
    me.uv_layers.active = layer
    layer.active_render = True
    print("head layout: %.1f times as fine" % (s / 1.0))


head_uv()


# ---------------------------------------------------------------- the hair, in locks
def hair(n_locks=130, seed=3):
    """Locks of hair grown over the scalp: parted on his left, those right of the part swept
    across the forehead and down past the temple, the rest falling to the jaw at the sides and the
    nape at the back, each lying on the ones beneath; every lock a tapered band, thick at the
    root, to a point. Its UVs give each lock a cell of its own, along its length running up the
    texture, so it can be painted along the strands. Rigged to the head."""
    rng = random.Random(seed)
    # The locks are combed over a smoothed copy of the head, the ears and every small form smoothed
    # away, so they fall past the ears cleanly instead of bunching over them.
    me = human.data
    n = len(me.vertices)
    co = np.array([tuple(MW @ v.co) for v in me.vertices])
    body = np.zeros(n, bool)
    body[list(sets["body"])] = True
    ed = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ed)
    ed = ed.reshape(-1, 2)
    ed = ed[body[ed[:, 0]] & body[ed[:, 1]]]
    deg = np.bincount(ed.ravel(), minlength=n).astype(float)
    has = deg > 0
    for _ in range(40):
        acc = np.zeros_like(co)
        np.add.at(acc, ed[:, 0], co[ed[:, 1]])
        np.add.at(acc, ed[:, 1], co[ed[:, 0]])
        co[has] += 0.5 * (acc[has] / deg[has, None] - co[has])
    polys = [tuple(pl.vertices) for pl in me.polygons if all(body[v] for v in pl.vertices)]
    bvh = BVHTree.FromPolygons([Vector(c) for c in co], polys)

    def nearest(p):
        q, n_, _, d = bvh.find_nearest(p)
        return q, n_.normalized(), d

    scalp = [i for i in sets["scalp"] if i in sets["body"]]
    roots = []
    for i in rng.sample(scalp, len(scalp)):
        p = pts[i]
        if all((p - q).length > 0.011 for q in roots):
            roots.append(p)
        if len(roots) >= n_locks:
            break
    part_x = E.x + 0.045                                # his left (+X), above the outer end of the brow, as in the photos
    wisps = []
    specs = [(r, False) for r in sorted(roots, key=lambda p: -p.z)] + [(r, True) for r in wisps]   # crown first, wisps last
    verts, faces, uvs, along, shade, vn = [], [], [], [], [], []
    cols = 16
    rows = math.ceil(len(specs) / cols)
    seg = 7
    for k, (r, wisp) in enumerate(specs):
        _, n0, _ = nearest(r)
        side = 1.0 if r.x > part_x else -1.0
        top = ramp01(E.z + 0.04, E.z + 0.11, r.z)        # 1 on the crown, 0 low on the side of the head
        # The comb, as a smooth field over the head, so neighbouring locks lie the same way: the back
        # falls to the nape, the sides to the jaw, and right of the part the front sweeps across the
        # forehead (the fringe), blended from one to the next.
        back = ramp01(E.y + 0.06, E.y + 0.13, r.y)
        fringe = (1.0 if side < 0 else 0.0) * ramp01(E.y + 0.07, E.y + 0.03, r.y) * ramp01(0.2, 0.5, top)
        d_side = Vector((side * (0.25 + 0.7 * top), 0.1, -(1.0 - 0.75 * top)))
        d = d_side.lerp(Vector((0.2 * side, 0.6, -0.8)), back).lerp(Vector((-0.85, -0.3, -0.42)), fringe)
        swept = (1.0 if side > 0 else 0.0) * ramp01(E.y + 0.07, E.y + 0.03, r.y)   # right of the part, the front swept back, as in the photos
        d = d.lerp(Vector((0.5, 0.75, -0.45)), 0.8 * swept)
        end_z = (E.z - 0.085 + rng.uniform(-0.012, 0.012)) * (1 - back) + (E.z - 0.13) * back
        end_z = end_z * (1 - fringe) + (E.z - 0.06) * fringe
        fall = 1.0 - 0.25 * fringe
        lift = (0.008 + 0.014 * top + 0.003 * (k / len(specs))) * (1 - 0.3 * fringe)   # the crown's over the side's; the fringe close   # the crown's locks lie over the side's; the fringe stands off
        wave = 40.0 * r.x + 30.0 * r.y                 # neighbours wave together, as combed hair does
        p = r - n0 * 0.003                              # rooted in the scalp
        path, norms = [p.copy()], [n0]
        for i in range(60):
            q, nq, _ = nearest(p)
            d = (d - nq * d.dot(nq) * 0.8).normalized()                      # along the head, not into it
            d = (d + Vector((0, 0, -1)) * fall * (0.015 + 0.012 * i)).normalized()  # falling more as it goes
            d = (d + d.cross(nq).normalized() * 0.07 * math.sin(0.28 * i + wave)).normalized()   # a slight wave
            if p.z < end_z + 0.025:                                          # the ends flick out, as in the photos
                d = (d + nq * 0.35 * ramp01(end_z + 0.025, end_z, p.z)).normalized()
            p = p + d * 0.008
            q, nq, _ = nearest(p)
            li = 0.006 + (lift - 0.006) * ramp01(0, 5, i)              # rising from the part, not standing up from it
            if (p - q).dot(nq) < li:
                p = q + nq * li
            lim = E.z + 0.035 - 0.12 * ramp01(0.065, 0.095, abs(p.x - E.x))
            if fringe > 0.2:                           # the fringe's edge a diagonal, as in the photos: high at the part, the brow at his right temple
                lim = max(lim, E.z + 0.03 + 0.55 * (p.x - (E.x - 0.07)))
            if p.y < E.y + 0.01 and p.z < lim:
                p.z = lim                              # off the eyes: the fringe stops at the brow, easing down past the temple
                if fringe > 0.2 and i > 12:
                    path.append(p.copy())
                    norms.append(nq)
                    break                              # a fringe lock ends where it meets its edge, rather than sliding along it
                if fringe > 0.2:                       # a short one flows on along the edge, toward his right temple
                    d = (0.3 * d + Vector((-0.88, 0.0, -0.48))).normalized()
            path.append(p.copy())
            norms.append(nq)
            if p.z < end_z and i > 6:
                break
        width = rng.uniform(0.005, 0.01) if wisp else rng.uniform(0.045, 0.065)   # big locks that merge into one mass, as Vi's; wisps fine
        width *= 0.45 + 0.55 * ramp01(0.04, 0.1, 0.008 * (len(path) - 1))           # short ones narrower, not lumps
        taper = 1.8 if fringe > 0.2 else 3.0                                         # the fringe's ends to points
        cx, cy = k % cols, k // cols
        n = len(path)
        base = len(verts)
        tone = rng.uniform(0.92, 1.08)
        s_prev = None
        for j, (c, nq) in enumerate(zip(path, norms)):
            u = j / (n - 1)
            t = (path[min(j + 1, n - 1)] - path[max(j - 1, 0)]).normalized()
            s = t.cross(nq).normalized()
            if s_prev is not None and s.dot(s_prev) < 0:                # no twist where the lock bends
                s = -s
            s_prev = s
            w = width * (1 - u ** taper) * (0.75 + 0.25 * min(1.0, u * 6)) + 0.0004
            for a in range(seg + 1):
                ang = 2 * math.pi * a / seg - math.pi / 2      # the seam underneath, out of sight
                verts.append(tuple(c + s * (0.5 * w * math.cos(ang)) + nq * (0.3 * w * math.sin(ang))))
                vn.append(tuple((nq * 0.75 + (s * math.cos(ang) + nq * math.sin(ang)) * 0.25).normalized()))
                uvs.append(((cx + 0.05 + 0.9 * a / seg) / cols, (cy + 0.03 + 0.94 * u) / rows))
                along.append(u)
                shade.append(tone)
        for j in range(n - 1):
            for a in range(seg):
                i0 = base + j * (seg + 1) + a
                faces.append((i0, i0 + seg + 1, i0 + seg + 2, i0 + 1))      # wound to face outward
        c0 = len(verts)                                                  # the root closed, so no open end shows at the part
        verts.append(tuple(path[0]))
        vn.append(tuple(norms[0]))
        uvs.append(((cx + 0.5) / cols, (cy + 0.03) / rows))
        along.append(0.0)
        shade.append(tone)
        for a in range(seg):
            faces.append((c0, base + a, base + a + 1))
    me = bpy.data.meshes.new("Hair locks")
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    loops = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", loops)
    uv.data.foreach_set("uv", np.array(uvs)[loops].ravel())
    me.attributes.new("along", 'FLOAT', 'POINT').data.foreach_set("value", along)
    me.attributes.new("shade", 'FLOAT', 'POINT').data.foreach_set("value", shade)
    me.attributes.new("hair_masks", 'FLOAT_COLOR', 'POINT').data.foreach_set(
        "color", [v for a in along for v in (a, 0.0, 0.0, 1.0)])          # red: how far along the lock, for the painter
    print("hair: %d locks, %d wisps" % (len(roots), len(wisps)))
    me.shade_smooth()
    me.normals_split_custom_set_from_vertices(vn)     # shaded as one mass, as painted hair is, not as so many tubes
    ob = bpy.data.objects.new("Hair locks", me)
    scene.collection.objects.link(ob)
    mw = ob.matrix_world.copy()
    ob.parent, ob.parent_type, ob.parent_bone = rig, 'BONE', "Head"
    bpy.context.view_layer.update()
    ob.matrix_world = mw
    print("hair: %d locks" % len(roots))
    inner = set(scalp)
    for _ in range(2):
        inner |= {b for a, b in ed.tolist() if a in inner} | {a for a, b in ed.tolist() if b in inner}
    keep = [pl for pl in polys if all(v in inner for v in pl)]
    used = sorted({v for pl in keep for v in pl})
    ix = {v: i for i, v in enumerate(used)}
    ring = {v: 0 for v in scalp}                     # how far out from the scalp each point is: 0 inside, 1 and 2 the rings beyond
    for r_ in (1, 2):
        for a, b in ed.tolist():
            if (a in ring) != (b in ring):
                ring[b if a in ring else a] = r_
    cm = bpy.data.meshes.new("Hair mass")
    cm.from_pydata([tuple(co[v]) for v in used], [], [tuple(ix[v] for v in pl) for pl in keep])
    cm.update()
    vn = np.empty(len(used) * 3)
    cm.vertices.foreach_get("normal", vn)
    thick = np.array([(0.006 + 0.008 * ramp01(E.z + 0.04, E.z + 0.11, co[v][2])) * (1.0, 0.45, 0.08)[ring.get(v, 2)]
                      for v in used])                # thick at the crown, under the locks' lift; to nothing at the hairline
    cm.vertices.foreach_set("co", (co[used] + thick[:, None] * vn.reshape(-1, 3)).ravel())
    cm.update()
    cm.shade_smooth()
    cap = bpy.data.objects.new("Hair mass", cm)
    scene.collection.objects.link(cap)
    cap.parent, cap.parent_type, cap.parent_bone = rig, 'BONE', "Head"
    bpy.context.view_layer.update()
    cap.matrix_world = Matrix.Identity(4)
    return ob, cap


bpy.context.view_layer.update()
locks, beneath = hair()
print("head built in %.0fs" % (time.time() - t_start))


def wear(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


def picture(ob):
    """The image texture a fitted asset's own material uses (for its cut-out)."""
    for m in ob.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and "normal" not in n.image.name.lower():
                    return n.image
    return None


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

# ---------------------------------------------------------------- camera, light, backdrop
scene.frame_set(F0)
bpy.context.view_layer.update()
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
    cd.dof.aperture_fstop = 8.0                    # the whole face in focus, as Vi's is (your note: it looked out of focus)


def aim(view):
    """Straight on, close, the head from the crown to the neck, as your frame of Vi; or the left
    three-quarter, as in the third photo, a little below the eyes."""
    if view == "front":
        cam.location, at, focus = E + Vector((0.0, -1.35, -0.01)), E + Vector((0.0, 0.0, -0.025)), 0.012
    else:
        cam.location, at, focus = E + Vector((0.5, -0.95, 0.0)), E + Vector((0.035, 0.0, -0.045)), 0.03
    cam.rotation_euler = (at - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cd.dof.focus_distance = (E - cam.location).length - focus


aim("three-quarter")


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


# Azimuth from +X (the head's left), counter-clockwise; the face looks toward -Y (270). As on Vi
# (your note: sunlight on the face, and shadows): the sun high on his right and in front, so his
# left side turns into shadow and the brow, the nose, the lips and the hair cast theirs onto the
# face; a cool fill from the sky on his left; a rim from behind on his left, along the shadow side.
def window(elevation, azimuth, dist=1.3, opening=(0.8, 1.2), bar=0.04, mullion=-0.16, transom=-0.15,
           slats=()):
    """A wall with a window in it, between the sun and the head (your note): the light comes in
    only through the window, so one side of his face is lit and the other is in its own shadow, and
    the window's bars throw theirs, the cross-bar's across his neck. Out of the camera's sight."""
    d = Vector((math.cos(math.radians(elevation)) * math.cos(math.radians(azimuth)),
                math.cos(math.radians(elevation)) * math.sin(math.radians(azimuth)),
                math.sin(math.radians(elevation))))
    c = E + d * dist
    u = Vector((0, 0, 1)).cross(d).normalized()     # across the window, level
    v = d.cross(u).normalized()                     # up the window
    ow, oh = opening[0] / 2, opening[1] / 2
    boxes = [(-(1.5 + ow) / 2, 0.0, (1.5 - ow) / 2, 1.5), ((1.5 + ow) / 2, 0.0, (1.5 - ow) / 2, 1.5),
             (0.0, (1.5 + oh) / 2, ow, (1.5 - oh) / 2), (0.0, -(1.5 + oh) / 2, ow, (1.5 - oh) / 2),
             (mullion, 0.0, bar / 2, oh), (0.0, transom, ow, bar / 2)] \
        + [(0.0, s_, ow, 0.018) for s_ in slats]     # a blind, clear across the band that lights his face: the slats' shadows cut the air into rays
    verts, faces = [], []
    for a, b, hu, hv in boxes:
        k = len(verts)
        for su in (-1, 1):
            for sv in (-1, 1):
                for sd in (-1, 1):
                    verts.append(tuple(c + u * (a + su * hu) + v * (b + sv * hv) + d * (0.02 * sd)))
        faces += [(k + i0, k + i1, k + i3, k + i2) for i0, i1, i2, i3 in
                  ((0, 1, 2, 3), (4, 6, 5, 7), (0, 4, 1, 5), (2, 3, 6, 7), (0, 2, 4, 6), (1, 5, 3, 7))]
    me = bpy.data.meshes.new("Window")
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new("Window", me)
    scene.collection.objects.link(ob)
    ob.visible_camera = False
    return ob


if LIVE:
    KEY = (40, 210)                                # elevation, azimuth: the sun high on his right, as in your frame of Vi: the brow shades the eyes, the nose casts across
    key = sun("Sun", 4.0, (1.0, 0.9, 0.76), *KEY, angle=1.2)    # soft-edged, as a sun through a window is
    for k, v in (("use_shadow_jitter", False), ("shadow_filter_radius", 1.0), ("shadow_maximum_resolution", 0.0005)):
        try:                                       # soft edges traced and filtered, which came out cleanest
            setattr(key.data, k, v)
        except (AttributeError, TypeError):
            pass
    for k, v in (("shadow_ray_count", 4), ("shadow_step_count", 32)):
        try:
            setattr(scene.eevee, k, v)
        except (AttributeError, TypeError):
            pass
    sun("Sky fill", 0.2, (0.7, 0.76, 0.84), 20, 320, angle=25.0)     # the shadow side modeled by the sky, as Vi's is
    sun("Bounce", 0.16, (1.0, 0.86, 0.76), -15, 300, angle=30.0)    # and warm light up from the floor
    sun("Rim", 0.6, (0.96, 0.9, 0.82), 20, 85, angle=6.0)    # from behind, only along the edge of the shadow side
    window(*KEY)

    def air(density=0.12, size=3.0):
        """Air in the room (your note, 2026-10-16: atmospheric shading, light rays): a faint haze, so
        the sun through the window shows in it as shafts, cut into rays by the slats, with his head's
        own shadow running back through it."""
        h = size / 2                                # only behind his face, so it doesn't veil it
        verts = [tuple(E + Vector((sx * h, 0.02 + (sy + 1) * h, sz * h))) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        me = bpy.data.meshes.new("Air")
        me.from_pydata(verts, [], faces)
        ob = bpy.data.objects.new("Air", me)
        scene.collection.objects.link(ob)
        m, g, out = P.material("Air")
        vol = g.new("ShaderNodeVolumePrincipled", {"Density": density, "Anisotropy": 0.15, "Color": (*P.srgb((0.9, 0.88, 0.85)), 1.0)})
        g.nt.links.new(vol.outputs[0], out.inputs["Volume"])
        me.materials.append(m)
        e = scene.eevee
        for k, v in (("volumetric_tile_size", '2'), ("volumetric_samples", 128), ("volumetric_start", 0.1),
                     ("volumetric_end", 8.0), ("use_volumetric_shadows", True), ("volumetric_shadow_samples", 32)):
            try:
                setattr(e, k, v)
            except (AttributeError, TypeError):
                pass
        return ob

    air()
    # The rays (your note: light rays): a second sun that lights only the air, not him, through slats
    # set edge-on to the camera, so their shadows read as rays across the air behind him; the key's
    # own glow in the air kept low, so it doesn't veil the background.
    key.data.volume_factor = 0.1
    RAYS = (40, 182)
    rays = sun("Rays", 3.5, (1.0, 0.88, 0.72), *RAYS, angle=0.5)
    rays.data.diffuse_factor = rays.data.specular_factor = 0.0
    rays.data.volume_factor = 1.0
    d = Vector((math.cos(math.radians(RAYS[0])) * math.cos(math.radians(RAYS[1])),
                math.cos(math.radians(RAYS[0])) * math.sin(math.radians(RAYS[1])), math.sin(math.radians(RAYS[0]))))
    u = Vector((0, 0, 1)).cross(d).normalized()
    v = d.cross(u).normalized()
    c = E + d * 1.6
    verts, faces = [], []
    for i in range(-8, 9):                           # slats 4 cm deep, 7 cm apart; only behind the line to his face, so the key isn't crossed
        k = len(verts)
        for a in (-1.6, -0.05):                     # u runs toward the camera: these lie behind his face, over the air
            for b in (0.07 * i - 0.02, 0.07 * i + 0.02):
                verts.append(tuple(c + u * a + v * b))
        faces.append((k, k + 1, k + 3, k + 2))
    me = bpy.data.meshes.new("Slats")
    me.from_pydata(verts, [], faces)
    sl = bpy.data.objects.new("Slats", me)
    scene.collection.objects.link(sl)
    sl.visible_camera = False
else:
    sun("Sun", 3.6, (1.0, 0.9, 0.76), 42, 232, angle=6.0)
    sun("Sky fill", 0.26, (0.62, 0.74, 0.86), 12, 320, angle=25.0)
    sun("Rim", 2.2, (0.96, 0.9, 0.82), 28, 70, angle=6.0)
    sun("Bounce", 0.3, (1.0, 0.9, 0.8), -12, 275, angle=30.0)   # warm light up from below, lifting the shadow under the eyes
P.sky(scene, zenith=(0.06, 0.1, 0.12), horizon=(0.15, 0.2, 0.21), below=(0.08, 0.11, 0.12),   # dark teal, as behind Vi
      clouds=(0.2, 0.26, 0.27), fill=(0.6, 0.7, 0.78), fill_strength=0.3, soft=0.35)


# ---------------------------------------------------------------- bake and paint
def node_mat(name, build):
    m, g, out = P.material(name)
    shader = build(g)
    g.nt.links.new(shader, out.inputs["Surface"])
    return m, g


def skin_colour(g, uv):
    skin_img = bpy.data.images.get("skin scan") or bpy.data.images.load(
        str(H.mpfb_data("skins") / "young_caucasian_male" / "young_lightskinned_male_diffuse.png"))
    skin_img.name = "skin scan"
    tex = g.new("ShaderNodeTexImage", {"Vector": g.new("ShaderNodeUVMap", uv_map=SCAN_UV).outputs["UV"]}, image=skin_img).outputs["Color"]
    col = g.mix(0.45, (*P.srgb((0.86, 0.8, 0.78)), 1.0), tex)     # pale and muted, as Vi, with the scan's own variation (its pores blurred out by the painter)
    amt = g.math('MULTIPLY', g.new("ShaderNodeAttribute", attribute_name="stubble").outputs["Fac"], STUBBLE)
    col = g.mix(amt, col, g.scale(col, (0.72, 0.7, 0.75)))        # stubble, a soft cool tone (none: clean-shaven, your call)
    warm = g.new("ShaderNodeAttribute", attribute_name="warmth").outputs["Fac"]
    col = g.mix(g.math('MULTIPLY', warm, 0.55), col, g.scale(col, (1.0, 0.82, 0.8)))   # warmer, rosier, as Vi's cheeks and nose
    lip = g.new("ShaderNodeAttribute", attribute_name="lip_tint").outputs["Fac"]
    col = g.mix(g.math('MULTIPLY', lip, 0.6), col, g.scale(col, (0.76, 0.52, 0.5)))   # lips their own, a muted rose, as Vi's (their shape painted)
    up = g.new("ShaderNodeAttribute", attribute_name="upper_lip").outputs["Fac"]
    return g.mix(g.math('MULTIPLY', up, 0.7), col, g.scale(col, (0.8, 0.74, 0.75)))   # the upper lip in its own shade


def hair_mass_colour(g, uv=None):
    """The solid mass under the locks: the hair's one colour, with dark streaks running down it, as the locks have."""
    pos = g.new("ShaderNodeTexCoord").outputs["Object"]
    streak = g.noise(g.new("ShaderNodeVectorMath", [pos, (60.0, 60.0, 4.0)], operation='MULTIPLY').outputs[0], 1.0, detail=1.0)
    dark = g.remap(streak, 0.38, 0.5, 1.0, 0.0)
    return g.mix(g.math('MULTIPLY', dark, 0.65), (*P.srgb((0.27, 0.17, 0.1)), 1.0), (*P.srgb((0.1, 0.07, 0.05)), 1.0))


def hair_colour(g, uv):
    a = g.new("ShaderNodeAttribute", attribute_name="along").outputs["Fac"]
    sh = g.new("ShaderNodeAttribute", attribute_name="shade").outputs["Fac"]
    col = g.mix(g.remap(a, 0.2, 1.0, 0.0, 1.0), (*P.srgb((0.24, 0.15, 0.09)), 1.0), (*P.srgb((0.29, 0.18, 0.105)), 1.0))   # almost one colour, as Vi's
    return g.scale(col, sh)                         # darker at the root, lighter to the ends, as in the photos


def on_face(dx, dz):
    """The front-most point of the skin at (dx, dz) from between the eyes."""
    near = [p for p in pts if abs(p.x - E.x - dx) < 0.006 and abs(p.z - E.z - dz) < 0.006]
    return min(near, key=lambda p: p.y)


def marks(g):
    """Very light marks, as a face has (your note, 2026-10-15): freckles across the nose and the
    cheeks, two small moles (his left cheek, the right of his neck), a faint birthmark low on the
    left of his neck, a thin pale scar on his chin. Red, how much darker; green, how much paler."""
    pos = g.new("ShaderNodeNewGeometry").outputs["Position"]
    flat = g.new("ShaderNodeVectorMath", [pos, (1.0, 0.0, 1.0)], operation='MULTIPLY').outputs[0]   # seen from the front

    def vec(op, a, b):
        return g.new("ShaderNodeVectorMath", [a, b], operation=op)

    def near(c, r):                                 # only on the skin in front, not through the head
        return g.remap(vec('DISTANCE', pos, tuple(c)).outputs["Value"], r, 1.6 * r, 1.0, 0.0)

    def spot(c, r, amount, rough=0.0):
        d = vec('DISTANCE', flat, (c.x, 0.0, c.z)).outputs["Value"]
        if rough:
            d = g.math('MULTIPLY_ADD', g.noise(pos, 500.0, 3.0), rough, d)
        return g.math('MULTIPLY', g.math('MULTIPLY', g.remap(d, 0.5 * r, r, 1.0, 0.0), near(c, 0.01)), amount)

    region = g.new("ShaderNodeAttribute", attribute_name="freckles").outputs["Fac"]
    vor = g.new("ShaderNodeTexVoronoi", {"Vector": pos, "Scale": 260.0, "Randomness": 1.0})
    rnd = g.new("ShaderNodeSeparateColor", [vor.outputs["Color"]]).outputs
    dot = g.remap(vor.outputs["Distance"], 0.08, 0.2, 1.0, 0.0)
    keep = g.math('LESS_THAN', rnd[0], g.math('MULTIPLY', region, 0.55))
    dark = g.math('MULTIPLY', g.math('MULTIPLY', dot, keep), g.math('MULTIPLY_ADD', rnd[1], 0.2, 0.15))
    for c, r, amount, rough in ((on_face(0.043, -0.06), 0.0011, 0.55, 0.0),       # a mole on his left cheek
                                (on_face(-0.032, -0.152), 0.0013, 0.5, 0.0),      # and one on the right of his neck
                                (on_face(0.026, -0.172), 0.006, 0.1, 0.004)):     # a faint birthmark
        dark = g.math('MAXIMUM', dark, spot(c, r, amount, rough))
    a, b = on_face(0.004, -0.123), on_face(0.013, -0.111)                         # the scar, on his chin
    A, AB = Vector((a.x, 0.0, a.z)), Vector((b.x - a.x, 0.0, b.z - a.z))
    pa = vec('SUBTRACT', flat, tuple(A)).outputs[0]
    t = g.math('DIVIDE', vec('DOT_PRODUCT', pa, tuple(AB)).outputs["Value"], AB.length_squared)
    t = g.math('MINIMUM', g.math('MAXIMUM', t, 0.0), 1.0)
    along = g.new("ShaderNodeVectorMath", operation='SCALE')
    g.set(along.inputs[0], tuple(AB))
    g.set(along.inputs[3], t)
    d = vec('DISTANCE', pa, along.outputs[0]).outputs["Value"]
    taper = g.math('MULTIPLY', g.remap(t, 0.0, 0.2, 0.3, 1.0), g.remap(t, 0.8, 1.0, 1.0, 0.3))
    scar = g.math('MULTIPLY', g.math('MULTIPLY', g.remap(d, 0.0003, 0.0007, 1.0, 0.0), near((a + b) / 2, 0.012)),
                  g.math('MULTIPLY', taper, 0.5))
    hollow = g.new("ShaderNodeAttribute", attribute_name="hollow").outputs["Fac"]      # blue: the hollows, for line accents
    return g.new("ShaderNodeCombineColor", [dark, scar, hollow]).outputs[0]


def attr_colour(name):
    return lambda g: g.new("ShaderNodeAttribute", attribute_name=name).outputs["Color"]


def bake(ob, colour, size, name, ao_distance=0.015, extra=(), form_distance=None):
    """Bake ob's colour (EMIT) and the light that reaches it (DIFFUSE, light only) into its UVs;
    save both as half floats for the painter. extra: (kind, colour) pairs, more for the painter,
    each baked as the colour is."""
    builders = dict(extra)
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for dv in prefs.devices:
        dv.use = dv.type == 'OPTIX'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 48
    img = bpy.data.images.new(name + " bake", size, size, float_buffer=True, alpha=False)
    out = {}
    scene.world.light_settings.distance = ao_distance
    for kind in ("base",) + (() if LIVE else ("light",)) + ("ao",) + (("form",) if form_distance else ()) + tuple(builders):
        if kind == "base":
            m, g = node_mat(name + " base", lambda g: g.new("ShaderNodeEmission", {"Color": colour(g, g.new("ShaderNodeTexCoord").outputs["UV"]), "Strength": 1.0}).outputs[0])
        elif kind in builders:                      # the painter's masks and marks
            m, g = node_mat(name + " " + kind, lambda g: g.new("ShaderNodeEmission", {"Color": builders[kind](g), "Strength": 1.0}).outputs[0])
        else:
            m, g = node_mat(name + " " + kind, lambda g: g.new("ShaderNodeBsdfDiffuse", {"Color": (1, 1, 1, 1)}).outputs[0])
        tn = g.new("ShaderNodeTexImage", image=img)
        g.nt.nodes.active = tn
        keep = list(ob.data.materials)
        wear(ob, m)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        t = time.time()
        if kind == "base" or kind in builders:
            bpy.ops.object.bake(type='EMIT', margin=24, use_clear=True)
        elif kind in ("ao", "form"):                # occlusion close in: the creases; wide: the form's hollows, for its painted shading
            scene.world.light_settings.distance = ao_distance if kind == "ao" else form_distance
            bpy.ops.object.bake(type='AO', margin=24, use_clear=True)
        else:
            bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=24, use_clear=True)
        a = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(a)
        np.save(PAINT / ("%s-%s.npy" % (name, kind)), a.reshape(size, size, 4).astype(np.float16))
        out[kind] = PAINT / ("%s-%s.npy" % (name, kind))
        ob.data.materials.clear()
        for mm in keep:
            ob.data.materials.append(mm)
        print("baked %s %s in %.0fs" % (name, kind, time.time() - t))
    return out


def bake_brows(size):
    """The brows' shape, cast onto the skin's texture (Cycles, selected to active), so the painter
    can paint them full underneath their hairs (your note: fuller, thicker brows)."""
    brow = fitted["eyebrows"]
    img = bpy.data.images.new("brows bake", size, size, float_buffer=True, alpha=False)
    mb, gb = node_mat("Brow shape", lambda g: g.new("ShaderNodeEmission", {"Color": g.new(
        "ShaderNodeTexImage", {"Vector": g.new("ShaderNodeTexCoord").outputs["UV"]}, image=cutouts["eyebrows"]).outputs["Alpha"],
        "Strength": 1.0}).outputs[0])
    ms, gs = node_mat("Brow target", lambda g: g.new("ShaderNodeEmission", {"Color": (0, 0, 0, 1)}).outputs[0])
    gs.nt.nodes.active = gs.new("ShaderNodeTexImage", image=img)
    keep_b, keep_s = list(brow.data.materials), list(human.data.materials)
    wear(brow, mb)
    wear(human, ms)
    bpy.ops.object.select_all(action='DESELECT')
    brow.select_set(True)
    human.select_set(True)
    bpy.context.view_layer.objects.active = human
    t = time.time()
    bpy.ops.object.bake(type='EMIT', use_selected_to_active=True, cage_extrusion=0.004, max_ray_distance=0.01,
                        margin=8, use_clear=True)
    a = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(a)
    path = PAINT / "skin-brows.npy"
    np.save(path, a.reshape(size, size, 4).astype(np.float16))
    for ob, keep in ((brow, keep_b), (human, keep_s)):
        ob.data.materials.clear()
        for mm in keep:
            ob.data.materials.append(mm)
    print("baked brows in %.0fs" % (time.time() - t))
    return path


def region():
    """The UV polygons of the head, neck and shoulders, where the fine brushes go."""
    me = human.data
    uv = me.uv_layers.active.data
    polys = []
    for p in me.polygons:
        if all(v in sets["body"] and pts[v].z > E.z - 0.32 for v in p.vertices):
            polys.append([tuple(uv[li].uv) for li in p.loop_indices])
    path = PAINT / "skin-region.json"
    json.dump(polys, open(path, "w"))
    return path


def painted_mat(name, png, sheen=0.0, rim=0.0, quiet=None):
    """The paint as it is, with, live over it, a faint sheen where the light catches the surface and
    a rim of light along the edges (so the skin isn't empty: your note, 2026-10-15)."""
    img = bpy.data.images.load(str(png))
    m, g, out = P.material(name)
    uv = g.new("ShaderNodeTexCoord").outputs["UV"]
    c = g.new("ShaderNodeTexImage", {"Vector": uv}, image=img).outputs["Color"]
    if sheen:
        gl = g.new("ShaderNodeBsdfGlossy", {"Color": (1, 1, 1, 1), "Roughness": 0.42})
        hi = g.remap(g.bw(g.new("ShaderNodeShaderToRGB", [gl.outputs[0]]).outputs[0]), 0.25, 1.2, 0.0, sheen)
        if quiet:                                   # none where the attribute says (the closed lids)
            hi = g.math('MULTIPLY', hi, g.math('SUBTRACT', 1.0, g.new("ShaderNodeAttribute", attribute_name=quiet).outputs["Fac"]))
        c = g.mix(hi, c, (*P.srgb((1.0, 0.95, 0.9)), 1.0), 'SCREEN')
    if rim:
        face = g.new("ShaderNodeLayerWeight", {"Blend": 0.3}).outputs["Facing"]
        c = g.mix(g.remap(face, 0.62, 0.95, 0.0, rim), c, (*P.srgb((0.95, 0.88, 0.8)), 1.0), 'SCREEN')
    em = g.new("ShaderNodeEmission", {"Color": c, "Strength": 1.0})
    g.nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def live_mat(name, png, shadow, light, soft, steps=None, warm=None, sheen=0.0, quiet=None, cool=None, edge=None,
             roughness=0.42, albedo=None):
    """The paint lit live (your note, 2026-10-15: the real shadows): the renderer's own light on the
    surface, its cast shadows included, read as a value and turned into the painter's colours, as
    in your frame of Vi: the paint as it is in full light; deep and warm in shadow, cooler where the
    sky's fill reaches into it (cool); a short turn between (soft), warm and reddish (warm), its edge
    broken along brush strokes (edge: the stroke map and how far it moves the edge); and a second,
    gentler turn (steps), so the planes of a form facing the light less take a half-tone."""
    m, g, out = P.material(name)
    uv = g.new("ShaderNodeTexCoord").outputs["UV"]
    if albedo:                                      # a colour built in nodes instead of a painted image
        alb = albedo(g, uv)
    else:
        alb = g.new("ShaderNodeTexImage", {"Vector": uv}, image=bpy.data.images.load(str(png))).outputs["Color"]
    lum = g.bw(g.new("ShaderNodeShaderToRGB", [g.new("ShaderNodeBsdfDiffuse", {"Color": (1, 1, 1, 1)}).outputs[0]]).outputs[0])
    raw = lum
    if edge:
        st = bpy.data.images.load(str(edge[0]), check_existing=True)
        st.colorspace_settings.name = 'Non-Color'
        n = g.bw(g.new("ShaderNodeTexImage", {"Vector": g.scale(uv, 0.5)}, image=st).outputs["Color"])   # strokes the size of a brush on screen
        lum = g.math('MULTIPLY', lum, g.math('MULTIPLY_ADD', g.math('SUBTRACT', n, 0.5), edge[1], 1.0))   # at the edge, not inside the shadow
    t = g.remap(lum, soft[0], soft[1], 0.0, 1.0)
    if steps:                                       # full light only on the planes facing it; a half-tone on the rest
        t = g.math('MULTIPLY', t, g.math('MULTIPLY_ADD', g.remap(lum, steps[0], steps[1], 0.0, 1.0), 1 - steps[2], steps[2]))
    sh = (*P.srgb(shadow), 1.0)
    if cool:
        sh = g.mix(g.remap(raw, cool[1], cool[2], 0.0, 1.0), sh, (*P.srgb(cool[0]), 1.0))
    c = g.scale(alb, g.mix(t, sh, (*P.srgb(light), 1.0)))
    if warm:                                        # the painter's warm note where light turns to shadow
        band = g.math('SUBTRACT', 1.0, g.math('ABSOLUTE', g.math('MULTIPLY_ADD', t, 2.0, -1.0)))
        c = g.mix(g.math('MULTIPLY', band, warm[1]), c, g.scale(c, P.srgb(warm[0])))
    if sheen:
        gl = g.new("ShaderNodeBsdfGlossy", {"Color": (1, 1, 1, 1), "Roughness": roughness})
        hi = g.math('MULTIPLY', g.remap(g.bw(g.new("ShaderNodeShaderToRGB", [gl.outputs[0]]).outputs[0]), 0.25, 1.2, 0.0, sheen), t)
        if quiet:
            hi = g.math('MULTIPLY', hi, g.math('SUBTRACT', 1.0, g.new("ShaderNodeAttribute", attribute_name=quiet).outputs["Fac"]))
        c = g.mix(hi, c, (*P.srgb((1.0, 0.95, 0.9)), 1.0), 'SCREEN')
    g.nt.links.new(g.new("ShaderNodeEmission", {"Color": c, "Strength": 1.0}).outputs[0], out.inputs["Surface"])
    return m


def eye_mat(iris=EYE_COLOUR):
    """The eyes painted, from where each point of the eyeball faces (no texture needed): an off-white;
    the iris a disc of colour, darker at its rim and lighter toward the pupil; the pupil black; a
    small highlight toward the sun."""
    m, g, out = P.material("Painted eye")
    geo = g.new("ShaderNodeNewGeometry")
    n = geo.outputs["Normal"]
    eye = fitted["eyes"]
    cos = [eye.matrix_world @ v.co for v in eye.data.vertices]
    centres = [sum((c for c in cos if (c.x > E.x) == side), Vector()) / sum(1 for c in cos if (c.x > E.x) == side) for side in (True, False)]
    facing = None
    for c in centres:                               # 1 at the front of each eye, from where the point lies round its centre
        v = g.new("ShaderNodeVectorMath", [geo.outputs["Position"], tuple(c)], operation='SUBTRACT').outputs[0]
        f = g.new("ShaderNodeVectorMath", [g.new("ShaderNodeVectorMath", [v], operation='NORMALIZE').outputs[0], (0.0, -1.0, 0.0)],
                  operation='DOT_PRODUCT').outputs["Value"]
        facing = f if facing is None else g.math('MAXIMUM', facing, f)
    hazel, ring = (*P.srgb(iris[0]), 1.0), (*P.srgb(iris[1]), 1.0)
    rim = g.remap(facing, 0.79, 0.83, 0.0, 1.0)                     # inside the limbus: a large iris, as Vi's (your note: it looked small)
    col = g.mix(rim, (*P.srgb((0.8, 0.77, 0.75)), 1.0), g.scale(hazel, 0.5))
    inner = g.remap(facing, 0.83, 0.94, 0.0, 1.0)                   # lighter toward the middle
    col = g.mix(g.math('MULTIPLY', inner, rim), col, g.scale(hazel, 1.15))
    col = g.mix(g.remap(facing, 0.93, 0.962, 0.0, 1.0), col, ring)  # the brown ring round the pupil
    col = g.mix(g.remap(facing, 0.962, 0.972, 0.0, 1.0), col, (0.02, 0.015, 0.015, 1.0))   # the pupil
    h = Vector((-0.4, -0.84, 0.39))                                  # halfway between the sun and the camera
    spec = g.new("ShaderNodeVectorMath", [n, tuple(h)], operation='DOT_PRODUCT').outputs["Value"]
    col = g.mix(g.remap(spec, 0.985, 0.995, 0.0, 1.0), col, (1.0, 1.0, 1.0, 1.0))
    g.nt.links.new(g.new("ShaderNodeEmission", {"Color": col, "Strength": 1.0}).outputs[0], out.inputs["Surface"])
    return m


def raw_mat(name, png):
    """The same paint shaded plainly by the renderer, for comparison."""
    m, g, out = P.material(name)
    alb = g.new("ShaderNodeTexImage", {"Vector": g.new("ShaderNodeTexCoord").outputs["UV"]},
                image=bpy.data.images.load(str(png), check_existing=True)).outputs["Color"]
    g.nt.links.new(g.new("ShaderNodeBsdfDiffuse", {"Color": alb}).outputs[0], out.inputs["Surface"])
    return m


if CHECK:
    clay = P.paint("Clay", (0.75, 0.72, 0.7), shadow=(0.45, 0.45, 0.5), vary=0.0, strokes=0.0, rim_amount=0.0,
                   crease=0.0, grain=0.0, half=None, hard=0.25)
    for ob in [human, locks, beneath] + list(fitted.values()):
        wear(ob, clay)
else:
    PAINT.mkdir(parents=True, exist_ok=True)
    skin_png, hair_png = (PAINT / "skin-colour.png", PAINT / "hair-colour.png") if LIVE else (PAINT / "skin-painted.png", PAINT / "hair-painted.png")
    cutouts = {kind: picture(fitted[kind]) for kind in ("eyebrows", "eyelashes")}   # before the bake's stand-ins replace them
    if not (REUSE and skin_png.exists() and hair_png.exists()):
        for ob in [human, locks, beneath] + list(fitted.values()):  # something to cast shadows while baking
            wear(ob, P.flat("Bake stand-in", (0.8, 0.8, 0.8)))
        for kind in ("eyebrows", "eyelashes", "eyes"):    # their shadows on the skin read as eyeshadow
            fitted[kind].hide_render = True
        sk = bake(human, skin_colour, SKIN_RES, "skin", 0.012, form_distance=0.07,
                  extra=(("masks", attr_colour("paint_masks")), ("masks2", attr_colour("paint_masks2")), ("marks", marks),
                         ("scan", lambda g: g.new("ShaderNodeTexImage", {"Vector": g.new("ShaderNodeUVMap", uv_map=SCAN_UV).outputs["UV"]},
                                                  image=bpy.data.images["skin scan"]).outputs["Color"])))
        for kind in ("eyebrows", "eyelashes", "eyes"):
            fitted[kind].hide_render = False
        sk["brows"] = bake_brows(SKIN_RES)
        hb = bake(locks, hair_colour, HAIR_RES, "hair", 0.01, extra=(("masks", attr_colour("hair_masks")),))
        reg = region()
        for (src, png, pal, radii, extra) in ((sk, skin_png, "skin", "24,12,6,3", ["--region", str(reg), "--bristles", "0.05", "--threshold", "8"]),
                                              (hb, hair_png, "hair", "10,5,3", ["--along", "v"])):
            t = time.time()
            subprocess.run(["py", str(BRUSH), str(src["base"]), str(src.get("light", src["base"])), str(png), "--palette", pal,
                            "--radii", radii, "--ao", str(src["ao"])] + extra + (["--unlit"] if LIVE else [])
                           + [x for k in ("masks", "masks2", "marks", "scan", "brows", "form") if k in src for x in ("--" + k, str(src[k]))],
                           check=True)
            print("painted %s in %.0fs" % (png.name, time.time() - t))
    if LIVE:
        strokes = PAINT / "strokes.png"
        if not strokes.exists():
            subprocess.run(["py", str(BRUSH), "strokes", str(strokes), "2048"], check=True)
        wear(human, live_mat("Painted skin", skin_png, (0.34, 0.22, 0.2), (0.98, 0.97, 0.96), (0.15, 0.3),
                             steps=(0.4, 0.9, 0.5), warm=((1.15, 0.8, 0.7), 0.35), sheen=0.0, roughness=0.3,
                             quiet="lid_region", cool=((0.52, 0.36, 0.32), 0.03, 0.1), edge=(strokes, 0.25)))   # deep warm shadow, lifted where the sky and the floor reach it; the edge a little broken, as Vi's
        wear(locks, live_mat("Painted hair", hair_png, (0.4, 0.34, 0.36), (1.0, 0.97, 0.92), (0.08, 0.3),
                             edge=(strokes, 0.3)))
        wear(beneath, live_mat("Hair mass", None, (0.4, 0.34, 0.36), (1.0, 0.97, 0.92), (0.08, 0.3), albedo=hair_mass_colour))
    else:
        wear(human, painted_mat("Painted skin", skin_png, sheen=0.07, rim=0.12, quiet="lid_region"))
        wear(locks, painted_mat("Painted hair", hair_png))
    if not LIVE:
        wear(beneath, P.flat("Hair beneath", (0.13, 0.085, 0.055)))
    for kind, col in (("eyebrows", (0.17, 0.12, 0.1)), ("eyelashes", (0.1, 0.07, 0.06))):
        m, g, out = P.material("Painted " + kind)
        tex = g.new("ShaderNodeTexImage", {"Vector": g.new("ShaderNodeTexCoord").outputs["UV"]}, image=cutouts[kind])
        em = g.new("ShaderNodeEmission", {"Color": (*P.srgb(col), 1.0), "Strength": 1.0})
        tr = g.new("ShaderNodeBsdfTransparent")
        a = g.remap(tex.outputs["Alpha"], 0.03 if kind == "eyelashes" else 0.06, 0.3 if kind == "eyelashes" else 0.4, 0.0, 1.0,
                    smooth=False)   # a bold lid line; the brows' hairs full over their soft painted shape
        g.nt.links.new(g.new("ShaderNodeMixShader", [a, tr.outputs[0], em.outputs[0]]).outputs[0], out.inputs["Surface"])
        wear(fitted[kind], m)
        fitted[kind].visible_shadow = False        # their cards' shadows smeared the cheeks
    wear(fitted["eyes"], eye_mat() if all(v < 1.0 for v in CLOSED.values()) else P.flat("Eye", (0.85, 0.82, 0.78)))

r = scene.render
r.resolution_x, r.resolution_y, r.resolution_percentage = (900, 1200, 100) if CHECK else (1920, 1080, 100)
P.eevee(scene, 64 if not LIVE else 128)            # live: enough samples for the soft shadows and the air
r.filter_size = 0.75                               # a tighter pixel filter: crisp, not soft (your note)
bpy.context.preferences.system.anisotropic_filter = 'FILTER_16'   # the paint sharp where the face turns away
if CHECK:
    r.use_compositing = False
else:                                              # the whole look: glow, grade, vignette, a touch of the lens, grain
    P.final_look(scene, F0, F1, **(dict(shadows=(0.95, 0.98, 1.0), glow=0.12, glow_threshold=1.0, dispersion=0.002, sharpen=0.15)
                                   if LIVE else {}))
r.use_stamp = False
scene.frame_start, scene.frame_end = F0, F1
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "face.blend"))
print("built in %.0fs" % (time.time() - t_start))

r.image_settings.media_type = 'IMAGE'
r.image_settings.file_format = 'PNG'
if CHECK:
    for name, off in (("front", Vector((0, -1.2, 0))), ("side", Vector((-1.2, 0, 0)))):
        cam.location = E + off
        cam.rotation_euler = (-off).to_track_quat('-Z', 'Y').to_euler()
        r.filepath = str(OUT / ("face-check-%s.png" % name))
        bpy.ops.render.render(write_still=True)
    sys.exit(0)
for name, f, view in (("front", F0, "front"), ("neutral", F0, "three-quarter"), ("breath", F1, "three-quarter")):
    aim(view)
    scene.frame_set(f)
    r.filepath = str(OUT / ("face-%s.png" % name))
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print("still", r.filepath, "%.1fs" % (time.time() - t))
    if LIVE and name == "front":                   # the same light, shaded plainly, for comparison
        keep = {ob: list(ob.data.materials) for ob in (human, locks)}
        wear(human, raw_mat("Plain skin", skin_png))
        wear(locks, raw_mat("Plain hair", hair_png))
        r.filepath = str(OUT / "face-front-raw.png")
        bpy.ops.render.render(write_still=True)
        for ob, ms in keep.items():
            ob.data.materials.clear()
            for mm in ms:
                ob.data.materials.append(mm)
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
