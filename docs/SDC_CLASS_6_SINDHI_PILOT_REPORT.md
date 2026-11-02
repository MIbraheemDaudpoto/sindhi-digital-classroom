# SDC Phase 2.3 — Class 6 Sindhi Pilot & Evidence Verification Report

**Date**: 2026-10-17  
**Status**: COMPLETE / PENDING_TEXTBOOK_PDF  
**Project**: Sindhi Digital Classroom (SDC)  
**Target Class & Subject**: Class 6 — Sindhi (سنڌي سليس)  

---

## 1. Executive Summary

This pilot investigation for Phase 2.3 evaluated the source materials and platform readiness for **Class 6 Sindhi**:
1. **Curriculum PDF Ingestion**: Verified that the expected directory `data/curriculum_pdfs/class_6/sindhi/` exists. No PDF file is currently present in the repository. As per protocol, content was **not invented** or hallucinated; status is recorded honestly as `PENDING_TEXTBOOK_PDF`.
2. **Channel & Content Verification**: Inspected `https://www.youtube.com/@SindhOnlineSchool`. Using oEmbed endpoint validation on 30 retrieved video identifiers, confirmed the official channel is indeed **Sindh Online School**. However, all 30 sampled videos correspond to Classes 8–10 (Math, Chemistry, Physics). No Class 6 Sindhi lesson videos were found in the current sampled page snapshot.
3. **Data-Driven Curriculum Manifest**: Created `data/curriculum_manifest.json` as the unified source-of-truth tracking pilots, provenance, video audits, and ingestion readiness.
4. **Test Suite Coverage**: Created `tests/test_class6_sindhi_curriculum.py` covering Class 6 Sindhi browsing, detail retrieval, and manifest schema integrity. The entire test suite passed (122 tests passing total: 119 baseline + 3 new tests).

---

## 2. Source Document & Ingestion Audit

| Item | Finding / Status |
|---|---|
| Target Directory | `data/curriculum_pdfs/class_6/sindhi/` |
| Directory Status | Created, Verified Empty |
| Expected Document | `STBB_Class_6_Sindhi.pdf` |
| Actual File Found | `False` |
| Provenance / Publisher | PENDING — to be extracted upon PDF drop |
| Ingestion Status | `PENDING_TEXTBOOK_PDF` |

### Ingestion Action Item
Once `STBB_Class_6_Sindhi.pdf` is placed in `data/curriculum_pdfs/class_6/sindhi/`, run the ingestion pipeline to parse units, chapters, exercises, and vocabulary into the database.

---

## 3. Video Channel Audit (`@SindhOnlineSchool`)

- **URL**: `https://www.youtube.com/@SindhOnlineSchool`
- **Channel Verification**: Verified via oEmbed query against `www.youtube.com/oembed`.
- **Author Name**: `Sindh Online School`
- **Sample Count**: 30 unique video IDs extracted and verified.
- **Findings**:
  - Sample contained Class 8 Math (e.g., Geometry concepts, Exercise 9.7), Class 9 Math (Graph of equations), and Class 10 Chemistry (Water pollution, Chapter 6 detailed questions).
  - Class 6 Sindhi language videos: **0 found in sample**.
- **Action**: A deeper playlist-level crawl or targeted keyword search across the channel's full upload library can be conducted when video associations are mapped.

---

## 4. Platform Readiness & Test Verification

- **Curriculum Browsing API**: `/api/lessons?class_level=6&subject=Sindhi` successfully returns `crs-sindhi-6` with existing seed lesson.
- **Video Fallback**: Multi-tier playback schema verified (`.m3u8` -> `.mp4` -> `.mp3`).
- **Test Results**:
  - `tests/test_class6_sindhi_curriculum.py`: 3/3 PASSED in 11.47s.
  - Full suite: 122 tests passing with zero failures.

---

## 5. Artifacts Created & Modified

1. [curriculum_manifest.json](file:///D:/Ai%20Agents/agency-agents/sindhi-digital-classroom/data/curriculum_manifest.json) — Schema-validated manifest tracking Class 6 Sindhi pilot.
2. [test_class6_sindhi_curriculum.py](file:///D:/Ai%20Agents/agency-agents/sindhi-digital-classroom/tests/test_class6_sindhi_curriculum.py) — Regression suite for Class 6 Sindhi.
3. [SDC_CLASS_6_SINDHI_PILOT_REPORT.md](file:///D:/Ai%20Agents/agency-agents/sindhi-digital-classroom/docs/SDC_CLASS_6_SINDHI_PILOT_REPORT.md) — This formal pilot audit report.
