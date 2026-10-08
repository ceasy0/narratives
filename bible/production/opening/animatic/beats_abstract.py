"""Beats 1-9 of the Opening: the static, the faces, the alternation, the particle sea, the proton,
the web, the stars, and the photon's crossing. Every function takes global time t (seconds) and
returns an H x W x 3 float32 image. Everything is a pure function of t, so frames can be rendered
in any order and in parallel.

Timings follow treatment v3.1 §2 exactly.
"""
from __future__ import annotations

import numpy as np

from common import (Grid, Static, ValueNoise, Noise3, curl_field, worley, smoothstep, sstep, lerp,
                    ease_in_out, disc, gauss, blur, hsv, gray, over, over_img, add, rng, clamp01)
import face as F

# beat boundaries (seconds)
B = dict(deep=0.0, light=28.0, sep=36.0, eve=58.0, vault=74.0, land=94.0, earth=112.0,
         lights=122.0, cross=142.0, swarm=156.0, landbeat=188.0, dust=212.0, fill=230.0, rest=266.0, end=290.0)

SMALL = 0.55   # half-height of the small face
LARGE = 2.0    # half-height of the large face


class Ctx:
    """Per-process cache of noise tables and precomputed particle events."""

    def __init__(self, g: Grid):
        self.g = g
        self.static = Static(1, size=1024)
        self.flow = ValueNoise(2, 256)
        self.n3 = Noise3(3, 128)
        self.n3b = Noise3(4, 128)
        self.vn = ValueNoise(5, 256)
        self.vn2 = ValueNoise(6, 256)
        self.pairs = make_pair_events(20261008)
        self.protons = make_protons(77)
        self.web_pts = make_web_points(91)
        self._face_cache = {}

    def face(self, cx, cy, s, e, key=None):
        """Cache faces by quantized parameters so repeated frames don't rebuild identical depth maps."""
        k = (round(cx, 3), round(cy, 3), round(s, 4)) + tuple(round(e[n], 3) for n in ("brow", "curve", "open", "eyes", "wide"))
        f = self._face_cache.get(k)
        if f is None:
            f = F.face_fields(self.g, cx, cy, s, e)
            if len(self._face_cache) > 6:
                self._face_cache.clear()
            self._face_cache[k] = f
        return f


# ----------------------------------------------------------------------------- beat 1: the deep

def up4(a, g):
    out = np.repeat(np.repeat(a, 4, axis=0), 4, axis=1)[:g.h, :g.w]
    if out.shape != (g.h, g.w):
        pad = np.zeros((g.h, g.w), np.float32)
        pad[:out.shape[0], :out.shape[1]] = out
        out = pad
    return blur(out, 3)


def face_strength(t):
    """How clearly the face stands out of the static, 0..1."""
    return sstep(5.0, 17.0, t)


def flow_amp(t):
    return 0.30 * sstep(3.0, 10.0, t)


def beat_deep(c: Ctx, t):
    g = c.g
    amp = flow_amp(t)
    vx, vy = curl_field(c.flow, g.x[::4, ::4], g.y[::4, ::4], scale=1.3, eps=0.02, t=0.03 * t)
    vx = up4(vx, g) * amp * 0.06
    vy = up4(vy, g) * amp * 0.06
    # the face: the static inside it flows differently (turned and slowed), nothing else marks it
    fs = face_strength(t)
    if fs > 0:
        f = c.face(0.0, 0.0, SMALL, F.NEUTRAL_CLOSED)
        inside = f["mask"] * fs
        # inside the face the current runs along the contours of the depth, slowly
        gy, gx = np.gradient(f["depth"])
        gl = np.sqrt(gx * gx + gy * gy) + 1e-6
        tx, ty = -gy / gl, -gx / gl  # tangent to the contour
        vin_x = tx * amp * 0.035 + vx * 0.2
        vin_y = ty * amp * 0.035 + vy * 0.2
        vx = vx * (1 - inside) + vin_x * inside
        vy = vy * (1 - inside) + vin_y * inside
        sparkle = 0.10 * (1 - 0.6 * inside)
    else:
        sparkle = 0.10
    s = c.static.render(g, vx, vy, t, period=1.4, sparkle=0.0, seed_t=t)
    r = rng(int(t * 1000) + 11)
    flip = r.random(s.shape, dtype=np.float32) < sparkle
    s = np.where(flip, 1 - s, s)
    if fs > 0:
        # a faint contrast cue inside the face so it survives video compression in the animatic.
        # The final build should drop this once the motion cue alone is tested at full quality.
        s = s * (1 - 0.30 * inside) + 0.5 * 0.30 * inside
    img = gray(s)
    return img


# ----------------------------------------------------------------------------- beat 2: light

