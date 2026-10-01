"""
Predefined Architectures & Scenarios.
Member 2 responsibility: Architecture definitions & Scenario definitions.

All parameters are hardcoded — the user cannot modify them.

KEY DESIGN DECISIONS
──────────────────────────────────────────────────────────────────────────────
1. ARCHITECTURE-DIFFERENTIATED LATENCIES
   Each architecture has its own base processing_time_ms, network_latency_ms,
   and db_latency_ms that reflect real-world trade-offs:
     - Single Server  : highest processing cost (no parallelism)
     - Load Balanced  : network overhead of the extra LB hop
     - Auto Scaling   : same as load balanced (dynamic pool)
     - Three Tier     : higher network cost (extra cache hop) but DB latency
                        reduced by cache hit rate

2. ARCH-SPECIFIC FAILURE EVENTS
   The "server_failure" scenario must target a server that actually exists in
   the chosen architecture.  get_scenario_for_arch() clones the base scenario
   and rewrites failure_events to use the correct server_id.
     - single_server  → fails server_1  (total outage — SPOF demo)
     - load_balanced  → fails server_2  (partial; server_1 & server_3 survive)
     - auto_scaling   → fails server_2  (auto-scaler may compensate)
     - three_tier     → fails server_2  (server_1 stays up; cache absorbs some)
──────────────────────────────────────────────────────────────────────────────
"""

import copy

# ────────────────────────────────────────────────────────────────────────────
# ARCHITECTURE LATENCY PROFILES
# Realistic per-architecture base latency constants used by get_scenario_for_arch()
# ────────────────────────────────────────────────────────────────────────────

_ARCH_LATENCY = {
    #              proc_ms  net_ms  db_ms
    "single_server":  (70,     8,     25),   # higher proc: no load distribution
    "load_balanced":  (50,    14,     22),   # +LB network hop, moderate proc
    "auto_scaling":   (52,    14,     22),   # similar to LB; scaling reduces proc spikes
    "three_tier":     (48,    18,     22),   # +cache hop net cost; db_ms reduced by cache
}


# ────────────────────────────────────────────────────────────────────────────
# ARCHITECTURES
# ────────────────────────────────────────────────────────────────────────────

ARCHITECTURES = {
    "single_server": {
        "id": "single_server",
        "label": "Single Server",
        "description": "One server handles all requests directly. Simplest possible setup.",
        "servers": 1,
        "has_load_balancer": False,
        "has_cache": False,
        "auto_scaling": False,
        "max_servers": 1,
        "min_servers": 1,
        # capacity = max concurrent requests; CPU = (active/capacity)*100
        # With 100 rps and ~103ms avg latency: avg concurrent ≈ 10.3 → capacity=10 → CPU~100%
        "server_capacity": 10,
        "lb_algorithm": None,
        "cache_hit_rate": 0.0,
        "cache_latency_reduction": 0.0,
        # Which server to fail in server_failure scenario (only 1 server exists → SPOF)
        "failure_server_id": "server_1",
    },
    "load_balanced": {
        "id": "load_balanced",
        "label": "Load Balanced",
        "description": "A load balancer distributes requests across 3 servers using Round Robin.",
        "servers": 3,
        "has_load_balancer": True,
        "has_cache": False,
        "auto_scaling": False,
        "max_servers": 3,
        "min_servers": 3,
        # 100 rps / 3 servers = ~33 rps each; 33 * 0.086s ≈ 2.8 concurrent → cap=5 → CPU~57%
        "server_capacity": 5,
        "lb_algorithm": "round_robin",
        "cache_hit_rate": 0.0,
        "cache_latency_reduction": 0.0,
        # server_2 fails; server_1 & server_3 continue handling traffic
        "failure_server_id": "server_2",
    },
    "auto_scaling": {
        "id": "auto_scaling",
        "label": "Auto Scaling",
        "description": "Starts with 3 servers; automatically adds servers when CPU > 80%.",
        "servers": 3,
        "has_load_balancer": True,
        "has_cache": False,
        "auto_scaling": True,
        "max_servers": 5,
        "min_servers": 3,
        # 500 rps spike / 3 servers = ~167 rps each; 167 * 0.086s ≈ 14 concurrent → CPU > 100% → scale
        "server_capacity": 5,
        "lb_algorithm": "least_connections",
        "scale_up_threshold": 80.0,
        "cache_hit_rate": 0.0,
        "cache_latency_reduction": 0.0,
        # server_2 fails; auto-scaler may replace capacity automatically
        "failure_server_id": "server_2",
    },
    "three_tier": {
        "id": "three_tier",
        "label": "Three Tier",
        "description": "Load balancer → App servers → Cache → Database. Cache reduces DB load.",
        "servers": 2,
        "has_load_balancer": True,
        "has_cache": True,
        "auto_scaling": False,
        "max_servers": 2,
        "min_servers": 2,
        # 150 rps / 2 servers = 75 rps each; 75 * 0.088s ≈ 6.6 concurrent → cap=8 → CPU~82%
        "server_capacity": 8,
        "lb_algorithm": "round_robin",
        # 60% of DB requests served from cache (no DB delay for those)
        "cache_hit_rate": 0.60,
        "cache_latency_reduction": 0.80,  # cache serves in 20% of DB latency
        # server_2 fails; server_1 alone handles all traffic (may saturate)
        "failure_server_id": "server_2",
    },
}


