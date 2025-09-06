import React from 'react';
import { useNavigate } from 'react-router-dom';
import { HomeIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-secondary-50 dark:bg-secondary-900 flex flex-col items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        {/* 404 Illustration */}
        <div className="mb-8">
          <svg
            className="mx-auto h-48 w-48 text-secondary-400 dark:text-secondary-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={0.5}
              d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 12h.01M12 12h-.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h1 className="text-6xl font-bold text-secondary-900 dark:text-white mt-4">
            404
          </h1>
        </div>

        {/* Error Message */}
        <div className="mb-8">
          <h2 className="text-2xl font-semibold text-secondary-900 dark:text-white mb-4">
            页面未找到
          </h2>
          <p className="text-secondary-600 dark:text-secondary-400">
            抱歉，您访问的页面不存在。可能已被删除或移动到其他位置。
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => navigate(-1)}
            className="btn btn-secondary flex items-center justify-center"
          >
            <ArrowLeftIcon className="w-5 h-5 mr-2" />
            返回上一页
          </button>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn btn-primary flex items-center justify-center"
          >
            <HomeIcon className="w-5 h-5 mr-2" />
            回到首页
          </button>
        </div>

        {/* Help Links */}
        <div className="mt-12 pt-8 border-t border-secondary-200 dark:border-secondary-700">
          <p className="text-sm text-secondary-500 dark:text-secondary-400 mb-4">
            需要帮助？试试这些页面：
          </p>
          <div className="flex flex-wrap justify-center gap-4 text-sm">
            <button
              onClick={() => navigate('/dashboard')}
              className="text-primary-600 dark:text-primary-400 hover:underline"
            >
              仪表板
            </button>
            <span className="text-secondary-300 dark:text-secondary-600">•</span>
            <button
              onClick={() => navigate('/projects')}
              className="text-primary-600 dark:text-primary-400 hover:underline"
            >
              项目列表
            </button>
            <span className="text-secondary-300 dark:text-secondary-600">•</span>
            <button
              onClick={() => navigate('/settings')}
              className="text-primary-600 dark:text-primary-400 hover:underline"
            >
              设置
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFound;