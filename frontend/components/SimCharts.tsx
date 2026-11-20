'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { MetricsSnapshot } from '@/types';

interface ChartsProps {
  snapshots: MetricsSnapshot[];
}

const CHART_STYLE = {
  background: 'transparent',
};

const tooltipStyle = {
  backgroundColor: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#e2e8f0',
  fontSize: 12,
};

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">{title}</h3>
      <div className="h-44">{children}</div>
    </div>
  );
}

export default function SimCharts({ snapshots }: ChartsProps) {
  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {['CPU Utilization', 'Response Time', 'Throughput', 'Queue Length'].map((t) => (
          <ChartCard key={t} title={t}>
            <div className="h-full flex items-center justify-center text-slate-600 text-sm">
              No data yet
            </div>
          </ChartCard>
        ))}
      </div>
    );
  }

  const data = snapshots.map((s) => ({
    time: s.time,
    cpu: parseFloat(s.cpu_utilization.toFixed(1)),
    responseTime: parseFloat(s.avg_response_time.toFixed(1)),
    throughput: parseFloat(s.throughput.toFixed(1)),
    queueLength: s.queue_length,
    dbLatency: parseFloat(s.db_latency.toFixed(1)),
    errorRate: parseFloat(s.error_rate.toFixed(2)),
  }));

  return (
    <div className="grid grid-cols-2 gap-3">
      <ChartCard title=" CPU Utilization (%)">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} style={CHART_STYLE}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}%`, 'CPU']} />
            <ReferenceLine y={80} stroke="#ef4444" strokeDasharray="4 4" label={{ value: '80% threshold', fill: '#ef4444', fontSize: 10 }} />
            <Line
              type="monotone"
              dataKey="cpu"
              stroke="#000000"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#000000' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title=" Avg Response Time (ms)">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} style={CHART_STYLE}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
            <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}ms`, 'Avg RT']} />
            <Line
              type="monotone"
              dataKey="responseTime"
              stroke="#ff3000"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#ff3000' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title=" Throughput (req/s)">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} style={CHART_STYLE}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
            <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v} req/s`, 'Throughput']} />
            <Line
              type="monotone"
              dataKey="throughput"
              stroke="#000000"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#000000' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title=" DB Latency (ms) & Queue">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} style={CHART_STYLE}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
            <YAxis yAxisId="left" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 10, color: '#94a3b8' }} />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="dbLatency"
              name="DB Latency (ms)"
              stroke="#000000"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#000000' }}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="queueLength"
              name="Queue"
              stroke="#ff3000"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#ff3000' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
