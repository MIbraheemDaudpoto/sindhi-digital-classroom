// Sindhi Digital Classroom (SDC) - Robust Video Player Component
// Supports Local MP4/HLS playback, Official YouTube Embeds, and Offline Fallbacks.
// Authored under agency-frontend-developer and agency-ux-architect.

class SDCVideoPlayer {
  constructor(videoElementId, quizOverlayId) {
    this.video = document.getElementById(videoElementId);
    this.youtubeIframe = document.getElementById('sdc-youtube-iframe');
    this.quizOverlay = document.getElementById(quizOverlayId);
    this.errorCard = document.getElementById('video-error-state');
    this.youtubeBanner = document.getElementById('youtube-attribution-banner');
    this.youtubeOfflineBanner = document.getElementById('youtube-offline-banner');
    this.audioOverlay = document.getElementById('audio-only-overlay');
    
    this.currentLesson = null;
    this.questions = [];
    this.triggeredQuestionIds = new Set();
    this.completedQuestionIds = new Set();
    this.lastObservedTime = 0;
    this.activeQuestion = null;
    this.isAudioOnly = false;
    this.activeSourceType = 'LOCAL'; // 'LOCAL' or 'YOUTUBE'
    this.ytPlayer = null;
    this.ytCurrentTime = 0;
    this.ytDuration = 0;
    this.isYtReady = false;
    this.isYtPlaying = false;
    this.isPlaying = false;
    this._keyHandler = null;
    
    this.initYouTubeApi();
    this.setupListeners();
  }

  initYouTubeApi() {
    // Listen for postMessage from YouTube iframe
    window.addEventListener('message', (event) => {
      try {
        if (typeof event.data === 'string') {
          const data = JSON.parse(event.data);
          if (data.event === 'infoDelivery' && data.info) {
            if (typeof data.info.playerState === 'number') {
              this.isYtPlaying = (data.info.playerState === 1);
              this.isPlaying = this.isYtPlaying;
              if (data.info.playerState === 0) {
                this.onVideoPlaybackEnded();
              }
            }
            if (typeof data.info.currentTime === 'number') {
              this.ytCurrentTime = data.info.currentTime;
              if (this.activeSourceType === 'YOUTUBE' && this.isYtPlaying) {
                this.checkQuizPopups(this.ytCurrentTime);
              }
            }
            if (typeof data.info.duration === 'number') {
              this.ytDuration = data.info.duration;
            }
          }
        }
      } catch (e) {}
    });

    // Request periodic info from YouTube iframe (400ms polling interval)
    setInterval(() => {
      if (this.activeSourceType === 'YOUTUBE' && this.youtubeIframe && this.youtubeIframe.contentWindow) {
        this.sendYouTubeCommand('listening');
        if (this.ytPlayer && typeof this.ytPlayer.getCurrentTime === 'function') {
          try {
            if (typeof this.ytPlayer.getPlayerState === 'function') {
              this.isYtPlaying = (this.ytPlayer.getPlayerState() === 1);
              this.isPlaying = this.isYtPlaying;
            }
            const cur = this.ytPlayer.getCurrentTime();
            if (typeof cur === 'number' && !isNaN(cur)) {
              this.ytCurrentTime = cur;
              if (this.isYtPlaying) {
                this.checkQuizPopups(cur);
              }
            }
          } catch(e) {}
        }
      }
    }, 400);
  }

  sendYouTubeCommand(func, args) {
    if (!this.youtubeIframe || !this.youtubeIframe.contentWindow) return;
    try {
      this.youtubeIframe.contentWindow.postMessage(JSON.stringify({
        event: 'command',
        func: func,
        args: args || []
      }), '*');
    } catch (e) {
      console.warn('[SDC Player] YouTube postMessage failed:', e);
    }
  }

  setupListeners() {
    if (this.video) {
      this.video.addEventListener('play', () => {
        this.isPlaying = true;
      });

      this.video.addEventListener('playing', () => {
        this.isPlaying = true;
      });

      this.video.addEventListener('pause', () => {
        this.isPlaying = false;
      });

      this.video.addEventListener('waiting', () => {
        this.isPlaying = false;
      });

      this.video.addEventListener('timeupdate', () => {
        this.checkQuizPopups();
      });

      this.video.addEventListener('seeking', () => {
        this.handleSeeking();
      });

      this.video.addEventListener('seeked', () => {
        this.handleSeeked();
      });

      this.video.addEventListener('ended', () => {
        if (this.currentLesson) {
          const expectedDur = this.currentLesson.duration_seconds || 600;
          if (this.video.duration < 30.0 && expectedDur > 60.0) {
            // Short demo/placeholder video - record watch position but do NOT falsely mark 100% completed
            this.saveProgress(this.video.currentTime, false);
            if (window.showToast) {
              window.showToast('هي مختصر نمونو (Demo Video) هو. مڪمل سبق لاءِ درسي ڪتاب جا نوٽس ڏسو.');
            }
          } else {
            this.saveProgress(this.video.currentTime, true);
            if (window.showToast) window.showToast('سبق مڪمل ٿي ويو! شاباس.');
          }
        }
      });

      this.video.addEventListener('error', (e) => {
        this.handleVideoError(e);
      });

      this.video.addEventListener('canplay', () => {
        this.hideError();
      });

      // Periodic progress bookmark every 15s (FR-08)
      setInterval(() => {
        if (this.video && !this.video.paused && this.currentLesson && this.activeSourceType === 'LOCAL') {
          this.saveProgress(this.video.currentTime, false);
        }
      }, 15000);
    }

    // Monitor online/offline events for YouTube embed handling
    window.addEventListener('online', () => {
      if (this.currentLesson && this.activeSourceType === 'YOUTUBE') {
        this.loadLesson(this.currentLesson, this.questions);
      }
    });

    window.addEventListener('offline', () => {
      if (this.currentLesson && this.activeSourceType === 'YOUTUBE') {
        this.showYouTubeOfflineState();
      }
    });
  }

