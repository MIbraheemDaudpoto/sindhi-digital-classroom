"""Small provider double for assessment orchestration tests (not model evidence)."""

import re
import uuid


class FakeGroundedQuizProvider:
    provider_type = "TEST_LLM_PROVIDER"
    model_name = "test-grounded-model"

    def __init__(self):
        self.last_quiz_inference = False
        self.last_quiz_request_id = None
        self._request_number = 0

    def generate_draft_quiz_questions(self, lesson_title, context_text, count=3):
        self.last_quiz_inference = False
        self.last_quiz_request_id = None
        contexts = re.findall(
            r"\[LESSON_ID=([^ |]+).*?CITATION=(.*?) \| TOPIC=",
            context_text,
        )
        if not contexts:
            return []
        contexts_by_lesson = {}
        for lesson_id, citation in contexts:
            contexts_by_lesson.setdefault(lesson_id, citation)
        lessons = list(contexts_by_lesson.items())

        self._request_number += 1
        self.last_quiz_inference = True
        self.last_quiz_request_id = str(uuid.uuid4())
        return [
            {
                "text_sindhi": f"هي نصابي سوال {self._request_number}-{index} چونڊيل سبق بابت ڇا پڇي ٿو؟",
                "options": [
                    f"جواب الف {index}",
                    f"جواب ب {index}",
                    f"جواب ج {index}",
                    f"جواب د {index}",
                ],
                "correct_answer_index": 0,
                "explanation_sindhi": "چونڊيل درسي مواد مطابق.",
                "topic": lesson_title,
                "lesson_id": lessons[(index - 1) % len(lessons)][0],
                "citation": lessons[(index - 1) % len(lessons)][1],
            }
            for index in range(1, count + 1)
        ]
