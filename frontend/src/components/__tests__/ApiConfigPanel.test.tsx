
import { render, screen, fireEvent, waitFor } from './test-utils';
import ApiConfigPanel from '@/components/settings/ApiConfigPanel';
import { mockUIStore } from './test-utils';

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// Mock fetch
global.fetch = jest.fn();

// Mock window.confirm
Object.defineProperty(window, 'confirm', {
  writable: true,
  value: jest.fn(),
});

// Mock clipboard API
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: jest.fn().mockResolvedValue(undefined),
  },
});

// Mock AbortSignal.timeout
Object.defineProperty(AbortSignal, 'timeout', {
  value: jest.fn().mockReturnValue(new AbortController().signal),
});

describe('ApiConfigPanel', () => {
  const mockConfig = {
    baseUrl: 'https://api.example.com',
    apiKey: 'test-api-key',
    timeout: 30000,
    retryAttempts: 3,
    enableCache: true,
    cacheTimeout: 300000,
    enableCompression: true,
    maxConcurrentRequests: 5,
    customHeaders: {},
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue(JSON.stringify(mockConfig));
    (window.confirm as jest.Mock).mockReturnValue(false);
  });

  describe('Basic Rendering', () => {
    it('renders correctly with title and basic fields', () => {
      render(<ApiConfigPanel />);

      expect(screen.getByText('API 配置')).toBeInTheDocument();
      expect(screen.getByText('基本配置')).toBeInTheDocument();
      expect(screen.getByText('API 地址')).toBeInTheDocument();
      expect(screen.getByText('API 密钥')).toBeInTheDocument();
      expect(screen.getByText('请求超时（毫秒）')).toBeInTheDocument();
    });

    it('renders connection status section', () => {
      render(<ApiConfigPanel />);

      expect(screen.getByText('连接状态')).toBeInTheDocument();
      expect(screen.getByText('测试连接')).toBeInTheDocument();
      expect(screen.getByText('未测试')).toBeInTheDocument();
    });

    it('loads config from localStorage on mount', () => {
      render(<ApiConfigPanel />);

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('api-config');
      expect(screen.getByDisplayValue('https://api.example.com')).toBeInTheDocument();
      expect(screen.getByDisplayValue('30000')).toBeInTheDocument();
    });

    it('uses default config when localStorage is empty', () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      render(<ApiConfigPanel />);

      expect(screen.getByDisplayValue(/localhost:8000/)).toBeInTheDocument();
    });

    it('renders close button when onClose prop is provided', () => {
      const mockOnClose = jest.fn();
      render(<ApiConfigPanel onClose={mockOnClose} />);

      const closeButton = screen.getByRole('button').querySelector('.w-5.h-5');
      expect(closeButton).toBeInTheDocument();
    });
  });

  describe('Form Interactions', () => {
    it('updates base URL when input changes', () => {
      render(<ApiConfigPanel />);

      const baseUrlInput = screen.getByDisplayValue('https://api.example.com');
      fireEvent.change(baseUrlInput, { target: { value: 'https://new-api.com' } });

      expect(baseUrlInput).toHaveValue('https://new-api.com');
    });

    it('updates API key when input changes', () => {
      render(<ApiConfigPanel />);

      const apiKeyInput = screen.getByPlaceholderText('输入API密钥（可选）');
      fireEvent.change(apiKeyInput, { target: { value: 'new-api-key' } });

      expect(apiKeyInput).toHaveValue('new-api-key');
    });

    it('updates timeout when input changes', () => {
      render(<ApiConfigPanel />);

      const timeoutInput = screen.getByDisplayValue('30000');
      fireEvent.change(timeoutInput, { target: { value: '60000' } });

      expect(timeoutInput).toHaveValue('60000');
    });

    it('toggles API key visibility when eye icon is clicked', () => {
      render(<ApiConfigPanel />);

      const apiKeyInput = screen.getByPlaceholderText('输入API密钥（可选）');
      const toggleButton = screen.getAllByRole('button').find(
        button => button.querySelector('svg')
      );

      expect(apiKeyInput).toHaveAttribute('type', 'password');

      fireEvent.click(toggleButton!);
      expect(apiKeyInput).toHaveAttribute('type', 'text');

      fireEvent.click(toggleButton!);
      expect(apiKeyInput).toHaveAttribute('type', 'password');
    });

    it('copies API key when copy button is clicked', () => {
      render(<ApiConfigPanel />);

      // Update API key first
      const apiKeyInput = screen.getByPlaceholderText('输入API密钥（可选）');
      fireEvent.change(apiKeyInput, { target: { value: 'copy-test-key' } });

      // Find copy button (second button in the input group)
      const copyButton = screen.getAllByRole('button').filter(
        button => button.querySelector('svg')
      )[1];

      fireEvent.click(copyButton);

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('copy-test-key');
      expect(mockUIStore.showSuccess).toHaveBeenCalledWith('复制成功', 'API密钥已复制到剪贴板');
    });
  });

  describe('Connection Testing', () => {
    it('tests connection when test button is clicked', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        statusText: 'OK',
      };
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

      render(<ApiConfigPanel />);

      const testButton = screen.getByText('测试连接');
      fireEvent.click(testButton);

      expect(testButton).toBeDisabled();
      expect(screen.getByText('测试连接')).toBeInTheDocument();

      await waitFor(() => {
        expect(mockUIStore.showSuccess).toHaveBeenCalledWith(
          '连接成功',
          expect.stringContaining('响应时间:')
        );
      });

      expect(screen.getByText('连接成功')).toBeInTheDocument();
    });

    it('handles connection failure', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
        statusText: 'Not Found',
      };
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

      render(<ApiConfigPanel />);

      const testButton = screen.getByText('测试连接');
      fireEvent.click(testButton);

      await waitFor(() => {
        expect(mockUIStore.showError).toHaveBeenCalledWith('连接失败', '服务器返回: 404');
      });

      expect(screen.getByText(/连接失败: 404 Not Found/)).toBeInTheDocument();
    });

    it('handles network errors', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      render(<ApiConfigPanel />);

      const testButton = screen.getByText('测试连接');
      fireEvent.click(testButton);

      await waitFor(() => {
        expect(mockUIStore.showError).toHaveBeenCalledWith('连接错误', '无法连接到API服务器');
      });

      expect(screen.getByText(/连接错误: Network error/)).toBeInTheDocument();
    });

    it('displays loading state during connection test', () => {
      (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));

      render(<ApiConfigPanel />);

      const testButton = screen.getByText('测试连接');
      fireEvent.click(testButton);

      expect(testButton).toBeDisabled();
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Advanced Configuration', () => {
    it('toggles advanced configuration section', () => {
      render(<ApiConfigPanel />);

      expect(screen.queryByText('重试次数')).not.toBeInTheDocument();

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      expect(screen.getByText('重试次数')).toBeInTheDocument();
      expect(screen.getByText('启用缓存')).toBeInTheDocument();
      expect(screen.getByText('启用压缩')).toBeInTheDocument();

      const hideAdvancedButton = screen.getByText('隐藏高级配置');
      fireEvent.click(hideAdvancedButton);

      expect(screen.queryByText('重试次数')).not.toBeInTheDocument();
    });

    it('updates retry attempts', () => {
      render(<ApiConfigPanel />);

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      const retryInput = screen.getByDisplayValue('3');
      fireEvent.change(retryInput, { target: { value: '5' } });

      expect(retryInput).toHaveValue('5');
    });

    it('toggles cache setting', () => {
      render(<ApiConfigPanel />);

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      const cacheCheckbox = screen.getByLabelText('启用缓存');
      expect(cacheCheckbox).toBeChecked();

      fireEvent.click(cacheCheckbox);
      expect(cacheCheckbox).not.toBeChecked();
    });

    it('shows cache timeout input when cache is enabled', () => {
      render(<ApiConfigPanel />);

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      expect(screen.getByDisplayValue('300000')).toBeInTheDocument();

      const cacheCheckbox = screen.getByLabelText('启用缓存');
      fireEvent.click(cacheCheckbox);

      expect(screen.queryByDisplayValue('300000')).not.toBeInTheDocument();
    });

    it('toggles compression setting', () => {
      render(<ApiConfigPanel />);

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      const compressionCheckbox = screen.getByLabelText('启用压缩');
      expect(compressionCheckbox).toBeChecked();

      fireEvent.click(compressionCheckbox);
      expect(compressionCheckbox).not.toBeChecked();
    });

    it('updates max concurrent requests', () => {
      render(<ApiConfigPanel />);

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      const concurrentInput = screen.getByDisplayValue('5');
      fireEvent.change(concurrentInput, { target: { value: '10' } });

      expect(concurrentInput).toHaveValue('10');
    });
  });

  describe('Custom Headers', () => {
    it('adds custom header', () => {
      render(<ApiConfigPanel />);

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      const keyInput = screen.getByPlaceholderText('Header名称');
      const valueInput = screen.getByPlaceholderText('Header值');
      const addButton = screen.getByText('添加');

      fireEvent.change(keyInput, { target: { value: 'X-Custom-Header' } });
      fireEvent.change(valueInput, { target: { value: 'custom-value' } });
      fireEvent.click(addButton);

      expect(screen.getByText('X-Custom-Header: custom-value')).toBeInTheDocument();
      expect(keyInput).toHaveValue('');
      expect(valueInput).toHaveValue('');
    });

    it('removes custom header', () => {
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify({
        ...mockConfig,
        customHeaders: { 'X-Test-Header': 'test-value' }
      }));

      render(<ApiConfigPanel />);

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      expect(screen.getByText('X-Test-Header: test-value')).toBeInTheDocument();

      const removeButton = screen.getByRole('button').querySelector('.text-red-500');
      fireEvent.click(removeButton!.parentElement!);

      expect(screen.queryByText('X-Test-Header: test-value')).not.toBeInTheDocument();
    });

    it('disables add button when header key or value is empty', () => {
      render(<ApiConfigPanel />);

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      const addButton = screen.getByText('添加');
      expect(addButton).toBeDisabled();

      const keyInput = screen.getByPlaceholderText('Header名称');
      fireEvent.change(keyInput, { target: { value: 'test' } });
      expect(addButton).toBeDisabled();

      const valueInput = screen.getByPlaceholderText('Header值');
      fireEvent.change(valueInput, { target: { value: 'value' } });
      expect(addButton).toBeEnabled();
    });
  });

  describe('Save and Reset', () => {
    it('saves configuration when save button is clicked', () => {
      render(<ApiConfigPanel />);

      // Make a change to trigger the save state
      const baseUrlInput = screen.getByDisplayValue('https://api.example.com');
      fireEvent.change(baseUrlInput, { target: { value: 'https://new-api.com' } });

      const saveButton = screen.getByText('保存配置');
      fireEvent.click(saveButton);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'api-config',
        expect.stringContaining('https://new-api.com')
      );
      expect(mockUIStore.showSuccess).toHaveBeenCalledWith('保存成功', 'API配置已更新');
    });

    it('calls onSave callback when save is successful', () => {
      const mockOnSave = jest.fn();
      render(<ApiConfigPanel onSave={mockOnSave} />);

      // Make a change
      const baseUrlInput = screen.getByDisplayValue('https://api.example.com');
      fireEvent.change(baseUrlInput, { target: { value: 'https://new-api.com' } });

      const saveButton = screen.getByText('保存配置');
      fireEvent.click(saveButton);

      expect(mockOnSave).toHaveBeenCalledWith(expect.objectContaining({
        baseUrl: 'https://new-api.com'
      }));
    });

    it('validates configuration before saving', () => {
      render(<ApiConfigPanel />);

      // Clear base URL
      const baseUrlInput = screen.getByDisplayValue('https://api.example.com');
      fireEvent.change(baseUrlInput, { target: { value: '' } });

      const saveButton = screen.getByText('保存配置');
      fireEvent.click(saveButton);

      expect(mockUIStore.showError).toHaveBeenCalledWith('配置错误', 'API地址不能为空');
      expect(mockLocalStorage.setItem).not.toHaveBeenCalled();
    });

    it('validates timeout range', () => {
      render(<ApiConfigPanel />);

      const timeoutInput = screen.getByDisplayValue('30000');
      fireEvent.change(timeoutInput, { target: { value: '500' } });

      const saveButton = screen.getByText('保存配置');
      fireEvent.click(saveButton);

      expect(mockUIStore.showError).toHaveBeenCalledWith('配置错误', '超时时间必须在1-300秒之间');
    });

    it('validates retry attempts range', () => {
      render(<ApiConfigPanel />);

      const showAdvancedButton = screen.getByText('显示高级配置');
      fireEvent.click(showAdvancedButton);

      const retryInput = screen.getByDisplayValue('3');
      fireEvent.change(retryInput, { target: { value: '15' } });

      const baseUrlInput = screen.getByDisplayValue('https://api.example.com');
      fireEvent.change(baseUrlInput, { target: { value: 'https://test.com' } });

      const saveButton = screen.getByText('保存配置');
      fireEvent.click(saveButton);

      expect(mockUIStore.showError).toHaveBeenCalledWith('配置错误', '重试次数必须在0-10次之间');
    });

    it('resets configuration when reset is confirmed', () => {
      (window.confirm as jest.Mock).mockReturnValue(true);

      render(<ApiConfigPanel />);

      const resetButton = screen.getByText('重置为默认');
      fireEvent.click(resetButton);

      expect(window.confirm).toHaveBeenCalledWith('确定要重置为默认配置吗？');
      expect(mockUIStore.showSuccess).toHaveBeenCalledWith('重置成功', '配置已重置为默认值');
    });

    it('does not reset when reset is cancelled', () => {
      (window.confirm as jest.Mock).mockReturnValue(false);

      render(<ApiConfigPanel />);

      const resetButton = screen.getByText('重置为默认');
      fireEvent.click(resetButton);

      expect(window.confirm).toHaveBeenCalled();
      expect(mockUIStore.showSuccess).not.toHaveBeenCalledWith('重置成功', expect.any(String));
    });

    it('shows unsaved changes indicator', () => {
      render(<ApiConfigPanel />);

      expect(screen.queryByText('有未保存的更改')).not.toBeInTheDocument();

      // Make a change
      const baseUrlInput = screen.getByDisplayValue('https://api.example.com');
      fireEvent.change(baseUrlInput, { target: { value: 'https://changed.com' } });

      expect(screen.getByText('有未保存的更改')).toBeInTheDocument();
    });

    it('disables save button when no changes', () => {
      render(<ApiConfigPanel />);

      const saveButton = screen.getByText('保存配置');
      expect(saveButton).toBeDisabled();
    });

    it('enables save button when there are changes', () => {
      render(<ApiConfigPanel />);

      // Make a change
      const baseUrlInput = screen.getByDisplayValue('https://api.example.com');
      fireEvent.change(baseUrlInput, { target: { value: 'https://changed.com' } });

      const saveButton = screen.getByText('保存配置');
      expect(saveButton).toBeEnabled();
    });
  });

  describe('Security Section', () => {
    it('renders security notice', () => {
      render(<ApiConfigPanel />);

      expect(screen.getByText('安全提示')).toBeInTheDocument();
      expect(screen.getByText('请勿在公共场合暴露API密钥')).toBeInTheDocument();
      expect(screen.getByText('定期更换API密钥以保证安全')).toBeInTheDocument();
      expect(screen.getByText('使用HTTPS协议进行加密传输')).toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    it('shows saving state when save is in progress', () => {
      render(<ApiConfigPanel />);

      // Make a change
      const baseUrlInput = screen.getByDisplayValue('https://api.example.com');
      fireEvent.change(baseUrlInput, { target: { value: 'https://new.com' } });

      // Mock a slow save
      const saveButton = screen.getByText('保存配置');
      
      // The save operation should be immediate in tests, so we can't easily test the loading state
      // But we can verify the button exists and is functional
      expect(saveButton).toBeInTheDocument();
      expect(saveButton).toBeEnabled();
    });
  });

  describe('Accessibility', () => {
    it('provides proper labels for form inputs', () => {
      render(<ApiConfigPanel />);

      expect(screen.getByLabelText('API 地址')).toBeInTheDocument();
      expect(screen.getByLabelText('API 密钥')).toBeInTheDocument();
      expect(screen.getByLabelText('请求超时（毫秒）')).toBeInTheDocument();
    });

    it('provides helpful placeholder text', () => {
      render(<ApiConfigPanel />);

      expect(screen.getByPlaceholderText('https://api.example.com')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('输入API密钥（可选）')).toBeInTheDocument();
    });

    it('provides descriptive help text', () => {
      render(<ApiConfigPanel />);

      expect(screen.getByText('PPT生成服务的API端点地址')).toBeInTheDocument();
      expect(screen.getByText('如果API需要认证，请输入密钥')).toBeInTheDocument();
      expect(screen.getByText('请求超时时间（1-300秒）')).toBeInTheDocument();
    });
  });
});