def beat_light(c: Ctx, t):
    g = c.g
    tl = t - B["light"]
    img = g.blank(0.0)
    f = c.face(0.0, 0.0, SMALL, F.NEUTRAL_CLOSED)
    if tl < 0.21:
        # the blast: four frames. 0: the static as a sheet over the face, every contour shown.
        # 1-3: whipped outward and behind the head, taking the dark with it; the face left white.
        k = tl / 0.21
        sh = F.shade(f, light=(0.1, 0.4, 0.9), ambient=0.15, strength=1.6)
        if k < 0.25:
            vx = vy = 0.0
            s = c.static.render(g, vx, vy, t, sparkle=0.0, seed_t=t)
            sheet = s * (0.35 + 0.65 * sh) * f["mask"] + s * (1 - f["mask"])
            return gray(sheet)
        # the whip: the field is blasted away from us, into the picture. The texture contracts toward
        # the head and the outer edge of the static comes in after it, shutting behind the head and
        # taking the dark with it. The face left behind is white.
        push = (k - 0.25) / 0.75
        scale = g.h / 2
        shrink = 1 - 0.7 * push
        u = (g.x * shrink + g.aspect) * scale
        v = (1 - g.y * shrink) * scale
        s = c.static.sample(u, v)
        d = np.sqrt((g.x / (SMALL * 0.78)) ** 2 + (g.y / SMALL) ** 2)
        outer = 1.0 + (1 - push) ** 1.5 * 4.5
        band = smoothstep(0.95, 1.05, d) * (1 - smoothstep(outer - 0.25, outer + 0.05, d))
        white = F.white_face(f, g, modeling=0.25)
        out = s * band + white * (0.3 + 0.7 * push)
        return gray(np.clip(out, 0, 1))
    # black, silence, the white face alone, eyes closed; then the eyes open and the large face forms
    k = sstep(6.5, 7.3, tl)  # 34.5 - 35.3
    e = F.mix_expr(F.NEUTRAL_CLOSED, F.NEUTRAL_OPEN, k)
    if k > 0:
        # the second face forms in the same instant, on both sides
        big = c.face(0.0, 0.0, LARGE, F.MALICE)
        img += gray(F.black_face(big, g, edge=0.16 * k))
    f2 = c.face(0.0, 0.0, SMALL, e)
    w = F.white_face(f2, g)
    img = over_img(img, f2["mask"], gray(w))
    return img


# ----------------------------------------------------------------------------- beat 3: the separation

def beat_sep(c: Ctx, t):
    g = c.g
    ts = t - B["sep"]
    if ts < 12.5:
        # the climb: fear to terror, malice to laughter. The dark face comes for the white one from 11 s.
        k = ease_in_out(ts / 11.0)
        es = F.mix_expr(F.FEAR, F.TERROR, k)
        eb = F.mix_expr(F.MALICE, F.LAUGH, k)
        # laughter: the large face pulses with the hiss from 6 s
        pulse = 0.0
        if ts > 6:
            pulse = 0.02 * (sstep(6, 9, ts)) * max(0.0, np.sin(ts * 2 * np.pi * 4.5)) ** 2
        reach = sstep(11.0, 12.5, ts)
        sL = LARGE * (1 + pulse) * (1 - 0.55 * reach)
        img = g.blank(0.0)
        big = c.face(0.0, -0.05 * reach, sL, eb)
        img += gray(F.black_face(big, g, edge=0.16 + 0.06 * k))
        small = c.face(0.0, 0.0, SMALL, es)
        w = F.white_face(small, g)
        # terror: a tremor
        img = over_img(img, small["mask"], gray(w))
        return img
    # the turn-over: ground white, the small face dark and upset, the large face white and compassionate
    tt = ts - 12.5
    k = ease_in_out(tt / 7.5)  # settle over 7.5 s
    es = F.mix_expr(F.UPSET, F.PEACE, k)
    eb = F.mix_expr(F.COMPASSION, F.PEACE, k)
    # eyes close at the end
    kz = sstep(7.0, 9.5, tt)
    es = F.mix_expr(es, F.SLEEP, kz)
    eb = F.mix_expr(eb, F.SLEEP, kz)
    img = g.blank(1.0)
    big = c.face(0.0, -0.03, LARGE * (1 - 0.1 * k), eb)
    img = gray(F.white_on_white(big, g, edge=0.18))
    small = c.face(0.0, 0.0, SMALL, es)
    d = dark_face(small, g)
    img = over_img(img, small["mask"], gray(d))
    return img


def dark_face(fields, g, edge=0.22):
    """The small face gone dark on a white ground: black with faint grey in the creases."""
    sh = F.shade(fields, light=(0.3, 0.6, 0.75), ambient=0.0, strength=1.5)
    rim = np.clip(1 - sh, 0, 1) ** 2
    v = edge * np.maximum(fields["crease"], 0.9 * rim) * fields["mask"]
    v += edge * 0.9 * fields["eyes"] + edge * 0.6 * fields["mouth"]
    return np.clip(v, 0, 1)


# ----------------------------------------------------------------------------- beat 4: evening and morning

_FLIP_A, _FLIP_R = 2.0, 0.72  # first interval and ratio; the intervals converge at a/(1-r) = 7.14 s


def flip_count(tau):
    """Number of turn-overs completed by local time tau (array ok). Whole-frame while the count is
    below 3; after that the per-pixel offsets in beat_eve take over."""
    tau = np.asarray(tau, np.float32)
    lim = _FLIP_A / (1 - _FLIP_R)
    x = 1 - np.clip(tau, 0, lim - 1e-4) * (1 - _FLIP_R) / _FLIP_A
    n = np.log(x) / np.log(_FLIP_R)
    return np.floor(n).astype(np.int64), n


