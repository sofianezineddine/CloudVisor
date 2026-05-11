/* eslint-disable */
// @ts-nocheck
'use client';

import React from 'react';
import './asset-graph.css';
import { useTheme } from '@/components/theme-provider';

// ─── Palette — all spec resource types ───────────────────────────────────────
const NODE_TYPES = [
  { id:'iamrole',        label:'IAM Role',      color:'#f0a030', icon:'◆' },
  { id:'iamuser',        label:'IAM User',       color:'#e058a0', icon:'◆' },
  { id:'securitygroup',  label:'Sec Group',      color:'#e05060', icon:'●' },
  { id:'vpc',            label:'VPC',            color:'#4a90e8', icon:'◉' },
  { id:'subnet',         label:'Subnet',         color:'#30b8c4', icon:'◆' },
  { id:'s3bucket',       label:'S3 Bucket',      color:'#4a90e8', icon:'■' },
  { id:'ec2',            label:'EC2',            color:'#9878e8', icon:'◆' },
  { id:'lambdafunction', label:'Lambda',         color:'#c084fc', icon:'λ' },
  { id:'rdsinstance',    label:'RDS',            color:'#38c472', icon:'◆' },
  { id:'ekscluster',     label:'EKS',            color:'#818cf8', icon:'☸' },
  { id:'internet',       label:'Internet',       color:'#e05060', icon:'◉' },
];

const TYPE_MAP: Record<string, typeof NODE_TYPES[0]> = {};
NODE_TYPES.forEach(t => { TYPE_MAP[t.id] = t; });

function getNodeType(resourceType: string) {
  const k = resourceType.split('::').pop()?.toLowerCase().replace(/_/g,'') || '';
  return TYPE_MAP[k] || { id: k, label: k || 'Resource', color: '#6b7194', icon: '◆' };
}

// ─── Risk helpers ─────────────────────────────────────────────────────────────
function riskScore(r: any): number {
  if (r.risk_score != null && r.risk_score > 0) return r.risk_score;
  let s = 10;
  if (r.is_public || r.is_internet_exposed) s += 20;
  if (r.contains_pii || r.contains_sensitive_data) s += 15;
  if (r.open_findings_count > 0) s += Math.min(r.open_findings_count * 10, 60);
  if (r.environment === 'prod') s = Math.round(s * 1.5);
  return Math.min(s, 100);
}

function riskLevel(score: number): 'high' | 'med' | 'low' {
  return score >= 70 ? 'high' : score >= 40 ? 'med' : 'low';
}

function riskColor(score: number): string {
  return score >= 70 ? '#e05060' : score >= 40 ? '#f0a030' : '#38c472';
}

// ─── Relationship rules ───────────────────────────────────────────────────────
const RULES: Record<string, Array<[string, string]>> = {
  ec2:            [['subnet','RUNS_IN'],['securitygroup','BELONGS_TO'],['iamrole','HAS_ROLE']],
  instance:       [['subnet','RUNS_IN'],['securitygroup','BELONGS_TO'],['iamrole','HAS_ROLE']],
  subnet:         [['vpc','BELONGS_TO']],
  securitygroup:  [['vpc','BELONGS_TO']],
  iamuser:        [['iamrole','HAS_ACCESS_TO']],
  iamrole:        [['iamrole','ASSUMES'],['s3bucket','HAS_ACCESS_TO'],['rdsinstance','HAS_ACCESS_TO']],
  lambdafunction: [['iamrole','HAS_ROLE'],['rdsinstance','CONNECTS_TO']],
  ekscluster:     [['vpc','RUNS_IN']],
};

const EDGE_COLORS: Record<string, string> = {
  RUNS_IN:'#4a90e8', BELONGS_TO:'#6b7194', HAS_ROLE:'#f0a030',
  HAS_ACCESS_TO:'#30b8c4', ASSUMES:'#f0a030', CONNECTS_TO:'#38c472',
  CONTAINS:'#9878e8', RUNS_ON:'#9878e8', EXPOSES:'#e05060',
};

// ─── Graph data builder ───────────────────────────────────────────────────────
interface GraphNode {
  id: string;
  x: number; y: number;
  vx: number; vy: number;
  r: number;
  color: string;
  label: string;
  typeLabel: string;
  typeId: string;
  region: string;
  risk: number;
  riskLvl: 'high' | 'med' | 'low';
  edgeCount: number;
  hidden: boolean;
  resource: any;
}

interface GraphEdge {
  a: number; b: number;
  rel: string;
  color: string;
  dashed: boolean;
}

