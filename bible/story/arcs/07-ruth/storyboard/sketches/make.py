"""Ruth storyboard sketches: sixteen pencil-and-wash panels, same staging as ../draw.py and STORYBOARD.md section 2.

Run:  python3 make.py            (all panels + both contact sheets)
      python3 make.py P1 3.5     (just those panels; sheets are rebuilt from whatever PNGs exist)
Needs: Pillow, and a headless Chromium to rasterize the SVGs (Playwright's, at /opt/pw-browsers, is found automatically;
       or set CHROME=/path/to/chrome). The SVG sources land in svg/, the PNGs next to this file.
"""
from __future__ import annotations

import glob
import math
import os
import random
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sketchlib import *  # noqa: E402,F401,F403
import sketchlib as SL  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SVG_DIR = os.path.join(HERE, "svg")

RED = "#8e2f24"

SHORT = {
    "P1": "The bare threshing floor at dawn: wide, static; dust blows left to right",
    "P3": "The bread bin: the boys at the bin, Elimelech between, Naomi laughing behind",
    "P7": "The view east: over Elimelech's shoulder, Moab under rain across the rift",
    "1.1": "Arrival in Moab: the family left, the Moabites right; Ruth and Orpah watch",
    "1.8": "The grave, wide and high: three and nobody else; far right, Ruth with bread",
    "1.11": "The double wedding: Naomi dances in the middle of Moab, lit from below",
    "1.17": "Three graves: Moab mourns at the edges; Naomi binds Ruth's arms. No words",
    "1.21": "The parting on the road: Orpah goes back up-right; the wind; inset, the oath",
    "1.25": "The well by the gate: the women under the gate; Naomi and Ruth apart. \u201cMara\u201d",
    "2.5": "The field: the reapers' line; Ruth gleaning low; Boaz comes to her through it",
    "2.6": "The meal, in the shelter's shade: his roasted grain reaching to her hands",
    "3.5": "Midnight on the floor: Boaz starts awake; Ruth at his feet, an arm's length off",
    "3.8": "\u201cEmpty\u201d: dawn in the ruin, the barley between them; Naomi sits, Ruth speaks",
    "4.1": "The gate: ten elders on the bench; the sandal passes left, to Boaz",
    "4.6": "The naming: Naomi, the child in her lap, laughs up at Ruth. The fullest frame",
    "4.7": "The roof at dusk: Naomi sings to Obed; Moab turns blue; push in to his face",
}



# ----------------------------------------------------------------------------------------------- small shared bits

def group(sk, transform):
    sk.add(f'<g transform="{transform}">')


def end(sk):
    sk.add("</g>")


def sub_sketch(sk, seed):
    s = Sketch(seed, hatch_angle=sk.hatch_angle)
    s.uid = 10000 * (seed % 50 + 1)
    return s


def embed(sk, sub, x, y, w, h, vx, vy, vw, vh, label=None):
    """Put a sub-sketch (drawn in full-frame coordinates) into an inset box on sk."""
    sk.defs.extend(sub.defs)
    sk.add(f'<rect x="{x - 6}" y="{y - 6}" width="{w + 12}" height="{h + 12}" fill="{PAPER}"/>')
    sk.add(f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{vx} {vy} {vw} {vh}" preserveAspectRatio="xMidYMid slice">'
           f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" fill="{sub.paper}"/>' + "".join(sub.body) + "</svg>")
    sk.line([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], 2.6, 0.9, closed=True, amp=0.5)
    if label:
        note(sk, x + 4, y - 10, label, 15, RED)


def sky(sk, horizon, top=0.72, bottom=0.92):
    sk.rect_grad(0, 0, W, horizon + 2, [(0, grey(top)), (1, grey(bottom))])


def cloud_scribble(sk, rng, x0, y0, x1, y1, n=14, op=0.25, w=1.0):
    for _ in range(n):
        cx, cy = rng.uniform(x0, x1), rng.uniform(y0, y1)
        L = rng.uniform(60, 180)
        pts = [(cx - L / 2 + L * t / 6, cy + math.sin(t * 1.3 + rng.random()) * 5 - (8 if 1 < t < 5 else 0)) for t in range(7)]
        sk.line(pts, w, op, passes=1, amp=1.5)


def dust_streaks(sk, rng, x0, y0, x1, y1, n=18, op=0.3, slope=0.0):
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        L = rng.uniform(40, 160)
        pts = [(x + L * t / 5, y + slope * L * t / 5 + math.sin(t + x) * 2.5) for t in range(6)]
        sk.line(pts, rng.uniform(0.6, 1.4), op * rng.uniform(0.5, 1), passes=1, amp=1.2)


def terraces(sk, rng, x0, x1, y_top, y_bot, rows, op=0.5, tone=None, stubble=True, curve=12):
    """Stepped hillside terraces: curved retaining walls with stones, getting closer together toward y_top."""
    for i in range(rows):
        t = (i / max(rows - 1, 1)) ** 1.6
        y = lerp(y_top, y_bot, t)
        pts = [(lerp(x0, x1, k / 10), y + math.sin(k / 10 * math.pi) * -curve * (0.4 + t) + rng.uniform(-2, 2)) for k in range(11)]
        sk.line(pts, lerp(0.7, 1.6, t), op, passes=2, amp=1.0)
        # wall face: little stone ticks under the line
        d = []
        for k in range(int(lerp(25, 60, t))):
            x = rng.uniform(x0, x1)
            kk = (x - x0) / (x1 - x0)
            yy = y + math.sin(kk * math.pi) * -curve * (0.4 + t)
            hgt = lerp(2, 7, t)
            d.append(f"M{x:.1f},{yy + 1:.1f}l{rng.uniform(-1, 1):.1f},{hgt:.1f}")
        sk.add(f'<path d="{"".join(d)}" stroke="{INK}" stroke-width="0.8" stroke-opacity="{op * 0.7:.2f}" fill="none"/>')
        if stubble:
            grass(sk, rng, int(lerp(10, 30, t)), x0, yy - lerp(6, 20, t), x1, yy - 2, h=(2, lerp(3, 7, t)), op=0.35)


def houses(sk, rng, x0, y_base, n, scale=1.0, tone=0.82):
    """A small hilltop village of flat-roofed houses."""
    x = x0
    for i in range(n):
        w = rng.uniform(18, 34) * scale
        h = rng.uniform(10, 18) * scale
        yb = y_base + rng.uniform(-4, 4) * scale
        pts = [(x, yb), (x, yb - h), (x + w, yb - h), (x + w, yb)]
        sk.fill(pts, grey(tone), 1, amp=0.3, smooth=False)
        sk.line(pts + [pts[0]], 0.9, 0.7, passes=1, amp=0.4)
        sk.fill([(x + w * 0.6, yb - h), (x + w, yb - h), (x + w, yb), (x + w * 0.6, yb)], INK, 0.12, amp=0.2, smooth=False)
        if rng.random() < 0.6:
            dx = x + rng.uniform(0.2, 0.5) * w
            sk.fill([(dx, yb), (dx, yb - h * 0.45), (dx + 3 * scale, yb - h * 0.45), (dx + 3 * scale, yb)], INK, 0.55, amp=0, smooth=False)
        x += w * rng.uniform(0.75, 1.05)


def olive(sk, rng, x, y, s=1.0, tone=0.6):
    """A small olive tree: twisted trunk, clumped canopy."""
    sk.line([(x, y), (x + 3 * s, y - 14 * s), (x - 2 * s, y - 26 * s)], 2.5 * s, 0.8, passes=2)
    blobs = [ellipse_pts(x + rng.uniform(-16, 16) * s, y - 30 * s + rng.uniform(-8, 6) * s, rng.uniform(10, 16) * s, rng.uniform(7, 10) * s, 12) for _ in range(4)]
    sk.blob(blobs, grey(tone), 1.0, (1, 0.6), True, 3.0, 0.5, construct=False, amp=1.6)


def ground_band(sk, y0, y1, top=0.8, bottom=0.68):
    sk.rect_grad(0, y0, W, y1, [(0, grey(top)), (1, grey(bottom))])


def label_corner(sk, num):
    sk.add(f'<rect x="14" y="14" width="{24 + 13 * len(num)}" height="34" fill="{PAPER}" fill-opacity="0.9" stroke="{INK}" stroke-width="1.5"/>')
    sk.add(f'<text x="{26}" y="39" font-family="DejaVu Sans, sans-serif" font-size="20" font-weight="bold" fill="{INK}">{num}</text>')


# ----------------------------------------------------------------------------------------------- the panels

PANELS = []


def panel(num, caption):
    def deco(fn):
        PANELS.append((num, caption, fn))
        return fn
    return deco


@panel("P1", "The bare threshing floor at dawn. Wide, static; dust crossing left to right.")
def p1(sk, rng):
    hz = 300
    sky(sk, hz, 0.74, 0.93)
    # low sun on the left, just over the ridge
    sx, sy = 118, 168
    sk.radial(sx, sy, 330, "#ffffff", 0.85, 0.0, [(0.3, 0.5)])
    for a in range(0, 360, 15):
        aa = math.radians(a + rng.uniform(-4, 4))
        r0, r1 = 30, 30 + rng.uniform(25, 70)
        sk.line([(sx + math.cos(aa) * r0, sy + math.sin(aa) * r0), (sx + math.cos(aa) * r1, sy + math.sin(aa) * r1)], 0.8, 0.3, passes=1)
    sk.add(f'<circle cx="{sx}" cy="{sy}" r="22" fill="#fbfaf6"/>')
    sk.line(ellipse_pts(sx, sy, 22, 22, 24), 1.3, 0.55, closed=True)
    cloud_scribble(sk, rng, 420, 50, 1220, 150, 12, 0.22)
    ground_band(sk, 240, H, 0.8, 0.55)
    # far ridge (Bethlehem's) with the village on top, near spur in front of it
    far = [(0, 250), (150, 228), (300, 200), (450, 178), (600, 170), (760, 182), (930, 205), (1100, 222), (1280, 236)]
    ridge(sk, far, 0.7, hz + 30, (1, 0.25), 1.4, 4.5, 0.4)
    houses(sk, rng, 455, 182, 10, 1.0, 0.86)
    terraces(sk, rng, 200, 1180, 196, 262, 5, 0.38, stubble=True, curve=5)
    near = [(0, 300), (120, 286), (260, 270), (380, 268), (520, 282), (640, 290), (800, 280), (960, 262), (1120, 258), (1280, 270)]
    ridge(sk, near, 0.62, H, (1, 0.25), 1.6, 4, 0.35)
    sk.rect_grad(0, 290, W, H, [(0, grey(0.8), 0.0), (0.25, grey(0.78), 0.9), (1, grey(0.56), 1)])
    for x, y, s_ in ((880, 270, 0.75), (930, 266, 0.65), (1010, 258, 0.8), (200, 282, 0.6)):
        olive(sk, rng, x, y, s_)
    scribble_ground(sk, rng, 0, 300, W, H, 110, 0.2)
    # the floor: a flat packed oval of beaten earth on a low bedrock shelf, rimmed with stones
    fx, fy, rx, ry = 640, 480, 480, 112
    shelf = ellipse_pts(fx, fy + 14, rx + 14, ry + 8, 60)
    sk.fill(shelf, grey(0.48), 1, amp=2)
    sk.hatch_region([shelf], 3.5, None, 0.8, 0.45)
    floor = ellipse_pts(fx, fy, rx, ry, 60)
    sk.fill(floor, grey(0.88), 1, amp=2)
    sk.wash_region([floor], INK, 0.22, (1, 0.15), 0.25, 1.0)
    # mottled beaten earth
    for _ in range(26):
        a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.random()) * 0.8
        x, y = fx + math.cos(a) * rx * r, fy + math.sin(a) * ry * r
        sk.fill(ellipse_pts(x, y, rng.uniform(20, 60), rng.uniform(5, 12), 12), INK, 0.05, amp=2)
    sk.line(floor, 1.6, 0.7, closed=True, amp=1.5)
    d = []
    for _ in range(160):
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.random()) * 0.93
        x, y = fx + math.cos(a) * rx * r, fy + math.sin(a) * ry * r
        L = rng.uniform(3, 10) * (0.6 + (y - fy + ry) / (2 * ry))
        d.append(f"M{x:.1f},{y:.1f}l{L:.1f},{rng.uniform(-0.8, 0.8):.1f}")
    sk.add(f'<path d="{"".join(d)}" stroke="{INK}" stroke-width="0.8" stroke-opacity="0.4" fill="none"/>')
    for k in range(50):
        a = 2 * math.pi * k / 50 + rng.uniform(-0.03, 0.03)
        x, y = fx + math.cos(a) * (rx + 6), fy + math.sin(a) * (ry + 3)
        s_ = lerp(5, 16, (y - (fy - ry)) / (2 * ry))
        sk.fill([(x + s_ * 0.6, y + s_ * 0.15), (x + s_ * 5, y + s_ * 0.2), (x + s_ * 4.5, y + s_ * 0.5), (x + s_ * 0.4, y + s_ * 0.5)], INK, 0.2, amp=0.5)
        pts = [(x + math.cos(t) * s_ * rng.uniform(0.75, 1.1), y + math.sin(t) * s_ * 0.55 * rng.uniform(0.7, 1.1)) for t in [i * 2 * math.pi / 7 for i in range(7)]]
        sk.fill(pts, grey(0.72), 1, amp=0.4, smooth=False)
        sk.line(pts, 0.9, 0.7, closed=True, passes=1, amp=0.4)
        sk.line([(x + s_ * 0.2, y + s_ * 0.3), (x + s_ * 0.8, y + s_ * 0.1)], 1.8, 0.45, passes=1)
    # the one thing left on it: a broken winnowing fork
    sk.line([(930, 548), (1060, 520)], 2.4, 0.85)
    for k in range(4):
        sk.line([(1060, 520), (1086 + k * 2, 505 + k * 6)], 1.3, 0.8, passes=1)
    sk.fill([(935, 552), (1065, 526), (1100, 530), (960, 558)], INK, 0.15)
    # dust: puffs lifting off the floor and trailing away to the right
    for k in range(6):
        cx = 220 + k * 175 + rng.uniform(-30, 30)
        cy = 430 + rng.uniform(-30, 25)
        L = rng.uniform(120, 200)
        puff = [(cx + L * t / 8, cy - 14 * math.sin(math.pi * t / 8) * (1 - t / 10) + rng.uniform(-3, 3)) for t in range(9)] + \
               [(cx + L * (8 - t) / 8, cy + 10 * math.sin(math.pi * (8 - t) / 8) * (1 - (8 - t) / 10)) for t in range(9)]
        sk.fill(puff, INK, 0.13, amp=3)
        dust_streaks(sk, rng, cx - 20, cy - 12, cx + L * 0.7, cy + 10, 5, 0.4, 0.0)
    # foreground: dry thistles and stones
    grass(sk, rng, 90, 0, 630, W, 715, (8, 22), 0.6)
    stones(sk, rng, 22, 20, 640, 1260, 712, (6, 15), 0.55, (1, 0.2))
    for x in (80, 150, 1150, 1215):
        for k in range(5):
            a = math.radians(-90 + (k - 2) * 16 + rng.uniform(-5, 5))
            L = rng.uniform(45, 75)
            sk.line([(x, 716), (x + math.cos(a) * L, 716 + math.sin(a) * L)], 1.2, 0.75, passes=1)
            sk.add(f'<circle cx="{x + math.cos(a) * L:.0f}" cy="{716 + math.sin(a) * L:.0f}" r="5" fill="{grey(0.35)}"/>')
    arrow(sk, [(240, 372), (420, 364), (580, 366)], label="wind: dust, left to right", label_dy=-12)
    note(sk, 152, 214, "low sun", 15)
    note(sk, 640, 645, "the floor: empty", 15, anchor="middle")


