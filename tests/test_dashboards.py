"""Tests for Student, Teacher, and Officer Dashboards (FR-29, FR-30, FR-31).
Authored under agency-analytics-reporter and agency-test-automation-engineer.
"""

from pathlib import Path
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
    test_db = test_dir / "dashboards_test.db"
    if test_db.exists():
        test_db.unlink(missing_ok=True)
    orig = settings.database_path
    orig_roles = list(settings.active_pilot_roles)
    settings.database_path = str(test_db)
    settings.active_pilot_roles = ["STUDENT", "TEACHER", "OFFICER", "SUPER_ADMIN", "ADMIN"]
    init_db(str(test_db))
    seed_sdc_curriculum(str(test_db))
    yield str(test_db)
    settings.database_path = orig
    settings.active_pilot_roles = orig_roles
    if test_db.exists():
        test_db.unlink(missing_ok=True)


def test_student_dashboard():
    """Verify student dashboard returns progress, score, and next recommended unit (FR-29)."""
    client = TestClient(app)
    res = client.get("/api/dashboards/student?user_id=usr-stu-101")
    assert res.status_code == 200
    data = res.json()
    assert data["student_code"] == "STU-101"
    assert "completed_lessons_count" in data
    assert "total_quiz_score_pct" in data
    assert "active_streak_days" in data
    assert data["active_streak_days"] >= 1
    assert "streak_badge_sindhi" in data


def test_teacher_dashboard_with_cohens_d():
    """Verify teacher dashboard returns class analytics, Cohen's d gain, and approval count (FR-30)."""
    client = TestClient(app)
    res = client.get("/api/dashboards/teacher?teacher_id=usr-tch-01")
    assert res.status_code == 200
    data = res.json()
    assert data["total_students_enrolled"] >= 1
    assert data["cohens_d_gain"] > 0.0 # Positive learning gain vs baseline (PRD target)
    assert data["pending_approval_questions_count"] >= 1


def test_officer_dashboard_district_summaries():
    """Verify district summaries for education officers (FR-31)."""
    client = TestClient(app)
    res = client.get("/api/dashboards/officer?user_id=usr-off-01")
    assert res.status_code == 200
    districts = res.json()
    assert len(districts) >= 1
    d_names = [d["district"] for d in districts]
    assert "Hyderabad" in d_names or "Larkana" in d_names
