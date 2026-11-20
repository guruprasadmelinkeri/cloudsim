'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useState, useEffect, useRef, useCallback } from 'react';
import { getArchitectures, getScenarios, runSimulation } from '@/lib/api';
import {
  Architecture,
  Scenario,
  SimulationResult,
  TimelineFrame,
  MetricsSnapshot,
  SimulationEvent,
} from '@/types';
import MetricsPanel from '@/components/MetricsPanel';
import SimCharts from '@/components/SimCharts';
import EventTimeline from '@/components/EventTimeline';
import CompareView from '@/components/CompareView';
import { Play, BarChart2, GitCompare, Layers, Zap } from 'lucide-react';

// Dynamic import for React Flow (requires browser)
const TopologyView = dynamic(() => import('@/components/TopologyView'), { ssr: false });

//  Scenario Badge Colors 
const scenarioBadge: Record<string, string> = {
  normal_traffic: 'bg-emerald-900/40 border-emerald-600/40 text-emerald-300',
  high_traffic: 'bg-orange-900/40 border-orange-600/40 text-orange-300',
  traffic_spike: 'bg-red-900/40 border-red-600/40 text-red-300',
  server_failure: 'bg-rose-900/40 border-rose-600/40 text-rose-300',
  auto_scaling_event: 'bg-violet-900/40 border-violet-600/40 text-violet-300',
  database_slowdown: 'bg-yellow-900/40 border-yellow-600/40 text-yellow-300',
};

// Replay speed (ms per simulated second)
const REPLAY_MS = 400;

