"""Shared helpers for the Opening animatic: grids, noise, shapes, compositing.

Everything works in normalized coordinates: x runs -A..A (A = aspect ratio),
y runs -1..1 with +y up, so the same code renders at any resolution.
All images are float32 arrays H x W x 3 in 0..1 (linear-ish; we don't gamma-correct).
"""
from __future__ import annotations

import numpy as np

FPS = 24
DURATION = 290.0  # 4:50

_rng_master = np.random.default_rng(20261008)


def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


# ---------------------------------------------------------------- grids

class Grid:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.aspect = w / h
        xs = (np.arange(w, dtype=np.float32) + 0.5) / w * 2 - 1
        ys = 1 - (np.arange(h, dtype=np.float32) + 0.5) / h * 2
        self.x, self.y = np.meshgrid(xs * self.aspect, ys)  # H x W
        self.r = np.sqrt(self.x ** 2 + self.y ** 2)
        self.theta = np.arctan2(self.y, self.x)
        self.px = 2.0 / h  # size of one pixel in normalized units

    def blank(self, v=0.0):
        out = np.empty((self.h, self.w, 3), np.float32)
        out[...] = v
        return out


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def sstep(e0, e1, x):
    """Scalar smoothstep."""
    t = min(max((x - e0) / (e1 - e0 + 1e-9), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp01(a):
    return np.clip(a, 0.0, 1.0)


def ease_in_out(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- noise

class ValueNoise:
    """Tileable value noise from a random lattice, sampled bilinearly. Cheap and smooth enough."""

    def __init__(self, seed: int, size: int = 256):
        self.size = size
        self.table = rng(seed).random((size, size), dtype=np.float32)

    def sample(self, u, v):
        """u, v arrays in lattice units (1 lattice cell = 1.0). Returns 0..1."""
        s = self.size
        u = np.asarray(u, np.float32)
        v = np.asarray(v, np.float32)
        iu = np.floor(u)
        iv = np.floor(v)
        fu = u - iu
        fv = v - iv
        fu = fu * fu * (3 - 2 * fu)
        fv = fv * fv * (3 - 2 * fv)
        iu = iu.astype(np.int64) % s
        iv = iv.astype(np.int64) % s
        iu1 = (iu + 1) % s
        iv1 = (iv + 1) % s
        t = self.table
        a = t[iv, iu]
        b = t[iv, iu1]
        c = t[iv1, iu]
        d = t[iv1, iu1]
        return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv

    def fbm(self, u, v, octaves=4, lac=2.0, gain=0.5):
        amp, tot, norm = 1.0, 0.0, 0.0
        for i in range(octaves):
            tot = tot + amp * self.sample(u * (lac ** i) + 17.3 * i, v * (lac ** i) - 9.1 * i)
            norm += amp
            amp *= gain
        return tot / norm


class Noise3:
    """Time-varying noise: two 2D noise layers crossfaded per integer time step, with a new random
    pair per step (deterministic by step index)."""

    def __init__(self, seed: int, size: int = 128):
        self.seed = seed
        self.size = size
        self._cache = {}

    def _layer(self, k: int):
        if k not in self._cache:
            self._cache[k] = ValueNoise(self.seed * 7919 + k, self.size)
            if len(self._cache) > 8:
                oldest = min(self._cache)
                if oldest != k:
                    del self._cache[oldest]
        return self._cache[k]

    def sample(self, u, v, t, octaves=3):
        k = int(np.floor(t))
        f = t - k
        f = f * f * (3 - 2 * f)
        a = self._layer(k).fbm(u, v, octaves)
        b = self._layer(k + 1).fbm(u, v, octaves)
        return a * (1 - f) + b * f


def curl_field(noise: ValueNoise, x, y, scale=1.5, eps=0.01, t=0.0):
    """Divergence-free 2D flow (eddies) from the curl of a scalar noise potential."""
    u = x * scale + t
    v = y * scale - 0.7 * t
    n_up = noise.fbm(u, v + eps, 3)
    n_dn = noise.fbm(u, v - eps, 3)
    n_rt = noise.fbm(u + eps, v, 3)
    n_lf = noise.fbm(u - eps, v, 3)
    vx = (n_up - n_dn) / (2 * eps)
    vy = -(n_rt - n_lf) / (2 * eps)
    return vx, vy


def worley(points: np.ndarray, x, y):
    """Distances to the nearest and second-nearest feature points (brute force; points <= ~200)."""
    f1 = np.full(x.shape, 1e9, np.float32)
    f2 = np.full(x.shape, 1e9, np.float32)
    for px, py in points:
        d = (x - px) ** 2 + (y - py) ** 2
        closer = d < f1
        f2 = np.where(closer, f1, np.minimum(f2, d))
        f1 = np.where(closer, d, f1)
    return np.sqrt(f1), np.sqrt(f2)


# ---------------------------------------------------------------- static

class Static:
    """Black-and-white static that can flow. A large binary texture, sampled with a flow map:
    two layers advected along a velocity field and crossfaded so the motion never resets visibly."""

    def __init__(self, seed: int, size: int = 1024, grain: float = 1.0):
        r = rng(seed)
        self.size = size
        tex = r.random((size, size), dtype=np.float32)
        self.tex = tex
        self.grain = grain

    def sample(self, u, v):
        s = self.size
        iu = np.floor(u).astype(np.int64) % s
        iv = np.floor(v).astype(np.int64) % s
        return self.tex[iv, iu]

    def render(self, g: Grid, vx, vy, t, period=1.6, scale=None, sparkle=0.08, seed_t=0):
        """vx, vy: velocity in normalized units per second (arrays or scalars)."""
        if scale is None:
            scale = g.h / 2 * self.grain  # one texel ~ one pixel
        base_u = (g.x + g.aspect) * scale
        base_v = (1 - g.y) * scale
        out = np.zeros(g.x.shape, np.float32)
        for k in range(2):
            ph = ((t / period) + k * 0.5) % 1.0
            w = 1 - abs(ph * 2 - 1)  # triangle crossfade
            dt = (ph - 0.5) * period
            u = base_u - vx * dt * scale + k * 311.7
            v = base_v + vy * dt * scale + k * 127.3
            out += w * self.sample(u, v)
        # temporal sparkle: random flips so a paused frame still reads as static
        if sparkle > 0:
            r = rng(int(seed_t * 1000) + 7)
            flip = r.random(out.shape, dtype=np.float32) < sparkle
            out = np.where(flip, 1 - out, out)
        return out


# ---------------------------------------------------------------- shapes

def disc(g: Grid, cx, cy, radius, soft=None):
    if soft is None:
        soft = g.px * 1.5
    d = np.sqrt((g.x - cx) ** 2 + (g.y - cy) ** 2)
    return 1 - smoothstep(radius - soft, radius + soft, d)


def ellipse(g: Grid, cx, cy, rx, ry, soft=None, rot=0.0):
    if soft is None:
        soft = g.px * 1.5
    dx = g.x - cx
    dy = g.y - cy
    if rot:
        c, s = np.cos(rot), np.sin(rot)
        dx, dy = c * dx + s * dy, -s * dx + c * dy
    d = np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
    return 1 - smoothstep(1 - soft / min(rx, ry), 1 + soft / min(rx, ry), d)


def gauss(g: Grid, cx, cy, sx, sy, rot=0.0):
    dx = g.x - cx
    dy = g.y - cy
    if rot:
        c, s = np.cos(rot), np.sin(rot)
        dx, dy = c * dx + s * dy, -s * dx + c * dy
    return np.exp(-0.5 * ((dx / sx) ** 2 + (dy / sy) ** 2))


def line_mask(g: Grid, x0, y0, x1, y1, width, soft=None):
    if soft is None:
        soft = g.px
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy + 1e-9
    t = np.clip(((g.x - x0) * dx + (g.y - y0) * dy) / L2, 0, 1)
    px = x0 + t * dx
    py = y0 + t * dy
    d = np.sqrt((g.x - px) ** 2 + (g.y - py) ** 2)
    return 1 - smoothstep(width - soft, width + soft, d)


def polygon_mask(g: Grid, pts):
    """Even-odd fill of a polygon given as list of (x, y). Vectorized ray casting."""
    inside = np.zeros(g.x.shape, bool)
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cond = (g.y > min(y0, y1)) & (g.y <= max(y0, y1))
        if y1 == y0:
            continue
        xint = x0 + (g.y - y0) * (x1 - x0) / (y1 - y0)
        inside ^= cond & (g.x < xint)
    return inside.astype(np.float32)


def soft_poly(g: Grid, pts, blur_px=1.0):
    m = polygon_mask(g, pts)
    return blur(m, blur_px)


def blur(img, radius_px: float):
    """Separable box-ish blur via cumulative sums (repeated twice for smoothness)."""
    r = int(max(1, round(radius_px)))
    if r <= 0:
        return img
    out = img
    for _ in range(2):
        out = _box(out, r, axis=0)
        out = _box(out, r, axis=1)
    return out


def _box(a, r, axis):
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    ap = np.pad(a, pad, mode="edge")
    c = np.cumsum(ap, axis=axis, dtype=np.float32)
    n = a.shape[axis]
    sl_hi = [slice(None)] * a.ndim
    sl_lo = [slice(None)] * a.ndim
    sl_hi[axis] = slice(2 * r + 1, 2 * r + 1 + n)
    sl_lo[axis] = slice(0, n)
    zero = np.zeros_like(np.take(c, [0], axis=axis))
    c = np.concatenate([zero, c], axis=axis)
    return (c[tuple(sl_hi)] - c[tuple(sl_lo)]) / (2 * r + 1)


# ---------------------------------------------------------------- color

def hsv(h, s, v):
    """Vectorized HSV->RGB. h in 0..1 (wraps), s, v arrays or scalars. Returns ...x3."""
    h = np.asarray(h, np.float32) % 1.0
    s = np.asarray(s, np.float32)
    v = np.asarray(v, np.float32)
    i = np.floor(h * 6).astype(np.int64) % 6
    f = h * 6 - np.floor(h * 6)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [v, q, p, p, t, v])
    gg = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [t, v, v, q, p, p])
    b = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [p, p, t, v, v, q])
    return np.stack([r, gg, b], axis=-1).astype(np.float32)


