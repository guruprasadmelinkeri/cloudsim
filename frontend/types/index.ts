// Types for CloudArchSim frontend
// Mirrors the backend Pydantic schemas

export interface Architecture {
  id: string;
  label: string;
  description: string;
  servers: number;
  has_load_balancer: boolean;
  has_cache: boolean;
  auto_scaling: boolean;
  lb_algorithm: string | null;
}

export interface Scenario {
  id: string;
  label: string;
  description: string;
  duration: number;
  traffic_phases: [number, number, number][];
  has_failures: boolean;
  has_db_slowdown: boolean;
}

export interface ServerState {
  id: string;
  cpu: number;
  active_requests: number;
  total_requests: number;
  failed_requests: number;
  failed: boolean;
  status: 'healthy' | 'failed' | 'new';
}

export interface MetricsSnapshot {
  time: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  dropped_requests: number;
  avg_response_time: number;
  max_response_time: number;
  throughput: number;
  queue_length: number;
  cpu_utilization: number;
  error_rate: number;
  active_servers: number;
  db_latency: number;
  db_status: string;
}

export interface SimulationEvent {
  time: number;
  type: string;
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'error' | 'success';
}

export interface TopologyNode {
  id: string;
  type: string;
  label: string;
  status: string;
  data: Record<string, unknown>;
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  active: boolean;
}

export interface TimelineFrame {
  time: number;
  servers: ServerState[];
  metrics: MetricsSnapshot;
  events: SimulationEvent[];
  active_requests: number;
  db_status: string;
  topology_nodes: TopologyNode[];
  topology_edges: TopologyEdge[];
}

export interface SimulationResult {
  architecture: string;
  scenario: string;
  duration: number;
  architecture_label: string;
  scenario_label: string;
  timeline: TimelineFrame[];
  final_metrics: MetricsSnapshot;
  all_events: SimulationEvent[];
  summary: {
    total_requests: number;
    successful_requests: number;
    failed_requests: number;
    dropped_requests: number;
    avg_response_time_ms: number;
    max_response_time_ms: number;
    throughput: number;
    error_rate_pct: number;
    peak_servers: number;
    scaling_events: number;
    failure_events: number;
  };
}

export interface CompareResult {
  architecture_a: string;
  architecture_b: string;
  scenario: string;
  result_a: SimulationResult;
  result_b: SimulationResult;
}