  getStudentId() {
    try {
      if (window.currentUser && (window.currentUser.user_id || window.currentUser.id)) {
        return window.currentUser.user_id || window.currentUser.id;
      }
      const raw = localStorage.getItem('sdc_current_user') || localStorage.getItem('sdc_user');
      if (raw) {
        const u = JSON.parse(raw);
        if (u && (u.user_id || u.id)) return u.user_id || u.id;
      }
    } catch(e) {}
    return 'usr-stu-101';
  }

  loadLesson(lessonDetail, approvedQuestions) {
    this.currentLesson = lessonDetail;
    this.questions = (approvedQuestions || []).sort((a, b) => (a.timestamp_seconds || 0) - (b.timestamp_seconds || 0));
    this.triggeredQuestionIds.clear();
    this.completedQuestionIds.clear();
    this.lastObservedTime = 0;
    this.hideError();

    // Restore completed checkpoints from localStorage for this student & lesson
    const uid = this.getStudentId();
    const savedCompletedKey = `sdc_checkpoints_${uid}_${lessonDetail.id}`;
    try {
      const saved = localStorage.getItem(savedCompletedKey);
      if (saved) {
        const arr = JSON.parse(saved);
        if (Array.isArray(arr)) {
          arr.forEach(id => {
            this.completedQuestionIds.add(id);
            this.triggeredQuestionIds.add(id);
          });
        }
      }
    } catch (e) {}

    // Also mark questions with server is_completed flag
    this.questions.forEach(q => {
      if (q.is_completed) {
        this.completedQuestionIds.add(q.id);
        this.triggeredQuestionIds.add(q.id);
      }
    });

    // Reset audio-only display on new lesson
    if (this.isAudioOnly) {
      this.toggleAudioOnly(false);
    }

    // Determine source: YouTube vs Local MP4
    const yt = lessonDetail.youtube_video;
    if (lessonDetail.video_source_type === 'YOUTUBE' && yt && yt.is_embeddable) {
      this.setupYouTubePlayer(yt);
    } else {
      this.setupLocalPlayer(lessonDetail);
    }

    this.renderCheckpointTimelineMarkers();

    // Update Resume banner if student left previously
    const resumeCard = document.getElementById('continue-learning-card');
    if (resumeCard) {
      if (lessonDetail.last_position_seconds > 5.0 && !lessonDetail.is_completed) {
        resumeCard.style.display = 'flex';
        const mins = Math.floor(lessonDetail.last_position_seconds / 60);
        const secs = Math.round(lessonDetail.last_position_seconds % 60);
        const timeEl = document.getElementById('continue-lesson-time');
        if (timeEl) timeEl.textContent = `آخري جاءِ: ${mins} منٽ ${secs} سيڪنڊ`;
        const titleEl = document.getElementById('continue-lesson-title');
        if (titleEl) titleEl.textContent = lessonDetail.title_sindhi;
      } else {
        resumeCard.style.display = 'none';
      }
    }
  }

