import sqlite3, json, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
c = conn.cursor()
c.execute("SELECT questions_snapshot_json, answers_json FROM quiz_sessions WHERE id = 'qz-sess-501cd8ad1932'")
row = c.fetchone()
qs = json.loads(row[0])
ans = json.loads(row[1])
for q in qs:
    if 'پلاسٽڪ' in json.dumps(q['options']):
        print('Q ID:', q['id'])
        print('Text:', q['text_sindhi'])
        print('Options:', q['options'])
        print('Correct index in snapshot:', q['correct_answer_index'])
        print('Answer recorded:', ans.get(q['id']))

