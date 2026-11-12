# CloudArchSim Feature Demo and User Guide

This guide walks through the features available in CloudArchSim and how to try them locally. The original predefined simulator remains available alongside the separate Architecture Intelligence Center.

## Start CloudArchSim

You need Python 3.10+, Node.js 20+, and npm. From the repository root, start the backend in one terminal:

```bash
cd backend
python -m venv venv
# Linux/macOS: source venv/bin/activate
# Windows PowerShell: .\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the app at [http://localhost:3000](http://localhost:3000). The API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs). Gemini is optional: the designer, analysis, cost estimate, reliability analysis, optimizer, report, and simulation work without an API key. To enable Gemini, follow [docs/GEMINI_SETUP.md](docs/GEMINI_SETUP.md).

## Existing simulation dashboard

The home dashboard continues to run the original SimPy scenarios and predefined architecture implementations.

1. Select one of the four built-in architectures: **Single Server**, **Load Balanced**, **Auto Scaling**, or **Three Tier**.
2. Select a scenario, such as **Normal Traffic**, **High Traffic**, **Traffic Spike**, **Server Failure**, **Auto Scaling Event**, or **Database Slowdown**.
3. Run the simulation and inspect the topology, metrics, time series, events, and comparison view.
4. Use the existing comparison feature to compare the built-in architectures under its selected scenario.

This workflow uses the original simulator; the custom graph simulator described below is a separate engine.

## Architecture Intelligence Center

Open **Architecture Intelligence** from the dashboard, or visit [http://localhost:3000/intelligence](http://localhost:3000/intelligence). This area lets you build or import a custom design, analyze it, save versions, estimate illustrative costs, compare designs, and create a report.

### Create a design manually

1. Enter a descriptive design name. The starter design has a client, load balancer, application server, and database.
2. Add components using the component buttons: client, CDN, load balancer, application server, auto scaling group, database, cache, API gateway, queue, and storage.
3. Configure component names, instance counts, processing latency, processing capacity, network latency, concurrency, failure probability, and recovery time. Cache components also expose hit rate; application servers and auto scaling groups expose maximum instances.
4. Connect components with the **From component**, **To component**, and **Connect** controls. Remove unwanted components or connections with their remove controls.
5. Select **Save** to store the design in the local JSON catalogue. Use the saved-design list to load a design; the adjacent delete control removes it.

For example, create `Client → Load balancer → App server → Database`. To add caching, insert a cache on the request path between the app and database. Request graph connections matter to the custom simulator.

### Generate a design with AI Advisor

1. In **AI Architecture Advisor**, describe the application, workload, expected traffic, data, availability goals, and constraints.
2. Choose **Generate and import architecture**. Gemini returns a structured architecture and explanation; the generated components and connections are loaded into the designer for review and editing.
3. Save the design when you want it in the local catalogue. You can then analyze, optimize, export, or simulate it like a manually created design.

Gemini requires the optional `GEMINI_API_KEY` in `backend/.env`. With no `GEMINI_MODEL`, the backend discovers available Gemini 3 Flash text models and prefers Gemini 3.0 IDs when exposed; set `GEMINI_MODEL` to pin an exact ID. Verify free-tier eligibility in AI Studio because API model discovery does not report billing tier. AI availability, model access, and quota depend on Google AI Studio. No Gemini key is needed for non-AI features.

### Analyze, estimate cost, and inspect reliability

Select **Analyze** to run local deterministic checks. The results include design quality indicators, graph reliability findings, optimizer suggestions, and a component-wise cost estimate in hourly, daily, and monthly USD values.

The graph checks flag disconnected components, single points of failure, critical dependencies, and potential downstream cascade risks. The score is a topology heuristic, not an availability percentage. Cost values use an illustrative catalogue and are not provider quotes or actual bills.

### Optimize without losing the original

1. Run **Analyze** to populate optimizer suggestions.
2. Tick the changes you want to accept. Suggestions include changes such as adding a cache, read replica, or load balancer, along with reasons and trade-offs.
3. Select **Apply accepted**. The changes are applied to a new in-editor design version; the saved original is not overwritten. Save the result with a new name if you want to keep both.

### Compare saved designs

Save at least two designs, then select **Compare saved**. The center compares up to five saved designs by component count, illustrative monthly cost, scalability proxy, reliability heuristic, and complexity. When Gemini is configured, it can provide a narrative explanation of trade-offs; the deterministic comparison remains available without it.

### Export a PDF report

Select **PDF report** to download a report for the current design. It includes a diagram, components and connections, available architecture explanation and assumptions, illustrative costs, reliability findings, and optimizer suggestions. The export is generated locally with ReportLab; PDF generation itself does not call Gemini.

## Custom Architecture Simulation

Select **Save and simulate** in the designer, or open [http://localhost:3000/intelligence/simulation](http://localhost:3000/intelligence/simulation). The custom simulator loads saved designs and traverses each design's actual directed connections. It does not use the existing four architecture implementations or claim to measure real cloud infrastructure.

### Run a scenario

1. Select the architecture to simulate.
2. Choose a scenario:

   | Scenario | What it exercises |
   | --- | --- |
   | Normal Traffic | Stable baseline request rate |
   | High Traffic | Sustained elevated request volume |
   | Traffic Spike | A peak followed by traffic normalization |
   | Server Failure | Selected component outage and recovery |
   | Database Slowdown | Increased database latency and reduced effective capacity |
   | Auto Scaling | Rising load and autoscaling capacity changes |
   | Network Latency | Added delay between connected components |
   | Cache Failure | Cache outage and origin/database fallback |
   | Multiple Component Failures | Multiple selected outages, simultaneous or sequential |

3. Configure duration, initial and peak request rates, traffic pattern, failure times and targets, database slowdown, network delay, scaling threshold/cooldown, repetition count, random seed, and request limit as appropriate for the selected case.
4. Select **Run simulation**. The run is reproducible for the same design, configuration, and seed. Repetitions provide multiple runs to inspect variability.

### Read simulation results

The results dashboard labels values as simulated and reports incoming, successful, failed, and dropped requests; throughput; average, maximum, P95, and P99 response latency; error rate; queue length; component utilization and active instances; cache hits/misses; and database visits/latency.

The React Flow topology shows component health, utilization, active instances, and request counts. Recharts panels show throughput, response/database latency, utilization, and queue/error trends. The event list records failures, recovery, scaling, and other chronological events. Use play/pause, restart, and timeline scrubbing to review the sampled run timeline.

### Compare architectures under matching conditions

In **Compare with the same conditions**, select saved designs and optionally include the four predefined architectures. Select **Compare simulations** to run the selected alternatives with the same scenario configuration and seed sequence. The chart and table compare throughput, request outcomes, average/P95/P99 latency, error rate, utilization, recovery events, and illustrative monthly cost estimates. The summary explains the numerical differences from these simulation runs.

### Ask Gemini to interpret a completed run

After a run, select **Ask Gemini to analyze**. Gemini receives the design, scenario configuration, engine metrics, events, utilization, sampled timeline, and assumptions. Its narrative can explain likely bottlenecks and suggest changes. Measured numbers remain those returned by the simulation engine; Gemini does not generate or replace metrics. If suggestions are offered, select the ones you accept and choose **Apply accepted changes as new design** to create a separate design version, then simulate it again.

## Simulation model and limits

The custom engine uses SimPy resources to model request traversal, resource contention, concurrency, waiting queues, processing and network delays, failures and recovery, caching, database slowdown, and autoscaling. Load balancers and API gateways route to one child using the configured routing strategy; ordinary components with multiple outgoing edges treat dependencies as parallel required work. Cache/CDN hits skip downstream origin work. Autoscaling provisions after the modeled delay and does not scale down.

Cycles and unsupported component types or connection fields are rejected and reported. Disconnected components are reported as excluded instead of receiving requests. This educational model approximates component service time from configured latency and capacity; results are not production capacity forecasts, live monitoring, or actual SimPy outputs from the original predefined scenarios. Cost figures in comparisons remain illustrative catalogue estimates.

## API and automated checks

FastAPI interactive docs are available at `http://localhost:8000/docs`. Intelligence endpoints use `/api/intelligence/`; custom simulation endpoints include:

- `GET /api/intelligence/simulation/scenarios`
- `POST /api/intelligence/simulation/run`
- `POST /api/intelligence/simulation/compare`
- `POST /api/intelligence/simulation/analyze`

To run the backend test suite, activate the backend virtual environment and run from `backend/`:

```bash
python -m unittest discover -s tests
```

For frontend checks, from `frontend/` run `npm run lint` or `npm run build`.

## Troubleshooting

- **The app cannot reach the backend:** ensure FastAPI is running on port 8000 and the frontend is at port 3000.
- **Saved designs are missing:** designs are stored locally in the backend's JSON catalogue; use the same checkout and backend data directory.
- **Gemini is unavailable:** configure `GEMINI_API_KEY` in `backend/.env`, restart FastAPI, and check model availability and quota in AI Studio. Set `GEMINI_MODEL` only if you need to pin a model. Local analysis and simulation do not require Gemini.
- **A design cannot run:** check that connections refer to existing component IDs, the graph is acyclic, and every component type is supported. Disconnected nodes are excluded and reported.
- **A simulation is slow:** lower the request limit or rates, shorten duration, or use fewer repetitions.
