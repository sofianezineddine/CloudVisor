/* eslint-disable */
// @ts-nocheck
'use client';

import React from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  BackgroundVariant,
  Handle,
  Position,
  MarkerType,
  Panel,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './asset-graph.css';

const TYPE_PALETTE = {
  iamrole: { accent: '#f97316', label: 'IAM Role' },
  iamuser: { accent: '#fb923c', label: 'IAM User' },
  ec2: { accent: '#a78bfa', label: 'EC2' },
  vpc: { accent: '#60a5fa', label: 'VPC' },
  subnet: { accent: '#93c5fd', label: 'Subnet' },
  securitygroup: { accent: '#f87171', label: 'Sec Group' },
  s3bucket: { accent: '#38bdf8', label: 'S3' },
  kmskey: { accent: '#fdba74', label: 'KMS' },
  internet: { accent: '#f43f5e', label: 'Internet' },
};

function getPalette(resourceType) {
  const key = resourceType.split('::').pop()?.toLowerCase().replace(/_/g, '') || '';
  return TYPE_PALETTE[key] || { accent: '#6e7681', label: key || 'Resource' };
}

function deriveRisk(r) {
  let s = 10;
  if (r.is_public) s += 40;
  if (r.environment === 'prod') s = Math.round(s * 1.5);
  return Math.min(s, 100);
}

function AssetNode({ data, selected }) {
  const { accent, label } = getPalette(data.resource_type);
  const risk = data.resource_type === 'internet' ? 100 : deriveRisk(data);
  const riskColor = risk >= 60 ? '#f85149' : risk >= 30 ? '#f97316' : '#3fb950';

  if (data.resource_type === 'internet') {
    const internetStyle = {
      background: 'rgba(248,81,73,0.07)',
      border: '1.5px dashed rgba(248,81,73,0.45)',
      borderRadius: '12px',
      padding: '10px 18px',
      textAlign: 'center',
      minWidth: '96px',
      boxShadow: selected ? '0 0 0 2px rgba(248,81,73,0.3)' : '0 2px 10px rgba(0,0,0,0.4)',
    };
    return React.createElement('div', { style: internetStyle },
      React.createElement(Handle, { type: 'source', position: Position.Bottom, style: { background: '#f85149' } }),
      React.createElement('div', { style: { fontSize: 22, lineHeight: 1, marginBottom: 4 } }, '🌐'),
      React.createElement('div', { style: { color: '#f85149', fontSize: 10, fontWeight: 700 } }, 'Internet')
    );
  }

  const nodeStyle = {
    background: selected ? 'linear-gradient(135deg, #1c2128 0%, #161b22 100%)' : '#161b22',
    border: `1px solid ${selected ? accent : '#30363d'}`,
    borderRadius: '9px',
    padding: '8px 12px',
    width: '182px',
    boxShadow: selected
      ? `0 0 0 2px ${accent}30, 0 6px 24px rgba(0,0,0,0.6)`
      : '0 2px 8px rgba(0,0,0,0.4)',
    position: 'relative',
  };

  return React.createElement('div', { style: nodeStyle },
    React.createElement('div', {
      style: {
        position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
        background: `linear-gradient(90deg, transparent, ${accent}60, transparent)`,
        opacity: selected ? 1 : 0.4,
      }
    }),
    React.createElement(Handle, { type: 'target', position: Position.Top, style: { background: accent } }),
    React.createElement('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '5px' } },
      React.createElement('span', {
        style: {
          background: `${accent}15`, color: accent,
          fontSize: '8px', fontWeight: 700, letterSpacing: '0.08em',
          textTransform: 'uppercase', padding: '2px 6px', borderRadius: '4px',
          border: `1px solid ${accent}25`,
        }
      }, label),
      React.createElement('span', {
        style: {
          width: '7px', height: '7px', borderRadius: '50%',
          background: riskColor, boxShadow: `0 0 6px ${riskColor}70`,
        },
        title: `Risk: ${risk}`,
      })
    ),
    React.createElement('div', {
      style: {
        color: '#cdd9e5', fontSize: '11px', fontWeight: 500, lineHeight: 1.35,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      },
      title: data.name,
    }, data.name),
    React.createElement('div', {
      style: { color: '#484f58', fontSize: '9px', marginTop: '3px' }
    }, data.region || 'global',
      data.is_public && React.createElement('span', {
        style: {
          color: '#f85149', fontWeight: 700, fontSize: '8px',
          background: 'rgba(248,81,73,0.1)', padding: '1px 4px',
          borderRadius: '3px', marginLeft: '4px',
        }
      }, 'PUBLIC')
    ),
    React.createElement(Handle, { type: 'source', position: Position.Bottom, style: { background: accent } })
  );
}

const nodeTypes = { asset: AssetNode };

