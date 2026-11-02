// Sindhi Digital Classroom (SDC) - Main Application Controller
// Complete RBAC Navigation, Curriculum Browsing, YouTube Integration & Offline Sync
// Authored under agency-frontend-developer, agency-application-security-engineer, and agency-backend-architect.

let currentUser = null;
window.currentUser = null;

let sdcPlayer = null;
let sdcTutor = null;
let currentLoadedLessonId = null;
let allLoadedCourses = [];
let allFlattenedLessons = [];
let completedLessonsSet = new Set();
window.completedLessonsSet = completedLessonsSet;
let activeClassLevel = 6;
let activeSubjectFilter = 'Science';

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

// Toast helper
window.showToast = function(msg) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const t = document.createElement('div');
  t.className = 'toast-msg';
  t.textContent = msg;
  container.appendChild(t);
  setTimeout(() => t.remove(), 4000);
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  const isLms = document.getElementById('lms-sidebar') || window.location.pathname.startsWith('/app');

  // Load saved session if available
  const savedUser = localStorage.getItem('sdc_current_user');
  if (savedUser) {
    try {
      currentUser = JSON.parse(savedUser);
      window.currentUser = currentUser;
    } catch (e) {
      localStorage.removeItem('sdc_current_user');
    }
  }

  // Enforce session boundary for protected LMS workspace
  if (isLms && (!currentUser || !currentUser.token)) {
    const nextTarget = window.location.pathname + window.location.search;
    window.location.href = `/login?next=${encodeURIComponent(nextTarget)}`;
    return;
  }

  // Setup Player & Tutor
  if (document.getElementById('sdc-video-player')) {
    sdcPlayer = new SDCVideoPlayer('sdc-video-player', 'quiz-popup-overlay');
    window.sdcPlayer = sdcPlayer;
  }

  if (document.getElementById('tutor-drawer')) {
    sdcTutor = new SDCAITutor('tutor-drawer');
    window.sdcTutor = sdcTutor;
  }

  // Setup Network Connectivity Monitoring
  setupConnectivityMonitoring();

  if (currentUser) {
    // Render Role-Gated Navigation & Header Badge
    updateHeaderUserDisplay();
    renderNavigationTabs();

    // Verify session token with backend (non-blocking for offline resilience)
    const activeToken = currentUser.token || currentUser.user_id;
    fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${activeToken}` }
    }).then(res => {
      if (!res.ok) {
        localStorage.removeItem('sdc_current_user');
        window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
      }
    }).catch(err => {
      console.log('[SDC PWA] Offline session retained for offline learning.');
    });

    // If student, immediately fetch their real progress metrics
    if (currentUser.role === 'STUDENT') {
      loadStudentDashboard();
    }

    // Handle initial route
    routeLmsByPath();
  }

  // Listen to browser navigation back/forward
  window.addEventListener('popstate', () => {
    if (isLms) routeLmsByPath();
  });

  // Background queue sync if online
  flushOfflineSyncQueue();

  // Register Service Worker for PWA Offline Caching
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
      .then(reg => console.log('[SDC PWA] Service Worker registered'))
      .catch(err => console.log('[SDC PWA] Service Worker registration note:', err));
  }
});

// Connectivity Monitoring
function setupConnectivityMonitoring() {
  const pill = document.getElementById('connectivity-pill');
  const text = document.getElementById('connectivity-text');
  const barSync = document.getElementById('bar-sync-status');

  async function checkOfflinePackSaved(lessonId) {
    if (!lessonId || typeof getOfflineUnitPack !== 'function') return false;
    try {
      const pack = await getOfflineUnitPack(lessonId);
      return !!pack;
    } catch (e) {
      return false;
    }
  }

  window.updateLessonMediaStatus = async function(lessonId, videoPlayableState = null) {
    const isOnline = navigator.onLine;
    const isPackSaved = await checkOfflinePackSaved(lessonId || currentLoadedLessonId);

    if (pill && text) {
      if (!isOnline) {
        pill.className = 'status-pill offline';
        text.textContent = 'آف لائن نيٽورڪ';
      } else {
        pill.className = 'status-pill online';
        text.textContent = 'آن لائن نيٽورڪ';
      }
    }

    if (barSync) {
      if (isPackSaved) {
        barSync.textContent = 'آف لائن پيڪ محفوظ ٿيل (Pack Saved)';
        barSync.style.color = 'var(--accent-emerald)';
      } else if (videoPlayableState === true) {
        barSync.textContent = isOnline ? 'وڊيو هلڻ لاءِ تيار (Video Ready)' : 'لوڪل وڊيو تيار';
        barSync.style.color = 'var(--accent-emerald)';
      } else if (videoPlayableState === false) {
        barSync.textContent = 'وڊيو غير دستياب (Video Unavailable)';
        barSync.style.color = 'var(--accent-rose)';
      } else {
        barSync.textContent = isOnline ? 'انٽرنيٽ فعال (Online)' : 'آف لائن موڊ (Offline)';
        barSync.style.color = isOnline ? 'var(--accent-primary)' : 'var(--accent-amber)';
      }
    }
  };

  function updateStatus() {
    window.updateLessonMediaStatus(currentLoadedLessonId, null);
  }

  window.addEventListener('online', () => {
    updateStatus();
    window.showToast('انٽرنيٽ بحال ٿيو! آف لائن رڪارڊ خودڪار سنڪ ٿي رهيا آهن...');
    flushOfflineSyncQueue();
  });

  window.addEventListener('offline', () => {
    updateStatus();
    window.showToast('انٽرنيٽ ڪٽجي ويو. آف لائن موڊ خودڪار فعال ٿي ويو.');
  });

  updateStatus();
}

// Update Header User Profile Badge
function updateHeaderUserDisplay() {
  if (!currentUser) return;
  const roleEl = document.getElementById('header-user-role');
  const schoolEl = document.getElementById('header-user-school');
  const avatarEl = document.getElementById('sidebar-user-avatar');
  
  const roleLabels = {
    'STUDENT': 'شاگرد (Student)',
    'ADMIN': 'ايڊمن (Admin)',
    'SUPER_ADMIN': 'ايڊمن (Admin)',
    'SCHOOL_ADMIN': 'ايڊمن (Admin)',
    'TEACHER': 'ايڊمن (Admin)',
    'CONTENT_REVIEWER': 'ايڊمن (Admin)',
    'DISTRICT_OFFICER': 'ايڊمن (Admin)'
  };

  const roleText = roleLabels[currentUser.role] || currentUser.role;
  if (roleEl) roleEl.innerHTML = `${escapeHtml(roleText)}: <span class="ltr-text" style="direction: ltr; font-weight: 800;">${escapeHtml(currentUser.pseudonymous_code || '')}</span>`;
  if (schoolEl) schoolEl.textContent = currentUser.school_name || 'سنڌ ايجوڪيشن اينڊ لٽريسي ڊپارٽمينٽ';
  if (avatarEl) {
    const initial = (currentUser.pseudonymous_code || 'U').charAt(0).toUpperCase();
    avatarEl.textContent = initial;
  }
}

// Render Role-Gated Navigation Tabs (Strict RBAC UI Guard)
function renderNavigationTabs() {
  const nav = document.getElementById('nav-tabs-container');
  if (!nav || !currentUser) return;

  const role = currentUser.role;
  let tabs = [];

  if (role === 'STUDENT') {
    tabs = [
      { id: 'pane-learn', path: '/app/learn', icon: 'book', label: 'سبق، Tutor ۽ ڪوئيز', default: true },
      { id: 'pane-student-dash', path: '/app/progress', icon: 'chart', label: 'منهنجي محفوظ ترقي' }
    ];
  } else if (role === 'SUPER_ADMIN' || role === 'ADMIN') {
    tabs = [
      { id: 'pane-school-admin', path: '/app/school', icon: 'users', label: 'شاگردن جي ترقي', default: true },
      { id: 'pane-super-admin', path: '/app/admin', icon: 'shield', label: 'سيڪيورٽي لاگ' }
    ];
  }

  nav.innerHTML = tabs.map(t => `
    <button class="lms-nav-item tab-btn ${t.default ? 'active' : ''}" data-tab="${t.id}" data-path="${t.path}">
      <svg class="sdc-icon sdc-icon-sm" aria-hidden="true"><use href="#icon-${t.icon || 'book'}"></use></svg>
      <span>${t.label}</span>
    </button>
  `).join('');

  // Attach tab switching events
  const tabBtns = nav.querySelectorAll('.lms-nav-item, .tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const clickedTab = btn.getAttribute('data-tab');
      if (clickedTab === 'pane-assessment-hub-tab') {
        if (typeof window.openAssessmentHub === 'function') {
          window.openAssessmentHub();
        }
        return;
      }
      const targetId = btn.getAttribute('data-tab');
      const targetPath = btn.getAttribute('data-path') || '/app';
      if (window.location.pathname !== targetPath) {
        history.pushState(null, '', targetPath);
      }
      activatePane(targetId, targetPath);
    });
  });
}

function activatePane(paneId, urlPath) {
  // Update button active state
  document.querySelectorAll('#nav-tabs-container .lms-nav-item, #nav-tabs-container .tab-btn').forEach(b => {
    if (b.getAttribute('data-tab') === paneId) {
      b.classList.add('active');
    } else {
      b.classList.remove('active');
    }
  });

  // Hide all panes
  document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
  const targetPane = document.getElementById(paneId);
  if (targetPane) targetPane.style.display = 'block';

  // Update Breadcrumb
  const breadcrumbEl = document.getElementById('breadcrumb-current-pane');
  if (breadcrumbEl) {
    const paneLabels = {
      'pane-learn': 'ڪلاس روم ۽ وڊيو (Learn)',
      'pane-sdc-classroom': 'سنڌ ٽيڪسٽ بڪ بورڊ نصابي اوزار (Curriculum Tools)',
      'pane-student-dash': 'سکيا جي ترقي (Progress)',
      'pane-student-assignments': 'هوم ورڪ (Homework)',
      'pane-teacher': 'سوالن جي منظوري (Approval Gate)',
      'pane-teacher-upload': 'سبق اپلوڊ (Upload Lesson)',
      'pane-teacher-assignments': 'گريڊنگ (Grading)',
      'pane-teacher-analytics': 'ڪلاس اينالائيٽڪس (Analytics)',
      'pane-reviewer': 'نصاب نظرثاني (Curriculum Approval)',
      'pane-youtube-catalog': 'يوٽيوب ڪئٽلاگ (YouTube Catalog)',
      'pane-school-admin': 'اسڪول يوزرس (School Users)',
      'pane-officer-dash': 'ضلعي مانيٽرنگ (District Telemetry)',
      'pane-super-admin': 'سيڪيورٽي لاگز (Audit Logs)',
      'pane-rag-course': 'RAG ۽ LLM اڪيڊمي (AI Course)'
    };
    breadcrumbEl.textContent = paneLabels[paneId] || 'ڊيش بورڊ';
  }

  // Update URL in browser history
  if (urlPath && window.location.pathname !== urlPath) {
    window.history.pushState({ pane: paneId }, '', urlPath);
  }

  // Close mobile sidebar if open
  const sidebar = document.getElementById('lms-sidebar');
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
  }

  // Lazy load tab data
  handleTabActivation(paneId);
}

function routeLmsByPath() {
  if (!currentUser) return;
  const path = window.location.pathname;
  const role = currentUser.role;
  if (!['STUDENT', 'ADMIN', 'SUPER_ADMIN'].includes(role)) {
    window.location.href = '/unauthorized';
    return;
  }

  // 1. Protected lesson classroom route: /app/learn/:lessonId
  const lessonMatch = path.match(/\/app\/learn\/(lesson-[a-zA-Z0-9_\-]+)/);
  if (lessonMatch) {
    const targetLessonId = lessonMatch[1];
    activatePane('pane-learn', '/app/learn');
    selectLesson(targetLessonId);
    return;
  }

  // 2. Section routing
  if (path === '/app/progress' && role === 'STUDENT') {
    activatePane('pane-student-dash', '/app/progress');
  } else if (path === '/app/progress') {
    window.history.replaceState({}, '', '/app/school');
    activateDefaultRolePane();
  } else if (path === '/app/tools' || path === '/app/classroom' || path === '/classroom') {
    activatePane('pane-sdc-classroom', '/app/tools');
  } else if (path === '/app/assignments') {
    window.history.replaceState({}, '', role === 'STUDENT' ? '/app/learn' : '/app/school');
    activateDefaultRolePane();
  } else if (path === '/app/tutor') {
    activatePane('pane-learn', '/app/tutor');
    const tutorDrawer = document.getElementById('tutor-drawer');
    if (tutorDrawer) tutorDrawer.scrollIntoView({ behavior: 'smooth' });
    const tutorInput = document.getElementById('tutor-question-input');
    if (tutorInput) tutorInput.focus();
  } else if (path.startsWith('/app/teacher') || path.startsWith('/app/reviewer') || path.startsWith('/app/district') || path.startsWith('/app/rag-course')) {
    window.history.replaceState({}, '', role === 'STUDENT' ? '/app/learn' : '/app/school');
    activateDefaultRolePane();
  } else if (path.startsWith('/app/school')) {
    if (role !== 'ADMIN' && role !== 'SUPER_ADMIN') {
      window.location.href = '/unauthorized';
      return;
    }
    activatePane('pane-school-admin', '/app/school');
  } else if (path.startsWith('/app/admin')) {
    if (role !== 'SUPER_ADMIN') {
      window.location.href = '/unauthorized';
      return;
    }
    activatePane('pane-super-admin', '/app/admin');
  } else {
    // Default entry for role
    activateDefaultRolePane();
  }
}

function activateDefaultRolePane() {
  if (!currentUser) return;
  const role = currentUser.role;
  if (role === 'STUDENT') {
    activatePane('pane-learn', '/app/learn');
    } else {
    activatePane('pane-school-admin', '/app/school');
  }
}

function toggleLmsSidebar() {
  const sidebar = document.getElementById('lms-sidebar');
  if (sidebar) sidebar.classList.toggle('open');
}

function handleTabActivation(tabId) {
  if (tabId === 'pane-learn') {
    if (!currentLoadedLessonId) loadCurriculum(activeClassLevel);
  } else if (tabId === 'pane-student-dash') {
    loadStudentDashboard();
  } else if (tabId === 'pane-student-assignments') {
    loadStudentAssignments();
  } else if (tabId === 'pane-teacher') {
    loadTeacherPendingQuestions();
  } else if (tabId === 'pane-teacher-assignments') {
    loadTeacherSubmissionsQueue();
  } else if (tabId === 'pane-teacher-analytics') {
    loadTeacherAnalytics();
  } else if (tabId === 'pane-reviewer') {
    loadReviewerQueue();
  } else if (tabId === 'pane-youtube-catalog') {
    loadYouTubeCatalog();
  } else if (tabId === 'pane-school-admin') {
    loadAdminStudentProgress();
  } else if (tabId === 'pane-officer-dash') {
    loadOfficerDashboard();
  } else if (tabId === 'pane-super-admin') {
    loadSuperAdminAuditLogs();
  } else if (tabId === 'pane-rag-course') {
    loadRAGCourseModules();
  } else if (tabId === 'pane-sdc-classroom') {
    initIntegratedClassroomTools();
  }
}

// =========================================================================
// SINDH ONLINE SCHOOL STEP-BY-STEP GUIDED FLOW CONTROLLER (FR-05)
// Authored under agency-ux-researcher, agency-ux-architect, agency-ui-designer
// Step 1: Select Class -> Step 2: Select Subject -> Step 3: Select Lesson
// =========================================================================
window.sosCurrentStep = 1;

function sosGoToStep(step) {
  window.sosCurrentStep = step;
  
  const p1 = document.getElementById('sos-panel-classes');
  const p2 = document.getElementById('sos-panel-subjects');
  const p3 = document.getElementById('sos-panel-lessons');
  
  if (p1) p1.style.display = (step === 1) ? 'block' : 'none';
  if (p2) p2.style.display = (step === 2) ? 'block' : 'none';
  if (p3) p3.style.display = (step === 3) ? 'block' : 'none';
  
  // Stepper buttons
  const b1 = document.getElementById('sos-step-btn-1');
  const b2 = document.getElementById('sos-step-btn-2');
  const b3 = document.getElementById('sos-step-btn-3');
  
  if (b1) {
    b1.classList.toggle('active', step === 1);
    b1.classList.toggle('completed', step > 1);
  }
  if (b2) {
    b2.classList.toggle('active', step === 2);
    b2.classList.toggle('completed', step > 2);
  }
  if (b3) {
    b3.classList.toggle('active', step === 3);
  }
  
  // Breadcrumb visibility
  const crumbSub = document.getElementById('sos-crumb-subject');
  const crumbSep = document.getElementById('sos-crumb-lesson-sep');
  const crumbLes = document.getElementById('sos-crumb-lesson');
  const btnBack = document.getElementById('sos-btn-back-step');
  
  if (crumbSub) crumbSub.style.display = (step >= 2) ? 'inline' : 'none';
  if (crumbSep) crumbSep.style.display = (step >= 3) ? 'inline' : 'none';
  if (crumbLes) crumbLes.style.display = (step >= 3) ? 'inline' : 'none';
  if (btnBack) btnBack.style.display = (step > 1) ? 'inline-flex' : 'none';
  
  // Auto-scroll to curriculum area when advancing steps
  const anchor = document.getElementById('curriculum-browser-anchor');
  if (anchor && step > 1) {
    anchor.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function sosChooseClass(classLevel, el) {
  activeClassLevel = classLevel;
  
  // Update class cards styling
  document.querySelectorAll('.sos-class-card').forEach(c => c.classList.remove('active'));
  if (el) el.classList.add('active');
  const card = document.getElementById(`sos-class-card-${classLevel}`);
  if (card) card.classList.add('active');
  
  // Update badges & labels
  const valClass = document.getElementById('sos-val-class');
  if (valClass) valClass.textContent = `ڪلاس ${classLevel}`;
  const crumbClass = document.getElementById('sos-crumb-class');
  if (crumbClass) crumbClass.textContent = classLevel;
  const tagClass = document.getElementById('sos-active-class-tag');
  if (tagClass) tagClass.textContent = `ڪلاس ${classLevel} جا مضمون`;
  
  // Load curriculum for this class level and advance to Step 2
  loadCurriculum(classLevel, null);
  sosGoToStep(2);
}

function sosChooseSubject(subject) {
  activeSubjectFilter = subject;
  
  const subTitle = (subject === 'Math') ? 'رياضي (Mathematics)'
    : (subject === 'Science') ? 'عام سائنس (General Science)'
    : (subject === 'Sindhi') ? 'سنڌي سليس (Sindhi)'
    : (subject === 'English') ? 'انگريزي (English)'
    : 'سڀ مضمون (All Subjects)';
    
  const valSub = document.getElementById('sos-val-subject');
  if (valSub) valSub.textContent = (subject === 'Math') ? 'رياضي' : (subject === 'Science' ? 'سائنس' : (subject || 'سڀ'));
  const crumbSub = document.getElementById('sos-crumb-subject');
  if (crumbSub) crumbSub.textContent = subTitle;
  
  // Sync Step 3 quick pills
  document.querySelectorAll('#subject-selector-pills .pill-btn').forEach(b => b.classList.remove('active'));
  const pillId = (subject === 'Math') ? 'pill-sub-math' 
    : (subject === 'Science') ? 'pill-sub-sci' 
    : (subject === 'Sindhi') ? 'pill-sub-sindhi' 
    : (subject === 'English') ? 'pill-sub-eng' 
    : 'pill-sub-all';
  const activePill = document.getElementById(pillId);
  if (activePill) activePill.classList.add('active');
  
  const panelTitle = document.getElementById('sos-lessons-panel-title');
  if (panelTitle) {
    panelTitle.textContent = `📖 ڪلاس ${activeClassLevel || 6} > ${subTitle} جا سبق`;
  }
  
  filterAndRenderCourses();
  sosGoToStep(3);

  // Auto-switch player & tutor to first lesson in chosen subject
  if (Array.isArray(allLoadedCourses)) {
    const chosenCourse = allLoadedCourses.find(c => c.subject && c.subject.toLowerCase() === subject.toLowerCase());
    if (chosenCourse && Array.isArray(chosenCourse.lessons) && chosenCourse.lessons.length > 0) {
      selectLesson(chosenCourse.lessons[0].id);
    }
  }
}

function sosGoBackOneStep() {
  if (window.sosCurrentStep === 3) {
    sosGoToStep(2);
  } else if (window.sosCurrentStep === 2) {
    sosGoToStep(1);
  }
}

// Backward-compatible wrappers for pills and direct calls
function selectClassLevel(level, btn) {
  sosChooseClass(level, btn);
}

function selectSubjectFilter(subject, btn) {
  sosChooseSubject(subject);
}

function filterCurriculumLessons(searchTerm) {
  filterAndRenderCourses(searchTerm);
}

async function loadCurriculum(classLevel = 6, subject = null) {
  const listEl = document.getElementById('curriculum-lessons-list');
  if (!listEl) return;
  listEl.innerHTML = '<div style="color: var(--text-dim); padding: 12px;">سبق لوڊ ٿي رهيا آهن...</div>';

  try {
    let url = `/api/lessons?class_level=${classLevel}`;
    if (subject) url += `&subject=${encodeURIComponent(subject)}`;
    const res = await fetch(url);
    const courses = await res.json();
    
    // Prioritize Science courses first (Primary pilot syllabus)
    courses.sort((a, b) => {
      if (a.subject.toLowerCase() === 'science') return -1;
      if (b.subject.toLowerCase() === 'science') return 1;
      return 0;
    });
    allLoadedCourses = courses;

    // Flatten all curriculum lessons across courses for sequential navigation
    allFlattenedLessons = [];
    allLoadedCourses.forEach(c => {
      if (Array.isArray(c.lessons)) {
        c.lessons.forEach(l => {
          allFlattenedLessons.push({
            ...l,
            course_subject: c.subject,
            course_title_sindhi: c.title_sindhi
          });
        });
      }
    });

    filterAndRenderCourses();

    // Auto-select lesson: prefer saved lesson or lesson-sci-6-1 or first science lesson
    if (!currentLoadedLessonId) {
      const savedLesson = localStorage.getItem('sdc_last_lesson_id');
      const scienceCourse = allLoadedCourses.find(c => c.subject.toLowerCase() === 'science') || allLoadedCourses[0];
      const targetLessonId = savedLesson 
        ? savedLesson 
        : (scienceCourse?.lessons[0]?.id || allLoadedCourses[0]?.lessons[0]?.id);
      
      if (targetLessonId) {
        selectLesson(targetLessonId);
      }
    }
  } catch (err) {
    listEl.innerHTML = '<div style="color: var(--accent-rose); padding: 12px;">سبق لوڊ ڪرڻ ۾ مسئلو آيو.</div>';
  }
}

function filterAndRenderCourses(searchTerm = '') {
  const listEl = document.getElementById('curriculum-lessons-list');
  if (!listEl) return;

  const term = searchTerm.trim().toLowerCase();
  let filtered = allLoadedCourses;

  if (activeSubjectFilter) {
    filtered = filtered.filter(c => c.subject.toLowerCase() === activeSubjectFilter.toLowerCase());
  }

  let html = '';
  let matchCount = 0;

  filtered.forEach(c => {
    let matchedLessons = c.lessons;
    if (term) {
      matchedLessons = matchedLessons.filter(l =>
        l.title_sindhi.toLowerCase().includes(term) ||
        (l.summary_sindhi && l.summary_sindhi.toLowerCase().includes(term)) ||
        l.title_english.toLowerCase().includes(term)
      );
    }

    if (matchedLessons.length > 0) {
      html += `
        <div style="grid-column: 1 / -1; margin-top: 14px; font-weight: 700; color: var(--accent-cyan); display: flex; justify-content: space-between;">
          <span>${escapeHtml(c.title_sindhi)}</span>
          <span style="font-size: 0.78rem; color: var(--text-dim);">${matchedLessons.length} سبق</span>
        </div>
      `;

      matchedLessons.forEach(l => {
        matchCount++;
        const isPlaying = l.id === currentLoadedLessonId;
        const isCompleted = completedLessonsSet.has(l.id);
        html += `
          <div class="lesson-card ${isPlaying ? 'active-playing' : ''}" onclick="selectLesson('${l.id}')" id="card-${l.id}" tabindex="0" role="button" aria-pressed="${isPlaying}">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span class="lesson-unit-tag">يونٽ ${l.unit_number}</span>
                ${isCompleted ? '<span class="lesson-completed-check">&#10004; مڪمل</span>' : ''}
              </div>
              <div class="lesson-title">${escapeHtml(l.title_sindhi)}</div>
              <div class="lesson-desc">${escapeHtml(l.summary_sindhi || '')}</div>
            </div>
            <div class="lesson-meta-bar">
              <span>&#9201; ${Math.round(l.duration_seconds / 60)} منٽ</span>
              <span class="stbb-verified-badge">&#10004; STBB تصديق ٿيل</span>
            </div>
          </div>
        `;
      });
    }
  });

  if (matchCount === 0) {
    listEl.innerHTML = '<div style="color: var(--text-muted); padding: 14px;">هن تلاش يا فلٽر مطابق ڪوبه سبق نه مليو.</div>';
  } else {
    listEl.innerHTML = html;
  }
}

// 2. Select and Load Lesson
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
    }

    // 3. Update titles
    const titleEl = document.getElementById('current-lesson-title');
    const unitEl = document.getElementById('current-lesson-unit');
    const engEl = document.getElementById('current-lesson-english');
    if (titleEl) titleEl.textContent = detail.title_sindhi;
    if (unitEl) unitEl.textContent = `يونٽ ${detail.unit_number}`;
    if (engEl) engEl.textContent = detail.title_english || '';

    // Update Sindh Online School style breadcrumbs
    const bcClass = document.getElementById('sos-bc-class');
    const bcSubject = document.getElementById('sos-bc-subject');
    const bcChapter = document.getElementById('sos-bc-chapter');
    const displayClass = activeClassLevel || 6;
    const isMath = (detail.course_id && detail.course_id.includes('math')) || (detail.id && detail.id.includes('math'));
    const displaySubject = isMath ? 'Math' : ((!activeSubjectFilter || activeSubjectFilter === 'ALL') ? 'Science' : activeSubjectFilter);
    if (bcClass) bcClass.textContent = `Class ${displayClass} (${displayClass === 6 ? 'ڇهون' : displayClass})`;
    if (bcSubject) bcSubject.textContent = isMath ? 'رياضي (Mathematics)' : `${displaySubject} (${displaySubject.toLowerCase() === 'science' ? 'جنرل سائنس' : displaySubject})`;
    if (bcChapter) bcChapter.textContent = `Chapter ${String(detail.unit_number).padStart(2, '0')} (${detail.title_english || detail.title_sindhi})`;

    // Update SOS Guided Stepper breadcrumb bar
    const crumbClass = document.getElementById('sos-crumb-class');
    if (crumbClass) crumbClass.textContent = displayClass;
    const crumbSub = document.getElementById('sos-crumb-subject');
    if (crumbSub) crumbSub.textContent = isMath ? 'رياضي (Mathematics)' : (displaySubject === 'Science' ? 'عام سائنس (General Science)' : displaySubject);
    const crumbSep = document.getElementById('sos-crumb-lesson-sep');
    if (crumbSep) crumbSep.style.display = 'inline';
    const crumbLes = document.getElementById('sos-crumb-lesson');
    if (crumbLes) {
      crumbLes.style.display = 'inline';
      crumbLes.textContent = detail.title_sindhi;
    }
    const valLes = document.getElementById('sos-val-lesson');
    if (valLes) valLes.textContent = detail.title_sindhi;

    // 4. Load into Video Player Component (Supports Local & YouTube)
    sdcPlayer.loadLesson(detail, questions);

    // 5. Update Tutor Quick Prompts & Context for the Selected Lesson
    updateLessonTutorContext(detail);

    // Synchronize AI Tutor drawer with active lesson
    if (window.sdcTutor && typeof window.sdcTutor.setActiveLesson === 'function') {
      window.sdcTutor.setActiveLesson(detail);
    }

    // Save as last viewed lesson in localStorage for continue learning
    localStorage.setItem('sdc_last_lesson_id', lessonId);

    // Update Mark as Watched button state
    const isCompleted = window.completedLessonsSet && window.completedLessonsSet.has(lessonId);
    const markBtn = document.getElementById('btn-mark-watched');
    const markLabel = document.getElementById('btn-mark-watched-label');
    if (markLabel) {
      markLabel.textContent = isCompleted ? '✔ مڪمل ٿيل (Watched)' : 'مڪمل قرار ڏيو (Mark as Watched)';
    }
    if (markBtn) {
      if (isCompleted) {
        markBtn.style.borderColor = 'var(--accent-emerald)';
        markBtn.style.color = 'var(--accent-emerald)';
        markBtn.style.background = 'var(--accent-emerald-soft, #ecfdf5)';
      } else {
        markBtn.style.borderColor = 'var(--border-subtle)';
        markBtn.style.color = 'var(--text-primary)';
        markBtn.style.background = 'var(--bg-card)';
      }
    }

    // Update sticky previous and next buttons state
    updateLessonNavigationControls(lessonId);

  } catch (err) {
    console.error('[SDC] Failed to load lesson detail:', err);
  }
}

function updateLessonTutorContext(lessonDetail) {
  if (!lessonDetail) return;
  const promptsBar = document.querySelector('.tutor-quick-prompts');
  if (!promptsBar) return;

  const unit = lessonDetail.unit_number || 1;
  const title = lessonDetail.title_sindhi || '';
  const isMath = (lessonDetail.course_id && lessonDetail.course_id.includes('math')) || (lessonDetail.id && lessonDetail.id.includes('math'));

  let prompts = [];
  if (isMath) {
    // Math Specific Starter Prompts
    if (unit === 1) {
      prompts = [
        { label: '🔢 سيٽ ڇا آهي؟', q: 'سيٽ جي تعريف ۽ ان جا بنيادي تصور سمجهايو.' },
        { label: '⭕ خالي سيٽ', q: 'خالي سيٽ (Null Set) ڇا کي چئجي ٿو ۽ ان جي نشاني ڇا آهي؟' },
        { label: '🌐 يونيورسل سيٽ', q: 'يونيورسل سيٽ ۽ ذيلي سيٽ (Subset) ۾ ڪهڙو فرق آهي؟' },
        { label: '∩ ٻن سيٽن جي گڏجاڻي', q: 'سيٽن جي يونين (Union) ۽ انٽرسيڪشن (Intersection) جا مثال ڏيو.' }
      ];
    } else if (unit === 2) {
      prompts = [
        { label: '➕ پورا عدد', q: 'پورا عدد (Whole Numbers) ڪهڙا آهن ۽ انهن جون خاصيتون ڇا آهن؟' },
        { label: '🔢 عددي پٽي', q: 'عددي پٽي (Number Line) تي عددن کي ڪيئن ڏيکاريو ويندو آهي؟' }
      ];
    } else if (unit === 3) {
      prompts = [
        { label: '✖️ جزا ۽ ضربينڊڙ', q: 'جزا (Factors) ۽ ضربينڊڙ (Multiples) ۾ ڪهڙو فرق آهي؟' },
        { label: '🔝 وڏي ۾ وڏو عام جزو (HCF)', q: 'HCF (وڏو عام جزو) ڪيئن معلوم ڪيو ويندو آهي؟' }
      ];
    } else if (unit === 4) {
      prompts = [
        { label: '➖ سڄا عدد (Integers)', q: 'سڄا عدد (Integers) ۽ واڌو/ڪاٽو عددن جا اصول سمجهايو.' }
      ];
    } else if (unit === 8) {
      prompts = [
        { label: '🔣 الجبرا جا اصول', q: 'الجبرا ۾ مٽجندڙ (Variables) ۽ مستقل (Constants) ڇا هوندا آهن؟' }
      ];
    } else if (unit === 10) {
      prompts = [
        { label: '📐 جاميٽري ۽ ڪنڊون', q: 'جاميٽري ۾ ڪنڊن (Angles) جا مختلف قسم ڪهڙا آهن؟' }
      ];
    } else {
      prompts = [
        { label: `🔢 ${title} جو تصور`, q: `${title} جو رياضي ۾ بنيادي تصور ۽ مثال سمجهايو.` },
        { label: `❓ فارمولا ۽ حل`, q: `هن يونٽ جا اهم فارمولا ۽ حل جا قدم ٻڌايو.` },
        { label: `📝 درسي مشق جو حل`, q: `هن سبق جي مشق جو پهريون سوال ڪيئن حل ڪجي؟` }
      ];
    }
  } else {
    // Science Specific Starter Prompts
    if (unit === 1) {
      prompts = [
        { label: '🔬 جيو گهرڙو ڇا آهي؟', q: 'جيو گهرڙو ڇا آهي ۽ ان جا مکيه حصا ڪهڙا آهن؟' },
        { label: '🔍 خوردبين جا حصا', q: 'خوردبين جا مکيه حصا ۽ ان جو ڪم ڇا آهي؟' },
        { label: '🌱 ٻوٽي ۽ جانور جو گهرڙو', q: 'ٻوٽي جي گهرڙي ۽ جانور جي گهرڙي ۾ ڪهڙو فرق آهي؟' }
      ];
    } else if (unit === 2) {
      prompts = [
        { label: '👁️ اک جا حصا', q: 'انساني اک جا مختلف حصا ۽ انهن جا ڪم ڪهڙا آهن؟' },
        { label: '👂 ڪن جي بناوٽ', q: 'ڪن جا ٽي مکيه حصا ڪهڙا آهن؟' },
        { label: '👃 سنگھڻ جو حس', q: 'نڪ ذريعي سنگھڻ جو عمل ڪيئن ٿئي ٿو؟' }
      ];
    } else if (unit === 3) {
      prompts = [
        { label: '🌿 فوٽوسنٿيسز جو عمل', q: 'ٻوٽن ۾ فوٽوسنٿيسز جو عمل ڪيئن ٿيندو آهي؟' },
        { label: '☀️ سج جي روشني ۽ ڪلوروفل', q: 'فوٽوسنٿيسز ۾ ڪلوروفل ۽ سج جي روشنيءَ جو ڪردار ڇا آهي؟' },
        { label: '💨 آڪسيجن جو نيڪال', q: 'ٻوٽا فوٽوسنٿيسز دوران ڪهڙي گيس خارج ڪندا آهن؟' }
      ];
    } else {
      prompts = [
        { label: `📖 هن سبق جو مکيه نڪتو`, q: `${title} جو بنيادي تصور ڇا آهي؟` },
        { label: `❓ اهم اصطلاح`, q: `هن سبق ۾ آيل اهم سائنسي اصطلاحن جي سمجهاڻي ڏيو.` },
        { label: `📝 خلاصو`, q: `هن سبق جو مختصر خلاصو ٻڌايو.` }
      ];
    }
  }

  promptsBar.innerHTML = prompts.map(p => `
    <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('${escapeHtml(p.q)}')">${escapeHtml(p.label)}</button>
  `).join('');
}


window.markCurrentLessonWatched = async function () {
  const lessonId = window.currentLoadedLessonId || (window.sdcPlayer && window.sdcPlayer.currentLesson && window.sdcPlayer.currentLesson.id);
  if (!lessonId) {
    if (window.showToast) window.showToast('مهرباني ڪري پهريان ڪو سبق چونڊيو.');
    return;
  }
  const lesson = window.currentLoadedLesson || (window.sdcPlayer && window.sdcPlayer.currentLesson);
  const duration = (window.sdcPlayer && window.sdcPlayer.getCurrentDuration && window.sdcPlayer.getCurrentDuration()) || (lesson && lesson.duration_seconds) || 600;

  if (window.sdcPlayer && typeof window.sdcPlayer.saveProgress === 'function') {
    await window.sdcPlayer.saveProgress(duration, true);
  } else {
    const token = (currentUser && (currentUser.token || currentUser.user_id)) || localStorage.getItem('sdc_token');
    try {
      await fetch('/api/lessons/' + lessonId + '/progress', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({
          lesson_id: lessonId,
          position_seconds: duration,
          is_completed: true
        })
      });
      if (!window.completedLessonsSet) window.completedLessonsSet = new Set();
      window.completedLessonsSet.add(lessonId);
      if (typeof filterAndRenderCourses === 'function') filterAndRenderCourses();
    } catch(e) {}
  }
  if (window.showToast) {
    window.showToast('🎉 سبق ڪاميابيءَ سان مڪمل طور رڪارڊ ٿي ويو.');
  }
};

function updateLessonNavigationControls(currentId) {
  const prevBtn = document.getElementById('btn-prev-lesson');
  const nextBtn = document.getElementById('btn-next-lesson');
  const indexEl = document.getElementById('lesson-index-indicator');

  if (!allFlattenedLessons || allFlattenedLessons.length === 0) {
    if (prevBtn) prevBtn.disabled = true;
    if (nextBtn) nextBtn.disabled = true;
    return;
  }

  const idx = allFlattenedLessons.findIndex(l => l.id === currentId);
  if (idx === -1) {
    if (prevBtn) prevBtn.disabled = true;
    if (nextBtn) nextBtn.disabled = true;
    return;
  }

  if (prevBtn) {
    prevBtn.disabled = (idx <= 0);
    prevBtn.title = idx > 0 ? `پويون سبق: ${allFlattenedLessons[idx - 1].title_sindhi}` : 'هي پهريون سبق آهي';
  }

  if (nextBtn) {
    nextBtn.disabled = (idx >= allFlattenedLessons.length - 1);
    nextBtn.title = idx < allFlattenedLessons.length - 1 ? `اڳيون سبق: ${allFlattenedLessons[idx + 1].title_sindhi}` : 'هي آخري سبق آهي';
  }

  if (indexEl) {
    indexEl.textContent = `سبق ${idx + 1} مان ${allFlattenedLessons.length}`;
  }
}

function navigateToNextLesson() {
  if (!allFlattenedLessons || allFlattenedLessons.length === 0) return;
  const idx = allFlattenedLessons.findIndex(l => l.id === currentLoadedLessonId);
  if (idx !== -1 && idx < allFlattenedLessons.length - 1) {
    const nextLesson = allFlattenedLessons[idx + 1];
    selectLesson(nextLesson.id);
    window.showToast(`اڳيون سبق لوڊ ٿيو: ${nextLesson.title_sindhi}`);
  }
}

function navigateToPrevLesson() {
  if (!allFlattenedLessons || allFlattenedLessons.length === 0) return;
  const idx = allFlattenedLessons.findIndex(l => l.id === currentLoadedLessonId);
  if (idx > 0) {
    const prevLesson = allFlattenedLessons[idx - 1];
    selectLesson(prevLesson.id);
    window.showToast(`پويون سبق لوڊ ٿيو: ${prevLesson.title_sindhi}`);
  }
}

function toggleOrientationBanner() {
  const content = document.getElementById('orientation-steps-content');
  const btn = document.getElementById('orientation-toggle-btn');
  if (!content) return;
  const isHidden = content.style.display === 'none';
  content.style.display = isHidden ? 'grid' : 'none';
  if (btn) {
    btn.innerHTML = isHidden ? '<span>سمجھاڻي لڪايو</span> &#9650;' : '<span>سمجھاڻي ڏسو</span> &#9660;';
    btn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
  }
}

function resumeLastLesson() {
  const lastLessonId = localStorage.getItem('sdc_last_lesson_id') || 'lesson-sci-6-1';
  selectLesson(lastLessonId);
}

function scrollToTutor() {
  const drawer = document.getElementById('tutor-drawer');
  if (drawer) {
    drawer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const input = document.getElementById('tutor-question-input');
    if (input) {
      setTimeout(() => input.focus(), 350);
    }
  }
}

// 3. Download Unit Pack for Offline Use (FR-32)
async function downloadCurrentUnitOffline() {
  if (!currentLoadedLessonId) return;
  const btn = document.getElementById('btn-download-offline');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'ڊائونلوڊ ٿي رهيو آهي...';
  }

  try {
    const res = await fetch(`/api/sync/unit-pack/${currentLoadedLessonId}`);
    const pack = await res.json();

    if (typeof saveUnitPackOffline === 'function') {
      await saveUnitPackOffline(pack);
    }
    window.showToast('يونٽ پيڪ مڪمل طور تي آف لائن محفوظ ٿي ويو! هاڻي بغير انٽرنيٽ پڙهو.');
  } catch (err) {
    window.showToast('آف لائن پيڪ ڊائونلوڊ ناڪام ٿيو.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '&#128190; آف لائن پيڪ محفوظ ڪريو';
    }
  }
}

let currentStudentDashboardData = null;

// 4. Student Dashboard & Streak (FR-29)
window.switchDashboardSubject = function (subject) {
  activeSubjectFilter = subject;
  window.activeSubjectFilter = subject;
  const courseId = (subject === 'Math' || subject === 'Mathematics') ? 'crs-math-6' : 'crs-sci-6';
  window.activeCourseId = courseId;
  const btnSci = document.getElementById('dash-tab-sci');
  const btnMath = document.getElementById('dash-tab-math');
  if (btnSci && btnMath) {
    if (courseId === 'crs-math-6') {
      btnMath.classList.add('active');
      btnSci.classList.remove('active');
    } else {
      btnSci.classList.add('active');
      btnMath.classList.remove('active');
    }
  }
  loadStudentDashboard(courseId);
};

async function loadStudentDashboard(targetCourseId = null) {
  try {
    const token = currentUser.token || currentUser.user_id;
    let currentCourseId = targetCourseId;
    if (!currentCourseId) {
      if (window.activeCourseId) {
        currentCourseId = window.activeCourseId;
      } else if (activeSubjectFilter === 'Math' || activeSubjectFilter === 'Mathematics') {
        currentCourseId = 'crs-math-6';
      } else {
        currentCourseId = 'crs-sci-6';
      }
    }
    window.activeCourseId = currentCourseId;

    const res = await fetch(`/api/dashboards/student?course_id=${encodeURIComponent(currentCourseId)}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    currentStudentDashboardData = data;

    const compEl = document.getElementById('stat-completed-lessons');
    const compScopeLabel = document.getElementById('stat-completed-scope-label');
    const compTotalSub = document.getElementById('stat-completed-total-sub');
    const scoreEl = document.getElementById('stat-quiz-score');
    const scoreAttemptsSub = document.getElementById('stat-quiz-attempts-sub');
    const streakEl = document.getElementById('stat-streak-days');
    const streakSub = document.getElementById('stat-streak-sub');
    const barStreak = document.getElementById('bar-streak-days');
    const barComp = document.getElementById('bar-completed-count');
    const barScore = document.getElementById('bar-quiz-accuracy');

    const streakCount = typeof data.active_streak_days === 'number' ? data.active_streak_days : 0;
    const compCount = data.completed_lessons_count || 0;
    const courseCompCount = typeof data.course_completed_count === 'number' ? data.course_completed_count : compCount;
    const courseTotalCount = typeof data.course_total_count === 'number' ? data.course_total_count : (data.enrolled_lessons ? data.enrolled_lessons.length : 0);
    const scoreVal = typeof data.total_quiz_score_pct === 'number' ? Math.round(data.total_quiz_score_pct) : 0;

    const totalAttempts = typeof data.total_quiz_attempts === 'number' ? data.total_quiz_attempts : (data.recent_attempts ? data.recent_attempts.length : 0);
    const hasAttempts = totalAttempts > 0;

    const subjectSindhi = data.course_subject === 'Science' ? 'سائنس' : (data.course_subject === 'Math' ? 'حساب' : (data.course_subject === 'Sindhi' ? 'سنڌي' : (data.course_subject === 'English' ? 'انگريزي' : (data.course_subject || 'مضمون'))));

    if (compScopeLabel) compScopeLabel.textContent = `ڪلاس ${data.class_level || 6} ${subjectSindhi} مڪمل`;
    if (compEl) compEl.textContent = `${courseCompCount} / ${courseTotalCount} سبق`;
    if (compTotalSub) compTotalSub.textContent = `سمورن ڪورسن ۾ ڪل مڪمل: ${compCount} سبق`;
    if (scoreEl) scoreEl.textContent = hasAttempts ? `${scoreVal}%` : 'اڃا ڪوئيز ناهي';
    if (scoreAttemptsSub) scoreAttemptsSub.textContent = hasAttempts ? `${totalAttempts} سوال حل ڪيا` : 'پهرين سوال جي ڪوشش ڪريو';
    if (streakEl) streakEl.textContent = streakCount > 0 ? `${streakCount} ڏينهن \u{1F525}` : '0 ڏينهن';
    if (streakSub) streakSub.textContent = streakCount > 0 ? `${data.streak_badge_sindhi || 'مسلسل سکيا'}` : 'اڄ ئي سکيا جو آغاز ڪريو';
    if (barStreak) barStreak.textContent = streakCount > 0 ? `${streakCount} ڏينهن` : '0 ڏينهن (شروع ڪريو)';
    if (barComp) barComp.textContent = `${courseCompCount} سبق`;
    if (barScore) barScore.textContent = hasAttempts ? `${scoreVal}%` : 'اڃا ناهي';

    // Populate Next Step / Recommended Lesson Action Card
    const nextLessonContainer = document.getElementById('student-next-lesson-content');
    if (nextLessonContainer) {
      if (data.next_recommended_lesson) {
        const nl = data.next_recommended_lesson;
        nextLessonContainer.innerHTML = `
          <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 8px;">
            <div style="font-size: 0.76rem; color: var(--accent-primary); font-weight: 700; margin-bottom: 2px;">يونٽ ${nl.unit_number || '1'} &bull; ${escapeHtml(nl.title_english || '')}</div>
            <div style="font-weight: 800; font-size: 0.95rem; color: var(--text-primary); margin-bottom: 6px;">${escapeHtml(nl.title_sindhi)}</div>
            <div style="font-size: 0.78rem; color: var(--text-muted); line-height: 1.4; margin-bottom: 10px;">${escapeHtml(nl.summary_sindhi || '')}</div>
            <button class="btn-ctrl active" onclick="selectLesson('${nl.id}'); activatePane('pane-learn', '/app/learn');" style="width: 100%; justify-content: center; font-size: 0.82rem; padding: 7px;">
              <span>سبق شروع ڪريو &rarr;</span>
            </button>
          </div>
        `;
      } else {
        nextLessonContainer.innerHTML = '<div style="color: var(--accent-emerald); font-size: 0.82rem; padding: 6px 0;">🎉 اوهان سمورا سبق مڪمل ڪري چڪا آهيو!</div>';
      }
    }

    // Populate Last Activity Status Card
    const lastActContainer = document.getElementById('student-last-activity-content');
    const lastActBadge = document.getElementById('student-last-act-badge');
    if (lastActContainer) {
      if (data.last_activity) {
        const la = data.last_activity;
        const actLabel = la.type === 'QUIZ' ? 'ڪوئيز سوال حل ڪيو' : 'سبق پڙهيو';
        const dateStr = la.timestamp ? la.timestamp.replace('T', ' ').split('.')[0] : 'تازو';
        if (lastActBadge) lastActBadge.textContent = la.type === 'QUIZ' ? 'ڪوئيز' : 'سبق';
        lastActContainer.innerHTML = `
          <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">${escapeHtml(la.title || 'سرگرمي')}</div>
          <div style="font-size: 0.78rem; color: var(--text-muted);">${actLabel} &bull; <span dir="ltr">${escapeHtml(dateStr)}</span></div>
        `;
      } else {
        if (lastActBadge) lastActBadge.textContent = 'نئون';
        lastActContainer.innerHTML = '<div style="color: var(--text-dim); font-size: 0.8rem;">اڃا ڪابه سرگرمي رڪارڊ ناهي ٿي. پنهنجو پهريون سبق شروع ڪريو!</div>';
      }
    }

    // Populate completed lessons set for global LMS badges
    completedLessonsSet.clear();
    if (Array.isArray(data.enrolled_lessons)) {
      data.enrolled_lessons.forEach(l => {
        if (l.is_completed) {
          completedLessonsSet.add(l.lesson_id);
        }
      });
    }

    // If curriculum cards are already loaded, refresh their completed checks
    if (allLoadedCourses && allLoadedCourses.length > 0) {
      filterAndRenderCourses();
    }

    // Render real enrolled lessons
    renderStudentDashboardLessons('all');

    // Render weekly activity chart bars
    const chartBars = document.getElementById('student-weekly-chart-bars');
    if (chartBars && data.weekly_activity && data.weekly_activity.length > 0) {
      const maxCount = Math.max(...data.weekly_activity.map(w => w.count), 1);
      chartBars.innerHTML = data.weekly_activity.map(w => {
        const heightPct = Math.max(Math.round((w.count / maxCount) * 100), 12);
        const isPeak = w.count > 0 && w.count === maxCount;
        const dayShort = w.day === 'سومر' ? 'سو' : (w.day === 'اڱارو' ? 'اڱ' : (w.day === 'اربع' ? 'ار' : (w.day === 'خميس' ? 'خم' : (w.day === 'جمعو' ? 'جم' : (w.day === 'ڇنڇر' ? 'ڇن' : 'آچ')))));
        return `
          <div class="lisa-bar-col" title="${escapeHtml(w.day)}: ${w.count} حل ڪيل سوال">
            <div class="lisa-bar-pill ${isPeak ? 'peak' : ''}" style="height: ${heightPct}%;"></div>
            <div class="lisa-bar-label" ${isPeak ? 'style="color: var(--accent-primary); font-weight: 800;"' : ''}>${escapeHtml(dayShort)}</div>
          </div>
        `;
      }).join('');
    }

    // Render recent attempts table
    const tableBody = document.getElementById('student-attempts-table-body');
    if (tableBody && data.recent_attempts) {
      if (data.recent_attempts.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-dim); padding: 14px;">اڃا ڪوبه ڪوئيز حل ناهي ڪيو ويو. سبق شروع ڪريو!</td></tr>';
      } else {
        tableBody.innerHTML = data.recent_attempts.map(a => `
          <tr>
            <td><strong>${escapeHtml(a.topic || 'سبق ڪوئيز')}</strong></td>
            <td>آپشن ${a.selected_option !== undefined ? (a.selected_option + 1) : '-'}</td>
            <td>${a.is_correct ? '<span style="color: var(--accent-emerald); font-weight: 700;">&#10004; درست</span>' : '<span style="color: var(--accent-rose); font-weight: 700;">&#10008; غلط</span>'}</td>
            <td style="font-size: 0.78rem; color: var(--text-dim);">${a.created_at ? a.created_at.split('T')[0] : ''}</td>
          </tr>
        `).join('');
      }
    }
  } catch (e) {
    console.warn('[SDC] Student dashboard load note:', e);
  }
}

