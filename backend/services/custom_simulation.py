"""Graph-driven SimPy runner kept completely separate from the legacy engine."""
from __future__ import annotations

from collections import defaultdict
import math
import random
import statistics
from typing import Any

import networkx as nx
import simpy

from models.custom_simulation import CustomDesign, SimulationConfig

LATENCY_MS = {
    "client": 0, "cdn": 2, "load_balancer": 1, "application_server": 25,
    "auto_scaling_group": 2, "api_gateway": 4, "cache": 1,
    "database": 18, "queue": 3, "storage": 25,
}
SUPPORTED_TYPES = set(LATENCY_MS)


def validate_simulation_design(design: CustomDesign) -> dict[str, Any]:
    ids = [node.id for node in design.components]
    if len(ids) != len(set(ids)):
        raise ValueError("Component IDs must be unique.")
    graph = nx.DiGraph()
    graph.add_nodes_from((node.id, {"type": node.type, "name": node.name}) for node in design.components)
    for edge in design.connections:
        if edge.source not in graph or edge.target not in graph:
            raise ValueError(f"Unsupported connection {edge.source} → {edge.target}: endpoint does not exist.")
        if edge.source == edge.target:
            raise ValueError(f"Unsupported self-connection on component {edge.source}.")
        if graph.has_edge(edge.source, edge.target):
            raise ValueError(f"Duplicate connection {edge.source} → {edge.target} is unsupported.")
        graph.add_edge(edge.source, edge.target)
    cyclic = not nx.is_directed_acyclic_graph(graph)
    if cyclic:
        raise ValueError("Cyclic request paths are unsupported; use a directed acyclic component graph.")
    clients = [node.id for node in design.components if node.type == "client"]
    if not clients:
        raise ValueError("Architecture needs at least one client/traffic-generator component.")
    reachable = set().union(*(nx.descendants(graph, client) | {client} for client in clients))
    sinks = [node for node in graph if graph.out_degree(node) == 0 and graph.nodes[node]["type"] != "client"]
    if not any(sink in reachable for sink in sinks):
        raise ValueError("No terminal component is reachable from a client.")
    disconnected = sorted(set(graph) - reachable)
    unsupported = []
    for node in design.components:
        invalid_numeric = set()
        for key in ("processing_capacity_rps", "max_concurrent", "processing_latency_ms", "network_latency_ms", "failure_probability", "instances", "count", "replicas", "max_instances", "max_queue_length", "scale_up_delay", "launch_delay", "hit_rate", "cache_hit_rate", "scale_up_threshold"):
            if key in node.config and not isinstance(node.config[key], (int, float)):
                unsupported.append(f"{node.id}.{key} must be numeric")
                invalid_numeric.add(key)
        for key in ("processing_capacity_rps", "max_concurrent", "instances", "count", "replicas", "max_instances"):
            if key in node.config and key not in invalid_numeric and float(node.config[key]) <= 0:
                unsupported.append(f"{node.id}.{key} must be greater than zero")
        for key in ("processing_latency_ms", "network_latency_ms", "max_queue_length", "scale_up_delay", "launch_delay"):
            if key in node.config and key not in invalid_numeric and float(node.config[key]) < 0:
                unsupported.append(f"{node.id}.{key} must be zero or greater")
        for key in ("failure_probability", "hit_rate", "cache_hit_rate"):
            if key in node.config and key not in invalid_numeric and not 0 <= float(node.config[key]) <= 1:
                unsupported.append(f"{node.id}.{key} must be between 0 and 1")
    if unsupported:
        raise ValueError("Unsupported configuration: " + "; ".join(unsupported))
    return {"graph": graph, "reachable": reachable, "disconnected": disconnected, "warnings": [f"Disconnected component '{node}' is excluded from request flow." for node in disconnected]}


