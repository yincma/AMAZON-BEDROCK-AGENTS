import { useState, useCallback, useEffect } from 'react';
import { 
  getPresentationApiService, 
  PresentationApiService,
  CreatePresentationRequest,
  PresentationTask,
  PresentationResult,
  ModifySlideRequest,
  Slide,
  Template
} from '@/services/PresentationApiService';

interface UsePresentationApiOptions {
  baseURL?: string;
  apiKey?: string;
  autoInit?: boolean;
}

interface UsePresentationApiReturn {
  // 状态
  loading: boolean;
  error: string | null;
  currentTask: PresentationTask | null;
  presentations: PresentationResult[];
  templates: Template[];
  
  // 方法
  createPresentation: (request: CreatePresentationRequest) => Promise<PresentationTask | null>;
  getTaskStatus: (taskId: string) => Promise<PresentationTask | null>;
  pollTask: (taskId: string, onProgress?: (status: string) => void) => Promise<PresentationTask | null>;
  listPresentations: () => Promise<void>;
  getPresentation: (id: string) => Promise<PresentationResult | null>;
  modifySlide: (presentationId: string, slideData: ModifySlideRequest) => Promise<Slide | null>;
  deletePresentation: (id: string) => Promise<boolean>;
  downloadPresentation: (id: string, format?: 'pptx' | 'pdf') => Promise<void>;
  listTemplates: () => Promise<void>;
  checkHealth: () => Promise<boolean>;
  updateApiKey: (key: string) => void;
  clearError: () => void;
}

/**
 * React Hook for Presentation API
 * 提供与后端 API 交互的便捷方法
 */
export function usePresentationApi(options: UsePresentationApiOptions = {}): UsePresentationApiReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentTask, setCurrentTask] = useState<PresentationTask | null>(null);
  const [presentations, setPresentations] = useState<PresentationResult[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [apiService, setApiService] = useState<PresentationApiService | null>(null);

  // 初始化服务
  useEffect(() => {
    if (options.autoInit !== false) {
      try {
        const service = getPresentationApiService(options.baseURL, options.apiKey);
        setApiService(service);
      } catch (err) {
        setError('无法初始化 API 服务');
        console.error('API 服务初始化失败:', err);
      }
    }
  }, [options.baseURL, options.apiKey, options.autoInit]);

  // 清除错误
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // 创建演示文稿
  const createPresentation = useCallback(async (
    request: CreatePresentationRequest
  ): Promise<PresentationTask | null> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return null;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.createPresentation(request);
      
      if (response.success && response.data) {
        setCurrentTask(response.data);
        return response.data;
      } else {
        setError(response.error?.message || '创建演示文稿失败');
        return null;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '创建演示文稿时发生错误';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  // 获取任务状态
  const getTaskStatus = useCallback(async (taskId: string): Promise<PresentationTask | null> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return null;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.getTaskStatus(taskId);
      
      if (response.success && response.data) {
        setCurrentTask(response.data);
        return response.data;
      } else {
        setError(response.error?.message || '获取任务状态失败');
        return null;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '获取任务状态时发生错误';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  // 轮询任务状态
  const pollTask = useCallback(async (
    taskId: string,
    onProgress?: (status: string) => void
  ): Promise<PresentationTask | null> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return null;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.pollTaskUntilComplete(taskId, {
        maxAttempts: 60,
        interval: 2000,
        onProgress: (status) => {
          if (onProgress) {
            onProgress(status);
          }
          // 更新当前任务状态
          setCurrentTask(prev => prev ? { ...prev, status: status as any } : null);
        }
      });
      
      if (response.success && response.data) {
        setCurrentTask(response.data);
        return response.data;
      } else {
        setError(response.error?.message || '任务执行失败');
        return null;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '轮询任务状态时发生错误';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  // 获取演示文稿列表
  const listPresentations = useCallback(async (): Promise<void> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.listPresentations();
      
      if (response.success && response.data) {
        setPresentations(response.data.presentations || []);
      } else {
        setError(response.error?.message || '获取演示文稿列表失败');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '获取演示文稿列表时发生错误';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  // 获取单个演示文稿
  const getPresentation = useCallback(async (id: string): Promise<PresentationResult | null> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return null;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.getPresentation(id);
      
      if (response.success && response.data) {
        return response.data;
      } else {
        setError(response.error?.message || '获取演示文稿详情失败');
        return null;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '获取演示文稿详情时发生错误';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  // 修改幻灯片
  const modifySlide = useCallback(async (
    presentationId: string,
    slideData: ModifySlideRequest
  ): Promise<Slide | null> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return null;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.modifySlide(presentationId, slideData);
      
      if (response.success && response.data) {
        return response.data;
      } else {
        setError(response.error?.message || '修改幻灯片失败');
        return null;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '修改幻灯片时发生错误';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  // 删除演示文稿
  const deletePresentation = useCallback(async (id: string): Promise<boolean> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return false;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.deletePresentation(id);
      
      if (response.success) {
        // 从本地列表中移除
        setPresentations(prev => prev.filter(p => p.presentation_id !== id));
        return true;
      } else {
        setError(response.error?.message || '删除演示文稿失败');
        return false;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '删除演示文稿时发生错误';
      setError(message);
      return false;
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  // 下载演示文稿
  const downloadPresentation = useCallback(async (
    id: string,
    format: 'pptx' | 'pdf' = 'pptx'
  ): Promise<void> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.downloadPresentation(id, format);
      
      if (!response.success) {
        setError(response.error?.message || '下载演示文稿失败');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '下载演示文稿时发生错误';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  // 获取模板列表
  const listTemplates = useCallback(async (): Promise<void> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.listTemplates();
      
      if (response.success && response.data) {
        setTemplates(response.data);
      } else {
        setError(response.error?.message || '获取模板列表失败');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '获取模板列表时发生错误';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [apiService]);

  // 健康检查
  const checkHealth = useCallback(async (): Promise<boolean> => {
    if (!apiService) {
      setError('API 服务未初始化');
      return false;
    }

    setError(null);
    
    try {
      const response = await apiService.checkHealth();
      
      if (response.success && response.data) {
        return response.data.status === 'healthy';
      } else {
        setError(response.error?.message || '服务健康检查失败');
        return false;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '健康检查时发生错误';
      setError(message);
      return false;
    }
  }, [apiService]);

  // 更新 API 密钥
  const updateApiKey = useCallback((key: string) => {
    if (apiService) {
      apiService.updateApiKey(key);
    } else {
      // 重新初始化服务
      try {
        const service = getPresentationApiService(options.baseURL, key);
        setApiService(service);
      } catch (err) {
        setError('无法更新 API 密钥');
      }
    }
  }, [apiService, options.baseURL]);

  return {
    // 状态
    loading,
    error,
    currentTask,
    presentations,
    templates,
    
    // 方法
    createPresentation,
    getTaskStatus,
    pollTask,
    listPresentations,
    getPresentation,
    modifySlide,
    deletePresentation,
    downloadPresentation,
    listTemplates,
    checkHealth,
    updateApiKey,
    clearError
  };
}

export default usePresentationApi;