def beat_eve(c: Ctx, t):
    g = c.g
    te = t - B["eve"]
    # the ground: dark/light with the count of flips. First three flips take the whole frame.
    n_frame, n_cont = flip_count(te)
    n_frame = int(n_frame)
    spread = sstep(3.2, 7.2, te)  # the change starts spreading at about the fourth turn
    # organic per-pixel offset: fbm at a scale that keeps breaking smaller
    scale = 1.5 * (2.0 ** (spread * 5.0))
    off = c.vn.fbm(g.x * scale + 3.1, g.y * scale - 1.7, octaves=4)
    off2 = c.vn2.fbm(g.x * scale * 2.3 + 9.1, g.y * scale * 2.3 + 4.7, octaves=3)
    offset = (off - 0.5) * 1.6 * spread + (off2 - 0.5) * 0.6 * spread
    tau_px = te - offset
    npx, ncont_px = flip_count(tau_px)
    # beyond the convergence the grains turn on their own beats, too fast to follow: the frame shimmers
    grain = sstep(6.0, 8.5, te)
    gseed = c.vn.sample(g.x * 220 + 7.0, g.y * 220 + 2.0)  # a per-grain phase
    r = rng(int(te * 24) + 101)
    fast = (r.random(g.x.shape, dtype=np.float32) < 0.5).astype(np.float32)
    state = (npx % 2).astype(np.float32)
    state = state * (1 - grain) + fast * grain
    # whole-frame for the first turns
    state = np.where(spread <= 0.0, float(n_frame % 2), state)
    ground = state  # 0 = dark, 1 = light
    # the first color: where two grains meet, a flash whose hue is the local phase
    edges = np.abs(np.diff(ground, axis=1, prepend=ground[:, :1])) + np.abs(np.diff(ground, axis=0, prepend=ground[:1, :]))
    edges = np.clip(edges, 0, 1)
    color_amt = sstep(9.0, 15.5, te) * 0.9
    hue = (gseed * 3.0 + te * 0.05) % 1.0
    col = hsv(hue, 0.9, 1.0)
    img = gray(ground)
    img = img * (1 - (edges * color_amt)[..., None]) + col * (edges * color_amt)[..., None]

    # the faces: they turn with the ground, quicker each time, then blur into one grey grain
    blur_amt = sstep(5.0, 9.0, te)
    shrink = sstep(9.0, 15.0, te)
    face_s = SMALL * (1 - shrink) + 0.012 * shrink
    if blur_amt < 1.0 or shrink < 1.0:
        light_phase = n_frame % 2 == 1 if spread <= 0 else None
        # in each dark phase the small face is white and afraid, the large laughs; in each light phase
        # the small face is dark and upset, the large tends it. Progress within the phase:
        frac = float(n_cont - np.floor(n_cont)) if np.isfinite(n_cont) else 0.5
        if light_phase is None:
            # once the ground has broken up, the faces hold every expression at once
            es = F.mix_expr(F.mix_expr(F.TERROR, F.SLEEP, 0.5), F.NEUTRAL_CLOSED, 0.3)
            eb = F.mix_expr(F.LAUGH, F.COMPASSION, 0.5)
            dark_ground = 0.5
        elif not light_phase:
            es = F.mix_expr(F.FEAR, F.TERROR, frac)
            eb = F.mix_expr(F.MALICE, F.LAUGH, frac)
            dark_ground = 1.0
        else:
            es = F.mix_expr(F.UPSET, F.SLEEP, frac)
            eb = F.mix_expr(F.COMPASSION, F.SLEEP, frac)
            dark_ground = 0.0
        if shrink < 0.99:
            big = c.face(0.0, 0.0, LARGE * (1 - 0.85 * shrink), eb)
            fade = (1 - blur_amt) * (1 - shrink)
            if fade > 0.01:
                if dark_ground >= 0.5:
                    img = img + gray(F.black_face(big, g, edge=0.18)) * fade
                else:
                    img = img - gray(1 - F.white_on_white(big, g, edge=0.18)) * fade
            small = c.face(0.0, 0.0, face_s, es)
            if dark_ground >= 0.5:
                sv = F.white_face(small, g) * (1 - blur_amt) + 0.5 * blur_amt
            else:
                sv = dark_face(small, g) * (1 - blur_amt) + 0.5 * blur_amt
            svimg = gray(sv)
            if blur_amt > 0:
                svimg = blur(svimg, 1 + 18 * blur_amt * g.h / 540)
                m = blur(small["mask"], 1 + 18 * blur_amt * g.h / 540)
            else:
                m = small["mask"]
            img = over_img(img, np.clip(m, 0, 1), svimg)
    # the one grain we stay on
    if shrink > 0.3:
        gm = disc(g, 0.0, 0.0, 0.012, soft=g.px * 2)
        img = over(img, gm * sstep(0.3, 0.8, shrink), (0.55, 0.55, 0.55))
    return np.clip(img, 0, 1)


# ----------------------------------------------------------------------------- beat 5: the vault

def make_pair_events(seed, n=48000, t0=B["vault"], t1=B["land"] + 4.0):
    r = rng(seed)
    birth = r.uniform(t0 - 1.0, t1, n).astype(np.float32)
    life = r.uniform(0.25, 1.4, n).astype(np.float32)
    x = r.uniform(-3.5, 3.5, n).astype(np.float32)
    y = r.uniform(-2.2, 2.2, n).astype(np.float32)
    z = r.uniform(0.6, 5.0, n).astype(np.float32)
    ang = r.uniform(0, 2 * np.pi, n).astype(np.float32)
    hue = r.random(n, dtype=np.float32)
    amp = r.uniform(0.05, 0.3, n).astype(np.float32)
    order = np.argsort(birth)
    return dict(birth=birth[order], life=life[order], x=x[order], y=y[order], z=z[order],
                ang=ang[order], hue=hue[order], amp=amp[order])


def make_protons(seed, n=1400):
    r = rng(seed)
    return dict(x=r.uniform(-3.5, 3.5, n).astype(np.float32), y=r.uniform(-2.2, 2.2, n).astype(np.float32),
                z=r.uniform(0.7, 5.0, n).astype(np.float32), ph=r.uniform(0, 2 * np.pi, n).astype(np.float32),
                hue=r.random(n, dtype=np.float32))


