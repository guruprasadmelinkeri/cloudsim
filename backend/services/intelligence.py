"""Deterministic architecture intelligence and optional Gemini integration."""
from io import BytesIO
import json, os
import networkx as nx
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

PRICES = {"client":{"hourly":0},"cdn":{"hourly":0.02},"load_balancer":{"hourly":0.025},"application_server":{"hourly":0.05},"auto_scaling_group":{"hourly":0.05},"database":{"hourly":0.12},"cache":{"hourly":0.04},"api_gateway":{"hourly":0.01},"queue":{"hourly":0.02},"storage":{"hourly":0.023},"data_transfer":{"per_gb_month":0.09}}
SIMULATION_LATENCY_MS = {"cdn":2,"load_balancer":1,"application_server":25,"auto_scaling_group":2,"database":18,"cache":1,"api_gateway":4,"queue":3,"storage":25}

def ensure_traffic_generator(architecture):
    """Guarantee a client source and connect it to otherwise unrooted services."""
    components=architecture["components"]
    raw_connections=architecture.setdefault("connections",[])
    connections=[]; seen=set()
    for edge in raw_connections:
        key=(edge["source"],edge["target"])
        if key not in seen: seen.add(key); connections.append(edge)
    architecture["connections"]=connections
    clients=[item for item in components if item.get("type")=="client"]
    if not clients:
        ids={item["id"] for item in components}
        ident="traffic-generator"
        while ident in ids: ident+="-1"
        clients=[{"id":ident,"type":"client","name":"Traffic Generator","config":{}}]
        components.append(clients[0])
    graph=nx.DiGraph(); graph.add_nodes_from(item["id"] for item in components)
    graph.add_edges_from((edge["source"],edge["target"]) for edge in connections)
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("Generated architecture has cyclic request paths; a directed acyclic request graph is required.")
    roots=[node for node in graph if graph.in_degree(node)==0 and not any(c["id"]==node for c in clients)]
    source=clients[0]["id"]
    for root in roots:
        if root!=source and not graph.has_edge(source,root):
            connections.append({"source":source,"target":root})
            graph.add_edge(source,root)
    return architecture

def populate_simulation_defaults(architecture):
    """Replace omitted or zero-valued service settings with usable local defaults."""
    counts={"application_server":2,"auto_scaling_group":2}
    for component in architecture["components"]:
        if component.get("type")=="client":
            component.setdefault("config",{})
            continue
        config=component.setdefault("config",{})
        defaults={"processing_latency_ms":SIMULATION_LATENCY_MS.get(component["type"],10),"processing_capacity_rps":100,"network_latency_ms":5,"max_concurrent":20 if component["type"]=="database" else 10,"max_queue_length":1000,"failure_probability":0,"recovery_time":5,"count":1,"instances":1,"max_instances":1}
        if component["type"] in counts:
            count=counts[component["type"]]; defaults.update({"count":count,"instances":count,"max_instances":4,"min_instances":1})
        if component["type"]=="auto_scaling_group": defaults.update({"min_instances":2,"scale_up_threshold":.8,"scale_up_delay":2})
        if component["type"]=="cache": defaults["hit_rate"]=.7
        if component["type"]=="cdn": defaults["hit_rate"]=.8
        for key,value in defaults.items():
            current=config.get(key)
            if current is None or (key in {"processing_latency_ms","processing_capacity_rps","network_latency_ms","max_concurrent","recovery_time","count","instances","max_instances","max_queue_length","min_instances","scale_up_threshold","scale_up_delay"} and (not isinstance(current,(int,float)) or current<=0)):
                config[key]=value
    return architecture

def _available_text_models(client):
    """Discover models exposed to this API key and prefer Gemini 3 text models."""
    models=list(client.models.list())
    names=[]
    for item in models:
        name=(getattr(item,"name","") or "").removeprefix("models/")
        actions=getattr(item,"supported_actions",None) or []
        # Auto mode is intentionally limited to Gemini 3 Flash text models. The
        # model-list endpoint does not expose billing/free-tier metadata, so it
        # must not be treated as permission to fall back to arbitrary models.
        media_model=any(tag in name.lower() for tag in ("-image","-tts","-live","translate"))
        if name.startswith("gemini-3") and "flash" in name.lower() and not media_model and "generateContent" in actions:
            names.append(name)
    # Prefer the requested 3.0 family, then other Gemini 3 Flash variants.
    return sorted(set(names),key=lambda n:(0 if n.startswith("gemini-3.0") else 1,n))

