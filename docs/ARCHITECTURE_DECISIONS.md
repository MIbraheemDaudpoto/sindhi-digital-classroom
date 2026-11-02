# Sindhi Digital Classroom (SDC) - Architecture Decision Log (ADL)

Authored under **agency-software-architect** and **agency-software-security-engineer**.  
Date: 2026-10-16  
Status: Authoritative Engineering Decision Log for SDC Project Stakeholders  

---

## Decision 1: SQLite WAL Mode vs. PostgreSQL + pgvector (Embedding & Vector Storage)

- **PRD / Architecture Conflict:**
  - PRD Section 11 / Cloud Architecture earlier proposed PostgreSQL with the `pgvector` extension for storing and performing high-dimensional cosine similarity searches over lesson text embeddings.
  - The repository implementation currently uses **SQLite in Write-Ahead Logging (WAL) mode** with an in-memory/regex STBB chunk keyword-matching index in `src/services/ai_tutor_service.py`.
- **Available Evidence:**
  - SQLite WAL mode is zero-dependency, operates reliably on low-resource hardware, supports fast local concurrent reads, and is embedded directly inside the application container without requiring a managed cloud database.
  - SDC targets rural school deployments and offline edge environments where reliable broadband connectivity to a central cloud PostgreSQL cluster is intermittent or non-existent.
  - Current lesson volume (Sindh Textbook Board Classes 6–10, 4 subjects, ~40 units) totals under 500 pedagogical chunks, making full vector indexing overhead disproportionate for initial pilot stages.
- **Architectural Options:**
  1. *Option A (Recommended for Pilot / Edge):* Retain SQLite WAL for relational data, attempts, and transcripts. Use an embedded vector search engine (e.g., `sqlite-vss` or local `faiss-cpu`/`chromadb` embedded) when semantic vector search becomes necessary.
  2. *Option B (Cloud Centralization):* Migrate backend persistence to managed PostgreSQL with `pgvector` hosted on cloud infrastructure (e.g., Supabase / AWS RDS).
- **Risks:**
  - Option A: Cannot scale to millions of concurrent cloud users on a single node without read-replicas (LiteFS/Turso).
  - Option B: High operational overhead, recurring cloud cost, and complete failure of tutor/quiz services when school connectivity is severed.
- **Approval Authority:** Lead Software Architect & SELD Technical Project Director.

---

## Decision 2: Online-Only AI Tutor vs. Scoped Offline Lesson Search

- **PRD / Architecture Conflict:**
  - FR-20 to FR-25 specify a Grounded Sindhi AI Tutor that answers questions from STBB lesson chunks.
  - FR-32 specifies downloading unit packs for 100% offline use.
  - Currently, `/api/tutor/ask` requires an active server connection. Offline unit packs contain lesson transcripts and text chunks in IndexedDB, but the client does not yet execute in-browser semantic search over those offline chunks.
- **Available Evidence:**
  - Running a large LLM (e.g. 7B+ parameters) entirely in a client mobile browser (WebLLM/ONNX) on entry-level Android devices (2GB–3GB RAM) used by rural students causes out-of-memory crashes and severe thermal throttling.
  - STBB approved lesson chunks are already packaged into offline JSON unit packs (`saveUnitPackOffline`).
- **Architectural Options:**
  1. *Option A (Recommended Tiered Approach):*
     - **Online:** Full RAG pipeline querying `/api/tutor/ask` with semantic retrieval.
     - **Offline:** Client-side keyword/BM25 search over the cached unit pack transcripts in IndexedDB, returning exact timestamped video citations and text snippets without generative synthesis.
  2. *Option B (Strict Online-Only):* Disable the AI Tutor tab completely when `navigator.onLine === false` and show an offline notice.
- **Risks:**
  - Option A requires maintaining a lightweight client-side search indexer in JavaScript (`lunr.js` or `minisearch`).
  - Option B frustrates rural students who study offline without connectivity.
- **Approval Authority:** Curriculum Lead & Product Manager.

---

