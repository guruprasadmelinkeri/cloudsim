"""
Single Server Architecture Simulation.
Member 1 responsibility.
Direct client-to-server-to-database routing without load balancing or caching.

SPOF Demo: In the server_failure scenario, server_1 (the only server) fails.
This results in a total outage window from 10s–20s — all requests are dropped.
The error rate spikes to 100% during the outage window, demonstrating the
Single Point of Failure (SPOF) weakness of this architecture.
"""

from typing import List, Optional, Tuple
from simulation.base import BaseSimulation, Server


class SingleServerSimulation(BaseSimulation):
    """
    Simulation implementation for a single server architecture.
    A solitary server handles all inbound requests directly.

    Architecture characteristics:
    - Highest processing latency (no load distribution, all work on one server)
    - No fault tolerance — server failure = total outage (SPOF)
    - Capacity: 10 concurrent requests; CPU saturates quickly under load
    """

    def _build_infrastructure(self):
        capacity = self.arch.get("server_capacity", 10)
        self.servers.append(Server(self.env, "server_1", capacity))

    def _select_server(self, req_id: str) -> Optional[Server]:
        """Return server_1 if healthy, None if failed (causes full drop)."""
        s = self.servers[0]
        if s.failed:
            return None  # Total outage — all requests dropped
        return s

    def _build_topology(self) -> Tuple[List[dict], List[dict]]:
        s = self.servers[0]
        nodes = [
            {
                "id": "client",
                "type": "client",
                "label": "CLIENT",
                "status": "healthy",
                "data": {},
            },
            {
                "id": s.id,
                "type": "server",
                "label": s.id.replace("_", " ").upper(),
                "status": "failed" if s.failed else "healthy",
                "data": {
                    "cpu": round(s.cpu_utilization, 1),
                    "active_requests": s.active_requests,
                    "total_requests": s.total_requests,
                    "failed_requests": s.failed_requests,
                },
            },
            {
                "id": "database",
                "type": "database",
                "label": "DATABASE",
                "status": self.db_status,
                "data": {"latency_ms": round(self.db_latency, 0)},
            },
        ]

        edges = [
            {
                "id": "client-server",
                "source": "client",
                "target": s.id,
                # Edge goes inactive when server fails (total outage)
                "active": not s.failed,
            },
            {
                "id": "server-db",
                "source": s.id,
                "target": "database",
                "active": not s.failed,
            },
        ]

        return nodes, edges
