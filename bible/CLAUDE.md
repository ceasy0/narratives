# Adonai — working rules for Claude

*Adonai* is the working title. A creative dramatization of the Bible: screenplays first, then a 3D animated series as the placeholder for an eventual live-action version. It expresses the author's understanding of Christianity. It is faithful to the spirit of the texts and never contradicts them.

## Read first

1. `canon/FOUNDATIONS.md`: the author's stance and every decision so far. It wins over other docs.
2. `canon/POSITIONS.md`: the Positions Register, every interpretive choice the story depends on.
3. `canon/FRAMINGS.md`: the author's unconventional framings, each with its fit grade and status.
4. `discussions/README.md`: which discussions are open, and what each one blocks.
5. `style/STORYTELLING.md`: the author's notes on how scenes should play. Apply them to every draft, along with `style/VOICES.md` (how each character speaks) and `style/LEXICON.md` (the word list).
6. `canon/RULES.md`: how the series is written: §3 (principles), §4 (provenance), §5 (language), §8.8 (the fit check). Where it conflicts with the files above, they win. The founding roadmap it came from is `archive/ROADMAP.md`, kept as the record.

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
| Where the project stands | `README.md`, "Status" | CLAUDE.md points to it |
| Past reviews and audits | `archive/` (dated records; their open calls are README items) | — |
| What changed, and when | git history (`git log -p <file>`) and the discussions' rounds | nowhere in the documents |
| The series as episodes | `story/ARCHITECTURE.md` | arc plans link to their section |

Record a decision once, in its home, and link from the rest. Don't paste it into a second file.

**Documents show the current state, not their history** (the author, 2026-10-13). When something changes, rewrite the passage so it reads as if it had always been that way; don't append a dated update, a "from vX to vY" table or a change log. A status line is one line: version, date, and what the document is now. History lives in git, and the reasoning lives in the discussions, whose rounds are kept in full. Fold new notes from the author into the section they belong to, by topic, rather than adding a section named for the date they arrived.

## Current phase

Where every piece stands (versions, what's next) is `README.md`'s "Status"; read it before starting. The working method:

- **The map** is `story/ARCHITECTURE.md`. Fill each episode first with what the Bible itself gives, runtime aside; contextual scenes fill the gaps later (the author, 2026-10-09). When an arc is treated, correct its lines in the map.
- **Writing front to end, treatments and beats first,** from Genesis 1 (the author, 2026-10-03 and 2026-10-05). Ruth is parked as a first draft; `story/arcs/07-ruth/README.md` says what's next for it.
- **The Opening (Gen 1:1–2:7) is the exception** (the author, 2026-10-07): it has a treatment, a script and an animatic ahead of the first pass. Its timings are the treatment's table; change the table, re-render. How the finished Opening gets made is `production/opening/PLAN.md`; what's placeholder in the animatic is `production/opening/README.md`.
- **The Garden (Gen 2:8–3:24)** is the rest of Episode 1, and its treatment is the next writing deliverable. Everything decided about it is in `story/arcs/01-beginnings/garden/DOSSIER.md`, with the research behind the look in `garden/LAYOUT.md`.
- **Sessions run on the author's computer when they can** (the RTX 2060 Super desktop, 32 GB RAM, Blender 5.0, FL Studio 2024 and 2025 installed; Python 3.14 with numpy and Pillow, run as `py`, since bare `python` is only the Store's placeholder; ffmpeg 9.0.2, installed with winget on 2026-10-08). Cloud sessions can't reach the prototype at `C:\Users\corbi\Personal\Current\Projects\Agentic\Biblical Story Concept`, Blender or FL Studio. The author has allowed installing video tools and anything else needed (2026-10-05). The animatic needs only Python, numpy, Pillow and ffmpeg.
- **Keep `README.md`'s "What I need from you" list current.** It is the one place the author tracks every open question, and everything open or needing the author goes there, including questions for later arcs (the author, 2026-10-11). **When a question is answered, delete it from the list; never strike it through** (the author, 2026-10-10). First record the answer where it belongs (FOUNDATIONS §4, the arc's dossier, ARCHITECTURE, the discussion), then remove the item, renumber the list, and fix every `README item N` reference elsewhere in `bible/`.
- **Commit and push after every round of edits** (the author's instruction, 2026-10-03). Git works in the projects folder on the author's SSD (`C:\Users\corbi\Personal\Current\Projects`) without extra flags.

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
- **One language rule** (confirmed by the author). English always stands for Israel's own language; sister dialects are accents; every other language follows the author's three tiers (RULES §5.7). Use "Yahweh" only in oaths and where the Name itself is the point (§5.5).
- **Non-English lines** always come with the original script, a transliteration, a literal back-translation and a confidence level. Flag reconstructed languages, especially first-century Galilean Aramaic, for specialist review.
- **Write decisions down.** Decisions go in `canon/FOUNDATIONS.md` or `canon/POSITIONS.md`, dated. Long conversations go in `discussions/`. Nothing important should live only in chat, because the next session won't see it.
- **Check citations.** Verify verse references, and flag anything stated with less than full confidence.
- **Say "kind," not "species,"** of Adam and Eve (the author, 2026-10-07): the change in them isn't bodily. They are "of one kind" (the author, 2026-10-08).
