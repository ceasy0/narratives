"""The AI video tests on one run shot (PLAN §9, item 3): Google's Veo and Runway's Aleph.

The shot is the layout's travelling camera from 04:14:00 to 04:17:12 (SH1320 and the start of
SH1330): the band running left through the forest, the big cat coming up behind them. It's
rendered clean, without the burn-in, by the layout script:

    blender -b --factory-startup -P layout_b12_13.py -- clean=04:14:00-04:17:12

which writes work/aitest/clean-041400-041712.mp4 and its first and last frames. Then, with the
project's Python environment (C:\\Users\\corbi\\AdonaiOpening\\venv\\Scripts\\python.exe):

    python ai_video_test.py check           are the keys set, and what can they reach? (free)
    python ai_video_test.py frames --go     Gemini repaints the first and last frames as live action (a few cents)
    python ai_video_test.py veo --go        Veo 3.1 Fast: a 4 s clip from those two frames and a prompt (about $0.40)
    python ai_video_test.py aleph --go      Aleph: the clean layout clip itself restyled as live action (about $1)

The two tests answer different questions. Veo makes its own shot between a first and a last
frame: it can't follow our camera or timing, only start and end where we say. Aleph keeps the
layout's camera, timing and movement and changes the look. Everything lands in work/aitest/.

The keys come from your environment, never from this file or the chat: GEMINI_API_KEY for
Google, RUNWAYML_API_SECRET for Runway. Without --go nothing is sent and nothing is spent: it
says what it would do and roughly what it would cost.
"""
import base64
import os
import pathlib
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
AITEST = HERE.parent / "work" / "aitest"
TAG = "041400-041712"
CLIP = AITEST / ("clean-%s.mp4" % TAG)
FIRST, LAST = AITEST / ("clean-%s-first.png" % TAG), AITEST / ("clean-%s-last.png" % TAG)
LIVE_FIRST, LIVE_LAST = AITEST / "live-first.png", AITEST / "live-last.png"

LOOK = ("Photorealistic live-action film, shot on 35 mm film with natural morning light: a dense, "
        "green, primeval forest of tall straight trunks, ferns and undergrowth, about 55,000 years "
        "ago in Africa. A small band of early modern humans, men and women, lean and strong, wearing "
        "simple hide wraps, some carrying wooden spears, run hard from right to left through the trees. "
        "Behind them, at the right, a lion-sized big cat bounds after them. No text, no captions.")
REPAINT = ("Repaint this grey 3D layout frame as a single frame of that film. Keep the exact composition, "
           "camera height, lens and framing, and keep every figure exactly where it is, in the same pose and "
           "the same size. The grey stick figures are the people; the grey cones on the ground are ferns and "
           "undergrowth; the balls on tall poles are trees; the dark low shape behind them, if there is one, is "
           "the big cat. " + LOOK)
MOTION = ("The camera tracks alongside them at running speed, a little shaky, at chest height. They never stop. "
          + LOOK)
NEGATIVE = "cartoon, CGI, video game, animation, text, captions, watermark, deformed bodies, extra limbs, nudity"

GO = "--go" in sys.argv


def need(path):
    if not path.exists():
        sys.exit("missing %s: run the step that makes it first (see the top of this file)" % path)


def key(name):
    v = os.environ.get(name)
    if not v:
        sys.exit("%s isn't set in this environment. Set it yourself (see PLAN §9, item 3), then restart "
                 "the app or terminal you run this from, so it sees the new variable." % name)
    return v


def google():
    from google import genai
    return genai.Client(api_key=key("GEMINI_API_KEY"))


def pick(names, wants):
    for w in wants:
        hits = [n for n in names if w in n]
        if hits:
            return sorted(hits)[-1]
    return None


def models():
    c = google()
    names = [m.name.split("/")[-1] for m in c.models.list()]
    image = pick(names, ["gemini-3-pro-image", "gemini-2.5-flash-image", "image"])
    video = pick(names, ["veo-3.1-fast", "veo-3.1", "veo-3"])
    return c, image, video


