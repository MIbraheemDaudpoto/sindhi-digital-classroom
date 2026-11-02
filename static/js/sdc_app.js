/**
 * Sindhi Digital Classroom (SDC) Pilot Application Logic.
 * Manages 4 screens: Search/RAG, Glossary, Exercises, and Videos.
 * Implements offline detection, YouTube embedded video player with offline fallback,
 * IndexedDB caching for client queries, and citation display.
 */

// Global State
const SDC_STATE = {
  activeScreen: 'chat',
  selectedChapter: null,
  isOnline: navigator.onLine,
  stats: null,
  activeVideoId: null
};

// IndexedDB Helper for Client-Side Query & State Cache
const DB_NAME = 'SDC_Offline_Store';
const DB_VERSION = 1;

function openSDCDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('query_cache')) {
        db.createObjectStore('query_cache', { keyPath: 'query_key' });
      }
      if (!db.objectStoreNames.contains('notes')) {
        db.createObjectStore('notes', { keyPath: 'id', autoIncrement: true });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function cacheSearchResult(key, data) {
  try {
    const db = await openSDCDatabase();
    const tx = db.transaction('query_cache', 'readwrite');
    tx.objectStore('query_cache').put({ query_key: key, data, timestamp: Date.now() });
  } catch (err) {
    console.warn('IndexedDB caching skipped:', err);
  }
}

async function getCachedSearchResult(key) {
  try {
    const db = await openSDCDatabase();
    return new Promise((resolve) => {
      const tx = db.transaction('query_cache', 'readonly');
      const req = tx.objectStore('query_cache').get(key);
      req.onsuccess = () => resolve(req.result ? req.result.data : null);
      req.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

// Network Status Listeners
function updateOnlineStatus() {
  SDC_STATE.isOnline = navigator.onLine;
  const banner = document.getElementById('offline-banner');
  const badge = document.getElementById('connection-badge');

  if (!SDC_STATE.isOnline) {
    banner.classList.add('active');
    badge.innerHTML = '<span class="status-dot" style="background:#f59e0b;"></span> آف لائن موڊ (Offline)';
    badge.style.color = '#f59e0b';
    badge.style.borderColor = 'rgba(245, 158, 11, 0.4)';
  } else {
    banner.classList.remove('active');
    badge.innerHTML = '<span class="status-dot"></span> آن لائن جڙيل (Online)';
    badge.style.color = '#34d399';
    badge.style.borderColor = 'rgba(52, 211, 153, 0.3)';
  }
}

window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);

// Navigation Switcher
function switchScreen(screenName) {
  SDC_STATE.activeScreen = screenName;
  document.querySelectorAll('.screen-view').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

  const targetScreen = document.getElementById(`screen-${screenName}`);
  const targetBtn = document.getElementById(`nav-${screenName}`);
  if (targetScreen) targetScreen.classList.add('active');
  if (targetBtn) targetBtn.classList.add('active');

  // Trigger screen specific loaders
  if (screenName === 'glossary') loadGlossary();
  if (screenName === 'exercises') loadExercises();
  if (screenName === 'videos') loadVideos();
}

// Search & Ask RAG Logic
async function handleSearch(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('search-query-input');
  const query = input.value.trim();
  if (!query) return;

  const btn = document.getElementById('search-btn');
  const originalText = btn.innerHTML;
  btn.innerHTML = 'ڳولا جاري...';
  btn.disabled = true;

  const cacheKey = `search_${query}_ch${SDC_STATE.selectedChapter || 'all'}`;

  try {
    let url = `/api/sdc/search?q=${encodeURIComponent(query)}`;
    if (SDC_STATE.selectedChapter) {
      url += `&chapter_id=${SDC_STATE.selectedChapter}`;
    }

    let responseData = null;
    try {
      const res = await fetch(url);
      if (res.ok) {
        responseData = await res.json();
        await cacheSearchResult(cacheKey, responseData);
      }
    } catch {
      responseData = await getCachedSearchResult(cacheKey);
    }

    if (responseData) {
      renderSearchResults(responseData.chunks || []);
    }

    // Also trigger grounded RAG Ask
    await handleRAGAsk(query);
  } catch (err) {
    console.error('Search error:', err);
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

async function handleRAGAsk(query) {
  const answerCard = document.getElementById('ai-answer-card');
  const answerBody = document.getElementById('ai-answer-body');
  const citationsContainer = document.getElementById('ai-citations-container');
  const provenanceAlert = document.getElementById('ai-provenance-alert');

  answerCard.style.display = 'block';
  answerBody.innerHTML = '✨ RAG جواب تيار ٿي رهيو آهي (Generating grounded answer)...';
  citationsContainer.innerHTML = '';
  provenanceAlert.style.display = 'none';

  const cacheKey = `rag_${query}_ch${SDC_STATE.selectedChapter || 'all'}`;

  try {
    let ragData = null;
    try {
      const res = await fetch('/api/sdc/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          chapter_id: SDC_STATE.selectedChapter
        })
      });
      if (res.ok) {
        const json = await res.json();
        ragData = json.data;
        await cacheSearchResult(cacheKey, ragData);
      }
    } catch {
      ragData = await getCachedSearchResult(cacheKey);
    }

    if (ragData) {
      answerBody.textContent = ragData.answer_sd;

      if (ragData.ch7_provenance_note) {
        provenanceAlert.style.display = 'flex';
        provenanceAlert.innerHTML = `⚠️ <strong>نوٽ:</strong> ${ragData.ch7_provenance_note}`;
      }

      if (ragData.citations && ragData.citations.length > 0) {
        citationsContainer.innerHTML = ragData.citations.map(c => `
          <span class="citation-chip">📖 ${c}</span>
        `).join('');
      }
    }
  } catch (err) {
    answerBody.textContent = 'معاف ڪجو، جواب کڻڻ ۾ مسئلو پيش آيو.';
  }
}

function renderSearchResults(chunks) {
  const container = document.getElementById('search-results-grid');
  const header = document.getElementById('results-header');
  header.style.display = 'block';

  if (!chunks || chunks.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
        ڪوبه نتيجو نه مليو۔ مهرباني ڪري ٻيو لفظ يا باب چونڊيو۔
      </div>
    `;
    return;
  }

  container.innerHTML = chunks.map(chunk => `
    <div class="sdc-card">
      <div>
        <div class="card-top">
          <span class="card-chapter-tag">باب ${chunk.chapter_id}</span>
          <span class="card-citation">${chunk.citation}</span>
        </div>
        <div class="card-title-sd">${chunk.topic_title_sd}</div>
        <div class="card-title-en">${chunk.topic_title_en}</div>
        <div class="card-summary">${chunk.summary_sd}</div>
      </div>
      <div class="card-footer">
        <span style="font-size: 0.8rem; color: var(--text-muted);">${chunk.source}</span>
        ${chunk.video_id ? `
          <button class="btn-video-watch" onclick="openVideoModal('${chunk.video_id}', '${escapeHtml(chunk.video_title || chunk.topic_title_sd)}')">
            ▶️ وڊيو ليڪچر
          </button>
        ` : ''}
      </div>
    </div>
  `).join('');
}

// Chapter Filter Pills
function setChapterFilter(chNum, btn) {
  SDC_STATE.selectedChapter = chNum;
  document.querySelectorAll('.ch-pill').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');

  // Trigger reload based on current screen
  if (SDC_STATE.activeScreen === 'search') {
    const input = document.getElementById('search-query-input');
    if (input.value.trim()) {
      handleSearch();
    } else if (chNum) {
      loadChapterDefaultChunks(chNum);
    }
  } else if (SDC_STATE.activeScreen === 'glossary') {
    loadGlossary();
  } else if (SDC_STATE.activeScreen === 'exercises') {
    loadExercises();
  } else if (SDC_STATE.activeScreen === 'videos') {
    loadVideos();
  }
}

async function loadChapterDefaultChunks(chNum) {
  try {
    const res = await fetch(`/api/sdc/search?q=&chapter_id=${chNum}&limit=12`);
    if (res.ok) {
      const data = await res.json();
      renderSearchResults(data.chunks);
    }
  } catch (err) {
    console.error(err);
  }
}

// Glossary Logic
async function loadGlossary(letter = null) {
  const container = document.getElementById('glossary-list-container');
  container.innerHTML = '<div style="text-align:center; padding:30px;">لوڊ ٿي رهيو آهي...</div>';

  let url = `/api/sdc/glossary?limit=205`;
  if (SDC_STATE.selectedChapter) url += `&chapter_id=${SDC_STATE.selectedChapter}`;
  if (letter) url += `&letter=${encodeURIComponent(letter)}`;

  try {
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      renderGlossary(data.terms || []);
    }
  } catch {
    container.innerHTML = '<div style="text-align:center; padding:30px;">آف لائن ڊيٽا لوڊ ٿي نه سگهي.</div>';
  }
}

function renderGlossary(terms) {
  const container = document.getElementById('glossary-list-container');
  if (!terms || terms.length === 0) {
    container.innerHTML = '<div style="text-align:center; padding:30px;">ڪوبه لفظ نه مليو.</div>';
    return;
  }

  container.innerHTML = terms.map(t => `
    <div class="glossary-item-card">
      <div class="glossary-terms-row">
        <span class="glossary-sd">${t.term_sd}</span>
        <span class="glossary-en">${t.term_en}</span>
      </div>
      <div class="glossary-def">${t.definition_sd}</div>
      <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; color:var(--text-muted); margin-top:4px;">
        <span style="color:#fbbf24;">حوالو: ${t.citation}</span>
        ${t.is_ch7_blank ? '<span style="color:#f59e0b;">(باب 7 پي ڊي ايف ۾ خالي آهي)</span>' : ''}
      </div>
    </div>
  `).join('');
}

// Exercise Logic
async function loadExercises() {
  const container = document.getElementById('exercise-list-container');
  container.innerHTML = '<div style="text-align:center; padding:30px;">لوڊ ٿي رهيو آهي...</div>';

  let url = '/api/sdc/exercises';
  if (SDC_STATE.selectedChapter) url += `?chapter_id=${SDC_STATE.selectedChapter}`;

  try {
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      renderExercises(data.exercises || []);
    }
  } catch {
    container.innerHTML = '<div style="text-align:center; padding:30px;">آف لائن ڊيٽا لوڊ ٿي نه سگهي.</div>';
  }
}

function renderExercises(exercises) {
  const container = document.getElementById('exercise-list-container');
  if (!exercises || exercises.length === 0) {
    container.innerHTML = '<div style="text-align:center; padding:30px;">ڪا مشق نه ملي.</div>';
    return;
  }

  container.innerHTML = exercises.map(ex => `
    <div class="exercise-card">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span class="item-badge ${ex.item_type}">${ex.item_type}</span>
        <span class="card-chapter-tag">باب ${ex.chapter_id}</span>
      </div>
      <h3 style="font-size:1.1rem; color:var(--text-main); font-weight:700; margin-bottom:6px;">${ex.topic_en}</h3>
      <div style="font-size:0.88rem; color:#b45309; font-weight:600; margin-bottom:12px;">حوالو: ${ex.citation}</div>
      ${ex.sos_video_id ? `
        <div style="border-top:1px solid var(--border-color); padding-top:10px; display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:0.85rem; color:var(--text-muted);">${ex.sos_video_title || 'وڊيو حل'}</span>
          <button class="btn-video-watch" onclick="openVideoModal('${ex.sos_video_id}', '${escapeHtml(ex.sos_video_title || ex.topic_en)}')">
            ▶️ وڊيو ڏسو
          </button>
        </div>
      ` : `
        <div style="font-size:0.8rem; color:var(--text-muted);">(وڊيو ليڪچر موجود ناهي)</div>
      `}
    </div>
  `).join('');
}

// Video Lessons Logic
async function loadVideos() {
  const container = document.getElementById('videos-grid-container');
  container.innerHTML = '<div style="text-align:center; padding:30px;">لوڊ ٿي رهيو آهي...</div>';

  let url = '/api/sdc/videos';
  if (SDC_STATE.selectedChapter) url += `?chapter_id=${SDC_STATE.selectedChapter}`;

  try {
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      renderVideos(data.videos || []);
    }
  } catch {
    container.innerHTML = '<div style="text-align:center; padding:30px;">آف لائن ڊيٽا لوڊ ٿي نه سگهي.</div>';
  }
}

function renderVideos(videos) {
  const container = document.getElementById('videos-grid-container');
  if (!videos || videos.length === 0) {
    container.innerHTML = '<div style="text-align:center; padding:30px;">ڪا وڊيو نه ملي.</div>';
    return;
  }

  container.innerHTML = videos.map(v => `
    <div class="sdc-card">
      <div>
        <div class="card-top">
          <span class="card-chapter-tag">باب ${v.chapter_id}</span>
          <span style="font-size:0.82rem; color:#94a3b8;">⏱️ ${v.duration || '--'}</span>
        </div>
        <div style="font-size:1rem; font-weight:700; color:#fff; margin-bottom:12px;">${v.title}</div>
      </div>
      <div class="card-footer">
        <span style="font-size:0.8rem; color:#34d399;">سنڌ آن لائن اسڪول</span>
        <button class="btn-video-watch" onclick="openVideoModal('${v.video_id}', '${escapeHtml(v.title)}')">
          ▶️ هلائي ڏسو
        </button>
      </div>
    </div>
  `).join('');
}

// Video Modal & YouTube Playback
function openVideoModal(videoId, title) {
  SDC_STATE.activeVideoId = videoId;
  const modal = document.getElementById('video-modal');
  const titleEl = document.getElementById('video-modal-title');
  const container = document.getElementById('video-player-frame-container');
  const watchUrl = `https://www.youtube.com/watch?v=${videoId}`;

  titleEl.textContent = title;
  modal.classList.add('active');

  if (navigator.onLine && videoId) {
    container.innerHTML = `
      <div style="position: relative; width: 100%; padding-top: 56.25%; background: #000;">
        <iframe
          src="https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1"
          title="${title}"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowfullscreen>
        </iframe>
      </div>
      <div style="padding: 14px 18px; background: rgba(15, 23, 42, 0.95); display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); flex-wrap: wrap; gap: 10px;">
        <span style="font-size: 0.85rem; color: var(--text-muted);">جيڪڏهن براؤزر ۾ وڊيو بند هجي يا گوگل تصديق چوي:</span>
        <a href="${watchUrl}" target="_blank" rel="noopener noreferrer" class="btn-video-watch" style="text-decoration: none; padding: 6px 16px; border-radius: 8px;">
          🌐 سڌو يوٽيوب تي کوليو (Open in YouTube)
        </a>
      </div>
    `;
  } else {
    // Offline Degradation
    container.innerHTML = `
      <div class="video-fallback-msg">
        <div style="font-size: 2.5rem; margin-bottom: 12px;">📶</div>
        <h3 style="font-size: 1.2rem; color: #fff; margin-bottom: 8px;">انٽرنيٽ موجود ناهي (Offline)</h3>
        <p style="font-size: 0.9rem; color: var(--text-muted); max-width: 400px; margin: 0 auto; line-height: 1.6;">
          هي وڊيو آن لائن هجڻ وقت ڏسي سگهجي ٿي۔ پي ڊي ايف ۽ نصابي خلاصا بنا انٽرنيٽ جي مڪمل طور ڪم ڪري رهيا آهن۔
        </p>
      </div>
    `;
  }
}

function closeVideoModal() {
  const modal = document.getElementById('video-modal');
  const container = document.getElementById('video-player-frame-container');
  modal.classList.remove('active');
  container.innerHTML = '';
  SDC_STATE.activeVideoId = null;
}

// Initial System Stats Fetch
async function loadSystemStats() {
  try {
    const res = await fetch('/api/sdc/stats');
    if (res.ok) {
      const data = await res.json();
      SDC_STATE.stats = data.stats;
      const statsEl = document.getElementById('footer-stats-text');
      if (statsEl && data.stats) {
        statsEl.textContent = `ڊيٽابيس: ${data.stats.database_size_mb} MB | چنڪس: ${data.stats.chunks} | اصطلاح: ${data.stats.glossary} | وڊيوز: ${data.stats.videos}`;
      }
    }
  } catch (err) {
    console.warn('Could not fetch stats:', err);
  }
}

// Helpers
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// Setup Alphabet Buttons
function setupAlphabetButtons() {
  const container = document.getElementById('alphabet-bar');
  if (!container) return;
  const sindhiLetters = ['سڀ', 'الف', 'ب', 'ٻ', 'ت', 'ٽ', 'ث', 'پ', 'ج', 'ڄ', 'ڃ', 'چ', 'ڇ', 'ح', 'خ', 'د', 'ڌ', 'ڏ', 'ڊ', 'ڍ', 'ذ', 'ر', 'ڙ', 'ز', 'ژ', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ڦ', 'ق', 'ڪ', 'ک', 'گ', 'ڳ', 'ڱ', 'گھ', 'ل', 'م', 'ن', 'ڻ', 'و', 'ه', 'ء', 'ي'];

  container.innerHTML = sindhiLetters.map(l => `
    <button class="alpha-btn ${l === 'سڀ' ? 'active' : ''}" onclick="filterByLetter('${l === 'سڀ' ? '' : l}', this)">
      ${l}
    </button>
  `).join('');
}

function filterByLetter(letter, btn) {
  document.querySelectorAll('.alpha-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadGlossary(letter);
}

// Service Worker Registration for PWA Offline Functionality
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .then(reg => console.log('[PWA] Service Worker registered with scope:', reg.scope))
      .catch(err => console.warn('[PWA] Service Worker registration failed:', err));
  });
}

// Conversational AI Tutor Chat Implementation (Powered by RAG & STBB)
async function sendQuickChatMessage(text) {
  const input = document.getElementById('classroom-chat-input');
  if (input) input.value = text;
  await handleClassroomChatSubmit();
}

async function handleClassroomChatSubmit(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('classroom-chat-input');
  const chatStream = document.getElementById('classroom-chat-stream');
  if (!input || !chatStream) return;

  const query = input.value.trim();
  if (!query) return;

  // Append Student User Bubble
  const userBubble = document.createElement('div');
  userBubble.className = 'chat-bubble user-bubble';
  userBubble.innerHTML = `<div class="bubble-text">${escapeHtml(query)}</div>`;
  chatStream.appendChild(userBubble);
  input.value = '';
  chatStream.scrollTop = chatStream.scrollHeight;

  // Loading indicator
  const loadingBubble = document.createElement('div');
  loadingBubble.className = 'chat-bubble tutor-bubble';
  loadingBubble.innerHTML = `<div class="bubble-text" style="color: var(--text-muted);">✨ جواب تيار ٿي رهيو آهي (Thinking)...</div>`;
  chatStream.appendChild(loadingBubble);
  chatStream.scrollTop = chatStream.scrollHeight;

  try {
    const res = await fetch('/api/sdc/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });

    loadingBubble.remove();

    if (res.ok) {
      const data = (await res.json()).data;
      const tutorBubble = document.createElement('div');
      tutorBubble.className = 'chat-bubble tutor-bubble';

      let citationHtml = '';
      if (data.citations && data.citations.length > 0) {
        citationHtml = `
          <div class="tutor-citation-box">
            <span style="font-weight: 700; color: var(--primary);">📖 ڪتاب جو حوالو (STBB Citation):</span>
            <div style="margin-top: 4px; display: flex; flex-wrap: wrap; gap: 6px;">
              ${data.citations.map(c => `<span class="citation-chip">📌 ${escapeHtml(c)}</span>`).join('')}
            </div>
          </div>
        `;
      }

      tutorBubble.innerHTML = `
        <div class="bubble-header">
          <span class="tutor-name">🤖 سنڌي اي آءِ استاد (STBB Verified RAG)</span>
        </div>
        <div class="bubble-text">${escapeHtml(data.answer_sd)}</div>
        ${citationHtml}
      `;
      chatStream.appendChild(tutorBubble);
    } else {
      const errBubble = document.createElement('div');
      errBubble.className = 'chat-bubble tutor-bubble';
      errBubble.innerHTML = `<div class="bubble-text" style="color: var(--accent-red);">معاف ڪجو، جواب کڻڻ ۾ مسئلو پيش آيو.</div>`;
      chatStream.appendChild(errBubble);
    }
  } catch (err) {
    loadingBubble.remove();
    const errBubble = document.createElement('div');
    errBubble.className = 'chat-bubble tutor-bubble';
    errBubble.innerHTML = `<div class="bubble-text" style="color: var(--accent-red);">نيٽ ورڪ يا سرور سان رابطو نه ٿي سگهيو.</div>`;
    chatStream.appendChild(errBubble);
  }

  chatStream.scrollTop = chatStream.scrollHeight;
}

// Bootstrap
document.addEventListener('DOMContentLoaded', () => {
  updateOnlineStatus();
  setupAlphabetButtons();
  loadSystemStats();

  // Search input enter listener
  const searchInput = document.getElementById('search-query-input');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleSearch(e);
    });
  }

  // Initial load: Ch1 default preview
  loadChapterDefaultChunks(1);
});
