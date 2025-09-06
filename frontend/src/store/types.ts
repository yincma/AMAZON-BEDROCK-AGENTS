// Store types and interfaces
import { Project, UserPreferences, ApiConfig } from '@/types/models';

// Store state interfaces
export interface ProjectStoreState {
  // Data
  projects: Project[];
  currentProject: Project | null;
  recentProjects: Project[];
  
  // UI State
  isLoading: boolean;
  error: string | null;
  searchQuery: string;
  filterStatus: string | null;
  
  // Actions
  loadProjects: () => Promise<void>;
  createProject: (project: Omit<Project, 'id' | 'createdAt' | 'updatedAt'>) => Promise<Project>;
  updateProject: (id: string, updates: Partial<Project>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  setCurrentProject: (project: Project | null) => void;
  searchProjects: (query: string) => void;
  setFilterStatus: (status: string | null) => void;
  clearError: () => void;
}

export interface UIStoreState {
  // Modal states
  modals: {
    createProject: boolean;
    apiConfig: boolean;
    exportData: boolean;
    importData: boolean;
    imageGallery: boolean;
  };
  
  // Loading states
  loadingStates: Map<string, boolean>;
  
  // Notifications
  notifications: Notification[];
  
  // Theme
  theme: 'light' | 'dark' | 'system';
  sidebarCollapsed: boolean;
  
  // Actions
  openModal: (modal: keyof UIStoreState['modals']) => void;
  closeModal: (modal: keyof UIStoreState['modals']) => void;
  setLoading: (key: string, loading: boolean) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSidebar: () => void;
}

export interface EditorStoreState {
  // Editor content
  outline: any[];
  slides: any[];
  currentSlideIndex: number;
  
  // Editor state
  isDirty: boolean;
  isAutoSaving: boolean;
  lastSaved: Date | null;
  
  // Selection
  selectedNodes: string[];
  clipboard: any | null;
  
  // Actions
  setOutline: (outline: any[]) => void;
  updateOutlineNode: (nodeId: string, updates: any) => void;
  addOutlineNode: (parentId: string | null, node: any) => void;
  deleteOutlineNode: (nodeId: string) => void;
  reorderOutlineNodes: (sourceIndex: number, destinationIndex: number) => void;
  
  setSlides: (slides: any[]) => void;
  updateSlide: (slideId: string, updates: any) => void;
  setCurrentSlide: (index: number) => void;
  
  setDirty: (isDirty: boolean) => void;
  saveContent: () => Promise<void>;
  
  selectNode: (nodeId: string, multi?: boolean) => void;
  clearSelection: () => void;
  copySelection: () => void;
  pasteSelection: (parentId?: string) => void;
}

export interface ApiStoreState {
  // Configuration
  config: ApiConfig | null;
  isConfigured: boolean;
  isConnected: boolean;
  
  // Session
  currentSessionId: string | null;
  sessionExpiresAt: Date | null;
  
  // Generation state
  isGenerating: boolean;
  generationProgress: number;
  generationMessage: string;
  
  // Actions
  setConfig: (config: ApiConfig) => void;
  testConnection: () => Promise<boolean>;
  createSession: () => Promise<string>;
  refreshSession: () => Promise<void>;
  endSession: () => Promise<void>;
  
  setGenerationState: (state: {
    isGenerating?: boolean;
    progress?: number;
    message?: string;
  }) => void;
}

// Notification type
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  timestamp: Date;
  action?: {
    label: string;
    onClick: () => void;
  };
}