def _generate_with_available_model(client, contents, config):
    preferred=os.getenv("GEMINI_MODEL","").strip()
    if preferred:
        preferred=preferred.removeprefix("models/")
        media_model=any(tag in preferred.lower() for tag in ("-image","-tts","-live","translate"))
        if not (preferred.startswith("gemini-3") and "flash" in preferred.lower() and not media_model):
            raise RuntimeError("GEMINI_MODEL must name a Gemini 3 Flash text model. Confirm its free-tier availability in AI Studio.")
        candidates=[preferred]
        try:
            candidates.extend(name for name in _available_text_models(client) if name not in candidates)
        except Exception:
            # A configured model can still work if model listing is temporarily unavailable.
            pass
    else:
        candidates=_available_text_models(client)
    if not candidates:
        raise RuntimeError("No Gemini text-generation models are available to this API key. Set GEMINI_MODEL to a model enabled for this project.")
    last_error=None
    for model in candidates:
        try:
            return client.models.generate_content(model=model,contents=contents,config=config)
        except Exception as error:
            last_error=error
            detail=str(error).lower()
            # Don't retry quota/auth errors. Continue on an unavailable model or
            # transient model-specific failure, using only discovered Gemini 3
            # Flash candidates (or the user's explicit first-choice override).
            if any(token in detail for token in ("429","resource_exhausted","rate limit","401","403","permission denied")):
                raise
    raise last_error

def _count(c): return max(1,int(c.config.get("instances",c.config.get("count",c.config.get("replicas",1))) or 1))

def estimate_cost(design):
    items=[]; hourly=0.0
    for c in design.components:
        count=_count(c); rate=PRICES[c.type]["hourly"]
        if c.type=="storage": rate*=max(1,float(c.config.get("gb",100)))/100
        if c.type=="cdn": rate+=max(0,float(c.config.get("gb_month",100)))*0.0008/730
        rate+=max(0,float(c.config.get("egress_gb_month",0)))*PRICES["data_transfer"]["per_gb_month"]/730
        if c.type in ("application_server","auto_scaling_group","database","cache"): rate*=max(.25,float(c.config.get("size_factor",1)))
        amount=rate*count; hourly+=amount
        items.append({"id":c.id,"name":c.name,"type":c.type,"count":count,"hourly":round(amount,4),"daily":round(amount*24,2),"monthly":round(amount*730,2)})
    return {"currency":"USD","hourly":round(hourly,4),"daily":round(hourly*24,2),"monthly":round(hourly*730,2),"breakdown":items,"disclaimer":"Illustrative estimates only. Actual provider prices, region, usage, discounts and data transfer vary."}

def analyze_graph(design):
    g=nx.DiGraph(); g.add_nodes_from((c.id,{"type":c.type,"name":c.name}) for c in design.components); g.add_edges_from((e.source,e.target) for e in design.connections)
    components=list(nx.connected_components(g.to_undirected())) if g else []; clients=[c.id for c in design.components if c.type=="client"]; reachable=set()
    for client in clients:
        if client in g: reachable.update(nx.descendants(g,client)); reachable.add(client)
    types={}
    for c in design.components: types.setdefault(c.type,[]).append(c.id)
    single=[{"id":i,"name":g.nodes[i]["name"],"type":t} for t,ids in types.items() if t in {"load_balancer","database","cache","queue","api_gateway"} and len(ids)==1 for i in ids]
    critical=sorted(g,key=lambda n:g.in_degree(n)+g.out_degree(n),reverse=True)[:3]
    disconnected=[sorted(x) for x in components if not x.intersection(reachable)]
    choke_points=[]
    undirected=g.to_undirected()
    for node in nx.articulation_points(undirected) if len(undirected)>1 else []:
        choke_points.append({"id":node,"name":g.nodes[node]["name"],"reason":"Removing this component disconnects parts of the architecture graph."})
    risks=[]
    for i in critical:
        if g.nodes[i]["type"] == "client": continue
        down=nx.descendants(g,i)
        if len(down)>=2: risks.append({"component":i,"impact":"failure may interrupt downstream dependencies","affected":sorted(down)})
    rec=[]
    if single: rec.append("Add redundancy for critical single-instance components: "+", ".join(x["name"] for x in single))
    if disconnected: rec.append("Connect or remove components outside client request paths.")
    if len(types.get("application_server",[]))<2: rec.append("Use multiple application instances behind a load balancer for horizontal scale and failover.")
    return {"single_points_of_failure":single,"critical_components":critical,"choke_points":choke_points,"disconnected_components":disconnected,"cascading_failure_risks":risks,"recommendations":rec,"method":"NetworkX graph-structure findings; not a SimPy simulation or production availability prediction."}