function filterStudentDashboardLessons(filterType, btn) {
  if (btn) {
    document.querySelectorAll('#student-lessons-filter-bar .lisa-tab-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }
  renderStudentDashboardLessons(filterType);
}

function renderStudentDashboardLessons(filterType = 'all') {
  const container = document.getElementById('student-lessons-container');
  if (!container || !currentStudentDashboardData) return;

  const lessons = currentStudentDashboardData.enrolled_lessons || [];
  let filtered = lessons;

  if (filterType === 'in_progress') {
    filtered = lessons.filter(l => !l.is_completed && l.last_position_seconds > 5);
  } else if (filterType === 'completed') {
    filtered = lessons.filter(l => l.is_completed);
  } else if (filterType === 'planned') {
    filtered = lessons.filter(l => !l.is_completed && l.last_position_seconds <= 5);
  }

  if (filtered.length === 0) {
    container.innerHTML = '<div style="color: var(--text-dim); padding: 16px; text-align: center;">هن زمري ۾ ڪوبه سبق ناهي.</div>';
    return;
  }

  container.innerHTML = filtered.map(l => {
    const isComp = l.is_completed;
    const isProg = !isComp && l.last_position_seconds > 5;
    const tagClass = isComp ? 'var(--accent-emerald)' : (isProg ? 'var(--accent-amber)' : 'var(--text-muted)');
    
    return `
      <div class="lisa-lesson-card" onclick="selectLesson('${l.lesson_id}'); activatePane('pane-learn', '/app/learn');" style="cursor: pointer;">
        <div class="lisa-icon-box science" style="background: ${isComp ? 'rgba(5, 150, 105, 0.12)' : 'rgba(37, 99, 235, 0.12)'};">
          <span style="font-size: 1.4rem;">${isComp ? '✅' : (isProg ? '▶️' : '📖')}</span>
        </div>
        <div class="lisa-card-content">
          <div class="lisa-card-header">
            <div class="lisa-card-title">${escapeHtml(l.title_sindhi)}</div>
            <span style="font-size: 0.76rem; font-weight: 700; color: ${tagClass};">${escapeHtml(l.status_label)}</span>
          </div>
          <div class="lisa-card-desc">${escapeHtml(l.summary_sindhi || l.title_english || '')}</div>
          <div class="lisa-card-footer">
            <div class="lisa-tags">
              <span class="lisa-tag">يونٽ ${l.unit_number}</span>
              <span class="lisa-tag">ڪلاس 6</span>
              <span class="lisa-tag">عام سائنس</span>
            </div>
            <div class="lisa-progress-ahead" style="color: var(--accent-primary); font-weight: 700;">
              ${isComp ? 'مڪمل ٿيل ✔' : (isProg ? `${Math.round(l.last_position_seconds)}s وڊيو ڏٺل` : 'سبق پڙهو →')}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// 5. Student Assignments (AI-Managed Homework Lifecycle)
async function loadStudentAssignments() {
  const container = document.getElementById('student-assignments-list');
  if (!container) return;
  container.innerHTML = '<div style="color: var(--text-dim); padding: 12px;">لوڊ ٿي رهيو آهي...</div>';

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/assignments', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const assignments = await res.json();

    if (!assignments || assignments.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); padding: 14px;">هن وقت ڪابه نئين اسائينمينٽ باقي ناهي.</div>';
      return;
    }

    container.innerHTML = assignments.map(a => {
      let statusTag = '';
      if (a.my_submission) {
        if (a.my_submission.is_graded) {
          statusTag = '<span style="padding: 4px 10px; background: var(--accent-emerald-soft); color: var(--accent-emerald); border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">جاچيل (Graded) &#10004;</span>';
        } else if (a.my_submission.grading_status === 'NEEDS_RETRY') {
          statusTag = '<span style="padding: 4px 10px; background: rgba(245,158,11,0.15); color: var(--accent-amber); border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">خودڪار تصديق باقي (Needs Retry)</span>';
        } else {
          statusTag = '<span style="padding: 4px 10px; background: var(--accent-cyan-soft); color: var(--accent-cyan); border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">جمع ٿيل (Submitted)</span>';
        }
      } else if (a.is_overdue) {
        statusTag = '<span style="padding: 4px 10px; background: rgba(244,63,94,0.15); color: var(--accent-rose); border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">مدو ختم (Overdue)</span>';
      } else {
        statusTag = '<span style="padding: 4px 10px; background: rgba(59,130,246,0.15); color: #3b82f6; border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">دستياب (Available)</span>';
      }

      const questionsHtml = a.questions && a.questions.length > 0 ? `
        <div style="margin: 12px 0; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 12px;">
          <div style="font-size: 0.82rem; font-weight: 700; color: var(--accent-cyan); margin-bottom: 8px;">سوالن جي فهرست (Question Sheet):</div>
          ${a.questions.map((q, idx) => `
            <div style="margin-bottom: 8px; font-size: 0.85rem; color: var(--text-primary);">
              <strong>سوال ${idx + 1} (${q.question_type}):</strong> ${escapeHtml(q.question_text_sindhi)}
              <span style="font-size: 0.75rem; color: var(--text-dim); margin-right: 6px;">[${q.max_marks} مارڪون]</span>
              ${q.options ? `<div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">آپشنز: ${q.options.map(escapeHtml).join(' | ')}</div>` : ''}
            </div>
          `).join('')}
        </div>
      ` : '';

      const sourceCitationHtml = a.source_reference ? `
        <div style="font-size: 0.75rem; color: var(--text-dim); margin-bottom: 8px;">
          &#128218; نصاب حوالو: ${escapeHtml(a.source_reference)}
        </div>
      ` : '';

      return `
        <div class="glass-card" style="margin-bottom: 14px; padding: 18px;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
              <h3 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary);">${escapeHtml(a.title_sindhi)}</h3>
              <span style="font-size: 0.78rem; color: var(--accent-primary);">آخري تاريخ: ${a.due_date.substring(0, 10)} | ڪل مارڪون: ${a.max_marks}</span>
            </div>
            ${statusTag}
          </div>
          <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 8px;">${escapeHtml(a.description_sindhi)}</p>
          ${sourceCitationHtml}
          ${questionsHtml}

          ${a.my_submission ? `
            <div style="background: var(--bg-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 12px; margin-top: 10px;">
              <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px;">توهان جو جمع ڪيل جواب:</div>
              <div style="font-size: 0.88rem; color: var(--text-primary); margin-bottom: 8px;">${escapeHtml(a.my_submission.submission_text)}</div>
              ${a.my_submission.is_graded ? `
                <div style="border-top: 1px solid var(--border-glass); padding-top: 8px; color: var(--accent-emerald); font-weight: 700; font-size: 0.85rem;">
                  حاصل ڪيل مارڪون: ${a.my_submission.marks_awarded} / ${a.max_marks}
                  <div style="font-size: 0.8rem; font-weight: normal; color: var(--text-secondary); margin-top: 4px;">خودڪار تصديق ٿيل تبصرو: ${escapeHtml(a.my_submission.teacher_feedback || 'شاباس')}</div>
                  ${a.my_submission.grading_details ? `
                    <div style="margin-top: 6px; font-size: 0.75rem; color: var(--text-dim); font-weight: normal;">
                      ${a.my_submission.grading_details.map(gd => `<div>&bull; ${gd.question_id}: ${gd.marks_awarded}/${gd.max_marks} (${escapeHtml(gd.feedback_sindhi)})</div>`).join('')}
                    </div>
                  ` : ''}
                </div>
              ` : '<div style="font-size: 0.78rem; color: var(--accent-amber);">اي آءِ خودڪار تصديق ۽ گريڊنگ جاري آهي (AI Autonomous Grading in progress)...</div>'}
            </div>
          ` : `
            <form onsubmit="event.preventDefault(); submitStudentAssignmentResponse('${a.id}', this);">
              <textarea class="chat-input" placeholder="پنهنجو جواب هتي لکو (تمام سوالن جا حل يا نمبر وار جواب)..." required style="width: 100%; height: 85px; margin-bottom: 8px;"></textarea>
              <button type="submit" class="btn-ctrl active">&#10004; اسائينمينٽ جمع ڪرايو (Submit to AI Tutor)</button>
            </form>
          `}
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = '<div style="color: var(--accent-rose); padding: 12px;">اسائينمينٽس لوڊ ڪرڻ ۾ مسئلو آيو.</div>';
  }
}


async function studentRequestAIHomework() {
  const unitSelect = document.getElementById('student-ai-hw-unit');
  const unitNum = unitSelect ? parseInt(unitSelect.value, 10) : 1;

  if (window.showToast) window.showToast('اي آءِ درسي ڪتاب مان نئون هوم ورڪ تيار ڪري رهيو آهي...');

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/assignments/ai/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        class_level: 6,
        subject: 'Science',
        unit_number: unitNum,
        question_count: 4,
        auto_publish: true
      })
    });

    if (res.ok) {
      if (window.showToast) window.showToast('نئون هوم ورڪ ڪاميابيءَ سان جاري ٿيو!');
      loadStudentAssignments();
    } else {
      const err = await res.json().catch(() => ({}));
      if (window.showToast) window.showToast(err.detail || 'هوم ورڪ ٺاهڻ ۾ مسئلو آيو.');
    }
  } catch (e) {
    if (window.showToast) window.showToast('نيٽ ورڪ يا سرور ايرر.');
  }
}

async function submitStudentAssignmentResponse(asgId, form) {
  const textarea = form.querySelector('textarea');
  const text = textarea ? textarea.value.trim() : '';
  if (!text) return;

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch(`/api/assignments/${asgId}/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ submission_text: text })
    });
    if (res.ok) {
      window.showToast('اسائينمينٽ ڪاميابيءَ سان جمع ٿي وئي! اي آءِ فوري تصديق ڪري رهيو آهي.');
      loadStudentAssignments();
    } else {
      window.showToast('جمع ڪرائڻ ناڪام ٿيو.');
    }
  } catch (e) {
    window.showToast('ايرر آيو.');
  }
}

// 6. Teacher Question Approval Gate (FR-13 Gate)
async function loadTeacherPendingQuestions() {
  const container = document.getElementById('teacher-approval-list');
  if (!container) return;
  container.innerHTML = '<div style="color: var(--text-dim); padding: 12px;">لوڊ ٿي رهيو آهي...</div>';

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/quiz/pending', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const questions = await res.json();

    if (!questions || questions.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); padding: 14px;">منظوريءَ لاءِ ڪوبه نئون سوال باقي ناهي. تمام سوال منظور ٿيل آهن (All questions approved).</div>';
      return;
    }

    container.innerHTML = `
      <table class="sdc-table">
        <thead>
          <tr>
            <th>سبق ۽ موضوع</th>
            <th>سوال جي عبارت (Sindhi)</th>
            <th>آپشنز</th>
            <th>عمل (Action)</th>
          </tr>
        </thead>
        <tbody>
          ${questions.map(q => `
            <tr id="row-${q.id}">
              <td><strong>${escapeHtml(q.topic)}</strong><br><span style="font-size: 0.75rem; color: var(--text-dim);">${Math.round(q.timestamp_seconds)}s</span></td>
              <td>${escapeHtml(q.text_sindhi)}</td>
              <td><span style="font-size: 0.8rem; color: var(--text-muted);">${q.options.map(escapeHtml).join(' | ')}</span></td>
              <td>
                <button class="btn-ctrl active" onclick="teacherReviewQuestion('${q.id}', 'APPROVED')">&#10004; منظور ڪريو</button>
                <button class="btn-ctrl" onclick="teacherReviewQuestion('${q.id}', 'REJECTED')" style="color: var(--accent-rose); border-color: rgba(244,63,94,0.3);">&#10008; رد ڪريو</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    container.innerHTML = '<div style="color: var(--accent-rose); padding: 12px;">پينڊنگ سوال لوڊ ڪرڻ ۾ ايرر آيو.</div>';
  }
}