def jar_r(t, mouth):
    if t < 0.68:
        return 0.42 + 0.58 * math.sin(math.pi / 2 * t / 0.68) ** 0.9
    if t < 0.9:
        k = (t - 0.68) / 0.22
        return 1 - (1 - mouth) * (1 - math.cos(math.pi * k)) / 2
    return mouth


def jar(sk, rng, cx, base, w, h, tone=0.7, light=(1, 0.2), mouth=0.5, lw=2.0, handles=True, dark_inside=True):
    """A big clay storage jar: rounded shoulder, collared rim."""
    pts = []
    for i in range(25):
        t = i / 24
        y = base - h * t
        r = w / 2 * jar_r(t, mouth)
        pts.append((cx + r, y))
    rim = (base - h, w / 2 * mouth)
    left = [(cx - (x - cx), y) for x, y in pts[::-1]]
    body = pts + [(cx + rim[1] * 1.08, rim[0] - h * 0.04), (cx - rim[1] * 1.08, rim[0] - h * 0.04)] + left
    sk.blob([body], grey(tone), lw, light, True, 3.4, 0.5, start=0.3, end=0.8)
    mo = ellipse_pts(cx, rim[0] - h * 0.04, rim[1] * 1.08, rim[1] * 0.28, 20)
    sk.shape(mo, grey(0.25 if dark_inside else 0.6), lw * 0.8)
    # throwing rings
    for k in (0.3, 0.55, 0.72):
        y = base - h * k
        r = w / 2 * jar_r(k, mouth)
        sk.line([(cx - r * 0.98, y), (cx, y + r * 0.08), (cx + r * 0.98, y)], 0.8, 0.4, passes=1)
    if handles:
        for sgn in (-1, 1):
            y0 = base - h * 0.78
            sk.line([(cx + sgn * w * 0.4, y0), (cx + sgn * w * 0.52, y0 - h * 0.03), (cx + sgn * w * 0.5, y0 + h * 0.1), (cx + sgn * w * 0.44, y0 + h * 0.12)], lw * 1.6, 0.85, passes=1)


def interior_wall(sk, rng, y_floor, tone=0.66, light_from_left=True):
    masonry(sk, rng, 0, 0, W, y_floor, 26, tone, 0.3)
    sk.rect_grad(0, 0, W, y_floor, [(0, INK, 0.05), (1, INK, 0.45)] if light_from_left else [(0, INK, 0.45), (1, INK, 0.05)], vertical=False)


@panel("P3", "The bread bin. Medium, interior: the boys at the bin, Elimelech between them, Naomi behind their backs laughing.")
def p3(sk, rng):
    yf = 560
    interior_wall(sk, rng, yf, 0.66)
    # ceiling beams and the branch-and-mud roof
    sk.fill([(0, 0), (W, 0), (W, 58), (0, 70)], grey(0.35), 1, smooth=False)
    for x in range(-40, W, 150):
        sk.shape([(x, 52), (x + 60, 48), (x + 64, 84), (x + 4, 88)], grey(0.45), 1.6)
    sk.hatch_region([[(0, 0), (W, 0), (W, 58), (0, 70)]], 3, 20, 0.8, 0.5, smooth=False)
    # floor
    sk.fill([(0, yf), (W, yf), (W, H), (0, H)], grey(0.62), 1, smooth=False)
    scribble_ground(sk, rng, 0, yf + 5, W, H, 50, 0.22)
    sk.line([(0, yf), (W, yf)], 1.6, 0.8, amp=1.5)
    # the doorway on the left, bright, with the courtyard beyond
    dx0, dx1, dy0 = 40, 230, 120
    sk.fill([(dx0, dy0), (dx1, dy0), (dx1, yf), (dx0, yf)], "#faf8f2", 1, smooth=False, amp=0.6)
    sk.line([(dx0 + 15, 420), (dx1, 400)], 1.0, 0.35, passes=1)  # far courtyard wall
    sk.line([(dx0, 470), (dx1, 470)], 0.8, 0.3, passes=1)
    sk.shape([(dx0 - 20, dy0 - 26), (dx1 + 24, dy0 - 30), (dx1 + 26, dy0 - 4), (dx0 - 18, dy0)], grey(0.4), 2.2)  # lintel
    sk.line([(dx0, dy0), (dx0, yf)], 2.6, 0.9)
    sk.line([(dx1, dy0), (dx1, yf)], 2.6, 0.9)
    # light from the door: a pale wedge across the floor and up the boys
    sk.fill([(dx0, yf), (dx1, yf), (900, H), (60, H)], "#fbfaf5", 0.55, smooth=False, amp=1)
    sk.radial(150, 360, 520, "#ffffff", 0.35, 0.0)
    # a stone pillar of the four-room house, and a shelf with jars on the right
    sk.blob([[(930, 70), (990, 72), (995, yf), (925, yf)]], grey(0.6), 2.0, (1, 0.2), True, 3.4, 0.55, soft=0)
    for y in range(110, yf, 34):
        sk.line([(928, y), (993, y + rng.uniform(-3, 3))], 0.8, 0.5, passes=1)
    sk.shape([(1010, 300), (1270, 296), (1272, 312), (1010, 316)], grey(0.45), 1.6)
    for x in (1040, 1095, 1150, 1210):
        jar(sk, rng, x, 298, rng.uniform(34, 46), rng.uniform(50, 70), 0.55, (1, 0.2), 0.45, 1.3, handles=False)
    # Naomi, behind their backs, laughing into her hand, basket on her hip
    L = (1, 0.22)
    Figure(sk, pose_stand(women=True, lean=-0.05), 1080, 760, 64, -1, tone=0.45, head="veil", veil_tone=0.3, expr="laugh", face_turn=0.5,
           arms={"n": {"e": (0.75, 4.95), "w": (0.55, 6.2), "hand": "fist"}, "f": {"e": (-0.9, 4.7), "w": (-0.4, 3.9)}}, light=L,
           props=[("before_head", lambda sk_, f: basket(sk_, f, (-0.95, 4.0), 0.9))]).draw()
    # Elimelech between the boys, a step back, arms folded, looking at Chilion
    Figure(sk, pose_stand(), 600, 745, 66, 1, tone=0.72, head="headcloth", beard=True, face_turn=0.45, expr="neutral",
           arms={"n": {"e": (0.85, 4.75), "w": (-0.25, 5.05), "hand": "fist"}, "f": {"e": (-0.75, 4.75), "w": (0.4, 5.15), "hand": "fist"}}, light=L).draw()
    # the bin
    jar(sk, rng, 640, 700, 230, 250, 0.72, L, 0.55, 2.2)
    sk.fill(ellipse_pts(660, 702, 150, 14, 20), INK, 0.2)
    # Mahlon, thin, the cough he keeps swallowing
    Figure(sk, pose_stand(lean=0.15), 395, 780, 66, 1, tone=0.8, head="hair", hair_tone=0.3, face_turn=0.55, expr="neutral", eyes="down",
           arms={"n": {"e": (1.2, 5.0), "w": (0.65, 6.25), "hand": "fist"}, "f": (-5, 5)}, light=L).draw()
    # Chilion, lid up, peering in: "House of bread."
    Figure(sk, pose_stand(lean=0.45, stride=0.2), 860, 775, 62, -1, tone=0.78, head="hair", hair_tone=0.25, face_turn=0.7, expr="speak",
           head_tilt=14, arms={"n": {"e": (1.4, 6.4), "w": (1.7, 7.5), "hand": "mitt", "obj": obj_lid}, "f": {"e": (0.95, 4.9), "w": (1.75, 4.4)}}, light=L).draw()
    arrow(sk, [(250, 200), (330, 215), (380, 240)], label=None)
    note(sk, 240, 190, "door light", 15)
    note(sk, 860, 140, "\u201cHouse of bread.\u201d", 19)


def basket(sk, f, at, size):
    c = f.P(at)
    u = f.u * size
    pts = [(c[0] - 0.8 * u, c[1] - 0.5 * u), (c[0] + 0.8 * u, c[1] - 0.5 * u), (c[0] + 0.65 * u, c[1] + 0.6 * u), (c[0] - 0.65 * u, c[1] + 0.6 * u)]
    sk.blob([pts], grey(0.62), f.lw, f.light, True, 3, 0.5)
    for k in range(4):
        y = c[1] - 0.3 * u + k * 0.26 * u
        sk.line([(c[0] - 0.75 * u, y), (c[0] + 0.75 * u, y)], 0.8, 0.5, passes=1)


def tag(sk, x, y, text, tx, ty, size=15):
    """A small red name tag with a leader line, for wide shots."""
    sk.line([(tx, ty), (x, y)], 1.0, 0.7, color=RED, passes=1, overshoot=0)
    note(sk, tx + (4 if tx >= x else -4), ty - 4, text, size, RED, "start" if tx >= x else "end")


@panel("P7", "The view east. Wide, over Elimelech's shoulder: Moab across the rift under rain; the dead terraces below.")
def p7(sk, rng):
    hz = 250
    # sky: dry and pale in the west (left), a heavy rain cloud over Moab (right)
    sky(sk, hz + 40, 0.86, 0.9)
    cloud = [(420, 150), (520, 110), (640, 90), (780, 70), (930, 60), (1080, 64), (1280, 50), (1280, 190), (1150, 200), (1000, 190), (850, 196), (700, 190), (560, 180)]
    sk.fill(cloud, grey(0.5), 0.85, amp=6)
    sk.hatch_region([cloud], 4, None, 0.8, 0.35)
    cloud_scribble(sk, rng, 480, 60, 1250, 190, 18, 0.3, 1.2)
    # the rain curtain falling on the plateau
    for k in range(70):
        x = rng.uniform(640, 1220)
        y0 = rng.uniform(170, 200)
        sk.line([(x, y0), (x - 22, hz + rng.uniform(-6, 6))], 0.8, rng.uniform(0.15, 0.35), passes=1, amp=0.3, overshoot=0)
    # Moab: the long flat wall of the plateau across the rift
    moab = [(330, hz + 20), (420, hz - 2), (520, hz - 12), (650, hz - 16), (800, hz - 14), (950, hz - 18), (1100, hz - 12), (1280, hz - 16)]
    ridge(sk, moab, 0.6, hz + 60, (0.3, 1), 1.4, 3.5, 0.3)
    for k in range(40):  # wadis cut into the escarpment face
        x = rng.uniform(380, 1270)
        sk.line([(x, hz - 10), (x + rng.uniform(-6, 6), hz + rng.uniform(20, 40))], 0.7, 0.35, passes=1)
    # the rift: haze, and the sea as a pale band
    sk.rect_grad(0, hz + 8, W, hz + 95, [(0, grey(0.78), 0.0), (0.3, grey(0.8), 1), (1, grey(0.86), 1)])
    sk.fill([(420, hz + 52), (980, hz + 46), (1280, hz + 52), (1280, hz + 66), (430, hz + 64)], "#f7f5ef", 1, amp=1.5)
    sk.line([(430, hz + 64), (1280, hz + 66)], 0.8, 0.35, passes=1)
    note(sk, 560, hz + 44, "the Salt Sea", 13)
    # the wilderness falling away toward the rift, ridge after ridge, nearer is darker
    layers = [(hz + 80, 0.8, 0.25), (hz + 120, 0.74, 0.3), (hz + 175, 0.68, 0.35), (hz + 250, 0.62, 0.4)]
    for i, (y, tone, hop) in enumerate(layers):
        pts = [(x, y - 30 * math.sin(x / 210 + i * 1.7) - 20 * math.sin(x / 97 + i)) for x in range(0, W + 40, 40)]
        ridge(sk, pts, tone, H, (0.4, 1), 1.3, 4, hop)
    # the dead terraces below us: dry walls, stubble, a dead vine
    terraces(sk, rng, 380, 1280, hz + 250, H - 10, 6, 0.6, stubble=True, curve=20)
    for x in (620, 860, 1100):
        y = 600 + rng.uniform(-20, 20)
        sk.line([(x, y), (x + 8, y - 30), (x - 10, y - 46), (x + 6, y - 60)], 1.6, 0.8)
        sk.line([(x + 8, y - 30), (x + 30, y - 40)], 1.0, 0.7, passes=1)
    # Elimelech, back to us, on the ridge, left of frame
    Figure(sk, pose_back(), 215, 1065, 112, 1, tone=0.55, head="back", veil_tone=0.66, face_turn=0.0, light=(1, 0.35), beard=True,
           arms={"n": (6, 2), "f": (-6, -2)}, hatch_op=0.55).draw()
    arrow(sk, [(420, 330), (560, 300), (700, 282)], label="east: Moab, in rain", label_dy=-12)
    note(sk, 760, 650, "dead terraces", 15)
    note(sk, 120, 120, "dry, west", 15)


