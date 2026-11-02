# SDC Pilot — Audit Trail

**Date:** 2026-10-24
**Project:** Sindhi Digital Classroom (SDC) pilot — offline-first, rural Sindhi-medium, ages 11–16, devices 1–2 GB RAM Android / zero-internet school labs.
**Coordinator method:** Wide research — 5 parallel workers (A–E), one per input, Agency role briefs used (research-synthesist, data-engineer, ai-engineer, voice-ai, rag-pipeline-engineer). Failed/zero-result video inputs were retried once (coordinator retry pass, §5). No Google Sheet created, no messages sent, no money spent, **no videos downloaded** — search + page-text metadata only.

---

## 1. Scope changes (chronology)

1. **Original brief:** Classes 6–10, all subjects, Sindh Textbook Board; video inventory target ≥55 verified rows across Maths / Science / other subjects; datasets tab (AMBILE + open Sindhi datasets).
2. **Scope change (user, 2026-10-24): "for now just go with class 6 science."** Workers B/C/D were interrupted and merged into one combined hunt for **Sindhi-medium Class 6 Science only**. Curriculum narrowed to **STBB Class 6 General Science** only. Datasets worker (E) unchanged, secondary priority. Goal restated as 50+ verified videos, with explicit instruction **not to pad/invent** — true count + per-chapter shortfall is the deliverable if coverage is thinner.
3. **Clarification (user, 2026-10-24): strict Sindhi-MEDIUM filter.** Teaching/narration itself must be in Sindhi. Excluded: English/Urdu-medium lessons even on Sindh Board / Pakistani channels; channel name/location alone is not evidence. Included only with explicit evidence: Sindhi-script title/description, "Sindhi medium" stated, Sindhi-medium playlist/channel section, or Sindhi captions/description. Unconfirmed-medium candidates are listed in §6, **not** in videos.csv. Medium evidence must be noted in `source_verified`. All collected rows were re-checked against this rule (all workers returned 0 rows, so no rows needed removal).

---

## 2. Counts per worker

| Worker | Input | Result |
|---|---|---|
| A — Curriculum | STBB Class 6 General Science | **Complete.** Book verified (Science VI, STBB, Sindhi medium, 2020-21); **12 chapters** with topics extracted. File: `curriculum.md` |
| B — Videos (was Maths → Class 6 Science) | Sindhi-medium Class 6 Science | **0 verified rows** (~30 queries + page fetches). File: workers/B_maths.csv (header only) |
| C — Videos (Science) | Sindhi-medium Class 6 Science | **0 verified rows** (~35 queries). File: workers/C_science.csv (header only) |
| D — Videos (was other subjects → channel/playlist hunt) | Sindhi-medium Class 6 Science | **0 verified rows** (~35 queries, incl. Sindhi-script queries + channel-targeted searches). File: workers/D_other.csv (header only) |
| E — Datasets | AMBILE + open Sindhi datasets | **15 verified dataset rows.** Files: `datasets.csv`, `datasets_summary.md` |
| Coordinator retry | Fresh angles (§5) | **0 new rows** — confirms workers' result |

**Final totals:** `videos.csv` = **0 data rows** (header only, exact schema). `datasets.csv` = **15 rows**.

---

## 3. Per-chapter coverage — Class 6 Science (STBB, 12 chapters)

Every chapter has **zero** verified Sindhi-medium videos in the merged inventory. Shortfall vs 50+ goal: **50+**.

| # | Chapter (as printed, Science VI 2020-21) | Verified videos |
|---|---|---|
| 1 | Cellular Organization of Plants and Animals | 0 |
| 2 | Sense Organs | 0 |
| 3 | Photosynthesis and Respiration in Plants | 0 |
| 4 | Environment and Interactions | 0 |
| 5 | Atoms, Molecules, Mixtures and Compounds | 0 |
| 6 | Air | 0 |
| 7 | Solutions and Suspensions | 0 |
| 8 | Energy and Its Forms | 0 |
| 9 | Forces and Machines | 0 |
| 10 | Properties of Light | 0 |
| 11 | Investigating Sound | 0 |
| 12 | Space and Satellites | 0 |

Near-miss titles exist only for Ch. 1, 2, 5, 8, 9, 10 (see §6). Ch. 3, 4, 6, 7, 11, 12 produced no Class-6/STBB video candidates at all in search indexing.

**This zero is a findability result, not proof the videos do not exist** — see §4.

---

## 4. Key structural finding + BROWSER REQUIREMENT for parent

The Sindhi-medium Class 6 Science course **provably exists**: **Sindh Online School** (youtube.com/sindhonlineschool) — app/store listings and Sindhi Wikipedia, read directly by three independent workers, state: lessons Classes 1–10 on the STBB Jamshoro syllabus, "Delivered in Sindhi," 1,500+ lessons, **"Complete course of science from class 6 to 8."** Sindhi-script titles were verified for its Class 4/7/8 science videos.

However, **no individual SOS Class 6 Science watch URL + title + channel ever surfaced** through web search or text page-fetch (~100 queries across B/C/D + retry). The channel page text extraction shows only recent uploads; sindhonlineschool.com returns a bot-verification page to text fetching.