  setupYouTubePlayer(yt) {
    this.activeSourceType = 'YOUTUBE';
    this.ytCurrentTime = 0;

    // Hide local video & error card
    if (this.video) {
      this.video.pause();
      this.video.style.display = 'none';
    }
    if (this.youtubeOfflineBanner) this.youtubeOfflineBanner.style.display = 'none';
    if (this.errorCard) this.errorCard.style.display = 'none';

    // Show YouTube iframe with standard embed
    if (this.youtubeIframe) {
      const origin = window.location.origin;
      const targetSrc = `https://www.youtube.com/embed/${yt.youtube_id}?enablejsapi=1&origin=${encodeURIComponent(origin)}&autoplay=1&rel=0&modestbranding=1`;
      if (this.youtubeIframe.src !== targetSrc) {
        this.youtubeIframe.src = targetSrc;
      }
      this.youtubeIframe.style.display = 'block';

      if (window.YT && window.YT.Player) {
        try {
          if (!this.ytPlayer) {
            this.ytPlayer = new YT.Player('sdc-youtube-iframe', {
              events: {
                'onStateChange': (event) => {
                  this.isYtPlaying = (event.data === 1);
                  this.isPlaying = this.isYtPlaying;
                  if (event.data === 1 && this.activeQuestion) {
                    try { this.ytPlayer.pauseVideo(); } catch(e) {}
                  }
                  if (event.data === 0) {
                    this.onVideoPlaybackEnded();
                  }
                }
              }
            });
          }
        } catch(e) {}
      }
    }

    // Display official YouTube attribution banner
    if (this.youtubeBanner) {
      this.youtubeBanner.style.display = 'flex';
      const chEl = document.getElementById('yt-channel-name');
      if (chEl) chEl.textContent = yt.channel_name || 'Official Educational Channel';
      const titEl = document.getElementById('yt-video-title');
      if (titEl) titEl.textContent = yt.title || '';
      const linkEl = document.getElementById('yt-original-link');
      if (linkEl) linkEl.href = yt.original_url || `https://www.youtube.com/watch?v=${yt.youtube_id}`;
    }

    // Configure source switch button
    const switchBtn = document.getElementById('btn-switch-source');
    if (switchBtn) {
      switchBtn.style.display = 'inline-flex';
      switchBtn.textContent = '🔄 لوڪل وڊيو';
      switchBtn.title = 'لوڪل ويڊيو يا ايم پي 4 پليئر تي تبديل ڪريو';
    }
  }

  showYouTubeOfflineState() {
    if (this.youtubeIframe) {
      this.youtubeIframe.src = '';
      this.youtubeIframe.style.display = 'none';
    }
    if (this.video) this.video.style.display = 'none';
    if (this.youtubeBanner) this.youtubeBanner.style.display = 'none';
    if (this.youtubeOfflineBanner) this.youtubeOfflineBanner.style.display = 'flex';
  }

  switchToLocalOrTranscript() {
    if (this.youtubeOfflineBanner) this.youtubeOfflineBanner.style.display = 'none';
    this.setupLocalPlayer(this.currentLesson);
    if (window.showToast) {
      window.showToast('لوڪل وڊيو ۽ آف لائن سوال چالو ڪيا ويا.');
    }
  }

  setupLocalPlayer(lessonDetail) {
    this.activeSourceType = 'LOCAL';

    if (this.youtubeIframe) {
      this.youtubeIframe.src = '';
      this.youtubeIframe.style.display = 'none';
    }
    if (this.youtubeBanner) this.youtubeBanner.style.display = 'none';
    if (this.youtubeOfflineBanner) this.youtubeOfflineBanner.style.display = 'none';

    if (this.video) {
      this.video.style.display = 'block';
      const videoSrc = lessonDetail.video_fallback_url || `/static/media/${lessonDetail.id}.mp4`;
      this.video.src = videoSrc;
      this.video.load();

      // Resume position (FR-08)
      if (lessonDetail.last_position_seconds > 5.0 && !lessonDetail.is_completed) {
        this.video.currentTime = lessonDetail.last_position_seconds;
        this.lastObservedTime = lessonDetail.last_position_seconds;
      } else {
        this.lastObservedTime = 0;
      }

      this.video.play().catch(e => {
        console.log('[SDC Player] Autoplay paused or waiting for student interaction');
      });
    }

    this.renderCheckpointTimelineMarkers();

    const switchBtn = document.getElementById('btn-switch-source');
    if (switchBtn) {
      if (lessonDetail.youtube_video) {
        switchBtn.style.display = 'inline-flex';
        switchBtn.textContent = '🔄 يوٽيوب وڊيو';
        switchBtn.title = 'سرڪاري يوٽيوب پليئر تي واپس تبديل ڪريو';
      } else {
        switchBtn.style.display = 'none';
      }
    }
  }

  toggleVideoSource() {
    if (!this.currentLesson) return;
    if (this.activeSourceType === 'LOCAL' && this.currentLesson.youtube_video) {
      this.setupYouTubePlayer(this.currentLesson.youtube_video);
      if (window.showToast) window.showToast('سرڪاري يوٽيوب پليئر تي تبديل ڪيو ويو.');
    } else {
      this.setupLocalPlayer(this.currentLesson);
      if (window.showToast) window.showToast('لوڪل پليئر تي تبديل ڪيو ويو.');
    }
  }

  handleVideoError(err) {
    console.warn('[SDC Player] Video playback error encountered:', err);
    if (typeof window.updateLessonMediaStatus === 'function') {
      window.updateLessonMediaStatus(this.currentLesson ? this.currentLesson.id : null, false);
    }
    if (this.errorCard) {
      this.errorCard.style.display = 'flex';
      const descEl = document.getElementById('video-error-desc');
      if (descEl) {
        if (!navigator.onLine) {
          descEl.textContent = 'انٽرنيٽ ڪنيڪشن موجود ناهي يا وڊيو مقامي طور تي محفوظ نه آهي. توهان سبق جا نوٽس پڙهي، Tutor ۽ وڊيو کان الڳ ڪوئيز جاري رکي سگهو ٿا.';
        } else {
          descEl.textContent = 'هي سبق وڊيو هن وقت هلائي نه ٿي سگهي. نوٽس، Tutor ۽ ڪوئيز موجود رهن ٿا؛ وڊيو ٻيهر آزمائڻ لاءِ Retry چونڊيو.';
        }
      }
    }
  }

