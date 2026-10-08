"""Build the Opening animatic end to end: frames (in parallel), the soundtrack, and the mux.

    python build.py                       # 960x540, 24 fps, 4 processes -> ../opening-animatic-v1.mp4
    python build.py --w 1920 --h 1080     # full HD (about four times the render time)
    python build.py --audio-only          # regenerate the soundtrack and remux

Needs: Python 3.10+, numpy, Pillow, and ffmpeg on the PATH. Nothing else.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, default=960)
    ap.add_argument("--h", type=int, default=540)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "opening-animatic-v1.mp4"))
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--no-stems", action="store_true")
    a = ap.parse_args()

    work = os.path.join(HERE, "out")
    os.makedirs(work, exist_ok=True)
    silent = os.path.join(work, "video-silent.mp4")
    t0 = time.time()
    if not a.audio_only:
        subprocess.check_call([sys.executable, os.path.join(HERE, "render.py"), "--video", silent, "--w", str(a.w), "--h", str(a.h),
                               "--fps", str(a.fps), "--procs", str(a.procs)])
        print(f"video done in {time.time() - t0:.0f} s", flush=True)
    import sound
    mix = sound.build(os.path.join(work, "audio"), write_stems=not a.no_stems)
    print(f"audio done at {time.time() - t0:.0f} s", flush=True)
    final = os.path.abspath(a.out)
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", mix, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                           "-shortest", "-movflags", "+faststart", final])
    print(f"wrote {final} ({os.path.getsize(final) / 1e6:.1f} MB) in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
