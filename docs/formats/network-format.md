# Network file format — v1 (DRAFT)

**Status:** Draft skeleton under the accepted [ADR-0007](../adr/0007-network-file-format.md) (2026-07-06, container amended to columnar at review). Field lists below are indicative; they are completed and frozen as the builder is implemented (ADR-0007 action item 2).

One file describes one loadable network: **`<name>.network.zip`**, containing

- `meta.json` — the `meta` block below (tiny, human-readable JSON);
- `nodes.parquet`, `segments.parquet`, `lanes.parquet`, `connections.parquet`, `signals.parquet` — one Parquet table per record group, mirroring the field tables below.

All coordinates are projected meters in the CRS named in `meta.crs`. The builder also offers a **non-normative** `--export-json` debug view (canonical JSON of the same logical content) for review and diffing; the zip is the artifact of record.

## Canonicalization rules (normative)

1. Rows in every table sorted ascending by `id`; columns in the order defined per record group below.
2. Parquet writer settings are pinned by the builder (library version, compression, row-group size — exact values frozen at builder implementation) so identical inputs produce identical bytes; no NaN/Infinity values permitted.
3. `meta.content_hash` = SHA-256 (hex) over the byte concatenation of the five table members in the fixed order nodes, segments, lanes, connections, signals. `meta.json` is excluded (it contains the hash).
4. Same source inputs + same builder version (incl. pinned pyarrow) ⇒ byte-identical zip members (builder determinism; CI-enforced).
5. Zip members are stored deterministically (fixed member order, zeroed timestamps).

## Record groups

### `meta`

| Field | Type | Notes |
|---|---|---|
| `format_version` / `format_minor` | int / int | Breaking / additive schema changes |
| `network_name` | string | e.g. `toronto-corridor-v1`; pinned by scenarios (ADR-0004) |
| `network_version` | string | e.g. `2026.07-r1`; pinned together with name |
| `content_hash` | string | See canonicalization rule 3 |
| `crs` | string | e.g. `EPSG:32617` |
| `provenance` | object | OSM snapshot date, signal-timing snapshot date, builder version, bbox |

### `nodes` (sorted by id)

| Field | Type | Notes |
|---|---|---|
| `id` | string | `node:<osm_node_id>` (synthesized nodes get a documented suffix scheme) |
| `x`, `y` | float | Projected meters |
| `kind` | string | `intersection` \| `dead_end` \| `boundary` — boundary nodes are demand entry/exit points (ADR-0005) |

### `segments` (sorted by id)

| Field | Type | Notes |
|---|---|---|
| `id` | string | `seg:<osm_way_id>[.<part>]:<dir>` — one record per direction of travel |
| `from_node`, `to_node` | string | Node ids |
| `name`, `road_class` | string | Display name; OSM highway class |
| `source` | object | OSM way id(s) and any split/merge notes |

### `lanes` (sorted by id)

| Field | Type | Notes |
|---|---|---|
| `id` | string | `<segment_id>:<index>`, index 0 = curbside |
| `segment` | string | Parent segment id |
| `length_m` | float | Along-geometry length |
| `speed_limit_mps` | float | Inferred defaults documented by the builder |
| `modes` | array[string] | Open vocabulary; v1 emits `["car"]` (ADR-0002 extensibility) |
| `geometry` | array[[x, y]] | Polyline, projected meters |

### `connections` (sorted by id)

| Field | Type | Notes |
|---|---|---|
| `id` | string | `conn:<from_lane>-><to_lane>` |
| `from_lane`, `to_lane` | string | Lane ids; the node is implied by the lane endpoints |
| `movement` | string | `through` \| `left` \| `right` \| `uturn` |
| `signal_phase` | string \| null | Phase id protecting this movement, if signalized |

Turn restrictions and inferred `turn:lanes` are resolved *before* emission: a prohibited movement is an absent connection. The file states resolved truth; inference lives in the builder.

### `signals` (sorted by id)

| Field | Type | Notes |
|---|---|---|
| `id` | string | `sig:px<PX>` (City of Toronto PX number) where matched |
| `node` | string | Node id |
| `control_mode` | string | As observed (`FT`, `SA1`, `SAV`, …) — descriptive; control *policy* is kernel-side (ADR-0002 amendment) |
| `offset_s` | float | Plan offset |
| `phases` | array | Ordered: `{id, duration_s, connections: [connection ids served]}` |

Future actuated/AI control adds detector fields **additively** (format_minor bump), never restructures phases.

## Validation (loader MUST enforce)

- Referential integrity: every cross-reference resolves; no orphan lanes/connections/phases.
- `format_version` known; `content_hash` verifies.
- Geometry sanity: lane `length_m` consistent with geometry within tolerance; no zero-length lanes.
- Connectivity sanity: every non-boundary lane has ≥1 inbound and ≥1 outbound connection (warnings vs errors to be specified with the builder).

## Related

- [ADR-0007](../adr/0007-network-file-format.md) — decision record and rationale.
- Demand file format (ADR-0005 action item 1) will be specified as a sibling document sharing the ID + versioning conventions.
