# Scenario definitions package
from .normal_traffic import NORMAL_TRAFFIC
from .high_traffic import HIGH_TRAFFIC
from .traffic_spike import TRAFFIC_SPIKE
from .server_failure import SERVER_FAILURE
from .auto_scaling_event import AUTO_SCALING_EVENT
from .database_slowdown import DATABASE_SLOWDOWN

ALL_SCENARIOS = {
    "normal_traffic": NORMAL_TRAFFIC,
    "high_traffic": HIGH_TRAFFIC,
    "traffic_spike": TRAFFIC_SPIKE,
    "server_failure": SERVER_FAILURE,
    "auto_scaling_event": AUTO_SCALING_EVENT,
    "database_slowdown": DATABASE_SLOWDOWN,
}

__all__ = [
    "NORMAL_TRAFFIC",
    "HIGH_TRAFFIC",
    "TRAFFIC_SPIKE",
    "SERVER_FAILURE",
    "AUTO_SCALING_EVENT",
    "DATABASE_SLOWDOWN",
    "ALL_SCENARIOS",
]
