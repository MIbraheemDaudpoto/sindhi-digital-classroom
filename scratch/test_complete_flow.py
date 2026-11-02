import sys
import requests

sys.stdout.reconfigure(encoding='utf-8')
from src.services.auth_service import auth_service

token = auth_service.create_session_token('usr-stu-101', 'STUDENT')
headers = {'Authorization': f'Bearer {token}'}

print("=== STEP 1: GENERATE MATH QUIZ (CLASS 6) ===")
math_gen_res = requests.post('http://127.0.0.1:8000/api/quiz/generate', json={
    'course_id': 'crs-math-6',
    'class_level': 6,
    'subject': 'Math',
    'lesson_ids': ['lesson-math-6-1'],
    'question_count': 3,
    'difficulty': 'MEDIUM',
    'mode': 'PRACTICE'
}, headers=headers)
assert math_gen_res.status_code == 200, f'Math quiz gen failed: {math_gen_res.text}'
math_sess = math_gen_res.json()
sess_id = math_sess['session_id']
print(f"Math Quiz Session: {sess_id}, Provider: {math_sess['provider_type']}, is_live_ai: {math_sess['is_live_ai']}")
print(f"Questions Count: {len(math_sess['questions'])}")
for idx, q in enumerate(math_sess['questions']):
    txt = q['text_sindhi']
    lsn = q['lesson_title_sd']
    print(f"  Q{idx+1}: {txt} (Lesson: {lsn})")

print("\n=== STEP 2: ANSWER IN PRACTICE MODE (REAL-TIME FEEDBACK) ===")
q1 = math_sess['questions'][0]
ans_res = requests.post(f'http://127.0.0.1:8000/api/quiz/{sess_id}/answer', json={
    'question_id': q1['id'],
    'selected_option': 0,
    'time_taken_seconds': 4.0
}, headers=headers)
assert ans_res.status_code == 200, f'Answer submission failed: {ans_res.text}'
ans_fb = ans_res.json()
print(f"Option 0 Feedback: is_correct={ans_fb['is_correct']}, message={ans_fb['message']}")
print(f"Explanation: {ans_fb.get('explanation_sindhi')}")
print(f"Citation: {ans_fb.get('citation')}")

print("\n=== STEP 3: SUBMIT REMAINING ANSWERS & FINALIZE QUIZ ===")
for q in math_sess['questions'][1:]:
    requests.post(f'http://127.0.0.1:8000/api/quiz/{sess_id}/answer', json={
        'question_id': q['id'],
        'selected_option': 1,
        'time_taken_seconds': 3.0
    }, headers=headers)

sub_res = requests.post(f'http://127.0.0.1:8000/api/quiz/{sess_id}/submit', headers=headers)
assert sub_res.status_code == 200, f'Submit failed: {sub_res.text}'
sub_data = sub_res.json()
print(f"Math Quiz Result: Score={sub_data['score']}%, Correct={sub_data['correct_count']}/{sub_data['total_questions']}, Passed={sub_data['passed']}")

print("\n=== STEP 4: PASS A SCIENCE QUIZ WITH >= 50% AND CHECK LESSON PROGRESS ===")
sci_gen_res = requests.post('http://127.0.0.1:8000/api/quiz/generate', json={
    'course_id': 'crs-sci-6',
    'class_level': 6,
    'subject': 'Science',
    'lesson_ids': ['lesson-sci-6-2'],
    'question_count': 3,
    'difficulty': 'MEDIUM',
    'mode': 'ASSESSMENT'
}, headers=headers)
assert sci_gen_res.status_code == 200, f'Sci quiz gen failed: {sci_gen_res.text}'
sci_sess = sci_gen_res.json()
sci_sess_id = sci_sess['session_id']

# To ensure passing, query the correct answers from DB session snapshot
from src.database.session import get_db
import json
with get_db() as conn:
    row = conn.execute("SELECT questions_snapshot_json FROM quiz_sessions WHERE id = ?", (sci_sess_id,)).fetchone()
    q_snap = json.loads(row["questions_snapshot_json"])

for q in q_snap:
    c_idx = q["correct_answer_index"]
    requests.post(f'http://127.0.0.1:8000/api/quiz/{sci_sess_id}/answer', json={
        'question_id': q['id'],
        'selected_option': c_idx,
        'time_taken_seconds': 2.0
    }, headers=headers)

sci_sub_res = requests.post(f'http://127.0.0.1:8000/api/quiz/{sci_sess_id}/submit', headers=headers)
assert sci_sub_res.status_code == 200
sci_sub = sci_sub_res.json()
print(f"Science Quiz Result: Score={sci_sub['score']}%, Passed={sci_sub['passed']}, Lesson Breakdown={sci_sub['per_lesson_breakdown']}")

print("\n=== STEP 5: VERIFY STUDENT DASHBOARD ===")
dash_res = requests.get('http://127.0.0.1:8000/api/dashboards/student?course_id=crs-sci-6', headers=headers)
assert dash_res.status_code == 200, f'Dashboard failed: {dash_res.text}'
dash = dash_res.json()
print(f"Student: {dash['student_code']} at {dash['school_name']}")
print(f"Course Completed Count: {dash['course_completed_count']} / {dash['course_total_count']} (Total All Courses: {dash['completed_lessons_count']})")
print(f"Total Quiz Attempts: {dash['total_quiz_attempts']}")
print(f"Total Quiz Accuracy: {dash['total_quiz_score_pct']}%")
print(f"Streak: {dash['active_streak_days']} days ({dash['streak_badge_sindhi']})")
print("\nTop 5 Recent Attempts in Table:")
for i, a in enumerate(dash['recent_attempts'][:5]):
    opt_str = f"Option {a.get('selected_option') + 1}" if a.get('selected_option') is not None else "Option -"
    print(f"  {i+1}. Topic: {a['topic']} | Answer: {opt_str} | Result: {'Correct' if a['is_correct'] else 'Wrong'} | Date: {a['created_at'][:10]}")

print("\nWeekly Activity Breakdown:")
for d in dash['weekly_activity']:
    if d['count'] > 0:
        print(f"  - {d['day']}: {d['count']} activities")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