def check():
    print("GEMINI_API_KEY set:", bool(os.environ.get("GEMINI_API_KEY")))
    print("RUNWAYML_API_SECRET set:", bool(os.environ.get("RUNWAYML_API_SECRET")))
    if os.environ.get("GEMINI_API_KEY"):
        try:
            _, image, video = models()
            print("Google: image model", image, "| video model", video)
        except Exception as e:  # noqa: BLE001
            print("Google: the key didn't work:", e)
    if os.environ.get("RUNWAYML_API_SECRET"):
        try:
            import runwayml
            org = runwayml.RunwayML().organization.retrieve()
            print("Runway: reached; credits", getattr(org, "credit_balance", "?"))
        except Exception as e:  # noqa: BLE001
            print("Runway: the key didn't work:", e)
    for p in (CLIP, FIRST, LAST):
        print("input", p.name, "present" if p.exists() else "MISSING")


def frames():
    need(FIRST), need(LAST)
    print("Gemini repaints the clean first and last frames as live action: 2 images, a few cents.")
    if not GO:
        return print("(not sent: add --go)")
    from google.genai import types
    from PIL import Image
    c, image_model, _ = models()
    for src, dst in ((FIRST, LIVE_FIRST), (LAST, LIVE_LAST)):
        r = c.models.generate_content(model=image_model, contents=[REPAINT, Image.open(src)],
                                      config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
        parts = [p for p in r.candidates[0].content.parts if getattr(p, "inline_data", None)]
        if not parts:
            sys.exit("no image came back for %s: %s" % (src.name, r.text))
        dst.write_bytes(parts[0].inline_data.data)
        print("wrote", dst)


def veo():
    need(LIVE_FIRST), need(LIVE_LAST)
    print("Veo 3.1 Fast, 720p, 4 s, no sound, from live-first.png to live-last.png: about $0.40.")
    if not GO:
        return print("(not sent: add --go)")
    from google.genai import types
    c, _, video_model = models()
    img = lambda p: types.Image(image_bytes=p.read_bytes(), mime_type="image/png")  # noqa: E731
    cfg = dict(aspect_ratio="16:9", resolution="720p", duration_seconds=4, number_of_videos=1,
               last_frame=img(LIVE_LAST), negative_prompt=NEGATIVE, person_generation="allow_adult",
               generate_audio=False)
    try:
        op = c.models.generate_videos(model=video_model, prompt=MOTION, image=img(LIVE_FIRST),
                                      config=types.GenerateVideosConfig(**cfg))
    except Exception as e:  # noqa: BLE001
        if "generate_audio" not in str(e):
            raise
        cfg.pop("generate_audio")                                  # some Veo models always make sound
        op = c.models.generate_videos(model=video_model, prompt=MOTION, image=img(LIVE_FIRST),
                                      config=types.GenerateVideosConfig(**cfg))
    print("sent to", video_model, "; waiting")
    while not op.done:
        time.sleep(10)
        op = c.operations.get(op)
    vids = (op.response.generated_videos if op.response else None) or []
    if not vids:
        sys.exit("no video came back: %s" % (op.error or op.response))
    out = AITEST / ("veo-%s.mp4" % time.strftime("%Y%m%d-%H%M%S"))
    c.files.download(file=vids[0].video)
    vids[0].video.save(str(out))
    print("wrote", out)


def aleph():
    need(CLIP)
    print("Aleph 2 restyles the clean layout clip (about 3.5 s) as live action, 1280x720: about $1.")
    if not GO:
        return print("(not sent: add --go)")
    import runwayml
    c = runwayml.RunwayML(api_key=key("RUNWAYML_API_SECRET"))
    with open(CLIP, "rb") as fh:
        up = c.uploads.create_ephemeral(file=(CLIP.name, fh, "video/mp4"))
    uri = getattr(up, "uri", None) or ("data:video/mp4;base64," + base64.b64encode(CLIP.read_bytes()).decode())
    task = c.video_to_video.create(model="aleph2", video_uri=uri, prompt_text=LOOK, ratio="1280:720")
    print("sent to aleph2; waiting")
    while True:
        time.sleep(10)
        t = c.tasks.retrieve(task.id)
        if t.status in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
    if t.status != "SUCCEEDED":
        sys.exit("Aleph %s: %s" % (t.status, getattr(t, "failure", "") or getattr(t, "failure_code", "")))
    out = AITEST / ("aleph-%s.mp4" % time.strftime("%Y%m%d-%H%M%S"))
    urllib.request.urlretrieve(t.output[0], out)
    print("wrote", out)


if __name__ == "__main__":
    AITEST.mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    {"check": check, "frames": frames, "veo": veo, "aleph": aleph}[cmd]()
