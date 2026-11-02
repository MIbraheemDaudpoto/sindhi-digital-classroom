import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8')

# Login as STU-101
login_res = requests.post("http://127.0.0.1:8000/api/auth/login/student", json={
    "school_code": "SCH-HYD-01",
    "student_code": "STU-101",
    "pin": "1234"
})
token = login_res.json().get("token")

# Test 1: Single word "سيٽ" in Math Lesson 1
payload1 = {
    "question": "سيٽ",
    "lesson_id": "lesson-math-6-1",
    "class_level": 6,
    "subject_id": "math",
    "chapter_id": 1
}
res1 = requests.post("http://127.0.0.1:8000/api/tutor/ask", headers={"Authorization": f"Bearer {token}"}, json=payload1)
print("=== TEST 1: 'سيٽ' ===")
print("Status:", res1.status_code)
d1 = res1.json()
print("is_refused:", d1.get("is_refused"))
print("inference_status:", d1.get("inference_status"))
print("citations:", len(d1.get("citations", [])))
print("answer:", d1.get("answer_sindhi", "")[:150])

# Test 2: "سيٽ جا ڪيترا قسم ۽ ڪهڙا ڪهڙا" in Math Lesson 1
payload2 = {
    "question": "سيٽ جا ڪيترا قسم ۽ ڪهڙا ڪهڙا",
    "lesson_id": "lesson-math-6-1",
    "class_level": 6,
    "subject_id": "math",
    "chapter_id": 1
}
res2 = requests.post("http://127.0.0.1:8000/api/tutor/ask", headers={"Authorization": f"Bearer {token}"}, json=payload2)
print("\n=== TEST 2: 'سيٽ جا ڪيترا قسم ۽ ڪهڙا ڪهڙا' ===")
print("Status:", res2.status_code)
d2 = res2.json()
print("is_refused:", d2.get("is_refused"))
print("inference_status:", d2.get("inference_status"))
print("citations:", len(d2.get("citations", [])))
print("answer:", d2.get("answer_sindhi", "")[:150])

