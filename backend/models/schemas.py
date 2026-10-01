"""
Pydantic schemas for CloudArchSim API.
Member 2 responsibility: FastAPI & Architecture Model
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


# ── Request Models ──────────────────────────────────────────────────────────

class SimulationRequest(BaseModel):
    """User only selects architecture + scenario. Nothing else."""
    architecture: str   # e.g. "single_server", "load_balanced", "auto_scaling", "three_tier"
    scenario: str       # e.g. "normal_traffic", "high_traffic", "traffic_spike", ...


class CompareRequest(BaseModel):
    """Run the same scenario on two architectures and compare."""
    architecture_a: str
    architecture_b: str
    scenario: str


# ── Data Models ─────────────────────────────────────────────────────────────

class ServerState(BaseModel):
    id: str
    cpu: float
    active_requests: int
    total_requests: int
    failed: bool
    status: str  # "healthy" | "failed" | "new"


class TopologyNode(BaseModel):
    id: str
    type: str       # "client" | "load_balancer" | "server" | "cache" | "database"
    label: str
    status: str
    data: Dict[str, Any] = {}


class TopologyEdge(BaseModel):
    id: str
    source: str
    target: str
    active: bool = True


class MetricsSnapshot(BaseModel):
    """A metrics snapshot at a point in simulated time."""
    time: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    dropped_requests: int
    avg_response_time: float
    max_response_time: float
    throughput: float         # requests/sec
    queue_length: int
    cpu_utilization: float    # average across servers
    error_rate: float
    active_servers: int
    db_latency: float


class SimulationEvent(BaseModel):
    """A notable event that occurred during the simulation."""
    time: float
    type: str       # "start" | "failure" | "recovery" | "auto_scale" | "db_slow" | "db_recover" | "end"
    title: str
    description: str
    severity: str   # "info" | "warning" | "error" | "success"


class TimelineFrame(BaseModel):
    """A single frame of the replay timeline."""
    time: float
    servers: List[ServerState]
    metrics: MetricsSnapshot
    events: List[SimulationEvent]   # events that fired at this exact second
    active_requests: int
    db_status: str     # "healthy" | "slow"
    topology_nodes: List[TopologyNode]
    topology_edges: List[TopologyEdge]


class SimulationResult(BaseModel):
    """Full simulation result returned to the frontend for replay."""
    architecture: str
    scenario: str
    duration: int
    architecture_label: str
    scenario_label: str
    timeline: List[TimelineFrame]     # one frame per simulated second
    final_metrics: MetricsSnapshot
    all_events: List[SimulationEvent]
    summary: Dict[str, Any]


class CompareResult(BaseModel):
    architecture_a: str
    architecture_b: str
    scenario: str
    result_a: SimulationResult
    result_b: SimulationResult