//  Main Dashboard 
export default function Home() {
  const [architectures, setArchitectures] = useState<Architecture[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedArch, setSelectedArch] = useState<string>('auto_scaling');
  const [selectedScenario, setSelectedScenario] = useState<string>('traffic_spike');
  const [isLoading, setIsLoading] = useState(false);
  const [isReplaying, setIsReplaying] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [currentFrame, setCurrentFrame] = useState<TimelineFrame | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [collectedMetrics, setCollectedMetrics] = useState<MetricsSnapshot[]>([]);
  const [collectedEvents, setCollectedEvents] = useState<SimulationEvent[]>([]);
  const [activeTab, setActiveTab] = useState<'simulate' | 'compare'>('simulate');
  const [error, setError] = useState<string | null>(null);
  const replayRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const frameIndexRef = useRef(0);

  // Load architectures and scenarios from backend
  useEffect(() => {
    getArchitectures()
      .then((d) => setArchitectures(d.architectures))
      .catch(() => {});
    getScenarios()
      .then((d) => setScenarios(d.scenarios))
      .catch(() => {});
  }, []);

  //  Replay logic 
  const stopReplay = useCallback(() => {
    if (replayRef.current) {
      clearTimeout(replayRef.current);
      replayRef.current = null;
    }
    setIsReplaying(false);
  }, []);

  const startReplay = useCallback((res: SimulationResult) => {
    stopReplay();
    frameIndexRef.current = 0;
    setCollectedMetrics([]);
    setCollectedEvents([]);
    setIsReplaying(true);

    const tick = () => {
      const idx = frameIndexRef.current;
      if (idx >= res.timeline.length) {
        setIsReplaying(false);
        return;
      }
      const frame = res.timeline[idx];
      setCurrentFrame(frame);
      setCurrentTime(frame.time);
      setCollectedMetrics((prev) => [...prev, frame.metrics]);
      if (frame.events.length > 0) {
        setCollectedEvents((prev) => [...prev, ...frame.events]);
      }
      frameIndexRef.current = idx + 1;
      replayRef.current = setTimeout(tick, REPLAY_MS);
    };

    tick();
  }, [stopReplay]);

  //  Run Simulation 
  const handleRun = async () => {
    if (!selectedArch || !selectedScenario) return;
    stopReplay();
    setIsLoading(true);
    setError(null);
    setResult(null);
    setCurrentFrame(null);
    setCurrentTime(0);
    setCollectedMetrics([]);
    setCollectedEvents([]);

    try {
      const data: SimulationResult = await runSimulation(selectedArch, selectedScenario);
      setResult(data);
      startReplay(data);
    } catch (e) {
      setError('Could not reach the backend. Make sure it is running at http://localhost:8000');
    } finally {
      setIsLoading(false);
    }
  };

  const duration = result?.duration ?? (scenarios.find((s) => s.id === selectedScenario)?.duration ?? 30);

  //  Default topology 
  const topologyNodes = currentFrame?.topology_nodes ?? [];
  const topologyEdges = currentFrame?.topology_edges ?? [];

  //  Render 
  return (
    <div className="min-h-screen bg-[#0a0f1e] text-slate-100 flex flex-col font-sans">
      {/*  Header  */}
      <header className="border-b border-slate-800/80 bg-[#0d1424]/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-screen-2xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Layers size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white leading-none">CloudArchSim</h1>
              <p className="text-[11px] text-slate-500 leading-none mt-0.5">
                Cloud Architecture Simulation &amp; Evaluation
              </p>
            </div>
          </div>

          <nav className="flex gap-1 bg-slate-800/50 rounded-lg p-1 border border-slate-700/50">
            <button
              onClick={() => setActiveTab('simulate')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'simulate'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BarChart2 size={13} /> Simulate
            </button>
            <button
              onClick={() => setActiveTab('compare')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'compare'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <GitCompare size={13} /> Compare
            </button>
          </nav>
          <Link href="/intelligence" className="ml-3 rounded-lg bg-violet-700/80 px-3 py-2 text-xs font-semibold text-white hover:bg-violet-600">Architecture Intelligence</Link>
        </div>
      </header>

      {activeTab === 'compare' ? (
        <main className="max-w-screen-2xl mx-auto w-full px-6 py-6">
          <CompareView />
        </main>
      ) : (
        <main className="max-w-screen-2xl mx-auto w-full px-6 py-4 flex flex-col gap-4 flex-1">
          <section className="swiss-grid-pattern border-4 border-black bg-[#f2f2f2] px-6 py-8 md:px-12 md:py-10">
            <div className="mb-3 text-xs font-bold tracking-[0.24em] text-[#ff3000]">01 / CLOUD SYSTEMS</div>
            <div className="grid gap-6 md:grid-cols-[7fr_5fr] md:items-end">
              <h2 className="max-w-4xl text-5xl font-black uppercase leading-[0.88] tracking-[-0.07em] md:text-7xl xl:text-8xl">
                Architecture under load.
              </h2>
              <p className="max-w-lg border-l-2 border-black pl-4 text-sm leading-relaxed text-neutral-700 md:ml-auto">
                Model cloud systems, observe live infrastructure behavior, and compare performance across scenarios.
              </p>
            </div>
          </section>
          {/*  Control Row  */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Scenarios */}
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                <Zap size={12} /> Scenario
              </h2>
              <div className="grid grid-cols-2 gap-2">
                {scenarios.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setSelectedScenario(s.id)}
                    className={`text-left p-2.5 rounded-lg border text-xs transition-all ${
                      selectedScenario === s.id
                        ? scenarioBadge[s.id] + ' ring-1 ring-current'
                        : 'bg-slate-800/50 border-slate-700/30 text-slate-400 hover:border-slate-600/50 hover:text-slate-300'
                    }`}
                  >
                    <div className="font-semibold text-[11px]">
                      {s.label}
                    </div>
                    <div className="text-[10px] mt-0.5 opacity-70 line-clamp-2">{s.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Architectures */}
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                <Layers size={12} /> Architecture
              </h2>
              <div className="grid grid-cols-1 gap-2">
                {architectures.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => setSelectedArch(a.id)}
                    className={`text-left p-3 rounded-lg border text-xs transition-all ${
                      selectedArch === a.id
                        ? 'bg-indigo-900/40 border-indigo-500/50 text-indigo-200 ring-1 ring-indigo-500/50'
                        : 'bg-slate-800/50 border-slate-700/30 text-slate-400 hover:border-slate-600/50 hover:text-slate-300'
                    }`}
                  >
                    <div className="font-semibold flex items-center gap-1.5">
                      {a.label}
                    </div>
                    <div className="text-[10px] mt-0.5 opacity-70 line-clamp-1">{a.description}</div>
                    <div className="flex gap-2 mt-1.5 flex-wrap">
                      {a.has_load_balancer && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-800/50 text-blue-300 border border-blue-700/30">LB</span>
                      )}
                      {a.has_cache && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-800/50 text-amber-300 border border-amber-700/30">CACHE</span>
                      )}
                      {a.auto_scaling && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-violet-800/50 text-violet-300 border border-violet-700/30">AUTO-SCALE</span>
                      )}
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400 border border-slate-600/30">
                        {a.servers} server{a.servers > 1 ? 's' : ''}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Run panel + Live metrics */}
            <div className="flex flex-col gap-3">
              {/* Run button */}
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm">
                <button
                  onClick={handleRun}
                  disabled={isLoading || isReplaying}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 active:scale-95 text-white font-bold text-sm tracking-wide transition-all disabled:opacity-60 disabled:cursor-not-allowed shadow-xl shadow-indigo-500/20 flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <span className="animate-spin inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
                      Running Simulation...
                    </>
                  ) : isReplaying ? (
                    <>
                      <Play size={15} /> Replaying...
                    </>
                  ) : (
                    <>
                      <Play size={15} /> RUN SIMULATION
                    </>
                  )}
                </button>
                {error && <div className="mt-2 text-red-400 text-xs">{error}</div>}
                {result && !isLoading && (
                  <div className="mt-2 text-[11px] text-slate-500 text-center">
                    {result.architecture_label} · {result.scenario_label} · {result.duration}s
                  </div>
                )}
              </div>

              {/* Live Metrics */}
              <MetricsPanel
                metrics={currentFrame?.metrics ?? null}
                isRunning={isReplaying}
                currentTime={currentTime}
                duration={duration}
              />
            </div>
          </div>

          {/*  Topology + Charts  */}
          <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
            {/* Topology */}
            <div className="xl:col-span-3 bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden backdrop-blur-sm" style={{ minHeight: 480 }}>
              <div className="px-4 py-2.5 border-b border-slate-700/50 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Network Topology
                </span>
                {currentFrame && (
                  <span className="text-xs text-indigo-400 font-mono">
                    t = {currentTime.toFixed(1)}s
                  </span>
                )}
              </div>
              <div style={{ height: 440 }}>
                <TopologyView
                  topologyNodes={topologyNodes}
                  topologyEdges={topologyEdges}
                />
              </div>
            </div>

            {/* Events */}
            <div className="xl:col-span-2 flex flex-col gap-3">
              <EventTimeline events={collectedEvents} />
              {/* Summary if complete */}
              {result && !isReplaying && (
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Final Summary</h3>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    {[
                      ['Total', result.summary.total_requests.toLocaleString()],
                      ['Success', result.summary.successful_requests.toLocaleString()],
                      ['Dropped', result.summary.dropped_requests.toLocaleString()],
                      ['Avg RT', `${result.summary.avg_response_time_ms.toFixed(1)}ms`],
                      ['Throughput', `${result.summary.throughput.toFixed(1)} r/s`],
                      ['Error %', `${result.summary.error_rate_pct.toFixed(2)}%`],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between py-0.5 border-b border-slate-700/20">
                        <span className="text-slate-500">{k}</span>
                        <span className="text-slate-200 font-medium">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/*  Charts  */}
          <SimCharts snapshots={collectedMetrics} />
        </main>
      )}
    </div>
  );
}