def make_web_points(seed, n=70):
    r = rng(seed)
    pts = np.stack([r.uniform(-2.4, 2.4, n), r.uniform(-1.5, 1.5, n)], axis=1).astype(np.float32)
    ignite = np.sort(r.uniform(0, 7.0, n)).astype(np.float32)
    r.shuffle(ignite)
    burst = r.random(n) < 0.3
    burst_t = r.uniform(3.0, 9.0, n).astype(np.float32)
    return dict(pts=pts, ignite=ignite, burst=burst, burst_t=burst_t)


def splat(g: Grid, xs, ys, cols, intens, radius_px, glow_px=0.0):
    """Rasterize points additively, then blur to soft discs. cols: N x 3."""
    H, W = g.h, g.w
    px = ((xs / g.aspect + 1) * 0.5 * W).astype(np.int64)
    py = ((1 - ys) * 0.5 * H).astype(np.int64)
    ok = (px >= 0) & (px < W) & (py >= 0) & (py < H) & (intens > 0)
    acc = np.zeros((H, W, 3), np.float32)
    if ok.any():
        np.add.at(acc, (py[ok], px[ok]), cols[ok] * intens[ok][:, None])
    r = max(1, int(radius_px))
    comp = (2 * r / (2 * r + 1)) ** 4  # keeps the gain the beats were tuned with
    out = blur(acc, r) * (2 * r + 1) ** 2 * 0.35 * comp
    if glow_px > 0:
        gr = max(1, int(glow_px))
        compg = (2 * gr / (2 * gr + 1)) ** 4
        out = out + blur(acc, gr) * (2 * gr + 1) ** 2 * 0.12 * compg
    return out


def project(x, y, z, cam_z, g: Grid, fov=1.0):
    d = z - cam_z
    ok = d > 0.15
    d = np.where(ok, d, 1.0)
    return x / d * fov, y / d * fov, d, ok


def warp_positions(c: Ctx, x, y, t, amount):
    """Domain warp so the sea folds and streams."""
    wx = c.n3.sample(x * 0.6 + 2.0, y * 0.6, t * 0.5, octaves=2) - 0.5
    wy = c.n3b.sample(x * 0.6 - 3.0, y * 0.6 + 1.0, t * 0.5, octaves=2) - 0.5
    return x + wx * amount, y + wy * amount


def our_particle_pos(c: Ctx, t):
    """Restless: darts and doubles back around the centre."""
    tv = t - B["vault"]
    px = (c.n3.sample(np.array([tv * 1.7]), np.array([0.3]), 0.0, octaves=2)[0] - 0.5) * 0.5
    py = (c.n3b.sample(np.array([tv * 1.7 + 5]), np.array([0.8]), 0.0, octaves=2)[0] - 0.5) * 0.35
    return float(px), float(py)


def sea_layer(c: Ctx, t, cam_z, pair_gain=1.0, warp=0.9, glare=1.0):
    """The pair sea: grains appearing in pairs and vanishing in pairs, every flash a color."""
    g = c.g
    P = c.pairs
    lo = np.searchsorted(P["birth"], t - 1.5)
    hi = np.searchsorted(P["birth"], t)
    if hi <= lo:
        return np.zeros((g.h, g.w, 3), np.float32)
    b = P["birth"][lo:hi]
    L = P["life"][lo:hi]
    tau = (t - b) / L
    alive = (tau > 0) & (tau < 1)
    if not alive.any():
        return np.zeros((g.h, g.w, 3), np.float32)
    tau = tau[alive]
    x = P["x"][lo:hi][alive]
    y = P["y"][lo:hi][alive]
    z = (P["z"][lo:hi][alive] + cam_z)  # the sea moves with the camera so it's endless
    ang = P["ang"][lo:hi][alive]
    hue = P["hue"][lo:hi][alive]
    amp = P["amp"][lo:hi][alive]
    sep = np.sin(np.pi * tau) * amp
    bright = np.sin(np.pi * tau) ** 0.7
    xs = np.concatenate([x + np.cos(ang) * sep, x - np.cos(ang) * sep])
    ys = np.concatenate([y + np.sin(ang) * sep, y - np.sin(ang) * sep])
    zs = np.concatenate([z, z])
    hues = np.concatenate([hue, (hue + 0.5) % 1.0])
    br = np.concatenate([bright, bright])
    xs, ys = warp_positions(c, xs, ys, t, warp)
    sx, sy, d, ok = project(xs, ys, zs, cam_z, g)
    cols = hsv(hues, 0.85, 1.0)
    inten = br * ok / (d ** 1.2) * pair_gain
    near = d < 1.6
    out = splat(g, sx[near], sy[near], cols[near], inten[near] * 0.9, radius_px=4 * g.h / 540, glow_px=18 * g.h / 540 * glare)
    out += splat(g, sx[~near], sy[~near], cols[~near], inten[~near], radius_px=1.5 * g.h / 540, glow_px=6 * g.h / 540 * glare)
    return out


