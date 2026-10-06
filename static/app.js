/* ────────────────────────────────────────────────────────────
   AI Video Transcriber · app.js
   ──────────────────────────────────────────────────────────── */

class VideoTranscriber {
  constructor() {
    this.currentTaskId  = null;
    this.eventSource    = null;
    this.apiBase        = '/api';
    this.currentLang    = 'en';

    /* Smart progress simulation */
    this.sp = {
      enabled: false, current: 0, target: 15,
      lastServer: 0, interval: null, startTime: null, stage: 'preparing'
    };

    this.i18n = {
      en: {
        title:                   'AI Video Transcriber',
        subtitle:                'Automatic transcription, AI summary, and original video download for 30+ platforms',
        video_url_placeholder:   'Paste YouTube, Tiktok, Bilibili or other platform video URLs...',
        start_transcription:     'Transcribe',
        ai_settings:             'AI Settings',
        model_base_url:          'Model API Base URL',
        model_base_url_placeholder: 'https://openrouter.ai/api/v1',
        api_key:                 'API Key',
        api_key_placeholder:     'sk-...',
        fetch_models:            'Fetch',
        model_select:            'Model',
        model_default:           '— use server default —',
        summary_language:        'Summary Language',
        processing_progress:     'Processing',
        preparing:               'Preparing…',
        transcript_text:         'Transcript',
        intelligent_summary:     'AI Summary',
        translation:             'Translation',
        download_transcript:     'Download transcript',
        download_translation:    'Download translation',
        download_summary:        'Download summary',
        copy_transcript:         'Copy transcript',
        copy_translation:        'Copy translation',
        copy_summary:            'Copy summary',
        error_copy_failed:       'Copy failed: ',
        empty_hint:              'Paste a video URL or drop a file above and let AI do the heavy lifting.',
        footer_text:             'This tool is part of <a href="https://sipsip.ai" target="_blank" style="color:#fff;text-decoration:none;">sipsip.ai</a> — distill anything and get daily AI briefs from your favorite creators',
        processing:              'Processing…',
        downloading_video:       'Downloading audio…',
        parsing_video:           'Parsing video info…',
        transcribing_audio:      'Transcribing audio…',
        optimizing_transcript:   'Optimizing transcript…',
        generating_summary:      'Generating summary…',
        detecting_subtitles:     'Detecting subtitles…',
        subtitle_found:          'Subtitles found! Processing text…',
        no_subtitle:             'No subtitles found, downloading audio…',
        mode_subtitle:           '⚡ Subtitle',
        mode_whisper:            '🎙 Whisper',
        completed:               'Done!',
        error_invalid_url:       'Please enter a valid video URL',
        error_processing_failed: 'Processing failed: ',
        error_no_download:       'No file available for download',
        error_download_failed:   'Download failed: ',
        fetching_models:         'Fetching models…',
        models_loaded:           (n) => `${n} models loaded`,
        models_error:            'Failed to fetch models',
        upload_or:               'or drop your files',
        upload_formats:          '.mp3 · .mp4 · .wav · .m4a · .webm · .mkv · .ogg · .flac',
        upload_files_btn:        'Upload files',
        error_upload_type:       'Unsupported file type',
        error_upload_empty:      'File is empty',
        error_upload_size:       (mb) => `File exceeds ${mb} MB limit`,
        keep_video:              'Keep original video',
        original_media:          'Original video',
        original_media_audio:    'Original audio',
        download_video:          'Download original video',
        download_audio:          'Download original audio',
        preparing_video:         'Preparing original video…',
        error_no_video:          'No video available for download',
        no_speech_notice:        'No speech detected in this video, so there is nothing to transcribe. Summary and translation are skipped — the original video is still available below.',
      },
      zh: {
        title:                   'AI 视频转录器',
        subtitle:                '粘贴 YouTube、TikTok 或任意公开视频链接，获取转录文本、AI 摘要，并下载原视频。',
        video_url_placeholder:   '请输入视频链接…',
        start_transcription:     '开始转录',
        ai_settings:             'AI 设置',
        model_base_url:          'Model API 地址',
        model_base_url_placeholder: 'https://openrouter.ai/api/v1',
        api_key:                 'API Key',
        api_key_placeholder:     'sk-...',
        fetch_models:            '获取',
        model_select:            '模型',
        model_default:           '— 使用服务器默认 —',
        summary_language:        '摘要语言',
        processing_progress:     '处理进度',
        preparing:               '准备中…',
        transcript_text:         '转录文本',
        intelligent_summary:     '智能摘要',
        translation:             '翻译',
        download_transcript:     '下载转录文本',
        download_translation:    '下载翻译',
        download_summary:        '下载摘要',
        copy_transcript:         '复制转录文本',
        copy_translation:        '复制翻译',
        copy_summary:            '复制摘要',
        error_copy_failed:       '复制失败：',
        empty_hint:              '在上方粘贴视频链接或拖放文件，让 AI 来处理一切。',
        footer_text:             '本工具是 <a href="https://sipsip.ai" target="_blank" style="color:#fff;text-decoration:none;">sipsip.ai</a> 的一部分 — 提取任何内容要点并构建你自己的知识库。',
        processing:              '处理中…',
        downloading_video:       '正在下载音频…',
        parsing_video:           '正在解析视频信息…',
        transcribing_audio:      '正在转录音频…',
        optimizing_transcript:   '正在优化转录文本…',
        generating_summary:      '正在生成摘要…',
        detecting_subtitles:     '正在检测字幕…',
        subtitle_found:          '字幕获取成功！正在处理文本…',
        no_subtitle:             '未找到字幕，正在下载音频…',
        mode_subtitle:           '⚡ 字幕模式',
        mode_whisper:            '🎙 Whisper 模式',
        completed:               '处理完成！',
        error_invalid_url:       '请输入有效的视频链接',
        error_processing_failed: '处理失败：',
        error_no_download:       '没有可下载的文件',
        error_download_failed:   '下载失败：',
        fetching_models:         '正在获取模型列表…',
        models_loaded:           (n) => `已加载 ${n} 个模型`,
        models_error:            '获取模型失败',
        upload_or:               '或拖放文件到此处',
        upload_formats:          '.mp3 · .mp4 · .wav · .m4a · .webm · .mkv · .ogg · .flac',
        upload_files_btn:        '上传文件',
        error_upload_type:       '不支持的文件类型',
        error_upload_empty:      '文件为空',
        error_upload_size:       (mb) => `文件超过 ${mb} MB 限制`,
        keep_video:              '保留原视频',
        original_media:          '原视频',
        original_media_audio:    '原音频',
        download_video:          '下载原视频',
        download_audio:          '下载原音频',
        preparing_video:         '正在准备原视频…',
        error_no_video:          '没有可下载的视频',
        no_speech_notice:        '这个视频中未检测到任何语音，因此没有可转录的内容。摘要与翻译已跳过 —— 原视频仍可在下方下载。',
      }
    };

    this._initElements();
    this._bindEvents();
    this._loadSettings();
    this._switchLang('en');
  }

