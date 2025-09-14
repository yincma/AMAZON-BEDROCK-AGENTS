// 状态轮询管理
class StatusPoller {
    constructor(generator) {
        this.generator = generator;
        this.pollInterval = 3000; // 3秒轮询一次
        this.maxRetries = 100; // 最多轮询100次（5分钟）
        this.currentRetries = 0;
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
            const response = await fetch(
                `${this.generator.apiEndpoint}/status/${presentationId}`,
                {
                    method: 'GET',
                    headers: {
                        'X-API-Key': this.generator.apiKey
                    }
                }
            );

            if (!response.ok) {
                throw new Error(`状态查询失败: ${response.status}`);
            }

            const data = await response.json();
            this.handleStatusUpdate(data, presentationId);

            // 根据状态决定是否继续轮询
            // 我们的简化API总是返回completed状态，所以不需要继续轮询
            if (data.status === 'processing' || data.status === 'pending') {
                this.currentRetries++;

                if (this.currentRetries < this.maxRetries) {
                    this.generator.statusPoller = setTimeout(
                        () => this.poll(presentationId),
                        this.pollInterval
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
            this.handleError(error);
        }
    }

    handleStatusUpdate(data, presentationId) {
        const progress = data.progress || 0;
        let statusText = '';
        let details = '';

        // 根据进度设置不同的状态文本
        if (progress < 20) {
            statusText = '正在分析需求...';
            details = '解析主题，准备生成大纲';
        } else if (progress < 40) {
            statusText = '生成内容大纲...';
            details = '使用 AI 创建演示文稿结构';
        } else if (progress < 60) {
            statusText = '扩展幻灯片内容...';
            details = '为每页生成详细内容和演讲备注';
        } else if (progress < 80) {
            statusText = '生成配图...';
            details = '为幻灯片创建或搜索合适的图片';
        } else if (progress < 100) {
            statusText = '编译 PPT 文件...';
            details = '组装最终的演示文稿文件';
        } else {
            statusText = '完成！';
            details = '演示文稿已生成成功';
        }

        // 更新进度显示
        this.generator.updateProgress(progress, statusText, details);

        // 处理不同的状态
        switch (data.status) {
            case 'completed':
                this.handleCompletion(presentationId, data);
                break;
            case 'failed':
                this.handleFailure(data.message || '生成失败');
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

        // 更新进度到100%
        this.generator.updateProgress(100, '生成完成！', '正在准备下载...');

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

        // 3秒后隐藏进度条
        setTimeout(() => {
            this.generator.hideProgress();
        }, 3000);
    }

    handleFailure(message) {
        // 停止轮询
        this.stop();

        // 显示错误
        this.generator.showError(`生成失败: ${message}`);

        // 更新历史记录状态
        if (this.generator.currentPresentationId) {
            this.updateHistoryStatus(this.generator.currentPresentationId, 'failed');
        }

        // 隐藏进度条
        this.generator.hideProgress();
    }

    handleTimeout() {
        this.stop();
        this.generator.showError('生成超时，请稍后重试');
        this.generator.hideProgress();

        if (this.generator.currentPresentationId) {
            this.updateHistoryStatus(this.generator.currentPresentationId, 'failed');
        }
    }

    handleError(error) {
        // 重试几次
        if (this.currentRetries < 3) {
            console.log('状态查询失败，重试中...');
            setTimeout(() => {
                this.poll(this.generator.currentPresentationId);
            }, this.pollInterval);
        } else {
            this.handleFailure('网络错误，无法获取状态');
        }
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