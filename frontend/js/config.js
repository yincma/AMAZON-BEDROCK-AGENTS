// 统一配置管理中心
class ConfigManager {
    constructor() {
        this.config = this.initializeConfig();
        this.listeners = new Map();
    }

    initializeConfig() {
        // 基础配置（可扩展为环境配置）
        const baseConfig = {
            // AWS API Gateway 端点
            api: {
                endpoint: 'https://fe2kf91287.execute-api.us-east-1.amazonaws.com/dev',
                key: '',
                timeout: 300000 // 5分钟超时
            },

            // 重试配置
            retry: {
                maxAttempts: 3,
                delayMs: 1000,
                backoffMultiplier: 2,
                retryableErrors: ['网络连接错误', '请求超时', 'API 错误: 5']
            },

            // 轮询配置
            polling: {
                intervalMs: 2000,
                maxAttempts: 150, // 5分钟最大轮询时间
                timeoutMs: 300000 // 5分钟超时
            },

            // 默认配置
            defaults: {
                pageCount: 10,
                language: 'zh-CN',
                style: 'consultant' // 咨询顾问风格
            },

            // UI配置
            ui: {
                notificationDuration: 3000,
                animationDuration: 300,
                maxHistoryItems: 10
            }
        };

        // 合并本地存储的配置
        return this.mergeWithStoredConfig(baseConfig);
    }

    mergeWithStoredConfig(baseConfig) {
        // 优先级：localStorage > baseConfig
        const storedEndpoint = localStorage.getItem('apiEndpoint');
        const storedKey = localStorage.getItem('apiKey');

        if (storedEndpoint) {
            baseConfig.api.endpoint = storedEndpoint;
        }

        if (storedKey) {
            baseConfig.api.key = storedKey;
        }

        return baseConfig;
    }

    // 获取配置值
    get(path, defaultValue = null) {
        return this.getNestedValue(this.config, path) || defaultValue;
    }

    // 设置配置值（同时更新localStorage）
    set(path, value) {
        this.setNestedValue(this.config, path, value);

        // 特定配置需要同步到localStorage
        if (path === 'api.endpoint') {
            localStorage.setItem('apiEndpoint', value);
        } else if (path === 'api.key') {
            localStorage.setItem('apiKey', value);
        }

        // 通知配置变更
        this.notifyListeners(path, value);
    }

    // 监听配置变更
    onChange(path, callback) {
        if (!this.listeners.has(path)) {
            this.listeners.set(path, new Set());
        }
        this.listeners.get(path).add(callback);
    }

    // 移除监听器
    off(path, callback) {
        if (this.listeners.has(path)) {
            this.listeners.get(path).delete(callback);
        }
    }

    // 通知监听器
    notifyListeners(path, value) {
        if (this.listeners.has(path)) {
            this.listeners.get(path).forEach(callback => {
                try {
                    callback(value, path);
                } catch (error) {
                    console.error('Config listener error:', error);
                }
            });
        }
    }

    // 获取嵌套值的辅助方法
    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => current?.[key], obj);
    }

    // 设置嵌套值的辅助方法
    setNestedValue(obj, path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        const target = keys.reduce((current, key) => {
            if (!current[key] || typeof current[key] !== 'object') {
                current[key] = {};
            }
            return current[key];
        }, obj);
        target[lastKey] = value;
    }

    // 验证必需配置
    validate() {
        const required = ['api.endpoint'];
        const missing = required.filter(path => !this.get(path));

        if (missing.length > 0) {
            throw new Error(`缺少必需配置: ${missing.join(', ')}`);
        }

        return true;
    }

    // 重置配置
    reset() {
        localStorage.removeItem('apiEndpoint');
        localStorage.removeItem('apiKey');
        this.config = this.initializeConfig();
    }

    // 导出配置（用于调试）
    export() {
        return JSON.stringify(this.config, null, 2);
    }
}

// 创建全局配置管理实例
const configManager = new ConfigManager();

// 辅助函数 - 获取API端点
function getAPIEndpoint() {
    return configManager.get('api.endpoint');
}

// 辅助函数 - 获取API Key
function getAPIKey() {
    return configManager.get('api.key');
}

// 向后兼容的API_CONFIG对象
const API_CONFIG = {
    get endpoint() { return configManager.get('api.endpoint'); },
    get apiKey() { return configManager.get('api.key'); },
    get retry() {
        return {
            ...configManager.get('retry'),
            retryableStatusCodes: [408, 429, 500, 502, 503, 504],
            retryableErrors: ['NetworkError', 'TimeoutError', 'TypeError']
        };
    },
    get polling() { return configManager.get('polling'); },
    get defaults() { return configManager.get('defaults'); },
    // 添加请求配置
    request: {
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    }
};

// 导出配置管理器和兼容API
window.configManager = configManager;
window.API_CONFIG = API_CONFIG;
window.getAPIEndpoint = getAPIEndpoint;
window.getAPIKey = getAPIKey;