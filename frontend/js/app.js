// 统一错误处理器
class ErrorHandler {
    constructor(app) {
        this.app = app;
        this.retryQueue = new Map();
    }

    // 处理API错误
    async handleApiError(error, operation, context = {}) {
        console.error(`API错误 [${operation}]:`, error);

        const errorInfo = this.parseError(error);

        // 检查是否应该重试
        if (this.shouldRetry(errorInfo, context.retryCount || 0)) {
            return await this.retryOperation(operation, context);
        }

        // 显示错误信息
        this.displayError(errorInfo, operation);
        return false;
    }

    // 处理HTTP响应状态码
    async handleHTTPResponse(response) {
        if (response.ok) {
            return response;
        }

        let errorMessage = '';
        let errorDetails = '';

        // 检测CORS错误的特殊处理
        if (response.type === 'opaque' || response.type === 'opaqueredirect') {
            const error = new Error(this.app.t('errors.cors_error', 'CORS 错误，请检查API配置'));
            error.status = response.status;
            error.details = this.app.t('errors.cors_details', '可能原因：1) API端点不正确 2) 缺少CORS配置 3) API Key错误');
            throw error;
        }

        switch (response.status) {
            case 400:
                errorMessage = this.app.t('errors.bad_request', '请求参数错误');
                try {
                    const errorData = await response.json();
                    errorDetails = errorData.message || '';
                } catch (e) {
                    // 忽略解析错误
                }
                break;
            case 401:
                errorMessage = this.app.t('errors.unauthorized', 'API Key 无效或已过期');
                break;
            case 403:
                errorMessage = this.app.t('errors.forbidden', '访问被拒绝，请检查权限');
                break;
            case 404:
                errorMessage = this.app.t('errors.not_found', 'API端点不存在');
                errorDetails = this.app.t('errors.check_endpoint', '请检查API Gateway URL是否正确');
                break;
            case 408:
                errorMessage = this.app.t('errors.timeout_error', '请求超时');
                break;
            case 429:
                errorMessage = this.app.t('errors.rate_limit', '请求过于频繁，请稍后重试');
                break;
            case 500:
                errorMessage = this.app.t('errors.server_error', '服务器内部错误');
                break;
            case 502:
            case 503:
            case 504:
                errorMessage = this.app.t('errors.service_unavailable', '服务暂时不可用');
                break;
            default:
                errorMessage = this.app.t('errors.api_error', 'API 错误') + ': ' + response.status;
        }

        const error = new Error(errorMessage + (errorDetails ? ' - ' + errorDetails : ''));
        error.status = response.status;
        error.response = response;
        throw error;
    }

    // 错误分类方法
    classifyError(error) {
        // 如果请求被取消
        if (error.name === 'AbortError') {
            const classifiedError = new Error(this.app.t('errors.request_cancelled', '请求已取消'));
            classifiedError.isAborted = true;
            return classifiedError;
        }

        // 网络错误
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            const networkError = new Error(this.app.t('errors.network_error', '网络连接失败，请检查网络或API端点'));
            networkError.name = 'NetworkError';
            return networkError;
        }

