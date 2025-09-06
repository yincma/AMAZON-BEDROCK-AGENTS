import ApiService from './ApiService';
import { StorageService } from './StorageService';
import {
  SearchImagesRequest,
  SearchImagesResponse,
  ApiResponse,
} from '@/types/api';
import { Image } from '@/types/models';

// Cache configuration
const CACHE_CONFIG = {
  TTL: 3600000, // 1 hour
  MAX_CACHED_QUERIES: 50,
  CACHE_KEY_PREFIX: 'image_search_',
};

// Image search filters
export interface ImageSearchFilters {
  query: string;
  count?: number;
  safeSearch?: boolean;
  license?: 'all' | 'creative_commons' | 'commercial';
  orientation?: 'landscape' | 'portrait' | 'square';
  size?: 'small' | 'medium' | 'large';
  color?: 'color' | 'grayscale' | 'transparent';
  imageType?: 'photo' | 'illustration' | 'vector' | 'gif';
}

// Search history item
export interface SearchHistoryItem {
  query: string;
  timestamp: Date;
  resultCount: number;
  filters?: Partial<ImageSearchFilters>;
}

/**
 * Image Search Service
 * Handles image search operations and caching
 */
export class ImageService extends ApiService {
  private storageService: StorageService;
  private searchHistory: SearchHistoryItem[] = [];
  private cachedQueries: Map<string, { data: Image[]; timestamp: number }> = new Map();

  constructor() {
    super();
    this.storageService = new StorageService();
    this.loadSearchHistory();
  }

  /**
   * Search for images
   */
  async searchImages(filters: ImageSearchFilters): Promise<ApiResponse<Image[]>> {
    try {
      // Check cache first
      const cacheKey = this.getCacheKey(filters);
      const cachedResult = await this.getCachedSearch(cacheKey);
      
      if (cachedResult) {
        return {
          success: true,
          data: cachedResult,
          metadata: {
            fromCache: true,
            timestamp: new Date().toISOString(),
          },
        };
      }

      // Prepare request
      const request: SearchImagesRequest = {
        query: filters.query,
        count: filters.count || 20,
        safeSearch: filters.safeSearch ?? true,
        license: filters.license || 'all',
        orientation: filters.orientation,
      };

      // Make API call
      const response = await this.post<SearchImagesResponse>('/images/search', request);

      if (response.success && response.data) {
        const images = response.data.images;
        
        // Cache the results
        await this.cacheSearchResults(cacheKey, images);
        
        // Update search history
        this.addToSearchHistory({
          query: filters.query,
          timestamp: new Date(),
          resultCount: images.length,
          filters,
        });

        return {
          success: true,
          data: images,
        };
      }

      return {
        success: false,
        error: response.error || {
          code: 'SEARCH_FAILED',
          message: 'Failed to search images',
        },
      };
    } catch (error) {
      console.error('Image search failed:', error);
      return {
        success: false,
        error: {
          code: 'SEARCH_ERROR',
          message: error instanceof Error ? error.message : 'Unknown error occurred',
        },
      };
    }
  }

  /**
   * Get image suggestions based on content
   */
  async getImageSuggestions(content: string, count: number = 5): Promise<Image[]> {
    try {
      // Extract keywords from content
      const keywords = this.extractKeywords(content);
      
      if (keywords.length === 0) {
        return [];
      }

      // Search for images using extracted keywords
      const response = await this.searchImages({
        query: keywords.join(' '),
        count,
        safeSearch: true,
      });

      return response.success && response.data ? response.data : [];
    } catch (error) {
      console.error('Failed to get image suggestions:', error);
      return [];
    }
  }

  /**
   * Batch search for multiple queries
   */
  async batchSearchImages(queries: string[]): Promise<Map<string, Image[]>> {
    const results = new Map<string, Image[]>();

    // Process queries in parallel with rate limiting
    const batchSize = 3;
    for (let i = 0; i < queries.length; i += batchSize) {
      const batch = queries.slice(i, i + batchSize);
      const promises = batch.map(query => 
        this.searchImages({ query, count: 10 })
      );

      const batchResults = await Promise.all(promises);
      
      batch.forEach((query, index) => {
        const result = batchResults[index];
        if (result.success && result.data) {
          results.set(query, result.data);
        } else {
          results.set(query, []);
        }
      });

      // Add delay between batches to avoid rate limiting
      if (i + batchSize < queries.length) {
        await this.delay(500);
      }
    }

    return results;
  }

