// API 配置文件
const API_CONFIG = {
    // AWS API Gateway 端点
    endpoint: 'https://n1s8cxndac.execute-api.us-east-1.amazonaws.com/dev',

    // API Key (如果需要的话)
    apiKey: '',

    // 默认配置
    defaults: {
        pageCount: 10,
        language: 'zh-CN',
        style: 'consultant' // 咨询顾问风格
    }
};

// 自动加载配置到localStorage（如果还没有设置）
if (!localStorage.getItem('apiEndpoint')) {
    localStorage.setItem('apiEndpoint', API_CONFIG.endpoint);
}

// 导出配置
window.API_CONFIG = API_CONFIG;