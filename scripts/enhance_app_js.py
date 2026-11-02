from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_JS_PATH = ROOT / "static" / "js" / "app.js"

with open(APP_JS_PATH, "r", encoding="utf-8") as f:
    js_content = f.read()

# Enhance selectLesson to update stepper badges and breadcrumbs
target_bc = '''    // Update Sindh Online School style breadcrumbs
    const bcClass = document.getElementById('sos-bc-class');
    const bcSubject = document.getElementById('sos-bc-subject');
    const bcChapter = document.getElementById('sos-bc-chapter');
    const displayClass = activeClassLevel || 6;
    const displaySubject = (!activeSubjectFilter || activeSubjectFilter === 'ALL') ? 'Science' : activeSubjectFilter;
    if (bcClass) bcClass.textContent = `Class ${displayClass} (${displayClass === 6 ? 'ڇهون' : displayClass})`;
    if (bcSubject) bcSubject.textContent = `${displaySubject} (${displaySubject.toLowerCase() === 'science' ? 'جنرل سائنس' : displaySubject})`;
    if (bcChapter) bcChapter.textContent = `Chapter ${String(detail.unit_number).padStart(2, '0')} (${detail.title_english || detail.title_sindhi})`;'''

replacement_bc = '''    // Update Sindh Online School style breadcrumbs
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
    if (valLes) valLes.textContent = detail.title_sindhi;'''

# Enhance updateLessonTutorContext for both Math and Science
target_prompts = '''function updateLessonTutorContext(lessonDetail) {
  if (!lessonDetail) return;
  const promptsBar = document.querySelector('.tutor-quick-prompts');
  if (!promptsBar) return;

  const unit = lessonDetail.unit_number || 1;
  const title = lessonDetail.title_sindhi || '';

  // Generate lesson-specific starter prompts
  let prompts = [];
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

  promptsBar.innerHTML = prompts.map(p => `
    <button type="button" class="quick-prompt-pill" onclick="sdcTutor.askQuickPrompt('${escapeHtml(p.q)}')">${escapeHtml(p.label)}</button>
  `).join('');
}'''

replacement_prompts = '''function updateLessonTutorContext(lessonDetail) {
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
}'''

if target_bc in js_content:
    js_content = js_content.replace(target_bc, replacement_bc)
    print("Replaced breadcrumbs logic in app.js")
else:
    print("Warning: target_bc not found in app.js")

if target_prompts in js_content:
    js_content = js_content.replace(target_prompts, replacement_prompts)
    print("Replaced prompts logic in app.js")
else:
    print("Warning: target_prompts not found in app.js")

with open(APP_JS_PATH, "w", encoding="utf-8") as f:
    f.write(js_content)
print("app.js enhancement completed successfully!")

