// API request and response type definitions

import { Project, OutlineNode, Slide, Session, Image } from './models';

// Base API response structure
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  metadata?: ResponseMetadata;
}

// API error structure
export interface ApiError {
  code: string;
  message: string;
  details?: any;
  timestamp?: string;
  traceId?: string;
}

// Response metadata
export interface ResponseMetadata {
  requestId?: string;
  timestamp?: string;
  duration?: number; // in milliseconds
  version?: string;
}

// Pagination
export interface PaginationParams {
  page: number;
  pageSize: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    pageSize: number;
    totalPages: number;
    totalItems: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

// Session API
export interface CreateSessionRequest {
  projectId?: string;
  metadata?: Record<string, any>;
}

export interface CreateSessionResponse {
  sessionId: string;
  expiresAt: string;
}

export interface GetSessionRequest {
  sessionId: string;
}

export interface GetSessionResponse extends Session {}

// Outline API
export interface CreateOutlineRequest {
  sessionId: string;
  topic: string;
  slidesCount: number;
  language?: 'zh' | 'en';
  tone?: string;
  targetAudience?: string;
  additionalContext?: string;
}

export interface CreateOutlineResponse {
  outline: OutlineNode[];
  suggestedTitle?: string;
  keywords?: string[];
}

export interface UpdateOutlineRequest {
  sessionId: string;
  outline: OutlineNode[];
}

export interface UpdateOutlineResponse {
  outline: OutlineNode[];
  status: 'updated' | 'validated';
}

// Content Enhancement API
export interface EnhanceContentRequest {
  sessionId: string;
  content: string;
  type: 'title' | 'paragraph' | 'bullet_points';
  context?: string;
  maxLength?: number;
  tone?: string;
}

export interface EnhanceContentResponse {
  enhancedContent: string;
  suggestions?: string[];
  confidence?: number;
}

export interface BatchEnhanceContentRequest {
  sessionId: string;
  items: Array<{
    id: string;
    content: string;
    type: string;
  }>;
}

export interface BatchEnhanceContentResponse {
  items: Array<{
    id: string;
    originalContent: string;
    enhancedContent: string;
  }>;
}

// PPT Generation API
export interface GeneratePptRequest {
  sessionId: string;
  projectId: string;
  outline: OutlineNode[];
  slides?: Slide[];
  theme: string;
  includeImages: boolean;
  format?: 'pptx' | 'pdf' | 'both';
}

export interface GeneratePptResponse {
  fileUrl: string;
  downloadUrl: string;
  previewUrl?: string;
  expiresAt: string;
  metadata: {
    fileSize: number;
    slideCount: number;
    format: string;
    generatedAt: string;
  };
}

export interface GeneratePptProgress {
  sessionId: string;
  status: 'queued' | 'processing' | 'generating' | 'completed' | 'failed';
  progress: number; // 0-100
  currentStep?: string;
  estimatedTimeRemaining?: number; // in seconds
}

// Image Search API
export interface SearchImagesRequest {
  query: string;
  count?: number;
  safeSearch?: boolean;
  license?: 'all' | 'creative_commons' | 'commercial';
  orientation?: 'landscape' | 'portrait' | 'square';
}

export interface SearchImagesResponse {
  images: Image[];
  totalResults: number;
  query: string;
}

// Project API (local storage)
export interface SaveProjectRequest {
  project: Omit<Project, 'id' | 'createdAt' | 'updatedAt'>;
}

export interface SaveProjectResponse {
  project: Project;
}

export interface GetProjectRequest {
  projectId: string;
}

export interface GetProjectResponse {
  project: Project;
}

export interface ListProjectsRequest extends PaginationParams {
  searchQuery?: string;
  status?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface ListProjectsResponse extends PaginatedResponse<Project> {}

export interface DeleteProjectRequest {
  projectId: string;
}

export interface DeleteProjectResponse {
  success: boolean;
  projectId: string;
}

// Export/Import API
export interface ExportProjectRequest {
  projectId: string;
  format: 'json' | 'yaml' | 'markdown';
  includeImages?: boolean;
}

export interface ExportProjectResponse {
  data: string | Blob;
  filename: string;
  mimeType: string;
}

export interface ImportProjectRequest {
  file: File;
  format: 'json' | 'yaml' | 'markdown';
}

export interface ImportProjectResponse {
  project: Project;
  warnings?: string[];
}

// Health Check API
export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  services: {
    api: boolean;
    database?: boolean;
    storage?: boolean;
    ai?: boolean;
  };
}

// WebSocket events for real-time updates
export interface WebSocketEvent {
  type: 'progress' | 'error' | 'complete' | 'update';
  sessionId: string;
  data: any;
  timestamp: string;
}

// Request configuration
export interface RequestConfig {
  headers?: Record<string, string>;
  timeout?: number;
  retryCount?: number;
  retryDelay?: number;
  signal?: AbortSignal;
}

// API method types
export type ApiMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

// Generic API request interface
export interface ApiRequest<T = any> {
  url: string;
  method: ApiMethod;
  data?: T;
  params?: Record<string, any>;
  config?: RequestConfig;
}