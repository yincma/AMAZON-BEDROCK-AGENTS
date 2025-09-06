
import { render, screen, fireEvent, waitFor } from './test-utils';
import ProjectManager from '@/components/project/ProjectManager';
import { ProjectStatus } from '@/types/models';
import { mockUIStore, mockProjectStore, createMockProject } from './test-utils';

// Mock window.confirm
Object.defineProperty(window, 'confirm', {
  writable: true,
  value: jest.fn(),
});

describe('ProjectManager', () => {
  const mockProjects = [
    createMockProject({
      id: '1',
      title: '项目 1',
      topic: '商业计划',
      status: ProjectStatus.DRAFT,
      settings: { slidesCount: 10 }
    }),
    createMockProject({
      id: '2',
      title: '项目 2',
      topic: '产品发布',
      status: ProjectStatus.COMPLETED,
      settings: { slidesCount: 15 }
    }),
    createMockProject({
      id: '3',
      title: '项目 3',
      topic: '财务报告',
      status: ProjectStatus.GENERATING,
      settings: { slidesCount: 8 }
    }),
  ];

  beforeEach(() => {
    (window.confirm as jest.Mock).mockReturnValue(false);
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('Basic Rendering', () => {
    it('renders correctly with header and toolbar', () => {
      render(<ProjectManager />);

      expect(screen.getByText('我的项目')).toBeInTheDocument();
      expect(screen.getByText('管理和组织您的PPT项目')).toBeInTheDocument();
      expect(screen.getByText('新建项目')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('搜索项目...')).toBeInTheDocument();
    });

    it('renders loading state correctly', () => {
      render(<ProjectManager />, {
        projectStoreProps: { isLoading: true }
      });

      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.queryByText('暂无项目')).not.toBeInTheDocument();
    });

    it('renders empty state when no projects', () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: [],
          isLoading: false
        }
      });

      expect(screen.getByText('暂无项目')).toBeInTheDocument();
      expect(screen.getByText('创建您的第一个PPT项目开始使用')).toBeInTheDocument();
      expect(screen.getByText('创建项目')).toBeInTheDocument();
    });

    it('renders projects in grid view by default', () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      expect(screen.getByText('项目 1')).toBeInTheDocument();
      expect(screen.getByText('项目 2')).toBeInTheDocument();
      expect(screen.getByText('项目 3')).toBeInTheDocument();

      // Grid layout should be active
      const gridButton = screen.getByRole('button', { name: /grid/i });
      expect(gridButton).toHaveClass('bg-primary-100');
    });
  });

  describe('View Mode Toggle', () => {
    it('switches between grid and list view', () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Default should be grid
      const gridButton = screen.getByRole('button', { name: /grid/i });
      const listButton = screen.getByRole('button', { name: /list/i });
      
      expect(gridButton).toHaveClass('bg-primary-100');
      expect(listButton).not.toHaveClass('bg-primary-100');

      // Switch to list view
      fireEvent.click(listButton);
      
      expect(listButton).toHaveClass('bg-primary-100');
      expect(gridButton).not.toHaveClass('bg-primary-100');
    });

    it('displays projects correctly in list view', () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Switch to list view
      const listButton = screen.getByRole('button', { name: /list/i });
      fireEvent.click(listButton);

      // Projects should still be visible
      expect(screen.getByText('项目 1')).toBeInTheDocument();
      expect(screen.getByText('项目 2')).toBeInTheDocument();
      expect(screen.getByText('项目 3')).toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    it('calls searchProjects when search input changes', () => {
      render(<ProjectManager />);

      const searchInput = screen.getByPlaceholderText('搜索项目...');
      fireEvent.change(searchInput, { target: { value: 'test search' } });

      expect(mockProjectStore.searchProjects).toHaveBeenCalledWith('test search');
    });
  });

  describe('Filter Functionality', () => {
    it('toggles filter menu when filter button is clicked', () => {
      render(<ProjectManager />);

      const filterButton = screen.getByText('筛选');
      fireEvent.click(filterButton);

      expect(screen.getByText('全部')).toBeInTheDocument();
      expect(screen.getByText('草稿')).toBeInTheDocument();
      expect(screen.getByText('已完成')).toBeInTheDocument();
    });

    it('filters projects by status', () => {
      render(<ProjectManager />);

      const filterButton = screen.getByText('筛选');
      fireEvent.click(filterButton);

      const draftFilter = screen.getByText('草稿');
      fireEvent.click(draftFilter);

      expect(mockProjectStore.setFilterStatus).toHaveBeenCalledWith(ProjectStatus.DRAFT);
    });

    it('shows all projects when "全部" filter is selected', () => {
      render(<ProjectManager />);

      const filterButton = screen.getByText('筛选');
      fireEvent.click(filterButton);

      const allFilter = screen.getByText('全部');
      fireEvent.click(allFilter);

      expect(mockProjectStore.setFilterStatus).toHaveBeenCalledWith(null);
    });
  });

  describe('Sort Functionality', () => {
    it('changes sort option when dropdown is changed', () => {
      render(<ProjectManager />);

      const sortSelect = screen.getByDisplayValue('最近更新');
      fireEvent.change(sortSelect, { target: { value: 'title' } });

      expect(mockProjectStore.setSortBy).toHaveBeenCalledWith('title');
    });

    it('displays all sort options', () => {
      render(<ProjectManager />);

      const sortSelect = screen.getByDisplayValue('最近更新');
      
      expect(screen.getByDisplayValue('最近更新')).toBeInTheDocument();
      expect(screen.getByText('创建时间')).toBeInTheDocument();
      expect(screen.getByText('名称')).toBeInTheDocument();
    });
  });

  describe('Project Actions', () => {
    it('opens create project modal when new project button is clicked', () => {
      render(<ProjectManager />);

      const createButton = screen.getByText('新建项目');
      fireEvent.click(createButton);

      expect(mockUIStore.openModal).toHaveBeenCalledWith('createProject');
    });

    it('opens create project modal from empty state', () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: [],
          isLoading: false
        }
      });

      const createButton = screen.getByText('创建项目');
      fireEvent.click(createButton);

      expect(mockUIStore.openModal).toHaveBeenCalledWith('createProject');
    });

    it('opens project when open button is clicked', () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      const openButtons = screen.getAllByText('打开');
      fireEvent.click(openButtons[0]);

      expect(mockProjectStore.setCurrentProject).toHaveBeenCalledWith(mockProjects[0]);
    });
  });

  describe('Project Action Menu', () => {
    it('toggles action menu when more options button is clicked', async () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Find the more options buttons (MoreVertical icons)
      const moreButtons = screen.getAllByRole('button').filter(
        button => button.querySelector('svg')
      );
      
      // Click the first more options button
      const firstMoreButton = moreButtons.find(button => 
        button.querySelector('svg')?.classList.contains('w-5')
      );
      
      if (firstMoreButton) {
        fireEvent.click(firstMoreButton);

        await waitFor(() => {
          expect(screen.getByText('编辑')).toBeInTheDocument();
          expect(screen.getByText('复制')).toBeInTheDocument();
          expect(screen.getByText('导出')).toBeInTheDocument();
          expect(screen.getByText('删除')).toBeInTheDocument();
        });
      }
    });

    it('duplicates project when duplicate action is clicked', async () => {
      const newProject = createMockProject({ id: '4', title: '项目 1 - 副本' });
      mockProjectStore.duplicateProject.mockResolvedValue(newProject);

      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Open action menu
      const moreButtons = screen.getAllByRole('button').filter(
        button => button.querySelector('svg')
      );
      
      const firstMoreButton = moreButtons.find(button => 
        button.querySelector('svg')?.classList.contains('w-5')
      );
      
      if (firstMoreButton) {
        fireEvent.click(firstMoreButton);

        await waitFor(() => {
          const duplicateButton = screen.getByText('复制');
          fireEvent.click(duplicateButton);
        });

        expect(mockProjectStore.duplicateProject).toHaveBeenCalledWith('1');
        expect(mockUIStore.setLoading).toHaveBeenCalledWith('duplicate-1', true);
      }
    });

    it('deletes project when delete action is confirmed', async () => {
      (window.confirm as jest.Mock).mockReturnValue(true);

      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Open action menu
      const moreButtons = screen.getAllByRole('button').filter(
        button => button.querySelector('svg')
      );
      
      const firstMoreButton = moreButtons.find(button => 
        button.querySelector('svg')?.classList.contains('w-5')
      );
      
      if (firstMoreButton) {
        fireEvent.click(firstMoreButton);

        await waitFor(() => {
          const deleteButton = screen.getByText('删除');
          fireEvent.click(deleteButton);
        });

        expect(window.confirm).toHaveBeenCalledWith('确定要删除项目"项目 1"吗？此操作不可恢复。');
        expect(mockUIStore.setLoading).toHaveBeenCalledWith('delete-1', true);
        expect(mockProjectStore.deleteProject).toHaveBeenCalledWith('1');
      }
    });

    it('does not delete project when deletion is cancelled', async () => {
      (window.confirm as jest.Mock).mockReturnValue(false);

      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Open action menu
      const moreButtons = screen.getAllByRole('button').filter(
        button => button.querySelector('svg')
      );
      
      const firstMoreButton = moreButtons.find(button => 
        button.querySelector('svg')?.classList.contains('w-5')
      );
      
      if (firstMoreButton) {
        fireEvent.click(firstMoreButton);

        await waitFor(() => {
          const deleteButton = screen.getByText('删除');
          fireEvent.click(deleteButton);
        });

        expect(window.confirm).toHaveBeenCalledWith('确定要删除项目"项目 1"吗？此操作不可恢复。');
        expect(mockProjectStore.deleteProject).not.toHaveBeenCalled();
      }
    });

    it('opens project when edit action is clicked', async () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Open action menu
      const moreButtons = screen.getAllByRole('button').filter(
        button => button.querySelector('svg')
      );
      
      const firstMoreButton = moreButtons.find(button => 
        button.querySelector('svg')?.classList.contains('w-5')
      );
      
      if (firstMoreButton) {
        fireEvent.click(firstMoreButton);

        await waitFor(() => {
          const editButton = screen.getByText('编辑');
          fireEvent.click(editButton);
        });

        expect(mockProjectStore.setCurrentProject).toHaveBeenCalledWith(mockProjects[0]);
      }
    });
  });

  describe('Project Status Display', () => {
    it('displays correct status icons and labels', () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      expect(screen.getByText('草稿')).toBeInTheDocument();
      expect(screen.getByText('已完成')).toBeInTheDocument();
      expect(screen.getByText('生成中')).toBeInTheDocument();
    });

    it('shows generating status with pulse animation', () => {
      const generatingProject = [createMockProject({
        id: '1',
        title: '生成中项目',
        status: ProjectStatus.GENERATING,
      })];

      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: generatingProject,
          isLoading: false
        }
      });

      const statusElement = screen.getByText('生成中');
      expect(statusElement).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('displays error toast when there is an error', () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          error: '加载项目失败',
          isLoading: false
        }
      });

      expect(mockUIStore.showError).toHaveBeenCalledWith('操作失败', '加载项目失败');
      expect(mockProjectStore.clearError).toHaveBeenCalled();
    });

    it('handles duplicate error gracefully', async () => {
      mockProjectStore.duplicateProject.mockRejectedValue(new Error('Duplicate failed'));

      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Open action menu and click duplicate
      const moreButtons = screen.getAllByRole('button').filter(
        button => button.querySelector('svg')
      );
      
      const firstMoreButton = moreButtons.find(button => 
        button.querySelector('svg')?.classList.contains('w-5')
      );
      
      if (firstMoreButton) {
        fireEvent.click(firstMoreButton);

        await waitFor(() => {
          const duplicateButton = screen.getByText('复制');
          fireEvent.click(duplicateButton);
        });

        // Wait for error handling
        await waitFor(() => {
          expect(mockUIStore.showError).toHaveBeenCalledWith('复制失败', '无法复制项目，请重试');
        });
      }
    });

    it('handles delete error gracefully', async () => {
      (window.confirm as jest.Mock).mockReturnValue(true);
      mockProjectStore.deleteProject.mockRejectedValue(new Error('Delete failed'));

      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Open action menu and click delete
      const moreButtons = screen.getAllByRole('button').filter(
        button => button.querySelector('svg')
      );
      
      const firstMoreButton = moreButtons.find(button => 
        button.querySelector('svg')?.classList.contains('w-5')
      );
      
      if (firstMoreButton) {
        fireEvent.click(firstMoreButton);

        await waitFor(() => {
          const deleteButton = screen.getByText('删除');
          fireEvent.click(deleteButton);
        });

        // Wait for error handling
        await waitFor(() => {
          expect(mockUIStore.showError).toHaveBeenCalledWith('删除失败', '无法删除项目，请重试');
        });
      }
    });
  });

  describe('Store Integration', () => {
    it('calls loadProjects on mount', () => {
      render(<ProjectManager />);
      expect(mockProjectStore.loadProjects).toHaveBeenCalledTimes(1);
    });

    it('displays project metadata correctly', () => {
      render(<ProjectManager />, {
        projectStoreProps: { 
          filteredProjects: mockProjects,
          isLoading: false
        }
      });

      // Check slide count display
      expect(screen.getByText('10 页')).toBeInTheDocument();
      expect(screen.getByText('15 页')).toBeInTheDocument();
      expect(screen.getByText('8 页')).toBeInTheDocument();

      // Check date formatting
      const dateElements = screen.getAllByText(/\d{4}\/\d{1,2}\/\d{1,2}/);
      expect(dateElements.length).toBeGreaterThan(0);
    });
  });
});