def rgb(r, g, b):
    return np.array([r, g, b], np.float32)


def over(dst, mask, color):
    """Composite a flat color over dst with mask (H x W)."""
    m = mask[..., None]
    return dst * (1 - m) + np.asarray(color, np.float32) * m


def over_img(dst, mask, src):
    m = mask[..., None]
    return dst * (1 - m) + src * m


def gray(mask):
    return np.repeat(mask[..., None], 3, axis=-1)


def add(dst, mask, color):
    return dst + mask[..., None] * np.asarray(color, np.float32)


def vignette(g: Grid, strength=0.35, power=2.0):
    return 1 - strength * np.clip(g.r / (g.aspect + 0.2), 0, 1) ** power


def to_uint8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def points_layer(g: Grid, xs, ys, sizes, colors, intensities=None, soft=1.0):
    """Draw many soft discs additively. xs, ys in normalized coords; sizes in normalized units.
    Uses a coarse bucketed approach: a gaussian splat drawn per point onto the frame (loop over
    points, but each splat is a small window)."""
    out = np.zeros((g.h, g.w, 3), np.float32)
    if intensities is None:
        intensities = np.ones(len(xs), np.float32)
    H, W = g.h, g.w
    sx = W / (2 * g.aspect)
    for px, py, sz, col, it in zip(xs, ys, sizes, colors, intensities):
        if it <= 0 or sz <= 0:
            continue
        cx = (px / g.aspect + 1) * 0.5 * W
        cy = (1 - py) * 0.5 * H
        rad = max(1.0, sz * sx)
        R = int(rad * 3) + 1
        x0, x1 = int(cx) - R, int(cx) + R + 1
        y0, y1 = int(cy) - R, int(cy) + R + 1
        if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H:
            continue
        xa, xb = max(x0, 0), min(x1, W)
        ya, yb = max(y0, 0), min(y1, H)
        yy, xx = np.mgrid[ya:yb, xa:xb]
        d2 = ((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2) / (rad * rad * soft)
        splat = np.exp(-d2 * 2.0) * it
        out[ya:yb, xa:xb] += splat[..., None] * np.asarray(col, np.float32)
    return out
