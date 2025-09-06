import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useProjectStore } from '@/store/projectStore';
import { OutlineNode } from '@/types/models';
import {
  ChevronRight,
  ChevronDown,
  Plus,
  Trash2,
  Edit3,
  GripVertical,
  FileText,
  Save,
  X,
  Copy,
  Clipboard,
  MoreVertical,
} from 'lucide-react';

interface OutlineEditorProps {
  projectId: string;
  onSave?: (outline: OutlineNode[]) => void;
  onGenerate?: () => void;
  readOnly?: boolean;
}

interface DragState {
  draggedNode: OutlineNode | null;
  draggedParentId: string | null;
  draggedIndex: number;
  dropTargetId: string | null;
  dropPosition: 'before' | 'after' | 'inside' | null;
}

const OutlineEditor: React.FC<OutlineEditorProps> = ({
  projectId,
  onSave,
  onGenerate,
  readOnly = false,
}) => {
  const { getProject, updateProjectOutline } = useProjectStore();
  const project = getProject(projectId);
  
  const [outline, setOutline] = useState<OutlineNode[]>(
    project?.outline || []
  );
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(
    new Set()
  );
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [dragState, setDragState] = useState<DragState>({
    draggedNode: null,
    draggedParentId: null,
    draggedIndex: 0,
    dropTargetId: null,
    dropPosition: null,
  });
  
  const dragCounter = useRef(0);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    // Expand first level by default
    const firstLevelIds = outline.map(node => node.id);
    setExpandedNodes(new Set(firstLevelIds));
  }, []);

  // Generate unique ID
  const generateId = () => {
    return `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  };

  // Toggle node expansion
  const toggleExpand = (nodeId: string) => {
    setExpandedNodes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return newSet;
    });
  };

  // Find node by ID
  const findNode = (
    nodes: OutlineNode[],
    id: string
  ): { node: OutlineNode; parent: OutlineNode | null; index: number } | null => {
    for (let i = 0; i < nodes.length; i++) {
      if (nodes[i].id === id) {
        return { node: nodes[i], parent: null, index: i };
      }
      if (nodes[i].children && nodes[i].children.length > 0) {
        const found = findNodeInChildren(nodes[i].children, id, nodes[i]);
        if (found) return found;
      }
    }
    return null;
  };

  const findNodeInChildren = (
    children: OutlineNode[],
    id: string,
    parent: OutlineNode
  ): { node: OutlineNode; parent: OutlineNode; index: number } | null => {
    for (let i = 0; i < children.length; i++) {
      if (children[i].id === id) {
        return { node: children[i], parent, index: i };
      }
      if (children[i].children && children[i].children.length > 0) {
        const found = findNodeInChildren(children[i].children, id, children[i]);
        if (found) return found;
      }
    }
    return null;
  };

  // Add new node
  const addNode = (parentId?: string) => {
    const newNode: OutlineNode = {
      id: generateId(),
      title: '新章节',
      content: '',
      level: parentId ? 2 : 1,
      children: [],
    };

    setOutline(prev => {
      if (!parentId) {
        return [...prev, newNode];
      }
      
      return updateNodeInTree(prev, parentId, node => ({
        ...node,
        children: [...(node.children || []), newNode],
      }));
    });
    
    setHasChanges(true);
    setEditingNodeId(newNode.id);
    setEditingContent('新章节');
    
    if (parentId) {
      setExpandedNodes(prev => new Set([...prev, parentId]));
    }
  };

  // Update node in tree
  const updateNodeInTree = (
    nodes: OutlineNode[],
    nodeId: string,
    updater: (node: OutlineNode) => OutlineNode
  ): OutlineNode[] => {
    return nodes.map(node => {
      if (node.id === nodeId) {
        return updater(node);
      }
      if (node.children && node.children.length > 0) {
        return {
          ...node,
          children: updateNodeInTree(node.children, nodeId, updater),
        };
      }
      return node;
    });
  };

  // Delete node
  const deleteNode = (nodeId: string) => {
    setOutline(prev => deleteNodeFromTree(prev, nodeId));
    setHasChanges(true);
  };

  const deleteNodeFromTree = (
    nodes: OutlineNode[],
    nodeId: string
  ): OutlineNode[] => {
    return nodes
      .filter(node => node.id !== nodeId)
      .map(node => ({
        ...node,
        children: node.children
          ? deleteNodeFromTree(node.children, nodeId)
          : [],
      }));
  };

  // Start editing
  const startEdit = (node: OutlineNode) => {
    setEditingNodeId(node.id);
    setEditingContent(node.title);
  };

  // Save edit
  const saveEdit = () => {
    if (editingNodeId && editingContent.trim()) {
      setOutline(prev =>
        updateNodeInTree(prev, editingNodeId, node => ({
          ...node,
          title: editingContent.trim(),
        }))
      );
      setHasChanges(true);
    }
    setEditingNodeId(null);
    setEditingContent('');
  };

  // Cancel edit
  const cancelEdit = () => {
    setEditingNodeId(null);
    setEditingContent('');
  };

  // Duplicate node
  const duplicateNode = (nodeId: string) => {
    const found = findNode(outline, nodeId);
    if (found) {
      const newNode: OutlineNode = {
        ...found.node,
        id: generateId(),
        title: `${found.node.title} (副本)`,
        children: [],
      };
      
      if (found.parent) {
        setOutline(prev =>
          updateNodeInTree(prev, found.parent!.id, parent => ({
            ...parent,
            children: [
              ...parent.children.slice(0, found.index + 1),
              newNode,
              ...parent.children.slice(found.index + 1),
            ],
          }))
        );
      } else {
        setOutline(prev => [
          ...prev.slice(0, found.index + 1),
          newNode,
          ...prev.slice(found.index + 1),
        ]);
      }
      setHasChanges(true);
    }
  };

  // Handle drag start
  const handleDragStart = (
    e: React.DragEvent,
    node: OutlineNode,
    parentId: string | null,
    index: number
  ) => {
    e.dataTransfer.effectAllowed = 'move';
    setDragState({
      draggedNode: node,
      draggedParentId: parentId,
      draggedIndex: index,
      dropTargetId: null,
      dropPosition: null,
    });
  };

  // Handle drag over
  const handleDragOver = (e: React.DragEvent, targetNode: OutlineNode) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const y = e.clientY - rect.top;
    const height = rect.height;
    
    let position: 'before' | 'after' | 'inside';
    if (y < height * 0.25) {
      position = 'before';
    } else if (y > height * 0.75) {
      position = 'after';
    } else {
      position = 'inside';
    }
    
    setDragState(prev => ({
      ...prev,
      dropTargetId: targetNode.id,
      dropPosition: position,
    }));
  };

  // Handle drop
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    
    const { draggedNode, dropTargetId, dropPosition } = dragState;
    
    if (!draggedNode || !dropTargetId || !dropPosition) return;
    
    // Don't allow dropping on itself or its children
    if (isDescendant(draggedNode, dropTargetId)) return;
    
    setOutline(prev => {
      // Remove dragged node from tree
      let newOutline = deleteNodeFromTree(prev, draggedNode.id);
      
      // Insert at new position
      if (dropPosition === 'inside') {
        newOutline = updateNodeInTree(newOutline, dropTargetId, target => ({
          ...target,
          children: [...(target.children || []), draggedNode],
        }));
        setExpandedNodes(expanded => new Set([...expanded, dropTargetId]));
      } else {
        const targetFound = findNode(newOutline, dropTargetId);
        if (targetFound) {
          if (targetFound.parent) {
            const insertIndex =
              targetFound.index + (dropPosition === 'after' ? 1 : 0);
            newOutline = updateNodeInTree(
              newOutline,
              targetFound.parent.id,
              parent => ({
                ...parent,
                children: [
                  ...parent.children.slice(0, insertIndex),
                  draggedNode,
                  ...parent.children.slice(insertIndex),
                ],
              })
            );
          } else {
            const insertIndex =
              targetFound.index + (dropPosition === 'after' ? 1 : 0);
            newOutline = [
              ...newOutline.slice(0, insertIndex),
              draggedNode,
              ...newOutline.slice(insertIndex),
            ];
          }
        }
      }
      
      return newOutline;
    });
    
    setHasChanges(true);
    setDragState({
      draggedNode: null,
      draggedParentId: null,
      draggedIndex: 0,
      dropTargetId: null,
      dropPosition: null,
    });
  };

  // Check if target is descendant of node
  const isDescendant = (node: OutlineNode, targetId: string): boolean => {
    if (node.id === targetId) return true;
    if (node.children) {
      for (const child of node.children) {
        if (isDescendant(child, targetId)) return true;
      }
    }
    return false;
  };

  // Save outline
  const handleSave = () => {
    updateProjectOutline(projectId, outline);
    setHasChanges(false);
    onSave?.(outline);
  };

  // Render outline node
  const renderNode = (
    node: OutlineNode,
    index: number,
    parentId: string | null = null,
    depth: number = 0
  ) => {
    const isExpanded = expandedNodes.has(node.id);
    const hasChildren = node.children && node.children.length > 0;
    const isEditing = editingNodeId === node.id;
    const isSelected = selectedNodeId === node.id;
    const isDragTarget = dragState.dropTargetId === node.id;

    return (
      <div key={node.id} className="outline-node">
        <div
          className={`
            flex items-center gap-2 px-2 py-1.5 rounded-lg
            hover:bg-secondary-100 dark:hover:bg-secondary-700
            transition-colors cursor-pointer group
            ${isSelected ? 'bg-primary-50 dark:bg-primary-900/20' : ''}
            ${isDragTarget ? 'bg-primary-100 dark:bg-primary-800/30' : ''}
            ${
              isDragTarget && dragState.dropPosition === 'before'
                ? 'border-t-2 border-primary-500'
                : ''
            }
            ${
              isDragTarget && dragState.dropPosition === 'after'
                ? 'border-b-2 border-primary-500'
                : ''
            }
          `}
          style={{ paddingLeft: `${depth * 24 + 8}px` }}
          onClick={() => setSelectedNodeId(node.id)}
          draggable={!readOnly && !isEditing}
          onDragStart={e => handleDragStart(e, node, parentId, index)}
          onDragOver={e => handleDragOver(e, node)}
          onDrop={handleDrop}
          onDragEnd={() =>
            setDragState(prev => ({ ...prev, dropTargetId: null }))
          }
        >
          {!readOnly && (
            <GripVertical className="w-4 h-4 text-secondary-400 opacity-0 group-hover:opacity-100 cursor-move" />
          )}
          
          <button
            onClick={e => {
              e.stopPropagation();
              if (hasChildren) toggleExpand(node.id);
            }}
            className={`p-0.5 ${!hasChildren ? 'invisible' : ''}`}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-secondary-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-secondary-500" />
            )}
          </button>

          <FileText className="w-4 h-4 text-secondary-400" />

          {isEditing ? (
            <input
              type="text"
              value={editingContent}
              onChange={e => setEditingContent(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') saveEdit();
                if (e.key === 'Escape') cancelEdit();
              }}
              onBlur={saveEdit}
              className="flex-1 px-2 py-0.5 bg-white dark:bg-secondary-800 border border-primary-500 rounded focus:outline-none"
              autoFocus
            />
          ) : (
            <span className="flex-1 text-sm text-secondary-800 dark:text-secondary-200">
              {node.title}
            </span>
          )}

          {!readOnly && !isEditing && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
              <button
                onClick={e => {
                  e.stopPropagation();
                  startEdit(node);
                }}
                className="p-1 hover:bg-secondary-200 dark:hover:bg-secondary-600 rounded"
                title="编辑"
              >
                <Edit3 className="w-3.5 h-3.5 text-secondary-600 dark:text-secondary-400" />
              </button>
              
              <button
                onClick={e => {
                  e.stopPropagation();
                  addNode(node.id);
                }}
                className="p-1 hover:bg-secondary-200 dark:hover:bg-secondary-600 rounded"
                title="添加子节点"
              >
                <Plus className="w-3.5 h-3.5 text-secondary-600 dark:text-secondary-400" />
              </button>
              
              <button
                onClick={e => {
                  e.stopPropagation();
                  duplicateNode(node.id);
                }}
                className="p-1 hover:bg-secondary-200 dark:hover:bg-secondary-600 rounded"
                title="复制"
              >
                <Copy className="w-3.5 h-3.5 text-secondary-600 dark:text-secondary-400" />
              </button>
              
              <button
                onClick={e => {
                  e.stopPropagation();
                  if (window.confirm('确定要删除此节点及其所有子节点吗？')) {
                    deleteNode(node.id);
                  }
                }}
                className="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded"
                title="删除"
              >
                <Trash2 className="w-3.5 h-3.5 text-red-500" />
              </button>
            </div>
          )}
        </div>

        {isExpanded && hasChildren && (
          <div className="ml-4">
            {node.children.map((child, childIndex) =>
              renderNode(child, childIndex, node.id, depth + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-secondary-800 rounded-lg shadow-sm">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-secondary-200 dark:border-secondary-700">
        <h3 className="text-lg font-semibold text-secondary-900 dark:text-white">
          大纲编辑器
        </h3>
        
        <div className="flex items-center gap-2">
          {!readOnly && (
            <>
              <button
                onClick={() => addNode()}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                <Plus className="w-4 h-4" />
                添加章节
              </button>
              
              {hasChanges && (
                <button
                  onClick={handleSave}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                >
                  <Save className="w-4 h-4" />
                  保存
                </button>
              )}
            </>
          )}
          
          {onGenerate && outline.length > 0 && (
            <button
              onClick={onGenerate}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
            >
              生成PPT
            </button>
          )}
        </div>
      </div>

      {/* Outline tree */}
      <div className="flex-1 overflow-y-auto p-4">
        {outline.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-secondary-400">
            <FileText className="w-12 h-12 mb-2" />
            <p>暂无大纲内容</p>
            {!readOnly && (
              <button
                onClick={() => addNode()}
                className="mt-4 text-primary-500 hover:text-primary-600"
              >
                添加第一个章节
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-1">
            {outline.map((node, index) => renderNode(node, index))}
          </div>
        )}
      </div>

      {/* Status bar */}
      {outline.length > 0 && (
        <div className="px-4 py-2 border-t border-secondary-200 dark:border-secondary-700">
          <div className="flex items-center justify-between text-xs text-secondary-500">
            <span>
              {outline.length} 个章节
              {hasChanges && (
                <span className="ml-2 text-amber-500">• 有未保存的更改</span>
              )}
            </span>
            <span>
              可拖拽节点进行排序
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default OutlineEditor;