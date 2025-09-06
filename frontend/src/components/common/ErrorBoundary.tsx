import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
    // Optionally reload the page
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-secondary-50 dark:bg-secondary-900 flex items-center justify-center px-4">
          <div className="max-w-md w-full bg-white dark:bg-secondary-800 rounded-lg shadow-xl p-6">
            <div className="flex items-center justify-center w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full mx-auto mb-4">
              <ExclamationTriangleIcon className="w-8 h-8 text-red-600 dark:text-red-400" />
            </div>
            
            <h1 className="text-2xl font-bold text-center text-secondary-900 dark:text-white mb-2">
              出现了错误
            </h1>
            
            <p className="text-center text-secondary-600 dark:text-secondary-400 mb-6">
              应用程序遇到了意外错误。请刷新页面重试。
            </p>

            {import.meta.env.DEV && this.state.error && (
              <div className="mb-6">
                <details className="bg-secondary-100 dark:bg-secondary-700 rounded-lg p-4">
                  <summary className="cursor-pointer font-medium text-sm text-secondary-700 dark:text-secondary-300">
                    错误详情（开发模式）
                  </summary>
                  <div className="mt-2 space-y-2">
                    <p className="text-xs text-red-600 dark:text-red-400 font-mono">
                      {this.state.error.toString()}
                    </p>
                    {this.state.errorInfo && (
                      <pre className="text-xs text-secondary-600 dark:text-secondary-400 overflow-x-auto">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    )}
                  </div>
                </details>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="flex-1 btn btn-primary"
              >
                刷新页面
              </button>
              <button
                onClick={() => window.location.href = '/'}
                className="flex-1 btn btn-secondary"
              >
                返回首页
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;