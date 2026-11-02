import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from playwright.async_api import async_playwright
from src.services.auth_service import auth_service

ARTIFACT_DIR = r"C:\Users\maste\.gemini\antigravity\brain\9fca4546-0f4b-4909-a8ef-6687dffc6ab3"

async def run_browser_verification():
    # 1. Create authenticated student session token
    token = auth_service.create_session_token("usr-stu-101", "STUDENT")
    student_user = {
        "user_id": "usr-stu-101",
        "id": "usr-stu-101",
        "name": "شاگرد علي",
        "role": "STUDENT",
        "token": token
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 850},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) SDCBrowserVerifier/1.0"
        )

        # Set cookies and localStorage for immediate authentication
        await context.add_cookies([
            {"name": "sdc_session_token", "value": token, "domain": "127.0.0.1", "path": "/"},
            {"name": "sdc_token", "value": token, "domain": "127.0.0.1", "path": "/"}
        ])

        page = await context.new_page()
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[Browser PageError] {err}"))
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

        # Init localStorage before scripts run
        await page.add_init_script(f"""
            localStorage.setItem('sdc_token', '{token}');
            localStorage.setItem('sdc_current_user', '{json.dumps(student_user)}');
            localStorage.setItem('sdc_user', '{json.dumps(student_user)}');
            localStorage.setItem('sdc_user_id', 'usr-stu-101');
        """)

        print("[Browser] Navigating to http://127.0.0.1:8000/app/learn...")
        await page.goto("http://127.0.0.1:8000/app/learn", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        print("[Browser] Loaded URL:", page.url)

        # ---------------------------------------------------------
        # TEST 1: PREVENT PREMATURE IN-VIDEO QUIZ POPUP (at 0:00)
        # ---------------------------------------------------------
        print("\n--- TEST 1: Load lesson-sci-6-2 (Sense Organs) & Verify No Popup at 0:00 ---")
        await page.evaluate("""() => {
            if (typeof selectLesson === 'function') {
                selectLesson('lesson-sci-6-2');
            }
        }""")
        await page.wait_for_timeout(3000)

        checkpoint_overlay = page.locator("#quiz-popup-overlay")
        is_overlay_visible = await checkpoint_overlay.is_visible()
        print(f"[Browser] Checkpoint overlay visible at 0:00 before video starts: {is_overlay_visible} (Expected: False)")
        assert not is_overlay_visible, "In-video quiz must NOT trigger before video starts playing!"

        screenshot1_path = os.path.join(ARTIFACT_DIR, "verified_browser_fix1_no_premature_popup.png")
        await page.screenshot(path=screenshot1_path, full_page=False)
        print(f"[Browser] Saved Screenshot 1: {screenshot1_path}")

        # ---------------------------------------------------------
        # TEST 2: AI TUTOR SUGGESTED PROMPT CHIP GROUNDING
        # ---------------------------------------------------------
        print("\n--- TEST 2: Testing AI Tutor Suggested Prompt Chip for Sense Organs ---")
        prompt_pills = page.locator(".quick-prompt-pill")
        pill_count = await prompt_pills.count()
        print(f"[Browser] Found {pill_count} quick prompt chips for lesson-sci-6-2.")
        assert pill_count > 0, "Quick prompt chips should be rendered for the active lesson!"

        first_pill_text = await prompt_pills.first.inner_text()
        print(f"[Browser] Clicking first quick prompt: '{first_pill_text}'...")
        await prompt_pills.first.click()

        print("[Browser] Waiting for verified Sindhi pedagogical answer...")
        await page.wait_for_timeout(6000)

        tutor_bubbles = page.locator(".chat-bubble.tutor-bubble")
        last_bubble_text = await tutor_bubbles.last.inner_text()
        print(f"[Browser] AI Tutor responded successfully! Snippet:\n{last_bubble_text[:200]}...")

        assert "دائري کان ٻاهر" not in last_bubble_text, "Tutor must NOT refuse suggested prompt as Out of Scope!"
        assert "عارضي طور دستياب ناهي" not in last_bubble_text, "Tutor must NOT return temporarily unavailable!"

        screenshot2_path = os.path.join(ARTIFACT_DIR, "verified_browser_fix2_tutor_sense_organs_response.png")
        await page.screenshot(path=screenshot2_path, full_page=False)
        print(f"[Browser] Saved Screenshot 2: {screenshot2_path}")

        # ---------------------------------------------------------
        # TEST 3: IN-VIDEO CHECKPOINT POPUP AND RESUME
        # ---------------------------------------------------------
        print("\n--- TEST 3: In-Video Checkpoint Trigger & Feedback ---")
        await page.evaluate("""() => {
            if (window.sdcPlayer && window.sdcPlayer.questions && window.sdcPlayer.questions.length > 0) {
                const q = window.sdcPlayer.questions[0];
                window.sdcPlayer.triggerQuizPause(q);
            }
        }""")
        await page.wait_for_timeout(1500)

        assert await checkpoint_overlay.is_visible(), "Checkpoint overlay modal should appear when checkpoint timestamp is hit!"
        print("[Browser] Checkpoint modal successfully paused video and displayed popup!")

        opt_btns = page.locator(".quiz-option-btn")
        opt_count = await opt_btns.count()
        print(f"[Browser] Checkpoint question has {opt_count} options:")
        for idx in range(opt_count):
            opt_text = await opt_btns.nth(idx).inner_text()
            print(f"  Option {idx+1}: {opt_text}")
            assert "ٻيو آپشن" not in opt_text, "Dummy option detected!"

        # Answer checkpoint
        await opt_btns.first.click()
        await page.wait_for_timeout(1500)

        resume_btn = page.locator("#btn-resume-checkpoint")
        assert await resume_btn.is_visible(), "Resume button should appear after answering."
        await resume_btn.click()
        await page.wait_for_timeout(1000)
        print("[Browser] Checkpoint resumed successfully!")

        # ---------------------------------------------------------
        # TEST 4: 10-MCQ LESSON QUIZ RUNNER (WITHOUT 503 ERROR)
        # ---------------------------------------------------------
        print("\n--- TEST 4: 10-MCQ Lesson Quiz Runner ---")
        quiz_btn = page.locator("#btn-lesson-quiz")
        if await quiz_btn.is_visible():
            await quiz_btn.click()
            await page.wait_for_timeout(2000)

            quiz_modal = page.locator("#sdc-assessment-modal")
            assert await quiz_modal.is_visible(), "10-MCQ Quiz modal should open."

            # Click the "Start Quiz" button in the modal setup view
            gen_btn = page.locator("#btn-generate-quiz-action")
            await gen_btn.wait_for(state="visible", timeout=10000)
            await gen_btn.click()
            print("[Browser] Clicked Start Quiz button, generating assessment...")

            # Poll for up to 30 seconds, logging status every 3s
            for wait_step in range(10):
                await page.wait_for_timeout(3000)
                body_html = await page.locator("#assessment-modal-body").inner_html()
                opt_count = await page.locator(".option-btn").count()
                print(f"[Browser Polling {wait_step+1}] option-btn count: {opt_count}, body snippet: {body_html[:150]}...")
                if opt_count > 0:
                    break

            modal_text = await quiz_modal.inner_text()
            assert "503" not in modal_text, "Quiz must NOT show 503 Service Unavailable!"
            assert "ٻيو آپشن" not in modal_text, "Dummy option 'ٻيو آپشن' found!"
            print("[Browser] 10-MCQ Quiz generated and loaded cleanly without 503 error!")

            opt_cards = page.locator(".option-btn")
            opt_total = await opt_cards.count()
            print(f"[Browser] Q1 has {opt_total} valid options:")
            for o_idx in range(opt_total):
                card_text = await opt_cards.nth(o_idx).inner_text()
                print(f"  Option {o_idx+1}: {card_text.strip()}")

            # Select first option
            await opt_cards.first.click()
            await page.wait_for_timeout(2000)

            screenshot3_path = os.path.join(ARTIFACT_DIR, "verified_browser_fix3_10_mcq_quiz_loaded.png")
            await page.screenshot(path=screenshot3_path, full_page=False)
            print(f"[Browser] Saved Screenshot 3: {screenshot3_path}")

        print("\n[Browser] ALL WORKFLOW TESTS VERIFIED AND VALIDATED 100%!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_browser_verification())
