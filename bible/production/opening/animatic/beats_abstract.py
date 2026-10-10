"""Beats 1-9 of the Opening: the static, the faces, the alternation, the particle sea, the proton,
the web, the stars, and the photon's crossing. Every function takes global time t (seconds) and
returns an H x W x 3 float32 image. Everything is a pure function of t, so frames can be rendered
in any order and in parallel.

Timings follow treatment v3.3 §2 exactly (v3.2's table, unchanged in v3.3): v3.1's table with ten seconds added at the front, which
are the fade from black (the author, 2026-10-08). Everything after 0:00 runs ten seconds later.
"""
from __future__ import annotations

import numpy as np

from common import (Grid, Static, ValueNoise, Noise3, curl_field, worley, smoothstep, sstep, lerp,
                    ease_in_out, disc, gauss, blur, hsv, gray, over, over_img, add, rng, clamp01,
                    mandelbrot_glow, cosine_palette, worley3)
import face as F
import facemesh as FM

# beat boundaries (seconds)
B = dict(deep=0.0, light=38.0, sep=46.0, eve=68.0, vault=84.0, land=104.0, earth=122.0,
         lights=132.0, cross=152.0, swarm=166.0, landbeat=198.0, dust=222.0, fill=240.0, rest=276.0, end=300.0)

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
        self._mesh = None
        self._mface_cache = {}

    def mface(self, cx, cy, s, e, yaw=0.0):
        """The mesh face (facemesh.py), cached by quantized parameters."""
        if self._mesh is None:
            self._mesh = FM.FaceMesh()
        k = (round(cx, 3), round(cy, 3), round(s, 3), round(yaw, 3)) + tuple(round(e[n], 3) for n in ("brow", "curve", "open", "eyes", "wide"))
        f = self._mface_cache.get(k)
        if f is None:
            f = self._mesh.render(self.g, cx, cy, s, e, yaw=yaw)
            if len(self._mface_cache) > 6:
                self._mface_cache.clear()
            self._mface_cache[k] = f
        return f

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
#
# v3 (the author's notes on v2, 2026-10-09): the static is sand. It flows over a face that rises out
# of it from underneath, the way sand pours over a relief, and the face is seen by how the grains
# catch the light on its contours: brow, eyes, nose, mouth. Nothing is outlined. The picture fades in
# from the first frame, slowly.

FADE = (0.0, 10.0)        # the fade from black starts on frame 0 (the author, 2026-10-09)
FACE_POS = (0.0, -0.02)   # where the first face is, in beats 1-2
FACE_S = 0.62             # its half-height


def fade_in(t):
    """Slow at first and slow at the end: barely there at 1 s, half at about 6 s, full at 10 s."""
    x = min(max((t - FADE[0]) / (FADE[1] - FADE[0]), 0.0), 1.0)
    return x * x * x * (x * (x * 6 - 15) + 10)


def face_strength(t):
    """How far the face has risen out of the sand, 0..1."""
    return sstep(15.0, 30.0, t)


def flow_amp(t):
    return sstep(12.0, 20.0, t)


def relief(c, t, e=None, rise=1.0):
    """The face as a height field under the sand: (height, gradient x, gradient y, fields)."""
    g = c.g
    if e is None:
        e = F.NEUTRAL_CLOSED
    f = c.mface(FACE_POS[0], FACE_POS[1], FACE_S, e)
    # the head lies under the sand: its silhouette is a slope, not an edge
    soft = smoothstep(0.5, 1.0, blur(f["mask"], 0.22 * FACE_S * g.h))
    d = f["depth"] * soft
    # the features are what we need to read, so they stand higher than the dome of the head
    detail = d - blur(d, 0.12 * FACE_S * g.h)
    h = (0.45 * d + 2.2 * detail) * rise
    h = h + 0.12 * rise * gauss(g, FACE_POS[0], FACE_POS[1] + 0.05, FACE_S * 0.9, FACE_S * 1.2)
    gy, gx = np.gradient(h)
    return h, gx / g.px * FACE_S * 0.12, -gy / g.px * FACE_S * 0.12, f


