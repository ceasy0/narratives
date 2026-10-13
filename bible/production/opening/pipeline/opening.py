"""Shared paths, timecodes and the shot list for the Opening's Blender scripts.

Frames are film frames: frame 0 is the first frame of the Opening, 24 a second,
so 03:42:00 is frame 5328 in every scene and in the master edit.
"""
import csv
import pathlib

FPS = 24
TOTAL = 300 * FPS

HERE = pathlib.Path(__file__).resolve().parent
OPENING = HERE.parent                         # bible/production/opening
WORK = OPENING / "work"                       # big files, on H, out of git
EDIT = WORK / "edit"
LAYOUT = WORK / "layout"
PLAYBLAST = WORK / "playblast"
LOCAL = pathlib.Path(r"C:\Users\corbi\AdonaiOpening\blender")   # caches, on the PC
ANIMATIC = OPENING / "opening-animatic-v3.1.mp4"
MASTER = EDIT / "opening-master.blend"


def frame(tc):
    """'mm:ss' or 'mm:ss:ff' -> film frame."""
    p = [int(x) for x in tc.split(":")]
    return (p[0] * 60 + p[1]) * FPS + (p[2] if len(p) > 2 else 0)


def timecode(f):
    return "%02d:%02d:%02d" % (f // (60 * FPS), f // FPS % 60, f % FPS)


def shots():
    """The shot list as dicts: shot, beat, start, end (frames, end exclusive), what."""
    out = []
    with open(HERE / "shots.csv", newline="", encoding="utf-8") as h:
        for r in csv.DictReader(h):
            out.append({"shot": r["shot"], "beat": int(r["beat"]), "start": frame(r["start"]),
                        "end": frame(r["end"]), "what": r["what"]})
    for a, b in zip(out, out[1:]):
        assert a["end"] == b["start"], "gap or overlap after shot " + a["shot"]
    assert out[0]["start"] == 0 and out[-1]["end"] == TOTAL
    return out
