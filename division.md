# CloudArchSim — Comprehensive 4-Person Project Work Division

This document divides work among **4 team members** across the complete **CloudArchSim** platform. Each member has a backend responsibility, a frontend responsibility, and an architecture/scenario or analytics responsibility. Frontend and backend work is shared across the team instead of being concentrated in one role.

Each team member is assigned:
1. **One dedicated Cloud Architecture Simulation** (simulation logic, routing, failure/scaling/caching mechanics, and graph topology).
2. **One or more Scenarios** (traffic profile definitions in dedicated files under `backend/data/scenarios/`).
3. **A mixed full-stack responsibility** with owned backend files, owned frontend files, and a distinct project area.

---

## Executive Summary Matrix

| Member | Architecture | Scenarios Owned | Backend Responsibility | Frontend Responsibility | Additional Responsibility |
|---|---|---|---|---|---|
| **Member 1** | **Single Server** (SPOF) | `normal_traffic`, `high_traffic` | Single-server simulation, `POST /api/simulate`, shared-engine failure handling, and PDF report generation | Main dashboard, predefined topology, and report download | Own single-server run flow, failure behavior, and report artifact generation |
| **Member 2** | **Load Balanced** (Round Robin, failover) | `server_failure` | Load-balanced simulation, API bootstrap/catalog, architecture definitions, runner/factory integration, design APIs, and report schemas | API client/types, shared layout/styles, Intelligence Center design editor | Own design workflows and report contract; connect frontend to backend APIs |
| **Member 3** | **Auto-Scaling** (Elasticity, CPU triggers) | `traffic_spike`, `auto_scaling_event` | Auto-scaling simulation, request generation/monitoring engine, and graph-driven custom simulation/routes | Simulation charts, custom-run controls, and custom topology playback | Own simulation behavior and supply run metrics/events for reports |
| **Member 4** | **Three-Tier with Cache** (Cache hits, DB offload) | `database_slowdown` | Three-tier simulation, metrics collection, comparison API, and architecture/cost/risk analysis | Metrics panel, event timeline, comparison view, and report findings/results | Own comparison and report findings, cost estimates, and recommendations |

**All four members own backend, frontend, simulation, and report work.** Frontend work is split among dashboard/topology (Member 1), API/design UI (Member 2), simulation charts/playback (Member 3), and metrics/comparison/report findings (Member 4). Backend simulation work is split among each architecture plus shared engine/API slices: failure handling and single-run integration (Member 1), runner/catalog/design contracts (Member 2), request generation/custom execution (Member 3), and metrics/comparison/analysis (Member 4). Reports share a contract, simulation data, analysis findings, and PDF output across the team.

### Workload Balance

| Member | Major backend work | Major frontend work |
|---|---|---|
| **1** | Single-server simulation, shared failure handling, run API, PDF generation | Dashboard, topology, playback, report download |
| **2** | Load-balanced simulation, FastAPI/catalog, schemas, design APIs, Gemini, runner integration | Design editor, API integration, shared layout and styling |
| **3** | Auto-scaling, request engine, custom simulation | Custom simulation controls, charts, topology playback |
| **4** | Three-tier simulation, metrics, comparison, cost and risk analysis | Metrics, timeline, comparison, analysis and report findings |

Each member must implement and test their assigned backend behavior and deliver a complete frontend feature that uses it. Every feature includes API integration, error handling, and tests. For shared files, ownership is divided by the functions or sections listed below; members coordinate integration and review without transferring feature ownership.

---

## Detailed Member Breakdown

### Member 1: Main Dashboard + Single Server Architecture

#### 1. Architecture Simulation Responsibility
- **Architecture**: Single Server (`single_server`)
- **Backend File**: `backend/simulation/single_server.py`
- Implement and maintain this architecture's backend simulation logic alongside the dashboard and topology frontend.
- **Class**: `SingleServerSimulation` (inherits from `BaseSimulation`)
- **Simulated Mechanisms**:
  - Solitary server allocation (`server_1`, capacity = 10).
  - Direct client-to-server routing without load balancers.
  - **SPOF Demo**: In `server_failure` scenario, `server_1` (the only server) fails → 100% error rate from 10s–20s.
  - Architecture-specific latency: `processing_time_ms=70` (highest — no load distribution), `network_latency_ms=8`, `db_latency_ms=25`.
  - Generates 3-node linear topology: `CLIENT → SERVER_1 → DATABASE`, with edges going inactive during failure.

