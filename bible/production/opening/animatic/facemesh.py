"""A human face for the animatic, from a real face mesh rather than sculpted bumps (v3).

The geometry is MediaPipe's canonical face model (`data/canonical_face_model.obj`, Apache 2.0): 468
vertices measured from real faces, forehead to chin and cheek to cheek. It has no back of the head,
no ears and no hair, which suits the Opening: the face always comes out of something (sand, black,
white) and its edges are meant to dissolve into it.

Expressions are made by moving landmark groups (brows, lids, mouth corners, jaw) and letting the
movement spread smoothly to the vertices around them, so the four-face rule's parameters still apply:

  brow   -1 lowered .. +1 raised       curve  -1 frown .. +1 smile
  open    0 shut   ..  1 wide open     eyes    0 closed .. 1 open      wide  0 .. 1 eyes widened

The renderer splats a dense point cloud sampled from the mesh (fixed barycentric samples, so a
deformed mesh moves its points with it) into a depth buffer, with smooth normals. Output is the same
kind of dictionary face.face_fields returns, plus normals, so the beats can light the face.

This is still a placeholder for the filmed face (DOSSIER §6). When depth maps from the face shoot
exist, they replace `render_face`'s depth and normals; everything that lights or sculpts sand with
them stays.
"""
from __future__ import annotations

import os

import numpy as np

from common import Grid, blur, smoothstep, polygon_mask

HERE = os.path.dirname(os.path.abspath(__file__))

# landmark groups (MediaPipe face mesh indices). "R" and "L" are the image's right and left.
EYE_L = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
EYE_R = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
LID_UP_L = [173, 157, 158, 159, 160, 161, 246]
LID_UP_R = [398, 384, 385, 386, 387, 388, 466]
LID_LO_L = [7, 163, 144, 145, 153, 154, 155]
LID_LO_R = [249, 390, 373, 374, 380, 381, 382]
BROW_L = [70, 63, 105, 66, 107, 46, 53, 52, 65, 55]
BROW_R = [300, 293, 334, 296, 336, 276, 283, 282, 295, 285]
BROW_INNER = [107, 66, 55, 65, 336, 296, 285, 295]
LIP_IN = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
LIP_IN_LOWER = [95, 88, 178, 87, 14, 317, 402, 318, 324]
LIP_OUT_LOWER = [146, 91, 181, 84, 17, 314, 405, 321, 375]
CORNERS = [61, 291, 78, 308]
CHIN = 152
HEAD_C = (0.0, 0.12, -0.42)   # the skull behind the face, in face units (half-height 1)
HEAD_R = (0.90, 1.15, 0.95)


def _load_obj(path):
    V, Fc = [], []
    with open(path) as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            if p[0] == "v":
                V.append([float(a) for a in p[1:4]])
            elif p[0] == "f":
                Fc.append([int(a.split("/")[0]) - 1 for a in p[1:4]])
    return np.array(V, np.float64), np.array(Fc, np.int64)