def moab_man(sk, x, y, u, d, tone=0.55, cap=True, arms=None, light=(0.5, 0.6), expr="neutral", turn=0.55, beard=True, short=True, hatch=True):
    return Figure(sk, pose_stand(short=short), x, y, u, d, tone=tone, head="headcloth" if cap else "hair", hair_tone=0.3, beard=beard,
                  face_turn=turn, expr=expr, arms=arms or {}, light=light, hatch=hatch).draw()


def donkey(sk, x, y, s, d=1, tone=0.55):
    """A pack donkey in side view, facing d."""
    P = lambda px, py: (x + d * px * s, y - py * s)
    body = [P(-1.2, 1.4), P(-1.1, 2.1), P(0.0, 2.25), P(0.9, 2.15), P(1.35, 2.5), P(1.75, 3.0), P(2.15, 2.9), P(2.25, 2.55), P(1.7, 2.2),
            P(1.2, 1.5), P(0.8, 1.25), P(-0.6, 1.25), P(-1.2, 1.4)]
    legs = [capsule(P(-0.9, 1.4), P(-1.0, 0.0), 0.28 * s, 0.18 * s), capsule(P(-0.55, 1.3), P(-0.45, 0.0), 0.26 * s, 0.18 * s),
            capsule(P(0.6, 1.3), P(0.75, 0.0), 0.26 * s, 0.18 * s), capsule(P(0.95, 1.4), P(0.95, 0.0), 0.26 * s, 0.18 * s)]
    ears = [capsule(P(1.75, 3.0), P(1.55, 3.6), 0.14 * s, 0.08 * s), capsule(P(1.85, 3.0), P(1.8, 3.65), 0.14 * s, 0.08 * s)]
    sk.blob(legs[:2] + ears, grey(tone - 0.05), 1.5, (1, 0.3), True, 3, 0.5)
    sk.blob([body] + legs[2:], grey(tone), 1.6, (1, 0.3), True, 3, 0.5)
    sk.add(f'<circle cx="{P(2.0, 2.75)[0]:.1f}" cy="{P(2.0, 2.75)[1]:.1f}" r="{0.06 * s:.1f}" fill="{INK}"/>')
    sk.line([P(-1.2, 1.8), P(-1.5, 1.0)], 1.0, 0.7, passes=1)  # tail
    # packs and a rolled bundle
    sk.blob([[P(-0.9, 2.1), P(0.6, 2.1), P(0.7, 1.15), P(-1.0, 1.15)], ellipse_pts(*P(-0.15, 2.45), 0.8 * s, 0.3 * s, 14)], grey(0.7), 1.5, (1, 0.3), True, 3, 0.5)
    sk.line([P(-0.8, 1.9), P(0.5, 1.9)], 0.8, 0.5, passes=1)


@panel("1.1", "Arrival on the threshing floor in Moab. Wide, two groups: the family enters left; the Moabites stand right; Ruth and Orpah apart, watching.")
def p1_1(sk, rng):
    hz = 290
    sky(sk, hz, 0.82, 0.92)
    cloud_scribble(sk, rng, 100, 50, 1200, 150, 10, 0.18)
    flat = [(0, hz - 8), (200, hz - 18), (420, hz - 12), (700, hz - 22), (940, hz - 14), (1280, hz - 24)]
    ground_band(sk, hz - 30, H, 0.8, 0.62)
    ridge(sk, flat, 0.74, hz + 10, None, 1.3)
    houses(sk, rng, 960, hz - 16, 7, 0.9, 0.84)
    for x in (150, 260, 840):
        olive(sk, rng, x, hz - 6, 0.55)
    scribble_ground(sk, rng, 0, hz + 5, W, H, 100, 0.2)
    # the floor, with a grain heap and a threshing sledge at work
    fx, fy, rx, ry = 650, 500, 450, 95
    fl = ellipse_pts(fx, fy, rx, ry, 60)
    sk.fill(fl, grey(0.88), 1, amp=2)
    sk.line(fl, 1.5, 0.6, closed=True, amp=1.5)
    for k in range(40):
        a = 2 * math.pi * k / 40
        sk.line([(fx + math.cos(a) * (rx + 6), fy + math.sin(a) * (ry + 4)), (fx + math.cos(a) * (rx + 6) + 7, fy + math.sin(a) * (ry + 4) + 2)], 2.2, 0.5, passes=1)
    d = []
    for _ in range(140):
        a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.random()) * 0.9
        x, y = fx + math.cos(a) * rx * r, fy + math.sin(a) * ry * r
        d.append(f"M{x:.1f},{y:.1f}l{rng.uniform(3, 9):.1f},{rng.uniform(-2, 2):.1f}")
    sk.add(f'<path d="{"".join(d)}" stroke="{INK}" stroke-width="0.8" stroke-opacity="0.4" fill="none"/>')
    heap = [(820, 470), (850, 430), (900, 412), (960, 418), (1000, 440), (1030, 472)]
    sk.blob([heap + [(820, 472)]], grey(0.7), 1.6, (1, 0.4), True, 3, 0.5)
    d = []
    for _ in range(60):
        x = rng.uniform(835, 1015); y = rng.uniform(420, 468)
        d.append(f"M{x:.1f},{y:.1f}l{rng.uniform(-3, 3):.1f},{rng.uniform(4, 8):.1f}")
    sk.add(f'<path d="{"".join(d)}" stroke="{INK}" stroke-width="0.7" stroke-opacity="0.45" fill="none"/>')
    # Ruth and Orpah, apart, behind the men, small, watching the parents
    Figure(sk, pose_stand(women=True), 760, 455, 15, -1, tone=0.62, head="veil", veil_tone=0.5, face_turn=0.5, light=(1, 0.4)).draw()
    Figure(sk, pose_stand(women=True), 718, 452, 15, -1, tone=0.78, head="veil", veil_tone=0.66, face_turn=0.5, light=(1, 0.4),
           arms={"n": (20, 60)}).draw()
    # the Moabites, right, facing the newcomers
    L = (1, 0.5)
    moab_man(sk, 1220, 575, 26, -1, 0.5, True, {"n": (5, 10)}, L)
    moab_man(sk, 1150, 560, 25, -1, 0.66, False, {"n": {"e": (0.6, 4.8), "w": (0.9, 5.9)}}, L, beard=0.4)
    sk.line([(1150 - 0.95 * 25 + 10, 380), (1150 - 25 * 0.7, 575)], 2.0, 0.8)  # a winnowing fork
    for k in range(4):
        sk.line([(1150 - 0.95 * 25 + 10, 380), (1150 - 0.95 * 25 + 4 + k * 5, 350)], 1.0, 0.7, passes=1)
    moab_man(sk, 1070, 572, 26, -1, 0.72, True, {"n": {"e": (0.85, 4.75), "w": (-0.25, 5.05), "hand": "fist"}, "f": {"e": (-0.75, 4.75), "w": (0.4, 5.15), "hand": "fist"}}, L, expr="neutral")
    moab_man(sk, 1000, 548, 23, -1, 0.6, True, {}, L)
    moab_man(sk, 955, 538, 21, -1, 0.7, False, {"n": (30, 45)}, L, beard=0.5)
    # the family, left: Elimelech's hand on Mahlon's chest, holding him back
    donkey(sk, 70, 640, 34, 1, 0.55)
    Figure(sk, pose_stand(women=True), 195, 640, 28, 1, tone=0.42, head="veil", veil_tone=0.3, face_turn=0.5, light=L, expr="neutral").draw()
    Figure(sk, pose_stand(), 255, 622, 26, 1, tone=0.8, head="hair", hair_tone=0.28, face_turn=0.5, light=L).draw()
    Figure(sk, pose_stand(stride=0.3), 330, 655, 30, 1, tone=0.72, head="headcloth", beard=True, face_turn=0.55, light=L,
           arms={"n": {"e": (1.0, 5.1), "w": (2.1, 5.45), "hand": "open"}}, expr="stern").draw()
    Figure(sk, pose_stand(stride=0.25, lean=0.2), 420, 650, 29, 1, tone=0.8, head="hair", hair_tone=0.3, face_turn=0.6, light=L, expr="speak").draw()
    tag(sk, 418, 432, "Mahlon", 470, 400)
    tag(sk, 330, 445, "Elimelech", 300, 395)
    tag(sk, 195, 440, "Naomi", 150, 410)
    tag(sk, 255, 440, "Chilion", 250, 360)
    tag(sk, 760, 388, "Ruth", 800, 350)
    tag(sk, 718, 386, "Orpah", 680, 350)
    note(sk, 1120, 330, "Moabites", 15, anchor="middle")
    note(sk, 640, 690, "\u201cIsraelites.\u201d", 18, anchor="middle")


@panel("1.8", "The grave. Wide and high, noon, flat light: three at the grave and nobody else. Far right, small: Ruth with bread.")
def p1_8(sk, rng):
    # high angle: no sky, the frame is ground
    sk.rect_grad(0, 0, W, H, [(0, grey(0.74)), (1, grey(0.66))])
    sk.fill([(0, 0), (W, 0), (W, 46), (900, 58), (500, 40), (0, 54)], grey(0.82), 1, amp=2)
    sk.line([(0, 54), (500, 40), (900, 58), (W, 46)], 1.2, 0.5)
    scribble_ground(sk, rng, 0, 60, W, H, 150, 0.22)
    stones(sk, rng, 70, 0, 70, W, H - 10, (3, 10), 0.6, (0.2, 1))
    grass(sk, rng, 120, 0, 70, W, H, (3, 9), 0.35)
    # outcrops of bedrock
    for (x, y, rx_, ry_) in ((180, 200, 120, 40), (1050, 160, 150, 45), (300, 620, 160, 50), (980, 640, 190, 55)):
        pts = ellipse_pts(x, y, rx_, ry_, 14)
        pts = [(px + rng.uniform(-10, 10), py + rng.uniform(-6, 6)) for px, py in pts]
        sk.blob([pts], grey(0.76), 1.4, (0.2, 1), True, 3.5, 0.4, amp=2)
    # a path coming in from the right
    sk.line([(W, 470), (1100, 455), (980, 430), (860, 418)], 1.0, 0.4, passes=2)
    sk.line([(W, 500), (1100, 482), (980, 452), (860, 436)], 1.0, 0.4, passes=2)
    # the grave: fresh earth under a heap of stones
    gx, gy = 610, 380
    mound = ellipse_pts(gx, gy, 110, 46, 24)
    sk.blob([mound], grey(0.5), 1.8, (0.2, 1), True, 3, 0.5, amp=2)
    for _ in range(40):
        a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.random())
        x, y = gx + math.cos(a) * 95 * r, gy + math.sin(a) * 36 * r - 6
        s_ = rng.uniform(7, 13)
        pts = [(x + math.cos(t) * s_, y + math.sin(t) * s_ * 0.6) for t in [i * 2 * math.pi / 6 for i in range(6)]]
        sk.fill(pts, grey(0.7 + rng.uniform(-0.08, 0.08)), 1, amp=0.6, smooth=False)
        sk.line(pts, 0.9, 0.7, closed=True, passes=1, amp=0.4)
    # the three: Naomi, the two sons; seen from above (squashed), no shadows to speak of
    L = (0.15, 1)
    for (x, y, u, d, kw) in ((470, 430, 26, 1, dict(tone=0.4, head="veil", veil_tone=0.28, expr="grief", head_tilt=22, eyes="down")),
                             (745, 418, 25, -1, dict(tone=0.78, head="hair", hair_tone=0.28, expr="grief", head_tilt=18, eyes="down")),
                             (805, 446, 26, -1, dict(tone=0.72, head="hair", hair_tone=0.3, expr="grief", head_tilt=10, eyes="down",
                                                     arms={"n": {"e": (0.4, 4.7), "w": (1.2, 4.5)}}))):
        sk.fill(ellipse_pts(x, y, u * 1.0, u * 0.3, 14), INK, 0.25)
        group(sk, f"translate({x},{y}) scale(1,0.82) translate({-x},{-y})")
        Figure(sk, pose_stand(women=kw.get("head") == "veil"), x, y, u, d, light=L, face_turn=0.5, **kw).draw()
        end(sk)
    # far right, small: Ruth with bread
    rx0, ry0 = 1175, 560
    sk.fill(ellipse_pts(rx0, ry0, 12, 4, 10), INK, 0.25)
    group(sk, f"translate({rx0},{ry0}) scale(1,0.82) translate({-rx0},{-ry0})")
    Figure(sk, pose_stand(women=True), rx0, ry0, 13, -1, tone=0.7, head="veil", veil_tone=0.58, face_turn=0.5, light=L,
           arms={"n": (55, 80, "mitt", obj_bread)}).draw()
    end(sk)
    tag(sk, 1170, 470, "Ruth, with bread", 1140, 410)
    note(sk, 610, 300, "Elimelech's grave", 15, anchor="middle")
    note(sk, 40, 700, "camera high; noon, flat, no shadows", 15)


