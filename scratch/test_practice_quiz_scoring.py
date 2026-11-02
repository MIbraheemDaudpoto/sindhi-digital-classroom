import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8')

# Login as STU-101
login_res = requests.post("http://127.0.0.1:8000/api/auth/login/student", json={
    "school_code": "SCH-HYD-01",
    "student_code": "STU-101",
    "pin": "1234"
})
token = login_res.json().get("token")
headers = {"Authorization": f"Bearer {token}"}

# Generate Practice Quiz for Science Class 6 Lesson 1
gen_payload = {
    "class_level": 6,
    "subject": "Science",
    "lesson_ids": ["lesson-sci-6-1"],
    "question_count": 5,
    "difficulty": "ALL",
    "mode": "PRACTICE"
}
gen_res = requests.post("http://127.0.0.1:8000/api/quiz/generate", headers=headers, json=gen_payload)
print("Generate status:", gen_res.status_code)
quiz = gen_res.json()
session_id = quiz.get("session_id")
print("Session ID:", session_id)
print("Mode:", quiz.get("mode"))
questions = quiz.get("questions", [])
print(f"Generated {len(questions)} questions")

for idx, q in enumerate(questions):
    print(f"\n--- Question {idx+1} ---")
    print("ID:", q["id"])
    print("Text:", q["text_sindhi"])
    for opt_idx, opt in enumerate(q["options"]):
        print(f"  [{opt_idx}]: {opt}")
    
    # Let's test submitting option 0, option 1, option 2, option 3... wait! What is the correct answer according to DB?
    # Let's submit option 0 first
    ans_res = requests.post(f"http://127.0.0.1:8000/api/quiz/{session_id}/answer", headers=headers, json={
        "question_id": q["id"],
        "selected_option": 0,
        "time_taken_seconds": 3.0
    })
    ans_data = ans_res.json()
    print("Answer submitted: selected_option=0")
    print("Response is_correct:", ans_data.get("is_correct"))
    print("Response correct_answer_index:", ans_data.get("correct_answer_index"))
    print("Response message:", ans_data.get("message"))

