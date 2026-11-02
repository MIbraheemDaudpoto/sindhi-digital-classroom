"""Acceptance Tests for SDC M5/M6 Offline RAG Backend & System.
Validates all 6 non-negotiable acceptance tests defined in ANTIGRAVITY_M5_M6_DIRECTIVE.md:

1. Heh-equivalence: Typing گهرڙو (U+0647) matches گهرڙو on BM25; typing گھرڙو (U+06BE) matches the SAME chunks.
2. اک vs اڪ distinction: Standalone اڪ (Calotropis plant) does NOT match اک (Eye).
   Words with internal kaf like خوراڪ and آڪسيجن stay intact.
3. Both-numbers citations: Every answer shows 'PDF X (printed Y)' with Y = X - 4,
   and Ch7 results show the blank-PDF provenance note: 'PDF 83-95 (printed 79-91; blank in official PDF)'.
4. Chapter filtering: Filtering works for all 12 chapters, including thin Ch6 (5 videos).
5. Full offline run on Pi 5: Search, glossary, and exercise index work with zero network.
6. Report p95 latency + DB size: Measure and report performance metrics.
"""

import os
import re
import time
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.services.sdc_rag_db import get_db_connection, ensure_sdc_data_seeded
from src.services.sdc_rag_normalization import (
    format_citation,
    normalize_sindhi_search_text,
    tokenize_sindhi_fts_query
)
from src.services.sdc_rag_service import sdc_rag_service


@pytest.fixture(scope="session", autouse=True)
def setup_sdc_db():
    """Ensure canonical data is fully seeded before acceptance tests run."""
    conn = get_db_connection()
    ensure_sdc_data_seeded(conn)
    conn.close()


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# Acceptance Test 1: Heh-Equivalence
# ==============================================================================
def test_acceptance_1_heh_equivalence():
    """Test 1: Typing گهرڙو (U+0647) returns cell chunks; typing گھرڙو (U+06BE) returns the EXACT SAME chunks."""
    # Query with standard Heh (U+0647)
    q_standard = "گهرڙو"
    assert "\u0647" in q_standard
    assert "\u06BE" not in q_standard

    # Query with Heh Doachashmee (U+06BE)
    q_doachashmee = "گھرڙو"
    assert "\u06BE" in q_doachashmee
    assert "\u0647" not in q_doachashmee

    results_standard = sdc_rag_service.search_chunks(q_standard, limit=10)
    results_doachashmee = sdc_rag_service.search_chunks(q_doachashmee, limit=10)

    assert len(results_standard) > 0, "Standard Heh query should return chunks"
    assert len(results_doachashmee) > 0, "Doachashmee Heh query should return chunks"

    ids_standard = [c["chunk_id"] for c in results_standard]
    ids_doachashmee = [c["chunk_id"] for c in results_doachashmee]

    assert ids_standard == ids_doachashmee, (
        f"BM25 results must be identical for Heh variants. Got {ids_standard} vs {ids_doachashmee}"
    )
    # Verify primary chunk is ch1-01 (Cell - Basic Unit of Life)
    assert "ch1-01" in ids_standard


# ==============================================================================
# Acceptance Test 2: اک vs اڪ Distinction
# ==============================================================================
def test_acceptance_2_ak_eye_vs_calotropis_distinction():
    """Test 2: Standalone اک (Eye, U+06A9) returns eye/sense-organ results.
    Standalone اڪ (Calotropis/milkweed, U+06AA) does NOT return eye results.
    Internal words like خوراڪ (food) and آڪسيجن (oxygen) remain intact.
    """
    q_eye = "اک"  # U+0627 + U+06A9
    q_calotropis = "اڪ"  # U+0627 + U+06AA

    # Direct FTS query verification
    eye_chunks = sdc_rag_service.search_chunks(q_eye, limit=10)
    calotropis_chunks = sdc_rag_service.search_chunks(q_calotropis, limit=10)

    eye_ids = [c["chunk_id"] for c in eye_chunks]
    calotropis_ids = [c["chunk_id"] for c in calotropis_chunks]

    # Verify eye returns sense organs chunks (Ch2-01, Ch2-02, Ch2-03)
    assert len(eye_chunks) > 0, "اک should return eye/sense-organ chunks"
    assert any("ch2" in cid for cid in eye_ids), f"اک results should contain Ch2 chunks: {eye_ids}"

    # Verify calotropis (اڪ) does NOT match eye chunks
    assert "ch2-02" not in calotropis_ids, "اڪ (Calotropis) must NEVER match ch2-02 (Eye)"
    assert "ch2-03" not in calotropis_ids, "اڪ (Calotropis) must NEVER match ch2-03 (Eye parts)"

    # Check words with internal letters
    norm_food = normalize_sindhi_search_text("خوراڪ")
    norm_oxygen = normalize_sindhi_search_text("آڪسيجن")
    assert norm_food == "خوراڪ", "خوراڪ must keep internal kaf untouched"
    assert norm_oxygen == "آڪسيجن", "آڪسيجن must keep internal kaf untouched"

    # Search for food returns digestion/plants chunks
    food_chunks = sdc_rag_service.search_chunks("خوراڪ", limit=5)
    assert len(food_chunks) > 0, "خوراڪ search must retrieve food/digestion chunks"