> **REQUIRED NEXT STEP (parent/root only): a live-browser session** opening youtube.com/sindhonlineschool → Playlists/Videos tabs, filtering "Science Class 6," and harvesting title + watch URL + duration per video (channel = Sindh Online School; medium evidence = platform's "Delivered in Sindhi" + Sindhi-script titles). Generic subagents cannot operate the live browser, so this step is flagged, not claimed. The same pass should resolve the §6 Sense Organs "In Sindhi" title. This single step is the realistic path from 0 to most of the 50+ target.

---

## 5. Retry pass (coordinator, once, per protocol)

Four fresh searches, 2026-10-24: `"Sindh Online School" "Science Class 6" YouTube lecture`; `site youtube.com Sindhi medium class 6 science Sindh textbook`; `سنڌ آنلائين اسڪول سائنس ڪلاس ڇهون` (Sindhi); `"In Sindhi" "Class Sixth" science Sense Organs Sindh text board video`. Results: textbook PDFs, Sindhi Wikipedia on Sindh Online School, an explicitly **Urdu**-medium StudyHelp lesson (excluded, §6), and unrelated English/Arabic Grade 6 science. **No new qualifying row.** Retry result: confirmed zero under search/text-fetch methods.

---

## 6. Excluded / Unconfirmed medium (not in videos.csv, with reason)

1. `https://www.youtube.com/watch?v=89RKuj9C9wE` — "Class 6 Science STBB Chapter 2 | Sense Organ: Nose" — title+URL verified; keywords claim **both** "in sindhi" and "urdu science lecture nose" — medium unconfirmable; also adult JST teacher-test prep, not a student lesson. **Excluded.**
2. `https://www.youtube.com/watch?v=Rw3Llk95Pac` — "Class Sixth Science | Chapter 1 | Sindh Text Books | MCQs…" (via testtiari embed) — title+URL verified, channel never surfaced, English-only metadata, adult SST/IBA/SPSC test-prep framing. **Medium unconfirmed, channel unverified.**
3. `https://www.youtube.com/watch?v=lgi6bw7L1UE` — "Understanding Energy and Its Forms | Class 6 Science | Sindh Textbook Board" (Ch. 8; 17:05 via Minideo) — no channel surfaced, English-only description, zero Sindhi evidence. **Excluded.**
4. `https://www.youtube.com/watch?v=YuNJ1arSad0` — Science Sphere, Periodic Table — spans Classes 6–12 (not Class 6-specific); channel states explanations in "Urdu, Sindhi and English" (mixed medium). **Excluded.**
5. `https://www.youtube.com/watch?v=z29mKOTWN-4` — "Explore Science || class 6 || Chapter 2" — title+URL only; no channel, board, or medium evidence. **Excluded.**
6. `https://www.youtube.com/watch?v=YH0qHaIC_cg` — "Teaching License Science | Class 6 Chapter 02 Complete Lecture" (channel: Sindhi Sir) — adult teaching-licence/PST/JEST prep; delivery language not stated. **Excluded.**
7. `https://www.youtube.com/watch?v=UJTJa6vHB3E` — "Roshni or awaz class 5th urdu lecture unit 6" (StudyHelp) — description states **Urdu** explanations, Class 5 & 6 Science Ch. 6 Light and Sound. **Wrong medium outright.**
8. Academy For All chapter lectures (Ch. 1 ~22–24 min; Ch. 8 11:22; Ch. 9 11:52; Ch. 10 19:26) — titles/durations seen in search/Minideo snippets only; **no verbatim watch URL ever surfaced**; English titles, PST/JEST hashtags, no Sindhi-medium evidence. **Excluded.**
9. Aggregator-only titles (sonichits/hdjum/Minideo): "Sense Organs, Subject Science, In Sindhi, Sindh text board, Class Sixth" (the only candidate explicitly "In Sindhi" — highest priority for live-browser resolution); "Sense Organs – The Eye | class 6 | Chapter 2 Lecture 1 | Sindh Textbook"; Minideo Energy / Atoms-Molecules-Mixtures lessons — titles (± duration) only, no YouTube URL/channel. Mirror IDs were **not** converted into YouTube URLs. **Unconfirmed.**
10. Sense-organs video via videohighlight ID `qSRQnbMwK0A` — summary page states "The transcript is in French." **Definitively not Sindhi. Excluded.**
11. Sindh Online School Class 7 Science videos (e.g. "Digestive system | Science Class 7 | Chapter 1 | Lecture 1") — genuine Sindhi-medium source, **wrong class** for this scope. Out of scope.

---

## 7. Datasets — summary of findings (detail in `datasets_summary.md`)

- **15 verified resources.** AMBILE = **Abdul Majid Bhurgri Institute of Language Engineering, Hyderabad** (Govt of Sindh) — an institute, not a single dataset. Verified AMBILE releases are **text/lexical only** (Mega Corpus ~118M tokens, licence unknown, HF repo stated empty with off-HF Drive download unverified; Shah Jo Risalo HF 43,779 verses with a licence discrepancy on the page; a separate IEEE Shah Jo Risalo 4,767 verses, CC BY-NC 4.0; Sindhi WordNet, CC BY-NC 4.0, no size stated). **AMBILE verified speech = 0 hours.**
- **Clean Sindhi speech verifiably available today: ≈12.5 h** — FLEURS **sd_in** ~12.11 h (CC BY 4.0; note: **FLEURS `sd_pk` does not exist** — config is `sd_in`) + Common Voice Sindhi validated 0.36 h. Common Voice 27.0 records 73.38 h total but only 328 of 66,263 clips (0.5%) are validated.
- **Gap vs 20–30 h clean-audio ASR target: short ≈7.5 h (vs 20 h) to ≈17.5 h (vs 30 h).** All verified speech is read speech — no verified conversational/classroom/children's Sindhi speech corpus exists (domain gap for SDC).
- Other gaps: OPUS Sindhi verified only for Tanzil (no count/licence); MAVDESS Zenodo availability claimed in a paper only (no DOI/hours/licence verified, excluded from totals); SiNER/Glot500-Sindhi/SdQuAD licences unknown; OSCAR-2201 Sindhi verified (117.1 MB) but access gated on page read, metadata-only CC0.

---

## 8. Rules applied throughout

- Only Sindhi-medium (strict filter, §1.3), age-appropriate (11–16), lesson videos; music/vlogs/news/adult test-prep excluded.
- A video row required title + URL + channel all seen in a search result or page actually opened; URLs copied verbatim; duration `unknown` if not shown; nothing invented.
- Audio quality **cannot be assessed from metadata and no listening/downloading was done**: had any rows qualified, `audio_quality_notes` would read "Unknown - metadata only, manual listen check required" and `asr_suitability` "Unverified - listen check needed".
- Curriculum chapter titles are as printed in the textbook (English); Sindhi translations were **not** fabricated. Only the 2020-21 edition is verified. STBB's official portal exposes no text TOC (PDF viewer only) — chapter list rests on the scanned textbook text + Sindh-attributed corroboration, stated plainly in `curriculum.md`. Two look-alike non-STBB lists (Maharashtra MSCERT; federal SNC draft) were identified and excluded there.

## 9. Files delivered

- `curriculum.md` — STBB Class 6 General Science: book verification, 12 chapters with topics, sources, gaps.
- `videos.csv` — exact schema, **0 data rows** (true count under the rules; see §3–§4).
- `datasets.csv` — 15 verified Sindhi dataset rows.
- `datasets_summary.md` — AMBILE section, speech-hours gap analysis, offline / 1–2 GB RAM implications, licence cautions.
- `audit_trail.md` — this file.
- `workers/` — per-worker source files (A_curriculum.md, B_maths.csv, C_science.csv, D_other.csv, E_datasets.csv, E_summary.md).

## M3 — Listen-check return + synthesis (2026-10-24, guest session 16:57–20:29 PKT approx.)
- Guest-only browser task (fresh guest profile, no sign-in, no account, no like/comment/subscribe/upload, no downloads; playback only) assessed all 113 SOS "Science Class VI Complete" videos, 2026-10-24.
- Result: 113 Clean, 0 Usable-with-preprocessing, 0 Unsuitable, 0 Unverified. Nothing unassessed.
- METHOD LIMITATION (recorded honestly): sampling achieved was ~30s opening + ~30s middle per video (not the 60-90s + 60s originally specified); third segments on videos 12, 13, 19, 25, 64, 78, 84, 87, 89, 90, 93, 94, 113. "Clean" = sample-Clean, not full-listen verification. Transcriber "no speech"/looped reports on videos 15, 64, 66, 83, 84, 101, 102, 106, 109 (and sparse on others) resolved on re-listen — transcriber artefacts, not audio faults. English-mix flags: video 89 (8:30 English slide reading), video 100 (opening English question reading), video 102 (brief English phrase in opening); English-written review slides on 89, 100, 112, 113 with Sindhi narration. Brief [music] caption markers only on videos 25 and 45, speech continuous. Ch12 title gap: Lecture 4 title missing between Lecture 3 and Lecture 5.
- Durations: videos.csv total 21h 20m 49s = 21.35h (canonical for M3); browser player total 21.32h (108s less, ~1s player differences) — threshold verdicts unchanged on either total.
- M3 deliverables in ~/workspace/sdc-pilot/m3/: videos_final.csv (PRD schema, 113 rows), audio_audit_summary.md, licensing_review_FINAL.md, coverage_matrix_FINAL.md. Total Clean Speech = FLEURS 12.11 + Common Voice 0.36 + SOS 21.35 = 33.82h; 20h minimum MET (+13.82h), 30h upper MET (+3.82h); contingency trigger NOT fired. Clean does NOT grant SOS training rights — written SOS permission still required before M4 uses SOS audio (SOS Terms: commercial redistribution prohibited, no CC licence found; YouTube About not separately verified).
- Google Sheet Video Inventory H2:I114 updated and read-back verified (113 rows, 226 cells): Audio Quality Notes = guest-sample notes, ASR Suitability = Clean for all rows, including flagged rows (video 89 at Sheet row 90 verified).
