"""Draw the Ruth storyboard sheets: blocked compositions, not drawings.

Each panel places the figures, the horizon, the light and the camera for one key scene of the
first-draft script, so staging and screen direction can be judged before anything is drawn properly.
Run: python draw.py   (writes sheet-1.png and sheet-2.png next to this file; needs Pillow)
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

W, H = 480, 270
PAD = 12
HERE = os.path.dirname(os.path.abspath(__file__))

NAOMI = (40, 40, 50)
RUTH = (120, 70, 50)
ORPAH = (150, 110, 80)
BOAZ = (200, 180, 140)
ELIMELECH = (70, 60, 50)
SONS = (90, 80, 70)
MOAB = (130, 130, 150)
TOWN = (170, 160, 140)
CHILD = (230, 200, 160)


def font(size=11):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


class Panel:
    def __init__(self):
        self.im = Image.new("RGB", (W, H), (235, 230, 220))
        self.d = ImageDraw.Draw(self.im)

    def sky(self, top, bottom, horizon=0.55):
        hy = int(H * horizon)
        for y in range(hy):
            k = y / max(hy - 1, 1)
            c = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))
            self.d.line([(0, y), (W, y)], fill=c)

    def ground(self, color, horizon=0.55, color2=None):
        hy = int(H * horizon)
        if color2 is None:
            self.d.rectangle([0, hy, W, H], fill=color)
        else:
            for y in range(hy, H):
                k = (y - hy) / max(H - hy - 1, 1)
                c = tuple(int(color[i] + (color2[i] - color[i]) * k) for i in range(3))
                self.d.line([(0, y), (W, y)], fill=c)

    def hills(self, color, pts):
        self.d.polygon([(x * W, y * H) for x, y in pts], fill=color)

    def figure(self, x, y, s, color, pose="stand", face=1, arms=None):
        """x, y: feet position in 0..1; s: height in px."""
        px, py = x * W, y * H
        head_r = s * 0.09
        if pose == "stand":
            self.d.polygon([(px - s * 0.14, py), (px + s * 0.14, py), (px + s * 0.09, py - s * 0.78), (px - s * 0.09, py - s * 0.78)], fill=color)
            self.d.ellipse([px - head_r, py - s * 0.98, px + head_r, py - s * 0.98 + 2 * head_r], fill=color)
        elif pose == "kneel":
            self.d.polygon([(px - s * 0.2, py), (px + s * 0.2, py), (px + s * 0.1, py - s * 0.5), (px - s * 0.1, py - s * 0.5)], fill=color)
            self.d.ellipse([px - head_r, py - s * 0.7, px + head_r, py - s * 0.7 + 2 * head_r], fill=color)
        elif pose == "sit":
            self.d.polygon([(px - s * 0.22, py), (px + s * 0.22, py), (px + s * 0.1, py - s * 0.45), (px - s * 0.1, py - s * 0.45)], fill=color)
            self.d.ellipse([px - head_r, py - s * 0.65, px + head_r, py - s * 0.65 + 2 * head_r], fill=color)
        elif pose == "lie":
            self.d.polygon([(px - s * 0.45, py), (px + s * 0.45, py), (px + s * 0.45, py - s * 0.14), (px - s * 0.45, py - s * 0.14)], fill=color)
            self.d.ellipse([px + s * 0.45, py - s * 0.16, px + s * 0.45 + 2 * head_r, py - s * 0.16 + 2 * head_r], fill=color)
        elif pose == "dance":
            self.d.polygon([(px - s * 0.18, py), (px + s * 0.12, py), (px + s * 0.12, py - s * 0.76), (px - s * 0.12, py - s * 0.76)], fill=color)
            self.d.ellipse([px - head_r + s * 0.05, py - s * 1.0, px + head_r + s * 0.05, py - s * 1.0 + 2 * head_r], fill=color)
            self.d.line([(px, py - s * 0.65), (px + face * s * 0.3, py - s * 0.95)], fill=color, width=max(2, int(s * 0.05)))
            self.d.line([(px, py - s * 0.65), (px - face * s * 0.28, py - s * 0.85)], fill=color, width=max(2, int(s * 0.05)))
        if arms == "out":
            self.d.line([(px, py - s * 0.62), (px + face * s * 0.32, py - s * 0.55)], fill=color, width=max(2, int(s * 0.05)))
        if arms == "up":
            self.d.line([(px, py - s * 0.62), (px + face * s * 0.2, py - s * 0.95)], fill=color, width=max(2, int(s * 0.05)))
        if arms == "hold":
            self.d.ellipse([px + face * s * 0.08 - s * 0.08, py - s * 0.6, px + face * s * 0.08 + s * 0.08, py - s * 0.48], fill=CHILD)

    def prop_rect(self, x0, y0, x1, y1, color):
        self.d.rectangle([x0 * W, y0 * H, x1 * W, y1 * H], fill=color)

    def prop_ellipse(self, x, y, rx, ry, color):
        self.d.ellipse([(x - rx) * W, (y - ry) * H, (x + rx) * W, (y + ry) * H], fill=color)

    def light(self, x, y, label="light"):
        self.d.ellipse([x * W - 6, y * H - 6, x * W + 6, y * H + 6], outline=(240, 200, 60), width=2)
        self.d.text((x * W + 9, y * H - 7), label, fill=(120, 90, 20), font=font(9))

    def arrow(self, x0, y0, x1, y1, label="", color=(200, 40, 40)):
        self.d.line([(x0 * W, y0 * H), (x1 * W, y1 * H)], fill=color, width=2)
        self.d.ellipse([x1 * W - 3, y1 * H - 3, x1 * W + 3, y1 * H + 3], fill=color)
        if label:
            self.d.text((x1 * W + 4, y1 * H - 6), label, fill=color, font=font(9))

    def frame_note(self, text):
        import textwrap
        lines = textwrap.wrap(text, 92)
        self.d.rectangle([0, 0, W, 4 + 13 * len(lines)], fill=(245, 242, 235))
        for i, ln in enumerate(lines):
            self.d.text((6, 3 + 13 * i), ln, fill=(30, 30, 30), font=font(10))

    def done(self):
        self.d.rectangle([0, 0, W - 1, H - 1], outline=(60, 60, 60), width=2)
        return self.im


def panels():
    out = []

    # P1 The bare threshing floor at dawn
    p = Panel(); p.sky((150, 160, 190), (240, 200, 150), 0.5); p.ground((190, 170, 130), 0.5, (160, 140, 100))
    p.hills((170, 150, 120), [(0, 0.5), (0.3, 0.42), (0.6, 0.47), (1, 0.44), (1, 0.5)])
    p.prop_ellipse(0.5, 0.75, 0.32, 0.1, (205, 190, 150))
    p.arrow(0.15, 0.68, 0.45, 0.7, "wind, dust")
    p.light(0.9, 0.12, "low sun, left of frame is west")
    p.frame_note("WIDE, static, dawn. The floor empty. Nothing moves but dust.")
    out.append(("P1", "The bare threshing floor at dawn", p.done()))

    # P3 The bread bin
    p = Panel(); p.sky((80, 60, 40), (60, 45, 30), 0.0); p.ground((110, 85, 60), 0.0, (70, 55, 40))
    p.prop_rect(0.55, 0.55, 0.75, 0.9, (160, 130, 90))
    p.figure(0.3, 0.95, 150, ELIMELECH, face=1, arms="out")
    p.figure(0.47, 0.95, 140, SONS, face=1)
    p.figure(0.62, 0.95, 130, SONS, face=-1, arms="up")
    p.figure(0.85, 0.93, 150, NAOMI, face=-1)
    p.light(0.1, 0.2, "doorway light from left")
    p.frame_note("MEDIUM, interior. Boys at the bin; Elimelech between; Naomi behind their backs, laughing. The full family.")
    out.append(("P3", "The bread bin: \"House of bread.\" \"Enough.\"", p.done()))

    # P7 The view east
    p = Panel(); p.sky((120, 130, 160), (200, 190, 170), 0.45); p.ground((120, 100, 70), 0.45, (90, 75, 55))
    p.hills((80, 90, 120), [(0.45, 0.45), (0.6, 0.36), (0.8, 0.4), (1, 0.33), (1, 0.45)])
    for i in range(12):
        p.d.line([(0.6 * W + i * 14, 0.1 * H), (0.58 * W + i * 14, 0.36 * H)], fill=(90, 100, 130), width=1)
    p.figure(0.18, 0.98, 170, ELIMELECH, face=1)
    p.arrow(0.3, 0.6, 0.75, 0.42, "east: Moab, rain")
    p.frame_note("WIDE over the shoulder. Elimelech on the ridge, back to us. Rain over Moab across the rift. The dead terraces below.")
    out.append(("P7", "The view east", p.done()))

    # 1.1 Arrival on the threshing floor in Moab
    p = Panel(); p.sky((160, 170, 200), (220, 210, 190), 0.5); p.ground((170, 160, 130), 0.5, (140, 130, 100))
    p.prop_ellipse(0.5, 0.72, 0.4, 0.12, (195, 185, 150))
    for i, x in enumerate((0.72, 0.8, 0.88, 0.95)):
        p.figure(x, 0.92 - 0.02 * i, 110 - 8 * i, MOAB, face=-1)
    p.figure(0.22, 0.95, 130, ELIMELECH, face=1, arms="out")
    p.figure(0.32, 0.95, 120, SONS, face=1)
    p.figure(0.12, 0.93, 120, NAOMI, face=1)
    p.figure(0.4, 0.93, 115, SONS, face=1)
    p.figure(0.62, 0.78, 70, RUTH, face=-1)
    p.figure(0.56, 0.76, 65, ORPAH, face=-1)
    p.arrow(0.25, 0.6, 0.31, 0.6, "hand on Mahlon's chest", (160, 40, 40))
    p.frame_note("WIDE, two groups facing. The family left (they came from the west). Moabites right. Ruth apart, watching the parents.")
    out.append(("1.1", "Arrival on the threshing floor: \"Israelites.\"", p.done()))

    # 1.8 The grave
    p = Panel(); p.sky((200, 190, 170), (230, 220, 200), 0.5); p.ground((130, 110, 80), 0.5, (100, 85, 60))
    p.prop_ellipse(0.5, 0.8, 0.12, 0.05, (90, 70, 50))
    p.figure(0.36, 0.9, 130, NAOMI, face=1)
    p.figure(0.6, 0.9, 125, SONS, face=-1)
    p.figure(0.66, 0.88, 120, SONS, face=-1)
    p.figure(0.93, 0.7, 60, RUTH, face=-1, arms="hold")
    p.frame_note("WIDE, high noon, flat light. Three at the grave and nobody else. Far right, small: Ruth coming with bread.")
    out.append(("1.8", "The grave: nobody comes", p.done()))

    # 1.11 The double wedding
    p = Panel(); p.sky((40, 30, 50), (90, 60, 50), 0.4); p.ground((110, 80, 60), 0.4, (60, 45, 35))
    for i, x in enumerate((0.1, 0.2, 0.75, 0.85, 0.95)):
        p.figure(x, 0.92, 110, MOAB, face=1 if x < 0.5 else -1)
    p.figure(0.5, 0.95, 150, NAOMI, pose="dance", face=1)
    p.figure(0.35, 0.9, 120, RUTH, face=1)
    p.figure(0.63, 0.9, 120, ORPAH, face=-1)
    p.light(0.5, 0.15, "fire from below, warm")
    p.frame_note("MEDIUM WIDE, night, firelight. Naomi dances in the middle of Moab. The last time she's full. Fade to black after.")
    out.append(("1.11", "The double wedding: Naomi dances", p.done()))

    # 1.17 Three graves
    p = Panel(); p.sky((170, 170, 180), (210, 205, 195), 0.5); p.ground((120, 105, 80), 0.5, (90, 80, 60))
    for x in (0.3, 0.5, 0.7):
        p.prop_ellipse(x, 0.68, 0.08, 0.035, (85, 70, 50))
    for i, x in enumerate((0.05, 0.12, 0.88, 0.95)):
        p.figure(x, 0.75, 80, MOAB, face=1 if x < 0.5 else -1)
    p.figure(0.42, 0.97, 150, NAOMI, pose="kneel", face=1)
    p.figure(0.55, 0.97, 150, RUTH, pose="sit", face=-1)
    p.arrow(0.46, 0.75, 0.52, 0.75, "binding the cuts", (160, 40, 40))
    p.frame_note("MEDIUM, low angle. Moab mourns them as kin, at the edges. Centre: Naomi binds Ruth's arms. No words.")
    out.append(("1.17", "Three graves", p.done()))

    # 1.21 The edge: the parting
    p = Panel(); p.sky((140, 150, 180), (220, 200, 170), 0.5); p.ground((150, 130, 95), 0.5, (110, 95, 70))
    p.hills((110, 100, 90), [(0, 0.5), (0.25, 0.4), (0.5, 0.47), (0.75, 0.38), (1, 0.45), (1, 0.5)])
    p.d.line([(0, 0.85 * H), (W, 0.6 * H)], fill=(180, 160, 120), width=6)
    p.figure(0.3, 0.93, 150, NAOMI, face=1, arms="out")
    p.figure(0.5, 0.9, 140, RUTH, face=-1)
    p.figure(0.78, 0.82, 110, ORPAH, face=1)
    p.arrow(0.82, 0.62, 0.95, 0.58, "Orpah back east")
    p.arrow(0.2, 0.62, 0.05, 0.66, "west: home")
    p.frame_note("WIDE then CLOSE. The road at the rift's edge. Orpah going back right; Naomi facing Ruth. The oath; the nod. Wind.")
    out.append(("1.21", "The parting on the road, 1:8-18", p.done()))

    # 1.25 The well by the gate
    p = Panel(); p.sky((200, 200, 210), (235, 225, 205), 0.45); p.ground((175, 160, 125), 0.45, (150, 135, 100))
    p.prop_rect(0.6, 0.2, 0.9, 0.75, (150, 135, 105))
    p.prop_ellipse(0.25, 0.8, 0.1, 0.05, (120, 110, 90))
    for i, x in enumerate((0.45, 0.52, 0.58, 0.66)):
        p.figure(x, 0.85 - 0.01 * i, 95 - 5 * i, TOWN, face=-1)
    p.figure(0.3, 0.98, 160, NAOMI, face=1)
    p.figure(0.2, 0.96, 150, RUTH, face=1)
    p.frame_note("MEDIUM. The town women at the gate; Naomi and Ruth at the well in the foreground, dusty. \"Naomi?\" \"Call me Mara.\" Empty.")
    out.append(("1.25", "The well by the gate: \"Call me Mara\"", p.done()))

    # 2.3 / 2.5 The field
    p = Panel(); p.sky((170, 190, 220), (240, 225, 180), 0.4); p.ground((215, 190, 110), 0.4, (190, 165, 90))
    for i in range(30):
        x = (i * 37) % W
        p.d.line([(x, 0.4 * H + (i * 13) % 40), (x + 3, 0.4 * H + (i * 13) % 40 + 40)], fill=(170, 140, 70), width=2)
    for i, x in enumerate((0.1, 0.22, 0.34, 0.82, 0.92)):
        p.figure(x, 0.8, 90, TOWN, pose="kneel", face=1)
    p.figure(0.62, 0.95, 160, BOAZ, face=-1, arms="out")
    p.figure(0.45, 0.97, 140, RUTH, pose="kneel", face=1)
    p.light(0.1, 0.12, "hard midday light")
    p.frame_note("WIDE to TWO-SHOT. Reapers in a line; Ruth behind them, gleaning; Boaz comes to her. \"Why would you notice me?\"")
    out.append(("2.5", "The field: Boaz and Ruth, 2:8-13", p.done()))

    # 2.6 The meal
    p = Panel(); p.sky((200, 210, 230), (240, 230, 200), 0.35); p.ground((200, 180, 120), 0.35, (170, 150, 95))
    p.prop_rect(0.0, 0.3, 1.0, 0.42, (120, 100, 60))
    for i, x in enumerate((0.1, 0.2, 0.3, 0.8, 0.9)):
        p.figure(x, 0.75, 85, TOWN, pose="sit", face=1)
    p.figure(0.6, 0.95, 150, BOAZ, pose="sit", face=-1, arms="out")
    p.figure(0.42, 0.95, 140, RUTH, pose="sit", face=1, arms="out")
    p.frame_note("MEDIUM, in the shade of the shelter. Roasted grain from his own hand to hers. She eats until she's full. \"You.\"")
    out.append(("2.6", "The meal", p.done()))

    # 3.5 Midnight on the threshing floor
    p = Panel(); p.sky((15, 15, 35), (35, 30, 50), 0.5); p.ground((60, 50, 40), 0.5, (35, 30, 25))
    p.prop_ellipse(0.5, 0.62, 0.4, 0.14, (90, 75, 50))
    p.figure(0.55, 0.9, 150, BOAZ, pose="sit", face=-1, arms="up")
    p.figure(0.32, 0.93, 130, RUTH, pose="kneel", face=1)
    p.light(0.85, 0.12, "moon, high")
    p.frame_note("CLOSE, night, moonlight only. Boaz starts awake; Ruth at his feet. \"Who are you?\" \"Spread your wing...\" An arm's length apart.")
    out.append(("3.5", "Midnight on the threshing floor, 3:8-13", p.done()))

    # 3.8 Empty
    p = Panel(); p.sky((80, 70, 60), (120, 100, 80), 0.3); p.ground((110, 95, 70), 0.3, (70, 60, 45))
    p.prop_rect(0.42, 0.78, 0.58, 0.92, (190, 165, 100))
    p.figure(0.25, 0.97, 160, NAOMI, pose="sit", face=1)
    p.figure(0.72, 0.97, 165, RUTH, face=-1, arms="out")
    p.light(0.95, 0.1, "first light through the door")
    p.frame_note("MEDIUM, dawn in the ruin. Six measures of barley between them. \"He said I shouldn't come back to you empty.\" Naomi sits. \"Wait, my daughter.\"")
    out.append(("3.8", "\"Empty\"", p.done()))

    # 4.1 The gate
    p = Panel(); p.sky((190, 200, 220), (235, 225, 200), 0.4); p.ground((175, 160, 125), 0.4, (150, 135, 100))
    p.prop_rect(0.0, 0.1, 0.18, 0.75, (140, 125, 95))
    p.prop_rect(0.82, 0.1, 1.0, 0.75, (140, 125, 95))
    p.prop_rect(0.2, 0.62, 0.8, 0.68, (120, 105, 80))
    for i, x in enumerate((0.25, 0.33, 0.41, 0.49, 0.57, 0.65, 0.73)):
        p.figure(x, 0.74, 85, TOWN, pose="sit", face=1 if x < 0.5 else -1)
    p.figure(0.38, 0.98, 160, BOAZ, face=1, arms="out")
    p.figure(0.62, 0.98, 160, ELIMELECH, face=-1)
    p.figure(0.72, 0.96, 110, SONS, face=-1)
    p.arrow(0.55, 0.9, 0.45, 0.9, "the sandal", (160, 40, 40))
    p.frame_note("WIDE, the gate, morning. Ten elders on the bench. Boaz and Mr. So-and-so face to face; his son beside him. \"You are witnesses.\"")
    out.append(("4.1", "The gate, 4:1-12", p.done()))

    # 4.6 The naming
    p = Panel(); p.sky((90, 70, 50), (130, 100, 70), 0.0); p.ground((120, 95, 65), 0.0, (80, 65, 45))
    for i, x in enumerate((0.1, 0.2, 0.78, 0.88)):
        p.figure(x, 0.92, 120, TOWN, face=1 if x < 0.5 else -1)
    p.figure(0.5, 0.97, 160, NAOMI, pose="sit", face=1, arms="hold")
    p.figure(0.66, 0.92, 140, RUTH, face=-1)
    p.light(0.1, 0.15, "lamp, warm")
    p.frame_note("MEDIUM CLOSE. The women around Naomi; the child on her lap. She looks up and sees Ruth. \"A son has been born to Naomi!\" She laughs. \"Obed.\"")
    out.append(("4.6", "The naming, 4:14-17", p.done()))

    # 4.7 The roof
    p = Panel(); p.sky((30, 40, 80), (120, 90, 90), 0.5); p.ground((70, 60, 50), 0.5, (40, 35, 30))
    p.hills((50, 60, 100), [(0.5, 0.5), (0.7, 0.42), (0.85, 0.46), (1, 0.4), (1, 0.5)])
    p.figure(0.3, 0.96, 160, NAOMI, pose="sit", face=1, arms="hold")
    p.arrow(0.5, 0.6, 0.8, 0.46, "Moab turning blue")
    p.frame_note("WIDE to EXTREME CLOSE. The roof at dusk; the lullaby with the words; Moab across the rift going blue. The last shot rests on Obed's face.")
    out.append(("4.7", "The roof: the lullaby; Obed's face", p.done()))
    return out


def main():
    ps = panels()
    f = font(12)
    fb = font(13)
    per = 8
    for s in range(0, len(ps), per):
        chunk = ps[s:s + per]
        cols = 2
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (W + PAD) + PAD, rows * (H + 42) + PAD + 30), (250, 248, 243))
        d = ImageDraw.Draw(sheet)
        d.text((PAD, 8), f"Ruth, storyboard sheet {s // per + 1} of 2: blocked compositions from the first-draft script. Figures are placeholders; what's fixed is who stands where, which way they face, and the light.", fill=(40, 40, 40), font=font(11))
        for i, (num, title, im) in enumerate(chunk):
            x = PAD + (i % cols) * (W + PAD)
            y = PAD + 30 + (i // cols) * (H + 42)
            sheet.paste(im, (x, y))
            d.text((x, y + H + 4), f"{num}  {title}", fill=(30, 30, 30), font=f)
        sheet.save(os.path.join(HERE, f"sheet-{s // per + 1}.png"))
        print("wrote", f"sheet-{s // per + 1}.png")


if __name__ == "__main__":
    main()
