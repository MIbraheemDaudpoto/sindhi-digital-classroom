import asyncio
import os
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def test_live_browser():
    print("=== STARTING DIRECT BROWSER RUN FOR LMS & MATHEMATICS QUIZ ===")
    os.makedirs("scratch/screenshots", exist_ok=True)
    logs = []
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 850})
        page = await context.new_page()

        page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))

        print("1. Opening http://127.0.0.1:8000/app/learn in browser...")
        await page.goto("http://127.0.0.1:8000/app/learn", wait_until="networkidle")
        await asyncio.sleep(1)

        # Login if needed
        if "login" in page.url:
            print("Authenticating student STU-101...")
            await page.fill("#student-identifier", "STU-101")
            await page.fill("#student-pin", "1234")
            await page.click("#btn-submit-student")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            print("Logged in successfully. URL:", page.url)

        await page.screenshot(path="scratch/screenshots/direct_01_learn_dashboard.png")

        print("2. Opening Assessment Hub...")
        await page.evaluate("window.openAssessmentHub ? window.openAssessmentHub() : null")
        await asyncio.sleep(1)
        await page.screenshot(path="scratch/screenshots/direct_02_assessment_opened.png")

        print("3. Switching to Mathematics (reproducing exact user action)...")
        await page.evaluate("window.onQuizSubjectChanged('Mathematics')")
        await asyncio.sleep(1)
        await page.screenshot(path="scratch/screenshots/direct_03_math_selected.png")

        # Verify Math lessons listed
        math_lessons = await page.query_selector_all("#quiz-lessons-checklist .lesson-check-row")
        print(f"Total Math lessons loaded: {len(math_lessons)}")
        for idx, row in enumerate(math_lessons[:3]):
            print(f"  Math Unit {idx+1}: {(await row.inner_text()).replace(chr(10), ' | ')}")

        print("4. Clicking 'Start Quiz' for Mathematics (نئون ڪوئز تيار ڪريو)...")
        # Ensure at least 1 unit selected
        await page.evaluate("""() => {
            if (QuizState.selectedLessons.size === 0 && QuizState.allLessonsForSubject.length > 0) {
                QuizState.selectedLessons.add(QuizState.allLessonsForSubject[0].id);
            }
        }""")
        await page.evaluate("window.startGeneratedQuiz()")
        await asyncio.sleep(3)
        await page.screenshot(path="scratch/screenshots/direct_04_math_quiz_running.png")

        # Check if error dialog appeared or if quiz runner is active
        err_box = await page.query_selector(".assessment-error-screen")
        if err_box:
            err_text = await err_box.inner_text()
            print("ERROR: Assessment error appeared!")
            print(err_text)
            assert False, f"Assessment error occurred: {err_text}"
        else:
            print("SUCCESS: Mathematics Quiz generated and running smoothly!")
            q_title = await page.evaluate("() => document.querySelector('.question-title-text')?.innerText || ''")
            badge = await page.evaluate("() => document.querySelector('.runner-badge-prov')?.innerText || ''")
            print(f"Question Title: {q_title}")
            print(f"Provenance Badge: {badge}")

            # Verify options
            options = await page.query_selector_all(".option-btn")
            print(f"Options ({len(options)} total):")
            for oi, opt in enumerate(options):
                print(f"  Option {oi+1}: {(await opt.inner_text()).replace(chr(10), ' - ')}")

            # Answer Question 1
            if options:
                print("Clicking Option 1...")
                await options[0].click()
                await asyncio.sleep(1)
                await page.screenshot(path="scratch/screenshots/direct_05_math_answered.png")

        print("5. Closing modal and checking Lesson Player...")
        await page.evaluate("window.closeAssessmentModal()")
        await asyncio.sleep(1)

        # Trigger selectLesson directly via JS
        await page.evaluate("window.selectLesson ? window.selectLesson('lesson-sci-6-1') : null")
        await asyncio.sleep(2)
        await page.screenshot(path="scratch/screenshots/direct_06_lesson_detail.png")
        lesson_title = await page.evaluate("() => document.getElementById('lesson-header-title')?.innerText || ''")
        print(f"Selected Lesson: {lesson_title}")

        print("6. Testing AI Tutor Question...")
        tutor_input = await page.query_selector("#tutor-query-input, #input-tutor-message, textarea[placeholder*='سوال']")
        if tutor_input:
            await tutor_input.fill("رياضي ۾ سيٽ ڇا کي چئبو آهي؟")
            ask_btn = await page.query_selector("#btn-tutor-send, button:has-text('پڇو'), button:has-text('موڪليو')")
            if ask_btn:
                await ask_btn.click()
                print("Waiting for tutor response...")
                await asyncio.sleep(4)
                await page.screenshot(path="scratch/screenshots/direct_07_tutor_answered.png")
                tutor_msgs = await page.query_selector_all(".tutor-msg-bot, .chat-bubble-bot, .response-bubble")
                if tutor_msgs:
                    print("Tutor response:", (await tutor_msgs[-1].inner_text())[:150])

        print("\n=== Browser Logs Summary ===")
        print(f"Total Errors: {len(errors)}")
        for e in errors:
            print("  PAGE ERROR:", e)

        print("\n=== DIRECT BROWSER RUN COMPLETE ===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_live_browser())