#### 2. Scenario Ownership
- **`data/scenarios/normal_traffic.py`** — Steady 100 req/s for 30s. Baseline scenario, no events.
- **`data/scenarios/high_traffic.py`** — Sustained 300 req/s for 30s. Demonstrates single server saturation.

#### 3. Frontend Responsibility: Main Dashboard and Predefined Topology
- **`frontend/app/page.tsx`**:
  - Primary application container and interactive dashboard.
  - Architecture selector and Scenario selector controls.
  - Timeline player controls: Play, Pause, Step Forward, Reset, Scrubber slider, and playback speed multipliers (1x, 2x, 5x).
  - Synchronizes replay time across topology, metrics cards, charts, and event timeline.
- **`frontend/components/TopologyView.tsx`**:
  - Interactive canvas powered by **React Flow**.
  - Custom SVG/Tailwind nodes:
    - `ClientNode`: Inbound user traffic source.
    - `LoadBalancerNode`: Shows routing algorithm badge.
    - `ServerNode`: Live CPU utilization gauge, active requests count, failed requests count, and color-coded status badges (`healthy`, `failed`, `new`).
    - `CacheNode`: Cache hit-rate indicator.
    - `DatabaseNode`: Latency display and health indicator.
  - Dynamic edges with active/inactive stroke styling reflecting live connection state and server health.

#### 4. Backend Responsibility: Single-Run API Integration
- **`backend/api/routes.py` — `POST /api/simulate`**:
  - Own the single-run route behavior that adapts the selected scenario and invokes the selected architecture simulation.
- **`backend/simulation/base.py` — request failure outcomes**: own failure handling and total-outage events; coordinate with Member 3, who owns request generation and monitoring.
- **`backend/api/intelligence.py` — `POST /report` and PDF generation**: build and serve the PDF using report schemas from Member 2, simulation data from Member 3, and findings from Member 4.
- Add the main dashboard's report-download control and handle the returned PDF artifact.

---

### Member 2: Design Editor and API Workflows + Load Balanced Architecture

#### 1. Architecture Simulation Responsibility
- **Architecture**: Load Balanced (`load_balanced`)
- **Backend File**: `backend/simulation/load_balanced.py`
- **Class**: `LoadBalancedSimulation` (inherits from `BaseSimulation`)
- **Simulated Mechanisms**:
  - Multi-server pool of 3 instances (`server_1`, `server_2`, `server_3`, capacity = 5 each).
  - Round Robin load balancing across active servers.
  - Architecture-specific latency: `processing_time_ms=50`, `network_latency_ms=14` (+LB hop), `db_latency_ms=22`.
  - **Partial failure**: `server_2` fails in `server_failure` scenario; `server_1` & `server_3` continue. Error spikes only for in-flight requests on `server_2`.
  - Generates topology: `CLIENT → LOAD BALANCER → [SERVER 1, 2, 3] → DATABASE`.

#### 2. Scenario Ownership
- **`data/scenarios/server_failure.py`** — Server fails at 10s, recovers at 20s (200 req/s throughout).
  - Failure target is architecture-specific (adapted by `get_scenario_for_arch()`):
    - `single_server` → `server_1` (SPOF: total outage)
    - `load_balanced` → `server_2` (partial failure; 2 servers remain)
    - `auto_scaling` → `server_2` (auto-scaler may compensate)
    - `three_tier` → `server_2` (1 server remains; may saturate)

#### 3. Backend and Frontend Responsibilities: API Contracts and Design Controls
- **`backend/main.py`**:
  - FastAPI application bootstrapping, CORS middleware setup, and lifespan configuration.
- **`backend/api/routes.py`**:
  - `GET /api/architectures`: Serves list of available predefined architectures.
  - `GET /api/scenarios`: Serves list of traffic profiles and scenario definitions.
  - `GET /api/health`: Health-check endpoint.
