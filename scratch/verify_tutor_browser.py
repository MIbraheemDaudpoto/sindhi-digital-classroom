# -*- coding: utf-8 -*-
"""Playwright browser verification for SDC LMS Tutor.
Simulates student interacting with Tutor on Math Sets lesson:
1. Loads /app/learn with authenticated student session.
2. Switches to Mathematics and selects Sets lesson (lesson-math-6-1).
3. Asks: 'سيٽ جي معني ڇا آهي؟'
4. Asks typo query: 'سيت'
Captures high-res screenshots and asserts that both queries receive grounded pedagogical answers.
"""

import json
import os
import sys
import time

sys.path.insert(0, r"D:\Ai Agents\agency-agents\sindhi-digital-classroom")
os.chdir(r"D:\Ai Agents\agency-agents\sindhi-digital-classroom")

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.sync_api import sync_playwright
from src.services.auth_service import auth_service

ARTIFACT_DIR = r"C:\Users\maste\.gemini\antigravity\brain\9fca4546-0f4b-4909-a8ef-6687dffc6ab3"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

def run_verification():
    print("Starting Playwright Tutor Browser Verification...")
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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="sd-PK"
        )
        page = context.new_page()

        # 1. Seed auth
        page.goto("http://127.0.0.1:8000/static/index.html")
        page.evaluate(f"""
            localStorage.setItem('sdc_token', '{token}');
            localStorage.setItem('sdc_current_user', JSON.stringify({json.dumps(user_obj)}));
        """)

        # 2. Go to /app/learn
        page.goto("http://127.0.0.1:8000/app/learn")
        page.wait_for_selector("#tutor-chat-stream", timeout=15000)
        time.sleep(2)

        # 3. Select Mathematics subject and load Sets lesson (lesson-math-6-1)
        print("Selecting Mathematics and loading Sets lesson (lesson-math-6-1)...")
        page.evaluate("""() => {
            if (typeof filterSubject === 'function') {
                filterSubject('math');
            }
            if (typeof selectLesson === 'function') {
                selectLesson('lesson-math-6-1');
            }
        }""")
        time.sleep(2)

        # 4. Ask Question 1: 'سيٽ جي معني ڇا آهي؟'
        print("Submitting question 1: سيٽ جي معني ڇا آهي؟")
        tutor_input = page.locator("#tutor-question-input")
        tutor_input.fill("سيٽ جي معني ڇا آهي؟")

        send_btn = page.locator("#btn-tutor-send")
        send_btn.click()

        # Wait for tutor response
        time.sleep(3.5)
        page.wait_for_selector(".tutor-bubble .bubble-text", timeout=15000)

        # Check response content
        chat_texts = page.locator(".tutor-bubble .bubble-text").all_text_contents()
        latest_answer = chat_texts[-1] if chat_texts else ""
        print(f"Received answer 1: {latest_answer[:120]}...")

        assert "سيٽ" in latest_answer, "Expected 'سيٽ' in tutor response"
        assert "معاف ڪجو" not in latest_answer, "Tutor incorrectly refused valid query!"

        # Screenshot 1
        shot1_path = os.path.join(ARTIFACT_DIR, "tutor_math_sets_meaning_browser.png")
        page.screenshot(path=shot1_path, full_page=False)
        print(f"Screenshot 1 saved to: {shot1_path}")

        # 5. Ask Question 2: 'سيت' (with typing variant Te instead of Tte)
        print("Submitting question 2: سيت")
        tutor_input.fill("سيت")
        send_btn.click()

        # Wait for response
        time.sleep(3.5)
        chat_texts = page.locator(".tutor-bubble .bubble-text").all_text_contents()
        latest_answer_2 = chat_texts[-1] if chat_texts else ""
        print(f"Received answer 2: {latest_answer_2[:120]}...")

        assert "سيٽ" in latest_answer_2, "Expected 'سيٽ' in response to typo query 'سيت'"
        assert "معاف ڪجو" not in latest_answer_2, "Typo query 'سيت' was incorrectly refused!"

        # Screenshot 2
        shot2_path = os.path.join(ARTIFACT_DIR, "tutor_math_sets_typo_browser.png")
        page.screenshot(path=shot2_path, full_page=False)
        print(f"Screenshot 2 saved to: {shot2_path}")

        browser.close()
        print("SUCCESS: Playwright Tutor Browser Verification Passed Completely!")

if __name__ == "__main__":
    run_verification()
