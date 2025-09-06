import ApiService from './ApiService';
import {
  CreateOutlineRequest,
  CreateOutlineResponse,
  UpdateOutlineRequest,
  UpdateOutlineResponse,
  EnhanceContentRequest,
  EnhanceContentResponse,
  BatchEnhanceContentRequest,
  BatchEnhanceContentResponse,
  GeneratePptRequest,
  GeneratePptResponse,
  GeneratePptProgress,
  CreateSessionRequest,
  CreateSessionResponse,
  GetSessionRequest,
  GetSessionResponse,
  ApiResponse,
} from '@/types/api';
import { OutlineNode, Slide } from '@/types/models';

// Event types for progress tracking
export enum PptServiceEvent {
  SESSION_CREATED = 'session_created',
  OUTLINE_STARTED = 'outline_started',
  OUTLINE_COMPLETED = 'outline_completed',
  CONTENT_ENHANCEMENT_STARTED = 'content_enhancement_started',
  CONTENT_ENHANCEMENT_PROGRESS = 'content_enhancement_progress',
  CONTENT_ENHANCEMENT_COMPLETED = 'content_enhancement_completed',
  PPT_GENERATION_STARTED = 'ppt_generation_started',
  PPT_GENERATION_PROGRESS = 'ppt_generation_progress',
  PPT_GENERATION_COMPLETED = 'ppt_generation_completed',
  ERROR = 'error',
}

// Progress event data
export interface ProgressEventData {
  type: PptServiceEvent;
  progress?: number;
  message?: string;
  data?: any;
  error?: Error;
}

/**
 * PPT Generation Service
 * Handles all PPT-related API operations
 */
export class PptService extends ApiService {
  private currentSessionId: string | null = null;
  private eventListeners: Map<PptServiceEvent, Set<(data: ProgressEventData) => void>> = new Map();
  private progressCheckInterval: NodeJS.Timeout | null = null;

  constructor() {
    super();
  }

