"""People for the Opening: rigged bodies from MPFB2, moved by motion capture from CMU.

Imported by band_mocap_test.py inside Blender 5.0. The mocap half (reading the CMU files,
finding a stride that loops, the retargeting maths) is plain numpy and runs outside Blender too:

    py humans.py            the run clips: speed, stride, cadence, and the stride each one loops

Bodies. MPFB2, the MakeHuman plugin for Blender (extensions.blender.org/add-ons/mpfb; its code
is GPL-3.0, and the characters it makes are CC0, yours outright), builds each person from its
sliders (sex, age, muscle, weight, height, proportions, African ancestry) on its "cmu_mb"
skeleton, which has the same 31 bones as the CMU data, so the motion goes on bone for bone.
It's installed once into Blender's user extensions:

    blender -c extension install-file -r user_default add-on-mpfb-v2.0.18.zip

Clothing is cut from MPFB's own fitting shells (its skirt and tights, which sit just off the
skin and are weighted to the skeleton), so it moves with the body without a cloth simulation:
a hide wrap at the hips for everyone, a band over the chest for the women, a top to the waist
for the girl. No nudity.

In real mode (person(..., real=True)) the bodies wear MakeHuman's scanned African skins, its
coiled hair, brows and lashes, all from its asset pack (CC0, files.makehumancommunity.org,
unpacked into MPFB's user data), and the hides are a scanned leather from Poly Haven (CC0)
with ragged edges.

Motion. The CMU Graphics Lab Motion Capture Database (mocap.cs.cmu.edu), its run and jog
trials. Its terms: free for all uses; it may go into commercially sold products, but the data
itself may not be resold, even converted; and it asks for this line in the acknowledgments:
"The data used in this project was obtained from mocap.cs.cmu.edu. The database was created
with funding from NSF EIA-0196217." Clips are fetched once into MOCAP, out of git.

How the motion goes on, with no steps by hand: read the ASF skeleton and the AMC frames; find
one stride (two steps) whose last pose matches its first, and spread the small mismatch over
it so it loops; swing the CMU skeleton's limbs (its zero pose has the arms straight out and the
legs splayed) onto the MPFB body's (an A-pose), and give each of the body's bones the turn its
CMU bone makes away from that pose; scale the hips' travel by the ratio of leg lengths. Along a
path, the stride runs at the mocap's own cadence where the path's speed fits it, and faster or
slower only as the speed to the power 0.3, so a runner who speeds up mostly lengthens the
stride, as people do; two-bone IK on each leg holds a planted foot still while it's down, so
the stretched or shortened stride doesn't slide.
"""
import math
import pathlib
import random
import urllib.request

import numpy as np

try:
    import bpy
    import bmesh
    from mathutils import Matrix, Vector
except ImportError:                           # the mocap half, outside Blender
    bpy = None

MOCAP = pathlib.Path(r"C:\Users\corbi\AdonaiOpening\mocap\cmu")
CMU_URL = "http://mocap.cs.cmu.edu/subjects/%s/%s"
CMU_FPS = 120
UNIT = 0.0254 / 0.45                          # CMU's length unit, in metres
MPFB = "bl_ext.user_default.mpfb"
MPFB_ZIP = pathlib.Path(r"C:\Users\corbi\AdonaiOpening\downloads\mpfb\add-on-mpfb-v2.0.18.zip")

# The run and jog trials that loop cleanly, by CMU subject and trial: six performers. (Left
# out: 16_55 and 127_03, whose strides don't match end to start; 113_07, a walk-jog; 141 and 143,
# too short, or recorded at another rate than the 120 a second they're listed at.)
CLIPS = ["127_07", "127_06", "16_46", "16_45", "104_37", "09_01", "35_22", "09_02", "09_05",
         "104_04", "35_17", "35_18", "16_35", "02_03", "127_08"]

# CMU bone -> MPFB's cmu_mb bone (the same skeleton, the names of the BVH conversion).
BONES = {"root": "Hips", "lhipjoint": "LHipJoint", "lfemur": "LeftUpLeg", "ltibia": "LeftLeg",
         "lfoot": "LeftFoot", "ltoes": "LeftToeBase", "rhipjoint": "RHipJoint", "rfemur": "RightUpLeg",
         "rtibia": "RightLeg", "rfoot": "RightFoot", "rtoes": "RightToeBase", "lowerback": "LowerBack",
         "upperback": "Spine", "thorax": "Spine1", "lowerneck": "Neck", "upperneck": "Neck1", "head": "Head",
         "lclavicle": "LeftShoulder", "lhumerus": "LeftArm", "lradius": "LeftForeArm", "lwrist": "LeftHand",
         "lhand": "LeftFingerBase", "lfingers": "LeftHandFinger1", "lthumb": "LThumb",
         "rclavicle": "RightShoulder", "rhumerus": "RightArm", "rradius": "RightForeArm",
         "rwrist": "RightHand", "rhand": "RightFingerBase", "rfingers": "RightHandFinger1", "rthumb": "RThumb"}

# CMU is Y up, the subject facing +Z with its left at +X; Blender is Z up, and an MPFB body
# faces -Y with its left at +X. This turns the one into the other (a quarter turn about X).
F = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])


# ---------------------------------------------------------------- rotations
def rot_x(a):
    c, s = np.cos(a), np.sin(a)
    o, z = np.ones_like(a), np.zeros_like(a)
    return np.stack([np.stack([o, z, z], -1), np.stack([z, c, -s], -1), np.stack([z, s, c], -1)], -2)


def rot_y(a):
    c, s = np.cos(a), np.sin(a)
    o, z = np.ones_like(a), np.zeros_like(a)
    return np.stack([np.stack([c, z, s], -1), np.stack([z, o, z], -1), np.stack([-s, z, c], -1)], -2)


def rot_z(a):
    c, s = np.cos(a), np.sin(a)
    o, z = np.ones_like(a), np.zeros_like(a)
    return np.stack([np.stack([c, -s, z], -1), np.stack([s, c, z], -1), np.stack([z, z, o], -1)], -2)


def euler_xyz(rx, ry, rz):
    """CMU's Euler order: X first, then Y, then Z, about fixed axes (Rz Ry Rx)."""
    return rot_z(rz) @ rot_y(ry) @ rot_x(rx)


