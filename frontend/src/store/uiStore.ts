import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { v4 as uuidv4 } from 'uuid';

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

interface UIState {
  // Modal states
  modals: {
    createProject: boolean;
    apiConfig: boolean;
    exportData: boolean;
    importData: boolean;
    imageGallery: boolean;
    deleteConfirm: boolean;
    settings: boolean;
  };
  
  // Loading states
  loadingStates: Map<string, boolean>;
  globalLoading: boolean;
  loadingMessage: string;
  
  // Notifications
  notifications: Notification[];
  maxNotifications: number;
  
  // Theme and preferences
  theme: 'light' | 'dark' | 'system';
  sidebarCollapsed: boolean;
  compactMode: boolean;
  language: 'zh' | 'en';
  
  // Page title
  pageTitle: string;
  
  // Toast position
  toastPosition: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  
  // Actions - Modals
  openModal: (modal: keyof UIState['modals']) => void;
  closeModal: (modal: keyof UIState['modals']) => void;
  closeAllModals: () => void;
  toggleModal: (modal: keyof UIState['modals']) => void;
  
  // Actions - Loading
  setLoading: (key: string, loading: boolean, message?: string) => void;
  setGlobalLoading: (loading: boolean, message?: string) => void;
  isLoading: (key?: string) => boolean;
  clearLoading: (key?: string) => void;
  clearAllLoading: () => void;
  
  // Actions - Notifications
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => string;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  clearNotificationsByType: (type: Notification['type']) => void;
  
  // Actions - Success/Error shortcuts
  showSuccess: (title: string, message?: string) => void;
  showError: (title: string, message?: string) => void;
  showWarning: (title: string, message?: string) => void;
  showInfo: (title: string, message?: string) => void;
  
  // Actions - Theme and preferences
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSidebar: () => void;
  setCompactMode: (compact: boolean) => void;
  setToastPosition: (position: UIState['toastPosition']) => void;
  setPageTitle: (title: string) => void;
  setLanguage: (language: 'zh' | 'en') => void;
  
  // Actions - Utility
  reset: () => void;
}

// Initial state
const initialState = {
  modals: {
    createProject: false,
    apiConfig: false,
    exportData: false,
    importData: false,
    imageGallery: false,
    deleteConfirm: false,
    settings: false,
  },
  loadingStates: new Map<string, boolean>(),
  globalLoading: false,
  loadingMessage: '',
  notifications: [] as Notification[],
  maxNotifications: 5,
  theme: 'system' as const,
  sidebarCollapsed: false,
  compactMode: false,
  language: 'zh' as const,
  pageTitle: '',
  toastPosition: 'top-right' as const,
};

