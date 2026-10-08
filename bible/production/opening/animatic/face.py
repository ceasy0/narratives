"""A procedural placeholder face, as a depth map with expression controls.

This stands in for the filmed face the dossier plans (DOSSIER §6, "Real expressions, cheaply"):
film a real face, turn the footage into depth maps, drive the static and the lighting from the depth.
Here the depth map is built from smooth bumps so the whole pipeline can run today. When the face
shoot exists, `face_fields` is the one function to replace: it should return the same dictionary
from a filmed depth frame.

Expression parameters (all floats):
  brow   -1 lowered .. +1 raised
  curve  -1 frown  .. +1 smile      (the mouth line)
  open    0 shut   ..  1 wide open  (the mouth)
  eyes    0 closed ..  1 open       (the lids)
  wide    0 ..  1 eyes widened (fear, terror)
Expressions follow the four-face rule (STORYTELLING): large faces smile, small faces frown;
raised brows for fear and compassion, lowered for malice and upset.
"""
from __future__ import annotations

import numpy as np

from common import Grid, gauss, smoothstep, lerp

# The four starting states, by the author's rule (2026-10-07).
FEAR = dict(brow=0.8, curve=-0.6, open=0.25, eyes=1.0, wide=0.6)
TERROR = dict(brow=1.0, curve=-1.0, open=0.8, eyes=1.0, wide=1.0)
MALICE = dict(brow=-0.8, curve=0.6, open=0.1, eyes=0.7, wide=0.0)
LAUGH = dict(brow=-1.0, curve=1.0, open=1.0, eyes=0.45, wide=0.0)
UPSET = dict(brow=-0.7, curve=-0.6, open=0.05, eyes=0.8, wide=0.0)
COMPASSION = dict(brow=0.7, curve=0.5, open=0.0, eyes=0.85, wide=0.0)
PEACE = dict(brow=0.1, curve=0.15, open=0.0, eyes=0.5, wide=0.0)
SLEEP = dict(brow=0.0, curve=0.05, open=0.0, eyes=0.0, wide=0.0)
NEUTRAL_CLOSED = dict(brow=0.0, curve=0.0, open=0.0, eyes=0.0, wide=0.0)
NEUTRAL_OPEN = dict(brow=0.0, curve=0.0, open=0.12, eyes=1.0, wide=0.0)


def mix_expr(a: dict, b: dict, t: float) -> dict:
    t = min(max(t, 0.0), 1.0)
    return {k: lerp(a[k], b[k], t) for k in a}


def face_fields(g: Grid, cx: float, cy: float, s: float, e: dict, soft_scale: float = 1.0):
    """Return depth and masks for a face centred at (cx, cy) with half-height s.

    Returns dict(depth, mask, eyes, mouth, crease). depth is 0 outside the head and up to ~1.2
    at the nose tip. crease is a soft mask of the lines that read in black-on-black: brows,
    lids, nose, mouth, jaw."""
    x = (g.x - cx) / s
    y = (g.y - cy) / s
    px = g.px / s * soft_scale

    # head: an oval dome, slightly narrower at the chin
    rx = 0.72 + 0.10 * y
    rx = np.clip(rx, 0.58, 0.80)
    q = (x / rx) ** 2 + (y / 1.0) ** 2
    head = 1 - smoothstep(1 - 2 * px, 1 + 2 * px, np.sqrt(q))
    depth = np.sqrt(np.clip(1 - q, 0, 1)) * 0.9

    brow = e["brow"]
    curve = e["curve"]
    opn = e["open"]
    eyes = e["eyes"]
    wide = e["wide"]

    # brows: two ridges; raised brows go up and arch, lowered brows come down and slope inward
    by = 0.34 + 0.09 * brow
    rot = 0.30 * brow + 0.1  # inner ends tilt
    for sgn in (-1, 1):
        depth += 0.09 * gauss(_G(x, y), sgn * 0.31, by, 0.21, 0.045, rot=-sgn * (rot - 0.25))

    # eye sockets
    for sgn in (-1, 1):
        depth -= 0.09 * gauss(_G(x, y), sgn * 0.31, 0.21, 0.17, 0.10)

    # eye apertures
    ry_eye = 0.004 + 0.062 * eyes * (1 + 0.7 * wide)
    rx_eye = 0.135 + 0.02 * wide
    eyes_m = np.zeros_like(x)
    lids = np.zeros_like(x)
    for sgn in (-1, 1):
        dx = (x - sgn * 0.31) / rx_eye
        dy = (y - 0.215) / max(ry_eye, 1e-3)
        d = np.sqrt(dx * dx + dy * dy)
        if eyes > 0.05:
            eyes_m = np.maximum(eyes_m, 1 - smoothstep(1 - 3 * px / ry_eye, 1 + 3 * px / ry_eye, d))
        # the lid line, which is what shows when the eyes are shut
        lids = np.maximum(lids, np.exp(-0.5 * ((y - 0.215) / 0.010) ** 2) * (np.abs(dx) < 1.0))
        # eyeball under the lids
        depth += 0.035 * gauss(_G(x, y), sgn * 0.31, 0.215, 0.11, 0.07) * (0.4 + 0.6 * eyes)
    # brow lines (the hair of the brows), following the ridge
    browline = np.zeros_like(x)
    for sgn in (-1, 1):
        xx = (x - sgn * 0.31)
        yy = by + sgn * xx * (0.35 * brow - 0.05) - 0.5 * (xx * xx) * (1 + 0.5 * brow)
        browline = np.maximum(browline, np.exp(-0.5 * ((y - yy) / 0.016) ** 2) * (np.abs(xx) < 0.22))

    # nose: a ridge widening downward, a tip, two nostrils
    nose_t = np.clip((0.25 - y) / 0.36, 0, 1)
    ridge = np.exp(-0.5 * (x / (0.045 + 0.05 * nose_t)) ** 2) * (y < 0.27) * (y > -0.13)
    depth += 0.14 * ridge * (0.3 + 0.7 * nose_t)
    depth += 0.09 * gauss(_G(x, y), 0.0, -0.10, 0.11, 0.075)
    for sgn in (-1, 1):
        depth -= 0.03 * gauss(_G(x, y), sgn * 0.085, -0.15, 0.035, 0.025)

    # cheeks rise with a smile
    for sgn in (-1, 1):
        depth += (0.05 + 0.04 * max(curve, 0)) * gauss(_G(x, y), sgn * 0.44, -0.08 + 0.05 * max(curve, 0), 0.16, 0.14)

    # mouth: a lip line whose corners rise with `curve`; the aperture opens below it
    mx = x / 0.33
    corner = 0.11 * curve * (mx * mx)
    my = -0.40 + corner
    lip_w = np.clip(1 - mx * mx, 0, 1)  # 1 at centre, 0 at the corners
    upper = my + 0.08 * opn * lip_w
    lower = my - 0.20 * opn * np.sqrt(lip_w) - 0.01
    inside = (y < upper) & (y > lower) & (np.abs(mx) < 1.0)
    mouth_m = inside.astype(np.float32)
    # soften the aperture edges
    mouth_m = mouth_m * smoothstep(0.0, 0.08, lip_w) if opn > 0.02 else mouth_m * 0
    depth -= 0.16 * mouth_m
    # lips as two faint ridges
    depth += 0.03 * np.exp(-0.5 * ((y - upper - 0.025) / 0.022) ** 2) * lip_w * (np.abs(mx) < 1.05)
    depth += 0.035 * np.exp(-0.5 * ((y - lower + 0.03) / 0.028) ** 2) * lip_w * (np.abs(mx) < 1.05)
    # the lip line itself, a crease
    lipline = np.exp(-0.5 * ((y - my) / 0.012) ** 2) * (np.abs(mx) < 1.05)

    # chin, dropping as the mouth opens
    depth += 0.06 * gauss(_G(x, y), 0.0, -0.72 - 0.06 * opn, 0.22, 0.13)

    depth = depth * head

    # creases: the lines that show in black-on-black. Built from depth curvature plus the explicit lines.
    gy, gx = np.gradient(depth)
    lap = np.abs(np.gradient(gx, axis=1) + np.gradient(gy, axis=0))
    lap = lap / (lap.max() + 1e-6)
    crease = np.clip(lap * 6, 0, 1) * head
    crease = np.maximum(crease, lipline * 0.9)
    crease = np.maximum(crease, eyes_m * 0.7)
    crease = np.maximum(crease, lids * 0.8)
    crease = np.maximum(crease, browline * 0.9)
    rim = head - (1 - smoothstep(1 - 8 * px, 1 - 2 * px, np.sqrt(q)))
    crease = np.maximum(crease, np.clip(rim, 0, 1))

    return dict(depth=depth, mask=head, eyes=eyes_m, mouth=mouth_m, crease=crease,
                local=(x, y), lipline=lipline, brow=browline, lids=lids, px=px, scale=s)


