import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
  KeyboardSensor,
  MouseSensor,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable';
import { 
  ChevronRight, 
  ChevronDown, 
  Plus, 
  Trash2, 
  Edit2, 
  MoreVertical,
  Check,
  X,
  GripVertical,
  FileText,
  Copy,
  Scissors,
  Clipboard,
} from 'lucide-react';
import { OutlineNode } from '@/types/models';
import { cn } from '@/lib/utils';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface OutlineEditorProps {
  outline: OutlineNode[];
  onOutlineChange: (outline: OutlineNode[]) => void;
  selectedNodeId?: string;
  onNodeSelect?: (nodeId: string) => void;
  className?: string;
}

interface TreeNodeProps {
  node: OutlineNode;
  level: number;
  onUpdate: (node: OutlineNode) => void;
  onDelete: (nodeId: string) => void;
  onAddChild: (parentId: string) => void;
  selected?: boolean;
  onSelect?: (nodeId: string) => void;
  onDuplicate: (node: OutlineNode) => void;
  onCut: (nodeId: string) => void;
  onPaste: (nodeId: string) => void;
  clipboard?: OutlineNode | null;
}

// TreeNode component with drag and drop
const TreeNode: React.FC<TreeNodeProps> = ({
  node,
  level,
  onUpdate,
  onDelete,
  onAddChild,
  selected,
  onSelect,
  onDuplicate,
  onCut,
  onPaste,
  clipboard,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(node.title);
  const [showContextMenu, setShowContextMenu] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: node.id,
    data: { node, level },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleEdit = () => {
    setIsEditing(true);
    setShowContextMenu(false);
  };

  const handleSave = () => {
    if (editValue.trim()) {
      onUpdate({ ...node, title: editValue.trim() });
    } else {
      setEditValue(node.title);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditValue(node.title);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  const hasChildren = node.children && node.children.length > 0;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group relative',
        isDragging && 'z-50'
      )}
    >
      <div
        className={cn(
          'flex items-center gap-2 px-2 py-1.5 rounded-md transition-all',
          'hover:bg-gray-100 dark:hover:bg-gray-800',
          selected && 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-500',
          isDragging && 'bg-gray-50 dark:bg-gray-800'
        )}
        style={{ paddingLeft: `${level * 24 + 8}px` }}
        onClick={() => onSelect?.(node.id)}
      >
        {/* Drag Handle */}
        <div
          {...attributes}
          {...listeners}
          className="opacity-0 group-hover:opacity-100 cursor-grab active:cursor-grabbing p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
        >
          <GripVertical className="w-4 h-4 text-gray-400" />
        </div>

        {/* Expand/Collapse Icon */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
          className={cn(
            'p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700',
            !hasChildren && 'invisible'
          )}
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>

        {/* Node Icon */}
        <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />

        {/* Title */}
        {isEditing ? (
          <div className="flex items-center gap-1 flex-1">
            <input
              ref={inputRef}
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleSave}
              className="flex-1 px-2 py-0.5 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSave();
              }}
              className="p-1 hover:bg-green-100 rounded"
            >
              <Check className="w-3 h-3 text-green-600" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCancel();
              }}
              className="p-1 hover:bg-red-100 rounded"
            >
              <X className="w-3 h-3 text-red-600" />
            </button>
          </div>
        ) : (
          <span className="flex-1 text-sm select-none truncate">
            {node.title}
          </span>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleEdit();
            }}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            title="Edit"
          >
            <Edit2 className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAddChild(node.id);
            }}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            title="Add Child"
          >
            <Plus className="w-3 h-3" />
          </button>
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowContextMenu(!showContextMenu);
              }}
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            >
              <MoreVertical className="w-3 h-3" />
            </button>
            
            {/* Context Menu */}
            {showContextMenu && (
              <div className="absolute right-0 top-6 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 z-50">
                <button
                  onClick={() => {
                    onDuplicate(node);
                    setShowContextMenu(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  <Copy className="w-3 h-3" /> Duplicate
                </button>
                <button
                  onClick={() => {
                    onCut(node.id);
                    setShowContextMenu(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  <Scissors className="w-3 h-3" /> Cut
                </button>
                <button
                  onClick={() => {
                    onPaste(node.id);
                    setShowContextMenu(false);
                  }}
                  disabled={!clipboard}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Clipboard className="w-3 h-3" /> Paste
                </button>
                <hr className="my-1 border-gray-200 dark:border-gray-700" />
                <button
                  onClick={() => {
                    onDelete(node.id);
                    setShowContextMenu(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 flex items-center gap-2"
                >
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Children */}
      {isExpanded && hasChildren && (
        <div>
          {node.children!.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              level={level + 1}
              onUpdate={onUpdate}
              onDelete={onDelete}
              onAddChild={onAddChild}
              selected={selected}
              onSelect={onSelect}
              onDuplicate={onDuplicate}
              onCut={onCut}
              onPaste={onPaste}
              clipboard={clipboard}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const OutlineEditor: React.FC<OutlineEditorProps> = ({
  outline,
  onOutlineChange,
  selectedNodeId,
  onNodeSelect,
  className,
}) => {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [clipboard, setClipboard] = useState<OutlineNode | null>(null);
  
  const sensors = useSensors(
    useSensor(MouseSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Generate unique ID
  const generateId = () => `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  // Find node by ID in the tree
  const findNode = (nodes: OutlineNode[], id: string): OutlineNode | null => {
    for (const node of nodes) {
      if (node.id === id) return node;
      if (node.children) {
        const found = findNode(node.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  // Update node in tree
  const updateNode = (node: OutlineNode) => {
    const updateInTree = (nodes: OutlineNode[]): OutlineNode[] => {
      return nodes.map((n) => {
        if (n.id === node.id) {
          return node;
        }
        if (n.children) {
          return { ...n, children: updateInTree(n.children) };
        }
        return n;
      });
    };
    onOutlineChange(updateInTree(outline));
  };

  // Delete node from tree
  const deleteNode = (nodeId: string) => {
    const removeFromTree = (nodes: OutlineNode[]): OutlineNode[] => {
      return nodes
        .filter((n) => n.id !== nodeId)
        .map((n) => {
          if (n.children) {
            return { ...n, children: removeFromTree(n.children) };
          }
          return n;
        });
    };
    onOutlineChange(removeFromTree(outline));
  };

  // Add child node
  const addChildNode = (parentId: string) => {
    const newNode: OutlineNode = {
      id: generateId(),
      title: 'New Section',
      level: 0,
      children: [],
    };

    if (parentId === 'root') {
      onOutlineChange([...outline, newNode]);
    } else {
      const addToTree = (nodes: OutlineNode[]): OutlineNode[] => {
        return nodes.map((n) => {
          if (n.id === parentId) {
            return {
              ...n,
              children: [...(n.children || []), newNode],
            };
          }
          if (n.children) {
            return { ...n, children: addToTree(n.children) };
          }
          return n;
        });
      };
      onOutlineChange(addToTree(outline));
    }
  };

  // Duplicate node
  const duplicateNode = (node: OutlineNode) => {
    const duplicate = (n: OutlineNode): OutlineNode => ({
      ...n,
      id: generateId(),
      title: `${n.title} (Copy)`,
      children: n.children ? n.children.map(duplicate) : [],
    });

    const duplicatedNode = duplicate(node);
    
    const addAfter = (nodes: OutlineNode[]): OutlineNode[] => {
      const result: OutlineNode[] = [];
      for (const n of nodes) {
        result.push(n);
        if (n.id === node.id) {
          result.push(duplicatedNode);
        }
        if (n.children) {
          n.children = addAfter(n.children);
        }
      }
      return result;
    };
    
    onOutlineChange(addAfter(outline));
  };

  // Cut node (copy to clipboard and mark for deletion)
  const cutNode = (nodeId: string) => {
    const node = findNode(outline, nodeId);
    if (node) {
      setClipboard(node);
      // Optionally add visual indicator that node is cut
    }
  };

  // Paste node
  const pasteNode = (targetId: string) => {
    if (!clipboard) return;

    // Remove from original position if it was cut
    const removeFromTree = (nodes: OutlineNode[]): OutlineNode[] => {
      return nodes
        .filter((n) => n.id !== clipboard.id)
        .map((n) => {
          if (n.children) {
            return { ...n, children: removeFromTree(n.children) };
          }
          return n;
        });
    };

    // Add to new position
    const pastedNode = {
      ...clipboard,
      id: generateId(),
    };

    const addToTree = (nodes: OutlineNode[]): OutlineNode[] => {
      return nodes.map((n) => {
        if (n.id === targetId) {
          return {
            ...n,
            children: [...(n.children || []), pastedNode],
          };
        }
        if (n.children) {
          return { ...n, children: addToTree(n.children) };
        }
        return n;
      });
    };

    const cleanedOutline = removeFromTree(outline);
    onOutlineChange(addToTree(cleanedOutline));
    setClipboard(null);
  };

  // Handle drag start
  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over && active.id !== over.id) {
      const oldIndex = outline.findIndex((item) => item.id === active.id);
      const newIndex = outline.findIndex((item) => item.id === over.id);
      
      if (oldIndex !== -1 && newIndex !== -1) {
        onOutlineChange(arrayMove(outline, oldIndex, newIndex));
      }
    }
    
    setActiveId(null);
  };

  // Get all node IDs for sortable context
  const getAllNodeIds = (nodes: OutlineNode[]): string[] => {
    const ids: string[] = [];
    const traverse = (nodeList: OutlineNode[]) => {
      for (const node of nodeList) {
        ids.push(node.id);
        if (node.children) {
          traverse(node.children);
        }
      }
    };
    traverse(nodes);
    return ids;
  };

  const nodeIds = getAllNodeIds(outline);

  return (
    <div className={cn('bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800', className)}>
      <div className="p-4 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">PPT Outline</h3>
          <button
            onClick={() => addChildNode('root')}
            className="px-3 py-1.5 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors flex items-center gap-1"
          >
            <Plus className="w-4 h-4" />
            Add Section
          </button>
        </div>
      </div>
      
      <div className="p-4 max-h-[600px] overflow-y-auto">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={nodeIds}
            strategy={verticalListSortingStrategy}
          >
            {outline.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No outline created yet.</p>
                <p className="text-sm mt-1">Click "Add Section" to start building your presentation.</p>
              </div>
            ) : (
              outline.map((node) => (
                <TreeNode
                  key={node.id}
                  node={node}
                  level={0}
                  onUpdate={updateNode}
                  onDelete={deleteNode}
                  onAddChild={addChildNode}
                  selected={selectedNodeId === node.id}
                  onSelect={onNodeSelect}
                  onDuplicate={duplicateNode}
                  onCut={cutNode}
                  onPaste={pasteNode}
                  clipboard={clipboard}
                />
              ))
            )}
          </SortableContext>
          
          <DragOverlay>
            {activeId ? (
              <div className="bg-white dark:bg-gray-800 rounded shadow-lg p-2 opacity-80">
                {findNode(outline, activeId)?.title}
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>
    </div>
  );
};