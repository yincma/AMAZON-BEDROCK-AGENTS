import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { Project, ProjectStatus } from '@/types/models';
import { storageService } from '@/services/StorageService';
import { v4 as uuidv4 } from 'uuid';

interface ProjectState {
  // Data
  projects: Project[];
  currentProject: Project | null;
  recentProjects: Project[];
  
  // UI State
  isLoading: boolean;
  error: string | null;
  searchQuery: string;
  filterStatus: ProjectStatus | null;
  sortBy: 'updatedAt' | 'createdAt' | 'title';
  sortOrder: 'asc' | 'desc';
  
  // Computed values
  filteredProjects: Project[];
  projectsCount: number;
  
  // Actions
  loadProjects: () => Promise<void>;
  createProject: (project: Omit<Project, 'id' | 'createdAt' | 'updatedAt' | 'status'>) => Promise<Project>;
  updateProject: (id: string, updates: Partial<Project>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  duplicateProject: (id: string) => Promise<Project | null>;
  
  setCurrentProject: (project: Project | null) => void;
  loadRecentProjects: () => Promise<void>;
  
  searchProjects: (query: string) => void;
  setFilterStatus: (status: ProjectStatus | null) => void;
  setSortBy: (sortBy: 'updatedAt' | 'createdAt' | 'title') => void;
  setSortOrder: (order: 'asc' | 'desc') => void;
  
  clearError: () => void;
  reset: () => void;
}

// Initial state
const initialState = {
  projects: [],
  currentProject: null,
  recentProjects: [],
  isLoading: false,
  error: null,
  searchQuery: '',
  filterStatus: null,
  sortBy: 'updatedAt' as const,
  sortOrder: 'desc' as const,
  filteredProjects: [],
  projectsCount: 0,
};

// Create the store
export const useProjectStore = create<ProjectState>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,
        
        // Load all projects from storage
        loadProjects: async () => {
          set(state => {
            state.isLoading = true;
            state.error = null;
          });
          
          try {
            const projects = await storageService.getAllProjects();
            set(state => {
              state.projects = projects;
              state.projectsCount = projects.length;
              state.isLoading = false;
            });
            
            // Update filtered projects
            get().updateFilteredProjects();
          } catch (error) {
            set(state => {
              state.error = error instanceof Error ? error.message : 'Failed to load projects';
              state.isLoading = false;
            });
          }
        },
        
        // Create a new project
        createProject: async (projectData) => {
          const newProject: Project = {
            ...projectData,
            id: uuidv4(),
            status: ProjectStatus.DRAFT,
            createdAt: new Date(),
            updatedAt: new Date(),
          };
          
          set(state => {
            state.isLoading = true;
            state.error = null;
          });
          
          try {
            await storageService.saveProject(newProject);
            
            set(state => {
              state.projects.unshift(newProject);
              state.projectsCount = state.projects.length;
              state.currentProject = newProject;
              state.isLoading = false;
            });
            
            // Update filtered projects
            get().updateFilteredProjects();
            
            return newProject;
          } catch (error) {
            set(state => {
              state.error = error instanceof Error ? error.message : 'Failed to create project';
              state.isLoading = false;
            });
            throw error;
          }
        },
        
        // Update an existing project
        updateProject: async (id, updates) => {
          const project = get().projects.find(p => p.id === id);
          if (!project) {
            throw new Error('Project not found');
          }
          
          const updatedProject: Project = {
            ...project,
            ...updates,
            updatedAt: new Date(),
          };
          
          set(state => {
            state.isLoading = true;
            state.error = null;
          });
          
          try {
            await storageService.saveProject(updatedProject);
            
            set(state => {
              const index = state.projects.findIndex(p => p.id === id);
              if (index !== -1) {
                state.projects[index] = updatedProject;
              }
              
              if (state.currentProject?.id === id) {
                state.currentProject = updatedProject;
              }
              
              state.isLoading = false;
            });
            
            // Update filtered projects
            get().updateFilteredProjects();
          } catch (error) {
            set(state => {
              state.error = error instanceof Error ? error.message : 'Failed to update project';
              state.isLoading = false;
            });
            throw error;
          }
        },
        
