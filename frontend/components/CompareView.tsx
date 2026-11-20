'use client';

import { useState } from 'react';
import { compareArchitectures } from '@/lib/api';
import { CompareResult, SimulationResult } from '@/types';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
} from 'recharts';

const ARCHITECTURES = [
  { id: 'single_server', label: 'Single Server' },
  { id: 'load_balanced', label: 'Load Balanced' },
  { id: 'auto_scaling', label: 'Auto Scaling' },
  { id: 'three_tier', label: 'Three Tier' },
];

const SCENARIOS = [
  { id: 'normal_traffic', label: 'Normal Traffic' },
  { id: 'high_traffic', label: 'High Traffic' },
  { id: 'traffic_spike', label: 'Traffic Spike' },
  { id: 'server_failure', label: 'Server Failure' },
  { id: 'auto_scaling_event', label: 'Auto Scaling Event' },
  { id: 'database_slowdown', label: 'Database Slowdown' },
];

const tooltipStyle = {
  backgroundColor: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#e2e8f0',
  fontSize: 12,
};

//  Winner Badge 
function WinnerBadge({ winner }: { winner: 'a' | 'b' | 'tie' }) {
  if (winner === 'tie') return <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-400">TIE</span>;
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
      winner === 'a' ? 'bg-indigo-900/60 text-indigo-300' : 'bg-violet-900/60 text-violet-300'
    }`}>
      {winner === 'a' ? ' A' : ' B'}
    </span>
  );
}

//  Summary Table 
function SummaryTable({ labelA, labelB, a, b }: { labelA: string; labelB: string; a: SimulationResult; b: SimulationResult }) {
  const rows: Array<{
    metric: string;
    aVal: number;
    bVal: number;
    aStr: string;
    bStr: string;
    higherIsBetter: boolean;
  }> = [
    {
      metric: 'Total Requests',
      aVal: a.summary.total_requests,
      bVal: b.summary.total_requests,
      aStr: a.summary.total_requests.toLocaleString(),
      bStr: b.summary.total_requests.toLocaleString(),
      higherIsBetter: true,
    },
    {
      metric: 'Successful',
      aVal: a.summary.successful_requests,
      bVal: b.summary.successful_requests,
      aStr: a.summary.successful_requests.toLocaleString(),
      bStr: b.summary.successful_requests.toLocaleString(),
      higherIsBetter: true,
    },
    {
      metric: 'Failed / Dropped',
      aVal: a.summary.failed_requests + a.summary.dropped_requests,
      bVal: b.summary.failed_requests + b.summary.dropped_requests,
      aStr: (a.summary.failed_requests + a.summary.dropped_requests).toLocaleString(),
      bStr: (b.summary.failed_requests + b.summary.dropped_requests).toLocaleString(),
      higherIsBetter: false,
    },
    {
      metric: 'Avg Response (ms)',
      aVal: a.summary.avg_response_time_ms,
      bVal: b.summary.avg_response_time_ms,
      aStr: a.summary.avg_response_time_ms.toFixed(1),
      bStr: b.summary.avg_response_time_ms.toFixed(1),
      higherIsBetter: false,
    },
    {
      metric: 'Max Response (ms)',
      aVal: a.summary.max_response_time_ms,
      bVal: b.summary.max_response_time_ms,
      aStr: a.summary.max_response_time_ms.toFixed(1),
      bStr: b.summary.max_response_time_ms.toFixed(1),
      higherIsBetter: false,
    },
    {
      metric: 'Throughput (req/s)',
      aVal: a.summary.throughput,
      bVal: b.summary.throughput,
      aStr: a.summary.throughput.toFixed(1),
      bStr: b.summary.throughput.toFixed(1),
      higherIsBetter: true,
    },
    {
      metric: 'Error Rate (%)',
      aVal: a.summary.error_rate_pct,
      bVal: b.summary.error_rate_pct,
      aStr: a.summary.error_rate_pct.toFixed(2),
      bStr: b.summary.error_rate_pct.toFixed(2),
      higherIsBetter: false,
    },
    {
      metric: 'Peak Servers',
      aVal: a.summary.peak_servers,
      bVal: b.summary.peak_servers,
      aStr: a.summary.peak_servers.toString(),
      bStr: b.summary.peak_servers.toString(),
      higherIsBetter: true,
    },
    {
      metric: 'Scaling Events',
      aVal: a.summary.scaling_events,
      bVal: b.summary.scaling_events,
      aStr: a.summary.scaling_events.toString(),
      bStr: b.summary.scaling_events.toString(),
      higherIsBetter: true,
    },
    {
      metric: 'Failure Events',
      aVal: a.summary.failure_events,
      bVal: b.summary.failure_events,
      aStr: a.summary.failure_events.toString(),
      bStr: b.summary.failure_events.toString(),
      higherIsBetter: false,
    },
  ];

  const getWinner = (aVal: number, bVal: number, higherIsBetter: boolean): 'a' | 'b' | 'tie' => {
    if (Math.abs(aVal - bVal) < 0.001) return 'tie';
    const aBetter = higherIsBetter ? aVal > bVal : aVal < bVal;
    return aBetter ? 'a' : 'b';
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/50">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700/50 bg-slate-800/80">
            <th className="text-left px-4 py-3 text-slate-400 font-medium">Metric</th>
            <th className="text-right px-4 py-3 text-indigo-300 font-semibold">{labelA}</th>
            <th className="text-right px-4 py-3 text-violet-300 font-semibold">{labelB}</th>
            <th className="text-center px-4 py-3 text-slate-500 font-medium text-xs">Winner</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const winner = getWinner(row.aVal, row.bVal, row.higherIsBetter);
            return (
              <tr
                key={row.metric}
                className={`border-b border-slate-700/30 ${i % 2 === 0 ? 'bg-slate-800/30' : 'bg-slate-800/10'}`}
              >
                <td className="px-4 py-2.5 text-slate-300">{row.metric}</td>
                <td className={`px-4 py-2.5 text-right font-mono ${winner === 'a' ? 'text-indigo-300 font-bold' : 'text-slate-400'}`}>
                  {row.aStr}
                </td>
                <td className={`px-4 py-2.5 text-right font-mono ${winner === 'b' ? 'text-violet-300 font-bold' : 'text-slate-400'}`}>
                  {row.bStr}
                </td>
                <td className="px-4 py-2.5 text-center">
                  <WinnerBadge winner={winner} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

//  Scorecard 
function Scorecard({ labelA, labelB, a, b }: { labelA: string; labelB: string; a: SimulationResult; b: SimulationResult }) {
  const checks: Array<{ higherIsBetter: boolean; aVal: number; bVal: number }> = [
    { higherIsBetter: true, aVal: a.summary.successful_requests, bVal: b.summary.successful_requests },
    { higherIsBetter: false, aVal: a.summary.error_rate_pct, bVal: b.summary.error_rate_pct },
    { higherIsBetter: true, aVal: a.summary.throughput, bVal: b.summary.throughput },
    { higherIsBetter: false, aVal: a.summary.avg_response_time_ms, bVal: b.summary.avg_response_time_ms },
    { higherIsBetter: false, aVal: a.summary.max_response_time_ms, bVal: b.summary.max_response_time_ms },
  ];

  let aScore = 0, bScore = 0;
  for (const c of checks) {
    const diff = Math.abs(c.aVal - c.bVal);
    if (diff < 0.001) continue;
    const aBetter = c.higherIsBetter ? c.aVal > c.bVal : c.aVal < c.bVal;
    if (aBetter) aScore++; else bScore++;
  }

  const overallWinner = aScore > bScore ? 'A' : bScore > aScore ? 'B' : 'Tie';
  const label = overallWinner === 'A' ? labelA : overallWinner === 'B' ? labelB : 'Tie';
  const color = overallWinner === 'A' ? 'text-indigo-300' : overallWinner === 'B' ? 'text-violet-300' : 'text-slate-400';

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 flex items-center justify-between gap-4">
      <div>
        <div className="text-xs text-slate-500 uppercase tracking-widest mb-1">Overall Winner</div>
        <div className={`text-xl font-bold ${color}`}>{label}</div>
        <div className="text-xs text-slate-500 mt-0.5">{aScore} vs {bScore} criteria wins</div>
      </div>
      <div className="flex gap-6 text-center">
        <div>
          <div className="text-2xl font-bold text-indigo-300">{aScore}</div>
          <div className="text-xs text-slate-500 mt-0.5">{labelA}</div>
        </div>
        <div className="text-slate-600 self-center font-bold">vs</div>
        <div>
          <div className="text-2xl font-bold text-violet-300">{bScore}</div>
          <div className="text-xs text-slate-500 mt-0.5">{labelB}</div>
        </div>
      </div>
    </div>
  );
}

//  Main Compare View 
export default function CompareView() {
  const [archA, setArchA] = useState('single_server');
  const [archB, setArchB] = useState('load_balanced');
  const [scenario, setScenario] = useState('server_failure');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCompare = async () => {
    if (archA === archB) {
      setError('Please select two different architectures.');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await compareArchitectures(archA, archB, scenario);
      setResult(data);
    } catch (e) {
      setError('Comparison failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const labelA = ARCHITECTURES.find((a) => a.id === archA)?.label ?? archA;
  const labelB = ARCHITECTURES.find((a) => a.id === archB)?.label ?? archB;
  const scenarioLabel = SCENARIOS.find((s) => s.id === scenario)?.label ?? scenario;

  // Bar chart: key metrics side-by-side
  const barData = result
    ? [
        { name: 'Throughput\n(req/s)', a: result.result_a.summary.throughput, b: result.result_b.summary.throughput },
        { name: 'Avg Resp\n(ms)', a: result.result_a.summary.avg_response_time_ms, b: result.result_b.summary.avg_response_time_ms },
        { name: 'Error\nRate %', a: result.result_a.summary.error_rate_pct, b: result.result_b.summary.error_rate_pct },
        { name: 'Dropped\nReqs', a: result.result_a.summary.dropped_requests, b: result.result_b.summary.dropped_requests },
      ]
    : [];

  const selectClass =
    'bg-slate-800/80 border border-slate-600/50 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all';

  return (
    <div className="flex flex-col gap-6">
      {/*  Selector panel  */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5 backdrop-blur-sm">
        <h3 className="text-base font-semibold text-slate-200 mb-4"> Architecture Comparison</h3>
        <p className="text-xs text-slate-500 mb-4">
          Each architecture uses its own latency profile and failure targets, so results will genuinely differ.
          Try <span className="text-rose-400 font-medium">Server Failure</span> to see SPOF vs fault-tolerant contrast.
        </p>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Architecture A </label>
            <select value={archA} onChange={(e) => setArchA(e.target.value)} className={selectClass}>
              {ARCHITECTURES.map((a) => (
                <option key={a.id} value={a.id}>{a.label}</option>
              ))}
            </select>
          </div>
          <span className="text-slate-500 font-bold pb-1">vs</span>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Architecture B </label>
            <select value={archB} onChange={(e) => setArchB(e.target.value)} className={selectClass}>
              {ARCHITECTURES.map((a) => (
                <option key={a.id} value={a.id}>{a.label}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Scenario</label>
            <select value={scenario} onChange={(e) => setScenario(e.target.value)} className={selectClass}>
              {SCENARIOS.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleCompare}
            disabled={loading}
            className="px-5 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/20"
          >
            {loading ? 'COMPARING...' : 'COMPARE'}
          </button>
        </div>
        {error && <div className="mt-3 text-red-400 text-sm">{error}</div>}
      </div>

      {result && (
        <>
          {/*  Scorecard  */}
          <Scorecard labelA={labelA} labelB={labelB} a={result.result_a} b={result.result_b} />

          {/*  Summary table  */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5 backdrop-blur-sm">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">
               {labelA} vs {labelB}  {scenarioLabel}
            </h3>
            <SummaryTable labelA={labelA} labelB={labelB} a={result.result_a} b={result.result_b} />
          </div>

          {/*  Bar chart  */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5 backdrop-blur-sm">
            <h3 className="text-sm font-semibold text-slate-300 mb-3"> Visual Comparison</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} barCategoryGap="25%">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                  <Bar dataKey="a" name={labelA} fill="#000000" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="b" name={labelB} fill="#ff3000" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/*  Event summary  */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: labelA, result: result.result_a, color: 'indigo' },
              { label: labelB, result: result.result_b, color: 'violet' },
            ].map(({ label, result: r, color }) => (
              <div key={label} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm">
                <h4 className={`text-xs font-bold uppercase tracking-widest mb-3 text-${color}-300`}>
                  {label}  Events
                </h4>
                {r.all_events.filter(e => !['start', 'end'].includes(e.type)).length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No notable events during simulation.</p>
                ) : (
                  <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
                    {r.all_events
                      .filter(e => !['start', 'end'].includes(e.type))
                      .map((e, i) => (
                        <div key={i} className="flex gap-2 text-xs">
                          <span className="text-slate-500 font-mono shrink-0">{e.time.toFixed(1)}s</span>
                          <span className={
                            e.severity === 'error' ? 'text-red-400' :
                            e.severity === 'warning' ? 'text-amber-400' :
                            e.severity === 'success' ? 'text-emerald-400' : 'text-slate-400'
                          }>{e.title}</span>
                        </div>
                      ))
                    }
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
