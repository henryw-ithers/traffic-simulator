# ADR-0004: Scenario definition format — typed operation vocabulary in layerable YAML, with scenario/experiment separation and Python authoring tools

**Status:** Accepted
**Date:** 2026-07-06
**Deciders:** Henry

## Context

A founding principle of the project (README) is that every modification to the city exists as a **scenario layered on a base network, never a mutation of it** — and that scenarios are *data, not code*, so they can be diffed, validated, shared, and reproduced. [ADR-0003](0003-kernel-python-interface.md) fixed one anchor: the base network is a versioned file, so a scenario is expressed against a specific network version.

Several project principles depend directly on what a scenario file actually is:

- **Transparency** — anyone should be able to read a scenario and know what intervention it describes, without executing anything.
- **Reproducibility** — the same scenario applied to the same network version must mean the same thing, every time.
- **The public-sandbox vision** — scenarios will eventually be authored and exchanged by people who don't trust each other; a scenario must be inert content, not executable code.
- **Phase 4 toolability** — a future natural-language interface generating scenarios, visual editors, and automated conflict detection are all tractable over structured data and roughly impossible over arbitrary code.

This ADR settles four coupled sub-decisions: how mutations are expressed, whether scenarios compose, whether the intervention is separate from run parameters, and the concrete file format.

## Decision

### 1. Mutations: a typed operation vocabulary, with Python authoring tools

A scenario is an ordered list of **named, schema-validated operations** — e.g. `add_lane`, `close_edge`, `set_signal_timing`, `add_signal_phase`, later `add_transit_stop`, `add_route` — each with typed parameters referencing stable element IDs from the base network file. Example shape:

```yaml
base_network: toronto-corridor-v3
mutations:
  - op: add_lane
    segment: eglinton_wb_approach_allen
    side: left
    turn_movements: [left]
    length_m: 75
  - op: add_signal_phase
    intersection: eglinton_allen
    phase: {protects: [wb_left], duration_s: 12}
```

Applying a scenario maps operations directly onto the ECS model ([ADR-0002](0002-core-simulation-data-model.md)) — spawn entities, attach/modify components — delivered through the kernel's command buffer ([ADR-0003](0003-kernel-python-interface.md)). The simulator only ever interprets vocabulary operations; it never executes scenario-supplied code.

For bulk or rule-based interventions ("add a reversible lane to every Allen Road segment with 3+ lanes"), a **Python authoring library** generates scenario files programmatically. The loop-and-query expressiveness of scripting lives at *authoring time*, on the author's machine; what is saved, validated, shared, and executed remains pure data. When authoring reveals a genuinely new intervention *type*, that is the signal to add a first-class operation to the vocabulary — a deliberate, reviewed act, same rhythm as adding an ECS component.

### 2. Composition: layerable — base network + ordered mutation layers

A scenario names its base network version and an ordered list of mutation layers, and may include other scenarios as layers (e.g. `bus-lane` + `signal-priority` = a combined study). Later layers apply after earlier ones. Conflict rules (two layers touching the same element) must be defined as part of the schema — at minimum, detection with a clear error; silent last-writer-wins is not acceptable for a tool whose purpose is trustworthy comparison.

### 3. Scenario vs. experiment: separate configs

- A **scenario** describes only the intervention — what you would physically build or change.
- An **experiment** describes a run: which scenarios to compare, over which demand, duration, and seed set.

A comparison ("baseline vs. turning lane, identical seeds and demand") is one experiment file referencing two scenarios. The experiment file is the reproducibility artifact for every published result — it pins network version, scenario versions, demand inputs, and seeds in one place.

### 4. File format: YAML, validated against a published JSON Schema

Scenario and experiment files are YAML — they are documents humans write, comment ("this models the 2027 construction closure"), and review. YAML's looseness is contained by validating every file against a published JSON Schema before use; tooling treats schema violations as hard errors.

## Options Considered

### Mutation expression

| Option | Assessment |
|---|---|
| **Typed vocabulary + authoring tools (chosen)** | Readable, diffable, validatable before execution (element IDs exist? physically plausible? layers conflict?); inert and safe to share; directly toolable for Phase 4. Cost: expressiveness grows only as the vocabulary grows — occasional friction when a wanted operation doesn't exist yet. That friction is arguably a feature: new intervention types become named, documented concepts rather than anonymous code. |
| Raw network-file patch/diff | No vocabulary to design; but the file says what bytes changed, not what intervention was made — unreadable, unreviewable, fragile across network regenerations, and unvalidatable for physical sense. |
| Embedded scripting (Python in scenarios) | Unbounded day-one expressiveness; but scenario meaning becomes discoverable only by execution; nothing is validatable until after the fact; behavioral diffs are invisible in textual diffs; sharing scenarios becomes arbitrary code execution; and "same scenario = same meaning" no longer holds. Breaks transparency, reproducibility, safe sharing, and toolability at once — several stated project principles sit on those properties. |

