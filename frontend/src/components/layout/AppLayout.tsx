import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import { useProjectStore } from '@/store/projectStore';
import {
  Menu,
  X,
  Home,
  FolderOpen,
  Settings,
  Plus,
  Search,
  Moon,
  Sun,
  Monitor,
  ChevronLeft,
  ChevronRight,
  FileText,
  Image,
  Download,
  Upload,
} from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    sidebarCollapsed,
    toggleSidebar,
    theme,
    setTheme,
    openModal,
  } = useUIStore();
  
  const { recentProjects, loadRecentProjects } = useProjectStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    loadRecentProjects();
  }, [loadRecentProjects]);

  // Initialize theme on mount
  useEffect(() => {
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
  }, [theme]);

  const handleThemeToggle = () => {
    const themes: ('light' | 'dark' | 'system')[] = ['light', 'dark', 'system'];
    const currentIndex = themes.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex]);
  };

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return <Sun className="w-5 h-5" />;
      case 'dark':
        return <Moon className="w-5 h-5" />;
      default:
        return <Monitor className="w-5 h-5" />;
    }
  };

  const navigationItems = [
    { 
      icon: Home, 
      label: '主页', 
      path: '/dashboard',
      onClick: () => navigate('/dashboard'),
      isActive: location.pathname === '/dashboard'
    },
    { 
      icon: FolderOpen, 
      label: '项目', 
      path: '/projects',
      onClick: () => navigate('/projects'),
      isActive: location.pathname.startsWith('/projects')
    },
    { 
      icon: FileText, 
      label: '模板', 
      path: '/templates',
      onClick: () => {
        // 模板功能暂时显示提示
        openModal('settings');
      },
      isActive: location.pathname === '/templates'
    },
    { 
      icon: Image, 
      label: '图片库', 
      onClick: () => openModal('imageGallery'),
      isActive: false
    },
    { 
      icon: Settings, 
      label: '设置', 
      path: '/settings',
      onClick: () => navigate('/settings'),
      isActive: location.pathname.startsWith('/settings')
    },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-secondary-900 transition-colors duration-200">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-white dark:bg-secondary-800 border-b border-secondary-200 dark:border-secondary-700 z-40">
        <div className="flex items-center justify-between h-full px-4">
          {/* Left section */}
          <div className="flex items-center space-x-4">
            {/* Mobile menu button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-2 rounded-md hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6 text-secondary-600 dark:text-secondary-300" />
              ) : (
                <Menu className="w-6 h-6 text-secondary-600 dark:text-secondary-300" />
              )}
            </button>

            {/* Sidebar toggle for desktop */}
            <button
              onClick={toggleSidebar}
              className="hidden lg:flex p-2 rounded-md hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
            >
              {sidebarCollapsed ? (
                <ChevronRight className="w-6 h-6 text-secondary-600 dark:text-secondary-300" />
              ) : (
                <ChevronLeft className="w-6 h-6 text-secondary-600 dark:text-secondary-300" />
              )}
            </button>

            {/* Logo */}
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold">P</span>
              </div>
              <span className="font-semibold text-lg text-secondary-900 dark:text-white">
                PPT Assistant
              </span>
            </div>
          </div>

          {/* Center section - Search */}
          <div className="hidden md:flex flex-1 max-w-xl mx-8">
            <div className="relative w-full">
              <input
                type="text"
                placeholder="搜索项目..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-secondary-50 dark:bg-secondary-700 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
              />
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-secondary-400" />
            </div>
          </div>

          {/* Right section */}
          <div className="flex items-center space-x-3">
            {/* Create new button */}
            <button
              onClick={() => openModal('createProject')}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              <Plus className="w-5 h-5" />
              <span className="hidden sm:inline">新建项目</span>
            </button>

            {/* Theme toggle */}
            <button
              onClick={handleThemeToggle}
              className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
              title={`当前主题: ${theme}`}
            >
              {getThemeIcon()}
            </button>

            {/* Import/Export buttons */}
            <button
              onClick={() => openModal('importData')}
              className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
              title="导入数据"
            >
              <Upload className="w-5 h-5 text-secondary-600 dark:text-secondary-300" />
            </button>
            
            <button
              onClick={() => openModal('exportData')}
              className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
              title="导出数据"
            >
              <Download className="w-5 h-5 text-secondary-600 dark:text-secondary-300" />
            </button>
          </div>
        </div>
      </header>

      {/* Sidebar for desktop */}
      <aside
        className={`
          hidden lg:block fixed left-0 top-16 bottom-0 bg-white dark:bg-secondary-800 
          border-r border-secondary-200 dark:border-secondary-700 transition-all duration-300 z-30
          ${sidebarCollapsed ? 'w-16' : 'w-64'}
        `}
      >
        <nav className="p-4">
          <ul className="space-y-2">
            {navigationItems.map((item, index) => (
              <li key={index}>
                <button
                  onClick={item.onClick}
                  className={`
                    w-full flex items-center space-x-3 px-3 py-2 rounded-lg
                    transition-colors
                    ${item.isActive 
                      ? 'bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400' 
                      : 'hover:bg-secondary-100 dark:hover:bg-secondary-700 text-secondary-700 dark:text-secondary-200'
                    }
                  `}
                >
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </button>
              </li>
            ))}
          </ul>

          {/* Recent projects */}
          {!sidebarCollapsed && recentProjects.length > 0 && (
            <div className="mt-8">
              <h3 className="text-sm font-semibold text-secondary-500 dark:text-secondary-400 mb-3">
                最近项目
              </h3>
              <ul className="space-y-1">
                {recentProjects.slice(0, 5).map((project) => (
                  <li key={project.id}>
                    <button
                      onClick={() => navigate(`/editor/${project.id}`)}
                      className="w-full text-left px-3 py-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
                    >
                      <p className="text-sm text-secondary-700 dark:text-secondary-200 truncate">
                        {project.title}
                      </p>
                      <p className="text-xs text-secondary-400 dark:text-secondary-500">
                        {new Date(project.updatedAt).toLocaleDateString('zh-CN')}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </nav>
      </aside>

      {/* Mobile sidebar */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black bg-opacity-50"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          
          {/* Sidebar */}
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-white dark:bg-secondary-800">
            <div className="p-4">
              {/* Logo */}
              <div className="flex items-center space-x-2 mb-6">
                <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold">P</span>
                </div>
                <span className="font-semibold text-lg text-secondary-900 dark:text-white">
                  PPT Assistant
                </span>
              </div>

              {/* Search for mobile */}
              <div className="relative mb-6">
                <input
                  type="text"
                  placeholder="搜索项目..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-secondary-50 dark:bg-secondary-700 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-secondary-400" />
              </div>

              {/* Navigation */}
              <nav>
                <ul className="space-y-2">
                  {navigationItems.map((item, index) => (
                    <li key={index}>
                      <button
                        onClick={() => {
                          item.onClick();
                          setIsMobileMenuOpen(false);
                        }}
                        className={`
                          w-full flex items-center space-x-3 px-3 py-2 rounded-lg
                          transition-colors
                          ${item.isActive 
                            ? 'bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400' 
                            : 'hover:bg-secondary-100 dark:hover:bg-secondary-700 text-secondary-700 dark:text-secondary-200'
                          }
                        `}
                      >
                        <item.icon className="w-5 h-5" />
                        <span>{item.label}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </nav>
            </div>
          </aside>
        </div>
      )}

      {/* Main content */}
      <main
        className={`
          pt-16 transition-all duration-300
          ${sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'}
        `}
      >
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
};

export default AppLayout;