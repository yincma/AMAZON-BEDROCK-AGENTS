import localforage from 'localforage';
import { Project, UserPreferences } from '@/types/models';
import { STORAGE_KEYS } from '@/utils/constants';

// Configure localforage instances
const projectStorage = localforage.createInstance({
  name: 'PPTAssistant',
  storeName: 'projects',
  description: 'Project data storage',
});

const preferencesStorage = localforage.createInstance({
  name: 'PPTAssistant',
  storeName: 'preferences',
  description: 'User preferences storage',
});

const cacheStorage = localforage.createInstance({
  name: 'PPTAssistant',
  storeName: 'cache',
  description: 'Temporary cache storage',
});

/**
 * Local Storage Service
 * Handles all local data persistence operations
 */
export class StorageService {
  /**
   * Project operations
   */
  async saveProject(project: Project): Promise<void> {
    try {
      // Save individual project
      await projectStorage.setItem(project.id, project);
      
      // Update project index
      const projectIds = await this.getProjectIds();
      if (!projectIds.includes(project.id)) {
        projectIds.push(project.id);
        await projectStorage.setItem('_project_ids', projectIds);
      }
      
      // Update recent projects
      await this.updateRecentProjects(project.id);
    } catch (error) {
      console.error('Failed to save project:', error);
      throw new Error('Failed to save project to local storage');
    }
  }

  async getProject(projectId: string): Promise<Project | null> {
    try {
      return await projectStorage.getItem<Project>(projectId);
    } catch (error) {
      console.error('Failed to get project:', error);
      return null;
    }
  }

