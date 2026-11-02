import sys, os
sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from collections import Counter
from src.services.assessment_quiz_service import assessment_quiz_service

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row
course = dict(conn.execute("SELECT * FROM courses WHERE subject='Science' AND class_level=6").fetchone())
lessons = [dict(r) for r in conn.execute("SELECT * FROM lessons WHERE course_id=? LIMIT 1", (course["id"],)).fetchall()]

# Test calling _generate_with_live_ai when target_lessons is fixed
try:
    res = assessment_quiz_service._generate_with_live_ai(conn, course, lessons, count=10, difficulty="MEDIUM")
    print(f"Live AI generated {len(res)} questions:")
    for i, q in enumerate(res):
        print(f"  {i+1}. {q['text_sindhi']}")
    texts = [q['text_sindhi'].strip() for q in res]
    counts = Counter(texts)
    for t, c in counts.items():
        if c > 1:
            print(f"DUPLICATE DETECTED IN LIVE AI! [{c}x] {t}")
except Exception as e:
    print(f"Exception: {e}")

