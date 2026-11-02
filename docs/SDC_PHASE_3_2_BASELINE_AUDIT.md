# SDC Phase 3.2: Baseline Audit Report
**Project:** Sindhi Digital Classroom (SDC)  
**Repository:** `D:\Ai Agents\agency-agents\sindhi-digital-classroom`  
**Milestone:** Phase 3.2 — Production-Oriented Sindhi Textbook AI, Hugging Face Models & Multi-Subject Architecture  
**Audit Date:** 2026-10-18  
**Author:** Agency Antigravity AI Engineering & Backend Architecture Team  
**Evaluation Standard:** Zero-fantasy, evidence-grounded codebase audit  

---

## 1. Executive Summary & Verification State

This audit was conducted directly against the live repository at `D:\Ai Agents\agency-agents\sindhi-digital-classroom`. Prior documentation claimed features, test counts, and integrations that required ground-truth verification.

### Key Audit Findings:
1. **Curriculum Data / Grade 6 Science Textbook Status:**
   - **Ground Truth:** No PDF or text files exist for Grade 6 Science (`data/curriculum_pdfs/class_6/` contains only `computer/Computer Ji Taleem - VI.pdf` and `sindhi/Sindhi Reader.pdf`).
   - The Grade 6 Science textbook has **not yet been supplied** by the project owner.
   - Any claim that Grade 6 Science is fully ingested or indexed is false. The system must operate with synthetic/test fixtures for Science until the actual PDF is uploaded.
2. **Current AI Tutor Implementation (`src/services/ai_tutor_service.py`):**
   - **Mechanism:** Hardcoded static dictionary of 4 seed chunks (`lesson-sci-6-1`, `lesson-math-6-1`, `lesson-sindhi-6-1`, `lesson-eng-6-1`) with keyword matching (`kw_match -> sim = max(sim, 0.85)`).
   - If not in static chunks, it queries `transcripts` table with `LIKE %token%`.
   - **Defect/Gap:** Answers are not textbook-page-grounded; static chunks are synthetic snippets, not real textbook extractions.
3. **AI Inference & Hugging Face Adapter (`src/services/ai_provider.py`):**
   - Implements two tiers:
     - `LocalRuleBasedAIProvider` (Tier 1): Deterministic string formatting fallback.
     - `HuggingFaceInferenceProvider` (Tier 2): Cloud API client calling Hugging Face inference API (`https://api-inference.huggingface.co/models/{model_name}`).
   - **Defect/Gap:** On any failure or if token is absent, it silently falls back to Tier 1 without explicitly indicating whether real inference succeeded or fallback was triggered.
4. **Database & Schema (`src/database/schema.py`):**
   - Contains `courses`, `lessons`, `videos`, `transcripts`, `questions`, `attempts`, `progress`, `chat_logs`.
   - **Defect/Gap:** Lacks dedicated entities for `textbooks`, `document_pages`, `curriculum_chunks`, and `ingestion_jobs`. Page numbers, PDF offsets, and multi-version activations are absent.
5. **Testing Baseline:**
   - 28 unit/integration tests previously reported; regression suite `tests/test_phase3_audit_regressions.py` passed with 3/3 passing tests.

---

## 2. Detailed Component Audit

### 2.1 Application Entry & Routing
- **Entry Point:** `src/api/app.py`
- **FastAPI Mounts:**
  - `/api/auth` (`src/api/routes/auth.py`)
  - `/api/lessons` (`src/api/routes/lessons.py`)
  - `/api/tutor` (`src/api/routes/tutor.py`)
  - `/api/admin` (`src/api/routes/admin.py`)
  - `/api/assignments` (`src/api/routes/assignments.py`)
  - `/api/dashboards` (`src/api/routes/dashboards.py`)
  - `/api/sync` (`src/api/routes/sync.py`)
  - `/api/quiz` (`src/api/routes/video_quiz.py`)
- **CORS & Middleware:** Correctly configured; security headers applied in middleware.

### 2.2 Database Schema & Migrations
- **Current DB:** SQLite (`sdc.db`) managed through `src/database/session.py`.
- **Migration Engine:** None (raw `CREATE TABLE IF NOT EXISTS` in `SCHEMA_SQL`).
- **Gaps Identified:**
  - No table for `subjects` or flexible multi-subject taxonomy.
  - No `textbooks` table to track title, edition, PDF hash, page count, and active status.
  - No `textbook_pages` or `textbook_chunks` storing printed page vs PDF page index, raw Sindhi text vs normalized search text.
  - No `ingestion_jobs` to track processing stage, progress percentage, and OCR fallback status.

