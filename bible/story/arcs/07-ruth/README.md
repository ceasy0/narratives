# Ruth — Pilot Plan

> How we'll write the pilot, step by step: which files, what goes in each, and where you review.

**Status: parked, 2026-10-03.** You've said Ruth is good for what it is, that your remaining changes are small, and that expansions can be discussed later, once more of the broader story is laid out. The work has moved to [Genesis](../01-beginnings/README.md). What follows is where Ruth stood when it was parked. The [dossier](./DOSSIER.md) is done, and the whole-Bible chronology is decided ([`world/TIMELINE.md`](../../../world/TIMELINE.md)). The [treatment](./TREATMENT.md) is at v4, with three rounds of your notes applied. The [beat sheet](./BEATS.md) and a complete **first-draft script** ([`scripts/ruth/ruth.fountain`](../../../scripts/ruth/ruth.fountain)) are written. **Next: your pass on the script.** For why Ruth is the pilot, see ROADMAP §11.4.

---

## The files

| Step | File | Format | What's in it |
|---|---|---|---|
| 1 | [`DOSSIER.md`](./DOSSIER.md) ✓ | Markdown | Everything we need to know before writing. Built so that it also teaches you the story. |
| 2 | [`TREATMENT.md`](./TREATMENT.md) ✓ v4 | Markdown, in prose | The whole episode told as a short story (roughly 3–8 pages): what happens, how it's shaped, and what it means |
| 3 | [`BEATS.md`](./BEATS.md) ✓ v1 | Markdown | The structure scene by scene, Naomi's arc marker by marker, and the pacing, with page numbers from the draft |
| 4 | `SCENES.md` | Markdown | One scene card per scene (template in ROADMAP §13.2). **For the pilot, the story side is folded into the beat sheet,** and the production side (props, costumes, light) waits until the script is locked, so it's written once from the final scenes. |
| Test | `scripts/ruth/sample-the-road.fountain` ✓ | Fountain | One scene written as a script before the beat sheet, to test how the dialogue sounds. Your notes on it went into the full script, which now contains the scene, so the sample was retired; it's in the git history. |
| 4b | [`STORYBOARD.md`](./STORYBOARD.md) ✓ v1 | Markdown + PNG | **New, 2026-10-08:** sixteen key frames as blocked compositions, drawn in code (`storyboard/draw.py`), with shot notes and two proposed rules. Sketches, not a full board, since Ruth may still change. |
| 5 | [`scripts/ruth/ruth.fountain`](../../../scripts/ruth/ruth.fountain) ✓ first draft | Fountain (`.fountain`) | The screenplay, 37 pages. It's plain text that renders to standard screenplay format, and every line carries a hidden `[[tag]]` saying where it came from. The tier mix is at the end. |
| Alongside | [`style/VOICES.md`](../../../style/VOICES.md) ✓ v1, [`style/LEXICON.md`](../../../style/LEXICON.md) ✓ v1 | Markdown | How each character speaks, and the rules for words and idioms. These start with Ruth and grow throughout the series. |

The files get created one at a time, in order. You can read the Markdown files on GitHub or in any editor. For the `.fountain` script, use a screenplay app such as Highland, Beat or Slugline, or the free command-line tool `afterwriting`, which makes a PDF.

---

## What goes into each step

### 1. Dossier

- **The story in plain words.** A short retelling, for reading before anything else.
- **A full working translation of all 85 verses.** I'll translate it myself from the Hebrew and check it against several published translations, with notes on the choices I make. This becomes the base for every recorded line of dialogue (Tier B). There's no Tier A in Ruth, because God never speaks.
- **Textual notes.** These cover places where the manuscripts or the written and spoken Hebrew traditions differ. In 4:5, for example, the written Hebrew reads "I acquire" Ruth, while the traditional reading says "you acquire" her. That changes how the scene at the gate plays.
- **The literary design:**
  - the word "return," which repeats through chapter 1;
  - *hesed* (loyal kindness);
  - the "wing" (2:12 and 3:9);
  - "worth" (2:1 and 3:11);
  - "chance" (2:3);
  - Mr. So-and-so (4:1);
  - the two moments where the narrator says God acted (1:6 and 4:13).