function buildGraphData(resources: any[]): { nodes: GraphNode[]; edges: GraphEdge[]; connectedCount: number } {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const idToIdx: Record<string, number> = {};
  const connected = new Set<number>();
  const seen = new Set<string>();

  // Build nodes — color by RISK LEVEL (not just type) for security visibility
  resources.forEach((r, i) => {
    const t = getNodeType(r.resource_type);
    const rs = riskScore(r);
    const rl = riskLevel(rs);
    // Use risk-based color for the node border/glow, type color for the fill
    const nodeColor = rs > 0 ? riskColor(rs) : t.color;
    nodes.push({
      id: r.id,
      x: 50 + Math.random() * 2400,
      y: 50 + Math.random() * 1400,
      vx: 0, vy: 0,
      r: t.id === 'vpc' ? 10 : t.id === 'subnet' ? 8 : rs >= 70 ? 9 : rs >= 40 ? 7 : 6,
      color: t.color,
      label: r.name || r.id,
      typeLabel: t.label,
      typeId: t.id,
      region: r.region || 'global',
      risk: rs,
      riskLvl: rl,
      edgeCount: 0,
      hidden: false,
      resource: r,
    });
    idToIdx[r.id] = i;
  });

  // Index by type
  const byType: Record<string, number[]> = {};
  nodes.forEach((n, i) => {
    if (!byType[n.typeId]) byType[n.typeId] = [];
    byType[n.typeId].push(i);
  });

  // Build edges
  nodes.forEach((n, ai) => {
    const rules = RULES[n.typeId] || [];
    for (const [tk, rel] of rules) {
      for (const bi of (byType[tk] || []).slice(0, 6)) {
        if (ai === bi) continue;
        const nb = nodes[bi];
        if (n.resource.account_id !== nb.resource.account_id) continue;
        const key = `${Math.min(ai,bi)}-${Math.max(ai,bi)}-${rel}`;
        if (seen.has(key)) continue;
        seen.add(key);
        const c = EDGE_COLORS[rel] || '#6b7194';
        edges.push({ a: ai, b: bi, rel, color: c, dashed: rel === 'HAS_ACCESS_TO' });
        nodes[ai].edgeCount++;
        nodes[bi].edgeCount++;
        connected.add(ai);
        connected.add(bi);
      }
    }
    // Public resources → internet
    if (n.resource.is_public || n.resource.is_internet_exposed) {
      connected.add(ai);
    }
  });

  const connectedCount = connected.size;
  return { nodes, edges, connectedCount };
}

// ─── Sidebar component ────────────────────────────────────────────────────────
function Sidebar({
  stats, presentTypes, selectedNode, onClose, onFilter, filterText, onToggleType, hiddenTypes, isDark,
}: {
  stats: { connected: number; edges: number; isolated: number; total: number };
  presentTypes: string[];
  selectedNode: GraphNode | null;
  onClose: () => void;
  onFilter: (q: string) => void;
  filterText: string;
  onToggleType: (id: string) => void;
  hiddenTypes: Set<string>;
  isDark?: boolean;
}) {
  return (
    <>
      {/* Search */}
      <div className="ag-sb-sec">
        <div className="ag-sb-label">Search</div>
        <input
          className="ag-filter-input"
          placeholder="Filter assets..."
          value={filterText}
          onChange={e => onFilter(e.target.value)}
        />
      </div>

      {/* Stats */}
      <div className="ag-sb-sec">
        <div className="ag-sb-label">Graph overview</div>
        <div className="ag-stats-grid">
          <div className="ag-stat-card">
            <div className="ag-stat-num ag-s-connected">{stats.connected}</div>
            <div className="ag-stat-lbl">CONNECTED</div>
          </div>
          <div className="ag-stat-card">
            <div className="ag-stat-num ag-s-edges">{stats.edges}</div>
            <div className="ag-stat-lbl">EDGES</div>
          </div>
          <div className="ag-stat-card">
            <div className="ag-stat-num ag-s-isolated">{stats.isolated}</div>
            <div className="ag-stat-lbl">ISOLATED</div>
          </div>
        </div>
      </div>

      {/* Node types legend */}
      <div className="ag-sb-sec">
        <div className="ag-sb-label">Node types</div>
        {presentTypes.map(tid => {
          const t = TYPE_MAP[tid] || { id: tid, label: tid, color: '#6b7194' };
          const hidden = hiddenTypes.has(tid);
          return (
            <div key={tid} className="ag-leg-item" onClick={() => onToggleType(tid)}>
              <div className="ag-leg-dot" style={{ background: hidden ? t.color + '44' : t.color }} />
              <span className="ag-leg-name" style={{ opacity: hidden ? 0.4 : 1 }}>{t.label}</span>
            </div>
          );
        })}
      </div>

      {/* Relationships */}
      <div className="ag-sb-sec">
        <div className="ag-sb-label">Relationships</div>
        {[
          { rel: 'ASSUMES',       color: '#f0a030', dashed: false },
          { rel: 'HAS ACCESS TO', color: '#30b8c4', dashed: true  },
          { rel: 'BELONGS TO',    color: '#6b7194', dashed: false },
          { rel: 'RUNS IN',       color: '#4a90e8', dashed: false },
          { rel: 'HAS ROLE',      color: '#f0a030', dashed: false },
        ].map(({ rel, color, dashed }) => (
          <div key={rel} className="ag-rel-item">
            <div className="ag-rel-line" style={{
              background: dashed ? 'none' : color,
              borderTop: dashed ? `1px dashed ${color}` : 'none',
            }} />
            <span className="ag-rel-name">{rel}</span>
          </div>
        ))}
      </div>

      {/* Risk scale */}
      <div className="ag-sb-sec">
        <div className="ag-sb-label">Risk scale</div>
        {[
          { color: '#e05060', label: 'High (≥70)' },
          { color: '#f0a030', label: 'Medium (≥40)' },
          { color: '#38c472', label: 'Low (<40)' },
        ].map(({ color, label }) => (
          <div key={label} className="ag-risk-row">
            <div className="ag-risk-dot" style={{ background: color }} />
            <span className="ag-risk-lbl">{label}</span>
          </div>
        ))}
      </div>

      {/* Selected node */}
      {selectedNode && (
        <div className="ag-sb-sec">
          <div className="ag-sb-label">Selected node</div>
          <div className="ag-sel-panel">
            <div className="ag-sel-name">{selectedNode.label}</div>
            {[
              { l: 'Type',     v: selectedNode.typeLabel },
              { l: 'Region',   v: selectedNode.region },
              { l: 'Edges',    v: String(selectedNode.edgeCount) },
              { l: 'Risk',     v: `${selectedNode.riskLvl.toUpperCase()} (${Math.round(selectedNode.risk)})`,
                color: riskColor(selectedNode.risk) },
              { l: 'Findings', v: String(selectedNode.resource?.open_findings_count ?? 0),
                color: (selectedNode.resource?.open_findings_count ?? 0) > 0 ? '#e05060' : undefined },
              { l: 'Provider', v: selectedNode.resource?.provider?.toUpperCase() || '—' },
              { l: 'Exposure', v: selectedNode.resource?.is_public ? '⚠ Public' : 'Private',
                color: selectedNode.resource?.is_public ? '#e05060' : undefined },
            ].map(({ l, v, color }) => (
              <div key={l} className="ag-sel-row">
                <span>{l}</span>
                <span className="ag-sel-val" style={color ? { color } : {}}>{v}</span>
              </div>
            ))}
            <button className="ag-sel-action" onClick={onClose}>✕ Deselect</button>
          </div>
        </div>
      )}
    </>
  );
}

