
import { render, screen, fireEvent, waitFor } from './test-utils';
import AppLayout from '@/components/layout/AppLayout';
import { mockUIStore, mockProjectStore, createMockProject } from './test-utils';

describe('AppLayout', () => {
  beforeEach(() => {
    // Reset window.matchMedia mock for each test
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query.includes('prefers-color-scheme: dark'),
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
  });

  describe('Basic Rendering', () => {
    it('renders correctly with basic content', () => {
      render(
        <AppLayout>
          <div>Test Content</div>
        </AppLayout>
      );

      // Check if main elements are present
      expect(screen.getByText('PPT Assistant')).toBeInTheDocument();
      expect(screen.getByText('Test Content')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('搜索项目...')).toBeInTheDocument();
    });

    it('renders navigation items correctly', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      // Check navigation items
      expect(screen.getByText('主页')).toBeInTheDocument();
      expect(screen.getByText('项目')).toBeInTheDocument();
      expect(screen.getByText('模板')).toBeInTheDocument();
      expect(screen.getByText('图片库')).toBeInTheDocument();
      expect(screen.getByText('设置')).toBeInTheDocument();
    });

    it('renders header buttons', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      expect(screen.getByText('新建项目')).toBeInTheDocument();
      expect(screen.getByTitle('导入数据')).toBeInTheDocument();
      expect(screen.getByTitle('导出数据')).toBeInTheDocument();
    });
  });

  describe('Sidebar Functionality', () => {
    it('toggles sidebar when toggle button is clicked', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      // Find the desktop sidebar toggle button
      const toggleButton = screen.getAllByRole('button').find(
        button => button.querySelector('svg')?.classList.contains('w-6')
      );

      expect(toggleButton).toBeInTheDocument();
      
      fireEvent.click(toggleButton!);
      expect(mockUIStore.toggleSidebar).toHaveBeenCalledTimes(1);
    });

    it('shows collapsed state correctly', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>,
        {
          uiStoreProps: { sidebarCollapsed: true }
        }
      );

      // In collapsed state, navigation labels should still be present in desktop view
      // but the sidebar should have collapsed styling
      const sidebar = document.querySelector('aside');
      expect(sidebar).toHaveClass('w-16');
    });

    it('shows expanded state correctly', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>,
        {
          uiStoreProps: { sidebarCollapsed: false }
        }
      );

      const sidebar = document.querySelector('aside');
      expect(sidebar).toHaveClass('w-64');
    });
  });

  describe('Mobile Menu', () => {
    it('toggles mobile menu when mobile button is clicked', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      // Find mobile menu button (visible only on mobile but still in DOM)
      const mobileButtons = screen.getAllByRole('button');
      const mobileMenuButton = mobileButtons.find(
        button => button.className.includes('lg:hidden')
      );

      expect(mobileMenuButton).toBeInTheDocument();
      
      fireEvent.click(mobileMenuButton!);

      // Mobile sidebar should appear
      expect(screen.getAllByText('PPT Assistant')).toHaveLength(2); // Header + mobile sidebar
    });

    it('closes mobile menu when backdrop is clicked', async () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      // Open mobile menu first
      const mobileButtons = screen.getAllByRole('button');
      const mobileMenuButton = mobileButtons.find(
        button => button.className.includes('lg:hidden')
      );
      
      fireEvent.click(mobileMenuButton!);

      // Find and click backdrop
      const backdrop = document.querySelector('.bg-black.bg-opacity-50');
      expect(backdrop).toBeInTheDocument();
      
      fireEvent.click(backdrop!);

      // Mobile menu should close
      await waitFor(() => {
        expect(screen.getAllByText('PPT Assistant')).toHaveLength(1);
      });
    });
  });

  describe('Theme Functionality', () => {
    it('cycles through themes when theme button is clicked', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      const themeButton = screen.getByTitle('当前主题: light');
      fireEvent.click(themeButton);

      expect(mockUIStore.setTheme).toHaveBeenCalledWith('dark');
    });

    it('displays correct theme icon', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>,
        {
          uiStoreProps: { theme: 'dark' }
        }
      );

      expect(screen.getByTitle('当前主题: dark')).toBeInTheDocument();
    });

    it('displays system theme icon', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>,
        {
          uiStoreProps: { theme: 'system' }
        }
      );

      expect(screen.getByTitle('当前主题: system')).toBeInTheDocument();
    });
  });

  describe('Recent Projects', () => {
    it('displays recent projects when available', () => {
      const recentProjects = [
        createMockProject({ id: '1', title: '项目 1', updatedAt: '2024-01-01' }),
        createMockProject({ id: '2', title: '项目 2', updatedAt: '2024-01-02' }),
      ];

      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>,
        {
          projectStoreProps: { recentProjects },
          uiStoreProps: { sidebarCollapsed: false }
        }
      );

      expect(screen.getByText('最近项目')).toBeInTheDocument();
      expect(screen.getByText('项目 1')).toBeInTheDocument();
      expect(screen.getByText('项目 2')).toBeInTheDocument();
    });

    it('does not display recent projects section when sidebar is collapsed', () => {
      const recentProjects = [
        createMockProject({ id: '1', title: '项目 1' }),
      ];

      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>,
        {
          projectStoreProps: { recentProjects },
          uiStoreProps: { sidebarCollapsed: true }
        }
      );

      expect(screen.queryByText('最近项目')).not.toBeInTheDocument();
    });

    it('limits recent projects to 5 items', () => {
      const recentProjects = Array.from({ length: 10 }, (_, i) => 
        createMockProject({ id: `${i}`, title: `项目 ${i}` })
      );

      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>,
        {
          projectStoreProps: { recentProjects },
          uiStoreProps: { sidebarCollapsed: false }
        }
      );

      // Should only show first 5 projects
      expect(screen.getByText('项目 0')).toBeInTheDocument();
      expect(screen.getByText('项目 4')).toBeInTheDocument();
      expect(screen.queryByText('项目 5')).not.toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    it('updates search query when user types', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      const searchInputs = screen.getAllByPlaceholderText('搜索项目...');
      const desktopSearchInput = searchInputs[0];

      fireEvent.change(desktopSearchInput, { target: { value: 'test query' } });
      expect(desktopSearchInput).toHaveValue('test query');
    });

    it('shows search input in mobile menu', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      // Open mobile menu
      const mobileButtons = screen.getAllByRole('button');
      const mobileMenuButton = mobileButtons.find(
        button => button.className.includes('lg:hidden')
      );
      fireEvent.click(mobileMenuButton!);

      // Should have search input in mobile menu
      const searchInputs = screen.getAllByPlaceholderText('搜索项目...');
      expect(searchInputs.length).toBeGreaterThan(1);
    });
  });

  describe('Button Actions', () => {
    it('opens create project modal when new project button is clicked', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      const createButton = screen.getByText('新建项目');
      fireEvent.click(createButton);

      expect(mockUIStore.openModal).toHaveBeenCalledWith('createProject');
    });

    it('opens image gallery modal when image gallery nav item is clicked', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      const imageGalleryButton = screen.getByText('图片库');
      fireEvent.click(imageGalleryButton);

      expect(mockUIStore.openModal).toHaveBeenCalledWith('imageGallery');
    });

    it('opens settings modal when settings nav item is clicked', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      const settingsButton = screen.getByText('设置');
      fireEvent.click(settingsButton);

      expect(mockUIStore.openModal).toHaveBeenCalledWith('settings');
    });

    it('opens import modal when import button is clicked', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      const importButton = screen.getByTitle('导入数据');
      fireEvent.click(importButton);

      expect(mockUIStore.openModal).toHaveBeenCalledWith('importData');
    });

    it('opens export modal when export button is clicked', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      const exportButton = screen.getByTitle('导出数据');
      fireEvent.click(exportButton);

      expect(mockUIStore.openModal).toHaveBeenCalledWith('exportData');
    });
  });

  describe('Layout Responsiveness', () => {
    it('applies correct main content padding based on sidebar state', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      const mainElement = document.querySelector('main');
      expect(mainElement).toHaveClass('lg:pl-64');
    });

    it('applies correct main content padding when sidebar is collapsed', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>,
        {
          uiStoreProps: { sidebarCollapsed: true }
        }
      );

      const mainElement = document.querySelector('main');
      expect(mainElement).toHaveClass('lg:pl-16');
    });
  });

  describe('Store Integration', () => {
    it('calls loadRecentProjects on mount', () => {
      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      expect(mockProjectStore.loadRecentProjects).toHaveBeenCalledTimes(1);
    });

    it('handles navigation click events with console.log', () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();

      render(
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      );

      const homeButton = screen.getByText('主页');
      fireEvent.click(homeButton);

      expect(consoleSpy).toHaveBeenCalledWith('Navigate to home');

      consoleSpy.mockRestore();
    });
  });
});