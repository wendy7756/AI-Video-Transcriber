/* ────────────────────────────────────────────────────────────
   AI Video Transcriber · app.js
   ──────────────────────────────────────────────────────────── */

class VideoTranscriber {
  constructor() {
    this.currentTaskId  = null;
    this.eventSource    = null;
    this.apiBase        = '/api';
    this.currentLang    = 'zh';
    this.defaultBaseUrl  = 'https://openrouter.ai/api/v1';
    this.defaultModelId  = 'google/gemini-2.0-flash-001';
    this.llmPresets     = null;
    this.currentProviderId = 'openrouter';
    this._fetchedModels = [];

    /* Smart progress simulation */
    this.sp = {
      enabled: false, current: 0, target: 15,
      lastServer: 0, interval: null, startTime: null, stage: 'preparing'
    };

    this.i18n = {
      en: {
        title:                   'Video Trans',
        subtitle:                'Paste a video URL or upload a file — preview the video when done; transcript & export under Advanced.',
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
        provider_preset:         'Provider',
        models_recommended:      'Recommended',
        models_fetched:          'From API',
        summary_language:        'Summary Language',
        processing_progress:     'Processing',
        preparing:               'Preparing…',
        transcript_text:         'Transcript',
        intelligent_summary:     'AI Summary',
        translation:             'Translation',
        download_transcript:     'Transcript',
        download_translation:    'Translation',
        download_summary:        'Summary',
        download_media:          'Video',
        export_bundle:           'Export bundle (video + transcript)',
        advanced_panel:          'Advanced · Transcript & export',
        no_video_preview:        'No video preview available',
        from_cache:              'Loaded from local cache',
        empty_hint:              'Paste a video URL or drop a file above and let AI do the heavy lifting.',
        footer_text:             'Video Trans — AI video transcription & summary',
        processing:              'Processing…',
        downloading_video:       'Downloading video…',
        parsing_video:           'Parsing video info…',
        transcribing_audio:      'Transcribing audio…',
        optimizing_transcript:   'Optimizing transcript…',
        generating_summary:      'Generating summary…',
        detecting_subtitles:     'Detecting subtitles…',
        subtitle_found:          'Subtitles found! Processing text…',
        no_subtitle:             'No subtitles found, downloading video…',
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
      },
      zh: {
        title:                   'Video Trans',
        subtitle:                '粘贴视频链接或上传文件，完成后直接预览视频；文案与导出在高级选项中。',
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
        provider_preset:         '模型提供商',
        models_recommended:      '推荐三方模型',
        models_fetched:          '接口返回模型',
        summary_language:        '摘要语言',
        processing_progress:     '处理进度',
        preparing:               '准备中…',
        transcript_text:         '转录文本',
        intelligent_summary:     '智能摘要',
        translation:             '翻译',
        download_transcript:     '转写文案',
        download_translation:    '翻译',
        download_summary:        '摘要',
        download_media:          '视频',
        export_bundle:           '打包导出（视频+文案）',
        advanced_panel:          '高级 · 文案与导出',
        no_video_preview:        '暂无视频预览',
        from_cache:              '已命中本地缓存',
        empty_hint:              '在上方粘贴视频链接或拖放文件，让 AI 来处理一切。',
        footer_text:             'Video Trans — AI 视频转录与摘要',
        processing:              '处理中…',
        downloading_video:       '正在下载视频…',
        parsing_video:           '正在解析视频信息…',
        transcribing_audio:      '正在转录音频…',
        optimizing_transcript:   '正在优化转录文本…',
        generating_summary:      '正在生成摘要…',
        detecting_subtitles:     '正在检测字幕…',
        subtitle_found:          '字幕获取成功！正在处理文本…',
        no_subtitle:             '未找到字幕，正在下载视频…',
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
      }
    };

    this._initElements();
    this._bindEvents();
    this._switchLang('zh');
    this._bootstrapSettings();
  }

