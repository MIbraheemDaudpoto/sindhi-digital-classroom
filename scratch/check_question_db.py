import sqlite3, json, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
c = conn.cursor()
c.execute("SELECT id, text_sindhi, options_json, correct_answer_index FROM questions WHERE text_sindhi LIKE '%گهرڙي%' OR explanation_sindhi LIKE '%گهرڙي%'")
rows = c.fetchall()
print(f'Found {len(rows)} questions in DB matching گهرڙي:')
for r in rows:
    print('ID:', r[0], 'correct_answer_index:', r[3])
    print('Question:', r[1])
    opts = json.loads(r[2])
    for i, o in enumerate(opts):
        print(f'  [{i}] {o}')
    print('-' * 40)

