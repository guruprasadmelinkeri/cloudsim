"""Validated inputs for the standalone custom-architecture SimPy adapter."""
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict, Field


class FailureEvent(BaseModel):
    component_id: str
    start_time: float = Field(ge=0)
    recovery_time: float = Field(gt=0, description="Seconds until the component recovers")


class SimComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: Literal[
        "client", "cdn", "load_balancer", "application_server", "auto_scaling_group",
        "api_gateway", "cache", "database", "queue", "storage"
    ]
    name: str
    config: dict[str, Any] = Field(default_factory=dict)


class SimConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    target: str


class CustomDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = None
    name: str = "Custom architecture"
    components: list[SimComponent] = Field(min_length=1, max_length=100)
    connections: list[SimConnection] = Field(max_length=300)


class SimulationConfig(BaseModel):
    scenario: Literal[
        "normal_traffic", "high_traffic", "traffic_spike", "server_failure",
        "database_slowdown", "auto_scaling", "network_latency", "cache_failure",
        "multiple_component_failures"
    ] = "normal_traffic"
    duration: int = Field(default=30, ge=1, le=600)
    initial_request_rate: float = Field(default=100, gt=0, le=5000)
    peak_request_rate: float = Field(default=500, gt=0, le=5000)
    traffic_pattern: Literal["stable", "ramp", "spike", "wave"] = "stable"
    failure_start_time: float = Field(default=10, ge=0)
    recovery_time: float = Field(default=10, gt=0)
    failure_mode: Literal["simultaneous", "sequential"] = "sequential"
    affected_components: list[str] = Field(default_factory=list, max_length=100)
    failure_events: list[FailureEvent] = Field(default_factory=list, max_length=100)
    database_slowdown_duration: float = Field(default=10, gt=0)
    database_latency_ms: float = Field(default=500, ge=0, le=60000)
    network_latency_ms: float = Field(default=100, ge=0, le=60000)
    scaling_threshold: float = Field(default=0.8, gt=0, le=1)
    scaling_cooldown: float = Field(default=5, ge=0)
    repetitions: int = Field(default=1, ge=1, le=10)
    seed: int = 7
    max_requests: int = Field(default=50000, ge=1, le=100000)


class RunSimulationRequest(BaseModel):
    design: CustomDesign
    config: SimulationConfig = Field(default_factory=SimulationConfig)


class CompareSimulationRequest(BaseModel):
    designs: list[CustomDesign] = Field(max_length=8)
    config: SimulationConfig = Field(default_factory=SimulationConfig)
    include_predefined: bool = False


class SimulationAnalysisRequest(BaseModel):
    design: CustomDesign
    config: SimulationConfig
    result: dict
