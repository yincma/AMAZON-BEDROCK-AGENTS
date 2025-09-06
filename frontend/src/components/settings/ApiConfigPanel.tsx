import React, { useState, useEffect } from 'react';
import { ApiService, apiService } from '@/services/ApiService';
import { AwsApiGatewayService, getAwsApiGatewayService } from '@/services/AwsApiGatewayService';
import { useUIStore } from '@/store/uiStore';
import {
  Settings,
  Server,
  Key,
  Save,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  XCircle,
  Eye,
  EyeOff,
  Copy,
  Info,
  Shield,
  Zap,
  Globe,
  Clock,
  HelpCircle,
} from 'lucide-react';

interface ApiConfigPanelProps {
  onClose?: () => void;
  onSave?: (config: ApiConfig) => void;
}

interface ApiConfig {
  baseUrl: string;
  apiKey: string;
  timeout: number;
  retryAttempts: number;
  enableCache: boolean;
  cacheTimeout: number;
  enableCompression: boolean;
  maxConcurrentRequests: number;
  customHeaders: Record<string, string>;
}

interface ConnectionStatus {
  isConnected: boolean;
  message: string;
  responseTime?: number;
  lastChecked?: Date;
}

const ApiConfigPanel: React.FC<ApiConfigPanelProps> = ({
  onClose,
  onSave,
}) => {
  const { showSuccess, showError, showWarning } = useUIStore();
  
  // Load saved config from localStorage
  const loadConfig = (): ApiConfig => {
    const saved = localStorage.getItem('api-config');
    if (saved) {
      return JSON.parse(saved);
    }
    return {
      baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
      apiKey: '',
      timeout: 30000,
      retryAttempts: 3,
      enableCache: true,
      cacheTimeout: 300000, // 5 minutes
      enableCompression: true,
      maxConcurrentRequests: 5,
      customHeaders: {},
    };
  };
  
  const [config, setConfig] = useState<ApiConfig>(loadConfig());
  const [showApiKey, setShowApiKey] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    isConnected: false,
    message: '未测试',
  });
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customHeaderKey, setCustomHeaderKey] = useState('');
  const [customHeaderValue, setCustomHeaderValue] = useState('');

  // Detect changes
  useEffect(() => {
    const savedConfig = loadConfig();
    setHasChanges(JSON.stringify(config) !== JSON.stringify(savedConfig));
  }, [config]);

  // Test connection
  const testConnection = async () => {
    setIsTesting(true);
    
    try {
      // 检测是否是AWS API Gateway URL
      const isAwsApiGateway = config.baseUrl.includes('execute-api') && 
                              config.baseUrl.includes('amazonaws.com');
      
      let result;
      
      if (isAwsApiGateway) {
        // 使用AWS专用服务
        const awsService = getAwsApiGatewayService(config.baseUrl, config.apiKey);
        result = await awsService.healthCheck();
        
        // 如果是认证问题，提供更详细的指导
        if (!result.success && result.error?.includes('API密钥')) {
          setConnectionStatus({
            isConnected: false,
            message: 'AWS API Gateway需要认证',
            responseTime: result.responseTime,
            lastChecked: new Date(),
          });
          showWarning('需要API密钥', '请在下方输入AWS API Gateway的API密钥（x-api-key）');
          return;
        }
      } else {
        // 使用通用API服务
        const testApiService = new ApiService({
          baseURL: config.baseUrl,
          timeout: config.timeout || 5000,
          headers: {
            ...(config.apiKey && { 'Authorization': `Bearer ${config.apiKey}` }),
            ...config.customHeaders,
          },
        });
        
        result = await testApiService.healthCheck();
      }
      
      if (result.success) {
        setConnectionStatus({
          isConnected: true,
          message: '连接成功',
          responseTime: result.responseTime,
          lastChecked: new Date(),
        });
        showSuccess('连接成功', `响应时间: ${result.responseTime}ms`);
      } else {
        setConnectionStatus({
          isConnected: false,
          message: result.error || '连接失败: 服务器无响应',
          lastChecked: new Date(),
        });
        showError('连接失败', result.error || '服务器无响应');
      }
    } catch (error) {
      setConnectionStatus({
        isConnected: false,
        message: `连接错误: ${error instanceof Error ? error.message : '未知错误'}`,
        lastChecked: new Date(),
      });
      showError('连接错误', '无法连接到API服务器');
    } finally {
      setIsTesting(false);
    }
  };

  // Save configuration
  const handleSave = () => {
    setIsSaving(true);
    
    // Validate config
    if (!config.baseUrl) {
      showError('配置错误', 'API地址不能为空');
      setIsSaving(false);
      return;
    }
    
    if (config.timeout < 1000 || config.timeout > 300000) {
      showError('配置错误', '超时时间必须在1-300秒之间');
      setIsSaving(false);
      return;
    }
    
    if (config.retryAttempts < 0 || config.retryAttempts > 10) {
      showError('配置错误', '重试次数必须在0-10次之间');
      setIsSaving(false);
      return;
    }
    
    // Save to localStorage
    localStorage.setItem('api-config', JSON.stringify(config));
    
    // 检测是否是AWS API Gateway
    const isAwsApiGateway = config.baseUrl.includes('execute-api') && 
                            config.baseUrl.includes('amazonaws.com');
    
    if (isAwsApiGateway) {
      // 为AWS API Gateway更新配置
      // 注意：AWS使用x-api-key头而不是Authorization头
      apiService.updateConfig({
        baseURL: config.baseUrl,
        timeout: config.timeout,
        headers: {
          ...(config.apiKey && { 'x-api-key': config.apiKey }),
          ...config.customHeaders,
        },
      });
    } else {
      // 为普通API更新配置
      apiService.updateConfig({
        baseURL: config.baseUrl,
        timeout: config.timeout,
        headers: {
          ...(config.apiKey && { 'Authorization': `Bearer ${config.apiKey}` }),
          ...config.customHeaders,
        },
      });
    }
    
    showSuccess('保存成功', 'API配置已更新');
    setHasChanges(false);
    setIsSaving(false);
    
    onSave?.(config);
  };

  // Reset to defaults
  const handleReset = () => {
    if (window.confirm('确定要重置为默认配置吗？')) {
      const defaultConfig: ApiConfig = {
        baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
        apiKey: '',
        timeout: 30000,
        retryAttempts: 3,
        enableCache: true,
        cacheTimeout: 300000,
        enableCompression: true,
        maxConcurrentRequests: 5,
        customHeaders: {},
      };
      setConfig(defaultConfig);
      showSuccess('重置成功', '配置已重置为默认值');
    }
  };

  // Add custom header
  const addCustomHeader = () => {
    if (customHeaderKey && customHeaderValue) {
      setConfig(prev => ({
        ...prev,
        customHeaders: {
          ...prev.customHeaders,
          [customHeaderKey]: customHeaderValue,
        },
      }));
      setCustomHeaderKey('');
      setCustomHeaderValue('');
    }
  };

  // Remove custom header
  const removeCustomHeader = (key: string) => {
    setConfig(prev => {
      const headers = { ...prev.customHeaders };
      delete headers[key];
      return {
        ...prev,
        customHeaders: headers,
      };
    });
  };

  // Copy API key
  const copyApiKey = () => {
    if (config.apiKey) {
      navigator.clipboard.writeText(config.apiKey);
      showSuccess('复制成功', 'API密钥已复制到剪贴板');
    }
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-secondary-800 rounded-lg shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-secondary-200 dark:border-secondary-700">
        <div className="flex items-center gap-3">
          <Settings className="w-6 h-6 text-primary-500" />
          <h2 className="text-xl font-semibold text-secondary-900 dark:text-white">
            API 配置
          </h2>
        </div>
        
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded-lg transition-colors"
          >
            <XCircle className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Connection Status - 更大更明显的测试区域 */}
        <div className="mb-6 p-6 bg-secondary-50 dark:bg-secondary-700 rounded-lg border-2 border-secondary-200 dark:border-secondary-600">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`w-4 h-4 rounded-full ${
                connectionStatus.isConnected
                  ? 'bg-green-500 animate-pulse'
                  : connectionStatus.message === '未测试' 
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
              }`} />
              <div>
                <h3 className="font-semibold text-lg text-secondary-900 dark:text-white">
                  API 连接状态
                </h3>
                <p className="text-sm text-secondary-600 dark:text-secondary-400">
                  {connectionStatus.isConnected 
                    ? '已连接' 
                    : connectionStatus.message === '未测试' 
                      ? '尚未测试连接' 
                      : '连接失败'}
                </p>
              </div>
            </div>
          </div>
          
          {/* 大型测试按钮 */}
          <button
            onClick={testConnection}
            disabled={isTesting || !config.baseUrl}
            className={`
              w-full flex items-center justify-center gap-3 px-6 py-3 
              text-lg font-medium rounded-lg transition-all
              ${!config.baseUrl 
                ? 'bg-secondary-200 dark:bg-secondary-600 text-secondary-400 cursor-not-allowed'
                : isTesting
                  ? 'bg-primary-400 text-white cursor-wait'
                  : connectionStatus.isConnected
                    ? 'bg-green-500 hover:bg-green-600 text-white'
                    : 'bg-primary-500 hover:bg-primary-600 text-white shadow-lg hover:shadow-xl'
              }
            `}
          >
            {isTesting ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>测试中...</span>
              </>
            ) : connectionStatus.isConnected ? (
              <>
                <CheckCircle className="w-5 h-5" />
                <span>重新测试连接</span>
              </>
            ) : (
              <>
                <Zap className="w-5 h-5" />
                <span>测试 API 连接</span>
              </>
            )}
          </button>
          
          {/* 状态详情 */}
          {connectionStatus.message !== '未测试' && (
            <div className="mt-4 p-3 bg-white dark:bg-secondary-800 rounded-lg">
              <div className="flex items-start gap-2">
                {connectionStatus.isConnected ? (
                  <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-medium text-secondary-900 dark:text-white">
                    {connectionStatus.message}
                  </p>
                  {connectionStatus.responseTime !== undefined && (
                    <p className="text-xs text-secondary-500 mt-1">
                      响应时间: {connectionStatus.responseTime}ms
                    </p>
                  )}
                  {connectionStatus.lastChecked && (
                    <p className="text-xs text-secondary-500">
                      测试时间: {new Date(connectionStatus.lastChecked).toLocaleString('zh-CN')}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
          
          {/* 提示信息 */}
          {!config.baseUrl && (
            <div className="mt-3 p-2 bg-amber-100 dark:bg-amber-900/20 rounded-lg">
              <p className="text-xs text-amber-800 dark:text-amber-400 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                请先输入API地址后再测试连接
              </p>
            </div>
          )}
        </div>

        {/* Basic Configuration */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-secondary-900 dark:text-white mb-4">
            基本配置
          </h3>
          
          {/* API Base URL */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
              <Server className="w-4 h-4" />
              API 地址
            </label>
            <div className="relative">
              <input
                type="text"
                value={config.baseUrl}
                onChange={(e) => setConfig(prev => ({ ...prev, baseUrl: e.target.value }))}
                placeholder="https://api.example.com"
                className="w-full px-4 py-2 bg-secondary-50 dark:bg-secondary-700 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                <select
                  onChange={(e) => {
                    if (e.target.value) {
                      setConfig(prev => ({ ...prev, baseUrl: e.target.value }));
                      e.target.value = '';
                    }
                  }}
                  className="text-xs px-2 py-1 bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 rounded cursor-pointer hover:bg-primary-200 dark:hover:bg-primary-900/30"
                  value=""
                >
                  <option value="">快速填充</option>
                  <option value="http://localhost:8000">本地开发 (8000)</option>
                  <option value="http://localhost:3000">本地开发 (3000)</option>
                  <option value="https://jsonplaceholder.typicode.com">测试API (JSONPlaceholder)</option>
                  <option value="https://api.github.com">GitHub API</option>
                  <option value="https://your-api-gateway.amazonaws.com/prod">AWS API Gateway</option>
                </select>
              </div>
            </div>
            <p className="text-xs text-secondary-500 mt-1">
              PPT生成服务的API端点地址，可选择示例地址快速测试
            </p>
          </div>
          
          {/* API Key */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
              <Key className="w-4 h-4" />
              API 密钥
              {config.baseUrl.includes('execute-api') && config.baseUrl.includes('amazonaws.com') && (
                <span className="text-xs bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 px-2 py-0.5 rounded">
                  AWS必需
                </span>
              )}
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={config.apiKey}
                  onChange={(e) => setConfig(prev => ({ ...prev, apiKey: e.target.value }))}
                  placeholder={
                    config.baseUrl.includes('execute-api') && config.baseUrl.includes('amazonaws.com')
                      ? "输入AWS API Gateway密钥 (x-api-key)"
                      : "输入API密钥（可选）"
                  }
                  className="w-full px-4 py-2 pr-20 bg-secondary-50 dark:bg-secondary-700 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex gap-1">
                  <button
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="p-1 hover:bg-secondary-200 dark:hover:bg-secondary-600 rounded"
                  >
                    {showApiKey ? (
                      <EyeOff className="w-4 h-4 text-secondary-500" />
                    ) : (
                      <Eye className="w-4 h-4 text-secondary-500" />
                    )}
                  </button>
                  <button
                    onClick={copyApiKey}
                    className="p-1 hover:bg-secondary-200 dark:hover:bg-secondary-600 rounded"
                  >
                    <Copy className="w-4 h-4 text-secondary-500" />
                  </button>
                </div>
              </div>
            </div>
            {config.baseUrl.includes('execute-api') && config.baseUrl.includes('amazonaws.com') ? (
              <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-xs text-blue-700 dark:text-blue-400">
                  <Info className="inline w-3 h-3 mr-1" />
                  AWS API Gateway需要x-api-key头。请输入您从AWS控制台获取的API密钥。
                </p>
              </div>
            ) : (
              <p className="text-xs text-secondary-500 mt-1">
                如果API需要认证，请输入密钥
              </p>
            )}
          </div>
          
          {/* Timeout */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
              <Clock className="w-4 h-4" />
              请求超时（毫秒）
            </label>
            <input
              type="number"
              value={config.timeout}
              onChange={(e) => setConfig(prev => ({ ...prev, timeout: parseInt(e.target.value) || 30000 }))}
              min="1000"
              max="300000"
              step="1000"
              className="w-full px-4 py-2 bg-secondary-50 dark:bg-secondary-700 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <p className="text-xs text-secondary-500 mt-1">
              请求超时时间（1-300秒）
            </p>
          </div>
        </div>

        {/* Advanced Configuration */}
        <div className="mt-6">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm font-medium text-primary-500 hover:text-primary-600"
          >
            <Settings className="w-4 h-4" />
            {showAdvanced ? '隐藏' : '显示'}高级配置
          </button>
          
          {showAdvanced && (
            <div className="mt-4 space-y-4 p-4 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
              {/* Retry Attempts */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                  <RefreshCw className="w-4 h-4" />
                  重试次数
                </label>
                <input
                  type="number"
                  value={config.retryAttempts}
                  onChange={(e) => setConfig(prev => ({ ...prev, retryAttempts: parseInt(e.target.value) || 3 }))}
                  min="0"
                  max="10"
                  className="w-full px-4 py-2 bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              
              {/* Cache Settings */}
              <div>
                <label className="flex items-center gap-2 mb-2">
                  <input
                    type="checkbox"
                    checked={config.enableCache}
                    onChange={(e) => setConfig(prev => ({ ...prev, enableCache: e.target.checked }))}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-secondary-700 dark:text-secondary-300">
                    启用缓存
                  </span>
                </label>
                {config.enableCache && (
                  <input
                    type="number"
                    value={config.cacheTimeout}
                    onChange={(e) => setConfig(prev => ({ ...prev, cacheTimeout: parseInt(e.target.value) || 300000 }))}
                    min="60000"
                    max="3600000"
                    step="60000"
                    className="w-full px-4 py-2 bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="缓存超时时间（毫秒）"
                  />
                )}
              </div>
              
              {/* Compression */}
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config.enableCompression}
                    onChange={(e) => setConfig(prev => ({ ...prev, enableCompression: e.target.checked }))}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-secondary-700 dark:text-secondary-300">
                    启用压缩
                  </span>
                </label>
              </div>
              
              {/* Max Concurrent Requests */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                  <Zap className="w-4 h-4" />
                  最大并发请求数
                </label>
                <input
                  type="number"
                  value={config.maxConcurrentRequests}
                  onChange={(e) => setConfig(prev => ({ ...prev, maxConcurrentRequests: parseInt(e.target.value) || 5 }))}
                  min="1"
                  max="20"
                  className="w-full px-4 py-2 bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              
              {/* Custom Headers */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                  <Globe className="w-4 h-4" />
                  自定义请求头
                </label>
                <div className="space-y-2">
                  {Object.entries(config.customHeaders).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-2">
                      <span className="flex-1 px-3 py-2 bg-white dark:bg-secondary-800 rounded-lg text-sm">
                        {key}: {value}
                      </span>
                      <button
                        onClick={() => removeCustomHeader(key)}
                        className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={customHeaderKey}
                      onChange={(e) => setCustomHeaderKey(e.target.value)}
                      placeholder="Header名称"
                      className="flex-1 px-3 py-2 bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <input
                      type="text"
                      value={customHeaderValue}
                      onChange={(e) => setCustomHeaderValue(e.target.value)}
                      placeholder="Header值"
                      className="flex-1 px-3 py-2 bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <button
                      onClick={addCustomHeader}
                      disabled={!customHeaderKey || !customHeaderValue}
                      className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50"
                    >
                      添加
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Security Notice */}
        <div className="mt-6 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
          <div className="flex items-start gap-2">
            <Shield className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-800 dark:text-amber-300">
              <p className="font-medium mb-1">安全提示</p>
              <ul className="list-disc list-inside space-y-1 text-xs">
                <li>请勿在公共场合暴露API密钥</li>
                <li>定期更换API密钥以保证安全</li>
                <li>使用HTTPS协议进行加密传输</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-6 py-4 border-t border-secondary-200 dark:border-secondary-700">
        <button
          onClick={handleReset}
          className="text-sm text-secondary-600 dark:text-secondary-400 hover:text-secondary-800 dark:hover:text-secondary-200"
        >
          重置为默认
        </button>
        
        <div className="flex items-center gap-3">
          {hasChanges && (
            <span className="text-sm text-amber-600 dark:text-amber-400">
              <AlertCircle className="inline w-4 h-4 mr-1" />
              有未保存的更改
            </span>
          )}
          
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {isSaving ? '保存中...' : '保存配置'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ApiConfigPanel;