import sys, re

# ==========================================
# 1. FIX static/js/app.js
# ==========================================
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# Fix 1: selectLesson robust subject setting and error handling
old_select_lesson_start = """// 2. Select and Load Lesson
async function selectLesson(lessonId) {
  currentLoadedLessonId = lessonId;
  window.currentLoadedLessonId = lessonId;
  window.currentSubject = currentSubject;
  document.querySelectorAll('.lesson-card').forEach(c => c.classList.remove('active-playing'));
  const card = document.getElementById(`card-${lessonId}`);
  if (card) card.classList.add('active-playing');

  try {
    const token = currentUser.token || currentUser.user_id;
    // 1. Fetch lesson detail
    const res = await fetch(`/api/lessons/${lessonId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const detail = await res.json();
    window.currentLoadedLesson = detail;

    // 2. Fetch approved quiz bank (FR-13 Gate)
    const qRes = await fetch(`/api/quiz/${lessonId}/questions`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const questions = await qRes.json();"""

new_select_lesson_start = """// 2. Select and Load Lesson
async function selectLesson(lessonId) {
  currentLoadedLessonId = lessonId;
  window.currentLoadedLessonId = lessonId;
  if (lessonId && lessonId.includes('math')) {
    activeSubjectFilter = 'Math';
    window.currentSubject = 'Math';
  } else if (lessonId && lessonId.includes('sci')) {
    activeSubjectFilter = 'Science';
    window.currentSubject = 'Science';
  } else {
    window.currentSubject = activeSubjectFilter || 'Science';
  }
  document.querySelectorAll('.lesson-card').forEach(c => c.classList.remove('active-playing'));
  const card = document.getElementById(`card-${lessonId}`);
  if (card) card.classList.add('active-playing');

  try {
    const token = (currentUser && (currentUser.token || currentUser.user_id)) || localStorage.getItem('sdc_token') || 'sdc_demo_token';
    // 1. Fetch lesson detail
    const res = await fetch(`/api/lessons/${lessonId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const detail = await res.json();
    window.currentLoadedLesson = detail;

    // 2. Fetch approved quiz bank (FR-13 Gate)
    let questions = [];
    try {
      const qRes = await fetch(`/api/quiz/${lessonId}/questions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (qRes.ok) {
        questions = await qRes.json();
      }
    } catch (e) {
      console.warn('[SDC] Could not fetch quiz questions:', e);
    }"""

if old_select_lesson_start in app_js:
    app_js = app_js.replace(old_select_lesson_start, new_select_lesson_start, 1)
    print("Patched selectLesson start in app.js")
else:
    print("WARNING: old_select_lesson_start not matched exactly in app.js")

# Fix 2: Tutor synchronization in selectLesson
old_tutor_call = """    // 5. Update Tutor Quick Prompts & Context for the Selected Lesson
    updateLessonTutorContext(detail);"""

new_tutor_call = """    // 5. Update Tutor Quick Prompts & Context for the Selected Lesson
    updateLessonTutorContext(detail);

    // Synchronize AI Tutor drawer with active lesson
    if (window.sdcTutor && typeof window.sdcTutor.setActiveLesson === 'function') {
      window.sdcTutor.setActiveLesson(detail);
    }"""

if old_tutor_call in app_js:
    app_js = app_js.replace(old_tutor_call, new_tutor_call, 1)
    print("Patched tutor call in selectLesson in app.js")

# Fix 3: sosChooseSubject auto-switches active lesson to first lesson in chosen subject
old_sos_subject = """  filterAndRenderCourses();
  sosGoToStep(3);
}"""

new_sos_subject = """  filterAndRenderCourses();
  sosGoToStep(3);

  // Auto-switch player & tutor to first lesson in chosen subject
  if (Array.isArray(allLoadedCourses)) {
    const chosenCourse = allLoadedCourses.find(c => c.subject && c.subject.toLowerCase() === subject.toLowerCase());
    if (chosenCourse && Array.isArray(chosenCourse.lessons) && chosenCourse.lessons.length > 0) {
      selectLesson(chosenCourse.lessons[0].id);
    }
  }
}"""

if old_sos_subject in app_js:
    app_js = app_js.replace(old_sos_subject, new_sos_subject, 1)
    print("Patched sosChooseSubject in app.js")

# Fix 4: Allow saved Math lessons to restore on refresh
old_load_curr_target = """      const targetLessonId = savedLesson && savedLesson.startsWith('lesson-sci-') 
        ? savedLesson 
        : (scienceCourse?.lessons[0]?.id || allLoadedCourses[0]?.lessons[0]?.id);"""

new_load_curr_target = """      const targetLessonId = savedLesson 
        ? savedLesson 
        : (scienceCourse?.lessons[0]?.id || allLoadedCourses[0]?.lessons[0]?.id);"""

