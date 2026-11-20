'use client';

import { SimulationEvent } from '@/types';

interface EventTimelineProps {
  events: SimulationEvent[];
}

const severityConfig = {
  info: { dot: 'bg-blue-500', border: 'border-blue-500/30', text: 'text-blue-300', bg: 'bg-blue-900/20' },
  warning: { dot: 'bg-yellow-500', border: 'border-yellow-500/30', text: 'text-yellow-300', bg: 'bg-yellow-900/20' },
  error: { dot: 'bg-red-500 animate-pulse', border: 'border-red-500/30', text: 'text-red-300', bg: 'bg-red-900/20' },
  success: { dot: 'bg-emerald-500', border: 'border-emerald-500/30', text: 'text-emerald-300', bg: 'bg-emerald-900/20' },
};

export default function EventTimeline({ events }: EventTimelineProps) {
  const sorted = [...events].sort((a, b) => a.time - b.time);

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm">
      <h3 className="text-sm font-semibold text-slate-300 mb-3"> Event Timeline</h3>
      {sorted.length === 0 ? (
        <div className="text-slate-600 text-sm text-center py-4">
          No events yet. Run a simulation to see events.
        </div>
      ) : (
        <div className="flex flex-col gap-2 max-h-64 overflow-y-auto pr-1 scrollbar-thin">
          {sorted.map((ev, idx) => {
            const cfg = severityConfig[ev.severity] ?? severityConfig.info;
            return (
              <div
                key={idx}
                className={`flex gap-3 p-2.5 rounded-lg border ${cfg.border} ${cfg.bg} transition-all`}
              >
                {/* Time */}
                <div className="flex-shrink-0 flex flex-col items-center gap-1 pt-0.5">
                  <div className={`w-2.5 h-2.5 rounded-full ${cfg.dot}`} />
                  <span className="text-[10px] text-slate-500 font-mono">{ev.time.toFixed(1)}s</span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className={`text-xs font-semibold ${cfg.text} truncate`}>{ev.title}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">{ev.description}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