async function teacherReviewQuestion(questionId, status) {
  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch(`/api/quiz/${questionId}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ status: status })
    });
    if (res.ok) {
      window.showToast(`سوال ڪاميابيءَ سان ${status === 'APPROVED' ? 'منظور' : 'رد'} ڪيو ويو.`);
      const row = document.getElementById(`row-${questionId}`);
      if (row) row.remove();
    }
  } catch (err) {
    window.showToast('منظوري ناڪام ٿي.');
  }
}

// 7. Teacher Upload Lesson & Media (FR-09)
async function teacherSubmitLessonUpload() {
  const courseId = document.getElementById('upload-course-id').value;
  const unitNum = parseInt(document.getElementById('upload-unit-num').value) || 2;
  const titleSindhi = document.getElementById('upload-title-sindhi').value.trim();
  const titleEng = document.getElementById('upload-title-english').value.trim() || 'STBB Lesson';
  const summarySindhi = document.getElementById('upload-summary-sindhi').value.trim();
  const fileInput = document.getElementById('upload-video-file');

  if (!titleSindhi) {
    window.showToast('مهرباني ڪري سبق جو سنڌي عنوان لکو.');
    return;
  }

  const btn = document.getElementById('btn-submit-upload');
  if (btn) { btn.disabled = true; btn.textContent = 'اپلوڊ ٿي رهيو آهي...'; }

  try {
    const token = currentUser.token || currentUser.user_id;
    // Step 1: Create lesson metadata
    const res = await fetch('/api/lessons/upload', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        course_id: courseId,
        unit_number: unitNum,
        title_sindhi: titleSindhi,
        title_english: titleEng,
        summary_sindhi: summarySindhi,
        duration_seconds: 600
      })
    });

    if (!res.ok) {
      window.showToast('سبق اپلوڊ ناڪام ٿيو.');
      return;
    }
    const newLesson = await res.json();

    // Step 2: Upload video binary file if selected
    if (fileInput && fileInput.files && fileInput.files[0]) {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);

      const vidRes = await fetch(`/api/lessons/${newLesson.id}/video-file`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if (vidRes.ok) {
        window.showToast('سبق ۽ وڊيو ڪاميابيءَ سان اپلوڊ ٿي ويا!');
      } else {
        window.showToast('سبق محفوظ ٿيو پر وڊيو اپلوڊ ۾ ايرر آيو.');
      }
    } else {
      window.showToast('سبق ڪاميابيءَ سان شامل ڪيو ويو!');
    }

    document.getElementById('form-teacher-upload').reset();
    loadCurriculum(activeClassLevel);

  } catch (err) {
    window.showToast('اپلوڊ ڪرڻ ۾ ايرر آيو.');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = '&#10004; سبق ۽ وڊيو محفوظ ڪريو (Save Lesson)'; }
  }
}

// 8. Teacher Submissions & Analytics
async function loadTeacherSubmissionsQueue() {
  const container = document.getElementById('teacher-submissions-queue');
  if (!container) return;
  container.innerHTML = '<div style="color: var(--text-dim); padding: 10px;">لوڊ ٿي رهيو آهي...</div>';

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/assignments', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const assignments = await res.json();

    if (!assignments || assignments.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); padding: 10px;">ڪابه اسائينمينٽ ناهي ٺهيل.</div>';
      return;
    }

    let html = '';
    for (const a of assignments) {
      html += `
        <div style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 10px; box-shadow: var(--shadow-card);">
          <div style="font-weight: 700; color: var(--text-primary);">${escapeHtml(a.title_sindhi)}</div>
          <span style="font-size: 0.78rem; color: var(--text-muted);">ڪل جمع ٿيل جواب: ${a.submissions_count || 0}</span>
          <div style="margin-top: 8px;">
            <button class="btn-ctrl" onclick="viewAssignmentSubmissions('${a.id}')">جواب چيڪ ڪريو</button>
          </div>
        </div>
      `;
    }
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<div style="color: var(--accent-rose); padding: 10px;">لوڊ ناڪام ٿيو.</div>';
  }
}

async function viewAssignmentSubmissions(asgId) {
  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch(`/api/assignments/${asgId}/submissions`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const subs = await res.json();

    const container = document.getElementById('teacher-submissions-queue');
    if (!container) return;

    if (!subs || subs.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); padding: 12px;">هن اسائينمينٽ تي اڃا ڪنهن شاگرد جواب جمع ناهي ڪرايو.</div>';
      return;
    }

    container.innerHTML = `
      <button class="btn-ctrl" onclick="loadTeacherSubmissionsQueue()" style="margin-bottom: 10px;">&larr; لسٽ تي واپس وڃو</button>
      ${subs.map(s => `
        <div style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 10px; box-shadow: var(--shadow-card);">
          <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span style="font-weight: 700; color: var(--accent-primary);">شاگرد: ${escapeHtml(s.student_code || s.user_id)}</span>
            <span style="font-size: 0.75rem; color: var(--text-dim);">${s.submitted_at ? s.submitted_at.split('T')[0] : ''}</span>
          </div>
          <p style="font-size: 0.85rem; color: var(--text-primary); margin-bottom: 10px;">${escapeHtml(s.submission_text)}</p>
          <div style="display: flex; gap: 8px; align-items: center;">
            <input type="number" id="grade-mark-${s.id}" class="chat-input" placeholder="مارڪون" value="${s.marks_awarded || 10}" style="width: 80px;">
            <input type="text" id="grade-fb-${s.id}" class="chat-input" placeholder="استاد جو سنڌي تبصرو..." value="${escapeHtml(s.teacher_feedback || 'شاباس')}" style="flex: 1;">
            <button class="btn-ctrl active" onclick="teacherGradeSubmission('${asgId}', '${s.id}')">&#10004; گريڊ ڏيو</button>
          </div>
        </div>
      `).join('')}
    `;
  } catch (e) {}
}

async function teacherGradeSubmission(asgId, subId) {
  const mark = parseFloat(document.getElementById(`grade-mark-${subId}`).value) || 0;
  const fb = document.getElementById(`grade-fb-${subId}`).value.trim();

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch(`/api/assignments/${asgId}/submissions/${subId}/grade`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ marks_awarded: mark, teacher_feedback: fb })
    });
    if (res.ok) {
      window.showToast('شاگرد جو نتيجو محفوظ ڪيو ويو!');
      viewAssignmentSubmissions(asgId);
    } else {
      window.showToast('گريڊ ڏيڻ ۾ ايرر آيو.');
    }
  } catch (e) {}
}

async function teacherCreateAssignment() {
  const title = document.getElementById('asg-title-sindhi').value.trim();
  const desc = document.getElementById('asg-desc-sindhi').value.trim();
  const maxM = parseInt(document.getElementById('asg-max-marks').value) || 10;
  const due = document.getElementById('asg-due-date').value || '2026-12-31';

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/assignments', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        course_id: 'crs-sci-6',
        title_sindhi: title,
        description_sindhi: desc,
        max_marks: maxM,
        due_date: due
      })
    });
    if (res.ok) {
      window.showToast('نئين اسائينمينٽ ڪاميابيءَ سان جاري ٿي وئي!');
      document.getElementById('form-create-assignment').reset();
      loadTeacherSubmissionsQueue();
    }
  } catch (e) {}
}

async function triggerAIAssignmentGeneration() {
  const cls = parseInt(document.getElementById('ai-asg-class') ? document.getElementById('ai-asg-class').value : '6') || 6;
  const subj = document.getElementById('ai-asg-subject') ? document.getElementById('ai-asg-subject').value : 'Science';

  window.showToast(`اي آءِ پاران ڪلاس ${cls} (${subj}) جو هوم ورڪ ٺاهيو پيو وڃي...`);

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/assignments/ai/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        class_level: cls,
        subject: subj,
        question_count: 3,
        auto_publish: true
      })
    });
    if (res.ok) {
      const data = await res.json();
      window.showToast(`اي آءِ خودڪار هوم ورڪ ڪاميابيءَ سان شايع ڪيو: ${data.title_sindhi}`);
      loadTeacherSubmissionsQueue();
    } else {
      const err = await res.json();
      window.showToast(`ايرر: ${err.detail || 'Generation failed'}`);
    }
  } catch (e) {
    window.showToast('اي آءِ خودڪار جنريشن ۾ مسئلو آيو.');
  }
}

async function loadExceptionSubmissions() {
  const container = document.getElementById('teacher-submissions-queue');
  if (!container) return;
  container.innerHTML = '<div style="color: var(--text-dim); padding: 10px;">استثنائي رڪارڊ لوڊ ٿي رهيا آهن...</div>';

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/assignments/exceptions', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const exceptions = await res.json();

    if (!exceptions || exceptions.length === 0) {
      container.innerHTML = `
        <div style="background: rgba(16,185,129,0.1); border: 1px solid var(--accent-emerald); border-radius: var(--radius-sm); padding: 12px; color: var(--accent-emerald);">
          &#10004; ڪابه استثنا يا مشڪوڪ گريڊنگ موجود ناهي! تمام جواب خودڪار طريقي سان ڪاميابيءَ سان جاچيل آهن.
          <div style="margin-top: 8px;"><button class="btn-ctrl" onclick="loadTeacherSubmissionsQueue()">&larr; عام فهرست ڏسو</button></div>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div style="margin-bottom: 8px;"><button class="btn-ctrl" onclick="loadTeacherSubmissionsQueue()">&larr; مڪمل لسٽ تي واپس</button></div>
      ${exceptions.map(s => `
        <div style="background: rgba(245,158,11,0.08); border: 1px solid var(--accent-amber); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <strong style="color: var(--accent-amber);">شاگرد: ${escapeHtml(s.student_code || s.user_id)}</strong>
            <span style="font-size: 0.75rem; color: var(--accent-rose); font-weight: 700;">اسٽيٽس: ${s.grading_status}</span>
          </div>
          <p style="font-size: 0.85rem; color: var(--text-primary); margin-bottom: 8px;">${escapeHtml(s.submission_text)}</p>
          <div style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 8px;">سبب: ${escapeHtml(s.teacher_feedback || 'اي آءِ خودڪار ري-ٽرائي جي ضرورت')}</div>
          <div style="display: flex; gap: 8px;">
            <input type="number" id="grade-mark-${s.id}" class="chat-input" placeholder="مارڪون" value="10" style="width: 80px;">
            <input type="text" id="grade-fb-${s.id}" class="chat-input" placeholder="دستي تصديق ۽ تبصرو..." value="دستي تصديق ڪئي وئي" style="flex: 1;">
            <button class="btn-ctrl active" onclick="teacherGradeSubmission('${s.assignment_id}', '${s.id}')">دستي گريڊ ڏيو</button>
          </div>
        </div>
      `).join('')}
    `;
  } catch (e) {
    container.innerHTML = '<div style="color: var(--accent-rose); padding: 10px;">لوڊ ناڪام ٿيو.</div>';
  }
}


async function loadTeacherAnalytics() {
  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/dashboards/teacher', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const d = await res.json();

    const stuEl = document.getElementById('t-analytics-students');
    const scoreEl = document.getElementById('t-analytics-avg-score');
    const dEl = document.getElementById('t-analytics-cohens-d');
    const topicsEl = document.getElementById('t-analytics-weak-topics');

    if (stuEl) stuEl.textContent = d.total_students_enrolled;
    if (scoreEl) scoreEl.textContent = `${d.average_quiz_score_pct}%`;
    if (dEl) dEl.textContent = `d = ${d.cohens_d_gain} (High Effect)`;

    if (topicsEl && d.weak_topics) {
      topicsEl.innerHTML = d.weak_topics.map(t => `
        <tr>
          <td><strong>${escapeHtml(t.topic)}</strong></td>
          <td style="color: var(--accent-rose); font-weight: 700;">${t.error_rate_pct}%</td>
          <td>${t.total_attempts} حل ٿيل</td>
        </tr>
      `).join('');
    }
  } catch (e) {}
}

// 9. Content Reviewer Workflow
async function loadReviewerQueue() {
  const container = document.getElementById('reviewer-queue-list');
  if (!container) return;
  container.innerHTML = '<div style="color: var(--text-dim); padding: 12px;">لوڊ ٿي رهيو آهي...</div>';

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/lessons?class_level=6');
    const courses = await res.json();

    let html = '';
    courses.forEach(c => {
      c.lessons.forEach(l => {
        html += `
          <div class="glass-card" style="margin-bottom: 12px; padding: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div>
                <span class="lesson-unit-tag">${escapeHtml(c.title_sindhi)} &bull; يونٽ ${l.unit_number}</span>
                <h3 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary);">${escapeHtml(l.title_sindhi)}</h3>
                <p style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(l.summary_sindhi || '')}</p>
                <div style="font-size: 0.75rem; color: var(--accent-cyan); margin-top: 4px;">اسٽيٽس: ${l.status}</div>
              </div>
              <div style="display: flex; gap: 6px;">
                <button class="btn-ctrl active" onclick="reviewerAction('${l.id}', 'APPROVED')">&#10004; نصاب منظور ڪريو</button>
                <button class="btn-ctrl" onclick="reviewerAction('${l.id}', 'REVISION_REQUESTED')" style="color: var(--accent-amber);">&#9888; نظرثاني طلب ڪريو</button>
                <button class="btn-ctrl" onclick="reviewerAction('${l.id}', 'REJECTED')" style="color: var(--accent-rose);">&#10008; رد ڪريو</button>
              </div>
            </div>
          </div>
        `;
      });
    });
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<div style="color: var(--accent-rose); padding: 12px;">نظرثاني لسٽ لوڊ نه ٿي.</div>';
  }
}

async function reviewerAction(lessonId, action) {
  const comment = prompt('نظرثاني جو تبصرو لکو (Review comments):', action === 'APPROVED' ? 'نصاب مطابق درست آهي.' : 'اصلاح گهربل آهي.');
  if (comment === null) return;

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch(`/api/lessons/${lessonId}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ action: action, comments: comment })
    });
    if (res.ok) {
      window.showToast(`سبق جو عمل ڪاميابيءَ سان ${action} رڪارڊ ڪيو ويو.`);
      loadReviewerQueue();
    }
  } catch (e) {}
}

