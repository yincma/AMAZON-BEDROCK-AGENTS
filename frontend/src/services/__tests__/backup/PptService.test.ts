import { PptService, PptServiceEvent } from '../PptService';
import { ApiResponse } from '../../types/api';
import { OutlineNode } from '../../types/models';

// Mock the parent ApiService
jest.mock('../ApiService');

// Mock timers
jest.useFakeTimers();

describe('PptService', () => {
  let pptService: PptService;
  let mockPost: jest.Mock;
  let mockGet: jest.Mock;
  let mockDelete: jest.Mock;

  const mockSessionResponse = {
    success: true,
    data: {
      sessionId: 'test-session-id',
      createdAt: '2023-01-01T00:00:00Z',
    },
  };

  const mockOutlineResponse = {
    success: true,
    data: {
      outline: [
        {
          id: '1',
          title: 'Introduction',
          content: 'Welcome to the presentation',
          level: 1,
          order: 0,
          children: [],
        },
      ] as OutlineNode[],
    },
  };

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Create new service instance
    pptService = new PptService();

    // Setup method mocks
    mockPost = jest.fn();
    mockGet = jest.fn();
    mockDelete = jest.fn();

    (pptService as any).post = mockPost;
    (pptService as any).get = mockGet;
    (pptService as any).delete = mockDelete;
  });

  afterEach(() => {
    pptService.dispose();
    jest.clearAllTimers();
  });

  describe('Session Management', () => {
    it('should create a new session successfully', async () => {
      mockPost.mockResolvedValue(mockSessionResponse);

      const result = await pptService.createSession('project-123');

      expect(mockPost).toHaveBeenCalledWith('/sessions', {
        projectId: 'project-123',
        metadata: {
          clientVersion: '1.0.0',
          timestamp: expect.any(String),
        },
      });

      expect(result).toEqual(mockSessionResponse);
      expect(pptService.getCurrentSessionId()).toBe('test-session-id');
    });

    it('should create session without projectId', async () => {
      mockPost.mockResolvedValue(mockSessionResponse);

      await pptService.createSession();

      expect(mockPost).toHaveBeenCalledWith('/sessions', {
        projectId: undefined,
        metadata: {
          clientVersion: '1.0.0',
          timestamp: expect.any(String),
        },
      });
    });

    it('should emit session created event', async () => {
      const eventListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.SESSION_CREATED, eventListener);

      mockPost.mockResolvedValue(mockSessionResponse);

      await pptService.createSession();

      expect(eventListener).toHaveBeenCalledWith({
        type: PptServiceEvent.SESSION_CREATED,
        data: mockSessionResponse.data,
      });
    });

    it('should emit error event when session creation fails', async () => {
      const errorListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.ERROR, errorListener);

      const error = new Error('Session creation failed');
      mockPost.mockRejectedValue(error);

      await expect(pptService.createSession()).rejects.toThrow(error);

      expect(errorListener).toHaveBeenCalledWith({
        type: PptServiceEvent.ERROR,
        error,
        message: 'Failed to create session',
      });
    });

    it('should get existing session', async () => {
      const sessionData = { sessionId: 'test-session', status: 'active' };
      mockGet.mockResolvedValue({ success: true, data: sessionData });

      const result = await pptService.getSession('test-session');

      expect(mockGet).toHaveBeenCalledWith('/sessions/test-session');
      expect(result.data).toEqual(sessionData);
    });

    it('should set and get current session ID', () => {
      expect(pptService.getCurrentSessionId()).toBeNull();

      pptService.setCurrentSessionId('new-session-id');
      expect(pptService.getCurrentSessionId()).toBe('new-session-id');
    });
  });

  describe('Event Management', () => {
    it('should add and remove event listeners', () => {
      const listener1 = jest.fn();
      const listener2 = jest.fn();

      pptService.addEventListener(PptServiceEvent.OUTLINE_STARTED, listener1);
      pptService.addEventListener(PptServiceEvent.OUTLINE_STARTED, listener2);

      // Emit event to test listeners are added
      (pptService as any).emitEvent(PptServiceEvent.OUTLINE_STARTED, { message: 'test' });

      expect(listener1).toHaveBeenCalledWith({
        type: PptServiceEvent.OUTLINE_STARTED,
        message: 'test',
      });
      expect(listener2).toHaveBeenCalledWith({
        type: PptServiceEvent.OUTLINE_STARTED,
        message: 'test',
      });

      // Remove one listener
      pptService.removeEventListener(PptServiceEvent.OUTLINE_STARTED, listener1);

      // Reset mock calls
      listener1.mockClear();
      listener2.mockClear();

      // Emit event again
      (pptService as any).emitEvent(PptServiceEvent.OUTLINE_STARTED, { message: 'test2' });

      expect(listener1).not.toHaveBeenCalled();
      expect(listener2).toHaveBeenCalledWith({
        type: PptServiceEvent.OUTLINE_STARTED,
        message: 'test2',
      });
    });
  });

  describe('Outline Operations', () => {
    beforeEach(() => {
      pptService.setCurrentSessionId('test-session-id');
    });

    it('should create outline successfully', async () => {
      const outlineListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.OUTLINE_STARTED, outlineListener);
      pptService.addEventListener(PptServiceEvent.OUTLINE_COMPLETED, outlineListener);

      mockPost.mockResolvedValue(mockOutlineResponse);

      const result = await pptService.createOutline('AI Technology', 10, {
        language: 'en',
        tone: 'professional',
        targetAudience: 'developers',
      });

      expect(mockPost).toHaveBeenCalledWith('/outlines/create', {
        sessionId: 'test-session-id',
        topic: 'AI Technology',
        slidesCount: 10,
        language: 'en',
        tone: 'professional',
        targetAudience: 'developers',
      });

      expect(result).toEqual(mockOutlineResponse);
      expect(outlineListener).toHaveBeenCalledTimes(2); // Started and completed events
    });

    it('should create session if none exists when creating outline', async () => {
      pptService.setCurrentSessionId(null);

      mockPost
        .mockResolvedValueOnce(mockSessionResponse) // createSession call
        .mockResolvedValueOnce(mockOutlineResponse); // createOutline call

      await pptService.createOutline('Test Topic', 5);

      expect(mockPost).toHaveBeenCalledTimes(2);
      expect(mockPost).toHaveBeenNthCalledWith(1, '/sessions', expect.any(Object));
      expect(mockPost).toHaveBeenNthCalledWith(2, '/outlines/create', expect.any(Object));
    });

    it('should handle outline creation failure', async () => {
      const errorListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.ERROR, errorListener);

      const failureResponse = {
        success: false,
        error: { message: 'Outline creation failed' },
      };
      mockPost.mockResolvedValue(failureResponse);

      const result = await pptService.createOutline('Test Topic', 5);

      expect(result).toEqual(failureResponse);
      expect(errorListener).toHaveBeenCalledWith({
        type: PptServiceEvent.ERROR,
        error: expect.any(Error),
      });
    });

    it('should update outline', async () => {
      const outline: OutlineNode[] = [
        {
          id: '1',
          title: 'Updated Introduction',
          content: 'Updated content',
          level: 1,
          order: 0,
          children: [],
        },
      ];

      const mockResponse = { success: true, data: { updated: true } };
      const mockPut = jest.fn().mockResolvedValue(mockResponse);
      (pptService as any).put = mockPut;

      const result = await pptService.updateOutline(outline);

      expect(mockPut).toHaveBeenCalledWith('/outlines/update', {
        sessionId: 'test-session-id',
        outline,
      });

      expect(result).toEqual(mockResponse);
    });

    it('should throw error when updating outline without session', async () => {
      pptService.setCurrentSessionId(null);

      const outline: OutlineNode[] = [];

      await expect(pptService.updateOutline(outline)).rejects.toThrow('No active session');
    });
  });

  describe('Content Enhancement', () => {
    beforeEach(() => {
      pptService.setCurrentSessionId('test-session-id');
    });

    it('should enhance single content item', async () => {
      const mockResponse = {
        success: true,
        data: { enhancedContent: 'Enhanced test content' },
      };
      mockPost.mockResolvedValue(mockResponse);

      const result = await pptService.enhanceContent(
        'Test content',
        'paragraph',
        {
          context: 'presentation context',
          maxLength: 100,
          tone: 'professional',
        }
      );

      expect(mockPost).toHaveBeenCalledWith('/content/enhance', {
        sessionId: 'test-session-id',
        content: 'Test content',
        type: 'paragraph',
        context: 'presentation context',
        maxLength: 100,
        tone: 'professional',
      });

      expect(result).toEqual(mockResponse);
    });

    it('should enhance content in batch', async () => {
      const enhancementListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.CONTENT_ENHANCEMENT_STARTED, enhancementListener);
      pptService.addEventListener(PptServiceEvent.CONTENT_ENHANCEMENT_PROGRESS, enhancementListener);
      pptService.addEventListener(PptServiceEvent.CONTENT_ENHANCEMENT_COMPLETED, enhancementListener);

      const items = [
        { id: '1', content: 'Content 1', type: 'title' },
        { id: '2', content: 'Content 2', type: 'paragraph' },
      ];

      const mockResponse = {
        success: true,
        data: { enhancedItems: items },
      };
      mockPost.mockResolvedValue(mockResponse);

      const result = await pptService.batchEnhanceContent(items);

      // Fast-forward timers to trigger progress updates
      jest.advanceTimersByTime(1000);

      expect(mockPost).toHaveBeenCalledWith('/content/enhance-batch', {
        sessionId: 'test-session-id',
        items,
      });

      expect(result).toEqual(mockResponse);
      expect(enhancementListener).toHaveBeenCalledWith(
        expect.objectContaining({
          type: PptServiceEvent.CONTENT_ENHANCEMENT_STARTED,
        })
      );
    });

    it('should handle batch enhancement failure', async () => {
      const errorListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.ERROR, errorListener);

      const items = [{ id: '1', content: 'Content 1', type: 'title' }];
      const error = new Error('Batch enhancement failed');
      mockPost.mockRejectedValue(error);

      await expect(pptService.batchEnhanceContent(items)).rejects.toThrow(error);

      expect(errorListener).toHaveBeenCalledWith({
        type: PptServiceEvent.ERROR,
        error,
        message: 'Failed to enhance content',
      });
    });

    it('should throw error when enhancing content without session', async () => {
      pptService.setCurrentSessionId(null);

      await expect(
        pptService.enhanceContent('test', 'paragraph')
      ).rejects.toThrow('No active session');
    });
  });

  describe('PPT Generation', () => {
    beforeEach(() => {
      pptService.setCurrentSessionId('test-session-id');
    });

    it('should generate PPT successfully', async () => {
      const generationListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.PPT_GENERATION_STARTED, generationListener);
      pptService.addEventListener(PptServiceEvent.PPT_GENERATION_COMPLETED, generationListener);

      const outline: OutlineNode[] = [
        { id: '1', title: 'Slide 1', content: 'Content 1', level: 1, order: 0, children: [] },
      ];

      const mockResponse = {
        success: true,
        data: { downloadUrl: 'https://example.com/download', fileId: 'file-123' },
      };
      mockPost.mockResolvedValue(mockResponse);

      const result = await pptService.generatePpt('project-123', outline, {
        theme: 'modern',
        includeImages: true,
        format: 'pptx',
      });

      expect(mockPost).toHaveBeenCalledWith('/ppt/generate', {
        sessionId: 'test-session-id',
        projectId: 'project-123',
        outline,
        theme: 'modern',
        includeImages: true,
        format: 'pptx',
      });

      expect(result).toEqual(mockResponse);
      expect(generationListener).toHaveBeenCalledTimes(2); // Started and completed events
    });

    it('should handle PPT generation failure', async () => {
      const errorListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.ERROR, errorListener);

      const outline: OutlineNode[] = [];
      const error = new Error('PPT generation failed');
      mockPost.mockRejectedValue(error);

      await expect(pptService.generatePpt('project-123', outline)).rejects.toThrow(error);

      expect(errorListener).toHaveBeenCalledWith({
        type: PptServiceEvent.ERROR,
        error,
        message: 'Failed to generate PPT',
      });
    });

    it('should get generation progress', async () => {
      const progressData = {
        status: 'in_progress',
        progress: 50,
        currentStep: 'Generating slides',
        estimatedTimeRemaining: 120,
      };

      mockGet.mockResolvedValue({ success: true, data: progressData });

      const result = await pptService.getGenerationProgress();

      expect(mockGet).toHaveBeenCalledWith('/ppt/progress/test-session-id');
      expect(result.data).toEqual(progressData);
    });

    it('should cancel generation', async () => {
      const generationListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.PPT_GENERATION_COMPLETED, generationListener);

      mockDelete.mockResolvedValue({ success: true });

      await pptService.cancelGeneration();

      expect(mockDelete).toHaveBeenCalledWith('/ppt/cancel/test-session-id');
      expect(generationListener).toHaveBeenCalledWith({
        type: PptServiceEvent.PPT_GENERATION_COMPLETED,
        message: 'Generation cancelled',
        data: { cancelled: true },
      });
    });

    it('should throw error when generating PPT without session', async () => {
      pptService.setCurrentSessionId(null);

      await expect(
        pptService.generatePpt('project-123', [])
      ).rejects.toThrow('No active session');
    });
  });

  describe('Progress Polling', () => {
    beforeEach(() => {
      pptService.setCurrentSessionId('test-session-id');
    });

    it('should poll progress during PPT generation', async () => {
      const progressListener = jest.fn();
      pptService.addEventListener(PptServiceEvent.PPT_GENERATION_PROGRESS, progressListener);

      // Mock progress responses
      const progressResponses = [
        {
          success: true,
          data: {
            status: 'in_progress',
            progress: 30,
            currentStep: 'Creating slides',
            estimatedTimeRemaining: 60,
          },
        },
        {
          success: true,
          data: {
            status: 'completed',
            progress: 100,
            currentStep: 'Generation complete',
            estimatedTimeRemaining: 0,
          },
        },
      ];

      mockGet
        .mockResolvedValueOnce(progressResponses[0])
        .mockResolvedValueOnce(progressResponses[1]);

      mockPost.mockResolvedValue({
        success: true,
        data: { downloadUrl: 'test-url' },
      });

      // Start generation (this will start progress polling)
      const generationPromise = pptService.generatePpt('project-123', []);

      // Fast-forward to trigger progress polling
      jest.advanceTimersByTime(2000);
      await Promise.resolve(); // Let promises resolve

      jest.advanceTimersByTime(2000);
      await Promise.resolve(); // Let promises resolve

      await generationPromise;

      expect(mockGet).toHaveBeenCalledWith('/ppt/progress/test-session-id');
      expect(progressListener).toHaveBeenCalledWith(
        expect.objectContaining({
          type: PptServiceEvent.PPT_GENERATION_PROGRESS,
          progress: 30,
          message: 'Creating slides',
        })
      );
    });
  });

  describe('Download Operations', () => {
    it('should download PPT successfully', async () => {
      const mockBlob = new Blob(['fake ppt data'], { type: 'application/octet-stream' });
      
      // Mock fetch
      const mockResponse = {
        ok: true,
        blob: jest.fn().mockResolvedValue(mockBlob),
      };
      global.fetch = jest.fn().mockResolvedValue(mockResponse);

      const result = await pptService.downloadPpt('https://example.com/download');

      expect(fetch).toHaveBeenCalledWith('https://example.com/download');
      expect(result).toBe(mockBlob);
    });

    it('should handle download failure', async () => {
      const mockResponse = {
        ok: false,
        statusText: 'Not Found',
      };
      global.fetch = jest.fn().mockResolvedValue(mockResponse);

      await expect(
        pptService.downloadPpt('https://example.com/download')
      ).rejects.toThrow('Failed to download PPT: Not Found');
    });
  });

  describe('Cleanup', () => {
    it('should dispose resources properly', () => {
      const listener = jest.fn();
      pptService.addEventListener(PptServiceEvent.OUTLINE_STARTED, listener);
      pptService.setCurrentSessionId('test-session');

      // Mock cancelAllRequests method
      const mockCancelAllRequests = jest.fn();
      (pptService as any).cancelAllRequests = mockCancelAllRequests;

      pptService.dispose();

      expect(pptService.getCurrentSessionId()).toBeNull();
      expect(mockCancelAllRequests).toHaveBeenCalled();

      // Event listeners should be cleared
      (pptService as any).emitEvent(PptServiceEvent.OUTLINE_STARTED);
      expect(listener).not.toHaveBeenCalled();
    });
  });
});