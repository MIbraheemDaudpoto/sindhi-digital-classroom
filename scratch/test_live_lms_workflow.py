import urllib.request
import urllib.parse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def request_json(url, data=None, headers=None, method="GET"):
    req_headers = headers or {}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))

def main():
    print("=" * 60)
    print("🚀 SDC LMS LIVE WORKFLOW TEST RUNNER")
    print("=" * 60)

    # 1. Login
    print("\n[Step 1] Logging in as student STU-101...")
    code, auth_data = request_json(f"{BASE_URL}/api/auth/login/student", data={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    }, method="POST")
    assert code == 200, f"Login failed: {code}"
    token = auth_data["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Authenticated! Token acquired for {auth_data['user']['pseudonymous_code']}")

    # 2. Browse Lessons & Curriculum
    print("\n[Step 2] Browsing Class 6 Curriculum...")
    code, courses_data = request_json(f"{BASE_URL}/api/lessons?class_level=6", headers=headers)
    assert code == 200
    print(f"✅ Retrieved {len(courses_data)} courses:")
    for c in courses_data:
        print(f"   - {c['subject']} ({c['title_sindhi']}): {len(c['lessons'])} lessons")

    # 3. Test Science Quiz Generation
    print("\n[Step 3] Generating Real-Time Quiz for Science Unit 1 (The Cell)...")
    code, quiz_sci = request_json(f"{BASE_URL}/api/quiz/generate", data={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-sci-6-1"],
        "question_count": 3,
        "mode": "practice",
        "difficulty": "MEDIUM"
    }, headers=headers, method="POST")
    assert code == 201, f"Failed: {code}"
    print(f"✅ Science Quiz Generated! Session ID: {quiz_sci['session_id']}")
    print(f"   Provider: {quiz_sci['provider_type']}")
    print(f"   Status Message: {quiz_sci.get('ai_status_message')}")
    
    FORBIDDEN_PHRASES = [
        "هي تصور درسي نصاب ۾ شامل ناهي",
        "مٿيان سمورا جواب نامڪمل آهن",
        "هي عمل صرف مصنوعي حالتن ۾ ٿئي ٿو",
        "غير ضروري معلومات",
        "ٻيو آپشن"
    ]

    for i, q in enumerate(quiz_sci["questions"], 1):
        print(f"\n   [Q{i}] {q['text_sindhi']}")
        for opt_idx, opt in enumerate(q["options"]):
            print(f"        {chr(65+opt_idx)}: {opt}")
            for fb in FORBIDDEN_PHRASES:
                assert fb not in opt, f"Forbidden boilerplate phrase '{fb}' found in option: {opt}"
        print(f"   Lesson: {q['lesson_title_sd']} ({q['lesson_id']})")

    # 4. Answer First Question in Practice Mode
    print("\n[Step 4] Submitting Practice Answer for Q1...")
    q1 = quiz_sci["questions"][0]
    code, ans_fb = request_json(
        f"{BASE_URL}/api/quiz/{quiz_sci['session_id']}/answer",
        data={"question_id": q1["id"], "selected_option": 0, "time_taken_seconds": 15},
        headers=headers,
        method="POST"
    )
    assert code == 200
    print(f"✅ Immediate Feedback: {ans_fb['message']}")
    print(f"   Correct Answer Index: {ans_fb['correct_answer_index']}")
    print(f"   Citation: {ans_fb['citation']}")
    print(f"   Explanation: {ans_fb['explanation_sindhi']}")

    # Answer remaining questions
    for q in quiz_sci["questions"][1:]:
        request_json(
            f"{BASE_URL}/api/quiz/{quiz_sci['session_id']}/answer",
            data={"question_id": q["id"], "selected_option": 0, "time_taken_seconds": 10},
            headers=headers,
            method="POST"
        )

    # 5. Submit Final Quiz
    print("\n[Step 5] Submitting Final Quiz Session...")
    code, submit_resp = request_json(
        f"{BASE_URL}/api/quiz/{quiz_sci['session_id']}/submit",
        data={"answers": {}},
        headers=headers,
        method="POST"
    )
    assert code == 200
    print(f"✅ Final Result: Score {submit_resp['score']}%, Passed: {submit_resp['passed']}")
    print(f"   Correct: {submit_resp['correct_count']}/{submit_resp['total_questions']}")
    print(f"   Lesson Breakdown: {submit_resp['per_lesson_breakdown']}")

    # 6. Test Mathematics Quiz Generation
    print("\n[Step 6] Generating Real-Time Quiz for Mathematics Unit 1 (Sets)...")
    code, quiz_math = request_json(f"{BASE_URL}/api/quiz/generate", data={
        "class_level": 6,
        "subject": "Mathematics",
        "lesson_ids": ["lesson-math-6-1"],
        "question_count": 3,
        "mode": "practice",
        "difficulty": "MEDIUM"
    }, headers=headers, method="POST")
    assert code == 201
    print(f"✅ Math Quiz Generated! Session ID: {quiz_math['session_id']}")
    for i, q in enumerate(quiz_math["questions"], 1):
        print(f"\n   [Math Q{i}] {q['text_sindhi']}")
        for opt_idx, opt in enumerate(q["options"]):
            print(f"        {chr(65+opt_idx)}: {opt}")
            for fb in FORBIDDEN_PHRASES:
                assert fb not in opt, f"Forbidden boilerplate phrase '{fb}' found in option: {opt}"

    # 7. Check Student Progress Endpoint
    print("\n[Step 7] Checking Student Progress Tracking...")
    code, prog_data = request_json(f"{BASE_URL}/api/progress/student", headers=headers)
    assert code == 200
    print(f"✅ Student Progress Retrieved: {len(prog_data.get('lessons', []))} lessons tracked.")

    print("\n" + "=" * 60)
    print("🎉 ALL END-TO-END LMS WORKFLOW STEPS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
