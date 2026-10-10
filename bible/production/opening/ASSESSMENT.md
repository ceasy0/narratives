# The Opening — how good it can get, and how

> Your question of 2026-10-09: "a realistic idea for how much better quality can we make this first animatic," given that it's meant to be the most visually and audibly stimulating part of the series. And: "If it would be better for us to do everything in Blender, let me know." My answer, the tools, a plan for your machine, and the brief for the sound in FL Studio.

**Status:** v1, 2026-10-09, written alongside animatic v3. Everything here is my view (P6) unless it quotes you.

---

## 1. The short answer

**Animatic v3 is close to the ceiling of the way it's made.** It's numpy on a CPU at 960×540: every pixel computed in Python arrays, no graphics card, no real light. That's the right tool for timing, staging and sound sync, and it's the wrong tool for the finished look. The jump from here to what you're imagining doesn't come from more of the same code. It comes from three changes, and each one is large:

| | v3 (now) | Realistic target | How much better |
|---|---|---|---|
| **The face** | A generic 468-point face mesh (MediaPipe's canonical face), shaded in code. It reads as a human face, not as a person. | Your own face, filmed or scanned, with skin, pores and real expressions, lit in Blender | The largest single jump. This is the difference between "a face" and "someone." |
| **The sand, grains, gas, stars** | 2D fields, shaded to look 3D, at 960×540 | Millions of real particles with real light, shadow and depth of field (Blender), or GPU shaders at 4K with ten times the detail | About 16× the pixels (4K) and real light: the sand catches the light grain by grain instead of as a texture |
| **The fractal and the abstract layers** | A 2D Mandelbrot glow at half resolution, a few seconds deep | A true deep zoom, and 3D fractals (raymarched: Mandelbulb, kaleidoscopic sets) with lighting and fog, rendered on the GPU | From a backdrop to a place you fall into |
| **The sound** | Synthesized in numpy: sine waves, filtered noise, one generated reverb | Produced in FL Studio with Serum 2 and your plugins: designed patches, real reverbs, a mix done by ear | The biggest jump per hour of work, and the cheapest |
| **The world (beats 10–14)** | Flat silhouettes | Blender scenes, or AI video from painted key frames, as decided per beat | From a plan to a picture |

**Realistic ceiling for beats 1–9:** title-sequence or high-end music-video quality, the level of the best motion-design work, is reachable by one person with your desktop and me writing the code and scenes. That's the right bar for these beats, since they're abstract: there's no "realistic" to fall short of. **For the face:** photoreal is reachable only with your face as the source (a scan or a filmed take), not by any procedural model. **For beats 10–14:** good stylized 3D is reachable; photoreal animals and people at that length isn't, for one person, without AI video or a lot of hours.

## 2. Should everything be in Blender?

**Mostly yes, as the place where it all comes together, but not everything should be *made* in it.**

- **Make in Blender:** the face (beats 1–4 and 14), the sand over the face (a particle or displacement simulation over the face's surface, lit by one raking light, which is exactly the "flowing sand over an extruding face" you described), the gas and the star's interior (volumes), and beats 9–14 (you were already planning the post-sun beats there). Geometry Nodes' simulation zones handle the sand and the grains; Cycles or EEVEE renders them.
- **Make as GPU shaders, and bring into Blender as image sequences:** the grain sea's shimmer and sparks (beat 4), the pair sea and the fractal (beat 5), the cosmic web (beat 7). These are equations evaluated per pixel, which is what a GPU fragment shader does hundreds of times faster than this numpy code. Blender's own shader nodes can't loop, so a deep Mandelbrot or a raymarched fractal is awkward there; a small Python program running GLSL on your graphics card is the natural home, and it's code I can write and you can run.
- **Keep the numpy animatic** as the timing reference. Each layer rendered properly replaces its placeholder in the cut, one beat at a time, so the sequence is always watchable.
- **Assemble and grade in Blender** (the compositor and the Video Sequencer), or in DaVinci Resolve if you'd rather; Resolve is free and is better at color, but one more tool.

**On your references:** I couldn't load either x.com post (x.com refuses automated access) or the YouTube video (it refused the request too), and searching turned up nothing I could check. I worked from your descriptions: the colors changing as in the first post, fractal zooms, and the soundscape. My guess, which I haven't verified, is that the second link is Yuri Artiukh's account, whose work is WebGL shader art; if so, that's the GPU-shader tier above, and a good sign the abstract beats belong there. A screen recording of each, dropped into the project's files, would let me look properly.

**"Simple equations that produce complex results"** is the right instinct, and it's how the abstract beats should be built at every tier. Already in v3: domain-warped noise (the fronts in beat 4), Worley noise (the web's threads and knots), curl noise (the sand's flow), the Mandelbrot set (beat 5). Next, on the GPU: the Mandelbrot zoom as deep as you like (perturbation methods go far past the float limit v3 hits), Julia sets morphing as their constant moves (one number animating, the whole shape changing), raymarched 3D fractals, reaction-diffusion (two equations that grow coral, stripes and cells, possibly the best fit for beats 7 and 10, where life comes), and strange attractors for the particles' paths.

## 3. What it would take on your desktop

Rough numbers for the RTX 2060 Super (8 GB of video memory), from what similar scenes usually cost. They're estimates, not measurements; the first test render will correct them.

| Route | Per frame at 1080p | The whole 5:00 (7,200 frames at 24 fps) |
|---|---|---|
| GPU shaders (beats 4, 5, 7) | Well under a second, often real time | Minutes to an hour per beat |
| Blender EEVEE (the face, sand, beats 9–14) | A few seconds | Several hours to a day |
| Blender Cycles with volumes (the gas, the star) | Half a minute to several minutes | Days; render only the beats that need it in Cycles |
| 4K instead of 1080p | About 4× the above | |

The 8 GB of video memory is the real limit: tens of millions of sand grains or a dense volume can run out of it. The workarounds are standard (render in layers, instance the grains, bake the simulation), and the laptop's RTX 4060, if it has 8 GB too, doesn't change that.

**The face, three ways, best first:**
1. **Your face, scanned and filmed.** A photo scan (a phone and photogrammetry, or a FaceBuilder-type add-on) gives the shape and the skin; your six expression runs (README item 4) drive it. The most "you," and the most work to rig.
2. **A MetaHuman sculpted toward your face.** Very high quality and rigged already. Epic's licence now allows using MetaHumans outside Unreal, as I understand it; check the current terms before committing.
3. **The filmed depth maps alone** (dossier §6, "Real expressions, cheaply"): your phone takes turned into depth by a depth-estimation model, used as the relief the sand flows over. Cheapest, and enough for beats 1–2, where the face is under sand; not enough for the lit faces of beats 3 and 14.

## 4. How we'd work on your machine

A cloud thread like this one can't reach your PC. A **Remote Control session** on your desktop can: Claude Code running there, in the project folder, driving Blender from the command line (`blender -b -P script.py` runs a Python script against Blender with no window, so I can build scenes, simulate and render, and you open the same `.blend` to look and tweak). It can also read your plugin folders, so the sound brief can name the exact plugins you have. FL Studio can't be driven that way in any useful sense, so the sound is your hands with the brief below; I can supply the timed material (stems, and MIDI for anything event-locked, see §5).

A sensible order, each step watchable on its own:
1. **The sound first, in FL Studio** (§5). It's what you flagged as the biggest problem and the cheapest to fix well.
2. **The face:** the shoot (item 4), then the scan or MetaHuman route in Blender.
3. **Beats 1–3 in Blender:** the sand over the face, the release, the two faces.
4. **Beats 4, 5, 7 as GPU shaders,** composited in Blender.
5. **Beats 6, 8, 9 in Blender** (the proton, the star's interior, the photon).
6. **Beats 10–14** by the route you choose per beat.

## 5. The sound in FL Studio: a brief

**Why the held note sounded like "an alien video from the 1980s":** a bug, not a choice. The note's vibrato was computed wrongly in v2, so the wobble in pitch grew the longer the note held; by a minute in it was swinging far more than any real voice does. v3 fixes it (the phase is integrated properly, and the vibrato is slow and slight), and layers the note as three voices a few cents apart, so it shimmers instead of wobbling. In FL, the rule is simply: **no pitch LFO on the note at all.**

**Set-up:** a project at 48 kHz. Set the tempo to 60 BPM so one beat is one second and the treatment's timecodes are bar positions. Import `animatic/out/audio/mix.wav` as a guide track at 0:00, and the stems beside it (written by `py animatic/build.py`, one per layer: hiss, whisper, release, note, atmos, laugh, grains, cosmos, world, and the shared reverb as `space`). Keep any stem that works, replace the rest.

**One space.** Every layer sends to one long reverb bus (a large hall or a "cosmic" algorithmic verb, decay 5–8 s, darker at the top), wide open through the abstract beats and closing in from beat 10 to almost dry at the cliff. That shared space is most of what makes it a soundscape and not a collection of sounds.

| Beat | Layers | In Serum 2 or your plugins |
|---|---|---|
| **1, the deep (0:00–0:38)** | Wind over water; the crackle of pouring sand; a low swell; the whisper; the in-drawn breath that climbs for twelve seconds | Wind: filtered noise, very slow filter movement, wide. Sand: a granular texture (Serum 2's granular oscillator on a noise or sand sample), high-passed, scattered across the stereo field. Swell: a sine sub, rising with the fade. Whisper: noise through a formant/vowel filter, centred. The climb: everything through one filter opening and narrowing, plus a riser. Fade everything from frame 0. |
| **2, the release (0:38)** | Six layers, the loudest moment by a wide margin (20 dB or more over the hiss): a reverse suck into it; a distorted sub drop (about 55 down to 28 Hz); a punch with a click on top; a noise blast; the static's tail, pitched and smeared, passing the ears front to back; its own dark reverb, about six seconds. Then true silence | Sub: a sine with a pitch envelope into saturation. Punch: a layered kick. Blast: white noise through a band-pass sweeping down. Tail: the hiss stem, pitch-shifted and stretched, through a panner or binaural plugin moving front to back. Duck everything else under the hit. The current stem has all six; replace them one by one. |
| **The held note (0:44 to 4:58)** | One clear note that never stops and belongs to whatever is in focus: low after the turn, a fifth up in beat 4, an octave in beat 5, with a fifth and octave locking on at the proton | A near-sine wavetable with a little second and third harmonic, three unison voices at about ±4 cents, no pitch LFO, slow filter movement only. Glide between pitches over a second or two. Send generously to the space. |
| **3, the separation (0:46–1:08)** | The note; the laugh as hard pulses in the hiss, growing; a dissonant cluster under it; the pulses stop dead on the turn; an open fifth for the connection | The laugh: the hiss through a volume gate or Gross Beat-style shaper in the laugh's rhythm. Cluster: three pads a semitone and a tritone apart, very quiet. |
| **4, evening and morning (1:08–1:24)** | A tick on each turn; ticks multiplying into a granular shimmer, each grain on its own beat; from 1:17, pitched grains: the first color, the first pitches | Granular synthesis; random pitch per grain within a scale; the grains stem as a guide. |
| **5, the vault (1:24–1:44)** | Thousands of blips, each one a flash in the picture: pitch is its color, pan is its place | The blips are event-locked to the picture. The stem is the reference; if you'd rather play them with your own patch, I can write the events out as a MIDI file (time, pitch, and pan as a controller), so every note still lands on its flash. |
| **6–9 (1:44–2:46)** | The electron's ping each orbit; the gas as a pad; the stars' ignitions (attack and a high blip, at each star's own time and place); bursts as low booms; the fall into the star as a rising roar; two impacts; the photon's flight in near silence | Pad: wide fifths with a slow filter sweep. Ignitions and booms: same as the release's kit, smaller. The cosmos stem is timed to the stars in the picture. |
| **10–14 (2:46–5:00)** | The world: water, the swarm, wind, the land, the night, the band, the cliff | Real recordings or sample libraries, little reverb, the space closing in. Beat 14 almost dry: open air, real time. |

**Deliver** 48 kHz, 24-bit stems back into the project, named as above, and the build will mux them over the picture (`build.py --audio-only` remuxes without re-rendering).

## 6. What I'd do next, in order

1. You: a pass on v3's sound and picture, and the references as screen recordings if you'd like me to look at them.
2. A Remote Control session on the desktop: read the plugin folders and tailor §5; set up the FL project with the stems.
3. The face shoot, then the face in Blender.
4. Beats 1–3 in Blender, the first finished minute.
