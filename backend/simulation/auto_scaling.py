"""
Auto-Scaling Architecture Simulation.
Member 3 responsibility.
Monitors cluster load and dynamically provisions server instances when CPU exceeds threshold.

Architecture characteristics:
- Starts with 3 servers, expands up to 5 when avg CPU > 80%
- Uses Least Connections routing (smarter than Round Robin under load)
- In server_failure scenario, auto-scaler may compensate for lost capacity
"""

from typing import List, Optional, Tuple
from simulation.base import BaseSimulation, Server, LoadBalancer


class AutoScalingSimulation(BaseSimulation):
    """
    Simulation implementation for an auto-scaling cluster.
    Monitors average server CPU utilization and dynamically adds new server resources.
    """

    def _build_infrastructure(self):
        initial_servers = self.arch.get("servers", 3)
        capacity = self.arch.get("server_capacity", 5)
        for i in range(1, initial_servers + 1):
            self.servers.append(Server(self.env, f"server_{i}", capacity))

        alg = self.arch.get("lb_algorithm") or "least_connections"
        self.lb = LoadBalancer(alg)

    def _select_server(self, req_id: str) -> Optional[Server]:
        if self.lb:
            return self.lb.select(self.servers)
        healthy = [s for s in self.servers if not s.failed]
        return healthy[0] if healthy else None

    def _on_second_tick(self, t: float):
        self._check_autoscale()

    def _check_autoscale(self):
        """Checks cluster CPU every second and adds a server if threshold exceeded."""
        threshold = self.arch.get("scale_up_threshold", 80.0)
        max_servers = self.arch.get("max_servers", 5)
        healthy_servers = [s for s in self.servers if not s.failed]
        if not healthy_servers:
            return

        avg_cpu = sum(s.cpu_utilization for s in healthy_servers) / len(healthy_servers)

        if avg_cpu >= threshold and len(self.servers) < max_servers:
            new_id = f"server_{len(self.servers) + 1}"
            new_server = Server(self.env, new_id, self.arch["server_capacity"])
            new_server.is_new = True
            self.servers.append(new_server)
            self.metrics.record_event(
                self.env.now,
                "auto_scale",
                f"⚡ Auto Scaling: {new_id.replace('_', ' ').title()} Added",
                f"Average CPU exceeded {threshold:.0f}% ({avg_cpu:.1f}%). "
                f"{new_id.replace('_', ' ').title()} created and added to pool.",
                "success",
            )

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
