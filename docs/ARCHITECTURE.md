# Sindhi Digital Classroom (SDC) - System Architecture

Authored under **agency-software-architect** and **agency-backend-architect**.

---

## 1. System Context & Overview

Sindhi Digital Classroom (SDC) is an offline-capable Progressive Web App (PWA) designed for rural Sindhi-speaking students (Class 6 to 10), teachers, school administrators, and education officers under the Sindh Education and Literacy Department (SELD) and Sindh Textbook Board (STBB) curriculum.

```
+---------------------------------------------------------------------------------------+
|                                    CLIENT PWA (BROWSER)                               |
|                                                                                       |
|   +-------------------+  +--------------------+  +------------------+  +----------+   |
|   | Sindhi RTL UI     |  | Video Player       |  | Voice AI Input   |  | AI Tutor |   |
|   | (Class 6-10 STBB) |  | (Quiz Pop-up Pause)|  | (ASR Correction) |  | (Grounded|   |
|   +---------+---------+  +---------+----------+  +--------+---------+  | Sindhi)  |   |
|             |                      |                      |            +----+-----+   |
|             v                      v                      v                 v         |
|   +-------------------------------------------------------------------------------+   |
|   |          Service Worker (App Shell Cache) + IndexedDB (Offline Packs)        |   |
|   +---------------------------------------+---------------------------------------+   |
+-------------------------------------------|-------------------------------------------+
                                            | (Sync when online / REST JSON)
                                            v
+---------------------------------------------------------------------------------------+
|                                  FASTAPI SERVER (BACKEND)                             |
|                                                                                       |
|   +----------------+  +-----------------+  +-------------------+  +---------------+   |
|   | Auth & RBAC    |  | Lesson & Video  |  | Smart Video Quiz  |  | RAG Tutor     |   |
|   | (School+PIN)   |  | Service         |  | & Approval Gate   |  | (STBB Chunks) |   |
|   +--------+-------+  +--------+--------+  +---------+---------+  +-------+-------+   |
|            |                   |                     |                    |           |
+------------|-------------------|---------------------|--------------------|-----------+
             v                   v                     v                    v
+---------------------------------------------------------------------------------------+
|                               PERSISTENCE (SQLITE WAL MODE)                           |
|                                                                                       |
|   Tables: users, schools, courses, lessons, videos, transcripts, questions,           |
|           attempts, progress, chat_logs, audio_samples, consents, audit_logs           |
+---------------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Subsystems

### 2.1 Offline-First PWA & Storage Strategy (FR-32, FR-33)
- **App Shell Cache:** Static HTML, CSS, JavaScript, and Sindhi web fonts are cached via `sw.js` using Cache-First strategy.
- **IndexedDB Client Storage (`db.js`):**
  - Stores complete downloaded unit packs (metadata, timestamped transcripts, approved questions, tutor chunks).
  - Queues student quiz attempts, progress checkpoints, and chat logs locally with ISO timestamps.
- **Background Sync Engine:** When connectivity is restored, the queue flushes to `/api/sync/queue` with idempotent deduplication.

### 2.2 Smart Video Quiz Pipeline (FR-10 through FR-19)
1. **Upload & Transcription:** Lessons are uploaded with video metadata and timestamped transcripts (`start`, `end`, `confidence`).
2. **Topic Segmentation:** Transcripts are partitioned into 2 to 3 minute pedagogical segments.
3. **MCQ Generation:** Draft questions with 1 correct answer and 3 plausible distractors are generated per segment.
4. **Mandatory Teacher Approval Gate (FR-13):** Every question is assigned status `DRAFT` or `PENDING_APPROVAL`. Unapproved questions are strictly excluded from student quiz pools.
5. **Interactive Video Overlay (FR-14, FR-15):** The client video player listens to playback time. When reaching a pop-up point, playback pauses automatically until answered or skipped.
6. **Randomization & Difficulty Balancing (FR-16, FR-17):** Students receive randomized subsets from the approved bank to prevent copying.

### 2.3 Grounded Sindhi AI Tutor (FR-23 through FR-26)
- **Approved Chunks Only:** The RAG retrieval pipeline searches strictly against approved Sindh Textbook Board lesson chunks.
- **Strict Out-of-Scope Refusal (FR-24):** If similarity score falls below threshold or chunk relevance is zero, the tutor returns a standardized Sindhi refusal:
  > **معاف ڪجو، هي سوال سبق جي دائري کان ٻاهر آهي. مهرباني ڪري سبق بابت پڇو.**  
  *(Sorry, this question is outside the lesson scope. Please ask about the lesson.)*
- **Source Citation (FR-25):** Valid answers include the exact lesson title, unit, and video timestamp jump link.

### 2.4 Voice AI & Correction (FR-20, FR-21, FR-22)
- Audio capture via Web Speech API / ASR service.
- Transcribed text is displayed in an editable box so rural students can fix ASR dialect errors before submitting.
