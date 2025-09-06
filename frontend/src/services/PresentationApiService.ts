import { getAwsApiGatewayService } from './AwsApiGatewayService';
import { ApiResponse } from '@/types/api';

// 接口定义
export interface CreatePresentationRequest {
  title: string;
  topic: string;
  language?: string;
  slide_count?: number;
  style?: 'corporate' | 'modern' | 'creative' | 'minimal';
  template?: string;
  audience_type?: string;
  tone?: string;
  include_speaker_notes?: boolean;
  color_scheme?: string;
}

export interface PresentationTask {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at?: string;
  result?: PresentationResult;
  error?: string;
}

export interface PresentationResult {
  presentation_id: string;
  title: string;
  slides: Slide[];
  download_url?: string;
  metadata?: {
    total_slides: number;
    language: string;
    style: string;
    created_at: string;
  };
}

export interface Slide {
  slide_id: string;
  slide_number: number;
  title: string;
  content: string;
  speaker_notes?: string;
  layout?: string;
  images?: string[];
}

export interface ModifySlideRequest {
  slide_number: number;
  title?: string;
  content?: string;
  speaker_notes?: string;
  layout?: string;
}

export interface Template {
  template_id: string;
  name: string;
  description: string;
  category: string;
  preview_url?: string;
  style: string;
  default_slide_count: number;
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  version: string;
  timestamp: string;
  services?: {
    bedrock: boolean;
    s3: boolean;
    dynamodb: boolean;
  };
}

/**
 * Presentation API 服务类
 * 处理与后端 Lambda 函数的所有交互
 */
export class PresentationApiService {
  private apiService: ReturnType<typeof getAwsApiGatewayService>;

  constructor(baseURL: string, apiKey?: string) {
    this.apiService = getAwsApiGatewayService(baseURL, apiKey);
  }

  /**
   * 创建新的演示文稿
   */
  async createPresentation(request: CreatePresentationRequest): Promise<ApiResponse<PresentationTask>> {
    try {
      const response = await this.apiService.post<PresentationTask>('/presentations', request);
      
      if (response.success && response.data) {
        console.log('[PresentationAPI] 创建任务成功:', response.data.task_id);
        return response;
      }
      
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 创建演示文稿失败:', error);
      return {
        success: false,
        error: {
          code: 'CREATE_FAILED',
          message: '创建演示文稿失败，请稍后重试',
          details: error
        }
      };
    }
  }

  /**
   * 获取任务状态
   */
  async getTaskStatus(taskId: string): Promise<ApiResponse<PresentationTask>> {
    try {
      const response = await this.apiService.get<PresentationTask>(`/tasks/${taskId}`);
      
      if (response.success && response.data) {
        console.log('[PresentationAPI] 任务状态:', response.data.status);
        return response;
      }
      
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 获取任务状态失败:', error);
      return {
        success: false,
        error: {
          code: 'STATUS_FAILED',
          message: '获取任务状态失败',
          details: error
        }
      };
    }
  }

  /**
   * 轮询任务状态直到完成
   */
  async pollTaskUntilComplete(
    taskId: string,
    options: {
      maxAttempts?: number;
      interval?: number;
      onProgress?: (status: string) => void;
    } = {}
  ): Promise<ApiResponse<PresentationTask>> {
    const maxAttempts = options.maxAttempts || 60;
    const interval = options.interval || 2000;
    let attempts = 0;

    return new Promise((resolve) => {
      const checkStatus = async () => {
        attempts++;
        
        const response = await this.getTaskStatus(taskId);
        
        if (!response.success) {
          resolve(response);
          return;
        }

        const task = response.data!;
        
        if (options.onProgress) {
          options.onProgress(task.status);
        }

        if (task.status === 'completed' || task.status === 'failed') {
          resolve(response);
          return;
        }

        if (attempts >= maxAttempts) {
          resolve({
            success: false,
            error: {
              code: 'TIMEOUT',
              message: '任务执行超时，请稍后查看结果'
            }
          });
          return;
        }

        setTimeout(checkStatus, interval);
      };

      checkStatus();
    });
  }

  /**
   * 获取演示文稿列表
   */
  async listPresentations(params?: {
    page_size?: number;
    page_token?: string;
    status?: 'completed' | 'processing' | 'failed';
    created_after?: string;
  }): Promise<ApiResponse<{
    presentations: PresentationResult[];
    next_page_token?: string;
  }>> {
    try {
      const response = await this.apiService.get('/presentations', { params });
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 获取演示文稿列表失败:', error);
      return {
        success: false,
        error: {
          code: 'LIST_FAILED',
          message: '获取演示文稿列表失败',
          details: error
        }
      };
    }
  }

  /**
   * 获取单个演示文稿详情
   */
  async getPresentation(presentationId: string): Promise<ApiResponse<PresentationResult>> {
    try {
      const response = await this.apiService.get<PresentationResult>(`/presentations/${presentationId}`);
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 获取演示文稿详情失败:', error);
      return {
        success: false,
        error: {
          code: 'GET_FAILED',
          message: '获取演示文稿详情失败',
          details: error
        }
      };
    }
  }

