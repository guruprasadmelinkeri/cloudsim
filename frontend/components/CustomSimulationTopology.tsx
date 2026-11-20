'use client';

import { useMemo } from 'react';
import ReactFlow, { Background, Controls, MiniMap, Handle, Position, Node, Edge, NodeProps } from 'reactflow';
import 'reactflow/dist/style.css';

type Design={components:{id:string;name:string;type:string}[];connections:{source:string;target:string}[]};
type Frame={component_status?:Record<string,string>;utilization?:Record<string,number>;active_instances?:Record<string,number>;component_requests?:Record<string,number>};
type SimulationNodeData={name:string;type:string;status:string;util:number;instances:number;requests:number};
function SimulationNode({data}:NodeProps<SimulationNodeData>){
 const failed=data.status==='down';
 return <div className={`min-w-36 rounded-xl border px-3 py-2 shadow-lg ${failed?'border-rose-500 bg-rose-950':'border-cyan-600 bg-slate-900'}`}>
  <Handle type="target" position={Position.Top}/><div className="text-[10px] uppercase text-cyan-300">{data.type.replaceAll('_',' ')}</div><div className="text-xs font-semibold">{failed?'':''} {data.name}</div>
  <div className="mt-1 text-[10px] text-slate-300">Util {(data.util*100).toFixed(0)}% · instances {data.instances}</div><div className="text-[9px] text-cyan-200">{data.requests} traversals</div><div className="h-1 bg-slate-700 mt-1 rounded"><div className={`h-full ${failed?'bg-rose-500':'bg-cyan-400'} rounded`} style={{width:`${Math.min(100,data.util*100)}%`}}/></div><Handle type="source" position={Position.Bottom}/>
 </div>
}
const nodeTypes={simulation:SimulationNode};
export default function CustomSimulationTopology({design,frame,playing}:{design:Design;frame?:Frame;playing:boolean}){
 const {nodes,edges}=useMemo(()=>{
  const nodes:Node<SimulationNodeData>[] = design.components.map((c,i)=>({id:c.id,type:'simulation',position:{x:(i%4)*210,y:Math.floor(i/4)*150},data:{name:c.name,type:c.type,status:frame?.component_status?.[c.id]||'healthy',util:frame?.utilization?.[c.id]||0,instances:frame?.active_instances?.[c.id]||0,requests:frame?.component_requests?.[c.id]||0}}));
  const edges:Edge[]=design.connections.map((e,i)=>({id:`${e.source}-${e.target}-${i}`,source:e.source,target:e.target,animated:playing&&Boolean(frame?.component_requests?.[e.target]),label:frame?`${frame.component_requests?.[e.target]||0} req`:undefined,labelStyle:{fill:'#000000',fontSize:10},style:{stroke:'#000000',strokeWidth:2}}));
  return {nodes,edges};
 },[design,frame,playing]);
 return <div className="h-[420px] rounded-xl overflow-hidden border border-slate-700"><ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView><Background color="#d0d0d0" gap={24}/><Controls/><MiniMap nodeColor={(node)=>node.data.status==='down'?'#f43f5e':'#0891b2'}/></ReactFlow></div>;
}
