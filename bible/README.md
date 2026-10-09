# Adonai

*Working title.* A creative, faithful dramatization of the Bible that expresses your understanding of Christianity. It gets written first as story and screenplay, then produced as a fully rendered 3D animated series, which is the placeholder for an eventual live-action version. It uses modern dialogue so that ancient people feel as present to us as they did to the people who first heard their stories.

This directory holds the planning documents, the Opening's research, treatment, script and animatic, the Garden's dossier, the Ruth pilot's research, treatment, beat sheet, storyboard and first-draft script.

## Documents

| File | What's in it |
|---|---|
| [`REVIEW.md`](./REVIEW.md) | **New, 2026-10-07:** a fresh read of the whole project, what's working, and what I'd change, in order |
| [`story/ARCHITECTURE.md`](./story/ARCHITECTURE.md) | The whole Bible as episodes, one line each: 205 hours in 18 arcs (v1.1, with your names and count for Genesis), the threads that run through them, the seasons, and every change from your draft |
| [`ROADMAP.md`](./ROADMAP.md) | The founding plan: principles, the provenance system, language rules, the fit check for framings, story architecture, the writing pipeline and the road to 3D. **Start with §0.** |
| [`canon/FOUNDATIONS.md`](./canon/FOUNDATIONS.md) | Your stance and every decision so far, in your own words where possible. It overrides everything else. |
| [`canon/POSITIONS.md`](./canon/POSITIONS.md) | The Positions Register: every interpretive and theological choice the story depends on, and when each must be decided |
| [`canon/FRAMINGS.md`](./canon/FRAMINGS.md) | Your unconventional framings: what each says, which texts support it and which pull against it, and a first-pass fit grade |
| [`discussions/`](./discussions/) | The theological, philosophical and production conversations. 002, 005, 007, 008, 009 (for the Garden) and (for Genesis) 001 are decided. 006 is under discussion. |
| [`world/TIMELINE.md`](./world/TIMELINE.md) | The working chronology: fixed anchors, the major dating questions, every arc's dates, the kings and the prophets |
| [`story/arcs/01-beginnings/`](./story/arcs/01-beginnings/README.md) | Arc 1, *Genesis* (Genesis 1–11). The Opening (1:1–2:7): [dossier](./story/arcs/01-beginnings/opening/DOSSIER.md), [treatment v3.3](./story/arcs/01-beginnings/opening/TREATMENT.md), [script](./scripts/beginnings/opening.fountain) and the [animatic](./production/opening/README.md). The Garden (2:8–3:24): its [dossier](./story/arcs/01-beginnings/garden/DOSSIER.md), seeded with the look |
| [`production/opening/`](./production/opening/README.md) | The Opening's animatic, all 5:00 with sound, rendered in code (`opening-animatic-v3.mp4`, 2026-10-09; v2 and v1 are the earlier cuts), the code that makes it, and the [assessment](./production/opening/ASSESSMENT.md) of how far the finished film can go, with the sound brief for FL Studio |
| [`story/arcs/07-ruth/`](./story/arcs/07-ruth/README.md) | The Ruth pilot: the plan, the research dossier, the treatment, the beat sheet and a [storyboard](./story/arcs/07-ruth/STORYBOARD.md) of sixteen key frames, drawn as sketches (2026-10-09) |
| [`scripts/ruth/`](./scripts/ruth/ruth.fountain) | The first-draft Ruth screenplay, with every line tagged |
| [`style/`](./style/STORYTELLING.md) | Your notes on how scenes should play ([`STORYTELLING`](./style/STORYTELLING.md)), how each character speaks ([`VOICES`](./style/VOICES.md)), and the word list ([`LEXICON`](./style/LEXICON.md)) |
| [`CLAUDE.md`](./CLAUDE.md) | The working rules Claude loads in every session, so nothing depends on memory. |

## The short version

**Modern words, ancient minds.** Characters speak contemporary English, so the audience hears them as people rather than statues. They think, want and know only what people of their own time could have.

**Everything has a provenance.** Every element of a scene is labeled by where it came from: Scripture, history, tradition, scholarly inference, your own conviction, or invention. Every line of dialogue is labeled by how much freedom was taken with it. The words the text records, above all from God and from Jesus, are the default: changing their substance takes a discussion first.

**Make it land the way it landed.** For every scene we ask what the first audience knew and felt that a modern audience doesn't. Then we get that across through staging and story, not through lectures.

**Front to end.** The writing goes from Genesis to Revelation, treatments and beats first, so the whole story is laid out before any part is revised. Ruth, the pilot, is parked as a first draft.

## Status