class FaceMesh:
    """Loaded once per process. Points are sampled at three densities; render picks one by size."""

    def __init__(self, seed=7):
        V, Fc = _load_obj(os.path.join(HERE, "data", "canonical_face_model.obj"))
        # centre: the face spans y -9.4 (chin) .. 8.26 (top); centre it and make half-height 1
        self.cy = (V[:, 1].max() + V[:, 1].min()) / 2
        self.half = (V[:, 1].max() - V[:, 1].min()) / 2
        V = V.copy()
        V[:, 1] -= self.cy
        V /= self.half
        self.V0 = V.astype(np.float32)
        self.F = Fc
        r = np.random.default_rng(seed)
        a, b, c = V[Fc[:, 0]], V[Fc[:, 1]], V[Fc[:, 2]]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        self.levels = []
        for n in (40_000, 160_000, 640_000):
            cnt = r.multinomial(n, area / area.sum())
            tri = np.repeat(np.arange(len(Fc)), cnt)
            u = r.random(n)
            v = r.random(n)
            flip = u + v > 1
            u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
            w = np.stack([1 - u - v, u, v], 1).astype(np.float32)
            self.levels.append((n, tri, w))
        # the rest of the head: an ellipsoid set just behind the face, so the forehead rolls on into a
        # skull and the cheeks into the sides of the head instead of stopping at a mask's edge
        self.head = []
        for n in (150_000, 600_000, 2_000_000):
            th = np.arccos(1 - 2 * r.random(n))
            ph = r.random(n) * 2 * np.pi
            ux, uy, uz = np.sin(th) * np.cos(ph), np.cos(th), np.sin(th) * np.sin(ph)
            keep = uz > -0.35
            ux, uy, uz = ux[keep], uy[keep], uz[keep]
            P = np.stack([HEAD_C[0] + HEAD_R[0] * ux, HEAD_C[1] + HEAD_R[1] * uy, HEAD_C[2] + HEAD_R[2] * uz], 1)
            Nn = np.stack([ux / HEAD_R[0], uy / HEAD_R[1], uz / HEAD_R[2]], 1)
            Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
            self.head.append((P.astype(np.float32), Nn.astype(np.float32)))
        self._half_grid = None
        # neighbourhood weights for the deformer: distance from each vertex to each control group
        self._wcache = {}

    # ------------------------------------------------------------------ deformation

    def _w(self, ids, sigma):
        k = (tuple(ids), sigma)
        if k not in self._wcache:
            P = self.V0[ids]
            d2 = ((self.V0[:, None, :2] - P[None, :, :2]) ** 2).sum(-1).min(1)
            self._wcache[k] = np.exp(-0.5 * d2 / sigma ** 2).astype(np.float32)
        return self._wcache[k]

    def deform(self, e: dict) -> np.ndarray:
        V = self.V0.copy()
        x, y = self.V0[:, 0], self.V0[:, 1]
        brow, curve, opn, eyes, wide = e["brow"], e["curve"], e["open"], e["eyes"], e.get("wide", 0.0)
        u = 1.0 / self.half  # one centimetre of the original model

        # brows: raised go up and arch (the inner ends highest, as in fear and compassion); lowered come
        # down and draw in toward the nose (malice, upset)
        wb = self._w(BROW_L + BROW_R, 1.1 * u)
        wi = self._w(BROW_INNER, 0.9 * u)
        V[:, 1] += wb * brow * 0.95 * u + wi * brow * 0.55 * u
        V[:, 0] -= wi * np.sign(x) * min(brow, 0.0) * -0.45 * u
        V[:, 2] += wi * min(brow, 0.0) * -0.25 * u  # the frown's knot: the inner brows push forward

        # lids: the upper lid comes down to meet the lower; wide eyes lift it
        for up, lo in ((LID_UP_L, LID_LO_L), (LID_UP_R, LID_LO_R)):
            wu = self._w(up, 0.35 * u)
            y_lo = self.V0[lo, 1].mean()
            y_up = self.V0[up, 1].mean()
            gap = y_up - y_lo
            shut = 1.0 - eyes
            V[:, 1] -= wu * (shut * gap * 1.05 - wide * 0.35 * u)
            V[:, 2] += wu * shut * 0.12 * u  # the lid rounds over the eyeball

        # mouth corners: up and out for a smile, down for a frown; cheeks ride up with a smile
        wc = self._w(CORNERS, 0.75 * u)
        V[:, 1] += wc * curve * 1.1 * u
        V[:, 0] += wc * np.sign(x) * abs(curve) * 0.35 * u * (1 if curve > 0 else 0.4)
        wch = self._w([205, 425, 50, 280, 187, 411], 1.0 * u)
        V[:, 1] += wch * max(curve, 0.0) * 0.7 * u
        V[:, 2] += wch * max(curve, 0.0) * 0.30 * u

        # the jaw: everything below the mouth line drops and swings back, most at the chin; the lower
        # lip goes with it, so the lips part along the line between them
        y_mouth = float(self.V0[[13, 14], 1].mean())
        y_chin = float(self.V0[CHIN, 1])
        lat = np.clip(1 - (np.abs(x) / 0.62) ** 2, 0, 1).astype(np.float32)
        w_low = smoothstep(y_mouth + 0.004, y_mouth - 0.02, y) * lat
        frac = np.clip((y_mouth - y) / (y_mouth - y_chin), 0, 1)
        V[:, 1] -= w_low * opn * (2.6 + 1.0 * frac) * u
        V[:, 2] -= w_low * opn * (0.4 + 1.0 * frac) * u
        # the corners part less than the middle
        wcn = self._w([61, 291, 78, 308], 0.35 * u)
        V[:, 1] += wcn * w_low * opn * 1.2 * u
        # the upper lip lifts a little
        w_up = smoothstep(y_mouth - 0.004, y_mouth + 0.02, y) * self._w([0, 37, 267, 13, 82, 312, 39, 269], 0.5 * u)
        V[:, 1] += w_up * opn * 0.45 * u
        return V

    # ------------------------------------------------------------------ rendering

    def render(self, g: Grid, cx, cy, s, e: dict, yaw=0.0, pitch=0.0, roll=0.0, feather=0.06, head=True):
        """Render the face centred at (cx, cy), half-height s (normalized units), turned by yaw
        (positive: the face turns toward screen right). Returns a fields dict. Large faces are rendered
        at half resolution and scaled up: they're smooth, and it keeps the point cloud dense enough."""
        if s * g.h > 380 and g.w > 400:
            if self._half_grid is None or self._half_grid.w != g.w // 2:
                self._half_grid = Grid(g.w // 2, g.h // 2)
            f = self._render(self._half_grid, cx, cy, s, e, yaw, pitch, roll, feather, head)
            return _upsample_fields(f, g, cx, cy, s)
        return self._render(g, cx, cy, s, e, yaw, pitch, roll, feather, head)

    def _render(self, g, cx, cy, s, e, yaw, pitch, roll, feather, head):
        V = self.deform(e)
        R = _rot(yaw, pitch, roll)
        Vr = V @ R.T
        # vertex normals
        Fc = self.F
        a, b, c = Vr[Fc[:, 0]], Vr[Fc[:, 1]], Vr[Fc[:, 2]]
        fn = np.cross(b - a, c - a)
        vn = np.zeros_like(Vr)
        for k in range(3):
            np.add.at(vn, Fc[:, k], fn)
        vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9
        # the point level by size on screen
        px_h = s * g.h  # face height in pixels
        lvl = 0 if px_h < 160 else (1 if px_h < 420 else 2)
        n, tri, w = self.levels[lvl]
        # the area each point must cover grows with the face: subsample less when it's small
        P = (Vr[Fc[tri, 0]] * w[:, :1] + Vr[Fc[tri, 1]] * w[:, 1:2] + Vr[Fc[tri, 2]] * w[:, 2:3])
        N_ = (vn[Fc[tri, 0]] * w[:, :1] + vn[Fc[tri, 1]] * w[:, 1:2] + vn[Fc[tri, 2]] * w[:, 2:3])
        depth, nrm, hit = _splat(g, cx, cy, s, P, N_)
        # the skull goes in only where the face isn't, so the two never fight over a pixel
        if head:
            HP, HN = self.head[lvl]
            hd, hn, hh = _splat(g, cx, cy, s, HP @ R.T, HN @ R.T)
            face_hit = hit.copy()
            # the skull wins only where it is clearly nearer (the far side of a turned head) or the
            # face has no point at all; the bias keeps them from fighting where they nearly touch
            use = hh & (~face_hit | (hd > depth + 0.06))
            # decide by neighbourhood, not by pixel, or the two surfaces speckle where they cross
            use = hh & ((blur(use.astype(np.float32), 3) > 0.5) | ~face_hit)
            depth = np.where(use, hd, depth)
            nrm = np.where(use[..., None], hn, nrm)
            hit = hit | use
            inside = blur(hit.astype(np.float32), 3) > 0.45
            for _ in range(4):
                if not (inside & ~hit).any():
                    break
                depth, nrm, hit = _fill(depth, nrm, hit, inside)
            # soften the seam where the face meets the skull
            fm = face_hit.astype(np.float32)
            rs = max(3, int(px_h / 60))
            seam = np.abs(blur(fm, rs) - fm) > 0.02
            nb = blur(nrm, rs)
            nb /= np.linalg.norm(nb, axis=-1, keepdims=True) + 1e-6
            nrm = np.where(seam[..., None], nb, nrm)
            hm = hit.astype(np.float32)
            dzb = blur(np.where(hit, depth, 0) * hm, rs) / (blur(hm, rs) + 1e-6)
            depth = np.where(seam & hit, dzb, depth)
        mask = hit.astype(np.float32)
        depth = np.where(hit, depth, 0.0).astype(np.float32)
        # smooth: the point cloud is piecewise flat; blur depth and normals inside the mask
        r = max(1, int(round(px_h / 300)))
        mb = blur(mask, r) + 1e-6
        depth = np.where(hit, blur(depth * mask, r) / mb, 0.0)
        nrm = blur(nrm * mask[..., None], r) / mb[..., None]
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-6
        nrm[~hit] = (0, 0, 1)
        # the edge dissolves: the mesh stops at the temples and forehead, so fade it out there
        soft = blur(mask, max(1.0, feather * px_h / 2))
        edge = np.clip((soft - 0.5) * 2.0, 0, 1) * mask
        # feature masks from the deformed landmarks
        def poly(ids):
            pts = [(cx + Vr[i, 0] * s, cy + Vr[i, 1] * s) for i in ids]
            return blur(polygon_mask(g, pts), 1)
        eyes_m = np.maximum(poly(EYE_L), poly(EYE_R)) if e["eyes"] > 0.08 else np.zeros_like(mask)
        mouth_m = poly(LIP_IN) if e["open"] > 0.03 else np.zeros_like(mask)
        # irises: discs at the eye centres, clipped by the lids
        iris = np.zeros_like(mask)
        if e["eyes"] > 0.08:
            for ids in (EYE_L, EYE_R):
                ex = cx + Vr[ids, 0].mean() * s
                ey = cy + Vr[ids, 1].mean() * s
                rad = 0.040 * s
                d = np.sqrt((g.x - ex) ** 2 + (g.y - ey) ** 2)
                iris = np.maximum(iris, 1 - smoothstep(rad - g.px, rad + g.px, d))
            iris *= eyes_m
        # depth from just behind the skull's centre plane, 0 at the silhouette, 1 at the nose
        zb = HEAD_C[2] - 0.05
        rel = np.where(hit, np.clip((depth - zb) / (float(Vr[:, 2].max()) - zb + 1e-6), 0, 1), 0.0).astype(np.float32)
        x_local = (g.x - cx) / s
        y_local = (g.y - cy) / s
        return dict(depth=rel, mask=mask, edge=edge, normal=nrm, eyes=eyes_m, iris=iris, mouth=mouth_m,
                    local=(x_local, y_local), px=g.px / s, scale=s, centre=(cx, cy))


def _splat(g, cx, cy, s, P, N_):
    """Points to a depth buffer with normals; the nearest point wins each pixel; gaps closed."""
    sx = cx + P[:, 0] * s
    sy = cy + P[:, 1] * s
    H, W = g.h, g.w
    ix = ((sx / g.aspect + 1) * 0.5 * W).astype(np.int64)
    iy = ((1 - sy) * 0.5 * H).astype(np.int64)
    ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
    ix, iy, z, N_ = ix[ok], iy[ok], P[ok, 2], N_[ok]
    order = np.argsort(z)
    idx = (iy * W + ix)[order]
    depth = np.full(H * W, -np.inf, np.float32)
    nrm = np.zeros((H * W, 3), np.float32)
    depth[idx] = z[order]
    nrm[idx] = N_[order]
    depth = depth.reshape(H, W)
    nrm = nrm.reshape(H, W, 3)
    hit = np.isfinite(depth)
    inside = blur(hit.astype(np.float32), 3) > 0.45
    for _ in range(6):
        if not (inside & ~hit).any():
            break
        depth, nrm, hit = _fill(depth, nrm, hit, inside)
    # stray points from a surface just behind (where the mesh folds away near a silhouette) poke
    # through as specks: replace any pixel that disagrees with its neighbourhood
    m = hit.astype(np.float32)
    dz = np.where(hit, depth, 0.0)
    for _ in range(2):
        mb = blur(m, 2) + 1e-6
        db_ = blur(dz * m, 2) / mb
        nb = blur(nrm * m[..., None], 2) / mb[..., None]
        nb /= np.linalg.norm(nb, axis=-1, keepdims=True) + 1e-6
        bad = hit & (((nrm * nb).sum(-1) < 0.92) | (db_ - dz > 0.02))
        nrm = np.where(bad[..., None], nb, nrm)
        dz = np.where(bad, db_, dz)
    depth = np.where(hit, dz, depth)
    return depth, nrm, hit


def _upsample_fields(f, g, cx, cy, s):
    def up(a):
        a = np.repeat(np.repeat(a, 2, axis=0), 2, axis=1)
        out = np.zeros((g.h, g.w) + a.shape[2:], np.float32)
        out[:min(g.h, a.shape[0]), :min(g.w, a.shape[1])] = a[:g.h, :g.w]
        return blur(out, 1)
    o = {k: up(f[k]) for k in ("depth", "mask", "edge", "eyes", "iris", "mouth")}
    n = up(f["normal"])
    o["normal"] = n / (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-6)
    o["local"] = ((g.x - cx) / s, (g.y - cy) / s)
    o["px"] = g.px / s
    o["scale"] = s
    o["centre"] = (cx, cy)
    return o


def _fill(depth, nrm, hit, inside):
    H, W = depth.shape
    best = np.where(hit, depth, -np.inf)
    bn = nrm.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            d = np.roll(np.roll(depth, dy, 0), dx, 1)
            h = np.roll(np.roll(hit, dy, 0), dx, 1)
            n = np.roll(np.roll(nrm, dy, 0), dx, 1)
            take = (~hit) & h & (d > best)
            best = np.where(take, d, best)
            bn[take] = n[take]
    # only fill holes inside the face, never grow the silhouette
    grow = np.isfinite(best) & (~hit) & inside
    out_hit = hit | grow
    return np.where(out_hit, best, depth), np.where(out_hit[..., None], bn, nrm), out_hit


def _rot(yaw, pitch, roll):
    cy_, sy_ = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cr, sr = np.cos(roll), np.sin(roll)
    Ry = np.array([[cy_, 0, sy_], [0, 1, 0], [-sy_, 0, cy_]], np.float32)
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]], np.float32)
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]], np.float32)
    return Rz @ Ry @ Rx