- **`backend/models/schemas.py`**:
  - Pydantic models validating all incoming payloads and outgoing API responses.
- **`backend/data/definitions.py`**:
  - Hardcoded catalog of architectures (`ARCHITECTURES`) with latency profiles and `failure_server_id`.
  - `get_scenario_for_arch(scenario_id, arch_id)` adapter that clones and tailors scenarios per architecture.
- **`backend/simulation/factory.py` & `backend/simulation/engine.py`**:
  - Own simulation registry and public runner integration; coordinate with Members 1 and 3 for their simulation classes and shared engine behavior.
- **`frontend/lib/api.ts` & `frontend/types/index.ts`**:
  - Frontend API client functions (`getArchitectures`, `getScenarios`, `runSimulation`, `compareArchitectures`).
  - Strict TypeScript interface definitions matching backend Pydantic models.
- **`frontend/app/intelligence/page.tsx` — design form and lifecycle controls**:
  - Own the Intelligence Center editor, including topology editing, component configuration, save/load/delete controls, and advisor UI; Member 4 owns analysis/report result presentation.
- **`frontend/app/layout.tsx` & `frontend/app/globals.css`**:
  - Own shared application layout, typography, dark-mode, and responsive styling.
- Define report request/response schemas in `backend/models/schemas.py`; add report selection/metadata controls to the Intelligence Center and pass them to Member 1's generator.

#### 4. Additional Backend Responsibility: Intelligence API and Design Lifecycle
- **`backend/api/intelligence.py`** (design lifecycle and API integration):
  - Own design data/API contracts and request/response validation for the health check, component catalogue, and design catalogue endpoints (`GET/POST /designs`, `GET/DELETE /designs/{id}`).
  - Implement local JSON design catalogue operations: list, save, retrieve, and delete designs.
  - Validate design component identifiers, connections, client/traffic-generator presence, and directed acyclic graph shape before persistence or processing.
  - Own the advisor endpoint contract and recommendation schema; connect the editor request to the optional Gemini service.
- **`backend/api/custom_simulation.py`** (route integration):
  - Own `GET /scenarios`; coordinate `POST /run` with Member 3 and `POST /compare` with Member 4.
- **`backend/services/intelligence.py` (AI advisor integration and configuration)**:
  - Keep optional Gemini model discovery/generation integration behind backend APIs; credentials remain backend-side.
  - Maintain Gemini setup guidance in `docs/GEMINI_SETUP.md` and ensure non-AI design workflows remain available without credentials.
- **`backend/models`**:
  - Maintain Pydantic design/advisor, custom simulation, and report request/response models. Member 2 owns the report contract consumed by Members 1, 3, and 4.

---

### Member 3: Custom Simulation and Playback + Auto-Scaling Architecture

#### 1. Architecture Simulation Responsibility
- **Architecture**: Auto-Scaling (`auto_scaling`)
- **Backend File**: `backend/simulation/auto_scaling.py`
- **Class**: `AutoScalingSimulation` (inherits from `BaseSimulation`)
- **Simulated Mechanisms**:
  - Starts with 3 baseline servers and dynamically expands up to 5 instances.
  - Least Connections routing algorithm (routes traffic to node with fewest concurrent requests).
  - Architecture-specific latency: `processing_time_ms=52`, `network_latency_ms=14`, `db_latency_ms=22`.
  - Threshold-based scaling: monitors aggregate CPU every second (`_on_second_tick`). When cluster CPU exceeds 80%, instantiates a new `Server` resource (`is_new=True`) and emits an `auto_scale` timeline event.
  - In `server_failure` scenario, scaler may provision a replacement server automatically.
  - Dynamic topology generation reflecting on-demand provisioned server nodes and edges.

#### 2. Scenario Ownership
- **`data/scenarios/traffic_spike.py`** — 100→500→100 req/s spike. Triggers auto-scaling.
- **`data/scenarios/auto_scaling_event.py`** — 100→400→100 req/s. More gradual ramp to CPU > 80%.

