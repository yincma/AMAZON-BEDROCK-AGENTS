// 状态轮询管理 - 优化版
class StatusPoller {
    constructor(generator) {
        this.generator = generator;
        this.pollInterval = window.configManager.get('polling.intervalMs', 2000);
        this.maxRetries = window.configManager.get('polling.maxAttempts', 150);
        this.currentRetries = 0;
        this.backoffMultiplier = 1.5; // 指数退避系数
        this.maxInterval = 30000; // 最大轮询间隔30秒
        this.consecutiveErrors = 0; // 连续错误计数
        this.lastProgress = 0; // 上次进度
    }

    // 国际化辅助方法
    t(key, fallback = '') {
        return window.i18n ? window.i18n.t(key) : fallback;
    }

    start(presentationId) {
        this.currentRetries = 0;
        this.poll(presentationId);
    }

    stop() {
        if (this.generator.statusPoller) {
            clearTimeout(this.generator.statusPoller);
            this.generator.statusPoller = null;
        }
    }

    async poll(presentationId) {
        try {
            // 检查是否应该继续轮询
            if (this.currentRetries >= this.maxRetries) {
                this.handleTimeout();
                return;
            }

            // 使用缓存检查
            const cacheKey = `status:${presentationId}`;
            const cached = this.generator.requestCache?.get(`${getAPIEndpoint()}/status/${presentationId}`, {});

            if (cached && cached.status === 'completed') {
                this.handleCompletion(presentationId, cached);
                return;
            }

            // 使用统一的API端点和Key
            const endpoint = getAPIEndpoint();
            const apiKey = getAPIKey();

            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            };

            // 如果有API Key，添加到headers
            if (apiKey) {
                headers['X-API-Key'] = apiKey;
            }

            // 使用限流器执行请求
            const response = await (this.generator.requestThrottler ?
                this.generator.requestThrottler.execute(async () => {
                    return await fetch(
                        `${endpoint}/status/${presentationId}`,
                        {
                            method: 'GET',
                            headers,
                            signal: AbortSignal.timeout(10000) // 10秒超时
                        }
                    );
                }) :
                fetch(
                    `${endpoint}/status/${presentationId}`,
                    {
                        method: 'GET',
                        headers
                    }
                )
            );

            // 使用主应用的错误处理逻辑
            if (!response.ok) {
                await this.generator.handleHTTPResponse(response);
            }

            const data = await response.json();

            // 缓存状态结果
            if (this.generator.requestCache) {
                this.generator.requestCache.set(
                    `${endpoint}/status/${presentationId}`,
                    {},
                    data
                );
            }

            // 重置连续错误计数
            this.consecutiveErrors = 0;

            this.handleStatusUpdate(data, presentationId);

            // 智能轮询策略
            if (data.status === 'processing' || data.status === 'pending') {
                this.currentRetries++;

                if (this.currentRetries < this.maxRetries) {
                    // 动态调整轮询间隔
                    const nextInterval = this.calculateDynamicInterval(data.progress || 0);

                    this.generator.statusPoller = setTimeout(
                        () => this.poll(presentationId),
                        nextInterval
                    );
                } else {
                    this.handleTimeout();
                }
            } else if (data.status === 'completed') {
                // 直接处理完成状态
                this.handleCompletion(presentationId, data);
            }

        } catch (error) {
            console.error('状态轮询错误:', error);
            this.consecutiveErrors++;

            // 使用指数退避策略处理错误
            if (this.consecutiveErrors < 3) {
                const retryDelay = Math.min(
                    this.pollInterval * Math.pow(this.backoffMultiplier, this.consecutiveErrors),
                    this.maxInterval
                );

                console.log(`状态查询失败，${retryDelay}ms 后重试... (${this.consecutiveErrors}/3)`);

                this.generator.statusPoller = setTimeout(
                    () => this.poll(presentationId),
                    retryDelay
                );
            } else {
                this.handleError(error);
            }
        }
    }

    // 计算动态轮询间隔
    calculateDynamicInterval(currentProgress) {
        const progressDiff = currentProgress - this.lastProgress;
        this.lastProgress = currentProgress;

        // 根据进度变化速度调整间隔
        if (progressDiff > 20) {
            // 进度快速变化，频繁轮询
            return Math.max(this.pollInterval * 0.5, 1000);
        } else if (progressDiff > 10) {
            // 正常进度
            return this.pollInterval;
        } else if (progressDiff > 0) {
            // 进度缓慢，减少轮询频率
            return Math.min(this.pollInterval * 1.5, 5000);
        } else {
            // 进度停滞，使用指数退避
            const interval = Math.min(
                this.pollInterval * Math.pow(this.backoffMultiplier, Math.floor(this.currentRetries / 10)),
                this.maxInterval
            );
            return interval;
        }
    }

    handleStatusUpdate(data, presentationId) {
        const progress = data.progress || 0;
        let statusText = '';
        let details = '';

        // 根据进度设置不同的状态文本
        if (progress < 20) {
            statusText = this.t('progress.initializing', '正在初始化...');
            details = this.t('progress.analyzing', '解析主题，准备生成大纲');
        } else if (progress < 40) {
            statusText = this.t('progress.creating_outline', '生成内容大纲...');
            details = this.t('progress.ai_structure', '使用 AI 创建演示文稿结构');
        } else if (progress < 60) {
            statusText = this.t('progress.generating_content', '扩展幻灯片内容...');
            details = this.t('progress.detailed_content', '为每页生成详细内容和演讲备注');
        } else if (progress < 80) {
            statusText = this.t('progress.processing_images', '生成配图...');
            details = this.t('progress.suitable_images', '为幻灯片创建或搜索合适的图片');
        } else if (progress < 100) {
            statusText = this.t('progress.compiling', '编译 PPT 文件...');
            details = this.t('progress.final_assembly', '组装最终的演示文稿文件');
        } else {
            statusText = this.t('progress.completed', '完成！');
            details = this.t('progress.success_generated', '演示文稿已生成成功');
        }

        // 更新进度显示
        this.generator.updateProgress(progress, statusText, details);

        // 处理不同的状态
        switch (data.status) {
            case 'completed':
                this.handleCompletion(presentationId, data);
                break;
            case 'failed':
                this.handleFailure(data.message || this.t('errors.generation_failed', '生成失败'));
                break;
            case 'processing':
            case 'pending':
                // 继续轮询
                break;
            default:
                console.warn('未知状态:', data.status);
        }
    }

    handleCompletion(presentationId, data) {
        // 停止轮询
        this.stop();

        // 重置状态
        this.currentRetries = 0;
        this.consecutiveErrors = 0;
        this.lastProgress = 0;

        // 更新进度到100%
        this.generator.updateProgress(100, this.t('progress.completed', '生成完成！'), this.t('progress.preparing_download', '正在准备下载...'));

        // 更新历史记录状态
        this.updateHistoryStatus(presentationId, 'completed');

        // 显示结果卡片 - 使用API返回的数据
        const presentation = {
            id: presentationId,
            topic: data?.topic || '演示文稿',
            pageCount: data?.page_count || 10,
            timestamp: data?.created_at || new Date().toISOString(),
            status: 'completed'
        };

        this.generator.showResult(presentation);

        // 播放完成提示音（如果浏览器支持）
        this.playNotificationSound();

        // 优化：使用 requestAnimationFrame 提升动画流畅度
        requestAnimationFrame(() => {
            setTimeout(() => {
                this.generator.hideProgress();
            }, 3000);
        });
    }

    handleFailure(message) {
        // 停止轮询
        this.stop();

        // 显示错误
        this.generator.showError(`${this.t('errors.generation_failed', '生成失败')}: ${message}`);

        // 更新历史记录状态
        if (this.generator.currentPresentationId) {
            this.updateHistoryStatus(this.generator.currentPresentationId, 'failed');
        }

        // 隐藏进度条
        this.generator.hideProgress();
    }

    handleTimeout() {
        this.stop();
        this.generator.showError(this.t('errors.timeout_error', '生成超时，请稍后重试'));
        this.generator.hideProgress();

        if (this.generator.currentPresentationId) {
            this.updateHistoryStatus(this.generator.currentPresentationId, 'failed');
        }
    }

    handleError(error) {
        console.error('状态轮询最终错误:', error);

        // 使用主应用的错误分类逻辑
        const classifiedError = this.generator.classifyError(error);

        // 不再重试，直接处理失败
        this.handleFailure(classifiedError.message);
    }

    updateHistoryStatus(presentationId, status) {
        let history = JSON.parse(localStorage.getItem('pptHistory') || '[]');
        const index = history.findIndex(h => h.id === presentationId);

        if (index !== -1) {
            history[index].status = status;
            localStorage.setItem('pptHistory', JSON.stringify(history));
            this.generator.loadHistory();
        }
    }

    playNotificationSound() {
        try {
            // 创建一个简单的提示音
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (e) {
            // 忽略音频错误
            console.log('无法播放提示音');
        }
    }
}

// 扩展主应用的轮询功能
document.addEventListener('DOMContentLoaded', () => {
    // 等待一小段时间确保app.js初始化完成
    setTimeout(() => {
        if (window.pptGenerator) {
            const statusPoller = new StatusPoller(window.pptGenerator);

            window.pptGenerator.startStatusPolling = function() {
                statusPoller.start(this.currentPresentationId);
            };

            window.pptGenerator.stopStatusPolling = function() {
                statusPoller.stop();
            };
        }
    }, 100);
});