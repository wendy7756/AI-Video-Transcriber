/**
 * AI 影片轉錄器前端應用程式
 * 
 * 這是一個支援多平台影片（YouTube、TikTok、Bilibili等）自動轉錄和智慧摘要的前端應用程式。
 * 主要功能包括：
 * - 影片URL輸入和驗證
 * - 即時處理進度顯示和智慧進度模擬
 * - 多語言國際化支援（中文/英文）
 * - Server-Sent Events (SSE) 即時通訊
 * - 轉錄結果、翻譯和摘要的分頁顯示
 * - 檔案下載功能
 * 
 * @author AI Video Transcriber Team
 * @version 1.0.0
 * @since 2024
 */

/**
 * VideoTranscriber 類別 - 影片轉錄器的主要控制器
 * 
 * 負責管理整個前端應用程式的生命週期，包括：
 * - 使用者介面初始化和事件綁定
 * - 與後端 API 的通訊
 * - 處理進度追蹤和顯示
 * - 管理多語言切換
 * - 處理檔案下載
 * 
 * @class VideoTranscriber
 */
class VideoTranscriber {
    /**
     * VideoTranscriber 建構函式
     * 
     * 初始化影片轉錄器實例，設定預設值和配置，
     * 包括 API 端點、語言設定、智慧進度系統等
     * 
     * @constructor
     */
    constructor() {
        /** @type {string|null} 目前正在處理的任務ID */
        this.currentTaskId = null;
        
        /** @type {EventSource|null} Server-Sent Events 連線物件 */
        this.eventSource = null;
        
        /** @type {string} API 基礎URL，動態產生以適應不同部署環境 */
        this.apiBase = `${window.location.protocol}//${window.location.hostname}:${window.location.port}/api`;
        
        /** @type {string} 目前使用的語言代碼，預設為英文 */
        this.currentLanguage = 'en';
        
        /**
         * 智慧進度模擬系統配置
         * 用於在等待伺服器更新期間提供流暢的使用者體驗
         * @type {Object}
         */
        this.smartProgress = {
            enabled: false,          // 是否啟用智慧進度模擬
            current: 0,             // 目前顯示的進度值 (0-100)
            target: 0,              // 目標進度值，模擬會逐漸接近此值
            lastServerUpdate: 0,    // 最後一次從伺服器接收的真實進度
            interval: null,         // 進度更新定時器
            estimatedDuration: 0,   // 預估處理總時長（秒）
            startTime: null,        // 任務開始時間戳
            stage: 'preparing'      // 目前處理階段標識
        };
        
        /**
         * 多語言翻譯字典
         * 包含所有使用者介面文字的中英文對照
         * @type {Object}
         */
        this.translations = {
            en: {
                title: "AI Video Transcriber",
                subtitle: "Supports automatic transcription and AI summary for YouTube, Tiktok, Bilibili and other platforms",
                video_url: "Video URL",
                video_url_placeholder: "Enter YouTube, Tiktok, Bilibili or other platform video URLs...",
                summary_language: "Summary Language",
                start_transcription: "Start",
                processing_progress: "Processing Progress",
                preparing: "Preparing...",
                transcription_results: "Results",
                download_transcript: "Download Transcript",
                download_translation: "Download Translation",
                download_summary: "Download Summary",
                transcript_text: "Transcript Text",
                translation: "Translation",
                intelligent_summary: "AI Summary",
                footer_text: "Powered by AI, supports multi-platform video transcription",
                processing: "Processing...",
                downloading_video: "Downloading video...",
                parsing_video: "Parsing video info...",
                transcribing_audio: "Transcribing audio...",
                optimizing_transcript: "Optimizing transcript...",
                generating_summary: "Generating summary...",
                completed: "Processing completed!",
                error_invalid_url: "Please enter a valid video URL",
                error_processing_failed: "Processing failed: ",
                error_task_not_found: "Task not found",
                error_task_not_completed: "Task not completed yet",
                error_invalid_file_type: "Invalid file type",
                error_file_not_found: "File not found",
                error_download_failed: "Download failed: ",
                error_no_file_to_download: "No file available for download"
            },
            zh: {
                title: "AI影片轉錄器",
                subtitle: "支援YouTube、Tiktok、Bilibili等平台的影片自動轉錄和智慧摘要",
                video_url: "影片連結",
                video_url_placeholder: "請輸入YouTube、Tiktok、Bilibili等平台的影片連結...",
                summary_language: "摘要語言",
                start_transcription: "開始轉錄",
                processing_progress: "處理進度",
                preparing: "準備中...",
                transcription_results: "轉錄結果",
                download_transcript: "下載轉錄",
                download_translation: "下載翻譯",
                download_summary: "下載摘要",
                transcript_text: "轉錄文字",
                translation: "翻譯",
                intelligent_summary: "AI 摘要",
                footer_text: "由 AI 驅動，支援多平台影片轉錄",
                processing: "處理中...",
                downloading_video: "正在下載影片...",
                parsing_video: "正在解析影片資訊...",
                transcribing_audio: "正在轉錄音訊...",
                optimizing_transcript: "正在最佳化轉錄文字...",
                generating_summary: "正在產生摘要...",
                completed: "處理完成！",
                error_invalid_url: "請輸入有效的影片連結",
                error_processing_failed: "處理失敗：",
                error_task_not_found: "任務不存在",
                error_task_not_completed: "任務尚未完成",
                error_invalid_file_type: "無效的檔案類型",
                error_file_not_found: "檔案不存在",
                error_download_failed: "下載檔案失敗：",
                error_no_file_to_download: "沒有可下載的檔案"
            }
        };
        
        // 初始化應用程式
        this.initializeElements();
        this.bindEvents();
        this.initializeLanguage();
    }
    
