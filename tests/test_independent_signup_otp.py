"""Tests for Independent Student Registration, Mobile OTP, and PIN Reset.
Authored under agency-test-automation-engineer and agency-application-security-engineer.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import init_db
from data.seed_curriculum import seed_sdc_curriculum


@pytest.fixture(autouse=True)
def setup_otp_test_db():
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "otp_test.db"
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


def test_otp_flow_and_independent_signup():
    """Verify that independent student can request OTP, verify it, register with School & City, and login."""
    client = TestClient(app)

    # 1. Request OTP
    otp_req = {"phone": "03019876543", "purpose": "REGISTRATION"}
    send_resp = client.post("/api/auth/otp/send", json=otp_req)
    assert send_resp.status_code == 200
    otp_data = send_resp.json()
    assert otp_data["status"] == "ok"
    otp_code = otp_data["otp_hint"]

    # 2. Verify OTP
    verify_resp = client.post("/api/auth/otp/verify", json={"phone": "03019876543", "otp": otp_code})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified"] is True

    # 3. Register Independent Student (no preset school code, free school name + city)
    signup_payload = {
        "full_name": "احمد علي سولنگي",
        "school_name": "سنڌ ماڊل هاءِ اسڪول",
        "city": "حيدرآباد",
        "phone": "03019876543",
        "otp": otp_code,
        "pin": "4321",
        "class_level": 8,
        "language": "sindhi"
    }
    signup_resp = client.post("/api/auth/register", json=signup_payload)
    assert signup_resp.status_code == 201
    user_data = signup_resp.json()
    assert user_data["role"] == "STUDENT"
    assert user_data["full_name"] == "احمد علي سولنگي"
    assert user_data["city"] == "حيدرآباد"
    assert user_data["school_name"] == "سنڌ ماڊل هاءِ اسڪول"
    assert user_data["phone"] == "03019876543"
    assert user_data["pseudonymous_code"].startswith("STU-")
    assigned_stu_id = user_data["pseudonymous_code"]

    # 4. Student can login with Mobile Number + PIN
    login_phone_resp = client.post("/api/auth/login/student", json={
        "identifier": "03019876543",
        "pin": "4321"
    })
    assert login_phone_resp.status_code == 200
    assert login_phone_resp.json()["pseudonymous_code"] == assigned_stu_id

    # 5. Student can also login with assigned unique Student ID + PIN
    login_id_resp = client.post("/api/auth/login/student", json={
        "identifier": assigned_stu_id,
        "pin": "4321"
    })
    assert login_id_resp.status_code == 200
    assert login_id_resp.json()["pseudonymous_code"] == assigned_stu_id

    # 6. Reset PIN using Mobile OTP
    reset_otp_resp = client.post("/api/auth/otp/send", json={"phone": "03019876543", "purpose": "RESET_PIN"})
    new_otp = reset_otp_resp.json()["otp_hint"]

    reset_resp = client.post("/api/auth/reset-pin", json={
        "phone": "03019876543",
        "otp": new_otp,
        "new_pin": "8899"
    })
    assert reset_resp.status_code == 200

    # 7. Old PIN fails, new PIN succeeds
    old_pin_resp = client.post("/api/auth/login/student", json={
        "identifier": "03019876543",
        "pin": "4321"
    })
    assert old_pin_resp.status_code == 401

    new_pin_resp = client.post("/api/auth/login/student", json={
        "identifier": "03019876543",
        "pin": "8899"
    })
    assert new_pin_resp.status_code == 200
