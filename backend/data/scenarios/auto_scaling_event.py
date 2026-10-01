"""
Auto Scaling Event Scenario — Member 3 (Scenario Definitions)
CPU > 80% triggers automatic server provisioning.
100→400→100 req/s ramp. Designed for auto_scaling architecture.
"""

AUTO_SCALING_EVENT = {
    "id": "auto_scaling_event",
    "label": "Auto Scaling Event",
    "description": "100→400→100 req/s. CPU > 80% triggers new server creation.",
    "duration": 30,
    "traffic_phases": [
        (0, 10, 100),
        (10, 20, 400),
        (20, 30, 100),
    ],
    "processing_time_ms": 50,
    "network_latency_ms": 10,
    "db_latency_ms": 20,
    "failure_events": [],
    "db_slowdown_events": [],
}