def sand_field(c, t, h, gx, gy, amp, light=(-0.75, 0.55), grain_scale=0.6, sparkle=0.05):
    """Grains flowing across the frame and over the relief h, lit by a raking light. 0..1 grey."""
    g = c.g
    # the current: two scales of eddies and a slow drift to the left
    vx1, vy1 = curl_field(c.flow, g.x[::4, ::4], g.y[::4, ::4], scale=1.1, eps=0.02, t=0.025 * t)
    vx2, vy2 = curl_field(c.vn2, g.x[::4, ::4], g.y[::4, ::4], scale=3.2, eps=0.01, t=-0.04 * t)
    vx = up4(vx1 * 0.05 + vx2 * 0.015, g) - 0.06
    vy = up4(vy1 * 0.05 + vy2 * 0.015, g)
    # over the relief the grains are turned along its contours and slowed as they climb
    gm = np.sqrt(gx * gx + gy * gy) + 1e-6
    nx, ny = gx / gm, gy / gm
    along = vx * nx + vy * ny
    w = np.clip(gm * 1.5, 0, 0.85)
    vx = vx - along * nx * w
    vy = vy - along * ny * w
    slow = 1.0 / (1.0 + 1.2 * h)
    vx, vy = vx * slow * amp, vy * slow * amp
    # sample the grain along its own motion (sand streaks) and lift it by the relief (parallax)
    scale = g.h / 2 * grain_scale
    par = 0.10 * h
    acc = np.zeros(g.x.shape, np.float32)
    for k, dt in enumerate((-0.02, 0.0, 0.02)):
        gg = _shift_grid(g, -(g.x - FACE_POS[0]) * par + vx * dt * 6, -(g.y - FACE_POS[1]) * par + vy * dt * 6)
        acc += c.static.render(gg, vx, vy, t, period=1.5, scale=scale, sparkle=0.0, seed_t=t)
    s = acc / 3.0
    # grains are hard: push the grey toward black and white, keep a little in between
    s = np.clip((s - 0.5) * 2.2 + 0.5, 0, 1)
    if sparkle > 0:
        r = rng(int(t * 1000) + 11)
        flip = r.random(s.shape, dtype=np.float32) < sparkle
        s = np.where(flip, 1 - s, s)
    # the light: the relief's normal against a low light from the upper left
    lx, ly = light
    lz = 0.45
    nz = 1.0
    n = np.sqrt(gx * gx + gy * gy + nz * nz)
    lam = np.clip((-gx * lx - gy * ly + nz * lz) / (n * np.sqrt(lx * lx + ly * ly + lz * lz)), 0, 1)
    flat = lz / np.sqrt(lx * lx + ly * ly + lz * lz)
    shade = lam / flat  # 1 on flat sand, brighter facing the light, dark in the lee
    # the hollows hold shadow (eye sockets, under the nose, the mouth line)
    hb = blur(h, 5 * g.h / 540)
    occ = np.clip((hb - h) * 14.0, 0, 0.85)
    # on the face the sand lies thinner, so the light on the form shows through the grain more
    on = np.clip(h * 3.0, 0, 1)
    gc = 0.85 - 0.35 * on
    v = (1 - gc + gc * s) * (0.12 + 0.88 * np.clip(shade, 0, 1.8)) * (1 - occ)
    return np.clip(v, 0, 1.3)


def _shift_grid(g, dx, dy):
    gg = Grid.__new__(Grid)
    gg.__dict__.update(g.__dict__)
    gg.x = g.x + dx
    gg.y = g.y + dy
    return gg


def up4(a, g):
    out = np.repeat(np.repeat(a, 4, axis=0), 4, axis=1)[:g.h, :g.w]
    if out.shape != (g.h, g.w):
        pad = np.zeros((g.h, g.w), np.float32)
        pad[:out.shape[0], :out.shape[1]] = out
        out = pad
    return blur(out, 3)


def beat_deep(c: Ctx, t):
    g = c.g
    amp = flow_amp(t)
    fs = face_strength(t)
    if fs > 0:
        h, gx, gy, _ = relief(c, t, rise=ease_in_out(fs))
    else:
        h = gx = gy = np.zeros(g.x.shape, np.float32)
    # before the flow, the static only shimmers in place
    s = sand_field(c, t, h, gx, gy, max(amp, 0.04), sparkle=0.07 * (1 - 0.7 * amp))
    img = gray(s)
    f = fade_in(t)
    if f < 1.0:
        img = img * f
    return img


# ----------------------------------------------------------------------------- beat 2: light
#
# v3: the release. For one frame the sand is pressed onto the face and shows every contour. Then it is
# blown off it, away from us and into the picture: every grain streaks inward past the head and is
# gone behind it, the dark going with it, and the face is left lit, white, in black.

RELEASE = 0.42  # seconds, the blast, still about a blink


def white_face(c, e, light=(-0.45, 0.5, 0.75), cx=None, cy=None, s=None, yaw=0.0, gain=1.0):
    cx = FACE_POS[0] if cx is None else cx
    cy = FACE_POS[1] if cy is None else cy
    s = FACE_S if s is None else s
    f = c.mface(cx, cy, s, e, yaw=yaw)
    return FM.skin(f, light=light) * gain, f


def beat_light(c: Ctx, t):
    g = c.g
    tl = t - B["light"]
    if tl < 2.0 / 24:
        # pressed on: the relief at full height and twice the light, every contour shown
        h, gx, gy, _ = relief(c, t, rise=1.6)
        s = sand_field(c, t, h, gx * 1.4, gy * 1.4, 0.0, sparkle=0.0)
        return gray(s * 1.15)
    if tl < RELEASE:
        k = (tl - 2.0 / 24) / (RELEASE - 2.0 / 24)
        # the sand rushes inward toward a point behind the head, streaking as it goes
        cx, cy = FACE_POS
        pull = k ** 1.6
        acc = np.zeros(g.x.shape, np.float32)
        for j in range(8):
            z = 1.0 + (pull + 0.06 * j * (0.4 + k)) * 4.0
            gg = _shift_grid(g, (g.x - cx) * (z - 1), (g.y - cy) * (z - 1))
            acc += c.static.render(gg, 0.0, 0.0, B["light"], period=1.5, sparkle=0.0, seed_t=t)
        s = np.clip((acc / 8 - 0.5) * 2.2 + 0.5, 0, 1)
        # the field thins from the outside in: the dark goes with it
        rr = np.sqrt(((g.x - cx) / 1.0) ** 2 + ((g.y - cy) / 0.8) ** 2)
        keep = 1 - smoothstep(2.6 * (1 - pull) - 0.2, 2.6 * (1 - pull) + 0.25, rr)
        s = s * keep * (1 - 0.6 * k)
        w, f = white_face(c, F.NEUTRAL_CLOSED, gain=sstep(0.0, 0.6, k) * 1.25)
        # a burst of light from the face as it's stripped
        glow = gauss(g, cx, cy, 0.35 + 0.3 * k, 0.45 + 0.3 * k) * (1 - k) ** 2 * 0.5
        img = gray(s * (1 - f["edge"] * sstep(0.1, 0.7, k)) + glow)
        img = img + gray(w)
        return np.clip(img, 0, 1)
    # black, silence, the white face alone, eyes closed; then the eyes open and the large face forms
    k = sstep(6.5, 7.3, tl)
    e = F.mix_expr(F.NEUTRAL_CLOSED, F.NEUTRAL_OPEN, k)
    settle = sstep(RELEASE, RELEASE + 1.2, tl)
    if k > 0:
        img = dark_scene(c, t, e, F.MALICE, form=k)
    else:
        w, f = white_face(c, e, gain=1.25 - 0.25 * settle)
        img = gray(w)
    # the last of the glow dies away
    img += gray(gauss(g, FACE_POS[0], FACE_POS[1], 0.6, 0.7)) * 0.18 * (1 - settle)
    return np.clip(img, 0, 1)


