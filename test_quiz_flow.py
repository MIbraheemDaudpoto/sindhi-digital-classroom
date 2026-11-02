import json
import sys
import urllib.request
sys.stdout.reconfigure(encoding='utf-8')
from src.database.session import get_db
from src.services.auth_service import auth_service

token = auth_service.create_session_token('usr-stu-101', 'STUDENT')
print('Generated student token:', token)

req_data = {
    'course_id': 'crs-sci-6',
    'class_level': 6,
    'subject': 'Science',
    'lesson_ids': ['lesson-sci-6-1'],
    'question_count': 3,
    'difficulty': 'MEDIUM',
    'mode': 'PRACTICE'
}

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/quiz/generate',
    data=json.dumps(req_data).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
    method='POST'
)

with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    session_id = res['session_id']
    print('Generated Session ID:', session_id)
    print('Client Questions count:', len(res['questions']))
    q0 = res['questions'][0]
    print('Client Q0 id:', q0['id'])
    print('Client Q0 text:', q0['text_sindhi'])
    print('Client Q0 options:', q0['options'])

with get_db() as conn:
    row = conn.execute('SELECT questions_snapshot_json, mode FROM quiz_sessions WHERE id = ?', (session_id,)).fetchone()
    snaps = json.loads(row['questions_snapshot_json'])
    correct_idx = snaps[0]['correct_answer_index']
    print('DB Session Mode:', row['mode'])
    print('DB Q0 correct_idx:', correct_idx)
    print('DB Q0 correct option text:', snaps[0]['options'][correct_idx])

# Submit answer
ans_payload = {
    'question_id': q0['id'],
    'selected_option': correct_idx,
    'time_taken_seconds': 5.0
}
ans_req = urllib.request.Request(
    f'http://127.0.0.1:8000/api/quiz/{session_id}/answer',
    data=json.dumps(ans_payload).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
    method='POST'
)

with urllib.request.urlopen(ans_req) as ans_resp:
    ans_res = json.loads(ans_resp.read().decode('utf-8'))
    print('API Answer Feedback Response:')
    for k, v in ans_res.items():
        print(f'  {k}: {v}')
