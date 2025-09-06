import React, { useState } from 'react';
import { useUIStore, showToast } from '@/store/uiStore';
import { createProgressNotification } from '@/components/common/NotificationToast';

const NotificationTest: React.FC = () => {
  const { 
    addNotification, 
    clearNotifications, 
    setToastPosition,
    toastPosition 
  } = useUIStore();
  const [progress, setProgress] = useState(0);

  const testSuccess = () => {
    addNotification({
      type: 'success',
      title: '操作成功',
      message: '你的操作已成功完成！',
    });
  };

  const testError = () => {
    addNotification({
      type: 'error',
      title: '操作失败',
      message: '抱歉，操作过程中出现了错误，请重试。',
    });
  };

  const testWarning = () => {
    addNotification({
      type: 'warning',
      title: '警告',
      message: '此操作可能会影响现有数据，请确认后继续。',
    });
  };

  const testInfo = () => {
    addNotification({
      type: 'info',
      title: '提示信息',
      message: '这是一条普通的信息提示。',
    });
  };

  const testWithAction = () => {
    addNotification({
      type: 'warning',
      title: '需要确认',
      message: '是否要删除此项目？',
      action: {
        label: '确认删除',
        onClick: () => {
          addNotification({
            type: 'success',
            title: '已删除',
            message: '项目已成功删除！',
          });
        },
      },
    });
  };

  const testProgress = () => {
    const progressNotification = createProgressNotification('文件上传', '正在上传文件...');
    let currentProgress = 0;

    const interval = setInterval(() => {
      currentProgress += 10;
      setProgress(currentProgress);
      
      if (currentProgress >= 100) {
        clearInterval(interval);
        progressNotification.complete('文件上传完成！');
        setProgress(0);
      } else {
        progressNotification.update(currentProgress, `正在上传文件... ${currentProgress}%`);
      }
    }, 500);
  };

  const positions: Array<typeof toastPosition> = [
    'top-left',
    'top-center', 
    'top-right',
    'bottom-left',
    'bottom-center',
    'bottom-right'
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">通知系统测试</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 基础通知测试 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-md">
          <h2 className="text-lg font-semibold mb-4">基础通知</h2>
          <div className="space-y-3">
            <button
              onClick={testSuccess}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
            >
              成功通知
            </button>
            <button
              onClick={testError}
              className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            >
              错误通知
            </button>
            <button
              onClick={testWarning}
              className="w-full px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 transition-colors"
            >
              警告通知
            </button>
            <button
              onClick={testInfo}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              信息通知
            </button>
          </div>
        </div>

        {/* 高级功能测试 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-md">
          <h2 className="text-lg font-semibold mb-4">高级功能</h2>
          <div className="space-y-3">
            <button
              onClick={testWithAction}
              className="w-full px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors"
            >
              带操作的通知
            </button>
            <button
              onClick={testProgress}
              className="w-full px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
            >
              进度通知
            </button>
            <button
              onClick={clearNotifications}
              className="w-full px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
            >
              清除所有通知
            </button>
          </div>
        </div>
      </div>

      {/* 位置设置 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-md mt-6">
        <h2 className="text-lg font-semibold mb-4">通知位置设置</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {positions.map((position) => (
            <button
              key={position}
              onClick={() => setToastPosition(position)}
              className={`px-4 py-2 rounded-md transition-colors ${
                toastPosition === position
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-500'
              }`}
            >
              {position.split('-').map(word => 
                word.charAt(0).toUpperCase() + word.slice(1)
              ).join(' ')}
            </button>
          ))}
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-3">
          当前位置: <strong>{toastPosition}</strong>
        </p>
      </div>

      {/* 使用说明 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-md mt-6">
        <h2 className="text-lg font-semibold mb-4">使用说明</h2>
        <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <p><strong>基础用法:</strong></p>
          <code className="block bg-gray-100 dark:bg-gray-700 p-2 rounded">
            {`import { useUIStore } from '@/store/uiStore';
const { showSuccess, showError, showWarning, showInfo } = useUIStore();
showSuccess('标题', '消息内容');`}
          </code>
          
          <p className="mt-4"><strong>进度通知:</strong></p>
          <code className="block bg-gray-100 dark:bg-gray-700 p-2 rounded">
            {`import { createProgressNotification } from '@/components/common/NotificationToast';
const progress = createProgressNotification('任务', '正在处理...');
progress.update(50); // 更新进度
progress.complete('完成！'); // 完成`}
          </code>
        </div>
      </div>
    </div>
  );
};

export default NotificationTest;