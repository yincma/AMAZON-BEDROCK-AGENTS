import React, { useEffect, useState } from 'react';
import { useProjectStore } from '@/store/projectStore';
import { useUIStore, showToast } from '@/store/uiStore';
import { Project, ProjectStatus } from '@/types/models';
import {
  Plus,
  Search,
  Filter,
  Grid,
  List,
  Calendar,
  Clock,
  FileText,
  MoreVertical,
  Edit,
  Trash2,
  Copy,
  Download,
  Play,
  CheckCircle,
  AlertCircle,
  XCircle,
} from 'lucide-react';

type ViewMode = 'grid' | 'list';
type SortBy = 'updatedAt' | 'createdAt' | 'title';

const ProjectManager: React.FC = () => {
  const {
    projects,
    filteredProjects,
    isLoading,
    error,
    loadProjects,
    deleteProject,
    duplicateProject,
    setCurrentProject,
    searchProjects,
    setFilterStatus,
    setSortBy,
    setSortOrder,
    clearError,
  } = useProjectStore();

  const { openModal, setLoading } = useUIStore();

  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [selectedStatus, setSelectedStatus] = useState<ProjectStatus | 'all'>('all');
  const [sortOption, setSortOption] = useState<SortBy>('updatedAt');
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [actionMenuProject, setActionMenuProject] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (error) {
      showToast.error('操作失败', error);
      clearError();
    }
  }, [error, clearError]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    searchProjects(e.target.value);
  };

  const handleStatusFilter = (status: ProjectStatus | 'all') => {
    setSelectedStatus(status);
    setFilterStatus(status === 'all' ? null : status);
  };

  const handleSort = (sortBy: SortBy) => {
    setSortOption(sortBy);
    setSortBy(sortBy);
  };

  const handleDeleteProject = async (project: Project) => {
    if (window.confirm(`确定要删除项目"${project.title}"吗？此操作不可恢复。`)) {
      try {
        setLoading(`delete-${project.id}`, true);
        await deleteProject(project.id);
        showToast.success('删除成功', `项目"${project.title}"已删除`);
      } catch (error) {
        showToast.error('删除失败', '无法删除项目，请重试');
      } finally {
        setLoading(`delete-${project.id}`, false);
      }
    }
  };

  const handleDuplicateProject = async (project: Project) => {
    try {
      setLoading(`duplicate-${project.id}`, true);
      const newProject = await duplicateProject(project.id);
      if (newProject) {
        showToast.success('复制成功', `已创建项目"${newProject.title}"`);
      }
    } catch (error) {
      showToast.error('复制失败', '无法复制项目，请重试');
    } finally {
      setLoading(`duplicate-${project.id}`, false);
    }
  };

  const handleOpenProject = (project: Project) => {
    setCurrentProject(project);
    // Navigate to editor
    console.log('Navigate to editor with project:', project.id);
  };

  const getStatusIcon = (status: ProjectStatus) => {
    switch (status) {
      case ProjectStatus.COMPLETED:
        return <CheckCircle className="w-4 h-4 text-success-500" />;
      case ProjectStatus.GENERATING:
        return <AlertCircle className="w-4 h-4 text-warning-500 animate-pulse" />;
      case ProjectStatus.ERROR:
        return <XCircle className="w-4 h-4 text-error-500" />;
      default:
        return <Clock className="w-4 h-4 text-secondary-400" />;
    }
  };

  const getStatusLabel = (status: ProjectStatus) => {
    const labels: Record<ProjectStatus, string> = {
      [ProjectStatus.DRAFT]: '草稿',
      [ProjectStatus.OUTLINE_READY]: '大纲就绪',
      [ProjectStatus.CONTENT_READY]: '内容就绪',
      [ProjectStatus.GENERATING]: '生成中',
      [ProjectStatus.COMPLETED]: '已完成',
      [ProjectStatus.ERROR]: '错误',
    };
    return labels[status];
  };

  const ProjectCard = ({ project }: { project: Project }) => (
    <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-soft hover:shadow-medium transition-all duration-200 overflow-hidden group">
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-secondary-900 dark:text-white mb-1 line-clamp-1">
              {project.title}
            </h3>
            <p className="text-sm text-secondary-500 dark:text-secondary-400 line-clamp-2">
              {project.description || project.topic}
            </p>
          </div>
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setActionMenuProject(actionMenuProject === project.id ? null : project.id);
              }}
              className="p-1 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors opacity-0 group-hover:opacity-100"
            >
              <MoreVertical className="w-5 h-5 text-secondary-500" />
            </button>
            
            {actionMenuProject === project.id && (
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-secondary-700 rounded-lg shadow-lg border border-secondary-200 dark:border-secondary-600 z-10">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleOpenProject(project);
                    setActionMenuProject(null);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-secondary-100 dark:hover:bg-secondary-600 flex items-center space-x-2"
                >
                  <Edit className="w-4 h-4" />
                  <span>编辑</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDuplicateProject(project);
                    setActionMenuProject(null);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-secondary-100 dark:hover:bg-secondary-600 flex items-center space-x-2"
                >
                  <Copy className="w-4 h-4" />
                  <span>复制</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // Export project
                    setActionMenuProject(null);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-secondary-100 dark:hover:bg-secondary-600 flex items-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>导出</span>
                </button>
                <hr className="my-1 border-secondary-200 dark:border-secondary-600" />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteProject(project);
                    setActionMenuProject(null);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-error-50 dark:hover:bg-error-900 text-error-600 dark:text-error-400 flex items-center space-x-2"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>删除</span>
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-4 text-sm text-secondary-500 dark:text-secondary-400 mb-4">
          <div className="flex items-center space-x-1">
            <FileText className="w-4 h-4" />
            <span>{project.settings.slidesCount} 页</span>
          </div>
          <div className="flex items-center space-x-1">
            <Calendar className="w-4 h-4" />
            <span>{new Date(project.updatedAt).toLocaleDateString('zh-CN')}</span>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getStatusIcon(project.status)}
            <span className="text-sm text-secondary-600 dark:text-secondary-300">
              {getStatusLabel(project.status)}
            </span>
          </div>
          
          <button
            onClick={() => handleOpenProject(project)}
            className="flex items-center space-x-1 px-3 py-1.5 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            <Play className="w-4 h-4" />
            <span>打开</span>
          </button>
        </div>
      </div>
    </div>
  );

  const ProjectListItem = ({ project }: { project: Project }) => (
    <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-soft hover:shadow-medium transition-all duration-200 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4 flex-1">
          {getStatusIcon(project.status)}
          <div className="flex-1">
            <h3 className="text-base font-semibold text-secondary-900 dark:text-white">
              {project.title}
            </h3>
            <p className="text-sm text-secondary-500 dark:text-secondary-400">
              {project.description || project.topic}
            </p>
          </div>
          <div className="flex items-center space-x-6 text-sm text-secondary-500 dark:text-secondary-400">
            <div className="flex items-center space-x-1">
              <FileText className="w-4 h-4" />
              <span>{project.settings.slidesCount} 页</span>
            </div>
            <div className="flex items-center space-x-1">
              <Calendar className="w-4 h-4" />
              <span>{new Date(project.updatedAt).toLocaleDateString('zh-CN')}</span>
            </div>
            <span className="text-secondary-600 dark:text-secondary-300">
              {getStatusLabel(project.status)}
            </span>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => handleOpenProject(project)}
            className="flex items-center space-x-1 px-3 py-1.5 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            <Play className="w-4 h-4" />
            <span>打开</span>
          </button>
          
          <div className="relative">
            <button
              onClick={() => setActionMenuProject(actionMenuProject === project.id ? null : project.id)}
              className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
            >
              <MoreVertical className="w-5 h-5 text-secondary-500" />
            </button>
            
            {actionMenuProject === project.id && (
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-secondary-700 rounded-lg shadow-lg border border-secondary-200 dark:border-secondary-600 z-10">
                <button
                  onClick={() => {
                    handleDuplicateProject(project);
                    setActionMenuProject(null);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-secondary-100 dark:hover:bg-secondary-600 flex items-center space-x-2"
                >
                  <Copy className="w-4 h-4" />
                  <span>复制</span>
                </button>
                <button
                  onClick={() => {
                    // Export project
                    setActionMenuProject(null);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-secondary-100 dark:hover:bg-secondary-600 flex items-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>导出</span>
                </button>
                <hr className="my-1 border-secondary-200 dark:border-secondary-600" />
                <button
                  onClick={() => {
                    handleDeleteProject(project);
                    setActionMenuProject(null);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-error-50 dark:hover:bg-error-900 text-error-600 dark:text-error-400 flex items-center space-x-2"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>删除</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900 dark:text-white">
            我的项目
          </h1>
          <p className="text-secondary-500 dark:text-secondary-400">
            管理和组织您的PPT项目
          </p>
        </div>
        
        <button
          onClick={() => openModal('createProject')}
          className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
        >
          <Plus className="w-5 h-5" />
          <span>新建项目</span>
        </button>
      </div>

      {/* Toolbar */}
      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-soft p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <input
                type="text"
                placeholder="搜索项目..."
                onChange={handleSearch}
                className="w-full pl-10 pr-4 py-2 bg-secondary-50 dark:bg-secondary-700 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all"
              />
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-secondary-400" />
            </div>

            {/* Status filter */}
            <div className="relative">
              <button
                onClick={() => setShowFilterMenu(!showFilterMenu)}
                className="flex items-center space-x-2 px-4 py-2 bg-secondary-100 dark:bg-secondary-700 rounded-lg hover:bg-secondary-200 dark:hover:bg-secondary-600 transition-colors"
              >
                <Filter className="w-5 h-5" />
                <span>筛选</span>
              </button>
              
              {showFilterMenu && (
                <div className="absolute top-full mt-2 w-48 bg-white dark:bg-secondary-700 rounded-lg shadow-lg border border-secondary-200 dark:border-secondary-600 z-10">
                  <button
                    onClick={() => {
                      handleStatusFilter('all');
                      setShowFilterMenu(false);
                    }}
                    className={`w-full text-left px-4 py-2 hover:bg-secondary-100 dark:hover:bg-secondary-600 ${
                      selectedStatus === 'all' ? 'bg-secondary-100 dark:bg-secondary-600' : ''
                    }`}
                  >
                    全部
                  </button>
                  {Object.values(ProjectStatus).map(status => (
                    <button
                      key={status}
                      onClick={() => {
                        handleStatusFilter(status);
                        setShowFilterMenu(false);
                      }}
                      className={`w-full text-left px-4 py-2 hover:bg-secondary-100 dark:hover:bg-secondary-600 ${
                        selectedStatus === status ? 'bg-secondary-100 dark:bg-secondary-600' : ''
                      }`}
                    >
                      {getStatusLabel(status)}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Sort */}
            <select
              value={sortOption}
              onChange={(e) => handleSort(e.target.value as SortBy)}
              className="px-4 py-2 bg-secondary-100 dark:bg-secondary-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="updatedAt">最近更新</option>
              <option value="createdAt">创建时间</option>
              <option value="title">名称</option>
            </select>
          </div>

          {/* View mode toggle */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'grid'
                  ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                  : 'hover:bg-secondary-100 dark:hover:bg-secondary-700'
              }`}
            >
              <Grid className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'list'
                  ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                  : 'hover:bg-secondary-100 dark:hover:bg-secondary-700'
              }`}
            >
              <List className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Projects */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-soft p-12 text-center">
          <FileText className="w-16 h-16 text-secondary-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-secondary-900 dark:text-white mb-2">
            暂无项目
          </h3>
          <p className="text-secondary-500 dark:text-secondary-400 mb-6">
            创建您的第一个PPT项目开始使用
          </p>
          <button
            onClick={() => openModal('createProject')}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            <Plus className="w-5 h-5" />
            <span>创建项目</span>
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredProjects.map((project) => (
            <ProjectListItem key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  );
};

export default ProjectManager;