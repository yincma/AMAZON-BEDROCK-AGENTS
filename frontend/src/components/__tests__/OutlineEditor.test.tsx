
import { render, screen, fireEvent, waitFor } from './test-utils';
import { OutlineEditor } from '@/components/editor/OutlineEditor';
import { mockProjectStore, createMockProject } from './test-utils';
import { OutlineNode } from '@/types/models';

// Mock window.confirm
Object.defineProperty(window, 'confirm', {
  writable: true,
  value: jest.fn(),
});

describe('OutlineEditor', () => {
  const mockOutline: OutlineNode[] = [
    {
      id: 'node-1',
      title: '引言',
      content: '项目介绍',
      level: 1,
      children: [
        {
          id: 'node-1-1',
          title: '项目背景',
          content: '背景描述',
          level: 2,
          children: []
        }
      ]
    },
    {
      id: 'node-2',
      title: '主体内容',
      content: '详细内容',
      level: 1,
      children: []
    }
  ];

  const mockProject = createMockProject({
    id: 'test-project-id',
    title: 'Test Project',
    outline: mockOutline
  });

  beforeEach(() => {
    (window.confirm as jest.Mock).mockReturnValue(false);
    mockProjectStore.getProject.mockReturnValue(mockProject);
  });

  describe('Basic Rendering', () => {
    it('renders correctly with project outline', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      expect(screen.getByText('大纲编辑器')).toBeInTheDocument();
      expect(screen.getByText('引言')).toBeInTheDocument();
      expect(screen.getByText('主体内容')).toBeInTheDocument();
      expect(screen.getByText('添加章节')).toBeInTheDocument();
    });

    it('renders empty state when no outline', () => {
      mockProjectStore.getProject.mockReturnValue({
        ...mockProject,
        outline: []
      });

      render(<OutlineEditor projectId="test-project-id" />);

      expect(screen.getByText('暂无大纲内容')).toBeInTheDocument();
      expect(screen.getByText('添加第一个章节')).toBeInTheDocument();
    });

    it('renders in read-only mode correctly', () => {
      render(<OutlineEditor projectId="test-project-id" readOnly />);

      expect(screen.getByText('引言')).toBeInTheDocument();
      expect(screen.queryByText('添加章节')).not.toBeInTheDocument();
      expect(screen.queryByTitle('编辑')).not.toBeInTheDocument();
      expect(screen.queryByTitle('删除')).not.toBeInTheDocument();
    });

    it('displays status bar with node count', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      expect(screen.getByText('2 个章节')).toBeInTheDocument();
      expect(screen.getByText('可拖拽节点进行排序')).toBeInTheDocument();
    });
  });

  describe('Node Management', () => {
    it('adds new root node when add button is clicked', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const addButton = screen.getByText('添加章节');
      fireEvent.click(addButton);

      expect(screen.getByDisplayValue('新章节')).toBeInTheDocument();
    });

    it('adds new child node when add child button is clicked', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      // Find the "引言" node and hover to show action buttons
      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      // Find and click the add child button
      const addChildButton = screen.getByTitle('添加子节点');
      fireEvent.click(addChildButton);

      expect(screen.getByDisplayValue('新章节')).toBeInTheDocument();
    });

    it('deletes node when delete button is clicked and confirmed', () => {
      (window.confirm as jest.Mock).mockReturnValue(true);

      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const deleteButton = screen.getByTitle('删除');
      fireEvent.click(deleteButton);

      expect(window.confirm).toHaveBeenCalledWith('确定要删除此节点及其所有子节点吗？');
    });

    it('does not delete node when deletion is cancelled', () => {
      (window.confirm as jest.Mock).mockReturnValue(false);

      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const deleteButton = screen.getByTitle('删除');
      fireEvent.click(deleteButton);

      expect(window.confirm).toHaveBeenCalled();
      expect(screen.getByText('引言')).toBeInTheDocument();
    });

    it('duplicates node when duplicate button is clicked', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const duplicateButton = screen.getByTitle('复制');
      fireEvent.click(duplicateButton);

      expect(screen.getByText('引言 (副本)')).toBeInTheDocument();
    });
  });

  describe('Node Editing', () => {
    it('starts editing when edit button is clicked', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const editButton = screen.getByTitle('编辑');
      fireEvent.click(editButton);

      expect(screen.getByDisplayValue('引言')).toBeInTheDocument();
    });

    it('saves edit when Enter key is pressed', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const editButton = screen.getByTitle('编辑');
      fireEvent.click(editButton);

      const input = screen.getByDisplayValue('引言');
      fireEvent.change(input, { target: { value: '新引言' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(screen.getByText('新引言')).toBeInTheDocument();
      expect(screen.queryByDisplayValue('新引言')).not.toBeInTheDocument();
    });

    it('cancels edit when Escape key is pressed', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const editButton = screen.getByTitle('编辑');
      fireEvent.click(editButton);

      const input = screen.getByDisplayValue('引言');
      fireEvent.change(input, { target: { value: '新引言' } });
      fireEvent.keyDown(input, { key: 'Escape' });

      expect(screen.getByText('引言')).toBeInTheDocument();
      expect(screen.queryByDisplayValue('新引言')).not.toBeInTheDocument();
    });

    it('saves edit when input loses focus', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const editButton = screen.getByTitle('编辑');
      fireEvent.click(editButton);

      const input = screen.getByDisplayValue('引言');
      fireEvent.change(input, { target: { value: '新引言' } });
      fireEvent.blur(input);

      expect(screen.getByText('新引言')).toBeInTheDocument();
    });

    it('does not save empty title', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const editButton = screen.getByTitle('编辑');
      fireEvent.click(editButton);

      const input = screen.getByDisplayValue('引言');
      fireEvent.change(input, { target: { value: '   ' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      // Should still show original title
      expect(screen.getByText('引言')).toBeInTheDocument();
    });
  });

  describe('Node Expansion and Collapse', () => {
    it('expands first level nodes by default', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      expect(screen.getByText('项目背景')).toBeInTheDocument();
    });

    it('toggles node expansion when chevron is clicked', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      // Find the chevron button for the "引言" node
      const introNode = screen.getByText('引言').closest('.outline-node');
      const chevronButton = introNode!.querySelector('button');

      expect(screen.getByText('项目背景')).toBeInTheDocument();

      // Click to collapse
      fireEvent.click(chevronButton!);
      expect(screen.queryByText('项目背景')).not.toBeInTheDocument();

      // Click to expand again
      fireEvent.click(chevronButton!);
      expect(screen.getByText('项目背景')).toBeInTheDocument();
    });

    it('does not show chevron for nodes without children', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const mainContentNode = screen.getByText('主体内容').closest('.outline-node');
      const chevronButton = mainContentNode!.querySelector('button');
      
      expect(chevronButton).toHaveClass('invisible');
    });
  });

  describe('Node Selection', () => {
    it('selects node when clicked', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('div[style]');
      fireEvent.click(introNode!);

      expect(introNode).toHaveClass('bg-primary-50');
    });

    it('changes selection when different node is clicked', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('div[style]');
      const mainContentNode = screen.getByText('主体内容').closest('div[style]');

      fireEvent.click(introNode!);
      expect(introNode).toHaveClass('bg-primary-50');

      fireEvent.click(mainContentNode!);
      expect(mainContentNode).toHaveClass('bg-primary-50');
      expect(introNode).not.toHaveClass('bg-primary-50');
    });
  });

  describe('Drag and Drop', () => {
    it('makes nodes draggable when not in read-only mode', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('div[style]');
      expect(introNode).toHaveAttribute('draggable', 'true');
    });

    it('does not make nodes draggable in read-only mode', () => {
      render(<OutlineEditor projectId="test-project-id" readOnly />);

      const introNode = screen.getByText('引言').closest('div[style]');
      expect(introNode).toHaveAttribute('draggable', 'false');
    });

    it('does not make editing nodes draggable', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const editButton = screen.getByTitle('编辑');
      fireEvent.click(editButton);

      const editingNode = screen.getByDisplayValue('引言').closest('div[style]');
      expect(editingNode).toHaveAttribute('draggable', 'false');
    });

    it('shows grip handle on hover', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const gripHandle = introNode!.querySelector('.cursor-move');
      expect(gripHandle).toBeInTheDocument();
    });

    it('handles drag start event', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('div[style]');
      
      const dragStartEvent = new DragEvent('dragstart', {
        bubbles: true,
        dataTransfer: new DataTransfer()
      });

      fireEvent(introNode!, dragStartEvent);

      expect(dragStartEvent.dataTransfer?.effectAllowed).toBe('move');
    });
  });

  describe('Save Functionality', () => {
    it('shows save button when there are changes', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      // Make a change by adding a node
      const addButton = screen.getByText('添加章节');
      fireEvent.click(addButton);

      expect(screen.getByText('保存')).toBeInTheDocument();
      expect(screen.getByText('• 有未保存的更改')).toBeInTheDocument();
    });

    it('saves outline when save button is clicked', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const addButton = screen.getByText('添加章节');
      fireEvent.click(addButton);

      const saveButton = screen.getByText('保存');
      fireEvent.click(saveButton);

      expect(mockProjectStore.updateProjectOutline).toHaveBeenCalledWith(
        'test-project-id',
        expect.any(Array)
      );
    });

    it('calls onSave callback when save is clicked', () => {
      const mockOnSave = jest.fn();
      render(<OutlineEditor projectId="test-project-id" onSave={mockOnSave} />);

      const addButton = screen.getByText('添加章节');
      fireEvent.click(addButton);

      const saveButton = screen.getByText('保存');
      fireEvent.click(saveButton);

      expect(mockOnSave).toHaveBeenCalledWith(expect.any(Array));
    });

    it('hides save button after saving', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const addButton = screen.getByText('添加章节');
      fireEvent.click(addButton);

      expect(screen.getByText('保存')).toBeInTheDocument();

      const saveButton = screen.getByText('保存');
      fireEvent.click(saveButton);

      expect(screen.queryByText('保存')).not.toBeInTheDocument();
      expect(screen.queryByText('• 有未保存的更改')).not.toBeInTheDocument();
    });
  });

  describe('Generate PPT Button', () => {
    it('shows generate button when onGenerate prop is provided and outline exists', () => {
      const mockOnGenerate = jest.fn();
      render(<OutlineEditor projectId="test-project-id" onGenerate={mockOnGenerate} />);

      expect(screen.getByText('生成PPT')).toBeInTheDocument();
    });

    it('does not show generate button when no outline exists', () => {
      mockProjectStore.getProject.mockReturnValue({
        ...mockProject,
        outline: []
      });

      const mockOnGenerate = jest.fn();
      render(<OutlineEditor projectId="test-project-id" onGenerate={mockOnGenerate} />);

      expect(screen.queryByText('生成PPT')).not.toBeInTheDocument();
    });

    it('calls onGenerate when generate button is clicked', () => {
      const mockOnGenerate = jest.fn();
      render(<OutlineEditor projectId="test-project-id" onGenerate={mockOnGenerate} />);

      const generateButton = screen.getByText('生成PPT');
      fireEvent.click(generateButton);

      expect(mockOnGenerate).toHaveBeenCalledTimes(1);
    });

    it('does not show generate button when onGenerate is not provided', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      expect(screen.queryByText('生成PPT')).not.toBeInTheDocument();
    });
  });

  describe('Keyboard Navigation', () => {
    it('handles Enter key during editing', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const editButton = screen.getByTitle('编辑');
      fireEvent.click(editButton);

      const input = screen.getByDisplayValue('引言');
      fireEvent.change(input, { target: { value: '新标题' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(screen.getByText('新标题')).toBeInTheDocument();
    });

    it('handles Escape key during editing', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const editButton = screen.getByTitle('编辑');
      fireEvent.click(editButton);

      const input = screen.getByDisplayValue('引言');
      fireEvent.change(input, { target: { value: '新标题' } });
      fireEvent.keyDown(input, { key: 'Escape' });

      expect(screen.getByText('引言')).toBeInTheDocument();
      expect(screen.queryByDisplayValue('新标题')).not.toBeInTheDocument();
    });
  });

  describe('Empty State Actions', () => {
    it('adds first node when "添加第一个章节" is clicked', () => {
      mockProjectStore.getProject.mockReturnValue({
        ...mockProject,
        outline: []
      });

      render(<OutlineEditor projectId="test-project-id" />);

      const addFirstButton = screen.getByText('添加第一个章节');
      fireEvent.click(addFirstButton);

      expect(screen.getByDisplayValue('新章节')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles missing project gracefully', () => {
      mockProjectStore.getProject.mockReturnValue(null);

      const { container } = render(<OutlineEditor projectId="nonexistent-project" />);

      expect(screen.getByText('暂无大纲内容')).toBeInTheDocument();
      expect(container).toBeInTheDocument();
    });

    it('handles project without outline', () => {
      mockProjectStore.getProject.mockReturnValue({
        ...mockProject,
        outline: undefined
      });

      render(<OutlineEditor projectId="test-project-id" />);

      expect(screen.getByText('暂无大纲内容')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('provides proper button titles for screen readers', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      expect(screen.getByTitle('编辑')).toBeInTheDocument();
      expect(screen.getByTitle('添加子节点')).toBeInTheDocument();
      expect(screen.getByTitle('复制')).toBeInTheDocument();
      expect(screen.getByTitle('删除')).toBeInTheDocument();
    });

    it('provides proper input focus during editing', () => {
      render(<OutlineEditor projectId="test-project-id" />);

      const introNode = screen.getByText('引言').closest('.outline-node');
      fireEvent.mouseEnter(introNode!);

      const editButton = screen.getByTitle('编辑');
      fireEvent.click(editButton);

      const input = screen.getByDisplayValue('引言');
      expect(input).toHaveFocus();
    });
  });
});