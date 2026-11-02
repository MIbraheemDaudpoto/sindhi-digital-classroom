import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_HTML_PATH = ROOT / "static" / "app.html"
APP_JS_PATH = ROOT / "static" / "js" / "app.js"

# 1. Update app.html
with open(APP_HTML_PATH, "r", encoding="utf-8") as f:
    html_content = f.read()

old_curriculum_pattern = re.compile(
    r'<div id="curriculum-browser-anchor"[^>]*>.*?<!-- Dynamic Course & Lesson Cards Grid -->\s*<div id="curriculum-lessons-list" class="course-grid"></div>\s*</div>',
    re.DOTALL
)

new_curriculum_html = '''<!-- SINDH ONLINE SCHOOL STEP-BY-STEP PROGRESSIVE CURRICULUM FLOW (Class -> Subject -> Lesson) -->
              <div id="curriculum-browser-anchor" class="sos-curriculum-container">
                
                <!-- Stepper Progress Bar (Step 1 -> 2 -> 3) -->
                <div class="sos-stepper-header" role="navigation" aria-label="قدم به قدم نصاب چونڊيو">
                  <div class="sos-stepper-track">
                    <button type="button" class="sos-step-btn active" id="sos-step-btn-1" onclick="sosGoToStep(1)">
                      <span class="sos-step-badge">1</span>
                      <span class="sos-step-label">ڪلاس چونڊيو (Class)</span>
                      <span class="sos-step-val" id="sos-val-class">ڪلاس 6</span>
                    </button>
                    <div class="sos-step-divider"></div>
                    <button type="button" class="sos-step-btn" id="sos-step-btn-2" onclick="sosGoToStep(2)">
                      <span class="sos-step-badge">2</span>
                      <span class="sos-step-label">مضمون چونڊيو (Subject)</span>
                      <span class="sos-step-val" id="sos-val-subject">رياضي / سائنس</span>
                    </button>
                    <div class="sos-step-divider"></div>
                    <button type="button" class="sos-step-btn" id="sos-step-btn-3" onclick="sosGoToStep(3)">
                      <span class="sos-step-badge">3</span>
                      <span class="sos-step-label">سبق چونڊيو (Lesson)</span>
                      <span class="sos-step-val" id="sos-val-lesson">13 سبق</span>
                    </button>
                  </div>
                </div>

                <!-- Breadcrumb & Back Action Bar -->
                <div class="sos-breadcrumb-bar" id="sos-breadcrumb-bar">
                  <div class="sos-breadcrumbs">
                    <span class="sos-crumb-link" onclick="sosGoToStep(1)">ڪلاس <span id="sos-crumb-class">6</span></span>
                    <span class="sos-crumb-sep">›</span>
                    <span class="sos-crumb-link" onclick="sosGoToStep(2)" id="sos-crumb-subject">رياضي (Mathematics)</span>
                    <span class="sos-crumb-sep" id="sos-crumb-lesson-sep" style="display: none;">›</span>
                    <span class="sos-crumb-active" id="sos-crumb-lesson" style="display: none;">سبق</span>
                  </div>
                  <div class="sos-actions">
                    <button type="button" class="sos-back-btn" id="sos-btn-back-step" onclick="sosGoBackOneStep()" style="display: none;">
                      <span>← واپس وڃو (Back)</span>
                    </button>
                  </div>
                </div>

                <!-- STEP 1: CLASS SELECTION PANEL -->
                <div class="sos-panel" id="sos-panel-classes">
                  <div class="sos-panel-header">
                    <h3>🎓 قدم 1: پنهنجي ڪلاس چونڊيو (Step 1: Choose Your Class)</h3>
                    <p>سنڌ ٽيڪسٽ بوڪ بورڊ (STBB) جي منظور ٿيل نصاب مان پنهنجو درجو چونڊيو:</p>
                  </div>
                  <div class="sos-classes-grid">
                    <div class="sos-class-card active" onclick="sosChooseClass(6, this)" id="sos-class-card-6" tabindex="0" role="button">
                      <div class="sos-class-emblem">6</div>
                      <div class="sos-class-name-sd">ڇهين ڪلاس</div>
                      <div class="sos-class-name-en">Class 6 (Middle)</div>
                      <div class="sos-class-tag" style="background: var(--accent-emerald-soft); color: var(--accent-emerald-dark); font-weight: 700;">13 رياضي • 12 سائنس سبق فعال</div>
                    </div>
                    <div class="sos-class-card" onclick="sosChooseClass(7, this)" id="sos-class-card-7" tabindex="0" role="button">
                      <div class="sos-class-emblem">7</div>
                      <div class="sos-class-name-sd">ستين ڪلاس</div>
                      <div class="sos-class-name-en">Class 7 (Middle)</div>
                      <div class="sos-class-tag">سنڌ بورڊ درسي نصاب</div>
                    </div>
                    <div class="sos-class-card" onclick="sosChooseClass(8, this)" id="sos-class-card-8" tabindex="0" role="button">
                      <div class="sos-class-emblem">8</div>
                      <div class="sos-class-name-sd">اٺين ڪلاس</div>
                      <div class="sos-class-name-en">Class 8 (Middle)</div>
                      <div class="sos-class-tag">سنڌ بورڊ درسي نصاب</div>
                    </div>
                    <div class="sos-class-card" onclick="sosChooseClass(9, this)" id="sos-class-card-9" tabindex="0" role="button">
                      <div class="sos-class-emblem">9</div>
                      <div class="sos-class-name-sd">نائين ڪلاس</div>
                      <div class="sos-class-name-en">Class 9 (Matric)</div>
                      <div class="sos-class-tag">ميٽرڪ پارٽ 1</div>
                    </div>
                    <div class="sos-class-card" onclick="sosChooseClass(10, this)" id="sos-class-card-10" tabindex="0" role="button">
                      <div class="sos-class-emblem">10</div>
                      <div class="sos-class-name-sd">ڏهين ڪلاس</div>
                      <div class="sos-class-name-en">Class 10 (Matric)</div>
                      <div class="sos-class-tag">ميٽرڪ پارٽ 2</div>
                    </div>
                  </div>
                </div>

                <!-- STEP 2: SUBJECT SELECTION PANEL -->
                <div class="sos-panel" id="sos-panel-subjects" style="display: none;">
                  <div class="sos-panel-header">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                      <h3>📚 قدم 2: مضمون چونڊيو (Step 2: Choose Subject)</h3>
                      <span class="sos-class-tag" id="sos-active-class-tag" style="background: var(--accent-primary-soft); color: var(--accent-primary); font-size: 0.8rem; font-weight: 800;">ڇهين ڪلاس جا مضمون</span>
                    </div>
                    <p>هن ڪلاس لاءِ سنڌ ٽيڪسٽ بوڪ بورڊ جا موجود سرڪاري درسي مضمون:</p>
                  </div>
                  <div class="sos-subjects-grid" id="sos-subjects-grid">
                    <!-- Math Subject Card -->
                    <div class="sos-subject-card" onclick="sosChooseSubject('Math')" id="sos-subject-card-math" tabindex="0" role="button">
                      <div class="sos-subject-banner math">
                        <div class="sos-subject-title-box">
                          <h4>رياضي (Mathematics)</h4>
                          <span>سنڌ ٽيڪسٽ بوڪ بورڊ 2024-25</span>
                        </div>
                        <div class="sos-subject-icon-box">🔢</div>
                      </div>
                      <div class="sos-subject-body">
                        <p class="sos-subject-desc">سيٽ، پورا عدد، جزا ۽ ضربينڊڙ، سڄا عدد، سادي صورت، نسبت، الجبرا، جاميٽري ۽ معلومات سيهڙڻ.</p>
                        <div class="sos-subject-meta">
                          <span class="sos-subject-count-pill" style="color: #4f46e5; font-weight: 800;">13 يونٽ / سبق موجود</span>
                          <span style="color: var(--accent-emerald); font-weight: 700;">✔ STBB 2024-25 تصديق ٿيل</span>
                        </div>
                        <div class="sos-subject-btn-explore">
                          <span>سبق ڏسو (Explore Lessons)</span>
                          <span>➔</span>
                        </div>
                      </div>
                    </div>

                    <!-- Science Subject Card -->
                    <div class="sos-subject-card" onclick="sosChooseSubject('Science')" id="sos-subject-card-sci" tabindex="0" role="button">
                      <div class="sos-subject-banner science">
                        <div class="sos-subject-title-box">
                          <h4>عام سائنس (General Science)</h4>
                          <span>سنڌ ٽيڪسٽ بوڪ بورڊ</span>
                        </div>
                        <div class="sos-subject-icon-box">🔬</div>
                      </div>
                      <div class="sos-subject-body">
                        <p class="sos-subject-desc">جيو گهرڙو، خوردبين، ٻوٽا ۽ فوٽوسنٿيسز، ماحول، مادو، توانائي، روشني، آواز ۽ نظام شمسي.</p>
                        <div class="sos-subject-meta">
                          <span class="sos-subject-count-pill" style="color: #059669; font-weight: 800;">12 باب / سبق موجود</span>
                          <span style="color: var(--accent-emerald); font-weight: 700;">✔ STBB تصديق ٿيل</span>
                        </div>
                        <div class="sos-subject-btn-explore">
                          <span>سبق ڏسو (Explore Lessons)</span>
                          <span>➔</span>
                        </div>
                      </div>
                    </div>

                    <!-- Sindhi Subject Card -->
                    <div class="sos-subject-card" onclick="sosChooseSubject('Sindhi')" id="sos-subject-card-sindhi" tabindex="0" role="button">
                      <div class="sos-subject-banner sindhi">
                        <div class="sos-subject-title-box">
                          <h4>سنڌي سليس (Sindhi)</h4>
                          <span>سنڌي درسي ڪتاب</span>
                        </div>
                        <div class="sos-subject-icon-box">📖</div>
                      </div>
                      <div class="sos-subject-body">
                        <p class="sos-subject-desc">شاهه عبداللطيف ڀٽائي، سچل سرمست، سنڌ جا بيت ۽ سنڌي ادب جا اهم نصابي سبق.</p>
                        <div class="sos-subject-meta">
                          <span class="sos-subject-count-pill" style="color: #0891b2; font-weight: 800;">درسي مواد</span>
                          <span style="color: var(--text-dim);">سنڌ سليبس</span>
                        </div>
                        <div class="sos-subject-btn-explore">
                          <span>سبق ڏسو (Explore Lessons)</span>
                          <span>➔</span>
                        </div>
                      </div>
                    </div>

                    <!-- English Subject Card -->
                    <div class="sos-subject-card" onclick="sosChooseSubject('English')" id="sos-subject-card-eng" tabindex="0" role="button">
                      <div class="sos-subject-banner english">
                        <div class="sos-subject-title-box">
                          <h4>انگريزي (English)</h4>
                          <span>English Grammar &amp; Reader</span>
                        </div>
                        <div class="sos-subject-icon-box">🔤</div>
                      </div>
                      <div class="sos-subject-body">
                        <p class="sos-subject-desc">Parts of Speech, Sentence Formation, Reading Comprehension, and Vocabulary.</p>
                        <div class="sos-subject-meta">
                          <span class="sos-subject-count-pill" style="color: #d97706; font-weight: 800;">1 سبق موجود</span>
                          <span style="color: var(--text-dim);">STBB English</span>
                        </div>
                        <div class="sos-subject-btn-explore">
                          <span>سبق ڏسو (Explore Lessons)</span>
                          <span>➔</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- STEP 3: LESSONS LIST PANEL -->
                <div class="sos-panel" id="sos-panel-lessons" style="display: none;">
                  <div class="sos-panel-header">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                      <div>
                        <h3 id="sos-lessons-panel-title">📖 قدم 3: سبق / باب چونڊيو (Step 3: Choose Lesson)</h3>
                        <p id="sos-lessons-panel-subtitle">مڪمل وڊيو ليڪچر، خلاصو ۽ اي آءِ استاد مان رهنمائي لاءِ سبق تي ڪلڪ ڪريو:</p>
                      </div>
                      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                        <input type="text" id="curriculum-search-input" class="search-input-box" placeholder="هن مضمون ۾ سبق ڳوليو..." oninput="filterCurriculumLessons(this.value)" style="max-width: 240px;">
                        <button type="button" class="sos-back-btn" onclick="sosGoToStep(2)" style="background: var(--accent-primary-soft); color: var(--accent-primary); border-color: rgba(37, 99, 235, 0.25);">
                          <span>← ٻيو مضمون چونڊيو</span>
                        </button>
                      </div>
                    </div>

                    <!-- Quick Switch Subject Pills within Step 3 -->
                    <div class="filter-pills-row" id="subject-selector-pills" style="margin-top: 14px; padding-top: 10px; border-top: 1px dashed var(--border-subtle);">
                      <button class="pill-btn active" onclick="sosChooseSubject('Math')" id="pill-sub-math">
                        <span>🔢 رياضي (Mathematics)</span>
                      </button>
                      <button class="pill-btn" onclick="sosChooseSubject('Science')" id="pill-sub-sci">
                        <span>🔬 عام سائنس (General Science)</span>
                      </button>
                      <button class="pill-btn" onclick="sosChooseSubject('Sindhi')" id="pill-sub-sindhi">
                        <span>📖 سنڌي سليس (Sindhi)</span>
                      </button>
                      <button class="pill-btn" onclick="sosChooseSubject('English')" id="pill-sub-eng">
                        <span>🔤 انگريزي (English)</span>
                      </button>
                      <button class="pill-btn" onclick="sosChooseSubject(null)" id="pill-sub-all" style="opacity: 0.85;">
                        <span>📚 سڀ مضمون (All)</span>
                      </button>
                    </div>
                  </div>

                  <!-- Dynamic Course & Lesson Cards Grid -->
                  <div id="curriculum-lessons-list" class="course-grid"></div>
                </div>
              </div>'''

if old_curriculum_pattern.search(html_content):
    html_content = old_curriculum_pattern.sub(new_curriculum_html, html_content)
    with open(APP_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Successfully replaced curriculum browser in app.html!")
else:
    print("Warning: regex pattern did not match app.html!")

