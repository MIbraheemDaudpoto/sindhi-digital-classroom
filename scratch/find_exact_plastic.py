import sqlite3, json, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
c = conn.cursor()
c.execute("SELECT id, questions_snapshot_json, answers_json FROM quiz_sessions")
for r in c.fetchall():
    qs = json.loads(r[1])
    ans = json.loads(r[2] or '{}')
    for q in qs:
        opts = q.get('options', [])
        if len(opts) > 0 and 'پلاسٽڪ' in opts[0]:
            print('MATCH FOUND in session:', r[0])
            print('  Q ID:', q['id'])
            print('  Text:', q['text_sindhi'])
            print('  Options:', opts)
            print('  Snapshot correct_idx:', q['correct_answer_index'])
            print('  Answer in DB:', ans.get(q['id']))

