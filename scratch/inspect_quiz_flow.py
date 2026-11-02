import sqlite3
import json

conn = sqlite3.connect('data/sdc_platform.db')
cur = conn.cursor()
cur.execute('SELECT id, lesson_id, text_sindhi, options_json, correct_answer_index, topic FROM questions WHERE lesson_id = "lesson-sci-6-1" LIMIT 5')
rows = cur.fetchall()
with open('scratch/q_sample.json', 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print(f"Dumped {len(rows)} sample questions to scratch/q_sample.json")
