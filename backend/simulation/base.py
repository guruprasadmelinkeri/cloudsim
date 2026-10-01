"""
Base simulation components and engine.
Defines foundational models, load balancing, metrics tracking, and base simulation lifecycle.

Member 3: BaseSimulation, Server, LoadBalancer (SimPy engine core)
Member 4: MetricsCollector (telemetry & analytics)
"""

import simpy
import random
from typing import Dict, List, Optional, Tuple, Any
from abc import ABC, abstractmethod


# ── Server Model ─────────────────────────────────────────────────────────────

class Server:
    """
    Simulated server resource.
    capacity = max concurrent requests (requests above this are dropped).
    """

    def __init__(self, env: simpy.Environment, server_id: str, capacity: int):
        self.env = env
        self.id = server_id
        self.capacity = capacity
        self.resource = simpy.Resource(env, capacity=capacity)
        self.active_requests: int = 0
        self.total_requests: int = 0
        self.failed_requests: int = 0
        self.failed: bool = False
        self.is_new: bool = False       # True for servers added by auto-scaling

    @property
    def cpu_utilization(self) -> float:
        """CPU % estimated from active requests vs capacity."""
        return min(100.0, (self.active_requests / self.capacity) * 100.0)

    def to_dict(self) -> dict:
        status = "failed" if self.failed else ("new" if self.is_new else "healthy")
        return {
            "id": self.id,
            "cpu": round(self.cpu_utilization, 1),
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "failed": self.failed,
            "status": status,
        }


# ── Load Balancer ─────────────────────────────────────────────────────────────

class LoadBalancer:
    """
    Load balancer implementing Round Robin and Least Connections.
    """

    def __init__(self, algorithm: str = "round_robin"):
        self.algorithm = algorithm
        self._rr_index: int = 0

    def select(self, servers: List[Server]) -> Optional[Server]:
        """Return the best healthy server or None if all are down."""
        healthy = [s for s in servers if not s.failed]
        if not healthy:
            return None

        if self.algorithm == "round_robin":
            server = healthy[self._rr_index % len(healthy)]
            self._rr_index = (self._rr_index + 1) % len(healthy)
            return server
        elif self.algorithm == "least_connections":
            return min(healthy, key=lambda s: s.active_requests)
        else:
            return healthy[0]


# ── Metrics Collector ─────────────────────────────────────────────────────────

class MetricsCollector:
    """
    Collects per-second snapshots, request statistics, and events.
    Member 4 responsibility.
    """

    def __init__(self):
        self.snapshots: List[dict] = []          # one entry per simulated second
        self.events: List[dict] = []             # notable events

        # running counters
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.dropped_requests: int = 0
        self.response_times: List[float] = []    # ms
        self.queue_lengths: List[int] = []

    def record_request(self, response_time_ms: float, success: bool, dropped: bool = False):
        self.total_requests += 1
        if dropped:
            self.dropped_requests += 1
        elif success:
            self.successful_requests += 1
            self.response_times.append(response_time_ms)
        else:
            self.failed_requests += 1

    def record_event(self, time: float, event_type: str, title: str, description: str, severity: str):
        self.events.append({
            "time": round(time, 2),
            "type": event_type,
            "title": title,
            "description": description,
            "severity": severity,
        })

    def snapshot(self, time: float, servers: List[Server], db_latency: float, db_status: str):
        """Record a snapshot of the system state at this point in time."""
        avg_rt = round(sum(self.response_times[-100:]) / max(len(self.response_times[-100:]), 1), 2)
        max_rt = round(max(self.response_times[-100:]) if self.response_times else 0.0, 2)
        avg_cpu = round(
            sum(s.cpu_utilization for s in servers if not s.failed) / max(len([s for s in servers if not s.failed]), 1),
            1,
        )
        active_servers = len([s for s in servers if not s.failed])
        queue_len = sum(max(0, s.active_requests - s.capacity) for s in servers)
        error_rate = round(
            (self.failed_requests + self.dropped_requests) / max(self.total_requests, 1) * 100, 2
        )
        throughput = round(self.successful_requests / max(time, 1), 2)

        snap = {
            "time": round(time, 1),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "dropped_requests": self.dropped_requests,
            "avg_response_time": avg_rt,
            "max_response_time": max_rt,
            "throughput": throughput,
            "queue_length": queue_len,
            "cpu_utilization": avg_cpu,
            "error_rate": error_rate,
            "active_servers": active_servers,
            "db_latency": db_latency,
            "db_status": db_status,
        }
        self.snapshots.append(snap)
        return snap


