# CloudArchSim

### Cloud Architecture Simulation & Evaluation Platform

CloudArchSim is a **local cloud architecture simulation and visualization platform**. It demonstrates how different cloud architectures behave under predefined traffic loads, request patterns, failures, auto-scaling events, and database slowdowns.

This is an educational prototype built for a mid-term college project by a 4-member team. 
It focuses on clear, visual demonstration rather than complex production deployments. 
Everything runs entirely locally without Docker, databases, or cloud accounts.

---

## 🏗️ Predefined Architectures

1. **Single Server**: A simple client → server → database setup.
2. **Load Balanced**: A load balancer distributing requests to 3 servers using Round Robin.
3. **Auto Scaling**: Starts with 3 servers and scales up to 5 automatically when CPU exceeds 80%.
4. **Three Tier**: Includes App Servers, a Database, and a Cache layer that reduces database load.

## 🚦 Predefined Scenarios

- **Normal Traffic**: Stable baseline traffic (100 req/s).
- **High Traffic**: Sustained heavy load (300 req/s).
- **Traffic Spike**: Traffic jumps from 100 to 500 req/s, testing auto-scaling.
- **Server Failure**: Server 2 goes offline and recovers, testing fault tolerance and request rerouting.
- **Auto Scaling Event**: Load triggers new servers to be provisioned.
- **Database Slowdown**: DB latency spikes, causing queues to fill up.

---

## 👥 Four-Member Division

1. **Member 1**: Next.js Frontend, Dashboard, Topology Visualization, UI.
2. **Member 2**: Python FastAPI Backend, API endpoints, Data Models, Architecture Definitions.
3. **Member 3**: SimPy Discrete-Event Simulation Engine, core logic.
4. **Member 4**: Metrics Collection, Event System, Architecture Comparison functionality.

---

## 🚀 Installation & Running

You only need **Node.js/npm** and **Python 3** installed.

### Terminal 1: Backend (FastAPI + SimPy)

```bash
cd backend
python -m venv venv

# Activate the virtual environment:
# Windows: .\venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```
The backend API and Swagger UI will be available at `http://localhost:8000/docs`.

### Terminal 2: Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```
The dashboard will be available at `http://localhost:3000`.

---

## 🔬 Simulation Assumptions (Educational Context)

This is a simplified mathematical simulation, not a real distributed system:
- **CPU Utilization** is estimated as `(active_requests / server_capacity) * 100`.
- **Network & Database Latency** are represented using fixed, predefined delays.
- **Servers** are simulated SimPy `Resource` objects, not actual processes or VMs.
- **Auto Scaling** is modeled by dynamically creating new simulated server resources into the pool.
- Requests are discrete events processed in the engine, not real HTTP calls.

---

## 🎥 Example Demos

- **Auto Scaling Demo**: Select "Auto Scaling" architecture + "Traffic Spike" scenario. Watch the CPU metrics rise, triggering Server 4 and Server 5 to be created, which then redistributes traffic.
- **Failover Demo**: Select "Load Balanced" architecture + "Server Failure" scenario. Watch Server 2 turn red (offline) at 10s, with requests automatically routed to remaining servers, and recover at 20s.

*(Add screenshots here)*

## Architecture Intelligence Center

The separate `/intelligence` section adds a custom architecture designer, optional Gemini architecture advisor, illustrative component cost estimator, NetworkX reliability analysis, optimizer, custom-design comparison, PDF reports, and a separate graph-driven SimPy simulation dashboard at `/intelligence/simulation`. The custom simulation engine models graph traversal, resources/queues, failures and recovery, caching, and autoscaling without changing the four original simulation implementations. Cost figures are illustrative and simulation results are local model outputs, not provider bills or live infrastructure measurements. See [docs/FEATURE_GUIDE.md](docs/FEATURE_GUIDE.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [docs/GEMINI_SETUP.md](docs/GEMINI_SETUP.md).

## How to Run the Project

### Prerequisites

- Python 3.10 or newer and `pip`
- Node.js 20 or newer and npm
- Gemini API credentials are optional; non-AI features work without them.

### Repository setup

Clone/download the repository and open a terminal at its root (`CloudArchSim`). Do not run the commands from a guessed subfolder: both exact project directories are `backend/` and `frontend/`.

### Backend environment and dependencies

```bash
cd backend
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows PowerShell instead: .\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Optionally create `backend/.env` for Gemini:

```dotenv
GEMINI_API_KEY=your-secret-key
# Optional: leave empty for Gemini 3 Flash model discovery, or pin a verified free-tier model.
GEMINI_MODEL=
```

Automatic discovery prefers available Gemini 3 Flash text models, with Gemini 3.0 IDs first when present. The model list does not report free-tier eligibility, so verify in AI Studio that your selected model is free for your project. Follow [Gemini setup](docs/GEMINI_SETUP.md). Leave this file absent for non-AI functionality.

### Start the backend

From the `backend/` directory with the environment activated:

```bash
uvicorn main:app --reload
```

Backend: `http://localhost:8000`; API docs: `http://localhost:8000/docs`; intelligence health: `http://localhost:8000/api/intelligence/health`.

### Install and start the frontend

Open a second terminal at the repository root:

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`; Architecture Intelligence Center: `http://localhost:3000/intelligence`; custom simulation dashboard: `http://localhost:3000/intelligence/simulation`.

### Tests and checks

With backend dependencies installed, from `backend/` run `python -m unittest discover -s tests`. Gemini tests use mocks and do not consume API quota. To check the Next.js application, from `frontend/` run `npm run lint` and `npm run build`.

### Common troubleshooting

- `python` is not found: install Python and use `python3` on Linux distributions that do not provide the `python` alias.
- Frontend cannot reach the API: start FastAPI and confirm port 8000; the frontend API client targets `http://localhost:8000`.
- Gemini advisor unavailable: check `backend/.env`, restart the backend, verify `GEMINI_MODEL` is enabled for the free tier, and check AI Studio usage/quota. All other intelligence features work without Gemini.
- Port already in use: stop the other local process or use the relevant framework’s port option, then adjust the frontend API URL if moving the backend.
- npm dependency trouble: use Node.js 20+ and rerun `npm install` from `frontend/`.
