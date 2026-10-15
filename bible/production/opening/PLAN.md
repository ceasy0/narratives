# The Opening — production plan

> How to make the Opening's five minutes at high quality, and whether I can. Your request of 2026-10-13: "I want you to tell me if you think you actually can make this animatic at a high quality? And if so, how you would do so." With your rules: the sound is its own part, made by you in FL Studio and laid over the finished picture; no face scan if a normal face can be had without one; settle the pipeline and the workflow first.

**Status:** v1, 2026-10-13. The research behind every tool and price is in [TOOLS.md](./TOOLS.md), with sources. The visual references are in [REFERENCES.md](./REFERENCES.md). Everything here is my view (P6) unless it quotes you; the decisions it rests on are in [FOUNDATIONS §4](../../canon/FOUNDATIONS.md#4-decisions-so-far).

---

## 1. The honest answer

**Yes, I think I can make it at high quality, for most of it, but not the way I've been making it.** And there are two places where "high quality" depends on things other than me.

**Why fixing v3 note by note won't get there.** You're right that the faults can't be fixed one at a time. They come from the method, not from the individual shots:

- **There is no space.** Every animatic so far was drawn in 2D by coordinates in code. There's no camera, no lens, no ground plane, no scale. When something is in the wrong place or moves the wrong way, nothing in the method catches it; I place it by numbers and check a few still frames.
- **There's no fast loop.** A full render took 50 minutes in the cloud, and you saw the result days later. Pacing can only be judged in motion, at speed, many times. Neither of us could do that.
- **I was the only reviewer between your notes.** I can't watch motion in real time the way you do; I look at frames and measure. So the feel of a beat, fast or slow, was never checked by the one person who knows what it should feel like.
- **The pacing was set per beat, never per shot.** The treatment's table gives each beat a length, but nothing says how fast things move inside it. Measured on v3, three beats are almost motionless where the story wants speed: beat 3 (the faces climb, but nothing else moves), beat 7 (ten seconds of gas drawing into threads, barely moving) and beat 11 (the land's eras, as flat silhouettes). See §6.

