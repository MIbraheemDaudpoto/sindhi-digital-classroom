"""
Ingestion Script for Sindh Textbook Board (STBB) Class 6 Mathematics Dataset.

Source Book: Riazi Sindhi VI (2024-25 edition, STBB portal id=270, 264 pages)
Input file: data/stbb_math_6_complete.json

Ingests:
- 13 official units into `lessons` table under `crs-math-6`
- 54 curriculum chunks into `sdc_chunks` and `sdc_chunks_fts` (subject_id = 'math-6')
- 105 mathematical terms into `sdc_glossary` and `sdc_glossary_fts` (subject_id = 'math-6')
- 39 videos into `sdc_videos` (subject_id = 'math-6')
- 39 interactive quiz questions into `questions` table
"""

import json
import logging
import sqlite3
import sys
import uuid
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("ingest_math")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
DB_PATH = ROOT_DIR / "data" / "sdc_platform.db"
JSON_PATH = ROOT_DIR / "data" / "stbb_math_6_complete.json"


def ensure_column_exists(conn: sqlite3.Connection, table_name: str, col_name: str, col_type: str, default_val: str):
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    cols = [r[1] for r in cur.fetchall()]
    if col_name not in cols:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
        logger.info("Added column %s to table %s", col_name, table_name)


def main():
    if not JSON_PATH.exists():
        logger.error("JSON file not found: %s", JSON_PATH)
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # 1. Ensure subject_id column in all relevant RAG tables
        ensure_column_exists(conn, "sdc_chunks", "subject_id", "TEXT", "'science-6'")
        ensure_column_exists(conn, "sdc_glossary", "subject_id", "TEXT", "'science-6'")
        ensure_column_exists(conn, "sdc_exercises", "subject_id", "TEXT", "'science-6'")
        ensure_column_exists(conn, "sdc_videos", "subject_id", "TEXT", "'science-6'")

        # Backfill any null subject_ids for existing science content
        conn.execute("UPDATE sdc_chunks SET subject_id = 'science-6' WHERE subject_id IS NULL")
        conn.execute("UPDATE sdc_glossary SET subject_id = 'science-6' WHERE subject_id IS NULL")
        conn.execute("UPDATE sdc_videos SET subject_id = 'science-6' WHERE subject_id IS NULL")

        # 2. Ensure course 'crs-math-6' exists
        conn.execute("""
            INSERT OR REPLACE INTO courses (id, class_level, subject, title_sindhi, title_english)
            VALUES ('crs-math-6', 6, 'Math', 'رياضي (Mathematics)', 'Mathematics Class 6')
        """)

        # 3. Create or update 13 Math Units in 'lessons'
        chapters_meta = data.get("meta", {}).get("chapters", [])
        for ch in chapters_meta:
            ch_num = ch["chapter_id"]
            lesson_id = f"lesson-math-6-{ch_num}"
            title_sd = ch["title_sd"]
            title_en = ch["title_en"]

            conn.execute("""
                INSERT OR REPLACE INTO lessons (
                    id, course_id, unit_number, title_sindhi, title_english,
                    version, duration_seconds, status, summary_sindhi, created_at
                ) VALUES (?, ?, ?, ?, ?, 1, 600, 'APPROVED', ?, datetime('now'))
            """, (
                lesson_id,
                "crs-math-6",
                ch_num,
                f"{title_sd} ({title_en})",
                f"Unit {ch_num}: {title_en}",
                f"سنڌ ٽيڪسٽ بڪ بورڊ ڪلاس 6 رياضي — سبق {ch_num}: {title_sd}"
            ))

        logger.info("Synchronized %d lessons for Math-6", len(chapters_meta))

        # 4. Ingest Chunks
        chunks = data.get("chunks", [])
        chunk_count = 0
        from src.services.sdc_rag_normalization import normalize_sindhi_search_text

        for c in chunks:
            cid = c["chunk_id"]
            ch_id = c["chapter_id"]
            t_sd = c["topic_title_sd"]
            t_en = c["topic_title_en"]
            summary = c["summary_sd"]
            pdf_range = c["pdf_page_range"]
            cit = c["citation_formatted"]
            norm_sum = normalize_sindhi_search_text(summary)
            norm_tit = normalize_sindhi_search_text(t_sd)

            conn.execute("""
                INSERT OR REPLACE INTO sdc_chunks (
                    chunk_id, chapter_id, topic_title_en, topic_title_sd,
                    pdf_page_range, summary_sd, source, normalized_summary_sd,
                    normalized_title_sd, citation_formatted, subject_id
                ) VALUES (?, ?, ?, ?, ?, ?, 'STBB_Math_VI_Official_2024', ?, ?, ?, 'math-6')
            """, (cid, ch_id, t_en, t_sd, pdf_range, summary, norm_sum, norm_tit, cit))

            # Update FTS5 index
            conn.execute("DELETE FROM sdc_chunks_fts WHERE chunk_id = ?", (cid,))
            conn.execute("""
                INSERT INTO sdc_chunks_fts (chunk_id, chapter_id, topic_title_en, topic_title_sd, summary_sd)
                VALUES (?, ?, ?, ?, ?)
            """, (cid, ch_id, t_en, t_sd, summary))
            chunk_count += 1

        logger.info("Ingested %d Math chunks into sdc_chunks & sdc_chunks_fts", chunk_count)

        # 5. Ingest Glossary
        glossary = data.get("glossary", [])
        glossary_count = 0
        for g in glossary:
            ch_id = g["chapter_id"]
            term_sd = g["term_sd"]
            term_en = g["term_en"]
            definition = g["definition_sd"]
            pdf_page = g.get("pdf_page", "")
            cit = g.get("citation", pdf_page)
            norm_term = normalize_sindhi_search_text(term_sd)
            norm_def = normalize_sindhi_search_text(definition)

            # Insert glossary row
            cur = conn.execute("""
                INSERT INTO sdc_glossary (
                    chapter_id, term_en, term_sd, definition_sd,
                    pdf_page, citation_formatted, normalized_term_sd,
                    normalized_definition_sd, subject_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'math-6')
            """, (ch_id, term_en, term_sd, definition, pdf_page, cit, norm_term, norm_def))
            gid = cur.lastrowid

            # Update FTS5 index
            conn.execute("""
                INSERT INTO sdc_glossary_fts (glossary_id, chapter_id, term_en, term_sd, definition_sd)
                VALUES (?, ?, ?, ?, ?)
            """, (gid, ch_id, term_en, term_sd, definition))
            glossary_count += 1

        logger.info("Ingested %d Math glossary terms into sdc_glossary & sdc_glossary_fts", glossary_count)

        # 6. Ingest Videos
        videos = data.get("videos", [])
        vid_count = 0
        for v in videos:
            ch_id = v["chapter_id"]
            title = v["title_sd"]
            watch_url = v["watch_url"]
            dur = v.get("duration", "08:00")

            conn.execute("""
                INSERT INTO sdc_videos (
                    chapter_id, title, watch_url, duration,
                    audio_quality_notes, asr_suitability, source_status, subject_id
                ) VALUES (?, ?, ?, ?, 'Sindh Online School Math VI playlist', 'PENDING_SINDHI_NARRATION_VERIFICATION', 'CURRICULUM_OFFICIAL', 'math-6')
            """, (ch_id, title, watch_url, dur))
            vid_count += 1

        logger.info("Ingested %d Math video metadata rows into sdc_videos", vid_count)

        # 7. Ingest Exercises into interactive 'questions' table
        exercises = data.get("exercises", [])
        q_count = 0
        for ex in exercises:
            ch_id = ex["chapter_id"]
            lesson_id = f"lesson-math-6-{ch_id}"
            q_sd = ex["question_sd"]
            options = ex["options"]
            corr_val = ex["correct_answer"]
            corr_idx = 0
            if corr_val in options:
                corr_idx = options.index(corr_val)

            conn.execute("""
                INSERT OR IGNORE INTO questions (
                    id, lesson_id, timestamp_seconds, text_sindhi, options_json,
                    correct_answer_index, difficulty, topic, status, approved_by, approved_at
                ) VALUES (?, ?, 60.0, ?, ?, ?, 'MEDIUM', 'Mathematics', 'APPROVED', 'CURRICULUM_BOT', datetime('now'))
            """, (
                f"q-math-{ch_id}-{q_count+1}",
                lesson_id,
                q_sd,
                json.dumps(options, ensure_ascii=False),
                corr_idx
            ))
            q_count += 1

        logger.info("Ingested %d interactive quiz questions into questions table", q_count)

        conn.commit()
        conn.execute("VACUUM")
        logger.info("Successfully ingested Math-6 dataset and vacuumed database!")

    except Exception as e:
        conn.rollback()
        logger.error("Failed to ingest Math-6 dataset: %s", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