- **The world:**
  - famine and migration;
  - the history between Moab and Israel, including Gen 19:37, Num 25 and Deut 23:3;
  - widowhood;
  - gleaning (Lev 19:9–10; Deut 24:19–22);
  - the kinsman-redeemer (Lev 25);
  - levirate marriage (Deut 25:5–10, and Judah and Tamar in Gen 38, which Ruth 4:12 cites);
  - the barley and wheat harvests, which fall between Passover and Pentecost;
  - winnowing at night on the threshing floor;
  - the legal assembly at the city gate;
  - the custom of the sandal (4:7);
  - houses, clothing and food in the hill country of Judah around 1100 BC;
  - the road between Moab and Bethlehem.
- **What they knew that we don't, and what we know that they didn't.**
- **The interpretive puzzles:**
  - what happens on the threshing floor ("uncover his feet," 3:4–7);
  - Naomi's motives;
  - Orpah;
  - why the nearer kinsman refuses;
  - how old Boaz is.
- **The framings and decisions that apply:**
  - FR-08 (Boaz as Ruth's opposite);
  - Discussion 001 (Ruth as the book where God works through people);
  - God's name used in full (Ruth 2:4);
  - the light version of "God among the nations" (Moab and Chemosh).
- **Open decisions, each with my recommended default** (see the table below).

**Checkpoint:** you read the dossier, flag anything that doesn't sit right, and answer the open decisions.

### 2. Treatment

The episode written as prose. I'll offer two or three options for where the story opens, and I'll mark every addition with its source level (P4–P6) and how it passes the addition test.

**Checkpoint:** you react. This is the cheapest stage at which to change anything big.

### 3–4. Beats and scene cards

The structure, then a card for each scene. Each card records:
- its purpose;
- what the original audience would have felt;
- what they knew that we don't;
- any additions;
- the mix of dialogue tiers;
- production notes such as props, costumes, location and time of day.

**Checkpoint:** you approve the structure.

### 5. Script

A first draft in Fountain at setting 2 (plain modern English), with every line tagged. You then rewrite whatever you want, probably most of the dialogue. After that I:
- compare my draft with your version and write down the patterns in `style/`;
- ask about anything I can't interpret;
- run the audit checklist (ROADMAP §13.4);
- fit-check any new interpretation your edits introduce.

Then we lock the script.

---

## Decisions the pilot needs

*Updated 2026-10-02 (round 3). The details are in [DOSSIER §12](./DOSSIER.md#12-decisions-for-you). The treatment's own choices are in [TREATMENT §6](./TREATMENT.md#6-choices-for-you).*

| Decision | Status | Needed by |
|---|---|---|
| Format | **Decided:** one episode, with a prologue and four acts, one for each chapter. The first-draft script runs 37 pages, about 40 to 45 minutes ([BEATS §1](./BEATS.md#1-the-shape)). | Treatment |
| Where the story opens | **Decided:** Bethlehem during the famine, with a glimpse of Boaz as the one who stays. The treatment offers three ways in. | Treatment |
| Boaz's mother | **Decided by the chronology:** Rahab is his ancestor several generations back, remembered but not seen (DOSSIER §5) | Treatment |
| Moab's religion on screen | **Decided:** sincere and textured | Treatment |
| Ruth's first marriage | **Decided** (FR-08): real and loving on her side, but unfinished | Treatment |
| The threshing floor (3:1–14) | **Default:** keep the text's charged ambiguity, resolved toward honor. It can be intense, but not explicit (principle 8). | Scene cards |
| Ruth's speech | **Decided by the series rule** (ROADMAP §5.7), which you confirmed 2026-10-02: English with a Moabite accent, all the way through | Treatment |
| 1:13 | **Decided 2026-10-02:** the most likely reading, "far more bitter for me than for you" ([TREATMENT §7](./TREATMENT.md#from-your-notes)) | Script |
| Expansions | **Decided 2026-10-02:** the friend names Obed, Boaz's hesitation, Mr. So-and-so's son, and Naomi's lullaby. Orpah and Chilion stay a gap to explore later. | Script |
| The David connection | **Deferred** until more of the story exists. The last shot rests on Obed's face so a flash-forward can be added later ([TREATMENT §7](./TREATMENT.md#for-later-arcs)). | Before lock, or later |
