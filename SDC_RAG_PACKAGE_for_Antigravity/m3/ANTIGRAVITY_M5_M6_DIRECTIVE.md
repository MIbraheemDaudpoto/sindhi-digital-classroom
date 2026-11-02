# Antigravity Directive — SDC M5/M6: Offline RAG Backend + PWA (Track 1, independent of audio ratings)
Project: Sindhi Digital Classroom (SDC) Pilot, Class 6 Science, Sindhi medium, STBB curriculum.
Target hardware: Raspberry Pi 5, OFFLINE, zero-internet school labs, 1-2 GB RAM Android clients via PWA.
Status: This track does NOT wait for the listen-check / M3 audio ratings. Build now from the files below.
Canonical input files (ignore any "(1)" / "(3)" download-duplicate suffixes — these are the originals):
- rag_chunks_sindhi.jsonl — 90 chunks (workspace/sdc-pilot/m3/rag_chunks_sindhi.jsonl)
  Fields: chunk_id, chapter_id, topic_title_en, topic_title_sd, pdf_page_range, summary_sd, source
- sindhi_science_glossary.csv — 201 rows (workspace/sdc-pilot/m3/sindhi_science_glossary.csv)
  Fields: term_en, term_sd, definition_sd, pdf_page
- exercise_page_map.csv — 39 rows (workspace/sdc-pilot/m3/exercise_page_map.csv)
  Fields: chapter_id, item_type, topic_en, pdf_page, sos_video_id, sos_video_title
- videos.csv — 113 SOS videos (workspace/sdc-pilot/research/videos.csv)
  Fields: title, url, channel, duration, grade_level, subject, curriculum_topic_match, audio_quality_notes, asr_suitability, source_verified
  NOTE: audio_quality_notes / asr_suitability in videos.csv are STILL "unknown/unverified" until M3 lands. Do NOT display audio-quality badges from this file yet; M3 will supply the finalized PRD-schema videos.csv separately.

## What to build
1. FastAPI backend (Python, lightweight — must run on Pi 5 alongside the retriever, no GPU, no cloud calls).
2. SQLite database with:
   - FTS5 full-text index over summary_sd + topic titles + glossary definitions (BM25 ranking).
   - sqlite-vec (or equivalent lightweight vector table) over chunk embeddings — embeddings must be generatable OFFLINE on the Pi (small multilingual embedding model, e.g. a compact sentence-transformer that runs on CPU; if no suitable offline Sindhi embedding is available, ship BM25-first with the vector table schema ready and document the gap — do NOT call a cloud embedding API at query time).
   - Tables: chunks, glossary, exercises, videos (with chapter_id 1-12, pdf_page, printed_page parsed from the citation strings).
3. PWA UI (installable, works offline after first load, Sindhi-script friendly):
   - Search bar (Sindhi + English), chapter filter 1-12, results as: Sindhi summary, English topic title, chapter, citation, linked SOS video (open YouTube link only when online; offline, show title + "watch when online" — never bundle video files).
   - Glossary lookup, exercise index per chapter (review questions / summaries / practicals / projects with PDF page + video link).
   - Every answer/result MUST show its citation in BOTH forms, e.g. "PDF 24 (printed 20)" — students/teachers use the printed page in the physical book.

## Sindhi search normalization — MANDATORY, apply at index AND query time (identical function both sides)
- Normalize Heh: U+06BE (ھ) -> U+0647 (ه). The corpus is already normalized to ه (گهرڙو, not گھرڙو); a query typed either way must match.
- Normalize sentence delimiters: treat ۔ (U+06D4) and "." as equivalent delimiters in tokenization; do not let a trailing period/full-stop break a match.
- Do NOT normalize اک (Eye) and اڪ apart — they are DIFFERENT words (اک = Eye, اڪ would be the milkweed plant). The corpus uses اک for Eye and ايڪو for "unit"; keep them distinct in the index. Likewise خوراڪ (food) and آڪسيجن (oxygen) must stay intact.
- Arabic kaf ك must never be conflated with Sindhi ڪ in matching: normalize any query-side ك to ڪ before lookup.
- Case-fold English terms; keep Sindhi script in UTF-8 throughout (no transliteration, no Roman Urdu output).

## Content rules (do not break these)
- NO verbatim textbook text is in the inputs and none may be generated: summaries/definitions are original paraphrases. Do not reconstruct book pages from chunks.
- NO query-time VLM / screenshot reading in the retrieval path. Retrieval = text chunks + page citations only.
- Chapter 7 flag: chunks with pdf_page_range "PDF 83-95 (printed 79-91; blank in official PDF)" come from curriculum SLOs + SOS videos, NOT from the PDF. Display that provenance on Ch7 results (e.g. "Source: curriculum + SOS videos — Ch7 pages are blank in the official PDF").
- "unverified" pages (20 glossary rows, 2 exercise rows) must display as "page unverified" — never invent a page number.
- Licensing: SOS videos are LINKED only. Do NOT download, cache, or redistribute SOS video/audio in the PWA, and do NOT use SOS audio for model training — SOS Terms prohibit commercial redistribution and no CC licence was found; audio-training rights need SOS written permission (separate M4 track). This M5/M6 build is text-RAG + links only.

## Acceptance tests (must all pass before handoff)
1. Query "گهرڙو" (with standard ه) returns the cell chunks; query "گھرڙو" (with ھ) returns the SAME chunks.
2. Query "اک" returns eye/sense-organ results; query "اڪ" does NOT return eye results (different word).
3. Every search result shows "PDF X (printed Y)" with Y = X - 4, and Ch7 results show the blank-PDF provenance note.
4. Chapter filter 1-12 returns only that chapter's chunks/glossary/exercises; Ch6 (thinnest: 5 videos) still returns its chunks.
5. Full backend + PWA runs offline on a Pi 5 with no network: search, glossary, and exercise index all work; video links degrade gracefully to title-only when offline.
6. Startup time and per-query latency on Pi 5 are reported (p95), and total DB size is reported — both must be plausible for a Pi 5 + 1-2 GB RAM clients.

## Deliverables back to SDC
- Source code + README (how to build the DB from the 4 input files, how to run FastAPI + PWA offline on Pi 5).
- The built SQLite DB (or a reproducible build script + the DB).
- Acceptance-test report (the 6 tests above, with numbers).
- Open gaps list (e.g. offline embedding model choice, if BM25-only at first).
