import React, { Suspense } from 'react';
import { 
  createBrowserRouter, 
  RouterProvider, 
  Navigate,
  Outlet,
  useRouteError,
  isRouteErrorResponse
} from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import LoadingSpinner from '@/components/common/LoadingSpinner';

// Lazy load pages for code splitting
const Dashboard = React.lazy(() => import('@/pages/Dashboard'));
const ProjectPage = React.lazy(() => import('@/pages/ProjectPage'));
const EditorPage = React.lazy(() => import('@/pages/EditorPage'));
const SettingsPage = React.lazy(() => import('@/pages/SettingsPage'));
const NotFound = React.lazy(() => import('@/pages/NotFound'));
const PresentationGenerator = React.lazy(() => import('@/components/PresentationGenerator'));

// Error Boundary Component
const ErrorBoundary: React.FC = () => {
  const error = useRouteError();
  
  if (isRouteErrorResponse(error)) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-secondary-50 dark:bg-secondary-900">
        <div className="max-w-md w-full p-8 bg-white dark:bg-secondary-800 rounded-lg shadow-lg">
          <h1 className="text-2xl font-bold text-red-600 mb-4">
            {error.status} {error.statusText}
          </h1>
          <p className="text-secondary-600 dark:text-secondary-400">
            {error.data || '发生了意外错误'}
          </p>
          <button
            onClick={() => window.location.href = '/'}
            className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-secondary-50 dark:bg-secondary-900">
      <div className="max-w-md w-full p-8 bg-white dark:bg-secondary-800 rounded-lg shadow-lg">
        <h1 className="text-2xl font-bold text-red-600 mb-4">
          应用错误
        </h1>
        <p className="text-secondary-600 dark:text-secondary-400">
          {error instanceof Error ? error.message : '发生了意外错误'}
        </p>
        <button
          onClick={() => window.location.href = '/'}
          className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
        >
          返回首页
        </button>
      </div>
    </div>
  );
};

// Loading fallback component
const PageLoader: React.FC = () => (
  <div className="flex items-center justify-center min-h-[400px]">
    <LoadingSpinner size="large" message="加载中..." />
  </div>
);

// Protected Route Wrapper
const ProtectedRoute: React.FC = () => {
  // Here you can add authentication logic
  // For now, we'll just render the outlet
  const isAuthenticated = true; // This would come from auth context/store
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return (
    <AppLayout>
      <Suspense fallback={<PageLoader />}>
        <Outlet />
      </Suspense>
    </AppLayout>
  );
};

// Route configuration
export const router = createBrowserRouter([
  {
    path: '/',
    element: <ProtectedRoute />,
    errorElement: <ErrorBoundary />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />
      },
      {
        path: 'dashboard',
        element: <Dashboard />,
        handle: { 
          title: '仪表板',
          breadcrumb: '首页'
        }
      },
      {
        path: 'projects',
        children: [
          {
            index: true,
            element: <Dashboard />, // Projects list is part of dashboard
            handle: { 
              title: '项目列表',
              breadcrumb: '项目'
            }
          },
          {
            path: ':projectId',
            element: <ProjectPage />,
            handle: { 
              title: '项目详情',
              breadcrumb: '项目详情'
            },
            children: [
              {
                path: 'edit',
                element: <EditorPage />,
                handle: { 
                  title: '编辑器',
                  breadcrumb: '编辑'
                }
              }
            ]
          }
        ]
      },
      {
        path: 'editor',
        element: <Navigate to="/projects" replace />
      },
      {
        path: 'editor/:projectId',
        element: <EditorPage />,
        handle: { 
          title: 'PPT编辑器',
          breadcrumb: '编辑器'
        }
      },
      {
        path: 'presentation',
        element: <PresentationGenerator />,
        handle: { 
          title: 'AI 演示文稿生成',
          breadcrumb: 'AI生成'
        }
      },
      {
        path: 'settings',
        element: <SettingsPage />,
        handle: { 
          title: '设置',
          breadcrumb: '设置'
        },
        children: [
          {
            path: 'api',
            element: <SettingsPage />,
            handle: { 
              title: 'API配置',
              breadcrumb: 'API'
            }
          },
          {
            path: 'preferences',
            element: <SettingsPage />,
            handle: { 
              title: '偏好设置',
              breadcrumb: '偏好'
            }
          }
        ]
      }
    ]
  },
  {
    path: '*',
    element: (
      <Suspense fallback={<PageLoader />}>
        <NotFound />
      </Suspense>
    )
  }
]);

// Route guards and helpers
export const routeGuards = {
  // Check if user has access to a route
  canActivate: (path: string): boolean => {
    // Add your authorization logic here
    // For now, all routes are accessible
    return true;
  },

  // Check if user can leave current route
  canDeactivate: (path: string): boolean => {
    // Check for unsaved changes, etc.
    // For now, always allow navigation
    return true;
  },

  // Redirect to login if not authenticated
  requireAuth: (): boolean => {
    // Check authentication status
    const isAuthenticated = true; // This would come from auth context
    if (!isAuthenticated) {
      window.location.href = '/login';
      return false;
    }
    return true;
  }
};

// Navigation helpers
export const navigationHelpers = {
  // Generate project edit URL
  getProjectEditUrl: (projectId: string): string => {
    return `/editor/${projectId}`;
  },

  // Generate project view URL
  getProjectUrl: (projectId: string): string => {
    return `/projects/${projectId}`;
  },

  // Check if current route is active
  isRouteActive: (path: string, currentPath: string): boolean => {
    return currentPath.startsWith(path);
  },

  // Get breadcrumb trail for current route
  getBreadcrumbs: (pathname: string): Array<{ label: string; path: string }> => {
    const paths = pathname.split('/').filter(Boolean);
    const breadcrumbs: Array<{ label: string; path: string }> = [
      { label: '首页', path: '/' }
    ];

    let currentPath = '';
    paths.forEach((path) => {
      currentPath += `/${path}`;
      // Map path segments to readable labels
      const labelMap: Record<string, string> = {
        dashboard: '仪表板',
        projects: '项目',
        editor: '编辑器',
        settings: '设置',
        api: 'API配置',
        preferences: '偏好设置'
      };
      breadcrumbs.push({
        label: labelMap[path] || path,
        path: currentPath
      });
    });

    return breadcrumbs;
  }
};

// Router Provider Component
const RouterApp: React.FC = () => {
  return <RouterProvider router={router} />;
};

export default RouterApp;