# ----------------------------------------------------------------------------- beat 3: the separation
#
# v3: the large face is off to the side, turned toward the small one, not behind it (the author,
# 2026-10-09). In the dark it is lit only by the white face, so we see the side of it that faces the
# light. The turn-over is a front of light that runs out from where they touch, fast but not a cut.

SMALL_S = 0.50
BIG_S = 1.30
BIG_POS = (1.02, 0.04)
SMALL_TO = (-0.62, -0.02)
SMALL_YAW = 0.32    # the small face looks toward the large one, screen right
BIG_YAW = -0.55     # the large face turns toward screen left
WHITE = 0.94        # the white ground


def layout(t):
    """Positions and sizes of the two faces at time t (beats 2-4)."""
    k = ease_in_out(sstep(B["light"] + 6.3, B["light"] + 9.5, t))  # the small face makes room
    sx = lerp(FACE_POS[0], SMALL_TO[0], k)
    sy = lerp(FACE_POS[1], SMALL_TO[1], k)
    ss = lerp(FACE_S, SMALL_S, k)
    syaw = SMALL_YAW * k
    ts = t - B["sep"]
    reach = ease_in_out(sstep(10.6, 12.5, ts)) if t < B["sep"] + 12.5 else 0.0
    bx = lerp(BIG_POS[0], 0.10, reach)
    bs = BIG_S * (1 + 0.25 * reach)
    return (sx, sy, ss, syaw), (bx, BIG_POS[1], bs, BIG_YAW * (1 - 0.3 * reach)), reach


def big_dark_face(c, t, eb, form, pulse=0.0):
    """Black on black, lit only from the small white face's side."""
    g = c.g
    (sx, sy, ss, syaw), (bx, by, bs, byaw), _ = layout(t)
    f = c.mface(bx, by, bs * (1 + pulse), eb, yaw=byaw)
    L = (sx - bx, (sy - by) * 0.6 + 0.15, 0.55)
    lam = FM.lambert(f, L, wrap=0.0)
    rim = lam ** 3.0
    v = (0.22 * rim + 0.01) * f["edge"]
    v = v * (1 - 0.8 * f["iris"]) * (1 - 0.9 * f["mouth"])
    return gray(v * form)


def small_white_face(c, t, es, gain=1.0):
    (sx, sy, ss, syaw), (bx, by, bs, byaw), _ = layout(t)
    f = c.mface(sx, sy, ss, es, yaw=syaw)
    return FM.skin(f, light=(-0.35, 0.5, 0.8)) * 1.15 * gain, f


def dark_scene(c, t, es, eb, form=1.0, pulse=0.0, tremor=0.0):
    img = big_dark_face(c, t, eb, form, pulse)
    w, f = small_white_face(c, t, es)
    m = f["edge"]
    return img * (1 - m[..., None]) + gray(w)


def light_scene(c, t, es, eb, tend=0.0):
    """White ground: the large face white on white, compassionate; the small face dark and upset."""
    g = c.g
    (sx, sy, ss, syaw), (bx, by, bs, byaw), _ = layout(t)
    bx2 = lerp(bx, 0.55, tend)
    fb = c.mface(bx2, by, bs, eb, yaw=byaw * (1 - 0.2 * tend))
    lam = FM.lambert(fb, (-0.3, 0.6, 0.75), wrap=0.4)
    occ = FM.cavity(fb)
    vb = WHITE - (0.30 * (1 - lam) + 0.25 * occ + 0.12 * blur(fb["iris"], 2) + 0.1 * fb["eyes"] + 0.4 * fb["mouth"]) * fb["edge"]
    fs = c.mface(sx, sy, ss, es, yaw=syaw)
    # the dark face, lit from the white face beside it
    L = (bx2 - sx, 0.2, 0.6)
    lam_s = FM.lambert(fs, L, wrap=0.1)
    vs = 0.04 + 0.30 * lam_s ** 2
    vs = vs * (1 - 0.7 * fs["iris"]) * (1 - 0.8 * fs["mouth"])
    m = fs["edge"]
    v = vb * (1 - m) + vs * m
    return gray(v)


def front_mask(c, t, t0, origin, dur=0.5, warp=0.25):
    """A front of light running out from origin, starting at t0, crossing the frame in dur seconds.
    Returns (inside 0..1, rim 0..1)."""
    g = c.g
    k = (t - t0) / dur
    if k <= 0:
        z = np.zeros(g.x.shape, np.float32)
        return z, z
    rad = 4.0 * k ** 1.3
    n = c.vn.fbm(g.x * 2.2 + t0, g.y * 2.2 - t0, 4) - 0.5
    d = np.sqrt((g.x - origin[0]) ** 2 + (g.y - origin[1]) ** 2) + n * warp * (0.3 + rad)
    soft = 0.05 + 0.12 * rad
    inside = 1 - smoothstep(rad - soft, rad + soft, d)
    rim = np.exp(-0.5 * ((d - rad) / (soft * 0.8)) ** 2) * (1 - sstep(0.7, 1.0, k))
    return inside, rim


