import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Slide, SlideContent } from '@/types/models';
import {
  ChevronLeft,
  ChevronRight,
  Grid,
  Maximize2,
  Minimize2,
  Download,
  Share2,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Copy,
  Trash2,
  Edit3,
  FileText,
  Image as ImageIcon,
  BarChart3,
  List,
} from 'lucide-react';

interface SlidePreviewProps {
  slides: Slide[];
  currentSlideIndex?: number;
  onSlideChange?: (index: number) => void;
  onSlideEdit?: (slide: Slide, index: number) => void;
  onSlideDelete?: (index: number) => void;
  onSlideReorder?: (fromIndex: number, toIndex: number) => void;
  showThumbnails?: boolean;
  autoPlay?: boolean;
  autoPlayInterval?: number;
  readOnly?: boolean;
  className?: string;
}

type ViewMode = 'single' | 'grid' | 'list';
type ContentType = 'text' | 'image' | 'chart' | 'mixed';

const SlidePreview: React.FC<SlidePreviewProps> = ({
  slides,
  currentSlideIndex = 0,
  onSlideChange,
  onSlideEdit,
  onSlideDelete,
  onSlideReorder,
  showThumbnails = true,
  autoPlay = false,
  autoPlayInterval = 5000,
  readOnly = false,
  className = '',
}) => {
  const [activeIndex, setActiveIndex] = useState(currentSlideIndex);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [viewMode, setViewMode] = useState<ViewMode>('single');
  const [zoom, setZoom] = useState(100);
  const [draggedSlide, setDraggedSlide] = useState<number | null>(null);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const autoPlayTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Update active index when prop changes
  useEffect(() => {
    setActiveIndex(currentSlideIndex);
  }, [currentSlideIndex]);

  // Auto-play functionality
  useEffect(() => {
    if (isPlaying && slides.length > 1) {
      autoPlayTimerRef.current = setTimeout(() => {
        handleNext();
      }, autoPlayInterval);
    }
    
    return () => {
      if (autoPlayTimerRef.current) {
        clearTimeout(autoPlayTimerRef.current);
      }
    };
  }, [isPlaying, activeIndex, autoPlayInterval, slides.length]);

  // Handle slide navigation
  const handlePrevious = () => {
    const newIndex = activeIndex > 0 ? activeIndex - 1 : slides.length - 1;
    setActiveIndex(newIndex);
    onSlideChange?.(newIndex);
  };

  const handleNext = () => {
    const newIndex = activeIndex < slides.length - 1 ? activeIndex + 1 : 0;
    setActiveIndex(newIndex);
    onSlideChange?.(newIndex);
  };

  const handleSlideSelect = (index: number) => {
    setActiveIndex(index);
    onSlideChange?.(index);
    setViewMode('single');
  };

  // Toggle fullscreen
  const toggleFullscreen = () => {
    if (!isFullscreen) {
      containerRef.current?.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
    setIsFullscreen(!isFullscreen);
  };

  // Toggle play/pause
  const togglePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  // Handle zoom
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 10, 200));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 10, 50));
  };

  const handleZoomReset = () => {
    setZoom(100);
  };

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (viewMode === 'single') {
        switch (e.key) {
          case 'ArrowLeft':
            handlePrevious();
            break;
          case 'ArrowRight':
            handleNext();
            break;
          case ' ':
            e.preventDefault();
            togglePlayPause();
            break;
          case 'f':
            toggleFullscreen();
            break;
          case 'Escape':
            if (isFullscreen) {
              toggleFullscreen();
            }
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeIndex, viewMode, isFullscreen, isPlaying]);

  // Handle drag and drop for reordering
  const handleDragStart = (index: number) => {
    setDraggedSlide(index);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    if (draggedSlide !== null && draggedSlide !== targetIndex) {
      onSlideReorder?.(draggedSlide, targetIndex);
    }
    setDraggedSlide(null);
  };

  // Get content type icon
  const getContentIcon = (content: SlideContent): React.ReactNode => {
    if (content.image) return <ImageIcon className="w-4 h-4" />;
    if (content.chart) return <BarChart3 className="w-4 h-4" />;
    if (content.bullets && content.bullets.length > 0) return <List className="w-4 h-4" />;
    return <FileText className="w-4 h-4" />;
  };

  // Render slide content
  const renderSlideContent = (slide: Slide, index: number) => {
    return (
      <div className="h-full flex flex-col bg-white dark:bg-secondary-800 rounded-lg shadow-lg p-8">
        {/* Slide header */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-secondary-900 dark:text-white mb-2">
            {slide.title}
          </h2>
          {slide.subtitle && (
            <p className="text-lg text-secondary-600 dark:text-secondary-400">
              {slide.subtitle}
            </p>
          )}
        </div>

        {/* Slide content */}
        <div className="flex-1 overflow-auto">
          {slide.content.text && (
            <p className="text-secondary-700 dark:text-secondary-300 mb-4">
              {slide.content.text}
            </p>
          )}
          
          {slide.content.bullets && slide.content.bullets.length > 0 && (
            <ul className="list-disc list-inside space-y-2 mb-4">
              {slide.content.bullets.map((bullet, i) => (
                <li key={i} className="text-secondary-700 dark:text-secondary-300">
                  {bullet}
                </li>
              ))}
            </ul>
          )}
          
          {slide.content.image && (
            <div className="mb-4">
              <img
                src={slide.content.image.url}
                alt={slide.content.image.alt || ''}
                className="max-w-full h-auto rounded-lg"
              />
              {slide.content.image.caption && (
                <p className="text-sm text-secondary-500 mt-2 text-center">
                  {slide.content.image.caption}
                </p>
              )}
            </div>
          )}
          
          {slide.content.chart && (
            <div className="mb-4 p-4 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
              <p className="text-sm text-secondary-600 dark:text-secondary-400">
                图表: {slide.content.chart.type}
              </p>
              {slide.content.chart.title && (
                <p className="font-semibold mt-2">{slide.content.chart.title}</p>
              )}
            </div>
          )}
        </div>

        {/* Slide footer */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-secondary-200 dark:border-secondary-700">
          <span className="text-sm text-secondary-500">
            {index + 1} / {slides.length}
          </span>
          {slide.notes && (
            <span className="text-sm text-secondary-500">
              备注: {slide.notes.substring(0, 50)}...
            </span>
          )}
        </div>
      </div>
    );
  };

  // Render single slide view
  const renderSingleView = () => (
    <div className="relative h-full flex flex-col">
      {/* Slide container */}
      <div 
        className="flex-1 overflow-hidden flex items-center justify-center p-4"
        style={{ transform: `scale(${zoom / 100})` }}
      >
        {slides[activeIndex] && renderSlideContent(slides[activeIndex], activeIndex)}
      </div>

      {/* Navigation controls */}
      <div className="absolute inset-y-0 left-0 flex items-center">
        <button
          onClick={handlePrevious}
          className="p-2 m-2 bg-white dark:bg-secondary-800 rounded-full shadow-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
          disabled={slides.length <= 1}
        >
          <ChevronLeft className="w-6 h-6" />
        </button>
      </div>
      
      <div className="absolute inset-y-0 right-0 flex items-center">
        <button
          onClick={handleNext}
          className="p-2 m-2 bg-white dark:bg-secondary-800 rounded-full shadow-lg hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
          disabled={slides.length <= 1}
        >
          <ChevronRight className="w-6 h-6" />
        </button>
      </div>
    </div>
  );

  // Render grid view
  const renderGridView = () => (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4 overflow-auto">
      {slides.map((slide, index) => (
        <div
          key={index}
          className={`
            relative group cursor-pointer rounded-lg overflow-hidden shadow-md
            hover:shadow-lg transition-shadow
            ${activeIndex === index ? 'ring-2 ring-primary-500' : ''}
          `}
          onClick={() => handleSlideSelect(index)}
          draggable={!readOnly}
          onDragStart={() => handleDragStart(index)}
          onDragOver={handleDragOver}
          onDrop={e => handleDrop(e, index)}
        >
          <div className="aspect-video bg-white dark:bg-secondary-800 p-4">
            <h3 className="text-sm font-semibold truncate mb-2">{slide.title}</h3>
            <div className="text-xs text-secondary-500">
              {getContentIcon(slide.content)}
            </div>
          </div>
          
          {!readOnly && (
            <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={e => {
                  e.stopPropagation();
                  onSlideEdit?.(slide, index);
                }}
                className="p-1 bg-white dark:bg-secondary-800 rounded shadow"
              >
                <Edit3 className="w-3 h-3" />
              </button>
              <button
                onClick={e => {
                  e.stopPropagation();
                  onSlideDelete?.(index);
                }}
                className="p-1 bg-white dark:bg-secondary-800 rounded shadow"
              >
                <Trash2 className="w-3 h-3 text-red-500" />
              </button>
            </div>
          )}
          
          <div className="absolute bottom-2 left-2 bg-black bg-opacity-50 text-white text-xs px-1 rounded">
            {index + 1}
          </div>
        </div>
      ))}
    </div>
  );

  // Render list view
  const renderListView = () => (
    <div className="overflow-auto">
      <table className="w-full">
        <thead className="bg-secondary-50 dark:bg-secondary-700 sticky top-0">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-semibold text-secondary-600 dark:text-secondary-300">
              #
            </th>
            <th className="px-4 py-2 text-left text-xs font-semibold text-secondary-600 dark:text-secondary-300">
              标题
            </th>
            <th className="px-4 py-2 text-left text-xs font-semibold text-secondary-600 dark:text-secondary-300">
              类型
            </th>
            <th className="px-4 py-2 text-left text-xs font-semibold text-secondary-600 dark:text-secondary-300">
              内容
            </th>
            {!readOnly && (
              <th className="px-4 py-2 text-right text-xs font-semibold text-secondary-600 dark:text-secondary-300">
                操作
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {slides.map((slide, index) => (
            <tr
              key={index}
              className={`
                border-b border-secondary-200 dark:border-secondary-700 
                hover:bg-secondary-50 dark:hover:bg-secondary-700 cursor-pointer
                ${activeIndex === index ? 'bg-primary-50 dark:bg-primary-900/20' : ''}
              `}
              onClick={() => handleSlideSelect(index)}
            >
              <td className="px-4 py-2 text-sm">{index + 1}</td>
              <td className="px-4 py-2 text-sm font-medium">{slide.title}</td>
              <td className="px-4 py-2 text-sm">
                <span className="inline-flex items-center">
                  {getContentIcon(slide.content)}
                </span>
              </td>
              <td className="px-4 py-2 text-sm text-secondary-600 dark:text-secondary-400">
                {slide.content.text?.substring(0, 50)}...
              </td>
              {!readOnly && (
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      onSlideEdit?.(slide, index);
                    }}
                    className="p-1 hover:bg-secondary-200 dark:hover:bg-secondary-600 rounded"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      onSlideDelete?.(index);
                    }}
                    className="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded ml-2"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div
      ref={containerRef}
      className={`flex flex-col h-full bg-secondary-50 dark:bg-secondary-900 ${className}`}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-secondary-800 border-b border-secondary-200 dark:border-secondary-700">
        <div className="flex items-center gap-2">
          {/* View mode buttons */}
          <button
            onClick={() => setViewMode('single')}
            className={`p-2 rounded ${
              viewMode === 'single'
                ? 'bg-primary-500 text-white'
                : 'hover:bg-secondary-100 dark:hover:bg-secondary-700'
            }`}
            title="单页视图"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 rounded ${
              viewMode === 'grid'
                ? 'bg-primary-500 text-white'
                : 'hover:bg-secondary-100 dark:hover:bg-secondary-700'
            }`}
            title="网格视图"
          >
            <Grid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 rounded ${
              viewMode === 'list'
                ? 'bg-primary-500 text-white'
                : 'hover:bg-secondary-100 dark:hover:bg-secondary-700'
            }`}
            title="列表视图"
          >
            <List className="w-4 h-4" />
          </button>
          
          <div className="w-px h-6 bg-secondary-300 dark:bg-secondary-600 mx-1" />
          
          {/* Playback controls */}
          {viewMode === 'single' && (
            <>
              <button
                onClick={() => setActiveIndex(0)}
                className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded"
                title="第一页"
              >
                <SkipBack className="w-4 h-4" />
              </button>
              <button
                onClick={togglePlayPause}
                className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded"
                title={isPlaying ? '暂停' : '播放'}
              >
                {isPlaying ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
              </button>
              <button
                onClick={() => setActiveIndex(slides.length - 1)}
                className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded"
                title="最后一页"
              >
                <SkipForward className="w-4 h-4" />
              </button>
              
              <div className="w-px h-6 bg-secondary-300 dark:bg-secondary-600 mx-1" />
              
              {/* Zoom controls */}
              <button
                onClick={handleZoomOut}
                className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded"
                title="缩小"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="px-2 text-sm">{zoom}%</span>
              <button
                onClick={handleZoomIn}
                className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded"
                title="放大"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={handleZoomReset}
                className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded"
                title="重置缩放"
              >
                <RotateCw className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {viewMode === 'single' && (
            <button
              onClick={toggleFullscreen}
              className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded"
              title={isFullscreen ? '退出全屏' : '全屏'}
            >
              {isFullscreen ? (
                <Minimize2 className="w-4 h-4" />
              ) : (
                <Maximize2 className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'single' && renderSingleView()}
        {viewMode === 'grid' && renderGridView()}
        {viewMode === 'list' && renderListView()}
      </div>

      {/* Thumbnails */}
      {showThumbnails && viewMode === 'single' && (
        <div className="flex gap-2 p-2 bg-white dark:bg-secondary-800 border-t border-secondary-200 dark:border-secondary-700 overflow-x-auto">
          {slides.map((slide, index) => (
            <button
              key={index}
              onClick={() => handleSlideSelect(index)}
              className={`
                flex-shrink-0 w-24 h-16 rounded border-2 overflow-hidden
                ${
                  activeIndex === index
                    ? 'border-primary-500'
                    : 'border-secondary-300 dark:border-secondary-600'
                }
              `}
            >
              <div className="w-full h-full bg-white dark:bg-secondary-700 p-1">
                <p className="text-xs truncate">{slide.title}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default SlidePreview;