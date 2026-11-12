"""Routes for graph-driven custom SimPy simulation; legacy APIs are not touched."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from data.definitions import ARCHITECTURES
from models.custom_simulation import (
    CompareSimulationRequest, CustomDesign, RunSimulationRequest,
    SimulationAnalysisRequest,
)
from services.custom_simulation import run_custom_simulation, validate_simulation_design
from services.intelligence import estimate_cost, explain_simulation, optimize

router = APIRouter()


def _run(design, config):
    try:
        return run_custom_simulation(design, config)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/scenarios")
def scenarios():
    return {"scenarios": [
        {"id": "normal_traffic", "label": "Normal Traffic"},
        {"id": "high_traffic", "label": "High Traffic"},
        {"id": "traffic_spike", "label": "Traffic Spike"},
        {"id": "server_failure", "label": "Server Failure"},
        {"id": "database_slowdown", "label": "Database Slowdown"},
        {"id": "auto_scaling", "label": "Auto Scaling"},
        {"id": "network_latency", "label": "Network Latency"},
        {"id": "cache_failure", "label": "Cache Failure"},
        {"id": "multiple_component_failures", "label": "Multiple Component Failures"},
    ], "traffic_patterns": ["stable", "ramp", "spike", "wave"]}


@router.post("/run")
def run(request: RunSimulationRequest):
    if request.config.max_requests * request.config.repetitions > 500_000:
        raise HTTPException(422, "Run request budget exceeds 500,000 total requests; lower max_requests or repetitions.")
    return _run(request.design, request.config)


def _predefined_designs():
    result = []
    for key, architecture in ARCHITECTURES.items():
        components = [{"id": "client", "type": "client", "name": "Traffic Generator", "config": {}}]
        connections = []
        last = "client"
        if architecture["has_load_balancer"]:
            components.append({"id": "load-balancer", "type": "load_balancer", "name": "Load Balancer", "config": {"algorithm": architecture.get("lb_algorithm") or "round_robin"}})
            connections.append({"source": last, "target": "load-balancer"})
            last = "load-balancer"
        app_type = "auto_scaling_group" if architecture["auto_scaling"] else "application_server"
        components.append({"id": "app", "type": app_type, "name": architecture["label"] + " application servers", "config": {
            "instances": architecture["servers"], "min_instances": architecture["min_servers"],
            "max_instances": architecture["max_servers"], "max_concurrent": architecture["server_capacity"],
            "processing_latency_ms": 50, "auto_scaling": architecture["auto_scaling"],
            "scale_up_threshold": architecture.get("scale_up_threshold", 80), "launch_delay": 2,
        }})
        connections.append({"source": last, "target": "app"})
        last = "app"
        if architecture["has_cache"]:
            components.append({"id": "cache", "type": "cache", "name": "Cache", "config": {"hit_rate": .7, "max_concurrent": 50, "processing_latency_ms": 1}})
            connections.append({"source": last, "target": "cache"})
            last = "cache"
        components.append({"id": "database", "type": "database", "name": "Database", "config": {"max_concurrent": 20, "processing_latency_ms": 18}})
        connections.append({"source": last, "target": "database"})
        result.append(CustomDesign(id=key, name=architecture["label"], components=components, connections=connections))
    return result


@router.post("/compare")
def compare(request: CompareSimulationRequest):
    designs = list(request.designs)
    if request.include_predefined:
        designs.extend(_predefined_designs())
    if len(designs) < 2:
        raise HTTPException(422, "Choose at least two custom designs or include predefined strategies.")
    if len(designs) > 8:
        raise HTTPException(422, "A comparison can contain at most eight designs including predefined strategies.")
    if request.config.max_requests * request.config.repetitions * len(designs) > 500_000:
        raise HTTPException(422, "Comparison request budget exceeds 500,000 total requests; lower max_requests, repetitions or design count.")
    results = [_run(design, request.config) for design in designs]
    rows = [{"architecture": result["architecture"], "metrics": result["metrics"], "cost_estimate": estimate_cost(design), "scenario": result["scenario"], "events": result["events"], "timeline": result["timeline"], "warnings": result["warnings"]} for design, result in zip(designs, results)]
    best = min(rows, key=lambda row: (-row["metrics"]["throughput_rps"], row["metrics"]["error_rate"], row["metrics"]["p95_response_ms"]))
    return {"config": request.config.model_dump(), "comparisons": rows, "summary": f"{best['architecture']} delivered the highest simulated throughput ({best['metrics']['throughput_rps']} req/s), with P95 latency {best['metrics']['p95_response_ms']}ms and error fraction {best['metrics']['error_rate']}. Review the full comparison and illustrative cost before choosing; all numeric performance values come from the custom SimPy runs."}


@router.post("/analyze")
def analyze(request: SimulationAnalysisRequest):
    try:
        validate_simulation_design(request.design)
        explanation = explain_simulation(request.design, request.config, request.result)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"analysis": explanation, "measured_metrics": request.result.get("metrics", {}), "optimizer_suggestions": optimize(request.design), "disclaimer": "The metrics above are the engine output. Gemini supplies narrative only and cannot change or produce metric values."}
