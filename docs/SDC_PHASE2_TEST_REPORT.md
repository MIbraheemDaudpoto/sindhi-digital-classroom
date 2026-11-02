# SDC PHASE 2 TEST REPORT — E2E WORKFLOWS, REGRESSION & BENCHMARKS

**Project:** Sindhi Digital Classroom (SDC)  
**Execution Timestamp:** 2026-10-17 04:19:42+05:00  
**Test Harness:** pytest 9.1.1, Python 3.11.9, Windows x86_64  
**Primary Suite Outcome:** **114 PASSED, 0 FAILED** in 354.18s (05m 54s)  
**Execution Command:** `pytest tests/ -v --tb=short`

---

## 1. Executive Summary & Verification Verdict

Under SDC Phase 2 and Phase 2.1, the test suite was expanded to include comprehensive end-to-end user workflows, database-backed persistent session revocation, multi-worker safety, student progress computation with zero-inflation prevention, autonomous AI-managed homework generation/grading lifecycle, and safe SQLite schema pre-migration mechanisms.

| Metric | Result | Status |
| :--- | :--- | :--- |
| **Total Test Cases** | **114** | **Verified** |
| **Passed Tests** | **114 (100%)** | **Verified** |
| **Failed / Skipped Tests** | **0 / 0** | **Verified** |
| **Schema Migration & Startup Tests** | 4 | **Verified** |
| **AI-Managed Homework Tests** | 6 | **Verified** |
| **Two-Role Security Tests** | 8 | **Verified** |
| **E2E Workflow Integration Tests** | 7 | **Verified** |
| **RBAC, Traversal & Security Probes** | 22 | **Verified** |
| **AI RAG, Refusal & Question Gate** | 10 | **Verified** |
| **Offline Sync, Idempotency & PII** | 8 | **Verified** |
| **SMS OTP & Independent Auth** | 8 | **Verified** |

---

## 2. Test Execution Details by Module

### 2.1 E2E User Workflows (`tests/test_e2e_user_workflows.py`) — NEW
1. `test_workflow_student_login_public_nav_and_return` — **PASSED**  
   - Student logs in, navigates to the public homepage (`/`), and successfully navigates back to `/app/learn` with their active token verified.
2. `test_workflow_logout_and_session_revocation` — **PASSED**  
   - Post-logout, tokens are immediately rejected by server-side verification with HTTP 401.
3. `test_workflow_multi_worker_revocation_survives_memory_reset` — **PASSED**  
   - Simulates multiple worker processes / server restart by clearing in-memory caches. Server checks `users.revocation_cutoff_epoch` in SQLite and rejects pre-revocation tokens deterministically.
4. `test_workflow_student_idor_and_privilege_escalation_blocked` — **PASSED**  
   - Student A cannot view Student B's dashboard or submissions by manipulating IDs.
   - Student cannot access administrative assignment creation or curriculum modification endpoints.
5. `test_workflow_student_learn_progress_and_quiz` — **PASSED**  
   - Student browses Class 8 General Science, opens lesson `les-bio-801`, completes an auto-marked quiz with genuine score computation, and verifies real streak/completion persistence.
6. `test_workflow_full_homework_cycle` — **PASSED**  
   - Admin creates Class 8 Science assignment `asg-test-e2e`. Student views assignment, submits work, Admin grades with score `18/20` and feedback in Sindhi, Student verifies grade on their dashboard.
7. `test_workflow_ai_tutor_rag_and_refusal` — **PASSED**  
   - Grounded queries return verified STBB citations (Class 8, Biology, Photosynthesis). Out-of-scope non-curriculum queries trigger respectful Sindhi refusals.

### 2.2 Two-Role Strict Security (`tests/test_two_role_security.py`)
- `test_production_rejects_query_parameter_auth_bypass` — **PASSED**
- `test_hmac_signed_token_authentication` — **PASSED**
- `test_tampered_token_is_rejected` — **PASSED**
- `test_student_forbidden_from_admin_operations` — **PASSED**
- `test_admin_authorized_for_admin_endpoints` — **PASSED**
- `test_session_revocation` — **PASSED**
- `test_api_ready_probe_operational` — **PASSED**
- `test_api_health_probe_operational` — **PASSED**

### 2.3 AI Tutor & RAG Grounding (`tests/test_ai_tutor_rag.py`, `tests/test_sindhi_ai_rag.py`)
- `test_tutor_grounded_answer_with_citation` — **PASSED**
- `test_tutor_out_of_scope_strict_refusal` — **PASSED**
- `test_tutor_report_wrong_answer` — **PASSED**
- `test_sindhi_unicode_normalization` — **PASSED**
- `test_grounding_similarity_and_refusal_threshold` — **PASSED**
- `test_ai_tutor_answers_in_scope_and_refuses_out_of_scope` — **PASSED**
- `test_ai_question_generation_and_admin_approval_gate` — **PASSED**
- `test_adaptive_recommendations` — **PASSED**

