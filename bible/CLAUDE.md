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

## Current phase (2026-10-10)

- **The map:** `story/ARCHITECTURE.md` v1.2, 205 hours in 18 arcs. Arc 1 is *Genesis*, eight hours with the author's names (In the Beginning; Cain and Abel; The Days of Noah; The Ark; The Flood; The Table of Nations; The Tower of Babel; The Scattering). Every hour after it is numbered two higher than in v1. Season 3 is *The Struggle*, for now (2026-10-09). **Filling the hours** (the author, 2026-10-09): first fill each episode with what the Bible itself gives, without worrying about runtime; contextual scenes fill the gaps later. Keep the map current: when an arc is treated, its lines get corrected.
- **Writing front to end, treatments and beats first,** from Genesis 1 (the author's decisions of 2026-10-03 and 2026-10-05). Ruth is parked as a first draft, with a storyboard.
- **The Opening (Gen 1:1–2:7) is the exception** (the author, 2026-10-07): treatment v3.3, script v1.2 (`scripts/beginnings/opening.fountain`, PDF beside it) and animatic v3 (`production/opening/opening-animatic-v3.mp4`, rendered in code with a generated soundtrack) as of 2026-10-09. It runs 5:00, the fade from black starting on frame 0, the release at 0:38. The author said the treatment and script fit what they imagine; the work is getting the animatic to match it, and they want it the most stimulating part of the series. Its timings are the treatment's table; change the table, re-render. What's placeholder (the face is a generic face mesh, the world is silhouettes, the sound is synthesized) is in `production/opening/README.md`; the quality ceiling, the tools (Blender for the face, sand, volumes and beats 9–14; GPU shaders for the abstract layers) and the FL Studio sound brief are in `production/opening/ASSESSMENT.md`. Open: pacing of the leaf and the run in beats 12–13 (README item 2). Next: the author's notes on v3, the sound in FL Studio, the face shoot, beats 1–3 in Blender.
- **The Garden (Gen 2:8–3:24)** is the rest of Episode 1. Discussions `008` and `009` are decided (2026-10-08). The Garden's dossier (`story/arcs/01-beginnings/garden/DOSSIER.md`) gathers the decisions and the look; `garden/LAYOUT.md` (2026-10-09) is the research on the shape, the stone and the light (decided 2026-10-09: a square island in fresh water in the marsh, a stepped centre built by its own spring, straight grey limestone paths along the four headwaters and winding paths through the quarters, a shadow-led mood, plants and animals of the region; the rule is "the line between natural and too rare to be natural"). Proposed 2026-10-10, open (README item 20, LAYOUT §9): a ring instead of the square, the terraces squared at the top by Adam, and Babel built over the buried Garden. **The Garden's treatment is the next writing deliverable.** The rule for it: no invented speech between Adam and Eve that the Opening's grammar could carry instead; God through the world in two registers; nothing in the world speaks but the serpent.
- **Sessions run on the author's computer when they can** (the RTX 2060 Super desktop, 32 GB RAM, Blender 5.0, FL Studio 2024 and 2025 installed; Python 3.14 with numpy and Pillow, run as `py`, since bare `python` is only the Store's placeholder; ffmpeg 9.0.2, installed with winget on 2026-10-08). Cloud sessions can't reach the prototype at `H:\Current\Projects\Agentic\Biblical Story Concept`, Blender or FL Studio. The author has allowed installing video tools and anything else needed (2026-10-05). The animatic needs only Python, numpy, Pillow and ffmpeg.
- **Keep `README.md`'s "What I need from you" list current.** It is the one place the author tracks every open question. **When a question is answered, delete it from the list; never strike it through** (the author, 2026-10-10). First record the answer where it belongs (FOUNDATIONS §4, the arc's dossier, ARCHITECTURE, the discussion), then remove the item, renumber the list, and fix every `README item N` reference elsewhere in `bible/`.
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
