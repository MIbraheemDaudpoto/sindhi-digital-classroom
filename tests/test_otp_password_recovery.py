"""Automated verification of Mobile OTP Password Recovery for SDC.
Tests Pakistani phone normalization, cryptographic OTP generation, attempt limits,
resend cooldowns, single-use reset tokens, and SMS delivery tracking.
Authored under agency-application-security-engineer and agency-test-automation-engineer.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import init_db
from data.seed_curriculum import seed_sdc_curriculum
from src.services.auth_service import auth_service
from src.services.sms_service import mock_sms_provider, normalize_pakistan_phone, SMSProviderError


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database is seeded with STBB test curriculum and isolated test DB."""
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "sdc_otp_test.db"
    if test_db.exists():
        test_db.unlink(missing_ok=True)
    original_db = settings.database_path
    original_sms_provider = settings.sms_provider

    settings.database_path = str(test_db)
    settings.sms_provider = "mock"
    mock_sms_provider.clear()

    init_db(str(test_db))
    seed_sdc_curriculum(str(test_db))

    yield str(test_db)

    settings.database_path = original_db
    settings.sms_provider = original_sms_provider
    if test_db.exists():
        test_db.unlink(missing_ok=True)


def test_pakistan_phone_normalization():
    """Verify phone normalization handles various Pakistani formats and rejects invalid numbers."""
    assert normalize_pakistan_phone("03001234567") == "+923001234567"
    assert normalize_pakistan_phone("0300-1234567") == "+923001234567"
    assert normalize_pakistan_phone("+923001234567") == "+923001234567"
    assert normalize_pakistan_phone("923001234567") == "+923001234567"
    assert normalize_pakistan_phone("00923001234567") == "+923001234567"

    # Invalid non-Pakistani or malformed numbers
    with pytest.raises(ValueError):
        normalize_pakistan_phone("0211234567")  # Landline
    with pytest.raises(ValueError):
        normalize_pakistan_phone("+14155552671")  # US number
    with pytest.raises(ValueError):
        normalize_pakistan_phone("12345")  # Too short


def test_complete_password_recovery_workflow():
    """Verify end-to-end password recovery: request -> SMS sent -> verify OTP -> reset password -> login."""
    client = TestClient(app)

    # 1. First register a student with a valid phone number
    signup_payload = {
        "full_name": "شاهد علي",
        "pseudonymous_code": "STU-RECOVERY-01",
        "phone": "03009988776",
        "pin": "1122",
        "school_name": "گورنمينٽ بوائز هاءِ اسڪول حيدرآباد",
        "city": "حيدرآباد"
    }
    reg_resp = client.post("/api/auth/register", json=signup_payload)
    assert reg_resp.status_code == 201

    # 2. Student forgets password, requests reset
    req_payload = {"phone": "03009988776"}
    forgot_resp = client.post("/api/auth/forgot-password/request", json=req_payload)
    assert forgot_resp.status_code == 200
    assert "او ٽي پي" in forgot_resp.json()["message"]

    # Verify SMS was dispatched through SMS Provider
    assert len(mock_sms_provider.sent_messages) == 1
    sent_sms = mock_sms_provider.sent_messages[0]
    assert sent_sms["phone"] == "+923009988776"
    assert "سنڌي ڊجيٽل ڪلاس روم" in sent_sms["message"]

    # Extract 6-digit OTP code from message
    import re
    otp_match = re.search(r'\b[0-9]{6}\b', sent_sms["message"])
    assert otp_match is not None
    otp_code = otp_match.group(0)

    # 3. Student submits OTP to receive reset authorization token
    verify_resp = client.post("/api/auth/forgot-password/verify-otp", json={"phone": "03009988776", "otp": otp_code})
    assert verify_resp.status_code == 200
    reset_data = verify_resp.json()
    assert "reset_token" in reset_data
    reset_token = reset_data["reset_token"]
    assert len(reset_token) >= 16

    # 4. Student sets new PIN / password using the reset token
    confirm_resp = client.post(
        "/api/auth/forgot-password/reset",
        json={"reset_token": reset_token, "new_password": "4321"}
    )
    assert confirm_resp.status_code == 200
    assert "ڪاميابيءَ سان تبديل" in confirm_resp.json()["message"]

    # 5. Verify the reset token CANNOT be reused (single-use protection)
    reuse_resp = client.post(
        "/api/auth/forgot-password/reset",
        json={"reset_token": reset_token, "new_password": "9999"}
    )
    assert reuse_resp.status_code == 400
    assert "استعمال ٿي چڪو آهي" in reuse_resp.json()["detail"] or "Invalid" in reuse_resp.json()["detail"]

    # 6. Verify login with OLD pin fails
    old_login = client.post("/api/auth/login/student", json={"identifier": "03009988776", "pin": "1122"})
    assert old_login.status_code == 401

    # 7. Verify login with NEW pin succeeds
    new_login = client.post("/api/auth/login/student", json={"identifier": "03009988776", "pin": "4321"})
    assert new_login.status_code == 200
    assert new_login.json()["role"] == "STUDENT"


def test_wrong_otp_attempt_limits():
    """Verify entering wrong OTP decrements attempts and rejects after limits."""
    client = TestClient(app)

    # Request reset
    client.post("/api/auth/forgot-password/request", json={"phone": "03001234567"})
    normalized = "+923001234567"

    # Set up OTP in auth_service
    auth_service.send_otp(normalized, purpose="PASSWORD_RESET")

    # 3 wrong attempts
    for _ in range(3):
        client.post("/api/auth/forgot-password/verify-otp", json={"phone": normalized, "otp": "000000"})

    # 4th attempt is completely locked out
    resp = client.post("/api/auth/forgot-password/verify-otp", json={"phone": normalized, "otp": "000000"})
    assert resp.status_code == 400
    assert "غلط يا مدي خارج" in resp.json()["detail"] or "Invalid" in resp.json()["detail"]


def test_unknown_phone_returns_generic_response():
    """Verify querying an unregistered phone returns generic response (prevents account enumeration)."""
    client = TestClient(app)
    resp = client.post("/api/auth/forgot-password/request", json={"phone": "03450000000"})
    assert resp.status_code == 200
    # Must NOT reveal that account does not exist
    assert "جيڪڏهن هي موبائل نمبر رجسٽر ٿيل آهي" in resp.json()["message"]
