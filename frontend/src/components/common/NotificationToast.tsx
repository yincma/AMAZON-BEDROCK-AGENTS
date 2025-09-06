import React, { useEffect, useState, useCallback } from 'react';
import {
  CheckCircle,
  AlertTriangle,
  Info,
  XCircle,
  X,
  Clock,
  Loader2,
} from 'lucide-react';
import { useUIStore, Notification } from '@/store/uiStore';

interface ToastItemProps {
  notification: Notification;
  onRemove: (id: string) => void;
  position: string;
  progress?: number;
}

const ToastItem: React.FC<ToastItemProps> = ({
  notification,
  onRemove,
  position,
  progress,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isRemoving, setIsRemoving] = useState(false);

  useEffect(() => {
    // Trigger enter animation
    const timer = setTimeout(() => setIsVisible(true), 10);
    return () => clearTimeout(timer);
  }, []);

  const handleRemove = useCallback(() => {
    setIsRemoving(true);
    setTimeout(() => {
      onRemove(notification.id);
    }, 200); // Match animation duration
  }, [notification.id, onRemove]);

  const icons = {
    success: <CheckCircle className="w-6 h-6 text-green-400" />,
    error: <XCircle className="w-6 h-6 text-red-400" />,
    info: <Info className="w-6 h-6 text-blue-400" />,
    warning: <AlertTriangle className="w-6 h-6 text-yellow-400" />,
  };

  const backgrounds = {
    success: 'bg-green-600 dark:bg-green-700',
    error: 'bg-red-600 dark:bg-red-700',
    info: 'bg-blue-600 dark:bg-blue-700',
    warning: 'bg-yellow-600 dark:bg-yellow-700',
  };

  const borderColors = {
    success: 'border-green-500',
    error: 'border-red-500',
    info: 'border-blue-500',
    warning: 'border-yellow-500',
  };

  const getTransformClass = () => {
    const isRight = position.includes('right');
    const isLeft = position.includes('left');
    const isTop = position.includes('top');
    const isBottom = position.includes('bottom');
    const isCenter = position.includes('center');

    if (!isVisible || isRemoving) {
      if (isRight) return 'translate-x-full opacity-0';
      if (isLeft) return '-translate-x-full opacity-0';
      if (isCenter && isTop) return '-translate-y-full opacity-0';
      if (isCenter && isBottom) return 'translate-y-full opacity-0';
    }

    return 'translate-x-0 translate-y-0 opacity-100';
  };

  return (
    <div
      className={`
        transform transition-all duration-200 ease-in-out
        ${getTransformClass()}
        max-w-md w-full bg-white dark:bg-gray-800
        shadow-lg rounded-lg pointer-events-auto
        border-l-4 ${borderColors[notification.type]}
        ring-1 ring-black ring-opacity-5 dark:ring-white dark:ring-opacity-10
      `}
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {icons[notification.type]}
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {notification.title}
            </p>
            {notification.message && (
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                {notification.message}
              </p>
            )}
            
            {/* Progress Bar */}
            {progress !== undefined && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                  <span>Progress</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-300 ease-out rounded-full ${
                      progress === 100 
                        ? 'bg-green-500' 
                        : backgrounds[notification.type].replace('bg-', 'bg-').split(' ')[0]
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
                  />
                </div>
              </div>
            )}

            {/* Action Button */}
            {notification.action && (
              <div className="mt-3">
                <button
                  onClick={notification.action.onClick}
                  className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300"
                >
                  {notification.action.label}
                </button>
              </div>
            )}

            {/* Timestamp */}
            <div className="mt-2 flex items-center text-xs text-gray-400 dark:text-gray-500">
              <Clock className="w-3 h-3 mr-1" />
              {new Intl.DateTimeFormat('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              }).format(notification.timestamp)}
            </div>
          </div>
          
          {/* Close Button */}
          <div className="ml-4 flex-shrink-0">
            <button
              onClick={handleRemove}
              className="inline-flex text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 rounded-md p-1"
            >
              <span className="sr-only">Close</span>
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Progress notification manager
export class ProgressNotification {
  private id: string;
  private title: string;
  private baseMessage: string;
  private addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => string;
  private removeNotification: (id: string) => void;
  private updateProgress?: (progress: number, message?: string) => void;

  constructor(title: string, message: string) {
    const uiStore = useUIStore.getState();
    this.addNotification = uiStore.addNotification;
    this.removeNotification = uiStore.removeNotification;
    this.title = title;
    this.baseMessage = message;
    this.id = this.addNotification({
      type: 'info',
      title,
      message,
      duration: 0, // Persistent until completed
    });
  }

  update(progress: number, message?: string) {
    // Update the progress through a custom mechanism
    if (this.updateProgress) {
      this.updateProgress(progress, message);
    }
  }

  setUpdateHandler(handler: (progress: number, message?: string) => void) {
    this.updateProgress = handler;
  }

  complete(successMessage?: string) {
    this.removeNotification(this.id);
    if (successMessage) {
      this.addNotification({
        type: 'success',
        title: this.title,
        message: successMessage,
        duration: 4000,
      });
    }
  }

  error(errorMessage: string) {
    this.removeNotification(this.id);
    this.addNotification({
      type: 'error',
      title: this.title,
      message: errorMessage,
      duration: 8000,
    });
  }

  getId(): string {
    return this.id;
  }
}

export const createProgressNotification = (title: string, message: string) => {
  return new ProgressNotification(title, message);
};

// Main NotificationToast component
const NotificationToast: React.FC = () => {
  const { notifications, removeNotification, toastPosition } = useUIStore();
  const [progressMap, setProgressMap] = useState<Map<string, number>>(new Map());

  // Handle automatic removal of notifications
  useEffect(() => {
    const timers = new Map<string, NodeJS.Timeout>();

    notifications.forEach((notification) => {
      if (notification.duration && notification.duration > 0 && !timers.has(notification.id)) {
        const timer = setTimeout(() => {
          removeNotification(notification.id);
          timers.delete(notification.id);
        }, notification.duration);
        timers.set(notification.id, timer);
      }
    });

    // Cleanup timers for removed notifications
    Array.from(timers.keys()).forEach((id) => {
      if (!notifications.find(n => n.id === id)) {
        const timer = timers.get(id);
        if (timer) {
          clearTimeout(timer);
          timers.delete(id);
        }
      }
    });

    return () => {
      // Clear all timers on unmount
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [notifications, removeNotification]);

  const getContainerClasses = () => {
    const baseClasses = 'fixed z-50 p-4 space-y-3 pointer-events-none';
    
    switch (toastPosition) {
      case 'top-left':
        return `${baseClasses} top-0 left-0`;
      case 'top-center':
        return `${baseClasses} top-0 left-1/2 transform -translate-x-1/2`;
      case 'top-right':
        return `${baseClasses} top-0 right-0`;
      case 'bottom-left':
        return `${baseClasses} bottom-0 left-0`;
      case 'bottom-center':
        return `${baseClasses} bottom-0 left-1/2 transform -translate-x-1/2`;
      case 'bottom-right':
        return `${baseClasses} bottom-0 right-0`;
      default:
        return `${baseClasses} top-0 right-0`;
    }
  };

  const shouldReverse = toastPosition.includes('bottom');
  const displayNotifications = shouldReverse 
    ? [...notifications].reverse() 
    : notifications;

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div className={getContainerClasses()}>
      {displayNotifications.map((notification) => (
        <ToastItem
          key={notification.id}
          notification={notification}
          onRemove={removeNotification}
          position={toastPosition}
          progress={progressMap.get(notification.id)}
        />
      ))}
    </div>
  );
};

// Convenience functions that work with uiStore
export const showToast = {
  success: (title: string, message?: string, duration?: number) => {
    const uiStore = useUIStore.getState();
    return uiStore.addNotification({ type: 'success', title, message, duration });
  },
  error: (title: string, message?: string, duration?: number) => {
    const uiStore = useUIStore.getState();
    return uiStore.addNotification({ type: 'error', title, message, duration: duration || 8000 });
  },
  warning: (title: string, message?: string, duration?: number) => {
    const uiStore = useUIStore.getState();
    return uiStore.addNotification({ type: 'warning', title, message, duration: duration || 6000 });
  },
  info: (title: string, message?: string, duration?: number) => {
    const uiStore = useUIStore.getState();
    return uiStore.addNotification({ type: 'info', title, message, duration });
  },
  dismiss: (id?: string) => {
    const uiStore = useUIStore.getState();
    if (id) {
      uiStore.removeNotification(id);
    } else {
      uiStore.clearNotifications();
    }
  },
};

export default NotificationToast;