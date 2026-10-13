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

Your desktop: RTX 2060 Super (8 GB video memory), 32 GB RAM, Windows, Blender 5.0, Python 3.14 (`py`), ffmpeg, FL Studio. The 2060 Super is a modest card for this work but enough, if we choose the right tools: Blender's EEVEE renderer for most beats (seconds a frame), Cycles only where volumes or refraction need it (a minute a frame), and GPU shaders for the abstract layers (fractions of a second a frame).

| Tool | For | Cost | Status |
|---|---|---|---|
| **Blender 5.0** (or 5.2 LTS) | Layout, the face, the sand, the stars, the volumes, the world, the edit, the compositing | Free | Installed. 5.0 added shader nodes that can loop, which makes fractal shaders possible in EEVEE |
| **Python + moderngl** | GPU shader passes (grains, sparks, fractal, web) rendered to image sequences without a window | Free | To install, in its own environment |
| **Kalles Fraktaler 2+ and zoomasm** | A true deep zoom into the Mandelbrot set, if beat 5 wants one | Free, open source | Optional |
| **Mandelbulber2** | 3D fractal fly-throughs, scriptable from the command line | Free, open source | Optional |
| **MediaPipe** (Python) | Your expressions from a webcam video: 52 expression weights per frame, no scan | Free | To install, in its own environment |
| **A face tool** (§5) | The designed face | Free (MetaHuman, MPFB2) or about $500 (Character Creator 5 + Headshot 3) | Your call after a test |
| **ComfyUI** with FLUX.2 Klein 4B or SDXL | Concept frames and style frames; restyling Blender renders | Free; the models run on 8 GB | Optional, for look development |
| **An AI video API** (Veo 3.1 Fast, or Kling 3.0, Runway) | Beats 10–14, from our layouts and key frames | Pay per second (§7) | Needs your account and key |
| **DaVinci Resolve** | Color grade, if Blender's isn't enough | Free | Optional |
| **FL Studio** | The sound | Yours | Installed |

**Where things live.** Scripts, shot lists, notes and the small reference files stay in this repository. The big files (`.blend` scenes, caches, renders, EXR sequences) live in a working folder outside git on your fastest drive with room to spare. Renders of five minutes in layers can run to a few hundred gigabytes. Question 3 (§9) asks where.

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

The registers come from Discussion 006 (decided 2026-10-13): beats 1–9 are the vision register, vibrant and abstract; the descent into the world (10–14) takes either the live-action look or *Arcane* (question 1).

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
| **12. Dust** (3:42–4:00) | Time running on the skull; ferns, flowers, the tree; the slow leaf | Blender time-lapse (decay, growth); the leaf as a simulated cloth leaf in real time | — |
| **13. Fill the earth** (4:00–4:36) | The run, always left; the cat, the clash, the newborn, the grave, the generations | Blender layout of the whole run (one long camera path); AI video for the people, shot by shot along it | Content filters: the fight, the clash and the child's burial may be refused by commercial models; those shots can be done in Blender or with an open model on your machine |
| **14. Rest** (4:36–5:00) | Real time: the cliff, the delta at dawn, the face, the breath, the eye | Blender: the designed face, lit for real, and the delta (NASA imagery for the geography) | The close-up of the eye is the hardest shot for realism |

## 5. The face, without a scan

You'd rather not do scans, and you thought v3's face looked fairly realistic. Good: a scan isn't needed. Two separate things make the face: **its design** (the shape, skin and eyes) and **its performance** (the expressions moving).

