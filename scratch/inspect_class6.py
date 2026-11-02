import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json
from src.services.lesson_service import lesson_service

sys.stdout.reconfigure(encoding="utf-8")
courses = lesson_service.list_courses(6)
for c in courses:
    print(f"Course: {c.id} | Subject: {c.subject} | Title: {c.title_english} | Lessons count: {len(c.lessons)}")
    for l in c.lessons:
        print(f"  Lesson: {l.id} | unit_number: {l.unit_number} (type {type(l.unit_number)}) | sindhi: {l.title_sindhi} | eng: {l.title_english}")
