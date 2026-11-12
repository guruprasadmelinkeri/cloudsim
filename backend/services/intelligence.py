"""Deterministic architecture intelligence and optional Gemini integration."""
from io import BytesIO
import json, os
import networkx as nx
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

PRICES = {"client":{"hourly":0},"cdn":{"hourly":0.02},"load_balancer":{"hourly":0.025},"application_server":{"hourly":0.05},"auto_scaling_group":{"hourly":0.05},"database":{"hourly":0.12},"cache":{"hourly":0.04},"api_gateway":{"hourly":0.01},"queue":{"hourly":0.02},"storage":{"hourly":0.023},"data_transfer":{"per_gb_month":0.09}}

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
    risks=[]
    for i in critical:
        if g.nodes[i]["type"] == "client": continue
        down=nx.descendants(g,i)
        if len(down)>=2: risks.append({"component":i,"impact":"failure may interrupt downstream dependencies","affected":sorted(down)})
    score=max(0,100-18*len(single)-12*len(disconnected)-min(30,len(risks)*8)); rec=[]
    if single: rec.append("Add redundancy for critical single-instance components: "+", ".join(x["name"] for x in single))
    if disconnected: rec.append("Connect or remove components outside client request paths.")
    if len(types.get("application_server",[]))<2: rec.append("Use multiple application instances behind a load balancer for horizontal scale and failover.")
    return {"single_points_of_failure":single,"critical_components":critical,"disconnected_components":disconnected,"cascading_failure_risks":risks,"reliability_score":score,"recommendations":rec,"method":"NetworkX topology heuristics; not a SimPy simulation or production availability prediction."}

def optimize(d):
    findings=[]; types=[c.type for c in d.components]
    if "cache" not in types and "database" in types: findings.append({"id":"add_cache","title":"Add a cache","reason":"Reduce repeated database reads and latency.","tradeoff":"Adds invalidation and operational complexity."})
    if types.count("database")==1: findings.append({"id":"add_replica","title":"Add a read replica","reason":"Separate read traffic to improve capacity and recovery options.","tradeoff":"Replication lag and additional cost."})
    if "load_balancer" not in types and types.count("application_server")+types.count("auto_scaling_group")>1: findings.append({"id":"add_load_balancer","title":"Add a load balancer","reason":"Distribute traffic across application instances.","tradeoff":"Adds another dependency to make redundant."})
    return findings

def assess_architecture(d):
    failure=analyze_graph(d); types=[c.type for c in d.components]; costs=estimate_cost(d)
    performance=max(0,100-(18 if "database" in types and "cache" not in types else 0)-(12 if "cdn" not in types else 0))
    app_count=types.count("application_server")+types.count("auto_scaling_group")
    scale=100 if "load_balancer" in types and app_count>=2 else 65 if app_count>=2 else 40
    complexity=max(0,100-4*len(d.components)-2*len(d.connections))
    cost_score=max(0,min(100,100-int(costs["monthly"]/10)))
    return {"performance":{"score":performance,"findings":["Cache placement can reduce repeated database reads." if "database" in types and "cache" not in types else "Cache is present in the component inventory.","CDN presence reduces origin load for cacheable content." if "cdn" in types else "No CDN component is present."]},"scalability":{"score":scale,"findings":["Horizontal app capacity and a load balancer provide a basic scale path." if scale==100 else "Add application replicas and a load balancer for a clearer horizontal scale path."]},"reliability":{"score":failure["reliability_score"],"findings":failure["recommendations"]},"cost_efficiency":{"score":cost_score,"monthly_estimate":costs["monthly"],"findings":["Illustrative catalogue estimate; size, region and traffic assumptions change actual spend."]},"complexity":{"score":complexity,"component_count":len(d.components),"connection_count":len(d.connections),"findings":["Complexity proxy is based on component and connection counts."]},"method":"Deterministic design heuristics, not a production benchmark or SimPy result."}

def recommend(requirements):
    if not os.getenv("GEMINI_API_KEY"): raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY in backend/.env; deterministic features remain available.")
    try:
        from google import genai
        from google.genai import types
        client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"),http_options=types.HttpOptions(timeout=30000))
        schema={"type":"OBJECT","properties":{"name":{"type":"STRING"},"components":{"type":"ARRAY","items":{"type":"OBJECT","properties":{"id":{"type":"STRING"},"type":{"type":"STRING"},"name":{"type":"STRING"},"config":{"type":"OBJECT"}},"required":["id","type","name","config"]}},"connections":{"type":"ARRAY","items":{"type":"OBJECT","properties":{"source":{"type":"STRING"},"target":{"type":"STRING"}},"required":["source","target"]}},"explanation":{"type":"STRING"},"tradeoffs":{"type":"ARRAY","items":{"type":"STRING"}},"bottlenecks":{"type":"ARRAY","items":{"type":"STRING"}},"scalability":{"type":"ARRAY","items":{"type":"STRING"}},"assumptions":{"type":"ARRAY","items":{"type":"STRING"}}},"required":["name","components","connections","explanation","tradeoffs","bottlenecks","scalability","assumptions"]}
        response=_generate_with_available_model(client,"Design a cloud architecture from these requirements. Use component types client, cdn, load_balancer, application_server, auto_scaling_group, database, cache, api_gateway, queue, storage. Return schema JSON. Requirements: "+requirements,types.GenerateContentConfig(response_mime_type="application/json",response_schema=schema,temperature=.2))
        data=json.loads(response.text); ids={c["id"] for c in data["components"]}; allowed=set(PRICES)-{"data_transfer"}
        if any(c["type"] not in allowed for c in data["components"]): raise ValueError("Unsupported component type")
        if any(e["source"] not in ids or e["target"] not in ids for e in data["connections"]): raise ValueError("Invalid connection")
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
        response=_generate_with_available_model(client,"Compare these custom architectures using their supplied cost, graph reliability, scale and complexity heuristics. Explain the main trade-offs and do not call estimates actual bills or reliability scores measured availability. Data: "+json.dumps(comparisons),types.GenerateContentConfig(temperature=.2,max_output_tokens=700))
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

def pdf_report(d,failure,cost,suggestions=None,ai_assessment=None,assessment=None):
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
    line(f"Reliability heuristic score: {failure['reliability_score']}/100")
    for category, result in (assessment or {}).items():
        if isinstance(result,dict) and "score" in result: line(f"{category.replace('_',' ').title()} heuristic score: {result['score']}/100",10)
    for r in failure["recommendations"]: line("Recommendation: "+r,10)
    for item in suggestions or []: line(f"Optimization: {item['title']} — {item['reason']} Trade-off: {item['tradeoff']}",10)
    line("Critical components: "+", ".join(failure["critical_components"]))
    if ai_assessment:
        line("AI assessment: "+str(ai_assessment.get("explanation","Not provided")))
        for key in ("tradeoffs","bottlenecks","scalability"):
            for item in ai_assessment.get(key,[]) or []: line(f"AI {key}: {item}",10)
        assumptions=ai_assessment.get("assumptions",[]) or []
    else:
        line("AI assessment: Not requested. "+failure["method"]); assumptions=[]
    line("Assumptions: illustrative USD catalogue; 730 hours/month; configured replica/count values; data transfer priced at catalogue assumption; excludes provider region, usage tiers and discounts.")
    for assumption in assumptions: line("AI assumption: "+assumption,10)
    p.save(); return out.getvalue()