// ─── Main canvas graph component ─────────────────────────────────────────────
function CanvasGraph({ resources, loading, onSwitchToTable }: {
  resources: any[];
  loading: boolean;
  onSwitchToTable?: () => void;
}) {
  const wrapRef = React.useRef<HTMLDivElement>(null);
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const mmRef = React.useRef<HTMLCanvasElement>(null);
  const tooltipRef = React.useRef<HTMLDivElement>(null);

  // Graph state — stored in refs to avoid re-renders on every frame
  const graphRef = React.useRef<{ nodes: GraphNode[]; edges: GraphEdge[]; connectedCount: number } | null>(null);
  const transformRef = React.useRef({ x: 0, y: 0, scale: 1 });
  const draggingRef = React.useRef(false);
  const lastMouseRef = React.useRef({ x: 0, y: 0 });
  const hoveredRef = React.useRef<GraphNode | null>(null);
  const selectedRef = React.useRef<GraphNode | null>(null);
  const draggingNodeRef = React.useRef<GraphNode | null>(null);       // node being dragged
  const lassoRef = React.useRef<{ x1:number;y1:number;x2:number;y2:number } | null>(null); // lasso rect
  const lassoActiveRef = React.useRef(false);
  const selectedGroupRef = React.useRef<Set<number>>(new Set());     // multi-selected node indices
  const groupDragRef = React.useRef(false);                          // dragging a group
  const hiddenTypesRef = React.useRef<Set<string>>(new Set());
  const filterRef = React.useRef('');
  const rafRef = React.useRef<number>(0);
  const isDarkRef = React.useRef(true);

  // React state for sidebar (only updates when selection/filter changes)
  const [selected, setSelected] = React.useState<GraphNode | null>(null);
  const [filterText, setFilterText] = React.useState('');
  const [hiddenTypes, setHiddenTypes] = React.useState<Set<string>>(new Set());
  const [stats, setStats] = React.useState({ connected: 0, edges: 0, isolated: 0, total: 0 });
  const [presentTypes, setPresentTypes] = React.useState<string[]>([]);
  const [sidebarOpen, setSidebarOpen] = React.useState(true);

  // Use global theme from header toggle
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Build graph data when resources change
  React.useEffect(() => {
    if (!resources.length) return;
    const data = buildGraphData(resources);
    graphRef.current = data;
    setStats({
      connected: data.connectedCount,
      edges: data.edges.length,
      isolated: resources.length - data.connectedCount,
      total: resources.length,
    });
    const types = [...new Set(data.nodes.map(n => n.typeId))];
    setPresentTypes(types);
    resetView();
  }, [resources.length]); // eslint-disable-line

  // Sync isDarkRef with global theme and redraw
  React.useEffect(() => {
    isDarkRef.current = isDark;
    drawFrame();
  }, [isDark]); // eslint-disable-line

  // Canvas sizing — observe wrap for resize
  React.useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const ro = new ResizeObserver(() => resizeCanvas());
    ro.observe(wrap);
    resizeCanvas();
    return () => ro.disconnect();
  }, []); // eslint-disable-line

  function resizeCanvas() {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;
    const { width, height } = wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    const ctx = canvas.getContext('2d')!;
    ctx.scale(dpr, dpr);
    // After resize, re-fit the graph to fill the new canvas dimensions
    if (graphRef.current && graphRef.current.nodes.length > 0) {
      resetView();
    } else {
      drawFrame();
    }
  }

  function getCanvasSize() {
    const canvas = canvasRef.current;
    if (!canvas) return { W: 0, H: 0 };
    return { W: parseFloat(canvas.style.width) || 0, H: parseFloat(canvas.style.height) || 0 };
  }

  // World ↔ screen transforms
  function ws(x: number, y: number) {
    const t = transformRef.current;
    return { x: x * t.scale + t.x, y: y * t.scale + t.y };
  }
  function sw(x: number, y: number) {
    const t = transformRef.current;
    return { x: (x - t.x) / t.scale, y: (y - t.y) / t.scale };
  }

  function drawFrame() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    const { W, H } = getCanvasSize();
    if (!W || !H) return;
    ctx.clearRect(0, 0, W, H);

    const t = transformRef.current;
    const graph = graphRef.current;
    const selNode = selectedRef.current;
    const hovNode = hoveredRef.current;
    const dark = isDarkRef.current;

    // Background fill
    ctx.fillStyle = dark ? '#0d0f14' : '#eef0f5';
    ctx.fillRect(0, 0, W, H);

    // Grid
    ctx.save();
    ctx.strokeStyle = dark ? 'rgba(42,47,66,0.28)' : 'rgba(180,185,210,0.35)';
    ctx.lineWidth = 0.5;
    const gs = 60 * t.scale;
    const ox = t.x % gs, oy = t.y % gs;
    for (let x = ox; x < W; x += gs) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = oy; y < H; y += gs) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    ctx.restore();

    if (!graph) return;

    const selId = selNode ? graph.nodes.indexOf(selNode) : -1;
    const selNeighbors = new Set<number>();
    if (selId >= 0) {
      graph.edges.forEach(e => {
        if (e.a === selId) selNeighbors.add(e.b);
        if (e.b === selId) selNeighbors.add(e.a);
      });
    }

    // Edges
    graph.edges.forEach(e => {
      const na = graph.nodes[e.a], nb = graph.nodes[e.b];
      if (na.hidden || nb.hidden) return;
      const pa = ws(na.x, na.y), pb = ws(nb.x, nb.y);
      const isSel = selId >= 0 && (e.a === selId || e.b === selId);
      ctx.save();
      ctx.strokeStyle = isSel ? e.color + 'cc' : e.color + '30';
      ctx.lineWidth = isSel ? 1.5 : 0.6;
      if (e.dashed) ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
      ctx.restore();
    });

    // Nodes
    graph.nodes.forEach((n, i) => {
      if (n.hidden) return;
      const p = ws(n.x, n.y);
      if (p.x < -20 || p.x > W + 20 || p.y < -20 || p.y > H + 20) return;

      const isHov = hovNode === n;
      const isSel = selId === i;
      const isGroupSel = selectedGroupRef.current.has(i);
      const isNeighbor = selId >= 0 && selNeighbors.has(i) && !isSel;
      const isDim = selId >= 0 && !isSel && !isNeighbor && !isGroupSel;
      const r = n.r * t.scale * (isHov || isSel ? 1.5 : 1);
      const alpha = isDim ? 0.12 : 1;

      // Glow
      if ((isHov || isSel || n.riskLvl === 'high') && !isDim) {
        ctx.save();
        ctx.globalAlpha = isHov || isSel ? 0.35 : 0.15;
        const grad = ctx.createRadialGradient(p.x, p.y, r * 0.5, p.x, p.y, r * 2.8);
        grad.addColorStop(0, n.color);
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r * 2.8, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      ctx.save();
      ctx.globalAlpha = alpha;

      // Fill — blend type color with risk intensity
      const riskA = n.riskLvl === 'high' ? 0.9 : n.riskLvl === 'med' ? 0.75 : 0.55;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = n.color + Math.round(riskA * 255).toString(16).padStart(2, '0');
      ctx.fill();

      // Border — colored by RISK LEVEL for security visibility
      const borderColor = n.risk >= 70 ? '#e05060' : n.risk >= 40 ? '#f0a030' : n.color;
      ctx.strokeStyle = isSel ? '#ffffff' : isGroupSel ? '#4a90e8' : isHov ? borderColor : borderColor + '70';
      ctx.lineWidth = isSel ? 2 : isGroupSel ? 1.5 : isHov ? 1.5 : n.risk >= 70 ? 1.2 : 0.5;
      ctx.stroke();

      // Label
      if ((isHov || isSel || isNeighbor) && t.scale > 0.4) {
        ctx.font = `${Math.min(11, 10 * t.scale)}px 'IBM Plex Mono', monospace`;
        ctx.textAlign = 'center';
        ctx.fillStyle = isHov || isSel ? '#e2e4ef' : '#9398b8';
        ctx.fillText(n.label.slice(0, 14), p.x, p.y + r + 11 * t.scale + 2);
      }

      ctx.restore();
    });

    drawMinimap(graph.nodes.filter(n => !n.hidden));

    // Draw lasso selection rect
    const lasso = lassoRef.current;
    if (lasso) {
      const dark = isDarkRef.current;
      ctx.save();
      ctx.strokeStyle = '#4a90e8';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(lasso.x1, lasso.y1, lasso.x2 - lasso.x1, lasso.y2 - lasso.y1);
      ctx.fillStyle = 'rgba(74,144,232,0.06)';
      ctx.fillRect(lasso.x1, lasso.y1, lasso.x2 - lasso.x1, lasso.y2 - lasso.y1);
      ctx.restore();
    }
  }

  function drawMinimap(nodes: GraphNode[]) {
    const mm = mmRef.current;
    if (!mm) return;
    const mw = 100, mh = 70;
    const ctx = mm.getContext('2d')!;
    ctx.clearRect(0, 0, mw, mh);
    const dark = isDarkRef.current;
    ctx.fillStyle = dark ? 'rgba(20,23,32,0.85)' : 'rgba(240,241,245,0.92)';
    ctx.fillRect(0, 0, mw, mh);

    if (!nodes.length) return;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(n => {
      if (n.x < minX) minX = n.x; if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y; if (n.y > maxY) maxY = n.y;
    });
    const ww = maxX - minX || 1, wh = maxY - minY || 1;
    const sc = Math.min(mw / ww, mh / wh) * 0.82;
    const ox = (mw - ww * sc) / 2, oy = (mh - wh * sc) / 2;

    nodes.forEach(n => {
      const px = ox + (n.x - minX) * sc, py = oy + (n.y - minY) * sc;
      ctx.beginPath();
      ctx.arc(px, py, 1.5, 0, Math.PI * 2);
      ctx.fillStyle = n.color + '90';
      ctx.fill();
    });

    const { W, H } = getCanvasSize();
    const t = transformRef.current;
    const vx = (-t.x / t.scale - minX) * sc + ox;
    const vy = (-t.y / t.scale - minY) * sc + oy;
    const vw = (W / t.scale) * sc, vh = (H / t.scale) * sc;
    ctx.strokeStyle = 'rgba(74,144,232,0.55)';
    ctx.lineWidth = 1;
    ctx.strokeRect(vx, vy, vw, vh);
  }

  function resetView() {
    const graph = graphRef.current;
    const { W, H } = getCanvasSize();
    if (!graph || !W || !H) return;
    const vis = graph.nodes.filter(n => !n.hidden);
    if (!vis.length) return;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    vis.forEach(n => {
      if (n.x < minX) minX = n.x; if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y; if (n.y > maxY) maxY = n.y;
    });
    const pad = 40;
    const ww = (maxX - minX) + pad * 2 || 1;
    const wh = (maxY - minY) + pad * 2 || 1;
    // Scale to fill the canvas — use the smaller ratio so everything fits
    const scale = Math.min(W / ww, H / wh, 3);
    const cx = minX + (maxX - minX) / 2;
    const cy = minY + (maxY - minY) / 2;
    transformRef.current = {
      scale,
      x: W / 2 - cx * scale,
      y: H / 2 - cy * scale,
    };
    drawFrame();
  }

  function zoom(factor: number) {
    const { W, H } = getCanvasSize();
    const t = transformRef.current;
    const newScale = Math.max(0.08, Math.min(6, t.scale * factor));
    transformRef.current = {
      scale: newScale,
      x: W / 2 - (W / 2 - t.x) * (newScale / t.scale),
      y: H / 2 - (H / 2 - t.y) * (newScale / t.scale),
    };
    drawFrame();
  }

  function toggleLayout() {
    const graph = graphRef.current;
    if (!graph) return;
    const { W, H } = getCanvasSize();
    // Use the actual canvas dimensions to spread clusters across the full area
    const cx = 1200, cy = 800;
    const clusterR = Math.min(cx, cy) * 0.45;
    const types = [...new Set(graph.nodes.map(n => n.typeId))];
    types.forEach((tid, ti) => {
      const angle = (ti / types.length) * Math.PI * 2;
      const tx = cx + Math.cos(angle) * clusterR;
      const ty = cy + Math.sin(angle) * clusterR;
      const typeNodes = graph.nodes.filter(n => n.typeId === tid);
      typeNodes.forEach((n, i) => {
        const a = (i / typeNodes.length) * Math.PI * 2;
        const spread = 60 + Math.min(typeNodes.length, 50) * 3;
        n.x = tx + Math.cos(a) * spread;
        n.y = ty + Math.sin(a) * spread;
      });
    });
    resetView();
  }

  // Mouse events — pan, node drag, lasso select, group drag
  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onMouseDown = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      const wp = sw(mx, my);
      const graph = graphRef.current;

      // Check if clicking on a node
      let hitNode: GraphNode | null = null;
      let hitIdx = -1;
      if (graph) {
        graph.nodes.forEach((n, i) => {
          if (n.hidden) return;
          const d = Math.hypot(n.x - wp.x, n.y - wp.y);
          if (d < (n.r + 6) / transformRef.current.scale) { hitNode = n; hitIdx = i; }
        });
      }

      if (hitNode) {
        // If node is in group, start group drag
        if (selectedGroupRef.current.has(hitIdx)) {
          groupDragRef.current = true;
        } else {
          // Start dragging this single node
          draggingNodeRef.current = hitNode;
          selectedGroupRef.current.clear();
        }
        lastMouseRef.current = { x: e.clientX, y: e.clientY };
      } else {
        // Start lasso or pan
        if (e.shiftKey) {
          // Shift+drag = lasso
          lassoActiveRef.current = true;
          lassoRef.current = { x1: mx, y1: my, x2: mx, y2: my };
        } else {
          // Regular drag = pan canvas
          draggingRef.current = true;
          selectedGroupRef.current.clear();
        }
        lastMouseRef.current = { x: e.clientX, y: e.clientY };
      }
    };

    const onMouseUp = (e: MouseEvent) => {
      // Finish lasso — select nodes inside rect
      if (lassoActiveRef.current && lassoRef.current) {
        const graph = graphRef.current;
        if (graph) {
          const { x1, y1, x2, y2 } = lassoRef.current;
          const lx1 = Math.min(x1, x2), lx2 = Math.max(x1, x2);
          const ly1 = Math.min(y1, y2), ly2 = Math.max(y1, y2);
          const newGroup = new Set<number>();
          graph.nodes.forEach((n, i) => {
            if (n.hidden) return;
            const p = ws(n.x, n.y);
            if (p.x >= lx1 && p.x <= lx2 && p.y >= ly1 && p.y <= ly2) newGroup.add(i);
          });
          selectedGroupRef.current = newGroup;
        }
        lassoRef.current = null;
        lassoActiveRef.current = false;
      }
      draggingRef.current = false;
      draggingNodeRef.current = null;
      groupDragRef.current = false;
      drawFrame();
    };

    const onMouseMove = (e: MouseEvent) => {
      const dx = e.clientX - lastMouseRef.current.x;
      const dy = e.clientY - lastMouseRef.current.y;

      // Pan canvas
      if (draggingRef.current) {
        const t = transformRef.current;
        t.x += dx; t.y += dy;
        lastMouseRef.current = { x: e.clientX, y: e.clientY };
        drawFrame();
        return;
      }

      // Drag single node
      if (draggingNodeRef.current) {
        const n = draggingNodeRef.current;
        n.x += dx / transformRef.current.scale;
        n.y += dy / transformRef.current.scale;
        lastMouseRef.current = { x: e.clientX, y: e.clientY };
        drawFrame();
        return;
      }

      // Drag group
      if (groupDragRef.current) {
        const graph = graphRef.current;
        if (graph) {
          const sc = transformRef.current.scale;
          selectedGroupRef.current.forEach(i => {
            graph.nodes[i].x += dx / sc;
            graph.nodes[i].y += dy / sc;
          });
        }
        lastMouseRef.current = { x: e.clientX, y: e.clientY };
        drawFrame();
        return;
      }

      // Update lasso rect
      if (lassoActiveRef.current && lassoRef.current) {
        const rect = canvas.getBoundingClientRect();
        lassoRef.current.x2 = e.clientX - rect.left;
        lassoRef.current.y2 = e.clientY - rect.top;
        drawFrame();
        return;
      }

      // Hover detection
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      const wp = sw(mx, my);
      const graph = graphRef.current;
      if (!graph) return;

      let found: GraphNode | null = null, bestDist = Infinity;
      graph.nodes.forEach(n => {
        if (n.hidden) return;
        const d = Math.hypot(n.x - wp.x, n.y - wp.y);
        const threshold = (n.r + 5) / transformRef.current.scale;
        if (d < threshold && d < bestDist) { bestDist = d; found = n; }
      });

      if (found !== hoveredRef.current) { hoveredRef.current = found; drawFrame(); }

      const tt = tooltipRef.current;
      if (!tt) return;
      if (found) {
        tt.classList.add('show');
        tt.style.left = (mx + 16) + 'px';
        tt.style.top = (my - 10) + 'px';
        (tt.querySelector('#ag-tt-name') as HTMLElement).textContent = found.label;
        (tt.querySelector('#ag-tt-type') as HTMLElement).textContent = found.typeLabel;
        (tt.querySelector('#ag-tt-region') as HTMLElement).textContent = found.region;
        (tt.querySelector('#ag-tt-edges') as HTMLElement).textContent = String(found.edgeCount);
        const findingsEl = tt.querySelector('#ag-tt-findings') as HTMLElement;
        if (findingsEl) {
          const fc = found.resource?.open_findings_count ?? 0;
          findingsEl.textContent = fc > 0 ? `${fc} open` : 'None';
          findingsEl.style.color = fc >= 5 ? '#e05060' : fc > 0 ? '#f0a030' : '';
        }
        const riskEl = tt.querySelector('#ag-tt-risk') as HTMLElement;
        riskEl.textContent = `${found.riskLvl.charAt(0).toUpperCase() + found.riskLvl.slice(1)} (${Math.round(found.risk)})`;
        riskEl.className = 'ag-tt-risk ag-risk-' + found.riskLvl;
      } else {
        tt.classList.remove('show');
      }
    };

    const onClick = (e: MouseEvent) => {
      if (Math.hypot(e.movementX, e.movementY) > 4) return;
      if (lassoActiveRef.current) return;
      const newSel = hoveredRef.current === selectedRef.current ? null : hoveredRef.current;
      selectedRef.current = newSel;
      setSelected(newSel);
      drawFrame();
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      const factor = e.deltaY > 0 ? 0.85 : 1.18;
      const t = transformRef.current;
      const newScale = Math.max(0.08, Math.min(6, t.scale * factor));
      transformRef.current = {
        scale: newScale,
        x: mx - (mx - t.x) * (newScale / t.scale),
        y: my - (my - t.y) * (newScale / t.scale),
      };
      drawFrame();
    };

    // Cursor style
    const onMouseMoveForCursor = (e: MouseEvent) => {
      if (draggingNodeRef.current || groupDragRef.current) {
        canvas.style.cursor = 'grabbing';
      } else if (hoveredRef.current) {
        canvas.style.cursor = 'pointer';
      } else if (e.shiftKey) {
        canvas.style.cursor = 'crosshair';
      } else {
        canvas.style.cursor = draggingRef.current ? 'grabbing' : 'grab';
      }
    };

    canvas.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mouseup', onMouseUp);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mousemove', onMouseMoveForCursor);
    canvas.addEventListener('click', onClick);
    canvas.addEventListener('wheel', onWheel, { passive: false });

    return () => {
      canvas.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mousemove', onMouseMoveForCursor);
      canvas.removeEventListener('click', onClick);
      canvas.removeEventListener('wheel', onWheel);
    };
  }, []); // eslint-disable-line

  function handleFilter(q: string) {
    filterRef.current = q.toLowerCase();
    setFilterText(q);
    const graph = graphRef.current;
    if (!graph) return;
    graph.nodes.forEach(n => {
      n.hidden = hiddenTypesRef.current.has(n.typeId) ||
        (filterRef.current !== '' &&
          !n.label.toLowerCase().includes(filterRef.current) &&
          !n.typeLabel.toLowerCase().includes(filterRef.current));
    });
    drawFrame();
  }

  function handleToggleType(tid: string) {
    const next = new Set(hiddenTypesRef.current);
    if (next.has(tid)) next.delete(tid); else next.add(tid);
    hiddenTypesRef.current = next;
    setHiddenTypes(new Set(next));
    const graph = graphRef.current;
    if (!graph) return;
    graph.nodes.forEach(n => {
      n.hidden = next.has(n.typeId) ||
        (filterRef.current !== '' &&
          !n.label.toLowerCase().includes(filterRef.current) &&
          !n.typeLabel.toLowerCase().includes(filterRef.current));
    });
    drawFrame();
  }

  if (loading) {
    return (
      <div className={`ag-root ${isDark ? 'ag-dark' : 'ag-light'}`}>
        <div className="ag-loading">
          <div className="ag-spinner" />
          <p style={{ color: '#6b7194', fontSize: 12 }}>Building relationship graph…</p>
        </div>
      </div>
    );
  }

  if (!resources.length) {
    return (
      <div className={`ag-root ${isDark ? 'ag-dark' : 'ag-light'}`}>
        <div className="ag-empty">
          <div style={{ fontSize: 40, marginBottom: 12 }}>◈</div>
          <div style={{ color: '#e2e4ef', fontSize: 13, fontWeight: 500 }}>No resources discovered</div>
          <div style={{ color: '#6b7194', fontSize: 11, marginTop: 6 }}>Connect a cloud account and run a sync.</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`ag-root ${isDark ? 'ag-dark' : 'ag-light'}`}>
      {/* Header */}
      <div className="ag-header">
        <span className="ag-header-title">Asset Inventory</span>
        <span className="ag-header-count">{resources.length.toLocaleString()}</span>
        <span className="ag-badge-live">● LIVE</span>
        <span className="ag-header-spacer" />
        <button className="ag-btn" onClick={resetView}>Fit view</button>
        <button className="ag-btn" onClick={toggleLayout}>⟳ Layout</button>
        {onSwitchToTable && (
          <button className="ag-btn ag-btn-primary" onClick={onSwitchToTable}>
            ☰ Table view
          </button>
        )}
      </div>

      {/* Body — sidebar LEFT, canvas RIGHT */}
      <div className="ag-body">
        {/* Left collapsible sidebar */}
        <div className={`ag-sidebar ${sidebarOpen ? 'ag-sb-expanded' : 'ag-sb-collapsed'}`}>
          {/* Toggle button — right edge of sidebar */}
          <div className="ag-sb-toggle" onClick={() => setSidebarOpen(o => !o)}
            title={sidebarOpen ? 'Collapse panel' : 'Expand panel'}>
            <span className="ag-sb-chevron" />
          </div>

          {/* Icon strip — visible when collapsed */}
          {!sidebarOpen && (
            <div className="ag-sb-icons">
              <button className="ag-sb-icon-btn" title="Search" onClick={() => setSidebarOpen(true)}>⌕</button>
              <button className="ag-sb-icon-btn" title="Stats"  onClick={() => setSidebarOpen(true)}>◈</button>
              <button className="ag-sb-icon-btn" title="Types"  onClick={() => setSidebarOpen(true)}>◆</button>
              <button className="ag-sb-icon-btn" title="Risk"   onClick={() => setSidebarOpen(true)}>⚠</button>
            </div>
          )}

          {/* Full content — visible when expanded */}
          <div className="ag-sb-content">
            <Sidebar
              stats={stats}
              presentTypes={presentTypes}
              selectedNode={selected}
              onClose={() => { selectedRef.current = null; setSelected(null); drawFrame(); }}
              onFilter={handleFilter}
              filterText={filterText}
              onToggleType={handleToggleType}
              hiddenTypes={hiddenTypes}
              isDark={isDark}
            />
          </div>
        </div>

        {/* Canvas */}
        <div className="ag-canvas-wrap" ref={wrapRef}>
          <canvas id="ag-graph" ref={canvasRef} />

          {/* Tooltip */}
          <div className="ag-tooltip" ref={tooltipRef}>
            <div className="ag-tt-name" id="ag-tt-name">—</div>
            <div className="ag-tt-row"><span>Type</span><span className="ag-tt-val" id="ag-tt-type">—</span></div>
            <div className="ag-tt-row"><span>Region</span><span className="ag-tt-val" id="ag-tt-region">—</span></div>
            <div className="ag-tt-row"><span>Edges</span><span className="ag-tt-val" id="ag-tt-edges">—</span></div>
            <div className="ag-tt-row"><span>Findings</span><span className="ag-tt-val" id="ag-tt-findings">—</span></div>
            <div><span className="ag-tt-risk" id="ag-tt-risk">—</span></div>
          </div>

          {/* Zoom controls */}
          <div className="ag-controls">
            <button className="ag-ctrl-btn" onClick={() => zoom(1.25)} title="Zoom in">+</button>
            <button className="ag-ctrl-btn" onClick={() => zoom(0.8)} title="Zoom out">−</button>
            <button className="ag-ctrl-btn" onClick={resetView} title="Reset">⊡</button>
          </div>

          {/* Minimap */}
          <div className="ag-minimap">
            <canvas id="ag-minimap" ref={mmRef} width={100} height={70} />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="ag-footer">
        <div className="ag-footer-left">
          <span className="ag-footer-dot" style={{ background: '#38c472' }} />
          <span className="ag-footer-text">{stats.connected} connected · {stats.edges} edges · {stats.isolated} isolated</span>
        </div>
        <div className="ag-footer-center">
          <span className="ag-footer-hint">Scroll to zoom · Drag to pan · Click node to inspect · Shift+drag to select group</span>
        </div>
        <div className="ag-footer-right">
          <span className="ag-footer-text">CloudVisor Asset Graph</span>
        </div>
      </div>
    </div>
  );
}

// ─── Export ───────────────────────────────────────────────────────────────────
export function AssetGraph({ resources, loading, onSwitchToTable }: {
  resources: any[];
  loading: boolean;
  onSwitchToTable?: () => void;
}) {
  return <CanvasGraph resources={resources} loading={loading} onSwitchToTable={onSwitchToTable} />;
}