**The design.** Three routes, best first ([TOOLS §1](./TOOLS.md#1-designed-realistic-faces-without-a-scan-usable-in-blender)):

1. **MetaHuman** (free). The most realistic faces with a full expression rig, designed in a creator, not scanned. Since 2025 Epic's licence allows MetaHumans in any software, free under $1M a year in revenue, with one clause to respect: they must not be used to *train* AI models. It runs inside Unreal Engine (a large install), and reaching Blender needs a community add-on that's still in beta. Your card is below Epic's recommended one. **I'd test it first, in the first session:** design a face, bring it into Blender, render one frame. If that works, it's the face.
2. **Character Creator 5 with Headshot 3** (about $500). Builds a realistic head from one portrait, which can itself be a designed, AI-generated face, so still no scan. A mature bridge to Blender. The fallback if MetaHuman fights us.
3. **MPFB2** (free, all inside Blender, and whatever it makes is yours outright). Less realistic out of the box, but with the 52 standard expression shapes and fully scriptable. Enough for beats 1–4, where the face is under sand, white on white or black on black; weaker for the close-up at the cliff.

**This is the face that recurs through the series** (Discussion 007), so it's worth designing once, carefully, with references, before any shot uses it. It should be "similar enough to recognize" between the first face and the early human at the cliff (your words, 2026-10-03), which is easiest if it's literally the same head, aged and weathered for the cliff.

**The performance.** Your face, but no scan: you film yourself on a webcam doing the six expression runs (eyes closed and still; eyes opening; fear to terror; malice to a wild laugh; upset to peace and sleep; compassion to peace and sleep). Software reads your expression from the video as 52 numbers a frame and drives the designed face with them. Your likeness is never used; only your acting. With MetaHuman, its own Animator does this from a webcam; otherwise MediaPipe does it for any face in Blender. The extremes (terror, the wild laugh) will need pushing by hand, because webcam tracking softens them. If you'd rather not perform at all, I can key the expressions by hand from the four-face rule; it'll be less alive.

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
| 12. Dust | 18 s | Low | Time racing, then slowing to the leaf, then stillness | The leaf was too fast; fixed in v3.1 |
| 13. Fill the earth | 36 s | Medium | Relentless: running, always left | — |
| 14. Rest | 24 s | Still | Real time, stillness, one breath | — |

**Two questions for the tempo map** (question 4, §9): should beat 1 stay slow as the one slow opening, or should the sand move faster sooner? And do beats 3, 7 and 11 match what I wrote in the fourth column?

Pacing also depends on the music, and you'll score to the picture. Two ways to work: lock the picture first and score to it (the plan's default), or you sketch a rough score early, a few minutes in FL Studio with the main hits and the held note, and the layout is cut to it. The second is how many music-driven sequences are made, and it may suit how you work. Your call (question 5).

## 7. Costs and time

**Money.** Everything in the pipeline is free except:
- **AI video for beats 10–14.** For about 134 seconds of footage at roughly four tries per kept shot, about 550 seconds generated: about **$70 with Veo 3.1 Fast**, about **$130 with Kling 3.0**, about **$220 with standard Veo 3.1**, before retakes. For the whole of beats 10–14 with generous retakes, plan on **$150–500**. Video-to-video restyling of Blender renders (Runway Aleph) is about $0.28 a second. Sora's API was withdrawn in September 2026. Prices from [TOOLS §5](./TOOLS.md#5-ai-video-for-live-action-looking-placeholder-shots), October 2026.
- **The face, only if MetaHuman fails:** about $500 for Character Creator 5 and Headshot 3.
- Optional add-ons (Faceit, about $80–100).

**Render time on your card** (estimates; the first test will correct them): EEVEE at 2–10 seconds a frame is 4–20 hours for all 7,200 frames; Cycles at 30–60 seconds a frame would be 60–120 hours, so it's used only for the beats that need it. GPU shader passes take minutes. Renders run overnight, in ten-second parts that pick up where they stopped.

**Your time.** The sessions need you for the review gates, the webcam performance, and the AI video account. Most of the building I can do while you're away from the machine, once the session is set up.

**Rights.** In the US, purely AI-generated frames generally can't be copyrighted; your designs, layouts, edits and direction can. For a placeholder that's fine; it's one more reason the 3D layout should be ours, not the model's (Discussion 006).

## 8. The sound: handoff

The sound is yours, made in FL Studio and laid over the picture afterward (your decision, 2026-10-13). What I hand you at picture lock:

1. **The locked picture**, two copies: one clean, one with the timecode and shot numbers burned in.
2. **A cue sheet** (a spreadsheet): every sound event the picture makes, frame-accurate: the release at 0:38:00, each turn in beat 4, each ignition (with its position in the frame, for panning), the impacts, the quake, the leaf landing, the first footfall at 4:00, the breath.
3. **The guide stems** from the code (`animatic/out/audio/`), as reference only. You liked the held note; its recipe is below so you can rebuild it properly.

**The held note, as made in v3:** three voices at 0 and ±4 cents, panned centre, left and right, a near-sine with a little of the second and third harmonics (fading to a pure tone for the photon), no audible vibrato, gliding between pitches over two or three seconds. It enters at 0:44.4 out of silence and ends at 4:58. Its pitch follows whatever is in focus:

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
| 4:00 | E3 (165 Hz) | The people |
| 4:36 | A2 (110 Hz) | The face again |

**Across the cut into the Garden** (from the Garden's walk in, [LAYOUT §10](../../story/arcs/01-beginnings/garden/LAYOUT.md#10-the-walk-in), 2026-10-13): the Opening ends on black with the breath held, and the Garden's first shot is Adam, a man in his early twenties, letting it out at the east entrance. So the breath is one stem that carries over the cut, and the FL Studio project should hold both sides of it. By then the held note has faded under the cliff's wind; the Garden's walk has little or no music, only birds, water and wind, and the note comes back only at the command. If the animatic ever runs past 5:00, that out-breath is its tail shot, and Adam's face should read as kin to the cliff's ([Discussion 007](../../discussions/007-the-faces-of-god.md)).

The longer sound brief from the assessment (layers per beat, the release's six layers, one shared reverb space) still applies as a starting point; it's in the git history of this file (the assessment of 2026-10-09, §5) if you want it.

## 9. What I need from you

1. **Beats 10–14: the live-action look or *Arcane*?** Discussion 006 gives the series *Arcane* as its base and accepts a live-action-looking placeholder for now; the Opening's descent sits between the two. *My recommendation:* the live-action look, because the Opening lands on a real face in the real world, and it's the best proof of the live-action goal; the Garden then opens the *Arcane* register.
2. **A Remote Control session on your desktop,** started from this thread, in the project folder. The first session: install moderngl and MediaPipe in their own environment; set up the working folder and the master edit; test the face (MetaHuman, then the fallbacks); build the layout of one beat as the proof of the method. *Recommended first beat:* beat 12 into 13, the leaf and the run, because it's where your notes are and it has everything: time-lapse, a real-time moment, a camera move and people.
3. **Where the big files live:** which drive and folder, and roughly how much free space it has. And whether Unreal Engine is installed (MetaHuman needs it; it's a large download).
4. **The tempo map** (§6): mark any beat where the fourth column is wrong.
5. **Score first or picture first** (§6): lock the picture and score to it, or a rough score first and the layout cut to it?
6. **The webcam performance:** are you willing to film the six expression runs (a few minutes, on a webcam or phone), or should I key the expressions by hand?
7. **An AI video account,** when we reach beats 10–14: which provider you'd rather use, and a budget. *My recommendation:* Google's Veo 3.1 Fast through the Gemini API, for its first-and-last-frame control and price.

You offered to list folders: the only listing I need now is the free space on your drives (in PowerShell, `Get-PSDrive -PSProvider FileSystem`). The session can read the rest itself.

## 10. Order of work

1. **Now (done in this round):** this plan; the [reference page](./REFERENCES.md); animatic v3.1 with your leaf note and the impact on screen, as the timing reference until layout replaces it.
2. **Session 1, on your desktop:** set-up; the face test; the master edit with v3.1 cut into it shot by shot; the layout of beats 12–13 as the proof.
3. **The shot list and tempo map** for all fourteen beats (stage A), drafted from the script and corrected by you.
4. **Layout of every beat** (stage B), reviewed in batches, to layout lock.
5. **Style frames** (stage C), one per beat.
6. **Build** (stage D) in this order: beats 1–3 (the face and the sand, the heart of it), 4–5 (the shaders), 6–9, then 10–14 with the AI video.
7. **Picture lock,** your score, the finish.
