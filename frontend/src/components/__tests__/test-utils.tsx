import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { useUIStore, Notification } from '@/store/uiStore';
import { useProjectStore } from '@/store/projectStore';
import { Project, OutlineNode, Slide, ProjectImage, ProjectStatus } from '@/types/models';

// Mock stores
export const mockUIStore = {
  // Modal states
  modals: {
    createProject: false,
    apiConfig: false,
    exportData: false,
    importData: false,
    imageGallery: false,
    deleteConfirm: false,
    settings: false,
  },
  
  // Loading states
  loadingStates: new Map<string, boolean>(),
  globalLoading: false,
  loadingMessage: '',
  
  // Notifications
  notifications: [] as Notification[],
  maxNotifications: 5,
  
  // Theme and preferences
  theme: 'light' as 'light' | 'dark' | 'system',
  sidebarCollapsed: false,
  compactMode: false,
  
  // Toast position
  toastPosition: 'top-right' as 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right',
  
  // Actions - Modals
  openModal: jest.fn(),
  closeModal: jest.fn(),
  closeAllModals: jest.fn(),
  toggleModal: jest.fn(),
  
  // Actions - Loading
  setLoading: jest.fn(),
  setGlobalLoading: jest.fn(),
  isLoading: jest.fn(() => false),
  clearLoading: jest.fn(),
  clearAllLoading: jest.fn(),
  
  // Actions - Notifications
  addNotification: jest.fn().mockReturnValue('mock-id'),
  removeNotification: jest.fn(),
  clearNotifications: jest.fn(),
  clearNotificationsByType: jest.fn(),
  
  // Actions - Success/Error shortcuts
  showSuccess: jest.fn(),
  showError: jest.fn(),
  showWarning: jest.fn(),
  showInfo: jest.fn(),
  
  // Actions - Theme and preferences
  setTheme: jest.fn(),
  toggleSidebar: jest.fn(),
  setCompactMode: jest.fn(),
  setToastPosition: jest.fn(),
  
  // Actions - Utility
  reset: jest.fn(),
};

export const mockProjectStore = {
  projects: [] as Project[],
  currentProject: null as Project | null,
  recentProjects: [] as Project[],
  loadRecentProjects: jest.fn(),
  createProject: jest.fn(),
  updateProject: jest.fn(),
  deleteProject: jest.fn(),
  setCurrentProject: jest.fn(),
  getProject: jest.fn(),
  outlines: [] as OutlineNode[],
  slides: [] as Slide[],
  images: [] as ProjectImage[],
  apiConfig: {
    region: 'us-east-1',
    modelId: 'claude-3-haiku',
    accessKey: '',
    secretKey: '',
  },
  isGenerating: false,
  generateOutline: jest.fn(),
  generateContent: jest.fn(),
  generateSlides: jest.fn(),
  uploadImage: jest.fn(),
  deleteImage: jest.fn(),
  updateProjectOutline: jest.fn(),
  getOutline: jest.fn(),
  updateOutlineNode: jest.fn(),
  deleteOutlineNode: jest.fn(),
  moveOutlineNode: jest.fn(),
  generateSlideContent: jest.fn(),
  updateSlide: jest.fn(),
  deleteSlide: jest.fn(),
  reorderSlides: jest.fn(),
  exportProject: jest.fn(),
  importProject: jest.fn(),
  validateApiConfig: jest.fn(),
  updateApiConfig: jest.fn(),
};

// Mock store modules
jest.mock('@/store/uiStore', () => ({
  useUIStore: jest.fn(),
}));

jest.mock('@/store/projectStore', () => ({
  useProjectStore: jest.fn(),
}));

// Setup default mocks
beforeEach(() => {
  (useUIStore as unknown as jest.Mock).mockReturnValue(mockUIStore);
  (useProjectStore as unknown as jest.Mock).mockReturnValue(mockProjectStore);
  
  // Reset all mocks
  jest.clearAllMocks();
});

// Custom render function
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  uiStoreProps?: Partial<typeof mockUIStore>;
  projectStoreProps?: Partial<typeof mockProjectStore>;
}

export function customRender(
  ui: ReactElement,
  options: CustomRenderOptions = {}
): ReturnType<typeof render> {
  const { uiStoreProps = {}, projectStoreProps = {}, ...renderOptions } = options;

  // Override store mocks with custom props
  (useUIStore as unknown as jest.Mock).mockReturnValue({
    ...mockUIStore,
    ...uiStoreProps,
  });

  (useProjectStore as unknown as jest.Mock).mockReturnValue({
    ...mockProjectStore,
    ...projectStoreProps,
  });

  return render(ui, renderOptions);
}

// Mock data factories
export const createMockProject = (overrides = {}) => ({
  id: 'test-project-id',
  title: 'Test Project',
  description: 'Test project description',
  createdAt: '2024-01-01T00:00:00.000Z',
  updatedAt: '2024-01-01T00:00:00.000Z',
  status: ProjectStatus.DRAFT,
  settings: {
    language: 'zh-CN' as const,
    slideCount: 10,
    includeImages: true,
    template: 'business' as const,
  },
  ...overrides,
});

export const createMockOutline = (overrides = {}) => ({
  id: 'test-outline-id',
  projectId: 'test-project-id',
  title: 'Test Outline',
  content: 'Test outline content',
  sections: [
    { id: '1', title: '引言', content: '这是引言部分', order: 0 },
    { id: '2', title: '主体', content: '这是主体部分', order: 1 },
    { id: '3', title: '结论', content: '这是结论部分', order: 2 },
  ],
  createdAt: '2024-01-01T00:00:00.000Z',
  updatedAt: '2024-01-01T00:00:00.000Z',
  ...overrides,
});

export const createMockSlide = (overrides = {}) => ({
  id: 'test-slide-id',
  projectId: 'test-project-id',
  title: 'Test Slide',
  content: 'Test slide content',
  order: 0,
  layout: 'title-content' as const,
  background: '#ffffff',
  images: [],
  createdAt: '2024-01-01T00:00:00.000Z',
  updatedAt: '2024-01-01T00:00:00.000Z',
  ...overrides,
});

export const createMockImage = (overrides = {}) => ({
  id: 'test-image-id',
  projectId: 'test-project-id',
  filename: 'test-image.jpg',
  url: 'https://example.com/test-image.jpg',
  size: 1024000,
  type: 'image/jpeg',
  thumbnailUrl: 'https://example.com/test-image-thumb.jpg',
  tags: ['test', 'image'],
  uploadedAt: '2024-01-01T00:00:00.000Z',
  ...overrides,
});

export const createMockNotification = (overrides = {}) => ({
  id: 'test-notification-id',
  type: 'success' as 'success' | 'error' | 'warning' | 'info',
  title: 'Test Notification',
  message: 'This is a test notification',
  duration: 5000,
  timestamp: new Date(),
  ...overrides,
});

// Export everything needed for tests
export * from '@testing-library/react';
export { customRender as render };
export { default as userEvent } from '@testing-library/user-event';