"""
Frontend Assessment Integration Patch for SDC
Patches static/app.html and static/js/app.js
"""

import re
import sys

def patch_app_html():
    with open('static/app.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add btn-lesson-quiz next to btn-jump-to-tutor
    quiz_btn_html = """                  <button id="btn-lesson-quiz" class="btn-ctrl active" onclick="openAssessmentForCurrentLesson()" style="background: var(--accent-emerald, #059669); color: #fff; border: none; font-weight: 700;" title="هن سبق جو نئون ڪوئز تيار ڪريو">
                    <svg class="sdc-icon sdc-icon-xs" style="color: #fff;" aria-hidden="true"><use href="#icon-sparkles"></use></svg>
                    <span>📝 سبق جو ڪوئز (Lesson Quiz)</span>
                  </button>
"""
    if 'id="btn-lesson-quiz"' not in content:
        target = '<button id="btn-jump-to-tutor"'
        # Insert after the closing tag of btn-jump-to-tutor
        btn_pattern = r'(<button id="btn-jump-to-tutor".*?</button>)'
        match = re.search(btn_pattern, content, re.DOTALL)
        if match:
            content = content[:match.end()] + "\n" + quiz_btn_html + content[match.end():]
            print("Added btn-lesson-quiz in app.html")
        else:
            print("ERROR: Could not find btn-jump-to-tutor in app.html")

    # 2. Upgrade video-error-state card
    old_card_pattern = r'(<div id="video-error-state" class="video-error-card".*?</div>\s*</div>)'
    # Find exact error card
    card_regex = r'<div id="video-error-state" class="video-error-card"[^>]*>.*?</div>'
    match = re.search(card_regex, content, re.DOTALL)
    if match:
        new_card = """<div id="video-error-state" class="video-error-card" style="display: none;">
                  <h3 id="video-error-title" style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                    <svg class="sdc-icon sdc-icon-sm" style="color: var(--accent-rose);" aria-hidden="true"><use href="#icon-help"></use></svg>
                    <span>وڊيو فوري طور تي دستياب ناهي (تعليم جاري آهي)</span>
                  </h3>
                  <p id="video-error-desc">وڊيو فوري طور تي دستياب ناهي. توهان درسي نوٽس پڙهي سگهو ٿا يا سڌو سنئون امتحاني ڪوئز شروع ڪري سگهو ٿا.</p>
                  <div style="display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; justify-content: center;">
                    <button class="btn-retry" onclick="openAssessmentForCurrentLesson()" style="background: var(--accent-emerald, #059669); color: #fff; display: inline-flex; align-items: center; gap: 6px; font-weight: 700; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer;">
                      <svg class="sdc-icon sdc-icon-xs" style="color: #fff;" aria-hidden="true"><use href="#icon-sparkles"></use></svg>
                      <span>📝 سبق جو ڪوئز شروع ڪريو (Start Lesson Quiz)</span>
                    </button>
                    <button class="btn-retry" onclick="sdcPlayer.retryCurrentVideo()" style="display: inline-flex; align-items: center; gap: 6px; background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border-subtle); padding: 8px 14px; border-radius: 8px; cursor: pointer;">
                      <svg class="sdc-icon sdc-icon-xs" aria-hidden="true"><use href="#icon-refresh"></use></svg>
                      <span>ٻيهر ڪوشش (Retry)</span>
                    </button>
                  </div>
                </div>"""
        content = content[:match.start()] + new_card + content[match.end():]
        print("Upgraded video-error-state in app.html")

    # 3. Add btn-open-assessment-hub to player controls
    if 'id="btn-open-assessment-hub"' not in content:
        ctrl_pattern = r'(<button id="btn-audio-only".*?</button>)'
        match = re.search(ctrl_pattern, content, re.DOTALL)
        if match:
            hub_btn = """                  <button id="btn-open-assessment-hub" class="btn-ctrl" onclick="openAssessmentHub()" style="background: var(--accent-indigo, #4338ca); color: #fff; font-weight: 700; border: none;" title="ڪلاس ۽ مضمون وار امتحاني ڪوئز شروع ڪريو">
                    <svg class="sdc-icon sdc-icon-xs" style="color: #fff;" aria-hidden="true"><use href="#icon-sparkles"></use></svg>
                    <span>🎯 امتحاني مرڪز (Assessment Hub)</span>
                  </button>
"""
            content = content[:match.end()] + "\n" + hub_btn + content[match.end():]
            print("Added btn-open-assessment-hub in app.html")

    # 4. Add modal container before toast-container
    if 'id="sdc-assessment-modal"' not in content:
        modal_html = """  <!-- Real-Time Curriculum Assessment Hub Modal -->
  <div id="sdc-assessment-modal" style="display: none;">
    <div class="assessment-modal-dialog">
      <div id="assessment-modal-body" class="assessment-modal-body">
        <!-- Rendered dynamically by quiz.js -->
      </div>
    </div>
  </div>

"""
        target = '<div id="toast-container"'
        pos = content.find(target)
        if pos != -1:
            content = content[:pos] + modal_html + content[pos:]
            print("Added sdc-assessment-modal in app.html")

    # 5. Add script tag for quiz.js
    if '/static/js/quiz.js' not in content:
        app_js_tag = '<script src="/static/js/app.js"></script>'
        pos = content.find(app_js_tag)
        if pos != -1:
            end_pos = pos + len(app_js_tag)
            content = content[:end_pos] + '\n  <script src="/static/js/quiz.js"></script>' + content[end_pos:]
            print("Added quiz.js script tag in app.html")

    with open('static/app.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully updated static/app.html")

def patch_app_js():
    with open('static/js/app.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add assessment hub tab in renderNavTabs
    if 'pane-assessment-hub-tab' not in content:
        student_tabs_marker = "if (role === 'STUDENT') {"
        pos = content.find(student_tabs_marker)
        if pos != -1:
            bracket_pos = content.find('tabs = [', pos)
            first_entry_pos = content.find('{ id: \'pane-learn\'', bracket_pos)
            if first_entry_pos != -1:
                end_entry = content.find('},', first_entry_pos)
                if end_entry != -1:
                    insert_pos = end_entry + 2
                    tab_entry = """
      { id: 'pane-assessment-hub-tab', path: '#assessment', icon: 'sparkles', label: 'امتحاني مرڪز (AI Quizzes)' },"""
                    content = content[:insert_pos] + tab_entry + content[insert_pos:]
                    print("Added pane-assessment-hub-tab to student tabs")

    # 2. Add click interception for pane-assessment-hub-tab
    if "targetId === 'pane-assessment-hub-tab'" not in content:
        btn_click_marker = "btn.addEventListener('click', () => {"
        pos = content.find(btn_click_marker)
        if pos != -1:
            insert_pos = pos + len(btn_click_marker)
            interception = """
      const clickedTab = btn.getAttribute('data-tab');
      if (clickedTab === 'pane-assessment-hub-tab') {
        if (typeof window.openAssessmentHub === 'function') {
          window.openAssessmentHub();
        }
        return;
      }"""
            content = content[:insert_pos] + interception + content[insert_pos:]
            print("Added click interception for pane-assessment-hub-tab")

    with open('static/js/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully updated static/js/app.js")

if __name__ == '__main__':
    patch_app_html()
    patch_app_js()