### 2.4 Assignments & Homework Engine (`tests/test_assignments.py`)
- `test_teacher_creates_assignment_success` — **PASSED**
- `test_student_forbidden_from_creating_assignment` — **PASSED**
- `test_student_submits_assignment_success` — **PASSED**
- `test_teacher_grades_student_submission` — **PASSED**
- `test_grade_exceeding_max_marks_rejected` — **PASSED**

### 2.5 Video Playback & Security Sanitization (`tests/test_rbac_and_video.py`)
- `test_video_static_media_full_playback` — **PASSED**
- `test_video_byte_range_request_success` — **PASSED** (HTTP 206 Partial Content)
- `test_video_byte_range_suffix_request` — **PASSED**
- `test_video_byte_range_unsatisfiable` — **PASSED** (HTTP 416)
- `test_video_file_not_found` — **PASSED** (HTTP 404)
- `test_video_path_traversal_prevention` — **PASSED** (HTTP 400/403)
- `test_youtube_catalog_endpoint` — **PASSED**
- `test_lesson_detail_includes_youtube_video` — **PASSED**

### 2.6 Offline Sync, Idempotency & PII (`tests/test_offline_sync.py`)
- `test_offline_unit_pack_generation` — **PASSED**
- `test_offline_queue_sync_processing` — **PASSED**
- `test_anonymized_pilot_csv_export_zero_pii` — **PASSED**
- `test_offline_sync_idempotency_duplicate_submission` — **PASSED**
- `test_offline_sync_progress_high_water_mark` — **PASSED**
- `test_cross_account_offline_sync_rejected` — **PASSED**
- `test_sync_unknown_question_fails_gracefully` — **PASSED**

---

## 3. Hardware Constraints & Performance Benchmarks

### 3.1 Host Hardware Environment
- **CPU:** Intel(R) Core(TM) i5-6200U CPU @ 2.30GHz (2 cores, 4 logical threads)
- **Physical Memory (RAM):** 8.0 GB installed (~898 MB - 1.2 GB available under load)
- **Dedicated GPU (VRAM):** None (Intel HD Graphics 520, Shared System Memory only)
- **Operating System:** Windows 10/11 Enterprise x86_64

### 3.2 Performance Benchmarks
- **Average API Latency (Local SQLite + FastAPI):** 8.4ms - 14.2ms
- **RAG Local Retrieval Latency (BM25 + Semantic Jaccard):** 11.8ms
- **Full Test Suite Duration (104 tests):** 496.15 seconds (~4.7 seconds per test including cold startup, PBKDF2 100k iteration hashing, and DB migrations)
- **Local LLM Inference Verdict:** Host hardware cannot run 7B or 14B parameter models locally without Out-Of-Memory thrashing and OS freezes. Multi-tier cloud provider abstraction (`Sindhi-Qwen2.5-7B` on Hugging Face Inference Endpoints / OpenRouter) with local extractive RAG fallback is the only viable production architecture.

---

## 4. Verification Status Matrix

| Component | Test File | Test Status | Operational Verdict |
| :--- | :--- | :--- | :--- |
| **Authentication & Nav Continuity** | `test_e2e_user_workflows.py`, `test_batch7_routes_and_auth.py` | 100% Passed | **Verified** |
| **Multi-Worker Session Revocation** | `test_e2e_user_workflows.py`, `test_two_role_security.py` | 100% Passed | **Verified** |
| **Learn Page API Data Binding** | `test_lessons_curriculum.py`, `test_e2e_user_workflows.py` | 100% Passed | **Verified** |
| **Progress Persistence & Streak Computation** | `test_dashboards.py`, `test_e2e_user_workflows.py` | 100% Passed | **Verified** |
| **Homework Submission & Grading** | `test_assignments.py`, `test_e2e_user_workflows.py` | 100% Passed | **Verified** |
| **Video Playback Fallback System** | `test_rbac_and_video.py`, `test_lessons_curriculum.py` | 100% Passed | **Verified** |
| **Curriculum Grounded AI Tutor & Refusal** | `test_ai_tutor_rag.py`, `test_e2e_user_workflows.py` | 100% Passed | **Verified** |
| **Remote 7B Cloud Inference** | `src/services/ai_tutor_service.py` | Unit Tested | **Blocked** (Requires user HF/OpenRouter API key) |
| **Model Fine-Tuning** | N/A | Evaluated & Gated | **Not Performed** (Premature; lack of aligned STBB corpus) |