def axis_angle(axis, angle):
    """Rotation matrices about unit axes (n,3) by angles (n,)."""
    axis = np.asarray(axis, float)
    k = np.zeros(axis.shape[:-1] + (3, 3))
    k[..., 0, 1], k[..., 0, 2], k[..., 1, 2] = -axis[..., 2], axis[..., 1], -axis[..., 0]
    k[..., 1, 0], k[..., 2, 0], k[..., 2, 1] = axis[..., 2], -axis[..., 1], axis[..., 0]
    a = np.asarray(angle, float)[..., None, None]
    return np.eye(3) + np.sin(a) * k + (1 - np.cos(a)) * (k @ k)


def log_rot(r):
    """Axis and angle of rotation matrices."""
    ang = np.arccos(np.clip((np.trace(r, axis1=-2, axis2=-1) - 1) / 2, -1, 1))
    v = np.stack([r[..., 2, 1] - r[..., 1, 2], r[..., 0, 2] - r[..., 2, 0], r[..., 1, 0] - r[..., 0, 1]], -1)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return np.where(n > 1e-9, v / np.maximum(n, 1e-9), np.array([1.0, 0, 0])), ang


def between(a, b):
    """The shortest rotation taking direction a onto direction b."""
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    c = np.cross(a, b)
    s, d = np.linalg.norm(c), float(np.dot(a, b))
    if s < 1e-9:
        if d > 0:
            return np.eye(3)
        p = np.cross(a, [1.0, 0, 0] if abs(a[0]) < 0.9 else [0, 1.0, 0])
        return axis_angle(p / np.linalg.norm(p), math.pi)
    return axis_angle(c / s, math.atan2(s, d))


