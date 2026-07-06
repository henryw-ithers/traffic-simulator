# AGENTS.md

Guidance for AI coding agents (and contributors) working in this repository.

## Project status

Scaffolded, pre-simulation. `/core` (Cargo workspace: `sim-kernel` + `traffic-sim-kernel` PyO3 bindings), `/python` (`traffic_sim` package), and CI (Ubuntu + Windows, determinism harness stub) exist — see [ADR-0006](docs/adr/0006-scaffolding-choices.md) — but the kernel is a stub with no simulation logic. The next milestones are the network and demand file formats (ADR-0003/0005) and the first real kernel state. Do not scaffold further code speculatively; confirm scope against [Initial project scope (v0.1)](README.md#initial-project-scope-v01) in the README first.

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

- **Rust**: format with `rustfmt`, lint with `clippy` (CI denies warnings). Prefer explicit, readable code over clever generics in the simulation loop — this code needs to be auditable, per the project's transparency principle.
- **Python**: format/lint with `ruff`/`black`, type-hint public functions. Prefer `dataclasses`/`pydantic` models for scenario and config schemas over loose dicts.
- **Scenarios** are data (YAML/JSON), not code — don't implement a new scenario as a hardcoded branch in simulation logic; it should be expressible as a graph mutation + demand override loaded from a scenario file.
- **Reproducibility**: any stochastic behavior must take an explicit seed; don't rely on unseeded global RNG state.
- **Signal control is a swappable policy, never baked into signal state handling** — AI signal control over a networked sensor grid is a core project goal (see ADR-0002's 2026-07-06 amendment). Don't write signal logic that assumes fixed-time plans structurally.
- **Toronto is the reference city, never a core assumption** — porting to other cities is a stated long-term goal (README "Beyond Toronto"). City-specific logic (municipal data-source URLs/schemas, local identifiers like PX signal numbers, corridor definitions) belongs in importer/adapter modules and data files, never in the kernel, file formats, scenario vocabulary, or evaluation logic. Litmus test when touching core code: "would this line change for Montreal?" — if yes, it's in the wrong layer. This is a *boundary* discipline, not license to build multi-city features now (see scope discipline above).
- Don't commit datasets, credentials, or `.env` files.

## Before recommending a build vs. reuse shortcut

The project has deliberately chosen to build the simulation kernel from scratch rather than adopt an existing engine (e.g. SUMO/MATSim), for two reasons: (1) transparency/ownership of the model, and (2) architectural freedom to add arbitrary new infrastructure/mode/behavior types as first-class citizens, which existing engines' data models and extension points weren't designed for — see README's "[Why build the simulation kernel from scratch](README.md#why-build-the-simulation-kernel-from-scratch)" and [ADR-0001](docs/adr/0001-simulation-kernel-from-scratch.md). Because of reason (2), the kernel's core abstractions (road/lane/signal/mode/zone) must be designed for extensibility from the start — don't hardcode assumptions that only the currently-known set of infrastructure/mode types will ever exist. Don't suggest replacing the kernel with an existing simulator; using an existing engine as an *external validation reference* is fine and encouraged.

## Architecture decisions require the user's sign-off

Henry (the project owner) wants to be included as a decider on every architecture decision — language/framework choices, storage choices, module boundaries, external dependencies, data formats, etc. Concretely:

- Don't unilaterally pick or change an architectural approach and present it as settled. Propose options with trade-offs and get explicit agreement first.
- Every non-trivial architecture decision should be captured as an ADR in `docs/adr/` (numbered sequentially, e.g. `0002-*.md`), following the format used in [ADR-0001](docs/adr/0001-simulation-kernel-from-scratch.md), with Henry listed under **Deciders**.
- If you're an agent picking up a task that implies an architectural choice not yet covered by an existing ADR, stop and ask rather than deciding silently.

## Commands

Rust (run from `core/`):

```bash
cargo test --workspace                                # all tests incl. determinism harness
cargo fmt --check                                     # formatting (CI-enforced)
cargo clippy --workspace --all-targets -- -D warnings # lint (CI-enforced)
```

Python (run from the repo root, inside a venv):

```bash
pip install -e "python[dev]"    # traffic_sim + pytest/ruff/black/maturin
pip install ./core/bindings     # build + install the compiled kernel (maturin)
pytest python/tests             # tests incl. determinism harness stub
ruff check python
black --check python
```

Rust-edit loop for the bindings: `maturin develop --manifest-path core/bindings/Cargo.toml`.

The kernel is intentionally not a declared pip dependency of `traffic_sim` while unpublished; `traffic_sim.kernel` raises a clear install hint if the extension is missing, and kernel-dependent tests skip. CI (`.github/workflows/ci.yml`) runs everything above on Ubuntu and Windows and fails if the kernel extension fails to import.
