// Project related types
export interface Project {
  id: string;
  title: string;
  description?: string;
  topic?: string;
  status: ProjectStatus;
  settings: ProjectSettings;
  outline?: OutlineNode[];
  slides?: Slide[];
  createdAt: string;
  updatedAt: string;
}

export enum ProjectStatus {
  DRAFT = 'draft',
  OUTLINE_READY = 'outline_ready',
  CONTENT_READY = 'content_ready',
  GENERATING = 'generating',
  COMPLETED = 'completed',
  ERROR = 'error',
}

export interface ProjectSettings {
  language: 'zh-CN' | 'en-US';
  slideCount?: number;
  slidesCount?: number;
  includeImages: boolean;
  template: 'business' | 'academic' | 'creative';
}

// Outline related types
export interface OutlineNode {
  id: string;
  title: string;
  content: string;
  level: number;
  children: OutlineNode[];
}

// Slide related types
export interface Slide {
  id: string;
  projectId: string;
  title: string;
  subtitle?: string;
  content: SlideContent;
  layout: SlideLayout;
  order: number;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface SlideContent {
  text?: string;
  bullets?: string[];
  image?: SlideImage;
  chart?: SlideChart;
}

export interface SlideImage {
  url: string;
  alt?: string;
  caption?: string;
}

export interface SlideChart {
  type: 'bar' | 'line' | 'pie' | 'scatter';
  title?: string;
  data: any[];
}

export type SlideLayout = 'title-content' | 'content-image' | 'chart' | 'bullets' | 'full-image';

// Image related types
export interface ProjectImage {
  id: string;
  projectId: string;
  filename: string;
  url: string;
  thumbnailUrl?: string;
  size: number;
  type: string;
  tags: string[];
  uploadedAt: string;
}

// For compatibility with existing code
export interface Image extends ProjectImage {}

// User preferences
export interface UserPreferences {
  language: 'zh-CN' | 'en-US';
  theme: 'light' | 'dark' | 'system';
  autoSave: boolean;
  notifications: boolean;
}