    /**
     * 初始化DOM元素引用
     * 
     * 取得頁面中所有需要操作的DOM元素並儲存為實例屬性，
     * 包括表單控制項、進度顯示元素、結果區域等
     * 
     * @method
     * @memberof VideoTranscriber
     */
    initializeElements() {
        // 表單元素
        this.form = document.getElementById('videoForm');
        this.videoUrlInput = document.getElementById('videoUrl');
        this.summaryLanguageSelect = document.getElementById('summaryLanguage');
        this.submitBtn = document.getElementById('submitBtn');

        // 進度元素
        this.progressSection = document.getElementById('progressSection');
        this.progressStatus = document.getElementById('progressStatus');
        this.progressFill = document.getElementById('progressFill');
        this.progressMessage = document.getElementById('progressMessage');

        // 錯誤提示
        this.errorAlert = document.getElementById('errorAlert');
        this.errorMessage = document.getElementById('errorMessage');

        // 結果元素
        this.resultsSection = document.getElementById('resultsSection');
        this.scriptContent = document.getElementById('scriptContent');
        this.translationContent = document.getElementById('translationContent');
        this.summaryContent = document.getElementById('summaryContent');
        this.downloadScriptBtn = document.getElementById('downloadScript');
        this.downloadTranslationBtn = document.getElementById('downloadTranslation');
        this.downloadSummaryBtn = document.getElementById('downloadSummary');
        this.translationTabBtn = document.getElementById('translationTabBtn');

        // 除錯：檢查元素是否正確初始化
        console.log('[DEBUG] 🔧 初始化檢查:', {
            translationTabBtn: !!this.translationTabBtn,
            elementId: this.translationTabBtn ? this.translationTabBtn.id : 'N/A'
        });

        // 標籤頁
        this.tabButtons = document.querySelectorAll('.tab-button');
        this.tabContents = document.querySelectorAll('.tab-content');

        // 語言切換按鈕
        this.langToggle = document.getElementById('langToggle');
        this.langText = document.getElementById('langText');
    }
    
