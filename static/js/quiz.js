/**
 * Sindhi Digital Classroom (SDC) - Real-Time Assessment Quiz Engine
 * Replaces broken video checkpoints with authentic, curriculum-grounded quizzes.
 * Supports:
 * - Single lesson assessment
 * - Multi-lesson assessment
 * - Full class & subject assessment
 * - Practice mode (instant feedback + citations) vs Assessment mode (withheld until submission)
 * - Server-side attempt generation, session ownership, server-side grading, and LMS progress persistence
 * - Honest Provenance: Explicitly distinguishes Live AI vs Local Curriculum Bank (Non-AI)
 */

(function () {
  'use strict';

  // State object
  const QuizState = {
    isOpen: false,
    currentStep: 'SETUP', // 'SETUP' | 'QUIZ' | 'RESULTS'
    selectedClass: 6,
    selectedSubject: 'Science',
    selectedLessons: new Set(),
    allLessonsForSubject: [],
    questionCount: 5,
    mode: 'PRACTICE', // 'PRACTICE' | 'ASSESSMENT'
    difficulty: 'MEDIUM',
    activeSessionId: null,
    providerStatus: null,
    providerModelName: null,
    inferenceRequestId: null,
    inferenceStatus: 'NOT_RUN',
    isLiveAi: false,
    aiStatusMessage: null,
    questions: [],
    currentQuestionIndex: 0,
    answers: {}, // question_id -> { selected_option, is_correct, explanation, citation, correct_index }
    startTime: null,
    timerInterval: null,
    submissionResult: null
  };

  // Expose to window
  window.QuizState = QuizState;

  function getAuthToken() {
    if (window.currentUser && window.currentUser.token) return window.currentUser.token;
    try {
      const raw = localStorage.getItem('sdc_current_user');
      if (raw) {
        const u = JSON.parse(raw);
        if (u && u.token) return u.token;
        if (u && u.user_id) return u.user_id;
      }
    } catch (e) {}
    const tok = localStorage.getItem('sdc_token');
    if (tok) return tok;
    return null;
  }

  /**
   * Open the Assessment Hub
   * @param {string|null} preselectedLessonId - optional lesson to preselect
   */
  window.openAssessmentHub = async function (preselectedLessonId = null) {
    const modal = document.getElementById('sdc-assessment-modal');
    if (!modal) {
      console.error('[Quiz] Modal container #sdc-assessment-modal not found');
      return;
    }

    modal.style.display = 'flex';
    QuizState.isOpen = true;
    QuizState.currentStep = 'SETUP';

    // If preselected lesson is provided, determine subject & class
    if (preselectedLessonId && !preselectedLessonId.startsWith('crs-')) {
      const isMath = preselectedLessonId.includes('math') || (window.currentLoadedLesson && window.currentLoadedLesson.course_id && window.currentLoadedLesson.course_id.includes('math'));
      QuizState.selectedClass = window.activeClassLevel || 6;
      QuizState.selectedSubject = isMath ? 'Mathematics' : 'Science';
      QuizState.selectedLessons = new Set([preselectedLessonId]);
    } else {
      const isMathFromPre = preselectedLessonId && preselectedLessonId.includes('math');
      QuizState.selectedClass = window.activeClassLevel || 6;
      const curSubject = window.activeSubjectFilter;
      QuizState.selectedSubject = (isMathFromPre || curSubject === 'Math' || curSubject === 'Mathematics') ? 'Mathematics' : 'Science';
      QuizState.selectedLessons.clear();
    }

    renderSetupView();
    await loadLessonsForSetup();
  };

  /**
   * Shortcut for current lesson quiz
   */
  window.openAssessmentForCurrentLesson = function () {
    const lessonId = window.currentLoadedLessonId || (window.sdcPlayer && window.sdcPlayer.currentLesson ? window.sdcPlayer.currentLesson.id : null);
    if (lessonId) {
      window.openAssessmentHub(lessonId);
    } else {
      window.openAssessmentHub();
    }
  };

  /**
   * Close the Assessment Modal
   */
  window.closeAssessmentModal = function () {
    const modal = document.getElementById('sdc-assessment-modal');
    if (modal) modal.style.display = 'none';
    QuizState.isOpen = false;
    clearInterval(QuizState.timerInterval);
  };

  /**
   * Render the Initial Setup View (Scope Selector)
   */
  function renderSetupView() {
    const container = document.getElementById('assessment-modal-body');
    if (!container) return;

    container.innerHTML = `
      <div class="assessment-setup-container" dir="rtl">
        <div class="assessment-header-bar">
          <div class="assessment-title-wrap">
            <span class="assessment-badge-pill">🎓 سنڌ ٽيڪسٽ بڪ بورڊ - امتحاني مرڪز</span>
            <h2 class="assessment-modal-title">درسي ڪوئيز (Curriculum Assessment)</h2>
            <p class="assessment-modal-subtitle">پنهنجو مضمون ۽ هڪ يا وڌيڪ سبق چونڊيو. سوالن جو ذريعو ڪوئيز شروع ٿيڻ کان اڳ واضح ڪيو ويندو.</p>
          </div>
          <button type="button" class="assessment-btn-close" onclick="closeAssessmentModal()" title="بند ڪريو">✕</button>
        </div>

        <div class="assessment-grid-config">
          <!-- Step A: Class & Subject Selector -->
          <div class="config-card">
            <h4 class="config-card-title">1. ڪلاس ۽ مضمون چونڊيو</h4>
            <div class="config-field">
              <label class="config-label">ڪلاس:</label>
              <div class="pill-group" id="quiz-class-selector">
                <button type="button" class="pill-btn active" disabled>ڪلاس 6</button>
              </div>
            </div>

            <div class="config-field" style="margin-top: 14px;">
              <label class="config-label">مضمون:</label>
              <div class="pill-group" id="quiz-subject-selector">
                <button type="button" class="pill-btn ${QuizState.selectedSubject === 'Science' ? 'active' : ''}" onclick="onQuizSubjectChanged('Science')">🔬 جنرل سائنس (Science)</button>
                <button type="button" class="pill-btn ${QuizState.selectedSubject === 'Mathematics' ? 'active' : ''}" onclick="onQuizSubjectChanged('Mathematics')">📐 رياضي (Mathematics)</button>
              </div>
            </div>

            <div class="config-field" style="margin-top: 14px;">
              <label class="config-label">امتحان جو قسم (Mode):</label>
              <div class="pill-group" id="quiz-mode-selector">
                <button type="button" class="pill-btn ${QuizState.mode === 'PRACTICE' ? 'active' : ''}" onclick="onQuizModeChanged('PRACTICE')">
                  💡 مشقي موڊ (فوري رهنمائي ۽ حوالو)
                </button>
                <button type="button" class="pill-btn ${QuizState.mode === 'ASSESSMENT' ? 'active' : ''}" onclick="onQuizModeChanged('ASSESSMENT')">
                  📝 حقيقي امتحان (نتيجو آخر ۾)
                </button>
              </div>
            </div>

            <div class="config-field" style="margin-top: 14px;">
              <label class="config-label">سوالن جو تعداد:</label>
              <div class="pill-group" id="quiz-count-selector">
                <button type="button" class="pill-btn ${QuizState.questionCount === 3 ? 'active' : ''}" onclick="onQuizCountChanged(3)">3 سوال (مختصر)</button>
                <button type="button" class="pill-btn ${QuizState.questionCount === 5 ? 'active' : ''}" onclick="onQuizCountChanged(5)">5 سوال (معياري)</button>
                <button type="button" class="pill-btn ${QuizState.questionCount === 10 ? 'active' : ''}" onclick="onQuizCountChanged(10)">10 سوال (مڪمل)</button>
              </div>
            </div>
          </div>

          <!-- Step B: Lessons Multi-Select -->
          <div class="config-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <h4 class="config-card-title" style="margin: 0;">2. سبق چونڊيو (Lessons)</h4>
              <div style="display: flex; gap: 8px;">
                <button type="button" class="link-btn-action" onclick="selectAllQuizLessons(true)">سڀ چونڊيو</button>
                <span style="color: var(--border-subtle);">|</span>
                <button type="button" class="link-btn-action" onclick="selectAllQuizLessons(false)">ختم ڪريو</button>
              </div>
            </div>
            <p class="config-help">هڪ يا وڌيڪ سبق چونڊيو، يا پوري مضمون جا سڀئي سبق شامل ڪريو.</p>

            <div id="quiz-lessons-checklist" class="quiz-lessons-checklist">
              <div class="loading-spinner-sindhi">سبق لوڊ ٿي رهيا آهن...</div>
            </div>
          </div>
        </div>

        <!-- Action Footer -->
        <div class="assessment-footer-bar">
          <div id="quiz-scope-summary" class="quiz-scope-summary">
            0 سبق چونڊيل
          </div>
          <button type="button" id="btn-generate-quiz-action" class="btn-primary-action" onclick="startGeneratedQuiz()">
            🚀 نئون ڪوئز تيار ڪريو (Start Quiz)
          </button>
        </div>
      </div>
    `;
  }

  window.onQuizClassChanged = async function (newClass) {
    if (newClass !== 6) return;
    QuizState.selectedClass = newClass;
    QuizState.selectedLessons.clear();
    renderSetupView();
    await loadLessonsForSetup();
  };

  window.onQuizSubjectChanged = async function (newSubject) {
    QuizState.selectedSubject = newSubject;
    QuizState.selectedLessons.clear();
    renderSetupView();
    await loadLessonsForSetup();
  };

  window.onQuizModeChanged = function (newMode) {
    QuizState.mode = newMode;
    renderSetupView();
    renderLessonsChecklist();
  };

  window.onQuizCountChanged = function (newCount) {
    QuizState.questionCount = newCount;
    renderSetupView();
    renderLessonsChecklist();
  };

  window.selectAllQuizLessons = function (select) {
    if (select) {
      QuizState.allLessonsForSubject.forEach(l => QuizState.selectedLessons.add(l.id));
    } else {
      QuizState.selectedLessons.clear();
    }
    renderLessonsChecklist();
  };

  window.toggleQuizLessonSelection = function (lessonId) {
    if (QuizState.selectedLessons.has(lessonId)) {
      QuizState.selectedLessons.delete(lessonId);
    } else {
      QuizState.selectedLessons.add(lessonId);
    }
    renderLessonsChecklist();
  };

  /**
   * Load published/approved lessons for selected class & subject.
   * Handles List[CourseResponse] where lessons are nested in course.lessons.
   */
  async function loadLessonsForSetup() {
    try {
      const token = getAuthToken();
      const res = await fetch(`/api/lessons?class_level=${QuizState.selectedClass}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to load lessons from server');
      const data = await res.json();

      const isMath = (QuizState.selectedSubject === 'Mathematics' || QuizState.selectedSubject === 'Math');
      let extractedLessons = [];

      if (Array.isArray(data)) {
        for (const item of data) {
          if (Array.isArray(item.lessons) && item.lessons.length > 0) {
            // It's a CourseResponse containing lessons array
            const courseId = (item.id || '').toLowerCase();
            const courseTitle = (item.title_english || '').toLowerCase();
            const courseSub = (item.subject || '').toLowerCase();
            const courseMatches = isMath
              ? (courseId.includes('math') || courseTitle.includes('math') || courseSub.includes('math'))
              : (courseId.includes('sci') || courseTitle.includes('sci') || courseSub.includes('sci') || (!courseId.includes('math') && !courseTitle.includes('math') && !courseId.includes('eng') && !courseId.includes('sindhi')));
            if (courseMatches) {
              extractedLessons.push(...item.lessons);
            }
          } else if (item.id && !item.id.startsWith('crs-') && item.unit_number !== undefined) {
            // It's a direct lesson record
            const lId = (item.id || '').toLowerCase();
            const cId = (item.course_id || '').toLowerCase();
            const matches = isMath
              ? (lId.includes('math') || cId.includes('math'))
              : (lId.includes('sci') || cId.includes('sci') || (!lId.includes('math') && !cId.includes('math')));
            if (matches) {
              extractedLessons.push(item);
            }
          }
        }
      }

      // Sort by unit number ascending
      extractedLessons.sort((a, b) => (Number(a.unit_number) || 0) - (Number(b.unit_number) || 0));
      QuizState.allLessonsForSubject = extractedLessons;

      // If no lessons selected yet, select the first one by default
      if (QuizState.selectedLessons.size === 0 && QuizState.allLessonsForSubject.length > 0) {
        QuizState.selectedLessons.add(QuizState.allLessonsForSubject[0].id);
      }

      renderLessonsChecklist();
    } catch (err) {
      console.warn('[Quiz] Could not fetch lessons list:', err);
      const listEl = document.getElementById('quiz-lessons-checklist');
      if (listEl) {
        listEl.innerHTML = `<div class="error-msg-sindhi">سبق جي لسٽ لوڊ نه ٿي سگهي. مهرباني ڪري نيٽ ورڪ چيڪ ڪريو.</div>`;
      }
    }
  }

  function renderLessonsChecklist() {
    const listEl = document.getElementById('quiz-lessons-checklist');
    const summaryEl = document.getElementById('quiz-scope-summary');
    const genBtn = document.getElementById('btn-generate-quiz-action');
    if (!listEl) return;

    if (QuizState.allLessonsForSubject.length === 0) {
      listEl.innerHTML = `<div class="empty-msg-sindhi">هن ڪلاس ۽ مضمون لاءِ ڪي به منظور ٿيل سبق دستياب ناهن.</div>`;
      if (summaryEl) summaryEl.textContent = 'ڪو به سبق دستياب ناهي';
      if (genBtn) genBtn.disabled = true;
      return;
    }

    listEl.innerHTML = QuizState.allLessonsForSubject.map(l => {
      const isChecked = QuizState.selectedLessons.has(l.id);
      return `
        <label class="lesson-check-row ${isChecked ? 'checked' : ''}" onclick="toggleQuizLessonSelection('${l.id}')">
          <input type="checkbox" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation(); toggleQuizLessonSelection('${l.id}')" />
          <div class="lesson-check-info">
            <span class="lesson-check-unit">يونٽ ${l.unit_number || '1'}</span>
            <span class="lesson-check-title">${escapeHtml(l.title_sindhi)}</span>
            ${l.title_english ? `<span class="lesson-check-eng ltr-text">${escapeHtml(l.title_english)}</span>` : ''}
          </div>
        </label>
      `;
    }).join('');

    const count = QuizState.selectedLessons.size;
    if (summaryEl) {
      summaryEl.innerHTML = `<strong>${count}</strong> مان <strong>${QuizState.allLessonsForSubject.length}</strong> سبق چونڊيل`;
    }
    if (genBtn) {
      genBtn.disabled = (count === 0);
    }
  }

  /**
   * Start Generated Quiz (Requires POST /api/quiz/generate, no unpersisted client fallback)
   */
  window.startGeneratedQuiz = async function () {
    if (QuizState.selectedLessons.size === 0) {
      alert('مهرباني ڪري گهٽ ۾ گهٽ هڪ سبق چونڊيو.');
      return;
    }

    const container = document.getElementById('assessment-modal-body');
    if (!container) return;

    container.innerHTML = `
      <div class="assessment-loading-screen" dir="rtl">
        <div class="spinner-large"></div>
        <h3>سنڌ ٽيڪسٽ بڪ بورڊ جي نصاب مان سوال تيار ٿي رهيا آهن...</h3>
        <p>مهرباني ڪري ڪجهه سيڪنڊ انتظار ڪريو.</p>
      </div>
    `;

    const token = getAuthToken();
    const isMath = (QuizState.selectedSubject === 'Mathematics' || QuizState.selectedSubject === 'Math');
    const requestPayload = {
      course_id: isMath ? `crs-math-${QuizState.selectedClass}` : `crs-sci-${QuizState.selectedClass}`,
      class_level: QuizState.selectedClass,
      subject: isMath ? 'Math' : QuizState.selectedSubject,
      lesson_ids: Array.from(QuizState.selectedLessons),
      question_count: QuizState.questionCount,
      difficulty: QuizState.difficulty,
      mode: QuizState.mode,
      allow_fallback: true
    };

    const controller = new AbortController();
    const requestTimeout = setTimeout(() => controller.abort(), 50000);
    try {
      const res = await fetch('/api/quiz/generate', {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestPayload)
      });

      if (!res.ok) {
        const errDetail = await res.json().catch(() => ({}));
        const detailMsg = typeof errDetail.detail === 'string' ? errDetail.detail : '';
        throw new Error(detailMsg || `ڪوئز تيار ڪرڻ ۾ ڏکيائي آئي (سرور رسپانس: ${res.status}).`);
      }

      const sessionData = await res.json();

      QuizState.activeSessionId = sessionData.session_id;
      QuizState.mode = (sessionData.mode || QuizState.mode).toUpperCase();
      QuizState.providerStatus = sessionData.provider_type || 'LOCAL_CURRICULUM_BANK';
      QuizState.providerModelName = sessionData.model_name || null;
      QuizState.inferenceRequestId = sessionData.inference_request_id || null;
      QuizState.inferenceStatus = sessionData.inference_status || 'NOT_REPORTED';
      QuizState.isLiveAi = !!sessionData.is_live_ai;
      QuizState.aiStatusMessage = sessionData.ai_status_message || null;
      QuizState.questions = sessionData.questions || [];
      QuizState.currentQuestionIndex = 0;
      QuizState.answers = {};
      QuizState.startTime = Date.now();
      QuizState.currentStep = 'QUIZ';

      renderQuizRunner(sessionData);
      startQuizTimer();

    } catch (err) {
      console.error('[Quiz] Quiz generation failed:', err);
      const message = err.name === 'AbortError'
        ? 'AI سوال تيار ڪرڻ ۾ گهڻو وقت لڳي ويو، نتيجو نه مليو. مهرباني ڪري ڪجهه دير بعد ٻيهر ڪوشش ڪريو. (Quiz generation timed out; no result was received.)'
        : (err.message || 'مسئلو پيش آيو. مهرباني ڪري ٻيهر ڪوشش ڪريو.');
      container.innerHTML = `
        <div class="assessment-error-screen" dir="rtl">
          <h3>ڪوئز تيار نه ٿي سگهيو</h3>
          <p>${escapeHtml(message)}</p>
          <div style="display: flex; gap: 10px; justify-content: center; margin-top: 14px;">
            <button type="button" class="btn-primary-action" onclick="openAssessmentHub()">واپس وڃو</button>
            <button type="button" class="btn-secondary-action" onclick="closeAssessmentModal()">بند ڪريو</button>
          </div>
        </div>
      `;
    } finally {
      clearTimeout(requestTimeout);
    }
  };

  /**
   * Render Quiz Runner
   */
  function renderQuizRunner(sessionData) {
    const container = document.getElementById('assessment-modal-body');
    if (!container) return;

    const isLiveAi = !!QuizState.isLiveAi;
    const provLabel = isLiveAi
      ? `🤖 لائيو ماڊل: ${escapeHtml(QuizState.providerStatus)} / ${escapeHtml(QuizState.providerModelName || 'نامعلوم ماڊل')}`
      : '📚 غير AI درسي سوال بئنڪ';

    container.innerHTML = `
      <div class="assessment-runner-container" dir="rtl">
        <!-- Top Banner Bar -->
        <div class="runner-header-bar">
          <div class="runner-meta-left">
            <span class="runner-badge-mode ${QuizState.mode === 'PRACTICE' ? 'practice' : 'assessment'}">
              ${QuizState.mode === 'PRACTICE' ? '💡 مشقي موڊ (فوري تصديق ۽ حوالو)' : '📝 حقيقي امتحاني موڊ (نتيجو آخر ۾)'}
            </span>
            <span class="runner-badge-prov ${isLiveAi ? 'badge-live-ai' : 'badge-curriculum-bank'}">
              ${provLabel}
            </span>
          </div>

          <div class="runner-meta-right">
            <span id="quiz-runner-timer" class="runner-timer">00:00</span>
            <button type="button" class="btn-cancel-quiz" onclick="confirmExitQuiz()">ڇڏي ڏيو ✕</button>
          </div>
        </div>

        ${QuizState.aiStatusMessage ? `
          <div class="assessment-provenance-notice">
            ℹ️ ${escapeHtml(QuizState.aiStatusMessage)}
            ${isLiveAi ? `<div>انفرنس: ${escapeHtml(QuizState.inferenceStatus)} · درخواست: ${escapeHtml(QuizState.inferenceRequestId || 'ID دستياب ناهي')}</div>` : ''}
          </div>
        ` : ''}

        <!-- Progress Indicator -->
        <div class="runner-progress-row">
          <div class="runner-progress-info">
            <span id="runner-q-counter">سوال 1 مان ${QuizState.questions.length}</span>
            <span id="runner-pct-counter">0% مڪمل</span>
          </div>
          <div class="runner-progress-track">
            <div id="runner-progress-fill" class="runner-progress-fill" style="width: 0%;"></div>
          </div>
        </div>

        <!-- Question View Box -->
        <div id="runner-question-stage" class="runner-question-stage">
          <!-- Question inserted dynamically here -->
        </div>

        <!-- Runner Actions Footer -->
        <div class="runner-footer-bar">
          <button type="button" id="btn-quiz-prev" class="btn-secondary-action" onclick="goToPrevQuestion()" style="display: none;">
            ← پويون سوال
          </button>
          <div style="flex: 1;"></div>
          <button type="button" id="btn-quiz-next" class="btn-primary-action" onclick="goToNextQuestion()" disabled>
            اڳيون سوال →
          </button>
        </div>
      </div>
    `;

    renderCurrentQuestion();
  }

  function startQuizTimer() {
    clearInterval(QuizState.timerInterval);
    const timerEl = document.getElementById('quiz-runner-timer');
    QuizState.timerInterval = setInterval(() => {
      if (!timerEl) return;
      const elapsedSec = Math.floor((Date.now() - QuizState.startTime) / 1000);
      const mins = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
      const secs = String(elapsedSec % 60).padStart(2, '0');
      timerEl.textContent = `${mins}:${secs}`;
    }, 1000);
  }

  function renderCurrentQuestion() {
    const qIndex = QuizState.currentQuestionIndex;
    const totalQ = QuizState.questions.length;
    const q = QuizState.questions[qIndex];
    if (!q) return;

    // Update Progress
    const counterEl = document.getElementById('runner-q-counter');
    const pctEl = document.getElementById('runner-pct-counter');
    const fillEl = document.getElementById('runner-progress-fill');
    if (counterEl) counterEl.textContent = `سوال ${qIndex + 1} مان ${totalQ}`;
    const pct = Math.round(((qIndex) / totalQ) * 100);
    if (pctEl) pctEl.textContent = `${pct}% مڪمل`;
    if (fillEl) fillEl.style.width = `${pct}%`;

    const stageEl = document.getElementById('runner-question-stage');
    if (!stageEl) return;

    const existingAnswer = QuizState.answers[q.id];
    const hasAnswered = (existingAnswer !== undefined);

    const letters = ['الف', 'ب', 'ج', 'د'];
    const attributionText = q.lesson_title_sd || q.lesson_title || q.attribution_tag || 'سنڌ ٽيڪسٽ بڪ بورڊ';

    const isPractice = (QuizState.mode || '').toUpperCase() === 'PRACTICE';

    stageEl.innerHTML = `
      <div class="question-card" id="q-card-${q.id}">
        <div class="question-header">
          <span class="question-attribution">[${escapeHtml(attributionText)}]</span>
          <span class="question-num-badge">سوال نمبر ${qIndex + 1}</span>
        </div>

        <h3 class="question-title-text">${escapeHtml(q.text_sindhi || q.question_text)}</h3>

        <div class="question-options-list">
          ${q.options.map((optText, optIdx) => {
            const isSelected = hasAnswered && existingAnswer.selected_option === optIdx;
            let statusClass = '';
            if (hasAnswered) {
              if (isPractice && existingAnswer.is_correct !== null && existingAnswer.is_correct !== undefined) {
                if (optIdx === existingAnswer.correct_index || (existingAnswer.is_correct === true && isSelected)) {
                  statusClass = 'correct-option';
                } else if (isSelected && existingAnswer.is_correct === false) {
                  statusClass = 'incorrect-option';
                }
              } else if (isSelected) {
                statusClass = 'selected-option';
              }
            }

            return `
              <button type="button" class="option-btn ${statusClass}" 
                      ${hasAnswered ? 'disabled' : ''} 
                      onclick="onSelectOption(${optIdx})">
                <span class="option-letter-tag">${letters[optIdx] || (optIdx + 1)}</span>
                <span class="option-content-text">${escapeHtml(optText)}</span>
              </button>
            `;
          }).join('')}
        </div>

        <!-- Feedback Box: Instant feedback in Practice mode or Save confirmation in Assessment mode -->
        <div id="runner-instant-feedback" class="runner-feedback-box" style="${hasAnswered ? 'display: block;' : 'display: none;'}">
          ${hasAnswered ? renderFeedbackHtml(existingAnswer) : ''}
        </div>
      </div>
    `;

    // Update Action Buttons
    const prevBtn = document.getElementById('btn-quiz-prev');
    const nextBtn = document.getElementById('btn-quiz-next');

    if (prevBtn) {
      prevBtn.style.display = (qIndex > 0) ? 'inline-flex' : 'none';
    }

    if (nextBtn) {
      nextBtn.disabled = !hasAnswered;
      if (qIndex === totalQ - 1) {
        nextBtn.innerHTML = '🏁 امتحان مڪمل ۽ جمع ڪريو (Submit)';
        nextBtn.classList.add('submit-mode');
      } else {
        nextBtn.innerHTML = 'اڳيون سوال →';
        nextBtn.classList.remove('submit-mode');
      }
    }
  }

  function renderFeedbackHtml(ans) {
    if (!ans) return '';
    if (ans.is_correct === null || ans.is_correct === undefined) {
      return `
        <div class="feedback-card info">
          <div class="feedback-title">📝 جواب محفوظ ٿي ويو (Answer Saved)</div>
          <div class="feedback-explanation">امتحاني موڊ: درسي وضاحتون، درست جواب ۽ نتيجو سڀني سوالن کي جمع ڪرڻ بعد سامهون ايندا.</div>
        </div>
      `;
    }
    const isCorrect = (ans.is_correct === true);
    return `
      <div class="feedback-card ${isCorrect ? 'success' : 'failure'}">
        <div class="feedback-title">
          ${isCorrect ? '✅ شاباس! درست جواب' : '❌ غلط جواب'}
        </div>
        ${ans.explanation ? `<div class="feedback-explanation"><strong>${isCorrect ? 'وضاحت' : 'درست درسي وضاحت'}:</strong> ${escapeHtml(ans.explanation)}</div>` : ''}
        ${ans.citation ? `<div class="feedback-citation">📖 <strong>درسي حوالو:</strong> ${escapeHtml(ans.citation)}</div>` : ''}
      </div>
    `;
  }

  /**
   * Option Click Handler (Always sends to server endpoint)
   */
  window.onSelectOption = async function (selectedIndex) {
    const qIndex = QuizState.currentQuestionIndex;
    const q = QuizState.questions[qIndex];
    if (!q || QuizState.answers[q.id] !== undefined) return;

    const token = getAuthToken();

    try {
      const res = await fetch(`/api/quiz/${QuizState.activeSessionId}/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          question_id: q.id,
          selected_option: selectedIndex,
          time_taken_seconds: 5.0
        })
      });

      if (!res.ok) {
        const errDetail = await res.json().catch(() => ({}));
        throw new Error(errDetail.detail || `جواب محفوظ نه ٿي سگهيو (HTTP ${res.status}).`);
      }

      const data = await res.json();
      QuizState.answers[q.id] = {
        selected_option: selectedIndex,
        is_correct: data.is_correct,
        explanation: data.explanation_sindhi,
        citation: data.citation,
        correct_index: data.correct_answer_index
      };

      renderCurrentQuestion();

    } catch (e) {
      console.error('[Quiz] Answer submission failed:', e);
      alert(e.message || 'جواب محفوظ ڪرڻ ۾ ڏکيائي آئي.');
    }
  };

  window.goToPrevQuestion = function () {
    if (QuizState.currentQuestionIndex > 0) {
      QuizState.currentQuestionIndex--;
      renderCurrentQuestion();
    }
  };

  window.goToNextQuestion = function () {
    const totalQ = QuizState.questions.length;
    if (QuizState.currentQuestionIndex < totalQ - 1) {
      QuizState.currentQuestionIndex++;
      renderCurrentQuestion();
    } else {
      // Last question - submit quiz
      submitFinalAssessment();
    }
  };

  window.confirmExitQuiz = function () {
    if (confirm('ڇا توهان واقعي هي امتحان اڌ ۾ ڇڏڻ چاهيو ٿا؟')) {
      window.openAssessmentHub();
    }
  };

  /**
   * Submit Final Assessment (Server-side scoring only)
   */
  async function submitFinalAssessment() {
    clearInterval(QuizState.timerInterval);
    const container = document.getElementById('assessment-modal-body');
    if (!container) return;

    container.innerHTML = `
      <div class="assessment-loading-screen" dir="rtl">
        <div class="spinner-large"></div>
        <h3>امتحان جا نتيجا ۽ سبق وار تجزيو تيار ٿي رهيو آهي...</h3>
      </div>
    `;

    const token = getAuthToken();

    try {
      const res = await fetch(`/api/quiz/${QuizState.activeSessionId}/submit`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) {
        const errDetail = await res.json().catch(() => ({}));
        throw new Error(errDetail.detail || `نتيجو حاصل نه ٿي سگهيو (HTTP ${res.status}).`);
      }

      const results = await res.json();
      QuizState.submissionResult = results;
      QuizState.currentStep = 'RESULTS';

      // If passed, trigger progress update in UI
      if (results.passed && window.loadStudentDashboardStats) {
        window.loadStudentDashboardStats();
      }

      renderResultsScreen(results);

    } catch (e) {
      console.error('[Quiz] Final submission to API failed:', e);
      container.innerHTML = `
        <div class="assessment-error-screen" dir="rtl">
          <h3>امتحان جمع ڪرڻ ۾ ڏکيائي آئي</h3>
          <p>${escapeHtml(e.message || 'سرور سان رابطو نه ٿي سگهيو.')}</p>
          <div style="display: flex; gap: 10px; justify-content: center; margin-top: 14px;">
            <button type="button" class="btn-primary-action" onclick="submitFinalAssessment()">ٻيهر ڪوشش ڪريو (Retry Submit)</button>
            <button type="button" class="btn-secondary-action" onclick="closeAssessmentModal()">بند ڪريو</button>
          </div>
        </div>
      `;
    }
  }

  /**
   * Render Comprehensive Results & Review Screen
   */
  function renderResultsScreen(res) {
    const container = document.getElementById('assessment-modal-body');
    if (!container) return;

    const letters = ['الف', 'ب', 'ج', 'د'];

    const scorePct = (res.percentage !== undefined) ? res.percentage : ((res.score !== undefined) ? res.score : (res.score_percentage || 0));
    const correctAnswers = (res.correct_count !== undefined) ? res.correct_count : (res.correct_answers || 0);
    const totalQuestions = res.total_questions || 0;

    let breakdownList = [];
    if (res.per_lesson_breakdown) {
      if (Array.isArray(res.per_lesson_breakdown)) {
        breakdownList = res.per_lesson_breakdown;
      } else if (typeof res.per_lesson_breakdown === 'object') {
        breakdownList = Object.values(res.per_lesson_breakdown);
      }
    } else if (res.lesson_breakdown) {
      breakdownList = Array.isArray(res.lesson_breakdown) ? res.lesson_breakdown : Object.values(res.lesson_breakdown);
    }

    const reviewTopics = res.topics_to_review || res.review_topics || [];
    const questionsReview = res.review || res.questions_review || [];

    container.innerHTML = `
      <div class="assessment-results-container" dir="rtl">
        <!-- Results Hero Banner -->
        <div class="results-hero-card ${res.passed ? 'passed' : 'review-needed'}">
          <div class="results-score-circle">
            <span class="results-score-number">${Math.round(scorePct)}%</span>
            <span class="results-score-label">${res.passed ? 'ڪامياب' : 'ٻيهر مشق'}</span>
          </div>

          <div class="results-summary-text">
            <h2>${res.passed ? '🎉 زبردست! توهان ڪاميابي حاصل ڪئي' : 'توهان کي وڌيڪ درسي مشق جي ضرورت آهي'}</h2>
            <p>توهان <strong>${totalQuestions}</strong> مان <strong>${correctAnswers}</strong> سوالن جا درست جواب ڏنا.</p>
            <div class="results-progress-pill">
              ${res.passed ? '✅ شاگرد جي LMS پروفائل ۾ اڳڀرائي رڪارڊ ٿي چڪي آهي.' : '⚠️ اڳڀرائي صرف 50% يا ان کان وڌيڪ نتيجي تي رڪارڊ ٿيندي آهي.'}
            </div>
          </div>
        </div>

        <!-- Per-Lesson Breakdown Table -->
        <div class="results-section">
          <h4 class="results-section-title">📊 سبق وار ڪارڪردگي (Lesson-by-Lesson Breakdown)</h4>
          <div class="breakdown-table-wrapper">
            <table class="breakdown-table">
              <thead>
                <tr>
                  <th>سبق جو نالو</th>
                  <th>ڪل سوال</th>
                  <th>درست جواب</th>
                  <th>فيصد (Score %)</th>
                  <th>حيثيت</th>
                </tr>
              </thead>
              <tbody>
                ${breakdownList.map(b => {
                  const bTitle = b.lesson_title_sd || b.lesson_title || b.lesson_id;
                  const bTotal = b.total_questions || b.total || 0;
                  const bCorr = (b.correct_questions !== undefined) ? b.correct_questions : (b.correct_answers || 0);
                  const bPct = Math.round((b.percentage !== undefined) ? b.percentage : (b.score_percentage || 0));
                  const bPass = bPct >= 50;
                  return `
                    <tr>
                      <td><strong>${escapeHtml(bTitle)}</strong></td>
                      <td>${bTotal}</td>
                      <td>${bCorr}</td>
                      <td><strong>${bPct}%</strong></td>
                      <td>
                        <span class="status-badge ${bPass ? 'pass' : 'fail'}">
                          ${bPass ? 'ڪامياب' : 'ڪمزور'}
                        </span>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Topics to Review (if any) -->
        ${reviewTopics.length > 0 ? `
          <div class="results-section review-topics-box">
            <h4 class="results-section-title" style="color: #b91c1c;">⚠️ ٻيهر نظرثاني جا عنوان (Topics to Review)</h4>
            <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 8px;">هيٺ ڏنل سبقن ۾ توهان جا جواب غلط ٿيا آهن. مهرباني ڪري ڪتاب مان اهي صفحا پڙهو يا AI استاد کان پڇو:</p>
            <ul class="review-topics-list">
              ${reviewTopics.map(t => `<li>📖 ${escapeHtml(t)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}

        <!-- Question-by-Question Detailed Review -->
        <div class="results-section">
          <h4 class="results-section-title">🔍 سمورن سوالن جي تفصيلي نظرثاني (Full Question Review)</h4>
          <div class="questions-review-list">
            ${questionsReview.map((item, idx) => {
              const qTitle = item.lesson_title_sd || item.lesson_title || '';
              const qText = item.text_sindhi || item.question_text || '';
              const selOpt = item.selected_option;
              const corrOpt = (item.correct_answer_index !== undefined) ? item.correct_answer_index : item.correct_option_index;
              const isCorr = !!item.is_correct;
              const expl = item.explanation_sindhi || '';
              const cit = item.citation || '';

              return `
                <div class="review-item-card ${isCorr ? 'correct' : 'incorrect'}">
                  <div class="review-item-header">
                    <span class="review-q-num">سوال ${idx + 1} ${qTitle ? `(${escapeHtml(qTitle)})` : ''}</span>
                    <span class="review-q-status">${isCorr ? '✅ درست' : '❌ غلط'}</span>
                  </div>
                  <h4 class="review-q-text">${escapeHtml(qText)}</h4>

                  <div class="review-options-display">
                    ${item.options.map((opt, oIdx) => {
                      const isSelected = (selOpt === oIdx);
                      const isCorrectOpt = (corrOpt === oIdx);
                      let optClass = '';
                      if (isCorrectOpt) optClass = 'opt-is-correct';
                      else if (isSelected && !isCorrectOpt) optClass = 'opt-is-wrong';

                      return `
                        <div class="review-opt-row ${optClass}">
                          <span class="opt-tag">${letters[oIdx] || (oIdx + 1)}</span>
                          <span class="opt-text">${escapeHtml(opt)}</span>
                          ${isSelected ? '<span class="student-pick-tag">(توهان جو انتخاب)</span>' : ''}
                          ${isCorrectOpt ? '<span class="correct-pick-tag">(درست جواب)</span>' : ''}
                        </div>
                      `;
                    }).join('')}
                  </div>

                  ${expl ? `
                    <div class="review-explanation-bar">
                      <strong>درسي وضاحت:</strong> ${escapeHtml(expl)}
                    </div>
                  ` : ''}
                  ${cit ? `
                    <div class="review-citation-bar">
                      📖 <strong>حوالو:</strong> ${escapeHtml(cit)}
                    </div>
                  ` : ''}
                </div>
              `;
            }).join('')}
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="results-actions-bar">
          <button type="button" class="btn-primary-action" onclick="openAssessmentHub()">
            🔄 نئون ڪوئز تيار ڪريو (Try Another Quiz)
          </button>
          <button type="button" class="btn-secondary-action" onclick="closeAssessmentModal()">
            ✖ بند ڪريو ۽ ڪلاس روم ڏسو
          </button>
        </div>
      </div>
    `;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

})();