## Decision 3: Interactive Video Quiz Policy: Mandatory Answer vs. Permitted Skip

- **PRD / Architecture Conflict:**
  - FR-14 states: *"Pause video at set points; student must answer to continue."*
  - The prototype video player (`static/js/player.js`) implements a *"Skip & Continue"* button (`skipQuiz()`) allowing students to bypass the quiz without submitting an answer or penalty.
- **Available Evidence:**
  - In formative learning research, forcing an answer prevents students from abandoning lessons when stuck on difficult questions, but allowing unrestricted skipping encourages students to skip all pop-up checks to reach the end.
  - Pedagogical pilot goals require measuring active engagement and comprehension before proceeding to new lesson topics.
- **Architectural Options:**
  1. *Option A (Configurable by Teacher):* Default to mandatory answer (no skip button) for formal chapter reviews; allow 1 skip per lesson for formative video pauses, recording a `SKIPPED` attempt in the audit log.
  2. *Option B (Strict PRD Compliance):* Remove the skip button entirely. Video remains paused until an option is selected.
  3. *Option C (Retry after Clue):* If student is stuck, offer a "Review Previous 30 Seconds" button that seeks back and replays the explanation rather than skipping.
- **Risks:**
  - Option B may cause students to get stuck and abandon playback if they do not know the answer.
  - Option C provides the best learning outcome while preserving mandatory completion.
- **Approval Authority:** SELD Pedagogical Advisory Committee & Lead Product Manager.

---

## Decision 4: ASR & TTS Providers, Sindhi Capability, and Child Audio Handling

- **PRD / Architecture Conflict:**
  - FR-20 specifies *"Tap microphone, speak Sindhi question, see text."* FR-22 specifies *"Spoken Sindhi reply (TTS)."*
  - The repo currently relies on client-side browser Web Speech API (`webkitSpeechRecognition(lang='sd-PK')`) with heuristic fallbacks, and Web Speech Synthesis (`SpeechSynthesisUtterance(lang='ur-PK')`).
  - Real Sindhi speech recognition on rural Android devices frequently fails because Google Speech Services has poor or missing offline Sindhi acoustic models.
- **Available Evidence:**
  - No dedicated fine-tuned Whisper-Sindhi or Meta MMS ASR model is hosted on the backend server.
  - Streaming minor child voice audio to public external APIs (OpenAI Whisper API, Google Cloud) without localized data residency agreements violates international child privacy laws (COPPA, GDPR-K) and SELD child protection frameworks.
- **Architectural Options:**
  1. *Option A (Self-Hosted Edge ASR):* Deploy a containerized, self-hosted Whisper-small / MMS-Sindhi model on the school local server or SELD sovereign cloud; client sends audio strictly to internal sovereign endpoint.
  2. *Option B (Browser-First with Editable Fallback):* Keep the current editable text box (FR-21) as primary, relying on keyboard/touch input in Sindhi script with optional browser voice dictation when supported.
- **Risks:**
  - Option A requires server GPU or optimized ONNX CPU runtime on deployment hardware.
  - Option B places typing burden on young rural students with low digital literacy.
- **Approval Authority:** SELD IT Security Officer & AI Engineering Lead.

---

## Decision 5: Student Audio Retention, Deletion, and Guardian Consent Governance

- **PRD / Architecture Conflict:**
  - Schema defines `audio_samples` and `consents` tables for speech fine-tuning datasets.
  - PRD emphasizes strict child privacy and zero PII.
  - There is currently no automated time-to-live (TTL) expiration or explicit guardian consent verification workflow before audio collection.
- **Available Evidence:**
  - Under UNICEF and COPPA child data guidelines, raw biometric voice recordings of children under 16 cannot be stored indefinitely and must not be collected without verified parental/guardian consent.
- **Architectural Options:**
  1. *Option A (Zero Audio Persistence - Safest):* Audio processed in-memory for real-time transcription and immediately discarded. Never write student audio files to disk.
  2. *Option B (Consented Research Corpus with 90-Day TTL):* Only store audio if an active record exists in `consents` with `is_granted = 1` and `scope = 'SPEECH_TRAINING'`. Auto-purge audio files older than 90 days via scheduled cron job.
