"""Painting with real brush strokes, in a texture's own space (the style test of the painted look,
PLAN §9 item 3; your notes of 2026-10-15: it should genuinely look painted).

    py brush.py BASE.npy LIGHT.npy OUT.png [--palette skin|hair] [--radii 16,8,4,2]
                [--region REGION.json] [--along v] [--ao AO.npy] [--bristles 0|1] [--threshold 14]

BASE and LIGHT are what Blender baked into the model's UVs (face_test.py): its colour, and the
light that reaches it (cast shadows and all). First the two make the picture to paint: the colour
in its light, the shadow a cooler, darker version of it, soft-edged, with a little warmth where
light turns to shadow (compose). Then the painter covers a canvas with strokes, big brushes first,
then smaller ones only where the picture still differs: each stroke a curve that follows the form,
along the lines of equal light, in one colour, laid opaque, with bristle streaks in it. That's
Hertzmann's method (Painterly Rendering with Curved Brush Strokes of Multiple Sizes, SIGGRAPH
1998). Painted in the texture, the strokes stay on the surface as it moves, so nothing flickers.
--region: UV polygons (from face_test.py) of the part the camera sees; only there are the finer
brushes used. --along v: strokes run along the texture's v (hair: along the strands).
--ao: the occlusion close in, baked too: where it's deep (creases: the lids, the nostrils, the
line of the lips; the gaps between locks of hair) the picture is painted dark there, as a painter
accents them. --bristles 0: no bristle streaks (skin is painted smooth, as on Vi).
"""
import argparse
import json
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PALETTES = {
    # shadow, light: what the colour is multiplied by in shadow and in light; soft: where in the
    # light the shadow turns (a wide, soft turn); warm: the warmth where it turns; highlight: a
    # colour laid where the light is strongest, and from how strong.
    # After the frame of Vi (your reference, 2026-10-15): pale, muted skin, mostly in light, the
    # shadow a cool grey-brown in a soft, wide gradient; dark accents in the creases; the hair's
    # locks parted by dark and lit with strong painted highlights.
    "skin": dict(shadow=(0.6, 0.54, 0.53), light=(1.02, 1.0, 0.97), soft=(0.15, 0.8),
                 warm=((1.05, 0.92, 0.88), 0.12), highlight=None,
                 crease=((0.45, 0.36, 0.36), 0.45), crease_at=(0.62, 0.32), wet=0.35),
    "hair": dict(shadow=(0.45, 0.42, 0.5), light=(1.05, 1.0, 0.94), soft=(0.04, 0.5),
                 warm=((1.1, 0.9, 0.8), 0.15), highlight=((0.68, 0.52, 0.36), 0.55),
                 crease=((0.3, 0.22, 0.18), 0.5), crease_at=(0.72, 0.36), wet=0.15, strands=True),
}


def srgb(a):
    a = np.clip(a, 0, None)
    return np.where(a <= 0.0031308, 12.92 * a, 1.055 * np.power(a, 1 / 2.4) - 0.055)


def smoothstep(a, b, x):
    u = np.clip((x - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def blur(a, r):
    """A box blur, r pixels each way, twice (near enough a Gaussian)."""
    for _ in range(2):
        for axis in range(min(2, a.ndim)):
            c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode="edge"), axis=axis)
            a = (np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis) - np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)) / (2 * r + 1)
    return a


