import sqlite3, json, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
c = conn.cursor()
c.execute("SELECT id, text_sindhi, options_json, correct_answer_index FROM questions WHERE options_json LIKE '%پلاسٽڪ%'")
rows = c.fetchall()
print(f'Matching questions in DB: {len(rows)}')
for r in rows:
    print('ID:', r[0], 'correct_answer_index:', r[3])
    print('Text:', r[1])
    for i, opt in enumerate(json.loads(r[2])):
        print(f'  [{i}] {opt}')

