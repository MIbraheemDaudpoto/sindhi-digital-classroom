import asyncio
import os
import sys
import sqlite3
import json
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

ARTIFACT_DIR = r"C:\Users\maste\.gemini\antigravity\brain\9fca4546-0f4b-4909-a8ef-6687dffc6ab3"

async def run_verification():
    print("--- 1. STARTING BROWSER END-TO-END VERIFICATION ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 768})
        page = await context.new_page()

        # Step 1: Open Login and Log in as Student
        print("Navigating to login page...")
        await page.goto("http://127.0.0.1:8000/login", wait_until="networkidle")
        
        # Verify Font on Login Page
        font_login = await page.evaluate("() => window.getComputedStyle(document.body).fontFamily")
        print(f"Login body font-family: {font_login}")
        assert "MB Sindhi web" in font_login

        # Fill student login
        # First check a student account from db
        conn = sqlite3.connect("data/sdc_platform.db")
        conn.row_factory = sqlite3.Row
        stu = conn.execute("SELECT id, pseudonymous_code, pin_hash FROM users WHERE role = 'STUDENT' LIMIT 1").fetchone()
        student_code = stu["pseudonymous_code"]
        print(f"Logging in as student: {student_code}")

        # In SDC, student logs in with identifier + PIN 1234
        await page.fill("#student-identifier", student_code)
        await page.fill("#student-pin", "1234")
        await page.click("#btn-submit-student")
        await page.wait_for_timeout(2000)

        # Should be on /app or /app/learn
        print(f"Current URL after login: {page.url}")
        if "/app/learn" not in page.url:
            await page.goto("http://127.0.0.1:8000/app/learn", wait_until="networkidle")
            await page.wait_for_timeout(1500)

        # Step 2: Verify MB Sindhi Web font loaded and applied on LMS page
        font_check = await page.evaluate("""() => {
            return {
                bodyFont: window.getComputedStyle(document.body).fontFamily,
                checkMBSindhiWeb: document.fonts.check('16px "MB Sindhi web"'),
                checkBoldMBSindhiWeb: document.fonts.check('bold 16px "MB Sindhi web"'),
                btnFont: window.getComputedStyle(document.querySelector('#btn-mark-watched')).fontFamily
            };
        }""")
        print(f"LMS Font Check: {font_check}")
        assert "MB Sindhi web" in font_check["bodyFont"]
        assert font_check["checkMBSindhiWeb"] is True

        # Screenshot 1: LMS with MB Sindhi web font
        snap1_path = os.path.join(ARTIFACT_DIR, "verified_mb_sindhi_web_font_lms.png")
        await page.screenshot(path=snap1_path, full_page=False)
        print(f"Saved snapshot 1: {snap1_path}")

        # Step 3: Select Science Unit 3 (lesson-sci-6-3)
        print("Selecting Science Unit 3 (lesson-sci-6-3)...")
        await page.evaluate("() => selectLesson('lesson-sci-6-3')")
        await page.wait_for_timeout(2000)

        # Check in-video quiz checkpoints loaded in player
        player_check = await page.evaluate("""() => {
            return {
                currentLessonId: sdcPlayer.currentLesson ? sdcPlayer.currentLesson.id : null,
                questionsCount: sdcPlayer.questions ? sdcPlayer.questions.length : 0,
                firstQuestion: sdcPlayer.questions && sdcPlayer.questions[0] ? sdcPlayer.questions[0].text_sindhi : null
            };
        }""")
        print(f"Player questions check: {player_check}")
        assert player_check["questionsCount"] >= 3, "Expected at least 3 checkpoints for Unit 3"

        # Trigger in-video checkpoint modal
        print("Triggering in-video quiz popup at 60s checkpoint...")
        await page.evaluate("""() => {
            const q = sdcPlayer.questions[0];
            sdcPlayer.triggerQuizPause(q);
        }""")
        await page.wait_for_timeout(1000)

        # Verify quiz modal is visible and check font & content
        modal_visible = await page.is_visible("#quiz-popup-overlay")
        print(f"Quiz overlay visible: {modal_visible}")
        assert modal_visible is True

        # Check question text and options
        modal_content = await page.evaluate("""() => {
            const qText = document.querySelector('.quiz-question-text');
            const opts = Array.from(document.querySelectorAll('.quiz-option-btn')).map(b => b.textContent.trim());
            const font = qText ? window.getComputedStyle(qText).fontFamily : null;
            return {
                question: qText ? qText.textContent.trim() : null,
                options: opts,
                font: font
            };
        }""")
        print(f"Checkpoint content: {modal_content}")
        assert "MB Sindhi web" in modal_content["font"]
        assert len(modal_content["options"]) == 4

        # Screenshot 2: In-video checkpoint popup
        snap2_path = os.path.join(ARTIFACT_DIR, "verified_in_video_quiz_checkpoint_popup.png")
        await page.screenshot(path=snap2_path, full_page=False)
        print(f"Saved snapshot 2: {snap2_path}")

        # Submit answer to checkpoint (click first option)
        print("Submitting answer to in-video checkpoint...")
        await page.click("#quiz-opt-0")
        await page.wait_for_timeout(1500)

        # Verify feedback box is displayed
        feedback_visible = await page.is_visible("#quiz-feedback-box")
        print(f"Feedback box visible: {feedback_visible}")
        assert feedback_visible is True

        feedback_text = await page.evaluate("() => document.getElementById('quiz-feedback-box').textContent")
        print(f"Feedback text: {feedback_text.strip()[:100]}...")

        # Resume playback
        print("Resuming playback...")
        await page.click("#btn-resume-checkpoint")
        await page.wait_for_timeout(1000)
        assert await page.is_visible("#quiz-popup-overlay") is False

        # Step 4: Test Mark as Watched & Student Progress Update
        print("Clicking 'Mark as Watched' button...")
        # Check current progress in DB before
        c = conn.cursor()
        c.execute("SELECT * FROM progress WHERE user_id = ? AND lesson_id = 'lesson-sci-6-3'", (stu["id"],))
        prev_row = c.fetchone()
        print(f"Progress before: {dict(prev_row) if prev_row else 'None'}")

        # Click the mark as watched button
        await page.click("#btn-mark-watched")
        await page.wait_for_timeout(2000)

        # Check DB after
        c.execute("SELECT * FROM progress WHERE user_id = ? AND lesson_id = 'lesson-sci-6-3'", (stu["id"],))
        post_row = c.fetchone()
        print(f"Progress after: {dict(post_row) if post_row else 'None'}")
        assert post_row is not None
        assert post_row["is_completed"] == 1
        print("Verified in database: is_completed = 1")

        # Check UI button label and playlist card badge
        ui_status = await page.evaluate("""() => {
            const btnLabel = document.getElementById('btn-mark-watched-label').textContent;
            const card = document.getElementById('card-lesson-sci-6-3');
            const check = card ? card.querySelector('.lesson-completed-check') : null;
            return {
                btnLabel: btnLabel,
                hasCheckOnCard: !!check,
                checkText: check ? check.textContent : null,
                isInCompletedSet: window.completedLessonsSet ? window.completedLessonsSet.has('lesson-sci-6-3') : false
            };
        }""")
        print(f"UI Status after mark watched: {ui_status}")
        assert "مڪمل ٿيل" in ui_status["btnLabel"]
        assert ui_status["isInCompletedSet"] is True

        # Screenshot 3: Watched badge and updated button
        snap3_path = os.path.join(ARTIFACT_DIR, "verified_video_watched_and_progress_updated.png")
        await page.screenshot(path=snap3_path, full_page=False)
        print(f"Saved snapshot 3: {snap3_path}")

        print("\n--- ALL VERIFICATIONS PASSED SUCCESSFULLY! ---")
        await browser.close()
        conn.close()

if __name__ == "__main__":
    asyncio.run(run_verification())
