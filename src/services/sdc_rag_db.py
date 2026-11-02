"""SDC RAG Database Ingestion & Repository.
Builds the SQLite database with FTS5 BM25 indexes and ingests the 4 canonical files:
1. rag_chunks_sindhi.jsonl
2. sindhi_science_glossary.csv
3. exercise_page_map.csv
4. videos_final.csv

Adheres strictly to ANTIGRAVITY_M5_M6_DIRECTIVE.md.
"""

import csv
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from src.config import settings
from src.services.sdc_rag_normalization import (
    format_citation,
    normalize_sindhi_search_text,
    tokenize_sindhi_fts_query
)

logger = logging.getLogger("sdc.rag_db")

# Locate canonical input directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
M3_DIR = ROOT_DIR / "SDC_RAG_PACKAGE_for_Antigravity" / "m3"
if not M3_DIR.exists():
    M3_DIR = ROOT_DIR / "m3"


import threading

_local = threading.local()

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get SQLite database connection in WAL mode with fast row factory."""
    target_path = db_path or str(settings.get_db_path())
    conn = sqlite3.connect(target_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA cache_size = -64000")  # ~64MB cache
    conn.execute("PRAGMA mmap_size = 268435456")  # 256MB memory map for ultra-fast BM25
    return conn


def init_sdc_rag_schema(conn: sqlite3.Connection):
    """Create all relational tables and FTS5 BM25 virtual tables."""
    cursor = conn.cursor()

    # 1. Chunks Table (90 curriculum units)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sdc_chunks (
        chunk_id TEXT PRIMARY KEY,
        chapter_id INTEGER NOT NULL,
        topic_title_en TEXT NOT NULL,
        topic_title_sd TEXT NOT NULL,
        pdf_page_range TEXT NOT NULL,
        summary_sd TEXT NOT NULL,
        source TEXT NOT NULL,
        normalized_summary_sd TEXT NOT NULL,
        normalized_title_sd TEXT NOT NULL,
        citation_formatted TEXT NOT NULL
    )
    """)

    # 2. Glossary Table (201 bilingual terms)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sdc_glossary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id INTEGER,
        term_en TEXT NOT NULL,
        term_sd TEXT NOT NULL,
        definition_sd TEXT NOT NULL,
        pdf_page TEXT NOT NULL,
        citation_formatted TEXT NOT NULL,
        normalized_term_sd TEXT NOT NULL,
        normalized_definition_sd TEXT NOT NULL
    )
    """)

    # 3. Exercises Table (39 exercises/SLOs/practicals)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sdc_exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id INTEGER NOT NULL,
        item_type TEXT NOT NULL,
        topic_en TEXT NOT NULL,
        pdf_page TEXT NOT NULL,
        citation_formatted TEXT NOT NULL,
        sos_video_id TEXT,
        sos_video_title TEXT
    )
    """)

    # 4. Videos Table (113 Sindh Online School videos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sdc_videos (
        id INTEGER PRIMARY KEY,
        chapter_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        watch_url TEXT NOT NULL,
        duration TEXT,
        audio_quality_notes TEXT,
        asr_suitability TEXT,
        source_status TEXT
    )
    """)

    # 5. FTS5 Virtual Tables using unicode61 tokenizer for BM25 ranking
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS sdc_chunks_fts USING fts5(
        chunk_id UNINDEXED,
        chapter_id UNINDEXED,
        topic_title_en,
        topic_title_sd,
        summary_sd,
        tokenize='unicode61'
    )
    """)

    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS sdc_glossary_fts USING fts5(
        glossary_id UNINDEXED,
        chapter_id UNINDEXED,
        term_en,
        term_sd,
        definition_sd,
        tokenize='unicode61'
    )
    """)

    conn.commit()


def ingest_canonical_files(conn: sqlite3.Connection, m3_dir: Optional[Path] = None):
    """Read and ingest the 4 canonical input files with full normalization."""
    base_dir = m3_dir or M3_DIR
    cursor = conn.cursor()

    # Clear existing SDC data for a clean ingest
    cursor.execute("DELETE FROM sdc_chunks")
    cursor.execute("DELETE FROM sdc_glossary")
    cursor.execute("DELETE FROM sdc_exercises")
    cursor.execute("DELETE FROM sdc_videos")
    cursor.execute("DELETE FROM sdc_chunks_fts")
    cursor.execute("DELETE FROM sdc_glossary_fts")

    # A. Ingest rag_chunks_sindhi.jsonl (90 chunks)
    jsonl_path = base_dir / "rag_chunks_sindhi.jsonl"
    chunk_count = 0
    if jsonl_path.exists():
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                ch_id = int(item["chapter_id"])
                norm_summary = normalize_sindhi_search_text(item["summary_sd"])
                norm_title = normalize_sindhi_search_text(item["topic_title_sd"])
                citation = format_citation(item["pdf_page_range"], ch_id)

                cursor.execute("""
                INSERT INTO sdc_chunks (
                    chunk_id, chapter_id, topic_title_en, topic_title_sd,
                    pdf_page_range, summary_sd, source,
                    normalized_summary_sd, normalized_title_sd, citation_formatted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["chunk_id"], ch_id, item["topic_title_en"], item["topic_title_sd"],
                    item["pdf_page_range"], item["summary_sd"], item.get("source", "companion+curriculum"),
                    norm_summary, norm_title, citation
                ))

                # Populate FTS5 table
                cursor.execute("""
                INSERT INTO sdc_chunks_fts (
                    chunk_id, chapter_id, topic_title_en, topic_title_sd, summary_sd
                ) VALUES (?, ?, ?, ?, ?)
                """, (
                    item["chunk_id"], ch_id, item["topic_title_en"], norm_title, norm_summary
                ))
                chunk_count += 1

    # B. Ingest sindhi_science_glossary.csv (201 rows)
    glossary_path = base_dir / "sindhi_science_glossary.csv"
    glossary_count = 0
    if glossary_path.exists():
        with open(glossary_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                norm_term = normalize_sindhi_search_text(row["term_sd"])
                norm_def = normalize_sindhi_search_text(row["definition_sd"])
                pdf_page = row.get("pdf_page", "")
                
                # Derive chapter_id if possible from citation or text
                ch_id = None
                if "blank in official pdf" in pdf_page.lower():
                    ch_id = 7

                citation = format_citation(pdf_page, ch_id)

                cursor.execute("""
                INSERT INTO sdc_glossary (
                    chapter_id, term_en, term_sd, definition_sd, pdf_page,
                    citation_formatted, normalized_term_sd, normalized_definition_sd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ch_id, row["term_en"], row["term_sd"], row["definition_sd"],
                    pdf_page, citation, norm_term, norm_def
                ))
                glossary_id = cursor.lastrowid

                # Populate FTS5 table
                cursor.execute("""
                INSERT INTO sdc_glossary_fts (
                    glossary_id, chapter_id, term_en, term_sd, definition_sd
                ) VALUES (?, ?, ?, ?, ?)
                """, (
                    glossary_id, ch_id, row["term_en"], norm_term, norm_def
                ))
                glossary_count += 1

    # C. Ingest exercise_page_map.csv (39 rows)
    exercise_path = base_dir / "exercise_page_map.csv"
    exercise_count = 0
    if exercise_path.exists():
        with open(exercise_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ch_id = int(row["chapter_id"])
                pdf_page = row.get("pdf_page", "")
                citation = format_citation(pdf_page, ch_id)
                cursor.execute("""
                INSERT INTO sdc_exercises (
                    chapter_id, item_type, topic_en, pdf_page,
                    citation_formatted, sos_video_id, sos_video_title
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    ch_id, row["item_type"], row["topic_en"], pdf_page,
                    citation, row.get("sos_video_id", ""), row.get("sos_video_title", "")
                ))
                exercise_count += 1

    # D. Ingest videos_final.csv (113 videos)
    video_path = base_dir / "videos_final.csv"
    video_count = 0
    if video_path.exists():
        with open(video_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vid_id = int(row["id"])
                ch_id = int(row["chapter"])
                cursor.execute("""
                INSERT INTO sdc_videos (
                    id, chapter_id, title, watch_url, duration,
                    audio_quality_notes, asr_suitability, source_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vid_id, ch_id, row["title"], row["watch_url"], row.get("duration", ""),
                    row.get("audio_quality_notes", ""), row.get("asr_suitability", ""),
                    row.get("source_status", "")
                ))
                video_count += 1

    conn.commit()
    logger.info(
        f"SDC Ingestion Complete: {chunk_count} chunks, {glossary_count} glossary terms, "
        f"{exercise_count} exercises, {video_count} videos."
    )
    return {
        "chunks": chunk_count,
        "glossary": glossary_count,
        "exercises": exercise_count,
        "videos": video_count
    }


def ensure_sdc_data_seeded(conn: Optional[sqlite3.Connection] = None):
    """Ensure SDC tables exist and are populated with the 90 chunks and canonical data."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        init_sdc_rag_schema(conn)
        row = conn.execute("SELECT count(*) as cnt FROM sdc_chunks").fetchone()
        fts_row = conn.execute("SELECT count(*) as cnt FROM sdc_chunks_fts").fetchone()
        if not row or row["cnt"] < 90 or not fts_row or fts_row["cnt"] < 90:
            logger.info("SDC chunks table or FTS index empty/incomplete. Ingesting canonical files...")
            ingest_canonical_files(conn)
    finally:
        if should_close:
            conn.close()
