"""Tests for Class 6 Sindhi Curriculum Pilot (Phase 2.3).
Validates Sindhi subject course structure, lesson retrieval,
curriculum manifest integrity, and graceful handling of pending textbook status.
"""

from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.database.session import init_db
from data.seed_curriculum import seed_sdc_curriculum
from src.config import settings


@pytest.fixture(autouse=True)
def setup_test_db():
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "class6_sindhi_test.db"
    if test_db.exists():
        test_db.unlink(missing_ok=True)
    orig = settings.database_path
    settings.database_path = str(test_db)
    init_db(str(test_db))
    seed_sdc_curriculum(str(test_db))
    yield str(test_db)
    settings.database_path = orig
    if test_db.exists():
        test_db.unlink(missing_ok=True)


def test_browse_class6_sindhi_curriculum():
    """Verify Class 6 Sindhi course exists and has seeded lessons."""
    client = TestClient(app)
    res = client.get("/api/lessons?class_level=6&subject=Sindhi")
    assert res.status_code == 200
    courses = res.json()
    assert len(courses) >= 1
    course = courses[0]
    assert course["class_level"] == 6
    assert course["subject"] == "Sindhi"
    assert "سنڌي" in course["title_sindhi"]
    assert len(course["lessons"]) >= 1
    
    lesson = course["lessons"][0]
    assert lesson["id"] == "lesson-sindhi-6-1"
    assert "شاهه عبداللطيف" in lesson["title_sindhi"]
    assert lesson["unit_number"] == 1


def test_class6_sindhi_lesson_detail():
    """Verify detailed retrieval of Class 6 Sindhi lesson."""
    client = TestClient(app)
    res = client.get("/api/lessons/lesson-sindhi-6-1?user_id=usr-stu-101")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "lesson-sindhi-6-1"
    assert data["title_english"] == "Life and Poetry of Shah Latif"
    assert "video_fallback_url" in data


def test_curriculum_manifest_integrity():
    """Verify curriculum_manifest.json accurately documents Class 6 Sindhi pilot."""
    manifest_path = Path("data/curriculum_manifest.json")
    assert manifest_path.exists(), "curriculum_manifest.json must exist"
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    assert "_schema_version" in manifest
    pilots = manifest.get("pilots", [])
    assert len(pilots) >= 1
    
    c6_sindhi = next((p for p in pilots if p.get("pilot_id") == "CLASS6_SINDHI_2026"), None)
    assert c6_sindhi is not None
    assert c6_sindhi["class_level"] == 6
    assert c6_sindhi["subject"] == "Sindhi"
    assert c6_sindhi["source_document"]["actual_file_found"] is True
    assert c6_sindhi["source_document"]["ingestion_status"] in {"PENDING_TEXTBOOK_PDF", "SCANNED_PDF_OCR_REQUIRED"}
    assert c6_sindhi["youtube_channel"]["channel_verified"] is True