- **Risks:**
  - Option A prevents building a fine-tuning dataset to improve rural Sindhi ASR dialects.
  - Option B carries legal compliance overhead and requires parental consent collection forms in Sindhi.
- **Approval Authority:** SELD Legal Counsel & Child Data Privacy Officer.

---

## Decision 6: Offline Conflict Policy: Quiz Attempts vs. Progress Checkpoints

- **PRD / Architecture Conflict:**
  - When devices are offline for multiple days and synced later, quiz attempts may arrive out of order, or multiple devices used by the same student may submit conflicting progress bookmarks for the same lesson.
- **Available Evidence:**
  - Quiz attempts are discrete immutable events (`INSERT INTO attempts`).
  - Lesson progress is a continuous state (`INSERT OR REPLACE INTO progress` with `last_position_seconds` and `is_completed`).
- **Architectural Options:**
  1. *Option A (Deterministic Domain Rules - Implemented):*
     - **Attempts:** Append-only with client-side UUID and idempotency check (`question_id` + `client_timestamp`). Never overwrite attempts.
     - **Progress Checkpoints:** High-water mark rule: `is_completed` is sticky (once completed, never revert to incomplete). For `last_position_seconds`, accept `MAX(client_position, stored_position)` or the latest timestamp.
- **Risks:**
  - Client clock drift on rural devices could distort timestamp ordering if device clocks are unsynchronized (mitigated by using server receipt time alongside device time).
- **Approval Authority:** Backend Architect & QA Lead.
- **Batch 3 Resolution (Verified):** Implemented in `src/services/sync_service.py` using `INSERT OR IGNORE INTO attempts` and `last_position_seconds = MAX(progress.last_position_seconds, excluded.last_position_seconds)`. Automated regression tests passed in `tests/test_offline_sync.py`.

---

## Decision 7: Session Token Expiration & Shared-Device Account Isolation

- **Context / Threat Model:**
  - In rural Sindh schools, tablets and Chromebooks are shared across multiple students and teachers throughout the school day.
  - Previous tokens were static strings without embedded timestamps or server-side expiration validation, creating session hijacking risks if a student left their browser open or switched accounts.
- **Architectural Decision:**
  - **Embedded Epoch Timestamp:** Auth tokens now follow the deterministic format `sdc_{role}_{user_id}_{epoch}_{rand}`.
  - **24-Hour Session TTL:** Enforced in `src/api/deps.py`. Any token timestamp older than 86,400 seconds is rejected with HTTP 401 and a localized Sindhi prompt to re-authenticate.
  - **Shared-Device Queue Flushing:** Prior to switching active user session (`switchUserRole`), the client triggers `flushOfflineSyncQueue()` to ensure no queued attempts from the outgoing student leak into or sync under the incoming student's identifier.
  - **IndexedDB Isolation:** All records in `sync_queue` and `offline_progress` are partitioned by `user_id`. Queries and clears strictly filter by active `currentUser.user_id`.
- **Status:** **Verified** via `test_expired_token_rejected` and `test_cross_school_teacher_isolation`.
- **Approval Authority:** Application Security Engineer & Lead Architect.

---

## Decision 8: Teacher Assignment Workflow & Manual Grading Architecture (FR-28)

- **Context / Requirement:**
  - FR-28 requires teachers to issue assignments with due dates, description in Sindhi, and assign marks with qualitative feedback.
  - Previous architecture only accommodated automated multiple-choice quiz attempts.
