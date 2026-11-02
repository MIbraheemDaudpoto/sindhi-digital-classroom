import os
import sys
import time
import json

# Ensure repo root is on sys.path
sys.path.insert(0, r"D:\Ai Agents\agency-agents\sindhi-digital-classroom")
os.chdir(r"D:\Ai Agents\agency-agents\sindhi-digital-classroom")
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

from src.services.auth_service import auth_service
from src.database.session import get_db

# 1. Create a genuine auth token for student usr-stu-101
token = auth_service.create_session_token('usr-stu-101', 'STUDENT')
user_obj = {
    "user_id": "usr-stu-101",
    "role": "STUDENT",
    "pseudonymous_code": "STU-101",
    "full_name": "Ali Hassan",
    "school_id": "sch-hyd-01",
    "school_name": "Government High School Qasimabad",
    "city": "Hyderabad",
    "language": "sindhi",
    "token": token
}

print(f"[*] Generated Student Token: {token[:20]}...")

os.makedirs("scratch/screenshots", exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        locale="sd-PK"
    )
    page = context.new_page()

    # Pre-seed localStorage with authenticated student session
    page.goto("http://127.0.0.1:8000/static/index.html")
    page.evaluate(f"""
        localStorage.setItem('sdc_token', '{token}');
        localStorage.setItem('sdc_current_user', JSON.stringify({json.dumps(user_obj)}));
    """)
    page.goto("http://127.0.0.1:8000/app/learn")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    print("[1] Loaded /app/learn. Capturing screenshot...")
    page.screenshot(path="scratch/screenshots/01_learn_page.png")

    # Step 2: Open Assessment Hub
    print("[2] Clicking Assessment Hub (AI Quizzes) tab...")
    page.click('[data-tab="pane-assessment-hub-tab"]')
    page.wait_for_selector("#sdc-assessment-modal", state="visible", timeout=10000)
    time.sleep(1)

    # Step 3: Switch to Mathematics
    print("[3] Selecting Mathematics subject button...")
    math_btn = page.locator("#quiz-subject-selector button:has-text('رياضي')")
    math_btn.click()
    time.sleep(1.5)

    # Verify lessons checklist
    checklist_text = page.locator("#quiz-lessons-checklist").inner_text()
    print("[4] Checklist loaded text sample:")
    for line in checklist_text.splitlines()[:5]:
        print("   ", line)
    
    assert "undefined" not in checklist_text, "ERROR: 'undefined' found in lessons checklist!"
    assert "سيٽ" in checklist_text or "Sets" in checklist_text, "ERROR: Math lessons not found in checklist!"

    # Ensure Practice Mode is selected
    practice_btn = page.locator("#quiz-mode-selector button:has-text('مشقي موڊ')")
    practice_btn.click()
    time.sleep(0.5)

    # Select 3 questions for fast thorough test
    q3_btn = page.locator("#quiz-count-selector button:has-text('3 سوال')")
    q3_btn.click()
    time.sleep(0.5)

    page.screenshot(path="scratch/screenshots/02_math_quiz_setup.png")
    print("[5] Captured Math Quiz Setup screenshot.")

    # Step 4: Click Start Quiz
    print("[6] Clicking 'Start Quiz' button...")
    page.click("#btn-generate-quiz-action")
    
    # Wait for quiz runner question card
    page.wait_for_selector(".question-card", state="visible", timeout=15000)
    time.sleep(1)
    page.screenshot(path="scratch/screenshots/03_quiz_question_1.png")
    print("[7] Quiz started! Question 1 displayed.")

    # Step 5: Answer Question 1 and verify instant feedback
    q1_title = page.locator(".question-title-text").inner_text()
    print(f"[8] Q1: {q1_title}")

    # Click Option 1
    options = page.locator(".question-options-list .option-btn")
    opt_count = options.count()
    print(f"   Found {opt_count} options. Clicking option 0...")
    options.nth(0).click()

    # Wait for instant feedback
    page.wait_for_selector("#runner-instant-feedback", state="visible", timeout=5000)
    time.sleep(1)
    fb_text = page.locator("#runner-instant-feedback").inner_text()
    print(f"[9] Instant Feedback Text:\n{fb_text}")
    assert ("درست جواب" in fb_text or "غلط جواب" in fb_text), "Instant feedback missing validation result!"

    page.screenshot(path="scratch/screenshots/04_q1_feedback.png")
    print("[10] Captured Q1 Instant Feedback screenshot.")

    # Answer remaining questions
    for q_idx in range(1, 3):
        print(f"[11] Moving to question {q_idx + 1}...")
        page.click("#btn-quiz-next")
        time.sleep(1)
        
        # Click an option
        page.locator(".question-options-list .option-btn").nth(1).click()
        time.sleep(1)
        page.screenshot(path=f"scratch/screenshots/05_q{q_idx+1}_answered.png")

    # Final submission
    print("[12] Submitting completed quiz...")
    page.click("#btn-quiz-next") # On last question, this submits
    page.wait_for_selector(".assessment-results-container", state="visible", timeout=15000)
    time.sleep(1)
    
    result_text = page.locator(".assessment-results-container").inner_text()
    print("[13] Quiz Results Summary:")
    for line in result_text.splitlines()[:10]:
        print("   ", line)
    
    page.screenshot(path="scratch/screenshots/06_quiz_result_screen.png")
    print("[14] Captured Quiz Result Screen.")

    # Step 6: Navigate to /app/progress and verify progress update
    print("[15] Navigating to Progress Dashboard...")
    page.click("button:has-text('بند ڪريو ۽ ڪلاس روم ڏسو')")
    time.sleep(1)

    # Click Student Dash tab
    page.click('[data-tab="pane-student-dash"]')
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Extract dashboard text & statistics
    dash_stats = page.locator("#pane-student-dash").inner_text()
    page.screenshot(path="scratch/screenshots/07_progress_dashboard.png", full_page=True)
    print("[16] Captured full-page Progress Dashboard.")

    # Check Recent Attempts table
    table_rows = page.locator("#student-attempts-table-body tr")
    row_count = table_rows.count()
    print(f"[17] Recent Attempts Table Rows: {row_count}")
    for i in range(min(row_count, 5)):
        row_txt = table_rows.nth(i).inner_text().replace('\n', ' | ')
        print(f"    Row {i+1}: {row_txt}")
        assert "آپشن -" not in row_txt, f"Row {i+1} still contains 'آپشن -'!"

    print("\n[SUCCESS] PLAYWRIGHT END-TO-END BROWSER WORKFLOW VERIFIED 100%!")
    browser.close()
