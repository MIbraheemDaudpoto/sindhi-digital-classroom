from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_JS_PATH = ROOT / "static" / "js" / "app.js"

with open(APP_JS_PATH, "r", encoding="utf-8") as f:
    js_content = f.read()

# Define the replacement block for curriculum functions
target = '''// 1. Curriculum Browsing (Class 6-10, FR-05)
function selectClassLevel(level, btn) {
  activeClassLevel = level;
  document.querySelectorAll('.filter-pills-row .pill-btn').forEach(b => {
    if (b.textContent.includes('ڪلاس')) b.classList.remove('active');
  });
  if (btn) btn.classList.add('active');
  loadCurriculum(activeClassLevel, activeSubjectFilter);
}

function selectSubjectFilter(subject, btn) {
  activeSubjectFilter = subject;
  document.querySelectorAll('.filter-pills-row .pill-btn').forEach(b => {
    if (!b.textContent.includes('ڪلاس')) b.classList.remove('active');
  });
  if (btn) btn.classList.add('active');
  filterAndRenderCourses();
}'''

replacement = '''// =========================================================================
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
}'''

if target in js_content:
    js_content = js_content.replace(target, replacement)
    with open(APP_JS_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)
    print("Successfully updated app.js with SOS flow controller!")
else:
    print("Warning: target not found in app.js!")

