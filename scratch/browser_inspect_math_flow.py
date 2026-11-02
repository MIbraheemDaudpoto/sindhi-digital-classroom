import time, sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[ERROR] {err}"))

        print("1. Navigating to login page...")
        page.goto("http://127.0.0.1:8000/login")
        page.wait_for_load_state("networkidle")

        # Fill student credentials
        page.fill("#student-identifier", "STU-101")
        page.fill("#student-pin", "1234")
        page.click("#btn-submit-student")
        page.wait_for_timeout(2000)

        print("URL after login:", page.url)

        # Go to /app/learn
        print("2. Navigating to /app/learn...")
        page.goto("http://127.0.0.1:8000/app/learn")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2500)

        # Inspect state after page load
        init_state = page.evaluate("""() => ({
            lessonId: window.currentLoadedLessonId,
            lessonTitle: document.getElementById('current-lesson-title')?.textContent,
            ytDisplay: document.getElementById('sdc-youtube-iframe')?.style.display,
            ytSrc: document.getElementById('sdc-youtube-iframe')?.src,
            vidDisplay: document.getElementById('sdc-video-player')?.style.display
        })""")
        print(f"Initial Learn Page State:\n  Lesson: {init_state['lessonTitle']} (ID: {init_state['lessonId']})\n  YT Display: {init_state['ytDisplay']}, Src: {init_state['ytSrc']}")

        # 3. Switch to Mathematics subject
        print("\n3. Switching to Mathematics subject via sosChooseSubject('Math')...")
        page.evaluate("() => sosChooseSubject('Math')")
        page.wait_for_timeout(2500)

        math_state = page.evaluate("""() => ({
            lessonId: window.currentLoadedLessonId,
            lessonTitle: document.getElementById('current-lesson-title')?.textContent,
            lessonUnit: document.getElementById('current-lesson-unit')?.textContent,
            ytDisplay: document.getElementById('sdc-youtube-iframe')?.style.display,
            ytSrc: document.getElementById('sdc-youtube-iframe')?.src,
            vidDisplay: document.getElementById('sdc-video-player')?.style.display,
            activeBadge: document.getElementById('tutor-active-lesson-badge')?.textContent
        })""")
        print(f"State After Choosing Math:\n  Lesson: {math_state['lessonTitle']} ({math_state['lessonUnit']})\n  ID: {math_state['lessonId']}\n  YT Display: {math_state['ytDisplay']}\n  YT Src: {math_state['ytSrc']}\n  Tutor Badge: {math_state['activeBadge']}")

        # Capture screenshot of Math Lesson 1 with YouTube Video
        screenshot1 = "C:/Users/maste/.gemini/antigravity/brain/9fca4546-0f4b-4909-a8ef-6687dffc6ab3/playwright_math_flow_lesson1.png"
        page.screenshot(path=screenshot1)
        print("Saved screenshot 1 to:", screenshot1)

        # 4. Switch to Math Lesson 2 (Whole Numbers)
        print("\n4. Clicking Math Lesson 2 (Whole Numbers)...")
        page.evaluate("() => selectLesson('lesson-math-6-2')")
        page.wait_for_timeout(2500)

        math2_state = page.evaluate("""() => ({
            lessonId: window.currentLoadedLessonId,
            lessonTitle: document.getElementById('current-lesson-title')?.textContent,
            ytDisplay: document.getElementById('sdc-youtube-iframe')?.style.display,
            ytSrc: document.getElementById('sdc-youtube-iframe')?.src,
            tutorBadge: document.getElementById('tutor-active-lesson-badge')?.textContent
        })""")
        print(f"State After Selecting Math Lesson 2:\n  Lesson: {math2_state['lessonTitle']} (ID: {math2_state['lessonId']})\n  YT Display: {math2_state['ytDisplay']}\n  YT Src: {math2_state['ytSrc']}\n  Tutor Badge: {math2_state['tutorBadge']}")

        screenshot2 = "C:/Users/maste/.gemini/antigravity/brain/9fca4546-0f4b-4909-a8ef-6687dffc6ab3/playwright_math_flow_lesson2.png"
        page.screenshot(path=screenshot2)
        print("Saved screenshot 2 to:", screenshot2)

        # 5. Return to Math Lesson 1 and test AI Tutor
        print("\n5. Returning to Math Lesson 1 (Sets) and testing AI Tutor...")
        page.evaluate("() => selectLesson('lesson-math-6-1')")
        page.wait_for_timeout(1500)

        # Test single word "سيٽ" (Sets) from Screenshot 9
        print("Asking AI Tutor: 'سيٽ'...")
        page.fill("#tutor-question-input", "سيٽ")
        page.click("#btn-tutor-send")
        page.wait_for_timeout(4000)

        tutor_answer1 = page.evaluate("""() => {
            const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble .bubble-text'));
            return bubbles.length ? bubbles[bubbles.length - 1].textContent.trim().replace(/\\s+/g, ' ') : 'NO_RESPONSE';
        }""")
        print(f"Tutor Response to 'سيٽ':\n  {tutor_answer1[:160]}...")

        # Test "سيٽ جا ڪيترا قسم ۽ ڪهڙا ڪهڙا" from Screenshot 7 & 8
        print("\nAsking AI Tutor: 'سيٽ جا ڪيترا قسم ۽ ڪهڙا ڪهڙا'...")
        page.fill("#tutor-question-input", "سيٽ جا ڪيترا قسم ۽ ڪهڙا ڪهڙا")
        page.click("#btn-tutor-send")
        page.wait_for_timeout(4000)

        tutor_answer2 = page.evaluate("""() => {
            const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble .bubble-text'));
            return bubbles.length ? bubbles[bubbles.length - 1].textContent.trim().replace(/\\s+/g, ' ') : 'NO_RESPONSE';
        }""")
        print(f"Tutor Response to 'سيٽ جا ڪيترا قسم ۽ ڪهڙا ڪهڙا':\n  {tutor_answer2[:160]}...")

        # Capture AI Tutor screenshot
        screenshot3 = "C:/Users/maste/.gemini/antigravity/brain/9fca4546-0f4b-4909-a8ef-6687dffc6ab3/playwright_math_flow_tutor.png"
        page.screenshot(path=screenshot3)
        print("Saved screenshot 3 to:", screenshot3)

        # 6. Test Lesson Quiz Modal for Math Sets
        print("\n6. Opening Lesson Quiz for Math Sets...")
        page.evaluate("() => openAssessmentForCurrentLesson()")
        page.wait_for_timeout(1500)

        quiz_modal_visible = page.evaluate("() => document.getElementById('sdc-assessment-modal')?.style.display !== 'none'")
        print("Quiz modal visible:", quiz_modal_visible)

        # Start Quiz
        print("Clicking Start Quiz button...")
        page.evaluate("() => startGeneratedQuiz()")
        page.wait_for_timeout(3000)

        quiz_runner_state = page.evaluate("""() => ({
            questionCount: QuizState.questions?.length,
            currentQuestion: QuizState.questions?.[0]?.text_sindhi,
            activeSessionId: QuizState.activeSessionId,
            mode: QuizState.mode
        })""")
        print(f"Quiz Runner State:\n  Session: {quiz_runner_state['activeSessionId']}\n  Mode: {quiz_runner_state['mode']}\n  Count: {quiz_runner_state['questionCount']}\n  Q1: {quiz_runner_state['currentQuestion']}")

        # Answer Question 1
        print("Submitting answer for Question 1 (option 0)...")
        page.evaluate("() => onSelectOption(0)")
        page.wait_for_timeout(2000)

        feedback_text = page.evaluate("() => document.getElementById('runner-instant-feedback')?.textContent?.trim()?.replace(/\\s+/g, ' ')")
        print(f"Instant Feedback Result:\n  {feedback_text}")

        screenshot4 = "C:/Users/maste/.gemini/antigravity/brain/9fca4546-0f4b-4909-a8ef-6687dffc6ab3/playwright_math_quiz_flow.png"
        page.screenshot(path=screenshot4)
        print("Saved screenshot 4 to:", screenshot4)

        print("\n--- BROWSER CONSOLE LOGS ---")
        for log in console_logs:
            if "ERROR" in log or "failed" in log or "warning" in log:
                print("  ", log)

        browser.close()

if __name__ == '__main__':
    run()
