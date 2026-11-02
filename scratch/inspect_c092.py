import sqlite3, json, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
c = conn.cursor()
c.execute("SELECT questions_snapshot_json, answers_json FROM quiz_sessions WHERE id = 'qz-sess-c09215e4a930'")
row = c.fetchone()
if row:
    qs = json.loads(row[0])
    ans = json.loads(row[1])
    for q in qs[:3]:
        print('Q ID:', q['id'])
        print('Text:', q['text_sindhi'])
        print('Options:', q['options'])
        print('Snapshot correct_idx:', q['correct_answer_index'])
        print('Answer recorded in DB:', ans.get(q['id']))

