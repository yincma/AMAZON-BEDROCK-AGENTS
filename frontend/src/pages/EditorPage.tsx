import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProjectStore } from '@/store/projectStore';
import { useUIStore } from '@/store/uiStore';
import { OutlineEditor } from '@/components/editor/OutlineEditor';
import { ContentEditor } from '@/components/editor/ContentEditor';
import { SlidePreview } from '@/components/preview/SlidePreview';
import { ImageGallery } from '@/components/media/ImageGallery';
import { Project, Slide } from '@/types/models';
import { 
  DocumentTextIcon, 
  PhotoIcon, 
  PresentationChartBarIcon,
  ArrowLeftIcon,
  CloudArrowDownIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import { showToast } from '@/store/uiStore';

const EditorPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { currentProject, loadProject, updateProject, generatePPT } = useProjectStore();
  const { setLoading } = useUIStore();
  
  const [activeTab, setActiveTab] = useState<'outline' | 'content' | 'preview'>('outline');
  const [selectedSlide, setSelectedSlide] = useState<Slide | null>(null);
  const [showImageGallery, setShowImageGallery] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    if (projectId && (!currentProject || currentProject.id !== projectId)) {
      loadProject(projectId);
    }
  }, [projectId, currentProject, loadProject]);

  useEffect(() => {
    if (currentProject && currentProject.slides.length > 0 && !selectedSlide) {
      setSelectedSlide(currentProject.slides[0]);
    }
  }, [currentProject, selectedSlide]);

  const handleOutlineChange = (outline: any) => {
    if (currentProject) {
      updateProject(currentProject.id, { outline });
      showToast.success('大纲更新', '大纲已成功更新');
    }
  };

  const handleContentChange = (content: string) => {
    if (currentProject && selectedSlide) {
      const updatedSlides = currentProject.slides.map(slide =>
        slide.id === selectedSlide.id ? { ...slide, content } : slide
      );
      updateProject(currentProject.id, { slides: updatedSlides });
      setSelectedSlide({ ...selectedSlide, content });
    }
  };

  const handleGeneratePPT = async () => {
    if (!currentProject) return;
    
    setIsGenerating(true);
    setLoading(true, '正在生成PPT...');
    
    try {
      const result = await generatePPT(currentProject.id);
      if (result.downloadUrl) {
        showToast.success('生成成功', 'PPT已成功生成！');
        // 下载文件
        const link = document.createElement('a');
        link.href = result.downloadUrl;
        link.download = `${currentProject.title}.pptx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch (error) {
      showToast.error('生成失败', 'PPT生成失败，请重试');
      console.error('Generate PPT error:', error);
    } finally {
      setIsGenerating(false);
      setLoading(false);
    }
  };

  const handleImageSelect = (imageUrl: string) => {
    if (currentProject && selectedSlide) {
      const updatedSlides = currentProject.slides.map(slide =>
        slide.id === selectedSlide.id 
          ? { ...slide, images: [...(slide.images || []), { url: imageUrl, alt: '', position: 'right' }] }
          : slide
      );
      updateProject(currentProject.id, { slides: updatedSlides });
      setShowImageGallery(false);
      showToast.success('添加成功', '图片已添加到幻灯片');
    }
  };

  if (!currentProject) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-secondary-600 dark:text-secondary-400 mb-4">
            项目未找到
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn btn-primary"
          >
            返回仪表板
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-white dark:bg-secondary-800 border-b border-secondary-200 dark:border-secondary-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded-lg transition-colors"
            >
              <ArrowLeftIcon className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-semibold text-secondary-900 dark:text-white">
                {currentProject.title}
              </h1>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">
                {currentProject.slides.length} 张幻灯片
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowImageGallery(true)}
              className="btn btn-secondary"
            >
              <PhotoIcon className="w-5 h-5 mr-2" />
              添加图片
            </button>
            <button
              onClick={handleGeneratePPT}
              disabled={isGenerating}
              className="btn btn-primary"
            >
              {isGenerating ? (
                <>
                  <SparklesIcon className="w-5 h-5 mr-2 animate-pulse" />
                  生成中...
                </>
              ) : (
                <>
                  <CloudArrowDownIcon className="w-5 h-5 mr-2" />
                  生成PPT
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white dark:bg-secondary-800 border-b border-secondary-200 dark:border-secondary-700 px-6">
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab('outline')}
            className={`py-3 px-1 border-b-2 transition-colors ${
              activeTab === 'outline'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200'
            }`}
          >
            <DocumentTextIcon className="w-5 h-5 inline-block mr-2" />
            大纲
          </button>
          <button
            onClick={() => setActiveTab('content')}
            className={`py-3 px-1 border-b-2 transition-colors ${
              activeTab === 'content'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200'
            }`}
          >
            <DocumentTextIcon className="w-5 h-5 inline-block mr-2" />
            内容
          </button>
          <button
            onClick={() => setActiveTab('preview')}
            className={`py-3 px-1 border-b-2 transition-colors ${
              activeTab === 'preview'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200'
            }`}
          >
            <PresentationChartBarIcon className="w-5 h-5 inline-block mr-2" />
            预览
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
          {/* Left Panel - Editor */}
          <div className="bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 overflow-hidden">
            {activeTab === 'outline' && (
              <OutlineEditor
                outline={currentProject.outline}
                onOutlineChange={handleOutlineChange}
              />
            )}
            {activeTab === 'content' && selectedSlide && (
              <ContentEditor
                content={selectedSlide.content}
                onChange={handleContentChange}
              />
            )}
            {activeTab === 'preview' && (
              <div className="p-6">
                <p className="text-secondary-600 dark:text-secondary-400">
                  全屏预览模式
                </p>
              </div>
            )}
          </div>

          {/* Right Panel - Preview */}
          <div className="bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 overflow-hidden">
            {selectedSlide ? (
              <SlidePreview
                slide={selectedSlide}
                template="default"
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-secondary-500 dark:text-secondary-400">
                  选择一张幻灯片进行预览
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Slide Navigation */}
      <div className="bg-white dark:bg-secondary-800 border-t border-secondary-200 dark:border-secondary-700 px-6 py-4">
        <div className="flex space-x-2 overflow-x-auto">
          {currentProject.slides.map((slide, index) => (
            <button
              key={slide.id}
              onClick={() => setSelectedSlide(slide)}
              className={`flex-shrink-0 w-32 h-20 border-2 rounded-lg p-2 transition-all ${
                selectedSlide?.id === slide.id
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-secondary-200 dark:border-secondary-700 hover:border-secondary-300 dark:hover:border-secondary-600'
              }`}
            >
              <div className="text-xs text-left">
                <p className="font-medium text-secondary-900 dark:text-white truncate">
                  {slide.title}
                </p>
                <p className="text-secondary-500 dark:text-secondary-400 mt-1">
                  幻灯片 {index + 1}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Image Gallery Modal */}
      {showImageGallery && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-secondary-800 rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b border-secondary-200 dark:border-secondary-700">
              <h2 className="text-lg font-semibold">选择图片</h2>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              <ImageGallery
                onImageSelect={handleImageSelect}
                searchQuery={selectedSlide?.title || ''}
              />
            </div>
            <div className="p-4 border-t border-secondary-200 dark:border-secondary-700">
              <button
                onClick={() => setShowImageGallery(false)}
                className="btn btn-secondary"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EditorPage;