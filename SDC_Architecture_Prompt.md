# Project: Sindhi Digital Classroom (SDC) - System Architecture & Engineering Spec

## 1. Context & Objective
Offline-first Progressive Web App (PWA) & edge-deployable backend for 2.5M+ rural Sindhi-medium students (Classes 6–10) under the Sindh Textbook Board (STBB). Optimized for 1–2GB RAM Android phones, intermittent grid power (12V solar), and zero-internet school labs.
*(Scope: Frontend PWA, Backend REST API, SQLite WAL Database, Video Delivery, Offline Sync Engine, and Edge Deployment. Excludes AI/RAG).*

---

## 2. Frontend Architecture (PWA)
- **Tech Stack:** Vanilla HTML5, Vanilla CSS3 (custom RTL tokens, CSS Grid/Flexbox), Vanilla ES6+ JavaScript (zero React/Vue overhead).
- **RTL Typography:** Native Sindhi Perso-Arabic alphabet (52 glyphs) using `Noto Naskh Arabic` + `Inter` for Latin numerals.
- **Offline Storage (`IndexedDB` - `SDC_Offline_Store`):**
  - `unit_packs`: Pre-downloaded lesson metadata, WebVTT transcripts, and approved questions.
  - `sync_queue`: Buffered student attempts and completion timestamps recorded during offline periods.
- **Service Worker (`sw.js`):** Cache-First for static assets (HTML/CSS/JS/Fonts); Network-First with IndexedDB fallback for curriculum data.
- **Smart Video Player (`player.js`):** Custom HTML5 player supporting local 240p/360p MP4 byte-range playback and YouTube embeds. Listens to `timeupdate` and automatically pauses playback at pedagogical timestamps to display interactive Sindhi quiz overlays with randomized distractors.

---

## 3. Backend Architecture (FastAPI & Services)
- **Tech Stack:** Python 3.11+, FastAPI 0.115+, Pydantic V2, SQLAlchemy 2.0.
- **API Endpoints:**
  - `/api/auth`: PBKDF2-SHA256 password hashing, signed JWT Bearer authentication. Rejects URL query parameter bypasses.
  - `/api/lessons`: STBB hierarchy (Course > Chapter > Lesson > Transcripts).
  - `/api/quiz`: Question fetching and automated grading with mandatory **Teacher Approval Gate** (`is_approved = 1`).
  - `/api/sync/offline-batch`: Ingestion of buffered student quiz attempts.
  - `/api/dashboard`: Aggregated analytics for students, teachers, and district education officers.
- **Offline Sync & Idempotency:** Sync worker uses client-generated `attempt_uuid` with `INSERT OR IGNORE` deduplication. Prevents double-scoring and handles network re-transmissions seamlessly.
- **RBAC Security (6 Tiers):** `STUDENT`, `PARENT`, `TEACHER`, `HEAD_TEACHER`, `OFFICER`, and `SUPER_ADMIN`.

---

## 4. Relational Database Design (SQLite WAL / PostgreSQL)
- **Engine Optimization:** SQLite in WAL (Write-Ahead Logging) mode with `PRAGMA synchronous = NORMAL` and `PRAGMA busy_timeout = 5000` for high concurrency without locks. Compatible with cloud PostgreSQL 16.
- **Core Relational Schemas:**
  - `schools`: `id`, `name`, `district`, `division`.
  - `users`: `id`, `school_id`, `full_name`, `role`, `hashed_password`, `mobile_number`.
  - `courses` & `lessons`: `class_level` (6–10), `unit_number`, `title_sindhi`, `video_path_mp4`, `duration_seconds`.
  - `video_quizzes`: `lesson_id`, `timestamp_sec`, `question_sindhi`, `options_json`, `correct_idx`, `approval_status`.
  - `quiz_attempts`: `attempt_uuid` (UNIQUE), `user_id`, `question_id`, `selected_option`, `is_correct`, `created_at`.
  - `audit_logs` & `consents`: PECA/GDPR-compliant telemetry and event tracking.

---

## 5. Media Streaming & "School-in-a-Box" Edge Deployment
- **Video Delivery:** Highly compressed H.264 at 240p (~300 Kbps) and 360p (~600 Kbps). 15-minute lesson = 35MB–60MB. Delivered via HTTP 206 Partial Content byte-range streaming for seamless scrubbing.
- **Rural Edge Hardware ("School-in-a-Box"):**
  - **Hardware:** Raspberry Pi 5 / Mini-PC powered by 12V solar DC battery.
  - **Networking:** Local low-cost Wi-Fi router (No internet required, local DHCP `192.168.x`).
  - **Workflow:** Students connect to local Wi-Fi, PWA boots from local server. Local SQLite database buffers all school activity and pushes scheduled batch syncs to central cloud when backhaul connectivity is available.
