import { ImageService, ImageSearchFilters } from '../ImageService';
import { StorageService } from '../StorageService';
import { Image } from '../../types/models';

// Mock the parent ApiService and StorageService
jest.mock('../ApiService');
jest.mock('../StorageService');

// Mock timers for rate limiting tests
jest.useFakeTimers();

describe('ImageService', () => {
  let imageService: ImageService;
  let mockPost: jest.Mock;
  let mockGet: jest.Mock;
  let mockStorageService: jest.Mocked<StorageService>;

  const mockImage: Image = {
    id: 'img-123',
    url: 'https://example.com/image.jpg',
    thumbnailUrl: 'https://example.com/thumb.jpg',
    alt: 'Test Image',
    caption: 'A test image',
    width: 800,
    height: 600,
    size: 102400,
    source: 'unsplash',
  };

  const mockSearchResponse = {
    success: true,
    data: {
      images: [mockImage],
      totalCount: 1,
      hasMore: false,
    },
  };

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();

    // Create new service instance
    imageService = new ImageService();

    // Setup method mocks
    mockPost = jest.fn();
    mockGet = jest.fn();
    mockStorageService = {
      getCacheItem: jest.fn(),
      setCacheItem: jest.fn(),
      clearCache: jest.fn(),
    } as any;

    (imageService as any).post = mockPost;
    (imageService as any).get = mockGet;
    (imageService as any).storageService = mockStorageService;
  });

  afterEach(() => {
    jest.clearAllTimers();
  });

  describe('Image Search', () => {
    const searchFilters: ImageSearchFilters = {
      query: 'artificial intelligence',
      count: 20,
      safeSearch: true,
      license: 'creative_commons',
      orientation: 'landscape',
    };

    it('should search images successfully', async () => {
      mockStorageService.getCacheItem.mockResolvedValue(null); // No cache
      mockPost.mockResolvedValue(mockSearchResponse);

      const result = await imageService.searchImages(searchFilters);

      expect(mockPost).toHaveBeenCalledWith('/images/search', {
        query: 'artificial intelligence',
        count: 20,
        safeSearch: true,
        license: 'creative_commons',
        orientation: 'landscape',
      });

      expect(result).toEqual({
        success: true,
        data: [mockImage],
      });

      expect(mockStorageService.setCacheItem).toHaveBeenCalled();
    });

    it('should return cached results when available', async () => {
      const cachedImages = [mockImage];
      mockStorageService.getCacheItem.mockResolvedValue(cachedImages);

      const result = await imageService.searchImages(searchFilters);

      expect(mockPost).not.toHaveBeenCalled();
      expect(result).toEqual({
        success: true,
        data: cachedImages,
        metadata: {
          fromCache: true,
          timestamp: expect.any(String),
        },
      });
    });

    it('should use default values for optional parameters', async () => {
      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost.mockResolvedValue(mockSearchResponse);

      const basicFilters: ImageSearchFilters = {
        query: 'test query',
      };

      await imageService.searchImages(basicFilters);

      expect(mockPost).toHaveBeenCalledWith('/images/search', {
        query: 'test query',
        count: 20,
        safeSearch: true,
        license: 'all',
        orientation: undefined,
      });
    });

    it('should handle search API failure', async () => {
      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost.mockResolvedValue({
        success: false,
        error: { code: 'API_ERROR', message: 'Search failed' },
      });

      const result = await imageService.searchImages(searchFilters);

      expect(result).toEqual({
        success: false,
        error: { code: 'API_ERROR', message: 'Search failed' },
      });
    });

    it('should handle search exceptions', async () => {
      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost.mockRejectedValue(new Error('Network error'));

      const result = await imageService.searchImages(searchFilters);

      expect(result).toEqual({
        success: false,
        error: {
          code: 'SEARCH_ERROR',
          message: 'Network error',
        },
      });
    });

    it('should update search history after successful search', async () => {
      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost.mockResolvedValue(mockSearchResponse);

      await imageService.searchImages(searchFilters);

      const history = imageService.getSearchHistory();
      expect(history).toHaveLength(1);
      expect(history[0]).toMatchObject({
        query: 'artificial intelligence',
        resultCount: 1,
        filters: searchFilters,
      });
    });
  });

  describe('Image Suggestions', () => {
    it('should get image suggestions from content', async () => {
      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost.mockResolvedValue(mockSearchResponse);

      const content = 'This presentation is about artificial intelligence and machine learning technology.';
      const result = await imageService.getImageSuggestions(content, 5);

      expect(result).toEqual([mockImage]);
      expect(mockPost).toHaveBeenCalledWith('/images/search', expect.objectContaining({
        count: 5,
        safeSearch: true,
      }));
    });

    it('should return empty array when no keywords found', async () => {
      const content = 'the a an and or but in on at to for';
      const result = await imageService.getImageSuggestions(content);

      expect(result).toEqual([]);
      expect(mockPost).not.toHaveBeenCalled();
    });

    it('should handle suggestion errors gracefully', async () => {
      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost.mockRejectedValue(new Error('Search failed'));

      const result = await imageService.getImageSuggestions('test content');

      expect(result).toEqual([]);
    });

    it('should extract relevant keywords from content', async () => {
      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost.mockResolvedValue(mockSearchResponse);

      const content = 'Learn about machine learning algorithms and neural networks in AI.';
      await imageService.getImageSuggestions(content);

      // Should extract meaningful keywords and filter out common words
      expect(mockPost).toHaveBeenCalledWith('/images/search', expect.objectContaining({
        query: expect.stringContaining('machine'),
      }));
    });
  });

  describe('Batch Search', () => {
    it('should perform batch search with rate limiting', async () => {
      const queries = ['AI', 'machine learning', 'neural networks', 'deep learning', 'algorithms'];
      const responses = queries.map((query, index) => ({
        success: true,
        data: [{ ...mockImage, id: `img-${index}` }],
      }));

      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost.mockImplementation(() => Promise.resolve(responses.shift()));

      const resultPromise = imageService.batchSearchImages(queries);

      // Fast-forward timers to simulate delays between batches
      jest.advanceTimersByTime(500);

      const result = await resultPromise;

      expect(result.size).toBe(5);
      expect(result.get('AI')).toHaveLength(1);
      expect(mockPost).toHaveBeenCalledTimes(5);
    });

    it('should handle batch search failures gracefully', async () => {
      const queries = ['query1', 'query2'];
      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost
        .mockResolvedValueOnce({ success: true, data: [mockImage] })
        .mockResolvedValueOnce({ success: false, error: { message: 'Failed' } });

      const result = await imageService.batchSearchImages(queries);

      expect(result.size).toBe(2);
      expect(result.get('query1')).toEqual([mockImage]);
      expect(result.get('query2')).toEqual([]);
    });

    it('should process queries in batches of 3', async () => {
      const queries = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7'];
      mockStorageService.getCacheItem.mockResolvedValue(null);
      mockPost.mockResolvedValue({ success: true, data: [mockImage] });

      const resultPromise = imageService.batchSearchImages(queries);

      // Advance timers for batch processing delays
      jest.advanceTimersByTime(1000);

      const result = await resultPromise;

      expect(result.size).toBe(7);
      expect(mockPost).toHaveBeenCalledTimes(7);
    });
  });

  describe('Trending Images', () => {
    it('should get trending images without category', async () => {
      const trendingResponse = {
        success: true,
        data: { images: [mockImage] },
      };
      mockGet.mockResolvedValue(trendingResponse);

      const result = await imageService.getTrendingImages();

      expect(mockGet).toHaveBeenCalledWith('/images/trending');
      expect(result).toEqual([mockImage]);
    });

    it('should get trending images with category', async () => {
      const trendingResponse = {
        success: true,
        data: { images: [mockImage] },
      };
      mockGet.mockResolvedValue(trendingResponse);

      const result = await imageService.getTrendingImages('technology');

      expect(mockGet).toHaveBeenCalledWith('/images/trending?category=technology');
      expect(result).toEqual([mockImage]);
    });

    it('should handle trending images API failure', async () => {
      mockGet.mockRejectedValue(new Error('API error'));

      const result = await imageService.getTrendingImages();

      expect(result).toEqual([]);
    });
  });

  describe('Image Download', () => {
    it('should download image successfully', async () => {
      const mockResponse = {
        success: true,
        data: { data: btoa('fake image data') }, // base64 encoded
      };
      mockPost.mockResolvedValue(mockResponse);

      const result = await imageService.downloadImage('https://example.com/image.jpg');

      expect(mockPost).toHaveBeenCalledWith('/images/download', {
        url: 'https://example.com/image.jpg',
      });

      expect(result).toBeInstanceOf(Blob);
      expect(result?.type).toBe('image/jpeg');
    });

    it('should handle download failure', async () => {
      mockPost.mockResolvedValue({ success: false });

      const result = await imageService.downloadImage('https://example.com/image.jpg');

      expect(result).toBeNull();
    });

    it('should handle download exceptions', async () => {
      mockPost.mockRejectedValue(new Error('Download failed'));

      const result = await imageService.downloadImage('https://example.com/image.jpg');

      expect(result).toBeNull();
    });
  });

  describe('Cache Management', () => {
    it('should generate consistent cache keys', () => {
      const filters1: ImageSearchFilters = { query: 'test', count: 20, orientation: 'landscape' };
      const filters2: ImageSearchFilters = { query: 'test', count: 20, orientation: 'landscape' };

      const key1 = (imageService as any).getCacheKey(filters1);
      const key2 = (imageService as any).getCacheKey(filters2);

      expect(key1).toBe(key2);
      expect(key1).toContain('test');
    });

    it('should check memory cache before storage cache', async () => {
      const cachedData = [mockImage];
      const cacheKey = 'test_cache_key';

      // Set up memory cache
      (imageService as any).cachedQueries.set(cacheKey, {
        data: cachedData,
        timestamp: Date.now(),
      });

      const result = await (imageService as any).getCachedSearch(cacheKey);

      expect(result).toEqual(cachedData);
      expect(mockStorageService.getCacheItem).not.toHaveBeenCalled();
    });

    it('should fall back to storage cache when memory cache is expired', async () => {
      const cachedData = [mockImage];
      const cacheKey = 'test_cache_key';

      // Set up expired memory cache
      (imageService as any).cachedQueries.set(cacheKey, {
        data: cachedData,
        timestamp: Date.now() - 3700000, // Expired (older than 1 hour)
      });

      mockStorageService.getCacheItem.mockResolvedValue(cachedData);

      const result = await (imageService as any).getCachedSearch(cacheKey);

      expect(result).toEqual(cachedData);
      expect(mockStorageService.getCacheItem).toHaveBeenCalledWith(cacheKey);
    });

    it('should limit memory cache size', async () => {
      const maxCachedQueries = 50;
      
      // Fill cache to maximum
      for (let i = 0; i <= maxCachedQueries; i++) {
        await (imageService as any).cacheSearchResults(`key_${i}`, [mockImage]);
      }

      const cacheSize = (imageService as any).cachedQueries.size;
      expect(cacheSize).toBeLessThanOrEqual(maxCachedQueries);
    });

    it('should clear all caches', async () => {
      // Add some data to memory cache
      (imageService as any).cachedQueries.set('test', { data: [mockImage], timestamp: Date.now() });

      await imageService.clearCache();

      expect((imageService as any).cachedQueries.size).toBe(0);
      expect(mockStorageService.clearCache).toHaveBeenCalled();
    });
  });

  describe('Search History Management', () => {
    it('should maintain search history', () => {
      const historyItem = {
        query: 'test query',
        timestamp: new Date(),
        resultCount: 5,
        filters: { query: 'test query' },
      };

      (imageService as any).addToSearchHistory(historyItem);

      const history = imageService.getSearchHistory();
      expect(history).toHaveLength(1);
      expect(history[0]).toMatchObject({
        query: 'test query',
        resultCount: 5,
      });
    });

    it('should limit search history to 100 items', () => {
      // Add 101 items to history
      for (let i = 0; i <= 100; i++) {
        (imageService as any).addToSearchHistory({
          query: `query ${i}`,
          timestamp: new Date(),
          resultCount: 1,
        });
      }

      const history = imageService.getSearchHistory();
      expect(history).toHaveLength(100);
      expect(history[0].query).toBe('query 100'); // Most recent first
    });

    it('should get popular searches', () => {
      // Add repeated searches
      const searches = [
        'AI', 'machine learning', 'AI', 'neural networks', 'AI',
        'deep learning', 'machine learning', 'algorithms', 'AI',
      ];

      searches.forEach(query => {
        (imageService as any).addToSearchHistory({
          query,
          timestamp: new Date(),
          resultCount: 5,
        });
      });

      const popular = imageService.getPopularSearches();
      
      expect(popular).toContain('AI'); // Most frequent
      expect(popular).toContain('machine learning');
      expect(popular.length).toBeLessThanOrEqual(10);
    });

    it('should save search history to storage', () => {
      const historyItem = {
        query: 'test query',
        timestamp: new Date(),
        resultCount: 5,
      };

      (imageService as any).addToSearchHistory(historyItem);

      expect(mockStorageService.setCacheItem).toHaveBeenCalledWith(
        'image_search_history',
        expect.any(Array)
      );
    });
  });

  describe('Image Metadata', () => {
    it('should get image metadata', async () => {
      const metadata = {
        width: 800,
        height: 600,
        size: 102400,
        format: 'jpeg',
      };

      mockPost.mockResolvedValue({ success: true, data: metadata });

      const result = await imageService.getImageMetadata('https://example.com/image.jpg');

      expect(mockPost).toHaveBeenCalledWith('/images/metadata', {
        url: 'https://example.com/image.jpg',
      });

      expect(result).toEqual(metadata);
    });

    it('should handle metadata API failure', async () => {
      mockPost.mockResolvedValue({ success: false });

      const result = await imageService.getImageMetadata('https://example.com/image.jpg');

      expect(result).toBeNull();
    });

    it('should handle metadata exceptions', async () => {
      mockPost.mockRejectedValue(new Error('Metadata error'));

      const result = await imageService.getImageMetadata('https://example.com/image.jpg');

      expect(result).toBeNull();
    });
  });

  describe('URL Validation', () => {
    it('should validate valid image URLs', () => {
      const validUrls = [
        'https://example.com/image.jpg',
        'https://example.com/photo.jpeg',
        'https://example.com/graphic.png',
        'https://example.com/animation.gif',
        'https://example.com/vector.svg',
        'https://example.com/picture.webp',
        'https://example.com/bitmap.bmp',
      ];

      validUrls.forEach(url => {
        expect(imageService.isValidImageUrl(url)).toBe(true);
      });
    });

    it('should reject invalid image URLs', () => {
      const invalidUrls = [
        'https://example.com/document.pdf',
        'https://example.com/video.mp4',
        'https://example.com/audio.mp3',
        'https://example.com/text.txt',
        'not-a-url',
        '',
      ];

      invalidUrls.forEach(url => {
        expect(imageService.isValidImageUrl(url)).toBe(false);
      });
    });

    it('should handle malformed URLs', () => {
      expect(imageService.isValidImageUrl('://invalid-url')).toBe(false);
      expect(imageService.isValidImageUrl('ftp://example.com/image.jpg')).toBe(true);
    });
  });

  describe('Keyword Extraction', () => {
    it('should extract meaningful keywords from content', () => {
      const content = 'This presentation covers artificial intelligence, machine learning, and neural networks in modern technology applications.';
      
      const keywords = (imageService as any).extractKeywords(content);

      expect(keywords).toContain('artificial');
      expect(keywords).toContain('intelligence');
      expect(keywords).toContain('machine');
      expect(keywords).toContain('learning');
      expect(keywords).not.toContain('the');
      expect(keywords).not.toContain('and');
      expect(keywords.length).toBeLessThanOrEqual(5);
    });

    it('should filter out common words', () => {
      const content = 'The quick brown fox jumps over the lazy dog.';
      
      const keywords = (imageService as any).extractKeywords(content);

      expect(keywords).not.toContain('the');
      expect(keywords).not.toContain('over');
      expect(keywords).toContain('quick');
      expect(keywords).toContain('brown');
    });

    it('should handle empty or short content', () => {
      expect((imageService as any).extractKeywords('')).toEqual([]);
      expect((imageService as any).extractKeywords('a')).toEqual([]);
      expect((imageService as any).extractKeywords('the quick')).toEqual(['quick']);
    });

    it('should handle content with punctuation and special characters', () => {
      const content = 'AI/ML technologies, neural-networks & deep-learning algorithms!';
      
      const keywords = (imageService as any).extractKeywords(content);

      expect(keywords).toContain('technologies');
      expect(keywords).toContain('neural');
      expect(keywords).toContain('networks');
      expect(keywords).toContain('algorithms');
    });
  });

  describe('Error Handling', () => {
    it('should handle storage errors gracefully', async () => {
      mockStorageService.getCacheItem.mockRejectedValue(new Error('Storage error'));
      mockPost.mockResolvedValue(mockSearchResponse);

      const result = await imageService.searchImages({ query: 'test' });

      // Should still work despite cache error
      expect(result.success).toBe(true);
      expect(mockPost).toHaveBeenCalled();
    });

    it('should handle search history errors gracefully', () => {
      mockStorageService.setCacheItem.mockImplementation(() => {
        throw new Error('Storage error');
      });

      // Should not throw
      expect(() => {
        (imageService as any).addToSearchHistory({
          query: 'test',
          timestamp: new Date(),
          resultCount: 1,
        });
      }).not.toThrow();
    });
  });
});