class _G:
    """A tiny shim so common.gauss can take face-local coordinates."""

    def __init__(self, x, y):
        self.x, self.y = x, y


def normals(depth, strength=1.0, px=1.0):
    gy, gx = np.gradient(depth)
    nx = -gx * strength / px
    ny = gy * strength / px  # image y runs downward
    nz = np.ones_like(depth)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    return nx / n, ny / n, nz / n


def shade(fields, light=(0.3, 0.5, 0.8), ambient=0.25, strength=1.0):
    """Lambert shading of the depth map, 0..1, inside the mask."""
    nx, ny, nz = normals(fields["depth"], strength, fields["px"])
    lx, ly, lz = light
    L = np.sqrt(lx * lx + ly * ly + lz * lz)
    lam = np.clip((nx * lx + ny * ly + nz * lz) / L, 0, 1)
    return (ambient + (1 - ambient) * lam) * fields["mask"]


def white_face(fields, g: Grid, modeling=0.35):
    """The face stripped white: white fill, with just enough modeling to read the features."""
    sh = shade(fields, light=(0.2, 0.6, 0.8), ambient=0.0, strength=1.2)
    v = 1.0 - modeling * (1 - sh)
    v = v - 0.55 * fields["mouth"] - 0.55 * fields["eyes"] - 0.25 * fields["brow"] - 0.2 * fields["lids"] * (1 - fields["eyes"])
    return np.clip(v, 0, 1) * fields["mask"]


def black_face(fields, g: Grid, edge=0.16):
    """Black on black: only the edges and creases, as faint grey."""
    sh = shade(fields, light=(-0.4, 0.5, 0.75), ambient=0.0, strength=1.5)
    rim = np.clip(1 - sh, 0, 1) ** 2
    v = edge * np.maximum(fields["crease"], 0.9 * rim) * fields["mask"]
    v += edge * 0.8 * fields["eyes"] + edge * 0.6 * fields["mouth"]
    return np.clip(v, 0, 1)


def white_on_white(fields, g: Grid, edge=0.18):
    """The compassionate face: white on white, seen by faint shadows in the creases."""
    sh = shade(fields, light=(0.3, 0.6, 0.75), ambient=0.0, strength=1.5)
    rim = np.clip(1 - sh, 0, 1) ** 2
    v = 1 - edge * np.maximum(fields["crease"], 0.9 * rim) * fields["mask"]
    v -= edge * 0.9 * fields["eyes"] + edge * 0.7 * fields["mouth"]
    return np.clip(v, 0, 1)
