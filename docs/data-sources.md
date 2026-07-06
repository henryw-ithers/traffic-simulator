# Data Sources

**Last updated:** 2026-07-06 (initial corridor reconnaissance)
**Corridor coverage evidence:** [osm-lane-audit.md](osm-lane-audit.md) (regenerable)

Raw and derived datasets are **never committed** (`/data` is gitignored). Fetch them with the documented scripts below; each caches and supports `--force`:

```bash
pip install -e "python[dev,data]"
python python/scripts/fetch_corridor_osm.py         # → /data/osm/
python python/scripts/fetch_toronto_open_data.py    # → /data/open/
python python/scripts/audit_osm_lanes.py            # → docs/osm-lane-audit.md
```

## Licensing summary

| Source | License | Attribution required |
|---|---|---|
| OpenStreetMap (road network, via Overpass/osmnx) | [ODbL 1.0](https://www.openstreetmap.org/copyright) | "© OpenStreetMap contributors". **Share-alike:** any published *derived database* (e.g. our network files) must be ODbL-compatible — flag before redistributing derived network data. |
| City of Toronto Open Data (all datasets below) | [Open Government Licence – Toronto](https://open.toronto.ca/open-data-license/) | "Contains information licensed under the Open Government Licence – Toronto." (Several packages report no license in CKAN metadata; the portal's blanket license applies.) |

## Road network

- **OpenStreetMap** drive network for the corridor bbox `(-79.475, 43.650, -79.395, 43.745)`; way tags for lanes/turn-lanes/speed, plus `type=restriction` relations fetched separately (osmnx graphs don't retain relations).
- **Corridor tagging quality (2026-07-06 audit):** `lanes` coverage is 98–100% everywhere that matters; `turn:lanes` ~30–40% on corridor arterials (lane-connectivity inference is a real but bounded workload); `maxspeed` 25–100% by street (defaults needed); 753 turn-restriction relations in-bbox. Details in the [audit](osm-lane-audit.md).
- Toronto Centreline (City open data) remains available as a cross-reference if OSM geometry proves problematic; not fetched yet.

## Traffic — turning movement counts (demand input + consistency checks)

- **Dataset:** [Traffic Volumes – Multimodal Intersection Turning Movement Counts](https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/) (CKAN package `811c4c10-7e5d-4c76-8d42-dab4e31c8265`); vehicles/bikes/pedestrians by approach and movement, 1984→present, refreshed frequently (last 2026-07-05). Datastore-queryable; raw data resources per decade.
- **Corridor verdict: excellent.** 314 counted locations in the study bbox. Every key junction has a recent 14-hour count: Allen/Eglinton W + E **2026-03-24**, Bathurst/Eglinton 2026-03-24, Dufferin/Eglinton 2026-01-14, Bathurst & Dufferin/St Clair 2025-10-18, Bathurst/Bloor 2026-05-13, Dufferin/Bloor 2025-09-20.
- Supports a **2025–2026 baseline year** for v0.1 demand generation (ADR-0005).

## Traffic — travel times (validation-critical)

- **Dataset:** [Travel Times – Bluetooth](https://open.toronto.ca/dataset/travel-times-bluetooth/) (`61321d76-a02f-459f-bcc9-d4c4d9b86395`): 5-minute averaged sensor travel times, **2014–2017 only, dormant since 2019**. 60 routes citywide; 14 route geometries intersect our bbox (identities need a map check against Eglinton specifically — route IDs are opaque codes).
- **Era caveat:** 2014–2017 falls inside Eglinton Crosstown LRT construction (roughly 2013–2024), which heavily distorted corridor traffic. These travel times describe construction-era conditions and are a poor validation target for a 2025–2026 baseline.
- **Corridor verdict: GAP for a modern baseline.** No current public travel-time source found. Related but not useful here: King St Transit Pilot Bluetooth datasets (different corridor).

### Options analysis for closing the gap (2026-07-06; decision: floating-car primary)

| Option | Cost | Effort | Data quality for v0.1 | Open-science fit |
|---|---|---|---|---|
| **Floating-car GPS runs (chosen primary)** | ~0 | High (Henry's driving time) | Good means; thin variability (one driver/vehicle — state as limitation) | Excellent — raw GPX publishable |
| Commercial probe data (TomTom Move/HERE/INRIX) | $$$ | Low | Excellent | Poor — license forbids redistribution; black-box processing |
| Sampled routing-API estimates (Google/TomTom APIs) | ~0–$ | Low | Moderate — validating our model against *their* model | Weak — ToS limits storing/republishing |
| TTC GTFS-Realtime vehicle positions as proxy | 0 | Medium | Weak for car times (dwell removal, proxy assumptions); OK for relative patterns | Good |
| Ask the City / FOI (internal travel-time system likely still runs; Crosstown before/after studies probably exist) | 0 | Trivial + weeks of waiting | Unknown; possibly excellent | Good |
| City traffic-camera images | 0 | Medium | Not travel times — earmarked for the **queue-observation** gap instead | Good |

**Plan of record:** floating-car runs as the primary validation source (protocol doc to be written before calibration begins: route legs, AM/PM/off-peak periods aligned with count periods, 6–10 runs per direction per period, floating-driver technique, per-run condition log, calibration/validation split declared up front — see validation.md's hold-out discipline). In parallel, email/FOI the City (free; might surface the unpublished successor to the Bluetooth program or Crosstown post-opening studies). Camera images earmarked for queue observations. Probe data and routing-API sampling are fallbacks only if the above under-deliver.

**When this is needed:** consumed at the **calibration milestone** (after kernel physics, network format, and demand generation exist). Time-sensitivity is moderate, not urgent: runs should be collected reasonably close to the count era (counts are 2025–2026) so baseline conditions match — months of slack, not years. The City email/FOI should go early because its latency is weeks-to-months. See the **signal timing** section for the one genuinely perishable dataset (rolling 7-day window, archived by our fetch script).

## Traffic — midblock speeds/volumes (supplementary)

- **Dataset:** [Traffic Volumes – Midblock Vehicle Speed, Volume and Classification Counts](https://open.toronto.ca/dataset/traffic-volumes-midblock-vehicle-speed-volume-and-classification-counts/) (`7a0ac637-43da-4e42-a79c-6d8279e21d85`), 24–168 h continuous counts since 1993, refreshed 2026-07-06. Point speeds/volumes — not corridor travel times, but usable as spot validation of simulated link speeds. Corridor coverage not yet audited.

## Traffic signals — timing and controller type (model input)

- **Datasets:** [Traffic Signals Tabular](https://open.toronto.ca/dataset/traffic-signals-tabular/) (`1a106e88-…`, refreshed 2026-07-04): all ~2,550 signals with `SIGNALSYSTEM` and `CONTROL_MODE` per intersection, plus data dictionary. [Traffic Signal Timing](https://open.toronto.ca/dataset/traffic-signal-timing/) (`7dda2235-…`, refreshed daily): phasing and interval sequences for the **past 7 days** at ~2,300 TransSuite signals; **excludes SCOOT/SCATS adaptive signals**.
- **Corridor verdict: found, with a plan-affecting finding.** All key corridor junctions are on TransSuite (so their timing *is* in the timing dataset). Because the portal serves only a **rolling 7-day window**, `fetch_toronto_open_data.py` archives a dated snapshot on every run (`/data/open/signal_timing/`) — run it at least weekly once corridor timing matters, and back up the accumulated snapshots. Control modes: predominantly **semi-actuated** — Eglinton/Allen is `SA1` (south jct) and `SAV` (north jct, presence loops + vehicle extensions); Bathurst/Eglinton, St Clair junctions, Dufferin/Bloor all `SA1`; only Dufferin/Eglinton and Bathurst/Bloor are fixed-time (`FT`). Legend (from the data dictionary): SAV = semi-actuated, presence loops, vehicle extensions, no ped buttons; SA2 = semi-actuated with ped push buttons; FXT/FT = fixed time.
- **Consequence:** per the ADR-0002 amendment, the vehicle-actuated signal policy moves up the schedule — a fixed-time-only v0.1 cannot faithfully reproduce the corridor's dominant control mode. (Signal *state* vs *policy* decoupling already anticipates this.)

## Queue observations (validation)

- **Confirmed absent** from the open data portal (searched 2026-07-06). Fallback per validation.md: manual observation / video at Allen/Eglinton during peak periods.

## Deferred (later phases)

- TTC GTFS static + realtime, station usage, ridership; census/TTS demand data — out of v0.1 scope (cars only), to be inventoried when transit phases begin.
