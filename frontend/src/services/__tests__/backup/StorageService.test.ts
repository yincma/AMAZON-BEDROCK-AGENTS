import { StorageService } from '../StorageService';
import { Project, UserPreferences, ProjectStatus } from '../../types/models';
import localforage from 'localforage';

// Mock localforage
jest.mock('localforage');
const mockedLocalforage = localforage as jest.Mocked<typeof localforage>;

// Mock console methods
console.error = jest.fn();

describe('StorageService', () => {
  let storageService: StorageService;
  let mockProjectStorage: jest.Mocked<any>;
  let mockPreferencesStorage: jest.Mocked<any>;
  let mockCacheStorage: jest.Mocked<any>;

  const mockProject: Project = {
    id: 'project-123',
    title: 'Test Project',
    description: 'A test project',
    topic: 'AI Technology',
    outline: [],
    slides: [],
    settings: {
      slidesCount: 10,
      theme: 'professional',
      includeImages: true,
      language: 'en',
      tone: 'professional',
    },
    createdAt: new Date('2023-01-01T00:00:00Z'),
    updatedAt: new Date('2023-01-01T12:00:00Z'),
    status: ProjectStatus.DRAFT,
  };

  const mockPreferences: UserPreferences = {
    theme: 'light',
    language: 'en',
    autoSave: true,
    autoSaveInterval: 60,
    recentProjects: ['project-123'],
    defaultProjectSettings: {
      slidesCount: 10,
      theme: 'professional',
      includeImages: true,
      language: 'en',
      tone: 'professional',
    },
  };

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();

    // Create mock storage instances
    mockProjectStorage = {
      setItem: jest.fn().mockResolvedValue(undefined),
      getItem: jest.fn(),
      removeItem: jest.fn().mockResolvedValue(undefined),
      clear: jest.fn().mockResolvedValue(undefined),
    };

    mockPreferencesStorage = {
      setItem: jest.fn().mockResolvedValue(undefined),
      getItem: jest.fn(),
      removeItem: jest.fn().mockResolvedValue(undefined),
      clear: jest.fn().mockResolvedValue(undefined),
    };

    mockCacheStorage = {
      setItem: jest.fn().mockResolvedValue(undefined),
      getItem: jest.fn(),
      removeItem: jest.fn().mockResolvedValue(undefined),
      clear: jest.fn().mockResolvedValue(undefined),
    };

    // Mock createInstance to return different mocks based on storeName
    mockedLocalforage.createInstance.mockImplementation(({ storeName }) => {
      switch (storeName) {
        case 'projects':
          return mockProjectStorage;
        case 'preferences':
          return mockPreferencesStorage;
        case 'cache':
          return mockCacheStorage;
        default:
          return mockProjectStorage;
      }
    });

    storageService = new StorageService();
  });

  describe('Project Operations', () => {
    beforeEach(() => {
      // Mock project IDs
      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') {
          return Promise.resolve(['project-123']);
        }
        if (key === 'project-123') {
          return Promise.resolve(mockProject);
        }
        return Promise.resolve(null);
      });
    });

    it('should save a new project', async () => {
      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') {
          return Promise.resolve([]);
        }
        return Promise.resolve(null);
      });

      await storageService.saveProject(mockProject);

      expect(mockProjectStorage.setItem).toHaveBeenCalledWith('project-123', mockProject);
      expect(mockProjectStorage.setItem).toHaveBeenCalledWith('_project_ids', ['project-123']);
    });

    it('should save existing project without duplicating ID', async () => {
      await storageService.saveProject(mockProject);

      expect(mockProjectStorage.setItem).toHaveBeenCalledWith('project-123', mockProject);
      // Should not add duplicate ID
      expect(mockProjectStorage.setItem).toHaveBeenCalledTimes(2); // project + recent projects update
    });

    it('should get project by ID', async () => {
      const result = await storageService.getProject('project-123');

      expect(mockProjectStorage.getItem).toHaveBeenCalledWith('project-123');
      expect(result).toEqual(mockProject);
    });

    it('should return null for non-existent project', async () => {
      mockProjectStorage.getItem.mockResolvedValue(null);

      const result = await storageService.getProject('non-existent');

      expect(result).toBeNull();
    });

    it('should handle errors when getting project', async () => {
      mockProjectStorage.getItem.mockRejectedValue(new Error('Storage error'));

      const result = await storageService.getProject('project-123');

      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalledWith('Failed to get project:', expect.any(Error));
    });

    it('should get all projects sorted by update date', async () => {
      const project1 = { ...mockProject, id: 'project-1', updatedAt: '2023-01-01T00:00:00Z' };
      const project2 = { ...mockProject, id: 'project-2', updatedAt: '2023-01-02T00:00:00Z' };

      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') return Promise.resolve(['project-1', 'project-2']);
        if (key === 'project-1') return Promise.resolve(project1);
        if (key === 'project-2') return Promise.resolve(project2);
        return Promise.resolve(null);
      });

      const result = await storageService.getAllProjects();

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual(project2); // Most recent first
      expect(result[1]).toEqual(project1);
    });

    it('should handle empty project list', async () => {
      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') return Promise.resolve([]);
        return Promise.resolve(null);
      });

      const result = await storageService.getAllProjects();

      expect(result).toEqual([]);
    });

    it('should delete project and update indices', async () => {
      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') return Promise.resolve(['project-123', 'project-456']);
        return Promise.resolve(null);
      });

      await storageService.deleteProject('project-123');

      expect(mockProjectStorage.removeItem).toHaveBeenCalledWith('project-123');
      expect(mockProjectStorage.setItem).toHaveBeenCalledWith('_project_ids', ['project-456']);
    });

    it('should handle errors when deleting project', async () => {
      mockProjectStorage.removeItem.mockRejectedValue(new Error('Delete failed'));

      await expect(storageService.deleteProject('project-123')).rejects.toThrow(
        'Failed to delete project from local storage'
      );

      expect(console.error).toHaveBeenCalledWith('Failed to delete project:', expect.any(Error));
    });

    it('should search projects by title, description, and topic', async () => {
      const project1 = { ...mockProject, title: 'AI Technology', description: 'Machine learning' };
      const project2 = { ...mockProject, id: 'project-2', title: 'Web Development', topic: 'React' };
      const project3 = { ...mockProject, id: 'project-3', title: 'Mobile Apps', description: 'React Native' };

      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') return Promise.resolve(['project-123', 'project-2', 'project-3']);
        if (key === 'project-123') return Promise.resolve(project1);
        if (key === 'project-2') return Promise.resolve(project2);
        if (key === 'project-3') return Promise.resolve(project3);
        return Promise.resolve(null);
      });

      const result = await storageService.searchProjects('react');

      expect(result).toHaveLength(2);
      expect(result.map(p => p.id)).toContain('project-2');
      expect(result.map(p => p.id)).toContain('project-3');
    });
  });

  describe('Recent Projects Management', () => {
    it('should get recent projects', async () => {
      mockPreferencesStorage.getItem.mockResolvedValue({
        ...mockPreferences,
        recentProjects: ['project-123', 'project-456'],
      });

      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === 'project-123') return Promise.resolve(mockProject);
        if (key === 'project-456') return Promise.resolve({ ...mockProject, id: 'project-456' });
        return Promise.resolve(null);
      });

      const result = await storageService.getRecentProjects(5);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual(mockProject);
    });

    it('should limit recent projects to specified count', async () => {
      mockPreferencesStorage.getItem.mockResolvedValue({
        ...mockPreferences,
        recentProjects: ['project-1', 'project-2', 'project-3'],
      });

      mockProjectStorage.getItem.mockImplementation((key) => {
        return Promise.resolve({ ...mockProject, id: key });
      });

      const result = await storageService.getRecentProjects(2);

      expect(result).toHaveLength(2);
    });

    it('should handle missing recent projects in preferences', async () => {
      mockPreferencesStorage.getItem.mockResolvedValue({
        ...mockPreferences,
        recentProjects: undefined,
      });

      const result = await storageService.getRecentProjects();

      expect(result).toEqual([]);
    });
  });

  describe('User Preferences Operations', () => {
    it('should save user preferences', async () => {
      await storageService.saveUserPreferences(mockPreferences);

      expect(mockPreferencesStorage.setItem).toHaveBeenCalledWith(
        'ppt-assistant-user-preferences',
        mockPreferences
      );
    });

    it('should handle errors when saving preferences', async () => {
      mockPreferencesStorage.setItem.mockRejectedValue(new Error('Save failed'));

      await expect(storageService.saveUserPreferences(mockPreferences)).rejects.toThrow(
        'Failed to save user preferences'
      );

      expect(console.error).toHaveBeenCalledWith('Failed to save user preferences:', expect.any(Error));
    });

    it('should get user preferences', async () => {
      mockPreferencesStorage.getItem.mockResolvedValue(mockPreferences);

      const result = await storageService.getUserPreferences();

      expect(mockPreferencesStorage.getItem).toHaveBeenCalledWith('ppt-assistant-user-preferences');
      expect(result).toEqual(mockPreferences);
    });

    it('should return null when preferences not found', async () => {
      mockPreferencesStorage.getItem.mockResolvedValue(null);

      const result = await storageService.getUserPreferences();

      expect(result).toBeNull();
    });

    it('should handle errors when getting preferences', async () => {
      mockPreferencesStorage.getItem.mockRejectedValue(new Error('Get failed'));

      const result = await storageService.getUserPreferences();

      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalledWith('Failed to get user preferences:', expect.any(Error));
    });
  });

  describe('API Configuration Operations', () => {
    const apiConfig = {
      apiKey: 'test-key',
      endpoint: 'https://api.test.com',
      timeout: 5000,
    };

    it('should save API configuration', async () => {
      const setItemSpy = jest.spyOn(localStorage, 'setItem');

      await storageService.saveApiConfig(apiConfig);

      expect(mockPreferencesStorage.setItem).toHaveBeenCalledWith(
        'ppt-assistant-api-config',
        apiConfig
      );
      expect(setItemSpy).toHaveBeenCalledWith(
        'ppt-assistant-api-config',
        JSON.stringify(apiConfig)
      );
    });

    it('should get API configuration', async () => {
      mockPreferencesStorage.getItem.mockResolvedValue(apiConfig);

      const result = await storageService.getApiConfig();

      expect(result).toEqual(apiConfig);
    });

    it('should handle errors when saving API config', async () => {
      mockPreferencesStorage.setItem.mockRejectedValue(new Error('Save failed'));

      await expect(storageService.saveApiConfig(apiConfig)).rejects.toThrow(
        'Failed to save API configuration'
      );
    });
  });

  describe('Cache Operations', () => {
    it('should set cache item with TTL', async () => {
      const data = { test: 'data' };
      const ttl = 5000;

      await storageService.setCacheItem('test-key', data, ttl);

      expect(mockCacheStorage.setItem).toHaveBeenCalledWith('test-key', {
        value: data,
        timestamp: expect.any(Number),
        ttl,
      });
    });

    it('should set cache item with default TTL', async () => {
      const data = { test: 'data' };

      await storageService.setCacheItem('test-key', data);

      expect(mockCacheStorage.setItem).toHaveBeenCalledWith('test-key', {
        value: data,
        timestamp: expect.any(Number),
        ttl: 3600000, // Default 1 hour
      });
    });

    it('should get valid cache item', async () => {
      const cacheItem = {
        value: { test: 'data' },
        timestamp: Date.now() - 1000, // 1 second ago
        ttl: 3600000, // 1 hour TTL
      };

      mockCacheStorage.getItem.mockResolvedValue(cacheItem);

      const result = await storageService.getCacheItem('test-key');

      expect(result).toEqual(cacheItem.value);
    });

    it('should return null for expired cache item', async () => {
      const cacheItem = {
        value: { test: 'data' },
        timestamp: Date.now() - 7200000, // 2 hours ago
        ttl: 3600000, // 1 hour TTL
      };

      mockCacheStorage.getItem.mockResolvedValue(cacheItem);

      const result = await storageService.getCacheItem('test-key');

      expect(result).toBeNull();
      expect(mockCacheStorage.removeItem).toHaveBeenCalledWith('test-key');
    });

    it('should return null for non-existent cache item', async () => {
      mockCacheStorage.getItem.mockResolvedValue(null);

      const result = await storageService.getCacheItem('non-existent');

      expect(result).toBeNull();
    });

    it('should clear cache', async () => {
      await storageService.clearCache();

      expect(mockCacheStorage.clear).toHaveBeenCalled();
    });

    it('should handle errors in cache operations', async () => {
      mockCacheStorage.setItem.mockRejectedValue(new Error('Cache error'));

      // Should not throw
      await expect(storageService.setCacheItem('test', 'data')).resolves.toBeUndefined();

      expect(console.error).toHaveBeenCalledWith('Failed to set cache item:', expect.any(Error));
    });
  });

  describe('Export/Import Operations', () => {
    it('should export projects data', async () => {
      const projects = [mockProject];
      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') return Promise.resolve(['project-123']);
        if (key === 'project-123') return Promise.resolve(mockProject);
        return Promise.resolve(null);
      });

      mockPreferencesStorage.getItem.mockImplementation((key) => {
        if (key === 'ppt-assistant-user-preferences') return Promise.resolve(mockPreferences);
        if (key === 'ppt-assistant-api-config') return Promise.resolve({ apiKey: 'test' });
        return Promise.resolve(null);
      });

      const result = await storageService.exportProjects();

      const exportData = JSON.parse(result);

      expect(exportData).toEqual({
        version: '1.0.0',
        exportDate: expect.any(String),
        projects,
        preferences: mockPreferences,
        apiConfig: { apiKey: 'test' },
      });
    });

    it('should import projects data', async () => {
      const importData = {
        version: '1.0.0',
        exportDate: '2023-01-01T00:00:00Z',
        projects: [mockProject],
        preferences: mockPreferences,
        apiConfig: { apiKey: 'test' },
      };

      // Mock that project doesn't exist
      mockProjectStorage.getItem.mockResolvedValue(null);

      const result = await storageService.importProjects(JSON.stringify(importData));

      expect(result).toEqual({
        imported: 1,
        skipped: 0,
        errors: [],
      });

      expect(mockProjectStorage.setItem).toHaveBeenCalledWith('project-123', mockProject);
      expect(mockPreferencesStorage.setItem).toHaveBeenCalledWith(
        'ppt-assistant-user-preferences',
        mockPreferences
      );
    });

    it('should skip existing projects during import', async () => {
      const importData = {
        projects: [mockProject],
      };

      // Mock that project already exists
      mockProjectStorage.getItem.mockResolvedValue(mockProject);

      const result = await storageService.importProjects(JSON.stringify(importData));

      expect(result).toEqual({
        imported: 0,
        skipped: 1,
        errors: [],
      });
    });

    it('should handle invalid import data', async () => {
      await expect(storageService.importProjects('invalid json')).rejects.toThrow(
        'Failed to parse import data'
      );
    });

    it('should handle missing projects array in import data', async () => {
      const invalidData = { version: '1.0.0' };

      await expect(storageService.importProjects(JSON.stringify(invalidData))).rejects.toThrow(
        'Invalid import data format'
      );
    });
  });

  describe('Storage Management', () => {
    it('should get storage info', async () => {
      const projects = [
        { ...mockProject, createdAt: '2023-01-01T00:00:00Z' },
        { ...mockProject, id: 'project-2', createdAt: '2023-01-02T00:00:00Z' },
      ];

      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') return Promise.resolve(['project-123', 'project-2']);
        if (key === 'project-123') return Promise.resolve(projects[0]);
        if (key === 'project-2') return Promise.resolve(projects[1]);
        return Promise.resolve(null);
      });

      const result = await storageService.getStorageInfo();

      expect(result).toEqual({
        projectCount: 2,
        totalSize: expect.any(Number),
        oldestProject: new Date('2023-01-01T00:00:00Z'),
        newestProject: new Date('2023-01-02T00:00:00Z'),
      });
    });

    it('should handle empty storage info', async () => {
      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') return Promise.resolve([]);
        return Promise.resolve(null);
      });

      const result = await storageService.getStorageInfo();

      expect(result).toEqual({
        projectCount: 0,
        totalSize: 2, // Empty array JSON
        oldestProject: undefined,
        newestProject: undefined,
      });
    });

    it('should clear all data', async () => {
      const removeItemSpy = jest.spyOn(localStorage, 'removeItem');

      await storageService.clearAllData();

      expect(mockProjectStorage.clear).toHaveBeenCalled();
      expect(mockPreferencesStorage.clear).toHaveBeenCalled();
      expect(mockCacheStorage.clear).toHaveBeenCalled();
      expect(removeItemSpy).toHaveBeenCalledWith('ppt-assistant-api-config');
    });

    it('should handle errors when clearing data', async () => {
      mockProjectStorage.clear.mockRejectedValue(new Error('Clear failed'));

      await expect(storageService.clearAllData()).rejects.toThrow('Failed to clear storage');

      expect(console.error).toHaveBeenCalledWith('Failed to clear all data:', expect.any(Error));
    });
  });

  describe('Backup Operations', () => {
    it('should create backup blob', async () => {
      mockProjectStorage.getItem.mockImplementation((key) => {
        if (key === '_project_ids') return Promise.resolve(['project-123']);
        if (key === 'project-123') return Promise.resolve(mockProject);
        return Promise.resolve(null);
      });

      mockPreferencesStorage.getItem.mockResolvedValue(null);

      const blob = await storageService.createBackup();

      expect(blob).toBeInstanceOf(Blob);
      expect(blob.type).toBe('application/json');
    });

    it('should restore backup from file', async () => {
      const exportData = {
        version: '1.0.0',
        projects: [mockProject],
      };

      const file = new File([JSON.stringify(exportData)], 'backup.json', {
        type: 'application/json',
      });

      // Mock that project doesn't exist
      mockProjectStorage.getItem.mockResolvedValue(null);

      await storageService.restoreBackup(file);

      expect(mockProjectStorage.setItem).toHaveBeenCalledWith('project-123', mockProject);
    });
  });
});