- **Architectural Decision:**
  - Modeled two dedicated relational tables in SQLite (`assignments` and `assignment_submissions`) with foreign keys to `courses`, `lessons`, and `users`.
  - **Role-Based Permissions:**
    - Only `TEACHER` and `ADMIN` roles can create assignments (`POST /api/assignments`) and grade submissions (`POST /api/assignments/{id}/submissions/{sub_id}/grade`).
    - Only `STUDENT` role can submit assignment answers (`POST /api/assignments/{id}/submit`).
    - Both roles can view assignments, but students only receive their own submission details.
  - **Boundary Enforcement:**
    - `marks_awarded` must be non-negative and cannot exceed `assignment.max_marks` (enforced with HTTP 400 rejection).
    - Submissions are unique per `(assignment_id, user_id)` with `ON CONFLICT DO UPDATE` allowing student revisions before deadline.
    - All assignment creations and grading actions are immutably recorded in `audit_logs`.
- **Status:** **Verified** via `tests/test_assignments.py` (5 passing tests).
- **Approval Authority:** Software Architect & Curriculum Lead.

---

## Decision 9: Server-Side Media Upload MIME, Extension & Storage Bounds Enforcement

- **Context / Threat Model:**
  - FR-09 requires teachers to upload video lesson recordings and associated curriculum metadata.
  - Allowing unverified file uploads or arbitrary remote URLs introduces risks of Remote Code Execution (RCE), stored Cross-Site Scripting (XSS), server-side storage exhaustion, and malicious executable hosting (`.exe`, `.sh`).
- **Architectural Decision:**
  - **Strict Extension Whitelist:** Server rejects any upload whose extension is not in `{'.mp4', '.webm', '.mov', '.mkv', '.m3u8'}` with HTTP 400 Bad Request.
  - **MIME Type Verification:** Inspects `file.content_type` against `{video/mp4, video/webm, video/quicktime, video/x-matroska, application/x-mpegurl}`. Non-video MIME types receive HTTP 415 Unsupported Media Type.
  - **Payload Size Ceiling:** Sets a hard limit of 50 MB (52,428,800 bytes) per media upload suitable for low-bandwidth rural pilot deployments. Files exceeding this ceiling receive HTTP 413 Request Entity Too Large.
  - **URL Parameter Sanitation:** Any `video_url` supplied in JSON payloads must pass Pydantic validator inspection checking approved video file extensions.
  - **Isolated Storage Path:** Uploaded media is saved to `static/media/{lesson_id}.{ext}` preventing path traversal attacks.
- **Status:** **Verified** via `test_teacher_video_file_upload_success`, `test_video_file_upload_invalid_mime_rejected`, `test_video_file_upload_invalid_extension_rejected`, and `test_video_url_invalid_extension_rejected`.
- **Approval Authority:** Application Security Engineer & Infrastructure Architect.

---

## Decision 10: Server-Side Offline Queue Ownership & Cross-Account Isolation

- **Context / Threat Model:**
  - In rural Sindh schools, Android tablets and shared Chromebooks are passed between multiple students throughout the school day.
  - While client-side IndexedDB partitions queues by `user_id`, client-side enforcement alone does not protect against:
    1. A malicious or modified client submitting attempts tagged for Student A while authenticated under Student B's token.
    2. Shared-device account switching race conditions where outgoing items are inadvertently sent under the incoming session.
- **Architectural Decision:**
  - **Independent Server-Side Ownership Enforcement:** In `src/services/sync_service.py`, `process_sync_queue` inspects the claimed `user_id` of every individual attempt or progress update.
  - If `item.get("user_id")` does not match the authenticated session `user_id`, the server **strictly refuses ingestion**, increments `failed_items`, and records an immutable audit log entry: `SYNC_OWNERSHIP_MISMATCH`.
  - Under no circumstances does the server overwrite or attribute a foreign student's attempt to the currently authenticated user.
  - **Failure Resilience:** Failed items or unknown question references are reported in `failed_items` without throwing unhandled exceptions or aborting the remaining queue batch.
- **Status:** **Verified** via `test_cross_account_offline_sync_rejected` and `test_sync_unknown_question_fails_gracefully`.
- **Approval Authority:** Application Security Engineer & Lead Software Architect.

---

## Decision 11: HTTP 206 Byte-Range Video Streaming & ISO BMFF Container Validation (Batch 5)