  hideError() {
    if (this.errorCard) this.errorCard.style.display = 'none';
    if (typeof window.updateLessonMediaStatus === 'function') {
      window.updateLessonMediaStatus(this.currentLesson ? this.currentLesson.id : null, true);
    }
  }

  retryCurrentVideo() {
    this.hideError();
    if (this.currentLesson) {
      this.loadLesson(this.currentLesson, this.questions);
    }
  }

  skipSeconds(secs) {
    if (this.activeSourceType === 'LOCAL' && this.video) {
      this.video.currentTime = Math.max(0, this.video.currentTime + secs);
      if (window.showToast) {
        window.showToast(secs > 0 ? `${secs} سيڪنڊ اڳتي` : `${Math.abs(secs)} سيڪنڊ پوئتي`);
      }
    } else if (this.activeSourceType === 'YOUTUBE') {
      const targetTime = Math.max(0, (this.ytCurrentTime || 0) + secs);
      this.ytCurrentTime = targetTime;
      this.sendYouTubeCommand('seekTo', [targetTime, true]);
      if (window.showToast) {
        window.showToast(secs > 0 ? `${secs} سيڪنڊ اڳتي (YouTube)` : `${Math.abs(secs)} سيڪنڊ پوئتي (YouTube)`);
      }
    }
  }

  toggleAudioOnly(forceState) {
    if (window.showToast) {
      window.showToast('رڳو آواز واري آڊيو فائل (MP3) سرور تي موجود ناهي؛ ڊيٽا سيوور موڊ بند آهي.');
    }
    const btn = document.getElementById('btn-audio-only');
    const audioOverlay = document.getElementById('audio-only-overlay');
    if (btn) {
      btn.classList.remove('active');
      btn.classList.add('disabled');
      btn.innerHTML = '&#128263; رڳو آواز (دستياب ناهي)';
      btn.title = 'مستقل آڊيو فائل سرور تي دستياب ناهي';
    }
    if (audioOverlay) audioOverlay.style.display = 'none';
    if (this.video) this.video.style.opacity = '1.0';
    if (this.youtubeIframe) this.youtubeIframe.style.opacity = '1.0';
  }

  renderCheckpointTimelineMarkers() {
    let track = document.getElementById('checkpoint-indicator-track');
    if (!track && this.video && this.video.parentElement) {
      track = document.createElement('div');
      track.id = 'checkpoint-indicator-track';
      track.className = 'checkpoint-indicator-track';
      this.video.parentElement.insertBefore(track, this.video.nextSibling);
    }
    if (!track) return;

    track.innerHTML = '';
    if (!this.questions || !this.questions.length) {
      track.style.display = 'none';
      return;
    }
    track.style.display = 'block';

    const dur = (this.video && this.video.duration && !isNaN(this.video.duration) && this.video.duration > 1.0)
      ? this.video.duration
      : (this.currentLesson ? (this.currentLesson.duration_seconds || 10) : 10);

    this.questions.forEach((q, idx) => {
      const pct = Math.min(100, Math.max(0, (q.timestamp_seconds / dur) * 100));
      const dot = document.createElement('div');
      const isDone = this.completedQuestionIds.has(q.id);
      dot.className = `checkpoint-dot ${isDone ? 'completed' : 'pending'}`;
      dot.id = `checkpoint-dot-${q.id}`;
      dot.style.left = `${pct}%`;
      const mins = Math.floor(q.timestamp_seconds / 60);
      const secs = String(Math.round(q.timestamp_seconds % 60)).padStart(2, '0');
      dot.title = `چيڪ پوائنٽ ${idx + 1} (${mins}:${secs}) - ${isDone ? 'حل ٿيل' : 'ٻڌو ۽ حل ڪريو'}`;

      dot.onclick = () => {
        const targetTime = Math.max(0, q.timestamp_seconds - 0.2);
        if (this.activeSourceType === 'LOCAL' && this.video) {
          this.video.currentTime = targetTime;
        } else if (this.activeSourceType === 'YOUTUBE') {
          this.ytCurrentTime = targetTime;
          this.sendYouTubeCommand('seekTo', [targetTime, true]);
          if (this.ytPlayer && typeof this.ytPlayer.seekTo === 'function') {
            try { this.ytPlayer.seekTo(targetTime, true); } catch(e) {}
          }
        }
      };
      track.appendChild(dot);
    });
  }

