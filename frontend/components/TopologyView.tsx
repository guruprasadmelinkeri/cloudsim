'use client';

import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { TopologyNode, TopologyEdge } from '@/types';

//  Custom Node Components 

function ClientNode({ data }: NodeProps) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="px-4 py-2 rounded-xl bg-gradient-to-br from-violet-500 to-purple-700 border border-violet-400/50 shadow-lg shadow-violet-500/30 text-white text-xs font-bold tracking-wider">
        <div>CLIENT</div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-violet-400 !w-3 !h-3" />
    </div>
  );
}

function LoadBalancerNode({ data }: NodeProps) {
  return (
    <div className="flex flex-col items-center gap-1">
      <Handle type="target" position={Position.Top} className="!bg-blue-400 !w-3 !h-3" />
      <div className="px-4 py-2 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-600 border border-blue-400/50 shadow-lg shadow-blue-500/30 text-white text-xs font-bold tracking-wider">
        <div>LOAD BALANCER</div>
        {data.algorithm && (
          <div className="text-blue-200 text-[10px] font-normal mt-0.5 capitalize">
            {String(data.algorithm).replace('_', ' ')}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-blue-400 !w-3 !h-3" />
    </div>
  );
}

function ServerNode({ data }: NodeProps) {
  const status = data.status as string;
  const cpu = data.cpu as number;

  const containerClass =
    status === 'failed'
      ? 'from-red-900/80 to-red-800/60 border-red-500/60 shadow-red-500/30'
      : status === 'new'
      ? 'from-emerald-900/80 to-green-800/60 border-emerald-400/60 shadow-emerald-500/30'
      : 'from-slate-800/90 to-slate-700/60 border-slate-500/50 shadow-slate-500/20';

  const cpuColor =
    cpu >= 80 ? 'text-red-400' : cpu >= 60 ? 'text-yellow-400' : 'text-emerald-400';

  const cpuBarColor =
    cpu >= 80 ? 'bg-red-500' : cpu >= 60 ? 'bg-yellow-500' : 'bg-emerald-500';

  const statusLabel = status === 'failed' ? 'FAILED' : status === 'new' ? 'NEW' : 'ACTIVE';

  return (
    <div className="flex flex-col items-center">
      <Handle type="target" position={Position.Top} className="!bg-slate-400 !w-3 !h-3" />
      <div
        className={`w-36 px-3 py-2 rounded-xl bg-gradient-to-br ${containerClass} border shadow-lg text-white text-xs font-semibold tracking-wider`}
      >
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-bold">
            {statusLabel} · {(data.label as string)}
          </span>
          {status === 'new' && (
            <span className="text-[9px] bg-emerald-500 text-white px-1 rounded font-bold">NEW</span>
          )}
          {status === 'failed' && (
            <span className="text-[9px] bg-red-500 text-white px-1 rounded font-bold">FAILED</span>
          )}
        </div>
        {status !== 'failed' && (
          <>
            <div className="flex justify-between items-center text-[10px] mb-0.5">
              <span className="text-slate-400">CPU</span>
              <span className={`font-bold ${cpuColor}`}>{cpu?.toFixed(0) ?? 0}%</span>
            </div>
            <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full ${cpuBarColor} rounded-full transition-all duration-500`}
                style={{ width: `${Math.min(100, cpu ?? 0)}%` }}
              />
            </div>
            <div className="text-[9px] text-slate-400 mt-1">
              Active: {data.active_requests ?? 0}
            </div>
          </>
        )}
        {status === 'failed' && (
          <div className="text-[10px] text-red-300 text-center mt-1 animate-pulse">
             OFFLINE
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-slate-400 !w-3 !h-3" />
    </div>
  );
}

function CacheNode({ data }: NodeProps) {
  return (
    <div className="flex flex-col items-center">
      <Handle type="target" position={Position.Top} className="!bg-amber-400 !w-3 !h-3" />
      <div className="px-4 py-2 rounded-xl bg-gradient-to-br from-amber-900/80 to-orange-800/60 border border-amber-500/50 shadow-lg shadow-amber-500/20 text-white text-xs font-bold tracking-wider">
        <div>CACHE</div>
        {data.hit_rate && (
          <div className="text-amber-300 text-[10px] font-normal">Hit: {String(data.hit_rate)}</div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-amber-400 !w-3 !h-3" />
    </div>
  );
}

function DatabaseNode({ data }: NodeProps) {
  const status = data.status as string;
  const latency = data.latency_ms as number;
  const isSlow = status === 'slow';

  return (
    <div className="flex flex-col items-center">
      <Handle type="target" position={Position.Top} className="!bg-teal-400 !w-3 !h-3" />
      <div
        className={`px-4 py-2 rounded-xl border shadow-lg text-white text-xs font-bold tracking-wider transition-all duration-500 ${
          isSlow
            ? 'bg-gradient-to-br from-yellow-900/80 to-orange-800/60 border-yellow-500/60 shadow-yellow-500/30'
            : 'bg-gradient-to-br from-teal-900/80 to-cyan-800/60 border-teal-500/50 shadow-teal-500/20'
        }`}
      >
        <div>DATABASE</div>
        <div className={`text-[10px] font-normal mt-0.5 ${isSlow ? 'text-yellow-300 animate-pulse' : 'text-teal-300'}`}>
          {isSlow ? 'SLOW' : 'HEALTHY'}
        </div>
        <div className="text-[10px] text-slate-400 mt-0.5">{latency}ms</div>
      </div>
    </div>
  );
}

//  Node type registry 

const nodeTypes = {
  client: ClientNode,
  load_balancer: LoadBalancerNode,
  server: ServerNode,
  cache: CacheNode,
  database: DatabaseNode,
};

//  Layout Positions 

function computeLayout(nodes: TopologyNode[]): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {};
  const servers = nodes.filter((n) => n.type === 'server');
  const nServers = servers.length;
  const serverSpacing = 180;
  const totalWidth = (nServers - 1) * serverSpacing;
  const startX = -totalWidth / 2;

  nodes.forEach((n) => {
    if (n.type === 'client') positions[n.id] = { x: 0, y: 0 };
    else if (n.type === 'load_balancer') positions[n.id] = { x: 0, y: 140 };
    else if (n.type === 'server') {
      const idx = servers.indexOf(n);
      positions[n.id] = { x: startX + idx * serverSpacing, y: 290 };
    } else if (n.type === 'cache') positions[n.id] = { x: 0, y: 450 };
    else if (n.type === 'database') {
      const hasCache = nodes.some((nn) => nn.type === 'cache');
      positions[n.id] = { x: 0, y: hasCache ? 590 : 450 };
    }
  });

  // Single server: direct path
  const hasLB = nodes.some((n) => n.type === 'load_balancer');
  if (!hasLB) {
    nodes.forEach((n) => {
      if (n.type === 'server') positions[n.id] = { x: 0, y: 140 };
      else if (n.type === 'database') positions[n.id] = { x: 0, y: 290 };
    });
  }

  return positions;
}

//  Main Topology Component 

interface TopologyViewProps {
  topologyNodes: TopologyNode[];
  topologyEdges: TopologyEdge[];
}

export default function TopologyView({ topologyNodes, topologyEdges }: TopologyViewProps) {
  const positions = useMemo(() => computeLayout(topologyNodes), [topologyNodes.length]);

  const rfNodes: Node[] = useMemo(
    () =>
      topologyNodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: positions[n.id] ?? { x: 0, y: 0 },
        data: { ...n.data, label: n.label, status: n.status },
        draggable: false,
      })),
    [topologyNodes, positions]
  );

  const rfEdges: Edge[] = useMemo(
    () =>
      topologyEdges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        animated: e.active,
        style: {
          stroke: e.active ? '#ff3000' : '#000000',
          strokeWidth: e.active ? 2 : 1,
          opacity: e.active ? 1 : 0.3,
        },
        type: 'smoothstep',
      })),
    [topologyEdges]
  );

  return (
    <div className="w-full h-full rounded-xl overflow-hidden">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnScroll
      >
        <Background color="#1e293b" gap={24} size={1} />
        <Controls showInteractive={false} className="!bg-slate-800/80 !border-slate-600/50" />
      </ReactFlow>
    </div>
  );
}
