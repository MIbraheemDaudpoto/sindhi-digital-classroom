with open("tests/test_assessment_quiz_system.py", "r", encoding="utf-8") as f:
    content = f.read()

target = """def test_honest_provider_status_reporting():
    \"\"\"Verify provider status truthfully indicates LOCAL_CURRICULUM_BANK when live AI is offline.\"\"\"
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "question_count": 2
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_live_ai"] is False
    assert "LOCAL" in data["provider_type"] or "CURRICULUM" in data["provider_type"]
    assert "آف لائن" in data["ai_status_message"] or "تصديق ٿيل" in data["ai_status_message"]"""

replacement = """def test_honest_provider_status_reporting(monkeypatch):
    \"\"\"Verify provider status truthfully indicates LOCAL_CURRICULUM_BANK when live AI is offline.\"\"\"
    monkeypatch.setattr(
        "src.services.assessment_quiz_service.get_ai_system_status",
        lambda: {"is_live_inference": False, "active_provider_type": "LOCAL_DETERMINISTIC_FALLBACK"}
    )
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "question_count": 2
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_live_ai"] is False
    assert "LOCAL" in data["provider_type"] or "CURRICULUM" in data["provider_type"]
    assert "آف لائن" in data["ai_status_message"] or "تصديق ٿيل" in data["ai_status_message"]


def test_unique_questions_guarantee_10_mcqs():
    \"\"\"Verify that 10-MCQ quizzes across Math and Science NEVER contain duplicate questions.\"\"\"
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    for subject in ["Math", "Science"]:
        for lesson_scope in [[], ["lesson-math-6-1" if subject == "Math" else "lesson-sci-6-1"]]:
            resp = client.post("/api/quiz/generate", headers=headers, json={
                "class_level": 6,
                "subject": subject,
                "lesson_ids": lesson_scope,
                "question_count": 10,
                "mode": "ASSESSMENT"
            })
            assert resp.status_code == 201, resp.text
            data = resp.json()
            questions = data["questions"]
            assert len(questions) == 10, f"Expected 10 questions, got {len(questions)}"
            texts = [q["text_sindhi"].strip() for q in questions]
            unique_texts = set(texts)
            assert len(texts) == len(unique_texts), f"Duplicates found in 10-MCQ {subject} quiz: {len(texts) - len(unique_texts)} duplicates" """

assert target in content, "target not found in test_assessment_quiz_system.py"
content = content.replace(target, replacement, 1)

with open("tests/test_assessment_quiz_system.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated test_assessment_quiz_system.py successfully.")