  checkQuizPopups(currentTimeOverride) {
    if (this.activeQuestion) return;

    // Check if player is actively playing before evaluating checkpoints
    let isPlaying = false;
    if (this.activeSourceType === 'LOCAL' && this.video) {
      isPlaying = !this.video.paused && !this.video.ended && this.video.readyState >= 2;
    } else if (this.activeSourceType === 'YOUTUBE') {
      if (this.ytPlayer && typeof this.ytPlayer.getPlayerState === 'function') {
        try {
          isPlaying = (this.ytPlayer.getPlayerState() === 1);
        } catch(e) {
          isPlaying = this.isYtPlaying;
        }
      } else {
        isPlaying = this.isYtPlaying;
      }
    }
    if (!isPlaying) return;

    let currentTime = 0;
    if (typeof currentTimeOverride === 'number') {
      currentTime = currentTimeOverride;
    } else if (this.activeSourceType === 'LOCAL' && this.video) {
      currentTime = this.video.currentTime;
    } else if (this.activeSourceType === 'YOUTUBE') {
      currentTime = this.ytCurrentTime || 0;
    } else {
      return;
    }

    // Never trigger quiz checkpoints during initial load or before adequate playback buffer
    if (currentTime < 2.0) return;

    const prevTime = this.lastObservedTime;

    for (const q of this.questions) {
      if (this.completedQuestionIds.has(q.id) || this.triggeredQuestionIds.has(q.id)) {
        continue;
      }
      // Pedagogical safeguard: Full video lectures (>60s) should not trigger popups at early intro seconds (<30s)
      const isLongLecture = (this.video && this.video.duration > 60) || (this.ytDuration && this.ytDuration > 60);
      if (isLongLecture && q.timestamp_seconds < 30.0) {
        continue;
      }
      if (q.timestamp_seconds < 2.0) {
        continue;
      }
      // Check if playback crossed or is at checkpoint timestamp
      if (
        (currentTime >= q.timestamp_seconds && currentTime <= q.timestamp_seconds + 2.0) ||
        (prevTime > 0 && prevTime < q.timestamp_seconds && currentTime >= q.timestamp_seconds)
      ) {
        this.lastObservedTime = q.timestamp_seconds;
        this.triggerQuizPause(q);
        return;
      }
    }
    this.lastObservedTime = currentTime;
  }

  handleSeeking(targetTimeOverride) {
    if (this.activeQuestion) return;

    let targetTime = 0;
    if (typeof targetTimeOverride === 'number') {
      targetTime = targetTimeOverride;
    } else if (this.activeSourceType === 'LOCAL' && this.video) {
      targetTime = this.video.currentTime;
    } else if (this.activeSourceType === 'YOUTUBE') {
      targetTime = this.ytCurrentTime || 0;
    } else {
      return;
    }

    const prevTime = this.lastObservedTime;

    // Only intercept seeking after playback has started (prevTime > 1.0) and seeking forward
    if (prevTime > 1.0 && targetTime > prevTime + 0.5) {
      for (const q of this.questions) {
        if (!this.completedQuestionIds.has(q.id) && !this.triggeredQuestionIds.has(q.id)) {
          if (q.timestamp_seconds > prevTime && q.timestamp_seconds <= targetTime) {
            // Intercept forward seek! Snap back to checkpoint
            if (this.activeSourceType === 'LOCAL' && this.video) {
              this.video.currentTime = q.timestamp_seconds;
            } else if (this.activeSourceType === 'YOUTUBE') {
              this.ytCurrentTime = q.timestamp_seconds;
              this.sendYouTubeCommand('seekTo', [q.timestamp_seconds, true]);
              if (this.ytPlayer && typeof this.ytPlayer.seekTo === 'function') {
                try { this.ytPlayer.seekTo(q.timestamp_seconds, true); } catch(e) {}
              }
            }
            this.lastObservedTime = q.timestamp_seconds;
            if (window.showToast) {
              window.showToast('مهرباني ڪري وڊيو ۾ اڳتي وڌڻ کان اڳ چيڪ پوائنٽ سوال حل ڪريو.');
            }
            this.triggerQuizPause(q);
            return;
          }
        }
      }
    }
    this.lastObservedTime = targetTime;
  }

  handleSeeked() {
    this.checkQuizPopups();
  }

  triggerQuizPause(question) {
    if (this.activeSourceType === 'LOCAL' && this.video) {
      this.video.pause();
    } else if (this.activeSourceType === 'YOUTUBE') {
      this.sendYouTubeCommand('pauseVideo');
      if (this.ytPlayer && typeof this.ytPlayer.pauseVideo === 'function') {
        try { this.ytPlayer.pauseVideo(); } catch(e) {}
      }
    }
    this.triggeredQuestionIds.add(question.id);
    this.activeQuestion = question;
    this.renderQuizModal(question);
  }

