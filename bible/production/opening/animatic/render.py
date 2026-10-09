"""Frame renderer for the Opening animatic.

    python render.py --preview 10 30 45            # PNGs of single frames at those seconds
    python render.py --video out.mp4 --w 960 --h 540 --fps 24 --procs 4
    python render.py --video out.mp4 --start 0 --end 30   # a slice

The video path renders in parallel: each process renders a slice of time to its own silent mp4
through an ffmpeg pipe; the slices are then concatenated. build.py adds the soundtrack.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import Grid, FPS, DURATION, to_uint8, vignette  # noqa: E402
import beats_abstract as A  # noqa: E402
import beats_world as Wd  # noqa: E402

B = A.B

SCHEDULE = [
    ("deep", B["deep"], B["light"], A.beat_deep),
    ("light", B["light"], B["sep"], A.beat_light),
    ("sep", B["sep"], B["eve"], A.beat_sep),
    ("eve", B["eve"], B["vault"], A.beat_eve),
    ("vault", B["vault"], B["land"], A.beat_vault),
    ("land", B["land"], B["earth"], A.beat_land),
    ("earth", B["earth"], B["lights"], A.beat_earth),
    ("lights", B["lights"], B["cross"], A.beat_lights),
    ("cross", B["cross"], B["swarm"], A.beat_cross),
    ("swarm", B["swarm"], B["landbeat"], Wd.beat_swarm),
    ("landbeat", B["landbeat"], B["dust"], Wd.beat_land),
    ("dust", B["dust"], B["fill"], Wd.beat_dust),
    ("fill", B["fill"], B["rest"], Wd.beat_fill),
    ("rest", B["rest"], B["end"], Wd.beat_rest),
]


def beat_at(t):
    for name, t0, t1, fn in SCHEDULE:
        if t0 <= t < t1:
            return name, fn
    return SCHEDULE[-1][0], SCHEDULE[-1][3]


class Renderer:
    def __init__(self, w, h):
        self.g = Grid(w, h)
        self.ctx = A.Ctx(self.g)
        self.wctx = Wd.WCtx(self.g, self.ctx)
        self.vig = vignette(self.g, 0.25, 2.5)

    def frame(self, t):
        name, fn = beat_at(t)
        if fn.__module__ == "beats_world":
            img = fn(self.wctx, t)
        else:
            img = fn(self.ctx, t)
        img = np.clip(img, 0, 1)
        # a gentle vignette through the abstract beats, none once the world is ordinary
        if t < B["swarm"]:
            img = img * self.vig[..., None]
        return to_uint8(img)


def render_slice(args):
    w, h, fps, t0, t1, path = args
    R = Renderer(w, h)
    n0 = int(round(t0 * fps))
    n1 = int(round(t1 * fps))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-f", "mp4", path + ".tmp"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t_start = time.time()
    for n in range(n0, n1):
        t = n / fps
        fr = R.frame(t)
        p.stdin.write(fr.tobytes())
        if (n - n0) % 240 == 0:
            el = time.time() - t_start
            done = n - n0 + 1
            print(f"[{os.getpid()}] {t:7.2f}s  {done}/{n1 - n0} frames  {el / done * 1000:.0f} ms/frame", flush=True)
    p.stdin.close()
    p.wait()
    os.replace(path + ".tmp", path)  # a finished part only ever exists complete, so a stopped render resumes
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", nargs="*", type=float)
    ap.add_argument("--out", default="preview")
    ap.add_argument("--video")
    ap.add_argument("--w", type=int, default=960)
    ap.add_argument("--h", type=int, default=540)
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=DURATION)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--chunk", type=float, default=10.0)
    a = ap.parse_args()

    if a.preview is not None:
        from PIL import Image
        os.makedirs(a.out, exist_ok=True)
        R = Renderer(a.w, a.h)
        for t in a.preview:
            t0 = time.time()
            fr = R.frame(t)
            Image.fromarray(fr).save(os.path.join(a.out, f"t{t:07.2f}.png"))
            print(f"{t:7.2f}s  {beat_at(t)[0]:9s} {(time.time() - t0) * 1000:.0f} ms")
        return

    if a.video:
        from multiprocessing import Pool
        tmpdir = a.video + ".parts"
        os.makedirs(tmpdir, exist_ok=True)
        n = a.procs
        # ten-second parts, so a stopped render picks up where it left off: finished parts are kept
        # (delete the .parts folder after changing the code, or the old parts are reused)
        edges = np.arange(a.start, a.end, a.chunk).tolist() + [a.end]
        jobs = [(a.w, a.h, a.fps, float(edges[i]), float(edges[i + 1]),
                 os.path.join(tmpdir, f"part{a.w}x{a.h}-{edges[i]:07.2f}.mp4")) for i in range(len(edges) - 1)]
        parts = [j[-1] for j in jobs]
        todo = [j for j in jobs if not os.path.exists(j[-1])]
        print(f"{len(jobs) - len(todo)} of {len(jobs)} parts already rendered", flush=True)
        t0 = time.time()
        with Pool(n) as pool:
            # the slow beats first, so the processes finish together
            for _ in pool.imap_unordered(render_slice, todo[::-1]):
                pass
        lst = os.path.join(tmpdir, "list.txt")
        with open(lst, "w") as f:
            for p in parts:
                f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", a.video])
        print(f"rendered {a.video} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
