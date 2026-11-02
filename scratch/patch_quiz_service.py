import re

filepath = "src/services/assessment_quiz_service.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update generate_quiz deduplication & backfill guard
old_part_1 = """            if not raw_questions:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="هن چونڊ لاءِ سوال تيار نه ٿي سگهيا. مهرباني ڪري ٻيو سبق يا مضمون چونڊيو."
                )

            # 5. Build Immutable Snapshot & Client View"""

new_part_1 = """            if not raw_questions:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="هن چونڊ لاءِ سوال تيار نه ٿي سگهيا. مهرباني ڪري ٻيو سبق يا مضمون چونڊيو."
                )

            # 5. Strict Global Deduplication & Final Backfill Guard
            # Guarantees that in 10-MCQ quizzes, zero duplicate questions ever appear
            final_unique_questions: List[Dict[str, Any]] = []
            seen_final_texts: Set[str] = set()
            for q in raw_questions:
                norm_q = re.sub(r"\\s+", " ", q.get("text_sindhi", "")).strip()
                if norm_q and norm_q not in seen_final_texts:
                    seen_final_texts.add(norm_q)
                    final_unique_questions.append(q)

            if len(final_unique_questions) < req.question_count:
                more_needed = req.question_count - len(final_unique_questions)
                extra_fill = self._generate_from_curriculum_bank(
                    conn=conn,
                    course=course,
                    lessons=lessons_meta,
                    count=more_needed * 2,
                    difficulty=req.difficulty,
                    weak_lesson_ids=weak_lesson_ids
                )
                for eq in extra_fill:
                    norm_eq = re.sub(r"\\s+", " ", eq.get("text_sindhi", "")).strip()
                    if norm_eq and norm_eq not in seen_final_texts:
                        seen_final_texts.add(norm_eq)
                        final_unique_questions.append(eq)
                    if len(final_unique_questions) >= req.question_count:
                        break

            raw_questions = final_unique_questions[:req.question_count]

            # 6. Build Immutable Snapshot & Client View"""

assert old_part_1 in content, "old_part_1 not found"
content = content.replace(old_part_1, new_part_1, 1)

# 2. Update _generate_from_curriculum_bank unselected pool & fallback & backfill
old_part_2 = """        # If we need more questions to reach count, pull from remaining unselected pool without duplicating
        if len(selected_questions) < count and all_unselected_pool:
            random.shuffle(all_unselected_pool)
            for extra_q in all_unselected_pool:
                if len(selected_questions) >= count:
                    break
                selected_questions.append(extra_q)

        # If still short, pull from other units of the same course
        if len(selected_questions) < count:
            remaining_needed = count - len(selected_questions)
            fallback_rows = conn.execute(
                \"\"\"
                SELECT * FROM questions
                WHERE lesson_id LIKE ? AND status = 'APPROVED'
                  AND text_sindhi NOT LIKE '%اسلام جو ڪهڙو ڪردار%'
                  AND options_json NOT LIKE '%غير ضروري معلومات%'
                ORDER BY RANDOM() LIMIT ?
                \"\"\",
                (f"%{subj_filter}%", remaining_needed * 2)
            ).fetchall()
            for fr in fallback_rows:
                if len(selected_questions) >= count:
                    break
                norm_k = re.sub(r"\\s+", " ", fr["text_sindhi"]).strip()
                if norm_k in seen_texts:
                    continue
                seen_texts.add(norm_k)
                opts = json.loads(fr["options_json"])
                selected_questions.append({
                    "text_sindhi": fr["text_sindhi"],
                    "options": opts,
                    "correct_answer_index": fr["correct_answer_index"],
                    "explanation_sindhi": f"درسي ڪتاب جي موضوع '{fr['topic']}' مان ورتل.",
                    "citation": f"STBB {subject_name} VI",
                    "difficulty": fr["difficulty"],
                    "topic": fr["topic"],
                    "lesson_id": fr["lesson_id"]
                })

        # Truncate to exact requested count and shuffle question order
        random.shuffle(selected_questions)
        return selected_questions[:count]"""