class _Run:
    def __init__(self, design: CustomDesign, config: SimulationConfig, seed: int):
        validated = validate_simulation_design(design)
        self.design, self.config, self.graph = design, config, validated["graph"]
        self.warnings = validated["warnings"]
        self.env = simpy.Environment()
        self.seed = seed
        # Keep the load generator's random stream independent from component
        # cache/failure draws so compared designs receive identical arrivals.
        self.traffic_rng = random.Random(seed)
        self.rng = random.Random(seed ^ 0x5EED5EED)
        self.nodes = {node.id: node for node in design.components}
        self.sem = {}
        self.max_capacity = {}
        self.capacity = {}
        self.busy = defaultdict(int)
        self.waiting = defaultdict(int)
        self.busy_area = defaultdict(float)
        self.last_change = defaultdict(float)
        self.requests_at = defaultdict(int)
        self.service_latency = defaultdict(list)
        self.node_flow = defaultdict(int)
        self.cache_hits = defaultdict(int)
        self.cache_misses = defaultdict(int)
        self.is_down = defaultdict(bool)
        self.active_instances = {}
        self.rr = defaultdict(int)
        self.failed = self.dropped = self.incoming = self.successful = 0
        self.inflight = 0
        self.response_times = []
        self.failed_times = []
        self.events = []
        self.timeline = []
        self.previous_successful = 0
        self.last_response_index = 0
        self.last_db_latency_index = 0
        self.slowdown_until = 0
        self.db_requests = 0
        self.db_latency_samples = []
        self.scale_threshold = config.scaling_threshold
        self.last_scale = defaultdict(lambda: -9999)
        self.scale_pending = defaultdict(bool)
        self._initialize_resources()
        self._schedule_scenario()

    def _initialize_resources(self):
        for node in self.design.components:
            if node.type == "client":
                continue
            count = max(1, int(node.config.get("instances", node.config.get("count", node.config.get("replicas", 1)))))
            minimum = max(1, int(node.config.get("min_instances", 1)))
            count = max(count, minimum)
            maximum = max(count, int(node.config.get("max_instances", count)))
            concurrent = max(1, int(node.config.get("max_concurrent", node.config.get("concurrent_requests", 10))))
            cap = count * concurrent
            max_cap = maximum * concurrent
            self.active_instances[node.id] = count
            self.capacity[node.id] = cap
            self.max_capacity[node.id] = max_cap
            self.sem[node.id] = simpy.Container(self.env, capacity=max_cap, init=cap)

    def _event(self, kind: str, component: str | None, description: str):
        self.events.append({"time": round(float(self.env.now), 3), "type": kind, "component_id": component, "description": description})

    def _set_down(self, component: str, duration: float, cause: str = "scheduled failure"):
        self.is_down[component] = True
        self._event("failure", component, f"{cause}; recovery scheduled after {duration:g}s")
        yield self.env.timeout(duration)
        self.is_down[component] = False
        self._event("recovery", component, "Component recovered")

    def _schedule_scenario(self):
        cfg = self.config
        events = [item.model_dump() for item in cfg.failure_events]
        ids_by_type = lambda types: [n.id for n in self.design.components if n.type in types]
        if cfg.scenario in ("server_failure", "multiple_component_failures", "cache_failure") and not events:
            affected = list(cfg.affected_components)
            if cfg.scenario == "cache_failure" and not affected:
                affected = ids_by_type({"cache"})
            if cfg.scenario == "server_failure" and not affected:
                affected = ids_by_type({"application_server", "auto_scaling_group"})[:1]
                if not affected:
                    affected = ids_by_type({"load_balancer", "database"})[:1]
            if cfg.scenario == "multiple_component_failures" and not affected:
                affected = ids_by_type({"application_server", "database"})[:2]
            events.extend({"component_id": item, "start_time": cfg.failure_start_time + (i * 2 if cfg.failure_mode == "sequential" else 0), "recovery_time": cfg.recovery_time} for i, item in enumerate(affected))
        for event in events:
            if event["component_id"] not in self.graph:
                raise ValueError(f"Failure event references unsupported component '{event['component_id']}'.")
            self.env.process(self._scheduled_failure(event))
        if cfg.scenario == "database_slowdown":
            databases = ids_by_type({"database"})
            if not databases:
                raise ValueError("Database Slowdown scenario requires a database component.")
            self.env.process(self._database_slowdown(databases))
        if cfg.scenario == "network_latency":
            self._event("scenario", None, f"Additional network delay: {cfg.network_latency_ms:g}ms per connection")
        if cfg.scenario == "auto_scaling":
            self._event("scenario", None, "Autoscaling scenario enabled")
            for node in self.design.components:
                if node.type in {"application_server", "auto_scaling_group"}:
                    self.env.process(self._autoscaler(node.id))
        else:
            for node in self.design.components:
                if node.type == "auto_scaling_group" or (node.type == "application_server" and node.config.get("auto_scaling", False)):
                    self.env.process(self._autoscaler(node.id))

    def _scheduled_failure(self, event):
        yield self.env.timeout(event["start_time"])
        yield from self._set_down(event["component_id"], event["recovery_time"])

    def _database_slowdown(self, databases):
        yield self.env.timeout(self.config.failure_start_time)
        self.slowdown_until = self.env.now + self.config.database_slowdown_duration
        for db in databases:
            self._event("database_slowdown", db, f"Database latency raised to {self.config.database_latency_ms:g}ms; effective throughput reduced")
        yield self.env.timeout(self.config.database_slowdown_duration)
        self.slowdown_until = 0
        for db in databases:
            self._event("database_recovery", db, "Database slowdown ended")

    def _autoscaler(self, component_id):
        node = self.nodes[component_id]
        cfg = node.config
        threshold = float(cfg.get("scale_up_threshold", self.scale_threshold))
        threshold = threshold / 100 if threshold > 1 else threshold
        threshold = min(threshold, self.scale_threshold)
        min_instances = max(1, int(cfg.get("min_instances", self.active_instances[component_id])))
        max_instances = max(min_instances, int(cfg.get("max_instances", self.active_instances[component_id])))
        launch_delay = max(0, float(cfg.get("scale_up_delay", cfg.get("launch_delay", 2))))
        cooldown = max(self.config.scaling_cooldown, float(cfg.get("scaling_cooldown", 0)))
        while self.env.now < self.config.duration:
            yield self.env.timeout(1)
            cap = max(1, self.capacity[component_id])
            utilization = self.busy[component_id] / cap
            if utilization >= threshold and self.active_instances[component_id] < max_instances and not self.scale_pending[component_id] and self.env.now - self.last_scale[component_id] >= cooldown:
                self.scale_pending[component_id] = True
                self._event("scale_start", component_id, f"Utilization {utilization:.0%} reached threshold {threshold:.0%}")
                yield self.env.timeout(launch_delay)
                if self.active_instances[component_id] < max_instances:
                    increment = int(cfg.get("instances_per_scale", 1))
                    increment = min(max_instances - self.active_instances[component_id], max(1, increment))
                    per_instance = max(1, int(cfg.get("max_concurrent", cfg.get("concurrent_requests", 10))))
                    self._record_busy(component_id)
                    yield self.sem[component_id].put(increment * per_instance)
                    self.active_instances[component_id] += increment
                    self.capacity[component_id] += increment * per_instance
                    self._event("scale_complete", component_id, f"Provisioned {increment} instance(s); now {self.active_instances[component_id]}")
                self.last_scale[component_id] = self.env.now
                self.scale_pending[component_id] = False

    def _record_busy(self, component_id):
        now = float(self.env.now)
        cap = max(1, self.capacity.get(component_id, 1))
        self.busy_area[component_id] += max(0, now - self.last_change[component_id]) * self.busy[component_id] / cap
        self.last_change[component_id] = now

    def _rate_at(self, now):
        cfg = self.config
        pattern = cfg.traffic_pattern
        if cfg.scenario == "high_traffic":
            return cfg.peak_request_rate
        if cfg.scenario in {"traffic_spike", "auto_scaling"} or pattern == "spike":
            first = max(1, cfg.duration * .25)
            last = max(first + 1, cfg.duration * .65)
            return cfg.peak_request_rate if first <= now < last else cfg.initial_request_rate
        if pattern == "ramp":
            return cfg.initial_request_rate + (cfg.peak_request_rate - cfg.initial_request_rate) * min(1, now / max(1, cfg.duration))
        if pattern == "wave":
            return cfg.initial_request_rate + (cfg.peak_request_rate - cfg.initial_request_rate) * (0.5 + 0.5 * math.sin(now * 2 * math.pi / max(1, cfg.duration / 2)))
        return cfg.initial_request_rate

    def _traffic(self):
        clients = [node.id for node in self.design.components if node.type == "client"]
        request_no = 0
        while self.env.now < self.config.duration and request_no < self.config.max_requests:
            rate = max(.01, self._rate_at(self.env.now))
            yield self.env.timeout(self.traffic_rng.expovariate(rate))
            if self.env.now >= self.config.duration:
                break
            request_no += 1
            self.incoming += 1
            self.inflight += 1
            root = clients[(request_no - 1) % len(clients)]
            self.node_flow[root] += 1
            self.env.process(self._serve_request(root, self.env.now))
        if request_no >= self.config.max_requests:
            self._event("request_limit", None, f"Traffic generator reached max_requests={self.config.max_requests}")

    def _network_delay(self, source, target):
        target_cfg = self.nodes[target].config
        latency = float(target_cfg.get("network_latency_ms", 1))
        if self.config.scenario == "network_latency":
            latency += self.config.network_latency_ms
        yield self.env.timeout(max(0, latency) / 1000)

    def _follow_edge(self, source, target, started, state, path):
        yield from self._network_delay(source, target)
        yield self.env.process(self._request(target, started, state, path))

    def _serve_request(self, root, started):
        state = {"failed": False, "dropped": False}
        yield self.env.process(self._request(root, started, state, set()))
        self.inflight = max(0, self.inflight - 1)
        if state["dropped"]:
            self.dropped += 1
        elif state["failed"]:
            self.failed += 1
        else:
            self.successful += 1
            self.response_times.append((self.env.now - started) * 1000)

    def _request(self, component_id, started, state, path):
        if component_id in path:
            state["failed"] = True
            return
        path = path | {component_id}
        node = self.nodes[component_id]
        if self.is_down[component_id]:
            state["failed"] = True
            return
        if self.rng.random() < float(node.config.get("failure_probability", 0)):
            recovery = max(.1, float(node.config.get("recovery_time", 5)))
            if not self.is_down[component_id]:
                self.env.process(self._set_down(component_id, recovery, "random component failure"))
            state["failed"] = True
            return
        cache_hit = False
        if node.type in {"cdn", "cache"}:
            hit_rate = max(0, min(1, float(node.config.get("hit_rate", node.config.get("cache_hit_rate", .7 if node.type == "cache" else .8)))))
            if self.rng.random() < hit_rate:
                self.cache_hits[component_id] += 1
                cache_hit = True
            else:
                self.cache_misses[component_id] += 1
        if node.type != "client":
            semaphore = self.sem[component_id]
            hold_for_children = node.type in {"application_server", "auto_scaling_group", "api_gateway", "load_balancer", "queue"}
            queue_limit = max(0, int(node.config.get("max_queue_length", 1000)))
            if semaphore.level < 1 and self.waiting[component_id] >= queue_limit:
                state["dropped"] = True
                self._event("drop", component_id, "Component queue limit reached")
                return
            if semaphore.level < 1:
                self.waiting[component_id] += 1
            yield semaphore.get(1)
            self.waiting[component_id] = max(0, self.waiting[component_id] - 1)
            if self.is_down[component_id]:
                yield semaphore.put(1)
                state["failed"] = True
                return
            self._record_busy(component_id)
            self.busy[component_id] += 1
            self.node_flow[component_id] += 1
            self.requests_at[component_id] += 1
            start_service = self.env.now
            config = node.config
            processing_ms = max(0, float(config.get("processing_latency_ms", config.get("latency_ms", LATENCY_MS[node.type]))))
            capacity_rps = max(.01, float(config.get("processing_capacity_rps", config.get("capacity_rps", 100))))
            processing_seconds = processing_ms / 1000 + 1 / capacity_rps
            if node.type == "database" and self.env.now < self.slowdown_until:
                processing_seconds += self.config.database_latency_ms / 1000
            yield self.env.timeout(processing_seconds)
            elapsed = self.env.now - start_service
            self.service_latency[component_id].append(elapsed * 1000)
            if node.type == "database":
                self.db_requests += 1
                self.db_latency_samples.append(elapsed * 1000)
            self._record_busy(component_id)
            if not hold_for_children:
                self.busy[component_id] = max(0, self.busy[component_id] - 1)
                yield semaphore.put(1)
        if cache_hit:
            return
        children = list(self.graph.successors(component_id))
        if not children:
            if node.type != "client" and hold_for_children:
                self._record_busy(component_id)
                self.busy[component_id] = max(0, self.busy[component_id] - 1)
                yield self.sem[component_id].put(1)
            return
        if node.type in {"load_balancer", "api_gateway"}:
            algorithm = str(node.config.get("algorithm", node.config.get("lb_algorithm", "round_robin"))).lower()
            if algorithm in {"least_connections", "least_conn"}:
                child = min(children, key=lambda item: self.busy[item] + self.waiting[item])
            else:
                child = children[self.rr[component_id] % len(children)]
                self.rr[component_id] += 1
            children = [child]
        tasks = [self.env.process(self._follow_edge(component_id, child, started, state, path)) for child in children]
        if tasks:
            yield simpy.events.AllOf(self.env, tasks)
        if node.type != "client" and hold_for_children:
            self._record_busy(component_id)
            self.busy[component_id] = max(0, self.busy[component_id] - 1)
            yield self.sem[component_id].put(1)

    def _sample(self):
        while self.env.now < self.config.duration:
            yield self.env.timeout(1)
            self._record_snapshot()

    def _record_snapshot(self):
        utilization = {}
        for node_id in self.sem:
            cap = max(1, self.capacity[node_id])
            utilization[node_id] = round(min(1, self.busy[node_id] / cap), 4)
        completed_delta = self.successful - self.previous_successful
        self.previous_successful = self.successful
        new_responses = self.response_times[self.last_response_index:]
        self.last_response_index = len(self.response_times)
        new_database_samples = self.db_latency_samples[self.last_db_latency_index:]
        self.last_db_latency_index = len(self.db_latency_samples)
        self.timeline.append({
            "time": round(float(self.env.now), 2), "incoming": self.incoming,
            "successful": self.successful, "failed": self.failed, "dropped": self.dropped,
            "queue_length": sum(self.waiting.values()), "utilization": utilization,
            "active_instances": dict(self.active_instances), "component_status": {n: "down" if self.is_down[n] else "healthy" for n in self.graph},
            "throughput_rps": completed_delta,
            "average_response_ms": round(statistics.fmean(new_responses), 3) if new_responses else 0,
            "error_rate": round((self.failed + self.dropped) / max(1, self.incoming), 4),
            "active_servers": sum(self.active_instances.get(node.id, 0) for node in self.design.components if node.type in {"application_server", "auto_scaling_group"}),
            "database_latency_ms": round(statistics.fmean(new_database_samples), 3) if new_database_samples else 0,
            "component_requests": dict(self.node_flow),
        })

    def run(self):
        self.env.process(self._traffic())
        self.env.process(self._sample())
        self.env.run(until=self.config.duration)
        # A request still in flight at the simulation horizon is reported as dropped,
        # ensuring the request accounting identity remains exact.
        self.dropped += self.inflight
        self.inflight = 0
        self._record_snapshot()
        total = self.incoming
        sorted_latencies = sorted(self.response_times)
        def percentile(p):
            if not sorted_latencies:
                return 0.0
            return round(sorted_latencies[min(len(sorted_latencies) - 1, math.ceil(p * len(sorted_latencies)) - 1)], 3)
        component_utilization = {}
        for node_id in self.sem:
            self._record_busy(node_id)
            component_utilization[node_id] = round(self.busy_area[node_id] / max(1, self.config.duration), 4)
        metrics = {
            "total_incoming": total, "successful": self.successful, "failed": self.failed,
            "dropped": self.dropped, "throughput_rps": round(self.successful / max(1, self.config.duration), 3),
            "average_response_ms": round(statistics.fmean(self.response_times), 3) if self.response_times else 0,
            "maximum_response_ms": round(max(self.response_times), 3) if self.response_times else 0,
            "p95_response_ms": percentile(.95), "p99_response_ms": percentile(.99),
            "error_rate": round((self.failed + self.dropped) / max(1, total), 4),
            "average_queue_length": round(statistics.fmean([item["queue_length"] for item in self.timeline]), 3) if self.timeline else 0,
            "peak_queue_length": max((item["queue_length"] for item in self.timeline), default=0),
            "component_utilization": component_utilization, "active_instances": dict(self.active_instances),
            "cache_hits": dict(self.cache_hits), "cache_misses": dict(self.cache_misses),
            "database_requests": self.db_requests,
            "database_average_latency_ms": round(statistics.fmean(self.db_latency_samples), 3) if self.db_latency_samples else 0,
            "component_requests": dict(self.node_flow),
        }
        return {"architecture": self.design.name, "scenario": self.config.model_dump(), "seed": self.seed, "metrics": metrics, "timeline": self.timeline, "events": sorted(self.events, key=lambda event: event["time"]), "warnings": self.warnings, "assumptions": ["Every directed outgoing edge of an ordinary component is treated as a required parallel dependency; load balancers and API gateways choose one child.", "Processing capacity is modeled as concurrent slots plus a per-request service delay; provider-specific protocol behavior is outside this model.", "Requests still in flight at the configured duration are counted as dropped at the horizon."], "component_config": {node.id: {"type": node.type, **node.config} for node in self.design.components}}