def to_quat(m):
    """Rotation matrices (n,3,3) -> quaternions (n,4), w first, sign kept continuous along n."""
    m = np.asarray(m)
    q = np.empty(m.shape[:-2] + (4,))
    t = np.trace(m, axis1=-2, axis2=-1)
    for idx in np.ndindex(m.shape[:-2]):
        r, tr = m[idx], t[idx]
        if tr > 0:
            s = 2 * math.sqrt(tr + 1)
            q[idx] = (0.25 * s, (r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s)
        elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
            s = 2 * math.sqrt(1 + r[0, 0] - r[1, 1] - r[2, 2])
            q[idx] = ((r[2, 1] - r[1, 2]) / s, 0.25 * s, (r[0, 1] + r[1, 0]) / s, (r[0, 2] + r[2, 0]) / s)
        elif r[1, 1] > r[2, 2]:
            s = 2 * math.sqrt(1 + r[1, 1] - r[0, 0] - r[2, 2])
            q[idx] = ((r[0, 2] - r[2, 0]) / s, (r[0, 1] + r[1, 0]) / s, 0.25 * s, (r[1, 2] + r[2, 1]) / s)
        else:
            s = 2 * math.sqrt(1 + r[2, 2] - r[0, 0] - r[1, 1])
            q[idx] = ((r[1, 0] - r[0, 1]) / s, (r[0, 2] + r[2, 0]) / s, (r[1, 2] + r[2, 1]) / s, 0.25 * s)
    flat = q.reshape(-1, 4)
    for i in range(1, len(flat)):
        if np.dot(flat[i], flat[i - 1]) < 0:
            flat[i] = -flat[i]
    return q


# ---------------------------------------------------------------- reading CMU's files
def fetch(clip):
    """The ASF and AMC files of a trial, downloaded once into MOCAP."""
    subject = clip.split("_")[0]
    MOCAP.mkdir(parents=True, exist_ok=True)
    for name in (subject + ".asf", clip + ".amc"):
        path = MOCAP / name
        if not path.exists():
            urllib.request.urlretrieve(CMU_URL % (subject, name), str(path))
    return MOCAP / (subject + ".asf"), MOCAP / (clip + ".amc")


def read_asf(path):
    """Bones: name -> dict(direction, length (m), axis matrix C, dof list, parent)."""
    bones = {"root": {"direction": np.zeros(3), "length": 0.0, "C": np.eye(3),
                      "dof": ["tx", "ty", "tz", "rx", "ry", "rz"], "parent": None}}
    section, cur = None, None
    for raw in open(path, encoding="latin-1"):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        if line.startswith(":"):
            section = line.split()[0]
            continue
        w = line.split()
        if section == ":bonedata":
            if w[0] == "begin":
                cur = {"dof": [], "parent": None}
            elif w[0] == "end":
                bones[cur["name"]] = cur
            elif w[0] == "name":
                cur["name"] = w[1]
            elif w[0] == "direction":
                cur["direction"] = np.array([float(x) for x in w[1:4]])
            elif w[0] == "length":
                cur["length"] = float(w[1]) * UNIT
            elif w[0] == "axis":
                a = np.radians([float(x) for x in w[1:4]])
                cur["C"] = euler_xyz(*a)
            elif w[0] == "dof":
                cur["dof"] = w[1:]
        elif section == ":hierarchy" and w[0] not in ("begin", "end"):
            for child in w[1:]:
                bones[child]["parent"] = w[0]
    return bones


def read_amc(path, bones):
    """Frames: name -> (n, len(dof)) values, in degrees and CMU units."""
    data, frames = {}, 0
    for raw in open(path, encoding="latin-1"):
        line = raw.strip()
        if not line or line[0] in "#:":
            continue
        w = line.split()
        if w[0].isdigit():
            frames += 1
            continue
        data.setdefault(w[0], []).append([float(x) for x in w[1:]])
    out = {}
    for name, rows in data.items():
        a = np.array(rows)
        assert len(a) == frames, (path, name)
        out[name] = a
    return out, frames


class Motion:
    """A CMU trial, in Blender's frame: local rotations per bone and the root's path, in metres."""

    def __init__(self, clip):
        asf, amc = fetch(clip)
        self.clip = clip
        self.bones = read_asf(asf)
        vals, self.n = read_amc(amc, self.bones)
        self.fps = CMU_FPS
        self.order = []
        todo = ["root"]
        while todo:                                       # parents before children
            b = todo.pop(0)
            self.order.append(b)
            todo += [c for c, v in self.bones.items() if v["parent"] == b]
        self.parent = {b: self.bones[b]["parent"] for b in self.order}
        self.dir = {b: F @ self.bones[b]["direction"] for b in self.order}
        self.length = {b: self.bones[b]["length"] for b in self.order}
        self.local = {}
        for b in self.order:
            bo = self.bones[b]
            rx = ry = rz = np.zeros(self.n)
            v = vals.get(b)
            for i, d in enumerate(bo["dof"]):
                if v is None:
                    break
                if d == "rx":
                    rx = np.radians(v[:, i])
                elif d == "ry":
                    ry = np.radians(v[:, i])
                elif d == "rz":
                    rz = np.radians(v[:, i])
            c = bo["C"]
            self.local[b] = F @ c @ euler_xyz(rx, ry, rz) @ c.T @ F.T
        self.root = (F @ (vals["root"][:, :3] * UNIT).T).T

    def fk(self, local=None, root=None):
        """World rotations of every bone, and the end point of each, per frame."""
        local = local or self.local
        root = self.root if root is None else root
        g, end = {}, {}
        for b in self.order:
            p = self.parent[b]
            g[b] = local[b] if p is None else g[p] @ local[b]
            end[b] = root if p is None else end[p] + self.length[b] * (g[b] @ self.dir[b])
        return g, end

    def leg(self):
        return self.length["lfemur"] + self.length["ltibia"]


def heading_frame(v):
    """Rotations about Z taking horizontal directions v (n,3) onto -Y, the body's forward."""
    yaw = np.arctan2(v[..., 0], -v[..., 1])
    return rot_z(-yaw)


class Stride:
    """One stride of a trial, looped: local rotations with the heading taken out, and the hips'
    path split into the steady advance (`length` metres per stride) and what's left over."""

    LOOK = ["ltibia", "rtibia", "lfoot", "rfoot", "ltoes", "rtoes", "lradius", "rradius", "lwrist",
            "rwrist", "head", "thorax"]

    def __init__(self, mo, lo=0.5, hi=0.95):
        self.mo = mo
        g, end = mo.fk()
        n, fps = mo.n, mo.fps
        p = mo.root
        h = int(0.1 * fps)
        vel = np.zeros_like(p)
        vel[h:-h] = (p[2 * h:] - p[:-2 * h]) / (2 * h / fps)
        vel[:h], vel[-h:] = vel[h], vel[-h - 1]
        vel[:, 2] = 0
        speed = np.linalg.norm(vel, axis=1)
        y = heading_frame(vel)
        feat = np.concatenate([np.einsum("nij,nj->ni", y, end[b] - p) for b in self.LOOK] +
                              [p[:, 2:3], 0.08 * np.einsum("nij,nj->ni", y, vel)[:, 1:2],
                               0.3 * np.einsum("nij,nj->ni", y @ g["root"], np.tile([0, 0, 1.0], (n, 1)))], 1)
        best = None
        top = speed[h:-h].max()
        for N in range(int(lo * fps), int(hi * fps) + 1):
            for i in range(h, n - N - h):
                s = speed[i:i + N + 1]
                err = np.linalg.norm(feat[i] - feat[i + N]) / math.sqrt(len(self.LOOK))
                cost = err + 0.4 * (s.max() - s.min()) / s.mean() + 0.15 * (1 - s.mean() / top)
                if best is None or cost < best[0]:
                    best = (cost, i, N, err)
        if best is None:
            raise ValueError(mo.clip + ": too short for a stride")
        _, i, N, err = best
        self.start, self.N, self.err = i, N, err
        self.fps = fps
        travel = p[i + N] - p[i]
        travel[2] = 0
        yc = heading_frame(travel)
        # Local rotations over the stride, the heading taken off the root, then looped: the
        # mismatch between the stride's last frame and its first, spread evenly through it.
        u = np.arange(N + 1) / N
        local = {}
        for b in mo.order:
            r = mo.local[b][i:i + N + 1]
            if b == "root":
                r = yc @ r
            ax, ang = log_rot(r[-1].T @ r[0])
            local[b] = (r @ axis_angle(np.tile(ax, (N + 1, 1)), u * ang))[:N]
        q = (yc @ (p[i:i + N + 1] - p[i]).T).T
        self.length = float(-q[-1, 1])                                   # metres per stride
        fwd = -q[:, 1] - self.length * u
        side = q[:, 0] - q[-1, 0] * u
        up = p[i:i + N + 1, 2] - (p[i + N, 2] - p[i, 2]) * u
        self.offset = np.stack([side - side[:N].mean(), -fwd, up], 1)[:N]   # hips, about the steady advance
        self.local = local
        self.speed = self.length / (N / fps)
        self.cadence = 2 * 60.0 / (N / fps)                                 # steps a minute


class Retarget:
    """A stride put onto one MPFB body: per stride frame, every bone's turn from rest (`delta`,
    `dq`, armature space), its local rotation (`local`, quaternions, as Blender keys them) and
    where the hips are, about the steady advance (`offset`)."""

    CURL = 1.2                                    # radians: how far the fingers close
    LIMBS = ("femur", "tibia", "foot", "toes", "humerus", "radius", "wrist", "hand", "fingers", "thumb")

    def __init__(self, stride, rest):
        """rest: bone -> dict(R (3x3, armature space), head, tail, parent), the rig at rest."""
        mo = stride.mo
        self.stride = stride
        self.rest = rest
        # The calibration pose: the CMU skeleton with its limbs swung onto the body's (its zero
        # pose has the arms straight out and the legs splayed). The spine, neck and collarbones
        # aren't swung: there the two skeletons just lay their bones out differently, and copying
        # CMU's directions would hunch the body's shoulders.
        cal = {}
        for b in mo.order:
            par = mo.parent[b]
            gp = np.eye(3) if par is None else cal[par]
            t = rest[BONES[b]]
            if b[1:] in self.LIMBS and mo.length[b] > 0:
                cal[b] = between(gp @ mo.dir[b], t["tail"] - t["head"]) @ gp
            else:
                cal[b] = gp
        g, _ = mo.fk(stride.local, np.zeros((stride.N, 3)))
        delta = {b: g[b] @ cal[b].T for b in mo.order}         # each bone's turn away from the calibration pose
        # Hands loosely closed. CMU's fingers barely move; the body has one bone for its four
        # fingers, bent here toward the palm at the knuckles.
        for side, medial in (("l", -1.0), ("r", 1.0)):
            t = rest[BONES[side + "fingers"]]
            d = (t["tail"] - t["head"]) / np.linalg.norm(t["tail"] - t["head"])
            ax = np.cross(d, [medial, 0.0, 0.0])
            delta[side + "fingers"] = delta[side + "hand"] @ axis_angle(ax / np.linalg.norm(ax), self.CURL)
        self.dq = {b: to_quat(delta[b]) for b in mo.order}
        self.local = {}
        for b in mo.order:
            t = rest[BONES[b]]
            r = t["R"]
            par = mo.parent[b]
            dp = np.eye(3) if par is None else delta[par]
            self.local[BONES[b]] = to_quat(r.T @ np.swapaxes(dp, -1, -2) @ delta[b] @ r)
        self.k = (np.linalg.norm(rest["LeftUpLeg"]["tail"] - rest["LeftUpLeg"]["head"]) +
                  np.linalg.norm(rest["LeftLeg"]["tail"] - rest["LeftLeg"]["head"])) / mo.leg()
        self.length = self.k * stride.length
        off = self.k * stride.offset
        # Lift or drop the whole stride so the lowest the feet go is the ground.
        heads, tails = self.joints(off, delta)
        low = []
        for side in ("Left", "Right"):
            low.append(heads[side + "Foot"][:, 2] - rest[side + "Foot"]["head"][2])
            low.append(tails[side + "ToeBase"][:, 2] - rest[side + "ToeBase"]["tail"][2])
        self.dz = -float(np.min(low))
        self.offset = off + np.array([0, 0, self.dz])
        self.delta = delta

    def joints(self, hips, delta):
        """The body's joints at each stride frame, the hips at `hips` (armature space, no heading)."""
        rest = self.rest
        inv = {v: k for k, v in BONES.items()}
        heads, tails = {}, {}
        for b in self.stride.mo.order:
            name = BONES[b]
            t = rest[name]
            par = t["parent"]
            d = delta[b]
            if par is None:
                heads[name] = hips
            else:
                heads[name] = heads[par] + np.einsum("nij,j->ni", delta[inv[par]], t["head"] - rest[par]["head"])
            tails[name] = heads[name] + np.einsum("nij,j->ni", d, t["tail"] - t["head"])
        return heads, tails

    def slide(self):
        """How far a planted foot would drift without `plant`, in cm: the stride laid along a
        straight path at its own pace, the largest wander of the ball of either foot while it's
        on the ground."""
        N = self.stride.N
        adv = np.stack([np.zeros(N), -self.length * np.arange(N) / N, np.zeros(N)], 1)
        _, tails = self.joints(self.offset, self.delta)
        worst = 0.0
        for side in ("Left", "Right"):
            ball = tails[side + "Foot"] + adv
            down = ball[:, 2] - self.rest[side + "Foot"]["tail"][2] < 0.02
            if down.all() or not down.any():
                continue
            s = int(np.argmin(down))                                       # start on a frame in the air
            idx = np.roll(np.arange(N), -s)
            run = []
            for i in list(idx) + [idx[0]]:
                if down[i]:
                    run.append(i)
                elif run:
                    wrap = np.array(run)[:, None] < run[0]                 # past the end of the stride
                    pts = ball[run, :2] + np.where(wrap, [0.0, -self.length], 0.0)
                    worst = max(worst, float(np.linalg.norm(np.ptp(pts, axis=0))))
                    run = []
        return 100 * worst


def mean_rot(m):
    """The average of rotation matrices (n,3,3), as a rotation."""
    u, _, vt = np.linalg.svd(np.mean(m, axis=0))
    r = u @ vt
    return r if np.linalg.det(r) > 0 else u @ np.diag([1, 1, -1.0]) @ vt


# ---------------------------------------------------------------- inside Blender: materials
def srgb(c):
    return tuple(((v + 0.055) / 1.055) ** 2.4 for v in c)


SKIN = [srgb(c) for c in ((0.36, 0.22, 0.15), (0.30, 0.18, 0.12), (0.42, 0.27, 0.18), (0.27, 0.16, 0.11),
                          (0.33, 0.20, 0.13), (0.39, 0.24, 0.16))]
HIDE = [srgb(c) for c in ((0.36, 0.26, 0.17), (0.30, 0.21, 0.13), (0.42, 0.31, 0.2), (0.27, 0.2, 0.14))]


def material(name, build):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    build(nt, p)
    return m


def noise(nt, scale, detail=4.0):
    """Noise laid on the mesh's UVs, so it stays put on a body in motion."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs["UV"], n.inputs["Vector"])
    return n


def ramp(nt, src, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
    els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, c in stops[1:-1]:
        e = els.new(pos)
        e.color = (*c, 1)
    nt.links.new(src, r.inputs["Fac"])
    return r


def bump(nt, src, strength, p, distance=0.002):
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    nt.links.new(src, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"])


def skin(tone, rng):
    def build(nt, p):
        c = ramp(nt, noise(nt, 40.0).outputs["Fac"], [(0.3, [v * 0.82 for v in tone]), (0.7, [v * 1.12 for v in tone])])
        nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Subsurface Weight"].default_value = 0.25
        p.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.25)
        p.inputs["Subsurface Scale"].default_value = 0.012
        p.inputs["Roughness"].default_value = rng.uniform(0.4, 0.52)
        p.inputs["Specular IOR Level"].default_value = 0.45
        bump(nt, noise(nt, 900.0, 2.0).outputs["Fac"], 0.06, p)
    return material("Skin", build)


def hide(rng):
    tone = rng.choice(HIDE)

    def build(nt, p):
        c = ramp(nt, noise(nt, 25.0, 6.0).outputs["Fac"], [(0.35, [v * 0.7 for v in tone]), (0.5, tone), (0.68, [v * 1.15 for v in tone])])
        nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Roughness"].default_value = 0.82
        p.inputs["Sheen Weight"].default_value = 0.3
        bump(nt, noise(nt, 120.0, 6.0).outputs["Fac"], 0.35, p)
    return material("Hide", build)


def image(nt, path, data=False):
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    if data:
        tex.image.colorspace_settings.name = 'Non-Color'
    return tex


def skin_scan(path, rng):
    """Skin on MakeHuman's scanned texture (CC0): its colour a little darker or lighter person to
    person, a shallow scatter (a few mm, as in skin), rough, with pores."""
    def build(nt, p):
        t = image(nt, path)
        hsv = nt.nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Saturation"].default_value = 0.95
        hsv.inputs["Value"].default_value = rng.uniform(0.45, 0.62)
        nt.links.new(t.outputs["Color"], hsv.inputs["Color"])
        nt.links.new(hsv.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Subsurface Weight"].default_value = 0.12
        p.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
        p.inputs["Subsurface Scale"].default_value = 0.006
        p.inputs["Roughness"].default_value = rng.uniform(0.36, 0.46)       # a sheen of sweat: they're running
        p.inputs["Specular IOR Level"].default_value = 0.5
        bump(nt, noise(nt, 900.0, 2.0).outputs["Fac"], 0.05, p)
    return material("Skin, scanned", build)


def leather(rng, maps):
    """Hide: a scanned leather (Poly Haven, CC0) in patches lighter and darker, mapped by the
    wrap's rest shape so it doesn't swim, its edge ragged: where the `hem` attribute (0 at the
    cut, 1 a few cm in) is low, noise eats it away."""
    warm = (rng.uniform(1.25, 1.5), rng.uniform(1.15, 1.35), rng.uniform(0.95, 1.1))    # raw hide: paler than skin

    def build(nt, p):
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "rest"
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (2.0, 2.0, 2.0)
        mp.inputs["Location"].default_value = (rng.random(), rng.random(), 0)
        nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
        tex = {k: image(nt, v, k != "Diffuse") for k, v in maps.items() if k in ("Diffuse", "Rough", "nor_gl")}
        for t in tex.values():
            nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        patch = ramp(nt, noise(nt, 6.0, 4.0).outputs["Fac"], [(0.35, [v * 0.7 for v in warm]), (0.65, [v * 1.15 for v in warm])])
        col = nt.nodes.new("ShaderNodeMix")
        col.data_type, col.blend_type = 'RGBA', 'MULTIPLY'
        col.inputs[0].default_value = 1.0
        a, b = [i for i in col.inputs if i.type == 'RGBA'][:2]
        dull = nt.nodes.new("ShaderNodeHueSaturation")
        dull.inputs["Saturation"].default_value = 0.45
        nt.links.new(tex["Diffuse"].outputs["Color"], dull.inputs["Color"])
        nt.links.new(dull.outputs["Color"], a)
        nt.links.new(patch.outputs["Color"], b)
        nt.links.new([o for o in col.outputs if o.type == 'RGBA'][0], p.inputs["Base Color"])
        nt.links.new(tex["Rough"].outputs["Color"], p.inputs["Roughness"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.uv_map = "rest"
        nt.links.new(tex["nor_gl"].outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
        # The ragged edge: hem minus noise, sharpened; below zero is gone.
        hem = nt.nodes.new("ShaderNodeAttribute")
        hem.attribute_name = "hem"
        n = noise(nt, 40.0, 3.0)
        cut = nt.nodes.new("ShaderNodeMath")
        cut.operation = 'SUBTRACT'
        nt.links.new(hem.outputs["Fac"], cut.inputs[0])
        nt.links.new(n.outputs["Fac"], cut.inputs[1])
        sharp = nt.nodes.new("ShaderNodeMath")
        sharp.operation, sharp.use_clamp = 'MULTIPLY_ADD', True
        sharp.inputs[1].default_value = 12.0
        sharp.inputs[2].default_value = 0.5
        nt.links.new(cut.outputs[0], sharp.inputs[0])
        clear = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        out = [x for x in nt.nodes if x.type == 'OUTPUT_MATERIAL'][0]
        nt.links.new(sharp.outputs[0], mix.inputs["Fac"])
        nt.links.new(clear.outputs[0], mix.inputs[1])
        nt.links.new(p.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return material("Hide", build)


def hair(rng):
    def build(nt, p):
        p.inputs["Base Color"].default_value = (*srgb((0.035, 0.028, 0.022)), 1)
        p.inputs["Roughness"].default_value = 0.85
        p.inputs["Sheen Weight"].default_value = 0.25
        p.inputs["Sheen Tint"].default_value = (*srgb((0.25, 0.2, 0.17)), 1)
        p.inputs["Sheen Roughness"].default_value = 0.6
        bump(nt, noise(nt, 1500.0, 2.0).outputs["Fac"], 0.9, p, 0.004)
    return material("Hair", build)


def eye(rng):
    def build(nt, p):
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_name = "iris"
        white, iris = srgb((0.62, 0.56, 0.5)), srgb((0.12, 0.06, 0.03))
        c = ramp(nt, a.outputs["Fac"], [(0.0, white), (0.8, white), (0.83, iris), (0.955, iris), (0.965, (0.002, 0.002, 0.002)), (1.0, (0.002, 0.002, 0.002))])
        nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Roughness"].default_value = 0.06
        p.inputs["Coat Weight"].default_value = 1.0
    return material("Eye", build)


def wood():
    def build(nt, p):
        c = ramp(nt, noise(nt, 8.0).outputs["Fac"], [(0.3, srgb((0.26, 0.18, 0.1))), (0.7, srgb((0.4, 0.29, 0.17)))])
        nt.links.new(c.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Roughness"].default_value = 0.7
    return material("Spear shaft", build)


def stone():
    def build(nt, p):
        p.inputs["Base Color"].default_value = (*srgb((0.2, 0.19, 0.18)), 1)
        p.inputs["Roughness"].default_value = 0.55
    return material("Stone point", build)


# ---------------------------------------------------------------- inside Blender: bodies
def mpfb():
    """MPFB's HumanService and TargetService, with the extension enabled."""
    import importlib
    if MPFB not in bpy.context.preferences.addons:
        bpy.ops.preferences.addon_enable(module=MPFB)
    try:
        hs = importlib.import_module(MPFB + ".services.humanservice")
        ts = importlib.import_module(MPFB + ".services.targetservice")
    except ImportError:
        raise RuntimeError("MPFB2 isn't installed in Blender 5.0. Install it with:\n"
                           "  blender -c extension install-file -r user_default " + str(MPFB_ZIP))
    return hs.HumanService, ts.TargetService


def vertex_sets(ob, names):
    """Vertex group name -> set of the vertex indices in it."""
    want = {ob.vertex_groups[n].index: n for n in names if n in ob.vertex_groups}
    out = {n: set() for n in names}
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group in want and g.weight > 0:
                out[want[g.group]].add(v.index)
    return out


def strongest(ob, bones):
    """The vertices whose strongest bone is one of `bones`."""
    rig = {ob.vertex_groups[b].index for b in BONES.values() if b in ob.vertex_groups}
    want = {ob.vertex_groups[b].index for b in bones}
    out = set()
    for v in ob.data.vertices:
        best = max((g for g in v.groups if g.group in rig), key=lambda g: g.weight, default=None)
        if best is not None and best.group in want:
            out.add(v.index)
    return out


def rest_of(rig):
    """The rig at rest, for Retarget: bone -> rotation, head, tail, parent (armature space)."""
    out = {}
    for b in rig.data.bones:
        m = np.array(b.matrix_local)
        out[b.name] = {"R": m[:3, :3], "head": np.array(b.head_local), "tail": np.array(b.tail_local),
                       "parent": b.parent.name if b.parent else None}
    return out


def piece(src, name, keep, mats, solid=0.0, subsurf=1, hem=None):
    """A copy of the body with only the vertices in `keep`, still weighted to the rig. hem: the
    heights of its cut edges, for a wrap: then it gets UVs from its rest shape (metres round and
    up) and a `hem` attribute, 0 at a cut edge and 1 from 6 cm in."""
    ob = src.copy()
    ob.data = src.data.copy()
    ob.name = ob.data.name = name
    for c in src.users_collection:
        c.objects.link(ob)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.materials.clear()
    for m in mats:
        ob.data.materials.append(m)
    for p in ob.data.polygons:
        p.use_smooth = True
    if hem is not None:
        me = ob.data
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        d = np.min([np.abs(co[:, 2] - h) for h in hem], axis=0)
        me.attributes.new("hem", 'FLOAT', 'POINT').data.foreach_set("value", np.clip(d / 0.06, 0, 1))
        uv = me.uv_layers.new(name="rest")
        loops = np.empty(len(me.loops), dtype=np.int32)
        me.loops.foreach_get("vertex_index", loops)
        c = co[loops]
        ang = np.arctan2(c[:, 0], -c[:, 1])
        uv.data.foreach_set("uv", np.stack([ang * 0.16, c[:, 2]], 1).ravel())
    if solid:
        so = ob.modifiers.new("Thickness", 'SOLIDIFY')
        so.thickness, so.offset, so.use_even_offset = solid, 1.0, True
    if subsurf:
        sd = ob.modifiers.new("Smooth", 'SUBSURF')
        sd.levels, sd.render_levels = 0, subsurf
    return ob


def mpfb_data(kind):
    """A folder of MPFB's user data (where the MakeHuman asset pack is unpacked)."""
    import importlib
    return pathlib.Path(importlib.import_module(MPFB + ".services.locationservice").LocationService.get_user_data(kind))


# Real mode: MakeHuman's CC0 asset pack (makehuman_system_assets_cc0.zip, from
# files.makehumancommunity.org, unpacked into mpfb_data): scanned skins, hair, brows and lashes.
HAIR = {"man": ["afro01"], "woman": ["afro01"], "girl": ["afro01"]}     # short, tightly coiled


def person(name, sex, height, seed, real=False, leather_maps=None):
    """A rigged person `height` m tall, feet at the origin, facing -Y: sex is 'man', 'woman' or
    'girl'. Returns the rig, its parts, and the rig at rest. real: MakeHuman's textured skin,
    hair, brows and lashes, fitted by MPFB, and hides of scanned leather (leather_maps)."""
    HS, TS = mpfb()
    rng = random.Random(seed)
    girl = sex == "girl"
    md = TS.get_default_macro_info_dict()
    md.update({"gender": rng.uniform(0.9, 1.0) if sex == "man" else rng.uniform(0.0, 0.08),
               "age": 0.169 if girl else rng.uniform(0.45, 0.58),          # 10 years old; 22 to 33
               "muscle": 0.5 if girl else rng.uniform(0.55, 0.8),
               "weight": rng.uniform(0.32, 0.48),
               "proportions": rng.uniform(0.55, 0.9),
               "height": rng.uniform(0.35, 0.65),
               "cupsize": 0.5 if girl else rng.uniform(0.35, 0.6),
               "firmness": 0.5 if girl else rng.uniform(0.4, 0.7)})
    md["race"] = {"african": 1.0, "asian": 0.0, "caucasian": 0.0}
    human = HS.create_human(mask_helpers=False, macro_detail_dict=md)
    TS.bake_targets(human)
    sets = vertex_sets(human, ["body", "helper-skirt", "helper-tights", "helper-l-eye", "helper-r-eye",
                               "scalp", "nipple"])
    co = np.empty(len(human.data.vertices) * 3)
    human.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    s = height / co[list(sets["body"]), 2].max()
    human.data.transform(Matrix.Scale(s, 4))
    co *= s
    rig = HS.add_builtin_rig(human, "cmu_mb")
    rig.name = rig.data.name = name + " rig"
    for m in human.modifiers:                     # dual quaternions: shoulders and hips keep their volume
        if m.type == 'ARMATURE':
            m.use_deform_preserve_volume = True
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    rest = rest_of(rig)
    hair_style = rng.choice(HAIR[sex]) if real else None
    fitted = {}
    if real:                              # fitted to the whole mesh, so before the shells are cut off
        for kind, what in (("eyebrows", "eyebrow%03d" % rng.randint(1, 12)), ("eyelashes", "eyelashes0%d" % rng.randint(1, 4)),
                           ("hair", hair_style)):
            if what:
                ob = HS.add_mhclo_asset(str(mpfb_data(kind) / what / (what + ".mhclo")), human,
                                        asset_type=kind.capitalize(), subdiv_levels=0)
                ob.name = name + " " + kind
                fitted[kind] = ob
        age = "young" if girl or md["age"] < 0.52 else "middleage"
        skin_dir = mpfb_data("skins") / ("%s_african_%s" % (age, "male" if sex == "man" else "female"))
        mhmat = next(skin_dir.glob("*.mhmat"))
        tex = next(l.split()[1] for l in open(mhmat, encoding="utf-8") if l.startswith("diffuseTexture"))
        scanned = skin_scan(skin_dir / tex, rng)
    z = co[:, 2]
    hip, knee = rest["LeftUpLeg"]["head"][2], rest["LeftLeg"]["head"][2]
    shoulder = rest["LeftArm"]["head"][2]
    waist = rest["LowerBack"]["head"][2]
    tone = SKIN[seed % len(SKIN)]
    torso = strongest(human, ("Hips", "LowerBack", "Spine", "Spine1"))         # not the arms
    parts = {"rig": rig, **fitted}
    wrap = (lambda: leather(rng, leather_maps)) if real and leather_maps else (lambda: hide(rng))
    # The hide wrap: MPFB's skirt shell, cut off part way down the thigh.
    cut = knee + (hip - knee) * {"man": 0.55, "woman": 0.42, "girl": 0.38}[sex]
    parts["wrap"] = piece(human, name + " wrap", {i for i in sets["helper-skirt"] if z[i] >= cut},
                          [wrap()], solid=0.004, hem=[cut])
    if sex == "woman":                    # a band of hide over the breasts, from the tights shell
        zn = co[list(sets["nipple"]), 2].mean()
        lo, hi = zn - 0.055 * height / 1.6, zn + 0.075 * height / 1.6
        parts["top"] = piece(human, name + " top", {i for i in sets["helper-tights"] & torso if lo <= z[i] <= hi},
                             [wrap()], solid=0.004, hem=[lo, hi])
    elif girl:                            # a top of hide from under the arms to the waist
        hi = shoulder - 0.07 * height / 1.3
        parts["top"] = piece(human, name + " top", {i for i in sets["helper-tights"] & torso if waist - 0.04 <= z[i] <= hi},
                             [wrap()], solid=0.004, hem=[waist - 0.04, hi])
    if "hair" not in fitted:              # close-cropped: a shell over the scalp
        parts["hair"] = piece(human, name + " hair", sets["scalp"], [hair(rng)], solid=0.007)
    eyes = piece(human, name + " eyes", sets["helper-l-eye"] | sets["helper-r-eye"], [eye(rng)], subsurf=0)
    me = eyes.data
    ec = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", ec)
    ec = ec.reshape(-1, 3)
    iris = np.zeros(len(ec))
    for side in (ec[:, 0] > 0, ec[:, 0] <= 0):                            # each eye about its own centre
        d = ec[side] - ec[side].mean(0)
        iris[side] = -d[:, 1] / np.linalg.norm(d, axis=1)
    at = me.attributes.new("iris", 'FLOAT', 'POINT')
    at.data.foreach_set("value", iris)
    parts["eyes"] = eyes
    # The body itself: everything but the fitting shells.
    bm = bmesh.new()
    bm.from_mesh(human.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in sets["body"]], context='VERTS')
    bm.to_mesh(human.data)
    bm.free()
    human.name = human.data.name = name + " body"
    human.data.materials.clear()
    human.data.materials.append(scanned if real else skin(tone, rng))
    for p in human.data.polygons:
        p.use_smooth = True
    sd = human.modifiers.new("Smooth", 'SUBSURF')
    sd.levels, sd.render_levels = 0, 1
    parts["body"] = human
    parts["rest"] = rest
    return parts


