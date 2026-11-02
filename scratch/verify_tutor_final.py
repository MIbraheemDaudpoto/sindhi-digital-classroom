import time, sys, os
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

ARTIFACT_DIR = r"C:\Users\maste\.gemini\antigravity\brain\9fca4546-0f4b-4909-a8ef-6687dffc6ab3"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto("http://127.0.0.1:8000/login")
        page.wait_for_timeout(1000)

        page.fill("#student-identifier", "STU-101")
        page.fill("#student-pin", "1234")
        page.click("#btn-submit-student")
        page.wait_for_timeout(2000)

        page.goto("http://127.0.0.1:8000/app/learn")
        page.wait_for_timeout(2000)

        page.evaluate("() => sosChooseSubject('Math')")
        page.wait_for_timeout(1500)

        page.evaluate("() => selectLesson('lesson-math-6-1')")
        page.wait_for_timeout(1500)

        print("Submitting question: 'سيٽ جي معني ڇا آهي؟'...")
        page.fill("#tutor-question-input", "سيٽ جي معني ڇا آهي؟")
        page.click("#btn-tutor-send")

        # Wait for the tutor answer bubble to arrive and settle
        for _ in range(12):
            page.wait_for_timeout(2000)
            text = page.evaluate("""() => {
                const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble .bubble-text'));
                return bubbles.length ? bubbles[bubbles.length - 1].textContent.trim() : '';
            }""")
            if text and "تيار ٿي رهيو آهي" not in text:
                print("Answer arrived!")
                break
            print("Still waiting for answer...")

        res = page.evaluate("""() => {
            const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble'));
            const last = bubbles[bubbles.length - 1];
            return {
                text: last ? last.querySelector('.bubble-text')?.textContent.trim() : null,
                citation: last ? last.querySelector('.tutor-citation')?.textContent.trim() : null,
                activeBadge: document.getElementById('tutor-active-lesson-badge')?.textContent
            };
        }""")
        print("Final Result:")
        print("  Active Badge:", res.get("activeBadge"))
        print("  Answer:", res.get("text"))
        print("  Citation:", res.get("citation"))

        screenshot_path = os.path.join(ARTIFACT_DIR, "playwright_verified_rag_tutor_final.png")
        page.screenshot(path=screenshot_path)
        print("Saved final screenshot to:", screenshot_path)
        browser.close()

if __name__ == '__main__':
    run()