def beat_vault(c: Ctx, t):
    g = c.g
    tv = t - B["vault"]
    cam_z = tv * 0.35
    opening = sstep(0.0, 4.0, tv)  # the picture gains depth
    img = sea_layer(c, t, cam_z, pair_gain=2.6, warp=0.9, glare=1.3)
    # before the opening the grains are flat: fade from the beat-4 shimmer
    if opening < 1:
        r = rng(int(t * 24) + 55)
        flat = (r.random(g.x.shape, dtype=np.float32) < 0.5).astype(np.float32)
        gseed = c.vn.sample(g.x * 220 + 7.0, g.y * 220 + 2.0)
        edges = np.abs(np.diff(flat, axis=1, prepend=flat[:, :1]))
        col = hsv((gseed * 3.0 + t * 0.05) % 1.0, 0.9, 1.0)
        flat_img = gray(flat) * 0.9 * (1 - edges[..., None]) + col * edges[..., None]
        img = flat_img * (1 - opening) + img * opening
    # our particle: steady, bright, centre frame, restless
    px, py = our_particle_pos(c, t)
    img += gray(gauss(g, px, py, 0.035, 0.035)) * 1.4 + gray(gauss(g, px, py, 0.12, 0.12)) * 0.25
    return np.clip(img, 0, 1.2)


# ----------------------------------------------------------------------------- beat 6: land and seas

def proton_layer(c: Ctx, t, cam_z, lock, electron, gas, bright=1.0):
    """The surround as protons: triplets locking, then atoms, then a thinning sea."""
    g = c.g
    P = c.protons
    x, y, z = P["x"], P["y"], P["z"] + cam_z
    ph = P["ph"]
    hue = P["hue"]
    x, y = warp_positions(c, x, y, t, 0.5)
    orbit = 0.06 * (1 - 0.6 * lock)  # the three circle fast and settle
    w = 14.0
    pts_x, pts_y, pts_z, pts_c, pts_i = [], [], [], [], []
    base_cols = hsv(hue, 0.7, 1.0)
    for k in range(3):
        a = ph + t * w * (1 - 0.9 * lock) + k * 2 * np.pi / 3
        # settle two above and one below
        sx_ = np.where(k == 2, 0.0, np.where(k == 0, -0.5, 0.5)) * orbit * 1.4
        sy_ = np.where(k == 2, -0.5, 0.45) * orbit * 1.4
        ox = np.cos(a) * orbit * (1 - lock) + sx_ * lock
        oy = np.sin(a) * orbit * (1 - lock) + sy_ * lock
        pts_x.append(x + ox)
        pts_y.append(y + oy)
        pts_z.append(z)
        pts_c.append(base_cols)
        pts_i.append(np.ones_like(x) * bright)
    if electron > 0:
        a = ph * 3 + t * 9.0
        rr = 0.16
        pts_x.append(x + np.cos(a) * rr)
        pts_y.append(y + np.sin(a) * rr)
        pts_z.append(z)
        pts_c.append(np.tile(np.array([[0.7, 0.85, 1.0]], np.float32), (len(x), 1)))
        pts_i.append(np.ones_like(x) * 0.6 * electron)
    xs = np.concatenate(pts_x)
    ys = np.concatenate(pts_y)
    zs = np.concatenate(pts_z)
    cols = np.concatenate(pts_c)
    inten = np.concatenate(pts_i)
    sx, sy, d, ok = project(xs, ys, zs, cam_z, g)
    inten = inten * ok / (d ** 1.1)
    near = d < 1.8
    out = splat(g, sx[near], sy[near], cols[near], inten[near] * 0.8, radius_px=3 * g.h / 540, glow_px=10 * g.h / 540 * (1 - gas))
    out += splat(g, sx[~near], sy[~near], cols[~near], inten[~near] * 0.9, radius_px=1.2 * g.h / 540, glow_px=4 * g.h / 540 * (1 - gas))
    return out


def gas_layer(c: Ctx, t, amount, warm=0.0):
    g = c.g
    n = c.n3.sample(g.x * 1.2 + 1.0, g.y * 1.2, t * 0.08, octaves=4)
    v = (0.10 + 0.14 * n) * amount
    col = np.array([1.0, 0.95 - 0.1 * warm, 0.9 - 0.25 * warm], np.float32)
    return gray(v) * col


def beat_land(c: Ctx, t):
    g = c.g
    tl = t - B["land"]
    cam_z = (B["land"] - B["vault"]) * 0.35 + tl * 0.18
    lock = sstep(2.5, 5.0, tl)        # the three lock together
    thin = sstep(3.0, 9.0, tl)        # the flashes thin out; the pairs stop coming
    electron = sstep(7.0, 10.0, tl)   # a smaller, quicker thing falls in
    clear = sstep(9.5, 16.0, tl)      # the glare clears; we can see a long way
    img = gas_layer(c, t, clear)
    img += sea_layer(c, t, cam_z, pair_gain=1.6 * (1 - thin), warp=0.9, glare=1.0 - clear)
    img += proton_layer(c, t, cam_z, lock, electron, clear, bright=1.0 - 0.5 * clear) * sstep(0.5, 3.0, tl)
    # ours: two others approach and the three lock, circling so fast they read as one body
    px, py = our_particle_pos(c, t) if tl < 2.5 else (lerp(our_particle_pos(c, B["land"] + 2.5)[0], 0.0, sstep(2.5, 6, tl)),
                                                       lerp(our_particle_pos(c, B["land"] + 2.5)[1], 0.0, sstep(2.5, 6, tl)))
    approach = sstep(0.0, 2.5, tl)
    orbit = 0.11 * (1 - 0.55 * lock)
    pts = []
    cols = [(1.0, 0.95, 0.85), (0.95, 0.6, 1.0), (0.6, 0.9, 1.0)]
    for k in range(3):
        a = t * 16.0 * (1 - 0.92 * lock) + k * 2 * np.pi / 3
        tx = [0.0, -0.5, 0.5][k] * orbit * 1.4
        ty = [-0.5, 0.45, 0.45][k] * orbit * 1.4
        ox = np.cos(a) * orbit * (1 - lock) + tx * lock
        oy = np.sin(a) * orbit * (1 - lock) + ty * lock
        if k > 0:
            # the two others come in from far off
            start = (1.6 if k == 1 else -1.5, 0.9 if k == 1 else -0.8)
            ox = lerp(start[0], ox, approach)
            oy = lerp(start[1], oy, approach)
        pts.append((px + ox, py + oy, cols[k]))
    for (x_, y_, col) in pts:
        img += gray(gauss(g, x_, y_, 0.03, 0.03)) * np.array(col, np.float32) * 1.3
        img += gray(gauss(g, x_, y_, 0.09, 0.09)) * np.array(col, np.float32) * 0.2
    if electron > 0:
        a = t * 11.0
        img += gray(gauss(g, px + np.cos(a) * 0.32, py + np.sin(a) * 0.32, 0.012, 0.012)) * np.array([0.7, 0.85, 1.0], np.float32) * 1.2 * electron
        ring = np.abs(np.sqrt((g.x - px) ** 2 + (g.y - py) ** 2) - 0.32)
        img += gray(np.exp(-0.5 * (ring / 0.006) ** 2)) * 0.12 * electron
    return np.clip(img, 0, 1.2)


