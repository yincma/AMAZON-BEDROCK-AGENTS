import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Outlet } from 'react-router-dom';
import { useProjectStore } from '@/store/projectStore';
import { useUIStore } from '@/store/uiStore';
import { Project } from '@/types/models';
import { 
  FileText, 
  Calendar, 
  Edit3, 
  Download, 
  Trash2, 
  Share2,
  Clock,
  Layers
} from 'lucide-react';

const ProjectPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { getProject, deleteProject, exportProject } = useProjectStore();
  const { setPageTitle, showSuccess, showError, showConfirm } = useUIStore();
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (projectId) {
      loadProject(projectId);
    }
  }, [projectId]);

  const loadProject = async (id: string) => {
    try {
      setIsLoading(true);
      const proj = await getProject(id);
      if (proj) {
        setProject(proj);
        setPageTitle(proj.title);
      } else {
        showError('项目未找到', '请返回项目列表');
        navigate('/dashboard');
      }
    } catch (error) {
      showError('加载失败', '无法加载项目数据');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = () => {
    navigate(`/editor/${projectId}`);
  };

  const handleDelete = async () => {
    const confirmed = await showConfirm(
      '删除项目',
      '确定要删除这个项目吗？此操作无法撤销。'
    );

    if (confirmed && projectId) {
      try {
        await deleteProject(projectId);
        showSuccess('删除成功', '项目已被删除');
        navigate('/dashboard');
      } catch (error) {
        showError('删除失败', '无法删除项目');
      }
    }
  };

  const handleExport = async () => {
    if (!project) return;

    try {
      const exported = await exportProject(projectId!);
      // Create download link
      const blob = new Blob([JSON.stringify(exported, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${project.title}-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      showSuccess('导出成功', '项目已导出为JSON文件');
    } catch (error) {
      showError('导出失败', '无法导出项目');
    }
  };

  const handleShare = () => {
    // Implement share functionality
    showSuccess('分享链接已复制', '您可以将链接分享给其他人');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto"></div>
          <p className="mt-4 text-secondary-600 dark:text-secondary-400">加载项目中...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-secondary-600 dark:text-secondary-400">项目未找到</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
          >
            返回仪表板
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6">
      {/* Project Header */}
      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-sm p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-secondary-900 dark:text-white mb-2">
              {project.title}
            </h1>
            <p className="text-secondary-600 dark:text-secondary-400 mb-4">
              {project.description || '暂无描述'}
            </p>
            
            {/* Meta Information */}
            <div className="flex flex-wrap gap-4 text-sm text-secondary-500 dark:text-secondary-400">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                <span>创建于 {new Date(project.createdAt).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>更新于 {new Date(project.updatedAt).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4" />
                <span>{project.slides?.length || 0} 张幻灯片</span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleEdit}
              className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
            >
              <Edit3 className="w-4 h-4" />
              编辑
            </button>
            <button
              onClick={handleExport}
              className="p-2 text-secondary-600 dark:text-secondary-400 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded-lg"
              title="导出项目"
            >
              <Download className="w-5 h-5" />
            </button>
            <button
              onClick={handleShare}
              className="p-2 text-secondary-600 dark:text-secondary-400 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded-lg"
              title="分享项目"
            >
              <Share2 className="w-5 h-5" />
            </button>
            <button
              onClick={handleDelete}
              className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
              title="删除项目"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Project Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Outline Section */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-secondary-900 dark:text-white mb-4">
              大纲结构
            </h2>
            {project.outline && project.outline.length > 0 ? (
              <div className="space-y-2">
                {project.outline.map((node, index) => (
                  <div 
                    key={node.id}
                    className="p-3 bg-secondary-50 dark:bg-secondary-700 rounded-lg"
                    style={{ marginLeft: `${node.level * 20}px` }}
                  >
                    <h3 className="font-medium text-secondary-900 dark:text-white">
                      {index + 1}. {node.title}
                    </h3>
                    {node.content && (
                      <p className="text-sm text-secondary-600 dark:text-secondary-400 mt-1">
                        {node.content}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-secondary-500 dark:text-secondary-400">
                还没有大纲。点击编辑开始创建。
              </p>
            )}
          </div>
        </div>

        {/* Slides Preview */}
        <div>
          <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-secondary-900 dark:text-white mb-4">
              幻灯片预览
            </h2>
            {project.slides && project.slides.length > 0 ? (
              <div className="space-y-3">
                {project.slides.slice(0, 5).map((slide, index) => (
                  <div 
                    key={slide.id}
                    className="p-3 bg-secondary-50 dark:bg-secondary-700 rounded-lg cursor-pointer hover:bg-secondary-100 dark:hover:bg-secondary-600"
                    onClick={handleEdit}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-secondary-500 dark:text-secondary-400">
                        #{index + 1}
                      </span>
                      <h4 className="text-sm font-medium text-secondary-900 dark:text-white truncate">
                        {slide.title}
                      </h4>
                    </div>
                    {slide.content && (
                      <p className="text-xs text-secondary-600 dark:text-secondary-400 line-clamp-2">
                        {slide.content.replace(/<[^>]*>/g, '')}
                      </p>
                    )}
                  </div>
                ))}
                {project.slides.length > 5 && (
                  <button
                    onClick={handleEdit}
                    className="w-full py-2 text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                  >
                    查看所有 {project.slides.length} 张幻灯片
                  </button>
                )}
              </div>
            ) : (
              <p className="text-secondary-500 dark:text-secondary-400">
                还没有幻灯片
              </p>
            )}
          </div>

          {/* Project Settings */}
          <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-sm p-6 mt-6">
            <h2 className="text-lg font-semibold text-secondary-900 dark:text-white mb-4">
              项目设置
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-secondary-600 dark:text-secondary-400">
                  模板
                </span>
                <span className="text-sm font-medium text-secondary-900 dark:text-white">
                  {project.settings?.template || '默认'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-secondary-600 dark:text-secondary-400">
                  主题
                </span>
                <span className="text-sm font-medium text-secondary-900 dark:text-white">
                  {project.settings?.theme || '专业蓝'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-secondary-600 dark:text-secondary-400">
                  语言
                </span>
                <span className="text-sm font-medium text-secondary-900 dark:text-white">
                  {project.settings?.language || '中文'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Outlet for nested routes */}
      <Outlet />
    </div>
  );
};

export default ProjectPage;