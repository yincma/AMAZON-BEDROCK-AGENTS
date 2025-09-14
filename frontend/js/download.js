// 下载管理
class DownloadManager {
    constructor(generator) {
        this.generator = generator;
    }

    async downloadPresentation(presentationId) {
        try {
            // 显示下载中状态
            const downloadBtn = document.getElementById('downloadBtn');
            const originalText = downloadBtn.innerHTML;
            downloadBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 获取下载链接...';
            downloadBtn.disabled = true;

            // 获取下载链接
            const response = await fetch(
                `${this.generator.apiEndpoint}/download/${presentationId}`,
                {
                    method: 'GET',
                    headers: {
                        'X-API-Key': this.generator.apiKey
                    }
                }
            );

            if (!response.ok) {
                throw new Error(`获取下载链接失败: ${response.status}`);
            }

            const data = await response.json();

            // 如果有下载链接，使用它；否则显示提示
            if (data.download_url) {
                // 如果是模拟链接，显示提示
                if (data.download_url.includes('example.com')) {
                    this.generator.showError('PPT下载功能仅在完整部署后可用');
                    return;
                }

                // 获取文件信息（可选）
                await this.updateFileSize(data.download_url);

                // 触发下载
                this.triggerDownload(data.download_url, presentationId);
            } else {
                // 如果没有下载链接，显示演示数据
                this.showPresentationData(data);
            }

            // 恢复按钮状态
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;

            // 记录下载
            this.recordDownload(presentationId);

        } catch (error) {
            console.error('下载失败:', error);
            this.generator.showError(`下载失败: ${error.message}`);

            // 恢复按钮
            const downloadBtn = document.getElementById('downloadBtn');
            downloadBtn.innerHTML = '<i class="bi bi-download"></i> 下载 PPT';
            downloadBtn.disabled = false;
        }
    }

    triggerDownload(url, presentationId) {
        // 方法1：使用隐藏的 a 标签
        const link = document.createElement('a');
        link.href = url;
        link.download = `presentation_${presentationId}.pptx`;
        link.style.display = 'none';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // 方法2：如果方法1不工作，打开新窗口
        // window.open(url, '_blank');

        // 显示成功提示
        this.showDownloadSuccess();
    }

    async updateFileSize(url) {
        try {
            // 尝试 HEAD 请求获取文件大小
            const response = await fetch(url, {
                method: 'HEAD'
            });

            if (response.ok) {
                const contentLength = response.headers.get('content-length');
                if (contentLength) {
                    const sizeInBytes = parseInt(contentLength);
                    const sizeText = this.formatFileSize(sizeInBytes);
                    document.getElementById('fileSize').textContent = sizeText;
                }
            }
        } catch (error) {
            // 忽略错误，文件大小不是必需的
            document.getElementById('fileSize').textContent = 'N/A';
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    recordDownload(presentationId) {
        // 更新下载次数
        let downloadStats = JSON.parse(localStorage.getItem('downloadStats') || '{}');

        if (!downloadStats[presentationId]) {
            downloadStats[presentationId] = {
                count: 0,
                lastDownload: null
            };
        }

        downloadStats[presentationId].count++;
        downloadStats[presentationId].lastDownload = new Date().toISOString();

        localStorage.setItem('downloadStats', JSON.stringify(downloadStats));
    }

    showDownloadSuccess() {
        // 创建临时提示
        const toast = document.createElement('div');
        toast.className = 'position-fixed bottom-0 end-0 p-3';
        toast.style.zIndex = '11';
        toast.innerHTML = `
            <div class="toast show" role="alert">
                <div class="toast-header bg-success text-white">
                    <i class="bi bi-check-circle me-2"></i>
                    <strong class="me-auto">下载成功</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    PPT 文件已开始下载，请查看浏览器下载列表。
                </div>
            </div>
        `;

        document.body.appendChild(toast);

        // 3秒后自动移除
        setTimeout(() => {
            toast.remove();
        }, 3000);

        // 绑定关闭按钮
        toast.querySelector('.btn-close').addEventListener('click', () => {
            toast.remove();
        });
    }

    showPresentationData(data) {
        // 显示演示数据（用于开发测试）
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">演示文稿内容预览</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 绑定关闭事件
        modal.querySelectorAll('[data-bs-dismiss="modal"]').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.remove();
            });
        });

        // 点击背景也关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    // 批量下载功能（可选）
    async downloadMultiple(presentationIds) {
        for (const id of presentationIds) {
            await this.downloadPresentation(id);
            // 延迟1秒避免并发过多
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }

    // 检查下载链接是否有效
    async checkDownloadLink(presentationId) {
        try {
            const response = await fetch(
                `${this.generator.apiEndpoint}/download/${presentationId}`,
                {
                    method: 'GET',
                    headers: {
                        'X-API-Key': this.generator.apiKey
                    }
                }
            );

            return response.ok;
        } catch (error) {
            return false;
        }
    }

    // 预下载检查
    async preDownloadCheck(presentationId) {
        // 检查文件是否存在
        const exists = await this.checkDownloadLink(presentationId);

        if (!exists) {
            // 尝试重新生成
            const regenerate = confirm('文件可能已过期，是否重新生成？');
            if (regenerate) {
                // 触发重新生成逻辑
                return false;
            }
        }

        return exists;
    }
}

// 扩展主应用的下载功能
document.addEventListener('DOMContentLoaded', () => {
    // 等待一小段时间确保app.js初始化完成
    setTimeout(() => {
        if (window.pptGenerator) {
            const downloadManager = new DownloadManager(window.pptGenerator);

            window.pptGenerator.downloadPresentation = async function(presentationId) {
                await downloadManager.downloadPresentation(presentationId);
            };

            // 添加拖拽下载功能（可选）
            const resultCard = document.getElementById('resultCard');
            if (resultCard) {
                resultCard.addEventListener('dragstart', (e) => {
                    if (window.pptGenerator.currentPresentationId) {
                        e.dataTransfer.effectAllowed = 'copy';
                        e.dataTransfer.setData('text/plain',
                            `presentation_${window.pptGenerator.currentPresentationId}.pptx`);
                    }
                });
            }
        }
    }, 100);
});