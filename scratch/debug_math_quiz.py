import sys
sys.path.insert(0, ".")
import json
import sqlite3
from src.api.app import app
from fastapi.testclient import TestClient
from src.services.auth_service import auth_service

client = TestClient(app)
auth_service._rate_limits.clear()
resp = client.post("/api/auth/login/student", json={
    "school_code": "SCH-HYD-01",
    "student_code": "STU-101",
    "pin": "1234"
})
token = resp.json()["token"]

resp1 = client.post("/api/quiz/generate", headers={"Authorization": f"Bearer {token}"}, json={
    "class_level": 6,
    "subject": "Math",
    "lesson_ids": ["lesson-math-6-1"],
    "question_count": 3
})
print("Status:", resp1.status_code)
with open("scratch/debug_res.txt", "w", encoding="utf-8") as f:
    f.write(resp1.text)
print("Wrote response to scratch/debug_res.txt")
