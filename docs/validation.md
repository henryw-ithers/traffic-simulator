# Validation & Calibration Methodology

**Status:** Methodology accepted; numeric thresholds provisional until real corridor data is inspected (marked TBD).
**Last updated:** 2026-07-06

The project's credibility rests on one claim: the simulator reproduces observed reality before it is used to evaluate anything hypothetical. This document defines what that claim means, how it is tested, and what "good enough to trust" is.

## Three distinct activities (never conflate them)

1. **Verification** — is the code correct? Does the kernel do what its model says it does (no bugs)? Covered by unit tests, property tests, the determinism harness (ADR-0003: same seed + platform ⇒ byte-identical), and cross-checks against an independent engine.
2. **Calibration** — tuning model parameters (car-following parameters, lane-change aggressiveness, signal compliance, etc.) so simulated output matches observed reality on the focus corridor.
3. **Validation** — testing the *calibrated* model against observations it was **not** tuned on. Only validation earns trust; calibration alone proves nothing (enough free parameters can fit anything).

## The consistency-check trap (ADR-0005 obligation)

v0.1 demand is *generated from* turning movement counts (boundary inflows + turning proportions, per [ADR-0005](adr/0005-demand-representation-and-routing.md)). Therefore:

> **Reproducing turning counts is a consistency check, not validation.** It confirms the demand generator and kernel don't lose or invent vehicles — necessary, but circular. True validation must come from observations that played no role in generating demand: travel times, queue lengths, saturation behavior.

Any report of calibration quality must label each comparison as *consistency* or *validation*. Conflating them is the fastest way to fool ourselves.

## Verification gates (pre-calibration)

These must pass before calibration is even attempted:

- **Determinism:** same seed + network + demand ⇒ byte-identical results on the same platform/binary, in CI from the first runnable kernel (ADR-0003).
- **Conservation:** every vehicle that enters either exits or is still present at sim end; no creation/loss. Exact, not statistical.
- **Physical sanity:** no negative speeds, no overlapping vehicles on a lane, no teleports; speeds bounded by limits + model parameters.
- **Cross-engine sanity check (ADR-0001):** run the same OSM extract through SUMO with comparable demand; corridor-level travel times and throughput should agree within order-of-agreement bounds (provisionally ±20% — this is a *bug detector*, not a validation standard; SUMO is not ground truth).

## Calibration targets & acceptance criteria (v0.1)

Standards below follow common traffic-engineering practice (UK DMRB/TAG conventions), provisional until corridor data is inspected.

| Quantity | Test | Acceptance (provisional) | Type |
|---|---|---|---|
| Link/turning flows | GEH statistic per count location, per time period | GEH < 5 for ≥ 85% of locations; no location > 10 | **Consistency** (v0.1 demand derives from these) |
| Corridor travel times | Simulated vs observed end-to-end and segment times, by period (AM/PM/off-peak) | Within ±15% or ±1 minute (whichever larger) for ≥ 85% of routes | **Validation** |
| Queue lengths | Simulated vs observed max/average queues at key approaches (esp. Allen/Eglinton) | Order-of-magnitude + pattern agreement (which approaches queue, when); numeric threshold TBD after data inspection | **Validation** |
| Bottleneck behavior | Onset/dissipation timing of congestion at Allen/Eglinton | Congestion appears/clears within TBD minutes of observed | **Validation** |

**GEH reference:** GEH = √(2(m−c)²/(m+c)), m = modeled hourly flow, c = counted hourly flow. Standard in traffic engineering because it tolerates proportionally more error on low flows.

## Stochastic discipline

- Results are **distributions, not single runs**: every reported metric comes from N seeded replications (provisionally N = 10) with mean and spread. A comparison ("scenario A vs B") is made on distributions with identical seed sets (per ADR-0004's experiment files, which pin seeds).
- Calibration is judged on the ensemble, not a lucky seed.

## Hold-out discipline

- Independent observations (travel times, queues) are split: a **calibration set** (tune against) and a **validation set** (never tuned against; e.g. hold out time periods or days). The split is declared *before* tuning begins and recorded in the experiment files.
- If validation fails, the model changes and re-validation uses fresh or re-split data — iterating against the validation set until it passes converts it into a calibration set.

## Transparency of assumptions

- Every calibrated parameter (car-following constants, reaction times, compliance rates) lives in **versioned config, never hardcoded** — a calibration result is a config artifact, referenced by experiment files like any other input.
- The chosen car-following model (IDM vs. Krauss vs. other — to be decided at implementation) is documented with its equations and the rationale, as a visible assumption.

## Data needed (v0.1 corridor) — to be confirmed against actual availability

| Need | Candidate source | Status |
|---|---|---|
| Turning movement counts (demand input + consistency) | City of Toronto Open Data (turning movement counts) | TBD — locate counts for corridor intersections; check dates/periods |
| Travel times (validation) | City of Toronto travel time studies; Bluetooth/WiFi sensor data if published; otherwise floating-car runs | TBD — this is the critical gap to resolve first; without independent travel times, v0.1 cannot be validated |
| Signal timing (input, not target) | City of Toronto signal timing data / FOI if needed | TBD |
| Queue observations (validation) | May require manual observation/video at Allen/Eglinton if no dataset exists | TBD |

**Open risk:** if no independent travel-time source exists for the corridor, validation degrades to queue-pattern plausibility — acceptable for a first milestone but must be stated honestly in any result. Resolving travel-time data availability is an early data-work priority.

## What "v0.1 is calibrated" means (exit criteria)

All of:
1. All verification gates pass in CI.
2. Consistency: GEH criterion met on turning counts.
3. Validation: travel-time criterion met on held-out observations (or, if travel-time data proves unavailable, the documented fallback with the limitation stated).
4. Queue/bottleneck pattern agreement at Allen/Eglinton.
5. All calibrated parameters committed as versioned config with the calibration experiment file that produced them.

Only after these hold do scenario comparisons (baseline vs. turning lane) carry weight.
