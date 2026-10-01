"""
Database Slowdown Scenario — Member 4 (Scenario Definitions)
DB latency spikes from baseline to 200ms between 15s-25s.
Demonstrates how Three-Tier caching absorbs DB pressure better than other architectures.
"""

DATABASE_SLOWDOWN = {
    "id": "database_slowdown",
    "label": "Database Slowdown",
    "description": "DB latency jumps from 20ms to 200ms at 15s, recovers at 25s.",
    "duration": 30,
    "traffic_phases": [
        (0, 30, 150),
    ],
    "processing_time_ms": 50,
    "network_latency_ms": 10,
    "db_latency_ms": 20,
    "failure_events": [],
    # DB slowdown event: latency spikes 10x during the window
    "db_slowdown_events": [
        {"start": 15.0, "end": 25.0, "slow_latency_ms": 200},
    ],
}
