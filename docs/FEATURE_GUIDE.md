# Architecture Intelligence Center

Open **Architecture Intelligence** from the existing dashboard or visit `http://localhost:3000/intelligence`. This area works independently from the predefined SimPy architectures and comparison.

## Design

Start with the example design or add clients, CDN, load balancer, application servers, database, cache, API gateway, queue and storage. At least one client/traffic generator is required and the editor prevents deleting the last one. Add and remove components, edit names, instance counts and simulation settings, connect components, and save/load designs in the local JSON catalogue at `backend/data/designs.json`. New and older saved designs are populated with nonzero illustrative service latency, network latency, capacity, concurrency and recovery defaults; the client generator has no processing-latency controls. Size factor and storage/transfer assumptions are represented in the component `config` object; use the API or edit design JSON for detailed parameters.

## Advisor

Describe the product, workload, expected traffic, data, availability, compliance and budget constraints in **Architecture Expert**. The Advisor returns two complete designs at once: a plausible **baseline** that exposes its identified choke points and project-specific risks, and a **mitigated recommendation** that addresses them. Both results include components, connections, explanations, trade-offs, scalability notes and assumptions. Risk descriptions must be grounded in the prompt; uncertain details are marked as assumptions, not presented as confirmed incidents. Review the side-by-side findings, then select **Load to editor** on either option to edit, save, analyze or simulate it. With `GEMINI_API_KEY` configured, the backend discovers generation-capable Gemini 3 Flash models and prefers Gemini 3.0 model IDs when available; set optional `GEMINI_MODEL` to pin a model. When Gemini is unavailable, local design and analysis remain available. API model discovery does not reveal free-tier billing eligibility; confirm the model and project tier in AI Studio. Setup is in [GEMINI_SETUP.md](GEMINI_SETUP.md).

## Analyze and estimate

Select **Analyze** to run NetworkX structural checks and the local illustrative USD catalogue. Findings include single points of failure, articulation-point choke points, disconnected nodes, critical dependencies and downstream cascade risks. The page displays findings instead of aggregate heuristic scores. Cost includes hourly, daily and 730-hour monthly totals and component breakdowns. Costs are illustrative estimates, never cloud bills or SimPy outcomes.

Example: create `client → load balancer → two app servers → database`, add a cache between application and database, then analyze. A single database is flagged as a failure dependency; adding a read replica is one possible improvement.

## Optimize, compare, export

Analyze first, then select the optimizer suggestions to accept and apply them. The optimizer offers cache/read-replica/load-balancer suggestions with trade-offs. Accepted changes create a new unsaved “(optimized)” version and leave the original saved design unchanged. Save it under a new ID/name to retain both.

To compare designs, save each one and open the **Custom Architecture Simulation** dashboard. Select the saved designs in **Compare with the same conditions** to compare engine results using matching traffic and failure conditions. The component editor intentionally has no separate saved-design comparison control. The PDF action downloads a report with a diagram, design details, estimates, graph-risk findings and optimizer suggestions. Selected AI design findings and assumptions are included when supplied; PDF export itself does not call Gemini.

The API is mounted under `/api/intelligence/`; OpenAPI details are at `http://localhost:8000/docs`. Structural findings describe graph topology; they are not availability percentages or simulation measurements. Custom designs are not passed to the existing predefined simulation engine.

Custom simulator endpoints are `GET /api/intelligence/simulation/scenarios`, `POST /api/intelligence/simulation/run`, `POST /api/intelligence/simulation/compare`, and `POST /api/intelligence/simulation/analyze`.

## Custom SimPy simulation

Choose **Save and simulate** in the designer to open `/intelligence/simulation` with that design selected. The simulator also loads previously saved designs. Configure one of nine scenarios, duration, stable/ramps/spikes/waves, initial and peak request rates, failure targets and timing, database slowdown, network delay, autoscale threshold, repetitions and random seed. Component cards configure instance counts, service capacity and latency, concurrency, failure chance/recovery, cache hit rate and autoscaling maximums.

The isolated `services/custom_simulation.py` engine builds a directed graph from the submitted design and runs request processes through its actual edges. Load balancers/API gateways route to one child; ordinary components process all outgoing dependencies in parallel. SimPy semaphores model concurrency and queue contention; cache/CDN hits terminate origin traversal; autoscaling groups add capacity after configured delay; failures and recovery appear in the event timeline. Cyclic request graphs are rejected, unknown node types/connection fields are rejected, and disconnected nodes are reported as excluded.

The dashboard reports simulated request counts, throughput, average/max/P95/P99 latency, error and drop rates, queues, database visits/latency, cache hits/misses, component utilization and active instances. React Flow renders health, traffic counts and utilization; Recharts shows utilization, throughput, response and queue/error trends. Play, pause, restart and scrubbing replay the sampled simulation timeline. Repetition summaries average the numerical run metrics while retaining each run's seed and metrics.

Use **Compare with the same conditions** to run selected saved designs and optionally all four predefined strategies with an identical configuration and seed sequence. The comparison includes simulated throughput/latency/errors, events and illustrative cost estimates. Gemini narrative analysis is optional and receives the architecture, scenario, simulation metrics, timeline samples and events. The endpoint returns Gemini text separately from the exact engine metrics; AI does not supply or alter numerical results.

### Simulation assumptions and limits

- Simulation is a local educational model, not a cloud provider or production performance forecast. Component processing latency plus inverse configured requests-per-second approximates service time.
- A request waits for a component concurrency slot; a full configured waiting queue drops that request. Requests still active at the end of the time window are classified as dropped at the horizon.
- Each ordinary component's outgoing edges represent required parallel dependencies. Load balancers and API gateways choose one child by round-robin or least outstanding requests. Unsupported cycles are rejected rather than approximated.
- A cache/CDN hit skips downstream origin traversal; misses continue over the graph. A database slowdown adds latency, which lowers effective service capacity through resource contention.
- Failure probabilities are sampled per component visit. Scheduled component failures take the component offline and restore it after the configured delay. Autoscaling adds instances after threshold detection, cooldown and launch delay; it does not scale down.
- Network delay is applied per connection from destination component configuration and the Network Latency scenario's added delay.
- All values are generated from the custom SimPy engine; they are separate from the existing four predefined simulation classes and their results.