  async getAllProjects(): Promise<Project[]> {
    try {
      const projectIds = await this.getProjectIds();
      const projects: Project[] = [];
      
      for (const id of projectIds) {
        const project = await this.getProject(id);
        if (project) {
          projects.push(project);
        }
      }
      
      // Sort by updated date (most recent first)
      return projects.sort((a, b) => 
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
    } catch (error) {
      console.error('Failed to get all projects:', error);
      return [];
    }
  }

  async deleteProject(projectId: string): Promise<void> {
    try {
      // Remove from storage
      await projectStorage.removeItem(projectId);
      
      // Update project index
      const projectIds = await this.getProjectIds();
      const updatedIds = projectIds.filter(id => id !== projectId);
      await projectStorage.setItem('_project_ids', updatedIds);
      
      // Remove from recent projects
      await this.removeFromRecentProjects(projectId);
    } catch (error) {
      console.error('Failed to delete project:', error);
      throw new Error('Failed to delete project from local storage');
    }
  }

  async searchProjects(query: string): Promise<Project[]> {
    const allProjects = await this.getAllProjects();
    const lowerQuery = query.toLowerCase();
    
    return allProjects.filter(project => 
      project.title.toLowerCase().includes(lowerQuery) ||
      project.description?.toLowerCase().includes(lowerQuery) ||
      project.topic.toLowerCase().includes(lowerQuery)
    );
  }

  private async getProjectIds(): Promise<string[]> {
    try {
      const ids = await projectStorage.getItem<string[]>('_project_ids');
      return ids || [];
    } catch (error) {
      console.error('Failed to get project IDs:', error);
      return [];
    }
  }

  /**
   * Recent projects management
   */
  private async updateRecentProjects(projectId: string): Promise<void> {
    const preferences = await this.getUserPreferences();
    const recentProjects = preferences?.recentProjects || [];
    
    // Remove if already exists and add to beginning
    const filtered = recentProjects.filter(id => id !== projectId);
    filtered.unshift(projectId);
    
    // Keep only last 10 recent projects
    const updated = filtered.slice(0, 10);
    
    if (preferences) {
      preferences.recentProjects = updated;
      await this.saveUserPreferences(preferences);
    }
  }

  private async removeFromRecentProjects(projectId: string): Promise<void> {
    const preferences = await this.getUserPreferences();
    if (preferences?.recentProjects) {
      preferences.recentProjects = preferences.recentProjects.filter(id => id !== projectId);
      await this.saveUserPreferences(preferences);
    }
  }

  async getRecentProjects(limit: number = 5): Promise<Project[]> {
    const preferences = await this.getUserPreferences();
    const recentIds = (preferences?.recentProjects || []).slice(0, limit);
    const projects: Project[] = [];
    
    for (const id of recentIds) {
      const project = await this.getProject(id);
      if (project) {
        projects.push(project);
      }
    }
    
    return projects;
  }

  /**
   * User preferences operations
   */
  async saveUserPreferences(preferences: UserPreferences): Promise<void> {
    try {
      await preferencesStorage.setItem(STORAGE_KEYS.USER_PREFERENCES, preferences);
    } catch (error) {
      console.error('Failed to save user preferences:', error);
      throw new Error('Failed to save user preferences');
    }
  }

  async getUserPreferences(): Promise<UserPreferences | null> {
    try {
      return await preferencesStorage.getItem<UserPreferences>(STORAGE_KEYS.USER_PREFERENCES);
    } catch (error) {
      console.error('Failed to get user preferences:', error);
      return null;
    }
  }

  /**
   * API configuration operations
   */
  async saveApiConfig(config: Record<string, any>): Promise<void> {
    try {
      await preferencesStorage.setItem(STORAGE_KEYS.API_CONFIG, config);
      // Also save to localStorage for immediate access by ApiService
      localStorage.setItem(STORAGE_KEYS.API_CONFIG, JSON.stringify(config));
    } catch (error) {
      console.error('Failed to save API config:', error);
      throw new Error('Failed to save API configuration');
    }
  }

  async getApiConfig(): Promise<Record<string, any> | null> {
    try {
      return await preferencesStorage.getItem<Record<string, any>>(STORAGE_KEYS.API_CONFIG);
    } catch (error) {
      console.error('Failed to get API config:', error);
      return null;
    }
  }

  /**
   * Cache operations
   */
  async setCacheItem(key: string, value: any, ttl?: number): Promise<void> {
    try {
      const item = {
        value,
        timestamp: Date.now(),
        ttl: ttl || 3600000, // Default 1 hour TTL
      };
      await cacheStorage.setItem(key, item);
    } catch (error) {
      console.error('Failed to set cache item:', error);
    }
  }

  async getCacheItem<T>(key: string): Promise<T | null> {
    try {
      const item = await cacheStorage.getItem<{
        value: T;
        timestamp: number;
        ttl: number;
      }>(key);
      
      if (!item) return null;
      
      // Check if cache is still valid
      if (Date.now() - item.timestamp > item.ttl) {
        await cacheStorage.removeItem(key);
        return null;
      }
      
      return item.value;
    } catch (error) {
      console.error('Failed to get cache item:', error);
      return null;
    }
  }

  async clearCache(): Promise<void> {
    try {
      await cacheStorage.clear();
    } catch (error) {
      console.error('Failed to clear cache:', error);
    }
  }

  /**
   * Export/Import operations
   */
  async exportProjects(): Promise<string> {
    try {
      const projects = await this.getAllProjects();
      const preferences = await this.getUserPreferences();
      const apiConfig = await this.getApiConfig();
      
      const exportData = {
        version: '1.0.0',
        exportDate: new Date().toISOString(),
        projects,
        preferences,
        apiConfig,
      };
      
      return JSON.stringify(exportData, null, 2);
    } catch (error) {
      console.error('Failed to export projects:', error);
      throw new Error('Failed to export projects');
    }
  }

  async importProjects(jsonData: string): Promise<{
    imported: number;
    skipped: number;
    errors: string[];
  }> {
    const result = {
      imported: 0,
      skipped: 0,
      errors: [] as string[],
    };
    
    try {
      const data = JSON.parse(jsonData);
      
      if (!data.projects || !Array.isArray(data.projects)) {
        throw new Error('Invalid import data format');
      }
      
      // Import projects
      for (const project of data.projects) {
        try {
          // Check if project already exists
          const existing = await this.getProject(project.id);
          if (existing) {
            result.skipped++;
            continue;
          }
          
          await this.saveProject(project);
          result.imported++;
        } catch (error) {
          result.errors.push(`Failed to import project ${project.id}: ${error}`);
        }
      }
      
      // Optionally import preferences and config
      if (data.preferences) {
        try {
          await this.saveUserPreferences(data.preferences);
        } catch (error) {
          result.errors.push('Failed to import preferences');
        }
      }
      
      if (data.apiConfig) {
        try {
          await this.saveApiConfig(data.apiConfig);
        } catch (error) {
          result.errors.push('Failed to import API configuration');
        }
      }
      
      return result;
    } catch (error) {
      console.error('Failed to import projects:', error);
      throw new Error('Failed to parse import data');
    }
  }

  /**
   * Storage management
   */
  async getStorageInfo(): Promise<{
    projectCount: number;
    totalSize: number;
    oldestProject?: Date;
    newestProject?: Date;
  }> {
    const projects = await this.getAllProjects();
    
    // Estimate size (rough calculation)
    const totalSize = JSON.stringify(projects).length;
    
    const dates = projects.map(p => new Date(p.createdAt));
    
    return {
      projectCount: projects.length,
      totalSize,
      oldestProject: dates.length > 0 ? new Date(Math.min(...dates.map(d => d.getTime()))) : undefined,
      newestProject: dates.length > 0 ? new Date(Math.max(...dates.map(d => d.getTime()))) : undefined,
    };
  }

  async clearAllData(): Promise<void> {
    try {
      await projectStorage.clear();
      await preferencesStorage.clear();
      await cacheStorage.clear();
      localStorage.removeItem(STORAGE_KEYS.API_CONFIG);
    } catch (error) {
      console.error('Failed to clear all data:', error);
      throw new Error('Failed to clear storage');
    }
  }

  /**
   * Backup operations
   */
  async createBackup(): Promise<Blob> {
    const exportData = await this.exportProjects();
    return new Blob([exportData], { type: 'application/json' });
  }

  async restoreBackup(file: File): Promise<void> {
    const text = await file.text();
    await this.importProjects(text);
  }
}

// Export singleton instance
export const storageService = new StorageService();

export default StorageService;