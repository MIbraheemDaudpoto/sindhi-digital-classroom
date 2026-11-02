"""SDC Pilot RAG API Router.
Exposes endpoints for offline search, question answering, glossary, exercises,
videos, and performance stats.
Directly adheres to ANTIGRAVITY_M5_M6_DIRECTIVE.md.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.services.sdc_rag_service import sdc_rag_service
from src.services.sdc_rag_db import get_db_connection

router = APIRouter(prefix="/api/sdc", tags=["SDC Offline RAG & Curriculum"])


class SDCAskRequest(BaseModel):
    query: str = Field(..., description="Student or teacher question in Sindhi or English", min_length=1, max_length=500)
    chapter_id: Optional[int] = Field(None, ge=1, le=13, description="Optional chapter filter (1-13)")
    subject_id: Optional[str] = Field(None, description="Optional subject filter: math or science")
    context_query: Optional[str] = Field(default=None, description="Previous turn query or topic context for follow-up questions")


@router.get("/search")
async def search_sdc(
    q: str = Query(..., min_length=1, max_length=500, description="Search query in Sindhi or English"),
    chapter_id: Optional[int] = Query(None, ge=1, le=13, description="Optional chapter filter (1-13)"),
    subject_id: Optional[str] = Query(None, description="Optional subject filter: math or science"),
    limit: int = Query(10, ge=1, le=50)
):
    """BM25 Full-text search across Class 6 Science and Mathematics chunks and glossary terms."""
    chunks = sdc_rag_service.search_chunks(q, chapter_id=chapter_id, subject_id=subject_id, limit=limit)
    glossary = sdc_rag_service.search_glossary(q, chapter_id=chapter_id, subject_id=subject_id, limit=5)
    return {
        "status": "success",
        "query": q,
        "chapter_id": chapter_id,
        "subject_id": subject_id,
        "total_chunks": len(chunks),
        "total_glossary": len(glossary),
        "chunks": chunks,
        "glossary": glossary
    }


@router.post("/ask")
async def ask_rag_assistant(req: SDCAskRequest):
    """RAG QA endpoint executing prompt template, context retrieval, and grounded answer synthesis."""
    result = sdc_rag_service.generate_grounded_answer(
        req.query,
        chapter_id=req.chapter_id,
        subject_id=req.subject_id,
        context_query=req.context_query
    )
    return {
        "status": "success",
        "data": result
    }


@router.get("/glossary")
async def get_glossary(
    q: Optional[str] = Query(None, description="Search query for term or definition"),
    chapter_id: Optional[int] = Query(None, ge=1, le=13, description="Filter by chapter 1-13"),
    subject_id: Optional[str] = Query(None, description="Filter by subject: math or science"),
    letter: Optional[str] = Query(None, description="Filter by starting letter (Sindhi or English)"),
    limit: int = Query(50, ge=1, le=350)
):
    """Browse or search bilingual Science and Mathematics terms with definitions and citations."""
    terms = sdc_rag_service.search_glossary(query=q, chapter_id=chapter_id, alphabet_letter=letter, subject_id=subject_id, limit=limit)
    return {
        "status": "success",
        "count": len(terms),
        "terms": terms
    }


@router.get("/exercises")
async def get_exercises(
    chapter_id: Optional[int] = Query(None, ge=1, le=13, description="Filter by chapter 1-13")
):
    """Retrieve review questions, practicals, SLOs, and linked videos."""
    exercises = sdc_rag_service.get_exercises(chapter_id=chapter_id)
    return {
        "status": "success",
        "count": len(exercises),
        "exercises": exercises
    }


@router.get("/videos")
async def get_videos(
    chapter_id: Optional[int] = Query(None, ge=1, le=13, description="Filter by chapter 1-13")
):
    """Retrieve Sindh Online School videos with watch URLs, durations, and ratings."""
    videos = sdc_rag_service.get_videos(chapter_id=chapter_id)
    return {
        "status": "success",
        "count": len(videos),
        "videos": videos
    }


@router.get("/stats")
async def get_system_stats():
    """Report database size, chunk counts, and performance metrics."""
    import os
    from src.config import settings
    conn = get_db_connection()
    try:
        chunk_count = conn.execute("SELECT count(*) FROM sdc_chunks").fetchone()[0]
        glossary_count = conn.execute("SELECT count(*) FROM sdc_glossary").fetchone()[0]
        exercise_count = conn.execute("SELECT count(*) FROM sdc_exercises").fetchone()[0]
        video_count = conn.execute("SELECT count(*) FROM sdc_videos").fetchone()[0]
        db_file = settings.get_db_path()
        db_size_bytes = os.path.getsize(db_file) if os.path.exists(db_file) else 0

        return {
            "status": "success",
            "stats": {
                "chunks": chunk_count,
                "glossary": glossary_count,
                "exercises": exercise_count,
                "videos": video_count,
                "database_size_bytes": db_size_bytes,
                "database_size_mb": round(db_size_bytes / (1024 * 1024), 2),
                "journal_mode": "WAL",
                "hardware_target": "Raspberry Pi 5 (ARM64)"
            }
        }
    finally:
        conn.close()
