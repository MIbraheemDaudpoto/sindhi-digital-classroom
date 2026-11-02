import sqlite3, json, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
c = conn.cursor()
c.execute("SELECT id, questions_snapshot_json, answers_json FROM quiz_sessions WHERE questions_snapshot_json LIKE '%گهرڙي ۽ گهڻ گهرڙن%'")
rows = c.fetchall()
print(f'Matching sessions: {len(rows)}')
for r in rows:
    print('Session ID:', r[0])
    qs = json.loads(r[1])
    ans = json.loads(r[2] or '{}')
    for q in qs:
        if 'گهرڙي ۽ گهڻ گهرڙن' in q['text_sindhi']:
            print('  Q:', q['text_sindhi'])
            print('  Snapshot correct_idx:', q['correct_answer_index'])
            for i, opt in enumerate(q['options']):
                print(f'    [{i}] {opt[:60]}...')
            print('  User Answer:', ans.get(q['id']))

