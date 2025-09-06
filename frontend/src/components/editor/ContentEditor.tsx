import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Bold,
  Italic,
  Underline,
  List,
  ListOrdered,
  Link2,
  Image,
  Code,
  Quote,
  Heading1,
  Heading2,
  Heading3,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Undo,
  Redo,
  Copy,
  Clipboard,
  Save,
  Eye,
  Edit,
  FileText,
} from 'lucide-react';

interface ContentEditorProps {
  content: string;
  onChange: (content: string) => void;
  onSave?: (content: string) => void;
  placeholder?: string;
  maxLength?: number;
  readOnly?: boolean;
  showToolbar?: boolean;
  height?: string;
  autoSave?: boolean;
  autoSaveDelay?: number;
}

interface ToolbarButton {
  icon: React.FC<{ className?: string }>;
  label: string;
  action: () => void;
  shortcut?: string;
  active?: boolean;
  divider?: boolean;
}

const ContentEditor: React.FC<ContentEditorProps> = ({
  content,
  onChange,
  onSave,
  placeholder = '请输入内容...',
  maxLength = 10000,
  readOnly = false,
  showToolbar = true,
  height = '400px',
  autoSave = false,
  autoSaveDelay = 2000,
}) => {
  const [editorContent, setEditorContent] = useState(content);
  const [isPreview, setIsPreview] = useState(false);
  const [selectedText, setSelectedText] = useState('');
  const [cursorPosition, setCursorPosition] = useState(0);
  const [history, setHistory] = useState<string[]>([content]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [wordCount, setWordCount] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Update word count
  useEffect(() => {
    const words = editorContent.trim().split(/\s+/).filter(word => word.length > 0);
    setWordCount(words.length);
  }, [editorContent]);

  // Auto-save functionality
  useEffect(() => {
    if (autoSave && onSave) {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
      
      autoSaveTimerRef.current = setTimeout(() => {
        handleSave();
      }, autoSaveDelay);
    }
    
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [editorContent, autoSave, autoSaveDelay]);

  // Handle content change
  const handleContentChange = (value: string) => {
    if (value.length <= maxLength) {
      setEditorContent(value);
      onChange(value);
      
      // Add to history for undo/redo
      const newHistory = history.slice(0, historyIndex + 1);
      newHistory.push(value);
      setHistory(newHistory);
      setHistoryIndex(newHistory.length - 1);
    }
  };

  // Get selected text
  const updateSelection = () => {
    if (textareaRef.current) {
      const start = textareaRef.current.selectionStart;
      const end = textareaRef.current.selectionEnd;
      const text = textareaRef.current.value.substring(start, end);
      setSelectedText(text);
      setCursorPosition(start);
    }
  };

  // Insert text at cursor
  const insertAtCursor = (textBefore: string, textAfter: string = '') => {
    if (textareaRef.current) {
      const start = textareaRef.current.selectionStart;
      const end = textareaRef.current.selectionEnd;
      const text = textareaRef.current.value;
      const selected = text.substring(start, end);
      
      const newText = 
        text.substring(0, start) + 
        textBefore + 
        selected + 
        textAfter + 
        text.substring(end);
      
      handleContentChange(newText);
      
      // Restore cursor position
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.focus();
          const newPosition = start + textBefore.length + selected.length;
          textareaRef.current.setSelectionRange(newPosition, newPosition);
        }
      }, 0);
    }
  };

  // Wrap selected text
  const wrapSelection = (wrapper: string) => {
    if (textareaRef.current) {
      const start = textareaRef.current.selectionStart;
      const end = textareaRef.current.selectionEnd;
      const text = textareaRef.current.value;
      const selected = text.substring(start, end) || '文本';
      
      const newText = 
        text.substring(0, start) + 
        wrapper + 
        selected + 
        wrapper + 
        text.substring(end);
      
      handleContentChange(newText);
      
      // Select the wrapped text
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.focus();
          textareaRef.current.setSelectionRange(
            start + wrapper.length,
            start + wrapper.length + selected.length
          );
        }
      }, 0);
    }
  };

  // Format actions
  const formatBold = () => wrapSelection('**');
  const formatItalic = () => wrapSelection('*');
  const formatUnderline = () => wrapSelection('<u>', '</u>');
  const formatCode = () => wrapSelection('`');
  const formatQuote = () => insertAtCursor('> ');
  const formatH1 = () => insertAtCursor('# ');
  const formatH2 = () => insertAtCursor('## ');
  const formatH3 = () => insertAtCursor('### ');
  const formatBulletList = () => insertAtCursor('- ');
  const formatNumberedList = () => insertAtCursor('1. ');
  
  const formatLink = () => {
    const url = prompt('请输入链接地址:');
    if (url) {
      if (selectedText) {
        insertAtCursor(`[${selectedText}](${url})`);
      } else {
        insertAtCursor(`[链接文本](${url})`);
      }
    }
  };
  
  const formatImage = () => {
    const url = prompt('请输入图片地址:');
    if (url) {
      insertAtCursor(`![图片描述](${url})\n`);
    }
  };

  // Undo/Redo
  const undo = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      setHistoryIndex(newIndex);
      setEditorContent(history[newIndex]);
      onChange(history[newIndex]);
    }
  };

  const redo = () => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      setHistoryIndex(newIndex);
      setEditorContent(history[newIndex]);
      onChange(history[newIndex]);
    }
  };

  // Copy to clipboard
  const copyToClipboard = () => {
    if (selectedText) {
      navigator.clipboard.writeText(selectedText);
    } else {
      navigator.clipboard.writeText(editorContent);
    }
  };

  // Save content
  const handleSave = async () => {
    if (onSave) {
      setIsSaving(true);
      await onSave(editorContent);
      setTimeout(() => setIsSaving(false), 1000);
    }
  };

  // Toolbar buttons configuration
  const toolbarButtons: ToolbarButton[] = [
    { icon: Undo, label: '撤销', action: undo, shortcut: 'Ctrl+Z' },
    { icon: Redo, label: '重做', action: redo, shortcut: 'Ctrl+Y' },
    { divider: true, icon: Bold, label: '', action: () => {} },
    { icon: Bold, label: '粗体', action: formatBold, shortcut: 'Ctrl+B' },
    { icon: Italic, label: '斜体', action: formatItalic, shortcut: 'Ctrl+I' },
    { icon: Underline, label: '下划线', action: formatUnderline, shortcut: 'Ctrl+U' },
    { icon: Code, label: '代码', action: formatCode, shortcut: 'Ctrl+`' },
    { divider: true, icon: Bold, label: '', action: () => {} },
    { icon: Heading1, label: '标题1', action: formatH1 },
    { icon: Heading2, label: '标题2', action: formatH2 },
    { icon: Heading3, label: '标题3', action: formatH3 },
    { divider: true, icon: Bold, label: '', action: () => {} },
    { icon: List, label: '无序列表', action: formatBulletList },
    { icon: ListOrdered, label: '有序列表', action: formatNumberedList },
    { icon: Quote, label: '引用', action: formatQuote },
    { divider: true, icon: Bold, label: '', action: () => {} },
    { icon: Link2, label: '链接', action: formatLink },
    { icon: Image, label: '图片', action: formatImage },
    { divider: true, icon: Bold, label: '', action: () => {} },
    { icon: Copy, label: '复制', action: copyToClipboard, shortcut: 'Ctrl+C' },
  ];

  // Render markdown preview
  const renderMarkdown = (text: string) => {
    // Simple markdown rendering (can be enhanced with a markdown library)
    let html = text
      // Headers
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mb-2">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mb-3">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mb-4">$1</h1>')
      // Bold
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // Code
      .replace(/`(.+?)`/g, '<code class="px-1 py-0.5 bg-secondary-100 dark:bg-secondary-700 rounded">$1</code>')
      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary-500 hover:underline">$1</a>')
      // Images
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="max-w-full rounded-lg my-2" />')
      // Lists
      .replace(/^\- (.+)$/gim, '<li class="ml-4">$1</li>')
      .replace(/^\d+\. (.+)$/gim, '<li class="ml-4 list-decimal">$1</li>')
      // Quotes
      .replace(/^> (.+)$/gim, '<blockquote class="pl-4 border-l-4 border-secondary-300 dark:border-secondary-600 italic">$1</blockquote>')
      // Line breaks
      .replace(/\n/g, '<br />');
    
    return { __html: html };
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-secondary-800 rounded-lg shadow-sm">
      {/* Toolbar */}
      {showToolbar && !readOnly && (
        <div className="flex items-center justify-between px-3 py-2 border-b border-secondary-200 dark:border-secondary-700">
          <div className="flex items-center gap-1">
            {toolbarButtons.map((button, index) =>
              button.divider ? (
                <div
                  key={index}
                  className="w-px h-6 bg-secondary-300 dark:bg-secondary-600 mx-1"
                />
              ) : (
                <button
                  key={index}
                  onClick={button.action}
                  className="p-1.5 rounded hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors group relative"
                  title={`${button.label}${button.shortcut ? ` (${button.shortcut})` : ''}`}
                >
                  <button.icon className="w-4 h-4 text-secondary-600 dark:text-secondary-400" />
                  <span className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1 px-2 py-1 text-xs bg-secondary-800 dark:bg-secondary-900 text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    {button.label}
                    {button.shortcut && (
                      <span className="ml-1 text-secondary-400">
                        {button.shortcut}
                      </span>
                    )}
                  </span>
                </button>
              )
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPreview(!isPreview)}
              className="flex items-center gap-1 px-2 py-1 text-sm rounded hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
            >
              {isPreview ? (
                <>
                  <Edit className="w-4 h-4" />
                  编辑
                </>
              ) : (
                <>
                  <Eye className="w-4 h-4" />
                  预览
                </>
              )}
            </button>
            
            {onSave && (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-1 px-3 py-1 text-sm bg-primary-500 text-white rounded hover:bg-primary-600 transition-colors disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {isSaving ? '保存中...' : '保存'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Editor/Preview */}
      <div className="flex-1 relative" style={{ minHeight: height }}>
        {isPreview || readOnly ? (
          <div
            className="h-full p-4 overflow-y-auto prose prose-sm max-w-none dark:prose-invert"
            dangerouslySetInnerHTML={renderMarkdown(editorContent)}
          />
        ) : (
          <textarea
            ref={textareaRef}
            value={editorContent}
            onChange={e => handleContentChange(e.target.value)}
            onSelect={updateSelection}
            onKeyUp={updateSelection}
            onMouseUp={updateSelection}
            placeholder={placeholder}
            disabled={readOnly}
            className="w-full h-full p-4 resize-none bg-transparent text-secondary-900 dark:text-secondary-100 placeholder-secondary-400 focus:outline-none"
            style={{ minHeight: height }}
          />
        )}
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between px-3 py-2 border-t border-secondary-200 dark:border-secondary-700 text-xs text-secondary-500">
        <div className="flex items-center gap-4">
          <span>{wordCount} 字</span>
          <span>{editorContent.length} / {maxLength} 字符</span>
        </div>
        
        <div className="flex items-center gap-4">
          {autoSave && (
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              自动保存已启用
            </span>
          )}
          {selectedText && (
            <span>已选择 {selectedText.length} 字符</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default ContentEditor;