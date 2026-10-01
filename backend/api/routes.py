"""
FastAPI route handlers — Member 2 responsibility.
Provides endpoints for architectures, scenarios, simulation, and comparison.

Updated: routes now call get_scenario_for_arch() to produce architecture-specific
scenario configs. This ensures:
  - Each architecture gets its own latency profile (different response times).
  - server_failure events always target a server that actually exists in the arch.
  - Compare endpoint uses arch-adapted scenarios for both sides.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from data.definitions import ARCHITECTURES, SCENARIOS, get_scenario_for_arch
from models.schemas import SimulationRequest, CompareRequest
from simulation.engine import CloudSimulation

router = APIRouter()


# ── GET /api/architectures ───────────────────────────────────────────────────

@router.get("/architectures")
def get_architectures():
    """Return all available predefined architectures."""
    result = []
    for key, arch in ARCHITECTURES.items():
        result.append({
            "id": arch["id"],
            "label": arch["label"],
            "description": arch["description"],
            "servers": arch["servers"],
            "has_load_balancer": arch["has_load_balancer"],
            "has_cache": arch["has_cache"],
            "auto_scaling": arch["auto_scaling"],
            "lb_algorithm": arch.get("lb_algorithm"),
        })
    return {"architectures": result}


# ── GET /api/scenarios ───────────────────────────────────────────────────────

@router.get("/scenarios")
def get_scenarios():
    """Return all predefined simulation scenarios."""
    result = []
    for key, sc in SCENARIOS.items():
        result.append({
            "id": sc["id"],
            "label": sc["label"],
            "description": sc["description"],
            "duration": sc["duration"],
            "traffic_phases": sc["traffic_phases"],
            "has_failures": len(sc.get("failure_events", [])) > 0,
            "has_db_slowdown": len(sc.get("db_slowdown_events", [])) > 0,
        })
    return {"scenarios": result}


# ── POST /api/simulate ───────────────────────────────────────────────────────

@router.post("/simulate")
def run_simulation(request: SimulationRequest):
    """
    Run a SimPy simulation for the given architecture + scenario.

    The scenario is adapted for the chosen architecture via get_scenario_for_arch():
      - Architecture-specific latency constants are applied (proc/net/db ms).
      - failure_events server_id is rewritten to match the arch's actual servers.
    """
    arch = ARCHITECTURES.get(request.architecture)
    if arch is None:
        raise HTTPException(status_code=400, detail=f"Unknown architecture: {request.architecture}")

    if request.scenario not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {request.scenario}")

    # Build architecture-specific scenario (different latencies + correct server IDs)
    scenario = get_scenario_for_arch(request.scenario, request.architecture)

    sim = CloudSimulation(arch, scenario)
    result = sim.run()
    return result


# ── POST /api/compare ────────────────────────────────────────────────────────

@router.post("/compare")
def compare_architectures(request: CompareRequest):
    """
    Run the same scenario on two different architectures and return both results.
    Member 4 responsibility: comparison feature.

    Each architecture receives its own adapted scenario (different latencies,
    correct failure server IDs) so that comparison outputs are genuinely distinct.
    """
    arch_a = ARCHITECTURES.get(request.architecture_a)
    arch_b = ARCHITECTURES.get(request.architecture_b)

    if arch_a is None:
        raise HTTPException(status_code=400, detail=f"Unknown architecture A: {request.architecture_a}")
    if arch_b is None:
        raise HTTPException(status_code=400, detail=f"Unknown architecture B: {request.architecture_b}")
    if request.scenario not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {request.scenario}")

    # Each arch gets its OWN adapted scenario — different latencies, correct failure targets
    scenario_a = get_scenario_for_arch(request.scenario, request.architecture_a)
    scenario_b = get_scenario_for_arch(request.scenario, request.architecture_b)

    sim_a = CloudSimulation(arch_a, scenario_a)
    result_a = sim_a.run()

    sim_b = CloudSimulation(arch_b, scenario_b)
    result_b = sim_b.run()

    return {
        "architecture_a": request.architecture_a,
        "architecture_b": request.architecture_b,
        "scenario": request.scenario,
        "result_a": result_a,
        "result_b": result_b,
    }


# ── GET /api/health ──────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "CloudArchSim API"}
