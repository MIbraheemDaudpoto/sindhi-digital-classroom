import sys, os
sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from src.services.assessment_quiz_service import assessment_quiz_service
from src.services.ai_provider import get_ai_provider

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row
course = dict(conn.execute("SELECT * FROM courses WHERE subject='Math' AND class_level=6").fetchone())
lessons = [dict(r) for r in conn.execute("SELECT * FROM lessons WHERE course_id=? LIMIT 1", (course["id"],)).fetchall()]

ai_provider = get_ai_provider()
print(f"AI Provider: {ai_provider.provider_type}")

# Let's test calling generate_draft_quiz_questions
all_chunks = []
subj_filter = "math-6"
for lesson in lessons:
    unit_num = lesson["unit_number"]
    c_rows = conn.execute(
        "SELECT * FROM sdc_chunks WHERE subject_id = ? AND chapter_id = ? LIMIT 2",
        (subj_filter, unit_num)
    ).fetchall()
    all_chunks.extend([dict(r) for r in c_rows])

context_text = "\n".join([f"[{c['topic_title_sd']} ({c['citation_formatted']})]: {c['summary_sd']}" for c in all_chunks])
drafts = ai_provider.generate_draft_quiz_questions(
    lesson_title=lessons[0]["title_sindhi"],
    context_text=context_text,
    count=10
)
print(f"Drafts returned: {len(drafts)}")
for i, d in enumerate(drafts):
    print(f" {i+1}. {d.get('text_sindhi') or d.get('question_text_sindhi')}")

