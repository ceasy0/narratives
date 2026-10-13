# The Opening — production

> The visualization of Genesis 1:1–2:7. As of 2026-10-13: an animatic of the whole 5:00 (v3.1), rendered in code with a generated soundtrack, cut to [treatment v3.4](../../story/arcs/01-beginnings/opening/TREATMENT.md)'s timings and [script v1.3](../../scripts/beginnings/opening.fountain)'s shots. **How the finished Opening gets made** is [PLAN.md](./PLAN.md) (2026-10-13, your request): the honest answer on quality, the pipeline, the face without a scan, the tempo map, the costs and the handoff for the sound. The tools behind it, with sources, are in [TOOLS.md](./TOOLS.md); the look, with pictures, is in [REFERENCES.md](./REFERENCES.md).

**v3.1 (2026-10-13):** your notes on v3 of 2026-10-13 and the code bugs the [audit](../../AUDIT.md) found. The leaf falls slowly now, rocking for four seconds, and lies still for two, until the tribe's feet whip it up and away with the dust. Beat 11's impact is on screen for the first time, inside 3:18–3:42: the glow on the horizon, the quake, the creature's run and the sky falling, whose last fire is still coming down as beat 12 opens. The star's roar now drops away instead of playing under beats 10 and 11; the falling sky's whistles fire; beat 1's flow starts at 0:14; beat 4's faces dissolve on the script's time; the beat 9 cell lights in its beat; the release's tail is out of the silence before the note. Nothing else moved. **The sound is now a separate layer** (your decision, 2026-10-13): you make it in FL Studio and lay it over the finished picture; the animatic's generated sound stays only as a guide ([PLAN §8](./PLAN.md#8-the-sound-handoff)).

**v3 (2026-10-09):** your notes on v2 applied. No timing moved. The face is now a real human face mesh with the four-face rule's expressions; the static is sand pouring over the face as it rises, so the eyes, nose and mouth read; the fade starts on frame 0; the release has six layers and its own space; the held note no longer wobbles (v2's vibrato grew the longer it held: a bug); the large face forms off to the side; the turn-overs are fronts of light; the faces break up into the grains; the first colors are sparks of light with a soap-film sheen; beat 5 falls into the Mandelbrot set's boundary; the gas grows into a cosmic web and the stars light at its knots. Everything sits in one reverb space. v2 (5:00, with the fade) and v1 (4:50) are still in the folder until you say to remove them; v3 is in the git history.

**Watch:** [`opening-animatic-v3.1.mp4`](./opening-animatic-v3.1.mp4) (5:00, 854×480, 24 fps, stereo: the repository copy, re-encoded small because the grain beats don't compress). **Build it:** `py animatic/build.py` (needs Python 3.10+, numpy, Pillow, ffmpeg). v3 is slower than v2 (the face mesh, the sand and the web); on the cloud machine's four processes the full render takes over an hour, so on your desktop expect longer. The render goes in ten-second parts kept in `animatic/out/video-silent.mp4.parts/`, so if it's stopped, running the build again picks up where it left off (delete that folder after changing the code). For anything but a full rebuild, render the changed seconds alone with `py animatic/render.py --video part.mp4 --start A --end B`. The build also writes the full-quality 960×540 file and the sound stems to `animatic/out/`, kept out of git.

---

## 1. What this is, and isn't

You asked for the full animation of the Opening (2026-10-08). v3.1 is the latest complete pass of it: every one of the fourteen beats, in order, at the treatment's exact timings, with sound, so the whole sequence can be watched and judged for pace before anything expensive is made. That's the dossier's step 1 ("a timed storyboard of the whole sequence, with a rough soundtrack"), done as moving pictures rather than stills, with steps 2 and 3 started in the same code.

It isn't the finished animation, and it won't be made into it by fixing notes one at a time; [PLAN §1](./PLAN.md#1-the-honest-answer) says why, and how the finished one gets made. Three things are placeholders by necessity, because it's made in code without Blender, a real face or FL Studio:

| Placeholder | What it is now | What replaces it |
|---|---|---|
| **The face** (beats 1–4, 14) | Since v3, a real human face: MediaPipe's canonical face mesh (`animatic/facemesh.py`, Apache 2.0), deformed for the four-face rule's expressions and lit in code. It reads as a human face, but it's anyone's face, and it has no skin. | A realistic face without a scan (your preference, 2026-10-13): MetaHuman first, then the fallbacks, driven by your webcam performance if you're willing ([PLAN §5](./PLAN.md#5-the-face-without-a-scan)), in Blender. `FaceMesh.render` is the one function to swap. |
| **The world** (beats 10–14) | Flat silhouettes and gradients: cells, the swimmer, the fish, the great creature, the shore, the night, the *Triceratops*, the tree, the band, the delta. The face at the cliff is the mesh. Staging, direction and timing are real; the look isn't. | Blender for the layout, and AI video for the living bodies in a live-action look ([PLAN §4](./PLAN.md#4-beat-by-beat); the look is PLAN §9's first question). |
| **The sound** | Ten stems generated from the treatment's rules (`animatic/sound.py`): the hiss (wind, sand, swell), the whisper, the release (six layers), the held note, the atmospheres, the laugh, the grains, the cosmos, the world, and one shared reverb space. Better than v2, still synthesized. | Your FL Studio score and sound, made as a separate layer over the locked picture ([PLAN §8](./PLAN.md#8-the-sound-handoff): the cue sheet, the guide stems, the held note's pitches). The stems are written as 48 kHz stereo WAVs into `animatic/out/audio/` when you build. |

What's *not* placeholder: the timings, the staging, the direction of every movement (the band always left), the four-face rule, the alternation's safety design, the pair sea's tie between picture and sound, and the structure of the code, which is the structure of the build.

## 2. What to look at first

1. **The sand over the face (0:00–0:38).** Can you see the eyes, nose and mouth without being told, and is the face human enough? The sand is `sand_field` in `beats_abstract.py`; the relief it flows over is `relief`.
2. **The release (0:38).** Two frames of pressed sand, the streak inward, the white face; six layers of sound under it. Is it the strike now, and is it atmospheric enough?
3. **The held note.** It should now be steady, a slight shimmer and no wobble. Say if any of it still sounds like the 1980s.
4. **Beat 3 (0:46–1:08).** The large face off to the right, turned toward the small one; the front of light at the turn (0:58:12).
5. **Beat 4 and 5 (1:08–1:44).** Do the faces break into the grains now, rather than sitting under them? Are the first colors flashes of light? Is the fractal behind the pair sea the right idea?
6. **Pacing.** v3.1 slows the leaf (3:54–4:00) and lets the feet whip it away at 4:00. For the rest, the tempo map in [PLAN §6](./PLAN.md#6-pacing-the-tempo-map) measures how much each beat moves and asks you to mark where it's wrong.

## 3. The code

All in `animatic/`. Pure functions of time, so frames render in any order and in parallel, and every change is a number.

| File | What it does |
|---|---|
| `common.py` | Grids in normalized coordinates, value noise, curl flow, Worley noise (and its third-nearest form, for the web's knots), the Mandelbrot glow, cosine palettes, shapes, blur, color, point splatting |
| `facemesh.py` | **New in v3.** The face: MediaPipe's canonical mesh (`data/canonical_face_model.obj`, Apache 2.0) sampled as a dense point cloud with a head behind it, deformed for brows, eyes, mouth and jaw, splatted with a depth buffer; depth, normals, masks, eyes, irises and mouth out; lighting helpers |
| `face.py` | v2's procedural face; v3 keeps its eight named expressions and a few helpers |
| `beats_abstract.py` | Beats 1–9: the deep (sand over the face), light, the separation, evening and morning (fronts, grains, sparks), the vault (the pair sea and the fractal), land and seas, the earth brings forth (the cosmic web), lights (stars at the web's knots, the star's interior), the crossing |
| `beats_world.py` | Beats 10–14: the waters swarm, the land, dust, fill the earth, rest. Silhouettes via Pillow. |
| `sound.py` | The stems, the shared reverb space, the mix and the WAV writer. The pair sea's blips, the flips' ticks and the stars' ignitions come from the same event lists the picture uses. |
| `render.py` | The frame loop: `--preview 10 30 45` writes PNGs at those seconds; `--video out.mp4 --procs 4` renders slices in parallel through ffmpeg and concatenates them |
| `build.py` | Frames, soundtrack, mux: one command |

**To change a timing:** edit the beat boundaries `B` at the top of `beats_abstract.py` (they're the treatment's table) and the sub-timings inside the beat's function, then rebuild. **To preview a change:** `py animatic/render.py --preview 54 57.5 59 --out preview` (from this folder; inside `animatic/` it's `py render.py`) and look at the PNGs. On this machine the command is `py`, not `python` (dossier §6).

## 4. Safety

Beat 4's flicker and beat 11's falling sky are designed to the rules in [treatment §5](../../story/arcs/01-beginnings/opening/TREATMENT.md#5-whats-mine-and-the-open-problems): only the first three turns take the whole frame (never more than three a second), the spread is organic, and the grains turn out of step so the frame's brightness holds. A rough check on the rendered frames (mean luminance change per frame in beats 2, 4 and 11) is printed by `py animatic/check_flicker.py <video>`; v3.1 passes it, as v1, v2 and v3 did (v3.1's worst second: three large changes in beat 4, at the whole-frame turns; none in beat 11, where the falling sky is now on screen; one at the release). **Before anyone watches it full screen, run the finished render through IRIS or PEAT**, as the treatment requires; this animatic has not had that check.

## 5. Next

The order, and why, is in [PLAN §10](./PLAN.md#10-order-of-work). In short: your answers to [PLAN §9](./PLAN.md#9-what-i-need-from-you), then a session on your desktop that sets up the working folder and the master edit, tests the face, and builds the layout of one beat (12 into 13, the leaf and the run) as the proof of the method; then the layout of all fourteen beats, cut together and judged as a whole before anything is rendered at quality.