def fire(sk, rng, cx, cy, w, h):
    sk.radial(cx, cy - h * 0.3, w * 2.6, "#fffdf6", 0.85, 0.0, [(0.35, 0.45)])
    for k in range(5):
        a = math.radians(rng.uniform(-30, 30))
        x0 = cx + rng.uniform(-w * 0.5, w * 0.5)
        sk.line([(x0, cy + 10), (x0 + math.sin(a) * w * 0.6, cy - 6)], 9, 0.8, color=grey(0.25), passes=1)
    for k in range(9):
        x0 = cx + rng.uniform(-w * 0.45, w * 0.45)
        hh = h * rng.uniform(0.45, 1.0)
        ww = w * rng.uniform(0.14, 0.26)
        tip = (x0 + rng.uniform(-ww, ww), cy - hh)
        pts = [(x0 - ww, cy), (x0 - ww * 0.6, cy - hh * 0.4), tip, (x0 + ww * 0.7, cy - hh * 0.45), (x0 + ww, cy)]
        sk.fill(pts, "#ffffff", 0.75, amp=2)
        sk.line(pts, 1.2, 0.55, amp=1.5)
    for k in range(26):
        x, y = cx + rng.uniform(-w * 1.5, w * 1.5), cy - h - rng.uniform(0, 260)
        sk.add(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rng.uniform(1, 2.2):.1f}" fill="#ffffff" fill-opacity="0.85"/>')


def obj_drum(sk, Wr, ang, u, fig):
    c = (Wr[0] + math.cos(ang) * 0.3 * u, Wr[1] + math.sin(ang) * 0.3 * u - 0.3 * u)
    sk.shape(ellipse_pts(c[0], c[1], 0.32 * u, 0.85 * u, 20), grey(0.7), fig.lw)
    sk.line(ellipse_pts(c[0], c[1], 0.22 * u, 0.7 * u, 20), 0.8, 0.4, closed=True, passes=1)


@panel("1.11", "The double wedding. Medium wide, night, firelight from below: Naomi dancing in the middle of Moab, arms up; Ruth and Orpah either side.")
def p1_11(sk, rng):
    sk.rect_grad(0, 0, W, H, [(0, grey(0.12)), (0.6, grey(0.22)), (1, grey(0.3))])
    for k in range(40):
        sk.add(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, 150):.0f}" r="{rng.uniform(0.6, 1.5):.1f}" fill="#ffffff" fill-opacity="{rng.uniform(0.3, 0.8):.2f}"/>')
    # a house wall and roofline behind, just caught by the fire
    sk.fill([(0, 300), (380, 290), (380, 520), (0, 520)], grey(0.25), 1, amp=1)
    sk.fill([(900, 280), (1280, 290), (1280, 520), (900, 520)], grey(0.25), 1, amp=1)
    sk.line([(0, 300), (380, 290), (380, 520)], 1.2, 0.5)
    sk.line([(900, 520), (900, 280), (1280, 290)], 1.2, 0.5)
    sk.radial(640, 640, 700, "#fff8ea", 0.5, 0.0, [(0.4, 0.22)])
    sk.fill([(0, 560), (W, 550), (W, H), (0, H)], grey(0.3), 0.7, amp=1)
    L = (0, -1)  # light travels upward from the fire
    kw = dict(light=L, hatch_op=0.6)
    # Moab round the edges: drummer, clappers, faces caught by the fire
    Figure(sk, pose_stand(short=True), 1215, 735, 56, -1, tone=0.3, head="headcloth", beard=True, face_turn=0.6, expr="laugh",
           arms={"n": {"e": (0.9, 4.9), "w": (1.6, 5.8)}, "f": {"e": (-0.3, 4.9), "w": (0.8, 6.4), "hand": "mitt", "obj": obj_drum}}, **kw).draw()
    Figure(sk, pose_stand(women=True), 1085, 690, 46, -1, tone=0.36, head="veil", veil_tone=0.25, face_turn=0.5, expr="smile",
           arms={"n": {"e": (1.0, 4.8), "w": (1.5, 5.9), "hand": "open"}, "f": {"e": (-0.1, 4.8), "w": (1.3, 6.1), "hand": "open"}}, **kw).draw()
    Figure(sk, pose_stand(), 60, 740, 58, 1, tone=0.3, head="headcloth", beard=True, face_turn=0.6, expr="laugh",
           arms={"n": {"e": (0.9, 4.9), "w": (1.6, 5.9), "hand": "open"}, "f": {"e": (0.1, 4.9), "w": (1.4, 6.2), "hand": "open"}}, **kw).draw()
    Figure(sk, pose_stand(short=True), 200, 690, 46, 1, tone=0.38, head="hair", hair_tone=0.2, beard=0.3, face_turn=0.55, expr="smile", **kw).draw()
    # Ruth and Orpah, the brides, either side, clapping
    Figure(sk, pose_stand(women=True, lean=0.1), 410, 655, 50, 1, tone=0.82, head="veil", veil_tone=0.72, face_turn=0.5, expr="smile",
           arms={"n": {"e": (1.05, 4.9), "w": (1.6, 5.75), "hand": "open"}, "f": {"e": (0.05, 4.9), "w": (1.35, 5.95), "hand": "open"}}, **kw).draw()
    Figure(sk, pose_stand(women=True, lean=0.1), 880, 655, 50, -1, tone=0.78, head="veil", veil_tone=0.68, face_turn=0.5, expr="laugh",
           arms={"n": {"e": (1.05, 4.9), "w": (1.6, 5.75), "hand": "open"}, "f": {"e": (0.05, 4.9), "w": (1.35, 5.95), "hand": "open"}}, **kw).draw()
    # Naomi, dancing, arms up, laughing
    Figure(sk, pose_dance(), 640, 640, 56, 1, tone=0.5, head="veil", veil_tone=0.36, face_turn=0.3, expr="laugh", head_tilt=-14,
           arms={"n": {"e": (1.25, 7.2), "w": (1.05, 8.6), "hand": "open"}, "f": {"e": (-1.05, 7.1), "w": (-1.4, 8.4), "hand": "open"}}, **kw).draw()
    fire(sk, rng, 640, 712, 90, 120)
    note(sk, 1255, 704, "then fade to black", 16, "#e6c9bb", "end")
    note(sk, 640, 40, "firelight from below", 15, "#d9b8a8", "middle")


def cairn(sk, rng, x, y, w, h, tone=0.62, light=(0.1, 1)):
    base = ellipse_pts(x, y, w / 2, h * 0.35, 18)
    sk.blob([[(x - w / 2, y), (x - w * 0.3, y - h * 0.7), (x, y - h), (x + w * 0.32, y - h * 0.72), (x + w / 2, y)]], grey(tone), 1.6, light, True, 3.2, 0.5)
    for _ in range(int(w / 6)):
        px = x + rng.uniform(-w * 0.42, w * 0.42)
        top = y - h * (1 - abs(px - x) / (w / 2)) ** 0.8
        py = rng.uniform(top + 4, y - 2)
        s_ = rng.uniform(5, 10) * w / 160
        pts = [(px + math.cos(t) * s_, py + math.sin(t) * s_ * 0.6) for t in [i * 2 * math.pi / 6 for i in range(6)]]
        sk.line(pts, 0.8, 0.55, closed=True, passes=1, amp=0.3)


@panel("1.17", "Three graves. Medium, low angle, overcast: Moab at the edges, mourning them as kin; centre, Naomi kneeling, binding Ruth's arms. No words.")
def p1_17(sk, rng):
    hz = 470
    sky(sk, hz, 0.62, 0.8)
    for k in range(5):
        y = 40 + k * 70
        band = [(x, y + 18 * math.sin(x / 140 + k)) for x in range(-20, W + 40, 60)]
        sk.fill(band + [(W + 40, y + 60), (-20, y + 60)], grey(0.55 + k * 0.04), 0.35, amp=4)
    cloud_scribble(sk, rng, 0, 20, W, 380, 22, 0.25, 1.1)
    ground = [(0, hz), (300, hz - 6), (700, hz + 4), (1000, hz - 4), (W, hz + 2)]
    ridge(sk, ground, 0.6, H, (0.1, 1), 1.6, 4, 0.25)
    scribble_ground(sk, rng, 0, hz + 10, W, H, 80, 0.25)
    for x in (330, 640, 950):
        cairn(sk, rng, x, hz + 8, 170, 62, 0.58)
    L = (0.1, 1)
    # Moab at the edges, mourning them as kin
    Figure(sk, pose_crouch_mourn(), 220, 640, 34, 1, tone=0.42, head="veil", veil_tone=0.32, expr="grief", face_turn=0.5, light=L,
           arms={"n": {"e": (1.25, 3.4), "w": (1.0, 4.6), "hand": "mitt"}, "f": {"e": (0.2, 3.5), "w": (0.45, 4.7)}}).draw()
    Figure(sk, pose_stand(), 1085, 640, 32, -1, tone=0.4, head="hair", hair_tone=0.55, beard=False, expr="grief", face_turn=0.5, light=L, head_tilt=20,
           arms={"n": {"e": (0.85, 5.0), "w": (0.5, 6.6), "hand": "open"}, "f": {"e": (-0.6, 5.0), "w": (-0.2, 6.7), "hand": "open"}}).draw()
    Figure(sk, pose_stand(women=True), 70, 850, 70, 1, tone=0.32, head="veil", veil_tone=0.24, expr="grief", face_turn=0.6, light=L, head_tilt=-18,
           arms={"n": {"e": (1.0, 7.0), "w": (1.1, 8.4), "hand": "open"}, "f": {"e": (-0.5, 7.0), "w": (-0.6, 8.3), "hand": "open"}}).draw()
    Figure(sk, pose_stand(), 1210, 860, 72, -1, tone=0.34, head="headcloth", beard=True, expr="grief", face_turn=0.5, light=L, head_tilt=14,
           arms={"n": {"e": (0.9, 6.5), "w": (0.25, 7.5), "hand": "mitt"}, "f": {"e": (-0.85, 6.5), "w": (-0.2, 7.5)}}).draw()
    # Ruth, sitting back on her heels, arm held out; Naomi kneeling, binding it with a strip torn from her dress
    Figure(sk, pose_sit_heels(), 790, 712, 56, -1, tone=0.74, head="veil", veil_tone=0.62, expr="neutral", eyes="down", face_turn=0.55, light=L, head_tilt=16,
           arms={"n": {"e": (0.95, 3.0), "w": (2.05, 3.05), "hand": "open"}, "f": {"e": (0.4, 2.7), "w": (1.2, 2.5)}}).draw()
    Figure(sk, pose_kneel_up(), 545, 712, 56, 1, tone=0.4, head="veil", veil_tone=0.3, expr="grief", eyes="down", face_turn=0.6, light=L, head_tilt=20,
           arms={"n": {"e": (1.3, 3.7), "w": (2.1, 3.3), "hand": "mitt"}, "f": {"e": (0.9, 3.9), "w": (1.8, 3.65), "hand": "mitt"}}).draw()
    # the binding: a pale strip round Ruth's forearm, its torn end hanging from Naomi's hand
    bx, by = 660, 538
    for k in range(3):
        sk.fill([(bx - 14 + k * 9, by - 18), (bx - 6 + k * 9, by - 19), (bx - 4 + k * 9, by + 13), (bx - 12 + k * 9, by + 14)], "#f6f3ec", 1, amp=0.5, smooth=False)
        sk.line([(bx - 14 + k * 9, by - 18), (bx - 12 + k * 9, by + 14)], 1.0, 0.8, passes=1)
    sk.line([(bx + 14, by + 8), (bx + 22, by + 40), (bx + 12, by + 70)], 6, 0.25, passes=1)
    sk.line([(bx + 14, by + 8), (bx + 22, by + 40), (bx + 12, by + 70)], 1.2, 0.8, passes=1)
    # the tear in Naomi's dress
    sk.line([(585, 520), (592, 548), (583, 568), (596, 600)], 1.6, 0.85, passes=1)
    note(sk, 1000, 700, "no words", 16, anchor="middle")
    note(sk, 640, 40, "low angle; overcast", 15, anchor="middle")


def flutter(sk, f, at, length, droop, tone, width=0.5):
    """Cloth streaming downwind (to screen right) from a point on a figure."""
    p = f.P(at)
    u = f.u
    pts = [(p[0], p[1] - width * u * 0.5)]
    for k in range(1, 6):
        t = k / 5
        pts.append((p[0] + length * u * t, p[1] + droop * u * t - width * u * 0.5 * (1 - t * 0.6) + math.sin(t * 7) * 0.12 * u))
    for k in range(5, -1, -1):
        t = k / 5
        pts.append((p[0] + length * u * t * 0.95, p[1] + droop * u * t + width * u * 0.5 * (1 - t * 0.6) + math.sin(t * 7 + 1) * 0.12 * u))
    sk.blob([pts], grey(tone), f.lw, f.light, True, 3.2, 0.5)


