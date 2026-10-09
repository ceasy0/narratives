# The Opening — production

> The visualization of Genesis 1:1–2:7. As of 2026-10-09: an animatic of the whole 5:00 (v3), rendered in code with a generated soundtrack, cut to [treatment v3.3](../../story/arcs/01-beginnings/opening/TREATMENT.md)'s timings and [script v1.2](../../scripts/beginnings/opening.fountain)'s shots. How far past this the finished film can go, and with which tools, is in [ASSESSMENT.md](./ASSESSMENT.md), with the brief for the sound in FL Studio.

**v3 (2026-10-09):** your notes on v2 applied. No timing moved. The face is now a real human face mesh with the four-face rule's expressions; the static is sand pouring over the face as it rises, so the eyes, nose and mouth read; the fade starts on frame 0; the release has six layers and its own space; the held note no longer wobbles (v2's vibrato grew the longer it held: a bug); the large face forms off to the side; the turn-overs are fronts of light; the faces break up into the grains; the first colors are sparks of light with a soap-film sheen; beat 5 falls into the Mandelbrot set's boundary; the gas grows into a cosmic web and the stars light at its knots. Everything sits in one reverb space. v2 (5:00, with the fade) and v1 (4:50) are still in the folder until you say to remove them, and in the git history either way.

**Watch:** [`opening-animatic-v3.mp4`](./opening-animatic-v3.mp4) (5:00, 854×480, 24 fps, stereo: the repository copy, re-encoded small because the grain beats don't compress). **Build it:** `py animatic/build.py` (needs Python 3.10+, numpy, Pillow, ffmpeg). v3 is slower than v2 (the face mesh, the sand and the web); on the cloud machine's four processes the full render took over an hour, so on your desktop expect longer. For anything but a full rebuild, render the changed seconds alone with `py animatic/render.py --video part.mp4 --start A --end B`. The build also writes the full-quality 960×540 file and the sound stems to `animatic/out/`, kept out of git.

---

## 1. What this is, and isn't

You asked for the full animation of the Opening (2026-10-08). This is the first complete pass of it: every one of the fourteen beats, in order, at the treatment's exact timings, with sound, so the whole sequence can be watched and judged for pace before anything expensive is made. That's the dossier's step 1 ("a timed storyboard of the whole sequence, with a rough soundtrack"), done as moving pictures rather than stills, with steps 2 and 3 started in the same code.

It isn't the finished animation. Three things are placeholders by necessity, because it's made in code without the face shoot, Blender or FL Studio:

| Placeholder | What it is now | What replaces it |
|---|---|---|
| **The face** (beats 1–4, 14) | Since v3, a real human face: MediaPipe's canonical face mesh (`animatic/facemesh.py`, Apache 2.0), deformed for the four-face rule's expressions and lit in code. It reads as a human face, but it's anyone's face, and it has no skin. | Your face, scanned or filmed (README item 7; [ASSESSMENT §3](./ASSESSMENT.md#3-what-it-would-take-on-your-desktop)), in Blender. `FaceMesh.render` is the one function to swap. |
| **The world** (beats 10–14) | Flat silhouettes and gradients: cells, the swimmer, the fish, the great creature, the shore, the night, the *Triceratops*, the tree, the band, the delta. The face at the cliff is the mesh. Staging, direction and timing are real; the look isn't. | Blender, as you planned for the beats after the sun, or AI video from painted key frames, beat by beat. |
| **The sound** | Ten stems generated from the treatment's rules (`animatic/sound.py`): the hiss (wind, sand, swell), the whisper, the release (six layers), the held note, the atmospheres, the laugh, the grains, the cosmos, the world, and one shared reverb space. Better than v2, still synthesized. | Your FL Studio arrangement, from the brief in [ASSESSMENT §5](./ASSESSMENT.md#5-the-sound-in-fl-studio-a-brief). The stems are written as 48 kHz stereo WAVs into `animatic/out/audio/` when you build. |

What's *not* placeholder: the timings, the staging, the direction of every movement (the band always left), the four-face rule, the alternation's safety design, the pair sea's tie between picture and sound, and the structure of the code, which is the structure of the build.

## 2. What to look at first

1. **The sand over the face (0:00–0:38).** Can you see the eyes, nose and mouth without being told, and is the face human enough? The sand is `sand_field` in `beats_abstract.py`; the relief it flows over is `relief`.
2. **The release (0:38).** Two frames of pressed sand, the streak inward, the white face; six layers of sound under it. Is it the strike now, and is it atmospheric enough?
3. **The held note.** It should now be steady, a slight shimmer and no wobble. Say if any of it still sounds like the 1980s.
4. **Beat 3 (0:46–1:08).** The large face off to the right, turned toward the small one; the front of light at the turn (0:58:12).
5. **Beat 4 and 5 (1:08–1:44).** Do the faces break into the grains now, rather than sitting under them? Are the first colors flashes of light? Is the fractal behind the pair sea the right idea?
6. **Pacing.** You found the leaf and the run before the newborn too quick (beats 12–13), and said it would be easier to judge once the animatic is fuller. Nothing moved in v3; the proposal is README item 2.

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

**To change a timing:** edit the beat boundaries `B` at the top of `beats_abstract.py` (they're the treatment's table) and the sub-timings inside the beat's function, then rebuild. **To preview a change:** `py render.py --preview 54 57.5 59 --out preview` and look at the PNGs. On this machine the command is `py`, not `python` (dossier §6).

## 4. Safety

Beat 4's flicker and beat 11's falling sky are designed to the rules in [treatment §5](../../story/arcs/01-beginnings/opening/TREATMENT.md#5-whats-mine-and-the-open-problems): only the first three turns take the whole frame (never more than three a second), the spread is organic, and the grains turn out of step so the frame's brightness holds. A rough check on the rendered frames (mean luminance change per frame in beats 2, 4 and 11) is printed by `py animatic/check_flicker.py <video>`; v2 passes it, as v1 did (worst second: three large changes in beat 4, at the whole-frame turns; one in beat 11; two at the release). **Before anyone watches it full screen, run the finished render through IRIS or PEAT**, as the treatment requires; this animatic has not had that check.

## 5. Next

The order, and why, is in [ASSESSMENT §6](./ASSESSMENT.md#6-what-id-do-next-in-order):

1. Your pass on v3 (README, item 1), and your references as screen recordings if you'd like me to see them (x.com and YouTube refused this session).
2. A session on your desktop: read the plugin folders, and start the sound in FL Studio from the brief.
3. The face shoot (item 7), then your face in Blender.
4. Beats 1–3 in Blender; beats 4, 5 and 7 as GPU shaders; the rest by the route you choose.
