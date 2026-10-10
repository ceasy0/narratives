# Project audit, 2026-10-10

*A dated record.* At your request ("Go over everything and analyze the project deeply for faults, inconsistencies, or errors"), every document under `bible/` was read in full, in five parts: the canon and discussions; the Opening (dossier, treatment, script, production notes and the animatic's code); Ruth (dossier, treatment, beats, storyboard, script and sketches); the map, roadmap, timeline, style docs and README; and the Garden. Every internal link and anchor was checked by script, and about 900 verse citations were checked. Line numbers below are from commit 1252ab3.

The questions only you can answer are in the [README](./README.md#what-i-need-from-you), items 2, 3, 11, 13 (extended) and 21–24, not here.

## What held up

- The map's arithmetic: hours 1–205 with no gaps or duplicates, season ranges joined end to end, hour numbers cited elsewhere matching v1.2.
- The Opening's table: fourteen beats summing to 5:00 with no gaps; beat numbers and titles agree across the treatment, the script, the code and the READMEs; the v3 file is 300.0 s at 24 fps.
- Ruth's tier counts (214 speeches: B 102, C 2, D 110) match the script, the beats and the treatment; "Yahweh" is spoken only in the two oaths; the 37-page claim holds (about 37.3 rendered).
- Position and FR numbers, the count of nineteen framings, and every `README item N` reference.
- Links: all resolve, except three to a `primordia` folder that isn't in the repo or on your drive (now plain text).
- Citations: one confident error found (below).

## Fixed in this pass

**Stale versions and status lines.** README's map version (v1.1 → v1.2), its "last session" line (and that main now matches the shared branch), the discussions row (003 and 004 were missing; 002's round 3 shown as waiting); the Opening treatment's own status (script v1.2, animatic v3); the Opening dossier's §6 (v3 added, ffmpeg, FL Studio edition known); the arc README's open items (adds items 2 and 20); code comments citing treatment v3.2; TIMELINE's status (v1.1); STORYTELLING's status; CLAUDE.md's phase date; FOUNDATIONS' change-log count ("six" lines → eight).

**Decisions shown as still open.** 007's Decision 1 and FOUNDATIONS still called the face-as-God's-image "my reading"; you confirmed it 2026-10-07. FRAMINGS FR-19 still asked whether the fitting form says what you mean (confirmed 2026-10-08); FR-18's 2:19 question (answered 2026-10-07); FR-01's Nile-as-Gihon (superseded 2026-10-08); FR-15's "nothing flies" (fixed 2026-10-05). POSITIONS row 23 now records the light version of 004 applied to Ruth. ARCHITECTURE and TIMELINE still said "your call" on Judges 17–21 (accepted 2026-10-08). FOUNDATIONS' FR-03 row now says its on-screen approach is proposed, to confirm before the Gospels (README item 17). The two other questions of 002's round 3 (the Isaiah 53 bridge, the Temple at twelve) were untracked; they're now in item 13.

**ROADMAP.** One note at the top lists the superseded sections (the old order of writing, the pilot animatic, the draft arc map, the register's move, depicting God, hardware), as REVIEW §2.3.2 asked; §8.3, §8.4, §10.3, §15's "filmable" rule (the Opening and visions exception), §17 Phase 0, §19.1 row 4 and the not-yet-existing `HARMONY.md` are marked in place.

**Numbers and citations.**
- 008: "Episode 1 to Episode 11" → 13 (Genesis 18 is hour 13 since v1.1); the answer on the animals of 2:19 is numbered 10, matching its question.
- 005: the Watchers are alluded to in Jude 6; Jude 14–15 quotes 1 Enoch 1:9, not chapters 6–16.
- ARCHITECTURE: "could fold into 174" → 176 (*The Temple Courts*); *Twins* is Gen 25:19–26:35; hour 6 runs to 11:3, which it cites; §6's letters table named two hours that don't exist (*Troas and Miletus*, *Antioch and Herod*); §10 calls hour 2 *Cain and Abel*; Abraham's line now names Season 2.
- TIMELINE: the Conquest ends c. 1380, as its own table and the map have it; Malachi c. 460–430 is "around", not "after", Ezra and Nehemiah.

**Ruth.**
- The treatment now quotes Ruth's 3:17 line, the market scene ("Do you know—") and the bread at dusk (Naomi alone) as the script has them.
- The treatment's and script's page tables agree with the beat sheet (Prologue 4, Act One 17 = Moab 10 + road and return 7, Act Four 5; they summed to 36 and 38).
- The Ruth README stated the Name rule from before 2026-10-01.
- The dossier now counts Yahweh 18 times (16 in speech, 2 by the narrator).
- STORYBOARD: P3 is the courtyard; 1.21's wind is from the east, at their backs (the script, the treatment and its east-wind thread); 3.8 is Naomi's house roofed again. Sketches 1.21 and 3.8 are redrawn to match.
- VOICES quoted a line of narration as Mr. So-and-so's dialogue.

## Sent to the Garden thread

The Garden's files belong to the Garden thread, so these went to it, with line numbers and suggested text. The two biggest:
- **The dates put Eridu before the Garden.** 008 has Eridu founded about 5400 BC and LAYOUT has its temple from about 5300 BC, but the Garden is placed about 5000–4000 BC "near where Eridu would stand."
- **Ezekiel 31:3–4 is about Assyria, pictured as a cedar in Lebanon**, so its "rivers flowing around" is an echo of Eden rather than a description of it, and the ring argument and the "Supported" grade lean on it.

Also: Ur measures about 19 km from Eridu, not 12; the Syrian elephant was in the wider region; and eleven small fixes (a stale §8 reference, an SVG label "wild" against "never wild", the ring sketch tagged P6 instead of P5, terraces drawn about 15% over scale, the cedar's range, Avestan and Old Persian run together, and the stale Garden status lines in README).

## Noted, for when the work reaches them

**The Opening's code**, to fix with the next render (item 21):
- the beat 9 cell is never lit and pops on at 2:46 (`beats_abstract.py`, `lit` keyed past the beat's end);
- the star's roar is cut off at 2:32 instead of dropping away;
- beat 1's flow starts at about 0:12.5, not 0:14;
- beat 4's faces dissolve about 3.5 s later than the script says;
- the falling sky's whistles never fire, and the flicker check tests 3:37–3:46 for a falling sky that isn't there;
- the "true silence" after the release has the release's reverb tail running into the note.

**Ruth**, small, at your pass on the script:
- Act Three ends on a line, where the beat sheet says every act break lands on an image, and the script has no fade there;
- "Naomi? It's Naomi. Elimelech's Naomi" is tagged as recorded, but only "Is this Naomi?" is in the text;
- "the text stops using her name" holds only for 1:5 (she's named again at 1:8);
- "Ruth comes right after Proverbs" is true of the Leningrad Codex, not of every Hebrew order;
- the dossier's status line is still v1.1.

**Canon and discussions:**
- 005 says the map marks the Watchers and the flight to Pella; the map doesn't mark either as 005's;
- 006 still asks what computer you have, and plans a Ruth animatic, both overtaken; it needs a dated note before its round 2;
- POSITIONS row 4 says the genealogies stay undated without mentioning the Garden's provisional 5000–4000 BC (README item 8);
- your delete-don't-strike rule is in CLAUDE.md but not in FOUNDATIONS §4.

**The map:**
- its status line and §10 disagree on how far your draft went (to Judges, or from Exodus on), and `Bible_Structure.md` isn't in the repository to check;
- seasons 16 and 23 have four hours, under the six-to-twelve rule.

**REVIEW.md:**
- it cites "README item 14" from an older numbering (left as is, since it's a dated record);
- its "two depths" proposal (§2.2) was never answered.