// 10. YouTube Educational Video Catalog (Phase 4)
async function loadYouTubeCatalog() {
  const container = document.getElementById('youtube-catalog-grid');
  if (!container) return;
  container.innerHTML = '<div style="color: var(--text-dim); padding: 12px;">يوٽيوب ڪئٽلاگ لوڊ ٿي رهيو آهي...</div>';

  try {
    const res = await fetch('/api/lessons/youtube/catalog?class_level=6');
    const videos = await res.json();

    if (!videos || videos.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); padding: 14px;">ڪابه يوٽيوب وڊيو رڪارڊ ٿيل ناهي.</div>';
      return;
    }

    container.innerHTML = videos.map(v => `
      <div class="lesson-card" style="cursor: default;">
        <div>
          <div class="lesson-unit-tag">${escapeHtml(v.channel_name)} &bull; ڪلاس ${v.class_level || 6}</div>
          <div class="lesson-title">${escapeHtml(v.title)}</div>
          <div class="lesson-desc">${escapeHtml(v.attribution_text)}</div>
        </div>
        <div style="margin-top: 10px;">
          <a href="${v.original_url}" target="_blank" rel="noopener noreferrer" class="btn-watch-yt">
            &#128279; يوٽيوب تي ڏسو (Watch on YouTube)
          </a>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div style="color: var(--accent-rose); padding: 12px;">ڪئٽلاگ لوڊ نه ٿيو.</div>';
  }
}

// Admin student progress and single-use enrollment invites
let adminProgressOffset = 0;
const ADMIN_PROGRESS_PAGE_SIZE = 25;

async function loadAdminStudentProgress(offset = 0) {
  const tbody = document.getElementById('admin-progress-table-body');
  const pager = document.getElementById('admin-progress-pagination');
  if (!tbody || !currentUser || !['ADMIN', 'SUPER_ADMIN'].includes(currentUser.role)) return;
  adminProgressOffset = Math.max(0, Number(offset) || 0);
  const q = (document.getElementById('admin-student-search')?.value || '').trim();
  tbody.innerHTML = '<tr><td colspan="7">شاگردن جي ترقي لوڊ ٿي رهي آهي...</td></tr>';
  try {
    const token = currentUser.token;
    const params = new URLSearchParams({ limit: String(ADMIN_PROGRESS_PAGE_SIZE), offset: String(adminProgressOffset) });
    if (q) params.set('q', q);
    const res = await fetch(`/api/admin/students/progress?${params}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const summary = data.summary || {};
    document.getElementById('admin-progress-total').textContent = summary.students ?? data.total ?? 0;
    document.getElementById('admin-progress-lessons').textContent = summary.completed_lessons ?? 0;
    document.getElementById('admin-progress-quizzes').textContent = summary.completed_quizzes ?? 0;
    document.getElementById('admin-progress-average').textContent = summary.average_quiz_score_pct == null ? '—' : `${Number(summary.average_quiz_score_pct).toFixed(1)}%`;
    if (!data.items?.length) {
      tbody.innerHTML = `<tr><td colspan="7">${q ? 'هن ڳولا سان شاگرد نه مليو.' : 'اڃا ڪو شاگرد اڪائونٽ موجود ناهي.'}</td></tr>`;
    } else {
      tbody.innerHTML = data.items.map((student) => `<tr>
        <td><strong>${escapeHtml(student.student_code)}</strong></td>
        <td>${escapeHtml(student.school_name || 'اسڪول جو نالو موجود ناهي')}</td>
        <td>${student.completed_lessons} / ${student.total_lessons}</td>
        <td>${student.completed_quizzes}</td>
        <td>${student.average_quiz_score_pct == null ? '—' : `${Number(student.average_quiz_score_pct).toFixed(1)}%`}</td>
        <td>${student.last_activity ? escapeHtml(new Date(student.last_activity).toLocaleString()) : 'ڪابه سرگرمي ناهي'}</td>
        <td><button type="button" class="btn-ctrl admin-student-detail-button" data-student-id="${escapeHtml(student.user_id)}" data-student-code="${escapeHtml(student.student_code)}">تفصيل</button></td>
      </tr>`).join('');
      tbody.querySelectorAll('.admin-student-detail-button').forEach((button) => button.addEventListener('click', () => loadAdminStudentDetail(button.dataset.studentId, button.dataset.studentCode)));
    }
    if (pager) {
      const first = data.total ? data.offset + 1 : 0;
      const last = Math.min(data.offset + data.items.length, data.total);
      pager.innerHTML = `<span>${first}–${last} / ${data.total}</span>
        <button type="button" class="btn-ctrl" ${data.offset <= 0 ? 'disabled' : ''} data-offset="${Math.max(0, data.offset - data.limit)}">اڳيون/پويون</button>
        <button type="button" class="btn-ctrl" ${data.offset + data.limit >= data.total ? 'disabled' : ''} data-offset="${data.offset + data.limit}">اڳيون صفحو</button>`;
      const pageButtons = pager.querySelectorAll('button');
      if (pageButtons[0]) pageButtons[0].textContent = 'پوئين صفحي';
      pageButtons.forEach((button) => button.addEventListener('click', () => loadAdminStudentProgress(Number(button.dataset.offset))));
    }
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="7">شاگردن جي ڊيٽا نه ملي. مهرباني ڪري لاگ ان ۽ نيٽ ورڪ چيڪ ڪريو.</td></tr>';
    if (pager) pager.textContent = '';
  }
}