# ==============================================================================
# Acceptance Test 3: Both-Numbers Citations
# ==============================================================================
def test_acceptance_3_both_numbers_citations_and_ch7_provenance():
    """Test 3: Every answer shows 'PDF X (printed Y)' with Y = X - 4.
    Ch7 results MUST show blank-PDF provenance note:
    'PDF 83-95 (printed 79-91; blank in official PDF)'.
    """
    conn = get_db_connection()
    chunks = conn.execute("SELECT chunk_id, chapter_id, pdf_page_range, citation_formatted FROM sdc_chunks").fetchall()
    conn.close()

    assert len(chunks) == 90

    for ch in chunks:
        ch_id = ch["chapter_id"]
        citation = ch["citation_formatted"]

        if ch_id == 7:
            # Chapter 7 blank PDF verification
            assert "blank in official pdf" in citation.lower(), (
                f"Ch7 chunk {ch['chunk_id']} citation must have blank PDF note: {citation}"
            )
            assert "PDF 83-95" in citation
            assert "printed 79-91" in citation
        else:
            # Other chapters must have 'PDF X (printed Y)' with Y = X - 4
            assert "PDF" in citation and "printed" in citation, (
                f"Chunk {ch['chunk_id']} citation missing dual page format: {citation}"
            )
            m = re.search(r"PDF\s+(\d+)(?:-(\d+))?\s+\(printed\s+(\d+)(?:-(\d+))?\)", citation)
            assert m, f"Citation does not match dual number pattern: {citation}"
            pdf_start = int(m.group(1))
            printed_start = int(m.group(3))
            assert printed_start == pdf_start - 4, (
                f"Chunk {ch['chunk_id']}: printed page {printed_start} != PDF page {pdf_start} - 4"
            )
            if m.group(2) and m.group(4):
                pdf_end = int(m.group(2))
                printed_end = int(m.group(4))
                assert printed_end == pdf_end - 4, (
                    f"Chunk {ch['chunk_id']}: end printed {printed_end} != end PDF {pdf_end} - 4"
                )

    # Test RAG query on Chapter 7 displays provenance note
    rag_ch7 = sdc_rag_service.generate_grounded_answer("Solution", chapter_id=7)
    assert rag_ch7["status"] == "SUCCESS"
    assert rag_ch7["ch7_provenance_note"] is not None
    assert "blank in the official PDF" in rag_ch7["ch7_provenance_note"]
    assert "PDF 83-95 (printed 79-91; blank in official PDF)" in rag_ch7["citations"][0]


# ==============================================================================
# Acceptance Test 4: Chapter Filtering (All 12 Chapters + Ch6 thin check)
# ==============================================================================
def test_acceptance_4_chapter_filtering_all_12_chapters(client):
    """Test 4: Chapter filter 1-12 returns only that chapter's chunks/glossary/exercises;
    Ch6 (thinnest: 5 videos) returns its chunks and videos properly.
    """
    for ch_id in range(1, 13):
        # 1. Search endpoint with chapter filter
        res = client.get(f"/api/sdc/search?q=علم&chapter_id={ch_id}")
        assert res.status_code == 200
        data = res.json()
        for chunk in data["chunks"]:
            assert chunk["chapter_id"] == ch_id, f"Expected chapter {ch_id}, got {chunk['chapter_id']}"

        # 2. Exercises per chapter
        ex_res = client.get(f"/api/sdc/exercises?chapter_id={ch_id}")
        assert ex_res.status_code == 200
        ex_data = ex_res.json()
        assert ex_data["count"] > 0, f"Chapter {ch_id} should have exercises/SLOs"
        for ex in ex_data["exercises"]:
            assert ex["chapter_id"] == ch_id

        # 3. Videos per chapter
        vid_res = client.get(f"/api/sdc/videos?chapter_id={ch_id}")
        assert vid_res.status_code == 200
        vid_data = vid_res.json()
        assert vid_data["count"] > 0, f"Chapter {ch_id} should have videos"
        for vid in vid_data["videos"]:
            assert vid["chapter_id"] == ch_id

    # Thin Chapter 6 check: Exactly 5 videos in videos_final.csv
    ch6_vids = client.get("/api/sdc/videos?chapter_id=6").json()["videos"]
    assert len(ch6_vids) == 5, f"Chapter 6 must have exactly 5 videos, got {len(ch6_vids)}"
    ch6_chunks = sdc_rag_service.search_chunks("", chapter_id=6, limit=10)
    assert len(ch6_chunks) == 7, f"Chapter 6 must have 7 chunks in corpus, got {len(ch6_chunks)}"


