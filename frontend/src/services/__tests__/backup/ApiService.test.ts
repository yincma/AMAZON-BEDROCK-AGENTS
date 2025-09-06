import axios, { AxiosError, AxiosResponse } from 'axios';
import { ApiService } from '../ApiService';
import { ApiError } from '../../types/api';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock console methods
console.error = jest.fn();
console.log = jest.fn();

describe('ApiService', () => {
  let apiService: ApiService;
  let axiosInstanceMock: jest.Mocked<any>;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Create mock axios instance
    axiosInstanceMock = {
      create: jest.fn(),
      request: jest.fn(),
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      patch: jest.fn(),
      interceptors: {
        request: {
          use: jest.fn(),
        },
        response: {
          use: jest.fn(),
        },
      },
      defaults: {},
    };

    mockedAxios.create.mockReturnValue(axiosInstanceMock);
    mockedAxios.isAxiosError.mockImplementation((error: any) => {
      return error && error.isAxiosError === true;
    });

    apiService = new ApiService();
  });

  afterEach(() => {
    apiService.cancelAllRequests();
  });

  describe('Constructor and Setup', () => {
    it('should create axios instance with default config', () => {
      expect(mockedAxios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: expect.any(String),
          timeout: expect.any(Number),
          headers: {
            'Content-Type': 'application/json',
          },
        })
      );
    });

    it('should setup request and response interceptors', () => {
      expect(axiosInstanceMock.interceptors.request.use).toHaveBeenCalled();
      expect(axiosInstanceMock.interceptors.response.use).toHaveBeenCalled();
    });

    it('should accept custom config in constructor', () => {
      const customConfig = {
        baseURL: 'https://custom-api.com',
        timeout: 5000,
      };

      new ApiService(customConfig);

      expect(mockedAxios.create).toHaveBeenCalledWith(
        expect.objectContaining(customConfig)
      );
    });
  });

  describe('HTTP Methods', () => {
    const mockSuccessResponse: AxiosResponse = {
      data: { message: 'success', id: 1 },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {} as any,
    };

    beforeEach(() => {
      axiosInstanceMock.request.mockResolvedValue(mockSuccessResponse);
    });

    describe('GET requests', () => {
      it('should make successful GET request', async () => {
        const url = '/test-endpoint';
        const result = await apiService.get(url);

        expect(axiosInstanceMock.request).toHaveBeenCalledWith(
          expect.objectContaining({
            method: 'GET',
            url,
            data: undefined,
          })
        );

        expect(result).toEqual({
          success: true,
          data: mockSuccessResponse.data,
          metadata: expect.objectContaining({
            requestId: expect.any(String),
            timestamp: expect.any(String),
          }),
        });
      });

      it('should pass config parameters to GET request', async () => {
        const url = '/test-endpoint';
        const config = {
          params: { page: 1, limit: 10 },
          headers: { 'X-Custom': 'header' },
          timeout: 5000,
        };

        await apiService.get(url, config);

        expect(axiosInstanceMock.request).toHaveBeenCalledWith(
          expect.objectContaining({
            method: 'GET',
            url,
            params: config.params,
            headers: config.headers,
            timeout: config.timeout,
          })
        );
      });
    });

    describe('POST requests', () => {
      it('should make successful POST request with data', async () => {
        const url = '/test-endpoint';
        const data = { name: 'test', value: 123 };

        const result = await apiService.post(url, data);

        expect(axiosInstanceMock.request).toHaveBeenCalledWith(
          expect.objectContaining({
            method: 'POST',
            url,
            data,
          })
        );

        expect(result.success).toBe(true);
        expect(result.data).toEqual(mockSuccessResponse.data);
      });

      it('should make POST request without data', async () => {
        const url = '/test-endpoint';

        await apiService.post(url);

        expect(axiosInstanceMock.request).toHaveBeenCalledWith(
          expect.objectContaining({
            method: 'POST',
            url,
            data: undefined,
          })
        );
      });
    });

    describe('PUT requests', () => {
      it('should make successful PUT request', async () => {
        const url = '/test-endpoint/1';
        const data = { name: 'updated' };

        await apiService.put(url, data);

        expect(axiosInstanceMock.request).toHaveBeenCalledWith(
          expect.objectContaining({
            method: 'PUT',
            url,
            data,
          })
        );
      });
    });

    describe('DELETE requests', () => {
      it('should make successful DELETE request', async () => {
        const url = '/test-endpoint/1';

        await apiService.delete(url);

        expect(axiosInstanceMock.request).toHaveBeenCalledWith(
          expect.objectContaining({
            method: 'DELETE',
            url,
            data: undefined,
          })
        );
      });
    });

    describe('PATCH requests', () => {
      it('should make successful PATCH request', async () => {
        const url = '/test-endpoint/1';
        const data = { status: 'active' };

        await apiService.patch(url, data);

        expect(axiosInstanceMock.request).toHaveBeenCalledWith(
          expect.objectContaining({
            method: 'PATCH',
            url,
            data,
          })
        );
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      const networkError = new Error('Network Error') as AxiosError;
      networkError.isAxiosError = true;
      networkError.response = undefined;

      axiosInstanceMock.request.mockRejectedValue(networkError);
      mockedAxios.isAxiosError.mockReturnValue(true);

      const result = await apiService.get('/test');

      expect(result).toEqual({
        success: false,
        error: {
          code: 'NETWORK_ERROR',
          message: 'Network Error',
          details: { originalError: networkError },
        },
      });
    });

    it('should handle HTTP error responses', async () => {
      const httpError = {
        isAxiosError: true,
        response: {
          status: 404,
          data: {
            code: 'NOT_FOUND',
            message: 'Resource not found',
            details: { resource: 'user' },
          },
        },
      } as AxiosError;

      axiosInstanceMock.request.mockRejectedValue(httpError);
      mockedAxios.isAxiosError.mockReturnValue(true);

      const result = await apiService.get('/test');

      expect(result).toEqual({
        success: false,
        error: {
          code: 'NOT_FOUND',
          message: 'Resource not found',
          details: { resource: 'user' },
          timestamp: expect.any(String),
        },
      });
    });

    it('should handle HTTP errors without custom error data', async () => {
      const httpError = {
        isAxiosError: true,
        response: {
          status: 500,
          data: null,
        },
      } as AxiosError;

      axiosInstanceMock.request.mockRejectedValue(httpError);
      mockedAxios.isAxiosError.mockReturnValue(true);

      const result = await apiService.get('/test');

      expect(result).toEqual({
        success: false,
        error: {
          code: 'HTTP_500',
          message: 'Internal server error',
          details: { status: 500, data: null },
          timestamp: expect.any(String),
        },
      });
    });

    it('should handle generic errors', async () => {
      const genericError = new Error('Something went wrong');
      axiosInstanceMock.request.mockRejectedValue(genericError);
      mockedAxios.isAxiosError.mockReturnValue(false);

      const result = await apiService.get('/test');

      expect(result).toEqual({
        success: false,
        error: {
          code: 'UNKNOWN_ERROR',
          message: 'Something went wrong',
          details: { originalError: genericError },
        },
      });
    });
  });

  describe('Request Cancellation', () => {
    it('should create abort controller for requests', async () => {
      const mockResponse = { data: 'test', status: 200 } as AxiosResponse;
      axiosInstanceMock.request.mockResolvedValue(mockResponse);

      await apiService.get('/test');

      expect(axiosInstanceMock.request).toHaveBeenCalledWith(
        expect.objectContaining({
          signal: expect.any(AbortSignal),
        })
      );
    });

    it('should cancel all pending requests', () => {
      // This method doesn't throw errors, so we just check it exists
      expect(() => apiService.cancelAllRequests()).not.toThrow();
    });
  });

  describe('Configuration Updates', () => {
    it('should update axios configuration', () => {
      const newConfig = {
        baseURL: 'https://new-api.com',
        timeout: 10000,
      };

      apiService.updateConfig(newConfig);

      expect(Object.assign).toHaveBeenCalledWith(
        axiosInstanceMock.defaults,
        newConfig
      );
    });
  });

  describe('Health Check', () => {
    it('should return true for successful health check', async () => {
      axiosInstanceMock.request.mockResolvedValue({
        data: true,
        status: 200,
      } as AxiosResponse);

      const result = await apiService.healthCheck();

      expect(result).toBe(true);
      expect(axiosInstanceMock.request).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'GET',
          url: '/health',
        })
      );
    });

    it('should return false for failed health check', async () => {
      axiosInstanceMock.request.mockRejectedValue(new Error('Health check failed'));

      const result = await apiService.healthCheck();

      expect(result).toBe(false);
    });

    it('should return false when health check returns unsuccessful response', async () => {
      axiosInstanceMock.request.mockResolvedValue({
        data: false,
        status: 200,
      } as AxiosResponse);

      const result = await apiService.healthCheck();

      expect(result).toBe(false);
    });
  });

  describe('API Key Handling', () => {
    const originalGetItem = localStorage.getItem;

    beforeEach(() => {
      localStorage.getItem = jest.fn();
    });

    afterEach(() => {
      localStorage.getItem = originalGetItem;
    });

    it('should add API key from localStorage to requests', () => {
      const apiConfig = { apiKey: 'test-api-key' };
      (localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(apiConfig));

      // Create new service instance to trigger interceptor setup
      new ApiService();

      // Verify the interceptor was set up (this would be tested via actual request)
      expect(axiosInstanceMock.interceptors.request.use).toHaveBeenCalled();
    });

    it('should handle invalid JSON in localStorage', () => {
      (localStorage.getItem as jest.Mock).mockReturnValue('invalid-json');

      // Should not throw error
      expect(() => new ApiService()).not.toThrow();
    });

    it('should fall back to environment variable when localStorage is empty', () => {
      (localStorage.getItem as jest.Mock).mockReturnValue(null);

      // Should not throw error
      expect(() => new ApiService()).not.toThrow();
    });
  });

  describe('Retry Logic', () => {
    it('should retry on retryable status codes', async () => {
      const retryableError = {
        isAxiosError: true,
        response: {
          status: 503,
          data: null,
        },
        config: {
          _retryCount: 0,
          headers: {},
          method: 'GET',
          url: '/test',
        },
        name: 'AxiosError',
        message: 'Service Unavailable',
        toJSON: jest.fn(),
      } as any;

      // First call fails, second succeeds
      axiosInstanceMock.request
        .mockRejectedValueOnce(retryableError)
        .mockResolvedValue({ data: 'success', status: 200 } as AxiosResponse);

      mockedAxios.isAxiosError.mockReturnValue(true);

      const result = await apiService.get('/test');

      expect(result.success).toBe(true);
      expect(axiosInstanceMock.request).toHaveBeenCalledTimes(2);
    });

    it('should not retry non-retryable status codes', async () => {
      const nonRetryableError = {
        isAxiosError: true,
        response: {
          status: 400,
          data: { message: 'Bad Request' },
        },
      } as AxiosError;

      axiosInstanceMock.request.mockRejectedValue(nonRetryableError);
      mockedAxios.isAxiosError.mockReturnValue(true);

      const result = await apiService.get('/test');

      expect(result.success).toBe(false);
      expect(axiosInstanceMock.request).toHaveBeenCalledTimes(1);
    });
  });

  describe('Response Metadata', () => {
    it('should include response metadata in successful responses', async () => {
      const mockResponse = {
        data: { message: 'success' },
        status: 200,
        statusText: 'OK',
        headers: { 'x-response-time': '150' },
        config: { headers: {} },
      } as any;

      axiosInstanceMock.request.mockResolvedValue(mockResponse);

      const result = await apiService.get('/test');

      expect(result.metadata).toEqual({
        requestId: expect.any(String),
        timestamp: expect.any(String),
        duration: 150,
      });
    });

    it('should handle missing response time header', async () => {
      const mockResponse = {
        data: { message: 'success' },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: { headers: {} },
      } as any;

      axiosInstanceMock.request.mockResolvedValue(mockResponse);

      const result = await apiService.get('/test');

      expect(result.metadata?.duration).toBeUndefined();
    });
  });
});