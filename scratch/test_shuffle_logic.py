import sys
sys.path.insert(0, '.')
import sqlite3, json, random, re
from src.services.assessment_quiz_service import assessment_quiz_service
from src.database.session import get_db

with get_db() as conn:
    course = dict(conn.execute("SELECT * FROM courses WHERE id = 'crs-sci-6'").fetchone())
    lessons = [dict(r) for r in conn.execute("SELECT * FROM lessons WHERE course_id = 'crs-sci-6' ORDER BY unit_number").fetchall()]
    
    questions = assessment_quiz_service._generate_from_curriculum_bank(conn, course, lessons, count=30, difficulty="ALL")
    print(f"Generated {len(questions)} questions")
    
    mismatches = 0
    for i, q in enumerate(questions):
        corr_idx = q["correct_answer_index"]
        corr_val = q["options"][corr_idx]
        
        # Now simulate shuffling as done in generate_quiz:
        orig_opts = list(q["options"])
        shuffled = list(orig_opts)
        random.shuffle(shuffled)
        new_corr_idx = shuffled.index(corr_val)
        
        if shuffled[new_corr_idx] != corr_val:
            print(f"MISMATCH in question {i+1}!")
            mismatches += 1
            
    print(f"Total simulated mismatches: {mismatches}")