new_part_2 = """        # If we need more questions to reach count, pull from remaining unselected pool without duplicating
        if len(selected_questions) < count and all_unselected_pool:
            random.shuffle(all_unselected_pool)
            for extra_q in all_unselected_pool:
                if len(selected_questions) >= count:
                    break
                norm_k = re.sub(r"\\s+", " ", extra_q.get("text_sindhi", "")).strip()
                if not norm_k or norm_k in seen_texts:
                    continue
                seen_texts.add(norm_k)
                selected_questions.append(extra_q)

        # If still short, pull from other units of the same course
        if len(selected_questions) < count:
            remaining_needed = count - len(selected_questions)
            fallback_rows = conn.execute(
                \"\"\"
                SELECT * FROM questions
                WHERE lesson_id LIKE ? AND status = 'APPROVED'
                  AND text_sindhi NOT LIKE '%اسلام جو ڪهڙو ڪردار%'
                  AND options_json NOT LIKE '%غير ضروري معلومات%'
                ORDER BY RANDOM() LIMIT ?
                \"\"\",
                (f"%{subj_filter}%", remaining_needed * 3)
            ).fetchall()
            for fr in fallback_rows:
                if len(selected_questions) >= count:
                    break
                norm_k = re.sub(r"\\s+", " ", fr["text_sindhi"]).strip()
                if norm_k in seen_texts:
                    continue
                seen_texts.add(norm_k)
                opts = json.loads(fr["options_json"])
                selected_questions.append({
                    "text_sindhi": fr["text_sindhi"],
                    "options": opts,
                    "correct_answer_index": fr["correct_answer_index"],
                    "explanation_sindhi": f"درسي ڪتاب جي موضوع '{fr['topic']}' مان ورتل.",
                    "citation": f"STBB {subject_name} VI",
                    "difficulty": fr["difficulty"],
                    "topic": fr["topic"],
                    "lesson_id": fr["lesson_id"]
                })

        # If still short, dynamically synthesize distinct conceptual questions from all subject glossary terms
        if len(selected_questions) < count and all_subj_gloss:
            for gr in all_subj_gloss:
                if len(selected_questions) >= count:
                    break
                t_sd = gr["term_sd"]
                defn = gr.get("definition_sd", "")
                q_text = f"سنڌ ٽيڪسٽ بڪ مطابق اصطلاح '{t_sd}' مان ڇا مراد آهي؟"
                norm_k = re.sub(r"\\s+", " ", q_text).strip()
                if not defn or len(defn) < 10 or norm_k in seen_texts:
                    continue
                other_defs = [
                    g["definition_sd"] for g in all_subj_gloss 
                    if g["id"] != gr["id"] and g.get("definition_sd") and len(g.get("definition_sd", "")) > 10
                ]
                if len(other_defs) < 3:
                    continue
                distractors = random.sample(other_defs, 3)
                seen_texts.add(norm_k)
                selected_questions.append({
                    "text_sindhi": q_text,
                    "options": [defn] + distractors,
                    "correct_answer_index": 0,
                    "explanation_sindhi": f"{t_sd}: {defn}",
                    "citation": gr.get("citation_formatted") or f"STBB {subject_name} VI",
                    "difficulty": "MEDIUM",
                    "topic": t_sd,
                    "lesson_id": lessons[0]["id"]
                })

        # Truncate to exact requested count and shuffle question order
        random.shuffle(selected_questions)
        return selected_questions[:count]"""

assert old_part_2 in content, "old_part_2 not found"
content = content.replace(old_part_2, new_part_2, 1)

