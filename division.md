# CloudArchSim — Comprehensive 4-Person Project Work Division

This document provides the complete, logical division of work among **4 team members** across the entire **CloudArchSim** platform (Frontend, Backend, Simulation Engine, Telemetry, and Architecture Comparison).

Each team member is assigned:
1. **One dedicated Cloud Architecture Simulation** (simulation logic, routing, failure/scaling/caching mechanics, and graph topology).
2. **One or more Scenarios** (traffic profile definitions in dedicated files under `backend/data/scenarios/`).
3. **One major platform subsystem** (Frontend UI, Backend API & Data Schemas, Discrete-Event Engine & Charts, or Metrics & Comparative Evaluation).

---

## Executive Summary Matrix

| Member | Architecture | Scenarios Owned | Platform Subsystem | Primary Backend Files | Primary Frontend Files |
|---|---|---|---|---|---|
| **Member 1** | **Single Server** (SPOF) | `normal_traffic`, `high_traffic` | **Frontend Dashboard & Topology Visualization** | `simulation/single_server.py`, `data/scenarios/normal_traffic.py`, `data/scenarios/high_traffic.py` | `app/page.tsx`, `components/TopologyView.tsx`, `app/layout.tsx`, `app/globals.css` |
| **Member 2** | **Load Balanced** (Round Robin, failover) | `server_failure` | **FastAPI Backend, API Routes & Data Schemas** | `simulation/load_balanced.py`, `data/scenarios/server_failure.py`, `main.py`, `api/routes.py`, `models/schemas.py`, `data/definitions.py` | `lib/api.ts`, `types/index.ts` |
| **Member 3** | **Auto-Scaling** (Elasticity, CPU triggers) | `traffic_spike`, `auto_scaling_event` | **SimPy Discrete-Event Core & Real-Time Charts** | `simulation/auto_scaling.py`, `data/scenarios/traffic_spike.py`, `data/scenarios/auto_scaling_event.py`, `simulation/base.py` (BaseEngine), `simulation/factory.py`, `simulation/engine.py` | `components/SimCharts.tsx` |
| **Member 4** | **Three-Tier with Cache** (Cache hits, DB offload) | `database_slowdown` | **Telemetry, Event Timeline & Comparison Feature** | `simulation/three_tier.py`, `data/scenarios/database_slowdown.py`, `simulation/base.py` (MetricsCollector), `api/routes.py` (`/api/compare`) | `components/MetricsPanel.tsx`, `components/EventTimeline.tsx`, `components/CompareView.tsx` |

---

## Detailed Member Breakdown

### Member 1: Frontend Lead & Single Server Architecture

#### 1. Architecture Simulation Responsibility
- **Architecture**: Single Server (`single_server`)
- **Backend File**: `backend/simulation/single_server.py`
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

#### 3. Full-Stack Subsystem Responsibility: Dashboard UI & Topology Visualizer
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
- **`frontend/app/layout.tsx` & `frontend/app/globals.css`**:
  - Modern dark-mode styling, typography, and responsive container layout.

---

### Member 2: Backend API Architect & Load Balanced Architecture

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

#### 3. Full-Stack Subsystem Responsibility: FastAPI Backend & Data Specifications
- **`backend/main.py`**:
  - FastAPI application bootstrapping, CORS middleware setup, and lifespan configuration.
- **`backend/api/routes.py`**:
  - `GET /api/architectures`: Serves list of available predefined architectures.
  - `GET /api/scenarios`: Serves list of traffic profiles and scenario definitions.
  - `POST /api/simulate`: Calls `get_scenario_for_arch()` to build arch-specific scenario before running.
  - `POST /api/compare`: Builds separate arch-specific scenarios for both architectures being compared.
  - `GET /api/health`: Health-check endpoint.
- **`backend/models/schemas.py`**:
  - Pydantic models validating all incoming payloads and outgoing API responses.
- **`backend/data/definitions.py`**:
  - Hardcoded catalog of architectures (`ARCHITECTURES`) with latency profiles and `failure_server_id`.
  - `get_scenario_for_arch(scenario_id, arch_id)` adapter that clones and tailors scenarios per architecture.
- **`frontend/lib/api.ts` & `frontend/types/index.ts`**:
  - Frontend API client functions (`getArchitectures`, `getScenarios`, `runSimulation`, `compareArchitectures`).
  - Strict TypeScript interface definitions matching backend Pydantic models.

---

### Member 3: SimPy Engine Architect & Auto-Scaling Architecture

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