  /* ── Elements ─────────────────────────────────────────── */
  _initElements() {
    this.form               = document.getElementById('videoForm');
    this.videoUrlInput      = document.getElementById('videoUrl');
    this.submitBtn          = document.getElementById('submitBtn');
    this.summaryLangSel     = document.getElementById('summaryLanguage');
    this.langToggle         = document.getElementById('langToggle');
    this.langText           = document.getElementById('langText');
    this.errorBanner        = document.getElementById('errorBanner');
    this.errorMsg           = document.getElementById('errorMsg');
    this.emptyState         = document.getElementById('emptyState');
    this.progressPanel      = document.getElementById('progressPanel');
    this.modeBadge          = document.getElementById('modeBadge');
    this.progressStatus     = document.getElementById('progressStatus');
    this.progressFill       = document.getElementById('progressFill');
    this.progressMessage    = document.getElementById('progressMessage');
    this.resultsPanel       = document.getElementById('resultsPanel');
    this.scriptContent      = document.getElementById('scriptContent');
    this.summaryContent     = document.getElementById('summaryContent');
    this.translationContent = document.getElementById('translationContent');
    this.dlScript           = document.getElementById('downloadScript');
    this.dlTranslation      = document.getElementById('downloadTranslation');
    this.dlSummary          = document.getElementById('downloadSummary');
    this.dlVideo            = document.getElementById('downloadVideo');
    this.copyScript         = document.getElementById('copyScript');
    this.copyTranslation    = document.getElementById('copyTranslation');
    this.copySummary        = document.getElementById('copySummary');
    this.keepVideo          = document.getElementById('keepVideo');
    this.mediaBlock         = document.getElementById('mediaBlock');
    this.mediaFrame         = document.getElementById('mediaFrame');
    this.mediaMeta          = document.getElementById('mediaMeta');
    this.translationTabItem = document.getElementById('translationTabItem');
    this.summaryTabItem     = document.getElementById('summaryTabItem');
    this.noSpeechBanner     = document.getElementById('noSpeechBanner');
    this.tabBtns            = document.querySelectorAll('.tab-btn');
    this.tabItems           = document.querySelectorAll('.tab-item');
    this.tabPanes           = document.querySelectorAll('.tab-pane');
    // settings
    this.settingsToggle     = document.getElementById('settingsToggle');
    this.settingsBody       = document.getElementById('settingsBody');
    this.modelBaseUrl       = document.getElementById('modelBaseUrl');
    this.apiKeyInput        = document.getElementById('apiKeyInput');
    this.fetchModelsBtn     = document.getElementById('fetchModelsBtn');
    this.fetchStatus        = document.getElementById('fetchStatus');
    this.modelSelect        = document.getElementById('modelSelect');
    this.fetchIcon          = document.getElementById('fetchIcon');
    this.uploadZone         = document.getElementById('uploadZone');
    this.uploadPickBtn      = document.getElementById('uploadPickBtn');
    this.fileInput          = document.getElementById('fileInput');
    this.uploadMaxMb        = 200;
    this._allowedUploadExts = new Set(['.txt', '.mp3', '.mp4', '.m4a', '.wav', '.webm', '.mkv', '.ogg', '.flac']);
    this._markdown = {};
    // 当前结果对应的原视频/音频（由 _renderMedia 填充）
    this._mediaFile = null;
    this._mediaName = null;
  }

