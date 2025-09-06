import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search,
  X,
  Download,
  Check,
  ImageIcon,
  Loader2,
  RefreshCw,
  Grid3x3,
  List,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  Plus,
  Trash2,
  ExternalLink,
  Info,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useImageStore } from '@/store/imageStore';
import { ImageService } from '@/services/ImageService';
import { debounce } from '@/utils/helpers';

export interface ImageItem {
  id: string;
  url: string;
  thumbnailUrl?: string;
  title?: string;
  description?: string;
  width?: number;
  height?: number;
  size?: number;
  source?: string;
  license?: string;
  tags?: string[];
  selected?: boolean;
}

interface ImageGalleryProps {
  onImageSelect?: (images: ImageItem[]) => void;
  onImageAdd?: (image: ImageItem) => void;
  selectedImages?: ImageItem[];
  multiSelect?: boolean;
  maxSelection?: number;
  searchEnabled?: boolean;
  uploadEnabled?: boolean;
  viewMode?: 'grid' | 'list';
  className?: string;
}

const ImageGallery: React.FC<ImageGalleryProps> = ({
  onImageSelect,
  onImageAdd,
  selectedImages = [],
  multiSelect = false,
  maxSelection = 10,
  searchEnabled = true,
  uploadEnabled = false,
  viewMode: initialViewMode = 'grid',
  className,
}) => {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState(initialViewMode);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [previewImage, setPreviewImage] = useState<ImageItem | null>(null);
  const [filters, setFilters] = useState({
    size: 'all', // all, small, medium, large
    orientation: 'all', // all, landscape, portrait, square
    color: 'all', // all, color, grayscale
  });

  const observerRef = useRef<IntersectionObserver | null>(null);
  const lastImageRef = useRef<HTMLDivElement | null>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const imageService = useRef(new ImageService());

  // Initialize selected images
  useEffect(() => {
    const ids = new Set(selectedImages.map(img => img.id));
    setSelectedIds(ids);
  }, [selectedImages]);

  // Load images
  const loadImages = useCallback(async (query: string, pageNum: number, append = false) => {
    if (loading) return;
    
    setLoading(true);
    try {
      const result = await imageService.current.searchImages({
        query: query || 'presentation',
        page: pageNum,
        perPage: 20,
        filters,
      });

      if (result.images.length === 0) {
        setHasMore(false);
      } else {
        setImages(prev => append ? [...prev, ...result.images] : result.images);
        setHasMore(result.hasMore);
      }
    } catch (error) {
      console.error('Failed to load images:', error);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((query: string) => {
      setPage(1);
      setHasMore(true);
      loadImages(query, 1, false);
    }, 500),
    [loadImages]
  );

  // Handle search input
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    debouncedSearch(query);
  };

  // Handle image selection
  const handleImageSelect = (image: ImageItem) => {
    if (multiSelect) {
      const newSelectedIds = new Set(selectedIds);
      
      if (newSelectedIds.has(image.id)) {
        newSelectedIds.delete(image.id);
      } else if (newSelectedIds.size < maxSelection) {
        newSelectedIds.add(image.id);
      } else {
        // Show notification that max selection reached
        return;
      }
      
      setSelectedIds(newSelectedIds);
      
      const selectedImagesList = images.filter(img => newSelectedIds.has(img.id));
      onImageSelect?.(selectedImagesList);
    } else {
      setSelectedIds(new Set([image.id]));
      onImageSelect?.([image]);
    }
  };

  // Handle add image to slide
  const handleAddImage = (image: ImageItem) => {
    onImageAdd?.(image);
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedIds(new Set());
    onImageSelect?.([]);
  };

  // Handle filter change
  const handleFilterChange = (filterType: string, value: string) => {
    setFilters(prev => ({ ...prev, [filterType]: value }));
    setPage(1);
    setHasMore(true);
    loadImages(searchQuery, 1, false);
  };

  // Infinite scroll setup
  useEffect(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore && !loading) {
        setPage(prev => prev + 1);
      }
    });

    if (lastImageRef.current) {
      observerRef.current.observe(lastImageRef.current);
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [hasMore, loading]);

  // Load more images when page changes
  useEffect(() => {
    if (page > 1) {
      loadImages(searchQuery, page, true);
    }
  }, [page, searchQuery, loadImages]);

  // Initial load
  useEffect(() => {
    loadImages('', 1, false);
  }, []);

  // Render image card
  const renderImageCard = (image: ImageItem, index: number) => {
    const isSelected = selectedIds.has(image.id);
    const isLastImage = index === images.length - 1;

    return (
      <div
        key={image.id}
        ref={isLastImage ? lastImageRef : null}
        className={cn(
          'relative group cursor-pointer transition-all',
          viewMode === 'grid' 
            ? 'aspect-video overflow-hidden rounded-lg'
            : 'flex items-center p-3 hover:bg-gray-50 dark:hover:bg-gray-800',
          isSelected && 'ring-2 ring-blue-500'
        )}
        onClick={() => handleImageSelect(image)}
      >
        {viewMode === 'grid' ? (
          <>
            {/* Image thumbnail */}
            <div className="relative w-full h-full bg-gray-100 dark:bg-gray-800">
              <img
                src={image.thumbnailUrl || image.url}
                alt={image.title || 'Image'}
                className="w-full h-full object-cover"
                loading="lazy"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.src = '/placeholder-image.png';
                }}
              />
              
              {/* Selection indicator */}
              {isSelected && (
                <div className="absolute top-2 left-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                  <Check className="w-4 h-4 text-white" />
                </div>
              )}

              {/* Hover overlay */}
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                <div className="flex gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setPreviewImage(image);
                    }}
                    className="p-2 bg-white rounded-full hover:bg-gray-100 transition-colors"
                    title="Preview"
                  >
                    <Eye className="w-4 h-4 text-gray-700" />
                  </button>
                  {onImageAdd && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAddImage(image);
                      }}
                      className="p-2 bg-white rounded-full hover:bg-gray-100 transition-colors"
                      title="Add to slide"
                    >
                      <Plus className="w-4 h-4 text-gray-700" />
                    </button>
                  )}
                  <a
                    href={image.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-2 bg-white rounded-full hover:bg-gray-100 transition-colors"
                    title="Open in new tab"
                  >
                    <ExternalLink className="w-4 h-4 text-gray-700" />
                  </a>
                </div>
              </div>
            </div>

            {/* Image info */}
            {image.title && (
              <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black to-transparent">
                <p className="text-white text-xs truncate">{image.title}</p>
              </div>
            )}
          </>
        ) : (
          // List view
          <>
            <div className="flex items-center flex-1">
              <div className="w-20 h-20 flex-shrink-0 mr-4">
                <img
                  src={image.thumbnailUrl || image.url}
                  alt={image.title || 'Image'}
                  className="w-full h-full object-cover rounded"
                  loading="lazy"
                />
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-sm">{image.title || 'Untitled'}</h4>
                {image.description && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                    {image.description}
                  </p>
                )}
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                  {image.width && image.height && (
                    <span>{image.width}×{image.height}</span>
                  )}
                  {image.size && (
                    <span>{(image.size / 1024 / 1024).toFixed(1)}MB</span>
                  )}
                  {image.source && (
                    <span>{image.source}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 ml-4">
                {isSelected && (
                  <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                    <Check className="w-4 h-4 text-white" />
                  </div>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setPreviewImage(image);
                  }}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <Eye className="w-4 h-4" />
                </button>
                {onImageAdd && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAddImage(image);
                    }}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <div className={cn('bg-white dark:bg-gray-900 rounded-lg shadow-sm', className)}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Image Gallery</h3>
          <div className="flex items-center gap-2">
            {/* View mode toggle */}
            <div className="flex items-center bg-gray-100 dark:bg-gray-800 rounded p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={cn(
                  'p-1.5 rounded transition-colors',
                  viewMode === 'grid'
                    ? 'bg-white dark:bg-gray-700 shadow-sm'
                    : 'hover:bg-gray-200 dark:hover:bg-gray-700'
                )}
                title="Grid view"
              >
                <Grid3x3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={cn(
                  'p-1.5 rounded transition-colors',
                  viewMode === 'list'
                    ? 'bg-white dark:bg-gray-700 shadow-sm'
                    : 'hover:bg-gray-200 dark:hover:bg-gray-700'
                )}
                title="List view"
              >
                <List className="w-4 h-4" />
              </button>
            </div>

            {/* Refresh */}
            <button
              onClick={() => {
                setPage(1);
                setHasMore(true);
                loadImages(searchQuery, 1, false);
              }}
              disabled={loading}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
            </button>

            {/* Clear selection */}
            {selectedIds.size > 0 && (
              <button
                onClick={clearSelection}
                className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded flex items-center gap-1"
              >
                <X className="w-3 h-3" />
                Clear ({selectedIds.size})
              </button>
            )}
          </div>
        </div>

        {/* Search and filters */}
        {searchEnabled && (
          <div className="flex items-center gap-3">
            {/* Search input */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder="Search images..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800"
              />
              {searchQuery && (
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setPage(1);
                    setHasMore(true);
                    loadImages('', 1, false);
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Filters */}
            <div className="flex items-center gap-2">
              <select
                value={filters.size}
                onChange={(e) => handleFilterChange('size', e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md text-sm dark:bg-gray-800"
              >
                <option value="all">All sizes</option>
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large">Large</option>
              </select>

              <select
                value={filters.orientation}
                onChange={(e) => handleFilterChange('orientation', e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md text-sm dark:bg-gray-800"
              >
                <option value="all">All orientations</option>
                <option value="landscape">Landscape</option>
                <option value="portrait">Portrait</option>
                <option value="square">Square</option>
              </select>

              <select
                value={filters.color}
                onChange={(e) => handleFilterChange('color', e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md text-sm dark:bg-gray-800"
              >
                <option value="all">All colors</option>
                <option value="color">Color</option>
                <option value="grayscale">Grayscale</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {images.length === 0 && !loading ? (
          <div className="text-center py-12">
            <ImageIcon className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p className="text-gray-500 dark:text-gray-400">
              {searchQuery ? 'No images found for your search.' : 'No images available.'}
            </p>
          </div>
        ) : (
          <div
            className={cn(
              viewMode === 'grid'
                ? 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4'
                : 'space-y-2'
            )}
          >
            {images.map((image, index) => renderImageCard(image, index))}
          </div>
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
            <span className="ml-2 text-gray-500">Loading images...</span>
          </div>
        )}

        {/* No more images */}
        {!hasMore && images.length > 0 && (
          <div className="text-center py-4 text-gray-500 text-sm">
            No more images to load
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setPreviewImage(null)}
        >
          <div
            className="relative bg-white dark:bg-gray-900 rounded-lg max-w-4xl max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
              <h4 className="font-semibold">{previewImage.title || 'Image Preview'}</h4>
              <button
                onClick={() => setPreviewImage(null)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4">
              <img
                src={previewImage.url}
                alt={previewImage.title || 'Preview'}
                className="max-w-full max-h-[60vh] object-contain mx-auto"
              />
              {previewImage.description && (
                <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                  {previewImage.description}
                </p>
              )}
              <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
                <div className="flex items-center gap-4">
                  {previewImage.width && previewImage.height && (
                    <span>{previewImage.width}×{previewImage.height}px</span>
                  )}
                  {previewImage.size && (
                    <span>{(previewImage.size / 1024 / 1024).toFixed(2)}MB</span>
                  )}
                  {previewImage.source && (
                    <span>Source: {previewImage.source}</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href={previewImage.url}
                    download
                    className="px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors flex items-center gap-1"
                  >
                    <Download className="w-3 h-3" />
                    Download
                  </a>
                  {onImageAdd && (
                    <button
                      onClick={() => {
                        handleAddImage(previewImage);
                        setPreviewImage(null);
                      }}
                      className="px-3 py-1.5 bg-green-500 text-white rounded hover:bg-green-600 transition-colors flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      Add to Slide
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImageGallery;