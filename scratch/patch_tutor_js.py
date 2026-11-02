# -*- coding: utf-8 -*-
import sys

with open("static/js/tutor.js", "r", encoding="utf-8") as f:
    code = f.read()

old_block = """    // Loading indicator
    const loadingBubble = document.createElement('div');
    loadingBubble.className = 'chat-bubble tutor-bubble';
    loadingBubble.innerHTML = `
      <div class="bubble-header">
        <span class="tutor-name"><svg class="sdc-icon sdc-icon-xs" aria-hidden="true"><use href="#icon-robot"></use></svg> سنڌي اي آءِ استاد</span>
      </div>
      <div class="bubble-text" style="color: var(--text-dim); display: flex; align-items: center; gap: 8px;">
        <span class="loading-spinner-dots">● ● ●</span>
        <span>سنڌ ٽيڪسٽ بڪ بورڊ نصاب مان تصديق ٿيل جواب ڳولي رهيو آهي...</span>
      </div>
    `;
    chatStream.appendChild(loadingBubble);
    chatStream.scrollTop = chatStream.scrollHeight;

    let data = null;
    const activeToken = (user && (user.token || user.user_id)) || (window.currentUser && (window.currentUser.token || window.currentUser.user_id)) || 'sdc_demo_token';
    const activeLessonId = lessonId || window.currentLoadedLessonId;

    try {
      if (navigator.onLine) {
        const res = await fetch('/api/tutor/ask', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${activeToken}`
          },
          body: JSON.stringify({
            question: question,
            lesson_id: activeLessonId,
            voice_input_used: this.isRecording
          })
        });
        if (res.ok) {
          const jsonResp = await res.json();
          if (jsonResp && jsonResp.answer_sindhi && !jsonResp.offline) {
            data = jsonResp;
          }
        }
      }
    } catch (err) {
      console.log('Online tutor request failed, falling back to offline search:', err);
    }

    // Offline search fallback if server is unreachable or offline response returned
    if (!data || !data.answer_sindhi) {
      data = await this.searchOfflineUnitPack(question, activeLessonId);
    }

    loadingBubble.remove();"""

new_block = """    // Truthful sequential thinking/progress indicator stages
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

    let data = null;
    const activeToken = (user && (user.token || user.user_id)) || (window.currentUser && (window.currentUser.token || window.currentUser.user_id)) || 'sdc_demo_token';
    const activeLessonId = lessonId || window.currentLoadedLessonId || (window.currentLoadedLesson && window.currentLoadedLesson.id) || null;
    const curLesson = window.currentLoadedLesson;
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
      const chMatch = activeLessonId.match(/-(?:math|sci|sindhi|eng)-6-(\\d+)/);
      if (chMatch) activeChapterId = parseInt(chMatch[1], 10);
    }

    try {
      if (navigator.onLine) {
        const res = await fetch('/api/tutor/ask', {
          method: 'POST',
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
        if (res.ok) {
          const jsonResp = await res.json();
          if (jsonResp && jsonResp.answer_sindhi && !jsonResp.offline) {
            data = jsonResp;
          }
        }
      }
    } catch (err) {
      console.log('Online tutor request failed, falling back to offline search:', err);
    }

    // Offline search fallback if server is unreachable or offline response returned
    if (!data || !data.answer_sindhi) {
      data = await this.searchOfflineUnitPack(question, activeLessonId);
    }

    clearTimeout(stageTimer1);
    clearTimeout(stageTimer2);
    loadingBubble.remove();"""

# Citation Box and Bubble Template update
old_render_block = """    let citationHtml = '';
    if (data.citations && data.citations.length > 0) {
      citationHtml = `
        <div class="tutor-citation-box">
          <span class="citation-tag">
            <svg class="sdc-icon sdc-icon-xs" style="color: var(--accent-emerald);" aria-hidden="true"><use href="#icon-book"></use></svg>
            <span>ڪتاب جو تصديق ٿيل حوالو (STBB Citation):</span>
          </span>
          ${data.citations.map(c => `
            <div class="citation-link" ${c.timestamp_seconds ? `onclick="jumpToVideoTimestamp(${c.timestamp_seconds})"` : ''} style="cursor: pointer; margin-top: 4px;">
              <span>📌 ${escapeHtml(c.lesson_title_sindhi || 'سبق')}</span>
              ${c.citation_formatted ? `<span style="display: block; font-size: 0.78rem; color: var(--accent-emerald); font-weight: 700;">حوالو: ${escapeHtml(c.citation_formatted)}</span>` : ''}
              ${c.page_number && !c.citation_formatted ? `<span style="font-size: 0.76rem; color: var(--text-muted);">(صفحو: ${escapeHtml(String(c.page_number))})</span>` : ''}
              ${c.timestamp_seconds ? `<span style="display: inline-block; font-size: 0.74rem; color: #3b82f6; margin-top: 2px;">▶️ وڊيو ۾ ان وقت تي وڃو (${Math.round(c.timestamp_seconds)}s)</span>` : ''}
            </div>
          `).join('')}
        </div>
      `;
    }

    const statusBadge = navigator.onLine ? 'آن لائن' : 'آف لائن';
    const escapedAnswerForAttr = escapeHtml(data.answer_sindhi).replace(/'/g, "&#39;");

    tutorBubble.innerHTML = `
      <div class="bubble-header">
        <span class="tutor-name"><svg class="sdc-icon sdc-icon-xs" aria-hidden="true"><use href="#icon-robot"></use></svg> سنڌي اي آءِ استاد (${statusBadge})</span>
        ${data.report_id ? `<button class="report-btn" onclick="sdcTutor.reportAnswer('${data.report_id}')" title="غلط جواب جي شڪايت (Report wrong answer)">&#9873; شڪايت</button>` : ''}
      </div>
      <div class="bubble-text ${data.is_refused ? 'refusal-text' : ''}">${escapeHtml(data.answer_sindhi)}</div>
      ${citationHtml}
      <div style="margin-top: 8px;">
        <button type="button" class="tutor-tts-btn" onclick="sdcTutor.toggleSpeechAudio(this, '${escapedAnswerForAttr}')">
          <span class="tts-icon">🔊</span>
          <span class="tts-label">سنڌي ۾ ٻڌو (Listen)</span>
        </button>
      </div>
    `;"""

new_render_block = """    let citationHtml = '';
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

    const isLive = data.inference_status === 'REAL_LLM_INFERENCE' || (data.provider_type && data.provider_type.includes('NEURAL'));
    const badgeText = isLive ? `اي آءِ تجزيو (${data.model_name || 'Neural'})` : 'سنڌ ٽيڪسٽ بڪ بورڊ تصديق ٿيل درسي مواد';
    const badgeBg = isLive ? 'rgba(59, 130, 246, 0.15)' : 'rgba(16, 185, 129, 0.15)';
    const badgeColor = isLive ? '#3b82f6' : 'var(--accent-emerald)';

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
    `;"""

code_lf = code.replace("\r\n", "\n")
assert old_block in code_lf, "old_block not found in tutor.js"
assert old_render_block in code_lf, "old_render_block not found in tutor.js"

code_lf = code_lf.replace(old_block, new_block, 1)
code_lf = code_lf.replace(old_render_block, new_render_block, 1)

with open("static/js/tutor.js", "w", encoding="utf-8", newline="\r\n") as f:
    f.write(code_lf)

print("static/js/tutor.js successfully patched!")

