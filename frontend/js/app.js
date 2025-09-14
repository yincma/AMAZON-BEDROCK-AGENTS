// 主应用逻辑
class PPTGenerator {
    constructor() {
        this.apiEndpoint = '';
        this.apiKey = '';
        this.currentPresentationId = null;
        this.statusPoller = null;

        this.init();
    }

    init() {
        // 加载保存的配置
        this.loadConfig();

        // 绑定事件
        this.bindEvents();

        // 加载历史记录
        this.loadHistory();
    }

    loadConfig() {
        const savedEndpoint = localStorage.getItem('apiEndpoint');
        const savedKey = localStorage.getItem('apiKey');

        if (savedEndpoint) {
            document.getElementById('apiEndpoint').value = savedEndpoint;
            this.apiEndpoint = savedEndpoint;
        }

        if (savedKey) {
            document.getElementById('apiKey').value = savedKey;
            this.apiKey = savedKey;
        }
    }

    bindEvents() {
        // 表单提交
        document.getElementById('generateForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.generatePresentation();
        });

        // API 配置更改
        document.getElementById('apiEndpoint').addEventListener('change', (e) => {
            this.apiEndpoint = e.target.value;
            localStorage.setItem('apiEndpoint', this.apiEndpoint);
        });

        document.getElementById('apiKey').addEventListener('change', (e) => {
            this.apiKey = e.target.value;
            localStorage.setItem('apiKey', this.apiKey);
        });

        // 清除历史
        document.getElementById('clearHistory').addEventListener('click', () => {
            this.clearHistory();
        });

        // 新建按钮
        document.getElementById('newBtn').addEventListener('click', () => {
            this.resetForm();
        });
    }

    async generatePresentation() {
        // 验证配置
        if (!this.validateConfig()) {
            return;
        }

        // 获取表单数据
        const formData = {
            topic: document.getElementById('topic').value,
            page_count: parseInt(document.getElementById('pageCount').value),
            audience: document.getElementById('audience').value
        };

        // 显示进度
        this.showProgress();
        this.hideError();
        this.hideResult();

        try {
            // 调用 API
            const response = await fetch(`${this.apiEndpoint}/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                throw new Error(`API 错误: ${response.status}`);
            }

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

        } catch (error) {
            this.showError(`生成失败: ${error.message}`);
            this.hideProgress();
        }
    }

    validateConfig() {
        if (!this.apiEndpoint || !this.apiKey) {
            this.showError('请先配置 API Gateway URL 和 API Key');
            return false;
        }
        return true;
    }

    showProgress() {
        document.querySelector('.progress-container').style.display = 'block';
        this.updateProgress(0, '正在初始化...');
    }

    hideProgress() {
        document.querySelector('.progress-container').style.display = 'none';
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

    resetForm() {
        document.getElementById('generateForm').reset();
        this.hideProgress();
        this.hideError();
        this.hideResult();
        if (this.statusPoller) {
            clearInterval(this.statusPoller);
        }
    }

    saveToHistory(presentation) {
        let history = JSON.parse(localStorage.getItem('pptHistory') || '[]');

        // 添加到开头
        history.unshift(presentation);

        // 只保留最近10条
        history = history.slice(0, 10);

        localStorage.setItem('pptHistory', JSON.stringify(history));
        this.loadHistory();
    }

    loadHistory() {
        const history = JSON.parse(localStorage.getItem('pptHistory') || '[]');
        const historyList = document.getElementById('historyList');

        if (history.length === 0) {
            historyList.innerHTML = '<div class="text-muted text-center py-3">暂无历史记录</div>';
            return;
        }

        historyList.innerHTML = history.map(item => `
            <div class="list-group-item history-item" data-id="${item.id}">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${this.truncateText(item.topic, 30)}</h6>
                    <small>${this.formatDate(item.timestamp)}</small>
                </div>
                <p class="mb-1 small text-muted">
                    ${item.pageCount} 页 | ${this.getAudienceLabel(item.audience)}
                </p>
                <span class="badge ${this.getStatusBadgeClass(item.status)}">
                    ${this.getStatusLabel(item.status)}
                </span>
            </div>
        `).join('');

        // 绑定点击事件
        document.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.dataset.id;
                const historyItem = history.find(h => h.id === id);
                if (historyItem && historyItem.status === 'completed') {
                    this.downloadPresentation(id);
                }
            });
        });
    }

    clearHistory() {
        if (confirm('确定要清除所有历史记录吗？')) {
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
            return `${Math.floor(diff / 60000)} 分钟前`;
        } else if (diff < 86400000) {
            return `${Math.floor(diff / 3600000)} 小时前`;
        } else {
            return date.toLocaleDateString('zh-CN');
        }
    }

    getAudienceLabel(audience) {
        const labels = {
            'general': '普通观众',
            'technical': '技术人员',
            'executive': '高层管理',
            'academic': '学术研究'
        };
        return labels[audience] || audience;
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
        const labels = {
            'processing': '生成中',
            'completed': '已完成',
            'failed': '失败',
            'pending': '等待中'
        };
        return labels[status] || status;
    }

    showResult(presentation) {
        // 显示结果卡片
        const resultCard = document.getElementById('resultCard');
        resultCard.classList.remove('d-none');

        document.getElementById('resultTitle').textContent = presentation.topic;
        document.getElementById('generationTime').textContent = new Date(presentation.timestamp).toLocaleString('zh-CN');

        // 绑定下载按钮事件
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.onclick = () => {
            if (this.downloadPresentation) {
                this.downloadPresentation(presentation.id);
            }
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

        // 重置当前ID
        this.currentPresentationId = null;
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.pptGenerator = new PPTGenerator();
});