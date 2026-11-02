import sys, os
sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding='utf-8')
from src.services.assessment_quiz_service import assessment_quiz_service
from src.models.schemas import QuizGenerateRequest
from collections import Counter

req = QuizGenerateRequest(class_level=6, subject="Science", lesson_ids=["lesson-sci-6-1"], question_count=10, mode="assessment")
res = assessment_quiz_service.generate_quiz("usr-stu-101", req)
texts = [q.text_sindhi for q in res.questions]
print(f"Generated {len(texts)} questions for Science (lesson-sci-6-1):")
for i, t in enumerate(texts):
    print(f" {i+1}. {t}")
counts = Counter(texts)
duplicates_found = False
for t, c in counts.items():
    if c > 1:
        print(f"DUPLICATE: [{c}x] {t}")
        duplicates_found = True
if not duplicates_found:
    print("NO DUPLICATES FOUND IN THIS ATTEMPT.")
