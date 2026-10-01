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
