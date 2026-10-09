"""A rough photosensitivity check on a rendered video: counts frame-to-frame changes in mean
luminance larger than a threshold, per second, in the two risky stretches (beat 4 and beat 11),
and reports the worst second. This is not IRIS or PEAT and does not replace them (treatment §5).

    python check_flicker.py ../opening-animatic-v2.mp4
"""
import subprocess
import sys

import numpy as np

W, H = 320, 180


def luminance_series(path, t0, t1, fps=24):
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", str(t0), "-t", str(t1 - t0), "-i", path, "-f", "rawvideo",
           "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(fps), "-"]
    raw = subprocess.check_output(cmd)
    n = len(raw) // (W * H)
    frames = np.frombuffer(raw[:n * W * H], np.uint8).reshape(n, H, W).astype(np.float32) / 255
    return frames.mean(axis=(1, 2))


def report(path, name, t0, t1, fps=24):
    lum = luminance_series(path, t0, t1, fps)
    d = np.abs(np.diff(lum))
    # a "flash" here: a whole-frame mean change of more than 10% of full scale (a crude stand-in for
    # the 20 cd/m2 criterion); count per second
    flashes = d > 0.10
    per_sec = [int(flashes[i:i + fps].sum()) for i in range(0, len(flashes), fps)]
    worst = max(per_sec) if per_sec else 0
    print(f"{name}: {t0}-{t1}s  worst second {worst} large changes/s  (guideline: at most 3 flashes/s)  max step {d.max():.2f}")
    return worst


if __name__ == "__main__":
    p = sys.argv[1]
    # times are for the 5:00 cut (treatment v3.2); the 4:50 cut ran ten seconds earlier
    worst = max(report(p, "beat 4", 68, 84), report(p, "beat 11 (the sky falls)", 217, 226), report(p, "beat 2 (the release)", 37, 40))
    print("OK by this crude measure" if worst <= 3 else "WARNING: check with IRIS/PEAT before viewing full screen")