**What changes.** The work moves to your desktop, into Blender, with a real 3D layout of every shot, a fast preview loop you can scrub yourself, and a gate at each stage where you sign off before anything expensive is made. That's how studios catch exactly the faults you're seeing: in a layout pass, before animation and rendering ([TOOLS §7](./TOOLS.md#7-professional-pipeline-practice-solosmall-team)).

**How confident I am, part by part:**

| Part | Beats | Can I make it at high quality? | What it depends on |
|---|---|---|---|
| The abstract world: static and sand, grains, sparks, the fractal, the gas and the web, the stars, the photon | 1–9 | **Yes, with high confidence.** This is equations, particles and light, which is what code and a graphics card do best. The target is the level of the best title sequences and music videos. | Your desktop's graphics card, and your eye on the pacing |
| The face | 1–4, 14 | **Yes, to a believable human face, with medium-high confidence.** Without a scan. | A designed face from a character tool (§5), and a short webcam performance of yours for the expressions, or hand-keyed ones |
| The living world: cells, sea life, dinosaurs, the impact, the band, the cliff | 10–14 | **To a live-action-looking placeholder, yes, with medium confidence, but not by me alone.** A 3D build driven by me would look like a well-lit technical demo for animals and people. The practical route is AI video, guided by layouts I build in Blender. | A budget for AI video (§7: roughly $150–500 for these beats), your accounts with one provider, and your call on the look (question 1, §9) |
| The sound | all | **Yours**, in FL Studio, laid over the locked picture (your decision). I hand you a locked cut, a cue sheet and the guide stems (§8). | — |

**What I can't do,** so you can plan around it: I can't feel the pace of a cut the way you can, so you're the judge of every timing; I can't operate websites with my hands, so AI video goes through a provider's API with your key, or you run it; and I can't promise any AI video model will do exactly what we ask in one try. Everything else in this plan I can drive myself on your machine.

## 2. The machine and the tools

Your desktop: RTX 2060 Super (8 GB video memory), 32 GB RAM, Windows 10, Blender 5.0.1, Unreal Engine 5.7.2 with the Epic Games Launcher (so MetaHuman needs no engine download), Python 3.14 (`py`) and 3.12, ffmpeg 9.0.2, FL Studio. Drives, free space on 2026-10-14: C: (the internal 1 TB SSD, which holds the projects folder, the programs and the caches) 274 GB; D: (3 TB hard disk) 2,327 GB; E: (2 TB hard disk) 1,304 GB; H: (a Seagate Backup Plus 2 TB USB disk, with the older copy of the projects folder) 1,661 GB. C: is the fast drive and the smallest, so it's the one to watch. The 2060 Super is a modest card for this work but enough, if we choose the right tools: Blender's EEVEE renderer for most beats (seconds a frame), Cycles only where volumes or refraction need it (a minute a frame), and GPU shaders for the abstract layers (fractions of a second a frame).

| Tool | For | Cost | Status |
|---|---|---|---|
| **Blender 5.0** (or 5.2 LTS) | Layout, the face, the sand, the stars, the volumes, the world, the edit, the compositing | Free | Installed. 5.0 added shader nodes that can loop, which makes fractal shaders possible in EEVEE |
| **Python + moderngl** | GPU shader passes (grains, sparks, fractal, web) rendered to image sequences without a window | Free | Installed in the environment at `C:\Users\corbi\AdonaiOpening\venv` (Python 3.12, with numpy and Pillow); it opens an off-screen context on the RTX 2060 Super |
| **Kalles Fraktaler 2+ and zoomasm** | A true deep zoom into the Mandelbrot set, if beat 5 wants one | Free, open source | Optional |
| **Mandelbulber2** | 3D fractal fly-throughs, scriptable from the command line | Free, open source | Optional |
| **MediaPipe** (Python) | Your expressions from a webcam video: 52 expression weights per frame, no scan | Free | Installed in the same environment |
| **A face tool** (§5) | The designed face | Free (MetaHuman, MPFB2) or about $500 (Character Creator 5 + Headshot 3) | Your call after a test |
| **ComfyUI** with FLUX.2 Klein 4B or SDXL | Concept frames and style frames; restyling Blender renders | Free; the models run on 8 GB | Optional, for look development |
| **An AI video API** (Veo 3.1 Fast, or Kling 3.0, Runway) | Beats 10–14, from our layouts and key frames | Pay per second (§7) | Needs your account and key |
| **DaVinci Resolve** | Color grade, if Blender's isn't enough | Free | Optional |
| **FL Studio** | The sound | Yours | Installed |

**Where things live.** Scripts, shot lists, notes and the small reference files stay in this repository. The big files (`.blend` scenes, caches, renders, EXR sequences) live in a working folder outside git on your fastest drive with room to spare. Renders of five minutes in layers can run to a few hundred gigabytes. **Your rule:** project files live in the projects folder on the PC's internal SSD, `C:\Users\corbi\Personal\Current\Projects` (2026-10-14; the USB disk on H was too slow for the work), so this repository is `C:\Users\corbi\Personal\Current\Projects\Agentic\Narratives\bible`; program and system files go on whichever PC you're working on (2026-10-13). So the big files go in `bible/production/opening/work/`, which git ignores, and the programs (Blender add-ons, Python environments, Unreal and MetaHuman if needed) install on the PC. The SSD is fast enough for caches and for scrubbing image sequences, but it's the smallest drive and the only working copy of anything git doesn't hold. So two things I'd do: watch C:'s free space, and move finished renders we keep to D: when it gets tight; and back up `work/` to H, which keeps the older copy of the projects folder, as a backup rather than a second place to work.

**The folders.** The scripts that build everything are in [`pipeline/`](./pipeline/) (in git): the shot list, the master edit and each beat's layout. They write to `work/`: `work/edit/` (the master edit), `work/layout/` (one `.blend` per layout) and `work/playblast/` (the playblasts, which the master edit picks up by name). Blender's caches and proxies, and the Python environment, are on the PC in `C:\Users\corbi\AdonaiOpening\`. That folder isn't under `%LOCALAPPDATA%` because the Claude app redirects that path into its own private folder, where Blender wouldn't find it.

## 3. The pipeline

**The edit is the spine.** One master edit in Blender's Video Sequencer, five minutes long, with one strip per shot. Each shot starts as its v3.1 animatic strip and is replaced in place as it improves: layout playblast, then look-development frame, then final render. The film is watchable end to end at every stage, and timing never drifts, because every replacement has the same frame count. This is how Blender Studio runs its own films ([TOOLS §7](./TOOLS.md#7-professional-pipeline-practice-solosmall-team)).

| Stage | What gets made | What you check | Gate |
|---|---|---|---|
| **A. Pre-production lock** | The **shot list**: every shot with its timecode, what's in frame, the camera (lens, height, move), screen direction, speed of motion, and its sound hits. The **tempo map** (§6). An **overhead map** of every place with movement in it (the shore, the night, the dead animal, the forest run, the cliff). The [reference page](./REFERENCES.md), and one **style frame** per beat (§4). | That every shot is the shot you imagine, and where it should feel fast or slow | You sign off the shot list and the tempo map |
| **B. Layout** | Every shot built in Blender in grey: real cameras and lenses, stand-in shapes at true scale, the moves and the timing. Rendered as fast playblasts with the timecode and shot number burned in, cut into the master edit. | **Pacing, placement and movement.** This is the stage that catches what you saw in v3. You can open the file and scrub it yourself. | **Layout lock:** no timing changes after this |
| **C. Look development** | One finished frame per beat, at final quality: the face, the sand, the grain sea, the fractal, the web, the star, the Earth, the shore, the cliff | The look | You sign off each beat's frame |
| **D. Build** | Each beat made properly by its method (§4), shot by shot, replacing its layout strip | Each beat as it lands | Per beat |
| **E. Render and composite** | Final renders in layers; compositing, grade, grain; the cut at full resolution | The whole thing | **Picture lock** |
| **F. Sound** | You score and design the sound to the locked picture in FL Studio | — | Your mix |
| **G. Finish** | Your mix laid over the picture; the IRIS or PEAT flicker check on the final file; the master | The final | Done |

**How you give notes.** Each review is a playblast or a frame sheet with the timecode and shot number on screen. You send notes in the thread by timecode ("4:01, the leaf should lift higher"), and I keep them in a notes log beside the shot list, each marked open or done, so nothing is lost between sessions.

**How we work.** In sessions on your desktop through a Remote Control session from this project: Claude Code running on your machine, in the project folder, driving Blender from the command line (`blender -b -P script.py`) and writing everything as scripts, so every shot can be rebuilt and every change is a line. You open the same `.blend` files to look, scrub and tweak. Cloud threads like this one keep doing the writing, research and planning.

## 4. Beat by beat

The registers come from Discussion 006 (decided 2026-10-13): beats 1–9 are the vision register, vibrant and abstract; the descent into the world (10–14) takes the live-action look if it can be done, and *Arcane* if not (your answer, 2026-10-13). The test is the first AI-video shots: if they hold up next to the 3D layout, live action stays.

| Beat | What it needs to be | Method | Main risk |
|---|---|---|---|
| **1. The deep** (0:00–0:38) | Grain like fine sand pouring over a face rising beneath it, read by its contours and the way the grains catch one raking light | Blender: the face as a surface; millions of sand grains as particles flowing over it (Geometry Nodes simulation), plus a displacement layer; EEVEE | Grain counts on 8 GB; solved by rendering in layers |
| **2. Light** (0:38–0:46) | Two frames of pressed sand, the blast inward, the white face; six seconds of stillness; the eyes open | Blender, the same face; compositing for the blast | — |
| **3. The separation** (0:46–1:08) | Two faces, the large one off to the side, expressions climbing; the front of light at the turn | Blender: the face with its expression animation, lit white on black and black on black; the front as a shader | Expressions reading as real (§5) |
| **4. Evening and morning** (1:08–1:24) | Whole-frame turns, then organic fronts, the faces breaking into grains, sparks of colored light | GPU shader passes (fronts, grains, sparks) over Blender face renders | Flicker safety: the rules in treatment §4 stand |
| **5. The vault** (1:24–1:44) | The wildest part: pairs of light appearing and vanishing, depth, the fall into the fractal's edge | GPU shaders for the pair sea; a true deep zoom from Kalles Fraktaler, or a 3D fractal from Mandelbulber2, behind it | Choosing the fractal: style frames first |
| **6. Land and seas** (1:44–2:02) | Three lock into one; the sea of protons; the atom | Blender particles and glows | — |
| **7. The earth brings forth** (2:02–2:12) | The gas drawing into a web: fast, alive, growing | GPU shader, or Geometry Nodes points; a time-lapse feel, not a slow drift | It was nearly still in v3 |
| **8. Lights** (2:12–2:32) | Stars igniting at the web's knots; the fall into a star; the interior | Blender: point lights and volumes (Cycles for the interior) | Volume render time |
| **9. The crossing** (2:32–2:46) | The photon's flight; the Earth growing; down through cloud into the sea and a cell | Blender: a planet (public-domain NASA textures), clouds, water, a cell shader | — |
| **10. The waters swarm** (2:46–3:18) | Time-lapse of life in the sea: cells, the swimmer, fish, the great creature, the first wings | Blender layout and camera; AI video from key frames for the creatures | Consistency between AI shots |
| **11. The land** (3:18–3:42) | The haul-out, the lizard, the night of giants, the dead *Triceratops*, the small creature, the impact | Same; the impact's glow, quake and falling sky in Blender | AI video for animals; the impact can be all Blender |
| **12. Dust** (3:42–4:07) | Time running on the skull; ferns, flowers, the tree; the slow leaf | Blender time-lapse (decay, growth); the leaf as a simulated cloth leaf in real time | — |
| **13. Fill the earth** (4:07–4:43) | The run, always left; the cat, the clash, the newborn, the grave, the generations | Blender layout of the whole run (one long camera path); AI video for the people, shot by shot along it | Content filters: the fight, the clash and the child's burial may be refused by commercial models; those shots can be done in Blender or with an open model on your machine |
| **14. Rest** (4:43–5:07) | Real time: the cliff, the delta at dawn, the face, the breath, the eye | Blender: the designed face, lit for real, and the delta (NASA imagery for the geography) | The close-up of the eye is the hardest shot for realism |

## 5. The face, without a scan

You'd rather not do scans, and you thought v3's face looked fairly realistic. Good: a scan isn't needed. Two separate things make the face: **its design** (the shape, skin and eyes) and **its performance** (the expressions moving).

**The design.** Three routes, best first ([TOOLS §1](./TOOLS.md#1-designed-realistic-faces-without-a-scan-usable-in-blender)):

1. **MetaHuman** (free). The most realistic faces with a full expression rig, designed in a creator, not scanned. Since 2025 Epic's licence allows MetaHumans in any software, free under $1M a year in revenue, with one clause to respect: they must not be used to *train* AI models. It runs inside Unreal Engine (a large install), and reaching Blender needs a community add-on that's still in beta. Your card is below Epic's recommended one. **I'd test it first, in the first session:** design a face, bring it into Blender, render one frame. If that works, it's the face.
2. **Character Creator 5 with Headshot 3** (about $500). Builds a realistic head from one portrait, which can itself be a designed, AI-generated face, so still no scan. A mature bridge to Blender. The fallback if MetaHuman fights us.
3. **MPFB2** (free, all inside Blender, and whatever it makes is yours outright). Less realistic out of the box, but with the 52 standard expression shapes and fully scriptable. Enough for beats 1–4, where the face is under sand, white on white or black on black; weaker for the close-up at the cliff.

**This is the face that recurs through the series** (Discussion 007), so it's worth designing once, carefully, with references, before any shot uses it. It should be "similar enough to recognize" between the first face and the early human at the cliff (your words, 2026-10-03), which is easiest if it's literally the same head, aged and weathered for the cliff.

**One face, reshaped.** A face on a standard rigged head (a MetaHuman, or any head fitted to one) can be reshaped into kin: jaw, nose, brow, eye spacing, age and weight change while the expressions keep working, because the mesh layout doesn't. That gives Discussion 007's recurring face, with every bearer a variation of it. Shape warps well; skin doesn't, so each variant needs its skin reworked (age, weathering, tone). A woman, a child or a very different face is better designed from scratch than stretched.

**If the designed face doesn't look real enough, your own face is the fallback** (your offer, 2026-10-13), as the base for the recurring face only; the series' other characters stay designed, so they don't all descend from you. A set of photos, or a slow turn filmed on your phone, is enough: Headshot 3 or KeenTools FaceBuilder builds a head from photos, and Epic's free RealityScan app with Mesh to MetaHuman fits one to a rigged head. The photos stay out of git, in `work/face/`. The MetaHuman test decides whether it's needed (§9, item 2).

**The performance is made in software** (your call, 2026-10-14): you won't film the expression runs. The head's rig has the 52 standard expression controls, and I key them for the six runs (eyes closed and still; eyes opening; fear to terror; malice to a wild laugh; upset to peace and sleep; compassion to peace and sleep) from the four-face rule, with reference clips of real faces to time them against. MediaPipe can still read a clip of anyone's face as those 52 numbers a frame, as a starting point to push by hand. Keyed expressions are less alive than a performance, so the extremes and the holds get the most care, and you judge them in the face test.

## 6. Pacing: the tempo map

The brief (2026-10-03) says the sequence "should feel very fast," and you've found parts that feel slow where they should be fast. Pacing needs a target for each beat, not just a length. Here's a first tempo map for you to correct. It's the most useful thing you can mark up before the layout stage.

**Measured on v3** (how much the picture changes per second, averaged over each beat; grain inflates the abstract beats, so compare like with like):

| Beat | Length | Motion in v3 | What I think it should feel like | v3's problem |
|---|---|---|---|---|
| 1. The deep | 38 s | Steady (the grain) | Slow, held, a build of tension; the only slow opening in the sequence | The fade and the wait may be right; the rising face could move more |
| 2. Light | 8 s | Still, after one blast | One instant of violence, then stillness | — |
| 3. The separation | 22 s | **Almost none** | Slow faces, but a climbing intensity: the camera and the light should move with the climb | Only the expressions move |
| 4. Evening and morning | 16 s | Very high | Accelerating, then a shimmer | — |
| 5. The vault | 20 s | High | The wildest, fastest part | — |
| 6. Land and seas | 18 s | Medium | Locking: fast, then settling | — |
| 7. The earth brings forth | 10 s | **Almost none** | Fast growth, time-lapse | Nearly still |
| 8. Lights | 20 s | Medium | Ignitions in rhythm, then an accelerating fall | — |
| 9. The crossing | 14 s | Medium | Speed, then a plunge | — |
| 10. The waters swarm | 32 s | Medium | Fast time-lapse | Flat placeholders |
| 11. The land | 24 s | **Almost none** | Eras flying past, then one held moment of listening, then the impact | Flat placeholders; the impact wasn't on screen until v3.1 |
| 12. Dust | 25 s | Low | Time running, slower than before, then slowing to the leaf, then stillness | 7 s longer from your layout notes (2026-10-14), so the Opening runs 5:07 |
| 13. Fill the earth | 36 s | Medium | Relentless: running, always left | — |
| 14. Rest | 24 s | Still | Real time, stillness, one breath | — |

**The tempo map stands for now** (your answer, 2026-10-13: "sounds right for now"); the layout pass is where it gets tested, beat by beat.

**Picture and sound go back and forth** (your answer, 2026-10-13). The layout is cut first, so you have something to score against; your rough score then feeds back into the cut, and so on until both lock together. For the picture, you'll give me reference images to work from. For the sound, I guide you: how to make each sound in FL Studio, how the layers fit together, and, from your descriptions, where to find sounds in films to listen to for inspiration.

## 7. Costs and time

**Money.** Everything in the pipeline is free except:
- **AI video for beats 10–14** (Google Veo, your pick, 2026-10-13, unless something better exists when we get there). For about 134 seconds of footage at roughly four tries per kept shot, about 550 seconds generated: about **$70 with Veo 3.1 Fast**, about **$130 with Kling 3.0**, about **$220 with standard Veo 3.1**, before retakes. For the whole of beats 10–14 with generous retakes, plan on **$150–500**. Video-to-video restyling of Blender renders (Runway Aleph) is about $0.28 a second. Sora's API was withdrawn in September 2026. Prices from [TOOLS §5](./TOOLS.md#5-ai-video-for-live-action-looking-placeholder-shots), October 2026.
- **The face, only if MetaHuman fails:** about $500 for Character Creator 5 and Headshot 3.
- Optional add-ons (Faceit, about $80–100).

**Render time on your card,** measured: the leaf look test, with simple procedural assets, took about 2 seconds a frame at 1280×720 in EEVEE; the realistic test of the run, with rigged people on motion capture, took about 5⅓ minutes a frame at 1920×1080 (84 frames in 7½ hours), so the 36-second run alone would be about 3 days. GPU shader passes take minutes. **A faster PC is coming, and the aim is truly realistic** (you, 2026-10-15), so full-quality rendering waits for it. Until then the work is what the 2060 Super does quickly: the layout (Workbench playblasts, minutes), the look decided in single frames and short tests, the face, the assets, and the cloud tests (Aleph), none of which needs the new card. Renders, when they come, run overnight, in ten-second parts that pick up where they stopped.

**Your time.** The sessions need you for the review gates, your photos for the face (the expressions are made in software, 2026-10-14), and the AI video account. Most of the building I can do while you're away from the machine, once the session is set up.

**Rights.** In the US, purely AI-generated frames generally can't be copyrighted; your designs, layouts, edits and direction can. For a placeholder that's fine; it's one more reason the 3D layout should be ours, not the model's (Discussion 006).

## 8. The sound: handoff

The sound is yours, made in FL Studio and laid over the picture afterward (your decision, 2026-10-13). Along the way I guide you through making each sound and fitting the layers together, and find sounds in films for you to listen to from your descriptions (§6). What I hand you at picture lock:

1. **The locked picture**, two copies: one clean, one with the timecode and shot numbers burned in.
2. **A cue sheet** (a spreadsheet): every sound event the picture makes, frame-accurate: the release at 0:38:00, each turn in beat 4, each ignition (with its position in the frame, for panning), the impacts, the quake, the leaf landing, the first footfall at 4:07, the breath.
3. **The guide stems** from the code (`animatic/out/audio/`), as reference only. You liked the held note; its recipe is below so you can rebuild it properly.

**The held note, as made in v3:** three voices at 0 and ±4 cents, panned centre, left and right, a near-sine with a little of the second and third harmonics (fading to a pure tone for the photon), no audible vibrato, gliding between pitches over two or three seconds. It enters at 0:44.4 out of silence and ends at 5:05. Its pitch follows whatever is in focus:

| From | Pitch | What's in focus |
|---|---|---|
| 0:44 | A2 (110 Hz) | The faces |
| 1:18 | E3 (165 Hz), then A3 (220 Hz) by 1:24 | The grains, a fifth up, then an octave |
| 1:47 | A3, with a fifth and an octave locking on until about 2:22 | The proton and the atom |
| 2:02 | G3 (196 Hz) | The gas and the web |
| 2:24 | B3 (247 Hz), rising to A5 (880 Hz) by 2:31 | The fall into the star; the photon, high and pure |
| 2:44 | E4 (330 Hz) | The cell, the sea |
| 3:18 | A3 (220 Hz) | The animal |
| 3:42 | G3 (196 Hz) | The dust |
| 4:07 | E3 (165 Hz) | The people |
| 4:43 | A2 (110 Hz) | The face again |

**Across the cut into the Garden** (from the Garden's walk in, [LAYOUT §10](../../story/arcs/01-beginnings/garden/LAYOUT.md#10-the-walk-in), 2026-10-13): the Opening ends on black with the breath held, and the Garden's first shot is Adam, a man in his early twenties, letting it out at the east entrance. So the breath is one stem that carries over the cut, and the FL Studio project should hold both sides of it. By then the held note has faded under the cliff's wind; the Garden's walk has little or no music, only birds, water and wind, and the note comes back only at the command. If the picture ever runs past 5:07, that out-breath is its tail shot, and Adam's face should read as kin to the cliff's ([Discussion 007](../../discussions/007-the-faces-of-god.md)).

The longer sound brief from the assessment (layers per beat, the release's six layers, one shared reverb space) still applies as a starting point; it's in the git history of this file (the assessment of 2026-10-09, §5) if you want it.

## 9. What I need from you

1. **Watch the twelfth pass of the first layout: beats 12 and 13, 03:42 to 04:43.** It's `work/playblast/1200-1395-layout.mp4`, on channel 2 of the master edit (`work/edit/opening-master.blend`) over the animatic. Grey stand-ins at true scale: judge where the camera is, what's in frame, which way things move and how fast. Send notes by timecode. Your notes on the first eleven passes (2026-10-14) are folded in; each choice is a number in [`pipeline/layout_b12_13.py`](./pipeline/layout_b12_13.py):
   - **The Opening runs 5:07** (your call, 2026-10-14): beat 12 is 25 s instead of 18, and everything from 04:00 on is 7 s later. The decay is slower (the fire stops by 03:45, the flesh goes 03:45–03:48, the skull sinks 03:48–03:50:12, the green and the forest come back 03:50:12–03:54), the tree grows over 2.5 s (03:54–03:56:12), and everything is still for nearly two seconds before the leaf. The animatic stays 5:00; the master edit maps it onto the new timings shot by shot, so its beat 12 runs short under the layout.
   - **03:42–04:08, one unbroken shot, low and right up next to the dead animal, square to the band's path** (24 mm, 40 cm off the ground). The head decomposes in the centre of frame, 3.4 m away, with the burrow the small creature ran into beside it, filled by the ash. The tree grows where the head lay, centred, and we see only its stump, with the forest beyond. The leaf falls into frame from above like a feather, in front of the stump, and lands 1.6 m from the lens, at 04:03. It comes into frame at 04:01:09; a full second later the view starts to tip down, slowly, 11° over 2.6 seconds, settling after the leaf lands, so the ground fills the frame. Then it lies still for four seconds (one more, your note) before the feet. Because the camera looks straight across the path, nobody can be seen coming: legs and feet come in from the right as they reach the leaf, and the frame is too low to show more of them. Then the whip.
   - **The whip** is a jerk: it leaves at full speed and only eases into the runners, eight frames, straight left, aimed just ahead of the lead runner. (The last pass aimed at the middle of the band, which at that moment was still to the right of the leaf, so the camera first swung right; that was the counter-movement.) **The first cut in the Opening is at 04:08,** after it.
   - **04:08–04:15, fast cuts (SH1310–1316).** SH1310 is a woman's face, close (50 mm), running with her: the centre woman, the face the beat follows. Every cut after it is a camera planted in one place that turns to follow them and whips as they go by: the lead man looking back as he passes (35 mm now, wider); the band from high and wide, two seconds now; back past the last runners into the trees, where the big cat is charging, closing about 7 m a second. SH1314–1316 are from the far side of the band, so they run to the right of frame: the girl running hard, now at 28 mm from 4 m off and ahead of her, so she runs at us and past; spears and legs, low; the band coming at the lens and streaming past it, two seconds now. A forest now stands on that side too, so those shots look into trees. It's the one break in "always left" (your rule of 2026-10-05), confined to these three cuts; the travelling camera from 04:15 keeps them moving left. The two extra seconds come out of the travelling run before the cat (SH1320, now 04:15–04:17), so the cat still catches them at 04:17 and the Opening stays 5:07.
   - **The band is a crowd, not a formation** (your note): no two runners are in step, each has its own stride, and each wanders across and along the pack on slow waves of its own, settling as they fall into a line later. They swerve round the tree and the camera.
   - **What they're running from** is the big cat (my pick): it's after them from before the leaf, charges in SH1313 and trails them. **At 04:18:14 it catches them** (your note: not a fight, which would look awkward): it leaps on the last man but one and drags him down; the last man turns back, kills it with one thrust of his spear at 04:19:07, hauls him up by the arm, and the two run on and catch the band up by about 04:23. The travelling camera hangs back with them and then catches up too. The man who does the killing is the one who falls at the clash a few seconds later.
   - **04:15–04:43, the travelling camera,** 1.5 m high, always 9.5 m from the band's path, and **it only ever moves forward with them** (your note, 2026-10-14): never in or out, never back, and never slower than 0.5 m a second, however slowly it goes. Where it hangs back, the band outruns it. Getting closer or wider is the lens, which gives the framings the earlier passes got by moving: 35 mm through the forest, 37 for the cat, 51 after it, 39 for the clash, then **a small zoom to 43 mm in SH1360** (04:27:10–04:28:14) once the trunk has passed, **a little more, to 48 mm, at the grave** (04:33:12–04:34:12, after the lone tree), and wide, 33 mm, for the river. Generations pass where a trunk crosses the lens, four times: at 04:15:19 and 04:22:12 in the forest; at 04:26:07, a quick wipe as the clash ends (it used to hang at the edge of SH1360, where the camera now crawls); and at 04:33, a lone tree in the grass between us and the line just after the newborn has gone up it (your note: one more tree there, one more generation).
   - **At the grave (SH1390),** a man walking up the line behind her reaches her as she finishes, takes her arm and pulls her up and on with him. She looks back once.
   - **Known faults:** no motion blur in the playblast; the people are stick stand-ins, so the fights are positions, not action; the river doesn't read from eye height in grey; the cliff isn't built yet, so the layout stops at 04:43.
2. **The face, after these notes** (the order you set, 2026-10-13). Your photos go in `work/face/`, out of git. Best is a set (straight on, both three-quarter views, both profiles, neutral, soft even light, no glasses) or a slow 20-second turn on your phone; one front photo works, but the sides are then guessed. The expressions are made in software (§5). *Yours to say:* your face as the base of the recurring face from the start, or the fallback behind a designed face, as planned?


3. **The first look test: the leaf shot (SH1250), from grey to a lit picture** (your go-ahead, 2026-10-14). Three stills at 1920×1080 (`work/lookdev/leaf-040116.png`, `-040206`, `-040312`: the leaf just in frame, in front of the stump, landed) and a four-second clip at 1280×720 (`work/lookdev/leaf-lookdev.mp4`, 04:00:12–04:04:12). It's [`pipeline/lookdev_leaf.py`](./pipeline/lookdev_leaf.py): it opens the layout's own file and keeps its camera and the leaf's path, then swaps the grey for procedural materials (soil, leaf litter, bark, leaves), a sun from ahead and to the left with a little haze, ferns built leaflet by leaflet, an understory, a finer trunk, and a leaf with a real outline that's a cloth simulation pinned along its midrib, so it bends and flutters as the keyed path carries it down. EEVEE. What it shows:
   - **The pipeline works.** The layout goes straight to a lit shot: about 3 seconds a still at 1080p, about 2 seconds a frame for the clip at 720p with motion blur, well inside the estimates in §7.
   - **The cloth leaf works:** it falls as a curved, translucent blade, and the focus holds on it.
   - **Procedural assets give a clean CG forest, not live action.** Cone trunks, ball crowns and blob shrubs give it away at once. For the live-action look the trees, ferns and ground have to be real: scanned models and textures (Poly Haven's are CC0, free for any use; other libraries need their licences checked), or the AI pass over the render. That's the next test's job.
   - **The light is a choice to make with you.** A low sun behind the forest put the whole floor in cold shade; side light from 38° up reads better. I'd pick it from references, as we did for the look of each beat.
   *Yours:* look at the stills and the clip and say what you'd change.
4. **The AI video test** (your go-ahead for both, 2026-10-14, with Aleph your favourite). It's [`pipeline/ai_video_test.py`](./pipeline/ai_video_test.py), run with the project's Python (`C:\Users\corbi\AdonaiOpening\venv\Scripts\python.exe`, where I've installed Google's and Runway's libraries). The shot is the layout's travelling camera from 04:15:00 to 04:18:12, the band running left through the forest with the cat coming up behind: SH1311 is under a second, too short for either tool. The layout renders it clean, with no burn-in (`-- clean=04:15:00-04:18:12`, already done: `work/aitest/`). **Aleph** takes that clip and restyles it as live action, keeping our camera, timing and movement (about $1). **Veo** can't follow a clip: Gemini first repaints the first and last frames as live action (a few cents), then Veo makes 4 seconds between them (about $0.40). Nothing is sent or spent without `--go`, and I'll ask you before each.
   - **Google: done.** Your `GEMINI_API_KEY` is set and works: the free check reached the newest image model and Veo 3.1 Fast. Veo needs billing turned on for the key's project (Google AI Studio, then Billing), since it isn't on the free tier.
   - **Runway: yours to set up.** (1) Make an account on Runway's developer portal, dev.runwayml.com (the API is separate from the Runway app and its subscription). (2) Buy some API credits there; the API is prepaid. (3) Create an API key. (4) In your own PowerShell, set it for your user: `[Environment]::SetEnvironmentVariable("RUNWAYML_API_SECRET", "<your key>", "User")`. Don't paste the key to me. (5) Restart the Claude app, so this session sees the new variable. Then tell me, and I'll run the free check and ask before the paid run.
*Also yours to say:* whether v1 and v2 of the animatic stay in the folder beside v3.1.

Decided 2026-10-13, and folded in above: the live-action look for beats 10–14 if it can be done, *Arcane* if not (§4); the project files in the projects folder and the programs on the PC (§2); the tempo map for now (§6); picture and sound back and forth, with your reference images and my guidance on the sound (§6, §8); Google Veo (§7). Decided 2026-10-14: the expressions are made in software, not filmed (§5).

## 10. Order of work

1. **Done:** this plan; the [reference page](./REFERENCES.md) and its images; animatic v3.1, the timing reference until layout replaces it; the set-up on your desktop (§2); the master edit, with v3.1 cut into the script's 79 shots at their timecodes; the first layout of beats 12–13 and eleven more passes from your notes; the first look test, the leaf shot (§9).
2. **Next on your desktop:** your notes on the twelfth pass of the beats 12–13 layout. The face test (MetaHuman in Unreal 5.7, or a head from your photos, brought into Blender, one frame rendered with one keyed expression) comes after those notes: the story reel has to be right first (you, 2026-10-13).
3. **The shot list and tempo map** for all fourteen beats (stage A), the cut list is [`pipeline/shots.csv`](./pipeline/shots.csv), drafted from the script; each shot still needs its camera, screen direction, speed and sound hits, and your corrections.
4. **Layout of every beat** (stage B), reviewed in batches, to layout lock.
5. **Style frames** (stage C), one per beat; single frames, so they can start before the new PC.
6. **Build** (stage D), on the new PC, in this order: beats 1–3 (the face and the sand, the heart of it), 4–5 (the shaders), 6–9, then 10–14 with the AI video.
7. **Picture lock,** your score, the finish.
