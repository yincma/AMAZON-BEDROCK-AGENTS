// Application constants
export const APP_NAME = 'PPT Assistant';
export const APP_VERSION = '1.0.0';

// API endpoints
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const API_TIMEOUT = 30000; // 30 seconds

// Storage keys
export const STORAGE_KEYS = {
  PROJECTS: 'ppt-assistant-projects',
  API_CONFIG: 'ppt-assistant-api-config',
  USER_PREFERENCES: 'ppt-assistant-preferences',
  THEME: 'ppt-assistant-theme',
} as const;

// File limits
export const FILE_LIMITS = {
  MAX_IMAGE_SIZE: 5 * 1024 * 1024, // 5MB
  MAX_PPT_SIZE: 50 * 1024 * 1024, // 50MB
  ALLOWED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml'],
} as const;

// UI constants
export const UI_CONSTANTS = {
  TOAST_DURATION: 5000,
  DEBOUNCE_DELAY: 300,
  PAGE_SIZE: 20,
  MAX_TITLE_LENGTH: 100,
  MAX_DESCRIPTION_LENGTH: 500,
} as const;

// PPT generation settings
export const PPT_SETTINGS = {
  DEFAULT_SLIDES_COUNT: 10,
  MIN_SLIDES_COUNT: 3,
  MAX_SLIDES_COUNT: 50,
  DEFAULT_THEME: 'professional',
  THEMES: ['professional', 'creative', 'minimal', 'colorful'] as const,
} as const;