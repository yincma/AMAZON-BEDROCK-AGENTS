/**
 * Test data fixtures for E2E tests
 */

export const API_CONFIG = {
  valid: {
    apiKey: 'test-api-key-12345',
    endpoint: 'https://api.test.com',
    model: 'claude-3-sonnet',
  },
  invalid: {
    apiKey: 'invalid-key',
    endpoint: 'https://invalid-api.com',
    model: 'invalid-model',
  },
};

export const PROJECT_DATA = {
  simple: {
    title: 'Test Project',
    description: 'A simple test project for E2E testing',
    topic: 'Software Testing',
  },
  complex: {
    title: 'Advanced AI Presentation',
    description: 'A comprehensive presentation about artificial intelligence, machine learning, and their applications in modern software development',
    topic: 'Artificial Intelligence',
  },
  special_chars: {
    title: 'Test @#$%^&*()_+ Project',
    description: 'Project with special characters: <>&"\'',
    topic: 'Special Characters Testing',
  },
};

export const OUTLINE_DATA = {
  simple: {
    sections: 3,
    expectedTitles: ['Introduction', 'Main Content', 'Conclusion'],
  },
  detailed: {
    sections: 5,
    expectedTitles: ['Introduction', 'Background', 'Analysis', 'Implementation', 'Conclusion'],
  },
};

export const IMAGE_SEARCH = {
  keywords: [
    'technology',
    'business',
    'innovation',
    'data',
    'artificial intelligence',
  ],
  invalidKeywords: [
    '',
    '   ',
    'nsfw-content',
    'inappropriate-term',
  ],
};

export const ERROR_SCENARIOS = {
  network: {
    offline: 'Network connection lost',
    timeout: 'Request timeout',
    serverError: 'Internal server error',
  },
  validation: {
    emptyTitle: 'Project title cannot be empty',
    longTitle: 'A'.repeat(101), // Assuming 100 char limit
    emptyDescription: 'Project description cannot be empty',
  },
  storage: {
    quotaExceeded: 'Storage quota exceeded',
    accessDenied: 'Access denied to local storage',
  },
};

export const PERFORMANCE_THRESHOLDS = {
  pageLoad: 3000, // 3 seconds
  apiResponse: 5000, // 5 seconds
  imageLoad: 2000, // 2 seconds
  navigationTime: 1000, // 1 second
};

export const VIEWPORT_SIZES = {
  mobile: { width: 375, height: 667 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1280, height: 720 },
  wide: { width: 1920, height: 1080 },
};

export const USER_ACTIONS = {
  typing: {
    fast: { delay: 50 },
    normal: { delay: 100 },
    slow: { delay: 200 },
  },
  clicking: {
    single: { clickCount: 1 },
    double: { clickCount: 2 },
  },
  waiting: {
    short: 1000,
    medium: 3000,
    long: 5000,
  },
};