def compose(base, light, mask, palette, ao=None, masks=None):
    """The picture to paint, 0-255 sRGB: the colour in its painted light, the creases dark. masks
    (from face_test.py): red, where to leave it light; green, the ridges, for highlights where the
    light falls; blue, the line of the closed lids, painted dark."""
    lift = masks[..., 0] if masks is not None else None
    p = PALETTES[palette]
    L = blur(light[..., :3].mean(-1), 3)          # the bake's noise out, so it isn't painted as grit
    top = np.percentile(L[mask > 0], 99) if mask is not None and mask.any() else np.percentile(L, 99)
    L = L / max(top, 1e-6)
    t = smoothstep(p["soft"][0], p["soft"][1], L)[..., None]
    if lift is not None:                            # where a painter leaves it light (under the eyes)
        t = np.maximum(t, 0.85 * blur(lift, 4)[..., None])
    col = srgb(base[..., :3])
    out = col * (np.array(p["shadow"]) * (1 - t) + np.array(p["light"]) * t)
    w = np.exp(-((L - 0.5 * (p["soft"][0] + p["soft"][1])) / 0.12) ** 2)[..., None] * p["warm"][1]
    out = out * (1 + w * (np.array(p["warm"][0]) - 1))
    if p["highlight"]:
        h = smoothstep(p["highlight"][1], p["highlight"][1] + 0.12, L)[..., None]
        if p.get("strands"):                        # the sheen in strands across each lock, not in patches, as on Vi
            n = blur(np.random.default_rng(3).random(L.shape[1]), 2)
            h = h * (0.15 + 0.85 * smoothstep(0.5, 0.62, n))[None, :, None]
        out = out * (1 - h) + np.array(p["highlight"][0]) * h
    if ao is not None and p.get("crease"):
        c = (smoothstep(p["crease_at"][0], p["crease_at"][1], blur(ao[..., :3].mean(-1), 2)) * p["crease"][1])[..., None]
        if lift is not None:
            c = c * (1 - 0.7 * blur(lift, 4)[..., None])
        out = out * (1 - c) + out * np.array(p["crease"][0]) * c
    if masks is not None:
        h = (blur(masks[..., 1], 2) * smoothstep(0.55, 0.95, L) * 0.7)[..., None]     # highlights on the lit ridges
        out = out * (1 - h) + np.minimum(out * np.array((1.14, 1.1, 1.05)) + 0.03, 1.0) * h
        lid = (blur(masks[..., 2], 1) * 0.9)[..., None]                               # the lids' line, bold
        out = out * (1 - lid) + out * np.array((0.3, 0.23, 0.23)) * lid
    return np.clip(out * 255, 0, 255).astype(np.float32)


def region_mask(path, size):
    """The UV polygons of the part the camera sees, drawn into a mask the texture's size."""
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    for poly in json.load(open(path)):
        d.polygon([(u * size, (1 - v) * size) for u, v in poly], fill=255)
    return np.asarray(m.filter(ImageFilter.MaxFilter(9))) > 0


def offset(pts, d):
    """A path moved sideways by d, for a bristle streak along a stroke."""
    out = []
    for i, (x, y) in enumerate(pts):
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        n = math.hypot(tx, ty) or 1.0
        out.append((x - ty / n * d, y + tx / n * d))
    return out


def stroke(x0, y0, R, ref, cv, gx, gy, mag, along, min_len=3, max_len=14, curve=0.75):
    """One stroke from (x0, y0): its colour the picture's there, its path along the lines of equal
    light (or along v), until it would paint over what's already right."""
    H, W = ref.shape[:2]
    col = ref[y0, x0].copy()
    pts = [(float(x0), float(y0))]
    x, y, ldx, ldy = float(x0), float(y0), 0.0, 0.0
    for i in range(1, max_len):
        ix, iy = int(x), int(y)
        if not (0 <= ix < W and 0 <= iy < H):
            break
        if i > min_len and np.abs(ref[iy, ix] - cv[iy, ix]).sum() < np.abs(ref[iy, ix] - col).sum():
            break
        if along == "v":
            dx, dy = 0.15 * math.sin(0.7 * i + x0), 1.0
        else:
            if mag[iy, ix] < 0.05:
                if i > min_len:
                    break
                dx, dy = (ldx, ldy) if (ldx or ldy) else (1.0, 0.0)
            else:
                dx, dy = -gy[iy, ix], gx[iy, ix]
        n = math.hypot(dx, dy) or 1.0
        dx, dy = dx / n, dy / n
        if ldx * dx + ldy * dy < 0:
            dx, dy = -dx, -dy
        if i > 1:
            dx, dy = curve * dx + (1 - curve) * ldx, curve * dy + (1 - curve) * ldy
            n = math.hypot(dx, dy) or 1.0
            dx, dy = dx / n, dy / n
        x, y = x + R * dx, y + R * dy
        ldx, ldy = dx, dy
        pts.append((x, y))
    return pts, col


