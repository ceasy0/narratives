# The Opening — production

> The visualization of Genesis 1:1–2:7. As of 2026-10-08: an animatic of the whole 5:00 (v2), rendered in code with a generated soundtrack, cut to [treatment v3.2](../../story/arcs/01-beginnings/opening/TREATMENT.md)'s timings and the [script](../../scripts/beginnings/opening.fountain)'s shots.

**v2 (2026-10-08, evening):** your note applied. Ten seconds are added at the front, and they are a fade in from black: the hiss rises out of silence from 0:00, the static comes up from about 0:02 and is at full strength by 0:10. Everything after that runs ten seconds later than in v1, and nothing else has changed. v1 (4:50, opening cold on static) is still in the folder as `opening-animatic-v1.mp4` until you say to remove it.

**Watch:** [`opening-animatic-v2.mp4`](./opening-animatic-v2.mp4) (5:00, 854×480, 24 fps, stereo, 44 MB: the repository copy, re-encoded small because the static beats don't compress). **Build it:** `py animatic/build.py` (needs Python 3.10+, numpy, Pillow, ffmpeg). On your desktop the full render takes well over an hour, not the twenty minutes the cloud machine took, and the fall into the star (2:17–2:30) is by far the slowest stretch; for anything but a full rebuild, render the changed seconds alone with `py animatic/render.py --video part.mp4 --start A --end B`. The build also writes the full-quality 960×540 file to `animatic/out/`, about 230 MB, kept out of git.

---

## 1. What this is, and isn't

You asked for the full animation of the Opening (2026-10-08). This is the first complete pass of it: every one of the fourteen beats, in order, at the treatment's exact timings, with sound, so the whole sequence can be watched and judged for pace before anything expensive is made. That's the dossier's step 1 ("a timed storyboard of the whole sequence, with a rough soundtrack"), done as moving pictures rather than stills, with steps 2 and 3 started in the same code.

It isn't the finished animation. Three things are placeholders by necessity, because v1 was made in a cloud session without the face shoot, Blender or FL Studio (v2 was re-rendered on your machine from the same code, so the placeholders are the same):

| Placeholder | What it is now | What replaces it |
|---|---|---|
| **The face** (beats 1–4, 14) | A procedural depth-map face (`animatic/face.py`): a sculpted mask with the four-face rule's expressions as parameters. It reads as a mask, not a person. | The filmed face turned into depth maps (dossier §6, "Real expressions, cheaply"). `face_fields` is the one function to swap; everything downstream (the static flowing over the contours, the white and black faces, the lit face at the cliff) stays as it is. |
| **The world** (beats 10–14) | Flat silhouettes and gradients: cells, the swimmer, the fish, the great creature, the shore, the night, the *Triceratops*, the tree, the band, the delta. Staging, direction and timing are real; the look isn't. | A Blender build, MetaHuman or AI video from painted key frames, by the route you choose and the budget (dossier §6, "How I'd build it"). |
| **The sound** | Eight stems generated from the treatment's rules (`animatic/sound.py`): the hiss, the whisper, the release, the held note, the laugh, the grains, the cosmos, the world. Rough, and mixed by ear in numbers. | Your FL Studio arrangement. The stems are written as 48 kHz stereo WAVs into `animatic/out/audio/` when you build; take them in, keep what works, replace the rest. |

What's *not* placeholder: the timings, the staging, the direction of every movement (the band always left), the four-face rule, the alternation's safety design, the pair sea's tie between picture and sound, and the structure of the code, which is the structure of the build.

## 2. What to look at first

0. **The fade (0:00–0:10), new in v2.** Is ten seconds right, or does the wait before the face (now at 0:16) feel dead? Does the hiss arrive far enough ahead of the grain? The picture's fade is `FADE_PICTURE` in `beats_abstract.py`, and the sound's is the first line of `stem_hiss` in `sound.py`.
1. **The release at 0:38.** Four frames of picture, one hit of sound. Is it the strike you described?
2. **Beat 3 (0:46–1:08).** The REVIEW's worry was that two arcs of expression in 22 seconds would flicker. On a mask it's readable; on a real face it may want five seconds from beat 5. The treatment's table is the only thing to change.
3. **Beat 4's alternation (1:08–1:24).** Only the first three turns take the whole frame; then it spreads organically. Does the spread read as "ink in water," and is the first color visible?
4. **Beat 13 (4:00–4:36).** Does one steady speed hold it together, or does it read as a montage? Each event (the cat, the clash, the newborn, the grave) happens on the move.
5. **The face in the static (0:16–0:38).** The animatic adds a faint contrast cue inside the face because video compression kills the motion cue. Say whether you can see the face at all without being told, and whether that's too much or too little.

## 3. The code

All in `animatic/`. Pure functions of time, so frames render in any order and in parallel, and every change is a number.

| File | What it does |
|---|---|
| `common.py` | Grids in normalized coordinates, value noise, curl flow, Worley noise, the flowing static, shapes, blur, color, point splatting |
| `face.py` | The procedural face: depth, masks and creases from expression parameters; the eight named expressions; the white, black, white-on-white and dark renderings |
| `beats_abstract.py` | Beats 1–9: the deep, light, the separation, evening and morning, the vault, land and seas, the earth brings forth, lights, the crossing |
| `beats_world.py` | Beats 10–14: the waters swarm, the land, dust, fill the earth, rest. Silhouettes via Pillow. |
| `sound.py` | The eight stems, the mix and the WAV writer. The pair sea's blips, the flips' ticks and the stars' ignitions come from the same event lists the picture uses. |
| `render.py` | The frame loop: `--preview 10 30 45` writes PNGs at those seconds; `--video out.mp4 --procs 4` renders slices in parallel through ffmpeg and concatenates them |
| `build.py` | Frames, soundtrack, mux: one command |

**To change a timing:** edit the beat boundaries `B` at the top of `beats_abstract.py` (they're the treatment's table) and the sub-timings inside the beat's function, then rebuild. **To preview a change:** `py render.py --preview 54 57.5 59 --out preview` and look at the PNGs. On this machine the command is `py`, not `python` (dossier §6).

## 4. Safety

Beat 4's flicker and beat 11's falling sky are designed to the rules in [treatment §5](../../story/arcs/01-beginnings/opening/TREATMENT.md#5-whats-mine-and-the-open-problems): only the first three turns take the whole frame (never more than three a second), the spread is organic, and the grains turn out of step so the frame's brightness holds. A rough check on the rendered frames (mean luminance change per frame in beats 2, 4 and 11) is printed by `py animatic/check_flicker.py <video>`; v2 passes it, as v1 did (worst second: three large changes in beat 4, at the whole-frame turns; one in beat 11; two at the release). **Before anyone watches it full screen, run the finished render through IRIS or PEAT**, as the treatment requires; this animatic has not had that check.

## 5. Next

1. Your notes on the animatic (README, item 1).
2. The face shoot, at a local session (item 7). Then `face_fields` takes the filmed depth maps, and beats 1–4 and 14 are the real face.
3. Beats 1–8 properly: higher resolution, the particle sea and the web at full density, the sound built stem by stem in FL Studio.
4. Beats 9–14 by the route you choose.