The authoring-library middle ground captures scripting's real gap (generating many coordinated mutations from a rule) without giving up any data property: generation happens at authoring time, execution consumes only data.

### Composition

| Option | Assessment |
|---|---|
| **Layerable (chosen)** | Enables the comparison matrix the project vision implies (individual interventions and their combinations) without copy-paste drift; cost: conflict semantics must be designed and enforced. |
| Flat, self-contained | No conflict rules needed; but combined studies duplicate mutations across files, which drift apart silently — the failure mode lands exactly where the tool's credibility lives (comparisons). |

### Scenario vs. experiment

| Option | Assessment |
|---|---|
| **Separate (chosen)** | "Same conditions" is a structural guarantee, not a convention; one experiment file pins everything a published result depends on; scenarios stay reusable across experiments. |
| Combined per-run file | One file per run is a simpler mental model; but comparing N scenarios duplicates identical run parameters N times, and identical-conditions comparisons become a discipline problem. |

### File format

| Option | Assessment |
|---|---|
| **YAML + JSON Schema (chosen)** | Comments and readability for human-authored documents; strictness recovered via mandatory schema validation. |
| JSON | Strict and universal, but no comments — wrong trade for files whose purpose is human-readable intervention descriptions. |
| TOML | Comments and strictness, but ordered nested operation lists get awkward fast. |

## Trade-off Analysis

The through-line: **every choice keeps executed scenarios as inert, structured, versioned data, and pushes all expressive power to authoring time or to deliberate vocabulary growth.** This is the same shape as ADR-0002 (new types = additive components, not core-loop edits) and ADR-0003 (minimal stable contract, disciplined internals): the artifact that circulates is small, inspectable, and stable; the flexibility lives behind it. The main accepted cost across all four sub-decisions is upfront design work — an operation vocabulary, layer-conflict semantics, two schemas instead of one — paid once, in exchange for properties (validation, safe sharing, guaranteed-fair comparisons) the project's credibility rests on.

## Consequences

- An initial operation vocabulary must be designed for v0.1 — small (roughly `add_lane`, `remove_lane`, `close_edge`, `set_signal_timing`, `add_signal_phase`) and grown deliberately; each new operation is reviewed like a schema change, with documentation of its parameters and semantics.
- JSON Schemas for both scenario and experiment files are published artifacts, versioned alongside the network format from ADR-0003; validation is mandatory before any run.
- Layer-conflict semantics need a concrete design: at minimum, applying layers that touch the same network element produces a hard, explanatory error unless explicitly resolved.
- The Python authoring library becomes part of the `/python` package's surface: helpers to construct operations, query the base network at authoring time, and emit validated scenario files.
- Stable element IDs in the network file format are now load-bearing for two consumers (kernel loading, scenario references) — the network format design (ADR-0003 action item 1) must guarantee ID stability across regenerations of the same network version, and define what happens to scenario references when the base network version changes (at minimum: scenarios declare their base version and applying them to a different version is an error, not a guess).
- Experiment files are the citation unit for results: any published comparison should be reproducible from its experiment file + pinned data artifacts alone.
- The simulator never executes scenario-supplied code — this is a security/trust invariant of the eventual public sandbox, not just a style preference.
- Revisit if v0.1 authoring reveals the vocabulary friction is materially worse than expected (e.g. every scenario needs a new operation) — that would suggest the operation granularity is wrong, not that scripting is needed.

## Action Items

1. [ ] Design the v0.1 operation vocabulary (the ~5 operations above) with parameter schemas and semantics documentation.
2. [ ] Write the JSON Schemas for scenario and experiment files; wire validation into the scenario loading path from day one.
3. [ ] Define layer-conflict detection rules (same-element touches across layers ⇒ hard error with explanation).
4. [ ] Coordinate with the network file format design (ADR-0003 action item 1): stable element IDs across regenerations, and version-mismatch behavior for scenario references.
5. [ ] Sketch the Python authoring library API (construct ops, query base network, emit validated YAML) — can be minimal for v0.1.
