# Adonai — working rules for Claude

*Adonai* is the working title. A creative dramatization of the Bible: screenplays first, then a 3D animated series as the placeholder for an eventual live-action version. It expresses the author's understanding of Christianity. It is faithful to the spirit of the texts and never contradicts them.

## Read first

1. `canon/FOUNDATIONS.md`: the author's stance and every decision so far. It wins over other docs.
2. `canon/POSITIONS.md`: the Positions Register, every interpretive choice the story depends on.
3. `canon/FRAMINGS.md`: the author's unconventional framings, each with its fit grade and status.
4. `discussions/README.md`: which discussions are open, and what each one blocks.
5. `style/STORYTELLING.md`: the author's notes on how scenes should play. Apply them to every draft, along with `style/VOICES.md` (how each character speaks) and `style/LEXICON.md` (the word list).
6. `ROADMAP.md` is the founding document: §3 (principles), §4 (provenance), §5 (language), §8.8 (the fit check). Where it conflicts with the files above, they win.

## Where things live

| Thing | Canonical home | Everything else |
|---|---|---|
| A conversation and its outcome | `discussions/NNN-*.md` | links to it |
| A decision | one line in `canon/FOUNDATIONS.md` §4, dated, with a link | links to it |
| An interpretive position | `canon/POSITIONS.md` | links to it |
| A framing and its fit grade | `canon/FRAMINGS.md` | links to it |
| The open questions for the author | `README.md`, "What I need from you" | nowhere else |
| A storytelling rule | `style/STORYTELLING.md` | treatments cite it |
| An arc's research, treatment, beats | `story/arcs/NN-*/` | — |
| A project review | `REVIEW.md` (2026-10-07; a dated record, so its times for the Opening are the 4:50 cut's) | — |
| A project audit | `AUDIT.md` (2026-10-10; a dated record of faults found and fixed; its open calls are README items) | — |
| The series as episodes | `story/ARCHITECTURE.md` | arc plans link to their section |

Record a decision once, in its home, and link from the rest. Don't paste it into a second file.

## Current phase (2026-10-13)

- **The map:** `story/ARCHITECTURE.md` v1.2, 205 hours in 18 arcs. Arc 1 is *Genesis*, eight hours with the author's names (In the Beginning; Cain and Abel; The Days of Noah; The Ark; The Flood; The Table of Nations; The Tower of Babel; The Scattering). Every hour after it is numbered two higher than in v1. Season 3 is *The Struggle*, for now (2026-10-09). **Filling the hours** (the author, 2026-10-09): first fill each episode with what the Bible itself gives, without worrying about runtime; contextual scenes fill the gaps later. Keep the map current: when an arc is treated, its lines get corrected.
- **Writing front to end, treatments and beats first,** from Genesis 1 (the author's decisions of 2026-10-03 and 2026-10-05). Ruth is parked as a first draft, with a storyboard.
- **The Opening (Gen 1:1–2:7) is the exception** (the author, 2026-10-07): treatment v3.4, script v1.3 (`scripts/beginnings/opening.fountain`, PDF beside it) and animatic v3.1 (`production/opening/opening-animatic-v3.1.mp4`, rendered in code with a generated soundtrack) as of 2026-10-13. It runs 5:00, the fade from black starting on frame 0, the release at 0:38. The author said the treatment and script fit what they imagine; the work is getting the animatic to match it, and they want it the most stimulating part of the series. Its timings are the treatment's table; change the table, re-render. **How the finished Opening gets made is `production/opening/PLAN.md`** (2026-10-13, the author's request: faults can't be fixed one at a time): the honest answer on quality, stages A–G around one master edit with layout first, the face without a scan, the tempo map, costs, and the handoff of the sound, which the author makes in FL Studio as a separate layer over the locked picture. `TOOLS.md` is the research behind it; `REFERENCES.md` is the look book, beat by beat. What's placeholder in the animatic is in `production/opening/README.md`. Discussion 006 is decided (2026-10-13): live action is the goal, an AI live-action-looking placeholder is enough for now, *Arcane* is the base style, and visions and spiritual scenes are vibrant and abstract (*Spider-Verse*-like). Next: the plan's questions (README item 1), then Remote Control sessions on the author's desktop, the first setting up the master edit, testing the face and laying out beat 12 into 13.
- **The Garden (Gen 2:8–3:24)** is the rest of Episode 1. Discussions `008` and `009` are decided (2026-10-08). The Garden's dossier (`story/arcs/01-beginnings/garden/DOSSIER.md`) gathers the decisions and the look; `garden/LAYOUT.md` (2026-10-09) is the research on the shape, the stone and the light (decided 2026-10-09 and revised 2026-10-10: a round island in a ring of fresh water in the marsh, a stranger in the plain; a stepped centre built by its own spring, squared toward the top by Adam; the four headwaters straight to the ring with grey limestone paths, natural rivers beyond it; winding paths through the quarters; sunny, cool, breezy light made with shade; plants and animals of the region; the rule is "the line between natural and too rare to be natural"). Decided 2026-10-13 (LAYOUT §10): gold (the evening light, bdellium, living things; none in the water, nothing gilded); the tree of life north, the tree of knowledge south; the Garden about 5500 BC, with Eridu built after it at its gate; Babel at Eridu. **The Garden's treatment is the next writing deliverable.** The rule for it: no invented speech between Adam and Eve that the Opening's grammar could carry instead; God through the world in two registers; nothing in the world speaks but the serpent. **But 009 is reopened (2026-10-13)** for the author's idea of God seen as an old man, Adam's father (009 round 3, FR-20, README item 22): the treatment's staging of God waits on that answer; everything else in it can be written.
- **The rest of Genesis 1–11 (hours 2–8):** Discussion `010` (seeded 2026-10-13) holds Positions 6 and 7 and the dating of Genesis 1–11 (README items 6–8); `011` (seeded the same day) holds God's regret in Gen 6:6, the first of the stories' own questions (item 26). Hour 2, *Cain and Abel*, needs neither and can be treated right after the Garden.
- **Sessions run on the author's computer when they can** (the RTX 2060 Super desktop, 32 GB RAM, Blender 5.0, FL Studio 2024 and 2025 installed; Python 3.14 with numpy and Pillow, run as `py`, since bare `python` is only the Store's placeholder; ffmpeg 9.0.2, installed with winget on 2026-10-08). Cloud sessions can't reach the prototype at `H:\Current\Projects\Agentic\Biblical Story Concept`, Blender or FL Studio. The author has allowed installing video tools and anything else needed (2026-10-05). The animatic needs only Python, numpy, Pillow and ffmpeg.
- **Keep `README.md`'s "What I need from you" list current.** It is the one place the author tracks every open question, and everything open or needing the author goes there, including questions for later arcs (the author, 2026-10-11). **When a question is answered, delete it from the list; never strike it through** (the author, 2026-10-10). First record the answer where it belongs (FOUNDATIONS §4, the arc's dossier, ARCHITECTURE, the discussion), then remove the item, renumber the list, and fix every `README item N` reference elsewhere in `bible/`.
- **Commit and push after every round of edits** (the author's instruction, 2026-10-03). Git works on the author's drive without extra flags.
- **Ruth (parked):** `story/arcs/07-ruth/README.md`. Treatment v4, beat sheet, storyboard (sixteen frames, drawn in code; pencil sketches of them since 2026-10-09, at the author's request), and a 37-page first-draft script with every line tagged. Next, whenever the author returns to it: their pass on the script, then the audit and the lock. The David connection at the end is deferred.

Update this section as steps finish.

## Rules

- **Never contradict the texts.** If an edit or framing from the author pulls against a passage, say so plainly, cite the passages, give the fit grade (Supported, Compatible, Tension or Contradiction), and propose a discussion. Don't silently fix it and don't silently accept it.
- **Report problems as you find them.** The author has asked to hear about any problem with the story as it comes up, not only when asked.
- **Bring the case against.** For any framing, present the strongest opposing texts and views as well as the supporting ones. The author has asked for challenge, not agreement.
- **Converse; don't just annotate.** The author prefers real opinions and a conversation that moves forward over neutral lists of references. React, take a position, mark it as your own view, and end with the question that moves things on.
- **Tag everything.** Content gets a provenance level (P1–P6) and dialogue gets a tier (A–D). Recorded words are the default; changing their substance needs a discussion and a logged decision.
- **Modern words, ancient minds.** Setting 2 (plain modern) is the baseline register. No therapy-speak, no idiom before its origin, no knowledge a character couldn't have had.
- **No theology for its own sake.** Never add dialogue or scenes just to get more theology in. Additions must grow from context, evidence, or the spirit of the story.
- **Material from beyond the canon** comes in only after discussion. Label it P3.
- **Learn from the author's edits.** After each of their passes, compare it with the draft, record recurring patterns in the `style/` docs, and ask about any change you can't interpret.
- **Ambiguous text: use the most likely reading.** Where the Hebrew or Greek can be read more than one way, the dialogue follows the most likely reading, with the reasons and the alternatives in a note (the author's instruction, 2026-10-02).
- **One language rule** (confirmed by the author). English always stands for Israel's own language; sister dialects are accents; every other language follows the author's three tiers (ROADMAP §5.7). Use "Yahweh" only in oaths and where the Name itself is the point (§5.5).
- **Non-English lines** always come with the original script, a transliteration, a literal back-translation and a confidence level. Flag reconstructed languages, especially first-century Galilean Aramaic, for specialist review.
- **Write decisions down.** Decisions go in `canon/FOUNDATIONS.md` or `canon/POSITIONS.md`, dated. Long conversations go in `discussions/`. Nothing important should live only in chat, because the next session won't see it.
- **Check citations.** Verify verse references, and flag anything stated with less than full confidence.
- **Say "kind," not "species,"** of Adam and Eve (the author, 2026-10-07): the change in them isn't bodily. They are "of one kind" (the author, 2026-10-08).