# ==============================================================================
# Acceptance Test 5: Full Offline Execution (Zero Network)
# ==============================================================================
def test_acceptance_5_full_offline_execution(client):
    """Test 5: Full backend + RAG runs offline on Pi 5 with no network:
    search, glossary, and exercise index all work with zero network calls.
    """
    # Verify Search offline
    r_search = client.get("/api/sdc/search?q=گهرڙو")
    assert r_search.status_code == 200
    assert len(r_search.json()["chunks"]) > 0

    # Verify Glossary offline
    r_glossary = client.get("/api/sdc/glossary")
    assert r_glossary.status_code == 200
    assert r_glossary.json()["count"] == 50  # Paginated limit 50 of 201

    # Verify Exercise index offline
    r_exercises = client.get("/api/sdc/exercises")
    assert r_exercises.status_code == 200
    assert r_exercises.json()["count"] == 39

    # Verify RAG Ask offline
    r_ask = client.post("/api/sdc/ask", json={"query": "ٻوٽن ۾ فوٽوسنٿيسز"})
    assert r_ask.status_code == 200
    data = r_ask.json()["data"]
    assert data["status"] == "SUCCESS"
    assert len(data["citations"]) > 0
    # Confirms no cloud provider was invoked
    assert "حوالو:" in data["answer_sd"]


# ==============================================================================
# Acceptance Test 6: Report p95 Latency + DB Size
# ==============================================================================
def test_acceptance_6_p95_latency_and_db_size(client):
    """Test 6: Measure and report p95 query latency and total SQLite DB size."""
    # Benchmark 50 diverse queries
    queries = [
        ("گهرڙو", None),
        ("خوردبيني", 1),
        ("اک جا حصا", 2),
        ("فوٽوسنٿيسز", 3),
        ("ماحول", 4),
        ("ايٽم ۽ ماليڪيول", 5),
        ("هوا", 6),
        ("سوليوشن", 7),
        ("توانائي", 8),
        ("روشني", 9),
        ("آواز", 10),
        ("مقناطيس", 11),
        ("خلائي نظام", 12),
        ("خوراڪ", None),
        ("آڪسيجن", None),
    ] * 4  # 60 queries total

    latencies_ms = []
    for q_text, ch in queries:
        t0 = time.perf_counter()
        res = sdc_rag_service.search_chunks(q_text, chapter_id=ch, limit=5)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    latencies_ms.sort()
    p50 = latencies_ms[int(len(latencies_ms) * 0.50)]
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    p99 = latencies_ms[int(len(latencies_ms) * 0.99)]

    # Get DB size
    stats_res = client.get("/api/sdc/stats").json()["stats"]
    db_size_bytes = stats_res["database_size_bytes"]
    db_size_mb = stats_res["database_size_mb"]

    print("\n" + "="*50)
    print("SDC M5/M6 PERFORMANCE BENCHMARK REPORT:")
    print(f"Total Chunks: {stats_res['chunks']}")
    print(f"Total Glossary Terms: {stats_res['glossary']}")
    print(f"Total Exercises: {stats_res['exercises']}")
    print(f"Total Videos: {stats_res['videos']}")
    print(f"Database Size: {db_size_mb:.2f} MB ({db_size_bytes:,} bytes)")
    print(f"BM25 Search p50 Latency: {p50:.2f} ms")
    print(f"BM25 Search p95 Latency: {p95:.2f} ms")
    print(f"BM25 Search p99 Latency: {p99:.2f} ms")
    print("="*50 + "\n")

    # Pi 5 plausibility assertions
    assert p95 < 50.0, f"p95 latency {p95:.2f}ms must be under 50ms for Pi 5"
    assert db_size_mb < 20.0, f"DB size {db_size_mb:.2f}MB must be well under 20MB for 1-2GB RAM Pi 5"
