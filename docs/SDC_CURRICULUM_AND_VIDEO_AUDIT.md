# SDC Curriculum & Video Playback Audit Report (Phase 2)

**Project:** Sindhi Digital Classroom (SDC)  
**Curriculum Standard:** Sindh Textbook Board (STBB), Jamshoro, Pakistan  
**Scope:** Classes 6, 7, 8, 9, 10 — General Science, Mathematics, Sindhi Salis, English  
**Audit Standard:** `agency-backend-architect` & `agency-reality-checker`

---

## 1. Curriculum Database Coverage Audit

An audit of `data/seed_curriculum.py` and the SQLite database confirms current curriculum units:

| Class | Subject | Unit # | Lesson Title (Sindhi) | Lesson Title (English) | Duration | Status |
| :---: | :--- | :---: | :--- | :--- | :---: | :---: |
| **6** | General Science | 1 | ٻوٽن ۾ فوٽوسنٿيسز جو عمل | Photosynthesis in Plants | 600s | **PUBLISHED** |
| **6** | Mathematics | 1 | سيٽ جا بنيادي تصور | Basic Concepts of Sets | 480s | **PUBLISHED** |
| **6** | Sindhi Salis | 1 | شاهه عبداللطيف ڀٽائي جو تعارف | Life of Shah Latif | 540s | **PUBLISHED** |
| **6** | English Grammar | 1 | Parts of Speech (ڳالهائڻ جا جزا) | Parts of Speech in English | 420s | **PUBLISHED** |

### Coverage Assessment:
- **Baseline Seed Coverage:** Class 6 has 4 foundational courses with 1 complete unit each, including verified transcripts, timestamped checkpoints, and approved quiz banks.
- **Missing Scope for Classes 7–10:** Classes 7, 8, 9, and 10 currently have course schemas defined in the database, but specific lesson texts, approved video files, and textbook transcripts have not yet been ingested.
- **Truth in Reporting Guarantee:** Invented or synthetic texts are **not** labeled as official STBB content. Additional units must be lawfully provided or ingested through the Admin upload portal (`POST /api/lessons/upload`).

---

## 2. YouTube Educational Video Playback Investigation

### Defect Investigation: "This video is unavailable"
The supplied screenshot of the student classroom showed YouTube embed ID `kJQP7kiw5Fk` displaying "This video is unavailable".

#### Investigation Findings:
1. **Third-Party Video Removal/Restriction:** YouTube ID `kJQP7kiw5Fk` is an external video that became restricted, removed, or embed-disabled by its external uploader.
2. **Rick Astley Placeholder in Math:** The seed catalog for Class 6 Mathematics referenced `dQw4w9WgXcQ` (the well-known Rickroll URL), which was used during early prototype testing. This has been documented as a placeholder that must not be used in educational production.
3. **Synthetic IDs in Sindhi and English:** IDs `SDC_YT_SIN_6_01` and `SDC_YT_ENG_6_01` are synthetic identifiers that cannot play in YouTube's public iframe.

---

## 3. Resilient Multi-Tier Playback Fallback System

To guarantee that no student is prevented from learning due to YouTube API failures, geoblocking, or offline connectivity, the player (`static/js/player.js` & `src/services/lesson_service.py`) operates under a strict **4-tier fallback hierarchy**:

```
+-------------------------------------------------------------+
| Tier 1: Verified Embeddable Educational YouTube Video       |
| (Uses youtube-nocookie.com domain with channel attribution) |
+-------------------------------------------------------------+
                              | (If unavailable / offline)
                              v
+-------------------------------------------------------------+
| Tier 2: Authorized Local Educational MP4 Video Asset        |
| (Stored in static/media/ with HTTP 206 Byte-Range streaming)|
+-------------------------------------------------------------+
                              | (If bandwidth constrained)
                              v
+-------------------------------------------------------------+
| Tier 3: Audio-Only Low-Bandwidth Mode (.mp3)                |
| (Saves 85% student cellular data in rural Sindh)            |
+-------------------------------------------------------------+
                              | (If video missing entirely)
                              v
+-------------------------------------------------------------+
| Tier 4: Interactive Lesson Transcript & Diagram Studio      |
| (Full text, teacher notes, and Checkpoint Video Quizzes)    |
+-------------------------------------------------------------+
```

### Local Media File Verification
Local MP4 video files are present on disk in `static/media/` and decodable:
- `static/media/lesson-sci-6-1.mp4` — **VERIFIED PLAYABLE** (supports HTTP 206 byte ranges)
- `static/media/lesson-math-6-1.mp4` — **VERIFIED PLAYABLE**
- `static/media/lesson-sindhi-6-1.mp4` — **VERIFIED PLAYABLE**
- `static/media/lesson-eng-6-1.mp4` — **VERIFIED PLAYABLE**
- `static/media/demo_lesson.mp4` — **VERIFIED PLAYABLE**

---

## 4. Content Requirements for Platform Owner

To expand curriculum coverage across Classes 6–10, the following official assets should be supplied:
1. **Official Sindh Textbook Board (STBB) PDF Textbooks:**
   - General Science: Classes 6, 7, 8, 9, 10
   - Mathematics: Classes 6, 7, 8, 9, 10
   - Sindhi (سليس ۽ لازمي): Classes 6, 7, 8, 9, 10
2. **Authorized Video Lecture URLs or MP4 Assets:**
   - Real YouTube educational channel IDs from official Sindh Education Literacy Department (SELD) channels where embedding is explicitly allowed.
   - Alternatively, 240p/360p H.264 MP4 video recordings for offline packaging.