  /**
   * Event listener management
   */
  addEventListener(event: PptServiceEvent, listener: (data: ProgressEventData) => void): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)?.add(listener);
  }

  removeEventListener(event: PptServiceEvent, listener: (data: ProgressEventData) => void): void {
    this.eventListeners.get(event)?.delete(listener);
  }

  private emitEvent(event: PptServiceEvent, data?: Partial<ProgressEventData>): void {
    const eventData: ProgressEventData = {
      type: event,
      ...data,
    };
    this.eventListeners.get(event)?.forEach(listener => listener(eventData));
  }

  /**
   * Session management
   */
  async createSession(projectId?: string): Promise<ApiResponse<CreateSessionResponse>> {
    try {
      const request: CreateSessionRequest = {
        projectId,
        metadata: {
          clientVersion: '1.0.0',
          timestamp: new Date().toISOString(),
        },
      };

      const response = await this.post<CreateSessionResponse>('/sessions', request);
      
      if (response.success && response.data) {
        this.currentSessionId = response.data.sessionId;
        this.emitEvent(PptServiceEvent.SESSION_CREATED, {
          data: response.data,
        });
      }

      return response;
    } catch (error) {
      this.emitEvent(PptServiceEvent.ERROR, {
        error: error as Error,
        message: 'Failed to create session',
      });
      throw error;
    }
  }

  async getSession(sessionId: string): Promise<ApiResponse<GetSessionResponse>> {
    return this.get<GetSessionResponse>(`/sessions/${sessionId}`);
  }

  getCurrentSessionId(): string | null {
    return this.currentSessionId;
  }

  setCurrentSessionId(sessionId: string): void {
    this.currentSessionId = sessionId;
  }

  /**
   * Outline operations
   */
  async createOutline(
    topic: string,
    slidesCount: number,
    options?: {
      language?: 'zh' | 'en';
      tone?: string;
      targetAudience?: string;
      additionalContext?: string;
    }
  ): Promise<ApiResponse<CreateOutlineResponse>> {
    try {
      if (!this.currentSessionId) {
        const sessionResponse = await this.createSession();
        if (!sessionResponse.success) {
          throw new Error('Failed to create session');
        }
      }

      this.emitEvent(PptServiceEvent.OUTLINE_STARTED, {
        message: 'Creating outline...',
      });

      const request: CreateOutlineRequest = {
        sessionId: this.currentSessionId!,
        topic,
        slidesCount,
        ...options,
      };

      const response = await this.post<CreateOutlineResponse>('/outlines/create', request);

      if (response.success) {
        this.emitEvent(PptServiceEvent.OUTLINE_COMPLETED, {
          data: response.data,
          message: 'Outline created successfully',
        });
      } else {
        this.emitEvent(PptServiceEvent.ERROR, {
          error: new Error(response.error?.message || 'Failed to create outline'),
        });
      }

      return response;
    } catch (error) {
      this.emitEvent(PptServiceEvent.ERROR, {
        error: error as Error,
        message: 'Failed to create outline',
      });
      throw error;
    }
  }

  async updateOutline(outline: OutlineNode[]): Promise<ApiResponse<UpdateOutlineResponse>> {
    if (!this.currentSessionId) {
      throw new Error('No active session');
    }

    const request: UpdateOutlineRequest = {
      sessionId: this.currentSessionId,
      outline,
    };

    return this.put<UpdateOutlineResponse>('/outlines/update', request);
  }

  /**
   * Content enhancement operations
   */
  async enhanceContent(
    content: string,
    type: 'title' | 'paragraph' | 'bullet_points',
    options?: {
      context?: string;
      maxLength?: number;
      tone?: string;
    }
  ): Promise<ApiResponse<EnhanceContentResponse>> {
    if (!this.currentSessionId) {
      throw new Error('No active session');
    }

    const request: EnhanceContentRequest = {
      sessionId: this.currentSessionId,
      content,
      type,
      ...options,
    };

    return this.post<EnhanceContentResponse>('/content/enhance', request);
  }

  async batchEnhanceContent(
    items: Array<{
      id: string;
      content: string;
      type: string;
    }>
  ): Promise<ApiResponse<BatchEnhanceContentResponse>> {
    try {
      if (!this.currentSessionId) {
        throw new Error('No active session');
      }

      this.emitEvent(PptServiceEvent.CONTENT_ENHANCEMENT_STARTED, {
        message: `Enhancing ${items.length} items...`,
        progress: 0,
      });

      const request: BatchEnhanceContentRequest = {
        sessionId: this.currentSessionId,
        items,
      };

      // Simulate progress updates for batch enhancement
      const totalItems = items.length;
      let processedItems = 0;

      const progressInterval = setInterval(() => {
        processedItems = Math.min(processedItems + 1, totalItems - 1);
        const progress = (processedItems / totalItems) * 100;
        
        this.emitEvent(PptServiceEvent.CONTENT_ENHANCEMENT_PROGRESS, {
          progress,
          message: `Processing item ${processedItems}/${totalItems}`,
        });
      }, 500);

      const response = await this.post<BatchEnhanceContentResponse>('/content/enhance-batch', request);

      clearInterval(progressInterval);

      if (response.success) {
        this.emitEvent(PptServiceEvent.CONTENT_ENHANCEMENT_COMPLETED, {
          progress: 100,
          data: response.data,
          message: 'Content enhancement completed',
        });
      } else {
        this.emitEvent(PptServiceEvent.ERROR, {
          error: new Error(response.error?.message || 'Failed to enhance content'),
        });
      }

      return response;
    } catch (error) {
      this.emitEvent(PptServiceEvent.ERROR, {
        error: error as Error,
        message: 'Failed to enhance content',
      });
      throw error;
    }
  }

  /**
   * PPT generation operations
   */
  async generatePpt(
    projectId: string,
    outline: OutlineNode[],
    options?: {
      slides?: Slide[];
      theme?: string;
      includeImages?: boolean;
      format?: 'pptx' | 'pdf' | 'both';
    }
  ): Promise<ApiResponse<GeneratePptResponse>> {
    try {
      if (!this.currentSessionId) {
        throw new Error('No active session');
      }

      this.emitEvent(PptServiceEvent.PPT_GENERATION_STARTED, {
        message: 'Starting PPT generation...',
        progress: 0,
      });

      const request: GeneratePptRequest = {
        sessionId: this.currentSessionId,
        projectId,
        outline,
        theme: options?.theme || 'professional',
        includeImages: options?.includeImages ?? true,
        format: options?.format || 'pptx',
        ...options,
      };

      // Start progress polling
      this.startProgressPolling();

      const response = await this.post<GeneratePptResponse>('/ppt/generate', request);

      // Stop progress polling
      this.stopProgressPolling();

      if (response.success) {
        this.emitEvent(PptServiceEvent.PPT_GENERATION_COMPLETED, {
          progress: 100,
          data: response.data,
          message: 'PPT generated successfully',
        });
      } else {
        this.emitEvent(PptServiceEvent.ERROR, {
          error: new Error(response.error?.message || 'Failed to generate PPT'),
        });
      }

      return response;
    } catch (error) {
      this.stopProgressPolling();
      this.emitEvent(PptServiceEvent.ERROR, {
        error: error as Error,
        message: 'Failed to generate PPT',
      });
      throw error;
    }
  }

  /**
   * Get PPT generation progress
   */
  async getGenerationProgress(): Promise<ApiResponse<GeneratePptProgress>> {
    if (!this.currentSessionId) {
      throw new Error('No active session');
    }

    return this.get<GeneratePptProgress>(`/ppt/progress/${this.currentSessionId}`);
  }

  /**
   * Progress polling for long-running operations
   */
  private startProgressPolling(): void {
    this.stopProgressPolling(); // Clear any existing interval

    this.progressCheckInterval = setInterval(async () => {
      try {
        const progressResponse = await this.getGenerationProgress();
        
        if (progressResponse.success && progressResponse.data) {
          const { status, progress, currentStep, estimatedTimeRemaining } = progressResponse.data;
          
          this.emitEvent(PptServiceEvent.PPT_GENERATION_PROGRESS, {
            progress,
            message: currentStep,
            data: {
              status,
              estimatedTimeRemaining,
            },
          });

          // Stop polling if generation is complete or failed
          if (status === 'completed' || status === 'failed') {
            this.stopProgressPolling();
          }
        }
      } catch (error) {
        console.error('Failed to check progress:', error);
      }
    }, 2000); // Poll every 2 seconds
  }

  private stopProgressPolling(): void {
    if (this.progressCheckInterval) {
      clearInterval(this.progressCheckInterval);
      this.progressCheckInterval = null;
    }
  }

  /**
   * Cancel current PPT generation
   */
  async cancelGeneration(): Promise<void> {
    if (!this.currentSessionId) {
      return;
    }

    this.stopProgressPolling();
    await this.delete(`/ppt/cancel/${this.currentSessionId}`);
    
    this.emitEvent(PptServiceEvent.PPT_GENERATION_COMPLETED, {
      message: 'Generation cancelled',
      data: { cancelled: true },
    });
  }

  /**
   * Download generated PPT
   */
  async downloadPpt(downloadUrl: string): Promise<Blob> {
    const response = await fetch(downloadUrl);
    
    if (!response.ok) {
      throw new Error(`Failed to download PPT: ${response.statusText}`);
    }
    
    return response.blob();
  }

  /**
   * Clean up resources
   */
  dispose(): void {
    this.stopProgressPolling();
    this.eventListeners.clear();
    this.currentSessionId = null;
    this.cancelAllRequests();
  }
}

// Export singleton instance
export const pptService = new PptService();

export default PptService;