def beat_sep(c: Ctx, t):
    g = c.g
    ts = t - B["sep"]
    T_TURN = 12.5
    climb = ease_in_out(ts / 11.0)
    es_d = F.mix_expr(F.FEAR, F.TERROR, climb)
    eb_d = F.mix_expr(F.MALICE, F.LAUGH, climb)
    pulse = 0.0
    if ts > 6:
        pulse = 0.015 * sstep(6, 9, ts) * max(0.0, np.sin(ts * 2 * np.pi * 4.5)) ** 2
    if ts < T_TURN:
        return np.clip(dark_scene(c, t, es_d, eb_d, pulse=pulse), 0, 1)
    tt = ts - T_TURN
    k = ease_in_out(tt / 7.5)
    es = F.mix_expr(F.UPSET, F.PEACE, k)
    eb = F.mix_expr(F.COMPASSION, F.PEACE, k)
    kz = sstep(7.0, 9.5, tt)
    es = F.mix_expr(es, F.SLEEP, kz)
    eb = F.mix_expr(eb, F.SLEEP, kz)
    tend = ease_in_out(sstep(0.5, 6.0, tt))
    lit = light_scene(c, t, es, eb, tend)
    if tt < 0.6:
        # the turn-over: a front of light from where they touch
        (sx, sy, _, _), _, _ = layout(B["sep"] + T_TURN - 0.01)
        inside, rim = front_mask(c, t, B["sep"] + T_TURN, (sx + 0.35, sy), dur=0.5)
        dark = dark_scene(c, t, es_d, eb_d)
        img = dark * (1 - inside[..., None]) + lit * inside[..., None]
        return np.clip(img + gray(rim) * 0.6 * np.array([1.0, 0.97, 0.9], np.float32), 0, 1)
    return np.clip(lit, 0, 1)


def dark_face(fields, g, edge=0.22):
    """The small face gone dark on a white ground (the old sculpted face; kept for beat 4's tail)."""
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


def warped_fbm(c, x, y, t, scale=1.5):
    """Inigo Quilez's domain warping: fbm(p + fbm(p + fbm(p))). Simple sums of noise, folded back on
    themselves, give the organic, ink-in-water structure the alternation spreads through."""
    qx = c.vn.fbm(x * scale + 1.7, y * scale + 9.2, 4)
    qy = c.vn.fbm(x * scale + 8.3, y * scale + 2.8, 4)
    rx = c.vn2.fbm(x * scale + 4.0 * qx + 1.7 + 0.15 * t, y * scale + 4.0 * qy + 9.2, 4)
    ry = c.vn2.fbm(x * scale + 4.0 * qx + 8.3, y * scale + 4.0 * qy + 2.8 - 0.12 * t, 4)
    return c.vn.fbm(x * scale + 4.0 * rx, y * scale + 4.0 * ry, 4), rx, ry


