import sys
import os
sys.path.insert(0, os.getcwd())
from collections import Counter
from src.services.assessment_quiz_service import assessment_quiz_service
from src.models.schemas import QuizGenerateRequest

tests = [
    ("Math", ["lesson-math-6-1"], 10),
    ("Math", [], 10),
    ("Math", ["lesson-math-6-1", "lesson-math-6-2"], 10),
    ("Science", ["lesson-sci-6-1"], 10),
    ("Science", [], 10),
]

for subj, lids, count in tests:
    print(f"\n--- Testing {subj} (lids={lids}, count={count}) ---")
    for attempt in range(5):
        req = QuizGenerateRequest(class_level=6, subject=subj, lesson_ids=lids, question_count=count, mode="assessment")
        res = assessment_quiz_service.generate_quiz("usr-stu-101", req)
        texts = [q.text_sindhi.strip() for q in res.questions]
        unique_texts = set(texts)
        if len(texts) != len(unique_texts):
            print(f"Attempt {attempt + 1}: DUPLICATE DETECTED! Total: {len(texts)}, Unique: {len(unique_texts)}")
            counts = Counter(texts)
            for t, c in counts.items():
                if c > 1:
                    print(f"  Repeated {c}x: {t}")
        else:
            print(f"Attempt {attempt + 1}: All {len(texts)} questions are strictly UNIQUE.")
