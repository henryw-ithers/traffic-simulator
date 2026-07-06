# ADR-0002: Core simulation data model — ECS entities on a lane-level, unified multi-modal graph

**Status:** Accepted
**Date:** 2026-07-06
**Deciders:** Henry

## Context

[ADR-0001](0001-simulation-kernel-from-scratch.md) commits to a from-scratch kernel for two reasons: model transparency, and — the reason most relevant here — architectural freedom to add arbitrary new infrastructure/mode/zone types as first-class citizens without being bottlenecked by an external engine's data model. That decision explicitly made extensibility a hard constraint on this one: whatever the kernel's core data model turns out to be, adding a new category of infrastructure or behavior later must not require rewriting the simulation loop.

This ADR bundles three tightly coupled sub-decisions about that core data model, since none of them can really be decided independently:

1. **How entities are represented** (roads, lanes, signals, transit stops, zones) such that new types can be added without touching existing code.
2. **The granularity of the road network graph** — what a node/edge actually represents.
3. **How transit modes relate to the road graph**, given buses and streetcars share road space with cars but subway does not.

## Decision

### 1. Entity representation: Entity-Component-System (ECS)

Entities are plain IDs. Data lives in components (e.g. `RoadSegment`, `Lane`, `Signal`, `TransitStop`, `Zone`), attached to whichever entities need them. Simulation logic is written as systems that operate on entities having a given set of components, not as methods on a fixed type hierarchy.

Adding a new infrastructure type (e.g. a bike lane, a new signal behavior) means adding a new component struct and the system(s) that operate on it — existing components, systems, and the core simulation loop are untouched. This directly satisfies ADR-0001's extensibility requirement in a way that's idiomatic to Rust: lightweight ECS crates (e.g. `hecs`, `legion`, `shipyard`) provide the entity/component storage and query mechanics without pulling in a full game engine.

### 2. Graph granularity: lane-level

Each lane is its own graph element (edge, or sub-edge of a segment), and intersections connect specific lanes to specific lanes rather than segments to segments. This directly supports the v0.1 goal of evaluating a specific proposal (adding a turning lane at Eglinton/Allen) as a structural change to the graph, not a parameter tweak.

### 3. Multi-modal representation: unified graph with mode-specific properties

There is one graph, not one graph per mode. Edges and nodes carry which modes may use them and mode-specific properties (e.g. a lane edge tagged as streetcar-accessible, or car-only). Subway — which shares no physical space with road traffic — exists as its own disconnected subgraph within the same unified structure, connected to the road graph only at station/transfer nodes. This keeps a single coherent network to reason about and query, rather than reconciling parallel per-mode graphs whenever a mode shares infrastructure with another (buses and streetcars both running on a road edge).

## Options Considered

### Entity representation

| Option | Assessment |
|---|---|
| **ECS (chosen)** | New types added via new components/systems, no changes to existing code or the core loop; some upfront complexity in learning the pattern and choosing a crate; slightly less "obvious" to read than plain structs for someone unfamiliar with ECS. |
| Trait objects (`dyn Trait` polymorphism) | Familiar OOP-style mental model; but dynamic dispatch and heap allocation cost more at simulation scale, and behavior shared across unrelated entity types (e.g. "has a speed limit" applying to both roads and zones) is clunkier to express than as an orthogonal component. |
| Closed enum/struct per type | Simplest to write initially; but every new infrastructure type requires editing `match` statements throughout the kernel — directly contradicts ADR-0001's extensibility requirement, since the type is closed by definition. |

**Why ECS wins here:** it's the only option of the three where "add a new infrastructure type" is additive rather than requiring edits to existing, working code. That property is precisely what ADR-0001's extensibility argument asked for.

### Graph granularity

| Option | Assessment |
|---|---|
| **Lane-level (chosen)** | Enables real turning-lane and lane-change modeling directly; matches the v0.1 research question (would a turning lane help?) as a structural graph edit rather than a workaround; more setup complexity importing OSM data, since lane-level detail (turn restrictions per lane, lane count) is inconsistently tagged in OSM and often needs inference. |
| Segment-level, lanes as edge attributes | Faster to get an OSM import working end-to-end; but modeling a specific lane's behavior (e.g. a dedicated left-turn lane with its own signal phase) means retrofitting graph structure later rather than just adding data — exactly the kind of rework ADR-0001 is trying to avoid paying for twice. |

