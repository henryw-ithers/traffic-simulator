# ADR-0003: Kernel ↔ Python interface — batch-run API over step()-structured internals, columnar data transfer, Python-built network via a defined format

**Status:** Accepted
**Date:** 2026-07-06
**Deciders:** Henry

## Context

The platform is split between a Rust simulation kernel and a Python periphery (data import, demand modeling, scenarios, evaluation, visualization), bound via PyO3/maturin — that split was settled at project inception and recorded in the README. What remained open is the **shape** of the boundary between them, which decomposes into three coupled sub-decisions:

1. **Control granularity** — does Python invoke whole simulation runs, or drive the kernel tick-by-tick with mid-run inspection and mutation? Phase 2/3 (signal optimization, adaptive control, RL) fundamentally requires the latter: an optimizer is a loop that reads queue state and adjusts signals *during* a run. But v0.1 (batch corridor simulation, per README scope) does not, and a live control API is a large surface to design and stabilize — especially with no consumer yet existing to validate it against.
2. **Data transfer** — FFI calls across PyO3 are cheap individually but ruinous in aggregate. Per-entity access patterns (one call per vehicle position, per tick) multiply into millions of boundary crossings at city scale. Whatever the interface shape, boundary crossings must stay O(1) per query, not O(entities).
3. **Network loading** — the lane-level graph (ADR-0002) has to get into the kernel somehow. OSM lane inference is the messiest, most heuristic-laden part of the pipeline (inconsistent tagging, missing lane counts, ambiguous turn restrictions), and where it lives determines where iteration on those heuristics happens. This sub-decision also implicitly creates (or avoids) a network file format — which matters beyond this ADR, because scenario definitions (future ADR-0004) need a stable base artifact to express mutations against.

## Decision

### 1. Control granularity: batch-run public API, built over step()-structured internals

v0.1 exposes a minimal public API — approximately `Kernel.load(network, demand, seed)`, `run(duration)`, and result accessors. No public tick-level control yet.

Internally, however, the kernel is committed from day one to three disciplines that make tick-level control an additive change later rather than a restructuring:

- **The run loop is literally `for tick { step(dt) }`** — `run()` is a thin wrapper; `step()` never assumes knowledge of how many ticks remain or what happens between calls.
- **All mutations flow through a command buffer applied at tick boundaries** — including internal ones (e.g. the demand model releasing vehicles). When Phase 2 injects signal changes mid-run, it writes to a mechanism that already exists and is already tested. This also gives mutation semantics a clean answer by construction: changes requested during a tick take effect at the next tick boundary, never mid-tick.
- **State is queryable at any tick** — largely free given ADR-0002's ECS design, since components in the `World` *are* the live state; there is no separate accumulate-only-at-the-end representation. Entity IDs remain stable across ticks.

