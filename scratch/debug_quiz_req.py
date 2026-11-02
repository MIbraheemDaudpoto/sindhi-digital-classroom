import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests

login_resp = requests.post("http://127.0.0.1:8000/api/auth/login/student", json={
    "school_code": "SCH-HYD-01",
    "student_code": "STU-101",
    "pin": "1234"
})
print("Login status:", login_resp.status_code)
auth_data = login_resp.json()
jwt_token = auth_data.get("token") or auth_data.get("access_token")
print("User ID:", auth_data.get("user_id"), "Token:", jwt_token[:20] if jwt_token else None)

resp = requests.post("http://127.0.0.1:8000/api/quiz/generate", headers={
    "Authorization": f"Bearer {jwt_token}"
}, json={
    "class_level": 6,
    "subject": "Math",
    "lesson_ids": ["lesson-math-6-1"],
    "question_count": 10,
    "mode": "PRACTICE",
    "difficulty": "MEDIUM"
})
print("Quiz status:", resp.status_code)
if resp.status_code != 201:
    print("Error:", resp.text)
else:
    data = resp.json()
    qs = data.get("questions", [])
    print(f"Generated {len(qs)} questions:")
    for i, q in enumerate(qs):
        print(f"  {i+1}. {q['text_sindhi']}")