# 3. Update _generate_with_live_ai target_lessons NameError & deduplication
old_part_3 = """        for lesson in target_lessons:
            unit_num = lesson["unit_number"]
            c_rows = conn.execute(
                "SELECT * FROM sdc_chunks WHERE subject_id = ? AND chapter_id = ? LIMIT 2",
                (subj_filter, unit_num)
            ).fetchall()
            all_chunks.extend([dict(r) for r in c_rows])

        if not all_chunks:
            return []

        context_text = "\\n".join([f"[{c['topic_title_sd']} ({c['citation_formatted']})]: {c['summary_sd']}" for c in all_chunks])
        
        drafts = ai_provider.generate_draft_quiz_questions(
            lesson_title=lessons[0]["title_sindhi"],
            context_text=context_text,
            count=count
        )

        valid_items: List[Dict[str, Any]] = []
        for d in drafts:
            opts = d.get("options_json") or d.get("options", [])
            corr = d.get("correct_answer_index", 0)
            txt = d.get("text_sindhi", "")
            if len(opts) == 4 and 0 <= corr < 4 and len(txt) > 5:
                valid_items.append({
                    "text_sindhi": txt,
                    "options": opts,
                    "correct_answer_index": corr,
                    "explanation_sindhi": d.get("explanation_sindhi", "نصاب مطابق."),
                    "citation": all_chunks[0].get("citation_formatted", f"STBB {course['subject']} VI"),
                    "difficulty": difficulty,
                    "topic": d.get("topic", lessons[0]["title_sindhi"]),
                    "lesson_id": lessons[0]["id"]
                })

        return valid_items"""

new_part_3 = """        for lesson in lessons:
            unit_num = lesson["unit_number"]
            c_rows = conn.execute(
                "SELECT * FROM sdc_chunks WHERE subject_id = ? AND chapter_id = ? LIMIT 2",
                (subj_filter, unit_num)
            ).fetchall()
            all_chunks.extend([dict(r) for r in c_rows])

        if not all_chunks:
            return []

        context_text = "\\n".join([f"[{c['topic_title_sd']} ({c['citation_formatted']})]: {c['summary_sd']}" for c in all_chunks])
        
        drafts = ai_provider.generate_draft_quiz_questions(
            lesson_title=lessons[0]["title_sindhi"],
            context_text=context_text,
            count=count
        )

        valid_items: List[Dict[str, Any]] = []
        seen_ai_texts: Set[str] = set()
        for d in drafts:
            opts = d.get("options_json") or d.get("options", [])
            corr = d.get("correct_answer_index", 0)
            txt = d.get("text_sindhi") or d.get("question_text_sindhi") or ""
            norm_key = re.sub(r"\\s+", " ", txt).strip()
            if not norm_key or norm_key in seen_ai_texts:
                continue
            if len(opts) == 4 and 0 <= corr < 4 and len(txt) > 5:
                seen_ai_texts.add(norm_key)
                valid_items.append({
                    "text_sindhi": txt,
                    "options": opts,
                    "correct_answer_index": corr,
                    "explanation_sindhi": d.get("explanation_sindhi", "نصاب مطابق."),
                    "citation": all_chunks[0].get("citation_formatted", f"STBB {course['subject']} VI"),
                    "difficulty": difficulty,
                    "topic": d.get("topic", lessons[0]["title_sindhi"]),
                    "lesson_id": lessons[0]["id"]
                })

        # If live AI returned fewer unique valid items than requested count, fill remainder from curriculum bank
        if len(valid_items) < count:
            remaining_needed = count - len(valid_items)
            curriculum_fill = self._generate_from_curriculum_bank(
                conn=conn,
                course=course,
                lessons=lessons,
                count=remaining_needed,
                difficulty=difficulty
            )
            for cq in curriculum_fill:
                norm_key = re.sub(r"\\s+", " ", cq.get("text_sindhi", "")).strip()
                if norm_key not in seen_ai_texts:
                    seen_ai_texts.add(norm_key)
                    valid_items.append(cq)
                if len(valid_items) >= count:
                    break

        return valid_items[:count]"""

assert old_part_3 in content, "old_part_3 not found"
content = content.replace(old_part_3, new_part_3, 1)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS: assessment_quiz_service.py successfully patched.")

