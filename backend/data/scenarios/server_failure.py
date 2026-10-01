"""
Server Failure Scenario — Member 1 (Scenario Definitions)
Tests fault tolerance: a server fails at 10s and recovers at 20s.

IMPORTANT: The failure_events list here contains a TEMPLATE — the actual
server_id is filled in per-architecture by the routes layer using
get_scenario_for_arch(), since each architecture has different server counts
and IDs. The template uses "server_2" as a placeholder which is valid for
all multi-server architectures. Single Server will have this adapted to
"server_1" which triggers total outage (SPOF demonstration).
"""

SERVER_FAILURE = {
    "id": "server_failure",
    "label": "Server Failure",
    "description": "A server fails at 10s and recovers at 20s. Tests fault tolerance.",
    "duration": 30,
    "traffic_phases": [
        (0, 30, 200),
    ],
    "processing_time_ms": 50,
    "network_latency_ms": 10,
    "db_latency_ms": 20,
    # Template failure events — routes.py adapts server_id per architecture
    "failure_events": [
        {"time": 10.0, "server_id": "server_2", "event": "fail"},
        {"time": 20.0, "server_id": "server_2", "event": "recover"},
    ],
    "db_slowdown_events": [],
}