The public tick-level API (the project's TraCI equivalent — `step(n)`, state queries, mutation injection) is designed in Phase 2 **against a real consumer** (the first optimizer), when its actual requirements are known rather than guessed.

### 2. Data transfer: bulk columnar arrays + thin opaque handles

Simulation state and results cross the boundary as columnar arrays (numpy via `rust-numpy`, or Arrow if zero-copy dataframe interop proves worth the dependency) — e.g. one call returns *all* vehicle positions as parallel arrays of IDs/x/y/speed. Python-side consumers are dataframes (pandas/polars), which is the natural shape for the evaluation/calibration layer anyway.

Control objects (the simulation itself, result sets) are opaque PyO3 handles with methods — not per-entity Python objects. There are no Python classes wrapping individual lanes/vehicles/signals.

### 3. Network loading: Python builds the graph, kernel loads a defined network format

Python (osmnx/geopandas ecosystem) performs OSM import and all lane-level inference, and emits a **versioned, documented network file format** that the kernel loads. The messy geo-heuristics stay in Python where iteration is fastest and the ecosystem lives; the format becomes the clean, testable contract between the two halves.

The concrete serialization (likely a simple binary or columnar container; to be settled during scaffolding) is an implementation detail, but the format's *existence, versioning, and documentation* are part of this decision: a pinned network file is the reproducibility artifact ("this result was produced from network vX") and the stable base layer that scenario mutations (ADR-0004) will be expressed against.

## Options Considered

### Control granularity

| Option | Assessment |
|---|---|
| **Hybrid: batch API over step()-structured internals (chosen)** | Smallest stable public surface for v0.1; the three internal disciplines are cheap (ECS discourages the shortcuts they forbid anyway); Phase 2 tick-control becomes bindings work, not restructuring. Residual risk: internal-only interfaces get less scrutiny than public ones, so some mid-run-inspection edge cases will surface only in Phase 2 — accepted, since those are precisely the cases we can't predict without a consumer. |
| Full tick-level API from day one | Phase 2-ready on arrival and enables interactive notebook exploration early; but forces hard design questions now (mutation timing semantics, observation guarantees, determinism under injected mutations, chattiness mitigation like `step(n)`) with zero consumers to validate against — API guesses without consumers are usually wrong in the details. |
| Batch-only, no internal commitments | Maximum kernel freedom for v0.1; but internals predictably grow shapes hostile to live control (signal plans compiled to fixed schedules at load, aggregate-only metrics, recycled entity IDs), making Phase 2 the exact retrofit ADR-0001/0002 were structured to avoid. |

### Data transfer

| Option | Assessment |
|---|---|
| **Bulk columnar + thin handles (chosen)** | Boundary crossings O(1) per query regardless of entity count; lands directly in the dataframe tooling the evaluation layer uses; less ergonomic than object graphs for casual poking, mitigated by thin Python-side convenience wrappers over the arrays where wanted. |
| Rich PyO3 classes per entity | Most ergonomic for interactive exploration; but per-entity FFI calls are orders of magnitude slower at scale — fine for one corridor, a wall for the city, and the project's trajectory is the city. |
| Serialized snapshots (JSON/msgpack) | Simple and debuggable; but pays full serialization cost on every exchange and offers no live-control path, conflicting with the step()-structured future. |

### Network loading

| Option | Assessment |
|---|---|
| **Python builds, kernel loads a defined format (chosen)** | Lane-inference heuristics iterate at Python speed with the geo ecosystem; the format is a clean contract, a reproducibility artifact, and the base layer for scenario diffs; cost: one more format to define, version, and document. |
| Kernel imports OSM directly | One fewer format; but drags the most heuristic-heavy, iteration-hungry part of the pipeline into the compiled kernel, and couples the kernel to OSM's quirks when it should only know its own clean network model. |
| Python builds, streams via API calls (no file) | Avoids format versioning; but loses the pinned-artifact reproducibility property and leaves scenarios nothing stable to diff against — undermines two stated project principles for modest convenience. |

## Trade-off Analysis

The through-line in all three choices is the same: **keep the public boundary minimal and contract-shaped now, while holding the internals to disciplines that make the known future (live control, city scale, scenario diffing) additive rather than corrective.** The hybrid control decision trades some Phase 2 edge-case discovery risk for not designing APIs against imaginary consumers. Columnar transfer trades interactive ergonomics for a performance property that is non-negotiable at target scale. The network format trades upfront format-definition work for reproducibility and the scenario base layer the project's principles already demand.

## Consequences

- The kernel's internal architecture is constrained from the first line of code: explicit `step(dt)`, command-buffer mutations at tick boundaries, always-queryable ECS state with stable entity IDs. These are requirements, not suggestions — code review should treat violations as bugs.
- Determinism ("same seed + same inputs = same result") must hold at tick granularity, not merely end-to-end, since Phase 2 will inject mutations at arbitrary ticks and replay them. **Scope:** byte-identical results are guaranteed on the same platform and binary; across platforms, results are statistically equivalent but not necessarily bit-identical, since platform math libraries (libm transcendentals) may differ. Pursuing cross-platform bit-identity was considered and rejected as ongoing cost disproportionate to its value (2026-07-06 review).
- A network file format must be designed, versioned, and documented before the kernel can load anything — this is now on the v0.1 critical path, and its design should anticipate being the base layer scenario mutations reference (coordinate with ADR-0004).
- The Python package owns OSM import and lane inference for the focus corridor, including defaults/heuristics for incomplete tagging (per ADR-0002's action items).
- Result accessors return columnar data; any ergonomic Python-side wrappers are built *over* the arrays, never as per-entity FFI calls.
- The public tick-level control API is explicitly deferred to Phase 2 and should be designed against the first real optimizer — an ADR of its own at that point.
- Revisit if v0.1 reveals the internal disciplines are materially harder than expected (e.g. the command buffer fights the car-following implementation), rather than silently abandoning them.

## Action Items

1. [ ] Design the v0.1 network file format (schema, versioning scheme, documentation) — coordinate with ADR-0004 so scenario mutations can reference it cleanly.
2. [ ] Define the v0.1 public API surface concretely (load/run/results signatures) as part of scaffolding. — *Partially: the 2026-07-06 scaffold ships a stub (`Simulation(seed)` / `step` / `run` / `state_digest`); the real `load(network, demand, seed)`/results signatures are blocked on the network and demand file formats.*
3. [ ] Decide numpy-only vs. Arrow for columnar transfer during scaffolding (implementation detail; driven by whether zero-copy dataframe interop earns its dependency weight). — *Deferred past scaffolding (ADR-0006, 2026-07-06): no results cross the boundary yet; decide when they do.*
4. [x] Write a determinism test harness early: same seed + same network + same demand ⇒ byte-identical results on the same platform/binary, enforced in CI from the first runnable kernel. — *Done (2026-07-06, stub scope): tick-granular digest comparison in Rust (`core/kernel/tests/determinism.rs`) and through the bindings incl. cross-process runs (`python/tests/test_determinism.py`), enforced in CI on Ubuntu + Windows; must grow to load pinned network/demand inputs and compare full result output once those exist.*
5. [x] Document the three internal disciplines (step loop, command buffer, queryable state) in the kernel crate's top-level docs so they survive contributor turnover. — *Done (2026-07-06): `core/kernel/src/lib.rs` crate docs, flagged as requirements code review must enforce.*