        // 超时错误
        if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
            const timeoutError = new Error(this.app.t('errors.timeout_error', '请求超时，请稍后重试'));
            timeoutError.name = 'TimeoutError';
            return timeoutError;
        }

        // 如果已经是分类过的错误，直接返回
        if (error.status) {
            return error;
        }

        // 其他未分类错误
        return new Error(this.app.t('errors.unknown_error', '未知错误') + ': ' + error.message);
    }

    // 解析错误类型和信息
    parseError(error) {
        const info = {
            type: 'unknown',
            message: error.message || '未知错误',
            retryable: false,
            severity: 'medium'
        };

        if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
            info.type = 'timeout';
            info.retryable = true;
            info.message = this.app.t('errors.timeout_error', '请求超时');
        } else if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
            info.type = 'network';
            info.retryable = true;
            info.message = this.app.t('errors.network_error', '网络连接错误');
        } else if (error.message.includes('API 错误: 5')) {
            info.type = 'server';
            info.retryable = true;
            info.severity = 'high';
        } else if (error.message.includes('API 错误: 4')) {
            info.type = 'client';
            info.retryable = false;
            info.severity = 'high';
        }

        return info;
    }

    // 判断是否应该重试
    shouldRetry(errorInfo, retryCount) {
        if (!errorInfo.retryable) return false;

        const maxRetries = window.configManager.get('retry.maxAttempts', 3);
        const retryableErrors = window.configManager.get('retry.retryableErrors', []);

        // 基于HTTP状态码的重试判断
        if (errorInfo.status) {
            const retryableStatusCodes = window.configManager.get('retry.retryableStatusCodes', [408, 429, 500, 502, 503, 504]);
            return retryCount < maxRetries && retryableStatusCodes.includes(errorInfo.status);
        }

        return retryCount < maxRetries &&
               retryableErrors.some(pattern => errorInfo.message.includes(pattern));
    }

    // 重试操作
    async retryOperation(operation, context) {
        const retryCount = (context.retryCount || 0) + 1;
        const delay = this.calculateRetryDelay(retryCount);

        context.retryCount = retryCount;

        // 显示重试信息
        this.app.showError(
            `${context.originalError || '操作失败'}。正在重试... (${retryCount}/${window.configManager.get('retry.maxAttempts', 3)})`
        );

        // 延迟重试
        await new Promise(resolve => setTimeout(resolve, delay));

        return new Promise((resolve, reject) => {
            this.retryQueue.set(operation, { resolve, reject, context });
        });
    }

    // 计算重试延迟
    calculateRetryDelay(retryCount) {
        const baseDelay = window.configManager.get('retry.delayMs', 1000);
        const multiplier = window.configManager.get('retry.backoffMultiplier', 2);
        return baseDelay * Math.pow(multiplier, retryCount - 1);
    }

    // 显示错误信息
    displayError(errorInfo, operation) {
        let message = errorInfo.message;

        if (operation) {
            message = `${operation}失败: ${message}`;
        }

        // 根据严重程度选择不同的显示方式
        if (errorInfo.severity === 'high') {
            this.app.showError(message);
            this.showErrorNotification(message, 'danger');
        } else {
            this.app.showError(message);
        }
    }

    // 显示错误通知
    showErrorNotification(message, type = 'danger') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} position-fixed`;
        notification.style.cssText = `
            top: 80px;
            right: 20px;
            z-index: 1060;
            min-width: 300px;
            animation: slideInRight 0.3s ease;
        `;

        const icon = type === 'danger' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill';
        notification.innerHTML = `
            <i class="${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close ms-auto" aria-label="Close"></button>
        `;

        document.body.appendChild(notification);

        // 自动移除
        const duration = window.configManager.get('ui.notificationDuration', 3000);
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }
        }, duration);

        // 手动关闭
        notification.querySelector('.btn-close').addEventListener('click', () => {
            notification.remove();
        });
    }

    // 清理重试队列
    clearRetryQueue() {
        this.retryQueue.clear();
    }
}

// 请求缓存管理器
class RequestCache {
    constructor(ttl = 300000) { // 默认5分钟缓存
        this.cache = new Map();
        this.ttl = ttl;
        this.pendingRequests = new Map(); // 防止重复请求
    }

    generateKey(url, options = {}) {
        return `${url}:${JSON.stringify(options)}`;
    }

    get(url, options) {
        const key = this.generateKey(url, options);
        const cached = this.cache.get(key);

        if (cached && Date.now() - cached.timestamp < this.ttl) {
            return cached.data;
        }

        // 清理过期缓存
        if (cached) {
            this.cache.delete(key);
        }
        return null;
    }

    set(url, options, data) {
        const key = this.generateKey(url, options);
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });

        // 限制缓存大小
        if (this.cache.size > 50) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
    }

    clear() {
        this.cache.clear();
        this.pendingRequests.clear();
    }

    // 防止重复请求
    async dedupedRequest(key, requestFn) {
        // 如果已有相同请求在进行中，返回现有Promise
        if (this.pendingRequests.has(key)) {
            return this.pendingRequests.get(key);
        }

        // 创建新请求
        const promise = requestFn()
            .finally(() => {
                // 请求完成后清理
                this.pendingRequests.delete(key);
            });

        this.pendingRequests.set(key, promise);
        return promise;
    }
}

// 请求限流器
class RequestThrottler {
    constructor(maxConcurrent = 3, minInterval = 100) {
        this.maxConcurrent = maxConcurrent;
        this.minInterval = minInterval;
        this.activeRequests = 0;
        this.queue = [];
        this.lastRequestTime = 0;
    }

    async execute(fn) {
        return new Promise((resolve, reject) => {
            this.queue.push({ fn, resolve, reject });
            this.processQueue();
        });
    }

    async processQueue() {
        if (this.queue.length === 0 || this.activeRequests >= this.maxConcurrent) {
            return;
        }

        // 确保请求间隔
        const now = Date.now();
        const timeSinceLastRequest = now - this.lastRequestTime;
        if (timeSinceLastRequest < this.minInterval) {
            setTimeout(() => this.processQueue(), this.minInterval - timeSinceLastRequest);
            return;
        }

        const { fn, resolve, reject } = this.queue.shift();
        this.activeRequests++;
        this.lastRequestTime = Date.now();

        try {
            const result = await fn();
            resolve(result);
        } catch (error) {
            reject(error);
        } finally {
            this.activeRequests--;
            // 处理下一个请求
            setTimeout(() => this.processQueue(), this.minInterval);
        }
    }
}

// 主应用逻辑
class PPTGenerator {
    constructor() {
        this.apiEndpoint = '';
        this.apiKey = '';
        this.currentPresentationId = null;
        this.statusPoller = null;
        this.retryCount = 0;
        this.maxRetries = API_CONFIG.retry.maxAttempts;
        this.abortController = null; // 用于取消请求

        // 统一错误处理器
        this.errorHandler = new ErrorHandler(this);

        // 性能优化：请求缓存和限流
        this.requestCache = new RequestCache();
        this.requestThrottler = new RequestThrottler();
        this.historyCache = null; // 历史记录缓存
        this.isGenerating = false; // 防止重复提交

        this.init();
    }

    async init() {
        // 等待i18n初始化完成
        await this.waitForI18n();

        // 加载保存的配置
        this.loadConfig();

        // 绑定事件
        this.bindEvents();

        // 加载历史记录
        this.loadHistory();

        // 监听语言切换事件
        this.bindLanguageEvents();

        // 添加页面加载完成的视觉反馈
        this.showPageLoadedIndicator();
    }

    async waitForI18n() {
        // 等待i18n模块加载完成
        let attempts = 0;
        while (!window.i18n && attempts < 50) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }

        if (window.i18n) {
            // 等待i18n初始化完成
            await window.i18n.init();
        }
    }

    loadConfig() {
        // 使用统一配置管理器
        const endpoint = window.configManager.get('api.endpoint');
        const key = window.configManager.get('api.key');

        this.apiEndpoint = endpoint;
        this.apiKey = key;

        // 更新UI显示
        const endpointInput = document.getElementById('apiEndpoint');
        const keyInput = document.getElementById('apiKey');

        if (endpointInput) {
            endpointInput.value = this.apiEndpoint;
        }

        if (keyInput) {
            keyInput.value = this.apiKey;
        }

        // 监听配置变化
        window.configManager.onChange('api.endpoint', (value) => {
            this.apiEndpoint = value;
            if (endpointInput && endpointInput.value !== value) {
                endpointInput.value = value;
            }
        });

        window.configManager.onChange('api.key', (value) => {
            this.apiKey = value;
            if (keyInput && keyInput.value !== value) {
                keyInput.value = value;
            }
        });
    }

    bindEvents() {
        // 表单提交 - 添加防抖
        let submitTimer = null;
        document.getElementById('generateForm').addEventListener('submit', (e) => {
            e.preventDefault();

            // 防抖处理，避免快速重复点击
            clearTimeout(submitTimer);
            submitTimer = setTimeout(() => {
                this.generatePresentation();
            }, 300);
        });

        // API 配置更改 - 使用防抖优化
        let endpointTimer = null;
        document.getElementById('apiEndpoint').addEventListener('input', (e) => {
            clearTimeout(endpointTimer);
            endpointTimer = setTimeout(() => {
                const value = e.target.value.trim();
                window.configManager.set('api.endpoint', value);
                // 清除请求缓存
                this.requestCache.clear();
            }, 500);
        });

        let keyTimer = null;
        document.getElementById('apiKey').addEventListener('input', (e) => {
            clearTimeout(keyTimer);
            keyTimer = setTimeout(() => {
                const value = e.target.value.trim();
                window.configManager.set('api.key', value);
                // 清除请求缓存
                this.requestCache.clear();
            }, 500);
        });

        // 清除历史
        document.getElementById('clearHistory').addEventListener('click', () => {
            this.clearHistory();
        });

        // 新建按钮
        document.getElementById('newBtn').addEventListener('click', () => {
            this.resetForm();
        });

        // 取消按钮
        document.getElementById('cancelButton').addEventListener('click', () => {
            this.cancelCurrentRequest();
        });
    }

    bindLanguageEvents() {
        // 绑定语言切换选项
        document.querySelectorAll('.language-option').forEach(option => {
            option.addEventListener('click', async (e) => {
                e.preventDefault();
                const language = option.getAttribute('data-language');
                const currentLanguage = window.i18n ? window.i18n.getCurrentLanguage() : 'zh-CN';

                // 如果是当前语言，不执行切换
                if (language === currentLanguage) {
                    return;
                }

                // 添加切换动画效果
                this.showLanguageSwitchAnimation();

                if (window.i18n) {
                    try {
                        await window.i18n.switchLanguage(language);
                        // 重新加载历史记录以应用新语言
                        this.loadHistory();

                        // 显示成功消息
                        this.showLanguageChangeNotification(language);
                    } catch (error) {
                        console.error('Language switch failed:', error);
                        this.showError(this.t('errors.language_switch_failed', '语言切换失败'));
                    }
                }
            });
        });

        // 监听语言切换事件
        document.addEventListener('languageChanged', (e) => {
            // 更新下拉菜单显示的语言
            this.updateLanguageDisplay(e.detail.language);

            // 更新活跃语言选项样式
            this.updateActiveLanguageOption(e.detail.language);

            // 重新加载历史记录
            this.loadHistory();

            // 更新页面标题
            this.updatePageTitle();
        });

        // 初始化时设置当前语言
        this.initializeLanguageDisplay();
    }

    updateLanguageDisplay(language) {
        // 更新语言下拉菜单的当前选择显示
        const dropdown = document.getElementById('languageDropdown');
        const currentLabel = document.getElementById('currentLanguageLabel');

        if (dropdown && window.i18n) {
            const langText = window.i18n.getLanguageLabel(language);
            const icon = '<i class="bi bi-translate"></i>';
            const label = `<span class="text-adaptive" id="currentLanguageLabel">${langText}</span>`;
            dropdown.innerHTML = `${icon} ${label}`;
        }
    }

    updateActiveLanguageOption(language) {
        // 更新活跃语言选项的样式
        document.querySelectorAll('.language-option').forEach(option => {
            const optionLanguage = option.getAttribute('data-language');
            if (optionLanguage === language) {
                option.classList.add('active');
            } else {
                option.classList.remove('active');
            }
        });
    }

    initializeLanguageDisplay() {
        // 初始化语言显示
        setTimeout(() => {
            const currentLanguage = window.i18n ? window.i18n.getCurrentLanguage() : 'zh-CN';
            this.updateLanguageDisplay(currentLanguage);
            this.updateActiveLanguageOption(currentLanguage);
        }, 100);
    }

    showLanguageSwitchAnimation() {
        // 显示语言切换动画
        const switcher = document.querySelector('.language-switch-animation');
        if (switcher) {
            switcher.classList.add('switching');
            setTimeout(() => {
                switcher.classList.remove('switching');
            }, 600);
        }
    }

    showLanguageChangeNotification(language) {
        // 显示语言切换成功通知
        const langName = window.i18n ? window.i18n.getLanguageLabel(language) : language;

        // 创建临时通知元素
        const notification = document.createElement('div');
        notification.className = 'alert alert-success position-fixed';
        notification.style.cssText = `
            top: 80px;
            right: 20px;
            z-index: 1060;
            min-width: 250px;
            animation: slideInRight 0.3s ease;
        `;

        notification.innerHTML = `
            <i class="bi bi-check-circle-fill me-2"></i>
            ${this.t('messages.language_switched', '语言已切换至')}: <strong>${langName}</strong>
        `;

        document.body.appendChild(notification);

        // 3秒后自动移除
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);

        // 添加CSS动画样式
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    updatePageTitle() {
        // 更新页面标题
        const title = this.t('app.title', 'AI PPT 生成助手');
        document.title = title;
    }

    async generatePresentation() {
        // 防止重复提交
        if (this.isGenerating) {
            console.log('请求已在处理中，防止重复提交');
            return;
        }

        // 验证配置
        if (!this.validateConfig()) {
            return;
        }

        // 设置生成状态
        this.isGenerating = true;

        // 重置重试计数
        this.retryCount = 0;

        // 获取表单数据
        const formData = {
            topic: document.getElementById('topic').value.trim(),
            page_count: parseInt(document.getElementById('pageCount').value),
            audience: document.getElementById('audience').value
        };

        // 检查是否有相同的请求正在处理
        const requestKey = `generate:${JSON.stringify(formData)}`;

        // 显示进度
        this.showProgress();
        this.hideError();
        this.hideResult();

        // 更新生成按钮状态
        const generateBtn = document.getElementById('generateButton');
        const originalText = generateBtn.innerHTML;
        generateBtn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${this.t('form.generating', '生成中...')}`;
        generateBtn.disabled = true;

        try {
            // 使用请求去重机制
            await this.requestCache.dedupedRequest(requestKey, async () => {
                return await this.callGenerateAPI(formData, generateBtn, originalText);
            });
        } catch (error) {
            await this.errorHandler.handleApiError(error, '生成PPT', {
                generateBtn,
                originalText,
                formData
            });
        } finally {
            this.isGenerating = false;
        }
    }

    async callGenerateAPI(formData, generateBtn, originalText) {
        try {
            // 创建新的AbortController，带超时控制
            this.abortController = new AbortController();

            // 设置请求超时
            const timeoutId = setTimeout(() => {
                this.abortController.abort();
            }, window.configManager.get('api.timeout', 300000));

            // 使用统一的API端点
            const endpoint = getAPIEndpoint();
            const apiKey = getAPIKey();

            // 构建请求headers
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            };

            // 如果有API Key，添加到headers
            if (apiKey) {
                headers['X-API-Key'] = apiKey;
            }

            // 使用限流器调用 API
            const response = await this.requestThrottler.execute(async () => {
                return await fetch(`${endpoint}/generate`, {
                    method: 'POST',
                    headers,
                    body: JSON.stringify(formData),
                    signal: this.abortController.signal
                });
            });

            // 清除超时
            clearTimeout(timeoutId);

            // 详细的HTTP状态码处理
            await this.handleHTTPResponse(response);

            const data = await response.json();
            this.currentPresentationId = data.presentation_id;

            // 保存到历史
            this.saveToHistory({
                id: this.currentPresentationId,
                topic: formData.topic,
                pageCount: formData.page_count,
                audience: formData.audience,
                timestamp: new Date().toISOString(),
                status: 'processing'
            });

            // 开始轮询状态
            this.startStatusPolling();

            // 恢复按钮状态
            generateBtn.innerHTML = originalText;
            generateBtn.disabled = false;

        } catch (error) {
            // 统一错误分类处理
            throw this.classifyError(error);
        }
    }

    // HTTP响应处理方法
    async handleHTTPResponse(response) {
        if (response.ok) {
            return response;
        }

        let errorMessage = '';
        let errorDetails = '';

        // 检测CORS错误的特殊处理
        if (response.type === 'opaque' || response.type === 'opaqueredirect') {
            const error = new Error(this.t('errors.cors_error', 'CORS 错误，请检查API配置'));
            error.status = response.status;
            error.details = this.t('errors.cors_details', '可能原因：1) API端点不正确 2) 缺少CORS配置 3) API Key错误');
            throw error;
        }

        switch (response.status) {
            case 400:
                errorMessage = this.t('errors.bad_request', '请求参数错误');
                try {
                    const errorData = await response.json();
                    errorDetails = errorData.message || '';
                } catch (e) {
                    // 忽略解析错误
                }
                break;
            case 401:
                errorMessage = this.t('errors.unauthorized', 'API Key 无效或已过期');
                break;
            case 403:
                errorMessage = this.t('errors.forbidden', '访问被拒绝，请检查权限');
                break;
            case 404:
                errorMessage = this.t('errors.not_found', 'API端点不存在');
                errorDetails = this.t('errors.check_endpoint', '请检查API Gateway URL是否正确');
                break;
            case 408:
                errorMessage = this.t('errors.timeout_error', '请求超时');
                break;
            case 429:
                errorMessage = this.t('errors.rate_limit', '请求过于频繁，请稍后重试');
                break;
            case 500:
                errorMessage = this.t('errors.server_error', '服务器内部错误');
                break;
            case 502:
            case 503:
            case 504:
                errorMessage = this.t('errors.service_unavailable', '服务暂时不可用');
                break;
            default:
                errorMessage = this.t('errors.api_error', 'API 错误') + ': ' + response.status;
        }

        const error = new Error(errorMessage + (errorDetails ? ' - ' + errorDetails : ''));
        error.status = response.status;
        error.response = response;
        throw error;
    }

    // 错误分类方法
    classifyError(error) {
        // 如果请求被取消
        if (error.name === 'AbortError') {
            const classifiedError = new Error(this.t('errors.request_cancelled', '请求已取消'));
            classifiedError.isAborted = true;
            return classifiedError;
        }

        // 网络错误
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            const networkError = new Error(this.t('errors.network_error', '网络连接失败，请检查网络或API端点'));
            networkError.name = 'NetworkError';
            return networkError;
        }

        // 超时错误
        if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
            const timeoutError = new Error(this.t('errors.timeout_error', '请求超时，请稍后重试'));
            timeoutError.name = 'TimeoutError';
            return timeoutError;
        }

        // 如果已经是分类过的错误，直接返回
        if (error.status) {
            return error;
        }

        // 其他未分类错误
        return new Error(this.t('errors.unknown_error', '未知错误') + ': ' + error.message);
    }

    async handleGenerationError(error, generateBtn, originalText) {
        console.error('生成错误:', error);

        // 恢复按钮状态
        generateBtn.innerHTML = originalText;
        generateBtn.disabled = false;

        // 检查是否需要重试
        if (this.retryCount < this.maxRetries && this.shouldRetry(error)) {
            this.retryCount++;
            const delay = API_CONFIG.retry.delayMs * Math.pow(API_CONFIG.retry.backoffMultiplier, this.retryCount - 1);

            this.showError(`${this.t('errors.generation_failed', '生成失败')}: ${error.message}. ${this.t('status.retrying', '重试中')}... (${this.retryCount}/${this.maxRetries})`);

            setTimeout(async () => {
                const formData = {
                    topic: document.getElementById('topic').value,
                    page_count: parseInt(document.getElementById('pageCount').value),
                    audience: document.getElementById('audience').value
                };

                try {
                    await this.callGenerateAPI(formData, generateBtn, originalText);
                } catch (retryError) {
                    await this.handleGenerationError(retryError, generateBtn, originalText);
                }
            }, delay);
        } else {
            this.showError(`${this.t('errors.generation_failed', '生成失败')}: ${error.message}. ${this.t('errors.retry_later', '请稍后重试')}`);
            this.hideProgress();
        }
    }

    shouldRetry(error) {
        // 基于HTTP状态码和错误类型的智能重试判断
        if (error.isAborted) {
            return false; // 用户取消的请求不重试
        }

        // 检查HTTP状态码
        if (error.status) {
            const retryableStatusCodes = [408, 429, 500, 502, 503, 504];
            return retryableStatusCodes.includes(error.status);
        }

        // 检查错误类型
        const retryableErrors = ['NetworkError', 'TimeoutError', 'TypeError'];
        return retryableErrors.some(type =>
            error.name === type || error.message.includes(type)
        );
    }

    validateConfig() {
        const endpoint = getAPIEndpoint();
        const apiKey = getAPIKey();

        if (!endpoint) {
            this.showError(this.t('errors.config_missing', '请先配置 API Gateway URL'));
            return false;
        }

        if (!apiKey) {
            this.showError(this.t('errors.config_missing', '请先配置 API Key'));
            return false;
        }

        // 验证URL格式
        try {
            new URL(endpoint);
        } catch (e) {
            this.showError(this.t('errors.invalid_url', 'API URL 格式不正确'));
            return false;
        }

        return true;
    }

    // 国际化辅助方法
    t(key, fallback = '') {
        return window.i18n ? window.i18n.t(key) : fallback;
    }

    showPageLoadedIndicator() {
        // 显示页面加载完成指示器
        const indicator = document.createElement('div');
        indicator.className = 'position-fixed bg-success text-white px-3 py-2 rounded';
        indicator.style.cssText = `
            bottom: 20px;
            right: 20px;
            z-index: 1060;
            font-size: 0.875rem;
            opacity: 0;
            animation: fadeInUp 0.3s ease forwards;
        `;

        indicator.innerHTML = `
            <i class="bi bi-check-circle me-2"></i>
            ${this.t('messages.page_loaded', '页面加载完成')}
        `;

        document.body.appendChild(indicator);

        setTimeout(() => {
            indicator.style.animation = 'fadeOutDown 0.3s ease forwards';
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.parentNode.removeChild(indicator);
                }
            }, 300);
        }, 2000);

        // 添加动画样式
        if (!document.getElementById('page-load-styles')) {
            const style = document.createElement('style');
            style.id = 'page-load-styles';
            style.textContent = `
                @keyframes fadeInUp {
                    from { transform: translateY(20px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                @keyframes fadeOutDown {
                    from { transform: translateY(0); opacity: 1; }
                    to { transform: translateY(20px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    showProgress() {
        document.querySelector('.progress-container').style.display = 'block';
        this.updateProgress(0, this.t('progress.initializing', '正在初始化...'));

        // 显示取消按钮，隐藏生成按钮
        document.getElementById('generateButton').classList.add('d-none');
        document.getElementById('cancelButton').classList.remove('d-none');
    }

    hideProgress() {
        document.querySelector('.progress-container').style.display = 'none';

        // 恢复按钮状态
        document.getElementById('generateButton').classList.remove('d-none');
        document.getElementById('cancelButton').classList.add('d-none');

        const generateBtn = document.getElementById('generateButton');
        generateBtn.disabled = false;
        // 恢复按钮文本（如果需要）
        const icon = '<i class="bi bi-play-circle"></i>';
        const text = this.t('form.generate_button', '开始生成');
        generateBtn.innerHTML = `${icon} <span data-i18n="form.generate_button">${text}</span>`;
    }

    updateProgress(percent, status, details = '') {
        document.getElementById('progressBar').style.width = `${percent}%`;
        document.getElementById('progressPercent').textContent = `${percent}%`;
        document.getElementById('statusText').textContent = status;
        document.getElementById('statusDetails').textContent = details;
    }

    showError(message) {
        const alertDiv = document.getElementById('errorAlert');
        document.getElementById('errorMessage').textContent = message;
        alertDiv.classList.remove('d-none');
    }

    hideError() {
        document.getElementById('errorAlert').classList.add('d-none');
    }

    showResult(presentation) {
        const resultCard = document.getElementById('resultCard');
        document.getElementById('resultTitle').textContent = presentation.topic;
        document.getElementById('generationTime').textContent =
            new Date(presentation.timestamp).toLocaleString('zh-CN');

        resultCard.classList.remove('d-none');

        // 绑定下载按钮
        document.getElementById('downloadBtn').onclick = () => {
            this.downloadPresentation(presentation.id);
        };
    }

    hideResult() {
        document.getElementById('resultCard').classList.add('d-none');
    }

    saveToHistory(presentation) {
        let history = JSON.parse(localStorage.getItem('pptHistory') || '[]');

        // 去重：如果已存在相同ID，先删除旧的
        history = history.filter(item => item.id !== presentation.id);

        // 添加到开头
        history.unshift(presentation);

        // 只保留最近的条目，配置化
        const maxItems = window.configManager.get('ui.maxHistoryItems', 10);
        history = history.slice(0, maxItems);

        localStorage.setItem('pptHistory', JSON.stringify(history));

        // 清除缓存，强制刷新
        this.historyCache = null;
        this.loadHistory();
    }

    loadHistory() {
        // 使用缓存避免重复解析
        if (this.historyCache && Date.now() - this.historyCache.timestamp < 5000) {
            this.renderHistory(this.historyCache.data);
            return;
        }

        const history = JSON.parse(localStorage.getItem('pptHistory') || '[]');

        // 缓存历史记录
        this.historyCache = {
            data: history,
            timestamp: Date.now()
        };

        this.renderHistory(history);
    }

    renderHistory(history) {
        const historyList = document.getElementById('historyList');

        if (history.length === 0) {
            historyList.innerHTML = `<div class="text-muted text-center py-3">${this.t('history.empty', '暂无历史记录')}</div>`;
            return;
        }

        // 使用DocumentFragment提升渲染性能
        const fragment = document.createDocumentFragment();
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = history.map(item => `
            <div class="list-group-item history-item" data-id="${item.id}">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${this.truncateText(item.topic, 30)}</h6>
                    <small>${this.formatDate(item.timestamp)}</small>
                </div>
                <p class="mb-1 small text-muted">
                    ${item.pageCount} ${this.t('history.pages', '页')} | ${this.getAudienceLabel(item.audience)}
                </p>
                <span class="badge ${this.getStatusBadgeClass(item.status)}">
                    ${this.getStatusLabel(item.status)}
                </span>
            </div>
        `).join('');

        // 批量添加到Fragment
        while (tempDiv.firstChild) {
            fragment.appendChild(tempDiv.firstChild);
        }

        // 一次性更新DOM
        historyList.innerHTML = '';
        historyList.appendChild(fragment);

        // 使用事件委托替代多个监听器
        if (!historyList.hasAttribute('data-listeners-bound')) {
            historyList.addEventListener('click', (e) => {
                const item = e.target.closest('.history-item');
                if (item) {
                    const id = item.dataset.id;
                    const historyItem = history.find(h => h.id === id);
                    if (historyItem && historyItem.status === 'completed') {
                        // 防抖处理
                        if (!item.hasAttribute('data-downloading')) {
                            item.setAttribute('data-downloading', 'true');
                            this.downloadPresentation(id).finally(() => {
                                item.removeAttribute('data-downloading');
                            });
                        }
                    }
                }
            });
            historyList.setAttribute('data-listeners-bound', 'true');
        }
    }

    clearHistory() {
        if (confirm(this.t('history.clear_confirm', '确定要清除所有历史记录吗？'))) {
            localStorage.removeItem('pptHistory');
            this.loadHistory();
        }
    }

    truncateText(text, maxLength) {
        return text.length > maxLength ?
            text.substring(0, maxLength) + '...' : text;
    }

    formatDate(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return `${minutes} ${this.t('history.minutes_ago', '分钟前')}`;
        } else if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `${hours} ${this.t('history.hours_ago', '小时前')}`;
        } else {
            const locale = window.i18n ? window.i18n.getCurrentLanguage() : 'zh-CN';
            return date.toLocaleDateString(locale);
        }
    }

    getAudienceLabel(audience) {
        const labelKeys = {
            'general': 'form.audience_general',
            'technical': 'form.audience_technical',
            'executive': 'form.audience_executive',
            'academic': 'form.audience_academic'
        };

        const fallbacks = {
            'general': '普通观众',
            'technical': '技术人员',
            'executive': '高层管理',
            'academic': '学术研究'
        };

        return this.t(labelKeys[audience], fallbacks[audience] || audience);
    }

    getStatusBadgeClass(status) {
        const classes = {
            'processing': 'bg-warning',
            'completed': 'bg-success',
            'failed': 'bg-danger',
            'pending': 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }

    getStatusLabel(status) {
        const labelKeys = {
            'processing': 'history.status_processing',
            'completed': 'history.status_completed',
            'failed': 'history.status_failed',
            'pending': 'history.status_pending'
        };

        const fallbacks = {
            'processing': '生成中',
            'completed': '已完成',
            'failed': '失败',
            'pending': '等待中'
        };

        return this.t(labelKeys[status], fallbacks[status] || status);
    }

    showResult(presentation) {
        const resultCard = document.getElementById('resultCard');
        document.getElementById('resultTitle').textContent = presentation.topic;
        document.getElementById('generationTime').textContent =
            new Date(presentation.timestamp).toLocaleString('zh-CN');

        resultCard.classList.remove('d-none');

        // 绑定下载按钮
        document.getElementById('downloadBtn').onclick = () => {
            this.downloadPresentation(presentation.id);
        };
    }

    hideResult() {
        document.getElementById('resultCard').classList.add('d-none');
    }

    resetForm() {
        // 重置表单
        document.getElementById('generateForm').reset();

        // 隐藏进度和结果
        this.hideProgress();
        this.hideResult();
        this.hideError();

        // 取消正在进行的请求
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }

        // 重置状态
        this.currentPresentationId = null;
        this.isGenerating = false;
        this.retryCount = 0;

        // 清理缓存中的待处理请求
        this.requestCache.pendingRequests.clear();
    }

    // 取消当前请求
    cancelCurrentRequest() {
        // 确认取消操作
        if (confirm(this.t('messages.cancel_confirm', '确定要取消当前操作吗？'))) {
            // 取消网络请求
            if (this.abortController) {
                this.abortController.abort();
                this.abortController = null;
            }

            // 停止状态轮询
            if (this.statusPoller) {
                clearTimeout(this.statusPoller);
                this.statusPoller = null;
            }

            // 停止状态轮询器（如果存在）
            if (this.stopStatusPolling) {
                this.stopStatusPolling();
            }

            // 显示取消消息
            this.showError(this.t('messages.operation_cancelled', '操作已取消'));

            // 隐藏进度，恢复UI
            this.hideProgress();
            this.hideError();

            // 重置当前ID
            this.currentPresentationId = null;

            // 显示取消成功的临时提示
            setTimeout(() => {
                this.hideError();
            }, 3000);
        }
    }
}

// 内存泄漏清理
class MemoryManager {
    constructor(app) {
        this.app = app;
        this.setupCleanup();
    }

    setupCleanup() {
        // 页面卸载时清理
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });

        // 定期清理（每5分钟）
        setInterval(() => {
            this.periodicCleanup();
        }, 300000);
    }

    cleanup() {
        // 取消所有进行中的请求
        if (this.app.abortController) {
            this.app.abortController.abort();
        }

        // 清理定时器
        if (this.app.statusPoller) {
            clearTimeout(this.app.statusPoller);
        }

        // 清理缓存
        this.app.requestCache.clear();

        // 清理事件监听器
        this.removeUnusedListeners();
    }

    periodicCleanup() {
        // 清理过期缓存
        const now = Date.now();
        for (const [key, value] of this.app.requestCache.cache.entries()) {
            if (now - value.timestamp > this.app.requestCache.ttl) {
                this.app.requestCache.cache.delete(key);
            }
        }

        // 清理过大的历史记录
        const maxHistorySize = window.configManager.get('ui.maxHistoryItems', 10);
        let history = JSON.parse(localStorage.getItem('pptHistory') || '[]');
        if (history.length > maxHistorySize) {
            history = history.slice(0, maxHistorySize);
            localStorage.setItem('pptHistory', JSON.stringify(history));
        }
    }

    removeUnusedListeners() {
        // 移除未使用的事件监听器
        const unusedElements = document.querySelectorAll('[data-listener-removed]');
        unusedElements.forEach(el => {
            el.replaceWith(el.cloneNode(true));
        });
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.pptGenerator = new PPTGenerator();

    // 初始化内存管理器
    window.memoryManager = new MemoryManager(window.pptGenerator);

    // 性能监控
    if (window.performance && window.performance.mark) {
        window.performance.mark('app-initialized');
        console.log('应用初始化完成，性能优化已启用');
    }
});