  /**
   * Get trending or recommended images
   */
  async getTrendingImages(category?: string): Promise<Image[]> {
    try {
      const response = await this.get<{ images: Image[] }>(`/images/trending${category ? `?category=${category}` : ''}`);
      return response.success && response.data ? response.data.images : [];
    } catch (error) {
      console.error('Failed to get trending images:', error);
      return [];
    }
  }

  /**
   * Download image from URL
   */
  async downloadImage(url: string): Promise<Blob | null> {
    try {
      // Use proxy endpoint to avoid CORS issues
      const response = await this.post<{ data: string }>('/images/download', { url });
      
      if (response.success && response.data) {
        // Convert base64 to blob
        const base64Data = response.data.data;
        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);
        
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: 'image/jpeg' });
      }
      
      return null;
    } catch (error) {
      console.error('Failed to download image:', error);
      return null;
    }
  }

  /**
   * Cache management
   */
  private getCacheKey(filters: ImageSearchFilters): string {
    const key = `${filters.query}_${filters.count || 20}_${filters.orientation || 'all'}_${filters.license || 'all'}`;
    return `${CACHE_CONFIG.CACHE_KEY_PREFIX}${key}`;
  }

  private async getCachedSearch(cacheKey: string): Promise<Image[] | null> {
    // Check memory cache first
    const memoryCache = this.cachedQueries.get(cacheKey);
    if (memoryCache && Date.now() - memoryCache.timestamp < CACHE_CONFIG.TTL) {
      return memoryCache.data;
    }

    // Check storage cache
    const storageCache = await this.storageService.getCacheItem<Image[]>(cacheKey);
    if (storageCache) {
      // Update memory cache
      this.cachedQueries.set(cacheKey, {
        data: storageCache,
        timestamp: Date.now(),
      });
      return storageCache;
    }

    return null;
  }

  private async cacheSearchResults(cacheKey: string, images: Image[]): Promise<void> {
    // Update memory cache
    this.cachedQueries.set(cacheKey, {
      data: images,
      timestamp: Date.now(),
    });

    // Limit memory cache size
    if (this.cachedQueries.size > CACHE_CONFIG.MAX_CACHED_QUERIES) {
      const firstKey = this.cachedQueries.keys().next().value;
      this.cachedQueries.delete(firstKey);
    }

    // Update storage cache
    await this.storageService.setCacheItem(cacheKey, images, CACHE_CONFIG.TTL);
  }

  async clearCache(): Promise<void> {
    this.cachedQueries.clear();
    await this.storageService.clearCache();
  }

  /**
   * Search history management
   */
  private async loadSearchHistory(): Promise<void> {
    const history = await this.storageService.getCacheItem<SearchHistoryItem[]>('image_search_history');
    if (history) {
      this.searchHistory = history;
    }
  }

  private addToSearchHistory(item: SearchHistoryItem): void {
    this.searchHistory.unshift(item);
    
    // Keep only last 100 searches
    if (this.searchHistory.length > 100) {
      this.searchHistory = this.searchHistory.slice(0, 100);
    }

    // Save to storage
    this.storageService.setCacheItem('image_search_history', this.searchHistory);
  }

  getSearchHistory(): SearchHistoryItem[] {
    return [...this.searchHistory];
  }

  getPopularSearches(): string[] {
    const queryCount = new Map<string, number>();
    
    this.searchHistory.forEach(item => {
      const count = queryCount.get(item.query) || 0;
      queryCount.set(item.query, count + 1);
    });

    // Sort by frequency and return top 10
    return Array.from(queryCount.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([query]) => query);
  }

  /**
   * Keyword extraction
   */
  private extractKeywords(content: string): string[] {
    // Remove common words and extract meaningful keywords
    const commonWords = new Set([
      'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
      'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
      'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
      'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
      'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
    ]);

    // Extract words
    const words = content
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 2 && !commonWords.has(word));

    // Get unique keywords
    const uniqueWords = Array.from(new Set(words));

    // Return top 5 keywords
    return uniqueWords.slice(0, 5);
  }

  /**
   * Utility methods
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get image metadata
   */
  async getImageMetadata(imageUrl: string): Promise<{
    width?: number;
    height?: number;
    size?: number;
    format?: string;
  } | null> {
    try {
      const response = await this.post<any>('/images/metadata', { url: imageUrl });
      return response.success ? response.data : null;
    } catch (error) {
      console.error('Failed to get image metadata:', error);
      return null;
    }
  }

  /**
   * Validate image URL
   */
  isValidImageUrl(url: string): boolean {
    try {
      const urlObj = new URL(url);
      const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'];
      return imageExtensions.some(ext => urlObj.pathname.toLowerCase().endsWith(ext));
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const imageService = new ImageService();

export default ImageService;