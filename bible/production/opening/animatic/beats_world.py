"""Beats 10-14 of the Opening: the sea, the land, dust, the band, the cliff.

These are animatic placeholders: flat silhouettes and gradients standing where the Blender or
MetaHuman build will go (DOSSIER §6, "How I'd build it"). What they fix is the timing, the
staging and the direction of every movement, which is what the storyboard is for.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from common import (Grid, smoothstep, sstep, lerp, ease_in_out, disc, gauss, blur, hsv, gray, over,
                    over_img, add, rng, Static)
import face as F
import facemesh as FM
from beats_abstract import B, Ctx, draw_cell, splat, SMALL

# ------------------------------------------------------------------ a silhouette canvas (PIL)

class Canvas:
    def __init__(self, g: Grid):
        self.g = g
        self.im = Image.new("L", (g.w, g.h), 0)
        self.d = ImageDraw.Draw(self.im)

    def P(self, x, y):
        g = self.g
        return ((x / g.aspect + 1) * 0.5 * g.w, (1 - y) * 0.5 * g.h)

    def W(self, w):
        return max(1, int(w * self.g.h / 2))

    def poly(self, pts, v=255):
        self.d.polygon([self.P(*p) for p in pts], fill=v)

    def ellipse(self, cx, cy, rx, ry, v=255):
        x0, y0 = self.P(cx - rx, cy + ry)
        x1, y1 = self.P(cx + rx, cy - ry)
        self.d.ellipse([x0, y0, x1, y1], fill=v)

    def line(self, pts, w, v=255):
        self.d.line([self.P(*p) for p in pts], fill=v, width=self.W(w), joint="curve")

    def mask(self, soft_px=0.0):
        m = np.asarray(self.im, np.float32) / 255.0
        if soft_px > 0:
            m = blur(m, soft_px)
        return m


def sky(g: Grid, top, bottom, horizon=0.0, power=1.0):
    k = np.clip((g.y - horizon) / (1 - horizon + 1e-6), 0, 1) ** power
    top = np.asarray(top, np.float32)
    bottom = np.asarray(bottom, np.float32)
    return bottom + (top - bottom) * k[..., None]


def ground(g: Grid, near, far, horizon=0.0):
    k = np.clip((horizon - g.y) / (horizon + 1 + 1e-6), 0, 1)
    near = np.asarray(near, np.float32)
    far = np.asarray(far, np.float32)
    return far + (near - far) * k[..., None]


class WCtx:
    def __init__(self, g: Grid, c: Ctx):
        self.g = g
        self.c = c
        self.r = rng(2026)
        self.static = Static(9, 1024)
        # feature points for the band: trunks, figures, the delta
        self.trunks = self.r.uniform(-2.5, 2.5, 60).astype(np.float32)
        self.trunk_w = self.r.uniform(0.04, 0.12, 60).astype(np.float32)
        self.delta = make_delta(self.r)
        self.flock = self.r.random((900, 3)).astype(np.float32)
        self.insects = self.r.random((60, 4)).astype(np.float32)
        self.ash = self.r.random((400, 3)).astype(np.float32)
        self.stars = self.r.random((300, 3)).astype(np.float32)
        self.fire = self.r.random((400, 3)).astype(np.float32)
        self.flowers = self.r.random((160, 3)).astype(np.float32)
        self.fern_pts = self.r.random((40, 3)).astype(np.float32)


def make_delta(r):
    """Braided channels: a river entering from the bottom and splitting into many as it goes north."""
    segs = []  # (x0, y0, x1, y1, width)

    def grow(x, y, ang, w, depth):
        if depth > 7 or w < 0.004:
            return
        L = 0.10 + 0.08 * r.random()
        nx, ny = x + np.cos(ang) * L, y + np.sin(ang) * L
        segs.append((x, y, nx, ny, w))
        if r.random() < 0.55 and depth > 0:
            grow(nx, ny, ang + r.uniform(0.15, 0.6), w * 0.7, depth + 1)
            grow(nx, ny, ang - r.uniform(0.15, 0.6), w * 0.7, depth + 1)
        else:
            grow(nx, ny, ang + r.uniform(-0.25, 0.25), w * 0.92, depth + 1)

    for k in range(3):
        grow(0.0, 0.0, np.pi / 2 + r.uniform(-0.3, 0.3), 0.06, 0)
    return segs


# ------------------------------------------------------------------ beat 10: the waters swarm

def water_bg(w: WCtx, t, depth=0.5, flicker=0.0):
    g, c = w.g, w.c
    n = c.n3.sample(g.x * 1.8, g.y * 1.8 - t * 0.2, t * 0.25, octaves=3)
    day = 0.5 + 0.5 * np.sin(t * flicker * 2 * np.pi) if flicker > 0 else 1.0
    light = 0.45 + 0.55 * day
    base = np.stack([0.05 + 0.08 * n, 0.33 + 0.22 * n, 0.26 + 0.14 * n], axis=-1) * light * (1 - 0.3 * depth)
    rays = np.clip(np.sin(g.x * 9 + n * 4 + t * 0.7) * 0.5 + 0.5, 0, 1) * np.clip(g.y + 0.9, 0, 1.3) * 0.18 * light
    return base + gray(rays)


def creature_mask(w: WCtx, kind, cx, cy, s, t, facing=1):
    """Silhouettes of the line of descent: a soft swimmer with eyes, a fish, a four-legged thing,
    a lizard, a small furred creature. Returns (body mask, eye mask)."""
    cv = Canvas(w.g)
    ev = Canvas(w.g)
    f = facing
    if kind == "swimmer":
        # seen head-on: a rounded head, the body tapering away behind
        cv.ellipse(cx, cy, 0.42 * s, 0.34 * s)
        cv.ellipse(cx, cy - 0.15 * s, 0.22 * s, 0.4 * s)
        for sgn in (-1, 1):
            ev.ellipse(cx + sgn * 0.17 * s, cy + 0.08 * s, 0.06 * s, 0.06 * s)
    elif kind == "fish":
        wag = 0.08 * np.sin(t * 9)
        pts = [(-0.5, 0.0), (-0.2, 0.22), (0.25, 0.2), (0.5, 0.05), (0.5, -0.05), (0.25, -0.2), (-0.2, -0.22)]
        cv.poly([(cx + f * x * s, cy + y * s) for x, y in pts])
        cv.poly([(cx - f * 0.45 * s, cy), (cx - f * 0.75 * s, cy + (0.25 + wag) * s), (cx - f * 0.75 * s, cy - (0.25 - wag) * s)])
        cv.poly([(cx + f * 0.0 * s, cy + 0.18 * s), (cx - f * 0.2 * s, cy + 0.4 * s), (cx - f * 0.3 * s, cy + 0.15 * s)])
        ev.ellipse(cx + f * 0.35 * s, cy + 0.06 * s, 0.045 * s, 0.045 * s)
    elif kind == "tetrapod":
        pts = [(-0.6, 0.0), (-0.3, 0.16), (0.3, 0.18), (0.6, 0.1), (0.62, -0.02), (0.3, -0.12), (-0.3, -0.12)]
        cv.poly([(cx + f * x * s, cy + y * s) for x, y in pts])
        for i, lx in enumerate((-0.25, 0.25)):
            ph = t * 6 + i * np.pi
            cv.line([(cx + f * lx * s, cy - 0.08 * s), (cx + f * (lx + 0.15 * np.sin(ph)) * s, cy - 0.3 * s)], 0.07 * s)
        cv.poly([(cx - f * 0.58 * s, cy + 0.05 * s), (cx - f * 0.95 * s, cy - 0.05 * s), (cx - f * 0.58 * s, cy - 0.06 * s)])
        ev.ellipse(cx + f * 0.45 * s, cy + 0.06 * s, 0.035 * s, 0.035 * s)
    elif kind == "lizard":
        pts = [(-0.7, 0.0), (-0.3, 0.1), (0.35, 0.12), (0.7, 0.05), (0.72, -0.03), (0.35, -0.08), (-0.3, -0.08)]
        cv.poly([(cx + f * x * s, cy + y * s) for x, y in pts])
        for i, lx in enumerate((-0.3, 0.3)):
            ph = t * 10 + i * np.pi
            cv.line([(cx + f * lx * s, cy - 0.05 * s), (cx + f * (lx + 0.2 * np.sin(ph)) * s, cy - 0.22 * s)], 0.05 * s)
            cv.line([(cx + f * lx * s, cy - 0.05 * s), (cx + f * (lx - 0.2 * np.sin(ph)) * s, cy - 0.22 * s)], 0.05 * s)
        cv.line([(cx - f * 0.68 * s, cy), (cx - f * 1.3 * s, cy - 0.05 * s + 0.05 * s * np.sin(t * 5))], 0.05 * s)
        ev.ellipse(cx + f * 0.55 * s, cy + 0.04 * s, 0.03 * s, 0.03 * s)
    elif kind == "shrew":
        pts = [(-0.5, 0.05), (-0.3, 0.25), (0.2, 0.28), (0.55, 0.12), (0.75, 0.02), (0.55, -0.08), (0.1, -0.12), (-0.4, -0.1)]
        cv.poly([(cx + f * x * s, cy + y * s) for x, y in pts])
        for lx in (-0.25, 0.3):
            cv.line([(cx + f * lx * s, cy - 0.05 * s), (cx + f * lx * s, cy - 0.22 * s)], 0.05 * s)
        cv.line([(cx - f * 0.48 * s, cy), (cx - f * 0.9 * s, cy - 0.15 * s)], 0.025 * s)
        cv.ellipse(cx + f * 0.35 * s, cy + 0.3 * s, 0.06 * s, 0.07 * s)  # an ear
        ev.ellipse(cx + f * 0.5 * s, cy + 0.1 * s, 0.03 * s, 0.03 * s)
    return cv.mask(0.8), ev.mask(0.5)


def beat_swarm(w: WCtx, t):
    g, c = w.g, w.c
    ts = t - B["swarm"]
    # day and night flicker: starts slow, quickens, then settles into time skipping
    flick = 0.6 + 2.5 * sstep(2.0, 9.0, ts)
    if ts > 12:
        flick = 0.0
    img = water_bg(w, t, depth=0.4, flicker=flick)

    if ts < 11.0:
        # the cell divides, again and again; we stay with one line
        times = [2.0, 4.4, 6.2, 7.6, 8.7, 9.6, 10.3]
        n_done = sum(1 for x in times if ts > x + 0.5)
        # background cells from earlier divisions drift off
        for i in range(n_done):
            k = ts - times[i] - 0.5
            ang = 0.6 + i * 1.3
            r_ = 0.22 * (0.9 ** (i + 1))
            img = draw_cell(c, img, 0.3 + np.cos(ang) * (0.25 + k * 0.08), np.sin(ang) * (0.2 + k * 0.08), r_ * 0.7, t, tint=(0.8, 0.8, 0.6))
        r_ = 0.22 * (0.93 ** n_done)
        # a division in progress: stretch, pinch, split
        stretch, split = 0.0, None
        for x in times:
            if x - 0.6 < ts < x + 0.5:
                k = (ts - (x - 0.6)) / 1.1
                stretch = 0.9 * np.sin(np.pi * min(k, 0.6) / 0.6) if k < 0.6 else 0.0
                split = (k - 0.6) / 0.4 if k >= 0.6 else None
        if split is None:
            img = draw_cell(c, img, 0.0, 0.0, r_, t, lit=max(0.0, 1 - ts), stretch=stretch, ang=0.4)
        else:
            d = 0.12 + 0.3 * split
            img = draw_cell(c, img, 0.0, 0.0, r_ * 0.93, t, tint=(0.95, 0.9, 0.7))
            img = draw_cell(c, img, 0.3 + d * 0.8, d * 0.4, r_ * 0.9, t, tint=(0.8, 0.8, 0.6))
        return np.clip(img, 0, 1)

    if ts < 18.0:
        # something far larger closes around our cell and swallows it whole
        k = sstep(11.0, 14.0, ts)
        hx = lerp(-1.6, 0.05, k)
        hy = lerp(0.6, 0.02, k)
        host_r = 0.55
        hv = Canvas(g)
        hv.ellipse(hx, hy, host_r * 1.1, host_r * 0.95)
        hm = hv.mask(2.0)
        img = over_img(img, hm * 0.75, gray(np.ones_like(hm)) * np.array([0.72, 0.68, 0.5], np.float32))
        rim = np.exp(-0.5 * ((np.sqrt(((g.x - hx) / 1.1) ** 2 + ((g.y - hy) / 0.95) ** 2) - host_r) / 0.012) ** 2)
        img = add(img, rim * 0.5, (0.9, 0.9, 0.7))
        # ours settles inside and goes on dividing in step with its host
        cx_ = lerp(0.0, -0.15, sstep(14.0, 16.0, ts))
        stretch = 0.6 * max(0.0, np.sin((ts - 16.0) * 3.0)) if ts > 16 else 0.0
        img = draw_cell(c, img, cx_, 0.0, 0.17, t, stretch=stretch, ang=0.4)
        img = over(img, disc(g, hx + 0.2, hy + 0.1, 0.1) * 0.4, (0.5, 0.45, 0.3))
        return np.clip(img, 0, 1)

    if ts < 22.0:
        # clumps, sheets, bodies: cells that divide and hold together
        k = ts - 18.0
        n = int(min(2 ** (k * 1.2 + 1), 64))
        cv = Canvas(g)
        rr = rng(5)
        for i in range(n):
            a = i * 2.399
            rad = 0.12 * np.sqrt(i / max(n, 1)) * (1 + 0.3 * rr.random())
            rad = rad * (1 + 1.5 * sstep(2.5, 4.0, k))  # stretching into a body with a front and a back
            cv.ellipse(np.cos(a) * rad * (1 + sstep(2.5, 4.0, k)), np.sin(a) * rad * 0.6, 0.075, 0.07)
        m = cv.mask(1.5)
        img = over_img(img, m * 0.9, gray(np.ones_like(m)) * np.array([0.85, 0.82, 0.62], np.float32))
        return np.clip(img, 0, 1)

    if ts < 26.0:
        # a small, soft, swimming thing, with a rod down its back and two eyes: a face
        k = ts - 22.0
        sway = 0.04 * np.sin(t * 3.0)
        body, eyes = creature_mask(w, "swimmer", sway, -0.05, 0.5 + 0.1 * sstep(0, 2, k), t)
        img = over(img, body * 0.9, (0.55, 0.5, 0.42))
        img = over(img, eyes, (0.03, 0.03, 0.03))
        # the rod
        cv = Canvas(g)
        cv.line([(sway, 0.1), (sway, -0.6)], 0.012)
        img = over(img, cv.mask(0.8) * 0.5, (0.3, 0.28, 0.22))
        return np.clip(img, 0, 1)

    if ts < 29.5:
        # fish; behind it, something far bigger, armored and jawed. Ours gets away.
        k = ts - 26.0
        img = water_bg(w, t, depth=0.6)
        bx = lerp(1.6, -2.4, sstep(0.0, 3.5, k))
        bv = Canvas(g)
        pts = [(-1.3, 0.0), (-0.7, 0.35), (0.3, 0.45), (0.95, 0.3), (1.2, 0.05), (1.0, -0.25), (0.3, -0.42), (-0.7, -0.35)]
        bv.poly([(bx + x, 0.15 + y * 0.9) for x, y in pts])
        bv.poly([(bx - 1.25, 0.15), (bx - 1.9, 0.5), (bx - 1.9, -0.2)])
        jaw = 0.12 * max(0.0, np.sin(k * 3.0))
        bv.poly([(bx + 0.5, 0.0), (bx + 1.25, -0.05 - jaw), (bx + 0.5, -0.3)], v=0)
        big = bv.mask(3.0)
        img = over(img, big * 0.85, (0.08, 0.14, 0.14))
        esc = sstep(1.2, 2.6, k)
        fx = lerp(0.0, -0.9, esc) + 0.05 * np.sin(t * 7)
        fy = lerp(-0.1, 0.55, esc)
        body, eye = creature_mask(w, "fish", fx, fy, 0.5, t, facing=-1)
        img = over(img, body * 0.92, (0.45, 0.42, 0.35))
        img = over(img, eye, (0.03, 0.03, 0.03))
        return np.clip(img, 0, 1)

    # the shallows, seen from below: the bright skin of the surface, and small shadows with wings
    k = ts - 29.5
    img = water_bg(w, t, depth=0.1)
    n = c.n3.sample(g.x * 2.5, g.y * 4.0, t * 0.8, octaves=3)
    surface = smoothstep(0.35, 0.75, g.y + 0.25 * n)
    bright = np.stack([0.75 + 0.2 * n, 0.9 + 0 * n, 0.95 + 0 * n], axis=-1)
    img = over_img(img, surface, bright)
    caust = np.clip(np.sin(g.x * 14 + n * 9 + t * 2) * np.sin(g.y * 11 - n * 7 - t * 1.6), 0, 1) ** 2 * 0.25
    img = add(img, caust * (1 - surface), (1.0, 1.0, 0.9))
    cv = Canvas(g)
    for i in range(14):
        ph = i * 1.7
        wx = ((i * 0.37 + t * (0.5 + 0.1 * (i % 3))) % 4.0) - 2.0
        wy = 0.45 + 0.35 * np.sin(ph + t * 0.6)
        flap = 0.12 * np.sin(t * 14 + ph)
        s = 0.06 + 0.03 * (i % 3)
        cv.line([(wx - s, wy + flap * s * 3), (wx, wy), (wx + s, wy + flap * s * 3)], 0.012)
    img = over(img, cv.mask(1.0) * 0.55 * sstep(0.3, 1.5, k), (0.2, 0.25, 0.25))
    body, eye = creature_mask(w, "fish", -0.1 + 0.03 * np.sin(t * 5), -0.45, 0.45, t, facing=-1)
    img = over(img, body * 0.9, (0.3, 0.3, 0.25))
    img = over(img, eye, (0.03, 0.03, 0.03))
    return np.clip(img, 0, 1)


# ------------------------------------------------------------------ beat 11: the land

def ferns(w: WCtx, t, n, scale, y0, color, img, sway=0.02, seed=0, growth=1.0):
    g = w.g
    cv = Canvas(g)
    r = rng(seed + 3)
    for i in range(n):
        bx = r.uniform(-2.0, 2.0)
        by = y0 + r.uniform(-0.05, 0.05)
        h = scale * r.uniform(0.6, 1.3) * growth
        lean = r.uniform(-0.5, 0.5) + sway * np.sin(t * 1.5 + i)
        n_leaf = 7
        tip = (bx + lean * h, by + h)
        cv.line([(bx, by), tip], 0.01 * scale)
        for j in range(1, n_leaf + 1):
            f = j / (n_leaf + 1)
            px = bx + lean * h * f
            py = by + h * f
            L = h * 0.35 * (1 - f) + 0.02
            cv.line([(px, py), (px - L, py + L * 0.6)], 0.012 * scale)
            cv.line([(px, py), (px + L, py + L * 0.6)], 0.012 * scale)
    return over(img, cv.mask(0.8) * 0.95, color)


def night_sky(w: WCtx, t, amount):
    g = w.g
    img = sky(g, (0.02, 0.03, 0.08), (0.05, 0.06, 0.12), horizon=-0.2)
    st = w.stars
    xs = (st[:, 0] * 2 - 1) * g.aspect
    ys = st[:, 1] * 1.2 - 0.1
    cols = np.tile(np.array([[0.9, 0.9, 1.0]], np.float32), (len(st), 1))
    img += splat(g, xs, ys, cols, (0.3 + 0.7 * st[:, 2]) * amount, radius_px=1.0 * g.h / 540, glow_px=0)
    return img


def beat_land(w: WCtx, t):
    g, c = w.g, w.c
    tl = t - B["landbeat"]
    if tl < 8.0:
        # shallows, mud, air. The creature hauls out onto a shore; the air alive with wings
        day = sky(g, (0.75, 0.85, 0.95), (0.95, 0.9, 0.8), horizon=0.1)
        img = day
        n = c.n3.sample(g.x * 2, g.y * 6, t * 0.4, octaves=3)
        water = np.stack([0.35 + 0.1 * n, 0.5 + 0.1 * n, 0.5 + 0.08 * n], axis=-1)
        wmask = (1 - smoothstep(-0.2, 0.12, g.y)) * smoothstep(-1.0, -0.2 + 0.4 * (g.x + 1.0), g.x)
        img = over_img(img, wmask, water)
        mud = np.stack([0.45 + 0.1 * n, 0.38 + 0.08 * n, 0.3 + 0.05 * n], axis=-1)
        mmask = (1 - smoothstep(-0.25, 0.1, g.y)) * (1 - wmask)
        img = over_img(img, mmask, mud)
        # insects glinting
        ins = w.insects
        xs = (ins[:, 0] * 2 - 1) * g.aspect + 0.15 * np.sin(t * (3 + 4 * ins[:, 2]) + ins[:, 3] * 9)
        ys = ins[:, 1] * 0.8 - 0.1 + 0.1 * np.cos(t * (2 + 5 * ins[:, 3]))
        glint = (np.sin(t * 25 + ins[:, 2] * 40) > 0.6).astype(np.float32)
        cols = np.tile(np.array([[1.0, 1.0, 0.9]], np.float32), (len(ins), 1))
        img += splat(g, xs, ys, cols, 0.25 + 0.9 * glint, radius_px=1.0 * g.h / 540, glow_px=2 * g.h / 540)
        # plants hold their shapes
        img = ferns(w, t, 12, 0.35, -0.35, (0.2, 0.32, 0.15), img, seed=1)
        # the creature: fins that push like legs, hauling from the water (right) onto the mud
        k = sstep(0.5, 6.0, tl)
        cx = lerp(0.9, -0.3, k)
        cy = lerp(-0.25, -0.45, k)
        kind = "fish" if tl < 2.5 else "tetrapod"
        body, eye = creature_mask(w, kind, cx, cy, 0.5, t, facing=-1)
        img = over(img, body * 0.95, (0.22, 0.2, 0.15))
        img = over(img, eye, (0.02, 0.02, 0.02))
        img = ferns(w, t, 6, 0.5, -0.8, (0.12, 0.22, 0.1), img, seed=2)
        return np.clip(img, 0, 1)

    if tl < 12.0:
        # lizard-shaped now, low and quick, among ferns
        k = tl - 8.0
        img = sky(g, (0.7, 0.8, 0.9), (0.9, 0.85, 0.7), horizon=0.2)
        img = over_img(img, 1 - smoothstep(0.1, 0.25, g.y), np.stack([0.4 + 0.0 * g.x, 0.36 + 0.0 * g.x, 0.25 + 0.0 * g.x], axis=-1))
        img = ferns(w, t, 20, 0.5, -0.4, (0.18, 0.3, 0.12), img, seed=4)
        cx = -1.4 + 0.75 * k
        body, eye = creature_mask(w, "lizard", cx, -0.5, 0.45, t, facing=1)
        img = over(img, body * 0.95, (0.12, 0.12, 0.08))
        img = over(img, eye, (0.02, 0.02, 0.02))
        img = ferns(w, t, 10, 0.75, -0.9, (0.1, 0.2, 0.08), img, seed=5)
        return np.clip(img, 0, 1)

    if tl < 19.5:
        # night. Small, furred and sharp-nosed, at the feet of enormous animals. Wings cross the moon.
        k = tl - 12.0
        img = night_sky(w, t, 1.0)
        moon = disc(g, 1.0, 0.55, 0.13)
        img = over(img, moon, (0.92, 0.92, 0.85))
        # enormous animals: columns of legs, bodies above the frame
        cv = Canvas(g)
        for i, lx in enumerate((-1.3, -0.9, 0.5, 0.9)):
            sw = 0.03 * np.sin(t * 0.7 + i)
            cv.poly([(lx - 0.12 + sw, 1.0), (lx + 0.12 + sw, 1.0), (lx + 0.16, -0.35), (lx - 0.16, -0.35)])
        cv.poly([(-1.6, 1.0), (1.4, 1.0), (1.3, 0.55), (-1.5, 0.5)])
        img = over(img, cv.mask(2.0) * 0.97, (0.03, 0.03, 0.05))
        # ground
        img = over_img(img, 1 - smoothstep(-0.45, -0.3, g.y), np.stack([0.17 + 0 * g.x, 0.18 + 0 * g.x, 0.16 + 0 * g.x], axis=-1))
        # birds asleep in a branch
        bv = Canvas(g)
        bv.line([(-1.78, 0.1), (-1.0, 0.25), (-0.5, 0.2)], 0.02)
        for bx in (-1.4, -1.15, -0.8):
            bv.ellipse(bx, 0.17 + 0.06 * (bx + 1.0), 0.04, 0.03)
        img = over(img, bv.mask(1.0) * 0.95, (0.02, 0.02, 0.03))
        # a pterosaur crosses the moon
        if 2.0 < k < 5.5:
            px = lerp(1.6, 0.3, (k - 2.0) / 3.5)
            py = 0.55 + 0.05 * np.sin(k * 2)
            flap = 0.18 * np.sin(k * 6)
            pv = Canvas(g)
            pv.poly([(px - 0.42, py + flap), (px - 0.1, py + 0.03), (px + 0.1, py + 0.03), (px + 0.42, py + flap), (px + 0.1, py - 0.04), (px + 0.2, py - 0.02), (px - 0.1, py - 0.04)])
            img = over(img, pv.mask(1.0) * 0.97, (0.02, 0.02, 0.03))
        # the small furred creature, moving in short bursts
        step = np.floor(k * 1.5)
        cx = -0.5 + 0.12 * step + 0.06 * sstep(0, 0.3, (k * 1.5) % 1)
        body, eye = creature_mask(w, "shrew", cx, -0.52, 0.32, t, facing=1)
        img = over(img, body * 0.97, (0.03, 0.03, 0.03))
        img = over(img, eye, (0.6, 0.6, 0.55))
        img = ferns(w, t, 8, 0.45, -0.95, (0.03, 0.05, 0.03), img, seed=6)
        return np.clip(img, 0, 1)

    # the dead animal, and the small creature on it; then its face fills the frame; then the sky falls
    k = tl - 19.5
    img = night_sky(w, t, 1.0)
    if k > 3.5:
        # a glow comes up low in the south where no dawn should be, and climbs
        gk = sstep(3.5, 7.5, k)
        glow = np.clip(1 - np.sqrt(((g.x + 1.2) / 2.2) ** 2 + ((g.y + 0.7) / (0.5 + 1.2 * gk)) ** 2), 0, 1) ** 1.5
        img = add(img, glow * gk, (0.9, 0.35, 0.08))
        heat = sstep(7.5, 9.5, k)
        img = img * (1 - 0.5 * heat) + np.array([0.9, 0.45, 0.15], np.float32) * heat * 0.5
    shake = 0.0
    if 6.3 < k < 8.0:
        shake = 0.02 * np.sin(t * 60) * (1 - (k - 6.3) / 1.7)
    img = over_img(img, 1 - smoothstep(-0.55 + shake, -0.4 + shake, g.y), np.stack([0.16 + 0 * g.x, 0.17 + 0 * g.x, 0.15 + 0 * g.x], axis=-1))
    img = triceratops(w, img, -0.1, -0.35 + shake, 1.0, (0.05, 0.05, 0.06), k)
    if k < 2.0:
        body, eye = creature_mask(w, "shrew", 0.15, -0.05 + shake, 0.3, t, facing=1)
        img = over(img, body * 0.97, (0.09, 0.08, 0.07))
        img = over(img, eye, (0.6, 0.6, 0.55))
    elif k < 3.5:
        # its face fills the frame: whiskers, black eyes, listening
        cv = Canvas(g)
        cv.ellipse(0.0, -0.1, 0.9, 0.75)
        cv.poly([(0.6, 0.35), (0.85, 0.95), (1.05, 0.3)])
        cv.poly([(-0.6, 0.35), (-0.85, 0.95), (-1.05, 0.3)])
        cv.ellipse(0.0, -0.55, 0.3, 0.2)
        img = over(img, cv.mask(2.0) * 0.97, (0.1, 0.09, 0.08))
        ev = Canvas(g)
        for sgn in (-1, 1):
            ev.ellipse(sgn * 0.42, 0.05, 0.12, 0.12)
        img = over(img, ev.mask(1.0), (0.02, 0.02, 0.02))
        wv = Canvas(g)
        for i in range(4):
            for sgn in (-1, 1):
                wv.line([(sgn * 0.25, -0.5 + 0.03 * i), (sgn * 1.7, -0.55 + 0.25 * (i - 1.5) + 0.02 * np.sin(t * 20 + i))], 0.006)
        img = over(img, wv.mask(0.5) * 0.6, (0.7, 0.7, 0.65))
        img = add(img, disc(g, 0.42, 0.05, 0.03) + disc(g, -0.42, 0.05, 0.03), (0.5, 0.5, 0.5))
    else:
        # it goes still; then runs for a hole among the roots, at 8 s
        if k < 8.0:
            body, eye = creature_mask(w, "shrew", 0.15, -0.05 + shake, 0.3, t, facing=-1)
            img = over(img, body * 0.97, (0.09, 0.08, 0.07))
            img = over(img, eye, (0.6, 0.6, 0.55))
        elif k < 9.5:
            rk = (k - 8.0) / 1.5
            body, eye = creature_mask(w, "shrew", 0.15 - 1.9 * rk, -0.05 - 0.45 * rk, 0.3, t, facing=-1)
            img = over(img, body * 0.97, (0.09, 0.08, 0.07))
    if k > 8.0:
        # the sky starts to fall: one streak, then dozens, then the whole sky streaming down
        img = falling_sky(w, img, k - 8.0, t)
    return np.clip(img, 0, 1)


def triceratops(w: WCtx, img, cx, cy, s, color, k):
    """A huge horned head lying on its side in the ferns, the frill up, the beak toward us."""
    cv = Canvas(w.g)
    pts = [(-1.5, -0.1), (-1.3, 0.4), (-0.9, 0.75), (-0.4, 0.85), (0.0, 0.7), (0.3, 0.55), (0.6, 0.3), (1.0, 0.1), (1.25, -0.05), (1.1, -0.25), (0.6, -0.35), (0.0, -0.4), (-0.8, -0.45), (-1.4, -0.4)]
    cv.poly([(cx + x * s, cy + y * s) for x, y in pts])
    # horns
    cv.poly([(cx + 0.25 * s, cy + 0.5 * s), (cx + 0.75 * s, cy + 1.05 * s), (cx + 0.45 * s, cy + 0.35 * s)])
    cv.poly([(cx + 0.55 * s, cy + 0.3 * s), (cx + 1.1 * s, cy + 0.75 * s), (cx + 0.75 * s, cy + 0.15 * s)])
    cv.poly([(cx + 1.0 * s, cy + 0.0 * s), (cx + 1.45 * s, cy + 0.1 * s), (cx + 1.15 * s, cy - 0.15 * s)])
    m = cv.mask(1.5)
    img = over(img, m * 0.97, color)
    # the eye socket, a little lighter
    img = add(img, disc(w.g, cx + 0.55 * s, cy + 0.05 * s, 0.07 * s) * 0.25, (0.5, 0.45, 0.4))
    return img


def falling_sky(w: WCtx, img, k, t):
    g = w.g
    n = int(min(1 + k * k * 25, 400))
    fr = w.fire[:n]
    cv = Canvas(g)
    for i in range(n):
        ph = (t * (1.5 + fr[i, 1] * 2) + fr[i, 2] * 7) % 2.4
        x = (fr[i, 0] * 2 - 1) * g.aspect * 1.2
        y0 = 1.3 - ph
        cv.line([(x + 0.15, y0 + 0.3), (x, y0)], 0.006 + 0.004 * fr[i, 1])
    m = cv.mask(1.0)
    img = add(img, m * 1.0, (1.0, 0.75, 0.35))
    img = add(img, blur(m, 6 * g.h / 540) * 0.6, (1.0, 0.4, 0.1))
    return img


# ------------------------------------------------------------------ beat 12: dust

def tree(w: WCtx, cv: Canvas, x, y, h, growth, depth=0, ang=np.pi / 2, width=0.03, seed=11):
    r = rng(abs(int(seed + depth * 31 + x * 100)) % 100000)
    L = h * growth
    if L < 0.005:
        return
    nx, ny = x + np.cos(ang) * L, y + np.sin(ang) * L
    cv.line([(x, y), (nx, ny)], width * max(growth, 0.3))
    if depth < 5 and growth > 0.5:
        g2 = (growth - 0.5) * 2
        for sgn in (-1, 1):
            tree(w, cv, nx, ny, h * 0.62, g2, depth + 1, ang + sgn * r.uniform(0.35, 0.8), width * 0.65, seed)


def beat_dust(w: WCtx, t):
    g, c = w.g, w.c
    td = t - B["dust"]
    # the sky: fire stops by 2 s; dark and stays dark; clears from 9 s; green comes back
    fire = 1 - sstep(0.5, 2.5, td)
    dark = sstep(1.0, 3.0, td) * (1 - sstep(9.0, 12.0, td))
    day = sstep(9.0, 12.5, td)
    skyc = sky(g, (0.65, 0.78, 0.9), (0.9, 0.85, 0.75), horizon=-0.1) * day + np.array([0.1, 0.08, 0.06], np.float32) * (1 - day)
    img = skyc * (1 - dark * 0.8)
    if fire > 0:
        img = img * (1 - 0.4 * fire) + np.array([0.9, 0.45, 0.15], np.float32) * fire * 0.4
    # ground: ash grey, then green
    gm = 1 - smoothstep(-0.55, -0.4, g.y)
    n = c.vn.fbm(g.x * 3, g.y * 3, 3)
    ashcol = np.stack([0.32 + 0.1 * n, 0.3 + 0.1 * n, 0.28 + 0.1 * n], axis=-1)
    green = sstep(10.0, 13.5, td)
    greencol = np.stack([0.25 + 0.1 * n, 0.4 + 0.15 * n, 0.15 + 0.05 * n], axis=-1)
    gcol = ashcol * (1 - green) + greencol * green
    gcol = gcol * (1 - dark * 0.7)
    img = over_img(img, gm, gcol)
    # the head: flesh goes, the skull shows, sinks into the ground
    decay = sstep(4.0, 8.0, td)
    sink = sstep(7.5, 11.0, td)
    cy = -0.35 - 0.7 * sink
    if sink < 1.0:
        col = (0.05 * (1 - decay) + 0.55 * decay, 0.05 * (1 - decay) + 0.52 * decay, 0.06 * (1 - decay) + 0.45 * decay)
        img = triceratops(w, img, -0.1, cy, 1.0 - 0.15 * decay, col, 0)
        if decay > 0.3:
            # sockets and the ridge of the skull
            sv = Canvas(g)
            sv.ellipse(-0.1 + 0.55, cy + 0.05, 0.12, 0.1)
            sv.ellipse(-0.1 - 0.2, cy - 0.05, 0.1, 0.07)
            img = over(img, sv.mask(1.0) * decay, (0.12, 0.1, 0.08))
        # ash settles on the face
        if td > 2.0:
            amt = sstep(2.0, 7.0, td)
            img = over(img, (1 - smoothstep(cy + 0.3, cy + 0.6, g.y)) * smoothstep(cy + 0.1, cy + 0.35, g.y) * amt * 0.5, (0.4, 0.4, 0.4))
    # ash falling
    if 1.5 < td < 9.0:
        a = w.ash
        xs = (a[:, 0] * 2 - 1) * g.aspect
        ys = ((a[:, 1] * 2.4 - (td - 1.5) * (0.15 + 0.15 * a[:, 2])) % 2.4) - 1.2
        cols = np.tile(np.array([[0.6, 0.6, 0.6]], np.float32), (len(a), 1))
        img += splat(g, xs, ys, cols, np.ones(len(a), np.float32) * 0.6 * sstep(1.5, 3.0, td) * (1 - sstep(7.0, 9.0, td)), radius_px=1.0 * g.h / 540)
    # the first green to come back is ferns, everywhere; then flowering things and trees
    if td > 10.0:
        img = ferns(w, t, 30, 0.4, -0.5, (0.2, 0.36, 0.14), img, seed=8, growth=sstep(10.0, 13.0, td))
    if td > 12.5:
        fl = w.flowers
        xs = (fl[:, 0] * 2 - 1) * g.aspect
        ys = fl[:, 1] * 0.5 - 0.95
        cols = hsv(fl[:, 2], 0.8, 1.0)
        img += splat(g, xs, ys, cols, np.ones(len(fl), np.float32) * sstep(12.5, 14.5, td), radius_px=1.6 * g.h / 540, glow_px=0)
        tv = Canvas(g)
        for i, tx in enumerate((-1.6, -1.2, 1.3, 1.65)):
            tree(w, tv, tx, -0.5, 0.6, sstep(12.5, 15.0, td), seed=20 + i, width=0.05)
        img = over(img, tv.mask(1.0) * 0.9, (0.1, 0.09, 0.06))
    # animals pass as blurs
    if 12.5 < td < 15.5:
        bv = Canvas(g)
        for i in range(3):
            ph = ((td - 12.5) * (1.5 + 0.5 * i) + i * 0.7) % 1.0
            bx = -2.2 + ph * 4.4 * (1 if i % 2 == 0 else -1) * 1
            bv.ellipse(bx, -0.55, 0.25, 0.08)
        img = over(img, blur(bv.mask(0), 14 * g.h / 540) * 0.7, (0.15, 0.12, 0.08))
    # where the head lay, a shoot: a sapling, then a tree, in a few seconds
    if td > 14.0:
        gr = sstep(14.0, 16.5, td)
        tv = Canvas(g)
        tree(w, tv, -0.1, -0.55, 0.45 + 0.5 * gr, gr, seed=5, width=0.03 + 0.03 * gr)
        img = over(img, tv.mask(1.0) * 0.95, (0.12, 0.1, 0.06))
        if gr > 0.6:
            # leaves
            lv = Canvas(g)
            r = rng(9)
            for i in range(int(60 * (gr - 0.6) / 0.4)):
                lv.ellipse(-0.1 + r.uniform(-0.55, 0.55), 0.1 + r.uniform(-0.3, 0.5), 0.05, 0.035)
            img = over(img, lv.mask(1.0) * 0.9, (0.2, 0.4, 0.14))
    # one leaf comes loose and falls into frame, and settles on the earth
    if td > 16.0:
        lk = sstep(16.0, 17.6, td)
        lx = 0.1 + 0.12 * np.sin(lk * 9) * (1 - lk)
        ly = lerp(0.55, -0.72, lk)
        lv = Canvas(g)
        rot = 0.6 * np.sin(lk * 7)
        pts = [(0, 0.05), (0.03, 0.02), (0.04, -0.02), (0, -0.06), (-0.04, -0.02), (-0.03, 0.02)]
        lv.poly([(lx + x * np.cos(rot) - y * np.sin(rot), ly + x * np.sin(rot) + y * np.cos(rot)) for x, y in pts])
        img = over(img, lv.mask(0.8) * 0.95, (0.5, 0.35, 0.12))
    return np.clip(img, 0, 1)


# ------------------------------------------------------------------ beat 13: fill the earth

def figure(cv: Canvas, x, y, s, phase, facing=-1, spear=False, walk=1.0, kneel=0.0, v=255):
    """A walking human silhouette, side on, height s, facing left (-1) or right (+1)."""
    f = facing
    bob = 0.02 * s * np.sin(phase * 2) * walk
    y = y + bob - 0.45 * s * kneel
    head = (x + 0.02 * f * s, y + 0.86 * s)
    cv.ellipse(head[0], head[1], 0.085 * s, 0.1 * s, v)
    hip = (x, y + 0.45 * s)
    sh = (x, y + 0.72 * s)
    cv.line([sh, hip], 0.14 * s, v)
    swing = 0.35 * np.sin(phase) * walk
    for sgn in (-1, 1):
        a = swing * sgn
        knee = (hip[0] + f * np.sin(a) * 0.22 * s, hip[1] - np.cos(a) * 0.22 * s)
        foot = (knee[0] + f * np.sin(a * 0.5 + 0.2 * sgn) * 0.22 * s, knee[1] - 0.22 * s * (1 - 0.5 * kneel))
        cv.line([hip, knee, foot], 0.06 * s, v)
    for sgn in (-1, 1):
        a = -swing * sgn * 0.8
        elbow = (sh[0] + f * np.sin(a) * 0.16 * s, sh[1] - np.cos(a) * 0.16 * s)
        hand = (elbow[0] + f * np.sin(a + 0.4) * 0.16 * s, elbow[1] - 0.14 * s)
        cv.line([sh, elbow, hand], 0.045 * s, v)
        if spear and sgn == 1:
            cv.line([(hand[0] - f * 0.1 * s, hand[1] - 0.3 * s), (hand[0] + f * 0.25 * s, hand[1] + 0.55 * s)], 0.02 * s, v)
    return head


def band_positions(seed, n=9):
    r = rng(seed)
    xs = np.sort(r.uniform(-0.9, 0.9, n))
    ss = r.uniform(0.75, 1.0, n)
    ph = r.uniform(0, 2 * np.pi, n)
    sp = r.random(n) < 0.5
    return xs, ss, ph, sp


def beat_fill(w: WCtx, t):
    g, c = w.g, w.c
    tf = t - B["fill"]
    # the land changes: forest to woodland to grassland to dry country with the river
    forest = 1 - sstep(10.0, 18.0, tf)
    grass = sstep(18.0, 26.0, tf)
    dry = sstep(27.0, 33.0, tf)
    skytop = np.array([0.55, 0.7, 0.85], np.float32) * (1 - dry) + np.array([0.75, 0.8, 0.9], np.float32) * dry
    skybot = np.array([0.8, 0.85, 0.8], np.float32) * (1 - dry) + np.array([0.95, 0.88, 0.7], np.float32) * dry
    img = sky(g, skytop, skybot, horizon=-0.1)
    scroll = tf * 0.9
    # far hills / canopy
    n = c.vn.fbm((g.x + scroll * 0.15) * 1.2, g.y * 1.2, 3)
    hill = 1 - smoothstep(-0.05 + 0.25 * n - 0.1 * grass, 0.0 + 0.25 * n - 0.1 * grass, g.y)
    hillcol = np.array([0.18, 0.3, 0.14], np.float32) * (1 - dry) + np.array([0.6, 0.5, 0.3], np.float32) * dry
    img = over(img, hill, hillcol)
    # the river, in dry country: high and wide and green on both banks, running along our way
    if dry > 0:
        rv = (1 - smoothstep(-0.25, -0.2, g.y)) * smoothstep(-0.45, -0.4, g.y)
        rn = c.n3.sample((g.x + scroll * 0.3) * 3, g.y * 6, t * 0.5, octaves=2)
        rivercol = np.stack([0.25 + 0.1 * rn, 0.4 + 0.1 * rn, 0.4 + 0.1 * rn], axis=-1)
        img = over_img(img, rv * dry, rivercol)
        bank = (1 - smoothstep(-0.2, -0.1, g.y)) * smoothstep(-0.3, -0.2, g.y) + (1 - smoothstep(-0.45, -0.4, g.y)) * smoothstep(-0.55, -0.45, g.y)
        img = over(img, bank * dry * 0.9, (0.25, 0.42, 0.18))
        # reeds and papyrus; hippos in the shallows; birds everywhere
        cv = Canvas(g)
        r = rng(13)
        for i in range(50):
            rx = (((r.uniform(-2.5, 2.5) + scroll * 0.45) + 2.5) % 5.0) - 2.5
            ry = -0.2 + r.uniform(-0.03, 0.03)
            h = r.uniform(0.12, 0.25)
            cv.line([(rx, ry), (rx + 0.02 * np.sin(t + i), ry + h)], 0.008)
            if r.random() < 0.5:
                cv.ellipse(rx + 0.02 * np.sin(t + i), ry + h, 0.03, 0.02)
        for i in range(3):
            hx = (((i * 1.7 - 1.0) + scroll * 0.3 + 2.5) % 5.0) - 2.5
            cv.ellipse(hx, -0.33, 0.14, 0.05)
            cv.ellipse(hx + 0.12, -0.32, 0.06, 0.04)
        img = over(img, cv.mask(0.8) * dry * 0.9, (0.15, 0.2, 0.1))
        bv = Canvas(g)
        for i in range(25):
            ph = i * 1.3
            bx = ((i * 0.41 + t * 0.35 + 2.5) % 5.0) - 2.5
            by = 0.2 + 0.4 * ((i * 0.37) % 1.0) + 0.05 * np.sin(t + ph)
            fl = 0.05 * np.sin(t * 12 + ph)
            s = 0.025 + 0.02 * ((i * 0.53) % 1.0)
            bv.line([(bx - s, by + fl), (bx, by), (bx + s, by + fl)], 0.006)
        img = over(img, bv.mask(0.6) * dry * 0.8, (0.15, 0.15, 0.15))
    # ground
    gmask = 1 - smoothstep(-0.62, -0.55, g.y)
    gn = c.vn.fbm((g.x + scroll * 0.9) * 2, g.y * 2, 3)
    gcol_f = np.stack([0.2 + 0.1 * gn, 0.28 + 0.1 * gn, 0.12 + 0.05 * gn], axis=-1)
    gcol_g = np.stack([0.55 + 0.15 * gn, 0.55 + 0.1 * gn, 0.25 + 0.05 * gn], axis=-1)
    gcol_d = np.stack([0.7 + 0.1 * gn, 0.6 + 0.1 * gn, 0.4 + 0.05 * gn], axis=-1)
    gcol = gcol_f * (1 - grass) + gcol_g * grass
    gcol = gcol * (1 - dry) + gcol_d * dry
    img = over_img(img, gmask, gcol)
    # mid trees (the forest thins)
    tv = Canvas(g)
    for i, tx in enumerate(w.trunks[:40]):
        if (i / 40.0) > forest * 0.9 + 0.1 * (1 - dry):
            continue
        sx = (((tx + scroll * 0.5) + 2.6) % 5.2) - 2.6
        wd = w.trunk_w[i] * 0.6
        tv.poly([(sx - wd, -0.6), (sx + wd, -0.6), (sx + wd * 0.7, 0.9), (sx - wd * 0.7, 0.9)])
    img = over(img, tv.mask(1.0) * 0.9, (0.1, 0.12, 0.07))

    # the band, and the generations
    # time skips each time the view passes behind a tree: which generation is this?
    passes = [2.5 + 3.6 * i + 0.8 * np.sin(i * 2.1) for i in range(12)]
    gen = sum(1 for p in passes if tf > p)
    xs, ss, ph, sp = band_positions(100 + gen)
    cv = Canvas(g)
    heads = []
    walk = 1.0
    # events
    cat = 10.0 < tf < 14.0
    clash = 17.0 < tf < 20.0
    newborn = 22.0 < tf < 26.0
    grave = 27.0 < tf < 30.5
    if tf < 1.5:
        # feet, running straight over the leaf, right to left
        img = beat_feet(w, img, tf, t)
        return np.clip(img, 0, 1)
    zoomk = sstep(1.5, 3.0, tf)
    scale = lerp(2.2, 1.0, zoomk)
    for i in range(len(xs)):
        s = 0.5 * ss[i] * scale
        fx = xs[i] * scale + 0.06 * np.sin(t * 0.7 + i)
        fy = -0.62 - (1 - ss[i]) * 0.1
        kneel = 0.0
        if grave and i == 4:
            gk = tf - 27.0
            kneel = sstep(0.0, 0.6, gk) * (1 - sstep(2.3, 3.0, gk))
            fx = fx + 0.0
        hd = figure(cv, fx, fy, s, t * 7.0 + ph[i], facing=-1, spear=bool(sp[i]), walk=1.0 - kneel, kneel=kneel)
        heads.append((hd, s, i))
    if cat:
        ck = tf - 10.0
        cx = lerp(1.8, 0.1, sstep(0, 1.5, ck)) + lerp(0.0, 1.5, sstep(2.5, 4.0, ck))
        cy = -0.55 + 0.25 * max(0.0, np.sin(ck * 5)) * (1 - sstep(2.5, 3.2, ck))
        pts = [(-0.4, 0.0), (-0.2, 0.15), (0.2, 0.17), (0.45, 0.1), (0.55, 0.0), (0.4, -0.1), (-0.3, -0.12)]
        cv.poly([(cx + x * 0.6, cy + y * 0.6) for x, y in pts])
        cv.line([(cx - 0.25, cy), (cx - 0.6, cy + 0.15 + 0.1 * np.sin(t * 8))], 0.03)
        for lx in (-0.2, 0.25):
            cv.line([(cx + lx, cy - 0.05), (cx + lx + 0.1 * np.sin(t * 12), cy - 0.25)], 0.035)
    if clash:
        xs2, ss2, ph2, sp2 = band_positions(300)
        ck = tf - 17.0
        off = lerp(-2.6, -0.3, sstep(0, 1.2, ck)) + lerp(0.0, 2.8, sstep(1.6, 3.0, ck))
        for i in range(6):
            figure(cv, xs2[i] * 0.7 + off, -0.62, 0.45 * ss2[i], t * 9.0 + ph2[i], facing=1, spear=bool(sp2[i]))
    m = cv.mask(0.8)
    img = over(img, m * 0.97, (0.06, 0.05, 0.04))
    if newborn:
        nk = (tf - 22.0) / 4.0
        # a bundle passed from hand to hand along the moving line, leftward
        idx = min(int(nk * (len(xs) - 1)), len(xs) - 2)
        f_ = nk * (len(xs) - 1) - idx
        order = np.argsort(-xs)  # from right to left
        a, b_ = heads[order[idx]][0], heads[order[idx + 1]][0]
        bx = lerp(a[0], b_[0], f_)
        by = lerp(a[1], b_[1], f_) - 0.25
        bund = disc(g, bx, by, 0.06)
        img = over(img, bund, (0.75, 0.65, 0.5))
    if grave or (30.5 <= tf < 34):
        gk = tf - 27.0
        gx = -0.1 + (0.9 * max(0.0, gk - 3.0)) * 1.0
        mound = disc(g, gx, -0.75, 0.12) * (1 - smoothstep(-0.75, -0.7, g.y))
        img = over(img, mound * 0.9, (0.3, 0.22, 0.12))
    # we're always on a face: the one nearest the centre is lit a little
    near = min(heads, key=lambda h: abs(h[0][0]))
    hd, s, i = near
    img = add(img, disc(g, hd[0] - 0.03 * s, hd[1], 0.06 * s) * 0.35, (0.6, 0.45, 0.35))
    # foreground trunks, sweeping past (the time skips)
    fv = Canvas(g)
    for p in passes:
        dx = (tf - p) * 2.0
        if -1.0 < dx < 1.0:
            sx = dx * 2.6
            fv.poly([(sx - 0.25, -1.1), (sx + 0.25, -1.1), (sx + 0.2, 1.1), (sx - 0.2, 1.1)])
    img = over(img, fv.mask(2.0) * 0.98 * (1 - dry * 0.5), (0.04, 0.04, 0.03))
    return np.clip(img, 0, 1)


def beat_feet(w: WCtx, img, tf, t):
    """The leaf, and feet running straight over it, right to left."""
    g = w.g
    gcol = np.stack([0.32 + 0 * g.x, 0.28 + 0 * g.x, 0.18 + 0 * g.x], axis=-1)
    img = over_img(img, 1 - smoothstep(-0.2, 0.3, g.y), gcol)
    lv = Canvas(g)
    pts = [(0, 0.12), (0.08, 0.05), (0.1, -0.05), (0, -0.15), (-0.1, -0.05), (-0.08, 0.05)]
    lv.poly([(0.1 + x * 1.6, -0.3 + y * 1.6) for x, y in pts])
    img = over(img, lv.mask(1.0) * 0.95, (0.5, 0.35, 0.12))
    cv = Canvas(g)
    for i in range(10):
        ph = (t * 2.2 + i * 0.37) % 1.0
        x = 2.4 - ph * 4.8
        lift = 0.35 * max(0.0, np.sin((ph * 3 + i) * 2 * np.pi))
        cv.line([(x + 0.1, 1.2), (x, -0.2 + lift)], 0.18)
        cv.ellipse(x - 0.12, -0.3 + lift, 0.22, 0.09)
    img = over(img, cv.mask(1.5) * 0.97, (0.06, 0.05, 0.04))
    return img


# ------------------------------------------------------------------ beat 14: rest

def delta_view(w: WCtx, t, k_light):
    """Below them the valley opens: the river coming apart like a hand into many channels, green along
    every channel, mist in the early light, a flock lifting and settling."""
    g, c = w.g, w.c
    img = sky(g, (0.55, 0.65, 0.8), (0.95, 0.8, 0.6), horizon=0.3, power=0.7)
    # the plain, in perspective: y from -1 (near) to 0.3 (horizon)
    plain = 1 - smoothstep(0.28, 0.32, g.y)
    n = c.vn.fbm(g.x * 3, g.y * 8, 3)
    base = np.stack([0.55 + 0.1 * n, 0.5 + 0.1 * n, 0.32 + 0.05 * n], axis=-1)
    img = over_img(img, plain, base)
    cv = Canvas(g)
    gv = Canvas(g)
    for (x0, y0, x1, y1, wd) in w.delta:
        # perspective: the delta spreads north, which is away from us and screen-left
        def P(x, y):
            d = 0.12 + y * 0.9  # depth
            return (-0.2 + (x - 0.4) * 1.6 / (1 + d * 2.5) - d * 0.5, -0.95 + 1.22 * (1 - 1 / (1 + d * 2.0)))
        a, b_ = P(x0, y0), P(x1, y1)
        cv.line([a, b_], wd * 1.6)
        gv.line([a, b_], wd * 5.0)
    green = gv.mask(3.0)
    img = over(img, green * 0.85 * plain, (0.25, 0.42, 0.16))
    water = cv.mask(1.0)
    img = over(img, water * 0.8 * plain, (0.42, 0.58, 0.62))
    # reed beds and pools, as texture
    pools = smoothstep(0.62, 0.7, c.vn2.fbm(g.x * 6, g.y * 14, 3)) * plain * (1 - smoothstep(-0.3, 0.25, g.y))
    img = over(img, pools * 0.6, (0.45, 0.6, 0.6))
    # mist in the early light
    mist = c.n3.sample(g.x * 1.5, g.y * 3, t * 0.1, octaves=3) * plain * (1 - smoothstep(-0.2, 0.3, g.y)) * smoothstep(-0.9, -0.3, g.y)
    img = over(img, np.clip(mist * 1.3, 0, 1) * 0.6, (0.95, 0.93, 0.9))
    return img


def flock(w: WCtx, img, tk, t):
    """A flock lifts off the water in its thousands, turns, and settles again. tk runs 0..8."""
    g = w.g
    fl = w.flock
    lift = np.sin(np.pi * np.clip(tk / 8.0, 0, 1))
    xs = (fl[:, 0] * 1.6 - 1.4) + 0.3 * lift * np.sin(tk * 0.8 + fl[:, 2] * 3)
    ys = (fl[:, 1] * 0.25 - 0.55) + lift * (0.35 + 0.5 * fl[:, 2]) * (0.6 + 0.4 * np.sin(tk + fl[:, 1] * 6))
    cols = np.tile(np.array([[0.2, 0.2, 0.2]], np.float32), (len(fl), 1))
    inten = np.full(len(fl), 0.7, np.float32) * (0.3 + 0.7 * lift) + 0.3
    img += -splat(g, xs, ys, cols, inten, radius_px=0.9 * g.h / 540) * 2.5
    return np.clip(img, 0, 1)


def beat_rest(w: WCtx, t):
    g, c = w.g, w.c
    tr = t - B["rest"]
    if tr < 10.0:
        # they come up onto the edge of a cliff and stop. The valley opens below.
        img = delta_view(w, t, 1.0)
        if tr > 2.0:
            img = flock(w, img, tr - 2.0, t)
        # the cliff: a dark ridge of ground in the lower right, and the band on it, from behind and beside
        cv = Canvas(g)
        cv.poly([(0.1, -1.1), (1.9, -1.1), (1.9, -0.15), (0.9, -0.2), (0.35, -0.35), (0.1, -0.6)])
        img = over(img, cv.mask(1.5) * 0.98, (0.12, 0.1, 0.08))
        fv = Canvas(g)
        xs, ss, ph, sp = band_positions(100 + 12)
        stop = sstep(0.0, 2.0, tr)
        for i in range(len(xs)):
            s = 0.45 * ss[i]
            fx = 0.55 + xs[i] * 0.9 - (1 - stop) * 0.3
            fy = -0.3 - abs(xs[i]) * 0.12
            figure(fv, fx, fy, s, t * 7.0 + ph[i], facing=-1, spear=bool(sp[i]), walk=1.0 - stop)
        img = over(img, fv.mask(0.8) * 0.98, (0.06, 0.05, 0.04))
        # their breathing: nothing moves but the birds and the mist
        return np.clip(img, 0, 1)

    if tr < 17.0:
        # we move in, slowly, on one of them: the face we saw at the start, in the morning light
        k = sstep(10.0, 17.0, tr)
        bg = delta_view(w, t, 1.0)
        bg = flock(w, bg, 8.0, t)
        bg = blur(bg, (2 + 18 * k) * g.h / 540)
        img = bg
        # the silhouette head at the right grows into the lit face at the centre
        s = lerp(0.12, 0.95, k)
        cx = lerp(0.62, 0.0, k)
        cy = lerp(-0.08, 0.0, k)
        e = F.mix_expr(F.NEUTRAL_OPEN, dict(brow=0.1, curve=0.05, open=0.08, eyes=0.9, wide=0.0), 0.5)
        img = lit_face(w, img, cx, cy, s, e, lit=sstep(0.3, 0.8, k), t=t)
        return np.clip(img, 0, 1)

    if tr < 22.5:
        # the face draws a breath in: the chin lifts a little, the mouth opens a little, the nostrils
        k = tr - 17.0
        br = sstep(1.5, 5.0, k)
        bg = blur(flock(w, delta_view(w, t, 1.0), 8.0, t), 20 * g.h / 540)
        e = dict(brow=0.1 + 0.15 * br, curve=0.05, open=0.08 + 0.14 * br, eyes=0.9, wide=0.1 * br)
        img = lit_face(w, bg, 0.0, 0.0 + 0.02 * br, 0.95 * (1 + 0.025 * br), e, lit=1.0, t=t)
        # closer: toward the eye
        zoom = 1 + 2.5 * sstep(3.0, 5.5, k)
        if zoom > 1.01:
            img = zoom_to(w, img, 0.31 * 0.95, 0.215 * 0.95, zoom)
        return np.clip(img, 0, 1)

    # the eye, with the river in it. In the dark of the pupil, for an instant, the grain of the static.
    k = tr - 22.5
    img = eye_closeup(w, t, k)
    # black, on the held breath
    fade = sstep(0.9, 1.3, k)
    return np.clip(img * (1 - fade), 0, 1)


def lit_face(w: WCtx, img, cx, cy, s, e, lit, t):
    """The face at the cliff (v3): the same mesh face as the static's, lit by the early sun from the
    left, skin-toned, with a warm rim; its edge falls into shadow."""
    g = w.g
    f = w.c.mface(cx, cy, s, e)
    key = FM.lambert(f, (-0.6, 0.5, 0.65), wrap=0.3)
    rim = FM.lambert(f, (0.85, 0.25, 0.2), wrap=0.0) ** 2
    occ = FM.cavity(f)
    skin = np.array([0.62, 0.42, 0.28], np.float32)
    col = skin * (0.18 + 0.85 * key * (1 - 0.5 * occ))[..., None]
    col += rim[..., None] * np.array([0.5, 0.3, 0.15], np.float32) * 0.5
    eyes = f["eyes"]
    col = over(col, eyes * (1 - f["iris"]), (0.78, 0.74, 0.70))
    col = over(col, f["iris"], (0.22, 0.13, 0.06))
    col = over(col, f["mouth"], (0.15, 0.07, 0.05))
    sil = np.asarray((0.06, 0.05, 0.04), np.float32)
    face_img = sil[None, None, :] * (1 - lit) + col * lit
    return over_img(img, f["edge"], face_img)


def zoom_to(w: WCtx, img, cx, cy, zoom):
    """Resample the frame zoomed about a point (nearest neighbour; it's an animatic)."""
    g = w.g
    H, W = g.h, g.w
    px = (cx / g.aspect + 1) * 0.5 * W
    py = (1 - cy) * 0.5 * H
    yy, xx = np.mgrid[0:H, 0:W]
    sx = ((xx - px) / zoom + px).astype(np.int64).clip(0, W - 1)
    sy = ((yy - py) / zoom + py).astype(np.int64).clip(0, H - 1)
    return img[sy, sx]


def eye_closeup(w: WCtx, t, k):
    g, c = w.g, w.c
    img = w.g.blank(0.0) + np.array([0.55, 0.38, 0.26], np.float32)
    # lids
    lid = (1 - smoothstep(0.55, 0.62, np.abs(g.y) + 0.25 * (g.x / 1.5) ** 2))
    img = over(img, lid, (0.86, 0.83, 0.8))
    iris_r = 0.5
    rr = g.r
    ang = g.theta
    tex = c.vn.fbm(ang * 6, rr * 10, 3)
    iris = (1 - smoothstep(iris_r - 0.01, iris_r + 0.01, rr)) * lid
    icol = np.stack([0.35 + 0.25 * tex, 0.2 + 0.15 * tex, 0.08 + 0.05 * tex], axis=-1)
    img = over_img(img, iris, icol)
    pupil_r = 0.24 - 0.03 * sstep(0.0, 0.6, k)
    pupil = 1 - smoothstep(pupil_r - 0.01, pupil_r + 0.01, rr)
    img = over(img, pupil, (0.02, 0.015, 0.01))
    # the river in it: the delta's channels reflected on the eye's surface, dim
    cv = Canvas(g)
    for (x0, y0, x1, y1, wd) in w.delta:
        a = (-0.3 + (x0 - 0.4) * 1.2 - y0 * 0.4, -0.5 + y0 * 1.1)
        b_ = (-0.3 + (x1 - 0.4) * 1.2 - y1 * 0.4, -0.5 + y1 * 1.1)
        cv.line([a, b_], wd * 1.5)
    refl = cv.mask(1.5) * lid * (1 - smoothstep(0.3, 0.55, rr) * 0.3)
    img = add(img, refl * 0.35, (0.8, 0.9, 0.9))
    # highlight
    img = add(img, gauss(g, -0.18, 0.2, 0.06, 0.05), (0.9, 0.9, 0.9))
    # in the dark of the pupil, for an instant, the grain of the static
    if 0.35 < k < 0.75:
        amt = np.sin(np.pi * (k - 0.35) / 0.4)
        s = w.static.render(g, 0.0, 0.0, t, sparkle=0.1, seed_t=t)
        img = over_img(img, pupil * amt * 0.55, gray(s) * 0.5)
    return img