  renderQuizModal(question) {
    if (!this.quizOverlay) return;

    const mins = Math.floor(question.timestamp_seconds / 60);
    const secs = String(Math.round(question.timestamp_seconds % 60)).padStart(2, '0');

    this.quizOverlay.style.display = 'flex';
    this.quizOverlay.innerHTML = `
      <div class="quiz-modal-card" role="dialog" aria-modal="true" aria-labelledby="checkpoint-title">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span class="quiz-badge" id="checkpoint-title">📍 وڊيو چيڪ پوائنٽ (${mins}:${secs})</span>
          <span style="font-size: 0.76rem; font-weight: 700; color: #059669; background: #ecfdf5; padding: 2px 8px; border-radius: 12px;">مشق موڊ (Practice Mode)</span>
        </div>
        <h3 class="quiz-question-text" id="checkpoint-question-text">${escapeHtml(question.text_sindhi)}</h3>
        <div class="quiz-options-list" role="radiogroup" aria-label="سوال جا امڪاني جواب">
          ${question.options.map((opt, idx) => `
            <button class="quiz-option-btn" onclick="sdcPlayer.submitAnswer(${idx})" id="quiz-opt-${idx}" aria-label="آپشن ${idx + 1}: ${escapeHtml(opt)}">
              <span class="option-num">${idx + 1}</span>
              <span class="option-text">${escapeHtml(opt)}</span>
            </button>
          `).join('')}
        </div>
        <div id="quiz-status-indicator" class="quiz-status-indicator" style="display: none; padding: 10px; margin-bottom: 12px; border-radius: 6px; font-size: 0.88rem; background: var(--bg-subtle, #f1f5f9); color: var(--text-secondary, #475569);"></div>
        <div id="quiz-feedback-box" class="quiz-feedback-box" style="display: none;"></div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px;">
          <div style="display: flex; gap: 8px; align-items: center;">
            <button class="quiz-skip-btn" id="btn-skip-checkpoint" onclick="sdcPlayer.skipQuiz()">ڇڏي اڳتي وڌو (Skip)</button>
            <button class="quiz-retry-btn" id="btn-retry-checkpoint" style="display: none;" onclick="sdcPlayer.retryAnswer()">ٻيهر ڪوشش ڪريو (Retry) 🔄</button>
          </div>
          <button class="quiz-resume-btn" id="btn-resume-checkpoint" style="display: none;" onclick="sdcPlayer.resumePlayback()">وڊيو جاري رکو (Resume Video) ▶</button>
        </div>
        <div style="margin-top: 8px; font-size: 0.72rem; color: var(--text-dim, #94a3b8); text-align: left;">
          ⌨ ڪي بورڊ شارٽ ڪٽ: 1، 2، 3، 4 دٻايو | Enter دٻائي وڊيو جاري رکو
        </div>
      </div>
    `;

    // Keyboard navigation (1, 2, 3, 4, Enter)
    if (this._keyHandler) {
      window.removeEventListener('keydown', this._keyHandler);
    }
    this._keyHandler = (e) => {
      if (!this.activeQuestion) return;
      if (['1', '2', '3', '4'].includes(e.key)) {
        const idx = parseInt(e.key, 10) - 1;
        const btn = document.getElementById(`quiz-opt-${idx}`);
        if (btn && !btn.disabled) {
          this.submitAnswer(idx);
        }
      } else if (e.key === 'Enter') {
        const resBtn = document.getElementById('btn-resume-checkpoint');
        if (resBtn && resBtn.style.display !== 'none') {
          this.resumePlayback();
        }
      }
    };
    window.addEventListener('keydown', this._keyHandler);
  }

