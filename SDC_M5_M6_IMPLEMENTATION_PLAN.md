# SDC Pilot — M5/M6 Offline RAG System & PWA Implementation Plan

## Executive Overview & Architectural Decisions
The Sindhi Digital Classroom (SDC) pilot targets an offline-first RAG and curriculum exploration system for **Class 6 General Science (Sindhi medium, Sindh Textbook Board curriculum)**, designed for a **Raspberry Pi 5** server with zero internet connectivity and serving 1–2 GB RAM Android clients as an installable Progressive Web App (PWA).

### Canonical Source Files
Ingesting directly from `SDC_RAG_PACKAGE_for_Antigravity/m3/`:
1. `rag_chunks_sindhi.jsonl` — 90 chunks (Ch1–12), with Sindhi summaries, titles, and PDF/printed citations.
2. `sindhi_science_glossary.csv` — 201 bilingual science terms with Sindhi definitions and page citations.
3. `exercise_page_map.csv` — 39 exercise, SLO, review question, and practical rows with linked SOS video IDs.
4. `videos_final.csv` — 113 videos from Sindh Online School with lecture titles, duration, and URLs.

---

## Technical Architecture & Core Modules

### 1. Robust Unicode Normalization Engine (`src/services/sdc_rag_normalization.py`)
Applies the exact rules specified in the directive at index time and query time:
- **Heh Normalization**: Converts U+06BE (ھ) → U+0647 (ه) everywhere in Sindhi text fields. (e.g. `گھرڙو` -> `گهرڙو` so both spellings match in BM25 search).
- **Sentence Delimiters**: Normalizes ASCII periods (`.`) to Sindhi full stops `۔` (U+06D4), while preserving abbreviation dots like `ٽي.وی` (TV).
- **Kaf Conversion**: Converts Arabic Kaf `ك` (U+0643) -> Sindhi Kaf `ڪ` (U+06AA).
- **Word-Boundary Strictness**:
  - `اک` (Eye) is strictly differentiated from `اڪ` (Calotropis plant / milkweed).
  - Internal word patterns such as `خوراڪ` (food) and `آڪسيجن` (oxygen) remain untouched.
- **Citation Invariant**: Formats all citations as `"PDF X (printed Y)"` where `printed = pdf - 4`.
  - Chapter 7 displays the blank-PDF provenance note: `"PDF 83-95 (printed 79-91; blank in official PDF)"` with note `"Source: curriculum + SOS videos — Ch7 pages are blank in the official PDF"`.
  - Unverified pages display as `"page unverified"`.

### 2. SQLite Database Schema & FTS5 Ingestion (`src/services/sdc_rag_db.py`)
Dedicated SQLite database (WAL mode, synchronous=NORMAL, foreign keys enabled, cache size optimized for Pi 5 1-2GB RAM):
- `sdc_chunks`: `chunk_id`, `chapter_id`, `topic_title_en`, `topic_title_sd`, `pdf_page_range`, `summary_sd`, `source`, `normalized_summary_sd`, `normalized_title_sd`
- `sdc_glossary`: `id`, `chapter_id`, `term_en`, `term_sd`, `definition_sd`, `pdf_page`, `normalized_term_sd`, `normalized_definition_sd`
- `sdc_exercises`: `id`, `chapter_id`, `item_type`, `topic_en`, `pdf_page`, `sos_video_id`, `sos_video_title`
- `sdc_videos`: `id`, `chapter_id`, `title`, `watch_url`, `duration`, `audio_quality_notes`, `asr_suitability`, `source_status`
- **FTS5 Virtual Tables**:
  - `sdc_chunks_fts USING fts5(chunk_id UNINDEXED, chapter_id UNINDEXED, topic_title_en, topic_title_sd, summary_sd, tokenize='unicode61')`
  - `sdc_glossary_fts USING fts5(glossary_id UNINDEXED, chapter_id UNINDEXED, term_en, term_sd, definition_sd, tokenize='unicode61')`
- **Offline Vector Store Architecture**: Vector schema ready for CPU sentence-transformer/sqlite-vec, defaulting to high-speed zero-cloud BM25 retrieval with microsecond p95 latency.

### 3. SDC RAG Query & Inference Pipeline (`src/services/sdc_rag_service.py`)
Implements the RAG prompt specification:
- Formulates the exact prompt with Role, Instructions, Context chunks, and Question.
- Offline deterministic generative synthesizer producing fluent, accurate Sindhi answers strictly grounded in context with exact `PDF X (printed Y)` citations and Ch7 provenance banners.
- Support for query-time chapter filters (1–12).

### 4. Dedicated API Endpoints (`src/api/routes/sdc_rag.py`)
Mounted on `/api/sdc`:
- `GET /api/sdc/search`: Query search across chunks & glossary with optional `chapter_id` filter.
- `POST /api/sdc/ask`: RAG QA endpoint with grounded response synthesis and citations.
- `GET /api/sdc/glossary`: Browse/search 201 glossary terms filtered by chapter or alphabet.
- `GET /api/sdc/exercises`: Per-chapter review questions, SLOs, practicals, and video links.
- `GET /api/sdc/videos`: All 113 videos browsable by chapter.
- `GET /api/sdc/stats`: Database size, chunk counts, latency benchmarks.

### 5. Frontend Offline PWA (`static/sdc_classroom.html`, `static/js/sdc_app.js`, `static/css/sdc_style.css`, Service Worker)
4 Dedicated Screens tailored for Sindhi script (RTL) and low-resource Android devices:
1. **Search & Ask RAG Screen**: Sindhi & English query input, chapter pills (All, Ch 1–12), grounded AI answers, source chunks with citations, YouTube video preview/embed.
2. **Glossary Screen**: 201 bilingual terms with alphabet fast-indexer, search filter, and chapter grouping.
3. **Exercise Screen**: 39 exercises, review questions, and practicals per chapter with direct page references and video guides.
4. **Video Classroom Screen**: 113 Sindh Online School lessons organized by chapter.
   - Interactive YouTube Player modal rendering videos directly in the classroom.
   - Offline detection banner with "Watch when online" fallback indicator.
- Updated Service Worker caching app shell and IndexedDB caching for queries and student notes.

### 6. Comprehensive Acceptance Test Suite (`tests/test_sdc_m5_m6_acceptance.py`)
Validating all 6 acceptance tests from the directive:
1. **Heh-equivalence**: `گهرڙو` (U+0647) matches `گھرڙو` (U+06BE) in BM25 search.
2. **اک vs اڪ distinction**: `اک` (Eye) returns eye/sense-organ results, `اڪ` (Calotropis) does NOT return eye results.
3. **Both-numbers citations**: Every result formats `PDF X (printed Y)` with `Y = X - 4`, plus Ch7 blank-PDF provenance note.
4. **Chapter filtering**: Filtering works for all 12 chapters (including thin Ch6 with 5 videos).
5. **Full offline run on Pi 5**: Search, glossary, exercise index work with zero network.
6. **Report p95 latency + DB size**: Automated benchmark script measuring query latency and SQLite DB footprint.

### 7. Raspberry Pi 5 Deployment Artifacts
- `deploy/sdc-pilot.service`: systemd service configuration for auto-start.
- `deploy/install_pi5.sh`: Setup script for Raspberry Pi OS (ARM64).
- `README_PI5_SDC_PILOT.md`: Step-by-step instructions for offline Pi 5 deployment.
