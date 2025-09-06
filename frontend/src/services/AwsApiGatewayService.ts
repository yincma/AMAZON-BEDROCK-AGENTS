import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { ApiResponse, ApiError } from '@/types/api';

/**
 * AWS API Gateway专用服务类
 * 处理AWS特有的认证和请求配置
 */
export class AwsApiGatewayService {
  private axiosInstance: AxiosInstance;
  private apiKey: string = '';
  private baseURL: string;

  constructor(baseURL: string, apiKey?: string) {
    this.baseURL = baseURL;
    this.apiKey = apiKey || '';

    // 创建axios实例
    this.axiosInstance = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: this.getDefaultHeaders(),
    });

    this.setupInterceptors();
  }

  /**
   * 获取默认请求头
   */
  private getDefaultHeaders() {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    // 添加API密钥（如果有）
    if (this.apiKey) {
      // AWS API Gateway通常使用x-api-key头
      headers['x-api-key'] = this.apiKey;
    }

    return headers;
  }

  /**
   * 设置拦截器
   */
  private setupInterceptors(): void {
    // 请求拦截器
    this.axiosInstance.interceptors.request.use(
      (config) => {
        // 确保API密钥始终存在
        if (this.apiKey && config.headers) {
          config.headers['x-api-key'] = this.apiKey;
        }

        // 添加时间戳防止缓存
        if (config.method === 'get') {
          config.params = {
            ...config.params,
            _t: Date.now(),
          };
        }

        // 开发环境日志
        if (import.meta.env.DEV) {
          console.log(`[AWS API] ${config.method?.toUpperCase()} ${config.url}`, {
            headers: config.headers,
            data: config.data,
          });
        }

        return config;
      },
      (error) => {
        console.error('[AWS API Request Error]', error);
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.axiosInstance.interceptors.response.use(
      (response) => {
        if (import.meta.env.DEV) {
          console.log(`[AWS API Response] ${response.config.url}`, response.data);
        }
        return response;
      },
      async (error) => {
        if (import.meta.env.DEV) {
          console.error('[AWS API Response Error]', {
            url: error.config?.url,
            status: error.response?.status,
            data: error.response?.data,
            message: error.message,
          });
        }

        // 处理特定的AWS错误
        if (error.response) {
          const { status, data } = error.response;
          
          if (status === 403 && data?.message?.includes('Missing Authentication Token')) {
            console.error('AWS API Gateway认证失败：缺少认证令牌。请检查API密钥配置。');
          } else if (status === 403 && data?.message?.includes('Forbidden')) {
            console.error('AWS API Gateway访问被拒绝：API密钥可能无效或没有权限。');
          }
        }

        return Promise.reject(error);
      }
    );
  }

  /**
   * 更新API密钥
   */
  public updateApiKey(apiKey: string): void {
    this.apiKey = apiKey;
    this.axiosInstance.defaults.headers['x-api-key'] = apiKey;
  }

  /**
   * 健康检查 - 专门为AWS API Gateway优化
   */
  public async healthCheck(): Promise<{ success: boolean; responseTime?: number; error?: string }> {
    const startTime = Date.now();
    
    // AWS API Gateway的常见端点
    const endpoints = [
      '/health',
      '/ping',
      '/status',
      '/',
      '/api/health',
      '/api/ping',
      '/api/status',
    ];

    for (const endpoint of endpoints) {
      try {
        const response = await this.axiosInstance.get(endpoint, {
          timeout: 5000,
          validateStatus: (status) => {
            // 接受2xx和4xx作为"成功"（API可达）
            return status < 500;
          },
        });

        const responseTime = Date.now() - startTime;

        // 如果收到403错误，说明API可达但需要认证
        if (response.status === 403) {
          const errorMessage = response.data?.message || '';
          if (errorMessage.includes('Missing Authentication Token')) {
            return {
              success: false,
              responseTime,
              error: '需要API密钥认证。请在下方输入有效的API密钥。',
            };
          } else if (errorMessage.includes('Forbidden')) {
            return {
              success: false,
              responseTime,
              error: 'API密钥无效或没有权限。请检查API密钥是否正确。',
            };
          }
        }

        // 如果收到2xx响应，说明连接成功
        if (response.status >= 200 && response.status < 300) {
          return {
            success: true,
            responseTime,
          };
        }

        // 404可能意味着端点不存在，继续尝试其他端点
        if (response.status === 404) {
          continue;
        }

        // 其他4xx错误
        return {
          success: false,
          responseTime,
          error: `API返回错误状态: ${response.status} - ${response.data?.message || response.statusText}`,
        };
      } catch (error) {
        // 网络错误或超时，继续尝试下一个端点
        if (axios.isAxiosError(error) && !error.response) {
          continue;
        }
        // 其他错误，继续尝试
        continue;
      }
    }

    // 如果所有端点都失败，返回错误
    return {
      success: false,
      error: '无法连接到API。请检查API地址是否正确，或联系管理员。',
    };
  }

  /**
   * 通用请求方法
   */
  public async request<T>(
    method: 'get' | 'post' | 'put' | 'delete' | 'patch',
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.axiosInstance.request<T>({
        method,
        url,
        data,
        ...config,
      });

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const apiError: ApiError = {
          code: error.response?.status?.toString() || 'NETWORK_ERROR',
          message: error.response?.data?.message || error.message || '请求失败',
          details: error.response?.data,
        };
        return {
          success: false,
          error: apiError,
        };
      }

      return {
        success: false,
        error: {
          code: 'UNKNOWN_ERROR',
          message: '未知错误',
        },
      };
    }
  }

  // 便捷方法
  public get<T>(url: string, config?: AxiosRequestConfig) {
    return this.request<T>('get', url, undefined, config);
  }

  public post<T>(url: string, data?: any, config?: AxiosRequestConfig) {
    return this.request<T>('post', url, data, config);
  }

  public put<T>(url: string, data?: any, config?: AxiosRequestConfig) {
    return this.request<T>('put', url, data, config);
  }

  public delete<T>(url: string, config?: AxiosRequestConfig) {
    return this.request<T>('delete', url, undefined, config);
  }

  public patch<T>(url: string, data?: any, config?: AxiosRequestConfig) {
    return this.request<T>('patch', url, data, config);
  }
}

// 导出单例
let awsApiGatewayService: AwsApiGatewayService | null = null;

export const getAwsApiGatewayService = (baseURL?: string, apiKey?: string): AwsApiGatewayService => {
  if (!awsApiGatewayService && baseURL) {
    awsApiGatewayService = new AwsApiGatewayService(baseURL, apiKey);
  } else if (awsApiGatewayService && baseURL && baseURL !== awsApiGatewayService['baseURL']) {
    // 如果URL改变了，创建新实例
    awsApiGatewayService = new AwsApiGatewayService(baseURL, apiKey);
  } else if (awsApiGatewayService && apiKey) {
    // 更新API密钥
    awsApiGatewayService.updateApiKey(apiKey);
  }
  
  if (!awsApiGatewayService) {
    throw new Error('AWS API Gateway服务未初始化');
  }
  
  return awsApiGatewayService;
};

export default AwsApiGatewayService;