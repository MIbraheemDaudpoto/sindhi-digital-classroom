import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

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
    page.wait_for_timeout(3000)
    
    res = page.evaluate('''() => {
        const bubbles = Array.from(document.querySelectorAll('.chat-bubble.tutor-bubble'));
        const last = bubbles[bubbles.length - 1];
        return {
            answer: last ? last.querySelector('.bubble-text')?.textContent.trim() : null,
            citation: last ? last.querySelector('.tutor-citation-box')?.innerText?.trim() : null
        };
    }''')
    print('Answer:', res.get('answer'))
    print('Citation Box:\n', res.get('citation'))
    browser.close()

