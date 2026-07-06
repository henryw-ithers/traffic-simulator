# ADR-0006: Scaffolding choices — workspace layout, bindings, packaging, CI

**Status:** Proposed — implemented in the initial scaffold, awaiting Henry's review; each choice is cheap to reverse now and expensive later
**Date:** 2026-07-06
**Deciders:** Henry

## Context

ADRs 0001–0005 settled the architecture (Rust kernel + Python periphery via PyO3/maturin, monorepo with `/core` and `/python`, determinism harness in CI from the first runnable kernel). Actually creating the scaffold forced a set of smaller, concrete choices that no existing ADR pins down: names, packaging shape, binding ABI, CI provider, and which dependency decisions to *not* make yet. Per AGENTS.md, these are recorded here for sign-off rather than decided silently.

## Decision

### 1. Crate and package naming / layout

| Thing | Name | Location |
|---|---|---|
| Cargo workspace | — | `/core` (members: `kernel`, `bindings`) |
| Kernel crate (pure Rust, no PyO3) | `sim-kernel` | `/core/kernel` |
| Bindings crate (cdylib) | `traffic-sim-kernel` | `/core/bindings` |
| Compiled Python extension module | `traffic_sim_kernel` | built by maturin from `/core/bindings` |
| Python package (pure Python) | `traffic-sim` (import `traffic_sim`) | `/python` |

The kernel crate contains **zero PyO3**; the bindings crate contains **zero simulation logic**. This keeps the kernel testable with plain `cargo test` and enforces ADR-0003's thin-boundary rule structurally.

### 2. Bindings: pyo3 0.29, abi3 (Python ≥ 3.12)

The extension is built against the stable CPython ABI (`abi3-py312`): one wheel per platform works on every Python ≥ 3.12, so local Python upgrades and CI Python versions decouple from kernel rebuilds. Cost: a few abi3-unavailable optimizations/APIs — none relevant to a bulk-columnar boundary. `extension-module` is a cargo feature enabled only by maturin, so `cargo test --workspace` can link a real interpreter for binding tests.

### 3. Packaging: two installables, kernel not yet a declared dependency

`traffic-sim-kernel` (compiled, installed with `pip install ./core/bindings`) and `traffic-sim` (pure Python, `pip install -e python`) are separate. `traffic-sim` does **not** list the kernel in its dependencies while the kernel is unpublished — pip would try to resolve it from PyPI and fail. `traffic_sim.kernel` degrades to a clear install-hint error when the extension is missing, and pure-Python tests still run. Revisit when/if wheels are published.

### 4. CI: GitHub Actions, `ubuntu-latest` + `windows-latest`

The repo is hosted on GitHub; Actions is the zero-infrastructure choice. Two jobs, each on both OSes: **rust** (`cargo fmt --check`, `clippy --all-targets -- -D warnings`, `cargo test --workspace`) and **python** (pip-builds the bindings via maturin, explicit kernel import check, `ruff`, `black --check`, `pytest` including the determinism harness stub). The import check exists so pytest skip-markers can never silently mask a broken kernel build. Determinism scope per amended ADR-0003: the harness compares within one platform/binary; the two OS legs do not compare against each other.

### 5. Rust edition 2024, stable toolchain, `Cargo.lock` committed

Application workspace, not a library — the lockfile is part of reproducibility ("same commit ⇒ same binary" needs pinned deps).

### 6. Deliberately deferred (placeholders, not decisions)

- **ECS crate** (hecs/legion/shipyard — ADR-0002 left TBD): not chosen; the kernel stub has no entities yet. Choose when the first real component lands, as its own reviewed decision.
- **RNG crate**: inline 15-line SplitMix64 (public domain, integer-only, cross-platform-identical) as the seeded placeholder; adopting `rand`/`rand_chacha` is deferred until real stochastic behavior exists.
- **numpy vs. Arrow** for columnar transfer (ADR-0003 action item 3): no results cross the boundary yet; deferred until they do.

## Options Considered

| Choice | Alternative | Why not (for now) |
|---|---|---|
| abi3 wheel | Version-specific wheels (faster in some micro-paths) | Rebuild churn across Python versions buys nothing at this boundary's granularity |
| Two installables | maturin "mixed" project (Rust + Python source in one wheel) | Couples the periphery's release/dev loop to a Rust rebuild; blurs the `/core` vs `/python` boundary the README defines |
| GitHub Actions | Local scripts only / other CI | Determinism-in-CI is an ADR-0003 commitment; repo already lives on GitHub |
| Placeholder RNG inline | Adopt `rand` now | Dependency choices are sign-off decisions here; nothing stochastic exists yet to justify one |

## Consequences

- First push to GitHub validates the workflow file; until then CI is written but unexercised.
- `sim-kernel` is compiled into `traffic-sim-kernel`; publishing either to a registry would require a naming review first.
- **Local dev on Henry's PC:** initially scaffolded with the Windows *GNU* Rust toolchain (no MSVC Build Tools were installed), using a full WinLibs MinGW for the `dlltool`/`as` pair PyO3 needs on windows-gnu. Superseded same day: Henry installed VS Build Tools (2026/v18) and the local default host is now `x86_64-pc-windows-msvc` — matching CI's Windows leg — with the GNU toolchain and WinLibs removed.

## Action Items

1. [ ] Henry: review and either accept this ADR or flag choices to change (all still cheap to reverse).
2. [ ] Push to GitHub and confirm the CI matrix goes green on both OSes.
3. [ ] When the first real kernel state lands: pick the ECS crate (reviewed decision, updates ADR-0002's TBD).
