import asyncio
import os
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    print("==================================================")
    print("STARTING COMPLETE BROWSER AUDIT OF SDC LMS")
    print("==================================================")
    os.makedirs("scratch/screenshots", exist_ok=True)
    logs = []
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 850})
        page = await context.new_page()

        page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))

        print("\nStep 1: Navigate to LMS App (/app/learn)...")
        await page.goto("http://127.0.0.1:8000/app/learn", wait_until="networkidle")
        await asyncio.sleep(1)

        if "login" in page.url:
            print("Detected Login page. Submitting student credentials (STU-101 / 1234)...")
            await page.fill("#student-identifier", "STU-101")
            await page.fill("#student-pin", "1234")
            await page.click("#btn-submit-student")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            print("Logged in successfully. New URL:", page.url)

        await page.screenshot(path="scratch/screenshots/e2e_01_learn_dashboard.png")

        print("\nStep 2: Verify LMS Curriculum Navigation...")
        lesson_cards = await page.query_selector_all(".lesson-card")
        print(f"Total lesson cards displayed on dashboard: {len(lesson_cards)}")
        for idx, card in enumerate(lesson_cards[:4]):
            title = await card.query_selector(".lesson-title")
            unit = await card.query_selector(".lesson-unit-tag")
            print(f"  Lesson {idx+1}: {await unit.inner_text() if unit else 'No Unit'} - {await title.inner_text() if title else 'No Title'}")

        print("\nStep 3: Test AI Tutor (Search & Ask in LMS)...")
        tutor_input = await page.query_selector("#tutor-query-input, #input-tutor-message, textarea[placeholder*='سوال']")
        if tutor_input:
            print("Tutor input found. Asking question: 'جيو گهرڙو ڇا آهي؟'...")
            await tutor_input.fill("جيو گهرڙو ڇا آهي؟")
            ask_btn = await page.query_selector("#btn-tutor-send, button:has-text('پڇو'), button:has-text('موڪليو')")
            if ask_btn:
                await ask_btn.click()
                print("Waiting for tutor response...")
                await asyncio.sleep(4)
                await page.screenshot(path="scratch/screenshots/e2e_02_tutor_response.png")
                tutor_msgs = await page.query_selector_all(".tutor-msg-bot, .chat-bubble-bot, .response-bubble")
                if tutor_msgs:
                    latest_msg = await tutor_msgs[-1].inner_text()
                    print(f"Tutor responded: {latest_msg[:120]}...")

        print("\nStep 4: Open Assessment Hub Modal...")
        await page.evaluate("window.openAssessmentHub ? window.openAssessmentHub() : null")
        await asyncio.sleep(1)
        await page.screenshot(path="scratch/screenshots/e2e_03_assessment_hub.png")

        # Verify Science lessons in checklist
        sci_rows = await page.query_selector_all("#quiz-lessons-checklist .lesson-check-row")
        print(f"Science lessons in checklist: {len(sci_rows)}")
        for i, row in enumerate(sci_rows[:3]):
            unit = await row.query_selector(".lesson-check-unit")
            title = await row.query_selector(".lesson-check-title")
            print(f"  Sci Item {i+1}: {await unit.inner_text() if unit else ''} - {await title.inner_text() if title else ''}")

        print("\nStep 5: Switch to Mathematics...")
        await page.evaluate("window.onQuizSubjectChanged('Mathematics')")
        await asyncio.sleep(1)
        await page.screenshot(path="scratch/screenshots/e2e_04_math_checklist.png")

        math_rows = await page.query_selector_all("#quiz-lessons-checklist .lesson-check-row")
        print(f"Mathematics lessons in checklist: {len(math_rows)}")
        for i, row in enumerate(math_rows[:5]):
            unit = await row.query_selector(".lesson-check-unit")
            title = await row.query_selector(".lesson-check-title")
            print(f"  Math Item {i+1}: {await unit.inner_text() if unit else ''} - {await title.inner_text() if title else ''}")

        print("\nStep 6: Switch back to Science, set Practice Mode & 3 Questions...")
        await page.evaluate("window.onQuizSubjectChanged('Science')")
        await asyncio.sleep(1)
        await page.evaluate("window.onQuizModeChanged('PRACTICE')")
        await asyncio.sleep(0.5)
        await page.evaluate("window.onQuizCountChanged(3)")
        await asyncio.sleep(0.5)

        # Select Unit 1
        await page.evaluate("window.selectAllQuizLessons(false)")
        await asyncio.sleep(0.5)
        await page.evaluate("window.toggleQuizLessonSelection('lesson-sci-6-1')")
        await asyncio.sleep(0.5)
        await page.screenshot(path="scratch/screenshots/e2e_05_configured_assessment.png")

        selected_summary = await page.evaluate("() => document.getElementById('quiz-scope-summary')?.innerText || ''")
        print(f"Configured Assessment Scope: {selected_summary}")

        print("\nStep 7: Launch Generated Quiz...")
        await page.evaluate("window.startGeneratedQuiz()")
        await asyncio.sleep(3)
        await page.screenshot(path="scratch/screenshots/e2e_06_quiz_active.png")

        # Verify Quiz Runner displayed
        q_count = await page.evaluate("window.QuizState ? QuizState.questions.length : 0")
        provider = await page.evaluate("window.QuizState ? QuizState.providerStatus : ''")
        badge_text = await page.evaluate("() => document.querySelector('.runner-badge-prov')?.innerText || ''")
        print(f"Quiz successfully generated: {q_count} questions.")
        print(f"Provider: {provider} | Provenance Badge: {badge_text}")

        # Check Question 1
        q1_text = await page.evaluate("() => document.querySelector('.question-title-text')?.innerText || ''")
        print(f"Question 1: {q1_text}")
        options = await page.query_selector_all(".option-btn")
        print(f"Options for Q1 ({len(options)} total):")
        for oi, opt in enumerate(options):
            txt = await opt.inner_text()
            print(f"  Option {oi+1}: {txt.strip().replace(chr(10), ' - ')}")

        # Verify authentic distractors (no dummy options)
        for oi, opt in enumerate(options):
            txt = await opt.inner_text()
            assert "هي تصور درسي نصاب ۾ شامل ناهي" not in txt, f"Forbidden dummy option found in Option {oi+1}!"
            assert "مٿيان سمورا جواب نامڪمل آهن" not in txt, f"Forbidden dummy option found in Option {oi+1}!"

        print("\nStep 8: Submit Answer for Q1 in Practice Mode...")
        if options:
            await options[0].click()
            await asyncio.sleep(1)
            await page.screenshot(path="scratch/screenshots/e2e_07_practice_feedback.png")

            feedback_box = await page.query_selector("#runner-instant-feedback")
            if feedback_box:
                fb_text = await feedback_box.inner_text()
                print("Immediate Feedback displayed:")
                print(f"  {fb_text.replace(chr(10), ' ')}")

        print("\nStep 9: Answer remaining questions and submit...")
        for q_idx in range(1, q_count):
            print(f"Moving to Question {q_idx + 1}...")
            await page.evaluate("window.goToNextQuestion()")
            await asyncio.sleep(1)
            cur_options = await page.query_selector_all(".option-btn")
            if cur_options:
                await cur_options[0].click()
                await asyncio.sleep(1)

        print("Clicking Final Submit on last question...")
        await page.evaluate("window.goToNextQuestion()")
        await asyncio.sleep(3)
        await page.screenshot(path="scratch/screenshots/e2e_08_results_screen.png")

        # Verify Results Screen
        results_header = await page.evaluate("() => document.querySelector('.results-summary-text h2')?.innerText || ''")
        score_text = await page.evaluate("() => document.querySelector('.results-score-number')?.innerText || ''")
        score_label = await page.evaluate("() => document.querySelector('.results-score-label')?.innerText || ''")
        print(f"Results Header: {results_header}")
        print(f"Score: {score_text} ({score_label})")

        breakdown_rows = await page.query_selector_all(".lesson-breakdown-row, .results-breakdown-card")
        print(f"Lesson breakdown items in result: {len(breakdown_rows)}")

        print("\nStep 10: Close Modal and Verify Dashboard Progress...")
        await page.evaluate("window.closeAssessmentModal()")
        await asyncio.sleep(1)
        await page.goto("http://127.0.0.1:8000/app/progress", wait_until="networkidle")
        await asyncio.sleep(2)
        await page.screenshot(path="scratch/screenshots/e2e_09_progress_page.png")
        print("Progress page title:", await page.title())

        # Inspect any recorded client errors
        print("\n=== Console & Page Errors Summary ===")
        print(f"Total Page Errors: {len(errors)}")
        for err in errors:
            print("  PAGE ERROR:", err)

        warn_or_err_logs = [l for l in logs if "error" in l.lower() or "fail" in l.lower()]
        print(f"Relevant Console Warnings/Errors: {len(warn_or_err_logs)}")
        for l in warn_or_err_logs[:5]:
            print("  LOG:", l)

        await browser.close()
    print("\n==================================================")
    print("BROWSER AUDIT COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
