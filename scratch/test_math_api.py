import json
import urllib.request
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 1. Login
login_req = urllib.request.Request(
    "http://127.0.0.1:8000/api/auth/login/student",
    data=json.dumps({"identifier": "STU-101", "pin": "1234"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
login_resp = json.loads(urllib.request.urlopen(login_req).read().decode("utf-8"))
token = login_resp["token"]

# 2. Generate Mathematics Quiz
url_gen = "http://127.0.0.1:8000/api/quiz/generate"
payload_math = {
    "class_level": 6,
    "subject": "Mathematics",
    "lesson_ids": ["lesson-math-6-1"],
    "question_count": 3,
    "mode": "PRACTICE"
}
req = urllib.request.Request(url_gen, data=json.dumps(payload_math).encode("utf-8"), headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode("utf-8"))
print("Mathematics Quiz Generated Successfully!")
print(f"Session ID: {data['session_id']}")
print(f"Questions Count: {len(data['questions'])}")
for idx, q in enumerate(data['questions']):
    print(f"  Q{idx+1}: {q['text_sindhi']} (Options: {len(q['options'])})")

# 3. Answer Q1 correctly
import sqlite3
conn = sqlite3.connect("data/sdc_platform.db")
conn.row_factory = sqlite3.Row
sess = conn.execute("SELECT * FROM quiz_sessions WHERE id = ?", (data['session_id'],)).fetchone()
snapshots = json.loads(sess["questions_snapshot_json"])
q1 = snapshots[0]
corr_idx = q1["correct_answer_index"]

url_ans = f"http://127.0.0.1:8000/api/quiz/{data['session_id']}/answer"
ans_req = urllib.request.Request(url_ans, data=json.dumps({
    "question_id": q1["id"],
    "selected_option": corr_idx,
    "time_taken_seconds": 2.5
}).encode("utf-8"), headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
})
ans_resp = json.loads(urllib.request.urlopen(ans_req).read().decode("utf-8"))
print(f"\nSubmitting correct answer to Math Q1:")
print(f"is_correct: {ans_resp['is_correct']}")
print(f"message: {ans_resp['message']}")
assert ans_resp["is_correct"] is True, "FAIL: is_correct should be True!"

print("\n>>> MATHEMATICS END-TO-END API TEST PASSED! <<<")