@panel("1.21", "The parting on the road. Wide, then close: the road at the rift's edge; Orpah going back right and up; Naomi facing Ruth. The wind. The oath; the nod.")
def p1_21(sk, rng):
    hz = 290
    sky(sk, hz, 0.78, 0.9)
    cloud_scribble(sk, rng, 380, 40, 1250, 160, 14, 0.22)
    # the far side: Judah's hills across the rift (left), the plateau rising behind (right)
    judah = [(0, hz - 30), (120, hz - 46), (260, hz - 38), (420, hz - 52), (560, hz - 30), (700, hz - 14), (900, hz - 10)]
    ridge(sk, judah, 0.74, hz + 40, None, 1.2)
    sk.rect_grad(0, hz - 12, W, hz + 150, [(0, grey(0.86), 0.0), (0.12, grey(0.86), 1), (1, grey(0.8), 1)])
    plateau = [(560, hz + 40), (700, hz - 20), (860, hz - 60), (1040, hz - 78), (1280, hz - 84)]
    ridge(sk, plateau, 0.66, H, (1, 0.4), 1.5, 4, 0.3)
    lip = [(0, hz + 140), (200, hz + 128), (420, hz + 120), (620, hz + 108), (800, hz + 90), (1000, hz + 60), (1280, hz + 30)]
    ridge(sk, lip, 0.68, H, (1, 0.4), 1.8, 4, 0.3)
    for x in range(0, 700, 22):
        sk.line([(x, hz + 140 - x * 0.05), (x - 10, hz + 150 - x * 0.05)], 0.8, 0.4, passes=1)
    scribble_ground(sk, rng, 0, hz + 120, W, H, 90, 0.22)
    # the road: in from the bottom left, up across to the right and over the rise
    road_l = [(-20, H), (300, 610), (620, 520), (900, 430), (1120, 360), (1280, 330)]
    road_r = [(240, H), (520, 640), (780, 545), (980, 455), (1160, 378), (1280, 352)]
    sk.fill(road_l + road_r[::-1], grey(0.86), 1, amp=2)
    sk.line(road_l, 1.4, 0.65)
    sk.line(road_r, 1.4, 0.65)
    for k in range(30):
        t = rng.random()
        i = int(t * (len(road_l) - 1))
        f = t * (len(road_l) - 1) - i
        a = lerp2(road_l[i], road_l[i + 1], f); b = lerp2(road_r[i], road_r[i + 1], f)
        p = lerp2(a, b, rng.uniform(0.2, 0.8))
        sk.line([p, (p[0] + rng.uniform(8, 20), p[1] - rng.uniform(1, 4))], 0.8, 0.35, passes=1)
    stones(sk, rng, 16, 0, 600, 1280, 712, (5, 12), 0.6, (1, 0.4))
    grass(sk, rng, 50, 700, 560, 1280, 715, (6, 16), 0.5)
    L = (1, 0.4)
    # Orpah, small, going back up the road, looking over her shoulder
    Figure(sk, pose_stand(women=True, stride=0.45, lean=0.15), 1035, 418, 17, 1, tone=0.7, head="veil", veil_tone=0.55, face_turn=-0.4, light=L,
           arms={"n": (-15, -5), "f": (20, 25)}).draw()
    # Naomi (left, facing right) and Ruth (facing her), Ruth clinging to her; the wind pulls their mantles right
    nf = Figure(sk, pose_stand(women=True), 385, 655, 40, 1, tone=0.42, head="veil", veil_tone=0.3, face_turn=0.55, light=L, expr="sad",
                arms={"n": {"e": (0.95, 4.9), "w": (1.7, 4.4), "hand": "open"}, "f": (-10, 0)})
    nf.draw()
    flutter(sk, nf, (0.55, 6.3), 1.5, 0.9, 0.3, 0.45)
    rf = Figure(sk, pose_stand(women=True, lean=0.2), 560, 650, 40, -1, tone=0.72, head="veil", veil_tone=0.6, face_turn=0.6, light=L, expr="speak",
                arms={"n": {"e": (1.15, 4.8), "w": (2.15, 5.0), "hand": "mitt"}, "f": {"e": (0.75, 4.7), "w": (1.75, 4.55), "hand": "mitt"}})
    flutter(sk, rf, (-0.3, 6.4), 2.2, 1.1, 0.6, 0.55)
    rf.draw()
    dust_streaks(sk, rng, 0, 380, 900, 640, 26, 0.35, -0.03)
    arrow(sk, [(40, 250), (170, 244), (300, 248)], label="wind from the west", label_dy=-12)
    arrow(sk, [(1075, 440), (1150, 395), (1215, 360)], label=None)
    tag(sk, 1035, 285, "Orpah, back to her mother's house", 1000, 240)
    tag(sk, 385, 380, "Naomi", 330, 350)
    tag(sk, 560, 380, "Ruth", 610, 350)
    # inset: the close two-shot of the oath
    sub = sub_sketch(sk, 21)
    sub.rect_grad(0, 0, W, H, [(0, grey(0.8)), (1, grey(0.7))])
    cloud_scribble(sub, rng, 0, 40, W, 300, 8, 0.2)
    Figure(sub, pose_stand(women=True), 400, 1390, 150, 1, tone=0.42, head="veil", veil_tone=0.3, face_turn=0.6, light=L, expr="sad", eyes="down",
           arms={"n": "none", "f": "none"}).draw()
    Figure(sub, pose_stand(women=True), 900, 1400, 150, -1, tone=0.72, head="veil", veil_tone=0.6, face_turn=0.65, light=L, expr="speak",
           arms={"n": "none", "f": "none"}).draw()
    note(sub, 650, 190, "\u201cWhere you go, I will go...\u201d", 36, RED, "middle")
    embed(sk, sub, 700, 480, 380, 214, 210, 140, 880, 495, "CLOSE: the oath; Naomi's nod")


def gate_tower(sk, rng, x0, x1, y0, y1, tone=0.7, light=(1, 0.3), course=16):
    masonry(sk, rng, x0, y0, x1, y1, course, tone, 0.45)
    sk.hatch_region([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]], 4, None, 0.8, 0.35, light, 0.4, 1.0, smooth=False)


@panel("1.25", "The well by the gate. Medium, hazy: the town women in a group under the gate; Naomi and Ruth in the foreground, dusty, apart. \u201cCall me Mara.\u201d")
def p1_25(sk, rng):
    hz = 470
    sky(sk, hz, 0.86, 0.93)
    sk.fill([(0, hz), (W, hz), (W, H), (0, H)], grey(0.8), 1, smooth=False)
    scribble_ground(sk, rng, 0, hz, W, H, 90, 0.18)
    # the town wall and the gate, hazy
    houses(sk, rng, 20, 330, 14, 2.2, 0.86)
    masonry(sk, rng, 0, 330, 640, hz + 40, 15, 0.8, 0.22)
    gate_tower(sk, rng, 640, 780, 150, hz + 50, 0.78, (1, 0.3))
    gate_tower(sk, rng, 1060, 1210, 140, hz + 52, 0.76, (1, 0.3))
    gate_tower(sk, rng, 1210, 1280, 300, hz + 50, 0.8, (1, 0.3))
    sk.fill([(780, 230), (1060, 230), (1060, hz + 50), (780, hz + 50)], grey(0.5), 1, smooth=False)
    sk.hatch_region([[(780, 230), (1060, 230), (1060, hz + 50), (780, hz + 50)]], 3.5, None, 0.8, 0.4, smooth=False)
    sk.shape([(770, 200), (1070, 196), (1072, 232), (770, 236)], grey(0.66), 1.6, amp=0.6)  # lintel
    sk.line([(640, 150), (780, 150)], 1.2, 0.6)
    # the women under the gate, in a group, looking at the two newcomers; the friend in front, straightened up, staring
    L = (1, 0.3)
    hz_kw = dict(light=L, line_op=0.62, hatch_op=0.3)
    for (x, y, u, tone, jarp) in ((1000, 520, 22, 0.78, True), (935, 516, 22, 0.72, False), (880, 524, 23, 0.82, True), (820, 522, 22, 0.76, False), (960, 530, 23, 0.7, False)):
        f = Figure(sk, pose_stand(women=True), x, y, u, -1, tone=tone, head="veil", veil_tone=tone - 0.12, face_turn=0.45,
                   arms={"n": {"e": (0.75, 6.4), "w": (0.4, 7.7), "hand": "mitt"}} if jarp else {"n": (20, 40)}, **hz_kw)
        f.draw()
        if jarp:
            hx, hy = f.P((0.18, 7.55))
            jar(sk, rng, hx, hy, 18, 24, 0.75, L, 0.45, 1.0, handles=False, dark_inside=False)
    jar(sk, rng, 770, 548, 22, 28, 0.74, L, 0.45, 1.1, handles=False)
    Figure(sk, pose_stand(women=True), 735, 548, 26, -1, tone=0.68, head="veil", veil_tone=0.55, face_turn=0.55, expr="speak",
           arms={"n": {"e": (0.8, 4.9), "w": (0.45, 6.0), "hand": "open"}}, light=L, line_op=0.75, hatch_op=0.35).draw()
    tag(sk, 735, 360, "her old friend: \u201cNaomi?\u201d", 640, 300)
    # the well: a stone curb with a trough
    wx, wy = 520, 610
    sk.blob([ellipse_pts(wx, wy, 100, 26, 24), [(wx - 100, wy), (wx + 100, wy), (wx + 100, wy + 40), (wx - 100, wy + 40)],
             ellipse_pts(wx, wy + 40, 100, 26, 24)], grey(0.72), 1.8, L, True, 3.2, 0.45, soft=0)
    sk.fill(ellipse_pts(wx, wy, 82, 18, 20), grey(0.25), 1, amp=0.8)
    for k in range(10):
        x = wx - 95 + k * 21
        sk.line([(x, wy + 6 + 18 * math.sin(math.pi * k / 9) ** 0.5), (x + 2, wy + 50)], 0.8, 0.5, passes=1)
    sk.blob([[(wx + 105, wy + 30), (wx + 230, wy + 32), (wx + 226, wy + 58), (wx + 108, wy + 56)]], grey(0.7), 1.5, L, True, 3, 0.4, soft=0)
    # Naomi and Ruth, foreground left, dusty, bundles on their backs, apart from the women
    Figure(sk, pose_stand(women=True), 165, 790, 60, 1, tone=0.66, head="veil", veil_tone=0.54, face_turn=0.65, eyes="open", expr="neutral", light=L,
           arms={"n": (8, 14), "f": {"e": (-0.9, 5.0), "w": (-0.6, 6.0)}},
           props=[("before_head", lambda sk_, f: bundle(sk_, f, (-0.9, 5.6), 1.0))]).draw()
    Figure(sk, pose_stand(women=True), 335, 800, 64, 1, tone=0.42, head="veil", veil_tone=0.3, face_turn=0.5, expr="sad", light=L,
           arms={"n": (5, 10), "f": (-6, -2)}, props=[("before_head", lambda sk_, f: bundle(sk_, f, (-0.95, 5.4), 1.1))]).draw()
    for _ in range(40):  # dust of the road on their hems
        x = rng.uniform(80, 420); y = rng.uniform(560, 715)
        sk.add(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rng.uniform(0.6, 1.4):.1f}" fill="{INK}" fill-opacity="0.35"/>')
    note(sk, 450, 100, "Naomi: \u201cDon't call me Naomi. Call me Mara.\u201d", 19)
    tag(sk, 175, 320, "Ruth", 130, 290)
    tag(sk, 345, 300, "Naomi", 390, 268)


def bundle(sk, f, at, size):
    c = f.P(at)
    u = f.u * size
    pts = [(c[0] - 0.55 * u, c[1] - 0.7 * u), (c[0] - 0.1 * u, c[1] - 0.85 * u), (c[0] + 0.45 * u, c[1] - 0.6 * u), (c[0] + 0.5 * u, c[1] + 0.2 * u),
           (c[0] + 0.2 * u, c[1] + 0.75 * u), (c[0] - 0.4 * u, c[1] + 0.7 * u), (c[0] - 0.65 * u, c[1] + 0.1 * u)]
    sk.blob([pts], grey(0.62), f.lw, f.light, True, 3, 0.5)
    sk.line([(c[0] - 0.5 * u, c[1] - 0.2 * u), (c[0] + 0.1 * u, c[1] + 0.3 * u), (c[0] + 0.45 * u, c[1] - 0.1 * u)], f.lw * 0.6, 0.5, passes=1)
    sk.line([(c[0] + 0.2 * u, c[1] - 0.75 * u), (c[0] + 0.9 * u, c[1] - 1.5 * u)], f.lw * 1.4, 0.75, passes=1)  # the strap over the shoulder


def barley(sk, rng, x0, x1, y_back, y_front, n, h_back=10, h_front=34, op=0.55):
    """Standing barley: stalks with drooping bearded heads, bigger toward the front."""
    d = []
    heads = []
    for _ in range(n):
        y = rng.uniform(y_back, y_front)
        t = (y - y_back) / max(y_front - y_back, 1)
        h = lerp(h_back, h_front, t) * rng.uniform(0.8, 1.15)
        x = rng.uniform(x0, x1)
        lean = rng.uniform(-0.2, 0.35)
        top = (x + lean * h * 0.5, y - h)
        d.append(f"M{x:.1f},{y:.1f}Q{x:.1f},{y - h * 0.6:.1f} {top[0]:.1f},{top[1]:.1f}")
        heads.append((top, h, lean))
    sk.add(f'<path d="{"".join(d)}" fill="none" stroke="{INK}" stroke-width="0.8" stroke-opacity="{op}"/>')
    d = []
    for (tx, ty), h, lean in heads:
        L = h * 0.28
        d.append(f"M{tx:.1f},{ty:.1f}l{L * (0.5 + lean):.1f},{L * 0.7:.1f}")
        for k in range(3):
            d.append(f"M{tx + L * 0.2 * k:.1f},{ty + L * 0.25 * k:.1f}l{L * 0.5:.1f},{-L * 0.2:.1f}")
    sk.add(f'<path d="{"".join(d)}" fill="none" stroke="{INK}" stroke-width="{1.1}" stroke-opacity="{op}" stroke-linecap="round"/>')