def spear(rig, rt, name):
    """A spear 2 m long in the right hand, the grip two-fifths of the way up from the butt. It
    rides in the hand but keeps its angle to the hips, pointing forward and a little up, as a
    runner steadies a spear against the swing of the arm."""
    rest = rt.rest
    hips = mean_rot(rt.delta["root"]) @ rest["Hips"]["R"]                  # the hips' mean turn in the stride
    want = np.array([0.0, -1.0, 0.15]) / np.linalg.norm([0.0, -1.0, 0.15])
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.013, radius2=0.011, depth=2.0,
                          matrix=Matrix.Translation((0, 0, 0.2)))
    shaft = len(bm.faces)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.022, radius2=0.0, depth=0.16,
                          matrix=Matrix.Translation((0, 0, 1.28)) @ Matrix.Diagonal((1.0, 0.45, 1.0, 1.0)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(wood())
    me.materials.append(stone())
    for p in me.polygons:
        p.material_index = 0 if p.index < shaft else 1
    ob = bpy.data.objects.new(name, me)
    for c in rig.users_collection:
        c.objects.link(ob)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = Vector(hips.T @ want).to_track_quat('Z', 'Y')
    at = ob.constraints.new('COPY_LOCATION')                              # in the fist
    at.target, at.subtarget, at.head_tail = rig, "RightFingerBase", 0.3
    turn = ob.constraints.new('COPY_ROTATION')                            # turned with the hips
    turn.target, turn.subtarget, turn.mix_mode = rig, "Hips", 'BEFORE'
    return ob


def qslerp(q0, q1, w):
    """Slerp between quaternion arrays (n,4) by weights (n,)."""
    d = np.sum(q0 * q1, axis=1)
    q1 = np.where(d[:, None] < 0, -q1, q1)
    d = np.abs(d)
    a = np.arccos(np.clip(d, -1, 1))
    s = np.sin(a)
    small = s < 1e-6
    k0 = np.where(small, 1 - w, np.sin((1 - w) * a) / np.where(small, 1, s))
    k1 = np.where(small, w, np.sin(w * a) / np.where(small, 1, s))
    q = k0[:, None] * q0 + k1[:, None] * q1
    return q / np.linalg.norm(q, axis=1, keepdims=True)


def qmat(q):
    """Quaternions (n,4), w first -> rotation matrices (n,3,3)."""
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
                     np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
                     np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1)], -2)