async function loadAdminStudentDetail(userId, studentCode) {
  const panel = document.getElementById('admin-student-progress-detail');
  if (!panel || !currentUser || !['ADMIN', 'SUPER_ADMIN'].includes(currentUser.role)) return;
  panel.hidden = false;
  panel.innerHTML = `<h2>${escapeHtml(studentCode)} — محفوظ ترقي</h2><p>رياضي ۽ سائنس جا تفصيل لوڊ ٿي رهيا آهن...</p>`;
  try {
    const token = currentUser.token;
    const headers = { Authorization: `Bearer ${token}` };
    const [mathRes, scienceRes] = await Promise.all([
      fetch(`/api/dashboards/student?user_id=${encodeURIComponent(userId)}&course_id=crs-math-6`, { headers }),
      fetch(`/api/dashboards/student?user_id=${encodeURIComponent(userId)}&course_id=crs-sci-6`, { headers })
    ]);
    if (!mathRes.ok || !scienceRes.ok) throw new Error('Student dashboard unavailable');
    const [math, science] = await Promise.all([mathRes.json(), scienceRes.json()]);
    const courses = [math, science];
    panel.innerHTML = `<div class="admin-detail-heading"><h2>${escapeHtml(studentCode)} — ڪلاس 6 جي ترقي</h2><button type="button" class="btn-ctrl" id="admin-detail-close">بند ڪريو</button></div>
      ${courses.map((course) => `<section><h3>${escapeHtml(course.course_subject || 'مضمون')}</h3>
        <p>مڪمل سبق: ${course.course_completed_count || 0} / ${course.course_total_count || 0} · مڪمل ڪوئيز: ${course.completed_quiz_count || 0} · جوابن جي درستگي: ${Number(course.total_quiz_score_pct || 0).toFixed(1)}%</p>
        <ul>${(course.enrolled_lessons || []).map((lesson) => `<li>${escapeHtml(lesson.title_sindhi || lesson.title_english || lesson.lesson_id)} — ${escapeHtml(lesson.status_label || '')}</li>`).join('') || '<li>سبق جو رڪارڊ موجود ناهي.</li>'}</ul>
        </section>`).join('')}`;
    document.getElementById('admin-detail-close')?.addEventListener('click', () => { panel.hidden = true; });
  } catch (error) {
    panel.innerHTML = `<p>شاگرد جي تفصيلي ترقي لوڊ نه ٿي. ٻيهر ڪوشش ڪريو.</p><button type="button" class="btn-ctrl" onclick="this.closest('section').hidden=true">بند ڪريو</button>`;
  }
}