  /* ── Events ───────────────────────────────────────────── */
  _bindEvents() {
    this.form.addEventListener('submit', (e) => { e.preventDefault(); this._startTranscription(); });

    this.langToggle.addEventListener('click', () => {
      this._switchLang(this.currentLang === 'en' ? 'zh' : 'en');
    });

    // Settings toggle
    this.settingsToggle.addEventListener('click', () => {
      const open = this.settingsBody.classList.toggle('open');
      this.settingsToggle.classList.toggle('open', open);
    });

    // Fetch models
    this.fetchModelsBtn.addEventListener('click', () => this._fetchModels());

    // Auto-fetch when both fields filled (debounced)
    const debouncedFetch = this._debounce(() => {
      if (this.modelBaseUrl.value.trim() && this.apiKeyInput.value.trim()) this._fetchModels();
    }, 900);
    this.modelBaseUrl.addEventListener('input', debouncedFetch);
    this.apiKeyInput.addEventListener('input', debouncedFetch);

    // Persist settings
    [this.modelBaseUrl, this.apiKeyInput, this.modelSelect, this.summaryLangSel, this.keepVideo].forEach(el => {
      if (el) el.addEventListener('change', () => this._saveSettings());
    });

    // Tabs
    this.tabBtns.forEach(btn => {
      btn.addEventListener('click', () => this._switchTab(btn.dataset.tab));
    });

    // Copy/download — the tab icons fire without activating their tab, so you
    // can grab the summary while still reading the transcript.
    const bindTabAction = (el, action) => {
      if (!el) return;
      el.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        action();
      });
    };
    bindTabAction(this.dlScript,        () => this._downloadFile('script'));
    bindTabAction(this.dlTranslation,   () => this._downloadFile('translation'));
    bindTabAction(this.dlSummary,       () => this._downloadFile('summary'));
    bindTabAction(this.copyScript,      () => this._copyMarkdown('script', this.copyScript));
    bindTabAction(this.copyTranslation, () => this._copyMarkdown('translation', this.copyTranslation));
    bindTabAction(this.copySummary,     () => this._copyMarkdown('summary', this.copySummary));
    if (this.dlVideo) this.dlVideo.addEventListener('click', () => this._downloadMedia());

    if (this.uploadPickBtn && this.fileInput && this.uploadZone) {
      this.uploadPickBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.fileInput.click();
      });
      this.uploadZone.addEventListener('click', (e) => {
        if (e.target === this.uploadPickBtn || this.uploadPickBtn.contains(e.target)) return;
        this.fileInput.click();
      });
      this.fileInput.addEventListener('change', () => {
        const f = this.fileInput.files && this.fileInput.files[0];
        this.fileInput.value = '';
        if (f) this._startFileUpload(f);
      });
      ['dragenter', 'dragover'].forEach((ev) => {
        this.uploadZone.addEventListener(ev, (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.uploadZone.classList.add('dragover');
        });
      });
      this.uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        if (!this.uploadZone.contains(e.relatedTarget)) {
          this.uploadZone.classList.remove('dragover');
        }
      });
      this.uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.uploadZone.classList.remove('dragover');
        const f = e.dataTransfer.files && e.dataTransfer.files[0];
        if (f) this._startFileUpload(f);
      });
    }
  }

  /* ── i18n ─────────────────────────────────────────────── */
  t(key) { return this.i18n[this.currentLang][key] || this.i18n['en'][key] || key; }

  _switchLang(lang) {
    this.currentLang = lang;
    this.langText.textContent = lang === 'en' ? 'English' : '中文';
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    document.title = this.t('title');

    document.querySelectorAll('[data-i18n]').forEach(el => {
      const v = this.t(el.dataset.i18n);
      if (typeof v === 'string') {
        // footer 等允许含 HTML 的 key 用 innerHTML，其余保持 textContent
        if (el.dataset.i18n === 'footer_text') el.innerHTML = v;
        else el.textContent = v;
      }
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const v = this.t(el.dataset.i18nPlaceholder);
      if (typeof v === 'string') el.placeholder = v;
    });
    // Icon-only buttons: the tooltip is also their accessible name
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const v = this.t(el.dataset.i18nTitle);
      if (typeof v === 'string') { el.title = v; el.setAttribute('aria-label', v); }
    });

    this._applyMediaLabels();
  }

  /* ── Settings persistence ─────────────────────────────── */
  _saveSettings() {
    const s = {
      baseUrl:  this.modelBaseUrl.value,
      apiKey:   this.apiKeyInput.value,
      model:    this.modelSelect.value,
      summaryLang: this.summaryLangSel.value,
      keepVideo: this.keepVideo ? this.keepVideo.checked : true,
    };
    try { localStorage.setItem('vt_settings', JSON.stringify(s)); } catch (_) {}
  }

  _loadSettings() {
    try {
      const raw = localStorage.getItem('vt_settings');
      if (!raw) return;
      const s = JSON.parse(raw);
      if (s.baseUrl)     this.modelBaseUrl.value = s.baseUrl;
      if (s.apiKey)      this.apiKeyInput.value  = s.apiKey;
      if (s.summaryLang) this.summaryLangSel.value = s.summaryLang;
      if (this.keepVideo && typeof s.keepVideo === 'boolean') this.keepVideo.checked = s.keepVideo;
      // Model options will be restored after fetching
      this._savedModel = s.model || '';

      // Auto-open settings if credentials were saved
      if (s.baseUrl || s.apiKey) {
        this.settingsBody.classList.add('open');
        this.settingsToggle.classList.add('open');
        // Attempt to re-fetch model list silently
        if (s.baseUrl && s.apiKey) {
          setTimeout(() => this._fetchModels(true), 400);
        }
      }
    } catch (_) {}
  }

  /* ── Fetch models ─────────────────────────────────────── */
  async _fetchModels(silent = false) {
    const baseUrl = this.modelBaseUrl.value.trim().replace(/\/$/, '');
    const apiKey  = this.apiKeyInput.value.trim();

    if (!baseUrl || !apiKey) {
      if (!silent) this._setFetchStatus('err', this.t('api_key') + ' & URL required');
      return;
    }

    this.fetchModelsBtn.disabled = true;
    this.fetchIcon.className = 'fas fa-spinner fa-spin';
    if (!silent) this._setFetchStatus('', this.t('fetching_models'));

    try {
      const fd = new FormData();
      fd.append('base_url', baseUrl);
      fd.append('api_key',  apiKey);

      const resp = await fetch(`${this.apiBase}/models`, { method: 'POST', body: fd });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      const models = data.data || data.models || [];

      // Rebuild select options
      this.modelSelect.innerHTML = `<option value="">${this.t('model_default')}</option>`;
      models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.name || m.id;
        this.modelSelect.appendChild(opt);
      });

      // Restore previously selected model
      if (this._savedModel) {
        this.modelSelect.value = this._savedModel;
        this._savedModel = '';
      }

      this._setFetchStatus('ok', typeof this.t('models_loaded') === 'function'
        ? this.t('models_loaded')(models.length)
        : `${models.length} models`);

    } catch (e) {
      console.warn('Model fetch error:', e);
      this._setFetchStatus('err', this.t('models_error') + ': ' + e.message);
    } finally {
      this.fetchModelsBtn.disabled = false;
      this.fetchIcon.className = 'fas fa-sync-alt';
    }
  }

  _setFetchStatus(cls, msg) {
    this.fetchStatus.className = 'fetch-status' + (cls ? ` ${cls}` : '');
    this.fetchStatus.textContent = msg;
  }

  /* ── Transcription ────────────────────────────────────── */
  async _startTranscription() {
    if (this.submitBtn.disabled) return;

    const url     = this.videoUrlInput.value.trim();
    const sumLang = this.summaryLangSel.value;

    if (!url) { this._showError(this.t('error_invalid_url')); return; }

    this._setLoading(true);
    this._hideError();
    this._showProgress();

    try {
      const fd = new FormData();
      fd.append('url',              url);
      fd.append('summary_language', sumLang);
      fd.append('download_video',   this.keepVideo && this.keepVideo.checked ? '1' : '0');

      const apiKey  = this.apiKeyInput.value.trim();
      const baseUrl = this.modelBaseUrl.value.trim().replace(/\/$/, '');
      const modelId = this.modelSelect.value;
      if (apiKey)  fd.append('api_key',       apiKey);
      if (baseUrl) fd.append('model_base_url', baseUrl);
      if (modelId) fd.append('model_id',       modelId);

      const resp = await fetch(`${this.apiBase}/process-video`, { method: 'POST', body: fd });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Request failed');
      }

      const data = await resp.json();
      this.currentTaskId = data.task_id;

      this._initSP();
      this._updateProgress(5, this.t('preparing'), true);
      this._startSSE();
      this._saveSettings();

    } catch (err) {
      this._showError(this.t('error_processing_failed') + err.message);
      this._setLoading(false);
      this._hideProgress();
    }
  }

  async _startFileUpload(file) {
    if (this.submitBtn.disabled) return;

    const parts = (file.name || '').split('.');
    const ext = parts.length > 1 ? ('.' + parts.pop().toLowerCase()) : '';
    if (!this._allowedUploadExts.has(ext)) {
      this._showError(this.t('error_upload_type'));
      return;
    }
    if (!file.size) {
      this._showError(this.t('error_upload_empty'));
      return;
    }
    const maxB = this.uploadMaxMb * 1024 * 1024;
    if (file.size > maxB) {
      this._showError(this.t('error_upload_size')(this.uploadMaxMb));
      return;
    }

    this._setLoading(true);
    this._hideError();
    this._showProgress();

    const sumLang = this.summaryLangSel.value;
    try {
      const fd = new FormData();
      fd.append('file', file, file.name);
      fd.append('summary_language', sumLang);

      const apiKey  = this.apiKeyInput.value.trim();
      const baseUrl = this.modelBaseUrl.value.trim().replace(/\/$/, '');
      const modelId = this.modelSelect.value;
      if (apiKey)  fd.append('api_key',       apiKey);
      if (baseUrl) fd.append('model_base_url', baseUrl);
      if (modelId) fd.append('model_id',       modelId);

      const resp = await fetch(`${this.apiBase}/process-video`, { method: 'POST', body: fd });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        const d = err.detail;
        const msg = typeof d === 'string'
          ? d
          : (Array.isArray(d) && d[0] && (d[0].msg || d[0].message))
            || `HTTP ${resp.status}`;
        throw new Error(msg);
      }

      const data = await resp.json();
      this.currentTaskId = data.task_id;

      this._initSP();
      this._updateProgress(5, this.t('preparing'), true);
      this._startSSE();
      this._saveSettings();

    } catch (err) {
      this._showError(this.t('error_processing_failed') + err.message);
      this._setLoading(false);
      this._hideProgress();
    }
  }

  /* ── SSE ──────────────────────────────────────────────── */
  _startSSE() {
    if (!this.currentTaskId) return;
    this.eventSource = new EventSource(`${this.apiBase}/task-stream/${this.currentTaskId}`);

    this.eventSource.onmessage = (ev) => {
      try {
        const task = JSON.parse(ev.data);
        if (task.type === 'heartbeat') return;

        this._updateProgress(task.progress, task.message, true);

        if (task.status === 'completed') {
          this._stopSP(); this._stopSSE(); this._setLoading(false); this._hideProgress();
          this._showResults(task);
        } else if (task.status === 'error') {
          this._stopSP(); this._stopSSE(); this._setLoading(false); this._hideProgress();
          this._showError(task.error || 'Processing error');
        }
      } catch (_) {}
    };

    this.eventSource.onerror = async () => {
      this._stopSSE();
      try {
        if (this.currentTaskId) {
          const r = await fetch(`${this.apiBase}/task-status/${this.currentTaskId}`);
          if (r.ok) {
            const task = await r.json();
            if (task?.status === 'completed') {
              this._stopSP(); this._setLoading(false); this._hideProgress();
              this._showResults(task);
              return;
            }
          }
        }
      } catch (_) {}
      this._showError(this.t('error_processing_failed') + 'SSE disconnected');
      this._setLoading(false);
    };
  }

  _stopSSE() {
    if (this.eventSource) { this.eventSource.close(); this.eventSource = null; }
  }

  /* ── Progress ─────────────────────────────────────────── */
  _updateProgress(pct, msg, fromServer = false) {
    if (fromServer) {
      this._stopSP();
      this.sp.lastServer = pct;
      this.sp.current    = pct;
      this._renderProgress(pct, msg);
      this._updateStage(pct, msg);
      this._startSP();
    } else {
      this._renderProgress(pct, msg);
    }
  }

  _updateStage(pct, msg) {
    const m = (msg || '').toLowerCase();

    // ── 字幕路径（快速）──────────────────────────────────────
    if (m.includes('获取成功') || m.includes('subtitle found') || m.includes('字幕获取')) {
      this.sp.stage = 'subtitle_found';
      this.sp.target = 55;
      this._setModeBadge('subtitle');
    }
    // ── 无字幕 → 音频下载路径（慢）────────────────────────────
    else if (m.includes('未找到字幕') || m.includes('no subtitle') || m.includes('下载视频音频') || m.includes('下载音频')) {
      this.sp.stage = 'downloading';
      this.sp.target = 55;
      this._setModeBadge('whisper');
    }
    else if (m.includes('读取文本') || (m.includes('read') && m.includes('text'))) {
      this.sp.stage = 'parsing';
      this.sp.target = 55;
      this._setModeBadge('whisper');
    }
    else if (m.includes('转换音频') || m.includes('准备转录')) {
      this.sp.stage = 'downloading';
      this.sp.target = 55;
      this._setModeBadge('whisper');
    }
    else if (m.includes('上传') || m.includes('upload')) {
      this.sp.stage = 'preparing';
      this.sp.target = 40;
    }
    // ── 收尾等待原视频（须排在通用「下载/准备」判断之前）─────────────
    else if (m.includes('原视频') || m.includes('original video')) {
      this.sp.stage = 'finalizing';
      this.sp.target = 99;
    }
    // ── 通用字幕检测中 ─────────────────────────────────────────
    else if (m.includes('检测') && (m.includes('字幕') || m.includes('subtitle'))) {
      this.sp.stage = 'subtitle';
      this.sp.target = 40;
    }
    // ── 其他阶段 ───────────────────────────────────────────────
    else if (m.includes('解析') || m.includes('pars'))                     { this.sp.stage = 'parsing';       this.sp.target = 60; }
    else if (m.includes('下载') || m.includes('download'))                 { this.sp.stage = 'downloading';   this.sp.target = 60; }
    else if (m.includes('转录') || m.includes('transcrib') || m.includes('whisper')) { this.sp.stage = 'transcribing';  this.sp.target = 80; }
    else if (m.includes('优化') || m.includes('optimiz'))                  { this.sp.stage = 'optimizing';    this.sp.target = 90; }
    else if (m.includes('摘要') || m.includes('summary'))                  { this.sp.stage = 'summarizing';   this.sp.target = 95; }
    else if (m.includes('完成') || m.includes('complet'))                  { this.sp.stage = 'completed';     this.sp.target = 100; }

    if (pct >= this.sp.target) this.sp.target = Math.min(pct + 8, 99);
  }

  _setModeBadge(mode) {
    if (!this.modeBadge) return;
    if (mode === 'subtitle') {
      this.modeBadge.textContent  = this.t('mode_subtitle');
      this.modeBadge.className    = 'mode-badge subtitle';
      this.modeBadge.style.display = 'inline-block';
      if (this.progressFill) this.progressFill.classList.add('subtitle-mode');
    } else if (mode === 'whisper') {
      this.modeBadge.textContent  = this.t('mode_whisper');
      this.modeBadge.className    = 'mode-badge whisper';
      this.modeBadge.style.display = 'inline-block';
      if (this.progressFill) this.progressFill.classList.remove('subtitle-mode');
    }
  }

  _initSP() {
    this.sp.enabled = false; this.sp.current = 0; this.sp.target = 15;
    this.sp.lastServer = 0;  this.sp.startTime = Date.now(); this.sp.stage = 'preparing';
  }
  _startSP() {
    if (this.sp.interval) clearInterval(this.sp.interval);
    this.sp.enabled   = true;
    this.sp.startTime = this.sp.startTime || Date.now();
    this.sp.interval  = setInterval(() => this._tickSP(), 500);
  }
  _stopSP() {
    if (this.sp.interval) { clearInterval(this.sp.interval); this.sp.interval = null; }
    this.sp.enabled = false;
  }
  _tickSP() {
    if (!this.sp.enabled || this.sp.current >= this.sp.target) return;
    const speeds = { subtitle: .5, parsing: .3, downloading: .18, transcribing: .14, optimizing: .22, summarizing: .28, finalizing: .16 };
    let inc = speeds[this.sp.stage] || .2;
    const remaining = this.sp.target - this.sp.current;
    if (remaining < 5) inc *= .3;
    const next = Math.min(this.sp.current + inc, this.sp.target);
    if (next > this.sp.current) {
      this.sp.current = next;
      this._renderProgress(next, this._stageMsg());
    }
  }
  _stageMsg() {
    const map = {
      subtitle:       this.t('detecting_subtitles'),
      subtitle_found: this.t('subtitle_found'),
      downloading:    this.t('downloading_video'),
      parsing:        this.t('parsing_video'),
      transcribing:   this.t('transcribing_audio'),
      optimizing:     this.t('optimizing_transcript'),
      summarizing:    this.t('generating_summary'),
      finalizing:     this.t('preparing_video'),
      completed:      this.t('completed'),
    };
    return map[this.sp.stage] || this.t('processing');
  }

  _renderProgress(pct, msg) {
    const p = Math.round(pct * 10) / 10;
    this.progressStatus.textContent = `${p}%`;
    this.progressFill.style.width   = `${p}%`;

    // Translate common server messages — more specific checks first
    const m = (msg || '').toLowerCase();
    let label = msg;
    // ── Subtitle path ──────────────────────────────────────────
    if      (m.includes('获取成功') || m.includes('subtitle found'))        label = this.t('subtitle_found');
    else if (m.includes('未找到字幕') || m.includes('no subtitle'))         label = this.t('no_subtitle');
    else if (m.includes('检测') && (m.includes('字幕') || m.includes('subtitle'))) label = this.t('detecting_subtitles');
    // ── Original video (before the generic download/prepare checks) ──
    else if (m.includes('原视频') || m.includes('original video')) label = this.t('preparing_video');
    // ── Audio / Whisper path ────────────────────────────────────
    else if (m.includes('下载') || m.includes('download'))  label = this.t('downloading_video');
    else if (m.includes('解析') || m.includes('pars'))      label = this.t('parsing_video');
    else if (m.includes('转录') || m.includes('transcrib')) label = this.t('transcribing_audio');
    else if (m.includes('优化') || m.includes('optimiz'))   label = this.t('optimizing_transcript');
    else if (m.includes('摘要') || m.includes('summary'))   label = this.t('generating_summary');
    else if (m.includes('完成') || m.includes('complet'))   label = this.t('completed');
    else if (m.includes('准备') || m.includes('prepar'))    label = this.t('preparing');

    this.progressMessage.textContent = label;
  }

  _showProgress() {
    this.emptyState.style.display    = 'none';
    this.resultsPanel.classList.remove('show');
    this.progressPanel.classList.add('show');
    this._clearMedia();
    // Reset mode badge & progress bar color for new task
    if (this.modeBadge) { this.modeBadge.style.display = 'none'; this.modeBadge.className = 'mode-badge'; }
    if (this.progressFill) this.progressFill.classList.remove('subtitle-mode');
  }
  _hideProgress() { this.progressPanel.classList.remove('show'); }

  /* ── Results ──────────────────────────────────────────── */
  /** 与后端 Translator.normalize_lang_code 对齐，用于 Tab 展示判断 */
  _normLangTab(code) {
    if (!code) return '';
    const c = String(code).toLowerCase().trim();
    if (c.startsWith('zh')) return 'zh';
    if (c.length >= 2) return c.slice(0, 2);
    return c;
  }

  _showResults(task) {
    const script      = task.script;
    const summary     = task.summary;
    const translation = task.translation;
    this._markdown = { script, summary, translation };

    this.scriptContent.innerHTML  = script    ? marked.parse(script)      : '';
    this.summaryContent.innerHTML = summary   ? marked.parse(summary)     : '';

    // No speech in the source: there is no summary or translation to show, and
    // the backend deliberately skipped the LLM so nothing gets fabricated.
    const noSpeech = Boolean(task.no_speech);
    this.noSpeechBanner.classList.toggle('show', noSpeech);
    this.summaryTabItem.style.display = noSpeech ? 'none' : 'flex';

    const d = this._normLangTab(task.detected_language);
    const s = this._normLangTab(task.summary_language);
    const showTranslation = !noSpeech && Boolean(translation) && d && s && d !== s;
    if (showTranslation) {
      this.translationContent.innerHTML = marked.parse(translation);
      this.translationTabItem.style.display = 'flex';
    } else {
      this.translationTabItem.style.display = 'none';
    }

    this._renderMedia(task);

    // Self-sufficient: don't rely on _showProgress() having hidden the empty state
    this.emptyState.style.display = 'none';
    this.resultsPanel.classList.add('show');
    this._switchTab('script');
    this.resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  _hideResults() { this.resultsPanel.classList.remove('show'); }

  /* ── Original video / audio ───────────────────────────── */
  _renderMedia(task) {
    this._clearMedia();

    const file = task.media_filename;
    if (!file) return;

    this._mediaFile = file;
    this._mediaName = task.media_download_name || file;

    const isAudio = task.media_kind === 'audio';
    this._mediaIsAudio = isAudio;
    const el = document.createElement(isAudio ? 'audio' : 'video');
    el.src       = `${this.apiBase}/media/${encodeURIComponent(file)}`;
    el.controls  = true;
    el.preload   = 'metadata';
    el.className = isAudio ? 'media-audio' : 'media-video';
    this.mediaFrame.appendChild(el);

    this._applyMediaLabels();

    const bits = [];
    const ext = file.split('.').pop();
    if (ext) bits.push(ext.toUpperCase());
    const size = this._fmtSize(task.media_size_bytes);
    if (size) bits.push(size);
    this.mediaMeta.textContent = bits.join('  ·  ');

    this.mediaBlock.style.display = 'block';
    // Lives in the tab row now, so it needs toggling separately from the block
    if (this.dlVideo) this.dlVideo.style.display = 'inline-flex';
  }

  /**
   * Label + button wording follow the actual media kind (video vs audio).
   * Re-applied on language switch, which would otherwise reset both to the
   * video wording via their data-i18n keys.
   */
  _applyMediaLabels() {
    if (!this.mediaBlock || !this._mediaFile) return;
    const isAudio = this._mediaIsAudio;
    const labelEl = this.mediaBlock.querySelector('[data-i18n="original_media"]');
    const btnEl   = this.dlVideo && this.dlVideo.querySelector('[data-i18n="download_video"]');
    if (labelEl) labelEl.textContent = this.t(isAudio ? 'original_media_audio' : 'original_media');
    if (btnEl)   btnEl.textContent   = this.t(isAudio ? 'download_audio' : 'download_video');
  }

  /** Bytes → KB/MB/GB. Small clips shouldn't read as "0.0 MB". */
  _fmtSize(bytes) {
    if (!bytes || bytes <= 0) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let v = bytes, i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
    return `${v < 10 && i > 0 ? v.toFixed(1) : Math.round(v)} ${units[i]}`;
  }

  /** Stop playback and drop the source so a new task can't inherit stale media. */
  _clearMedia() {
    this._mediaFile = null;
    this._mediaName = null;
    this._mediaIsAudio = false;
    if (this.dlVideo) this.dlVideo.style.display = 'none';
    if (!this.mediaBlock) return;
    const el = this.mediaFrame.querySelector('video, audio');
    if (el) { try { el.pause(); } catch (_) {} el.removeAttribute('src'); el.load?.(); }
    this.mediaFrame.innerHTML = '';
    this.mediaMeta.textContent = '';
    this.mediaBlock.style.display = 'none';
  }

  _downloadMedia() {
    if (!this._mediaFile) { this._showError(this.t('error_no_video')); return; }
    const href = `${this.apiBase}/download/${encodeURIComponent(this._mediaFile)}`
               + `?name=${encodeURIComponent(this._mediaName)}`;
    const a = document.createElement('a');
    a.href = href;
    a.download = this._mediaName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  /* ── Tabs ─────────────────────────────────────────────── */
  _switchTab(name) {
    this.tabItems.forEach(it => it.classList.toggle('active', it.dataset.tab === name));
    this.tabPanes.forEach(p  => p.classList.toggle('active', p.id === `${name}Tab`));
  }

  /* ── Download ─────────────────────────────────────────── */
  async _downloadFile(type) {
    if (!this.currentTaskId) { this._showError(this.t('error_no_download')); return; }
    try {
      const r = await fetch(`${this.apiBase}/task-status/${this.currentTaskId}`);
      if (!r.ok) throw new Error('Failed to get task status');
      const task = await r.json();

      let filename;
      if      (type === 'script')      filename = task.script_path      ? task.script_path.split('/').pop()      : `transcript_${task.safe_title||'x'}_${task.short_id||'x'}.md`;
      else if (type === 'summary')     filename = task.summary_path     ? task.summary_path.split('/').pop()     : `summary_${task.safe_title||'x'}_${task.short_id||'x'}.md`;
      else if (type === 'translation') filename = task.translation_path ? task.translation_path.split('/').pop() : `translation_${task.safe_title||'x'}_${task.short_id||'x'}.md`;
      else throw new Error('Unknown type');

      const a = document.createElement('a');
      a.href = `${this.apiBase}/download/${encodeURIComponent(filename)}`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e) {
      this._showError(this.t('error_download_failed') + e.message);
    }
  }

  /* ── Copy ─────────────────────────────────────────────── */
  async _copyMarkdown(type, btn) {
    const text = this._markdown[type];
    if (!text) { this._showError(this.t('error_no_download')); return; }
    try {
      await this._writeClipboard(text);
    } catch (e) {
      this._showError(this.t('error_copy_failed') + e.message);
      return;
    }
    const icon = btn.querySelector('i');
    icon.className = 'fas fa-check';
    clearTimeout(btn._copyReset);
    btn._copyReset = setTimeout(() => { icon.className = 'fas fa-copy'; }, 1500);
  }

  async _writeClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    // navigator.clipboard is undefined over plain http, e.g. the Docker image opened by LAN IP
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    if (!ok) throw new Error('clipboard unavailable');
  }

  /* ── UI helpers ───────────────────────────────────────── */
  _setLoading(on) {
    this.submitBtn.disabled = on;
    this.submitBtn.innerHTML = on
      ? `<span class="spinner"></span> ${this.t('processing')}`
      : `<i class="fas fa-search"></i> <span>${this.t('start_transcription')}</span>`;
    if (this.uploadPickBtn) this.uploadPickBtn.disabled = on;
    if (this.uploadZone) {
      this.uploadZone.style.pointerEvents = on ? 'none' : '';
      this.uploadZone.style.opacity = on ? '0.65' : '';
      this.uploadZone.tabIndex = on ? -1 : 0;
    }
    if (this.fileInput) this.fileInput.disabled = on;
  }

  _showError(msg) {
    this.errorMsg.textContent = msg;
    this.errorBanner.classList.add('show');
    this.errorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    setTimeout(() => this._hideError(), 6000);
  }
  _hideError() { this.errorBanner.classList.remove('show'); }

  _debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }
}

/* ── Boot ──────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  window.vt = new VideoTranscriber();
});

window.addEventListener('beforeunload', () => {
  if (window.vt?.eventSource) window.vt._stopSSE();
});
