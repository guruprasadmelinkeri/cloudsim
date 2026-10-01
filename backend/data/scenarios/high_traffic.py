"""
High Traffic Scenario — Member 2 (Scenario Definitions)
Sustained heavy load: 300 req/s for 30 seconds.
Tests capacity limits. Single server will saturate, multi-server handles it.
"""

HIGH_TRAFFIC = {
    "id": "high_traffic",
    "label": "High Traffic",
    "description": "Sustained 300 req/s for 30 seconds. Tests capacity limits.",
    "duration": 30,
    "traffic_phases": [
        (0, 30, 300),
    ],
    "processing_time_ms": 50,
    "network_latency_ms": 10,
    "db_latency_ms": 20,
    "failure_events": [],
    "db_slowdown_events": [],
}