#### 3. Backend and Frontend Responsibilities: Simulation Core and Charts
- **`backend/simulation/base.py`** (`BaseSimulation`, `Server`, `LoadBalancer`):
  - SimPy discrete-event simulation orchestrator.
  - Own inter-arrival request generation, traffic phases, second-by-second monitoring, and snapshot timing. Member 1 owns failure processing in this shared module.
- **`frontend/components/SimCharts.tsx`**:
  - Real-time time-series telemetry charts using **Recharts**.
  - **CPU Utilization Chart**: CPU % over time with 80% auto-scaling threshold line.
  - **Throughput & Active Requests**: Requests completed/sec vs concurrent in-flight requests.
  - **Latency Chart**: Average and maximum response time trends.
  - Synchronized vertical reference cursor indicating the current scrubber time position.

#### 4. Additional Full-Stack Responsibility: Custom Design Simulation
- **Custom simulation scenario set**:
  - Implement the nine custom-run conditions: normal traffic, high traffic, traffic spike, server failure, database slowdown, auto scaling, network latency, cache failure, and multiple component failures.
  - Support stable, ramp, spike, and wave traffic patterns plus adjustable duration, rate, failure timing, recovery, repetitions, and seed.
- **`backend/models/custom_simulation.py`**:
  - Member 2 defines validated custom-design, scenario, failure, comparison, repetition, seed, and run-configuration inputs.
- **`backend/services/custom_simulation.py`**:
  - Implement the separate graph-driven SimPy runner: request traversal, capacity and queues, cache/CDN hits, routing, failures/recovery, database slowdown, network delay, autoscaling, timeline sampling, metrics, and repeated seeded runs.
  - Validate graph references and reject cyclic request paths; surface disconnected-component warnings.
- **`backend/api/custom_simulation.py`** (simulation execution):
  - Member 2 owns `GET /scenarios`; Member 3 owns `POST /run` and request-budget validation; Member 4 owns `POST /compare` and same-condition custom/predefined comparisons.
- **`frontend/app/intelligence/simulation/page.tsx` and `frontend/components/CustomSimulationTopology.tsx`**:
  - Build the custom simulation controls, run replay controls, topology playback, metric views, and saved-design comparisons.
  - Keep numerical metrics sourced from the custom engine; optional AI interpretation is narrative only.
- Provide custom and predefined run summaries, time-series metrics, and event records for Member 1's PDF generation and Member 4's report analysis; add the simulation results section to the report UI.

---

### Member 4: Telemetry and Analysis Experience + Three-Tier Architecture

#### 1. Architecture Simulation Responsibility
- **Architecture**: Three-Tier with Caching (`three_tier`)
- **Backend File**: `backend/simulation/three_tier.py`
- **Class**: `ThreeTierSimulation` (inherits from `BaseSimulation`)
- **Simulated Mechanisms**:
  - Multi-tier pipeline: Client → Load Balancer → 2 Application Servers → Cache Layer → Database.
  - Architecture-specific latency: `processing_time_ms=48`, `network_latency_ms=18` (+cache hop), `db_latency_ms=22`.
  - Cache hit/miss simulation (`cache_hit_rate = 60%`): 60% of requests bypass the DB.
  - Latency reduction (`cache_latency_reduction = 80%`): cache hits serve in 20% of database latency time.
  - **Resilience demo**: During `database_slowdown`, 60% of requests still served at cached speed → much lower avg latency vs other architectures.
  - 4-tier visual topology: `CLIENT → LB → [APP SERVERS] → CACHE → DATABASE`.

#### 2. Scenario Ownership
- **`data/scenarios/database_slowdown.py`** — DB latency spikes 10× (20ms → 200ms) from 15s–25s. Three-tier's cache absorbs 60% of the impact.

#### 3. Backend and Frontend Responsibilities: Telemetry and Comparison
- **`backend/simulation/base.py`** (`MetricsCollector`):
  - In-memory metrics accumulator for successful, failed, and dropped requests.
  - Rolling average response times and per-second snapshot generator (`snapshot()`).