### 2.3 Existing PDF Ingestion Capability
- **Installed Libraries:** `pypdf` is installed. `fitz` (PyMuPDF) and `pdfplumber` are **not installed**.
- **Existing Extraction Code:** No general PDF ingestion service exists in `src/services/`.
- **Findings on Existing PDFs:**
  - `Computer Ji Taleem - VI.pdf`: 213 pages, scanned raster images, `pypdf` extracts 0 characters.
  - `Sindhi Reader.pdf`: 103 pages; pages 0-1 and 95 contain raw text using Arabic Presentation Forms-A/B (e.g. `U+FEB3`, `U+FEE8`, `U+FB85`), requiring NFKC normalization to standard Sindhi Unicode characters. Remaining pages are scanned raster images.

### 2.4 Grounded AI Tutor & Refusal Gate
- **File:** `src/services/ai_tutor_service.py`
- **Refusal Mechanism:**
  - Computes `compute_grounding_similarity(normalized_query, chunk)`
  - Refusal threshold: `0.65` (configurable via `settings.grounding_confidence_threshold`).
  - Out-of-scope refusal message: `"معاف ڪجو، هي سوال سبق جي دائري کان ٻاهر آهي. مهرباني ڪري سبق بابت پڇو."`
- **Citation Metadata:**
  - Citations currently return video timestamps (`timestamp_seconds`), not textbook page numbers.

### 2.5 Security, Authentication & Authorisation
- **File:** `src/api/deps.py` & `src/services/auth_service.py`
- **Auth Model:** JWT access tokens + role-based checks. 2 primary user roles: `STUDENT` and `ADMIN`.
- **Token Security:** Passwords and PINs hashed with PBKDF2-HMAC-SHA256 (`pin_hash`). Revocation cutoff epoch supported.
- **Vulnerabilities / Gaps:**
  - Student queries are stored in `chat_logs` with raw question text. Retention and data minimization policies needed.
  - PDF upload endpoint needs file size limits (e.g., 50MB), magic-byte signature check (`%PDF-`), safe directory sandboxing, and admin-only authorization.

---

## 3. Verified Codebase Status Matrix

| Subsystem | Current State | Code Grounding | Phase 3.2 Action Required |
| :--- | :--- | :--- | :--- |
| **Grade 6 Science PDF** | **BLOCKED** (PDF not provided) | Repo inspected; no science PDF found | Build reusable ingestion pipeline & test with synthetic Science fixtures |
| **Multi-Subject Schema** | Missing | `src/database/schema.py` | Add `subjects`, `textbooks`, `textbook_pages`, `textbook_chunks`, `ingestion_jobs` |
| **PDF Ingestion Engine** | Missing | None in `src/services/` | Implement `textbook_ingestion_service.py` with `pypdf` + NFKC normalization |
| **Lexical RAG Pipeline** | Synthetic keyword matcher | `src/services/ai_tutor_service.py` | Upgrade to BM25 / token-overlap lexical index over textbook chunks with page citations |
| **HF Model Adapter** | Cloud API with silent fallback | `src/services/ai_provider.py` | Expose honest inference status (`REAL_LLM`, `FALLBACK`, `MOCKED`) |
| **Evaluation Dataset** | Seed assertions only | `tests/test_phase3_audit_regressions.py` | Create structured Sindhi Grade 6 Science benchmark dataset & rubric |

---

## 4. Phase 3.2 Proposed Implementation Sequence

1. **Step 1 (Docs & Models):** Finalize `SDC_SINDHI_MODEL_EVALUATION.md` comparing open-weight Sindhi models.
2. **Step 2 (Database Architecture):** Expand schema with non-destructive versioned migration adding `subjects`, `textbooks`, `textbook_pages`, `textbook_chunks`, and `ingestion_jobs`.
3. **Step 3 (Ingestion Service):** Build `src/services/textbook_ingestion_service.py` with PDF parsing, Arabic Presentation Forms-A/B normalization, scanned PDF detection, and chunk boundary creation.
4. **Step 4 (Tutor RAG Upgrade):** Refactor `src/services/ai_tutor_service.py` to retrieve against active textbook chunks and return authentic page-level citations.
5. **Step 5 (Honest AI Provider Status):** Update `ai_provider.py` so responses and admin status endpoints clearly report whether inference was live LLM, deterministic fallback, or mock.
6. **Step 6 (Admin & Student Endpoints):** Add Admin textbook upload and activation routes (`POST /api/admin/textbooks/upload`, `POST /api/admin/textbooks/{id}/activate`) and student subject/textbook selector.
7. **Step 7 (Evaluation Framework & Verification):** Add automated test suites for ingestion, retrieval, refusal, and permissions; output comprehensive implementation report and fine-tuning proposal.
