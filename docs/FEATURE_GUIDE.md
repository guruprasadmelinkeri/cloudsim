# Architecture Intelligence Center

Open **Architecture Intelligence** from the existing dashboard or visit `http://localhost:3000/intelligence`. This area works independently from the predefined SimPy architectures and comparison.

## Design

Start with the example design or add clients, CDN, load balancer, application servers, database, cache, API gateway, queue and storage. Add and remove components, edit component names and instance counts, connect component pairs, and save/load designs in a local JSON catalogue at `backend/data/designs.json`. Give a design a descriptive name before saving. Size factor and storage/transfer assumptions are represented in the component `config` object; use the API or edit design JSON for detailed parameters.

## Advisor

Describe the application, workload, availability needs, data and constraints in the advisor prompt. With `GEMINI_API_KEY` configured, the backend discovers generation-capable Gemini 3 Flash models exposed to that key and prefers Gemini 3.0 model IDs when available. Set optional `GEMINI_MODEL` to pin a model. Gemini returns schema-validated components, connections, explanation, trade-offs, bottlenecks, scalability guidance and assumptions. The proposed graph is imported into the editor. When Gemini is unavailable, local design and analysis remain available and the UI shows the backend error. API model discovery does not reveal free-tier billing eligibility; confirm the model and project tier in AI Studio. Setup is in [GEMINI_SETUP.md](GEMINI_SETUP.md).

## Analyze and estimate

Select **Analyze** to run deterministic NetworkX topology checks and the local illustrative USD catalogue. Findings include critical single instances, disconnected nodes, central dependencies and downstream cascade risks. Cost includes hourly, daily and 730-hour monthly totals and component breakdowns. These are heuristics and illustrative estimates, never cloud bills or SimPy outcomes.

Example: create `client → load balancer → two app servers → database`, add a cache between application and database, then analyze. A single database is flagged as a failure dependency; adding a read replica is one possible improvement.

## Optimize, compare, export

Analyze first, then select the optimizer suggestions to accept and apply them. The optimizer offers cache/read-replica/load-balancer suggestions with trade-offs. Accepted changes create a new unsaved “(optimized)” version and leave the original saved design unchanged. Save it under a new ID/name to retain both.

Save at least two designs and choose **Compare saved**. Up to five designs are compared for component count, illustrative monthly cost, scalability proxy, reliability heuristic and complexity, with a table and cost chart. When Gemini is configured, it also explains the trade-offs; deterministic comparison still works without it. The PDF action downloads a report with a diagram, design details, estimates, reliability findings and optimizer suggestions. Advisor assessment/assumptions are included when supplied; PDF export itself does not call Gemini.

The API is mounted under `/api/intelligence/`; OpenAPI details are at `http://localhost:8000/docs`. The reliability score is a topology heuristic, not an availability percentage. Custom designs are not passed to the existing simulation engine.

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
