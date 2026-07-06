# AGENTS.md

Guidance for AI coding agents (and contributors) working in this repository.

## Project status

Pre-implementation. There is no `/core` or `/python` code yet — only planning docs. Do not scaffold large amounts of code speculatively; if asked to start implementation, confirm scope against [Initial project scope (v0.1)](README.md#initial-project-scope-v01) in the README first.

## Scope discipline

This project has a large long-term vision (transit, ML, natural language interface) documented in the README, but v0.1 is deliberately narrow: one road corridor, cars only, one scenario comparison, no AI. When implementing:

- Default to v0.1 scope unless the user explicitly asks for later-phase work (transit modes, optimization, ML, NLP interface).
- Don't add abstractions or generality "for later phases" that aren't needed by the task at hand — the roadmap phases are not yet designed in detail and premature generalization will likely guess wrong.

## Architecture (see README for full detail)

- **`/core`** — Rust workspace. The simulation kernel (agent/vehicle state, car-following, lane-changing, signal logic) lives here, built from scratch. Exposed to Python via PyO3/maturin bindings.
- **`/python`** — Python package. Data import (OSM/GTFS/census), demand modeling, scenario engine, evaluation/metrics, visualization. Calls into the Rust kernel through the compiled bindings; does not reimplement simulation physics.
- **`/data`** — gitignored. Never commit raw or derived datasets here; fetch them via documented scripts.
- **`/docs`** — architecture decision records, validation methodology, data source/licensing notes.

## Conventions (apply once code exists)

- **Rust**: format with `rustfmt`, lint with `clippy` (deny warnings in CI once CI exists). Prefer explicit, readable code over clever generics in the simulation loop — this code needs to be auditable, per the project's transparency principle.
- **Python**: format/lint with `ruff`/`black`, type-hint public functions. Prefer `dataclasses`/`pydantic` models for scenario and config schemas over loose dicts.
- **Scenarios** are data (YAML/JSON), not code — don't implement a new scenario as a hardcoded branch in simulation logic; it should be expressible as a graph mutation + demand override loaded from a scenario file.
- **Reproducibility**: any stochastic behavior must take an explicit seed; don't rely on unseeded global RNG state.
- **Signal control is a swappable policy, never baked into signal state handling** — AI signal control over a networked sensor grid is a core project goal (see ADR-0002's 2026-07-06 amendment). Don't write signal logic that assumes fixed-time plans structurally.
- Don't commit datasets, credentials, or `.env` files.

## Before recommending a build vs. reuse shortcut

The project has deliberately chosen to build the simulation kernel from scratch rather than adopt an existing engine (e.g. SUMO/MATSim), for two reasons: (1) transparency/ownership of the model, and (2) architectural freedom to add arbitrary new infrastructure/mode/behavior types as first-class citizens, which existing engines' data models and extension points weren't designed for — see README's "[Why build the simulation kernel from scratch](README.md#why-build-the-simulation-kernel-from-scratch)" and [ADR-0001](docs/adr/0001-simulation-kernel-from-scratch.md). Because of reason (2), the kernel's core abstractions (road/lane/signal/mode/zone) must be designed for extensibility from the start — don't hardcode assumptions that only the currently-known set of infrastructure/mode types will ever exist. Don't suggest replacing the kernel with an existing simulator; using an existing engine as an *external validation reference* is fine and encouraged.

## Architecture decisions require the user's sign-off

Henry (the project owner) wants to be included as a decider on every architecture decision — language/framework choices, storage choices, module boundaries, external dependencies, data formats, etc. Concretely:

- Don't unilaterally pick or change an architectural approach and present it as settled. Propose options with trade-offs and get explicit agreement first.
- Every non-trivial architecture decision should be captured as an ADR in `docs/adr/` (numbered sequentially, e.g. `0002-*.md`), following the format used in [ADR-0001](docs/adr/0001-simulation-kernel-from-scratch.md), with Henry listed under **Deciders**.
- If you're an agent picking up a task that implies an architectural choice not yet covered by an existing ADR, stop and ask rather than deciding silently.

## Commands

To be filled in once the Rust workspace and Python package are scaffolded (build, test, lint, run commands for each).