def stubble(sk, rng, x0, y0, x1, y1, n, op=0.45):
    d = []
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        t = (y - y0) / max(y1 - y0, 1)
        h = lerp(2, 9, t)
        d.append(f"M{x:.1f},{y:.1f}l{rng.uniform(-1.5, 1.5):.1f},{-h:.1f}")
    sk.add(f'<path d="{"".join(d)}" fill="none" stroke="{INK}" stroke-width="0.9" stroke-opacity="{op}"/>')


def sheaf(sk, rng, x, y, s=1.0, tone=0.78):
    pts = [(x - 10 * s, y), (x - 7 * s, y - 14 * s), (x - 14 * s, y - 30 * s), (x, y - 36 * s), (x + 14 * s, y - 30 * s), (x + 7 * s, y - 14 * s), (x + 10 * s, y)]
    sk.blob([pts], grey(tone), 1.2, (0.2, 1), True, 3, 0.4)
    sk.line([(x - 8 * s, y - 15 * s), (x + 8 * s, y - 15 * s)], 1.6, 0.8, passes=1)


@panel("2.5", "The field. Wide, then two-shot, hard midday: the reapers in a line; Ruth behind them, lower, gleaning; Boaz comes to her through the line.")
def p2_5(sk, rng):
    hz = 220
    sky(sk, hz, 0.88, 0.95)
    hills = [(0, hz - 20), (180, hz - 50), (380, hz - 70), (560, hz - 62), (760, hz - 40), (980, hz - 58), (1280, hz - 30)]
    ridge(sk, hills, 0.76, hz + 30, (0.2, 1), 1.3, 4, 0.25)
    houses(sk, rng, 330, hz - 68, 9, 0.8, 0.88)
    terraces(sk, rng, 0, 1280, hz - 40, hz + 10, 3, 0.3, stubble=False, curve=4)
    sk.rect_grad(0, hz, W, H, [(0, grey(0.84)), (1, grey(0.8))])
    # standing barley beyond the reapers
    barley(sk, rng, 0, W, hz + 10, 380, 900, 6, 26, 0.5)
    sk.line([(0, 380), (W, 385)], 1.0, 0.35, passes=1)
    # the stubble field toward us
    stubble(sk, rng, 0, 390, W, H, 900, 0.4)
    L = (0.15, 1)  # sun overhead
    # the reapers in a line, bent to the sickle; sheaves behind them; a gap where Boaz has come through
    for x, y, s_ in ((90, 425, 22), (230, 428, 22), (380, 424, 22), (900, 426, 22), (1040, 430, 22), (1180, 426, 22)):
        sk.fill(ellipse_pts(x + 8, y + 2, 24, 4, 12), INK, 0.35)
        Figure(sk, pose_reap(), x, y, s_, 1, tone=0.82, head="headcloth", beard=0.45, face_turn=0.6, light=L, hatch_op=0.35,
               arms={"n": (35, 15, "fist", obj_sickle), "f": {"e": (1.4, 3.1), "w": (2.2, 2.9), "hand": "fist", "obj": obj_stalks}}).draw()
    for x in (40, 170, 320, 470, 850, 990, 1120, 1250):
        sheaf(sk, rng, x, 470 + rng.uniform(-6, 6), 0.9)
    # Boaz, through the line, standing over her; Ruth gleaning, low, in front of us
    sk.fill(ellipse_pts(770, 642, 52, 8, 14), INK, 0.4)
    Figure(sk, pose_stand(stride=0.35, lean=0.1), 770, 640, 48, -1, tone=0.85, head="headcloth", beard=0.5, face_turn=0.6, light=L, expr="speak",
           arms={"n": {"e": (1.0, 4.95), "w": (1.9, 5.6), "hand": "open"}, "f": (-10, -4)}, props=[("before_head", lambda sk_, f: mantle_over(sk_, f, 0.55))]).draw()
    sk.fill(ellipse_pts(470, 662, 80, 9, 14), INK, 0.4)
    Figure(sk, pose_bend_glean(), 440, 660, 50, 1, tone=0.68, head="veil", veil_tone=0.56, face_turn=0.45, light=L, expr="neutral", head_tilt=0,
           arms={"n": {"e": (1.95, 2.3), "w": (2.45, 1.25), "hand": "mitt", "obj": obj_stalks}, "f": {"e": (1.2, 2.5), "w": (1.9, 1.9), "hand": "fist"}}).draw()
    for _ in range(14):  # stalks dropped on purpose
        x = rng.uniform(520, 700); y = rng.uniform(640, 690)
        sk.line([(x, y), (x + rng.uniform(15, 30), y - rng.uniform(-4, 6))], 1.0, 0.65, passes=1)
    tag(sk, 770, 290, "Boaz", 820, 255)
    tag(sk, 520, 470, "Ruth", 560, 440)
    note(sk, 40, 690, "Ruth: \u201cWhy would you notice me? I'm a foreigner.\u201d", 18)
    note(sk, 1240, 260, "hard midday: shadows under them", 15, anchor="end")


def mantle_over(sk, f, tone):
    """A man's outer cloak over the shoulders (a man of standing)."""
    pts = [f.P(p) for p in ((-0.8, 6.15), (0.45, 6.15), (0.3, 4.6), (0.2, 1.5), (-0.5, 1.3), (-1.15, 1.45), (-1.0, 4.4))]
    sk.blob([pts], grey(tone), f.lw, f.light, True, 3.4, 0.45)
    for k in (-0.75, -0.45, -0.15):  # a striped cloak
        sk.line([f.P((k, 6.0)), f.P((k - 0.15, 1.5))], f.lw * 1.6, 0.35, passes=1)


@panel("2.6", "The meal. Medium, in shade, the bright field behind: reapers either side; Boaz's hand with the roasted grain reaching to hers. \u201cYou.\u201d")
def p2_6(sk, rng):
    # the bright field behind, almost paper
    hz = 300
    sky(sk, hz, 0.93, 0.97)
    ridge(sk, [(0, hz - 30), (300, hz - 52), (700, hz - 40), (1000, hz - 56), (1280, hz - 36)], 0.86, hz + 10, None, 1.0)
    sk.fill([(0, hz), (W, hz), (W, H), (0, H)], grey(0.93), 1, smooth=False)
    barley(sk, rng, 0, W, hz + 4, 420, 500, 6, 20, 0.35)
    for x in (230, 340, 1000):
        f = Figure(sk, pose_reap(), x, 380, 12, 1, tone=0.9, head="headcloth", light=(0.1, 1), hatch=False, line_op=0.5)
        f.draw()
    # the shade: the shelter's roof of branches, its posts, the dark ground under it
    shade = [(0, 0), (W, 0), (W, H), (0, H)]
    sk.fill([(0, 470), (W, 455), (W, H), (0, H)], grey(0.4), 1, amp=2)
    sk.hatch_region([[(0, 470), (W, 455), (W, H), (0, H)]], 4, None, 0.8, 0.35, smooth=False)
    roof = [(0, 0), (W, 0), (W, 120), (1100, 140), (900, 118), (640, 132), (400, 116), (200, 138), (0, 120)]
    sk.fill(roof, grey(0.3), 1, amp=4)
    for k in range(70):
        x = rng.uniform(0, W); y = rng.uniform(90, 150)
        sk.line([(x, y - 30), (x + rng.uniform(-14, 14), y)], 1.0, 0.7, passes=1)
        sk.add(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rng.uniform(4, 8):.1f}" ry="{rng.uniform(2, 4):.1f}" fill="{grey(0.3)}" stroke="{INK}" stroke-width="0.6" stroke-opacity="0.6"/>')
    for x in (60, 1220):
        sk.blob([[(x - 14, 0), (x + 14, 0), (x + 16, 720), (x - 16, 720)]], grey(0.32), 2.0, None, False, soft=0)
    sk.blob([[(632, 0), (652, 0), (654, 480), (630, 480)]], grey(0.34), 1.8, None, False, soft=0)
    L = (0, 0.25)
    kw = dict(light=L, hatch_op=0.5)
    # the reapers either side, eating
    Figure(sk, pose_sit_side(), 120, 690, 44, 1, tone=0.48, head="headcloth", beard=0.35, face_turn=0.5, expr="smile",
           arms={"n": {"e": (1.2, 3.1), "w": (1.0, 4.4), "hand": "mitt", "obj": obj_bread}}, **kw).draw()
    Figure(sk, pose_sit_side(), 1180, 700, 46, -1, tone=0.44, head="headcloth", beard=0.3, face_turn=0.55, expr="speak",
           arms={"n": {"e": (1.3, 3.0), "w": (2.2, 3.3), "hand": "cup"}}, **kw).draw()
    # the bowl of vinegar and the bread between them
    sk.blob([ellipse_pts(640, 660, 46, 14, 16), [(594, 660), (686, 660), (670, 684), (610, 684)]], grey(0.6), 1.6, L, True, 3, 0.45)
    sk.fill(ellipse_pts(640, 660, 38, 9, 14), grey(0.25), 1)
    sk.shape(ellipse_pts(580, 690, 34, 12, 14), grey(0.68), 1.4)
    # Ruth, left, cupped hands out; Boaz, right, reaching across with the roasted grain
    Figure(sk, pose_sit_side(), 465, 662, 52, 1, tone=0.6, head="veil", veil_tone=0.48, face_turn=0.6, expr="neutral",
           arms={"n": {"e": (1.55, 3.0), "w": (2.6, 3.3), "hand": "cup"}, "f": {"e": (1.2, 2.95), "w": (2.2, 3.05), "hand": "cup"}}, **kw).draw()
    Figure(sk, pose_sit_side(), 830, 668, 54, -1, tone=0.7, head="headcloth", beard=0.48, face_turn=0.55, expr="smile",
           arms={"n": {"e": (1.4, 3.75), "w": (2.65, 3.45), "hand": "cup", "obj": obj_grain}}, props=[("before_head", lambda sk_, f: mantle_over_sit(sk_, f, 0.5))], **kw).draw()
    note(sk, 640, 210, "\u201cYou.\u201d", 22, anchor="middle")
    note(sk, 640, 590, "roasted grain, his hand to hers", 15, anchor="middle")
    note(sk, 1000, 260, "bright field behind", 15)


def mantle_over_sit(sk, f, tone):
    pts = [f.P(p) for p in ((-0.55, 4.35), (0.7, 4.25), (0.8, 3.2), (0.6, 2.2), (-0.8, 2.0), (-0.75, 3.4))]
    sk.blob([pts], grey(tone), f.lw, f.light, True, 3.4, 0.45)


@panel("3.5", "Midnight on the threshing floor. Close, night, moon only: the heap of grain; Boaz starting awake, an arm up; Ruth at his feet. An arm's length between them.")
def p3_5(sk, rng):
    sk.rect_grad(0, 0, W, H, [(0, grey(0.1)), (0.55, grey(0.2)), (1, grey(0.26))])
    for _ in range(60):
        sk.add(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, 260):.0f}" r="{rng.uniform(0.6, 1.5):.1f}" fill="#ffffff" fill-opacity="{rng.uniform(0.25, 0.7):.2f}"/>')
    mx, my = 1120, 105
    sk.radial(mx, my, 260, "#ffffff", 0.35, 0.0)
    sk.add(f'<circle cx="{mx}" cy="{my}" r="34" fill="#f4f2ea"/>')
    sk.line(ellipse_pts(mx, my, 34, 34, 24), 1.2, 0.5, closed=True)
    # far side of the floor: other sleepers, low dark shapes; the hills black
    ridge(sk, [(0, 330), (250, 300), (520, 318), (800, 296), (1050, 312), (1280, 300)], 0.18, 380, None, 1.0)
    sk.fill([(0, 360), (W, 350), (W, H), (0, H)], grey(0.3), 1, amp=2)
    for x in (120, 260, 1030):
        sk.blob([ellipse_pts(x, 372, 50, 11, 14)], grey(0.24), 1.0, None, False)
    # the grain heap behind him, moonlit on its top
    heap = [(700, 560), (760, 430), (860, 352), (980, 318), (1120, 330), (1230, 390), (1300, 470), (1300, 580)]
    sk.blob([heap], grey(0.5), 2.0, (-0.6, 0.8), True, 3.4, 0.6, start=0.25, end=0.75)
    d = []
    for _ in range(260):
        x = rng.uniform(760, 1270); y = rng.uniform(340, 560)
        d.append(f"M{x:.1f},{y:.1f}l{rng.uniform(-2, 2):.1f},{rng.uniform(3, 6):.1f}")
    sk.add(f'<path d="{"".join(d)}" fill="none" stroke="{INK}" stroke-width="0.8" stroke-opacity="0.35"/>')
    sk.fill([(0, 650), (W, 640), (W, H), (0, H)], grey(0.22), 0.8, amp=2)
    L = (-0.6, 0.8)
    kw = dict(light=L, hatch_op=0.62)
    # Boaz, lying at the end of the heap, starting up on his elbow, one arm up; his feet uncovered, toward her
    Figure(sk, pose_recline_start(), 905, 660, 60, -1, tone=0.62, head="headcloth", beard=0.4, face_turn=0.6, expr="startle",
           arms={"n": {"e": (-0.35, 3.15), "w": (0.45, 4.15), "hand": "open"}, "f": {"sh": (-2.1, 2.85), "e": (-2.6, 1.3), "w": (-1.9, 0.35), "hand": "mitt"}},
           props=[("before_head", lambda sk_, f: cloak_on_legs(sk_, f))], **kw).draw()
    # Ruth at his feet, back on her heels, looking at him, her cloak about her
    Figure(sk, pose_sit_heels(), 370, 668, 60, 1, tone=0.48, head="veil", veil_tone=0.36, face_turn=0.6, expr="speak",
           arms={"n": {"e": (0.95, 2.7), "w": (1.2, 3.6), "hand": "mitt"}, "f": {"e": (0.4, 2.6), "w": (0.9, 3.4)}}, **kw).draw()
    # an arm's length
    sk.line([(470, 470), (580, 470)], 1.4, 0.8, color="#e6c9bb", passes=1)
    for x, sgn in ((470, -1), (580, 1)):
        sk.line([(x - sgn * 10, 462), (x, 470), (x - sgn * 10, 478)], 1.4, 0.8, color="#e6c9bb", passes=1, overshoot=0)
    note(sk, 525, 455, "an arm's length, and it stays", 15, "#e6c9bb", "middle")
    note(sk, 990, 200, "Boaz: \u201cWho are you?\u201d", 18, "#e6c9bb", "middle")
    note(sk, 300, 200, "Ruth: \u201cSpread your wing over your servant.\u201d", 18, "#e6c9bb", "middle")
    note(sk, 1170, 170, "moon only", 15, "#e6c9bb", "middle")


