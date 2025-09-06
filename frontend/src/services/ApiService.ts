import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { 
  ApiResponse, 
  ApiError, 
  RequestConfig,
  ApiMethod 
} from '@/types/api';
import { API_BASE_URL, API_TIMEOUT } from '@/utils/constants';

// Default configuration
const DEFAULT_CONFIG: AxiosRequestConfig = {
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
};

// Retry configuration
const RETRY_CONFIG = {
  maxRetries: 3,
  retryDelay: 1000, // 1 second
  retryableStatuses: [408, 429, 500, 502, 503, 504],
};

/**
 * Base API Service class
 * Provides common HTTP operations with error handling and retry logic
 */
export class ApiService {
  private axiosInstance: AxiosInstance;
  private abortControllers: Map<string, AbortController> = new Map();

  constructor(config?: AxiosRequestConfig) {
    this.axiosInstance = axios.create({
      ...DEFAULT_CONFIG,
      ...config,
    });

    this.setupInterceptors();
  }

  /**
   * Setup request and response interceptors
   */
  private setupInterceptors(): void {
    // Request interceptor
    this.axiosInstance.interceptors.request.use(
      (config) => {
        // Add timestamp to requests
        config.headers['X-Request-Time'] = new Date().toISOString();
        
        // Add API key if available
        const apiKey = this.getApiKey();
        if (apiKey) {
          config.headers['X-API-Key'] = apiKey;
        }

        // Log request in development
        if (import.meta.env.DEV) {
          console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data);
        }

        return config;
      },
      (error) => {
        console.error('[API Request Error]', error);
        return Promise.reject(this.handleError(error));
      }
    );

    // Response interceptor
    this.axiosInstance.interceptors.response.use(
      (response) => {
        // Log response in development
        if (import.meta.env.DEV) {
          console.log(`[API Response] ${response.config.url}`, response.data);
        }
        return response;
      },
      async (error) => {
        const originalRequest = error.config;

        // Check if retry is needed
        if (
          error.response &&
          RETRY_CONFIG.retryableStatuses.includes(error.response.status) &&
          !originalRequest._retry &&
          originalRequest._retryCount < RETRY_CONFIG.maxRetries
        ) {
          originalRequest._retry = true;
          originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;

          // Wait before retry
          await this.delay(RETRY_CONFIG.retryDelay * originalRequest._retryCount);

          if (import.meta.env.DEV) {
            console.log(`[API Retry] Attempt ${originalRequest._retryCount} for ${originalRequest.url}`);
          }

          return this.axiosInstance(originalRequest);
        }

        console.error('[API Response Error]', error);
        return Promise.reject(this.handleError(error));
      }
    );
  }

  /**
   * Get API key from storage or environment
   */
  private getApiKey(): string | null {
    // Try to get from localStorage first
    const storedConfig = localStorage.getItem('ppt-assistant-api-config');
    if (storedConfig) {
      try {
        const config = JSON.parse(storedConfig);
        if (config.apiKey) return config.apiKey;
      } catch (e) {
        console.error('Failed to parse API config', e);
      }
    }
    
    // Fall back to environment variable
    return import.meta.env.VITE_API_KEY || null;
  }

  /**
   * Handle and format errors
   */
  private handleError(error: AxiosError | Error): ApiError {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<any>;
      
      // Network error
      if (!axiosError.response) {
        return {
          code: 'NETWORK_ERROR',
          message: error.message || 'Network connection failed',
          details: { originalError: error },
        };
      }

      // API error response
      const { status, data } = axiosError.response;
      return {
        code: data?.code || `HTTP_${status}`,
        message: data?.message || this.getHttpErrorMessage(status),
        details: data?.details || { status, data },
        timestamp: new Date().toISOString(),
      };
    }

    // Generic error
    return {
      code: 'UNKNOWN_ERROR',
      message: error.message || 'An unexpected error occurred',
      details: { originalError: error },
    };
  }

  /**
   * Get human-readable HTTP error message
   */
  private getHttpErrorMessage(status: number): string {
    const messages: Record<number, string> = {
      400: 'Bad request',
      401: 'Unauthorized',
      403: 'Forbidden',
      404: 'Resource not found',
      408: 'Request timeout',
      429: 'Too many requests',
      500: 'Internal server error',
      502: 'Bad gateway',
      503: 'Service unavailable',
      504: 'Gateway timeout',
    };
    return messages[status] || `HTTP error ${status}`;
  }

  /**
   * Delay helper for retries
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Generic request method
   */
  protected async request<T>(
    method: ApiMethod,
    url: string,
    data?: any,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      // Create abort controller for this request
      const abortController = new AbortController();
      const requestId = `${method}-${url}-${Date.now()}`;
      this.abortControllers.set(requestId, abortController);

      const response = await this.axiosInstance.request<T>({
        method,
        url,
        data,
        params: config?.params,
        headers: config?.headers,
        timeout: config?.timeout,
        signal: config?.signal || abortController.signal,
        _retryCount: 0,
      } as AxiosRequestConfig);

      // Clean up abort controller
      this.abortControllers.delete(requestId);

      return {
        success: true,
        data: response.data,
        metadata: {
          requestId,
          timestamp: new Date().toISOString(),
          duration: response.headers['x-response-time'] 
            ? parseInt(response.headers['x-response-time']) 
            : undefined,
        },
      };
    } catch (error) {
      return {
        success: false,
        error: this.handleError(error as Error),
      };
    }
  }

  /**
   * HTTP method shortcuts
   */
  async get<T>(url: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('GET', url, undefined, config);
  }

  async post<T>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('POST', url, data, config);
  }

  async put<T>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', url, data, config);
  }

  async delete<T>(url: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', url, undefined, config);
  }

  async patch<T>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('PATCH', url, data, config);
  }

  /**
   * Cancel a specific request
   */
  cancelRequest(requestId: string): void {
    const controller = this.abortControllers.get(requestId);
    if (controller) {
      controller.abort();
      this.abortControllers.delete(requestId);
    }
  }

  /**
   * Cancel all pending requests
   */
  cancelAllRequests(): void {
    this.abortControllers.forEach(controller => controller.abort());
    this.abortControllers.clear();
  }

  /**
   * Update base configuration
   */
  updateConfig(config: Partial<AxiosRequestConfig>): void {
    Object.assign(this.axiosInstance.defaults, config);
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ success: boolean; responseTime?: number; error?: string }> {
    const startTime = Date.now();
    try {
      // Try common health check endpoints
      const endpoints = ['/health', '/api/health', '/ping', '/api/ping', '/status', '/'];
      
      for (const endpoint of endpoints) {
        try {
          const response = await this.get(endpoint, { timeout: 5000 });
          if (response.success) {
            return {
              success: true,
              responseTime: Date.now() - startTime,
            };
          }
        } catch {
          // Try next endpoint
          continue;
        }
      }
      
      // If no endpoint works, try a simple OPTIONS request to the base URL
      try {
        await this.axiosInstance.request({
          method: 'OPTIONS',
          url: '/',
          timeout: 5000,
        });
        return {
          success: true,
          responseTime: Date.now() - startTime,
        };
      } catch {
        // Continue to return false
      }
      
      return {
        success: false,
        error: 'No valid health check endpoint found',
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Health check failed',
      };
    }
  }

  /**
   * Static method to update global configuration
   */
  static setGlobalConfig(config: Partial<AxiosRequestConfig>): void {
    apiService.updateConfig(config);
  }
}

// Export singleton instance
export const apiService = new ApiService();

export default ApiService;