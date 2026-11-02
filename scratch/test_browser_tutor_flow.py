import time, sys, os
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

ARTIFACT_DIR = r"C:\Users\maste\.gemini\antigravity\brain\9fca4546-0f4b-4909-a8ef-6687dffc6ab3"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        page = context.new_page()

        print("1. Opening login page...")
        page.goto("http://127.0.0.1:8000/login", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        print("2. Logging in as student STU-101...")
        page.fill("#student-identifier", "STU-101")
        page.fill("#student-pin", "1234")
        page.click("#btn-submit-student")
        page.wait_for_timeout(2000)

        print("3. Navigating to /app/learn...")
        page.goto("http://127.0.0.1:8000/app/learn", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Select Math and Sets lesson
        print("4. Selecting Math and Lesson 1 (Sets)...")
        page.evaluate("() => { if (typeof sosChooseSubject === 'function') sosChooseSubject('Math'); }")
        page.wait_for_timeout(1500)
        page.evaluate("() => { if (typeof selectLesson === 'function') selectLesson('lesson-math-6-1'); }")
        page.wait_for_timeout(1500)

        # First question from user screenshot
        q1 = "خالي سيٽ (Null Set) ڇا کي چئجي ٿو ۽ ان جي نشاني ڇا آهي؟"
        print(f"5. Asking Question 1: '{q1}'...")
        page.fill("#tutor-question-input", q1)
        page.click("#btn-tutor-send")

        # Wait for answer 1 (up to 40s)
        for sec in range(40):
            page.wait_for_timeout(1000)
            text = page.evaluate("""() => {
                const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble .bubble-text'));
                return bubbles.length ? bubbles[bubbles.length - 1].textContent.trim() : '';
            }""")
            if text and "تيار ٿي رهيو آهي" not in text and "سمجھي رهيو آهيان" not in text and "ڳولي رهيو آهيان" not in text:
                print(f"   Answer 1 arrived in ~{sec+1}s!")
                break
            if (sec + 1) % 5 == 0:
                print(f"   Waiting for answer 1 ({sec+1}s)... {text[:50] if text else ''}")

        res1 = page.evaluate("""() => {
            const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble'));
            const last = bubbles[bubbles.length - 1];
            return {
                text: last ? last.querySelector('.bubble-text')?.textContent.trim() : null,
                citation: last ? last.querySelector('.tutor-citation')?.textContent.trim() : null
            };
        }""")
        print("Question 1 Result:")
        print("  Answer:", res1.get("text"))
        print("  Citation:", res1.get("citation"))

        # Wait for input to be re-enabled
        page.wait_for_selector("#tutor-question-input:not([disabled])", timeout=10000)

        # Second question from user screenshot textarea
        q2 = "سيٽ جي تعريف ۽ ان جا بنيادي تصور سمجهايو."
        print(f"6. Asking Question 2: '{q2}'...")
        page.fill("#tutor-question-input", q2)
        page.click("#btn-tutor-send")

        # Wait for answer 2 (up to 40s)
        for sec in range(40):
            page.wait_for_timeout(1000)
            text = page.evaluate("""() => {
                const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble .bubble-text'));
                return bubbles.length ? bubbles[bubbles.length - 1].textContent.trim() : '';
            }""")
            if text and "تيار ٿي رهيو آهي" not in text and "سمجھي رهيو آهيان" not in text and "ڳولي رهيو آهيان" not in text:
                print(f"   Answer 2 arrived in ~{sec+1}s!")
                break
            if (sec + 1) % 5 == 0:
                print(f"   Waiting for answer 2 ({sec+1}s)... {text[:50] if text else ''}")

        res2 = page.evaluate("""() => {
            const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble'));
            const last = bubbles[bubbles.length - 1];
            return {
                text: last ? last.querySelector('.bubble-text')?.textContent.trim() : null,
                citation: last ? last.querySelector('.tutor-citation')?.textContent.trim() : null
            };
        }""")
        print("Question 2 Result:")
        print("  Answer:", res2.get("text"))
        print("  Citation:", res2.get("citation"))

        screenshot_path = os.path.join(ARTIFACT_DIR, "playwright_live_browser_tutor_answers.png")
        page.screenshot(path=screenshot_path)
        print("7. Saved full browser screenshot to:", screenshot_path)

        browser.close()

if __name__ == '__main__':
    run()