def cloak_on_legs(sk, f):
    pts = [f.P(p) for p in ((-0.4, 1.3), (1.0, 1.25), (2.4, 1.05), (3.1, 0.75), (3.3, 0.1), (0.8, 0.0), (-0.9, 0.2))]
    sk.blob([pts], grey(0.42), f.lw, f.light, True, 3.4, 0.6)
    sk.line([f.P((0.4, 1.2)), f.P((1.4, 0.3))], f.lw * 0.6, 0.5, passes=1)
    sk.line([f.P((1.6, 1.15)), f.P((2.5, 0.2))], f.lw * 0.6, 0.5, passes=1)


@panel("3.8", "\u201cEmpty.\u201d Medium, dawn, in the ruin: the six measures of barley on the floor between them; Naomi sits as Ruth speaks. \u201cWait, my daughter.\u201d")
def p3_8(sk, rng):
    yf = 570
    interior_wall(sk, rng, yf, 0.6, light_from_left=False)
    # the broken top of the wall and the open roof: sky through the gap
    gap = [(0, 0), (W, 0), (W, 60), (1000, 90), (860, 140), (700, 120), (560, 170), (420, 130), (300, 150), (160, 100), (0, 110)]
    sk.fill(gap, grey(0.86), 1, amp=3)
    sk.line(gap[2:], 1.8, 0.85, amp=2)
    sk.shape([(120, 70), (900, 210), (905, 236), (115, 96)], grey(0.38), 2.0)  # a fallen beam
    # the floor, rubble, thistles
    sk.fill([(0, yf), (W, yf), (W, H), (0, H)], grey(0.55), 1, smooth=False)
    scribble_ground(sk, rng, 0, yf, W, H, 60, 0.25)
    stones(sk, rng, 26, 0, yf + 10, 260, H - 10, (6, 16), 0.58, (-1, 0.3))
    stones(sk, rng, 14, 1050, yf + 10, W, H - 10, (6, 16), 0.58, (-1, 0.3))
    for x in (60, 140, 1220):
        for k in range(4):
            a = math.radians(-90 + (k - 1.5) * 18)
            sk.line([(x, yf + 40), (x + math.cos(a) * 46, yf + 40 + math.sin(a) * 46)], 1.1, 0.75, passes=1)
            sk.add(f'<circle cx="{x + math.cos(a) * 46:.0f}" cy="{yf + 40 + math.sin(a) * 46:.0f}" r="4" fill="{grey(0.3)}"/>')
    # the door on the right, first light coming in
    dx0, dx1, dy0 = 1010, 1170, 170
    sk.fill([(dx0, dy0), (dx1, dy0), (dx1, yf), (dx0, yf)], "#faf8f2", 1, smooth=False, amp=0.5)
    sk.line([(dx0, dy0), (dx0, yf)], 2.4, 0.9)
    sk.line([(dx1, dy0), (dx1, yf)], 2.4, 0.9)
    sk.shape([(dx0 - 20, dy0 - 24), (dx1 + 20, dy0 - 26), (dx1 + 22, dy0), (dx0 - 18, dy0 + 2)], grey(0.4), 2.0)
    sk.fill([(dx0, yf), (dx1, yf), (520, H), (200, H)], "#fbfaf5", 0.45, smooth=False, amp=1)
    sk.fill([(dx0, dy0), (dx1, dy0 + 60), (420, 560), (300, 520)], "#ffffff", 0.18, smooth=False, amp=1)
    L = (-1, 0.3)
    kw = dict(light=L, hatch_op=0.55)
    # the shawl spread on the floor with the barley heaped on it
    sk.blob([[(470, 660), (560, 628), (700, 632), (770, 668), (690, 700), (520, 700)]], grey(0.7), 1.6, L, True, 3.2, 0.4)
    sk.blob([[(530, 662), (570, 630), (620, 612), (670, 630), (712, 664)]], grey(0.82), 1.6, L, True, 3.0, 0.45)
    d = []
    for _ in range(120):
        x = rng.uniform(540, 700); y = rng.uniform(625, 662)
        d.append(f"M{x:.1f},{y:.1f}l{rng.uniform(1, 3):.1f},{rng.uniform(-1, 1):.1f}")
    sk.add(f'<path d="{"".join(d)}" fill="none" stroke="{INK}" stroke-width="1" stroke-opacity="0.5"/>')
    # Naomi sits (on a fallen stone), looking up at Ruth
    sk.blob([[(150, 700), (165, 598), (230, 586), (330, 590), (345, 700)]], grey(0.62), 1.8, L, True, 3.2, 0.5, soft=0)
    Figure(sk, pose_sit_stone(2.0), 270, 700, 54, 1, tone=0.4, head="veil", veil_tone=0.3, face_turn=0.65, expr="neutral", head_tilt=-14,
           arms={"n": {"e": (1.0, 4.9), "w": (1.75, 4.1), "hand": "mitt"}, "f": {"e": (0.5, 4.9), "w": (1.3, 4.2)}}, **kw).draw()
    # Ruth, standing, speaking, a hand toward the grain
    Figure(sk, pose_stand(women=True), 870, 720, 58, -1, tone=0.76, head="veil", veil_tone=0.64, face_turn=0.55, expr="speak",
           arms={"n": {"e": (0.95, 4.75), "w": (1.9, 4.2), "hand": "open"}, "f": (-6, -2)}, **kw).draw()
    note(sk, 830, 110, "Ruth: \u201cHe said, Don't go back to your mother-in-law empty.\u201d", 17, anchor="middle")
    note(sk, 250, 300, "Naomi: \u201cWait, my daughter.\u201d", 18, anchor="start")
    note(sk, 1090, 600, "first light", 15, anchor="middle")
    note(sk, 615, 600, "six measures of barley", 14, anchor="middle")


def obj_sandal_out(sk, Wr, ang, u, fig):
    obj_sandal(sk, Wr, ang, u, fig)


@panel("4.1", "The gate. Wide, morning: the two piers framing it; ten elders on the bench; Boaz and Mr. So-and-so face to face, the son beside his father. The sandal passes left.")
def p4_1(sk, rng):
    # the gate chamber: back wall with the bench, the street seen through the passage
    yb = 470
    masonry(sk, rng, 150, 90, 1130, yb, 18, 0.74, 0.35)
    sk.rect_grad(150, 90, 1130, yb, [(0, INK, 0.0), (1, INK, 0.25)], vertical=False)
    sk.fill([(560, 150), (720, 150), (720, yb - 10), (560, yb - 10)], "#f8f6f0", 1, smooth=False, amp=0.4)  # the inner gateway, bright street beyond
    sk.line([(560, 150), (560, yb - 10)], 2.0, 0.85)
    sk.line([(720, 150), (720, yb - 10)], 2.0, 0.85)
    sk.shape([(548, 126), (732, 124), (734, 152), (546, 154)], grey(0.5), 1.8)
    sk.line([(560, 400), (720, 396)], 1.0, 0.5, passes=1)
    houses(sk, rng, 566, 400, 4, 1.9, 0.88)
    # the stone bench along both walls
    for x0, x1 in ((160, 545), (735, 1120)):
        sk.blob([[(x0, yb - 52), (x1, yb - 52), (x1, yb - 20), (x0, yb - 20)]], grey(0.6), 1.6, (1, 0.4), True, 3, 0.4, soft=0)
    # the ground of the gate
    sk.fill([(0, yb), (W, yb), (W, H), (0, H)], grey(0.76), 1, smooth=False)
    scribble_ground(sk, rng, 0, yb, W, H, 70, 0.22)
    L = (1, 0.4)
    # ten elders on the bench
    xs = [215, 290, 365, 440, 510, 770, 845, 920, 995, 1070]
    for i, x in enumerate(xs):
        d = 1 if x < 640 else -1
        Figure(sk, pose_sit_bench(), x, yb, 26, d, tone=rng.choice([0.7, 0.78, 0.84]), head="headcloth", beard=rng.choice([0.6, 0.7, 0.8]),
               face_turn=0.5, light=L, hatch_op=0.35, expr="neutral",
               arms={"n": {"e": (0.6, 4.7), "w": (1.2, 3.9)}, "f": {"e": (-0.6, 4.7), "w": (0.3, 3.85)}}).draw()
    tag(sk, 215, 270, "the old elder", 175, 225)
    # the piers framing the gate, near and dark
    for x0, x1 in ((0, 150), (1130, W)):
        masonry(sk, rng, x0, 0, x1, H, 24, 0.5, 0.5)
        sk.hatch_region([[(x0, 0), (x1, 0), (x1, H), (x0, H)]], 3.5, None, 0.8, 0.45, smooth=False)
    sk.fill([(150, 0), (1130, 0), (1130, 60), (150, 70)], grey(0.45), 1, smooth=False)
    masonry(sk, rng, 150, 0, 1130, 66, 22, 0.48, 0.4, wash=False)
    # Boaz (left) and Mr. So-and-so (right) face to face; the sandal passes left, to Boaz; the son at his father's elbow
    sk.fill(ellipse_pts(500, 700, 60, 9, 14), INK, 0.3)
    sk.fill(ellipse_pts(790, 700, 60, 9, 14), INK, 0.3)
    Figure(sk, pose_stand(), 470, 700, 52, 1, tone=0.84, head="headcloth", beard=0.5, face_turn=0.6, light=L, expr="neutral",
           arms={"n": {"e": (1.0, 5.0), "w": (2.0, 5.1), "hand": "open"}, "f": (-6, -2)}, props=[("before_head", lambda sk_, f: mantle_over(sk_, f, 0.55))]).draw()
    Figure(sk, pose_stand(), 975, 700, 40, -1, tone=0.8, head="hair", hair_tone=0.3, face_turn=0.3, light=L, expr="neutral", head_tilt=-10,
           arms={"n": (10, 20)}).draw()
    Figure(sk, pose_stand(), 810, 700, 52, -1, tone=0.7, head="headcloth", beard=0.42, face_turn=0.6, light=L, expr="neutral",
           arms={"n": {"e": (1.05, 5.1), "w": (2.05, 5.25), "hand": "mitt", "obj": obj_sandal}, "f": (-6, -2)}).draw()
    arrow(sk, [(800, 380), (700, 372), (600, 380)], label=None)
    note(sk, 700, 360, "the sandal passes left", 15, anchor="middle")
    tag(sk, 470, 300, "Boaz", 420, 240)
    tag(sk, 805, 300, "Mr. So-and-so", 860, 240)
    tag(sk, 975, 395, "his son", 1040, 380)
    note(sk, 640, 40, "Boaz: \u201cYou are witnesses today.\u201d", 18, "#f0dcd2", "middle")