    /**
     * 綁定事件監聽器
     * 
     * 為各種使用者互動元素添加事件監聽器，包括：
     * - 表單提交事件
     * - 標籤頁切換事件
     * - 下載按鈕點擊事件
     * - 語言切換事件
     * 
     * @method
     * @memberof VideoTranscriber
     */
    bindEvents() {
        // 表單提交
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.startTranscription();
        });

        // 標籤頁切換
        this.tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                this.switchTab(button.dataset.tab);
            });
        });

        // 下載按鈕
        if (this.downloadScriptBtn) {
            this.downloadScriptBtn.addEventListener('click', () => {
                this.downloadFile('script');
            });
        }

        if (this.downloadTranslationBtn) {
            this.downloadTranslationBtn.addEventListener('click', () => {
                this.downloadFile('translation');
            });
        }

        if (this.downloadSummaryBtn) {
            this.downloadSummaryBtn.addEventListener('click', () => {
                this.downloadFile('summary');
            });
        }

        // 語言切換按鈕
        this.langToggle.addEventListener('click', () => {
            this.toggleLanguage();
        });
    }

    /**
     * 初始化語言設定
     * 
     * 設定應用程式的預設語言為英文
     * 
     * @method
     * @memberof VideoTranscriber
     */
    initializeLanguage() {
        // 設定預設語言為英文
        this.switchLanguage('en');
    }

    /**
     * 切換語言
     * 
     * 在中文和英文之間切換，並更新整個使用者介面的語言顯示
     * 
     * @method
     * @memberof VideoTranscriber
     */
    toggleLanguage() {
        // 在中文和英文之間切換
        this.currentLanguage = this.currentLanguage === 'en' ? 'zh' : 'en';
        this.switchLanguage(this.currentLanguage);
    }

    /**
     * 切換到指定語言
     * 
     * 將整個應用程式的語言切換到指定的語言代碼，
     * 更新所有使用者介面元素的文字內容
     * 
     * @method
     * @memberof VideoTranscriber
     * @param {string} lang - 語言代碼 ('en' 或 'zh')
     */
    switchLanguage(lang) {
        this.currentLanguage = lang;

        // 更新語言按鈕文字 - 顯示目前語言
        this.langText.textContent = lang === 'en' ? 'English' : '繁體中文';

        // 更新頁面文字
        this.updatePageText();

        // 更新HTML lang屬性以改善無障礙性
        document.documentElement.lang = lang === 'zh' ? 'zh-TW' : 'en';

        // 更新頁面標題
        document.title = this.t('title');
    }

    /**
     * 翻譯函式
     * 
     * 根據目前語言設定獲取對應的翻譯文字
     * 
     * @method
     * @memberof VideoTranscriber
     * @param {string} key - 翻譯鍵值
     * @returns {string} 翻譯後的文字，如果找不到翻譯則返回原始鍵值
     */
    t(key) {
        return this.translations[this.currentLanguage][key] || key;
    }

    /**
     * 更新頁面文字內容
     * 
     * 遍歷所有標記了國際化屬性的DOM元素，
     * 根據目前語言設定更新其文字內容和placeholder
     * 
     * @method
     * @memberof VideoTranscriber
     */
    updatePageText() {
        // 更新所有帶有data-i18n屬性的元素的文字內容
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            element.textContent = this.t(key);
        });

        // 更新所有帶有data-i18n-placeholder屬性的元素的placeholder
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = this.t(key);
        });
    }
    
    async startTranscription() {
        // 立即禁用按鈕，防止重複點擊
        if (this.submitBtn.disabled) {
            return; // 如果按鈕已禁用，直接返回
        }

        const videoUrl = this.videoUrlInput.value.trim();
        const summaryLanguage = this.summaryLanguageSelect.value;

        if (!videoUrl) {
            this.showError(this.t('error_invalid_url'));
            return;
        }

        try {
            // 立即禁用按鈕和隱藏錯誤
            this.setLoading(true);
            this.hideError();
            this.hideResults();
            this.showProgress();

            // 發送轉錄請求
            const formData = new FormData();
            formData.append('url', videoUrl);
            formData.append('summary_language', summaryLanguage);

            const response = await fetch(`${this.apiBase}/process-video`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '請求失敗');
            }

            const data = await response.json();
            this.currentTaskId = data.task_id;

            console.log('[DEBUG] ✅ 任務已建立，Task ID:', this.currentTaskId);

            // 啟動智慧進度模擬
            this.initializeSmartProgress();
            this.updateProgress(5, this.t('preparing'), true);

            // 使用SSE即時接收狀態更新
            this.startSSE();

        } catch (error) {
            console.error('啟動轉錄失敗:', error);
            this.showError(this.t('error_processing_failed') + error.message);
            this.setLoading(false);
            this.hideProgress();
        }
    }
    
    startSSE() {
        if (!this.currentTaskId) return;

        console.log('[DEBUG] 🔄 啟動SSE連接，Task ID:', this.currentTaskId);

        // 建立EventSource連接
        this.eventSource = new EventSource(`${this.apiBase}/task-stream/${this.currentTaskId}`);

        this.eventSource.onmessage = (event) => {
            try {
                const task = JSON.parse(event.data);

                // 忽略心跳訊息
                if (task.type === 'heartbeat') {
                    console.log('[DEBUG] 💓 收到心跳');
                    return;
                }

                console.log('[DEBUG] 📊 收到SSE任務狀態:', {
                    status: task.status,
                    progress: task.progress,
                    message: task.message
                });

                // 更新進度 (標記為伺服器推送)
                console.log('[DEBUG] 📈 更新進度條:', `${task.progress}% - ${task.message}`);
                this.updateProgress(task.progress, task.message, true);

                if (task.status === 'completed') {
                    console.log('[DEBUG] ✅ 任務完成，顯示結果');
                    this.stopSmartProgress(); // 停止智慧進度模擬
                    this.stopSSE();
                    this.setLoading(false);
                    this.hideProgress();
                    this.showResults(task.script, task.summary, task.video_title, task.translation, task.detected_language, task.summary_language);
                } else if (task.status === 'error') {
                    console.log('[DEBUG] ❌ 任務失敗:', task.error);
                    this.stopSmartProgress(); // 停止智慧進度模擬
                    this.stopSSE();
                    this.setLoading(false);
                    this.hideProgress();
                    this.showError(task.error || '處理過程中發生錯誤');
                }
            } catch (error) {
                console.error('[DEBUG] 解析SSE資料失敗:', error);
            }
        };

        this.eventSource.onerror = async (error) => {
            console.error('[DEBUG] SSE連接錯誤:', error);
            this.stopSSE();

            // 兜底：查詢任務最終狀態，若已完成則直接渲染結果
            try {
                if (this.currentTaskId) {
                    const resp = await fetch(`${this.apiBase}/task-status/${this.currentTaskId}`);
                    if (resp.ok) {
                        const task = await resp.json();
                        if (task && task.status === 'completed') {
                            console.log('[DEBUG] 🔁 SSE中斷，但任務已完成，直接渲染結果');
                            this.stopSmartProgress();
                            this.setLoading(false);
                            this.hideProgress();
                            this.showResults(task.script, task.summary, task.video_title, task.translation, task.detected_language, task.summary_language);
                            return;
                        }
                    }
                }
            } catch (e) {
                console.error('[DEBUG] 兜底查詢任務狀態失敗:', e);
            }

            // 未完成則提示並保持頁面狀態（可由用戶重試或自動重連）
            this.showError(this.t('error_processing_failed') + 'SSE連線中斷');
            this.setLoading(false);
        };

        this.eventSource.onopen = () => {
            console.log('[DEBUG] 🔗 SSE連接已建立');
        };
    }

    /**
     * 停止 Server-Sent Events (SSE) 連線
     * 
     * 關閉與後端的即時通訊連線，清理資源
     * 
     * @method
     * @memberof VideoTranscriber
     */
    stopSSE() {
        if (this.eventSource) {
            console.log('[DEBUG] 🔌 關閉SSE連接');
            this.eventSource.close();
            this.eventSource = null;
        }
    }
    

    
    updateProgress(progress, message, fromServer = false) {
        console.log('[DEBUG] 🎯 updateProgress呼叫:', { progress, message, fromServer });

        if (fromServer) {
            // 伺服器推送的真實進度
            this.handleServerProgress(progress, message);
        } else {
            // 本地模擬進度
            this.updateProgressDisplay(progress, message);
        }
    }

    handleServerProgress(serverProgress, message) {
        console.log('[DEBUG] 📡 處理伺服器進度:', serverProgress);

        // 停止目前的模擬進度
        this.stopSmartProgress();

        // 更新伺服器進度記錄
        this.smartProgress.lastServerUpdate = serverProgress;
        this.smartProgress.current = serverProgress;

        // 立即顯示伺服器進度
        this.updateProgressDisplay(serverProgress, message);

        // 確定目前處理階段和預估目標
        this.updateProgressStage(serverProgress, message);

        // 重新啟動智慧進度模擬
        this.startSmartProgress();
    }

    /**
     * 更新進度階段和目標
     * 
     * 根據處理訊息判斷目前所處的處理階段，
     * 並設定相應的進度目標以提供更合理的進度模擬
     * 
     * @method
     * @memberof VideoTranscriber
     * @param {number} progress - 目前真實進度
     * @param {string} message - 處理狀態訊息
     */
    updateProgressStage(progress, message) {
        // 根據進度和訊息確定處理階段
        // 特別注意：解析資訊通常發生在長時間下載之前或期間，
        // 為了避免進度在下載階段停滯，將解析階段的目標設得更高，
        // 以覆蓋整個下載階段直到伺服器推送新的更新
        if (message.includes('解析') || message.includes('parsing')) {
            this.smartProgress.stage = 'parsing';
            this.smartProgress.target = 60;
        } else if (message.includes('下載') || message.includes('downloading')) {
            this.smartProgress.stage = 'downloading';
            this.smartProgress.target = 60;
        } else if (message.includes('轉錄') || message.includes('transcrib')) {
            this.smartProgress.stage = 'transcribing';
            this.smartProgress.target = 80;
        } else if (message.includes('最佳化') || message.includes('optimiz')) {
            this.smartProgress.stage = 'optimizing';
            this.smartProgress.target = 90;
        } else if (message.includes('摘要') || message.includes('summary')) {
            this.smartProgress.stage = 'summarizing';
            this.smartProgress.target = 95;
        } else if (message.includes('完成') || message.includes('completed')) {
            this.smartProgress.stage = 'completed';
            this.smartProgress.target = 100;
        }

        // 如果目前進度超過預設目標，動態調整目標
        if (progress >= this.smartProgress.target) {
            this.smartProgress.target = Math.min(progress + 10, 100);
        }

        console.log('[DEBUG] 🎯 階段更新:', {
            stage: this.smartProgress.stage,
            target: this.smartProgress.target,
            current: progress
        });
    }

    /**
     * 初始化智慧進度系統
     * 
     * 設定智慧進度模擬的初始狀態和參數，
     * 為新的處理任務做準備
     * 
     * @method
     * @memberof VideoTranscriber
     */
    initializeSmartProgress() {
        // 重設所有智慧進度狀態參數
        this.smartProgress.enabled = false;
        this.smartProgress.current = 0;
        this.smartProgress.target = 15;
        this.smartProgress.lastServerUpdate = 0;
        this.smartProgress.startTime = Date.now();
        this.smartProgress.stage = 'preparing';

        console.log('[DEBUG] 🔧 智慧進度模擬已初始化');
    }

    /**
     * 啟動智慧進度模擬
     * 
     * 開始以定時器方式模擬進度增長，在等待伺服器更新期間
     * 為使用者提供流暢的進度顯示體驗
     * 
     * @method
     * @memberof VideoTranscriber
     */
    startSmartProgress() {
        // 清理現有的定時器（如果存在）
        if (this.smartProgress.interval) {
            clearInterval(this.smartProgress.interval);
        }

        this.smartProgress.enabled = true;
        this.smartProgress.startTime = this.smartProgress.startTime || Date.now();

        // 每500毫秒更新一次模擬進度
        this.smartProgress.interval = setInterval(() => {
            this.simulateProgress();
        }, 500);

        console.log('[DEBUG] 🚀 智慧進度模擬已啟動');
    }

    /**
     * 停止智慧進度模擬
     * 
     * 清理定時器並停止進度模擬，通常在接收到伺服器
     * 真實進度更新或任務完成時呼叫
     * 
     * @method
     * @memberof VideoTranscriber
     */
    stopSmartProgress() {
        if (this.smartProgress.interval) {
            clearInterval(this.smartProgress.interval);
            this.smartProgress.interval = null;
        }
        this.smartProgress.enabled = false;
        console.log('[DEBUG] ⏹️ 智慧進度模擬已停止');
    }
    
    /**
     * 模擬進度增長
     * 
     * 根據目前階段和時間狀態計算進度增量，
     * 逐步將顯示進度推進到目標值
     * 
     * @method
     * @memberof VideoTranscriber
     * @private
     */
    simulateProgress() {
        if (!this.smartProgress.enabled) return;

        const current = this.smartProgress.current;
        const target = this.smartProgress.target;

        // 如果已經達到目標，暫停模擬
        if (current >= target) return;

        // 計算進度增量（基於階段的不同速度）
        let increment = this.calculateProgressIncrement();

        // 確保不超過目標進度
        const newProgress = Math.min(current + increment, target);

        if (newProgress > current) {
            this.smartProgress.current = newProgress;
            this.updateProgressDisplay(newProgress, this.getCurrentStageMessage());
        }
    }

    /**
     * 計算進度增量
     * 
     * 根據目前處理階段、經過時間和距離目標的距離
     * 計算合理的進度增量，以提供自然的進度變化
     * 
     * @method
     * @memberof VideoTranscriber
     * @returns {number} 進度增量值
     * @private
     */
    calculateProgressIncrement() {
        const elapsedTime = (Date.now() - this.smartProgress.startTime) / 1000; // 秒

        // 基於不同階段的預估速度
        const stageConfig = {
            'parsing': { speed: 0.3, maxTime: 30 },      // 解析階段：30秒內到25%
            'downloading': { speed: 0.2, maxTime: 120 }, // 下載階段：2分鐘內到60%
            'transcribing': { speed: 0.15, maxTime: 180 }, // 轉錄階段：3分鐘內到80%
            'optimizing': { speed: 0.25, maxTime: 60 },  // 最佳化階段：1分鐘內到90%
            'summarizing': { speed: 0.3, maxTime: 30 }   // 摘要階段：30秒內到95%
        };

        const config = stageConfig[this.smartProgress.stage] || { speed: 0.2, maxTime: 60 };

        // 基礎增量：每500ms增加的百分比
        let baseIncrement = config.speed;

        // 時間因子：如果時間過長，加快進度
        if (elapsedTime > config.maxTime) {
            baseIncrement *= 1.5;
        }

        // 距離因子：距離目標越近，速度越慢
        const remaining = this.smartProgress.target - this.smartProgress.current;
        if (remaining < 5) {
            baseIncrement *= 0.3; // 接近目標時放慢
        }

        return baseIncrement;
    }

    /**
     * 獲取目前階段的訊息
     * 
     * 根據目前處理階段返回相應的本地化訊息文字
     * 
     * @method
     * @memberof VideoTranscriber
     * @returns {string} 階段描述訊息
     * @private
     */
    getCurrentStageMessage() {
        const stageMessages = {
            'parsing': this.t('parsing_video'),
            'downloading': this.t('downloading_video'),
            'transcribing': this.t('transcribing_audio'),
            'optimizing': this.t('optimizing_transcript'),
            'summarizing': this.t('generating_summary'),
            'completed': this.t('completed')
        };

        return stageMessages[this.smartProgress.stage] || this.t('processing');
    }

    /**
     * 更新進度顯示介面
     * 
     * 實際更新UI中的進度條和狀態訊息，
     * 包括百分比數字、進度條寬度和訊息文字
     * 
     * @method
     * @memberof VideoTranscriber
     * @param {number} progress - 進度值 (0-100)
     * @param {string} message - 狀態訊息
     * @private
     */
    updateProgressDisplay(progress, message) {
        // 實際更新UI顯示
        const roundedProgress = Math.round(progress * 10) / 10; // 保留1位小數
        this.progressStatus.textContent = `${roundedProgress}%`;
        this.progressFill.style.width = `${roundedProgress}%`;
        console.log('[DEBUG] 📏 進度條已更新:', this.progressFill.style.width);

        // 翻譯常見的進度訊息
        let translatedMessage = message;
        if (message.includes('下載影片') || message.includes('downloading') || message.includes('Downloading')) {
            translatedMessage = this.t('downloading_video');
        } else if (message.includes('解析影片') || message.includes('parsing') || message.includes('Parsing')) {
            translatedMessage = this.t('parsing_video');
        } else if (message.includes('轉錄') || message.includes('transcrib') || message.includes('Transcrib')) {
            translatedMessage = this.t('transcribing_audio');
        } else if (message.includes('最佳化轉錄') || message.includes('optimizing') || message.includes('Optimizing')) {
            translatedMessage = this.t('optimizing_transcript');
        } else if (message.includes('摘要') || message.includes('summary') || message.includes('Summary')) {
            translatedMessage = this.t('generating_summary');
        } else if (message.includes('完成') || message.includes('complet') || message.includes('Complet')) {
            translatedMessage = this.t('completed');
        } else if (message.includes('準備') || message.includes('prepar') || message.includes('Prepar')) {
            translatedMessage = this.t('preparing');
        }

        this.progressMessage.textContent = translatedMessage;
    }
    
    /**
     * 顯示進度區域
     * 
     * 顯示進度條和相關狀態資訊的UI區域
     * 
     * @method
     * @memberof VideoTranscriber
     */
    showProgress() {
        this.progressSection.style.display = 'block';
    }
    
    /**
     * 隱藏進度區域
     * 
     * 隱藏進度條和相關狀態資訊的UI區域
     * 
     * @method
     * @memberof VideoTranscriber
     */
    hideProgress() {
        this.progressSection.style.display = 'none';
    }
    
    /**
     * 顯示處理結果
     * 
     * 在UI中呈現影片轉錄、翻譯和摘要結果，
     * 並根據語言情況決定是否顯示翻譯標籤頁
     * 
     * @method
     * @memberof VideoTranscriber
     * @param {string} script - 轉錄文字內容 (Markdown 格式)
     * @param {string} summary - 摘要內容 (Markdown 格式)
     * @param {string|null} [videoTitle=null] - 影片標題
     * @param {string|null} [translation=null] - 翻譯內容 (Markdown 格式)
     * @param {string|null} [detectedLanguage=null] - 偵測到的影片語言
     * @param {string|null} [summaryLanguage=null] - 摘要語言
     */
    showResults(script, summary, videoTitle = null, translation = null, detectedLanguage = null, summaryLanguage = null) {

        // 除錯日誌：檢查翻譯相關參數
        console.log('[DEBUG] 🔍 showResults參數:', {
            hasTranslation: !!translation,
            translationLength: translation ? translation.length : 0,
            detectedLanguage,
            summaryLanguage,
            languagesDifferent: detectedLanguage !== summaryLanguage
        });

        // 渲染markdown內容，確保參數不為null
        const safeScript = script || '';
        const safeSummary = summary || '';
        const safeTranslation = translation || '';

        this.scriptContent.innerHTML = safeScript ? marked.parse(safeScript) : '';
        this.summaryContent.innerHTML = safeSummary ? marked.parse(safeSummary) : '';

        // 處理翻譯
        const shouldShowTranslation = safeTranslation && detectedLanguage && summaryLanguage && detectedLanguage !== summaryLanguage;

        console.log('[DEBUG] 🌐 翻譯顯示判斷:', {
            safeTranslation: !!safeTranslation,
            detectedLanguage: detectedLanguage,
            summaryLanguage: summaryLanguage,
            languagesDifferent: detectedLanguage !== summaryLanguage,
            shouldShowTranslation: shouldShowTranslation,
            translationTabBtn: !!this.translationTabBtn,
            downloadTranslationBtn: !!this.downloadTranslationBtn
        });

        // 除錯：檢查DOM元素（多種方式）
        const debugBtn1 = document.getElementById('translationTabBtn');
        const debugBtn2 = document.querySelector('#translationTabBtn');
        const debugBtn3 = document.querySelector('[data-tab="translation"]');

        console.log('[DEBUG] 🔍 DOM檢查:', {
            getElementById: !!debugBtn1,
            querySelector_id: !!debugBtn2,
            querySelector_attr: !!debugBtn3,
            currentDisplay: debugBtn1 ? debugBtn1.style.display : 'N/A',
            computedStyle: debugBtn1 ? window.getComputedStyle(debugBtn1).display : 'N/A'
        });

        // 使用備用方法獲取元素
        const actualBtn = debugBtn1 || debugBtn2 || debugBtn3;
        if (actualBtn && !this.translationTabBtn) {
            this.translationTabBtn = actualBtn;
            console.log('[DEBUG] 🔄 使用備用方法找到翻譯按鈕');
        }

        if (shouldShowTranslation) {
            console.log('[DEBUG] ✅ 顯示翻譯標籤頁');
            // 顯示翻譯標籤頁和按鈕
            if (this.translationTabBtn) {
                this.translationTabBtn.style.display = 'inline-block';
                this.translationTabBtn.style.visibility = 'visible';
                console.log('[DEBUG] 🎯 翻譯按鈕樣式已設定:', this.translationTabBtn.style.display);
            }
            if (this.downloadTranslationBtn) {
                this.downloadTranslationBtn.style.display = 'inline-flex';
            }
            if (this.translationContent) {
                this.translationContent.innerHTML = marked.parse(safeTranslation);
            }
        } else {
            console.log('[DEBUG] ❌ 隱藏翻譯標籤頁');
            // 隱藏翻譯標籤頁和按鈕
            if (this.translationTabBtn) {
                this.translationTabBtn.style.display = 'none';
            }
            if (this.downloadTranslationBtn) {
                this.downloadTranslationBtn.style.display = 'none';
            }
        }

        // 顯示結果區域
        this.resultsSection.style.display = 'block';

        // 滾動到結果區域
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });

        // 高亮程式碼
        if (window.Prism) {
            Prism.highlightAll();
        }
    }
    
    /**
     * 隱藏結果區域
     * 
     * 隱藏轉錄結果顯示區域
     * 
     * @method
     * @memberof VideoTranscriber
     */
    hideResults() {
        this.resultsSection.style.display = 'none';
    }
    
    /**
     * 切換結果標籤頁
     * 
     * 在轉錄、翻譯和摘要之間切換顯示內容
     * 
     * @method
     * @memberof VideoTranscriber
     * @param {string} tabName - 標籤頁名稱 ('script', 'translation', 'summary')
     */
    switchTab(tabName) {
        // 移除所有活動狀態
        this.tabButtons.forEach(btn => btn.classList.remove('active'));
        this.tabContents.forEach(content => content.classList.remove('active'));

        // 啟用選中的標籤頁
        const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
        const activeContent = document.getElementById(`${tabName}Tab`);

        if (activeButton && activeContent) {
            activeButton.classList.add('active');
            activeContent.classList.add('active');
        }
    }

    /**
     * 下載檔案
     * 
     * 根據檔案類型下載相應的轉錄、翻譯或摘要檔案
     * 
     * @async
     * @method
     * @memberof VideoTranscriber
     * @param {string} fileType - 檔案類型 ('script', 'translation', 'summary')
     * @throws {Error} 當檔案不存在或下載失敗時拋出錯誤
     */
    async downloadFile(fileType) {
        if (!this.currentTaskId) {
            this.showError(this.t('error_no_file_to_download'));
            return;
        }

        try {
            // 首先獲取任務狀態，獲得實際檔案名
            const taskResponse = await fetch(`${this.apiBase}/task-status/${this.currentTaskId}`);
            if (!taskResponse.ok) {
                throw new Error('獲取任務狀態失敗');
            }

            const taskData = await taskResponse.json();
            let filename;

            // 根據檔案類型獲取對應的檔案名
            switch(fileType) {
                case 'script':
                    if (taskData.script_path) {
                        filename = taskData.script_path.split('/').pop(); // 獲取檔案名部分
                    } else {
                        filename = `transcript_${taskData.safe_title || 'untitled'}_${taskData.short_id || 'unknown'}.md`;
                    }
                    break;
                case 'summary':
                    if (taskData.summary_path) {
                        filename = taskData.summary_path.split('/').pop();
                    } else {
                        filename = `summary_${taskData.safe_title || 'untitled'}_${taskData.short_id || 'unknown'}.md`;
                    }
                    break;
                case 'translation':
                    if (taskData.translation_path) {
                        filename = taskData.translation_path.split('/').pop();
                    } else if (taskData.translation_filename) {
                        filename = taskData.translation_filename;
                    } else {
                        filename = `translation_${taskData.safe_title || 'untitled'}_${taskData.short_id || 'unknown'}.md`;
                    }
                    break;
                default:
                    throw new Error('未知的檔案類型');
            }

            // 使用簡單直接的下載方式
            const encodedFilename = encodeURIComponent(filename);
            const link = document.createElement('a');
            link.href = `${this.apiBase}/download/${encodedFilename}`;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

        } catch (error) {
            console.error('下載檔案失敗:', error);
            this.showError(this.t('error_download_failed') + error.message);
        }
    }

    /**
     * 設定載入狀態
     * 
     * 控制提交按鈕的啟用/禁用狀態和顯示文字，
     * 防止用戶在處理過程中重複提交
     * 
     * @method
     * @memberof VideoTranscriber
     * @param {boolean} loading - 是否處於載入狀態
     */
    setLoading(loading) {
        this.submitBtn.disabled = loading;

        if (loading) {
            this.submitBtn.innerHTML = `<div class="loading-spinner"></div> ${this.t('processing')}`;
        } else {
            this.submitBtn.innerHTML = `<i class="fas fa-play"></i> ${this.t('start_transcription')}`;
        }
    }

    /**
     * 顯示錯誤訊息
     * 
     * 在UI中顯示錯誤提示，並自動滾動到錯誤位置，
     * 5秒後自動隱藏
     * 
     * @method
     * @memberof VideoTranscriber
     * @param {string} message - 錯誤訊息內容
     */
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorAlert.style.display = 'block';

        // 滾動到錯誤提示位置以吸引使用者注意
        this.errorAlert.scrollIntoView({ behavior: 'smooth' });

        // 5秒後自動隱藏錯誤提示
        setTimeout(() => {
            this.hideError();
        }, 5000);
    }

    /**
     * 隱藏錯誤訊息
     * 
     * 隱藏錯誤提示區域
     * 
     * @method
     * @memberof VideoTranscriber
     */
    hideError() {
        this.errorAlert.style.display = 'none';
    }
}

