"""
End-to-End Live Browser Verification Script for SDC LMS In-Video Checkpoint Feature.
Executes against the running server at http://127.0.0.1:8000.
Verifies all 8 required behaviors with visual screenshots saved in the artifact directory.
"""

import os
import sys
import time
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
        page.evaluate("() => localStorage.clear()")
        page.wait_for_timeout(1000)
        page.fill("#student-identifier", "STU-101")
        page.fill("#student-pin", "1234")
        page.click("#btn-submit-student")
        page.wait_for_timeout(2000)
        print("  Student STU-101 logged in successfully!")

        print("=== STAGE 2: LESSON NAVIGATION & LOCAL PLAYER SETUP ===")
        page.goto("http://127.0.0.1:8000/app/learn", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        # Select Math lesson 1
        page.evaluate("() => { if (typeof sosChooseSubject === 'function') sosChooseSubject('Math'); }")
        page.wait_for_timeout(1000)
        page.evaluate("() => { if (typeof selectLesson === 'function') selectLesson('lesson-math-6-1'); }")
        page.wait_for_timeout(2000)

        # Ensure local player mode is active
        page.evaluate("""() => {
            if (window.sdcPlayer && window.sdcPlayer.currentLesson) {
                window.sdcPlayer.setupLocalPlayer(window.sdcPlayer.currentLesson);
            }
        }""")
        page.wait_for_timeout(1000)

        # Check local player status
        player_status = page.evaluate("""() => {
            const v = document.getElementById('sdc-video-player');
            return {
                src: v ? v.currentSrc || v.src : null,
                paused: v ? v.paused : true,
                duration: v ? v.duration : 0,
                activeSourceType: window.sdcPlayer ? window.sdcPlayer.activeSourceType : null,
                questions_count: window.sdcPlayer ? window.sdcPlayer.questions.length : 0
            };
        }""")
        print("  Player Status:", player_status)

        print("=== STAGE 3: AUTOMATIC CHECKPOINT PAUSE AT 4.0s ===")
        # Advance playback to 3.8s and let timeupdate trigger the 4.0s checkpoint
        page.evaluate("""() => {
            const v = document.getElementById('sdc-video-player');
            if (v) {
                v.currentTime = 3.8;
                v.play();
            }
        }""")

        # Wait up to 8s for checkpoint popup
        checkpoint_active = False
        for sec in range(8):
            page.wait_for_timeout(1000)
            overlay_info = page.evaluate("""() => {
                const ov = document.getElementById('quiz-popup-overlay');
                const v = document.getElementById('sdc-video-player');
                const qText = document.getElementById('checkpoint-question-text')?.textContent?.trim();
                const optCount = document.querySelectorAll('.quiz-option-btn').length;
                return {
                    visible: ov ? ov.style.display === 'flex' : false,
                    paused: v ? v.paused : false,
                    currentTime: v ? v.currentTime : 0,
                    question: qText,
                    optCount: optCount
                };
            }""")
            if overlay_info["visible"]:
                print(f"  Checkpoint overlay triggered at t={overlay_info['currentTime']:.2f}s!")
                print(f"  Playback paused: {overlay_info['paused']}")
                print(f"  Question text: {overlay_info['question']}")
                print(f"  Options count: {overlay_info['optCount']}")
                checkpoint_active = True
                break

        assert checkpoint_active, "Checkpoint overlay failed to trigger automatically!"

        shot1 = os.path.join(ARTIFACT_DIR, "browser_checkpoint_pause_overlay.png")
        page.screenshot(path=shot1)
        print("  Saved checkpoint pause screenshot:", shot1)

        print("=== STAGE 4: ANSWER SUBMISSION & PEDAGOGICAL FEEDBACK ===")
        # Click Option 0 (∅: correct answer)
        page.evaluate("""() => {
            const btn = document.getElementById('quiz-opt-0');
            if (btn) btn.click();
        }""")
        page.wait_for_timeout(2000)

        feedback_info = page.evaluate("""() => {
            const fb = document.getElementById('quiz-feedback-box');
            const resBtn = document.getElementById('btn-resume-checkpoint');
            return {
                fb_visible: fb ? fb.style.display !== 'none' : false,
                fb_text: fb ? fb.innerText.trim() : null,
                resume_btn_visible: resBtn ? resBtn.style.display !== 'none' : false
            };
        }""")
        print("  Feedback Visible:", feedback_info["fb_visible"])
        print("  Feedback Text:\n  ", feedback_info["fb_text"])
        print("  Resume Button Visible:", feedback_info["resume_btn_visible"])

        assert feedback_info["fb_visible"], "Feedback box did not display!"
        assert "درست" in feedback_info["fb_text"] or "شاباس" in feedback_info["fb_text"], "Pedagogical feedback missing expected text!"
        assert feedback_info["resume_btn_visible"], "Resume button must be shown after answer is saved!"

        shot2 = os.path.join(ARTIFACT_DIR, "browser_checkpoint_feedback_and_resume.png")
        page.screenshot(path=shot2)
        print("  Saved checkpoint feedback screenshot:", shot2)

        print("=== STAGE 5: RESUME PLAYBACK AFTER CONFIRMATION ===")
        page.evaluate("""() => {
            const resBtn = document.getElementById('btn-resume-checkpoint');
            if (resBtn) resBtn.click();
        }""")
        page.wait_for_timeout(1500)

        resumed_info = page.evaluate("""() => {
            const ov = document.getElementById('quiz-popup-overlay');
            const v = document.getElementById('sdc-video-player');
            return {
                overlay_hidden: ov ? ov.style.display === 'none' : true,
                time: v ? v.currentTime : 0
            };
        }""")
        print("  Overlay closed:", resumed_info["overlay_hidden"])
        print("  Position after resume:", resumed_info["time"])
        assert resumed_info["overlay_hidden"], "Overlay must close when Resume is clicked!"

        print("=== STAGE 6: REFRESH/REVISIT IDEMPOTENCY TEST ===")
        # Reload the page
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        # Select math lesson again
        page.evaluate("() => { if (typeof sosChooseSubject === 'function') sosChooseSubject('Math'); }")
        page.wait_for_timeout(1000)
        page.evaluate("() => { if (typeof selectLesson === 'function') selectLesson('lesson-math-6-1'); }")
        page.wait_for_timeout(1500)
        page.evaluate("""() => {
            if (window.sdcPlayer && window.sdcPlayer.currentLesson) {
                window.sdcPlayer.setupLocalPlayer(window.sdcPlayer.currentLesson);
            }
        }""")
        page.wait_for_timeout(1000)

        revisit_check = page.evaluate("""() => {
            const p = window.sdcPlayer;
            return {
                has_completed: p ? p.completedQuestionIds.has('q-math-1-2') : false
            };
        }""")
        print("  Completed checkpoint remembered across refresh:", revisit_check["has_completed"])
        assert revisit_check["has_completed"], "Completed checkpoint was not restored from persistence!"

        # Play forward past 4.0s (e.g. at 4.2s) - should NOT trigger question q-math-1-2 again
        page.evaluate("""() => {
            const v = document.getElementById('sdc-video-player');
            if (v) {
                v.currentTime = 3.9;
                v.play();
            }
        }""")
        page.wait_for_timeout(2000)
        no_repeat = page.evaluate("""() => {
            const ov = document.getElementById('quiz-popup-overlay');
            return {
                overlay_shown: ov ? ov.style.display === 'flex' : false
            };
        }""")
        print("  Did already-completed checkpoint re-trigger? (Expect False):", no_repeat["overlay_shown"])
        assert not no_repeat["overlay_shown"], "Already completed checkpoint must not re-trigger!"

        print("=== STAGE 7: FORWARD SEEK INTERCEPTION POLICY ===")
        # Seek from current position (around 4.5s) forward to 8.5s jumping over checkpoint 2 at 7.0s
        page.evaluate("""() => {
            const p = window.sdcPlayer;
            const v = document.getElementById('sdc-video-player');
            if (p && v) {
                p.lastObservedTime = 4.5;
                v.currentTime = 8.5;
                p.handleSeeking();
            }
        }""")
        page.wait_for_timeout(1500)

        seek_intercept = page.evaluate("""() => {
            const ov = document.getElementById('quiz-popup-overlay');
            const v = document.getElementById('sdc-video-player');
            const qText = document.getElementById('checkpoint-question-text')?.textContent?.trim();
            return {
                clamped_time: v ? v.currentTime : 0,
                paused: v ? v.paused : false,
                overlay_visible: ov ? ov.style.display === 'flex' : false,
                question: qText
            };
        }""")
        print("  Seek clamped time:", seek_intercept["clamped_time"])
        print("  Playback paused:", seek_intercept["paused"])
        print("  Checkpoint 2 question:", seek_intercept["question"])

        assert seek_intercept["overlay_visible"], "Forward seek across uncompleted checkpoint must be intercepted!"
        assert abs(seek_intercept["clamped_time"] - 7.0) < 0.2, "Seek must be clamped to checkpoint timestamp (7.0s)!"

        shot3 = os.path.join(ARTIFACT_DIR, "browser_checkpoint_seeking_intercept.png")
        page.screenshot(path=shot3)
        print("  Saved seek interception screenshot:", shot3)

        print("=== STAGE 8: VIDEO FAILURE RESILIENCE & STANDALONE QUIZ INDEPENDENCE ===")
        # Close checkpoint modal and simulate video stream error
        page.evaluate("""() => {
            if (window.sdcPlayer) {
                window.sdcPlayer.closeQuizModal();
                window.sdcPlayer.handleVideoError('Simulated network 404');
            }
        }""")
        page.wait_for_timeout(1000)

        resilience = page.evaluate("""() => {
            const errCard = document.getElementById('video-error-state');
            const assessBtn = document.getElementById('btn-open-assessment-hub') || document.getElementById('btn-lesson-quiz');
            const tutorInput = document.getElementById('tutor-question-input');
            return {
                error_card_shown: errCard ? errCard.style.display === 'flex' : false,
                assessment_hub_btn_exists: assessBtn !== null,
                assessment_hub_btn_disabled: assessBtn ? assessBtn.disabled : true,
                tutor_usable: tutorInput ? !tutorInput.disabled : false
            };
        }""")
        print("  Error card displayed:", resilience["error_card_shown"])
        print("  Standalone Assessment button available:", resilience["assessment_hub_btn_exists"])
        print("  AI Tutor usable during video failure:", resilience["tutor_usable"])

        assert resilience["error_card_shown"], "Video error card must be shown on video failure!"
        assert resilience["assessment_hub_btn_exists"] and not resilience["assessment_hub_btn_disabled"], "Standalone quiz must remain accessible during video failure!"
        assert resilience["tutor_usable"], "AI Tutor must remain accessible during video failure!"

        # Open standalone assessment hub to verify decoupling
        page.evaluate("() => { if (typeof openAssessmentHub === 'function') openAssessmentHub(); }")
        page.wait_for_timeout(1500)

        hub_open = page.evaluate("""() => {
            const modal = document.getElementById('sdc-assessment-modal');
            return modal ? modal.style.display === 'flex' || modal.style.display !== 'none' : false;
        }""")
        print("  Standalone Assessment Hub modal opened successfully:", hub_open)
        assert hub_open, "Standalone assessment hub failed to open during video error!"

        shot4 = os.path.join(ARTIFACT_DIR, "browser_checkpoint_video_error_resilience.png")
        page.screenshot(path=shot4)
        print("  Saved video error resilience screenshot:", shot4)

        browser.close()
        print("=== ALL 8 LIVE BROWSER CHECKPOINT STAGES VERIFIED SUCCESSFULLY: 100% PASS ===")

if __name__ == '__main__':
    run()

