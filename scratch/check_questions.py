import sqlite3

conn = sqlite3.connect('data/sdc_platform.db')
cursor = conn.cursor()

total = cursor.execute("SELECT count(*) FROM questions WHERE lesson_id='lesson-sci-6-1'").fetchone()[0]
distinct_text = cursor.execute("SELECT count(DISTINCT text_sindhi) FROM questions WHERE lesson_id='lesson-sci-6-1'").fetchone()[0]
print(f"Total rows for lesson-sci-6-1: {total}")
print(f"Distinct question text: {distinct_text}")

rows = cursor.execute("SELECT id, timestamp_seconds, topic, count(*) FROM questions WHERE lesson_id='lesson-sci-6-1' GROUP BY text_sindhi, timestamp_seconds").fetchall()
print(f"Unique question groups: {len(rows)}")
for r in rows:
    print(f"  topic={r[2]}, ts={r[1]}s, count={r[3]}")