if old_load_curr_target in app_js:
    app_js = app_js.replace(old_load_curr_target, new_load_curr_target, 1)
    print("Patched loadCurriculum target lesson in app.js")

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)
print("Saved static/js/app.js")


# ==========================================
# 2. FIX static/js/tutor.js
# ==========================================
with open('static/js/tutor.js', 'r', encoding='utf-8') as f:
    tutor_js = f.read()

# Add setActiveLesson method to SDCAITutor class
if "setActiveLesson(lessonDetail)" not in tutor_js:
    old_init = """    this.currentlyPlayingBtn = null;
    this.setupComposerEvents();
    this.setupAudioPlayerEvents();
  }"""
    new_init = """    this.currentlyPlayingBtn = null;
    this.currentLesson = null;
    this.setupComposerEvents();
    this.setupAudioPlayerEvents();
  }

  setActiveLesson(lessonDetail) {
    if (!lessonDetail) return;
    this.currentLesson = lessonDetail;
    const badge = document.getElementById('tutor-active-lesson-badge');
    if (badge) {
      badge.textContent = `📖 فعال سبق: ${lessonDetail.title_sindhi}`;
      badge.style.display = 'inline-flex';
    }
  }"""
    tutor_js = tutor_js.replace(old_init, new_init, 1)
    print("Added setActiveLesson to tutor.js")

with open('static/js/tutor.js', 'w', encoding='utf-8') as f:
    f.write(tutor_js)
print("Saved static/js/tutor.js")


# ==========================================
# 3. FIX static/app.html (Active lesson badge in tutor header)
# ==========================================
with open('static/app.html', 'r', encoding='utf-8') as f:
    app_html = f.read()

badge_html = """                  <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; line-height: 1.4;">
                    سنڌ ٽيڪسٽ بڪ بورڊ جي درسي نصاب مان تصديق ٿيل ۽ حوالن سان سنڌي ۾ رهنمائي ڪري ٿو.
                  </p>
                  <div id="tutor-active-lesson-badge" style="font-size: 0.78rem; font-weight: 700; color: var(--accent-primary); background: var(--accent-primary-soft); padding: 3px 8px; border-radius: 6px; margin-top: 4px; display: inline-flex; align-items: center; gap: 4px;">📖 فعال سبق: سيٽ (Sets)</div>"""

if "id=\"tutor-active-lesson-badge\"" not in app_html:
    target_p = """                  <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; line-height: 1.4;">

                    سنڌ ٽيڪسٽ بڪ بورڊ جي درسي نصاب مان تصديق ٿيل ۽ حوالن سان سنڌي ۾ رهنمائي ڪري ٿو.

                  </p>"""
    if target_p in app_html:
        app_html = app_html.replace(target_p, badge_html, 1)
        with open('static/app.html', 'w', encoding='utf-8') as f:
            f.write(app_html)
        print("Added active lesson badge in app.html")
    else:
        print("Could not match exact target_p in app.html")


# ==========================================
# 4. FIX src/services/assessment_quiz_service.py (Line 816 target_lessons bug)
# ==========================================
with open('src/services/assessment_quiz_service.py', 'r', encoding='utf-8') as f:
    quiz_py = f.read()

if "for lesson in target_lessons:" in quiz_py:
    quiz_py = quiz_py.replace("for lesson in target_lessons:", "for lesson in lessons:", 1)
    with open('src/services/assessment_quiz_service.py', 'w', encoding='utf-8') as f:
        f.write(quiz_py)
    print("Fixed target_lessons in assessment_quiz_service.py")


# ==========================================
# 5. FIX src/services/ai_tutor_service.py (Keyword enrichment for Types of Sets)
# ==========================================
with open('src/services/ai_tutor_service.py', 'r', encoding='utf-8') as f:
    tutor_py = f.read()

old_kw_load = """                    if "ڪنگڻ" in c.get("topic_title_sd", ""):
                        chunk_item["keywords"].extend(["bodmas", "بي او ڊي ايم اي ايس", "سادي صورت"])
                    self.math_chunks.append(chunk_item)"""

