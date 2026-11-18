"""Independent APIs for custom architecture intelligence (no SimPy coupling)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError
from typing import Any, Literal
from pathlib import Path
import json, os, uuid

import networkx as nx
from services.intelligence import analyze_graph, estimate_cost, optimize, recommend, pdf_report, explain_comparison, ensure_traffic_generator, populate_simulation_defaults

router = APIRouter()
STORE = Path(__file__).resolve().parents[1] / "data" / "designs.json"

class Component(BaseModel):
    id: str
    type: Literal["client", "cdn", "load_balancer", "application_server", "auto_scaling_group", "database", "cache", "api_gateway", "queue", "storage"]
    name: str
    config: dict[str, Any] = Field(default_factory=dict)

class Connection(BaseModel):
    source: str
    target: str

class Design(BaseModel):
    id: str | None = None
    name: str = "Untitled architecture"
    components: list[Component]
    connections: list[Connection]

class AdvisorRequest(BaseModel):
    requirements: str = Field(min_length=8, max_length=12000)

class OptimizeRequest(BaseModel):
    design: Design
    accepted: list[str] = Field(default_factory=list)

class ReportRequest(BaseModel):
    design: Design
    ai_assessment: dict[str, Any] | None = None

class ComparisonExplanationRequest(BaseModel):
    comparisons: list[dict[str, Any]]

class AdvisorArchitecture(BaseModel):
    name: str
    components: list[Component]
    connections: list[Connection]
    explanation: str
    tradeoffs: list[str]
    choke_points: list[str]
    project_specific_risks: list[str]
    mitigations: list[str]
    scalability: list[str]
    assumptions: list[str]

class Recommendation(BaseModel):
    baseline: AdvisorArchitecture
    mitigated: AdvisorArchitecture
    comparison_summary: str

def validate_design(d: Design):
    ids = [c.id for c in d.components]
    if len(ids) != len(set(ids)): raise HTTPException(422, "Component IDs must be unique")
    known = set(ids)
    edges=set()
    for edge in d.connections:
        if edge.source not in known or edge.target not in known: raise HTTPException(422, "Connections must reference existing components")
        if edge.source == edge.target: raise HTTPException(422, "Self-connections are not allowed")
        pair=(edge.source,edge.target)
        if pair in edges: raise HTTPException(422,"Duplicate connections are unsupported")
        edges.add(pair)
    clients=[c.id for c in d.components if c.type=="client"]
    if not clients: raise HTTPException(422,"Architecture needs at least one client/traffic-generator component")
    graph=nx.DiGraph(); graph.add_nodes_from(ids); graph.add_edges_from((e.source,e.target) for e in d.connections)
    if not nx.is_directed_acyclic_graph(graph): raise HTTPException(422,"Cyclic request paths are unsupported; connect components as a directed acyclic graph")
    reachable=set().union(*(nx.descendants(graph,client)|{client} for client in clients))
    if not any(graph.out_degree(node)==0 and node not in clients for node in graph if node in reachable):
        raise HTTPException(422,"Connect the client/traffic generator to at least one terminal infrastructure component")
    return d

def read_designs():
    if not STORE.exists(): return []
    try: return json.loads(STORE.read_text())
    except (ValueError, OSError): return []

def normalize_design_data(data):
    try:
        return populate_simulation_defaults(ensure_traffic_generator(data))
    except (ValueError, KeyError, TypeError):
        return data

@router.get("/health")
def health(): return {"status":"ok", "gemini_configured": bool(os.getenv("GEMINI_API_KEY"))}

@router.get("/catalogue")
def catalogue():
    from services.intelligence import PRICES
    return {"currency":"USD", "disclaimer":"Illustrative estimates only; not actual cloud bills.", "prices":PRICES}

@router.get("/designs")
def list_designs(): return {"designs":[normalize_design_data(item) for item in read_designs()]}

@router.post("/designs")
def save_design(design: Design):
    data=normalize_design_data(design.model_dump()); design=Design.model_validate(data)
    validate_design(design); items=read_designs(); ident=design.id or str(uuid.uuid4()); data=design.model_dump(); data["id"]=ident
    items=[x for x in items if x.get("id") != ident]; items.append(data); STORE.parent.mkdir(parents=True, exist_ok=True); STORE.write_text(json.dumps(items, indent=2)); return data

@router.get("/designs/{design_id}")
def get_design(design_id: str):
    item=next((x for x in read_designs() if x.get("id")==design_id), None)
    if item is None: raise HTTPException(404,"Design not found")
    return normalize_design_data(item)

@router.delete("/designs/{design_id}")
def delete_design(design_id: str):
    items=read_designs(); updated=[x for x in items if x.get("id")!=design_id]
    if len(updated)==len(items): raise HTTPException(404,"Design not found")
    STORE.write_text(json.dumps(updated,indent=2)); return {"deleted":design_id}

@router.post("/analyze")
def analyze(design: Design):
    validate_design(design); return {"failure":analyze_graph(design), "cost":estimate_cost(design), "optimizer":optimize(design)}

@router.post("/advisor")
def advisor(request: AdvisorRequest):
    try:
        payload=recommend(request.requirements)
        try:
            result=Recommendation.model_validate(payload)
            for option in (result.baseline,result.mitigated):
                validate_design(Design(name=option.name,components=option.components,connections=option.connections))
            return result.model_dump()
        except ValidationError as exc: raise HTTPException(502,"Gemini returned an architecture that did not match the required schema") from exc
    except RuntimeError as exc: raise HTTPException(503,str(exc))

@router.post("/optimize")
def optimization(request: OptimizeRequest):
    try: updated=ensure_traffic_generator(request.design.model_dump())
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    working_design=Design.model_validate(updated)
    validate_design(working_design); result=optimize(working_design); accepted=set(request.accepted)
    updated=working_design.model_dump()
    if "add_cache" in accepted and not any(c["type"]=="cache" for c in updated["components"]):
        updated["components"].append({"id":"cache-optimized", "type":"cache", "name":"Recommended cache", "config":{"replicas":2}})
        apps=[c["id"] for c in updated["components"] if c["type"]=="application_server"]
        db=next((c["id"] for c in updated["components"] if c["type"]=="database"),None)
        if db and apps:
            updated["connections"]=[edge for edge in updated["connections"] if not (edge["source"] in apps and edge["target"]==db)]
            updated["connections"].extend({"source":app,"target":"cache-optimized"} for app in apps)
            updated["connections"].append({"source":"cache-optimized","target":db})
    if "add_replica" in accepted:
        db=next((c for c in updated["components"] if c["type"]=="database"),None)
        if db: updated["components"].append({"id":"replica-optimized", "type":"database", "name":"Read replica", "config":{"role":"read_replica"}}); updated["connections"].append({"source":db["id"],"target":"replica-optimized"})
    if "add_load_balancer" in accepted and not any(c["type"]=="load_balancer" for c in updated["components"]):
        apps=[c["id"] for c in updated["components"] if c["type"]=="application_server"]
        if apps:
            updated["components"].append({"id":"lb-optimized", "type":"load_balancer", "name":"Recommended load balancer", "config":{}})
            clients=[c["id"] for c in updated["components"] if c["type"] in ("client","cdn","api_gateway")]
            updated["connections"]=[e for e in updated["connections"] if not (e["target"] in apps and e["source"] in clients)]
            updated["connections"].extend({"source":client,"target":"lb-optimized"} for client in clients)
            updated["connections"].extend({"source":"lb-optimized","target":app} for app in apps)
    updated=populate_simulation_defaults(ensure_traffic_generator(updated))
    updated["id"]=None; updated["name"]=f"{request.design.name} (optimized)"
    return {"recommendations":result,"design":updated}

@router.post("/compare")
def compare(designs: list[Design]):
    if not 2 <= len(designs) <= 5: raise HTTPException(422,"Compare between 2 and 5 designs")
    rows=[]
    for d in designs:
        validate_design(d); report=analyze_graph(d); cost=estimate_cost(d)
        rows.append({"id":d.id,"name":d.name,"components":len(d.components),"cost":cost,"failure":report})
    return {"comparisons":rows,"explanation":"Topology findings describe graph structure; cost values are illustrative catalogue estimates."}

@router.post("/compare/explanation")
def comparison_explanation(request: ComparisonExplanationRequest):
    try: return {"explanation":explain_comparison(request.comparisons)}
    except RuntimeError as exc: raise HTTPException(503,str(exc))

@router.post("/report")
def report(request: ReportRequest):
    design=request.design
    validate_design(design)
    from fastapi.responses import Response
    content=pdf_report(design,analyze_graph(design),estimate_cost(design),optimize(design),request.ai_assessment)
    return Response(content,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{design.name[:40].replace(chr(34), "")}.pdf"'})


from api.custom_simulation import router as simulation_router
router.include_router(simulation_router, prefix="/simulation", tags=["Custom SimPy Simulation"])