def grains(c, t, size_px=2.0, rate=(9.0, 15.0)):
    """Every grain turning between dark and light on its own beat, too fast to follow; out of step,
    so the frame as a whole never flashes. Returns 0..1 per pixel."""
    g = c.g
    gx = np.floor((g.x + g.aspect) * g.h / 2 / size_px).astype(np.int64)
    gy = np.floor((1 - g.y) * g.h / 2 / size_px).astype(np.int64)
    hsh = (gx * 73856093) ^ (gy * 19349663)
    ph = (hsh % 1009) / 1009.0
    rt = rate[0] + (rate[1] - rate[0]) * ((hsh // 1009) % 997) / 997.0
    return (np.sin(2 * np.pi * (rt * t + ph)) > 0).astype(np.float32)


def light_bloom(img_emit, g):
    """Light, not paint: a sharp core and two soft halos."""
    k = g.h / 540
    return img_emit * 0.9 + blur(img_emit, 4 * k) * 1.4 + blur(img_emit, 16 * k) * 1.6


def thin_film(c, g, t, amt):
    """The colors of oil on water: hue running along a slowly flowing field. Used for the first color."""
    n, rx, ry = warped_fbm(c, g.x[::2, ::2], g.y[::2, ::2], t, scale=1.1)
    hue = (n * 2.2 + rx * 0.6 + t * 0.07) % 1.0
    hue = np.repeat(np.repeat(hue, 2, 0), 2, 1)[:g.h, :g.w]
    return hsv(hue, 0.9, 1.0) * amt


def beat_eve(c: Ctx, t):
    g = c.g
    te = t - B["eve"]
    n_frame, n_cont = flip_count(te)
    n_frame = int(n_frame)
    # the first turns take the whole frame, each as a front of light or dark running out from the
    # faces in a third of a second. Then the turn spreads through the ground organically.
    spread = sstep(3.0, 7.0, te)
    warp, rx, ry = warped_fbm(c, g.x, g.y, t * 0.3, scale=1.2 + 2.5 * spread)
    offset = (warp - 0.5) * 2.4 * spread + (rx - 0.5) * 1.2 * spread
    (sx, sy, _, _), _, _ = layout(t)
    dist = np.sqrt((g.x - sx - 0.3) ** 2 + (g.y - sy) ** 2)
    tau = te - offset - dist * 0.09 * (1 - spread)  # the front: a third of a second to cross the frame
    npx, ncont_px = flip_count(tau)
    # soft edges between the turns: a quick ramp, not a cut
    frac = ncont_px - np.floor(ncont_px)
    edge_w = 0.10
    ramp = smoothstep(0.0, edge_w, frac)
    # 1 = light ground (connection), 0 = dark ground (separation). Turn k goes to dark when k is even:
    # the beat opens by turning back to dark. Each turn ramps from the last state in a fifth of a second.
    cur_light = (npx % 2) == 1
    state = np.where(cur_light, ramp, 1 - ramp).astype(np.float32)
    # grains: past the convergence, each turns on its own beat
    gr = sstep(6.0, 9.0, te)
    if gr > 0:
        state = state * (1 - gr) + grains(c, t, size_px=2.0 + 4.0 * (1 - gr)) * gr
    # the scene in both states; each patch shows one or the other
    climb = float(np.clip(te / 8.0, 0, 1))
    es_d = F.mix_expr(F.FEAR, F.TERROR, 0.5 + 0.5 * climb)
    eb_d = F.mix_expr(F.MALICE, F.LAUGH, 0.6 + 0.4 * climb)
    es_l = F.mix_expr(F.UPSET, F.SLEEP, 0.4 + 0.6 * climb)
    eb_l = F.mix_expr(F.COMPASSION, F.SLEEP, 0.4 + 0.6 * climb)
    fade = 1 - sstep(8.5, 13.0, te)  # the faces dissolve into the grains
    if fade > 0.01:
        dark = dark_scene(c, t, es_d, eb_d)
        lit = light_scene(c, t, es_l, eb_l, tend=0.6)
        ground_d = np.zeros_like(dark)
        ground_l = np.full_like(lit, WHITE)
        dark = ground_d * (1 - fade) + dark * fade
        lit = ground_l * (1 - fade) + lit * fade
    else:
        dark = g.blank(0.0)
        lit = g.blank(WHITE)
    st = state[..., None]
    img = dark * (1 - st) + lit * st
    # the first color: where dark meets light, a flash of colored light
    color_amt = sstep(7.5, 12.0, te)
    if color_amt > 0:
        edges = np.abs(state - blur(state, 1.2 * g.h / 540))
        edges = np.clip(edges * 3.0, 0, 1)
        # only a few meetings flash at any moment, each for a frame or two: sparks, not paint
        spark = grains(c, t * 0.37 + 11.0, size_px=3.0, rate=(2.0, 5.0)) * grains(c, t * 0.53 + 3.0, size_px=5.0, rate=(1.5, 4.0))
        # flares: small places that brighten and die in about half a second, all over the frame
        fl = c.n3.sample(g.x * 3.5, g.y * 3.5, t * 2.2, octaves=2)
        spark = spark * np.clip((fl - 0.56) / 0.08, 0, 1)
        film = thin_film(c, g, t, 1.0)
        emit = film * (edges * spark)[..., None] * color_amt * 0.9
        img = img * (1 - 0.25 * color_amt) + light_bloom(emit, g)
        # the shimmer: a faint sheen of the same colors drifting across the grain
        img = img + film * (0.06 * color_amt * state)[..., None]
    # the one grain we stay on: where the small face was, drawn in, then centre frame
    keep = sstep(10.0, 13.5, te)
    if keep > 0:
        gx_ = lerp(sx, 0.0, sstep(12.0, 15.5, te))
        gy_ = lerp(sy, 0.0, sstep(12.0, 15.5, te))
        gm = disc(g, gx_, gy_, 0.012, soft=g.px * 2)
        img = img * (1 - (gm * keep)[..., None]) + np.array([0.6, 0.6, 0.6], np.float32) * (gm * keep)[..., None]
        img = img + gray(gauss(g, gx_, gy_, 0.04, 0.04)) * 0.25 * keep
    return np.clip(img, 0, 1.2)


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


# The vault opens into a fractal (v3, the author's suggestion of 2026-10-09: "simple equations to
# produce complex things"). Behind the pair sea is the Mandelbrot set's boundary, z -> z^2 + c, lit
# by its own distance estimate, and we fall into it: depth that never runs out, patterns that gather
# and lose themselves, never regular.

MANDEL_C = -0.743643887037151 + 0.131825904205330j   # the seahorse valley, a classic deep-zoom point


def mandel_layer(c, t, amount, zoom_t0=B["vault"], hh0=0.012, rate=0.45):
    """The fractal as light, rendered at half resolution and bloomed. hh0: half-height at zoom_t0;
    rate: doublings of zoom per second."""
    g = c.g
    if amount <= 0:
        return np.zeros((g.h, g.w, 3), np.float32)
    tz = t - zoom_t0
    hh = hh0 * 2.0 ** (-rate * tz)
    it = int(np.clip(150 + 45 * np.log2(hh0 / hh + 1), 150, 900))
    w2, h2 = g.w // 2, g.h // 2
    glow, nu = mandelbrot_glow(w2, h2, MANDEL_C, hh, it, rot=0.05 * tz)
    col = cosine_palette(nu * 0.004 + t * 0.03, d=(0.0, 0.1, 0.2), c=(1.0, 1.0, 1.0)) * glow[..., None]
    col = np.repeat(np.repeat(col, 2, 0), 2, 1)
    out = np.zeros((g.h, g.w, 3), np.float32)
    out[:col.shape[0], :col.shape[1]] = col[:g.h, :g.w]
    out = blur(out, 1)
    return light_bloom(out * 0.22, g) * amount


def beat_vault(c: Ctx, t):
    g = c.g
    tv = t - B["vault"]
    cam_z = tv * 0.35
    opening = sstep(0.0, 4.5, tv)  # the picture gains depth
    img = mandel_layer(c, t, sstep(0.5, 5.0, tv))
    img = img + sea_layer(c, t, cam_z, pair_gain=2.0, warp=0.9, glare=1.1)
    # before the opening the grains are flat: the beat-4 shimmer carries on and gives way
    if opening < 1:
        img = beat_eve(c, t) * (1 - opening) + img * opening
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
    """The even gas of beat 6: the web's own fog before it draws in, so beat 7 grows out of it."""
    g = c.g
    if amount <= 0:
        return g.blank(0.0)
    hg = half_grid(c)
    dens, knots = cosmic_web(c, hg.x, hg.y, t, 0.0, 0.0)
    return up2(web_colour(dens, knots), g) * 1.2 * amount


def beat_land(c: Ctx, t):
    g = c.g
    tl = t - B["land"]
    cam_z = (B["land"] - B["vault"]) * 0.35 + tl * 0.18
    lock = sstep(2.5, 5.0, tl)        # the three lock together
    thin = sstep(3.0, 9.0, tl)        # the flashes thin out; the pairs stop coming
    electron = sstep(7.0, 10.0, tl)   # a smaller, quicker thing falls in
    clear = sstep(9.5, 16.0, tl)      # the glare clears; we can see a long way
    img = gas_layer(c, t, clear)
    img = img + mandel_layer(c, t, 1.0 - sstep(2.0, 11.0, tl))
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

_WEB_FINE = rng(92).uniform([-3.0, -1.8], [3.0, 1.8], (220, 2)).astype(np.float32)


def web_warp(c, x, y):
    """The bend in the threads: the same domain warp everywhere, so the knots and stars stay on them."""
    return (x + 0.45 * (c.vn.fbm(x * 0.8 + 3.3, y * 0.8 - 1.1, 4) - 0.5) + 0.08 * (c.vn.fbm(x * 4 + 1.3, y * 4, 2) - 0.5),
            y + 0.45 * (c.vn2.fbm(x * 0.8 - 7.7, y * 0.8 + 4.4, 4) - 0.5) + 0.08 * (c.vn2.fbm(x * 4 - 2.1, y * 4, 2) - 0.5))


def cosmic_web(c, x, y, t, draw, knot):
    """The gas drawn into threads (v3): curved threads between knots, finer threads branching between
    them like veins, all in a faint fog. Returns (density, knots) on the given coordinate arrays."""
    drift = 0.02 * (t - B["earth"])
    wx, wy = web_warp(c, x, y)
    pts = c.web_pts["pts"] + np.array([drift, -drift * 0.5], np.float32)
    f1, f2, f3 = worley3(pts, wx, wy)
    width = 0.22 * (1 - 0.85 * draw) + 0.010
    main = np.exp(-((f2 - f1) / width) ** 2)
    # the threads thin out toward the middle of each span and thicken toward the knots
    main = main * (0.35 + 0.65 * np.exp(-((f3 - f1) / 0.35) ** 2))
    # the finer branches, at two and a half times the scale, fainter
    g1, g2 = worley(_WEB_FINE * 0.6 + np.array([drift, 0.0], np.float32), wx * 1.0, wy * 1.0)
    fine = np.exp(-((g2 - g1) / (width * 0.5)) ** 2) * sstep(0.2, 0.8, draw)
    # matter is clumpy along the threads, not even
    along = c.vn.fbm(wx * 6.0 + 2.0, wy * 6.0 - 5.0, 3)
    fog = c.n3.sample(x * 1.2 + 1.0, y * 1.2, t * 0.08, octaves=4)
    knots = np.exp(-((f3 - f1) / (0.02 + 0.04 * knot)) ** 2) * np.exp(-(f2 - f1) ** 2 / 0.002)
    clump = np.clip((along - 0.35) * 2.2, 0, 1)
    dens = (0.12 + 0.18 * fog) * (1 - 0.8 * draw) + draw * (0.22 * main * clump + 0.07 * fine * clump + 0.03 * fog)
    dens = dens + 0.25 * knots * knot * draw
    return dens, knots


_STARS = None


def web_stars():
    """Where the stars light: the web's knots (where three threads meet), found once on a coarse grid
    in the web's own coordinates, so the picture and the sound (sound.py) agree. Sorted by x."""
    global _STARS
    if _STARS is None:
        g = Grid(480, 270)
        c = Ctx.__new__(Ctx)
        c.vn = ValueNoise(5, 256)
        c.vn2 = ValueNoise(6, 256)
        c.web_pts = make_web_points(91)
        c.n3 = Noise3(3, 128)
        drift = 0.02 * (B["lights"] - B["earth"])
        wx, wy = web_warp(c, g.x, g.y)
        pts = c.web_pts["pts"] + np.array([drift, -drift * 0.5], np.float32)
        f1, f2, f3 = worley3(pts, wx, wy)
        k = -(f3 - f1)
        loc = np.ones_like(k, bool)
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2):
                if dx or dy:
                    loc &= k >= np.roll(np.roll(k, dy, 0), dx, 1)
        loc &= k > -0.02
        ys, xs = np.nonzero(loc[3:-3, 3:-3])
        P = np.stack([g.x[ys + 3, xs + 3], g.y[ys + 3, xs + 3]], 1)
        _STARS = P[np.argsort(P[:, 0])].astype(np.float32)
    return _STARS


def half_grid(c):
    if getattr(c, "_hg", None) is None:
        c._hg = Grid(c.g.w // 2, c.g.h // 2)
    return c._hg


def up2(a, g):
    a = np.repeat(np.repeat(a, 2, 0), 2, 1)
    out = np.zeros((g.h, g.w) + a.shape[2:], np.float32)
    out[:min(g.h, a.shape[0]), :min(g.w, a.shape[1])] = a[:g.h, :g.w]
    return blur(out, 1)


def web_colour(dens, knots, warm=0.0):
    """Gas glows warm where it's thin and white-blue where it gathers."""
    lo = np.array([0.55, 0.35, 0.65], np.float32)
    mid = np.array([1.0, 0.78, 0.55], np.float32)
    hi = np.array([0.85, 0.92, 1.0], np.float32)
    d = np.clip(dens * 2.2, 0, 1)[..., None]
    col = lo * (1 - d) + mid * d
    col = col * (1 - knots[..., None] * 0.6) + hi * knots[..., None] * 0.6
    return col * dens[..., None]


def beat_earth(c: Ctx, t):
    g = c.g
    te = t - B["earth"]
    draw = sstep(0.0, 8.0, te)
    knot = sstep(3.0, 10.0, te)
    hg = half_grid(c)
    dens, knots = cosmic_web(c, hg.x, hg.y, t, draw, knot)
    img = up2(web_colour(dens, knots), g)
    img = img * 1.2 + light_bloom(img * 0.2, g) * 0.5
    # ours, the atom, as we pull back from it into the gas
    k = sstep(0.0, 6.0, te)
    sc = 1.0 - 0.85 * k
    amp = 1.0 - sstep(3.0, 7.0, te)
    if amp > 0:
        cols = [(1.0, 0.95, 0.85), (0.95, 0.6, 1.0), (0.6, 0.9, 1.0)]
        for kk, (ox, oy) in enumerate([(0.0, -0.5), (-0.5, 0.45), (0.5, 0.45)]):
            x_, y_ = ox * 0.11 * 0.45 * 1.4 * sc, oy * 0.11 * 0.45 * 1.4 * sc
            img += gray(gauss(g, x_, y_, 0.03 * sc + 0.004, 0.03 * sc + 0.004)) * np.array(cols[kk], np.float32) * 1.3 * amp
        a = t * 11.0
        img += gray(gauss(g, np.cos(a) * 0.32 * sc, np.sin(a) * 0.32 * sc, 0.012, 0.012)) * np.array([0.7, 0.85, 1.0], np.float32) * 1.2 * amp
        ring = np.abs(np.sqrt(g.x ** 2 + g.y ** 2) - 0.32 * sc)
        img += gray(np.exp(-0.5 * (ring / 0.006) ** 2)) * 0.12 * amp
    # the last of the protons, far off
    cam_z = (B["land"] - B["vault"]) * 0.35 + (B["earth"] - B["land"]) * 0.18 + te * 0.1
    img += proton_layer(c, t, cam_z, 1.0, 1.0, 1.0, bright=0.4 * (1 - draw * 0.7))
    return np.clip(img, 0, 1.2)


# ----------------------------------------------------------------------------- beat 8: lights

def star_sprite(img, g, x, y, amp, col, core=0.010, halo=0.07, spikes=0.0, zoom=1.0):
    """A star: a hard core, a soft halo and, for the bright ones, four thin spikes. Drawn in a window."""
    if amp <= 0.002:
        return img
    H, W = g.h, g.w
    R = (halo * 3.2 + spikes * 0.4) * zoom
    cx = (x / g.aspect + 1) * 0.5 * W
    cy = (1 - y) * 0.5 * H
    rp = int(R * H / 2) + 2
    x0, x1 = max(int(cx) - rp, 0), min(int(cx) + rp + 1, W)
    y0, y1 = max(int(cy) - rp, 0), min(int(cy) + rp + 1, H)
    if x1 <= x0 or y1 <= y0:
        return img
    gx = g.x[y0:y1, x0:x1] - x
    gy = g.y[y0:y1, x0:x1] - y
    r2 = gx * gx + gy * gy
    v = np.exp(-r2 / (2 * (core * zoom) ** 2)) * 1.6 + np.exp(-r2 / (2 * (halo * zoom) ** 2)) * 0.35
    if spikes > 0:
        sw = 0.0025 * zoom
        L = spikes * zoom
        v += (np.exp(-gy * gy / (2 * sw * sw)) * np.exp(-np.abs(gx) / (L * 0.35)) +
              np.exp(-gx * gx / (2 * sw * sw)) * np.exp(-np.abs(gy) / (L * 0.35))) * 0.5
    img[y0:y1, x0:x1] += v[..., None] * np.asarray(col, np.float32) * amp
    return img


def beat_lights(c: Ctx, t):
    g = c.g
    tl = t - B["lights"]
    W = c.web_pts
    stars = web_stars()
    n = len(stars)
    ign, burst, burst_t = W["ignite"][:n], W["burst"][:n], W["burst_t"][:n]
    d_now = 0.02 * (t - B["earth"])
    d_ref = 0.02 * (B["lights"] - B["earth"])
    sp = stars + np.array([d_now - d_ref, -(d_now - d_ref) * 0.5], np.float32)
    target = int(np.argmin(sp[:, 0] ** 2 + sp[:, 1] ** 2))
    fall = sstep(8.0, 12.0, tl)
    zoom = np.exp(fall * 6.0)
    tx, ty = sp[target]
    cx, cy = tx * fall, ty * fall
    if fall < 1.0:
        hg = half_grid(c)
        dens, knots = cosmic_web(c, hg.x / zoom + cx, hg.y / zoom + cy, t, 1.0, 1.0)
        img = up2(web_colour(dens, knots), g) * 1.2
        img = img + light_bloom(img * 0.2, g) * 0.5
        # the stars: blue-white points coming on along the threads, first one, then all of them
        for i in range(n):
            age = tl - float(ign[i])
            if age < 0:
                continue
            x_ = (sp[i, 0] - cx) * zoom
            y_ = (sp[i, 1] - cy) * zoom
            amp = sstep(0.0, 0.5, age) * (1.0 + 0.6 * np.exp(-age * 3.0))  # each one flares as it lights
            if burst[i] and age > burst_t[i]:
                ba = age - float(burst_t[i])
                # the burst: a shell thrown off, and the star gone; what it threw gathers and lights again
                rr = np.sqrt((g.x - x_) ** 2 + (g.y - y_) ** 2)
                shell = np.exp(-0.5 * ((rr - ba * 0.22 * zoom) / (0.015 * zoom + 0.01 * ba * zoom)) ** 2)
                shell = shell * (0.6 + 0.4 * c.vn.sample(np.arctan2(g.y - y_, g.x - x_) * 8 + i, ba * 2.0))
                img += shell[..., None] * np.array([1.0, 0.55, 0.45], np.float32) * max(0.0, 1 - ba * 0.6) * 0.8
                img = star_sprite(img, g, x_, y_, np.exp(-ba * 5.0) * 4.0, (1.0, 0.95, 0.9), zoom=zoom)
                amp = amp * max(0.0, 1 - ba * 3.0)
                if ba > 1.2:
                    img = star_sprite(img, g, x_ + 0.15 * zoom, y_ - 0.08 * zoom, sstep(1.2, 2.2, ba), (0.8, 0.9, 1.0), zoom=zoom)
            if i == target:
                amp = max(amp, sstep(5.0, 7.0, tl))
            big = 0.05 + 0.05 * ((i * 7) % 5) / 4
            img = star_sprite(img, g, x_, y_, amp, (0.85, 0.92, 1.0), halo=big, spikes=0.10 if (i % 3 == 0) else 0.0, zoom=zoom)
        # the glare fills the frame as we fall in
        img += gray(gauss(g, 0, 0, 0.9, 0.9)) * np.array([1.0, 0.85, 0.6], np.float32) * fall ** 2 * 2.0
        return np.clip(img, 0, 1.2)
    ti = tl - 12.0
    return star_interior(c, t, ti)


def granulation(c, x, y, t):
    """The inside of a star boiling: bright rising cells, darker lanes where the gas sinks, all moving."""
    wx = x + 0.15 * (c.n3.sample(x * 2 + 1, y * 2, t * 0.9, octaves=3) - 0.5)
    wy = y + 0.15 * (c.n3b.sample(x * 2 - 2, y * 2, t * 0.9, octaves=3) - 0.5)
    f1, f2 = worley(_WEB_FINE[:90] * 0.8, wx, wy)
    cell = np.clip((f2 - f1) / 0.25, 0, 1) ** 0.35
    return cell


def star_interior(c: Ctx, t, ti):
    """Violent: the electron torn away, bare nuclei slamming past in the glare, ours hits another and
    holds, hits a third, and a photon comes off. ti runs 0..8."""
    g = c.g
    hg = half_grid(c)
    zoomv = 1.0 + ti * 0.08
    gr = granulation(c, hg.x / zoomv, hg.y / zoomv, t)
    turb = c.n3.sample(hg.x * 2.0, hg.y * 2.0, t * 1.5, octaves=3)
    heat = np.clip(0.55 + 0.35 * gr + 0.5 * (turb - 0.5), 0, 1.2)
    col = np.stack([np.ones_like(heat) * 1.05, 0.30 + 0.62 * heat ** 1.5, 0.05 + 0.55 * heat ** 3], -1) * (0.55 + 0.5 * heat[..., None])
    img = up2(col, g) * 0.9
    # nuclei streaking past, each drawn along its own motion
    r = rng(1234)
    nn = 700
    bx = r.uniform(-2.2, 2.2, nn).astype(np.float32)
    by = r.uniform(-1.3, 1.3, nn).astype(np.float32)
    vx = r.uniform(-2.5, 2.5, nn).astype(np.float32)
    vy = r.uniform(-2.0, 2.0, nn).astype(np.float32)
    ph = r.uniform(0, 2, nn).astype(np.float32)
    cols = np.tile(np.array([[1.0, 0.97, 0.9]], np.float32), (nn, 1))
    for k in range(4):
        tt = t - k * 0.008
        xs = ((bx + vx * (tt + ph) + 2.2) % 4.4) - 2.2
        ys = ((by + vy * (tt + ph) + 1.3) % 2.6) - 1.3
        img += splat(g, xs, ys, cols, np.ones(nn, np.float32) * 0.35, radius_px=2.0 * g.h / 540, glow_px=6 * g.h / 540)
    for (ox, oy) in [(0.0, -0.035), (-0.035, 0.03), (0.035, 0.03)]:
        img += gray(gauss(g, ox, oy, 0.03, 0.03)) * 1.6
    if 0.5 < ti < 2.5:
        k = (ti - 0.5) / 2.0
        img += gray(gauss(g, 0.3 + k * 2.0, 0.1 + k * 0.6, 0.012, 0.012)) * np.array([0.7, 0.85, 1.0], np.float32) * (1 - k)
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
                rr = np.sqrt(g.x ** 2 + g.y ** 2)
                ring = np.exp(-0.5 * ((rr - (ti - arrive) * 1.2) / 0.05) ** 2) * fl
                img += gray(ring) * 0.5
    if ti > 6.0:
        k = ti - 6.0
        px = k * 0.9
        img += gray(gauss(g, px, px * 0.3, 0.014, 0.014)) * 2.0
        img += gray(gauss(g, px, px * 0.3, 0.06, 0.06)) * 0.5
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
