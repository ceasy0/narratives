# The Opening — production

> The visualization of Genesis 1:1–2:7: an animatic of the whole 5:00, rendered in code with a generated soundtrack, cut to the [treatment](../../story/arcs/01-beginnings/opening/TREATMENT.md)'s timings and the [script](../../scripts/beginnings/opening.fountain)'s shots. **How the finished Opening gets made** is [PLAN.md](./PLAN.md); the tools behind it, with sources, are in [TOOLS.md](./TOOLS.md); the look, beat by beat, is in [REFERENCES.md](./REFERENCES.md).

**Status:** animatic v3.1, 2026-10-13. It's the timing reference until the layout pass replaces it ([PLAN §3](./PLAN.md#3-the-pipeline)), except beats 12 and 13, which the layout now runs nine and six seconds longer, so the Opening is 5:15 and the animatic's 5:00 ([PLAN §9](./PLAN.md#9-what-i-need-from-you)). Its sound is a guide only: yours is made in FL Studio and laid over the locked picture ([PLAN §8](./PLAN.md#8-the-sound-handoff)). v2 (5:00) and v1 (4:50) are still in the folder until you say to remove them; v3 and every earlier state are in the git history.

**Watch:** [`opening-animatic-v3.1.mp4`](./opening-animatic-v3.1.mp4) (5:00, 854×480, 24 fps, stereo: the repository copy, re-encoded small because the grain beats don't compress). **Build it:** `py animatic/build.py` (needs Python 3.10+, numpy, Pillow, ffmpeg). On the cloud machine's four processes the full render takes over an hour, so on your desktop expect longer. The render goes in ten-second parts kept in `animatic/out/video-silent.mp4.parts/`, so if it's stopped, running the build again picks up where it left off (delete that folder after changing the code). For anything but a full rebuild, render the changed seconds alone with `py animatic/render.py --video part.mp4 --start A --end B`. The build also writes the full-quality 960×540 file and the sound stems to `animatic/out/`, kept out of git.

---

## 1. What this is, and isn't

You asked for the full animation of the Opening (2026-10-08). This is a complete pass of it: every one of the fourteen beats, in order, at the treatment's exact timings, with sound, so the whole sequence can be watched and judged for pace before anything expensive is made. That's the dossier's step 1 ("a timed storyboard of the whole sequence, with a rough soundtrack"), done as moving pictures rather than stills, with steps 2 and 3 started in the same code.

It isn't the finished animation, and it won't be made into it by fixing notes one at a time; [PLAN §1](./PLAN.md#1-the-honest-answer) says why, and how the finished one gets made. Three things are placeholders by necessity, because it's made in code without Blender, a real face or FL Studio:

| Placeholder | What it is now | What replaces it |
|---|---|---|
| **The face** (beats 1–4, 14) | A real human face: MediaPipe's canonical face mesh (`animatic/facemesh.py`, Apache 2.0), deformed for the four-face rule's expressions and lit in code. It reads as a human face, but it's anyone's face, and it has no skin. | A realistic face without a scan (your preference, 2026-10-13): MetaHuman first, then the fallbacks (your own face, from photos, among them), with the expressions keyed in software ([PLAN §5](./PLAN.md#5-the-face-without-a-scan)), in Blender. `FaceMesh.render` is the one function to swap. |
| **The world** (beats 10–14) | Flat silhouettes and gradients: cells, the swimmer, the fish, the great creature, the shore, the night, the *Triceratops*, the tree, the band, the delta. The face at the cliff is the mesh. Staging, direction and timing are real; the look isn't. | Blender for the layout, and AI video for the living bodies in a live-action look ([PLAN §4](./PLAN.md#4-beat-by-beat); *Arcane* if the live-action look can't be done). |
| **The sound** | Ten stems generated from the treatment's rules (`animatic/sound.py`): the hiss (wind, sand, swell), the whisper, the release (six layers), the held note, the atmospheres, the laugh, the grains, the cosmos, the world, and one shared reverb space. Still synthesized. | Your FL Studio score and sound, made as a separate layer over the locked picture ([PLAN §8](./PLAN.md#8-the-sound-handoff): the cue sheet, the guide stems, the held note's pitches). The stems are written as 48 kHz stereo WAVs into `animatic/out/audio/` when you build. |

What's *not* placeholder: the timings, the staging, the direction of every movement (the band always left), the four-face rule, the alternation's safety design, the pair sea's tie between picture and sound, and the structure of the code, which is the structure of the build.

## 2. What's in it

- **The deep (0:00–0:38):** sand pouring over a face that rises under it, read by how the grains run around its contours; the fade from black from frame 0. `sand_field` and `relief` in `beats_abstract.py`.
- **The release (0:38):** two frames of pressed sand, the streak inward, the white face, six layers of sound in one reverb space, then silence and the held note (steady, no vibrato).
- **Beats 3–5 (0:46–1:44):** the large face off to the side; turn-overs as fronts of light; the faces breaking into the grains; sparks of colored light with a soap-film sheen; the fall into the Mandelbrot set's boundary.
- **Beats 6–9 (1:44–2:46):** the proton and the atom; the gas growing into a cosmic web, stars lighting at its knots; the fall into the star; the photon's crossing to the cell.
- **Beats 10–14 (2:46–5:00):** silhouettes and gradients. Beat 11's impact (the glow, the quake, the sky falling) is inside 3:18–3:42. The leaf falls slowly from 3:54, lies still for two seconds, and the feet whip it away at 4:00.

How much each beat moves, and what it should feel like, is the tempo map in [PLAN §6](./PLAN.md#6-pacing-the-tempo-map).

## 3. The code

All in `animatic/`. Pure functions of time, so frames render in any order and in parallel, and every change is a number.

| File | What it does |
|---|---|
| `common.py` | Grids in normalized coordinates, value noise, curl flow, Worley noise (and its third-nearest form, for the web's knots), the Mandelbrot glow, cosine palettes, shapes, blur, color, point splatting |
| `facemesh.py` | The face: MediaPipe's canonical mesh (`data/canonical_face_model.obj`, Apache 2.0) sampled as a dense point cloud with a head behind it, deformed for brows, eyes, mouth and jaw, splatted with a depth buffer; depth, normals, masks, eyes, irises and mouth out; lighting helpers |
| `face.py` | The earlier procedural face; its eight named expressions and a few helpers are still used |
| `beats_abstract.py` | Beats 1–9: the deep (sand over the face), light, the separation, evening and morning (fronts, grains, sparks), the vault (the pair sea and the fractal), land and seas, the earth brings forth (the cosmic web), lights (stars at the web's knots, the star's interior), the crossing |
| `beats_world.py` | Beats 10–14: the waters swarm, the land, dust, fill the earth, rest. Silhouettes via Pillow. |
| `sound.py` | The stems, the shared reverb space, the mix and the WAV writer. The pair sea's blips, the flips' ticks and the stars' ignitions come from the same event lists the picture uses. |
| `render.py` | The frame loop: `--preview 10 30 45` writes PNGs at those seconds; `--video out.mp4 --procs 4` renders slices in parallel through ffmpeg and concatenates them |
| `build.py` | Frames, soundtrack, mux: one command |

**To change a timing:** edit the beat boundaries `B` at the top of `beats_abstract.py` (they're the treatment's table) and the sub-timings inside the beat's function, then rebuild. **To preview a change:** `py animatic/render.py --preview 54 57.5 59 --out preview` (from this folder; inside `animatic/` it's `py render.py`) and look at the PNGs. On this machine the command is `py`, not `python` (dossier §6).

## 4. Safety

Beat 4's flicker and beat 11's falling sky are designed to the rules in [treatment §4](../../story/arcs/01-beginnings/opening/TREATMENT.md#4-whats-mine-and-the-open-problems): only the first three turns take the whole frame (never more than three a second), the spread is organic, and the grains turn out of step so the frame's brightness holds. A rough check on the rendered frames (mean luminance change per frame in beats 2, 4 and 11) is printed by `py animatic/check_flicker.py <video>`; v3.1 passes it (its worst second: three large changes in beat 4, at the whole-frame turns; none in beat 11, where the falling sky is now on screen; one at the release). **Before anyone watches it full screen, run the finished render through IRIS or PEAT**, as the treatment requires; this animatic has not had that check.

## 5. The layout pipeline

The scripts in [`pipeline/`](./pipeline/) build the master edit and the layouts in Blender, on your desktop. Blender is at `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe` (it isn't on the PATH); run each as `blender -b --factory-startup -P <script>` from this folder. Everything they write goes to `work/`, which git ignores.

| File | What it does |
|---|---|
| `pipeline/shots.csv` | The cut list: 79 shots with their timecodes, from the script. Shot 1250 is beat 12's fifth shot. |
| `pipeline/opening.py` | Shared paths, timecodes and the shot list. Frames are film frames: 03:42:00 is frame 5328 everywhere. |
| `pipeline/master_edit.py` | Builds `work/edit/opening-master.blend`: one strip per shot cut from the v3.1 animatic (channel 1), every layout playblast in `work/playblast/` at its timecode (channel 2), the guide sound (channel 5), a marker at each beat. Run it again after any new playblast. |
| `pipeline/layout_b12_13.py` | Builds the grey layout of beats 12–13 (`work/layout/b12-13-layout.blend`) and, with `-- render`, its playblast (`work/playblast/1200-1395-layout.mp4`, six minutes to render). Every placement, lens and speed is a number at the top. `-- still=03:59:00,04:00:04` renders single frames instead. |
| `pipeline/lookdev_leaf.py` | The first look test: opens the layout of beats 12–13 and takes the leaf shot (SH1250) from grey to a lit picture: procedural materials, sun and haze, ferns, leaf litter, a cloth leaf. Writes three 1080p stills to `work/lookdev/`, and with `-- clip` a four-second clip. It was for the live-action look, and is kept as a record of EEVEE's speed on your card. |
| `pipeline/ai_video_test.py` | The AI video tests on one run shot, with the project's Python: Aleph restyles the clean layout clip as live action; Gemini repaints its first and last frames and Veo makes a clip between them. Keys from your environment; nothing is sent without `--go`. Out of the plan since the painted look ([PLAN §2](./PLAN.md#2-the-machine-and-the-tools)). |
| `pipeline/humans.py` | People: MPFB2 bodies (CC0), rigged and moved by CMU motion capture along any path and over any ground, feet held by two-bone IK, in hide wraps cut from MPFB's fitting shells. Imported by the run tests. |
| `pipeline/forest.py` | The scanned forest for the realistic test of the run, from Poly Haven's CC0 assets. Made for flat ground, before the layout's ground rolled. |
| `pipeline/band_mocap_test.py` | The run, 04:15:00–04:18:12, the layout's paths on motion-captured bodies: a quick EEVEE look (`work/aitest/`); `-- real`, the realistic test in Cycles; `-- painted`, the style test in the series' painted look, the people baked, painted with `brush.py` and lit live as the face is, the forest painted by shader (`work/styletest/run-041500-041812.mp4` and its sheet; `-- painted still` one frame; `-- painted reuse` from the paint already made). |
| `pipeline/painted.py` | The series' painted look ([Discussion 006](../../discussions/006-2d-or-3d.md), round 4): painted materials, the outline, a painted sky, the haze and brush filter over the frame, the finishing look (glow, grade, vignette, a lens's colour fringing, moving grain), and the characters' method shared by the face and the run: a surface's colour and occlusion baked into its own texture for `brush.py`, and the paint lit live, the renderer's light turned into the painter's colours. Imported by the style tests. |
| `pipeline/face_test.py` | The face in the painted look, after your photos (`work/face/`): the head given definition in its forms and built in planes, hair grown in locks and lit as one mass, the colour and creases baked into its textures and painted over by `brush.py`, and lit live, the sun through a window, its light turned into the painter's colours (`-- baked`: the light painted in instead); a front view and two three-quarter stills, and four seconds of the breath, with the whole look on (`work/styletest/`); `-- reuse` renders from the paint already made, `-- check` renders grey front and side views to set the shape ([PLAN §9](./PLAN.md#9-what-i-need-from-you), item 3). |
| `pipeline/brush.py` | Paints a baked texture with real brush strokes (Hertzmann's method): big brushes then small, each stroke a curve along the form, the creases accented, the lips' edges, the brows full, the lids smooth, the hair painted along its strands with strands drawn over it, and the face's marks and line accents laid over the paint. Run by `face_test.py` and `band_mocap_test.py` with the system Python. |
| `pipeline/woodcut.py` | The woodcut look of beats 1–4, after Nash's *Genesis* ([PLAN §4](./PLAN.md#4-beat-by-beat)): the sheet of sand with the face rising through it, the two exact passes Cycles renders (where each point lies among the cuts, and the light on it), the cut made from them in numpy, and the flash check. Imported by the two below. |
| `pipeline/woodcut_test.py` | The look's style test: two seconds of beat 1 at about 0:26 and a still, beside Nash's two prints (`work/woodcut/`). |
| `pipeline/beat1.py` | Beat 1 and the release, 0:00–0:42, in the woodcut look: `-- frames A B` renders film frames (several workers at once, one able to take the end of another's range), `-- assemble` makes `work/beat1/beat1-0000-1007.mp4` and its flash report, `-- keys` and `-- check TC` show the timeline small or a frame at full size; `half` with any of them works at 960 × 540 in `work/beat1/half/`, four times as fast, for a test. |

To look yourself: open `work/layout/b12-13-layout.blend`, press Numpad 0 for the camera, and scrub; the markers switch the camera at each shot. Open `work/edit/opening-master.blend` in the Video Editing workspace to see it in the cut.

## 6. Next

The order, and why, is in [PLAN §10](./PLAN.md#10-order-of-work). In short: your notes on the twelfth pass of the first layout, beats 12 into 13 ([PLAN §9](./PLAN.md#9-what-i-need-from-you)), then the face test once the story reel is right; then the layout of all fourteen beats, cut together and judged as a whole before anything is rendered at quality.