**Why lane-level wins here:** the v0.1 corridor's own headline question — would a turning lane help at Eglinton/Allen — is a lane-level question. Segment-level would need to be upgraded to answer it anyway.

### Multi-modal representation

| Option | Assessment |
|---|---|
| **Unified graph, mode-tagged (chosen)** | One structure to query and reason about; shared infrastructure (streetcars in mixed traffic) lives in one place; subway modeled as a disconnected subgraph joined at stations keeps the "one graph" property without forcing subway into road-like semantics it doesn't have. |
| Separate per-mode graphs, cross-linked at transfers | Cleaner separation of concerns per mode in isolation; but shared road/rail infrastructure (streetcars and cars on the same lane) has to be reconciled across two separate graphs instead of living in one place — more moving parts for the common case, not the rare one. |

**Why unified wins here:** most of the interesting multi-modal interactions in this project (streetcars blocking turning traffic, buses in mixed lanes, transit signal priority) are cases where a mode *shares* infrastructure with another, which is the case the separated-graphs option makes harder, not easier.

## Consequences

- The kernel takes a dependency on an ECS crate (a lightweight one, not a game engine) — the specific crate (`hecs` vs. `legion` vs. `shipyard`) is an implementation detail to be settled during scaffolding, not a separate ADR, but should be chosen before component types are written since it affects how they're declared.
- Component types for v0.1 are scoped to what the v0.1 corridor needs (`RoadSegment`, `Lane`, `Intersection`, `Signal` — car mode only, per the README's v0.1 scope). Transit-mode components (`TransitStop`, streetcar/subway-specific data) and `Zone` components are deferred to later phases, but the ECS pattern means adding them later should not require revisiting this ADR or the core loop.
- OSM import (Python side) must produce lane-level graph data, including inferring lane counts/turn restrictions where OSM tagging is incomplete for the focus corridor — this is new work not required by a segment-level model.
- A mode-tagging scheme for edges/nodes (e.g. which modes may traverse a given lane edge) needs to be defined as part of implementing this model — likely a small, extensible set (bitset or similar) rather than a closed enum, to stay consistent with the extensibility goal.
- Subway stations become the explicit join points between the road graph and the subway subgraph; the station/transfer node design deserves attention when subway modeling is actually implemented (later phase), but the unified-graph structure should already accommodate it.
- This ADR should be revisited if the ECS pattern proves to add more friction than value once the kernel is actually being written (e.g. if query ergonomics turn out to be worse than expected for a small, fixed-scope v0.1) — see Action Items.
- **Amendment (2026-07-06):** Testing AI traffic-light control over a fully connected network of lights and sensors is a **core project goal**, not a peripheral Phase 3 idea. Accordingly, signal *control policy* must be decoupled from signal *state* from the first implementation: a signal entity's components describe its phases and current state; the logic deciding phase changes is a swappable policy system. v0.1 ships a fixed-time policy; a vehicle-actuated policy follows if baseline calibration requires it (Toronto runs actuated/SCOOT control at many intersections — see the data audit in `docs/validation.md`); Phase 2/3 external/AI controllers drive signals through the command buffer and tick-level API (ADR-0003). Sensor/detector entities (loop detectors, cameras) become first-class components when actuated or AI control is implemented — an additive change under ECS. Fixed-time is v0.1's *policy choice*, never a structural assumption baked into the signal model.

## Action Items

1. [ ] Choose a specific lightweight ECS crate (`hecs`, `legion`, or `shipyard`) before writing component types — implementation detail. *Deferred past scaffolding (ADR-0006, 2026-07-06): the kernel stub has no entities yet; still to be chosen before the first component types are written.*
2. [ ] Define the v0.1 component set: `RoadSegment`, `Lane`, `Intersection`, `Signal` (car mode only, per README v0.1 scope) — defer transit/zone components.
3. [ ] Design the OSM → lane-level graph import mapping for the focus corridor, including how missing/ambiguous lane tagging is inferred or defaulted.
4. [ ] Define the mode-tagging scheme for graph edges/nodes (which modes can use a given lane) in a way that stays open to new modes being added later.
5. [ ] As part of ADR-0001's action item 1 (prototype the v0.1 corridor), confirm this data model is tractable to build and query at v0.1 scope before committing further phases to it.