# ----------------------------------------------------------------------------- beat 7: the earth brings forth

def web_field(c: Ctx, t, draw, knot):
    """Threads from Worley edges, knots at the feature points."""
    g = c.g
    pts = c.web_pts["pts"]
    drift = 0.02 * (t - B["earth"])
    f1, f2 = worley(pts + np.array([drift, -drift * 0.5], np.float32), g.x, g.y)
    width = 0.22 * (1 - 0.8 * draw) + 0.02
    threads = np.exp(-((f2 - f1) / width) ** 2)
    knots = np.exp(-(f1 / (0.05 + 0.10 * knot)) ** 2)
    return threads, knots


def beat_earth(c: Ctx, t):
    g = c.g
    te = t - B["earth"]
    draw = sstep(0.0, 8.0, te)
    knot = sstep(3.0, 10.0, te)
    threads, knots = web_field(c, t, draw, knot)
    n = c.n3.sample(g.x * 1.2 + 1.0, g.y * 1.2, t * 0.08, octaves=4)
    even = 0.10 + 0.14 * n
    dens = even * (1 - draw) + (0.03 + 0.26 * threads * (0.5 + 0.5 * n) + 0.3 * knots * knot) * draw
    col = np.array([1.0, 0.93, 0.82], np.float32)
    img = gray(dens) * col
    # the last of the protons, far off
    cam_z = (B["land"] - B["vault"]) * 0.35 + (B["earth"] - B["land"]) * 0.18 + te * 0.1
    img += proton_layer(c, t, cam_z, 1.0, 1.0, 1.0, bright=0.4 * (1 - draw * 0.7))
    return np.clip(img, 0, 1.2)


# ----------------------------------------------------------------------------- beat 8: lights

def star_sx(pts_i, c: Ctx):
    return c.web_pts["pts"][pts_i]


def beat_lights(c: Ctx, t):
    g = c.g
    tl = t - B["lights"]
    W = c.web_pts
    pts, ign, burst, burst_t = W["pts"], W["ignite"], W["burst"], W["burst_t"]
    # which star we fall into: the one nearest the centre
    target = int(np.argmin(pts[:, 0] ** 2 + pts[:, 1] ** 2))
    fall = sstep(8.0, 12.0, tl)
    zoom = np.exp(fall * 6.0)
    tx, ty = pts[target]
    # camera zooms onto the target
    cx = tx * fall
    cy = ty * fall
    if fall < 1.0:
        gz = Grid.__new__(Grid)
        gz.__dict__.update(g.__dict__)
        gz.x = (g.x) / zoom + cx
        gz.y = (g.y) / zoom + cy
        gz.px = g.px / zoom
        # the web, drawn, with the knots lit one by one
        drift = 0.02 * (t - B["earth"])
        f1, f2 = worley(pts + np.array([drift, -drift * 0.5], np.float32), gz.x, gz.y)
        threads = np.exp(-((f2 - f1) / 0.07) ** 2)
        n = c.n3.sample(gz.x * 1.2 + 1.0, gz.y * 1.2, t * 0.08, octaves=3)
        base = 0.03 + 0.26 * threads * (0.5 + 0.5 * n)
        img = gray(base) * np.array([1.0, 0.93, 0.82], np.float32)
        # ignitions
        xs, ys, cols, inten = [], [], [], []
        for i in range(len(pts)):
            age = tl - ign[i]
            if age < 0:
                continue
            x_, y_ = pts[i] + np.array([drift, -drift * 0.5])
            amp = sstep(0.0, 0.6, age)
            if burst[i] and age > burst_t[i]:
                ba = age - burst_t[i]
                ring = np.abs(np.sqrt((gz.x - x_) ** 2 + (gz.y - y_) ** 2) - ba * 0.25)
                img += gray(np.exp(-0.5 * (ring / 0.02) ** 2)) * np.array([1.0, 0.7, 0.5], np.float32) * max(0.0, 1 - ba * 0.8)
                amp = amp * max(0.0, 1 - ba * 2.0)
                # what it throws off gathers and lights again, nearby
                if ba > 1.2:
                    img += gray(gauss(gz, x_ + 0.18, y_ - 0.1, 0.03, 0.03)) * np.array([0.8, 0.9, 1.0], np.float32) * sstep(1.2, 2.0, ba)
            if i == target:
                amp = max(amp, sstep(5.0, 7.0, tl))
            img += gray(gauss(gz, x_, y_, 0.025, 0.025)) * np.array([0.85, 0.92, 1.0], np.float32) * amp * 1.5
            img += gray(gauss(gz, x_, y_, 0.11, 0.11)) * np.array([0.6, 0.8, 1.0], np.float32) * amp * 0.5
        # the glare fills the frame as we fall in
        img += gray(gauss(g, 0, 0, 0.9, 0.9)) * np.array([1.0, 0.85, 0.6], np.float32) * fall ** 2 * 2.0
        return np.clip(img, 0, 1.2)
    # inside the star
    ti = tl - 12.0
    img = star_interior(c, t, ti)
    return img