- **Context / Failure Analysis:**
  - In Phase 4, video playback failed across browsers with `MEDIA_ELEMENT_ERROR: Format error` and HTTP 404/200 anomalies.
  - Root cause investigation revealed:
    1. *Missing files:* Only `lesson-sci-6-1.mp4` existed on disk; `lesson-math-6-1.mp4`, `lesson-eng-6-1.mp4`, and other curriculum lessons did not exist on disk, returning HTTP 404.
    2. *Malformed container:* The existing file was only 24 bytes containing an unplayable dummy header, missing ISO BMFF (`ftyp`, `moov`, `mdat`) atom boxes.
    3. *Missing Byte-Range Support:* Starlette default `StaticFiles` returned HTTP 200 without `Accept-Ranges` and byte slicing, breaking scrubbing and seeking on mobile WebViews.
- **Architectural Decision:**
  - **Dedicated Range-Serving Endpoint:** Implemented `@app.get("/static/media/{filename:path}")` in `src/api/app.py` supporting `Range: bytes=start-end`, returning **HTTP 206 Partial Content**, `Content-Range: bytes start-end/total`, `Accept-Ranges: bytes`, and HTTP 416 for unsatisfiable ranges.
  - **Container Integrity:** All seeded lesson media files are generated as valid ISO BMFF containers (`ftypisom`, `moov`, `mvhd`, `mdat`).
  - **Directory Traversal Guard:** Canonical realpath resolution strictly ensures files remain within `static/media/`.
  - **Player Error Telemetry:** Upgraded `SDCVideoPlayer` with clear Sindhi/English error states, retry action, and audio fallback.
- **Status:** **Verified** via `test_video_static_media_full_playback`, `test_video_byte_range_request_success`, `test_video_byte_range_suffix_request`, `test_video_byte_range_unsatisfiable`, `test_video_file_not_found`, and `test_video_path_traversal_prevention`.
- **Approval Authority:** Frontend Developer, Backend Architect, and Video Streaming Specialist.

---

## Decision 12: YouTube Privacy-Enhanced Integration & Complete 6-Role Server-Enforced RBAC (Batch 5)

- **Context / Requirements:**
  - Phase 4 and Batch 5 required integrating educational videos from YouTube without downloading or rehosting platform content, and completing server-enforced RBAC for all 6 roles.
- **Architectural Decision:**
  - **Privacy-Enhanced Official Embeds:** Embeds use `https://www.youtube-nocookie.com/embed/{youtube_id}` with parameters `modestbranding=1&rel=0&iv_load_policy=3`.
  - **Catalog & Legal Attribution:** Modeled `youtube_videos` table storing `youtube_id`, `original_url`, `embed_url`, `channel_name`, and explicit attribution text: *"Attribution and promotion do not independently authorize copyright reuse."*
  - **Offline Policy:** YouTube media is strictly marked as online-only. The system never downloads YouTube video streams into IndexedDB; when offline, the player displays a dedicated offline badge while preserving lesson transcripts, local quizzes, and tutor RAG search.
  - **Complete 6-Role Server-Enforced RBAC:**
    - `STUDENT`: Curriculum viewing, video playback, quizzes, personal progress, assignments, AI tutor.
    - `TEACHER`: Lesson uploads, question draft approval, assignment creation, student grading.
    - `CONTENT_REVIEWER`: STBB syllabus audit, lesson approval/rejection (`POST /api/lessons/{id}/review`).
    - `SCHOOL_ADMIN`: School-scoped student/teacher account provisioning (`POST /api/admin/users`), strictly isolated from other schools and restricted from privilege escalation.
    - `DISTRICT_OFFICER`: District aggregate analytics and anonymized CSV export; zero student PII access.
    - `SUPER_ADMIN`: System-wide settings, user administration, immutable security audit logs viewer (`GET /api/admin/audit-logs`).
- **Status:** **Verified** via `tests/test_rbac_and_video.py` (21 passing tests; 63 total in suite).
- **Approval Authority:** Application Security Engineer, API Platform Engineer, and Legal Compliance Officer.