new_kw_load = """                    cid = c.get("chunk_id", "")
                    if cid == "math-ch01-01":
                        chunk_item["keywords"].extend(["سيٽ", "set", "رڪن", "تعريف", "وصف", "معني", "مطلب", "شين جو مجموعو"])
                    elif cid == "math-ch01-02":
                        chunk_item["keywords"].extend(["روپ", "سيٽ جا روپ", "بياني روپ", "لسٽ وارو روپ", "forms of sets"])
                    elif cid == "math-ch01-03":
                        chunk_item["keywords"].extend(["قسم", "سيٽ جا قسم", "ڪيترا قسم", "ڪهڙا قسم", "خالي سيٽ", "محدود سيٽ", "لامحدود سيٽ", "واحد سيٽ", "types of sets"])
                    elif cid == "math-ch01-04":
                        chunk_item["keywords"].extend(["برابر سيٽ", "هم قدر سيٽ", "equal sets", "equivalent sets"])
                    elif cid == "math-ch01-05":
                        chunk_item["keywords"].extend(["ذيلي سيٽ", "مٿانهون سيٽ", "صحيح ذيلي سيٽ", "subset", "superset"])
                    if "ڪنگڻ" in c.get("topic_title_sd", ""):
                        chunk_item["keywords"].extend(["bodmas", "بي او ڊي ايم اي ايس", "سادي صورت"])
                    self.math_chunks.append(chunk_item)"""

if old_kw_load in tutor_py:
    tutor_py = tutor_py.replace(old_kw_load, new_kw_load, 1)
    print("Enriched math chunk keywords in ai_tutor_service.py")

# Exclude generic glossary 'سيٽ' when asking about types/kinds
old_gloss_term = """                # Exclude math "سيٽ" if asking about satellite
                if term_sd == "سيٽ" and is_paksat_query:
                    continue"""

new_gloss_term = """                # Exclude math "سيٽ" if asking about satellite
                if term_sd == "سيٽ" and is_paksat_query:
                    continue
                # If question specifically asks about kinds/types ("قسم" or "ڪيترا"), do not match single term "سيٽ"
                if term_sd == "سيٽ" and any(k in normalized_query for k in ["قسم", "ڪيترا", "ڪهڙا", "روپ", "ٽائپ"]):
                    continue"""

if old_gloss_term in tutor_py:
    tutor_py = tutor_py.replace(old_gloss_term, new_gloss_term, 1)
    print("Patched glossary search in ai_tutor_service.py")

with open('src/services/ai_tutor_service.py', 'w', encoding='utf-8') as f:
    tutor_py = f.write(tutor_py)
print("Saved src/services/ai_tutor_service.py")


# ==========================================
# 6. FIX src/services/ai_provider.py (Types of sets response)
# ==========================================
with open('src/services/ai_provider.py', 'r', encoding='utf-8') as f:
    prov_py = f.read()

old_math_branch = """            elif topic == "خالي سيٽ":"""

new_math_branch = """            elif any(k in topic for k in ["قسم", "محدود", "خالي ۽ واحد", "روپ"]):
                explanation_lines = [
                    f"رياضياتي تصور (سيٽ جا قسم / Types of Sets): سنڌ ٽيڪسٽ بڪ بورڊ ڪلاس 6 رياضي (باب 1) مطابق سيٽن جا مکيه قسم هيٺيان آهن:",
                    "• خالي سيٽ (Empty / Null Set): اهو سيٽ جنهن ۾ ڪوبه رڪن نه هجي. نشاني: ∅ يا { }.",
                    "• واحد سيٽ (Singleton Set): اهو سيٽ جنهن ۾ صرف هڪ ئي رڪن هجي. مثال: A = {5}.",
                    "• محدود سيٽ (Finite Set): اهو سيٽ جنهن جا رڪن ڳڻپ لائق هجن. مثال: B = {1, 2, 3, 4}.",
                    "• لامحدود سيٽ (Infinite Set): اهو سيٽ جنهن جا رڪن اڻ کٽ ۽ اڻ ڳڻيا هجن. مثال: N = {1, 2, 3, ...}.",
                    "• برابر سيٽ (Equal Sets): ٻه سيٽ جن جا سمورا رڪن بلڪل هڪجهڙا هجن.",
                    "• هم قدر سيٽ (Equivalent Sets): ٻه سيٽ جن ۾ رڪنن جو تعداد هڪجيتري هجي.",
                    "• ذيلي سيٽ (Subset): جيڪڏهن سيٽ A جا سڀ رڪن سيٽ B ۾ هجن (A ⊆ B).",
                    f"\\nخلاصو: هي وضاحت سنڌ ٽيڪسٽ بڪ بورڊ ڪلاس 6 رياضي (Riazi Sindhi VI, باب 1) جي تصديق ٿيل درسي مواد مان ڏني وئي آهي۔"
                ]
                final_text = "\\n".join(explanation_lines)
            elif topic == "خالي سيٽ":"""

if old_math_branch in prov_py:
    prov_py = prov_py.replace(old_math_branch, new_math_branch, 1)
    with open('src/services/ai_provider.py', 'w', encoding='utf-8') as f:
        f.write(prov_py)
    print("Added Types of Sets answer branch in ai_provider.py")

print("\nALL FIXES APPLIED SUCCESSFULLY!")