# ── Base Simulation Class ────────────────────────────────────────────────────

class BaseSimulation(ABC):
    """
    Abstract base class for all architecture-specific simulations.
    Provides SimPy environment orchestration, event monitoring, metrics collection,
    and life-cycle hooks for architecture specializations.
    Member 3 responsibility.
    """

    def __init__(self, arch_config: dict, scenario_config: dict):
        self.arch = arch_config
        self.scenario = scenario_config
        self.env = simpy.Environment()
        self.servers: List[Server] = []
        self.lb: Optional[LoadBalancer] = None
        self.metrics = MetricsCollector()
        self.db_latency: float = scenario_config["db_latency_ms"]
        self.db_status: str = "healthy"
        self._timeline_frames: List[dict] = []
        self._req_counter: int = 0
        self._last_snap_second: int = -1
        self._fired_events: set = set()
        self._fired_db_events: set = set()

    # ── Architecture-Specific Hooks ──────────────────────────────────────────

    @abstractmethod
    def _build_infrastructure(self):
        """Construct the servers, load balancers, caches, etc. for this architecture."""
        pass

    @abstractmethod
    def _select_server(self, req_id: str) -> Optional[Server]:
        """Route incoming request to an appropriate server, or return None if unavailable."""
        pass

    @abstractmethod
    def _build_topology(self) -> Tuple[List[dict], List[dict]]:
        """Return (nodes, edges) describing current architecture topology."""
        pass

    def _on_second_tick(self, t: float):
        """Hook called every second by monitor process (e.g. for autoscaling checks)."""
        pass

    def _calculate_db_latency(self, base_db_ms: float) -> float:
        """Allow architectures (like caching tiers) to adjust DB latency per request."""
        return base_db_ms

    # ── Request Processing ───────────────────────────────────────────────────

    def _process_request(self, req_id: str, server: Server):
        """
        SimPy process: simulates request traversing server and persistence tiers.

        FAILURE HANDLING:
        If the server fails mid-processing (i.e., server.failed becomes True
        during execution), the request is counted as failed rather than
        silently succeeding. This correctly drives up the error rate when a
        server failure event fires mid-flight.
        """
        arrival = self.env.now
        proc_ms = self.scenario["processing_time_ms"]
        net_ms = self.scenario["network_latency_ms"]
        db_ms, db_stat = self._get_db_latency(self.env.now)

        # Allow architecture specialization (e.g. cache hit)
        db_ms = self._calculate_db_latency(db_ms)

        total_delay_s = (net_ms + proc_ms + db_ms) / 1000.0

        server.active_requests += 1
        server.total_requests += 1

        # Yield for the full processing time
        yield self.env.timeout(total_delay_s)

        server.active_requests = max(0, server.active_requests - 1)

        # ── Critical Fix: check if server failed DURING processing ──
        if server.failed:
            # Server died mid-request → request fails
            server.failed_requests += 1
            self.metrics.record_request(0.0, success=False)
        else:
            response_time_ms = round((self.env.now - arrival) * 1000.0, 2)
            self.metrics.record_request(response_time_ms, success=True)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_traffic_rate(self, t: float) -> float:
        """Return requests/sec for the given simulation time."""
        for start, end, rps in self.scenario["traffic_phases"]:
            if start <= t < end:
                return rps
        return 0.0

    def _get_db_latency(self, t: float) -> Tuple[float, str]:
        """Return (latency_ms, status_string) considering slowdown events."""
        for ev in self.scenario.get("db_slowdown_events", []):
            if ev["start"] <= t < ev["end"]:
                return ev["slow_latency_ms"], "slow"
        return self.scenario["db_latency_ms"], "healthy"

    def _apply_failure_events(self, t: float):
        """
        Apply pre-configured failure/recovery events at the right simulation time.

        The server_id in failure_events is always pre-validated by get_scenario_for_arch()
        to match a server that exists in this architecture. If somehow the ID is not
        found (e.g., server was never created), we skip with a warning event.
        """
        for ev in self.scenario.get("failure_events", []):
            event_key = f"{ev['time']}_{ev['server_id']}_{ev['event']}"
            if event_key in self._fired_events:
                continue
            if abs(t - ev["time"]) <= 0.6:
                self._fired_events.add(event_key)
                target = next((s for s in self.servers if s.id == ev["server_id"]), None)

                if target is None:
                    # Server ID not found — record a diagnostic warning event
                    self.metrics.record_event(
                        t,
                        "warning",
                        f"⚠ Event Target Missing: {ev['server_id']}",
                        f"Failure event targeted {ev['server_id']} but it does not exist in this architecture.",
                        "warning",
                    )
                    continue

                if ev["event"] == "fail":
                    target.failed = True
                    # Any in-flight active_requests on this server will be counted as failed
                    # (handled in _process_request when it resumes after timeout)
                    healthy_after = [s for s in self.servers if not s.failed]
                    severity = "error"
                    if not healthy_after:
                        # Total outage — SPOF scenario (single server)
                        desc = (
                            f"{ev['server_id'].replace('_', ' ').title()} failed at {t:.1f}s. "
                            f"NO healthy servers remain — all requests will be dropped (SPOF)."
                        )
                        self.metrics.record_event(
                            t, "failure",
                            f"💀 TOTAL OUTAGE: {ev['server_id'].replace('_', ' ').title()} Failed",
                            desc, "error",
                        )
                    else:
                        desc = (
                            f"{ev['server_id'].replace('_', ' ').title()} failed at {t:.1f}s. "
                            f"{len(healthy_after)} server(s) remain — traffic rerouted."
                        )
                        self.metrics.record_event(
                            t, "failure",
                            f"⚠ Server Failure: {ev['server_id'].replace('_', ' ').title()}",
                            desc, severity,
                        )

                elif ev["event"] == "recover":
                    target.failed = False
                    target.active_requests = 0
                    self.metrics.record_event(
                        t,
                        "recovery",
                        f"✅ Server Recovery: {ev['server_id'].replace('_', ' ').title()}",
                        f"{ev['server_id'].replace('_', ' ').title()} recovered at {t:.1f}s "
                        f"and rejoined the pool.",
                        "success",
                    )

    def _apply_db_slowdown_events(self, t: float):
        """Fire DB slowdown events."""
        for ev in self.scenario.get("db_slowdown_events", []):
            start_key = f"db_slow_start_{ev['start']}"
            end_key = f"db_slow_end_{ev['end']}"

            if start_key not in self._fired_db_events and abs(t - ev["start"]) <= 0.6:
                self._fired_db_events.add(start_key)
                self.metrics.record_event(
                    t,
                    "db_slow",
                    "🟡 Database Slowdown",
                    f"Database latency increased from {self.scenario['db_latency_ms']}ms "
                    f"to {ev['slow_latency_ms']}ms at {t:.1f}s.",
                    "warning",
                )
            if end_key not in self._fired_db_events and abs(t - ev["end"]) <= 0.6:
                self._fired_db_events.add(end_key)
                self.metrics.record_event(
                    t,
                    "db_recover",
                    "🟢 Database Recovered",
                    f"Database latency returned to normal ({self.scenario['db_latency_ms']}ms) "
                    f"at {t:.1f}s.",
                    "success",
                )

    def _take_snapshot(self, t: float, events_at_t: List[dict]):
        """Record a full timeline frame at the given second."""
        db_ms, db_stat = self._get_db_latency(t)
        self.db_latency = db_ms
        self.db_status = db_stat
        snap = self.metrics.snapshot(t, self.servers, db_ms, db_stat)
        nodes, edges = self._build_topology()

        server_states = [s.to_dict() for s in self.servers]

        frame = {
            "time": round(t, 1),
            "servers": server_states,
            "metrics": snap,
            "events": events_at_t,
            "active_requests": sum(s.active_requests for s in self.servers),
            "db_status": db_stat,
            "topology_nodes": nodes,
            "topology_edges": edges,
        }
        self._timeline_frames.append(frame)

    def _request_generator(self):
        """
        Generates requests according to traffic phases.

        Key behavior:
        - If _select_server() returns None → ALL servers are down → request is dropped.
        - If selected server is already failed → request dropped (race condition guard).
        - Otherwise: spawn a _process_request coroutine which self-reports failure if
          the server fails mid-flight.
        """
        duration = self.scenario["duration"]
        while self.env.now < duration:
            rps = self._get_traffic_rate(self.env.now)
            if rps <= 0:
                yield self.env.timeout(0.1)
                continue

            interval = 1.0 / rps

            self._req_counter += 1
            req_id = f"REQ-{self._req_counter:05d}"

            server = self._select_server(req_id)

            if server is None:
                # All servers are down — hard drop
                self.metrics.record_request(0.0, success=False, dropped=True)
            elif server.failed:
                # Race: server just failed before request could be dispatched
                self.metrics.record_request(0.0, success=False, dropped=True)
            else:
                self.env.process(self._process_request(req_id, server))

            yield self.env.timeout(interval)

    def _monitor(self):
        """Runs every simulated second to collect metrics and fire events."""
        duration = self.scenario["duration"]
        self.metrics.record_event(
            0.0,
            "start",
            "🚀 Simulation Started",
            f"Running {self.scenario['label']} on {self.arch['label']} architecture.",
            "info",
        )

        snapped_event_indices: set = set()

        for second in range(duration + 1):
            t = float(second)
            self._apply_failure_events(t)
            self._apply_db_slowdown_events(t)
            self._on_second_tick(t)

            events_at_t = []
            for idx, e in enumerate(self.metrics.events):
                if idx not in snapped_event_indices and abs(e["time"] - t) < 0.7:
                    events_at_t.append(e)
                    snapped_event_indices.add(idx)

            self._take_snapshot(t, events_at_t)

            if second == duration:
                self.metrics.record_event(
                    t,
                    "end",
                    "🏁 Simulation Complete",
                    f"Simulation finished at {t:.0f}s.",
                    "info",
                )
            else:
                yield self.env.timeout(1.0)

    # ── Public Run Method ────────────────────────────────────────────────────

    def run(self) -> dict:
        """
        Run the full SimPy simulation and return the result dict.
        """
        self._build_infrastructure()

        self.env.process(self._request_generator())
        self.env.process(self._monitor())

        self.env.run(until=self.scenario["duration"] + 1.5)

        final_db_ms, final_db_stat = self._get_db_latency(self.scenario["duration"])
        final_metrics = self.metrics.snapshot(
            self.scenario["duration"], self.servers, final_db_ms, final_db_stat
        )

        self.metrics.record_event(
            float(self.scenario["duration"]),
            "end",
            "🏁 Simulation Complete",
            f"All {self.metrics.total_requests} requests processed.",
            "info",
        )

        nodes, edges = self._build_topology()

        return {
            "architecture": self.arch["id"],
            "scenario": self.scenario["id"],
            "duration": self.scenario["duration"],
            "architecture_label": self.arch["label"],
            "scenario_label": self.scenario["label"],
            "timeline": self._timeline_frames,
            "final_metrics": final_metrics,
            "all_events": self.metrics.events,
            "summary": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "dropped_requests": self.metrics.dropped_requests,
                "avg_response_time_ms": round(
                    sum(self.metrics.response_times) / max(len(self.metrics.response_times), 1), 2
                ),
                "max_response_time_ms": round(max(self.metrics.response_times or [0]), 2),
                "throughput": round(self.metrics.successful_requests / self.scenario["duration"], 2),
                "error_rate_pct": round(
                    (self.metrics.failed_requests + self.metrics.dropped_requests)
                    / max(self.metrics.total_requests, 1) * 100, 2
                ),
                "peak_servers": len(self.servers),
                "scaling_events": len([e for e in self.metrics.events if e["type"] == "auto_scale"]),
                "failure_events": len([e for e in self.metrics.events if e["type"] == "failure"]),
            },
        }
