import json
import urllib.request
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 1. Login to obtain real session token
login_req = urllib.request.Request(
    "http://127.0.0.1:8000/api/auth/login/student",
    data=json.dumps({"identifier": "STU-101", "pin": "1234"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
login_resp = json.loads(urllib.request.urlopen(login_req).read().decode("utf-8"))
token = login_resp["token"]
print(f"Logged in STU-101, session token: {token[:16]}...")

# 2. Generate a quiz session
url_gen = "http://127.0.0.1:8000/api/quiz/generate"
payload_gen = {
    "class_level": 6,
    "subject": "Science",
    "lesson_ids": ["lesson-sci-6-1"],
    "question_count": 2,
    "mode": "PRACTICE"
}
req = urllib.request.Request(url_gen, data=json.dumps(payload_gen).encode("utf-8"), headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode("utf-8"))
session_id = data["session_id"]
questions = data["questions"]
print(f"Generated Quiz Session: {session_id} | Mode: {data['mode']}")
print(f"Total Questions: {len(questions)}")

# Inspect first question snapshot in DB to find correct answer
import sqlite3
conn = sqlite3.connect("data/sdc_platform.db")
conn.row_factory = sqlite3.Row
sess_row = conn.execute("SELECT * FROM quiz_sessions WHERE id = ?", (session_id,)).fetchone()
snapshots = json.loads(sess_row["questions_snapshot_json"])
q1 = snapshots[0]
corr_idx = q1["correct_answer_index"]
wrong_idx = (corr_idx + 1) % len(q1["options"])

print(f"\nQ1: {q1['text_sindhi']}")
print(f"Correct Index: {corr_idx} -> '{q1['options'][corr_idx]}'")
print(f"Wrong Index: {wrong_idx} -> '{q1['options'][wrong_idx]}'")

# Test submitting CORRECT answer
url_ans = f"http://127.0.0.1:8000/api/quiz/{session_id}/answer"
payload_corr = {
    "question_id": q1["id"],
    "selected_option": corr_idx,
    "time_taken_seconds": 3.0
}
req_corr = urllib.request.Request(url_ans, data=json.dumps(payload_corr).encode("utf-8"), headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
})
resp_corr = urllib.request.urlopen(req_corr)
data_corr = json.loads(resp_corr.read().decode("utf-8"))
print("\n--- Submitting CORRECT Answer ---")
print("is_correct:", data_corr["is_correct"])
print("correct_answer_index:", data_corr["correct_answer_index"])
print("message:", data_corr["message"])
print("explanation:", data_corr["explanation_sindhi"])

assert data_corr["is_correct"] is True, "FAIL: is_correct should be True!"
assert data_corr["correct_answer_index"] == corr_idx, "FAIL: correct_answer_index mismatch!"

# 2. Test submitting WRONG answer on Q2
q2 = snapshots[1]
corr_idx_2 = q2["correct_answer_index"]
wrong_idx_2 = (corr_idx_2 + 1) % len(q2["options"])

payload_wrong = {
    "question_id": q2["id"],
    "selected_option": wrong_idx_2,
    "time_taken_seconds": 4.0
}
req_wrong = urllib.request.Request(url_ans, data=json.dumps(payload_wrong).encode("utf-8"), headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
})
resp_wrong = urllib.request.urlopen(req_wrong)
data_wrong = json.loads(resp_wrong.read().decode("utf-8"))
print("\n--- Submitting WRONG Answer ---")
print("is_correct:", data_wrong["is_correct"])
print("correct_answer_index:", data_wrong["correct_answer_index"])
print("message:", data_wrong["message"])

assert data_wrong["is_correct"] is False, "FAIL: is_correct should be False!"
assert data_wrong["correct_answer_index"] == corr_idx_2, "FAIL: correct_answer_index mismatch!"

print("\n>>> ALL FEEDBACK ASSERTIONS PASSED! <<<")