  async _bootstrapSettings() {
    await this._loadLlmPresets();
    this._loadSettings();
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
    this.dlMedia            = document.getElementById('downloadMedia');
    this.exportBundle       = document.getElementById('exportBundle');
    this.cacheBadge         = document.getElementById('cacheBadge');
    this.resultTitle        = document.getElementById('resultTitle');
    this.resultVideo        = document.getElementById('resultVideo');
    this.videoEmpty         = document.getElementById('videoEmpty');
    this.advancedPanel      = document.getElementById('advancedPanel');
    this.translationTabBtn  = document.getElementById('translationTabBtn');
    this.tabBtns            = document.querySelectorAll('.tab-btn');
    this.tabPanes           = document.querySelectorAll('.tab-pane');
    // settings
    this.settingsToggle     = document.getElementById('settingsToggle');
    this.settingsBody       = document.getElementById('settingsBody');
    this.providerPreset     = document.getElementById('providerPreset');
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

    if (this.providerPreset) {
      this.providerPreset.addEventListener('change', () => this._onProviderChange());
    }

    // Auto-fetch when both fields filled (debounced)
    const debouncedFetch = this._debounce(() => {
      if (this.modelBaseUrl.value.trim() && this.apiKeyInput.value.trim()) this._fetchModels();
    }, 900);
    this.modelBaseUrl.addEventListener('input', debouncedFetch);
    this.apiKeyInput.addEventListener('input', debouncedFetch);

    // Persist settings
    [this.modelBaseUrl, this.apiKeyInput, this.modelSelect, this.summaryLangSel, this.providerPreset].forEach(el => {
      if (!el) return;
      el.addEventListener('change', () => this._saveSettings());
    });

    // Tabs
    this.tabBtns.forEach(btn => {
      btn.addEventListener('click', () => this._switchTab(btn.dataset.tab));
    });

    // Downloads
    this.dlScript.addEventListener('click',      () => this._downloadFile('script'));
    this.dlTranslation.addEventListener('click', () => this._downloadFile('translation'));
    this.dlSummary.addEventListener('click',     () => this._downloadFile('summary'));
    if (this.dlMedia) this.dlMedia.addEventListener('click', () => this._downloadMedia());
    if (this.exportBundle) this.exportBundle.addEventListener('click', () => this._exportBundle());

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
      if (typeof v === 'string') el.textContent = v;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const v = this.t(el.dataset.i18nPlaceholder);
      if (typeof v === 'string') el.placeholder = v;
    });
  }

  /* ── Settings persistence ─────────────────────────────── */
  _saveSettings() {
    const s = {
      provider: this.providerPreset ? this.providerPreset.value : this.currentProviderId,
      baseUrl:  this.modelBaseUrl.value,
      apiKey:   this.apiKeyInput.value,
      model:    this.modelSelect.value,
      summaryLang: this.summaryLangSel.value,
    };
    try { localStorage.setItem('vt_settings', JSON.stringify(s)); } catch (_) {}
  }

  async _loadLlmPresets() {
    try {
      const resp = await fetch(`${this.apiBase}/llm-presets`);
      if (resp.ok) {
        this.llmPresets = await resp.json();
        this.defaultBaseUrl = this.llmPresets.providers?.find(p => p.id === this.llmPresets.default_provider)?.base_url
          || this.defaultBaseUrl;
        this.defaultModelId = this.llmPresets.default_model || this.defaultModelId;
        this.currentProviderId = this.llmPresets.default_provider || 'openrouter';
      }
    } catch (e) {
      console.warn('Failed to load LLM presets:', e);
    }
    this._renderProviderOptions();
  }

  _renderProviderOptions() {
    if (!this.providerPreset) return;
    const providers = this.llmPresets?.providers || [
      { id: 'openrouter', name: 'OpenRouter', base_url: this.defaultBaseUrl },
    ];
    this.providerPreset.innerHTML = '';
    providers.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      opt.title = p.hint || p.base_url;
      this.providerPreset.appendChild(opt);
    });
    this.providerPreset.value = this.currentProviderId;
  }

  _presetModelsFor(providerId) {
    const all = this.llmPresets?.recommended_models || [];
    return all.filter(m => (m.providers || []).includes(providerId));
  }

  _onProviderChange() {
    if (!this.providerPreset) return;
    this.currentProviderId = this.providerPreset.value;
    const provider = this.llmPresets?.providers?.find(p => p.id === this.currentProviderId);
    if (provider?.base_url) {
      this.modelBaseUrl.value = provider.base_url;
    }
    this._fetchedModels = [];
    this._renderModelOptions(this.currentProviderId, [], this.modelSelect.value || this.defaultModelId);
    this._saveSettings();
  }

  _renderModelOptions(providerId, extraModels = [], preferredId = '') {
    const presets = this._presetModelsFor(providerId);
    const sel = this.modelSelect;
    sel.innerHTML = '';

    const recommended = document.createElement('optgroup');
    recommended.label = this.t('models_recommended');
    presets.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.name ? `${m.name} (${m.id})` : m.id;
      recommended.appendChild(opt);
    });
    sel.appendChild(recommended);

    if (extraModels.length) {
      const fetched = document.createElement('optgroup');
      fetched.label = this.t('models_fetched');
      const seen = new Set(presets.map(p => p.id));
      extraModels.forEach(m => {
        const id = m.id || m;
        if (!id || seen.has(id)) return;
        seen.add(id);
        const opt = document.createElement('option');
        opt.value = id;
        opt.textContent = m.name || id;
        fetched.appendChild(opt);
      });
      if (fetched.children.length) sel.appendChild(fetched);
    }

    const fallback = document.createElement('option');
    fallback.value = '';
    fallback.textContent = this.t('model_default');
    sel.appendChild(fallback);

    const pick = preferredId || this.defaultModelId;
    if ([...sel.options].some(o => o.value === pick)) {
      sel.value = pick;
    }
  }

  _loadSettings() {
    try {
      const raw = localStorage.getItem('vt_settings');
      if (!raw) {
        this.summaryLangSel.value = 'zh';
        this.modelBaseUrl.value = this.defaultBaseUrl;
        if (this.providerPreset) this.providerPreset.value = this.currentProviderId;
        this._renderModelOptions(this.currentProviderId, [], this.defaultModelId);
        return;
      }
      const s = JSON.parse(raw);
      if (s.provider && this.providerPreset) {
        this.currentProviderId = s.provider;
        this.providerPreset.value = s.provider;
      }
      if (s.baseUrl)     this.modelBaseUrl.value = s.baseUrl;
      if (s.apiKey)      this.apiKeyInput.value  = s.apiKey;
      if (s.summaryLang) this.summaryLangSel.value = s.summaryLang;
      else               this.summaryLangSel.value = 'zh';
      this._savedModel = s.model || '';
      this._renderModelOptions(
        this.currentProviderId,
        this._fetchedModels,
        this._savedModel || this.defaultModelId,
      );

      // Auto-open settings if credentials were saved
      if (s.baseUrl || s.apiKey) {
        this.settingsBody.classList.add('open');
        this.settingsToggle.classList.add('open');
        if (s.baseUrl && s.apiKey) {
          setTimeout(() => this._fetchModels(true), 400);
        }
      }
    } catch (_) {}
  }

  _applyDefaultModelOption() {
    this._renderModelOptions(this.currentProviderId, [], this.defaultModelId);
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
      this._fetchedModels = models;

      this._renderModelOptions(
        this.currentProviderId,
        models,
        this._savedModel || this.modelSelect.value || this.defaultModelId,
      );
      this._savedModel = '';

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
      this._showError(this.t('error_processing_failed') + this._formatRequestError(err));
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
      this._showError(this.t('error_processing_failed') + this._formatRequestError(err));
      this._setLoading(false);
      this._hideProgress();
    }
  }

  _formatRequestError(err) {
    const msg = (err && err.message) ? err.message : String(err);
    if (/load failed|failed to fetch|networkerror|network error/i.test(msg)) {
      return this.currentLang === 'zh'
        ? '无法连接后端服务，请确认本地服务已启动（8765 或 8000）'
        : 'Cannot reach backend — make sure the local server is running (8765 or 8000)';
    }
    return msg;
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
    else if (m.includes('缓存') || m.includes('cache'))                    { this.sp.stage = 'completed';     this.sp.target = 100; }
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
    const speeds = { subtitle: .5, parsing: .3, downloading: .18, transcribing: .14, optimizing: .22, summarizing: .28 };
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

  _mediaUrl(task) {
    const filename = task?.media_filename
      || (task?.media_path ? task.media_path.split('/').pop() : null);
    if (!filename) return null;
    return `${this.apiBase}/download/${encodeURIComponent(filename)}`;
  }

  _showMediaPreview(task) {
    const url = this._mediaUrl(task);
    if (!this.resultVideo || !this.videoEmpty) return;

    if (url) {
      this.resultVideo.src = url;
      this.resultVideo.style.display = 'block';
      this.videoEmpty.style.display = 'none';
      if (this.dlMedia) this.dlMedia.style.display = 'inline-flex';
    } else {
      this.resultVideo.pause();
      this.resultVideo.removeAttribute('src');
      this.resultVideo.load();
      this.resultVideo.style.display = 'none';
      this.videoEmpty.style.display = 'flex';
      if (this.dlMedia) this.dlMedia.style.display = 'none';
    }
  }

  _showResults(taskOrScript, summary, videoTitle, translation, detectedLang, summaryLang) {
    const task = (typeof taskOrScript === 'object' && taskOrScript !== null)
      ? taskOrScript
      : {
          script: taskOrScript,
          summary,
          video_title: videoTitle,
          translation,
          detected_language: detectedLang,
          summary_language: summaryLang,
        };

    this.currentTaskMeta = task;
    const script = task.script;
    const summaryText = task.summary;
    const translationText = task.translation;
    detectedLang = task.detected_language;
    summaryLang = task.summary_language;

    this.scriptContent.innerHTML  = script      ? marked.parse(script)      : '';
    this.summaryContent.innerHTML = summaryText ? marked.parse(summaryText) : '';

    const d = this._normLangTab(detectedLang);
    const s = this._normLangTab(summaryLang);
    const showTranslation = Boolean(translationText) && d && s && d !== s;
    if (showTranslation) {
      this.translationContent.innerHTML = marked.parse(translationText);
      this.translationTabBtn.style.display  = 'inline-block';
      this.dlTranslation.style.display      = 'inline-flex';
    } else {
      this.translationTabBtn.style.display  = 'none';
      this.dlTranslation.style.display      = 'none';
    }

    const hasMedia = Boolean(task.media_path || task.media_filename);
    if (this.cacheBadge) this.cacheBadge.classList.toggle('show', Boolean(task.from_cache));
    if (this.resultTitle) {
      this.resultTitle.textContent = task.video_title || '';
      this.resultTitle.style.display = task.video_title ? 'block' : 'none';
    }
    this._showMediaPreview(task);
    if (this.advancedPanel) this.advancedPanel.open = false;

    this.resultsPanel.classList.add('show');
    this._switchTab('script');
    this.resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  _hideResults() {
    this.resultsPanel.classList.remove('show');
    if (this.cacheBadge) this.cacheBadge.classList.remove('show');
    if (this.dlMedia) this.dlMedia.style.display = 'none';
    if (this.advancedPanel) this.advancedPanel.open = false;
    if (this.resultVideo) {
      this.resultVideo.pause();
      this.resultVideo.removeAttribute('src');
      this.resultVideo.load();
      this.resultVideo.style.display = 'none';
    }
    if (this.videoEmpty) this.videoEmpty.style.display = 'flex';
    if (this.resultTitle) this.resultTitle.textContent = '';
  }

  async _fetchCurrentTask() {
    if (!this.currentTaskId) throw new Error(this.t('error_no_download'));
    const r = await fetch(`${this.apiBase}/task-status/${this.currentTaskId}`);
    if (!r.ok) throw new Error('Failed to get task status');
    return r.json();
  }

  /* ── Tabs ─────────────────────────────────────────────── */
  _switchTab(name) {
    this.tabBtns.forEach(b  => b.classList.toggle('active',  b.dataset.tab === name));
    this.tabPanes.forEach(p => p.classList.toggle('active', p.id === `${name}Tab`));
  }

  /* ── Download ─────────────────────────────────────────── */
  async _downloadFile(type) {
    try {
      const task = await this._fetchCurrentTask();

      let filename;
      if      (type === 'script')      filename = task.script_filename      || (task.script_path      ? task.script_path.split('/').pop()      : `transcript_${task.safe_title||'x'}_${task.short_id||'x'}.md`);
      else if (type === 'summary')     filename = task.summary_filename     || (task.summary_path     ? task.summary_path.split('/').pop()     : `summary_${task.safe_title||'x'}_${task.short_id||'x'}.md`);
      else if (type === 'translation') filename = task.translation_filename || (task.translation_path ? task.translation_path.split('/').pop() : `translation_${task.safe_title||'x'}_${task.short_id||'x'}.md`);
      else throw new Error('Unknown type');

      this._triggerDownload(`${this.apiBase}/download/${encodeURIComponent(filename)}`, filename);
    } catch (e) {
      this._showError(this.t('error_download_failed') + e.message);
    }
  }

  async _downloadMedia() {
    try {
      const task = await this._fetchCurrentTask();
      const url = this._mediaUrl(task);
      if (!url) throw new Error(this.t('error_no_download'));
      const filename = task.media_filename
        || (task.media_path ? task.media_path.split('/').pop() : 'video.mp4');
      this._triggerDownload(url, filename);
    } catch (e) {
      this._showError(this.t('error_download_failed') + e.message);
    }
  }

  _exportBundle() {
    if (!this.currentTaskId) {
      this._showError(this.t('error_no_download'));
      return;
    }
    const task = this.currentTaskMeta || {};
    const zipName = `${task.safe_title || 'export'}_${task.short_id || this.currentTaskId.slice(0, 6)}.zip`;
    this._triggerDownload(`${this.apiBase}/export/${encodeURIComponent(this.currentTaskId)}`, zipName);
  }

  _triggerDownload(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
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