function buildGraph(resources) {
  const nodes = [];
  const edges = [];

  const groups = {};
  for (const r of resources) {
    const key = r.resource_type;
    if (!groups[key]) groups[key] = [];
    groups[key].push(r);
  }

  const sortedGroups = Object.entries(groups).sort(([, a], [, b]) => b.length - a.length);

  const NODE_W = 192, NODE_H = 82, H_GAP = 14, V_GAP = 18;
  const GROUP_PAD = 20, GROUP_GAP_X = 28, GROUP_GAP_Y = 36;
  const MAX_COLS = 6, GROUPS_PER_ROW = 3;

  let rowX = 0, rowY = 0, colInRow = 0, maxRowH = 0;

  for (const [, items] of sortedGroups) {
    const cols = Math.min(MAX_COLS, items.length);
    const rows = Math.ceil(items.length / cols);
    const gw = cols * NODE_W + (cols - 1) * H_GAP + GROUP_PAD * 2;
    const gh = rows * NODE_H + (rows - 1) * V_GAP + GROUP_PAD * 2 + 24;

    for (let i = 0; i < items.length; i++) {
      const col = i % cols;
      const row = Math.floor(i / cols);
      nodes.push({
        id: items[i].id,
        type: 'asset',
        position: {
          x: rowX + GROUP_PAD + col * (NODE_W + H_GAP),
          y: rowY + GROUP_PAD + 24 + row * (NODE_H + V_GAP),
        },
        data: items[i],
      });
    }

    maxRowH = Math.max(maxRowH, gh);
    colInRow++;
    if (colInRow >= GROUPS_PER_ROW) {
      colInRow = 0; rowX = 0;
      rowY += maxRowH + GROUP_GAP_Y;
      maxRowH = 0;
    } else {
      rowX += gw + GROUP_GAP_X;
    }
  }

  const roles = resources.filter(r => r.resource_type.includes('iamrole'));
  const users = resources.filter(r => r.resource_type.includes('iamuser'));
  for (const user of users) {
    for (const role of roles.slice(0, 4)) {
      if (user.account_id === role.account_id) {
        edges.push({
          id: `${user.id}-${role.id}`,
          source: user.id, target: role.id,
          type: 'smoothstep',
          style: { stroke: '#f97316', strokeWidth: 1.2, opacity: 0.45 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#f97316', width: 10, height: 10 },
        });
      }
    }
  }

  const publicResources = resources.filter(r => r.is_public);
  if (publicResources.length > 0) {
    nodes.push({
      id: '__internet__', type: 'asset',
      position: { x: -280, y: 60 },
      data: {
        id: '__internet__', name: 'Internet', resource_type: 'internet',
        region: '', is_public: false, environment: 'unknown',
        provider: 'aws', account_id: '', organization_id: '',
        cloud_resource_id: '', tags: {}, first_seen_at: null, last_seen_at: null,
      },
    });
    for (const r of publicResources) {
      edges.push({
        id: `inet-${r.id}`,
        source: '__internet__', target: r.id,
        type: 'smoothstep', animated: true,
        style: { stroke: '#f85149', strokeWidth: 1.5, opacity: 0.65 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#f85149', width: 10, height: 10 },
      });
    }
  }

  return { nodes, edges };
}

function LegendPanel({ items }) {
  const [open, setOpen] = React.useState(false);
  return React.createElement('div', null,
    React.createElement('button', {
      onClick: () => setOpen(o => !o),
      className: 'legend-toggle-btn',
    }, '● Legend ', React.createElement('span', { style: { transform: open ? 'rotate(180deg)' : 'none', display: 'inline-block', transition: 'transform 0.2s' } }, '▾')),
    open && React.createElement('div', { className: 'legend-content' },
      React.createElement('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '5px 18px', marginBottom: '8px' } },
        items.map(({ key, accent, label }) =>
          React.createElement('div', { key, style: { display: 'flex', alignItems: 'center', gap: '6px' } },
            React.createElement('span', { style: { width: '7px', height: '7px', borderRadius: '50%', background: accent, flexShrink: 0 } }),
            React.createElement('span', { style: { color: '#8b949e', fontSize: '9px' } }, label)
          )
        )
      ),
      React.createElement('div', { style: { borderTop: '1px solid #21262d', paddingTop: '8px', display: 'flex', gap: '12px' } },
        [['#f85149', 'High'], ['#f97316', 'Med'], ['#3fb950', 'Low']].map(([c, l]) =>
          React.createElement('div', { key: l, style: { display: 'flex', alignItems: 'center', gap: '5px' } },
            React.createElement('span', { style: { width: '7px', height: '7px', borderRadius: '50%', background: c } }),
            React.createElement('span', { style: { color: '#8b949e', fontSize: '9px' } }, l)
          )
        )
      )
    )
  );
}

function AssetGraphInner({ resources, loading }) {
  const { nodes: init_n, edges: init_e } = React.useMemo(() => buildGraph(resources), []);
  const [nodes, , onNodesChange] = useNodesState(init_n);
  const [edges, setEdges, onEdgesChange] = useEdgesState(init_e);
  const [selected, setSelected] = React.useState(null);
  const { fitView } = useReactFlow();

  React.useEffect(() => {
    const t = setTimeout(() => fitView({ padding: 0.1, duration: 500 }), 120);
    return () => clearTimeout(t);
  }, [fitView]);

  const onNodeClick = React.useCallback((_, node) => {
    if (node.id === '__internet__') { setSelected(null); return; }
    const r = resources.find(r => r.id === node.id) || null;
    setSelected(r);
    setEdges(eds => eds.map(e => ({
      ...e,
      style: { ...e.style, opacity: e.source === node.id || e.target === node.id ? 1 : 0.06 },
    })));
  }, [resources, setEdges]);

  const onPaneClick = React.useCallback(() => {
    setSelected(null);
    setEdges(eds => eds.map(e => ({ ...e, style: { ...e.style, opacity: 0.5 } })));
  }, [setEdges]);

  if (loading) {
    return React.createElement('div', { className: 'graph-loading' },
      React.createElement('div', { className: 'loading-spinner' }),
      React.createElement('p', { style: { color: '#8b949e', fontSize: '13px' } }, 'Building asset graph…')
    );
  }

  if (resources.length === 0) {
    return React.createElement('div', { className: 'graph-empty' },
      React.createElement('p', { style: { color: '#8b949e', fontSize: '13px' } }, 'No assets to visualize.')
    );
  }

  const presentKeys = [...new Set(resources.map(r => r.resource_type.split('::').pop()?.toLowerCase().replace(/_/g, '') || ''))];
  const legendItems = presentKeys.map(k => ({ key: k, ...getPalette(k) })).filter(e => e.key !== 'internet').slice(0, 10);

  return React.createElement('div', { className: 'asset-graph-container' },
    React.createElement(ReactFlow, {
      nodes,
      edges,
      onNodesChange,
      onEdgesChange,
      onNodeClick,
      onPaneClick,
      nodeTypes,
      fitView: true,
      fitViewOptions: { padding: 0.1 },
      minZoom: 0.04,
      maxZoom: 3,
      proOptions: { hideAttribution: true },
      defaultEdgeOptions: { style: { opacity: 0.5 } },
      nodesDraggable: true,
      nodesConnectable: false,
    },
      React.createElement(Background, { variant: BackgroundVariant.Dots, gap: 30, size: 1, color: 'rgba(139,148,158,0.05)' }),
      React.createElement(Controls, { showInteractive: false }),
      React.createElement(MiniMap, {
        nodeColor: (node) => {
          if (node.id === '__internet__') return '#f85149';
          const r = resources.find(r => r.id === node.id);
          return r ? getPalette(r.resource_type).accent : '#484f58';
        },
        maskColor: 'rgba(13,17,23,0.65)',
        nodeStrokeWidth: 0,
        pannable: true,
        zoomable: true,
      }),
      React.createElement(Panel, { position: 'top-right' },
        React.createElement('button', {
          onClick: () => fitView({ padding: 0.1, duration: 500 }),
          className: 'fit-view-btn',
        }, '⊞ Fit View')
      ),
      React.createElement(Panel, { position: 'top-left' },
        React.createElement(LegendPanel, { items: legendItems })
      )
    ),
    selected && React.createElement('div', { className: 'detail-panel' },
      React.createElement('div', { style: { display: 'flex', justifyContent: 'space-between', marginBottom: '12px' } },
        React.createElement('div', null,
          React.createElement('div', { style: { color: '#e6edf3', fontSize: '13px', fontWeight: 600 } }, selected.name),
          React.createElement('div', { style: { color: '#6e7681', fontSize: '10px', marginTop: '3px' } }, getPalette(selected.resource_type).label)
        ),
        React.createElement('button', {
          onClick: () => setSelected(null),
          style: { color: '#484f58', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px' }
        }, '✕')
      ),
      [
        { label: 'Provider', value: selected.provider.toUpperCase() },
        { label: 'Region', value: selected.region || 'global' },
        { label: 'Environment', value: selected.environment },
        { label: 'Exposure', value: selected.is_public ? '⚠ Public' : 'Private', danger: selected.is_public },
        { label: 'Risk', value: String(deriveRisk(selected)) },
      ].map(({ label, value, danger }) =>
        React.createElement('div', {
          key: label,
          style: { display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }
        },
          React.createElement('span', { style: { color: '#6e7681', fontSize: '11px' } }, label),
          React.createElement('span', {
            style: {
              color: danger ? '#f85149' : '#cdd9e5',
              fontSize: '11px', fontWeight: 500,
            }
          }, value)
        )
      )
    )
  );
}

export function AssetGraph({ resources, loading }) {
  const graphKey = React.useMemo(() => resources.map(r => r.id).sort().join(','), [resources]);
  return React.createElement(ReactFlowProvider, null,
    React.createElement(AssetGraphInner, { key: graphKey, resources, loading })
  );
}
