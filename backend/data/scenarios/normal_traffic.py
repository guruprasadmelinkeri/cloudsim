"""
Normal Traffic Scenario — Member 2 (Scenario Definitions)
Steady-state baseline: 100 req/s for 30 seconds.
No failures, no slowdown, no scaling events.
"""

NORMAL_TRAFFIC = {
    "id": "normal_traffic",
    "label": "Normal Traffic",
    "description": "Steady 100 req/s for 30 seconds. Stable baseline scenario.",
    "duration": 30,
    # (start_sec, end_sec, requests_per_sec)
    "traffic_phases": [
        (0, 30, 100),
    ],
    # Base request characteristics (milliseconds) — overridden per-architecture in routes
    "processing_time_ms": 50,
    "network_latency_ms": 10,
    "db_latency_ms": 20,
    "failure_events": [],
    "db_slowdown_events": [],
}
