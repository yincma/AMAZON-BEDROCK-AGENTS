import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '@/store/projectStore';
import { useUIStore } from '@/store/uiStore';
import ProjectManager from '@/components/project/ProjectManager';
import { Plus, FileText, Clock, TrendingUp } from 'lucide-react';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { projects, loadProjects, createProject } = useProjectStore();
  const { setPageTitle } = useUIStore();

  useEffect(() => {
    setPageTitle('仪表板');
    loadProjects();
  }, [setPageTitle, loadProjects]);

  const handleCreateProject = async () => {
    const newProject = await createProject({
      title: '新PPT项目',
      description: '点击编辑以开始创建您的演示文稿'
    });
    
    if (newProject) {
      navigate(`/editor/${newProject.id}`);
    }
  };

  const stats = {
    totalProjects: projects.length,
    recentProjects: projects.filter(p => {
      const dayAgo = new Date();
      dayAgo.setDate(dayAgo.getDate() - 1);
      return new Date(p.updatedAt) > dayAgo;
    }).length,
    totalSlides: projects.reduce((acc, p) => acc + (p.slides?.length || 0), 0)
  };

  return (
    <div className="container mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-secondary-900 dark:text-white mb-2">
          欢迎回来
        </h1>
        <p className="text-secondary-600 dark:text-secondary-400">
          管理您的PPT项目，创建精彩的演示文稿
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-primary-100 dark:bg-primary-900 rounded-lg">
              <FileText className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            </div>
            <span className="text-2xl font-bold text-secondary-900 dark:text-white">
              {stats.totalProjects}
            </span>
          </div>
          <p className="text-secondary-600 dark:text-secondary-400">
            总项目数
          </p>
        </div>

        <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
              <Clock className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <span className="text-2xl font-bold text-secondary-900 dark:text-white">
              {stats.recentProjects}
            </span>
          </div>
          <p className="text-secondary-600 dark:text-secondary-400">
            最近24小时
          </p>
        </div>

        <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-purple-100 dark:bg-purple-900 rounded-lg">
              <TrendingUp className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <span className="text-2xl font-bold text-secondary-900 dark:text-white">
              {stats.totalSlides}
            </span>
          </div>
          <p className="text-secondary-600 dark:text-secondary-400">
            总幻灯片数
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-white mb-4">
          快速操作
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={handleCreateProject}
            className="flex items-center justify-center gap-3 p-6 bg-primary-500 hover:bg-primary-600 text-white rounded-lg shadow-sm transition-colors"
          >
            <Plus className="w-6 h-6" />
            <span className="font-medium">创建新项目</span>
          </button>
          
          <button
            onClick={() => navigate('/settings/api')}
            className="flex items-center justify-center gap-3 p-6 bg-white dark:bg-secondary-800 hover:bg-secondary-50 dark:hover:bg-secondary-700 text-secondary-700 dark:text-secondary-300 rounded-lg shadow-sm transition-colors border border-secondary-200 dark:border-secondary-600"
          >
            <span className="font-medium">配置API</span>
          </button>

          <button
            onClick={() => navigate('/settings/preferences')}
            className="flex items-center justify-center gap-3 p-6 bg-white dark:bg-secondary-800 hover:bg-secondary-50 dark:hover:bg-secondary-700 text-secondary-700 dark:text-secondary-300 rounded-lg shadow-sm transition-colors border border-secondary-200 dark:border-secondary-600"
          >
            <span className="font-medium">偏好设置</span>
          </button>
        </div>
      </div>

      {/* Projects Section */}
      <div>
        <h2 className="text-xl font-semibold text-secondary-900 dark:text-white mb-4">
          我的项目
        </h2>
        <ProjectManager />
      </div>
    </div>
  );
};

export default Dashboard;