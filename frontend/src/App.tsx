import React from 'react';
import RouterApp from './router';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import NotificationToast from '@/components/common/NotificationToast';
import './styles/globals.css';

function App() {
  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-secondary-50 dark:bg-secondary-900">
        <RouterApp />
        <NotificationToast />
      </div>
    </ErrorBoundary>
  );
}

export default App;