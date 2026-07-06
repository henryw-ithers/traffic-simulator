# ADR-0005: Demand representation and routing locus — trip-list demand format with count-generated v0.1 content; routing in Python, kernel follows given paths

**Status:** Accepted
**Date:** 2026-07-06
**Deciders:** Henry

## Context

[ADR-0003](0003-kernel-python-interface.md) fixed the kernel's public API as approximately `Kernel.load(network, demand, seed)` — but left `demand` undefined. It is the third file format in the kernel's contract (alongside the network format and, indirectly, scenario files), and it hides two coupled decisions that shape both the kernel's internals and the Python pipeline:

1. **What demand *is*.** The calibration data available for the v0.1 corridor is turning movement counts at intersections. Estimating a true origin–destination (OD) matrix from counts alone is classically underdetermined — many OD matrices reproduce the same counts. Toronto does have a genuine OD source, the Transportation Tomorrow Survey (TTS), but it is zone-level, on a roughly five-year cycle, and integrating it is substantial work that Phase 1 calibration does not strictly need. Meanwhile, at least one stated research question ("how much traffic diverts through neighbourhood streets") eventually requires vehicles that *have destinations* and can divert — so whatever v0.1 does must not paint the demand format into a counts-only corner.
2. **Where routing lives.** Either the kernel computes routes (shortest paths, route choice, possibly congestion-responsive re-routing), or Python precomputes routes and the kernel purely executes them. This determines whether routing infrastructure and route-choice model assumptions enter the v0.1 kernel.

This was identified as the last contract-shaped gap in the 2026-07-06 architecture review; it was agreed it should be settled before any scaffolding.

## Decision

### 1. Demand format: a trip list — vehicles with departure times and routes — with v0.1 content generated from counts

The demand file format is, from day one: **a list of vehicles, each with a departure time and an explicit route** (a turn sequence / path through the lane-level network, referencing stable network element IDs per ADR-0003/0004).

For v0.1, Python *generates* that trip list from the data we actually have: boundary inflow counts (vehicles enter the corridor at measured rates) and turning movement proportions (each generated vehicle's turn sequence is sampled from measured proportions, using a seeded RNG so generation is reproducible). The vehicles are synthetic and destination-free in *origin*, but concrete and fully specified in *form* — the kernel cannot tell the difference between a count-generated trip and a future TTS/OD-generated one.

When later phases introduce real OD demand (TTS-based generation, demand models by time of day, mode choice), they fill **the same format**. The demand *file* never changes shape; only the *generator* behind it does.

Like the network format, the demand format is versioned and documented, and a pinned demand file is part of the reproducibility artifact chain (experiment file → network version + scenario versions + demand file + seeds).

### 2. Routing locus: Python routes; the kernel follows given paths

The kernel is pure physics: vehicles follow their assigned routes; the kernel never computes a route. Consequences of this stance:

- **Routes are inspectable data.** Every vehicle's intended path exists in a file before the simulation runs — directly serving the transparency principle ("why did flow appear on this street?" has a data-level answer).
- **Congestion-responsive behavior arrives later as an outer loop, not kernel routing.** The classic iterated-assignment pattern — run the simulation, measure experienced travel times, re-route demand in Python, run again until stable — fits ADR-0003's batch API exactly and covers the planning-scale questions (including neighbourhood diversion, once demand is OD-based) without any in-kernel routing.
- **Mid-run reactive rerouting** (a driver diverting around a queue in real time) is the one behavior this cannot express. If a research question ever genuinely requires it, adding it is a deliberate future decision (likely alongside the Phase 2 tick-level API, which provides the natural hook) — not something v0.1 pays for speculatively.

## Options Considered

### Demand representation

| Option | Assessment |
|---|---|
| **Trip-list format, count-generated content (chosen)** | Format is future-proof (OD/TTS generation fills it later with no format break); v0.1 stays directly calibratable against turning counts with no estimation problem; generation is seeded and reproducible; kernel contract is stable across phases. Cost: slightly more v0.1 machinery than raw inflow tables (a generator script rather than passing counts through). |
| Pure boundary-inflow model in the kernel | Least precomputation; but bakes a v0.1-only demand concept into the kernel's public contract, moves stochastic turn-sampling into Rust (another RNG consumer inside the determinism boundary), and is torn out the moment OD demand arrives — the exact rework pattern ADRs 0001–0004 are structured to avoid. |
| Full OD/trip demand from day one | Most realistic; enables diversion questions immediately; but puts a research-grade OD-estimation problem (underdetermined from counts; TTS integration) on the v0.1 critical path, delaying the calibration milestone everything else waits on. |

### Routing locus

| Option | Assessment |
|---|---|
| **Python routes, kernel follows (chosen)** | Kernel stays small, auditable, physics-only; routes are data (transparency, diffability); iterated assignment over batch runs covers congestion response for planning questions; route-choice model assumptions live in Python where iteration is fast and visible. Cost: mid-run reactive rerouting is inexpressible until a deliberate future addition. |
| Kernel computes routes | Enables reactive diversion from day one; but drags shortest-path infrastructure, route-choice assumptions, and their calibration burden into the v0.1 kernel before any v0.1 research question needs them, and buries routing assumptions in Rust where they're least visible. |

## Trade-off Analysis

Both choices follow the pattern established by ADRs 0002–0004: **stabilize the contract, keep the sophisticated behavior behind it, and let capability grow by swapping generators rather than reshaping interfaces.** The trip-list format costs a little v0.1 generation machinery to buy a permanent kernel contract; Python-side routing costs reactive rerouting (which no current research question requires) to keep the kernel pure, auditable physics and route choice inspectable. The rejected options each trade long-term structure for short-term convenience or premature realism.

## Consequences

- A third versioned file format (demand) must be designed alongside the network format — same stable-ID discipline, same documentation/versioning expectations (extends ADR-0003 action item 1).
- The Python package gains a **demand generator** module for v0.1: boundary counts + turning proportions → seeded trip list. The turning-count ingestion (City of Toronto open data) feeds this directly.
- The kernel's vehicle model needs a "follow this route" representation (next-turn/next-lane resolution against the lane-level graph) but **no** pathfinding, no route-choice parameters, and no demand-side RNG beyond what the demand file already fixed — shrinking the v0.1 kernel's scope and its determinism surface.
- Calibration for v0.1 compares simulated turning flows/travel times against the same counts that generated demand *plus* independent observations (travel times, queue lengths) — the validation methodology doc should be explicit that reproducing the counts you generated from is a consistency check, not validation; the independent observations are the real test.
- Iterated assignment (the congestion-response outer loop) is anticipated but **not built in v0.1** — it becomes relevant when demand is OD-based and route alternatives exist.
- Mid-run reactive rerouting is explicitly out of scope until a research question demands it; revisit alongside the Phase 2 tick-level API if so.

## Action Items

1. [ ] Design the demand file format (schema, versioning) together with the network format — they share the stable-ID discipline and should be documented as a pair.
2. [ ] Specify the v0.1 demand generator: inputs (boundary counts, turning proportions by time-of-day period), seeded sampling procedure, output trip list.
3. [ ] Identify and fetch the actual turning movement count datasets for the focus corridor intersections (City of Toronto open data) — the generator's inputs need to exist.
4. [ ] In `docs/validation.md` (to be written), distinguish consistency checks (reproducing generation inputs) from true validation (independent travel times/queue observations).
5. [ ] Define the kernel's route-following representation (how a vehicle resolves its next lane/turn against the graph) as part of the v0.1 component set design (ADR-0002 action item 2).