#### 3. Full-Stack Subsystem Responsibility: SimPy Discrete-Event Core & Charts
- **`backend/simulation/base.py`** (`BaseSimulation`, `Server`, `LoadBalancer`):
  - SimPy discrete-event simulation orchestrator.
  - Inter-arrival request generator process (`_request_generator`) with traffic phases.
  - **Failure-aware** request processing (`_process_request`): checks `server.failed` at completion; requests on a mid-flight failed server are counted as failures (previously silently succeeded).
  - Second-by-second clock process (`_monitor`) coordinating event triggers and snapshot captures.
  - `_apply_failure_events()`: detects SPOF (all servers down) and emits distinct `💀 TOTAL OUTAGE` event.
- **`backend/simulation/factory.py` & `backend/simulation/engine.py`**:
  - Factory pattern registry (`create_simulation`, `get_simulation_class`).
  - Polymorphic `CloudSimulation` entrypoint preserving backward compatibility.
- **`frontend/components/SimCharts.tsx`**:
  - Real-time time-series telemetry charts using **Recharts**.
  - **CPU Utilization Chart**: CPU % over time with 80% auto-scaling threshold line.
  - **Throughput & Active Requests**: Requests completed/sec vs concurrent in-flight requests.
  - **Latency Chart**: Average and maximum response time trends.
  - Synchronized vertical reference cursor indicating the current scrubber time position.

---

### Member 4: Telemetry/Analytics Lead & Three-Tier Architecture

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

#### 3. Full-Stack Subsystem Responsibility: Metrics, Event Timeline & Comparison
- **`backend/simulation/base.py`** (`MetricsCollector`):
  - In-memory metrics accumulator for successful, failed, and dropped requests.
  - Rolling average response times and per-second snapshot generator (`snapshot()`).
- **`backend/api/routes.py`** (`POST /api/compare`):
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

---

## File Ownership & Code Location Guide

```
CloudArchSim/
├── backend/
│   ├── main.py                         ── Member 2 (FastAPI bootstrap, CORS)
│   ├── api/
│   │   └── routes.py                   ── Member 2 (CRUD routes, get_scenario_for_arch) & Member 4 (Compare route)
│   ├── data/
│   │   ├── definitions.py              ── Member 2 (Architecture configs, latency profiles, get_scenario_for_arch adapter)
│   │   └── scenarios/
│   │       ├── __init__.py             ── Member 2 (Package init)
│   │       ├── normal_traffic.py       ── Member 1 (Steady 100 req/s baseline)
│   │       ├── high_traffic.py         ── Member 1 (Sustained 300 req/s)
│   │       ├── server_failure.py       ── Member 2 (Server fails at 10s, recovers at 20s)
│   │       ├── traffic_spike.py        ── Member 3 (100→500→100 req/s spike)
│   │       ├── auto_scaling_event.py   ── Member 3 (100→400→100 req/s scaling trigger)
│   │       └── database_slowdown.py    ── Member 4 (DB latency 20→200ms spike)
│   ├── models/
│   │   └── schemas.py                  ── Member 2 (Pydantic models)
│   └── simulation/
│       ├── base.py                     ── Member 3 (BaseSimulation, Server, LoadBalancer) & Member 4 (MetricsCollector)
│       ├── factory.py                  ── Member 3 (Simulation factory)
│       ├── engine.py                   ── Member 3 (Polymorphic runner)
│       ├── single_server.py            ── Member 1 (Single Server Architecture, SPOF logic)
│       ├── load_balanced.py            ── Member 2 (Load Balanced Architecture)
│       ├── auto_scaling.py             ── Member 3 (Auto-Scaling Architecture)
│       └── three_tier.py               ── Member 4 (Three-Tier Architecture)
└── frontend/
    ├── app/
    │   ├── page.tsx                    ── Member 1 (Main dashboard, playback scrubber)
    │   ├── layout.tsx                  ── Member 1 (Root layout)
    │   └── globals.css                 ── Member 1 (Global styles)
    ├── components/
    │   ├── TopologyView.tsx            ── Member 1 (React Flow canvas, custom nodes)
    │   ├── SimCharts.tsx               ── Member 3 (Recharts time-series performance graphs)
    │   ├── MetricsPanel.tsx            ── Member 4 (Live KPI cards)
    │   ├── EventTimeline.tsx           ── Member 4 (System incident feed)
    │   └── CompareView.tsx             ── Member 4 (Side-by-side comparison w/ scorecard)
    ├── lib/
    │   └── api.ts                      ── Member 2 (Frontend HTTP client)
    └── types/
        └── index.ts                    ── Member 2 (TypeScript interfaces)
```

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
