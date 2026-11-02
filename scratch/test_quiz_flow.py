import urllib.request, json, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Login as student
login_data = json.dumps({'school_code': 'SCH-HYD-01', 'student_code': 'STU-101', 'pin': '1234'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8000/api/auth/login/student', data=login_data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read().decode())['token']

# Generate quiz
gen_data = json.dumps({
    'class_level': 6,
    'subject': 'Science',
    'lesson_ids': ['lesson-sci-6-1'],
    'question_count': 3,
    'mode': 'practice'
}).encode('utf-8')
gen_req = urllib.request.Request('http://127.0.0.1:8000/api/quiz/generate', data=gen_data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(gen_req) as resp:
    session = json.loads(resp.read().decode())
    sess_id = session['session_id']
    print('Generated session:', sess_id, 'mode:', session['mode'], 'q count:', len(session['questions']))
    q0 = session['questions'][0]
    print('First question:', q0['id'], q0['text_sindhi'])
    for i, opt in enumerate(q0['options']):
        print(f'  [{i}] {opt}')

# Now answer option 0
ans_data = json.dumps({
    'question_id': q0['id'],
    'selected_option': 0,
    'time_taken_seconds': 5.0
}).encode('utf-8')
ans_req = urllib.request.Request(f'http://127.0.0.1:8000/api/quiz/{sess_id}/answer', data=ans_data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(ans_req) as resp:
    ans_res = json.loads(resp.read().decode())
    print('Answer feedback:', json.dumps(ans_res, ensure_ascii=False))

