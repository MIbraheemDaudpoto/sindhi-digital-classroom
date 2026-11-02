import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
c = conn.cursor()

c.execute('''
    SELECT c.subject, l.id, l.title_sindhi, q.id, q.timestamp_seconds, q.topic, q.text_sindhi, q.options_json, q.correct_answer_index
    FROM lessons l
    JOIN courses c ON l.course_id = c.id
    JOIN questions q ON l.id = q.lesson_id AND UPPER(q.status) = 'APPROVED'
    ORDER BY c.subject, l.unit_number, q.timestamp_seconds
''')

all_q = c.fetchall()
print(f"Total Approved Checkpoints across all lessons: {len(all_q)}")
cur_lesson = None
for r in all_q:
    if r[1] != cur_lesson:
        cur_lesson = r[1]
        print(f"\n=== [{r[0]}] {r[1]} - {r[2]} ===")
    opts = json.loads(r[7])
    print(f"  @{r[4]:.1f}s | Topic: {r[5]} | Q: {r[6]}")
    for idx, opt in enumerate(opts):
        mark = "(*)" if idx == r[8] else "   "
        print(f"     {mark} [{idx}] {opt}")

