import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ImageService } from '@/services/ImageService';
import { ImageSearchResult } from '@/types/models';
import { useUIStore } from '@/store/uiStore';
import {
  Search,
  Image as ImageIcon,
  Download,
  Plus,
  X,
  Loader2,
  Grid,
  List,
  Filter,
  Upload,
  Link2,
  History,
  Star,
  StarOff,
  Copy,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface ImageGalleryProps {
  onImageSelect?: (image: ImageSearchResult) => void;
  selectedImages?: string[];
  multiSelect?: boolean;
  showUpload?: boolean;
  maxSelections?: number;
  autoSearch?: string;
  onClose?: () => void;
}

type ViewMode = 'grid' | 'list';
type ImageSource = 'search' | 'uploaded' | 'favorites' | 'history';

interface UploadedImage {
  id: string;
  url: string;
  name: string;
  size: number;
  type: string;
  uploadedAt: Date;
}

const ImageGallery: React.FC<ImageGalleryProps> = ({
  onImageSelect,
  selectedImages = [],
  multiSelect = false,
  showUpload = true,
  maxSelections = 10,
  autoSearch,
  onClose,
}) => {
  const imageService = useRef(new ImageService()).current;
  const { setLoading, showError, showSuccess } = useUIStore();
  
  const [searchQuery, setSearchQuery] = useState(autoSearch || '');
  const [searchResults, setSearchResults] = useState<ImageSearchResult[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    new Set(selectedImages)
  );
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [imageSource, setImageSource] = useState<ImageSource>('search');
  const [isSearching, setIsSearching] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [favoriteImages, setFavoriteImages] = useState<Set<string>>(new Set());
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [previewImage, setPreviewImage] = useState<ImageSearchResult | null>(null);
  const [imageUrlInput, setImageUrlInput] = useState('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Load favorites and history on mount
  useEffect(() => {
    loadFavorites();
    loadSearchHistory();
    if (autoSearch) {
      handleSearch(autoSearch);
    }
  }, []);

  // Load favorites from localStorage
  const loadFavorites = () => {
    const saved = localStorage.getItem('image-favorites');
    if (saved) {
      setFavoriteImages(new Set(JSON.parse(saved)));
    }
  };

  // Save favorites to localStorage
  const saveFavorites = (favorites: Set<string>) => {
    localStorage.setItem('image-favorites', JSON.stringify(Array.from(favorites)));
  };

  // Load search history
  const loadSearchHistory = async () => {
    const history = await imageService.getSearchHistory();
    setSearchHistory(history);
  };

  // Handle image search
  const handleSearch = async (query?: string) => {
    const searchTerm = query || searchQuery.trim();
    if (!searchTerm) return;
    
    setIsSearching(true);
    setLoading('imageSearch', true);
    
    try {
      const results = await imageService.searchImages(searchTerm, {
        page: currentPage,
        perPage: 20,
      });
      
      setSearchResults(results);
      setTotalPages(Math.ceil(100 / 20)); // Assuming 100 total results
      
      // Add to search history
      if (!searchHistory.includes(searchTerm)) {
        const newHistory = [searchTerm, ...searchHistory.slice(0, 9)];
        setSearchHistory(newHistory);
      }
      
      showSuccess('图片搜索成功', `找到 ${results.length} 张相关图片`);
    } catch (error) {
      console.error('Image search error:', error);
      showError('搜索失败', '无法搜索图片，请稍后重试');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
      setLoading('imageSearch', false);
    }
  };

  // Handle file upload
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;
    
    Array.from(files).forEach(file => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const uploadedImage: UploadedImage = {
            id: `upload-${Date.now()}-${Math.random()}`,
            url: e.target?.result as string,
            name: file.name,
            size: file.size,
            type: file.type,
            uploadedAt: new Date(),
          };
          setUploadedImages(prev => [...prev, uploadedImage]);
        };
        reader.readAsDataURL(file);
      }
    });
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle URL input
  const handleUrlAdd = () => {
    if (!imageUrlInput.trim()) return;
    
    const uploadedImage: UploadedImage = {
      id: `url-${Date.now()}`,
      url: imageUrlInput.trim(),
      name: 'External Image',
      size: 0,
      type: 'image/external',
      uploadedAt: new Date(),
    };
    
    setUploadedImages(prev => [...prev, uploadedImage]);
    setImageUrlInput('');
    showSuccess('图片添加成功', '外部图片已添加到图库');
  };

  // Toggle image selection
  const toggleImageSelection = (image: ImageSearchResult | UploadedImage) => {
    const imageId = 'id' in image ? image.id : image.url;
    const imageUrl = image.url;
    
    if (multiSelect) {
      const newSelection = new Set(selectedIds);
      if (newSelection.has(imageId)) {
        newSelection.delete(imageId);
      } else if (newSelection.size < maxSelections) {
        newSelection.add(imageId);
      } else {
        showError('选择限制', `最多只能选择 ${maxSelections} 张图片`);
        return;
      }
      setSelectedIds(newSelection);
    } else {
      setSelectedIds(new Set([imageId]));
      if (onImageSelect) {
        onImageSelect({
          url: imageUrl,
          title: 'title' in image ? image.title : image.name,
          source: 'source' in image ? image.source : 'uploaded',
        });
      }
    }
  };

  // Toggle favorite
  const toggleFavorite = (imageUrl: string) => {
    const newFavorites = new Set(favoriteImages);
    if (newFavorites.has(imageUrl)) {
      newFavorites.delete(imageUrl);
    } else {
      newFavorites.add(imageUrl);
    }
    setFavoriteImages(newFavorites);
    saveFavorites(newFavorites);
  };

  // Copy image URL
  const copyImageUrl = (url: string) => {
    navigator.clipboard.writeText(url);
    showSuccess('复制成功', '图片链接已复制到剪贴板');
  };

  // Download image
  const downloadImage = async (url: string, filename: string) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      showSuccess('下载成功', '图片已开始下载');
    } catch (error) {
      showError('下载失败', '无法下载图片');
    }
  };

  // Get filtered images based on source
  const getFilteredImages = () => {
    switch (imageSource) {
      case 'search':
        return searchResults;
      case 'uploaded':
        return uploadedImages;
      case 'favorites':
        return searchResults.filter(img => favoriteImages.has(img.url));
      case 'history':
        // Return cached images from history
        return [];
      default:
        return [];
    }
  };

  // Render image card
  const renderImageCard = (image: ImageSearchResult | UploadedImage) => {
    const imageId = 'id' in image ? image.id : image.url;
    const isSelected = selectedIds.has(imageId);
    const isFavorite = favoriteImages.has(image.url);
    
    return (
      <div
        key={imageId}
        className={`
          relative group rounded-lg overflow-hidden cursor-pointer
          border-2 transition-all duration-200
          ${
            isSelected
              ? 'border-primary-500 shadow-lg scale-105'
              : 'border-transparent hover:border-secondary-300 dark:hover:border-secondary-600'
          }
        `}
        onClick={() => toggleImageSelection(image)}
      >
        <div className="aspect-square bg-secondary-100 dark:bg-secondary-800">
          <img
            src={image.url}
            alt={'title' in image ? image.title : image.name}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).src = '/placeholder-image.png';
            }}
          />
        </div>
        
        {/* Selection indicator */}
        {isSelected && (
          <div className="absolute top-2 left-2 bg-primary-500 text-white rounded-full p-1">
            <CheckCircle className="w-5 h-5" />
          </div>
        )}
        
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-black bg-opacity-50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleFavorite(image.url);
            }}
            className="p-2 bg-white dark:bg-secondary-800 rounded-full hover:bg-secondary-100 dark:hover:bg-secondary-700"
            title={isFavorite ? '取消收藏' : '收藏'}
          >
            {isFavorite ? (
              <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
            ) : (
              <StarOff className="w-4 h-4" />
            )}
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation();
              copyImageUrl(image.url);
            }}
            className="p-2 bg-white dark:bg-secondary-800 rounded-full hover:bg-secondary-100 dark:hover:bg-secondary-700"
            title="复制链接"
          >
            <Copy className="w-4 h-4" />
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation();
              downloadImage(image.url, 'title' in image ? image.title : image.name);
            }}
            className="p-2 bg-white dark:bg-secondary-800 rounded-full hover:bg-secondary-100 dark:hover:bg-secondary-700"
            title="下载"
          >
            <Download className="w-4 h-4" />
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation();
              setPreviewImage(image as ImageSearchResult);
            }}
            className="p-2 bg-white dark:bg-secondary-800 rounded-full hover:bg-secondary-100 dark:hover:bg-secondary-700"
            title="预览"
          >
            <ImageIcon className="w-4 h-4" />
          </button>
        </div>
        
        {/* Image info */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <p className="text-white text-xs truncate">
            {'title' in image ? image.title : image.name}
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-secondary-800 rounded-lg shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-secondary-200 dark:border-secondary-700">
        <h2 className="text-lg font-semibold text-secondary-900 dark:text-white">
          图片库
        </h2>
        
        <div className="flex items-center gap-2">
          {multiSelect && selectedIds.size > 0 && (
            <span className="text-sm text-secondary-600 dark:text-secondary-400">
              已选择 {selectedIds.size} / {maxSelections}
            </span>
          )}
          
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 p-3 border-b border-secondary-200 dark:border-secondary-700">
        {/* Source tabs */}
        <div className="flex gap-1 mr-4">
          <button
            onClick={() => setImageSource('search')}
            className={`px-3 py-1.5 rounded text-sm ${
              imageSource === 'search'
                ? 'bg-primary-500 text-white'
                : 'hover:bg-secondary-100 dark:hover:bg-secondary-700'
            }`}
          >
            搜索
          </button>
          {showUpload && (
            <button
              onClick={() => setImageSource('uploaded')}
              className={`px-3 py-1.5 rounded text-sm ${
                imageSource === 'uploaded'
                  ? 'bg-primary-500 text-white'
                  : 'hover:bg-secondary-100 dark:hover:bg-secondary-700'
              }`}
            >
              已上传
            </button>
          )}
          <button
            onClick={() => setImageSource('favorites')}
            className={`px-3 py-1.5 rounded text-sm ${
              imageSource === 'favorites'
                ? 'bg-primary-500 text-white'
                : 'hover:bg-secondary-100 dark:hover:bg-secondary-700'
            }`}
          >
            收藏
          </button>
          <button
            onClick={() => setImageSource('history')}
            className={`px-3 py-1.5 rounded text-sm ${
              imageSource === 'history'
                ? 'bg-primary-500 text-white'
                : 'hover:bg-secondary-100 dark:hover:bg-secondary-700'
            }`}
          >
            历史
          </button>
        </div>

        {/* Search bar */}
        {imageSource === 'search' && (
          <div className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSearch();
                }}
                placeholder="搜索图片..."
                className="w-full pl-10 pr-4 py-2 bg-secondary-50 dark:bg-secondary-700 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-secondary-400" />
            </div>
            <button
              onClick={() => handleSearch()}
              disabled={isSearching}
              className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50"
            >
              {isSearching ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                '搜索'
              )}
            </button>
          </div>
        )}

        {/* Upload controls */}
        {imageSource === 'uploaded' && showUpload && (
          <div className="flex-1 flex gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
            >
              <Upload className="w-4 h-4" />
              上传图片
            </button>
            
            <div className="flex-1 flex gap-2">
              <input
                type="text"
                value={imageUrlInput}
                onChange={(e) => setImageUrlInput(e.target.value)}
                placeholder="输入图片链接..."
                className="flex-1 px-3 py-2 bg-secondary-50 dark:bg-secondary-700 border border-secondary-200 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                onClick={handleUrlAdd}
                disabled={!imageUrlInput.trim()}
                className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50"
              >
                <Link2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        {/* View mode toggle */}
        <div className="flex gap-1">
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
        </div>
      </div>

      {/* Search history */}
      {imageSource === 'search' && searchHistory.length > 0 && !searchResults.length && (
        <div className="px-4 py-2 border-b border-secondary-200 dark:border-secondary-700">
          <p className="text-sm text-secondary-500 mb-2">搜索历史</p>
          <div className="flex flex-wrap gap-2">
            {searchHistory.map((term, index) => (
              <button
                key={index}
                onClick={() => {
                  setSearchQuery(term);
                  handleSearch(term);
                }}
                className="px-3 py-1 bg-secondary-100 dark:bg-secondary-700 rounded-full text-sm hover:bg-secondary-200 dark:hover:bg-secondary-600"
              >
                <History className="inline w-3 h-3 mr-1" />
                {term}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Image grid/list */}
      <div className="flex-1 overflow-auto p-4">
        {viewMode === 'grid' ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {getFilteredImages().map((image) => renderImageCard(image))}
          </div>
        ) : (
          <div className="space-y-2">
            {getFilteredImages().map((image) => {
              const imageId = 'id' in image ? image.id : image.url;
              const isSelected = selectedIds.has(imageId);
              const isFavorite = favoriteImages.has(image.url);
              
              return (
                <div
                  key={imageId}
                  className={`
                    flex items-center gap-4 p-3 rounded-lg cursor-pointer
                    ${
                      isSelected
                        ? 'bg-primary-50 dark:bg-primary-900/20'
                        : 'hover:bg-secondary-50 dark:hover:bg-secondary-700'
                    }
                  `}
                  onClick={() => toggleImageSelection(image)}
                >
                  <img
                    src={image.url}
                    alt={'title' in image ? image.title : image.name}
                    className="w-16 h-16 object-cover rounded"
                  />
                  <div className="flex-1">
                    <p className="font-medium text-secondary-900 dark:text-white">
                      {'title' in image ? image.title : image.name}
                    </p>
                    {'source' in image && (
                      <p className="text-sm text-secondary-500">
                        来源: {image.source}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFavorite(image.url);
                      }}
                      className="p-1 hover:bg-secondary-200 dark:hover:bg-secondary-600 rounded"
                    >
                      {isFavorite ? (
                        <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                      ) : (
                        <StarOff className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        copyImageUrl(image.url);
                      }}
                      className="p-1 hover:bg-secondary-200 dark:hover:bg-secondary-600 rounded"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        downloadImage(image.url, 'title' in image ? image.title : image.name);
                      }}
                      className="p-1 hover:bg-secondary-200 dark:hover:bg-secondary-600 rounded"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        
        {/* Empty state */}
        {getFilteredImages().length === 0 && !isSearching && (
          <div className="flex flex-col items-center justify-center h-full text-secondary-400">
            <ImageIcon className="w-16 h-16 mb-4" />
            <p className="text-lg">暂无图片</p>
            {imageSource === 'search' && (
              <p className="text-sm mt-2">搜索图片以开始</p>
            )}
            {imageSource === 'uploaded' && showUpload && (
              <button
                onClick={() => fileInputRef.current?.click()}
                className="mt-4 text-primary-500 hover:text-primary-600"
              >
                上传第一张图片
              </button>
            )}
          </div>
        )}
      </div>

      {/* Pagination */}
      {imageSource === 'search' && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 p-3 border-t border-secondary-200 dark:border-secondary-700">
          <button
            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            className="p-1 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded disabled:opacity-50"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          
          <span className="text-sm">
            第 {currentPage} / {totalPages} 页
          </span>
          
          <button
            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            className="p-1 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded disabled:opacity-50"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Footer with selection actions */}
      {multiSelect && selectedIds.size > 0 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-secondary-200 dark:border-secondary-700">
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-sm text-secondary-600 dark:text-secondary-400 hover:text-secondary-800 dark:hover:text-secondary-200"
          >
            清除选择
          </button>
          
          <button
            onClick={() => {
              const selected = Array.from(selectedIds).map(id => {
                const image = getFilteredImages().find(img => 
                  ('id' in img ? img.id : img.url) === id
                );
                return image;
              }).filter(Boolean);
              
              if (onImageSelect && selected.length > 0) {
                selected.forEach(img => {
                  if (img) {
                    onImageSelect({
                      url: img.url,
                      title: 'title' in img ? img.title : img.name,
                      source: 'source' in img ? img.source : 'uploaded',
                    });
                  }
                });
              }
            }}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
          >
            确认选择 ({selectedIds.size})
          </button>
        </div>
      )}

      {/* Image preview modal */}
      {previewImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4"
          onClick={() => setPreviewImage(null)}
        >
          <div
            className="relative max-w-4xl max-h-full"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={previewImage.url}
              alt={previewImage.title}
              className="max-w-full max-h-full rounded-lg"
            />
            <button
              onClick={() => setPreviewImage(null)}
              className="absolute top-2 right-2 p-2 bg-white dark:bg-secondary-800 rounded-full shadow-lg hover:bg-secondary-100 dark:hover:bg-secondary-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImageGallery;