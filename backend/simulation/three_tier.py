"""
Three-Tier Architecture Simulation.
Member 4 responsibility.
Multi-tier setup featuring load balancer, web/application servers, distributed cache, and database.

Architecture characteristics:
- Cache layer absorbs 60% of DB reads (cache_hit_rate=0.60, latency_reduction=80%)
- During DB slowdown, cached responses bypass the slow DB → much better avg latency
- Extra cache hop adds +4ms network cost vs load_balanced, offset by DB latency savings
"""

import random
from typing import List, Optional, Tuple
from simulation.base import BaseSimulation, Server, LoadBalancer


class ThreeTierSimulation(BaseSimulation):
    """
    Simulation implementation for a three-tier architecture with caching.
    A cache layer sits between application servers and the database to offload read traffic.
    """

    def __init__(self, arch_config: dict, scenario_config: dict):
        super().__init__(arch_config, scenario_config)
        self.cache_hit_rate = self.arch.get("cache_hit_rate", 0.60)
        self.cache_latency_reduction = self.arch.get("cache_latency_reduction", 0.80)

    def _build_infrastructure(self):
        n = self.arch.get("servers", 2)
        capacity = self.arch.get("server_capacity", 8)
        for i in range(1, n + 1):
            self.servers.append(Server(self.env, f"server_{i}", capacity))

        alg = self.arch.get("lb_algorithm") or "round_robin"
        self.lb = LoadBalancer(alg)

    def _select_server(self, req_id: str) -> Optional[Server]:
        if self.lb:
            return self.lb.select(self.servers)
        healthy = [s for s in self.servers if not s.failed]
        return healthy[0] if healthy else None

    def _calculate_db_latency(self, base_db_ms: float) -> float:
        """Apply cache hit latency reduction if cache hits."""
        if random.random() < self.cache_hit_rate:
            return base_db_ms * (1.0 - self.cache_latency_reduction)
        return base_db_ms

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
            "id": "cache",
            "type": "cache",
            "label": "CACHE",
            "status": "healthy",
            "data": {"hit_rate": f"{self.cache_hit_rate * 100:.0f}%"},
        })

        for s in self.servers:
            edges.append({
                "id": f"{s.id}-cache",
                "source": s.id,
                "target": "cache",
                "active": not s.failed,
            })

        nodes.append({
            "id": "database",
            "type": "database",
            "label": "DATABASE",
            "status": self.db_status,
            "data": {"latency_ms": round(self.db_latency, 0)},
        })

        edges.append({
            "id": "cache-db",
            "source": "cache",
            "target": "database",
            "active": True,
        })

        return nodes, edges