- **`backend/api/routes.py`** (`POST /api/compare`):
  - Own the comparison endpoint and its response assembly.
  - Each architecture gets its own adapted scenario (different latencies + correct failure server IDs).
  - Returns both results with `all_events` for side-by-side event log comparison.
- **`frontend/components/MetricsPanel.tsx`**:
  - Live metric summary cards: Total Requests, Success Rate %, Average Response Time (ms), Throughput (req/s), and Active Servers.
- **`frontend/components/EventTimeline.tsx`**:
  - Chronological event stream displaying system incidents with severity indicators.
- **`frontend/components/CompareView.tsx`**:
  - Dedicated architecture comparison interface with:
    - Overall **scorecard** showing which architecture wins and by how many criteria.
    - **Winner indicator column** in the metrics table (per-metric winner highlighted in bold).
    - **Bar chart** comparing throughput, response latency, error rate, and dropped requests.
    - **Per-architecture event log** showing failure/recovery/scaling events that occurred on each side.
- **`frontend/app/intelligence/page.tsx` — analysis and report presentation**:
  - Own analysis findings, optimization results, and optional advisor response presentation; coordinate editor form behavior with Member 2. Member 1 owns the PDF report action.

#### 4. Additional Full-Stack Responsibility: Architecture Intelligence Analysis and Reporting
- **`backend/services/intelligence.py`** (analysis and decision support):
  - Maintain the illustrative component price catalogue and hourly/daily/monthly cost estimates.
  - Implement NetworkX structural findings: single points of failure, articulation/choke points, disconnected components, critical dependencies, and cascading risks.
  - Produce cache, read-replica, and load-balancer optimization suggestions and apply user-accepted suggestions to a separate optimized design.
  - Prepare report findings: design details, estimates, structural risks, suggestions, and any supplied AI assessment. Member 1 handles PDF generation.
  - Provide optional narrative explanations for design comparison and custom simulation results without changing simulation metrics.
- **`backend/api/intelligence.py`** (analysis endpoints):
  - Own `POST /analyze`, `/optimize`, `/compare`, and `/compare/explanation`; coordinate design schemas with Member 2. Member 1 owns `POST /report`.
- **`backend/api/custom_simulation.py`**:
  - Own `POST /simulation/analyze` narrative analysis integration with Member 3's run result; keep engine metrics separate from AI-generated explanation.
- **`frontend/app/intelligence/simulation/page.tsx`** (result interpretation):
  - Coordinate metric summaries and comparison result presentation with Member 3; present cost estimates and optional narrative separately from engine measurements.
- Own the report findings/results section and present analysis recommendations supplied to Member 1's PDF generator.

---

## File Ownership & Code Location Guide

