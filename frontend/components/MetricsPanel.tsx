'use client';

import { MetricsSnapshot } from '@/types';
import { Activity, Zap, Clock, Cpu, AlertTriangle, Server } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  icon: React.ReactNode;
  colorClass: string;
  subLabel?: string;
}

function MetricCard({ label, value, unit, icon, colorClass, subLabel }: MetricCardProps) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 flex flex-col gap-2 backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">{label}</span>
        <span className={`${colorClass}`}>{icon}</span>
      </div>
      <div className="flex items-end gap-1">
        <span className={`text-2xl font-bold ${colorClass}`}>{value}</span>
        {unit && <span className="text-slate-400 text-sm mb-0.5">{unit}</span>}
      </div>
      {subLabel && <span className="text-xs text-slate-500">{subLabel}</span>}
    </div>
  );
}

interface MetricsPanelProps {
  metrics: MetricsSnapshot | null;
  isRunning: boolean;
  currentTime: number;
  duration: number;
}

export default function MetricsPanel({ metrics, isRunning, currentTime, duration }: MetricsPanelProps) {
  const m = metrics;

  const cpuColor =
    !m ? 'text-slate-400'
    : m.cpu_utilization >= 80 ? 'text-red-400'
    : m.cpu_utilization >= 60 ? 'text-yellow-400'
    : 'text-emerald-400';

  const errorColor =
    !m ? 'text-slate-400'
    : m.error_rate > 10 ? 'text-red-400'
    : m.error_rate > 5 ? 'text-yellow-400'
    : 'text-emerald-400';

  const rtColor =
    !m ? 'text-slate-400'
    : m.avg_response_time > 300 ? 'text-red-400'
    : m.avg_response_time > 150 ? 'text-yellow-400'
    : 'text-emerald-400';

  return (
    <div className="flex flex-col gap-3">
      {/* Progress */}
      {(isRunning || currentTime > 0) && (
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3 backdrop-blur-sm">
          <div className="flex justify-between text-xs text-slate-400 mb-1.5">
            <span>{isRunning ? ' Simulating...' : ' Complete'}</span>
            <span>{currentTime.toFixed(0)}s / {duration}s</span>
          </div>
          <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, (currentTime / duration) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 gap-2">
        <MetricCard
          label="Throughput"
          value={m ? m.throughput.toFixed(1) : ''}
          unit="req/s"
          icon={<Activity size={16} />}
          colorClass="text-indigo-400"
        />
        <MetricCard
          label="Total Requests"
          value={m ? m.total_requests.toLocaleString() : ''}
          icon={<Zap size={16} />}
          colorClass="text-violet-400"
        />
        <MetricCard
          label="Avg Response"
          value={m ? m.avg_response_time.toFixed(1) : ''}
          unit="ms"
          icon={<Clock size={16} />}
          colorClass={rtColor}
        />
        <MetricCard
          label="CPU Util."
          value={m ? m.cpu_utilization.toFixed(1) : ''}
          unit="%"
          icon={<Cpu size={16} />}
          colorClass={cpuColor}
        />
        <MetricCard
          label="Error Rate"
          value={m ? m.error_rate.toFixed(1) : ''}
          unit="%"
          icon={<AlertTriangle size={16} />}
          colorClass={errorColor}
        />
        <MetricCard
          label="Active Servers"
          value={m ? m.active_servers : ''}
          icon={<Server size={16} />}
          colorClass="text-cyan-400"
          subLabel={m ? `Queue: ${m.queue_length}` : undefined}
        />
      </div>

      {/* DB Status */}
      {m && (
        <div
          className={`rounded-xl p-3 border text-xs font-medium flex items-center gap-2 ${
            m.db_status === 'slow'
              ? 'bg-yellow-900/30 border-yellow-600/40 text-yellow-300'
              : 'bg-teal-900/20 border-teal-600/30 text-teal-300'
          }`}
        >
          <span className="h-2 w-2 bg-current" aria-hidden="true" />
          <span>
            Database: {m.db_status === 'slow' ? 'SLOW' : 'Healthy'}  {m.db_latency}ms
          </span>
        </div>
      )}
    </div>
  );
}