def run_custom_simulation(design: CustomDesign, config: SimulationConfig):
    """Run one or more deterministic-seed replications and return actual SimPy outputs."""
    runs = [_Run(design, config, config.seed + index).run() for index in range(config.repetitions)]
    metric_keys = ["total_incoming", "successful", "failed", "dropped", "throughput_rps", "average_response_ms", "maximum_response_ms", "p95_response_ms", "p99_response_ms", "error_rate", "average_queue_length", "peak_queue_length", "database_requests", "database_average_latency_ms"]
    aggregate = {key: round(statistics.fmean(run["metrics"][key] for run in runs), 3) for key in metric_keys}
    aggregate["component_utilization"] = {key: round(statistics.fmean(run["metrics"]["component_utilization"].get(key, 0) for run in runs), 4) for key in runs[0]["metrics"]["component_utilization"]}
    for key in ("cache_hits", "cache_misses", "active_instances"):
        aggregate[key] = {component: round(statistics.fmean(run["metrics"][key].get(component, 0) for run in runs), 3) for component in runs[0]["metrics"][key]}
    aggregate["component_requests"] = {key: round(statistics.fmean(run["metrics"]["component_requests"].get(key, 0) for run in runs), 3) for key in runs[0]["metrics"]["component_requests"]}
    return {**runs[0], "metrics": aggregate, "repetitions": config.repetitions, "individual_runs": [{"seed": run["seed"], "metrics": run["metrics"]} for run in runs]}