async function createStudentInvite() {
  const result = document.getElementById('admin-invite-result');
  if (!result || !currentUser || !['ADMIN', 'SUPER_ADMIN'].includes(currentUser.role)) return;
  result.hidden = false;
  result.textContent = 'داخلا ڪوڊ ٺاهيو پيو وڃي...';
  try {
    const res = await fetch('/api/admin/student-invites', {
      method: 'POST', headers: { Authorization: `Bearer ${currentUser.token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ expires_in_days: 7 })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'ڪوڊ نه ٺهيو.');
    result.innerHTML = `<strong>داخلا ڪوڊ (هڪ ڀيرو ڏيکاريو ويندو):</strong> <code dir="ltr">${escapeHtml(data.invite_code)}</code><br><span>ختم ٿيڻ: ${escapeHtml(new Date(data.expires_at).toLocaleString())}. ان کي شاگرد تائين محفوظ طريقي سان پهچايو.</span>`;
  } catch (error) {
    result.textContent = error.message || 'داخلا ڪوڊ ٺاهڻ ۾ ناڪامي.';
  }
}

// 11. Legacy directory kept for compatibility but not shown to current users.
async function loadSchoolUsers() {
  const tableBody = document.getElementById('school-users-table-body');
  if (!tableBody) return;
  tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 14px;">لوڊ ٿي رهيو آهي...</td></tr>';

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/admin/users', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const users = await res.json();

    tableBody.innerHTML = users.map(u => `
      <tr>
        <td><strong>${escapeHtml(u.pseudonymous_code)}</strong></td>
        <td><span style="font-weight: 700; color: var(--accent-cyan);">${u.role}</span></td>
        <td>${escapeHtml(u.school_name || 'مرڪزي انتظاميا')}</td>
        <td style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(u.email || u.phone || '-')}</td>
        <td style="font-size: 0.75rem; color: var(--text-dim);">${u.created_at ? u.created_at.split('T')[0] : ''}</td>
      </tr>
    `).join('');
  } catch (e) {
    tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--accent-rose); padding: 14px;">يوزرس لوڊ نه ٿيا.</td></tr>';
  }
}

function openCreateUserModal() {
  const m = document.getElementById('create-user-modal');
  if (m) m.style.display = 'flex';
}

function closeCreateUserModal() {
  const m = document.getElementById('create-user-modal');
  if (m) m.style.display = 'none';
}

async function submitCreateUser() {
  const role = document.getElementById('new-user-role').value;
  const code = document.getElementById('new-user-code').value.trim();
  const secret = document.getElementById('new-user-secret').value.trim();

  if (!code || !secret) {
    window.showToast('سڀ خانا ڀريو.');
    return;
  }

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/admin/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        role: role,
        pseudonymous_code: code,
        pin_or_password: secret,
        school_id: currentUser.school_id
      })
    });

    if (res.ok) {
      window.showToast(`نئون يوزر ${code} ڪاميابيءَ سان ٺاهيو ويو!`);
      closeCreateUserModal();
      loadSchoolUsers();
    } else {
      const err = await res.json();
      window.showToast(`ايرر: ${err.detail || 'يوزر ٺاهڻ ناڪام'}`);
    }
  } catch (e) {
    window.showToast('يوزر ٺاهڻ ۾ ايرر آيو.');
  }
}

// 12. District Officer Telemetry
async function loadOfficerDashboard() {
  const tableBody = document.getElementById('officer-districts-table-body');
  if (!tableBody) return;

  try {
    const res = await fetch('/api/dashboards/officer');
    const districts = await res.json();

    tableBody.innerHTML = districts.map(d => `
      <tr>
        <td><strong>${escapeHtml(d.district)}</strong></td>
        <td>${d.total_schools}</td>
        <td>${d.total_students}</td>
        <td>${d.active_rate_pct}%</td>
        <td>${d.avg_score_pct}%</td>
        <td><span style="color: var(--accent-emerald); font-weight: 700;">&#10004; ${d.offline_sync_count}</span></td>
      </tr>
    `).join('');
  } catch (e) {}
}

// 13. Super Admin Audit Logs
async function loadSuperAdminAuditLogs() {
  const tableBody = document.getElementById('superadmin-audit-table-body');
  if (!tableBody) return;
  tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 14px;">لوڊ ٿي رهيو آهي...</td></tr>';

  try {
    const token = currentUser.token || currentUser.user_id;
    const res = await fetch('/api/admin/audit-logs?limit=50', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const logs = await res.json();

    tableBody.innerHTML = logs.map(l => `
      <tr>
        <td style="font-size: 0.75rem; color: var(--text-dim);">${l.created_at ? l.created_at.replace('T', ' ').substring(0, 19) : ''}</td>
        <td><strong style="color: var(--accent-emerald);">${escapeHtml(l.action)}</strong></td>
        <td><span style="font-family: var(--font-mono); font-size: 0.78rem;">${escapeHtml(l.user_id || 'System')}</span></td>
        <td>${escapeHtml(l.resource_type)}</td>
        <td style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(l.details_json || '-')}</td>
      </tr>
    `).join('');
  } catch (e) {
    tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--accent-rose); padding: 14px;">آڊٽ لاگز ڏسڻ جي اجازت ناهي (Super Admin required).</td></tr>';
  }
}

// 14. Login & Account Switcher Modal
function openLoginModal() {
  const m = document.getElementById('login-modal');
  if (m) m.style.display = 'flex';
}

function closeLoginModal() {
  const m = document.getElementById('login-modal');
  if (m) m.style.display = 'none';
}

function switchLoginModalTab(tabType) {
  const stuBtn = document.getElementById('modal-tab-student');
  const staffBtn = document.getElementById('modal-tab-staff');
  const stuForm = document.getElementById('form-student-login');
  const staffForm = document.getElementById('form-staff-login');

  if (tabType === 'STUDENT') {
    stuBtn.classList.add('active');
    staffBtn.classList.remove('active');
    stuForm.style.display = 'block';
    staffForm.style.display = 'none';
  } else {
    staffBtn.classList.add('active');
    stuBtn.classList.remove('active');
    staffForm.style.display = 'block';
    stuForm.style.display = 'none';
  }
}

async function submitStudentLogin() {
  const schoolCode = document.getElementById('login-school-code').value.trim();
  const studentCode = document.getElementById('login-student-code').value.trim();
  const pin = document.getElementById('login-student-pin').value.trim();

  try {
    const res = await fetch('/api/auth/login/student', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ school_code: schoolCode, student_code: studentCode, pin: pin })
    });
    if (res.ok) {
      const data = await res.json();
      applyUserSession(data);
    } else {
      window.showToast('غلط اسڪول ڪوڊ يا پن داخل ڪيو ويو آهي.');
    }
  } catch (e) {
    window.showToast('لاگ ان ۾ ايرر آيو.');
  }
}

async function submitStaffLogin() {
  const identifier = document.getElementById('login-staff-identifier').value.trim();
  const password = document.getElementById('login-staff-password').value.trim();

  try {
    const res = await fetch('/api/auth/login/staff', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier: identifier, password: password })
    });
    if (res.ok) {
      const data = await res.json();
      applyUserSession(data);
    } else {
      window.showToast('غلط يوزر نالو يا پاسورڊ داخل ڪيو ويو آهي.');
    }
  } catch (e) {
    window.showToast('لاگ ان ۾ ايرر آيو.');
  }
}

function applyUserSession(authData) {
  // Flush outgoing offline queue before applying new user
  flushOfflineSyncQueue();

  currentUser = {
    user_id: authData.user_id,
    role: authData.role,
    pseudonymous_code: authData.pseudonymous_code,
    school_id: authData.school_id,
    school_name: authData.school_name,
    token: authData.token
  };
  window.currentUser = currentUser;
  localStorage.setItem('sdc_current_user', JSON.stringify(currentUser));

  closeLoginModal();
  updateHeaderUserDisplay();
  renderNavigationTabs();
  window.showToast(`لاگ ان ڪامياب! خوش آمديد ${currentUser.pseudonymous_code}`);
}

async function performLogout() {
  try {
    const token = (currentUser && currentUser.token) || (currentUser && currentUser.user_id);
    if (token) {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
    }
  } catch (e) {}

  flushOfflineSyncQueue();
  localStorage.removeItem('sdc_current_user');
  sessionStorage.clear();
  currentUser = null;
  window.currentUser = null;

  // Navigate to login page with confirmation parameter
  window.location.href = '/login?logged_out=1';
}

// 15. Offline Sync Queue Flushing (FR-19)
async function flushOfflineSyncQueue() {
  if (!navigator.onLine) return;
  const uid = currentUser && currentUser.user_id;
  if (!uid) return;

  try {
    if (typeof getSyncQueue !== 'function') return;
    const queue = await getSyncQueue(uid);
    if (!queue || queue.length === 0) return;

    const token = currentUser.token || uid;
    const res = await fetch('/api/sync/queue', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ queue: queue })
    });

    if (res.ok) {
      const result = await res.json();
      if (typeof clearSyncQueue === 'function') {
        await clearSyncQueue(uid);
      }
      window.showToast(`آف لائن رڪارڊ خودڪار سنڪ ٿي ويا (${result.attempts_processed} سوال)`);
      if (typeof loadStudentDashboard === 'function') {
        loadStudentDashboard();
      }
    }
  } catch (err) {
    console.warn('[SDC Sync] Background queue sync note:', err);
  }
}

// 16. Batch 6 NexStudio Enhancements: Offline Guide Modal & Navigation
function openOfflineGuideModal() {
  const m = document.getElementById('offline-guide-modal');
  if (m) m.style.display = 'flex';
}

function closeOfflineGuideModal() {
  const m = document.getElementById('offline-guide-modal');
  if (m) m.style.display = 'none';
}

function scrollToCurriculum(e) {
  if (e && e.preventDefault) e.preventDefault();
  const target = document.getElementById('curriculum-browser-anchor') || document.querySelector('.curriculum-toolbar');
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

window.openOfflineGuideModal = openOfflineGuideModal;
window.closeOfflineGuideModal = closeOfflineGuideModal;
window.scrollToCurriculum = scrollToCurriculum;

// ==========================================
// 17. RAG & LLM Interactive Course Module Controller
// ==========================================
let ragModules = [];
let activeRAGModuleIndex = 0;

async function loadRAGCourseModules() {
  try {
    const res = await fetch('/api/rag-course/modules');
    if (!res.ok) throw new Error('Failed to load RAG course modules');
    const data = await res.json();
    ragModules = data.modules || [];
    renderRAGModuleStepper();
    if (ragModules.length > 0) {
      selectRAGModule(0);
    }
  } catch (err) {
    console.error('[SDC RAG] Error loading modules:', err);
    window.showToast('آر اي جي ڪورس ماڊيول لوڊ ڪرڻ ۾ مسئلو آيو.');
  }
}

function renderRAGModuleStepper() {
  const container = document.getElementById('rag-modules-stepper');
  if (!container) return;

  container.innerHTML = ragModules.map((m, idx) => `
    <button class="rag-stepper-btn ${idx === activeRAGModuleIndex ? 'active' : ''}" 
            onclick="selectRAGModule(${idx})">
      <div class="rag-stepper-step">
        قدم ${m.step_number} (Module ${m.step_number})
      </div>
      <div class="rag-stepper-title">
        ${m.title_sindhi}
      </div>
    </button>
  `).join('');
}

function selectRAGModule(index) {
  if (!ragModules[index]) return;
  activeRAGModuleIndex = index;
  renderRAGModuleStepper();

  const mod = ragModules[index];
  const titleEl = document.getElementById('rag-active-module-title');
  const objEl = document.getElementById('rag-active-module-objective');
  const contentEl = document.getElementById('rag-active-module-content');

  if (titleEl) titleEl.textContent = `${mod.title} | ${mod.title_sindhi}`;
  if (objEl) objEl.innerHTML = `<strong>تعليمي مقصد (Objective):</strong> ${mod.objective}`;
  
  // Format markdown blocks safely
  if (contentEl) {
    let html = mod.content_markdown
      .replace(/### (.*?)\n/g, '<h4 style="color: var(--accent-primary); font-weight: 700; margin: 12px 0 6px;">$1</h4>')
      .replace(/```python([\s\S]*?)```/g, '<pre class="ltr-text" style="background: var(--bg-subtle); border: 1px solid var(--border-subtle); padding: 10px; border-radius: 6px; font-family: var(--font-mono); font-size: 0.8rem; overflow-x: auto; color: var(--text-primary); margin: 8px 0;">$1</pre>')
      .replace(/```([\s\S]*?)```/g, '<pre class="ltr-text" style="background: var(--bg-subtle); border: 1px solid var(--border-subtle); padding: 10px; border-radius: 6px; font-family: var(--font-mono); font-size: 0.8rem; overflow-x: auto; color: var(--text-primary); margin: 8px 0;">$1</pre>')
      .replace(/\n\n/g, '<br><br>');
    contentEl.innerHTML = html;
  }

  // Render Checkpoint Quiz
  renderRAGModuleQuiz(mod);
}

function renderRAGModuleQuiz(mod) {
  const qEl = document.getElementById('rag-quiz-question');
  const optsContainer = document.getElementById('rag-quiz-options');
  const feedbackEl = document.getElementById('rag-quiz-feedback');

  if (!mod.quiz) return;
  if (qEl) qEl.textContent = mod.quiz.question;
  if (feedbackEl) {
    feedbackEl.style.display = 'none';
    feedbackEl.className = 'quiz-feedback-box';
    feedbackEl.innerHTML = '';
  }

  if (optsContainer) {
    optsContainer.innerHTML = mod.quiz.options.map((opt, oIdx) => `
      <button class="quiz-option-card" id="quiz-opt-btn-${oIdx}" onclick="submitRAGQuizAnswer('${mod.id}', ${oIdx})">
        <span style="flex: 1; text-align: right;">${opt}</span>
        <span class="quiz-option-badge">${String.fromCharCode(65 + oIdx)}</span>
      </button>
    `).join('');
  }
}

async function submitRAGQuizAnswer(moduleId, selectedIdx) {
  try {
    const activeToken = currentUser ? (currentUser.token || currentUser.user_id) : '';
    const res = await fetch('/api/rag-course/module-quiz/submit', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${activeToken}`
      },
      body: JSON.stringify({ module_id: moduleId, selected_option_index: selectedIdx })
    });
    const result = await res.json();
    const feedbackEl = document.getElementById('rag-quiz-feedback');
    if (!feedbackEl) return;

    // Visual card state update (matching Reference 4: red wrong, green correct)
    const allBtns = document.querySelectorAll('#rag-quiz-options .quiz-option-card');
    allBtns.forEach((btn, idx) => {
      btn.disabled = true;
      if (idx === result.correct_answer_index) {
        btn.classList.add('correct');
      } else if (idx === selectedIdx && !result.is_correct) {
        btn.classList.add('incorrect');
      }
    });

    feedbackEl.style.display = 'block';
    if (result.is_correct) {
      feedbackEl.className = 'quiz-feedback-box correct';
      feedbackEl.innerHTML = `<strong>درست جواب! (Correct):</strong> ${result.explanation}`;
    } else {
      feedbackEl.className = 'quiz-feedback-box incorrect';
      feedbackEl.innerHTML = `<strong>غلط جواب!</strong> صحيح جواب آپشن ${String.fromCharCode(65 + result.correct_answer_index)} آهي.<br>${result.explanation}`;
    }
  } catch (err) {
    console.error('Quiz submit error:', err);
    window.showToast('ڪوئيز سبمٽ ڪرڻ ۾ مسئلو آيو.');
  }
}