def star_interior(c: Ctx, t, ti):
    """Violent: the electron torn away, bare nuclei slamming past, ours hits another and holds, hits a
    third, and a photon comes off. ti runs 0..8."""
    g = c.g
    glare = c.n3.sample(g.x * 2.0, g.y * 2.0, t * 1.5, octaves=3)
    img = gray(0.35 + 0.5 * glare) * np.array([1.0, 0.72, 0.42], np.float32)
    # nuclei streaking past
    r = rng(1234)
    n = 900
    bx = r.uniform(-2.2, 2.2, n).astype(np.float32)
    by = r.uniform(-1.3, 1.3, n).astype(np.float32)
    vx = r.uniform(-2.5, 2.5, n).astype(np.float32)
    vy = r.uniform(-2.0, 2.0, n).astype(np.float32)
    ph = r.uniform(0, 2, n).astype(np.float32)
    xs = ((bx + vx * (t * 1.0 + ph) + 2.2) % 4.4) - 2.2
    ys = ((by + vy * (t * 1.0 + ph) + 1.3) % 2.6) - 1.3
    cols = np.tile(np.array([[1.0, 0.95, 0.85]], np.float32), (n, 1))
    img += splat(g, xs, ys, cols, np.ones(n, np.float32) * 0.9, radius_px=2.5 * g.h / 540, glow_px=8 * g.h / 540)
    # ours at the centre, three quarks settled; an electron torn away at 0.5 s
    for k, (ox, oy) in enumerate([(0.0, -0.035), (-0.035, 0.03), (0.035, 0.03)]):
        img += gray(gauss(g, ox, oy, 0.03, 0.03)) * 1.6
    if 0.5 < ti < 2.5:
        k = (ti - 0.5) / 2.0
        img += gray(gauss(g, 0.3 + k * 2.0, 0.1 + k * 0.6, 0.012, 0.012)) * np.array([0.7, 0.85, 1.0], np.float32) * (1 - k)
    # a second proton arrives at 2.5 s and holds; a third at 4.5 s; a photon comes off at 6 s
    for arrive, side in ((2.5, 1), (4.5, -1)):
        if ti > arrive - 1.2:
            k = sstep(arrive - 1.2, arrive, ti)
            ax = lerp(side * 2.4, side * 0.11, k)
            ay = lerp(side * 0.8, 0.0, k)
            for (ox, oy) in [(0.0, -0.03), (-0.03, 0.025), (0.03, 0.025)]:
                img += gray(gauss(g, ax + ox, ay + oy, 0.028, 0.028)) * 1.4
            if ti > arrive:
                fl = np.exp(-(ti - arrive) * 3.0)
                img += gray(gauss(g, 0, 0, 0.5, 0.5)) * fl * 1.2
    if ti > 6.0:
        k = ti - 6.0
        # the photon: a white point leaving the centre, which the camera then follows
        px = min(k * 1.6, 0.0 + 0.0) if k < 0.0 else k * 0.9
        img += gray(gauss(g, px, px * 0.3, 0.014, 0.014)) * 2.0
        img += gray(gauss(g, px, px * 0.3, 0.06, 0.06)) * 0.5
        # the glare slides away behind us
        img = img * (1 - sstep(0.4, 2.0, k)) ** 0.8
    return np.clip(img, 0, 1.2)


# ----------------------------------------------------------------------------- beat 9: the crossing

def earth_disc(c: Ctx, t, tc, radius):
    """The world, cooling as we close on it: molten, crust, cloud, ocean and bare land."""
    g = c.g
    cool = sstep(5.0, 9.6, tc)
    x = g.x / radius
    y = g.y / radius
    rr = np.sqrt(x * x + y * y)
    m = 1 - smoothstep(0.98, 1.0 + g.px / radius, rr)
    n1 = c.vn.fbm(x * 2.5 + tc * 0.02, y * 2.5, 4)
    n2 = c.vn2.fbm(x * 5.0 - 3.0, y * 5.0 + 2.0, 4)
    molten = np.stack([0.55 + 0.4 * n1, 0.12 + 0.2 * n1 ** 2, 0.03 + 0.02 * n1], axis=-1)
    crust = np.stack([0.18 + 0.1 * n2, 0.15 + 0.08 * n2, 0.14 + 0.08 * n2], axis=-1)
    land = smoothstep(0.56, 0.6, n1)
    ocean = np.stack([0.20 + 0.05 * n2, 0.30 + 0.05 * n2, 0.38 + 0.08 * n2], axis=-1)
    dark_land = np.stack([0.12 + 0.05 * n2, 0.11 + 0.04 * n2, 0.09 + 0.03 * n2], axis=-1)
    world = ocean * (1 - land[..., None]) + dark_land * land[..., None]
    cloud = smoothstep(0.52, 0.7, c.vn.fbm(x * 3.0 + 9.0 + tc * 0.05, y * 3.0, 4))
    world = world * (1 - cloud[..., None] * 0.9) + cloud[..., None] * 0.9
    k1 = sstep(0.0, 0.5, cool)
    k2 = sstep(0.4, 1.0, cool)
    surf = molten * (1 - k1) + crust * k1
    surf = surf * (1 - k2) + world * k2
    # limb shading
    shade = np.clip(1 - rr ** 3, 0, 1) * (0.55 + 0.45 * np.clip(1 - np.sqrt((x + 0.5) ** 2 + (y - 0.3) ** 2) / 1.6, 0, 1))
    return surf * (shade * m)[..., None], m