def baby(sk, x, y, s, angle=0.0, d=1, eyes="closed", tone=0.86):
    """A swaddled infant: wrapped bundle and a small round head with a face."""
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    P = lambda px, py: (x + (ca * px * d - sa * py) * s, y + (sa * px * d + ca * py) * s)
    wrap = [P(-1.6, -0.35), P(-0.6, -0.55), P(0.5, -0.55), P(0.95, -0.2), P(0.95, 0.25), P(0.4, 0.55), P(-0.8, 0.5), P(-1.7, 0.2)]
    sk.blob([wrap], grey(tone), min(3.2, max(1.0, s * 0.06)), (1, 0.2), True, 3, 0.4)
    for k in (-0.9, -0.3, 0.3):
        sk.line([P(k, -0.5), P(k + 0.35, 0.5)], 0.8, 0.45, passes=1)
    hc = P(1.25, -0.05)
    head = ellipse_pts(hc[0], hc[1], 0.5 * s, 0.47 * s, 18)
    sk.blob([head], grey(0.9), min(3.2, max(1.0, s * 0.06)), (1, 0.2), True, 3, 0.35, construct=False)
    f = lambda px, py: (hc[0] + (ca * px * d - sa * py) * s, hc[1] + (sa * px * d + ca * py) * s)
    if eyes == "closed":
        for ex in (-0.15, 0.17):
            sk.line([f(ex - 0.09, 0.0), f(ex, 0.05), f(ex + 0.09, 0.0)], min(3.0, max(0.8, s * 0.04)), 0.85, passes=1, overshoot=0, amp=0.1)
    else:
        for ex in (-0.15, 0.17):
            c = f(ex, 0.02)
            sk.add(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{max(1.0, 0.055 * s):.1f}" fill="{INK}"/>')
    sk.line([f(0.0, 0.12), f(0.03, 0.17)], min(2.5, max(0.7, s * 0.03)), 0.6, passes=1, overshoot=0, amp=0.1)
    sk.line([f(-0.06, 0.27), f(0.0, 0.29), f(0.06, 0.27)], min(2.8, max(0.7, s * 0.035)), 0.75, passes=1, overshoot=0, amp=0.1)
    # the wrap's hood edge round the face
    sk.line([f(-0.45, -0.3), f(-0.1, -0.5), f(0.3, -0.48), f(0.5, -0.2)], min(3.2, max(1.0, s * 0.06)), 0.7, passes=1)


@panel("4.6", "The naming. Medium close, lamplight: the women around Naomi; the child on her lap; she looks up and sees Ruth standing behind. \u201cA son has been born to Naomi!\u201d She laughs.")
def p4_6(sk, rng):
    yf = 600
    interior_wall(sk, rng, yf, 0.55)
    sk.fill([(0, yf), (W, yf), (W, H), (0, H)], grey(0.45), 1, smooth=False)
    sk.rect_grad(0, 0, W, H, [(0, INK, 0.0), (1, INK, 0.25)], vertical=False)
    sk.radial(40, 600, 760, "#fffaf0", 0.6, 0.0, [(0.25, 0.4)])
    group(sk, "translate(640,720) scale(1.4) translate(-640,-790)")
    L = (1, -0.1)
    kw = dict(light=L, hatch_op=0.55)
    # Ruth, standing behind, right, smiling down at them
    Figure(sk, pose_stand(women=True), 930, 860, 66, -1, tone=0.74, head="veil", veil_tone=0.64, face_turn=0.5, expr="smile", head_tilt=12,
           arms={"n": {"e": (0.75, 4.95), "w": (0.15, 5.6), "hand": "mitt"}, "f": {"e": (-0.6, 4.9), "w": (0.0, 5.5)}}, **kw).draw()
    # women behind, left and right, crowding in
    Figure(sk, pose_stand(women=True), 300, 860, 64, 1, tone=0.6, head="veil", veil_tone=0.48, face_turn=0.5, expr="laugh",
           arms={"n": {"e": (1.0, 5.1), "w": (1.55, 6.2), "hand": "open"}, "f": {"e": (0.05, 5.0), "w": (1.3, 6.35), "hand": "open"}}, **kw).draw()
    # Naomi, centre, seated, the child in her lap, looking up at Ruth and laughing
    nf = Figure(sk, pose_sit_cross(), 650, 735, 64, 1, tone=0.48, head="veil", veil_tone=0.36, face_turn=0.6, expr="laugh", head_tilt=-26,
                arms={"n": {"e": (1.2, 3.0), "w": (0.05, 2.05), "hand": "mitt"}, "f": {"e": (-1.15, 3.0), "w": (-1.05, 2.2), "hand": "mitt"}},
                props=[("before_head", lambda sk_, f: baby(sk_, *f.P((-0.05, 2.15)), 46, -6, -1, "closed"))], **kw)
    nf.draw()
    # the old friend, kneeling in close, left, naming him
    Figure(sk, pose_kneel_up(), 385, 760, 62, 1, tone=0.68, head="veil", veil_tone=0.56, face_turn=0.6, expr="speak",
           arms={"n": {"e": (1.25, 3.7), "w": (2.3, 4.1), "hand": "open"}, "f": {"e": (0.5, 3.6), "w": (1.2, 3.0)}}, **kw).draw()
    end(sk)
    # the lamp, on a stand in the near left corner
    lx, ly = 60, 640
    sk.blob([[(lx - 40, ly), (lx + 40, ly), (lx + 30, H), (lx - 30, H)]], grey(0.35), 2.0, None, False, soft=0)
    sk.shape([(lx - 34, ly + 4), (lx + 40, ly + 4), (lx + 30, ly - 12), (lx - 26, ly - 12)], grey(0.55), 1.6)
    sk.radial(lx + 30, ly - 40, 120, "#ffffff", 0.9, 0.0)
    sk.fill([(lx + 24, ly - 12), (lx + 30, ly - 52), (lx + 37, ly - 12)], "#ffffff", 1, amp=0.6)
    sk.line([(lx + 24, ly - 12), (lx + 30, ly - 52), (lx + 37, ly - 12)], 1.0, 0.6, passes=1)
    note(sk, lx + 50, ly - 40, "lamp", 15)
    note(sk, 640, 62, "\u201cA son has been born to Naomi!\u201d  ...  \u201cObed.\u201d", 20, anchor="middle")
    tag(sk, 1050, 250, "Ruth", 1120, 120)
    tag(sk, 620, 270, "Naomi, laughing", 470, 130)


@panel("4.7", "The roof. Wide, then extreme close: Naomi on the roof with Obed; Moab across the rift turning blue; the lullaby. The camera comes in until the last shot is Obed's face.")
def p4_7(sk, rng):
    hz = 330
    sk.rect_grad(0, 0, W, hz + 60, [(0, grey(0.42)), (0.55, grey(0.7)), (1, grey(0.9))])
    cloud_scribble(sk, rng, 0, 40, W, 200, 12, 0.22)
    sk.add(f'<circle cx="300" cy="90" r="2" fill="#ffffff" fill-opacity="0.9"/>')
    # Moab across the rift, layered, turning blue
    BLUE1, BLUE2 = "#8d97ab", "#6f7a90"
    m1 = [(0, hz + 4), (160, hz - 14), (380, hz - 6), (520, hz - 18), (700, hz - 30), (880, hz - 26), (1060, hz - 38), (1280, hz - 30)]
    sk.fill(m1 + [(1280, hz + 60), (0, hz + 60)], BLUE1, 0.9, amp=1.5)
    sk.line(m1, 1.3, 0.6)
    m2 = [(0, hz + 26), (300, hz + 20), (500, hz + 14), (700, hz + 12), (900, hz + 22), (1280, hz + 8)]
    sk.fill(m2 + [(1280, hz + 70), (0, hz + 70)], BLUE2, 0.9, amp=1.5)
    sk.line(m2, 1.2, 0.55)
    sk.rect_grad(0, hz + 50, W, H, [(0, grey(0.74)), (0.2, grey(0.64)), (1, grey(0.48))])
    ridge(sk, [(0, hz + 110), (300, hz + 96), (640, hz + 106), (900, hz + 92), (1280, hz + 100)], 0.62, H, (1, 0.3), 1.2, 4, 0.25)
    for k in range(60):
        sk.add(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, 140):.0f}" r="{rng.uniform(0.5, 1.2):.1f}" fill="#ffffff" fill-opacity="{rng.uniform(0.2, 0.6):.2f}"/>')
    # the hill falling away below the house: Boaz's terraces with the barley coming up
    terraces(sk, rng, 300, 1280, hz + 100, 600, 6, 0.55, stubble=True, curve=10)
    barley(sk, rng, 600, 1280, hz + 160, 600, 300, 4, 12, 0.4)
    # the roof: beaten-earth surface, a low stone parapet along its far edge and down its right side, a roller stone, a jar
    roof = [(0, 540), (760, 512), (990, H), (0, H)]
    sk.fill(roof, grey(0.6), 1, amp=1.5)
    sk.rect_grad(0, 500, 1000, H, [(0, INK, 0.0), (1, INK, 0.18)])
    scribble_ground(sk, rng, 0, 545, 900, H, 50, 0.25)
    par_back = [(0, 505), (770, 478), (770, 512), (0, 541)]
    sk.blob([par_back], grey(0.68), 1.8, (1, 0.3), True, 3, 0.4, soft=0)
    for k in range(1, 16):
        x = 770 * k / 16
        y0 = 505 - 27 * k / 16
        sk.line([(x, y0), (x + rng.uniform(-2, 2), y0 + 34)], 0.8, 0.5, passes=1)
    sk.line([(0, 523), (770, 495)], 0.8, 0.45, passes=1)
    par_side = [(770, 478), (800, 478), (1030, H), (985, H)]
    sk.blob([par_side], grey(0.55), 1.8, (1, 0.3), True, 3, 0.5, soft=0)
    for k in range(1, 9):
        t = k / 9
        sk.line([(lerp(770, 985, t), lerp(478, H, t)), (lerp(800, 1030, t), lerp(478, H, t))], 0.8, 0.5, passes=1)
    sk.blob([ellipse_pts(110, 640, 42, 22, 16), [(68, 640), (152, 640), (152, 676), (68, 676)], ellipse_pts(110, 676, 42, 22, 16)], grey(0.62), 1.4, (1, 0.3), True, 3, 0.4)
    jar(sk, rng, 700, 600, 56, 80, 0.7, (1, 0.3), 0.45, 1.6)
    # the top of the ladder coming up through the roof hatch
    sk.fill([(150, 560), (250, 556), (262, 590), (140, 594)], grey(0.2), 1, amp=0.5)
    for x0 in (170, 228):
        sk.line([(x0, 592), (x0 + 6, 520)], 3.0, 0.85, passes=2)
    for y in (575, 552, 530):
        sk.line([(172, y), (232, y - 1)], 2.0, 0.8, passes=1)
    L = (1, 0.3)
    nf = Figure(sk, pose_sit_cross(), 410, 650, 56, 1, tone=0.42, head="veil", veil_tone=0.32, face_turn=0.7, expr="speak", head_tilt=8,
                arms={"n": {"e": (1.0, 3.2), "w": (0.4, 2.35), "hand": "mitt"}, "f": {"e": (-0.9, 3.2), "w": (-0.6, 2.2), "hand": "mitt"}}, light=L)
    nf.draw()
    bx, by = nf.P((0.0, 2.45))
    baby(sk, bx, by, 30, -14, 1, "open")

    # the push in
    for k, (x0, y0, x1, y1) in enumerate(((250, 320, 560, 494), (360, 455, 480, 523))):
        sk.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 1.6, 0.85, color=RED, closed=True, passes=1)
    arrow(sk, [(200, 250), (250, 320)], label=None)
    arrow(sk, [(560, 494), (480, 523)], label=None, head=10)
    note(sk, 195, 240, "push in, all the way to Obed", 15, RED, "start")
    note(sk, 1000, 260, "Moab, turning blue", 16)
    note(sk, 560, 640, "the lullaby, with the words", 16)
    # inset: the last shot, Obed's face
    sub = sub_sketch(sk, 47)
    sub.rect_grad(0, 0, W, H, [(0, grey(0.72)), (1, grey(0.6))])
    sub.fill(ellipse_pts(640, 560, 700, 300, 30), grey(0.38), 1)
    sub.hatch_region([ellipse_pts(640, 560, 700, 300, 30)], 6, None, 1.2, 0.4)
    baby(sub, 470, 400, 300, -12, 1, "open")
    embed(sk, sub, 900, 470, 340, 192, 470, 120, 760, 428, "ECU: Obed's face (the last shot)")


# ----------------------------------------------------------------------------------------------- driver

def find_chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    cands = sorted(glob.glob("/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell")) + \
        sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")) + \
        sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell")))
    for c in cands + ["chromium", "chromium-browser", "google-chrome"]:
        if os.path.exists(c) or subprocess.run(["which", c], capture_output=True).returncode == 0:
            return c
    raise SystemExit("No Chromium found: set CHROME=/path/to/chrome")


def slug(num):
    return num.replace(".", "-").lower()


def render(num, caption, fn, chrome):
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(num))
    sk = Sketch(seed)
    rng = random.Random(seed + 1)
    fn(sk, rng)
    label_corner(sk, num)
    svg = sk.svg(frame=True).replace("<defs>", f"<title>Ruth storyboard {num}</title><desc>{caption}</desc><defs>", 1)
    import xml.etree.ElementTree as ET
    ET.fromstring(svg)  # fail loudly on malformed SVG rather than rasterizing Chromium's error page
    os.makedirs(SVG_DIR, exist_ok=True)
    sp = os.path.join(SVG_DIR, f"{slug(num)}.svg")
    with open(sp, "w") as f:
        f.write(svg)
    raw = os.path.join(SVG_DIR, f".{slug(num)}.raw.png")
    subprocess.run([chrome, "--no-sandbox", "--hide-scrollbars", f"--window-size={W},{H}", f"--screenshot={raw}", "file://" + sp],
                   check=True, capture_output=True)
    im = Image.open(raw).convert("RGB")
    os.remove(raw)
    q = im.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = os.path.join(HERE, f"{slug(num)}.png")
    q.save(out, optimize=True)
    print("wrote", os.path.relpath(out, HERE), os.path.getsize(out) // 1024, "KB")


def font(size, bold=False):
    for p in (f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def sheets():
    pw, ph = 620, 349
    pad, cap_h = 18, 34
    for s in range(2):
        chunk = PANELS[s * 8:(s + 1) * 8]
        cols, rows = 2, 4
        sh = Image.new("RGB", (cols * (pw + pad) + pad, rows * (ph + cap_h) + pad + 44), (250, 248, 243))
        d = ImageDraw.Draw(sh)
        d.text((pad, 14), f"Ruth: storyboard sketches, sheet {s + 1} of 2  ({'prologue to the road' if s == 0 else 'the return to the roof'})",
               fill=(30, 30, 30), font=font(17, True))
        for i, (num, caption, _) in enumerate(chunk):
            p = os.path.join(HERE, f"{slug(num)}.png")
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGB").resize((pw, ph), Image.LANCZOS)
            x = pad + (i % cols) * (pw + pad)
            y = pad + 44 + (i // cols) * (ph + cap_h)
            sh.paste(im, (x, y))
            cap = SHORT.get(num, caption)
            fs = 14
            while fs > 10 and d.textlength(cap, font=font(fs)) > pw - 46:
                fs -= 1
            d.text((x, y + ph + 6), num, fill=(20, 20, 20), font=font(14, True))
            d.text((x + 46, y + ph + 7), cap, fill=(40, 40, 40), font=font(fs))
        out = os.path.join(HERE, f"sheet-{s + 1}.png")
        sh.quantize(colors=160, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(out, optimize=True)
        print("wrote", os.path.basename(out), os.path.getsize(out) // 1024, "KB")


def main(argv):
    chrome = find_chrome()
    want = set(argv)
    for num, caption, fn in PANELS:
        if want and num not in want:
            continue
        render(num, caption, fn, chrome)
    sheets()


if __name__ == "__main__":
    main(sys.argv[1:])
