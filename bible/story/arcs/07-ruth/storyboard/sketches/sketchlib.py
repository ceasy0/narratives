"""A small pencil-sketch kit for the Ruth storyboard: rough strokes, washes, hatching and robed figures, emitted as SVG.

Everything is drawn as jittered vector strokes so the panels read as hand-drawn pencil and wash, not as clip art.
Figures are built from hand-authored pose outlines (in head-units, facing right) plus arms set by angle, so a
pose can be re-aimed or mirrored per panel. See make.py for the panels themselves.
"""
from __future__ import annotations

import math
import random

W, H = 1280, 720
PAPER = "#f2efe7"
INK = "#2a2826"


# ----------------------------------------------------------------------------------------------- geometry helpers

def lerp(a, b, t):
    return a + (b - a) * t


def lerp2(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def dist(p, q):
    return math.hypot(q[0] - p[0], q[1] - p[1])


def grey(v, a=None):
    """v: 0 (black) .. 1 (paper). Mixes toward the warm paper tone so washes look like graphite on paper."""
    pr, pg, pb = 242, 239, 231
    r = int(lerp(38, pr, v)); g = int(lerp(36, pg, v)); b = int(lerp(35, pb, v))
    return f"#{r:02x}{g:02x}{b:02x}"


def resample(pts, step, closed=False):
    if closed:
        pts = list(pts) + [pts[0]]
    out = [pts[0]]
    carry = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = dist(a, b)
        if L == 0:
            continue
        d = step - carry
        while d <= L:
            out.append(lerp2(a, b, d / L))
            d += step
        carry = L - (d - step)
    if not closed and dist(out[-1], pts[-1]) > 0.5:
        out.append(pts[-1])
    if closed and len(out) > 2 and dist(out[-1], out[0]) < step * 0.5:
        out.pop()
    return out


def smooth_d(pts, closed=False):
    """Catmull-Rom through the points, as a cubic-bezier path string."""
    n = len(pts)
    if n < 2:
        return ""
    if n == 2:
        return f"M{pts[0][0]:.0f},{pts[0][1]:.0f}L{pts[1][0]:.0f},{pts[1][1]:.0f}"
    s = f"M{pts[0][0]:.0f},{pts[0][1]:.0f}"
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if closed or i > 0 else pts[i]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed or i + 2 < n else pts[(i + 1) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        s += f"C{c1[0]:.0f},{c1[1]:.0f} {c2[0]:.0f},{c2[1]:.0f} {p2[0]:.0f},{p2[1]:.0f}"
    if closed:
        s += "Z"
    return s


def chaikin(pts, it=1, closed=True):
    for _ in range(it):
        out = []
        n = len(pts)
        rng_ = range(n) if closed else range(n - 1)
        if not closed:
            out.append(pts[0])
        for i in rng_:
            p, q = pts[i], pts[(i + 1) % n]
            out.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            out.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts


def poly_d(pts, closed=True):
    s = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    return s + ("Z" if closed else "")


def ellipse_pts(cx, cy, rx, ry, n=28, rot=0.0, a0=0.0, a1=2 * math.pi):
    out = []
    cr, sr = math.cos(rot), math.sin(rot)
    for i in range(n):
        t = a0 + (a1 - a0) * i / (n if a1 - a0 >= 2 * math.pi - 1e-6 else n - 1)
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
    return out


def capsule(p, q, w1, w2=None, n=7):
    """Tapered capsule from p to q, widths w1 at p and w2 at q, as a polygon."""
    w2 = w1 if w2 is None else w2
    ang = math.atan2(q[1] - p[1], q[0] - p[0])
    nx, ny = -math.sin(ang), math.cos(ang)
    pts = []
    for i in range(n + 1):  # cap at q
        t = -math.pi / 2 + math.pi * i / n
        pts.append((q[0] + (w2 / 2) * (math.cos(t) * math.cos(ang) - math.sin(t) * math.sin(ang)) * 1,
                    q[1] + (w2 / 2) * (math.cos(t) * math.sin(ang) + math.sin(t) * math.cos(ang))))
    for i in range(n + 1):  # cap at p
        t = math.pi / 2 + math.pi * i / n
        pts.append((p[0] + (w1 / 2) * (math.cos(t) * math.cos(ang) - math.sin(t) * math.sin(ang)),
                    p[1] + (w1 / 2) * (math.cos(t) * math.sin(ang) + math.sin(t) * math.cos(ang))))
    return pts


def bbox(polys):
    xs = [x for P in polys for x, _ in P]
    ys = [y for P in polys for _, y in P]
    return min(xs), min(ys), max(xs), max(ys)


# ----------------------------------------------------------------------------------------------- the canvas

class Sketch:
    def __init__(self, seed=1, paper=PAPER, hatch_angle=58):
        self.rng = random.Random(seed)
        self.defs = []
        self.body = []
        self.uid = 0
        self.hatch_angle = hatch_angle
        self.paper = paper

    # ---- low level
    def new_id(self, prefix="i"):
        self.uid += 1
        return f"{prefix}{self.uid}"

    def add(self, s):
        self.body.append(s)

    def noise(self, n, knots=6, amp=1.0):
        k = [self.rng.uniform(-1, 1) for _ in range(knots + 2)]
        out = []
        for i in range(n):
            t = i / max(n - 1, 1) * knots
            j = int(t)
            f = t - j
            f = (1 - math.cos(f * math.pi)) / 2
            out.append((k[j] * (1 - f) + k[j + 1] * f) * amp)
        return out

    def rough(self, pts, amp=1.2, step=9, closed=False, knots=None):
        if len(pts) < 2:
            return pts
        r = resample(pts, step, closed)
        n = len(r)
        if n < 3:
            return r
        nz = self.noise(n, knots or max(3, n // 5), amp)
        out = []
        for i in range(n):
            a = r[i - 1] if (closed or i > 0) else r[i]
            b = r[(i + 1) % n] if (closed or i < n - 1) else r[i]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            out.append((r[i][0] - dy / L * nz[i], r[i][1] + dx / L * nz[i]))
        return out

    # ---- strokes
    def line(self, pts, w=1.6, op=0.85, color=INK, amp=0.9, passes=2, closed=False, overshoot=2.5, cap="round"):
        pts = list(pts)
        if len(pts) < 2:
            return
        for k in range(passes):
            q = list(pts)
            if not closed and overshoot and k == 0:
                # pencil overshoot at the ends
                a, b = q[0], q[1]
                L = dist(a, b) or 1
                q[0] = (a[0] - (b[0] - a[0]) / L * overshoot * self.rng.random(), a[1] - (b[1] - a[1]) / L * overshoot * self.rng.random())
                a, b = q[-1], q[-2]
                L = dist(a, b) or 1
                q[-1] = (a[0] - (b[0] - a[0]) / L * overshoot * self.rng.random(), a[1] - (b[1] - a[1]) / L * overshoot * self.rng.random())
            r = self.rough(q, amp * (1 + 0.6 * k), closed=closed)
            if k:
                r = [(x + self.rng.uniform(-0.6, 0.6), y + self.rng.uniform(-0.6, 0.6)) for x, y in r]
            ww = w if k == 0 else w * 0.55
            oo = op if k == 0 else op * 0.45
            self.add(f'<path d="{smooth_d(r, closed)}" fill="none" stroke="{color}" stroke-width="{ww:.2f}" '
                     f'stroke-opacity="{oo:.2f}" stroke-linecap="{cap}" stroke-linejoin="round"/>')

    def fill(self, pts, color, op=1.0, amp=0.8, smooth=True, extra=""):
        r = self.rough(pts, amp, closed=True) if amp else pts
        d = smooth_d(r, True) if smooth else poly_d(r)
        self.add(f'<path d="{d}" fill="{color}" fill-opacity="{op:.2f}" {extra}/>')

    def shape(self, pts, color, line_w=1.6, op=1.0, line_op=0.85, amp=0.9, smooth=True):
        """Filled shape with a sketchy outline."""
        r = self.rough(pts, amp, closed=True)
        d = smooth_d(r, True) if smooth else poly_d(r)
        self.add(f'<path d="{d}" fill="{color}" fill-opacity="{op:.2f}"/>')
        self.line(r, line_w, line_op, amp=0.5, closed=True)

    def rect_grad(self, x0, y0, x1, y1, stops, vertical=True, op=1.0):
        gid = self.new_id("g")
        x2, y2 = ("0", "1") if vertical else ("1", "0")
        st = "".join(f'<stop offset="{o[0]}" stop-color="{o[1]}" stop-opacity="{o[2] if len(o) > 2 else 1}"/>' for o in stops)
        self.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">{st}</linearGradient>')
        self.add(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#{gid})" opacity="{op}"/>')

    def radial(self, cx, cy, r, color, op_center=0.8, op_edge=0.0, extra_stops=None):
        gid = self.new_id("r")
        st = f'<stop offset="0" stop-color="{color}" stop-opacity="{op_center}"/>'
        for o, a in (extra_stops or []):
            st += f'<stop offset="{o}" stop-color="{color}" stop-opacity="{a}"/>'
        st += f'<stop offset="1" stop-color="{color}" stop-opacity="{op_edge}"/>'
        self.defs.append(f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}" gradientUnits="userSpaceOnUse">{st}</radialGradient>')
        self.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{gid})"/>')

    # ---- hatching
    def hatch_lines(self, x0, y0, x1, y1, spacing=4.0, angle=None, w=0.8, op=0.5, color=INK, gap=0.12, wob=0.6):
        ang = math.radians(self.hatch_angle if angle is None else angle)
        dx, dy = math.cos(ang), -math.sin(ang)
        nx, ny = -dy, dx
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        R = math.hypot(x1 - x0, y1 - y0) / 2 + 4
        out = []
        k = -R
        while k <= R:
            if self.rng.random() > gap:
                a = self.rng.uniform(-R, -R * 0.6)
                b = self.rng.uniform(R * 0.6, R)
                px, py = cx + nx * k, cy + ny * k
                p = (px + dx * a, py + dy * a)
                q = (px + dx * b, py + dy * b)
                m = lerp2(p, q, 0.5)
                m = (m[0] + nx * self.rng.uniform(-wob, wob), m[1] + ny * self.rng.uniform(-wob, wob))
                out.append(f"M{p[0]:.0f},{p[1]:.0f}Q{m[0]:.0f},{m[1]:.0f} {q[0]:.0f},{q[1]:.0f}")
            k += spacing * self.rng.uniform(0.8, 1.2)
        return f'<path d="{"".join(out)}" fill="none" stroke="{color}" stroke-width="{w}" stroke-opacity="{op}" stroke-linecap="round"/>'

    def clip(self, polys, smooth=True):
        cid = self.new_id("c")
        inner = "".join(f'<path d="{smooth_d(P, True) if smooth else poly_d(P)}"/>' for P in polys)
        self.defs.append(f'<clipPath id="{cid}">{inner}</clipPath>')
        return cid

    def grad_mask(self, p_light, p_dark, x0, y0, x1, y1, start=0.35, end=0.8, strength=1.0):
        mid = self.new_id("m")
        gid = self.new_id("g")
        v = int(255 * strength)
        self.defs.append(
            f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{p_light[0]:.1f}" y1="{p_light[1]:.1f}" x2="{p_dark[0]:.1f}" y2="{p_dark[1]:.1f}">'
            f'<stop offset="0" stop-color="#000"/><stop offset="{start}" stop-color="#000"/>'
            f'<stop offset="{end}" stop-color="rgb({v},{v},{v})"/><stop offset="1" stop-color="rgb({v},{v},{v})"/></linearGradient>')
        self.defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
                         f'<rect x="{x0 - 5:.0f}" y="{y0 - 5:.0f}" width="{x1 - x0 + 10:.0f}" height="{y1 - y0 + 10:.0f}" fill="url(#{gid})"/></mask>')
        return mid

    def hatch_region(self, polys, spacing=4.0, angle=None, w=0.8, op=0.5, light=None, start=0.35, end=0.8, cross=False, smooth=True, strength=1.0):
        """Hatch inside polygons; with light=(lx,ly) unit vector (direction the light travels), only the far side."""
        x0, y0, x1, y1 = bbox(polys)
        cid = self.clip(polys, smooth)
        lines = self.hatch_lines(x0, y0, x1, y1, spacing, angle, w, op)
        if cross:
            lines += self.hatch_lines(x0, y0, x1, y1, spacing * 1.3, (self.hatch_angle if angle is None else angle) - 70, w * 0.8, op * 0.7)
        if light is not None:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            R = max(x1 - x0, y1 - y0) / 2
            pl = (cx - light[0] * R, cy - light[1] * R)
            pd = (cx + light[0] * R, cy + light[1] * R)
            mid = self.grad_mask(pl, pd, x0, y0, x1, y1, start, end, strength)
            self.add(f'<g clip-path="url(#{cid})"><g mask="url(#{mid})">{lines}</g></g>')
        else:
            self.add(f'<g clip-path="url(#{cid})">{lines}</g>')

    def wash_region(self, polys, color, op, light, start=0.3, end=0.85, smooth=True):
        """A graded wash on the shadow side of a shape."""
        x0, y0, x1, y1 = bbox(polys)
        cid = self.clip(polys, smooth)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        R = max(x1 - x0, y1 - y0) / 2
        pl = (cx - light[0] * R, cy - light[1] * R)
        pd = (cx + light[0] * R, cy + light[1] * R)
        mid = self.grad_mask(pl, pd, x0, y0, x1, y1, start, end)
        self.add(f'<g clip-path="url(#{cid})"><rect x="{x0 - 2:.0f}" y="{y0 - 2:.0f}" width="{x1 - x0 + 4:.0f}" height="{y1 - y0 + 4:.0f}" '
                 f'fill="{color}" fill-opacity="{op}" mask="url(#{mid})"/></g>')

    # ---- outlined union of shapes (the core of the figures)
    def blob(self, polys, tone, lw=1.7, light=None, hatch=True, hatch_sp=3.6, hatch_op=0.5, construct=True,
             wash=0.0, amp=0.7, line_color=INK, line_op=0.9, start=0.38, end=0.85, soft=1):
        """Several overlapping polygons drawn as one figure: one outline round the union, faint construction lines inside."""
        rp = [self.rough(chaikin(P, soft) if soft else P, amp, step=8, closed=True) for P in polys]
        ds = [smooth_d(P, True) for P in rp]
        # doubled outer line, slightly offset
        ox, oy = self.rng.uniform(-0.9, 0.9), self.rng.uniform(-0.9, 0.9)
        g = "".join(f'<path d="{d}"/>' for d in ds)
        self.add(f'<g transform="translate({ox:.2f},{oy:.2f})" fill="{line_color}" stroke="{line_color}" stroke-width="{lw * 1.2:.2f}" '
                 f'stroke-linejoin="round" opacity="{0.35 * line_op:.2f}">{g}</g>')
        self.add(f'<g fill="{line_color}" stroke="{line_color}" stroke-width="{lw * 2:.2f}" stroke-linejoin="round" opacity="{line_op:.2f}">{g}</g>')
        self.add(f'<g fill="{tone}">{g}</g>')
        if wash and light is not None:
            self.wash_region(rp, INK, wash, light, start, end)
        if hatch and light is not None:
            self.hatch_region(rp, hatch_sp, None, 0.75, hatch_op, light, start, end)
        if construct:
            for P in rp:
                self.line(P, 0.6, 0.16, closed=True, passes=1, amp=1.2)
        return rp

    # ---- output
    def svg(self, frame=True, label=None):
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
                 "<defs>" + "".join(self.defs) + "</defs>",
                 f'<rect width="{W}" height="{H}" fill="{self.paper}"/>']
        parts += self.body
        if label:
            parts.append(f'<text x="22" y="40" font-family="DejaVu Sans, sans-serif" font-size="22" font-weight="bold" fill="{INK}" fill-opacity="0.8">{label}</text>')
        if frame:
            r = random.Random(7)
            for k in range(2):
                pts = [(6 + r.uniform(-1, 1), 6), (W - 6, 6 + r.uniform(-1, 1)), (W - 6 + r.uniform(-1, 1), H - 6), (6, H - 6 + r.uniform(-1, 1))]
                parts.append(f'<path d="{poly_d(pts)}" fill="none" stroke="{INK}" stroke-width="{4 if k == 0 else 1.5}" stroke-opacity="{0.9 if k == 0 else 0.4}"/>')
        parts.append("</svg>")
        return "\n".join(parts)


# ----------------------------------------------------------------------------------------------- figures

def arm_chain(sh, a_up, a_fore, l_up=1.35, l_fore=1.2):
    """Angles in degrees from straight down; positive swings forward (toward +x, the facing side)."""
    e = (sh[0] + l_up * math.sin(math.radians(a_up)), sh[1] - l_up * math.cos(math.radians(a_up)))
    w = (e[0] + l_fore * math.sin(math.radians(a_fore)), e[1] - l_fore * math.cos(math.radians(a_fore)))
    return e, w


class Pose:
    """A pose in head-units (u), facing right, y up, origin on the ground under the figure's centre of weight."""

    def __init__(self, body, head, neck, sh_n, sh_f, folds=(), belt=None, feet=(), tilt=0.0, extra_polys=(), lap=None):
        self.body = body  # list of polygons (u)
        self.head = head
        self.neck = neck
        self.sh_n = sh_n
        self.sh_f = sh_f
        self.folds = folds
        self.belt = belt
        self.feet = feet  # list of (x, y, angle_deg)
        self.tilt = tilt
        self.extra_polys = extra_polys
        self.lap = lap


def pose_stand(stride=0.0, lean=0.0, women=False, hem=0.15, short=False):
    l = lean
    if short:
        hem = 1.75
    sw = 0.62 if women else 0.7
    body = [[(0.0 + l, 6.3), (-sw + l, 6.05), (-0.72 + l * 0.9, 5.5), (-0.6 + l * 0.6, 4.45), (-0.68 + l * 0.4, 3.7),
             (-0.9 - stride * 0.6, 1.2), (-0.95 - stride, hem + 0.05), (-0.3 - stride * 0.3, hem - 0.05), (0.3 + stride * 0.3, hem),
             (0.85 + stride * 0.9, hem + 0.1), (0.78 + stride * 0.5, 1.2), (0.66 + l * 0.4, 3.7),
             (0.55 + l * 0.6, 4.45), ((0.68 if women else 0.66) + l * 0.85, 5.3), (sw + 0.05 + l, 6.0)]]
    folds = [[(0.1 + l * 0.5, 4.2), (0.15 + stride * 0.3, 2.4), (0.25 + stride * 0.5, 0.3)],
             [(-0.25 + l * 0.5, 4.1), (-0.4 - stride * 0.2, 2.0), (-0.55 - stride * 0.6, 0.25)],
             [(0.4 + l * 0.4, 3.6), (0.55 + stride * 0.5, 1.2)]]
    belt = [(-0.62 + l * 0.6, 4.45), (0.0 + l * 0.6, 4.35), (0.56 + l * 0.6, 4.42)]
    feet = [(-0.45 - stride, 0.05, 0), (0.45 + stride, 0.0, 0)]
    extra = ()
    if short:
        body[0] = [(x * 0.92 if y < 2.5 else x, y) for x, y in body[0]]
        extra = (capsule((-0.3 - stride * 0.4, 2.0), (-0.45 - stride, 0.2), 0.42, 0.3), capsule((0.3 + stride * 0.4, 2.0), (0.45 + stride, 0.15), 0.42, 0.3))
        folds = [[(0.1 + l * 0.5, 4.2), (0.2, 2.0)], [(-0.3 + l * 0.5, 4.1), (-0.45, 2.0)]]
    pose = Pose(body, (0.18 + l * 1.05, 7.0), (0.06 + l, 6.35), (0.66 + l, 5.95), (-0.55 + l, 6.0), folds, belt, feet, extra_polys=extra)
    return pose


def pose_front(women=False, hem=0.15, arms_wide=0.0):
    sw = 0.78 if women else 0.88
    body = [[(0, 6.3), (-sw, 6.02), (-0.86, 5.4), (-0.66, 4.45), (-0.74, 3.7), (-0.9, 1.2), (-1.0, hem + 0.05), (0, hem - 0.08),
             (1.0, hem + 0.05), (0.9, 1.2), (0.74, 3.7), (0.66, 4.45), (0.86, 5.4), (sw, 6.02)]]
    folds = [[(-0.2, 4.2), (-0.3, 0.3)], [(0.25, 4.2), (0.35, 0.3)], [(0.0, 3.4), (0.02, 0.4)]]
    belt = [(-0.66, 4.45), (0, 4.38), (0.66, 4.45)]
    feet = [(-0.4, 0.04, -60), (0.4, 0.04, -120)]
    return Pose(body, (0.0, 7.0), (0, 6.35), (sw, 5.95), (-sw, 5.95), folds, belt, feet)


def pose_back():
    body = [[(0, 6.3), (-0.95, 6.0), (-0.95, 5.3), (-0.75, 4.4), (-0.8, 3.6), (-0.95, 1.2), (-1.0, 0.1), (1.0, 0.1), (0.95, 1.2),
             (0.8, 3.6), (0.75, 4.4), (0.95, 5.3), (0.95, 6.0)]]
    folds = [[(-0.3, 5.6), (-0.4, 3.0), (-0.5, 0.3)], [(0.2, 5.5), (0.3, 2.6), (0.4, 0.3)], [(-0.05, 4.6), (0.0, 1.0)]]
    belt = [(-0.75, 4.4), (0, 4.45), (0.75, 4.4)]
    return Pose(body, (0.0, 6.9), (0, 6.35), (0.9, 5.95), (-0.9, 5.95), folds, belt, [])


def pose_kneel_up(women=True):
    """Upright kneeling, side three-quarter, knees on the ground, toes behind."""
    body = [[(0.15, 4.55), (-0.45, 4.35), (-0.55, 3.8), (-0.5, 2.85), (-0.75, 1.9), (-1.05, 1.05), (-1.7, 0.55), (-2.0, 0.05),
             (-0.6, 0.0), (0.4, -0.02), (1.2, 0.05), (1.15, 0.5), (0.65, 1.0), (0.55, 1.9), (0.6, 2.85), (0.62, 3.6), (0.7, 4.3)]]
    folds = [[(0.2, 2.6), (0.6, 1.0), (1.0, 0.15)], [(-0.3, 2.3), (-0.9, 0.9), (-1.6, 0.2)], [(-0.1, 1.6), (0.1, 0.1)]]
    belt = [(-0.5, 2.85), (0.05, 2.75), (0.58, 2.85)]
    return Pose(body, (0.4, 5.25), (0.25, 4.65), (0.6, 4.25), (-0.4, 4.3), folds, belt, [])


def pose_sit_heels():
    """Sitting back on the heels, side three-quarter."""
    body = [[(0.1, 4.0), (-0.45, 3.8), (-0.6, 3.2), (-0.6, 2.4), (-0.85, 1.6), (-1.1, 0.9), (-1.15, 0.05), (0.2, -0.02),
             (1.3, 0.05), (1.35, 0.55), (0.9, 0.95), (0.5, 1.5), (0.55, 2.4), (0.6, 3.2), (0.65, 3.8)]]
    folds = [[(-0.2, 1.9), (0.7, 0.6), (1.2, 0.2)], [(-0.5, 1.6), (-0.9, 0.2)], [(0.1, 1.3), (0.5, 0.1)]]
    belt = [(-0.6, 2.4), (0.0, 2.3), (0.55, 2.4)]
    return Pose(body, (0.4, 4.75), (0.22, 4.1), (0.6, 3.75), (-0.42, 3.8), folds, belt, [])


def pose_sit_cross(women=True):
    """Seated cross-legged on the ground, near front view; the lap is wide."""
    body = [[(0, 4.55), (-0.78, 4.3), (-0.82, 3.7), (-0.7, 2.7), (-0.9, 1.6), (-1.7, 0.85), (-1.85, 0.3), (-1.5, 0.0), (0, -0.05),
             (1.5, 0.0), (1.85, 0.3), (1.7, 0.85), (0.9, 1.6), (0.7, 2.7), (0.82, 3.7), (0.78, 4.3)]]
    folds = [[(-1.5, 0.6), (-0.5, 0.9), (0.4, 0.55)], [(1.4, 0.5), (0.5, 0.3)], [(-0.3, 1.6), (-0.6, 0.1)], [(0.3, 1.6), (0.7, 0.15)]]
    belt = [(-0.7, 2.7), (0, 2.62), (0.7, 2.7)]
    return Pose(body, (0.05, 5.25), (0.02, 4.6), (0.78, 4.25), (-0.78, 4.25), folds, belt, [], lap=(0.0, 1.5))


def pose_sit_side(knees=1.6):
    """Seated on the ground, legs forward, knees drawn up, side three-quarter facing right."""
    body = [[(0.05, 4.45), (-0.5, 4.25), (-0.65, 3.6), (-0.6, 2.6), (-0.85, 1.7), (-1.0, 0.6), (-0.8, 0.0), (0.6, -0.02),
             (1.9, 0.0), (2.05, 0.35), (1.75, knees - 0.2), (1.35, knees + 0.15), (0.7, knees * 0.9), (0.6, 2.2), (0.62, 3.6), (0.7, 4.2)]]
    folds = [[(0.0, 1.9), (1.0, knees), (1.7, 0.3)], [(-0.4, 1.7), (-0.2, 0.2)], [(0.6, 0.9), (1.4, 0.5)]]
    belt = [(-0.6, 2.6), (0.0, 2.5), (0.6, 2.6)]
    feet = [(2.1, 0.05, 0)]
    return Pose(body, (0.42, 5.2), (0.2, 4.55), (0.6, 4.2), (-0.45, 4.25), folds, belt, feet)


def pose_sit_bench():
    """Seated on a bench (seat height ~2u), front three-quarter."""
    body = [[(0, 6.1), (-0.8, 5.85), (-0.82, 5.2), (-0.7, 4.3), (-0.85, 2.3), (-0.95, 1.9), (-0.85, 0.15), (-0.2, 0.1), (0.2, 0.15),
             (0.95, 0.1), (1.0, 1.9), (1.05, 2.4), (0.75, 4.3), (0.82, 5.2), (0.8, 5.85)]]
    folds = [[(-0.6, 2.2), (0.0, 2.0), (0.8, 2.25)], [(-0.4, 1.8), (-0.45, 0.2)], [(0.45, 1.8), (0.5, 0.2)]]
    belt = [(-0.7, 4.25), (0.05, 4.18), (0.75, 4.25)]
    feet = [(-0.45, 0.02, -60), (0.5, 0.02, -110)]
    return Pose(body, (0.12, 6.8), (0.05, 6.15), (0.75, 5.85), (-0.75, 5.85), folds, belt, feet)


def pose_sit_stone(seat=2.0):
    """Seated on a stone or ledge, side three-quarter facing right: thighs forward, shins down."""
    k = seat
    body = [[(0.05, k + 4.3), (-0.5, k + 4.1), (-0.65, k + 3.4), (-0.55, k + 2.3), (-0.8, k + 1.2), (-0.85, k + 0.2), (-0.4, k - 0.15),
             (0.6, k - 0.1), (1.25, k - 0.35), (1.25, 1.0), (1.35, 0.1), (1.9, 0.05), (1.95, 0.4), (1.75, 1.2), (1.8, k + 0.2),
             (1.6, k + 0.65), (0.6, k + 1.0), (0.55, k + 2.3), (0.62, k + 3.4), (0.7, k + 4.05)]]
    folds = [[(-0.3, k + 1.0), (1.0, k + 0.5), (1.6, k + 0.1)], [(1.4, k - 0.2), (1.5, 0.5)], [(-0.2, k + 2.0), (0.3, k + 0.9)]]
    belt = [(-0.55, k + 2.3), (0.0, k + 2.2), (0.55, k + 2.3)]
    feet = [(1.65, 0.0, 0)]
    return Pose(body, (0.4, k + 5.05), (0.2, k + 4.4), (0.6, k + 4.05), (-0.45, k + 4.1), folds, belt, feet)


def pose_dance():
    """Front-ish, hips swung, one heel up, skirt swinging out; the arms are set separately (up)."""
    body = [[(0.05, 6.3), (-0.72, 6.05), (-0.78, 5.4), (-0.55, 4.45), (-0.5, 3.75), (-0.95, 1.4), (-1.35, 0.4), (-1.1, 0.15),
             (-0.2, 0.05), (0.6, 0.15), (1.25, 0.55), (1.2, 1.3), (0.85, 3.7), (0.72, 4.45), (0.85, 5.4), (0.75, 6.05)]]
    folds = [[(-0.2, 4.2), (-0.7, 2.0), (-1.1, 0.4)], [(0.3, 4.1), (0.6, 2.0), (1.0, 0.5)], [(0.05, 3.4), (-0.05, 0.3)]]
    belt = [(-0.55, 4.45), (0.1, 4.38), (0.72, 4.45)]
    feet = [(-0.5, 0.05, -40), (0.55, 0.12, -150)]
    return Pose(body, (0.22, 7.0), (0.12, 6.38), (0.78, 5.98), (-0.7, 5.98), folds, belt, feet, tilt=-12)


def pose_bend_glean():
    """Down on one knee, bent forward over the stubble, reaching to the ground ahead; side view facing right."""
    body = [[(0.95, 3.65), (0.2, 3.35), (-0.5, 2.7), (-0.9, 1.9), (-1.0, 1.0), (-1.45, 0.35), (-1.5, 0.02), (-0.2, 0.0), (1.0, 0.02),
             (1.75, 0.03), (1.75, 0.3), (1.6, 0.9), (1.75, 1.6), (1.5, 1.95), (1.15, 2.05), (1.45, 2.6), (1.6, 3.1), (1.4, 3.45)]]
    folds = [[(0.0, 2.9), (-0.4, 1.5), (-0.9, 0.3)], [(0.6, 2.2), (1.4, 1.7)], [(1.4, 1.5), (1.5, 0.3)]]
    belt = [(-0.75, 2.3), (0.3, 2.25), (1.2, 2.2)]
    return Pose(body, (2.0, 3.7), (1.55, 3.45), (1.35, 3.2), (0.85, 3.45), folds, belt, [], tilt=28)


def pose_reap():
    """Half-kneeling reaper, body forward, sickle hand low; side view facing right."""
    body = [[(1.0, 4.45), (0.3, 4.4), (-0.25, 3.8), (-0.55, 2.6), (-0.9, 1.6), (-1.25, 0.4), (-1.0, 0.0), (0.3, 0.0),
             (1.55, 0.05), (1.65, 0.6), (1.25, 1.2), (1.4, 1.75), (1.0, 2.7), (1.1, 3.6), (1.45, 4.2)]]
    folds = [[(0.2, 2.4), (0.9, 1.4), (1.4, 0.3)], [(-0.3, 2.2), (-0.7, 0.3)]]
    belt = [(-0.5, 2.7), (0.25, 2.55), (1.0, 2.65)]
    return Pose(body, (1.65, 4.85), (1.3, 4.45), (1.3, 4.15), (0.45, 4.35), folds, belt, [], tilt=22)


def pose_crouch_mourn():
    """Crouched, head bowed, front three-quarter; arms set separately (to the head)."""
    body = [[(0.3, 4.1), (-0.45, 3.95), (-0.7, 3.3), (-0.8, 2.3), (-1.25, 1.4), (-1.3, 0.4), (-1.0, 0.0), (0.3, -0.02),
             (1.3, 0.05), (1.45, 0.8), (1.1, 1.75), (0.75, 2.4), (0.75, 3.3), (0.95, 3.9)]]
    folds = [[(-0.6, 1.8), (-0.4, 0.2)], [(0.4, 1.7), (1.0, 0.3)]]
    return Pose(body, (0.55, 4.35), (0.35, 4.0), (0.85, 3.85), (-0.45, 3.9), folds, None, [], tilt=30)


def pose_recline_start():
    """Lying on the ground, starting up: legs along the ground to the right (toward his feet), torso up on the far elbow,
    head turned toward his feet. Facing right means his feet are to the right."""
    body = [[(-1.75, 3.0), (-2.4, 2.6), (-2.75, 1.7), (-2.5, 0.7), (-1.8, 0.2), (-0.5, 0.0), (1.5, 0.0), (3.4, 0.05), (3.9, 0.25),
             (3.8, 0.7), (2.6, 0.95), (1.4, 1.05), (0.0, 1.05), (-0.75, 1.45), (-1.0, 2.3), (-1.15, 2.8)]]
    folds = [[(-0.6, 0.9), (1.2, 0.6), (3.0, 0.4)], [(-1.6, 2.2), (-1.0, 1.3)], [(0.5, 1.0), (2.2, 0.7)]]
    belt = [(-2.4, 1.9), (-1.6, 1.6), (-0.95, 1.9)]
    feet = [(3.95, 0.3, -70)]
    return Pose(body, (-1.25, 3.85), (-1.55, 3.2), (-1.15, 2.95), (-2.1, 2.85), folds, belt, feet, tilt=-18)


class Figure:
    """Places a pose: x, y (px) of the pose origin; u (px per head unit); d = +1 facing right, -1 facing left."""

    def __init__(self, sk: Sketch, pose: Pose, x, y, u, d=1, tone=0.8, head="veil", veil_tone=None, beard=False,
                 face_turn=0.55, expr="neutral", arms=None, light=(1, 0.3), hatch=True, hatch_op=0.5, lw=None,
                 skin=0.86, head_tilt=None, eyes="open", line_op=0.9, props=None, details=1.0, hair_tone=0.35, hood_long=True):
        self.sk, self.p, self.x, self.y, self.u, self.d = sk, pose, x, y, u, d
        self.tone, self.head, self.veil_tone, self.beard = tone, head, veil_tone if veil_tone is not None else tone - 0.12, beard
        self.turn, self.expr = face_turn, expr
        self.arms = arms or {}
        self.light = light
        self.hatch = hatch
        self.hatch_op = hatch_op
        self.lw = lw if lw is not None else max(1.0, min(2.4, u * 0.075))
        self.skin = skin
        self.tilt = pose.tilt if head_tilt is None else head_tilt
        self.eyes = eyes
        self.line_op = line_op
        self.props = props or []
        self.details = details
        self.hair_tone = hair_tone
        self.hood_long = hood_long

    def P(self, p):
        return (self.x + self.d * p[0] * self.u, self.y - p[1] * self.u)

    def Ps(self, pts):
        return [self.P(p) for p in pts]

    def _arm_polys(self, side):
        spec = self.arms.get(side)
        if spec is None:
            spec = (8, 14) if side == "n" else (-6, -2)
        if spec == "none":
            return None
        if isinstance(spec, dict):
            sh = spec.get("sh", self.p.sh_n if side == "n" else self.p.sh_f)
            e, w = spec["e"], spec["w"]
            hand = spec.get("hand", "mitt")
            obj = spec.get("obj")
        else:
            sh = self.p.sh_n if side == "n" else self.p.sh_f
            a_up, a_fore = spec[0], spec[1]
            hand = spec[2] if len(spec) > 2 else "mitt"
            obj = spec[3] if len(spec) > 3 else None
            e, w = arm_chain(sh, a_up, a_fore)
        S, E, Wr = self.P(sh), self.P(e), self.P(w)
        u = self.u
        ang = math.atan2(Wr[1] - E[1], Wr[0] - E[0])
        ca, sa = math.cos(ang), math.sin(ang)
        nx, ny = -sa, ca
        # the sleeve: upper arm a capsule, the forearm widening to an open cuff
        cuff = 0.3 * u
        fore = [(E[0] + nx * 0.21 * u, E[1] + ny * 0.21 * u), (Wr[0] + nx * cuff + ca * 0.04 * u, Wr[1] + ny * cuff + sa * 0.04 * u),
                (Wr[0] + ca * 0.08 * u, Wr[1] + sa * 0.08 * u),
                (Wr[0] - nx * cuff + ca * 0.04 * u, Wr[1] - ny * cuff + sa * 0.04 * u), (E[0] - nx * 0.21 * u, E[1] - ny * 0.21 * u)]
        sleeve = [capsule(S, E, 0.5 * u, 0.42 * u), fore]
        tip = (Wr[0] + ca * 0.42 * u, Wr[1] + sa * 0.42 * u)
        flip = -1 if (self.d * (1 if side == "n" else -1)) < 0 else 1

        def local(pts, k=1.0):
            return [(Wr[0] + (ca * x - sa * y * flip) * u * k, Wr[1] + (sa * x + ca * y * flip) * u * k) for x, y in pts]
        if hand == "open":
            handp = local([(0.02, -0.13), (0.3, -0.16), (0.52, -0.12), (0.56, 0.0), (0.5, 0.1), (0.3, 0.13), (0.26, 0.24), (0.14, 0.24), (0.06, 0.14), (0.0, 0.1)])
        elif hand == "fist":
            handp = local([(0.02, -0.13), (0.22, -0.15), (0.32, -0.08), (0.33, 0.06), (0.24, 0.13), (0.06, 0.13)])
        elif hand == "cup":
            handp = local([(0.02, -0.13), (0.3, -0.14), (0.42, -0.04), (0.38, 0.1), (0.2, 0.15), (0.04, 0.12)])
        else:
            handp = local([(0.02, -0.12), (0.26, -0.13), (0.42, -0.07), (0.44, 0.02), (0.36, 0.08), (0.22, 0.1), (0.2, 0.17), (0.1, 0.16), (0.03, 0.1)])
        return sleeve, handp, (S, E, Wr, ang, hand, obj, tip)

    def _draw_arm(self, side):
        r = self._arm_polys(side)
        if r is None:
            return
        sleeve, handp, info = r
        S, E, Wr, ang, hand, obj, tip = info
        sk = self.sk
        sk.blob(sleeve, grey(self.tone if side == "n" else self.tone - 0.06), self.lw, self.light, self.hatch, 3.4, self.hatch_op,
                line_op=self.line_op)
        sk.blob([handp], grey(self.skin), self.lw * 0.8, self.light, self.hatch, 3.0, self.hatch_op * 0.8, construct=False, line_op=self.line_op)
        # cuff line
        u = self.u
        nx, ny = -math.sin(ang), math.cos(ang)
        c = (Wr[0] - math.cos(ang) * 0.02 * u, Wr[1] - math.sin(ang) * 0.02 * u)
        sk.line([(c[0] + nx * 0.27 * u, c[1] + ny * 0.27 * u), (c[0] - nx * 0.27 * u, c[1] - ny * 0.27 * u)], self.lw * 0.5, 0.45, passes=1, overshoot=0)
        if hand == "open" and u > 14:
            for k in (-1, 0, 1):
                b0 = (Wr[0] + math.cos(ang) * 0.32 * u + nx * k * 0.06 * u, Wr[1] + math.sin(ang) * 0.32 * u + ny * k * 0.06 * u)
                sk.line([b0, (b0[0] + math.cos(ang) * 0.2 * u, b0[1] + math.sin(ang) * 0.2 * u)], self.lw * 0.45, 0.55, passes=1, overshoot=0)
        if obj:
            obj(sk, Wr, ang, u, self)

    def _feet(self):
        for fx, fy, fa in self.p.feet:
            p = self.P((fx, fy))
            u = self.u
            if fa == 0:
                pts = [(p[0] - self.d * 0.25 * u, p[1]), (p[0] + self.d * 0.55 * u, p[1]), (p[0] + self.d * 0.45 * u, p[1] - 0.22 * u),
                       (p[0] - self.d * 0.2 * u, p[1] - 0.3 * u)]
            else:
                a = math.radians(fa)
                pts = ellipse_pts(p[0] + self.d * math.cos(a) * 0.1 * u, p[1] - 0.1 * u, 0.32 * u, 0.15 * u, 10, 0 if abs(fa) > 90 else 0)
            self.sk.blob([pts], grey(self.skin - 0.1), self.lw * 0.7, None, False, construct=False, line_op=self.line_op)

    def _head_polys(self):
        u, d = self.u, self.d
        hc = self.P(self.p.head)
        s = self.turn * d  # screen-space turn: + means looking screen right
        tilt = math.radians(self.tilt) * d
        rx, ry = 0.4 * u, 0.5 * u
        pts = []
        for i in range(32):
            t = 2 * math.pi * i / 32
            x, y = rx * math.cos(t), -ry * math.sin(t)  # y down
            if y > 0:  # lower half: narrow toward the chin, pushed toward the face side
                k = y / ry
                x = x * (1 - 0.32 * k) + s * 0.14 * u * k
                y = y * (1 + 0.08 * k)
            pts.append((x, y))
        if abs(s) > 0.35 and self.head != "back":
            # the nose and brow break the outline on the face side
            sign = 1 if s > 0 else -1
            prof = [(sign * (rx + 0.03 * u), -0.05 * u), (sign * (rx + 0.13 * u * abs(s)), 0.12 * u), (sign * (rx - 0.02 * u), 0.2 * u)]
            # insert: replace the points on the face side between y=-0.08u and 0.22u
            keep = [p for p in pts if not (sign * p[0] > 0.2 * u and -0.08 * u < p[1] < 0.24 * u)]
            # find insertion index (closest to the brow point)
            idx = min(range(len(keep)), key=lambda i: dist(keep[i], prof[0]))
            keep = keep[:idx + 1] + (prof if sign > 0 else prof) + keep[idx + 1:]
            if sign < 0:
                keep = [p for p in pts if not (sign * p[0] > 0.2 * u and -0.08 * u < p[1] < 0.24 * u)]
                idx = min(range(len(keep)), key=lambda i: dist(keep[i], prof[-1]))
                keep = keep[:idx + 1] + prof[::-1] + keep[idx + 1:]
            pts = keep
        ct, st = math.cos(tilt), math.sin(tilt)
        rot = lambda p: (hc[0] + p[0] * ct - p[1] * st, hc[1] + p[0] * st + p[1] * ct)
        return [rot(p) for p in pts], rot, s

    def _draw_head(self):
        sk, u, d = self.sk, self.u, self.d
        head, rot, s = self._head_polys()
        neck = capsule(self.P(self.p.neck), self.P(((self.p.neck[0] * 0.4 + self.p.head[0] * 0.6), self.p.head[1] - 0.2)), 0.34 * u, 0.34 * u)
        sk.blob([neck], grey(self.skin - 0.08), self.lw * 0.8, self.light, self.hatch, 3.2, self.hatch_op, construct=False, line_op=self.line_op)
        hw = self.head
        sg = 1 if s > 0.05 else (-1 if s < -0.05 else 0)
        back = -sg  # the side of the head away from the face (0 = front view)
        fr = sg
        if hw in ("veil", "headcloth"):
            # the mantle: over the crown, framing the face, over both shoulders and down the back
            longv = (2.7 if self.hood_long else 2.0) if hw == "veil" else 1.45
            frontv = 1.9 if hw == "veil" else 1.2
            bk = back if back else -1
            fw = fr if fr else 1
            sym = 1.0 if sg else 0.0
            vp = [(0.0, -0.68), (bk * 0.5, -0.56), (bk * (0.62 + 0.02 * sym), -0.1), (bk * 0.72, 0.55), (bk * (1.0 + 0.1 * sym), 1.15),
                  (bk * (1.1 + 0.1 * sym), longv - 0.5), (bk * (0.95 + 0.1 * sym), longv), (bk * 0.3, longv - 0.15 - (0.4 if not sg else 0)),
                  (fw * (0.25 if sg else 0.3), frontv - (0.25 if sg else 0.15)), (fw * (0.85 if sg else 1.05), frontv),
                  (fw * (0.95 if sg else 1.1), 1.2), (fw * (0.68 if sg else 0.75), 0.6), (fw * (0.55 if sg else 0.58), 0.0), (fw * 0.48, -0.45)]
            vt = self.veil_tone if hw == "veil" else self.tone + 0.06
            sk.blob([[rot((x * u, y * u)) for x, y in vp]], grey(vt), self.lw, self.light, self.hatch, 3.4, self.hatch_op, line_op=self.line_op)
            # a couple of fold lines in the mantle
            for k in (0.35, 0.7):
                a = (bk * (0.7 + 0.3 * k), 0.5 + k * 0.5)
                b = (bk * (0.6 + 0.5 * k), longv - 0.2)
                sk.line([rot((a[0] * u, a[1] * u)), rot((b[0] * u, b[1] * u))], self.lw * 0.55, 0.4, passes=1)
        if hw == "back":
            sk.blob([head], grey(self.skin - 0.05), self.lw, self.light, self.hatch, 3.2, self.hatch_op, line_op=self.line_op)
        else:
            sk.blob([head], grey(self.skin), self.lw, self.light, self.hatch, 3.2, self.hatch_op * 0.9, construct=False, line_op=self.line_op)
        if hw == "hair":
            # short dark hair: over the crown and down the back of the head to the nape; hairline above the brow
            sgn = 1 if s >= 0 else -1
            hp = [(-0.4, 0.3), (-0.5, -0.05), (-0.44, -0.4), (-0.18, -0.6), (0.15, -0.6), (0.38, -0.45), (0.46, -0.28),
                  (0.3 + 0.1 * abs(s), -0.3), (0.05 + 0.2 * abs(s), -0.36), (-0.1 + 0.1 * abs(s), -0.26), (-0.12, 0.05), (-0.24, 0.3)]
            hp = [(sgn * x * u, y * u) for x, y in hp]
            sk.blob([[rot(p) for p in hp]], grey(self.hair_tone), self.lw * 0.9, None, False, construct=False, line_op=self.line_op)
        # the band of the mantle over the crown, framing the face
        if hw == "back":
            cap = [(-0.5, 0.0), (-0.52, -0.32), (-0.34, -0.58), (0, -0.65), (0.34, -0.58), (0.52, -0.32), (0.5, 0.0), (0.62, 0.42), (0.95, 0.85), (0.5, 0.92), (0.0, 0.98), (-0.5, 0.92), (-0.95, 0.85), (-0.62, 0.42)]
            sk.blob([[rot((x * u, y * u)) for x, y in cap]], grey(self.veil_tone), self.lw, self.light, self.hatch, 3.4, self.hatch_op, line_op=self.line_op)
            if self.beard is not False:
                sk.line([rot((-0.5 * u, -0.12 * u)), rot((0, -0.2 * u)), rot((0.5 * u, -0.12 * u))], self.lw * 1.8, 0.85, passes=1)
                for k in (-0.25, 0.0, 0.25):
                    sk.line([rot((k * u, 0.0)), rot((k * 1.3 * u, 0.8 * u))], self.lw * 0.5, 0.4, passes=1)
        elif hw in ("veil", "headcloth"):
            fx = s * 0.1
            bk = back
            cap = [(-0.5, 0.15), (-0.54, -0.25), (-0.32, -0.62), (0.0, -0.7), (0.32, -0.62), (0.54, -0.25), (0.5, 0.15),
                   (0.42 + 0.06 * (bk > 0), -0.05), (0.36 + fx, -0.3), (fx, -0.4), (-0.36 + fx, -0.3), (-0.42 - 0.06 * (bk < 0), -0.05)]
            if bk:
                # on the back side the cloth comes down past the ear
                cap = [(x, y) for x, y in cap]
                cap.insert(0, (bk * 0.3, 0.45)) if bk < 0 else cap.insert(6, (bk * 0.3, 0.45))
            cap = [(x + (0.04 * s if x * s < 0 else 0.0), y) for x, y in cap]
            vt = self.veil_tone if hw == "veil" else self.tone + 0.06
            sk.blob([[rot((x * u, y * u)) for x, y in cap]], grey(vt), self.lw, self.light, self.hatch, 3.4, self.hatch_op, construct=False, line_op=self.line_op)
            if hw == "headcloth":
                band = [(-0.5, -0.12), (fx, -0.4), (0.5, -0.12)]
                sk.line([rot((x * u, y * u)) for x, y in band], self.lw * 1.5, 0.8, passes=1)
            elif u > 14:
                # hair showing under the veil's edge
                for k in range(3):
                    x0 = fx + (-0.22 + 0.2 * k)
                    sk.line([rot((x0 * u, -0.4 * u)), rot(((x0 + 0.06) * u, -0.3 * u))], self.lw * 0.6, 0.6, passes=1, overshoot=0)
        if self.beard is not False and hw != "back":
            bp = [(-0.38 + s * 0.08, 0.05), (-0.33 + s * 0.12, 0.45), (s * 0.2, 0.76), (0.33 + s * 0.12, 0.45), (0.38 + s * 0.08, 0.05),
                  (0.28 + s * 0.15, 0.3), (0.12 + s * 0.2, 0.3), (s * 0.2, 0.46), (-0.12 + s * 0.2, 0.3), (-0.28 + s * 0.15, 0.3)]
            if sg:  # three-quarter: the beard lies along the jaw toward the face side
                bp = [(x if x * sg > -0.15 else x * 0.75, y) for x, y in bp]
            bt = 0.52 if self.beard is True else self.beard
            sk.blob([[rot((x * u, y * u)) for x, y in bp]], grey(bt), self.lw * 0.8, self.light, self.hatch, 3.0,
                    self.hatch_op, construct=False, line_op=self.line_op)
        if hw not in ("back",) and u >= 9:
            self._face(rot, s)

    def _face(self, rot, s):
        sk, u = self.sk, self.u
        w = max(0.8, self.lw * 0.7)
        fx = s * 0.2 * u  # the face's centre line shifts toward where it looks
        spread = 0.16 * u * (1 - 0.4 * abs(s))
        ey = 0.0
        eyes = [(fx - spread, ey, -1), (fx + spread, ey, 1)]
        if abs(s) > 0.62:
            eyes = [e for e in eyes if e[2] * s > 0]
        small = u < 18
        R = lambda x, y: rot((x, y))
        for ex, eyy, side in eyes:
            far = side * s < 0
            ew = 0.075 * u * (0.7 if far else 1.0)
            if self.eyes == "closed" or self.expr == "grief":
                sk.line([R(ex - ew, eyy - 0.01 * u), R(ex, eyy + 0.03 * u), R(ex + ew, eyy - 0.01 * u)], w, 0.9, passes=1, amp=0.15, overshoot=0)
            elif self.eyes == "down":
                sk.line([R(ex - ew, eyy + 0.01 * u), R(ex, eyy + 0.035 * u), R(ex + ew, eyy + 0.015 * u)], w * 1.2, 0.9, passes=1, amp=0.15, overshoot=0)
            elif small:
                c = R(ex + s * 0.02 * u, eyy)
                sk.add(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{max(0.9, 0.05 * u):.1f}" fill="{INK}" fill-opacity="0.85"/>')
            else:
                op = 0.13 * u if self.expr == "startle" else 0.085 * u
                # almond: upper lid line, lower lid, pupil toward the look direction
                sk.line([R(ex - ew, eyy), R(ex, eyy - op * 0.55), R(ex + ew, eyy)], w * 1.1, 0.9, passes=1, amp=0.1, overshoot=0)
                sk.line([R(ex - ew * 0.6, eyy + 0.015 * u), R(ex, eyy + op * 0.4), R(ex + ew * 0.6, eyy + 0.015 * u)], w * 0.4, 0.3, passes=1, amp=0.1, overshoot=0)
                c = R(ex + s * 0.03 * u, eyy + 0.005 * u)
                sk.add(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{max(1.0, 0.04 * u * (1.1 if self.expr == "startle" else 1)):.1f}" fill="{INK}" fill-opacity="0.9"/>')
            if not small:
                lift = -0.16 * u if self.expr in ("startle", "laugh") else -0.12 * u
                inner_up = 0.05 * u if self.expr in ("grief", "sad") else (-0.02 * u if self.expr == "stern" else 0)
                xin, xout = (ex + side * -ew * 1.0, ex + side * ew * 1.25)
                sk.line([R(xin, eyy + lift - inner_up), R((xin + xout) / 2, eyy + lift - 0.025 * u), R(xout, eyy + lift + 0.01 * u)], w * 1.1, 0.8, passes=1, amp=0.1, overshoot=0)
        # nose: down from between the brows on the face side, a small hook at the end
        if not small:
            nx = fx + s * 0.06 * u
            sk.line([R(nx - s * 0.02 * u, 0.03 * u), R(nx + s * 0.07 * u, 0.19 * u), R(nx - s * 0.03 * u + (0.0 if abs(s) > 0.2 else -0.04 * u), 0.23 * u)], w, 0.75, passes=1, amp=0.1, overshoot=0)
        else:
            sk.line([R(fx + s * 0.06 * u, 0.08 * u), R(fx + s * 0.02 * u, 0.2 * u)], w, 0.6, passes=1, amp=0.1, overshoot=0)
        my = 0.36 * u
        mw = 0.12 * u * (1 - 0.3 * abs(s))
        mx = fx + s * 0.02 * u
        if self.expr == "laugh":
            pts = [(mx - mw * 1.25, my - 0.04 * u), (mx, my - 0.02 * u), (mx + mw * 1.25, my - 0.04 * u), (mx + mw * 0.6, my + 0.1 * u), (mx - mw * 0.6, my + 0.1 * u)]
            sk.add(f'<path d="{smooth_d([R(*p) for p in pts], True)}" fill="{INK}" fill-opacity="0.75"/>')
            if not small:
                for sgn in (-1, 1):
                    sk.line([R(mx + sgn * mw * 1.6, my - 0.17 * u), R(mx + sgn * mw * 1.9, my - 0.03 * u)], w * 0.6, 0.45, passes=1, amp=0.1, overshoot=0)
        elif self.expr == "startle":
            c = R(mx, my + 0.02 * u)
            sk.add(f'<ellipse cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="{mw * 0.55:.1f}" ry="{0.065 * u:.1f}" fill="{INK}" fill-opacity="0.75"/>')
        elif self.expr in ("grief", "sad"):
            sk.line([R(mx - mw, my + 0.03 * u), R(mx, my - 0.005 * u), R(mx + mw, my + 0.03 * u)], w, 0.8, passes=1, amp=0.1, overshoot=0)
        elif self.expr == "smile":
            sk.line([R(mx - mw, my - 0.025 * u), R(mx, my + 0.03 * u), R(mx + mw, my - 0.025 * u)], w, 0.8, passes=1, amp=0.1, overshoot=0)
        elif self.expr == "speak":
            c = R(mx, my + 0.01 * u)
            sk.add(f'<ellipse cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="{mw * 0.7:.1f}" ry="{0.04 * u:.1f}" fill="{INK}" fill-opacity="0.7"/>')
        else:
            sk.line([R(mx - mw, my), R(mx + mw, my + 0.005 * u)], w, 0.75, passes=1, amp=0.1, overshoot=0)
        if abs(s) > 0.25 and self.head in ("hair", "bare") and not small:
            ex = -(1 if s > 0 else -1) * 0.2 * u
            c = R(ex, 0.08 * u)
            sk.add(f'<ellipse cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="{0.07 * u:.1f}" ry="{0.11 * u:.1f}" fill="none" stroke="{INK}" stroke-width="{w}" stroke-opacity="0.6"/>')

    def draw(self):
        sk = self.sk
        # far arm, under the body
        self._draw_arm("f")
        self._feet()
        if self.p.extra_polys:
            sk.blob([self.Ps(P) for P in self.p.extra_polys], grey(self.skin - 0.08), self.lw * 0.9, self.light, self.hatch, 3.4, self.hatch_op,
                    construct=False, line_op=self.line_op)
        body = [self.Ps(P) for P in self.p.body]
        sk.blob(body, grey(self.tone), self.lw, self.light, self.hatch, 3.6, self.hatch_op, line_op=self.line_op)
        if self.details:
            for f in self.p.folds:
                sk.line(self.Ps(f), self.lw * 0.6, 0.45 * self.details, passes=1, amp=0.8)
            if self.p.belt:
                b = self.Ps(self.p.belt)
                sk.line(b, self.lw * 1.3, 0.7 * self.details, passes=2, amp=0.5)
        for pr in self.props:
            if pr[0] == "before_head":
                pr[1](sk, self)
        self._draw_head()
        self._draw_arm("n")
        for pr in self.props:
            if pr[0] == "after":
                pr[1](sk, self)
        return self


# ----------------------------------------------------------------------------------------------- props held in hands

def obj_bread(sk, Wr, ang, u, fig):
    c = (Wr[0] + math.cos(ang) * 0.4 * u, Wr[1] + math.sin(ang) * 0.4 * u - 0.15 * u)
    sk.shape(ellipse_pts(c[0], c[1], 0.45 * u, 0.25 * u, 14), grey(0.7), fig.lw * 0.8)
    sk.line([(c[0] - 0.25 * u, c[1] - 0.05 * u), (c[0] + 0.2 * u, c[1] - 0.1 * u)], fig.lw * 0.5, 0.5, passes=1)


def obj_sandal(sk, Wr, ang, u, fig):
    c = (Wr[0] + math.cos(ang) * 0.55 * u, Wr[1] + math.sin(ang) * 0.55 * u + 0.15 * u)
    sole = [(c[0] - 0.55 * u, c[1] - 0.05 * u), (c[0] + 0.5 * u, c[1] - 0.12 * u), (c[0] + 0.6 * u, c[1] + 0.05 * u), (c[0] - 0.5 * u, c[1] + 0.12 * u)]
    sk.shape(sole, grey(0.45), fig.lw * 0.9)
    for k in (-0.2, 0.15):
        sk.line([(c[0] + k * u, c[1] - 0.05 * u), (c[0] + (k + 0.1) * u, c[1] - 0.3 * u), (c[0] + (k + 0.25) * u, c[1] - 0.05 * u)], fig.lw * 0.6, 0.7, passes=1)


def obj_grain(sk, Wr, ang, u, fig):
    c = (Wr[0] + math.cos(ang) * 0.35 * u, Wr[1] + math.sin(ang) * 0.35 * u - 0.12 * u)
    r = sk.rng
    for _ in range(14):
        x = c[0] + r.uniform(-0.25, 0.25) * u
        y = c[1] + r.uniform(-0.12, 0.06) * u
        sk.add(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{0.05 * u:.1f}" ry="{0.03 * u:.1f}" fill="{grey(0.35)}" transform="rotate({r.uniform(0, 180):.0f} {x:.1f} {y:.1f})"/>')


def obj_sickle(sk, Wr, ang, u, fig):
    c = (Wr[0] + math.cos(ang) * 0.4 * u, Wr[1] + math.sin(ang) * 0.4 * u)
    d = fig.d
    pts = [c, (c[0] + d * 0.3 * u, c[1] + 0.25 * u), (c[0] + d * 0.85 * u, c[1] + 0.15 * u), (c[0] + d * 1.05 * u, c[1] - 0.25 * u)]
    sk.line(pts, fig.lw * 1.1, 0.85, passes=2)


def obj_stalks(sk, Wr, ang, u, fig):
    c = (Wr[0] + math.cos(ang) * 0.3 * u, Wr[1] + math.sin(ang) * 0.3 * u)
    for k in range(5):
        a = -math.pi / 2 + (k - 2) * 0.15
        p2 = (c[0] + math.cos(a) * 1.2 * u, c[1] + math.sin(a) * 1.2 * u)
        sk.line([c, p2], fig.lw * 0.5, 0.7, passes=1)
        sk.add(f'<ellipse cx="{p2[0]:.1f}" cy="{p2[1]:.1f}" rx="{0.06 * u:.1f}" ry="{0.18 * u:.1f}" fill="{grey(0.45)}" transform="rotate({math.degrees(a) + 90:.0f} {p2[0]:.1f} {p2[1]:.1f})"/>')


def obj_strip(sk, Wr, ang, u, fig):
    """A torn strip of cloth trailing from the hand."""
    c = (Wr[0] + math.cos(ang) * 0.4 * u, Wr[1] + math.sin(ang) * 0.4 * u)
    pts = [c, (c[0] - fig.d * 0.2 * u, c[1] + 0.4 * u), (c[0] + fig.d * 0.1 * u, c[1] + 0.8 * u)]
    sk.line(pts, 0.18 * u, 0.25, passes=1, color=INK)
    sk.line(pts, fig.lw * 0.6, 0.8, passes=1)


def obj_lid(sk, Wr, ang, u, fig):
    c = (Wr[0] + math.cos(ang) * 0.45 * u, Wr[1] + math.sin(ang) * 0.45 * u)
    sk.shape(ellipse_pts(c[0], c[1], 0.75 * u, 0.22 * u, 16, 0.25 * fig.d), grey(0.62), fig.lw)
    sk.line([(c[0] - 0.1 * u, c[1] - 0.2 * u), (c[0] + 0.1 * u, c[1] - 0.22 * u)], fig.lw * 1.5, 0.8, passes=1)


# ----------------------------------------------------------------------------------------------- landscape helpers

def ridge(sk, pts, tone, base_y, light=None, line=1.4, hatch_sp=5, hatch_op=0.3, op=1.0):
    poly = list(pts) + [(pts[-1][0], base_y), (pts[0][0], base_y)]
    sk.fill(poly, grey(tone), op, amp=1.0)
    if light is not None:
        sk.hatch_region([poly], hatch_sp, None, 0.7, hatch_op, light, 0.3, 0.9)
    sk.line(pts, line, 0.8, amp=1.4)


def stones(sk, rng, n, x0, y0, x1, y1, size=(4, 10), tone=0.55, light=(1, 0.3), persp=True):
    for _ in range(n):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        k = (y - y0) / max(y1 - y0, 1) if persp else 0.5
        s = lerp(size[0], size[1], k) * rng.uniform(0.7, 1.3)
        pts = [(x + math.cos(a) * s * rng.uniform(0.7, 1.1), y + math.sin(a) * s * 0.6 * rng.uniform(0.7, 1.1)) for a in
               [i * math.pi * 2 / 7 for i in range(7)]]
        sk.fill(pts, grey(tone + rng.uniform(-0.08, 0.08)), 1, amp=0.4, smooth=False)
        sk.line(pts, 0.9, 0.6, closed=True, passes=1, amp=0.4)
        # shadow side
        sk.line([(x + light[0] * s * 0.6 + 0.0, y + s * 0.15), (x + light[0] * s * 0.2, y + s * 0.55)], 1.6, 0.4, passes=1)


def grass(sk, rng, n, x0, y0, x1, y1, h=(4, 10), op=0.5):
    d = []
    for _ in range(n):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        k = (y - y0) / max(y1 - y0, 1)
        hh = lerp(h[0], h[1], k)
        for j in range(3):
            a = rng.uniform(-0.5, 0.5)
            d.append(f"M{x + j * 1.5:.1f},{y:.1f}q{a * hh * 0.3:.1f},{-hh * 0.5:.1f} {a * hh:.1f},{-hh:.1f}")
    sk.add(f'<path d="{"".join(d)}" fill="none" stroke="{INK}" stroke-width="0.8" stroke-opacity="{op}" stroke-linecap="round"/>')


def scribble_ground(sk, rng, x0, y0, x1, y1, n=60, op=0.25, horizon=None):
    """Loose horizontal strokes on the ground, shorter and closer toward the horizon."""
    d = []
    for _ in range(n):
        y = rng.uniform(y0, y1)
        k = (y - y0) / max(y1 - y0, 1)
        L = lerp(10, 70, k)
        x = rng.uniform(x0 - 20, x1)
        d.append(f"M{x:.1f},{y:.1f}q{L / 2:.1f},{rng.uniform(-1.5, 1.5):.1f} {L:.1f},{rng.uniform(-1, 1):.1f}")
    sk.add(f'<path d="{"".join(d)}" fill="none" stroke="{INK}" stroke-width="0.8" stroke-opacity="{op}" stroke-linecap="round"/>')


def cast_shadow(sk, x, y, w, h, dx=0.0, op=0.22):
    pts = ellipse_pts(x + dx / 2, y, w / 2 + abs(dx) / 2, h / 2, 18)
    sk.fill(pts, INK, op, amp=0.8)


def masonry(sk, rng, x0, y0, x1, y1, course=14, tone=0.7, op=0.55, light=None, wash=True):
    """A rough stone wall face: wash, then irregular courses and joints."""
    if wash:
        sk.fill([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], grey(tone), 1, amp=0.6, smooth=False)
    y = y0 + course * rng.uniform(0.6, 1.0)
    d = []
    while y < y1 - 2:
        d.append(f"M{x0:.1f},{y:.1f}" + "".join(f"L{x:.1f},{y + rng.uniform(-1.5, 1.5):.1f}" for x in [lerp(x0, x1, t / 6) for t in range(1, 7)]))
        x = x0 + rng.uniform(0, course * 1.5)
        while x < x1:
            yy = y - course * rng.uniform(0.8, 1.0)
            d.append(f"M{x:.1f},{max(yy, y0):.1f}L{x + rng.uniform(-1.5, 1.5):.1f},{y:.1f}")
            x += course * rng.uniform(1.2, 2.6)
        y += course * rng.uniform(0.8, 1.15)
    sk.add(f'<path d="{"".join(d)}" fill="none" stroke="{INK}" stroke-width="0.9" stroke-opacity="{op}" stroke-linecap="round"/>')
    sk.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 1.5, 0.8, closed=True, amp=0.8)


def arrow(sk, pts, color="#9b3b2f", w=2.4, op=0.85, head=14, label=None, label_dx=8, label_dy=-8, size=17):
    """A storyboard arrow (movement / camera), in red pencil."""
    sk.line(pts, w, op, color=color, passes=2, amp=0.6)
    a, b = pts[-2], pts[-1]
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-1, 1):
        q = (b[0] - math.cos(ang + s * 0.45) * head, b[1] - math.sin(ang + s * 0.45) * head)
        sk.line([q, b], w, op, color=color, passes=1, amp=0.3, overshoot=0)
    if label:
        sk.add(f'<text x="{b[0] + label_dx:.0f}" y="{b[1] + label_dy:.0f}" font-family="DejaVu Sans, sans-serif" font-size="{size}" '
               f'font-style="italic" fill="{color}" fill-opacity="0.9">{label}</text>')


def note(sk, x, y, text, size=17, color="#9b3b2f", anchor="start", halo=None):
    if halo is None:
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        halo = PAPER if (0.3 * r + 0.59 * g + 0.11 * b) < 140 else "#1c1b1a"
    sk.add(f'<text x="{x:.0f}" y="{y:.0f}" font-family="DejaVu Sans, sans-serif" font-size="{size}" font-style="italic" '
           f'fill="{color}" fill-opacity="0.95" text-anchor="{anchor}" stroke="{halo}" stroke-opacity="0.75" stroke-width="3.5" paint-order="stroke" stroke-linejoin="round">{text}</text>')


def inset(sk, x, y, w, h, label=None):
    """Frame for an inset close-up: returns the transform to draw into it (draw at full scale, scaled into the box)."""
    sk.add(f'<rect x="{x - 4}" y="{y - 4}" width="{w + 8}" height="{h + 8}" fill="{PAPER}"/>')
    sk.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{INK}" stroke-width="2.5" stroke-opacity="0.85"/>')
    if label:
        note(sk, x + 6, y + h + 20, label, 15)
