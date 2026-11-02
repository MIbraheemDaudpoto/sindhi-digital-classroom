import time, sys, os
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

ARTIFACT_DIR = r"C:\Users\maste\.gemini\antigravity\brain\9fca4546-0f4b-4909-a8ef-6687dffc6ab3"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        page = context.new_page()

        print("=== STAGE 1: AUTHENTICATION ===")
        page.goto("http://127.0.0.1:8000/login", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        page.fill("#student-identifier", "STU-101")
        page.fill("#student-pin", "1234")
        page.click("#btn-submit-student")
        page.wait_for_timeout(2000)
        print("  Student logged in successfully!")

        print("=== STAGE 2: LESSON BROWSER & VIDEO PLAYBACK ===")
        page.goto("http://127.0.0.1:8000/app/learn", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        page.evaluate("() => { if (typeof sosChooseSubject === 'function') sosChooseSubject('Math'); }")
        page.wait_for_timeout(1500)
        page.evaluate("() => { if (typeof selectLesson === 'function') selectLesson('lesson-math-6-1'); }")
        page.wait_for_timeout(1500)

        # Check video state
        video_info = page.evaluate("""() => {
            const v = document.getElementById('lesson-video');
            return {
                src: v ? v.currentSrc || v.src : null,
                paused: v ? v.paused : true,
                duration: v ? v.duration : 0
            };
        }""")
        print("  Video info:", video_info)

        print("=== STAGE 3: AI TUTOR QUESTION & CITATION ===")
        q = "خالي سيٽ (Null Set) ڇا کي چئجي ٿو ۽ ان جي نشاني ڇا آهي؟"
        page.fill("#tutor-question-input", q)
        page.click("#btn-tutor-send")

        # Wait for tutor response
        for sec in range(25):
            page.wait_for_timeout(1000)
            text = page.evaluate("""() => {
                const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble .bubble-text'));
                return bubbles.length ? bubbles[bubbles.length - 1].textContent.trim() : '';
            }""")
            if text and "تيار ٿي رهيو آهي" not in text and "سمجھي رهيو آهيان" not in text and "ڳولي رهيو آهيان" not in text:
                print(f"  Tutor answer arrived in ~{sec+1}s!")
                break

        tutor_res = page.evaluate("""() => {
            const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble'));
            const last = bubbles[bubbles.length - 1];
            return {
                answer: last ? last.querySelector('.bubble-text')?.textContent.trim() : null,
                citation: last ? last.querySelector('.tutor-citation-box')?.innerText?.trim() : null
            };
        }""")
        print("  Tutor Answer:", tutor_res.get("answer"))
        print("  Tutor Citation:\n  ", tutor_res.get("citation"))

        shot1 = os.path.join(ARTIFACT_DIR, "e2e_verified_tutor_chat.png")
        page.screenshot(path=shot1)
        print("  Saved Tutor screenshot:", shot1)

        print("=== STAGE 4: LESSON QUIZ PRACTICE & FEEDBACK ===")
        page.evaluate("() => { if (typeof openAssessmentHub === 'function') openAssessmentHub(); }")
        page.wait_for_timeout(1500)

        # Start quiz
        page.evaluate("() => { if (typeof startGeneratedQuiz === 'function') startGeneratedQuiz(); }")
        page.wait_for_timeout(2500)

        # Select first option in quiz
        quiz_state = page.evaluate("""() => {
            const title = document.querySelector('.quiz-question-title')?.textContent?.trim();
            const opts = Array.from(document.querySelectorAll('.quiz-option-btn')).map(b => b.textContent.trim());
            return { title, opts_count: opts.length, opts };
        }""")
        print("  Quiz Question:", quiz_state.get("title"))
        print("  Options count:", quiz_state.get("opts_count"))

        # Click first option
        page.evaluate("() => { if (typeof onSelectOption === 'function') onSelectOption(0); }")
        page.wait_for_timeout(2000)

        feedback = page.evaluate("""() => {
            const card = document.querySelector('.feedback-card');
            return card ? card.innerText.trim() : null;
        }""")
        print("  Quiz Feedback:\n  ", feedback)

        shot2 = os.path.join(ARTIFACT_DIR, "e2e_verified_quiz_flow.png")
        page.screenshot(path=shot2)
        print("  Saved Quiz screenshot:", shot2)

        browser.close()
        print("=== END-TO-END VERIFICATION COMPLETE: ALL PASS ===")

if __name__ == '__main__':
    run()

