# ADR-0007: v0.1 network file format — lane-level logical schema, readable stable IDs, columnar container

**Status:** Accepted (Henry, 2026-07-06 review) — schema, IDs, and versioning as proposed; container **amended during review** from the originally proposed canonical JSON to columnar-first (Parquet bundle)
**Date:** 2026-07-06
**Deciders:** Henry

## Context

ADR-0003 decided that Python builds the lane-level network and the kernel loads it through a **versioned, documented file format** — and deliberately left the concrete design to be settled during scaffolding, once real data was in hand. That evidence now exists ([osm-lane-audit.md](../osm-lane-audit.md), 2026-07-06): corridor `lanes` tagging is 98–100% complete, `turn:lanes` is 30–40% on the arterials (so Python must *infer* most lane-to-lane connectivity), 753 turn-restriction relations exist in the study area, and every key junction's signal is centrally documented with a City `PX` identifier, control system, and control mode.

The format has four consumers, and their requirements are already fixed by prior ADRs:

1. **The Rust kernel loader** — needs an unambiguous, validatable description of lane-level geometry, connectivity, and signals (ADR-0002's entity model).
2. **Scenario files (ADR-0004)** — reference network elements by **stable ID**; same-version regeneration must not shuffle IDs, and applying a scenario against a different network version is a hard error.
3. **Demand files (ADR-0005)** — trips carry explicit routes as sequences of the same stable IDs; the two formats share the ID and versioning conventions and are documented as a pair.
4. **Reproducibility** — a pinned network file is the artifact an experiment cites ("produced from network vX").

This ADR settles four coupled sub-decisions: the logical schema, the ID scheme, versioning/integrity, and the serialization container. The full field-level specification lives in [docs/formats/network-format.md](../formats/network-format.md) (draft, versioned alongside this ADR).

## Decision (proposed)

### 1. Logical schema: six record groups, lane-level, ECS-aligned

One file describes one loadable network:

- **`meta`** — format/version/provenance/CRS/integrity (see §3).
- **`nodes`** — point locations where segments meet: intersections, dead ends, and **boundary nodes** (flagged, because ADR-0005's v0.1 demand enters at measured boundary inflows).
- **`segments`** — directed stretches of road between two nodes (one per direction of travel), carrying name, road class, and source provenance. Segments exist mainly as the grouping/provenance layer; physics happens on lanes.
- **`lanes`** — the first-class simulation elements (ADR-0002: each lane its own graph element): parent segment, lane index (0 = curbside), length, speed limit, allowed modes (an **open list of mode strings**, not a closed enum — per ADR-0002's extensibility action item), and polyline geometry in projected meters.
- **`connections`** — lane-to-lane movements through a node (the lane-level turning graph): from-lane, to-lane, movement kind (`through`/`left`/`right`/`uturn`), and the signal phase that protects it, if any. Turn restrictions and inferred `turn:lanes` land here as *absent or present connections* — the file states the resolved truth; inference heuristics stay in Python and are documented in the builder.
- **`signals`** — one per signalized node: City `PX` cross-reference, recorded control mode (`FT`, `SA1`, `SAV`, … as observed), and the **initial timing plan** (ordered phases: durations, offset, and the connection movements each phase serves). Timing lives in the base network because ADR-0004's `set_signal_timing`/`add_signal_phase` operations mutate it — a scenario needs base state to diff against. Signal *control policy* is not in the file (it's a kernel-side swappable system per the ADR-0002 amendment); the file carries state and plan data only, so actuated/AI policies later require **additive** fields (detector placements), not schema surgery.

Zones, transit stops/routes, and anything beyond the car-only v0.1 scope are **not** in v1 of the format; they arrive as new record groups under the versioning rules below (additive ⇒ minor bump).

### 2. IDs: human-readable, structured, provenance-derived strings

Element IDs are strings with a typed prefix, derived deterministically from source-data identifiers:

```
node:249012345            # OSM node id
seg:15296123.2:wb         # OSM way id, split part 2, westbound
lane:15296123.2:wb:0      # curbside lane of that segment
conn:lane:…:wb:1->lane:…:nb:0   # from-lane -> to-lane
sig:px1307                # City of Toronto PX number (audit: Eglinton/Allen N)
```

Rationale: scenario YAML is a *human-authored document* (ADR-0004) — `close_edge: lane:15296123.2:wb:0` is reviewable and debuggable in a way opaque integers are not, and `sig:px1307` cross-references City datasets directly. The kernel interns strings to dense indices at load time, so runtime cost is a one-time mapping. *(Clarified 2026-07-06, portability review: PX is Toronto's jurisdiction-local signal reference, not part of the format — the format prescribes `sig:<local ref>` with the scheme documented per network, so other cities plug in their own identifiers.)*

**Stability contract:** the builder is deterministic — same inputs + same builder version ⇒ byte-identical file (this extends the project's determinism discipline to the *builder*, and CI can enforce it the same way). IDs are stable because they derive from source identifiers, not from iteration order. Across *different* network versions, IDs may change (OSM edits, re-splits); that is why scenarios pin `base_network` + version and mismatches are hard errors (ADR-0004) — no cross-version ID stability is promised, only cross-regeneration stability of the same version.

### 3. Versioning and integrity

The `meta` block carries:

- `format_version` (integer): breaking schema changes increment it; the kernel refuses formats newer than it knows. Additive record groups/fields are backward-compatible minor changes (`format_minor`).
- `network_name` + `network_version` (e.g. `toronto-corridor-v1` / `2026.07-r1`): the human-level identity that scenarios and experiments pin.
- `content_hash`: SHA-256 over the canonical serialization (hash field excluded) — experiments record it; "same version" claims become checkable.
- `provenance`: source snapshot dates (OSM fetch date, signal/timing snapshot date), builder version, corridor bbox.
- `crs`: the projected CRS of all coordinates (proposed: EPSG:32617 / UTM 17N — meters). The kernel does no geodesy; coordinates are opaque meters to it.

### 4. Container: columnar from day one — a zip bundle of Parquet tables plus `meta.json`

*(Amended at the 2026-07-06 review: the original proposal was canonical JSON with a city-scale columnar revisit; Henry opted for columnar-first so the container is scale-ready from the start and no format migration is ever needed.)*

A network file is `<name>.network.zip` containing:

- `meta.json` — the §3 metadata block, kept as tiny human-readable JSON;
- one Parquet file per record group (`nodes.parquet`, `segments.parquet`, `lanes.parquet`, `connections.parquet`, `signals.parquet`), each mirroring the logical schema exactly, rows sorted by `id`.

Costs accepted with this choice, and their mitigations:

- **Kernel dependency:** the loader takes on `arrow-rs`/`parquet` (crate confirmed at implementation) — heavier than `serde_json`, accepted.
- **Determinism/hashing discipline:** Parquet bytes are only reproducible if writer settings and library version are pinned. The builder pins pyarrow version + writer options (compression, row-group size — specified in the format doc), preserving the "same inputs ⇒ byte-identical file" contract; `content_hash` is defined over the table members in a fixed order (see format doc).
- **Human inspectability:** Parquet isn't reviewable in a text editor, so the builder ships a **non-normative `--export-json` debug view** (canonical JSON of the same logical content) for review and diffing. The zip member `meta.json` keeps identity/provenance readable without tools.

**Explicitly not settled here:** ADR-0003 action item 3 (numpy vs Arrow for *runtime* result transfer) is untouched — the file container and the FFI boundary remain independent decisions; a columnar file neither requires nor precludes Arrow at the FFI.

## Options Considered

### Logical schema

| Option | Assessment |
|---|---|
| **Lane-level records with explicit connections (chosen)** | Matches ADR-0002's data model one-to-one; the v0.1 research question (a turning lane at Eglinton/Allen) is expressible as *adding one lane record and its connections*; costs Python an inference step for the ~60–70% of arterial edges without `turn:lanes` — but that work is mandated by ADR-0002/0003 regardless of format. |
| Segment-level file, kernel expands to lanes | Smaller file, simpler builder; but moves lane inference *into the kernel* — exactly the heuristic-laden geo-work ADR-0003 assigned to Python, and it makes the file no longer the ground truth scenarios reference (`add_lane` would mutate something the kernel then re-derives). |
| Reuse OSM XML / GraphML directly | No format to design; but then the contract *is* OSM's tagging chaos (the audit's 30–40% `turn:lanes` coverage becomes the kernel's problem), IDs aren't stable under regeneration, and scenario references have nothing clean to point at. Rejected by ADR-0003's reasoning already. |

### ID scheme

| Option | Assessment |
|---|---|
| **Readable structured strings, provenance-derived (chosen)** | Reviewable scenarios/demand files (a stated ADR-0004 property); direct cross-reference to City PX numbers; deterministic derivation gives regeneration stability; cost: strings are bulkier than ints (mitigated by load-time interning; irrelevant at corridor scale). |
| Opaque sequential integers + provenance side-table | Compact; but IDs depend on assignment order (fragile stability), and every scenario/demand file becomes unreadable without the side-table — hostile to review and to the transparency principle. |
| Content-hash IDs | Stable under identical content, no assignment order; but any attribute fix changes the ID (worst possible property for scenario references), and hashes are unreadable. |

### Versioning/integrity

| Option | Assessment |
|---|---|
| **format_version + named network version + content hash (chosen)** | Distinguishes "schema changed" from "network changed"; hash makes pinning checkable; cheap to implement. |
| Git-tracking the network file instead | The file is derived data from gitignored inputs — committing it contradicts the repo's data policy; hashing gives the same pinning without the repo weight. (A pinned file can still be *published* alongside results, per the ODbL note in data-sources.md.) |

### Container

| Option | Assessment |
|---|---|
| **Parquet tables + `meta.json` in a zip (chosen at review)** | Columnar, scales to city size with no future migration, dovetails with a possible Arrow FFI future; costs a heavyweight kernel dependency now, pinned-writer discipline for determinism, and a JSON debug export for reviewability — all accepted (Henry, 2026-07-06). |
| Canonical JSON, optional gzip (original proposal) | Human-inspectable, diffable, trivially hashable, zero new kernel dependencies; but slower/bulkier at city scale and implies a later container migration — rejected at review in favor of being scale-ready from day one. Survives as the builder's non-normative `--export-json` debug view. |
| GeoPackage (SQLite) | GIS-tool friendly; but drags SQLite + geo schema conventions into the kernel, weak diffability, and canonical-form hashing is awkward. Better as an optional *export* from the builder for inspection. |
| Custom binary | Maximum control, maximum cost: a parser to verify on both sides, no tooling, opaque to review. Nothing at v0.1 scale justifies it. |

## Trade-off Analysis

The through-line matches ADRs 0003/0004: **the artifact that circulates is small, inspectable, and pinned; complexity lives in the builder, not the contract.** Readable IDs, a human-readable `meta.json`, and the builder's JSON debug export keep the transparency property; the columnar container (per the review amendment) buys city-scale readiness up front at the price of a kernel Arrow dependency and pinned-writer determinism discipline. The main accepted cost remains builder-side: deterministic ID derivation and lane-connectivity inference are real work — but that work is mandated by prior ADRs regardless of how the file is spelled.

## Consequences

- `docs/formats/network-format.md` becomes a versioned, published spec; changes to it are reviewed like schema changes (same rhythm as ADR-0004's operation vocabulary).
- The Python builder gains a determinism obligation (same inputs ⇒ byte-identical file), testable in CI alongside the kernel's determinism harness. With the columnar container this additionally requires pinning the pyarrow version and Parquet writer options in the builder's environment.
- The kernel loader takes an `arrow-rs`/`parquet` dependency when implemented; the builder ships a non-normative `--export-json` debug view so network content stays reviewable.
- The kernel's first real milestone becomes concrete: load a v1 file, validate referential integrity, intern IDs, and expose the loaded network via the existing `Simulation` API — this is also when the ECS crate decision (ADR-0002 action item 1) fires.
- The demand format (ADR-0005 action item 1) inherits the ID and versioning conventions defined here; it should be specified as a sibling section/file when demand work starts.
- Signal timing plans in the file come from the City's rolling 7-day snapshots (archived by `fetch_toronto_open_data.py`) — the provenance block records which snapshot.
- If lane-connectivity inference proves unreliable for the corridor (audit says 30–40% explicit coverage), the format is unaffected — quality problems are builder problems; the file always states resolved truth.

## Action Items

1. [x] Henry: review and accept/amend this ADR. — *Accepted 2026-07-06: schema, IDs, versioning as proposed; container amended to columnar-first (Parquet bundle) during review.*
2. [ ] Flesh out `docs/formats/network-format.md` from skeleton to field-complete v1 spec as the builder is implemented.
3. [ ] Implement the Python builder (OSM extract → v1 file) with a builder-determinism test in CI.
4. [ ] Implement the kernel loader with validation (referential integrity, connectivity sanity) — triggers the ECS crate decision (ADR-0002 #1).
5. [ ] Emit the real corridor network as the first pinned artifact and record its content hash in the first experiment file.