| | |
|---|---|
| Phase | Writing from the front of the Bible to the end (your decision, 2026-10-03). The first pass is treatments and beats only (2026-10-05); scripts come after. Episodes run about an hour. |
| Episode 1 | *In the Beginning:* the Opening (Genesis 1:1–2:7, 5:00), then the Garden to 3:24. |
| The Opening | **Treatment v3.3, script v1.2 and animatic v3 (2026-10-09).** You said the treatment and script fit what you imagine, and the work now is getting the animatic to match it. v3 applies your notes on v2: sand over a real human face mesh, the fade from frame 0, the steady note and a layered release in one reverb space, the large face to the side, fronts of light, the faces breaking into grains, sparks of color, the fractal. No timing moved. The [script](./scripts/beginnings/opening.fountain) is shot by shot, timed and tagged. The [animatic](./production/opening/README.md) is still code with placeholders (the face is anyone's, the world is silhouettes, the sound is synthesized); [ASSESSMENT.md](./production/opening/ASSESSMENT.md) says how far the finished film can go and with which tools. |
| The Garden | **Unblocked.** [008](./discussions/008-adam-eve-and-the-garden.md) and [009](./discussions/009-god-in-the-garden.md) are decided (2026-10-08). The [dossier](./story/arcs/01-beginnings/garden/DOSSIER.md) is seeded with every decision and the look (your stone paths and stepped centre, with my response). **Next: the treatment.** |
| The map | v1.1: Arc 1 is *Genesis* in eight hours with your names; every later hour is renumbered by two; Season 2 is *The Father of Nations*; Season 3 is *The Struggle*, for now (2026-10-09). Episodes are filled first with what the Bible gives, runtime aside, and the gaps filled with contextual scenes later (your rule, 2026-10-09; [§11](./story/ARCHITECTURE.md#11-what-the-map-needs-decided-and-when)). |
| Ruth | Parked as a first draft, now with a [storyboard](./story/arcs/07-ruth/STORYBOARD.md) of sixteen key frames, drawn as pencil sketches (2026-10-09). Its slot in the map is after Gideon (hour 69). |
| The last session | Ran in the cloud (2026-10-09): animatic v3, treatment v3.3, script v1.2, the assessment and the Ruth sketches, pushed to the branch `claude/project-thread-s9917q`, not merged. The one before ran on your computer (2026-10-08, late): ffmpeg was installed with winget; Python 3.14 with numpy and Pillow was already there, as `py`; animatic v2 was rendered there. |
| Formats | Markdown for docs · Fountain for screenplays · mp4 for the animatic |

## What I need from you

Everything the project is waiting on, in one place. I'll keep this list current. Your answers of 2026-10-08 (evening) settled the map's four questions, the Garden's five, Genesis 18 and the Garden's look; they're recorded in [Discussion 009](./discussions/009-god-in-the-garden.md#round-2--2026-10-08-evening), [FOUNDATIONS §4](./canon/FOUNDATIONS.md#4-decisions-so-far), [ARCHITECTURE §11](./story/ARCHITECTURE.md#11-what-the-map-needs-decided-and-when) and the [Garden dossier](./story/arcs/01-beginnings/garden/DOSSIER.md).

**The short version: item 1 is your reaction to animatic v3, item 2 is the pacing you flagged, item 3 is the Ruth sketches. Your answers of 2026-10-09 settled items 4 and 5 and the script; they're recorded in [FOUNDATIONS §4](./canon/FOUNDATIONS.md#4-decisions-so-far). Item 6 is the Garden's look. The rest are carried over.**

### The Opening, v3, and Ruth

1. **Animatic v3.** Watch [`opening-animatic-v3.mp4`](./production/opening/opening-animatic-v3.mp4) (5:00): your notes on v2 applied, with no timing moved ([production README](./production/opening/README.md), [treatment v3.3 §4](./story/arcs/01-beginnings/opening/TREATMENT.md#from-v32-to-v33-2026-10-09)). What I most want to know: can you see the eyes, nose and mouth in the sand now, and is the face human enough for a placeholder? Is the held note steady (v2's wobble was a bug)? Is the release atmospheric enough? Do the faces break into the grains, and are the first colors flashes of light? Is the fractal behind the pair sea the right idea? Your question about quality and Blender is answered in [ASSESSMENT.md](./production/opening/ASSESSMENT.md): Blender for the face, the sand, the volumes and beats 9–14, GPU shaders for the grain, fractal and web layers, and FL Studio first, since the sound is the cheapest big gain. *Also yours to say:* whether v1 and v2 stay in the folder beside v3.
2. **Pacing of beats 12 and 13.** You found the leaf falling and the run before the newborn too quick, and said it would be easier to judge in a fuller animatic. My proposal: the leaf falls for three seconds instead of one and a half, then two seconds of stillness instead of half a second (+3 s); the cat and the clash each get two more seconds (+4 s). The sequence would run 5:07. Yes, a change, or wait for the Blender pass?
3. **The Ruth sketches.** All sixteen frames, now drawn as pencil sketches: [sheet 1](./story/arcs/07-ruth/storyboard/sketches/sheet-1.png) and [sheet 2](./story/arcs/07-ruth/storyboard/sketches/sheet-2.png) ([STORYBOARD](./story/arcs/07-ruth/STORYBOARD.md)). Do they help? Keep the red-pencil names and lines on the frames, or strip them? Still open from v1: the two rules I proposed (toward the camera is home; Naomi's state as the frame's fullness), keep or strike.

### The map, and the Garden

4. ~~**Season 3's name.**~~ **Answered 2026-10-09:** *The Struggle*, "for now" ([§11](./story/ARCHITECTURE.md#11-what-the-map-needs-decided-and-when)).
5. ~~**Hour 8's name and shape.**~~ **Answered 2026-10-09:** fill each episode with what the Bible itself gives, without worrying about runtime, and fill the gaps with contextual scenes later. So hour 8 stays *The Scattering* and is written from the text; whether it holds an hour is seen at the treatment ([§11](./story/ARCHITECTURE.md#11-what-the-map-needs-decided-and-when)).
6. **The Garden's look.** The stepped centre, adopted as I've read it ([dossier §2](./story/arcs/01-beginnings/garden/DOSSIER.md#2-the-look)): a low, broad, worn terrace of placed stone, no wall, the way east a descent. And the color rule I drew from your description: color only in what lives. Yes, no, or a change?

### For the Opening's build, at a local session

7. **The face shoot.** Your own face, on a phone, lit from the front: the six expression runs in the [dossier §6](./story/arcs/01-beginnings/opening/DOSSIER.md#real-expressions-cheaply), ten seconds each, a few takes. With a photo scan if you can (the ways are in [ASSESSMENT §3](./production/opening/ASSESSMENT.md#3-what-it-would-take-on-your-desktop)). The animatic's face is a real mesh now, but it's anyone's face; yours is the one that drops in.
8. **A session on your desktop** (a Remote Control session from the project): read the plugin folders you listed, tailor the [sound brief](./production/opening/ASSESSMENT.md#5-the-sound-in-fl-studio-a-brief) to them, set up the FL Studio project with the generated stems, and start the Blender scenes. (Python and ffmpeg are on the machine as of 2026-10-08.)

### Before the rest of Genesis 1–11

9. **The "sons of God" and the Nephilim** (Gen 6:1–4; Position 6), before hour 3.
10. **The flood:** global or regional (Position 7), before hour 4.
11. **Dating Genesis 1–11.** Adam at about 5000–4000 BC stands as provisional until Genesis 4–5 is treated ([TIMELINE §3.4](./world/TIMELINE.md#34-primeval-history-genesis-111)).

### Ruth (parked)

12. Your pass on the [script](./scripts/ruth/ruth.fountain), whenever you return to it, then the audit and the lock.
13. The David connection at the end, deferred by your choice.
14. **Length.** The draft is 37 pages, about 37 minutes. At an hour an episode it needs about twenty minutes more, or a partner.

### Open discussions

15. **[006](./discussions/006-2d-or-3d.md):** 2D or 3D, the hybrid plan, and the look book. The animatic is a data point: everything in it is code, and the question is what the finished look is.
16. **[002](./discussions/002-jesus-humanity.md), round 3:** the two guardrails on 2 Sam 7:14b.

### Before later arcs

The map lists the hard passages it found, by arc, in [ARCHITECTURE §11](./story/ARCHITECTURE.md#11-what-the-map-needs-decided-and-when); the first is the ban (*herem*), before Arc 5.

17. **Before Job and the Gospels:** FR-19, the devil as what evil actions are, and who plays the role each time.
18. **Before the Exodus:** which pharaoh; the large numbers (Position 9); the full version of God among the nations (Discussion 004); how Moses is set apart (Discussion 001, deferred); the bridegroom of blood; Pharaoh's heart.
19. **Before the prophets:** whether the great visions of Isaiah, Ezekiel and Daniel are where the Opening's world comes back at full strength (Discussion 001, deferred; you said "possibly"); who speaks Isaiah 40–66.
20. **Before the Gospels:** FR-03's on-screen approach; the disputed passages (Position 3); Gospel harmony (Position 11, which sets the order of hours 146–183); Luke's census (Position 10); Peter's role and the Last Supper (Position 18); FR-09; FR-10's bloodline and "the colors of Christ" (the resurrection is decided); the two questions left from Discussion 002.
21. **Before Revelation:** how to read it (Position 19).
22. **Before Genesis 16:** Position 14 beyond Genesis 18, scene by scene (Hagar first).