```
CloudArchSim/
├── backend/
│   ├── main.py                         ── Member 2 (FastAPI bootstrap, CORS)
│   ├── api/
│   │   ├── routes.py                   ── Member 1 (POST /api/simulate), Member 2 (catalog/health routes and scenario adapter), Member 4 (POST /api/compare)
│   │   ├── intelligence.py             ── Member 1 (PDF report endpoint), Member 2 (design lifecycle/advisor), Member 4 (analysis endpoints)
│   │   └── custom_simulation.py        ── Member 2 (scenario catalog), Member 3 (run), Member 4 (compare and analysis)
│   ├── data/
│   │   ├── definitions.py              ── Member 2 (Architecture configs, latency profiles, get_scenario_for_arch adapter)
│   │   ├── designs.json                 ── Member 2 (local saved-design catalogue; generated/ignored runtime data)
│   │   └── scenarios/
│   │       ├── __init__.py             ── Member 2 (Package init)
│   │       ├── normal_traffic.py       ── Member 1 (Steady 100 req/s baseline)
│   │       ├── high_traffic.py         ── Member 1 (Sustained 300 req/s)
│   │       ├── server_failure.py       ── Member 2 (Server fails at 10s, recovers at 20s)
│   │       ├── traffic_spike.py        ── Member 3 (100→500→100 req/s spike)
│   │       ├── auto_scaling_event.py   ── Member 3 (100→400→100 req/s scaling trigger)
│   │       └── database_slowdown.py    ── Member 4 (DB latency 20→200ms spike)
│   ├── models/
│   │   ├── schemas.py                  ── Member 2 (predefined simulation Pydantic models)
│   │   └── custom_simulation.py        ── Member 2 (custom run request/response models)
│   ├── services/
│   │   ├── custom_simulation.py        ── Member 3 (graph-driven SimPy engine)
│   │   └── intelligence.py             ── Member 1 (PDF generation), Member 2 (Gemini integration), Member 4 (analysis, estimates, optimization, narratives)
│   └── simulation/
│       ├── base.py                     ── Member 1 (failure handling), Member 3 (request generation/monitoring), Member 4 (MetricsCollector)
│       ├── factory.py                  ── Member 2 (Simulation factory)
│       ├── engine.py                   ── Member 2 (Polymorphic runner)
│       ├── single_server.py            ── Member 1 (Single Server Architecture, SPOF logic)
│       ├── load_balanced.py            ── Member 2 (Load Balanced Architecture)
│       ├── auto_scaling.py             ── Member 3 (Auto-Scaling Architecture)
│       └── three_tier.py               ── Member 4 (Three-Tier Architecture)
└── frontend/
    ├── app/
    │   ├── page.tsx                    ── Member 1 (Main dashboard, playback scrubber)
    │   ├── intelligence/page.tsx       ── Member 2 (design editor/advisor), Member 4 (analysis/report findings)
    │   ├── intelligence/simulation/page.tsx ── Member 3 (custom simulation UI/playback) & Member 4 (analysis/cost interpretation)
    │   ├── layout.tsx                  ── Member 2 (Root layout)
    │   └── globals.css                 ── Member 2 (Global styles)
    ├── components/
    │   ├── TopologyView.tsx            ── Member 1 (React Flow canvas, custom nodes)
    │   ├── CustomSimulationTopology.tsx ── Member 3 (custom design topology and simulation playback)
    │   ├── SimCharts.tsx               ── Member 3 (Recharts time-series performance graphs)
    │   ├── MetricsPanel.tsx            ── Member 4 (Live KPI cards)
    │   ├── EventTimeline.tsx           ── Member 4 (System incident feed)
    │   └── CompareView.tsx             ── Member 4 (Side-by-side comparison w/ scorecard)
    ├── lib/
    │   └── api.ts                      ── Member 2 (Frontend HTTP client)
    └── types/
        └── index.ts                    ── Member 2 (TypeScript interfaces)
```

The Intelligence Center additions extend the existing assignments; they do not replace any original architecture, scenario, or subsystem ownership. Shared files are marked with the members responsible for their distinct parts.

---

## Key Architecture Differentiation Summary

| Metric | Single Server | Load Balanced | Auto Scaling | Three Tier |
|---|---|---|---|---|
| `processing_time_ms` | **70** (highest) | 50 | 52 | 48 (lowest) |
| `network_latency_ms` | 8 | **14** (+LB hop) | **14** (+LB hop) | **18** (+cache hop) |
| `db_latency_ms` | 25 | 22 | 22 | 22 (but 60% cached) |
| Server failure target | `server_1` (**SPOF** — total outage) | `server_2` (partial) | `server_2` (partial, auto-scales) | `server_2` (partial) |
| Fault tolerance | ❌ None | ✅ Partial | ✅ Partial + healing | ✅ Partial + cache buffer |
| Scaling | ❌ None | ❌ None | ✅ Up to 5 servers | ❌ Fixed 2 servers |

---

## Scenario-to-Architecture Design Intent

| Scenario | Best Architecture | Why |
|---|---|---|
| Normal Traffic | Any | Baseline — all architectures handle it, but single server shows highest latency |
| High Traffic | Auto Scaling | Single server saturates; load balanced helps; auto scaler adds capacity |
| Traffic Spike | Auto Scaling | Dynamic provisioning absorbs the spike burst |
| Server Failure | Three Tier / Load Balanced | SPOF on single server; others route around the failure |
| Auto Scaling Event | Auto Scaling | Only architecture that reacts to CPU thresholds |
| Database Slowdown | Three Tier | Cache absorbs 60% of reads — effectively immune to DB slowdown |
