import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def audit_lms():
    print("=== Starting Playwright LMS Audit ===")
    os.makedirs("scratch/screenshots", exist_ok=True)
    logs = []
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))

        print("1. Navigating to http://127.0.0.1:8000/app/learn...")
        await page.goto("http://127.0.0.1:8000/app/learn", wait_until="networkidle")
        await page.screenshot(path="scratch/screenshots/01_app_learn_initial.png")

        print("Current URL:", page.url)
        page_title = await page.title()
        print("Page title:", page_title)

        # Handle login if redirected
        if "login" in page.url:
            print("Logging in with STU-101 / 1234...")
            await page.fill("#student-identifier", "STU-101")
            await page.fill("#student-pin", "1234")
            await page.click("#btn-submit-student")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await page.screenshot(path="scratch/screenshots/02_after_login.png")
            print("URL after login:", page.url)

        if "/app/learn" not in page.url:
            await page.goto("http://127.0.0.1:8000/app/learn", wait_until="networkidle")
            await asyncio.sleep(2)

        await page.screenshot(path="scratch/screenshots/03_learn_dashboard.png")

        # Check lessons listed
        lesson_cards = await page.query_selector_all(".lesson-card")
        print(f"Found {len(lesson_cards)} lesson cards on dashboard.")

        # Check if Start Quiz button or Assessment Hub exists
        assessment_btn = await page.query_selector("#btn-open-assessment-hub")
        print("Assessment button found:", assessment_btn is not None)

        # Open Assessment Modal
        print("2. Opening Assessment Hub...")
        await page.evaluate("window.openAssessmentHub ? window.openAssessmentHub() : console.error('No openAssessmentHub')")
        await asyncio.sleep(1)
        await page.screenshot(path="scratch/screenshots/04_assessment_hub_modal.png")

        # Inspect checklist items in modal
        modal_checklist = await page.query_selector_all("#quiz-lessons-checklist .lesson-check-row")
        print(f"Found {len(modal_checklist)} lessons in quiz modal checklist for default selection.")
        for idx, row in enumerate(modal_checklist[:5]):
            text = await row.inner_text()
            print(f"  Row {idx+1}: {text.replace(chr(10), ' | ')}")

        # Switch to Mathematics
        print("3. Switching to Mathematics...")
        math_btn = await page.query_selector("button:has-text('رياضي')")
        if math_btn:
            await math_btn.click()
            await asyncio.sleep(1)
            await page.screenshot(path="scratch/screenshots/05_assessment_math_selected.png")
            math_checklist = await page.query_selector_all("#quiz-lessons-checklist .lesson-check-row")
            print(f"Found {len(math_checklist)} lessons in quiz modal for Mathematics.")
            for idx, row in enumerate(math_checklist[:5]):
                text = await row.inner_text()
                print(f"  Math Row {idx+1}: {text.replace(chr(10), ' | ')}")

        # Switch back to Science
        print("4. Switching back to Science...")
        sci_btn = await page.query_selector("button:has-text('سائنس')")
        if sci_btn:
            await sci_btn.click()
            await asyncio.sleep(1)

        # Choose Practice mode (مشقي موڊ)
        practice_btn = await page.query_selector("button:has-text('مشقي موڊ')")
        if practice_btn:
            await practice_btn.click()

        # Click Start Quiz
        print("5. Clicking Start Quiz (نئون ڪوئز تيار ڪريو)...")
        gen_btn = await page.query_selector("#btn-generate-assessment")
        if gen_btn:
            await gen_btn.click()
            # Wait for questions to load
            print("Waiting for questions to render...")
            await asyncio.sleep(3)
            await page.screenshot(path="scratch/screenshots/06_quiz_started.png")

            # Check if quiz questions container is displayed
            q_text_el = await page.query_selector(".assessment-question-text, .quiz-question-title")
            if q_text_el:
                print("Quiz Question Text:", await q_text_el.inner_text())
                badge = await page.query_selector(".assessment-provenance-badge")
                if badge:
                    print("Provenance Badge:", await badge.inner_text())

                # Click an option
                options = await page.query_selector_all(".quiz-option-btn")
                print(f"Found {len(options)} options for question 1.")
                for o_idx, opt in enumerate(options):
                    print(f"  Option {o_idx+1}: {await opt.inner_text()}")

                if len(options) >= 2:
                    await options[1].click()
                    await asyncio.sleep(1)
                    await page.screenshot(path="scratch/screenshots/07_practice_feedback.png")

                    # Check feedback
                    feedback_el = await page.query_selector(".feedback-box, .answer-feedback")
                    if feedback_el:
                        print("Feedback text:", (await feedback_el.inner_text())[:120])
            else:
                err_box = await page.query_selector(".assessment-error-screen, .error-msg-sindhi")
                if err_box:
                    print("ERROR SCREEN TEXT:", await err_box.inner_text())

        print("=== Console Errors recorded ===")
        for e in errors:
            print("PAGE ERROR:", e)
        for l in logs:
            if "error" in l.lower() or "warn" in l.lower():
                print("LOG:", l)

        await browser.close()
    print("=== Audit complete ===")

if __name__ == "__main__":
    asyncio.run(audit_lms())
