import sqlite3

conn = sqlite3.connect('data/sdc_platform.db')
cursor = conn.cursor()

with open('scratch/questions_analysis.txt', 'w', encoding='utf-8') as out:
    rows = cursor.execute("SELECT id, timestamp_seconds, topic, count(*) FROM questions WHERE lesson_id='lesson-sci-6-1' GROUP BY text_sindhi, timestamp_seconds").fetchall()
    for r in rows:
        out.write(f"  topic={r[2]}, ts={r[1]}s, count={r[3]}\n")

print("Written to scratch/questions_analysis.txt")