/**
 * 應用程式初始化
 * 
 * 當DOM內容加載完成後執行，初始化VideoTranscriber實例
 * 並設定URL輸入框的互動提示效果
 */
document.addEventListener('DOMContentLoaded', () => {
    // 初始化影片轉錄器實例並將其設為全域變數
    window.transcriber = new VideoTranscriber();

    // 為URL輸入框添加動態範例提示效果
    const urlInput = document.getElementById('videoUrl');
    
    // 當輸入框獲得焦點時顯示範例提示
    urlInput.addEventListener('focus', () => {
        if (!urlInput.value) {
            urlInput.placeholder = '例如：https://www.youtube.com/watch?v=... 或 https://www.bilibili.com/video/...';
        }
    });

    // 當輸入框失去焦點時恢復預設提示
    urlInput.addEventListener('blur', () => {
        if (!urlInput.value) {
            urlInput.placeholder = '請輸入YouTube、Bilibili等平台的影片連結...';
        }
    });
});

/**
 * 頁面卸載清理
 * 
 * 當使用者關閉或重新整理頁面時，清理SSE連線和其他資源，
 * 防止記憶體洩漏和網路連線殘留
 */
window.addEventListener('beforeunload', () => {
    if (window.transcriber && window.transcriber.eventSource) {
        window.transcriber.stopSSE();
    }
});