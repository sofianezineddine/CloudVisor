'use client';

import * as React from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeMouseHandler,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import type { TopologyGraph, TopologyServiceAlert } from '@/hooks/use-aiops-topology';

// ─── Types ────────────────────────────────────────────────────────────────────

interface TopologyGraphProps {
  graph: TopologyGraph;
  serviceAlerts: Map<string, TopologyServiceAlert[]>;
  selectedServiceId: string | null;
  onNodeClick: (serviceId: string) => void;
  className?: string;
}

// ─── Layout ───────────────────────────────────────────────────────────────────

const NODE_WIDTH = 160;
const NODE_HEIGHT = 50;

function getLayoutedElements(
  graph: TopologyGraph,
  serviceAlerts: Map<string, TopologyServiceAlert[]>
): { nodes: Node[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'LR', nodesep: 60, ranksep: 120 });

  // Add nodes
  graph.services.forEach((service) => {
    dagreGraph.setNode(service.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  // Add edges
  graph.edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source_service_id, edge.target_service_id);
  });

  dagre.layout(dagreGraph);

  // Build ReactFlow nodes
  const nodes: Node[] = graph.services.map((service) => {
    const nodeWithPosition = dagreGraph.node(service.id);
    const alerts = serviceAlerts.get(service.id) ?? [];
    const healthColor = getHealthColor(alerts);

    return {
      id: service.id,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
      data: {
        label: service.display_name || service.name,
        healthColor,
        alertCount: alerts.length,
      },
      style: {
        backgroundColor: 'var(--bg-surface)',
        border: `2px solid ${healthColor}`,
        borderRadius: '8px',
        padding: '8px 12px',
        fontSize: '12px',
        color: 'var(--text-primary)',
        width: NODE_WIDTH,
        cursor: 'pointer',
      },
    };
  });

  // Build ReactFlow edges
  const edges: Edge[] = graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source_service_id,
    target: edge.target_service_id,
    type: 'default',
    animated: false,
    style: { stroke: 'var(--border-default)', strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--border-default)' },
    label: edge.relationship_type !== 'depends_on' ? edge.relationship_type : undefined,
    labelStyle: { fontSize: 10, fill: 'var(--text-tertiary)' },
  }));

  return { nodes, edges };
}

// ─── Health Color ─────────────────────────────────────────────────────────────

function getHealthColor(alerts: TopologyServiceAlert[]): string {
  if (alerts.length === 0) return 'var(--success)';

  const hasCritical = alerts.some((a) => a.severity === 'critical');
  if (hasCritical) return 'var(--critical)';

  const hasWarning = alerts.some((a) => a.severity === 'warning' || a.severity === 'high');
  if (hasWarning) return 'var(--medium)';

  return 'var(--success)';
}

// ─── Component ────────────────────────────────────────────────────────────────

export function TopologyGraphView({
  graph,
  serviceAlerts,
  selectedServiceId,
  onNodeClick,
  className,
}: TopologyGraphProps) {
  const { nodes: layoutedNodes, edges: layoutedEdges } = React.useMemo(
    () => getLayoutedElements(graph, serviceAlerts),
    [graph, serviceAlerts]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  // Update nodes when layout changes
  React.useEffect(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges]);

  const handleNodeClick: NodeMouseHandler = React.useCallback(
    (_event, node) => {
      onNodeClick(node.id);
    },
    [onNodeClick]
  );

  return (
    <div
      className={className}
      style={{
        height: '500px',
        borderRadius: '8px',
        border: '1px solid var(--border-default)',
        overflow: 'hidden',
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--border-default)" gap={20} size={1} />
        <Controls
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: '6px',
          }}
        />
        <MiniMap
          nodeColor={(node) => node.data?.healthColor ?? 'var(--text-tertiary)'}
          style={{
            backgroundColor: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: '6px',
          }}
        />
      </ReactFlow>
    </div>
  );
}