def between_many(a, b):
    """Shortest rotations taking directions a (n,3) onto b (n,3)."""
    a = a / np.linalg.norm(a, axis=1, keepdims=True)
    b = b / np.linalg.norm(b, axis=1, keepdims=True)
    c = np.cross(a, b)
    s = np.linalg.norm(c, axis=1)
    ax = np.where(s[:, None] > 1e-9, c / np.maximum(s, 1e-9)[:, None], [1.0, 0, 0])
    return axis_angle(ax, np.arctan2(s, np.sum(a * b, axis=1)))


def step_rate(v, rt, bend=0.3):
    """Strides a second at speed v: the mocap's own rate at the speed its stride fits, rising
    only as v**0.3 beyond it, so a faster runner lengthens the stride more than the cadence, as
    people do. The difference in stride is taken up by the legs (see `plant`)."""
    native = rt.stride.fps / rt.stride.N
    return native * (np.maximum(v, 0.3) / (rt.length * native)) ** bend


def plant(world, heads, tails, rest, n, ground=0.025, ease=6):
    """Keep each foot still while it's on the ground. While the ball of the foot is down it's
    held where it was halfway through the contact, the leg reaching it by two-bone IK in the
    plane its knee already bends in; in the air the hold eases off and on again. world: bone ->
    (n,3,3) turns from rest, armature space; heads, tails: bone -> (n,3). Changes world in place
    and returns the largest drift left in a planted foot, in cm."""
    worst = 0.0
    for side in ("Left", "Right"):
        thigh, shin, foot = side + "UpLeg", side + "Leg", side + "Foot"
        ball = tails[foot]
        down = ball[:, 2] - rest[foot]["tail"][2] < ground
        shift = np.zeros((n, 3))
        runs, i = [], 0
        while i < n:
            if down[i]:
                j = i
                while j + 1 < n and down[j + 1]:
                    j += 1
                runs.append((i, j))
                i = j + 1
            else:
                i += 1
        for a, b in runs:
            hold = ball[(a + b) // 2, :2]
            shift[a:b + 1, :2] = hold - ball[a:b + 1, :2]
        for (a0, b0), (a1, b1) in zip([(None, -1)] + runs, runs + [(n, None)]):   # ease across each flight
            lo, hi = b0 + 1, a1
            if hi <= lo:
                continue
            s0 = shift[b0] if b0 >= 0 else np.zeros(3)
            s1 = shift[a1] if a1 < n else np.zeros(3)
            u = (np.arange(lo, hi) - (lo - 1)) / (hi - lo + 1)
            u = u * u * (3 - 2 * u)
            shift[lo:hi] = (1 - u)[:, None] * s0 + u[:, None] * s1
        hip, knee, ankle = heads[thigh], heads[shin], heads[foot]
        l1 = np.linalg.norm(rest[shin]["head"] - rest[thigh]["head"])
        l2 = np.linalg.norm(rest[foot]["head"] - rest[shin]["head"])
        goal = ankle + shift
        d = goal - hip
        dist = np.clip(np.linalg.norm(d, axis=1), abs(l1 - l2) + 1e-4, (l1 + l2) * 0.9995)
        dn = d / np.linalg.norm(d, axis=1, keepdims=True)
        goal = hip + dn * dist[:, None]
        pole = (knee - hip) - np.sum((knee - hip) * dn, axis=1)[:, None] * dn
        pole /= np.maximum(np.linalg.norm(pole, axis=1, keepdims=True), 1e-9)
        along = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
        new_knee = hip + dn * along[:, None] + pole * np.sqrt(np.maximum(l1 * l1 - along * along, 0))[:, None]
        s1 = between_many(knee - hip, new_knee - hip)
        world[thigh] = s1 @ world[thigh]
        s2 = between_many(np.einsum("nij,nj->ni", s1, ankle - knee), goal - new_knee)
        world[shin] = s2 @ s1 @ world[shin]
        new_ball = goal + np.einsum("nij,j->ni", world[foot], rest[foot]["tail"] - rest[foot]["head"])
        for a, b in runs:
            if b > a:
                worst = max(worst, float(np.linalg.norm(np.ptp(new_ball[a:b + 1, :2], axis=0))))
    return 100 * worst


def run(rig, rt, frames, xs, ys, phase0=0.0, fps=24):
    """Key the rig running along the path (xs, ys), one point per frame, turned to face along
    it, its stride advanced by `step_rate` and its feet held still on the ground by `plant`."""
    from bpy_extras import anim_utils
    rest = rt.rest
    p = np.stack([np.asarray(xs, float), np.asarray(ys, float)], 1)
    n = len(p)
    step = np.linalg.norm(np.diff(p, axis=0), axis=1)
    speed = np.convolve(np.concatenate([[step[0]], step]) * fps, np.ones(5) / 5, mode="same")
    speed[:2], speed[-2:] = speed[2], speed[-3]
    phase = phase0 + np.concatenate([[0.0], np.cumsum(step_rate(speed[1:], rt) / fps)])
    lo, hi = np.maximum(np.arange(n) - 3, 0), np.minimum(np.arange(n) + 3, n - 1)
    tang = p[hi] - p[lo]
    yaw = np.arctan2(tang[:, 0], -tang[:, 1])                                # the body's -Y along the path
    h = rot_z(yaw)
    # The stride at each frame's phase: turns from rest (world) per bone, and the hips.
    N = rt.stride.N
    x = (phase % 1.0) * N
    a = np.floor(x).astype(int) % N
    b, w = (a + 1) % N, x - np.floor(x)
    inv = {v: k for k, v in BONES.items()}
    world = {}
    for name in rt.local:
        dq = rt.dq[inv[name]]
        world[name] = h @ qmat(qslerp(dq[a], dq[b], w))
    off = (1 - w)[:, None] * rt.offset[a] + w[:, None] * rt.offset[b]
    hips = np.concatenate([p, np.zeros((n, 1))], 1) + np.einsum("nij,nj->ni", h, off)
    heads, tails = {}, {}
    for s in rt.stride.mo.order:
        name = BONES[s]
        t = rest[name]
        par = t["parent"]
        heads[name] = hips if par is None else heads[par] + np.einsum("nij,j->ni", world[par], t["head"] - rest[par]["head"])
        tails[name] = heads[name] + np.einsum("nij,j->ni", world[name], t["tail"] - t["head"])
    slide = plant(world, heads, tails, rest, n)
    keys = {}
    for name in rt.local:                                                   # back to each bone's own turn
        t = rest[name]
        r = t["R"]
        parent = np.eye(3) if t["parent"] is None else np.swapaxes(world[t["parent"]], -1, -2)
        keys[name] = to_quat(r.T @ parent @ world[name] @ r)
    loc = np.einsum("ij,nj->ni", rest["Hips"]["R"].T, hips - rest["Hips"]["head"])
    rig.animation_data_create()
    rig.pose.bones["Hips"].keyframe_insert("location", frame=frames[0])
    ad = rig.animation_data
    bag = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)

    def put(path, index, values):
        fc = bag.fcurves.find(path, index=index) or bag.fcurves.new(path, index=index)
        while len(fc.keyframe_points):
            fc.keyframe_points.remove(fc.keyframe_points[0], fast=True)
        fc.keyframe_points.add(n)
        flat = np.empty(2 * n)
        flat[0::2], flat[1::2] = frames, values
        fc.keyframe_points.foreach_set("co", flat)
        fc.keyframe_points.foreach_set("interpolation", [1] * n)            # linear
        fc.update()

    for name, q in keys.items():
        for j in range(4):
            put('pose.bones["%s"].rotation_quaternion' % name, j, q[:, j])
    for j in range(3):
        put('pose.bones["Hips"].location', j, loc[:, j])
    steps = step_rate(speed, rt) * 120                                     # two steps a stride, 60 s a minute
    return {"speed": speed, "steps": steps, "stretch": speed / (step_rate(speed, rt) * rt.length), "slide": slide}


if __name__ == "__main__":
    print("%-7s %6s %7s %6s %6s %7s %6s" % ("clip", "frames", "stride", "m/s", "steps", "loop", "err cm"))
    for c in CLIPS:
        mo = Motion(c)
        try:
            s = Stride(mo)
        except ValueError as e:
            print(e)
            continue
        print("%-7s %6d %6.2fm %6.2f %6.0f %3d+%-3d %6.1f" % (c, mo.n, s.length, s.speed, s.cadence, s.start, s.N, 100 * s.err))