def optimize(d):
    findings=[]; types=[c.type for c in d.components]
    if "cache" not in types and "database" in types: findings.append({"id":"add_cache","title":"Add a cache","reason":"Reduce repeated database reads and latency.","tradeoff":"Adds invalidation and operational complexity."})
    if types.count("database")==1: findings.append({"id":"add_replica","title":"Add a read replica","reason":"Separate read traffic to improve capacity and recovery options.","tradeoff":"Replication lag and additional cost."})
    if "load_balancer" not in types and types.count("application_server")+types.count("auto_scaling_group")>1: findings.append({"id":"add_load_balancer","title":"Add a load balancer","reason":"Distribute traffic across application instances.","tradeoff":"Adds another dependency to make redundant."})
    return findings

def recommend(requirements):
    if not os.getenv("GEMINI_API_KEY"): raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY in backend/.env; deterministic features remain available.")
    try:
        from google import genai
        from google.genai import types
        client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"),http_options=types.HttpOptions(timeout=30000))
        component={"type":"OBJECT","properties":{"id":{"type":"STRING"},"type":{"type":"STRING"},"name":{"type":"STRING"},"config":{"type":"OBJECT"}},"required":["id","type","name","config"]}
        connection={"type":"OBJECT","properties":{"source":{"type":"STRING"},"target":{"type":"STRING"}},"required":["source","target"]}
        strings={"type":"ARRAY","items":{"type":"STRING"}}
        architecture={"type":"OBJECT","properties":{"name":{"type":"STRING"},"components":{"type":"ARRAY","items":component},"connections":{"type":"ARRAY","items":connection},"explanation":{"type":"STRING"},"tradeoffs":strings,"choke_points":strings,"project_specific_risks":strings,"mitigations":strings,"scalability":strings,"assumptions":strings},"required":["name","components","connections","explanation","tradeoffs","choke_points","project_specific_risks","mitigations","scalability","assumptions"]}
        schema={"type":"OBJECT","properties":{"baseline":architecture,"mitigated":architecture,"comparison_summary":{"type":"STRING"}},"required":["baseline","mitigated","comparison_summary"]}
        prompt=("Act as a cloud architecture expert. From the product requirements, return TWO complete, comparable architecture designs. "
        "Both architectures MUST include exactly one component with type=client named Client or Traffic Generator, connected as the request-graph source. "
        "baseline is a plausible lower-cost/simple design that leaves its identified choke points and project-specific risks unmitigated; do not make it invalid or intentionally nonfunctional. "
        "mitigated is a production-minded alternative that addresses each identified baseline choke point and risk using components/configurations and explains trade-offs. "
        "Base risks only on evidence in the product description; label uncertain items as assumptions and never claim an unobserved error is confirmed. "
        "For each design return component IDs/types/names/config and real directed connections. Name the affected component IDs/names in each choke point and risk; map every mitigation to the risk or choke point it addresses and identify the concrete architecture/config change. "
        "Also return explanation, tradeoffs, choke_points, project_specific_risks, mitigations, scalability, assumptions; use empty arrays when the evidence does not support a finding. "
        "Use only component types client, cdn, load_balancer, application_server, auto_scaling_group, database, cache, api_gateway, queue, storage. "
        "Give every non-client component positive processing_latency_ms, processing_capacity_rps, network_latency_ms and max_concurrent simulation config values; use realistic nonzero service latencies rather than zero placeholders. Include instances/count on compute pools and cache/CDN hit_rate where applicable. "
        "Use unique component IDs, connect every required component into the client request path, use only valid unique directed connections, and ensure the graph is acyclic with at least one reachable terminal service. "
        "Make the two designs meaningfully different and preserve the same product requirements. Requirements: "+requirements)
        response=_generate_with_available_model(client,prompt,types.GenerateContentConfig(response_mime_type="application/json",response_schema=schema,temperature=.2))
        data=json.loads(response.text)
        allowed=set(PRICES)-{"data_transfer"}
        for option in (data["baseline"],data["mitigated"]):
            ensure_traffic_generator(option)
            populate_simulation_defaults(option)
            ids={c["id"] for c in option["components"]}
            if any(c["type"] not in allowed for c in option["components"]): raise ValueError("Unsupported component type")
            if any(e["source"] not in ids or e["target"] not in ids for e in option["connections"]): raise ValueError("Invalid connection")
            if len(ids)!=len(option["components"]): raise ValueError("Component IDs must be unique")
        return data
    except Exception as e:
        detail=str(e).lower()
        if "429" in detail or "resource_exhausted" in detail: message="Gemini free-tier quota or rate limit reached. Check AI Studio usage and retry after the quota resets."
        elif "timeout" in type(e).__name__.lower() or "timed out" in detail: message="Gemini request timed out. Retry when the service or network is available."
        elif "404" in detail or "not found" in detail: message="No discovered Gemini 3 Flash model is available to this API key. Check model access and free-tier eligibility in AI Studio."
        elif "401" in detail or "403" in detail or "permission" in detail: message="Gemini rejected the API key or model access. Check the key, project and free-tier access."
        else: message=f"Gemini request failed ({type(e).__name__}). Check model availability, quotas, network access and API key."
        raise RuntimeError(message) from e

