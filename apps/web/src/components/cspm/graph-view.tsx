'use client';

import * as React from 'react';
import {
  AttackPathGraph,
  type AttackPathNode,
  type AttackPathEdge,
} from '@/components/ui/attack-path-graph';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  type: 'entry' | 'intermediate' | 'target';
  metadata?: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  relationship?: string;
}

export interface GraphViewProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  direction?: 'TB' | 'LR';
  height?: string;
  onNodeClick?: (node: GraphNode) => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * GraphView — thin wrapper around AttackPathGraph providing consistent
 * defaults for CSPM graph visualizations (attack paths, escalation paths).
 *
 * Entry nodes → orange (--critical)
 * Target nodes → red (--high)
 * Intermediate nodes → yellow (--medium)
 *
 * Uses CSS variables for dark mode support.
 */
export function GraphView({
  nodes,
  edges,
  direction = 'TB',
  height = '400px',
  onNodeClick,
}: GraphViewProps) {
  // Map our simplified GraphNode to AttackPathNode
  const attackPathNodes: AttackPathNode[] = React.useMemo(
    () =>
      nodes.map((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
        metadata: n.metadata as AttackPathNode['metadata'],
      })),
    [nodes]
  );

  // Map our simplified GraphEdge to AttackPathEdge
  const attackPathEdges: AttackPathEdge[] = React.useMemo(
    () =>
      edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label ?? e.relationship,
        relationship: e.relationship,
      })),
    [edges]
  );

  const handleNodeClick = React.useCallback(
    (node: AttackPathNode) => {
      if (onNodeClick) {
        onNodeClick({
          id: node.id,
          label: node.label,
          type: node.type,
          metadata: node.metadata,
        });
      }
    },
    [onNodeClick]
  );

  return (
    <div
      className="w-full rounded-lg border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))]"
      style={{ height }}
    >
      <AttackPathGraph
        nodes={attackPathNodes}
        edges={attackPathEdges}
        direction={direction}
        onNodeClick={handleNodeClick}
      />
    </div>
  );
}
