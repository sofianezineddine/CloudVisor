'use client';

import * as React from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
  ReactFlowProvider,
} from 'reactflow';
import dagre from 'dagre';
import { cn } from '@/lib/utils';
import { AlertTriangle, ChevronDown, ChevronUp, Info, Target, Globe } from 'lucide-react';
import 'reactflow/dist/style.css';

// ─── Types ────────────────────────────────────────────────────────────────────

export type NodeType = 'entry' | 'intermediate' | 'target';

export interface AttackPathNode {
  id: string;
  label: string;
  type: NodeType;
  metadata?: {
    resourceType?: string;
    resourceId?: string;
    provider?: string;
    severity?: string;
    [key: string]: any;
  };
}

export interface AttackPathEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  relationship?: string;
}

export interface AttackPathGraphProps {
  nodes: AttackPathNode[];
  edges: AttackPathEdge[];
  direction?: 'TB' | 'LR'; // Top-to-Bottom or Left-to-Right
  className?: string;
  onNodeClick?: (node: AttackPathNode) => void;
  onEdgeClick?: (edge: AttackPathEdge) => void;
}

// ─── Layout Algorithm ─────────────────────────────────────────────────────────

const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 200;
  const nodeHeight = 80;

  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, ranksep: 100, nodesep: 50 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

// ─── Node Type Colors ─────────────────────────────────────────────────────────

const NODE_STYLES: Record<NodeType, { bg: string; border: string; text: string; icon: any }> = {
  entry: {
    bg: 'bg-[hsl(var(--critical-dim))]',
    border: 'border-[hsl(var(--critical))]',
    text: 'text-[hsl(var(--critical))]',
    icon: Globe,
  },
  intermediate: {
    bg: 'bg-[hsl(var(--medium-dim))]',
    border: 'border-[hsl(var(--medium))]',
    text: 'text-[hsl(var(--medium))]',
    icon: AlertTriangle,
  },
  target: {
    bg: 'bg-[hsl(var(--high-dim))]',
    border: 'border-[hsl(var(--high))]',
    text: 'text-[hsl(var(--high))]',
    icon: Target,
  },
};

// ─── Custom Node Component ───────────────────────────────────────────────────

interface CustomNodeProps {
  data: {
    label: string;
    type: NodeType;
    metadata?: Record<string, any>;
    isHighlighted?: boolean;
  };
}

