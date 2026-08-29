# Learning roadmap — background for building this project

**Last updated:** 2026-07-06

Study guide for the background knowledge this project assumes, ordered by when the project actually needs it. Links verified 2026-07-06; where no direct link is given, a **search term** is provided instead of a guessed URL.

**Honest assessment of video coverage per topic:**

| Topic | YouTube coverage |
|---|---|
| Rust | Excellent — full courses, beginner to expert |
| Data-oriented design / ECS | Good — the canonical talks are all on YouTube |
| Traffic flow fundamentals | Decent — university lecture series (NPTEL, UNSW) |
| **Car-following math, calibration, microsim practice** | **Weak** — this is book/paper territory; interactive demos beat video |
| Signal control | Decent for intuition, thin on engineering detail |
| Geo stack (OSMnx/CRS) | Thin — docs and written tutorials are better |

The two resources doing most of the work here are not videos: **Treiber & Kesting, *Traffic Flow Dynamics*** (the book by IDM's inventor) and **the Rust Book**. Treat video as scaffolding around those.

---

## Tier 1 — Needed for the next work (builder, loader, ECS decision, first physics)

### 1a. Rust — ownership, borrowing, lifetimes

Blocking for all kernel work. Path: watch a structured series alongside reading [the Rust Book](https://doc.rust-lang.org/book/), then do [Rustlings](https://github.com/rust-lang/rustlings) exercises — Rust is not learnable by watching alone.

- **Let's Get Rusty — "The Rust Lang Book" playlist.** Chapter-by-chapter companion to the official book; the standard beginner path. *Search: `Let's Get Rusty Rust Lang Book playlist`*
- **[Jon Gjengset — "Crust of Rust" series](https://www.youtube.com/c/JonGjengset).** Intermediate/advanced deep dives (lifetimes, iterators, smart pointers, macros). Not a starting point; come back once ownership clicks and you want to know *why*.
- freeCodeCamp and Tensor Programming both have full-length Rust courses if you prefer one long sitting. *Search: `freeCodeCamp Rust programming course`*

### 1b. Data-oriented design and ECS

Directly informs the imminent ECS crate decision (ADR-0002 action item 1).

- **[Mike Acton — "Data-Oriented Design and C++" (CppCon 2014)](https://www.youtube.com/watch?v=rX0ItVEVjHc).** The canonical argument for why data layout beats abstraction in hot loops. C++ examples, but the thinking is language-agnostic and it's the intellectual root of ECS.
- **Bevy-ECS Explained (Andreas Monitzer, Rust Vienna 2023).** ~35 min; covers archetype vs sparse-set storage — exactly the axis our crate candidates (hecs/legion vs shipyard) differ on. *Search: `Bevy ECS explained Rust Vienna Monitzer`*
- Written and better than most video here: [Richard Fabian's *Data-Oriented Design*](https://www.dataorienteddesign.com/dodbook/) (free) and Glenn Fiedler's ["Fix Your Timestep!"](https://gafferongames.com/post/fix_your_timestep/) — the latter is short and maps straight onto our `step(dt)` loop.

### 1c. OSM data model, OSMnx, coordinate systems

Needed to write the network builder. Video is genuinely weak here; the docs are good.

- **[OSMnx documentation + examples gallery](https://osmnx.readthedocs.io/)** and [Geoff Boeing's introduction](https://geoffboeing.com/2016/11/osmnx-python-street-networks/) (he wrote the library).
- For CRS intuition — why we project WGS84 lat/lon into UTM meters — any "map projections explained" video works; Vox's is the well-known one. *Search: `why all world maps are wrong Vox projections`*
- OSM tagging conventions are best learned from the [OSM Wiki](https://wiki.openstreetmap.org/wiki/Key:highway) directly, cross-referenced against our own [audit](osm-lane-audit.md).

### 1d. Traffic flow fundamentals

- **[Shockwave traffic jam experiment (Sugiyama et al., Nagoya)](https://www.youtube.com/watch?v=DMK4Xp7g5gI).** 22 cars on a circular track spontaneously produce a standing jam with no obstruction. Three minutes, and it's the single best demonstration of why microsimulation is worth doing — this behaviour *emerges* from car-following rules; nobody programs it in.
- **[CVEN9422 (UNSW) — Traffic flow theory, part 1](https://www.youtube.com/watch?v=nzeHzzqFIYk).** Fundamental diagram, Greenshields, time-space diagrams. University lecture pace, correct content.
- **[NPTEL — Traffic Engineering & Management (IIT Bombay)](https://nptel.ac.in/courses/105101008).** Full course; the early lectures cover fundamental parameters and relations of traffic flow, stream models, and [microscopic modelling](https://www.youtube.com/watch?v=4k-yIrPu5hA). Also [Traffic Stream Characteristics](https://www.youtube.com/watch?v=3XaTwQIugJ4) and [Traffic flow modeling](https://www.youtube.com/watch?v=YbERBok9s0I). Dry, but it is the actual curriculum.

### 1e. Car-following models (IDM) — the first real physics

**Video will not get you there.** The material to work from:

- **Treiber & Kesting, *Traffic Flow Dynamics*** — chapters on car-following and lane-changing. Treiber invented IDM; Kesting co-invented MOBIL.
- **[traffic-simulation.de](https://traffic-simulation.de/)** — Treiber's own browser simulations of IDM/MOBIL with live parameter sliders. Change the politeness factor and watch lane-changing behaviour shift. Worth more than any lecture for building intuition, and it's the closest thing to a preview of what we're building.
- The original papers are readable: Treiber, Hennecke & Helbing (2000) for IDM; Kesting, Treiber & Helbing (2007) for MOBIL.
- [SUMO's car-following documentation](https://sumo.dlr.de/docs/Definition_of_Vehicles,_Vehicle_Types,_and_Routes.html) explains the model zoo clearly even though we aren't using SUMO.

### 1f. Signal control — with emphasis on actuated

The recon found our corridor is predominantly semi-actuated, so this moved from "later" to "soon."

- **Practical Engineering — "How Do Traffic Signals Work?"** Best general-audience explanation of detection loops, controllers, and actuated logic. [Written version](https://practical.engineering/blog/2019/5/11/how-do-traffic-signals-work); the video is on the same channel. *Search: `Practical Engineering how do traffic signals work`*
- **Road Guy Rob** — a working traffic engineer's channel; good on why signals behave the way they do at real intersections. *Search: `Road Guy Rob traffic signals green light`*
- For engineering detail (cycle/split/offset, Webster's formula, ring-barrier structure, gap-out vs max-out), the FHWA **Signal Timing Manual** is the free authoritative text. *Search: `FHWA Signal Timing Manual PDF`*

---

## Tier 2 — Before calibration

- **Determinism and floating point.** Why `a+b+c ≠ a+c+b`, and why cross-platform transcendentals differ (already settled in ADR-0003's amendment). *Search: `Computerphile floating point`*
- **PRNGs.** Seeding, streams, why clock-seeding is banned here. Our SplitMix64 placeholder is 15 lines — read it in [`core/kernel/src/rng.rs`](../core/kernel/src/rng.rs).
- **Calibration statistics.** GEH, hold-out discipline, replication — mostly already written down in [validation.md](validation.md). The **FHWA Traffic Analysis Toolbox Volume III** is the practitioner's guide to microsimulation calibration. *Search: `FHWA Traffic Analysis Toolbox Volume III`*
- **Graph algorithms** (Dijkstra/A*), since Python owns routing per ADR-0005. William Fiset's graph theory playlist and Abdul Bari's algorithm videos are both solid. *Search: `William Fiset graph theory playlist`*

---

## Tier 3 — Later phases; do not study now

Reinforcement learning (David Silver's DeepMind course is the standard), optimization methods, GTFS/transit modelling, and visualization frameworks. These are Phase 2–4 material and will be forgotten before they're needed.

---

## Making an actual playlist

There's no way to auto-generate one from here — YouTube playlists must be built from an account. To assemble it: open each verified link above, "Save → New playlist" for the first, then add the rest; for the search-term entries, search, pick the version that looks current, and add it. Suggested playlist split, matching the tiers: **"Traffic sim — Rust & architecture"** (1a, 1b) and **"Traffic sim — domain"** (1d, 1e, 1f).

Ordering advice: don't binge. Interleave one Rust video with one traffic video, and stop watching as soon as a topic becomes something you could implement — the implementation teaches more than the next video.