  /**
   * 修改演示文稿幻灯片
   */
  async modifySlide(
    presentationId: string,
    slideRequest: ModifySlideRequest
  ): Promise<ApiResponse<Slide>> {
    try {
      const response = await this.apiService.put<Slide>(
        `/presentations/${presentationId}/slides`,
        slideRequest
      );
      
      if (response.success) {
        console.log('[PresentationAPI] 幻灯片修改成功');
      }
      
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 修改幻灯片失败:', error);
      return {
        success: false,
        error: {
          code: 'MODIFY_FAILED',
          message: '修改幻灯片失败',
          details: error
        }
      };
    }
  }

  /**
   * 删除演示文稿
   */
  async deletePresentation(presentationId: string): Promise<ApiResponse<void>> {
    try {
      const response = await this.apiService.delete<void>(`/presentations/${presentationId}`);
      
      if (response.success) {
        console.log('[PresentationAPI] 演示文稿删除成功');
      }
      
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 删除演示文稿失败:', error);
      return {
        success: false,
        error: {
          code: 'DELETE_FAILED',
          message: '删除演示文稿失败',
          details: error
        }
      };
    }
  }

  /**
   * 下载演示文稿
   */
  async downloadPresentation(
    presentationId: string,
    format: 'pptx' | 'pdf' = 'pptx'
  ): Promise<ApiResponse<{ download_url: string }>> {
    try {
      const response = await this.apiService.get<{ download_url: string }>(
        `/presentations/${presentationId}/download`,
        { params: { format } }
      );
      
      if (response.success && response.data) {
        console.log('[PresentationAPI] 获取下载链接成功');
        
        // 直接下载文件
        if (response.data.download_url) {
          window.open(response.data.download_url, '_blank');
        }
      }
      
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 下载演示文稿失败:', error);
      return {
        success: false,
        error: {
          code: 'DOWNLOAD_FAILED',
          message: '下载演示文稿失败',
          details: error
        }
      };
    }
  }

  /**
   * 获取模板列表
   */
  async listTemplates(params?: {
    category?: string;
    style?: string;
  }): Promise<ApiResponse<Template[]>> {
    try {
      const response = await this.apiService.get<Template[]>('/templates', { params });
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 获取模板列表失败:', error);
      return {
        success: false,
        error: {
          code: 'TEMPLATES_FAILED',
          message: '获取模板列表失败',
          details: error
        }
      };
    }
  }

  /**
   * 获取单个模板详情
   */
  async getTemplate(templateId: string): Promise<ApiResponse<Template>> {
    try {
      const response = await this.apiService.get<Template>(`/templates/${templateId}`);
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 获取模板详情失败:', error);
      return {
        success: false,
        error: {
          code: 'TEMPLATE_FAILED',
          message: '获取模板详情失败',
          details: error
        }
      };
    }
  }

  /**
   * 健康检查
   */
  async checkHealth(): Promise<ApiResponse<HealthStatus>> {
    try {
      const response = await this.apiService.get<HealthStatus>('/health');
      
      if (response.success && response.data) {
        console.log('[PresentationAPI] 服务健康状态:', response.data.status);
      }
      
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 健康检查失败:', error);
      return {
        success: false,
        error: {
          code: 'HEALTH_CHECK_FAILED',
          message: '服务健康检查失败',
          details: error
        }
      };
    }
  }

  /**
   * 就绪检查
   */
  async checkReady(): Promise<ApiResponse<{ ready: boolean; message: string }>> {
    try {
      const response = await this.apiService.get<{ ready: boolean; message: string }>('/health/ready');
      return response;
    } catch (error) {
      console.error('[PresentationAPI] 就绪检查失败:', error);
      return {
        success: false,
        error: {
          code: 'READY_CHECK_FAILED',
          message: '服务就绪检查失败',
          details: error
        }
      };
    }
  }

  /**
   * 更新 API 密钥
   */
  updateApiKey(apiKey: string): void {
    this.apiService.updateApiKey(apiKey);
  }
}

// 导出单例工厂函数
let presentationApiService: PresentationApiService | null = null;

export const getPresentationApiService = (baseURL?: string, apiKey?: string): PresentationApiService => {
  const url = baseURL || import.meta.env.VITE_API_BASE_URL;
  const key = apiKey || import.meta.env.VITE_API_KEY;
  
  if (!presentationApiService && url) {
    presentationApiService = new PresentationApiService(url, key);
  } else if (presentationApiService && baseURL && baseURL !== url) {
    // URL 改变，创建新实例
    presentationApiService = new PresentationApiService(baseURL, apiKey);
  } else if (presentationApiService && apiKey) {
    // 更新 API 密钥
    presentationApiService.updateApiKey(apiKey);
  }
  
  if (!presentationApiService) {
    throw new Error('Presentation API 服务未初始化');
  }
  
  return presentationApiService;
};

export default PresentationApiService;