def beat_cross(c: Ctx, t):
    g = c.g
    tc = t - B["cross"]
    img = g.blank(0.0)
    if tc < 10.0:
        # black, and speed
        r = rng(321)
        n = 700
        ang = r.uniform(0, 2 * np.pi, n).astype(np.float32)
        rad0 = r.uniform(0.02, 1.0, n).astype(np.float32)
        spd = r.uniform(0.6, 1.8, n).astype(np.float32)
        rad = ((rad0 + tc * spd * 0.5) % 1.9) + 0.03
        xs = np.cos(ang) * rad * g.aspect
        ys = np.sin(ang) * rad
        cols = np.tile(np.array([[0.55, 0.6, 0.75]], np.float32), (n, 1))
        inten = (rad * 0.5).astype(np.float32) * (1 - sstep(7.5, 9.5, tc))
        img += splat(g, xs, ys, cols, inten, radius_px=1.2 * g.h / 540, glow_px=3 * g.h / 540)
        # the photon, at the centre
        img += gray(gauss(g, 0, 0, 0.012, 0.012)) * 1.8 + gray(gauss(g, 0, 0, 0.05, 0.05)) * 0.4
        # ahead, a point of dull red that grows into a world
        if tc > 1.5:
            radius = 0.004 * np.exp((tc - 1.5) * 0.66)
            radius = min(radius, 1.3)
            disc_img, m = earth_disc(c, t, tc, radius)
            img = img * (1 - m[..., None]) + disc_img
        return np.clip(img, 0, 1)
    # down through cloud, through the surface, into green-lit water, into a single cell
    td = tc - 10.0
    if td < 1.5:
        # whiteout of cloud thinning to the sea surface
        n = c.n3.sample(g.x * 3 + td, g.y * 3, t * 0.5, octaves=4)
        cloud = 0.75 + 0.25 * n
        sea = np.stack([0.22 + 0.05 * n, 0.32 + 0.05 * n, 0.42 + 0.08 * n], axis=-1)
        k = sstep(0.3, 1.5, td)
        img = gray(cloud) * (1 - k) + sea * k
        # ripples approaching
        rip = np.sin((g.y + td * 2.0) * 40 + n * 6) * 0.5 + 0.5
        img += gray(rip * 0.12 * k)
        return np.clip(img, 0, 1)
    tw = td - 1.5
    if tw < 0.25:
        return g.blank(0.0) + np.array([0.5, 0.8, 1.0], np.float32) * (1 - tw / 0.25)
    # under the surface: green-lit water with light rays from above
    n = c.n3.sample(g.x * 2.0, g.y * 2.0 - tw * 0.6, t * 0.3, octaves=3)
    depthk = sstep(0.0, 3.0, tw)
    rays = np.clip(np.sin(g.x * 9 + n * 4 + t * 0.7) * 0.5 + 0.5, 0, 1) * np.clip(g.y + 0.9, 0, 1.3) * 0.25
    water = np.stack([0.05 + 0.1 * n, 0.35 + 0.25 * n, 0.25 + 0.15 * n], axis=-1) * (1 - 0.4 * depthk)
    img = water + gray(rays)
    # into a single cell: it grows at the centre as we close
    cell_r = 0.02 * np.exp(tw * 1.0)
    cell_r = min(cell_r, 0.24)
    img = draw_cell(c, img, 0.0, 0.0, cell_r, t, lit=sstep(2.6, 3.3, tw))
    return np.clip(img, 0, 1)


def draw_cell(c: Ctx, img, cx, cy, r_, t, lit=0.0, stretch=0.0, ang=0.0, tint=(0.95, 0.9, 0.7)):
    g = c.g
    dx, dy = g.x - cx, g.y - cy
    if ang:
        ca, sa = np.cos(ang), np.sin(ang)
        dx, dy = ca * dx + sa * dy, -sa * dx + ca * dy
    rx = r_ * (1 + stretch)
    ry = r_ / (1 + 0.5 * stretch)
    wob = 1 + 0.04 * np.sin(np.arctan2(dy, dx) * 5 + t * 2.0)
    d = np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2) / wob
    body = 1 - smoothstep(0.96, 1.0 + 2 * g.px / r_, d)
    membrane = np.exp(-0.5 * ((d - 0.96) / (0.02 + g.px / r_)) ** 2)
    inner = np.exp(-d * d * 2.0)
    col = np.array(tint, np.float32)
    cell = col * (0.35 + 0.45 * inner)[..., None] * (1 + 0.6 * lit)
    img = over_img(img, body * 0.85, cell)
    img = add(img, membrane * 0.6, (0.8, 0.9, 0.8))
    # the nucleus
    img = over(img, disc(g, cx, cy, r_ * 0.22) * 0.5, (0.45, 0.4, 0.3))
    return img