# ---------------------------------------------------------------------- lighting

def lambert(f, light, wrap=0.0):
    L = np.asarray(light, np.float32)
    L = L / np.linalg.norm(L)
    d = (f["normal"] * L).sum(-1)
    return np.clip((d + wrap) / (1 + wrap), 0, 1)


def cavity(f, radius_px=6):
    """A cheap ambient occlusion: how far a point sits below the blurred surface around it."""
    d = f["depth"]
    m = f["mask"]
    b = blur(d * m, radius_px) / (blur(m, radius_px) + 1e-6)
    return np.clip((b - d) * 12.0, 0, 1) * m


def skin(f, light=(-0.6, 0.45, 0.65), key=0.95, fill=0.12, spec=0.22, eye_dark=0.85, mouth_dark=0.9):
    """A lit face in grey, 0..1: wrapped key light (soft, like skin), a fill, a sheen, the cavities
    darkened, the irises and the mouth's opening dark. Edge already faded."""
    k = lambert(f, light, wrap=0.2)
    fl = lambert(f, (0.6, -0.1, 0.8), wrap=0.5)
    L = np.asarray(light, np.float32) / np.linalg.norm(light)
    # Blinn-ish sheen toward the viewer
    Hh = L + np.array([0, 0, 1], np.float32)
    Hh /= np.linalg.norm(Hh)
    sp = np.clip((f["normal"] * Hh).sum(-1), 0, 1) ** 24
    v = key * k + fill * fl + spec * sp
    v = v * (1 - 0.55 * cavity(f))
    v = v * (1 - eye_dark * f["iris"]) * (1 - 0.35 * f["eyes"] * (1 - f["iris"]))
    v = v * (1 - mouth_dark * f["mouth"])
    return np.clip(v, 0, 1.2) * f["edge"]