// Create the store
export const useUIStore = create<UIState>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,
        
        // Modal actions
        openModal: (modal) => {
          set(state => {
            state.modals[modal] = true;
          });
        },
        
        closeModal: (modal) => {
          set(state => {
            state.modals[modal] = false;
          });
        },
        
        closeAllModals: () => {
          set(state => {
            Object.keys(state.modals).forEach(key => {
              state.modals[key as keyof UIState['modals']] = false;
            });
          });
        },
        
        toggleModal: (modal) => {
          set(state => {
            state.modals[modal] = !state.modals[modal];
          });
        },
        
        // Loading actions
        setLoading: (key, loading, message) => {
          set(state => {
            if (loading) {
              state.loadingStates.set(key, true);
              if (message && key === 'global') {
                state.loadingMessage = message;
              }
            } else {
              state.loadingStates.delete(key);
              if (key === 'global') {
                state.loadingMessage = '';
              }
            }
          });
        },
        
        setGlobalLoading: (loading, message) => {
          set(state => {
            state.globalLoading = loading;
            state.loadingMessage = message || '';
          });
        },
        
        isLoading: (key) => {
          const state = get();
          if (key) {
            return state.loadingStates.has(key);
          }
          return state.globalLoading || state.loadingStates.size > 0;
        },
        
        clearLoading: (key) => {
          set(state => {
            if (key) {
              state.loadingStates.delete(key);
            } else {
              state.globalLoading = false;
              state.loadingMessage = '';
            }
          });
        },
        
        clearAllLoading: () => {
          set(state => {
            state.loadingStates.clear();
            state.globalLoading = false;
            state.loadingMessage = '';
          });
        },
        
        // Notification actions
        addNotification: (notification) => {
          const id = uuidv4();
          const newNotification: Notification = {
            ...notification,
            id,
            timestamp: new Date(),
            duration: notification.duration ?? 5000,
          };
          
          set(state => {
            state.notifications.unshift(newNotification);
            
            // Limit notifications
            if (state.notifications.length > state.maxNotifications) {
              state.notifications = state.notifications.slice(0, state.maxNotifications);
            }
          });
          
          // Auto-remove after duration
          if (newNotification.duration && newNotification.duration > 0) {
            setTimeout(() => {
              get().removeNotification(id);
            }, newNotification.duration);
          }
          
          return id;
        },
        
        removeNotification: (id) => {
          set(state => {
            state.notifications = state.notifications.filter(n => n.id !== id);
          });
        },
        
        clearNotifications: () => {
          set(state => {
            state.notifications = [];
          });
        },
        
        clearNotificationsByType: (type) => {
          set(state => {
            state.notifications = state.notifications.filter(n => n.type !== type);
          });
        },
        
        // Success/Error shortcuts
        showSuccess: (title, message) => {
          get().addNotification({
            type: 'success',
            title,
            message,
          });
        },
        
        showError: (title, message) => {
          get().addNotification({
            type: 'error',
            title,
            message,
            duration: 10000, // Errors stay longer
          });
        },
        
        showWarning: (title, message) => {
          get().addNotification({
            type: 'warning',
            title,
            message,
            duration: 7000,
          });
        },
        
        showInfo: (title, message) => {
          get().addNotification({
            type: 'info',
            title,
            message,
          });
        },
        
        // Theme and preferences
        setTheme: (theme) => {
          set(state => {
            state.theme = theme;
          });
          
          // Apply theme to document
          const root = document.documentElement;
          if (theme === 'dark') {
            root.classList.add('dark');
          } else if (theme === 'light') {
            root.classList.remove('dark');
          } else {
            // System preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDark) {
              root.classList.add('dark');
            } else {
              root.classList.remove('dark');
            }
          }
        },
        
        toggleSidebar: () => {
          set(state => {
            state.sidebarCollapsed = !state.sidebarCollapsed;
          });
        },
        
        setCompactMode: (compact) => {
          set(state => {
            state.compactMode = compact;
          });
        },
        
        setToastPosition: (position) => {
          set(state => {
            state.toastPosition = position;
          });
        },
        
        setPageTitle: (title) => {
          set(state => {
            state.pageTitle = title;
          });
          // Update document title
          document.title = title ? `${title} - PPT Assistant` : 'PPT Assistant';
        },
        
        setLanguage: (language) => {
          set(state => {
            state.language = language;
          });
        },
        
        // Reset
        reset: () => {
          set(state => ({
            ...initialState,
            theme: state.theme, // Preserve theme preference
            language: state.language, // Preserve language preference
            toastPosition: state.toastPosition, // Preserve toast position
          }));
        },
      })),
      {
        name: 'ui-store',
        partialize: (state) => ({
          theme: state.theme,
          sidebarCollapsed: state.sidebarCollapsed,
          compactMode: state.compactMode,
          language: state.language,
          toastPosition: state.toastPosition,
        }),
      }
    ),
    {
      name: 'UIStore',
    }
  )
);

// Selector hooks
export const useModals = () => useUIStore(state => state.modals);
export const useNotifications = () => useUIStore(state => state.notifications);
export const useTheme = () => useUIStore(state => state.theme);
export const useIsLoading = (key?: string) => useUIStore(state => state.isLoading(key));
export const useSidebarCollapsed = () => useUIStore(state => state.sidebarCollapsed);

// Helper functions
export const showToast = {
  success: (title: string, message?: string) => useUIStore.getState().showSuccess(title, message),
  error: (title: string, message?: string) => useUIStore.getState().showError(title, message),
  warning: (title: string, message?: string) => useUIStore.getState().showWarning(title, message),
  info: (title: string, message?: string) => useUIStore.getState().showInfo(title, message),
};