function CustomNode({ data }: CustomNodeProps) {
  const style = NODE_STYLES[data.type];
  const Icon = style.icon;

  return (
    <div
      className={cn(
        'rounded-lg border-2 px-4 py-3 shadow-md transition-all',
        style.bg,
        style.border,
        data.isHighlighted && 'ring-4 ring-[hsl(var(--accent))] ring-opacity-50 scale-105'
      )}
      style={{ width: 200 }}
    >
      <div className="flex items-start gap-2">
        <Icon className={cn('h-4 w-4 flex-shrink-0 mt-0.5', style.text)} />
        <div className="flex-1 min-w-0">
          <div className={cn('text-sm font-semibold leading-tight', style.text)}>
            {data.label}
          </div>
          {data.metadata?.resourceType && (
            <div className="mt-1 text-xs text-[hsl(var(--text-tertiary))] truncate">
              {data.metadata.resourceType}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const nodeTypes = {
  custom: CustomNode,
};

// ─── Legend Component ─────────────────────────────────────────────────────────

function Legend({ isCollapsed, onToggle }: { isCollapsed: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-lg border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-overlay))] shadow-lg">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-[hsl(var(--bg-elevated))] rounded-t-lg"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
          Legend
        </span>
        {isCollapsed ? (
          <ChevronDown className="h-3 w-3 text-[hsl(var(--text-tertiary))]" />
        ) : (
          <ChevronUp className="h-3 w-3 text-[hsl(var(--text-tertiary))]" />
        )}
      </button>
      {!isCollapsed && (
        <div className="space-y-2 px-3 pb-3">
          {Object.entries(NODE_STYLES).map(([type, style]) => {
            const Icon = style.icon;
            return (
              <div key={type} className="flex items-center gap-2">
                <div
                  className={cn(
                    'flex h-6 w-6 items-center justify-center rounded border',
                    style.bg,
                    style.border
                  )}
                >
                  <Icon className={cn('h-3 w-3', style.text)} />
                </div>
                <span className="text-xs text-[hsl(var(--text-primary))] capitalize">
                  {type === 'entry' ? 'Entry Point' : type}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

function AttackPathGraphInner({
  nodes: inputNodes,
  edges: inputEdges,
  direction = 'TB',
  className,
  onNodeClick,
  onEdgeClick,
}: AttackPathGraphProps) {
  const [legendCollapsed, setLegendCollapsed] = React.useState(false);
  const [highlightedNodes, setHighlightedNodes] = React.useState<Set<string>>(new Set());

  // Convert input nodes to React Flow nodes
  const initialNodes: Node[] = inputNodes.map((node) => ({
    id: node.id,
    type: 'custom',
    data: {
      label: node.label,
      type: node.type,
      metadata: node.metadata,
      isHighlighted: false,
    },
    position: { x: 0, y: 0 }, // Will be set by layout
  }));

  // Convert input edges to React Flow edges
  const initialEdges: Edge[] = inputEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    type: 'smoothstep',
    animated: true,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: 'hsl(var(--text-tertiary))',
    },
    style: {
      stroke: 'hsl(var(--text-tertiary))',
      strokeWidth: 2,
    },
    labelStyle: {
      fontSize: 11,
      fill: 'hsl(var(--text-secondary))',
      fontWeight: 500,
    },
    labelBgStyle: {
      fill: 'hsl(var(--bg-overlay))',
      fillOpacity: 0.9,
    },
  }));

  // Apply layout
  const { nodes: layoutedNodes, edges: layoutedEdges } = React.useMemo(
    () => getLayoutedElements(initialNodes, initialEdges, direction),
    [inputNodes, inputEdges, direction]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  // Update nodes when highlighted nodes change
  React.useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        data: {
          ...node.data,
          isHighlighted: highlightedNodes.has(node.id),
        },
      }))
    );
  }, [highlightedNodes, setNodes]);

  // Handle node click
  const handleNodeClick = React.useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const originalNode = inputNodes.find((n) => n.id === node.id);
      if (originalNode && onNodeClick) {
        onNodeClick(originalNode);
      }

      // Highlight connected nodes
      const connectedNodeIds = new Set<string>();
      connectedNodeIds.add(node.id);

      edges.forEach((edge) => {
        if (edge.source === node.id) {
          connectedNodeIds.add(edge.target);
        }
        if (edge.target === node.id) {
          connectedNodeIds.add(edge.source);
        }
      });

      setHighlightedNodes(connectedNodeIds);
    },
    [inputNodes, edges, onNodeClick]
  );

  // Handle edge click
  const handleEdgeClick = React.useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      const originalEdge = inputEdges.find((e) => e.id === edge.id);
      if (originalEdge && onEdgeClick) {
        onEdgeClick(originalEdge);
      }
    },
    [inputEdges, onEdgeClick]
  );

  // Clear highlights when clicking on pane
  const handlePaneClick = React.useCallback(() => {
    setHighlightedNodes(new Set());
  }, []);

  return (
    <div className={cn('relative h-full w-full', className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
        }}
      >
        <Background color="hsl(var(--border-faint))" gap={16} />
        <Controls className="rounded-lg border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-overlay))] shadow-lg" />
        <MiniMap
          className="rounded-lg border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-overlay))] shadow-lg"
          nodeColor={(node) => {
            const style = NODE_STYLES[node.data.type as NodeType];
            return `hsl(var(--${node.data.type === 'entry' ? 'critical' : node.data.type === 'target' ? 'high' : 'medium'}))`;
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
        <Panel position="top-right" className="space-y-2">
          <Legend isCollapsed={legendCollapsed} onToggle={() => setLegendCollapsed(!legendCollapsed)} />
        </Panel>
      </ReactFlow>
    </div>
  );
}

// ─── Wrapper with Provider ────────────────────────────────────────────────────

export function AttackPathGraph(props: AttackPathGraphProps) {
  return (
    <ReactFlowProvider>
      <AttackPathGraphInner {...props} />
    </ReactFlowProvider>
  );
}
