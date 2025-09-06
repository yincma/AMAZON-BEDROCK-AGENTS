import React, { useState, useEffect } from 'react';
import { usePresentationApi } from '@/hooks/usePresentationApi';
import { CreatePresentationRequest } from '@/services/PresentationApiService';

/**
 * 演示文稿生成器组件
 * 演示如何使用 PresentationApiService 与后端通信
 */
export const PresentationGenerator: React.FC = () => {
  const {
    loading,
    error,
    currentTask,
    presentations,
    createPresentation,
    pollTask,
    listPresentations,
    downloadPresentation,
    checkHealth,
    clearError
  } = usePresentationApi({
    autoInit: true
  });

  const [formData, setFormData] = useState<CreatePresentationRequest>({
    title: '',
    topic: '',
    language: 'zh',
    slide_count: 10,
    style: 'professional',
    include_speaker_notes: true
  });

  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [taskProgress, setTaskProgress] = useState<string>('');

  // 组件加载时检查健康状态
  useEffect(() => {
    const checkApiHealth = async () => {
      const healthy = await checkHealth();
      setIsHealthy(healthy);
      if (healthy) {
        await listPresentations();
      }
    };
    checkApiHealth();
  }, [checkHealth, listPresentations]);

  // 处理表单输入
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'slide_count' ? parseInt(value) : value
    }));
  };

  // 提交生成请求
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setTaskProgress('正在创建任务...');

    // 创建演示文稿任务
    const task = await createPresentation(formData);
    
    if (task) {
      setTaskProgress('任务已创建，正在处理...');
      
      // 轮询任务状态直到完成
      const completedTask = await pollTask(task.task_id, (status) => {
        setTaskProgress(`状态: ${status}`);
      });

      if (completedTask?.status === 'completed') {
        setTaskProgress('演示文稿生成完成！');
        // 刷新列表
        await listPresentations();
      } else if (completedTask?.status === 'failed') {
        setTaskProgress('生成失败: ' + (completedTask.error || '未知错误'));
      }
    }
  };

  // 下载演示文稿
  const handleDownload = async (presentationId: string) => {
    await downloadPresentation(presentationId, 'pptx');
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">AI 演示文稿生成器</h1>
      
      {/* 健康状态指示器 */}
      <div className="mb-6 p-4 rounded-lg bg-gray-100">
        <div className="flex items-center">
          <span className="mr-2">API 状态:</span>
          {isHealthy === null ? (
            <span className="text-gray-500">检查中...</span>
          ) : isHealthy ? (
            <span className="text-green-600 font-semibold">✅ 在线</span>
          ) : (
            <span className="text-red-600 font-semibold">❌ 离线</span>
          )}
        </div>
      </div>

      {/* 生成表单 */}
      <form onSubmit={handleSubmit} className="space-y-4 mb-8">
        <div>
          <label className="block text-sm font-medium mb-1">标题 *</label>
          <input
            type="text"
            name="title"
            value={formData.title}
            onChange={handleInputChange}
            required
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="例如：2024年度总结报告"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">主题内容 *</label>
          <textarea
            name="topic"
            value={formData.topic}
            onChange={handleInputChange}
            required
            rows={4}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="描述您想要生成的演示文稿内容..."
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">语言</label>
            <select
              name="language"
              value={formData.language}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="zh">中文</option>
              <option value="en">English</option>
              <option value="ja">日本語</option>
              <option value="ko">한국어</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
              <option value="de">Deutsch</option>
              <option value="pt">Português</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">幻灯片数量</label>
            <input
              type="number"
              name="slide_count"
              value={formData.slide_count}
              onChange={handleInputChange}
              min="5"
              max="30"
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">风格</label>
          <select
            name="style"
            value={formData.style}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border rounded-lg"
          >
            <option value="professional">专业</option>
            <option value="creative">创意</option>
            <option value="minimalist">简约</option>
            <option value="technical">技术</option>
            <option value="academic">学术</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading || !isHealthy}
          className={`w-full py-2 px-4 rounded-lg font-medium text-white transition-colors ${
            loading || !isHealthy
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {loading ? '处理中...' : '生成演示文稿'}
        </button>
      </form>

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
          {error}
        </div>
      )}

      {/* 进度提示 */}
      {taskProgress && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg text-blue-600">
          {taskProgress}
        </div>
      )}

      {/* 当前任务状态 */}
      {currentTask && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="font-medium mb-2">当前任务</h3>
          <p>任务 ID: {currentTask.task_id}</p>
          <p>状态: {currentTask.status}</p>
          {currentTask.created_at && (
            <p>创建时间: {new Date(currentTask.created_at).toLocaleString()}</p>
          )}
        </div>
      )}

      {/* 演示文稿列表 */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">已生成的演示文稿</h2>
        {presentations.length === 0 ? (
          <p className="text-gray-500">暂无演示文稿</p>
        ) : (
          <div className="space-y-3">
            {presentations.map((presentation) => (
              <div
                key={presentation.presentation_id}
                className="p-4 border rounded-lg hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-medium text-lg">{presentation.title}</h3>
                    <p className="text-sm text-gray-600">
                      {presentation.metadata?.total_slides || 0} 张幻灯片
                    </p>
                    <p className="text-sm text-gray-500">
                      创建于: {presentation.metadata?.created_at 
                        ? new Date(presentation.metadata.created_at).toLocaleString()
                        : '未知'}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDownload(presentation.presentation_id)}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    下载 PPTX
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PresentationGenerator;