# ────────────────────────────────────────────────────────────────────────────
# BASE SCENARIOS (templates — adapt via get_scenario_for_arch)
# ────────────────────────────────────────────────────────────────────────────

SCENARIOS = {
    "normal_traffic": {
        "id": "normal_traffic",
        "label": "Normal Traffic",
        "description": "Steady 100 req/s for 30 seconds. Stable baseline scenario.",
        "duration": 30,
        "traffic_phases": [(0, 30, 100)],
        "processing_time_ms": 50,
        "network_latency_ms": 10,
        "db_latency_ms": 20,
        "failure_events": [],
        "db_slowdown_events": [],
    },
    "high_traffic": {
        "id": "high_traffic",
        "label": "High Traffic",
        "description": "Sustained 300 req/s for 30 seconds. Tests capacity limits.",
        "duration": 30,
        "traffic_phases": [(0, 30, 300)],
        "processing_time_ms": 50,
        "network_latency_ms": 10,
        "db_latency_ms": 20,
        "failure_events": [],
        "db_slowdown_events": [],
    },
    "traffic_spike": {
        "id": "traffic_spike",
        "label": "Traffic Spike",
        "description": "100→500→100 req/s spike. Key demo scenario for auto-scaling.",
        "duration": 30,
        "traffic_phases": [(0, 10, 100), (10, 20, 500), (20, 30, 100)],
        "processing_time_ms": 50,
        "network_latency_ms": 10,
        "db_latency_ms": 20,
        "failure_events": [],
        "db_slowdown_events": [],
    },
    "server_failure": {
        "id": "server_failure",
        "label": "Server Failure",
        "description": "A server fails at 10s and recovers at 20s. Tests fault tolerance.",
        "duration": 30,
        "traffic_phases": [(0, 30, 200)],
        "processing_time_ms": 50,
        "network_latency_ms": 10,
        "db_latency_ms": 20,
        # NOTE: failure_events are adapted per-architecture by get_scenario_for_arch()
        # Template uses server_2 — single_server will be rewritten to server_1
        "failure_events": [
            {"time": 10.0, "server_id": "server_2", "event": "fail"},
            {"time": 20.0, "server_id": "server_2", "event": "recover"},
        ],
        "db_slowdown_events": [],
    },
    "auto_scaling_event": {
        "id": "auto_scaling_event",
        "label": "Auto Scaling Event",
        "description": "100→400→100 req/s. CPU > 80% triggers new server creation.",
        "duration": 30,
        "traffic_phases": [(0, 10, 100), (10, 20, 400), (20, 30, 100)],
        "processing_time_ms": 50,
        "network_latency_ms": 10,
        "db_latency_ms": 20,
        "failure_events": [],
        "db_slowdown_events": [],
    },
    "database_slowdown": {
        "id": "database_slowdown",
        "label": "Database Slowdown",
        "description": "DB latency jumps from 20ms to 200ms at 15s, recovers at 25s.",
        "duration": 30,
        "traffic_phases": [(0, 30, 150)],
        "processing_time_ms": 50,
        "network_latency_ms": 10,
        "db_latency_ms": 20,
        "failure_events": [],
        "db_slowdown_events": [
            {"start": 15.0, "end": 25.0, "slow_latency_ms": 200},
        ],
    },
}


# ────────────────────────────────────────────────────────────────────────────
# ADAPTER: build an arch-specific scenario copy
# ────────────────────────────────────────────────────────────────────────────

def get_scenario_for_arch(scenario_id: str, arch_id: str) -> dict:
    """
    Return a deep-copy of the base scenario adapted for the given architecture.

    Adaptations applied:
    1. Latency values (processing_time_ms, network_latency_ms, db_latency_ms)
       are replaced with architecture-specific constants so that each arch
       yields genuinely different performance numbers.

    2. failure_events server_id is rewritten to match the architecture's
       actual failure_server_id — preventing "server not found" silent no-ops.
       For single_server this means server_1 (total outage / SPOF demo).
    """
    base = SCENARIOS.get(scenario_id)
    if base is None:
        raise KeyError(f"Unknown scenario: {scenario_id}")

    arch = ARCHITECTURES.get(arch_id)
    if arch is None:
        raise KeyError(f"Unknown architecture: {arch_id}")

    scenario = copy.deepcopy(base)

    # 1. Apply architecture-differentiated latency profile
    proc_ms, net_ms, db_ms = _ARCH_LATENCY.get(arch_id, (50, 10, 20))
    scenario["processing_time_ms"] = proc_ms
    scenario["network_latency_ms"] = net_ms
    scenario["db_latency_ms"] = db_ms

    # Also update the baseline inside db_slowdown_events to match
    for ev in scenario.get("db_slowdown_events", []):
        # keep slow_latency_ms absolute (200ms spike is intentional regardless of arch)
        pass

    # 2. Rewrite failure_events to target the correct server for this arch
    target_server = arch.get("failure_server_id", "server_1")
    adapted_failures = []
    for ev in scenario.get("failure_events", []):
        ev_copy = dict(ev)
        ev_copy["server_id"] = target_server
        adapted_failures.append(ev_copy)
    scenario["failure_events"] = adapted_failures

    return scenario
