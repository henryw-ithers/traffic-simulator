# ADR-0001: Build the simulation kernel from scratch instead of adopting an existing traffic simulation engine

**Status:** Accepted
**Date:** 2026-07-06
**Deciders:** Henry

## Context

The Toronto Transportation Digital Twin needs a simulation kernel that can model vehicle movement, car-following, lane-changing, and signal logic on a real road network, with transit modes (bus, streetcar, subway) layered on top in later phases.

Mature open-source traffic simulation engines already exist and cover much of this ground:

- **SUMO** (Eclipse) — imports OSM road networks directly (`netconvert`), includes validated car-following (Krauss model) and lane-changing models, traffic signal logic, basic public transit support (buses/trains sharing the road network with schedules), and `TraCI`/`libsumo`, a live control API for reading simulation state and injecting changes mid-run.
- **MATSim** — activity-based demand modeling and large-scale agent simulation, also open source, with a different architectural philosophy (activity chains rather than a live control API).

Both represent a significant amount of validated engineering (car-following and lane-changing models refined over roughly two decades) that a from-scratch project would otherwise need to re-derive.

The project's stated philosophy (README: "every assumption should be visible," "simulations should explain why, not act as a black box") is in tension with adopting a third-party engine as the production simulation core, since the physics driving every result would then live in code the project didn't write and can't fully audit or explain.

Separately, the project's long-term vision is not just to simulate Toronto as it exists today, but to let users freely add and combine arbitrary new infrastructure — new road types, new transit lines and modes, novel signal behaviors, custom zone/neighbourhood constructs — as first-class, freely composable objects in the simulation, not as one-off special cases. Existing engines were built around their own internal data models and extension points (SUMO's XML network/route schema and plugin surface, MATSim's activity-chain paradigm), which were designed for the kinds of scenarios their communities needed, not for open-ended structural extension. Adding a genuinely new category of infrastructure or behavior to one of these engines generally means working within (or around) that engine's existing assumptions about what a "road," "vehicle," or "mode" is, rather than defining new categories on equal footing with the built-in ones. That constraint would directly limit how far the scenario engine could be pushed toward "add anything" rather than "configure what's already supported."

This decision does not cover the rest of the platform — data import, scenario/evaluation logic, visualization — which already depend on standard external libraries and a database (PostGIS). It is scoped specifically to the simulation kernel: the component responsible for the tick-by-tick physics of vehicle/agent movement, car-following, lane-changing, and signal logic.

## Decision

Build the simulation kernel from scratch, in Rust, rather than adopting SUMO, MATSim, or a comparable existing engine as the production simulation core.

There are two reasons, not one, and it's worth separating them because they carry different weight:

1. **Ownership and transparency of the model.** The project's core value proposition is that every assumption behind a result is inspectable and explainable — that claim is materially stronger when the physics is code this project wrote and understands line-by-line, rather than an external engine's implementation.
2. **Architectural control for open-ended modularity.** The long-term vision requires the ability to freely add and combine new infrastructure types, transit modes, and behaviors as first-class objects — not configuration of a fixed set of built-ins. This is not a claim that SUMO/MATSim are incapable of modeling any specific thing we need *today*; it's that their internal data models and extension points weren't designed to have arbitrary new categories of infrastructure/behavior plugged in on equal footing with what they already support, and retrofitting that kind of openness onto an existing engine's architecture is harder than designing for it from the start. This reason is capability/architecture-driven, distinct from the transparency argument above, and is arguably the harder constraint to satisfy with an external engine.

This is a conscious trade-off of slower time-to-parity against full model ownership and long-term extensibility. It is expected that reaching feature/fidelity parity with what SUMO offers out of the box (validated car-following, mature signal logic, existing transit support) will take substantially longer than it would take to build on top of an existing engine.

Existing engines may still be used as an **external validation reference**: running the same OSM extract through SUMO and comparing aggregate outputs (e.g. travel times) against the from-scratch kernel is a useful sanity check for catching fundamental modeling errors, independent of calibration against real-world data. This is a validation tool, not a dependency of the production system.

## Options Considered

### Option A: From-scratch kernel in Rust (chosen)

| Dimension | Assessment |
|-----------|------------|
| Complexity | High — car-following, lane-changing, and signal logic must be designed, implemented, and validated from zero. |
| Cost | Highest upfront engineering time; no licensing cost. |
| Scalability | Unknown until built; Rust gives a high performance ceiling once the model is correct. |
| Team familiarity | Depends on Rust experience; no existing codebase to learn. |
| Transparency fit | Best possible fit — every line of physics is first-party and auditable. |

**Pros:** Full control over the data model and semantics (e.g. neighbourhood zones as first-class objects, unified cross-mode metrics like person-minutes of delay); no external dependency risk, licensing friction, or version churn; strongest possible claim to "every assumption is visible"; pedagogical value of understanding every mechanism; new infrastructure/mode categories can be designed in as first-class extension points from day one rather than bolted onto someone else's schema.

**Cons:** Re-derives two decades of car-following/lane-changing/signal-logic refinement that already exists elsewhere; significantly slower to reach a working baseline; higher risk of subtle physics bugs that mature engines have already found and fixed; no existing TraCI-equivalent control API — will need to build one for the future AI/optimization layer.

