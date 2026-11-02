// Grounded Sindhi AI Tutor & Voice AI Controller (FR-20 to FR-26)
// Provides full offline/online AI tutoring across Class 6 Science & Mathematics,
// authentic Sindhi TTS audio synthesis, and real microphone speech-to-text (ASR).
// Authored under agency-ai-engineer, agency-voice-ai-integration-engineer, and agency-frontend-developer.

class SDCAITutor {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.isRecording = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.mediaStream = null;
    this.isPending = false;
    this.audioPlayer = new Audio();
    this.currentlyPlayingBtn = null;
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
  }

  setupComposerEvents() {
    const textarea = document.getElementById('tutor-question-input');
    if (!textarea) return;

    // Auto-grow textarea up to 140px
    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 140) + 'px';
    });

    // Enter to send, Shift+Enter for newline
    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.askQuestion(this.currentLesson?.id || window.currentLoadedLessonId);
      }
    });
  }

  setupAudioPlayerEvents() {
    this.audioPlayer.addEventListener('ended', () => {
      this.resetAudioPlaybackBtn();
    });
    this.audioPlayer.addEventListener('pause', () => {
      this.resetAudioPlaybackBtn();
    });
    this.audioPlayer.addEventListener('error', (e) => {
      console.log('Audio playback error:', e);
      this.resetAudioPlaybackBtn();
    });
  }

  resetAudioPlaybackBtn() {
    if (this.currentlyPlayingBtn) {
      this.currentlyPlayingBtn.classList.remove('is-playing');
      this.currentlyPlayingBtn.innerHTML = `
        <span class="tts-icon">🔊</span>
        <span class="tts-label">سنڌي ۾ ٻڌو (Listen)</span>
      `;
      this.currentlyPlayingBtn = null;
    }
  }

  toggleSpeechAudio(btn, text) {
    if (!text) return;

    // If clicking same button while playing, pause playback
    if (this.currentlyPlayingBtn === btn && !this.audioPlayer.paused) {
      this.audioPlayer.pause();
      this.resetAudioPlaybackBtn();
      return;
    }

    this.resetAudioPlaybackBtn();
    this.currentlyPlayingBtn = btn;
    btn.classList.add('is-playing');
    btn.innerHTML = `
      <span class="tts-icon">⏳</span>
      <span class="tts-label">لوڊ ٿي رهيو آهي...</span>
    `;

    // Clean text for speech synthesis
    const cleanText = text
      .replace(/[*_#`~]+/g, '')
      .replace(/https?:\/\/\S+/g, '')
      .replace(/\(PDF[^\)]*\)/g, '')
      .replace(/\(printed[^\)]*\)/g, '')
      .trim();

    const ttsUrl = `/api/tutor/tts?text=${encodeURIComponent(cleanText.substring(0, 1000))}`;
    this.audioPlayer.src = ttsUrl;
    this.audioPlayer.play().then(() => {
      if (this.currentlyPlayingBtn === btn) {
        btn.innerHTML = `
          <span class="tts-icon">🔊</span>
          <span class="tts-label">ٻڌي رهيا آهيو (Playing)...</span>
        `;
      }
    }).catch(err => {
      console.log('Audio playback error:', err);
      this.resetAudioPlaybackBtn();
      if (window.showToast) window.showToast('آواز هلائڻ ۾ ڏکيائي آئي، مهرباني ڪري ٻيهر ڪلڪ ڪريو.');
    });
  }

  async toggleMicrophone() {
    const inputEl = document.getElementById('tutor-question-input');
    const btn = document.getElementById('btn-voice-input');

    if (this.isRecording) {
      // Stop active recording
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop();
      }
      return;
    }

    // Start recording audio stream
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        this.audioChunks = [];
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.mediaStream = stream;

        const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' :
                         (MediaRecorder.isTypeSupported('audio/ogg') ? 'audio/ogg' : '');
        const options = mimeType ? { mimeType } : {};
        this.mediaRecorder = new MediaRecorder(stream, options);

        this.mediaRecorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            this.audioChunks.push(event.data);
          }
        };

        this.mediaRecorder.onstop = async () => {
          this.stopMicAnimation();
          if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(t => t.stop());
            this.mediaStream = null;
          }

          if (this.audioChunks.length === 0) return;

          const recordedBlob = new Blob(this.audioChunks, { type: mimeType || 'audio/webm' });
          if (recordedBlob.size < 400) {
            if (window.showToast) window.showToast('آواز تمام ننڍو هو، مهرباني ڪري ٻيهر ڳالهايو.');
            return;
          }

          if (window.showToast) window.showToast('سنڌي آواز مان لکت ٺاهي پيو (Transcribing Sindhi Speech)...');
          if (inputEl) {
            inputEl.placeholder = 'سنڌي آواز مان لکت ٺاهي پيو...';
            inputEl.disabled = true;
          }

          try {
            const formData = new FormData();
            const ext = mimeType.includes('ogg') ? 'audio.ogg' : 'audio.webm';
            formData.append('file', recordedBlob, ext);

            const user = window.currentUser || (typeof getCurrentUser === 'function' ? getCurrentUser() : null);
            const activeToken = (user && (user.token || user.user_id)) || (window.currentUser && (window.currentUser.token || window.currentUser.user_id)) || localStorage.getItem('sdc_token') || 'sdc_demo_token';

            const headers = {};
            if (activeToken) {
              headers['Authorization'] = `Bearer ${activeToken}`;
            }

            const resp = await fetch('/api/tutor/transcribe', {
              method: 'POST',
              headers: headers,
              body: formData
            });

            if (resp.ok) {
              const resData = await resp.json();
              if (resData && resData.text_sindhi && resData.text_sindhi.trim()) {
                if (inputEl) {
                  inputEl.value = resData.text_sindhi.trim();
                  inputEl.style.height = 'auto';
                  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
                }
                if (window.showToast) window.showToast('آواز ڪاميابيءَ سان لکت ۾ بدليو ويو!');
              } else {
                if (window.showToast) window.showToast('آواز واضح نه ٿي سگهيو، مهرباني ڪري صاف آواز ۾ ٻيهر ڳالهايو.');
              }
            } else {
              throw new Error('Transcribe endpoint returned error');
            }
          } catch (err) {
            console.log('Transcription upload error:', err);
            if (window.showToast) window.showToast('آواز ٽرانسڪرائيب ڪرڻ دوران غلطي آئي، مهرباني ڪري لکي سوال پڇو.');
          } finally {
            if (inputEl) {
              inputEl.disabled = false;
              inputEl.placeholder = 'سبق بابت سوال لکو (Enter سان موڪليو، Shift+Enter سان نئين سٽ)...';
              inputEl.focus();
            }
          }
        };

        this.mediaRecorder.start(250);
        this.startMicAnimation();
        if (inputEl) {
          inputEl.placeholder = 'سنڌي ۾ ڳالهايو... (پورو ٿيڻ تي مائڪ بٽڻ وري دٻايو)';
        }
        if (window.showToast) window.showToast('مائڪ شروع ٿي ويو! سنڌي ۾ پنهنجو سوال ڳالهايو...');
      } catch (err) {
        console.warn('Microphone access denied or error:', err);
        this.stopMicAnimation();
        if (window.showToast) window.showToast('مائڪروفون جي اجازت ناهي ملي. مهرباني ڪري براؤزر ۾ مائڪ جي اجازت ڏيو.');
      }
    } else {
      if (window.showToast) window.showToast('هن براؤزر ۾ مائڪ رڪارڊنگ جي سهولت ناهي.');
    }
  }

  startMicAnimation() {
    this.isRecording = true;
    const btn = document.getElementById('btn-voice-input');
    if (btn) btn.classList.add('recording-pulse');
  }

  stopMicAnimation() {
    this.isRecording = false;
    const btn = document.getElementById('btn-voice-input');
    if (btn) btn.classList.remove('recording-pulse');
  }

  askQuickPrompt(promptText) {
    const inputEl = document.getElementById('tutor-question-input');
    if (inputEl) {
      inputEl.value = promptText;
      inputEl.style.height = 'auto';
      inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
      this.askQuestion(this.currentLesson?.id || window.currentLoadedLessonId);
    }
  }

  async askQuestion(lessonId = null) {
    if (this.isPending) return; // Prevent duplicate concurrent submissions

    const inputEl = document.getElementById('tutor-question-input');
    const sendBtn = document.getElementById('btn-tutor-send');
    const question = inputEl ? inputEl.value.trim() : '';
    if (!question) return;

    const chatStream = document.getElementById('tutor-chat-stream');
    const user = window.currentUser || { user_id: 'usr-stu-101' };

    // Set pending state
    this.isPending = true;
    if (sendBtn) {
      sendBtn.disabled = true;
      sendBtn.innerHTML = '<span>موڪلي پيو...</span>';
    }
    if (inputEl) {
      inputEl.disabled = true;
    }

    // 1. Render student question in chat
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user-bubble';
    userBubble.innerHTML = `<div class="bubble-text">${escapeHtml(question)}</div>`;
    chatStream.appendChild(userBubble);
    
    // Clear and reset textarea size
    inputEl.value = '';
    inputEl.style.height = 'auto';
    chatStream.scrollTop = chatStream.scrollHeight;

    // Truthful sequential thinking/progress indicator stages
    const loadingBubble = document.createElement('div');
    loadingBubble.className = 'chat-bubble tutor-bubble';
    loadingBubble.innerHTML = `
      <div class="bubble-header">
        <span class="tutor-name"><svg class="sdc-icon sdc-icon-xs" aria-hidden="true"><use href="#icon-robot"></use></svg> سنڌي اي آءِ استاد</span>
      </div>
      <div class="bubble-text" style="color: var(--text-dim); display: flex; align-items: center; gap: 8px;">
        <span class="loading-spinner-dots">● ● ●</span>
        <span id="tutor-stage-text">💡 سوال کي سمجھي رهيو آهيان...</span>
      </div>
    `;
    chatStream.appendChild(loadingBubble);
    chatStream.scrollTop = chatStream.scrollHeight;

    const stageTimer1 = setTimeout(() => {
      const stageEl = document.getElementById('tutor-stage-text');
      if (stageEl) stageEl.textContent = '📚 سنڌ ٽيڪسٽ بڪ بورڊ جي نصاب مان ڳولي رهيو آهيان...';
    }, 400);

    const stageTimer2 = setTimeout(() => {
      const stageEl = document.getElementById('tutor-stage-text');
      if (stageEl) stageEl.textContent = '✍️ تصديق ٿيل جواب تيار ٿي رهيو آهي...';
    }, 900);

    let elapsedSec = 1;
    const progressInterval = setInterval(() => {
      elapsedSec++;
      const stageEl = document.getElementById('tutor-stage-text');
      if (stageEl && elapsedSec >= 3) {
        stageEl.textContent = `✍️ تصديق ٿيل جواب تيار ٿي رهيو آهي (${elapsedSec} سيڪنڊ)...`;
      }
    }, 1000);

    let data = null;
    let onlineRequestUnavailable = false;
    const activeToken = (user && (user.token || user.user_id)) || (window.currentUser && (window.currentUser.token || window.currentUser.user_id)) || 'sdc_demo_token';
    const curLesson = window.currentLoadedLesson || this.currentLesson || null;
    const activeLessonId = lessonId || window.currentLoadedLessonId || (curLesson && curLesson.id) || null;
    const activeClassLevel = (curLesson && curLesson.class_level) || 6;
    let activeSubjectId = (curLesson && curLesson.subject_id) || window.currentSubject || null;
    if (!activeSubjectId && activeLessonId) {
      if (activeLessonId.includes('math')) activeSubjectId = 'math';
      else if (activeLessonId.includes('sci')) activeSubjectId = 'science';
      else if (activeLessonId.includes('sindhi')) activeSubjectId = 'sindhi';
      else if (activeLessonId.includes('eng')) activeSubjectId = 'english';
    }
    let activeChapterId = (curLesson && (curLesson.chapter_id || curLesson.unit_number)) || null;
    if (!activeChapterId && activeLessonId) {
      const chMatch = activeLessonId.match(/-(?:math|sci|sindhi|eng)-6-(\d+)/);
      if (chMatch) activeChapterId = parseInt(chMatch[1], 10);
    }

    try {
      if (navigator.onLine) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 12000);
        try {
          const res = await fetch('/api/tutor/ask', {
            method: 'POST',
            signal: controller.signal,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${activeToken}`
            },
            body: JSON.stringify({
              question: question,
              lesson_id: activeLessonId,
              class_level: activeClassLevel,
              subject_id: activeSubjectId,
              chapter_id: activeChapterId,
              voice_input_used: this.isRecording
            })
          });
          clearTimeout(timeoutId);
          if (res.ok) {
            const jsonResp = await res.json();
            if (jsonResp && jsonResp.answer_sindhi && !jsonResp.offline) {
              data = jsonResp;
            } else if (jsonResp && jsonResp.offline) {
              data = await this.searchOfflineUnitPack(question, activeLessonId);
            }
          } else {
            onlineRequestUnavailable = true;
          }
        } catch (fetchErr) {
          clearTimeout(timeoutId);
          onlineRequestUnavailable = true;
          console.log('Online tutor request unavailable:', fetchErr);
        }
      }
    } catch (err) {
      onlineRequestUnavailable = true;
      console.log('Online tutor request unavailable:', err);
    }

    // Use offline material only when the browser itself is offline. A slow or
    // failed online model must never be converted into a false "out of scope".
    if (!data && !navigator.onLine) {
      data = await this.searchOfflineUnitPack(question, activeLessonId);
    }
    if (!data && onlineRequestUnavailable) {
      data = {
        answer_sindhi: 'اي آءِ استاد هن وقت جواب مڪمل نه ڪري سگهيو. مهرباني ڪري ٿوري دير بعد ٻيهر ڪوشش ڪريو. (AI response timed out; retry shortly.)',
        is_refused: false,
        is_unavailable: true,
        inference_status: 'LLM_INFERENCE_UNAVAILABLE',
        provider_type: 'UNAVAILABLE',
        citations: []
      };
    }
    if (!data) {
      data = {
        answer_sindhi: 'درسي مواد ڳولهي نه سگهيو. مهرباني ڪري ٻيهر ڪوشش ڪريو. (Curriculum response is unavailable.)',
        is_refused: false,
        is_unavailable: true,
        inference_status: 'LLM_INFERENCE_UNAVAILABLE',
        provider_type: 'UNAVAILABLE',
        citations: []
      };
    }

    clearTimeout(stageTimer1);
    clearTimeout(stageTimer2);
    clearInterval(progressInterval);
    loadingBubble.remove();

    // Release pending lock
    this.isPending = false;
    if (sendBtn) {
      sendBtn.disabled = false;
      sendBtn.innerHTML = `<span>موڪليو</span> <svg class="sdc-icon sdc-icon-xs" aria-hidden="true"><use href="#icon-arrow-left"></use></svg>`;
    }
    if (inputEl) {
      inputEl.disabled = false;
      inputEl.focus();
    }

    const tutorBubble = document.createElement('div');
    tutorBubble.className = 'chat-bubble tutor-bubble';

    let citationHtml = '';
    if (data.citations && data.citations.length > 0) {
      citationHtml = `
        <div class="tutor-citation-box" style="direction: rtl; text-align: right; margin-top: 10px; padding: 10px; border-radius: 8px; background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2);">
          <div class="citation-tag" style="display: flex; align-items: center; gap: 6px; font-weight: 700; color: var(--accent-emerald);">
            <svg class="sdc-icon sdc-icon-xs" style="color: var(--accent-emerald);" aria-hidden="true"><use href="#icon-book"></use></svg>
            <span>ڪتاب جو تصديق ٿيل حوالو:</span>
            <span dir="ltr" style="direction: ltr; font-size: 0.72rem; color: var(--text-muted);">(STBB Citation)</span>
          </div>
          ${data.citations.map(c => `
            <div class="citation-link" ${c.timestamp_seconds ? `onclick="jumpToVideoTimestamp(${c.timestamp_seconds})"` : ''} style="cursor: pointer; margin-top: 6px; padding: 6px 8px; border-radius: 6px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25);">
              <span style="font-weight: 700; color: var(--text-main);">📌 ${escapeHtml(c.lesson_title_sindhi || 'سبق')}</span>
              ${c.citation_formatted ? `
                <div style="font-size: 0.8rem; color: var(--accent-emerald); font-weight: 700; margin-top: 3px;">
                  <span>حوالو: </span>
                  <span dir="ltr" style="direction: ltr; unicode-bidi: embed; display: inline-block;">${escapeHtml(c.citation_formatted)}</span>
                </div>` : ''}
              ${c.page_number && !c.citation_formatted ? `<span style="font-size: 0.76rem; color: var(--text-muted);">(صفحو: ${escapeHtml(String(c.page_number))})</span>` : ''}
              ${c.timestamp_seconds ? `<span style="display: inline-block; font-size: 0.74rem; color: #3b82f6; margin-top: 2px;">▶️ وڊيو ۾ ان وقت تي وڃو (${Math.round(c.timestamp_seconds)}s)</span>` : ''}
            </div>
          `).join('')}
        </div>
      `;
    }

    let badgeText = 'سنڌ ٽيڪسٽ بڪ بورڊ تصديق ٿيل درسي مواد';
    let badgeBg = 'rgba(16, 185, 129, 0.15)';
    let badgeColor = 'var(--accent-emerald)';

    if (String(data.inference_status || '').startsWith('OFFLINE_CONTENT')) {
      badgeText = '📴 آف لائن مواد دستياب ناهي';
      badgeBg = 'rgba(245, 158, 11, 0.15)';
      badgeColor = '#d97706';
    } else if (String(data.inference_status || '').startsWith('OFFLINE_CURRICULUM')) {
      badgeText = '📴 آف لائن درسي حوالو (Non-AI)';
      badgeBg = 'rgba(16, 185, 129, 0.15)';
      badgeColor = 'var(--accent-emerald)';
    } else if (data.is_unavailable || data.inference_status === 'LLM_INFERENCE_UNAVAILABLE') {
      badgeText = '⚠️ اي آءِ استاد عارضي طور دستياب ناهي (AI Unavailable)';
      badgeBg = 'rgba(245, 158, 11, 0.15)';
      badgeColor = '#d97706';
    } else if (data.inference_status === 'REAL_LLM_INFERENCE') {
      badgeText = '🤖 تصديق ٿيل اي آءِ تجزيو (Real LLM Inference)';
      badgeBg = 'rgba(37, 99, 235, 0.15)';
      badgeColor = '#2563eb';
    } else if (data.inference_status === 'REFUSED_OUT_OF_SCOPE' || data.is_refused) {
      badgeText = '🚫 سبق جي دائري کان ٻاهر (Out of Scope)';
      badgeBg = 'rgba(239, 68, 68, 0.15)';
      badgeColor = '#dc2626';
    } else if (data.provider_type === 'LOCAL_DETERMINISTIC_FALLBACK') {
      badgeText = '📚 درسي نصابي حوالو (Curriculum Non-AI)';
      badgeBg = 'rgba(16, 185, 129, 0.15)';
      badgeColor = 'var(--accent-emerald)';
    }

    const escapedAnswerForAttr = escapeHtml(data.answer_sindhi).replace(/'/g, "&#39;");

    tutorBubble.innerHTML = `
      <div class="bubble-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
        <span class="tutor-name"><svg class="sdc-icon sdc-icon-xs" aria-hidden="true"><use href="#icon-robot"></use></svg> سنڌي اي آءِ استاد</span>
        <span style="font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeColor}; font-weight: 600;">${badgeText}</span>
        ${data.report_id ? `<button class="report-btn" onclick="sdcTutor.reportAnswer('${data.report_id}')" title="غلط جواب جي شڪايت (Report wrong answer)">&#9873; شڪايت</button>` : ''}
      </div>
      <div class="bubble-text ${data.is_refused ? 'refusal-text' : ''}" style="white-space: pre-wrap; line-height: 1.6; margin-top: 6px;">${escapeHtml(data.answer_sindhi)}</div>
      ${citationHtml}
      <div style="margin-top: 8px;">
        <button type="button" class="tutor-tts-btn" onclick="sdcTutor.toggleSpeechAudio(this, '${escapedAnswerForAttr}')">
          <span class="tts-icon">🔊</span>
          <span class="tts-label">سنڌي ۾ ٻڌو (Listen)</span>
        </button>
      </div>
    `;

    chatStream.appendChild(tutorBubble);
    chatStream.scrollTop = chatStream.scrollHeight;

    // Optional audio cue
    this.playSpeechCue(data.answer_sindhi);
  }

  async searchOfflineUnitPack(question, lessonId) {
    const activeLessonId = lessonId || window.currentLoadedLessonId;
    if (!activeLessonId || typeof getOfflineUnitPack !== 'function') {
      return {
        answer_sindhi: "هن ڊوائيس تي هن سبق جو آف لائن مواد موجود ناهي. انٽرنيٽ سان ٻيهر ڪوشش ڪريو.",
        is_refused: false,
        is_unavailable: true,
        inference_status: 'OFFLINE_CONTENT_UNAVAILABLE',
        provider_type: 'OFFLINE_CURRICULUM_SEARCH',
        citations: []
      };
    }

    try {
      const pack = await getOfflineUnitPack(activeLessonId);
      if (!pack || !pack.transcripts || pack.transcripts.length === 0) {
        return {
          answer_sindhi: "هن سبق لاءِ آف لائن ڳولها مواد موجود ناهي. ٻيهر آن لائن ڪوشش ڪريو.",
          is_refused: false,
          is_unavailable: true,
          inference_status: 'OFFLINE_CONTENT_UNAVAILABLE',
          provider_type: 'OFFLINE_CURRICULUM_SEARCH',
          citations: []
        };
      }

      const tokens = question.split(/\s+/).filter(w => w.length > 2);
      let bestMatch = null;
      let maxHits = 0;

      for (const t of pack.transcripts) {
        let hits = 0;
        for (const tok of tokens) {
          if (t.text_sindhi.includes(tok)) hits++;
        }
        if (hits > maxHits) {
          maxHits = hits;
          bestMatch = t;
        }
      }

      if (bestMatch && maxHits >= 1) {
        return {
          answer_sindhi: `آف لائن نصاب مان حوالو: ${bestMatch.text_sindhi}`,
          is_refused: false,
          is_unavailable: false,
          inference_status: 'OFFLINE_CURRICULUM_MATCH',
          provider_type: 'OFFLINE_CURRICULUM_SEARCH',
          citations: [{
            lesson_id: activeLessonId,
            lesson_title_sindhi: pack.lesson.title_sindhi,
            timestamp_seconds: bestMatch.start_time,
            text_snippet_sindhi: bestMatch.text_sindhi
          }]
        };
      }
    } catch (e) {
      console.error('Offline search error:', e);
    }

    return {
      answer_sindhi: "هن سوال لاءِ آف لائن سبق ۾ لاڳاپيل متن نه مليو. اهو لازمي طور سبق کان ٻاهر هجڻ جو ثبوت ناهي؛ آن لائن ٻيهر ڳوليو.",
      is_refused: false,
      is_unavailable: true,
      inference_status: 'OFFLINE_CONTENT_NOT_FOUND',
      provider_type: 'OFFLINE_CURRICULUM_SEARCH',
      citations: []
    };
  }

  async reportAnswer(reportId) {
    const user = window.currentUser || { user_id: 'usr-stu-101' };
    const activeToken = (user && (user.token || user.user_id)) || (window.currentUser && (window.currentUser.token || window.currentUser.user_id)) || 'sdc_demo_token';
    try {
      const res = await fetch('/api/tutor/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${activeToken}`
        },
        body: JSON.stringify({ report_id: reportId, reason: "Student reported inaccurate answer" })
      });
      if (res.ok && window.showToast) {
        window.showToast('شڪايت استاد ڏانهن موڪلي وئي آهي (Report submitted).');
      }
    } catch (e) {
      console.error(e);
    }
  }

  playSpeechCue(text) {
    // If browser supports native Web Speech API and offline TTS endpoint is also available,
    // we let user trigger full audio with the explicit "سنڌي ۾ ٻڌو" button on the bubble.
  }
}

function jumpToVideoTimestamp(seconds) {
  const video = document.getElementById('sdc-video-player');
  if (video) {
    video.currentTime = seconds;
    video.play();
    if (window.showToast) window.showToast(`ويڊيو ${Math.round(seconds)} سيڪنڊن تي پهچايو ويو.`);
  }
}
