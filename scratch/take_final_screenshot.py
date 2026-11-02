import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\maste\.gemini\antigravity\brain\9fca4546-0f4b-4909-a8ef-6687dffc6ab3"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 850})
    page.goto('http://127.0.0.1:8000/login', wait_until='domcontentloaded')
    page.wait_for_timeout(1000)
    page.fill('#student-identifier', 'STU-101')
    page.fill('#student-pin', '1234')
    page.click('#btn-submit-student')
    page.wait_for_timeout(2000)
    page.goto('http://127.0.0.1:8000/app/learn', wait_until='domcontentloaded')
    page.wait_for_timeout(2000)
    page.evaluate("() => { if (typeof sosChooseSubject === 'function') sosChooseSubject('Math'); }")
    page.wait_for_timeout(1000)
    page.evaluate("() => { if (typeof selectLesson === 'function') selectLesson('lesson-math-6-1'); }")
    page.wait_for_timeout(1000)
    
    q = 'خالي سيٽ (Null Set) ڇا کي چئجي ٿو ۽ ان جي نشاني ڇا آهي؟'
    page.fill('#tutor-question-input', q)
    page.click('#btn-tutor-send')
    page.wait_for_timeout(3500)
    
    screenshot_path = os.path.join(ARTIFACT_DIR, "playwright_verified_rag_tutor_screenshot.png")
    page.screenshot(path=screenshot_path)
    print("Screenshot successfully saved to:", screenshot_path)
    browser.close()

