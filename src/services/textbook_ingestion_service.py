"""Textbook PDF Ingestion, Parsing, Normalization and Chunking Service for SDC.
Supports Grade 6 Science and any arbitrary curriculum subject.
Handles Persian/Arabic Presentation Forms normalization, scanned PDF detection,
page boundary preservation, and safe ingestion job lifecycle.
Authored under agency-backend-architect and agency-ai-engineer.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

try:
    import pypdf
except ImportError:
    pypdf = None

from src.database.session import get_db
from src.services.sindhi_nlp import normalize_sindhi_text, tokenize_sindhi_query

logger = logging.getLogger("sdc.ingestion")

UPLOAD_BASE_DIR = Path("data/textbooks")


class TextbookIngestionService:
    """End-to-end ingestion processor for educational textbook PDFs."""

    def __init__(self, upload_dir: Path = UPLOAD_BASE_DIR):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_pdf_bytes(self, file_bytes: bytes, max_bytes: int = 100 * 1024 * 1024) -> Tuple[bool, str]:
        """Validate PDF magic bytes, file size, and non-corruption."""
        if len(file_bytes) == 0:
            return False, "Uploaded file is empty (0 bytes)."
        if len(file_bytes) > max_bytes:
            return False, f"File size exceeds maximum permitted limit ({max_bytes // (1024*1024)}MB)."
        if not file_bytes.startswith(b"%PDF-"):
            return False, "Invalid file signature; not a valid PDF document."
        return True, "Valid PDF"

    def compute_sha256(self, file_bytes: bytes) -> str:
        """Compute cryptographic SHA-256 hash of PDF for deduplication."""
        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        return hasher.hexdigest()

    def create_or_get_subject(
        self,
        class_level: int,
        slug: str,
        title_sindhi: str,
        title_english: str,
        curriculum_board: str = "Sindh Textbook Board, Jamshoro",
        description_sindhi: Optional[str] = None
    ) -> str:
        """Ensure subject entity exists in database."""
        now_iso = datetime.now(timezone.utc).isoformat()
        slug_clean = slug.strip().lower()
        with get_db() as conn:
            row = conn.execute(
                "SELECT id FROM subjects WHERE class_level = ? AND slug = ?",
                (class_level, slug_clean)
            ).fetchone()
            if row:
                return row["id"]

            new_id = f"subj-{slug_clean}-{class_level}-{uuid.uuid4().hex[:6]}"
            conn.execute(
                """
                INSERT INTO subjects (id, class_level, slug, title_sindhi, title_english, curriculum_board, description_sindhi, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (new_id, class_level, slug_clean, title_sindhi, title_english, curriculum_board, description_sindhi, now_iso)
            )
            return new_id

    def ingest_textbook_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        class_level: int,
        subject_id: str,
        title_sindhi: str,
        title_english: str,
        edition_year: str = "2024-2025"
    ) -> Dict[str, Any]:
        """Process textbook PDF through the complete ingestion lifecycle."""
        is_valid, err_msg = self.validate_pdf_bytes(file_bytes)
        if not is_valid:
            raise ValueError(err_msg)

        file_hash = self.compute_sha256(file_bytes)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check duplicate
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id, title_english, is_active FROM textbooks WHERE file_hash_sha256 = ?",
                (file_hash,)
            ).fetchone()
            if existing:
                return {
                    "status": "DUPLICATE_DETECTED",
                    "textbook_id": existing["id"],
                    "title": existing["title_english"],
                    "message": "This exact textbook PDF has already been ingested."
                }

        # Store file safely
        book_id = f"tb-{class_level}-{uuid.uuid4().hex[:8]}"
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        save_folder = self.upload_dir / str(class_level)
        save_folder.mkdir(parents=True, exist_ok=True)
        safe_path = save_folder / f"{file_hash[:16]}.pdf"

        with open(safe_path, "wb") as f:
            f.write(file_bytes)

        # Record textbook and ingestion job
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO textbooks (id, subject_id, title_sindhi, title_english, class_level, edition_year,
                                      original_filename, file_path, file_hash_sha256, file_size_bytes, page_count,
                                      version, is_active, processing_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, 0, 'PROCESSING', ?)
                """,
                (book_id, subject_id, title_sindhi, title_english, class_level, edition_year,
                 filename, str(safe_path), file_hash, len(file_bytes), now_iso)
            )
            conn.execute(
                """
                INSERT INTO ingestion_jobs (id, textbook_id, stage, progress_percentage, status, started_at)
                VALUES (?, ?, 'PARSING_PAGES', 10.0, 'IN_PROGRESS', ?)
                """,
                (job_id, book_id, now_iso)
            )

        # Parse pages
        try:
            if pypdf is None:
                return {
                    "success": False,
                    "error": "pypdf library is required for PDF ingestion. Install with: pip install pypdf",
                    "textbook_id": textbook_id
                }
            reader = pypdf.PdfReader(str(safe_path))
            total_pages = len(reader.pages)
            scanned_pages_count = 0
            good_pages_count = 0
            total_chunks = 0

            with get_db() as conn:
                conn.execute(
                    "UPDATE textbooks SET page_count = ? WHERE id = ?",
                    (total_pages, book_id)
                )

                for idx, page in enumerate(reader.pages):
                    raw_text = page.extract_text() or ""
                    clean_raw = raw_text.strip()
                    char_count = len(clean_raw)
                    words = clean_raw.split()
                    word_count = len(words)

                    # Scanned detection heuristic: under 20 chars on a standard textbook page
                    is_scanned = char_count < 20
                    quality = "SCANNED_IMAGE" if is_scanned else "GOOD"
                    if is_scanned:
                        scanned_pages_count += 1
                    else:
                        good_pages_count += 1

                    # Normalized search text (NFKC + diacritic stripped)
                    normalized_text = normalize_sindhi_text(clean_raw, strip_diacritics=True)
                    page_id = f"pg-{book_id}-{idx}"

                    conn.execute(
                        """
                        INSERT INTO textbook_pages (id, textbook_id, pdf_page_index, printed_page_number,
                                                   raw_sindhi_text, normalized_sindhi_text, character_count,
                                                   word_count, extraction_quality, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (page_id, book_id, idx, idx + 1, clean_raw, normalized_text, char_count, word_count, quality, now_iso)
                    )

                    # Create chunks for searchable pages
                    if not is_scanned and word_count >= 15:
                        # Chunking strategy: 150-250 word windows with 30 word overlap
                        step = 180
                        overlap = 30
                        for start_w in range(0, max(1, word_count), step):
                            chunk_words = words[start_w:start_w + step + overlap]
                            chunk_raw = " ".join(chunk_words)
                            chunk_norm = normalize_sindhi_text(chunk_raw, strip_diacritics=True)
                            chunk_tokens = tokenize_sindhi_query(chunk_norm)

                            chunk_id = f"chk-{book_id}-{idx}-{total_chunks}"
                            conn.execute(
                                """
                                INSERT INTO textbook_chunks (id, textbook_id, page_id, chunk_index, pdf_page_index,
                                                            printed_page_number, original_sindhi_text, normalized_search_text,
                                                            token_count, keywords_json, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (chunk_id, book_id, page_id, total_chunks, idx, idx + 1,
                                 chunk_raw, chunk_norm, len(chunk_tokens), json.dumps(chunk_tokens[:10], ensure_ascii=False), now_iso)
                            )
                            total_chunks += 1

                # Update job and textbook completion
                final_status = "OCR_REQUIRED" if scanned_pages_count > (total_pages * 0.7) else "COMPLETED"
                conn.execute(
                    """
                    UPDATE textbooks SET processing_status = ? WHERE id = ?
                    """,
                    (final_status, book_id)
                )
                conn.execute(
                    """
                    UPDATE ingestion_jobs SET stage = 'COMPLETED', progress_percentage = 100.0,
                                             total_pages = ?, processed_pages = ?, failed_pages = ?,
                                             status = 'SUCCESS', completed_at = ?
                    WHERE id = ?
                    """,
                    (total_pages, good_pages_count, scanned_pages_count, now_iso, job_id)
                )

            return {
                "status": "SUCCESS",
                "textbook_id": book_id,
                "job_id": job_id,
                "total_pages": total_pages,
                "good_text_pages": good_pages_count,
                "scanned_pages": scanned_pages_count,
                "total_chunks_created": total_chunks,
                "final_status": final_status,
                "is_active": 0,
                "activation_required": True
            }

        except Exception as e:
            logger.error(f"Textbook ingestion failed: {str(e)}", exc_info=True)
            with get_db() as conn:
                conn.execute(
                    "UPDATE textbooks SET processing_status = 'FAILED', processing_errors = ? WHERE id = ?",
                    (str(e), book_id)
                )
                conn.execute(
                    """
                    UPDATE ingestion_jobs SET stage = 'FAILED', status = 'FAILED', error_summary = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (str(e), now_iso, job_id)
                )
            raise RuntimeError(f"Ingestion processing failed: {str(e)}")

    def activate_textbook(self, textbook_id: str) -> bool:
        """Activate a validated textbook edition for student retrieval."""
        with get_db() as conn:
            tb = conn.execute("SELECT id, subject_id, class_level FROM textbooks WHERE id = ?", (textbook_id,)).fetchone()
            if not tb:
                return False
            # Deactivate other editions of same subject to ensure strict single-active edition
            conn.execute(
                "UPDATE textbooks SET is_active = 0 WHERE subject_id = ? AND class_level = ?",
                (tb["subject_id"], tb["class_level"])
            )
            conn.execute(
                "UPDATE textbooks SET is_active = 1 WHERE id = ?",
                (textbook_id,)
            )
            return True


# Global Singleton Instance
textbook_ingestion_service = TextbookIngestionService()