async function runRAGSandboxQuery() {
  const input = document.getElementById('rag-sandbox-query');
  const query = (input ? input.value : '').trim();
  if (!query) {
    window.showToast('مھرباني ڪري سوال داخل ڪريو');
    return;
  }

  const resultsBox = document.getElementById('rag-sandbox-results');
  const decisionEl = document.getElementById('rag-sandbox-decision');
  const relEl = document.getElementById('rag-sandbox-relevance');
  const ansEl = document.getElementById('rag-sandbox-answer');
  const chunksContainer = document.getElementById('rag-sandbox-chunks');

  if (resultsBox) resultsBox.style.display = 'block';
  if (decisionEl) decisionEl.textContent = 'ڳولا جاري آهي...';

  try {
    const activeToken = currentUser ? (currentUser.token || currentUser.user_id) : '';
    const res = await fetch('/api/rag-course/query-sandbox', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${activeToken}`
      },
      body: JSON.stringify({ query: query, use_reranker: true })
    });
    const json = await res.json();
    const data = json.data;

    if (decisionEl) decisionEl.textContent = `فيصلو: ${data.evaluation_metrics.decision}`;
    if (relEl) relEl.textContent = `Relevance Score: ${(data.evaluation_metrics.context_relevance * 100).toFixed(1)}%`;
    if (ansEl) ansEl.innerHTML = `<strong>جواب:</strong> ${data.generated_answer}`;

    if (chunksContainer) {
      chunksContainer.innerHTML = (data.re_ranked_top_chunks || []).map((c, i) => `
        <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.06); padding: 6px 10px; border-radius: 4px; font-size: 0.76rem;">
          <div style="display: flex; justify-content: space-between; color: var(--accent-cyan); margin-bottom: 2px;">
            <span>چنڪ ${i+1} (${c.metadata ? c.metadata.topic : 'General'})</span>
            <span>Rerank Score: ${c.reranked_score || c.hybrid_score}</span>
          </div>
          <div style="color: var(--text-muted);">${c.text}</div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Sandbox error:', err);
    window.showToast('سينڊ باڪس ايگزيڪيوٽ ڪرڻ ۾ مسئلو آيو.');
  }
}