### Option B: Adopt SUMO as the production simulation engine

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low-to-medium — mostly configuration, network conversion, and TraCI integration rather than physics implementation. |
| Cost | Low upfront engineering time; open source, no licensing cost. |
| Scalability | Proven at city scale in prior research and deployments. |
| Team familiarity | New tool to learn, but well-documented with a large user base. |
| Transparency fit | Weak — car-following/lane-changing/signal internals are SUMO's C++, not first-party code. |

**Pros:** Fast path to a working baseline; validated physics; direct OSM import; TraCI gives a ready-made live control API for the future AI/optimization layer; existing (if imperfect) transit support.

**Cons:** Conflicts directly with the project's transparency principle — the physics behind every result would be an external black box relative to this project; TTC-specific behavior (streetcars sharing lanes with turning traffic, subway platform crowding) would need to be bent to fit SUMO's assumptions rather than modeled natively; dependency on an external project's roadmap, bugs, and licensing terms; adding genuinely new infrastructure/mode categories beyond what SUMO's network/route schema and simulation model already support means working within (or patching) SUMO's own codebase rather than extending ours — a structural ceiling on the "add anything" scenario vision.

### Option C: Adopt MATSim as the production simulation engine

| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium — different paradigm (activity-based demand) requires reframing the demand model. |
| Cost | Low upfront engineering time; open source. |
| Scalability | Proven at large regional scale. |
| Team familiarity | New tool and new paradigm to learn. |
| Transparency fit | Weak, same concern as Option B. |

**Pros:** Strong activity-based demand modeling, which fits the project's Layer 2 (demand) concept well; large-scale validation history.

**Cons:** Same transparency conflict as Option B; no live control API equivalent to TraCI, which would complicate the future AI/optimization layer; steeper conceptual mismatch with a live, tick-by-tick control model; the activity-based paradigm constrains what's easy to add as a new first-class concept in the same way SUMO's schema does, for the same reason.

### Option D: Hybrid — SUMO as production engine, from-scratch extensions for TTC-specific gaps

**Pros:** Faster baseline than full from-scratch; only builds the genuinely differentiated pieces (streetcar/subway modeling).

**Cons:** Still concedes the transparency principle for the majority of the physics (car-following, lane-changing, generic signal logic remain SUMO's); creates an awkward architectural seam between "SUMO's world" and "our world" that is likely to be a persistent source of friction; the extensibility problem is *worse* here, not better — new infrastructure/mode categories now have to be reconciled across two different data models instead of one; rejected because it doesn't resolve the core tension, it just relocates and duplicates it.

## Trade-off Analysis

The decision rests on two distinct arguments, one values-driven and one capability-driven:

- **Values-driven:** SUMO and MATSim are both technically capable of most of what v0.1 needs today, and would get there faster. The project's stated purpose — a transparent, explainable decision-support tool — is best served by first-party ownership of the simulation physics, even at the cost of a slower path to a working baseline.
- **Capability-driven:** the long-term vision requires arbitrary new infrastructure/mode/behavior types to be addable as first-class citizens, not squeezed into an existing engine's schema. This is a real architectural limitation of adopting SUMO/MATSim, not just a preference — retrofitting genuine structural openness onto an engine that wasn't designed for it is a harder and more fragile path than designing the kernel's core abstractions (road/lane/signal/mode/zone) to be extensible from the outset.

Using an existing engine purely as an external validation reference (not as the production system) preserves most of the sanity-checking benefit of Options B/C without compromising either ownership of the production model or its long-term extensibility.

## Consequences

- Reaching a working, calibrated v0.1 (per README's "Initial project scope") will take longer than it would on top of SUMO/MATSim. This is accepted as the cost of the transparency goal.
- The project takes on responsibility for validating its own car-following, lane-changing, and signal logic against real-world data — there is no borrowed validation history to lean on.
- A live control/state-inspection API (a TraCI equivalent) will need to be designed and built in-house before the Phase 2/3 optimization and AI layers can operate on the kernel.
- Comparing kernel output against SUMO on the same OSM extract is available as a low-cost sanity check and should be considered during Phase 1 calibration, without introducing SUMO as a runtime dependency.
- This decision is scoped to the simulation kernel only; it does not preclude using mature third-party libraries elsewhere in the stack (geospatial, graph, GTFS parsing, database).
- **Extensibility becomes a hard design constraint, not a nice-to-have.** Because open-ended modularity is a stated reason for this decision, the kernel's core abstractions (road/lane/intersection/signal, transit mode, zone) must be designed so that new categories can be added without rewriting the kernel's core loop. This directly shapes the upcoming road-graph data model decision (ADR-0002) — it should be evaluated partly on how well it supports adding wholly new infrastructure/mode types later, not just on fitting v0.1's needs.
- If, after attempting v0.1, the from-scratch kernel proves substantially harder to calibrate than expected, this decision should be revisited explicitly (see Action Items) rather than silently worked around.

## Action Items

1. [ ] Design the core data model for the road graph (nodes, edges, lanes, signals) — first hands-on test of whether the from-scratch approach is tractable at v0.1 scope **and** whether it supports adding new infrastructure/mode types without structural rework. Capture as ADR-0002.
2. [ ] Prototype the minimal car-following model for the v0.1 corridor and compare aggregate travel-time output against a SUMO run of the same OSM extract, as an early sanity check.
3. [ ] Sketch the live control/state-inspection API the Rust kernel will expose to Python (the project's TraCI equivalent), even though it isn't needed until Phase 2.
4. [ ] Revisit this ADR if v0.1 calibration against real traffic counts proves unworkable within a reasonable timeframe, or if the extensibility goal turns out to require a different approach than expected.
