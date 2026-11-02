import sqlite3, sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row

tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("All tables:", tables)

lessons = conn.execute("SELECT id, course_id, unit_number, title_sindhi, title_english, duration_seconds, status FROM lessons ORDER BY course_id, unit_number").fetchall()
print(f"\nTotal lessons: {len(lessons)}")
for l in lessons:
    q_rows = conn.execute("SELECT id, timestamp_seconds, status, text_sindhi FROM questions WHERE lesson_id = ? ORDER BY timestamp_seconds", (l["id"],)).fetchall()
    print(f"Lesson: {l['id']} ({l['course_id']} U{l['unit_number']}) - {l['title_english']} [Status: {l['status']}] - Checkpoints: {len(q_rows)}")
    for q in q_rows:
        print(f"    Checkpoint {q['id']} at {q['timestamp_seconds']}s [{q['status']}]: {q['text_sindhi'][:50]}")
