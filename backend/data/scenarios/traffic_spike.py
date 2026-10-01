"""
Traffic Spike Scenario — Member 3 (Scenario Definitions)
Rapid traffic surge: 100 → 500 → 100 req/s.
Key demonstration scenario for auto-scaling elasticity.
"""

TRAFFIC_SPIKE = {
    "id": "traffic_spike",
    "label": "Traffic Spike",
    "description": "100→500→100 req/s spike. Key demo scenario for auto-scaling.",
    "duration": 30,
    "traffic_phases": [
        (0, 10, 100),
        (10, 20, 500),
        (20, 30, 100),
    ],
    "processing_time_ms": 50,
    "network_latency_ms": 10,
    "db_latency_ms": 20,
    "failure_events": [],
    "db_slowdown_events": [],
}
