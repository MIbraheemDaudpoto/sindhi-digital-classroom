import sys, os
sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from collections import Counter
from src.services.assessment_quiz_service import assessment_quiz_service
from src.models.schemas import QuizGenerateRequest

duplicates_found = []

with sqlite3.connect('data/sdc_platform.db') as conn:
    conn.row_factory = sqlite3.Row
    courses = [dict(r) for r in conn.execute("SELECT * FROM courses").fetchall()]

print(f"Testing {len(courses)} courses...")

for course in courses:
    subj = course["subject"]
    cls = course["class_level"]
    cid = course["id"]
    with sqlite3.connect('data/sdc_platform.db') as conn:
        conn.row_factory = sqlite3.Row
        lessons = [dict(r) for r in conn.execute("SELECT * FROM lessons WHERE course_id=?", (cid,)).fetchall()]
    
    lesson_id_options = [
        [],  # all lessons
    ]
    if lessons:
        lesson_id_options.append([lessons[0]["id"]])
    if len(lessons) >= 2:
        lesson_id_options.append([lessons[0]["id"], lessons[1]["id"]])
    if len(lessons) >= 5:
        lesson_id_options.append([l["id"] for l in lessons[:5]])
        
    for lids in lesson_id_options:
        for diff in ["ALL", "EASY", "MEDIUM", "HARD"]:
            for rep in range(3):
                try:
                    req = QuizGenerateRequest(
                        course_id=cid,
                        class_level=cls,
                        subject=subj,
                        lesson_ids=lids,
                        question_count=10,
                        difficulty=diff,
                        mode="assessment"
                    )
                    res = assessment_quiz_service.generate_quiz("usr-stu-101", req)
                    texts = [q.text_sindhi.strip() for q in res.questions]
                    counts = Counter(texts)
                    for t, c in counts.items():
                        if c > 1:
                            duplicates_found.append((subj, cls, lids, diff, c, t))
                            print(f"DUPLICATE DETECTED! Subj: {subj}, Cls: {cls}, Diff: {diff}, Lids: {len(lids)}")
                            print(f"  [{c}x] {t}")
                except Exception as e:
                    pass

print(f"\n--- TOTAL DUPLICATES DETECTED: {len(duplicates_found)} ---")

