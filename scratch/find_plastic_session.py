import sqlite3, json, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
c = conn.cursor()
c.execute("SELECT id, questions_snapshot_json, answers_json FROM quiz_sessions WHERE id = 'qz-sess-501cd8ad1932'")
r = c.fetchone()
if r:
    print('FOUND SESSION:', r[0])
    qs = json.loads(r[1])
    ans = json.loads(r[2] or '{}')
    for q in qs:
        opts_str = json.dumps(q['options'], ensure_ascii=False)
        if 'پلاسٽڪ' in opts_str:
            print('  Q ID:', q['id'])
            print('  Text:', q['text_sindhi'])
            print('  Options:', q['options'])
            print('  Snapshot correct_idx:', q['correct_answer_index'])
            print('  Answer recorded in DB:', ans.get(q['id']))
