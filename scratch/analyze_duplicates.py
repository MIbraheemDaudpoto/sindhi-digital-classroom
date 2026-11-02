import sqlite3
import json

conn = sqlite3.connect('data/backups/sdc_platform_backup_20261030_171849.db')
cur = conn.cursor()

with open('scratch/analyze_output.txt', 'w', encoding='utf-8') as out:
    cur.execute('SELECT count(DISTINCT text_sindhi), count(DISTINCT id), count(*) FROM questions WHERE lesson_id = "lesson-sci-6-1"')
    out.write(f"Distinct text, distinct ID, total: {cur.fetchone()}\n")

    cur.execute('''
        SELECT MIN(id), text_sindhi, timestamp_seconds, COUNT(*)
        FROM questions
        WHERE lesson_id = "lesson-sci-6-1"
        GROUP BY text_sindhi, timestamp_seconds
        ORDER BY COUNT(*) DESC
    ''')
    groups = cur.fetchall()
    out.write(f"Total distinct (text_sindhi, timestamp_seconds) groups: {len(groups)}\n")
    for g in groups:
        min_id, text, ts, count = g
        out.write(f"ID={min_id} | ts={ts} | count={count} | text={text[:60]}\n")

    cur.execute('SELECT id, text_sindhi FROM questions WHERE id = "q-sci-01"')
    q_sci_01 = cur.fetchone()
    out.write(f"q-sci-01 info: {q_sci_01}\n")

    cur.execute('SELECT id, status, approved_by, approved_at FROM questions WHERE id = "q-sci-01"')
    out.write(f"q-sci-01 status: {cur.fetchone()}\n")

print("Analysis written to scratch/analyze_output.txt")
