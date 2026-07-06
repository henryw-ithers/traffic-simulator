# Toronto Transportation Digital Twin

A realistic, from-scratch transportation simulation platform for Toronto that models traffic, transit, and people movement using real-world data.

The long-term goal is an open, transparent decision-support tool capable of evaluating proposed infrastructure changes before they are built — traffic light retiming, transit signal priority, new lanes, new roads, new transit lines, road closures, and more.

The emphasis is **transparency, not automation** — this tool is meant to inform transportation engineers and the public, not replace professional judgment.

---

## Table of contents

- [Vision](#vision)
- [Philosophy](#philosophy)
- [Why build the simulation kernel from scratch](#why-build-the-simulation-kernel-from-scratch)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Simulation layers](#simulation-layers)
- [Neighbourhood / zone model](#neighbourhood--zone-model)
- [Scenario engine](#scenario-engine)
- [Performance metrics](#performance-metrics)
- [Data sources](#data-sources)
- [Validation & calibration](#validation--calibration)
- [Roadmap](#roadmap)
- [Initial project scope (v0.1)](#initial-project-scope-v01)
- [Example research questions](#example-research-questions)
- [Getting started](#getting-started)
- [Contributing](#contributing)
- [License](#license)

---

## Vision

Build a simulation platform capable of answering, with evidence rather than opinion:

- Would this improve traffic?
- Would this improve transit?
- Who benefits, and who is negatively affected?
- Is the improvement worth the cost?

Example proposals the platform should eventually be able to evaluate:

- Traffic light timing changes and adaptive signal control
- Bus and streetcar dispatch optimization
- Transit signal priority
- Lane additions/removals, turning lanes
- New roads and arterials
- New transit lines and subway extensions
- Construction detours and road closures
- Bus lanes and bike lanes
- Transit frequency changes
- New housing/office developments and population growth

## Philosophy

- **Build the simulation kernel from scratch.** See [below](#why-build-the-simulation-kernel-from-scratch) for why, and what this does and doesn't mean in practice.
- **Every assumption should be visible.** No parameter or model choice should be hidden inside a black box.
- **Every result should be reproducible.** Same inputs + same scenario + same seed = same output, always.
- **Prefer real public datasets** over synthetic data wherever possible.
- **Optimize for moving people, not vehicles.** A metric like person-minutes of delay matters more than vehicle throughput alone.
- **Explain why, not just what.** Simulations should support explanations of causes, not just report numbers.
- **Modular subsystems.** Each layer (infrastructure, demand, modes, scenarios, evaluation) should be independently improvable and testable.

## Why build the simulation kernel from scratch

Mature open-source traffic simulators already exist (e.g. SUMO, MATSim) and represent decades of validated work on car-following, lane-changing, and signal logic. We are deliberately not building on top of one of them for the core simulation loop, for two reasons worth stating honestly and separately:

- **Ownership and transparency of the model itself.** The core principle of this project is that every assumption behind a result should be inspectable. That's a much stronger claim when the physics (car-following, lane-changing, signal logic, transit dwell/boarding behavior) is code this project wrote and fully understands, rather than an external engine's implementation details.
- **Architectural freedom for open-ended modularity.** The long-term vision is for users to freely add and combine entirely new infrastructure — new road types, new transit lines and modes, novel signal behaviors, custom zone constructs — as first-class objects, not as configuration of a fixed built-in set. This isn't a claim that SUMO/MATSim can't model specific things we need today; it's that their internal data models and extension points were built around the scenarios their own communities needed, not for arbitrary new categories to be defined on equal footing with the built-ins. That's a real architectural ceiling on how far an "add anything" scenario engine could be pushed on top of an existing engine, and it's a harder property to retrofit than to design in from the start.
- This is a conscious trade-off for depth of understanding and long-term extensibility over speed of delivery. It means v0.1 will take longer to reach parity with what an existing engine could produce out of the box.
- "From scratch" applies to the **simulation kernel and scenario/evaluation logic** — it does not mean reinventing general-purpose infrastructure. We still depend on:
  - OS-level and standard geospatial/graph libraries (see [Architecture](#architecture))
  - A relational/spatial database (PostGIS) rather than a hand-rolled data store
  - Standard data formats (OSM, GTFS, census extracts) rather than custom ones
- As an independent sanity check (not a dependency), it may be useful to compare our kernel's output against an existing engine (e.g. run the same OSM extract through SUMO) to catch fundamental modeling errors before comparing against real-world data.

See [ADR-0001](docs/adr/0001-simulation-kernel-from-scratch.md) for the full decision record, options considered, and consequences.

## Architecture

```
Raw Data (OSM, GTFS, census, traffic counts)
        │
        ▼
Data Import Layer (Python)
        │
        ▼
Road Graph  +  Transit Graph
        │
        ▼
Demand Model (Python)
        │
        ▼
Simulation Kernel (Rust)  ◄── scenario mutations
        │
        ▼
Scenario Engine (Python, orchestrates Rust kernel runs)
        │
        ▼
Evaluation Engine (Python) — metrics, calibration, comparison
        │
        ▼
Visualization (Python / web)
        │
        ▼
Optimization / AI Layer (later phases)
        │
        ▼
Natural Language Interface (later phase)
```

### Tech stack

| Layer | Choice | Why |
|---|---|---|
| Simulation kernel | **Rust** | Performance and memory safety for a tick-by-tick agent simulation loop; the core the project's transparency claims rest on. |
| Kernel ↔ Python bridge | **PyO3 / maturin** | Exposes the Rust kernel as a native Python extension module so the rest of the platform can call it directly. |
| Data import, scenario config, demand modeling, analysis, visualization | **Python** | Fast iteration; mature geospatial/graph/transit ecosystem (`osmnx`, `networkx`, `geopandas`, `shapely`, `gtfs-kit`/`partridge`). |
| Geospatial storage | **PostgreSQL + PostGIS** | De facto standard for road/transit/demand geospatial data at any real scale. |
| Scenario definitions | **Typed operation vocabulary in layerable YAML (schema-validated), authored by hand or via a Python authoring library** | Scenarios stay pure data — diffable, validatable, safe to share; scripting power lives at authoring time only. Experiments (which scenarios, seeds, demand, duration) are separate files that pin everything a published comparison depends on. See [ADR-0004](docs/adr/0004-scenario-definition-format.md). |
| Kernel entity model | **Entity-Component-System (ECS)**, lane-level graph, unified multi-modal representation | New infrastructure/mode types are added as new components/systems without touching the core simulation loop. See [ADR-0002](docs/adr/0002-core-simulation-data-model.md). |
| Kernel ↔ Python boundary | **Batch-run API over step()-structured internals; columnar data transfer; Python-built network loaded via a versioned file format** | Minimal public surface for v0.1, with internals disciplined so Phase 2's live control API is additive. See [ADR-0003](docs/adr/0003-kernel-python-interface.md). |
| Visualization | TBD — likely deck.gl/kepler.gl or a lightweight Leaflet map for spatial output | Deferred until v0.1 has something worth visualizing. |

## Repository layout

```
/core       Rust workspace — simulation kernel, PyO3 bindings
/python     Python package — data import, demand model, scenario engine,
            evaluation, visualization; calls into /core via bindings
/data       Gitignored. Local cache of fetched raw/derived datasets.
/docs       Architecture decision records, validation methodology, data
            source notes, roadmap detail
```

Raw and derived datasets (OSM extracts, GTFS snapshots, census extracts) are **not committed to git**. They're fetched and cached locally via documented scripts, both to keep the repository small and to avoid ambiguity around redistribution rights for third-party data. See [Data sources](#data-sources).

## Simulation layers

### Layer 1 — Physical infrastructure

The city itself, independent of any traffic on it: roads, lanes, intersections, traffic signals, sidewalks, crosswalks, bike lanes, bus lanes, streetcar tracks, subway tunnels, stations, bus stops, streetcar stops.

### Layer 2 — Demand

Where people actually want to travel, originating from residences, offices, schools, universities, shopping centres, hospitals, entertainment venues, and transit stations. Demand varies by time of day, day of week, season, special events, construction, and (future) weather.

### Layer 3 — Transportation modes

- **Cars** — personal routing, congestion effects, lane changes, turning decisions.
- **Buses** — passenger count, capacity, boarding/dwell time, schedule adherence, headway, signal priority.
- **Streetcars** — fixed tracks, cannot freely change lanes, passenger loading, interaction with turning traffic, signal priority.
- **Subway** — stations, travel time, frequency, capacity, transfers, platform crowding.
- **Pedestrians** — walking speed, crosswalk timing, transfer time, station access.
- **Cyclists** — future expansion.

## Neighbourhood / zone model

Residential streets don't need microscopic simulation. Interior neighbourhood streets are modeled as **traffic zones** with: population, internal travel time, entry/exit points, local road capacity, speed limits, traffic calming effects, and cut-through penalties. Major roads and corridors receive full microscopic detail. This keeps simulation cost proportional to where the interesting behavior actually happens.

## Scenario engine

Every modification to the city is a **scenario**, layered on top of the base network — never a mutation of it. This keeps comparisons clean and reproducible.

Example scenarios: baseline (existing Toronto), add a turning lane, add a bus lane, new subway line, new road, adaptive traffic lights, an alternative transit line proposal. A scenario is defined as data (a typed, schema-validated list of operations against a versioned base network), not code, so scenarios can be authored, diffed, validated, and shared without touching the simulation kernel — and layered, so combined studies (e.g. bus lane + signal priority) compose from individual scenarios. Run parameters (seeds, demand, duration) live in separate experiment files, making "same conditions" comparisons a structural guarantee. See [ADR-0004](docs/adr/0004-scenario-definition-format.md).

## Performance metrics

Metrics are tracked across modes, not just for vehicles:

**Road** — average travel time, queue length, throughput, delay, number of stops.
**Transit** — passenger delay, schedule adherence, headway regularity, bus/streetcar bunching, crowding, transfer reliability.
**Pedestrians** — waiting time, crossing delay, walking distance.
**City-wide** — person-minutes of delay, accessibility, mode share, emissions (future), fuel consumption (future).

## Data sources

| Category | Sources |
|---|---|
| Road network | OpenStreetMap, Toronto Centreline |
| Traffic | Turning movement counts, traffic signal timing, road classifications (City of Toronto Open Data) |
| Transit | TTC GTFS static + GTFS Realtime, station usage, ridership reports |
| Demographics | Census data, employment data, population, land use, schools, hospitals, commercial centres |

All datasets are fetched from their public sources at build/run time rather than committed to the repo. Licensing and attribution terms for each source should be recorded in `docs/data-sources.md` before redistribution of any derived data.

## Validation & calibration

Before any optimization or AI result is trusted, the simulator must first demonstrate it can reproduce observed reality on the focus corridor. Calibration compares simulated output against:

- Observed travel times
- Traffic counts (e.g. via the GEH statistic, standard in traffic engineering)
- Queue lengths
- Transit ridership and bus/streetcar arrival times
- Station usage

Reproducibility mechanics that support this: seeded RNGs for all stochastic behavior, versioned scenario configs, and versioned/pinned input data snapshots, so a given commit + scenario + seed always produces the same result.

## Roadmap

- **Phase 1 — Baseline reproduction.** No AI. Reproduce existing traffic and transit behavior on the focus corridor and calibrate against real data. This is the foundation every later phase depends on.
- **Phase 2 — Optimization.** Classical optimization algorithms for signal timing, transit priority, queue management, applied to the calibrated Phase 1 model.
- **Phase 3 — Machine learning.** Adaptive traffic control, bus dispatch optimization, streetcar spacing, demand/incident prediction — trained and validated against the Phase 1 ground truth.
- **Phase 4 — Natural language interface.** A conversational layer over simulation results (e.g. "Why is Allen Road congested?", "What happens if I add another lane?"), backed by and explainable in terms of actual simulation output.

Phases 2–4 are intentionally left at vision-level detail for now — they'll be scoped in `docs/` once Phase 1 has produced a calibrated baseline to build on.

## Initial project scope (v0.1)

**Focus corridor:** Dufferin & Bloor → Bathurst & Bloor → St. Clair corridor → Eglinton Avenue West → Allen Road.

**Primary objective:** Understand congestion around the Allen Road / Eglinton bottleneck.

**v0.1 is deliberately narrow:**

1. Import the OSM road network for the focus corridor only, as a graph.
2. Static car-only traffic flow — no transit, no pedestrians, no AI (per Phase 1).
3. One scenario comparison (e.g. baseline vs. an added turning lane at Eglinton/Allen).
4. One headline metric: average travel time / delay.
5. Minimal visualization sufficient to inspect and sanity-check results.
6. Calibration against real traffic counts for the corridor.

Everything else in this document is deferred until v0.1 is calibrated.

## Example research questions

**Traffic** — Is the Allen Road/Eglinton bottleneck caused by signal timing or road capacity? Would another turning lane help? Would another north-south arterial significantly reduce congestion? How much traffic diverts through neighbourhood streets?

**Transit** — Would signal priority improve bus reliability? Can bus bunching be reduced through smarter dispatch? Would another rapid transit corridor outperform existing proposals? Which corridor provides the greatest reduction in person-minutes of delay?

**Infrastructure** — Is adding capacity better than optimizing operations? Which improvements provide the greatest benefit per dollar? Which neighbourhoods benefit, and which are negatively affected?

## Getting started

Project scaffolding (Rust workspace, Python package, build tooling) has not been created yet — this section will be filled in once `/core` and `/python` exist with a runnable v0.1.

## Contributing

Contribution guidelines will be added in `CONTRIBUTING.md` once the project has a runnable scaffold and coding conventions to document. See [AGENTS.md](AGENTS.md) for conventions when using AI coding assistants in this repo.

## License

[MIT](LICENSE)