def explain_comparison(comparisons):
    key=os.getenv("GEMINI_API_KEY")
    if not key: raise RuntimeError("Gemini is not configured; the deterministic comparison is still available.")
    try:
        from google import genai
        from google.genai import types
        client=genai.Client(api_key=key,http_options=types.HttpOptions(timeout=30000))
        response=_generate_with_available_model(client,"Compare these custom architectures using only the supplied component inventories, concrete graph-risk findings and illustrative costs. Explain trade-offs without inventing metrics or describing cost estimates as actual bills. Data: "+json.dumps(comparisons),types.GenerateContentConfig(temperature=.2,max_output_tokens=700))
        return response.text or "Gemini returned no comparison explanation."
    except Exception as e:
        if "429" in str(e) or "resource_exhausted" in str(e).lower(): raise RuntimeError("Gemini free-tier quota or rate limit reached.") from e
        raise RuntimeError(f"Gemini comparison failed ({type(e).__name__}); deterministic comparison remains available.") from e

def explain_simulation(design, config, result):
    key=os.getenv("GEMINI_API_KEY")
    if not key: raise RuntimeError("Gemini simulation analysis is optional. Configure GEMINI_API_KEY to enable it.")
    metrics=result.get("metrics",{})
    evidence={"architecture":design.model_dump(),"scenario":config.model_dump(),"metrics":metrics,"events":result.get("events",[])[-80:],"component_utilization":metrics.get("component_utilization",{}),"timeline_samples":result.get("timeline",[])[::max(1,len(result.get("timeline",[]))//40)],"assumptions":result.get("assumptions",[])}
    try:
        from google import genai
        from google.genai import types
        client=genai.Client(api_key=key,http_options=types.HttpOptions(timeout=30000))
        prompt=("Analyze this discrete-event simulation. Explain likely bottlenecks using only supplied evidence. Discuss scaling, caching, failures/recovery, and actionable architecture changes. Never invent or recalculate metrics; any numeric value in your answer must be copied exactly from the supplied metrics, and label it as simulated. If evidence does not establish a claim, state that limitation. Narrative only; do not return JSON metrics. Evidence: "+json.dumps(evidence,default=str))
        response=_generate_with_available_model(client,prompt,types.GenerateContentConfig(temperature=.2,max_output_tokens=1000))
        return response.text or "Gemini returned no analysis."
    except Exception as e:
        detail=str(e).lower()
        if "429" in detail or "resource_exhausted" in detail: message="Gemini free-tier quota or rate limit reached. The numerical simulation results remain available."
        elif "timeout" in type(e).__name__.lower() or "timed out" in detail: message="Gemini analysis timed out. The numerical simulation results remain available."
        else: message=f"Gemini analysis failed ({type(e).__name__}); the numerical simulation results remain available."
        raise RuntimeError(message) from e

def pdf_report(d,failure,cost,suggestions=None,ai_assessment=None):
    out=BytesIO(); p=canvas.Canvas(out,pagesize=letter); w,h=letter; y=h-48
    def line(s,indent=0):
        nonlocal y
        if y<55: p.showPage(); y=h-48
        p.setFont("Helvetica",9); p.drawString(42+indent,y,str(s)[:115]); y-=15
    p.setFont("Helvetica-Bold",18); p.drawString(42,y,d.name[:65]); y-=30
    line("Architecture Intelligence Report | Illustrative analysis, not a cloud bill or simulation")
    if d.components:
        diagram_y=y-20; positions={c.id:48+i*min(500/max(1,len(d.components)),100) for i,c in enumerate(d.components)}
        p.setFont("Helvetica",7); p.setStrokeColorRGB(.35,.48,.7)
        for edge in d.connections:
            if edge.source in positions and edge.target in positions:
                p.line(positions[edge.source]+36,diagram_y,positions[edge.target],diagram_y)
        for c in d.components:
            x=positions[c.id]; p.setFillColorRGB(.12,.2,.34); p.roundRect(x,diagram_y-17,72,32,4,fill=1,stroke=1); p.setFillColorRGB(.9,.93,.98)
            p.drawCentredString(x+36,diagram_y+3,c.name[:12]); p.drawCentredString(x+36,diagram_y-8,c.type[:12])
        y=diagram_y-34; p.setFillColorRGB(0,0,0)
    line("Components")
    for c in d.components: line(f"{c.name} ({c.type}) — {json.dumps(c.config)}",10)
    line("Connections")
    for e in d.connections: line(f"{e.source} -> {e.target}",10)
    line(f"Cost estimates USD: hourly ${cost['hourly']} | daily ${cost['daily']} | monthly ${cost['monthly']}")
    for b in cost["breakdown"]: line(f"{b['name']}: ${b['monthly']}/month",10)
    line("Reliability findings (graph structure)")
    for item in failure["single_points_of_failure"]: line(f"Single point of failure: {item['name']} ({item['type']})",10)
    for item in failure["choke_points"]: line(f"Choke point: {item['name']} — {item['reason']}",10)
    for item in failure["cascading_failure_risks"]: line(f"Cascade risk at {item['component']}: {item['impact']}; affected: {', '.join(item['affected'])}",10)
    for r in failure["recommendations"]: line("Recommendation: "+r,10)
    for item in suggestions or []: line(f"Optimization: {item['title']} — {item['reason']} Trade-off: {item['tradeoff']}",10)
    line("Critical components: "+", ".join(failure["critical_components"]))
    if ai_assessment:
        line("AI assessment: "+str(ai_assessment.get("explanation","Not provided")))
        for key in ("tradeoffs","choke_points","project_specific_risks","mitigations","scalability"):
            for item in ai_assessment.get(key,[]) or []: line(f"AI {key}: {item}",10)
        assumptions=ai_assessment.get("assumptions",[]) or []
    else:
        line("AI assessment: Not requested. "+failure["method"]); assumptions=[]
    line("Assumptions: illustrative USD catalogue; 730 hours/month; configured replica/count values; data transfer priced at catalogue assumption; excludes provider region, usage tiers and discounts.")
    for assumption in assumptions: line("AI assumption: "+assumption,10)
    p.save(); return out.getvalue()