        // Delete a project
        deleteProject: async (id) => {
          set(state => {
            state.isLoading = true;
            state.error = null;
          });
          
          try {
            await storageService.deleteProject(id);
            
            set(state => {
              state.projects = state.projects.filter(p => p.id !== id);
              state.projectsCount = state.projects.length;
              
              if (state.currentProject?.id === id) {
                state.currentProject = null;
              }
              
              state.recentProjects = state.recentProjects.filter(p => p.id !== id);
              state.isLoading = false;
            });
            
            // Update filtered projects
            get().updateFilteredProjects();
          } catch (error) {
            set(state => {
              state.error = error instanceof Error ? error.message : 'Failed to delete project';
              state.isLoading = false;
            });
            throw error;
          }
        },
        
        // Duplicate a project
        duplicateProject: async (id) => {
          const project = get().projects.find(p => p.id === id);
          if (!project) {
            return null;
          }
          
          const duplicatedProject: Project = {
            ...project,
            id: uuidv4(),
            title: `${project.title} (Copy)`,
            status: ProjectStatus.DRAFT,
            createdAt: new Date(),
            updatedAt: new Date(),
          };
          
          try {
            await storageService.saveProject(duplicatedProject);
            
            set(state => {
              state.projects.unshift(duplicatedProject);
              state.projectsCount = state.projects.length;
            });
            
            // Update filtered projects
            get().updateFilteredProjects();
            
            return duplicatedProject;
          } catch (error) {
            set(state => {
              state.error = error instanceof Error ? error.message : 'Failed to duplicate project';
            });
            return null;
          }
        },
        
        // Set current project
        setCurrentProject: (project) => {
          set(state => {
            state.currentProject = project;
          });
        },
        
        // Load recent projects
        loadRecentProjects: async () => {
          try {
            const recentProjects = await storageService.getRecentProjects(5);
            set(state => {
              state.recentProjects = recentProjects;
            });
          } catch (error) {
            console.error('Failed to load recent projects:', error);
          }
        },
        
        // Search projects
        searchProjects: (query) => {
          set(state => {
            state.searchQuery = query;
          });
          get().updateFilteredProjects();
        },
        
        // Set filter status
        setFilterStatus: (status) => {
          set(state => {
            state.filterStatus = status;
          });
          get().updateFilteredProjects();
        },
        
        // Set sort by
        setSortBy: (sortBy) => {
          set(state => {
            state.sortBy = sortBy;
          });
          get().updateFilteredProjects();
        },
        
        // Set sort order
        setSortOrder: (order) => {
          set(state => {
            state.sortOrder = order;
          });
          get().updateFilteredProjects();
        },
        
        // Update filtered projects (internal helper)
        updateFilteredProjects: () => {
          set(state => {
            let filtered = [...state.projects];
            
            // Apply search filter
            if (state.searchQuery) {
              const query = state.searchQuery.toLowerCase();
              filtered = filtered.filter(project => 
                project.title.toLowerCase().includes(query) ||
                project.description?.toLowerCase().includes(query) ||
                project.topic.toLowerCase().includes(query)
              );
            }
            
            // Apply status filter
            if (state.filterStatus) {
              filtered = filtered.filter(project => project.status === state.filterStatus);
            }
            
            // Apply sorting
            filtered.sort((a, b) => {
              let comparison = 0;
              
              switch (state.sortBy) {
                case 'title':
                  comparison = a.title.localeCompare(b.title);
                  break;
                case 'createdAt':
                  comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
                  break;
                case 'updatedAt':
                default:
                  comparison = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
                  break;
              }
              
              return state.sortOrder === 'asc' ? comparison : -comparison;
            });
            
            state.filteredProjects = filtered;
          });
        },
        
        // Clear error
        clearError: () => {
          set(state => {
            state.error = null;
          });
        },
        
        // Reset store
        reset: () => {
          set(initialState);
        },
      })),
      {
        name: 'project-store',
        partialize: (state) => ({
          currentProject: state.currentProject,
          sortBy: state.sortBy,
          sortOrder: state.sortOrder,
        }),
      }
    ),
    {
      name: 'ProjectStore',
    }
  )
);

// Selector hooks
export const useCurrentProject = () => useProjectStore(state => state.currentProject);
export const useFilteredProjects = () => useProjectStore(state => state.filteredProjects);
export const useProjectsCount = () => useProjectStore(state => state.projectsCount);
export const useRecentProjects = () => useProjectStore(state => state.recentProjects);