def lay(draw, pts, col, R, rng, bristles=True):
    """Lay a stroke: opaque, round at its ends, with two bristle streaks a shade off its colour."""
    c = tuple(int(v) for v in col[:3])
    w = max(1, int(round(2 * R)))
    if len(pts) > 1:
        draw.line(pts, fill=c, width=w, joint="curve")
    for x, y in (pts[0], pts[-1]):
        draw.ellipse((x - R, y - R, x + R, y + R), fill=c)
    if bristles and R >= 3 and len(pts) > 1:
        for _ in range(2):
            k = rng.uniform(0.9, 1.1)
            cc = tuple(int(min(255, max(0, v * k))) for v in c)
            draw.line(offset(pts, rng.uniform(-0.55, 0.55) * R), fill=cc, width=max(1, w // 5), joint="curve")


def paint(ref, radii, fine=None, along=None, threshold=14.0, seed=7, bristles=True):
    """Hertzmann's painter: a layer of strokes for each brush size, big to small; the smaller ones
    only where the canvas still differs from the picture by more than `threshold` (0-255), and,
    for the two finest, only inside `fine`."""
    rng = random.Random(seed)
    H, W = ref.shape[:2]
    canvas = Image.fromarray(np.uint8(ref)).filter(ImageFilter.GaussianBlur(radii[0] * 2))
    for li, R in enumerate(radii):
        refR = np.asarray(Image.fromarray(np.uint8(ref)).filter(ImageFilter.GaussianBlur(max(0.6, 0.5 * R)))).astype(np.float32)
        L = refR @ np.array([0.3, 0.59, 0.11], np.float32)
        gy, gx = np.gradient(L)
        mag = np.hypot(gx, gy)
        cv = np.asarray(canvas).astype(np.float32)
        D = np.sqrt(((cv - refR) ** 2).sum(-1))
        if fine is not None and li >= len(radii) - 2:
            D = D * fine
        g = max(1, int(R))
        H2, W2 = (H // g) * g, (W // g) * g
        blocks = D[:H2, :W2].reshape(H2 // g, g, W2 // g, g).transpose(0, 2, 1, 3).reshape(H2 // g, W2 // g, g * g)
        err, arg = blocks.mean(-1), blocks.argmax(-1)
        cells = np.argwhere(err > (0.0 if li == 0 else threshold))
        strokes = [stroke(bx * g + arg[by, bx] % g, by * g + arg[by, bx] // g, R, refR, cv, gx, gy, mag, along)
                   for by, bx in cells]
        rng.shuffle(strokes)
        draw = ImageDraw.Draw(canvas)
        for pts, col in strokes:
            lay(draw, pts, col, R, rng, bristles)
        print("brush %d: %d strokes" % (R, len(strokes)), flush=True)
    return canvas


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("light")
    ap.add_argument("out")
    ap.add_argument("--palette", default="skin")
    ap.add_argument("--radii", default="16,8,4,2")
    ap.add_argument("--region")
    ap.add_argument("--along")
    ap.add_argument("--ao")
    ap.add_argument("--masks")
    ap.add_argument("--bristles", type=int, default=1)
    ap.add_argument("--threshold", type=float, default=14.0)
    a = ap.parse_args()
    base = np.load(a.base).astype(np.float32)[::-1]       # Blender's rows run bottom up
    light = np.load(a.light).astype(np.float32)[::-1]
    size = base.shape[0]
    fine = region_mask(a.region, size) if a.region else None
    ao = np.load(a.ao).astype(np.float32)[::-1] if a.ao else None
    masks = np.load(a.masks).astype(np.float32)[::-1] if a.masks else None
    ref = compose(base, light, fine, a.palette, ao, masks)
    Image.fromarray(np.uint8(ref)).save(a.out.replace(".png", "-ref.png"))
    canvas = paint(ref, [int(r) for r in a.radii.split(",")], fine, a.along, a.threshold, bristles=bool(a.bristles))
    wet = PALETTES[a.palette]["wet"]
    if wet:                                         # some of the smooth picture back in, as wet paint is blended
        soft = Image.fromarray(np.uint8(ref)).filter(ImageFilter.GaussianBlur(1.5))
        canvas = Image.blend(canvas, soft, wet)
    canvas.save(a.out)
    print("painted", a.out)
