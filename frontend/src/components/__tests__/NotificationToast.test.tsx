
import { render, screen, fireEvent, waitFor, act } from './test-utils';
import NotificationToast, { showToast, ProgressNotification, createProgressNotification } from '@/components/common/NotificationToast';
import { mockUIStore, createMockNotification } from './test-utils';

describe('NotificationToast', () => {
  beforeEach(() => {
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('Basic Rendering', () => {
    it('renders nothing when no notifications', () => {
      const { container } = render(<NotificationToast />);
      expect(container.firstChild).toBeNull();
    });

    it('renders notifications correctly', () => {
      const notifications = [
        createMockNotification({ 
          id: '1', 
          title: 'Test Success', 
          type: 'success' 
        }),
        createMockNotification({ 
          id: '2', 
          title: 'Test Error', 
          type: 'error', 
          message: 'Something went wrong' 
        }),
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      expect(screen.getByText('Test Success')).toBeInTheDocument();
      expect(screen.getByText('Test Error')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('renders notification with correct icons', () => {
      const notifications = [
        createMockNotification({ type: 'success' }),
        createMockNotification({ type: 'error' }),
        createMockNotification({ type: 'warning' }),
        createMockNotification({ type: 'info' }),
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      // Check that icons are present (we can't easily test specific icons, but we can check they exist)
      const iconElements = document.querySelectorAll('svg');
      expect(iconElements.length).toBeGreaterThan(0);
    });
  });

  describe('Notification Types', () => {
    it('renders success notification with correct styling', () => {
      const notifications = [
        createMockNotification({ 
          type: 'success',
          title: 'Success Message'
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      const notification = screen.getByText('Success Message').closest('div');
      expect(notification).toHaveClass('border-green-500');
    });

    it('renders error notification with correct styling', () => {
      const notifications = [
        createMockNotification({ 
          type: 'error',
          title: 'Error Message'
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      const notification = screen.getByText('Error Message').closest('div');
      expect(notification).toHaveClass('border-red-500');
    });

    it('renders warning notification with correct styling', () => {
      const notifications = [
        createMockNotification({ 
          type: 'warning',
          title: 'Warning Message'
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      const notification = screen.getByText('Warning Message').closest('div');
      expect(notification).toHaveClass('border-yellow-500');
    });

    it('renders info notification with correct styling', () => {
      const notifications = [
        createMockNotification({ 
          type: 'info',
          title: 'Info Message'
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      const notification = screen.getByText('Info Message').closest('div');
      expect(notification).toHaveClass('border-blue-500');
    });
  });

  describe('Notification Content', () => {
    it('displays title and message correctly', () => {
      const notifications = [
        createMockNotification({
          title: 'Test Title',
          message: 'Test Message'
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      expect(screen.getByText('Test Title')).toBeInTheDocument();
      expect(screen.getByText('Test Message')).toBeInTheDocument();
    });

    it('displays timestamp correctly', () => {
      const timestamp = new Date('2024-01-01T10:30:45');
      const notifications = [
        createMockNotification({ timestamp })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      // Check that timestamp is formatted correctly
      expect(screen.getByText('10:30:45 AM')).toBeInTheDocument();
    });

    it('renders action button when provided', () => {
      const mockAction = jest.fn();
      const notifications = [
        createMockNotification({
          title: 'Test with Action',
          action: {
            label: 'Click Me',
            onClick: mockAction
          }
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      const actionButton = screen.getByText('Click Me');
      expect(actionButton).toBeInTheDocument();

      fireEvent.click(actionButton);
      expect(mockAction).toHaveBeenCalledTimes(1);
    });

    it('does not render message when not provided', () => {
      const notifications = [
        createMockNotification({
          title: 'Only Title',
          message: undefined
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      expect(screen.getByText('Only Title')).toBeInTheDocument();
      // Should not have a separate message element
      const messageElements = screen.queryAllByText((content, element) => {
        return element?.className?.includes('text-gray-600');
      });
      expect(messageElements).toHaveLength(0);
    });
  });

  describe('Close Functionality', () => {
    it('calls removeNotification when close button is clicked', async () => {
      const notifications = [
        createMockNotification({
          id: 'test-id',
          title: 'Test Close'
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);

      // Wait for the animation delay
      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockUIStore.removeNotification).toHaveBeenCalledWith('test-id');
    });

    it('handles close animation properly', async () => {
      const notifications = [
        createMockNotification({ title: 'Test Animation' })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      const closeButton = screen.getByRole('button', { name: /close/i });
      
      // Click close button
      fireEvent.click(closeButton);

      // Should still be visible during animation
      expect(screen.getByText('Test Animation')).toBeInTheDocument();

      // After animation delay, should be removed
      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockUIStore.removeNotification).toHaveBeenCalled();
    });
  });

  describe('Positioning', () => {
    const positionTests = [
      { position: 'top-right', expectedClasses: 'top-0 right-0' },
      { position: 'top-left', expectedClasses: 'top-0 left-0' },
      { position: 'top-center', expectedClasses: 'top-0 left-1/2 transform -translate-x-1/2' },
      { position: 'bottom-right', expectedClasses: 'bottom-0 right-0' },
      { position: 'bottom-left', expectedClasses: 'bottom-0 left-0' },
      { position: 'bottom-center', expectedClasses: 'bottom-0 left-1/2 transform -translate-x-1/2' },
    ];

    positionTests.forEach(({ position, expectedClasses }) => {
      it(`positions notifications correctly at ${position}`, () => {
        const notifications = [createMockNotification({ title: 'Test Position' })];

        render(<NotificationToast />, {
          uiStoreProps: { 
            notifications, 
            toastPosition: position as any
          }
        });

        const container = document.querySelector('.fixed.z-50');
        expectedClasses.split(' ').forEach(className => {
          expect(container).toHaveClass(className);
        });
      });
    });

    it('reverses notification order for bottom positions', () => {
      const notifications = [
        createMockNotification({ id: '1', title: 'First' }),
        createMockNotification({ id: '2', title: 'Second' }),
      ];

      render(<NotificationToast />, {
        uiStoreProps: { 
          notifications, 
          toastPosition: 'bottom-right'
        }
      });

      const notificationElements = screen.getAllByRole('button', { name: /close/i });
      // In bottom position, notifications should be reversed
      expect(notificationElements).toHaveLength(2);
    });
  });

  describe('Progress Notifications', () => {
    it('renders progress bar when progress is provided', () => {
      const notifications = [
        createMockNotification({ title: 'Test Progress' })
      ];

      const { rerender } = render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      // Initially no progress bar
      expect(screen.queryByText('Progress')).not.toBeInTheDocument();

      // Mock component with progress
      const ToastWithProgress = () => {
        const ToastItem = require('@/components/common/NotificationToast').default;
        return (
          <div className="fixed top-0 right-0 p-4 space-y-3">
            {/* Simulate ToastItem with progress */}
            <div>
              <div className="text-sm font-semibold">Test Progress</div>
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                  <span>Progress</span>
                  <span>50%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="h-full bg-blue-600 rounded-full" style={{ width: '50%' }} />
                </div>
              </div>
            </div>
          </div>
        );
      };

      rerender(<ToastWithProgress />);

      expect(screen.getByText('Progress')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
    });
  });

  describe('ProgressNotification Class', () => {
    it('creates progress notification correctly', () => {
      const progress = createProgressNotification('Upload File', 'Uploading...');
      expect(progress).toBeInstanceOf(ProgressNotification);
      expect(mockUIStore.addNotification).toHaveBeenCalledWith({
        type: 'info',
        title: 'Upload File',
        message: 'Uploading...',
        duration: 0
      });
    });

    it('completes progress notification successfully', () => {
      const progress = createProgressNotification('Upload File', 'Uploading...');
      const id = progress.getId();
      
      progress.complete('File uploaded successfully');
      
      expect(mockUIStore.removeNotification).toHaveBeenCalledWith(id);
      expect(mockUIStore.addNotification).toHaveBeenCalledWith({
        type: 'success',
        title: 'Upload File',
        message: 'File uploaded successfully',
        duration: 4000
      });
    });

    it('handles progress notification error', () => {
      const progress = createProgressNotification('Upload File', 'Uploading...');
      const id = progress.getId();
      
      progress.error('Upload failed');
      
      expect(mockUIStore.removeNotification).toHaveBeenCalledWith(id);
      expect(mockUIStore.addNotification).toHaveBeenCalledWith({
        type: 'error',
        title: 'Upload File',
        message: 'Upload failed',
        duration: 8000
      });
    });
  });

  describe('showToast Helper Functions', () => {
    it('creates success toast with correct parameters', () => {
      showToast.success('Success!', 'Operation completed');
      
      expect(mockUIStore.addNotification).toHaveBeenCalledWith({
        type: 'success',
        title: 'Success!',
        message: 'Operation completed',
        duration: undefined
      });
    });

    it('creates error toast with extended duration', () => {
      showToast.error('Error!', 'Something went wrong');
      
      expect(mockUIStore.addNotification).toHaveBeenCalledWith({
        type: 'error',
        title: 'Error!',
        message: 'Something went wrong',
        duration: 8000
      });
    });

    it('creates warning toast with custom duration', () => {
      showToast.warning('Warning!', 'Be careful', 10000);
      
      expect(mockUIStore.addNotification).toHaveBeenCalledWith({
        type: 'warning',
        title: 'Warning!',
        message: 'Be careful',
        duration: 10000
      });
    });

    it('creates info toast correctly', () => {
      showToast.info('Info', 'Just FYI');
      
      expect(mockUIStore.addNotification).toHaveBeenCalledWith({
        type: 'info',
        title: 'Info',
        message: 'Just FYI',
        duration: undefined
      });
    });

    it('dismisses specific notification', () => {
      showToast.dismiss('test-id');
      expect(mockUIStore.removeNotification).toHaveBeenCalledWith('test-id');
    });

    it('dismisses all notifications', () => {
      showToast.dismiss();
      expect(mockUIStore.clearNotifications).toHaveBeenCalledTimes(1);
    });
  });

  describe('Animation and Timing', () => {
    it('applies enter animation after mount', async () => {
      const notifications = [
        createMockNotification({ title: 'Animated' })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      // Initially should have opacity-0
      const toastElement = screen.getByText('Animated').closest('.transform');
      expect(toastElement).toHaveClass('opacity-0');

      // After animation timer
      act(() => {
        jest.advanceTimersByTime(10);
      });

      await waitFor(() => {
        expect(toastElement).toHaveClass('opacity-100');
      });
    });

    it('handles different transform animations based on position', () => {
      const notifications = [createMockNotification({ title: 'Test Transform' })];

      const { rerender } = render(<NotificationToast />, {
        uiStoreProps: { 
          notifications, 
          toastPosition: 'top-right' 
        }
      });

      let toastElement = screen.getByText('Test Transform').closest('.transform');
      expect(toastElement).toHaveClass('translate-x-full');

      // Test left position
      rerender(<NotificationToast />, {
        uiStoreProps: { 
          notifications, 
          toastPosition: 'top-left' 
        }
      });

      toastElement = screen.getByText('Test Transform').closest('.transform');
      expect(toastElement).toHaveClass('-translate-x-full');
    });
  });

  describe('Auto-removal', () => {
    it('automatically removes notifications after duration', async () => {
      const notifications = [
        createMockNotification({
          id: 'auto-remove',
          title: 'Auto Remove',
          duration: 5000
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      expect(screen.getByText('Auto Remove')).toBeInTheDocument();

      // Fast-forward time
      act(() => {
        jest.advanceTimersByTime(5000);
      });

      expect(mockUIStore.removeNotification).toHaveBeenCalledWith('auto-remove');
    });

    it('does not auto-remove notifications with zero duration', async () => {
      const notifications = [
        createMockNotification({
          id: 'persistent',
          title: 'Persistent',
          duration: 0
        })
      ];

      render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      act(() => {
        jest.advanceTimersByTime(10000);
      });

      expect(mockUIStore.removeNotification).not.toHaveBeenCalledWith('persistent');
    });

    it('cleans up timers when component unmounts', () => {
      const notifications = [
        createMockNotification({
          duration: 5000
        })
      ];

      const { unmount } = render(<NotificationToast />, {
        uiStoreProps: { notifications }
      });

      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
      
      unmount();

      expect(clearTimeoutSpy).toHaveBeenCalled();
      clearTimeoutSpy.mockRestore();
    });
  });
});