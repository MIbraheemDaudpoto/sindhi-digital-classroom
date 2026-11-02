import time, sys, os
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

ARTIFACT_DIR = r"C:\Users\maste\.gemini\antigravity\brain\9fca4546-0f4b-4909-a8ef-6687dffc6ab3"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        print("1. Navigating to login page...")
        page.goto("http://127.0.0.1:8000/login")
        page.wait_for_timeout(1000)

        # Fill student credentials
        page.fill("#student-identifier", "STU-101")
        page.fill("#student-pin", "1234")
        page.click("#btn-submit-student")
        page.wait_for_timeout(2000)

        print("2. Navigating to /app/learn...")
        page.goto("http://127.0.0.1:8000/app/learn")
        page.wait_for_timeout(2500)

        # 3. Switch to Mathematics
        print("3. Switching to Mathematics via sosChooseSubject('Math')...")
        page.evaluate("() => sosChooseSubject('Math')")
        page.wait_for_timeout(2000)

        # 4. Select Math Lesson 1 (Sets)
        print("4. Selecting Math Lesson 1 (Sets)...")
        page.evaluate("() => selectLesson('lesson-math-6-1')")
        page.wait_for_timeout(2000)

        # 5. Open AI Tutor and submit query
        print("5. Submitting natural Sindhi question to AI Tutor: 'سيٽ جي معني ڇا آهي؟'...")
        page.fill("#tutor-question-input", "سيٽ جي معني ڇا آهي؟")
        page.click("#btn-tutor-send")
        page.wait_for_timeout(5000)

        # Extract answer and citation
        tutor_data = page.evaluate("""() => {
            const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble'));
            const last = bubbles[bubbles.length - 1];
            return {
                text: last ? last.querySelector('.bubble-text')?.textContent.trim() : null,
                citation: last ? last.querySelector('.tutor-citation')?.textContent.trim() : null,
                activeBadge: document.getElementById('tutor-active-lesson-badge')?.textContent
            };
        }""")
        print("AI Tutor Verification Result:")
        print("  Active Badge:", tutor_data.get("activeBadge"))
        print("  Answer Text:", tutor_data.get("text"))
        print("  Citation:", tutor_data.get("citation"))

        # Save screenshot artifact
        screenshot_path = os.path.join(ARTIFACT_DIR, "playwright_verified_rag_tutor.png")
        page.screenshot(path=screenshot_path)
        print("Screenshot saved to:", screenshot_path)

        browser.close()

if __name__ == '__main__':
    run()
