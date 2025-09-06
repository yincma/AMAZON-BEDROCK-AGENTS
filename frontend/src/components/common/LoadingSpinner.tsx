import React from 'react';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  message?: string;
  className?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'medium', 
  message,
  className = ''
}) => {
  const sizeClasses = {
    small: 'w-6 h-6',
    medium: 'w-10 h-10',
    large: 'w-16 h-16'
  };

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div className={`relative ${sizeClasses[size]}`}>
        <div className={`absolute inset-0 ${sizeClasses[size]} border-4 border-secondary-200 dark:border-secondary-700 rounded-full`}></div>
        <div className={`absolute inset-0 ${sizeClasses[size]} border-4 border-primary-500 rounded-full animate-spin border-t-transparent`}></div>
      </div>
      {message && (
        <p className="mt-4 text-secondary-600 dark:text-secondary-400 text-sm">
          {message}
        </p>
      )}
    </div>
  );
};

export default LoadingSpinner;