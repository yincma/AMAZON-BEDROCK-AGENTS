// 国际化（i18n）核心模块
class I18n {
    constructor() {
        this.currentLanguage = 'zh-CN';
        this.translations = {};
        this.supportedLanguages = ['zh-CN', 'en-US'];

        this.init();
    }

    async init() {
        // 从localStorage读取保存的语言设置
        const savedLanguage = localStorage.getItem('language');
        if (savedLanguage && this.supportedLanguages.includes(savedLanguage)) {
            this.currentLanguage = savedLanguage;
        }

        // 加载当前语言包
        await this.loadLanguage(this.currentLanguage);

        // 应用翻译
        this.applyTranslations();
    }

    async loadLanguage(language) {
        if (!this.supportedLanguages.includes(language)) {
            console.warn(`Unsupported language: ${language}`);
            return;
        }

        try {
            const response = await fetch(`js/i18n/${language}.json`);
            if (!response.ok) {
                throw new Error(`Failed to load language file: ${language}`);
            }

            this.translations = await response.json();
            this.currentLanguage = language;

            // 保存语言设置
            localStorage.setItem('language', language);

            // 更新HTML lang属性
            document.documentElement.lang = language;

        } catch (error) {
            console.error('Error loading language file:', error);
            // 如果加载失败且不是默认语言，尝试加载默认语言
            if (language !== 'zh-CN') {
                await this.loadLanguage('zh-CN');
            }
        }
    }

    async switchLanguage(language) {
        if (language === this.currentLanguage) {
            return;
        }

        await this.loadLanguage(language);
        this.applyTranslations();

        // 触发语言切换事件
        const event = new CustomEvent('languageChanged', {
            detail: { language: this.currentLanguage }
        });
        document.dispatchEvent(event);
    }

    t(key, params = {}) {
        const keys = key.split('.');
        let value = this.translations;

        for (const k of keys) {
            if (value && typeof value === 'object' && k in value) {
                value = value[k];
            } else {
                console.warn(`Translation key not found: ${key}`);
                return key; // 返回键名作为后备
            }
        }

        // 支持参数替换
        if (typeof value === 'string' && Object.keys(params).length > 0) {
            return this.interpolate(value, params);
        }

        return value;
    }

    interpolate(text, params) {
        return text.replace(/\{\{(\w+)\}\}/g, (match, key) => {
            return params[key] !== undefined ? params[key] : match;
        });
    }

    applyTranslations() {
        // 查找所有带有data-i18n属性的元素
        const elements = document.querySelectorAll('[data-i18n]');

        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.t(key);

            // 根据元素类型设置内容
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                if (element.type === 'submit' || element.type === 'button') {
                    element.value = translation;
                } else {
                    element.placeholder = translation;
                }
            } else {
                element.textContent = translation;
            }
        });

        // 更新title属性
        const titleElements = document.querySelectorAll('[data-i18n-title]');
        titleElements.forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            element.title = this.t(key);
        });
    }

    getCurrentLanguage() {
        return this.currentLanguage;
    }

    getSupportedLanguages() {
        return this.supportedLanguages;
    }

    getLanguageLabel(language) {
        const labels = {
            'zh-CN': '中文',
            'en-US': 'English'
        };
        return labels[language] || language;
    }
}

// 创建全局i18n实例
window.i18n = new I18n();