  async submitAnswer(selectedIndex) {
    if (!this.activeQuestion) return;

    const optButtons = document.querySelectorAll('.quiz-option-btn');
    optButtons.forEach(b => b.disabled = true);

    const skipBtn = document.getElementById('btn-skip-checkpoint');
    if (skipBtn) skipBtn.style.display = 'none';

    const retryBtn = document.getElementById('btn-retry-checkpoint');
    if (retryBtn) retryBtn.style.display = 'none';

    const statusEl = document.getElementById('quiz-status-indicator');
    if (statusEl) {
      statusEl.style.display = 'block';
      statusEl.innerHTML = '<span>⏳ جواب سرور تي محفوظ ٿي رهيو آهي... (Saving answer to server...)</span>';
    }

    const questionId = this.activeQuestion.id;
    const user = window.currentUser || { user_id: 'usr-stu-101' };
    const token = user.token || localStorage.getItem('sdc_token') || 'sdc_demo_token';

    try {
      let result = null;
      if (navigator.onLine) {
        const res = await fetch('/api/quiz/attempt', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            question_id: questionId,
            selected_option: selectedIndex,
            time_taken_seconds: 4.0
          })
        });
        if (res.ok) {
          result = await res.json();
        } else {
          throw new Error(`Server returned HTTP ${res.status}`);
        }
      } else {
        // Offline attempt fallback partitioned in IndexedDB
        if (typeof queueOfflineAttempt === 'function') {
          await queueOfflineAttempt({
            question_id: questionId,
            selected_option: selectedIndex,
            is_correct: true,
            time_taken_seconds: 4.0
          }, user.user_id || 'usr-stu-101');
        }
        result = {
          is_correct: true,
          correct_answer_index: selectedIndex,
          explanation_sindhi: "توهان جو جواب آف لائن محفوظ ڪيو ويو آهي (Saved offline)."
        };
      }

      if (statusEl) statusEl.style.display = 'none';

      // Mark completed & persist in client storage
      this.completedQuestionIds.add(questionId);
      const uid = this.getStudentId();
      const savedCompletedKey = `sdc_checkpoints_${uid}_${this.currentLesson ? this.currentLesson.id : 'default'}`;
      try {
        localStorage.setItem(savedCompletedKey, JSON.stringify(Array.from(this.completedQuestionIds)));
      } catch (e) {}

      // Update timeline marker dot
      const dot = document.getElementById(`checkpoint-dot-${questionId}`);
      if (dot) {
        dot.className = 'checkpoint-dot completed';
      }

      // Highlight selected button
      const selBtn = document.getElementById(`quiz-opt-${selectedIndex}`);
      if (result.is_correct) {
        if (selBtn) selBtn.classList.add('correct-choice');
      } else {
        if (selBtn) selBtn.classList.add('incorrect-choice');
        const correctBtn = document.getElementById(`quiz-opt-${result.correct_answer_index}`);
        if (correctBtn) correctBtn.classList.add('correct-choice');
      }

      // Render Pedagogical Feedback with Citation
      const feedbackBox = document.getElementById('quiz-feedback-box');
      if (feedbackBox) {
        feedbackBox.style.display = 'block';
        const topicName = (this.currentLesson && this.currentLesson.title_sindhi) || 'درسي سبق';
        const citation = `📖 درسي حوالو: سنڌ ٽيڪسٽ بڪ بورڊ ڪلاس 6 (${topicName})`;
        if (result.is_correct) {
          feedbackBox.className = 'quiz-feedback-box success';
          feedbackBox.innerHTML = `
            <div style="font-weight: 800; margin-bottom: 4px;">✅ شاباس! درست جواب</div>
            <div>${escapeHtml(result.explanation_sindhi || '')}</div>
            <div style="margin-top: 6px; font-size: 0.8rem; color: #065f46; font-weight: 700;">${citation}</div>
          `;
        } else {
          feedbackBox.className = 'quiz-feedback-box error';
          feedbackBox.innerHTML = `
            <div style="font-weight: 800; margin-bottom: 4px;">❌ جواب درست ناهي</div>
            <div>${escapeHtml(result.explanation_sindhi || 'صحيح آپشن تي غور ڪريو.')}</div>
            <div style="margin-top: 6px; font-size: 0.8rem; color: #9f1239; font-weight: 700;">${citation}</div>
          `;
        }
      }

      // Show Resume Button & Focus it (Explicit confirmation: NO automatic timer resume!)
      const resumeBtn = document.getElementById('btn-resume-checkpoint');
      if (resumeBtn) {
        resumeBtn.style.display = 'inline-flex';
        resumeBtn.focus();
      }

      // Check if all in-video checkpoints have now been attempted for this lesson
      if (this.questions && this.questions.length > 0 && this.completedQuestionIds.size >= this.questions.length) {
        console.log('[Player] All checkpoints answered for lesson. Updating completion progress...');
        const duration = (this.currentLesson && this.currentLesson.duration_seconds) || 600;
        this.saveProgress(duration, true);
        if (window.showToast) {
          window.showToast('🎉 شاباس! توهان هن سبق جا سمورا ان-ويڊيو ڪوئز حل ڪري ورتا ۽ سبق مڪمل ٿي ويو.');
        }
      }

    } catch (err) {
      console.error('Quiz attempt failed:', err);
      if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.innerHTML = '<span style="color: #b91c1c; font-weight: 700;">❌ جواب محفوظ نه ٿي سگهيو (Network / Save Error). مهرباني ڪري ٻيهر ڪوشش ڪريو.</span>';
      }
      if (retryBtn) retryBtn.style.display = 'inline-flex';
      optButtons.forEach(b => b.disabled = false);
      if (skipBtn) skipBtn.style.display = 'inline-block';
    }
  }

  retryAnswer() {
    const statusEl = document.getElementById('quiz-status-indicator');
    if (statusEl) statusEl.style.display = 'none';
    const retryBtn = document.getElementById('btn-retry-checkpoint');
    if (retryBtn) retryBtn.style.display = 'none';
    const optButtons = document.querySelectorAll('.quiz-option-btn');
    optButtons.forEach(b => b.disabled = false);
    const skipBtn = document.getElementById('btn-skip-checkpoint');
    if (skipBtn) skipBtn.style.display = 'inline-block';
  }

  async skipQuiz() {
    const question = this.activeQuestion;
    const user = window.currentUser || { user_id: 'usr-stu-101' };
    const token = user.token || localStorage.getItem('sdc_token') || 'sdc_demo_token';
    if (question) {
      if (navigator.onLine) {
        fetch('/api/quiz/attempt', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            question_id: question.id,
            selected_option: -1,
            time_taken_seconds: 0.0,
            is_skipped: true
          })
        }).catch(e => console.log('Skip attempt log failed:', e));
      } else {
        if (typeof queueOfflineAttempt === 'function') {
          await queueOfflineAttempt({
            question_id: question.id,
            selected_option: -1,
            is_correct: false,
            time_taken_seconds: 0.0,
            is_skipped: true
          }, user.user_id || 'usr-stu-101');
        }
      }
      this.completedQuestionIds.add(question.id);
      if (window.showToast) window.showToast('سوال ڇڏي ڏنو ويو (Question skipped).');
    }
    this.resumePlayback();
  }

  resumePlayback() {
    if (this._keyHandler) {
      window.removeEventListener('keydown', this._keyHandler);
      this._keyHandler = null;
    }
    this.closeQuizModal();
  }

  closeQuizModal() {
    if (this.quizOverlay) {
      this.quizOverlay.style.display = 'none';
      this.quizOverlay.innerHTML = '';
    }
    this.activeQuestion = null;
    if (this.activeSourceType === 'LOCAL' && this.video) {
      this.video.play().catch(e => console.log('Resume error:', e));
    } else if (this.activeSourceType === 'YOUTUBE') {
      this.sendYouTubeCommand('playVideo');
      if (this.ytPlayer && typeof this.ytPlayer.playVideo === 'function') {
        try { this.ytPlayer.playVideo(); } catch(e) {}
      }
    }
  }

  getAuthToken() {
    if (window.currentUser && window.currentUser.token) {
      return window.currentUser.token;
    }
    try {
      const stored = localStorage.getItem('sdc_current_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && parsed.token) return parsed.token;
      }
    } catch (e) {}
    const rawToken = localStorage.getItem('sdc_token');
    if (rawToken) return rawToken;
    return '';
  }

  getStudentId() {
    if (window.currentUser && (window.currentUser.user_id || window.currentUser.id)) {
      return window.currentUser.user_id || window.currentUser.id;
    }
    try {
      const stored = localStorage.getItem('sdc_current_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && (parsed.user_id || parsed.id)) return parsed.user_id || parsed.id;
      }
    } catch (e) {}
    return 'usr-stu-101';
  }

  onVideoPlaybackEnded() {
    if (!this.currentLesson) return;
    console.log('[Player] Video playback ended for lesson:', this.currentLesson.id);
    const expectedDur = this.currentLesson.duration_seconds || 600;
    this.saveProgress(expectedDur, true);
    if (window.showToast) {
      window.showToast('🎉 مبارڪون! هي ويڊيو سبق مڪمل ٿي ويو ۽ ترقي محفوظ ڪئي وئي.');
    }
  }

  async saveProgress(seconds, isCompleted) {
    if (!this.currentLesson) return;
    const uid = this.getStudentId();
    const token = this.getAuthToken();
    const lessonId = this.currentLesson.id;
    const duration = (this.currentLesson && this.currentLesson.duration_seconds) || 600;
    const pos = (isCompleted && (!seconds || seconds < duration * 0.8)) ? duration : (seconds || 0);

    if (navigator.onLine && token) {
      try {
        const resp = await fetch(`/api/lessons/${lessonId}/progress`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            lesson_id: lessonId,
            position_seconds: pos,
            is_completed: !!isCompleted
          })
        });
        if (resp.ok) {
          if (isCompleted) {
            this.updateCompletedUI(lessonId);
          }
        } else {
          console.warn('[Player] Server returned non-ok for progress:', resp.status);
        }
      } catch (e) {
        console.warn('[Player] Error saving online progress:', e);
      }
    }

    if (typeof saveOfflineProgress === 'function') {
      try {
        await saveOfflineProgress(uid, lessonId, pos, isCompleted);
      } catch (e) {}
    }
    if (isCompleted) {
      this.updateCompletedUI(lessonId);
    }
  }

  updateCompletedUI(lessonId) {
    if (!lessonId) return;
    if (!window.completedLessonsSet) window.completedLessonsSet = new Set();
    window.completedLessonsSet.add(lessonId);

    // Update playlist card
    const card = document.getElementById(`card-${lessonId}`);
    if (card) {
      const tagContainer = card.querySelector('.lesson-unit-tag');
      if (tagContainer && tagContainer.parentNode) {
        if (!card.querySelector('.lesson-completed-check')) {
          const checkSpan = document.createElement('span');
          checkSpan.className = 'lesson-completed-check';
          checkSpan.innerHTML = '&#10004; مڪمل';
          tagContainer.parentNode.appendChild(checkSpan);
        }
      }
    }

    // Update button if active lesson
    if (this.currentLesson && this.currentLesson.id === lessonId) {
      const btnLabel = document.getElementById('btn-mark-watched-label');
      const btn = document.getElementById('btn-mark-watched');
      if (btnLabel) btnLabel.textContent = '✔ مڪمل ٿيل (Watched)';
      if (btn) {
        btn.style.borderColor = 'var(--accent-emerald)';
        btn.style.color = 'var(--accent-emerald)';
        btn.style.background = 'var(--accent-emerald-soft, #ecfdf5)';
      }
    }

    // Refresh course cards if function exists
    if (typeof filterAndRenderCourses === 'function') {
      filterAndRenderCourses();
    }
  }
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
