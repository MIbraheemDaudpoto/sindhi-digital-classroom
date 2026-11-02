import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
c = conn.cursor()

c.execute('''
    SELECT c.subject, l.id, l.title_sindhi, COUNT(q.id) as q_cnt
    FROM lessons l
    JOIN courses c ON l.course_id = c.id
    LEFT JOIN questions q ON l.id = q.lesson_id AND q.status = 'approved'
    GROUP BY l.id
    ORDER BY c.subject, l.unit_number
''')
rows = c.fetchall()
print(f"Total Lessons: {len(rows)}")
for r in rows:
    print(f"Subject: {r[0]:<8} | Lesson: {r[1]:<20} | Questions: {r[3]} | Title: {r[2]}")

print("\n--- SAMPLE QUESTIONS BY SUBJECT ---")
for subj in ['Math', 'Science', 'English', 'Sindhi']:
    c.execute('''
        SELECT q.id, q.lesson_id, q.timestamp_seconds, q.text_sindhi, q.options_json, q.correct_answer_index, q.topic
        FROM questions q
        JOIN lessons l ON q.lesson_id = l.id
        JOIN courses c ON l.course_id = c.id
        WHERE c.subject = ?
        LIMIT 3
    ''', (subj,))
    q_rows = c.fetchall()
    print(f"\n--- {subj} Samples ({len(q_rows)}) ---")
    for qr in q_rows:
        opts = json.loads(qr[4]) if qr[4] else []
        print(f"  [{qr[1]} @ {qr[2]}s] {qr[3]}")
        for i, opt in enumerate(opts):
            marker = "(*)" if i == qr[5] else "( )"
            print(f"     {marker} {opt}")
