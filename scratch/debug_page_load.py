import time, sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

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
        page.wait_for_timeout(3000)

        # Inspect JS variables
        state = page.evaluate("""() => {
            return {
                currentUser: window.currentUser,
                currentLoadedLessonId: window.currentLoadedLessonId,
                currentLoadedLesson: window.currentLoadedLesson,
                activeSubjectFilter: window.activeSubjectFilter,
                activeClassLevel: typeof activeClassLevel !== 'undefined' ? activeClassLevel : null,
                allLoadedCourses: typeof allLoadedCourses !== 'undefined' ? allLoadedCourses.map(c => ({ id: c.id, subject: c.subject, count: c.lessons?.length })) : null,
                ytDisplay: document.getElementById('sdc-youtube-iframe')?.style.display,
                ytSrc: document.getElementById('sdc-youtube-iframe')?.src,
                vidDisplay: document.getElementById('sdc-video-player')?.style.display,
                vidSrc: document.getElementById('sdc-video-player')?.currentSrc,
                lessonTitleText: document.getElementById('current-lesson-title')?.textContent,
                localStorageLastLesson: localStorage.getItem('sdc_last_lesson_id'),
                localStorageUser: localStorage.getItem('sdc_current_user') ? 'SET' : 'NULL'
            };
        }""")
        print("Page state at /app/learn:")
        for k, v in state.items():
            print(f"  {k}: {v}")

        print("\nConsole logs on /app/learn:")
        for l in console_logs:
            print(" ", l)

        browser.close()

if __name__ == '__main__':
    run()