async function triggerWhisperVideoQuizGeneration() {
  const sel = document.getElementById('whisper-lesson-select');
  const statusEl = document.getElementById('whisper-quiz-status');
  if (!sel) return;

  const lessonId = sel.value;
  const lessonTitle = sel.options[sel.selectedIndex].text;
  const activeToken = currentUser ? (currentUser.token || currentUser.user_id) : '';

  if (statusEl) {
    statusEl.style.display = 'block';
    statusEl.textContent = 'Whisper وڊيو ٽرانسڪرپشن جاري آهي، 2-3 منٽن جا چيڪ پوائنٽس تجزيو ٿي رهيا آهن...';
  }

  try {
    const res = await fetch('/api/rag-course/generate-video-quiz', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${activeToken}`
      },
      body: JSON.stringify({ lesson_id: lessonId, lesson_title: lessonTitle })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to generate video quiz');
    }

    const data = await res.json();
    if (statusEl) {
      statusEl.textContent = `ڪاميابي! ${data.data.generated_quizzes_count} وڊيو چيڪ پوائنٽ ڪوئيز ٺهي ويا ۽ استاد جي منظوري واري گيٽ (FR-13 Gate) ۾ منتقل ٿيا.`;
    }
    window.showToast('Whisper وڊيو ڪوئيز ڪاميابي سان تيار ٿي ويا!');
  } catch (err) {
    console.error('Whisper generation error:', err);
    if (statusEl) {
      statusEl.style.color = 'var(--accent-rose)';
      statusEl.textContent = `مسئلو: ${err.message}`;
    }
  }
}

// Global exports
window.loadRAGCourseModules = loadRAGCourseModules;
window.selectRAGModule = selectRAGModule;
window.submitRAGQuizAnswer = submitRAGQuizAnswer;
window.runRAGSandboxQuery = runRAGSandboxQuery;
window.triggerWhisperVideoQuizGeneration = triggerWhisperVideoQuizGeneration;

// ============================================================================
// Integrated STBB Curriculum Tools Controller (Search, Glossary, Exercises, Videos)
// Consolidated directly into LMS Shell — Phase 5
// ============================================================================

let intSelectedChapter = null;
let intActiveTool = 'search';

function initIntegratedClassroomTools() {
  setupIntAlphabetButtons();
  if (intActiveTool === 'search') {
    loadIntChapterDefaultChunks(intSelectedChapter || 1);
  } else if (intActiveTool === 'glossary') {
    loadIntegratedGlossary();
  } else if (intActiveTool === 'exercises') {
    loadIntegratedExercises();
  } else if (intActiveTool === 'videos') {
    loadIntegratedVideos();
  }
}

function switchIntegratedTool(toolName) {
  intActiveTool = toolName;
  document.querySelectorAll('.integrated-tool-view').forEach(v => v.style.display = 'none');
  document.querySelectorAll('#pane-sdc-classroom .lisa-tab-pill').forEach(b => b.classList.remove('active'));

  const targetView = document.getElementById(`integrated-tool-${toolName}`);
  const targetBtn = document.getElementById(`lms-subtab-${toolName}`);
  if (targetView) targetView.style.display = 'block';
  if (targetBtn) targetBtn.classList.add('active');

  if (toolName === 'glossary') loadIntegratedGlossary();
  if (toolName === 'exercises') loadIntegratedExercises();
  if (toolName === 'videos') loadIntegratedVideos();
}

function setIntChapterFilter(chNum, btn) {
  intSelectedChapter = chNum;
  document.querySelectorAll('#pane-sdc-classroom .quick-prompt-pill').forEach(p => p.classList.remove('active'));
  if (btn) btn.classList.add('active');

  if (intActiveTool === 'search') {
    const input = document.getElementById('int-search-query-input');
    if (input && input.value.trim()) {
      handleIntegratedSearch();
    } else {
      loadIntChapterDefaultChunks(chNum || 1);
    }
  } else if (intActiveTool === 'glossary') {
    loadIntegratedGlossary();
  } else if (intActiveTool === 'exercises') {
    loadIntegratedExercises();
  } else if (intActiveTool === 'videos') {
    loadIntegratedVideos();
  }
}

async function handleIntegratedSearch(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('int-search-query-input');
  const query = input ? input.value.trim() : '';
  if (!query) return;

  const btn = document.getElementById('int-search-btn');
  const originalText = btn.innerHTML;
  btn.innerHTML = 'ڳولا جاري...';
  btn.disabled = true;

  try {
    const curSub = (window.activeCourse && window.activeCourse.subject) || 
                   (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('math') ? 'math' : null) ||
                   (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('sci') ? 'science' : null);

    let url = `/api/sdc/search?q=${encodeURIComponent(query)}`;
    if (intSelectedChapter) url += `&chapter_id=${intSelectedChapter}`;
    if (curSub) url += `&subject_id=${encodeURIComponent(curSub)}`;
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      renderIntSearchResults(data.chunks || []);
    }

    // Also trigger Grounded RAG Ask
    await handleIntRAGAsk(query);
  } catch (err) {
    console.error('Integrated search error:', err);
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

async function handleIntRAGAsk(query) {
  const answerCard = document.getElementById('int-ai-answer-card');
  const answerBody = document.getElementById('int-ai-answer-body');
  const citationsContainer = document.getElementById('int-ai-citations-container');
  const provenanceAlert = document.getElementById('int-ai-provenance-alert');

  if (!answerCard || !answerBody) return;
  answerCard.style.display = 'block';
  answerBody.innerHTML = '✨ سنڌ ٽيڪسٽ بڪ بورڊ چنڪس مان تصديق ٿيل جواب تيار ٿي رهيو آهي...';
  if (citationsContainer) citationsContainer.innerHTML = '';
  if (provenanceAlert) provenanceAlert.style.display = 'none';

  try {
    const curSub = (window.activeCourse && window.activeCourse.subject) || 
                   (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('math') ? 'math' : null) ||
                   (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('sci') ? 'science' : null);

    const payload = { query: query, chapter_id: intSelectedChapter };
    if (curSub) payload.subject_id = curSub;

    const res = await fetch('/api/sdc/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const json = await res.json();
      const ragData = json.data;
      if (ragData) {
        answerBody.textContent = ragData.answer_sd;
        if (ragData.ch7_provenance_note && provenanceAlert) {
          provenanceAlert.style.display = 'block';
          provenanceAlert.innerHTML = `⚠️ <strong>نوٽ:</strong> ${escapeHtml(ragData.ch7_provenance_note)}`;
        }
        if (ragData.citations && ragData.citations.length > 0 && citationsContainer) {
          citationsContainer.innerHTML = ragData.citations.map(c => `
            <span class="citation-chip" style="background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; font-size: 0.78rem; padding: 3px 8px; border-radius: 6px; font-weight: 700;">📖 ${escapeHtml(c)}</span>
          `).join('');
        }
      }
    }
  } catch (e) {
    answerBody.textContent = 'معاف ڪجو، جواب کڻڻ ۾ مسئلو پيش آيو.';
  }
}

async function loadIntChapterDefaultChunks(chNum) {
  try {
    const res = await fetch(`/api/sdc/search?q=&chapter_id=${chNum}&limit=12`);
    if (res.ok) {
      const data = await res.json();
      renderIntSearchResults(data.chunks || []);
    }
  } catch (err) {
    console.warn(err);
  }
}

function renderIntSearchResults(chunks) {
  const container = document.getElementById('int-search-results-grid');
  const header = document.getElementById('int-results-header');
  if (!container) return;
  if (header) header.style.display = 'block';

  if (!chunks || chunks.length === 0) {
    container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 30px; color: var(--text-muted);">ڪوبه نتيجو نه مليو۔ مهرباني ڪري ٻيو باب يا لفظ چونڊيو۔</div>';
    return;
  }

  container.innerHTML = chunks.map(chunk => `
    <div class="glass-card" style="padding: 16px; margin-bottom: 12px; display: flex; flex-direction: column; justify-content: space-between;">
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span class="lesson-unit-tag">باب ${chunk.chapter_id}</span>
          <span style="font-size: 0.75rem; color: var(--accent-emerald); font-weight: 700;">${escapeHtml(chunk.citation)}</span>
        </div>
        <h4 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">${escapeHtml(chunk.topic_title_sd)}</h4>
        <div style="font-size: 0.78rem; color: var(--text-muted); font-weight: 600; margin-bottom: 8px;" class="ltr-text">${escapeHtml(chunk.topic_title_en)}</div>
        <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6; margin-bottom: 12px;">${escapeHtml(chunk.summary_sd)}</p>
      </div>
      <div style="border-top: 1px solid var(--border-subtle); padding-top: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; color: var(--text-muted);">
        <span>${escapeHtml(chunk.source)}</span>
      </div>
    </div>
  `).join('');
}

// Integrated Glossary
function setupIntAlphabetButtons() {
  const container = document.getElementById('int-alphabet-bar');
  if (!container || container.children.length > 0) return;
  const letters = ['سڀ', 'الف', 'ب', 'ٻ', 'ت', 'ٽ', 'ث', 'پ', 'ج', 'ڄ', 'ڃ', 'چ', 'ڇ', 'ح', 'خ', 'د', 'ڌ', 'ڏ', 'ڊ', 'ڍ', 'ذ', 'ر', 'ڙ', 'ز', 'ژ', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ڦ', 'ق', 'ڪ', 'ک', 'گ', 'ڳ', 'ڱ', 'گھ', 'ل', 'م', 'ن', 'ڻ', 'و', 'ه', 'ء', 'ي'];
  container.innerHTML = letters.map(l => `
    <button type="button" class="quick-prompt-pill ${l === 'سڀ' ? 'active' : ''}" onclick="filterIntGlossaryLetter('${l === 'سڀ' ? '' : l}', this)" style="padding: 2px 8px; font-size: 0.76rem;">
      ${l}
    </button>
  `).join('');
}

function filterIntGlossaryLetter(letter, btn) {
  document.querySelectorAll('#int-alphabet-bar .quick-prompt-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  loadIntegratedGlossary(letter);
}

async function loadIntegratedGlossary(letter = null) {
  const container = document.getElementById('int-glossary-list-container');
  if (!container) return;
  container.innerHTML = '<div style="text-align: center; padding: 24px; color: var(--text-muted);">اصطلاح لوڊ ٿي رهيا آهن...</div>';

  const curSub = (window.activeCourse && window.activeCourse.subject) || 
                 (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('math') ? 'math' : null) ||
                 (window.currentLesson && window.currentLesson.course_id && window.currentLesson.course_id.includes('sci') ? 'science' : null);

  let url = '/api/sdc/glossary?limit=205';
  if (intSelectedChapter) url += `&chapter_id=${intSelectedChapter}`;
  if (curSub) url += `&subject_id=${encodeURIComponent(curSub)}`;
  if (letter) url += `&letter=${encodeURIComponent(letter)}`;

  try {
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      const terms = data.terms || [];
      if (terms.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 24px; color: var(--text-muted);">ڪوبه اصطلاح نه مليو.</div>';
        return;
      }
      container.innerHTML = terms.map(t => `
        <div class="glass-card" style="padding: 14px 18px; margin-bottom: 8px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap; gap: 8px;">
            <div style="display: flex; align-items: baseline; gap: 10px;">
              <span style="font-size: 1.1rem; font-weight: 800; color: var(--accent-primary);">${escapeHtml(t.term_sd)}</span>
              <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600;" class="ltr-text">${escapeHtml(t.term_en)}</span>
            </div>
            <span style="font-size: 0.75rem; color: var(--accent-emerald); font-weight: 700;">حوالو: ${escapeHtml(t.citation)}</span>
          </div>
          <p style="font-size: 0.86rem; color: var(--text-secondary); line-height: 1.6; margin: 0;">${escapeHtml(t.definition_sd)}</p>
        </div>
      `).join('');
    }
  } catch (e) {
    container.innerHTML = '<div style="text-align: center; padding: 24px; color: var(--accent-rose);">ڊيٽا لوڊ ڪرڻ ۾ مسئلو آيو.</div>';
  }
}

// Integrated Exercises
async function loadIntegratedExercises() {
  const container = document.getElementById('int-exercise-list-container');
  if (!container) return;
  container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 24px; color: var(--text-muted);">مشقون لوڊ ٿي رهيون آهن...</div>';

  let url = '/api/sdc/exercises';
  if (intSelectedChapter) url += `?chapter_id=${intSelectedChapter}`;

  try {
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      const exercises = data.exercises || [];
      if (exercises.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 24px; color: var(--text-muted);">ڪا مشق نه ملي.</div>';
        return;
      }
      container.innerHTML = exercises.map(ex => `
        <div class="glass-card" style="padding: 16px; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span class="lesson-unit-tag">${escapeHtml(ex.item_type)}</span>
              <span class="lesson-completed-check">باب ${ex.chapter_id}</span>
            </div>
            <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">${escapeHtml(ex.topic_en)}</h4>
            <div style="font-size: 0.8rem; color: var(--accent-emerald); font-weight: 700; margin-bottom: 12px;">حوالو: ${escapeHtml(ex.citation)}</div>
          </div>
          ${ex.sos_video_id ? `
            <div style="border-top: 1px solid var(--border-subtle); padding-top: 10px; display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(ex.sos_video_title || 'وڊيو ليڪچر')}</span>
              <a href="https://www.youtube.com/watch?v=${ex.sos_video_id}" target="_blank" rel="noopener noreferrer" class="btn-ctrl active" style="font-size: 0.76rem; padding: 4px 10px; text-decoration: none;">▶️ يوٽيوب</a>
            </div>
          ` : '<div style="font-size: 0.78rem; color: var(--text-muted);">(وڊيو موجود ناهي)</div>'}
        </div>
      `).join('');
    }
  } catch (e) {
    container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 24px; color: var(--accent-rose);">مشقون لوڊ نه ٿي سگهيون.</div>';
  }
}

// Integrated Videos
async function loadIntegratedVideos() {
  const container = document.getElementById('int-videos-grid-container');
  if (!container) return;
  container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 24px; color: var(--text-muted);">وڊيوز لوڊ ٿي رهيون آهن...</div>';

  let url = '/api/sdc/videos';
  if (intSelectedChapter) url += `?chapter_id=${intSelectedChapter}`;

  try {
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      const videos = data.videos || [];
      if (videos.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 24px; color: var(--text-muted);">ڪا وڊيو نه ملي.</div>';
        return;
      }
      container.innerHTML = videos.map(v => `
        <div class="glass-card" style="padding: 16px; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span class="lesson-unit-tag">باب ${v.chapter_id}</span>
              <span style="font-size: 0.78rem; color: var(--text-muted);">⏱️ ${v.duration || '--'}</span>
            </div>
            <h4 style="font-size: 0.96rem; font-weight: 700; color: var(--text-primary); margin-bottom: 12px; line-height: 1.5;">${escapeHtml(v.title)}</h4>
          </div>
          <div style="border-top: 1px solid var(--border-subtle); padding-top: 10px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.78rem; color: var(--accent-emerald);">سنڌ آن لائن اسڪول</span>
            <a href="https://www.youtube.com/watch?v=${v.video_id}" target="_blank" rel="noopener noreferrer" class="btn-ctrl active" style="font-size: 0.76rem; padding: 4px 10px; text-decoration: none;">▶️ هلايو</a>
          </div>
        </div>
      `).join('');
    }
  } catch (e) {
    container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 24px; color: var(--accent-rose);">وڊيوز لوڊ نه ٿي سگهيون.</div>';
  }
}

// Export functions to global scope
window.initIntegratedClassroomTools = initIntegratedClassroomTools;
window.switchIntegratedTool = switchIntegratedTool;
window.setIntChapterFilter = setIntChapterFilter;
window.handleIntegratedSearch = handleIntegratedSearch;
window.filterIntGlossaryLetter = filterIntGlossaryLetter;



