import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ApiConfigPanel from '@/components/settings/ApiConfigPanel';
import { useUIStore, showToast } from '@/store/uiStore';
import {
  Cog6ToothIcon,
  ServerStackIcon,
  PaintBrushIcon,
  LanguageIcon,
  BellIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline';

interface SettingSection {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  path: string;
}

const settingSections: SettingSection[] = [
  {
    id: 'api',
    title: 'API 配置',
    description: '配置后端API连接和认证设置',
    icon: ServerStackIcon,
    path: '/settings/api'
  },
  {
    id: 'preferences',
    title: '偏好设置',
    description: '自定义界面主题、语言和显示选项',
    icon: PaintBrushIcon,
    path: '/settings/preferences'
  },
  {
    id: 'language',
    title: '语言设置',
    description: '选择界面语言和区域设置',
    icon: LanguageIcon,
    path: '/settings/language'
  },
  {
    id: 'notifications',
    title: '通知设置',
    description: '管理通知偏好和提醒方式',
    icon: BellIcon,
    path: '/settings/notifications'
  },
  {
    id: 'security',
    title: '安全与隐私',
    description: '管理数据安全和隐私设置',
    icon: ShieldCheckIcon,
    path: '/settings/security'
  }
];

const SettingsPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, setTheme, language, setLanguage } = useUIStore();
  
  const [activeSection, setActiveSection] = useState(() => {
    const path = location.pathname;
    if (path.includes('/api')) return 'api';
    if (path.includes('/preferences')) return 'preferences';
    if (path.includes('/language')) return 'language';
    if (path.includes('/notifications')) return 'notifications';
    if (path.includes('/security')) return 'security';
    return 'api';
  });

  const handleSectionChange = (sectionId: string, path: string) => {
    setActiveSection(sectionId);
    navigate(path);
  };

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    showToast.success('主题切换成功', `主题已切换为 ${newTheme === 'light' ? '浅色' : newTheme === 'dark' ? '深色' : '跟随系统'}`);
  };

  const handleLanguageChange = (newLanguage: 'zh' | 'en') => {
    setLanguage(newLanguage);
    showToast.success('语言切换成功', `语言已切换为 ${newLanguage === 'zh' ? '中文' : '英文'}`);
  };

  const renderContent = () => {
    switch (activeSection) {
      case 'api':
        return <ApiConfigPanel />;
      
      case 'preferences':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                主题设置
              </h3>
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => handleThemeChange('light')}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    theme === 'light'
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                      : 'border-secondary-200 dark:border-secondary-700 hover:border-secondary-300'
                  }`}
                >
                  <div className="text-center">
                    <div className="w-12 h-12 bg-white rounded-lg mx-auto mb-2 border border-secondary-200"></div>
                    <p className="text-sm">浅色</p>
                  </div>
                </button>
                <button
                  onClick={() => handleThemeChange('dark')}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    theme === 'dark'
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                      : 'border-secondary-200 dark:border-secondary-700 hover:border-secondary-300'
                  }`}
                >
                  <div className="text-center">
                    <div className="w-12 h-12 bg-secondary-800 rounded-lg mx-auto mb-2 border border-secondary-700"></div>
                    <p className="text-sm">深色</p>
                  </div>
                </button>
                <button
                  onClick={() => handleThemeChange('system')}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    theme === 'system'
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                      : 'border-secondary-200 dark:border-secondary-700 hover:border-secondary-300'
                  }`}
                >
                  <div className="text-center">
                    <div className="w-12 h-12 bg-gradient-to-r from-white to-secondary-800 rounded-lg mx-auto mb-2 border border-secondary-400"></div>
                    <p className="text-sm">跟随系统</p>
                  </div>
                </button>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                字体大小
              </h3>
              <select className="input-field">
                <option value="small">小</option>
                <option value="medium">中</option>
                <option value="large">大</option>
              </select>
            </div>

            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                动画效果
              </h3>
              <label className="flex items-center">
                <input type="checkbox" className="form-checkbox" defaultChecked />
                <span className="ml-2">启用界面动画</span>
              </label>
            </div>
          </div>
        );
      
      case 'language':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                界面语言
              </h3>
              <div className="space-y-3">
                <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-secondary-50 dark:hover:bg-secondary-700">
                  <input
                    type="radio"
                    name="language"
                    value="zh"
                    checked={language === 'zh'}
                    onChange={() => handleLanguageChange('zh')}
                    className="form-radio"
                  />
                  <span className="ml-3">
                    <span className="block font-medium">简体中文</span>
                    <span className="block text-sm text-secondary-500">系统默认语言</span>
                  </span>
                </label>
                <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-secondary-50 dark:hover:bg-secondary-700">
                  <input
                    type="radio"
                    name="language"
                    value="en"
                    checked={language === 'en'}
                    onChange={() => handleLanguageChange('en')}
                    className="form-radio"
                  />
                  <span className="ml-3">
                    <span className="block font-medium">English</span>
                    <span className="block text-sm text-secondary-500">English Interface</span>
                  </span>
                </label>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                时区设置
              </h3>
              <select className="input-field">
                <option value="Asia/Shanghai">中国标准时间 (UTC+8)</option>
                <option value="America/New_York">美国东部时间 (UTC-5)</option>
                <option value="Europe/London">格林威治标准时间 (UTC+0)</option>
              </select>
            </div>
          </div>
        );
      
      case 'notifications':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                通知偏好
              </h3>
              <div className="space-y-3">
                <label className="flex items-center justify-between">
                  <span>PPT生成完成通知</span>
                  <input type="checkbox" className="form-checkbox" defaultChecked />
                </label>
                <label className="flex items-center justify-between">
                  <span>自动保存通知</span>
                  <input type="checkbox" className="form-checkbox" defaultChecked />
                </label>
                <label className="flex items-center justify-between">
                  <span>错误提示</span>
                  <input type="checkbox" className="form-checkbox" defaultChecked />
                </label>
                <label className="flex items-center justify-between">
                  <span>更新提醒</span>
                  <input type="checkbox" className="form-checkbox" />
                </label>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                通知声音
              </h3>
              <label className="flex items-center">
                <input type="checkbox" className="form-checkbox" />
                <span className="ml-2">启用通知声音</span>
              </label>
            </div>
          </div>
        );
      
      case 'security':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                数据存储
              </h3>
              <div className="space-y-4">
                <div className="p-4 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
                  <p className="text-sm text-secondary-600 dark:text-secondary-300 mb-2">
                    本地存储使用情况
                  </p>
                  <div className="w-full bg-secondary-200 dark:bg-secondary-600 rounded-full h-2 mb-2">
                    <div className="bg-primary-500 h-2 rounded-full" style={{ width: '35%' }}></div>
                  </div>
                  <p className="text-xs text-secondary-500">已使用 3.5 MB / 10 MB</p>
                </div>
                <button className="btn btn-secondary">
                  清理缓存数据
                </button>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                导出与备份
              </h3>
              <div className="space-y-3">
                <button className="btn btn-primary w-full">
                  导出所有项目
                </button>
                <button className="btn btn-secondary w-full">
                  导入项目数据
                </button>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">
                危险操作
              </h3>
              <button className="btn bg-red-500 hover:bg-red-600 text-white w-full">
                清除所有数据
              </button>
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-secondary-900 dark:text-white">
          设置
        </h1>
        <p className="text-secondary-600 dark:text-secondary-400 mt-2">
          管理应用程序配置和偏好设置
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <nav className="space-y-1">
            {settingSections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => handleSectionChange(section.id, section.path)}
                  className={`w-full flex items-start p-3 rounded-lg transition-colors ${
                    activeSection === section.id
                      ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                      : 'hover:bg-secondary-50 dark:hover:bg-secondary-700 text-secondary-700 dark:text-secondary-300'
                  }`}
                >
                  <Icon className="w-5 h-5 mt-0.5 mr-3 flex-shrink-0" />
                  <div className="text-left">
                    <p className="font-medium">{section.title}</p>
                    <p className="text-xs mt-1 opacity-70">
                      {section.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          <div className="bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 p-6">
            {renderContent()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;