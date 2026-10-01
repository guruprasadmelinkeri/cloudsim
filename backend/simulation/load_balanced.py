"""
Load Balanced Architecture Simulation.
Member 2 responsibility.
Distributes incoming requests across multiple backend servers using Round Robin.

Architecture characteristics:
- 3 servers, capacity 5 each; LB adds a small network hop (+4ms vs single server)
- server_2 fails in server_failure scenario; server_1 & server_3 absorb traffic
- Error rate spikes only for in-flight requests on the failing server (partial failure)
"""

from typing import List, Optional, Tuple
from simulation.base import BaseSimulation, Server, LoadBalancer


class LoadBalancedSimulation(BaseSimulation):
    """
    Simulation implementation for a load-balanced server pool architecture.
    A dedicated load balancer routes traffic across multiple healthy servers.
    """

    def _build_infrastructure(self):
        n = self.arch.get("servers", 3)
        capacity = self.arch.get("server_capacity", 5)
        for i in range(1, n + 1):
            self.servers.append(Server(self.env, f"server_{i}", capacity))

        alg = self.arch.get("lb_algorithm") or "round_robin"
        self.lb = LoadBalancer(alg)

    def _select_server(self, req_id: str) -> Optional[Server]:
        if self.lb:
            return self.lb.select(self.servers)
        healthy = [s for s in self.servers if not s.failed]
        return healthy[0] if healthy else None

    def _build_topology(self) -> Tuple[List[dict], List[dict]]:
        nodes = [
            {
                "id": "client",
                "type": "client",
                "label": "CLIENT",
                "status": "healthy",
                "data": {},
            },
            {
                "id": "lb",
                "type": "load_balancer",
                "label": "LOAD BALANCER",
                "status": "healthy",
                "data": {"algorithm": self.arch.get("lb_algorithm", "")},
            },
        ]

        edges = [
            {
                "id": "client-lb",
                "source": "client",
                "target": "lb",
                "active": True,
            }
        ]

        for s in self.servers:
            nodes.append({
                "id": s.id,
                "type": "server",
                "label": s.id.replace("_", " ").upper(),
                "status": "failed" if s.failed else ("new" if s.is_new else "healthy"),
                "data": {
                    "cpu": round(s.cpu_utilization, 1),
                    "active_requests": s.active_requests,
                    "total_requests": s.total_requests,
                    "failed_requests": s.failed_requests,
                },
            })
            edges.append({
                "id": f"lb-{s.id}",
                "source": "lb",
                "target": s.id,
                "active": not s.failed,
            })

        nodes.append({
            "id": "database",
            "type": "database",
            "label": "DATABASE",
            "status": self.db_status,
            "data": {"latency_ms": round(self.db_latency, 0)},
        })

        for s in self.servers:
            edges.append({
                "id": f"{s.id}-db",
                "source": s.id,
                "target": "database",
                "active": not s.failed,
            })

        return nodes, edges
