class VideoTranscriber {
    constructor() {
        this.currentTaskId = null;
        this.eventSource = null;
        this.apiBase = 'http://localhost:8000/api';
        this.currentLanguage = 'en'; // 默认英文
        
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
                transcription_results: "Transcription Results",
                download_transcript: "Download Transcript",
                download_summary: "Download Summary",
                transcript_text: "Transcript Text",
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
                title: "AI视频转录器",
                subtitle: "支持YouTube、Tiktok、Bilibili等平台的视频自动转录和智能摘要",
                video_url: "视频链接",
                video_url_placeholder: "请输入YouTube、Tiktok、Bilibili等平台的视频链接...",
                summary_language: "摘要语言",
                start_transcription: "开始转录",
                processing_progress: "处理进度",
                preparing: "准备中...",
                transcription_results: "转录结果",
                download_transcript: "下载转录",
                download_summary: "下载摘要",
                transcript_text: "转录文本",
                intelligent_summary: "智能摘要",
                footer_text: "由AI驱动，支持多平台视频转录",
                processing: "处理中...",
                downloading_video: "正在下载视频...",
                parsing_video: "正在解析视频信息...",
                transcribing_audio: "正在转录音频...",
                optimizing_transcript: "正在优化转录文本...",
                generating_summary: "正在生成摘要...",
                completed: "处理完成！",
                error_invalid_url: "请输入有效的视频链接",
                error_processing_failed: "处理失败: ",
                error_task_not_found: "任务不存在",
                error_task_not_completed: "任务尚未完成",
                error_invalid_file_type: "无效的文件类型",
                error_file_not_found: "文件不存在",
                error_download_failed: "下载文件失败: ",
                error_no_file_to_download: "没有可下载的文件"
            }
        };
        
        this.initializeElements();
        this.bindEvents();
        this.initializeLanguage();
    }
    
    initializeElements() {
        // 表单元素
        this.form = document.getElementById('videoForm');
        this.videoUrlInput = document.getElementById('videoUrl');
        this.summaryLanguageSelect = document.getElementById('summaryLanguage');
        this.submitBtn = document.getElementById('submitBtn');
        
        // 进度元素
        this.progressSection = document.getElementById('progressSection');
        this.progressStatus = document.getElementById('progressStatus');
        this.progressFill = document.getElementById('progressFill');
        this.progressMessage = document.getElementById('progressMessage');
        
        // 错误提示
        this.errorAlert = document.getElementById('errorAlert');
        this.errorMessage = document.getElementById('errorMessage');
        
        // 结果元素
        this.resultsSection = document.getElementById('resultsSection');
        this.scriptContent = document.getElementById('scriptContent');
        this.summaryContent = document.getElementById('summaryContent');
        this.downloadScriptBtn = document.getElementById('downloadScript');
        this.downloadSummaryBtn = document.getElementById('downloadSummary');
        
        // 标签页
        this.tabButtons = document.querySelectorAll('.tab-button');
        this.tabContents = document.querySelectorAll('.tab-content');
        
        // 语言切换按钮
        this.langToggle = document.getElementById('langToggle');
        this.langText = document.getElementById('langText');
    }
    
    bindEvents() {
        // 表单提交
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.startTranscription();
        });
        
        // 标签页切换
        this.tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                this.switchTab(button.dataset.tab);
            });
        });
        
        // 下载按钮
        this.downloadScriptBtn.addEventListener('click', () => {
            this.downloadFile('script');
        });
        
        this.downloadSummaryBtn.addEventListener('click', () => {
            this.downloadFile('summary');
        });
        
        // 语言切换按钮
        this.langToggle.addEventListener('click', () => {
            this.toggleLanguage();
        });
    }
    
    initializeLanguage() {
        // 设置默认语言为英文
        this.switchLanguage('en');
    }
    
    toggleLanguage() {
        // 切换语言
        this.currentLanguage = this.currentLanguage === 'en' ? 'zh' : 'en';
        this.switchLanguage(this.currentLanguage);
    }
    
    switchLanguage(lang) {
        this.currentLanguage = lang;
        
        // 更新语言按钮文本 - 显示当前语言
        this.langText.textContent = lang === 'en' ? 'English' : '中文';
        
        // 更新页面文本
        this.updatePageText();
        
        // 更新HTML lang属性
        document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
        
        // 更新页面标题
        document.title = this.t('title');
    }
    
    t(key) {
        return this.translations[this.currentLanguage][key] || key;
    }
    
    updatePageText() {
        // 更新所有带有data-i18n属性的元素
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            element.textContent = this.t(key);
        });
        
        // 更新placeholder
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = this.t(key);
        });
    }
    
    async startTranscription() {
        // 立即禁用按钮，防止重复点击
        if (this.submitBtn.disabled) {
            return; // 如果按钮已禁用，直接返回
        }
        
        const videoUrl = this.videoUrlInput.value.trim();
        const summaryLanguage = this.summaryLanguageSelect.value;
        
        if (!videoUrl) {
            this.showError(this.t('error_invalid_url'));
            return;
        }
        
        try {
            // 立即禁用按钮和隐藏错误
            this.setLoading(true);
            this.hideError();
            this.hideResults();
            this.showProgress();
            
            // 发送转录请求
            const formData = new FormData();
            formData.append('url', videoUrl);
            formData.append('summary_language', summaryLanguage);
            
            const response = await fetch(`${this.apiBase}/process-video`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '请求失败');
            }
            
            const data = await response.json();
            this.currentTaskId = data.task_id;
            
            console.log('[DEBUG] ✅ 任务已创建，Task ID:', this.currentTaskId);
            
            // 立即更新一次进度显示
            this.updateProgress(5, this.t('preparing'));
            
            // 使用SSE实时接收状态更新
            this.startSSE();
            
        } catch (error) {
            console.error('启动转录失败:', error);
            this.showError(this.t('error_processing_failed') + error.message);
            this.setLoading(false);
            this.hideProgress();
        }
    }
    
    startSSE() {
        if (!this.currentTaskId) return;
        
        console.log('[DEBUG] 🔄 启动SSE连接，Task ID:', this.currentTaskId);
        
        // 创建EventSource连接
        this.eventSource = new EventSource(`${this.apiBase}/task-stream/${this.currentTaskId}`);
        
        this.eventSource.onmessage = (event) => {
            try {
                const task = JSON.parse(event.data);
                
                // 忽略心跳消息
                if (task.type === 'heartbeat') {
                    console.log('[DEBUG] 💓 收到心跳');
                    return;
                }
                
                console.log('[DEBUG] 📊 收到SSE任务状态:', {
                    status: task.status,
                    progress: task.progress,
                    message: task.message
                });
                
                // 更新进度
                console.log('[DEBUG] 📈 更新进度条:', `${task.progress}% - ${task.message}`);
                this.updateProgress(task.progress, task.message);
                
                if (task.status === 'completed') {
                    console.log('[DEBUG] ✅ 任务完成，显示结果');
                    this.stopSSE();
                    this.setLoading(false);
                    this.hideProgress();
                    this.showResults(task.script, task.summary, task.video_title);
                } else if (task.status === 'error') {
                    console.log('[DEBUG] ❌ 任务失败:', task.error);
                    this.stopSSE();
                    this.setLoading(false);
                    this.hideProgress();
                    this.showError(task.error || '处理过程中发生错误');
                }
            } catch (error) {
                console.error('[DEBUG] 解析SSE数据失败:', error);
            }
        };
        
        this.eventSource.onerror = (error) => {
            console.error('[DEBUG] SSE连接错误:', error);
            this.stopSSE();
            this.showError(this.t('error_processing_failed') + 'SSE连接断开');
            this.setLoading(false);
        };
        
        this.eventSource.onopen = () => {
            console.log('[DEBUG] 🔗 SSE连接已建立');
        };
    }
    
    stopSSE() {
        if (this.eventSource) {
            console.log('[DEBUG] 🔌 关闭SSE连接');
            this.eventSource.close();
            this.eventSource = null;
        }
    }
    

    
    updateProgress(progress, message) {
        console.log('[DEBUG] 🎯 updateProgress调用:', { progress, message });
        this.progressStatus.textContent = `${progress}%`;
        this.progressFill.style.width = `${progress}%`;
        console.log('[DEBUG] 📏 进度条已更新:', this.progressFill.style.width);
        
        // 翻译常见的进度消息
        let translatedMessage = message;
        if (message.includes('下载视频') || message.includes('downloading') || message.includes('Downloading')) {
            translatedMessage = this.t('downloading_video');
        } else if (message.includes('解析视频') || message.includes('parsing') || message.includes('Parsing')) {
            translatedMessage = this.t('parsing_video');
        } else if (message.includes('转录') || message.includes('transcrib') || message.includes('Transcrib')) {
            translatedMessage = this.t('transcribing_audio');
        } else if (message.includes('优化转录') || message.includes('optimizing') || message.includes('Optimizing')) {
            translatedMessage = this.t('optimizing_transcript');
        } else if (message.includes('摘要') || message.includes('summary') || message.includes('Summary')) {
            translatedMessage = this.t('generating_summary');
        } else if (message.includes('完成') || message.includes('complet') || message.includes('Complet')) {
            translatedMessage = this.t('completed');
        } else if (message.includes('准备') || message.includes('prepar') || message.includes('Prepar')) {
            translatedMessage = this.t('preparing');
        }
        
        this.progressMessage.textContent = translatedMessage;
    }
    
    showProgress() {
        this.progressSection.style.display = 'block';
    }
    
    hideProgress() {
        this.progressSection.style.display = 'none';
    }
    
    showResults(script, summary, videoTitle = null) {
        // 不再显示重复的标题，因为内容中已经包含标题
        
        // 渲染markdown内容
        this.scriptContent.innerHTML = marked.parse(script || '');
        this.summaryContent.innerHTML = marked.parse(summary || '');
        
        // 显示结果区域
        this.resultsSection.style.display = 'block';
        
        // 滚动到结果区域
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
        
        // 高亮代码
        if (window.Prism) {
            Prism.highlightAll();
        }
    }
    
    hideResults() {
        this.resultsSection.style.display = 'none';
    }
    
    switchTab(tabName) {
        // 移除所有活动状态
        this.tabButtons.forEach(btn => btn.classList.remove('active'));
        this.tabContents.forEach(content => content.classList.remove('active'));
        
        // 激活选中的标签页
        const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
        const activeContent = document.getElementById(`${tabName}Tab`);
        
        if (activeButton && activeContent) {
            activeButton.classList.add('active');
            activeContent.classList.add('active');
        }
    }
    
    async downloadFile(fileType) {
        if (!this.currentTaskId) {
            this.showError(this.t('error_no_file_to_download'));
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/download/${this.currentTaskId}/${fileType}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '下载失败');
            }
            
            // 获取文件名
            const contentDisposition = response.headers.get('content-disposition');
            let filename = `${fileType}.md`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }
            
            // 下载文件
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
        } catch (error) {
            console.error('下载文件失败:', error);
            this.showError(this.t('error_download_failed') + error.message);
        }
    }
    
    setLoading(loading) {
        this.submitBtn.disabled = loading;
        
        if (loading) {
            this.submitBtn.innerHTML = `<div class="loading-spinner"></div> ${this.t('processing')}`;
        } else {
            this.submitBtn.innerHTML = `<i class="fas fa-play"></i> ${this.t('start_transcription')}`;
        }
    }
    
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorAlert.style.display = 'block';
        
        // 滚动到错误提示
        this.errorAlert.scrollIntoView({ behavior: 'smooth' });
        
        // 5秒后自动隐藏错误提示
        setTimeout(() => {
            this.hideError();
        }, 5000);
    }
    
    hideError() {
        this.errorAlert.style.display = 'none';
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.transcriber = new VideoTranscriber();
    
    // 添加一些示例链接提示
    const urlInput = document.getElementById('videoUrl');
    urlInput.addEventListener('focus', () => {
        if (!urlInput.value) {
            urlInput.placeholder = '例如: https://www.youtube.com/watch?v=... 或 https://www.bilibili.com/video/...';
        }
    });
    
    urlInput.addEventListener('blur', () => {
        if (!urlInput.value) {
            urlInput.placeholder = '请输入YouTube、Bilibili等平台的视频链接...';
        }
    });
});

// 处理页面刷新时的清理工作
window.addEventListener('beforeunload', () => {
    if (window.transcriber && window.transcriber.eventSource) {
        window.transcriber.stopSSE();
    }
});
